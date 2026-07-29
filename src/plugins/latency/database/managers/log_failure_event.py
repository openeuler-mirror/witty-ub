# Copyright (c) Huawei Technologies Co., Ltd. 2023-2025. All rights reserved.
"""PostgreSQL manager for log_failure_event / trace_failure_event.

This manager replicates the public API of ``LogFailureEventManager`` (SQLite)
using the PostgreSQL ORM models.  Aggregation queries are executed against the
raw ``trace_failure_event`` table because the PostgreSQL schema intentionally
keeps only raw failure events.
"""
from __future__ import annotations

import logging
import time
import uuid
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Any

from sqlalchemy import func, select, text
from sqlalchemy.dialects.postgresql import array

from latency.database.engine import PGManager
from latency.database.models import LogFailureEvent, LogFile, TraceFailureEvent
from latency.database.utils import format_ip, format_timestamp, parse_ip, parse_timestamp
from latency.schemas.log_failure_event import (
    LogFailureEventModel,
    TraceFailureEventModel,
)
from latency.schemas.request import (
    GetErrCodeMetricsRequest,
    ListLogFailureEventResultRequest,
    ListPodAggregatedFailureEventRequest,
    ListSrcDstAggregatedFailureEventRequest,
    ListTimeAggregatedFailureEventRequest,
    ListTraceFailureEventResultRequest,
)


logger = logging.getLogger(__name__)


class LogFailureEventPGManager:
    """PostgreSQL-backed failure event manager."""

    _COPY_THRESHOLD = 1_000
    _COPY_BATCH_SIZE = 50_000

    _LOG_FAILURE_COPY_COLUMNS = [
        "id",
        "log_id",
        "log_file",
        "raw_text",
        "host_name",
        "timestamp",
        "level",
        "filename",
        "pod_name",
        "pid",
        "tid",
        "trace_id",
        "cluster_name",
        "message",
        "status_code",
        "failure_mode",
    ]

    _TRACE_FAILURE_COPY_COLUMNS = [
        "id",
        "log_id",
        "trace_id",
        "pod_names",
        "src_ip",
        "dst_ip",
        "host_names",
        "cluster_names",
        "timestamp",
        "status_code",
        "failure_mode",
    ]

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    @staticmethod
    def _ip_eq(column, value: str | None):
        if value is None:
            return None
        if value == "":
            return column.is_(None)
        return func.host(column) == value

    @staticmethod
    def _array_overlap(column, values: list[str] | None):
        if not values:
            return None
        # Remove empty values to avoid matching against ''
        clean = [v for v in values if v]
        if not clean:
            return None
        return column.overlap(array(clean))

    @staticmethod
    def _log_ids_for_kb(kb_id: str | None) -> list[str] | None:
        """Return log ids for a kb_id.

        ``None`` means "no kb filter" (all logs).  An empty list means the kb
        has no logs and the caller should short-circuit to an empty result.
        """
        if not kb_id:
            return None
        # This synchronous helper is used by the aggregation methods below.
        # Callers that already run inside an async context should await the
        # inline query directly.
        return None  # placeholder; actual queries are async and inline.

    # ------------------------------------------------------------------
    # Write operations
    # ------------------------------------------------------------------
    @staticmethod
    async def add_log_failure_event(
        results: list[LogFailureEventModel],
    ) -> list[str]:
        ids_added: list[str] = []
        if not results:
            return ids_added

        batch_size = 1024
        for i in range(0, len(results), batch_size):
            batch = results[i : i + batch_size]
            objs = []
            for event in batch:
                data = event.model_dump(exclude_none=False, by_alias=True)
                failure_mode = data.get("failure_mode") or []
                failure_mode_str = ",".join(failure_mode) if isinstance(failure_mode, list) else (failure_mode or "")
                host_name = data.get("host_name")
                if not host_name:
                    host_name = "Unknown"
                objs.append(
                    LogFailureEvent(
                        id=data.get("id") or str(uuid.uuid4()),
                        log_id=data["log_id"],
                        log_file=data.get("log_file") or "",
                        raw_text=data.get("raw_text") or "",
                        host_name=host_name,
                        timestamp=parse_timestamp(data["timestamp"]),
                        level=data.get("level") or "",
                        filename=data.get("filename") or "",
                        pod_name=data.get("pod_name") or "",
                        pid=data.get("pid") or "",
                        tid=data.get("tid") or "",
                        trace_id=data.get("trace_id") or "",
                        cluster_name=data.get("cluster_name") or "",
                        message=data.get("message") or "",
                        status_code=data.get("status_code") or "",
                        failure_mode=failure_mode_str,
                    )
                )
            async with PGManager.session() as session:
                session.add_all(objs)
            ids_added.extend([o.id for o in objs])
        return ids_added

    @staticmethod
    def _log_failure_event_dict_to_tuple(event: dict) -> tuple[Any, ...]:
        param = dict(event)
        param.setdefault("id", str(uuid.uuid4()))
        failure_mode = param.get("failure_mode", [])
        if isinstance(failure_mode, list):
            param["failure_mode"] = ",".join(failure_mode)
        elif failure_mode is None:
            param["failure_mode"] = ""
        param.setdefault("host_name", "Unknown")
        param.setdefault("log_file", "")
        param.setdefault("raw_text", "")
        param.setdefault("level", "")
        param.setdefault("filename", "")
        param.setdefault("pod_name", "")
        param.setdefault("pid", "")
        param.setdefault("tid", "")
        param.setdefault("trace_id", "")
        param.setdefault("cluster_name", "")
        param.setdefault("message", "")
        param.setdefault("status_code", "")
        return (
            param["id"],
            param["log_id"],
            param["log_file"],
            param["raw_text"],
            param["host_name"],
            parse_timestamp(param.get("timestamp")),
            param["level"],
            param["filename"],
            param["pod_name"],
            param["pid"],
            param["tid"],
            param["trace_id"],
            param["cluster_name"],
            param["message"],
            param["status_code"],
            param["failure_mode"],
        )

    @staticmethod
    async def add_log_failure_event_raw(results: list[dict]) -> list[str]:
        ids_added: list[str] = []
        if not results:
            return ids_added

        if len(results) >= LogFailureEventPGManager._COPY_THRESHOLD:
            return await LogFailureEventPGManager._copy_log_failure_events(results)

        objs = []
        for event in results:
            param = dict(event)
            param.setdefault("id", str(uuid.uuid4()))
            failure_mode = param.get("failure_mode", [])
            if isinstance(failure_mode, list):
                param["failure_mode"] = ",".join(failure_mode)
            elif failure_mode is None:
                param["failure_mode"] = ""
            param.setdefault("host_name", "Unknown")
            param.setdefault("log_file", "")
            param.setdefault("raw_text", "")
            param.setdefault("level", "")
            param.setdefault("filename", "")
            param.setdefault("pod_name", "")
            param.setdefault("pid", "")
            param.setdefault("tid", "")
            param.setdefault("trace_id", "")
            param.setdefault("cluster_name", "")
            param.setdefault("message", "")
            param.setdefault("status_code", "")
            objs.append(
                LogFailureEvent(
                    id=param["id"],
                    log_id=param["log_id"],
                    log_file=param["log_file"],
                    raw_text=param["raw_text"],
                    host_name=param["host_name"],
                    timestamp=parse_timestamp(param.get("timestamp")),
                    level=param["level"],
                    filename=param["filename"],
                    pod_name=param["pod_name"],
                    pid=param["pid"],
                    tid=param["tid"],
                    trace_id=param["trace_id"],
                    cluster_name=param["cluster_name"],
                    message=param["message"],
                    status_code=param["status_code"],
                    failure_mode=param["failure_mode"],
                )
            )
        async with PGManager.session() as session:
            session.add_all(objs)
        ids_added.extend([o.id for o in objs])
        return ids_added

    @staticmethod
    async def _copy_log_failure_events(results: list[dict]) -> list[str]:
        t_start = time.perf_counter()
        records = [
            LogFailureEventPGManager._log_failure_event_dict_to_tuple(r)
            for r in results
        ]
        ids_added = [r[0] for r in records]
        async with PGManager.connection() as conn:
            raw_conn = await conn.get_raw_connection()
            asyncpg_conn = raw_conn.driver_connection
            columns = LogFailureEventPGManager._LOG_FAILURE_COPY_COLUMNS
            for i in range(0, len(records), LogFailureEventPGManager._COPY_BATCH_SIZE):
                batch = records[i : i + LogFailureEventPGManager._COPY_BATCH_SIZE]
                await asyncpg_conn.copy_records_to_table(
                    "log_failure_event",
                    records=batch,
                    columns=columns,
                )
        logger.info(
            "[Store][PG] COPY %s log_failure_event rows done in %.3fs",
            len(results),
            time.perf_counter() - t_start,
        )
        return ids_added

    @staticmethod
    async def add_log_failure_event_if_not_exist(
        results: list[LogFailureEventModel],
    ) -> list[str]:
        ids_added: list[str] = []
        if not results:
            return ids_added

        from latency.database.engine import PGManager as _pg
        from sqlalchemy.dialects.postgresql import insert

        batch_size = 1024
        for i in range(0, len(results), batch_size):
            batch = results[i : i + batch_size]
            values = []
            for event in batch:
                data = event.model_dump(exclude_none=False, by_alias=True)
                failure_mode = data.get("failure_mode") or []
                failure_mode_str = ",".join(failure_mode) if isinstance(failure_mode, list) else (failure_mode or "")
                host_name = data.get("host_name") or "Unknown"
                values.append(
                    {
                        "id": data.get("id") or str(uuid.uuid4()),
                        "log_id": data["log_id"],
                        "log_file": data.get("log_file") or "",
                        "raw_text": data.get("raw_text") or "",
                        "host_name": host_name,
                        "timestamp": parse_timestamp(data["timestamp"]),
                        "level": data.get("level") or "",
                        "filename": data.get("filename") or "",
                        "pod_name": data.get("pod_name") or "",
                        "pid": data.get("pid") or "",
                        "tid": data.get("tid") or "",
                        "trace_id": data.get("trace_id") or "",
                        "cluster_name": data.get("cluster_name") or "",
                        "message": data.get("message") or "",
                        "status_code": data.get("status_code") or "",
                        "failure_mode": failure_mode_str,
                    }
                )
            async with _pg.session() as session:
                stmt = insert(LogFailureEvent).values(values).on_conflict_do_nothing(
                    index_elements=["id"]
                )
                await session.execute(stmt)
            ids_added.extend([v["id"] for v in values])
        return ids_added

    @staticmethod
    async def update_failure_mode_by_raw_log(
        log_id: str, raw_text: str, failure_mode: str
    ) -> bool:
        async with PGManager.session() as session:
            result = await session.execute(
                text(
                    "UPDATE log_failure_event SET failure_mode = :failure_mode "
                    "WHERE log_id = :log_id AND raw_text = :raw_text"
                ),
                {"log_id": log_id, "raw_text": raw_text, "failure_mode": failure_mode},
            )
        return result.rowcount > 0

    @staticmethod
    async def delete_unclassified_log_events_by_log_id(log_id: str) -> bool:
        async with PGManager.session() as session:
            await session.execute(
                text(
                    "DELETE FROM log_failure_event "
                    "WHERE log_id = :log_id AND (failure_mode IS NULL OR failure_mode = '')"
                ),
                {"log_id": log_id},
            )
        return True

    @staticmethod
    async def delete_log_failure_events_by_log_id(log_id: str) -> bool:
        """删除指定日志文件的所有故障事件"""
        async with PGManager.session() as session:
            await session.execute(
                text("DELETE FROM log_failure_event WHERE log_id = :log_id"),
                {"log_id": log_id},
            )
        return True

    @staticmethod
    async def delete_trace_failure_events_by_log_id(log_id: str) -> bool:
        """删除指定日志文件的所有trace故障事件"""
        async with PGManager.session() as session:
            await session.execute(
                text("DELETE FROM trace_failure_event WHERE log_id = :log_id"),
                {"log_id": log_id},
            )
        return True

    @staticmethod
    async def add_trace_failure_event(
        results: list[TraceFailureEventModel],
    ) -> list[str]:
        ids_added: list[str] = []
        if not results:
            return ids_added

        batch_size = 1024
        for i in range(0, len(results), batch_size):
            batch = results[i : i + batch_size]
            objs = []
            for event in batch:
                objs.append(
                    TraceFailureEvent(
                        id=event.id or str(uuid.uuid4()),
                        log_id=event.log_id,
                        trace_id=event.trace_id,
                        pod_names=event.pod_names or [],
                        src_ip=event.src_ip or None,
                        dst_ip=event.dst_ip or None,
                        host_names=event.host_names or [],
                        cluster_names=event.cluster_names or [],
                        timestamp=parse_timestamp(event.timestamp),
                        status_code=event.status_code or "",
                        failure_mode=event.failure_mode or "",
                    )
                )
            async with PGManager.session() as session:
                session.add_all(objs)
            ids_added.extend([event.trace_id for event in batch])
        return ids_added

    @staticmethod
    def _trace_failure_event_dict_to_tuple(event: dict) -> tuple[Any, ...]:
        param = dict(event)
        param.setdefault("id", str(uuid.uuid4()))
        for key in ("pod_names", "host_names", "cluster_names"):
            value = param.get(key, [])
            if isinstance(value, str):
                param[key] = [v.strip() for v in value.split(",") if v.strip()]
            elif not isinstance(value, list):
                param[key] = []
        param.setdefault("src_ip", None)
        param.setdefault("dst_ip", None)
        param.setdefault("status_code", "")
        param.setdefault("failure_mode", "")
        return (
            param["id"],
            param["log_id"],
            param["trace_id"],
            param["pod_names"],
            parse_ip(param["src_ip"]),
            parse_ip(param["dst_ip"]),
            param["host_names"],
            param["cluster_names"],
            parse_timestamp(param.get("timestamp")),
            param["status_code"],
            param["failure_mode"],
        )

    @staticmethod
    async def add_trace_failure_event_raw(results: list[dict]) -> list[str]:
        ids_added: list[str] = []
        if not results:
            return ids_added

        if len(results) >= LogFailureEventPGManager._COPY_THRESHOLD:
            return await LogFailureEventPGManager._copy_trace_failure_events(results)

        objs = []
        for event in results:
            param = dict(event)
            param.setdefault("id", str(uuid.uuid4()))
            for key in ("pod_names", "host_names", "cluster_names"):
                value = param.get(key, [])
                if isinstance(value, str):
                    param[key] = [v.strip() for v in value.split(",") if v.strip()]
                elif not isinstance(value, list):
                    param[key] = []
            param.setdefault("src_ip", None)
            param.setdefault("dst_ip", None)
            param.setdefault("status_code", "")
            param.setdefault("failure_mode", "")
            objs.append(
                TraceFailureEvent(
                    id=param["id"],
                    log_id=param["log_id"],
                    trace_id=param["trace_id"],
                    pod_names=param["pod_names"],
                    src_ip=param["src_ip"] or None,
                    dst_ip=param["dst_ip"] or None,
                    host_names=param["host_names"],
                    cluster_names=param["cluster_names"],
                    timestamp=parse_timestamp(param.get("timestamp")),
                    status_code=param["status_code"],
                    failure_mode=param["failure_mode"],
                )
            )
        async with PGManager.session() as session:
            session.add_all(objs)
        ids_added.extend([o.trace_id for o in objs])
        return ids_added

    @staticmethod
    async def _copy_trace_failure_events(results: list[dict]) -> list[str]:
        t_start = time.perf_counter()
        records = [
            LogFailureEventPGManager._trace_failure_event_dict_to_tuple(r)
            for r in results
        ]
        ids_added = [r[2] for r in records]
        async with PGManager.connection() as conn:
            raw_conn = await conn.get_raw_connection()
            asyncpg_conn = raw_conn.driver_connection
            columns = LogFailureEventPGManager._TRACE_FAILURE_COPY_COLUMNS
            for i in range(0, len(records), LogFailureEventPGManager._COPY_BATCH_SIZE):
                batch = records[i : i + LogFailureEventPGManager._COPY_BATCH_SIZE]
                await asyncpg_conn.copy_records_to_table(
                    "trace_failure_event",
                    records=batch,
                    columns=columns,
                )
        logger.info(
            "[Store][PG] COPY %s trace_failure_event rows done in %.3fs",
            len(results),
            time.perf_counter() - t_start,
        )
        return ids_added

    # ------------------------------------------------------------------
    # Read operations
    # ------------------------------------------------------------------
    @staticmethod
    async def _log_ids_for_kb_id(kb_id: str | None) -> list[str]:
        if not kb_id:
            return []
        stmt = select(LogFile.id).where(LogFile.kb_id == kb_id).where(
            LogFile.existed_status.is_(True)
        )
        async with PGManager.session() as session:
            result = await session.execute(stmt)
            return [r for r in result.scalars().all()]

    @staticmethod
    def _build_trace_base_stmt(req) -> select:
        stmt = select(TraceFailureEvent)
        return stmt

    @staticmethod
    async def list_trace_failure_events(
        req: ListTraceFailureEventResultRequest,
    ) -> tuple[int, list[TraceFailureEventModel]]:
        try:
            log_ids = await LogFailureEventPGManager._log_ids_for_kb_id(req.kb_id)
            if req.kb_id and not log_ids:
                return 0, []

            stmt = select(TraceFailureEvent)
            if log_ids:
                stmt = stmt.where(TraceFailureEvent.log_id.in_(log_ids))

            if req.trace_ids:
                stmt = stmt.where(TraceFailureEvent.trace_id.in_(req.trace_ids))

            overlap = LogFailureEventPGManager._array_overlap
            cond = overlap(TraceFailureEvent.pod_names, req.pod_names)
            if cond is not None:
                stmt = stmt.where(cond)
            cond = overlap(TraceFailureEvent.host_names, req.host_names)
            if cond is not None:
                stmt = stmt.where(cond)
            cond = overlap(TraceFailureEvent.cluster_names, req.cluster_names)
            if cond is not None:
                stmt = stmt.where(cond)

            ip_cond = LogFailureEventPGManager._ip_eq(TraceFailureEvent.src_ip, req.src_ip)
            if ip_cond is not None:
                stmt = stmt.where(ip_cond)
            ip_cond = LogFailureEventPGManager._ip_eq(TraceFailureEvent.dst_ip, req.dst_ip)
            if ip_cond is not None:
                stmt = stmt.where(ip_cond)

            if req.status_codes:
                stmt = stmt.where(TraceFailureEvent.status_code.in_(req.status_codes))

            if req.is_anomalous is not None:
                if req.is_anomalous:
                    stmt = stmt.where(
                        TraceFailureEvent.failure_mode.is_not(None),
                        TraceFailureEvent.failure_mode != "",
                    )
                else:
                    stmt = stmt.where(
                        (TraceFailureEvent.failure_mode.is_(None))
                        | (TraceFailureEvent.failure_mode == "")
                    )

            if req.start_time:
                stmt = stmt.where(
                    TraceFailureEvent.timestamp >= parse_timestamp(req.start_time)
                )
            if req.end_time:
                stmt = stmt.where(
                    TraceFailureEvent.timestamp <= parse_timestamp(req.end_time)
                )

            count_stmt = select(func.count()).select_from(stmt.subquery())
            async with PGManager.session() as session:
                total = (await session.execute(count_stmt)).scalar() or 0

            order = (
                TraceFailureEvent.timestamp.desc()
                if req.sort_desc
                else TraceFailureEvent.timestamp.asc()
            )
            stmt = stmt.order_by(order)
            offset = (req.page_num - 1) * req.page_cnt
            stmt = stmt.offset(offset).limit(req.page_cnt)

            async with PGManager.session() as session:
                result = await session.execute(stmt)
                rows = result.scalars().all()

            events = []
            for row in rows:
                events.append(
                    TraceFailureEventModel(
                        id=row.id,
                        log_id=row.log_id,
                        trace_id=row.trace_id,
                        pod_names=row.pod_names or [],
                        src_ip=format_ip(row.src_ip) or "",
                        dst_ip=format_ip(row.dst_ip) or "",
                        host_names=row.host_names or [],
                        cluster_names=row.cluster_names or [],
                        timestamp=format_timestamp(row.timestamp) or "",
                        status_code=row.status_code or "",
                        failure_mode=row.failure_mode or "",
                    )
                )
            return total, events
        except Exception as e:
            print(f"查询trace故障事件失败，错误信息: {str(e)}")
            return 0, []

    @staticmethod
    async def list_log_failure_events(
        req: ListLogFailureEventResultRequest,
    ) -> tuple[int, list[LogFailureEventModel]]:
        try:
            log_ids = []
            if req.kb_id is not None:
                log_ids = await LogFailureEventPGManager._log_ids_for_kb_id(req.kb_id)
            if req.log_id is not None:
                log_ids.append(req.log_id)

            if req.kb_id is not None and not log_ids:
                return 0, []

            stmt = select(LogFailureEvent)
            if log_ids:
                stmt = stmt.where(LogFailureEvent.log_id.in_(log_ids))
            if req.trace_ids:
                stmt = stmt.where(LogFailureEvent.trace_id.in_(req.trace_ids))

            stmt = stmt.order_by(LogFailureEvent.timestamp.asc())

            async with PGManager.session() as session:
                result = await session.execute(stmt)
                rows = result.scalars().all()

            events = []
            for row in rows:
                failure_mode_str = row.failure_mode or ""
                failure_mode_list = [
                    fm.strip() for fm in failure_mode_str.split(",") if fm.strip()
                ]
                events.append(
                    LogFailureEventModel(
                        id=row.id,
                        log_id=row.log_id,
                        log_file=row.log_file or "",
                        raw_text=row.raw_text or "",
                        host_name=row.host_name,
                        timestamp=format_timestamp(row.timestamp) or "",
                        level=row.level or "",
                        filename=row.filename or "",
                        pod_name=row.pod_name or "",
                        pid=row.pid or "",
                        tid=row.tid or "",
                        trace_id=row.trace_id or "",
                        cluster_name=row.cluster_name or "",
                        message=row.message or "",
                        status_code=row.status_code or "",
                        failure_mode=failure_mode_list,
                    )
                )
            return len(events), events
        except Exception as e:
            print(f"查询日志故障事件失败，错误信息: {str(e)}")
            return 0, []

    @staticmethod
    async def get_err_code_metrics(
        req: GetErrCodeMetricsRequest,
    ) -> tuple[int, dict[str, list[dict]]]:
        try:
            log_ids = await LogFailureEventPGManager._log_ids_for_kb_id(req.kb_id)
            if req.kb_id and not log_ids:
                return 0, {}

            stmt = select(TraceFailureEvent).where(
                TraceFailureEvent.failure_mode.is_not(None),
                TraceFailureEvent.failure_mode != "",
            )
            if log_ids:
                stmt = stmt.where(TraceFailureEvent.log_id.in_(log_ids))
            if req.err_codes:
                stmt = stmt.where(TraceFailureEvent.status_code.in_(req.err_codes))

            ip_cond = LogFailureEventPGManager._ip_eq(TraceFailureEvent.src_ip, req.src_ip)
            if ip_cond is not None:
                stmt = stmt.where(ip_cond)
            ip_cond = LogFailureEventPGManager._ip_eq(TraceFailureEvent.dst_ip, req.dst_ip)
            if ip_cond is not None:
                stmt = stmt.where(ip_cond)

            overlap = LogFailureEventPGManager._array_overlap
            cond = overlap(TraceFailureEvent.pod_names, req.pod_names)
            if cond is not None:
                stmt = stmt.where(cond)
            cond = overlap(TraceFailureEvent.host_names, req.host_names)
            if cond is not None:
                stmt = stmt.where(cond)
            cond = overlap(TraceFailureEvent.cluster_names, req.cluster_names)
            if cond is not None:
                stmt = stmt.where(cond)

            if req.start_time:
                stmt = stmt.where(
                    TraceFailureEvent.timestamp >= parse_timestamp(req.start_time)
                )
            if req.end_time:
                stmt = stmt.where(
                    TraceFailureEvent.timestamp <= parse_timestamp(req.end_time)
                )

            stmt = stmt.order_by(TraceFailureEvent.timestamp.asc())

            async with PGManager.session() as session:
                result = await session.execute(stmt)
                rows = result.scalars().all()

            if not rows:
                return 0, {}

            def round_down(dt: datetime | None) -> datetime | None:
                return dt.replace(microsecond=0) if dt else None

            def round_up(dt: datetime | None) -> datetime | None:
                if dt is None:
                    return None
                if dt.microsecond > 0:
                    return (dt + timedelta(seconds=1)).replace(microsecond=0)
                return dt

            timestamps = []
            for row in rows:
                ts = row.timestamp
                if ts:
                    timestamps.append((ts, row.status_code or "UNKNOWN"))

            if not timestamps:
                return 0, {}

            min_time = min(ts[0] for ts in timestamps)
            max_time = max(ts[0] for ts in timestamps)

            if req.start_time:
                start_dt = parse_timestamp(req.start_time)
                if start_dt:
                    min_time = round_down(start_dt) or min_time
            if req.end_time:
                end_dt = parse_timestamp(req.end_time)
                if end_dt:
                    max_time = round_up(end_dt) or max_time
            else:
                max_time = round_up(max_time) or max_time

            err_code_events: dict[str, list[datetime]] = defaultdict(list)
            for ts, status_code in timestamps:
                err_code_events[status_code].append(ts)

            for code in err_code_events:
                err_code_events[code].sort()

            def sample_curve(points: list[dict], max_points: int) -> list[dict]:
                if len(points) <= max_points:
                    return points
                non_zero_points = [p for p in points if p["err_cnt"] > 0]
                if len(non_zero_points) <= max_points:
                    return non_zero_points
                peak_indices = set()
                for i in range(1, len(non_zero_points) - 1):
                    prev_cnt = non_zero_points[i - 1]["err_cnt"]
                    curr_cnt = non_zero_points[i]["err_cnt"]
                    next_cnt = non_zero_points[i + 1]["err_cnt"]
                    if curr_cnt > prev_cnt and curr_cnt > next_cnt:
                        peak_indices.add(i)
                    elif curr_cnt < prev_cnt and curr_cnt < next_cnt:
                        peak_indices.add(i)
                if len(peak_indices) >= max_points:
                    sorted_peaks = sorted(
                        peak_indices,
                        key=lambda i: non_zero_points[i]["err_cnt"],
                        reverse=True,
                    )
                    selected_indices = set(sorted_peaks[:max_points])
                    return sorted(
                        [non_zero_points[i] for i in selected_indices],
                        key=lambda p: p["time"],
                    )
                remaining_slots = max_points - len(peak_indices)
                non_peak_indices = [
                    i for i in range(len(non_zero_points)) if i not in peak_indices
                ]
                if len(non_peak_indices) <= remaining_slots:
                    return non_zero_points
                sorted_non_peak = sorted(
                    non_peak_indices,
                    key=lambda i: non_zero_points[i]["err_cnt"],
                    reverse=True,
                )
                selected_non_peak = set(sorted_non_peak[:remaining_slots])
                all_selected_indices = peak_indices | selected_non_peak
                return [non_zero_points[i] for i in sorted(all_selected_indices)]

            result: dict[str, list[dict]] = {}
            total_points = 0
            for err_code, event_times_sorted in err_code_events.items():
                time_count_map: dict[datetime, int] = defaultdict(int)
                for event_time in event_times_sorted:
                    base_second = event_time.replace(microsecond=0)
                    for offset in (-1, 0, 1):
                        check_time = base_second + timedelta(seconds=offset)
                        if min_time <= check_time <= max_time:
                            window_start = check_time - timedelta(seconds=0.5)
                            window_end = check_time + timedelta(seconds=0.5)
                            if window_start <= event_time <= window_end:
                                time_count_map[check_time] += 1
                curve_data = [
                    {
                        "time": time_point.strftime("%Y-%m-%d %H:%M:%S"),
                        "err_cnt": count,
                    }
                    for time_point, count in sorted(time_count_map.items())
                ]
                sampled_data = sample_curve(curve_data, req.max_points)
                result[err_code] = sampled_data
                if len(sampled_data) > total_points:
                    total_points = len(sampled_data)

            return total_points, result
        except Exception as e:
            print(f"获取故障码指标失败，错误信息: {str(e)}")
            import traceback

            traceback.print_exc()
            return 0, {}

    @staticmethod
    async def list_time_aggregated_failure_events(
        req: ListTimeAggregatedFailureEventRequest,
    ) -> tuple[int, list[str], list[dict]]:
        from collections import defaultdict

        try:
            log_ids = await LogFailureEventPGManager._log_ids_for_kb_id(req.kb_id)
            if req.kb_id and not log_ids:
                return 0, ["all"], []

            interval = req.interval
            if interval not in ("second", "minute", "hour"):
                interval = "minute"
            time_bucket = func.date_trunc(interval, TraceFailureEvent.timestamp).label(
                "time_bucket"
            )

            stmt = (
                select(
                    time_bucket,
                    TraceFailureEvent.status_code,
                    func.count().label("cnt"),
                )
                .where(TraceFailureEvent.failure_mode.is_not(None))
                .where(TraceFailureEvent.failure_mode != "")
                .where(TraceFailureEvent.status_code.is_not(None))
                .where(TraceFailureEvent.status_code != "")
                .where(TraceFailureEvent.src_ip.is_not(None))
                .where(TraceFailureEvent.dst_ip.is_not(None))
            )
            if log_ids:
                stmt = stmt.where(TraceFailureEvent.log_id.in_(log_ids))

            if req.cluster_name:
                stmt = stmt.where(
                    TraceFailureEvent.cluster_names.contains([req.cluster_name])
                )
            if req.host:
                stmt = stmt.where(TraceFailureEvent.host_names.contains([req.host]))
            if req.pod_ip:
                stmt = stmt.where(TraceFailureEvent.pod_names.contains([req.pod_ip]))

            ip_cond = LogFailureEventPGManager._ip_eq(TraceFailureEvent.src_ip, req.src_ip)
            if ip_cond is not None:
                stmt = stmt.where(ip_cond)
            ip_cond = LogFailureEventPGManager._ip_eq(TraceFailureEvent.dst_ip, req.dst_ip)
            if ip_cond is not None:
                stmt = stmt.where(ip_cond)

            if req.start_time:
                stmt = stmt.where(
                    TraceFailureEvent.timestamp >= parse_timestamp(req.start_time)
                )
            if req.end_time:
                stmt = stmt.where(
                    TraceFailureEvent.timestamp <= parse_timestamp(req.end_time)
                )

            stmt = stmt.group_by(time_bucket, TraceFailureEvent.status_code)

            async with PGManager.session() as session:
                result = await session.execute(stmt)
                rows = result.mappings().all()

            if not rows:
                return 0, ["all"], []

            interval_delta = {
                "second": timedelta(seconds=1),
                "minute": timedelta(minutes=1),
                "hour": timedelta(hours=1),
            }.get(interval, timedelta(minutes=1))

            time_buckets: dict[datetime, dict[str, int]] = defaultdict(dict)
            all_status_codes = set()
            time_format = "%Y-%m-%d %H:%M:%S"

            for row in rows:
                bucket = row["time_bucket"]
                status_code = row["status_code"] or ""
                cnt = row["cnt"]
                if status_code:
                    time_buckets[bucket][status_code] = cnt
                    all_status_codes.add(status_code)

            try:
                sorted_codes = sorted(
                    list(all_status_codes),
                    key=lambda x: int(x) if x.isdigit() else x,
                )
            except Exception:
                sorted_codes = sorted(list(all_status_codes))

            err_codes = ["all"] + sorted_codes

            results = []
            for bucket, code_counts in time_buckets.items():
                bucket_start = bucket if isinstance(bucket, datetime) else datetime.strptime(str(bucket), time_format)
                bucket_end = bucket_start + interval_delta
                total_cnt = sum(code_counts.values())
                item = {
                    "start_time": bucket_start.strftime(time_format),
                    "end_time": bucket_end.strftime(time_format),
                    "status_code_cnt": {"all": total_cnt},
                }
                for code in sorted_codes:
                    cnt = code_counts.get(code, 0)
                    if cnt > 0:
                        item["status_code_cnt"][code] = cnt
                results.append(item)

            sort_fields = req.sort_fields if req.sort_fields else []
            valid_sort_fields = [
                sf for sf in sort_fields
                if sf.field == "timestamp" or sf.field in err_codes
            ]
            if valid_sort_fields:
                for sort_field in reversed(valid_sort_fields):
                    field_name = sort_field.field
                    is_desc = sort_field.order == "desc"
                    if field_name == "timestamp":
                        results.sort(key=lambda x: x["start_time"], reverse=is_desc)
                    else:
                        results.sort(
                            key=lambda x: x["status_code_cnt"].get(field_name, 0),
                            reverse=is_desc,
                        )
            else:
                sort_key = req.sort_by
                if sort_key == "timestamp":
                    results.sort(
                        key=lambda x: x["start_time"], reverse=req.sort_desc
                    )
                elif sort_key == "all" or sort_key not in err_codes:
                    results.sort(
                        key=lambda x: x["status_code_cnt"].get("all", 0),
                        reverse=req.sort_desc,
                    )
                else:
                    results.sort(
                        key=lambda x: (
                            x["status_code_cnt"].get(sort_key, 0),
                            x["status_code_cnt"].get("all", 0),
                        ),
                        reverse=req.sort_desc,
                    )

            total = len(results)
            start_idx = (req.page_num - 1) * req.page_cnt
            end_idx = start_idx + req.page_cnt
            results = results[start_idx:end_idx]

            return total, err_codes, results
        except Exception as e:
            print(f"查询时间段聚合故障事件失败，错误信息: {str(e)}")
            import traceback

            traceback.print_exc()
            return 0, ["all"], []

    @staticmethod
    async def list_pod_aggregated_failure_events(
        req: ListPodAggregatedFailureEventRequest,
    ) -> tuple[int, list[dict]]:
        from collections import defaultdict

        try:
            log_ids = await LogFailureEventPGManager._log_ids_for_kb_id(req.kb_id)
            if req.kb_id and not log_ids:
                return 0, []

            stmt = (
                select(
                    TraceFailureEvent.pod_names,
                    TraceFailureEvent.status_code,
                    func.count().label("cnt"),
                )
                .where(TraceFailureEvent.src_ip.is_not(None))
                .where(TraceFailureEvent.dst_ip.is_not(None))
                .where(TraceFailureEvent.pod_names.is_not(None))
                .where(TraceFailureEvent.failure_mode.is_not(None))
                .where(TraceFailureEvent.failure_mode != "")
                .where(TraceFailureEvent.status_code.is_not(None))
                .where(TraceFailureEvent.status_code != "")
            )
            if log_ids:
                stmt = stmt.where(TraceFailureEvent.log_id.in_(log_ids))
            if req.start_time:
                stmt = stmt.where(
                    TraceFailureEvent.timestamp >= parse_timestamp(req.start_time)
                )
            if req.end_time:
                stmt = stmt.where(
                    TraceFailureEvent.timestamp <= parse_timestamp(req.end_time)
                )

            stmt = stmt.group_by(
                TraceFailureEvent.pod_names, TraceFailureEvent.status_code
            )

            async with PGManager.session() as session:
                result = await session.execute(stmt)
                rows = result.mappings().all()

            if not rows:
                return 0, []

            pod_status_counts: dict[str, dict[str, int]] = defaultdict(
                lambda: defaultdict(int)
            )
            all_status_codes = set()

            for row in rows:
                pod_names = row["pod_names"] or []
                status_code = row["status_code"] or ""
                cnt = row["cnt"]
                for pod_name in pod_names:
                    pod_name = pod_name.strip()
                    if not pod_name:
                        continue
                    pod_status_counts[pod_name][status_code] += cnt
                    pod_status_counts[pod_name]["all"] += cnt
                    all_status_codes.add(status_code)

            try:
                sorted_codes = sorted(
                    list(all_status_codes),
                    key=lambda x: int(x) if x.isdigit() else x,
                )
            except Exception:
                sorted_codes = sorted(list(all_status_codes))

            results = []
            for pod_name, code_counts in pod_status_counts.items():
                item = {
                    "pod_name": pod_name,
                    "status_code_cnt": {"all": code_counts.get("all", 0)},
                }
                for code in sorted_codes:
                    cnt = code_counts.get(code, 0)
                    if cnt > 0:
                        item["status_code_cnt"][code] = cnt
                results.append(item)

            sort_fields = req.sort_fields if req.sort_fields else []
            valid_codes = ["all"] + sorted_codes
            valid_sort_fields = [
                sf for sf in sort_fields if sf.field in valid_codes
            ]
            if valid_sort_fields:
                for sort_field in reversed(valid_sort_fields):
                    is_desc = sort_field.order == "desc"
                    results.sort(
                        key=lambda x: x["status_code_cnt"].get(sort_field.field, 0),
                        reverse=is_desc,
                    )
            else:
                sort_key = req.sort_by
                if sort_key == "all" or sort_key not in valid_codes:
                    results.sort(
                        key=lambda x: x["status_code_cnt"].get("all", 0),
                        reverse=req.sort_desc,
                    )
                else:
                    results.sort(
                        key=lambda x: (
                            0 if x["status_code_cnt"].get(sort_key, 0) == 0 else 1,
                            x["status_code_cnt"].get(sort_key, 0),
                            x["status_code_cnt"].get("all", 0),
                        ),
                        reverse=req.sort_desc,
                    )

            total = len(results)
            start_idx = (req.page_num - 1) * req.page_cnt
            end_idx = start_idx + req.page_cnt
            results = results[start_idx:end_idx]

            return total, results
        except Exception as e:
            print(f"查询pod聚合故障事件失败，错误信息: {str(e)}")
            import traceback

            traceback.print_exc()
            return 0, []

    @staticmethod
    async def list_src_dst_aggregated_failure_events(
        req: ListSrcDstAggregatedFailureEventRequest,
    ) -> tuple[int, list[dict]]:
        from collections import defaultdict

        try:
            log_ids = await LogFailureEventPGManager._log_ids_for_kb_id(req.kb_id)
            if req.kb_id and not log_ids:
                return 0, []

            src_ip_str = func.host(TraceFailureEvent.src_ip).label("src_ip_str")
            dst_ip_str = func.host(TraceFailureEvent.dst_ip).label("dst_ip_str")

            stmt = (
                select(
                    src_ip_str,
                    dst_ip_str,
                    TraceFailureEvent.status_code,
                    func.count().label("cnt"),
                )
                .where(TraceFailureEvent.src_ip.is_not(None))
                .where(TraceFailureEvent.src_ip.is_not(None))
                .where(TraceFailureEvent.dst_ip.is_not(None))
                .where(TraceFailureEvent.dst_ip.is_not(None))
                .where(TraceFailureEvent.failure_mode.is_not(None))
                .where(TraceFailureEvent.failure_mode != "")
                .where(TraceFailureEvent.status_code.is_not(None))
                .where(TraceFailureEvent.status_code != "")
            )
            if log_ids:
                stmt = stmt.where(TraceFailureEvent.log_id.in_(log_ids))

            if req.cluster_name:
                stmt = stmt.where(
                    TraceFailureEvent.cluster_names.contains([req.cluster_name])
                )
            if req.host:
                stmt = stmt.where(TraceFailureEvent.host_names.contains([req.host]))
            if req.pod_ip:
                stmt = stmt.where(TraceFailureEvent.pod_names.contains([req.pod_ip]))

            ip_cond = LogFailureEventPGManager._ip_eq(TraceFailureEvent.src_ip, req.src_ip)
            if ip_cond is not None:
                stmt = stmt.where(ip_cond)
            ip_cond = LogFailureEventPGManager._ip_eq(TraceFailureEvent.dst_ip, req.dst_ip)
            if ip_cond is not None:
                stmt = stmt.where(ip_cond)

            if req.start_time:
                stmt = stmt.where(
                    TraceFailureEvent.timestamp >= parse_timestamp(req.start_time)
                )
            if req.end_time:
                stmt = stmt.where(
                    TraceFailureEvent.timestamp <= parse_timestamp(req.end_time)
                )

            stmt = stmt.group_by(
                src_ip_str, dst_ip_str, TraceFailureEvent.status_code
            )

            async with PGManager.session() as session:
                result = await session.execute(stmt)
                rows = result.mappings().all()

            if not rows:
                return 0, []

            src_dst_status_counts: dict[str, dict[str, int]] = defaultdict(
                lambda: defaultdict(int)
            )
            all_status_codes = set()

            for row in rows:
                src_ip = row["src_ip_str"] or ""
                dst_ip = row["dst_ip_str"] or ""
                status_code = row["status_code"] or ""
                cnt = row["cnt"]
                key = f"{src_ip}|{dst_ip}"
                src_dst_status_counts[key][status_code] += cnt
                src_dst_status_counts[key]["all"] += cnt
                all_status_codes.add(status_code)

            try:
                sorted_codes = sorted(
                    list(all_status_codes),
                    key=lambda x: int(x) if x.isdigit() else x,
                )
            except Exception:
                sorted_codes = sorted(list(all_status_codes))

            results = []
            for key, code_counts in src_dst_status_counts.items():
                src_ip, dst_ip = key.split("|")
                item = {
                    "src_ip": src_ip,
                    "dst_ip": dst_ip,
                    "status_code_cnt": {"all": code_counts.get("all", 0)},
                }
                for code in sorted_codes:
                    cnt = code_counts.get(code, 0)
                    if cnt > 0:
                        item["status_code_cnt"][code] = cnt
                results.append(item)

            sort_fields = req.sort_fields if req.sort_fields else []
            valid_codes = ["all"] + sorted_codes
            valid_sort_fields = [
                sf for sf in sort_fields if sf.field in valid_codes
            ]
            if valid_sort_fields:
                for sort_field in reversed(valid_sort_fields):
                    is_desc = sort_field.order == "desc"
                    results.sort(
                        key=lambda x: x["status_code_cnt"].get(sort_field.field, 0),
                        reverse=is_desc,
                    )
            else:
                sort_key = req.sort_by
                if sort_key == "all" or sort_key not in valid_codes:
                    results.sort(
                        key=lambda x: x["status_code_cnt"].get("all", 0),
                        reverse=req.sort_desc,
                    )
                else:
                    results.sort(
                        key=lambda x: (
                            0 if x["status_code_cnt"].get(sort_key, 0) == 0 else 1,
                            x["status_code_cnt"].get(sort_key, 0),
                            x["status_code_cnt"].get("all", 0),
                        ),
                        reverse=req.sort_desc,
                    )

            total = len(results)
            start_idx = (req.page_num - 1) * req.page_cnt
            end_idx = start_idx + req.page_cnt
            results = results[start_idx:end_idx]

            return total, results
        except Exception as e:
            print(f"查询src_dst聚合故障事件失败，错误信息: {str(e)}")
            import traceback

            traceback.print_exc()
            return 0, []
