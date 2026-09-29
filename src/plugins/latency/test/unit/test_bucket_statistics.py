# Copyright (c) Huawei Technologies Co., Ltd. 2023-2025. All rights reserved.
"""latency.bucket.statistics 单元测试。"""
import time
from dataclasses import dataclass
from types import SimpleNamespace

import numpy as np
import polars as pl
import pytest

from latency.bucket import statistics as bstat
from latency.bucket.statistics import (
    GRANULARITY_KEYS,
    PERCENTILE_MODES,
    _group_edges,
    _normalize_op,
    compute_bucket_ids,
    compute_bucket_stats_from_frame,
    percentile_kth_positions,
    pick_percentile_rows,
)


class TestNormalizeOp:
    def test_get_variants(self):
        assert _normalize_op("GET") == 0
        assert _normalize_op("ds_get_object") == 0
        assert _normalize_op("ObjectGet") == 0

    def test_set_variants(self):
        assert _normalize_op("SET") == 1
        assert _normalize_op("CREATE") == 1
        assert _normalize_op("PUBLISH") == 1

    def test_none_and_empty(self):
        assert _normalize_op(None) == 1
        assert _normalize_op("") == 1


class TestComputeBucketIds:
    def test_single_timestamp(self):
        # 2024-01-01T00:00:05 UTC 的 epoch 秒 = 1704067205
        ts = np.array(["2024-01-01T00:00:05"], dtype="datetime64[s]")
        ids = compute_bucket_ids(ts, 10)
        assert ids.tolist() == [1704067205 // 10]

    def test_floor_alignment(self):
        # 同一 10s 桶内的两个时间戳（:05 和 :09）桶号相同
        ts = np.array(["2024-01-01T00:00:05", "2024-01-01T00:00:09"], dtype="datetime64[s]")
        ids = compute_bucket_ids(ts, 10)
        assert ids[0] == ids[1]

    def test_different_buckets(self):
        ts = np.array(["2024-01-01T00:00:05", "2024-01-01T00:00:15"], dtype="datetime64[s]")
        ids = compute_bucket_ids(ts, 10)
        assert ids[1] == ids[0] + 1

    def test_minute_granularity(self):
        ts = np.array(["2024-01-01T00:00:59", "2024-01-01T00:01:00"], dtype="datetime64[s]")
        ids = compute_bucket_ids(ts, 60)
        assert ids[1] == ids[0] + 1


class TestPercentileKthPositions:
    def test_zero_count(self):
        assert percentile_kth_positions(0) == [0, 0, 0, 0]

    def test_single_element(self):
        # cnt=1: 所有分位 clamp 到 0
        assert percentile_kth_positions(1) == [0, 0, 0, 0]

    def test_two_elements(self):
        # cnt=2: median=floor(1)-1=0, p99=floor(1.98)-1=0, p9999=0, pmax=floor(2)-1=1
        assert percentile_kth_positions(2) == [0, 0, 0, 1]

    def test_hundred_elements(self):
        # cnt=100: median=49, p99=98, p9999=98, pmax=99
        assert percentile_kth_positions(100) == [49, 98, 98, 99]

    def test_result_length_matches_modes(self):
        assert len(percentile_kth_positions(50)) == len(PERCENTILE_MODES)


class TestPickPercentileRows:
    def test_empty_slice(self):
        assert pick_percentile_rows(np.array([])) == []

    def test_single_element(self):
        result = pick_percentile_rows(np.array([5.0]))
        assert len(result) == 4
        assert all(idx == 0 for idx in result)

    def test_returns_aligned_indices(self):
        values = np.array([30.0, 10.0, 20.0])
        result = pick_percentile_rows(values)
        assert len(result) == 4
        # 最小值（10.0，索引 1）应被选中（小桶多个分位重复）
        assert 1 in result
        # 最大值（30.0，索引 0）pmax 必选
        assert 0 in result

    def test_explicit_kth_positions(self):
        values = np.array([1.0, 2.0, 3.0, 4.0])
        result = pick_percentile_rows(values, kth_positions=[3, 3])
        assert result == [3, 3]


def _make_trace_frame() -> pl.DataFrame:
    """构造最小 df_trace：4 行（2 GET + 1 SET 在同一 10s 桶，1 GET 在下一桶）。"""
    base = 1704067200  # 2024-01-01T00:00:00 epoch 秒（10s 对齐）
    return pl.DataFrame(
        {
            "bucket_epoch": [base, base, base, base + 10],
            "total_ms": [100.0, 200.0, 300.0, 50.0],
            "total_latency": [100.0, 200.0, 300.0, 50.0],
            "operation": ["GET", "GET", "SET", "GET"],
            "tid": ["t1", "t2", "t3", "t4"],
            "src": ["1.1.1.1"] * 4,
            "dst": ["2.2.2.2"] * 4,
        }
    )


class TestComputeBucketStatsFromFrame:
    # 说明：test_tuple_shape / test_operation_encoding / test_modes_per_group /
    # test_empty_frame_returns_empty_lists / test_total_latency_of_median_get /
    # test_materializer_path 及 TestYuanrongEnrichment 断言的是 dev 分支的
    # 48 列 tuple 行 + median/p99/p9999/pmax 模式输出；master 的
    # compute_bucket_stats_from_frame 返回 polars DataFrame，行为不同，
    # 相关用例删除（结构无关的键覆盖/过滤用例保留）。

    def test_all_granularity_keys_present(self):
        result = compute_bucket_stats_from_frame(_make_trace_frame(), kb_id="kb", log_id="log")
        assert set(result.keys()) == set(GRANULARITY_KEYS)

    def test_null_rows_filtered(self):
        df = _make_trace_frame().with_columns(
            pl.when(pl.col("tid") == "t1").then(None).otherwise(pl.col("bucket_epoch")).alias("bucket_epoch")
        )
        result = compute_bucket_stats_from_frame(df)
        # t1 被过滤后：桶1 内 GET 仅 t2、SET t3、桶2 GET t4 → 3 组 × 4 分位
        assert len(result[10]) == 12


class TestGroupEdges:
    def test_basic_grouping(self):
        bucket_ids = np.array([1, 1, 0, 1])
        op_codes = np.array([0, 0, 1, 1])
        order = np.lexsort((bucket_ids, op_codes))
        keys, edges, ops, buckets = _group_edges(bucket_ids, op_codes, order)
        # sort_key = op*2 + bucket → [1,1,2,3]
        assert keys.tolist() == [1, 2, 3]
        assert edges.tolist() == [0, 2, 3, 4]
        assert ops.tolist() == [0, 1, 1]
        assert buckets.tolist() == [1, 0, 1]


# 说明：TestRowField / TestMergeYuanrong / TestBuildBucketRows 依赖的
# _row_field/_merge_yuanrong/_build_bucket_rows 在 master 的 bucket
# 实现中不存在（dev 分支的富化行构建路径），相关用例随 import 一并移除。


class TestReport:
    async def test_report_stage_no_task_id(self):
        from latency.bucket.statistics import _report_stage

        t = await _report_stage(None, time.perf_counter(), time.perf_counter(), "label")
        assert t >= 0


class TestComputeAndStore:
    async def test_end_to_end_with_mocked_store(self, monkeypatch):
        stored = {}

        async def fake_store(log_id, rows_by_granularity, tables, on_table=None):
            stored["log_id"] = log_id
            stored["tables"] = tables
            stored["rows"] = rows_by_granularity
            if on_table is not None:
                for g in GRANULARITY_KEYS:
                    await on_table(g, time.perf_counter(), len(rows_by_granularity[g]))

        monkeypatch.setattr(bstat, "_store_bucket_rows", fake_store)
        result = await bstat.compute_and_store_bucket_stats_from_frame(
            _make_trace_frame(), log_id="log-1", kb_id="kb-1"
        )
        assert set(result.keys()) == set(GRANULARITY_KEYS)
        assert result[10] == 12
        assert stored["log_id"] == "log-1"
        assert stored["tables"] == bstat.DEFAULT_TABLES
        # on_table 回调被调用（打点路径覆盖）
        assert set(stored["rows"].keys()) == set(GRANULARITY_KEYS)

    async def test_custom_tables(self, monkeypatch):
        stored = {}

        async def fake_store(log_id, rows_by_granularity, tables, on_table=None):
            stored["tables"] = tables

        monkeypatch.setattr(bstat, "_store_bucket_rows", fake_store)
        custom = {10: "t10", 60: "t60", 600: "t600", 3600: "t3600"}
        await bstat.compute_and_store_bucket_stats_from_frame(
            _make_trace_frame(), log_id="l", kb_id="k", tables=custom
        )
        assert stored["tables"] == custom
