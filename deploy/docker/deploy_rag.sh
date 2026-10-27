#!/bin/bash
# Deploy the openGauss database and witty-rag-core used by Witty-UB.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
CONF_FILE="${SCRIPT_DIR}/../deploy.conf"

log_info()  { echo "[INFO]  $*"; }
log_ok()    { echo "[OK]    $*"; }
log_warn()  { echo "[WARN]  $*"; }
log_error() { echo "[ERROR] $*" >&2; }

# Environment values take precedence over deploy.conf.
_ENV_RAG_CONFIG_FILE="${RAG_CONFIG_FILE:-}"
_ENV_RAG_RUNTIME_DIR="${RAG_RUNTIME_DIR:-}"
_ENV_RAG_RERANK_MODEL_API_KEY_SECRET_FILE="${RAG_RERANK_MODEL_API_KEY_SECRET_FILE:-}"
_ENV_RAG_DB_SECRET_FILE="${RAG_DB_SECRET_FILE:-}"
_ENV_RAG_ACCESS_KEY_SECRET_FILE="${RAG_ACCESS_KEY_SECRET_FILE:-}"
_ENV_RAG_MODEL_API_KEY_SECRET_FILE="${RAG_MODEL_API_KEY_SECRET_FILE:-}"
_ENV_RAG_EMBEDDING_MODEL_NAME="${RAG_EMBEDDING_MODEL_NAME:-}"
_ENV_RAG_EMBEDDING_MODEL_PROVIDER="${RAG_EMBEDDING_MODEL_PROVIDER:-}"
_ENV_RAG_EMBEDDING_ENDPOINT="${RAG_EMBEDDING_ENDPOINT:-}"
_ENV_RAG_EMBEDDING_API_KEY="${RAG_EMBEDDING_API_KEY:-}"
_ENV_RAG_EMBEDDING_DIMENSION="${RAG_EMBEDDING_DIMENSION:-}"
_ENV_RAG_RERANK_ENABLED="${RAG_RERANK_ENABLED:-}"
_ENV_RAG_RERANK_MODEL_NAME="${RAG_RERANK_MODEL_NAME:-}"
_ENV_RAG_RERANK_MODEL_PROVIDER="${RAG_RERANK_MODEL_PROVIDER:-}"
_ENV_RAG_RERANK_ENDPOINT="${RAG_RERANK_ENDPOINT:-}"
_ENV_OPENGAUSS_RAG_IMAGE="${OPENGAUSS_RAG_IMAGE:-}"
_ENV_WITTY_RAG_CORE_IMAGE="${WITTY_RAG_CORE_IMAGE:-}"
_ENV_WITTY_RAG_MCP_IMAGE="${WITTY_RAG_MCP_IMAGE:-}"
_ENV_WITTY_NETWORK="${WITTY_NETWORK:-}"

if [ -f "$CONF_FILE" ]; then
    # shellcheck disable=SC1090
    source "$CONF_FILE"
fi

[ -n "$_ENV_RAG_CONFIG_FILE" ] && RAG_CONFIG_FILE="$_ENV_RAG_CONFIG_FILE"
[ -n "$_ENV_RAG_RUNTIME_DIR" ] && RAG_RUNTIME_DIR="$_ENV_RAG_RUNTIME_DIR"
[ -n "$_ENV_RAG_RERANK_MODEL_API_KEY_SECRET_FILE" ] && RAG_RERANK_MODEL_API_KEY_SECRET_FILE="$_ENV_RAG_RERANK_MODEL_API_KEY_SECRET_FILE"
[ -n "$_ENV_RAG_DB_SECRET_FILE" ] && RAG_DB_SECRET_FILE="$_ENV_RAG_DB_SECRET_FILE"
[ -n "$_ENV_RAG_ACCESS_KEY_SECRET_FILE" ] && RAG_ACCESS_KEY_SECRET_FILE="$_ENV_RAG_ACCESS_KEY_SECRET_FILE"
[ -n "$_ENV_RAG_MODEL_API_KEY_SECRET_FILE" ] && RAG_MODEL_API_KEY_SECRET_FILE="$_ENV_RAG_MODEL_API_KEY_SECRET_FILE"
[ -n "$_ENV_RAG_EMBEDDING_MODEL_NAME" ] && RAG_EMBEDDING_MODEL_NAME="$_ENV_RAG_EMBEDDING_MODEL_NAME"
[ -n "$_ENV_RAG_EMBEDDING_MODEL_PROVIDER" ] && RAG_EMBEDDING_MODEL_PROVIDER="$_ENV_RAG_EMBEDDING_MODEL_PROVIDER"
[ -n "$_ENV_RAG_EMBEDDING_ENDPOINT" ] && RAG_EMBEDDING_ENDPOINT="$_ENV_RAG_EMBEDDING_ENDPOINT"
[ -n "$_ENV_RAG_EMBEDDING_API_KEY" ] && RAG_EMBEDDING_API_KEY="$_ENV_RAG_EMBEDDING_API_KEY"
[ -n "$_ENV_RAG_EMBEDDING_DIMENSION" ] && RAG_EMBEDDING_DIMENSION="$_ENV_RAG_EMBEDDING_DIMENSION"
[ -n "$_ENV_RAG_RERANK_ENABLED" ] && RAG_RERANK_ENABLED="$_ENV_RAG_RERANK_ENABLED"
[ -n "$_ENV_RAG_RERANK_MODEL_NAME" ] && RAG_RERANK_MODEL_NAME="$_ENV_RAG_RERANK_MODEL_NAME"
[ -n "$_ENV_RAG_RERANK_MODEL_PROVIDER" ] && RAG_RERANK_MODEL_PROVIDER="$_ENV_RAG_RERANK_MODEL_PROVIDER"
[ -n "$_ENV_RAG_RERANK_ENDPOINT" ] && RAG_RERANK_ENDPOINT="$_ENV_RAG_RERANK_ENDPOINT"
[ -n "$_ENV_OPENGAUSS_RAG_IMAGE" ] && OPENGAUSS_RAG_IMAGE="$_ENV_OPENGAUSS_RAG_IMAGE"
[ -n "$_ENV_WITTY_RAG_CORE_IMAGE" ] && WITTY_RAG_CORE_IMAGE="$_ENV_WITTY_RAG_CORE_IMAGE"
[ -n "$_ENV_WITTY_RAG_MCP_IMAGE" ] && WITTY_RAG_MCP_IMAGE="$_ENV_WITTY_RAG_MCP_IMAGE"
[ -n "$_ENV_WITTY_NETWORK" ] && WITTY_NETWORK="$_ENV_WITTY_NETWORK"
unset _ENV_RAG_CONFIG_FILE _ENV_RAG_RUNTIME_DIR _ENV_RAG_RERANK_MODEL_API_KEY_SECRET_FILE _ENV_RAG_DB_SECRET_FILE _ENV_RAG_ACCESS_KEY_SECRET_FILE _ENV_RAG_MODEL_API_KEY_SECRET_FILE _ENV_OPENGAUSS_RAG_IMAGE \
    _ENV_RAG_EMBEDDING_MODEL_NAME _ENV_RAG_EMBEDDING_MODEL_PROVIDER _ENV_RAG_EMBEDDING_ENDPOINT \
    _ENV_RAG_EMBEDDING_API_KEY _ENV_RAG_EMBEDDING_DIMENSION _ENV_RAG_RERANK_ENABLED \
    _ENV_RAG_RERANK_MODEL_NAME _ENV_RAG_RERANK_MODEL_PROVIDER _ENV_RAG_RERANK_ENDPOINT \
    _ENV_WITTY_RAG_CORE_IMAGE _ENV_WITTY_RAG_MCP_IMAGE _ENV_WITTY_NETWORK

WITTY_NETWORK="${WITTY_NETWORK:-${PG_NETWORK:-witty-ub-network}}"
OPENGAUSS_RAG_CONTAINER="${OPENGAUSS_RAG_CONTAINER:-opengauss-rag}"
if [ -z "${OPENGAUSS_RAG_IMAGE:-}" ]; then
    LOCAL_HNSW_IMAGE="swr.cn-north-4.myhuaweicloud.com/kunpeng-ai/opengauss:7.0.0-RC3-hnsw"
    if command -v docker >/dev/null 2>&1 && docker image inspect "$LOCAL_HNSW_IMAGE" >/dev/null 2>&1; then
        OPENGAUSS_RAG_IMAGE="$LOCAL_HNSW_IMAGE"
        log_info "复用本地 openGauss HNSW 镜像: ${OPENGAUSS_RAG_IMAGE}"
    else
        case "$(uname -m)" in
            x86_64|amd64)
                OPENGAUSS_RAG_IMAGE="hub-harbor.oepkgs.net/neocopilot/opengauss@sha256:4fd44608ca3571d3ceb5bc2bc5cbcde131dde2ed2b8068ff3f58effc8c60d885"
                ;;
            aarch64|arm64)
                OPENGAUSS_RAG_IMAGE="hub-harbor.oepkgs.net/neocopilot/opengauss@sha256:38a63d58b2b41e3668cde9f9588a74cb4e8aee76b301f7feb86d6a49d871f10c"
                ;;
            *)
                log_error "不支持的宿主机架构: $(uname -m)；请在 deploy.conf 中显式设置 OPENGAUSS_RAG_IMAGE"
                exit 1
                ;;
        esac
    fi
    unset LOCAL_HNSW_IMAGE
fi
OPENGAUSS_RAG_HOST_PORT="${OPENGAUSS_RAG_HOST_PORT:-5440}"
OPENGAUSS_RAG_VOLUME="${OPENGAUSS_RAG_VOLUME:-opengauss-rag-data}"
RAG_DB_USER="${RAG_DB_USER:-gaussdb}"
RAG_DB_NAME="${RAG_DB_NAME:-postgres}"
RAG_DB_SECRET_FILE="${RAG_DB_SECRET_FILE:-/etc/witty-ub/rag-opengauss.passwd}"
RAG_ACCESS_KEY_SECRET_FILE="${RAG_ACCESS_KEY_SECRET_FILE:-/etc/witty-ub/rag-secrets/access-key}"
RAG_ACCESS_KEY_SECRET_DIR="$(dirname "$RAG_ACCESS_KEY_SECRET_FILE")"
RAG_MODEL_API_KEY_SECRET_FILE="${RAG_MODEL_API_KEY_SECRET_FILE:-/etc/witty-ub/rag-secrets/model-api-key}"
RAG_EMBEDDING_MODEL_NAME="${RAG_EMBEDDING_MODEL_NAME:-BAAI/bge-m3}"
RAG_EMBEDDING_MODEL_PROVIDER="${RAG_EMBEDDING_MODEL_PROVIDER:-openai}"
RAG_EMBEDDING_ENDPOINT="${RAG_EMBEDDING_ENDPOINT:-https://api.siliconflow.cn/v1/embeddings}"
# 向量维度上限；不低于所选模型的实际维度，超过该值写入会失败，改变维度必须重建索引。
RAG_EMBEDDING_DIMENSION="${RAG_EMBEDDING_DIMENSION:-1024}"
# rerank 默认关闭：多数模型厂商已不再提供 rerank 服务，开启需显式指定端点。
RAG_RERANK_ENABLED="${RAG_RERANK_ENABLED:-0}"
RAG_RERANK_MODEL_NAME="${RAG_RERANK_MODEL_NAME:-BAAI/bge-reranker-v2-m3}"
RAG_RERANK_MODEL_PROVIDER="${RAG_RERANK_MODEL_PROVIDER:-guijiliudong}"
RAG_RERANK_ENDPOINT="${RAG_RERANK_ENDPOINT:-https://api.siliconflow.cn/v1/rerank}"

WITTY_RAG_CORE_CONTAINER="${WITTY_RAG_CORE_CONTAINER:-witty-rag-core}"
if [ -z "${WITTY_RAG_CORE_IMAGE:-}" ]; then
    case "$(uname -m)" in
        x86_64|amd64) WITTY_RAG_CORE_IMAGE="hub-harbor.oepkgs.net/neocopilot/witty-rag-core:0.10.2-release-x86" ;;
        *) WITTY_RAG_CORE_IMAGE="hub-harbor.oepkgs.net/neocopilot/witty-rag-core:0.10.2-release-arm" ;;
    esac
fi
WITTY_RAG_MCP_IMAGE="${WITTY_RAG_MCP_IMAGE:-hub-harbor.oepkgs.net/neocopilot/witty-rag-core:mcp}"
WITTY_RAG_CORE_HOST_PORT="${WITTY_RAG_CORE_HOST_PORT:-9990}"
RAG_WORKERS="${RAG_WORKERS:-4}"
RAG_CONFIG_FILE="${RAG_CONFIG_FILE:-${SCRIPT_DIR}/../rag-core.toml}"
RAG_RUNTIME_DIR="${RAG_RUNTIME_DIR:-/opt/witty-rag}"
RAG_RUNTIME_CONFIG="${RAG_RUNTIME_DIR}/config/config.toml"
RAG_LOG_DIR="${RAG_RUNTIME_DIR}/logs"

if ! command -v docker >/dev/null 2>&1 || ! docker info >/dev/null 2>&1; then
    log_error "Docker 不可用，请先安装并启动 Docker。"
    exit 1
fi
if ! command -v python3 >/dev/null 2>&1; then
    log_error "需要 python3 来安全生成 RAG 运行配置。"
    exit 1
fi
if [ ! -f "$RAG_CONFIG_FILE" ]; then
    log_error "RAG 配置不存在: ${RAG_CONFIG_FILE}"
    log_error "请在 ${SCRIPT_DIR}/../rag-core.toml 中补齐模型配置。"
    exit 1
fi
if [ ! -s "$RAG_DB_SECRET_FILE" ]; then
    log_error "openGauss 密码文件不存在或为空: ${RAG_DB_SECRET_FILE}"
    log_error "请创建该文件并执行 chmod 600 ${RAG_DB_SECRET_FILE}"
    exit 1
fi
chmod 0600 "$RAG_DB_SECRET_FILE" 2>/dev/null || true
# API Key 可选：本地 OpenAI 兼容服务通常无鉴权，或使用任意短口令。
RAG_EMBEDDING_API_KEY="${RAG_EMBEDDING_API_KEY:-}"
if [ -z "$RAG_EMBEDDING_API_KEY" ] && [ -s "$RAG_MODEL_API_KEY_SECRET_FILE" ]; then
    RAG_EMBEDDING_API_KEY="$(tr -d '\r\n' <"$RAG_MODEL_API_KEY_SECRET_FILE")"
fi
if [ -z "$RAG_EMBEDDING_API_KEY" ]; then
    log_warn "未提供 embedding API Key，将按无鉴权服务连接 ${RAG_EMBEDDING_ENDPOINT}"
fi
mkdir -p "$RAG_ACCESS_KEY_SECRET_DIR"
chmod 0700 "$RAG_ACCESS_KEY_SECRET_DIR"

if ! docker network inspect "$WITTY_NETWORK" >/dev/null 2>&1; then
    docker network create "$WITTY_NETWORK" >/dev/null
    log_ok "已创建网络 ${WITTY_NETWORK}"
fi
docker volume inspect "$OPENGAUSS_RAG_VOLUME" >/dev/null 2>&1 || \
    docker volume create "$OPENGAUSS_RAG_VOLUME" >/dev/null

ensure_image() {
    local image="$1"
    if ! docker image inspect "$image" >/dev/null 2>&1; then
        log_info "拉取镜像 ${image}"
        docker pull "$image"
    fi
}

connect_network() {
    local container="$1"
    if ! docker inspect "$container" --format '{{json .NetworkSettings.Networks}}' | grep -q "\"${WITTY_NETWORK}\""; then
        docker network connect "$WITTY_NETWORK" "$container"
    fi
}

ensure_image "$OPENGAUSS_RAG_IMAGE"
if docker container inspect "$OPENGAUSS_RAG_CONTAINER" >/dev/null 2>&1; then
    log_warn "复用已有容器 ${OPENGAUSS_RAG_CONTAINER}，不会删除其数据"
    connect_network "$OPENGAUSS_RAG_CONTAINER"
    [ "$(docker inspect -f '{{.State.Running}}' "$OPENGAUSS_RAG_CONTAINER")" = "true" ] || \
        docker start "$OPENGAUSS_RAG_CONTAINER" >/dev/null
else
    RAG_DB_PASSWORD="$(tr -d '\r\n' <"$RAG_DB_SECRET_FILE")"
    docker run -d \
        --name "$OPENGAUSS_RAG_CONTAINER" \
        --restart unless-stopped \
        --network "$WITTY_NETWORK" \
        -p "${OPENGAUSS_RAG_HOST_PORT}:5432" \
        -v "${OPENGAUSS_RAG_VOLUME}:/var/lib/opengauss" \
        -e GS_PASSWORD="$RAG_DB_PASSWORD" \
        "$OPENGAUSS_RAG_IMAGE" >/dev/null
    unset RAG_DB_PASSWORD
    log_ok "已启动 ${OPENGAUSS_RAG_CONTAINER}"
fi

log_info "等待 openGauss 就绪"
db_ready=false
for _ in $(seq 1 60); do
    if docker exec "$OPENGAUSS_RAG_CONTAINER" su - omm -c \
        "gsql -d ${RAG_DB_NAME} -p 5432 -c 'select 1'" >/dev/null 2>&1; then
        db_ready=true
        break
    fi
    sleep 3
done
if [ "$db_ready" != true ]; then
    log_error "openGauss 未在规定时间内就绪，请检查: docker logs ${OPENGAUSS_RAG_CONTAINER}"
    exit 1
fi
docker exec "$OPENGAUSS_RAG_CONTAINER" su - omm -c \
    "gs_guc reload -D /var/lib/opengauss/data -c \"behavior_compat_options='accept_empty_str'\"" >/dev/null
log_ok "openGauss 已就绪并启用 accept_empty_str"

# Keep model and service settings supplied by the user, but force both RAG
# database sections to use the dedicated openGauss container.
mkdir -p "$(dirname "$RAG_RUNTIME_CONFIG")" "$RAG_LOG_DIR"
RAG_CONFIG_OLD_SHA="$(sha256sum "$RAG_RUNTIME_CONFIG" 2>/dev/null | awk '{print $1}' || true)"
export RAG_RENDER_SOURCE="$RAG_CONFIG_FILE"
export RAG_RENDER_TARGET="$RAG_RUNTIME_CONFIG"
export RAG_RENDER_PASSWORD="$(tr -d '\r\n' <"$RAG_DB_SECRET_FILE")"
export RAG_RENDER_HOST="$OPENGAUSS_RAG_CONTAINER"
export RAG_RENDER_USER="$RAG_DB_USER"
export RAG_RENDER_DB="$RAG_DB_NAME"
export RAG_RENDER_MODEL_API_KEY="$RAG_EMBEDDING_API_KEY"
export RAG_RENDER_EMBEDDING_DIMENSION="$RAG_EMBEDDING_DIMENSION"
export RAG_RENDER_RERANK_ENABLED="$RAG_RERANK_ENABLED"
export RAG_RENDER_EMBEDDING_MODEL_NAME="$RAG_EMBEDDING_MODEL_NAME"
export RAG_RENDER_EMBEDDING_MODEL_PROVIDER="$RAG_EMBEDDING_MODEL_PROVIDER"
export RAG_RENDER_EMBEDDING_ENDPOINT="$RAG_EMBEDDING_ENDPOINT"
export RAG_RENDER_RERANK_MODEL_NAME="$RAG_RERANK_MODEL_NAME"
export RAG_RENDER_RERANK_MODEL_PROVIDER="$RAG_RERANK_MODEL_PROVIDER"
export RAG_RENDER_RERANK_ENDPOINT="$RAG_RERANK_ENDPOINT"
python3 - <<'PY'
import json
import os
import re
from pathlib import Path

source = Path(os.environ["RAG_RENDER_SOURCE"]).read_text()
values = {
    "database_type": "opengauss",
    "database_host": os.environ["RAG_RENDER_HOST"],
    "database_port": 5432,
    "database_user": os.environ["RAG_RENDER_USER"],
    "database_password": os.environ["RAG_RENDER_PASSWORD"],
    "database_db": os.environ["RAG_RENDER_DB"],
}
service_values = {
    "max_vector_dimension": os.environ["RAG_RENDER_EMBEDDING_DIMENSION"],
}
model_values = {
    "embedding_model": {
        "model_name": os.environ["RAG_RENDER_EMBEDDING_MODEL_NAME"],
        "online_status": "online",
        "model_labels": ["txt2embedding"],
        "model_provider": os.environ["RAG_RENDER_EMBEDDING_MODEL_PROVIDER"],
        "end_point": os.environ["RAG_RENDER_EMBEDDING_ENDPOINT"],
        "api_key": os.environ["RAG_RENDER_MODEL_API_KEY"],
        "request_timeout": 60,
        "input_max_tokens": 8192,
        "output_max_tokens": 8192,
        "temperature": 0.7,
        "batch_size": 16,
    },
    "rerank_model": {
        "model_name": os.environ["RAG_RENDER_RERANK_MODEL_NAME"],
        "online_status": "online" if os.environ["RAG_RENDER_RERANK_ENABLED"] == "1" else "offline",
        "model_labels": ["reranker"],
        "model_provider": os.environ["RAG_RENDER_RERANK_MODEL_PROVIDER"],
        "end_point": os.environ["RAG_RENDER_RERANK_ENDPOINT"],
        "api_key": os.environ["RAG_RENDER_MODEL_API_KEY"],
        "request_timeout": 60,
        "input_max_tokens": 8192,
        "output_max_tokens": 8192,
        "temperature": 0.7,
        "batch_size": 16,
    },
}

def render_value(value):
    if isinstance(value, bool):
        return str(value).lower()
    if isinstance(value, (int, float)):
        return str(value)
    if isinstance(value, list):
        return json.dumps(value, ensure_ascii=False)
    return '"' + str(value).replace('\\', '\\\\').replace('"', '\\"') + '"'

def replace_section(match):
    name, body = match.group(1), match.group(2)
    if name == "static_source":
        key = "stop_words_path"
        value = '"/rag-service/rag_core/static/stopwords.txt"'
        pattern = rf"(?m)^\s*{key}\s*=.*$"
        if re.search(pattern, body):
            body = re.sub(pattern, f"{key} = {value}", body)
        else:
            body += f"{key} = {value}\n"
        return f"[{name}]\n{body}"
    if name == "service":
        for key, value in service_values.items():
            rendered = str(value)
            pattern = rf"(?m)^\s*{re.escape(key)}\s*=.*$"
            if re.search(pattern, body):
                body = re.sub(pattern, f"{key} = {rendered}", body)
            else:
                body += f"{key} = {rendered}\n"
        return f"[{name}]\n{body}"
    if name in model_values:
        for key, value in model_values[name].items():
            rendered = render_value(value)
            pattern = rf"(?m)^\s*{re.escape(key)}\s*=.*$"
            if re.search(pattern, body):
                body = re.sub(pattern, f"{key} = {rendered}", body)
            else:
                body += f"{key} = {rendered}\n"
        return f"[{name}]\n{body}"
    if name not in {"scalar_db", "vector_db"}:
        return match.group(0)
    for key, value in values.items():
        rendered = str(value) if isinstance(value, int) else '"' + value.replace('\\', '\\\\').replace('"', '\\"') + '"'
        pattern = rf"(?m)^\s*{re.escape(key)}\s*=.*$"
        if re.search(pattern, body):
            body = re.sub(pattern, f"{key} = {rendered}", body)
        else:
            body += f"{key} = {rendered}\n"
    return f"[{name}]\n{body}"

section_pattern = re.compile(r"(?ms)^\[([^]]+)]\s*\n(.*?)(?=^\[|\Z)")
found = set(re.findall(r"(?m)^\[([^]]+)]", source))
missing = {"service", "scalar_db", "vector_db", "static_source", "embedding_model", "rerank_model"} - found
if missing:
    raise SystemExit("RAG config missing section(s): " + ", ".join(sorted(missing)))
rendered = section_pattern.sub(replace_section, source)
Path(os.environ["RAG_RENDER_TARGET"]).write_text(rendered)
PY
unset RAG_RENDER_SOURCE RAG_RENDER_TARGET RAG_RENDER_PASSWORD RAG_RENDER_HOST \
    RAG_RENDER_USER RAG_RENDER_DB RAG_RENDER_MODEL_API_KEY \
    RAG_RENDER_EMBEDDING_MODEL_NAME RAG_RENDER_EMBEDDING_MODEL_PROVIDER RAG_RENDER_EMBEDDING_ENDPOINT \
    RAG_RENDER_EMBEDDING_DIMENSION RAG_RENDER_RERANK_ENABLED \
    RAG_RENDER_RERANK_MODEL_NAME RAG_RENDER_RERANK_MODEL_PROVIDER RAG_RENDER_RERANK_ENDPOINT
chmod 0600 "$RAG_RUNTIME_CONFIG"
RAG_CONFIG_NEW_SHA="$(sha256sum "$RAG_RUNTIME_CONFIG" | awk '{print $1}')"
RAG_CONFIG_CHANGED=false
if [ "$RAG_CONFIG_OLD_SHA" != "$RAG_CONFIG_NEW_SHA" ]; then
    RAG_CONFIG_CHANGED=true
    log_info "检测到 RAG 运行配置变更，将重建 RAG Core 容器"
fi
unset RAG_CONFIG_OLD_SHA RAG_CONFIG_NEW_SHA
log_ok "已生成 openGauss 专用 RAG 配置 ${RAG_RUNTIME_CONFIG}"

ensure_image "$WITTY_RAG_CORE_IMAGE"
# 优先使用预构建镜像：部署机只需拉取，不必在目标机 git clone 源码再构建。
if docker image inspect "$WITTY_RAG_MCP_IMAGE" >/dev/null 2>&1; then
    log_ok "复用本地 RAG MCP 镜像 ${WITTY_RAG_MCP_IMAGE}"
else
    log_info "拉取预构建 RAG MCP 镜像 ${WITTY_RAG_MCP_IMAGE}"
    if docker pull "$WITTY_RAG_MCP_IMAGE" >/dev/null 2>&1; then
        log_ok "RAG MCP 镜像已就绪"
    elif [ "${WITTY_RAG_MCP_BUILD:-0}" = "1" ]; then
        log_warn "拉取失败，按 WITTY_RAG_MCP_BUILD=1 在本地构建（需要访问源码仓库）"
        docker build \
            --build-arg "RAG_BASE_IMAGE=${WITTY_RAG_CORE_IMAGE}" \
            -t "$WITTY_RAG_MCP_IMAGE" \
            -f "${SCRIPT_DIR}/Dockerfile.rag-mcp" \
            "$SCRIPT_DIR" >/dev/null
        log_ok "RAG MCP 镜像已构建"
    else
        log_error "无法获取 RAG MCP 镜像: ${WITTY_RAG_MCP_IMAGE}"
        log_error "请确认镜像仓库可达，或设置 WITTY_RAG_MCP_BUILD=1 允许在本地构建"
        exit 1
    fi
fi

start_rag_core_container() {
    docker run -d \
        --name "$WITTY_RAG_CORE_CONTAINER" \
        --restart unless-stopped \
        --network "$WITTY_NETWORK" \
        -p "${WITTY_RAG_CORE_HOST_PORT}:9988" \
        -e CONFIG=/rag-service/rag_core/config.toml \
        -e RAG_WORKERS="$RAG_WORKERS" \
        -v "${RAG_RUNTIME_CONFIG}:/rag-service/rag_core/config.toml:ro" \
        -v "${RAG_LOG_DIR}:/rag-service/logs" \
        -v "${RAG_ACCESS_KEY_SECRET_DIR}:/run/secrets/witty-rag:ro" \
        "$WITTY_RAG_MCP_IMAGE" >/dev/null
    log_ok "已启动 ${WITTY_RAG_CORE_CONTAINER}"
}

if docker container inspect "$WITTY_RAG_CORE_CONTAINER" >/dev/null 2>&1; then
    if [ "$(docker inspect -f '{{.State.Running}}' "$WITTY_RAG_CORE_CONTAINER")" = "true" ] &&
        [ "$RAG_CONFIG_CHANGED" != true ] &&
        [ "$(docker inspect "$WITTY_RAG_CORE_CONTAINER" --format '{{range .Mounts}}{{if eq .Destination "/run/secrets/witty-rag"}}yes{{end}}{{end}}' 2>/dev/null)" = "yes" ] &&
        docker exec "$WITTY_RAG_CORE_CONTAINER" \
            curl -fsS --max-time 3 http://127.0.0.1:9988/health_check >/dev/null 2>&1 &&
        docker exec "$WITTY_RAG_CORE_CONTAINER" sh -lc \
            'status=$(curl -sS --max-time 3 -o /dev/null -w "%{http_code}" http://127.0.0.1:12312/sse || true); [ "$status" = 200 ]'; then
        log_warn "复用正在运行的容器 ${WITTY_RAG_CORE_CONTAINER}，不会中断现有 RAG 服务"
        connect_network "$WITTY_RAG_CORE_CONTAINER"
    else
        OLD_RAG_CONFIG_SOURCE="$(docker inspect "$WITTY_RAG_CORE_CONTAINER" \
            --format '{{range .Mounts}}{{if eq .Destination "/rag-service/rag_core/config.toml"}}{{.Source}}{{end}}{{end}}' \
            2>/dev/null || true)"
        log_warn "检测到未通过健康检查的旧 RAG Core 容器，将重建容器以应用当前配置"
        if [ -n "$OLD_RAG_CONFIG_SOURCE" ]; then
            log_warn "旧配置挂载: ${OLD_RAG_CONFIG_SOURCE}"
        fi
        # RAG 业务数据保存在 openGauss；这里只删除已停止的无状态服务容器，
        # 不删除 openGauss 容器、数据卷或日志目录。
        docker rm -f "$WITTY_RAG_CORE_CONTAINER" >/dev/null
        unset OLD_RAG_CONFIG_SOURCE
        start_rag_core_container
    fi
else
    start_rag_core_container
fi

log_info "等待 RAG Core 就绪"
rag_ready=false
for _ in $(seq 1 60); do
    if docker exec "$WITTY_RAG_CORE_CONTAINER" \
        curl -fsS http://127.0.0.1:9988/health_check >/dev/null 2>&1; then
        rag_ready=true
        break
    fi
    sleep 3
done
if [ "$rag_ready" != true ]; then
    log_error "RAG Core 未在规定时间内就绪，请检查: docker logs ${WITTY_RAG_CORE_CONTAINER}"
    if [ -f "${RAG_LOG_DIR}/rag-core.log" ]; then
        log_error "RAG Core 应用日志最后 80 行："
        tail -n 80 "${RAG_LOG_DIR}/rag-core.log" >&2
    fi
    exit 1
fi

log_ok "RAG Core 已连接 openGauss 并通过健康检查"

if [ ! -s "$RAG_ACCESS_KEY_SECRET_FILE" ]; then
    log_info "首次部署：为 Witty-UB Agent 创建 RAG 访问密钥"
    access_key_response="$(curl -fsS \
        -H 'Content-Type: application/json' \
        -d '{"owner_id":"witty-ub-agent","owner_name":"Witty-UB Agent","name":"witty-ub-agent","description":"Managed by Witty-UB deployment"}' \
        "http://127.0.0.1:${WITTY_RAG_CORE_HOST_PORT}/access_key/")"
    RAG_ACCESS_KEY_RESPONSE="$access_key_response" \
    RAG_ACCESS_KEY_TARGET="$RAG_ACCESS_KEY_SECRET_FILE" \
        python3 - <<'PY'
import json
import os
from pathlib import Path

payload = json.loads(os.environ["RAG_ACCESS_KEY_RESPONSE"])
key = payload.get("result", {}).get("key")
if not isinstance(key, str) or not key.strip():
    raise SystemExit("RAG access-key response does not contain result.key")
Path(os.environ["RAG_ACCESS_KEY_TARGET"]).write_text(key.strip() + "\n")
PY
    unset access_key_response RAG_ACCESS_KEY_RESPONSE RAG_ACCESS_KEY_TARGET
    chmod 0600 "$RAG_ACCESS_KEY_SECRET_FILE"
    log_ok "RAG 访问密钥已保存到受保护文件 ${RAG_ACCESS_KEY_SECRET_FILE}"
    docker restart "$WITTY_RAG_CORE_CONTAINER" >/dev/null
    log_info "重启 RAG Core 以加载访问密钥"
    rag_ready=false
    for _ in $(seq 1 60); do
        if docker exec "$WITTY_RAG_CORE_CONTAINER" \
            curl -fsS http://127.0.0.1:9988/health_check >/dev/null 2>&1; then
            rag_ready=true
            break
        fi
        sleep 3
    done
    if [ "$rag_ready" != true ]; then
        log_error "RAG Core 重启后未就绪"
        exit 1
    fi
else
    chmod 0600 "$RAG_ACCESS_KEY_SECRET_FILE" 2>/dev/null || true
    log_ok "复用已有 RAG 访问密钥文件 ${RAG_ACCESS_KEY_SECRET_FILE}"
fi

log_info "等待 RAG MCP SSE 就绪"
mcp_ready=false
for _ in $(seq 1 60); do
    if docker exec "$WITTY_RAG_CORE_CONTAINER" sh -lc \
        'status=$(curl -sS --max-time 3 -o /dev/null -w "%{http_code}" http://127.0.0.1:12312/sse 2>/dev/null || true); [ "$status" = 200 ]'; then
        mcp_ready=true
        break
    fi
    if [ "$(docker inspect -f '{{.State.Running}}' "$WITTY_RAG_CORE_CONTAINER" 2>/dev/null || true)" != "true" ]; then
        break
    fi
    sleep 2
done
if [ "$mcp_ready" = true ]; then
    log_ok "RAG MCP SSE 已就绪: http://${WITTY_RAG_CORE_CONTAINER}:12312/sse"
else
    log_error "RAG MCP SSE 未就绪"
    [ ! -f "${RAG_LOG_DIR}/rag-mcp.log" ] || tail -n 80 "${RAG_LOG_DIR}/rag-mcp.log" >&2
    exit 1
fi
# 探测 embedding 端点；连不上不阻断部署，由 manage.sh status 持续反映。
if docker run --rm --network "$WITTY_NETWORK" \
    -e RAG_PROBE_ENDPOINT="$RAG_EMBEDDING_ENDPOINT" -e RAG_PROBE_KEY="$RAG_EMBEDDING_API_KEY" \
    --entrypoint sh "$WITTY_RAG_MCP_IMAGE" -c '
        key="${RAG_PROBE_KEY:-none}"
        code=$(curl -sS --max-time 8 -o /dev/null -w "%{http_code}" \
            -X POST "$RAG_PROBE_ENDPOINT" -H "Content-Type: application/json" \
            -H "Authorization: Bearer ${key}" \
            -d "{\"model\":\"probe\",\"input\":[\"probe\"]}" 2>/dev/null || echo 000)
        # 400/404 说明端点可达（只是模型名不对）；401/403 说明鉴权有问题。
        case "$code" in 2*|400|404|405|422) exit 0 ;; *) echo "probe=$code"; exit 1 ;; esac
    ' >/dev/null 2>&1; then
    log_ok "embedding 端点可达: ${RAG_EMBEDDING_ENDPOINT} (模型 ${RAG_EMBEDDING_MODEL_NAME}, ${RAG_EMBEDDING_DIMENSION} 维)"
else
    log_warn "embedding 端点当前不可达: ${RAG_EMBEDDING_ENDPOINT}"
    log_warn "RAG 服务已启动，但语义检索会失败；请检查端点、网络和 API Key（manage.sh status 可复查）"
fi
echo "  Embedding: ${RAG_EMBEDDING_MODEL_NAME} @ ${RAG_EMBEDDING_ENDPOINT} (${RAG_EMBEDDING_DIMENSION}d)"
echo "  Rerank:    $([ "$RAG_RERANK_ENABLED" = "1" ] && echo "enabled (${RAG_RERANK_MODEL_NAME})" || echo "disabled")"
echo "  openGauss: ${OPENGAUSS_RAG_CONTAINER}:5432 (host ${OPENGAUSS_RAG_HOST_PORT})"
echo "  RAG Core:  http://localhost:${WITTY_RAG_CORE_HOST_PORT}"
echo "  Network:   ${WITTY_NETWORK}"
