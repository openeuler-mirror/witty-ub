from fastapi import APIRouter, Path, Body
from typing import Annotated
from latency.schemas.request import (
    ListLogFailureEventResultRequest,
    ListTraceFailureEventResultRequest,
    ListTimeAggregatedFailureEventRequest,
    ListPodAggregatedFailureEventRequest,
    GetErrCodeMetricsRequest
)
from latency.schemas.response import (
    ListLogFailureEventResultResponse,
    ListTraceFailureEventResultResponse,
    ListTimeAggregatedFailureEventResponse,
    ListPodAggregatedFailureEventResponse,
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

@router.post("/list_trace_events", response_model=ListTraceFailureEventResultResponse)
async def list_trace_failure_event_results(
    req: Annotated[ListTraceFailureEventResultRequest, Body()],
) -> ListTraceFailureEventResultResponse:
    msg = await LogFailureEventResultService.list_trace_failure_event_result(req=req)
    return ListTraceFailureEventResultResponse(result=msg)

@router.post("/list_time_aggregated_failure_events", response_model=ListTimeAggregatedFailureEventResponse)
async def list_time_aggregated_failure_event_results(
    req: Annotated[ListTimeAggregatedFailureEventRequest, Body()],
) -> ListTimeAggregatedFailureEventResponse:
    msg = await LogFailureEventResultService.list_time_aggregated_failure_event_result(req=req)
    return ListTimeAggregatedFailureEventResponse(result=msg)

@router.post("/list_pod_aggregated_failure_events", response_model=ListPodAggregatedFailureEventResponse)
async def list_pod_aggregated_failure_event_results(
    req: Annotated[ListPodAggregatedFailureEventRequest, Body()],
) -> ListPodAggregatedFailureEventResponse:
    msg = await LogFailureEventResultService.list_pod_aggregated_failure_event_result(req=req)
    return ListPodAggregatedFailureEventResponse(result=msg)

@router.post("/metrics/err_code", response_model=GetErrCodeMetricsResponse)
async def get_err_code_metrics(
    req: Annotated[GetErrCodeMetricsRequest, Body()],
) -> GetErrCodeMetricsResponse:
    """获取延迟指标时间曲线数据（必选指标：total_latency, urma_total_latency, worker_query_meta_latency）"""
    msg = await LogFailureEventResultService.get_err_code_metrics(req)
    return GetErrCodeMetricsResponse(result=msg)