#!/bin/bash
# Copyright (c) Huawei Technologies Co., Ltd. 2023-2024. All rights reserved.
# Latency Plugin One-Click Deployment Script

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
VENV_DIR="${PROJECT_DIR}/.venv"
INDEX_URL="https://mirrors.aliyun.com/pypi/simple/"

echo "========================================"
echo "Latency Plugin Deployment"
echo "========================================"

# 1. Check uv
if ! command -v uv &> /dev/null; then
    echo "[ERROR] uv not found. Please install uv first:"
    echo "  curl -LsSf https://astral.sh/uv/install.sh | sh"
    exit 1
fi
echo "[OK] uv found: $(uv --version)"

# 2. Create virtual environment
echo "[Step 1/4] Creating virtual environment at ${VENV_DIR} ..."
if [ -d "$VENV_DIR" ]; then
    echo "  Virtual environment already exists, skipping creation."
else
    # 优先使用系统已安装的 Python，避免从 GitHub 下载
    PYTHON_CMD=""
    for cmd in python3.10 python3 python; do
        if command -v $cmd &> /dev/null; then
            PYTHON_CMD=$cmd
            break
        fi
    done
    
    if [ -z "$PYTHON_CMD" ]; then
        echo "[WARN] No Python found, trying to use uv to download Python 3.10..."
        uv venv "$VENV_DIR" --python python3.10
    else
        echo "  Using system Python: $(which $PYTHON_CMD) ($($PYTHON_CMD --version))"
        $PYTHON_CMD -m venv "$VENV_DIR"
    fi
    echo "[OK] Virtual environment created."
fi

# 3. Install dependencies
echo "[Step 2/4] Installing dependencies from Aliyun mirror ..."
uv pip install --python "${VENV_DIR}/bin/python" \
    --index-url "$INDEX_URL" \
    -r "${SCRIPT_DIR}/requirements.txt"
echo "[OK] Dependencies installed."

# 4. Create necessary directories
echo "[Step 3/4] Creating necessary directories ..."
mkdir -p "${PROJECT_DIR}/latency/file/file_upload"
mkdir -p "${PROJECT_DIR}/latency/file/file_parse_result"
echo "[OK] Directories ready."

# 5. Start service
echo "[Step 4/4] Starting FastAPI service ..."
# Stop existing server if any
pkill -f "latency/access/fastapi_server.py" || true
sleep 1

export PYTHONPATH="${PROJECT_DIR}/..:${PYTHONPATH}"
nohup "${VENV_DIR}/bin/python" "${PROJECT_DIR}/access/fastapi_server.py" \
    > "${PROJECT_DIR}/latency_server.log" 2>&1 &

sleep 3
if curl -s http://127.0.0.1:9772/health_check | grep -q "ok"; then
    echo "[OK] Service started successfully on http://127.0.0.1:9772"
else
    echo "[WARN] Service may not have started correctly. Check ${PROJECT_DIR}/latency_server.log"
    exit 1
fi

echo "========================================"
echo "Deployment completed!"
echo "  - API:     http://127.0.0.1:9772"
echo "  - Health:  http://127.0.0.1:9772/health_check"
echo "  - Log:     ${PROJECT_DIR}/latency_server.log"
echo "========================================"
