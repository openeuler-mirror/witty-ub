"""Scanner ownership and batch-order regressions for the two-pass parser."""
import gzip
from unittest.mock import patch

import polars as pl
from polars.testing import assert_frame_equal
import pytest

from latency.parse import ClientInfoParser, SdkAccessLogParser, WorkerAccessLogParser, WorkerInfoParser
from latency.parse.columns import LIGHT_COLUMNS
from latency.parse.parallel_scanner import scan_vector as scan
from latency.parse.parallel_scanner.memory_scan import iter_wide
from latency.parse.parallel_scanner.trace_frame import build_trace_frame_light


def _line(tid, message):
    return f"2026-05-10T12:00:05.934807 | I | source.cpp:1 | pod | 1:2 | {tid} | cluster | {message}\n"


def _access(tid, elapsed=12000):
    return _line(tid, f"0 | DS_KV_CLIENT_GET | {elapsed} | 4096 | {{Object_key:{tid}}} | ")


def _rpc(tid, elapsed=900):
    return _line(tid, f"[ZMQ_RPC_FRAMEWORK_SLOW] trace_id={tid} framework_us=200 e2e_us={elapsed} client_req_framework_us=50 remote_processing_us=700 client_rsp_framework_us=50 server_req_queue_us=100 server_exec_us=500 server_rsp_queue_us=100 network_residual_us=100")


def _sources(tmp_path):
    parsers = [SdkAccessLogParser(), ClientInfoParser(), WorkerAccessLogParser(), WorkerInfoParser()]
    files = []
    for index in range(7):
        # Shared access/info routing, reverse insertion order, and repeated
        # traces make batch boundaries exercise first/last and RPC sum order.
        path = tmp_path / f"{6-index}.log"
        tid = f"0000000{index % 3}-9094-41bf-8204-e6b2ff438207"
        text = (_access(tid, 12000 + index) + _rpc(tid, 900 + index)
                + _line(tid, "[URMA_ELAPSED_TOTAL] cost 0.2ms, src address: 10.0.0.1, dst address: 10.0.0.2, urma_inflight_wr_count:3")
                + _line(tid, "ProcessGetObjectRequest: 3.5ms")
                + _line(tid, "ordinary irrelevant payload" * (index + 1)))
        if index == 6:
            path = path.with_suffix(".log.gz")
            with gzip.open(path, "wt") as stream:
                stream.write(text)
        else:
            path.write_text(text)
        files.append([str(path), [0, 1, 3]])
    return files, parsers


@pytest.mark.parametrize("progress", [False, True])
@pytest.mark.parametrize("sparse", [False, True])
def test_wide_batches_preserve_family_file_and_row_order(tmp_path, progress, sparse):
    files, parsers = _sources(tmp_path)
    cb = (lambda _: None) if progress else None
    with patch.object(scan.uuid, "uuid4", return_value="stable-file-id"):
        full, skipped, _, _ = scan.scan_frame(files, parsers, progress_cb=cb)
        light, _, ctx, _ = scan.scan_frame(files, parsers, light=True, progress_cb=cb)
    assert skipped == []
    assert light.columns == list(LIGHT_COLUMNS)
    assert ctx.light_rows.columns == ["tid", "__row"]
    assert ctx.lines.schema["__file"] == pl.Categorical
    wanted = light["tid"].unique().sort().head(2)
    expected = full.filter(pl.col("tid").is_in(wanted.implode()))
    direct = scan.materialize_wide(ctx, wanted)
    assert_frame_equal(direct, expected)
    parts = list(iter_wide(ctx, wanted, batch_rows=3, sparse=sparse))
    actual = pl.concat([scan._normalize(part) for part in parts])
    if sparse:
        # Sparse production batches omit generated response text; all numeric
        # RPC inputs and every field consumed by the trace reducer stay exact.
        expected = expected.drop("_resp_msg")
        actual = actual.drop("_resp_msg")
    assert_frame_equal(actual, expected)
    assert ctx.lines is None
    assert ctx.light_rows is None


def test_empty_subset_consumes_context_and_reusable_mode_does_not(tmp_path):
    files, parsers = _sources(tmp_path)
    light, _, ctx, _ = scan.scan_frame(files, parsers, light=True)
    assert list(iter_wide(ctx, [], consume=False)) == []
    assert ctx.lines is not None
    first = list(iter_wide(ctx, light["tid"], consume=False, batch_rows=10))
    second = list(iter_wide(ctx, light["tid"], consume=False, batch_rows=10))
    assert_frame_equal(pl.concat(first), pl.concat(second))
    assert list(iter_wide(ctx, [])) == []
    assert ctx.lines is None
    assert ctx.light_rows is None


def test_bad_files_sanitized_instead_of_skipped(tmp_path):
    files, parsers = _sources(tmp_path)
    broken = tmp_path / "broken.log"
    broken.write_bytes(b"2026 DS_KV_CLIENT_GET \xff\n")
    files.append([str(broken), [0]])
    rows, skipped, ctx, sanitized = scan.scan_frame(files, parsers, light=True)
    assert rows.height > 0
    assert skipped == []
    assert sanitized == [str(broken)]
    assert str(broken) in ctx.log_ids


def test_sanitization_failure_falls_back_to_skip(tmp_path, monkeypatch):
    files, parsers = _sources(tmp_path)
    broken = tmp_path / "broken.log"
    broken.write_bytes(b"2026 DS_KV_CLIENT_GET \xff\n")
    files.append([str(broken), [0]])
    monkeypatch.setattr(scan, "_try_sanitize_utf8", lambda _path: None)
    rows, skipped, ctx, sanitized = scan.scan_frame(files, parsers, light=True)
    assert rows.height > 0
    assert sanitized == []
    assert [path for path, reason in skipped] == [str(broken)]
    assert str(broken) not in ctx.log_ids
    assert str(broken) not in ctx.lines["__file"].to_list()


def test_access_projection_keeps_explicit_numeric_locator():
    parser = SdkAccessLogParser()
    source = pl.DataFrame({"line": [_access("trace-1"), _access("trace-2")], "__file": ["access.log"] * 2, "__row": [10, 35]})
    rows = scan.access_label_columns(source, ["access.log"], [[parser]], file_rank={"access.log": 0}, light=True)
    assert rows["__row"].to_list() == [10, 35]


@pytest.mark.parametrize("sparse", [False, True])
def test_direct_rpc_captures_keep_existing_response_key_precedence(sparse):
    # Access historically takes the first key from formatted response text;
    # INFO takes the last valid key. Even unusual trace text preserves this.
    line = _rpc("trace-1").replace(
        "trace_id=trace-1", "trace_id=prefix,e2e_us=13,server_exec_us=-0,"
    )
    source = pl.DataFrame({"line": [line], "__file": ["shared.log"]})
    kwargs = {"file_rank": {"shared.log": 0}, "sparse": sparse}
    access = scan.access_label_columns(source, ["shared.log"], [[ClientInfoParser()]], **kwargs)
    info = scan.info_label_columns(source, ["shared.log"], [[WorkerInfoParser()]], **kwargs)
    assert access.select("_rpc_e2e_us", "_rpc_server_exec_us", "_rpc_network_us").row(0) == (13., -0., 100.)
    assert info.select("_rpc_e2e_us", "_rpc_server_exec_us", "_rpc_network_us").row(0) == (900., 500., 100.)


def test_rpc_fields_embedded_in_sdk_slow_items_are_preserved():
    line = _line("trace-1", "totalCost:10.0ms, inflightRemoteGet:2 exceed 1ms: {item:1.2, e2e_us=7, network_residual_us=9}")
    source = pl.DataFrame({"line": [line], "__file": ["info.log"]})
    for sparse in (False, True):
        rows = scan.info_label_columns(
            source, ["info.log"], [[WorkerInfoParser()]],
            file_rank={"info.log": 0}, sparse=sparse,
        )
        assert rows.select("_rpc_e2e_us", "_rpc_network_us").row(0) == (7., 9.)


@pytest.mark.parametrize("progress", [False, True])
def test_light_batches_match_unsliced_projection_with_reordered_sources(tmp_path, progress):
    files, parsers = _sources(tmp_path)
    paths = [path for path, _ in files]
    # Ensure progress-mode physical input order differs from parser file rank;
    # each source is shared by access and INFO parsers, and traces span files.
    read_groups = [[paths[index] for index in group] for group in ((2, 5, 0), (4, 1, 6, 3))]
    callback = (lambda _: None) if progress else None
    with (
        patch.object(scan.uuid, "uuid4", return_value="stable-file-id"),
        patch.object(scan, "_split_paths_by_size", return_value=read_groups),
    ):
        with patch.object(scan, "_LIGHT_BATCH_ROWS", 1_000_000):
            expected, skipped, expected_ctx, _ = scan.scan_frame(
                files, parsers, light=True, progress_cb=callback
            )
        with patch.object(scan, "_LIGHT_BATCH_ROWS", 3):
            actual, actual_skipped, ctx, _ = scan.scan_frame(
                files, parsers, light=True, progress_cb=callback
            )
    assert actual_skipped == skipped == []
    assert_frame_equal(actual, expected)
    assert_frame_equal(ctx.light_rows, expected_ctx.light_rows)
    assert_frame_equal(ctx.lines, expected_ctx.lines)
    if progress:
        assert ctx.lines["__file"].cast(pl.String).unique(maintain_order=True).to_list() != paths
    merged = build_trace_frame_light(actual).sort("tid")
    assert_frame_equal(merged, build_trace_frame_light(expected).sort("tid"))
    first_tid = "00000000-9094-41bf-8204-e6b2ff438207"
    assert merged.filter(pl.col("tid") == first_tid)["total_ms"].item() == 12.0
    # The batch row offsets must still locate the same original source records
    # when details are subsequently requested.
    wanted = merged["tid"].head(2)
    assert_frame_equal(
        scan.materialize_wide(ctx, wanted),
        scan.materialize_wide(expected_ctx, wanted),
    )


def test_metric_free_candidates_never_change_light_aggregation(tmp_path):
    files, parsers = _sources(tmp_path)
    tid = "00000000-9094-41bf-8204-e6b2ff438207"
    path = tmp_path / "invalid-info.log"
    path.write_text(
        _line(tid, "ProcessGetObjectRequest: invalidms")
        + _line("no-access", "ProcessGetObjectRequest: 3.5ms")
        + _line("worker-only", "0 | DS_POSIX_PUBLISH | 4200 | 4096 | {} | ")
    )
    files.append([str(path), [2, 3]])
    rpc_path = tmp_path / "invalid-client-info.log"
    rpc_path.write_text(
        _line(tid, "[ZMQ_RPC_FRAMEWORK_SLOW] remote_processing_us=invalid")
        + _rpc(tid).replace("2026-05-10T12:00:05.934807", "2026-bad-timestamp")
    )
    files.append([str(rpc_path), [1]])
    with patch.object(scan.uuid, "uuid4", return_value="stable-file-id"):
        full, _, _, _ = scan.scan_frame(files, parsers)
        light, _, ctx, _ = scan.scan_frame(files, parsers, light=True)
    assert light.height < full.height
    assert_frame_equal(
        build_trace_frame_light(light).sort("tid"),
        build_trace_frame_light(full.select(LIGHT_COLUMNS)).sort("tid"),
    )
    # Deferred invalid candidates must still pass exact wide validation; an
    # explicit request for the metric-free trace remains supported as well.
    wanted = [tid, "no-access", "worker-only"]
    actual = pl.concat(list(iter_wide(ctx, wanted, batch_rows=2)))
    assert_frame_equal(actual, full.filter(pl.col("tid").is_in(wanted)))


def test_info_classification_includes_the_original_keyword_gate():
    from latency.parse.keywords import ALL_KEYWORDS
    from latency.parse.parallel_scanner.scan_vector_info import _CHAIN

    assert tuple(keyword for keyword, _ in _CHAIN if keyword is not None) == tuple(ALL_KEYWORDS)


@pytest.mark.parametrize("light", [False, True])
def test_unrelated_records_do_not_change_info_timestamp_inference(light):
    # A shared file can pass the scanner's SDK keyword gate for a record that
    # is not an INFO category. Its malformed timestamp must not participate in
    # INFO's inferred datetime format or suppress the following valid record.
    tid = "00000000-9094-41bf-8204-e6b2ff438207"
    unrelated = _access(tid).replace("2026-05-10T12:00:05.934807", "2026-bad-timestamp")
    valid = _line(tid, "[URMA_ELAPSED_TOTAL] cost 0.2ms, src address: 10.0.0.1, dst address: 10.0.0.2, urma_inflight_wr_count:3")
    kwargs = {"file_rank": {"shared.log": 0}, "light": light}
    parsers = [[WorkerInfoParser()]]
    frame = pl.DataFrame({"line": [unrelated, valid], "__file": ["shared.log"] * 2})
    actual = scan.info_label_columns(frame, ["shared.log"], parsers, **kwargs)
    expected = scan.info_label_columns(frame.tail(1), ["shared.log"], parsers, **kwargs)
    assert expected.height == 1
    assert_frame_equal(actual.drop("__row"), expected.drop("__row"))


def test_bad_info_timestamp_at_batch_start_does_not_drop_valid_following_rows(tmp_path):
    valid = _line("trace-1", "[URMA_ELAPSED_TOTAL] cost 0.2ms, src address: 10.0.0.1, dst address: 10.0.0.2, urma_inflight_wr_count:3")
    bad = valid.replace("2026-05-10T12:00:05.934807", "2026-bad-timestamp")
    path = tmp_path / "worker-info.log"
    path.write_text(valid + valid + bad + bad + valid)
    files = [[str(path), [0]]]
    parsers = [WorkerInfoParser()]
    with patch.object(scan, "_LIGHT_BATCH_ROWS", 1_000_000):
        expected, _, expected_ctx, _ = scan.scan_frame(files, parsers, light=True)
    with patch.object(scan, "_LIGHT_BATCH_ROWS", 3):
        actual, _, ctx, _ = scan.scan_frame(files, parsers, light=True)
    assert expected.height == 3
    assert_frame_equal(actual, expected)
    assert_frame_equal(ctx.light_rows, expected_ctx.light_rows)


@pytest.mark.parametrize("batch_rows", [1, 3])
def test_info_timestamp_formats_and_calendar_validation_are_batch_independent(tmp_path, batch_rows):
    timestamps = [
        ("2026-bad-timestamp", False),
        ("2026-05-10T12:00:05.934807", True),
        ("2026-02-29 12:00:05", False),
        ("2024-02-29 12:00:05", True),
        ("2026-05-10T12:00:05", True),
        ("2026-05-10 12:00:05.934807", True),
        ("2026-05-10 12:00:05", True),
        ("2026-04-31T00:00:00", False),
        ("2026-05-10T25:00:00", False),
    ]
    message = "[URMA_ELAPSED_TOTAL] cost 0.2ms, src address: 10.0.0.1, dst address: 10.0.0.2, urma_inflight_wr_count:3"
    path = tmp_path / "worker-info.log"
    path.write_text("".join(
        _line(f"trace-{index}", message).replace("2026-05-10T12:00:05.934807", timestamp)
        for index, (timestamp, _) in enumerate(timestamps)
    ))
    files = [[str(path), [0]]]
    parsers = [WorkerInfoParser()]
    with patch.object(scan, "_LIGHT_BATCH_ROWS", 1_000_000):
        expected, _, expected_ctx, _ = scan.scan_frame(files, parsers, light=True)
    with patch.object(scan, "_LIGHT_BATCH_ROWS", batch_rows):
        actual, _, ctx, _ = scan.scan_frame(files, parsers, light=True)
    wanted = [f"trace-{index}" for index, (_, valid) in enumerate(timestamps) if valid]
    assert actual["tid"].to_list() == wanted
    assert_frame_equal(actual, expected)
    assert_frame_equal(ctx.light_rows, expected_ctx.light_rows)
    assert_frame_equal(
        pl.concat(list(iter_wide(ctx, wanted, batch_rows=batch_rows))),
        scan.materialize_wide(expected_ctx, wanted),
    )


@pytest.mark.parametrize("family", ["access", "info"])
@pytest.mark.parametrize("backslash", [False, True])
def test_categorical_path_join_and_trace_fallback_keep_string_path_results(family, backslash):
    fallback = "00000000-9094-41bf-8204-e6b2ff438207"
    path = "worker_10.0.0.1/info.log"
    if backslash:
        path = path.replace("/", "\\")
    if family == "access":
        project, parser = scan.access_label_columns, SdkAccessLogParser()
        def line(header, explicit=""):
            return _access(header).rstrip() + f" payload={fallback} {explicit}\n"
    else:
        project, parser = scan.info_label_columns, WorkerInfoParser()
        def line(header, explicit=""):
            return _line(header, "[URMA_ELAPSED_TOTAL] cost 0.2ms, src address: 10.0.0.1, "
                         f"dst address: 10.0.0.2, urma_inflight_wr_count:3 payload={fallback} {explicit}")
    source = pl.DataFrame({
        "line": [line("header"), line(""), line("header", "trace_id=explicit"),
                 line("", "trace_id=explicit")],
        "__file": [path] * 4,
    })
    kwargs = dict(file_rank={path: 0})
    expected = project(source, [path], [[parser]], **kwargs)
    actual = project(source.with_columns(pl.col("__file").cast(pl.Categorical)),
                     [path], [[parser]], **kwargs)
    assert expected["tid"].to_list() == ["header", fallback, "explicit", "explicit"]
    assert_frame_equal(actual, expected, check_exact=True)


@pytest.mark.parametrize("sparse", [False, True])
def test_info_light_classification_cache_preserves_wide_validation(sparse):
    path = "worker_10.0.0.1/info.log"
    urma = ("[URMA_ELAPSED_TOTAL] cost 0.2ms, src address: 10.0.0.1, "
            "dst address: 10.0.0.2, urma_inflight_wr_count:3")
    lines = [
        # Category priority is independent of textual occurrence order.
        _line("trace-1", "ProcessGetObjectRequest: 3.5ms " + urma),
        _line("", urma),
        _line("trace-2", "src=10.0.0.1, dst=10.0.0.2"),
        _rpc("trace-3"),
        _line("trace-4", "Master query done, cost:bad"),
        _line("trace-5", "ProcessGetObjectRequest: 3.5ms").replace("2026-05", "2026-99"),
        _line("trace-6", "Remote get request: missing endpoints"),
        _line("trace-7", "ordinary unrelated message"),
    ]
    source = pl.DataFrame({"line": lines, "__file": [path] * len(lines)}).with_row_index("__row")
    parsers = [[WorkerInfoParser()]]
    kwargs = {"file_rank": {path: 0}}
    expected = scan.info_label_columns(source, [path], parsers, sparse=sparse, **kwargs)
    light = scan.info_label_columns(
        source, [path], parsers, light=True, defer_unused=True,
        cache_classification=True, **kwargs,
    )
    assert light.schema["__info_cat"] == pl.UInt8
    cache = light.select("__row", "__info_cat", pl.col("tid").alias("__info_tid"))
    cached_source = source.join(cache, on="__row", how="left")
    actual = scan.info_label_columns(cached_source, [path], parsers, sparse=sparse, **kwargs)
    assert_frame_equal(actual, expected, check_exact=True)
    assert expected["tid"].to_list() == ["trace-1", "", "trace-2", "trace-3"]
