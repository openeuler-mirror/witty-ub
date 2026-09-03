"""Minimal read-only BRPC diagnosis query API."""

from typing import Annotated

from fastapi import APIRouter, HTTPException, Path, Query

from latency.schemas.brpc_diagnosis import (
    BrpcAggregateWindowSize,
    BrpcComponent,
    BrpcMetricSortField,
    BrpcQueryTimestamp,
    BrpcSortOrder,
    BrpcWindowSize,
    GetBrpcAbnormalThreadDetailResponse,
    GetBrpcBatchResponse,
    GetBrpcInterfaceTimelineResponse,
    GetBrpcPodEventDetailResponse,
    GetBrpcTaskBatchResponse,
    GetBrpcThreadEventDetailResponse,
    ListBrpcAbnormalThreadsResponse,
    ListBrpcDiagHitsResponse,
    ListBrpcPodEventsResponse,
    ListBrpcThreadEventsResponse,
)
from latency.services.brpc_diagnosis import BrpcDiagnosisService
from latency.services.resource_id import ResourceIdService


router = APIRouter(prefix="/brpc-diagnosis", tags=["brpc-diagnosis"])

_QUERY_TIME_DESCRIPTION = (
    "UTC+8 时间字符串，严格使用 YYYY-MM-DD HH:MM:SS 格式；"
    "后端转换为 epoch 微秒时间戳"
)


def _build_metric_sort_fields(
    fields: list[str] | None,
    directions: list[BrpcSortOrder] | None,
) -> list[BrpcMetricSortField]:
    fields = fields or []
    directions = directions or []
    if len(fields) != len(directions):
        raise HTTPException(
            status_code=422,
            detail="sort_field 和 sort_direction 必须一一对应",
        )
    if len(fields) > 50:
        raise HTTPException(status_code=422, detail="排序字段不能超过 50 个")
    if len(set(fields)) != len(fields):
        raise HTTPException(status_code=422, detail="排序字段不能重复")
    if any(not field or len(field) > 256 for field in fields):
        raise HTTPException(
            status_code=422,
            detail="排序字段长度必须为 1 到 256 个字符",
        )
    return [
        BrpcMetricSortField(field=field, order=direction)
        for field, direction in zip(fields, directions, strict=True)
    ]


@router.get(
    "/task/{task_id}/batch",
    response_model=GetBrpcTaskBatchResponse,
    operation_id="get_brpc_batch_by_task",
    description="Resolve the final imported BRPC diagnosis batch for one task.",
)
async def get_batch_by_task_id(
    task_id: Annotated[str, Path(min_length=1)],
) -> GetBrpcTaskBatchResponse:
    await ResourceIdService.require("task", task_id)
    result = await BrpcDiagnosisService.get_batch_by_task_id(task_id)
    return GetBrpcTaskBatchResponse(result=result)


@router.get(
    "/batch/{batch_id}",
    response_model=GetBrpcBatchResponse,
    operation_id="get_brpc_batch",
    description="Get metadata for exactly one imported BRPC diagnosis batch.",
)
async def get_batch(
    batch_id: Annotated[str, Path(min_length=1)],
) -> GetBrpcBatchResponse:
    result = await BrpcDiagnosisService.get_batch(batch_id)
    return GetBrpcBatchResponse(result=result)


@router.get(
    "/batch/{batch_id}/hits",
    response_model=ListBrpcDiagHitsResponse,
    operation_id="list_brpc_diagnosis_hits",
    description=(
        "List hit logs for exactly one thread, identified by "
        "(pod_ip, thread_id), from one BRPC diagnosis batch in "
        "descending timestamp order. The optional UTC+8 time range is "
        "[start_time, end_time). pod_name can further narrow the result."
    ),
)
async def list_hits(
    batch_id: Annotated[str, Path(min_length=1)],
    pod_ip: Annotated[str, Query(min_length=1)],
    thread_id: Annotated[int, Query()],
    page_num: Annotated[int, Query(ge=1)] = 1,
    page_cnt: Annotated[int, Query(ge=1, le=1000)] = 100,
    start_time: Annotated[
        BrpcQueryTimestamp | None,
        Query(description=_QUERY_TIME_DESCRIPTION),
    ] = None,
    end_time: Annotated[
        BrpcQueryTimestamp | None,
        Query(description=_QUERY_TIME_DESCRIPTION),
    ] = None,
    pod_name: Annotated[str | None, Query(min_length=1)] = None,
) -> ListBrpcDiagHitsResponse:
    result = await BrpcDiagnosisService.list_hits(
        batch_id=batch_id,
        pod_ip=pod_ip,
        thread_id=thread_id,
        page_num=page_num,
        page_cnt=page_cnt,
        start_timestamp=start_time,
        end_timestamp=end_time,
        pod_name=pod_name,
    )
    return ListBrpcDiagHitsResponse(result=result)


@router.get(
    "/batch/{batch_id}/thread-logs",
    response_model=ListBrpcDiagHitsResponse,
    operation_id="list_brpc_thread_logs",
    description=(
        "List ALL log lines (fault + normal) for one thread from the original "
        "log file. Fault lines carry a failure_mode_id; normal lines have an "
        "empty failure_mode_id."
    ),
)
async def list_thread_logs(
    batch_id: Annotated[str, Path(min_length=1)],
    pod_ip: Annotated[str, Query(min_length=1)],
    thread_id: Annotated[int, Query()],
    start_time: Annotated[
        BrpcQueryTimestamp | None,
        Query(description=_QUERY_TIME_DESCRIPTION),
    ] = None,
    end_time: Annotated[
        BrpcQueryTimestamp | None,
        Query(description=_QUERY_TIME_DESCRIPTION),
    ] = None,
) -> ListBrpcDiagHitsResponse:
    result = await BrpcDiagnosisService.list_thread_logs(
        batch_id=batch_id,
        pod_ip=pod_ip,
        thread_id=thread_id,
        start_timestamp=start_time,
        end_timestamp=end_time,
    )
    return ListBrpcDiagHitsResponse(result=result)


@router.get(
    "/batch/{batch_id}/interface-timeline",
    response_model=GetBrpcInterfaceTimelineResponse,
    operation_id="get_brpc_interface_timeline",
    description=(
        "Get epoch-aligned interface hit-count series for exactly one BRPC "
        "diagnosis batch. The UTC+8 time range is [start_time, end_time), and missing "
        "windows are returned with a zero count. pod_ip and pod_name are optional "
        "exact-match filters."
    ),
)
async def get_interface_timeline(
    batch_id: Annotated[str, Path(min_length=1)],
    start_time: Annotated[
        BrpcQueryTimestamp,
        Query(description=_QUERY_TIME_DESCRIPTION),
    ],
    end_time: Annotated[
        BrpcQueryTimestamp,
        Query(description=_QUERY_TIME_DESCRIPTION),
    ],
    window_size: Annotated[BrpcWindowSize, Query()],
    component: Annotated[BrpcComponent | None, Query()] = None,
    interface_id: Annotated[str | None, Query(min_length=1)] = None,
    pod_ip: Annotated[str | None, Query(min_length=1)] = None,
    pod_name: Annotated[str | None, Query(min_length=1)] = None,
) -> GetBrpcInterfaceTimelineResponse:
    result = await BrpcDiagnosisService.get_interface_timeline(
        batch_id=batch_id,
        start_timestamp=start_time,
        end_timestamp=end_time,
        window_size=window_size,
        component=component,
        interface_id=interface_id,
        pod_ip=pod_ip,
        pod_name=pod_name,
    )
    return GetBrpcInterfaceTimelineResponse(result=result)


@router.get(
    "/batch/{batch_id}/pod-events",
    response_model=ListBrpcPodEventsResponse,
    operation_id="list_brpc_pod_events",
    description=(
        "List dynamic BRPC hit events grouped by epoch-aligned window and Pod IP. "
        "Hits without a Pod IP are excluded. pod_ip and pod_name are optional "
        "exact-match filters."
    ),
)
async def list_pod_events(
    batch_id: Annotated[str, Path(min_length=1)],
    start_time: Annotated[
        BrpcQueryTimestamp,
        Query(description=_QUERY_TIME_DESCRIPTION),
    ],
    end_time: Annotated[
        BrpcQueryTimestamp,
        Query(description=_QUERY_TIME_DESCRIPTION),
    ],
    window_size: Annotated[BrpcAggregateWindowSize, Query()],
    sort_order: Annotated[
        BrpcSortOrder,
        Query(description="按窗口开始时间排序，默认升序"),
    ] = "asc",
    sort_field: Annotated[
        list[str] | None,
        Query(description="多指标排序字段，按参数出现顺序确定优先级"),
    ] = None,
    sort_direction: Annotated[
        list[BrpcSortOrder] | None,
        Query(description="多指标排序方向，与 sort_field 一一对应"),
    ] = None,
    page_num: Annotated[int, Query(ge=1)] = 1,
    page_cnt: Annotated[int, Query(ge=1, le=1000)] = 10,
    pod_ip: Annotated[str | None, Query(min_length=1)] = None,
    pod_name: Annotated[str | None, Query(min_length=1)] = None,
) -> ListBrpcPodEventsResponse:
    result = await BrpcDiagnosisService.list_pod_events(
        batch_id=batch_id,
        start_timestamp=start_time,
        end_timestamp=end_time,
        window_size=window_size,
        sort_order=sort_order,
        metric_sort_fields=_build_metric_sort_fields(sort_field, sort_direction),
        page_num=page_num,
        page_cnt=page_cnt,
        pod_ip=pod_ip,
        pod_name=pod_name,
    )
    return ListBrpcPodEventsResponse(result=result)


@router.get(
    "/batch/{batch_id}/pod-events/{event_id}",
    response_model=GetBrpcPodEventDetailResponse,
    operation_id="get_brpc_pod_event_detail",
    description=(
        "Get a dynamic Pod event. The complete grouping key is required and is "
        "cryptographically checked against event_id."
    ),
)
async def get_pod_event_detail(
    batch_id: Annotated[str, Path(min_length=1)],
    event_id: Annotated[str, Path(pattern=r"^[0-9a-f]{64}$")],
    window_start_time: Annotated[
        BrpcQueryTimestamp,
        Query(description=_QUERY_TIME_DESCRIPTION),
    ],
    window_end_time: Annotated[
        BrpcQueryTimestamp,
        Query(description=_QUERY_TIME_DESCRIPTION),
    ],
    pod_ip: Annotated[str, Query(min_length=1)],
    page_num: Annotated[int, Query(ge=1)] = 1,
    page_cnt: Annotated[int, Query(ge=1, le=1000)] = 100,
    pod_name: Annotated[str | None, Query(min_length=1)] = None,
) -> GetBrpcPodEventDetailResponse:
    result = await BrpcDiagnosisService.get_pod_event_detail(
        event_id=event_id,
        batch_id=batch_id,
        window_start_timestamp=window_start_time,
        window_end_timestamp=window_end_time,
        pod_ip=pod_ip,
        page_num=page_num,
        page_cnt=page_cnt,
        pod_name=pod_name,
    )
    return GetBrpcPodEventDetailResponse(result=result)


@router.get(
    "/batch/{batch_id}/thread-events",
    response_model=ListBrpcThreadEventsResponse,
    operation_id="list_brpc_thread_events",
    description=(
        "List dynamic BRPC events grouped by window, Pod IP and thread ID. "
        "Hits missing Pod IP or thread ID are excluded. pod_ip and "
        "pod_name are optional exact-match filters."
    ),
)
async def list_thread_events(
    batch_id: Annotated[str, Path(min_length=1)],
    start_time: Annotated[
        BrpcQueryTimestamp,
        Query(description=_QUERY_TIME_DESCRIPTION),
    ],
    end_time: Annotated[
        BrpcQueryTimestamp,
        Query(description=_QUERY_TIME_DESCRIPTION),
    ],
    window_size: Annotated[BrpcAggregateWindowSize, Query()],
    sort_order: Annotated[
        BrpcSortOrder,
        Query(description="按窗口开始时间排序，默认升序"),
    ] = "asc",
    sort_field: Annotated[
        list[str] | None,
        Query(description="多指标排序字段，按参数出现顺序确定优先级"),
    ] = None,
    sort_direction: Annotated[
        list[BrpcSortOrder] | None,
        Query(description="多指标排序方向，与 sort_field 一一对应"),
    ] = None,
    page_num: Annotated[int, Query(ge=1)] = 1,
    page_cnt: Annotated[int, Query(ge=1, le=1000)] = 10,
    pod_ip: Annotated[str | None, Query(min_length=1)] = None,
    pod_name: Annotated[str | None, Query(min_length=1)] = None,
) -> ListBrpcThreadEventsResponse:
    result = await BrpcDiagnosisService.list_thread_events(
        batch_id=batch_id,
        start_timestamp=start_time,
        end_timestamp=end_time,
        window_size=window_size,
        sort_order=sort_order,
        metric_sort_fields=_build_metric_sort_fields(sort_field, sort_direction),
        page_num=page_num,
        page_cnt=page_cnt,
        pod_ip=pod_ip,
        pod_name=pod_name,
    )
    return ListBrpcThreadEventsResponse(result=result)


@router.get(
    "/batch/{batch_id}/thread-events/{event_id}",
    response_model=GetBrpcThreadEventDetailResponse,
    operation_id="get_brpc_thread_event_detail",
    description=(
        "Get a dynamic Thread event. The complete grouping key is required and "
        "checked against event_id before any detail query is run."
    ),
)
async def get_thread_event_detail(
    batch_id: Annotated[str, Path(min_length=1)],
    event_id: Annotated[str, Path(pattern=r"^[0-9a-f]{64}$")],
    window_start_time: Annotated[
        BrpcQueryTimestamp,
        Query(description=_QUERY_TIME_DESCRIPTION),
    ],
    window_end_time: Annotated[
        BrpcQueryTimestamp,
        Query(description=_QUERY_TIME_DESCRIPTION),
    ],
    pod_ip: Annotated[str, Query(min_length=1)],
    thread_id: Annotated[int, Query()],
    page_num: Annotated[int, Query(ge=1)] = 1,
    page_cnt: Annotated[int, Query(ge=1, le=1000)] = 100,
    pod_name: Annotated[str | None, Query(min_length=1)] = None,
) -> GetBrpcThreadEventDetailResponse:
    result = await BrpcDiagnosisService.get_thread_event_detail(
        event_id=event_id,
        batch_id=batch_id,
        window_start_timestamp=window_start_time,
        window_end_timestamp=window_end_time,
        pod_ip=pod_ip,
        thread_id=thread_id,
        page_num=page_num,
        page_cnt=page_cnt,
        pod_name=pod_name,
    )
    return GetBrpcThreadEventDetailResponse(result=result)


@router.get(
    "/batch/{batch_id}/abnormal-threads",
    response_model=ListBrpcAbnormalThreadsResponse,
    operation_id="list_brpc_abnormal_threads",
    description=(
        "List threads with at least one BRPC diagnosis hit in the requested time "
        "range. Threads missing Pod IP or thread ID are excluded. "
        "pod_ip and pod_name are optional exact-match filters. search performs "
        "a partial match against thread ID, Pod IP and Pod name."
    ),
)
async def list_abnormal_threads(
    batch_id: Annotated[str, Path(min_length=1)],
    start_time: Annotated[
        BrpcQueryTimestamp,
        Query(description=_QUERY_TIME_DESCRIPTION),
    ],
    end_time: Annotated[
        BrpcQueryTimestamp,
        Query(description=_QUERY_TIME_DESCRIPTION),
    ],
    pod_ip: Annotated[str | None, Query(min_length=1)] = None,
    pod_name: Annotated[str | None, Query(min_length=1)] = None,
    search: Annotated[
        str | None,
        Query(
            min_length=1,
            max_length=200,
            description="线程 ID、Pod IP 或 Pod 名称搜索关键词",
        ),
    ] = None,
    sort_field: Annotated[
        list[str] | None,
        Query(description="多指标排序字段，按参数出现顺序确定优先级"),
    ] = None,
    sort_direction: Annotated[
        list[BrpcSortOrder] | None,
        Query(description="多指标排序方向，与 sort_field 一一对应"),
    ] = None,
    page_num: Annotated[int, Query(ge=1)] = 1,
    page_cnt: Annotated[int, Query(ge=1, le=1000)] = 100,
) -> ListBrpcAbnormalThreadsResponse:
    result = await BrpcDiagnosisService.list_abnormal_threads(
        batch_id=batch_id,
        start_timestamp=start_time,
        end_timestamp=end_time,
        page_num=page_num,
        page_cnt=page_cnt,
        pod_ip=pod_ip,
        pod_name=pod_name,
        search=search,
        metric_sort_fields=_build_metric_sort_fields(sort_field, sort_direction),
    )
    return ListBrpcAbnormalThreadsResponse(result=result)


@router.get(
    "/batch/{batch_id}/abnormal-threads/{thread_key}",
    response_model=GetBrpcAbnormalThreadDetailResponse,
    operation_id="get_brpc_abnormal_thread_detail",
    description=(
        "Get one abnormal Thread's interface timeline, failure graph and hit logs. "
        "The complete Thread key is required and checked against thread_key."
    ),
)
async def get_abnormal_thread_detail(
    batch_id: Annotated[str, Path(min_length=1)],
    thread_key: Annotated[str, Path(pattern=r"^[0-9a-f]{64}$")],
    pod_ip: Annotated[str, Query(min_length=1)],
    thread_id: Annotated[int, Query()],
    start_time: Annotated[
        BrpcQueryTimestamp,
        Query(description=_QUERY_TIME_DESCRIPTION),
    ],
    end_time: Annotated[
        BrpcQueryTimestamp,
        Query(description=_QUERY_TIME_DESCRIPTION),
    ],
    window_size: Annotated[BrpcWindowSize, Query()],
    page_num: Annotated[int, Query(ge=1)] = 1,
    page_cnt: Annotated[int, Query(ge=1, le=1000)] = 100,
    pod_name: Annotated[str | None, Query(min_length=1)] = None,
) -> GetBrpcAbnormalThreadDetailResponse:
    result = await BrpcDiagnosisService.get_abnormal_thread_detail(
        thread_key=thread_key,
        batch_id=batch_id,
        pod_ip=pod_ip,
        thread_id=thread_id,
        start_timestamp=start_time,
        end_timestamp=end_time,
        window_size=window_size,
        page_num=page_num,
        page_cnt=page_cnt,
        pod_name=pod_name,
    )
    return GetBrpcAbnormalThreadDetailResponse(result=result)
