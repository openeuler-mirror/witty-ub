# Copyright (c) Huawei Technologies Co., Ltd. 2023-2025. All rights reserved.
"""明细子集 top_k 选择语义：`_tie_exact_top_k_tids` 必须逐值等于
``sort(total_latency desc, tid asc).head(k)``（并列按 tid 升序断结）。

覆盖：3 条同分 k=2、全同分 k 任意、第 k 名并列、不足 k 条、k=0、含 null、
随机大量并列；外加一条端到端断言（生产签名下 det 规则选中的并列 trace 必须
落在明细子集里）。

运行：cd src/plugins/latency && PYTHONPATH=<repo>/src/plugins \
  .venv/bin/python -m pytest test/test_trace_frame_topk_ties.py -q
"""
from __future__ import annotations

import random

import polars as pl
import pytest

from latency.parse.parallel_scanner.columnar import entries_to_columns
from latency.parse.parallel_scanner.trace_frame import (
    _tie_exact_top_k_tids,
    build_trace_frame,
)


# ---------------------------------------------------------------------------
# 1. 规则级：与整帧排序逐值比对
# ---------------------------------------------------------------------------

def _frame(pairs) -> pl.DataFrame:
    return pl.DataFrame({
        "tid": pl.Series([t for t, _ in pairs], dtype=pl.String),
        "total_latency": pl.Series([v for _, v in pairs], dtype=pl.Float64),
    })


def _ref(pairs, k) -> set:
    """老写法：整帧按 (total_latency desc, tid asc) 排序后取前 k 条。"""
    df = _frame(pairs)
    ranked = df.filter(pl.col("total_latency").is_not_null()).sort(
        ["total_latency", "tid"], descending=[True, False]
    )
    return set(ranked.head(k)["tid"].to_list())


def _check(pairs, k):
    got = _tie_exact_top_k_tids(_frame(pairs), k)
    want = _ref(pairs, k)
    assert got == want, (k, sorted(got), sorted(want))


def test_three_traces_same_latency_k2():
    """3 条同分、k=2 → 取 tid 升序前 2 条。"""
    pairs = [("t-c", 5.0), ("t-a", 5.0), ("t-b", 5.0)]
    assert _ref(pairs, 2) == {"t-a", "t-b"}
    _check(pairs, 2)


@pytest.mark.parametrize("k", [1, 2, 3, 4, 5, 10, 1000])
def test_all_tied_any_k(k):
    """全部同分、任意 k（含 k > n）。"""
    pairs = [(f"t{i:02d}", 7.0) for i in range(5)]
    _check(pairs, k)
    take = min(k, len(pairs))
    assert _tie_exact_top_k_tids(_frame(pairs), k) == {f"t{i:02d}" for i in range(take)}


def test_tie_at_kth_boundary():
    """2 条严格更大 + 第 3 名上 4 条并列，k=3 → 并列里补 tid 最小的那条。"""
    pairs = [("s1", 9.0), ("s2", 8.0)] + [(f"b{i}", 5.0) for i in (3, 1, 4, 2)]
    _check(pairs, 3)
    assert _tie_exact_top_k_tids(_frame(pairs), 3) == {"s1", "s2", "b1"}


def test_fewer_rows_than_k_and_zero_k():
    pairs = [("a", 3.0), ("b", 2.0)]
    _check(pairs, 5)
    _check(pairs, 0)
    assert _tie_exact_top_k_tids(_frame(pairs), 0) == set()
    assert _tie_exact_top_k_tids(_frame([]), 3) == set()


def test_nulls_excluded_like_full_sort():
    """total_latency 为 null 的行与整帧排序路径一样被排除。"""
    pairs = [("a", None), ("b", 2.0), ("c", None), ("d", 2.0), ("e", 1.0)]
    for k in (0, 1, 2, 3, 5, 9):
        _check(pairs, k)
    assert _tie_exact_top_k_tids(_frame(pairs), 4) == {"b", "d", "e"}


@pytest.mark.parametrize("k", [1, 2, 3, 7, 50, 199, 200, 201, 1000])
def test_randomized_many_ties(k):
    """200 条 trace、分数只有 4 个取值 → 大量并列；tid 随机（与插入序无关）。"""
    rnd = random.Random(20260915)
    pairs = [(f"t{rnd.randrange(10 ** 9):09d}", rnd.choice([1.0, 2.0, 3.0, 4.0]))
             for _ in range(200)]
    _check(pairs, k)


def test_randomized_insertion_order_does_not_matter():
    rnd = random.Random(7)
    pairs = [(f"t{i:03d}", rnd.choice([1.0, 2.0])) for i in range(60)]
    rnd.shuffle(pairs)
    _check(pairs, 30)


# ---------------------------------------------------------------------------
# 2. 端到端：生产签名下的明细子集必须含 det 规则选中的并列 trace
# ---------------------------------------------------------------------------

def _sdk(tid, elapsed_us):
    return ("2025-01-01T00:00:00", "GET", elapsed_us, None, None, tid,
            "10.0.0.9", 0, None, None, None, None, None, None, None, "log1")


def _worker_access(tid, elapsed_us):
    return ("2025-01-01T00:00:00", "GET", elapsed_us, None, None, tid, None,
            0, None, None, None, None, None, None, None, "log1")


def _columnar(latency_ms_by_tid) -> dict:
    merged: dict[str, list] = {"SDK access parse": [], "Worker access parse": []}
    for tid, ms in latency_ms_by_tid.items():
        merged["SDK access parse"].append(_sdk(tid, int(round(ms * 1000))))
        merged["Worker access parse"].append(
            _worker_access(tid, max(int(round(ms * 1000)) - 1, 0))
        )
    return entries_to_columns(merged)


def test_detail_subset_contains_tie_exact_picks():
    """2 条严格更大 + 4 条在第 3 名并列；threshold 极大 → 无异常 trace，
    明细子集 = det 规则 ∪ worker 侧 top_k。det 规则（tid 升序断结）选中的
    s1/s2/b1 必须都带 __ 列 —— 只走 top_k 时可能漏掉并列的 b1。

    （不断言 polars top_k 内部取谁：那是实现细节，不是本测试要钉的语义。）
    """
    lat = {"s1": 9.0, "s2": 8.0, "b1": 5.0, "b2": 5.0, "b3": 5.0, "b4": 5.0}
    df = build_trace_frame(_columnar(lat), threshold_ms=1e9, top_k=3)
    assert df.height == len(lat)
    got = set(df.filter(pl.col("__se").is_not_null())["tid"].to_list())
    assert {"s1", "s2", "b1"} <= got
    assert got <= set(lat)
