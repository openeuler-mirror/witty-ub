#!/bin/bash
# Copyright (c) Huawei Technologies Co., Ltd. 2023-2026. All rights reserved.
# witty-ub is licensed under the Mulan PSL v2.
#
# witty-ub manager - PostgreSQL 初始化脚本（RPM 安装后由 manager.sh 调用）
#
# 用法:
#   /usr/libexec/witty-ub-manager/deploy_pg.sh
#
# 由 manager.sh 的 deploy 子命令调用，幂等：已存在的资源（包/数据目录/用户/库）
# 跳过创建。仅支持 openEuler (RPM) / Ubuntu (APT)，不支持 Docker 模式。
#
# 配置来源: /etc/witty-ub/pg.conf（由 witty-ub-manager 子包安装）

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/_lib.sh"

# ──────────────────── 公共 PG 工具 ────────────────────

# 以 postgres 用户身份执行 psql（自动处理 root/sudo）
psql_as_postgres() {
    if _is_root; then
        su - postgres -c "psql -p ${PG_PORT} $*"
    else
        sudo su - postgres -c "psql -p ${PG_PORT} $*"
    fi
}

# 配置 postgresql.conf 的 listen_addresses 和 port
configure_pg_conf() {
    local PG_CONF="$1"
    [ -f "$PG_CONF" ] || return 1
    [ -f "${PG_CONF}.bak" ] || cp "$PG_CONF" "${PG_CONF}.bak"

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
}

# 配置 pg_hba.conf 的 md5 认证 + 远程访问
configure_pg_hba() {
    local PG_HBA="$1"
    [ -f "$PG_HBA" ] || return 1
    [ -f "${PG_HBA}.bak" ] || cp "$PG_HBA" "${PG_HBA}.bak"

    # postgres 超级用户本地 peer 认证
    grep -q "^local\s\+all\s\+postgres\s\+peer" "$PG_HBA" 2>/dev/null || \
        sed -i '/^local\s\+all\s\+all/i local   all             postgres                                peer' "$PG_HBA" 2>/dev/null || true

    # 本地用户 md5 认证
    sed -i 's/^local\s\+all\s\+all\s\+peer/local   all             all                                     md5/' "$PG_HBA" 2>/dev/null || true
    sed -i 's/^local\s\+all\s\+all\s\+ident/local   all             all                                     md5/' "$PG_HBA" 2>/dev/null || true
    sed -i 's/^local\s\+all\s\+all\s\+scram-sha-256/local   all             all                                     md5/' "$PG_HBA" 2>/dev/null || true
    sed -i 's/^host\s\+all\s\+all\s\+127\.0\.0\.1\/32\s\+ident/host    all             all             127.0.0.1\/32            md5/' "$PG_HBA" 2>/dev/null || true
    sed -i 's/^host\s\+all\s\+all\s\+::1\/128\s\+ident/host    all             all             ::1\/128                 md5/' "$PG_HBA" 2>/dev/null || true
    sed -i 's/^host\s\+all\s\+all\s\+127\.0\.0\.1\/32\s\+scram-sha-256/host    all             all             127.0.0.1\/32            md5/' "$PG_HBA" 2>/dev/null || true
    sed -i 's/^host\s\+all\s\+all\s\+::1\/128\s\+scram-sha-256/host    all             all             ::1\/128                 md5/' "$PG_HBA" 2>/dev/null || true

    # 远程访问
    grep -q "host    all             all             0.0.0.0/0" "$PG_HBA" 2>/dev/null || \
        echo "host    all             all             0.0.0.0/0               md5" >> "$PG_HBA"
    grep -q "host    all             all             ::/0" "$PG_HBA" 2>/dev/null || \
        echo "host    all             all             ::/0                    md5" >> "$PG_HBA"
}

# 等待 PG 就绪
wait_pg_ready() {
    local max=${1:-30}
    local i
    for i in $(seq 1 "$max"); do
        if _has_cmd pg_isready && pg_isready -p "${PG_PORT}" >/dev/null 2>&1; then
            return 0
        fi
        if psql_as_postgres "-c 'SELECT 1'" >/dev/null 2>&1; then
            return 0
        fi
        sleep 1
    done
    return 1
}

# 创建用户和数据库
create_user_and_db() {
    _info "创建用户 ${PG_USER} 和数据库 ${PG_DATABASE}..."

    local user_exists
    user_exists=$(printf "SELECT 1 FROM pg_roles WHERE rolname='%s';\n" "${PG_USER}" | psql_as_postgres "-tA" 2>/dev/null || echo "")
    if [ "$user_exists" = "1" ]; then
        _info "用户已存在，更新密码..."
        printf 'ALTER USER "%s" WITH PASSWORD '\''%s'\'';\n' "${PG_USER}" "${PG_PASSWORD}" | psql_as_postgres
    else
        printf 'CREATE USER "%s" WITH PASSWORD '\''%s'\'';\n' "${PG_USER}" "${PG_PASSWORD}" | psql_as_postgres
    fi
    _log "用户 ${PG_USER} 就绪"

    local db_exists
    db_exists=$(printf "SELECT 1 FROM pg_database WHERE datname='%s';\n" "${PG_DATABASE}" | psql_as_postgres "-tA" 2>/dev/null || echo "")
    if [ "$db_exists" = "1" ]; then
        _log "数据库 ${PG_DATABASE} 已存在"
    else
        printf 'CREATE DATABASE "%s" OWNER "%s";\n' "${PG_DATABASE}" "${PG_USER}" | psql_as_postgres
        _log "数据库 ${PG_DATABASE} 已创建"
    fi
}

# ──────────────────── RPM 部署 ────────────────────

deploy_rpm() {
    _step_header "PostgreSQL 部署 (RPM)"

    _require_root || return 1
    _load_pg_credentials || { _err "无法加载 PG 凭据（/etc/witty-ub/pg.conf）"; return 1; }

    # Step 1: 安装 PostgreSQL
    local PG_PKG_CANDIDATES=("postgresql15-server" "postgresql-server")
    local INSTALLED_PKG=""
    for pkg in "${PG_PKG_CANDIDATES[@]}"; do
        if rpm -q "$pkg" >/dev/null 2>&1; then
            _log "PostgreSQL 已安装: $pkg"
            INSTALLED_PKG="$pkg"
            break
        fi
    done

    if [ -z "$INSTALLED_PKG" ]; then
        local SUDO=""; _is_root || SUDO="sudo"
        for pkg in "${PG_PKG_CANDIDATES[@]}"; do
            _info "尝试安装 $pkg ..."
            if eval "$SUDO yum install -y --allowerasing $pkg" 2>&1 | tail -3; then
                INSTALLED_PKG="$pkg"
                break
            fi
        done
        [ -n "$INSTALLED_PKG" ] || { _err "安装 PostgreSQL 失败，请手动: sudo yum install -y postgresql15-server"; return 1; }
    fi

    command -v psql >/dev/null 2>&1 || {
        local SUDO=""; _is_root || SUDO="sudo"
        eval "$SUDO yum install -y --allowerasing postgresql" >/dev/null 2>&1 || true
    }
    _log "PostgreSQL client: $(psql --version 2>&1 | head -1)"

    # Step 2: 数据目录和服务名
    local PG_DATA_DIR PG_SERVICE_NAME
    if [ "$INSTALLED_PKG" = "postgresql15-server" ]; then
        PG_DATA_DIR="${PG_DATA_DIR_OVERRIDE:-/var/lib/pgsql/15/data}"
        PG_SERVICE_NAME="${PG_SERVICE_NAME_OVERRIDE:-postgresql-15}"
    else
        PG_DATA_DIR="${PG_DATA_DIR_OVERRIDE:-/var/lib/pgsql/data}"
        PG_SERVICE_NAME="${PG_SERVICE_NAME_OVERRIDE:-postgresql}"
    fi
    _info "Data dir: $PG_DATA_DIR"
    _info "Service:  $PG_SERVICE_NAME"

    # Step 3: 初始化数据库
    if [ ! -f "${PG_DATA_DIR}/PG_VERSION" ]; then
        _info "初始化数据库..."
        /usr/pgsql-15/bin/postgresql-15-setup initdb 2>/dev/null || \
        postgresql-setup --initdb 2>/dev/null || \
        su - postgres -c "/usr/pgsql-15/bin/initdb -D ${PG_DATA_DIR}" 2>/dev/null || \
        sudo su - postgres -c "initdb -D ${PG_DATA_DIR}"
        _log "数据库已初始化"
    else
        _log "数据库已初始化，跳过"
    fi

    # Step 4: 配置 postgresql.conf
    configure_pg_conf "${PG_DATA_DIR}/postgresql.conf"
    _log "postgresql.conf 已配置 (listen=*, port=${PG_PORT})"

    # Step 5: 配置 pg_hba.conf
    configure_pg_hba "${PG_DATA_DIR}/pg_hba.conf"
    _log "pg_hba.conf 已配置 (md5 auth + remote access)"

    # Step 6: 启动服务
    systemctl enable "$PG_SERVICE_NAME" 2>/dev/null || true
    systemctl restart "$PG_SERVICE_NAME"

    _info "等待 PostgreSQL 就绪..."
    if ! wait_pg_ready 30; then
        _err "PostgreSQL 启动失败: systemctl status $PG_SERVICE_NAME"
        return 1
    fi
    _log "PostgreSQL 服务已运行"

    # Step 7: 创建用户和数据库
    create_user_and_db

    # 验证
    if PGPASSWORD="${PG_PASSWORD}" psql -h "${PG_HOST}" -p "${PG_PORT}" -U "${PG_USER}" -d "${PG_DATABASE}" -c "SELECT version();" >/dev/null 2>&1; then
        _log "连接验证通过"
    else
        _warn "连接验证失败，请检查 pg_hba.conf / 防火墙 / deploy.conf"
    fi
}

# ──────────────────── APT 部署 ────────────────────

deploy_apt() {
    _step_header "PostgreSQL 部署 (APT)"

    _require_root || return 1
    _load_pg_credentials || { _err "无法加载 PG 凭据（/etc/witty-ub/pg.conf）"; return 1; }

    # Step 1: 安装 PostgreSQL
    local PG_PKG_CANDIDATES=("postgresql" "postgresql-15")
    local INSTALLED_PKG=""
    for pkg in "${PG_PKG_CANDIDATES[@]}"; do
        if dpkg -l "$pkg" 2>/dev/null | grep -q "^ii"; then
            _log "PostgreSQL 已安装: $pkg"
            INSTALLED_PKG="$pkg"
            break
        fi
    done

    if [ -z "$INSTALLED_PKG" ]; then
        local SUDO=""; _is_root || SUDO="sudo"
        _info "安装 postgresql ..."
        eval "$SUDO apt-get update -y" >/dev/null 2>&1 || true
        eval "$SUDO apt-get install -y postgresql postgresql-client" || { _err "安装失败"; return 1; }
        INSTALLED_PKG="postgresql"
    fi

    command -v psql >/dev/null 2>&1 || {
        local SUDO=""; _is_root || SUDO="sudo"
        eval "$SUDO apt-get install -y postgresql-client" >/dev/null 2>&1 || true
    }
    _log "PostgreSQL client: $(psql --version 2>&1 | head -1)"

    # Step 2: 检测版本和路径
    local PG_VERSION
    PG_VERSION=$(pg_lsclusters -h 2>/dev/null | head -1 | awk '{print $1}')
    [ -z "$PG_VERSION" ] && PG_VERSION=$(ls /etc/postgresql/ 2>/dev/null | sort -V | tail -1)
    [ -z "$PG_VERSION" ] && { _err "无法检测 PostgreSQL 版本"; return 1; }

    local PG_CONF_DIR="/etc/postgresql/${PG_VERSION}/main"
    local PG_DATA_DIR="/var/lib/postgresql/${PG_VERSION}/main"
    local PG_SERVICE_NAME="postgresql"

    _info "Version: $PG_VERSION"
    _info "Config:  $PG_CONF_DIR"
    _info "Data:    $PG_DATA_DIR"

    # Step 3: 初始化（若未初始化）
    if [ ! -f "${PG_DATA_DIR}/PG_VERSION" ]; then
        _info "运行 pg_createcluster ..."
        pg_createcluster "$PG_VERSION" main 2>/dev/null || sudo pg_createcluster "$PG_VERSION" main
    fi
    [ -f "${PG_DATA_DIR}/PG_VERSION" ] || { _err "数据库初始化失败"; return 1; }
    _log "数据库已初始化"

    # Step 4: 配置 postgresql.conf
    configure_pg_conf "${PG_CONF_DIR}/postgresql.conf"
    _log "postgresql.conf 已配置 (listen=*, port=${PG_PORT})"

    # Step 5: 配置 pg_hba.conf
    configure_pg_hba "${PG_CONF_DIR}/pg_hba.conf"
    _log "pg_hba.conf 已配置 (md5 auth + remote access)"

    # Step 6: 启动服务
    systemctl enable "$PG_SERVICE_NAME" 2>/dev/null || true
    systemctl restart "$PG_SERVICE_NAME"

    _info "等待 PostgreSQL 就绪..."
    if ! wait_pg_ready 30; then
        _err "PostgreSQL 启动失败: systemctl status $PG_SERVICE_NAME"
        return 1
    fi
    _log "PostgreSQL 服务已运行"

    # Step 7: 创建用户和数据库
    create_user_and_db

    # 验证
    if PGPASSWORD="${PG_PASSWORD}" psql -h "${PG_HOST}" -p "${PG_PORT}" -U "${PG_USER}" -d "${PG_DATABASE}" -c "SELECT version();" >/dev/null 2>&1; then
        _log "连接验证通过"
    else
        _warn "连接验证失败，请检查 pg_hba.conf / 防火墙 / deploy.conf"
    fi
}

# ──────────────────── 入口 ────────────────────

detect_os || exit 1
case "$OS_ID" in
    openeuler) deploy_rpm ;;
    ubuntu)    deploy_apt ;;
    *)         _err "不支持的 OS: $OS_ID"; exit 1 ;;
esac
