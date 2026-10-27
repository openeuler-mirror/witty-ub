# Copyright (c) Huawei Technologies Co., Ltd. 2023-2025. All rights reserved.
"""Human confirmation of a whole report and source navigation for cases.

Confirmation is stored in PostgreSQL next to the report index row and never
written back to the sidecar, so reviewing a report cannot change its hash.
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from latency.common.local_time import local_now
from latency.database.managers.phenomenon_index import PhenomenonIndexPGManager
from latency.exceptions import (
    BadRequestBizException,
    ConflictBizException,
    NotFoundBizException,
    UnprocessableBizException,
)
from latency.services import label_taxonomy, report_phenomenon
from latency.services.diagnostic_report import DiagnosticReportService, report_root

STATUS_UNCONFIRMED = "unconfirmed"
STATUS_CONFIRMED = "confirmed"
STATUS_STALE = "stale"
STATUS_UNAVAILABLE = "unavailable"

SOURCE_VALID = "valid"
SOURCE_STALE = "stale"
SOURCE_DELETED = "deleted"
SOURCE_UNAVAILABLE = "unavailable"
SOURCE_INDEPENDENT = "independent"

MAX_OPERATOR_LENGTH = 64
TRUSTED_OPERATOR_ENV = "WITTY_REQUIRE_TRUSTED_OPERATOR"


def trusted_operator_required() -> bool:
    """Whether this deployment accepts operators only from the auth gateway."""
    return (os.environ.get(TRUSTED_OPERATOR_ENV) or "").strip().lower() in {
        "1",
        "true",
        "yes",
    }


def _as_dict(value: Any) -> dict:
    return value if isinstance(value, dict) else {}


@dataclass(slots=True)
class ReportSnapshot:
    report_id: str
    kb_dir: str | None
    html: Path
    payload: dict[str, Any] | None
    sidecar_hash: str | None
    sidecar_state: str
    title: str | None


def require_operator(value: str | None, header_value: str | None = None) -> str:
    """Resolve the audit operator.

    Default deployments accept the frontend-supplied value with the gateway
    header taking precedence. When ``WITTY_REQUIRE_TRUSTED_OPERATOR`` is on,
    only the header injected by the trusted gateway is accepted so a direct
    API caller cannot forge a human review record.
    """
    if trusted_operator_required():
        operator = (header_value or "").strip()
        if not operator:
            raise BadRequestBizException(
                message="缺少可信操作人",
                detail=(
                    "部署已启用受控审核入口，操作人必须由认证网关注入 "
                    "X-Witty-Operator"
                ),
            )
    else:
        operator = (header_value or value or "").strip()
    if not operator:
        raise BadRequestBizException(
            message="缺少操作人",
            detail="报告确认和验证回填必须填写操作人",
        )
    if len(operator) > MAX_OPERATOR_LENGTH:
        raise BadRequestBizException(
            message="操作人过长",
            detail=f"操作人最多 {MAX_OPERATOR_LENGTH} 个字符",
        )
    return operator


class ReportReviewService:
    @staticmethod
    def _unique_report(report_id: str) -> ReportSnapshot:
        matches: list[tuple[str | None, Path]] = [
            (kb_dir, html)
            for kb_dir, html in DiagnosticReportService._iter_report_files(report_root())
            if html.stem == report_id
        ]
        if not matches:
            raise NotFoundBizException(
                resource=f"诊断报告 {report_id}",
                detail=f"报告文件不在 {report_root()} 下（或已被清理）",
            )
        if len(matches) > 1:
            raise ConflictBizException(
                message="报告ID不唯一",
                detail="多个知识库目录存在同名报告，无法确定审核目标",
            )
        kb_dir, html = matches[0]
        try:
            resolved = html.resolve()
            resolved.relative_to(report_root().resolve())
        except (OSError, ValueError) as exc:
            raise BadRequestBizException(
                message="报告路径非法", detail=str(exc)
            ) from exc
        sidecar = resolved.with_suffix(".json")
        sidecar_state = "ok"
        payload: dict[str, Any] | None = None
        if not sidecar.is_file():
            sidecar_state = "missing"
        else:
            try:
                parsed = json.loads(sidecar.read_text(encoding="utf-8"))
                payload = parsed if isinstance(parsed, dict) else None
            except (OSError, ValueError):
                payload = None
            if payload is None:
                sidecar_state = "invalid"
        sidecar_hash = (
            report_phenomenon.compute_sidecar_hash(payload)
            if payload is not None
            else None
        )
        report = _as_dict((payload or {}).get("report"))
        title = report.get("title") if isinstance(report.get("title"), str) else None
        return ReportSnapshot(
            report_id=report_id,
            kb_dir=kb_dir,
            html=resolved,
            payload=payload,
            sidecar_hash=sidecar_hash,
            sidecar_state=sidecar_state,
            title=title,
        )

    @staticmethod
    async def review_status(
        report_id: str, snapshot: ReportSnapshot | None = None
    ) -> dict[str, Any]:
        current = snapshot or ReportReviewService._unique_report(report_id)
        row = await PhenomenonIndexPGManager.get_report_index(report_id)
        if current.sidecar_state != "ok":
            status = STATUS_UNAVAILABLE
        elif row is None or not row.confirmed_sidecar_hash:
            status = STATUS_UNCONFIRMED
        elif row.confirmed_sidecar_hash != current.sidecar_hash:
            status = STATUS_STALE
        else:
            status = STATUS_CONFIRMED
        return {
            "review_status": status,
            "current_sidecar_hash": current.sidecar_hash,
            "review_confirmed_by": row.confirmed_by if row is not None else None,
            "review_confirmed_at": row.confirmed_at if row is not None else None,
            "review_confirmation_source": (
                getattr(row, "confirmation_source", None) if row is not None else None
            ),
        }

    @staticmethod
    async def confirm(
        report_id: str,
        expected_sidecar_hash: str,
        operator: str,
        *,
        confirmation_source: str = "review",
    ) -> dict[str, Any]:
        current = ReportReviewService._unique_report(report_id)
        if current.sidecar_state != "ok" or current.sidecar_hash is None:
            raise UnprocessableBizException(
                message="报告数据不完整",
                detail=(
                    "sidecar_missing: 侧车 JSON 不存在"
                    if current.sidecar_state == "missing"
                    else "sidecar_invalid: 侧车 JSON 损坏或超限"
                ),
            )
        if current.sidecar_hash != expected_sidecar_hash:
            raise ConflictBizException(
                message="报告版本已变化",
                detail="页面所见版本与当前侧车不一致，请刷新后重新确认",
            )
        confirmed_at = local_now()
        await PhenomenonIndexPGManager.upsert_report_index(
            {
                "report_id": report_id,
                "sidecar_hash": current.sidecar_hash,
                "confirmed_by": operator,
                "confirmed_at": confirmed_at,
                "confirmed_sidecar_hash": current.sidecar_hash,
                "confirmation_source": confirmation_source,
                "report_available": True,
            }
        )
        return await ReportReviewService.review_status(report_id, current)

    @staticmethod
    async def require_confirmed(
        report_id: str,
        expected_sidecar_hash: str | None = None,
    ) -> ReportSnapshot:
        current = ReportReviewService._unique_report(report_id)
        if current.sidecar_state != "ok" or current.sidecar_hash is None:
            raise UnprocessableBizException(
                message="报告数据不完整",
                detail=(
                    "sidecar_missing: 侧车 JSON 不存在"
                    if current.sidecar_state == "missing"
                    else "sidecar_invalid: 侧车 JSON 损坏或超限"
                ),
            )
        if expected_sidecar_hash and current.sidecar_hash != expected_sidecar_hash:
            raise ConflictBizException(
                message="报告版本已变化",
                detail="页面所见版本与当前侧车不一致，请刷新后重试",
            )
        state = await ReportReviewService.review_status(report_id, current)
        if state["review_status"] != STATUS_CONFIRMED:
            raise ConflictBizException(
                message="报告尚未确认",
                detail=(
                    "报告当前版本未经过人工确认，不能派生案例"
                    if state["review_status"] == STATUS_UNCONFIRMED
                    else "报告版本已变化，需要重新人工确认"
                ),
            )
        return current

    @staticmethod
    def labels_from_fault(fault: dict[str, Any]) -> dict[str, Any]:
        conclusion = _as_dict(fault.get("conclusion"))
        try:
            validation = label_taxonomy.validate_labels(
                conclusion.get("first_level_label"),
                conclusion.get("second_level_label"),
            )
        except label_taxonomy.TaxonomyError:
            return {
                "first_level_label": None,
                "second_level_label": None,
                "label_status": "unavailable",
                "label_error": "label_taxonomy_unavailable",
                "label_taxonomy_version": None,
            }
        return {
            "first_level_label": validation.first_level_label,
            "second_level_label": validation.second_level_label,
            "label_status": validation.status,
            "label_error": validation.error,
            "label_taxonomy_version": validation.taxonomy_version,
        }

    @staticmethod
    def find_fault(payload: dict[str, Any], fault_id: str) -> dict[str, Any] | None:
        for fault in report_phenomenon.normalise_faults(payload):
            if str(fault.get("id") or "") == fault_id:
                return fault
        return None

    @staticmethod
    async def describe_case_source(
        case: Any,
        current: ReportSnapshot | None = None,
        extraction: Any = None,
    ) -> dict[str, Any]:
        """Navigation metadata; never treats an attachment as a report source.

        ``current`` / ``extraction`` let list responses share one report scan
        across every case bound to the same report.
        """
        report_id = getattr(case, "report_id", None)
        fault_id = getattr(case, "source_fault_id", None)
        if not report_id or not fault_id:
            return {
                "status": SOURCE_INDEPENDENT,
                "report_id": None,
                "source_fault_id": None,
                "report_title": None,
                "source_fault_title": None,
                "review_status": None,
                "classification_status": "unclassified",
                "get_report": None,
                "get_fault": None,
            }
        if current is None:
            try:
                current = ReportReviewService._unique_report(report_id)
            except NotFoundBizException:
                return {
                    "status": SOURCE_DELETED,
                    "report_id": report_id,
                    "source_fault_id": fault_id,
                    "report_title": None,
                    "source_fault_title": None,
                    "review_status": None,
                    "classification_status": "unavailable",
                    "get_report": None,
                    "get_fault": None,
                }
            except (ConflictBizException, BadRequestBizException):
                return {
                    "status": SOURCE_UNAVAILABLE,
                    "report_id": report_id,
                    "source_fault_id": fault_id,
                    "report_title": None,
                    "source_fault_title": None,
                    "review_status": None,
                    "classification_status": "unavailable",
                    "get_report": None,
                    "get_fault": None,
                }
        if current.sidecar_state != "ok" or current.payload is None:
            return {
                "status": SOURCE_UNAVAILABLE,
                "report_id": report_id,
                "source_fault_id": fault_id,
                "report_title": current.title,
                "source_fault_title": None,
                "review_status": STATUS_UNAVAILABLE,
                "classification_status": "unavailable",
                "get_report": None,
                "get_fault": None,
            }
        fault = ReportReviewService.find_fault(current.payload, fault_id)
        if fault is None:
            return {
                "status": SOURCE_STALE,
                "report_id": report_id,
                "source_fault_id": fault_id,
                "report_title": current.title,
                "source_fault_title": None,
                "review_status": STATUS_STALE,
                "classification_status": "unavailable",
                "get_report": None,
                "get_fault": None,
            }
        if extraction is None:
            try:
                extraction = report_phenomenon.extract_report(
                    report_id, current.payload, kb_dir=current.kb_dir
                )
            except Exception:  # noqa: BLE001 - navigation must not fail browsing
                extraction = False
        doc = None
        if extraction:
            doc = next(
                (item for item in extraction.faults if item.source_fault_id == fault_id),
                None,
            )
        labels = ReportReviewService.labels_from_fault(fault)
        current_label_hash = None
        if labels.get("label_taxonomy_version"):
            current_label_hash = label_taxonomy.label_snapshot_hash(
                labels.get("first_level_label"),
                labels.get("second_level_label"),
                str(labels["label_taxonomy_version"]),
            )
        stored_label_hash = getattr(case, "source_label_hash", None)
        classification_status = "unclassified"
        if stored_label_hash and current_label_hash:
            classification_status = (
                "valid" if stored_label_hash == current_label_hash else "changed"
            )
        elif stored_label_hash:
            classification_status = "unavailable"
        source_valid = bool(
            doc is not None
            and doc.source_fault_hash == getattr(case, "source_fault_hash", None)
        )
        if classification_status == "changed":
            source_valid = False
        review = await ReportReviewService.review_status(report_id, current)
        return {
            "status": SOURCE_VALID if source_valid else SOURCE_STALE,
            "report_id": report_id,
            "source_fault_id": fault_id,
            "report_title": current.title,
            "source_fault_title": fault.get("title"),
            "review_status": review["review_status"],
            "classification_status": classification_status,
            "current_sidecar_hash": current.sidecar_hash,
            "current_first_level_label": labels.get("first_level_label"),
            "current_second_level_label": labels.get("second_level_label"),
            "get_report": (
                f"/diagnostic_report/{report_id}" if source_valid else None
            ),
            "get_fault": (
                f"/diagnostic_report/{report_id}/faults/{fault_id}"
                if source_valid
                else None
            ),
        }

    @staticmethod
    async def describe_case_sources(cases: list[Any]) -> list[dict[str, Any]]:
        """Resolve source navigation for a page of cases with one scan per report."""
        snapshots: dict[str, Any] = {}
        extractions: dict[str, Any] = {}
        sources: list[dict[str, Any]] = []
        for case in cases:
            report_id = getattr(case, "report_id", None)
            if not report_id or not getattr(case, "source_fault_id", None):
                sources.append(await ReportReviewService.describe_case_source(case))
                continue
            if report_id not in snapshots:
                try:
                    snapshots[report_id] = ReportReviewService._unique_report(report_id)
                except (
                    NotFoundBizException,
                    ConflictBizException,
                    BadRequestBizException,
                ) as exc:
                    snapshots[report_id] = exc
            current = snapshots[report_id]
            if isinstance(current, Exception):
                sources.append(await ReportReviewService.describe_case_source(case))
                continue
            if report_id not in extractions and current.sidecar_state == "ok":
                try:
                    extractions[report_id] = report_phenomenon.extract_report(
                        report_id, current.payload, kb_dir=current.kb_dir
                    )
                except Exception:  # noqa: BLE001 - navigation must not fail browsing
                    extractions[report_id] = False
            sources.append(
                await ReportReviewService.describe_case_source(
                    case, current=current, extraction=extractions.get(report_id)
                )
            )
        return sources
