#!/bin/bash
# Copyright (c) Huawei Technologies Co., Ltd. 2023-2026. All rights reserved.
# witty-ub 容器一键部署脚本
# 用法:
#   bash deploy/docker/deploy_witty.sh                          # 默认部署 All-in-One
#   bash deploy/docker/deploy_witty.sh --role backend           # 分离部署：仅后端（FastAPI，暴露 9772）
#   bash deploy/docker/deploy_witty.sh --role frontend          # 分离部署：仅前端（Nginx+OpenCode，暴露 32413）
#   bash deploy/docker/deploy_witty.sh --image <custom-image:tag>  # 指定镜像

set -e

# 保留原始命令行参数（自检失败自动回退时要原样再调用一次本脚本）
ORIG_ARGS=("$@")

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
    WITTY_NETWORK_MODE WITTY_SSL_VERIFY WITTY_SECCOMP
    WITTY_NETWORK_MODE_PG WITTY_NETWORK_MODE_APP WITTY_NETWORK_MODE_BACKEND
    WITTY_NETWORK_MODE_FRONTEND WITTY_NETWORK_SELFCHECK WITTY_NETWORK_FALLBACK
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
        # 宿主机 PG 在跑而仓库密钥缺失：系统密钥可能是上一轮容器化 PG 的残留，需告警。
        if host_pg_service_running; then
            log_warn "Host PostgreSQL service detected, but the repo secret is missing: ${REPO_PG_SECRET_FILE}"
            log_warn "Falling back to ${PG_SECRET_FILE}, which may belong to a containerized PG and hold a different password"
            log_warn "If the backend fails with 'password authentication failed', restore the host PG secret or run:"
            log_warn "  sudo bash deploy/deploy_pg.sh --rpm   (or export PG_SECRET_FILE=<correct secret>)"
        fi
    elif pg_secret_exists "$REPO_PG_SECRET_FILE"; then
        PG_SECRET_FILE="$REPO_PG_SECRET_FILE"
        log_warn "${SYSTEM_PG_SECRET_FILE} not found; using repo secret ${PG_SECRET_FILE} (host PG scenario)"
    else
        PG_SECRET_FILE="$SYSTEM_PG_SECRET_FILE"
    fi
fi
PG_SECRET_FILE="${PG_SECRET_FILE:-$SYSTEM_PG_SECRET_FILE}"

# 密钥目标权限：容器化 PG 0440（容器内 postgres uid26/gid0 需组可读），其余 0400（仅属主可读）。
# 最终值在 detect_pg_config 之后确定。
PG_SECRET_MODE="0400"

pg_secret_mode() {
    stat -c '%a' "$PG_SECRET_FILE" 2>/dev/null ||
        stat -f '%Lp' "$PG_SECRET_FILE" 2>/dev/null ||
        sudo -n stat -c '%a' "$PG_SECRET_FILE" 2>/dev/null || true
}

# 设置目标权限并校验
enforce_pg_secret_mode() {
    local want="$1" actual
    chmod "$want" "$PG_SECRET_FILE" 2>/dev/null ||
        sudo -n chmod "$want" "$PG_SECRET_FILE" 2>/dev/null || true
    actual="$(printf '%s' "$(pg_secret_mode)" | tr -d '\r\n')"
    if [ -z "$actual" ] || [ "$((8#${actual}))" -ne "$((8#${want}))" ]; then
        log_error "Cannot set the PG secret file mode to ${want}: ${PG_SECRET_FILE} (actual: ${actual:-unknown})"
        log_error "Run as root (or with passwordless sudo) so the file can be secured, e.g.:"
        log_error "  sudo chmod ${want} ${PG_SECRET_FILE}"
        exit 1
    fi
}

if [ "$ROLE" = "frontend" ]; then
    log_info "Role 'frontend' does not use the database; skipping PG secret checks"
else
    if ! pg_secret_exists "$PG_SECRET_FILE"; then
        log_error "PG secret file not found: ${PG_SECRET_FILE}"
        log_error "For a containerized PG run: bash deploy/deploy_pg.sh --docker"
        log_error "For a host PG run: sudo bash deploy/deploy_pg.sh --rpm"
        exit 1
    fi

    _pg_secret_perms="$(pg_secret_mode)"
    _pg_secret_perms="$(printf '%s' "$_pg_secret_perms" | tr -d '\r\n')"
    if [ -z "$_pg_secret_perms" ]; then
        log_error "Cannot read the mode of the PG secret file: ${PG_SECRET_FILE}"
        log_error "Make sure the current user or 'sudo -n' can access the file (a too-strict parent directory also triggers this)"
        exit 1
    fi
    if [ "$((8#${_pg_secret_perms}))" -gt "$((8#440))" ]; then
        log_warn "PG secret file is too permissive (mode ${_pg_secret_perms}); tightening to 0400"
        enforce_pg_secret_mode "0400"
        _pg_secret_perms="$(printf '%s' "$(pg_secret_mode)" | tr -d '\r\n')"
    fi
    log_info "PG secret file ready: ${PG_SECRET_FILE} (mode ${_pg_secret_perms}, target ${PG_SECRET_MODE})"

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

# ---------- 容器运行时选项（网络模式 / SSL 校验 / seccomp / 自检） ----------
# 枚举项校验: require_enum <变量名> <值> <允许值...>；非法值直接报错退出
require_enum() {
    local _k="$1" _v="$2" IFS='|' _a
    shift 2
    for _a in "$@"; do [ "$_v" = "$_a" ] && return 0; done
    log_error "Invalid ${_k} '${_v}' (expected: $*)"
    exit 1
}
# 布尔开关归一化为 true|false（接受 true/1/yes 与 false/0/no）
normalize_bool() {
    case "$2" in
    true | True | TRUE | 1 | yes | YES) printf -v "$1" '%s' true ;;
    false | False | FALSE | 0 | no | NO) printf -v "$1" '%s' false ;;
    *) log_error "Invalid $1 '$2' (expected: true|false)"; exit 1 ;;
    esac
}
# 网络模式: bridge（默认，接入 WITTY_NETWORK 组网）| host（共享宿主机网络）
WITTY_NETWORK_MODE="${WITTY_NETWORK_MODE:-bridge}"
require_enum WITTY_NETWORK_MODE "$WITTY_NETWORK_MODE" bridge host
# seccomp: default（默认过滤）| unconfined（关闭，兼容旧版 Docker/libseccomp 的 clone3 问题）
WITTY_SECCOMP="${WITTY_SECCOMP:-default}"
require_enum WITTY_SECCOMP "$WITTY_SECCOMP" default unconfined
# 自检失败回退: prompt（提示命令，默认）| auto（自动切 host 重跑一次）| off
WITTY_NETWORK_FALLBACK="${WITTY_NETWORK_FALLBACK:-prompt}"
require_enum WITTY_NETWORK_FALLBACK "$WITTY_NETWORK_FALLBACK" prompt auto off
# SSL 校验交给容器入口翻译为 NODE_TLS_REJECT_UNAUTHORIZED（OpenCode 是 Node 应用）
normalize_bool WITTY_SSL_VERIFY "${WITTY_SSL_VERIFY:-true}"
normalize_bool WITTY_NETWORK_SELFCHECK "${WITTY_NETWORK_SELFCHECK:-true}"

# ---------- 网络模式解析（全局 + 容器级覆盖） ----------
# 优先级: 容器级键（非空）> WITTY_NETWORK_MODE（全局）> bridge；一体只认 _APP，分离同机 _BACKEND 与
# _FRONTEND 必须一致，分离跨机各读本机键（详见 deploy.conf）
WITTY_NETWORK_MODE_GLOBAL="$WITTY_NETWORK_MODE"

for _mode_key in WITTY_NETWORK_MODE_PG WITTY_NETWORK_MODE_APP \
    WITTY_NETWORK_MODE_BACKEND WITTY_NETWORK_MODE_FRONTEND; do
    _mode_val="${!_mode_key:-}"
    [ -n "$_mode_val" ] || continue
    case "$_mode_val" in
    bridge | host) ;;
    *)
        log_error "Invalid ${_mode_key} '${_mode_val}' (expected: bridge|host)"
        exit 1
        ;;
    esac
done
unset _mode_key _mode_val

resolve_mode() {
    local _v="${!1:-}"
    printf '%s' "${_v:-$WITTY_NETWORK_MODE_GLOBAL}"
}

case "$ROLE" in
all)
    if [ -n "${WITTY_NETWORK_MODE_BACKEND:-}" ] || [ -n "${WITTY_NETWORK_MODE_FRONTEND:-}" ]; then
        log_warn "Role 'all' serves backend and frontend in one container; WITTY_NETWORK_MODE_BACKEND/_FRONTEND are ignored (use WITTY_NETWORK_MODE_APP)"
    fi
    WITTY_NETWORK_MODE="$(resolve_mode WITTY_NETWORK_MODE_APP)"
    ;;
backend)
    WITTY_NETWORK_MODE="$(resolve_mode WITTY_NETWORK_MODE_BACKEND)"
    ;;
frontend)
    WITTY_NETWORK_MODE="$(resolve_mode WITTY_NETWORK_MODE_FRONTEND)"
    ;;
esac
PG_EFFECTIVE_MODE="$(resolve_mode WITTY_NETWORK_MODE_PG)"

# 角色派生：容器名、镜像 tag、宿主机端口
# backend 暴露 9772 供前端/外部访问；frontend 默认 32413 与单机部署 32412 错开
case "$ROLE" in
backend)
    CONTAINER_NAME="${WITTY_CONTAINER_NAME}-backend"
    ROLE_TAG="backend"
    HOST_PORT="${WITTY_BACKEND_HOST_PORT:-9772}"
    CONTAINER_PORT="9772"
    ;;
frontend)
    CONTAINER_NAME="${WITTY_CONTAINER_NAME}-frontend"
    ROLE_TAG="frontend"
    HOST_PORT="${WITTY_FRONTEND_HOST_PORT:-32413}"
    CONTAINER_PORT="8080"
    ;;
*)
    CONTAINER_NAME="${WITTY_CONTAINER_NAME}"
    ROLE_TAG="latest"
    HOST_PORT="${WITTY_HOST_PORT}"
    CONTAINER_PORT="8080"
    ;;
esac

# host 模式：端口映射被 Docker 忽略，容器直接占用容器内端口
if [ "$WITTY_NETWORK_MODE" = "host" ]; then
    ACCESS_PORT="${CONTAINER_PORT}"
else
    ACCESS_PORT="${HOST_PORT}"
fi

# frontend 容器内访问后端的地址：显式配置 > host 模式走本机 9772 > 同网络后端容器名
if [ "$ROLE" = "frontend" ]; then
    if [ -n "${WITTY_BACKEND_URL:-}" ]; then
        BACKEND_URL="${WITTY_BACKEND_URL}"
    elif [ "$WITTY_NETWORK_MODE" = "host" ]; then
        BACKEND_URL="http://127.0.0.1:${WITTY_BACKEND_HOST_PORT:-9772}"
    else
        BACKEND_URL="http://${WITTY_CONTAINER_NAME}-backend:9772"
    fi
fi

# ---------- 拓扑判定与同机一致性校验 ----------
# 同机分离时前后端共享宿主机端口空间，网络模式必须一致（混合模式需额外发布后端 9772，本方案不允许）
is_local_host_ref() {
    local _h="$1" _ip
    case "$_h" in 127.0.0.1 | localhost | 0.0.0.0) return 0 ;; esac
    if command -v hostname &>/dev/null; then
        for _ip in $(hostname -I 2>/dev/null); do
            [ "$_ip" = "$_h" ] && return 0
        done
    fi
    return 1
}

detect_topology() {
    case "$ROLE" in
    all) printf 'allinone'; return 0 ;;
    backend) printf 'split-backend'; return 0 ;;
    esac
    local _url="${WITTY_BACKEND_URL:-}" _host
    # 留空 → 前端走容器名反代，必然同机组网
    if [ -z "$_url" ]; then
        printf 'split-local'
        return 0
    fi
    _host="${_url#*://}"
    _host="${_host%%/*}"
    _host="${_host%%:*}"
    case "$_host" in
    *.*)
        # 含点：IP 或域名，只有本机地址才算同机
        if is_local_host_ref "$_host"; then printf 'split-local'; else printf 'split-remote'; fi
        ;;
    *)
        # 无点：Docker 容器名 → 同机组网
        printf 'split-local'
        ;;
    esac
}

validate_modes() {
    local _topo="$1" _fb _ff
    _fb="$(resolve_mode WITTY_NETWORK_MODE_BACKEND)"
    _ff="$(resolve_mode WITTY_NETWORK_MODE_FRONTEND)"
    case "$_topo" in
    allinone | split-remote) return 0 ;; # 一体单容器 / 跨机：不做一致性约束
    split-backend)
        # 后端机：只有本机 deploy.conf 显式声明了前端模式才校验（跨机部署应留空）
        [ -n "${WITTY_NETWORK_MODE_FRONTEND:-}" ] || return 0
        ;;
    split-local) ;; # 同机分离：必须一致，走下面的比较
    *) return 0 ;;
    esac
    if [ "$_fb" != "$_ff" ]; then
        log_error "Same-host split deployment needs one network mode for both containers"
        log_error "  WITTY_NETWORK_MODE_BACKEND=${_fb} / WITTY_NETWORK_MODE_FRONTEND=${_ff}"
        log_error "Fix it in either way:"
        log_error "  a) make both the same, e.g. WITTY_NETWORK_MODE_FRONTEND=\"${_fb}\""
        log_error "  b) leave both empty to inherit WITTY_NETWORK_MODE (${WITTY_NETWORK_MODE_GLOBAL})"
        log_error "Mixed modes would require publishing backend port 9772 on the host, which is not supported"
        exit 1
    fi
}

TOPOLOGY="$(detect_topology)"
case "$TOPOLOGY" in
allinone) TOPOLOGY_DESC="all-in-one (single container)" ;;
split-local) TOPOLOGY_DESC="split, frontend and backend on the same host" ;;
split-remote) TOPOLOGY_DESC="split, cross-host" ;;
split-backend) TOPOLOGY_DESC="split, backend node" ;;
esac
validate_modes "$TOPOLOGY"
log_info "Topology: ${TOPOLOGY_DESC}"
log_info "Effective network mode: app=${WITTY_NETWORK_MODE}, PG container=${PG_EFFECTIVE_MODE}"

# OpenCode 配置目录（宿主机）
OPENCODE_CONFIG_DIR="${OPENCODE_CONFIG_DIR:-$HOME/.config/opencode}"

check_docker() {
    if ! command -v docker &>/dev/null; then
        log_error "Docker not found. Please install Docker first:"
        log_error "  see docs/troubleshooting/02-container-runtime.md (openEuler 24.03 需先配置 docker-ce 仓库)"
        exit 1
    fi
    if ! docker info &>/dev/null; then
        local _err _user
        _err="$(docker info 2>&1 || true)"
        _user="$(id -un 2>/dev/null || echo '<user>')"
        if printf '%s' "$_err" | grep -qiE 'permission denied|docker\.sock'; then
            log_error "Cannot access the Docker daemon socket (permission denied)."
            log_error "Current user '${_user}' is probably not in the 'docker' group:"
            log_error "  sudo usermod -aG docker ${_user} && newgrp docker   # or re-login"
        else
            log_error "Docker daemon is not running. Please start Docker:"
            log_error "  sudo systemctl start docker"
        fi
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

# 运行时参数（网络 / 端口 / seccomp / SSL），由上面的容器运行时选项派生
NETWORK_ARGS=(--network "${WITTY_NETWORK}")
PORT_ARGS=(-p "${HOST_PORT}:${CONTAINER_PORT}")
if [ "$WITTY_NETWORK_MODE" = "host" ]; then
    # host 模式下 -p 会被 Docker 忽略，容器直接占用容器内端口
    NETWORK_ARGS=(--network host)
    PORT_ARGS=()
    log_warn "Network mode 'host': port mapping is ignored; the container binds port ${CONTAINER_PORT} on the host"
    log_warn "  host port ${HOST_PORT} is not used; Web UI/API is served on http://<host-ip>:${ACCESS_PORT}"
fi

SECURITY_OPT_ARGS=()
if [ "$WITTY_SECCOMP" = "unconfined" ]; then
    SECURITY_OPT_ARGS=(--security-opt seccomp=unconfined)
    log_warn "seccomp policy 'unconfined': container syscall filtering is disabled"
fi

# SSL 校验开关交给容器入口翻译为 NODE_TLS_REJECT_UNAUTHORIZED（OpenCode 是 Node 应用）
SSL_ENV_ARGS=(-e "WITTY_SSL_VERIFY=${WITTY_SSL_VERIFY}")
if [ "$WITTY_SSL_VERIFY" = "false" ]; then
    log_warn "WITTY_SSL_VERIFY=false: OpenCode/LLM HTTPS certificate verification will be disabled in the container"
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
if [ "$WITTY_NETWORK_MODE" = "host" ]; then
    log_info "Network mode 'host': skipping Docker network creation"
else
    log_info "Preparing Docker network ..."
    if docker network ls --format '{{.Name}}' | grep -qx "${WITTY_NETWORK}"; then
        log_ok "Network ${WITTY_NETWORK} already exists"
    else
        log_info "Creating network ${WITTY_NETWORK} ..."
        docker network create "${WITTY_NETWORK}"
        log_ok "Network ${WITTY_NETWORK} created"
    fi
fi

# 3.2 准备数据卷
log_info "Preparing Docker volumes ..."
if [ "$ROLE" = "frontend" ]; then
    # frontend 也挂 witty-ub-logs：否则镜像声明的 VOLUME /var/log/witty-ub 会生成匿名卷，
    # 容器重建后日志丢失且残留孤儿卷（与文档"witty-ub-logs 通用"的描述保持一致）。
    ROLE_VOLUMES=(witty-ub-logs witty-ub-experience-data witty-ub-reports)
else
    ROLE_VOLUMES=(witty-ub-data witty-ub-logs witty-ub-uploads witty-ub-results witty-ub-reports)
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
# Docker 网络网关地址（bridge 模式的应用容器访问宿主机用）
docker_network_gateway() {
    docker network inspect "${WITTY_NETWORK}" --format '{{(index .IPAM.Config 0).Gateway}}' 2>/dev/null || true
}

detect_pg_config() {
    local _dock_gw=""
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

    # 按 (PG 容器模式, 应用容器模式) 组合推导访问地址（不再只看应用容器的模式）
    #   host+host→回环 5432；host+bridge→Docker 网关 5432；bridge+host→回环 PG_PORT；bridge+bridge→容器名
    #   （宿主机 RPM PG 走 Docker 网关，见下面的检测 1/2）
    if [ "$PG_EFFECTIVE_MODE" = "host" ] && [ "$WITTY_NETWORK_MODE" = "host" ]; then
        PG_IN_CONTAINER_HOST="127.0.0.1"
        PG_IN_CONTAINER_PORT="${PG_PORT_RPM:-5432}"
        log_info "PG and app are both in host mode: using ${PG_IN_CONTAINER_HOST}:${PG_IN_CONTAINER_PORT}"
        return 0
    fi
    if [ "$PG_EFFECTIVE_MODE" = "host" ] && [ "$WITTY_NETWORK_MODE" = "bridge" ]; then
        _dock_gw="$(docker_network_gateway)"
        if [ -n "$_dock_gw" ]; then
            PG_IN_CONTAINER_HOST="$_dock_gw"
            PG_IN_CONTAINER_PORT="${PG_PORT_RPM:-5432}"
            log_warn "Mixed modes (PG=host, app=bridge): reaching the host PostgreSQL via the Docker gateway ${PG_IN_CONTAINER_HOST}:${PG_IN_CONTAINER_PORT}"
            log_warn "  this combination is not guaranteed; prefer the same mode on both sides"
            return 0
        fi
        log_warn "Mixed modes (PG=host, app=bridge) but the gateway of ${WITTY_NETWORK} is unknown; falling back to auto-detection"
    fi
    if [ "$PG_EFFECTIVE_MODE" = "bridge" ] && [ "$WITTY_NETWORK_MODE" = "host" ]; then
        PG_IN_CONTAINER_HOST="127.0.0.1"
        PG_IN_CONTAINER_PORT="${PG_PORT:-15432}"
        log_warn "Mixed modes (PG=bridge, app=host): using the host-published PG port ${PG_IN_CONTAINER_HOST}:${PG_IN_CONTAINER_PORT}"
        log_warn "  this combination is not guaranteed; prefer the same mode on both sides"
        return 0
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

# 3.5.1 确定密钥最终权限：PG 容器消费 → 0440，其余 → 0400
if [ "$ROLE" != "frontend" ]; then
    if [ "$PG_SECRET_FILE" = "$SYSTEM_PG_SECRET_FILE" ] &&
        docker ps -a --format '{{.Names}}' 2>/dev/null | grep -qx "${PG_CONTAINER_NAME:-postgres}"; then
        PG_SECRET_MODE="0440"
    else
        PG_SECRET_MODE="0400"
    fi
    enforce_pg_secret_mode "$PG_SECRET_MODE"
    log_info "PG secret mode enforced: ${PG_SECRET_FILE} (${PG_SECRET_MODE})"
fi

# 3.6 启动容器
log_info "Starting container ${CONTAINER_NAME} (role: ${ROLE}) ..."

case "$ROLE" in
backend)
    docker run -d \
        --name "${CONTAINER_NAME}" \
        --restart unless-stopped \
        "${PORT_ARGS[@]}" \
        -v witty-ub-data:/var/witty-ub/data \
        -v witty-ub-logs:/var/log/witty-ub \
        -v witty-ub-uploads:/var/witty-ub/latency/file/file_upload \
        -v witty-ub-results:/var/witty-ub/latency/file/file_parse_result \
        -v witty-ub-reports:/var/witty-ub/reports \
        -v "${PG_SECRET_FILE}:/run/secrets/pg_password:ro" \
        "${EXTRA_MOUNT_ARGS[@]}" \
        -e WITTY_ROLE=backend \
        -e PYTHONPATH=/var/witty-ub \
        -e LOG_LEVEL="${WITTY_LOG_LEVEL}" \
        -e PG_HOST="${PG_IN_CONTAINER_HOST}" \
        -e PG_PORT="${PG_IN_CONTAINER_PORT}" \
        -e PG_DATABASE="${PG_DATABASE:-witty-ub}" \
        -e PG_USER="${PG_USER:-witty-ub}" \
        "${SSL_ENV_ARGS[@]}" \
        --health-cmd="curl -f http://localhost:9772/health_check" \
        --health-interval=30s \
        --health-timeout=10s \
        --health-retries=3 \
        --health-start-period=40s \
        "${SECURITY_OPT_ARGS[@]}" \
        "${NETWORK_ARGS[@]}" \
        "${SELECTED_IMAGE}"
    ;;
frontend)
    docker run -d \
        --name "${CONTAINER_NAME}" \
        --restart unless-stopped \
        "${PORT_ARGS[@]}" \
        -v witty-ub-logs:/var/log/witty-ub \
        -v "${OPENCODE_CONFIG_DIR}:/root/.config/opencode" \
        -v witty-ub-experience-data:/var/witty-ub/witty_ub_diagnostician/.opencode/skills/experience-skill/data \
        -v witty-ub-reports:/var/witty-ub/reports \
        "${EXTRA_MOUNT_ARGS[@]}" \
        -e WITTY_ROLE=frontend \
        -e WITTY_BACKEND_URL="${BACKEND_URL}" \
        "${SSL_ENV_ARGS[@]}" \
        "${SECURITY_OPT_ARGS[@]}" \
        "${NETWORK_ARGS[@]}" \
        "${SELECTED_IMAGE}"
    ;;
*)
    docker run -d \
        --name "${CONTAINER_NAME}" \
        --restart unless-stopped \
        "${PORT_ARGS[@]}" \
        -v witty-ub-data:/var/witty-ub/data \
        -v witty-ub-logs:/var/log/witty-ub \
        -v witty-ub-uploads:/var/witty-ub/latency/file/file_upload \
        -v witty-ub-results:/var/witty-ub/latency/file/file_parse_result \
        -v witty-ub-reports:/var/witty-ub/reports \
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
        "${SSL_ENV_ARGS[@]}" \
        --health-cmd="curl -f http://localhost:9772/health_check" \
        --health-interval=30s \
        --health-timeout=10s \
        --health-retries=3 \
        --health-start-period=40s \
        "${SECURITY_OPT_ARGS[@]}" \
        "${NETWORK_ARGS[@]}" \
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
    log_error "Application log /var/log/witty-ub/latency_server.log (last 20 lines):"
    docker exec "${CONTAINER_NAME}" tail -n 20 /var/log/witty-ub/latency_server.log 2>/dev/null |
        sed 's/^/    /' || true
    exit 1
fi

# ---------- 逐链路自检与回退 ----------
# 容器内链路走 docker exec 探 /health_check：200 且响应体含 "status" = 全通；503 = 应用在跑但连不上 PG；
# 拒绝/其他 = 应用或反代没起来（curl 退出码 7）。bridge 模式下容器内端口并不发布到宿主机，故不走宿主机端口
in_container_health() {
    local _port="$1" _out _code _body
    _out="$(docker exec "${CONTAINER_NAME}" curl -s -m 5 --noproxy '*' \
        -w '\n%{http_code}' "http://127.0.0.1:${_port}/health_check" 2>/dev/null || true)"
    _code="${_out##*$'\n'}"
    _body="${_out%$'\n'*}"
    if [ "$_code" = "200" ]; then
        # nginx 的 SPA 回退也会给 200，必须校验响应体确实是本接口
        if printf '%s' "$_body" | grep -q '"status"'; then
            printf '200'
        else
            printf 'noapi:200'
        fi
    elif [ -z "$_code" ] || [ "$_code" = "000" ]; then
        # curl 退出码 7：连接被拒 / 端口无人监听
        printf 'refused'
    else
        printf '%s' "$_code"
    fi
}

selfcheck_verdict() {
    case "$1" in
    200) printf 'ok' ;;
    503) printf 'pg' ;;
    noapi:*) printf 'noapi' ;; # 200 但不是本接口（多为 Nginx SPA 回退）
    *) printf 'down' ;;
    esac
}

# 同机分离部署回退到 host 模式时，前端容器内访问后端的地址（容器名在 host 网络下无法解析）
local_backend_url() { printf 'http://127.0.0.1:%s' "${WITTY_BACKEND_HOST_PORT:-9772}"; }

# 回退到 host 模式要覆盖的环境变量（提示命令与 auto 回退共用这一份推导，避免两处漂移）
fallback_env_pairs() {
    if [ "$ROLE" = "frontend" ]; then
        # 同机分离的一致性校验要求前后端模式相同，两个键必须一起给，否则命令自身会被拦下
        printf 'WITTY_NETWORK_MODE_BACKEND=host WITTY_NETWORK_MODE_FRONTEND=host WITTY_BACKEND_URL=%s' "$(local_backend_url)"
    elif [ "$ROLE" = "backend" ]; then
        printf 'WITTY_NETWORK_MODE_BACKEND=host WITTY_NETWORK_MODE_PG=host'
    else
        printf 'WITTY_NETWORK_MODE_APP=host WITTY_NETWORK_MODE_PG=host'
    fi
}

# 自检失败处理：off=只报错；prompt=给出手工回退命令；auto=自动切 host 重跑一次
netfallback_hint() {
    local _link="$1" _orig="${ORIG_ARGS[*]:-}"

    if [ "$WITTY_NETWORK_FALLBACK" = "off" ]; then
        log_error "Self-check failed on link '${_link}' (WITTY_NETWORK_FALLBACK=off: no remediation attempted)"
        return 0
    fi
    if [ "$TOPOLOGY" = "split-remote" ]; then
        log_error "Self-check failed on link '${_link}'"
        log_warn "Cross-host split deployment: check the backend node address (${BACKEND_URL:-unset}) and the firewall between the two hosts"
        log_warn "Switching this machine to host network mode will not fix a cross-host link"
        return 0
    fi
    if [ "$WITTY_NETWORK_FALLBACK" = "auto" ]; then
        log_warn "Self-check failed on link '${_link}'; WITTY_NETWORK_FALLBACK=auto: recreating with host network mode and retrying once"
        run_fallback_retry
        return 0
    fi

    log_error "Self-check failed on link '${_link}'"
    log_warn "The Docker network is probably untrusted/filtered on this host (docs/troubleshooting/02-container-runtime.md §3)"
    log_warn "Fallback to host network mode with env overrides (deploy.conf is NOT modified):"
    [ "$ROLE" = "frontend" ] || log_warn "  WITTY_NETWORK_MODE_PG=host bash ${DEPLOY_DIR}/../deploy_pg.sh --docker"
    log_warn "  $(fallback_env_pairs) bash ${SCRIPT_DIR}/deploy_witty.sh ${_orig}"
    if [ "$ROLE" = "frontend" ]; then
        log_warn "  (the backend on this host must listen on ${WITTY_BACKEND_HOST_PORT:-9772}: a bridge backend publishes it, a host backend binds it directly)"
    fi
}

# auto 回退：按与提示命令相同的推导设置环境变量后原样重跑（PG 与应用容器都会被重建，数据卷保留）
run_fallback_retry() {
    if [ -n "${WITTY_FALLBACK_APPLIED:-}" ]; then
        log_error "Automatic fallback already applied once; stopping to avoid a rebuild loop"
        return 1
    fi
    export WITTY_FALLBACK_APPLIED=1 WITTY_NETWORK_FALLBACK=off
    # shellcheck disable=SC2046
    export $(fallback_env_pairs)
    if [ "$ROLE" != "frontend" ]; then
        if ! bash "${DEPLOY_DIR}/../deploy_pg.sh" --docker; then
            log_error "Automatic fallback failed while recreating PostgreSQL; please rerun the deployment manually"
            exit 1
        fi
    fi
    bash "${SCRIPT_DIR}/deploy_witty.sh" "${ORIG_ARGS[@]}"
    exit $?
}

run_selfcheck() {
    local _code _verdict
    case "$ROLE" in
    frontend)
        _code="$(in_container_health "${CONTAINER_PORT}")"
        _verdict="$(selfcheck_verdict "$_code")"
        if [ "$_verdict" = "ok" ]; then
            log_ok "Self-check: nginx -> backend OK (HTTP 200, upstream ${BACKEND_URL})"
        elif [ "$_verdict" = "noapi" ]; then
            log_error "Self-check: ${CONTAINER_NAME}:${CONTAINER_PORT} answered 200 but not the API health payload"
            log_error "  nginx is up but /health_check is not reaching the backend upstream (${BACKEND_URL})"
        else
            log_error "Self-check: nginx -> backend failed (HTTP ${_code}), upstream ${BACKEND_URL}"
        fi
        if [ "$_verdict" != "ok" ]; then
            netfallback_hint "frontend -> backend"
            exit 1
        fi
        ;;
    *)
        # 一体/后端容器内 API 固定监听 9772（8080 是 Nginx 前端端口）
        _code="$(in_container_health 9772)"
        _verdict="$(selfcheck_verdict "$_code")"
        case "$_verdict" in
        ok)
            log_ok "Self-check: app -> PostgreSQL OK (HTTP 200, ${PG_IN_CONTAINER_HOST}:${PG_IN_CONTAINER_PORT})"
            ;;
        pg)
            log_error "Self-check: app -> PostgreSQL failed (HTTP 503): the app is up but cannot reach ${PG_IN_CONTAINER_HOST}:${PG_IN_CONTAINER_PORT}"
            log_error "  check the PG container: docker ps | grep ${PG_CONTAINER_NAME:-postgres}"
            netfallback_hint "app -> PostgreSQL"
            exit 1
            ;;
        noapi)
            log_error "Self-check: ${CONTAINER_NAME}:9772 answered 200 but not the API health payload"
            log_error "  another process/proxy is occupying port 9772 instead of the witty-ub API"
            exit 1
            ;;
        *)
            log_error "Self-check: the app inside ${CONTAINER_NAME} did not serve /health_check (HTTP ${_code})"
            log_error "  check: docker logs ${CONTAINER_NAME} --tail 50"
            exit 1
            ;;
        esac
        ;;
    esac
}

# ---------- 验证连接 ----------
echo ""
echo "========================================"
echo "Verifying connection ..."

# frontend 经 Nginx 反代探测远端后端；all/backend 直连本机 API（host 模式用容器内端口 8080/9772）
VERIFY_URL="http://localhost:${ACCESS_PORT}/health_check"
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
    if [ "$WITTY_NETWORK_SELFCHECK" = "true" ]; then
        netfallback_hint "host -> published port ${ACCESS_PORT}"
    fi
    log_error "Container state: $(docker inspect --format='{{.State.Status}} {{if .State.Health}}{{.State.Health.Status}}{{end}}' "${CONTAINER_NAME}" 2>/dev/null || echo unknown)"
    log_error "Container logs (last 20 lines):"
    docker logs --tail 20 "${CONTAINER_NAME}" 2>&1 | sed 's/^/    /' || true
    log_error "Application log /var/log/witty-ub/latency_server.log (last 20 lines):"
    docker exec "${CONTAINER_NAME}" tail -n 20 /var/log/witty-ub/latency_server.log 2>/dev/null |
        sed 's/^/    /' || true
    exit 1
fi

# 逐链路自检：宿主机端口通了，但容器内到 PG / 后端的链路可能仍然断
if [ "$WITTY_NETWORK_SELFCHECK" = "true" ]; then
    run_selfcheck
fi

echo ""
echo "========================================"
echo "witty-ub Deployment Completed! (role: ${ROLE})"
echo "========================================"
echo "  Container:  ${CONTAINER_NAME}"
echo "  Image:      ${SELECTED_IMAGE}"
if [ "$ROLE" != "backend" ]; then
    echo "  Web UI:     http://localhost:${ACCESS_PORT}"
    echo "  API:        http://localhost:${ACCESS_PORT}/health_check"
    echo "  Agent API:  http://localhost:${ACCESS_PORT}/agent-api/ (OpenCode via Nginx)"
fi
if [ "$ROLE" = "backend" ]; then
    echo "  API:        http://localhost:${ACCESS_PORT}/health_check (port 9772, proxied by the frontend node)"
fi
if [ "$ROLE" = "frontend" ]; then
    echo "  Backend:    ${BACKEND_URL} (nginx upstream inside the frontend container)"
fi

echo "  Topology:   ${TOPOLOGY_DESC}"
echo "  Self-check: ${WITTY_NETWORK_SELFCHECK} (fallback: ${WITTY_NETWORK_FALLBACK})"
if [ "$WITTY_NETWORK_MODE" = "host" ]; then
    echo "  Network:    host (shares the host network; port mapping disabled)"
else
    echo "  Network:    ${WITTY_NETWORK} (bridge)"
fi
if [ "$ROLE" != "frontend" ]; then
    if [ "$PG_EFFECTIVE_MODE" = "$WITTY_NETWORK_MODE" ]; then
        echo "  PG network: ${PG_EFFECTIVE_MODE}"
    else
        echo "  PG network: ${PG_EFFECTIVE_MODE} (mixed with the app mode; not covered by the deployment guarantees)"
    fi
fi
echo "  seccomp:    ${WITTY_SECCOMP}"
echo "  SSL verify: ${WITTY_SSL_VERIFY}"
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
