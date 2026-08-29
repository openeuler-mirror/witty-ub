#!/bin/bash
# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.
# witty-ub is licensed under the Mulan PSL v2.

set -e

echo "========================================"
echo "Witty-UB Container Startup"
echo "========================================"

export WITTY_DIR="${WITTY_DIR:-/var/witty-ub}"
export WITTY_INSTALL_PATH="${WITTY_INSTALL_PATH:-/usr/bin}"

# Refresh packaged rules on every start. Docker only initializes a named
# volume from the image on its first use, so an existing witty-ub-data volume
# would otherwise miss rules added by a newer image.
echo "[1/5] Syncing packaged diagnosis data..."
WITTY_DATA_SEED_DIR="/usr/share/witty-ub/data"
WITTY_RUNTIME_DATA_DIR="${WITTY_DIR}/data"
mkdir -p "${WITTY_RUNTIME_DATA_DIR}"
cp -a "${WITTY_DATA_SEED_DIR}/." "${WITTY_RUNTIME_DATA_DIR}/"

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

# Start nginx for web frontend
echo "[2/5] Starting Nginx web server..."
nginx -c /etc/witty-ub/web/nginx.conf
echo "[OK] Nginx started on port 8080"

# Start latency plugin (FastAPI)
echo "[3/5] Starting Latency Plugin..."
/var/witty-ub/latency/.venv/bin/python \
    /var/witty-ub/latency/access/fastapi_server.py \
    > /var/log/witty-ub/latency_server.log 2>&1 &

# Wait for latency plugin to be ready
echo "  Waiting for Latency Plugin to be ready..."
for i in $(seq 1 20); do
    if curl -s --noproxy 127.0.0.1 http://127.0.0.1:9772/health_check | grep -q "ok"; then
        echo "[OK] Latency Plugin started on port 9772"
        break
    fi
    if [ $i -eq 20 ]; then
        echo "[ERROR] Latency Plugin failed to start. Check /var/log/witty-ub/latency_server.log"
        exit 1
    fi
    sleep 2
done

# OpenCode queries the latency HTTP API directly, so start it only after the
# backend is healthy.
echo "[4/5] Starting OpenCode server..."
cd /var/witty-ub
export OPENCODE_CONFIG="${OPENCODE_CONFIG:-/var/witty-ub/witty_ub_diagnosticain/.opencode/opencode.json}"
nohup /usr/bin/opencode serve --hostname 127.0.0.1 --port 4096 \
    > /var/log/witty-ub/opencode_server.log 2>&1 &
OPENCODE_PID=$!

echo "  Waiting for OpenCode server to be ready..."
for i in $(seq 1 20); do
    if curl -s --max-time 3 --noproxy 127.0.0.1 http://127.0.0.1:4096/global/health | grep -q 'healthy'; then
        echo "[OK] OpenCode server started on port 4096"
        break
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

echo "[5/5] All services started successfully!"
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
