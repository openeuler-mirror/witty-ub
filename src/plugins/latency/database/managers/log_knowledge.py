# Copyright (c) Huawei Technologies Co., Ltd. 2023-2025. All rights reserved.
"""PostgreSQL-specific manager for log_knowledge."""
from __future__ import annotations

import logging
from typing import Any

from sqlalchemy import desc, func, insert, select, text

from latency.database.engine import PGManager
from latency.database.models import LogKnowledge
from latency.database.utils import format_timestamp, parse_timestamp
from latency.schemas.log import LogKnowledgeModel
from latency.schemas.request import ListLogKnowledgeRequest


logger = logging.getLogger(__name__)


class LogKnowledgePGManager:
    @staticmethod
    def _model_to_mapping(log_kb: LogKnowledgeModel) -> dict[str, Any]:
        return {
            "id": log_kb.id,
            "name": log_kb.name,
            "description": log_kb.description,
            "image_bytes": log_kb.image_bytes,
            "total_count": log_kb.task_cnt,
            "anomalous_count": log_kb.anomaly_cnt,
            "failure_count": 0,
            "existed_status": log_kb.existed_status,
            "created_at": parse_timestamp(log_kb.created_at),
            "updated_at": parse_timestamp(log_kb.updated_at),
        }

    @staticmethod
    async def add_log_kb(log_kb_model: LogKnowledgeModel) -> str:
        async with PGManager.session() as session:
            await session.execute(
                insert(LogKnowledge), [LogKnowledgePGManager._model_to_mapping(log_kb_model)]
            )
        return log_kb_model.id

    @staticmethod
    async def add_log_kbs(log_kbs: list[LogKnowledgeModel]) -> list[str]:
        if not log_kbs:
            return []
        mappings = [LogKnowledgePGManager._model_to_mapping(kb) for kb in log_kbs]
        async with PGManager.session() as session:
            await session.execute(insert(LogKnowledge), mappings)
        return [kb.id for kb in log_kbs]

    @staticmethod
    async def delete_log_kb_by_kb_id(kb_id: str) -> bool:
        async with PGManager.session() as session:
            await session.execute(
                text("DELETE FROM log_knowledge WHERE id = :id"),
                {"id": kb_id},
            )
        return True

    @staticmethod
    async def update_log_kb(log_kb_id: str, log_kb_info_dict: dict) -> int:
        allowed = {k: v for k, v in log_kb_info_dict.items() if hasattr(LogKnowledge, k)}
        dropped = {k: v for k, v in log_kb_info_dict.items() if not hasattr(LogKnowledge, k)}
        if dropped:
            logger.warning("log_knowledge update dropped unknown keys: %s", list(dropped.keys()))
        if not allowed:
            return 0
        set_clauses = ", ".join(f"{k} = :{k}" for k in allowed)
        params = {"id": log_kb_id, **allowed}
        async with PGManager.session() as session:
            result = await session.execute(
                text(f"UPDATE log_knowledge SET {set_clauses}, updated_at = NOW() WHERE id = :id"),
                params,
            )
        return result.rowcount or 0

    @staticmethod
    async def count_log_kbs(req: ListLogKnowledgeRequest) -> int:
        stmt = select(func.count()).where(LogKnowledge.existed_status.is_(True))
        if req.name:
            stmt = stmt.where(LogKnowledge.name.ilike(f"%{req.name}%"))
        if req.description:
            stmt = stmt.where(LogKnowledge.description.ilike(f"%{req.description}%"))
        if req.created_at_start:
            stmt = stmt.where(LogKnowledge.created_at >= req.created_at_start)
        if req.created_at_end:
            stmt = stmt.where(LogKnowledge.created_at <= req.created_at_end)
        async with PGManager.session() as session:
            return (await session.execute(stmt)).scalar() or 0

    @staticmethod
    async def list_log_kbs(req: ListLogKnowledgeRequest) -> list[LogKnowledgeModel]:
        stmt = select(
            LogKnowledge.id,
            LogKnowledge.name,
            LogKnowledge.description,
            LogKnowledge.total_count,
            LogKnowledge.anomalous_count,
            LogKnowledge.existed_status,
            LogKnowledge.created_at,
            LogKnowledge.updated_at,
        ).where(LogKnowledge.existed_status.is_(True))
        if req.name:
            stmt = stmt.where(LogKnowledge.name.ilike(f"%{req.name}%"))
        if req.description:
            stmt = stmt.where(LogKnowledge.description.ilike(f"%{req.description}%"))
        if req.created_at_start:
            stmt = stmt.where(LogKnowledge.created_at >= req.created_at_start)
        if req.created_at_end:
            stmt = stmt.where(LogKnowledge.created_at <= req.created_at_end)

        if req.created_sorted_desc:
            stmt = stmt.order_by(desc(LogKnowledge.created_at))
        else:
            stmt = stmt.order_by(LogKnowledge.created_at)

        offset = (req.page_num - 1) * req.page_cnt
        stmt = stmt.offset(offset).limit(req.page_cnt)

        async with PGManager.session() as session:
            result = await session.execute(stmt)
            rows = result.mappings().all()
        return [
            LogKnowledgeModel.model_validate(
                {
                    **dict(r),
                    "task_cnt": r["total_count"],
                    "log_file_cnt": 0,
                    "anomaly_cnt": r["anomalous_count"],
                    "created_at": format_timestamp(r["created_at"]),
                    "updated_at": format_timestamp(r["updated_at"]),
                }
            )
            for r in rows
        ]

    @staticmethod
    async def get_log_kb_by_kb_id(kb_id: str) -> LogKnowledgeModel | None:
        async with PGManager.session() as session:
            result = await session.execute(
                select(LogKnowledge).where(
                    LogKnowledge.id == kb_id, LogKnowledge.existed_status.is_(True)
                )
            )
            row = result.scalar_one_or_none()
        if row is None:
            return None
        return LogKnowledgeModel.model_validate(
            {
                "id": row.id,
                "name": row.name,
                "description": row.description,
                "image_bytes": row.image_bytes,
                "task_cnt": row.total_count,
                "log_file_cnt": 0,
                "anomaly_cnt": row.anomalous_count,
                "existed_status": row.existed_status,
                "created_at": format_timestamp(row.created_at),
                "updated_at": format_timestamp(row.updated_at),
            }
        )
