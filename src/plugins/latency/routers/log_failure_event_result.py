from fastapi import APIRouter, Path, Body
from typing import Annotated
from latency.schemas.request import (
    ListLogFailureEventResultRequest,
    ListTraceFailureEventResultRequest,
    ListTimeAggregatedFailureEventRequest,
    ListPodAggregatedFailureEventRequest,
    ListSrcDstAggregatedFailureEventRequest,
    GetErrCodeMetricsRequest
)
from latency.schemas.response import (
    ListLogFailureEventResultResponse,
    ListTraceFailureEventResultResponse,
    ListTimeAggregatedFailureEventResponse,
    ListPodAggregatedFailureEventResponse,
    ListSrcDstAggregatedFailureEventResponse,
    GetErrCodeMetricsResponse
)
from latency.services.log_failure_event_result import LogFailureEventResultService

router = APIRouter(prefix="/log_failure_event_result", tags=["log_failure_event_result"])


@router.post(
    "/list_log_events",
    response_model=ListLogFailureEventResultResponse,
    operation_id="list_connectivity_trace_logs",
    openapi_extra={"x-mcp-enabled": True, "x-mcp-read-only": True},
)
async def list_log_failure_event_results(
    req: Annotated[ListLogFailureEventResultRequest, Body()],
) -> ListLogFailureEventResultResponse:
    msg = await LogFailureEventResultService.list_log_failure_event_result(req)
    return ListLogFailureEventResultResponse(result=msg)

@router.post(
    "/list_trace_events",
    response_model=ListTraceFailureEventResultResponse,
    operation_id="list_connectivity_traces",
    openapi_extra={"x-mcp-enabled": True, "x-mcp-read-only": True},
)
async def list_trace_failure_event_results(
    req: Annotated[ListTraceFailureEventResultRequest, Body()],
) -> ListTraceFailureEventResultResponse:
    msg = await LogFailureEventResultService.list_trace_failure_event_result(req=req)
    return ListTraceFailureEventResultResponse(result=msg)

@router.post(
    "/list_time_aggregated_failure_events",
    response_model=ListTimeAggregatedFailureEventResponse,
    operation_id="list_connectivity_events_by_time_windows",
    openapi_extra={"x-mcp-enabled": True, "x-mcp-read-only": True},
)
async def list_time_aggregated_failure_event_results(
    req: Annotated[ListTimeAggregatedFailureEventRequest, Body()],
) -> ListTimeAggregatedFailureEventResponse:
    msg = await LogFailureEventResultService.list_time_aggregated_failure_event_result(req=req)
    return ListTimeAggregatedFailureEventResponse(result=msg)

@router.post(
    "/list_pod_aggregated_failure_events",
    response_model=ListPodAggregatedFailureEventResponse,
    operation_id="list_connectivity_events_by_pods",
    openapi_extra={"x-mcp-enabled": True, "x-mcp-read-only": True},
)
async def list_pod_aggregated_failure_event_results(
    req: Annotated[ListPodAggregatedFailureEventRequest, Body()],
) -> ListPodAggregatedFailureEventResponse:
    msg = await LogFailureEventResultService.list_pod_aggregated_failure_event_result(req=req)
    return ListPodAggregatedFailureEventResponse(result=msg)

@router.post(
    "/list_src_dst_aggregated_failure_events",
    response_model=ListSrcDstAggregatedFailureEventResponse,
    operation_id="list_connectivity_events",
    openapi_extra={"x-mcp-enabled": True, "x-mcp-read-only": True},
)
async def list_src_dst_aggregated_failure_event_results(
    req: Annotated[ListSrcDstAggregatedFailureEventRequest, Body()],
) -> ListSrcDstAggregatedFailureEventResponse:
    msg = await LogFailureEventResultService.list_src_dst_aggregated_failure_event_result(req=req)
    return ListSrcDstAggregatedFailureEventResponse(result=msg)

@router.post(
    "/metrics/err_code",
    response_model=GetErrCodeMetricsResponse,
    operation_id="get_connectivity_metrics",
    openapi_extra={"x-mcp-enabled": True, "x-mcp-read-only": True},
)
async def get_err_code_metrics(
    req: Annotated[GetErrCodeMetricsRequest, Body()],
) -> GetErrCodeMetricsResponse:
    """获取延迟指标时间曲线数据（必选指标：total_latency, urma_total_latency, worker_query_meta_latency）"""
    msg = await LogFailureEventResultService.get_err_code_metrics(req)
    return GetErrCodeMetricsResponse(result=msg)
