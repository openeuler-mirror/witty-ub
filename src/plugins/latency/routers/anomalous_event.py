# Copyright (c) Huawei Technologies Co., Ltd. 2023-2024. All rights reserved.

from fastapi import APIRouter, Path
from typing import Annotated
from latency.schemas.response import (
    GetAnomalousEventResponse,
)
from latency.services.anomalous_event import AnomalousEventService

router = APIRouter(prefix="/anomalous_event", tags=["anomalous_event"])


@router.get("/{event_id}", response_model=GetAnomalousEventResponse)
async def get_anomalous_event_by_id(
    event_id: Annotated[str, Path()],
) -> GetAnomalousEventResponse:
    msg = await AnomalousEventService.get_anomalous_event_by_id(event_id)
    return GetAnomalousEventResponse(result=msg)
