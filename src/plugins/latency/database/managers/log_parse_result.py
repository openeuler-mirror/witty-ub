# Copyright (c) Huawei Technologies Co., Ltd. 2023-2025. All rights reserved.
"""PostgreSQL-specific manager for log_parse_result.

This manager focuses on high-performance COPY ingestion and on-the-fly
aggregation via window functions / ordered-set aggregates.
"""
from __future__ import annotations

import logging
import time
from typing import Any

from sqlalchemy import Integer, func, select, text

from latency.database.engine import PGManager
from latency.database.models import LogFile, LogParseResult
from latency.database.utils import (
    COPY_COLUMNS,
    format_ip,
    format_timestamp,
    parse_timestamp,
    result_to_pg_tuple,
)
from latency.schemas.log import LogParseResultModel, LogParseResultStorage, YUANRONG_METRIC_FIELDS
from latency.schemas.request import (
    GetLatencyMetricsRequest,
    ListLogParseResultRequest,
    ListTracesByHostRequest,
)

logger = logging.getLogger(__name__)

# All latency/metric fields that can be aggregated.
_AGGREGATABLE_FIELDS = [
    "total_latency",
    "worker_query_meta_latency",
    "urma_total_latency",
    "urma_link_latency",
    "c2w_urma_latency",
    "w2w_urma_latency",
    "sdk_process",
    "sdk_rpc",
    "local_worker_cost",
    "local_worker_lock",
    "remote_worker_cost",
    "remote_worker_rpc",
    "master_process",
    "master_rpc_total",
    *(name for name in YUANRONG_METRIC_FIELDS if name != "request_mode"),
]


class LogParseResultPGManager:
    last_store_metrics: dict[str, Any] = {}

    @staticmethod
    async def add_log_parse_results(
        results: list[LogParseResultStorage],
        batch_size: int = 100_000,
    ) -> bool:
        """Bulk insert log_parse_result rows using asyncpg COPY."""
        LogParseResultPGManager.last_store_metrics = {}
        if not results:
            return True

        total_count = len(results)
        t_start = time.perf_counter()
        metrics = {
            "rows": total_count,
            "batch_size": batch_size,
            "batch_count": (total_count + batch_size - 1) // batch_size,
            "copy_seconds": 0.0,
            "total_seconds": 0.0,
            "success": False,
        }

        try:
            t_copy = time.perf_counter()
            async with PGManager.connection() as conn:
                raw_conn = await conn.get_raw_connection()
                asyncpg_conn = raw_conn.driver_connection

                for i in range(0, total_count, batch_size):
                    batch = [
                        result_to_pg_tuple(r) for r in results[i : i + batch_size]
                    ]
                    await asyncpg_conn.copy_records_to_table(
                        "log_parse_result",
                        records=batch,
                        columns=COPY_COLUMNS,
                    )

            metrics["copy_seconds"] = time.perf_counter() - t_copy
            metrics["success"] = True
            logger.info(
                "[Store][PG] COPY %s rows done in %.3fs",
                total_count,
                metrics["copy_seconds"],
            )
        except Exception as e:
            logger.error("[Store][PG] COPY failed: %s", e)
            metrics["error"] = str(e)
            return False
        finally:
            metrics["total_seconds"] = time.perf_counter() - t_start
            LogParseResultPGManager.last_store_metrics = metrics

        return True

    @staticmethod
    async def delete_by_log_id(log_id: str) -> bool:
        """Soft delete all log_parse_result rows for a log_id."""
        async with PGManager.session() as session:
            await session.execute(
                text(
                    "UPDATE log_parse_result SET existed_status = FALSE WHERE log_id = :log_id"
                ),
                {"log_id": log_id},
            )
        return True

    @staticmethod
    async def update_log_parse_results_existed_status_by_log_id(
        log_id: str, existed_status: int
    ) -> bool:
        async with PGManager.session() as session:
            await session.execute(
                text(
                    "UPDATE log_parse_result SET existed_status = :existed_status "
                    "WHERE log_id = :log_id"
                ),
                {"log_id": log_id, "existed_status": bool(existed_status)},
            )
        return True

    @staticmethod
    async def list_anomalous_trace_ids_by_log_id(log_id: str) -> set[str]:
        """Return distinct anomalous trace_ids for a log_id."""
        stmt = (
            select(LogParseResult.trace_id)
            .where(LogParseResult.log_id == log_id)
            .where(LogParseResult.existed_status.is_(True))
            .where(LogParseResult.is_anomalous.is_(True))
            .where(LogParseResult.trace_id.is_not(None))
            .where(LogParseResult.trace_id != "")
            .distinct()
        )
        async with PGManager.session() as session:
            rows = await session.execute(stmt)
            return {row[0].strip() for row in rows.all() if row[0].strip()}

    @staticmethod
    def _build_stats_select_exprs(field_names: list[str]) -> list[Any]:
        """Build SELECT expressions for COUNT/AVG/MIN/MAX/P95/P99/P9999."""
        exprs: list[Any] = [func.count().label("cnt")]
        for field in field_names:
            col = getattr(LogParseResult, field)
            exprs.extend(
                [
                    func.avg(col).label(f"ave_{field}"),
                    func.min(col).label(f"min_{field}"),
                    func.max(col).label(f"max_{field}"),
                    func.percentile_cont(0.95)
                    .within_group(col.asc())
                    .label(f"p95_{field}"),
                    func.percentile_cont(0.99)
                    .within_group(col.asc())
                    .label(f"p99_{field}"),
                    func.percentile_cont(0.9999)
                    .within_group(col.asc())
                    .label(f"p9999_{field}"),
                ]
            )
        return exprs

    @staticmethod
    async def get_src_dst_aggregates(
        log_id: str,
        field_names: list[str] | None = None,
    ) -> list[dict[str, Any]]:
        """Real-time aggregate by (log_id, src_ip, dst_ip)."""
        fields = field_names or _AGGREGATABLE_FIELDS[:6]
        select_exprs = [
            LogParseResult.log_id,
            LogParseResult.src_ip,
            LogParseResult.dst_ip,
            func.sum(func.cast(LogParseResult.is_anomalous, Integer)).label(
                "anomaly_cnt"
            ),
        ]
        select_exprs.extend(LogParseResultPGManager._build_stats_select_exprs(fields))

        stmt = (
            select(*select_exprs)
            .where(LogParseResult.log_id == log_id)
            .where(LogParseResult.existed_status.is_(True))
            .group_by(LogParseResult.log_id, LogParseResult.src_ip, LogParseResult.dst_ip)
        )

        async with PGManager.session() as session:
            rows = (await session.execute(stmt)).all()
            return [dict(r._mapping) for r in rows]

    @staticmethod
    async def get_time_window_aggregates(
        log_id: str,
        start_time: str | None = None,
        end_time: str | None = None,
        field_names: list[str] | None = None,
    ) -> list[dict[str, Any]]:
        """Real-time aggregate by time bucket (per-second)."""
        from latency.database.utils import parse_timestamp

        fields = field_names or _AGGREGATABLE_FIELDS
        time_bucket = func.date_trunc("second", LogParseResult.timestamp).label(
            "time_bucket"
        )
        select_exprs = [
            LogParseResult.log_id,
            LogParseResult.src_ip,
            LogParseResult.dst_ip,
            time_bucket,
            func.sum(func.cast(LogParseResult.is_anomalous, Integer)).label(
                "anomaly_cnt"
            ),
        ]
        select_exprs.extend(LogParseResultPGManager._build_stats_select_exprs(fields))

        stmt = (
            select(*select_exprs)
            .where(LogParseResult.log_id == log_id)
            .where(LogParseResult.existed_status.is_(True))
        )
        if start_time:
            stmt = stmt.where(LogParseResult.timestamp >= parse_timestamp(start_time))
        if end_time:
            stmt = stmt.where(LogParseResult.timestamp <= parse_timestamp(end_time))

        stmt = stmt.group_by(
            LogParseResult.log_id,
            LogParseResult.src_ip,
            LogParseResult.dst_ip,
            time_bucket,
        ).order_by(time_bucket)

        async with PGManager.session() as session:
            rows = (await session.execute(stmt)).all()
            return [dict(r._mapping) for r in rows]

    @staticmethod
    async def get_latency_metrics_curve(
        log_id: str,
        metric: str = "total_latency",
        sample_mode: str = "p99",
        start_time: str | None = None,
        end_time: str | None = None,
    ) -> list[dict[str, Any]]:
        """Latency curve from raw data, no pre-aggregated columns required."""
        from latency.database.utils import parse_timestamp

        pct_map = {
            "avg": lambda c: func.avg(c),
            "min": lambda c: func.min(c),
            "max": lambda c: func.max(c),
            "p95": lambda c: func.percentile_cont(0.95).within_group(c.asc()),
            "p99": lambda c: func.percentile_cont(0.99).within_group(c.asc()),
            "p9999": lambda c: func.percentile_cont(0.9999).within_group(c.asc()),
        }
        agg_fn = pct_map.get(sample_mode, pct_map["p99"])
        col = getattr(LogParseResult, metric)
        time_bucket = func.date_bin(
            text("INTERVAL '10 seconds'"),
            LogParseResult.timestamp,
            text("TIMESTAMP '1970-01-01'"),
        ).label("time")

        stmt = (
            select(
                time_bucket,
                func.count().label("cnt"),
                agg_fn(col).label(metric),
            )
            .where(LogParseResult.log_id == log_id)
            .where(LogParseResult.existed_status.is_(True))
        )
        if start_time:
            stmt = stmt.where(LogParseResult.timestamp >= parse_timestamp(start_time))
        if end_time:
            stmt = stmt.where(LogParseResult.timestamp <= parse_timestamp(end_time))

        stmt = stmt.group_by(time_bucket).order_by(time_bucket)

        async with PGManager.session() as session:
            rows = (await session.execute(stmt)).all()
            return [dict(r._mapping) for r in rows]

    # ------------------------------------------------------------------
    # Service-layer query methods (migrated from SQLite LogParseResultManager)
    # ------------------------------------------------------------------

    @staticmethod
    async def delete_log_parse_results_by_log_id(log_id: str) -> bool:
        """Hard delete all log_parse_result rows for a log_id."""
        async with PGManager.session() as session:
            await session.execute(
                text("DELETE FROM log_parse_result WHERE log_id = :log_id"),
                {"log_id": log_id},
            )
        return True

    @staticmethod
    async def list_log_parse_results(
        req: ListLogParseResultRequest,
    ) -> tuple[int, list[LogParseResultModel]]:
        """分页查询日志解析结果。"""
        stmt = select(LogParseResult).where(LogParseResult.existed_status.is_(True))

        if req.log_id:
            stmt = stmt.where(LogParseResult.log_id == req.log_id)
        if req.kb_id:
            stmt = stmt.join(LogFile, LogParseResult.log_id == LogFile.id).where(
                LogFile.kb_id == req.kb_id
            )
        if req.aggregated_event_id:
            stmt = stmt.where(LogParseResult.aggregated_event_id == req.aggregated_event_id)
        if req.trace_id:
            stmt = stmt.where(LogParseResult.trace_id == req.trace_id)
        if req.trace_ids:
            stmt = stmt.where(LogParseResult.trace_id.in_(req.trace_ids))
        if req.src_ip is not None:
            if req.src_ip == "":
                stmt = stmt.where(LogParseResult.src_ip.is_(None))
            else:
                stmt = stmt.where(
                    func.host(LogParseResult.src_ip).like(f"%{req.src_ip}%")
                )
        if req.dst_ip is not None:
            if req.dst_ip == "":
                stmt = stmt.where(LogParseResult.dst_ip.is_(None))
            else:
                stmt = stmt.where(
                    func.host(LogParseResult.dst_ip).like(f"%{req.dst_ip}%")
                )
        if req.pod_ip:
            stmt = stmt.where(LogParseResult.pod_ips.contains([req.pod_ip]))
        if req.host:
            stmt = stmt.where(LogParseResult.host.ilike(f"%{req.host}%"))
        if req.cluster_name:
            stmt = stmt.where(LogParseResult.cluster_name == req.cluster_name)
        if req.is_anomalous is not None:
            stmt = stmt.where(LogParseResult.is_anomalous.is_(req.is_anomalous))
        if req.start_time:
            stmt = stmt.where(LogParseResult.timestamp >= parse_timestamp(req.start_time))
        if req.end_time:
            stmt = stmt.where(LogParseResult.timestamp <= parse_timestamp(req.end_time))
        if req.created_at_start:
            stmt = stmt.where(LogParseResult.created_at >= parse_timestamp(req.created_at_start))
        if req.created_at_end:
            stmt = stmt.where(LogParseResult.created_at <= parse_timestamp(req.created_at_end))
        if req.operation:
            stmt = stmt.where(LogParseResult.operation.ilike(f"%{req.operation}%"))

        count_stmt = select(func.count()).select_from(stmt.subquery())
        async with PGManager.session() as session:
            total = (await session.execute(count_stmt)).scalar() or 0

        sort_field_mapping = {
            "total_latency": LogParseResult.total_latency,
            "timestamp": LogParseResult.timestamp,
            "trace_id": LogParseResult.trace_id,
            "pod_ips": LogParseResult.pod_ips,
            "cluster_name": LogParseResult.cluster_name,
            "host": LogParseResult.host,
            "query_meta_latency": LogParseResult.worker_query_meta_latency,
            "urma_total_latency": LogParseResult.urma_total_latency,
            "urma_link_latency": LogParseResult.urma_link_latency,
            "worker_query_meta_latency": LogParseResult.worker_query_meta_latency,
            "c2w_urma_latency": LogParseResult.c2w_urma_latency,
            "w2w_urma_latency": LogParseResult.w2w_urma_latency,
            "created_at": LogParseResult.created_at,
        }

        order_clauses = []
        if req.sort_fields:
            for sf in req.sort_fields:
                col = sort_field_mapping.get(sf.field)
                if col is not None:
                    order_clauses.append(col.desc() if sf.order == "desc" else col.asc())
        if not order_clauses:
            order_clauses.append(LogParseResult.total_latency.desc())

        stmt = stmt.order_by(*order_clauses)
        offset = (req.page_num - 1) * req.page_cnt
        stmt = stmt.offset(offset).limit(req.page_cnt)

        async with PGManager.session() as session:
            result = await session.execute(stmt)
            rows = result.scalars().all()

        results = []
        for row in rows:
            data = {
                "id": row.id,
                "log_id": row.log_id,
                "aggregated_event_id": row.aggregated_event_id,
                "anomalous_event_id": row.anomalous_event_id,
                "trace_id": row.trace_id,
                "timestamp": format_timestamp(row.timestamp),
                "src_ip": format_ip(row.src_ip),
                "dst_ip": format_ip(row.dst_ip),
                "pod_ips": row.pod_ips,
                "cluster_name": row.cluster_name,
                "host": row.host,
                "total_latency": row.total_latency,
                "c2w_latency": row.c2w_latency,
                "worker_query_meta_latency": row.worker_query_meta_latency,
                "urma_total_latency": row.urma_total_latency,
                "urma_link_latency": row.urma_link_latency,
                "urma_inflight_count": row.urma_inflight_count,
                "c2w_urma_latency": row.c2w_urma_latency,
                "w2w_urma_latency": row.w2w_urma_latency,
                "operation": row.operation,
                "data_size": row.data_size,
                "offset": row.offset,
                "is_anomalous": row.is_anomalous,
                "content": row.content,
                "anomaly_reason": row.anomaly_reason,
                "anomaly_score": row.anomaly_score,
                "remark": row.remark,
                "existed_status": row.existed_status,
                "created_at": format_timestamp(row.created_at),
                "sdk_process": row.sdk_process,
                "sdk_rpc": row.sdk_rpc,
                "local_worker_cost": row.local_worker_cost,
                "local_worker_lock": row.local_worker_lock,
                "remote_worker_cost": row.remote_worker_cost,
                "remote_worker_rpc": row.remote_worker_rpc,
                "master_process": row.master_process,
                "master_rpc_total": row.master_rpc_total,
                "create_latency": row.create_latency,
                "publish_latency": row.publish_latency,
                "worker_total_latency": row.worker_total_latency,
            }
            data.update({name: getattr(row, name) for name in YUANRONG_METRIC_FIELDS})
            results.append(LogParseResultModel(**data))
        return total, results

    @staticmethod
    async def get_log_parse_result_by_id(result_id: str) -> LogParseResultModel | None:
        # log_parse_result 使用 (id, log_id) 复合主键以支持 HASH 分区，
        # 因此不能直接用 session.get() 按单主键查询。
        stmt = (
            select(LogParseResult)
            .where(LogParseResult.id == result_id)
            .where(LogParseResult.existed_status.is_(True))
            .limit(1)
        )
        async with PGManager.session() as session:
            row = (await session.execute(stmt)).scalar_one_or_none()
        if row is None:
            return None
        data = {
            "id": row.id,
            "log_id": row.log_id,
            "aggregated_event_id": row.aggregated_event_id,
            "anomalous_event_id": row.anomalous_event_id,
            "trace_id": row.trace_id,
            "timestamp": format_timestamp(row.timestamp),
            "src_ip": format_ip(row.src_ip),
            "dst_ip": format_ip(row.dst_ip),
            "pod_ips": row.pod_ips,
            "cluster_name": row.cluster_name,
            "host": row.host,
            "total_latency": row.total_latency,
            "c2w_latency": row.c2w_latency,
            "worker_query_meta_latency": row.worker_query_meta_latency,
            "urma_total_latency": row.urma_total_latency,
            "urma_link_latency": row.urma_link_latency,
            "urma_inflight_count": row.urma_inflight_count,
            "c2w_urma_latency": row.c2w_urma_latency,
            "w2w_urma_latency": row.w2w_urma_latency,
            "operation": row.operation,
            "data_size": row.data_size,
            "offset": row.offset,
            "is_anomalous": row.is_anomalous,
            "content": row.content,
            "anomaly_reason": row.anomaly_reason,
            "anomaly_score": row.anomaly_score,
            "remark": row.remark,
            "existed_status": row.existed_status,
            "created_at": format_timestamp(row.created_at),
            "sdk_process": row.sdk_process,
            "sdk_rpc": row.sdk_rpc,
            "local_worker_cost": row.local_worker_cost,
            "local_worker_lock": row.local_worker_lock,
            "remote_worker_cost": row.remote_worker_cost,
            "remote_worker_rpc": row.remote_worker_rpc,
            "master_process": row.master_process,
            "master_rpc_total": row.master_rpc_total,
            "create_latency": row.create_latency,
            "publish_latency": row.publish_latency,
            "worker_total_latency": row.worker_total_latency,
        }
        data.update({name: getattr(row, name) for name in YUANRONG_METRIC_FIELDS})
        return LogParseResultModel(**data)

    @staticmethod
    async def list_traces_by_host(
        req: ListTracesByHostRequest,
    ) -> tuple[int, list[dict[str, Any]]]:
        pod_ips_str = func.array_to_string(LogParseResult.pod_ips, ",").label("pod_ips_str")
        stmt = (
            select(
                LogParseResult.id,
                LogParseResult.trace_id,
                LogParseResult.pod_ips,
                LogParseResult.cluster_name,
                LogParseResult.host,
                LogParseResult.timestamp.label("time"),
                LogParseResult.operation,
                LogParseResult.total_latency,
                LogParseResult.urma_total_latency,
                LogParseResult.c2w_latency,
                LogParseResult.worker_query_meta_latency,
                LogParseResult.w2w_urma_latency,
                LogParseResult.is_anomalous,
                LogParseResult.anomaly_reason,
                func.coalesce(LogParseResult.c2w_latency, 0).label("req_delay_ms"),
                (LogParseResult.total_latency - func.coalesce(LogParseResult.c2w_latency, 0)).label(
                    "rsp_delay_ms"
                ),
                LogParseResult.total_latency.label("sdk_ms"),
                LogParseResult.pod_ips.label("pod_id"),
            )
            .where(LogParseResult.existed_status.is_(True))
            .where(pod_ips_str.like(f"%{req.host}%"))
        )

        if req.kb_id:
            stmt = stmt.join(LogFile, LogParseResult.log_id == LogFile.id).where(
                LogFile.kb_id == req.kb_id
            )
        if req.start_time:
            stmt = stmt.where(LogParseResult.timestamp >= parse_timestamp(req.start_time))
        if req.end_time:
            stmt = stmt.where(LogParseResult.timestamp <= parse_timestamp(req.end_time))
        if req.operation:
            stmt = stmt.where(LogParseResult.operation.ilike(f"%{req.operation}%"))
        if req.is_anomalous is not None:
            stmt = stmt.where(LogParseResult.is_anomalous.is_(req.is_anomalous))

        count_stmt = select(func.count()).select_from(stmt.subquery())
        async with PGManager.session() as session:
            total = (await session.execute(count_stmt)).scalar() or 0

        valid_sort_fields = {
            "timestamp": LogParseResult.timestamp,
            "total_latency": LogParseResult.total_latency,
            "c2w_latency": LogParseResult.c2w_latency,
        }
        sort_col = valid_sort_fields.get(req.sort_by, LogParseResult.timestamp)
        stmt = stmt.order_by(sort_col.desc() if req.sort_order.lower() == "desc" else sort_col.asc())

        offset = (req.page_num - 1) * req.page_cnt
        stmt = stmt.offset(offset).limit(req.page_cnt)

        async with PGManager.session() as session:
            result = await session.execute(stmt)
            rows = result.mappings().all()

        def _format_trace(row):
            data = dict(row)
            pod_id = data.get("pod_id")
            if isinstance(pod_id, list):
                data["pod_id"] = ",".join(pod_id)
            else:
                data["pod_id"] = str(pod_id) if pod_id is not None else ""
            data["time"] = format_timestamp(data.get("time"))
            return data

        return total, [_format_trace(r) for r in rows]

    @staticmethod
    async def get_latency_metrics(
        req: GetLatencyMetricsRequest,
    ) -> tuple[int, list[dict[str, Any]]]:
        """从 log_parse_result 实时计算延迟指标时间曲线。

        按 (time_bucket, src_ip, dst_ip) 分组，与 master 分支
        time_window_aggregated_table 的维度保持一致。
        """
        time_bucket = func.date_trunc("second", LogParseResult.timestamp).label("time")

        pct_map = {
            "avg": lambda c: func.avg(c),
            "min": lambda c: func.min(c),
            "max": lambda c: func.max(c),
            "p95": lambda c: func.percentile_cont(0.95).within_group(c.asc()),
            "p99": lambda c: func.percentile_cont(0.99).within_group(c.asc()),
            "p9999": lambda c: func.percentile_cont(0.9999).within_group(c.asc()),
            "none": lambda c: func.percentile_cont(0.99).within_group(c.asc()),
        }
        agg_fn = pct_map.get(req.sample_mode.value, pct_map["p99"])

        metric_cols = [
            "total_latency",
            "urma_total_latency",
            "worker_query_meta_latency",
            "sdk_process",
            "sdk_rpc",
            "local_worker_cost",
            "local_worker_lock",
            "remote_worker_cost",
            "remote_worker_rpc",
            "master_process",
            "master_rpc_total",
            "create_latency",
            "publish_latency",
            "worker_total_latency",
            *(name for name in YUANRONG_METRIC_FIELDS if name != "request_mode"),
        ]
        select_exprs = [time_bucket]
        for name in metric_cols:
            column = getattr(LogParseResult, name)
            select_exprs.append(agg_fn(column).filter(column > 0).label(name))

        stmt = select(*select_exprs).where(LogParseResult.existed_status.is_(True))

        if req.kb_id:
            stmt = stmt.join(LogFile, LogParseResult.log_id == LogFile.id).where(
                LogFile.kb_id == req.kb_id
            )
        if req.cluster_name:
            stmt = stmt.where(LogParseResult.cluster_name == req.cluster_name)
        if req.host:
            stmt = stmt.where(LogParseResult.host.ilike(f"%{req.host}%"))
        if req.pod_ip:
            stmt = stmt.where(LogParseResult.pod_ips.contains([req.pod_ip]))
        if req.src_ip is not None:
            if req.src_ip == "":
                stmt = stmt.where(LogParseResult.src_ip.is_(None))
            else:
                stmt = stmt.where(
                    func.host(LogParseResult.src_ip).like(f"%{req.src_ip}%")
                )
        if req.dst_ip is not None:
            if req.dst_ip == "":
                stmt = stmt.where(LogParseResult.dst_ip.is_(None))
            else:
                stmt = stmt.where(
                    func.host(LogParseResult.dst_ip).like(f"%{req.dst_ip}%")
                )
        if req.start_time:
            stmt = stmt.where(LogParseResult.timestamp >= parse_timestamp(req.start_time))
        if req.end_time:
            stmt = stmt.where(LogParseResult.timestamp <= parse_timestamp(req.end_time))
        if req.operation:
            stmt = stmt.where(LogParseResult.operation.ilike(f"%{req.operation}%"))

        stmt = stmt.group_by(time_bucket).order_by(time_bucket)

        async with PGManager.session() as session:
            result = await session.execute(stmt)
            rows = result.mappings().all()

        formatted = []
        for r in rows:
            d = dict(r)
            if "time" in d and d["time"] is not None:
                d["time"] = format_timestamp(d["time"])
            formatted.append(d)
        return len(formatted), formatted

    @staticmethod
    async def get_cluster_list(kb_id: str | None = None) -> list[str]:
        stmt = (
            select(LogParseResult.cluster_name)
            .where(LogParseResult.existed_status.is_(True))
            .where(LogParseResult.cluster_name.is_not(None))
            .where(LogParseResult.cluster_name != "")
        )
        if kb_id:
            stmt = stmt.join(LogFile, LogParseResult.log_id == LogFile.id).where(
                LogFile.kb_id == kb_id
            )
        stmt = stmt.distinct().order_by(LogParseResult.cluster_name)
        async with PGManager.session() as session:
            result = await session.execute(stmt)
            rows = result.scalars().all()
        return [r for r in rows if r]

    @staticmethod
    async def get_host_list(kb_id: str | None = None) -> list[str]:
        stmt = (
            select(LogParseResult.host)
            .where(LogParseResult.existed_status.is_(True))
            .where(LogParseResult.host.is_not(None))
            .where(LogParseResult.host != "")
        )
        if kb_id:
            stmt = stmt.join(LogFile, LogParseResult.log_id == LogFile.id).where(
                LogFile.kb_id == kb_id
            )
        stmt = stmt.distinct().order_by(LogParseResult.host)
        async with PGManager.session() as session:
            result = await session.execute(stmt)
            rows = result.scalars().all()
        return [r for r in rows if r]

    @staticmethod
    async def list_anomalous_trace_ids_by_log_id(log_id: str) -> set[str]:
        """查询指定日志中所有异常解析结果的 trace_id。"""
        stmt = (
            select(LogParseResult.trace_id)
            .where(LogParseResult.log_id == log_id)
            .where(LogParseResult.existed_status.is_(True))
            .where(LogParseResult.is_anomalous.is_(True))
            .where(LogParseResult.trace_id.is_not(None))
            .where(LogParseResult.trace_id != "")
            .distinct()
        )
        async with PGManager.session() as session:
            result = await session.execute(stmt)
            rows = result.scalars().all()
        return {row.strip() for row in rows if row and row.strip()}
