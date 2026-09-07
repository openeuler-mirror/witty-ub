#!/bin/bash
# Copyright (c) Huawei Technologies Co., Ltd. 2023-2026. All rights reserved.
# 从受限密钥文件加载 PostgreSQL 密码并启动 FastAPI 后端。

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$(dirname "$SCRIPT_DIR")")"
PG_SECRET_FILE="${PG_SECRET_FILE:-$PROJECT_DIR/deploy/pg.passwd}"

if [ -z "${PG_PASSWORD:-}" ]; then
    if [ ! -r "$PG_SECRET_FILE" ]; then
        echo "[error] PostgreSQL 密钥文件不存在或不可读: $PG_SECRET_FILE" >&2
        exit 1
    fi
    PG_PASSWORD="$(tr -d '\r\n' <"$PG_SECRET_FILE")"
    if [ -z "$PG_PASSWORD" ]; then
        echo "[error] PostgreSQL 密钥文件为空: $PG_SECRET_FILE" >&2
        exit 1
    fi
    export PG_PASSWORD
fi

LATENCY_DIR="$PROJECT_DIR/src/plugins/latency"
exec "$LATENCY_DIR/.venv/bin/python" -u "$LATENCY_DIR/access/fastapi_server.py"
