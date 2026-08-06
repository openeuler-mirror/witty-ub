# Copyright (c) Huawei Technologies Co., Ltd. 2023-2025. All rights reserved.
"""PostgreSQL-specific manager for anomalous_event."""
from __future__ import annotations

import logging
import time
from typing import Any

from sqlalchemy import desc, func, select, text
from sqlalchemy.dialects.postgresql import insert

from latency.database.engine import PGManager
from latency.database.models import AnomalousEvent, LogFile
from latency.database.utils import format_timestamp, parse_timestamp
from latency.schemas.log import AnomalousEventDataclass, AnomalousEventModel
from latency.schemas.request import ListAnomalousEventRequest

logger = logging.getLogger(__name__)


def _anomalous_event_to_mapping(event: AnomalousEventDataclass | AnomalousEventModel) -> dict[str, Any]:
    return {
        "id": event.id,
        "log_id": event.log_id,
        "aggregated_event_id": event.aggregated_event_id,
        "start_log_parse_offset": event.start_log_parse_offset,
        "end_log_parse_offset": event.end_log_parse_offset,
        "anomaly_reason": event.anomaly_reason,
        "existed_status": event.existed_status,
        "created_at": parse_timestamp(event.created_at),
    }


def _row_to_model(row: Any) -> AnomalousEventModel:
    data = dict(row)
    if "created_at" in data:
        data["created_at"] = format_timestamp(data["created_at"])
    return AnomalousEventModel(**data)


class AnomalousEventPGManager:
    _COPY_THRESHOLD = 1_000
    _COPY_BATCH_SIZE = 50_000

    _COPY_COLUMNS = [
        "id",
        "log_id",
        "aggregated_event_id",
        "start_log_parse_offset",
        "end_log_parse_offset",
        "anomaly_reason",
        "existed_status",
        "created_at",
    ]

    @staticmethod
    def _event_to_copy_tuple(event: AnomalousEventDataclass | AnomalousEventModel) -> tuple[Any, ...]:
        return (
            event.id,
            event.log_id,
            event.aggregated_event_id,
            event.start_log_parse_offset,
            event.end_log_parse_offset,
            event.anomaly_reason,
            event.existed_status,
            parse_timestamp(event.created_at),
        )

    @staticmethod
    async def add_anomalous_event(event: AnomalousEventModel) -> bool:
        async with PGManager.session() as session:
            await session.execute(insert(AnomalousEvent), [_anomalous_event_to_mapping(event)])
        return True

    @staticmethod
    async def add_anomalous_events(
        events: list[AnomalousEventDataclass] | list[AnomalousEventModel],
        batch_size: int = 50000,
    ) -> list[str]:
        if not events:
            return []
        ids_added = [e.id for e in events]

        if len(events) >= AnomalousEventPGManager._COPY_THRESHOLD:
            return await AnomalousEventPGManager._add_anomalous_events_copy(events)

        total = len(events)
        for i in range(0, total, batch_size):
            batch = events[i : i + batch_size]
            mappings = [_anomalous_event_to_mapping(e) for e in batch]
            async with PGManager.session() as session:
                await session.execute(insert(AnomalousEvent), mappings)
        return ids_added

    @staticmethod
    async def _add_anomalous_events_copy(
        events: list[AnomalousEventDataclass] | list[AnomalousEventModel],
    ) -> list[str]:
        t_start = time.perf_counter()
        records = [AnomalousEventPGManager._event_to_copy_tuple(e) for e in events]
        async with PGManager.connection() as conn:
            raw_conn = await conn.get_raw_connection()
            asyncpg_conn = raw_conn.driver_connection
            for i in range(0, len(records), AnomalousEventPGManager._COPY_BATCH_SIZE):
                batch = records[i : i + AnomalousEventPGManager._COPY_BATCH_SIZE]
                await asyncpg_conn.copy_records_to_table(
                    "anomalous_event",
                    records=batch,
                    columns=AnomalousEventPGManager._COPY_COLUMNS,
                )
        logger.info(
            "[Store][PG] COPY %s anomalous_event rows done in %.3fs",
            len(events),
            time.perf_counter() - t_start,
        )
        return [e.id for e in events]

    @staticmethod
    async def delete_anomalous_events_by_log_id(log_id: str) -> bool:
        """Hard delete all anomalous_event rows for a log_id."""
        async with PGManager.session() as session:
            await session.execute(
                text("DELETE FROM anomalous_event WHERE log_id = :log_id"),
                {"log_id": log_id},
            )
        return True

    @staticmethod
    async def update_anomalous_events_existed_status_by_log_id(
        log_id: str, existed_status: int
    ) -> bool:
        async with PGManager.session() as session:
            await session.execute(
                text("UPDATE anomalous_event SET existed_status = :existed_status WHERE log_id = :log_id"),
                {"log_id": log_id, "existed_status": bool(existed_status)},
            )
        return True

    @staticmethod
    async def list_anomalous_events_by_log_id(log_id: str) -> list[AnomalousEventModel]:
        async with PGManager.session() as session:
            result = await session.execute(
                select(
                    AnomalousEvent.id,
                    AnomalousEvent.log_id,
                    AnomalousEvent.aggregated_event_id,
                    AnomalousEvent.start_log_parse_offset,
                    AnomalousEvent.end_log_parse_offset,
                    AnomalousEvent.anomaly_reason,
                    AnomalousEvent.existed_status,
                    AnomalousEvent.created_at,
                )
                .where(AnomalousEvent.log_id == log_id, AnomalousEvent.existed_status == True)
                .order_by(desc(AnomalousEvent.created_at))
            )
            rows = result.mappings().all()
        return [_row_to_model(r) for r in rows]

    @staticmethod
    async def get_anomalous_event_by_id(event_id: str) -> AnomalousEventModel | None:
        async with PGManager.session() as session:
            result = await session.execute(
                select(
                    AnomalousEvent.id,
                    AnomalousEvent.log_id,
                    AnomalousEvent.aggregated_event_id,
                    AnomalousEvent.start_log_parse_offset,
                    AnomalousEvent.end_log_parse_offset,
                    AnomalousEvent.anomaly_reason,
                    AnomalousEvent.existed_status,
                    AnomalousEvent.created_at,
                ).where(AnomalousEvent.id == event_id)
            )
            row = result.mappings().first()
        if row is None:
            return None
        return _row_to_model(row)

    @staticmethod
    async def list_anomalous_events(
        req: ListAnomalousEventRequest,
    ) -> tuple[int, list[AnomalousEventModel]]:
        stmt = select(
            AnomalousEvent.id,
            AnomalousEvent.log_id,
            AnomalousEvent.aggregated_event_id,
            AnomalousEvent.start_log_parse_offset,
            AnomalousEvent.end_log_parse_offset,
            AnomalousEvent.anomaly_reason,
            AnomalousEvent.existed_status,
            AnomalousEvent.created_at,
        ).where(AnomalousEvent.existed_status == True)

        if req.log_id:
            stmt = stmt.where(AnomalousEvent.log_id == req.log_id)
        if req.aggregated_event_id:
            stmt = stmt.where(AnomalousEvent.aggregated_event_id == req.aggregated_event_id)

        if req.kb_id:
            stmt = stmt.join(LogFile, AnomalousEvent.log_id == LogFile.id).where(
                LogFile.kb_id == req.kb_id
            )

        count_stmt = select(func.count()).select_from(stmt.subquery())
        async with PGManager.session() as session:
            total = (await session.execute(count_stmt)).scalar() or 0

        sort_field_mapping = {
            "created_at": AnomalousEvent.created_at,
            "anomaly_reason": AnomalousEvent.anomaly_reason,
        }
        if req.sort_fields:
            for sort_field in req.sort_fields:
                col = sort_field_mapping.get(sort_field.field)
                if col is not None:
                    stmt = stmt.order_by(desc(col) if sort_field.order == "desc" else col)
        else:
            stmt = stmt.order_by(desc(AnomalousEvent.created_at))

        offset = (req.page_num - 1) * req.page_cnt
        stmt = stmt.offset(offset).limit(req.page_cnt)

        async with PGManager.session() as session:
            result = await session.execute(stmt)
            rows = result.mappings().all()
        events = [_row_to_model(r) for r in rows]
        return total, events
