# Copyright (c) Huawei Technologies Co., Ltd. 2023-2025. All rights reserved.
"""get_latency_metrics 桶路径单测（回退实时 SQL 已删除）。

覆盖：
  1. 非法 bucket_seconds / sample_mode（MIN）/ IP 维度过滤 → BadRequestBizException
  2. 缺 log_id → 返回空结果 (0, [])
  3. 合法请求走 _query_bucket_stats

运行：cd src/plugins/latency && PYTHONPATH=/home/li/witty-ub_8632/src/plugins \
  .venv/bin/python -m pytest test/test_latency_metrics_query.py -v -p no:cacheprovider
"""
from __future__ import annotations

import pytest

from latency.database.managers.log_parse_result import LogParseResultPGManager
from latency.ENUM.sampling import SampleMode
from latency.exceptions.biz_exceptions import BadRequestBizException
from latency.schemas.request import GetLatencyMetricsRequest


@pytest.mark.asyncio
async def test_get_latency_metrics_rejects_unsupported_inputs(monkeypatch):
    calls = {"bucket": 0}

    async def _fake_query(table, req, stats_mode):
        calls["bucket"] += 1
        return []

    monkeypatch.setattr(
        LogParseResultPGManager, "_query_bucket_stats", staticmethod(_fake_query)
    )

    # MIN 模式
    with pytest.raises(BadRequestBizException):
        await LogParseResultPGManager.get_latency_metrics(
            GetLatencyMetricsRequest(kb_id="kb-1", sample_mode=SampleMode.MIN, bucket_seconds=60, log_id="lg")
        )
    # 非法 bucket_seconds
    with pytest.raises(BadRequestBizException):
        await LogParseResultPGManager.get_latency_metrics(
            GetLatencyMetricsRequest(kb_id="kb-1", sample_mode=SampleMode.P99, bucket_seconds=999, log_id="lg")
        )
    # IP 维度过滤
    with pytest.raises(BadRequestBizException):
        await LogParseResultPGManager.get_latency_metrics(
            GetLatencyMetricsRequest(kb_id="kb-1", sample_mode=SampleMode.P99, bucket_seconds=60, log_id="lg", src_ip="10.0.0.1")
        )
    assert calls["bucket"] == 0


@pytest.mark.asyncio
async def test_get_latency_metrics_missing_log_id_returns_empty():
    # master（e6a14a03）：缺少 log_id 直接 400 —— 时延曲线按单个日志文件查询
    with pytest.raises(BadRequestBizException):
        await LogParseResultPGManager.get_latency_metrics(
            GetLatencyMetricsRequest(kb_id="kb-1", sample_mode=SampleMode.P99, bucket_seconds=60)
        )


@pytest.mark.asyncio
async def test_get_latency_metrics_valid_request_uses_bucket_table(monkeypatch):
    captured = {}

    async def _fake_query(table, req, stats_mode):
        captured["table"] = table.__name__
        captured["mode"] = stats_mode
        return [{"time": "2026-05-10 10:00:00"}]

    monkeypatch.setattr(
        LogParseResultPGManager, "_query_bucket_stats", staticmethod(_fake_query)
    )
    total, rows = await LogParseResultPGManager.get_latency_metrics(
        GetLatencyMetricsRequest(kb_id="kb-1", sample_mode=SampleMode.P99, bucket_seconds=60, log_id="lg")
    )
    assert total == 1
    assert captured == {"table": "LatencyBucket1min", "mode": "p99l"}


@pytest.mark.asyncio
async def test_get_latency_metrics_avg_uses_true_average_mode(monkeypatch):
    captured = {}

    async def _fake_query(table, req, stats_mode):
        captured["mode"] = stats_mode
        return []

    monkeypatch.setattr(
        LogParseResultPGManager, "_query_bucket_stats", staticmethod(_fake_query)
    )
    await LogParseResultPGManager.get_latency_metrics(
        GetLatencyMetricsRequest(
            kb_id="kb-1", sample_mode=SampleMode.AVG, bucket_seconds=60, log_id="lg"
        )
    )
    assert captured["mode"] == "avg"


@pytest.mark.asyncio
async def test_get_latency_metrics_p9999_uses_linear_storage_mode(monkeypatch):
    captured = {}

    async def _fake_query(table, req, stats_mode):
        captured["mode"] = stats_mode
        return []

    monkeypatch.setattr(
        LogParseResultPGManager, "_query_bucket_stats", staticmethod(_fake_query)
    )
    await LogParseResultPGManager.get_latency_metrics(
        GetLatencyMetricsRequest(
            kb_id="kb-1", sample_mode=SampleMode.P9999, bucket_seconds=60, log_id="lg"
        )
    )
    assert captured["mode"] == "p9999l"


@pytest.mark.asyncio
@pytest.mark.parametrize("mode", [SampleMode.P99, SampleMode.NONE])
@pytest.mark.parametrize("operation, expected", [("GET", 19.9), ("SET", 199.0)])
async def test_web_p99_trend_returns_linear_bucket_value(monkeypatch, mode, operation, expected):
    """The chart's service returns exact precomputed P99, even at max_points=1."""
    import polars as pl
    from latency.bucket.statistics import compute_bucket_stats_from_frame
    from latency.services.log_parse_result import LogParseResultService

    frame = pl.DataFrame({
        "tid": ["g1", "g2", "s1", "s2"],
        "bucket_epoch": [1704067200] * 4,
        "total_ms": [10.0, 20.0, 100.0, 200.0],
        "total_latency": [10.0, 20.0, 100.0, 200.0],
        "operation": ["GET", "GET", "SET", "SET"],
    })
    buckets = compute_bucket_stats_from_frame(frame)[60]

    async def query(table, req, stats_mode):
        assert stats_mode == "p99l"
        row = buckets.filter(
            (pl.col("mode") == stats_mode) & (pl.col("operation") == req.operation)
        ).to_dicts()[0]
        return [{
            "time": "2024-01-01 00:00:00",
            "total_latency": row["total_latency"],
            "total_latency_us": row["total_latency_us"],
        }]

    monkeypatch.setattr(LogParseResultPGManager, "_query_bucket_stats", staticmethod(query))
    result = await LogParseResultService.get_latency_metrics(GetLatencyMetricsRequest(
        kb_id="kb", log_id="log", operation=operation, sample_mode=mode,
        bucket_seconds=60, max_points=1,
    ))
    assert result.total == 1
    assert result.metrics[0]["total_latency"] == pytest.approx(expected)
    assert result.metrics[0]["total_latency_us"] == pytest.approx(expected * 1000)
