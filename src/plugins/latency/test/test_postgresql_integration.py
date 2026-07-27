"""PostgreSQL integration tests.

Requires a running PostgreSQL instance. By default it targets the container
started for this project:

    postgresql://postgres:postgres@127.0.0.1:15432/latency_test

Set LATENCY_PG_DSN to override.
"""
from __future__ import annotations

import os
from datetime import datetime

import pytest
from sqlalchemy import text

from latency.database.engine import PGManager
from latency.database.init import init_postgresql_database
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

        req = ListTimeWindowAggregatedEventRequest(log_id=log_id, interval="second")
        total, rows = await TimeWindowAggregatedEventPGManager.list_time_window_events(
            req
        )
        assert total >= 1
        assert rows[0]["total_cnt"] == 10
        assert "ip_pairs" in rows[0]
    finally:
        await PGManager.close()
