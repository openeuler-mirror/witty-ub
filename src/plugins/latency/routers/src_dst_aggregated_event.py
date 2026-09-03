# Copyright (c) Huawei Technologies Co., Ltd. 2023-2024. All rights reserved.

from fastapi import APIRouter, Path, Body
from typing import Annotated
from latency.schemas.request import (
    ListSrcDstAggregatedEventRequest,
    ListTimeWindowAggregatedEventRequest,
)
from latency.schemas.response import (
    ListSrcDstAggregatedEventResponse,
    GetSrcDstAggregatedEventResponse,
    ListTimeWindowAggregatedEventResponse,
)
from latency.services.src_dst_aggregated_event import SrcDstAggregatedEventService
from latency.services.resource_id import ResourceIdService

router = APIRouter(prefix="/aggregated_event", tags=["aggregated_event"])


@router.post(
    "/list",
    response_model=ListSrcDstAggregatedEventResponse,
    operation_id="list_latency_events",
    description=(
        "List source/destination IP latency aggregates. Use this to find IP pairs "
        "with high latency or anomalous requests before drilling into traces. "
        "Supports operation, log-event time, topology and multi-column filters."
    ),
)
async def list_aggregated_events(
    req: Annotated[ListSrcDstAggregatedEventRequest, Body()],
) -> ListSrcDstAggregatedEventResponse:
    await ResourceIdService.validate_request(req)
    msg = await SrcDstAggregatedEventService.list_aggregated_events(req)
    return ListSrcDstAggregatedEventResponse(result=msg)


@router.get(
    "/{event_id}",
    response_model=GetSrcDstAggregatedEventResponse,
    operation_id="get_latency_event",
    description=(
        "Get one source/destination latency aggregate by ID. Use it to inspect the "
        "selected path and aggregate latency components before trace drill-down."
    ),
)
async def get_aggregated_event_by_id(
    event_id: Annotated[str, Path()],
) -> GetSrcDstAggregatedEventResponse:
    msg = await SrcDstAggregatedEventService.get_aggregated_event_by_id(event_id)
    return GetSrcDstAggregatedEventResponse(result=msg)


@router.post(
    "/list_time_window",
    response_model=ListTimeWindowAggregatedEventResponse,
    operation_id="list_latency_events_by_time_windows",
    description=(
        "List latency aggregates grouped into time windows. Use this to identify "
        "when latency increased and compare source/destination IP pairs within the "
        "same interval."
    ),
)
async def list_time_window_aggregated_events(
    req: Annotated[ListTimeWindowAggregatedEventRequest, Body()],
) -> ListTimeWindowAggregatedEventResponse:
    await ResourceIdService.validate_request(req)
    msg = await SrcDstAggregatedEventService.list_time_window_events(req)
    return ListTimeWindowAggregatedEventResponse(result=msg)
