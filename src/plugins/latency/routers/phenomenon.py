# Copyright (c) Huawei Technologies Co., Ltd. 2023-2025. All rights reserved.
"""HTTP API for phenomenon search and index maintenance."""
from typing import Annotated

from fastapi import APIRouter, Body, Path
from latency.schemas.phenomenon import (
    GetPhenomenonResponse,
    GetPhenomenonStatusResponse,
    IndexPhenomenonMsg,
    IndexPhenomenonRequest,
    IndexPhenomenonResponse,
    SearchPhenomenaResponse,
    SearchPhenomenonRequest,
)
from latency.services.phenomenon_index import PhenomenonIndexService
from latency.services.phenomenon_search import PhenomenonSearchService
from latency.services.phenomenon_status import PhenomenonStatusService

router = APIRouter(prefix="/phenomenon", tags=["Phenomenon"])


@router.post(
    "/search",
    response_model=SearchPhenomenaResponse,
    operation_id="search_phenomena",
    description=(
        "Search historical phenomenon cards by natural-language description. "
        "Returns normalized similarity, the published card summary and detail "
        "pointers only; it never returns report/case full text or raw chunks. "
        "A hit is a historical clue and must be verified against current evidence."
    ),
)
async def search_phenomena(
    req: Annotated[SearchPhenomenonRequest, Body()],
) -> SearchPhenomenaResponse:
    msg = await PhenomenonSearchService.search(req)
    return SearchPhenomenaResponse(result=msg)


@router.post(
    "/index",
    response_model=IndexPhenomenonResponse,
    status_code=202,
    operation_id="index_phenomena",
    description=(
        "Queue a rebuild of phenomenon cards. scope=report/case targets one "
        "object; all rebuilds every report and confirmed case; legacy_all "
        "rebuilds readable old file cases. force=true ignores unchanged hashes. "
        "This is an operations endpoint, not exposed to ordinary frontends."
    ),
)
async def index_phenomena(
    req: Annotated[IndexPhenomenonRequest, Body()],
) -> IndexPhenomenonResponse:
    result = await PhenomenonIndexService.index_scope(
        req.scope,
        report_id=req.report_id,
        case_id=req.case_id,
        force=req.force,
    )
    return IndexPhenomenonResponse(
        result=IndexPhenomenonMsg(
            accepted=True,
            scope=req.scope,
            target_id=result.get("target_id"),
            queued_count=int(result.get("queued_count") or 0),
            skipped_count=int(result.get("skipped_count") or 0),
            index_status=result.get("index_status"),
        )
    )


@router.get(
    "/status",
    response_model=GetPhenomenonStatusResponse,
    operation_id="get_phenomenon_status",
    description=(
        "Read-only operations snapshot: report/card index distribution, cleanup "
        "and outbox backlog, recent retrieval error rate and p95, plus alerts "
        "derived from the design thresholds. Never mutates cards or RAG state."
    ),
)
async def get_phenomenon_status() -> GetPhenomenonStatusResponse:
    msg = await PhenomenonStatusService.snapshot()
    return GetPhenomenonStatusResponse(result=msg)


@router.get(
    "/{doc_id:path}",
    response_model=GetPhenomenonResponse,
    operation_id="get_phenomenon_card",
    description=(
        "Get one phenomenon card by its logical doc_id (URL-encoded as a whole). "
        "Returns current pointers, published summary and index progress; the "
        "uploaded text is never returned."
    ),
)
async def get_phenomenon_card(
    doc_id: Annotated[str, Path(min_length=1, max_length=512)],
) -> GetPhenomenonResponse:
    msg = await PhenomenonSearchService.get_card(doc_id)
    return GetPhenomenonResponse(result=msg)
