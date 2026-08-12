#!/bin/bash
# Copyright (c) Huawei Technologies Co., Ltd. 2023-2026. All rights reserved.
# witty-ub 部署管理器（交互式菜单）
#
# 直接运行: bash deploy/manage.sh

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
DEPLOY_DIR="$SCRIPT_DIR"
CONF_FILE="${DEPLOY_DIR}/../pg.conf"

PG_CONTAINER="${PG_CONTAINER_NAME:-postgres}"
WITTY_CONTAINER="${WITTY_CONTAINER_NAME:-witty-ub}"
PG_VOLUME="${PG_VOLUME:-pg15-data}"

# ---------- 本地开发模式配置（非 Docker 部署） ----------
BACKEND_SERVICE="${BACKEND_SERVICE:-witty-ub-backend.service}"
BACKEND_PORT="${BACKEND_PORT:-9772}"
FRONTEND_PORT="${FRONTEND_PORT:-5173}"
FRONTEND_DIR="${FRONTEND_DIR:-${DEPLOY_DIR}/../src/web}"
VITE_LOG_FILE="${VITE_LOG_FILE:-/tmp/witty-vite.log}"

# ---------- 加载配置 ----------
if [ -f "$CONF_FILE" ]; then
    source "$CONF_FILE"
fi

# ---------- 工具函数 ----------
log_info()  { echo "[INFO]  $*"; }
log_ok()    { echo "[OK]    $*"; }
log_warn()  { echo "[WARN]  $*"; }
log_error() { echo "[ERROR] $*"; }

sep() { echo "----------------------------------------"; }

check_docker() {
    if ! command -v docker &> /dev/null; then
        log_error "Docker not found. Please install Docker first."
        return 1
    fi
    if ! docker info &> /dev/null; then
        log_error "Docker daemon is not running."
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
    local used_by=$(docker ps -a --format '{{.Image}}' 2>/dev/null | grep -Fx "$image" || true)
    if [ -z "$used_by" ]; then
        log_info "删除镜像: $image"
        docker rmi "$image" 2>/dev/null || true
        log_ok "已删除镜像: $image"
    else
        log_warn "镜像 $image 仍被其他容器使用，跳过删除"
    fi
}

confirm() {
    local msg="$1"
    echo ""
    read -p "${msg} (y/N): " choice
    case "$choice" in
        [yY][eE][sS]|[yY]) return 0 ;;
        *) return 1 ;;
    esac
}

# ============================================================
# 安装
# ============================================================
do_install_all() {
    sep
    echo "一键安装：PostgreSQL + witty-ub（Docker 方式）"
    sep
    check_docker || return 1
    echo ""
    bash "${DEPLOY_DIR}/../deploy_pg.sh" --docker
    echo ""
    bash "${DEPLOY_DIR}/deploy_witty.sh"
    sep
    log_ok "一键安装完成！"
    show_status
}

do_install_pg() {
    sep
    echo "安装：PostgreSQL"
    sep
    echo ""
    echo "选择安装方式："
    echo "  1) Docker 容器（推荐）"
    echo "  2) RPM 包（需要 sudo）"
    echo ""
    read -p "请选择 [1-2，默认 1]: " choice
    choice="${choice:-1}"
    case "$choice" in
        1) check_docker || return 1; bash "${DEPLOY_DIR}/../deploy_pg.sh" --docker ;;
        2) sudo bash "${DEPLOY_DIR}/../deploy_pg.sh" --rpm ;;
        *) log_error "无效选项" ;;
    esac
}

do_install_witty() {
    sep
    echo "安装：witty-ub"
    sep
    check_docker || return 1

    # ---------- 交互式配置 ----------
    echo ""
    echo "┌─────────────────────────────────────────────────────┐"
    echo "│           witty-ub 部署参数配置                       │"
    echo "│           直接回车使用 [ ] 中的默认值                  │"
    echo "└─────────────────────────────────────────────────────┘"
    echo ""

    default_port="${WITTY_HOST_PORT:-32412}"
    read -p "  [1] 宿主机端口          [${default_port}]: " input_port
    WITTY_HOST_PORT="${input_port:-${default_port}}"

    default_mounts="${WITTY_EXTRA_MOUNTS:-}"
    echo ""
    echo "  [2] 额外目录挂载（容器访问宿主机日志/数据文件）"
    echo "      格式: 宿主机路径:容器内路径[:ro|rw]  多个用空格分隔"
    echo "      ro=只读(推荐)  rw=读写  留空=跳过"
    if [ -n "${default_mounts}" ]; then
        read -p "                         [${default_mounts}]: " input_mounts
    else
        read -p "                         [留空跳过]: " input_mounts
    fi
    WITTY_EXTRA_MOUNTS="${input_mounts:-${default_mounts}}"

    default_image="${WITTY_IMAGE:-}"
    echo ""
    if [ -n "${default_image}" ]; then
        read -p "  [3] 指定镜像            [${default_image}]: " input_image
    else
        read -p "  [3] 指定镜像            [留空自动选择]: " input_image
    fi
    WITTY_IMAGE="${input_image:-${default_image}}"

    # ---------- 配置汇总 ----------
    echo ""
    echo "┌─────────────────────────────────────────────────────┐"
    echo "│                    配置汇总                            │"
    echo "├─────────────────────────────────────────────────────┤"
    printf "│  %-22s %-30s │\n" "宿主机端口" "${WITTY_HOST_PORT}"
    printf "│  %-22s %-30s │\n" "镜像" "${WITTY_IMAGE:-自动选择}"
    if [ -n "${WITTY_EXTRA_MOUNTS}" ]; then
        first=1
        for m in ${WITTY_EXTRA_MOUNTS}; do
            if [ "$first" -eq 1 ]; then
                printf "│  %-22s %-30s │\n" "额外挂载" "${m}"
                first=0
            else
                printf "│  %-22s %-30s │\n" "" "${m}"
            fi
        done
    else
        printf "│  %-22s %-30s │\n" "额外挂载" "无"
    fi
    echo "└─────────────────────────────────────────────────────┘"
    echo ""

    # ---------- 检测 PostgreSQL ----------
    PG_DETECTED="unknown"
    PG_DETAIL=""
    if container_running "$PG_CONTAINER"; then
        PG_DETECTED="container"
        PG_DETAIL="Docker 容器（${PG_CONTAINER}）"
        log_ok "检测到 PostgreSQL: ${PG_DETAIL}"
    fi
    if [ "$PG_DETECTED" = "unknown" ] && command -v systemctl &> /dev/null; then
        PG_RPM=$(systemctl list-units --type=service --state=running 2>/dev/null | grep -o 'postgresql[^ ]*' | head -1 || true)
        if [ -n "$PG_RPM" ]; then
            PG_DETECTED="rpm"
            PG_PORT_DETECTED=$(ss -tlnp 2>/dev/null | grep 'postgres' | head -1 | awk '{print $4}' | rev | cut -d: -f1 | rev)
            PG_DETAIL="宿主机服务（${PG_RPM}，端口 ${PG_PORT_DETECTED:-${PG_PORT:-15432}}）"
            log_ok "检测到 PostgreSQL: ${PG_DETAIL}"
        fi
    fi

    if [ "$PG_DETECTED" = "unknown" ]; then
        log_warn "未检测到正在运行的 PostgreSQL"
        log_warn "witty-ub 启动后可能无法连接数据库"
        if ! confirm "是否继续？"; then
            return 0
        fi
    fi

    # ---------- 导出环境变量并调用部署脚本 ----------
    export WITTY_HOST_PORT WITTY_EXTRA_MOUNTS WITTY_IMAGE
    bash "${DEPLOY_DIR}/deploy_witty.sh"
}

# ============================================================
# 卸载
# ============================================================
do_uninstall_all() {
    sep
    echo "一键卸载：删除所有容器和数据"
    sep
    check_docker || return 1
    echo ""

    echo "请选择卸载范围："
    echo "  1) 只删容器 + 数据卷（推荐）"
    echo "  2) 删容器 + 数据卷 + 镜像"
    echo ""
    read -p "请选择 [1-2，默认 1]: " scope
    scope="${scope:-1}"

    echo ""
    log_warn "即将删除："
    echo "  - 容器: ${WITTY_CONTAINER}, ${PG_CONTAINER}"
    echo "  - 数据卷: witty-ub-data, witty-ub-logs, witty-ub-uploads, witty-ub-results, ${PG_VOLUME}"
    if [ "$scope" = "2" ]; then
        echo "  - 镜像: 以上两个容器使用的镜像"
    fi
    echo ""
    if ! confirm "确认全部删除？此操作不可恢复！"; then
        log_info "已取消"
        return 0
    fi

    # 先记录每个容器使用的镜像（删容器后就查不到了）
    declare -A images_to_remove
    for c in "$WITTY_CONTAINER" "$PG_CONTAINER"; do
        if container_exists "$c"; then
            images_to_remove[$c]=$(get_container_image "$c")
        fi
    done

    # 先停 witty 再停 pg（优雅关闭）
    for c in "$WITTY_CONTAINER" "$PG_CONTAINER"; do
        if container_exists "$c"; then
            log_info "删除容器: $c"
            docker rm -f "$c" &> /dev/null
            log_ok "已删除: $c"
        fi
    done

    # 删除所有数据卷
    for v in witty-ub-data witty-ub-logs witty-ub-uploads witty-ub-results "$PG_VOLUME"; do
        if volume_exists "$v"; then
            log_info "删除数据卷: $v"
            docker volume rm "$v" &> /dev/null
            log_ok "已删除: $v"
        fi
    done

    # 删除镜像（如果选了选项 2）
    if [ "$scope" = "2" ]; then
        for c in "$WITTY_CONTAINER" "$PG_CONTAINER"; do
            if [ -n "${images_to_remove[$c]}" ]; then
                remove_image_if_unused "${images_to_remove[$c]}"
            fi
        done
    fi

    sep
    log_ok "一键卸载完成"
}

do_uninstall_witty() {
    sep
    echo "卸载：witty-ub 容器"
    sep
    check_docker || return 1

    if ! container_exists "$WITTY_CONTAINER"; then
        log_warn "容器 ${WITTY_CONTAINER} 不存在"
        return 0
    fi

    echo ""
    echo "请选择卸载范围："
    echo "  1) 只删容器（保留数据卷）"
    echo "  2) 删容器 + 镜像（保留数据卷）"
    echo ""
    read -p "请选择 [1-2，默认 1]: " scope
    scope="${scope:-1}"

    # 记录使用的镜像
    local witty_image=""
    if [ "$scope" = "2" ]; then
        witty_image=$(get_container_image "$WITTY_CONTAINER")
    fi

    if confirm "确认删除 witty-ub 容器？"; then
        log_info "删除容器: ${WITTY_CONTAINER}"
        docker rm -f "$WITTY_CONTAINER"
        log_ok "witty-ub 容器已删除（数据卷保留）"
        if [ "$scope" = "2" ] && [ -n "$witty_image" ]; then
            remove_image_if_unused "$witty_image"
        fi
    fi
}

do_uninstall_pg() {
    sep
    echo "卸载：PostgreSQL 容器"
    sep
    check_docker || return 1

    if ! container_exists "$PG_CONTAINER"; then
        log_warn "容器 ${PG_CONTAINER} 不存在"
        return 0
    fi

    # 先记录使用的镜像
    local pg_image=$(get_container_image "$PG_CONTAINER")

    echo ""
    echo "请选择："
    echo "  1) 只删除容器（保留数据卷和镜像）"
    echo "  2) 删除容器 + 数据卷（保留镜像）"
    echo "  3) 删除容器 + 数据卷 + 镜像（全部清除）"
    echo ""
    read -p "请选择 [1-3，默认 1]: " choice
    choice="${choice:-1}"

    case "$choice" in
        1)
            log_info "删除容器: ${PG_CONTAINER}"
            docker rm -f "$PG_CONTAINER"
            log_ok "PostgreSQL 容器已删除（数据卷和镜像保留）"
            ;;
        2)
            if confirm "确认删除 PostgreSQL 容器和数据卷？"; then
                log_info "删除容器: ${PG_CONTAINER}"
                docker rm -f "$PG_CONTAINER" &> /dev/null
                if volume_exists "$PG_VOLUME"; then
                    log_info "删除数据卷: ${PG_VOLUME}"
                    docker volume rm "$PG_VOLUME"
                fi
                log_ok "PostgreSQL 容器和数据卷已删除（镜像保留）"
            fi
            ;;
        3)
            if confirm "确认删除 PostgreSQL 容器、数据卷和镜像？此操作不可恢复！"; then
                log_info "删除容器: ${PG_CONTAINER}"
                docker rm -f "$PG_CONTAINER" &> /dev/null
                if volume_exists "$PG_VOLUME"; then
                    log_info "删除数据卷: ${PG_VOLUME}"
                    docker volume rm "$PG_VOLUME"
                fi
                if [ -n "$pg_image" ]; then
                    remove_image_if_unused "$pg_image"
                fi
                log_ok "PostgreSQL 容器、数据卷和镜像已全部删除"
            fi
            ;;
        *)
            log_error "无效选项"
            ;;
    esac
}

# ============================================================
# 启停/重启/状态/日志
# ============================================================
do_start() {
    check_docker || return 1
    for c in "$PG_CONTAINER" "$WITTY_CONTAINER"; do
        if container_exists "$c"; then
            if container_running "$c"; then
                log_ok "$c 已在运行"
            else
                log_info "启动: $c"
                docker start "$c" &> /dev/null
                log_ok "已启动: $c"
            fi
        else
            log_warn "$c 容器不存在，请先安装"
        fi
    done
}

do_stop() {
    check_docker || return 1
    for c in "$WITTY_CONTAINER" "$PG_CONTAINER"; do
        if container_running "$c"; then
            log_info "停止: $c"
            docker stop "$c" &> /dev/null
            log_ok "已停止: $c"
        elif container_exists "$c"; then
            log_info "$c 已停止"
        fi
    done
}

do_restart() {
    check_docker || return 1
    for c in "$PG_CONTAINER" "$WITTY_CONTAINER"; do
        if container_exists "$c"; then
            log_info "重启: $c"
            docker restart "$c" &> /dev/null
            log_ok "已重启: $c"
        else
            log_warn "$c 容器不存在"
        fi
    done
}

port_listening() {
    local port="$1"
    if command -v ss &> /dev/null; then
        ss -tln 2>/dev/null | grep -q ":${port} "
    elif command -v netstat &> /dev/null; then
        netstat -tln 2>/dev/null | grep -q ":${port} "
    else
        return 1
    fi
}

find_pid_by_port() {
    local port="$1"
    local pid=""
    if command -v ss &> /dev/null; then
        pid=$(ss -tlnp 2>/dev/null | grep ":${port} " | sed -n 's/.*pid=\([0-9][0-9]*\).*/\1/p' | head -1 || true)
    fi
    if [ -z "$pid" ] && command -v pgrep &> /dev/null; then
        pid=$(pgrep -f "node ./node_modules/.bin/vite" | head -1 || true)
    fi
    echo "$pid"
}

is_local_mode() {
    if command -v systemctl &> /dev/null; then
        local backend_state
        backend_state=$(systemctl --user is-active "${BACKEND_SERVICE}" 2>/dev/null || true)
        if [ "$backend_state" = "active" ]; then
            return 0
        fi
    fi
    if port_listening "${FRONTEND_PORT}"; then
        return 0
    fi
    return 1
}

# 以裸进程方式重启后端（systemd user 单元不可用时的回退；与 deploy.sh 的
# nohup 启动方式一致）。按端口 9772 找进程 → 停止 → 重新拉起 → 健康检查。
restart_backend_bare() {
    local old_pid
    old_pid=$(find_pid_by_port "${BACKEND_PORT}")
    if [ -n "$old_pid" ]; then
        log_info "停止旧后端进程: PID ${old_pid}"
        kill "$old_pid" 2>/dev/null || true
        local i
        for i in 1 2 3; do
            if ! kill -0 "$old_pid" 2>/dev/null; then
                break
            fi
            sleep 1
        done
        if kill -0 "$old_pid" 2>/dev/null; then
            log_warn "旧后端进程 ${old_pid} 3 秒内未退出，强制结束"
            kill -9 "$old_pid" 2>/dev/null || true
        fi
    else
        log_info "未检测到占用 ${BACKEND_PORT} 端口的旧后端进程"
    fi
    sleep 1

    local latency_dir="${DEPLOY_DIR}/../src/plugins/latency"
    latency_dir=$(cd "$latency_dir" 2>/dev/null && pwd || echo "")
    if [ -z "$latency_dir" ] || [ ! -f "$latency_dir/.venv/bin/activate" ]; then
        log_error "后端目录或 venv 不存在: ${latency_dir}"
        return 1
    fi
    local project_dir
    project_dir=$(cd "${DEPLOY_DIR}/.." && pwd)
    local log_dir="${project_dir}/.deploy-logs"
    mkdir -p "$log_dir"

    (
        source "$latency_dir/.venv/bin/activate"
        export WITTY_DIR="${WITTY_DIR:-/var/witty-ub}"
        export CONFIG="${CONFIG:-$project_dir/config/diagnosis_config.toml}"
        export PYTHONPATH="$project_dir/src/plugins${PYTHONPATH:+:$PYTHONPATH}"
        cd "$latency_dir"
        nohup python3 -u access/fastapi_server.py > "${log_dir}/backend.log" 2>&1 &
        echo $! > "${log_dir}/backend.pid"
    )
    log_ok "后端裸进程已在后台启动 (日志: ${log_dir}/backend.log)"

    log_info "等待后端健康检查（最多 30 秒）…"
    local ok=0
    local j=0
    while [ "$j" -lt 30 ]; do
        j=$((j + 1))
        if curl -sf --max-time 3 "http://127.0.0.1:${BACKEND_PORT}/health_check" > /dev/null 2>&1; then
            ok=1
            log_ok "后端健康检查通过: http://127.0.0.1:${BACKEND_PORT}/health_check"
            break
        fi
        sleep 1
    done
    if [ "$ok" -ne 1 ]; then
        log_error "后端健康检查失败（30 秒内未通过），请查看 ${log_dir}/backend.log"
        return 1
    fi
}

 do_restart_local() {
     sep
     echo "本地开发模式重启（backend: systemd user unit 或裸进程；frontend: vite dev server）"
     sep

     log_info "重启后端服务: ${BACKEND_SERVICE}"
     if command -v systemctl &> /dev/null && systemctl --user restart "${BACKEND_SERVICE}" 2>/dev/null; then
         log_ok "已重启后端服务: ${BACKEND_SERVICE}"
     else
         # systemd user 单元不可用 → 按裸进程重启（与 deploy.sh 的 nohup 方式一致）
         log_warn "systemd 服务 ${BACKEND_SERVICE} 不可用，改用裸进程重启"
         restart_backend_bare
     fi

    log_info "重启前端 vite dev server（端口 ${FRONTEND_PORT}）"
    local old_pid
    old_pid=$(find_pid_by_port "${FRONTEND_PORT}")
    if [ -n "$old_pid" ]; then
        log_info "停止旧 vite 进程: PID ${old_pid}"
        kill "$old_pid" 2>/dev/null || true
        local i
        for i in 1 2 3; do
            if ! kill -0 "$old_pid" 2>/dev/null; then
                break
            fi
            sleep 1
        done
        if kill -0 "$old_pid" 2>/dev/null; then
            log_warn "旧 vite 进程 ${old_pid} 3 秒内未退出，强制结束"
            kill -9 "$old_pid" 2>/dev/null || true
        fi
        log_ok "已停止旧 vite 进程: PID ${old_pid}"
    else
        log_warn "未检测到占用 ${FRONTEND_PORT} 端口的旧 vite 进程"
    fi
    sleep 1

    local frontend_dir
    frontend_dir=$(cd "${FRONTEND_DIR}" 2>/dev/null && pwd || echo "")
    if [ -z "$frontend_dir" ]; then
        log_error "前端目录不存在: ${FRONTEND_DIR}"
        return 1
    fi
    if [ ! -x "${frontend_dir}/node_modules/.bin/vite" ]; then
        log_error "vite 未安装: ${frontend_dir}/node_modules/.bin/vite 不存在，请先在 ${frontend_dir} 执行 npm install"
        return 1
    fi

    log_info "启动 vite dev server（目录: ${frontend_dir}，日志: ${VITE_LOG_FILE}）"
    (
        cd "$frontend_dir" \
        && nohup node ./node_modules/.bin/vite --host 0.0.0.0 --port "${FRONTEND_PORT}" > "${VITE_LOG_FILE}" 2>&1 &
    )
    log_ok "vite dev server 已在后台启动"

    sep
    log_info "健康检查（最多等待 30 秒）…"
    local wait_secs=30
    local backend_ok=0
    local frontend_ok=0
    local j=0
    while [ "$j" -lt "$wait_secs" ]; do
        j=$((j + 1))
        if [ "$backend_ok" -eq 0 ] && curl -sf --max-time 3 "http://127.0.0.1:${BACKEND_PORT}/health_check" > /dev/null 2>&1; then
            backend_ok=1
            log_ok "后端健康检查通过: http://127.0.0.1:${BACKEND_PORT}/health_check"
        fi
        if [ "$frontend_ok" -eq 0 ] && port_listening "${FRONTEND_PORT}"; then
            frontend_ok=1
            log_ok "前端已就绪: 端口 ${FRONTEND_PORT} 开始监听"
        fi
        if [ "$backend_ok" -eq 1 ] && [ "$frontend_ok" -eq 1 ]; then
            break
        fi
        sleep 1
    done

    sep
    if [ "$backend_ok" -eq 1 ] && [ "$frontend_ok" -eq 1 ]; then
        log_ok "本地开发环境重启完成！"
        log_ok "  Web UI:   http://localhost:${FRONTEND_PORT}"
        log_ok "  API:      http://localhost:${BACKEND_PORT}/health_check"
        return 0
    fi
    if [ "$backend_ok" -eq 0 ]; then
        log_error "后端健康检查失败（${wait_secs} 秒内未通过）: http://127.0.0.1:${BACKEND_PORT}/health_check"
    fi
    if [ "$frontend_ok" -eq 0 ]; then
        log_error "前端启动失败（${wait_secs} 秒内端口 ${FRONTEND_PORT} 未监听），请查看日志: ${VITE_LOG_FILE}"
    fi
    return 1
}

do_restart_all() {
    if is_local_mode; then
        do_restart_local
    else
        log_info "未检测到本地开发模式（systemd/vite），使用 Docker 容器模式重启"
        do_restart
    fi
}

show_status() {
    check_docker || return 1
    sep
    printf "%-15s %-10s %-12s %s\n" "CONTAINER" "STATUS" "HEALTH" "PORTS"
    sep
    for c in "$PG_CONTAINER" "$WITTY_CONTAINER"; do
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
    echo "访问地址："
    echo "  Web UI:   http://localhost:${actual_port}"
    echo "  API:      http://localhost:${actual_port}/health_check"
    echo "  API 文档: http://localhost:${actual_port}/docs"
}

do_logs() {
    check_docker || return 1
    echo ""
    echo "选择查看日志："
    echo "  1) PostgreSQL"
    echo "  2) witty-ub"
    echo ""
    read -p "请选择 [1-2，默认 2]: " choice
    choice="${choice:-2}"
    case "$choice" in
        1) container="$PG_CONTAINER" ;;
        2) container="$WITTY_CONTAINER" ;;
        *) log_error "无效选项"; return 1 ;;
    esac

    if container_exists "$container"; then
        log_info "查看 $container 日志（Ctrl+C 退出）"
        docker logs -f "$container"
    else
        log_error "容器 $container 不存在"
    fi
}

do_psql() {
    check_docker || return 1
    if ! container_running "$PG_CONTAINER"; then
        log_error "PostgreSQL 容器未运行"
        return 1
    fi
    log_info "进入 psql（输入 \q 退出）"
    docker exec -it "$PG_CONTAINER" psql -U "${PG_USER:-witty-ub}" -d "${PG_DATABASE:-witty-ub}"
}

do_shell() {
    check_docker || return 1
    echo ""
    echo "选择进入哪个容器："
    echo "  1) PostgreSQL"
    echo "  2) witty-ub"
    echo ""
    read -p "请选择 [1-2，默认 2]: " choice
    choice="${choice:-2}"
    case "$choice" in
        1) container="$PG_CONTAINER" ;;
        2) container="$WITTY_CONTAINER" ;;
        *) log_error "无效选项"; return 1 ;;
    esac

    if container_running "$container"; then
        log_info "进入 $container（输入 exit 退出）"
        docker exec -it "$container" bash
    else
        log_error "容器 $container 未运行"
    fi
}

# ============================================================
# 主菜单
# ============================================================
show_menu() {
    echo ""
    echo "========================================"
    echo "  witty-ub 部署管理器"
    echo "========================================"
    echo ""
    echo "  📦  安装"
    echo "    1) 一键安装：PG + witty-ub（Docker）"
    echo "    2) 仅安装 PostgreSQL"
    echo "    3) 仅安装 witty-ub"
    echo ""
    echo "  🗑️  卸载"
    echo "    4) 一键卸载：全部删除（含数据）"
    echo "    5) 仅卸载 witty-ub 容器"
    echo "    6) 仅卸载 PostgreSQL 容器"
    echo ""
    echo "  🔧  管理"
    echo "    7) 启动全部"
    echo "    8) 停止全部"
    echo "    9) 重启全部（自动检测: 本地/Docker）"
    echo "   10) 查看状态"
    echo "   11) 查看日志"
    echo ""
    echo "  💻  工具"
    echo "   12) 进入 psql（PG）"
    echo "   13) 进入容器 Shell"
    echo ""
    echo "    0) 退出"
    echo ""
    echo "========================================"
}

main() {
    while true; do
        show_menu
        read -p "请选择操作 [0-13]: " choice
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
            9) do_restart_all ;;
            10) show_status ;;
            11) do_logs ;;
            12) do_psql ;;
            13) do_shell ;;
            0)
                echo "再见！"
                exit 0
                ;;
            *)
                log_error "无效选项，请重新选择"
                ;;
        esac
        echo ""
        read -p "按回车继续..." _
    done
}

# 如果直接带参数运行，走命令行模式
if [ $# -gt 0 ]; then
    case "$1" in
        install|install-all)    do_install_all ;;
        install-pg)             do_install_pg ;;
        install-witty)          do_install_witty ;;
        uninstall|uninstall-all) do_uninstall_all ;;
        uninstall-witty)        do_uninstall_witty ;;
        uninstall-pg)           do_uninstall_pg ;;
        start)                  do_start ;;
        stop)                   do_stop ;;
        restart)                do_restart_all ;;
        status)                 show_status ;;
        logs)                   do_logs ;;
        psql)                   do_psql ;;
        shell)                  do_shell ;;
        -h|--help|help)
            cat <<EOF
witty-ub 部署管理器

用法:
  bash deploy/manage.sh              # 交互式菜单（默认）
  bash deploy/manage.sh <command>    # 命令行模式

命令:
  install          一键安装 PG + witty-ub（Docker）
  install-pg       仅安装 PG
  install-witty    仅安装 witty-ub
  uninstall        一键卸载全部（含数据）
  uninstall-witty  仅卸载 witty-ub 容器
  uninstall-pg     仅卸载 PG 容器
  start            启动全部
  stop             停止全部
  restart          重启全部（自动检测: 本地 systemd+vite / Docker）
  status           查看状态
  logs             查看日志
  psql             进入 psql
  shell            进入容器 Shell
EOF
            ;;
        *)
            echo "未知命令: $1"
            echo "使用 bash deploy/manage.sh --help 查看帮助"
            exit 1
            ;;
    esac
else
    main
fi
