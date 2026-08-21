# Copyright (c) Huawei Technologies Co., Ltd. 2023-2025. All rights reserved.
"""BRPC profiling 数据查询路由。"""

from fastapi import APIRouter, Path, Query
from typing import Annotated, Optional

from latency.database.managers.brpc_profiling_result import BrpcProfilingResultPGManager
from latency.schemas.response import BrpcProfilingDataResponse, BrpcProfilingDataMsg
from latency.exceptions import NotFoundBizException

router = APIRouter(prefix="/brpc_profiling", tags=["brpc_profiling"])


@router.get("/{log_id}", response_model=BrpcProfilingDataResponse)
async def get_brpc_profiling_data(
    log_id: Annotated[str, Path(description="日志文件 ID")],
    source_file: Annotated[Optional[str], Query(description="按源文件名过滤")] = None,
) -> BrpcProfilingDataResponse:
    """获取指定日志文件的 BRPC profiling 时序数据。

    返回按 timestamp 排序的完整数据，前端自行按接口名分组。
    可通过 source_file 参数过滤特定源文件的数据。
    """
    file_names = await BrpcProfilingResultPGManager.get_file_names_by_log_id(log_id)

    all_records = await BrpcProfilingResultPGManager.get_all_by_log_id(
        log_id, source_file=source_file
    )
    if not all_records:
        raise NotFoundBizException(resource="BRPC profiling 数据")

    interface_names = sorted(
        {r.interface_name for r in all_records}
    )

    rows = []
    for record in all_records:
        rows.append({
            "timestamp": record.timestamp.isoformat() if record.timestamp else None,
            "interface_name": record.interface_name,
            "source_file": record.source_file,
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
            file_names=file_names,
            rows=rows,
        ),
    )