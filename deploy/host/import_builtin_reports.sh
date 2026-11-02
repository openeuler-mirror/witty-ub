#!/bin/bash
# Copyright (c) Huawei Technologies Co., Ltd. 2023-2026. All rights reserved.
# witty-ub is licensed under the Mulan PSL v2.
#
# 源码/RPM 部署：同步并导入仓库内置的定界报告压缩包。
#
# 与容器入口同一套语义：仓库压缩包是只读来源，运行时目录里的副本才是生效版本；
# 压缩包哈希变化才替换并重新导入，未变化直接跳过。导入按需归档上一版本报告。
#
# 用法:
#   bash deploy/host/import_builtin_reports.sh          # 按需导入（默认）
#   bash deploy/host/import_builtin_reports.sh --force  # 忽略状态文件强制重新导入
#
# 环境变量:
#   WITTY_BUILTIN_REPORTS=0              禁用内置报告导入
#   WITTY_BUILTIN_REPORT_ARCHIVE=<path>  压缩包来源（默认仓库 data/builtin-reports/）
#   WITTY_BUILTIN_REPORT_DIR=<dir>       运行时目录（默认 .deploy-run/builtin-reports）
#   WITTY_BUILTIN_REPORT_OPERATOR=<name> 导入人（默认 builtin-reports）
#
# 需要后端 venv 与 PostgreSQL 口令；口令读取方式与 deploy/host/run_backend.sh 一致。

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$(dirname "$SCRIPT_DIR")")"
source "$SCRIPT_DIR/_lib.sh"

FORCE=0
[ "${1:-}" = "--force" ] && FORCE=1

if [ "${WITTY_BUILTIN_REPORTS:-1}" = "0" ]; then
    _info "WITTY_BUILTIN_REPORTS=0，跳过后端内置报告导入"
    exit 0
fi

# 报告正文根目录必须与后端一致，否则导入把 HTML 写到回落目录 /tmp/reports，
# 后端却在 /var/witty-ub/reports 里找，表现为"文档全都不见了"。
export WITTY_DIR="${WITTY_DIR:-/var/witty-ub}"
export WITTY_REPORT_DIR="${WITTY_REPORT_DIR:-$WITTY_DIR/reports}"

ARCHIVE="${WITTY_BUILTIN_REPORT_ARCHIVE:-$PROJECT_DIR/data/builtin-reports/builtin-diagnostic-reports.zip}"
RUN_DIR="${WITTY_BUILTIN_REPORT_DIR:-$PROJECT_DIR/.deploy-run/builtin-reports}"
OPERATOR="${WITTY_BUILTIN_REPORT_OPERATOR:-builtin-reports}"
PYTHON="$PROJECT_DIR/src/plugins/latency/.venv/bin/python"
LOG="$LOG_DIR/builtin_report_import.log"

if [ ! -f "$ARCHIVE" ]; then
    _warn "未找到内置报告压缩包: $ARCHIVE（跳过）"
    exit 0
fi
if [ ! -x "$PYTHON" ]; then
    _warn "后端 venv 不存在: $PYTHON（跳过内置报告导入，请先执行完整部署）"
    exit 0
fi

mkdir -p "$RUN_DIR" "$LOG_DIR"
ACTIVE="$RUN_DIR/reports.zip"
STATE="$RUN_DIR/import-state.json"
SOURCE_SUM="$(sha256sum "$ARCHIVE" | awk '{print $1}')"
ACTIVE_SUM=""
[ -f "$ACTIVE" ] && ACTIVE_SUM="$(sha256sum "$ACTIVE" | awk '{print $1}')"
if [ "$SOURCE_SUM" != "$ACTIVE_SUM" ]; then
    cp -f "$ARCHIVE" "$ACTIVE.tmp"
    mv -f "$ACTIVE.tmp" "$ACTIVE"
    _log "内置报告压缩包已更新 (${SOURCE_SUM:0:12})"
fi

# 口令来源与后端启动器一致：PG_PASSWORD > deploy/pg.passwd > /etc/witty-ub/pg.passwd。
if [ -z "${PG_PASSWORD:-}" ]; then
    for _file in "${PG_SECRET_FILE:-}" "$PROJECT_DIR/deploy/pg.passwd" "/etc/witty-ub/pg.passwd"; do
        [ -n "$_file" ] && [ -r "$_file" ] || continue
        PG_PASSWORD="$(tr -d '\r\n' <"$_file")"
        break
    done
fi
if [ -z "${PG_PASSWORD:-}" ]; then
    _err "未找到 PostgreSQL 口令，无法导入内置报告（见 deploy/host/run_backend.sh 的排查提示）"
    exit 1
fi
export PG_PASSWORD
export PYTHONPATH="$PROJECT_DIR/src/plugins${PYTHONPATH:+:$PYTHONPATH}"

ARGS=(--archive "$ACTIVE" --state "$STATE" --operator "$OPERATOR")
[ "$FORCE" -eq 1 ] && ARGS+=(--force)

_log "导入内置报告（后台执行，日志: $LOG）"
(
    set -euo pipefail
    exec "$PYTHON" -m latency.access.builtin_reports_cli "${ARGS[@]}"
) >>"$LOG" 2>&1 &
