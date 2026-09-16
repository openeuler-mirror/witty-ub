# Copyright (c) Huawei Technologies Co., Ltd. 2023-2025. All rights reserved.

from typing import Annotated, Optional

from fastapi import APIRouter, Body, Query

from latency.schemas.trace_light import (
    GetTraceResponse,
    ListTracesRequest,
    ListTracesResponse,
)
from latency.services.resource_id import ResourceIdService
from latency.services.trace import TraceService

router = APIRouter(prefix="/trace", tags=["trace"])


@router.post(
    "/list",
    response_model=ListTracesResponse,
    response_model_exclude_unset=True,
    operation_id="list_traces",
    description=(
        "trace 清单（粗筛主接口）：时延/故障双源合并，默认最小形态仅含"
        " trace_id/total_latency_ms/is_anomalous/operation 四个基础字段。"
        "include 指定的附加块（failure_codes/topology）才出现在响应里（非 null 占位）。"
        "sort_by=total_latency/timestamp 走时延侧原生排序（默认最快路径单查询）；"
        "sort_by=failure_cnt 以故障侧为主源按故障码计数排序（纯故障 trace 不丢条）。"
        "status_codes 过滤走故障侧语义（返回挂有任一指定故障码的 trace）。"
        "使用纪律：total > 500 时禁止翻页遍历，应收窄过滤或只取 Top。"
    ),
)
async def list_traces(
    req: Annotated[ListTracesRequest, Body()],
) -> ListTracesResponse:
    await ResourceIdService.validate_request(req)
    msg = await TraceService.list_traces(req)
    return ListTracesResponse(code=200, message="success", result=msg)


@router.get(
    "/{trace_id}",
    response_model=GetTraceResponse,
    response_model_exclude_unset=True,
    operation_id="get_trace",
    description=(
        "单 trace 下钻：一次拿全轻量画像（时延 + 故障码聚合 + 拓扑）。"
        "双源合并（log_parse_result + trace_failure_event），单侧缺失字段为 null/[]，"
        "不丢弃整条；timestamp 取故障侧最早日志时间，无故障记录时取解析侧时间。"
        "kb_id/log_id 为可选的作用域过滤，不传时按 trace_id 全局检索。"
    ),
)
async def get_trace(
    trace_id: str,
    kb_id: Annotated[Optional[str], Query(description="知识库ID，用于过滤")] = None,
    log_id: Annotated[Optional[str], Query(description="日志文件ID，用于过滤")] = None,
) -> GetTraceResponse:
    await ResourceIdService.require_trace_ids([trace_id])
    msg = await TraceService.get_trace(trace_id, kb_id=kb_id, log_id=log_id)
    return GetTraceResponse(code=200, message="success", result=msg)
