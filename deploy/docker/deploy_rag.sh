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
_ENV_RAG_DB_SECRET_FILE="${RAG_DB_SECRET_FILE:-}"
_ENV_OPENGAUSS_RAG_IMAGE="${OPENGAUSS_RAG_IMAGE:-}"
_ENV_WITTY_RAG_CORE_IMAGE="${WITTY_RAG_CORE_IMAGE:-}"
_ENV_WITTY_NETWORK="${WITTY_NETWORK:-}"

if [ -f "$CONF_FILE" ]; then
    # shellcheck disable=SC1090
    source "$CONF_FILE"
fi

[ -n "$_ENV_RAG_CONFIG_FILE" ] && RAG_CONFIG_FILE="$_ENV_RAG_CONFIG_FILE"
[ -n "$_ENV_RAG_DB_SECRET_FILE" ] && RAG_DB_SECRET_FILE="$_ENV_RAG_DB_SECRET_FILE"
[ -n "$_ENV_OPENGAUSS_RAG_IMAGE" ] && OPENGAUSS_RAG_IMAGE="$_ENV_OPENGAUSS_RAG_IMAGE"
[ -n "$_ENV_WITTY_RAG_CORE_IMAGE" ] && WITTY_RAG_CORE_IMAGE="$_ENV_WITTY_RAG_CORE_IMAGE"
[ -n "$_ENV_WITTY_NETWORK" ] && WITTY_NETWORK="$_ENV_WITTY_NETWORK"
unset _ENV_RAG_CONFIG_FILE _ENV_RAG_DB_SECRET_FILE _ENV_OPENGAUSS_RAG_IMAGE \
    _ENV_WITTY_RAG_CORE_IMAGE _ENV_WITTY_NETWORK

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

WITTY_RAG_CORE_CONTAINER="${WITTY_RAG_CORE_CONTAINER:-witty-rag-core}"
WITTY_RAG_CORE_IMAGE="${WITTY_RAG_CORE_IMAGE:-hub-harbor.oepkgs.net/neocopilot/witty-rag-core:0.10.2-release-arm}"
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
export RAG_RENDER_SOURCE="$RAG_CONFIG_FILE"
export RAG_RENDER_TARGET="$RAG_RUNTIME_CONFIG"
export RAG_RENDER_PASSWORD="$(tr -d '\r\n' <"$RAG_DB_SECRET_FILE")"
export RAG_RENDER_HOST="$OPENGAUSS_RAG_CONTAINER"
export RAG_RENDER_USER="$RAG_DB_USER"
export RAG_RENDER_DB="$RAG_DB_NAME"
python3 - <<'PY'
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
missing = {"scalar_db", "vector_db", "static_source"} - found
if missing:
    raise SystemExit("RAG config missing section(s): " + ", ".join(sorted(missing)))
rendered = section_pattern.sub(replace_section, source)
Path(os.environ["RAG_RENDER_TARGET"]).write_text(rendered)
PY
unset RAG_RENDER_SOURCE RAG_RENDER_TARGET RAG_RENDER_PASSWORD RAG_RENDER_HOST \
    RAG_RENDER_USER RAG_RENDER_DB
chmod 0600 "$RAG_RUNTIME_CONFIG"
log_ok "已生成 openGauss 专用 RAG 配置 ${RAG_RUNTIME_CONFIG}"

ensure_image "$WITTY_RAG_CORE_IMAGE"
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
        "$WITTY_RAG_CORE_IMAGE" >/dev/null
    log_ok "已启动 ${WITTY_RAG_CORE_CONTAINER}"
}

if docker container inspect "$WITTY_RAG_CORE_CONTAINER" >/dev/null 2>&1; then
    if [ "$(docker inspect -f '{{.State.Running}}' "$WITTY_RAG_CORE_CONTAINER")" = "true" ] &&
        docker exec "$WITTY_RAG_CORE_CONTAINER" \
            curl -fsS --max-time 3 http://127.0.0.1:9988/health_check >/dev/null 2>&1; then
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
echo "  openGauss: ${OPENGAUSS_RAG_CONTAINER}:5432 (host ${OPENGAUSS_RAG_HOST_PORT})"
echo "  RAG Core:  http://localhost:${WITTY_RAG_CORE_HOST_PORT}"
echo "  Network:   ${WITTY_NETWORK}"
