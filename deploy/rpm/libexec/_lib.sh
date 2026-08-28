#!/bin/bash
# Copyright (c) Huawei Technologies Co., Ltd. 2023-2026. All rights reserved.
# witty-ub is licensed under the Mulan PSL v2.
#
# witty-ub manager 共享工具库（RPM 安装后由 witty-ub-manager 子包提供）
# 被 manager.sh / install_deps.sh / deploy_pg.sh 共同 source。
# 提供色彩日志、OS 检测、PG 凭据加载（读 /etc/witty-ub/deploy.conf，兼容旧名 pg.conf）、
# psql 封装、交互确认等通用函数。
#
# 不要直接执行此脚本。

set -euo pipefail

# RPM 安装后路径常量（与 witty-ub.spec 中的安装路径一致）
WITTY_DIR="${WITTY_DIR:-/var/witty-ub}"
WITTY_MANAGER_DIR="${WITTY_MANAGER_DIR:-/usr/libexec/witty-ub-manager}"
WITTY_LATENCY_DIR="${WITTY_LATENCY_DIR:-${WITTY_DIR}/latency}"
WITTY_CONFIG_DIR="${WITTY_CONFIG_DIR:-${WITTY_DIR}/config}"
WITTY_ETC_DIR="${WITTY_ETC_DIR:-/etc/witty-ub}"
PG_CONF_FILE="${PG_CONF_FILE:-${WITTY_ETC_DIR}/deploy.conf}"
[ -f "$PG_CONF_FILE" ] || PG_CONF_FILE="${WITTY_ETC_DIR}/pg.conf"   # 兼容旧安装
DIAG_CONFIG_FILE="${DIAG_CONFIG_FILE:-${WITTY_CONFIG_DIR}/diagnosis_config.toml}"

# witty-ub 的 systemd services（system-wide，由 witty-ub 主包安装）
WITTY_SERVICES=(witty-ub-web witty-ub-latency)

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

# 需要 root 或 sudo。返回 0=可用，1=不可用。
_require_root() {
    if _is_root; then return 0; fi
    if _has_cmd sudo; then return 0; fi
    _err "需要 root 或 sudo 权限"
    return 1
}

# 以 postgres 用户身份执行 psql（自动处理 root/sudo）
_psql_as_postgres() {
    if _is_root; then
        su - postgres -c "psql -p ${PG_PORT:-5432} $*"
    else
        sudo su - postgres -c "psql -p ${PG_PORT:-5432} $*"
    fi
}

# ──────────────────── OS 检测 ────────────────────

detect_os() {
    if [ -f /etc/openEuler-release ] || grep -qi 'openeuler' /etc/os-release 2>/dev/null; then
        OS_ID="openeuler"
        PM_INSTALL="dnf install -y --allowerasing"
        PM_UPDATE="dnf update -y --allowerasing"
        _log "检测到 openEuler"
    elif grep -qi 'ubuntu' /etc/os-release 2>/dev/null; then
        OS_ID="ubuntu"
        PM_INSTALL="apt-get install -y"
        PM_UPDATE="apt-get update -y"
        _log "检测到 Ubuntu"
    else
        _err "不支持的操作系统，需要 openEuler 或 Ubuntu"
        _info "当前 OS: $(cut -d$'\n' -f1-3 /etc/os-release 2>/dev/null)"
        return 1
    fi
}

# ──────────────────── 交互确认 ────────────────────

# 交互确认(返回 0=确认, 1=取消)。
# NONINTERACTIVE=1 (CI/自动化测试) 时跳过交互, 视为确认。
_confirm() {
    local prompt="$1"
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

# 解析 /etc/witty-ub/pg.conf 的 PG 凭据并导出 PGPASSWORD, 供脚本内 psql 免密使用。
# 与 sync_pg_credentials 同源(pg.conf 是唯一真实凭据来源)。
_load_pg_credentials() {
    [ -f "$PG_CONF_FILE" ] || { _warn "pg.conf 不存在: $PG_CONF_FILE"; return 1; }
    PG_HOST="$(grep -E '^PG_HOST=' "$PG_CONF_FILE" | head -1 | cut -d= -f2 | tr -d '"')"
    PG_PORT="$(grep -E '^PG_PORT_RPM=' "$PG_CONF_FILE" | head -1 | cut -d= -f2 | tr -d '"')"
    [ -z "$PG_PORT" ] && PG_PORT="$(grep -E '^PG_PORT=' "$PG_CONF_FILE" | head -1 | cut -d= -f2 | tr -d '"')"
    PG_USER="$(grep -E '^PG_USER=' "$PG_CONF_FILE" | head -1 | cut -d= -f2 | tr -d '"')"
    PG_DATABASE="$(grep -E '^PG_DATABASE=' "$PG_CONF_FILE" | head -1 | cut -d= -f2 | tr -d '"')"
    PG_PASSWORD="$(grep -E '^PG_PASSWORD=' "$PG_CONF_FILE" | head -1 | cut -d= -f2 | tr -d '"')"
    [ -z "$PG_HOST" ] && PG_HOST="127.0.0.1"
    [ -z "$PG_PORT" ] && PG_PORT="5432"
    [ -z "$PG_USER" ] && PG_USER="witty-ub"
    [ -z "$PG_DATABASE" ] && PG_DATABASE="witty-ub"
    [ -n "$PG_PASSWORD" ] && export PGPASSWORD="$PG_PASSWORD"
    return 0
}

# psql 便捷封装: 使用 _load_pg_credentials 的凭据连接 witty-ub 业务库。
_psql() {
    _load_pg_credentials || return 1
    psql -h "$PG_HOST" -p "$PG_PORT" -U "$PG_USER" -d "$PG_DATABASE" "$@"
}
