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
readonly DEPLOYED_OPENCODE_CONFIG="/var/witty-ub/witty_ub_diagnostician/.opencode/opencode.json"
readonly REPO_ROOT="$(cd "${PLUGINS_DIR}/../.." && pwd)"
readonly LOCAL_OPENCODE_CONFIG="${REPO_ROOT}/witty_ub_diagnostician/opencode.json"
readonly OPENCODE_LOG="${LATENCY_PROJECT_DIR}/opencode_server.log"

# Select the configuration that belongs to this script's layout. A stale
# /var/witty-ub installation must not override a source-tree invocation.
if [[ "${LATENCY_PROJECT_DIR}" == "/var/witty-ub/latency" && -f "${DEPLOYED_OPENCODE_CONFIG}" ]]; then
    readonly OPENCODE_CONFIG_PATH="${DEPLOYED_OPENCODE_CONFIG}"
    readonly WITTY_ROOT="/var/witty-ub"
    readonly AGENT_PROMPT="${WITTY_ROOT}/witty_ub_diagnostician/.opencode/agents/witty-ub-diagnostician.md"
elif [[ -f "${LOCAL_OPENCODE_CONFIG}" ]]; then
    readonly OPENCODE_CONFIG_PATH="${LOCAL_OPENCODE_CONFIG}"
    readonly WITTY_ROOT="${REPO_ROOT}"
    readonly AGENT_PROMPT="${WITTY_ROOT}/witty_ub_diagnostician/agents/witty-ub-diagnostician.md"
else
    echo "[ERROR] OpenCode configuration not found." >&2
    echo "        Checked: ${DEPLOYED_OPENCODE_CONFIG}" >&2
    echo "        Checked: ${LOCAL_OPENCODE_CONFIG}" >&2
    exit 1
fi

if [[ ! -f "${AGENT_PROMPT}" ]]; then
    echo "[ERROR] Diagnosis agent prompt not found: ${AGENT_PROMPT}" >&2
    exit 1
fi

# ── 前后端分离部署: Agent 访问的后端基址与监听地址可参数化 ──
WITTY_API_BASE="${WITTY_API_BASE:-http://127.0.0.1:9772}"
WITTY_NO_PROXY="${WITTY_NO_PROXY:-127.0.0.1}"
OPENCODE_HOST="${OPENCODE_HOST:-127.0.0.1}"

# 渲染提示词中的占位符 (幂等: 已渲染内容不含占位符)。
# /var 下的部署副本归 root 所有, 无写权限时借助 sudo。
RENDER_SUDO=""
[[ -w "${AGENT_PROMPT}" ]] || RENDER_SUDO="sudo"
if ${RENDER_SUDO} sed -i \
    -e "s|\${WITTY_API_BASE}|${WITTY_API_BASE}|g" \
    -e "s|\${WITTY_NO_PROXY}|${WITTY_NO_PROXY}|g" \
    "${AGENT_PROMPT}" 2>/dev/null; then
    echo "[INFO] Agent prompt API base: ${WITTY_API_BASE}"
else
    echo "[WARN] Failed to render agent prompt placeholders: ${AGENT_PROMPT}" >&2
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

if ! curl --silent --fail --max-time 2 --noproxy '*' "${WITTY_API_BASE}/health_check" >/dev/null 2>&1; then
    echo "[WARN] Latency backend is not ready at ${WITTY_API_BASE}." >&2
    echo "       OpenCode will start, but diagnosis queries will fail until the backend is healthy." >&2
fi

# Start the OpenCode service in the background.
echo "[INFO] Using OpenCode configuration: ${OPENCODE_CONFIG}"
echo "[INFO] Starting OpenCode server at http://${OPENCODE_HOST}:4096 ..."
nohup "${COMMAND_NAME}" serve --hostname "${OPENCODE_HOST}" --port 4096 \
    >"${OPENCODE_LOG}" 2>&1 &
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
