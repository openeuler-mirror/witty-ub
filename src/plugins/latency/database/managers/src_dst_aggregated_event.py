# Copyright (c) Huawei Technologies Co., Ltd. 2023-2025. All rights reserved.
"""PostgreSQL-specific manager for src_dst_aggregated_event.

The table stores dimensions + counts; all statistics are computed on the fly
from log_parse_result via ordered-set aggregates.  The aggregate ``id`` column
is preserved so ``get_aggregated_event_by_id`` returns the same object that the
worker wrote.
"""
from __future__ import annotations

import logging
import time
from typing import Any

from sqlalchemy import Integer, case, func, select, text
from sqlalchemy.dialects.postgresql import insert

from latency.config.config import Config
from latency.database.engine import PGManager
from latency.database.models import LogFile, LogParseResult, SrcDstAggregatedEvent
from latency.database.utils import format_ip, format_timestamp, parse_ip, parse_timestamp
from latency.schemas.log import SrcDstAggregatedEventDataclass
from latency.schemas.request import ListSrcDstAggregatedEventRequest

logger = logging.getLogger(__name__)


class SrcDstAggregatedEventPGManager:
    _COPY_THRESHOLD = 1_000
    _COPY_BATCH_SIZE = 50_000

    _COPY_COLUMNS = [
        "id",
        "src_ip",
        "dst_ip",
        "log_id",
        "log_parse_result_cnt",
        "anomaly_log_parse_result_cnt",
        "anomaly_cnt",
        "existed_status",
        "created_at",
    ]

    @staticmethod
    def _format_row(row: dict[str, Any]) -> dict[str, Any]:
        row["src_ip"] = format_ip(row.get("src_ip")) or ""
        row["dst_ip"] = format_ip(row.get("dst_ip")) or ""
        return row

    @staticmethod
    def _event_to_mapping(event: SrcDstAggregatedEventDataclass) -> dict[str, Any]:
        return {
            "id": event.id,
            "src_ip": parse_ip(event.src_ip),
            "dst_ip": parse_ip(event.dst_ip),
            "log_id": event.log_id,
            "log_parse_result_cnt": event.log_parse_result_cnt,
            "anomaly_log_parse_result_cnt": event.anomaly_log_parse_result_cnt,
            "anomaly_cnt": event.anomaly_cnt,
            "existed_status": event.existed_status,
        }

    @staticmethod
    def _event_to_copy_tuple(event: SrcDstAggregatedEventDataclass) -> tuple[Any, ...]:
        return (
            event.id,
            parse_ip(event.src_ip),
            parse_ip(event.dst_ip),
            event.log_id,
            event.log_parse_result_cnt,
            event.anomaly_log_parse_result_cnt,
            event.anomaly_cnt,
            event.existed_status,
            parse_timestamp(event.created_at),
        )

    @staticmethod
    async def add_aggregated_events(
        events: list[SrcDstAggregatedEventDataclass],
    ) -> None:
        if not events:
            return
        if len(events) >= SrcDstAggregatedEventPGManager._COPY_THRESHOLD:
            await SrcDstAggregatedEventPGManager._add_aggregated_events_copy(events)
            return
        mappings = [
            SrcDstAggregatedEventPGManager._event_to_mapping(e) for e in events
        ]
        async with PGManager.connection() as conn:
            await conn.execute(insert(SrcDstAggregatedEvent), mappings)

    @staticmethod
    async def _add_aggregated_events_copy(
        events: list[SrcDstAggregatedEventDataclass],
    ) -> None:
        t_start = time.perf_counter()
        records = [SrcDstAggregatedEventPGManager._event_to_copy_tuple(e) for e in events]
        async with PGManager.connection() as conn:
            raw_conn = await conn.get_raw_connection()
            asyncpg_conn = raw_conn.driver_connection
            for i in range(0, len(records), SrcDstAggregatedEventPGManager._COPY_BATCH_SIZE):
                batch = records[i : i + SrcDstAggregatedEventPGManager._COPY_BATCH_SIZE]
                await asyncpg_conn.copy_records_to_table(
                    "src_dst_aggregated_event",
                    records=batch,
                    columns=SrcDstAggregatedEventPGManager._COPY_COLUMNS,
                )
        logger.info(
            "[Store][PG] COPY %s src_dst_aggregated_event rows done in %.3fs",
            len(events),
            time.perf_counter() - t_start,
        )

    @staticmethod
    def _stat_expr(col, stat_type: str):
        if stat_type == "p95":
            return func.percentile_cont(0.95).within_group(col.asc())
        if stat_type == "p99":
            return func.percentile_cont(0.99).within_group(col.asc())
        if stat_type == "ave":
            return func.avg(col)
        return getattr(func, stat_type)(col)

    @staticmethod
    def _stats_columns(field_map: dict[str, Any]) -> list[Any]:
        valid_stat_types = {"ave", "min", "max", "p95", "p99"}
        cols = []
        for name, col in field_map.items():
            for st in valid_stat_types:
                cols.append(
                    SrcDstAggregatedEventPGManager._stat_expr(col, st).label(
                        f"{st}_{name}"
                    )
                )
        return cols

    @staticmethod
    def _build_stats_subquery(
        req: ListSrcDstAggregatedEventRequest,
    ) -> Any:
        field_map = {
            "total_latency": LogParseResult.total_latency,
            "query_meta_latency": LogParseResult.worker_query_meta_latency,
            "urma_total_latency": LogParseResult.urma_total_latency,
            "urma_link_latency": LogParseResult.urma_link_latency,
            "c2w_urma_latency": LogParseResult.c2w_urma_latency,
            "w2w_urma_latency": LogParseResult.w2w_urma_latency,
        }

        filters = [LogParseResult.existed_status.is_(True)]
        if req.log_id:
            filters.append(LogParseResult.log_id == req.log_id)
        if req.start_time:
            filters.append(LogParseResult.timestamp >= parse_timestamp(req.start_time))
        if req.end_time:
            filters.append(LogParseResult.timestamp <= parse_timestamp(req.end_time))
        if req.src_ip:
            filters.append(
                func.host(LogParseResult.src_ip).like(f"%{req.src_ip}%")
            )
        if req.dst_ip:
            filters.append(
                func.host(LogParseResult.dst_ip).like(f"%{req.dst_ip}%")
            )
        if req.cluster_name:
            filters.append(LogParseResult.cluster_name == req.cluster_name)
        if req.host:
            filters.append(LogParseResult.host == req.host)
        if req.pod_ip:
            filters.append(LogParseResult.pod_ips.contains([req.pod_ip]))
        if req.operation:
            filters.append(LogParseResult.operation.ilike(f"%{req.operation}%"))

        return (
            select(
                LogParseResult.log_id,
                LogParseResult.src_ip,
                LogParseResult.dst_ip,
                func.count().label("log_parse_result_cnt"),
                func.sum(
                    case((LogParseResult.anomalous_event_id != "", 1), else_=0)
                ).label("anomaly_log_parse_result_cnt"),
                func.sum(func.cast(LogParseResult.is_anomalous, Integer)).label(
                    "anomaly_cnt"
                ),
                *SrcDstAggregatedEventPGManager._stats_columns(field_map),
            )
            .where(*filters)
            .group_by(
                LogParseResult.log_id, LogParseResult.src_ip, LogParseResult.dst_ip
            )
            .subquery()
        )

    @staticmethod
    async def list_aggregated_events(
        req: ListSrcDstAggregatedEventRequest,
    ) -> tuple[int, list[dict[str, Any]]]:
        """Return src/dst aggregates with real-time statistics.

        Mirrors the SQLite ``SrcDstAggregatedEventManager.list_aggregated_events``
        interface so the service layer can swap backends transparently.  The row
        ``id`` comes from the stored ``src_dst_aggregated_event`` row so the
        result is consistent with ``get_aggregated_event_by_id``.
        """
        valid_stat_types = {"ave", "min", "max", "p95", "p99"}
        stat = req.stat_type if req.stat_type in valid_stat_types else "ave"

        subq = SrcDstAggregatedEventPGManager._build_stats_subquery(req)

        selected_agg_cols = [
            SrcDstAggregatedEvent.id,
            SrcDstAggregatedEvent.src_ip,
            SrcDstAggregatedEvent.dst_ip,
            SrcDstAggregatedEvent.log_id,
            SrcDstAggregatedEvent.existed_status,
            SrcDstAggregatedEvent.created_at,
        ]
        stmt = (
            select(*selected_agg_cols, *subq.columns)
            .select_from(SrcDstAggregatedEvent)
            .join(
                subq,
                (
                    SrcDstAggregatedEvent.log_id == subq.c.log_id
                )
                & (SrcDstAggregatedEvent.src_ip == subq.c.src_ip)
                & (SrcDstAggregatedEvent.dst_ip == subq.c.dst_ip),
            )
            .where(SrcDstAggregatedEvent.existed_status.is_(True))
        )

        if req.log_id:
            stmt = stmt.where(SrcDstAggregatedEvent.log_id == req.log_id)
        if req.src_ip:
            stmt = stmt.where(
                func.host(SrcDstAggregatedEvent.src_ip).like(f"%{req.src_ip}%")
            )
        if req.dst_ip:
            stmt = stmt.where(
                func.host(SrcDstAggregatedEvent.dst_ip).like(f"%{req.dst_ip}%")
            )

        if req.kb_id:
            stmt = stmt.join(LogFile, SrcDstAggregatedEvent.log_id == LogFile.id).where(
                LogFile.kb_id == req.kb_id
            )

        sort_field_mapping = {
            "total_latency": subq.c[f"{stat}_total_latency"],
            "query_meta_latency": subq.c[f"{stat}_query_meta_latency"],
            "urma_total_latency": subq.c[f"{stat}_urma_total_latency"],
            "urma_link_latency": subq.c[f"{stat}_urma_link_latency"],
            "c2w_urma_latency": subq.c[f"{stat}_c2w_urma_latency"],
            "w2w_urma_latency": subq.c[f"{stat}_w2w_urma_latency"],
            "src_ip": SrcDstAggregatedEvent.src_ip,
            "dst_ip": SrcDstAggregatedEvent.dst_ip,
            "log_parse_result_cnt": subq.c.log_parse_result_cnt,
            "anomaly_log_parse_result_cnt": subq.c.anomaly_log_parse_result_cnt,
            "anomaly_cnt": subq.c.anomaly_cnt,
            "created_at": SrcDstAggregatedEvent.created_at,
        }

        order_clauses = []
        if req.sort_fields:
            for sf in req.sort_fields:
                col = sort_field_mapping.get(sf.field)
                if col is not None:
                    order_clauses.append(col.desc() if sf.order == "desc" else col.asc())
        if not order_clauses:
            order_clauses.append(sort_field_mapping["total_latency"].desc())

        count_stmt = select(func.count()).select_from(stmt.subquery())
        data_stmt = (
            stmt.order_by(*order_clauses)
            .limit(req.page_cnt)
            .offset((req.page_num - 1) * req.page_cnt)
        )

        async with PGManager.session() as session:
            total = (await session.execute(count_stmt)).scalar_one()
            rows = (await session.execute(data_stmt)).all()

        out: list[dict[str, Any]] = []
        for row in rows:
            mapping = dict(row._mapping)
            data: dict[str, Any] = {
                "id": mapping["id"],
                "src_ip": mapping["src_ip"],
                "dst_ip": mapping["dst_ip"],
                "log_id": mapping["log_id"],
                "log_parse_result_cnt": mapping.get("log_parse_result_cnt"),
                "anomaly_log_parse_result_cnt": mapping.get(
                    "anomaly_log_parse_result_cnt"
                ),
                "anomaly_cnt": mapping.get("anomaly_cnt"),
                "existed_status": mapping["existed_status"],
                "created_at": format_timestamp(mapping["created_at"]),
            }
            for name in [
                "total_latency",
                "query_meta_latency",
                "urma_total_latency",
                "urma_link_latency",
                "c2w_urma_latency",
                "w2w_urma_latency",
            ]:
                for st in valid_stat_types:
                    data[f"{st}_{name}"] = mapping.get(f"{st}_{name}")
            out.append(SrcDstAggregatedEventPGManager._format_row(data))
        return total, out

    @staticmethod
    async def get_aggregated_event_by_id(
        event_id: str,
    ) -> dict[str, Any] | None:
        """Look up the aggregate row by its UUID and compute real-time stats."""
        async with PGManager.session() as session:
            agg = await session.get(SrcDstAggregatedEvent, event_id)
            if agg is None or not agg.existed_status:
                return None

        field_map = {
            "total_latency": LogParseResult.total_latency,
            "query_meta_latency": LogParseResult.worker_query_meta_latency,
            "urma_total_latency": LogParseResult.urma_total_latency,
            "urma_link_latency": LogParseResult.urma_link_latency,
            "c2w_urma_latency": LogParseResult.c2w_urma_latency,
            "w2w_urma_latency": LogParseResult.w2w_urma_latency,
        }

        stmt = (
            select(
                LogParseResult.log_id,
                LogParseResult.src_ip,
                LogParseResult.dst_ip,
                func.count().label("log_parse_result_cnt"),
                func.sum(
                    case((LogParseResult.anomalous_event_id != "", 1), else_=0)
                ).label("anomaly_log_parse_result_cnt"),
                func.sum(func.cast(LogParseResult.is_anomalous, Integer)).label(
                    "anomaly_cnt"
                ),
                *SrcDstAggregatedEventPGManager._stats_columns(field_map),
            )
            .where(LogParseResult.log_id == agg.log_id)
            .where(LogParseResult.src_ip == agg.src_ip)
            .where(LogParseResult.dst_ip == agg.dst_ip)
            .where(LogParseResult.existed_status.is_(True))
            .group_by(LogParseResult.log_id, LogParseResult.src_ip, LogParseResult.dst_ip)
        )

        async with PGManager.session() as session:
            row = (await session.execute(stmt)).one_or_none()
            if row is None:
                return None
            data = dict(row._mapping)
            data["id"] = agg.id
            data["existed_status"] = agg.existed_status
            data["created_at"] = format_timestamp(agg.created_at)
            return SrcDstAggregatedEventPGManager._format_row(data)

    @staticmethod
    async def delete_aggregated_events_by_log_id(log_id: str) -> bool:
        """Hard delete all src/dst aggregates for a log_id."""
        async with PGManager.connection() as conn:
            await conn.execute(
                text("DELETE FROM src_dst_aggregated_event WHERE log_id = :log_id"),
                {"log_id": log_id},
            )
        return True

    @staticmethod
    async def update_aggregated_events_existed_status_by_log_id(
        log_id: str, existed_status: int
    ) -> bool:
        async with PGManager.connection() as conn:
            await conn.execute(
                text(
                    "UPDATE src_dst_aggregated_event "
                    "SET existed_status = :existed_status WHERE log_id = :log_id"
                ),
                {"log_id": log_id, "existed_status": bool(existed_status)},
            )
        return True
