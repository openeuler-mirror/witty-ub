# Copyright (c) Huawei Technologies Co., Ltd. 2023-2025. All rights reserved.
"""Report scanning, case events and the phenomenon publish / cleanup workers.

The service is the only module allowed to write the phenomenon knowledge base.
Business actions commit first; this module reacts asynchronously and never
blocks report browsing or case confirmation.
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
import socket
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from latency.common.local_time import local_now
from latency.config import phenomenon as settings
from latency.database.engine import PGManager
from latency.database.managers.phenomenon_index import PhenomenonIndexPGManager as Mgr
from latency.database.models import (
    DiagCaseLibrary,
    DiagnosticReportIndex,
    PhenomenonIndex,
)
from latency.ENUM.phenomenon import (
    BindingStatus,
    IndexEventType,
    PhenomenonContentSource,
    PhenomenonIndexStatus,
    ReportIndexStatus,
    VerificationLevel,
)
from latency.exceptions import (
    BadRequestBizException,
    NotFoundBizException,
    UnprocessableBizException,
)
from latency.services import label_taxonomy
from latency.services import report_phenomenon as extractor
from latency.services.case_service import CASE_DIR
from latency.services.diagnostic_report import DiagnosticReportService, report_root
from latency.services.rag_client import (
    RAGClient,
    RAGContractError,
    RAGError,
    RAGUnavailableError,
)
from latency.services.report_phenomenon import PhenomenonContentError, PhenomenonDoc
from sqlalchemy import select, update

logger = logging.getLogger(__name__)

REPORT_PREFIX = "report_"
REPORT_SUFFIX = ".html"
SIDECAR_MAX_BYTES = 10 * 1024 * 1024
LEGACY_MAX_BYTES = 5 * 1024 * 1024
RAG_DOC_PREFIX = "phenomenon_"
PARSE_DEADLINE_MINUTES = 30
MAX_PUBLISH_RETRIES = 5
MAX_EVENT_RETRIES = 10
MAX_CLEANUP_RETRIES = 10

WORKER_ID = f"{socket.gethostname()}:{os.getpid()}:{uuid.uuid4().hex[:8]}"

_scan_snapshot: dict[str, tuple] = {}
_missing_reports: set[str] = set()
_legacy_snapshot: dict[str, tuple] = {}
_self_check_done = False


def _now() -> datetime:
    return local_now()


def _backoff(retry: int, base_seconds: int, max_seconds: int) -> datetime:
    return _now() + timedelta(
        seconds=min(base_seconds * (2 ** max(0, retry - 1)), max_seconds)
    )


def _current_label_hash(doc: extractor.PhenomenonDoc | None) -> str | None:
    """Snapshot hash for the fault's current two-level labels."""
    if doc is None:
        return None
    try:
        validation = label_taxonomy.validate_labels(
            doc.first_level_label, doc.second_level_label
        )
    except label_taxonomy.TaxonomyError:
        return None
    if not validation.taxonomy_version:
        return None
    return label_taxonomy.label_snapshot_hash(
        validation.first_level_label,
        validation.second_level_label,
        validation.taxonomy_version,
    )


def _select_bound_case(
    doc: extractor.PhenomenonDoc, candidates: list[DiagCaseLibrary]
) -> DiagCaseLibrary | None:
    """Bind only when both the fault fingerprint and the label snapshot match."""
    label_hash = _current_label_hash(doc)
    for item in candidates:
        if item.source_fault_hash != doc.source_fault_hash:
            continue
        stored_label_hash = getattr(item, "source_label_hash", None)
        if stored_label_hash and stored_label_hash != label_hash:
            continue
        return item
    return None


def _read_json(path: Path, max_bytes: int) -> dict | None:
    try:
        if path.stat().st_size > max_bytes:
            return None
        with path.open("r", encoding="utf-8") as handle:
            payload = json.load(handle)
    except (OSError, ValueError):
        return None
    return payload if isinstance(payload, dict) else None


def _scan_paired_reports(root: Path) -> tuple[bool, list[tuple[str | None, Path]]]:
    """Return ``(scan_complete, [(kb_dir, html_path)])``.

    A failure to list the directory is reported explicitly so the caller never
    mistakes a transient mount problem for report deletion.
    """
    try:
        if not root.is_dir():
            return False, []
        entries = sorted(root.iterdir())
    except OSError:
        return False, []
    reports: list[tuple[str | None, Path]] = []
    complete = True
    for entry in entries:
        try:
            if entry.is_dir():
                for html in sorted(entry.glob(f"{REPORT_PREFIX}*{REPORT_SUFFIX}")):
                    reports.append((entry.name, html))
            elif (
                entry.is_file()
                and entry.name.startswith(REPORT_PREFIX)
                and entry.suffix == REPORT_SUFFIX
            ):
                reports.append((None, entry))
        except OSError:
            # An unreadable subtree hides reports; the scan is incomplete.
            complete = False
            continue
    return complete, reports


def _file_signature(html: Path) -> tuple | None:
    sidecar = html.with_suffix(".json")
    try:
        html_stat = html.stat()
        sidecar_stat = sidecar.stat() if sidecar.exists() else None
    except OSError:
        return None
    return (
        html_stat.st_mtime_ns,
        html_stat.st_size,
        sidecar_stat.st_mtime_ns if sidecar_stat else None,
        sidecar_stat.st_size if sidecar_stat else None,
    )


def _load_report_payload(report_id: str) -> tuple[dict | None, str | None, str | None]:
    """Return ``(payload, kb_dir, error)`` without ever parsing HTML."""
    try:
        kb_dir, html = DiagnosticReportService._locate(report_root(), report_id)
    except (NotFoundBizException, BadRequestBizException):
        return None, None, "report_missing"
    if not html.with_suffix(".json").exists():
        return None, kb_dir, "sidecar_missing"
    payload = _read_json(html.with_suffix(".json"), SIDECAR_MAX_BYTES)
    if payload is None:
        return None, kb_dir, "sidecar_invalid"
    return payload, kb_dir, None


class PhenomenonIndexService:
    """Index orchestration shared by the API, workers and CLI."""

    # ---------------------------------------------------------------- scan
    @staticmethod
    async def scan_reports() -> dict[str, Any]:
        root = report_root()
        ok, files = _scan_paired_reports(root)
        if not ok:
            logger.warning("report directory is not readable; keeping index untouched")
            return {"scan_ok": False, "indexed": 0, "deleted": 0}

        seen: set[str] = set()
        stable: list[tuple[str, str | None, Path]] = []
        for kb_dir, html in files:
            report_id = html.stem
            seen.add(report_id)
            signature = _file_signature(html)
            if signature is None:
                continue
            if _scan_snapshot.get(report_id) != signature:
                _scan_snapshot[report_id] = signature
                continue
            stable.append((report_id, kb_dir, html))

        queued = 0
        for report_id, kb_dir, html in stable:
            try:
                result = await PhenomenonIndexService.index_report(
                    report_id, html=html, kb_dir=kb_dir
                )
                queued += int(result.get("queued_count") or 0)
            except Exception:  # noqa: BLE001 - one report must not stop the scan
                logger.exception("failed to index report %s", report_id)

        deleted = 0
        rows = await PhenomenonIndexService._available_reports()
        for report_id in rows - seen:
            if report_id not in _missing_reports:
                _missing_reports.add(report_id)
                continue
            try:
                await PhenomenonIndexService.handle_report_deleted(report_id)
                deleted += 1
            except Exception:  # noqa: BLE001
                logger.exception("failed to handle deleted report %s", report_id)
        _missing_reports.intersection_update(rows - seen)
        _missing_reports.difference_update(seen)
        return {"scan_ok": True, "indexed": len(stable), "queued": queued, "deleted": deleted}

    @staticmethod
    async def _available_reports() -> set[str]:
        async with PGManager.session() as session:
            rows = await session.execute(
                select(DiagnosticReportIndex.report_id).where(
                    DiagnosticReportIndex.report_available.is_(True)
                )
            )
            return {row[0] for row in rows.all()}

    # ---------------------------------------------------------------- scope
    @staticmethod
    async def index_scope(
        scope: str,
        *,
        report_id: str | None = None,
        case_id: str | None = None,
        force: bool = False,
    ) -> dict[str, Any]:
        if scope == "report":
            if not report_id:
                raise BadRequestBizException(message="scope=report 时 report_id 必填")
            try:
                kb_dir, html = DiagnosticReportService._locate(
                    report_root(), report_id
                )
            except NotFoundBizException as exc:
                raise NotFoundBizException(
                    resource=f"诊断报告 {report_id}"
                ) from exc
            if not html.with_suffix(".json").exists():
                raise UnprocessableBizException(
                    message="报告数据不完整",
                    detail="sidecar_missing: 侧车 JSON 不存在",
                )
            if _read_json(html.with_suffix(".json"), SIDECAR_MAX_BYTES) is None:
                raise UnprocessableBizException(
                    message="报告数据不完整",
                    detail="sidecar_invalid: 侧车 JSON 损坏或超限",
                )
            result = await PhenomenonIndexService.index_report(
                report_id, html=html, kb_dir=kb_dir, force=force
            )
            return {
                "target_id": report_id,
                "queued_count": result.get("queued_count", 0),
                "skipped_count": 0,
                "index_status": result.get("status"),
            }
        if scope == "case":
            if not case_id:
                raise BadRequestBizException(message="scope=case 时 case_id 必填")
            result = await PhenomenonIndexService.sync_case(case_id, force=force)
            return {
                "target_id": case_id,
                "queued_count": result.get("queued_count", 0),
                "skipped_count": 0,
                "index_status": result.get("status"),
            }
        if scope == "legacy_all":
            queued = await PhenomenonIndexService.index_legacy_all(force=force)
            return {
                "target_id": None,
                "queued_count": queued,
                "skipped_count": 0,
                "index_status": PhenomenonIndexStatus.PENDING.value,
            }
        if scope == "all":
            return await PhenomenonIndexService._index_all(force=force)
        raise BadRequestBizException(message=f"非法重建范围 {scope}")

    @staticmethod
    async def _index_all(*, force: bool) -> dict[str, Any]:
        queued = 0
        for _mtime, kb_dir, html in DiagnosticReportService._collect(
            report_root(), None
        ):
            try:
                result = await PhenomenonIndexService.index_report(
                    html.stem, html=html, kb_dir=kb_dir, force=force
                )
                queued += int(result.get("queued_count") or 0)
            except Exception:  # noqa: BLE001
                logger.exception("full reindex failed for %s", html.stem)
        async with PGManager.session() as session:
            rows = await session.execute(
                select(DiagCaseLibrary.id).where(
                    DiagCaseLibrary.existed_status.is_(True),
                    DiagCaseLibrary.status == "confirmed",
                )
            )
            case_ids = [row[0] for row in rows.all()]
        for case_id in case_ids:
            result = await PhenomenonIndexService.sync_case(case_id, force=force)
            queued += int(result.get("queued_count") or 0)
        return {
            "target_id": None,
            "queued_count": queued,
            "skipped_count": 0,
            "index_status": PhenomenonIndexStatus.PENDING.value,
        }

    # ---------------------------------------------------------------- report
    @staticmethod
    async def index_report(
        report_id: str,
        *,
        html: Path | None = None,
        kb_dir: str | None = None,
        force: bool = False,
    ) -> dict[str, Any]:
        if html is None:
            payload, located_kb, error = _load_report_payload(report_id)
            kb_dir = located_kb
        else:
            payload, error = None, None
            sidecar = html.with_suffix(".json")
            if not sidecar.exists():
                error = "sidecar_missing"
            else:
                payload = _read_json(sidecar, SIDECAR_MAX_BYTES)
                error = None if payload is not None else "sidecar_invalid"

        if error or payload is None:
            await PhenomenonIndexService._record_sidecar_error(
                report_id, kb_dir, error or "sidecar_invalid"
            )
            return {"queued_count": 0, "status": ReportIndexStatus.FAILED.value}

        extraction = extractor.extract_report(report_id, payload, kb_dir=kb_dir)
        cases = await PhenomenonIndexService._bound_cases(report_id)
        # Several case versions may exist for one fault; only the version whose
        # fingerprint matches the current fault can be bound.
        cases_by_fault: dict[str, list[DiagCaseLibrary]] = {}
        for case in cases:
            if (
                case.status == "confirmed"
                and case.source_fault_id
                and case.source_fault_hash
            ):
                cases_by_fault.setdefault(case.source_fault_id, []).append(case)

        queued = 0
        bound_case_ids: set[str] = set()
        current_ids: set[str] = set()
        for doc in extraction.faults:
            current_ids.add(doc.doc_id)
            candidates = cases_by_fault.get(doc.source_fault_id or "", [])
            case = _select_bound_case(doc, candidates)
            if case is not None:
                doc.case_id = case.id
                doc.case_no = case.case_no
                doc.verification = extractor.verification_from_case(case)
                doc.binding_status = BindingStatus.VALID.value
                bound_case_ids.add(case.id)
                await PhenomenonIndexService._disable_independent_case(case.id)
            result = await Mgr.upsert_expected(doc, force=force)
            queued += int(result.queued)

        # Every confirmed case that did not bind to the current version must
        # continue as an independent ``case:`` card without a report pointer.
        for case in cases:
            if (
                case.status == "confirmed"
                and case.source_fault_id
                and case.source_fault_hash
                and case.id not in bound_case_ids
            ):
                await PhenomenonIndexService._ensure_independent_case(
                    case, stale=True, force=force
                )

        old_cards = await Mgr.get_cards_by_report(report_id)
        for card in old_cards:
            if card.doc_id in current_ids or not card.enabled:
                continue
            case = next(
                (
                    item
                    for item in cases
                    if item.source_fault_id == card.source_fault_id
                    and item.source_fault_hash == card.source_fault_hash
                ),
                None,
            )
            if case is not None and case.status == "confirmed":
                await PhenomenonIndexService._ensure_independent_case(
                    case, stale=True, force=force
                )
            await Mgr.disable_card(
                card.doc_id, reason="fault_removed", cleanup_reason="expired"
            )
            queued += 1

        index_error = None
        if extraction.fault_errors:
            index_error = "extraction_failed:" + ",".join(
                item["fault_id"] for item in extraction.fault_errors
            )
        await Mgr.upsert_report_index(
            {
                "report_id": report_id,
                "report_meta_id": extractor._text(
                    extractor._as_dict(payload.get("report")).get("report_id")
                ),
                "kb_id": extraction.kb_id,
                "kb_name": extraction.kb_name,
                "title": extraction.title,
                "generated_at": extraction.generated_at,
                "operation": extraction.operation,
                "time_range_start": extraction.time_range_start,
                "time_range_end": extraction.time_range_end,
                "fault_count": extraction.fault_count,
                "sidecar_hash": extraction.sidecar_hash,
                "index_status": ReportIndexStatus.PENDING.value,
                "index_error": index_error,
                "report_available": True,
            }
        )
        status = await PhenomenonIndexService.refresh_report_status(report_id)
        return {"queued_count": queued, "status": status}

    @staticmethod
    async def _record_sidecar_error(
        report_id: str, kb_dir: str | None, error: str
    ) -> None:
        await Mgr.upsert_report_index(
            {
                "report_id": report_id,
                "kb_id": kb_dir,
                "index_status": ReportIndexStatus.FAILED.value,
                "index_error": error,
                "report_available": True,
            }
        )
        async with PGManager.session() as session:
            await session.execute(
                update(PhenomenonIndex)
                .where(
                    PhenomenonIndex.report_id == report_id,
                    PhenomenonIndex.enabled.is_(True),
                )
                .values(
                    searchable=False,
                    index_status=PhenomenonIndexStatus.STALE.value,
                    index_error=error,
                    updated_at=_now(),
                )
            )

    @staticmethod
    async def refresh_report_status(report_id: str) -> str:
        report = await Mgr.get_report_index(report_id)
        if report is None:
            return ReportIndexStatus.UNKNOWN.value
        counts = await Mgr.card_status_counts(report_id)
        active = sum(counts.values())
        if active == 0:
            status = (
                ReportIndexStatus.FAILED.value
                if report.index_error
                else ReportIndexStatus.NOT_APPLICABLE.value
            )
        elif counts.get(PhenomenonIndexStatus.FAILED.value) or counts.get(
            PhenomenonIndexStatus.STALE.value
        ):
            status = ReportIndexStatus.FAILED.value
        elif counts.get(PhenomenonIndexStatus.INDEXED.value, 0) == active:
            status = ReportIndexStatus.INDEXED.value
        elif counts.get(PhenomenonIndexStatus.INDEXED.value, 0) > 0:
            status = ReportIndexStatus.PARTIAL.value
        else:
            status = ReportIndexStatus.PENDING.value
        await Mgr.update_report_status(
            report_id,
            status,
            index_error=report.index_error,
            indexed_at=_now() if status == ReportIndexStatus.INDEXED.value else None,
        )
        return status

    # ---------------------------------------------------------------- cases
    @staticmethod
    async def _bound_cases(report_id: str) -> list[DiagCaseLibrary]:
        async with PGManager.session() as session:
            rows = await session.execute(
                select(DiagCaseLibrary).where(
                    DiagCaseLibrary.report_id == report_id,
                    DiagCaseLibrary.existed_status.is_(True),
                    DiagCaseLibrary.status != "archived",
                )
            )
            return list(rows.scalars().all())

    @staticmethod
    async def sync_case(case_id: str, *, force: bool = False) -> dict[str, Any]:
        case = await PhenomenonIndexService._get_case(case_id)
        if case is None or case.status in ("draft", "archived"):
            await PhenomenonIndexService._remove_case_from_cards(case_id)
            return {"queued_count": 0, "status": case.status if case else "missing"}

        queued = 0
        if not (case.report_id and case.source_fault_id):
            queued = int(
                await PhenomenonIndexService._ensure_independent_case(
                    case, stale=False, force=force
                )
            )
            await PhenomenonIndexService._remove_case_pointer(case_id)
            return {"queued_count": queued, "status": "case_card"}

        current, error = await PhenomenonIndexService.resolve_current_fault(
            case.report_id, case.source_fault_id
        )
        report_doc_id = f"report:{case.report_id}:{case.source_fault_id}"
        card = await Mgr.get_card(report_doc_id)
        if error and error != "report_missing":
            # A transient mount / sidecar problem must not downgrade a valid
            # binding; let the outbox retry after the report is readable again.
            raise RuntimeError(f"report_unavailable:{error}")
        if error == "report_missing":
            if (
                card is not None
                and card.enabled
                and card.source_fault_hash == case.source_fault_hash
            ):
                await Mgr.touch_card_metadata(
                    report_doc_id,
                    case_id=case.id,
                    case_no=case.case_no,
                    verification=extractor.verification_from_case(case),
                    binding_status=BindingStatus.VALID.value,
                )
                await PhenomenonIndexService._disable_independent_case(case.id)
                if force and await Mgr.force_rebuild(report_doc_id):
                    queued += 1
                return {"queued_count": queued, "status": "merged"}
            queued += int(
                await PhenomenonIndexService._ensure_independent_case(
                    case, stale=True, force=force
                )
            )
            return {"queued_count": queued, "status": "stale"}

        valid = bool(
            current and current.source_fault_hash == case.source_fault_hash
        )
        if valid and getattr(case, "source_label_hash", None):
            valid = _current_label_hash(current) == case.source_label_hash
        if valid and (card is None or force):
            await PhenomenonIndexService.index_report(case.report_id, force=force)
            card = await Mgr.get_card(report_doc_id)
            if card is not None:
                queued += 1

        if valid and card is not None:
            await Mgr.touch_card_metadata(
                report_doc_id,
                case_id=case.id,
                case_no=case.case_no,
                verification=extractor.verification_from_case(case),
                binding_status=BindingStatus.VALID.value,
            )
            await PhenomenonIndexService._disable_independent_case(case.id)
        else:
            if card is not None:
                await Mgr.remove_case_pointer(
                    report_doc_id,
                    fallback_verification=(
                        VerificationLevel.REPORT_ONLY.value
                        if current and current.verification == VerificationLevel.REPORT_ONLY.value
                        else VerificationLevel.SUSPECTED.value
                    ),
                )
            queued += int(
                await PhenomenonIndexService._ensure_independent_case(
                    case, stale=True, force=force
                )
            )

        await PhenomenonIndexService.refresh_report_status(case.report_id)
        return {"queued_count": queued, "status": "merged" if valid else "stale"}

    @staticmethod
    async def _get_case(case_id: str) -> DiagCaseLibrary | None:
        async with PGManager.session() as session:
            row = await session.get(DiagCaseLibrary, case_id)
            if row is None or not row.existed_status:
                return None
            return row

    @staticmethod
    async def resolve_current_fault(
        report_id: str, fault_id: str
    ) -> tuple[PhenomenonDoc | None, str | None]:
        """Return the current fault card or a stable error code."""
        payload, kb_dir, error = _load_report_payload(report_id)
        if error:
            return None, error
        try:
            extraction = extractor.extract_report(report_id, payload or {}, kb_dir=kb_dir)
        except PhenomenonContentError as exc:
            return None, exc.code
        doc = next(
            (item for item in extraction.faults if item.source_fault_id == fault_id),
            None,
        )
        if doc is None:
            return None, "fault_not_found_or_excluded"
        return doc, None

    @staticmethod
    async def _current_fault_doc(
        report_id: str, fault_id: str
    ) -> PhenomenonDoc | None:
        doc, _error = await PhenomenonIndexService.resolve_current_fault(
            report_id, fault_id
        )
        return doc

    @staticmethod
    async def _ensure_independent_case(
        case: DiagCaseLibrary, *, stale: bool, force: bool = False
    ) -> bool:
        doc = extractor.extract_case_doc(case)
        doc.binding_status = (
            BindingStatus.STALE.value if stale else BindingStatus.NONE.value
        )
        doc.report_id = None
        doc.source_fault_id = None
        result = await Mgr.upsert_expected(doc, force=force)
        return bool(result.queued)

    @staticmethod
    async def _disable_independent_case(case_id: str) -> None:
        doc_id = f"case:{case_id}"
        card = await Mgr.get_card(doc_id)
        if card is not None and card.enabled:
            await Mgr.disable_card(doc_id, reason="merged_to_report")

    @staticmethod
    async def _remove_case_pointer(case_id: str) -> None:
        cards = await Mgr.get_cards_by_case(case_id)
        for card in cards:
            if card.kind == "case":
                continue
            if card.report_id and card.source_fault_id:
                current = await PhenomenonIndexService._current_fault_doc(
                    card.report_id, card.source_fault_id
                )
                fallback = (
                    VerificationLevel.REPORT_ONLY.value
                    if current and current.verification == VerificationLevel.REPORT_ONLY.value
                    else VerificationLevel.SUSPECTED.value
                )
                await Mgr.remove_case_pointer(
                    card.doc_id, fallback_verification=fallback
                )

    @staticmethod
    async def _remove_case_from_cards(case_id: str) -> None:
        cards = await Mgr.get_cards_by_case(case_id)
        for card in cards:
            if card.kind == "case":
                await Mgr.disable_card(card.doc_id, reason="case_archived")
                continue
            if card.content_source == PhenomenonContentSource.CASE.value:
                await Mgr.disable_card(card.doc_id, reason="case_archived")
                continue
            if card.report_id and card.source_fault_id:
                current = await PhenomenonIndexService._current_fault_doc(
                    card.report_id, card.source_fault_id
                )
                fallback = (
                    VerificationLevel.REPORT_ONLY.value
                    if current and current.verification == VerificationLevel.REPORT_ONLY.value
                    else VerificationLevel.SUSPECTED.value
                )
                await Mgr.remove_case_pointer(
                    card.doc_id, fallback_verification=fallback
                )

    @staticmethod
    async def handle_report_deleted(report_id: str) -> dict[str, Any]:
        cards = await Mgr.get_cards_by_report(report_id)
        cases = await PhenomenonIndexService._bound_cases(report_id)
        by_fault: dict[str, list[DiagCaseLibrary]] = {}
        for case in cases:
            if case.status == "confirmed" and case.source_fault_id:
                by_fault.setdefault(case.source_fault_id, []).append(case)
        switched = 0
        disabled = 0
        for card in cards:
            if not card.enabled:
                continue
            case = next(
                (
                    item
                    for item in by_fault.get(card.source_fault_id or "", [])
                    if item.source_fault_hash == card.source_fault_hash
                ),
                None,
            )
            if case is not None:
                doc = extractor.extract_case_doc(case)
                await Mgr.touch_card_metadata(
                    card.doc_id,
                    case_id=case.id,
                    case_no=case.case_no,
                    verification=extractor.verification_from_case(case),
                    binding_status=BindingStatus.VALID.value,
                    content_source=PhenomenonContentSource.CASE.value,
                    text=doc.text,
                    title=doc.title,
                    symptom=doc.symptom,
                    content_hash=doc.content_hash,
                    source_fault_hash=doc.source_fault_hash,
                )
                await PhenomenonIndexService._disable_independent_case(case.id)
                switched += 1
            else:
                await Mgr.disable_card(
                    card.doc_id, reason="report_deleted", cleanup_reason="expired"
                )
                disabled += 1
        await Mgr.set_report_available(report_id, False, index_error=None)
        return {"switched": switched, "disabled": disabled}

    # ---------------------------------------------------------------- legacy
    @staticmethod
    async def sync_legacy(
        legacy_case_id: str, *, deleted: bool = False, force: bool = False
    ) -> dict[str, Any]:
        if deleted:
            return await PhenomenonIndexService._disable_legacy_cards(legacy_case_id)
        path = Path(CASE_DIR) / f"{legacy_case_id}.json"
        payload = _read_json(path, LEGACY_MAX_BYTES)
        if payload is None:
            return await PhenomenonIndexService._disable_legacy_cards(legacy_case_id)
        try:
            doc = extractor.extract_legacy_doc(payload)
        except PhenomenonContentError as exc:
            logger.warning(
                "skip legacy case %s: %s", legacy_case_id, exc.code
            )
            return await PhenomenonIndexService._disable_legacy_cards(legacy_case_id)
        if doc is None:
            return await PhenomenonIndexService._disable_legacy_cards(legacy_case_id)
        result = await Mgr.upsert_expected(doc, force=force)
        return {"queued_count": int(result.queued), "status": "indexed"}

    @staticmethod
    async def _disable_legacy_cards(legacy_case_id: str) -> dict[str, Any]:
        cards = await Mgr.get_cards_by_legacy(legacy_case_id)
        for card in cards:
            if card.enabled:
                await Mgr.disable_card(
                    card.doc_id,
                    reason="legacy_deleted",
                    cleanup_reason="expired",
                )
        return {"queued_count": 0, "status": "deleted"}

    @staticmethod
    async def index_legacy_all(*, force: bool = False) -> int:
        queued = 0
        try:
            names = sorted(os.listdir(CASE_DIR))
        except OSError:
            return 0
        for name in names:
            if not name.endswith(".json") or name.startswith("_"):
                continue
            result = await PhenomenonIndexService.sync_legacy(
                name[:-5], force=force
            )
            queued += int(result.get("queued_count") or 0)
        return queued

    @staticmethod
    async def scan_legacy() -> dict[str, int]:
        """Reconcile old file cases by mtime; files remain the source of truth."""
        try:
            names = sorted(os.listdir(CASE_DIR))
            files: dict[str, tuple] = {}
            for name in names:
                if not name.endswith(".json") or name.startswith("_"):
                    continue
                path = Path(CASE_DIR) / name
                try:
                    stat = path.stat()
                except OSError:
                    continue
                files[name[:-5]] = (stat.st_mtime_ns, stat.st_size)
        except OSError:
            logger.warning("legacy case directory is not readable; keeping index")
            return {"indexed": 0, "deleted": 0}

        indexed = 0
        for legacy_id, signature in files.items():
            if _legacy_snapshot.get(legacy_id) == signature:
                continue
            _legacy_snapshot[legacy_id] = signature
            try:
                await PhenomenonIndexService.sync_legacy(legacy_id)
                indexed += 1
            except Exception:  # noqa: BLE001
                logger.exception("failed to index legacy case %s", legacy_id)

        deleted = 0
        for legacy_id in await Mgr.list_enabled_legacy_ids():
            if legacy_id in files:
                continue
            try:
                await PhenomenonIndexService.sync_legacy(legacy_id, deleted=True)
                deleted += 1
            except Exception:  # noqa: BLE001
                logger.exception("failed to disable legacy case %s", legacy_id)
        for legacy_id in list(_legacy_snapshot):
            if legacy_id not in files:
                _legacy_snapshot.pop(legacy_id, None)
        return {"indexed": indexed, "deleted": deleted}

    @staticmethod
    async def notify_legacy_changed(legacy_case_id: str) -> None:
        """Best-effort event; the periodic scan compensates a failed insert."""
        path = Path(CASE_DIR) / f"{legacy_case_id}.json"
        try:
            signature = str(path.stat().st_mtime_ns)
        except OSError:
            signature = uuid.uuid4().hex
        try:
            async with PGManager.session() as session:
                await Mgr.enqueue_event(
                    session,
                    event_key=f"legacy_changed:{legacy_case_id}:{signature}",
                    event_type=IndexEventType.LEGACY_CHANGED.value,
                    target_doc_id=f"legacy:{legacy_case_id}",
                    payload={"legacy_case_id": legacy_case_id},
                )
        except Exception:  # noqa: BLE001 - file write already succeeded
            logger.warning(
                "failed to enqueue legacy event for %s", legacy_case_id, exc_info=True
            )

    # ---------------------------------------------------------------- events
    @staticmethod
    async def consume_events(limit: int = 20) -> int:
        events = await Mgr.claim_events(
            WORKER_ID, limit, settings.event_lease_seconds()
        )
        processed = 0
        for event in events:
            try:
                await PhenomenonIndexService._handle_event(event)
                await Mgr.finish_event(event.id, WORKER_ID, success=True)
                processed += 1
            except Exception as exc:  # noqa: BLE001
                retries = int(event.retry_count or 0) + 1
                terminal = retries >= MAX_EVENT_RETRIES
                await Mgr.finish_event(
                    event.id,
                    WORKER_ID,
                    success=False,
                    error=f"{type(exc).__name__}: {exc}"[:256],
                    next_retry_at=None if terminal else _backoff(retries, 5, 3600),
                )
                logger.warning(
                    "index event %s failed (%s)", event.event_key, type(exc).__name__
                )
        return processed

    @staticmethod
    async def _handle_event(event: Any) -> None:
        payload = event.payload or {}
        event_type = event.event_type
        if event_type == IndexEventType.REPORT_DELETED.value:
            await PhenomenonIndexService.handle_report_deleted(payload["report_id"])
        elif event_type == IndexEventType.LEGACY_CHANGED.value:
            await PhenomenonIndexService.sync_legacy(
                payload["legacy_case_id"], deleted=bool(payload.get("deleted"))
            )
        elif event_type in {
            IndexEventType.CASE_CONFIRMED.value,
            IndexEventType.CASE_ARCHIVED.value,
            IndexEventType.CASE_VERIFICATION.value,
        }:
            await PhenomenonIndexService.sync_case(payload["case_id"])
        else:
            raise ValueError(f"unknown index event type {event_type}")

    # ---------------------------------------------------------------- publish
    @staticmethod
    def _rag_targets() -> tuple[RAGClient, str]:
        client = RAGClient.from_env()
        kb_id = settings.rag_kb_id()
        if not kb_id:
            raise RAGUnavailableError("RAG_PHENOMENON_KB_ID is not configured")
        return client, kb_id

    @staticmethod
    async def publish_due_cards() -> int:
        try:
            client, kb_id = PhenomenonIndexService._rag_targets()
        except RAGError as exc:
            logger.warning("phenomenon publish skipped: %s", exc)
            return 0
        cards = await Mgr.claim_due_cards(
            WORKER_ID,
            settings.rag_publish_workers(),
            settings.publish_lease_seconds(),
        )
        if not cards:
            return 0
        await asyncio.gather(
            *[
                PhenomenonIndexService._publish_card(card, client, kb_id)
                for card in cards
            ],
            return_exceptions=True,
        )
        return len(cards)

    @staticmethod
    async def resume_parsing_cards() -> int:
        try:
            client, kb_id = PhenomenonIndexService._rag_targets()
        except RAGError as exc:
            logger.warning("phenomenon parse poll skipped: %s", exc)
            return 0
        cards = await Mgr.claim_parsing_cards(
            WORKER_ID,
            settings.rag_publish_workers(),
            settings.publish_lease_seconds(),
        )
        for card in cards:
            await PhenomenonIndexService._poll_parsing(card, client, kb_id)
        return len(cards)

    @staticmethod
    async def _publish_card(
        card: PhenomenonIndex, client: RAGClient, kb_id: str
    ) -> None:
        owner = card.lease_owner or WORKER_ID
        token = card.lease_token or ""
        target_hash = card.content_hash or ""
        target_source = card.source_fault_hash

        if (
            card.indexed_content_hash == target_hash
            and card.published_source_fault_hash == target_source
            and card.rag_kb_id == kb_id
            and card.rag_doc_id
        ):
            status = await Mgr.metadata_publish(
                card.doc_id, owner, token, kb_id, target_hash, target_source
            )
            if status == "published":
                await PhenomenonIndexService._refresh_after_publish(card)
                return
            if status in {"lost_lease", "version_changed", "disabled", "not_found"}:
                return

        filename = f"{RAG_DOC_PREFIX}{extractor.sha256_hex(card.doc_id)[:16]}.txt"
        try:
            rag_doc_id = await client.upload_text(kb_id, filename, card.text or "")
        except RAGError as exc:
            await PhenomenonIndexService._fail_publish(card, str(exc))
            return

        registered = await Mgr.register_pending_candidate(
            card.doc_id,
            owner,
            token,
            kb_id,
            rag_doc_id,
            target_hash,
            target_source,
        )
        if not registered:
            await Mgr.enqueue_cleanup(kb_id, rag_doc_id, "expired", card.doc_id)
            await Mgr.record_publish_failure(
                card.doc_id,
                owner,
                token,
                error="candidate_rejected",
                next_retry_at=_backoff(1, 30, 1800),
                terminal=False,
            )
            return

        if not await Mgr.mark_parsing(card.doc_id, owner, token, kb_id, rag_doc_id):
            # The desired version moved on after this upload; release it.
            await Mgr.withdraw_candidate(card.doc_id, owner, token)
            await Mgr.enqueue_cleanup(kb_id, rag_doc_id, "expired", card.doc_id)
            return
        refreshed = await Mgr.get_card(card.doc_id)
        if refreshed is not None:
            await PhenomenonIndexService._poll_parsing(refreshed, client, kb_id)

    @staticmethod
    async def _poll_parsing(
        card: PhenomenonIndex, client: RAGClient, kb_id: str
    ) -> None:
        owner = card.lease_owner or WORKER_ID
        token = card.lease_token or ""
        rag_doc_id = card.pending_rag_doc_id or ""
        pending_kb = card.pending_rag_kb_id or kb_id
        if not rag_doc_id:
            return
        if card.next_retry_at is not None and card.next_retry_at < _now():
            await PhenomenonIndexService._fail_publish(card, "parse_timeout")
            return
        try:
            status = await client.parse_status(rag_doc_id)
        except RAGUnavailableError as exc:
            await Mgr.record_publish_failure(
                card.doc_id,
                owner,
                token,
                error=str(exc)[:256],
                next_retry_at=_backoff(1, 30, 1800),
                terminal=False,
            )
            return
        except RAGContractError as exc:
            await PhenomenonIndexService._fail_publish(card, f"contract:{exc}")
            return

        if status == "success":
            target_hash = card.pending_content_hash or ""
            if not target_hash:
                await Mgr.withdraw_candidate(card.doc_id, owner, token)
                await Mgr.enqueue_cleanup(pending_kb, rag_doc_id, "expired", card.doc_id)
                return
            result = await Mgr.switch_published(
                card.doc_id,
                owner,
                token,
                pending_kb,
                rag_doc_id,
                target_hash,
                card.pending_source_fault_hash,
            )
            if result.status != "switched":
                await Mgr.withdraw_candidate(card.doc_id, owner, token)
                await Mgr.enqueue_cleanup(pending_kb, rag_doc_id, "expired", card.doc_id)
                if result.status in {
                    "cleanup_conflict",
                    "doc_locked",
                    "version_changed",
                    "candidate_version_mismatch",
                }:
                    await Mgr.record_publish_failure(
                        card.doc_id,
                        owner,
                        token,
                        error=result.status,
                        next_retry_at=_backoff(1, 30, 1800),
                        terminal=False,
                    )
                return
            await PhenomenonIndexService._refresh_after_publish(card)
            return

        if status in {"failed", "failed_pending", "canceled"}:
            await PhenomenonIndexService._fail_publish(card, f"parse_{status}")
            return

        await Mgr.renew_lease(
            card.doc_id, owner, token, settings.publish_lease_seconds()
        )

    @staticmethod
    async def _fail_publish(card: PhenomenonIndex, error: str) -> None:
        owner = card.lease_owner or WORKER_ID
        token = card.lease_token or ""
        pair = await Mgr.withdraw_candidate(
            card.doc_id, owner, token, reason="expired"
        )
        if pair and pair[0] and pair[1]:
            await Mgr.enqueue_cleanup(pair[0], pair[1], "expired", card.doc_id)
        retries = int(card.retry_count or 0) + 1
        terminal = retries >= MAX_PUBLISH_RETRIES
        await Mgr.record_publish_failure(
            card.doc_id,
            owner,
            token,
            error=error[:256],
            next_retry_at=None if terminal else _backoff(retries, 30, 1800),
            terminal=terminal,
        )
        await PhenomenonIndexService._refresh_after_publish(card)

    @staticmethod
    async def _refresh_after_publish(card: PhenomenonIndex) -> None:
        if card.report_id:
            await PhenomenonIndexService.refresh_report_status(card.report_id)

    # ---------------------------------------------------------------- cleanup
    @staticmethod
    async def cleanup_documents(limit: int = 10) -> int:
        try:
            client, _kb_id = PhenomenonIndexService._rag_targets()
        except RAGError as exc:
            logger.warning("cleanup skipped: %s", exc)
            return 0
        done = 0
        for _ in range(limit):
            task = await Mgr.claim_cleanup_task(
                WORKER_ID, settings.cleanup_lease_seconds()
            )
            if task is None:
                break
            try:
                await client.delete_document(task.rag_doc_id)
                await Mgr.finish_cleanup(task.id, WORKER_ID, success=True)
                done += 1
            except RAGError as exc:
                retries = int(task.retry_count or 0) + 1
                await Mgr.finish_cleanup(
                    task.id,
                    WORKER_ID,
                    success=False,
                    error=str(exc)[:256],
                    next_retry_at=(
                        None
                        if retries >= MAX_CLEANUP_RETRIES
                        else _backoff(retries, 60, 21600)
                    ),
                )
        return done

    # ---------------------------------------------------------------- reconcile
    @staticmethod
    async def reconcile() -> dict[str, int]:
        stats = {"drift": 0, "invalid": 0, "stuck": 0, "missing": 0, "orphans": 0}
        await Mgr.promote_observing(600)

        for card in await Mgr.cards_with_source_drift():
            await Mgr.set_searchable(card.doc_id, False)
            await Mgr.requeue(card.doc_id)
            stats["drift"] += 1

        for card in await Mgr.cards_with_invalid_mapping():
            await Mgr.set_searchable(card.doc_id, False)
            if card.enabled:
                await Mgr.requeue(card.doc_id)
            stats["invalid"] += 1

        for card in await Mgr.stuck_parsing_cards(PARSE_DEADLINE_MINUTES):
            await Mgr.fail_card(
                card.doc_id, error="parse_timeout", next_retry_at=None
            )
            stats["stuck"] += 1

        try:
            client, kb_id = PhenomenonIndexService._rag_targets()
        except RAGError:
            return stats
        try:
            remote = await PhenomenonIndexService._list_all_remote_docs(client, kb_id)
        except RAGError as exc:
            logger.warning("reconcile skipped RAG document list: %s", exc)
            return stats

        local_pairs = {
            (kb, doc)
            for _doc_id, kb, doc in await Mgr.list_mapped_pairs()
            if kb == kb_id
        }
        # RAG 文档清单会保留已删除文档的墓碑记录；墓碑不算孤儿，也不能当作映射仍存在。
        active_remote = [
            doc for doc in remote if str(doc.get("status") or "") != "deleted"
        ]
        remote_ids = {
            str(doc.get("id")) for doc in active_remote if doc.get("id") is not None
        }
        for doc in active_remote:
            rag_doc_id = doc.get("id")
            if not rag_doc_id or not str(doc.get("name", "")).startswith(RAG_DOC_PREFIX):
                continue
            if (kb_id, str(rag_doc_id)) not in local_pairs:
                await Mgr.observe_orphan(kb_id, str(rag_doc_id))
                stats["orphans"] += 1

        for _doc_id, kb, rag_doc_id in await Mgr.list_mapped_pairs():
            if kb != kb_id:
                continue
            if rag_doc_id not in remote_ids:
                card = await Mgr.get_card_by_rag_doc(kb, rag_doc_id)
                if card is not None:
                    await Mgr.clear_mapping(
                        card.doc_id, error="remote_document_missing", requeue=True
                    )
                    stats["missing"] += 1
        return stats

    @staticmethod
    async def _list_all_remote_docs(
        client: RAGClient, kb_id: str
    ) -> list[dict[str, Any]]:
        documents: list[dict[str, Any]] = []
        page_num = 1
        while True:
            total, page = await client.list_documents(
                kb_id, page_size=100, page_num=page_num
            )
            documents.extend(page)
            if len(documents) >= total or not page:
                break
            page_num += 1
            if page_num > 1000:
                raise RAGContractError("document listing did not converge")
        return documents

    # ---------------------------------------------------------------- self check
    @staticmethod
    def self_check_done() -> bool:
        """Whether the startup upload→parse→search round trip has passed."""
        return _self_check_done

    @staticmethod
    async def run_self_check() -> bool:
        """Upload → parse → search → delete one throwaway document."""
        global _self_check_done
        if _self_check_done:
            return True
        try:
            client, kb_id = PhenomenonIndexService._rag_targets()
        except RAGError as exc:
            logger.warning("phenomenon self-check skipped: %s", exc)
            return False
        marker = f"witty-phenomenon-self-check-{uuid.uuid4().hex[:8]}"
        doc_id: str | None = None
        try:
            doc_id = await client.upload_text(
                kb_id, f"{RAG_DOC_PREFIX}self_check.txt", marker
            )
            for _ in range(30):
                if await client.parse_status(doc_id) == "success":
                    break
                await asyncio.sleep(2)
            else:
                logger.warning("phenomenon self-check parse timed out")
                return False
            chunks = await client.search_chunks(kb_id, marker, 3)
            matched = any(str(item.get("doc_id")) == doc_id for item in chunks)
            if not matched:
                logger.warning("phenomenon self-check search did not recall the test doc")
            _self_check_done = True
            return matched
        except RAGError as exc:
            logger.warning("phenomenon self-check failed: %s", exc)
            return False
        finally:
            if doc_id:
                try:
                    await client.delete_document(doc_id)
                except RAGError:
                    logger.warning("failed to remove self-check document")
