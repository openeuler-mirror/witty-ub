#!/bin/bash
# Copyright (c) Huawei Technologies Co., Ltd. 2023-2026. All rights reserved.
# witty-ub 部署管理器（交互式菜单）
#
# 直接运行: bash deploy/docker/manage.sh

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
DEPLOY_DIR="$SCRIPT_DIR"
CONF_FILE="${DEPLOY_DIR}/../deploy.conf"
[ -f "$CONF_FILE" ] || CONF_FILE="${DEPLOY_DIR}/../pg.conf" # 兼容旧名

# 保存环境变量传入的值（优先级高于配置文件）。deploy.conf 会覆盖同名 shell 变量，
# 因此必须按清单快照并回填，否则 `WITTY_BACKEND_URL=… bash manage.sh install-frontend`
# 这类命令中的值会被配置文件里的空值/默认值悄悄吃掉。
# 说明：不使用关联数组（bash 3.2 / macOS 自带 bash 不支持），改用 "KEY=VALUE" 行列表。
CONFIG_KEYS=(
    WITTY_HOST_PORT WITTY_EXTRA_MOUNTS WITTY_IMAGE WITTY_LOG_LEVEL WITTY_CONTAINER_NAME
    WITTY_BACKEND_URL WITTY_BACKEND_HOST_PORT WITTY_FRONTEND_HOST_PORT WITTY_NETWORK
    PG_HOST PG_PORT PG_DATABASE PG_USER PG_PASSWORD PG_SECRET_FILE
    PG_HOST_IN_CONTAINER PG_PORT_IN_CONTAINER PG_CONTAINER_NAME PG_NETWORK PG_VOLUME
    OPENCODE_CONFIG_DIR
)
ENV_OVERRIDES=""
for _key in "${CONFIG_KEYS[@]}"; do
    [ -n "${!_key:-}" ] || continue
    ENV_OVERRIDES="${ENV_OVERRIDES}${_key}=${!_key}"$'\n'
done
unset _key

# 把快照回填到当前 shell 并导出给子脚本（deploy_witty.sh / deploy_pg.sh）
restore_env_overrides() {
    local _line _k _v
    while IFS= read -r _line; do
        [ -n "$_line" ] || continue
        _k="${_line%%=*}"
        _v="${_line#*=}"
        printf -v "$_k" '%s' "$_v"
        export "${_k?}"
    done <<EOF
${ENV_OVERRIDES}
EOF
}

PG_CONTAINER="${PG_CONTAINER_NAME:-postgres}"
WITTY_CONTAINER="${WITTY_CONTAINER_NAME:-witty-ub}"
# 分离部署角色容器（deploy_witty.sh --role backend/frontend）
WITTY_BACKEND_CONTAINER="${WITTY_CONTAINER_NAME:-witty-ub}-backend"
WITTY_FRONTEND_CONTAINER="${WITTY_CONTAINER_NAME:-witty-ub}-frontend"
PG_VOLUME="${PG_VOLUME:-pg15-data}"

# ---------- 全局选项：-y / --yes 跳过确认（卸载类命令在非交互环境下必需） ----------
ASSUME_YES=0
_cli_args=()
for _arg in "$@"; do
    case "$_arg" in
    -y | --yes) ASSUME_YES=1 ;;
    *) _cli_args+=("$_arg") ;;
    esac
done
unset _arg
if [ ${#_cli_args[@]} -gt 0 ]; then
    set -- "${_cli_args[@]}"
else
    set --
fi
unset _cli_args

# ---------- 加载配置 ----------
if [ -f "$CONF_FILE" ]; then
    # --help/help 时不打印配置加载日志，保持帮助输出干净
    case "${1:-}" in
    -h | --help | help) ;;
    *) echo "[INFO]  Loading config from ${CONF_FILE}" ;;
    esac
    # shellcheck disable=SC1090
    source "$CONF_FILE"
fi

# 环境变量优先级高于配置文件（导出给 deploy_witty.sh / deploy_pg.sh 子进程）
restore_env_overrides
unset ENV_OVERRIDES CONFIG_KEYS

# ---------- 工具函数 ----------
log_info() { echo "[INFO]  $*"; }
log_ok() { echo "[OK]    $*"; }
log_warn() { echo "[WARN]  $*"; }
log_error() { echo "[ERROR] $*"; }

sep() { echo "----------------------------------------"; }

check_docker() {
    if ! command -v docker &>/dev/null; then
        log_error "Docker not found. Please install Docker first."
        return 1
    fi
    if ! docker info &>/dev/null; then
        local _err _user
        _err="$(docker info 2>&1 || true)"
        _user="$(id -un 2>/dev/null || echo '<user>')"
        if printf '%s' "$_err" | grep -qiE 'permission denied|docker\.sock'; then
            log_error "Cannot access the Docker daemon socket (permission denied)."
            log_error "Current user '${_user}' is probably not in the 'docker' group."
            log_error "  sudo usermod -aG docker ${_user} && newgrp docker   # or re-login"
        else
            log_error "Docker daemon is not running."
            log_error "  sudo systemctl start docker"
        fi
        return 1
    fi
    return 0
}

container_exists() {
    docker ps -a --format '{{.Names}}' 2>/dev/null | grep -qx "$1"
}

container_running() {
    docker ps --format '{{.Names}}' 2>/dev/null | grep -qx "$1"
}

container_health() {
    docker inspect --format='{{.State.Health.Status}}' "$1" 2>/dev/null || echo "unknown"
}

volume_exists() {
    docker volume ls --format '{{.Name}}' 2>/dev/null | grep -qx "$1"
}

get_container_image() {
    docker inspect --format='{{.Config.Image}}' "$1" 2>/dev/null || echo ""
}

remove_image_if_unused() {
    local image="$1"
    if [ -z "$image" ]; then
        return
    fi
    # 检查该镜像是否还被其他容器使用
    local used_by
    used_by=$(docker ps -a --format '{{.Image}}' 2>/dev/null | grep -Fx "$image" || true)
    if [ -z "$used_by" ]; then
        log_info "Removing image: $image"
        docker rmi "$image" 2>/dev/null || true
        log_ok "Removed image: $image"
    else
        log_warn "Image $image is still used by other containers; skipping removal"
    fi
}

confirm() {
    local msg="$1"
    if [ "${ASSUME_YES:-0}" = "1" ]; then
        log_info "${msg} (auto-confirmed by --yes)"
        return 0
    fi
    echo ""
    ask "${msg} (y/N): " choice
    case "$choice" in
    [yY][eE][sS] | [yY]) return 0 ;;
    *) return 1 ;;
    esac
}

# 交互输入：无 TTY（CI / ssh 非交互 / 管道）时 read 会失败，配合 set -e 会直接终止
# 脚本；这里统一吞掉失败，让"回车取默认值"的语义在脚本里也成立。
ask() {
    local prompt="$1" var="$2"
    # shellcheck disable=SC2162,SC2229
    read -r -p "$prompt" "$var" || true
}

# 提示当前处于非交互输入模式（所有提示取默认值 / 环境变量 / deploy.conf）
noninteractive_hint() {
    if [ ! -t 0 ]; then
        log_info "Non-interactive input: all prompts use their defaults (override with env vars or deploy.conf)"
    fi
}

# ============================================================
# 安装
# ============================================================
do_install_all() {
    sep
    echo "One-shot install: PostgreSQL + witty-ub (Docker)"
    sep
    check_docker || return 1
    echo ""
    if ! bash "${DEPLOY_DIR}/../deploy_pg.sh" --docker; then
        log_error "PostgreSQL deployment failed; aborting the one-shot install (witty-ub will not be deployed)"
        return 1
    fi
    echo ""
    if ! bash "${DEPLOY_DIR}/deploy_witty.sh"; then
        log_error "witty-ub deployment failed; check the log above and retry"
        return 1
    fi
    sep
    log_ok "One-shot install completed!"
    show_status
}

do_install_pg() {
    sep
    echo "Install: PostgreSQL"
    sep
    echo ""
    echo "Select install method:"
    echo "  1) Docker container (recommended)"
    echo "  2) RPM package (requires sudo)"
    echo ""
    ask "Select [1-2, default 1]: " choice
    choice="${choice:-1}"
    case "$choice" in
    1)
        check_docker || return 1
        bash "${DEPLOY_DIR}/../deploy_pg.sh" --docker
        ;;
    2) sudo bash "${DEPLOY_DIR}/../deploy_pg.sh" --rpm ;;
    *) log_error "Invalid option" ;;
    esac
}

do_install_witty() {
    sep
    echo "Install: witty-ub"
    sep
    check_docker || return 1

    # ---------- 交互式配置 ----------
    echo ""
    echo "┌─────────────────────────────────────────────────────┐"
    echo "│    witty-ub deployment parameters                   │"
    echo "│    Press Enter to use the default shown in [ ]      │"
    echo "└─────────────────────────────────────────────────────┘"
    echo ""

    default_port="${WITTY_HOST_PORT:-32412}"
    noninteractive_hint
    ask "  [1] Host port          [${default_port}]: " input_port
    WITTY_HOST_PORT="${input_port:-${default_port}}"

    default_mounts="${WITTY_EXTRA_MOUNTS:-}"
    echo ""
    echo "  [2] Extra directory mounts (container access to host logs/data)"
    echo "      Format: host_path:container_path[:ro|rw], space-separated"
    echo "      ro=read-only (recommended), rw=read-write, empty=skip"
    if [ -n "${default_mounts}" ]; then
        ask "                         [${default_mounts}]: " input_mounts
    else
        ask "                         [skip if empty]: " input_mounts
    fi
    WITTY_EXTRA_MOUNTS="${input_mounts:-${default_mounts}}"

    default_image="${WITTY_IMAGE:-}"
    echo ""
    if [ -n "${default_image}" ]; then
        ask "  [3] Image            [${default_image}]: " input_image
    else
        ask "  [3] Image            [auto-select if empty]: " input_image
    fi
    WITTY_IMAGE="${input_image:-${default_image}}"

    # ---------- 配置汇总 ----------
    echo ""
    echo "┌─────────────────────────────────────────────────────┐"
    echo "│    Configuration summary                            │"
    echo "├─────────────────────────────────────────────────────┤"
    printf "│  %-19s %-30s │\n" "Host port" "${WITTY_HOST_PORT}"
    printf "│  %-19s %-30s │\n" "Image" "${WITTY_IMAGE:-auto}"
    if [ -n "${WITTY_EXTRA_MOUNTS}" ]; then
        first=1
        for m in ${WITTY_EXTRA_MOUNTS}; do
            if [ "$first" -eq 1 ]; then
                printf "│  %-19s %-30s │\n" "Extra mounts" "${m}"
                first=0
            else
                printf "│  %-19s %-30s │\n" "" "${m}"
            fi
        done
    else
        printf "│  %-19s %-30s │\n" "Extra mounts" "none"
    fi
    echo "└─────────────────────────────────────────────────────┘"
    echo ""

    # ---------- 检测 PostgreSQL ----------
    PG_DETECTED="unknown"
    PG_DETAIL=""
    if container_running "$PG_CONTAINER"; then
        PG_DETECTED="container"
        PG_DETAIL="docker container (${PG_CONTAINER})"
        log_ok "Detected PostgreSQL: ${PG_DETAIL}"
    fi
    if [ "$PG_DETECTED" = "unknown" ] && command -v systemctl &>/dev/null; then
        PG_RPM=$(systemctl list-units --type=service --state=running 2>/dev/null | grep -o 'postgresql[^ ]*' | head -1 || true)
        if [ -n "$PG_RPM" ]; then
            PG_DETECTED="rpm"
            PG_PORT_DETECTED=$(ss -tlnp 2>/dev/null | grep 'postgres' | head -1 | awk '{print $4}' | rev | cut -d: -f1 | rev)
            PG_DETAIL="host service (${PG_RPM}, port ${PG_PORT_DETECTED:-${PG_PORT_RPM:-5432}})"
            log_ok "Detected PostgreSQL: ${PG_DETAIL}"
        fi
    fi

    if [ "$PG_DETECTED" = "unknown" ]; then
        log_warn "No running PostgreSQL detected"
        log_warn "witty-ub may fail to connect to the database after start"
        if ! confirm "Continue?"; then
            return 0
        fi
    fi

    # ---------- 导出环境变量并调用部署脚本 ----------
    export WITTY_HOST_PORT WITTY_EXTRA_MOUNTS WITTY_IMAGE
    bash "${DEPLOY_DIR}/deploy_witty.sh"
}

# ============================================================
# 分离部署（前后端分角色）
# ============================================================
do_install_witty_role() {
    local role="$1"
    sep
    echo "Install: witty-ub ${role} (split frontend/backend deployment)"
    sep
    check_docker || return 1

    echo ""
    echo "┌─────────────────────────────────────────────────────┐"
    echo "│    witty-ub ${role} deployment parameters           │"
    echo "│    Press Enter to use the default shown in [ ]      │"
    echo "└─────────────────────────────────────────────────────┘"
    echo ""

    local default_port input_port input_image input_backend_url
    if [ "$role" = "backend" ]; then
        default_port="${WITTY_BACKEND_HOST_PORT:-9772}"
        noninteractive_hint
        ask "  [1] Host port          [${default_port}]: " input_port
        WITTY_BACKEND_HOST_PORT="${input_port:-${default_port}}"

        echo ""
        ask "  [2] Image            [${WITTY_IMAGE:-auto-select witty-ub:backend if empty}]: " input_image
        WITTY_IMAGE="${input_image:-${WITTY_IMAGE:-}}"

        export WITTY_BACKEND_HOST_PORT WITTY_IMAGE
    else
        default_port="${WITTY_FRONTEND_HOST_PORT:-32413}"
        noninteractive_hint
        ask "  [1] Host port          [${default_port}]: " input_port
        WITTY_FRONTEND_HOST_PORT="${input_port:-${default_port}}"

        echo ""
        echo "  [2] Backend URL (frontend nginx upstream)"
        echo "      Same-machine split default: http://witty-ub-backend:9772"
        echo "      Cross-machine: http://<backend-ip>:9772"
        ask "  [2] Backend URL         [${WITTY_BACKEND_URL:-default}]: " input_backend_url
        WITTY_BACKEND_URL="${input_backend_url:-${WITTY_BACKEND_URL:-}}"

        echo ""
        ask "  [3] Image            [${WITTY_IMAGE:-auto-select witty-ub:frontend if empty}]: " input_image
        WITTY_IMAGE="${input_image:-${WITTY_IMAGE:-}}"

        export WITTY_FRONTEND_HOST_PORT WITTY_BACKEND_URL WITTY_IMAGE
    fi

    bash "${DEPLOY_DIR}/deploy_witty.sh" --role "${role}"
}

# ============================================================
# 卸载
# ============================================================
do_uninstall_all() {
    sep
    echo "Uninstall everything: remove all containers and data"
    sep
    check_docker || return 1
    echo ""

    echo "Select uninstall scope:"
    echo "  1) Containers + volumes (recommended)"
    echo "  2) Containers + volumes + images"
    echo ""
    ask "Select [1-2, default 1]: " scope
    scope="${scope:-1}"

    echo ""
    log_warn "About to delete:"
    echo "  - Containers: ${WITTY_CONTAINER}, ${WITTY_BACKEND_CONTAINER} (split), ${WITTY_FRONTEND_CONTAINER} (split), ${PG_CONTAINER}"
    echo "  - Volumes: witty-ub-data, witty-ub-logs, witty-ub-uploads, witty-ub-results, witty-ub-experience-data, ${PG_VOLUME}"
    if [ "$scope" = "2" ]; then
        echo "  - Images: images used by the containers above"
    fi
    echo ""
    if ! confirm "Delete everything? This cannot be undone!"; then
        log_info "Cancelled"
        return 0
    fi

    # 先记录每个容器使用的镜像（删容器后就查不到了）。
    # 用并列数组保存 容器名/镜像名，避免关联数组（bash 3.2 不支持）。
    local -a _doomed_names=() _doomed_images=()
    local _idx
    for c in "$WITTY_CONTAINER" "$WITTY_BACKEND_CONTAINER" "$WITTY_FRONTEND_CONTAINER" "$PG_CONTAINER"; do
        if container_exists "$c"; then
            _doomed_names+=("$c")
            _doomed_images+=("$(get_container_image "$c")")
        fi
    done

    # 先停 witty（含分离角色容器）再停 pg（优雅关闭）
    for c in "$WITTY_CONTAINER" "$WITTY_BACKEND_CONTAINER" "$WITTY_FRONTEND_CONTAINER" "$PG_CONTAINER"; do
        if container_exists "$c"; then
            log_info "Removing container: $c"
            docker rm -f "$c" &>/dev/null
            log_ok "Removed: $c"
        fi
    done

    # 删除所有数据卷
    for v in witty-ub-data witty-ub-logs witty-ub-uploads witty-ub-results witty-ub-experience-data "$PG_VOLUME"; do
        if volume_exists "$v"; then
            log_info "Removing volume: $v"
            docker volume rm "$v" &>/dev/null
            log_ok "Removed: $v"
        fi
    done

    # 删除镜像（如果选了选项 2）
    if [ "$scope" = "2" ]; then
        for _idx in "${!_doomed_names[@]}"; do
            if [ -n "${_doomed_images[$_idx]}" ]; then
                remove_image_if_unused "${_doomed_images[$_idx]}"
            fi
        done
    fi

    sep
    log_ok "Uninstall completed"
}

do_uninstall_witty() {
    sep
    echo "Uninstall: witty-ub containers (including split role containers)"
    sep
    check_docker || return 1

    # 收集实际存在的 witty-ub* 容器
    local targets=()
    local c
    for c in "$WITTY_CONTAINER" "$WITTY_BACKEND_CONTAINER" "$WITTY_FRONTEND_CONTAINER"; do
        container_exists "$c" && targets+=("$c")
    done
    if [ ${#targets[@]} -eq 0 ]; then
        log_warn "No witty-ub containers found (${WITTY_CONTAINER} / ${WITTY_BACKEND_CONTAINER} / ${WITTY_FRONTEND_CONTAINER})"
        return 0
    fi

    echo ""
    echo "Found the following witty-ub containers:"
    local idx=1
    for c in "${targets[@]}"; do
        echo "  ${idx}) $c"
        idx=$((idx + 1))
    done
    echo ""
    echo "Select uninstall scope:"
    echo "  a) Remove all (keep volumes)"
    echo "  or a number to remove a single container"
    echo ""
    ask "Select [a or 1-${#targets[@]}, default a]: " pick
    pick="${pick:-a}"

    local to_remove=()
    if [ "$pick" = "a" ]; then
        to_remove=("${targets[@]}")
    elif [[ "$pick" =~ ^[0-9]+$ ]] && [ "$pick" -ge 1 ] && [ "$pick" -le ${#targets[@]} ]; then
        to_remove=("${targets[$((pick - 1))]}")
    else
        log_error "Invalid option"
        return 1
    fi

    echo ""
    echo "Select what to remove:"
    echo "  1) Containers only (keep volumes and images)"
    echo "  2) Containers + images (keep volumes)"
    echo ""
    ask "Select [1-2, default 1]: " scope
    scope="${scope:-1}"

    local img
    for c in "${to_remove[@]}"; do
        img=""
        if [ "$scope" = "2" ]; then
            img=$(get_container_image "$c")
        fi
        log_info "Removing container: $c"
        docker rm -f "$c"
        log_ok "$c removed (volumes kept)"
        if [ "$scope" = "2" ] && [ -n "$img" ]; then
            remove_image_if_unused "$img"
        fi
    done
}

do_uninstall_pg() {
    sep
    echo "Uninstall: PostgreSQL container"
    sep
    check_docker || return 1

    if ! container_exists "$PG_CONTAINER"; then
        log_warn "Container ${PG_CONTAINER} does not exist"
        return 0
    fi

    # 先记录使用的镜像
    local pg_image
    pg_image=$(get_container_image "$PG_CONTAINER")

    echo ""
    echo "Select:"
    echo "  1) Containers only (keep volumes and images)"
    echo "  2) Containers + volumes (keep images)"
    echo "  3) Containers + volumes + images (remove everything)"
    echo ""
    ask "Select [1-3, default 1]: " choice
    choice="${choice:-1}"

    case "$choice" in
    1)
        log_info "Removing container: ${PG_CONTAINER}"
        docker rm -f "$PG_CONTAINER"
        log_ok "PostgreSQL container removed (volume and image kept)"
        ;;
    2)
        if confirm "Delete the PostgreSQL container and its volume?"; then
            log_info "Removing container: ${PG_CONTAINER}"
            docker rm -f "$PG_CONTAINER" &>/dev/null
            if volume_exists "$PG_VOLUME"; then
                log_info "Removing volume: ${PG_VOLUME}"
                docker volume rm "$PG_VOLUME"
            fi
            log_ok "PostgreSQL container and volume removed (image kept)"
        fi
        ;;
    3)
        if confirm "Delete the PostgreSQL container, volume and image? This cannot be undone!"; then
            log_info "Removing container: ${PG_CONTAINER}"
            docker rm -f "$PG_CONTAINER" &>/dev/null
            if volume_exists "$PG_VOLUME"; then
                log_info "Removing volume: ${PG_VOLUME}"
                docker volume rm "$PG_VOLUME"
            fi
            if [ -n "$pg_image" ]; then
                remove_image_if_unused "$pg_image"
            fi
            log_ok "PostgreSQL container, volume and image removed"
        fi
        ;;
    *)
        log_error "Invalid option"
        ;;
    esac
}

# ============================================================
# 启停/重启/状态/日志
# ============================================================
do_start() {
    check_docker || return 1
    local -a start_targets=("$PG_CONTAINER" "$WITTY_CONTAINER" "$WITTY_BACKEND_CONTAINER" "$WITTY_FRONTEND_CONTAINER")
    local c
    for c in "${start_targets[@]}"; do
        if container_exists "$c"; then
            if container_running "$c"; then
                log_ok "$c is already running"
            else
                log_info "Starting: $c"
                docker start "$c" &>/dev/null
                log_ok "Started: $c"
            fi
        elif [ "$c" = "$PG_CONTAINER" ] || [ "$c" = "$WITTY_CONTAINER" ]; then
            log_warn "$c container does not exist, install it first"
        fi
    done
}

do_stop() {
    check_docker || return 1
    local -a stop_targets=("$WITTY_CONTAINER" "$WITTY_BACKEND_CONTAINER" "$WITTY_FRONTEND_CONTAINER")
    local c
    for c in "${stop_targets[@]}"; do
        if container_running "$c"; then
            log_info "Stopping: $c"
            docker stop "$c" &>/dev/null
            log_ok "Stopped: $c"
        elif container_exists "$c"; then
            log_info "$c is stopped"
        fi
    done
    if container_running "$PG_CONTAINER"; then
        log_info "Stopping: $PG_CONTAINER"
        docker stop "$PG_CONTAINER" &>/dev/null
        log_ok "Stopped: $PG_CONTAINER"
    elif container_exists "$PG_CONTAINER"; then
        log_info "$PG_CONTAINER is stopped"
    fi
}

do_restart() {
    check_docker || return 1
    local -a restart_targets=("$WITTY_CONTAINER" "$WITTY_BACKEND_CONTAINER" "$WITTY_FRONTEND_CONTAINER" "$PG_CONTAINER")
    local c
    for c in "${restart_targets[@]}"; do
        if container_exists "$c"; then
            log_info "Restarting: $c"
            docker restart "$c" &>/dev/null
            log_ok "Restarted: $c"
        elif [ "$c" = "$PG_CONTAINER" ] || [ "$c" = "$WITTY_CONTAINER" ]; then
            log_warn "$c container does not exist"
        fi
    done
}

show_status() {
    check_docker || return 1
    sep
    printf "%-15s %-10s %-12s %s\n" "CONTAINER" "STATUS" "HEALTH" "PORTS"
    sep
    for c in "$PG_CONTAINER" "$WITTY_CONTAINER" "$WITTY_BACKEND_CONTAINER" "$WITTY_FRONTEND_CONTAINER"; do
        # 分离角色容器仅在已创建时显示
        if { [ "$c" = "$WITTY_BACKEND_CONTAINER" ] || [ "$c" = "$WITTY_FRONTEND_CONTAINER" ]; } && ! container_exists "$c"; then
            continue
        fi
        if container_exists "$c"; then
            if container_running "$c"; then
                status="running"
                health=$(container_health "$c")
                ports=$(docker port "$c" 2>/dev/null | head -1 || echo "")
            else
                status="stopped"
                health="-"
                ports="-"
            fi
            printf "%-15s %-10s %-12s %s\n" "$c" "$status" "$health" "$ports"
        else
            printf "%-15s %-10s %-12s %s\n" "$c" "not found" "-" "-"
        fi
    done
    sep

    # 从 docker port 获取实际映射端口
    local actual_port=""
    if container_running "$WITTY_CONTAINER"; then
        actual_port=$(docker port "$WITTY_CONTAINER" 2>/dev/null | grep '8080' | sed 's/.*://' | head -1 || true)
    fi
    actual_port="${actual_port:-${WITTY_HOST_PORT:-32412}}"

    echo ""
    echo "Access URLs:"
    echo "  Web UI:   http://localhost:${actual_port}"
    echo "  API:      http://localhost:${actual_port}/health_check"
    echo "  Agent API: http://localhost:${actual_port}/agent-api/ (OpenCode via Nginx)"
    if container_running "$WITTY_FRONTEND_CONTAINER"; then
        local fe_port
        fe_port=$(docker port "$WITTY_FRONTEND_CONTAINER" 2>/dev/null | grep '8080' | sed 's/.*://' | head -1 || true)
        echo "  Split frontend: http://localhost:${fe_port:-${WITTY_FRONTEND_HOST_PORT:-32413}} (proxying witty-ub-backend)"
    fi
}

do_logs() {
    check_docker || return 1
    echo ""
    echo "Select logs to view:"
    echo "  1) PostgreSQL"
    echo "  2) witty-ub"
    if container_exists "$WITTY_BACKEND_CONTAINER"; then
        echo "  3) witty-ub-backend (split backend)"
    fi
    if container_exists "$WITTY_FRONTEND_CONTAINER"; then
        echo "  4) witty-ub-frontend (split frontend)"
    fi
    echo ""
    ask "Select [default 2]: " choice
    choice="${choice:-2}"
    case "$choice" in
    1) container="$PG_CONTAINER" ;;
    2) container="$WITTY_CONTAINER" ;;
    3) container="$WITTY_BACKEND_CONTAINER" ;;
    4) container="$WITTY_FRONTEND_CONTAINER" ;;
    *)
        log_error "Invalid option"
        return 1
        ;;
    esac

    if container_exists "$container"; then
        log_info "Showing logs of $container (Ctrl+C to exit)"
        docker logs -f "$container"
    else
        log_error "Container $container does not exist"
    fi
}

do_psql() {
    check_docker || return 1
    if ! container_running "$PG_CONTAINER"; then
        log_error "PostgreSQL container is not running"
        return 1
    fi
    log_info "Entering psql (type \q to quit)"
    docker exec -it "$PG_CONTAINER" psql -U "${PG_USER:-witty-ub}" -d "${PG_DATABASE:-witty-ub}"
}

do_shell() {
    check_docker || return 1
    echo ""
    echo "Select the container to enter:"
    echo "  1) PostgreSQL"
    echo "  2) witty-ub"
    echo ""
    ask "Select [1-2, default 2]: " choice
    choice="${choice:-2}"
    case "$choice" in
    1) container="$PG_CONTAINER" ;;
    2) container="$WITTY_CONTAINER" ;;
    *)
        log_error "Invalid option"
        return 1
        ;;
    esac

    if container_running "$container"; then
        log_info "Entering $container (type 'exit' to leave)"
        docker exec -it "$container" bash
    else
        log_error "Container $container is not running"
    fi
}

# ============================================================
# 主菜单
# ============================================================
show_menu() {
    echo ""
    echo "========================================"
    echo "  witty-ub Deployment Manager"
    echo "========================================"
    echo ""
    echo "  📦  Install"
    echo "    1) One-shot install: PG + witty-ub (Docker)"
    echo "    2) Install PostgreSQL only"
    echo "    3) Install witty-ub only"
    echo ""
    echo "  🗑️  Uninstall"
    echo "    4) Uninstall everything (including data)"
    echo "    5) Uninstall witty-ub containers only"
    echo "    6) Uninstall the PostgreSQL container only"
    echo ""
    echo "  🔧  Manage"
    echo "    7) Start all"
    echo "    8) Stop all"
    echo "    9) Restart all containers"
    echo "   10) Show status"
    echo "   11) Show logs"
    echo ""
    echo "  💻  Tools"
    echo "   12) Open psql (PG)"
    echo "   13) Open container shell"
    echo ""
    echo "  🔀  Split frontend/backend deployment"
    echo "   14) Install the witty-ub backend only (role=backend)"
    echo "   15) Install the witty-ub frontend only (role=frontend)"
    echo ""
    echo "    0) Quit"
    echo ""
    echo "========================================"
}

main() {
    while true; do
        show_menu
        ask "Select an action [0-15]: " choice
        echo ""
        case "$choice" in
        1) do_install_all ;;
        2) do_install_pg ;;
        3) do_install_witty ;;
        4) do_uninstall_all ;;
        5) do_uninstall_witty ;;
        6) do_uninstall_pg ;;
        7) do_start ;;
        8) do_stop ;;
        9) do_restart ;;
        10) show_status ;;
        11) do_logs ;;
        12) do_psql ;;
        13) do_shell ;;
        14) do_install_witty_role backend ;;
        15) do_install_witty_role frontend ;;
        0)
            echo "Bye!"
            exit 0
            ;;
        *)
            log_error "Invalid option, please try again"
            ;;
        esac
        echo ""
        ask "Press Enter to continue..." _
    done
}

# 如果直接带参数运行，走命令行模式
if [ $# -gt 0 ]; then
    case "$1" in
    install | install-all) do_install_all ;;
    install-pg) do_install_pg ;;
    install-witty) do_install_witty ;;
    install-backend) do_install_witty_role backend ;;
    install-frontend) do_install_witty_role frontend ;;
    uninstall | uninstall-all) do_uninstall_all ;;
    uninstall-witty) do_uninstall_witty ;;
    uninstall-pg) do_uninstall_pg ;;
    start) do_start ;;
    stop) do_stop ;;
    restart) do_restart ;;
    status) show_status ;;
    logs) do_logs ;;
    psql) do_psql ;;
    shell) do_shell ;;
    -h | --help | help)
        cat <<EOF
witty-ub Deployment Manager

Usage:
  bash deploy/docker/manage.sh              # interactive menu (default)
  bash deploy/docker/manage.sh <command>    # command-line mode
  bash deploy/docker/manage.sh uninstall --yes   # non-interactive uninstall

Commands:
  install           One-shot install: PG + witty-ub (Docker)
  install-pg        Install PostgreSQL only
  install-witty     Install witty-ub only (All-in-One)
  install-backend   Install witty-ub backend only (split, role=backend)
  install-frontend  Install witty-ub frontend only (split, role=frontend)
  uninstall         Uninstall everything (including data); --yes = non-interactive
  uninstall-witty   Uninstall witty-ub containers only (including split roles)
  uninstall-pg      Uninstall the PostgreSQL container only
  start             Start all
  stop              Stop all
  restart           Restart all containers
  status            Show status
  logs              Show logs
  psql              Open psql
  shell             Open container shell

Options:
  -y, --yes         Assume "yes" for confirmation prompts (required by uninstall
                    in CI / ssh sessions; otherwise the prompt defaults to No)
EOF
        ;;
    *)
        echo "Unknown command: $1"
        echo "Run 'bash deploy/docker/manage.sh --help' for help"
        exit 1
        ;;
    esac
else
    main
fi
