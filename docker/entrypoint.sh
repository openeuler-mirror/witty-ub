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
# WITTY_ROLE: all（默认，单容器 All-in-One）| backend（仅 FastAPI）| frontend（Nginx+OpenCode+experience-skill）
export WITTY_ROLE="${WITTY_ROLE:-all}"
# Nginx 反代上游
export WITTY_BACKEND_URL="${WITTY_BACKEND_URL:-http://127.0.0.1:9772}"
export WITTY_AGENT_URL="${WITTY_AGENT_URL:-http://127.0.0.1:4096}"
# Agent 提示词中的后端基址；frontend 角色默认跟随 WITTY_BACKEND_URL
export WITTY_API_BASE="${WITTY_API_BASE:-$WITTY_BACKEND_URL}"
export WITTY_NO_PROXY="${WITTY_NO_PROXY:-127.0.0.1}"
# Remote MCP endpoint used by the bundled OpenCode configuration. Docker
# deployments resolve witty-rag-core through a shared Docker network.
export WITTY_RAG_MCP_URL="${WITTY_RAG_MCP_URL:-http://witty-rag-core:12312/sse}"
# OpenCode 绑定地址（兜底落位 B 需改为 0.0.0.0）
export OPENCODE_HOST="${OPENCODE_HOST:-127.0.0.1}"
# 诊断报告落盘根目录（由 witty-ub-reports 卷持久化；agent 子进程继承此变量）
export WITTY_REPORT_DIR="${WITTY_REPORT_DIR:-${WITTY_DIR}/reports}"
# 内置定界报告：镜像内的只读种子 → 独立卷中的生效副本，按压缩包哈希判断是否重载
export WITTY_BUILTIN_REPORTS="${WITTY_BUILTIN_REPORTS:-1}"
export WITTY_BUILTIN_REPORT_ARCHIVE="${WITTY_BUILTIN_REPORT_ARCHIVE:-/usr/share/witty-ub/builtin-reports/reports.zip}"
export WITTY_BUILTIN_REPORT_DIR="${WITTY_BUILTIN_REPORT_DIR:-${WITTY_DIR}/builtin-reports}"
export WITTY_BUILTIN_REPORT_OPERATOR="${WITTY_BUILTIN_REPORT_OPERATOR:-builtin-reports}"

# ── OpenCode/LLM 出网 HTTPS 证书校验（WITTY_SSL_VERIFY=false 时关闭） ──
# 内网自签证书/代理拦截会导致 OpenCode 调 LLM 报证书错误；无法导入 CA 时可设为 false。
# OpenCode 是 Node 应用，关闭校验通过 NODE_TLS_REJECT_UNAUTHORIZED=0（须在启动前导出）
export WITTY_SSL_VERIFY="${WITTY_SSL_VERIFY:-true}"
case "$WITTY_SSL_VERIFY" in
false | False | FALSE | 0 | no | NO)
    export NODE_TLS_REJECT_UNAUTHORIZED=0
    echo "[WARN] WITTY_SSL_VERIFY=${WITTY_SSL_VERIFY}: HTTPS certificate verification for OpenCode/LLM calls is DISABLED"
    ;;
*) ;;
esac

echo "Role: ${WITTY_ROLE}  Backend: ${WITTY_BACKEND_URL}  Agent: ${WITTY_AGENT_URL}  SSL verify: ${WITTY_SSL_VERIFY}"

# Docker 部署通过只读 bind mount / Compose secret 传入口令，避免将密码
# 写入镜像配置或 docker inspect 可见的容器环境配置。只在后端角色中加载。
load_pg_secret() {
    [ "$WITTY_ROLE" = "frontend" ] && return 0
    local secret_file="${PG_SECRET_FILE:-/run/secrets/pg_password}"
    if [ -z "${PG_PASSWORD:-}" ]; then
        if [ ! -r "$secret_file" ]; then
            echo "[ERROR] PostgreSQL secret is missing or unreadable: ${secret_file}"
            exit 1
        fi
        PG_PASSWORD="$(tr -d '\r\n' <"$secret_file")"
        if [ -z "$PG_PASSWORD" ]; then
            echo "[ERROR] PostgreSQL secret is empty: ${secret_file}"
            exit 1
        fi
        export PG_PASSWORD
    fi
}

load_pg_secret

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

    # Sync case library (similarity analysis / case management)
    # 先删除旧 case 文件再拷贝，确保删除的案例不残留（cp 只增不删会导致旧案例污染）
    local CASE_SEED_DIR="/usr/share/witty-ub/case"
    local CASE_RUNTIME_DIR="${WITTY_DIR}/case"
    mkdir -p "${CASE_RUNTIME_DIR}"
    if [ -d "${CASE_SEED_DIR}" ]; then
        echo "Syncing case library..."
        rm -f "${CASE_RUNTIME_DIR}"/*.json 2>/dev/null || true
        cp -a "${CASE_SEED_DIR}/." "${CASE_RUNTIME_DIR}/"
        echo "[OK] Case library synced: $(find "${CASE_RUNTIME_DIR}" -name '*.json' | wc -l) files"
    fi
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

# Agent 提示词保持原文，WITTY_API_BASE / WITTY_NO_PROXY 由 Bash 执行时展开。
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

# ── experience-skill（all / frontend 角色） ──────────────────────────────
# 和 RPM 服务一致：直接使用构建时安装的 venv，容器启动时不下载依赖。
start_experience() {
    local scripts="${WITTY_DIR}/witty_ub_diagnostician/.opencode/skills/experience-skill/scripts"
    local python="${scripts}/.venv/bin/python"
    local log="/var/log/witty-ub/experience_server.log"
    if [ ! -x "$python" ]; then
        echo "[ERROR] experience-skill venv is missing: ${python}. Rebuild the image."
        return 1
    fi
    mkdir -p /var/log/witty-ub
    echo "Syncing experience library..."
    if ! (
        cd "$scripts"
        export PYTHONPATH="${scripts}/src${PYTHONPATH:+:${PYTHONPATH}}"
        exec "$python" -m experience_skill_cli.cli sync
    ) >"$log" 2>&1; then
        echo "[ERROR] Experience library sync failed. Check ${log}"
        return 1
    fi

    echo "Starting experience-skill web server..."
    (
        cd "$scripts"
        export PYTHONPATH="${scripts}/src${PYTHONPATH:+:${PYTHONPATH}}"
        exec "$python" -m experience_skill_cli.cli web --host 127.0.0.1 --port 8082 --no-browser
    ) >>"$log" 2>&1 &
    EXPERIENCE_PID=$!

    echo "  Waiting for Skill/Wiki management APIs through Nginx..."
    for i in $(seq 1 30); do
        if ! kill -0 "$EXPERIENCE_PID" 2>/dev/null; then
            echo "[ERROR] experience-skill web server exited. Check ${log}"
            return 1
        fi
        if /healthcheck.sh --experience; then
            echo "[OK] Skill/Wiki management APIs are ready (8080 -> 8082)"
            return 0
        fi
        sleep 2
    done
    echo "[ERROR] Skill/Wiki management APIs failed their health check. Check ${log} and /var/log/witty-ub-web/error.log"
    return 1
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

# ── 内置定界报告（all / backend 角色） ──────────────────────────────
# 镜像内种子是只读的；独立卷中的 reports.zip 才是生效副本。每次启动比对哈希，
# 新镜像换了压缩包就替换并重新导入；导入在后台执行，失败只记日志，不阻塞启动。
sync_builtin_reports() {
    [ "${WITTY_BUILTIN_REPORTS}" = "0" ] && return 0
    local seed="${WITTY_BUILTIN_REPORT_ARCHIVE}"
    if [ ! -f "$seed" ]; then
        echo "[INFO] Built-in report archive not packaged: ${seed}"
        return 0
    fi
    local dir="${WITTY_BUILTIN_REPORT_DIR}"
    local active="${dir}/reports.zip"
    local state="${dir}/import-state.json"
    mkdir -p "$dir"
    local seed_sum active_sum=""
    seed_sum="$(sha256sum "$seed" | awk '{print $1}')"
    [ -f "$active" ] && active_sum="$(sha256sum "$active" | awk '{print $1}')"
    if [ "$seed_sum" != "$active_sum" ]; then
        echo "[OK] Built-in report archive updated (${seed_sum:0:12})"
        cp -f "$seed" "${active}.tmp" && mv -f "${active}.tmp" "$active"
    fi
    echo "Importing built-in reports in background (state: ${state})"
    (
        export PYTHONPATH="${WITTY_DIR}${PYTHONPATH:+:${PYTHONPATH}}"
        exec "${WITTY_DIR}/latency/.venv/bin/python" \
            -m latency.access.builtin_reports_cli \
            --archive "$active" --state "$state" \
            --operator "${WITTY_BUILTIN_REPORT_OPERATOR}"
    ) >>/var/log/witty-ub/builtin_report_import.log 2>&1 &
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
    # 使用原始 Agent 提示词；其 Bash 命令在执行时展开已导出的环境变量。
    detect_agent_layout
    cd /var/witty-ub
    export OPENCODE_CONFIG="${OPENCODE_CONFIG:-${AGENT_OPENCODE_CONFIG}}"
    # Standard .opencode layout dir for agents/skills/commands discovery;
    # a user-provided OPENCODE_CONFIG_DIR always wins.
    export OPENCODE_CONFIG_DIR="${OPENCODE_CONFIG_DIR:-$(cd "$(dirname "${AGENT_OPENCODE_CONFIG}")" && pwd)}"
    # 卷首次挂载为空目录，这里先建好报告根目录，保证 agent 渲染时可直接写盘。
    mkdir -p "${WITTY_REPORT_DIR}"
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

# 清理后台服务，也覆盖启动检查失败导致的退出；experience 子进程通过 exec 接收信号。
trap 'kill $(jobs -p) 2>/dev/null || true' EXIT
trap 'exit 0' SIGTERM SIGINT

case "${WITTY_ROLE}" in
all)
    sync_backend_data
    start_nginx
    start_experience
    start_backend
    sync_builtin_reports
    # OpenCode queries the latency HTTP API directly, so start it only
    # after the backend is healthy.
    start_opencode
    echo "All services started successfully!"
    echo "========================================"
    echo "  - Web UI:     http://localhost:8080"
    echo "  - API:        http://localhost:9772"
    echo "  - OpenCode:   http://localhost:4096"
    echo "  - Skill/Wiki: http://localhost:8080/experience_api/experiences"
    echo "  - Health:     http://localhost:9772/health_check"
    echo "  - Logs:       /var/log/witty-ub/"
    echo "========================================"
    ;;
backend)
    sync_backend_data
    start_backend
    sync_builtin_reports
    echo "Backend-only container started successfully!"
    echo "========================================"
    echo "  - API:        http://0.0.0.0:9772"
    echo "  - Health:     http://localhost:9772/health_check"
    echo "  - Logs:       /var/log/witty-ub/"
    echo "========================================"
    ;;
frontend)
    start_nginx
    start_experience
    wait_backend_ready
    start_opencode
    echo "Frontend-only container started successfully!"
    echo "========================================"
    echo "  - Web UI:     http://localhost:8080"
    echo "  - Backend:    ${WITTY_BACKEND_URL}"
    echo "  - OpenCode:   http://localhost:4096 (agent API base: ${WITTY_API_BASE})"
    echo "  - Skill/Wiki: http://localhost:8080/experience_api/experiences"
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
    tail -f /var/log/witty-ub/opencode_server.log /var/log/witty-ub/experience_server.log &
elif [ "${WITTY_ROLE}" = "backend" ]; then
    tail -f /var/log/witty-ub/latency_server.log &
else
    tail -f /var/log/witty-ub/latency_server.log /var/log/witty-ub/opencode_server.log /var/log/witty-ub/experience_server.log &
fi
wait
