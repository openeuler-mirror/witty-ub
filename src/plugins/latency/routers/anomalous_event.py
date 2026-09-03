# Copyright (c) Huawei Technologies Co., Ltd. 2023-2024. All rights reserved.

from fastapi import APIRouter, Path, Body
from typing import Annotated
from latency.schemas.request import ListAnomalousEventRequest
from latency.schemas.response import (
    GetAnomalousEventResponse,
    ListAnomalousEventsResponse,
)
from latency.services.anomalous_event import AnomalousEventService
from latency.services.resource_id import ResourceIdService

router = APIRouter(prefix="/anomalous_event", tags=["anomalous_event"])


@router.get("/{event_id}", response_model=GetAnomalousEventResponse)
async def get_anomalous_event_by_id(
    event_id: Annotated[str, Path()],
) -> GetAnomalousEventResponse:
    msg = await AnomalousEventService.get_anomalous_event_by_id(event_id)
    return GetAnomalousEventResponse(result=msg)


@router.post("/list", response_model=ListAnomalousEventsResponse)
async def list_anomalous_events(
    req: Annotated[ListAnomalousEventRequest, Body()],
) -> ListAnomalousEventsResponse:
    """批量查询异常事件（支持按 log_id 或 aggregated_event_id 过滤）"""
    await ResourceIdService.validate_request(req)
    msg = await AnomalousEventService.list_anomalous_events(req)
    return ListAnomalousEventsResponse(result=msg)


@router.get("/log/{log_id}", response_model=ListAnomalousEventsResponse)
async def list_anomalous_events_by_log_id(
    log_id: Annotated[str, Path()],
) -> ListAnomalousEventsResponse:
    """根据日志文件ID查询异常事件列表"""
    await ResourceIdService.require("log", log_id)
    msg = await AnomalousEventService.list_anomalous_events_by_log_id(log_id)
    return ListAnomalousEventsResponse(result=msg)
