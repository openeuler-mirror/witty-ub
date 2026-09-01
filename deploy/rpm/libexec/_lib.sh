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
[ -f "$PG_CONF_FILE" ] || PG_CONF_FILE="${WITTY_ETC_DIR}/pg.conf" # 兼容旧安装
DIAG_CONFIG_FILE="${DIAG_CONFIG_FILE:-${WITTY_CONFIG_DIR}/diagnosis_config.toml}"

# 前端连接配置（witty-ub-web 子包安装默认值，manager config 管理）
WITTY_WEB_ENV="${WITTY_ETC_DIR}/web/env"
NGINX_CONF_TEMPLATE="${NGINX_CONF_TEMPLATE:-/usr/share/witty-ub/nginx/witty-ub-web.conf.template}"
NGINX_CONF_FILE="${WITTY_ETC_DIR}/web/nginx.conf"
AGENT_PROMPT_FILE="${WITTY_DIR}/witty_ub_diagnostician/.opencode/agents/witty-ub-diagnostician.md"
# 旧布局兜底（Agent bundle 未随包安装时，提示词位于 config/agents）
AGENT_PROMPT_FILE_LEGACY="${WITTY_DIR}/config/agents/witty-ub-diagnostician.md"

# witty-ub 的 systemd services：由 role_services 按角色动态生成
WITTY_SERVICES=()

# ──────────────────── 色彩 ────────────────────

_COLOR_RESET='\033[0m'
_COLOR_GREEN='\033[0;32m'
_COLOR_YELLOW='\033[1;33m'
_COLOR_RED='\033[0;31m'
_COLOR_BLUE='\033[0;34m'

# ──────────────────── 日志 ────────────────────

_log() { echo -e "${_COLOR_GREEN}[witty-ub]${_COLOR_RESET} $*"; }
_warn() { echo -e "${_COLOR_YELLOW}[warn]${_COLOR_RESET}    $*"; }
_err() { echo -e "${_COLOR_RED}[error]${_COLOR_RESET}   $*"; }
_info() { echo -e "${_COLOR_BLUE}[info]${_COLOR_RESET}    $*"; }
_step_header() {
    echo ""
    echo -e "${_COLOR_GREEN}═══ $* ═══${_COLOR_RESET}"
}

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
    y | Y | yes | YES) return 0 ;;
    *) return 1 ;;
    esac
}

# ──────────────────── PG 凭据 ────────────────────

# 解析 /etc/witty-ub/pg.conf 的 PG 凭据并导出 PGPASSWORD, 供脚本内 psql 免密使用。
# 与 sync_pg_credentials 同源(pg.conf 是唯一真实凭据来源)。
_load_pg_credentials() {
    [ -f "$PG_CONF_FILE" ] || {
        _warn "pg.conf 不存在: $PG_CONF_FILE"
        return 1
    }
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

# ──────────────────── 角色探测 ────────────────────

# 按已安装子包探测本机部署角色:
#   witty-ub-backend + witty-ub-web → all（单机/前后端同机）
#   仅 witty-ub-backend            → backend
#   仅 witty-ub-web                → frontend
#   均未安装但旧单包 witty-ub 在   → all（旧单包负载全量，升级兼容）
# WITTY_ROLE_FORCE=all|backend|frontend 可覆盖探测结果（测试/特殊场景）。
detect_role() {
    if [ -n "${WITTY_ROLE_FORCE:-}" ]; then
        WITTY_ROLE="$WITTY_ROLE_FORCE"
        return 0
    fi
    _has_cmd rpm || {
        _err "rpm 命令不可用，无法探测部署角色（可用 WITTY_ROLE_FORCE 覆盖）"
        return 1
    }
    local backend=0 web=0
    rpm -q witty-ub-backend >/dev/null 2>&1 && backend=1
    rpm -q witty-ub-web >/dev/null 2>&1 && web=1
    if [ "$backend" = "1" ] && [ "$web" = "1" ]; then
        WITTY_ROLE="all"
    elif [ "$backend" = "1" ]; then
        WITTY_ROLE="backend"
    elif [ "$web" = "1" ]; then
        WITTY_ROLE="frontend"
    elif rpm -q witty-ub >/dev/null 2>&1; then
        WITTY_ROLE="all"
    else
        _err "未检测到 witty-ub 子包（witty-ub-backend / witty-ub-web）"
        _info "请先安装: sudo dnf install -y witty-ub-backend  # 或 witty-ub-web / witty-ub"
        return 1
    fi
    return 0
}

# 按角色生成 WITTY_SERVICES（本机服务集合）
role_services() {
    case "${WITTY_ROLE:-all}" in
    backend) WITTY_SERVICES=(witty-ub-latency) ;;
    frontend) WITTY_SERVICES=(witty-ub-web) ;;
    all) WITTY_SERVICES=(witty-ub-web witty-ub-latency) ;;
    *)
        _err "未知角色: ${WITTY_ROLE}"
        return 1
        ;;
    esac
}

# ──────────────────── 前端连接配置 / 渲染 ────────────────────

# 从 /etc/witty-ub/web/env 读取 KEY=VALUE 值；未设置时输出默认值。
web_env_get() {
    local key="$1" default="${2:-}" val=""
    if [ -f "$WITTY_WEB_ENV" ]; then
        val="$(grep -E "^${key}=" "$WITTY_WEB_ENV" 2>/dev/null | head -1 | cut -d= -f2 | tr -d '"')"
    fi
    echo "${val:-$default}"
}

# 提取 URL 中的主机名（用于 no_proxy）
_url_host() {
    printf '%s' "$1" | sed -E 's#^[a-zA-Z][a-zA-Z0-9+.-]*://([^:/]+).*#\1#'
}

# 写 /etc/witty-ub/web/env（唯一配置源，nginx 与 Agent 提示词共用）
write_web_env() {
    local backend_url="$1" agent_url="$2" host no_proxy
    host="$(_url_host "$backend_url")"
    no_proxy="127.0.0.1"
    [ -n "$host" ] && no_proxy="127.0.0.1,${host}"
    mkdir -p "$(dirname "$WITTY_WEB_ENV")"
    cat >"$WITTY_WEB_ENV" <<EOF
# witty-ub-web 前端连接配置（由 witty-ub manager config 管理）
# WITTY_BACKEND_URL: FastAPI 后端地址，nginx 反代与 Agent 提示词共用
WITTY_BACKEND_URL=${backend_url}
WITTY_API_BASE=${backend_url}
WITTY_AGENT_URL=${agent_url}
WITTY_NO_PROXY=${no_proxy}
EOF
    chmod 0640 "$WITTY_WEB_ENV"
}

# 渲染 nginx 配置（sed 替换模板占位符，不依赖 envsubst/gettext）
render_nginx_conf() {
    local backend_url="$1" agent_url="$2"
    [ -f "$NGINX_CONF_TEMPLATE" ] || {
        _warn "nginx 模板不存在: $NGINX_CONF_TEMPLATE（witty-ub-web 子包未安装?）"
        return 1
    }
    mkdir -p "$(dirname "$NGINX_CONF_FILE")"
    sed \
        -e "s|\${WITTY_BACKEND_URL}|${backend_url}|g" \
        -e "s|\${WITTY_AGENT_URL}|${agent_url}|g" \
        "$NGINX_CONF_TEMPLATE" >"${NGINX_CONF_FILE}.tmp" &&
        mv "${NGINX_CONF_FILE}.tmp" "$NGINX_CONF_FILE"
    chmod 0640 "$NGINX_CONF_FILE"
    _log "nginx 配置已渲染: $NGINX_CONF_FILE (backend=${backend_url} agent=${agent_url})"
}

# 渲染 Agent 提示词基址（幂等：已渲染内容不含占位符）
# 优先 Agent bundle 布局，兜底 config/agents 旧布局
render_agent_prompt() {
    local api_base="$1" no_proxy="$2"
    local prompt_file=""
    if [ -f "$AGENT_PROMPT_FILE" ]; then
        prompt_file="$AGENT_PROMPT_FILE"
    elif [ -f "$AGENT_PROMPT_FILE_LEGACY" ]; then
        prompt_file="$AGENT_PROMPT_FILE_LEGACY"
    else
        _warn "Agent 提示词不存在: $AGENT_PROMPT_FILE / $AGENT_PROMPT_FILE_LEGACY"
        return 0
    fi
    local RENDER_SUDO=""
    [ -w "$prompt_file" ] || RENDER_SUDO="sudo"
    ${RENDER_SUDO} sed -i \
        -e "s|\${WITTY_API_BASE}|${api_base}|g" \
        -e "s|\${WITTY_NO_PROXY}|${no_proxy}|g" \
        "$prompt_file" 2>/dev/null || {
        _warn "Agent 提示词渲染失败"
        return 0
    }
    _log "Agent 提示词已渲染: $prompt_file (api_base=${api_base})"
}

# 按当前 web env 渲染 nginx 与 Agent 提示词（config/install 共用）
render_frontend_configs() {
    local backend_url agent_url no_proxy
    backend_url="$(web_env_get WITTY_BACKEND_URL http://127.0.0.1:9772)"
    agent_url="$(web_env_get WITTY_AGENT_URL http://127.0.0.1:4096)"
    no_proxy="$(web_env_get WITTY_NO_PROXY 127.0.0.1)"
    render_nginx_conf "$backend_url" "$agent_url" || return 1
    render_agent_prompt "$backend_url" "$no_proxy"
}
