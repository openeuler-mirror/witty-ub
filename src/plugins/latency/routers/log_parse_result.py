# Copyright (c) Huawei Technologies Co., Ltd. 2023-2024. All rights reserved.

from fastapi import APIRouter, Path, Body
from typing import Annotated
from latency.schemas.request import ListLogParseResultRequest, ListTracesByHostRequest, GetLatencyMetricsRequest
from latency.schemas.response import (
    ListLogParseResultsResponse,
    GetLogParseResultResponse,
    ListTracesByHostResponse,
    GetLatencyMetricsResponse,
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


@router.post("/traces/host/list", response_model=ListTracesByHostResponse)
async def list_traces_by_host(
    req: Annotated[ListTracesByHostRequest, Body()],
) -> ListTracesByHostResponse:
    """根据主机获取trace列表"""
    msg = await LogParseResultService.list_traces_by_host(req)
    return ListTracesByHostResponse(result=msg)


@router.post("/metrics/latency", response_model=GetLatencyMetricsResponse)
async def get_latency_metrics(
    req: Annotated[GetLatencyMetricsRequest, Body()],
) -> GetLatencyMetricsResponse:
    """获取延迟指标时间曲线数据（必选指标：total_latency, urma_total_latency, worker_query_meta_latency）

    采样模式说明：
    - none: 不采样，返回全部数据
    - max: 时间窗口内取最大值（保留峰值特征）
    - avg: 时间窗口内取平均值（平滑波动）
    - min: 时间窗口内取最小值
    - p95: 时间窗口内取 95 百分位
    - p99: 时间窗口内取 99 百分位（SLA 监控常用）
    - p9999: 时间窗口内取 99.99 百分位（严格 SLA 监控）
    """
    msg = await LogParseResultService.get_latency_metrics(req)
    return GetLatencyMetricsResponse(result=msg)
