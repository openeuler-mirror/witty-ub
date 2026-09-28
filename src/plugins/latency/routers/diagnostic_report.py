# Copyright (c) Huawei Technologies Co., Ltd. 2023-2025. All rights reserved.
"""HTTP API for the diagnostic report library (``/diagnostic_report``).

Agent generated reports land in ``$WITTY_REPORT_DIR`` (persisted by the
``witty-ub-reports`` volume). This router only lists them and hands the
self-contained HTML back to the browser, so a report can be reviewed from the
frontend instead of being copied out of the container by hand.
"""
from typing import Annotated

from fastapi import APIRouter, Body
from starlette.responses import FileResponse

from latency.common.id_validation import DiagnosticReportIdPath
from latency.schemas.diagnostic_report import (
    GetDiagnosticReportResponse,
    ListDiagnosticReportsRequest,
    ListDiagnosticReportsResponse,
)
from latency.services.diagnostic_report import DiagnosticReportService


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