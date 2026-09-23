# Copyright (c) Huawei Technologies Co., Ltd. 2023-2025. All rights reserved.
"""Service layer for the supernode diagnosis case library."""
from __future__ import annotations

from latency.ENUM.case_library import DiagCaseSource, DiagCaseStatus
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
    UpdateDiagCaseRequest,
)

RESOURCE_NAME = "诊断案例"


class DiagCaseLibraryService:
    """Orchestrates the draft → confirmed → archived gate."""

    @staticmethod
    def _confirm_gate_errors(
        case: DiagCaseLibraryModel,
        confirmed_by: str | None = None,
    ) -> list[str]:
        """§4.2 确认闸门：返回所有未满足项（空列表表示可确认）。

        闸门只判「报告可信」（人看过并认可），**不判处置是否已闭环**：
        报告出稿时处置尚未执行，要求 `verification_json.observed_result` 非空
        只会迫使 agent 臆造验证记录。验证闭环是正交维度，见 §4.5。
        """
        errors: list[str] = []
        if case.status != DiagCaseStatus.DRAFT:
            errors.append(f"当前状态为 {case.status}，仅 draft 可确认")
        if not case.evidence_json:
            errors.append("缺少 evidence_json（证据锚点）")
        if not case.remediation_json:
            errors.append("缺少 remediation_json（分步处置）")
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
    async def update_case(
        case_id: str,
        req: UpdateDiagCaseRequest,
    ) -> GetDiagCaseMsg:
        """§4.4 / §4.5 局部更新：draft 可改内容物，confirmed 只开放事后验证字段。

        两阶段沉淀链路：报告出稿建草稿 → 人工确认 → 处置执行 + 复测后回填
        `verification_json`（此时案例已是 confirmed，内容物冻结、只放验证字段）。
        """
        case = await DiagCaseLibraryPGManager.get_case(case_id)
        if case is None:
            raise NotFoundBizException(resource=RESOURCE_NAME)
        if case.status == DiagCaseStatus.ARCHIVED:
            raise ConflictBizException(
                message="诊断案例已归档，不可修改",
                detail="archived 案例内容与验证记录均已冻结",
            )

        patch = req.model_dump(mode="json", exclude_unset=True)
        if not patch:
            raise BadRequestBizException(
                message="请求体为空",
                detail="PATCH 需要至少一个待更新字段（未传字段保持原值）",
            )
        if case.status == DiagCaseStatus.CONFIRMED:
            frozen = sorted(
                set(patch) - set(DiagCaseLibraryPGManager.VERIFICATION_COLUMNS)
            )
            if frozen:
                raise ConflictBizException(
                    message="已确认案例的内容物已冻结",
                    detail=(
                        "confirmed 案例只开放 verification_json（处置闭环回填）；"
                        f"不接受修改：{', '.join(frozen)}"
                    ),
                )

        merged = case.model_dump(mode="json")
        merged.update(patch)
        updated = DiagCaseLibraryModel.model_validate(merged)

        if updated.source in (
            DiagCaseSource.COMMUNITY,
            DiagCaseSource.ONLINE,
        ) and not (updated.source_url or "").strip():
            raise BadRequestBizException(
                message="缺少 source_url",
                detail="source 为 community / online 时 source_url 必填",
            )

        if case.status == DiagCaseStatus.CONFIRMED:
            await DiagCaseLibraryPGManager.update_verification(case_id, updated)
        else:
            await DiagCaseLibraryPGManager.update_draft(case_id, updated)
        refreshed = await DiagCaseLibraryPGManager.get_case(case_id)
        return GetDiagCaseMsg(case=refreshed)

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