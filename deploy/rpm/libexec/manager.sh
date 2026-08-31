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
# 子命令:
#   install      初始化 PostgreSQL + 同步凭据 + 启动服务
#   uninstall    停止并禁用 systemd units（保留数据）
#   clean        清空 PostgreSQL 数据 + /var/witty-ub/data（不可恢复）
#   start        systemctl start witty-ub-web witty-ub-latency
#   stop         systemctl stop witty-ub-web witty-ub-latency
#   restart      systemctl restart witty-ub-web witty-ub-latency
#   status       systemctl status witty-ub-web witty-ub-latency
#   logs         journalctl -u witty-ub-web / witty-ub-latency -f
#   psql         连接 PostgreSQL 终端

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/_lib.sh"

# ──────────────────── PG 凭据同步 ────────────────────

# 将 /etc/witty-ub/pg.conf 中实际的 PG 凭据写入 diagnosis_config.toml 的 [db] 段。
# 实测踩坑：仓库 config 默认 pg_password=""，而 deploy_pg.sh 用 pg.conf 的
# PG_PASSWORD 建库 → 后端 InvalidPasswordError。
sync_pg_credentials() {
    _load_pg_credentials || { _warn "无法加载 PG 凭据，跳过同步"; return 0; }

    [ -f "$DIAG_CONFIG_FILE" ] || { _warn "diagnosis_config.toml 不存在: $DIAG_CONFIG_FILE"; return 0; }

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
    echo "║  witty-ub 部署完成！                          ║"
    echo "║                                              ║"
    echo "║  前端:   http://localhost:8080               ║"
    if [ -n "$HOST_IP" ]; then
        printf "║  前端:   http://%-26s ║\n" "${HOST_IP}:8080"
    fi
    echo "║  后端:   http://localhost:9772               ║"
    echo "║  健康:   http://localhost:9772/health_check   ║"
    echo "║                                              ║"
    echo "║  管理入口: witty-ub manager                    ║"
    echo "╚══════════════════════════════════════════════╝"
    echo ""
}

# ──────────────────── install ────────────────────

do_install() {
    _step_header "初始化 witty-ub 部署"

    # 1. 检查 RPM 主包是否安装
    if ! rpm -q witty-ub >/dev/null 2>&1; then
        _err "witty-ub 主包未安装。请先执行: sudo yum install -y witty-ub"
        return 1
    fi
    _log "witty-ub 主包已安装"

    # 2. 检查依赖（venv / systemctl / psql 等）
    bash "$SCRIPT_DIR/install_deps.sh" || { _warn "依赖检查未通过，继续尝试初始化"; }

    # 3. PG 初始化（幂等：已存在的资源跳过）
    _info "初始化 PostgreSQL（如果尚未部署）..."
    bash "$SCRIPT_DIR/deploy_pg.sh" || { _err "PostgreSQL 初始化失败"; return 1; }

    # 4. 同步 PG 凭据到 diagnosis_config.toml
    sync_pg_credentials

    # 5. 启动服务
    _info "启动 witty-ub 服务..."
    systemctl daemon-reload 2>/dev/null || true
    systemctl enable --now "${WITTY_SERVICES[@]}" 2>/dev/null || true

    # 6. 等待后端健康检查（后端首次启动会自动建表）
    _info "等待后端启动（最多 60 秒，首次启动会自动建表）..."
    local ok=0
    for i in $(seq 1 30); do
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

    show_access_info
}

# ──────────────────── uninstall ────────────────────

do_uninstall() {
    _step_header "卸载 witty-ub 部署（保留数据）"

    _info "停止并禁用 systemd services..."
    systemctl disable --now "${WITTY_SERVICES[@]}" 2>/dev/null || true

    _log "服务已停止并禁用"
    _info "如需彻底卸载软件包: sudo yum remove -y witty-ub witty-ub-manager"
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
        _warn "PostgreSQL 未连接，跳过清库（检查 /etc/witty-ub/pg.conf）"
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
    _step_header "witty-ub 服务状态"
    local svc
    for svc in "${WITTY_SERVICES[@]}"; do
        echo ""
        systemctl status "$svc" 2>/dev/null || true
    done
    echo ""
    _info "端口监听:"
    if _has_cmd ss; then
        ss -tlnp 2>/dev/null | grep -E ':(8080|9772|5432) ' || true
    elif _has_cmd netstat; then
        netstat -tlnp 2>/dev/null | grep -E ':(8080|9772|5432) ' || true
    fi
}

# ──────────────────── logs ────────────────────

do_logs() {
    _step_header "查看 witty-ub 日志 (Ctrl+C 退出)"
    _info "选择查看哪个服务的日志:"
    echo "  1) witty-ub-web (Nginx 前端)"
    echo "  2) witty-ub-latency (FastAPI 后端)"
    echo "  3) 全部"
    local choice
    read -r -p "请选择 [1-3, 默认 3]: " choice
    choice="${choice:-3}"
    case "$choice" in
        1) journalctl -u witty-ub-web -f ;;
        2) journalctl -u witty-ub-latency -f ;;
        3) journalctl -u witty-ub-web -u witty-ub-latency -f ;;
        *) _err "无效选项"; return 1 ;;
    esac
}

# ──────────────────── psql ────────────────────

do_psql() {
    _step_header "连接 PostgreSQL 终端"
    if ! _has_cmd psql; then
        _err "psql 未安装"
        _info "安装: sudo yum install -y postgresql"
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
    echo "  witty-ub 部署管理器"
    echo "========================================"
    echo ""
    echo "  📦  部署"
    echo "    1) 初始化（PG + 凭据 + 启动服务）"
    echo ""
    echo "  🔧  管理"
    echo "    2) 启动服务"
    echo "    3) 停止服务"
    echo "    4) 重启服务"
    echo "    5) 查看状态"
    echo "    6) 查看日志"
    echo ""
    echo "  🗑️  清理"
    echo "    7) 清空数据（PG + /var 数据）"
    echo "    8) 卸载（停服务 + 禁用 units，保留数据）"
    echo ""
    echo "  💻  工具"
    echo "    9) 进入 psql"
    echo ""
    echo "    0) 退出"
    echo ""
    echo "========================================"
}

menu_main() {
    while true; do
        show_menu
        read -r -p "请选择操作 [0-9]: " choice
        echo ""
        case "$choice" in
            1) do_install ;;
            2) do_start ;;
            3) do_stop ;;
            4) do_restart ;;
            5) do_status ;;
            6) do_logs ;;
            7) do_clean ;;
            8) do_uninstall ;;
            9) do_psql ;;
            0) echo "再见！"; exit 0 ;;
            *) _err "无效选项，请重新选择" ;;
        esac
        echo ""
        read -r -p "按回车继续..." _
    done
}

# ──────────────────── 参数解析 ────────────────────

case "${1:-menu}" in
    install|i)        do_install ;;
    uninstall|u)      do_uninstall ;;
    clean|c)          do_clean ;;
    start|s)          do_start ;;
    stop|x)           do_stop ;;
    restart|r)        do_restart ;;
    status|st)        do_status ;;
    logs|l)           do_logs ;;
    psql|p)           do_psql ;;
    menu|-m|--menu)   menu_main ;;
    -h|--help|help)
        cat <<EOF
witty-ub 部署管理器

用法:
  witty-ub manager                # 交互式菜单
  witty-ub manager <subcommand>   # 直接执行子命令

子命令:
  install      初始化 PostgreSQL + 同步凭据 + 启动服务
  uninstall    停止并禁用 systemd units（保留数据）
  clean        清空 PostgreSQL 数据 + /var/witty-ub/data（不可恢复）
  start        systemctl start witty-ub-web witty-ub-latency
  stop         systemctl stop witty-ub-web witty-ub-latency
  restart      systemctl restart witty-ub-web witty-ub-latency
  status       systemctl status witty-ub-web witty-ub-latency
  logs         journalctl -u witty-ub-web / witty-ub-latency -f
  psql         连接 PostgreSQL 终端

环境变量:
  NONINTERACTIVE=1   跳过交互确认（CI/自动化测试）
EOF
        ;;
    *)
        echo "未知子命令: $1" >&2
        echo "使用 'witty-ub manager --help' 查看帮助" >&2
        exit 1
        ;;
esac
