# Copyright (c) Huawei Technologies Co., Ltd. 2023-2025. All rights reserved.
"""CLI for importing the deployment-shipped built-in report archive.

Usage:
    python -m latency.access.builtin_reports_cli \
        --archive data/builtin-reports/builtin-diagnostic-reports.zip \
        --state /var/witty-ub/builtin-reports/import-state.json \
        --operator builtin-reports

The command is idempotent: unchanged archive content is skipped, and reports
from the previous archive that are absent now are superseded. Per-file failures
are reported but do not fail the command, so a partially valid archive still
loads its usable reports. Requires the same PostgreSQL settings as the backend.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import logging
from pathlib import Path

from latency.config.config import Config
from latency.database.engine import PGManager
from latency.database.init import init_postgresql_database
from latency.services.builtin_reports import sync_builtin_reports_locked


async def _run(args: argparse.Namespace) -> dict:
    config = Config().get_config()
    PGManager.initialize(
        config.db.pg_dsn_url(),
        pool_size=config.db.pg_pool_size,
        max_overflow=config.db.pg_max_overflow,
    )
    await init_postgresql_database()
    return await sync_builtin_reports_locked(
        Path(args.archive).expanduser(),
        Path(args.state).expanduser(),
        args.operator,
        force=args.force,
        supersede=not args.no_supersede,
    )


async def _run_and_close(args: argparse.Namespace) -> dict:
    try:
        return await _run(args)
    finally:
        await PGManager.close()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Import the built-in diagnostic report archive"
    )
    parser.add_argument("--archive", required=True, help="内置报告压缩包路径")
    parser.add_argument("--state", required=True, help="导入状态文件路径")
    parser.add_argument(
        "--operator", default="builtin-reports", help="导入人；写入报告/案例确认记录"
    )
    parser.add_argument(
        "--force", action="store_true", help="忽略状态文件中的哈希，强制重新导入"
    )
    parser.add_argument(
        "--no-supersede", action="store_true", help="保留上一版本报告与案例"
    )
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO)
    print(json.dumps(asyncio.run(_run_and_close(args)), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
