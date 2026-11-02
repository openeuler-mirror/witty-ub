# Copyright (c) Huawei Technologies Co., Ltd. 2023-2025. All rights reserved.
"""Historical report import (P3-1..P3-3).

A batch validates historical report JSON (single file or zip), renders HTML
with the report-generation Skill renderer, writes ``<report_id>.html`` plus the
original JSON sidecar into the report volume root, records batch audit rows,
optionally confirms the reports and builds confirmed cases.

The renderer is an external Skill script: the backend image never depends on
Jinja2, so the CLI runs it as a subprocess with a Python that has ``jinja2``.
"""
from __future__ import annotations

import asyncio
import copy
import json
import logging
import os
import re
import shutil
import stat
import subprocess
import sys
import tempfile
import uuid
import zipfile
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import Any

from latency.common.local_time import local_now
from latency.database.managers.diag_case_library import DiagCaseLibraryPGManager
from latency.database.managers.phenomenon_index import PhenomenonIndexPGManager
from latency.database.managers.report_import import ReportImportPGManager
from latency.exceptions import BaseBizException
from latency.schemas.diag_case_library import ConfirmDiagCaseRequest
from latency.services import report_phenomenon
from latency.services.diag_case_library import DiagCaseLibraryService
from latency.services.diagnostic_report import (
    HISTORICAL_REPORT_PREFIX,
    report_root,
)
from latency.services.report_case_draft import build_draft_from_fault
from latency.services.report_review import ReportReviewService

logger = logging.getLogger(__name__)

MAX_ZIP_ENTRIES = 500
MAX_ITEM_BYTES = 5 * 1024 * 1024
MAX_BATCH_BYTES = 64 * 1024 * 1024
RENDER_TIMEOUT_SECONDS = 120
RENDERER_RELATIVE_PATH = (
    "witty_ub_diagnostician/skills/diagnostic-report-generation/scripts/render_report.py"
)

STATUS_IMPORTED = "imported"
STATUS_DUPLICATE = "duplicate"
STATUS_FAILED = "failed"

# 导入质量旁注（渲染期校验问题）；独立文件，不参与 sidecar_hash。
QUALITY_SUFFIX = ".import.json"

CASE_CONFIRMED = "confirmed"
CASE_DRAFT = "draft"
CASE_SKIPPED = "skipped"
CASE_EXISTING = "existing"


class ImportSourceError(ValueError):
    """The input file or zip cannot be imported as-is."""

    def __init__(self, code: str, detail: str = ""):
        self.code = code
        self.detail = detail
        super().__init__(f"{code}: {detail}" if detail else code)


class ImportRenderError(RuntimeError):
    """The Skill renderer is missing or rejected one report."""

    def __init__(self, code: str, detail: str = ""):
        self.code = code
        self.detail = detail
        super().__init__(f"{code}: {detail}" if detail else code)


@dataclass(slots=True)
class ImportEntry:
    name: str
    data: bytes


@dataclass(slots=True)
class ImportOptions:
    operator: str
    source_name: str | None = None
    declared_verified: bool = False
    # 批量建案是显式动作：CLI 在 --declared-verified 且未 --no-cases 时打开。
    build_cases: bool = False
    keep_draft: bool = False
    index: bool = True
    # 一线采集的真实数据可能缺字段：显式允许后，校验失败降级渲染、
    # 缺必填摘要的结论仍然建案，缺什么由 data_quality 记录，不静默丢弃。
    allow_incomplete: bool = False


@dataclass(slots=True)
class CaseOutcome:
    fault_id: str
    status: str
    case_id: str | None = None
    case_no: str | None = None
    reason: str | None = None
    missing_fields: list[str] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        return {
            "fault_id": self.fault_id,
            "status": self.status,
            "case_id": self.case_id,
            "case_no": self.case_no,
            "reason": self.reason,
            "missing_fields": list(self.missing_fields),
        }


@dataclass(slots=True)
class ImportItemResult:
    original_name: str
    status: str
    report_id: str | None = None
    content_hash: str | None = None
    report_meta_id: str | None = None
    error: str | None = None
    fault_count: int = 0
    eligible_case_count: int = 0
    report_confirmed: bool = False
    cases: list[CaseOutcome] = field(default_factory=list)
    # 放行不完整数据时渲染器报出的校验问题，随结果返回并写入侧车。
    render_warnings: list[str] = field(default_factory=list)

    def case_counts(self) -> dict[str, int]:
        counts = {
            CASE_CONFIRMED: 0,
            CASE_DRAFT: 0,
            CASE_SKIPPED: 0,
            CASE_EXISTING: 0,
        }
        for outcome in self.cases:
            counts[outcome.status] = counts.get(outcome.status, 0) + 1
        return counts

    def as_dict(self) -> dict[str, Any]:
        return {
            "original_name": self.original_name,
            "status": self.status,
            "report_id": self.report_id,
            "content_hash": self.content_hash,
            "report_meta_id": self.report_meta_id,
            "error": self.error,
            "fault_count": self.fault_count,
            "eligible_case_count": self.eligible_case_count,
            "report_confirmed": self.report_confirmed,
            "render_warnings": list(self.render_warnings),
            "case_counts": self.case_counts(),
            "cases": [outcome.as_dict() for outcome in self.cases],
        }


@dataclass(slots=True)
class ImportBatchResult:
    batch_id: str
    status: str
    imported_by: str
    declared_verified: bool
    file_count: int
    summary: dict[str, Any]
    items: list[ImportItemResult]

    def degraded_summary(self) -> dict[str, Any]:
        """放行不完整数据产生的降级，供调用方明确暴露而不是静默放过。

        分两层：报告层（渲染期校验问题）与案例层（缺建案字段）。
        """
        reports = [
            {"report_id": item.report_id, "warnings": list(item.render_warnings)}
            for item in self.items
            if item.render_warnings
        ]
        cases = [
            {"report_id": item.report_id, **outcome.as_dict()}
            for item in self.items
            for outcome in item.cases
            if outcome.missing_fields
        ]
        return {
            "report_count": len(reports),
            "reports": reports,
            "case_count": len(cases),
            "cases": cases,
        }


def _text(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _clip(value: Any, limit: int) -> str | None:
    """Fit a report-provided string into its index column without losing the file."""
    text = _text(value)
    return text[:limit] if text is not None else None


def derive_report_id(original_name: str, payload: dict[str, Any]) -> tuple[str, str]:
    """Content-addressed report ID: same bytes → same ID, edited content → new ID."""
    content_hash = report_phenomenon.compute_sidecar_hash(payload)
    return (
        f"{HISTORICAL_REPORT_PREFIX}{content_hash}",
        content_hash,
    )

def normalize_import_payload(payload: dict[str, Any]) -> dict[str, Any]:
    """Assign a stable imported fault ID while preserving the original in .source.json."""
    if isinstance(payload.get("faults"), list) and payload["faults"]:
        return payload
    if not isinstance(payload.get("conclusion"), dict):
        return payload
    normalized = copy.deepcopy(payload)
    fault = {
        key: copy.deepcopy(payload[key])
        for key in ("conclusion", "root_cause", "solution", "evidence_traces",
                    "knowledge_matches", "confidence", "severity")
        if key in payload
    }
    fault.update(
        id="F01",
        title=(payload.get("report") or {}).get("title"),
        status=payload.get("status") or "suspected",
        category=payload.get("fault_type") or payload.get("category") or "unknown",
    )
    normalized["faults"] = [fault]
    normalized["import_normalization"] = {
        "version": 1, "original_layout": "flat", "assigned_fault_ids": ["F01"],
    }
    return normalized


def _unsafe_zip_name(name: str) -> bool:
    normalized = name.replace("\\", "/")
    if normalized.startswith("/") or re.match(r"^[A-Za-z]:", normalized):
        return True
    return any(part == ".." for part in normalized.split("/") if part)


def _junk_entry(name: str) -> bool:
    parts = name.replace("\\", "/").split("/")
    return any(
        part.startswith("._") or part == "__MACOSX" for part in parts if part
    )


def collect_json_entries(source: Path) -> list[ImportEntry]:
    """Return the JSON entries of a file or zip, rejecting unsafe archives."""
    if not source.is_file():
        raise ImportSourceError("source_not_found", str(source))

    if source.suffix.lower() == ".json":
        if source.stat().st_size > MAX_ITEM_BYTES:
            raise ImportSourceError("item_too_large", source.name)
        return [ImportEntry(name=source.name, data=source.read_bytes())]

    if source.suffix.lower() != ".zip":
        raise ImportSourceError("source_unsupported", source.suffix or source.name)

    entries: list[ImportEntry] = []
    total = 0
    try:
        archive = zipfile.ZipFile(source)
    except (OSError, zipfile.BadZipFile) as exc:
        raise ImportSourceError("zip_invalid", str(exc)) from exc
    with archive:
        if len(archive.infolist()) > MAX_ZIP_ENTRIES:
            raise ImportSourceError("zip_too_many_entries", str(MAX_ZIP_ENTRIES))
        for info in archive.infolist():
            if info.is_dir() or _junk_entry(info.filename):
                continue
            if not info.filename.lower().endswith(".json"):
                continue
            if _unsafe_zip_name(info.filename):
                raise ImportSourceError("zip_entry_traversal", info.filename)
            if stat.S_ISLNK(info.external_attr >> 16):
                raise ImportSourceError("zip_entry_symlink", info.filename)
            if len(entries) >= MAX_ZIP_ENTRIES:
                raise ImportSourceError(
                    "zip_too_many_entries", str(MAX_ZIP_ENTRIES)
                )
            if info.file_size > MAX_ITEM_BYTES:
                raise ImportSourceError("item_too_large", info.filename)
            # Read one byte past the cap so a forged header cannot blow memory.
            try:
                with archive.open(info) as stream:
                    data = stream.read(MAX_ITEM_BYTES + 1)
            except (OSError, RuntimeError, zipfile.BadZipFile, NotImplementedError) as exc:
                raise ImportSourceError("zip_entry_unreadable", info.filename) from exc
            if len(data) > MAX_ITEM_BYTES:
                raise ImportSourceError("item_too_large", info.filename)
            total += len(data)
            if total > MAX_BATCH_BYTES:
                raise ImportSourceError(
                    "zip_uncompressed_too_large", str(MAX_BATCH_BYTES)
                )
            entries.append(ImportEntry(name=info.filename, data=data))

    if not entries:
        raise ImportSourceError("no_json_entries", source.name)
    entries.sort(key=lambda entry: entry.name)
    return entries


@lru_cache(maxsize=4)
def _render_python() -> str:
    candidates = [
        os.environ.get("WITTY_REPORT_RENDER_PYTHON"),
        sys.executable,
        shutil.which("python3"),
    ]
    for candidate in candidates:
        if not candidate:
            continue
        try:
            probe = subprocess.run(
                [candidate, "-c", "import jinja2"],
                capture_output=True,
                timeout=20,
                check=False,
            )
        except (OSError, subprocess.SubprocessError):
            continue
        if probe.returncode == 0:
            return candidate
    raise ImportRenderError(
        "render_python_missing",
        "需要带 jinja2 的 python3；可用 WITTY_REPORT_RENDER_PYTHON 指定",
    )


@lru_cache(maxsize=4)
def _renderer_path() -> Path:
    override = os.environ.get("WITTY_REPORT_RENDERER")
    if override:
        path = Path(override).expanduser()
        if path.is_file():
            return path
        raise ImportRenderError("renderer_not_found", str(path))
    relative = Path(RENDERER_RELATIVE_PATH)
    for start in (Path(__file__).resolve(), Path.cwd().resolve()):
        for parent in (start, *start.parents):
            candidate = parent / relative
            if candidate.is_file():
                return candidate
    from latency.services.label_taxonomy import taxonomy_path
    taxonomy = taxonomy_path()
    if taxonomy is not None:
        candidate = taxonomy.parent.parent / "scripts" / "render_report.py"
        if candidate.is_file():
            return candidate
    raise ImportRenderError(
        "renderer_not_found",
        "未在仓库内找到报告渲染器；可用 WITTY_REPORT_RENDERER 指定",
    )


def _render_report_html(
    payload: dict[str, Any], out_html: Path, *, allow_incomplete: bool = False
) -> list[str]:
    renderer = _renderer_path()
    python = _render_python()
    with tempfile.TemporaryDirectory(prefix="witty-report-import-") as tmp:
        data_path = Path(tmp) / "report.json"
        data_path.write_text(
            json.dumps(payload, ensure_ascii=False), encoding="utf-8"
        )
        try:
            proc = subprocess.run(
                [
                    python,
                    str(renderer),
                    str(data_path),
                    str(out_html),
                    "--no-sidecar",
                    *(["--allow-incomplete"] if allow_incomplete else []),
                ],
                capture_output=True,
                text=True,
                timeout=RENDER_TIMEOUT_SECONDS,
                check=False,
            )
        except (OSError, subprocess.SubprocessError) as exc:
            raise ImportRenderError("renderer_failed", str(exc)) from exc
    if proc.returncode != 0:
        lines = [
            line.strip()
            for line in (proc.stderr or proc.stdout or "").splitlines()
            if line.strip()
        ]
        raise ImportRenderError(
            "renderer_rejected",
            " | ".join(lines[-3:]) or f"exit {proc.returncode}",
        )
    # 放行模式下渲染器把校验问题降级为 ⚠ 提示；收集起来随报告一起落盘，
    # 保证「数据不完整」这件事有据可查，而不是只在构建日志里一闪而过。
    warnings = [
        line[1:].strip()
        for line in (proc.stderr or "").splitlines()
        if line.startswith("⚠") or line.strip().startswith("- ")
    ]
    return [item for item in warnings if item]


def _read_sidecar_hash(path: Path) -> str | None:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    if not isinstance(payload, dict):
        return None
    return report_phenomenon.compute_sidecar_hash(payload)


def _write_atomic(path: Path, content: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    handle, temp_name = tempfile.mkstemp(
        prefix=f".{path.stem}.", suffix=".tmp", dir=str(path.parent)
    )
    temp_path = Path(temp_name)
    try:
        with os.fdopen(handle, "wb") as stream:
            stream.write(content)
        os.replace(temp_path, path)
    except BaseException:
        temp_path.unlink(missing_ok=True)
        raise


def _eligible_fault_ids(payload: dict[str, Any]) -> list[str]:
    faults = report_phenomenon.normalise_faults(payload)
    ids = report_phenomenon.stable_fault_ids(payload)
    eligible: list[str] = []
    for fault, fault_id in zip(faults, ids, strict=False):
        if fault_id.startswith("auto:"):
            continue
        if str(fault.get("status") or "").lower() == "excluded":
            continue
        eligible.append(fault_id)
    return eligible


async def _build_cases(
    report_id: str,
    payload: dict[str, Any],
    content_hash: str,
    options: ImportOptions,
) -> list[CaseOutcome]:
    outcomes: list[CaseOutcome] = []
    faults = report_phenomenon.normalise_faults(payload)
    fault_ids = report_phenomenon.stable_fault_ids(payload)
    for fault, fault_id in zip(faults, fault_ids, strict=False):
        if str(fault.get("status") or "").lower() == "excluded":
            outcomes.append(
                CaseOutcome(fault_id=fault_id, status=CASE_SKIPPED, reason="fault_excluded")
            )
            continue
        if fault_id.startswith("auto:"):
            outcomes.append(
                CaseOutcome(
                    fault_id=fault_id,
                    status=CASE_SKIPPED,
                    reason="missing_stable_fault_id",
                )
            )
            continue
        try:
            preview = build_draft_from_fault(
                report_id, payload, fault_id, content_hash
            )
        except ValueError as exc:
            outcomes.append(
                CaseOutcome(fault_id=fault_id, status=CASE_SKIPPED, reason=str(exc))
            )
            continue
        if preview.labels.get("status") in {"invalid", "unavailable"}:
            outcomes.append(
                CaseOutcome(
                    fault_id=fault_id,
                    status=CASE_SKIPPED,
                    reason=str(preview.labels.get("error") or "label_invalid"),
                )
            )
            continue
        # 缺必填摘要默认跳过；显式允许不完整数据时仍建案，摘要由 fallback 派生，
        # 缺哪几个字段写进 data_quality，避免与字段齐全的案例混为一谈。
        degraded_fields = [
            name
            for name in ("symptom_summary", "root_cause_summary")
            if name in preview.missing_fields
        ]
        if degraded_fields and not options.allow_incomplete:
            outcomes.append(
                CaseOutcome(
                    fault_id=fault_id,
                    status=CASE_SKIPPED,
                    reason="missing_required_fields",
                    missing_fields=list(preview.missing_fields),
                )
            )
            continue

        existing = await DiagCaseLibraryPGManager.find_active_bound_case(
            report_id,
            fault_id,
            preview.source_fault_hash,
            preview.labels.get("first_level_label"),
            preview.labels.get("second_level_label"),
        )
        if not options.keep_draft:
            if existing is not None and existing.verification_json is not None and existing.verification_json.closed_loop:
                outcomes.append(CaseOutcome(
                    fault_id=fault_id, status=CASE_EXISTING,
                    case_id=existing.id, case_no=existing.case_no,
                ))
                continue
            try:
                verified = await DiagCaseLibraryService.verify_report_fault(
                    report_id, fault_id, content_hash, options.operator,
                    "导入人声明来源结论已完成实操验证",
                    "外部已验证资料导入声明",
                    confirmation_source="import",
                )
                if verified.case is None:
                    raise ImportSourceError("verified_case_missing")
                outcomes.append(CaseOutcome(
                    fault_id=fault_id, status=CASE_CONFIRMED,
                    case_id=verified.case.id, case_no=verified.case.case_no,
                    missing_fields=list(preview.missing_fields),
                ))
            except BaseBizException as exc:
                outcomes.append(CaseOutcome(
                    fault_id=fault_id, status=CASE_SKIPPED,
                    reason=f"{exc.message}: {exc.detail}",
                    missing_fields=list(preview.missing_fields),
                ))
            continue
        case_id: str | None = None
        case_no: str | None = None
        case_status = CASE_DRAFT
        try:
            if existing is not None:
                case_id = existing.id
                case_no = existing.case_no
                case_status = existing.status
            else:
                created = await DiagCaseLibraryService.create_report_case(
                    preview, options.operator
                )
                case_id = created.case_id
                case_no = created.case_no
        except BaseBizException as exc:
            outcomes.append(
                CaseOutcome(
                    fault_id=fault_id,
                    status=CASE_SKIPPED,
                    reason=f"{exc.message}: {exc.detail}".strip(": "),
                    missing_fields=list(preview.missing_fields),
                )
            )
            continue

        if options.keep_draft:
            outcomes.append(
                CaseOutcome(
                    fault_id=fault_id,
                    status=CASE_DRAFT,
                    case_id=case_id,
                    case_no=case_no,
                    missing_fields=list(preview.missing_fields),
                )
            )
            continue
        if case_status == "confirmed":
            outcomes.append(
                CaseOutcome(
                    fault_id=fault_id,
                    status=CASE_EXISTING,
                    case_id=case_id,
                    case_no=case_no,
                )
            )
            continue
        if preview.ready and case_id:
            try:
                await DiagCaseLibraryService.confirm_case(
                    case_id,
                    ConfirmDiagCaseRequest(confirmed_by=options.operator),
                    confirmation_source="import",
                )
            except BaseBizException as exc:
                outcomes.append(
                    CaseOutcome(
                        fault_id=fault_id,
                        status=CASE_DRAFT,
                        case_id=case_id,
                        case_no=case_no,
                        reason=f"confirm_failed: {exc.message} {exc.detail}".strip(),
                        missing_fields=list(preview.missing_fields),
                    )
                )
                continue
            outcomes.append(
                CaseOutcome(
                    fault_id=fault_id,
                    status=CASE_CONFIRMED,
                    case_id=case_id,
                    case_no=case_no,
                )
            )
        else:
            outcomes.append(
                CaseOutcome(
                    fault_id=fault_id,
                    status=CASE_DRAFT,
                    case_id=case_id,
                    case_no=case_no,
                    missing_fields=list(preview.missing_fields),
                )
            )
    return outcomes


async def _import_one(
    entry: ImportEntry, options: ImportOptions
) -> ImportItemResult:
    try:
        payload = json.loads(entry.data.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        return ImportItemResult(
            original_name=entry.name,
            status=STATUS_FAILED,
            error=f"invalid_json: {exc}",
        )
    if not isinstance(payload, dict):
        return ImportItemResult(
            original_name=entry.name,
            status=STATUS_FAILED,
            error="invalid_json: root_must_be_object",
        )

    original_payload = payload
    report_id, content_hash = derive_report_id(entry.name, original_payload)
    root = report_root()
    for existing_id in await ReportImportPGManager.reports_for_content(content_hash):
        if (root / f"{existing_id}.html").is_file() and (root / f"{existing_id}.json").is_file():
            report_id = existing_id
            break
    payload = normalize_import_payload(original_payload)
    sidecar_hash = report_phenomenon.compute_sidecar_hash(payload)
    html_path = root / f"{report_id}.html"
    sidecar_path = root / f"{report_id}.json"
    report = payload.get("report") if isinstance(payload.get("report"), dict) else {}
    basic = (
        payload.get("basic_info") if isinstance(payload.get("basic_info"), dict) else {}
    )
    faults = report_phenomenon.normalise_faults(payload)

    result = ImportItemResult(
        original_name=entry.name,
        status=STATUS_IMPORTED,
        report_id=report_id,
        content_hash=content_hash,
        report_meta_id=_text(report.get("report_id")),
        fault_count=len(faults),
        eligible_case_count=len(_eligible_fault_ids(payload)),
    )

    duplicate = (
        html_path.is_file()
        and sidecar_path.is_file()
        and _read_sidecar_hash(sidecar_path) == sidecar_hash
    )
    if duplicate:
        result.status = STATUS_DUPLICATE
    else:
        temp_html = root / f".{report_id}.{uuid.uuid4().hex[:8]}.html.tmp"
        try:
            warnings = await asyncio.to_thread(
                _render_report_html,
                original_payload,
                temp_html,
                allow_incomplete=options.allow_incomplete,
            )
            if warnings:
                result.render_warnings = list(warnings)
            _write_atomic(root / f"{report_id}.source.json", entry.data)
            # 导入质量单独落盘：侧车内容参与 sidecar_hash，混进去会让已确认的
            # 同一份报告在下次导入时被判成「版本已变化」。
            if warnings:
                _write_atomic(
                    root / f"{report_id}{QUALITY_SUFFIX}",
                    json.dumps(
                        {"render_warnings": list(warnings)}, ensure_ascii=False
                    ).encode("utf-8"),
                )
            _write_atomic(sidecar_path, json.dumps(payload, ensure_ascii=False).encode("utf-8"))
            os.replace(temp_html, html_path)
        except ImportRenderError as exc:
            temp_html.unlink(missing_ok=True)
            result.status = STATUS_FAILED
            result.error = f"{exc.code}: {exc.detail}".strip(": ")
            return result
        except OSError as exc:
            temp_html.unlink(missing_ok=True)
            result.status = STATUS_FAILED
            result.error = f"write_failed: {exc}"
            return result

    if not duplicate or await PhenomenonIndexPGManager.get_report_index(report_id) is None:
        # Historical metadata can exceed the index column widths (operation text
        # is free-form); clip to keep the audit row from aborting the import.
        try:
            await PhenomenonIndexPGManager.upsert_report_index(
                {
                    "report_id": report_id,
                    "report_meta_id": _clip(result.report_meta_id, 128),
                    "kb_id": None,
                    "kb_name": None,
                    "title": _text(report.get("title")),
                    "generated_at": _clip(report.get("generated_at"), 32),
                    "operation": report_phenomenon.fault_operation(payload),
                    "time_range_start": _clip(basic.get("time_range_start"), 32),
                    "time_range_end": _clip(basic.get("time_range_end"), 32),
                    "fault_count": len(faults) or None,
                    "sidecar_hash": sidecar_hash,
                    "index_status": "pending",
                    "index_error": None,
                    "report_available": True,
                }
            )
        except Exception as exc:  # noqa: BLE001 - indexing can heal the row later
            logger.exception("report index metadata failed for %s", report_id)
            suffix = f"metadata_failed: {type(exc).__name__}: {exc}"
            result.error = f"{result.error} | {suffix}" if result.error else suffix

    await ReportImportPGManager.detach_historical_assets(report_id)
    if options.declared_verified:
        try:
            row = await PhenomenonIndexPGManager.get_report_index(report_id)
            if getattr(row, "confirmed_sidecar_hash", None) == sidecar_hash:
                # Already confirmed for this exact version: keep the original audit time.
                result.report_confirmed = True
            else:
                await ReportReviewService.confirm(
                    report_id,
                    sidecar_hash,
                    options.operator,
                    confirmation_source="import",
                )
                result.report_confirmed = True
        except Exception as exc:  # noqa: BLE001 - one report must not abort the batch
            result.error = f"confirm_failed: {exc}".strip()

    if (
        result.report_confirmed
        and options.build_cases
        and result.status in {STATUS_IMPORTED, STATUS_DUPLICATE}
    ):
        try:
            result.cases = await _build_cases(
                report_id, payload, sidecar_hash, options
            )
        except Exception as exc:  # noqa: BLE001 - keep the imported report auditable
            logger.exception("case build failed for %s", report_id)
            suffix = f"cases_failed: {type(exc).__name__}: {exc}"
            result.error = f"{result.error} | {suffix}" if result.error else suffix
    return result


def _batch_status(items: list[ImportItemResult]) -> str:
    failed = sum(1 for item in items if item.status == STATUS_FAILED)
    if failed == 0:
        return "partial" if any(item.error or any(
            case.status in {CASE_DRAFT, CASE_SKIPPED} for case in item.cases
        ) for item in items) else "completed"
    return "failed" if failed == len(items) else "partial"


async def import_reports(
    source: Path, options: ImportOptions
) -> ImportBatchResult:
    if options.build_cases and not options.declared_verified:
        raise ValueError("批量建案需要先声明该批报告已验证")
    oper = (options.operator or "").strip()
    if not oper:
        raise ValueError("导入人不能为空")
    if len(oper) > 64:
        raise ValueError("导入人最多 64 个字符")
    options = ImportOptions(
        operator=oper,
        source_name=options.source_name,
        declared_verified=options.declared_verified,
        build_cases=options.build_cases,
        keep_draft=options.keep_draft,
        index=options.index,
        allow_incomplete=options.allow_incomplete,
    )

    entries = collect_json_entries(source)
    batch_id = f"rib_{local_now():%Y%m%d%H%M%S}_{uuid.uuid4().hex[:8]}"
    await ReportImportPGManager.create_batch(
        batch_id=batch_id,
        imported_by=options.operator,
        source_name=options.source_name or source.name,
        file_count=len(entries),
        declared_verified=options.declared_verified,
        build_cases=options.build_cases,
    )

    results: list[ImportItemResult] = []
    for entry in entries:
        try:
            result = await _import_one(entry, options)
        except Exception as exc:  # noqa: BLE001 - keep the batch audit complete
            logger.exception("report import failed for %s", entry.name)
            result = ImportItemResult(
                original_name=entry.name,
                status=STATUS_FAILED,
                error=f"internal_error: {type(exc).__name__}: {exc}",
            )
        results.append(result)
        await ReportImportPGManager.add_item(
            {
                "batch_id": batch_id,
                "original_name": result.original_name,
                "report_id": result.report_id,
                "content_hash": result.content_hash,
                "report_meta_id": result.report_meta_id,
                "status": result.status,
                "error": result.error,
                "fault_count": result.fault_count,
                "eligible_case_count": result.eligible_case_count,
                "report_confirmed": result.report_confirmed,
                "case_result_json": [outcome.as_dict() for outcome in result.cases],
            }
        )

    if options.index:
        from latency.services.phenomenon_index import PhenomenonIndexService

        for result in results:
            if result.report_id is None or result.status == STATUS_FAILED:
                continue
            try:
                await PhenomenonIndexService.index_scope(
                    "report", report_id=result.report_id
                )
            except Exception as exc:  # noqa: BLE001 - indexing is retryable
                logger.exception("report index queue failed for %s", result.report_id)
                suffix = f"index_failed: {type(exc).__name__}: {exc}"
                result.error = f"{result.error} | {suffix}" if result.error else suffix

    summary = {
        "imported": sum(1 for item in results if item.status == STATUS_IMPORTED),
        "duplicate": sum(1 for item in results if item.status == STATUS_DUPLICATE),
        "failed": sum(1 for item in results if item.status == STATUS_FAILED),
        "reports_confirmed": sum(1 for item in results if item.report_confirmed),
        "cases": {
            key: sum(item.case_counts().get(key, 0) for item in results)
            for key in (CASE_CONFIRMED, CASE_DRAFT, CASE_SKIPPED, CASE_EXISTING)
        },
    }
    status = _batch_status(results)
    await ReportImportPGManager.finish_batch(batch_id, status, summary)
    return ImportBatchResult(
        batch_id=batch_id,
        status=status,
        imported_by=options.operator,
        declared_verified=options.declared_verified,
        file_count=len(entries),
        summary=summary,
        items=results,
    )
