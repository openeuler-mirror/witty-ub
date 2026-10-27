# Copyright (c) Huawei Technologies Co., Ltd. 2023-2025. All rights reserved.
"""Persistence for historical report import batches and items.

Batch rows are audit records only: report files stay in the report volume and
the report index table keeps its existing role.
"""
from __future__ import annotations

import uuid
from typing import Any
from sqlalchemy import or_, select, update

from latency.common.local_time import local_now
from latency.database.engine import PGManager
from latency.database.models import DiagCaseLibrary, DiagnosticReportIndex, ReportImportBatch, ReportImportItem


class ReportImportPGManager:
    @staticmethod
    async def detach_historical_assets(report_id: str) -> None:
        """Correct old imported associations without changing the source document."""
        async with PGManager.session() as session:
            await session.execute(update(DiagnosticReportIndex).where(
                DiagnosticReportIndex.report_id == report_id,
                or_(DiagnosticReportIndex.kb_id.is_not(None), DiagnosticReportIndex.kb_name.is_not(None)),
            ).values(kb_id=None, kb_name=None))
            await session.execute(update(DiagCaseLibrary).where(
                DiagCaseLibrary.report_id == report_id,
                or_(DiagCaseLibrary.kb_id.is_not(None), DiagCaseLibrary.kb_name.is_not(None)),
            ).values(kb_id=None, kb_name=None, revision=DiagCaseLibrary.revision + 1, updated_at=local_now()))

    @staticmethod
    async def sources_for_reports(report_ids: list[str]) -> dict[str, dict[str, str]]:
        async with PGManager.session() as session:
            result = await session.execute(
                select(ReportImportItem.report_id, ReportImportBatch.source_name,
                       ReportImportBatch.imported_by)
                .join(ReportImportBatch, ReportImportBatch.batch_id == ReportImportItem.batch_id)
                .where(ReportImportItem.report_id.in_(report_ids),
                       ReportImportItem.status.in_(["imported", "duplicate"]))
                .order_by(ReportImportItem.created_at)
            )
            sources = {}
            for row in result.mappings():
                sources.setdefault(row["report_id"], {
                    "source_name": row["source_name"], "imported_by": row["imported_by"],
                })
            return sources

    @staticmethod
    async def reports_for_content(content_hash: str) -> list[str]:
        async with PGManager.session() as session:
            result = await session.execute(
                select(ReportImportItem.report_id).where(
                    ReportImportItem.content_hash == content_hash,
                    ReportImportItem.report_id.is_not(None),
                ).distinct()
            )
            return list(result.scalars())

    @staticmethod
    async def create_batch(
        *,
        batch_id: str,
        imported_by: str,
        source_name: str,
        file_count: int,
        declared_verified: bool,
        build_cases: bool,
    ) -> None:
        now = local_now()
        async with PGManager.session() as session:
            session.add(
                ReportImportBatch(
                    batch_id=batch_id,
                    imported_by=imported_by,
                    imported_at=now,
                    source_name=source_name,
                    file_count=file_count,
                    status="running",
                    declared_verified=declared_verified,
                    build_cases=build_cases,
                    summary_json={},
                    updated_at=now,
                )
            )

    @staticmethod
    async def finish_batch(
        batch_id: str,
        status: str,
        summary: dict[str, Any],
    ) -> None:
        async with PGManager.session() as session:
            batch = await session.get(ReportImportBatch, batch_id)
            if batch is None:
                return
            batch.status = status
            batch.summary_json = summary
            batch.updated_at = local_now()

    @staticmethod
    async def add_item(values: dict[str, Any]) -> None:
        async with PGManager.session() as session:
            session.add(
                ReportImportItem(
                    id=values.get("id") or uuid.uuid4().hex,
                    batch_id=values["batch_id"],
                    original_name=values["original_name"],
                    report_id=values.get("report_id"),
                    content_hash=values.get("content_hash"),
                    report_meta_id=values.get("report_meta_id"),
                    status=values["status"],
                    error=values.get("error"),
                    fault_count=int(values.get("fault_count") or 0),
                    eligible_case_count=int(values.get("eligible_case_count") or 0),
                    report_confirmed=bool(values.get("report_confirmed")),
                    case_result_json=values.get("case_result_json") or [],
                    created_at=local_now(),
                )
            )
