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
# 跳过创建。按 RPM/APT 包管理器选择安装方式，不支持 Docker 模式。
#
# 配置来源: /etc/witty-ub/deploy.conf（由 witty-ub-manager 子包安装，兼容旧名 pg.conf）

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/_lib.sh"

# ──────────────────── 公共 PG 工具 ────────────────────

ensure_pg_password() {
    # 密码存放于独立密钥文件 PG_SECRET_FILE（/etc/witty-ub/pg.passwd, mode 0600），
    # 不回写 deploy.conf —— 配置文件保持 <CHANGE_ME> 占位，杜绝污染源码/RPM 安装文件。
    #
    # 优先级: 已存在的密钥文件 > deploy.conf 中已设置的口令(一次性迁移) > 交互输入/自动生成。
    if [ -f "$PG_SECRET_FILE" ]; then
        local cached
        cached="$(cat "$PG_SECRET_FILE" 2>/dev/null | tr -d '\r\n')"
        if [ -n "$cached" ]; then
            chmod 0600 "$PG_SECRET_FILE"
            PG_PASSWORD="$cached"
            export PGPASSWORD="$PG_PASSWORD"
            _log "PostgreSQL 密码已从密钥文件加载: $PG_SECRET_FILE"
            return 0
        fi
    fi

    # 迁移路径: 旧部署已把口令写进 deploy.conf，一次性搬到密钥文件，之后不再回写配置。
    if [ -n "${PG_PASSWORD:-}" ] && [ "$PG_PASSWORD" != "<CHANGE_ME>" ] && [ "$PG_PASSWORD" != "witty-ub" ]; then
        _info "将 deploy.conf 中的旧口令迁移到密钥文件 $PG_SECRET_FILE"
        _write_pg_secret "$PG_PASSWORD" || return 1
        export PGPASSWORD="$PG_PASSWORD"
        _log "PostgreSQL 密码已迁移到密钥文件"
        return 0
    fi

    local input_password=""
    local confirm_password=""
    if [ -t 0 ]; then
        read -r -s -p "请输入 PostgreSQL 密码（至少 6 位字母数字，直接回车自动生成）: " input_password
        echo ""
        if [ -n "$input_password" ]; then
            if [[ ! "$input_password" =~ ^[A-Za-z0-9]{6,}$ ]]; then
                _err "PostgreSQL 密码必须为至少 6 位字母数字"
                return 1
            fi
            read -r -s -p "请再次输入 PostgreSQL 密码: " confirm_password
            echo ""
            if [ "$input_password" != "$confirm_password" ]; then
                _err "两次输入的 PostgreSQL 密码不一致"
                return 1
            fi
        fi
    fi
    if [ -n "$input_password" ]; then
        PG_PASSWORD="$input_password"
        _info "已使用用户输入的 PostgreSQL 密码"
    else
        PG_PASSWORD="$(head -c 24 /dev/urandom | base64 | tr -d '/+=' | head -c 24)"
        _warn "已为 PG 自动生成随机口令"
    fi
    _write_pg_secret "$PG_PASSWORD" || return 1
    export PGPASSWORD="$PG_PASSWORD"
    _info "PostgreSQL 密码已保存到密钥文件: $PG_SECRET_FILE"
}

# 将口令写入密钥文件（mode 0600，仅属主可读）。不修改任何配置文件。
_write_pg_secret() {
    local password="$1"
    local secret_dir
    secret_dir="$(dirname "$PG_SECRET_FILE")"
    [ -d "$secret_dir" ] || mkdir -p "$secret_dir"
    # umask 兜底: 即便 install -m 失败, 文件也不会变成 0644。
    ( umask 077 && printf '%s' "$password" > "$PG_SECRET_FILE" )
    chmod 0600 "$PG_SECRET_FILE" 2>/dev/null ||
        sudo chmod 0600 "$PG_SECRET_FILE" 2>/dev/null || true
    # 权限校验：本文件仅属主可读，权限不符时后端启动器会读不到口令
    local _mode
    _mode="$(stat -c '%a' "$PG_SECRET_FILE" 2>/dev/null || stat -f '%Lp' "$PG_SECRET_FILE" 2>/dev/null || echo "")"
    if [ -z "$_mode" ] || [ "$((8#${_mode}))" -ne "$((8#600))" ]; then
        _err "密钥文件权限不符合预期: $PG_SECRET_FILE（期望 0600，实际 ${_mode:-无法获取}）"
        return 1
    fi
    _log "密钥文件已写入: $PG_SECRET_FILE (mode 0600)"
}

# 以 postgres 用户身份执行 psql（自动处理 root/sudo）
psql_as_postgres() {
    if _is_root; then
        runuser -u postgres -- psql -p "${PG_PORT}" "$@"
    else
        sudo -u postgres -- psql -p "${PG_PORT}" "$@"
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
        if psql_as_postgres -c "SELECT 1" >/dev/null 2>&1; then
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
    user_exists=$(printf "SELECT 1 FROM pg_roles WHERE rolname = :'user';\n" | \
        psql_as_postgres -v "user=${PG_USER}" -tA 2>/dev/null || echo "")
    if [ "$user_exists" = "1" ]; then
        _info "用户已存在，更新密码..."
        psql_as_postgres -v ON_ERROR_STOP=1 -v "user=${PG_USER}" -v "password=${PG_PASSWORD}" <<'SQL'
SELECT format('ALTER USER %I WITH PASSWORD %L', :'user', :'password')
\gexec
SQL
    else
        psql_as_postgres -v ON_ERROR_STOP=1 -v "user=${PG_USER}" -v "password=${PG_PASSWORD}" <<'SQL'
SELECT format('CREATE USER %I WITH PASSWORD %L', :'user', :'password')
\gexec
SQL
    fi
    _log "用户 ${PG_USER} 就绪"

    local db_exists
    db_exists=$(printf "SELECT 1 FROM pg_database WHERE datname = :'database';\n" | \
        psql_as_postgres -v "database=${PG_DATABASE}" -tA 2>/dev/null || echo "")
    if [ "$db_exists" = "1" ]; then
        _log "数据库 ${PG_DATABASE} 已存在"
    else
        psql_as_postgres -v ON_ERROR_STOP=1 -v "database=${PG_DATABASE}" -v "user=${PG_USER}" <<'SQL'
SELECT format('CREATE DATABASE %I OWNER %I', :'database', :'user')
\gexec
SQL
        _log "数据库 ${PG_DATABASE} 已创建"
    fi
}

# ──────────────────── RPM 部署 ────────────────────

deploy_rpm() {
    _step_header "PostgreSQL 部署 (RPM)"

    _require_root || return 1
    _load_pg_credentials || { _err "无法加载 PG 凭据（/etc/witty-ub/deploy.conf）"; return 1; }
    ensure_pg_password

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
        local SUDO_CMD=(); _is_root || SUDO_CMD=(sudo)
        for pkg in "${PG_PKG_CANDIDATES[@]}"; do
            _info "尝试安装 $pkg ..."
            if "${SUDO_CMD[@]}" yum install -y --allowerasing "$pkg" 2>&1 | tail -3; then
                INSTALLED_PKG="$pkg"
                break
            fi
        done
        [ -n "$INSTALLED_PKG" ] || { _err "安装 PostgreSQL 失败，请手动: sudo yum install -y postgresql15-server"; return 1; }
    fi

    command -v psql >/dev/null 2>&1 || {
        local SUDO_CMD=(); _is_root || SUDO_CMD=(sudo)
        "${SUDO_CMD[@]}" yum install -y --allowerasing postgresql >/dev/null 2>&1 || true
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
    _load_pg_credentials || { _err "无法加载 PG 凭据（/etc/witty-ub/deploy.conf）"; return 1; }
    ensure_pg_password

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
        local SUDO_CMD=(); _is_root || SUDO_CMD=(sudo)
        _info "安装 postgresql ..."
        "${SUDO_CMD[@]}" apt-get update -y >/dev/null 2>&1 || true
        "${SUDO_CMD[@]}" apt-get install -y postgresql postgresql-client || { _err "安装失败"; return 1; }
        INSTALLED_PKG="postgresql"
    fi

    command -v psql >/dev/null 2>&1 || {
        local SUDO_CMD=(); _is_root || SUDO_CMD=(sudo)
        "${SUDO_CMD[@]}" apt-get install -y postgresql-client >/dev/null 2>&1 || true
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
    rpm) deploy_rpm ;;
    apt) deploy_apt ;;
    *)   _err "不支持的包管理器: $OS_ID"; exit 1 ;;
esac
