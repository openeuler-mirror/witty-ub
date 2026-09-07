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

# 最低 Node 版本: Vite 6 / Rolldown 需要 ≥ 20.19
_NODE_MIN_MAJOR=20
_NODE_MIN_MINOR=19

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
    local MAJOR MINOR
    MAJOR="$(echo "$VER" | cut -d. -f1)"
    MINOR="$(echo "$VER" | cut -d. -f2)"
    if [ "$MAJOR" -gt "$_NODE_MIN_MAJOR" ] || \
       { [ "$MAJOR" -eq "$_NODE_MIN_MAJOR" ] && [ "$MINOR" -ge "$_NODE_MIN_MINOR" ]; }; then
        _info "Node.js v$VER ✓"
        return 0
    fi
    _warn "Node.js v$VER 太旧，Vite 前端需要 ≥ v${_NODE_MIN_MAJOR}.${_NODE_MIN_MINOR}"
    _info "安装 Node 22.x LTS (示例):"
    _info "  curl -fsSL https://deb.nodesource.com/setup_22.x | sudo -E bash -"
    _info "  sudo apt-get install -y nodejs"
    _info "  或使用 nvm: nvm install 22 && nvm use 22"
    return 1
}

# ──────────────────── OS 检测 ────────────────────

detect_os() {
    if _has_cmd dnf; then
        OS_ID="rpm"
        PM_INSTALL="dnf install -y --allowerasing"
        PM_UPDATE="dnf update -y --allowerasing"
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
        _err "未检测到受支持的包管理器（dnf/yum/apt-get）"
        exit 1
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
