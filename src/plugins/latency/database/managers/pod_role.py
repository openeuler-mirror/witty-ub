# Copyright (c) Huawei Technologies Co., Ltd. 2023-2025. All rights reserved.
"""PostgreSQL manager for pod_role (trace 级容器角色聚合表)."""
from __future__ import annotations

import logging
import uuid
from typing import Any, Iterator, Protocol

from sqlalchemy import select

from latency.database.engine import PGManager
from latency.database.models import PodRole
from latency.database.utils import parse_timestamp


logger = logging.getLogger(__name__)


class _PodRoleRows(Protocol):
    def __len__(self) -> int: ...
    def __iter__(self) -> Iterator[dict]: ...


class PodRolePGManager:
    """PostgreSQL-backed pod_role manager."""

    _INSERT_BATCH_SIZE = 1024

    @staticmethod
    def _normalize_pod_list(value: Any) -> list[str]:
        if isinstance(value, str):
            return [v.strip() for v in value.split(",") if v.strip()]
        if isinstance(value, list):
            return [str(v).strip() for v in value if v is not None and str(v).strip()]
        return []

    @staticmethod
    def _pod_role_dict_to_obj(event: dict) -> PodRole:
        param = dict(event)
        if not param.get("id"):
            param["id"] = str(uuid.uuid4())
        return PodRole(
            id=param["id"],
            log_id=param["log_id"],
            trace_id=param.get("trace_id") or "",
            operation=param.get("operation") or "",
            client_pod=param.get("client_pod") or None,
            entry_worker_pods=PodRolePGManager._normalize_pod_list(
                param.get("entry_worker_pods", [])
            ),
            meta_worker_pods=PodRolePGManager._normalize_pod_list(
                param.get("meta_worker_pods", [])
            ),
            data_worker_pods=PodRolePGManager._normalize_pod_list(
                param.get("data_worker_pods", [])
            ),
            timestamp=parse_timestamp(param.get("timestamp")) if param.get("timestamp") else None,
        )

    @staticmethod
    async def add_pod_role_raw(results: _PodRoleRows) -> list[str]:
        """批量写入 trace 级角色聚合，主键冲突（同一 trace 二次写入）自动跳过。"""
        ids_added: list[str] = []
        if not results:
            return ids_added

        objs = []
        for event in results:
            obj = PodRolePGManager._pod_role_dict_to_obj(event)
            objs.append(obj)
            ids_added.append(obj.trace_id or "")

        for i in range(0, len(objs), PodRolePGManager._INSERT_BATCH_SIZE):
            batch = objs[i : i + PodRolePGManager._INSERT_BATCH_SIZE]
            async with PGManager.session() as session:
                session.add_all(batch)
        return ids_added

    @staticmethod
    async def list_pod_roles_by_log_id(
        log_id: str,
    ) -> list[PodRole]:
        """按日志包查询该日志下所有 trace 的角色聚合。"""
        stmt = select(PodRole).where(PodRole.log_id == log_id)
        async with PGManager.session() as session:
            result = await session.execute(stmt)
            return list(result.scalars().all())

    @staticmethod
    async def list_pod_roles_by_trace_ids(
        trace_ids: list[str],
        log_ids: list[str] | None = None,
    ) -> list[PodRole]:
        """按 trace_id 集合查询角色聚合（日志详情页 / 通断总览用）。

        ``log_ids`` 为空时不做日志包过滤（跨所有日志包查询），与
        ``LogFailureEventPGManager.list_trace_failure_events`` 的 kb 语义一致。
        """
        if not trace_ids:
            return []
        stmt = select(PodRole).where(PodRole.trace_id.in_(trace_ids))
        if log_ids:
            stmt = stmt.where(PodRole.log_id.in_(log_ids))
        async with PGManager.session() as session:
            result = await session.execute(stmt)
            return list(result.scalars().all())

    @staticmethod
    async def delete_pod_roles_by_log_id(log_id: str) -> bool:
        """删除指定日志文件的所有 trace 角色聚合。"""
        async with PGManager.session() as session:
            from sqlalchemy import text

            await session.execute(
                text("DELETE FROM pod_role WHERE log_id = :log_id"),
                {"log_id": log_id},
            )
        return True
