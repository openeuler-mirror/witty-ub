# Copyright (c) Huawei Technologies Co., Ltd. 2023-2024. All rights reserved.

from fastapi import APIRouter, Path, Body
from typing import Annotated
from latency.schemas.request import ListLogParseResultRequest
from latency.schemas.response import (
    ListLogParseResultsResponse,
    GetLogParseResultResponse,
)
from latency.services.log_parse_result import LogParseResultService

router = APIRouter(prefix="/log_parse_result", tags=["log_parse_result"])


@router.post("/list", response_model=ListLogParseResultsResponse)
async def list_log_parse_results(
    req: Annotated[ListLogParseResultRequest, Body()],
) -> ListLogParseResultsResponse:
    msg = await LogParseResultService.list_log_parse_results(req)
    return ListLogParseResultsResponse(result=msg)


@router.get("/{result_id}", response_model=GetLogParseResultResponse)
async def get_log_parse_result_by_id(
    result_id: Annotated[str, Path()],
) -> GetLogParseResultResponse:
    msg = await LogParseResultService.get_log_parse_result_by_id(result_id)
    return GetLogParseResultResponse(result=msg)
