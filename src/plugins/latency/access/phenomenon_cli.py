# Copyright (c) Huawei Technologies Co., Ltd. 2023-2025. All rights reserved.
"""Operations CLI for the phenomenon index.

Usage:
    python -m latency.access.phenomenon_cli --init-kb
    python -m latency.access.phenomenon_cli --self-check
    python -m latency.access.phenomenon_cli --all
    python -m latency.access.phenomenon_cli --report-id <report_id>
    python -m latency.access.phenomenon_cli --case-id <case_id>
    python -m latency.access.phenomenon_cli --legacy-all
    python -m latency.access.phenomenon_cli --reconcile
"""
from __future__ import annotations

import argparse
import asyncio
import json
import logging

from latency.config import phenomenon as settings
from latency.config.config import Config
from latency.database.engine import PGManager
from latency.database.init import init_postgresql_database
from latency.services.phenomenon_index import PhenomenonIndexService
from latency.services.rag_client import RAGClient, RAGContractError, RAGError


async def _init_kb(name: str) -> dict:
    """Create the dedicated KB once, or validate the configured one."""
    client = RAGClient.from_env()
    configured = settings.rag_kb_id()
    if configured:
        kb = await client.get_kb(configured)
        kb_type = kb.get("meta_data_type") or kb.get("kb_type") or kb.get("type")
        if kb_type is not None and str(kb_type) != "document":
            raise RAGContractError(
                f"RAG_PHENOMENON_KB_ID is not a document knowledge base: {kb_type}"
            )
        return {"kb_id": configured, "created": False, "kb_type": kb_type}
    kb_id = await client.create_document_kb(name)
    return {
        "kb_id": kb_id,
        "created": True,
        "kb_type": "document",
        "env": f"RAG_PHENOMENON_KB_ID={kb_id}",
    }


async def _run(args: argparse.Namespace) -> dict:
    if args.init_kb:
        return await _init_kb(args.kb_name)
    if args.self_check:
        return {"passed": await PhenomenonIndexService.run_self_check()}
    config = Config().get_config()
    PGManager.initialize(
        config.db.pg_dsn_url(),
        pool_size=config.db.pg_pool_size,
        max_overflow=config.db.pg_max_overflow,
    )
    await init_postgresql_database()
    if args.reconcile:
        return await PhenomenonIndexService.reconcile()
    if args.all:
        return await PhenomenonIndexService.index_scope("all", force=args.force)
    if args.report_id:
        return await PhenomenonIndexService.index_scope(
            "report", report_id=args.report_id, force=args.force
        )
    if args.case_id:
        return await PhenomenonIndexService.index_scope(
            "case", case_id=args.case_id, force=args.force
        )
    if args.legacy_all:
        return await PhenomenonIndexService.index_scope(
            "legacy_all", force=args.force
        )
    raise SystemExit(
        "必须指定一个操作：--init-kb / --self-check / --all / --report-id / "
        "--case-id / --legacy-all / --reconcile"
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Phenomenon index operations")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--init-kb", action="store_true", help="create or validate the dedicated KB")
    group.add_argument("--self-check", action="store_true", help="run upload→parse→search→delete")
    group.add_argument("--all", action="store_true", help="rebuild all reports and confirmed cases")
    group.add_argument("--report-id", help="rebuild one report")
    group.add_argument("--case-id", help="rebuild one confirmed case")
    group.add_argument("--legacy-all", action="store_true", help="rebuild readable legacy cases")
    group.add_argument("--reconcile", action="store_true", help="run one reconciliation round")
    parser.add_argument("--force", action="store_true", help="ignore unchanged hashes")
    parser.add_argument(
        "--kb-name",
        default="witty-ub-phenomenon",
        help="name of the KB created when RAG_PHENOMENON_KB_ID is unset",
    )
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO)
    try:
        result = asyncio.run(_run(args))
    except RAGError as exc:
        raise SystemExit(f"RAG 操作失败：{exc}") from exc
    finally:
        asyncio.run(PGManager.close())
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
