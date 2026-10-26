# Copyright (c) Huawei Technologies Co., Ltd. 2023-2025. All rights reserved.
"""HTTP API for the diagnostic report library (``/diagnostic_report``).

Agent generated reports land in ``$WITTY_REPORT_DIR`` (persisted by the
``witty-ub-reports`` volume). This router only lists them and hands the
self-contained HTML back to the browser, so a report can be reviewed from the
frontend instead of being copied out of the container by hand.
"""
from typing import Annotated

from fastapi import APIRouter, Body, Header, Path
from starlette.responses import FileResponse

from latency.common.id_validation import DiagnosticReportIdPath
from latency.exceptions import BadRequestBizException, UnprocessableBizException
from latency.schemas.diagnostic_report import (
    ClassificationModel,
    ConfirmDiagnosticReportRequest,
    ConfirmDiagnosticReportResponse,
    CreateCaseFromReportMsg,
    CreateCaseFromReportRequest,
    CreateCaseFromReportResponse,
    GetDiagnosticReportFaultResponse,
    GetDiagnosticReportResponse,
    LabelPairModel,
    LabelTaxonomyMsg,
    LabelTaxonomyResponse,
    ListDiagnosticReportsRequest,
    ListDiagnosticReportsResponse,
    ReindexDiagnosticReportMsg,
    ReindexDiagnosticReportResponse,
    ReportCasePreviewMsg,
    ReportCasePreviewResponse,
)
from latency.services import label_taxonomy
from latency.services.diag_case_library import DiagCaseLibraryService
from latency.services.diagnostic_report import DiagnosticReportService
from latency.services.report_case_draft import build_draft_from_fault
from latency.services.report_review import ReportReviewService, require_operator
from latency.services.phenomenon_index import PhenomenonIndexService


router = APIRouter(prefix="/diagnostic_report", tags=["Diagnostic Report"])


@router.post(
    "/list",
    response_model=ListDiagnosticReportsResponse,
    operation_id="list_diagnostic_reports",
    description=(
        "List generated diagnostic reports, newest first. The listing is read "
        "from the report directory (one sub-directory per knowledge base) and "
        "the sidecar JSON written next to each report supplies title / kb_name / "
        "operation / time range / fault count; a report without a sidecar still "
        "shows up with has_sidecar=false. kb_id is optional: leave it empty to "
        "list reports across knowledge bases."
    ),
)
async def list_diagnostic_reports(
    req: Annotated[ListDiagnosticReportsRequest, Body()],
) -> ListDiagnosticReportsResponse:
    msg = await DiagnosticReportService.list_reports(req)
    return ListDiagnosticReportsResponse(result=msg)


@router.get(
    "/labels",
    response_model=LabelTaxonomyResponse,
    operation_id="get_report_label_taxonomy",
    description=(
        "Return the two-level fault label dictionary shared with the report "
        "generation skill. Registered before the generic /{report_id} route so "
        "'labels' is not parsed as a report id."
    ),
)
async def get_report_label_taxonomy() -> LabelTaxonomyResponse:
    try:
        options = label_taxonomy.label_options()
    except label_taxonomy.TaxonomyError as exc:
        raise UnprocessableBizException(
            message="分类字典不可用", detail=str(exc)
        ) from exc
    return LabelTaxonomyResponse(
        result=LabelTaxonomyMsg(
            version=str(options["version"]),
            first_level_labels=list(options["first_level_labels"]),
            pairs=[
                LabelPairModel(
                    first_level_label=str(pair["first_level_label"]),
                    second_level_labels=list(pair["second_level_labels"]),
                )
                for pair in options["pairs"]
            ],
        )
    )


@router.get(
    "/{report_id}",
    response_model=GetDiagnosticReportResponse,
    operation_id="get_diagnostic_report",
    description=(
        "Get one diagnostic report by ID (the report HTML file stem), together "
        "with the original rendering payload stored in its sidecar JSON. data is "
        "null when the sidecar is missing. Use /diagnostic_report/{report_id}/html "
        "to actually open the report in a browser."
    ),
)
async def get_diagnostic_report(report_id: DiagnosticReportIdPath) -> GetDiagnosticReportResponse:
    msg = await DiagnosticReportService.get_report(report_id)
    return GetDiagnosticReportResponse(result=msg)


@router.get(
    "/{report_id}/html",
    operation_id="get_diagnostic_report_html",
    description=(
        "Download the self-contained report HTML with an inline disposition so "
        "the browser renders it directly. No CSP sandbox is applied on purpose: "
        "the report ships a small inline progressive-enhancement script "
        "(anchor based fault-file expansion, expand-all before printing) that "
        "sandboxing would break."
    ),
)
async def get_diagnostic_report_html(report_id: DiagnosticReportIdPath) -> FileResponse:
    html = await DiagnosticReportService.resolve_html(report_id)
    return FileResponse(
        html,
        media_type="text/html",
        filename=html.name,
        content_disposition_type="inline",
        headers={"X-Content-Type-Options": "nosniff"},
    )


@router.get(
    "/{report_id}/faults/{source_fault_id}",
    response_model=GetDiagnosticReportFaultResponse,
    operation_id="get_diagnostic_report_fault",
    description=(
        "Read exactly one fault from a report so the full sidecar JSON never "
        "enters an Agent context. Synthetic auto: keys are rejected; fall back "
        "to the full report endpoint for those. Returns the minimal report "
        "metadata, the untouched fault object and its bound case references."
    ),
)
async def get_diagnostic_report_fault(
    report_id: DiagnosticReportIdPath,
    source_fault_id: Annotated[str, Path(min_length=1, max_length=64)],
) -> GetDiagnosticReportFaultResponse:
    msg = await DiagnosticReportService.get_fault(report_id, source_fault_id)
    return GetDiagnosticReportFaultResponse(result=msg)


@router.post(
    "/{report_id}/confirm",
    response_model=ConfirmDiagnosticReportResponse,
    operation_id="confirm_diagnostic_report",
    description=(
        "Confirm the current version of a whole report. The request must carry "
        "the sidecar hash the page saw; a changed sidecar returns 409 and the "
        "review expires. Confirmation records the operator and never writes "
        "back to the report sidecar."
    ),
)
async def confirm_diagnostic_report(
    report_id: DiagnosticReportIdPath,
    req: Annotated[ConfirmDiagnosticReportRequest, Body()],
    operator_header: Annotated[str | None, Header(alias="X-Witty-Operator")] = None,
) -> ConfirmDiagnosticReportResponse:
    operator = require_operator(req.reviewed_by, operator_header)
    await ReportReviewService.confirm(
        report_id, req.expected_sidecar_hash, operator
    )
    msg = await DiagnosticReportService.get_report(report_id)
    return ConfirmDiagnosticReportResponse(result=msg.report)


def _classification_from_labels(labels: dict) -> ClassificationModel:
    return ClassificationModel(
        first_level_label=labels.get("first_level_label"),
        second_level_label=labels.get("second_level_label"),
        status=str(labels.get("status") or "empty"),
        error=labels.get("error"),
        taxonomy_version=labels.get("taxonomy_version"),
        snapshot_hash=labels.get("snapshot_hash"),
    )


@router.get(
    "/{report_id}/faults/{source_fault_id}/case_preview",
    response_model=ReportCasePreviewResponse,
    operation_id="preview_report_case",
    description=(
        "Build a deterministic case draft preview from a confirmed report "
        "fault. Missing evidence / remediation / matchable signals are listed "
        "explicitly; the preview never fabricates content."
    ),
)
async def preview_report_case(
    report_id: DiagnosticReportIdPath,
    source_fault_id: Annotated[str, Path(min_length=1, max_length=64)],
) -> ReportCasePreviewResponse:
    snapshot = ReportReviewService._unique_report(report_id)
    if snapshot.sidecar_state != "ok" or snapshot.payload is None:
        raise UnprocessableBizException(
            message="报告数据不完整",
            detail=(
                "sidecar_missing: 侧车 JSON 不存在"
                if snapshot.sidecar_state == "missing"
                else "sidecar_invalid: 侧车 JSON 损坏或超限"
            ),
        )
    try:
        preview = build_draft_from_fault(
            report_id,
            snapshot.payload,
            source_fault_id,
            snapshot.sidecar_hash or "",
        )
    except ValueError as exc:
        raise BadRequestBizException(
            message="故障不可用于建案", detail=str(exc)
        ) from exc
    return ReportCasePreviewResponse(
        result=ReportCasePreviewMsg(
            report_id=preview.report_id,
            source_fault_id=preview.source_fault_id,
            expected_sidecar_hash=preview.expected_sidecar_hash,
            source_fault_hash=preview.source_fault_hash,
            classification=_classification_from_labels(preview.labels),
            draft=preview.draft,
            missing_fields=preview.missing_fields,
            ready=preview.ready,
        )
    )


@router.post(
    "/{report_id}/faults/{source_fault_id}/case",
    response_model=CreateCaseFromReportResponse,
    operation_id="create_case_from_report",
    description=(
        "Create a case draft from one fault of a currently confirmed report. "
        "The server copies the two-level labels and the source-fault fingerprint; "
        "clients cannot supply either. The draft still has to pass the normal "
        "case confirm gate."
    ),
)
async def create_case_from_report(
    report_id: DiagnosticReportIdPath,
    source_fault_id: Annotated[str, Path(min_length=1, max_length=64)],
    req: Annotated[CreateCaseFromReportRequest, Body()],
    operator_header: Annotated[str | None, Header(alias="X-Witty-Operator")] = None,
) -> CreateCaseFromReportResponse:
    operator = require_operator(req.reviewed_by, operator_header)
    snapshot = await ReportReviewService.require_confirmed(
        report_id, req.expected_sidecar_hash
    )
    try:
        preview = build_draft_from_fault(
            report_id,
            snapshot.payload or {},
            source_fault_id,
            req.expected_sidecar_hash,
        )
    except ValueError as exc:
        raise BadRequestBizException(
            message="故障不可用于建案", detail=str(exc)
        ) from exc
    if preview.labels.get("status") in {"invalid", "unavailable"}:
        raise UnprocessableBizException(
            message="故障分类不可用",
            detail=str(preview.labels.get("error") or "label_invalid"),
        )
    msg = await DiagCaseLibraryService.create_report_case(preview, operator)
    return CreateCaseFromReportResponse(
        result=CreateCaseFromReportMsg(
            case_id=msg.case_id,
            case_no=msg.case_no,
            missing_fields=preview.missing_fields,
        )
    )


@router.post(
    "/{report_id}/reindex",
    response_model=ReindexDiagnosticReportResponse,
    status_code=202,
    operation_id="reindex_diagnostic_report",
    description=(
        "Re-extract one report and queue its phenomenon cards. Cards whose "
        "content and source-fault hashes are unchanged are skipped. Missing or "
        "damaged sidecars return 422; the report list still shows the file."
    ),
)
async def reindex_diagnostic_report(
    report_id: DiagnosticReportIdPath,
) -> ReindexDiagnosticReportResponse:
    result = await PhenomenonIndexService.index_scope("report", report_id=report_id)
    return ReindexDiagnosticReportResponse(
        result=ReindexDiagnosticReportMsg(
            accepted=True,
            report_id=report_id,
            queued_count=int(result.get("queued_count") or 0),
            index_status=result.get("index_status"),
        )
    )