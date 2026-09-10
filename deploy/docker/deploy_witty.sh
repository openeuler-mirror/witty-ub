#!/bin/bash
# Copyright (c) Huawei Technologies Co., Ltd. 2023-2026. All rights reserved.
# witty-ub 容器一键部署脚本
# 用法:
#   bash deploy/deploy_witty.sh                          # 默认部署 All-in-One
#   bash deploy/deploy_witty.sh --role backend           # 分离部署：仅后端（FastAPI，暴露 9772）
#   bash deploy/deploy_witty.sh --role frontend          # 分离部署：仅前端（Nginx+OpenCode，暴露 32413）
#   bash deploy/deploy_witty.sh --image <custom-image:tag>  # 指定镜像

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
DEPLOY_DIR="$SCRIPT_DIR"
CONF_FILE="${DEPLOY_DIR}/../deploy.conf"
[ -f "$CONF_FILE" ] || CONF_FILE="${DEPLOY_DIR}/../pg.conf" # 兼容旧名

# ---------- 参数解析 ----------
CUSTOM_IMAGE=""
ROLE="all"

usage() {
    cat <<EOF
witty-ub container one-shot deployment script

Usage:
  $0 [OPTIONS]

Options:
  --role <all|backend|frontend>  Deployment role (default: all = single machine).
                                 backend/frontend are used for split deployments;
                                 they may run on different machines, image defaults to witty-ub:<role>
  --image <name:tag>  Use a specific image (default: auto-select by priority)
  -h, --help           Show this help

Config file: ${CONF_FILE}
EOF
}

while [ $# -gt 0 ]; do
    case "$1" in
    --role)
        ROLE="$2"
        shift 2
        ;;
    --image)
        CUSTOM_IMAGE="$2"
        shift 2
        ;;
    -h | --help)
        usage
        exit 0
        ;;
    *)
        echo "[ERROR] Unknown option: $1"
        usage
        exit 1
        ;;
    esac
done

case "$ROLE" in
all | backend | frontend) ;;
*)
    echo "[ERROR] invalid --role '$ROLE' (expected: all|backend|frontend)"
    exit 1
    ;;
esac

# 保存环境变量传入的值（优先级高于配置文件）。deploy.conf 会覆盖同名 shell 变量，
# 因此按清单快照并回填，避免环境变量被配置文件里的空值/默认值吃掉。
# 说明：不使用关联数组（bash 3.2 / macOS 自带 bash 不支持），改用 "KEY=VALUE" 行列表。
CONFIG_KEYS=(
    WITTY_HOST_PORT WITTY_EXTRA_MOUNTS WITTY_IMAGE WITTY_LOG_LEVEL WITTY_CONTAINER_NAME
    WITTY_BACKEND_URL WITTY_BACKEND_HOST_PORT WITTY_FRONTEND_HOST_PORT WITTY_NETWORK
    PG_HOST PG_PORT PG_DATABASE PG_USER PG_PASSWORD PG_SECRET_FILE
    PG_HOST_IN_CONTAINER PG_PORT_IN_CONTAINER PG_CONTAINER_NAME PG_NETWORK PG_VOLUME
    OPENCODE_CONFIG_DIR PG_IMAGE PG_HEALTH_INTERVAL PG_HEALTH_TIMEOUT PG_HEALTH_RETRIES
    PG_HEALTH_START_PERIOD
)
ENV_OVERRIDES=""
for _key in "${CONFIG_KEYS[@]}"; do
    [ -n "${!_key:-}" ] || continue
    ENV_OVERRIDES="${ENV_OVERRIDES}${_key}=${!_key}"$'\n'
done
unset _key

# 把快照回填到当前 shell（本脚本不再向子脚本传递这些变量）
restore_env_overrides() {
    local _line _k _v
    while IFS= read -r _line; do
        [ -n "$_line" ] || continue
        _k="${_line%%=*}"
        _v="${_line#*=}"
        printf -v "$_k" '%s' "$_v"
    done <<EOF
${ENV_OVERRIDES}
EOF
}

# ---------- 加载配置 ----------
# 与 deploy_pg.sh 一致：所有脚本共用 deploy/deploy.conf（旧名 pg.conf 兼容）。
# 先加载配置文件，再用上面保存的环境变量覆盖，保证"环境变量 > 配置文件"。
if [ -f "$CONF_FILE" ]; then
    echo "[INFO]  Loading config from ${CONF_FILE}"
    # shellcheck disable=SC1090
    source "$CONF_FILE"
fi

# 环境变量优先级高于配置文件（来自 manage.sh 交互式输入或命令行）
restore_env_overrides
unset ENV_OVERRIDES CONFIG_KEYS

# ---------- 工具函数 ----------
log_info() { echo "[INFO]  $*"; }
log_ok() { echo "[OK]    $*"; }
log_warn() { echo "[WARN]  $*"; }
log_error() { echo "[ERROR] $*"; }

# PG 密码只通过只读挂载传给容器入口，不写入容器环境配置。
# 路径优先级: PG_SECRET_FILE(环境变量/配置) > /etc/witty-ub/pg.passwd（Docker PG）
#            > <仓库>/deploy/pg.passwd（宿主机 RPM/源码 PG，由 deploy_pg.sh --rpm/--apt 生成）
SYSTEM_PG_SECRET_FILE="/etc/witty-ub/pg.passwd"
REPO_PG_SECRET_FILE="$(cd "${DEPLOY_DIR}/.." && pwd)/pg.passwd"

# 普通用户可能无法 stat 0700 目录中的文件，这里兼容 sudo -n 探测。
pg_secret_exists() {
    local file="$1"
    [ -f "$file" ] 2>/dev/null || sudo -n test -f "$file" 2>/dev/null
}

# 宿主机是否运行着 RPM/源码方式安装的 PostgreSQL（决定用哪份密钥）
host_pg_service_running() {
    command -v systemctl &>/dev/null &&
        systemctl list-units --type=service --state=running 2>/dev/null | grep -q 'postgresql'
}

if [ "$ROLE" != "frontend" ] && [ -z "${PG_SECRET_FILE:-}" ]; then
    if host_pg_service_running && pg_secret_exists "$REPO_PG_SECRET_FILE"; then
        # 宿主机 PG 场景：deploy_pg.sh --rpm/--apt 生成的密钥在仓库目录
        PG_SECRET_FILE="$REPO_PG_SECRET_FILE"
        if pg_secret_exists "$SYSTEM_PG_SECRET_FILE"; then
            log_warn "Host PostgreSQL service detected; preferring the repo secret ${PG_SECRET_FILE}"
            log_warn "Set PG_SECRET_FILE explicitly to use a different secret file"
        else
            log_info "Host PostgreSQL service detected; using the repo secret ${PG_SECRET_FILE}"
        fi
    elif pg_secret_exists "$SYSTEM_PG_SECRET_FILE"; then
        PG_SECRET_FILE="$SYSTEM_PG_SECRET_FILE"
    elif pg_secret_exists "$REPO_PG_SECRET_FILE"; then
        PG_SECRET_FILE="$REPO_PG_SECRET_FILE"
        log_warn "${SYSTEM_PG_SECRET_FILE} not found; using repo secret ${PG_SECRET_FILE} (host PG scenario)"
    else
        PG_SECRET_FILE="$SYSTEM_PG_SECRET_FILE"
    fi
fi
PG_SECRET_FILE="${PG_SECRET_FILE:-$SYSTEM_PG_SECRET_FILE}"

if [ "$ROLE" = "frontend" ]; then
    log_info "Role 'frontend' does not use the database; skipping PG secret checks"
else
    if ! pg_secret_exists "$PG_SECRET_FILE"; then
        log_error "PG secret file not found: ${PG_SECRET_FILE}"
        log_error "For a containerized PG run: bash deploy/deploy_pg.sh --docker"
        log_error "For a host PG run: sudo bash deploy/deploy_pg.sh --rpm"
        exit 1
    fi

    # 权限收紧到 0640（容器内 postgres 用户 uid26/gid0 需组可读）；属主为 root 时回退 sudo -n。
    if chmod 0640 "$PG_SECRET_FILE" 2>/dev/null || sudo -n chmod 0640 "$PG_SECRET_FILE" 2>/dev/null; then
        :
    fi
    _pg_secret_perms="$(stat -c '%a' "$PG_SECRET_FILE" 2>/dev/null ||
        stat -f '%Lp' "$PG_SECRET_FILE" 2>/dev/null ||
        sudo -n stat -c '%a' "$PG_SECRET_FILE" 2>/dev/null || true)"
    _pg_secret_perms="$(printf '%s' "$_pg_secret_perms" | tr -d '\r\n')"
    if [ -z "$_pg_secret_perms" ]; then
        log_error "Cannot read the mode of the PG secret file: ${PG_SECRET_FILE}"
        log_error "Make sure the current user or 'sudo -n' can access the file (a too-strict parent directory also triggers this)"
        exit 1
    fi
    if [ "$((8#${_pg_secret_perms}))" -gt "$((8#640))" ]; then
        log_error "PG secret file is too permissive (mode ${_pg_secret_perms}): ${PG_SECRET_FILE} (expected <= 640)"
        log_error "Run: sudo chmod 0640 ${PG_SECRET_FILE}"
        exit 1
    fi
    case "$_pg_secret_perms" in
    0*) _pg_secret_perms_display="$_pg_secret_perms" ;;
    *) _pg_secret_perms_display="0${_pg_secret_perms}" ;;
    esac
    log_info "PG secret file ready: ${PG_SECRET_FILE} (mode ${_pg_secret_perms_display})"

    _SECRET_PW="$( {
        cat "$PG_SECRET_FILE" 2>/dev/null || sudo -n cat "$PG_SECRET_FILE" 2>/dev/null
    } | tr -d '\r\n')"
    if [ -n "$_SECRET_PW" ]; then
        log_info "PG secret file content loaded"
    else
        log_error "PG secret file is empty or unreadable by the current user: ${PG_SECRET_FILE}"
        exit 1
    fi
    unset _SECRET_PW
fi

# witty-ub 默认值（未在 deploy.conf 中配置的项）
WITTY_CONTAINER_NAME="${WITTY_CONTAINER_NAME:-witty-ub}"
WITTY_HOST_PORT="${WITTY_HOST_PORT:-32412}"
WITTY_NETWORK="${PG_NETWORK:-witty-ub-network}"
WITTY_LOG_LEVEL="${WITTY_LOG_LEVEL:-info}"

# 角色派生：容器名、镜像 tag、宿主机端口
# backend 暴露 9772 供前端/外部访问；frontend 默认 32413 与单机部署 32412 错开
case "$ROLE" in
backend)
    CONTAINER_NAME="${WITTY_CONTAINER_NAME}-backend"
    ROLE_TAG="backend"
    HOST_PORT="${WITTY_BACKEND_HOST_PORT:-9772}"
    ;;
frontend)
    CONTAINER_NAME="${WITTY_CONTAINER_NAME}-frontend"
    ROLE_TAG="frontend"
    HOST_PORT="${WITTY_FRONTEND_HOST_PORT:-32413}"
    ;;
*)
    CONTAINER_NAME="${WITTY_CONTAINER_NAME}"
    ROLE_TAG="latest"
    HOST_PORT="${WITTY_HOST_PORT}"
    ;;
esac

# frontend 容器内访问后端的地址：显式配置 > 同网络后端容器名 > Docker 网关 + 宿主机端口
if [ "$ROLE" = "frontend" ]; then
    if [ -n "${WITTY_BACKEND_URL:-}" ]; then
        BACKEND_URL="${WITTY_BACKEND_URL}"
    else
        BACKEND_URL="http://${WITTY_CONTAINER_NAME}-backend:9772"
    fi
fi

# OpenCode 配置目录（宿主机）
OPENCODE_CONFIG_DIR="${OPENCODE_CONFIG_DIR:-$HOME/.config/opencode}"

check_docker() {
    if ! command -v docker &>/dev/null; then
        log_error "Docker not found. Please install Docker first:"
        log_error "  curl -fsSL https://get.docker.com | sh"
        exit 1
    fi
    if ! docker info &>/dev/null; then
        log_error "Docker daemon is not running. Please start Docker:"
        log_error "  systemctl start docker"
        exit 1
    fi
}

# 额外目录挂载（从 deploy.conf 读取 WITTY_EXTRA_MOUNTS）
# 格式: "host_path:container_path[:ro|rw] host_path2:container_path2[:ro|rw]"
EXTRA_MOUNT_ARGS=()
if [ -n "${WITTY_EXTRA_MOUNTS:-}" ]; then
    for mount in ${WITTY_EXTRA_MOUNTS}; do
        host_path=$(echo "$mount" | cut -d: -f1)
        if [ ! -d "$host_path" ] && [ ! -f "$host_path" ]; then
            log_warn "Mount source does not exist: ${host_path}; skipping this mount"
            continue
        fi
        EXTRA_MOUNT_ARGS+=("-v" "${mount}")
        log_info "Extra mount: ${mount}"
    done
fi

# ============================================================
# witty-ub 镜像候选列表（按优先级从高到低，tag 跟随部署角色）
# ============================================================
declare -a WITTY_IMAGE_CANDIDATES=(
    "hub-harbor.oepkgs.net/neocopilot/witty-ub:${ROLE_TAG}"
    "witty-ub:${ROLE_TAG}"
)

# ============================================================
# 主流程
# ============================================================
echo "========================================"
echo "witty-ub Container Deployment"
echo "========================================"

check_docker

# Step 1: 检查/拉取镜像
echo ""
echo "[Step 1/3] Checking and pulling witty-ub image ..."

SELECTED_IMAGE=""

# 如果用户通过命令行指定了镜像，优先级最高
if [ -n "$CUSTOM_IMAGE" ]; then
    log_info "Using custom image (from --image): ${CUSTOM_IMAGE}"
    SELECTED_IMAGE="$CUSTOM_IMAGE"
# 如果配置文件里指定了镜像
elif [ -n "$WITTY_IMAGE" ]; then
    log_info "Using image (from deploy.conf): ${WITTY_IMAGE}"
    SELECTED_IMAGE="$WITTY_IMAGE"
fi

# 已指定镜像（命令行或配置），检查并拉取
if [ -n "$SELECTED_IMAGE" ]; then
    if ! docker image inspect "$SELECTED_IMAGE" &>/dev/null; then
        log_info "Pulling ${SELECTED_IMAGE} ..."
        docker pull "$SELECTED_IMAGE"
        log_ok "Pulled ${SELECTED_IMAGE} successfully"
    fi
else
    # 先看本地有没有可用的 witty-ub 镜像
    log_info "Checking local images for witty-ub ..."
    for image in "${WITTY_IMAGE_CANDIDATES[@]}"; do
        if docker image inspect "$image" &>/dev/null; then
            log_ok "Found local image: ${image}"
            SELECTED_IMAGE="$image"
            break
        fi
    done

    # 本地没有，按顺序拉取
    if [ -z "$SELECTED_IMAGE" ]; then
        log_info "No usable local image. Trying to pull ..."
        for image in "${WITTY_IMAGE_CANDIDATES[@]}"; do
            log_info "  Trying to pull ${image} ..."
            if docker pull "$image" &>/dev/null; then
                log_ok "Pulled ${image} successfully"
                SELECTED_IMAGE="$image"
                break
            else
                log_warn "  Failed to pull ${image}, trying next ..."
            fi
        done
    fi
fi

if [ -z "$SELECTED_IMAGE" ]; then
    log_error "No witty-ub image available. Tried:"
    for image in "${WITTY_IMAGE_CANDIDATES[@]}"; do
        log_error "  - ${image}"
    done
    log_error "Or build locally: docker build -t witty-ub:latest ."
    exit 1
fi

# Step 2: 验证镜像
echo ""
echo "[Step 2/3] Verifying image ..."

IMAGE_INFO=$(docker images --format '{{.Repository}}:{{.Tag}} {{.ID}} {{.Size}}' "$SELECTED_IMAGE" 2>/dev/null || echo "")
if [ -n "$IMAGE_INFO" ]; then
    log_ok "Image verified: ${IMAGE_INFO}"
else
    log_error "Image verification failed"
    exit 1
fi

log_info "Verifying image assets for role '${ROLE}' ..."
if [ "$ROLE" = "frontend" ]; then
    # frontend 镜像无 BRPC 工具，校验 Nginx 模板 / Web 静态资源 / Agent 配置
    if docker run --rm --entrypoint /bin/bash "$SELECTED_IMAGE" -c \
        'test -f /etc/witty-ub/web/nginx.conf.template &&
         test -d /var/witty-ub/web &&
         test -f /var/witty-ub/witty_ub_diagnostician/.opencode/opencode.json'; then
        log_ok "Nginx template, web assets and agent config verified"
    else
        log_error "Image is missing Nginx template, web assets or agent config"
        exit 1
    fi
else
    if docker run --rm --entrypoint /bin/bash "$SELECTED_IMAGE" -c \
        'test -x /usr/bin/witty-ub-brpc-diag &&
         test -f /var/witty-ub/data/ubsocket/ubsocket_failure_mode.json &&
         test -f /var/witty-ub/data/umq/umq_failure_mode.json &&
         test -f /var/witty-ub/data/urma/urma_failure_mode.json'; then
        log_ok "BRPC diagnosis binary and data verified"
    else
        log_error "Image is missing the BRPC diagnosis binary or required data files"
        log_error "Please use an updated image containing witty-ub-brpc-diag and ubsocket/umq/urma rules"
        exit 1
    fi
fi

# Step 3: 启动容器
echo ""
echo "[Step 3/3] Starting witty-ub container ..."

# 3.1 准备网络
log_info "Preparing Docker network ..."
if docker network ls --format '{{.Name}}' | grep -qx "${WITTY_NETWORK}"; then
    log_ok "Network ${WITTY_NETWORK} already exists"
else
    log_info "Creating network ${WITTY_NETWORK} ..."
    docker network create "${WITTY_NETWORK}"
    log_ok "Network ${WITTY_NETWORK} created"
fi

# 3.2 准备数据卷
log_info "Preparing Docker volumes ..."
if [ "$ROLE" = "frontend" ]; then
    ROLE_VOLUMES=(witty-ub-experience-data)
else
    ROLE_VOLUMES=(witty-ub-data witty-ub-logs witty-ub-uploads witty-ub-results)
fi
for vol in "${ROLE_VOLUMES[@]}"; do
    if docker volume ls --format '{{.Name}}' | grep -qx "$vol"; then
        log_ok "Volume $vol already exists"
    else
        log_info "Creating volume $vol ..."
        docker volume create "$vol"
        log_ok "Volume $vol created"
    fi
done

# 3.3 准备 OpenCode 配置目录（all / frontend 需要）
if [ "$ROLE" != "backend" ] && [ ! -d "$OPENCODE_CONFIG_DIR" ]; then
    log_info "Creating opencode config dir: ${OPENCODE_CONFIG_DIR}"
    mkdir -p "$OPENCODE_CONFIG_DIR"
fi

# 3.4 清理同名旧容器
if docker ps -a --format '{{.Names}}' | grep -qx "${CONTAINER_NAME}"; then
    log_warn "Container ${CONTAINER_NAME} already exists"
    if docker ps --format '{{.Names}}' | grep -qx "${CONTAINER_NAME}"; then
        log_info "Stopping running container ..."
        docker stop "${CONTAINER_NAME}"
    fi
    log_info "Removing existing container ..."
    docker rm "${CONTAINER_NAME}"
    log_ok "Existing container removed"
fi

# 3.5 自动检测 PG 连接配置（容器内视角）
# 优先级：用户显式配置 > 自动检测（PG 容器 > 宿主机 RPM PG > 默认值）
detect_pg_config() {
    # 如果用户在 deploy.conf 中显式配置了（非空且不是默认 postgres），直接使用
    if [ -n "${PG_HOST_IN_CONTAINER:-}" ] && [ "${PG_HOST_IN_CONTAINER}" != "postgres" ]; then
        log_info "Using PG connection from deploy.conf: ${PG_HOST_IN_CONTAINER}:${PG_PORT_IN_CONTAINER:-5432}"
        PG_IN_CONTAINER_HOST="${PG_HOST_IN_CONTAINER}"
        PG_IN_CONTAINER_PORT="${PG_PORT_IN_CONTAINER:-5432}"
        return 0
    fi
    # 用户显式配置了端口但没改 host（不常见，但兼容）
    if [ -n "${PG_PORT_IN_CONTAINER:-}" ] && [ "${PG_PORT_IN_CONTAINER}" != "5432" ]; then
        PG_IN_CONTAINER_PORT="${PG_PORT_IN_CONTAINER}"
    fi

    # 检测 1：PG 容器是否在同一网络中运行
    PG_CONTAINER="${PG_CONTAINER_NAME:-postgres}"
    if docker ps --format '{{.Names}}' 2>/dev/null | grep -qx "${PG_CONTAINER}"; then
        # 检查是否在同一网络
        PG_NET=$(docker inspect "${PG_CONTAINER}" --format '{{range $k,$v := .NetworkSettings.Networks}}{{$k}} {{end}}' 2>/dev/null || true)
        if echo " ${PG_NET} " | grep -q " ${WITTY_NETWORK} "; then
            log_info "PostgreSQL container (${PG_CONTAINER}) found on the same network; using container DNS name"
            PG_IN_CONTAINER_HOST="${PG_CONTAINER}"
            PG_IN_CONTAINER_PORT="${PG_PORT_IN_CONTAINER:-5432}"
            return 0
        fi
    fi

    # 检测 2：宿主机是否有 RPM 方式运行的 PostgreSQL
    if command -v systemctl &>/dev/null; then
        PG_RPM_SERVICE=$(systemctl list-units --type=service --state=running 2>/dev/null | grep -o 'postgresql[^ ]*' | head -1 || true)
        if [ -n "$PG_RPM_SERVICE" ]; then
            # 找到宿主机监听端口
            HOST_PG_PORT=$(ss -tlnp 2>/dev/null | grep 'postgres' | head -1 | awk '{print $4}' | rev | cut -d: -f1 | rev)
            if [ -z "$HOST_PG_PORT" ]; then
                HOST_PG_PORT="${PG_PORT_RPM:-5432}"
            fi
            # 找到 Docker 网络的网关 IP（容器访问宿主机用）
            DOCKER_GATEWAY=$(docker network inspect "${WITTY_NETWORK}" --format '{{(index .IPAM.Config 0).Gateway}}' 2>/dev/null || true)
            if [ -n "$DOCKER_GATEWAY" ]; then
                log_info "Host RPM PostgreSQL detected (${PG_RPM_SERVICE}, port ${HOST_PG_PORT}); connecting via Docker gateway ${DOCKER_GATEWAY}"
                PG_IN_CONTAINER_HOST="${DOCKER_GATEWAY}"
                PG_IN_CONTAINER_PORT="${HOST_PG_PORT}"
                return 0
            fi
        fi
    fi

    # 兜底：用默认值
    log_warn "No usable PostgreSQL detected; using default postgres:5432 (make sure the PG container runs on the same network)"
    PG_IN_CONTAINER_HOST="postgres"
    PG_IN_CONTAINER_PORT="5432"
}

if [ "$ROLE" != "frontend" ]; then
    detect_pg_config
fi

# 3.6 启动容器
log_info "Starting container ${CONTAINER_NAME} (role: ${ROLE}) ..."

case "$ROLE" in
backend)
    docker run -d \
        --name "${CONTAINER_NAME}" \
        --restart unless-stopped \
        -p "${HOST_PORT}:9772" \
        -v witty-ub-data:/var/witty-ub/data \
        -v witty-ub-logs:/var/log/witty-ub \
        -v witty-ub-uploads:/var/witty-ub/latency/file/file_upload \
        -v witty-ub-results:/var/witty-ub/latency/file/file_parse_result \
        -v "${PG_SECRET_FILE}:/run/secrets/pg_password:ro" \
        "${EXTRA_MOUNT_ARGS[@]}" \
        -e WITTY_ROLE=backend \
        -e PYTHONPATH=/var/witty-ub \
        -e LOG_LEVEL="${WITTY_LOG_LEVEL}" \
        -e PG_HOST="${PG_IN_CONTAINER_HOST}" \
        -e PG_PORT="${PG_IN_CONTAINER_PORT}" \
        -e PG_DATABASE="${PG_DATABASE:-witty-ub}" \
        -e PG_USER="${PG_USER:-witty-ub}" \
        --health-cmd="curl -f http://localhost:9772/health_check" \
        --health-interval=30s \
        --health-timeout=10s \
        --health-retries=3 \
        --health-start-period=40s \
        --network "${WITTY_NETWORK}" \
        "${SELECTED_IMAGE}"
    ;;
frontend)
    docker run -d \
        --name "${CONTAINER_NAME}" \
        --restart unless-stopped \
        -p "${HOST_PORT}:8080" \
        -v "${OPENCODE_CONFIG_DIR}:/root/.config/opencode" \
        -v witty-ub-experience-data:/var/witty-ub/witty_ub_diagnostician/.opencode/skills/experience-skill/data \
        "${EXTRA_MOUNT_ARGS[@]}" \
        -e WITTY_ROLE=frontend \
        -e WITTY_BACKEND_URL="${BACKEND_URL}" \
        --network "${WITTY_NETWORK}" \
        "${SELECTED_IMAGE}"
    ;;
*)
    docker run -d \
        --name "${CONTAINER_NAME}" \
        --restart unless-stopped \
        -p "${HOST_PORT}:8080" \
        -v witty-ub-data:/var/witty-ub/data \
        -v witty-ub-logs:/var/log/witty-ub \
        -v witty-ub-uploads:/var/witty-ub/latency/file/file_upload \
        -v witty-ub-results:/var/witty-ub/latency/file/file_parse_result \
        -v "${PG_SECRET_FILE}:/run/secrets/pg_password:ro" \
        -v "${OPENCODE_CONFIG_DIR}:/root/.config/opencode" \
        "${EXTRA_MOUNT_ARGS[@]}" \
        -e WITTY_ROLE=all \
        -e PYTHONPATH=/var/witty-ub \
        -e LOG_LEVEL="${WITTY_LOG_LEVEL}" \
        -e PG_HOST="${PG_IN_CONTAINER_HOST}" \
        -e PG_PORT="${PG_IN_CONTAINER_PORT}" \
        -e PG_DATABASE="${PG_DATABASE:-witty-ub}" \
        -e PG_USER="${PG_USER:-witty-ub}" \
        --health-cmd="curl -f http://localhost:9772/health_check" \
        --health-interval=30s \
        --health-timeout=10s \
        --health-retries=3 \
        --health-start-period=40s \
        --network "${WITTY_NETWORK}" \
        "${SELECTED_IMAGE}"
    ;;
esac

log_ok "Container ${CONTAINER_NAME} started"

# 3.7 等待健康
echo ""
log_info "Waiting for witty-ub (${ROLE}) to become healthy ..."
MAX_WAIT=180
WAITED=0
while [ "$WAITED" -lt "$MAX_WAIT" ]; do
    HEALTH=$(docker inspect --format='{{.State.Health.Status}}' "${CONTAINER_NAME}" 2>/dev/null || echo "starting")
    if [ "$HEALTH" = "healthy" ]; then
        break
    fi
    sleep 3
    WAITED=$((WAITED + 3))
    printf "  waiting... %3ds (health: %s)\r" "$WAITED" "$HEALTH"
done
echo ""

if [ "$HEALTH" = "healthy" ]; then
    log_ok "witty-ub (${ROLE}) is healthy!"
else
    log_error "witty-ub (${ROLE}) not healthy within ${MAX_WAIT}s (health: ${HEALTH})"
    log_error "Container logs (last 20 lines):"
    docker logs --tail 20 "${CONTAINER_NAME}" 2>&1 | sed 's/^/    /' || true
    exit 1
fi

# ---------- 验证连接 ----------
echo ""
echo "========================================"
echo "Verifying connection ..."

# frontend 经 Nginx 反代探测远端后端；all/backend 直连本机 API
VERIFY_URL="http://localhost:${HOST_PORT}/health_check"
VERIFY_OK=0
for i in {1..15}; do
    # 必须校验响应体，只看 curl 退出码会把 502/404 也当成成功
    if curl -sf --max-time 5 --noproxy '*' "$VERIFY_URL" 2>/dev/null | grep -q '"status"'; then
        VERIFY_OK=1
        log_ok "API connection verified (${VERIFY_URL})"
        break
    fi
    sleep 2
done
if [ "$VERIFY_OK" -ne 1 ]; then
    log_error "API health check failed: ${VERIFY_URL}"
    log_error "Container state: $(docker inspect --format='{{.State.Status}} {{if .State.Health}}{{.State.Health.Status}}{{end}}' "${CONTAINER_NAME}" 2>/dev/null || echo unknown)"
    log_error "Container logs (last 20 lines):"
    docker logs --tail 20 "${CONTAINER_NAME}" 2>&1 | sed 's/^/    /' || true
    exit 1
fi

echo ""
echo "========================================"
echo "witty-ub Deployment Completed! (role: ${ROLE})"
echo "========================================"
echo "  Container:  ${CONTAINER_NAME}"
echo "  Image:      ${SELECTED_IMAGE}"
if [ "$ROLE" != "backend" ]; then
    echo "  Web UI:     http://localhost:${HOST_PORT}"
    echo "  API:        http://localhost:${HOST_PORT}/health_check"
    echo "  Agent API:  http://localhost:${HOST_PORT}/agent-api/ (OpenCode via Nginx)"
fi
if [ "$ROLE" = "backend" ]; then
    echo "  API:        http://localhost:${HOST_PORT}/health_check (port 9772, proxied by the frontend node)"
fi
if [ "$ROLE" = "frontend" ]; then
    echo "  Backend:    ${BACKEND_URL} (nginx upstream inside the frontend container)"
fi
echo "  Network:    ${WITTY_NETWORK}"
if [ "$ROLE" != "frontend" ]; then
    echo "  PG Host:    ${PG_IN_CONTAINER_HOST}:${PG_IN_CONTAINER_PORT} (container)"
fi
if [ ${#EXTRA_MOUNT_ARGS[@]} -gt 0 ]; then
    echo "  Extra mounts:"
    for ((i = 1; i < ${#EXTRA_MOUNT_ARGS[@]}; i += 2)); do
        echo "    - ${EXTRA_MOUNT_ARGS[$i]}"
    done
fi
echo ""
echo "Useful commands:"
echo "  docker ps                                    # list running containers"
echo "  docker logs ${CONTAINER_NAME} -f      # view container logs"
echo "  docker stop ${CONTAINER_NAME}         # stop container"
echo "  docker start ${CONTAINER_NAME}        # start a stopped container"
echo "  docker restart ${CONTAINER_NAME}      # restart container"
echo "  docker exec -it ${CONTAINER_NAME} bash  # open a shell in the container"
echo "========================================"
