#!/bin/bash
# Copyright (c) Huawei Technologies Co., Ltd. 2023-2026. All rights reserved.
# witty-ub is licensed under the Mulan PSL v2.
#
# witty-ub 部署管理器主逻辑（RPM 安装后由 witty-ub-manager 子包提供）
#
# 用法:
#   /usr/libexec/witty-ub-manager/manager.sh             # 交互式菜单
#   /usr/libexec/witty-ub-manager/manager.sh <subcommand> # 直接执行子命令
#
# 由 /usr/bin/witty-ub dispatcher 调用: `witty-ub manager <subcommand>`
#
# 部署角色按已安装子包自动探测（detect_role）:
#   backend  = witty-ub-backend   后端节点（PG + FastAPI latency）
#   frontend = witty-ub-web       前端节点（Nginx + OpenCode Agent）
#   all      = 两个子包都在        单机 All-in-One / 旧单包升级
#
# 子命令:
#   install [--backend URL]   按角色初始化并启动服务（后端: PG+凭据+latency;
#                             前端: 渲染 nginx/Agent 配置+web）
#   config  [--backend URL]   前端机配置后端地址并自动生效（重渲染+重启 web）
#   config  --show            查看当前角色与连接配置
#   uninstall                 停止并禁用 systemd units（保留数据）
#   clean                     清空 PostgreSQL 数据 + /var/witty-ub/data（不可恢复）
#   start/stop/restart/status/logs   仅操作本机角色的服务
#   psql                      连接 PostgreSQL 终端

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/_lib.sh"

print_usage() {
    cat <<EOF
witty-ub 部署管理器

用法:
  witty-ub manager                # 交互式菜单
  witty-ub manager <subcommand>   # 直接执行子命令

子命令:
  install [--backend URL]   按角色初始化并启动服务
                            后端节点: PG 初始化 + 凭据同步 + 启动 latency
                            前端节点: 渲染 nginx/Agent 配置 + 启动 web
                            单机: 两者依次执行
  config [--backend URL]    前端节点配置后端地址，自动重渲染并重启 web
  config --show             查看当前角色与连接配置
  uninstall                 停止并禁用 systemd units（保留数据）
  clean                     清空 PostgreSQL 数据 + /var/witty-ub/data（不可恢复）
  start                     systemctl start 本机角色的服务
  stop                      systemctl stop 本机角色的服务
  restart                   systemctl restart 本机角色的服务
  status                    systemctl status 本机角色的服务
  logs                      journalctl 查看本机角色的服务日志
  psql                      连接 PostgreSQL 终端（仅后端角色）

角色:
  按已安装子包自动探测: witty-ub-backend → 后端, witty-ub-web → 前端,
  两者都在 → 单机。WITTY_ROLE_FORCE=all|backend|frontend 可覆盖。

环境变量:
  NONINTERACTIVE=1   跳过交互确认（CI/自动化测试）
  WITTY_ROLE_FORCE   覆盖角色探测结果
EOF
}

# --help 无需角色探测
case "${1:-}" in
-h | --help | help)
    print_usage
    exit 0
    ;;
esac

# 启动即探测角色（WITTY_ROLE_FORCE 可覆盖）
detect_role || exit 1
role_services
_log "部署角色: ${WITTY_ROLE}（服务: ${WITTY_SERVICES[*]:-无}）"

# ──────────────────── PG 凭据同步 ────────────────────

# 将 /etc/witty-ub/pg.conf 中实际的 PG 凭据写入 diagnosis_config.toml 的 [db] 段。
# 实测踩坑：仓库 config 默认 pg_password=""，而 deploy_pg.sh 用 pg.conf 的
# PG_PASSWORD 建库 → 后端 InvalidPasswordError。
sync_pg_credentials() {
    _load_pg_credentials || {
        _warn "无法加载 PG 凭据，跳过同步"
        return 0
    }

    [ -f "$DIAG_CONFIG_FILE" ] || {
        _warn "diagnosis_config.toml 不存在: $DIAG_CONFIG_FILE"
        return 0
    }

    sed -i \
        -e "s|^pg_host = .*|pg_host = \"$PG_HOST\"|" \
        -e "s|^pg_port = .*|pg_port = $PG_PORT|" \
        -e "s|^pg_database = .*|pg_database = \"$PG_DATABASE\"|" \
        -e "s|^pg_user = .*|pg_user = \"$PG_USER\"|" \
        -e "s|^pg_password = .*|pg_password = \"$PG_PASSWORD\"|" \
        "$DIAG_CONFIG_FILE" 2>/dev/null || true
    _log "PG 凭据已同步到 $DIAG_CONFIG_FILE (host=$PG_HOST port=$PG_PORT db=$PG_DATABASE user=$PG_USER)"
}

# ──────────────────── 访问信息 ────────────────────

show_access_info() {
    local HOST_IP
    HOST_IP="$(hostname -I 2>/dev/null | awk '{print $1}')"
    echo ""
    echo "╔══════════════════════════════════════════════╗"
    echo "║  witty-ub 部署完成！（角色: ${WITTY_ROLE}）      "
    if [ "$WITTY_ROLE" != "backend" ]; then
        echo "║  前端:   http://localhost:8080               ║"
        [ -n "$HOST_IP" ] && printf "║  前端:   http://%-26s ║\n" "${HOST_IP}:8080"
    fi
    if [ "$WITTY_ROLE" = "frontend" ]; then
        local BACKEND_URL
        BACKEND_URL="$(web_env_get WITTY_BACKEND_URL http://127.0.0.1:9772)"
        printf "║  后端:   http://%-26s ║\n" "${BACKEND_URL#http://}"
    else
        echo "║  后端:   http://localhost:9772               ║"
        echo "║  健康:   http://localhost:9772/health_check   ║"
    fi
    echo "║                                              ║"
    echo "║  管理入口: witty-ub manager                    ║"
    echo "╚══════════════════════════════════════════════╝"
    echo ""
}

# ──────────────────── install ────────────────────

# 后端角色初始化: 依赖检查 → PG 初始化 → 凭据同步 → 启动 latency → 健康检查
install_backend() {
    _step_header "初始化后端节点（PostgreSQL + latency）"

    bash "$SCRIPT_DIR/install_deps.sh" || { _warn "依赖检查未通过，继续尝试初始化"; }

    _info "初始化 PostgreSQL（如果尚未部署）..."
    bash "$SCRIPT_DIR/deploy_pg.sh" || {
        _err "PostgreSQL 初始化失败"
        return 1
    }

    sync_pg_credentials

    _info "启动 witty-ub-latency 服务..."
    systemctl daemon-reload 2>/dev/null || true
    systemctl enable --now witty-ub-latency 2>/dev/null || true

    _info "等待后端启动（最多 60 秒，首次启动会自动建表）..."
    local ok=0
    for _ in $(seq 1 30); do
        if curl --noproxy 127.0.0.1 -sf http://127.0.0.1:9772/health_check >/dev/null 2>&1; then
            ok=1
            break
        fi
        sleep 2
    done
    if [ "$ok" = "1" ]; then
        _log "后端已就绪: http://127.0.0.1:9772/health_check"
    else
        _warn "后端 60 秒内未通过健康检查"
        _info "查看日志: sudo witty-ub manager logs"
        _info "常见原因: PG 凭据不匹配 / 防火墙 / 端口被占用"
    fi
}

# 前端角色初始化: 依赖检查 → 写 web env → 渲染 nginx/Agent → 启动 web → 探测
# $1: 后端地址（空则读 /etc/witty-ub/web/env 现值）
install_frontend() {
    _step_header "初始化前端节点（Nginx + Agent 配置）"

    local backend_url agent_url
    backend_url="${1:-$(web_env_get WITTY_BACKEND_URL http://127.0.0.1:9772)}"
    agent_url="$(web_env_get WITTY_AGENT_URL http://127.0.0.1:4096)"

    bash "$SCRIPT_DIR/install_deps.sh" || { _warn "依赖检查未通过，继续尝试初始化"; }

    write_web_env "$backend_url" "$agent_url"
    render_frontend_configs

    _info "启动 witty-ub-web 服务..."
    systemctl daemon-reload 2>/dev/null || true
    systemctl enable --now witty-ub-web 2>/dev/null || true

    sleep 1
    if curl --noproxy 127.0.0.1 -sf -o /dev/null http://127.0.0.1:8080/ 2>/dev/null; then
        _log "前端页面就绪: http://127.0.0.1:8080"
    else
        _warn "前端页面未就绪，查看日志: sudo witty-ub manager logs"
    fi
    if curl --noproxy '*' -sf -o /dev/null --max-time 5 "${backend_url}/health_check" 2>/dev/null; then
        _log "后端可达: ${backend_url}/health_check"
    else
        _warn "后端不可达: ${backend_url}"
        _info "确认后端节点已执行 witty-ub manager install 且防火墙已放行 9772"
    fi

    _info "OpenCode Agent 维持手动启动:"
    _info "  set -a; source /etc/witty-ub/web/env; set +a"
    _info "  bash /var/witty-ub/latency/deploy/run_opencode.sh"
}

do_install_check_subpackages() {
    if [ "$WITTY_ROLE" != "frontend" ]; then
        rpm -q witty-ub-backend >/dev/null 2>&1 || rpm -q witty-ub >/dev/null 2>&1 || {
            _err "witty-ub-backend 未安装。请先执行: sudo dnf install -y witty-ub-backend"
            return 1
        }
    fi
    if [ "$WITTY_ROLE" != "backend" ]; then
        rpm -q witty-ub-web >/dev/null 2>&1 || rpm -q witty-ub >/dev/null 2>&1 || {
            _err "witty-ub-web 未安装。请先执行: sudo dnf install -y witty-ub-web"
            return 1
        }
    fi
}

do_install() {
    local backend_url=""
    while [ $# -gt 0 ]; do
        case "$1" in
        --backend)
            [ $# -ge 2 ] || {
                _err "--backend 需要参数: --backend http://<ip>:9772"
                return 1
            }
            backend_url="$2"
            shift 2
            ;;
        *)
            _err "未知参数: $1"
            return 1
            ;;
        esac
    done

    do_install_check_subpackages || return 1

    case "$WITTY_ROLE" in
    backend)
        install_backend
        ;;
    frontend)
        install_frontend "$backend_url"
        ;;
    all)
        install_backend
        [ -n "$backend_url" ] || backend_url="http://127.0.0.1:9772"
        install_frontend "$backend_url"
        ;;
    esac

    show_access_info
}

# ──────────────────── config ────────────────────

# 配置即生效: 写 web env → 重渲染 nginx/Agent 提示词 → 重启 web
do_config() {
    local backend_url="" show=0
    while [ $# -gt 0 ]; do
        case "$1" in
        --backend)
            [ $# -ge 2 ] || {
                _err "--backend 需要参数: --backend http://<ip>:9772"
                return 1
            }
            backend_url="$2"
            shift 2
            ;;
        --show)
            show=1
            shift
            ;;
        *)
            _err "未知参数: $1"
            return 1
            ;;
        esac
    done

    if [ "$show" = "1" ]; then
        _step_header "witty-ub 连接配置"
        echo "  部署角色:      ${WITTY_ROLE}"
        echo "  本机服务:      ${WITTY_SERVICES[*]:-无}"
        if [ -f "$WITTY_WEB_ENV" ]; then
            echo "  配置文件:      $WITTY_WEB_ENV"
            grep -E '^(WITTY_BACKEND_URL|WITTY_API_BASE|WITTY_AGENT_URL|WITTY_NO_PROXY)=' "$WITTY_WEB_ENV" | sed 's/^/    /'
        else
            echo "  配置文件:      $WITTY_WEB_ENV（不存在）"
        fi
        return 0
    fi

    [ -n "$backend_url" ] || {
        _err "请指定 --backend http://<ip>:9772（或使用 --show 查看当前配置）"
        return 1
    }
    case "$backend_url" in
    http://* | https://*) : ;;
    *)
        _err "后端地址格式应为 http://<ip>:9772，当前: $backend_url"
        return 1
        ;;
    esac

    if [ "$WITTY_ROLE" = "backend" ]; then
        _warn "当前是后端节点（角色: backend），无需配置后端地址"
        _info "如需修改 PG 凭据: 编辑 /etc/witty-ub/deploy.conf 后重新执行 witty-ub manager install"
        return 0
    fi

    _step_header "配置后端地址: ${backend_url}"

    local agent_url
    agent_url="$(web_env_get WITTY_AGENT_URL http://127.0.0.1:4096)"
    write_web_env "$backend_url" "$agent_url"
    render_frontend_configs || return 1

    if systemctl is-active --quiet witty-ub-web 2>/dev/null; then
        _info "重启 witty-ub-web 使配置生效..."
        systemctl restart witty-ub-web || {
            _err "witty-ub-web 重启失败"
            return 1
        }
        _log "配置已生效"
    else
        _log "配置已写入（witty-ub-web 未运行，下次启动时生效）"
    fi

    _info "如 OpenCode 已在运行，需重启以加载新的后端地址:"
    _info "  set -a; source /etc/witty-ub/web/env; set +a"
    _info "  bash /var/witty-ub/latency/deploy/run_opencode.sh"
}

# ──────────────────── uninstall ────────────────────

do_uninstall() {
    _step_header "卸载 witty-ub 部署（保留数据）"

    _info "停止并禁用 systemd services..."
    systemctl disable --now "${WITTY_SERVICES[@]}" 2>/dev/null || true

    _log "服务已停止并禁用（角色: ${WITTY_ROLE}）"
    case "$WITTY_ROLE" in
    backend) _info "如需彻底卸载软件包: sudo dnf remove -y witty-ub-backend witty-ub-manager" ;;
    frontend) _info "如需彻底卸载软件包: sudo dnf remove -y witty-ub-web witty-ub-manager" ;;
    *) _info "如需彻底卸载软件包: sudo dnf remove -y witty-ub witty-ub-backend witty-ub-web witty-ub-manager" ;;
    esac
    _info "如需清空数据:           sudo witty-ub manager clean"
}

# ──────────────────── clean ────────────────────

# 清空 PG 数据表 + /var/witty-ub 运行数据。保留 RPM 安装文件、PG 库本身、用户。
do_clean() {
    _step_header "清空 witty-ub 数据（不可恢复）"

    _warn "即将执行:"
    echo "  - 停止 witty-ub 服务"
    echo "  - 清空 PostgreSQL 全部数据表 (TRUNCATE CASCADE)"
    echo "  - 删除 /var/witty-ub/data 和 /var/witty-ub/latency/file 下文件"
    echo "  - 保留: RPM 安装文件 / PG 库本身 / PG 用户 / 配置文件"
    echo ""
    if ! _confirm "确认全部清理？此操作不可恢复"; then
        _log "已取消"
        return 0
    fi

    # 1. 停服务
    _info "停止服务..."
    systemctl stop "${WITTY_SERVICES[@]}" 2>/dev/null || true

    # 2. 清 PG 数据表（保留库本身，只清表数据）
    if _has_cmd psql && _psql -c "" >/dev/null 2>&1; then
        _info "清空 PostgreSQL 数据表..."
        _psql -c "
            DO \$\$ DECLARE t text; BEGIN
                FOR t IN SELECT tablename FROM pg_tables WHERE schemaname='public' LOOP
                    EXECUTE format('TRUNCATE TABLE %I CASCADE', t);
                END LOOP;
            END \$\$;" 2>&1 | tail -2
        _log "PostgreSQL 数据表已清空"
    else
        _warn "PostgreSQL 未连接，跳过清库（检查 /etc/witty-ub/deploy.conf）"
    fi

    # 3. 清 /var/witty-ub 运行数据（保留配置文件 diagnosis_config.toml 等）
    _info "清理运行数据..."
    # data 目录下是故障模式数据，rpm 重装会还原；用户清理表示要重来
    rm -rf "${WITTY_DIR}/data"/* 2>/dev/null || true
    rm -rf "${WITTY_DIR}/latency/file/file_upload"/* 2>/dev/null || true
    rm -rf "${WITTY_DIR}/latency/file/file_parse_result"/* 2>/dev/null || true
    rm -rf /var/log/witty-ub/* 2>/dev/null || true
    _log "运行数据已清空"

    _step_header "清理完成"
    _info "下次启动: sudo witty-ub manager start"
}

# ──────────────────── start/stop/restart/status ────────────────────

do_start() {
    _step_header "启动 witty-ub 服务"
    systemctl start "${WITTY_SERVICES[@]}" 2>/dev/null || {
        _err "启动失败"
        _info "查看日志: sudo witty-ub manager logs"
        return 1
    }
    _log "启动完成"
    _info "查看状态: witty-ub manager status"
}

do_stop() {
    _step_header "停止 witty-ub 服务"
    systemctl stop "${WITTY_SERVICES[@]}" 2>/dev/null || true
    _log "已停止"
}

do_restart() {
    _step_header "重启 witty-ub 服务"
    systemctl restart "${WITTY_SERVICES[@]}" 2>/dev/null || {
        _err "重启失败"
        return 1
    }
    _log "重启完成"
}

do_status() {
    _step_header "witty-ub 服务状态（角色: ${WITTY_ROLE}）"
    local svc
    for svc in "${WITTY_SERVICES[@]}"; do
        echo ""
        systemctl status "$svc" 2>/dev/null || true
    done
    echo ""
    _info "端口监听:"
    local PORTS="9772"
    [ "$WITTY_ROLE" != "backend" ] && PORTS="8080|4096|${PORTS}"
    [ "$WITTY_ROLE" != "frontend" ] && PORTS="${PORTS}|5432"
    if _has_cmd ss; then
        ss -tlnp 2>/dev/null | grep -E ":(${PORTS}) " || true
    elif _has_cmd netstat; then
        netstat -tlnp 2>/dev/null | grep -E ":(${PORTS}) " || true
    fi
}

# ──────────────────── logs ────────────────────

do_logs() {
    _step_header "查看 witty-ub 日志 (Ctrl+C 退出)"
    local choice
    if [ "$WITTY_ROLE" = "frontend" ]; then
        journalctl -u witty-ub-web -f
        return 0
    fi
    if [ "$WITTY_ROLE" = "backend" ]; then
        journalctl -u witty-ub-latency -f
        return 0
    fi
    _info "选择查看哪个服务的日志:"
    echo "  1) witty-ub-web (Nginx 前端)"
    echo "  2) witty-ub-latency (FastAPI 后端)"
    echo "  3) 全部"
    read -r -p "请选择 [1-3, 默认 3]: " choice
    choice="${choice:-3}"
    case "$choice" in
    1) journalctl -u witty-ub-web -f ;;
    2) journalctl -u witty-ub-latency -f ;;
    3) journalctl -u witty-ub-web -u witty-ub-latency -f ;;
    *)
        _err "无效选项"
        return 1
        ;;
    esac
}

# ──────────────────── psql ────────────────────

do_psql() {
    _step_header "连接 PostgreSQL 终端"
    if [ "$WITTY_ROLE" = "frontend" ]; then
        _err "当前是前端节点（角色: frontend），PostgreSQL 部署在后端节点"
        return 1
    fi
    if ! _has_cmd psql; then
        _err "psql 未安装"
        _info "安装: sudo dnf install -y postgresql"
        return 1
    fi
    if ! _psql -c "" >/dev/null 2>&1; then
        _err "无法连接 PostgreSQL，请先执行: sudo witty-ub manager install"
        return 1
    fi
    _info "进入 psql（输入 \\q 退出）"
    _psql
}

# ──────────────────── 交互式菜单 ────────────────────

show_menu() {
    echo ""
    echo "========================================"
    echo "  witty-ub 部署管理器（角色: ${WITTY_ROLE}）"
    echo "========================================"
    echo ""
    echo "  📦  部署"
    echo "    1) 初始化（按角色: 后端 PG+latency / 前端 渲染+web）"
    if [ "$WITTY_ROLE" != "backend" ]; then
        echo "    2) 配置后端地址（config --backend，自动生效）"
        echo "    3) 查看连接配置（config --show）"
    fi
    echo ""
    echo "  🔧  管理"
    echo "    4) 启动服务（${WITTY_SERVICES[*]:-无}）"
    echo "    5) 停止服务"
    echo "    6) 重启服务"
    echo "    7) 查看状态"
    echo "    8) 查看日志"
    echo ""
    echo "  🗑️  清理"
    echo "    9) 清空数据（PG + /var 数据）"
    echo "    a) 卸载（停服务 + 禁用 units，保留数据）"
    echo ""
    echo "  💻  工具"
    echo "    p) 进入 psql（仅后端角色）"
    echo ""
    echo "    0) 退出"
    echo ""
    echo "========================================"
}

menu_main() {
    while true; do
        show_menu
        read -r -p "请选择操作 [0-9,a,p]: " choice
        echo ""
        case "$choice" in
        1) do_install ;;
        2) menu_config_backend ;;
        3) do_config --show ;;
        4) do_start ;;
        5) do_stop ;;
        6) do_restart ;;
        7) do_status ;;
        8) do_logs ;;
        9) do_clean ;;
        a) do_uninstall ;;
        p) do_psql ;;
        0)
            echo "再见！"
            exit 0
            ;;
        *) _err "无效选项，请重新选择" ;;
        esac
        echo ""
        read -r -p "按回车继续..." _
    done
}

# 菜单项: 交互式输入后端地址
menu_config_backend() {
    if [ "$WITTY_ROLE" = "backend" ]; then
        _err "当前是后端节点，无需配置后端地址"
        return 1
    fi
    local url
    read -r -p "后端地址 (如 http://192.168.1.10:9772): " url
    [ -n "$url" ] || {
        _warn "未输入地址，已取消"
        return 0
    }
    do_config --backend "$url"
}

# ──────────────────── 参数解析 ────────────────────

case "${1:-menu}" in
install | i)
    shift
    do_install "$@"
    ;;
config | cf)
    shift
    do_config "$@"
    ;;
uninstall | u) do_uninstall ;;
clean | c) do_clean ;;
start | s) do_start ;;
stop | x) do_stop ;;
restart | r) do_restart ;;
status | st) do_status ;;
logs | l) do_logs ;;
psql | p) do_psql ;;
menu | -m | --menu) menu_main ;;
-h | --help | help) print_usage ;;
*)
    echo "未知子命令: $1" >&2
    echo "使用 'witty-ub manager --help' 查看帮助" >&2
    exit 1
    ;;
esac
