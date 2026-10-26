# Copyright (c) Huawei Technologies Co., Ltd. 2023-2025. All rights reserved.
"""HTTP API for the diagnostic report library (``/diagnostic_report``).

Agent generated reports land in ``$WITTY_REPORT_DIR`` (persisted by the
``witty-ub-reports`` volume). This router only lists them and hands the
self-contained HTML back to the browser, so a report can be reviewed from the
frontend instead of being copied out of the container by hand.
"""
from typing import Annotated

from fastapi import APIRouter, Body, Path
from starlette.responses import FileResponse

from latency.common.id_validation import DiagnosticReportIdPath
from latency.schemas.diagnostic_report import (
    GetDiagnosticReportFaultResponse,
    GetDiagnosticReportResponse,
    ListDiagnosticReportsRequest,
    ListDiagnosticReportsResponse,
    ReindexDiagnosticReportMsg,
    ReindexDiagnosticReportResponse,
)
from latency.services.diagnostic_report import DiagnosticReportService
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