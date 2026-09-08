# Copyright (c) Huawei Technologies Co., Ltd. 2023-2025. All rights reserved.
"""UBSocket profiling 数据查询路由。"""

from typing import Annotated, Optional

from fastapi import APIRouter, Path, Query

from latency.database.managers.brpc_profiling_result import BrpcProfilingResultPGManager
from latency.exceptions import NotFoundBizException
from latency.schemas.response import BrpcProfilingDataMsg, BrpcProfilingDataResponse
from latency.services.resource_id import ResourceIdService

router = APIRouter(prefix="/brpc_profiling", tags=["brpc_profiling"])


def _build_profiling_response(
    all_records,
    file_names: list[str] | None = None,
    files: list[dict] | None = None,
):
    if not all_records:
        raise NotFoundBizException(resource="UBSocket profiling 数据")

    interface_names = sorted({r.interface_name for r in all_records})
    rows = [
        {
            "timestamp": record.timestamp.isoformat() if record.timestamp else None,
            "log_id": record.log_id,
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
        }
        for record in all_records
    ]
    return BrpcProfilingDataResponse(
        result=BrpcProfilingDataMsg(
            interface_names=interface_names,
            file_names=file_names or [],
            files=files or [],
            rows=rows,
        )
    )


@router.get("/knowledge/{kb_id}", response_model=BrpcProfilingDataResponse)
async def get_brpc_profiling_data_by_knowledge(
    kb_id: Annotated[str, Path(description="资产库 ID")],
    log_id: Annotated[Optional[str], Query(description="上传日志 ID")] = None,
    source_file: Annotated[Optional[str], Query(description="按源文件名过滤")] = None,
) -> BrpcProfilingDataResponse:
    """列出资产库全部 profiling 文件并返回当前所选文件的时序数据。"""
    await ResourceIdService.require("kb", kb_id)
    files = await BrpcProfilingResultPGManager.get_file_options_by_kb_id(kb_id)
    if files and log_id is None and source_file is None:
        log_id = files[0]["log_id"]
        source_file = files[0]["source_file"]
    all_records = await BrpcProfilingResultPGManager.get_all_by_kb_id(
        kb_id, source_file=source_file, log_id=log_id
    )
    return _build_profiling_response(all_records, files=files)


@router.get("/{log_id}", response_model=BrpcProfilingDataResponse)
async def get_brpc_profiling_data(
    log_id: Annotated[str, Path(description="日志文件 ID")],
    source_file: Annotated[Optional[str], Query(description="按源文件名过滤")] = None,
) -> BrpcProfilingDataResponse:
    """获取指定日志文件的 UBSocket profiling 时序数据。

    返回按 timestamp 排序的完整数据，前端自行按接口名分组。
    可通过 source_file 参数过滤特定源文件的数据。
    """
    await ResourceIdService.require("log", log_id)
    file_names = await BrpcProfilingResultPGManager.get_file_names_by_log_id(log_id)

    all_records = await BrpcProfilingResultPGManager.get_all_by_log_id(
        log_id, source_file=source_file
    )
    return _build_profiling_response(all_records, file_names)
