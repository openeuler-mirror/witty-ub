"""PostgreSQL integration tests.

Requires a running PostgreSQL instance. By default it targets the container
started for this project:

    postgresql://postgres:postgres@127.0.0.1:15432/latency_test

Set LATENCY_PG_DSN to override.
"""
from __future__ import annotations

import os
from datetime import datetime, timedelta

import pytest
from sqlalchemy import text

from latency.database.engine import PGManager
from latency.database.init import (
    backfill_trace_failure_event_status_codes,
    init_postgresql_database,
)
from latency.database.managers.log_parse_result import LogParseResultPGManager
from latency.database.managers.src_dst_aggregated_event import (
    SrcDstAggregatedEventPGManager,
)
from latency.database.managers.time_window_aggregated_event import (
    TimeWindowAggregatedEventPGManager,
)
from latency.schemas.log import (
    LogParseResultDataclass,
    SrcDstAggregatedEventDataclass,
    TimeWindowAggregatedEventDataclass,
)
from latency.schemas.request import (
    ListSrcDstAggregatedEventRequest,
    ListTimeWindowAggregatedEventRequest,
)
from latency.database.models import LogParseResult


PG_DSN = os.getenv(
    "LATENCY_PG_DSN",
    "postgresql://postgres:postgres@127.0.0.1:15432/latency_test",
)


@pytest.mark.asyncio
async def _truncate_log_parse_result():
    async with PGManager.connection() as conn:
        await conn.execute(text("TRUNCATE TABLE log_parse_result CASCADE"))


@pytest.mark.asyncio
async def test_backfill_trace_failure_event_status_codes_uses_varchar_array():
    PGManager.initialize(PG_DSN)
    access_failure_mode_id = "pg-test-access-status-code-mode"
    runtime_failure_mode_id = "pg-test-runtime-status-code-mode"
    trace_event_id = "pg-test-status-code-trace"
    access_log_event_id = "pg-test-status-code-access-log"
    runtime_log_event_id = "pg-test-status-code-runtime-log"
    database_ready = False
    try:
        await init_postgresql_database()
        database_ready = True
        async with PGManager.engine().begin() as conn:
            await conn.execute(
                text(
                    "INSERT INTO failure_mode_knowledge (id, error_code) "
                    "VALUES (:access_id, :access_code), (:runtime_id, :runtime_code) "
                    "ON CONFLICT (id) DO UPDATE SET error_code = EXCLUDED.error_code"
                ),
                {
                    "access_id": access_failure_mode_id,
                    "access_code": "K_ACCESS(1)",
                    "runtime_id": runtime_failure_mode_id,
                    "runtime_code": "K_RUNTIME(2)",
                },
            )
            await conn.execute(
                text(
                    "INSERT INTO trace_failure_event "
                    "(id, log_id, failure_mode, status_code) "
                    "VALUES (:id, :log_id, :failure_mode, ARRAY[]::VARCHAR[]) "
                    "ON CONFLICT (id) DO UPDATE SET "
                    "failure_mode = EXCLUDED.failure_mode, "
                    "status_code = EXCLUDED.status_code"
                ),
                {
                    "id": trace_event_id,
                    "log_id": "pg-test-status-code-log",
                    "failure_mode": f"{access_failure_mode_id},{runtime_failure_mode_id}",
                },
            )
            await conn.execute(
                text(
                    "INSERT INTO log_failure_event "
                    "(id, log_id, trace_id, status_code, failure_mode, host_name) "
                    "VALUES "
                    "(:access_log_id, :log_id, :trace_id, '1', :access_mode, 'host'), "
                    "(:runtime_log_id, :log_id, :trace_id, '', :runtime_mode, 'host')"
                ),
                {
                    "access_log_id": access_log_event_id,
                    "runtime_log_id": runtime_log_event_id,
                    "log_id": "pg-test-status-code-log",
                    "trace_id": "pg-test-trace-id",
                    "access_mode": access_failure_mode_id,
                    "runtime_mode": runtime_failure_mode_id,
                },
            )
            await conn.execute(
                text(
                    "UPDATE trace_failure_event SET trace_id = :trace_id WHERE id = :id"
                ),
                {"trace_id": "pg-test-trace-id", "id": trace_event_id},
            )

        await backfill_trace_failure_event_status_codes()

        async with PGManager.connection() as conn:
            row = (
                await conn.execute(
                    text(
                        "SELECT status_code, pg_typeof(status_code)::TEXT "
                        "FROM trace_failure_event WHERE id = :id"
                    ),
                    {"id": trace_event_id},
                )
            ).one()
        assert row[0] == ["1"]
        assert row[1] == "character varying[]"
    finally:
        if database_ready:
            async with PGManager.engine().begin() as conn:
                await conn.execute(
                    text("DELETE FROM log_failure_event WHERE id IN (:access_id, :runtime_id)"),
                    {"access_id": access_log_event_id, "runtime_id": runtime_log_event_id},
                )
                await conn.execute(
                    text("DELETE FROM trace_failure_event WHERE id = :id"),
                    {"id": trace_event_id},
                )
                await conn.execute(
                    text("DELETE FROM failure_mode_knowledge WHERE id IN (:access_id, :runtime_id)"),
                    {"access_id": access_failure_mode_id, "runtime_id": runtime_failure_mode_id},
                )
        await PGManager.close()


@pytest.mark.asyncio
async def test_log_parse_result_copy_and_aggregate():
    PGManager.initialize(PG_DSN)
    try:
        await init_postgresql_database()
        await _truncate_log_parse_result()
        log_id = f"pg-test-{datetime.now().strftime('%Y%m%d%H%M%S')}"
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        results = [
            LogParseResultDataclass(
                total_latency=float(i),
                is_anomalous=i % 2 == 0,
                log_id=log_id,
                src_ip="10.0.0.1",
                dst_ip="10.0.0.2",
                timestamp=now,
                created_at=now,
            )
            for i in range(10)
        ]

        assert await LogParseResultPGManager.add_log_parse_results(results)

        # Aggregate row is written by the worker; simulate it here so the
        # list API can return the same id used by get_aggregated_event_by_id.
        await SrcDstAggregatedEventPGManager.add_aggregated_events(
            [
                SrcDstAggregatedEventDataclass(
                    id=f"{log_id}-sd",
                    src_ip="10.0.0.1",
                    dst_ip="10.0.0.2",
                    log_id=log_id,
                    log_parse_result_cnt=10,
                    anomaly_log_parse_result_cnt=5,
                    anomaly_cnt=5,
                )
            ]
        )

        req = ListSrcDstAggregatedEventRequest(log_id=log_id)
        total, rows = await SrcDstAggregatedEventPGManager.list_aggregated_events(req)
        assert total == 1
        assert rows[0]["id"] == f"{log_id}-sd"
        assert rows[0]["log_parse_result_cnt"] == 10
        assert rows[0]["ave_total_latency"] == 4.5

        by_id = await SrcDstAggregatedEventPGManager.get_aggregated_event_by_id(
            f"{log_id}-sd"
        )
        assert by_id is not None
        assert by_id["id"] == f"{log_id}-sd"
        assert by_id["log_parse_result_cnt"] == 10

        tw_rows = await TimeWindowAggregatedEventPGManager.get_time_window_events(
            log_id
        )
        assert len(tw_rows) >= 1
        assert tw_rows[0]["log_parse_result_cnt"] == 10
    finally:
        await PGManager.close()


@pytest.mark.asyncio
async def test_aggregate_dual_write_and_get_by_id():
    PGManager.initialize(PG_DSN)
    try:
        await init_postgresql_database()
        await _truncate_log_parse_result()
        log_id = f"pg-dual-{datetime.now().strftime('%Y%m%d%H%M%S')}"
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        src_dst = [
            SrcDstAggregatedEventDataclass(
                id=f"{log_id}-sd",
                src_ip="10.0.0.1",
                dst_ip="10.0.0.2",
                log_id=log_id,
                log_parse_result_cnt=5,
                anomaly_log_parse_result_cnt=1,
                anomaly_cnt=2,
            )
        ]
        await SrcDstAggregatedEventPGManager.add_aggregated_events(src_dst)

        # get_aggregated_event_by_id should return None when no raw rows exist.
        row = await SrcDstAggregatedEventPGManager.get_aggregated_event_by_id(
            f"{log_id}-sd"
        )
        assert row is None

        # Insert raw rows and verify lookup + stats.
        results = [
            LogParseResultDataclass(
                total_latency=float(i),
                is_anomalous=True,
                log_id=log_id,
                src_ip="10.0.0.1",
                dst_ip="10.0.0.2",
                timestamp=now,
                created_at=now,
            )
            for i in range(5)
        ]
        assert await LogParseResultPGManager.add_log_parse_results(results)

        row = await SrcDstAggregatedEventPGManager.get_aggregated_event_by_id(
            f"{log_id}-sd"
        )
        assert row is not None
        assert row["log_parse_result_cnt"] == 5
        assert row["ave_total_latency"] == 2.0
    finally:
        await PGManager.close()


@pytest.mark.asyncio
async def test_time_window_list_events():
    PGManager.initialize(PG_DSN)
    try:
        await init_postgresql_database()
        await _truncate_log_parse_result()
        log_id = f"pg-tw-{datetime.now().strftime('%Y%m%d%H%M%S')}"
        kb_id = f"kb-tw-{datetime.now().strftime('%Y%m%d%H%M%S')}"

        # 10s 物化桶：6 个连续 10s 桶（共 60s），每桶 cnt=10 anomaly=1 ave=5.0
        # p99 物化为 1.0..6.0，用于验证 10s 透传 + 1min p99-of-p99s。
        base = datetime.now().replace(second=0, microsecond=0)
        base -= timedelta(seconds=base.second % 10)
        events = [
            TimeWindowAggregatedEventDataclass(
                id=f"{log_id}-tw-{i}",
                kb_id=kb_id,
                log_id=log_id,
                time_bucket=(base + timedelta(seconds=10 * i)).strftime(
                    "%Y-%m-%d %H:%M:%S"
                ),
                src_ip="10.0.0.1",
                dst_ip="10.0.0.2",
                log_parse_result_cnt=10,
                anomaly_cnt=1,
                ave_total_latency=5.0,
                latency_sum=50.0,
                p99_total_latency=float(i + 1),
            )
            for i in range(6)
        ]
        await TimeWindowAggregatedEventPGManager.add_events(events)

        # 10s 粒度：6 个桶，全量 cnt 每桶 10 > anomaly 1
        req = ListTimeWindowAggregatedEventRequest(
            kb_id=kb_id, interval=10, page_cnt=100
        )
        total, rows = await TimeWindowAggregatedEventPGManager.list_time_window_events(
            req
        )
        assert total == 6
        assert sum(r["total_cnt"] for r in rows) == 60
        assert sum(r["anomaly_cnt"] for r in rows) == 6
        assert all(
            r["total_cnt"] > r["anomaly_cnt"] for r in rows
        )
        # 10s 单行透传：每组仅一行，ip_pair p99 = 物化值原样
        p99_10s = sorted(p["p99_total_latency"] for r in rows for p in r["ip_pairs"])
        assert p99_10s == [1.0, 2.0, 3.0, 4.0, 5.0, 6.0]

        # 1min 粒度：6×10s 聚合为 1 个父桶，cnt/anomaly 相加、ave 加权
        req = ListTimeWindowAggregatedEventRequest(
            kb_id=kb_id, interval=60, page_cnt=100
        )
        total, rows = await TimeWindowAggregatedEventPGManager.list_time_window_events(
            req
        )
        assert total == 1
        assert rows[0]["total_cnt"] == 60
        assert rows[0]["anomaly_cnt"] == 6
        assert rows[0]["ave_total_latency"] == 5.0
        assert "ip_pairs" in rows[0]
        # p99-of-p99s：percentile_cont(0.99) over [1..6]（线性插值）= 5.95
        assert rows[0]["ip_pairs"][0]["p99_total_latency"] == pytest.approx(5.95)
    finally:
        await PGManager.close()
