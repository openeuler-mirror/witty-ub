#!/bin/bash
# Copyright (c) Huawei Technologies Co., Ltd. 2023-2026. All rights reserved.
# witty-ub is licensed under the Mulan PSL v2.
#
# witty-ub 宿主机/裸金属 一键部署脚本
# 支持 openEuler 24.03-LTS / Ubuntu 24.04 / WSL (Ubuntu)
#
# 用法:
#   bash deploy/host/deploy.sh          # 完整部署（首次运行）
#   bash deploy/host/deploy.sh --start  # 仅启动服务（已部署过）
#   bash deploy/host/deploy.sh --stop   # 停止所有服务
#   bash deploy/host/deploy.sh --clean  # 一键清理
#
# 访问:
#   前端: http://localhost:5173     (开发模式, Vite HMR)
#   后端: http://localhost:9772
#   健康: http://localhost:9772/health_check

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$(dirname "$SCRIPT_DIR")")"
LOG_DIR="$PROJECT_DIR/.deploy-logs"

# ──────────────────── 载入子脚本 ────────────────────

source "$SCRIPT_DIR/_lib.sh"
source "$SCRIPT_DIR/install_deps.sh"

# ──────────────────── PostgreSQL ────────────────────

setup_postgresql() {
    _step_header "初始化 PostgreSQL"

    local PG_HOST="${PG_HOST:-127.0.0.1}"
    local PG_PORT="${PG_PORT:-15432}"

    if _has_cmd pg_isready && pg_isready -h "$PG_HOST" -p "$PG_PORT" 2>/dev/null; then
        _log "PostgreSQL 已运行在 $PG_HOST:$PG_PORT，跳过初始化"
        return 0
    fi

    local DEPLOY_PG_SCRIPT="$SCRIPT_DIR/../deploy_pg.sh"

    if [ ! -f "$DEPLOY_PG_SCRIPT" ]; then
        _err "找不到 $DEPLOY_PG_SCRIPT"
        return 1
    fi

    case "$OS_ID" in
        openeuler)
            _info "调用 deploy/deploy_pg.sh --rpm 部署 PostgreSQL..."
            if _is_root; then
                bash "$DEPLOY_PG_SCRIPT" --rpm
            elif _has_cmd sudo; then
                sudo bash "$DEPLOY_PG_SCRIPT" --rpm
            else
                _warn "需要 root 权限: sudo bash $DEPLOY_PG_SCRIPT --rpm"
                return 1
            fi
            ;;
        ubuntu)
            _info "调用 deploy/deploy_pg.sh --apt 部署 PostgreSQL..."
            if _is_root; then
                bash "$DEPLOY_PG_SCRIPT" --apt
            elif _has_cmd sudo; then
                sudo bash "$DEPLOY_PG_SCRIPT" --apt
            else
                _warn "需要 root 权限: sudo bash $DEPLOY_PG_SCRIPT --apt"
                return 1
            fi
            ;;
    esac

    _log "PostgreSQL 就绪: $PG_HOST:$PG_PORT"
}

# ──────────────────── C++ 编译 ────────────────────

build_cpp() {
    _step_header "编译 C++ 诊断工具"

    local BUILD_DIR="$PROJECT_DIR/build"
    local DIAG_TOOL="$BUILD_DIR/src/witty-ub-diag-tool"

    if [ -f "$DIAG_TOOL" ]; then
        _log "witty-ub-diag-tool 已存在，跳过编译"
        return 0
    fi

    mkdir -p "$BUILD_DIR"
    cd "$BUILD_DIR"

    _info "CMake 配置..."
    cmake "$PROJECT_DIR" -DCMAKE_BUILD_TYPE=Release 2>&1 | tail -3

    _info "编译 witty-ub-diag-tool (使用 $(nproc) 核)..."
    make -j"$(nproc)" witty-ub-diag-tool 2>&1 | tail -5

    if [ -f "$DIAG_TOOL" ]; then
        chmod +x "$DIAG_TOOL"
        _log "witty-ub-diag-tool 编译完成: $DIAG_TOOL"
    else
        _err "C++ 编译失败: $DIAG_TOOL 不存在"
        _err "诊断功能将不可用。请检查 CMake/make 输出后再运行:"
        _err "  cmake $PROJECT_DIR -DCMAKE_BUILD_TYPE=Release && make -j\$(nproc) witty-ub-diag-tool"
        return 1
    fi

    cd "$PROJECT_DIR"
}

# ──────────────────── 前端编译 ────────────────────

build_frontend() {
    _step_header "编译前端 (可选)"

    local WEB_DIR="$PROJECT_DIR/src/web"
    [ -d "$WEB_DIR" ] || { _warn "前端目录不存在，跳过"; return 0; }

    cd "$WEB_DIR"
    _check_node || _warn "Node 版本不满足要求，前端编译可能失败"
    if ! npm ping --silent 2>/dev/null; then
        _warn "npm registry 不可达 (SSL 代理拦截?)"
        _info "已检测到 .npmrc 文件:"
        grep -H '^registry=' "$WEB_DIR/.npmrc" "$PROJECT_DIR/.npmrc" 2>/dev/null || true
        _info "可尝试: npm config set strict-ssl false"
    fi
    [ -d node_modules ] || npm install --silent 2>&1 | tail -3
    npm run build-only 2>&1 | tail -5 || _warn "前端编译失败，运行 npm run dev 启动开发模式"
    cd "$PROJECT_DIR"
    _log "前端编译完成: $WEB_DIR/dist/"
}

# ──────────────────── 数据文件 ────────────────────

copy_data_files() {
    _step_header "部署数据文件"

    local WITTY_DIR="/var/witty-ub"
    local SUDO=""; _is_root || SUDO="sudo"

    $SUDO mkdir -p "$WITTY_DIR/data/kvcache" \
                  "$WITTY_DIR/data/urma" \
                  "$WITTY_DIR/data/view-vis" \
                  "$WITTY_DIR/config/agents" 2>/dev/null || true

    $SUDO cp "$PROJECT_DIR/data/failure_mode_tree.json" "$WITTY_DIR/data/" 2>/dev/null || true
    $SUDO cp "$PROJECT_DIR/data/kvcache/"*.json "$WITTY_DIR/data/kvcache/" 2>/dev/null || true
    $SUDO cp "$PROJECT_DIR/data/urma/"*.json "$WITTY_DIR/data/urma/" 2>/dev/null || true
    $SUDO cp "$PROJECT_DIR/data/view-vis/"* "$WITTY_DIR/data/view-vis/" 2>/dev/null || true
    $SUDO cp "$PROJECT_DIR/config/diagnosis_config.toml" "$WITTY_DIR/config/" 2>/dev/null || true
    $SUDO cp "$PROJECT_DIR/config/agents/"*.md "$WITTY_DIR/config/agents/" 2>/dev/null || true

    _log "数据文件已部署到 $WITTY_DIR"
}

# ──────────────────── PG 凭据同步 ────────────────────

sync_pg_credentials() {
    # 将 deploy/pg.conf 中实际的 PG 凭据写入 diagnosis_config.toml 的 [db] 段
    # （仓库 + /var 两份），确保后端连接凭据与 deploy_pg.sh 创建的库一致。
    # 实测踩坑：仓库 config 默认 pg_password=""，而 deploy_pg.sh 用 pg.conf
    # 的 PG_PASSWORD 建库 → 后端 InvalidPasswordError。
    local PG_CONF_FILE="$SCRIPT_DIR/../pg.conf"
    [ -f "$PG_CONF_FILE" ] || { _warn "pg.conf 不存在，跳过凭据同步"; return 0; }

    local PHOST P PORT PUSER PDB PPASS
    PHOST="$(grep -E '^PG_HOST=' "$PG_CONF_FILE" | head -1 | cut -d= -f2 | tr -d '"')"
    PORT="$(grep -E '^PG_PORT=' "$PG_CONF_FILE" | head -1 | cut -d= -f2 | tr -d '"')"
    PUSER="$(grep -E '^PG_USER=' "$PG_CONF_FILE" | head -1 | cut -d= -f2 | tr -d '"')"
    PDB="$(grep -E '^PG_DATABASE=' "$PG_CONF_FILE" | head -1 | cut -d= -f2 | tr -d '"')"
    PPASS="$(grep -E '^PG_PASSWORD=' "$PG_CONF_FILE" | head -1 | cut -d= -f2 | tr -d '"')"

    [ -n "$PHOST" ] || PHOST="127.0.0.1"
    [ -n "$PORT" ]  || PORT="15432"
    [ -n "$PUSER" ] || PUSER="witty-ub"
    [ -n "$PDB" ]   || PDB="witty-ub"
    [ -n "$PPASS" ] || { _warn "pg.conf 未设置 PG_PASSWORD，跳过"; return 0; }

    local SUDO=""; _is_root || SUDO="sudo"
    local WITTY_DIR="/var/witty-ub"
    for CONF in "$PROJECT_DIR/config/diagnosis_config.toml" "$WITTY_DIR/config/diagnosis_config.toml"; do
        [ -f "$CONF" ] || continue
        $SUDO sed -i \
            -e "s|^pg_host = .*|pg_host = \"$PHOST\"|" \
            -e "s|^pg_port = .*|pg_port = $PORT|" \
            -e "s|^pg_database = .*|pg_database = \"$PDB\"|" \
            -e "s|^pg_user = .*|pg_user = \"$PUSER\"|" \
            -e "s|^pg_password = .*|pg_password = \"$PPASS\"|" \
            "$CONF" 2>/dev/null || true
        _log "已同步 PG 凭据到 $CONF (host=$PHOST port=$PORT db=$PDB user=$PUSER)"
    done
}

# ──────────────────── 启动服务 ────────────────────

start_services() {
    _step_header "启动服务"

    local LATENCY_DIR="$PROJECT_DIR/src/plugins/latency"
    local WEB_DIR="$PROJECT_DIR/src/web"
    local BUILD_DIR="$PROJECT_DIR/build"

    mkdir -p "$LOG_DIR"

    # --- Kill old processes (PID file first, then by port) ---
    # 只杀本项目的旧进程：PID 文件 + 精确端口（fuser）。不用宽泛的
    # pkill -f "fastapi_server" —— 会误杀其他项目/用户的同名进程。
    [ -f "$LOG_DIR/backend.pid" ]  && kill "$(cat "$LOG_DIR/backend.pid")"  2>/dev/null || true
    [ -f "$LOG_DIR/frontend.pid" ] && kill "$(cat "$LOG_DIR/frontend.pid")" 2>/dev/null || true
    _has_cmd fuser && { fuser -k 9772/tcp 2>/dev/null || true; fuser -k 5173/tcp 2>/dev/null || true; }
    sleep 1

    # --- Verify PostgreSQL is reachable ---
    local PG_HOST="${PG_HOST:-127.0.0.1}"
    local PG_PORT="${PG_PORT:-15432}"
    if _has_cmd pg_isready && ! pg_isready -h "$PG_HOST" -p "$PG_PORT" -q 2>/dev/null; then
        _err "PostgreSQL 未就绪 ($PG_HOST:$PG_PORT)，后端将无法连接数据库"
        _info "请先启动 PostgreSQL: sudo systemctl start postgresql"
        _info "或设置环境变量 PG_HOST / PG_PORT 指向正确的数据库"
        return 1
    fi

    # --- Backend ---
    _info "启动 FastAPI 后端..."
    if [ -f "$LATENCY_DIR/.venv/bin/activate" ]; then
        source "$LATENCY_DIR/.venv/bin/activate"
    else
        _warn "Python venv 不存在，跳过后端启动"
        _info "请先运行完整部署: bash deploy/host/deploy.sh"
        return 1
    fi
    export WITTY_DIR="${WITTY_DIR:-/var/witty-ub}"
    export WITTY_INSTALL_PATH="${WITTY_INSTALL_PATH:-$BUILD_DIR/src}"
    export CONFIG="${CONFIG:-$PROJECT_DIR/config/diagnosis_config.toml}"
    export PYTHONPATH="$PROJECT_DIR/src/plugins${PYTHONPATH:+:$PYTHONPATH}"

    # 必须用 venv python：系统 python3 无 polars（T7 后是唯一解析路径），
    # 用系统 python 启动会导致解析任务 ModuleNotFoundError 重试耗尽失败。
    nohup "$LATENCY_DIR/.venv/bin/python" -u "$LATENCY_DIR/access/fastapi_server.py" \
        > "$LOG_DIR/backend.log" 2>&1 &
    local BACKEND_PID=$!
    echo "$BACKEND_PID" > "$LOG_DIR/backend.pid"

    # Wait for backend
    local BACKEND_OK=0
    for i in $(seq 1 30); do
        if curl -s http://127.0.0.1:9772/health_check 2>/dev/null | grep -q "ok"; then
            _log "后端已启动 (PID=$BACKEND_PID, port 9772)"
            BACKEND_OK=1
            break
        fi
        if [ $i -eq 30 ]; then
            _warn "后端启动超时，最近日志如下:"
            tail -20 "$LOG_DIR/backend.log" 2>/dev/null || true
        fi
        sleep 2
    done
    if [ "$BACKEND_OK" -ne 1 ]; then
        _err "后端启动失败(60 秒内健康检查未通过)。"
        _err "请检查 $LOG_DIR/backend.log 定位原因（最常见：PostgreSQL 密码/端口配置错误）。"
        return 1
    fi

    # --- Frontend (dev mode) ---
    if [ -d "$WEB_DIR" ]; then
        _check_node || _warn "Node 版本不满足要求，前端可能无法启动"
        _info "启动 Vite 前端 (开发模式)..."
        cd "$WEB_DIR"
        nohup ./node_modules/.bin/vite --host 0.0.0.0 --port 5173 \
            > "$LOG_DIR/frontend.log" 2>&1 &
        local FRONTEND_PID=$!
        echo "$FRONTEND_PID" > "$LOG_DIR/frontend.pid"
        cd "$PROJECT_DIR"

        sleep 3
        if curl -so /dev/null -w "%{http_code}" http://127.0.0.1:5173 2>/dev/null | grep -q 200; then
            _log "前端已启动 (PID=$FRONTEND_PID, port 5173)"
        else
            _warn "前端可能尚未就绪，等待 Vite 编译..."
        fi
    fi
}

stop_services() {
    _step_header "停止服务"

    _info "停止 FastAPI 后端..."
    [ -f "$LOG_DIR/backend.pid" ]  && kill "$(cat "$LOG_DIR/backend.pid")" 2>/dev/null || true
    _has_cmd fuser && fuser -k 9772/tcp 2>/dev/null || true

    _info "停止 Vite 前端..."
    [ -f "$LOG_DIR/frontend.pid" ] && kill "$(cat "$LOG_DIR/frontend.pid")" 2>/dev/null || true
    _has_cmd fuser && fuser -k 5173/tcp 2>/dev/null || true

    _log "所有服务已停止"
}

# ──────────────────── 清理 ────────────────────

# 检测环境是否已有部署痕迹: 端口占用 / PID 文件 / PG 已有数据。
# 返回 0=有残留, 1=干净。
detect_existing_deploy() {
    local found=0
    if _has_cmd fuser && { fuser -s 9772/tcp 2>/dev/null || fuser -s 5173/tcp 2>/dev/null; }; then
        _warn "检测到端口 9772/5173 已被占用(已有服务在运行)"
        found=1
    fi
    [ -f "$LOG_DIR/backend.pid" ] && { _warn "检测到 PID 文件: $LOG_DIR/backend.pid"; found=1; }
    [ -f "$LOG_DIR/frontend.pid" ] && { _warn "检测到 PID 文件: $LOG_DIR/frontend.pid"; found=1; }
    if _has_cmd psql && _psql -tAc "SELECT count(*) FROM log_knowledge" >/dev/null 2>&1 && \
        [ "$(_psql -tAc "SELECT count(*) FROM log_knowledge" 2>/dev/null | tr -d ' ')" != "0" ]; then
        _warn "检测到 PostgreSQL 中已有知识库数据"
        found=1
    fi
    [ "$found" = "1" ] && return 0
    return 1
}

# 一键清理: 停服务 + 清 PG 数据 + 清 /var/witty-ub 数据。
# 范围可交互选择: 1=服务+PG数据+var数据(默认)  2=再加 build/.venv/日志(彻底重装)
clean_all() {
    _step_header "一键清理"

    _info "清理前环境检测:"
    local found=0
    if _has_cmd fuser && { fuser -s 9772/tcp 2>/dev/null || fuser -s 5173/tcp 2>/dev/null; }; then
        echo "  - 端口 9772/5173 有服务运行"
        found=1
    fi
    if _has_cmd psql && _psql -c "" >/dev/null 2>&1; then
        local n
        n=$(_psql -tAc "SELECT count(*) FROM log_knowledge" 2>/dev/null | tr -d ' ')
        echo "  - PostgreSQL 数据库 witty-ub 存在 (知识库 $n 个)"
        found=1
    fi
    [ -d "$PROJECT_DIR/build" ] && echo "  - 构建产物: $PROJECT_DIR/build"
    [ -d "$PROJECT_DIR/src/plugins/latency/.venv" ] && echo "  - Python venv: $PROJECT_DIR/src/plugins/latency/.venv"
    [ -d "$LOG_DIR" ] && echo "  - 部署日志: $LOG_DIR"
    [ -d /var/witty-ub ] && echo "  - 运行数据: /var/witty-ub"
    [ "$found" = "0" ] && [ ! -d "$PROJECT_DIR/build" ] && [ ! -d "$PROJECT_DIR/src/plugins/latency/.venv" ] && {
        _log "环境已是干净的，无需清理"
        return 0
    }

    echo ""
    echo "请选择清理范围:"
    echo "  1) 停服务 + 清空 PostgreSQL 数据 + 清 /var/witty-ub (推荐, 保留构建产物/venv 可秒级重装)"
    echo "  2) 以上全部 + 删除 build/ + .venv/ + 部署日志 (彻底干净, 下次需重新编译/装依赖)"
    echo ""
    local scope
    read -r -p "请选择 [1-2, 默认 1]: " scope
    scope="${scope:-1}"
    case "$scope" in
        1|2) ;;
        *) _err "无效选择: $scope"; return 1 ;;
    esac

    echo ""
    _warn "即将执行:"
    [ "$scope" = "1" ] && echo "  - 停止前后端服务"
    [ "$scope" = "1" ] && echo "  - 清空 PostgreSQL 全部数据 (log_knowledge/log_file/task/聚合/明细/诊断 等所有表)"
    [ "$scope" = "1" ] && echo "  - 删除 /var/witty-ub 运行数据"
    [ "$scope" = "2" ] && echo "  - (范围2) 另删除 build/、.venv/、.deploy-logs/"
    echo ""
    if ! _confirm_clean "确认全部清理？此操作不可恢复"; then
        _log "已取消清理"
        return 0
    fi

    # 1. 停服务
    _info "停止服务..."
    stop_services >/dev/null 2>&1 || true

    # 2. 清 PG 数据(保留数据库本身, 只清数据)
    if _has_cmd psql && _psql -c "" >/dev/null 2>&1; then
        _info "清空 PostgreSQL 数据..."
        _psql -c "
            DO \$\$ DECLARE t text; BEGIN
                FOR t IN SELECT tablename FROM pg_tables WHERE schemaname='public' LOOP
                    EXECUTE format('TRUNCATE TABLE %I CASCADE', t);
                END LOOP;
            END \$\$;" 2>&1 | tail -2
        _log "PostgreSQL 数据已清空"
    else
        _warn "PostgreSQL 未连接，跳过清库 (检查 pg.conf 或 PG_HOST/PG_PORT 环境变量)"
    fi

    # 3. 清 /var/witty-ub
    if [ -d /var/witty-ub ]; then
        _info "删除 /var/witty-ub..."
        local SUDO=""; _is_root || SUDO="sudo"
        $SUDO rm -rf /var/witty-ub/data /var/witty-ub/config 2>/dev/null || true
        _log "/var/witty-ub 数据已删除"
    fi

    # 4. 范围2: 删构建/venv/日志
    if [ "$scope" = "2" ]; then
        _info "删除构建产物/venv/日志..."
        rm -rf "$PROJECT_DIR/build" "$PROJECT_DIR/src/plugins/latency/.venv" "$LOG_DIR" 2>/dev/null || true
        _log "build/、.venv/、.deploy-logs/ 已删除"
    fi

    _step_header "清理完成"
    _log "环境已清理。下次运行 bash deploy/host/deploy.sh 将全新部署。"
}

# ──────────────────── 入口 ────────────────────

show_banner() {
    echo "╔══════════════════════════════════════════════╗"
    echo "║         witty-ub 一键部署                    ║"
    echo "║  灵衢(UB)超节点故障智能诊断平台              ║"
    echo "╚══════════════════════════════════════════════╝"
    echo ""
}

show_access_info() {
    echo ""
    echo "╔══════════════════════════════════════════════╗"
    echo "║  部署完成！访问地址:                          ║"
    echo "║                                              ║"
    echo "║  前端:   http://localhost:5173               ║"
    if [ "$(hostname -I 2>/dev/null | awk '{print $1}')" != "" ]; then
        echo "║  前端:   http://$(hostname -I | awk '{print $1}'):5173        ║"
    fi
    echo "║  后端:   http://localhost:9772               ║"
    echo "║  健康:   http://localhost:9772/health_check   ║"
    echo "║                                              ║"
    echo "║  日志:   $LOG_DIR/                           ║"
    echo "╚══════════════════════════════════════════════╝"
    echo ""
}

main_deploy() {
    show_banner
    detect_os

    # 部署前检测: 若环境已有部署痕迹, 交互询问是否先清理再重装。
    if detect_existing_deploy; then
        echo ""
        _warn "检测到环境中已有 witty-ub 部署痕迹"
        echo ""
        if _confirm_clean "是否先清理旧环境再全新部署?(否则将直接叠加部署)"; then
            clean_all
            echo ""
            _info "旧环境已清理，开始全新部署..."
        else
            _info "保留现有环境，继续部署..."
        fi
    fi

    install_system_deps
    setup_postgresql
    install_python_deps
    build_cpp
    copy_data_files
    sync_pg_credentials
    start_services
    show_access_info
}

# ──────────────────── 参数解析 ────────────────────

case "${1:-deploy}" in
    --start|-s|start)
        detect_os
        start_services
        show_access_info
        ;;
    --stop|-x|stop)
        stop_services
        ;;
    --clean|-c|clean)
        show_banner
        detect_os
        clean_all
        ;;
    --help|-h|help)
        show_banner
        echo "用法: bash deploy/host/deploy.sh [选项]"
        echo ""
        echo "  (无参数)      完整部署（安装依赖 + 初始化 + 编译 + 启动）"
        echo "  --start / -s  仅启动服务"
        echo "  --stop  / -x  停止服务"
        echo "  --clean / -c  一键清理（交互选择范围: 服务+PG数据+var数据 / 或加 build+venv+日志）"
        echo "  --help  / -h  显示帮助"
        echo ""
        echo "相关脚本:"
        echo "  deploy/host/install_deps.sh  仅安装系统依赖 + Python 依赖"
        echo "  deploy/deploy_pg.sh          PostgreSQL 独立部署 (Docker/RPM/APT)"
        echo "  deploy/docker/deploy_witty.sh 容器一键部署"
        echo "  deploy/docker/manage.sh       容器运维管理"
        ;;
    *)
        main_deploy
        ;;
esac
