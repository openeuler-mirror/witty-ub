# Copyright (c) Huawei Technologies Co., Ltd. 2023-2024. All rights reserved.

from fastapi import APIRouter, Body
from typing import Annotated
from latency.schemas.request import ListAnomalousEventRequest
from latency.schemas.response import (
    GetAnomalousEventResponse,
    ListAnomalousEventsResponse,
)
from latency.services.anomalous_event import AnomalousEventService
from latency.services.resource_id import ResourceIdService
from latency.common.id_validation import ResourceIdPath

router = APIRouter(prefix="/anomalous_event", tags=["anomalous_event"])


@router.get("/{event_id}", response_model=GetAnomalousEventResponse)
async def get_anomalous_event_by_id(
    event_id: ResourceIdPath,
) -> GetAnomalousEventResponse:
    await ResourceIdService.require("anomalous_event", event_id)
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
    log_id: ResourceIdPath,
) -> ListAnomalousEventsResponse:
    """根据日志文件ID查询异常事件列表"""
    await ResourceIdService.require("log", log_id)
    msg = await AnomalousEventService.list_anomalous_events_by_log_id(log_id)
    return ListAnomalousEventsResponse(result=msg)
