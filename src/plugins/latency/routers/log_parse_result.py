# Copyright (c) Huawei Technologies Co., Ltd. 2023-2024. All rights reserved.

from fastapi import APIRouter, Path, Body, Query
from typing import Annotated, Optional
from latency.schemas.request import ListLogParseResultRequest, ListTracesByHostRequest
from latency.schemas.response import (
    ListLogParseResultsResponse,
    GetLogParseResultResponse,
    ListTracesByHostResponse,
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


@router.get("/traces/host/{host}", response_model=ListTracesByHostResponse)
async def list_traces_by_host(
    host: Annotated[str, Path(description="主机名或IP地址")],
    start_time: Annotated[Optional[str], Query(description="开始时间，格式为YYYY-MM-DD HH:MM:SS")] = None,
    end_time: Annotated[Optional[str], Query(description="结束时间，格式为YYYY-MM-DD HH:MM:SS")] = None,
    operation: Annotated[Optional[str], Query(description="操作类型过滤：GET / SET")] = None,
    page_cnt: Annotated[int, Query(description="每页数量")] = 20,
    page_num: Annotated[int, Query(description="页码")] = 1,
    sort_by: Annotated[str, Query(description="排序字段")] = "timestamp",
    sort_order: Annotated[str, Query(description="排序方向")] = "desc",
) -> ListTracesByHostResponse:
    """根据主机获取trace列表"""
    req = ListTracesByHostRequest(
        host=host,
        start_time=start_time,
        end_time=end_time,
        operation=operation,
        page_cnt=page_cnt,
        page_num=page_num,
        sort_by=sort_by,
        sort_order=sort_order,
    )
    msg = await LogParseResultService.list_traces_by_host(req)
    return ListTracesByHostResponse(result=msg)
