# Copyright (c) Huawei Technologies Co., Ltd. 2023-2025. All rights reserved.
"""Deployment-shipped report archive: import once per archive version.

The image (or the source checkout) carries one immutable archive. The runtime
copy is authoritative: a changed archive replaces it and is imported again,
which is how a new image refreshes the built-in reports.

``report_id`` is content-addressed, so a corrected report arrives under a new
id while its predecessor keeps working. Superseded ids recorded by the previous
state file are therefore archived (cases) and removed (report files) explicitly
instead of being left behind as a second version of the same document.
"""
from __future__ import annotations

import hashlib
import json
import logging
import os
import re
import tempfile
from pathlib import Path
from typing import Any

from sqlalchemy import select, text

from latency.common.local_time import local_now
from latency.database.engine import PGManager
from latency.database.models import DiagCaseLibrary, DiagnosticReportIndex
from latency.schemas.diag_case_library import ArchiveDiagCaseRequest
from latency.services.diag_case_library import DiagCaseLibraryService
from latency.services.diagnostic_report import report_root
from latency.services.phenomenon_index import PhenomenonIndexService
from latency.services.report_import import (
    STATUS_DUPLICATE,
    STATUS_IMPORTED,
    ImportOptions,
    import_reports,
)

logger = logging.getLogger(__name__)

STATE_VERSION = 1
# One built-in sync at a time across replicas; released with the transaction.
ARCHIVE_LOCK_KEY = 0x57554B42
DEFAULT_SOURCE_NAME = "内置定界报告"
SUPERSEDE_REASON = "内置定界报告已由新版本替换"
# Only content-addressed imported reports may be removed by supersede.
REPORT_ID_RE = re.compile(r"^report_hist_[0-9a-f]{8,64}$")
REPORT_SUFFIXES = (".html", ".json", ".source.json", ".import.json")

STATUS_COMPLETED = "completed"
STATUS_PARTIAL = "partial"
STATUS_BUSY = "busy"


def archive_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_state(state_path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(state_path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    if not isinstance(payload, dict) or payload.get("version") != STATE_VERSION:
        return {}
    return payload


def _write_state(state_path: Path, payload: dict[str, Any]) -> None:
    state_path.parent.mkdir(parents=True, exist_ok=True)
    handle, temp_name = tempfile.mkstemp(
        prefix=f".{state_path.stem}.", suffix=".tmp", dir=str(state_path.parent)
    )
    temp_path = Path(temp_name)
    try:
        with os.fdopen(handle, "w", encoding="utf-8") as stream:
            json.dump(payload, stream, ensure_ascii=False, indent=2)
            stream.write("\n")
        os.replace(temp_path, state_path)
    except BaseException:
        temp_path.unlink(missing_ok=True)
        raise


async def _cases_bound_to(report_id: str) -> list[DiagCaseLibrary]:
    """Every live case derived from one report, including drafts."""
    async with PGManager.session() as session:
        rows = await session.execute(
            select(DiagCaseLibrary)
            .where(
                DiagCaseLibrary.report_id == report_id,
                DiagCaseLibrary.existed_status.is_(True),
                DiagCaseLibrary.status != "archived",
            )
            .order_by(DiagCaseLibrary.created_at)
        )
        return list(rows.scalars().all())


async def _missing_report_rows(report_ids: list[str]) -> list[str]:
    """Report ids the state file claims to have imported but the database lost."""
    if not report_ids:
        return []
    async with PGManager.session() as session:
        rows = await session.execute(
            select(DiagnosticReportIndex.report_id).where(
                DiagnosticReportIndex.report_id.in_(report_ids)
            )
        )
        present = {str(value) for value in rows.scalars().all()}
    return [report_id for report_id in report_ids if report_id not in present]


def _remove_report_files(report_id: str) -> list[str]:
    if not REPORT_ID_RE.match(report_id):
        raise ValueError(f"refusing to remove non-imported report id: {report_id}")
    root = report_root()
    removed: list[str] = []
    for suffix in REPORT_SUFFIXES:
        path = root / f"{report_id}{suffix}"
        if path.is_file():
            path.unlink()
            removed.append(path.name)
    return removed


async def supersede_report(report_id: str, operator: str) -> dict[str, Any]:
    """Archive the cases of an obsolete built-in report and drop its files."""
    if not REPORT_ID_RE.match(report_id):
        raise ValueError(f"refusing to supersede non-imported report id: {report_id}")
    archived: list[str] = []
    for case in await _cases_bound_to(report_id):
        await DiagCaseLibraryService.archive_case(
            case.id,
            ArchiveDiagCaseRequest(
                archived_by=operator,
                archive_reason=SUPERSEDE_REASON,
            ),
        )
        archived.append(case.id)
    cleanup = await PhenomenonIndexService.handle_report_deleted(report_id)
    removed = _remove_report_files(report_id)
    return {
        "report_id": report_id,
        "archived_cases": archived,
        "disabled_cards": int(cleanup.get("disabled") or 0),
        "removed_files": removed,
    }


async def sync_builtin_reports(
    archive: Path,
    state_path: Path,
    operator: str,
    *,
    force: bool = False,
    supersede: bool = True,
) -> dict[str, Any]:
    """Import the archive when its content changed; supersede previous ids.

    Per-file failures keep the archive's hash in the state file: the material is
    deterministic, so retrying on every start would stay red until the archive is
    fixed. Unexpected exceptions leave the state untouched so the next start
    retries.
    """
    if not archive.is_file():
        return {"status": "skipped", "reason": "archive_missing", "archive": str(archive)}
    digest = archive_sha256(archive)
    state = read_state(state_path)
    recorded = [
        str(rid) for rid in state.get("report_ids") or [] if REPORT_ID_RE.match(str(rid))
    ]
    if (
        not force
        and state.get("archive_sha256") == digest
        and state.get("status") in {STATUS_COMPLETED, STATUS_PARTIAL}
    ):
        # 状态文件与报告卷可能比数据库活得久（重建数据库、换库、只删 pg 卷），
        # 只比哈希会把空库当成"已导入"，所以先确认记录的每篇报告仍在库里。
        missing = await _missing_report_rows(recorded)
        if not missing:
            return {
                "status": "skipped",
                "reason": "already_imported",
                "archive_sha256": digest,
                "report_count": len(recorded),
            }
        logger.warning(
            "Built-in report state matches the archive but %d report(s) are missing "
            "from the database; importing again",
            len(missing),
        )

    result = await import_reports(
        archive,
        ImportOptions(
            operator=operator,
            source_name=DEFAULT_SOURCE_NAME,
            declared_verified=True,
            build_cases=True,
            index=True,
            # 一线运维沉淀的真实报告，字段不全都属于可接受的采集差异：
            # 放行后缺失项会写进案例的适用范围，不静默丢弃。
            allow_incomplete=True,
        ),
    )
    active_ids = [
        item.report_id
        for item in result.items
        if item.report_id
        and item.status in {STATUS_IMPORTED, STATUS_DUPLICATE}
        and REPORT_ID_RE.match(item.report_id)
    ]
    failures = [
        {"file": item.original_name, "error": item.error or item.status}
        for item in result.items
        if item.status not in {STATUS_IMPORTED, STATUS_DUPLICATE}
    ]

    superseded: list[dict[str, Any]] = []
    if supersede:
        stale = [rid for rid in state.get("report_ids") or [] if rid not in set(active_ids)]
        for report_id in stale:
            try:
                superseded.append(await supersede_report(report_id, operator))
            except Exception as exc:  # noqa: BLE001 - keep the rest of the set consistent
                logger.exception("supersede failed for %s", report_id)
                failures.append({"file": report_id, "error": f"supersede_failed: {exc}"})

    status = STATUS_COMPLETED if not failures else STATUS_PARTIAL
    _write_state(
        state_path,
        {
            "version": STATE_VERSION,
            "archive": archive.name,
            "archive_sha256": digest,
            "status": status,
            "imported_at": local_now().strftime("%Y-%m-%d %H:%M:%S"),
            "operator": operator,
            "report_ids": active_ids,
            "failures": failures,
            "summary": result.summary,
            "superseded": superseded,
        },
    )
    return {
        "status": status,
        "archive_sha256": digest,
        "report_count": len(active_ids),
        "failures": failures,
        "superseded": superseded,
        "summary": result.summary,
    }


async def sync_builtin_reports_locked(
    archive: Path,
    state_path: Path,
    operator: str,
    *,
    force: bool = False,
    supersede: bool = True,
) -> dict[str, Any]:
    """Serialize the sync across replicas sharing one database."""
    async with PGManager.connection() as connection:
        acquired = (
            await connection.execute(
                text("SELECT pg_try_advisory_xact_lock(:key)"),
                {"key": ARCHIVE_LOCK_KEY},
            )
        ).scalar()
        if not acquired:
            return {"status": STATUS_BUSY, "reason": "another_instance_importing"}
        return await sync_builtin_reports(
            archive, state_path, operator, force=force, supersede=supersede
        )
