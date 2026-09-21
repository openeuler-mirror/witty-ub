# Copyright (c) Huawei Technologies Co., Ltd. 2023-2025. All rights reserved.
"""HTTP API for the supernode diagnosis case library.

Independent from ``/diagnosis_case``: only human confirmed cases are searched by
default, ``kb_id`` is an optional source annotation (cross-knowledge-base recall)
and the ``operation`` field is filterable.
"""
from typing import Annotated

from fastapi import APIRouter, Body

from latency.common.id_validation import ResourceIdPath
from latency.schemas.diag_case_library import (
    ArchiveDiagCaseRequest,
    ConfirmDiagCaseRequest,
    CreateDiagCaseDraftRequest,
    CreateDiagCaseDraftResponse,
    ArchiveDiagCaseResponse,
    ConfirmDiagCaseResponse,
    GetDiagCaseResponse,
    HitDiagCaseResponse,
    SearchDiagCaseLibraryRequest,
    SearchDiagCasesResponse,
    UpdateDiagCaseDraftRequest,
    UpdateDiagCaseDraftResponse,
)
from latency.services.diag_case_library import DiagCaseLibraryService
from latency.services.resource_id import ResourceIdService


router = APIRouter(prefix="/diag_case_library", tags=["Diag Case Library"])


async def _validate_kb_id(kb_id: str | None) -> None:
    """``kb_id`` is optional; only a non-empty value is checked for existence."""
    if kb_id:
        await ResourceIdService.require("kb", kb_id)


@router.post(
    "",
    response_model=CreateDiagCaseDraftResponse,
    operation_id="create_diag_case_draft",
    description=(
        "Create a supernode diagnosis case draft. The draft starts in status "
        "'draft' and is NOT searchable until it passes the confirm gate. The "
        "server generates the readable case_no (UB-CASE-000123) and the "
        "embedding body search_text; neither is accepted from the caller. "
        "kb_id is optional: leave it empty for a global, cross-knowledge-base case."
    ),
)
async def create_diag_case_draft(
    req: Annotated[CreateDiagCaseDraftRequest, Body()],
) -> CreateDiagCaseDraftResponse:
    await _validate_kb_id(req.kb_id)
    msg = await DiagCaseLibraryService.create_draft(req)
    return CreateDiagCaseDraftResponse(result=msg)


@router.get(
    "/{case_id}",
    response_model=GetDiagCaseResponse,
    operation_id="get_diag_case",
    description=(
        "Get one supernode diagnosis case by ID, including status, revision, "
        "structured evidence, root cause, step-by-step remediation, verification "
        "closure and related cases. Use it after search to read the full content."
    ),
)
async def get_diag_case(case_id: ResourceIdPath) -> GetDiagCaseResponse:
    msg = await DiagCaseLibraryService.get_case(case_id)
    return GetDiagCaseResponse(result=msg)


@router.patch(
    "/{case_id}",
    response_model=UpdateDiagCaseDraftResponse,
    operation_id="update_diag_case_draft",
    description=(
        "Partially update a draft case. Only fields present in the body are "
        "changed, so the same channel appends new evidence and, after the fix is "
        "executed and re-tested, the verification closure "
        "(verification_json.closed_loop / observed_result / verified_at). "
        "Only drafts can be updated; confirmed or archived cases are frozen. "
        "revision increments and search_text plus matching signals are "
        "recomputed. Case metadata (case_no / status / revision / confirmed_by) "
        "cannot be changed here. Never fabricate observed_result before the "
        "remediation has actually been executed."
    ),
)
async def update_diag_case_draft(
    case_id: ResourceIdPath,
    req: Annotated[UpdateDiagCaseDraftRequest, Body()],
) -> UpdateDiagCaseDraftResponse:
    await _validate_kb_id(req.kb_id)
    msg = await DiagCaseLibraryService.update_draft(case_id, req)
    return UpdateDiagCaseDraftResponse(result=msg)


@router.post(
    "/{case_id}/confirm",
    response_model=ConfirmDiagCaseResponse,
    operation_id="confirm_diag_case",
    description=(
        "Confirm a draft case (draft -> confirmed) so it becomes searchable. "
        "The confirm gate only judges whether the report is trustworthy: it "
        "rejects the request unless evidence, remediation, at least one "
        "matchable signal and confirmed_by are all present. It does NOT require "
        "verification_json.observed_result, because remediation has not been "
        "executed yet at report time; remediation closure is a separate "
        "dimension appended later through the PATCH endpoint. Only drafts can "
        "be confirmed."
    ),
)
async def confirm_diag_case(
    case_id: ResourceIdPath,
    req: Annotated[ConfirmDiagCaseRequest, Body()],
) -> ConfirmDiagCaseResponse:
    msg = await DiagCaseLibraryService.confirm_case(case_id, req)
    return ConfirmDiagCaseResponse(result=msg)


@router.post(
    "/{case_id}/archive",
    response_model=ArchiveDiagCaseResponse,
    operation_id="archive_diag_case",
    description=(
        "Archive a draft or confirmed case so it is no longer returned by "
        "search. Archiving an already archived case is idempotent and returns "
        "the current case unchanged."
    ),
)
async def archive_diag_case(
    case_id: ResourceIdPath,
    req: Annotated[ArchiveDiagCaseRequest, Body()],
) -> ArchiveDiagCaseResponse:
    msg = await DiagCaseLibraryService.archive_case(case_id, req)
    return ArchiveDiagCaseResponse(result=msg)


@router.post(
    "/search",
    response_model=SearchDiagCasesResponse,
    operation_id="search_diag_cases",
    description=(
        "Search the confirmed supernode diagnosis case library using current "
        "signals (status codes, failure modes, IPs, hosts, pods, clusters, "
        "latency component bucket keys, log phrases). kb_id is optional and only "
        "filters the source, so leaving it empty recalls cases across knowledge "
        "bases. Each match returns match_score, score_norm (0~1) and the signals "
        "that actually hit. A match is a hypothesis to verify, not proof."
    ),
)
async def search_diag_cases(
    req: Annotated[SearchDiagCaseLibraryRequest, Body()],
) -> SearchDiagCasesResponse:
    await _validate_kb_id(req.kb_id)
    msg = await DiagCaseLibraryService.search_cases(req)
    return SearchDiagCasesResponse(result=msg)


@router.post(
    "/{case_id}/hit",
    response_model=HitDiagCaseResponse,
    operation_id="hit_diag_case",
    description=(
        "Record that a searched case was adopted: increments hit_count and "
        "returns the refreshed case. Call it when a retrieved case actually "
        "helped the diagnosis, so popularity ranking stays meaningful."
    ),
)
async def hit_diag_case(case_id: ResourceIdPath) -> HitDiagCaseResponse:
    msg = await DiagCaseLibraryService.mark_hit(case_id)
    return HitDiagCaseResponse(result=msg)