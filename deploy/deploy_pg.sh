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
CONF_FILE="${DEPLOY_DIR}/pg.conf"

# ---------- 参数解析 ----------
DEPLOY_MODE="docker"   # 默认 docker

usage() {
    cat <<EOF
PostgreSQL 一键部署脚本

用法:
  $0 [OPTIONS]

 选项:
  --docker    Docker 容器部署（默认）
  --rpm       RPM 包部署（适用于 openEuler / CentOS / RHEL）
  --apt       APT 包部署（适用于 Ubuntu / Debian）
  -h, --help  显示此帮助

配置文件: ${CONF_FILE}
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

# ---------- 加载配置 ----------
if [ -f "$CONF_FILE" ]; then
    echo "[INFO] Loading config from ${CONF_FILE}"
    source "$CONF_FILE"
else
    echo "[ERROR] Config file not found: ${CONF_FILE}"
    exit 1
fi

# ---------- 公共工具函数 ----------
log_info()  { echo "[INFO]  $*"; }
log_ok()    { echo "[OK]    $*"; }
log_warn()  { echo "[WARN]  $*"; }
log_error() { echo "[ERROR] $*"; }

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
        log_warn "${prompt} (非交互环境，自动继续)"
        return 0
    fi
    local ans=""
    printf "%s [y/N] " "$prompt"
    read -r ans
    case "$ans" in
        y|Y|yes|YES) return 0 ;;
        *) return 1 ;;
    esac
}

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

# ============================================================
# Docker 容器部署
# ============================================================
deploy_docker() {
    echo "========================================"
    echo "PostgreSQL Docker Deployment"
    echo "========================================"

    check_docker

    # ---------- PostgreSQL 镜像候选列表（按优先级从高到低）
    # 每个条目: 镜像地址|用户环境变量|密码环境变量|库名环境变量|容器内数据目录
    declare -a PG_IMAGE_CANDIDATES=(
        "quay.io/sclorg/postgresql-15-c9s:latest|POSTGRESQL_USER|POSTGRESQL_PASSWORD|POSTGRESQL_DATABASE|/var/lib/pgsql/data"
        "postgres:15|POSTGRES_USER|POSTGRES_PASSWORD|POSTGRES_DB|/var/lib/postgresql/data"
        "postgres:latest|POSTGRES_USER|POSTGRES_PASSWORD|POSTGRES_DB|/var/lib/postgresql/data"
    )

    parse_image_entry() {
        echo "$1" | cut -d'|' -f"$2"
    }

    # Step 1: 检查/拉取镜像（带回退）
    echo ""
    echo "[Step 1/6] Checking and pulling PostgreSQL image ..."

    SELECTED_IMAGE=""
    SELECTED_ENV_USER=""
    SELECTED_ENV_PASS=""
    SELECTED_ENV_DB=""
    SELECTED_DATA_DIR=""

    log_info "Checking local images for PostgreSQL 15 ..."
    for entry in "${PG_IMAGE_CANDIDATES[@]}"; do
        image=$(parse_image_entry "$entry" 1)
        if docker image inspect "$image" &> /dev/null; then
            log_ok "Found local image: ${image}"
            SELECTED_IMAGE="$image"
            SELECTED_ENV_USER=$(parse_image_entry "$entry" 2)
            SELECTED_ENV_PASS=$(parse_image_entry "$entry" 3)
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
            if docker pull "$image" &> /dev/null; then
                log_ok "Pulled ${image} successfully"
                SELECTED_IMAGE="$image"
                SELECTED_ENV_USER=$(parse_image_entry "$entry" 2)
                SELECTED_ENV_PASS=$(parse_image_entry "$entry" 3)
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
        -e "${SELECTED_ENV_USER}=${PG_USER}" \
        -e "${SELECTED_ENV_PASS}=${PG_PASSWORD}" \
        -e "${SELECTED_ENV_DB}=${PG_DATABASE}" \
        --health-cmd="pg_isready -U ${PG_USER} -d ${PG_DATABASE}" \
        --health-interval="${PG_HEALTH_INTERVAL}" \
        --health-timeout="${PG_HEALTH_TIMEOUT}" \
        --health-retries="${PG_HEALTH_RETRIES}" \
        --health-start-period="${PG_HEALTH_START_PERIOD}" \
        --network "${PG_NETWORK}" \
        "${SELECTED_IMAGE}"
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
        log_warn "PostgreSQL health status: ${HEALTH} (may still be starting)"
    fi

    # 验证连接
    echo ""
    echo "========================================"
    echo "Verifying connection ..."
    for i in {1..10}; do
        if PGPASSWORD="${PG_PASSWORD}" psql -h "${PG_HOST}" -p "${PG_PORT}" -U "${PG_USER}" -d "${PG_DATABASE}" -c "SELECT version();" &> /dev/null; then
            log_ok "Connection verified successfully!"
            break
        fi
        sleep 2
    done

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
    echo "  docker ps                                    # 查看运行中的容器"
    echo "  docker logs ${PG_CONTAINER_NAME} -f         # 查看容器日志"
    echo "  docker stop ${PG_CONTAINER_NAME}            # 停止容器"
    echo "  docker start ${PG_CONTAINER_NAME}           # 启动已停止的容器"
    echo "  docker restart ${PG_CONTAINER_NAME}         # 重启容器"
    echo "  docker exec -it ${PG_CONTAINER_NAME} psql   # 进入 psql"
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

    # Step 1: 安装 PostgreSQL
    echo ""
    echo "[Step 1/7] Installing PostgreSQL 15 ..."

    PG_PKG_CANDIDATES=("postgresql15-server" "postgresql-server")
    INSTALLED_PKG=""
    for pkg in "${PG_PKG_CANDIDATES[@]}"; do
        if rpm -q "$pkg" &> /dev/null; then
            log_ok "PostgreSQL already installed: $pkg"
            INSTALLED_PKG="$pkg"
            break
        fi
    done

    if [ -z "$INSTALLED_PKG" ]; then
        INSTALL_SUCCESS=0
        for pkg in "${PG_PKG_CANDIDATES[@]}"; do
            log_info "Trying to install $pkg ..."
            if yum install -y --allowerasing "$pkg" &> /dev/null; then
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

    if ! command -v psql &> /dev/null; then
        log_info "Installing PostgreSQL client ..."
        yum install -y --allowerasing postgresql &> /dev/null || true
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
        /usr/pgsql-15/bin/postgresql-15-setup initdb 2>/dev/null || \
        postgresql-setup --initdb 2>/dev/null || \
        su - postgres -c "/usr/pgsql-15/bin/initdb -D ${PG_DATA_DIR}" 2>/dev/null || \
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
        echo "listen_addresses = '*'" >> "$PG_CONF"
    fi

    if grep -q "^#port" "$PG_CONF" 2>/dev/null; then
        sed -i "s/^#port.*/port = ${PG_PORT}/" "$PG_CONF"
    elif grep -q "^port" "$PG_CONF" 2>/dev/null; then
        sed -i "s/^port.*/port = ${PG_PORT}/" "$PG_CONF"
    else
        echo "port = ${PG_PORT}" >> "$PG_CONF"
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
        sed -i '/^local\s\+all\s\+all/i local   all             postgres                                peer' "$PG_HBA" 2>/dev/null || \
        echo "local   all             postgres                                peer" > /tmp/pg_hba_insert.tmp
    fi

    # 本地用户 md5 认证
    sed -i 's/^local\s\+all\s\+all\s\+peer/local   all             all                                     md5/' "$PG_HBA"
    sed -i 's/^local\s\+all\s\+all\s\+ident/local   all             all                                     md5/' "$PG_HBA"
    sed -i 's/^host\s\+all\s\+all\s\+127\.0\.0\.1\/32\s\+ident/host    all             all             127.0.0.1\/32            md5/' "$PG_HBA"
    sed -i 's/^host\s\+all\s\+all\s\+::1\/128\s\+ident/host    all             all             ::1\/128                 md5/' "$PG_HBA"

    if ! grep -q "host    all             all             0.0.0.0/0" "$PG_HBA" 2>/dev/null; then
        echo "host    all             all             0.0.0.0/0               md5" >> "$PG_HBA"
    fi
    if ! grep -q "host    all             all             ::/0" "$PG_HBA" 2>/dev/null; then
        echo "host    all             all             ::/0                    md5" >> "$PG_HBA"
    fi
    log_ok "pg_hba.conf configured (md5 auth + remote access)"

    # Step 6: 启动服务
    echo ""
    echo "[Step 6/7] Starting PostgreSQL service ..."
    systemctl enable "$PG_SERVICE_NAME" &> /dev/null || true

    if command -v getenforce &> /dev/null && [ "$(getenforce 2>/dev/null)" = "Enforcing" ]; then
        if command -v semanage &> /dev/null; then
            log_info "Setting SELinux port label for port ${PG_PORT} ..."
            semanage port -a -t postgresql_port_t -p tcp "${PG_PORT}" 2>/dev/null || \
            semanage port -m -t postgresql_port_t -p tcp "${PG_PORT}" 2>/dev/null || true
        else
            log_warn "SELinux is Enforcing but semanage not found. Install it first:"
            log_warn "  yum install -y policycoreutils-python-utils"
        fi
    fi

    systemctl start "$PG_SERVICE_NAME"

    log_info "Waiting for PostgreSQL to become ready ..."
    READY=0
    for i in {1..30}; do
        if command -v pg_isready &> /dev/null; then
            if pg_isready -p "${PG_PORT}" &> /dev/null; then
                READY=1
                break
            fi
        fi
        if su - postgres -c "psql -h 127.0.0.1 -p ${PG_PORT} -U postgres -c 'SELECT 1'" &> /dev/null; then
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
    if PGPASSWORD="${PG_PASSWORD}" psql -h "${PG_HOST}" -p "${PG_PORT}" -U "${PG_USER}" -d "${PG_DATABASE}" -c "SELECT version();" &> /dev/null; then
        log_ok "Connection verified successfully!"
    else
        log_warn "Connection verification failed. Check:"
        log_warn "  systemctl status ${PG_SERVICE_NAME}"
        log_warn "  firewall port ${PG_PORT}"
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
    echo "  systemctl status ${PG_SERVICE_NAME}   # 查看服务状态"
    echo "  systemctl restart ${PG_SERVICE_NAME}  # 重启服务"
    echo "  journalctl -u ${PG_SERVICE_NAME} -f   # 查看服务日志"
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
        apt-get update -y &> /dev/null
        apt-get install -y postgresql postgresql-client
        INSTALLED_PKG="postgresql"
    fi

    if ! command -v psql &> /dev/null; then
        log_info "Installing PostgreSQL client ..."
        apt-get install -y postgresql-client &> /dev/null || true
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
        log_warn "检测到 PostgreSQL 当前监听端口为 ${CURRENT_PORT}，将改为 ${PG_PORT}"
        log_warn "若 ${CURRENT_PORT} 上有正在使用的数据（如既有部署），请先确认再继续"
        if ! confirm "确认将 PostgreSQL 端口从 ${CURRENT_PORT} 改为 ${PG_PORT}？"; then
            log_error "已取消：不修改端口"
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
        echo "listen_addresses = '*'" >> "$PG_CONF"
    fi

    if grep -q "^#port" "$PG_CONF" 2>/dev/null; then
        sed -i "s/^#port.*/port = ${PG_PORT}/" "$PG_CONF"
    elif grep -q "^port" "$PG_CONF" 2>/dev/null; then
        sed -i "s/^port.*/port = ${PG_PORT}/" "$PG_CONF"
    else
        echo "port = ${PG_PORT}" >> "$PG_CONF"
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
        sed -i '/^local\s\+all\s\+all/i local   all             postgres                                peer' "$PG_HBA" 2>/dev/null || \
        echo "local   all             postgres                                peer" > /tmp/pg_hba_insert.tmp
    fi

    # Local users md5 auth
    sed -i 's/^local\s\+all\s\+all\s\+peer/local   all             all                                     md5/' "$PG_HBA"
    sed -i 's/^local\s\+all\s\+all\s\+scram-sha-256/local   all             all                                     md5/' "$PG_HBA"
    sed -i 's/^host\s\+all\s\+all\s\+127\.0\.0\.1\/32\s\+scram-sha-256/host    all             all             127.0.0.1\/32            md5/' "$PG_HBA"
    sed -i 's/^host\s\+all\s\+all\s\+::1\/128\s\+scram-sha-256/host    all             all             ::1\/128                 md5/' "$PG_HBA"
    sed -i 's/^host\s\+all\s\+all\s\+127\.0\.0\.1\/32\s\+md5/host    all             all             127.0.0.1\/32            md5/' "$PG_HBA"

    if ! grep -q "host    all             all             0.0.0.0/0" "$PG_HBA" 2>/dev/null; then
        echo "host    all             all             0.0.0.0/0               md5" >> "$PG_HBA"
    fi
    if ! grep -q "host    all             all             ::/0" "$PG_HBA" 2>/dev/null; then
        echo "host    all             all             ::/0                    md5" >> "$PG_HBA"
    fi
    log_ok "pg_hba.conf configured (md5 auth + remote access)"

    # Step 6: Start service
    echo ""
    echo "[Step 6/7] Starting PostgreSQL service ..."
    systemctl enable "$PG_SERVICE_NAME" &> /dev/null || true
    systemctl restart "$PG_SERVICE_NAME"

    log_info "Waiting for PostgreSQL to become ready ..."
    READY=0
    for i in {1..30}; do
        if command -v pg_isready &> /dev/null; then
            if pg_isready -p "${PG_PORT}" &> /dev/null; then
                READY=1
                break
            fi
        fi
        if su - postgres -c "psql -h 127.0.0.1 -p ${PG_PORT} -U postgres -c 'SELECT 1'" &> /dev/null; then
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
    if PGPASSWORD="${PG_PASSWORD}" psql -h "${PG_HOST}" -p "${PG_PORT}" -U "${PG_USER}" -d "${PG_DATABASE}" -c "SELECT version();" &> /dev/null; then
        log_ok "Connection verified successfully!"
    else
        log_warn "Connection verification failed. Check:"
        log_warn "  systemctl status ${PG_SERVICE_NAME}"
        log_warn "  firewall port ${PG_PORT}"
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
    echo "  systemctl status ${PG_SERVICE_NAME}            # 查看服务状态"
    echo "  pg_lsclusters                                   # 列出所有集群"
    echo "  journalctl -u ${PG_SERVICE_NAME} -f            # 查看服务日志"
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
