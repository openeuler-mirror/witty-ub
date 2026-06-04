# Copyright (c) Huawei Technologies Co., Ltd. 2023-2024. All rights reserved.

from fastapi import APIRouter, Body
from typing import Annotated
from latency.schemas.request import ListAnomalousEventChainRequest
from latency.schemas.response import (
    ListAnomalousEventChainsResponse,
)
from latency.services.anomalous_event_chain import AnomalousEventChainService

router = APIRouter(prefix="/anomalous_event_chain", tags=["anomalous_event_chain"])


@router.post("/list", response_model=ListAnomalousEventChainsResponse)
async def list_anomalous_event_chains(
    req: Annotated[ListAnomalousEventChainRequest, Body()],
) -> ListAnomalousEventChainsResponse:
    msg = await AnomalousEventChainService.list_event_chains(req)
    return ListAnomalousEventChainsResponse(result=msg)
