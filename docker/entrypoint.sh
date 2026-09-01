#!/bin/bash
# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.
# witty-ub is licensed under the Mulan PSL v2.

set -e

echo "========================================"
echo "Witty-UB Container Startup"
echo "========================================"

export WITTY_DIR="${WITTY_DIR:-/var/witty-ub}"
export WITTY_INSTALL_PATH="${WITTY_INSTALL_PATH:-/usr/bin}"

# ── 角色与分离部署配置 ──────────────────────────────
# WITTY_ROLE: all（默认，单容器 All-in-One）| backend（仅 FastAPI）| frontend（Nginx+OpenCode）
export WITTY_ROLE="${WITTY_ROLE:-all}"
# Nginx 反代上游
export WITTY_BACKEND_URL="${WITTY_BACKEND_URL:-http://127.0.0.1:9772}"
export WITTY_AGENT_URL="${WITTY_AGENT_URL:-http://127.0.0.1:4096}"
# Agent 提示词中的后端基址；frontend 角色默认跟随 WITTY_BACKEND_URL
export WITTY_API_BASE="${WITTY_API_BASE:-$WITTY_BACKEND_URL}"
export WITTY_NO_PROXY="${WITTY_NO_PROXY:-127.0.0.1}"
# OpenCode 绑定地址（兜底落位 B 需改为 0.0.0.0）
export OPENCODE_HOST="${OPENCODE_HOST:-127.0.0.1}"

echo "Role: ${WITTY_ROLE}  Backend: ${WITTY_BACKEND_URL}  Agent: ${WITTY_AGENT_URL}"

# ── 后端数据同步（all / backend 角色） ──────────────────────────────
sync_backend_data() {
    # Refresh packaged rules on every start. Docker only initializes a named
    # volume from the image on its first use, so an existing witty-ub-data volume
    # would otherwise miss rules added by a newer image.
    # Source-built images seed from /usr/share/witty-ub/data; RPM images already
    # install the data directly into the runtime dir.
    echo "Syncing packaged diagnosis data..."
    WITTY_DATA_SEED_DIR="/usr/share/witty-ub/data"
    WITTY_RUNTIME_DATA_DIR="${WITTY_DIR}/data"
    mkdir -p "${WITTY_RUNTIME_DATA_DIR}"
    if [ -d "${WITTY_DATA_SEED_DIR}" ]; then
        cp -a "${WITTY_DATA_SEED_DIR}/." "${WITTY_RUNTIME_DATA_DIR}/"
    fi

    for required_file in \
        "${WITTY_RUNTIME_DATA_DIR}/failure_mode_tree.json" \
        "${WITTY_RUNTIME_DATA_DIR}/ubsocket/ubsocket_failure_mode.json" \
        "${WITTY_RUNTIME_DATA_DIR}/umq/umq_failure_mode.json" \
        "${WITTY_RUNTIME_DATA_DIR}/urma/urma_failure_mode.json"; do
        if [ ! -f "${required_file}" ]; then
            echo "[ERROR] Required diagnosis data is missing: ${required_file}"
            exit 1
        fi
    done
    if [ ! -x "${WITTY_INSTALL_PATH}/witty-ub-brpc-diag" ]; then
        echo "[ERROR] BRPC diagnosis tool is missing: ${WITTY_INSTALL_PATH}/witty-ub-brpc-diag"
        exit 1
    fi
    echo "[OK] BRPC diagnosis tool and data are ready"
}

# ── Agent 配置布局检测 ──────────────────────────────────────────────
# bundle: 源码镜像 witty_ub_diagnostician/.opencode/
# legacy: RPM 镜像 config/（仅提示词的旧布局）
detect_agent_layout() {
    local bundle="${WITTY_DIR}/witty_ub_diagnostician/.opencode"
    local legacy="${WITTY_DIR}/config"
    if [ -f "${bundle}/opencode.json" ] && [ -f "${bundle}/agents/witty-ub-diagnostician.md" ]; then
        AGENT_OPENCODE_CONFIG="${bundle}/opencode.json"
        AGENT_PROMPT_MD="${bundle}/agents/witty-ub-diagnostician.md"
    elif [ -f "${legacy}/opencode.json" ] && [ -f "${legacy}/agents/witty-ub-diagnostician.md" ]; then
        AGENT_OPENCODE_CONFIG="${legacy}/opencode.json"
        AGENT_PROMPT_MD="${legacy}/agents/witty-ub-diagnostician.md"
    else
        echo "[ERROR] OpenCode agent config not found (checked ${bundle} and ${legacy})"
        exit 1
    fi
    echo "[OK] Agent config: ${AGENT_OPENCODE_CONFIG}"
}

# ── 渲染 Agent 提示词（WITTY_API_BASE / WITTY_NO_PROXY） ────────────
render_agent_prompt() {
    detect_agent_layout
    # 幂等: 已渲染内容不含占位符, envsubst 为 no-op
    envsubst '${WITTY_API_BASE} ${WITTY_NO_PROXY}' <"${AGENT_PROMPT_MD}" >"${AGENT_PROMPT_MD}.tmp" &&
        mv "${AGENT_PROMPT_MD}.tmp" "${AGENT_PROMPT_MD}"
    echo "[OK] Agent prompt rendered with API base: ${WITTY_API_BASE}"
}

# ── Nginx（all / frontend 角色） ──────────────────────────────
start_nginx() {
    echo "Rendering Nginx config..."
    mkdir -p /run/witty-ub-web /var/log/witty-ub-web
    envsubst '${WITTY_BACKEND_URL} ${WITTY_AGENT_URL}' \
        </etc/witty-ub/web/nginx.conf.template >/etc/witty-ub/web/nginx.conf
    echo "Starting Nginx web server..."
    nginx -c /etc/witty-ub/web/nginx.conf
    echo "[OK] Nginx started on port 8080 (backend: ${WITTY_BACKEND_URL})"
}

# ── FastAPI 后端（all / backend 角色） ──────────────────────────────
start_backend() {
    echo "Starting Latency Plugin..."
    /var/witty-ub/latency/.venv/bin/python \
        /var/witty-ub/latency/access/fastapi_server.py \
        >/var/log/witty-ub/latency_server.log 2>&1 &

    echo "  Waiting for Latency Plugin to be ready..."
    for i in $(seq 1 20); do
        if curl -s --noproxy 127.0.0.1 http://127.0.0.1:9772/health_check | grep -q "ok"; then
            echo "[OK] Latency Plugin started on port 9772"
            return 0
        fi
        if [ "$i" -eq 20 ]; then
            echo "[ERROR] Latency Plugin failed to start. Check /var/log/witty-ub/latency_server.log"
            exit 1
        fi
        sleep 2
    done
}

wait_backend_ready() {
    # frontend 角色等待远端后端就绪（不失败, 后端可能稍后启动）
    echo "  Waiting for backend at ${WITTY_BACKEND_URL} ..."
    for i in $(seq 1 20); do
        if curl -s --max-time 3 --noproxy '*' "${WITTY_BACKEND_URL}/health_check" | grep -q "ok"; then
            echo "[OK] Backend at ${WITTY_BACKEND_URL} is healthy"
            return 0
        fi
        sleep 2
    done
    echo "[WARN] Backend at ${WITTY_BACKEND_URL} is not reachable yet; continuing anyway"
}

# ── OpenCode（all / frontend 角色） ──────────────────────────────
start_opencode() {
    render_agent_prompt
    cd /var/witty-ub
    export OPENCODE_CONFIG="${OPENCODE_CONFIG:-${AGENT_OPENCODE_CONFIG}}"
    # Standard .opencode layout dir for agents/skills/commands discovery;
    # a user-provided OPENCODE_CONFIG_DIR always wins.
    export OPENCODE_CONFIG_DIR="${OPENCODE_CONFIG_DIR:-$(cd "$(dirname "${AGENT_OPENCODE_CONFIG}")" && pwd)}"
    nohup /usr/bin/opencode serve --hostname "${OPENCODE_HOST}" --port 4096 \
        >/var/log/witty-ub/opencode_server.log 2>&1 &
    OPENCODE_PID=$!

    echo "  Waiting for OpenCode server to be ready..."
    for i in $(seq 1 20); do
        if curl -s --max-time 3 --noproxy 127.0.0.1 http://127.0.0.1:4096/global/health | grep -q 'healthy'; then
            echo "[OK] OpenCode server started on port 4096"
            return 0
        fi
        if ! kill -0 "${OPENCODE_PID}" 2>/dev/null; then
            echo "[ERROR] OpenCode server exited. Check /var/log/witty-ub/opencode_server.log"
            exit 1
        fi
        if [ "$i" -eq 20 ]; then
            echo "[ERROR] OpenCode server failed its health check. Check /var/log/witty-ub/opencode_server.log"
            exit 1
        fi
        sleep 1
    done
}

trap 'kill $(jobs -p) 2>/dev/null; exit 0' SIGTERM SIGINT

case "${WITTY_ROLE}" in
all)
    sync_backend_data
    start_nginx
    start_backend
    # OpenCode queries the latency HTTP API directly, so start it only
    # after the backend is healthy.
    start_opencode
    echo "All services started successfully!"
    echo "========================================"
    echo "  - Web UI:     http://localhost:8080"
    echo "  - API:        http://localhost:9772"
    echo "  - OpenCode:   http://localhost:4096"
    echo "  - Health:     http://localhost:9772/health_check"
    echo "  - Logs:       /var/log/witty-ub/"
    echo "========================================"
    ;;
backend)
    sync_backend_data
    start_backend
    echo "Backend-only container started successfully!"
    echo "========================================"
    echo "  - API:        http://0.0.0.0:9772"
    echo "  - Health:     http://localhost:9772/health_check"
    echo "  - Logs:       /var/log/witty-ub/"
    echo "========================================"
    ;;
frontend)
    start_nginx
    wait_backend_ready
    start_opencode
    echo "Frontend-only container started successfully!"
    echo "========================================"
    echo "  - Web UI:     http://localhost:8080"
    echo "  - Backend:    ${WITTY_BACKEND_URL}"
    echo "  - OpenCode:   http://localhost:4096 (agent API base: ${WITTY_API_BASE})"
    echo "  - Logs:       /var/log/witty-ub/"
    echo "========================================"
    ;;
*)
    echo "[ERROR] Invalid WITTY_ROLE '${WITTY_ROLE}' (expected: all|backend|frontend)"
    exit 1
    ;;
esac

# Keep container running and forward signals
# Use tail to keep the container alive and capture any background process output
if [ "${WITTY_ROLE}" = "frontend" ]; then
    tail -f /var/log/witty-ub/opencode_server.log &
else
    tail -f /var/log/witty-ub/latency_server.log /var/log/witty-ub/opencode_server.log &
fi
wait
