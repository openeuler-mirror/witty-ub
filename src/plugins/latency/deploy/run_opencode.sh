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
readonly DEPLOYED_OPENCODE_CONFIG="/var/witty-ub/config/opencode.json"
readonly REPO_ROOT="$(cd "${PLUGINS_DIR}/../.." && pwd)"
readonly LOCAL_OPENCODE_CONFIG="${REPO_ROOT}/config/opencode.json"
readonly OPENCODE_LOG="${LATENCY_PROJECT_DIR}/opencode_server.log"

# Select the configuration that belongs to this script's layout. A stale
# /var/witty-ub installation must not override a source-tree invocation.
if [[ "${LATENCY_PROJECT_DIR}" == "/var/witty-ub/latency" && -f "${DEPLOYED_OPENCODE_CONFIG}" ]]; then
    readonly OPENCODE_CONFIG_PATH="${DEPLOYED_OPENCODE_CONFIG}"
    readonly WITTY_ROOT="/var/witty-ub"
elif [[ -f "${LOCAL_OPENCODE_CONFIG}" ]]; then
    readonly OPENCODE_CONFIG_PATH="${LOCAL_OPENCODE_CONFIG}"
    readonly WITTY_ROOT="${REPO_ROOT}"
else
    echo "[ERROR] OpenCode configuration not found." >&2
    echo "        Checked: ${DEPLOYED_OPENCODE_CONFIG}" >&2
    echo "        Checked: ${LOCAL_OPENCODE_CONFIG}" >&2
    exit 1
fi

readonly AGENT_PROMPT="${WITTY_ROOT}/config/agents/witty-ub-diagnostician.md"
if [[ ! -f "${AGENT_PROMPT}" ]]; then
    echo "[ERROR] Diagnosis agent prompt not found: ${AGENT_PROMPT}" >&2
    exit 1
fi

# Skip installation when a working OpenCode command is already available.
if command -v "${COMMAND_NAME}" >/dev/null 2>&1; then
    echo "[INFO] OpenCode is already installed; skipping installation."
else
    if ! command -v npm >/dev/null 2>&1; then
        echo "[ERROR] npm not found. Please install Node.js and npm first." >&2
        exit 1
    fi

    echo "[INFO] npm found: $(npm --version)"
    echo "[INFO] Installing ${PACKAGE_NAME} globally from ${NPM_REGISTRY}..."
    npm install -g "${PACKAGE_NAME}" --registry="${NPM_REGISTRY}"

    if ! command -v "${COMMAND_NAME}" >/dev/null 2>&1; then
        echo "[ERROR] ${PACKAGE_NAME} was installed, but '${COMMAND_NAME}' is not in PATH." >&2
        echo "        Ensure npm's global bin directory is included in PATH." >&2
        exit 1
    fi
fi

echo "[OK] OpenCode is ready: $(${COMMAND_NAME} --version)"

if ! command -v curl >/dev/null 2>&1; then
    echo "[ERROR] curl not found. The diagnosis agent requires curl to query the backend API." >&2
    exit 1
fi

# Resolve the prompt path in opencode.json for both source and packaged layouts.
export OPENCODE_CONFIG="${OPENCODE_CONFIG_PATH}"
export WITTY_DIR="${WITTY_ROOT}"

echo "[INFO] Validating OpenCode configuration and diagnosis agent..."
if ! "${COMMAND_NAME}" debug agent witty-ub-diagnostician >/dev/null; then
    echo "[ERROR] OpenCode configuration is invalid: ${OPENCODE_CONFIG}" >&2
    exit 1
fi

if curl --silent --fail --max-time 2 --noproxy 127.0.0.1 http://127.0.0.1:4096/global/health >/dev/null 2>&1; then
    echo "[OK] OpenCode server is already running at http://127.0.0.1:4096"
    exit 0
fi

if ! curl --silent --fail --max-time 2 --noproxy 127.0.0.1 http://127.0.0.1:9772/health_check >/dev/null 2>&1; then
    echo "[WARN] Latency backend is not ready at http://127.0.0.1:9772." >&2
    echo "       OpenCode will start, but diagnosis queries will fail until the backend is healthy." >&2
fi

# Start the OpenCode service in the background.
echo "[INFO] Using OpenCode configuration: ${OPENCODE_CONFIG}"
echo "[INFO] Starting OpenCode server at http://127.0.0.1:4096 ..."
nohup "${COMMAND_NAME}" serve --hostname 127.0.0.1 --port 4096 \
    > "${OPENCODE_LOG}" 2>&1 &
OPENCODE_PID=$!

for _ in $(seq 1 20); do
    if curl --silent --fail --max-time 1 --noproxy 127.0.0.1 http://127.0.0.1:4096/global/health >/dev/null 2>&1; then
        echo "[OK] OpenCode server started in the background (PID: ${OPENCODE_PID})."
        echo "     Log: ${OPENCODE_LOG}"
        exit 0
    fi
    if ! kill -0 "${OPENCODE_PID}" 2>/dev/null; then
        break
    fi
    sleep 0.5
done

echo "[ERROR] OpenCode server failed to become healthy at http://127.0.0.1:4096." >&2
echo "        Check ${OPENCODE_LOG}" >&2
exit 1
