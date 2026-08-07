# Copyright (c) Huawei Technologies Co., Ltd. 2023-2025. All rights reserved.
"""字段表（field table）切片并行 golden fixture 单测（Todo 2/5 + T4/T5 验收）。

覆盖：
  1. 字段表串行构建（_build_field_table_rows）= list[LogParseResultDataclass]
     全 trace（is_anomalous=False），顺序 = SDK entry 顺序 —— golden 基线。
  2. src/dst 取源统一 = URMA→RemotePull→"" 链（与聚合一致，SDK entry 无
     SRC_ADDR/DST_ADDR）。
  3. c2w_latency 派生 = max(0, sdk_elapsed − worker_elapsed)/1000
     （result_builder.py:496-505 生产语义）。
  4. T5/T7 明细物化：df_trace 过滤 anomalous_tids → _make_field_row ==
     字段表（_build_field_table_rows 过滤子集）逐字段一致。
  5. generate_aggregate_result 4-tuple 兼容 + _aggregate_three_way 5-tuple。

运行：cd src/plugins/latency && PYTHONPATH=/home/li/witty-ub_8632/src/plugins \
  .venv/bin/python -m pytest test/test_field_table_slice.py -v -p no:cacheprovider
"""
from __future__ import annotations

from dataclasses import fields

import pytest

from latency.schemas.log import LogParseResultDataclass
from latency.task.worker.kv_cache_log_parse_worker import (
    KVCacheLogParseWorker,
)


# ---------------------------------------------------------------------------
# fixture 构造：16 元组按 TupleField 顺序
# ---------------------------------------------------------------------------

def _sdk(tid, op="GET", elapsed_us=1000, status=0, ts="2025-01-01T00:00:00",
         pod="10.0.0.9", log="log1"):
    return (ts, op, elapsed_us, None, None, tid, pod, status, None, None,
            None, None, None, None, None, log)


def _urma(tid, src="10.0.0.1", dst="10.0.0.2", elapsed_us=400):
    return ("2025-01-01T00:00:00", "URMA", elapsed_us, None, None, tid, None,
            0, None, None, None, src, dst, None, None, "log1")


def _remote_pull(tid, src="10.1.0.1", dst="10.1.0.2", elapsed_us=400):
    return ("2025-01-01T00:00:00", "REMOTE_PULL", elapsed_us, None, None, tid,
            None, 0, None, None, None, src, dst, None, None, "log1")


def _worker_access(tid, elapsed_us=300):
    return ("2025-01-01T00:00:00", "GET", elapsed_us, None, None, tid, None,
            0, None, None, None, None, None, None, None, "log1")


def _fixture():
    """5 traces：t1 URMA 链、t2 RemotePull 链 + SET、t3 status 异常、
    t4 无下游链、t5 无 SDK（应跳过）。

    返回平铺 dict(与生产 parse_log 的 trace_index 同构):
    {trace_id: {29字段平铺dict}} —— 从 3 层原始经 _build_flat_trace_index。
    """
    raw = {
        "t1": {
            "SDK access parse": [_sdk("t1", elapsed_us=1000)],
            "Worker urma parse": [_urma("t1", "10.0.0.1", "10.0.0.2")],
            "Worker access parse": [_worker_access("t1", 300)],
        },
        "t2": {
            "SDK access parse": [_sdk("t2", op="SET", elapsed_us=5000)],
            "Worker remote pull parse": [
                _remote_pull("t2", "10.1.0.1", "10.1.0.2")
            ],
        },
        "t3": {
            "SDK access parse": [_sdk("t3", elapsed_us=2500, status=3)],
            "Worker access parse": [_worker_access("t3", 2500)],
        },
        "t4": {
            "SDK access parse": [_sdk("t4", elapsed_us=1500)],
        },
        "t5": {},
    }
    # 生产函数吃 {label: [entries]}: 先把 3 层 raw 转成该形态再归并
    by_label: dict[str, list] = {}
    for tid, labels in raw.items():
        for label, entries in labels.items():
            by_label.setdefault(label, []).extend(entries)
    return KVCacheLogParseWorker._build_flat_trace_index(by_label)


def _row_dict(row):
    """逐字段快照（排除 created_at 墙钟时间戳，避免并行/串行不可比）。"""
    return {
        f.name: getattr(row, f.name)
        for f in fields(row)
        if f.name != "created_at"
    }


# ---------------------------------------------------------------------------
# 1. 字段表串行构建
# ---------------------------------------------------------------------------

def test_field_table_serial_all_valid_traces():
    rows = KVCacheLogParseWorker._build_field_table_rows(_fixture())
    # t5 无 SDK 被跳过
    assert [r.trace_id for r in rows] == ["t1", "t2", "t3", "t4"]
    assert all(r.is_anomalous is False for r in rows)
    # 顺序 = SDK entry 顺序（list 保序）


def test_field_table_src_dst_urma_chain():
    rows = {r.trace_id: r for r in
            KVCacheLogParseWorker._build_field_table_rows(_fixture())}
    # URMA 链优先
    assert rows["t1"].src_ip == "10.0.0.1"
    assert rows["t1"].dst_ip == "10.0.0.2"
    # RemotePull 回退
    assert rows["t2"].src_ip == "10.1.0.1"
    assert rows["t2"].dst_ip == "10.1.0.2"
    # 无下游链 → None（与聚合 ("","") 键同源）
    assert rows["t3"].src_ip is None
    assert rows["t3"].dst_ip is None
    assert rows["t4"].src_ip is None
    assert rows["t4"].dst_ip is None


def test_field_table_c2w_latency_derivation():
    rows = {r.trace_id: r for r in
            KVCacheLogParseWorker._build_field_table_rows(_fixture())}
    # max(0, 1000 − 300)/1000 = 0.7
    assert rows["t1"].c2w_latency == 0.7
    # max(0, 2500 − 2500)/1000 = 0.0
    assert rows["t3"].c2w_latency == 0.0
    # 无 Worker access → None
    assert rows["t2"].c2w_latency is None
    assert rows["t4"].c2w_latency is None


def test_field_table_latency_surface_remap():
    rows = {r.trace_id: r for r in
            KVCacheLogParseWorker._build_field_table_rows(_fixture())}
    assert rows["t1"].total_latency == 1.0
    assert rows["t1"].urma_total_latency == 0.4
    # query_meta → worker_query_meta remap（无 query meta → None）
    assert rows["t1"].worker_query_meta_latency is None
    assert rows["t1"].c2w_urma_latency == (1000 - 300) / 1000.0


def test_field_table_log_file_id_override():
    rows = KVCacheLogParseWorker._build_field_table_rows(_fixture(), "op001")
    assert all(r.log_id == "op001" for r in rows)


# ---------------------------------------------------------------------------
# 2. generate_aggregate_result 兼容 + _aggregate_three_way 5-tuple（df_trace 输入）
# ---------------------------------------------------------------------------

def _to_df():
    """fixture 平铺 dict 的 df_trace 等价物（与 _fixture() 同源，T2 parity 验证）。"""
    from latency.parse.parallel_scanner.columnar import entries_to_columns
    from latency.parse.parallel_scanner.trace_frame import build_trace_frame
    from test_trace_frame import _fixture_raw

    return build_trace_frame(entries_to_columns(_fixture_raw()))


def test_aggregate_serial_fallback_small():
    """df_trace → 聚合：t2/t3 异常、src/dst 取源与聚合一致。"""
    import asyncio

    async def _check():
        agg = await KVCacheLogParseWorker.generate_aggregate_result(_to_df())
        assert len(agg) == 4
        results, src_dst_map, tw, anom_tids = agg
        assert len(results) == 3
        assert len(tw) == 3
        # t2（5ms>2ms）与 t3（status=3）异常
        assert anom_tids == {"t2", "t3"}
        assert len(src_dst_map) == 3
        # src/dst 取源与聚合一致（URMA 链）
        by_sd = {(e.src_ip, e.dst_ip) for e in results}
        assert ("10.0.0.1", "10.0.0.2") in by_sd
        assert ("10.1.0.1", "10.1.0.2") in by_sd
        return True

    assert asyncio.run(_check())


def test_aggregate_three_way_field_table():
    import asyncio

    async def _check():
        sd, sdmap, tw, anom, df_trace = (
            await KVCacheLogParseWorker._aggregate_three_way(
                _to_df(), None, "op001"
            )
        )
        # T7：第 5 位 = df_trace（polars DataFrame, T2/T3 契约）
        assert df_trace.height == 4
        assert set(df_trace["tid"].to_list()) == {"t1", "t2", "t3", "t4"}
        # 明细物化走 _build_anomalous_detail_rows（df_trace 过滤）。
        detail = KVCacheLogParseWorker._build_anomalous_detail_rows(
            _to_df(), anom, kb_id="test_kb", log_file_id="op001"
        )
        assert {r.trace_id for r in detail} == {"t2", "t3"}
        assert all(r.log_id == "op001" for r in detail)
        for r in detail:
            r.is_anomalous = True
            op = (r.operation or "").strip().upper()
            op_key = "SET" if "SET" in op else "GET"
            r.aggregated_event_id = sdmap.get(
                (r.src_ip or "", r.dst_ip or "", op_key), ""
            )
        assert all(r.aggregated_event_id for r in detail)
        assert all(r.is_anomalous for r in detail)
        return True

    assert asyncio.run(_check())


# ---------------------------------------------------------------------------
# 3. T5/T7：df_trace 行 to_dict → 明细行 == 字段表参照（None vs "" 哨兵）
# ---------------------------------------------------------------------------

def test_detail_rows_from_frame_matches_field_table():
    """T5/T7: df_trace 过滤 anomalous_tids → _make_field_row == 字段表参照。

    TRACE_COLUMNS == 平铺 dict 键名（冻结契约），``frame.to_dicts()`` 直接可
    被 ``_make_field_row`` 消费。参照 = ``_build_field_table_rows`` 全量字段表
    过滤 anomalous_tids（同 ``_make_field_row`` 物化），对 {t2,t3} 子集逐字段
    相等（排除 created_at，is_anomalous 归一为 True），覆盖 None vs "" 哨兵：
    t3 无下游链 → src_ip/dst_ip None；t2 RemotePull 链 → src_ip 10.1.0.1。
    golden detail_rows（total_latency 5.0/2.5、c2w_latency 0.0）spot-check。
    """
    from latency.parse.parallel_scanner.columnar import entries_to_columns
    from latency.parse.parallel_scanner.trace_frame import build_trace_frame
    from test_trace_frame import _fixture_raw

    anom = {"t2", "t3"}
    reference = [
        r for r in KVCacheLogParseWorker._build_field_table_rows(_fixture(), "op001")
        if r.trace_id in anom
    ]
    for r in reference:
        r.is_anomalous = True
    df_trace = build_trace_frame(entries_to_columns(_fixture_raw()))
    got = KVCacheLogParseWorker._build_anomalous_detail_rows(
        df_trace, anom, kb_id="test_kb", log_file_id="op001"
    )

    assert sorted(r.trace_id or "" for r in got) == ["t2", "t3"]
    assert all(r.is_anomalous for r in got)
    ref_by_id = {r.trace_id: r for r in reference}
    for r in got:
        ref = ref_by_id[r.trace_id]
        for f in fields(r):
            if f.name == "created_at":
                continue
            if f.name.endswith("_us") or f.name in ("request_mode", "urma_inflight_max"):
                continue  # yuanrong 字段由新路径另测
            assert getattr(r, f.name) == getattr(ref, f.name), (
                r.trace_id, f.name, getattr(r, f.name), getattr(ref, f.name),
            )

    by_id = {r.trace_id: r for r in got}
    # 哨兵语义：RemotePull 链 → IP；无下游链 → None
    assert by_id["t2"].src_ip == "10.1.0.1"
    assert by_id["t2"].dst_ip == "10.1.0.2"
    assert by_id["t3"].src_ip is None
    assert by_id["t3"].dst_ip is None
    # golden detail_rows spot-check
    assert by_id["t2"].total_latency == 5.0
    assert by_id["t3"].total_latency == 2.5
    assert by_id["t3"].c2w_latency == 0.0
    assert by_id["t3"].worker_total_latency == 2.5


def test_detail_rows_from_frame_empty_anomalous():
    """T5: anomalous_tids 为空/无匹配 → 空列表（不崩溃）。"""
    from latency.parse.parallel_scanner.columnar import entries_to_columns
    from latency.parse.parallel_scanner.trace_frame import build_trace_frame
    from test_trace_frame import _fixture_raw

    df_trace = build_trace_frame(entries_to_columns(_fixture_raw()))
    assert KVCacheLogParseWorker._build_anomalous_detail_rows(
        df_trace, set(), kb_id="test_kb", log_file_id="op001"
    ) == []
    assert KVCacheLogParseWorker._build_anomalous_detail_rows(
        df_trace, {"no-such-tid"}, kb_id="test_kb", log_file_id="op001"
    ) == []
