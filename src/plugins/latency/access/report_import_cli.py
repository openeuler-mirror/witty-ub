# Copyright (c) Huawei Technologies Co., Ltd. 2023-2025. All rights reserved.
"""CLI for importing verified historical diagnostic reports.

Usage:
    python -m latency.access.report_import_cli reports.zip \
        --operator <name> --declared-verified
    python -m latency.access.report_import_cli one.json \
        --operator <name> --declared-verified --keep-draft

Requires ``WITTY_REPORT_DIR`` (same as the backend) and a ``python3`` with
``jinja2`` for the report renderer; override with ``WITTY_REPORT_RENDER_PYTHON``
or ``WITTY_REPORT_RENDERER``.
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
from latency.services.report_import import (
    ImportOptions,
    ImportSourceError,
    import_reports,
)


async def _run(args: argparse.Namespace) -> dict:
    config = Config().get_config()
    PGManager.initialize(
        config.db.pg_dsn_url(),
        pool_size=config.db.pg_pool_size,
        max_overflow=config.db.pg_max_overflow,
    )
    await init_postgresql_database()
    result = await import_reports(
        Path(args.source).expanduser(),
        ImportOptions(
            operator=args.operator,
            declared_verified=args.declared_verified,
            build_cases=args.declared_verified and not args.no_cases,
            keep_draft=args.keep_draft,
            index=not args.no_index,
            allow_incomplete=not args.strict,
        ),
    )
    return {
        "batch_id": result.batch_id,
        "status": result.status,
        "imported_by": result.imported_by,
        "declared_verified": result.declared_verified,
        "file_count": result.file_count,
        "summary": result.summary,
        "degraded": result.degraded_summary(),
        "items": [item.as_dict() for item in result.items],
    }


async def _run_and_close(args: argparse.Namespace) -> dict:
    try:
        return await _run(args)
    finally:
        await PGManager.close()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Import verified historical diagnostic reports"
    )
    parser.add_argument("source", help="报告 JSON 或 zip 路径")
    parser.add_argument(
        "--operator", required=True, help="导入人；写入报告/案例确认记录"
    )
    parser.add_argument(
        "--declared-verified",
        action="store_true",
        help="声明该批报告已人工验证；报告确认并批量建案",
    )
    parser.add_argument(
        "--no-cases", action="store_true", help="只导入报告，不批量建案"
    )
    parser.add_argument(
        "--keep-draft", action="store_true", help="批量建案只生成草稿，不自动确认"
    )
    parser.add_argument(
        "--no-index", action="store_true", help="不触发报告卡片索引"
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="字段不全即拒绝：校验失败不渲染、缺摘要不建案。默认放行不完整数据，"
             "缺什么会写进案例的适用范围（scope_limits）",
    )
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO)
    try:
        result = asyncio.run(_run_and_close(args))
    except ImportSourceError as exc:
        raise SystemExit(f"导入源不可用：{exc}") from exc
    except ValueError as exc:
        raise SystemExit(str(exc)) from exc
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if result["status"] == "failed":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
