# Copyright (c) Huawei Technologies Co., Ltd. 2023-2024. All rights reserved.

from fastapi import APIRouter, Path, Body, Query
from typing import Annotated, Optional
from latency.schemas.request import ListLogParseResultRequest, ListTracesByHostRequest, GetLatencyMetricsRequest
from latency.schemas.response import (
    ListLogParseResultsResponse,
    GetLogParseResultResponse,
    ListTracesByHostResponse,
    GetLatencyMetricsResponse,
    GetLogParseOptionsResponse,
)
from latency.services.log_parse_result import LogParseResultService

router = APIRouter(prefix="/log_parse_result", tags=["log_parse_result"])


@router.post(
    "/list",
    response_model=ListLogParseResultsResponse,
    operation_id="list_latency_traces",
    description=(
        "List parsed latency traces. Filter by aggregate event, trace ID, operation, "
        "host, pod or IP pair. Results contain detailed latency components and "
        "anomaly markers used as diagnosis evidence."
    ),
)
async def list_log_parse_results(
    req: Annotated[ListLogParseResultRequest, Body()],
) -> ListLogParseResultsResponse:
    msg = await LogParseResultService.list_log_parse_results(req)
    return ListLogParseResultsResponse(result=msg)

@router.get(
    "/options",
    response_model=GetLogParseOptionsResponse,
    operation_id="list_clusters_hosts",
    description=(
        "List cluster and host filter values that actually exist in parsed logs. "
        "Use this before filtering by cluster or host instead of guessing names."
    ),
)
async def get_log_parse_options(
    kb_id: Annotated[Optional[str], Query(description="知识库ID，用于过滤")] = None,
) -> GetLogParseOptionsResponse:
    """获取日志解析选项（集群和主机名称列表）

    返回数据库中已有的集群名称和主机名称列表，用于前端下拉框选项。
    """
    msg = await LogParseResultService.get_log_parse_options(kb_id)
    return GetLogParseOptionsResponse(result=msg)

@router.get(
    "/{result_id}",
    response_model=GetLogParseResultResponse,
    operation_id="get_latency_trace",
    description=(
        "Get one parsed latency trace by result ID, including detailed latency "
        "components, topology fields, trace ID and anomaly markers."
    ),
)
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


@router.post(
    "/metrics/latency",
    response_model=GetLatencyMetricsResponse,
    operation_id="get_latency_metrics",
    description=(
        "Get latency metric time series for a knowledge base, host or IP pair. Use "
        "P99 for fault spikes and AVG for general trends. Respect the returned "
        "sampling metadata and do not describe sampled points as full raw data."
    ),
)
async def get_latency_metrics(
    req: Annotated[GetLatencyMetricsRequest, Body()],
) -> GetLatencyMetricsResponse:
    """获取延迟指标时间曲线数据

    指标计算完全采用 yuanrong_tool 口径：总时延及 24 项请求分段指标，
    包括 SDK/Master/Worker 处理、Worker Access、URMA、三类本地 RPC
    网络与框架拆分、两类 Client Direct RPC 网络与框架拆分，以及 URMA 并发数。
    所有新指标统一使用微秒（URMA 并发数除外）。

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
