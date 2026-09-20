# Copyright (c) Huawei Technologies Co., Ltd. 2023-2025. All rights reserved.
"""Service layer for the supernode diagnosis case library."""
from __future__ import annotations

from latency.ENUM.case_library import DiagCaseStatus
from latency.database.managers.diag_case_library import DiagCaseLibraryPGManager
from latency.exceptions import (
    BadRequestBizException,
    ConflictBizException,
    NotFoundBizException,
)
from latency.schemas.diag_case_library import (
    ArchiveDiagCaseRequest,
    ConfirmDiagCaseRequest,
    CreateDiagCaseDraftMsg,
    CreateDiagCaseDraftRequest,
    DiagCaseLibraryModel,
    GetDiagCaseMsg,
    SearchDiagCaseLibraryRequest,
    SearchDiagCasesMsg,
)

RESOURCE_NAME = "诊断案例"


class DiagCaseLibraryService:
    """Orchestrates the draft → confirmed → archived gate."""

    @staticmethod
    def _confirm_gate_errors(
        case: DiagCaseLibraryModel,
        confirmed_by: str | None = None,
    ) -> list[str]:
        """§4.2 确认闸门：返回所有未满足项（空列表表示可确认）。"""
        errors: list[str] = []
        if case.status != DiagCaseStatus.DRAFT:
            errors.append(f"当前状态为 {case.status}，仅 draft 可确认")
        if not case.evidence_json:
            errors.append("缺少 evidence_json（证据锚点）")
        if not case.remediation_json:
            errors.append("缺少 remediation_json（分步处置）")
        verification = case.verification_json
        if verification is None or not (verification.observed_result or "").strip():
            errors.append("缺少 verification_json.observed_result（验证闭环）")
        matchable = [
            signal
            for signal in DiagCaseLibraryPGManager._signals_for_case(case)
            if signal.signal_type != DiagCaseLibraryPGManager.OPERATION_SIGNAL
        ]
        if not matchable:
            errors.append(
                "缺少可匹配信号（status_codes / failure_mode_ids / latency_components / "
                "log_keywords / hosts / pods / IP / cluster_name 至少一项非空）"
            )
        if not (confirmed_by or "").strip():
            errors.append("缺少 confirmed_by（确认人标识）")
        return errors

    @staticmethod
    async def create_draft(
        req: CreateDiagCaseDraftRequest,
    ) -> CreateDiagCaseDraftMsg:
        case = DiagCaseLibraryModel.model_validate(req.model_dump())
        case.status = DiagCaseStatus.DRAFT
        case_id = await DiagCaseLibraryPGManager.add_draft(case)
        return CreateDiagCaseDraftMsg(case_id=case_id or None, case_no=case.case_no)

    @staticmethod
    async def get_case(case_id: str) -> GetDiagCaseMsg:
        case = await DiagCaseLibraryPGManager.get_case(case_id)
        if case is None:
            raise NotFoundBizException(resource=RESOURCE_NAME)
        return GetDiagCaseMsg(case=case)

    @staticmethod
    async def confirm_case(
        case_id: str,
        req: ConfirmDiagCaseRequest,
    ) -> GetDiagCaseMsg:
        case = await DiagCaseLibraryPGManager.get_case(case_id)
        if case is None:
            raise NotFoundBizException(resource=RESOURCE_NAME)

        errors = DiagCaseLibraryService._confirm_gate_errors(case, req.confirmed_by)
        if errors:
            detail = "; ".join(errors)
            if case.status != DiagCaseStatus.DRAFT:
                raise ConflictBizException(
                    message=f"诊断案例当前状态为 {case.status}，仅 draft 可确认",
                    detail=detail,
                )
            raise BadRequestBizException(message="确认闸门未通过", detail=detail)

        await DiagCaseLibraryPGManager.confirm_case(
            case_id, req.confirmed_by, req.confidence
        )
        updated = await DiagCaseLibraryPGManager.get_case(case_id)
        return GetDiagCaseMsg(case=updated)

    @staticmethod
    async def archive_case(
        case_id: str,
        req: ArchiveDiagCaseRequest,
    ) -> GetDiagCaseMsg:
        case = await DiagCaseLibraryPGManager.get_case(case_id)
        if case is None:
            raise NotFoundBizException(resource=RESOURCE_NAME)
        if case.status == DiagCaseStatus.ARCHIVED:
            # 已归档案例幂等返回，不重复写留痕。
            return GetDiagCaseMsg(case=case)

        await DiagCaseLibraryPGManager.archive_case(
            case_id, req.archived_by, req.archive_reason
        )
        updated = await DiagCaseLibraryPGManager.get_case(case_id)
        return GetDiagCaseMsg(case=updated)

    @staticmethod
    async def search_cases(
        req: SearchDiagCaseLibraryRequest,
    ) -> SearchDiagCasesMsg:
        total, matches = await DiagCaseLibraryPGManager.search_cases(req)
        return SearchDiagCasesMsg(total=total, matches=matches)

    @staticmethod
    async def mark_hit(case_id: str) -> GetDiagCaseMsg:
        case = await DiagCaseLibraryPGManager.get_case(case_id)
        if case is None:
            raise NotFoundBizException(resource=RESOURCE_NAME)
        await DiagCaseLibraryPGManager.mark_hit(case_id)
        updated = await DiagCaseLibraryPGManager.get_case(case_id)
        return GetDiagCaseMsg(case=updated)