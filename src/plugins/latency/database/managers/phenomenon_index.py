# Copyright (c) Huawei Technologies Co., Ltd. 2023-2025. All rights reserved.
"""PostgreSQL manager for report metadata, phenomenon cards, cleanup and outbox.

Business state changes and local card updates stay in one short transaction.
Remote RAG calls are never made here; the service layer uses these primitives
and performs HTTP outside the transaction.
"""
from __future__ import annotations

import uuid
from collections.abc import AsyncIterator, Iterable
from contextlib import asynccontextmanager
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any

from latency.common.local_time import local_now
from latency.database.engine import PGManager
from latency.database.models import (
    DiagnosticReportIndex,
    IndexEventOutbox,
    PhenomenonIndex,
    RagDocCleanupTask,
)
from latency.ENUM.phenomenon import (
    BindingStatus,
    IndexEventStatus,
    PhenomenonIndexStatus,
    RagCleanupStatus,
)
from latency.services.report_phenomenon import PhenomenonDoc, sha256_hex
from sqlalchemy import and_, delete, func, or_, select, text, tuple_, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession


@asynccontextmanager
async def session_scope(session: AsyncSession | None = None) -> AsyncIterator[AsyncSession]:
    """Use the caller's transaction when provided; otherwise commit on exit."""
    if session is not None:
        yield session
        return
    async with PGManager.session() as current:
        yield current


def _now() -> datetime:
    return local_now()


def _new_token() -> str:
    return uuid.uuid4().hex


@dataclass(slots=True)
class UpsertResult:
    action: str
    queued: bool
    text_changed: bool
    fingerprint_changed: bool
    enabled: bool
    searchable: bool


@dataclass(slots=True)
class SwitchResult:
    status: str
    cleanup_pairs: list[tuple[str, str]]


class PhenomenonIndexPGManager:
    """CRUD and conditional state transitions for the phenomenon index."""

    # ---------------------------------------------------------------- report
    @staticmethod
    async def upsert_report_index(
        values: dict[str, Any], session: AsyncSession | None = None
    ) -> None:
        data = dict(values)
        data["updated_at"] = _now()
        async with session_scope(session) as current:
            stmt = insert(DiagnosticReportIndex).values(**data)
            update_cols = {key: value for key, value in data.items() if key != "report_id"}
            await current.execute(
                stmt.on_conflict_do_update(
                    index_elements=[DiagnosticReportIndex.report_id],
                    set_=update_cols,
                )
            )

    @staticmethod
    async def get_report_index(report_id: str) -> DiagnosticReportIndex | None:
        async with PGManager.session() as session:
            return await session.get(DiagnosticReportIndex, report_id)

    @staticmethod
    async def get_report_indexes(
        report_ids: Iterable[str],
    ) -> dict[str, DiagnosticReportIndex]:
        ids = list(dict.fromkeys(report_ids))
        if not ids:
            return {}
        async with PGManager.session() as session:
            rows = await session.execute(
                select(DiagnosticReportIndex).where(
                    DiagnosticReportIndex.report_id.in_(ids)
                )
            )
            return {row.report_id: row for row in rows.scalars().all()}

    @staticmethod
    async def set_report_available(
        report_id: str,
        available: bool,
        *,
        index_error: str | None = None,
        session: AsyncSession | None = None,
    ) -> None:
        async with session_scope(session) as current:
            await current.execute(
                update(DiagnosticReportIndex)
                .where(DiagnosticReportIndex.report_id == report_id)
                .values(
                    report_available=available,
                    index_error=index_error,
                    updated_at=_now(),
                )
            )

    @staticmethod
    async def update_report_status(
        report_id: str,
        status: str,
        *,
        index_error: str | None = None,
        indexed_at: datetime | None = None,
        session: AsyncSession | None = None,
    ) -> None:
        values: dict[str, Any] = {
            "index_status": status,
            "index_error": index_error,
            "updated_at": _now(),
        }
        if indexed_at is not None:
            values["indexed_at"] = indexed_at
        async with session_scope(session) as current:
            await current.execute(
                update(DiagnosticReportIndex)
                .where(DiagnosticReportIndex.report_id == report_id)
                .values(**values)
            )

    @staticmethod
    async def card_status_counts(report_id: str) -> dict[str, int]:
        """Count only cards that still carry the report's current facts."""
        async with PGManager.session() as session:
            rows = await session.execute(
                select(PhenomenonIndex.index_status, func.count())
                .where(
                    PhenomenonIndex.report_id == report_id,
                    PhenomenonIndex.enabled.is_(True),
                )
                .group_by(PhenomenonIndex.index_status)
            )
            return {status: int(count) for status, count in rows.all()}

    @staticmethod
    async def card_status_counts_for_reports(
        report_ids: Iterable[str],
    ) -> dict[str, dict[str, int]]:
        ids = list(dict.fromkeys(report_ids))
        if not ids:
            return {}
        async with PGManager.session() as session:
            rows = await session.execute(
                select(
                    PhenomenonIndex.report_id,
                    PhenomenonIndex.index_status,
                    func.count(),
                )
                .where(
                    PhenomenonIndex.report_id.in_(ids),
                    PhenomenonIndex.enabled.is_(True),
                )
                .group_by(PhenomenonIndex.report_id, PhenomenonIndex.index_status)
            )
            result: dict[str, dict[str, int]] = {}
            for report_id, status, count in rows.all():
                result.setdefault(report_id, {})[status] = int(count)
            return result

    # ---------------------------------------------------------------- cards
    @staticmethod
    async def get_card(doc_id: str) -> PhenomenonIndex | None:
        async with PGManager.session() as session:
            return await session.get(PhenomenonIndex, doc_id)

    @staticmethod
    async def get_cards_by_report(report_id: str) -> list[PhenomenonIndex]:
        async with PGManager.session() as session:
            rows = await session.execute(
                select(PhenomenonIndex).where(PhenomenonIndex.report_id == report_id)
            )
            return list(rows.scalars().all())

    @staticmethod
    async def get_cards_by_case(case_id: str) -> list[PhenomenonIndex]:
        async with PGManager.session() as session:
            rows = await session.execute(
                select(PhenomenonIndex).where(PhenomenonIndex.case_id == case_id)
            )
            return list(rows.scalars().all())

    @staticmethod
    async def list_enabled_legacy_ids() -> set[str]:
        async with PGManager.session() as session:
            rows = await session.execute(
                select(PhenomenonIndex.legacy_case_id)
                .where(
                    PhenomenonIndex.enabled.is_(True),
                    PhenomenonIndex.legacy_case_id.is_not(None),
                )
                .distinct()
            )
            return {row[0] for row in rows.all()}

    @staticmethod
    async def get_cards_by_legacy(legacy_case_id: str) -> list[PhenomenonIndex]:
        async with PGManager.session() as session:
            rows = await session.execute(
                select(PhenomenonIndex).where(
                    PhenomenonIndex.legacy_case_id == legacy_case_id
                )
            )
            return list(rows.scalars().all())

    @staticmethod
    async def get_cards_by_rag_docs(
        pairs: Iterable[tuple[str, str]],
    ) -> list[PhenomenonIndex]:
        unique = list(dict.fromkeys(pairs))
        if not unique:
            return []
        async with PGManager.session() as session:
            rows = await session.execute(
                select(PhenomenonIndex).where(
                    tuple_(
                        PhenomenonIndex.rag_kb_id, PhenomenonIndex.rag_doc_id
                    ).in_(unique)
                )
            )
            return list(rows.scalars().all())

    @staticmethod
    async def get_card_by_rag_doc(kb_id: str, rag_doc_id: str) -> PhenomenonIndex | None:
        async with PGManager.session() as session:
            row = await session.execute(
                select(PhenomenonIndex).where(
                    PhenomenonIndex.rag_kb_id == kb_id,
                    PhenomenonIndex.rag_doc_id == rag_doc_id,
                )
            )
            return row.scalars().first()

    @staticmethod
    def _apply_doc(row: PhenomenonIndex, doc: PhenomenonDoc) -> None:
        row.kind = doc.kind
        row.content_source = doc.content_source
        row.report_id = doc.report_id
        row.source_fault_id = doc.source_fault_id
        row.source_fault_hash = doc.source_fault_hash
        row.case_id = doc.case_id
        row.case_no = doc.case_no
        row.legacy_case_id = doc.legacy_case_id
        row.title = doc.title
        row.symptom = doc.symptom
        row.root_cause_summary = doc.root_cause_summary
        row.log_type = doc.log_type
        row.operation = doc.operation
        row.fault_type = doc.fault_type
        row.status_codes = doc.status_codes
        row.failure_mode_ids = doc.failure_mode_ids
        row.verification = doc.verification
        row.binding_status = doc.binding_status
        row.text = doc.text
        row.content_hash = doc.content_hash

    @staticmethod
    async def upsert_expected(
        doc: PhenomenonDoc,
        *,
        force: bool = False,
        enabled: bool = True,
        session: AsyncSession | None = None,
    ) -> UpsertResult:
        """Save the desired version and decide whether a publish is needed."""
        now = _now()
        async with session_scope(session) as current:
            row = (
                await current.execute(
                    select(PhenomenonIndex)
                    .where(PhenomenonIndex.doc_id == doc.doc_id)
                    .with_for_update()
                )
            ).scalars().first()
            if row is None:
                current.add(
                    PhenomenonIndex(
                        doc_id=doc.doc_id,
                        kind=doc.kind,
                        content_source=doc.content_source,
                        report_id=doc.report_id,
                        source_fault_id=doc.source_fault_id,
                        source_fault_hash=doc.source_fault_hash,
                        case_id=doc.case_id,
                        case_no=doc.case_no,
                        legacy_case_id=doc.legacy_case_id,
                        title=doc.title,
                        symptom=doc.symptom,
                        root_cause_summary=doc.root_cause_summary,
                        log_type=doc.log_type,
                        operation=doc.operation,
                        fault_type=doc.fault_type,
                        status_codes=doc.status_codes,
                        failure_mode_ids=doc.failure_mode_ids,
                        verification=doc.verification,
                        binding_status=doc.binding_status,
                        text=doc.text,
                        content_hash=doc.content_hash,
                        enabled=enabled,
                        searchable=False,
                        index_status=PhenomenonIndexStatus.PENDING.value,
                        retry_count=0,
                        next_retry_at=now,
                        created_at=now,
                        updated_at=now,
                    )
                )
                return UpsertResult(
                    action="created",
                    queued=True,
                    text_changed=True,
                    fingerprint_changed=True,
                    enabled=enabled,
                    searchable=False,
                )

            text_changed = row.content_hash != doc.content_hash
            fingerprint_changed = row.source_fault_hash != doc.source_fault_hash
            was_disabled = not row.enabled
            PhenomenonIndexPGManager._apply_doc(row, doc)
            row.enabled = enabled
            row.updated_at = now

            queued = text_changed or fingerprint_changed or force or was_disabled
            if fingerprint_changed:
                row.searchable = False
            if force:
                # Force must re-upload even when the hashes are unchanged.
                row.indexed_content_hash = None
            if queued:
                row.index_status = (
                    PhenomenonIndexStatus.STALE.value
                    if row.published_text
                    else PhenomenonIndexStatus.PENDING.value
                )
                row.next_retry_at = now
                row.retry_count = 0
                row.index_error = None
            return UpsertResult(
                action="queued" if queued else "skipped",
                queued=queued,
                text_changed=text_changed,
                fingerprint_changed=fingerprint_changed,
                enabled=enabled,
                searchable=bool(row.searchable),
            )

    @staticmethod
    async def touch_card_metadata(
        doc_id: str,
        *,
        case_id: str | None,
        case_no: str | None,
        verification: str,
        binding_status: str,
        content_source: str | None = None,
        text: str | None = None,
        title: str | None = None,
        symptom: str | None = None,
        content_hash: str | None = None,
        source_fault_hash: str | None = None,
        enabled: bool | None = None,
        session: AsyncSession | None = None,
    ) -> bool:
        """Update pointers / labels; only queue when the text actually changes."""
        now = _now()
        async with session_scope(session) as current:
            row = (
                await current.execute(
                    select(PhenomenonIndex)
                    .where(PhenomenonIndex.doc_id == doc_id)
                    .with_for_update()
                )
            ).scalars().first()
            if row is None:
                return False
            text_changed = (
                content_hash is not None and row.content_hash != content_hash
            )
            row.case_id = case_id
            row.case_no = case_no
            row.verification = verification
            row.binding_status = binding_status
            if content_source is not None:
                row.content_source = content_source
            if text is not None:
                row.text = text
            if title is not None:
                row.title = title
            if symptom is not None:
                row.symptom = symptom
            if content_hash is not None:
                row.content_hash = content_hash
            if source_fault_hash is not None:
                if row.source_fault_hash != source_fault_hash:
                    row.source_fault_hash = source_fault_hash
                    row.searchable = False
            if enabled is not None:
                row.enabled = enabled
            if text_changed:
                row.index_status = (
                    PhenomenonIndexStatus.STALE.value
                    if row.published_text
                    else PhenomenonIndexStatus.PENDING.value
                )
                row.next_retry_at = now
                row.retry_count = 0
            row.updated_at = now
            return text_changed

    @staticmethod
    async def disable_card(
        doc_id: str,
        *,
        reason: str | None = None,
        cleanup_reason: str = "expired",
        session: AsyncSession | None = None,
    ) -> list[tuple[str, str]]:
        """Disable a card, release both document pairs and enqueue cleanup."""
        now = _now()
        async with session_scope(session) as current:
            row = (
                await current.execute(
                    select(PhenomenonIndex)
                    .where(PhenomenonIndex.doc_id == doc_id)
                    .with_for_update()
                )
            ).scalars().first()
            if row is None:
                return []
            pairs = [
                (row.rag_kb_id, row.rag_doc_id),
                (row.pending_rag_kb_id, row.pending_rag_doc_id),
            ]
            row.enabled = False
            row.searchable = False
            row.lease_owner = None
            row.lease_token = None
            row.lease_expires_at = None
            row.pending_rag_kb_id = None
            row.pending_rag_doc_id = None
            row.pending_content_hash = None
            row.pending_source_fault_hash = None
            row.rag_kb_id = None
            row.rag_doc_id = None
            row.index_error = reason
            row.updated_at = now
            released: list[tuple[str, str]] = []
            for kb_id, rag_doc_id in pairs:
                if kb_id and rag_doc_id:
                    await PhenomenonIndexPGManager._enqueue_cleanup(
                        current, kb_id, rag_doc_id, cleanup_reason, row.doc_id
                    )
                    released.append((kb_id, rag_doc_id))
            if not released:
                # Nothing was published, so no remote deletion is pending.
                row.index_status = PhenomenonIndexStatus.DELETED.value
            return released

    @staticmethod
    async def remove_case_pointer(
        doc_id: str,
        *,
        fallback_verification: str,
        session: AsyncSession | None = None,
    ) -> bool:
        now = _now()
        async with session_scope(session) as current:
            row = (
                await current.execute(
                    select(PhenomenonIndex)
                    .where(PhenomenonIndex.doc_id == doc_id)
                    .with_for_update()
                )
            ).scalars().first()
            if row is None:
                return False
            row.case_id = None
            row.case_no = None
            row.verification = fallback_verification
            row.binding_status = BindingStatus.NONE.value
            row.updated_at = now
            return True

