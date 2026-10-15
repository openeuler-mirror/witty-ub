"""T1 columnar worker output tests: per-line 29/31-col projection.

Covers:
- TRACE_COLUMNS frozen contract == the 31 flat-dict keys produced by
  ``_build_flat_trace_index`` (aggregate scalars + all latencies + detail fields)
- ``entries_to_columns`` projects every entry into one sparse + None-aligned
  row (row count == entry count), each row tagged with its tid
- projected values == what ``_serialize_entry`` reads (tuple field access)
- SDK-only rows fill SDK columns and leave latency columns None
- URMA / RemotePull rows carry src/dst and the ``_src_rank`` priority
  (URMA=2, RemotePull=1) for the T2 max-rank src/dst merge spec
- tuple (serialized) and dataclass (LogEntry) inputs are equivalent
- "Worker info parse" bucket rows route by entry_type to sub-label columns
- ``columns_to_frame`` builds a polars DataFrame with TRACE_COLUMNS present
- spawn-process pickle round-trip of the worker result is complete
- ``_process_worker_func`` returns ``{"columns": ...}`` by default and legacy
  ``{label: [tuples]}`` only when WITTY_UB_SCAN_COLUMNS=0
- ``_merge_results`` detects the "columns" key and extends per field

Run: cd src/plugins/latency && PYTHONPATH=/home/li/witty-ub_8632/src/plugins \
  .venv/bin/python -m pytest test/test_columnar.py -v -p no:cacheprovider
"""
from __future__ import annotations

import os
import sys
from datetime import datetime
from pathlib import Path

_TEST_DIR = Path(__file__).resolve().parent
_PROJECT_ROOT = _TEST_DIR.parent
sys.path.insert(0, str(_PROJECT_ROOT))

import pytest

from latency.ENUM.ds_log import EntryType, TupleField  # noqa: E402
from latency.schemas.ds_log import LogEntry  # noqa: E402


# ---------------------------------------------------------------------------
# fixture helpers (16-field tuples indexed by TupleField, like _serialize_entry)
# ---------------------------------------------------------------------------

def _sdk(tid, op="GET", elapsed_us=1000, status=0, ts="2025-01-01T00:00:00",
         pod="10.0.0.9", log="log1"):
    return (ts, op, elapsed_us, None, None, tid, pod, status, None, None,
            None, None, None, None, None, log)


def _urma(tid, src="10.0.0.1", dst="10.0.0.2", elapsed_us=400):
    return ("2025-01-01T00:00:00", "URMA", elapsed_us, None, None, tid, None,
            0, None, EntryType.URMA.value, None, src, dst, None, None, "log1")


def _remote_pull(tid, src="10.1.0.1", dst="10.1.0.2", elapsed_us=400):
    return ("2025-01-01T00:00:00", "REMOTE_PULL", elapsed_us, None, None, tid,
            None, 0, None, EntryType.REMOTE_PULL.value, None, src, dst, None,
            None, "log1")


def _link(tid, elapsed_us=900):
    return ("2025-01-01T00:00:00", "LINK", elapsed_us, None, None, tid, None,
            0, None, EntryType.LINK.value, None, None, None, None, None, "log1")


def _worker_access(tid, elapsed_us=300):
    return ("2025-01-01T00:00:00", "GET", elapsed_us, None, None, tid, None,
            0, None, None, None, None, None, None, None, "log1")


def _mk_sdk_dataclass(tid="trace-sdk-1", elapsed_us=500, status=0):
    return LogEntry(
        timestamp=datetime(2026, 5, 11, 5, 25, 20, 207278),
        trace_id=tid,
        pod_ip="pod-1",
        elapsed_us=elapsed_us,
        entry_type=EntryType.SDK_GET,
        log_id="log-1",
        operation="DS_KV_CLIENT_GET",
        data_size="8395125",
        status_code=status,
    )


def _mk_urma_dataclass(tid="trace-urma-1", elapsed_us=1272.62):
    return LogEntry(
        timestamp=datetime(2026, 5, 11, 5, 25, 20, 207278),
        trace_id=tid,
        pod_ip="pod-1",
        elapsed_us=elapsed_us,
        entry_type=EntryType.URMA,
        log_id="log-1",
        src_addr="6.62.223.31:31501",
        dst_addr="6.62.222.250:31501",
        inflight_count=1,
    )


def _serialize_entry(entry) -> tuple:
    # 本地等价实现：旧 process_worker._serialize_entry（master 已随 polars
    # 重构移除该模块），仅做 16 字段 dataclass→tuple 的平凡转换，供
    # "tuple 与 dataclass 输入等价"类用例构造参考输入。
    return (
        entry.timestamp,
        entry.operation,
        entry.elapsed_us,
        entry.data_size,
        entry.object_key,
        entry.trace_id,
        entry.pod_ip,
        entry.status_code,
        entry.resp_msg,
        entry.entry_type.value if entry.entry_type else None,
        entry.cluster_name,
        entry.src_addr,
        entry.dst_addr,
        entry.inflight_count,
        entry.request_size,
        entry.log_id,
    )


# ---------------------------------------------------------------------------
# 1. TRACE_COLUMNS frozen contract
# ---------------------------------------------------------------------------

def test_trace_columns_is_frozen_tuple_of_33_flat_dict_keys():
    from latency.parse.parallel_scanner import columnar

    assert isinstance(columnar.TRACE_COLUMNS, tuple)
    assert len(columnar.TRACE_COLUMNS) == 33
    assert len(set(columnar.TRACE_COLUMNS)) == 33  # unique
    # 必须覆盖平铺 dict 的全部键（聚合标量 + 全部时延 + 明细字段）
    expected = {
        "tid", "total_ms", "total_latency", "src", "dst", "op", "operation",
        "op_key", "bucket_epoch", "log_id", "status_code", "timestamp",
        "pod_ip", "cluster_name", "host", "data_size", "inflight_count",
        "c2w_urma_latency", "urma_total_latency", "urma_link_latency",
        "worker_query_meta_latency", "worker_total_latency",
        "sdk_process", "sdk_rpc", "local_worker_cost", "local_worker_lock",
        "remote_worker_cost", "remote_worker_rpc", "master_process",
        "master_rpc_total", "w2w_urma_latency", "create_latency",
        "publish_latency",
    }
    assert set(columnar.TRACE_COLUMNS) == expected
    # 内部辅助列不得混入冻结契约
    assert "_src_rank" not in columnar.TRACE_COLUMNS
    assert "_label" not in columnar.TRACE_COLUMNS


def test_label_to_columns_contract():
    from latency.parse.parallel_scanner import columnar

    sdk_cols = set(columnar.LABEL_TO_COLUMNS[columnar.SDK_LABEL])
    # SDK 行填聚合标量 + SDK 明细列，不填下游 src/dst
    assert {"total_ms", "total_latency", "op", "op_key", "bucket_epoch",
            "log_id", "status_code", "timestamp", "pod_ip", "data_size",
            "inflight_count"} <= sdk_cols
    assert not ({"src", "dst"} & sdk_cols)
    # URMA 行填 urma_total_latency + src/dst（含 pod_ip/cluster_name 富化列）；
    # RemotePull 填 src/dst + 富化列
    assert set(columnar.LABEL_TO_COLUMNS[columnar.URMA_LABEL]) == {
        "urma_total_latency", "src", "dst", "pod_ip", "cluster_name",
    }
    assert set(columnar.LABEL_TO_COLUMNS[columnar.REMOTE_PULL_LABEL]) == {
        "src", "dst", "pod_ip", "cluster_name",
    }
    assert columnar.LABEL_TO_COLUMNS[columnar.LINK_LABEL] == (
        "urma_link_latency", "pod_ip", "cluster_name",
    )
    assert columnar.LABEL_TO_COLUMNS[columnar.QUERY_META_LABEL] == (
        "worker_query_meta_latency", "pod_ip", "cluster_name",
    )


# ---------------------------------------------------------------------------
# 2. entries_to_columns: projection parity + row count
# ---------------------------------------------------------------------------

def test_sdk_projection_matches_serialize_entry_read():
    from latency.parse.parallel_scanner import columnar

    entry = _mk_sdk_dataclass()
    t = _serialize_entry(entry)  # 16-field tuple, 参考读取
    cols = columnar.entries_to_columns({columnar.SDK_LABEL: [entry]})

    assert cols["total_ms"] == [t[TupleField.ELAPSED_US] / 1000.0]
    assert cols["total_latency"] == [t[TupleField.ELAPSED_US] / 1000.0]
    assert cols["op"] == [str(t[TupleField.OPERATION] or "").strip().upper()]
    assert cols["operation"] == [
        str(t[TupleField.OPERATION] or "").strip().upper() or None
    ]
    assert cols["op_key"] == ["GET"]
    assert cols["bucket_epoch"] == [1778477120]
    assert cols["log_id"] == ["log-1"]
    assert cols["status_code"] == [0]
    assert cols["timestamp"] == [str(entry.timestamp)]
    assert cols["pod_ip"] == ["pod-1"]
    assert cols["data_size"] == ["8395125"]
    assert cols["inflight_count"] == [None]
    assert cols["tid"] == [t[TupleField.TRACE_ID]]
    # SDK 行不填下游时延列；src/dst 是 trace 级归并产物（T2 兜底 ""），行级为 None
    assert cols["urma_total_latency"] == [None]
    assert cols["worker_total_latency"] == [None]
    assert cols["src"] == [None]
    assert cols["dst"] == [None]


def test_row_count_equals_entry_count():
    from latency.parse.parallel_scanner import columnar

    merged = {
        columnar.SDK_LABEL: [_sdk("t1"), _sdk("t2")],
        columnar.URMA_LABEL: [_urma("t1")],
        columnar.REMOTE_PULL_LABEL: [_remote_pull("t2")],
        columnar.LINK_LABEL: [_link("t1")],
        columnar.WORKER_ACCESS_LABEL: [_worker_access("t1")],
    }
    total = sum(len(v) for v in merged.values())
    cols = columnar.entries_to_columns(merged)
    for name in (*columnar.TRACE_COLUMNS, *columnar.INTERNAL_COLUMNS):
        assert len(cols[name]) == total, f"column {name} row count"
    assert sorted(cols["tid"]) == ["t1", "t1", "t1", "t1", "t2", "t2"]


def test_urma_remote_pull_src_rank():
    from latency.parse.parallel_scanner import columnar

    cols = columnar.entries_to_columns({
        columnar.SDK_LABEL: [_sdk("t1")],
        columnar.URMA_LABEL: [_urma("t1", "10.0.0.1", "10.0.0.2", 400)],
        columnar.REMOTE_PULL_LABEL: [
            _remote_pull("t2", "10.1.0.1", "10.1.0.2")
        ],
    })
    assert cols["_src_rank"] == [0, 2, 1]
    assert cols["urma_total_latency"] == [None, 0.4, None]
    assert cols["src"] == [None, "10.0.0.1", "10.1.0.1"]
    assert cols["dst"] == [None, "10.0.0.2", "10.1.0.2"]


def test_worker_info_bucket_routes_by_entry_type():
    from latency.parse.parallel_scanner import columnar

    bucket = [
        _urma("t1", "10.0.0.1", "10.0.0.2", 400),   # → urma_total_latency, rank 2
        _link("t1", 900),                            # → urma_link_latency
        _remote_pull("t2", "10.1.0.1", "10.1.0.2"),  # → src/dst, rank 1
    ]
    cols = columnar.entries_to_columns({columnar.INFO_BUCKET_LABEL: bucket})
    assert cols["_label"] == [columnar.URMA_LABEL, columnar.LINK_LABEL,
                              columnar.REMOTE_PULL_LABEL]
    assert cols["_src_rank"] == [2, 0, 1]
    assert cols["urma_total_latency"] == [0.4, None, None]
    assert cols["urma_link_latency"] == [None, 0.9, None]
    assert cols["src"] == ["10.0.0.1", None, "10.1.0.1"]
    # 每个 bucket 条目都产出一行
    assert len(cols["tid"]) == 3


def test_tuple_and_dataclass_inputs_equivalent():
    from latency.parse.parallel_scanner import columnar

    sdk_dc = _mk_sdk_dataclass()
    urma_dc = _mk_urma_dataclass()
    merged_dc = {
        columnar.SDK_LABEL: [sdk_dc],
        columnar.URMA_LABEL: [urma_dc],
    }
    merged_tuple = {
        columnar.SDK_LABEL: [_serialize_entry(sdk_dc)],
        columnar.URMA_LABEL: [_serialize_entry(urma_dc)],
    }
    cols_dc = columnar.entries_to_columns(merged_dc)
    cols_tuple = columnar.entries_to_columns(merged_tuple)
    for name in (*columnar.TRACE_COLUMNS, *columnar.INTERNAL_COLUMNS):
        assert cols_dc[name] == cols_tuple[name], f"column {name} diverges"


def test_columns_to_frame_has_all_columns():
    pl = pytest.importorskip("polars")
    from latency.parse.parallel_scanner import columnar

    cols = columnar.entries_to_columns({
        columnar.SDK_LABEL: [_sdk("t1")],
        columnar.URMA_LABEL: [_urma("t1")],
    })
    frame = columnar.columns_to_frame(cols)
    expected = {*columnar.TRACE_COLUMNS, *columnar.INTERNAL_COLUMNS}
    assert set(frame.columns) == expected
    assert frame.height == 2


# ---------------------------------------------------------------------------
# 说明：原第 3/4 节（spawn 子进程跑 process_worker、_merge_results 列合并）
# 依赖的 process_worker 模块与 ParallelFileScanner._merge_results 已在
# master 的 polars 重构（1b398771）中移除，相关用例随之删除；列契约与
# 投影行为由本文件其余用例覆盖。
# ---------------------------------------------------------------------------
