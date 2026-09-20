"""Partitioned wide reduction keeps the existing trace contract exactly."""

from io import BytesIO
import random

import polars as pl
from polars.testing import assert_frame_equal
import pytest

from latency.parse.parallel_scanner import bounded_trace
from latency.parse.columns import FLOAT_COLUMNS, INT_COLUMNS, OUTPUT_COLUMNS
from latency.parse.labels import (
    CLIENT_RPC_LABEL,
    MASTER_RPC_LABEL,
    QUERY_META_LABEL,
    REMOTE_WORKER_RPC_LABEL,
    SDK_LABEL,
    URMA_LABEL,
    WORKER_ACCESS_LABEL,
)
from latency.parse.parallel_scanner.bounded_trace import build_trace_frame_batched
from latency.parse.parallel_scanner.trace_frame import build_trace_frame


_SCHEMA = {
    name: pl.Float64 if name in FLOAT_COLUMNS else pl.Int64 if name in INT_COLUMNS
    else pl.String
    for name in OUTPUT_COLUMNS
}


def _frame(rows):
    return pl.DataFrame(rows, schema=_SCHEMA)


def _batches(frame, width=7):
    for start in range(0, frame.height, width):
        yield frame.slice(start, width)


def _mixed_rows():
    randomizer = random.Random(20260918)
    labels = [
        SDK_LABEL, WORKER_ACCESS_LABEL, CLIENT_RPC_LABEL, URMA_LABEL,
        MASTER_RPC_LABEL, REMOTE_WORKER_RPC_LABEL, QUERY_META_LABEL,
    ]
    rows = []
    for cycle in range(6):
        for tid in range(37):
            label = labels[(tid + cycle) % len(labels)]
            row = {
                "tid": f"trace-{tid:03}", "_label": label,
                "_src_rank": 2 if label == URMA_LABEL else 1,
                "total_ms": 10.0 if label == SDK_LABEL else None,
                "total_latency": 10.0 if label == SDK_LABEL else None,
                "worker_total_latency": 7.0 if label == WORKER_ACCESS_LABEL else None,
                "timestamp": f"stamp-{cycle}-{tid}",
                # Values exceed the inline StringView capacity so list
                # aggregation also exercises external string buffers.
                "pod_ip": f"2001:db8:abcd::{cycle % 3}",
                "cluster_name": f"中文-cluster-{cycle % 2}",
            }
            for name, dtype in _SCHEMA.items():
                if name in row:
                    continue
                if randomizer.random() < .3:
                    row[name] = None
                elif dtype == pl.Float64:
                    row[name] = randomizer.choice([.1, .2, 1e16, 4.0, -1e16])
                elif dtype == pl.Int64:
                    row[name] = randomizer.randrange(10)
                else:
                    row[name] = f"{name}-{cycle}-{tid}"
            rows.append(row)
    return rows


@pytest.mark.parametrize("width", [1, 7, 41, 1000])
@pytest.mark.parametrize("deterministic", ["1", "0"])
@pytest.mark.parametrize("compression", [False, True])
def test_all_fields_match_full_reducer_across_batches(
    monkeypatch, width, deterministic, compression,
):
    monkeypatch.setenv("WITTY_UB_DETERMINISTIC", deterministic)
    frame = _frame(_mixed_rows())
    reference = build_trace_frame(frame)
    actual = build_trace_frame_batched(
        _batches(frame, width), frame.height, target_partition_rows=37,
        compression=compression,
    )
    if deterministic == "0":
        reference, actual = reference.sort("tid"), actual.sort("tid")
    assert_frame_equal(actual, reference, check_exact=True)


def test_cross_batch_first_rank_lists_and_float_sum(monkeypatch):
    monkeypatch.setenv("WITTY_UB_DETERMINISTIC", "1")
    rows = [
        {"tid": "same", "_label": WORKER_ACCESS_LABEL, "_src_rank": 0,
         "worker_total_latency": 1., "_elapsed_us": 1e16,
         "timestamp": "worker-time", "pod_ip": "z", "cluster_name": "b"},
        {"tid": "same", "_label": CLIENT_RPC_LABEL, "_src_rank": 0,
         "_rpc_e2e_us": None},
        {"tid": "same", "_label": URMA_LABEL, "_src_rank": 2,
         "src": "first-source", "dst": None, "pod_ip": "a"},
        {"tid": "same", "_label": WORKER_ACCESS_LABEL, "_src_rank": 0,
         "_elapsed_us": 1.},
        {"tid": "same", "_label": SDK_LABEL, "_src_rank": 0,
         "total_ms": 2., "total_latency": 2., "_elapsed_us": 2000.,
         "timestamp": "sdk-time", "pod_ip": "z", "cluster_name": "a"},
        {"tid": "same", "_label": URMA_LABEL, "_src_rank": 2,
         "src": "later-source", "dst": "later-destination"},
        {"tid": "same", "_label": WORKER_ACCESS_LABEL, "_src_rank": 0,
         "_elapsed_us": -1e16},
        {"tid": "same", "_label": CLIENT_RPC_LABEL, "_src_rank": 0,
         "_rpc_e2e_us": 31.},
        {"tid": "other", "_label": SDK_LABEL, "_src_rank": 0,
         "total_ms": 3., "total_latency": 3.},
    ]
    frame = _frame(rows)
    actual = build_trace_frame_batched(
        _batches(frame, 2), frame.height, target_partition_rows=3,
    )
    assert_frame_equal(actual, build_trace_frame(frame), check_exact=True)
    trace = actual.filter(pl.col("tid") == "same").row(0, named=True)
    assert trace["src"] == "first-source"
    assert trace["dst"] == ""
    assert trace["timestamp"] == "sdk-time"
    assert trace["pod_ip"] == ["a", "z"]
    assert trace["cluster_name"] == ["a", "b"]
    assert trace["__ce0"] is None
    assert trace["__ce1"] == 31.
    assert trace["__wsum"] == 0.


@pytest.mark.parametrize("width", [777, 8192])
def test_long_float_sums_keep_exact_order_across_chunks(width):
    rows = []
    for index in range(12_000):
        label = (
            SDK_LABEL if index < 3 else WORKER_ACCESS_LABEL
            if index % 2 else CLIENT_RPC_LABEL
        )
        rows.append({
            "tid": f"t-{index % 3}", "_label": label, "_src_rank": 0,
            "total_ms": 10. if label == SDK_LABEL else None,
            "total_latency": 10. if label == SDK_LABEL else None,
            "_elapsed_us": [1e16, 1., -1e16, .3][index % 4],
            "_rpc_e2e_us": [.3, 1e16, 1., -1e16][index % 4],
        })
    frame = _frame(rows)
    actual = build_trace_frame_batched(
        _batches(frame, width), frame.height, target_partition_rows=5000,
    )
    assert_frame_equal(actual, build_trace_frame(frame), check_exact=True)


def test_scalar_materials_preserve_legacy_list_reduction():
    """Changing list.sum to group.sum silently changes floating-point bits."""
    from latency.parse.parallel_scanner.trace_frame import _yuanrong_agg_exprs

    randomizer = random.Random(9)
    rows = [
        {
            "tid": str(index % 23),
            "_label": WORKER_ACCESS_LABEL if index % 2 else CLIENT_RPC_LABEL,
            "_elapsed_us": randomizer.choice([.1, .3, 1e16, -1e16, None]),
            "_rpc_e2e_us": randomizer.choice([.1, .3, 1e16, -1e16, None]),
        }
        for index in range(10_000)
    ]
    frame = _frame(rows)
    old = frame.group_by("tid").agg(
        worker=pl.col("_elapsed_us").filter(pl.col("_label") == WORKER_ACCESS_LABEL).implode(),
        client=pl.col("_rpc_e2e_us").filter(pl.col("_label") == CLIENT_RPC_LABEL).implode(),
    ).select(
        "tid",
        pl.col("worker").list.sum().alias("__wsum"),
        pl.col("client").list.sum().alias("__ce2esum"),
        pl.col("client").list.first().alias("__ce0"),
        pl.col("client").list.last().alias("__ce1"),
    ).sort("tid")
    actual = frame.group_by("tid").agg(**_yuanrong_agg_exprs())
    assert_frame_equal(actual.select(old.columns).sort("tid"), old, check_exact=True)


def test_nullable_endpoint_rank_preserves_null_first_order():
    frame = _frame([
        {"tid": "t", "_label": SDK_LABEL, "_src_rank": 3,
         "total_ms": 1., "total_latency": 1., "src": "ranked"},
        {"tid": "t", "_label": URMA_LABEL, "_src_rank": None,
         "src": "unranked"},
    ])
    expected = frame.group_by("tid").agg(
        pl.col("src").sort_by("_src_rank", descending=True).first()
    )
    assert_frame_equal(build_trace_frame(frame).select("tid", "src"), expected)


@pytest.mark.parametrize("partition_rows", [1, 100])
def test_invalid_traces_and_worker_fallback(partition_rows):
    frame = _frame([
        {"tid": "worker", "_label": WORKER_ACCESS_LABEL, "_src_rank": 0,
         "worker_total_latency": 4., "timestamp": "worker-ts"},
        {"tid": "negative", "_label": SDK_LABEL, "_src_rank": 0,
         "total_ms": -1.},
        {"tid": "empty-latency", "_label": SDK_LABEL, "_src_rank": 0},
        {"tid": "", "_label": SDK_LABEL, "_src_rank": 0, "total_ms": 2.},
        {"tid": None, "_label": SDK_LABEL, "_src_rank": 0, "total_ms": 2.},
    ])
    actual = build_trace_frame_batched(
        _batches(frame, 2), frame.height, target_partition_rows=partition_rows,
    )
    assert_frame_equal(actual, build_trace_frame(frame), check_exact=True)
    assert actual["tid"].to_list() == ["worker"]
    assert actual["total_ms"].to_list() == [4.]


def test_small_inputs_skip_compression(monkeypatch):
    frame = _frame(_mixed_rows())

    def unexpected_write(*args, **kwargs):
        pytest.fail("small inputs should not serialize their rows")

    monkeypatch.setattr(pl.DataFrame, "write_ipc", unexpected_write)
    actual = build_trace_frame_batched(_batches(frame), frame.height)
    assert_frame_equal(actual, build_trace_frame(frame), check_exact=True)


def test_payloads_are_sparse_and_use_only_memory(monkeypatch):
    original_write = pl.DataFrame.write_ipc
    original_read = pl.read_ipc
    written = []

    def write_sparse(frame, file, **kwargs):
        assert file is None
        assert kwargs["compression"] == "lz4"
        assert "_resp_msg" not in frame.columns
        assert "create_latency" not in frame.columns
        assert "host" not in frame.columns
        assert all(frame[name].null_count() != frame.height for name in frame.columns)
        written.append(frame.height)
        return original_write(frame, file, **kwargs)

    def read_memory(source, **kwargs):
        assert isinstance(source, BytesIO)
        return original_read(source, **kwargs)

    monkeypatch.setattr(pl.DataFrame, "write_ipc", write_sparse)
    monkeypatch.setattr(pl, "read_ipc", read_memory)
    frame = _frame([
        {"tid": f"t-{index}", "_label": SDK_LABEL, "_src_rank": 0,
         "total_ms": float(index), "total_latency": float(index),
         "_resp_msg": "unused very large response" * 100}
        for index in range(10)
    ])
    actual = build_trace_frame_batched(
        _batches(frame, 3), frame.height, target_partition_bytes=100,
        compression_threshold_bytes=1,
    )
    assert sum(written) == frame.height
    assert_frame_equal(actual, build_trace_frame(frame), check_exact=True)


def test_native_partitions_restore_categorical_columns_before_reducing(monkeypatch):
    original_restore = bounded_trace._restore_columns
    original_build = bounded_trace.build_trace_frame
    stored_columns = set()

    def restore(parts, schema):
        for part in parts:
            assert part.schema["tid"] == pl.String
            stored_columns.update(
                name for name, dtype in part.schema.items() if dtype == pl.Categorical
            )
        return original_restore(parts, schema)

    def build(frame):
        assert not any(dtype == pl.Categorical for dtype in frame.dtypes)
        return original_build(frame)

    def unexpected_write(*args, **kwargs):
        pytest.fail("compression=False should keep native partitions")

    monkeypatch.setattr(bounded_trace, "_restore_columns", restore)
    monkeypatch.setattr(bounded_trace, "build_trace_frame", build)
    monkeypatch.setattr(pl.DataFrame, "write_ipc", unexpected_write)
    frame = _frame(_mixed_rows())
    actual = build_trace_frame_batched(
        _batches(frame), frame.height, target_partition_rows=37,
        compression=False, compression_threshold_bytes=1,
    )
    assert {"_label", "pod_ip", "cluster_name"}.issubset(stored_columns)
    assert_frame_equal(actual, build_trace_frame(frame), check_exact=True)


def test_without_yuanrong_columns():
    frame = _frame(_mixed_rows()).drop(
        "_elapsed_us", "_rpc_e2e_us", "_rpc_server_exec_us", "_rpc_network_us",
    )
    actual = build_trace_frame_batched(
        _batches(frame), frame.height, target_partition_rows=37,
    )
    assert_frame_equal(actual, build_trace_frame(frame), check_exact=True)


@pytest.mark.parametrize("batches", [[], [_frame([])], [_frame([]), _frame([])]])
def test_empty_input_preserves_schema(batches):
    assert_frame_equal(
        build_trace_frame_batched(iter(batches), 0),
        build_trace_frame(_frame([])),
        check_exact=True,
    )


@pytest.mark.parametrize("kwargs", [
    {"expected_rows": -1},
    {"expected_rows": 0, "target_partition_rows": 0},
    {"expected_rows": 0, "target_partition_bytes": 0},
    {"expected_rows": 0, "compression_threshold_bytes": 0},
])
def test_invalid_partition_targets(kwargs):
    with pytest.raises(ValueError):
        build_trace_frame_batched([], **kwargs)
