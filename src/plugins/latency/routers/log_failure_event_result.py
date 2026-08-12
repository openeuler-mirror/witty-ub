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
    description=(
        "Get raw connectivity fault log events for one or more trace IDs. These "
        "records are primary evidence; quote only relevant fields and do not infer "
        "a root cause solely from coincident log messages."
    ),
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
    description=(
        "List connectivity fault traces by knowledge base, fault code, topology, "
        "IP pair, trace ID or time. Use returned trace IDs and failure-mode IDs to "
        "retrieve raw logs and knowledge evidence."
    ),
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
    description=(
        "Aggregate connectivity fault codes by time window. Use this first to "
        "locate periods with concentrated connectivity failures."
    ),
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
    description=(
        "Aggregate connectivity fault codes by pod within a time range. Use this "
        "only when the investigation needs to identify pods contributing faults."
    ),
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
    description=(
        "Aggregate connectivity fault codes by source/destination IP pair. Use "
        "this after locating a failure window to identify affected paths before "
        "drilling into traces."
    ),
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
    description=(
        "Get connectivity error-code time series for a knowledge base. Filter by "
        "error code, cluster, host, pod, IP pair or time range to quantify fault "
        "frequency and correlate spikes."
    ),
)
async def get_err_code_metrics(
    req: Annotated[GetErrCodeMetricsRequest, Body()],
) -> GetErrCodeMetricsResponse:
    """获取延迟指标时间曲线数据（必选指标：total_latency, urma_total_latency, worker_query_meta_latency）"""
    msg = await LogFailureEventResultService.get_err_code_metrics(req)
    return GetErrCodeMetricsResponse(result=msg)
