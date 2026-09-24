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
    _build_bucket_rows,
    _group_edges,
    _merge_yuanrong,
    _normalize_op,
    _report,
    _row_field,
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
    def test_all_granularity_keys_present(self):
        result = compute_bucket_stats_from_frame(_make_trace_frame(), kb_id="kb", log_id="log")
        assert set(result.keys()) == set(GRANULARITY_KEYS)

    def test_tuple_shape(self):
        result = compute_bucket_stats_from_frame(_make_trace_frame(), kb_id="kb", log_id="log")
        for g, rows in result.items():
            for row in rows:
                # 8 固定键 + 14 legacy 指标 + 26 yuanrong = 48 列
                assert len(row) == 48
                assert row[0] == "kb"  # kb_id
                assert row[1] == "log"

    def test_operation_encoding(self):
        result = compute_bucket_stats_from_frame(_make_trace_frame())
        for rows in result.values():
            for row in rows:
                assert row[3] in ("GET", "SET")

    def test_modes_per_group(self):
        # g=10：桶1 内 GET 组(2行)+SET 组(1行) + 桶2 GET 组(1行) → 每组 4 个分位
        result = compute_bucket_stats_from_frame(_make_trace_frame())
        assert len(result[10]) == 12
        modes = {row[4] for row in result[10]}
        assert modes == {"median", "p99", "p9999", "pmax"}

    def test_empty_frame_returns_empty_lists(self):
        df = _make_trace_frame().filter(pl.lit(False))
        result = compute_bucket_stats_from_frame(df)
        assert result == {g: [] for g in GRANULARITY_KEYS}

    def test_null_rows_filtered(self):
        df = _make_trace_frame().with_columns(
            pl.when(pl.col("tid") == "t1").then(None).otherwise(pl.col("bucket_epoch")).alias("bucket_epoch")
        )
        result = compute_bucket_stats_from_frame(df)
        # t1 被过滤后：桶1 内 GET 仅 t2、SET t3、桶2 GET t4 → 3 组 × 4 分位
        assert len(result[10]) == 12

    def test_total_latency_of_median_get(self):
        # 桶1（epoch 1704067200，即 2024-01-01 00:00:00）GET 组 = [100(t1), 200(t2)]：
        # median → 100，pmax → 200
        from datetime import datetime as _dt

        result = compute_bucket_stats_from_frame(_make_trace_frame())
        bucket1 = _dt(2024, 1, 1, 0, 0, 0)
        get_rows = [
            r for r in result[10]
            if r[3] == "GET" and r[4] in ("median", "pmax") and r[2] == bucket1
        ]
        latencies = {r[4]: r[8] for r in get_rows}
        assert latencies["median"] == 100.0
        assert latencies["pmax"] == 200.0

    def test_materializer_path(self):
        """materializer（dataclass 物化）路径与 dict 路径产出一致的键列。"""

        def materializer(row):
            return SimpleNamespace(
                trace_id=row.get("tid"),
                src_ip=row.get("src"),
                dst_ip=row.get("dst"),
                **{k: row.get(k) for k in bstat.METRIC_KEYS},
            )

        result = compute_bucket_stats_from_frame(
            _make_trace_frame(), kb_id="kb", log_id="log", materializer=materializer
        )
        assert set(result.keys()) == set(GRANULARITY_KEYS)
        for rows in result.values():
            for row in rows:
                assert len(row) == 48
                assert row[0] == "kb"
                assert row[1] == "log"
        # trace_id 列（row[7]）应来自 materializer 对象
        tids = {r[7] for r in result[10]}
        assert tids == {"t1", "t2", "t3", "t4"}


_YR_INTERNAL_INT_COLS = (
    "__se", "__wsum", "__wmax", "__wn", "__umax", "__uimax", "__cn",
    "__ce2esum", "__ce0", "__ce1", "__cs0", "__cs1", "__cnw0", "__cnw1",
    "__me", "__ms", "__mn", "__re", "__rs", "__rn", "__qm",
)


def _make_yuanrong_frame() -> pl.DataFrame:
    """在基础 frame 上附加 22 个 yuanrong 内部列（合法零值），触发 Phase 2 富化。"""
    df = _make_trace_frame()
    cols = [pl.lit(0.0, dtype=pl.Float64).alias(c) for c in _YR_INTERNAL_INT_COLS]
    cols.append(pl.lit("GET", dtype=pl.Utf8).alias("__sop"))
    return df.with_columns(cols)


class TestYuanrongEnrichment:
    def test_phase2_runs_with_internal_cols(self):
        result = compute_bucket_stats_from_frame(_make_yuanrong_frame(), kb_id="kb", log_id="log")
        assert set(result.keys()) == set(GRANULARITY_KEYS)
        # 48 列结构不变，yuanrong 26 列由 Phase 2 填充
        for rows in result.values():
            for row in rows:
                assert len(row) == 48


class TestRowField:
    def test_dict_source(self):
        assert _row_field({"a": 1}, "a") == 1
        assert _row_field({"a": 1}, "b") is None

    def test_object_source(self):
        obj = SimpleNamespace(x=5)
        assert _row_field(obj, "x") == 5
        assert _row_field(obj, "y") is None


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


class TestMergeYuanrong:
    def test_none_passthrough(self):
        r = {"a": 1}
        assert _merge_yuanrong(r, None) is r

    def test_dict_update(self):
        r = {"a": 1}
        out = _merge_yuanrong(r, {"a": 2, "b": 3})
        assert out == {"a": 2, "b": 3}

    def test_dataclass_setattr_skips_none(self):
        @dataclass
        class Row:
            a: int = 1
            b: int = 2

        row = Row()
        _merge_yuanrong(row, {"a": 10, "b": None})
        assert row.a == 10
        assert row.b == 2  # None 不覆盖


class TestBuildBucketRows:
    def test_builds_rows_per_granularity(self):
        valid_rows = [
            {"trace_id": "t1", "src_ip": "1.1.1.1", "dst_ip": "2.2.2.2"},
            {"trace_id": "t2", "src_ip": "1.1.1.1", "dst_ip": "2.2.2.2"},
        ]
        # g=10 单组：bucket_ids=[0,0], op=[0,0]
        per_granularity = {
            g: _group_edges(np.array([0, 0]), np.array([0, 0]), np.array([0, 1]))
            for g in GRANULARITY_KEYS
        }
        # reps: (gid, mode_idx, orig) —— 4 个分位全选第 0/1 行
        reps = {g: [(0, mi, mi % 2) for mi in range(4)] for g in GRANULARITY_KEYS}
        result = _build_bucket_rows(valid_rows, per_granularity, reps, kb_id="kb", log_id="log")
        assert set(result.keys()) == set(GRANULARITY_KEYS)
        for rows in result.values():
            assert len(rows) == 4
            for row in rows:
                assert len(row) == 48
                assert row[0] == "kb"
                assert row[7] in ("t1", "t2")

    def test_materializer_only_for_selected(self):
        calls = []

        def materializer(row):
            calls.append(row["trace_id"])
            return SimpleNamespace(
                trace_id=row["trace_id"], src_ip=None, dst_ip=None,
                **{k: None for k in bstat.METRIC_KEYS},
            )

        valid_rows = [{"trace_id": f"t{i}"} for i in range(4)]
        per_granularity = {
            g: _group_edges(np.array([0, 0, 0, 0]), np.array([0, 0, 0, 0]), np.array([0, 1, 2, 3]))
            for g in GRANULARITY_KEYS
        }
        # 每粒度只选 1 个代表行（median → orig 0）
        reps = {g: [(0, 0, 0)] for g in GRANULARITY_KEYS}
        result = _build_bucket_rows(
            valid_rows, per_granularity, reps, kb_id="kb", log_id="log", materializer=materializer
        )
        # 同一 orig=0 在 4 个粒度中被复用，只物化一次
        assert calls == ["t0"]
        assert all(len(rows) == 1 for rows in result.values())


class TestReport:
    async def test_no_task_id_is_silent(self):
        # task_id=None 时静默跳过，不触碰 BaseWorker
        await _report(None, "message", 0.5)

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
