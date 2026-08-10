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
            GetLatencyMetricsRequest(sample_mode=SampleMode.MIN, bucket_seconds=60, log_id="lg")
        )
    # 非法 bucket_seconds
    with pytest.raises(BadRequestBizException):
        await LogParseResultPGManager.get_latency_metrics(
            GetLatencyMetricsRequest(sample_mode=SampleMode.P99, bucket_seconds=999, log_id="lg")
        )
    # IP 维度过滤
    with pytest.raises(BadRequestBizException):
        await LogParseResultPGManager.get_latency_metrics(
            GetLatencyMetricsRequest(sample_mode=SampleMode.P99, bucket_seconds=60, log_id="lg", src_ip="10.0.0.1")
        )
    assert calls["bucket"] == 0


@pytest.mark.asyncio
async def test_get_latency_metrics_missing_log_id_returns_empty():
    total, rows = await LogParseResultPGManager.get_latency_metrics(
        GetLatencyMetricsRequest(sample_mode=SampleMode.P99, bucket_seconds=60)
    )
    assert total == 0
    assert rows == []


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
        GetLatencyMetricsRequest(sample_mode=SampleMode.P99, bucket_seconds=60, log_id="lg")
    )
    assert total == 1
    assert captured == {"table": "LatencyBucket1min", "mode": "p99"}
