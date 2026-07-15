#!/bin/bash
# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.
# witty-ub is licensed under the Mulan PSL v2.

set -e

echo "========================================"
echo "Witty-UB Container Startup"
echo "========================================"

# Start nginx for web frontend
echo "[1/4] Starting Nginx web server..."
nginx -c /etc/witty-ub/web/nginx.conf
echo "[OK] Nginx started on port 8080"

# Start OpenCode server first
echo "[2/4] Starting OpenCode server..."
cd /var/witty-ub/latency
export OPENCODE_CONFIG="${OPENCODE_CONFIG:-/var/witty-ub/config/opencode.json}"
export WITTY_UB_PLUGINS_DIR="${WITTY_UB_PLUGINS_DIR:-/var/witty-ub/src/plugins}"
export WITTY_DIR="${WITTY_DIR:-/var/witty-ub}"
nohup /usr/bin/opencode serve --hostname 127.0.0.1 --port 4096 \
    > /var/log/witty-ub/opencode_server.log 2>&1 &
OPENCODE_PID=$!

# Wait for OpenCode server to be ready (reference: run_opencode.sh)
echo "  Waiting for OpenCode server to be ready..."
sleep 1
if ! kill -0 "${OPENCODE_PID}" 2>/dev/null; then
    echo "[ERROR] OpenCode server failed to start. Check /var/log/witty-ub/opencode_server.log"
    exit 1
fi
echo "[OK] OpenCode server started on port 4096"

# Start latency plugin (FastAPI)
echo "[3/4] Starting Latency Plugin..."
/var/witty-ub/latency/.venv/bin/python \
    /var/witty-ub/latency/access/fastapi_server.py \
    > /var/log/witty-ub/latency_server.log 2>&1 &

# Wait for latency plugin to be ready
echo "  Waiting for Latency Plugin to be ready..."
for i in $(seq 1 20); do
    if curl -s http://127.0.0.1:9772/health_check | grep -q "ok"; then
        echo "[OK] Latency Plugin started on port 9772"
        break
    fi
    if [ $i -eq 20 ]; then
        echo "[ERROR] Latency Plugin failed to start. Check /var/log/witty-ub/latency_server.log"
        exit 1
    fi
    sleep 2
done

echo "[4/4] All services started successfully!"
echo "========================================"
echo "  - Web UI:     http://localhost:8080"
echo "  - API:        http://localhost:9772"
echo "  - OpenCode:   http://localhost:4096"
echo "  - Health:     http://localhost:9772/health_check"
echo "  - Logs:       /var/log/witty-ub/"
echo "========================================"

# Keep container running and forward signals
# Use tail to keep the container alive and capture any background process output
tail -f /var/log/witty-ub/latency_server.log /var/log/witty-ub/opencode_server.log &
wait
