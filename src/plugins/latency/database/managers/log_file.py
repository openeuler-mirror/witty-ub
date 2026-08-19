# Copyright (c) Huawei Technologies Co., Ltd. 2023-2025. All rights reserved.
"""PostgreSQL-specific manager for log_file."""
from __future__ import annotations

import logging
from typing import Any

from sqlalchemy import desc, func, insert, select, text

from latency.database.engine import PGManager
from latency.database.models import LogFile
from latency.database.utils import format_timestamp, parse_timestamp
from latency.schemas.log import LogFileModel
from latency.schemas.request import ListLogFilesRequest


logger = logging.getLogger(__name__)


class LogFilePGManager:
    @staticmethod
    def _model_to_mapping(log_file: LogFileModel) -> dict[str, Any]:
        return {
            "id": log_file.id,
            "kb_id": log_file.kb_id,
            "name": log_file.name,
            "parse_status": log_file.parse_status.value if log_file.parse_status else None,
            "file_path": log_file.file_path,
            "size": log_file.file_size,
            "total_count": 0,
            "anomalous_count": 0,
            "failure_count": 0,
            "log_type": getattr(log_file, "log_type", "kv-cache") or "kv-cache",
            "existed_status": log_file.existed_status,
            "created_at": parse_timestamp(log_file.created_at),
            "updated_at": parse_timestamp(log_file.created_at),
        }

    @staticmethod
    async def add_log_file(log_file: LogFileModel) -> bool:
        async with PGManager.session() as session:
            await session.execute(insert(LogFile), [LogFilePGManager._model_to_mapping(log_file)])
        return True

    @staticmethod
    async def add_log_files(log_files: list[LogFileModel]) -> list[str]:
        if not log_files:
            return []
        mappings = [LogFilePGManager._model_to_mapping(lf) for lf in log_files]
        async with PGManager.session() as session:
            await session.execute(insert(LogFile), mappings)
        return [lf.id for lf in log_files]

    @staticmethod
    async def delete_log_file_by_log_file_id(log_file_id: str) -> bool:
        async with PGManager.session() as session:
            await session.execute(
                text("DELETE FROM log_file WHERE id = :id"),
                {"id": log_file_id},
            )
        return True

    @staticmethod
    async def update_log_file(log_file_id: str, log_file_info_dict: dict) -> int:
        allowed = {
            k: v for k, v in log_file_info_dict.items() if hasattr(LogFile, k)
        }
        dropped = {k: v for k, v in log_file_info_dict.items() if not hasattr(LogFile, k)}
        if dropped:
            logger.warning("log_file update dropped unknown keys: %s", list(dropped.keys()))
        if not allowed:
            return 0
        set_clauses = ", ".join(f"{k} = :{k}" for k in allowed)
        params = {"id": log_file_id, **allowed}
        async with PGManager.session() as session:
            result = await session.execute(
                text(f"UPDATE log_file SET {set_clauses}, updated_at = NOW() WHERE id = :id"),
                params,
            )
        return result.rowcount or 0

    @staticmethod
    async def list_log_files(
        kb_id: str, req: ListLogFilesRequest
    ) -> tuple[int, list[LogFileModel]]:
        stmt = select(LogFile).where(LogFile.kb_id == kb_id, LogFile.existed_status.is_(True))
        if req.name:
            stmt = stmt.where(LogFile.name.ilike(f"%{req.name}%"))
        if req.parse_status:
            stmt = stmt.where(LogFile.parse_status == req.parse_status.value)
        if req.created_at_start:
            stmt = stmt.where(LogFile.created_at >= req.created_at_start)
        if req.created_at_end:
            stmt = stmt.where(LogFile.created_at <= req.created_at_end)

        count_stmt = select(func.count()).select_from(stmt.subquery())
        async with PGManager.session() as session:
            total = (await session.execute(count_stmt)).scalar() or 0

        if req.created_sorted_desc:
            stmt = stmt.order_by(desc(LogFile.created_at))
        else:
            stmt = stmt.order_by(LogFile.created_at)

        offset = (req.page_num - 1) * req.page_cnt
        stmt = stmt.offset(offset).limit(req.page_cnt)

        async with PGManager.session() as session:
            result = await session.execute(stmt)
            rows = result.scalars().all()

        log_files = []
        for row in rows:
            data = {
                "id": row.id,
                "kb_id": row.kb_id,
                "name": row.name,
                "parse_status": row.parse_status,
                "file_path": row.file_path,
                "file_size": row.size,
                "anomaly_cnt": row.anomalous_count,
                "trace_failure_event_cnt": row.failure_count or 0,
                "log_type": getattr(row, "log_type", "kv-cache") or "kv-cache",
                "existed_status": row.existed_status,
                "created_at": format_timestamp(row.created_at),
            }
            log_files.append(LogFileModel(**data))
        return total, log_files

    @staticmethod
    async def get_log_file_by_log_file_id(log_file_id: str) -> LogFileModel | None:
        async with PGManager.session() as session:
            result = await session.execute(
                select(LogFile).where(LogFile.id == log_file_id)
            )
            row = result.scalar_one_or_none()
        if row is None:
            return None
        data = {
            "id": row.id,
            "kb_id": row.kb_id,
            "name": row.name,
            "parse_status": row.parse_status,
            "file_path": row.file_path,
            "file_size": row.size,
            "anomaly_cnt": row.anomalous_count,
            "trace_failure_event_cnt": row.failure_count or 0,
            "log_type": getattr(row, "log_type", "kv-cache") or "kv-cache",
            "existed_status": row.existed_status,
            "created_at": format_timestamp(row.created_at),
        }
        return LogFileModel(**data)

    @staticmethod
    async def list_log_file_ids(
        kb_id: str | None = None, log_id: str | None = None
    ) -> list[str]:
        stmt = select(LogFile.id).where(LogFile.existed_status.is_(True))
        if kb_id:
            stmt = stmt.where(LogFile.kb_id == kb_id)
        if log_id:
            stmt = stmt.where(LogFile.id == log_id)
        stmt = stmt.order_by(LogFile.created_at.desc())
        async with PGManager.session() as session:
            result = await session.execute(stmt)
            return [r for r in result.scalars().all()]

    @staticmethod
    async def list_log_file_paths(
        kb_id: str | None = None, log_id: str | None = None
    ) -> list[tuple[str, str]]:
        stmt = select(LogFile.id, LogFile.file_path).where(
            LogFile.existed_status.is_(True)
        )
        if kb_id:
            stmt = stmt.where(LogFile.kb_id == kb_id)
        if log_id:
            stmt = stmt.where(LogFile.id == log_id)
        stmt = stmt.order_by(LogFile.created_at.desc())
        async with PGManager.session() as session:
            result = await session.execute(stmt)
            rows = result.mappings().all()
        return [(r["id"], r["file_path"]) for r in rows]
