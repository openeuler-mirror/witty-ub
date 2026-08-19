# Copyright (c) Huawei Technologies Co., Ltd. 2023-2025. All rights reserved.
"""BRPC profiling 数据查询路由。"""

from fastapi import APIRouter, Path
from typing import Annotated

from latency.database.managers.brpc_profiling_result import BrpcProfilingResultPGManager
from latency.schemas.response import BrpcProfilingDataResponse, BrpcProfilingDataMsg
from latency.exceptions import NotFoundBizException

router = APIRouter(prefix="/brpc_profiling", tags=["brpc_profiling"])


@router.get("/{log_id}", response_model=BrpcProfilingDataResponse)
async def get_brpc_profiling_data(
    log_id: Annotated[str, Path(description="日志文件 ID")],
) -> BrpcProfilingDataResponse:
    """获取指定日志文件的 BRPC profiling 时序数据。

    返回按 timestamp 排序的完整数据，前端自行按接口名分组。
    """
    timestamps = await BrpcProfilingResultPGManager.get_timestamps_by_log_id(log_id)
    if not timestamps:
        raise NotFoundBizException(resource="BRPC profiling 数据")

    # 一次性获取所有记录
    all_records = await BrpcProfilingResultPGManager.get_all_by_log_id(log_id)

    # 提取接口名列表（去重排序）
    interface_names = sorted(
        {r.interface_name for r in all_records}
    )

    # 构建数据行
    rows = []
    for record in all_records:
        rows.append({
            "timestamp": record.timestamp.isoformat() if record.timestamp else None,
            "interface_name": record.interface_name,
            "success_count": record.success_count,
            "failure_count": record.failure_count,
            "total_ns": record.total_ns,
            "avg_ns": record.avg_ns,
            "max_ns": record.max_ns,
            "min_ns": record.min_ns,
            "p50_ns": record.p50_ns,
            "p90_ns": record.p90_ns,
            "p95_ns": record.p95_ns,
            "p99_ns": record.p99_ns,
            "p999_ns": record.p999_ns,
        })

    return BrpcProfilingDataResponse(
        result=BrpcProfilingDataMsg(
            interface_names=interface_names,
            rows=rows,
        ),
    )