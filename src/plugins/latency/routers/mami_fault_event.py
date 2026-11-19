from fastapi import APIRouter, Body
from typing import Annotated

from latency.schemas.request import MamiFaultScanRequest
from latency.schemas.response import MamiFaultScanResponse, MamiFaultScanMsg
from latency.services.mami_fault_scan import resolve_mami_scan

router = APIRouter(prefix="/mami_fault_event", tags=["mami_fault_event"])


@router.post(
    "/query",
    response_model=MamiFaultScanResponse,
    operation_id="query_mami_fault_scan",
    description=(
        "Query the windowed mami hardware-fault scan summary for one asset "
        "(kb_name / log_id / kb_id). Returns whether hardware fault signals "
        "(RAS interrupt / UB link change / port_mng error) were found inside the "
        "KVCache fault window. Used by the case-matching secondary ranking channel."
    ),
)
async def query_mami_fault_scan(
    req: Annotated[MamiFaultScanRequest, Body()],
) -> MamiFaultScanResponse:
    result = await resolve_mami_scan(
        kb_name=req.kb_name, log_id=req.log_id, kb_id=req.kb_id
    )
    return MamiFaultScanResponse(result=MamiFaultScanMsg(**result))
