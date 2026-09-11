# Copyright (c) Huawei Technologies Co., Ltd. 2023-2025. All rights reserved.
"""Parse-side configuration (no FastAPI dependency).

Workers spawned by the parallel scanner only need ``ParseConfig`` and its
small dependency chain (``StrictRequestModel`` / ``TimeStr`` / ``SortField``).
Keeping them here lets worker processes skip importing ``fastapi`` (~124ms
per process at spawn time), which is the dominant fixed cost when the scanner
spawns N child processes.

The API-side ``latency.schemas.request`` module re-exports everything below
for backward compatibility, so existing ``from latency.schemas.request import
ParseConfig`` imports keep working unchanged.
"""
from __future__ import annotations

from datetime import datetime

from pydantic import (
    AfterValidator,
    BaseModel,
    ConfigDict,
    Field,
)
from typing import Annotated, Optional


class StrictRequestModel(BaseModel):
    """Base class for API request payloads without implicit type coercion."""

    model_config = ConfigDict(strict=True)


def _validate_time_str(value: str) -> str:
    try:
        datetime.strptime(value, "%Y-%m-%d %H:%M:%S")
    except ValueError as exc:
        raise ValueError("时间必须使用 YYYY-MM-DD HH:MM:SS 格式") from exc
    return value


# Time-range filter strings shared by list/metrics requests and parse configs.
TimeStr = Annotated[str, AfterValidator(_validate_time_str)]


class SortField(StrictRequestModel):
    """
    排序字段配置

    用于配置单个排序字段及其排序方向
    """
    field: str = Field(description="排序字段名称")
    order: Optional[str] = Field(default="desc", description="排序方向：asc升序，desc降序")


class ParseConfig(StrictRequestModel):
    """
    日志解析配置

    用于配置解析器的行为，包括时间范围过滤、耗时阈值过滤等
    """
    start_time: Optional[TimeStr] = Field(
        default=None,
        description="日志内容时间范围开始，格式 YYYY-MM-DD HH:MM:SS"
    )
    end_time: Optional[TimeStr] = Field(
        default=None,
        description="日志内容时间范围结束，格式 YYYY-MM-DD HH:MM:SS"
    )
    min_elapsed_ms: Optional[int] = Field(
        default=None,
        description="最小耗时阈值（毫秒），用于过滤快速操作"
    )

    def is_time_filter_enabled(self) -> bool:
        """判断是否启用了时间过滤"""
        return self.start_time is not None or self.end_time is not None

    def is_elapsed_filter_enabled(self) -> bool:
        """判断是否启用了耗时过滤"""
        return self.min_elapsed_ms is not None
