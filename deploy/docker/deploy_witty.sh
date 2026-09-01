#!/bin/bash
# Copyright (c) Huawei Technologies Co., Ltd. 2023-2026. All rights reserved.
# witty-ub 容器一键部署脚本
# 用法:
#   bash deploy/deploy_witty.sh            # 默认部署
#   bash deploy/deploy_witty.sh --image <custom-image:tag>  # 指定镜像

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
DEPLOY_DIR="$SCRIPT_DIR"
CONF_FILE="${DEPLOY_DIR}/../deploy.conf"
[ -f "$CONF_FILE" ] || CONF_FILE="${DEPLOY_DIR}/../pg.conf"   # 兼容旧名

# ---------- 参数解析 ----------
CUSTOM_IMAGE=""

usage() {
    cat <<EOF
witty-ub 容器一键部署脚本

用法:
  $0 [OPTIONS]

选项:
  --image <name:tag>  指定镜像（默认按优先级自动选择）
  -h, --help           显示此帮助

配置文件: ${CONF_FILE}
EOF
}

while [ $# -gt 0 ]; do
    case "$1" in
        --image)
            CUSTOM_IMAGE="$2"
            shift 2
            ;;
        -h|--help)
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

# 保存环境变量传入的值（优先级高于配置文件）
_SAVED_HOST_PORT="${WITTY_HOST_PORT:-}"
_SAVED_EXTRA_MOUNTS="${WITTY_EXTRA_MOUNTS:-}"
_SAVED_IMAGE="${WITTY_IMAGE:-}"

# ---------- 加载配置 ----------
if [ -f "$CONF_FILE" ]; then
    echo "[INFO] Loading config from ${CONF_FILE}"
    source "$CONF_FILE"
else
    echo "[WARN]  Config file not found: ${CONF_FILE}, using defaults"
fi

# 环境变量优先级高于配置文件（来自 manage.sh 交互式输入）
[ -n "$_SAVED_HOST_PORT" ] && WITTY_HOST_PORT="$_SAVED_HOST_PORT"
[ -n "$_SAVED_EXTRA_MOUNTS" ] && WITTY_EXTRA_MOUNTS="$_SAVED_EXTRA_MOUNTS"
[ -n "$_SAVED_IMAGE" ] && WITTY_IMAGE="$_SAVED_IMAGE"
unset _SAVED_HOST_PORT _SAVED_EXTRA_MOUNTS _SAVED_IMAGE

# witty-ub 默认值（未在 pg.conf 中配置的项）
WITTY_CONTAINER_NAME="${WITTY_CONTAINER_NAME:-witty-ub}"
WITTY_HOST_PORT="${WITTY_HOST_PORT:-32412}"
WITTY_NETWORK="${PG_NETWORK:-witty-ub-network}"
WITTY_LOG_LEVEL="${WITTY_LOG_LEVEL:-info}"

# OpenCode 配置目录（宿主机）
OPENCODE_CONFIG_DIR="${OPENCODE_CONFIG_DIR:-$HOME/.config/opencode}"

# ---------- 工具函数 ----------
log_info()  { echo "[INFO]  $*"; }
log_ok()    { echo "[OK]    $*"; }
log_warn()  { echo "[WARN]  $*"; }
log_error() { echo "[ERROR] $*"; }

check_docker() {
    if ! command -v docker &> /dev/null; then
        log_error "Docker not found. Please install Docker first:"
        log_error "  curl -fsSL https://get.docker.com | sh"
        exit 1
    fi
    if ! docker info &> /dev/null; then
        log_error "Docker daemon is not running. Please start Docker:"
        log_error "  systemctl start docker"
        exit 1
    fi
}

# 额外目录挂载（从 pg.conf 读取 WITTY_EXTRA_MOUNTS）
# 格式: "host_path:container_path[:ro|rw] host_path2:container_path2[:ro|rw]"
EXTRA_MOUNT_ARGS=()
if [ -n "${WITTY_EXTRA_MOUNTS:-}" ]; then
    for mount in ${WITTY_EXTRA_MOUNTS}; do
        host_path=$(echo "$mount" | cut -d: -f1)
        if [ ! -d "$host_path" ] && [ ! -f "$host_path" ]; then
            log_warn "挂载源路径不存在: ${host_path}，跳过该挂载"
            continue
        fi
        EXTRA_MOUNT_ARGS+=("-v" "${mount}")
        log_info "额外挂载: ${mount}"
    done
fi

# ============================================================
# witty-ub 镜像候选列表（按优先级从高到低）
# ============================================================
declare -a WITTY_IMAGE_CANDIDATES=(
    "hub-harbor.oepkgs.net/neocopilot/witty-ub:latest"
    "witty-ub:latest"
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
    log_info "Using image (from pg.conf): ${WITTY_IMAGE}"
    SELECTED_IMAGE="$WITTY_IMAGE"
fi

# 已指定镜像（命令行或配置），检查并拉取
if [ -n "$SELECTED_IMAGE" ]; then
    if ! docker image inspect "$SELECTED_IMAGE" &> /dev/null; then
        log_info "Pulling ${SELECTED_IMAGE} ..."
        docker pull "$SELECTED_IMAGE"
        log_ok "Pulled ${SELECTED_IMAGE} successfully"
    fi
else
    # 先看本地有没有可用的 witty-ub 镜像
    log_info "Checking local images for witty-ub ..."
    for image in "${WITTY_IMAGE_CANDIDATES[@]}"; do
        if docker image inspect "$image" &> /dev/null; then
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
            if docker pull "$image" &> /dev/null; then
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

log_info "Verifying BRPC diagnosis assets in image ..."
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
for vol in witty-ub-data witty-ub-logs witty-ub-uploads witty-ub-results; do
    if docker volume ls --format '{{.Name}}' | grep -qx "$vol"; then
        log_ok "Volume $vol already exists"
    else
        log_info "Creating volume $vol ..."
        docker volume create "$vol"
        log_ok "Volume $vol created"
    fi
done

# 3.3 准备 OpenCode 配置目录
if [ ! -d "$OPENCODE_CONFIG_DIR" ]; then
    log_info "Creating opencode config dir: ${OPENCODE_CONFIG_DIR}"
    mkdir -p "$OPENCODE_CONFIG_DIR"
fi

# 3.4 清理同名旧容器
if docker ps -a --format '{{.Names}}' | grep -qx "${WITTY_CONTAINER_NAME}"; then
    log_warn "Container ${WITTY_CONTAINER_NAME} already exists"
    if docker ps --format '{{.Names}}' | grep -qx "${WITTY_CONTAINER_NAME}"; then
        log_info "Stopping running container ..."
        docker stop "${WITTY_CONTAINER_NAME}"
    fi
    log_info "Removing existing container ..."
    docker rm "${WITTY_CONTAINER_NAME}"
    log_ok "Existing container removed"
fi

# 3.5 自动检测 PG 连接配置（容器内视角）
# 优先级：用户显式配置 > 自动检测（PG 容器 > 宿主机 RPM PG > 默认值）
detect_pg_config() {
    # 如果用户在 deploy.conf 中显式配置了（非空且不是默认 postgres），直接使用
    if [ -n "${PG_HOST_IN_CONTAINER:-}" ] && [ "${PG_HOST_IN_CONTAINER}" != "postgres" ]; then
        log_info "使用 deploy.conf 中配置的 PG 连接: ${PG_HOST_IN_CONTAINER}:${PG_PORT_IN_CONTAINER:-5432}"
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
            log_info "检测到 PostgreSQL 容器（${PG_CONTAINER}）在同一网络，使用容器名连接"
            PG_IN_CONTAINER_HOST="${PG_CONTAINER}"
            PG_IN_CONTAINER_PORT="${PG_PORT_IN_CONTAINER:-5432}"
            return 0
        fi
    fi

    # 检测 2：宿主机是否有 RPM 方式运行的 PostgreSQL
    if command -v systemctl &> /dev/null; then
        PG_RPM_SERVICE=$(systemctl list-units --type=service --state=running 2>/dev/null | grep -o 'postgresql[^ ]*' | head -1 || true)
        if [ -n "$PG_RPM_SERVICE" ]; then
            # 找到宿主机监听端口
            HOST_PG_PORT=$(ss -tlnp 2>/dev/null | grep 'postgres' | head -1 | awk '{print $4}' | rev | cut -d: -f1 | rev)
            if [ -z "$HOST_PG_PORT" ]; then
                HOST_PG_PORT="${PG_PORT:-15432}"
            fi
            # 找到 Docker 网络的网关 IP（容器访问宿主机用）
            DOCKER_GATEWAY=$(docker network inspect "${WITTY_NETWORK}" --format '{{(index .IPAM.Config 0).Gateway}}' 2>/dev/null || true)
            if [ -n "$DOCKER_GATEWAY" ]; then
                log_info "检测到宿主机 RPM PostgreSQL（${PG_RPM_SERVICE}，端口 ${HOST_PG_PORT}），使用 Docker 网关 ${DOCKER_GATEWAY} 连接"
                PG_IN_CONTAINER_HOST="${DOCKER_GATEWAY}"
                PG_IN_CONTAINER_PORT="${HOST_PG_PORT}"
                return 0
            fi
        fi
    fi

    # 兜底：用默认值
    log_warn "未检测到可用的 PostgreSQL，使用默认配置 postgres:5432（请确保 PG 容器在同一网络运行）"
    PG_IN_CONTAINER_HOST="postgres"
    PG_IN_CONTAINER_PORT="5432"
}

detect_pg_config

# 3.6 启动容器
log_info "Starting container ${WITTY_CONTAINER_NAME} ..."

docker run -d \
    --name "${WITTY_CONTAINER_NAME}" \
    --restart unless-stopped \
    -p "${WITTY_HOST_PORT}:8080" \
    -v witty-ub-data:/var/witty-ub/data \
    -v witty-ub-logs:/var/log/witty-ub \
    -v witty-ub-uploads:/var/witty-ub/latency/file/file_upload \
    -v witty-ub-results:/var/witty-ub/latency/file/file_parse_result \
    -v "${OPENCODE_CONFIG_DIR}:/root/.config/opencode" \
    "${EXTRA_MOUNT_ARGS[@]}" \
    -e PYTHONPATH=/var/witty-ub \
    -e LOG_LEVEL="${WITTY_LOG_LEVEL}" \
    -e PG_HOST="${PG_IN_CONTAINER_HOST}" \
    -e PG_PORT="${PG_IN_CONTAINER_PORT}" \
    -e PG_DATABASE="${PG_DATABASE:-witty-ub}" \
    -e PG_USER="${PG_USER:-witty-ub}" \
    -e PG_PASSWORD="${PG_PASSWORD:-witty-ub}" \
    --health-cmd="curl -f http://localhost:9772/health_check" \
    --health-interval=30s \
    --health-timeout=10s \
    --health-retries=3 \
    --health-start-period=40s \
    --network "${WITTY_NETWORK}" \
    "${SELECTED_IMAGE}"

log_ok "Container ${WITTY_CONTAINER_NAME} started"

# 3.7 等待健康
echo ""
log_info "Waiting for witty-ub to become healthy ..."
MAX_WAIT=180
WAITED=0
while [ "$WAITED" -lt "$MAX_WAIT" ]; do
    HEALTH=$(docker inspect --format='{{.State.Health.Status}}' "${WITTY_CONTAINER_NAME}" 2>/dev/null || echo "starting")
    if [ "$HEALTH" = "healthy" ]; then
        break
    fi
    sleep 3
    WAITED=$((WAITED + 3))
    printf "  waiting... %3ds (health: %s)\r" "$WAITED" "$HEALTH"
done
echo ""

if [ "$HEALTH" = "healthy" ]; then
    log_ok "witty-ub is healthy!"
else
    log_warn "witty-ub health status: ${HEALTH} (may still be starting)"
fi

# ---------- 验证连接 ----------
echo ""
echo "========================================"
echo "Verifying connection ..."

for i in {1..15}; do
    if curl -s "http://localhost:${WITTY_HOST_PORT}/health_check" &> /dev/null; then
        log_ok "API connection verified (http://localhost:${WITTY_HOST_PORT})"
        break
    fi
    sleep 2
done

echo ""
echo "========================================"
echo "witty-ub Deployment Completed!"
echo "========================================"
echo "  Container:  ${WITTY_CONTAINER_NAME}"
echo "  Image:      ${SELECTED_IMAGE}"
echo "  Web UI:     http://localhost:${WITTY_HOST_PORT}"
echo "  API:        http://localhost:${WITTY_HOST_PORT}/health_check"
echo "  API Docs:   http://localhost:${WITTY_HOST_PORT}/docs"
echo "  OpenCode:   http://localhost:${WITTY_HOST_PORT}/opencode/"
echo "  Network:    ${WITTY_NETWORK}"
echo "  PG Host:    ${PG_IN_CONTAINER_HOST}:${PG_IN_CONTAINER_PORT} (container)"
if [ ${#EXTRA_MOUNT_ARGS[@]} -gt 0 ]; then
    echo "  Extra mounts:"
    for ((i=1; i<${#EXTRA_MOUNT_ARGS[@]}; i+=2)); do
        echo "    - ${EXTRA_MOUNT_ARGS[$i]}"
    done
fi
echo ""
echo "Useful commands:"
echo "  docker ps                                    # 查看运行中的容器"
echo "  docker logs ${WITTY_CONTAINER_NAME} -f      # 查看容器日志"
echo "  docker stop ${WITTY_CONTAINER_NAME}         # 停止容器"
echo "  docker start ${WITTY_CONTAINER_NAME}        # 启动已停止的容器"
echo "  docker restart ${WITTY_CONTAINER_NAME}      # 重启容器"
echo "  docker exec -it ${WITTY_CONTAINER_NAME} bash  # 进入容器"
echo "========================================"
