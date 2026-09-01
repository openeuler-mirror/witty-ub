#!/bin/bash
# Copyright (c) Huawei Technologies Co., Ltd. 2023-2026. All rights reserved.
# witty-ub is licensed under the Mulan PSL v2.
#
# witty-ub 宿主机/裸金属 一键部署脚本
# 支持 openEuler 24.03-LTS / Ubuntu 24.04 / WSL (Ubuntu)
#
# 用法:
#   bash deploy/host/deploy.sh          # 交互式菜单（默认）
#   bash deploy/host/deploy.sh --deploy # 直接完整部署（跳过菜单，首次运行）
#   bash deploy/host/deploy.sh --start  # 仅启动服务（已部署过）
#   bash deploy/host/deploy.sh --stop   # 停止所有服务
#   bash deploy/host/deploy.sh --clean  # 一键清理
#
# 前后端分离部署 (WITTY_ROLE=all|backend|frontend, 或 --role backend/frontend):
#   后端机: bash deploy/host/deploy.sh --deploy --role backend
#   前端机: WITTY_BACKEND_URL=http://<backend>:9772 \
#           bash deploy/host/deploy.sh --deploy --role frontend
#   前端机只跑 前端 + OpenCode(手动 deploy_opencode.sh), 不依赖 PostgreSQL/C++ 工具链。
#
# 访问:
#   前端: http://localhost:5173     (生产: vite preview 托管 dist/; 无 dist 时回退 dev server)
#   后端: http://localhost:9772
#   健康: http://localhost:9772/health_check
#
# 进程管理:
#   默认 systemd user units 托管 (witty-ub-backend / witty-ub-frontend),
#   机器重启 / 异常退出后自动拉起 (Restart=always)。
#   systemctl --user 不可用 (缺 systemd-pam / WSL / 容器) 时自动回退
#   nohup 裸进程 + PID 文件托管 (无崩溃自愈/开机自启)。
#   可用 DEPLOY_PM=systemd|nohup 强制指定托管方式 (测试/排障)。
#   开发前端时手动运行: cd src/web && npm run dev

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$(dirname "$SCRIPT_DIR")")"
LOG_DIR="$PROJECT_DIR/.deploy-logs"

# ──────────────────── 前后端分离部署角色 ────────────────────
# all: 单机全量 (默认, 行为与历史版本一致)
# backend: 仅 FastAPI 后端 + PostgreSQL + C++ 工具链 + 数据
# frontend: 仅前端 (nginx 静态托管 + 反代远端后端, 无 nginx 时回退 vite
#           preview) + OpenCode (Agent 随前端节点, 访问远端后端 9772)
WITTY_ROLE="${WITTY_ROLE:-all}"
WITTY_BACKEND_URL="${WITTY_BACKEND_URL:-http://127.0.0.1:9772}"
WITTY_API_BASE="${WITTY_API_BASE:-$WITTY_BACKEND_URL}"
WITTY_NO_PROXY="${WITTY_NO_PROXY:-127.0.0.1}"
WITTY_AGENT_URL="${WITTY_AGENT_URL:-http://127.0.0.1:4096}"
# export 供 envsubst / deploy_opencode.sh 等子进程读取
export WITTY_ROLE WITTY_BACKEND_URL WITTY_API_BASE WITTY_NO_PROXY WITTY_AGENT_URL
# 前端托管方式: start_services 中按 nginx 可用性置为 nginx, 默认 vite
WEB_MODE="vite"

# ──────────────────── 载入子脚本 ────────────────────

source "$SCRIPT_DIR/_lib.sh"
source "$SCRIPT_DIR/install_deps.sh"

# ──────────────────── PostgreSQL ────────────────────

setup_postgresql() {
    _step_header "初始化 PostgreSQL"

    _load_pg_credentials || true
    local PG_HOST="${PG_HOST:-127.0.0.1}"
    local PG_PORT="${PG_PORT:-5432}"

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
    local BRPC_DIAG_TOOL="$BUILD_DIR/src/witty-ub-brpc-diag"

    mkdir -p "$LOG_DIR"

    # 是否需要 (重新) 编译:
    #   1. FORCE_REBUILD_CPP=1          -> 强制重编
    #   2. 任一二进制缺失                -> 必然重编
    #   3. src/ 下源码 (*.cpp/*.cc/*.c/*.h/*.hpp) 或任一 CMakeLists.txt
    #      比两个二进制中较旧的那个新    -> 源码改过, 重编
    #   否则跳过编译 (避免改了 cpp 仍命中旧二进制)
    local NEED_REBUILD=0
    if [ "${FORCE_REBUILD_CPP:-0}" = "1" ]; then
        NEED_REBUILD=1
        _info "FORCE_REBUILD_CPP=1, 强制重新编译"
    elif [ ! -f "$DIAG_TOOL" ] || [ ! -f "$BRPC_DIAG_TOOL" ]; then
        NEED_REBUILD=1
        [ -f "$DIAG_TOOL" ]      || _info "缺少 $DIAG_TOOL, 需要编译"
        [ -f "$BRPC_DIAG_TOOL" ] || _info "缺少 $BRPC_DIAG_TOOL, 需要编译"
    else
        # 取两个二进制中较旧的那个作为 mtime 基准 (任一源码比它新就要重编)
        local REF_BIN
        if [ "$(stat -c %Y "$DIAG_TOOL" 2>/dev/null || echo 0)" \
             -le "$(stat -c %Y "$BRPC_DIAG_TOOL" 2>/dev/null || echo 0)" ]; then
            REF_BIN="$DIAG_TOOL"
        else
            REF_BIN="$BRPC_DIAG_TOOL"
        fi
        # find -newer 找到第一个匹配即 quit, 不全量遍历
        if find "$PROJECT_DIR/src" -type f \( -name '*.cpp' -o -name '*.cc' \
                 -o -name '*.c' -o -name '*.h' -o -name '*.hpp' \) \
                 -newer "$REF_BIN" -print -quit 2>/dev/null | grep -q . || \
           find "$PROJECT_DIR" -type f -name 'CMakeLists.txt' \
                 -not -path '*/build/*' -newer "$REF_BIN" -print -quit 2>/dev/null | grep -q .; then
            NEED_REBUILD=1
            _info "检测到 C++ 源码/CMakeLists.txt 比二进制新, 重新编译"
        fi
    fi

    if [ "$NEED_REBUILD" = "0" ]; then
        _log "C++ 诊断工具已存在且源码未改动, 跳过编译"
        return 0
    fi

    mkdir -p "$BUILD_DIR"
    cd "$BUILD_DIR"

    _info "CMake 配置..."
    cmake "$PROJECT_DIR" -DCMAKE_BUILD_TYPE=Release 2>&1 | tail -3

    _info "编译 witty-ub-diag-tool 和 witty-ub-brpc-diag (使用 $(nproc) 核)..."
    if ! make -j"$(nproc)" witty-ub-diag-tool witty-ub-brpc-diag 2>&1 | tee "$LOG_DIR/cpp-build.log"; then
        _err "C++ 编译失败，最近日志:"
        tail -30 "$LOG_DIR/cpp-build.log"
        return 1
    fi

    if [ ! -f "$DIAG_TOOL" ] || [ ! -f "$BRPC_DIAG_TOOL" ]; then
        _err "C++ 编译失败: 诊断工具产物不完整"
        [ -f "$DIAG_TOOL" ] || _err "  缺少 $DIAG_TOOL"
        [ -f "$BRPC_DIAG_TOOL" ] || _err "  缺少 $BRPC_DIAG_TOOL"
        _err "诊断功能将不可用。请检查 CMake/make 输出后再运行:"
        _err "  cmake $PROJECT_DIR -DCMAKE_BUILD_TYPE=Release && make -j\$(nproc) witty-ub-diag-tool witty-ub-brpc-diag"
        return 1
    fi

    chmod +x "$DIAG_TOOL" "$BRPC_DIAG_TOOL"
    _log "witty-ub-diag-tool 编译完成: $DIAG_TOOL"
    _log "witty-ub-brpc-diag 编译完成: $BRPC_DIAG_TOOL"

    cd "$PROJECT_DIR"
}

# ──────────────────── 前端编译 ────────────────────

build_frontend() {
    _step_header "编译前端 (可选)"

    local WEB_DIR="$PROJECT_DIR/src/web"
    [ -d "$WEB_DIR" ] || {
        _warn "前端目录不存在，跳过"
        return 0
    }

    mkdir -p "$LOG_DIR"

    cd "$WEB_DIR"
    _check_node || _warn "Node 版本不满足要求，前端编译可能失败"
    if ! npm ping --silent 2>/dev/null; then
        _warn "npm registry 不可达 (SSL 代理拦截?)"
        _info "已检测到 .npmrc 文件:"
        grep -H '^registry=' "$WEB_DIR/.npmrc" "$PROJECT_DIR/.npmrc" 2>/dev/null || true
        _info "可尝试: npm config set strict-ssl false"
    fi
    [ -d node_modules ] || npm install --silent 2>&1 | tee "$LOG_DIR/frontend-build.log" >/dev/null
    if ! npm run build-only 2>&1 | tee "$LOG_DIR/frontend-build.log"; then
        _warn "前端编译失败，最近日志:"
        tail -30 "$LOG_DIR/frontend-build.log"
        _warn "可先运行 npm run dev 启动开发模式"
    fi
    cd "$PROJECT_DIR"
    _log "前端编译完成: $WEB_DIR/dist/"
}

# ──────────────────── 数据文件 ────────────────────

copy_data_files() {
    _step_header "部署数据文件"

    local WITTY_DIR="/var/witty-ub"
    local SUDO=""
    _is_root || SUDO="sudo"

    $SUDO mkdir -p "$WITTY_DIR/data/kvcache" \
        "$WITTY_DIR/data/urma" \
        "$WITTY_DIR/data/ubsocket" \
        "$WITTY_DIR/data/umq" \
        "$WITTY_DIR/config" 2>/dev/null || true

    $SUDO cp "$PROJECT_DIR/data/failure_mode_tree.json" "$WITTY_DIR/data/" 2>/dev/null || true
    $SUDO cp "$PROJECT_DIR/data/kvcache/"*.json "$WITTY_DIR/data/kvcache/" 2>/dev/null || true
    $SUDO cp "$PROJECT_DIR/data/urma/"*.json "$WITTY_DIR/data/urma/" 2>/dev/null || true
    $SUDO cp "$PROJECT_DIR/data/ubsocket/"*.json "$WITTY_DIR/data/ubsocket/" 2>/dev/null || true
    $SUDO cp "$PROJECT_DIR/data/umq/"*.json "$WITTY_DIR/data/umq/" 2>/dev/null || true
    $SUDO cp "$PROJECT_DIR/config/diagnosis_config.toml" "$WITTY_DIR/config/" 2>/dev/null || true

    # Deploy witty_ub_diagnostician into .opencode directory
    # (OpenCode/Agent 随前端角色部署; backend 角色不跑 OpenCode, 跳过)
    if [ "$WITTY_ROLE" != "backend" ]; then
        $SUDO mkdir -p "$WITTY_DIR/witty_ub_diagnostician/.opencode" 2>/dev/null || true
        $SUDO cp -r "$PROJECT_DIR/witty_ub_diagnostician/"* "$WITTY_DIR/witty_ub_diagnostician/.opencode/" 2>/dev/null || true
        _log "Agent bundle 已部署（提示词保持原始占位符）"
    fi

    _log "数据文件已部署到 $WITTY_DIR"
}

# ──────────────────── PG 凭据同步 ────────────────────

sync_pg_credentials() {
    # 将 deploy/deploy.conf 中实际的 PG 凭据写入运行时配置。
    # 仓库中的 config/diagnosis_config.toml 是源码模板，启动/部署不得改写。
    if ! _load_pg_credentials; then
        _warn "deploy.conf 不存在，跳过凭据同步"
        return 0
    fi

    local PHOST P PORT PUSER PDB PPASS
    PHOST="$PG_HOST"
    PORT="$PG_PORT"
    PUSER="$PG_USER"
    PDB="$PG_DATABASE"
    PPASS="$PG_PASSWORD"

    [ -n "$PHOST" ] || PHOST="127.0.0.1"
    [ -n "$PORT" ] || PORT="5432"
    [ -n "$PUSER" ] || PUSER="witty-ub"
    [ -n "$PDB" ] || PDB="witty-ub"
    [ -n "$PPASS" ] || {
        _warn "pg.conf 未设置 PG_PASSWORD，跳过"
        return 0
    }

    local SUDO=""
    _is_root || SUDO="sudo"
    local RUNTIME_WITTY_DIR="${WITTY_DIR:-/var/witty-ub}"
    local CONF="$RUNTIME_WITTY_DIR/config/diagnosis_config.toml"
    [ -f "$CONF" ] || {
        _warn "运行时配置不存在，跳过凭据同步: $CONF"
        return 0
    }
    $SUDO sed -i \
        -e "s|^pg_host = .*|pg_host = \"$PHOST\"|" \
        -e "s|^pg_port = .*|pg_port = $PORT|" \
        -e "s|^pg_database = .*|pg_database = \"$PDB\"|" \
        -e "s|^pg_user = .*|pg_user = \"$PUSER\"|" \
        -e "s|^pg_password = .*|pg_password = \"$PPASS\"|" \
        "$CONF"
    _log "已同步 PG 凭据到运行时配置 $CONF (host=$PHOST port=$PORT db=$PDB user=$PUSER)"
}

prepare_runtime_diagnosis_config() {
    # “仅启动服务”也必须使用独立运行时副本，避免把部署参数写回源码。
    local RUNTIME_WITTY_DIR="${WITTY_DIR:-/var/witty-ub}"
    local SOURCE_CONF="$PROJECT_DIR/config/diagnosis_config.toml"
    local RUNTIME_CONF="$RUNTIME_WITTY_DIR/config/diagnosis_config.toml"
    local SUDO=""
    _is_root || SUDO="sudo"

    if [ ! -f "$RUNTIME_CONF" ]; then
        [ -f "$SOURCE_CONF" ] || {
            _err "源配置不存在: $SOURCE_CONF"
            return 1
        }
        $SUDO mkdir -p "$RUNTIME_WITTY_DIR/config"
        $SUDO cp "$SOURCE_CONF" "$RUNTIME_CONF"
        _log "已创建运行时配置: $RUNTIME_CONF"
    fi
    sync_pg_credentials
}

# ──────────────────── systemd user units ────────────────────

# systemctl --user 是否可用。user 会话强依赖 pam_systemd.so
# (openEuler 24.03+ 拆到独立包 systemd-pam), 缺失时 user@0.service PAM
# 加载失败 → /run/user/<UID> 不建 → systemctl --user 全部失败。
systemd_user_available() {
    command -v systemctl >/dev/null 2>&1 || return 1
    systemctl --user daemon-reload >/dev/null 2>&1
}

# 从 deploy/host/systemd/*.service 模板生成 user units 并安装到
# ~/.config/systemd/user/ (路径占位符 __PROJECT_DIR__ / __WITTY_DIR__
# 替换为实际路径)。幂等: 每次 start 前调用, 保证 units 存在且与
# deploy.sh 的运行时语义 (WITTY_DIR/CONFIG/WITTY_INSTALL_PATH) 一致。
# systemd 不可用时返回 1 (调用方决定是否回退 nohup)。
install_systemd_units() {
    _step_header "安装 systemd user units"

    local UNIT_SRC="$SCRIPT_DIR/systemd"
    local UNIT_DIR="${XDG_CONFIG_HOME:-$HOME/.config}/systemd/user"
    local SYS_WITTY_DIR="${WITTY_DIR:-/var/witty-ub}"

    [ -d "$UNIT_SRC" ] || {
        _warn "systemd 模板目录缺失: $UNIT_SRC"
        return 1
    }
    mkdir -p "$UNIT_DIR"

    # 按角色安装 units: frontend 角色的 web/OpenCode 为裸进程托管,
    # 不安装 vite frontend unit; backend 角色不需要 frontend unit。
    local UNITS=()
    if [ "$WITTY_ROLE" != "frontend" ]; then
        sed -e "s|__PROJECT_DIR__|$PROJECT_DIR|g" \
            -e "s|__WITTY_DIR__|$SYS_WITTY_DIR|g" \
            "$UNIT_SRC/witty-ub-backend.service" >"$UNIT_DIR/witty-ub-backend.service"
        UNITS+=(witty-ub-backend.service)
    fi
    if [ "$WITTY_ROLE" != "backend" ]; then
        sed -e "s|__PROJECT_DIR__|$PROJECT_DIR|g" \
            "$UNIT_SRC/witty-ub-frontend.service" >"$UNIT_DIR/witty-ub-frontend.service"
        UNITS+=(witty-ub-frontend.service)
    fi

    if ! systemd_user_available; then
        _warn "systemctl --user 不可用 (缺 pam_systemd.so / 无 systemd user 会话?)"
        _warn "openEuler 24.03+ 修复: sudo dnf install -y systemd-pam; 或 loginctl enable-linger $USER"
        return 1
    fi
    systemctl --user enable "${UNITS[@]}" >/dev/null 2>&1 || true
    _log "systemd user units 已安装并启用 (${UNITS[*]})"
}

# ──────────────────── frontend 角色: Web + OpenCode ────────────────────

render_web_nginx() {
    # 渲染统一 nginx 模板: 静态托管 dist/ + 反代远端后端/本机 OpenCode。
    # envsubst 优先 (gettext), 缺失时 sed 兜底, 不强依赖新包。
    if command -v envsubst >/dev/null 2>&1; then
        envsubst '${WITTY_BACKEND_URL} ${WITTY_AGENT_URL}' \
            <"$PROJECT_DIR/packaging/nginx/witty-ub-web.conf.template"
    else
        sed -e "s|\${WITTY_BACKEND_URL}|$WITTY_BACKEND_URL|g" \
            -e "s|\${WITTY_AGENT_URL}|$WITTY_AGENT_URL|g" \
            "$PROJECT_DIR/packaging/nginx/witty-ub-web.conf.template"
    fi | sed \
        -e "s|pid /run/witty-ub-web/nginx.pid;|pid $PROJECT_DIR/.deploy-run/nginx.pid;|" \
        -e "s|error_log /var/log/witty-ub-web/error.log warn;|error_log $LOG_DIR/web-error.log warn;|" \
        -e "s|access_log /var/log/witty-ub-web/access.log;|access_log $LOG_DIR/web-access.log;|"
}

start_frontend_node() {
    local DIST_DIR="$PROJECT_DIR/src/web/dist"
    local SUDO=""
    _is_root || SUDO="sudo"

    # --- Web: nginx 静态托管 + 反代 (需 dist 构建产物), 否则回退 vite preview ---
    if [ -d "$DIST_DIR" ] && [ -n "$(ls -A "$DIST_DIR" 2>/dev/null)" ] && _has_cmd nginx; then
        WEB_MODE="nginx"
        _info "启动 Web (nginx 静态托管 dist/ + 反代, port 8080)..."
        # 清理本项目旧 nginx / 旧 vite 实例
        [ -f "$PROJECT_DIR/.deploy-run/nginx.pid" ] && $SUDO kill "$($SUDO cat "$PROJECT_DIR/.deploy-run/nginx.pid")" 2>/dev/null || true
        _has_cmd fuser && fuser -k 8080/tcp 5173/tcp 2>/dev/null || true
        sleep 1
        mkdir -p "$PROJECT_DIR/.deploy-run" "$LOG_DIR"
        # 发布 dist 到 /var/witty-ub/web: nginx worker(非特权用户)无法
        # 穿透用户 home 目录(750), 不能直接托管 ~/src/web/dist。
        $SUDO mkdir -p /var/witty-ub
        $SUDO rm -rf /var/witty-ub/web
        $SUDO cp -r "$DIST_DIR" /var/witty-ub/web
        $SUDO chmod -R a+rX /var/witty-ub/web
        render_web_nginx >"$PROJECT_DIR/.deploy-run/nginx.conf"
        $SUDO nginx -c "$PROJECT_DIR/.deploy-run/nginx.conf"
        sleep 1
        if curl --noproxy '*' -so /dev/null -w "%{http_code}" http://127.0.0.1:8080 2>/dev/null | grep -q 200; then
            _log "Web 已启动 (nginx, port 8080, backend=$WITTY_BACKEND_URL)"
        else
            _err "nginx 启动失败, 查看 $LOG_DIR/web-error.log"
            return 1
        fi
    else
        WEB_MODE="vite"
        _warn "nginx 或 dist/ 不可用, 回退 vite preview 反代 (port 5173)"
        _check_node || _warn "Node 版本不满足要求，前端可能无法启动"
        export VITE_DEV_API_TARGET="$WITTY_BACKEND_URL"
        nohup bash "$SCRIPT_DIR/run_frontend.sh" >"$LOG_DIR/frontend.log" 2>&1 &
        echo $! >"$LOG_DIR/frontend.pid"
        sleep 3
        if curl --noproxy 127.0.0.1 -so /dev/null -w "%{http_code}" http://127.0.0.1:5173 2>/dev/null | grep -q 200; then
            _log "Web 已启动 (vite preview, port 5173, backend=$WITTY_BACKEND_URL)"
        else
            _warn "前端可能尚未就绪，等待 Vite 编译..."
        fi
    fi

    # --- OpenCode: Agent 随前端节点, 经 WITTY_API_BASE 访问(远端)后端 ---
    _info "启动 OpenCode (Agent 后端基址: $WITTY_API_BASE)..."
    if ! WITTY_API_BASE="$WITTY_API_BASE" \
        WITTY_NO_PROXY="$WITTY_NO_PROXY" \
        OPENCODE_HOST="${OPENCODE_HOST:-127.0.0.1}" \
        bash "$PROJECT_DIR/deploy/deploy_opencode.sh"; then
        _warn "OpenCode 启动失败 (Agent 诊断不可用, Web 页面不受影响)"
        _info "排查: bash deploy/deploy_opencode.sh"
    fi
}

# ──────────────────── 启动服务 ────────────────────

start_services() {
    _step_header "启动服务"

    local LATENCY_DIR="$PROJECT_DIR/src/plugins/latency"
    local WEB_DIR="$PROJECT_DIR/src/web"

    mkdir -p "$LOG_DIR"

    if [ "$WITTY_ROLE" != "frontend" ]; then
        prepare_runtime_diagnosis_config
    fi

    # --- 选择进程托管方式 ---
    # 默认 auto: systemd user units 优先 (崩溃自愈/开机自启);
    # systemctl --user 不可用 (缺 systemd-pam / WSL / 容器) 时回退 nohup 裸进程。
    # DEPLOY_PM=systemd|nohup 可强制指定 (测试/排障)。
    local USE_SYSTEMD=0
    case "${DEPLOY_PM:-auto}" in
    systemd)
        if systemd_user_available; then
            USE_SYSTEMD=1
        else
            _err "DEPLOY_PM=systemd 但 systemctl --user 不可用"
            return 1
        fi
        ;;
    nohup)
        USE_SYSTEMD=0
        _warn "DEPLOY_PM=nohup 强制使用裸进程托管"
        ;;
    *)
        if install_systemd_units; then
            USE_SYSTEMD=1
            _log "进程托管: systemd user units (崩溃自愈/开机自启)"
        else
            _warn "进程托管: 回退 nohup 裸进程 + PID 文件 (无崩溃自愈/开机自启)"
            _info "恢复 systemd 托管: openEuler 24.03+ 执行 sudo dnf install -y systemd-pam 后重跑"
        fi
        ;;
    esac

    # --- 清理旧进程 (PID 文件 + 精确端口) ---
    # 只杀本项目的旧进程, 不用宽泛 pkill 以免误杀他项目同名进程。
    # systemd 托管时仅当 unit 非活跃才清, 避免误杀 systemd 正在管理的进程。
    if [ "$USE_SYSTEMD" = "1" ]; then
        if ! systemctl --user is-active --quiet witty-ub-backend.service 2>/dev/null; then
            [ -f "$LOG_DIR/backend.pid" ] && kill "$(cat "$LOG_DIR/backend.pid")" 2>/dev/null || true
            _has_cmd fuser && fuser -k 9772/tcp 2>/dev/null || true
        fi
        if ! systemctl --user is-active --quiet witty-ub-frontend.service 2>/dev/null; then
            [ -f "$LOG_DIR/frontend.pid" ] && kill "$(cat "$LOG_DIR/frontend.pid")" 2>/dev/null || true
            _has_cmd fuser && fuser -k 5173/tcp 2>/dev/null || true
        fi
    else
        [ -f "$LOG_DIR/backend.pid" ] && kill "$(cat "$LOG_DIR/backend.pid")" 2>/dev/null || true
        [ -f "$LOG_DIR/frontend.pid" ] && kill "$(cat "$LOG_DIR/frontend.pid")" 2>/dev/null || true
        _has_cmd fuser && {
            fuser -k 9772/tcp 2>/dev/null || true
            fuser -k 5173/tcp 2>/dev/null || true
        }
    fi
    sleep 1

    # --- frontend 角色: 探测远端后端 (不阻塞, 后端可能稍后就绪) ---
    if [ "$WITTY_ROLE" = "frontend" ]; then
        local BE_OK=0
        for i in $(seq 1 15); do
            if curl -s --max-time 3 --noproxy '*' "$WITTY_BACKEND_URL/health_check" 2>/dev/null | grep -q "ok"; then
                _log "远端后端就绪: $WITTY_BACKEND_URL"
                BE_OK=1
                break
            fi
            sleep 2
        done
        [ "$BE_OK" = "1" ] || _warn "远端后端 $WITTY_BACKEND_URL 暂不可达, 前端仍将启动 (API 请求将失败)"
    else
        # --- Verify PostgreSQL is reachable ---
        local PG_HOST="${PG_HOST:-127.0.0.1}"
        local PG_PORT="${PG_PORT:-5432}"
        if _has_cmd pg_isready && ! pg_isready -h "$PG_HOST" -p "$PG_PORT" -q 2>/dev/null; then
            _err "PostgreSQL 未就绪 ($PG_HOST:$PG_PORT)，后端将无法连接数据库"
            _info "请先启动 PostgreSQL: sudo systemctl start postgresql"
            _info "或设置环境变量 PG_HOST / PG_PORT_RPM 指向正确的数据库"
            return 1
        fi
    fi

    # --- Backend (frontend 角色跳过, 后端在远端机器上) ---
    if [ "$WITTY_ROLE" != "frontend" ]; then
        if [ ! -f "$LATENCY_DIR/.venv/bin/python" ]; then
            _warn "Python venv 不存在，跳过后端启动"
            _info "请先运行完整部署: bash deploy/host/deploy.sh"
            return 1
        fi
        if [ "$USE_SYSTEMD" = "1" ]; then
            _info "启动 FastAPI 后端 (systemd user unit)..."
            systemctl --user start witty-ub-backend.service || {
                _err "后端 unit 启动失败"
                return 1
            }
        else
            _info "启动 FastAPI 后端 (nohup 裸进程)..."
            # 环境与 systemd unit 对齐 (PYTHONPATH/WITTY_DIR/WITTY_INSTALL_PATH/CONFIG)。
            # 必须用 venv python: 系统 python3 无 polars, 解析任务会 ModuleNotFoundError。
            export WITTY_DIR="${WITTY_DIR:-/var/witty-ub}"
            export WITTY_INSTALL_PATH="${WITTY_INSTALL_PATH:-$PROJECT_DIR/build/src}"
            export CONFIG="${CONFIG:-$WITTY_DIR/config/diagnosis_config.toml}"
            export PYTHONPATH="$PROJECT_DIR/src/plugins${PYTHONPATH:+:$PYTHONPATH}"
            nohup "$LATENCY_DIR/.venv/bin/python" -u "$LATENCY_DIR/access/fastapi_server.py" \
                >"$LOG_DIR/backend.log" 2>&1 &
            echo $! >"$LOG_DIR/backend.pid"
        fi

        # Wait for backend
        local BACKEND_OK=0
        for i in $(seq 1 30); do
            if curl --noproxy 127.0.0.1 -s http://127.0.0.1:9772/health_check 2>/dev/null | grep -q "ok"; then
                _log "后端已启动 (${USE_SYSTEMD:+unit=witty-ub-backend, }port 9772)"
                BACKEND_OK=1
                break
            fi
            if [ $i -eq 30 ]; then
                _warn "后端启动超时，最近日志如下:"
                journalctl --user -u witty-ub-backend.service -n 20 --no-pager 2>/dev/null || tail -20 "$LOG_DIR/backend.log" 2>/dev/null || true
            fi
            sleep 2
        done
        if [ "$BACKEND_OK" -ne 1 ]; then
            _err "后端启动失败(60 秒内健康检查未通过)。"
            _err "请检查 journalctl --user -u witty-ub-backend.service 或 $LOG_DIR/backend.log 定位原因（最常见：PostgreSQL 密码/端口配置错误）。"
            return 1
        fi
    fi

    # --- Frontend (backend 角色跳过) ---
    if [ "$WITTY_ROLE" = "frontend" ]; then
        # frontend 角色: nginx 静态托管 + 反代远端后端 + OpenCode (裸进程)
        start_frontend_node
    elif [ "$WITTY_ROLE" != "backend" ] && [ -d "$WEB_DIR" ]; then
        _check_node || _warn "Node 版本不满足要求，前端可能无法启动"
        if [ "$USE_SYSTEMD" = "1" ]; then
            _info "启动前端 (systemd user unit, vite preview 托管 dist/)..."
            systemctl --user start witty-ub-frontend.service || {
                _err "前端 unit 启动失败"
                return 1
            }
        else
            _info "启动前端 (nohup 裸进程, vite preview 托管 dist/)..."
            nohup bash "$SCRIPT_DIR/run_frontend.sh" >"$LOG_DIR/frontend.log" 2>&1 &
            echo $! >"$LOG_DIR/frontend.pid"
        fi

        sleep 3
        if curl --noproxy 127.0.0.1 -so /dev/null -w "%{http_code}" http://127.0.0.1:5173 2>/dev/null | grep -q 200; then
            _log "前端已启动 (${USE_SYSTEMD:+unit=witty-ub-frontend, }port 5173)"
        else
            _warn "前端可能尚未就绪，等待 Vite 编译..."
        fi
    fi
}

stop_services() {
    _step_header "停止服务"

    _info "停止 FastAPI 后端..."
    systemctl --user stop witty-ub-backend.service 2>/dev/null || true
    _info "停止 Vite 前端..."
    systemctl --user stop witty-ub-frontend.service 2>/dev/null || true

    # 停止 frontend 角色的 nginx (本项目实例, pid 文件存在才动)
    local SUDO=""
    _is_root || SUDO="sudo"
    if [ -f "$PROJECT_DIR/.deploy-run/nginx.pid" ]; then
        _info "停止 Web nginx..."
        $SUDO kill "$($SUDO cat "$PROJECT_DIR/.deploy-run/nginx.pid")" 2>/dev/null || true
    fi
    # 停止 OpenCode 裸进程 (frontend 角色)
    _has_cmd fuser && fuser -k 4096/tcp 2>/dev/null || true

    # 清理残留 nohup 孤儿进程 (历史部署方式遗留)
    [ -f "$LOG_DIR/backend.pid" ] && kill "$(cat "$LOG_DIR/backend.pid")" 2>/dev/null || true
    [ -f "$LOG_DIR/frontend.pid" ] && kill "$(cat "$LOG_DIR/frontend.pid")" 2>/dev/null || true
    _has_cmd fuser && {
        fuser -k 9772/tcp 2>/dev/null || true
        fuser -k 5173/tcp 2>/dev/null || true
    }

    _log "所有服务已停止"
}

# ──────────────────── Agent 服务 ────────────────────

# 启动 Agent 服务 (OpenCode): 跑 deploy/deploy_opencode.sh, 脚本内自带
# 健康检查、pidfile (${WITTY_ROOT}/opencode.pid) 写入、已运行早退逻辑。
start_agent() {
    if [ "$WITTY_ROLE" = "backend" ]; then
        _err "当前是后端节点（角色: backend），Agent 服务运行在前端节点"
        return 1
    fi
    _step_header "启动 Agent 服务 (OpenCode)"
    local agent_script="$PROJECT_DIR/deploy/deploy_opencode.sh"
    if [[ ! -f "$agent_script" ]]; then
        _err "未找到 Agent 启动脚本: $agent_script"
        return 1
    fi
    _info "Agent 后端基址: ${WITTY_API_BASE:-http://127.0.0.1:9772}"
    WITTY_API_BASE="${WITTY_API_BASE}" \
        WITTY_NO_PROXY="${WITTY_NO_PROXY}" \
        OPENCODE_HOST="${OPENCODE_HOST:-127.0.0.1}" \
        bash "$agent_script" || {
            _warn "Agent 服务启动失败 (查看 $PROJECT_DIR/opencode_server.log)"
            return 1
        }
}

# 停止 Agent 服务: 优先读 ${WITTY_ROOT}/opencode.pid (启动脚本写入),
# pidfile 缺失/失效时按端口 4096 兜底 kill。
stop_agent() {
    if [ "$WITTY_ROLE" = "backend" ]; then
        _err "当前是后端节点（角色: backend），Agent 服务运行在前端节点"
        return 1
    fi
    _step_header "停止 Agent 服务 (OpenCode)"
    local pidfile="$PROJECT_DIR/opencode.pid"
    local pid=""
    if [[ -f "$pidfile" ]]; then
        pid="$(cat "$pidfile" 2>/dev/null || true)"
    fi

    if [[ -n "$pid" ]] && kill -0 "$pid" 2>/dev/null; then
        kill "$pid" 2>/dev/null || true
        # 等待最多 5s 让进程优雅退出
        local i
        for i in $(seq 1 10); do
            kill -0 "$pid" 2>/dev/null || break
            sleep 0.5
        done
        # 仍在运行则强杀
        if kill -0 "$pid" 2>/dev/null; then
            _warn "进程未响应 SIGTERM, 发送 SIGKILL"
            kill -9 "$pid" 2>/dev/null || true
        fi
        _log "已停止 Agent (PID: $pid)"
    else
        _info "pidfile 缺失或 PID 已不存活, 按端口兜底"
    fi

    # 端口兜底 (pidfile 缺失/失效, 或残留的孤儿进程)
    _has_cmd fuser && fuser -k 4096/tcp 2>/dev/null || true

    # 清理 pidfile
    rm -f "$pidfile"
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
    [ -f "$LOG_DIR/backend.pid" ] && {
        _warn "检测到 PID 文件: $LOG_DIR/backend.pid"
        found=1
    }
    [ -f "$LOG_DIR/frontend.pid" ] && {
        _warn "检测到 PID 文件: $LOG_DIR/frontend.pid"
        found=1
    }
    if _has_cmd psql && _psql -tAc "SELECT count(*) FROM log_knowledge" >/dev/null 2>&1 &&
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
    # CLEAN_SCOPE 环境变量 (CI/自动化测试) 优先, 跳过交互;
    # NONINTERACTIVE=1 时默认 scope=1 (保留构建产物, 可秒级重装)。
    if [ -n "${CLEAN_SCOPE:-}" ]; then
        scope="$CLEAN_SCOPE"
    elif [ "${NONINTERACTIVE:-0}" = "1" ]; then
        scope=1
    else
        read -r -p "请选择 [1-2, 默认 1]: " scope
        scope="${scope:-1}"
    fi
    case "$scope" in
    1 | 2) ;;
    *)
        _err "无效选择: $scope"
        return 1
        ;;
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
        _warn "PostgreSQL 未连接，跳过清库 (检查 deploy.conf 或 PG_HOST/PG_PORT_RPM 环境变量)"
    fi

    # 3. 清 /var/witty-ub
    if [ -d /var/witty-ub ]; then
        _info "删除 /var/witty-ub..."
        local SUDO=""
        _is_root || SUDO="sudo"
        $SUDO rm -rf \
            /var/witty-ub/data \
            /var/witty-ub/config \
            /var/witty-ub/witty_ub_diagnostician \
            /var/witty-ub/cache 2>/dev/null || true
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
    case "$WITTY_ROLE" in
    backend)
        echo "║  角色:   backend (仅后端)                    ║"
        echo "║  后端:   http://0.0.0.0:9772                 ║"
        echo "║  健康:   http://localhost:9772/health_check   ║"
        ;;
    frontend)
        echo "║  角色:   frontend (仅前端)                   ║"
        if [ "$WEB_MODE" = "nginx" ]; then
            echo "║  前端:   http://localhost:8080 (nginx)       ║"
            if [ "$(hostname -I 2>/dev/null | awk '{print $1}')" != "" ]; then
                echo "║  前端:   http://$(hostname -I | awk '{print $1}'):8080        ║"
            fi
        else
            echo "║  前端:   http://localhost:5173 (vite preview) ║"
            if [ "$(hostname -I 2>/dev/null | awk '{print $1}')" != "" ]; then
                echo "║  前端:   http://$(hostname -I | awk '{print $1}'):5173        ║"
            fi
        fi
        echo "║  后端:   $WITTY_BACKEND_URL (远端)"
        echo "║  Agent:  http://localhost:4096 → $WITTY_API_BASE"
        ;;
    *)
        echo "║  前端:   http://localhost:5173               ║"
        if [ "$(hostname -I 2>/dev/null | awk '{print $1}')" != "" ]; then
            echo "║  前端:   http://$(hostname -I | awk '{print $1}'):5173        ║"
        fi
        echo "║  后端:   http://localhost:9772               ║"
        echo "║  健康:   http://localhost:9772/health_check   ║"
        ;;
    esac
    echo "║                                              ║"
    echo "║  日志:   $LOG_DIR/                           ║"
    echo "╚══════════════════════════════════════════════╝"
    echo ""
}

main_deploy() {
    show_banner
    detect_os

    if [ "$WITTY_ROLE" != "all" ]; then
        _log "前后端分离部署, 角色: $WITTY_ROLE (backend=$WITTY_BACKEND_URL)"
    fi

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
    if [ "$WITTY_ROLE" != "frontend" ]; then
        setup_postgresql
        install_python_deps
    fi
    if [ "$WITTY_ROLE" != "backend" ]; then
        build_frontend
    fi
    if [ "$WITTY_ROLE" != "frontend" ]; then
        build_cpp
    fi
    copy_data_files
    start_services
    show_access_info
}

# ──────────────────── 交互式菜单 ────────────────────

# 与 deploy/docker/manage.sh 的交互式菜单风格一致, 选项映射到
# deploy.sh 现有的子命令。命令行模式 (--start/--stop/--clean) 不受影响。
show_menu() {
    echo ""
    echo "========================================"
    echo "  witty-ub 宿主机部署管理器"
    echo "========================================"
    echo ""
    echo "  📦  安装"
    echo "    1) 完整部署（依赖 + PostgreSQL + 编译 + 启动）"
    echo "    2) 仅安装依赖"
    echo ""
    echo "  🔧  管理"
    echo "    3) 仅启动服务（已部署过）"
    echo "    4) 停止所有服务"
    echo ""
    if [ "$WITTY_ROLE" != "backend" ]; then
        echo "  🤖  Agent 服务"
        echo "    5) 启动 Agent 服务（OpenCode）"
        echo "    6) 停止 Agent 服务"
        echo ""
    fi
    echo "  🗑️  清理"
    echo "    7) 一键清理（交互选择范围）"
    echo ""
    echo "    0) 退出"
    echo ""
    echo "========================================"
}

menu_main() {
    show_banner
    detect_os
    # NONINTERACTIVE=1 (CI/自动化测试) 时跳过菜单, 直接完整部署。
    if [ "${NONINTERACTIVE:-0}" = "1" ]; then
        main_deploy
        return 0
    fi
    while true; do
        show_menu
        if [ "$WITTY_ROLE" != "backend" ]; then
            read -r -p "请选择操作 [0-7]: " choice
        else
            read -r -p "请选择操作 [0-4,7]: " choice
        fi
        echo ""
        case "$choice" in
        1) main_deploy ;;
        2) install_deps ;;
        3)
            start_services
            show_access_info
            ;;
        4) stop_services ;;
        5) start_agent ;;
        6) stop_agent ;;
        7) clean_all ;;
        0)
            echo "再见！"
            exit 0
            ;;
        *)
            _err "无效选项，请重新选择"
            ;;
        esac
        echo ""
        read -r -p "按回车继续..." _
    done
}

# ──────────────────── 参数解析 ────────────────────

# 先提取 --role <role> / --role=<role> (剩余参数原样传给子命令 case)
ROLE_ARGS=()
while [ $# -gt 0 ]; do
    case "$1" in
    --role)
        [ $# -ge 2 ] || {
            echo "错误: --role 需要参数 (all|backend|frontend)"
            exit 1
        }
        WITTY_ROLE="$2"
        shift 2
        ;;
    --role=*)
        WITTY_ROLE="${1#--role=}"
        shift
        ;;
    *)
        ROLE_ARGS+=("$1")
        shift
        ;;
    esac
done
set -- ${ROLE_ARGS[@]+"${ROLE_ARGS[@]}"}

case "$WITTY_ROLE" in
all | backend | frontend) ;;
*)
    echo "错误: 无效角色 '$WITTY_ROLE' (可选: all|backend|frontend)"
    exit 1
    ;;
esac

case "${1:-menu}" in
--start | -s | start)
    detect_os
    start_services
    show_access_info
    ;;
--stop | -x | stop)
    stop_services
    ;;
--clean | -c | clean)
    show_banner
    detect_os
    clean_all
    ;;
--deploy | deploy)
    main_deploy
    ;;
--menu | -m | menu)
    menu_main
    ;;
--help | -h | help)
    show_banner
    echo "用法: bash deploy/host/deploy.sh [选项]"
    echo ""
    echo "  (无参数)      交互式菜单（选择部署 / 启动 / 停止 / 清理）"
    echo "  --deploy      直接完整部署（跳过菜单，同 NONINTERACTIVE=1）"
    echo "  --start / -s  仅启动服务"
    echo "  --stop  / -x  停止服务"
    echo "  --clean / -c  一键清理（交互选择范围: 服务+PG数据+var数据 / 或加 build+venv+日志）"
    echo "  --help  / -h  显示帮助"
    echo ""
    echo "前后端分离部署:"
    echo "  --role all|backend|frontend   部署角色（默认 all, 也可用环境变量 WITTY_ROLE）"
    echo "  WITTY_BACKEND_URL=http://<backend>:9772  frontend 角色指向的远端后端"
    echo "  示例(后端机): bash deploy/host/deploy.sh --deploy --role backend"
    echo "  示例(前端机): WITTY_BACKEND_URL=http://be:9772 bash deploy/host/deploy.sh --deploy --role frontend"
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
