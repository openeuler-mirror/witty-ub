#!/bin/bash
# Copyright (c) Huawei Technologies Co., Ltd. 2023-2026. All rights reserved.
# PostgreSQL 一键部署脚本
# 用法:
#   bash deploy/deploy_pg.sh            # 默认 Docker 容器部署
#   bash deploy/deploy_pg.sh --docker   # Docker 容器部署
#   bash deploy/deploy_pg.sh --rpm     # RPM 包部署（openEuler/CentOS/RHEL）
#   bash deploy/deploy_pg.sh --apt     # APT 包部署（Ubuntu/Debian）

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
DEPLOY_DIR="$SCRIPT_DIR"
CONF_FILE="${DEPLOY_DIR}/deploy.conf"
[ -f "$CONF_FILE" ] || CONF_FILE="${DEPLOY_DIR}/pg.conf" # 兼容旧名

# ---------- 参数解析 ----------
DEPLOY_MODE="docker" # 默认 docker
# 保留命令行环境变量覆盖；source deploy.conf 会改写同名变量。
PG_PORT_OVERRIDE="${PG_PORT:-}"
PG_PORT_RPM_OVERRIDE="${PG_PORT_RPM:-}"

usage() {
    cat <<EOF
PostgreSQL one-shot deployment script

Usage:
  $0 [OPTIONS]

Options:
  --docker    Docker container deployment (default)
  --rpm       RPM package deployment (openEuler / CentOS / RHEL)
  --apt       APT package deployment (Ubuntu / Debian)
  -h, --help  Show this help

Config file: ${CONF_FILE}
EOF
}

while [ $# -gt 0 ]; do
    case "$1" in
    --docker)
        DEPLOY_MODE="docker"
        shift
        ;;
    --rpm)
        DEPLOY_MODE="rpm"
        shift
        ;;
    --apt)
        DEPLOY_MODE="apt"
        shift
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

# ---------- 加载配置 ----------
if [ -f "$CONF_FILE" ]; then
    echo "[INFO] Loading config from ${CONF_FILE}"
    # shellcheck disable=SC1090
    source "$CONF_FILE"
else
    echo "[ERROR] Config file not found: ${CONF_FILE}"
    exit 1
fi

# RPM/APT 使用本机 PostgreSQL 端口；PG_PORT 仅是 Docker 容器的宿主机映射端口。
if [ "$DEPLOY_MODE" = "rpm" ] || [ "$DEPLOY_MODE" = "apt" ]; then
    PG_PORT="${PG_PORT_RPM_OVERRIDE:-${PG_PORT_RPM:-5432}}"
elif [ -n "$PG_PORT_OVERRIDE" ]; then
    PG_PORT="$PG_PORT_OVERRIDE"
fi

# PG 密码独立密钥文件（Docker 模式 0440，其余 0400）：ensure_pg_password 生成/写入，不回写 deploy.conf。
# Docker 部署 → /etc/witty-ub/pg.passwd（系统级稳定路径，不依赖仓库目录）；
# 源码 host 部署（--rpm/--apt）→ deploy/pg.passwd（仓库目录内，开发/源码部署场景）。
# 环境变量 PG_SECRET_FILE 可覆盖（测试/自定义路径）。
if [ "$DEPLOY_MODE" = "docker" ]; then
    PG_SECRET_FILE="${PG_SECRET_FILE:-/etc/witty-ub/pg.passwd}"
else
    PG_SECRET_FILE="${PG_SECRET_FILE:-${DEPLOY_DIR}/pg.passwd}"
fi

# ---------- 公共工具函数 ----------
log_info() { echo "[INFO]  $*"; }
log_ok() { echo "[OK]    $*"; }
log_warn() { echo "[WARN]  $*"; }
log_error() { echo "[ERROR] $*"; }

ensure_pg_password() {
    # 密码存放于独立密钥文件 PG_SECRET_FILE（Docker 模式 0440，其余 0400），
    # 不回写 deploy.conf —— 配置文件保持 <CHANGE_ME> 占位，杜绝污染源码/RPM 安装文件。
    # Docker 模式: /etc/witty-ub/pg.passwd；源码 host 模式: deploy/pg.passwd。
    #
    # 优先级: 已存在的密钥文件 > deploy.conf 中已设置的口令(一次性迁移) > 交互输入/自动生成。
    if [ -f "$PG_SECRET_FILE" ]; then
        local cached
        cached="$(_read_pg_secret)"
        if [ -n "$cached" ]; then
            PG_PASSWORD="$cached"
            _secure_pg_secret_permissions
            _assert_pg_secret_mode || return 1
            log_info "PostgreSQL password loaded from ${PG_SECRET_FILE} (mode $(_pg_secret_mode))"
            return 0
        fi
    fi

    # 迁移路径: 旧部署已把口令写进 deploy.conf，一次性搬到密钥文件，之后不再回写配置。
    if [ -n "${PG_PASSWORD:-}" ] && [ "$PG_PASSWORD" != "<CHANGE_ME>" ] && [ "$PG_PASSWORD" != "witty-ub" ]; then
        log_info "Migrating the legacy password from deploy.conf to ${PG_SECRET_FILE}"
        _write_pg_secret "$PG_PASSWORD" || return 1
        log_info "PostgreSQL password migrated to the secret file"
        return 0
    fi

    local input_password=""
    local confirm_password=""
    if [ -t 0 ]; then
        read -r -s -p "Enter PostgreSQL password (>=6 alphanumeric chars, Enter to auto-generate): " input_password
        echo ""
        if [ -n "$input_password" ]; then
            if [[ ! "$input_password" =~ ^[A-Za-z0-9]{6,}$ ]]; then
                log_error "PostgreSQL password must be at least 6 alphanumeric characters"
                return 1
            fi
            read -r -s -p "Confirm PostgreSQL password: " confirm_password
            echo ""
            if [ "$input_password" != "$confirm_password" ]; then
                log_error "The two passwords do not match"
                return 1
            fi
        fi
    fi
    if [ -n "$input_password" ]; then
        PG_PASSWORD="$input_password"
        log_info "Using the password entered by the user"
    else
        PG_PASSWORD="$(head -c 24 /dev/urandom | base64 | tr -d '/+=' | head -c 24)"
        log_warn "Generated a random PostgreSQL password"
    fi
    _write_pg_secret "$PG_PASSWORD" || return 1
    log_info "PostgreSQL password saved to ${PG_SECRET_FILE}"
}

# 密钥文件目标权限：Docker 模式 0440（容器内 postgres 以 uid26/gid0 运行，需组可读且不需写），
# 其余模式 0400（仅属主可读）。
_pg_secret_mode() {
    if [ "$DEPLOY_MODE" = "docker" ]; then
        echo "0440"
    else
        echo "0400"
    fi
}

# 读取密钥内容；普通用户读不到（文件属主 root、目录不可遍历）时回退 sudo -n。
_read_pg_secret() {
    local content
    content="$(cat "$PG_SECRET_FILE" 2>/dev/null || sudo -n cat "$PG_SECRET_FILE" 2>/dev/null)"
    printf '%s' "$content" | tr -d '\r\n'
}

# 源码部署通常由普通用户通过 sudo 初始化 PG。密钥需要归还给该部署用户，
# 否则 systemd --user / nohup 后端无法读取；Docker/RPM 系统密钥仍归 root。
# 注意：密钥由 sudo 写入时属主为 root，普通用户 chmod 会失败，必须回退 sudo -n，
# 否则 Docker 模式下密钥会停留在 0600 导致 PG 容器读不到并崩溃循环。
_secure_pg_secret_permissions() {
    local mode
    mode="$(_pg_secret_mode)"
    chmod "$mode" "$PG_SECRET_FILE" 2>/dev/null ||
        sudo -n chmod "$mode" "$PG_SECRET_FILE" 2>/dev/null ||
        true
    if [ "$DEPLOY_MODE" != "docker" ] && [ -n "${SUDO_UID:-}" ] && [ -n "${SUDO_GID:-}" ]; then
        chown "${SUDO_UID}:${SUDO_GID}" "$PG_SECRET_FILE" 2>/dev/null || true
    fi
}

# 权限收紧后必须校验：不符合预期时 PG 容器读不到密钥（Permission denied → 崩溃循环）。
_assert_pg_secret_mode() {
    local expected actual
    expected="$(_pg_secret_mode)"
    actual="$(stat -c '%a' "$PG_SECRET_FILE" 2>/dev/null ||
        stat -f '%Lp' "$PG_SECRET_FILE" 2>/dev/null ||
        sudo -n stat -c '%a' "$PG_SECRET_FILE" 2>/dev/null || true)"
    actual="$(printf '%s' "$actual" | tr -d '\r\n')"
    # stat 输出不带前导 0（440 / 400），按八进制数值比较
    if [ -z "$actual" ] || [ "$((8#$actual))" -ne "$((8#$expected))" ]; then
        log_error "Unexpected secret file mode: ${PG_SECRET_FILE} (expected ${expected}, actual ${actual:-unknown})"
        log_error "Fix it manually and retry: sudo chmod ${expected} ${PG_SECRET_FILE}"
        return 1
    fi
    return 0
}

# 将口令写入密钥文件（不修改任何配置文件）。
# 先以 umask 077 落盘（不会出现短暂的世界可读窗口），再收紧到目标权限并校验。
_write_pg_secret() {
    local password="$1"
    local secret_dir
    secret_dir="$(dirname "$PG_SECRET_FILE")"
    if ! mkdir -p "$secret_dir" 2>/dev/null; then
        sudo mkdir -p "$secret_dir"
    fi
    # 0400/0440 的既有密钥需先恢复属主写位才能原地重写
    [ -w "$PG_SECRET_FILE" ] || chmod u+w "$PG_SECRET_FILE" 2>/dev/null || true
    if ! (umask 077 && printf '%s' "$password" >"$PG_SECRET_FILE") 2>/dev/null; then
        # 普通用户运行时密钥目录可能需要 root 权限（如 /etc/witty-ub）
        printf '%s' "$password" | sudo sh -c "umask 077 && cat > '$PG_SECRET_FILE'"
    fi
    _secure_pg_secret_permissions
    _assert_pg_secret_mode || return 1
    log_info "Secret file written: ${PG_SECRET_FILE} (mode $(_pg_secret_mode))"
}

check_root() {
    if [ "$(id -u)" -ne 0 ]; then
        log_error "This script must be run as root"
        exit 1
    fi
}

# 交互确认：非 TTY（如被 deploy.sh 自动调用）时自动继续，避免卡住自动部署。
confirm() {
    local prompt="$1"
    if [ ! -t 0 ]; then
        log_warn "${prompt} (non-interactive environment, continuing)"
        return 0
    fi
    local ans=""
    printf "%s [y/N] " "$prompt"
    read -r ans
    case "$ans" in
    y | Y | yes | YES) return 0 ;;
    *) return 1 ;;
    esac
}

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

# ============================================================
# Docker 容器部署
# ============================================================
deploy_docker() {
    echo "========================================"
    echo "PostgreSQL Docker Deployment"
    echo "========================================"

    check_docker
    ensure_pg_password

    # SCL 镜像不支持 *_PASSWORD_FILE，因此用 bash 入口从只读密钥挂载读取
    # 密码后再 exec 原入口。保留既有镜像和数据目录，避免升级时迁移数据卷。
    # 每个条目: 镜像地址|用户环境变量|密码环境变量|库名环境变量|容器内数据目录
    declare -a PG_IMAGE_CANDIDATES=(
        "quay.io/sclorg/postgresql-15-c9s:latest|POSTGRESQL_USER|POSTGRESQL_PASSWORD|POSTGRESQL_DATABASE|/var/lib/pgsql/data"
    )

    parse_image_entry() {
        echo "$1" | cut -d'|' -f"$2"
    }

    # Step 1: 检查/拉取镜像（带回退）
    echo ""
    echo "[Step 1/6] Checking and pulling PostgreSQL image ..."

    SELECTED_IMAGE=""
    SELECTED_ENV_USER=""
    SELECTED_ENV_DB=""
    SELECTED_DATA_DIR=""

    log_info "Checking local images for PostgreSQL 15 ..."
    for entry in "${PG_IMAGE_CANDIDATES[@]}"; do
        image=$(parse_image_entry "$entry" 1)
        if docker image inspect "$image" &>/dev/null; then
            log_ok "Found local image: ${image}"
            SELECTED_IMAGE="$image"
            SELECTED_ENV_USER=$(parse_image_entry "$entry" 2)
            SELECTED_ENV_DB=$(parse_image_entry "$entry" 4)
            SELECTED_DATA_DIR=$(parse_image_entry "$entry" 5)
            break
        fi
    done

    if [ -z "$SELECTED_IMAGE" ]; then
        log_info "No usable local image. Trying to pull ..."
        for entry in "${PG_IMAGE_CANDIDATES[@]}"; do
            image=$(parse_image_entry "$entry" 1)
            log_info "  Trying to pull ${image} ..."
            if docker pull "$image" &>/dev/null; then
                log_ok "Pulled ${image} successfully"
                SELECTED_IMAGE="$image"
                SELECTED_ENV_USER=$(parse_image_entry "$entry" 2)
                SELECTED_ENV_DB=$(parse_image_entry "$entry" 4)
                SELECTED_DATA_DIR=$(parse_image_entry "$entry" 5)
                break
            else
                log_warn "  Failed to pull ${image}, trying next ..."
            fi
        done
    fi

    if [ -z "$SELECTED_IMAGE" ]; then
        log_error "No PostgreSQL image available. Tried:"
        for entry in "${PG_IMAGE_CANDIDATES[@]}"; do
            log_error "  - $(parse_image_entry "$entry" 1)"
        done
        exit 1
    fi

    PG_CONTAINER_DATA_DIR="${SELECTED_DATA_DIR}"
    log_info "Using image: ${SELECTED_IMAGE}"
    log_info "Data directory in container: ${PG_CONTAINER_DATA_DIR}"

    # Step 2: Docker 网络
    echo ""
    echo "[Step 2/6] Preparing Docker network ..."
    if docker network ls --format '{{.Name}}' | grep -qx "${PG_NETWORK}"; then
        log_ok "Network ${PG_NETWORK} already exists"
    else
        log_info "Creating network ${PG_NETWORK} ..."
        docker network create "${PG_NETWORK}"
        log_ok "Network ${PG_NETWORK} created"
    fi

    # Step 3: 数据卷
    echo ""
    echo "[Step 3/6] Preparing Docker volume ..."
    if docker volume ls --format '{{.Name}}' | grep -qx "${PG_VOLUME}"; then
        log_ok "Volume ${PG_VOLUME} already exists"
    else
        log_info "Creating volume ${PG_VOLUME} ..."
        docker volume create "${PG_VOLUME}"
        log_ok "Volume ${PG_VOLUME} created"
    fi

    # Step 4: 清理同名旧容器
    echo ""
    echo "[Step 4/6] Checking existing container ..."
    if docker ps -a --format '{{.Names}}' | grep -qx "${PG_CONTAINER_NAME}"; then
        log_warn "Container ${PG_CONTAINER_NAME} already exists"
        if docker ps --format '{{.Names}}' | grep -qx "${PG_CONTAINER_NAME}"; then
            log_info "Stopping running container ..."
            docker stop "${PG_CONTAINER_NAME}"
        fi
        log_info "Removing existing container ..."
        docker rm "${PG_CONTAINER_NAME}"
        log_ok "Existing container removed"
    fi

    # Step 5: 启动容器
    echo ""
    echo "[Step 5/6] Starting PostgreSQL container ..."
    docker run -d \
        --name "${PG_CONTAINER_NAME}" \
        --restart unless-stopped \
        -p "${PG_PORT}:5432" \
        -v "${PG_VOLUME}:${PG_CONTAINER_DATA_DIR}" \
        -v "${PG_SECRET_FILE}:/run/secrets/pg_password:ro" \
        -e "${SELECTED_ENV_USER}=${PG_USER}" \
        -e "${SELECTED_ENV_DB}=${PG_DATABASE}" \
        --health-cmd="pg_isready -U ${PG_USER} -d ${PG_DATABASE}" \
        --health-interval="${PG_HEALTH_INTERVAL}" \
        --health-timeout="${PG_HEALTH_TIMEOUT}" \
        --health-retries="${PG_HEALTH_RETRIES}" \
        --health-start-period="${PG_HEALTH_START_PERIOD}" \
        --network "${PG_NETWORK}" \
        --entrypoint /bin/bash \
        "${SELECTED_IMAGE}" \
        -c 'export POSTGRESQL_PASSWORD="$(tr -d '\''\r\n'\'' </run/secrets/pg_password)"; [ -n "$POSTGRESQL_PASSWORD" ] || exit 1; exec /usr/bin/container-entrypoint /usr/bin/run-postgresql'
    log_ok "Container ${PG_CONTAINER_NAME} started"

    # Step 6: 等待健康 + 验证
    echo ""
    echo "[Step 6/6] Waiting for PostgreSQL to become healthy ..."
    MAX_WAIT=120
    WAITED=0
    while [ "$WAITED" -lt "$MAX_WAIT" ]; do
        HEALTH=$(docker inspect --format='{{.State.Health.Status}}' "${PG_CONTAINER_NAME}" 2>/dev/null || echo "starting")
        if [ "$HEALTH" = "healthy" ]; then
            break
        fi
        sleep 2
        WAITED=$((WAITED + 2))
        printf "  waiting... %3ds (health: %s)\r" "$WAITED" "$HEALTH"
    done
    echo ""

    if [ "$HEALTH" = "healthy" ]; then
        log_ok "PostgreSQL is healthy!"
    else
        log_error "PostgreSQL was not ready within ${MAX_WAIT}s (health: ${HEALTH})"
        log_error "Container logs (last 20 lines):"
        docker logs --tail 20 "${PG_CONTAINER_NAME}" 2>&1 | sed 's/^/    /' || true
        log_error "Common cause: insufficient secret file permissions (expected $(_pg_secret_mode) root:root)"
        log_error "  Check: sudo stat -c '%a %U:%G' ${PG_SECRET_FILE}"
        exit 1
    fi

    # 验证连接
    echo ""
    echo "========================================"
    echo "Verifying connection ..."
    PG_VERIFY_OK=0
    for _ in {1..15}; do
        # 宿主机有 psql 时优先做端到端验证（宿主机 → 映射端口 → 容器）
        if command -v psql &>/dev/null &&
            PGPASSWORD="${PG_PASSWORD}" psql -h "${PG_HOST}" -p "${PG_PORT}" \
                -U "${PG_USER}" -d "${PG_DATABASE}" -tAc "select 1" &>/dev/null; then
            PG_VERIFY_OK=1
            log_ok "Connection verified successfully! (host psql: ${PG_HOST}:${PG_PORT})"
            break
        fi
        # 宿主机没有客户端时退回容器内 psql（真实认证验证，而不是只看端口）
        if docker exec -e PGPASSWORD="${PG_PASSWORD}" "${PG_CONTAINER_NAME}" \
            psql -h 127.0.0.1 -U "${PG_USER}" -d "${PG_DATABASE}" -tAc "select 1" &>/dev/null; then
            PG_VERIFY_OK=1
            if ! command -v psql &>/dev/null; then
                log_warn "psql not found on the host; verified authentication with the container psql instead"
            fi
            log_ok "Connection verified successfully! (container psql)"
            break
        fi
        sleep 2
    done
    if [ "$PG_VERIFY_OK" -ne 1 ]; then
        log_error "PostgreSQL connection verification failed (${PG_HOST}:${PG_PORT}, db=${PG_DATABASE}, user=${PG_USER})"
        log_error "Container logs (last 20 lines):"
        docker logs --tail 20 "${PG_CONTAINER_NAME}" 2>&1 | sed 's/^/    /' || true
        exit 1
    fi

    echo ""
    echo "========================================"
    echo "PostgreSQL Docker Deployment Completed!"
    echo "========================================"
    echo "  Container:  ${PG_CONTAINER_NAME}"
    echo "  Image:      ${SELECTED_IMAGE}"
    echo "  Host:       ${PG_HOST} (host) / ${PG_CONTAINER_NAME} (container)"
    echo "  Port:       ${PG_PORT} (host) / 5432 (container)"
    echo "  Database:   ${PG_DATABASE}"
    echo "  User:       ${PG_USER}"
    echo "  Network:    ${PG_NETWORK}"
    echo "  Volume:     ${PG_VOLUME}"
    echo ""
    echo "Useful commands:"
    echo "  docker ps                                    # list running containers"
    echo "  docker logs ${PG_CONTAINER_NAME} -f         # view container logs"
    echo "  docker stop ${PG_CONTAINER_NAME}            # stop container"
    echo "  docker start ${PG_CONTAINER_NAME}           # start a stopped container"
    echo "  docker restart ${PG_CONTAINER_NAME}         # restart container"
    echo "  docker exec -it ${PG_CONTAINER_NAME} psql   # open psql"
    echo "========================================"
}

# ============================================================
# RPM 包部署
# ============================================================
deploy_rpm() {
    echo "========================================"
    echo "PostgreSQL 15 RPM Deployment"
    echo "========================================"

    check_root
    ensure_pg_password

    # Step 1: 安装 PostgreSQL
    echo ""
    echo "[Step 1/7] Installing PostgreSQL 15 ..."

    PG_PKG_CANDIDATES=("postgresql15-server" "postgresql-server")
    INSTALLED_PKG=""
    for pkg in "${PG_PKG_CANDIDATES[@]}"; do
        if rpm -q "$pkg" &>/dev/null; then
            log_ok "PostgreSQL already installed: $pkg"
            INSTALLED_PKG="$pkg"
            break
        fi
    done

    if [ -z "$INSTALLED_PKG" ]; then
        INSTALL_SUCCESS=0
        for pkg in "${PG_PKG_CANDIDATES[@]}"; do
            log_info "Trying to install $pkg ..."
            if yum install -y --allowerasing "$pkg" &>/dev/null; then
                log_ok "Installed $pkg successfully"
                INSTALLED_PKG="$pkg"
                INSTALL_SUCCESS=1
                break
            fi
        done
        if [ "$INSTALL_SUCCESS" -ne 1 ]; then
            log_error "Failed to install PostgreSQL. Please install manually:"
            log_error "  yum install -y postgresql15-server"
            exit 1
        fi
    fi

    if ! command -v psql &>/dev/null; then
        log_info "Installing PostgreSQL client ..."
        yum install -y --allowerasing postgresql &>/dev/null || true
    fi
    log_ok "PostgreSQL client: $(psql --version 2>&1 | head -1)"

    # Step 2: 数据目录和服务名
    echo ""
    echo "[Step 2/7] Preparing data directory ..."
    if [ "$INSTALLED_PKG" = "postgresql15-server" ]; then
        PG_DATA_DIR="${PG_DATA_DIR:-/var/lib/pgsql/15/data}"
        PG_SERVICE_NAME="${PG_SERVICE_NAME:-postgresql-15}"
    else
        PG_DATA_DIR="${PG_DATA_DIR:-/var/lib/pgsql/data}"
        PG_SERVICE_NAME="${PG_SERVICE_NAME:-postgresql}"
    fi
    log_info "Data directory: ${PG_DATA_DIR}"
    log_info "Service name: ${PG_SERVICE_NAME}"

    # Step 3: 初始化数据库
    echo ""
    echo "[Step 3/7] Initializing database ..."
    if [ ! -f "${PG_DATA_DIR}/PG_VERSION" ]; then
        /usr/pgsql-15/bin/postgresql-15-setup initdb 2>/dev/null ||
            postgresql-setup --initdb 2>/dev/null ||
            su - postgres -c "/usr/pgsql-15/bin/initdb -D ${PG_DATA_DIR}" 2>/dev/null ||
            su - postgres -c "initdb -D ${PG_DATA_DIR}"
        log_ok "Database initialized"
    else
        log_ok "Database already initialized, skipping"
    fi

    # Step 4: 配置 postgresql.conf
    echo ""
    echo "[Step 4/7] Configuring postgresql.conf ..."
    PG_CONF="${PG_DATA_DIR}/postgresql.conf"
    if [ -f "$PG_CONF" ] && [ ! -f "${PG_CONF}.bak" ]; then
        cp "$PG_CONF" "${PG_CONF}.bak"
    fi

    if grep -q "^#listen_addresses" "$PG_CONF" 2>/dev/null; then
        sed -i "s/^#listen_addresses.*/listen_addresses = '*'/" "$PG_CONF"
    elif grep -q "^listen_addresses" "$PG_CONF" 2>/dev/null; then
        sed -i "s/^listen_addresses.*/listen_addresses = '*'/" "$PG_CONF"
    else
        echo "listen_addresses = '*'" >>"$PG_CONF"
    fi

    if grep -q "^#port" "$PG_CONF" 2>/dev/null; then
        sed -i "s/^#port.*/port = ${PG_PORT}/" "$PG_CONF"
    elif grep -q "^port" "$PG_CONF" 2>/dev/null; then
        sed -i "s/^port.*/port = ${PG_PORT}/" "$PG_CONF"
    else
        echo "port = ${PG_PORT}" >>"$PG_CONF"
    fi
    log_ok "postgresql.conf configured (listen=*, port=${PG_PORT})"

    # Step 5: 配置 pg_hba.conf
    echo ""
    echo "[Step 5/7] Configuring pg_hba.conf ..."
    PG_HBA="${PG_DATA_DIR}/pg_hba.conf"
    if [ -f "$PG_HBA" ] && [ ! -f "${PG_HBA}.bak" ]; then
        cp "$PG_HBA" "${PG_HBA}.bak"
    fi

    # postgres 超级用户本地免密
    if grep -q "^local\s\+all\s\+postgres\s\+peer" "$PG_HBA" 2>/dev/null; then
        :
    else
        sed -i '/^local\s\+all\s\+all/i local   all             postgres                                peer' "$PG_HBA" 2>/dev/null ||
            echo "local   all             postgres                                peer" >/tmp/pg_hba_insert.tmp
    fi

    # 本地用户 md5 认证
    sed -i 's/^local\s\+all\s\+all\s\+peer/local   all             all                                     md5/' "$PG_HBA"
    sed -i 's/^local\s\+all\s\+all\s\+ident/local   all             all                                     md5/' "$PG_HBA"
    sed -i 's/^host\s\+all\s\+all\s\+127\.0\.0\.1\/32\s\+ident/host    all             all             127.0.0.1\/32            md5/' "$PG_HBA"
    sed -i 's/^host\s\+all\s\+all\s\+::1\/128\s\+ident/host    all             all             ::1\/128                 md5/' "$PG_HBA"

    if ! grep -q "host    all             all             0.0.0.0/0" "$PG_HBA" 2>/dev/null; then
        echo "host    all             all             0.0.0.0/0               md5" >>"$PG_HBA"
    fi
    if ! grep -q "host    all             all             ::/0" "$PG_HBA" 2>/dev/null; then
        echo "host    all             all             ::/0                    md5" >>"$PG_HBA"
    fi
    log_ok "pg_hba.conf configured (md5 auth + remote access)"

    # Step 6: 启动服务
    echo ""
    echo "[Step 6/7] Starting PostgreSQL service ..."
    systemctl enable "$PG_SERVICE_NAME" &>/dev/null || true

    if command -v getenforce &>/dev/null && [ "$(getenforce 2>/dev/null)" = "Enforcing" ]; then
        if command -v semanage &>/dev/null; then
            log_info "Setting SELinux port label for port ${PG_PORT} ..."
            semanage port -a -t postgresql_port_t -p tcp "${PG_PORT}" 2>/dev/null ||
                semanage port -m -t postgresql_port_t -p tcp "${PG_PORT}" 2>/dev/null || true
        else
            log_warn "SELinux is Enforcing but semanage not found. Install it first:"
            log_warn "  yum install -y policycoreutils-python-utils"
        fi
    fi

    # listen_addresses/port/pg_hba 的变更需要重启服务才会生效；仅 start 在服务
    # 已运行时是 no-op，会导致后面的连接校验失败（且现场很难看出原因）。
    systemctl restart "$PG_SERVICE_NAME"

    log_info "Waiting for PostgreSQL to become ready ..."
    READY=0
    for _ in {1..30}; do
        if command -v pg_isready &>/dev/null; then
            if pg_isready -p "${PG_PORT}" &>/dev/null; then
                READY=1
                break
            fi
        fi
        if su - postgres -c "psql -h 127.0.0.1 -p ${PG_PORT} -U postgres -c 'SELECT 1'" &>/dev/null; then
            READY=1
            break
        fi
        sleep 1
    done

    if [ "$READY" -eq 1 ] && systemctl is-active --quiet "$PG_SERVICE_NAME"; then
        log_ok "PostgreSQL service is running"
    else
        log_error "PostgreSQL service failed to start"
        log_error "Check: systemctl status ${PG_SERVICE_NAME}"
        exit 1
    fi

    # Step 7: 创建用户和数据库
    echo ""
    echo "[Step 7/7] Creating user and database ..."
    psql_cmd() {
        su - postgres -c "psql -p ${PG_PORT} $*"
    }

    USER_EXISTS=$(printf "SELECT 1 FROM pg_roles WHERE rolname='%s';\n" "${PG_USER}" | psql_cmd -tA 2>/dev/null || echo "")
    if [ "$USER_EXISTS" = "1" ]; then
        log_info "User ${PG_USER} already exists, updating password ..."
        printf 'ALTER USER "%s" WITH PASSWORD '\''%s'\'';\n' "${PG_USER}" "${PG_PASSWORD}" | psql_cmd
    else
        log_info "Creating user ${PG_USER} ..."
        printf 'CREATE USER "%s" WITH PASSWORD '\''%s'\'';\n' "${PG_USER}" "${PG_PASSWORD}" | psql_cmd
    fi
    log_ok "User ${PG_USER} ready"

    DB_EXISTS=$(printf "SELECT 1 FROM pg_database WHERE datname='%s';\n" "${PG_DATABASE}" | psql_cmd -tA 2>/dev/null || echo "")
    if [ "$DB_EXISTS" = "1" ]; then
        log_ok "Database ${PG_DATABASE} already exists"
    else
        log_info "Creating database ${PG_DATABASE} ..."
        printf 'CREATE DATABASE "%s" OWNER "%s";\n' "${PG_DATABASE}" "${PG_USER}" | psql_cmd
        log_ok "Database ${PG_DATABASE} created"
    fi

    # 验证
    echo ""
    echo "========================================"
    echo "Verifying connection ..."
    if PGPASSWORD="${PG_PASSWORD}" psql -h "${PG_HOST}" -p "${PG_PORT}" -U "${PG_USER}" -d "${PG_DATABASE}" -c "SELECT version();" &>/dev/null; then
        log_ok "Connection verified successfully!"
    else
        log_error "PostgreSQL connection verification failed (${PG_HOST}:${PG_PORT}, db=${PG_DATABASE}, user=${PG_USER})"
        log_error "  systemctl status ${PG_SERVICE_NAME}"
        log_error "  firewall port ${PG_PORT}"
        log_error "  tail -30 ${PG_DATA_DIR}/log/postgresql-*.log"
        exit 1
    fi

    echo ""
    echo "========================================"
    echo "PostgreSQL RPM Deployment Completed!"
    echo "========================================"
    echo "  Host:     ${PG_HOST}"
    echo "  Port:     ${PG_PORT}"
    echo "  Database: ${PG_DATABASE}"
    echo "  User:     ${PG_USER}"
    echo "  Service:  ${PG_SERVICE_NAME}"
    echo "  Data Dir: ${PG_DATA_DIR}"
    echo ""
    echo "Useful commands:"
    echo "  systemctl status ${PG_SERVICE_NAME}   # show service status"
    echo "  systemctl restart ${PG_SERVICE_NAME}  # restart service"
    echo "  journalctl -u ${PG_SERVICE_NAME} -f   # follow service logs"
    echo "========================================"
}

# ============================================================
# APT 包部署（Ubuntu / Debian）
# ============================================================
deploy_apt() {
    echo "========================================"
    echo "PostgreSQL APT Deployment (Ubuntu/Debian)"
    echo "========================================"

    check_root
    ensure_pg_password

    # Step 1: Install PostgreSQL
    echo ""
    echo "[Step 1/7] Installing PostgreSQL ..."

    PG_PKG_CANDIDATES=("postgresql" "postgresql-15")
    INSTALLED_PKG=""
    for pkg in "${PG_PKG_CANDIDATES[@]}"; do
        if dpkg -l "$pkg" 2>/dev/null | grep -q "^ii"; then
            log_ok "PostgreSQL already installed: $pkg"
            INSTALLED_PKG="$pkg"
            break
        fi
    done

    if [ -z "$INSTALLED_PKG" ]; then
        log_info "Installing postgresql ..."
        apt-get update -y &>/dev/null
        apt-get install -y postgresql postgresql-client
        INSTALLED_PKG="postgresql"
    fi

    if ! command -v psql &>/dev/null; then
        log_info "Installing PostgreSQL client ..."
        apt-get install -y postgresql-client &>/dev/null || true
    fi
    log_ok "PostgreSQL client: $(psql --version 2>&1 | head -1)"

    # Step 2: Detect version and paths
    echo ""
    echo "[Step 2/7] Detecting PostgreSQL version and paths ..."

    PG_VERSION=$(pg_lsclusters -h 2>/dev/null | head -1 | awk '{print $1}')
    if [ -z "$PG_VERSION" ]; then
        PG_VERSION=$(ls /etc/postgresql/ 2>/dev/null | sort -V | tail -1)
    fi
    if [ -z "$PG_VERSION" ]; then
        log_error "Cannot detect PostgreSQL version. Is postgresql installed?"
        exit 1
    fi

    PG_CONF_DIR="/etc/postgresql/${PG_VERSION}/main"
    PG_DATA_DIR="/var/lib/postgresql/${PG_VERSION}/main"
    PG_SERVICE_NAME="postgresql"

    log_info "Version: ${PG_VERSION}"
    log_info "Config directory: ${PG_CONF_DIR}"
    log_info "Data directory: ${PG_DATA_DIR}"

    # Step 3: Initialize if needed
    echo ""
    echo "[Step 3/7] Checking database initialization ..."
    if [ ! -f "${PG_DATA_DIR}/PG_VERSION" ]; then
        log_info "Running pg_createcluster ..."
        pg_createcluster "$PG_VERSION" main 2>/dev/null || true
    fi
    if [ ! -f "${PG_DATA_DIR}/PG_VERSION" ]; then
        log_error "Database initialization failed"
        exit 1
    fi
    log_ok "Database initialized"

    # Step 4: Configure postgresql.conf
    echo ""
    echo "[Step 4/7] Configuring postgresql.conf ..."
    PG_CONF="${PG_CONF_DIR}/postgresql.conf"

    # 端口冲突检测：若系统 PG 已运行且当前端口 ≠ 目标端口，明确警告（防止
    # 静默改端口导致既有部署/数据访问失效——实测踩坑：5432 被改成 15432）。
    local CURRENT_PORT=""
    if [ -f "$PG_CONF" ]; then
        CURRENT_PORT="$(grep -E "^port" "$PG_CONF" 2>/dev/null | awk '{print $3}' | tr -d "'\"")"
    fi
    if [ -n "$CURRENT_PORT" ] && [ "$CURRENT_PORT" != "$PG_PORT" ]; then
        log_warn "PostgreSQL currently listens on ${CURRENT_PORT}; changing to ${PG_PORT}"
        log_warn "Confirm that no existing deployment still uses ${CURRENT_PORT} before continuing"
        if ! confirm "Change the PostgreSQL port from ${CURRENT_PORT} to ${PG_PORT}?"; then
            log_error "Cancelled: port not changed"
            exit 1
        fi
    fi

    if [ -f "$PG_CONF" ] && [ ! -f "${PG_CONF}.bak" ]; then
        cp "$PG_CONF" "${PG_CONF}.bak"
    fi

    if grep -q "^#listen_addresses" "$PG_CONF" 2>/dev/null; then
        sed -i "s/^#listen_addresses.*/listen_addresses = '*'/" "$PG_CONF"
    elif grep -q "^listen_addresses" "$PG_CONF" 2>/dev/null; then
        sed -i "s/^listen_addresses.*/listen_addresses = '*'/" "$PG_CONF"
    else
        echo "listen_addresses = '*'" >>"$PG_CONF"
    fi

    if grep -q "^#port" "$PG_CONF" 2>/dev/null; then
        sed -i "s/^#port.*/port = ${PG_PORT}/" "$PG_CONF"
    elif grep -q "^port" "$PG_CONF" 2>/dev/null; then
        sed -i "s/^port.*/port = ${PG_PORT}/" "$PG_CONF"
    else
        echo "port = ${PG_PORT}" >>"$PG_CONF"
    fi
    log_ok "postgresql.conf configured (listen=*, port=${PG_PORT})"

    # Step 5: Configure pg_hba.conf
    echo ""
    echo "[Step 5/7] Configuring pg_hba.conf ..."
    PG_HBA="${PG_CONF_DIR}/pg_hba.conf"
    if [ -f "$PG_HBA" ] && [ ! -f "${PG_HBA}.bak" ]; then
        cp "$PG_HBA" "${PG_HBA}.bak"
    fi

    # Keep postgres superuser local as peer
    if grep -q "^local\s\+all\s\+postgres\s\+peer" "$PG_HBA" 2>/dev/null; then
        :
    else
        sed -i '/^local\s\+all\s\+all/i local   all             postgres                                peer' "$PG_HBA" 2>/dev/null ||
            echo "local   all             postgres                                peer" >/tmp/pg_hba_insert.tmp
    fi

    # Local users md5 auth
    sed -i 's/^local\s\+all\s\+all\s\+peer/local   all             all                                     md5/' "$PG_HBA"
    sed -i 's/^local\s\+all\s\+all\s\+scram-sha-256/local   all             all                                     md5/' "$PG_HBA"
    sed -i 's/^host\s\+all\s\+all\s\+127\.0\.0\.1\/32\s\+scram-sha-256/host    all             all             127.0.0.1\/32            md5/' "$PG_HBA"
    sed -i 's/^host\s\+all\s\+all\s\+::1\/128\s\+scram-sha-256/host    all             all             ::1\/128                 md5/' "$PG_HBA"
    sed -i 's/^host\s\+all\s\+all\s\+127\.0\.0\.1\/32\s\+md5/host    all             all             127.0.0.1\/32            md5/' "$PG_HBA"

    if ! grep -q "host    all             all             0.0.0.0/0" "$PG_HBA" 2>/dev/null; then
        echo "host    all             all             0.0.0.0/0               md5" >>"$PG_HBA"
    fi
    if ! grep -q "host    all             all             ::/0" "$PG_HBA" 2>/dev/null; then
        echo "host    all             all             ::/0                    md5" >>"$PG_HBA"
    fi
    log_ok "pg_hba.conf configured (md5 auth + remote access)"

    # Step 6: Start service
    echo ""
    echo "[Step 6/7] Starting PostgreSQL service ..."
    systemctl enable "$PG_SERVICE_NAME" &>/dev/null || true
    systemctl restart "$PG_SERVICE_NAME"

    log_info "Waiting for PostgreSQL to become ready ..."
    READY=0
    for _ in {1..30}; do
        if command -v pg_isready &>/dev/null; then
            if pg_isready -p "${PG_PORT}" &>/dev/null; then
                READY=1
                break
            fi
        fi
        if su - postgres -c "psql -h 127.0.0.1 -p ${PG_PORT} -U postgres -c 'SELECT 1'" &>/dev/null; then
            READY=1
            break
        fi
        sleep 1
    done

    if [ "$READY" -eq 1 ] && systemctl is-active --quiet "$PG_SERVICE_NAME"; then
        log_ok "PostgreSQL service is running"
    else
        log_error "PostgreSQL service failed to start"
        log_error "Check: systemctl status ${PG_SERVICE_NAME}"
        log_error "Check: tail -50 ${PG_DATA_DIR}/log/postgresql-*.log"
        exit 1
    fi

    # Step 7: Create user and database
    echo ""
    echo "[Step 7/7] Creating user and database ..."
    psql_cmd() {
        su - postgres -c "psql -p ${PG_PORT} $*"
    }

    USER_EXISTS=$(printf "SELECT 1 FROM pg_roles WHERE rolname='%s';\n" "${PG_USER}" | psql_cmd -tA 2>/dev/null || echo "")
    if [ "$USER_EXISTS" = "1" ]; then
        log_info "User ${PG_USER} already exists, updating password ..."
        printf 'ALTER USER "%s" WITH PASSWORD '\''%s'\'';\n' "${PG_USER}" "${PG_PASSWORD}" | psql_cmd
    else
        log_info "Creating user ${PG_USER} ..."
        printf 'CREATE USER "%s" WITH PASSWORD '\''%s'\'';\n' "${PG_USER}" "${PG_PASSWORD}" | psql_cmd
    fi
    log_ok "User ${PG_USER} ready"

    DB_EXISTS=$(printf "SELECT 1 FROM pg_database WHERE datname='%s';\n" "${PG_DATABASE}" | psql_cmd -tA 2>/dev/null || echo "")
    if [ "$DB_EXISTS" = "1" ]; then
        log_ok "Database ${PG_DATABASE} already exists"
    else
        log_info "Creating database ${PG_DATABASE} ..."
        printf 'CREATE DATABASE "%s" OWNER "%s";\n' "${PG_DATABASE}" "${PG_USER}" | psql_cmd
        log_ok "Database ${PG_DATABASE} created"
    fi

    # Verify
    echo ""
    echo "========================================"
    echo "Verifying connection ..."
    if PGPASSWORD="${PG_PASSWORD}" psql -h "${PG_HOST}" -p "${PG_PORT}" -U "${PG_USER}" -d "${PG_DATABASE}" -c "SELECT version();" &>/dev/null; then
        log_ok "Connection verified successfully!"
    else
        log_error "PostgreSQL connection verification failed (${PG_HOST}:${PG_PORT}, db=${PG_DATABASE}, user=${PG_USER})"
        log_error "  systemctl status ${PG_SERVICE_NAME}"
        log_error "  firewall port ${PG_PORT}"
        log_error "  tail -30 ${PG_DATA_DIR}/log/postgresql-*.log"
        exit 1
    fi

    echo ""
    echo "========================================"
    echo "PostgreSQL APT Deployment Completed!"
    echo "========================================"
    echo "  Host:     ${PG_HOST}"
    echo "  Port:     ${PG_PORT}"
    echo "  Database: ${PG_DATABASE}"
    echo "  User:     ${PG_USER}"
    echo "  Version:  ${PG_VERSION}"
    echo "  Config:   ${PG_CONF_DIR}"
    echo "  Data Dir: ${PG_DATA_DIR}"
    echo ""
    echo "Useful commands:"
    echo "  systemctl status ${PG_SERVICE_NAME}            # show service status"
    echo "  pg_lsclusters                                   # list clusters"
    echo "  journalctl -u ${PG_SERVICE_NAME} -f            # follow service logs"
    echo "========================================"
}

# ============================================================
# 入口
# ============================================================
case "$DEPLOY_MODE" in
docker)
    deploy_docker
    ;;
rpm)
    deploy_rpm
    ;;
apt)
    deploy_apt
    ;;
esac
