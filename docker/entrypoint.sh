#!/bin/bash
# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.
# witty-ub is licensed under the Mulan PSL v2.

set -e

echo "========================================"
echo "Witty-UB Container Startup"
echo "========================================"

# Start nginx for web frontend
echo "[1/3] Starting Nginx web server..."
nginx -c /etc/witty-ub/web/nginx.conf
echo "[OK] Nginx started on port 8080"

# Start latency plugin (FastAPI)
echo "[2/3] Starting Latency Plugin..."
cd /var/witty-ub/latency
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

echo "[3/3] All services started successfully!"
echo "========================================"
echo "  - Web UI:     http://localhost:8080"
echo "  - API:        http://localhost:9772"
echo "  - Health:     http://localhost:9772/health_check"
echo "  - Logs:       /var/log/witty-ub/"
echo "========================================"

# Keep container running and forward signals
# Use tail to keep the container alive and capture any background process output
tail -f /var/log/witty-ub/latency_server.log &
wait
