from typing import Annotated

from fastapi import APIRouter, Body, Path

from latency.schemas.request import CreateDiagnosisCaseRequest, SearchDiagnosisCasesRequest
from latency.schemas.response import (
    CreateDiagnosisCaseResponse,
    GetDiagnosisCaseResponse,
    SearchDiagnosisCasesResponse,
)
from latency.services.diagnosis_case import DiagnosisCaseService


router = APIRouter(prefix="/diagnosis_case", tags=["Diagnosis Case"])


@router.post("", response_model=CreateDiagnosisCaseResponse)
async def create_diagnosis_case(
    req: Annotated[CreateDiagnosisCaseRequest, Body()],
) -> CreateDiagnosisCaseResponse:
    msg = await DiagnosisCaseService.create_case(req)
    return CreateDiagnosisCaseResponse(result=msg)


@router.get(
    "/{case_id}",
    response_model=GetDiagnosisCaseResponse,
    operation_id="get_diagnosis_case",
    description=(
        "Get one historical diagnosis case by ID. Inspect its symptom, root cause, "
        "recommendation, fingerprint and evidence references after case search."
    ),
    openapi_extra={"x-mcp-enabled": True, "x-mcp-read-only": True},
)
async def get_diagnosis_case(
    case_id: Annotated[str, Path()],
) -> GetDiagnosisCaseResponse:
    msg = await DiagnosisCaseService.get_case(case_id)
    return GetDiagnosisCaseResponse(result=msg)


@router.post(
    "/search",
    response_model=SearchDiagnosisCasesResponse,
    operation_id="list_diagnosis_cases",
    description=(
        "Search historical diagnosis cases using current signals such as status "
        "codes, failure modes, IPs, hosts, pods, clusters, latency components and "
        "log phrases. A match is a hypothesis to verify, not proof."
    ),
    openapi_extra={"x-mcp-enabled": True, "x-mcp-read-only": True},
)
async def search_diagnosis_cases(
    req: Annotated[SearchDiagnosisCasesRequest, Body()],
) -> SearchDiagnosisCasesResponse:
    msg = await DiagnosisCaseService.search_cases(req)
    return SearchDiagnosisCasesResponse(result=msg)


@router.post("/{case_id}/hit", response_model=GetDiagnosisCaseResponse)
async def mark_diagnosis_case_hit(
    case_id: Annotated[str, Path()],
) -> GetDiagnosisCaseResponse:
    msg = await DiagnosisCaseService.mark_case_hit(case_id)
    return GetDiagnosisCaseResponse(result=msg)
