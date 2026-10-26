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

    # ---------------------------------------------------------------- metrics
    @staticmethod
    async def report_status_counts() -> dict[str, int]:
        """Report index status distribution for the ops snapshot."""
        async with PGManager.session() as session:
            rows = await session.execute(
                select(DiagnosticReportIndex.index_status, func.count()).group_by(
                    DiagnosticReportIndex.index_status
                )
            )
            return {str(status): int(count) for status, count in rows.all()}

    @staticmethod
    async def card_status_counts_all() -> dict[str, int]:
        """Enabled card index status distribution across every report."""
        async with PGManager.session() as session:
            rows = await session.execute(
                select(PhenomenonIndex.index_status, func.count())
                .where(PhenomenonIndex.enabled.is_(True))
                .group_by(PhenomenonIndex.index_status)
            )
            return {str(status): int(count) for status, count in rows.all()}

    @staticmethod
    async def searchable_card_count() -> int:
        async with PGManager.session() as session:
            return int(
                await session.scalar(
                    select(func.count()).select_from(PhenomenonIndex).where(
                        PhenomenonIndex.enabled.is_(True),
                        PhenomenonIndex.searchable.is_(True),
                    )
                )
                or 0
            )

    @staticmethod
    async def cleanup_backlog() -> tuple[int, datetime | None]:
        """Active cleanup tasks and the oldest creation time."""
        active = (
            RagCleanupStatus.OBSERVING.value,
            RagCleanupStatus.PENDING.value,
            RagCleanupStatus.DELETING.value,
        )
        async with PGManager.session() as session:
            row = (
                await session.execute(
                    select(func.count(), func.min(RagDocCleanupTask.created_at)).where(
                        RagDocCleanupTask.status.in_(active)
                    )
                )
            ).one()
            return int(row[0] or 0), row[1]

    @staticmethod
    async def event_backlog() -> tuple[int, datetime | None]:
        """Unfinished outbox events and the oldest creation time."""
        active = (
            IndexEventStatus.PENDING.value,
            IndexEventStatus.PROCESSING.value,
            IndexEventStatus.FAILED.value,
        )
        async with PGManager.session() as session:
            row = (
                await session.execute(
                    select(func.count(), func.min(IndexEventOutbox.created_at)).where(
                        IndexEventOutbox.status.in_(active)
                    )
                )
            ).one()
            return int(row[0] or 0), row[1]

    @staticmethod
    async def stuck_parsing_count(ttl_minutes: int = 30) -> int:
        cutoff = _now() - timedelta(minutes=ttl_minutes)
        async with PGManager.session() as session:
            return int(
                await session.scalar(
                    select(func.count()).select_from(PhenomenonIndex).where(
                        PhenomenonIndex.index_status
                        == PhenomenonIndexStatus.PARSING.value,
                        PhenomenonIndex.updated_at < cutoff,
                    )
                )
                or 0
            )

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

    # ---------------------------------------------------------------- leases
    @staticmethod
    async def claim_due_cards(
        owner: str, limit: int, lease_seconds: int
    ) -> list[PhenomenonIndex]:
        now = _now()
        deadline = now + timedelta(seconds=lease_seconds)
        due = or_(
            PhenomenonIndex.index_status.in_(
                [
                    PhenomenonIndexStatus.PENDING.value,
                    PhenomenonIndexStatus.STALE.value,
                ]
            ),
            and_(
                PhenomenonIndex.index_status == PhenomenonIndexStatus.FAILED.value,
                PhenomenonIndex.next_retry_at.is_not(None),
            ),
        )
        async with PGManager.session() as session:
            rows = await session.execute(
                select(PhenomenonIndex)
                .where(
                    PhenomenonIndex.enabled.is_(True),
                    due,
                    or_(
                        PhenomenonIndex.next_retry_at.is_(None),
                        PhenomenonIndex.next_retry_at <= now,
                    ),
                    or_(
                        PhenomenonIndex.lease_expires_at.is_(None),
                        PhenomenonIndex.lease_expires_at < now,
                    ),
                )
                .order_by(
                    PhenomenonIndex.next_retry_at.asc().nullsfirst(),
                    PhenomenonIndex.updated_at.asc(),
                )
                .limit(limit)
                .with_for_update(skip_locked=True)
            )
            claimed = list(rows.scalars().all())
            for row in claimed:
                # A previous owner's candidate lost its lease; release the
                # reference so the leaked document can be cleaned up.
                pair = (row.pending_rag_kb_id, row.pending_rag_doc_id)
                if pair[0] and pair[1] and pair != (row.rag_kb_id, row.rag_doc_id):
                    await PhenomenonIndexPGManager._enqueue_cleanup(
                        session, pair[0], pair[1], "expired", row.doc_id
                    )
                row.pending_rag_kb_id = None
                row.pending_rag_doc_id = None
                row.pending_content_hash = None
                row.pending_source_fault_hash = None
                row.lease_owner = owner
                row.lease_token = _new_token()
                row.lease_expires_at = deadline
                row.updated_at = now
            return claimed

    @staticmethod
    async def renew_lease(
        doc_id: str, owner: str, token: str, lease_seconds: int
    ) -> bool:
        now = _now()
        async with PGManager.session() as session:
            result = await session.execute(
                update(PhenomenonIndex)
                .where(
                    PhenomenonIndex.doc_id == doc_id,
                    PhenomenonIndex.lease_owner == owner,
                    PhenomenonIndex.lease_token == token,
                )
                .values(
                    lease_expires_at=now + timedelta(seconds=lease_seconds),
                    updated_at=now,
                )
            )
            return bool(result.rowcount)

    @staticmethod
    async def _try_doc_lock(
        session: AsyncSession, kb_id: str, rag_doc_id: str
    ) -> bool:
        return bool(
            await session.scalar(
                text(
                    "SELECT pg_try_advisory_xact_lock("
                    "hashtext(:kb_id), hashtext(:rag_doc_id))"
                ),
                {"kb_id": kb_id, "rag_doc_id": rag_doc_id},
            )
        )

    @staticmethod
    async def register_pending_candidate(
        doc_id: str,
        owner: str,
        token: str,
        kb_id: str,
        rag_doc_id: str,
        target_hash: str,
        target_source_hash: str | None,
    ) -> bool:
        now = _now()
        async with PGManager.session() as session:
            if not await PhenomenonIndexPGManager._try_doc_lock(
                session, kb_id, rag_doc_id
            ):
                return False
            row = (
                await session.execute(
                    select(PhenomenonIndex)
                    .where(PhenomenonIndex.doc_id == doc_id)
                    .with_for_update()
                )
            ).scalars().first()
            if row is None or not row.enabled:
                return False
            if (
                row.lease_owner != owner
                or row.lease_token != token
                or row.lease_expires_at is None
                or row.lease_expires_at < now
            ):
                return False
            if row.content_hash != target_hash:
                return False
            if row.source_fault_hash != target_source_hash:
                return False
            conflict = await session.scalar(
                select(func.count()).select_from(RagDocCleanupTask).where(
                    RagDocCleanupTask.rag_kb_id == kb_id,
                    RagDocCleanupTask.rag_doc_id == rag_doc_id,
                    RagDocCleanupTask.status.in_(
                        [RagCleanupStatus.DELETING.value, RagCleanupStatus.DONE.value]
                    ),
                )
            )
            if conflict:
                return False
            # A document that is about to be referenced must not be deleted later.
            await session.execute(
                delete(RagDocCleanupTask).where(
                    RagDocCleanupTask.rag_kb_id == kb_id,
                    RagDocCleanupTask.rag_doc_id == rag_doc_id,
                    RagDocCleanupTask.status.in_(
                        [RagCleanupStatus.OBSERVING.value, RagCleanupStatus.PENDING.value]
                    ),
                )
            )
            row.pending_rag_kb_id = kb_id
            row.pending_rag_doc_id = rag_doc_id
            # The candidate was built from this exact version; publishing must
            # never fall back to a later desired version.
            row.pending_content_hash = target_hash
            row.pending_source_fault_hash = target_source_hash
            row.updated_at = now
            return True

    @staticmethod
    async def switch_published(
        doc_id: str,
        owner: str,
        token: str,
        kb_id: str,
        rag_doc_id: str,
        target_hash: str,
        target_source_hash: str | None,
    ) -> SwitchResult:
        now = _now()
        async with PGManager.session() as session:
            if not await PhenomenonIndexPGManager._try_doc_lock(
                session, kb_id, rag_doc_id
            ):
                return SwitchResult(status="doc_locked", cleanup_pairs=[])
            row = (
                await session.execute(
                    select(PhenomenonIndex)
                    .where(PhenomenonIndex.doc_id == doc_id)
                    .with_for_update()
                )
            ).scalars().first()
            if row is None:
                return SwitchResult(status="not_found", cleanup_pairs=[])
            if not row.enabled:
                return SwitchResult(status="disabled", cleanup_pairs=[])
            if (
                row.lease_owner != owner
                or row.lease_token != token
                or row.lease_expires_at is None
                or row.lease_expires_at < now
            ):
                return SwitchResult(status="lost_lease", cleanup_pairs=[])
            if row.content_hash != target_hash or row.source_fault_hash != target_source_hash:
                return SwitchResult(status="version_changed", cleanup_pairs=[])
            if (
                row.pending_rag_kb_id != kb_id
                or row.pending_rag_doc_id != rag_doc_id
            ):
                return SwitchResult(status="candidate_mismatch", cleanup_pairs=[])
            if (
                row.pending_content_hash != target_hash
                or row.pending_source_fault_hash != target_source_hash
            ):
                # The uploaded candidate belongs to an older version.
                return SwitchResult(status="candidate_version_mismatch", cleanup_pairs=[])
            conflict = await session.scalar(
                select(func.count()).select_from(RagDocCleanupTask).where(
                    RagDocCleanupTask.rag_kb_id == kb_id,
                    RagDocCleanupTask.rag_doc_id == rag_doc_id,
                    RagDocCleanupTask.status.in_(
                        [RagCleanupStatus.DELETING.value, RagCleanupStatus.DONE.value]
                    ),
                )
            )
            if conflict:
                return SwitchResult(status="cleanup_conflict", cleanup_pairs=[])

            cleanup_pairs: list[tuple[str, str]] = []
            old_pair = (row.rag_kb_id, row.rag_doc_id)
            if old_pair[0] and old_pair[1] and old_pair != (kb_id, rag_doc_id):
                await PhenomenonIndexPGManager._enqueue_cleanup(
                    session, old_pair[0], old_pair[1], "replaced", row.doc_id
                )
                cleanup_pairs.append(old_pair)

            row.rag_kb_id = kb_id
            row.rag_doc_id = rag_doc_id
            row.indexed_content_hash = target_hash
            row.published_title = row.title
            row.published_symptom = row.symptom
            row.published_text = row.text
            row.published_source_fault_hash = row.source_fault_hash
            row.searchable = True
            row.index_status = PhenomenonIndexStatus.INDEXED.value
            row.indexed_at = now
            row.index_error = None
            row.next_retry_at = None
            row.retry_count = 0
            row.pending_rag_kb_id = None
            row.pending_rag_doc_id = None
            row.pending_content_hash = None
            row.pending_source_fault_hash = None
            row.lease_owner = None
            row.lease_token = None
            row.lease_expires_at = None
            row.updated_at = now
            return SwitchResult(status="switched", cleanup_pairs=cleanup_pairs)

    @staticmethod
    async def metadata_publish(
        doc_id: str,
        owner: str,
        token: str,
        kb_id: str,
        target_hash: str,
        target_source_hash: str | None,
    ) -> str:
        """Reuse the existing vector when only metadata changed."""
        now = _now()
        async with PGManager.session() as session:
            row = (
                await session.execute(
                    select(PhenomenonIndex)
                    .where(PhenomenonIndex.doc_id == doc_id)
                    .with_for_update()
                )
            ).scalars().first()
            if row is None:
                return "not_found"
            if not row.enabled:
                return "disabled"
            if (
                row.lease_owner != owner
                or row.lease_token != token
                or row.lease_expires_at is None
                or row.lease_expires_at < now
            ):
                return "lost_lease"
            if row.content_hash != target_hash or row.source_fault_hash != target_source_hash:
                return "version_changed"
            if row.pending_rag_doc_id is not None:
                return "pending_candidate"
            if not row.rag_kb_id or not row.rag_doc_id:
                return "mapping_missing"
            if row.rag_kb_id != kb_id:
                # A different KB target means a real re-upload is required.
                return "kb_mismatch"
            if not row.published_text or not row.published_title or row.published_symptom is None:
                return "snapshot_incomplete"
            if sha256_hex(row.published_text) != row.indexed_content_hash:
                return "snapshot_hash_mismatch"
            if row.indexed_content_hash != target_hash:
                return "content_hash_mismatch"
            if not await PhenomenonIndexPGManager._try_doc_lock(
                session, row.rag_kb_id, row.rag_doc_id
            ):
                return "doc_locked"
            conflict = await session.scalar(
                select(func.count()).select_from(RagDocCleanupTask).where(
                    RagDocCleanupTask.rag_kb_id == row.rag_kb_id,
                    RagDocCleanupTask.rag_doc_id == row.rag_doc_id,
                    RagDocCleanupTask.status.in_(
                        [RagCleanupStatus.DELETING.value, RagCleanupStatus.DONE.value]
                    ),
                )
            )
            if conflict:
                return "cleanup_conflict"

            row.published_title = row.title
            row.published_symptom = row.symptom
            row.published_text = row.text
            row.published_source_fault_hash = row.source_fault_hash
            row.searchable = True
            row.index_status = PhenomenonIndexStatus.INDEXED.value
            row.indexed_at = now
            row.index_error = None
            row.next_retry_at = None
            row.retry_count = 0
            row.lease_owner = None
            row.lease_token = None
            row.lease_expires_at = None
            row.updated_at = now
            return "published"

    @staticmethod
    async def mark_parsing(
        doc_id: str, owner: str, token: str, kb_id: str, rag_doc_id: str
    ) -> bool:
        now = _now()
        async with PGManager.session() as session:
            row = (
                await session.execute(
                    select(PhenomenonIndex)
                    .where(PhenomenonIndex.doc_id == doc_id)
                    .with_for_update()
                )
            ).scalars().first()
            if row is None or not row.enabled:
                return False
            if (
                row.lease_owner != owner
                or row.lease_token != token
                or row.lease_expires_at is None
                or row.lease_expires_at < now
            ):
                return False
            if (
                row.pending_rag_kb_id != kb_id
                or row.pending_rag_doc_id != rag_doc_id
            ):
                return False
            if (
                row.pending_content_hash is None
                or row.pending_content_hash != row.content_hash
                or row.pending_source_fault_hash != row.source_fault_hash
            ):
                # The desired version moved on after this candidate was built.
                return False
            row.index_status = PhenomenonIndexStatus.PARSING.value
            # Repurposed as the parse deadline; switched/cleared on completion.
            row.next_retry_at = now + timedelta(minutes=30)
            row.updated_at = now
            return True

    @staticmethod
    async def claim_parsing_cards(
        owner: str, limit: int, lease_seconds: int
    ) -> list[PhenomenonIndex]:
        now = _now()
        deadline = now + timedelta(seconds=lease_seconds)
        async with PGManager.session() as session:
            rows = await session.execute(
                select(PhenomenonIndex)
                .where(
                    PhenomenonIndex.enabled.is_(True),
                    PhenomenonIndex.index_status == PhenomenonIndexStatus.PARSING.value,
                    PhenomenonIndex.pending_rag_doc_id.is_not(None),
                    or_(
                        PhenomenonIndex.lease_expires_at.is_(None),
                        PhenomenonIndex.lease_expires_at < now,
                    ),
                )
                .order_by(PhenomenonIndex.updated_at.asc())
                .limit(limit)
                .with_for_update(skip_locked=True)
            )
            claimed = list(rows.scalars().all())
            for row in claimed:
                row.lease_owner = owner
                row.lease_token = _new_token()
                row.lease_expires_at = deadline
                row.updated_at = now
            return claimed

    @staticmethod
    async def withdraw_candidate(
        doc_id: str,
        owner: str,
        token: str,
        *,
        reason: str = "expired",
    ) -> tuple[str, str] | None:
        """Release this task's pending pair and persist its cleanup."""
        async with PGManager.session() as session:
            row = (
                await session.execute(
                    select(PhenomenonIndex)
                    .where(PhenomenonIndex.doc_id == doc_id)
                    .with_for_update()
                )
            ).scalars().first()
            if row is None:
                return None
            pair = (row.pending_rag_kb_id, row.pending_rag_doc_id)
            if not pair[0] or not pair[1]:
                return None
            if row.lease_owner != owner or row.lease_token != token:
                # A stale worker may still submit its own upload for cleanup;
                # the cleaner re-checks references before deleting.
                return pair
            row.pending_rag_kb_id = None
            row.pending_rag_doc_id = None
            row.pending_content_hash = None
            row.pending_source_fault_hash = None
            row.updated_at = _now()
            if pair != (row.rag_kb_id, row.rag_doc_id):
                await PhenomenonIndexPGManager._enqueue_cleanup(
                    session, pair[0], pair[1], reason, row.doc_id
                )
            return pair

    @staticmethod
    async def record_publish_failure(
        doc_id: str,
        owner: str,
        token: str,
        *,
        error: str,
        next_retry_at: datetime | None,
        terminal: bool,
    ) -> int:
        now = _now()
        async with PGManager.session() as session:
            result = await session.execute(
                update(PhenomenonIndex)
                .where(
                    PhenomenonIndex.doc_id == doc_id,
                    PhenomenonIndex.lease_owner == owner,
                    PhenomenonIndex.lease_token == token,
                    PhenomenonIndex.lease_expires_at.is_not(None),
                    PhenomenonIndex.lease_expires_at >= now,
                )
                .values(
                    retry_count=PhenomenonIndex.retry_count + 1,
                    index_error=error,
                    next_retry_at=next_retry_at,
                    index_status=(
                        PhenomenonIndexStatus.FAILED.value
                        if terminal
                        else PhenomenonIndexStatus.STALE.value
                    ),
                    pending_rag_kb_id=None,
                    pending_rag_doc_id=None,
                    pending_content_hash=None,
                    pending_source_fault_hash=None,
                    lease_owner=None,
                    lease_token=None,
                    lease_expires_at=None,
                    updated_at=now,
                )
                .returning(PhenomenonIndex.retry_count)
            )
            row = result.first()
            return int(row[0]) if row else 0

    # ---------------------------------------------------------------- cleanup
    @staticmethod
    async def _enqueue_cleanup(
        session: AsyncSession,
        kb_id: str,
        rag_doc_id: str,
        reason: str,
        doc_id: str | None = None,
    ) -> None:
        now = _now()
        stmt = insert(RagDocCleanupTask).values(
            rag_kb_id=kb_id,
            rag_doc_id=rag_doc_id,
            doc_id=doc_id,
            reason=reason,
            status=RagCleanupStatus.PENDING.value,
            retry_count=0,
            next_retry_at=now,
            created_at=now,
            updated_at=now,
        )
        await session.execute(
            stmt.on_conflict_do_update(
                index_elements=[
                    RagDocCleanupTask.rag_kb_id,
                    RagDocCleanupTask.rag_doc_id,
                ],
                # A card that now owns the pair is the one to mark deleted.
                set_={"doc_id": stmt.excluded.doc_id},
                where=RagDocCleanupTask.doc_id.is_(None),
            )
        )

    @staticmethod
    async def enqueue_cleanup(
        kb_id: str, rag_doc_id: str, reason: str, doc_id: str | None = None
    ) -> None:
        async with PGManager.session() as session:
            await PhenomenonIndexPGManager._enqueue_cleanup(
                session, kb_id, rag_doc_id, reason, doc_id
            )

    @staticmethod
    async def observe_orphan(kb_id: str, rag_doc_id: str) -> None:
        now = _now()
        async with PGManager.session() as session:
            stmt = insert(RagDocCleanupTask).values(
                rag_kb_id=kb_id,
                rag_doc_id=rag_doc_id,
                reason="orphan",
                status=RagCleanupStatus.OBSERVING.value,
                retry_count=0,
                next_retry_at=now,
                created_at=now,
                updated_at=now,
            )
            await session.execute(stmt.on_conflict_do_nothing())

    @staticmethod
    async def promote_observing(grace_seconds: int = 600) -> int:
        now = _now()
        cutoff = now - timedelta(seconds=grace_seconds)
        async with PGManager.session() as session:
            result = await session.execute(
                update(RagDocCleanupTask)
                .where(
                    RagDocCleanupTask.status == RagCleanupStatus.OBSERVING.value,
                    RagDocCleanupTask.created_at <= cutoff,
                    RagDocCleanupTask.updated_at <= cutoff,
                )
                .values(
                    status=RagCleanupStatus.PENDING.value,
                    next_retry_at=now,
                    updated_at=now,
                )
            )
            return int(result.rowcount or 0)

    @staticmethod
    async def claim_cleanup_task(
        owner: str, lease_seconds: int
    ) -> RagDocCleanupTask | None:
        now = _now()
        async with PGManager.session() as session:
            rows = await session.execute(
                select(RagDocCleanupTask)
                .where(
                    or_(
                        and_(
                            RagDocCleanupTask.status == RagCleanupStatus.PENDING.value,
                            or_(
                                RagDocCleanupTask.next_retry_at.is_(None),
                                RagDocCleanupTask.next_retry_at <= now,
                            ),
                        ),
                        and_(
                            RagDocCleanupTask.status == RagCleanupStatus.DELETING.value,
                            or_(
                                RagDocCleanupTask.lease_expires_at.is_(None),
                                RagDocCleanupTask.lease_expires_at < now,
                            ),
                            RagDocCleanupTask.next_retry_at.is_not(None),
                            RagDocCleanupTask.next_retry_at <= now,
                        ),
                    )
                )
                .order_by(RagDocCleanupTask.id.asc())
                .limit(1)
                .with_for_update(skip_locked=True)
            )
            task = rows.scalars().first()
            if task is None:
                return None
            if not await PhenomenonIndexPGManager._try_doc_lock(
                session, task.rag_kb_id, task.rag_doc_id
            ):
                return None
            referenced = await session.scalar(
                select(func.count()).select_from(PhenomenonIndex).where(
                    or_(
                        and_(
                            PhenomenonIndex.rag_kb_id == task.rag_kb_id,
                            PhenomenonIndex.rag_doc_id == task.rag_doc_id,
                        ),
                        and_(
                            PhenomenonIndex.pending_rag_kb_id == task.rag_kb_id,
                            PhenomenonIndex.pending_rag_doc_id == task.rag_doc_id,
                        ),
                    )
                )
            )
            if referenced:
                await session.execute(
                    delete(RagDocCleanupTask).where(RagDocCleanupTask.id == task.id)
                )
                return None
            task.status = RagCleanupStatus.DELETING.value
            task.lease_owner = owner
            task.lease_expires_at = now + timedelta(seconds=lease_seconds)
            task.updated_at = now
            return task

    @staticmethod
    async def finish_cleanup(
        task_id: int,
        owner: str,
        *,
        success: bool,
        error: str | None = None,
        next_retry_at: datetime | None = None,
    ) -> bool:
        now = _now()
        async with PGManager.session() as session:
            target = await session.get(RagDocCleanupTask, task_id)
            if target is None or target.lease_owner != owner:
                return False
            if success:
                target.status = RagCleanupStatus.DONE.value
                target.lease_owner = None
                target.lease_expires_at = None
                target.last_error = None
                target.next_retry_at = None
                if target.doc_id:
                    # The disabled card is deleted only after its document pair
                    # is really gone; a card that has been re-enabled or still
                    # holds another mapping must keep its current status.
                    await session.execute(
                        update(PhenomenonIndex)
                        .where(
                            PhenomenonIndex.doc_id == target.doc_id,
                            PhenomenonIndex.enabled.is_(False),
                            PhenomenonIndex.rag_doc_id.is_(None),
                            PhenomenonIndex.pending_rag_doc_id.is_(None),
                        )
                        .values(
                            index_status=PhenomenonIndexStatus.DELETED.value,
                            updated_at=now,
                        )
                    )
            else:
                target.retry_count += 1
                target.lease_owner = None
                target.lease_expires_at = None
                target.last_error = error
                target.next_retry_at = next_retry_at
            target.updated_at = now
            return True

    @staticmethod
    async def cleanup_pair_state(kb_id: str, rag_doc_id: str) -> str | None:
        async with PGManager.session() as session:
            return await session.scalar(
                select(RagDocCleanupTask.status).where(
                    RagDocCleanupTask.rag_kb_id == kb_id,
                    RagDocCleanupTask.rag_doc_id == rag_doc_id,
                )
            )

    # ---------------------------------------------------------------- outbox
    @staticmethod
    async def enqueue_event(
        session: AsyncSession,
        *,
        event_key: str,
        event_type: str,
        target_doc_id: str | None,
        payload: dict[str, Any],
    ) -> None:
        now = _now()
        await session.execute(
            insert(IndexEventOutbox)
            .values(
                event_key=event_key,
                event_type=event_type,
                target_doc_id=target_doc_id,
                payload=payload,
                status=IndexEventStatus.PENDING.value,
                retry_count=0,
                next_retry_at=now,
                created_at=now,
            )
            .on_conflict_do_nothing(index_elements=[IndexEventOutbox.event_key])
        )

    @staticmethod
    async def claim_events(owner: str, limit: int, lease_seconds: int) -> list[IndexEventOutbox]:
        now = _now()
        async with PGManager.session() as session:
            rows = await session.execute(
                select(IndexEventOutbox)
                .where(
                    or_(
                        and_(
                            IndexEventOutbox.status
                            == IndexEventStatus.PENDING.value,
                            or_(
                                IndexEventOutbox.next_retry_at.is_(None),
                                IndexEventOutbox.next_retry_at <= now,
                            ),
                        ),
                        and_(
                            IndexEventOutbox.status
                            == IndexEventStatus.FAILED.value,
                            IndexEventOutbox.next_retry_at.is_not(None),
                            IndexEventOutbox.next_retry_at <= now,
                        ),
                        and_(
                            IndexEventOutbox.status == IndexEventStatus.PROCESSING.value,
                            or_(
                                IndexEventOutbox.lease_expires_at.is_(None),
                                IndexEventOutbox.lease_expires_at < now,
                            ),
                        ),
                    )
                )
                .order_by(IndexEventOutbox.id.asc())
                .limit(limit)
                .with_for_update(skip_locked=True)
            )
            events = list(rows.scalars().all())
            for event in events:
                event.status = IndexEventStatus.PROCESSING.value
                event.lease_owner = owner
                event.lease_expires_at = now + timedelta(seconds=lease_seconds)
            return events

    @staticmethod
    async def finish_event(
        event_id: int,
        owner: str,
        *,
        success: bool,
        error: str | None = None,
        next_retry_at: datetime | None = None,
    ) -> bool:
        now = _now()
        async with PGManager.session() as session:
            event = await session.get(IndexEventOutbox, event_id)
            if event is None or event.lease_owner != owner:
                return False
            event.lease_owner = None
            event.lease_expires_at = None
            event.last_error = error
            if success:
                event.status = IndexEventStatus.PROCESSED.value
                event.processed_at = now
                event.next_retry_at = None
            else:
                event.retry_count += 1
                event.status = IndexEventStatus.FAILED.value
                event.next_retry_at = next_retry_at
            event.updated_at = now
            return True

    # ---------------------------------------------------------------- reconcile
    @staticmethod
    async def cards_with_source_drift() -> list[PhenomenonIndex]:
        async with PGManager.session() as session:
            rows = await session.execute(
                select(PhenomenonIndex).where(
                    PhenomenonIndex.searchable.is_(True),
                    PhenomenonIndex.published_source_fault_hash.is_distinct_from(
                        PhenomenonIndex.source_fault_hash
                    ),
                )
            )
            return list(rows.scalars().all())

    @staticmethod
    async def cards_with_invalid_mapping() -> list[PhenomenonIndex]:
        async with PGManager.session() as session:
            rows = await session.execute(
                select(PhenomenonIndex).where(
                    or_(
                        and_(
                            PhenomenonIndex.searchable.is_(True),
                            or_(
                                PhenomenonIndex.rag_doc_id.is_(None),
                                PhenomenonIndex.published_text.is_(None),
                            ),
                        ),
                        and_(
                            PhenomenonIndex.enabled.is_(False),
                            PhenomenonIndex.searchable.is_(True),
                        ),
                        and_(
                            PhenomenonIndex.index_status
                            == PhenomenonIndexStatus.INDEXED.value,
                            PhenomenonIndex.indexed_content_hash.is_distinct_from(
                                PhenomenonIndex.content_hash
                            ),
                        ),
                    )
                )
            )
            return list(rows.scalars().all())

    @staticmethod
    async def stuck_parsing_cards(ttl_minutes: int = 30) -> list[PhenomenonIndex]:
        cutoff = _now() - timedelta(minutes=ttl_minutes)
        async with PGManager.session() as session:
            rows = await session.execute(
                select(PhenomenonIndex).where(
                    PhenomenonIndex.index_status == PhenomenonIndexStatus.PARSING.value,
                    PhenomenonIndex.updated_at < cutoff,
                )
            )
            return list(rows.scalars().all())

    @staticmethod
    async def list_mapped_pairs() -> list[tuple[str, str, str]]:
        async with PGManager.session() as session:
            rows = await session.execute(
                select(
                    PhenomenonIndex.doc_id,
                    PhenomenonIndex.rag_kb_id,
                    PhenomenonIndex.rag_doc_id,
                ).where(PhenomenonIndex.rag_doc_id.is_not(None))
            )
            return [
                (doc_id, kb_id, rag_doc_id)
                for doc_id, kb_id, rag_doc_id in rows.all()
                if kb_id and rag_doc_id
            ]

    @staticmethod
    async def set_searchable(doc_id: str, searchable: bool) -> None:
        async with PGManager.session() as session:
            await session.execute(
                update(PhenomenonIndex)
                .where(PhenomenonIndex.doc_id == doc_id)
                .values(searchable=searchable, updated_at=_now())
            )

    @staticmethod
    async def requeue(doc_id: str) -> None:
        now = _now()
        async with PGManager.session() as session:
            await session.execute(
                update(PhenomenonIndex)
                .where(PhenomenonIndex.doc_id == doc_id)
                .values(
                    index_status=PhenomenonIndexStatus.PENDING.value,
                    next_retry_at=now,
                    retry_count=0,
                    index_error=None,
                    updated_at=now,
                )
            )

    @staticmethod
    async def force_rebuild(doc_id: str) -> bool:
        """Requeue a card and invalidate the reusable vector snapshot."""
        now = _now()
        async with PGManager.session() as session:
            result = await session.execute(
                update(PhenomenonIndex)
                .where(PhenomenonIndex.doc_id == doc_id)
                .values(
                    indexed_content_hash=None,
                    index_status=PhenomenonIndexStatus.PENDING.value,
                    next_retry_at=now,
                    retry_count=0,
                    index_error=None,
                    updated_at=now,
                )
            )
            return bool(result.rowcount)

    @staticmethod
    async def fail_card(
        doc_id: str,
        *,
        error: str,
        next_retry_at: datetime | None,
    ) -> None:
        async with PGManager.session() as session:
            await session.execute(
                update(PhenomenonIndex)
                .where(PhenomenonIndex.doc_id == doc_id)
                .values(
                    index_status=PhenomenonIndexStatus.FAILED.value,
                    index_error=error,
                    next_retry_at=next_retry_at,
                    lease_owner=None,
                    lease_token=None,
                    lease_expires_at=None,
                    updated_at=_now(),
                )
            )

    @staticmethod
    async def clear_mapping(
        doc_id: str,
        *,
        error: str,
        requeue: bool,
    ) -> None:
        now = _now()
        values: dict[str, Any] = {
            "rag_kb_id": None,
            "rag_doc_id": None,
            "searchable": False,
            "index_status": (
                PhenomenonIndexStatus.PENDING.value
                if requeue
                else PhenomenonIndexStatus.FAILED.value
            ),
            "index_error": error,
            "next_retry_at": now if requeue else None,
            "updated_at": now,
        }
        async with PGManager.session() as session:
            await session.execute(
                update(PhenomenonIndex)
                .where(PhenomenonIndex.doc_id == doc_id)
                .values(**values)
            )
