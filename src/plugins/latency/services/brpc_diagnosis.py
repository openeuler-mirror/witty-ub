"""Read-only service layer for imported BRPC diagnosis results."""

from __future__ import annotations

import hashlib
import json
import logging
import os
import re
from collections import defaultdict
from datetime import datetime, timedelta, timezone

from latency.database.engine import PGManager
from latency.database.managers.brpc_diagnosis import (
    UNRESOLVED_INTERFACE_ID,
    UNRESOLVED_INTERFACE_NAME,
    BrpcDiagnosisPGManager,
)
from latency.exceptions import BadRequestBizException, NotFoundBizException
from latency.schemas.brpc_diagnosis import (
    BrpcAbnormalThread,
    BrpcAggregateWindowSize,
    BrpcComponent,
    BrpcDiagBatchMetadata,
    BrpcDiagHitLog,
    BrpcDiagSchema,
    BrpcFailureModeHit,
    BrpcFailureGraph,
    BrpcFailureGraphNode,
    BrpcInterfaceHit,
    BrpcInterfaceTimelinePoint,
    BrpcInterfaceTimelineSeries,
    BrpcMetricSortField,
    BrpcPodAggregatedEvent,
    BrpcSortOrder,
    BrpcThreadAggregatedEvent,
    BrpcWindowSize,
    GetBrpcAbnormalThreadDetailMsg,
    GetBrpcBatchMsg,
    GetBrpcInterfaceTimelineMsg,
    GetBrpcPodEventDetailMsg,
    GetBrpcTaskBatchMsg,
    GetBrpcThreadEventDetailMsg,
    ListBrpcAbnormalThreadsMsg,
    ListBrpcDiagHitsMsg,
    ListBrpcPodEventsMsg,
    ListBrpcThreadEventsMsg,
)


WINDOW_SIZE_US: dict[BrpcWindowSize, int] = {
    "10s": 10_000_000,
    "1m": 60_000_000,
    "10m": 600_000_000,
    "1h": 3_600_000_000,
}
AGGREGATE_WINDOW_SIZE_US: dict[BrpcAggregateWindowSize, int] = {
    "1s": 1_000_000,
    "1m": 60_000_000,
    "1h": 3_600_000_000,
}

# Zero-filling is performed after database aggregation.  Bound the number of
# generated buckets so an accidental multi-year 10-second query cannot exhaust
# the API process before PostgreSQL returns any rows.
MAX_TIMELINE_WINDOWS = 100_000


class BrpcDiagnosisService:
    @staticmethod
    def _validate_timestamp_range(
        start_timestamp: int,
        end_timestamp: int,
    ) -> None:
        if end_timestamp <= start_timestamp:
            raise BadRequestBizException(
                message="end_time 必须晚于 start_time"
            )

    @staticmethod
    async def _require_batch(session, batch_id: str):
        batch = await BrpcDiagnosisPGManager.get_batch(session, batch_id)
        if batch is None:
            raise NotFoundBizException(resource="BRPC 诊断 batch")
        return batch

    @staticmethod
    def _stable_hash(*parts: object) -> str:
        """Hash a typed, unambiguous JSON representation of a grouping key."""
        payload = json.dumps(
            list(parts),
            ensure_ascii=False,
            separators=(",", ":"),
        ).encode("utf-8")
        return hashlib.sha256(payload).hexdigest()

    @staticmethod
    def pod_event_id(
        batch_id: str,
        window_start_timestamp: int,
        window_end_timestamp: int,
        pod_ip: str,
    ) -> str:
        return BrpcDiagnosisService._stable_hash(
            batch_id,
            window_start_timestamp,
            window_end_timestamp,
            pod_ip,
        )

    @staticmethod
    def thread_event_id(
        batch_id: str,
        window_start_timestamp: int,
        window_end_timestamp: int,
        pod_ip: str,
        thread_id: int,
    ) -> str:
        return BrpcDiagnosisService._stable_hash(
            batch_id,
            window_start_timestamp,
            window_end_timestamp,
            pod_ip,
            thread_id,
        )

    @staticmethod
    def thread_key(
        batch_id: str,
        pod_ip: str,
        thread_id: int,
    ) -> str:
        return BrpcDiagnosisService._stable_hash(
            batch_id,
            pod_ip,
            thread_id,
        )

    @staticmethod
    async def get_batch_by_task_id(task_id: str) -> GetBrpcTaskBatchMsg:
        async with PGManager.session() as session:
            batch = await BrpcDiagnosisPGManager.get_batch_by_task_id(
                session,
                task_id,
            )
        if batch is None:
            raise NotFoundBizException(resource="BRPC 诊断 batch")
        return GetBrpcTaskBatchMsg(task_id=task_id, batch_id=batch.batch_id)

    @staticmethod
    async def get_batch(batch_id: str) -> GetBrpcBatchMsg:
        async with PGManager.session() as session:
            batch = await BrpcDiagnosisPGManager.get_batch(session, batch_id)
        if batch is None:
            raise NotFoundBizException(resource="BRPC 诊断 batch")
        return GetBrpcBatchMsg(
            batch=BrpcDiagBatchMetadata.model_validate(batch)
        )

    @staticmethod
    async def list_hits(
        *,
        batch_id: str,
        pod_ip: str,
        thread_id: int,
        page_num: int,
        page_cnt: int,
        start_timestamp: int | None = None,
        end_timestamp: int | None = None,
        pod_name: str | None = None,
    ) -> ListBrpcDiagHitsMsg:
        if (
            start_timestamp is not None
            and end_timestamp is not None
            and end_timestamp < start_timestamp
        ):
            raise BadRequestBizException(
                message="end_time 不能早于 start_time"
            )

        async with PGManager.session() as session:
            batch = await BrpcDiagnosisPGManager.get_batch(session, batch_id)
            if batch is None:
                raise NotFoundBizException(resource="BRPC 诊断 batch")
            total, rows = await BrpcDiagnosisPGManager.list_hits(
                session,
                batch_id=batch_id,
                pod_ip=pod_ip,
                thread_id=thread_id,
                page_num=page_num,
                page_cnt=page_cnt,
                start_timestamp=start_timestamp,
                end_timestamp=end_timestamp,
                pod_name=pod_name,
            )

        return ListBrpcDiagHitsMsg(
            batch_id=batch_id,
            total=total,
            hits=[BrpcDiagHitLog.model_validate(row) for row in rows],
        )

    # --- Thread log reader (all lines, not just fault hits) ---

    _UTC_EPOCH = datetime(1970, 1, 1, tzinfo=timezone.utc)
    _UTC_PLUS_8 = timezone(timedelta(hours=8))

    _LOG_LINE_RE = re.compile(
        r"^\[(\d{8} \d{2}:\d{2}:\d{2}\.\d{6})\]"
        r"\[([^\]]*)\]"
        r"\[([^\]]*)\]"
        r"\[([^\]]*)\]"
        r"\[([^\]]*)\]"
        r"\[([^\]]*)\]"
        r"\[([^\]]*)\]"
        r"\s?(.*)$"
    )

    _URMA_PREFIX = "[URMA]"
    _URMA_INNER_RE = re.compile(
        r"^\[URMA\]\[thread_id=(\d+)\]\[([^\]]*)\]\[([^\]]*)\]"
    )

    @staticmethod
    def _log_time_to_epoch_us(time_str: str) -> int:
        dt = datetime.strptime(time_str, "%Y%m%d %H:%M:%S.%f")
        dt = dt.replace(tzinfo=BrpcDiagnosisService._UTC_PLUS_8)
        delta = dt - BrpcDiagnosisService._UTC_EPOCH
        return int(
            delta.days * 86_400_000_000
            + delta.seconds * 1_000_000
            + delta.microseconds
        )

    @staticmethod
    async def list_thread_logs(
        *,
        batch_id: str,
        pod_ip: str,
        thread_id: int,
        start_timestamp: int | None = None,
        end_timestamp: int | None = None,
    ) -> ListBrpcDiagHitsMsg:
        """Read ALL log lines for one thread from the original log file.

        Fault lines are matched with hits from the database to populate
        failure_mode_id; non-fault lines get an empty failure_mode_id.
        """
        from latency.database.managers.log_file import LogFilePGManager
        from latency.database.managers.task import TaskPGManager

        logger = logging.getLogger(__name__)

        async with PGManager.session() as session:
            batch = await BrpcDiagnosisPGManager.get_batch(session, batch_id)
            if batch is None:
                raise NotFoundBizException(resource="BRPC 诊断 batch")

            # Resolve batch → task → log file path
            task = await TaskPGManager.get_task_by_task_id(batch.task_id)
            if task is None or not task.op_id:
                raise NotFoundBizException(resource="BRPC 诊断 task")
            log_file = await LogFilePGManager.get_log_file_by_log_file_id(
                task.op_id
            )
            if log_file is None or not log_file.file_path:
                raise NotFoundBizException(resource="BRPC 诊断日志文件")

            # Get fault hits for matching
            _, hit_rows = await BrpcDiagnosisPGManager.list_hits(
                session,
                batch_id=batch_id,
                pod_ip=pod_ip,
                thread_id=thread_id,
                page_num=1,
                page_cnt=1_000_000,
                start_timestamp=start_timestamp,
                end_timestamp=end_timestamp,
            )

        # Build {timestamp_us: failure_mode_id} for fault matching
        fault_map: dict[int, str] = {}
        for row in hit_rows:
            fault_map[row.timestamp] = row.failure_mode_id

        file_path = log_file.file_path

        # Determine which file(s) to read — mirror C++ ForEachBrpcLog:
        # recursive read of all regular files (any extension)
        files_to_read: list[str] = []
        if os.path.isdir(file_path):
            for name in (f"{pod_ip}.log", pod_ip):
                candidate = os.path.join(file_path, name)
                if os.path.isfile(candidate):
                    files_to_read = [candidate]
                    break
            if not files_to_read:
                walked: list[str] = []
                for root, _dirs, fnames in os.walk(file_path):
                    for fname in fnames:
                        fpath = os.path.join(root, fname)
                        if os.path.isfile(fpath):
                            walked.append(fpath)
                files_to_read = sorted(walked)
        elif os.path.isfile(file_path):
            files_to_read = [file_path]
        else:
            logger.warning("BRPC thread-logs: log file not found: %s", file_path)
            return ListBrpcDiagHitsMsg(
                batch_id=batch_id, total=0, hits=[]
            )

        # Parse and filter log lines
        all_logs: list[BrpcDiagHitLog] = []
        counter = 0
        tid_str = str(thread_id)
        for fpath in files_to_read:
            try:
                with open(fpath, "r", encoding="utf-8", errors="ignore") as f:
                    for line in f:
                        line = line.rstrip("\n")
                        m = BrpcDiagnosisService._LOG_LINE_RE.match(line)
                        if m is None:
                            continue
                        (
                            time_str,
                            pod_name,
                            line_pod_ip,
                            component_raw,
                            location,
                            line_tid,
                            trace_id,
                            message,
                        ) = m.groups()

                        # URMA inner log: override thread_id/component/location/
                        # trace_id to match C++ ParseBrpcLogFields behaviour.
                        urma_offset = message.find(
                            BrpcDiagnosisService._URMA_PREFIX
                        )
                        if urma_offset != -1:
                            um = BrpcDiagnosisService._URMA_INNER_RE.match(
                                message[urma_offset:]
                            )
                            if um is None:
                                continue
                            line_tid = um.group(1)
                            component_raw = "URMA"
                            location = um.group(3)
                            trace_id = um.group(2) if um.group(2) != "-" else ""

                        if line_pod_ip != pod_ip:
                            continue
                        if line_tid != tid_str:
                            continue

                        ts_us = (
                            BrpcDiagnosisService._log_time_to_epoch_us(time_str)
                        )
                        if (
                            start_timestamp is not None
                            and ts_us < start_timestamp
                        ):
                            continue
                        if (
                            end_timestamp is not None
                            and ts_us >= end_timestamp
                        ):
                            continue

                        # Parse filename:func:line
                        parts = location.rsplit(":", 2)
                        if len(parts) == 3:
                            filename, func_name, line_num_str = parts
                            try:
                                line_num = int(line_num_str)
                            except ValueError:
                                line_num = None
                        else:
                            filename = location
                            func_name = None
                            line_num = None

                        component = component_raw.lower() or None
                        failure_mode_id = fault_map.get(ts_us, "")

                        counter += 1
                        all_logs.append(
                            BrpcDiagHitLog(
                                hit_id=f"{batch_id}:{ts_us}:{counter}",
                                batch_id=batch_id,
                                schema_id=batch.schema_id,
                                failure_mode_id=failure_mode_id,
                                interface_id=None,
                                interface_resolution="unresolved",
                                time=ts_us,
                                pod_name=pod_name or None,
                                pod_ip=line_pod_ip or None,
                                component=component,
                                filename=filename or None,
                                function_name=func_name,
                                line_number=line_num,
                                thread_id=thread_id,
                                trace_id=trace_id or None,
                                message=message,
                            )
                        )
            except (IOError, OSError) as exc:
                logger.warning("BRPC thread-logs: failed to read %s: %s", fpath, exc)

        all_logs.sort(key=lambda h: h.time)

        return ListBrpcDiagHitsMsg(
            batch_id=batch_id,
            total=len(all_logs),
            hits=all_logs,
        )

    @staticmethod
    async def get_interface_timeline(
        *,
        batch_id: str,
        start_timestamp: int,
        end_timestamp: int,
        window_size: BrpcWindowSize,
        component: BrpcComponent | None = None,
        interface_id: str | None = None,
        pod_ip: str | None = None,
        pod_name: str | None = None,
    ) -> GetBrpcInterfaceTimelineMsg:
        BrpcDiagnosisService._validate_timestamp_range(
            start_timestamp,
            end_timestamp,
        )

        window_us = WINDOW_SIZE_US[window_size]
        first_window_timestamp = (start_timestamp // window_us) * window_us
        window_count = (
            end_timestamp - first_window_timestamp + window_us - 1
        ) // window_us
        if window_count > MAX_TIMELINE_WINDOWS:
            raise BadRequestBizException(
                message=(
                    "查询时间范围过大，请增大 window_size 或缩小时间范围"
                )
            )

        async with PGManager.session() as session:
            batch = await BrpcDiagnosisPGManager.get_batch(session, batch_id)
            if batch is None:
                raise NotFoundBizException(resource="BRPC 诊断 batch")
            aggregates = (
                await BrpcDiagnosisPGManager.get_interface_timeline_aggregates(
                    session,
                    batch_id=batch_id,
                    start_timestamp=start_timestamp,
                    end_timestamp=end_timestamp,
                    window_us=window_us,
                    interface_component=component,
                    interface_id=interface_id,
                    pod_ip=pod_ip,
                    pod_name=pod_name,
                )
            )

        series = BrpcDiagnosisService._zero_fill_timeline(
            aggregates=aggregates,
            first_window_timestamp=first_window_timestamp,
            end_timestamp=end_timestamp,
            window_us=window_us,
        )
        if (
            component is None
            and interface_id is None
            and not any(
                item.interface_id == UNRESOLVED_INTERFACE_ID for item in series
            )
        ):
            series.append(
                BrpcInterfaceTimelineSeries(
                    component="unknown",
                    interface_id=UNRESOLVED_INTERFACE_ID,
                    interface_name=UNRESOLVED_INTERFACE_NAME,
                    function_name="",
                    points=[
                        BrpcInterfaceTimelinePoint(
                            window_start_time=window_start_timestamp,
                            window_end_time=window_start_timestamp + window_us,
                            interface_hit_count=0,
                        )
                        for window_start_timestamp in range(
                            first_window_timestamp, end_timestamp, window_us
                        )
                    ],
                )
            )

        return GetBrpcInterfaceTimelineMsg(
            batch_id=batch_id,
            start_time=start_timestamp,
            end_time=end_timestamp,
            window_size=window_size,
            series=series,
        )

    @staticmethod
    def _interface_hits(rows: list[dict]) -> list[BrpcInterfaceHit]:
        return sorted(
            (BrpcInterfaceHit.model_validate(row) for row in rows),
            key=lambda item: (item.component, item.interface_id),
        )

    @staticmethod
    def _failure_mode_hits(rows: list[dict]) -> list[BrpcFailureModeHit]:
        return [BrpcFailureModeHit.model_validate(row) for row in rows]

    @staticmethod
    def _decode_interface_hits(value) -> list[BrpcInterfaceHit]:
        if isinstance(value, str):
            value = json.loads(value)
        return BrpcDiagnosisService._interface_hits(list(value or []))

    @staticmethod
    async def list_pod_events(
        *,
        batch_id: str,
        start_timestamp: int,
        end_timestamp: int,
        window_size: BrpcAggregateWindowSize,
        sort_order: BrpcSortOrder = "asc",
        metric_sort_fields: list[BrpcMetricSortField] | None = None,
        page_num: int,
        page_cnt: int,
        pod_ip: str | None = None,
        pod_name: str | None = None,
    ) -> ListBrpcPodEventsMsg:
        BrpcDiagnosisService._validate_timestamp_range(
            start_timestamp,
            end_timestamp,
        )
        window_us = AGGREGATE_WINDOW_SIZE_US[window_size]
        async with PGManager.session() as session:
            await BrpcDiagnosisService._require_batch(session, batch_id)
            total, rows = await BrpcDiagnosisPGManager.list_pod_events(
                session,
                batch_id=batch_id,
                start_timestamp=start_timestamp,
                end_timestamp=end_timestamp,
                window_us=window_us,
                sort_order=sort_order,
                metric_sort_fields=metric_sort_fields or [],
                page_num=page_num,
                page_cnt=page_cnt,
                pod_ip=pod_ip,
                pod_name=pod_name,
            )
        events = []
        for row in rows:
            window_start_timestamp = int(row["window_start_timestamp"])
            window_end_timestamp = window_start_timestamp + window_us
            pod_ip = str(row["pod_ip"])
            events.append(
                BrpcPodAggregatedEvent(
                    event_id=BrpcDiagnosisService.pod_event_id(
                        batch_id,
                        window_start_timestamp,
                        window_end_timestamp,
                        pod_ip,
                    ),
                    batch_id=batch_id,
                    window_start_time=window_start_timestamp,
                    window_end_time=window_end_timestamp,
                    pod_ip=pod_ip,
                    pod_name=row.get("pod_name"),
                    interface_hits=BrpcDiagnosisService._decode_interface_hits(
                        row.get("interface_hits")
                    ),
                )
            )
        return ListBrpcPodEventsMsg(
            batch_id=batch_id,
            total=total,
            events=events,
        )

    @staticmethod
    async def list_thread_events(
        *,
        batch_id: str,
        start_timestamp: int,
        end_timestamp: int,
        window_size: BrpcAggregateWindowSize,
        sort_order: BrpcSortOrder = "asc",
        metric_sort_fields: list[BrpcMetricSortField] | None = None,
        page_num: int,
        page_cnt: int,
        pod_ip: str | None = None,
        pod_name: str | None = None,
    ) -> ListBrpcThreadEventsMsg:
        BrpcDiagnosisService._validate_timestamp_range(
            start_timestamp,
            end_timestamp,
        )
        window_us = AGGREGATE_WINDOW_SIZE_US[window_size]
        async with PGManager.session() as session:
            await BrpcDiagnosisService._require_batch(session, batch_id)
            total, rows = await BrpcDiagnosisPGManager.list_thread_events(
                session,
                batch_id=batch_id,
                start_timestamp=start_timestamp,
                end_timestamp=end_timestamp,
                window_us=window_us,
                sort_order=sort_order,
                metric_sort_fields=metric_sort_fields or [],
                page_num=page_num,
                page_cnt=page_cnt,
                pod_ip=pod_ip,
                pod_name=pod_name,
            )
        events = []
        for row in rows:
            window_start_timestamp = int(row["window_start_timestamp"])
            window_end_timestamp = window_start_timestamp + window_us
            pod_ip = str(row["pod_ip"])
            thread_id = int(row["thread_id"])
            events.append(
                BrpcThreadAggregatedEvent(
                    event_id=BrpcDiagnosisService.thread_event_id(
                        batch_id,
                        window_start_timestamp,
                        window_end_timestamp,
                        pod_ip,
                        thread_id,
                    ),
                    batch_id=batch_id,
                    window_start_time=window_start_timestamp,
                    window_end_time=window_end_timestamp,
                    pod_ip=pod_ip,
                    pod_name=row.get("pod_name"),
                    thread_id=thread_id,
                    interface_hits=BrpcDiagnosisService._decode_interface_hits(
                        row.get("interface_hits")
                    ),
                )
            )
        return ListBrpcThreadEventsMsg(
            batch_id=batch_id,
            total=total,
            events=events,
        )

    @staticmethod
    async def get_pod_event_detail(
        *,
        event_id: str,
        batch_id: str,
        window_start_timestamp: int,
        window_end_timestamp: int,
        pod_ip: str,
        page_num: int,
        page_cnt: int,
        pod_name: str | None = None,
    ) -> GetBrpcPodEventDetailMsg:
        BrpcDiagnosisService._validate_timestamp_range(
            window_start_timestamp,
            window_end_timestamp,
        )
        expected_id = BrpcDiagnosisService.pod_event_id(
            batch_id,
            window_start_timestamp,
            window_end_timestamp,
            pod_ip,
        )
        if event_id != expected_id:
            raise BadRequestBizException(message="event_id 与 Pod 分组键不匹配")
        async with PGManager.session() as session:
            batch = await BrpcDiagnosisService._require_batch(session, batch_id)
            interface_rows = await BrpcDiagnosisPGManager.get_interface_hit_counts(
                session,
                batch_id=batch_id,
                start_timestamp=window_start_timestamp,
                end_timestamp=window_end_timestamp,
                pod_ip=pod_ip,
                pod_name=pod_name,
            )
            failure_rows = (
                await BrpcDiagnosisPGManager.get_failure_mode_hit_counts(
                    session,
                    batch_id=batch_id,
                    start_timestamp=window_start_timestamp,
                    end_timestamp=window_end_timestamp,
                    pod_ip=pod_ip,
                    pod_name=pod_name,
                )
            )
            hit_total, hit_rows = await BrpcDiagnosisPGManager.list_hits(
                session,
                batch_id=batch_id,
                page_num=page_num,
                page_cnt=page_cnt,
                start_timestamp=window_start_timestamp,
                end_timestamp=window_end_timestamp,
                pod_ip=pod_ip,
                pod_name=pod_name,
            )
            schema = await BrpcDiagnosisPGManager.get_schema(
                session,
                batch.schema_id,
            )
        if not failure_rows or schema is None:
            raise NotFoundBizException(resource="BRPC Pod 聚合事件")
        interface_hits = BrpcDiagnosisService._interface_hits(interface_rows)
        failures = BrpcDiagnosisService._failure_mode_hits(failure_rows)
        return GetBrpcPodEventDetailMsg(
            event=BrpcPodAggregatedEvent(
                event_id=event_id,
                batch_id=batch_id,
                window_start_time=window_start_timestamp,
                window_end_time=window_end_timestamp,
                pod_ip=pod_ip,
                pod_name=hit_rows[0].pod_name if hit_rows else None,
                interface_hits=interface_hits,
            ),
            failure_modes=failures,
            failure_graph=BrpcDiagnosisService._build_failure_graph(
                schema,
                failure_rows,
            ),
            hit_total=hit_total,
            hits=[BrpcDiagHitLog.model_validate(row) for row in hit_rows],
        )

    @staticmethod
    async def get_thread_event_detail(
        *,
        event_id: str,
        batch_id: str,
        window_start_timestamp: int,
        window_end_timestamp: int,
        pod_ip: str,
        thread_id: int,
        page_num: int,
        page_cnt: int,
        pod_name: str | None = None,
    ) -> GetBrpcThreadEventDetailMsg:
        BrpcDiagnosisService._validate_timestamp_range(
            window_start_timestamp,
            window_end_timestamp,
        )
        expected_id = BrpcDiagnosisService.thread_event_id(
            batch_id,
            window_start_timestamp,
            window_end_timestamp,
            pod_ip,
            thread_id,
        )
        if event_id != expected_id:
            raise BadRequestBizException(message="event_id 与 Thread 分组键不匹配")
        async with PGManager.session() as session:
            batch = await BrpcDiagnosisService._require_batch(session, batch_id)
            interface_rows = await BrpcDiagnosisPGManager.get_interface_hit_counts(
                session,
                batch_id=batch_id,
                start_timestamp=window_start_timestamp,
                end_timestamp=window_end_timestamp,
                pod_ip=pod_ip,
                pod_name=pod_name,
                thread_id=thread_id,
            )
            failure_rows = (
                await BrpcDiagnosisPGManager.get_failure_mode_hit_counts(
                    session,
                    batch_id=batch_id,
                    start_timestamp=window_start_timestamp,
                    end_timestamp=window_end_timestamp,
                    pod_ip=pod_ip,
                    pod_name=pod_name,
                    thread_id=thread_id,
                )
            )
            hit_total, hit_rows = await BrpcDiagnosisPGManager.list_hits(
                session,
                batch_id=batch_id,
                page_num=page_num,
                page_cnt=page_cnt,
                start_timestamp=window_start_timestamp,
                end_timestamp=window_end_timestamp,
                pod_ip=pod_ip,
                pod_name=pod_name,
                thread_id=thread_id,
            )
            schema = await BrpcDiagnosisPGManager.get_schema(
                session,
                batch.schema_id,
            )
        if not failure_rows or schema is None:
            raise NotFoundBizException(resource="BRPC Thread 聚合事件")
        interface_hits = BrpcDiagnosisService._interface_hits(interface_rows)
        failures = BrpcDiagnosisService._failure_mode_hits(failure_rows)
        return GetBrpcThreadEventDetailMsg(
            event=BrpcThreadAggregatedEvent(
                event_id=event_id,
                batch_id=batch_id,
                window_start_time=window_start_timestamp,
                window_end_time=window_end_timestamp,
                pod_ip=pod_ip,
                pod_name=hit_rows[0].pod_name if hit_rows else None,
                thread_id=thread_id,
                interface_hits=interface_hits,
            ),
            failure_modes=failures,
            failure_graph=BrpcDiagnosisService._build_failure_graph(
                schema,
                failure_rows,
            ),
            hit_total=hit_total,
            hits=[BrpcDiagHitLog.model_validate(row) for row in hit_rows],
        )

    @staticmethod
    async def list_abnormal_threads(
        *,
        batch_id: str,
        start_timestamp: int,
        end_timestamp: int,
        page_num: int,
        page_cnt: int,
        pod_ip: str | None = None,
        pod_name: str | None = None,
        search: str | None = None,
        metric_sort_fields: list[BrpcMetricSortField] | None = None,
    ) -> ListBrpcAbnormalThreadsMsg:
        BrpcDiagnosisService._validate_timestamp_range(
            start_timestamp,
            end_timestamp,
        )
        async with PGManager.session() as session:
            await BrpcDiagnosisService._require_batch(session, batch_id)
            total, rows = await BrpcDiagnosisPGManager.list_abnormal_threads(
                session,
                batch_id=batch_id,
                start_timestamp=start_timestamp,
                end_timestamp=end_timestamp,
                page_num=page_num,
                page_cnt=page_cnt,
                pod_ip=pod_ip,
                pod_name=pod_name,
                search=search,
                metric_sort_fields=metric_sort_fields or [],
            )
        threads = [
            BrpcDiagnosisService._abnormal_thread_from_row(batch_id, row)
            for row in rows
        ]
        return ListBrpcAbnormalThreadsMsg(
            batch_id=batch_id,
            total=total,
            threads=threads,
        )

    @staticmethod
    def _abnormal_thread_from_row(
        batch_id: str,
        row: dict,
    ) -> BrpcAbnormalThread:
        pod_ip = str(row["pod_ip"])
        thread_id = int(row["thread_id"])
        return BrpcAbnormalThread(
            thread_key=BrpcDiagnosisService.thread_key(
                batch_id,
                pod_ip,
                thread_id,
            ),
            batch_id=batch_id,
            pod_ip=pod_ip,
            pod_name=row.get("pod_name"),
            thread_id=thread_id,
            first_hit_time=int(row["first_hit_timestamp"]),
            last_hit_time=int(row["last_hit_timestamp"]),
            total_interface_hit_count=int(row["total_interface_hit_count"]),
            interface_hits=BrpcDiagnosisService._decode_interface_hits(
                row.get("interface_hits")
            ),
        )

    @staticmethod
    async def get_abnormal_thread_detail(
        *,
        thread_key: str,
        batch_id: str,
        pod_ip: str,
        thread_id: int,
        start_timestamp: int,
        end_timestamp: int,
        window_size: BrpcWindowSize,
        page_num: int,
        page_cnt: int,
        pod_name: str | None = None,
    ) -> GetBrpcAbnormalThreadDetailMsg:
        BrpcDiagnosisService._validate_timestamp_range(
            start_timestamp,
            end_timestamp,
        )
        expected_key = BrpcDiagnosisService.thread_key(
            batch_id,
            pod_ip,
            thread_id,
        )
        if thread_key != expected_key:
            raise BadRequestBizException(
                message="thread_key 与 Thread 分组键不匹配"
            )
        window_us = WINDOW_SIZE_US[window_size]
        first_window_timestamp = (start_timestamp // window_us) * window_us
        window_count = (
            end_timestamp - first_window_timestamp + window_us - 1
        ) // window_us
        if window_count > MAX_TIMELINE_WINDOWS:
            raise BadRequestBizException(
                message="查询时间范围过大，请增大 window_size 或缩小时间范围"
            )
        async with PGManager.session() as session:
            batch = await BrpcDiagnosisService._require_batch(session, batch_id)
            _, summaries = await BrpcDiagnosisPGManager.list_abnormal_threads(
                session,
                batch_id=batch_id,
                start_timestamp=start_timestamp,
                end_timestamp=end_timestamp,
                page_num=1,
                page_cnt=1,
                pod_ip=pod_ip,
                pod_name=pod_name,
                thread_id=thread_id,
            )
            timeline_rows = (
                await BrpcDiagnosisPGManager.get_interface_timeline_aggregates(
                    session,
                    batch_id=batch_id,
                    start_timestamp=start_timestamp,
                    end_timestamp=end_timestamp,
                    window_us=window_us,
                    pod_ip=pod_ip,
                    pod_name=pod_name,
                    thread_id=thread_id,
                )
            )
            failure_rows = (
                await BrpcDiagnosisPGManager.get_failure_mode_hit_counts(
                    session,
                    batch_id=batch_id,
                    start_timestamp=start_timestamp,
                    end_timestamp=end_timestamp,
                    pod_ip=pod_ip,
                    pod_name=pod_name,
                    thread_id=thread_id,
                )
            )
            hit_total, hit_rows = await BrpcDiagnosisPGManager.list_hits(
                session,
                batch_id=batch_id,
                page_num=page_num,
                page_cnt=page_cnt,
                start_timestamp=start_timestamp,
                end_timestamp=end_timestamp,
                pod_ip=pod_ip,
                pod_name=pod_name,
                thread_id=thread_id,
            )
            schema = await BrpcDiagnosisPGManager.get_schema(
                session,
                batch.schema_id,
            )
        if not summaries or not failure_rows or schema is None:
            raise NotFoundBizException(resource="BRPC 异常 Thread")
        return GetBrpcAbnormalThreadDetailMsg(
            thread=BrpcDiagnosisService._abnormal_thread_from_row(
                batch_id,
                summaries[0],
            ),
            start_time=start_timestamp,
            end_time=end_timestamp,
            window_size=window_size,
            interface_timeline=BrpcDiagnosisService._zero_fill_timeline(
                aggregates=timeline_rows,
                first_window_timestamp=first_window_timestamp,
                end_timestamp=end_timestamp,
                window_us=window_us,
            ),
            failure_modes=BrpcDiagnosisService._failure_mode_hits(failure_rows),
            failure_graph=BrpcDiagnosisService._build_failure_graph(
                schema,
                failure_rows,
            ),
            hit_total=hit_total,
            hits=[BrpcDiagHitLog.model_validate(row) for row in hit_rows],
        )

    @staticmethod
    def _build_failure_graph(
        schema: BrpcDiagSchema,
        failure_rows: list[dict],
    ) -> BrpcFailureGraph:
        hit_counts = {
            str(row["failure_mode_id"]): int(row["hit_count"])
            for row in failure_rows
        }
        directly_hit = set(hit_counts)
        resolved_interfaces_by_failure = {
            str(row["failure_mode_id"]): {
                str(interface_id)
                for interface_id in row.get("interface_ids") or []
                if interface_id is not None
            }
            for row in failure_rows
        }
        mappings_by_failure = {
            mapping.failure_mode_id: mapping
            for mapping in schema.failure_interface_mappings
        }
        # Retain interfaces for each directly-hit failure mode.  When the
        # diagnosis engine uniquely attributed the hit to an interface, only
        # that resolved interface is kept.  When the hit is unresolved
        # (interface_id=NULL, e.g. singleton hit with multiple candidates and
        # no cross-component anchor), ALL candidate interfaces from the schema
        # mapping are kept so the failure mode always has an interface root —
        # never a standalone rootless failure-mode node.  Edges remain strictly
        # schema-backed; do not synthesize interface-to-failure links.
        retained = set(directly_hit)
        for failure_mode_id in directly_hit:
            mapping = mappings_by_failure[failure_mode_id]
            resolved_interface_ids = resolved_interfaces_by_failure.get(
                failure_mode_id, set()
            ).intersection(mapping.interface_ids)
            if resolved_interface_ids:
                retained.update(resolved_interface_ids)
            else:
                retained.update(mapping.interface_ids)
        # Bridge cross-component interface endpoints that lie on a schema path
        # between two retained nodes. Without this, a per-Thread graph whose
        # hits span UBSocket -> UMQ -> URMA splits into one island per
        # component because the bridge interface (e.g. umq_070) is neither
        # directly hit nor a resolved interface, so the cross-component edges
        # touching it get pruned for lacking a retained endpoint. The rule is
        # symmetric: a non-retained interface is added only when it is both
        # forward-reachable from a retained node AND can still reach another
        # retained node via cross-component edges. Failure modes are never
        # added this way — they must still be directly hit to appear.
        node_type_by_id = {node.node_id: node.node_type for node in schema.nodes}
        cross_out: dict[str, list[str]] = {}
        cross_in: dict[str, list[str]] = {}
        for edge in schema.edges:
            if edge.edge_type != "cross_component":
                continue
            cross_out.setdefault(edge.source_node_id, []).append(edge.target_node_id)
            cross_in.setdefault(edge.target_node_id, []).append(edge.source_node_id)
        forward_reachable = set(retained)
        pending_forward = list(retained)
        while pending_forward:
            current = pending_forward.pop()
            for nxt in cross_out.get(current, ()):
                if nxt not in forward_reachable:
                    forward_reachable.add(nxt)
                    pending_forward.append(nxt)
        backward_reachable = set(retained)
        pending_backward = list(retained)
        while pending_backward:
            current = pending_backward.pop()
            for prev in cross_in.get(current, ()):
                if prev not in backward_reachable:
                    backward_reachable.add(prev)
                    pending_backward.append(prev)
        bridges = {
            node_id
            for node_id in forward_reachable & backward_reachable
            if node_id not in retained and node_type_by_id.get(node_id) == "interface"
        }
        retained.update(bridges)
        nodes = [
            BrpcFailureGraphNode(
                **node.model_dump(),
                directly_hit=node.node_id in directly_hit,
                hit_count=(
                    hit_counts.get(node.node_id, 0)
                    if node.node_type == "failure_mode"
                    else 0
                ),
            )
            for node in sorted(schema.nodes, key=lambda item: item.node_id)
            if node.node_id in retained
        ]
        edges = [
            edge
            for edge in sorted(
                schema.edges,
                key=lambda item: (
                    item.source_node_id,
                    item.target_node_id,
                    item.edge_type,
                ),
            )
            if edge.source_node_id in retained
            and edge.target_node_id in retained
        ]
        # Suppress shortcut edges: if edge X→Y coexists with a longer path
        # X→…→Y through other retained nodes, the direct edge is a schema
        # shortcut that visually duplicates the real causal chain.  Remove
        # it so the graph shows a single coherent path instead of parallel
        # arcs that make the view look disconnected.
        forward_adj: dict[str, list[str]] = {}
        reverse_adj: dict[str, list[str]] = {}
        for edge in edges:
            forward_adj.setdefault(edge.source_node_id, []).append(
                edge.target_node_id
            )
            reverse_adj.setdefault(edge.target_node_id, []).append(
                edge.source_node_id
            )

        def _has_alternative_path(source: str, target: str) -> bool:
            """True if `target` is reachable from `source` via a path of
            length ≥ 2 (excluding the direct edge)."""
            other_parents = [
                p for p in reverse_adj.get(target, []) if p != source
            ]
            if not other_parents:
                return False
            visited = {source}
            queue = [source]
            while queue:
                node = queue.pop(0)
                for nxt in forward_adj.get(node, []):
                    if node == source and nxt == target:
                        continue
                    if nxt in other_parents:
                        return True
                    if nxt not in visited:
                        visited.add(nxt)
                        queue.append(nxt)
            return False

        edges = [
            edge
            for edge in edges
            if not _has_alternative_path(
                edge.source_node_id, edge.target_node_id
            )
        ]
        return BrpcFailureGraph(nodes=nodes, edges=edges)

    @staticmethod
    def _zero_fill_timeline(
        *,
        aggregates: list[dict],
        first_window_timestamp: int,
        end_timestamp: int,
        window_us: int,
    ) -> list[BrpcInterfaceTimelineSeries]:
        counts_by_series: dict[
            tuple[str, str, str, str], dict[int, int]
        ] = defaultdict(dict)
        for row in aggregates:
            series_key = (
                str(row["component"]),
                str(row["interface_id"]),
                str(row["interface_name"]),
                str(row["function_name"]),
            )
            counts_by_series[series_key][int(row["window_start_timestamp"])] = int(
                row["interface_hit_count"]
            )

        window_start_timestamps = range(
            first_window_timestamp,
            end_timestamp,
            window_us,
        )
        series: list[BrpcInterfaceTimelineSeries] = []
        for (
            component,
            interface_id,
            interface_name,
            function_name,
        ), counts in sorted(counts_by_series.items()):
            series.append(
                BrpcInterfaceTimelineSeries(
                    component=component,
                    interface_id=interface_id,
                    interface_name=interface_name,
                    function_name=function_name,
                    points=[
                        BrpcInterfaceTimelinePoint(
                            window_start_time=window_start_timestamp,
                            window_end_time=window_start_timestamp + window_us,
                            interface_hit_count=counts.get(window_start_timestamp, 0),
                        )
                        for window_start_timestamp in window_start_timestamps
                    ],
                )
            )
        return series
