# Copyright (c) Huawei Technologies Co., Ltd. 2023-2025. All rights reserved.
"""get_latency_metrics 查询改造单测（计划 Phase 2 任务 10 验收）。

覆盖：
  1. 回退实时 SQL 结构：ROW_NUMBER + COUNT(*) OVER（动态桶, src_ip, dst_ip,
     operation）选分位代表行，无 percentile_cont（纯编译断言，不需 DB）。
  2. 动态桶表达式墙钟对齐：已知非对齐时间戳 → 桶起点与手算墙钟对齐值一致
     （10s→:20/:30/:40，60s→:00，600s→:40，3600s→整点）。
  3. 回退 nearest-rank 代表行：cnt=10 时各模式选中行与手算 floor(cnt*p) 一致。

运行：cd src/plugins/latency && PYTHONPATH=/home/li/witty-ub_8632/src/plugins \
  .venv/bin/python -m pytest test/test_latency_metrics_query.py -v -p no:cacheprovider
"""
from __future__ import annotations

import math
import os
import uuid
from datetime import datetime
from typing import Any

import pytest
from sqlalchemy import text
from sqlalchemy.dialects import postgresql

from latency.database.engine import PGManager
from latency.database.managers.log_parse_result import (
    _has_ip_dimension_filters,
    LogParseResultPGManager,
)
from latency.ENUM.sampling import SampleMode
from latency.schemas.request import GetLatencyMetricsRequest

PG_DSN = os.getenv(
    "LATENCY_PG_DSN",
    "postgresql://witty-ub:witty-ub@127.0.0.1:5432/witty-ub",
)

# 回退实时 SQL 涉及的列（仿 log_parse_result 结构；测试自建自删临时表）。
_TMP_TABLE_DDL = """
CREATE TABLE IF NOT EXISTS {tbl} (
    id          varchar     PRIMARY KEY,
    log_id      varchar,
    trace_id    varchar,
    timestamp   timestamp without time zone,
    src_ip      inet,
    dst_ip      inet,
    operation   varchar,
    existed_status boolean,
    total_latency float,
    urma_total_latency float,
    worker_query_meta_latency float,
    sdk_process float, sdk_rpc float,
    local_worker_cost float, local_worker_lock float,
    remote_worker_cost float, remote_worker_rpc float,
    master_process float, master_rpc_total float,
    create_latency float, publish_latency float,
    worker_total_latency float
)
"""


def _req(mode: SampleMode, bucket_seconds: int = 60, **kwargs) -> GetLatencyMetricsRequest:
    """最小化请求（无 log_id → 走回退实时 SQL 构造路径）。"""
    return GetLatencyMetricsRequest(
        sample_mode=mode,
        bucket_seconds=bucket_seconds,
        **kwargs,
    )


def _compile_fallback(mode: SampleMode, bucket_seconds: int = 60) -> str:
    stmt = LogParseResultPGManager._build_fallback_stmt(
        _req(mode, bucket_seconds)
    )
    return str(
        stmt.compile(
            dialect=postgresql.dialect(),
            compile_kwargs={"literal_binds": True},
        )
    )


# ---------------------------------------------------------------------------
# 1. 回退 SQL 结构（纯编译断言，不需 DB）
# ---------------------------------------------------------------------------

def test_fallback_sql_uses_row_number_partition_by_bucket_src_dst_op():
    sql = _compile_fallback(SampleMode.P99, 60).lower()

    assert "row_number() over (partition by" in sql
    assert "count(*) over (partition by" in sql
    # 分区键：动态桶表达式 + src_ip + dst_ip + operation
    assert "date_trunc('minute'" in sql
    assert "log_parse_result.src_ip, log_parse_result.dst_ip, log_parse_result.operation" in sql
    # 分位代表行筛选：nearest-rank（1-based rn = GREATEST(1, FLOOR(cnt * p))）
    assert "greatest(1, floor(" in sql
    # 不用 percentile_cont 聚合 / 窗口
    assert "percentile_cont" not in sql


def test_fallback_sql_bucket_expr_depends_on_bucket_seconds():
    # 10s/600s 粒度应出现提取 + 对齐表达式，3600s 出现 date_trunc('hour')
    for bs, needle in (
        (10, "extract(second from"),
        (600, "extract(minute from"),
        (3600, "date_trunc('hour'"),
        (999, "date_trunc('second'"),
    ):
        sql = _compile_fallback(SampleMode.P99, bs).lower()
        assert needle in sql, f"bucket_seconds={bs} 应含 {needle}"


def test_fallback_sql_mode_maps_to_nearest_rank():
    # 每种模式对应的分位点：GREATEST(1, FLOOR(cnt * p))
    cases = [
        (SampleMode.P95, "0.95"),
        (SampleMode.P99, "0.99"),
        (SampleMode.P9999, "0.9999"),
        (SampleMode.AVG, "0.5"),
        (SampleMode.MAX, "1.0"),
        (SampleMode.NONE, "0.99"),
    ]
    for mode, p in cases:
        sql = _compile_fallback(mode, 60).lower()
        assert "floor(" in sql and f"* {p})" in sql, f"mode={mode.value} 应含 p={p}"


# ---------------------------------------------------------------------------
# 1b. IP 维度过滤守卫：统计表无 IP 维度，带过滤必须走回退实时 SQL
# ---------------------------------------------------------------------------

def test_has_ip_dimension_filters_detects_each_field():
    # 无 IP 维度过滤 → False
    assert _has_ip_dimension_filters(_req(SampleMode.P99)) is False

    # 任一字段存在 → True；空字符串 src/dst 视为未过滤（与回退 builder 语义一致）
    cases = [
        ("cluster_name", "c1"),
        ("host", "h1"),
        ("pod_ip", "10.0.0.9"),
        ("src_ip", "10.0.0.1"),
        ("dst_ip", "10.0.0.2"),
    ]
    for field, value in cases:
        req = GetLatencyMetricsRequest(sample_mode=SampleMode.P99, bucket_seconds=60)
        setattr(req, field, value)
        assert _has_ip_dimension_filters(req) is True
    # 空字符串等价于未过滤（回退 builder 里 src_ip=="" 分支过滤 is_(None)，
    # 统计表路径无对应语义 → 同样视为无 IP 维度过滤）
    assert _has_ip_dimension_filters(
        _req(SampleMode.P99, src_ip="", dst_ip="")
    ) is False


@pytest.mark.asyncio
async def test_ip_dimension_filter_forces_fallback_path(monkeypatch):
    """带 src_ip + log_id 的请求必须走回退实时 SQL，绝不触碰统计表。"""
    calls = {"stats": 0, "fallback": 0}

    async def _fake_stats(table, req, stats_mode):
        calls["stats"] += 1
        raise AssertionError("IP 维度过滤不应查询统计表")

    async def _fake_fallback(req):
        calls["fallback"] += 1
        return 0, []

    monkeypatch.setattr(
        LogParseResultPGManager, "_query_bucket_stats", staticmethod(_fake_stats)
    )
    monkeypatch.setattr(
        LogParseResultPGManager, "_fallback_latency_metrics", staticmethod(_fake_fallback)
    )

    req = _req(SampleMode.P99, bucket_seconds=60, log_id="lg", src_ip="10.0.0.1")
    await LogParseResultPGManager.get_latency_metrics(req)
    assert calls["fallback"] == 1
    assert calls["stats"] == 0


def test_fallback_sql_filters_by_log_id():
    """MAJOR 2 回归：回退实时 SQL 必须带上 req.log_id 过滤，禁止扫全库。"""
    stmt = LogParseResultPGManager._build_fallback_stmt(
        _req(SampleMode.P99, bucket_seconds=60, log_id="lg-123")
    )
    sql = str(
        stmt.compile(
            dialect=postgresql.dialect(),
            compile_kwargs={"literal_binds": True},
        )
    )
    assert "log_id = 'lg-123'" in sql
    # 不带 log_id 的请求不产生该过滤条件。
    assert "log_id =" not in _compile_fallback(SampleMode.P99, 60)


# ---------------------------------------------------------------------------
# 2 & 3. 真实 DB 断言：桶边界墙钟对齐 + nearest-rank 代表行
# ---------------------------------------------------------------------------

def _table_name() -> str:
    return f"latency_metrics_test_{uuid.uuid4().hex[:8]}"


async def _run_fallback_sql(
    tbl: str, mode: SampleMode, bucket_seconds: int
) -> list[dict[str, Any]]:
    """把回退 SQL 编译（literal_binds）后指向临时表执行。"""
    stmt = LogParseResultPGManager._build_fallback_stmt(
        _req(mode, bucket_seconds)
    )
    sql = str(
        stmt.compile(
            dialect=postgresql.dialect(),
            compile_kwargs={"literal_binds": True},
        )
    ).replace("log_parse_result", tbl)
    rows = []
    async with PGManager.session() as session:
        result = await session.execute(text(sql))
        for r in result.mappings().all():
            rows.append(dict(r))
    return rows


@pytest.mark.asyncio
async def test_dynamic_bucket_expr_wall_clock_alignment_and_nearest_rank():
    PGManager.initialize(PG_DSN)
    tbl = _table_name()
    try:
        try:
            async with PGManager.connection() as conn:
                await conn.execute(text(_TMP_TABLE_DDL.format(tbl=tbl)))
        except Exception as e:
            pytest.skip(f"PostgreSQL 不可达或建临时表失败（跳过 DB 断言）: {e}")

        # 3 行非对齐时间戳，同一 (GET, 10.0.0.1 → 10.0.0.2)。
        base = datetime(2026, 5, 10, 12, 47, 24)
        async with PGManager.connection() as conn:
            for i, sec in enumerate((0, 9, 17)):
                ts = base.replace(second=base.second + sec)
                await conn.execute(
                    text(
                        f"INSERT INTO {tbl} (id, log_id, trace_id, timestamp, src_ip, dst_ip,"
                        " operation, existed_status, total_latency) VALUES"
                        " (:id, :log_id, :trace_id, :ts, '10.0.0.1', '10.0.0.2', 'GET', TRUE, :lat)"
                    ),
                    {
                        "id": f"r{i}",
                        "log_id": "lg",
                        "trace_id": f"tr-{i}",
                        "ts": ts,
                        "lat": float(i + 1),
                    },
                )

        # 桶边界墙钟对齐（手算：10s→:20/:30/:40，60s→:00，600s→:40，3600s→整点）。
        rows10 = await _run_fallback_sql(tbl, SampleMode.P99, 10)
        assert sorted(r["time"] for r in rows10) == [
            datetime(2026, 5, 10, 12, 47, 20),
            datetime(2026, 5, 10, 12, 47, 30),
            datetime(2026, 5, 10, 12, 47, 40),
        ]
        rows60 = await _run_fallback_sql(tbl, SampleMode.P99, 60)
        assert [r["time"] for r in rows60] == [datetime(2026, 5, 10, 12, 47, 0)]
        rows600 = await _run_fallback_sql(tbl, SampleMode.P99, 600)
        assert [r["time"] for r in rows600] == [datetime(2026, 5, 10, 12, 40, 0)]
        rows3600 = await _run_fallback_sql(tbl, SampleMode.P99, 3600)
        assert [r["time"] for r in rows3600] == [datetime(2026, 5, 10, 12, 0, 0)]

        # 60s 桶内 3 行，cnt=3：p99 → rn=FLOOR(3*0.99)=2 → 排序后第 2 个（lat=2.0）。
        assert [r["total_latency"] for r in rows60] == [2.0]

        # 10s 桶各 1 行：代表行即该行本身。
        assert sorted(r["total_latency"] for r in rows10) == [1.0, 2.0, 3.0]

    finally:
        try:
            async with PGManager.connection() as conn:
                await conn.execute(text(f"DROP TABLE IF EXISTS {tbl}"))
        except Exception:
            pass
        await PGManager.close()


@pytest.mark.asyncio
async def test_fallback_nearest_rank_representative_hand_computed():
    PGManager.initialize(PG_DSN)
    tbl = _table_name()
    try:
        try:
            async with PGManager.connection() as conn:
                await conn.execute(text(_TMP_TABLE_DDL.format(tbl=tbl)))
        except Exception as e:
            pytest.skip(f"PostgreSQL 不可达或建临时表失败（跳过 DB 断言）: {e}")

        # 单组 10 行，latency 1..10（同 60s 桶 / GET / 同一 IP 对）。
        ts = datetime(2026, 5, 10, 12, 0, 0)
        async with PGManager.connection() as conn:
            for i in range(1, 11):
                await conn.execute(
                    text(
                        f"INSERT INTO {tbl} (id, log_id, trace_id, timestamp, src_ip, dst_ip,"
                        " operation, existed_status, total_latency) VALUES"
                        " (:id, :log_id, :trace_id, :ts, '10.0.0.1', '10.0.0.2', 'GET', TRUE, :lat)"
                    ),
                    {
                        "id": f"r{i}",
                        "log_id": "lg",
                        "trace_id": f"tr-{i}",
                        "ts": ts,
                        "lat": float(i),
                    },
                )

        # 手算 nearest-rank（1-based rn = GREATEST(1, FLOOR(cnt * p))）。
        cnt = 10
        expected = {
            SampleMode.P95: max(1, math.floor(cnt * 0.95)),
            SampleMode.P99: max(1, math.floor(cnt * 0.99)),
            SampleMode.P9999: max(1, math.floor(cnt * 0.9999)),
            SampleMode.AVG: max(1, math.floor(cnt * 0.5)),
            SampleMode.MAX: max(1, math.floor(cnt * 1.0)),
            SampleMode.MIN: max(1, math.floor(cnt * 0.0)),
            SampleMode.NONE: max(1, math.floor(cnt * 0.99)),
        }
        for mode, rn in expected.items():
            rows = await _run_fallback_sql(tbl, mode, 60)
            assert len(rows) == 1, f"mode={mode.value} 应恰选中 1 行"
            assert rows[0]["total_latency"] == float(rn), (
                f"mode={mode.value}: 手算 rn={rn} → 期望代表行 latency={rn}"
            )
    finally:
        try:
            async with PGManager.connection() as conn:
                await conn.execute(text(f"DROP TABLE IF EXISTS {tbl}"))
        except Exception:
            pass
        await PGManager.close()
