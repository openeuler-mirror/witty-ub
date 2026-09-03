"""Existence validation shared by APIs that accept resource IDs."""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Iterable
from typing import Any

from latency.database.managers.resource_id import ResourceIdPGManager
from latency.exceptions import NotFoundBizException


class ResourceIdService:
    _RESOURCE_NAMES = {
        "kb": "知识库",
        "log": "日志文件",
        "task": "任务",
        "batch": "BRPC 诊断 batch",
        "aggregated_event": "聚合事件",
        "anomalous_event": "异常事件",
        "log_parse_result": "日志解析结果",
        "diagnosis_case": "诊断案例",
        "failure_mode": "故障模式",
        "trace": "Trace",
    }

    @staticmethod
    def _values(values: Iterable[str | None]) -> list[str]:
        return list(dict.fromkeys(value for value in values if value is not None))

    @classmethod
    async def require(cls, resource: str, *values: str | None) -> None:
        requested = cls._values(values)
        if not requested:
            return
        missing = await ResourceIdPGManager.find_missing(resource, requested)
        if missing:
            raise NotFoundBizException(
                resource=cls._RESOURCE_NAMES[resource],
                detail=f"不存在的 ID: {', '.join(missing)}",
            )

    @classmethod
    async def require_trace_ids(cls, values: Iterable[str]) -> None:
        requested = cls._values(values)
        if not requested:
            return
        missing = await ResourceIdPGManager.find_missing_trace_ids(requested)
        if missing:
            raise NotFoundBizException(
                resource=cls._RESOURCE_NAMES["trace"],
                detail=f"不存在的 trace_id: {', '.join(missing)}",
            )

    @classmethod
    async def validate_request(cls, req: Any) -> None:
        """Validate conventional ID fields on a Pydantic request model."""
        checks: list[Awaitable[None]] = []

        field_resources = {
            "kb_id": "kb",
            "log_id": "log",
            "aggregated_event_id": "aggregated_event",
            "op_id": "log",
        }
        for field, resource in field_resources.items():
            value = getattr(req, field, None)
            if value is not None:
                checks.append(cls.require(resource, value))

        source_log_ids = getattr(req, "source_log_ids", None) or []
        if source_log_ids:
            checks.append(cls.require("log", *source_log_ids))

        failure_mode_ids = getattr(req, "failure_mode_ids", None) or []
        if failure_mode_ids:
            checks.append(cls.require("failure_mode", *failure_mode_ids))

        trace_ids = list(getattr(req, "trace_ids", None) or [])
        trace_id = getattr(req, "trace_id", None)
        if trace_id is not None:
            trace_ids.append(trace_id)
        if trace_ids:
            checks.append(cls.require_trace_ids(trace_ids))

        if checks:
            await asyncio.gather(*checks)
