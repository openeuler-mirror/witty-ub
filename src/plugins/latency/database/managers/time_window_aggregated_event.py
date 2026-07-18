# Copyright (c) Huawei Technologies Co., Ltd. 2023-2025. All rights reserved.
"""PostgreSQL-specific manager for time_window_aggregated.

The table only stores dimensions + counts; all statistics are computed on the
fly from log_parse_result via ordered-set aggregates.
"""
from __future__ import annotations

import logging
import time
from collections import defaultdict
from datetime import datetime, timedelta, timezone
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
]


<<<<<<< HEAD
@dataclass(slots=True)
class TimeWindowAggregatedEventDataclass:
    id: str = ""
    kb_id: str = ""
    log_id: str = ""
    time_bucket: str = ""
    src_ip: str = ""
    dst_ip: str = ""
    operation: str = ""
    log_parse_result_cnt: int = 0
    anomaly_cnt: int = 0
    ave_total_latency: float | None = None
    min_total_latency: float | None = None
    max_total_latency: float | None = None
    p99_total_latency: float | None = None
    p95_total_latency: float | None = None
    p9999_total_latency: float | None = None
    ave_query_meta_latency: float | None = None
    min_query_meta_latency: float | None = None
    max_query_meta_latency: float | None = None
    p99_query_meta_latency: float | None = None
    p95_query_meta_latency: float | None = None
    p9999_query_meta_latency: float | None = None
    ave_urma_total_latency: float | None = None
    min_urma_total_latency: float | None = None
    max_urma_total_latency: float | None = None
    p99_urma_total_latency: float | None = None
    p95_urma_total_latency: float | None = None
    p9999_urma_total_latency: float | None = None
    ave_urma_link_latency: float | None = None
    min_urma_link_latency: float | None = None
    max_urma_link_latency: float | None = None
    p99_urma_link_latency: float | None = None
    p95_urma_link_latency: float | None = None
    p9999_urma_link_latency: float | None = None
    ave_c2w_urma_latency: float | None = None
    min_c2w_urma_latency: float | None = None
    max_c2w_urma_latency: float | None = None
    p99_c2w_urma_latency: float | None = None
    p95_c2w_urma_latency: float | None = None
    p9999_c2w_urma_latency: float | None = None
    ave_w2w_urma_latency: float | None = None
    min_w2w_urma_latency: float | None = None
    max_w2w_urma_latency: float | None = None
    p99_w2w_urma_latency: float | None = None
    p95_w2w_urma_latency: float | None = None
    p9999_w2w_urma_latency: float | None = None
    ave_sdk_process: float | None = None
    min_sdk_process: float | None = None
    max_sdk_process: float | None = None
    p99_sdk_process: float | None = None
    p95_sdk_process: float | None = None
    p9999_sdk_process: float | None = None
    ave_sdk_rpc: float | None = None
    min_sdk_rpc: float | None = None
    max_sdk_rpc: float | None = None
    p99_sdk_rpc: float | None = None
    p95_sdk_rpc: float | None = None
    p9999_sdk_rpc: float | None = None
    ave_local_worker_cost: float | None = None
    min_local_worker_cost: float | None = None
    max_local_worker_cost: float | None = None
    p99_local_worker_cost: float | None = None
    p95_local_worker_cost: float | None = None
    p9999_local_worker_cost: float | None = None
    ave_local_worker_lock: float | None = None
    min_local_worker_lock: float | None = None
    max_local_worker_lock: float | None = None
    p99_local_worker_lock: float | None = None
    p95_local_worker_lock: float | None = None
    p9999_local_worker_lock: float | None = None
    ave_remote_worker_cost: float | None = None
    min_remote_worker_cost: float | None = None
    max_remote_worker_cost: float | None = None
    p99_remote_worker_cost: float | None = None
    p95_remote_worker_cost: float | None = None
    p9999_remote_worker_cost: float | None = None
    ave_remote_worker_rpc: float | None = None
    min_remote_worker_rpc: float | None = None
    max_remote_worker_rpc: float | None = None
    p99_remote_worker_rpc: float | None = None
    p95_remote_worker_rpc: float | None = None
    p9999_remote_worker_rpc: float | None = None
    ave_master_process: float | None = None
    min_master_process: float | None = None
    max_master_process: float | None = None
    p99_master_process: float | None = None
    p95_master_process: float | None = None
    p9999_master_process: float | None = None
    ave_master_rpc_total: float | None = None
    min_master_rpc_total: float | None = None
    max_master_rpc_total: float | None = None
    p99_master_rpc_total: float | None = None
    p95_master_rpc_total: float | None = None
    p9999_master_rpc_total: float | None = None
    ave_create_latency: float | None = None
    min_create_latency: float | None = None
    max_create_latency: float | None = None
    p99_create_latency: float | None = None
    p95_create_latency: float | None = None
    p9999_create_latency: float | None = None
    ave_publish_latency: float | None = None
    min_publish_latency: float | None = None
    max_publish_latency: float | None = None
    p99_publish_latency: float | None = None
    p95_publish_latency: float | None = None
    p9999_publish_latency: float | None = None
    ave_worker_total_latency: float | None = None
    min_worker_total_latency: float | None = None
    max_worker_total_latency: float | None = None
    p99_worker_total_latency: float | None = None
    p95_worker_total_latency: float | None = None
    p9999_worker_total_latency: float | None = None
    existed_status: bool = True
    created_at: str = field(
        default_factory=lambda: datetime.now().strftime(
            "%Y-%m-%d %H:%M:%S.%f"
        )[:-3]
    )
=======
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
>>>>>>> ee54a6a (sqlite切换pg)

    # Use COPY for large batches; INSERT is fine for smaller ones.
    _COPY_THRESHOLD = 1_000
    _COPY_BATCH_SIZE = 50_000

<<<<<<< HEAD
def _time_window_event_to_db_tuple(event: TimeWindowAggregatedEventDataclass) -> tuple:
    return (
        event.id,
        event.kb_id,
        event.log_id,
        event.time_bucket,
        event.src_ip,
        event.dst_ip,
        event.operation,
        event.log_parse_result_cnt,
        event.anomaly_cnt,
        event.ave_total_latency,
        event.min_total_latency,
        event.max_total_latency,
        event.p99_total_latency,
        event.p95_total_latency,
        event.p9999_total_latency,
        event.ave_query_meta_latency,
        event.min_query_meta_latency,
        event.max_query_meta_latency,
        event.p99_query_meta_latency,
        event.p95_query_meta_latency,
        event.p9999_query_meta_latency,
        event.ave_urma_total_latency,
        event.min_urma_total_latency,
        event.max_urma_total_latency,
        event.p99_urma_total_latency,
        event.p95_urma_total_latency,
        event.p9999_urma_total_latency,
        event.ave_urma_link_latency,
        event.min_urma_link_latency,
        event.max_urma_link_latency,
        event.p99_urma_link_latency,
        event.p95_urma_link_latency,
        event.p9999_urma_link_latency,
        event.ave_c2w_urma_latency,
        event.min_c2w_urma_latency,
        event.max_c2w_urma_latency,
        event.p99_c2w_urma_latency,
        event.p95_c2w_urma_latency,
        event.p9999_c2w_urma_latency,
        event.ave_w2w_urma_latency,
        event.min_w2w_urma_latency,
        event.max_w2w_urma_latency,
        event.p99_w2w_urma_latency,
        event.p95_w2w_urma_latency,
        event.p9999_w2w_urma_latency,
        event.ave_sdk_process,
        event.min_sdk_process,
        event.max_sdk_process,
        event.p99_sdk_process,
        event.p95_sdk_process,
        event.p9999_sdk_process,
        event.ave_sdk_rpc,
        event.min_sdk_rpc,
        event.max_sdk_rpc,
        event.p99_sdk_rpc,
        event.p95_sdk_rpc,
        event.p9999_sdk_rpc,
        event.ave_local_worker_cost,
        event.min_local_worker_cost,
        event.max_local_worker_cost,
        event.p99_local_worker_cost,
        event.p95_local_worker_cost,
        event.p9999_local_worker_cost,
        event.ave_local_worker_lock,
        event.min_local_worker_lock,
        event.max_local_worker_lock,
        event.p99_local_worker_lock,
        event.p95_local_worker_lock,
        event.p9999_local_worker_lock,
        event.ave_remote_worker_cost,
        event.min_remote_worker_cost,
        event.max_remote_worker_cost,
        event.p99_remote_worker_cost,
        event.p95_remote_worker_cost,
        event.p9999_remote_worker_cost,
        event.ave_remote_worker_rpc,
        event.min_remote_worker_rpc,
        event.max_remote_worker_rpc,
        event.p99_remote_worker_rpc,
        event.p95_remote_worker_rpc,
        event.p9999_remote_worker_rpc,
        event.ave_master_process,
        event.min_master_process,
        event.max_master_process,
        event.p99_master_process,
        event.p95_master_process,
        event.p9999_master_process,
        event.ave_master_rpc_total,
        event.min_master_rpc_total,
        event.max_master_rpc_total,
        event.p99_master_rpc_total,
        event.p95_master_rpc_total,
        event.p9999_master_rpc_total,
        event.ave_create_latency,
        event.min_create_latency,
        event.max_create_latency,
        event.p99_create_latency,
        event.p95_create_latency,
        event.p9999_create_latency,
        event.ave_publish_latency,
        event.min_publish_latency,
        event.max_publish_latency,
        event.p99_publish_latency,
        event.p95_publish_latency,
        event.p9999_publish_latency,
        event.ave_worker_total_latency,
        event.min_worker_total_latency,
        event.max_worker_total_latency,
        event.p99_worker_total_latency,
        event.p95_worker_total_latency,
        event.p9999_worker_total_latency,
        event.existed_status,
        event.created_at,
    )
=======
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
>>>>>>> ee54a6a (sqlite切换pg)

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
            parse_timestamp(event.created_at) or datetime.now(timezone.utc),
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

<<<<<<< HEAD
                    sql_str = """
                        INSERT INTO time_window_aggregated_table (
                            id, kb_id, log_id, time_bucket, src_ip, dst_ip, operation,
                            log_parse_result_cnt, anomaly_cnt,
                            ave_total_latency, min_total_latency, max_total_latency,
                            p99_total_latency, p95_total_latency, p9999_total_latency,
                            ave_query_meta_latency, min_query_meta_latency, max_query_meta_latency,
                            p99_query_meta_latency, p95_query_meta_latency, p9999_query_meta_latency,
                            ave_urma_total_latency, min_urma_total_latency, max_urma_total_latency,
                            p99_urma_total_latency, p95_urma_total_latency, p9999_urma_total_latency,
                            ave_urma_link_latency, min_urma_link_latency, max_urma_link_latency,
                            p99_urma_link_latency, p95_urma_link_latency, p9999_urma_link_latency,
                            ave_c2w_urma_latency, min_c2w_urma_latency, max_c2w_urma_latency,
                            p99_c2w_urma_latency, p95_c2w_urma_latency, p9999_c2w_urma_latency,
                            ave_w2w_urma_latency, min_w2w_urma_latency, max_w2w_urma_latency,
                            p99_w2w_urma_latency, p95_w2w_urma_latency, p9999_w2w_urma_latency,
                            ave_sdk_process, min_sdk_process, max_sdk_process,
                            p99_sdk_process, p95_sdk_process, p9999_sdk_process,
                            ave_sdk_rpc, min_sdk_rpc, max_sdk_rpc,
                            p99_sdk_rpc, p95_sdk_rpc, p9999_sdk_rpc,
                            ave_local_worker_cost, min_local_worker_cost, max_local_worker_cost,
                            p99_local_worker_cost, p95_local_worker_cost, p9999_local_worker_cost,
                            ave_local_worker_lock, min_local_worker_lock, max_local_worker_lock,
                            p99_local_worker_lock, p95_local_worker_lock, p9999_local_worker_lock,
                            ave_remote_worker_cost, min_remote_worker_cost, max_remote_worker_cost,
                            p99_remote_worker_cost, p95_remote_worker_cost, p9999_remote_worker_cost,
                            ave_remote_worker_rpc, min_remote_worker_rpc, max_remote_worker_rpc,
                            p99_remote_worker_rpc, p95_remote_worker_rpc, p9999_remote_worker_rpc,
                            ave_master_process, min_master_process, max_master_process,
                            p99_master_process, p95_master_process, p9999_master_process,
                            ave_master_rpc_total, min_master_rpc_total, max_master_rpc_total,
                            p99_master_rpc_total, p95_master_rpc_total, p9999_master_rpc_total,
                            ave_create_latency, min_create_latency, max_create_latency,
                            p99_create_latency, p95_create_latency, p9999_create_latency,
                            ave_publish_latency, min_publish_latency, max_publish_latency,
                            p99_publish_latency, p95_publish_latency, p9999_publish_latency,
                            ave_worker_total_latency, min_worker_total_latency, max_worker_total_latency,
                            p99_worker_total_latency, p95_worker_total_latency, p9999_worker_total_latency,
                            existed_status, created_at
                        ) VALUES (
                            ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
                            ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
                            ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
                            ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
                            ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
                            ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
                        )
                    """
                    for i in range(0, total_count, batch_size):
                        end = min(i + batch_size, total_count)
                        batch = (
                            _time_window_event_to_db_tuple(events[index])
                            for index in range(i, end)
                        )
                        conn.executemany(sql_str, batch)
=======
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
>>>>>>> ee54a6a (sqlite切换pg)

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
<<<<<<< HEAD
        operation: str | None = None,
    ) -> list[dict]:
        """获取时间窗口聚合事件"""
        db = AsyncSQLiteSingleton()

        conditions = ["existed_status = 1"]
        params = {}
        cte_sql = ""

        if kb_id:
            conditions.append("kb_id = :kb_id")
            params["kb_id"] = kb_id
=======
    ) -> list[dict[str, Any]]:
        """Real-time time-window aggregation from raw log_parse_result."""
        time_bucket = func.date_trunc("second", LogParseResult.timestamp).label(
            "time_bucket"
        )
>>>>>>> ee54a6a (sqlite切换pg)

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
        if kb_id:
            kb_subq = select(LogFile.id).where(LogFile.kb_id == kb_id).subquery()
            filters.append(LogParseResult.log_id.in_(select(kb_subq.c.id)))

<<<<<<< HEAD
        if operation:
            op = operation.upper()
            if op == "GET":
                conditions.append("(operation = :operation OR operation = '')")
            else:
                conditions.append("operation = :operation")
            params["operation"] = op

        sql_str = cte_sql + f"""
            SELECT id, kb_id, log_id, time_bucket, src_ip, dst_ip, operation,
                   log_parse_result_cnt, anomaly_cnt,
                   ave_total_latency, min_total_latency, max_total_latency,
                   p99_total_latency, p95_total_latency,
                   ave_query_meta_latency, min_query_meta_latency, max_query_meta_latency,
                   p99_query_meta_latency, p95_query_meta_latency,
                   ave_urma_total_latency, min_urma_total_latency, max_urma_total_latency,
                   p99_urma_total_latency, p95_urma_total_latency,
                   ave_urma_link_latency, min_urma_link_latency, max_urma_link_latency,
                   p99_urma_link_latency, p95_urma_link_latency,
                   ave_c2w_urma_latency, min_c2w_urma_latency, max_c2w_urma_latency,
                   p99_c2w_urma_latency, p95_c2w_urma_latency,
                   ave_w2w_urma_latency, min_w2w_urma_latency, max_w2w_urma_latency,
                   p99_w2w_urma_latency, p95_w2w_urma_latency,
                   ave_create_latency, min_create_latency, max_create_latency,
                   p99_create_latency, p95_create_latency, p9999_create_latency,
                   ave_publish_latency, min_publish_latency, max_publish_latency,
                   p99_publish_latency, p95_publish_latency, p9999_publish_latency,
                   ave_worker_total_latency, min_worker_total_latency, max_worker_total_latency,
                   p99_worker_total_latency, p95_worker_total_latency, p9999_worker_total_latency
            FROM time_window_aggregated_table
            WHERE {' AND '.join(conditions)}
            ORDER BY time_bucket ASC, src_ip ASC, dst_ip ASC
            LIMIT 50000
        """
=======
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
>>>>>>> ee54a6a (sqlite切换pg)

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
