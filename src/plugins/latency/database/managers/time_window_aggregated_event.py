# Copyright (c) Huawei Technologies Co., Ltd. 2023-2025. All rights reserved.
"""PostgreSQL-specific manager for time_window_aggregated.

The table only stores dimensions + counts; all statistics are computed on the
fly from log_parse_result via ordered-set aggregates.
"""
from __future__ import annotations

import logging
import time
from datetime import datetime, timezone
from typing import Any, Sequence

from sqlalchemy import Integer, func, insert, select, text

from latency.database.engine import PGManager
from latency.database.init import ensure_time_window_partitions
from latency.database.models import LogFile, LogParseResult, TimeWindowAggregated
from latency.database.utils import format_ip, parse_ip, parse_timestamp
from latency.schemas.log import TimeWindowAggregatedEventDataclass, YUANRONG_METRIC_FIELDS
from latency.schemas.request import ListTimeWindowAggregatedEventRequest

logger = logging.getLogger(__name__)


def _keep_min(a: float | None, b: float | None) -> float | None:
    if a is None:
        return b
    if b is None:
        return a
    return a if a < b else b


def _keep_max(a: float | None, b: float | None) -> float | None:
    if a is None:
        return b
    if b is None:
        return a
    return a if a > b else b


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

_YUANRONG_BREAKDOWN_FIELDS = [
    (name, getattr(LogParseResult, name))
    for name in YUANRONG_METRIC_FIELDS
    if name != "request_mode"
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
        "ave_total_latency",
        "latency_sum",
        "min_total_latency",
        "max_total_latency",
        "p95_total_latency",
        "p99_total_latency",
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
            "ave_total_latency": event.ave_total_latency,
            "latency_sum": event.latency_sum,
            "min_total_latency": event.min_total_latency,
            "max_total_latency": event.max_total_latency,
            "p95_total_latency": event.p95_total_latency,
            "p99_total_latency": event.p99_total_latency,
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
            event.ave_total_latency,
            event.latency_sum,
            event.min_total_latency,
            event.max_total_latency,
            event.p95_total_latency,
            event.p99_total_latency,
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
        for name, col in _YUANRONG_BREAKDOWN_FIELDS:
            stats_columns.append(func.avg(col).label(f"ave_{name}"))

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

    _VALID_INTERVALS: tuple[int, ...] = (10, 60, 600, 3600)

    @staticmethod
    def _normalize_interval(interval: Any) -> int:
        """Map request interval (seconds or legacy name) to one of 10/60/600/3600."""
        if isinstance(interval, str):
            interval = {"second": 10, "minute": 60, "hour": 3600}.get(
                interval.strip().lower(), 60
            )
        try:
            secs = int(interval)
        except (TypeError, ValueError):
            secs = 60
        if secs not in TimeWindowAggregatedEventPGManager._VALID_INTERVALS:
            secs = min(
                TimeWindowAggregatedEventPGManager._VALID_INTERVALS,
                key=lambda v: abs(v - secs),
            )
        return secs

    @staticmethod
    def _epoch_to_str(epoch_sec: int) -> str:
        return datetime.fromtimestamp(epoch_sec, tz=timezone.utc).strftime(
            "%Y-%m-%d %H:%M:%S"
        )

    @staticmethod
    def _rows_to_events(
        rows: Sequence[Any],
        interval: int,
        req: ListTimeWindowAggregatedEventRequest,
    ) -> tuple[int, list[dict[str, Any]]]:
        """Assemble parent/child time-window dicts from aggregated SQL rows.

        Each row is already aggregated per (interval bucket, src_ip, dst_ip):
        cnt/anomaly summed, ave_total_latency computed by SQL as
        sum(latency_sum)/sum(cnt) (with COALESCE fallback for old rows), and
        p99 pre-computed by SQL as percentile_cont(0.99) over the inner 10s rows
        (p99-of-p99s approximation for coarse intervals; single-row passthrough
        for interval=10s).  Parent rows sum cnt/anomaly across IP pairs and
        recompute a cnt-weighted average.
        """
        buckets: dict[int, dict[str, Any]] = {}
        for row in rows:
            bep: int = int(row.bucket_epoch)
            bucket = buckets.get(bep)
            if bucket is None:
                bucket = {
                    "start_time": "",
                    "end_time": "",
                    "total_cnt": 0,
                    "anomaly_cnt": 0,
                    "ave_total_latency": None,
                    "_ave_num": 0.0,
                    "_ave_den": 0,
                    "min_total_latency": None,
                    "max_total_latency": None,
                    "p95_total_latency": None,
                    "p99_total_latency": None,
                    "ip_pairs": [],
                }
                buckets[bep] = bucket
            cnt = int(row.total_cnt or 0)
            anomaly = int(row.anomaly_cnt or 0)
            bucket["total_cnt"] += cnt
            bucket["anomaly_cnt"] += anomaly
            if row.ave is not None:
                bucket["_ave_num"] += row.ave * cnt
                bucket["_ave_den"] += cnt

            src_str = TimeWindowAggregatedEventPGManager._format_ip(row.src_ip)
            dst_str = TimeWindowAggregatedEventPGManager._format_ip(row.dst_ip)
            pair = next(
                (p for p in bucket["ip_pairs"] if p["src_ip"] == src_str and p["dst_ip"] == dst_str),
                None,
            )
            if pair is None:
                pair = {
                    "src_ip": src_str,
                    "dst_ip": dst_str,
                    "log_parse_result_cnt": 0,
                    "anomaly_log_parse_result_cnt": 0,
                    "anomaly_cnt": 0,
                    "ave_total_latency": None,
                    "min_total_latency": None,
                    "max_total_latency": None,
                    "p95_total_latency": None,
                    "p99_total_latency": None,
                    "_ave_num": 0.0,
                    "_ave_den": 0,
                }
                bucket["ip_pairs"].append(pair)
            pair["log_parse_result_cnt"] += cnt
            pair["anomaly_log_parse_result_cnt"] += anomaly
            pair["anomaly_cnt"] += anomaly
            if row.ave is not None:
                pair["_ave_num"] += row.ave * cnt
                pair["_ave_den"] += cnt
            pair["min_total_latency"] = _keep_min(pair["min_total_latency"], row.min_lat)
            pair["max_total_latency"] = _keep_max(pair["max_total_latency"], row.max_lat)
            pair["p95_total_latency"] = _keep_max(pair["p95_total_latency"], row.p95)
            pair["p99_total_latency"] = _keep_max(pair["p99_total_latency"], row.p99)

        events: list[dict[str, Any]] = []
        for bep in sorted(buckets):
            b = buckets[bep]
            b["start_time"] = TimeWindowAggregatedEventPGManager._epoch_to_str(bep)
            b["end_time"] = TimeWindowAggregatedEventPGManager._epoch_to_str(
                bep + interval
            )
            b["ave_total_latency"] = (
                b["_ave_num"] / b["_ave_den"] if b["_ave_den"] else None
            )
            b.pop("_ave_num")
            b.pop("_ave_den")
            for pair in b["ip_pairs"]:
                pair["ave_total_latency"] = (
                    pair["_ave_num"] / pair["_ave_den"] if pair["_ave_den"] else None
                )
                pair.pop("_ave_num")
                pair.pop("_ave_den")
            # Propagate min/max/p95/p99 from child ip_pairs to parent bucket.
            # min = min of children, max/p95/p99 = max of children (worst-path proxy).
            for pair in b["ip_pairs"]:
                b["min_total_latency"] = _keep_min(b["min_total_latency"], pair["min_total_latency"])
                b["max_total_latency"] = _keep_max(b["max_total_latency"], pair["max_total_latency"])
                b["p95_total_latency"] = _keep_max(b["p95_total_latency"], pair["p95_total_latency"])
                b["p99_total_latency"] = _keep_max(b["p99_total_latency"], pair["p99_total_latency"])
            b["ip_pairs"].sort(
                key=lambda p: p.get("ave_total_latency") or 0, reverse=True
            )
            events.append(b)

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
            return event.get(f"ave_{sort_field}") or event.get(sort_field) or 0

        events.sort(key=get_sort_value, reverse=(sort_order == "desc"))

        total = len(events)
        offset = (req.page_num - 1) * req.page_cnt
        return total, events[offset : offset + req.page_cnt]

    @staticmethod
    async def _attach_yuanrong_breakdown(
        events: list[dict[str, Any]],
        req: ListTimeWindowAggregatedEventRequest,
        interval: int,
    ) -> None:
        """TODO(Issue 2 follow-up): 分位桶表已携带 26 项 yuanrong 代表行值后，本方法仍对
        log_parse_result（仅 top1000+异常 trace）做 func.avg()，曲线数据不完整。
        未来应改读 latency_bucket_*；注意语义差异——桶表是每 (bucket, op, mode) 的
        代表行原始值，而这里是全量 trace 的均值，两者口径不同，需先对齐前端展示语义。

        补齐当前页的 yuanrong_tool 分阶段均值。

        主列表仍从物化时间窗口表读取；这里只对已经分页出的时间桶查询明细表，
        因而保留上游预聚合路径的性能收益，同时避免横向时延柱只剩旧指标颜色。
        """
        if not events:
            return

        bucket_epochs = {
            int(
                datetime.strptime(event["start_time"], "%Y-%m-%d %H:%M:%S")
                .replace(tzinfo=timezone.utc)
                .timestamp()
            )
            for event in events
        }
        bucket_epoch = (
            func.floor(func.extract("epoch", LogParseResult.timestamp) / interval)
            .cast(Integer)
            * interval
        ).label("bucket_epoch")

        filters = [
            LogParseResult.existed_status.is_(True),
            bucket_epoch.in_(bucket_epochs),
        ]
        if req.kb_id:
            kb_subq = select(LogFile.id).where(LogFile.kb_id == req.kb_id).subquery()
            filters.append(LogParseResult.log_id.in_(select(kb_subq.c.id)))
        if req.start_time:
            filters.append(LogParseResult.timestamp >= parse_timestamp(req.start_time))
        if req.end_time:
            filters.append(LogParseResult.timestamp <= parse_timestamp(req.end_time))
        if req.src_ip:
            filters.append(func.host(LogParseResult.src_ip).like(f"%{req.src_ip}%"))
        if req.dst_ip:
            filters.append(func.host(LogParseResult.dst_ip).like(f"%{req.dst_ip}%"))
        if req.cluster_name:
            filters.append(LogParseResult.cluster_name == req.cluster_name)
        if req.host:
            filters.append(LogParseResult.host == req.host)
        if req.pod_ip:
            filters.append(LogParseResult.pod_ips.contains([req.pod_ip]))
        if req.operation:
            filters.append(LogParseResult.operation.ilike(f"%{req.operation}%"))

        stmt = (
            select(
                bucket_epoch,
                LogParseResult.src_ip,
                LogParseResult.dst_ip,
                func.count().label("metric_weight"),
                *[
                    func.avg(column).label(f"ave_{name}")
                    for name, column in _YUANRONG_BREAKDOWN_FIELDS
                ],
            )
            .where(*filters)
            .group_by(bucket_epoch, LogParseResult.src_ip, LogParseResult.dst_ip)
        )
        async with PGManager.session() as session:
            rows = (await session.execute(stmt)).all()

        events_by_epoch = {
            int(
                datetime.strptime(event["start_time"], "%Y-%m-%d %H:%M:%S")
                .replace(tzinfo=timezone.utc)
                .timestamp()
            ): event
            for event in events
        }
        parent_values: dict[int, dict[str, list[tuple[float, int]]]] = {}
        for row in rows:
            epoch = int(row.bucket_epoch)
            event = events_by_epoch.get(epoch)
            if event is None:
                continue
            src_ip = TimeWindowAggregatedEventPGManager._format_ip(row.src_ip)
            dst_ip = TimeWindowAggregatedEventPGManager._format_ip(row.dst_ip)
            pair = next(
                (
                    item
                    for item in event["ip_pairs"]
                    if item["src_ip"] == src_ip and item["dst_ip"] == dst_ip
                ),
                None,
            )
            weight = int(row.metric_weight or 0)
            epoch_values = parent_values.setdefault(epoch, {})
            for name, _ in _YUANRONG_BREAKDOWN_FIELDS:
                value = getattr(row, f"ave_{name}")
                if pair is not None:
                    pair[f"ave_{name}"] = value
                if value is not None and weight > 0:
                    epoch_values.setdefault(name, []).append((float(value), weight))

        for epoch, metrics in parent_values.items():
            event = events_by_epoch[epoch]
            for name, weighted_values in metrics.items():
                total_weight = sum(weight for _, weight in weighted_values)
                event[f"ave_{name}"] = (
                    sum(value * weight for value, weight in weighted_values) / total_weight
                    if total_weight
                    else None
                )

    @staticmethod
    async def list_time_window_events(
        req: ListTimeWindowAggregatedEventRequest,
    ) -> tuple[int, list[dict[str, Any]]]:
        """Read 10s materialized rows and aggregate to the requested granularity.

        ``time_window_aggregated`` stores one row per 10s wall-clock bucket per
        (src_ip, dst_ip) with cnt / anomaly / ave_total_latency / p99_total_latency.
        Coarser intervals (60/600/3600s) are bucketed in SQL via
        ``floor(EXTRACT(EPOCH FROM time_bucket) / interval) * interval``:
        cnt/anomaly summed, total latency summed as
        ``COALESCE(latency_sum, ave_total_latency*cnt)`` (old rows without a
        materialized latency_sum fall back to ave*cnt), and p99 re-aggregated as
        p99-of-p99s (``percentile_cont(0.99)`` over each inner 10s row's
        materialized p99 — an approximation, not statistically exact).  For
        interval=10s each group is a single row, so p99 passes through the
        materialized value unchanged.  No real-time aggregation over
        log_parse_result is performed.
        """
        interval = TimeWindowAggregatedEventPGManager._normalize_interval(
            req.interval
        )

        filters = [TimeWindowAggregated.existed_status.is_(True)]
        if req.kb_id:
            filters.append(TimeWindowAggregated.kb_id == req.kb_id)
        if req.start_time:
            filters.append(
                TimeWindowAggregated.time_bucket >= parse_timestamp(req.start_time)
            )
        if req.end_time:
            filters.append(
                TimeWindowAggregated.time_bucket <= parse_timestamp(req.end_time)
            )
        if req.src_ip:
            filters.append(func.host(TimeWindowAggregated.src_ip).like(f"%{req.src_ip}%"))
        if req.dst_ip:
            filters.append(func.host(TimeWindowAggregated.dst_ip).like(f"%{req.dst_ip}%"))

        bucket_epoch = (
            func.floor(
                func.extract("epoch", TimeWindowAggregated.time_bucket) / interval
            ).cast(Integer)
            * interval
        ).label("bucket_epoch")

        stmt = (
            select(
                bucket_epoch,
                TimeWindowAggregated.src_ip,
                TimeWindowAggregated.dst_ip,
                func.sum(TimeWindowAggregated.log_parse_result_cnt).label("total_cnt"),
                func.sum(TimeWindowAggregated.anomaly_cnt).label("anomaly_cnt"),
                (
                    func.sum(
                        func.coalesce(
                            TimeWindowAggregated.latency_sum,
                            TimeWindowAggregated.ave_total_latency
                            * TimeWindowAggregated.log_parse_result_cnt,
                        )
                    )
                    / func.nullif(
                        func.sum(TimeWindowAggregated.log_parse_result_cnt), 0
                    )
                ).label("ave"),
                func.min(TimeWindowAggregated.min_total_latency).label("min_lat"),
                func.max(TimeWindowAggregated.max_total_latency).label("max_lat"),
                func.percentile_cont(0.95).within_group(
                    TimeWindowAggregated.p95_total_latency.asc()
                ).label("p95"),
                func.percentile_cont(0.99).within_group(
                    TimeWindowAggregated.p99_total_latency.asc()
                ).label("p99"),
            )
            .where(*filters)
            .group_by(
                bucket_epoch,
                TimeWindowAggregated.src_ip,
                TimeWindowAggregated.dst_ip,
            )
            .order_by(bucket_epoch)
        )

        async with PGManager.session() as session:
            rows = (await session.execute(stmt)).all()

        total, events = TimeWindowAggregatedEventPGManager._rows_to_events(
            rows, interval, req
        )
        await TimeWindowAggregatedEventPGManager._attach_yuanrong_breakdown(
            events, req, interval
        )
        return total, events
