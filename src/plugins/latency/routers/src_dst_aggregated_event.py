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

router = APIRouter(prefix="/aggregated_event", tags=["aggregated_event"])


@router.post("/list", response_model=ListSrcDstAggregatedEventResponse)
async def list_aggregated_events(
    req: Annotated[ListSrcDstAggregatedEventRequest, Body()],
) -> ListSrcDstAggregatedEventResponse:
    msg = await SrcDstAggregatedEventService.list_aggregated_events(req)
    return ListSrcDstAggregatedEventResponse(result=msg)


@router.get("/{event_id}", response_model=GetSrcDstAggregatedEventResponse)
async def get_aggregated_event_by_id(
    event_id: Annotated[str, Path()],
) -> GetSrcDstAggregatedEventResponse:
    msg = await SrcDstAggregatedEventService.get_aggregated_event_by_id(event_id)
    return GetSrcDstAggregatedEventResponse(result=msg)


@router.post("/list_time_window", response_model=ListTimeWindowAggregatedEventResponse)
async def list_time_window_aggregated_events(
    req: Annotated[ListTimeWindowAggregatedEventRequest, Body()],
) -> ListTimeWindowAggregatedEventResponse:
    msg = await SrcDstAggregatedEventService.list_time_window_events(req)
    return ListTimeWindowAggregatedEventResponse(result=msg)
