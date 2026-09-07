#!/bin/bash
# Load the RPM-managed PostgreSQL secret only for the backend process.

set -euo pipefail

PG_SECRET_FILE="${PG_SECRET_FILE:-/etc/witty-ub/pg.passwd}"
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

exec /var/witty-ub/latency/.venv/bin/python \
    /var/witty-ub/latency/access/fastapi_server.py
