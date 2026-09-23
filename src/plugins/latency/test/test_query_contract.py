"""跨接口查询契约测试（trace 明细 / 故障事件 / 时间窗聚合）。

覆盖：
- 半开时间窗 ``[start_time, end_time)``：起点恰为 ``end_time`` 的行/桶不入窗
  （相邻桶边界不重复计数）；主列表、轻量投影、时延曲线与各统计接口同契约；
- ``endpoint_ip`` OR 语义（``src_ip = ip OR dst_ip = ip``）：主列表与轻量
  投影一致，total 与分页正确；
- ``log_id`` 收窄：同 trace_id 跨日志不串数据；时间桶、IP 对计数与阶段均值
  随 log_id 同步收窄；
- 组合过滤（operation + 时间窗 + endpoint_ip + 分页）。

需要 PostgreSQL 实例（与 test_postgresql_integration.py 相同）：

    postgresql://postgres:postgres@127.0.0.1:15432/latency_test

可用 LATENCY_PG_DSN 覆盖。
"""
from __future__ import annotations

import os
import uuid
from datetime import datetime

import pytest
from latency.database.engine import PGManager
from latency.database.init import init_postgresql_database
from latency.database.managers.log_failure_event import LogFailureEventPGManager
from latency.database.managers.log_file import LogFilePGManager
from latency.database.managers.log_knowledge import LogKnowledgePGManager
from latency.database.managers.log_parse_result import LogParseResultPGManager
from latency.database.managers.time_window_aggregated_event import (
    TimeWindowAggregatedEventPGManager,
)
from latency.database.managers.trace_light import TraceLightPGManager
from latency.schemas.log import (
    LogFileModel,
    LogKnowledgeModel,
    LogParseResultDataclass,
    TimeWindowAggregatedEventDataclass,
)
from latency.schemas.request import (
    ListLogFailureEventResultRequest,
    ListLogParseResultRequest,
    ListTimeWindowAggregatedEventRequest,
    ListTraceFailureEventResultRequest,
)
from sqlalchemy import text

PG_DSN = os.getenv(
    "LATENCY_PG_DSN",
    "postgresql://postgres:postgres@127.0.0.1:15432/latency_test",
)

DAY = "2026-01-01"


async def _setup_kb() -> tuple[str, str]:
    await init_postgresql_database()
    kb_id = f"kb-contract-{uuid.uuid4().hex[:8]}"
    log_id = f"log-contract-{uuid.uuid4().hex[:8]}"
    await LogKnowledgePGManager.add_log_kb(
        LogKnowledgeModel(id=kb_id, name=f"contract_{kb_id}", description="query contract test")
    )
    await LogFilePGManager.add_log_file(
        LogFileModel(id=log_id, kb_id=kb_id, name="contract.log", file_path="/tmp/contract.log", file_size=1)
    )
    return kb_id, log_id


@pytest.mark.asyncio
async def test_time_window_half_open_boundary():
    """前一桶不得包含后一桶起点：end_time=10:03:00 排除 10:03:00 桶。"""
    PGManager.initialize(PG_DSN)
    try:
        kb_id, log_id = await _setup_kb()

        def bucket_event(suffix: str, bucket: str, ave: float, p99: float):
            return TimeWindowAggregatedEventDataclass(
                id=f"{log_id}-tw-{suffix}",
                kb_id=kb_id,
                log_id=log_id,
                time_bucket=bucket,
                src_ip="10.0.0.1",
                dst_ip="10.0.0.2",
                operation="SET",
                log_parse_result_cnt=10,
                anomaly_cnt=3,
                ave_total_latency=ave,
                latency_sum=ave * 10,
                p99_total_latency=p99,
            )

        await TimeWindowAggregatedEventPGManager.add_events(
            [
                bucket_event("a", f"{DAY} 10:02:50", 5.0, 6.0),
                bucket_event("b", f"{DAY} 10:03:00", 7.0, 8.0),
            ]
        )

        req = ListTimeWindowAggregatedEventRequest(
            kb_id=kb_id,
            interval=10,
            page_cnt=100,
            start_time=f"{DAY} 10:02:50",
            end_time=f"{DAY} 10:03:00",
        )
        total, rows = await TimeWindowAggregatedEventPGManager.list_time_window_events(req)
        assert total == 1
        assert rows[0]["start_time"] == f"{DAY} 10:02:50"
        assert rows[0]["end_time"] == f"{DAY} 10:03:00"
        assert rows[0]["total_cnt"] == 10

        # 不带 end_time 时两个桶都在
        req = ListTimeWindowAggregatedEventRequest(kb_id=kb_id, interval=10, page_cnt=100)
        total, _ = await TimeWindowAggregatedEventPGManager.list_time_window_events(req)
        assert total == 2
    finally:
        await PGManager.close()


@pytest.mark.asyncio
async def test_time_window_breakdown_and_realtime_query_exclude_end_boundary():
    """阶段均值与实时聚合在同一粗桶内也必须排除 end_time 边界。"""
    PGManager.initialize(PG_DSN)
    try:
        kb_id, log_id = await _setup_kb()
        await TimeWindowAggregatedEventPGManager.add_events(
            [
                TimeWindowAggregatedEventDataclass(
                    id=f"{log_id}-tw-stage",
                    kb_id=kb_id,
                    log_id=log_id,
                    time_bucket=f"{DAY} 10:02:50",
                    src_ip="10.0.1.1",
                    dst_ip="10.0.1.2",
                    operation="GET",
                    log_parse_result_cnt=2,
                    anomaly_cnt=1,
                    ave_total_latency=5.0,
                    latency_sum=10.0,
                    p99_total_latency=6.0,
                )
            ]
        )
        await LogParseResultPGManager.add_log_parse_results(
            [
                LogParseResultDataclass(
                    id=f"{log_id}-stage-in",
                    log_id=log_id,
                    trace_id="stage-in",
                    timestamp=f"{DAY} 10:02:54",
                    src_ip="10.0.1.1",
                    dst_ip="10.0.1.2",
                    operation="GET",
                    total_latency=5.0,
                    sdk_processing_us=100.0,
                    is_anomalous=True,
                    created_at=f"{DAY} 10:02:54",
                ),
                LogParseResultDataclass(
                    id=f"{log_id}-stage-boundary",
                    log_id=log_id,
                    trace_id="stage-boundary",
                    timestamp=f"{DAY} 10:02:55",
                    src_ip="10.0.1.1",
                    dst_ip="10.0.1.2",
                    operation="GET",
                    total_latency=5.0,
                    sdk_processing_us=900.0,
                    is_anomalous=True,
                    created_at=f"{DAY} 10:02:55",
                ),
            ]
        )

        req = ListTimeWindowAggregatedEventRequest(
            kb_id=kb_id,
            interval=10,
            page_cnt=100,
            start_time=f"{DAY} 10:02:50",
            end_time=f"{DAY} 10:02:55",
            operation="GET",
        )
        total, rows = await TimeWindowAggregatedEventPGManager.list_time_window_events(req)
        assert total == 1
        assert rows[0]["ip_pairs"][0]["p99_sdk_processing_us"] == pytest.approx(100.0)

        realtime_rows = await TimeWindowAggregatedEventPGManager.get_time_window_events(
            log_id,
            kb_id=kb_id,
            start_time=f"{DAY} 10:02:50",
            end_time=f"{DAY} 10:02:55",
            operation="GET",
        )
        assert len(realtime_rows) == 1
        assert realtime_rows[0]["ave_sdk_processing_us"] == pytest.approx(100.0)
    finally:
        await PGManager.close()


@pytest.mark.asyncio
async def test_latency_trace_half_open_boundary_and_endpoint_ip():
    """时延 Trace：半开区间边界 + endpoint_ip OR 语义 + 分页 total。"""
    PGManager.initialize(PG_DSN)
    try:
        kb_id, log_id = await _setup_kb()

        def trace(tid: str, ts: str, src: str, dst: str, op: str = "DS_KV_CLIENT_SET", anomalous: bool = True):
            return LogParseResultDataclass(
                id=f"{log_id}-{tid}",
                log_id=log_id,
                trace_id=tid,
                timestamp=ts,
                src_ip=src,
                dst_ip=dst,
                operation=op,
                total_latency=10.0,
                is_anomalous=anomalous,
                created_at=ts,
            )

        await LogParseResultPGManager.add_log_parse_results(
            [
                # 窗内：src 命中 endpoint_ip
                trace("t1", f"{DAY} 10:02:59", "10.0.0.10", "10.0.0.20"),
                # 窗内：dst 命中 endpoint_ip（OR 的另一侧）
                trace("t2", f"{DAY} 10:02:30", "10.0.0.30", "10.0.0.10"),
                # 窗内但不命中 endpoint_ip
                trace("t3", f"{DAY} 10:02:40", "10.0.0.40", "10.0.0.50"),
                # 恰好位于 end_time 边界：必须被排除
                trace("t4", f"{DAY} 10:03:00", "10.0.0.10", "10.0.0.20"),
                # 窗外（GET）
                trace("t5", f"{DAY} 10:02:45", "10.0.0.10", "10.0.0.20", op="SDK_GET"),
            ]
        )

        # 半开区间 + endpoint_ip：只有 t1/t2
        req = ListLogParseResultRequest(
            kb_id=kb_id,
            is_anomalous=True,
            operation="SET",
            start_time=f"{DAY} 10:02:00",
            end_time=f"{DAY} 10:03:00",
            endpoint_ip="10.0.0.10",
            page_cnt=10,
            page_num=1,
        )
        total, rows = await LogParseResultPGManager.list_log_parse_results(req)
        assert total == 2
        assert sorted(r.trace_id for r in rows) == ["t1", "t2"]

        # 分页正确：page_cnt=1 page_num=2 返回第二条
        req.page_cnt = 1
        req.page_num = 2
        total, rows = await LogParseResultPGManager.list_log_parse_results(req)
        assert total == 2
        assert len(rows) == 1
        assert rows[0].trace_id in ("t1", "t2")

        # src_ip/dst_ip 与 endpoint_ip 组合过滤
        req.page_cnt = 10
        req.page_num = 1
        req.src_ip = "10.0.0.30"
        total, rows = await LogParseResultPGManager.list_log_parse_results(req)
        assert total == 1
        assert rows[0].trace_id == "t2"

        # 不带 endpoint_ip：SET + 窗内 = t1/t2/t3（t4 在边界被排除）
        req.src_ip = None
        req.endpoint_ip = None
        total, rows = await LogParseResultPGManager.list_log_parse_results(req)
        assert total == 3
        assert sorted(str(r.trace_id) for r in rows) == ["t1", "t2", "t3"]
    finally:
        await PGManager.close()


@pytest.mark.asyncio
async def test_light_projection_matches_main_list_contract():
    """轻量投影与主列表同契约：半开窗排除 end 边界，endpoint_ip OR 语义一致。"""
    PGManager.initialize(PG_DSN)
    try:
        kb_id, log_id = await _setup_kb()

        def trace(tid: str, ts: str, src: str, dst: str, op: str = "DS_KV_CLIENT_SET"):
            return LogParseResultDataclass(
                id=f"{log_id}-{tid}",
                log_id=log_id,
                trace_id=tid,
                timestamp=ts,
                src_ip=src,
                dst_ip=dst,
                operation=op,
                total_latency=10.0,
                is_anomalous=True,
                created_at=ts,
            )

        await LogParseResultPGManager.add_log_parse_results(
            [
                # 窗内：src 命中 endpoint_ip
                trace("t1", f"{DAY} 10:02:59", "10.0.0.10", "10.0.0.20"),
                # 窗内：dst 命中 endpoint_ip（OR 的另一侧）
                trace("t2", f"{DAY} 10:02:30", "10.0.0.30", "10.0.0.10"),
                # 窗内但不命中 endpoint_ip
                trace("t3", f"{DAY} 10:02:40", "10.0.0.40", "10.0.0.50"),
                # 恰好位于 end_time 边界：主列表与轻量投影都必须排除
                trace("t4", f"{DAY} 10:03:00", "10.0.0.10", "10.0.0.20"),
            ]
        )

        req = ListLogParseResultRequest(
            kb_id=kb_id,
            is_anomalous=True,
            operation="SET",
            start_time=f"{DAY} 10:02:00",
            end_time=f"{DAY} 10:03:00",
            endpoint_ip="10.0.0.10",
            page_cnt=10,
            page_num=1,
        )
        main_total, main_rows = await LogParseResultPGManager.list_log_parse_results(req)
        light_total, light_rows = await TraceLightPGManager.list_latency_projection(req)
        assert main_total == light_total == 2
        assert sorted(str(r.trace_id) for r in main_rows) == ["t1", "t2"]
        assert sorted(r.trace_id for r in light_rows) == ["t1", "t2"]
    finally:
        await PGManager.close()


@pytest.mark.asyncio
async def test_connectivity_trace_endpoint_ip_and_half_open():
    """通断 Trace：endpoint_ip OR 语义 + 半开区间 + 分页 total。"""
    PGManager.initialize(PG_DSN)
    try:
        kb_id, log_id = await _setup_kb()

        rows = [
            # (id, trace_id, timestamp, src, dst)
            (f"{log_id}-c1", "ft1", f"{DAY} 10:02:59", "10.1.0.10", "10.1.0.20"),
            (f"{log_id}-c2", "ft2", f"{DAY} 10:02:30", "10.1.0.30", "10.1.0.10"),
            (f"{log_id}-c3", "ft3", f"{DAY} 10:02:40", "10.1.0.40", "10.1.0.50"),
            (f"{log_id}-c4", "ft4", f"{DAY} 10:03:00", "10.1.0.10", "10.1.0.20"),
        ]
        async with PGManager.connection() as conn:
            for rid, tid, ts, src, dst in rows:
                await conn.execute(
                    text(
                        "INSERT INTO trace_failure_event "
                        "(id, log_id, trace_id, pod_names, src_ip, dst_ip, host_names, "
                        "cluster_names, timestamp, status_code, failure_mode, operation) "
                        "VALUES (:id, :log_id, :trace_id, :pod_names, :src_ip, :dst_ip, "
                        ":host_names, :cluster_names, :timestamp, :status_code, "
                        ":failure_mode, :operation)"
                    ),
                    {
                        "id": rid,
                        "log_id": log_id,
                        "trace_id": tid,
                        "pod_names": [f"pod-{rid}"],
                        "src_ip": src,
                        "dst_ip": dst,
                        "host_names": ["host-a"],
                        "cluster_names": ["cluster-a"],
                        "timestamp": datetime.strptime(ts, "%Y-%m-%d %H:%M:%S"),
                        "status_code": ["1"],
                        "failure_mode": "fm-test",
                        "operation": "SET",
                    },
                )

        req = ListTraceFailureEventResultRequest(
            kb_id=kb_id,
            is_anomalous=True,
            operation="SET",
            start_time=f"{DAY} 10:02:00",
            end_time=f"{DAY} 10:03:00",
            endpoint_ip="10.1.0.10",
            page_cnt=10,
            page_num=1,
        )
        total, events = await LogFailureEventPGManager.list_trace_failure_events(req)
        assert total == 2
        assert sorted(e.trace_id for e in events) == ["ft1", "ft2"]

        req.page_cnt = 1
        req.page_num = 2
        total, events = await LogFailureEventPGManager.list_trace_failure_events(req)
        assert total == 2
        assert len(events) == 1
    finally:
        await PGManager.close()


@pytest.mark.asyncio
async def test_trace_detail_queries_are_strictly_isolated_by_log_id():
    """相同 trace_id 出现在两个日志时，抽屉补充查询不得跨日志串数据。"""
    PGManager.initialize(PG_DSN)
    try:
        kb_id, first_log_id = await _setup_kb()
        second_log_id = f"log-second-{uuid.uuid4().hex[:8]}"
        await LogFilePGManager.add_log_file(
            LogFileModel(
                id=second_log_id,
                kb_id=kb_id,
                name="second.log",
                file_path="/tmp/second.log",
                file_size=1,
            )
        )
        shared_trace_id = f"shared-{uuid.uuid4().hex[:8]}"
        await LogFailureEventPGManager.add_trace_failure_event_raw(
            [
                {
                    "log_id": first_log_id,
                    "trace_id": shared_trace_id,
                    "timestamp": f"{DAY} 10:00:01",
                    "pod_names": [],
                    "host_names": [],
                    "cluster_names": [],
                    "failure_mode": ["fm-first"],
                },
                {
                    "log_id": second_log_id,
                    "trace_id": shared_trace_id,
                    "timestamp": f"{DAY} 10:00:02",
                    "pod_names": [],
                    "host_names": [],
                    "cluster_names": [],
                    "failure_mode": ["fm-second"],
                },
            ]
        )
        await LogFailureEventPGManager.add_log_failure_event_raw(
            [
                {
                    "log_id": first_log_id,
                    "trace_id": shared_trace_id,
                    "timestamp": f"{DAY} 10:00:01",
                    "raw_text": "first-log-only",
                },
                {
                    "log_id": second_log_id,
                    "trace_id": shared_trace_id,
                    "timestamp": f"{DAY} 10:00:02",
                    "raw_text": "second-log-only",
                },
            ]
        )

        trace_req = ListTraceFailureEventResultRequest(
            kb_id=kb_id,
            log_id=first_log_id,
            trace_ids=[shared_trace_id],
            page_cnt=10,
        )
        total, trace_events = await LogFailureEventPGManager.list_trace_failure_events(
            trace_req
        )
        assert total == 1
        assert [event.log_id for event in trace_events] == [first_log_id]
        assert trace_events[0].failure_mode == ["fm-first"]

        log_req = ListLogFailureEventResultRequest(
            kb_id=kb_id,
            log_id=first_log_id,
            trace_ids=[shared_trace_id],
        )
        total, log_events = await LogFailureEventPGManager.list_log_failure_events(
            log_req
        )
        assert total == 1
        assert [event.log_id for event in log_events] == [first_log_id]
        assert log_events[0].raw_text == "first-log-only"
    finally:
        await PGManager.close()


@pytest.mark.asyncio
async def test_latency_trace_time_window_matches_ip_pair_window():
    """时间窗接口的 IP 对窗口与 Trace 接口窗口一致：相邻桶不串。"""
    PGManager.initialize(PG_DSN)
    try:
        kb_id, log_id = await _setup_kb()
        await TimeWindowAggregatedEventPGManager.add_events(
            [
                TimeWindowAggregatedEventDataclass(
                    id=f"{log_id}-tw-win",
                    kb_id=kb_id,
                    log_id=log_id,
                    time_bucket=f"{DAY} 11:00:00",
                    src_ip="10.2.0.1",
                    dst_ip="10.2.0.2",
                    operation="GET",
                    log_parse_result_cnt=4,
                    anomaly_cnt=2,
                    ave_total_latency=3.0,
                    latency_sum=12.0,
                    p99_total_latency=4.0,
                ),
                TimeWindowAggregatedEventDataclass(
                    id=f"{log_id}-tw-next",
                    kb_id=kb_id,
                    log_id=log_id,
                    time_bucket=f"{DAY} 11:01:00",
                    src_ip="10.2.0.1",
                    dst_ip="10.2.0.2",
                    operation="GET",
                    log_parse_result_cnt=4,
                    anomaly_cnt=2,
                    ave_total_latency=3.0,
                    latency_sum=12.0,
                    p99_total_latency=4.0,
                ),
            ]
        )
        await LogParseResultPGManager.add_log_parse_results(
            [
                LogParseResultDataclass(
                    id=f"{log_id}-w{i}",
                    log_id=log_id,
                    trace_id=f"wt{i}",
                    timestamp=f"{DAY} 11:00:{i * 10:02d}",
                    src_ip="10.2.0.1",
                    dst_ip="10.2.0.2",
                    operation="GET",
                    total_latency=3.0,
                    is_anomalous=True,
                    created_at=f"{DAY} 11:00:{i * 10:02d}",
                )
                for i in range(6)
            ]
        )

        req = ListTimeWindowAggregatedEventRequest(
            kb_id=kb_id,
            interval=60,
            page_cnt=100,
            start_time=f"{DAY} 11:00:00",
            end_time=f"{DAY} 11:01:00",
        )
        total, rows = await TimeWindowAggregatedEventPGManager.list_time_window_events(req)
        assert total == 1
        assert rows[0]["anomaly_cnt"] == 2
        assert rows[0]["ip_pairs"][0]["anomaly_cnt"] == 2

        trace_req = ListLogParseResultRequest(
            kb_id=kb_id,
            is_anomalous=True,
            operation="GET",
            start_time=f"{DAY} 11:00:00",
            end_time=f"{DAY} 11:01:00",
            src_ip="10.2.0.1",
            dst_ip="10.2.0.2",
            page_cnt=100,
            page_num=1,
        )
        trace_total, traces = await LogParseResultPGManager.list_log_parse_results(trace_req)
        assert trace_total == 6
        assert all(str(t.timestamp).startswith(f"{DAY} 11:00:") for t in traces)
    finally:
        await PGManager.close()


@pytest.mark.asyncio
async def test_log_id_scopes_time_window_and_breakdown():
    """log_id 同时收窄时间桶、IP 对计数与阶段均值，而非只影响明细均值。"""
    PGManager.initialize(PG_DSN)
    try:
        kb_id, log_a = await _setup_kb()
        log_b = f"log-b-{uuid.uuid4().hex[:8]}"
        await LogFilePGManager.add_log_file(
            LogFileModel(id=log_b, kb_id=kb_id, name="contract-b.log", file_path="/tmp/contract-b.log", file_size=1)
        )

        def bucket(suffix: str, log_id: str, bucket_time: str, src: str, anomaly: int):
            return TimeWindowAggregatedEventDataclass(
                id=f"{log_id}-tw-{suffix}",
                kb_id=kb_id,
                log_id=log_id,
                time_bucket=bucket_time,
                src_ip=src,
                dst_ip="10.9.0.2",
                operation="GET",
                log_parse_result_cnt=4,
                anomaly_cnt=anomaly,
                ave_total_latency=3.0,
                latency_sum=12.0,
                p99_total_latency=4.0,
            )

        await TimeWindowAggregatedEventPGManager.add_events(
            [
                bucket("tw-a1", log_a, f"{DAY} 12:00:00", "10.9.0.1", 2),
                bucket("tw-a2", log_a, f"{DAY} 12:01:00", "10.9.0.1", 2),
                bucket("tw-b1", log_b, f"{DAY} 12:00:00", "10.9.0.3", 5),
            ]
        )
        await LogParseResultPGManager.add_log_parse_results(
            [
                LogParseResultDataclass(
                    id=f"{log_a}-w1",
                    log_id=log_a,
                    trace_id="la1",
                    timestamp=f"{DAY} 12:00:10",
                    src_ip="10.9.0.1",
                    dst_ip="10.9.0.2",
                    operation="GET",
                    total_latency=3.0,
                    is_anomalous=True,
                    created_at=f"{DAY} 12:00:10",
                ),
                LogParseResultDataclass(
                    id=f"{log_b}-w1",
                    log_id=log_b,
                    trace_id="lb1",
                    timestamp=f"{DAY} 12:00:20",
                    src_ip="10.9.0.3",
                    dst_ip="10.9.0.2",
                    operation="GET",
                    total_latency=9.0,
                    is_anomalous=True,
                    created_at=f"{DAY} 12:00:20",
                ),
            ]
        )

        # 不带 log_id：两个日志的桶都返回（异常合计 2+2+5）
        req = ListTimeWindowAggregatedEventRequest(kb_id=kb_id, interval=60, page_cnt=100)
        total, rows = await TimeWindowAggregatedEventPGManager.list_time_window_events(req)
        assert total == 2
        assert sum(r["anomaly_cnt"] for r in rows) == 9

        # 带 log_id=log_a：只剩 log_a 的桶（12:00/12:01）与 IP 对
        req.log_id = log_a
        total, rows = await TimeWindowAggregatedEventPGManager.list_time_window_events(req)
        assert total == 2
        assert [r["start_time"] for r in rows] == [f"{DAY} 12:00:00", f"{DAY} 12:01:00"]
        assert sum(r["anomaly_cnt"] for r in rows) == 4
        first = next(r for r in rows if r["start_time"] == f"{DAY} 12:00:00")
        assert [(p["src_ip"], p["dst_ip"]) for p in first["ip_pairs"]] == [
            ("10.9.0.1", "10.9.0.2")
        ]
        # 阶段均值补齐同样只统计 log_a 的 trace（3.0 而非混入 log_b 的 9.0）
        assert first["ip_pairs"][0]["ave_total_latency"] == pytest.approx(3.0)

        # log_parse_result/list 的 log_id 收窄保持一致
        trace_req = ListLogParseResultRequest(
            kb_id=kb_id,
            log_id=log_a,
            is_anomalous=True,
            operation="GET",
            page_cnt=100,
            page_num=1,
        )
        trace_total, _ = await LogParseResultPGManager.list_log_parse_results(trace_req)
        assert trace_total == 1
    finally:
        await PGManager.close()
