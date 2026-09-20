#!/bin/bash
# Copyright (c) Huawei Technologies Co., Ltd. 2023-2026. All rights reserved.
# witty-ub is licensed under the Mulan PSL v2.
#
# witty-ub 部署共享工具库
# 被 deploy.sh / install_deps.sh / deploy_backend.sh / deploy_frontend.sh 共同 source。
# 提供色彩、日志、OS 检测、PG 凭据加载、psql 封装等通用函数。
#
# 不要直接执行此脚本。

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$(dirname "$SCRIPT_DIR")")"
LOG_DIR="$PROJECT_DIR/.deploy-logs"

# ──────────────────── 色彩 ────────────────────

_COLOR_RESET='\033[0m'
_COLOR_GREEN='\033[0;32m'
_COLOR_YELLOW='\033[1;33m'
_COLOR_RED='\033[0;31m'
_COLOR_BLUE='\033[0;34m'

# ──────────────────── 日志 ────────────────────

_log()  { echo -e "${_COLOR_GREEN}[witty-ub]${_COLOR_RESET} $*"; }
_warn() { echo -e "${_COLOR_YELLOW}[warn]${_COLOR_RESET}    $*"; }
_err()  { echo -e "${_COLOR_RED}[error]${_COLOR_RESET}   $*"; }
_info() { echo -e "${_COLOR_BLUE}[info]${_COLOR_RESET}    $*"; }
_step_header() { echo ""; echo -e "${_COLOR_GREEN}═══ $* ═══${_COLOR_RESET}"; }

# ──────────────────── 工具 ────────────────────

_has_cmd() { command -v "$1" &>/dev/null; }
_is_root() { [ "$(id -u)" -eq 0 ]; }

# 最低 Node 版本与 src/web/package.json 的 engines.node 一致。
_NODE_MIN_MAJOR=20
_NODE_MIN_MINOR=18
_NODE_MIN_PATCH=2

_check_node() {
    if ! _has_cmd node; then
        _warn "未检测到 Node.js，前端将无法启动"
        _info "安装指引: https://nodejs.org (推荐 22.x LTS)"
        return 1
    fi
    local VER
    VER="$(node --version 2>/dev/null | sed 's/^v//')" || true
    if [ -z "$VER" ]; then
        _warn "无法解析 Node 版本"
        return 1
    fi
    local MAJOR MINOR PATCH
    MAJOR="$(echo "$VER" | cut -d. -f1)"
    MINOR="$(echo "$VER" | cut -d. -f2)"
    PATCH="$(echo "$VER" | cut -d. -f3 | tr -dc '0-9')"
    [ -n "$PATCH" ] || PATCH=0
    if [ "$MAJOR" -gt "$_NODE_MIN_MAJOR" ] || \
       { [ "$MAJOR" -eq "$_NODE_MIN_MAJOR" ] && [ "$MINOR" -gt "$_NODE_MIN_MINOR" ]; } || \
       { [ "$MAJOR" -eq "$_NODE_MIN_MAJOR" ] && [ "$MINOR" -eq "$_NODE_MIN_MINOR" ] && \
         [ "$PATCH" -ge "$_NODE_MIN_PATCH" ]; }; then
        _info "Node.js v$VER ✓"
        return 0
    fi
    _warn "Node.js v$VER 太旧，前端需要 ≥ v${_NODE_MIN_MAJOR}.${_NODE_MIN_MINOR}.${_NODE_MIN_PATCH}"
    _info "安装 Node 22.x LTS (示例):"
    _info "  curl -fsSL https://deb.nodesource.com/setup_22.x | sudo -E bash -"
    _info "  sudo apt-get install -y nodejs"
    _info "  或使用 nvm: nvm install 22 && nvm use 22"
    return 1
}

# 自动安装/升级 Node.js 的目标版本（官方 tarball；可用 WITTY_NODE_VERSION 覆盖）
_NODE_INSTALL_VERSION="${WITTY_NODE_VERSION:-22.14.0}"

_install_node_from_tarball() {
    # 与发行版无关：直接从 nodejs.org 取官方 tarball。jdos / 未知发行版 / 仓库里的 node 太旧
    # 都能用；root 装到 /usr/local，普通用户装到 ~/.local/node 并临时进 PATH。
    local ARCH URL TMP TARGET
    ARCH="$(uname -m)"
    case "$ARCH" in
        x86_64 | amd64) ARCH="x64" ;;
        aarch64 | arm64) ARCH="arm64" ;;
        *)
            _warn "未知架构 $ARCH，跳过自动安装 Node"
            return 1
            ;;
    esac
    URL="https://nodejs.org/dist/v${_NODE_INSTALL_VERSION}/node-v${_NODE_INSTALL_VERSION}-linux-${ARCH}.tar.xz"
    TMP="$(mktemp -d)"
    _info "下载 Node.js v${_NODE_INSTALL_VERSION}: $URL"
    if ! curl -fsSL "$URL" -o "$TMP/node.tar.xz"; then
        _warn "下载失败（离线 / 代理拦截？）"
        rm -rf "$TMP"
        return 1
    fi
    if ! tar -xJf "$TMP/node.tar.xz" -C "$TMP" --strip-components=1; then
        _warn "解压失败"
        rm -rf "$TMP"
        return 1
    fi
    if _is_root; then
        TARGET="/usr/local"
    else
        TARGET="${HOME}/.local/node"
    fi
    mkdir -p "$TARGET"
    cp -a "$TMP/." "$TARGET/"
    rm -rf "$TMP"
    export PATH="$TARGET/bin:$PATH"
    _info "Node.js 已安装到 $TARGET（PATH 已临时前置）"
    return 0
}

ensure_node() {
    # 保证 Node.js >= 20.19：不满足就装/升，装不上才失败。
    # 顺序：① 已满足 → 直接返回；② 发行版包管理器（可能仍是旧版，随后复验）；
    #       ③ 官方 tarball（最稳，不依赖仓库版本）；④ 仍不行 → 明确失败并给手工步骤。
    if _check_node > /dev/null 2>&1; then
        return 0
    fi
    _info "Node.js 未安装或版本过低，尝试自动安装/升级 ..."

    # 需要先知道发行版/包管理器（ensure_node 可能被单独调用，OS_ID 还没设）
    if [ -z "${OS_ID:-}" ]; then
        detect_os > /dev/null 2>&1 || true
    fi

    local SUDO_CMD=()
    _is_root || SUDO_CMD=(sudo)
    if [ "${OS_ID:-}" = "rpm" ] && _has_cmd dnf; then
        "${SUDO_CMD[@]}" dnf install -y nodejs npm > /dev/null 2>&1 || true
    elif [ "${OS_ID:-}" = "apt" ] && _has_cmd apt-get; then
        "${SUDO_CMD[@]}" apt-get install -y nodejs npm > /dev/null 2>&1 || true
    fi
    if _check_node > /dev/null 2>&1; then
        return 0
    fi

    _install_node_from_tarball || true
    if _check_node > /dev/null 2>&1; then
        return 0
    fi

    _warn "仍不满足 Node.js >= ${_NODE_MIN_MAJOR}.${_NODE_MIN_MINOR}"
    _info "手工安装：见 https://nodejs.org （推荐 22.x LTS），或设 WITTY_NODE_VERSION 后重跑"
    return 1
}

# ──────────────────── OS 检测 ────────────────────

detect_os() {
    if _has_cmd dnf; then
        OS_ID="rpm"
        PM_INSTALL="dnf install -y"
        PM_UPDATE="dnf update -y"
        _log "检测到 dnf 包管理器"
    elif _has_cmd yum; then
        OS_ID="rpm"
        PM_INSTALL="yum install -y"
        PM_UPDATE="yum update -y"
        _log "检测到 yum 包管理器"
    elif _has_cmd apt-get; then
        OS_ID="apt"
        PM_INSTALL="apt-get install -y"
        PM_UPDATE="apt-get update -y"
        _log "检测到 apt-get 包管理器"
    else
        # 认不出包管理器（jdos / WSL / 精简镜像 / 定制内核…）时**不再直接失败**：
        # 一律按 openEuler(rpm) 处理；需要 apt 的场合请显式 OS_ID=apt 覆盖。
        if [ "${OS_ID:-}" = "apt" ]; then
            PM_INSTALL="apt-get install -y"
            PM_UPDATE="apt-get update -y"
            _warn "未检测到包管理器，按显式指定的 apt 处理"
        else
            OS_ID="rpm"
            PM_INSTALL="dnf install -y"
            PM_UPDATE="dnf update -y"
            _warn "未检测到包管理器（dnf/yum/apt-get），按 openEuler(rpm/dnf) 处理"
            _info "  如实际是 deb 系（Ubuntu/WSL），请用 OS_ID=apt 重跑"
        fi
    fi
    _info "架构: $(uname -m)"
}

# ──────────────────── 交互确认 ────────────────────

# 交互确认(返回 0=确认, 1=取消)。deploy.sh 用 read 而非 manage.sh 的
# confirm(manage 是 Docker 路径);保持与脚本其它交互一致。
_confirm_clean() {
    local prompt="$1"
    # NONINTERACTIVE=1 (CI/自动化测试) 时跳过交互, 视为确认。
    if [ "${NONINTERACTIVE:-0}" = "1" ]; then
        return 0
    fi
    local ans
    read -r -p "$prompt [y/N]: " ans
    case "$ans" in
        y|Y|yes|YES) return 0 ;;
        *) return 1 ;;
    esac
}

# ──────────────────── PG 凭据 ────────────────────

# 解析 deploy.conf 的 PG 凭据并导出 PGPASSWORD, 供脚本内 psql 免密使用。
# 密码读取优先级: PG_SECRET_FILE(deploy/pg.passwd) > deploy.conf 的 PG_PASSWORD > 空。
# 密钥文件是运行时唯一真实口令来源, deploy.conf 保持 <CHANGE_ME> 占位不回写。
_load_pg_credentials() {
    local PG_CONF_FILE="$SCRIPT_DIR/../deploy.conf"
    local PG_SECRET_FILE="$SCRIPT_DIR/../pg.passwd"
    [ -f "$PG_CONF_FILE" ] || PG_CONF_FILE="$SCRIPT_DIR/../pg.conf"   # 兼容旧名
    [ -f "$PG_CONF_FILE" ] || [ -f "$PG_SECRET_FILE" ] || return 1
    local CONF_HOST CONF_PORT CONF_USER CONF_DATABASE CONF_PASSWORD
    CONF_HOST="$(grep -E '^PG_HOST=' "$PG_CONF_FILE" 2>/dev/null | head -1 | cut -d= -f2 | tr -d '"')"
    # 宿主机源码部署与 RPM 部署一样连接本机 PostgreSQL；
    # PG_PORT 是 Docker 宿主机映射端口，不能用在这里。
    CONF_PORT="$(grep -E '^PG_PORT_RPM=' "$PG_CONF_FILE" 2>/dev/null | head -1 | cut -d= -f2 | tr -d '"')"
    CONF_USER="$(grep -E '^PG_USER=' "$PG_CONF_FILE" 2>/dev/null | head -1 | cut -d= -f2 | tr -d '"')"
    CONF_DATABASE="$(grep -E '^PG_DATABASE=' "$PG_CONF_FILE" 2>/dev/null | head -1 | cut -d= -f2 | tr -d '"')"
    CONF_PASSWORD="$(grep -E '^PG_PASSWORD=' "$PG_CONF_FILE" 2>/dev/null | head -1 | cut -d= -f2 | tr -d '"')"
    PG_HOST="${PG_HOST:-$CONF_HOST}"
    # 仅接受原生部署专用的 PG_PORT_RPM 覆盖，不读取 Docker PG_PORT。
    PG_PORT="${PG_PORT_RPM:-$CONF_PORT}"
    PG_USER="${PG_USER:-$CONF_USER}"
    PG_DATABASE="${PG_DATABASE:-$CONF_DATABASE}"
    [ -z "$PG_HOST" ] && PG_HOST="127.0.0.1"
    [ -z "$PG_PORT" ] && PG_PORT="5432"
    [ -z "$PG_USER" ] && PG_USER="witty-ub"
    [ -z "$PG_DATABASE" ] && PG_DATABASE="witty-ub"
    # 优先读密钥文件；deploy.conf 的 PG_PASSWORD 仅作旧部署回退（<CHANGE_ME>/witty-ub 视为未设置）。
    local SECRET_PASSWORD=""
    if [ -f "$PG_SECRET_FILE" ]; then
        SECRET_PASSWORD="$(cat "$PG_SECRET_FILE" 2>/dev/null | tr -d '\r\n')"
    fi
    if [ -n "$SECRET_PASSWORD" ]; then
        PG_PASSWORD="$SECRET_PASSWORD"
    elif [ -n "$CONF_PASSWORD" ] && [ "$CONF_PASSWORD" != "<CHANGE_ME>" ] && [ "$CONF_PASSWORD" != "witty-ub" ]; then
        PG_PASSWORD="$CONF_PASSWORD"
    else
        PG_PASSWORD=""
    fi
    if [ -n "$PG_PASSWORD" ]; then
        export PGPASSWORD="$PG_PASSWORD"
    else
        # 防止调用方环境中残留的 PGPASSWORD 被误用于当前部署。
        unset PGPASSWORD
    fi
    return 0
}

# psql 便捷封装: 使用 _load_pg_credentials 的凭据连接。
_psql() {
    _load_pg_credentials || return 1
    # --no-password 禁止 libpq 回退到交互式密码询问。部署探测会在密钥文件
    # 尚未生成时调用本函数；此时应快速返回失败，由后续 PG 初始化生成并
    # 同步凭据，而不是反复显示含糊的 "Password for user ..."。
    psql --no-password -h "$PG_HOST" -p "$PG_PORT" -U "$PG_USER" -d "$PG_DATABASE" "$@"
}


# ── 进程托管：双主人防护（2026-09-16）────────────────────────────────────
# 事故复盘：systemd user unit 在托管后端时，手工跑 deploy.sh 若连不上 user
# bus（SSH 无 linger / WSL 缺 XDG_RUNTIME_DIR / 容器），脚本会回退 "nohup
# 裸进程"。于是 9772 上出现两个主人：裸进程占着端口，systemd 每 10s 重试
# bind 失败；这个窗口里提交的解析任务会成批失败。下面两个函数把这个口子堵住。

# unit 文件是否已安装（只看文件，不依赖 user bus）
systemd_unit_installed() {
    local unit_dir="${XDG_CONFIG_HOME:-$HOME/.config}/systemd/user"
    [ -f "$unit_dir/witty-ub-backend.service" ] || [ -f "$unit_dir/witty-ub-frontend.service" ]
}

# 9772 上是否已经有人应答。有人 → 拒绝再裸启一个。
# 用法: refuse_if_backend_already_serving [pid_file]
refuse_if_backend_already_serving() {
    local pid_file="${1:-}"
    if ! curl --noproxy 127.0.0.1 -s --max-time 2 \
        http://127.0.0.1:9772/health_check 2>/dev/null | grep -q ok; then
        return 0
    fi
    _err "9772 上已经有后端在应答 —— 拒绝再裸启一个（会变成两个主人抢端口，解析任务成批失败）"
    if [ -n "$pid_file" ] && [ -f "$pid_file" ]; then
        _info "PID 文件记录: $(cat "$pid_file" 2>/dev/null || echo '?')"
    fi
    _info "推荐交给 systemd: systemctl --user restart witty-ub-backend"
    _info "确认要裸进程托管: 先停掉现有后端（kill <pid>）再重跑"
    return 1
}
