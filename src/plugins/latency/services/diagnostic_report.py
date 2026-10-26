# Copyright (c) Huawei Technologies Co., Ltd. 2023-2025. All rights reserved.
"""Service layer for the diagnostic report library (``/diagnostic_report``).

Reports are written by the ``diagnostic-report-generation`` skill into
``$WITTY_REPORT_DIR`` as ``<kb_id>/report_<kb_id>_<ts>.html`` plus a sidecar
``.json`` holding the original rendering payload. This module only reads that
directory tree — nothing here touches the database (design document
``docs/design/diagnostic-report-library.md`` §5 / §6).
"""
from __future__ import annotations

import json
import logging
import os
import re
from pathlib import Path
from typing import Any, Iterator, Optional

from sqlalchemy import select

from latency.ENUM.phenomenon import BindingStatus, VerificationLevel
from latency.database.engine import PGManager
from latency.database.managers.phenomenon_index import PhenomenonIndexPGManager
from latency.database.models import DiagCaseLibrary
from latency.exceptions import (
    BadRequestBizException,
    NotFoundBizException,
    UnprocessableBizException,
)
from latency.schemas.diagnostic_report import (
    DiagnosticCaseRefModel,
    DiagnosticReportDetailItem,
    DiagnosticReportItem,
    GetDiagnosticReportFaultMsg,
    GetDiagnosticReportMsg,
    ListDiagnosticReportsMsg,
    ListDiagnosticReportsRequest,
)
from latency.services import report_phenomenon as phenomenon_extractor

logger = logging.getLogger(__name__)

# 与 render_report.py 的 FALLBACK_OUT_DIR 保持同一条兜底规则，才能保证
# 「agent 写到哪」与「服务读哪」永远一致：容器内由 entrypoint 注入
# WITTY_REPORT_DIR=/var/witty-ub/reports，未注入时两边都回落 /tmp/reports。
FALLBACK_REPORT_DIR = Path("/tmp/reports")
REPORT_SUFFIX = ".html"
REPORT_PREFIX = "report_"
KB_SLUG_FALLBACK = "unknown"
_UNSAFE_SLUG = re.compile(r"[^A-Za-z0-9_-]")

RESOURCE_NAME = "诊断报告"


def report_root() -> Path:
    """报告根目录：运行时读 WITTY_REPORT_DIR，未设置时回落 /tmp/reports。"""
    return Path(os.environ.get("WITTY_REPORT_DIR") or FALLBACK_REPORT_DIR)


def kb_slug(kb_id: Any) -> str:
    """知识库 ID → 报告目录名（与 render_report.py 的清洗规则一致）。"""
    slug = _UNSAFE_SLUG.sub("_", str(kb_id or "").strip())
    return slug or KB_SLUG_FALLBACK


def _opt_str(value: Any) -> Optional[str]:
    """空值统一收敛成 None，避免前端拿到空字符串占位。"""
    return None if value in (None, "") else str(value)


def _fault_count(data: dict) -> Optional[int]:
    """故障数：多故障取 faults 长度，扁平单故障取 conclusion.fault_count。"""
    faults = data.get("faults")
    if isinstance(faults, list) and faults:
        return len(faults)
    conclusion = data.get("conclusion")
    if isinstance(conclusion, dict):
        count = conclusion.get("fault_count")
        return count if isinstance(count, int) and count > 0 else 1
    return None


def _fault_stats(data: Optional[dict]) -> tuple[Optional[int], Optional[int]]:
    """Return ``(indexable_fault_count, confirmed_fault_count)``."""
    if not data:
        return None, None
    faults = data.get("faults")
    if isinstance(faults, list) and faults:
        indexable = 0
        confirmed = 0
        for fault in faults:
            if not isinstance(fault, dict):
                continue
            status = str(fault.get("status") or "suspected").lower()
            if status == "excluded":
                continue
            indexable += 1
            if status == "confirmed":
                confirmed += 1
        return indexable, confirmed
    if isinstance(data.get("conclusion"), dict):
        confirmed = 1 if str(data.get("status") or "").lower() == "confirmed" else 0
        return 1, confirmed
    return None, None


def _fault_hashes(report_id: str, data: Optional[dict]) -> dict[str, str]:
    """Current source-fault fingerprints keyed by stable fault ID."""
    if not data:
        return {}
    try:
        extraction = phenomenon_extractor.extract_report(report_id, data)
    except Exception:  # noqa: BLE001 - metadata decoration must not fail
        return {}
    return {
        doc.source_fault_id: doc.source_fault_hash
        for doc in extraction.faults
        if doc.source_fault_id and doc.source_fault_hash
    }


def _case_verification(case: DiagCaseLibrary) -> str:
    if case.status != "confirmed":
        return VerificationLevel.SUSPECTED.value
    verification = case.verification_json or {}
    closed_loop = (
        bool(verification.get("closed_loop"))
        if isinstance(verification, dict)
        else bool(getattr(verification, "closed_loop", False))
    )
    return (
        VerificationLevel.VERIFIED.value
        if closed_loop
        else VerificationLevel.CONFIRMED_UNVERIFIED.value
    )


class DiagnosticReportService:
    """Read-only view over the report directory tree."""

    # ---------------------------------------------------------------- 目录扫描
    @staticmethod
    def _iter_report_files(root: Path) -> Iterator[tuple[Optional[str], Path]]:
        """产出 ``(kb 目录名, HTML 路径)``。

        布局固定为 ``<kb_id>/report_*.html``；根目录下直接摆放的
        ``report_*.html`` 也收（手工搬运历史报告的场景，知识库归属未知）。
        """
        if not root.is_dir():
            return
        try:
            entries = sorted(root.iterdir())
        except OSError:
            return
        for entry in entries:
            if entry.is_dir():
                for html in sorted(entry.glob(f"{REPORT_PREFIX}*{REPORT_SUFFIX}")):
                    yield entry.name, html
            elif entry.is_file() and entry.name.startswith(REPORT_PREFIX) and entry.suffix == REPORT_SUFFIX:
                yield None, entry

    @staticmethod
    def _collect(root: Path, kb_filter: Optional[str]) -> list[tuple[float, Optional[str], Path]]:
        """扫描 + 过滤 + 按修改时间倒序（排序只用 stat，不解析侧车）。"""
        rows: list[tuple[float, Optional[str], Path]] = []
        for kb_dir, html in DiagnosticReportService._iter_report_files(root):
            if kb_filter and kb_dir != kb_filter:
                continue
            try:
                mtime = html.stat().st_mtime
            except OSError:
                continue
            rows.append((mtime, kb_dir, html))
        rows.sort(key=lambda row: row[0], reverse=True)
        return rows

    # ---------------------------------------------------------------- 侧车读取
    @staticmethod
    def _read_sidecar(path: Path) -> Optional[dict]:
        """读取侧车 JSON；缺失或损坏一律返回 None（单条降级，不影响整体列表）。"""
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return None
        return payload if isinstance(payload, dict) else None

    @staticmethod
    def _build_item(
        kb_dir: Optional[str],
        html: Path,
        data: Optional[dict] = None,
        *,
        read_sidecar: bool = True,
    ) -> DiagnosticReportItem:
        try:
            file_size = html.stat().st_size
        except OSError:
            file_size = 0
        item = DiagnosticReportItem(
            report_id=html.stem,
            kb_id=kb_dir,
            file_name=html.name,
            file_size=file_size,
            has_sidecar=False,
        )
        if read_sidecar and data is None:
            data = DiagnosticReportService._read_sidecar(html.with_suffix(".json"))
        if data is None:
            return item

        report = data.get("report")
        report = report if isinstance(report, dict) else {}
        basic = data.get("basic_info")
        basic = basic if isinstance(basic, dict) else {}

        item.has_sidecar = True
        item.kb_id = basic.get("kb_id") or kb_dir
        item.kb_name = _opt_str(basic.get("kb_name"))
        item.title = _opt_str(report.get("title"))
        item.generated_at = _opt_str(report.get("generated_at"))
        item.operation = _opt_str(basic.get("operation") or report.get("operation"))
        item.time_range_start = _opt_str(basic.get("time_range_start"))
        item.time_range_end = _opt_str(basic.get("time_range_end"))
        item.fault_count = _fault_count(data)
        indexable, confirmed = _fault_stats(data)
        item.indexable_fault_count = indexable
        item.confirmed_fault_count = confirmed
        return item

    @staticmethod
    async def _decorate_items(
        items: list[DiagnosticReportItem],
        payloads: dict[str, Optional[dict]],
        *,
        with_case_refs: bool = False,
    ) -> list[DiagnosticReportItem]:
        """Attach index status and case counts; DB failure degrades to unknown."""
        details: list[DiagnosticReportItem] = [
            (
                DiagnosticReportDetailItem.model_validate(item.model_dump())
                if with_case_refs
                else DiagnosticReportItem.model_validate(item.model_dump())
            )
            for item in items
        ]
        if not details:
            return details
        report_ids = [item.report_id for item in details]
        try:
            report_rows = await PhenomenonIndexPGManager.get_report_indexes(report_ids)
            status_counts = (
                await PhenomenonIndexPGManager.card_status_counts_for_reports(
                    report_ids
                )
            )
            async with PGManager.session() as session:
                rows = await session.execute(
                    select(DiagCaseLibrary).where(
                        DiagCaseLibrary.report_id.in_(report_ids),
                        DiagCaseLibrary.existed_status.is_(True),
                    )
                )
                cases = list(rows.scalars().all())
        except Exception:  # noqa: BLE001 - report browsing must stay available
            logger.warning("failed to decorate report index fields", exc_info=True)
            return details

        cases_by_report: dict[str, list[DiagCaseLibrary]] = {}
        for case in cases:
            if case.report_id:
                cases_by_report.setdefault(case.report_id, []).append(case)

        for detail in details:
            row = report_rows.get(detail.report_id)
            if row is not None:
                detail.index_status = row.index_status or "pending"
                detail.index_error = row.index_error
                detail.report_available = bool(row.report_available)
            elif detail.has_sidecar:
                detail.index_status = "pending"
            detail.status_counts = status_counts.get(detail.report_id, {})

            hashes = _fault_hashes(
                detail.report_id, payloads.get(detail.report_id)
            )
            refs: list[DiagnosticCaseRefModel] = []
            case_count = 0
            verified_count = 0
            for case in cases_by_report.get(detail.report_id, []):
                is_current = bool(
                    case.source_fault_hash
                    and hashes.get(case.source_fault_id or "") == case.source_fault_hash
                )
                refs.append(
                    DiagnosticCaseRefModel(
                        case_id=case.id,
                        case_no=case.case_no,
                        source_fault_id=case.source_fault_id,
                        source_fault_hash=case.source_fault_hash,
                        is_current_version=is_current,
                        status=case.status,
                        verification=_case_verification(case),
                        binding_status=(
                            BindingStatus.VALID.value
                            if is_current
                            else BindingStatus.STALE.value
                        ),
                    )
                )
                if case.status == "confirmed" and is_current:
                    case_count += 1
                    if _case_verification(case) == VerificationLevel.VERIFIED.value:
                        verified_count += 1
            detail.case_count = case_count
            detail.verified_case_count = verified_count
            if with_case_refs:
                detail.case_refs = refs  # type: ignore[attr-defined]
        return details

    # ---------------------------------------------------------------- 定位
    @staticmethod
    def _locate(root: Path, report_id: str) -> tuple[Optional[str], Path]:
        """按 report_id 定位 ``(kb 目录名, HTML 路径)``。

        ``report_id`` 已在路由层做过字符集校验（无 ``/`` 与 ``.``），这里再用
        ``resolve()`` 做一次包含性兜底，双保险挡住路径穿越（设计文档 §10）。
        """
        for kb_dir, html in DiagnosticReportService._iter_report_files(root):
            if html.stem != report_id:
                continue
            try:
                resolved = html.resolve()
                resolved.relative_to(root.resolve())
            except (OSError, ValueError) as exc:
                raise BadRequestBizException(
                    message="报告路径非法", detail=f"report_id={report_id}: {exc}"
                ) from exc
            return kb_dir, resolved
        raise NotFoundBizException(
            resource=f"{RESOURCE_NAME} {report_id}",
            detail=f"报告文件不在 {root} 下（或已被清理）",
        )

    # ---------------------------------------------------------------- 对外接口
    @staticmethod
    async def list_reports(req: ListDiagnosticReportsRequest) -> ListDiagnosticReportsMsg:
        root = report_root()
        kb_filter = kb_slug(req.kb_id) if req.kb_id else None
        rows = DiagnosticReportService._collect(root, kb_filter)
        start = (req.page_num - 1) * req.page_cnt
        page = rows[start:start + req.page_cnt]
        items: list[DiagnosticReportItem] = []
        payloads: dict[str, Optional[dict]] = {}
        for _, kb_dir, html in page:
            data = DiagnosticReportService._read_sidecar(html.with_suffix(".json"))
            payloads[html.stem] = data
            items.append(DiagnosticReportService._build_item(kb_dir, html, data))
        if not items:
            return ListDiagnosticReportsMsg(total=len(rows), items=[])
        decorated = await DiagnosticReportService._decorate_items(items, payloads)
        return ListDiagnosticReportsMsg(total=len(rows), items=decorated)

    @staticmethod
    async def get_report(report_id: str) -> GetDiagnosticReportMsg:
        kb_dir, html = DiagnosticReportService._locate(report_root(), report_id)
        data = DiagnosticReportService._read_sidecar(html.with_suffix(".json"))
        item = DiagnosticReportService._build_item(kb_dir, html, data)
        decorated = await DiagnosticReportService._decorate_items(
            [item], {report_id: data}, with_case_refs=True
        )
        return GetDiagnosticReportMsg(report=decorated[0], data=data)

    @staticmethod
    async def get_fault(report_id: str, source_fault_id: str) -> GetDiagnosticReportFaultMsg:
        if len(source_fault_id) > 64 or source_fault_id.startswith("auto:"):
            raise BadRequestBizException(
                message="故障ID不可用于单故障读取",
                detail="合成键没有稳定的故障 ID，请改用完整报告接口",
            )
        kb_dir, html = DiagnosticReportService._locate(report_root(), report_id)
        data = DiagnosticReportService._read_sidecar(html.with_suffix(".json"))
        if data is None:
            raise UnprocessableBizException(
                message="报告数据不完整",
                detail="侧车 JSON 缺失或损坏，无法读取单故障",
            )
        faults = data.get("faults")
        fault = next(
            (
                item
                for item in faults or []
                if isinstance(item, dict) and item.get("id") == source_fault_id
            ),
            None,
        )
        if fault is None:
            raise NotFoundBizException(resource=f"报告故障 {source_fault_id}")
        item = DiagnosticReportService._build_item(kb_dir, html, data)
        decorated = await DiagnosticReportService._decorate_items(
            [item], {report_id: data}, with_case_refs=True
        )
        refs = [
            ref
            for ref in decorated[0].case_refs
            if ref.source_fault_id == source_fault_id
        ]
        return GetDiagnosticReportFaultMsg(
            report=decorated[0], fault=fault, case_refs=refs
        )

    @staticmethod
    async def resolve_html(report_id: str) -> Path:
        _kb_dir, html = DiagnosticReportService._locate(report_root(), report_id)
        return html