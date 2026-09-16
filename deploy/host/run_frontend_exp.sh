#!/bin/bash
# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.
# witty-ub is licensed under the Mulan PSL v2.
#
# witty-ub 试验性前端（exp）启动器（供 systemd user unit 调用）
#
#   1) dist/ + nginx 可用 → nginx 静态托管 + 反代（端口 WITTY_WEB_EXP_PORT，默认 8081）
#   2) 否则              → vite preview/dev（端口 5174）
#
# 与既有前端（run_frontend.sh，8080/5173）完全隔离：静态根 /var/witty-ub/web-exp、
# 独立配置/pid/日志、独立端口；后端地址与 Agent 地址复用同一组环境变量。
#
# 反代地址:
#   WITTY_BACKEND_URL  后端 FastAPI (默认 http://127.0.0.1:9772)
#   WITTY_AGENT_URL    OpenCode     (默认 http://127.0.0.1:4096)

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$(dirname "$SCRIPT_DIR")")"
if [ -n "${EXP_WEB_DIR:-}" ]; then
    WEB_DIR="$EXP_WEB_DIR"
elif [ -d "$PROJECT_DIR/src/web_exp" ]; then
    WEB_DIR="$PROJECT_DIR/src/web_exp"
else
    WEB_DIR="$PROJECT_DIR/src/web_new"
fi
LOG_DIR="$PROJECT_DIR/.deploy-logs"
RUN_DIR="$PROJECT_DIR/.deploy-run"
WEB_ROOT=/var/witty-ub/web-exp

# 持久化配置（由 deploy_frontend_exp.sh 写入）：systemd 单元通过 EnvironmentFile 加载，
# nohup 回退路径在此显式 source，保证重启后仍指向同一后端/Agent。
ENV_FILE="$RUN_DIR/frontend-exp.env"
# shellcheck disable=SC1090
[ -f "$ENV_FILE" ] && . "$ENV_FILE"

WEB_PORT="${WITTY_WEB_EXP_PORT:-8081}"
FALLBACK_PORT="${WITTY_WEB_EXP_FALLBACK_PORT:-5174}"
export WITTY_BACKEND_URL="${WITTY_BACKEND_URL:-http://127.0.0.1:9772}"
export WITTY_AGENT_URL="${WITTY_AGENT_URL:-http://127.0.0.1:4096}"

SUDO=""
[ "$(id -u)" -eq 0 ] || SUDO="sudo"

render_nginx_conf() {
    if command -v envsubst >/dev/null 2>&1; then
        envsubst '${WITTY_BACKEND_URL} ${WITTY_AGENT_URL}' \
            <"$PROJECT_DIR/packaging/nginx/witty-ub-web-exp.conf.template"
    else
        sed -e "s|\${WITTY_BACKEND_URL}|$WITTY_BACKEND_URL|g" \
            -e "s|\${WITTY_AGENT_URL}|$WITTY_AGENT_URL|g" \
            "$PROJECT_DIR/packaging/nginx/witty-ub-web-exp.conf.template"
    fi | sed \
        -e "s|pid /run/witty-ub-web-exp/nginx.pid;|pid $RUN_DIR/nginx-web-exp.pid;|" \
        -e "s|error_log /var/log/witty-ub-web-exp/error.log warn;|error_log $LOG_DIR/web-exp-error.log warn;|" \
        -e "s|access_log /var/log/witty-ub-web-exp/access.log;|access_log $LOG_DIR/web-exp-access.log;|" \
        -e "s|root /var/witty-ub/web-exp;|root $WEB_ROOT;|" \
        -e "s|listen 8081;|listen $WEB_PORT;|"
}

if [ -d "$WEB_DIR/dist" ] && [ -n "$(ls -A "$WEB_DIR/dist" 2>/dev/null)" ] && command -v nginx >/dev/null 2>&1; then
    [ -f "$RUN_DIR/nginx-web-exp.pid" ] && $SUDO kill "$($SUDO cat "$RUN_DIR/nginx-web-exp.pid")" 2>/dev/null || true
    command -v fuser >/dev/null 2>&1 && fuser -k "$WEB_PORT/tcp" "$FALLBACK_PORT/tcp" 2>/dev/null || true
    sleep 1
    mkdir -p "$RUN_DIR" "$LOG_DIR"
    # 发布 dist 到 $WEB_ROOT: nginx worker(非特权用户)无法穿透用户 home 目录(750)
    $SUDO mkdir -p "$(dirname "$WEB_ROOT")"
    $SUDO rm -rf "$WEB_ROOT"
    $SUDO cp -r "$WEB_DIR/dist" "$WEB_ROOT"
    $SUDO chmod -R a+rX "$WEB_ROOT"
    render_nginx_conf >"$RUN_DIR/nginx-web-exp.conf"
    echo "[run_frontend_exp] 启动 exp 前端 (nginx, port $WEB_PORT, backend=$WITTY_BACKEND_URL)"
    exec $SUDO nginx -c "$RUN_DIR/nginx-web-exp.conf" -g 'daemon off;'
fi

# 回退: vite preview (有 dist/) 或 dev server
cd "$WEB_DIR"
if [ -d dist ] && [ -n "$(ls -A dist 2>/dev/null)" ]; then
    echo "[run_frontend_exp] nginx 不可用, 回退 vite preview (port $FALLBACK_PORT)"
    exec ./node_modules/.bin/vite preview --host 0.0.0.0 --port "$FALLBACK_PORT" --strictPort
fi
echo "[run_frontend_exp] dist/ 不可用, 回退 vite dev (port $FALLBACK_PORT)"
exec ./node_modules/.bin/vite --host 0.0.0.0 --port "$FALLBACK_PORT" --strictPort
