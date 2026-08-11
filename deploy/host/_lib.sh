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
    if [ -f /etc/openEuler-release ] || grep -qi 'openeuler' /etc/os-release 2>/dev/null; then
        OS_ID="openeuler"
        PM_INSTALL="dnf install -y --allowerasing"
        PM_UPDATE="dnf update -y --allowerasing"
        _log "检测到 openEuler"
        if [ "$(uname -m)" = "aarch64" ]; then
            _info "架构: aarch64"
        fi
    elif grep -qi 'ubuntu' /etc/os-release 2>/dev/null; then
        OS_ID="ubuntu"
        PM_INSTALL="apt-get install -y"
        PM_UPDATE="apt-get update -y"
        _log "检测到 Ubuntu"
        if grep -qi 'microsoft' /proc/version 2>/dev/null; then
            _info "运行在 WSL 环境"
        fi
    else
        _err "不支持的操作系统，需要 openEuler 或 Ubuntu"
        _info "当前 OS: $(cat /etc/os-release 2>/dev/null | head -3)"
        exit 1
    fi
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

# 解析 pg.conf 的 PG 凭据并导出 PGPASSWORD, 供脚本内 psql 免密使用。
# 与 sync_pg_credentials 同源(pg.conf 是唯一真实凭据来源)。
_load_pg_credentials() {
    local PG_CONF_FILE="$SCRIPT_DIR/../pg.conf"
    [ -f "$PG_CONF_FILE" ] || return 1
    PG_HOST="$(grep -E '^PG_HOST=' "$PG_CONF_FILE" | head -1 | cut -d= -f2 | tr -d '"')"
    PG_PORT="$(grep -E '^PG_PORT=' "$PG_CONF_FILE" | head -1 | cut -d= -f2 | tr -d '"')"
    PG_USER="$(grep -E '^PG_USER=' "$PG_CONF_FILE" | head -1 | cut -d= -f2 | tr -d '"')"
    PG_DATABASE="$(grep -E '^PG_DATABASE=' "$PG_CONF_FILE" | head -1 | cut -d= -f2 | tr -d '"')"
    PG_PASSWORD="$(grep -E '^PG_PASSWORD=' "$PG_CONF_FILE" | head -1 | cut -d= -f2 | tr -d '"')"
    [ -z "$PG_HOST" ] && PG_HOST="127.0.0.1"
    [ -z "$PG_PORT" ] && PG_PORT="15432"
    [ -z "$PG_USER" ] && PG_USER="witty-ub"
    [ -z "$PG_DATABASE" ] && PG_DATABASE="witty-ub"
    [ -n "$PG_PASSWORD" ] && export PGPASSWORD="$PG_PASSWORD"
    return 0
}

# psql 便捷封装: 使用 _load_pg_credentials 的凭据连接。
_psql() {
    _load_pg_credentials
    psql -h "$PG_HOST" -p "$PG_PORT" -U "$PG_USER" -d "$PG_DATABASE" "$@"
}
