# Copyright (c) Huawei Technologies Co., Ltd. 2023-2025. All rights reserved.
"""PostgreSQL-specific manager for time_window_aggregated.

The table only stores dimensions + counts; all statistics are computed on the
fly from log_parse_result via ordered-set aggregates.
"""
from __future__ import annotations

import logging
import time
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Any

import math
from sqlalchemy import Integer, func, insert, select, text

from latency.database.engine import PGManager
from latency.database.init import ensure_time_window_partitions
from latency.database.models import LogFile, LogParseResult, TimeWindowAggregated
from latency.database.utils import format_ip, parse_ip, parse_timestamp
from latency.schemas.log import TimeWindowAggregatedEventDataclass
from latency.schemas.request import ListTimeWindowAggregatedEventRequest

logger = logging.getLogger(__name__)

_LATENCY_FIELDS = [
    ("total_latency", LogParseResult.total_latency),
    ("query_meta_latency", LogParseResult.worker_query_meta_latency),
    ("urma_total_latency", LogParseResult.urma_total_latency),
    ("urma_link_latency", LogParseResult.urma_link_latency),
    ("c2w_urma_latency", LogParseResult.c2w_urma_latency),
    ("w2w_urma_latency", LogParseResult.w2w_urma_latency),
    ("create_latency", LogParseResult.create_latency),
    ("publish_latency", LogParseResult.publish_latency),
    ("worker_total_latency", LogParseResult.worker_total_latency),
]


class TimeWindowAggregatedEventPGManager:
    _TIME_WINDOW_COPY_COLUMNS = [
        "id",
        "time_bucket",
        "kb_id",
        "log_id",
        "src_ip",
        "dst_ip",
        "log_parse_result_cnt",
        "anomaly_cnt",
        "existed_status",
        "created_at",
    ]

    # Use COPY for large batches; INSERT is fine for smaller ones.
    _COPY_THRESHOLD = 1_000
    _COPY_BATCH_SIZE = 50_000

    @staticmethod
    def _event_to_mapping(
        event: TimeWindowAggregatedEventDataclass,
    ) -> dict[str, Any]:
        return {
            "id": event.id,
            "kb_id": event.kb_id,
            "log_id": event.log_id,
            "time_bucket": parse_timestamp(event.time_bucket),
            "src_ip": parse_ip(event.src_ip),
            "dst_ip": parse_ip(event.dst_ip),
            "log_parse_result_cnt": event.log_parse_result_cnt,
            "anomaly_cnt": event.anomaly_cnt,
            "existed_status": event.existed_status,
        }

    @staticmethod
    def _event_to_copy_tuple(
        event: TimeWindowAggregatedEventDataclass,
    ) -> tuple[Any, ...]:
        return (
            event.id,
            parse_timestamp(event.time_bucket),
            event.kb_id,
            event.log_id,
            parse_ip(event.src_ip),
            parse_ip(event.dst_ip),
            event.log_parse_result_cnt,
            event.anomaly_cnt,
            event.existed_status,
            parse_timestamp(event.created_at) or datetime.now(),
        )

    @staticmethod
    async def add_events(
        events: list[TimeWindowAggregatedEventDataclass],
    ) -> list[str]:
        if not events:
            return []

        # Determine the full time range covered by this batch and create any
        # missing monthly partitions up front.
        time_buckets = [
            parse_timestamp(e.time_bucket)
            for e in events
            if parse_timestamp(e.time_bucket) is not None
        ]
        if time_buckets:
            await ensure_time_window_partitions(min(time_buckets), max(time_buckets))

        total_count = len(events)
        if total_count >= TimeWindowAggregatedEventPGManager._COPY_THRESHOLD:
            return await TimeWindowAggregatedEventPGManager._add_events_copy(events)
        return await TimeWindowAggregatedEventPGManager._add_events_insert(events)

    @staticmethod
    async def _add_events_insert(
        events: list[TimeWindowAggregatedEventDataclass],
    ) -> list[str]:
        mappings = [
            TimeWindowAggregatedEventPGManager._event_to_mapping(e) for e in events
        ]
        async with PGManager.connection() as conn:
            await conn.execute(insert(TimeWindowAggregated), mappings)
        return [e.id for e in events]

    @staticmethod
    async def _add_events_copy(
        events: list[TimeWindowAggregatedEventDataclass],
    ) -> list[str]:
        """Bulk insert time-window events using asyncpg COPY.

        COPY is significantly faster than a large multi-row INSERT and avoids
        the per-statement parameter limit when workers produce tens of
        thousands of events.
        """
        t_start = time.perf_counter()
        records = [
            TimeWindowAggregatedEventPGManager._event_to_copy_tuple(e)
            for e in events
        ]
        async with PGManager.connection() as conn:
            raw_conn = await conn.get_raw_connection()
            asyncpg_conn = raw_conn.driver_connection
            columns = TimeWindowAggregatedEventPGManager._TIME_WINDOW_COPY_COLUMNS
            for i in range(0, len(records), TimeWindowAggregatedEventPGManager._COPY_BATCH_SIZE):
                batch = records[i : i + TimeWindowAggregatedEventPGManager._COPY_BATCH_SIZE]
                await asyncpg_conn.copy_records_to_table(
                    "time_window_aggregated",
                    records=batch,
                    columns=columns,
                )
        logger.info(
            "[Store][PG] COPY %s time_window_aggregated rows done in %.3fs",
            len(events),
            time.perf_counter() - t_start,
        )
        return [e.id for e in events]

    @staticmethod
    async def delete_by_log_id(log_id: str) -> bool:
        async with PGManager.connection() as conn:
            await conn.execute(
                text(
                    "UPDATE time_window_aggregated SET existed_status = FALSE "
                    "WHERE log_id = :log_id"
                ),
                {"log_id": log_id},
            )
        return True

    @staticmethod
    async def delete_by_kb_id(kb_id: str) -> bool:
        async with PGManager.connection() as conn:
            await conn.execute(
                text(
                    "UPDATE time_window_aggregated SET existed_status = FALSE "
                    "WHERE kb_id = :kb_id"
                ),
                {"kb_id": kb_id},
            )
        return True

    @staticmethod
    def _calc_percentile(sorted_vals: list[float], pct: float) -> float | None:
        if not sorted_vals:
            return None
        k = (pct / 100) * (len(sorted_vals) - 1)
        f = math.floor(k)
        c = math.ceil(k)
        if f == c:
            return sorted_vals[int(k)]
        d0 = sorted_vals[f] * (c - k)
        d1 = sorted_vals[c] * (k - f)
        return d0 + d1

    @staticmethod
    def _format_ip(value: Any) -> str:
        return format_ip(value) or ""

    @staticmethod
    async def get_time_window_events(
        log_id: str,
        *,
        kb_id: str = "",
        start_time: str = "",
        end_time: str = "",
        src_ip: str | None = None,
        dst_ip: str | None = None,
        cluster_name: str | None = None,
        host: str | None = None,
        pod_ip: str | None = None,
        operation: str | None = None,
    ) -> list[dict[str, Any]]:
        """Real-time time-window aggregation from raw log_parse_result."""
        time_bucket = func.date_trunc("second", LogParseResult.timestamp).label(
            "time_bucket"
        )

        filters = [
            LogParseResult.log_id == log_id,
            LogParseResult.existed_status.is_(True),
        ]
        if start_time:
            filters.append(LogParseResult.timestamp >= parse_timestamp(start_time))
        if end_time:
            filters.append(LogParseResult.timestamp <= parse_timestamp(end_time))
        if src_ip is not None:
            filters.append(LogParseResult.src_ip == parse_ip(src_ip))
        if dst_ip is not None:
            filters.append(LogParseResult.dst_ip == parse_ip(dst_ip))
        if cluster_name:
            filters.append(LogParseResult.cluster_name == cluster_name)
        if host:
            filters.append(LogParseResult.host == host)
        if pod_ip:
            filters.append(LogParseResult.pod_ips.contains([pod_ip]))
        if operation:
            filters.append(LogParseResult.operation.ilike(f"%{operation}%"))
        if kb_id:
            kb_subq = select(LogFile.id).where(LogFile.kb_id == kb_id).subquery()
            filters.append(LogParseResult.log_id.in_(select(kb_subq.c.id)))

        stats_columns = []
        for name, col in _LATENCY_FIELDS:
            stats_columns.append(func.avg(col).label(f"ave_{name}"))
            stats_columns.append(func.min(col).label(f"min_{name}"))
            stats_columns.append(func.max(col).label(f"max_{name}"))
            stats_columns.append(
                func.percentile_cont(0.95).within_group(col.asc()).label(f"p95_{name}")
            )
            stats_columns.append(
                func.percentile_cont(0.99).within_group(col.asc()).label(f"p99_{name}")
            )

        stmt = (
            select(
                LogParseResult.log_id,
                LogParseResult.src_ip,
                LogParseResult.dst_ip,
                time_bucket,
                func.count().label("log_parse_result_cnt"),
                func.sum(func.cast(LogParseResult.is_anomalous, Integer)).label(
                    "anomaly_cnt"
                ),
                *stats_columns,
            )
            .where(*filters)
            .group_by(
                LogParseResult.log_id,
                LogParseResult.src_ip,
                LogParseResult.dst_ip,
                time_bucket,
            )
            .order_by(time_bucket)
        )

        async with PGManager.session() as session:
            rows = (await session.execute(stmt)).all()
            formatted = []
            for r in rows:
                d = dict(r._mapping)
                d["src_ip"] = TimeWindowAggregatedEventPGManager._format_ip(d.get("src_ip"))
                d["dst_ip"] = TimeWindowAggregatedEventPGManager._format_ip(d.get("dst_ip"))
                formatted.append(d)
            return formatted

    @staticmethod
    async def list_time_window_events(
        req: ListTimeWindowAggregatedEventRequest,
    ) -> tuple[int, list[dict[str, Any]]]:
        """Return time-window aggregates with real-time statistics.

        Mirrors the SQLite ``SrcDstAggregatedEventManager.list_time_window_events``
        response shape so the service layer can swap backends transparently.
        """
        interval = req.interval if req.interval in ("second", "minute", "hour") else "minute"
        trunc_unit = {"second": "second", "minute": "minute", "hour": "hour"}[interval]
        interval_delta = {
            "second": timedelta(seconds=1),
            "minute": timedelta(minutes=1),
            "hour": timedelta(hours=1),
        }[interval]

        valid_stat_types = {"ave", "min", "max", "p95", "p99"}
        stat = req.stat_type if req.stat_type in valid_stat_types else "ave"

        time_bucket = func.date_trunc(trunc_unit, LogParseResult.timestamp).label(
            "time_bucket"
        )

        filters = [
            LogParseResult.existed_status.is_(True),
        ]
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

        if req.kb_id:
            kb_subq = select(LogFile.id).where(LogFile.kb_id == req.kb_id).subquery()
            filters.append(LogParseResult.log_id.in_(select(kb_subq.c.id)))

        # Build stat columns for all latency dimensions.
        stats_columns = []
        for name, col in _LATENCY_FIELDS:
            stats_columns.append(func.avg(col).label(f"ave_{name}"))
            stats_columns.append(func.min(col).label(f"min_{name}"))
            stats_columns.append(func.max(col).label(f"max_{name}"))
            stats_columns.append(
                func.percentile_cont(0.95).within_group(col.asc()).label(f"p95_{name}")
            )
            stats_columns.append(
                func.percentile_cont(0.99).within_group(col.asc()).label(f"p99_{name}")
            )

        stmt = (
            select(
                LogParseResult.log_id,
                LogParseResult.src_ip,
                LogParseResult.dst_ip,
                time_bucket,
                func.count().label("log_parse_result_cnt"),
                func.sum(func.cast(LogParseResult.is_anomalous, Integer)).label(
                    "anomaly_cnt"
                ),
                *stats_columns,
            )
            .where(*filters)
            .group_by(
                LogParseResult.log_id,
                LogParseResult.src_ip,
                LogParseResult.dst_ip,
                time_bucket,
            )
            .order_by(time_bucket)
        )

        async with PGManager.session() as session:
            rows = (await session.execute(stmt)).all()

        # Post-process into the same shape as the SQLite manager.
        def strip_port(ip: Any) -> str:
            if not ip:
                return ""
            s = str(ip)
            return s.rsplit(":", 1)[0] if ":" in s else s

        buckets: dict[str, dict] = defaultdict(
            lambda: {
                "start_time": "",
                "end_time": "",
                "total_cnt": 0,
                "anomaly_cnt": 0,
                "ip_pairs": [],
            }
        )

        for row in rows:
            bucket_dt: datetime = row.time_bucket
            bucket_key = bucket_dt.strftime("%Y-%m-%d %H:%M:%S")
            bucket = buckets[bucket_key]
            bucket["start_time"] = bucket_key
            bucket["end_time"] = (bucket_dt + interval_delta).strftime(
                "%Y-%m-%d %H:%M:%S"
            )
            bucket["total_cnt"] += row.log_parse_result_cnt or 0
            bucket["anomaly_cnt"] += row.anomaly_cnt or 0

            ip_pair = {
                "src_ip": strip_port(row.src_ip),
                "dst_ip": strip_port(row.dst_ip),
                "log_parse_result_cnt": row.log_parse_result_cnt or 0,
                "anomaly_log_parse_result_cnt": row.anomaly_cnt or 0,
                "anomaly_cnt": row.anomaly_cnt or 0,
            }
            for name, _ in _LATENCY_FIELDS:
                for st in ("ave", "min", "max", "p99", "p95"):
                    ip_pair[f"{st}_{name}"] = getattr(row, f"{st}_{name}")
            bucket["ip_pairs"].append(ip_pair)

        # Recompute bucket-level stats from ip_pair stats.
        for bucket in buckets.values():
            bucket["ip_pairs"].sort(
                key=lambda x: x.get("p99_total_latency") or 0, reverse=True
            )
            for name, _ in _LATENCY_FIELDS:
                for st in ("ave", "min", "max", "p99", "p95"):
                    vals = [
                        p[f"{st}_{name}"]
                        for p in bucket["ip_pairs"]
                        if p[f"{st}_{name}"] is not None
                    ]
                    if not vals:
                        bucket[f"{st}_{name}"] = None
                    elif st == "ave":
                        bucket[f"{st}_{name}"] = sum(vals) / len(vals)
                    elif st == "min":
                        bucket[f"{st}_{name}"] = min(vals)
                    elif st == "max":
                        bucket[f"{st}_{name}"] = max(vals)
                    else:
                        pct = 95.0 if st == "p95" else 99.0
                        bucket[f"{st}_{name}"] = (
                            TimeWindowAggregatedEventPGManager._calc_percentile(
                                sorted(vals), pct
                            )
                        )

        events = [buckets[k] for k in sorted(buckets.keys())]

        # Sorting.
        sort_field = req.sort_by or "start_time"
        sort_order = req.sort_order or "asc"
        if sort_fields := req.sort_fields:
            # Use the first sort field if provided.
            sort_field = sort_fields[0].field
            sort_order = sort_fields[0].order or "asc"

        def get_sort_value(event: dict) -> Any:
            if sort_field == "start_time":
                return event["start_time"]
            if sort_field == "total_cnt":
                return event["total_cnt"]
            if sort_field == "anomaly_cnt":
                return event["anomaly_cnt"]
            return event.get(f"{stat}_{sort_field}") or 0

        events.sort(key=get_sort_value, reverse=(sort_order == "desc"))

        total = len(events)
        offset = (req.page_num - 1) * req.page_cnt
        return total, events[offset : offset + req.page_cnt]
