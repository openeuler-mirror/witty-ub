# Copyright (c) Huawei Technologies Co., Ltd. 2023-2025. All rights reserved.
"""T3 (polars-pipeline-rewrite): _aggregate_polars vs golden fixture parity.

简单直接（用户明确要求，不做 400 行脚手架）：

1. fixture parity：``_fixture_raw()`` → ``entries_to_columns`` → ``build_trace_frame``
   → ``_aggregate_polars``，src_dst / time_window / anomalous_tids 与
   golden_fixture.json 字段级相等（排除 id/uuid、created_at）。
2. quantile-linear 显式断言：p99 == np.percentile(99)（polars 默认 nearest
   会偏差 ~1%，golden 捕获自 np.percentile 的 linear 语义）。

运行：cd src/plugins/latency && PYTHONPATH=/home/li/witty-ub_8632/src/plugins \
  .venv/bin/python -m pytest test/test_polars_pipeline_parity.py -q
"""
from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path

import numpy as np
import pytest

from latency.parse.parallel_scanner.columnar import entries_to_columns
from latency.parse.parallel_scanner.trace_frame import build_trace_frame
from latency.task.worker.kv_cache_log_parse_worker import KVCacheLogParseWorker

from test_trace_frame import _fixture_raw

# id(uuid4) / created_at(构造时刻) 每次运行不同，golden 也未捕获，比较时排除。
# log_id：T7 后语义 = 传入的 log_file_id（顶层 log_file.id），不再是组内
# first_log（扫描器文件级随机 uuid）——golden 捕获的是旧语义，故排除并
# 在 test_aggregate_log_id_binds_log_file_id 显式断言新语义。
_EXCLUDED_KEYS = frozenset({"id", "created_at", "log_id"})


def _load_golden() -> dict:
    golden_path = Path(__file__).parent / "golden" / "golden_fixture.json"
    return json.loads(golden_path.read_text(encoding="utf-8"))


def _build_aggregate():
    """fixture → df_trace → _aggregate_polars，返回 (results, agg_map, tw, anom)。"""
    df_trace = build_trace_frame(entries_to_columns(_fixture_raw()))
    return KVCacheLogParseWorker._aggregate_polars(
        df_trace, threshold_ms=5.0, log_file_id="op001"
    )


def _field_subset(rows, golden_rows):
    """把 dataclass 行投影为 golden 行的字段子集（排除运行期字段）。"""
    got = []
    for row in rows:
        d = {k: v for k, v in asdict(row).items() if k not in _EXCLUDED_KEYS}
        # golden 不含的键（dataclass 独有，如超集统计字段）不参与比较
        got.append({k: d[k] for k in golden_rows[0] if k in d})
    return got


def test_aggregate_counts_match_golden():
    results, _, tw, anom_tids = _build_aggregate()
    golden = _load_golden()["summary"]

    assert len(results) == golden["src_dst_events"]
    assert len(tw) == golden["time_window_events"]
    assert len(anom_tids) == golden["anomalous_tids"]
    assert anom_tids == {"t2", "t3"}


def test_src_dst_parity_field_by_field():
    results, _, _, _ = _build_aggregate()
    golden_rows = _load_golden()["src_dst_events"]

    got = _field_subset(results, golden_rows)
    assert len(got) == len(golden_rows)
    # 组键(src,dst,op) → 字段 dict；忽略输出顺序，字段级精确相等
    got_by_key = {(r["src_ip"], r["dst_ip"], r["operation"]): r for r in got}
    exp_by_key = {
        (r["src_ip"], r["dst_ip"], r["operation"]): r for r in golden_rows
    }
    assert set(got_by_key) == set(exp_by_key)
    for key in exp_by_key:
        for field, expected in exp_by_key[key].items():
            if field in _EXCLUDED_KEYS:
                continue
            actual = got_by_key[key][field]
            if isinstance(expected, float):
                assert actual == pytest.approx(expected), (key, field, actual, expected)
            else:
                assert actual == expected, (key, field, actual, expected)


def test_time_window_parity_field_by_field():
    _, _, tw, _ = _build_aggregate()
    golden_rows = _load_golden()["time_window_events"]

    got = _field_subset(tw, golden_rows)
    assert len(got) == len(golden_rows)
    got_by_key = {(r["time_bucket"], r["src_ip"], r["dst_ip"]): r for r in got}
    exp_by_key = {
        (r["time_bucket"], r["src_ip"], r["dst_ip"]): r for r in golden_rows
    }
    assert set(got_by_key) == set(exp_by_key)
    for key in exp_by_key:
        for field, expected in exp_by_key[key].items():
            if field in _EXCLUDED_KEYS:
                continue
            actual = got_by_key[key][field]
            if isinstance(expected, float):
                assert actual == pytest.approx(expected), (key, field, actual, expected)
            else:
                assert actual == expected, (key, field, actual, expected)


def test_quantile_uses_linear_interpolation():
    """p99 必须 == np.percentile(99)（linear）；polars 默认 nearest 会偏差。"""
    _, _, tw, _ = _build_aggregate()
    by_key = {(r.time_bucket, r.src_ip, r.dst_ip): r for r in tw}

    # ("", "", GET) 桶内 total_ms = [2.5 (t3), 1.5 (t4)]
    row = by_key[("2025-01-01 00:00:00", "", "")]
    expected = float(np.percentile(np.asarray([2.5, 1.5], dtype=np.float64), 99))
    assert row.p99_total_latency == pytest.approx(expected)
    assert row.p99_total_latency == pytest.approx(2.49)

    # 单元素组：p99 == 该值
    row = by_key[("2025-01-01 00:00:00", "10.1.0.1", "10.1.0.2")]
    assert row.p99_total_latency == pytest.approx(5.0)


def test_aggregate_log_id_binds_log_file_id():
    """T7 修复：聚合事件 log_id 必须 = 传入 log_file_id（顶层 log_file.id）。

    旧实现用组内 ``first_log``（df_trace.log_id 列 = 扫描器文件级随机
    uuid，process_worker.py:608），导致 API 按顶层 log_file.id 查不到
    聚合结果。修复后 src_dst / time_window 事件 log_id 均绑定参数。
    """
    _, _, tw, _ = _build_aggregate()
    assert all(r.log_id == "op001" for r in tw)
    results, _, _, _ = _build_aggregate()
    assert all(r.log_id == "op001" for r in results)
