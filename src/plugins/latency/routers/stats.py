# Copyright (c) Huawei Technologies Co., Ltd. 2023-2025. All rights reserved.

from typing import Annotated

from fastapi import APIRouter, Body

from latency.schemas.trace_light import (
    ErrorCodeStatsResponse,
    GetStageStatsRequest,
    GetStageStatsResponse,
    HeatmapStatsRequest,
    HeatmapStatsResponse,
    LinkStatsResponse,
    PodStatsResponse,
    StatsDimensionRequest,
)
from latency.services.resource_id import ResourceIdService
from latency.services.stats import StatsService

router = APIRouter(prefix="/stats", tags=["stats"])


@router.post(
    "/stages",
    response_model=GetStageStatsResponse,
    operation_id="get_stage_stats",
    description=(
        "主导问题分类（组件定位入口）：每条 trace 按最大互斥阶段归入唯一桶"
        "（winner-take-all），8 桶固定返回（含零计数桶），桶间计数可直接比较、"
        "合计 = 采样数。样本集 = 异常 trace 全量 + top 慢正常（合并去重，"
        "sample_cap 截断）。仅 GET 支持主导问题分类，SET 返回空 items + note。"
        "top_traces 为桶内证据耗时 Top 种子，可直接用于 /trace/list 批查节点集中度"
        "或 GET /trace/{id} 取代表证据。"
    ),
)
async def get_stage_stats(
    req: Annotated[GetStageStatsRequest, Body()],
) -> GetStageStatsResponse:
    await ResourceIdService.validate_request(req)
    msg = await StatsService.get_stage_stats(req)
    return GetStageStatsResponse(code=200, message="success", result=msg)


@router.post(
    "/error_codes",
    response_model=ErrorCodeStatsResponse,
    operation_id="get_error_code_stats",
    description=(
        "Top 故障码统计：trace 级 Counter（trace_cnt 降序，trace_failure_event "
        "按码 unnest 的 distinct trace 计数）+ 日志级事件数 event_cnt"
        "（log_failure_event 侧，无数据时为 null）。"
        "联动纪律：Top 码可直接作为 /trace/list 的 status_codes 过滤取值。"
    ),
)
async def get_error_code_stats(
    req: Annotated[StatsDimensionRequest, Body()],
) -> ErrorCodeStatsResponse:
    await ResourceIdService.validate_request(req)
    msg = await StatsService.get_error_code_stats(req)
    return ErrorCodeStatsResponse(code=200, message="success", result=msg)


@router.post(
    "/pods",
    response_model=PodStatsResponse,
    operation_id="get_pod_stats",
    description=(
        "Top Pod 统计：时延侧 pod 聚合（unnest pod_ips，多 Pod trace 在各 Pod "
        "均计数一次）+ 故障侧 join（fault_trace_cnt，fault_trace_cnt 降序）。"
        "联动纪律：Top Pod 可直接作为 /trace/list 的 pod_ip 过滤取值。"
    ),
)
async def get_pod_stats(
    req: Annotated[StatsDimensionRequest, Body()],
) -> PodStatsResponse:
    await ResourceIdService.validate_request(req)
    msg = await StatsService.get_pod_stats(req)
    return PodStatsResponse(code=200, message="success", result=msg)


@router.post(
    "/links",
    response_model=LinkStatsResponse,
    operation_id="get_link_stats",
    description=(
        "Top 源目对统计：时延侧 src/dst 聚合（仅统计两端均非空的链路）+ "
        "故障侧 join（fault_trace_cnt 降序）。"
        "联动纪律：Top 源目对可直接作为 /trace/list 的 src_ip/dst_ip 过滤取值。"
    ),
)
async def get_link_stats(
    req: Annotated[StatsDimensionRequest, Body()],
) -> LinkStatsResponse:
    await ResourceIdService.validate_request(req)
    msg = await StatsService.get_link_stats(req)
    return LinkStatsResponse(code=200, message="success", result=msg)


@router.post(
    "/heatmap",
    response_model=HeatmapStatsResponse,
    operation_id="get_heatmap_stats",
    description=(
        "时间热点统计：故障 trace 按时间槽计数（window_start 升序，仅含有数据"
        "时间槽）。window_size 缺省按时长自动（跨度≤2h→1m、≤48h→10m、否则 1h），"
        "自动模式下 slots 上限 240（超限自动放大窗口）；返回全部时间槽（≤240），"
        "top_n 不适用。跨槽 trace 在每个有事件的槽各计一次。"
    ),
)
async def get_heatmap_stats(
    req: Annotated[HeatmapStatsRequest, Body()],
) -> HeatmapStatsResponse:
    await ResourceIdService.validate_request(req)
    msg = await StatsService.get_heatmap_stats(req)
    return HeatmapStatsResponse(code=200, message="success", result=msg)
