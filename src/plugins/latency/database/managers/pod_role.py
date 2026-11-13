# Copyright (c) Huawei Technologies Co., Ltd. 2023-2025. All rights reserved.
"""PostgreSQL manager for pod_role (trace 级容器角色聚合表)."""
from __future__ import annotations

import logging
import uuid
from typing import Any, Iterator, Protocol

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert

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
        """批量写入 trace 级角色聚合，主键冲突（同一 trace 二次写入）自动跳过。

        id 为 ``uuid5(log_id:trace_id)`` 的确定性取值：任务重试、同一批日志被
        重复入库时必然命中已存在的行。必须用 ``ON CONFLICT DO NOTHING`` 落库，
        否则整批 insert 抛 UniqueViolationError 把任务打成失败。
        """
        ids_added: list[str] = []
        if not results:
            return ids_added

        rows: list[dict] = []
        for event in results:
            obj = PodRolePGManager._pod_role_dict_to_obj(event)
            ids_added.append(obj.trace_id or "")
            rows.append(
                {
                    "id": obj.id,
                    "log_id": obj.log_id,
                    "trace_id": obj.trace_id,
                    "operation": obj.operation,
                    "client_pod": obj.client_pod,
                    "entry_worker_pods": obj.entry_worker_pods,
                    "meta_worker_pods": obj.meta_worker_pods,
                    "data_worker_pods": obj.data_worker_pods,
                    "timestamp": obj.timestamp,
                }
            )

        for i in range(0, len(rows), PodRolePGManager._INSERT_BATCH_SIZE):
            batch = rows[i : i + PodRolePGManager._INSERT_BATCH_SIZE]
            stmt = (
                pg_insert(PodRole)
                .values(batch)
                .on_conflict_do_nothing(index_elements=["id"])
            )
            async with PGManager.session() as session:
                await session.execute(stmt)
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
