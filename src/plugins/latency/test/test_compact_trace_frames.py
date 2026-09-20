"""Compact trace storage and bounded detail COPY preserve output semantics."""

import polars as pl
import pytest

from latency.task.worker.kv_cache_log_parse_worker import KVCacheLogParseWorker


def test_detail_frame_uses_threshold_without_materializing_anomaly_set():
    class ForbiddenIds:
        def __iter__(self):
            raise AssertionError("anomaly ids must not be materialized")

        def __bool__(self):
            raise AssertionError("anomaly ids must not be inspected")

    detail = pl.DataFrame(
        {
            "tid": ["top", "anomaly", "normal"],
            "total_ms": [10.0, 8.0, 1.0],
            "total_latency": [10.0, 8.0, 1.0],
            "op": ["GET", "GET", "GET"],
            "src": ["", "", ""],
            "dst": ["", "", ""],
        }
    )
    frame = KVCacheLogParseWorker._build_detail_frame(
        detail,
        top1000_tids={"top"},
        anomalous_only_tids=ForbiddenIds(),
        anomalous_tids=ForbiddenIds(),
        threshold_ms=5.0,
    )

    assert frame["tid"].to_list() == ["top", "anomaly"]
    assert frame["is_anomalous"].to_list() == [True, True]

def test_sparse_trace_storage_gathers_nullable_rows_without_expanding_all_traces():
    from latency.parse.trace_frames import TraceFrames
    from polars.testing import assert_frame_equal

    light = pl.DataFrame({"tid": [str(i) for i in range(20_000)], "total_ms": [1.] * 20_000})
    wide = pl.DataFrame({"tid": ["17", "3"], **{f"metric_{i}": [17., 3.] for i in range(40)}})
    compact = TraceFrames.from_frames(light, wide)
    expected = light.join(wide, on="tid", how="left", maintain_order="left")
    assert_frame_equal(compact.enrich(compact.light), expected)
    selection = compact.light[[17, 1, 3]]
    assert_frame_equal(compact.enrich(selection), expected[[17, 1, 3]])
    assert compact.light.estimated_size() + compact.wide.estimated_size() < expected.estimated_size() / 4
    assert "_wide_row" not in compact.enrich(selection).columns

def test_compact_trace_detail_and_bucket_parity(monkeypatch):
    from polars.testing import assert_frame_equal
    from latency.parse.trace_frames import TraceFrames
    from latency.parse.parallel_scanner.trace_frame import build_trace_frame, _LIGHT_TRACE_COLUMNS
    from latency.parse.parallel_scanner.columnar import entries_to_columns
    from latency.bucket.statistics import compute_bucket_stats_from_frame
    from test_trace_frame import _fixture_raw

    full = build_trace_frame(entries_to_columns(_fixture_raw()))
    compact = TraceFrames.from_frames(full.select(_LIGHT_TRACE_COLUMNS), full)
    expected_buckets = compute_bucket_stats_from_frame(full)
    from latency.bucket import representatives
    compact.bucket_representatives = representatives.select_bucket_representatives(compact.light)

    def unexpected_selection(*args, **kwargs):
        raise AssertionError("bucket writes must reuse the parser's representative selection")

    monkeypatch.setattr(representatives, "select_bucket_representatives", unexpected_selection)
    actual_buckets = compute_bucket_stats_from_frame(compact.light, trace_details=compact)
    for granularity in expected_buckets:
        assert_frame_equal(actual_buckets[granularity], expected_buckets[granularity])

    from latency.task.worker import kv_cache_log_parse_worker as worker_module
    monkeypatch.setattr(worker_module, "_utc_now_str", lambda: "2026-01-01 00:00:00.000000")
    args = dict(top1000_tids={"t1"}, threshold_ms=2.0, src_dst_to_agg_id_map={},
                log_file_id="log", anomalous_only_count=2, batch_size=1)
    expected = list(KVCacheLogParseWorker._iter_detail_frames(full, **args))
    actual = list(KVCacheLogParseWorker._iter_detail_frames(compact.light, trace_details=compact, **args))
    assert len(expected) == len(actual)
    for left, right in zip(actual, expected):
        assert_frame_equal(left, right)

def test_compact_trace_omits_typed_null_buffers_and_restores_schema():
    from latency.parse.trace_frames import TraceFrames
    from polars.testing import assert_frame_equal

    light = pl.DataFrame({"tid": ["a", "b"]})
    wide = pl.DataFrame({
        "tid": ["b"],
        "metric": pl.Series([None], dtype=pl.Float64),
        "pod_ip": pl.Series([None], dtype=pl.List(pl.String)),
    })
    compact = TraceFrames.from_frames(light, wide)
    assert compact.wide.width == 0
    expected = light.join(wide, on="tid", how="left").select("tid", "pod_ip", "metric")
    assert_frame_equal(compact.enrich(compact.light), expected)
    assert_frame_equal(compact.enrich(compact.light.head(0)), expected.head(0))


def test_detached_trace_text_preserves_nullable_lists_and_unicode():
    from polars.testing import assert_frame_equal
    from latency.parse.trace_frames import detach_trace_strings

    frame = pl.DataFrame({
        "tid": ["中文-trace-" * 8, None, ""],
        "pod_ip": [["2001:db8:abcd::1", None, ""], None, []],
        "latency": [1.0, None, 0.0],
    })
    assert_frame_equal(detach_trace_strings(frame), frame)


@pytest.mark.parametrize("batch_size", [1, 3, 50_000])
def test_detail_batches_match_original_order_values_and_timestamps(monkeypatch, batch_size):
    from polars.testing import assert_frame_equal
    from latency.parse.parallel_scanner.columnar import entries_to_columns
    from latency.parse.parallel_scanner.trace_frame import build_trace_frame, _yuanrong_from_grouped
    from latency.task.worker import kv_cache_log_parse_worker as module
    from test_trace_frame import _fixture_raw

    frame = build_trace_frame(entries_to_columns(_fixture_raw()))
    top, anomalies = {"t1", "t4"}, {"t2", "t3"}
    aggregate_ids = {("", "", "GET"): "group", ("10.0.0.1", "10.0.0.2", "GET"): "urma"}
    monkeypatch.setattr(module, "_utc_now_str", lambda: "2026-01-01 00:00:00.000000")
    expected = KVCacheLogParseWorker._build_detail_payload(
        _yuanrong_from_grouped(frame), top, anomalies, anomalies, aggregate_ids, "log"
    )
    batches = list(KVCacheLogParseWorker._iter_detail_frames(
        frame, top, 2.0, aggregate_ids, "log", 2, batch_size=batch_size
    ))
    assert all(0 < part.height <= batch_size for part in batches)
    assert_frame_equal(pl.concat(batches), expected)


@pytest.mark.asyncio
@pytest.mark.parametrize("fail", [False, True])
async def test_bounded_detail_copy_uses_one_transaction_and_closes_on_failure(monkeypatch, fail):
    from contextlib import asynccontextmanager
    from types import SimpleNamespace
    from latency.database.engine import PGManager
    from latency.task.worker import kv_cache_log_parse_worker as module

    events = []
    driver = SimpleNamespace()

    class Connection:
        async def get_raw_connection(self):
            return SimpleNamespace(driver_connection=driver)

    @asynccontextmanager
    async def connection():
        events.append("begin")
        try:
            yield Connection()
        except Exception:
            events.append("rollback")
            raise
        else:
            events.append("commit")

    def frames():
        try:
            for i in range(3):
                events.append(f"build{i}")
                yield pl.DataFrame({"tid": [str(i)]})
        finally:
            events.append("close")

    calls = []

    async def copy(table, *, records, columns):
        calls.append(True)
        assert table == 'log_parse_result'
        assert columns == ['trace_id']
        assert not isinstance(records, list)
        count = 0
        for (tid,) in records:
            events.append(f"copy{tid}")
            if fail and tid == "1":
                raise RuntimeError("COPY failed")
            count += 1
        return f"COPY {count}"

    driver.copy_records_to_table = copy
    monkeypatch.setattr(PGManager, "connection", connection)
    monkeypatch.setattr(module, "LOG_PARSE_RESULT_SPEC", module.LOG_PARSE_RESULT_SPEC.with_columns(("trace_id",)))
    if fail:
        with pytest.raises(RuntimeError, match="COPY failed"):
            await KVCacheLogParseWorker._store_detail_frames(frames())
        assert events == ["begin", "build0", "copy0", "build1", "copy1", "rollback", "close"]
    else:
        assert await KVCacheLogParseWorker._store_detail_frames(frames()) == 3
        assert events == ["begin", "build0", "copy0", "build1", "copy1", "build2", "copy2", "close", "commit"]
    assert calls == [True]


@pytest.mark.asyncio
async def test_streamed_details_and_aggregate_writes_remain_concurrent(monkeypatch):
    import asyncio
    from types import SimpleNamespace
    from latency.common.stage_timing import StageTimer
    from latency.task.worker import kv_cache_log_parse_worker as module

    aggregates_started = asyncio.Event()
    arrivals = []

    async def details(frames, **kwargs):
        arrivals.append("detail")
        await asyncio.wait_for(aggregates_started.wait(), timeout=1)
        return 1

    async def aggregate(_rows):
        arrivals.append("aggregate")
        if arrivals.count("aggregate") == 2:
            aggregates_started.set()

    monkeypatch.setattr(KVCacheLogParseWorker, "_store_detail_frames", details)
    monkeypatch.setattr(module.SrcDstAggregatedEventPGManager, "add_aggregated_events", aggregate)
    monkeypatch.setattr(module.TimeWindowAggregatedEventPGManager, "add_events", aggregate)
    assert await KVCacheLogParseWorker.store_result(
        None, [SimpleNamespace()], [SimpleNamespace()], detail_frames=iter(()), stage_timer=StageTimer()
    )
    assert arrivals == ["detail", "aggregate", "aggregate"]


@pytest.mark.asyncio
async def test_copy_releases_previous_python_records_before_building_next_batch(monkeypatch):
    import weakref
    from latency.database.managers import log_parse_result_bulk as bulk

    class Records(list):
        pass

    original = bulk.build_records
    previous = None
    seen = []
    timestamps = []

    def build(frame, spec, **kwargs):
        nonlocal previous
        assert previous is None or previous() is None
        records, columns = original(frame, spec, **kwargs)
        records = Records(records)
        previous = weakref.ref(records)
        timestamps.append(kwargs["created_at"])
        return records, columns

    class Connection:
        async def copy_records_to_table(self, table, *, records, columns):
            assert table == "log_parse_result" and columns == ["trace_id"]
            seen.extend(row[0] for row in records)

    monkeypatch.setattr(bulk, "build_records", build)
    result = await bulk.copy_dataframe(
        pl.DataFrame({"tid": ["a", "b", "c", "d", "e"]}),
        bulk.CopySpec("log_parse_result", ("trace_id",), source_map={"trace_id": "tid"}),
        batch_size=2, pg_conn=Connection(),
    )
    assert result.rows == 5 and result.batches == 3
    assert seen == ["a", "b", "c", "d", "e"]
    assert previous() is None
    assert timestamps[0] == timestamps[1] == timestamps[2]
