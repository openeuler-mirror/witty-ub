# Copyright (c) Huawei Technologies Co., Ltd. 2023-2025. All rights reserved.
"""Service layer for the supernode diagnosis case library."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy.exc import IntegrityError

from latency.ENUM.case_library import DiagCaseSource, DiagCaseStatus
from latency.common.local_time import WALL_CLOCK_TZ, local_now
from latency.database.managers.diag_case_library import DiagCaseLibraryPGManager
from latency.exceptions import (
    BadRequestBizException,
    ConflictBizException,
    NotFoundBizException,
    UnprocessableBizException,
)
from latency.services import label_taxonomy, report_phenomenon
from latency.services.report_case_draft import CaseDraftPreview
from latency.services.report_review import (
    ReportReviewService,
    require_operator,
    trusted_operator_required,
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
    SourceReportModel,
    UpdateDiagCaseRequest,
)

RESOURCE_NAME = "诊断案例"


def _local_verification_time(value: str) -> str:
    """Convert an offset-aware client timestamp to the deployment wall clock.

    Naive legacy values are kept as-is so historical records stay readable.
    """
    text = value.strip()
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return text
    if parsed.tzinfo is None:
        return text
    return parsed.astimezone(WALL_CLOCK_TZ).strftime("%Y-%m-%d %H:%M:%S")


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
    async def _resolve_binding(req: CreateDiagCaseDraftRequest):
        """Validate a report-derived binding through the report review gate.

        Returns ``None`` for independent cases. Classification is always copied
        from the confirmed fault, never accepted from the client.
        """
        if not (req.report_id and req.source_fault_id):
            return None
        snapshot = await ReportReviewService.require_confirmed(
            req.report_id, req.expected_sidecar_hash
        )
        payload = snapshot.payload or {}
        try:
            extraction = report_phenomenon.extract_report(
                req.report_id, payload, kb_dir=snapshot.kb_dir
            )
        except report_phenomenon.PhenomenonContentError as exc:
            raise BadRequestBizException(
                message="报告故障绑定校验失败", detail=exc.code
            ) from exc
        doc = next(
            (
                item
                for item in extraction.faults
                if item.source_fault_id == req.source_fault_id
            ),
            None,
        )
        if doc is None:
            raise BadRequestBizException(
                message="报告故障绑定校验失败",
                detail="fault_not_found_or_excluded",
            )
        if doc.source_fault_id.startswith("auto:"):
            raise BadRequestBizException(
                message="报告故障ID不稳定，不能绑定案例",
                detail="请先为源报告补齐稳定的 faults[].id",
            )
        fault = ReportReviewService.find_fault(payload, doc.source_fault_id)
        if fault is None:
            raise BadRequestBizException(
                message="报告故障绑定校验失败", detail="fault_not_found"
            )
        labels = ReportReviewService.labels_from_fault(fault)
        if labels.get("label_status") in {"invalid", "unavailable"}:
            raise UnprocessableBizException(
                message="故障分类不可用",
                detail=str(labels.get("label_error") or "label_invalid"),
            )
        taxonomy_version = str(labels.get("label_taxonomy_version") or "")
        if not taxonomy_version:
            raise UnprocessableBizException(
                message="故障分类不可用", detail="label_taxonomy_unavailable"
            )
        snapshot_hash = label_taxonomy.label_snapshot_hash(
            labels.get("first_level_label"),
            labels.get("second_level_label"),
            taxonomy_version,
        )
        return {
            "doc": doc,
            "labels": labels,
            "snapshot_hash": snapshot_hash,
            "sidecar_hash": snapshot.sidecar_hash,
        }

    @staticmethod
    def _independent_labels(req: CreateDiagCaseDraftRequest):
        if not (req.first_level_label or req.second_level_label):
            return None
        try:
            validation = label_taxonomy.validate_labels(
                req.first_level_label, req.second_level_label
            )
        except label_taxonomy.TaxonomyError as exc:
            raise UnprocessableBizException(
                message="分类字典不可用", detail=str(exc)
            ) from exc
        if validation.status == "invalid":
            raise BadRequestBizException(
                message="分类不合法", detail=str(validation.error)
            )
        version = validation.taxonomy_version or ""
        return {
            "first_level_label": validation.first_level_label,
            "second_level_label": validation.second_level_label,
            "label_taxonomy_version": version,
            "source_label_hash": label_taxonomy.label_snapshot_hash(
                validation.first_level_label,
                validation.second_level_label,
                version,
            ),
        }

    @staticmethod
    async def create_draft(
        req: CreateDiagCaseDraftRequest,
    ) -> CreateDiagCaseDraftMsg:
        binding = await DiagCaseLibraryService._resolve_binding(req)
        case = DiagCaseLibraryModel.model_validate(
            req.model_dump(exclude={"expected_sidecar_hash"})
        )
        case.status = DiagCaseStatus.DRAFT
        if binding is not None:
            case.report_id = req.report_id
            case.source_fault_id = binding["doc"].source_fault_id
            case.source_fault_hash = binding["doc"].source_fault_hash
            case.source_sidecar_hash = binding["sidecar_hash"]
            case.first_level_label = binding["labels"].get("first_level_label")
            case.second_level_label = binding["labels"].get("second_level_label")
            case.label_taxonomy_version = str(
                binding["labels"].get("label_taxonomy_version") or ""
            ) or None
            case.source_label_hash = binding["snapshot_hash"]
        elif (labels := DiagCaseLibraryService._independent_labels(req)) is not None:
            case.first_level_label = labels["first_level_label"]
            case.second_level_label = labels["second_level_label"]
            case.label_taxonomy_version = labels["label_taxonomy_version"] or None
            case.source_label_hash = labels["source_label_hash"]
        if binding is not None:
            # 文件与 DB 无共同事务：落库前再核对一次页面所示版本。
            await ReportReviewService.require_confirmed(
                req.report_id, req.expected_sidecar_hash
            )
        try:
            case_id = await DiagCaseLibraryPGManager.add_draft(case)
        except IntegrityError as exc:
            existing = None
            if binding is not None:
                existing = await DiagCaseLibraryPGManager.find_active_bound_case(
                    req.report_id or "",
                    binding["doc"].source_fault_id or "",
                    binding["doc"].source_fault_hash or "",
                    case.first_level_label,
                    case.second_level_label,
                )
            detail = (
                f"已有案例 case_id={existing.id}, case_no={existing.case_no}"
                if existing is not None
                else "同一报告故障的同一版本已存在活跃案例"
            )
            raise ConflictBizException(
                message="案例绑定冲突", detail=detail
            ) from exc
        if binding is not None:
            # 插入期间侧车若被改写，撤回本次草稿，不发布成功结果。
            try:
                await ReportReviewService.require_confirmed(
                    req.report_id, req.expected_sidecar_hash
                )
            except Exception:
                if case_id:
                    await DiagCaseLibraryPGManager.delete_case(case_id)
                raise
        return CreateDiagCaseDraftMsg(case_id=case_id or None, case_no=case.case_no)

    @staticmethod
    async def create_report_case(
        preview: CaseDraftPreview, operator: str
    ) -> CreateDiagCaseDraftMsg:
        """Create a draft from a server-built preview; labels are not client input."""
        payload = dict(preview.draft)
        payload.pop("verification_history_json", None)
        payload.update(
            {
                "report_id": preview.report_id,
                "source_fault_id": preview.source_fault_id,
                "expected_sidecar_hash": preview.expected_sidecar_hash,
                "created_by": operator,
            }
        )
        req = CreateDiagCaseDraftRequest.model_validate(payload)
        return await DiagCaseLibraryService.create_draft(req)

    @staticmethod
    async def _case_message(case: DiagCaseLibraryModel) -> GetDiagCaseMsg:
        """Case detail plus source navigation, shared by every detail response."""
        try:
            source = await ReportReviewService.describe_case_source(case)
        except Exception:  # noqa: BLE001 - navigation must not hide the case
            source = {
                "status": "unavailable",
                "report_id": case.report_id,
                "source_fault_id": case.source_fault_id,
                "classification_status": "unavailable",
            }
        return GetDiagCaseMsg(
            case=case,
            source_report=SourceReportModel.model_validate(source),
        )

    @staticmethod
    async def get_case(case_id: str) -> GetDiagCaseMsg:
        case = await DiagCaseLibraryPGManager.get_case(case_id)
        if case is None:
            raise NotFoundBizException(resource=RESOURCE_NAME)
        return await DiagCaseLibraryService._case_message(case)

    @staticmethod
    async def update_case(
        case_id: str,
        req: UpdateDiagCaseRequest,
        operator_header: str | None = None,
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
        expected_revision = patch.pop("expected_revision", None)
        if "verification_json" in patch and expected_revision is None:
            raise BadRequestBizException(
                message="缺少案例版本",
                detail="验证回填必须携带页面所见的 expected_revision",
            )
        if expected_revision is not None and int(expected_revision) != case.revision:
            raise ConflictBizException(
                message="案例已被其他操作更新",
                detail=(
                    f"页面 revision={expected_revision}，当前 revision={case.revision}；"
                    "请刷新后重试"
                ),
            )
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

        if "verification_json" in patch:
            verification = updated.verification_json
            now = local_now().strftime("%Y-%m-%d %H:%M:%S")
            if verification is not None and (verification.verified_at or "").strip():
                # 客户端可传带时区的 ISO 时间；库内统一存部署墙钟。
                verification.verified_at = _local_verification_time(
                    verification.verified_at
                )
            if verification is not None and verification.closed_loop:
                missing = [
                    name
                    for name, value in (
                        ("method", verification.method),
                        ("observed_result", verification.observed_result),
                        ("verified_by", verification.verified_by),
                    )
                    if not (value or "").strip()
                ]
                if missing:
                    raise BadRequestBizException(
                        message="验证闭环信息不完整",
                        detail=f"closed_loop=true 缺少：{', '.join(missing)}",
                    )
                if not (verification.verified_at or "").strip():
                    verification.verified_at = now
            actor: str | None = None
            if verification is not None and (
                verification.verified_by or verification.closed_loop
            ):
                # 受控审核部署下，操作人只认认证网关注入的请求头。
                actor = require_operator(verification.verified_by, operator_header)
                verification.verified_by = actor
            elif trusted_operator_required():
                # 撤回、清空或未闭环记录同样是验证写操作，也必须证明身份。
                actor = require_operator(None, operator_header)
                if verification is not None:
                    verification.verified_by = actor
            old = case.verification_json
            new = updated.verification_json
            if (old or new) and old != new:
                history = list(case.verification_history_json or [])
                history.append(
                    {
                        "revision_from": case.revision,
                        "revision_to": case.revision + 1,
                        "verified_by": (
                            actor
                            or (
                                new.verified_by
                                if new is not None
                                else (old.verified_by if old is not None else None)
                            )
                        ),
                        "verified_at": (
                            new.verified_at
                            if new is not None and new.verified_at
                            else now
                        ),
                        "method": new.method if new is not None else None,
                        "observed_result": (
                            new.observed_result if new is not None else None
                        ),
                        "closed_loop": bool(new.closed_loop) if new is not None else False,
                    }
                )
                updated.verification_history_json = history

        if updated.source in (
            DiagCaseSource.COMMUNITY,
            DiagCaseSource.ONLINE,
        ) and not (updated.source_url or "").strip():
            raise BadRequestBizException(
                message="缺少 source_url",
                detail="source 为 community / online 时 source_url 必填",
            )

        revision_kwargs = (
            {"expected_revision": expected_revision}
            if expected_revision is not None
            else {}
        )
        if case.status == DiagCaseStatus.CONFIRMED:
            ok = await DiagCaseLibraryPGManager.update_verification(
                case_id, updated, **revision_kwargs
            )
        else:
            ok = await DiagCaseLibraryPGManager.update_draft(
                case_id, updated, **revision_kwargs
            )
        if not ok:
            raise ConflictBizException(
                message="案例更新冲突",
                detail="案例状态或 revision 已变化，请刷新后重试",
            )
        refreshed = await DiagCaseLibraryPGManager.get_case(case_id)
        return await DiagCaseLibraryService._case_message(refreshed)

    @staticmethod
    async def confirm_case(
        case_id: str,
        req: ConfirmDiagCaseRequest,
        operator_header: str | None = None,
    ) -> GetDiagCaseMsg:
        case = await DiagCaseLibraryPGManager.get_case(case_id)
        if case is None:
            raise NotFoundBizException(resource=RESOURCE_NAME)
        operator = require_operator(req.confirmed_by, operator_header)

        if case.report_id and case.source_fault_id:
            if not case.source_sidecar_hash:
                raise ConflictBizException(
                    message="案例缺少建案时报告版本",
                    detail="旧草稿没有保存报告审核版本，请按当前已确认版本重新建案",
                )
            snapshot = await ReportReviewService.require_confirmed(
                case.report_id, case.source_sidecar_hash
            )
            payload = snapshot.payload or {}
            try:
                extraction = report_phenomenon.extract_report(
                    case.report_id, payload, kb_dir=snapshot.kb_dir
                )
            except report_phenomenon.PhenomenonContentError as exc:
                raise ConflictBizException(
                    message="源报告故障已不可校验", detail=exc.code
                ) from exc
            doc = next(
                (
                    item
                    for item in extraction.faults
                    if item.source_fault_id == case.source_fault_id
                ),
                None,
            )
            if doc is None:
                raise ConflictBizException(
                    message="源报告故障已不可校验",
                    detail="fault_not_found_or_excluded",
                )
            if doc.source_fault_hash != case.source_fault_hash:
                raise ConflictBizException(
                    message="源报告版本已变更",
                    detail="故障指纹与建案时不一致，请归档后按新版本重新建案",
                )
            if case.source_label_hash:
                fault = ReportReviewService.find_fault(
                    payload, case.source_fault_id
                )
                labels = (
                    ReportReviewService.labels_from_fault(fault)
                    if fault is not None
                    else {}
                )
                version = str(labels.get("label_taxonomy_version") or "")
                current_label_hash = (
                    label_taxonomy.label_snapshot_hash(
                        labels.get("first_level_label"),
                        labels.get("second_level_label"),
                        version,
                    )
                    if version
                    else None
                )
                if current_label_hash != case.source_label_hash:
                    raise ConflictBizException(
                        message="源报告分类已变更",
                        detail="故障分类快照与建案时不一致，请归档后按新版本重新建案",
                    )

        errors = DiagCaseLibraryService._confirm_gate_errors(case, operator)
        if errors:
            detail = "; ".join(errors)
            if case.status != DiagCaseStatus.DRAFT:
                raise ConflictBizException(
                    message=f"诊断案例当前状态为 {case.status}，仅 draft 可确认",
                    detail=detail,
                )
            raise BadRequestBizException(message="确认闸门未通过", detail=detail)

        await DiagCaseLibraryPGManager.confirm_case(
            case_id, operator, req.confidence
        )
        updated = await DiagCaseLibraryPGManager.get_case(case_id)
        return await DiagCaseLibraryService._case_message(updated)

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
            return await DiagCaseLibraryService._case_message(case)

        await DiagCaseLibraryPGManager.archive_case(
            case_id, req.archived_by, req.archive_reason
        )
        updated = await DiagCaseLibraryPGManager.get_case(case_id)
        return await DiagCaseLibraryService._case_message(updated)

    @staticmethod
    async def search_cases(
        req: SearchDiagCaseLibraryRequest,
    ) -> SearchDiagCasesMsg:
        if req.second_level_label and not req.first_level_label:
            raise BadRequestBizException(
                message="二级分类筛选缺少一级",
                detail="second_level_label 必须与 first_level_label 同时使用",
            )
        total, matches = await DiagCaseLibraryPGManager.search_cases(req)
        sources = await ReportReviewService.describe_case_sources(
            [match.case for match in matches]
        )
        for match, source in zip(matches, sources, strict=False):
            match.source_report = SourceReportModel.model_validate(source)
        return SearchDiagCasesMsg(total=total, matches=matches)

    @staticmethod
    async def mark_hit(case_id: str) -> GetDiagCaseMsg:
        case = await DiagCaseLibraryPGManager.get_case(case_id)
        if case is None:
            raise NotFoundBizException(resource=RESOURCE_NAME)
        await DiagCaseLibraryPGManager.mark_hit(case_id)
        updated = await DiagCaseLibraryPGManager.get_case(case_id)
        return GetDiagCaseMsg(case=updated)