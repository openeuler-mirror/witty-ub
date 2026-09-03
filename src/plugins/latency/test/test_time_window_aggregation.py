# Copyright (c) Huawei Technologies Co., Ltd. 2023-2025. All rights reserved.
"""time_window 10s 物化 + 查询聚合单测（tw10s 验收）。

覆盖：
  1. 写入侧 10s 桶对齐（kv_cache_log_parse_worker._bucket_epoch_10s /
     _format_bucket_epoch）：秒级时间戳 floor 到 10s 墙钟（:00/:10/:20/:30/:40/:50）。
  2. 查询侧粒度归一化 _normalize_interval：10/60/600/3600，兼容旧字符串。
  3. _rows_to_events 聚合：1min=6×10s、10min=60×10s、1h=360×10s，
     cnt/anomaly 相加、ave_total_latency 加权、p99 按 SQL percentile_cont
     预聚合结果透传到 ip_pair（10s 单行透传；粗粒度 = p99-of-p99s 近似）。
  4. latency_sum 落库后旧行守卫 COALESCE(latency_sum, ave*cnt) 由 SQL 承担，
     本文件在 _rows_to_events 层验证 ave 与 p99 透传语义。

运行：cd src/plugins/latency && PYTHONPATH=/home/li/witty-ub_8632/src/plugins \
  .venv/bin/python -m pytest test/test_time_window_aggregation.py -v -p no:cacheprovider
"""
from __future__ import annotations

from datetime import datetime
from types import SimpleNamespace

import numpy as np
import pytest

from latency.database.managers.time_window_aggregated_event import (
    TimeWindowAggregatedEventPGManager,
)
from latency.schemas.request import ListTimeWindowAggregatedEventRequest
from latency.task.worker.kv_cache_log_parse_worker import KVCacheLogParseWorker

# 2025-01-01 00:00:00 UTC（墙钟）
BASE_EPOCH = 1735689600


def _row(
    bucket_epoch: int,
    cnt: int,
    anomaly: int,
    ave: float,
    p99: float | None = None,
    min_lat: float | None = None,
    max_lat: float | None = None,
    p95: float | None = None,
) -> SimpleNamespace:
    return SimpleNamespace(
        bucket_epoch=bucket_epoch,
        src_ip="10.0.0.1",
        dst_ip="10.0.0.2",
        total_cnt=cnt,
        anomaly_cnt=anomaly,
        ave=ave,
        p99=p99,
        min_lat=min_lat,
        max_lat=max_lat,
        p95=p95,
    )


def _aligned(epoch: int, interval: int) -> int:
    """模拟 SQL 的 floor(epoch/interval)*interval 对齐。"""
    return (epoch // interval) * interval


def _req(**kwargs) -> ListTimeWindowAggregatedEventRequest:
    kwargs.setdefault("kb_id", "kb-test")
    return ListTimeWindowAggregatedEventRequest(page_num=1, page_cnt=1000, **kwargs)


# ---------------------------------------------------------------------------
# 1. 写入侧 10s 桶对齐
# ---------------------------------------------------------------------------

def test_bucket_10s_alignment_string() -> None:
    # numpy 桶转换：epoch 秒 floor 到 10s（UTC 墙钟）
    assert KVCacheLogParseWorker._bucket_epoch_10s(
        "2025-01-01 12:00:07.123"
    ) == 1735732800  # 12:00:00 UTC
    assert KVCacheLogParseWorker._bucket_epoch_10s(
        "2025-01-01 12:00:12"
    ) == 1735732810  # 12:00:10
    assert KVCacheLogParseWorker._bucket_epoch_10s(
        "2025-01-01 12:00:59"
    ) == 1735732850  # 12:00:50
    assert KVCacheLogParseWorker._bucket_epoch_10s(
        "2025-01-01 12:01:00"
    ) == 1735732860  # 12:01:00
    # epoch → "YYYY-MM-DD HH:MM:SS" 字符串（替代 _time_bucket_10s 的输出）
    assert KVCacheLogParseWorker._format_bucket_epoch(1735732800) == "2025-01-01 12:00:00"
    assert KVCacheLogParseWorker._format_bucket_epoch(1735732850) == "2025-01-01 12:00:50"


def test_bucket_10s_alignment_datetime() -> None:
    assert KVCacheLogParseWorker._bucket_epoch_10s(
        datetime(2025, 1, 1, 12, 0, 5)
    ) == 1735732800  # 12:00:00
    assert KVCacheLogParseWorker._bucket_epoch_10s(
        datetime(2025, 1, 1, 12, 0, 16)
    ) == 1735732810  # 12:00:10


def test_bucket_10s_empty_and_garbage() -> None:
    # 不可解析时间戳 → None（聚合侧归入 "" bucket）
    assert KVCacheLogParseWorker._bucket_epoch_10s(None) is None
    assert KVCacheLogParseWorker._bucket_epoch_10s("") is None
    assert KVCacheLogParseWorker._bucket_epoch_10s("garbage") is None


# ---------------------------------------------------------------------------
# 2. 粒度归一化
# ---------------------------------------------------------------------------

def test_normalize_interval_seconds() -> None:
    m = TimeWindowAggregatedEventPGManager._normalize_interval
    assert m(10) == 10
    assert m(60) == 60
    assert m(600) == 600
    assert m(3600) == 3600


def test_normalize_interval_legacy_names() -> None:
    m = TimeWindowAggregatedEventPGManager._normalize_interval
    assert m("second") == 10
    assert m("minute") == 60
    assert m("hour") == 3600


def test_normalize_interval_unknown_clamps_to_nearest() -> None:
    m = TimeWindowAggregatedEventPGManager._normalize_interval
    assert m(25) == 10
    assert m(100) == 60
    assert m(700) == 600
    assert m(None) == 60
    assert m("bogus") == 60


# ---------------------------------------------------------------------------
# 3. 查询聚合：cnt/anomaly 相加、ave 按 cnt 加权
# ---------------------------------------------------------------------------

def test_rows_to_events_1min_sums_6x10s() -> None:
    rows = [
        _row(_aligned(BASE_EPOCH + i * 10, 60), cnt=10, anomaly=1, ave=5.0, p99=8.8)
        for i in range(6)
    ]
    total, events = TimeWindowAggregatedEventPGManager._rows_to_events(
        rows, 60, _req(interval=60)
    )
    assert total == 1
    ev = events[0]
    assert ev["start_time"] == "2025-01-01 00:00:00"
    assert ev["end_time"] == "2025-01-01 00:01:00"
    assert ev["total_cnt"] == 60
    assert ev["anomaly_cnt"] == 6
    assert ev["ave_total_latency"] == 5.0
    assert len(ev["ip_pairs"]) == 1
    pair = ev["ip_pairs"][0]
    assert pair["log_parse_result_cnt"] == 60
    assert pair["anomaly_log_parse_result_cnt"] == 6
    assert pair["anomaly_cnt"] == 6
    # 6×10s 桶 p99 均为 8.8，SQL percentile_cont(0.99) → 8.8 透传
    assert pair["p99_total_latency"] == 8.8


def test_rows_to_events_p99_of_p99s_approximation() -> None:
    # 粗粒度(1min)重聚合语义：桶内 6 个 10s 行的物化 p99 取 p99。
    # SQL 侧用 percentile_cont(0.99) within group 计算（近似，非统计精确）；
    # 此处用 np.percentile 模拟同一插值算法，再验证该预聚合值透传到 ip_pair。
    per_10s_p99 = [1.0, 2.0, 3.0, 4.0, 5.0, 6.0]
    sql_p99 = np.percentile(per_10s_p99, 99)  # 5.95
    rows = [
        _row(_aligned(BASE_EPOCH, 60), cnt=1, anomaly=0, ave=3.5, p99=sql_p99)
    ]
    total, events = TimeWindowAggregatedEventPGManager._rows_to_events(
        rows, 60, _req(interval=60)
    )
    assert total == 1
    pair = events[0]["ip_pairs"][0]
    assert pair["p99_total_latency"] == pytest.approx(5.95)
    # 10s 单行透传：interval=10 时每组仅一行，p99 = 物化值原样
    rows10 = [
        _row(_aligned(BASE_EPOCH, 10), cnt=3, anomaly=0, ave=4.0, p99=7.7)
    ]
    _, events10 = TimeWindowAggregatedEventPGManager._rows_to_events(
        rows10, 10, _req(interval=10)
    )
    assert events10[0]["ip_pairs"][0]["p99_total_latency"] == 7.7
    # 旧行 p99 未物化 → NULL → ip_pair p99 保持 None（前端显示空）
    rows_old = [_row(_aligned(BASE_EPOCH, 60), cnt=5, anomaly=0, ave=2.0)]
    _, events_old = TimeWindowAggregatedEventPGManager._rows_to_events(
        rows_old, 60, _req(interval=60)
    )
    assert events_old[0]["ip_pairs"][0]["p99_total_latency"] is None


def test_rows_to_events_10min_sums_60x10s() -> None:
    rows = [_row(_aligned(BASE_EPOCH + i * 10, 600), cnt=1, anomaly=1 if i % 5 == 0 else 0, ave=float(i % 10 + 1)) for i in range(60)]
    total, events = TimeWindowAggregatedEventPGManager._rows_to_events(
        rows, 600, _req(interval=600)
    )
    assert total == 1
    ev = events[0]
    assert ev["start_time"] == "2025-01-01 00:00:00"
    assert ev["end_time"] == "2025-01-01 00:10:00"
    assert ev["total_cnt"] == 60
    assert ev["anomaly_cnt"] == 12
    # 加权平均 = Σ((i%10+1)*1)/60 = 55*6/60 = 5.5
    assert abs(ev["ave_total_latency"] - 5.5) < 1e-9


def test_rows_to_events_1h_sums_360x10s() -> None:
    rows = [_row(_aligned(BASE_EPOCH + i * 10, 3600), cnt=1, anomaly=1 if i % 5 == 0 else 0, ave=float(i % 10 + 1)) for i in range(360)]
    total, events = TimeWindowAggregatedEventPGManager._rows_to_events(
        rows, 3600, _req(interval=3600)
    )
    assert total == 1
    ev = events[0]
    assert ev["start_time"] == "2025-01-01 00:00:00"
    assert ev["end_time"] == "2025-01-01 01:00:00"
    assert ev["total_cnt"] == 360
    assert ev["anomaly_cnt"] == 72
    assert abs(ev["ave_total_latency"] - 5.5) < 1e-9


def test_rows_to_events_weighted_ave_not_simple_mean() -> None:
    rows = [
        _row(_aligned(BASE_EPOCH, 60), cnt=10, anomaly=1, ave=2.0),
        _row(_aligned(BASE_EPOCH + 10, 60), cnt=20, anomaly=3, ave=4.0),
    ]
    total, events = TimeWindowAggregatedEventPGManager._rows_to_events(
        rows, 60, _req(interval=60)
    )
    assert total == 1
    ev = events[0]
    assert ev["total_cnt"] == 30
    assert ev["anomaly_cnt"] == 4
    # 加权：(10*2 + 20*4)/30 = 100/30，而非简单均值 3.0
    assert abs(ev["ave_total_latency"] - 100.0 / 30.0) < 1e-9


def test_rows_to_events_multiple_parent_buckets_2x1min() -> None:
    rows = [_row(_aligned(BASE_EPOCH + i * 10, 60), cnt=5, anomaly=0, ave=1.0) for i in range(12)]
    total, events = TimeWindowAggregatedEventPGManager._rows_to_events(
        rows, 60, _req(interval=60)
    )
    assert total == 2
    assert [e["start_time"] for e in events] == [
        "2025-01-01 00:00:00",
        "2025-01-01 00:01:00",
    ]
    assert events[0]["total_cnt"] == 30
    assert events[1]["total_cnt"] == 30
