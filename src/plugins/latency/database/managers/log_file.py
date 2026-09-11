# Copyright (c) Huawei Technologies Co., Ltd. 2023-2025. All rights reserved.
"""PostgreSQL-specific manager for log_file."""
from __future__ import annotations

import logging
from typing import Any

from sqlalchemy import desc, func, insert, select, text

from latency.ENUM.general import DiagnosisConfigLogType
from latency.common.local_time import local_now, parse_asset_timestamp, utc_now
from latency.database.engine import PGManager
from latency.database.managers.log_knowledge import LogKnowledgePGManager
from latency.database.models import LogFile
from latency.database.utils import format_timestamp
from latency.schemas.log import LogFileModel
from latency.schemas.request import ListLogFilesRequest


logger = logging.getLogger(__name__)


class LogFilePGManager:
    # All data in these tables is derived from one log file.  Keep this list
    # close to the aggregate-root deletion below so a log cannot disappear
    # while leaving queryable parse/diagnosis rows behind.
    _DERIVED_TABLES_BY_LOG_ID = (
        "anomalous_event_chain",
        "anomalous_event",
        "src_dst_aggregated_event",
        "time_window_aggregated",
        "latency_bucket_10s",
        "latency_bucket_1min",
        "latency_bucket_10min",
        "latency_bucket_1h",
        "log_failure_event",
        "trace_failure_event",
        "brpc_profiling_result",
        "log_parse_result",
    )

    @staticmethod
    def _model_to_mapping(log_file: LogFileModel) -> dict[str, Any]:
        return {
            "id": log_file.id,
            "kb_id": log_file.kb_id,
            "name": log_file.name,
            "file_path": log_file.file_path,
            "size": log_file.file_size,
            "total_count": 0,
            "anomalous_count": 0,
            "failure_count": 0,
            "log_type": getattr(log_file, "log_type", DiagnosisConfigLogType.KVCACHE) or DiagnosisConfigLogType.KVCACHE,
            "existed_status": log_file.existed_status,
            "created_at": parse_asset_timestamp(log_file.created_at),
            "updated_at": parse_asset_timestamp(log_file.created_at),
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
            result = await session.execute(
                text("DELETE FROM log_file WHERE id = :id"),
                {"id": log_file_id},
            )
        return bool(result.rowcount)

    @staticmethod
    async def hard_delete_log_file_with_related_data(log_file_id: str) -> bool:
        """Hard-delete a log file and every per-log result in one transaction.

        The schema intentionally has few foreign keys because several result
        tables are partitioned.  Consequently the application owns the
        cascade.  Using one session here is important: either the complete
        aggregate is removed, or PGManager rolls the whole operation back.
        """
        params = {"log_id": log_file_id}
        async with PGManager.session() as session:
            # Read the owning KB before its row disappears so the aggregate
            # counters can be refreshed at the end of this transaction.
            kb_id = (
                await session.execute(
                    text("SELECT kb_id FROM log_file WHERE id = :log_id"), params
                )
            ).scalar_one_or_none()

            # A diagnosis case survives while it still has at least one
            # remaining source log.  Cases whose every source is this log are
            # removed entirely (signals first, they have no FK); cases that
            # also reference other logs only forget this log id.
            only_source_cond = (
                "COALESCE(source_log_ids, '[]'::jsonb) "
                "@> jsonb_build_array(CAST(:log_id AS text)) "
                "AND NOT EXISTS ("
                "SELECT 1 FROM jsonb_array_elements("
                "COALESCE(source_log_ids, '[]'::jsonb)) AS elem "
                "WHERE elem <> to_jsonb(CAST(:log_id AS text)))"
            )
            await session.execute(
                text(
                    "DELETE FROM diagnosis_case_signal WHERE case_id IN ("
                    f"SELECT id FROM diagnosis_case WHERE {only_source_cond})"
                ),
                params,
            )
            await session.execute(
                text(f"DELETE FROM diagnosis_case WHERE {only_source_cond}"),
                params,
            )
            await session.execute(
                text(
                    "UPDATE diagnosis_case SET source_log_ids = ("
                    "SELECT jsonb_agg(elem ORDER BY ord) FROM "
                    "jsonb_array_elements(COALESCE(source_log_ids, '[]'::jsonb)) "
                    "WITH ORDINALITY AS t(elem, ord) "
                    "WHERE t.elem <> to_jsonb(CAST(:log_id AS text))"
                    "), updated_at = :server_updated_at "
                    "WHERE COALESCE(source_log_ids, '[]'::jsonb) "
                    "@> jsonb_build_array(CAST(:log_id AS text))"
                ),
                {**params, "server_updated_at": local_now()},
            )

            # A UBSocket diagnosis is linked through task -> batch -> hit rather
            # than directly through log_id.  Delete children explicitly so
            # this also works on databases created before the CASCADE FK was
            # introduced.
            await session.execute(
                text(
                    "DELETE FROM brpc_diag_hit WHERE batch_id IN ("
                    "SELECT batch_id FROM brpc_diag_batch WHERE task_id IN ("
                    "SELECT id FROM task WHERE op_id = :log_id))"
                ),
                params,
            )
            await session.execute(
                text(
                    "DELETE FROM brpc_diag_batch WHERE task_id IN ("
                    "SELECT id FROM task WHERE op_id = :log_id)"
                ),
                params,
            )
            await session.execute(
                text(
                    "DELETE FROM task_report WHERE task_id IN ("
                    "SELECT id FROM task WHERE op_id = :log_id)"
                ),
                params,
            )
            await session.execute(
                text("DELETE FROM task WHERE op_id = :log_id"),
                params,
            )

            for table in LogFilePGManager._DERIVED_TABLES_BY_LOG_ID:
                await session.execute(
                    text(f"DELETE FROM {table} WHERE log_id = :log_id"),
                    params,
                )

            result = await session.execute(
                text("DELETE FROM log_file WHERE id = :log_id"),
                params,
            )
            if kb_id:
                await LogKnowledgePGManager.refresh_kb_counters(kb_id, session=session)
            return bool(result.rowcount)

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
        for key in ("created_at", "updated_at"):
            if key in allowed:
                allowed[key] = parse_asset_timestamp(allowed[key])
        allowed.pop("updated_at", None)  # The update time is generated below.
        set_clauses = ", ".join([*(f"{k} = :{k}" for k in allowed), "updated_at = :server_updated_at"])
        params = {"id": log_file_id, **allowed, "server_updated_at": utc_now()}
        async with PGManager.session() as session:
            result = await session.execute(
                text(f"UPDATE log_file SET {set_clauses} WHERE id = :id"),
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
        if req.created_at_start:
            stmt = stmt.where(LogFile.created_at >= parse_asset_timestamp(req.created_at_start))
        if req.created_at_end:
            stmt = stmt.where(LogFile.created_at <= parse_asset_timestamp(req.created_at_end))

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
                "file_path": row.file_path,
                "file_size": row.size,
                "anomaly_cnt": row.anomalous_count,
                "trace_failure_event_cnt": row.failure_count or 0,
                "log_type": getattr(row, "log_type", DiagnosisConfigLogType.KVCACHE) or DiagnosisConfigLogType.KVCACHE,
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
            "file_path": row.file_path,
            "file_size": row.size,
            "anomaly_cnt": row.anomalous_count,
            "trace_failure_event_cnt": row.failure_count or 0,
            "log_type": getattr(row, "log_type", DiagnosisConfigLogType.KVCACHE) or DiagnosisConfigLogType.KVCACHE,
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
