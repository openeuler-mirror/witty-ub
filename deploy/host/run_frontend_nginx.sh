#!/bin/bash
# Copyright (c) Huawei Technologies Co., Ltd. 2023-2026. All rights reserved.
# witty-ub is licensed under the Mulan PSL v2.
#
# witty-ub 前端 Web 入口（Nginx 模式）
#   静态托管 src/web/dist（发布到 /var/witty-ub/web），API 反代到 WITTY_BACKEND_URL，
#   /agent-api/ 反代到 WITTY_AGENT_URL。需要 nginx 与 sudo 权限。
#   免 root 的 Vite 模式见 run_frontend_vite.sh。
#
# 用法:
#   bash deploy/host/run_frontend_nginx.sh [start|stop|restart|reload|status]  # 默认 start
#   bash deploy/host/run_frontend_nginx.sh start --no-publish                  # 不重新发布 dist/
#
# 环境变量:
#   WITTY_BACKEND_URL  API 反代上游               (默认 http://127.0.0.1:9772)
#   WITTY_AGENT_URL    /agent-api/ 反代上游       (默认 http://127.0.0.1:4096)
#   WITTY_WEB_PORT     监听端口                   (默认 8080)
#   WITTY_WEB_ROOT     静态根目录                 (默认 /var/witty-ub/web)
#   WITTY_WEB_CONF     渲染出的 nginx 配置文件    (默认 $PROJECT_DIR/.deploy-run/nginx.conf)
#
# 运行时文件:
#   配置 $PROJECT_DIR/.deploy-run/nginx.conf  PID $PROJECT_DIR/.deploy-run/nginx.pid
#   日志 $PROJECT_DIR/.deploy-logs/web-error.log、web-access.log

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$(dirname "$SCRIPT_DIR")")"
LOG_DIR="$PROJECT_DIR/.deploy-logs"
RUN_DIR="$PROJECT_DIR/.deploy-run"

WITTY_BACKEND_URL="${WITTY_BACKEND_URL:-http://127.0.0.1:9772}"
WITTY_AGENT_URL="${WITTY_AGENT_URL:-http://127.0.0.1:4096}"
WITTY_WEB_PORT="${WITTY_WEB_PORT:-8080}"
WITTY_WEB_ROOT="${WITTY_WEB_ROOT:-/var/witty-ub/web}"
WITTY_WEB_CONF="${WITTY_WEB_CONF:-$RUN_DIR/nginx.conf}"
NGINX_TEMPLATE="${NGINX_TEMPLATE:-$PROJECT_DIR/packaging/nginx/witty-ub-web.conf.template}"
# envsubst 只读取环境变量, 必须显式导出。
export WITTY_BACKEND_URL WITTY_AGENT_URL
NGINX_PID_FILE="$RUN_DIR/nginx.pid"
WEB_ERROR_LOG="$LOG_DIR/web-error.log"
WEB_ACCESS_LOG="$LOG_DIR/web-access.log"
DIST_DIR="$PROJECT_DIR/src/web/dist"

_log()  { echo "[witty-ub] $*"; }
_warn() { echo "[warn]    $*" >&2; }
_err()  { echo "[error]   $*" >&2; }

_is_root() { [ "$(id -u)" -eq 0 ]; }
SUDO=""
_is_root || SUDO="sudo"

# nginx 通常在 /usr/sbin (root 的 secure_path), 普通用户的 PATH 里可能没有。
NGINX_BIN="$(command -v nginx 2>/dev/null || true)"
if [ -z "$NGINX_BIN" ] && [ -x /usr/sbin/nginx ]; then
    NGINX_BIN=/usr/sbin/nginx
fi

_nginx() { $SUDO "$NGINX_BIN" "$@"; }

usage() {
    cat <<'EOF'
witty-ub 前端 Web 入口（Nginx 模式）

用法:
  bash deploy/host/run_frontend_nginx.sh [start|stop|restart|reload|status]   # 默认 start
  bash deploy/host/run_frontend_nginx.sh start --no-publish                   # 不重新发布 dist/

环境变量:
  WITTY_BACKEND_URL  API 反代上游               (默认 http://127.0.0.1:9772)
  WITTY_AGENT_URL    /agent-api/ 反代上游       (默认 http://127.0.0.1:4096)
  WITTY_WEB_PORT     监听端口                   (默认 8080)
  WITTY_WEB_ROOT     静态根目录                 (默认 /var/witty-ub/web)
  WITTY_WEB_CONF     渲染出的 nginx 配置文件    (默认 .deploy-run/nginx.conf)
EOF
}

# ──────────────────── 校验 ────────────────────

check_env() {
    if [ -z "$NGINX_BIN" ]; then
        _err "未找到 nginx, 请先安装: sudo dnf install -y nginx (或 yum/apt-get)"
        _err "使用 Vite 模式: bash deploy/host/run_frontend_vite.sh"
        return 1
    fi
    [ -f "$NGINX_TEMPLATE" ] || {
        _err "nginx 配置模板缺失: $NGINX_TEMPLATE"
        return 1
    }
    # 防止 WITTY_WEB_ROOT 误配成根目录/父目录后被执行 rm -rf。
    case "${WITTY_WEB_ROOT%/}" in
        ""|"/"|"/var"|"/usr"|"/etc"|"/opt"|"$HOME"|"$PROJECT_DIR")
            _err "WITTY_WEB_ROOT 取值不安全: $WITTY_WEB_ROOT"
            return 1
            ;;
    esac
    return 0
}

# ──────────────────── 发布前端产物 ────────────────────

publish_dist() {
    if [ ! -d "$DIST_DIR" ] || [ -z "$(ls -A "$DIST_DIR" 2>/dev/null)" ]; then
        _err "前端构建产物不存在或为空: $DIST_DIR"
        _err "请先构建前端: cd src/web && npm install && npm run build-only"
        return 1
    fi
    _log "发布前端产物: $DIST_DIR -> $WITTY_WEB_ROOT"
    # nginx worker 若以非特权用户运行, 无法穿透用户 home 目录 (750),
    # 因此统一发布到 /var/witty-ub/web 这类系统目录。
    $SUDO mkdir -p "$(dirname "$WITTY_WEB_ROOT")"
    $SUDO rm -rf "$WITTY_WEB_ROOT"
    $SUDO cp -r "$DIST_DIR" "$WITTY_WEB_ROOT"
    $SUDO chmod -R a+rX "$WITTY_WEB_ROOT"
}

# ──────────────────── 渲染 nginx 配置 ────────────────────

render_conf() {
    mkdir -p "$RUN_DIR" "$LOG_DIR"

    local rendered
    if command -v envsubst >/dev/null 2>&1; then
        # envsubst 优先 (gettext), 缺失时 sed 兜底, 不强依赖新包。
        rendered="$(envsubst '${WITTY_BACKEND_URL} ${WITTY_AGENT_URL}' <"$NGINX_TEMPLATE")"
    else
        rendered="$(sed -e "s|\${WITTY_BACKEND_URL}|$WITTY_BACKEND_URL|g" \
            -e "s|\${WITTY_AGENT_URL}|$WITTY_AGENT_URL|g" "$NGINX_TEMPLATE")"
    fi

    # 把模板里 systemd/容器专用的路径改写为项目内路径。
    printf '%s\n' "$rendered" | sed \
        -e "s|^\([[:space:]]*\)pid /run/witty-ub-web/nginx.pid;|\1pid $NGINX_PID_FILE;|" \
        -e "s|^\([[:space:]]*\)error_log /var/log/witty-ub-web/error.log warn;|\1error_log $WEB_ERROR_LOG warn;|" \
        -e "s|^\([[:space:]]*\)access_log /var/log/witty-ub-web/access.log;|\1access_log $WEB_ACCESS_LOG;|" \
        -e "s|^\([[:space:]]*\)root /var/witty-ub/web;|\1root $WITTY_WEB_ROOT;|" \
        -e "s|^\([[:space:]]*\)listen 8080;|\1listen $WITTY_WEB_PORT;|" \
        >"$WITTY_WEB_CONF"

    # 渲染结果只允许出现仓库内路径; 残留系统目录说明模板与改写规则不一致。
    local leftover
    leftover="$(awk '/^[[:space:]]*#/ {next}
        /\/run\/witty-ub-web|\/var\/log\/witty-ub-web/ {print NR": "$0}' "$WITTY_WEB_CONF")"
    if [ -n "$leftover" ]; then
        _err "nginx 配置渲染失败: 仍残留 systemd/容器专用路径 ($NGINX_TEMPLATE 模板已变化?)"
        echo "$leftover" >&2
        return 1
    fi
    if ! grep -qF "pid $NGINX_PID_FILE;" "$WITTY_WEB_CONF" ||
        ! grep -qF "root $WITTY_WEB_ROOT;" "$WITTY_WEB_CONF"; then
        _err "nginx 配置渲染失败: pid/静态根目录未改写 ($NGINX_TEMPLATE 模板已变化?)"
        return 1
    fi
    _log "nginx 配置已渲染: $WITTY_WEB_CONF"
}

# ──────────────────── 进程管理 ────────────────────

_pid_alive() {
    local pid="${1:-}"
    [ -n "$pid" ] || return 1
    kill -0 "$pid" 2>/dev/null && return 0
    # nginx 以 root 启动时, 普通用户 kill -0 返回 EPERM, 需按 /proc 判定存活。
    [ -d "/proc/$pid" ] && return 0
    return 1
}

_nginx_pid() {
    [ -f "$NGINX_PID_FILE" ] || return 1
    $SUDO cat "$NGINX_PID_FILE" 2>/dev/null | tr -d '\r\n'
}

stop_web() {
    local pid
    pid="$(_nginx_pid || true)"
    if _pid_alive "$pid"; then
        _log "停止 Web nginx (pid $pid)..."
        $SUDO kill "$pid" 2>/dev/null || true
        local i
        for i in $(seq 1 20); do
            _pid_alive "$pid" || break
            sleep 0.5
        done
        if _pid_alive "$pid"; then
            _warn "nginx (pid $pid) 未在 10 秒内退出, 发送 SIGKILL"
            $SUDO kill -9 "$pid" 2>/dev/null || true
        fi
    fi
    $SUDO rm -f "$NGINX_PID_FILE" 2>/dev/null || true
    return 0
}

_free_port() {
    command -v fuser >/dev/null 2>&1 || return 0
    if curl --noproxy '*' -so /dev/null --max-time 2 "http://127.0.0.1:$WITTY_WEB_PORT/" 2>/dev/null; then
        _warn "端口 $WITTY_WEB_PORT 仍被其他进程占用, 尝试结束该进程"
        _warn "若非本项目的服务占用该端口, 请改用 WITTY_WEB_PORT=<其他端口> 启动"
        $SUDO fuser -k "$WITTY_WEB_PORT/tcp" 2>/dev/null || true
        sleep 1
    fi
}

start_web() {
    local publish=1
    if [ "${1:-}" = "--no-publish" ]; then
        publish=0
    fi
    if [ "$publish" -eq 1 ]; then
        publish_dist || return 1
    fi
    render_conf || return 1

    stop_web
    _free_port

    if ! _nginx -t -c "$WITTY_WEB_CONF" 2>&1 | sed 's/^/          /'; then
        _err "nginx 配置校验失败: $WITTY_WEB_CONF"
        return 1
    fi
    if ! _nginx -c "$WITTY_WEB_CONF"; then
        _err "nginx 启动失败, 查看 $WEB_ERROR_LOG"
        return 1
    fi

    local i code
    for i in $(seq 1 10); do
        code="$(curl --noproxy '*' -so /dev/null --max-time 2 -w '%{http_code}' \
            "http://127.0.0.1:$WITTY_WEB_PORT/" 2>/dev/null || true)"
        [ "$code" = "200" ] && break
        sleep 1
    done
    if [ "${code:-}" != "200" ]; then
        _err "Web 健康检查失败 (http://127.0.0.1:$WITTY_WEB_PORT/ 返回 ${code:-无响应})"
        _err "排查: tail -50 $WEB_ERROR_LOG"
        return 1
    fi
    _log "Web 已启动 (nginx, port $WITTY_WEB_PORT)"
    _log "  静态根目录: $WITTY_WEB_ROOT"
    _log "  API 反代:   $WITTY_BACKEND_URL"
    _log "  Agent 反代: $WITTY_AGENT_URL (/agent-api/)"
    _log "  配置/日志:  $WITTY_WEB_CONF , $WEB_ERROR_LOG"
    return 0
}

status_web() {
    local pid code
    pid="$(_nginx_pid || true)"
    if _pid_alive "$pid"; then
        _log "Web nginx 运行中 (pid $pid, port $WITTY_WEB_PORT)"
    else
        _warn "Web nginx 未运行 (pid 文件: $NGINX_PID_FILE)"
    fi
    code="$(curl --noproxy '*' -so /dev/null --max-time 3 -w '%{http_code}' \
        "http://127.0.0.1:$WITTY_WEB_PORT/health_check" 2>/dev/null || true)"
    _log "反代健康检查 /health_check -> ${code:-无响应} (上游 $WITTY_BACKEND_URL)"
    _pid_alive "$pid"
}

reload_web() {
    render_conf || return 1
    if ! _nginx -t -c "$WITTY_WEB_CONF" >/dev/null 2>&1; then
        _err "nginx 配置校验失败: $WITTY_WEB_CONF"
        return 1
    fi
    _nginx -c "$WITTY_WEB_CONF" -s reload || return 1
    _log "Web nginx 已重载 ($WITTY_WEB_CONF)"
}

# ──────────────────── 入口 ────────────────────

CMD="${1:-start}"
shift || true

check_env || exit 1

case "$CMD" in
    start)   start_web "$@" ;;
    stop)    stop_web ;;
    restart) start_web "$@" ;;
    reload)  reload_web ;;
    status)  status_web ;;
    -h|--help|help)
        usage
        ;;
    *)
        _err "未知子命令: $CMD (可用: start/stop/restart/reload/status)"
        exit 2
        ;;
esac
