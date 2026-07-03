#!/usr/bin/env bash
# Copyright (c) Huawei Technologies Co., Ltd. 2023-2024. All rights reserved.
#
# OpenCode installation and deployment script.
# This script is intended for users who do not already have an OpenCode
# service deployed. It installs OpenCode when necessary and starts a local
# OpenCode service on 127.0.0.1:4096.

set -euo pipefail

readonly PACKAGE_NAME="opencode-ai"
readonly COMMAND_NAME="opencode"
readonly NPM_REGISTRY="https://mirrors.huaweicloud.com/repository/npm/"
readonly SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
readonly LATENCY_PROJECT_DIR="$(dirname "${SCRIPT_DIR}")"
readonly PLUGINS_DIR="$(dirname "${LATENCY_PROJECT_DIR}")"
readonly VENV_PYTHON="${LATENCY_PROJECT_DIR}/.venv/bin/python"

# Skip installation when a working OpenCode command is already available.
if "${COMMAND_NAME}" -v >/dev/null 2>&1; then
    echo "[INFO] OpenCode is already installed; skipping installation."
else
    if ! command -v npm >/dev/null 2>&1; then
        echo "[ERROR] npm not found. Please install Node.js and npm first." >&2
        exit 1
    fi

    echo "[INFO] npm found: $(npm --version)"
    echo "[INFO] Installing ${PACKAGE_NAME} globally from ${NPM_REGISTRY}..."
    npm install -g "${PACKAGE_NAME}" --registry="${NPM_REGISTRY}"

    if ! "${COMMAND_NAME}" -v >/dev/null 2>&1; then
        echo "[ERROR] ${PACKAGE_NAME} was installed, but '${COMMAND_NAME}' is not in PATH." >&2
        echo "        Ensure npm's global bin directory is included in PATH." >&2
        exit 1
    fi
fi

echo "[OK] OpenCode is ready: $(${COMMAND_NAME} -v)"

# Pass dynamically resolved Python paths to opencode.json.
export WITTY_UB_LATENCY_PYTHON="${VENV_PYTHON}"
export WITTY_UB_PLUGINS_DIR="${PLUGINS_DIR}"

# Start the OpenCode service in the background.
echo "[INFO] Starting OpenCode server at http://127.0.0.1:4096 ..."
nohup "${COMMAND_NAME}" serve --hostname 127.0.0.1 --port 4096 \
    > "${LATENCY_PROJECT_DIR}/opencode_server.log" 2>&1 &
OPENCODE_PID=$!

sleep 1
if ! kill -0 "${OPENCODE_PID}" 2>/dev/null; then
    echo "[ERROR] OpenCode server failed to start." >&2
    echo "        Check ${LATENCY_PROJECT_DIR}/opencode_server.log" >&2
    exit 1
fi

echo "[OK] OpenCode server started in the background (PID: ${OPENCODE_PID})."
echo "     Log: ${LATENCY_PROJECT_DIR}/opencode_server.log"
