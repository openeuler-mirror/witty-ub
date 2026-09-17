#!/bin/bash
# Copyright (c) Huawei Technologies Co., Ltd. 2023-2026. All rights reserved.
# witty-ub is licensed under the Mulan PSL v2.
#
# 从密钥文件加载 PostgreSQL 密码并启动 FastAPI 后端。
#
# 口令来源优先级:
#   1. 环境变量 PG_PASSWORD
#   2. 密钥文件: $PG_SECRET_FILE > <项目>/deploy/pg.passwd > /etc/witty-ub/pg.passwd
#   3. deploy/deploy.conf 的 PG_PASSWORD (<CHANGE_ME> 与 witty-ub 视为未设置)

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$(dirname "$SCRIPT_DIR")")"
PG_CONF_FILE="$PROJECT_DIR/deploy/deploy.conf"
PG_SECRET_FILE="${PG_SECRET_FILE:-}"

_resolve_pg_password() {
    # 按 PG_SECRET_FILE、仓库内、系统级顺序取第一个可读密钥文件。
    local candidates=("$PG_SECRET_FILE" \
        "$PROJECT_DIR/deploy/pg.passwd" \
        "/etc/witty-ub/pg.passwd")
    local file
    for file in "${candidates[@]}"; do
        [ -n "$file" ] || continue
        [ -r "$file" ] || continue
        PG_SECRET_FILE="$file"
        tr -d '\r\n' <"$file"
        return 0
    done
    # 旧部署兼容: deploy.conf 里仍写着真实口令时兜底 (占位符除外)。
    if [ -r "$PG_CONF_FILE" ]; then
        local conf_password
        conf_password="$(grep -E '^PG_PASSWORD=' "$PG_CONF_FILE" 2>/dev/null | head -1 | cut -d= -f2 | tr -d '"' | tr -d '\r\n')"
        case "$conf_password" in
            ""|"<CHANGE_ME>"|"witty-ub") ;;
            *)
                PG_SECRET_FILE="$PG_CONF_FILE"
                printf '%s' "$conf_password"
                return 0
                ;;
        esac
    fi
    return 1
}

if [ -z "${PG_PASSWORD:-}" ]; then
    PG_PASSWORD="$(_resolve_pg_password || true)"
    if [ -z "$PG_PASSWORD" ]; then
        echo "[error] 未找到 PostgreSQL 口令, 后端无法连接数据库。" >&2
        echo "" >&2
        echo "        已查找的密钥文件:" >&2
        if [ -n "$PG_SECRET_FILE" ]; then
            echo "          - $PG_SECRET_FILE (\$PG_SECRET_FILE)" >&2
        fi
        echo "          - $PROJECT_DIR/deploy/pg.passwd" >&2
        echo "          - /etc/witty-ub/pg.passwd" >&2
        echo "          - $PG_CONF_FILE (PG_PASSWORD, 仅兼容旧部署)" >&2
        # 密钥属主为 root 时, 降权运行后端的用户读不到, 需要单独提示。
        candidate=""
        owner=""
        for candidate in "$PG_SECRET_FILE" "$PROJECT_DIR/deploy/pg.passwd" "/etc/witty-ub/pg.passwd"; do
            [ -n "$candidate" ] || continue
            [ -e "$candidate" ] && [ ! -r "$candidate" ] || continue
            owner="$(stat -c '%U:%G' "$candidate" 2>/dev/null || echo '?')"
            echo "" >&2
            echo "        注: $candidate 已存在但当前用户 ($(id -un)) 不可读 (属主 $owner)。" >&2
            echo "            修复: sudo chown \$(id -u):\$(id -g) $candidate" >&2
        done
        echo "" >&2
        echo "        选择一种方式提供口令:" >&2
        echo "        1) 已知 PG 口令时, 写入密钥文件 (推荐, 权限 0400):" >&2
        echo "             printf '%s' '<PG 口令>' | install -m 0400 /dev/stdin $PROJECT_DIR/deploy/pg.passwd" >&2
        echo "        2) 尚未初始化 PostgreSQL 时, 由部署脚本生成口令:" >&2
        echo "             bash $PROJECT_DIR/deploy/deploy_pg.sh --rpm   # 或 --apt" >&2
        echo "        3) 仅本次启动临时指定:" >&2
        echo "             PG_PASSWORD='<PG 口令>' bash $SCRIPT_DIR/run_backend.sh" >&2
        exit 1
    fi
    export PG_PASSWORD
fi

LATENCY_DIR="$PROJECT_DIR/src/plugins/latency"

# 直接执行或由 systemd 启动时都需要: import latency 包、定位 C++ 工具产物。
export PYTHONPATH="$PROJECT_DIR/src/plugins${PYTHONPATH:+:$PYTHONPATH}"
export WITTY_INSTALL_PATH="${WITTY_INSTALL_PATH:-$PROJECT_DIR/build/src}"

exec "$LATENCY_DIR/.venv/bin/python" -u "$LATENCY_DIR/access/fastapi_server.py"
