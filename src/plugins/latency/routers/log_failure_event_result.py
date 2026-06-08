from fastapi import APIRouter, Path, Body
from typing import Annotated
from latency.schemas.request import (
    ListLogFailureEventResultRequest,
    ListTraceFailureEventResultRequest,
    GetErrCodeMetricsRequest
)
from latency.schemas.response import (
    ListLogFailureEventResultResponse,
    ListTraceFailureEventResultReponse,
    GetErrCodeMetricsResponse
)
from latency.services.log_failure_event_result import LogFailureEventResultService

router = APIRouter(prefix="/log_failure_event_result", tags=["log_failure_event_result"])


@router.post("/list_log_events", response_model=ListLogFailureEventResultResponse)
async def list_log_failure_event_results(
    req: Annotated[ListLogFailureEventResultRequest, Body()],
) -> ListLogFailureEventResultResponse:
    msg = await LogFailureEventResultService.list_log_failure_event_result(req)
    return ListLogFailureEventResultResponse(result=msg)

@router.post("/list_trace_events", response_model=ListTraceFailureEventResultReponse)
async def list_trace_failure_event_results(
    req: Annotated[ListTraceFailureEventResultRequest, Body()],
) -> ListTraceFailureEventResultReponse:
    msg = await LogFailureEventResultService.list_trace_failure_event_result(req=req)
    return ListTraceFailureEventResultReponse(result=msg)

@router.post("/metrics/err_code", response_model=GetErrCodeMetricsResponse)
async def get_err_code_metrics(
    req: Annotated[GetErrCodeMetricsRequest, Body()],
) -> GetErrCodeMetricsResponse:
    """获取延迟指标时间曲线数据（必选指标：total_latency, urma_total_latency, worker_query_meta_latency）"""
    msg = await LogFailureEventResultService.get_err_code_metrics(req)
    return GetErrCodeMetricsResponse(result=msg)