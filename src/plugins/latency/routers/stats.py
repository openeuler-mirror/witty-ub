# Copyright (c) Huawei Technologies Co., Ltd. 2023-2025. All rights reserved.

from typing import Annotated

from fastapi import APIRouter, Body

from latency.schemas.trace_light import GetStageStatsRequest, GetStageStatsResponse
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
