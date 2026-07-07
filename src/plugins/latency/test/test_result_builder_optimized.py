import asyncio
from dataclasses import asdict, fields
from datetime import datetime, timedelta, timezone

from latency.ENUM.ds_log import EntryType
from latency.database.managers import log_parse_result as log_parse_result_manager_module
from latency.database.managers.log_parse_result import (
    LogParseResultManager,
    _can_use_minimal_insert,
    _can_use_sparse_insert,
    _log_parse_result_to_db_tuple,
    _log_parse_result_to_minimal_db_tuple,
    _log_parse_result_to_sparse_db_tuple,
)
from latency.parse.correlation.result_builder import ParseResultBuilder
from latency.parse.correlation.correlator import LogCorrelator
from latency.parse.worker_info_parser import WorkerInfoParser
from latency.parse.worker_metrics_log_parser import WorkerMetricsLogParser
from latency.schemas.ds_log import CorrelationResult, TupleField
from latency.schemas.log import (
    LogParseResultBatch,
    LogParseResultDataclass,
    SparseLogParseResultDataclass,
    generate_uuids_hex,
)
from latency.task.worker import kv_cache_log_parse_worker as worker_module
from latency.task.worker.kv_cache_log_parse_worker import KVCacheLogParseWorker


def _raw_entry(
    *,
    timestamp: datetime,
    trace_id: str,
    elapsed_us: float,
    entry_type: str,
    pod_ip: str = "10.0.0.1",
    status_code: int = 0,
    resp_msg: str | None = "",
    cluster_name: str = "sdk-cluster",
    src_addr: str | None = None,
    dst_addr: str | None = None,
    inflight_count: int | None = None,
    log_id: str = "entry-log",
) -> tuple:
    return (
        timestamp,
        "DS_KV_CLIENT_GET",
        elapsed_us,
        "4096",
        "object-key",
        trace_id,
        pod_ip,
        status_code,
        resp_msg,
        entry_type,
        cluster_name,
        src_addr,
        dst_addr,
        inflight_count,
        None,
        log_id,
    )


def test_timestamp_format_matches_previous_output() -> None:
    values = [
        datetime(2026, 7, 2, 1, 2, 3, 456789),
        datetime(2026, 7, 2, 1, 2, 3),
        datetime(2026, 7, 2, 1, 2, 3, 456789, tzinfo=timezone(timedelta(hours=8))),
    ]
    for value in values:
        expected = value.strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
        assert ParseResultBuilder._format_timestamp(value) == expected
    assert ParseResultBuilder._format_timestamp(None) is None


def test_unmatched_sdk_fast_path_matches_general_builder() -> None:
    timestamps = [
        datetime(2026, 7, 2, 1, 2, 3, 456789),
        datetime(2026, 7, 2, 1, 2, 3),
        datetime(2026, 7, 2, 1, 2, 4, 999999),
        datetime(
            2026,
            7,
            2,
            1,
            2,
            5,
            123456,
            tzinfo=timezone(timedelta(hours=8)),
        ),
    ]
    sdk_entries = [
        _raw_entry(
            timestamp=timestamps[0],
            trace_id="ok-float",
            elapsed_us=2200.444,
            entry_type="SDK_GET",
        ),
        _raw_entry(
            timestamp=timestamps[1],
            trace_id="ok-int",
            elapsed_us=1000,
            entry_type="SDK_GET",
            resp_msg=None,
        ),
        _raw_entry(
            timestamp=timestamps[2],
            trace_id="not-found",
            elapsed_us=3000,
            entry_type="SDK_GET",
            resp_msg="K_NOT_FOUND object-key",
        ),
        _raw_entry(
            timestamp=timestamps[3],
            trace_id="failed",
            elapsed_us=4000,
            entry_type="SDK_GET",
            status_code=1,
            resp_msg="sdk error",
        ),
    ]
    positive_urma = _raw_entry(
        timestamp=timestamps[0],
        trace_id="ok-float",
        elapsed_us=321.987,
        entry_type="URMA",
    )
    negative_urma = _raw_entry(
        timestamp=timestamps[1],
        trace_id="ok-int",
        elapsed_us=-100,
        entry_type="URMA",
    )
    sdk_urma_index = {
        ("10.0.0.1", "ok-float"): [positive_urma],
        ("10.0.0.1", "ok-int"): [negative_urma],
    }
    fast_builder = ParseResultBuilder(
        sdk_entries,
        [],
        CorrelationResult(sdk_urma_index=sdk_urma_index),
        log_dir="fallback-dir",
        log_file_id="file-id",
    )
    # An unused SDK→Worker entry forces the general path while keeping every
    # SDK in this fixture semantically unmatched.
    reference_builder = ParseResultBuilder(
        sdk_entries,
        [],
        CorrelationResult(
            sdk_worker_map={len(sdk_entries): sdk_entries[0]},
            sdk_urma_index=sdk_urma_index,
        ),
        log_dir="fallback-dir",
        log_file_id="file-id",
    )

    fast_results = fast_builder.build()
    reference_results = reference_builder.build()

    assert isinstance(fast_results, LogParseResultBatch)
    assert fast_results.all_sparse is True
    assert fast_builder.anomalous_count == reference_builder.anomalous_count == 3
    assert all(isinstance(result, SparseLogParseResultDataclass) for result in fast_results)
    assert [
        {**asdict(result), "created_at": ""} for result in fast_results
    ] == [
        {**asdict(result), "created_at": ""} for result in reference_results
    ]


def test_raw_builder_preserves_correlated_fields_and_remarks() -> None:
    timestamp = datetime(2026, 7, 2, 1, 2, 3, 456789)
    sdk_entries = [
        _raw_entry(timestamp=timestamp, trace_id="ok", elapsed_us=2200.444, entry_type="SDK_GET"),
        _raw_entry(timestamp=timestamp, trace_id="missing", elapsed_us=1000, entry_type="SDK_GET", resp_msg="K_NOT_FOUND object-key"),
        _raw_entry(timestamp=timestamp, trace_id="failed", elapsed_us=3000, entry_type="SDK_GET", status_code=1, resp_msg="sdk error"),
        _raw_entry(timestamp=timestamp, trace_id="fallback", elapsed_us=2400, entry_type="SDK_GET", resp_msg=None),
    ]
    workers = [
        _raw_entry(timestamp=timestamp, trace_id="ok", elapsed_us=1200, entry_type="WORKER_GET", cluster_name="worker-cluster"),
        _raw_entry(timestamp=timestamp, trace_id="failed", elapsed_us=2000, entry_type="WORKER_GET", status_code=2, resp_msg="worker error"),
        _raw_entry(timestamp=timestamp, trace_id="fallback", elapsed_us=1400, entry_type="WORKER_GET"),
    ]
    urma = _raw_entry(timestamp=timestamp, trace_id="ok", elapsed_us=321.987, entry_type="URMA", src_addr="10.1.0.1", dst_addr="10.2.0.1", inflight_count=7)
    remote_pull = _raw_entry(timestamp=timestamp, trace_id="fallback", elapsed_us=1, entry_type="REMOTE_PULL", src_addr="10.3.0.1", dst_addr="10.4.0.1")
    metric = _raw_entry(timestamp=timestamp, trace_id="ok", elapsed_us=111.555, entry_type="QUERY_META")
    master_rpc = _raw_entry(timestamp=timestamp, trace_id="ok", elapsed_us=987.654, entry_type="MASTER_RPC")
    correlated = CorrelationResult(
        sdk_worker_map={0: workers[0], 2: workers[1], 3: workers[2]},
        worker_idx_map={0: 0, 2: 1, 3: 2},
        sdk_urma_index={("10.0.0.1", "ok"): [metric]},
        worker_urma_map={0: [urma]},
        worker_remote_pull_map={2: [remote_pull]},
        worker_query_meta_map={0: [metric]},
        worker_link_map={0: [metric]},
        worker_worker_urma_map={0: [metric]},
        worker_sdk_process_map={0: [metric]},
        worker_sdk_rpc_map={0: [metric]},
        worker_local_worker_cost_map={0: [metric]},
        worker_local_worker_lock_map={0: [metric]},
        worker_remote_worker_cost_map={0: [metric]},
        worker_remote_worker_rpc_map={0: [metric]},
        worker_master_process_map={0: [metric]},
        worker_master_rpc_map={0: [master_rpc]},
        urma_empty_reasons={1: "no matching URMA"},
    )
    results = ParseResultBuilder(sdk_entries, workers, correlated, log_dir="fallback-dir", log_file_id="file-id").build()

    ok = results[0]
    assert ok.timestamp == "2026-07-02 01:02:03.456"
    assert ok.log_id == "file-id"
    assert ok.cluster_name == "worker-cluster"
    assert ok.total_latency == 2.2
    assert ok.c2w_latency == 1.0
    assert ok.c2w_urma_latency == 0.112
    assert ok.worker_query_meta_latency == 0.112
    assert ok.urma_total_latency == 0.322
    assert ok.urma_inflight_count == 7
    assert (ok.src_ip, ok.dst_ip) == ("10.1.0.1", "10.2.0.1")
    assert ok.master_rpc_total == 987.654
    assert not ok.is_anomalous
    assert ok.remark == "OK"
    assert results[1].remark == "SDK not found,K_NOT_FOUND object-key"
    assert isinstance(results[1], SparseLogParseResultDataclass)
    assert results[1].c2w_latency is None
    assert results[1].src_ip is None
    assert results[1].to_pydantic().worker_query_meta_latency is None
    assert results[2].remark == (
        "SDK failed with status_code=1 resp_msg=sdk error;"
        "Worker failed with status_code=2 resp_msg=worker error;"
        "no matching URMA"
    )
    assert (results[3].src_ip, results[3].dst_ip) == ("10.3.0.1", "10.4.0.1")


def test_scan_scope_reuses_trace_set_and_info_split_is_single_pass() -> None:
    timestamp = datetime(2026, 7, 2)
    sdk_entries = [
        _raw_entry(timestamp=timestamp, trace_id="wanted", elapsed_us=1, entry_type="SDK_GET"),
        _raw_entry(timestamp=timestamp, trace_id="other", elapsed_us=1, entry_type="SDK_GET"),
    ]
    workers = [
        _raw_entry(timestamp=timestamp, trace_id="wanted", elapsed_us=1, entry_type="WORKER_GET"),
        _raw_entry(timestamp=timestamp, trace_id="other", elapsed_us=1, entry_type="WORKER_GET"),
    ]
    reused_trace_ids = {"wanted"}
    scope = KVCacheLogParseWorker._build_worker_info_scan_scope(
        {"SDK access parse": sdk_entries, "Worker access parse": workers}, reused_trace_ids
    )
    assert scope["trace_ids"] is reused_trace_ids
    assert scope["_stats"]["worker_scope"] == 1

    info_entries = [
        _raw_entry(timestamp=timestamp, trace_id="wanted", elapsed_us=1, entry_type=entry_type.value)
        for entry_type in (EntryType.URMA, EntryType.REMOTE_PULL, EntryType.LINK, EntryType.QUERY_META)
    ]
    info_entries.append(_raw_entry(timestamp=timestamp, trace_id="wanted", elapsed_us=1, entry_type="UNKNOWN"))
    parsed = {"Worker info parse": info_entries}
    KVCacheLogParseWorker._split_worker_info_entries(parsed)
    assert "Worker info parse" not in parsed
    assert list(parsed) == [
        "Worker urma parse",
        "Worker remote pull parse",
        "Worker link parse",
        "Worker query meta parse",
    ]
    assert all(len(entries) == 1 for entries in parsed.values())


def test_worker_query_meta_scope_uses_pod_ip_from_log_line() -> None:
    trace_id = "wanted-trace"
    parser = WorkerInfoParser()
    parser.set_scan_scope(
        {
            "enabled": True,
            "trace_ids": {trace_id},
            "pod_trace_keys": {("192.168.1.10", trace_id)},
            "pod_ips": {"192.168.1.10"},
        }
    )
    line = (
        "2026-05-11T00:09:31.042186 | I | worker.cpp:1 | "
        f"192.168.1.10 | 1:2 | {trace_id} | cluster | "
        "[Get] Master query done, targets: 1, hits: 1, cost: 0.048ms\n"
    )

    entries = parser.match_line(line, "worker_192.168.1.10")

    assert entries is not None
    assert len(entries) == 1
    assert entries[0].entry_type == EntryType.QUERY_META
    assert entries[0].elapsed_us == 48.0


def test_worker_metrics_preserves_remote_endpoint_from_message() -> None:
    parser = WorkerMetricsLogParser()
    trace_id = "trace-with-endpoint"
    line = (
        "2026-05-11T00:08:27.123456 | I | worker.cpp:1 | "
        f"192.168.102.119 | 1:2 | {trace_id} | cluster | "
        "[Get] Remote done, count: 1, path: UB, cost: 0.616ms, "
        "src=192.168.102.119:31402, dst=192.168.182.7:31402\n"
    )

    entries = parser.match_line(line, "worker_192.168.102.119")

    assert entries is not None
    assert len(entries) == 1
    entry = entries[0]
    assert entry.entry_type == EntryType.REMOTE_WORKER_RPC
    assert entry.elapsed_us == 616.0
    assert entry.src_addr == "192.168.102.119:31402"
    assert entry.dst_addr == "192.168.182.7:31402"


def test_worker_info_urma_parses_target_dst_and_destination_address() -> None:
    parser = WorkerInfoParser()
    trace_id = "trace-with-urma-endpoint"

    for target_field in ("target address", "dst address", "destination address"):
        line = (
            "2026-05-11T00:08:27.123456 | I | worker.cpp:1 | "
            f"192.168.102.119 | 1:2 | {trace_id} | cluster | "
            "[URMA_ELAPSED_TOTAL] read done, cost 1.234ms, "
            f"src address:192.168.102.119:31402, "
            f"{target_field}:192.168.182.7:31402, "
            "urma_inflight_wr_count:7\n"
        )

        entries = parser.match_line(line, "worker_192.168.102.119")

        assert entries is not None
        assert len(entries) == 1
        entry = entries[0]
        assert entry.entry_type == EntryType.URMA
        assert entry.elapsed_us == 1234.0
        assert entry.src_addr == "192.168.102.119:31402"
        assert entry.dst_addr == "192.168.182.7:31402"
        assert entry.inflight_count == 7


def test_worker_metrics_tuple_entry_type_is_correlated() -> None:
    timestamp = datetime(2026, 7, 2)
    trace_id = "wanted"
    sdk = _raw_entry(
        timestamp=timestamp,
        trace_id=trace_id,
        elapsed_us=2000,
        entry_type=EntryType.SDK_GET.value,
    )
    worker = _raw_entry(
        timestamp=timestamp,
        trace_id=trace_id,
        elapsed_us=1000,
        entry_type=EntryType.WORKER_GET.value,
    )
    metric_maps = (
        (EntryType.SDK_PROCESS, "worker_sdk_process_map"),
        (EntryType.SDK_RPC, "worker_sdk_rpc_map"),
        (EntryType.LOCAL_WORKER_COST, "worker_local_worker_cost_map"),
        (EntryType.LOCAL_WORKER_LOCK, "worker_local_worker_lock_map"),
        (EntryType.REMOTE_WORKER_COST, "worker_remote_worker_cost_map"),
        (EntryType.REMOTE_WORKER_RPC, "worker_remote_worker_rpc_map"),
        (EntryType.MASTER_PROCESS, "worker_master_process_map"),
        (EntryType.MASTER_RPC, "worker_master_rpc_map"),
    )
    metrics = [
        _raw_entry(
            timestamp=timestamp,
            trace_id=trace_id,
            elapsed_us=index + 1,
            entry_type=entry_type.value,
        )
        for index, (entry_type, _) in enumerate(metric_maps)
    ]

    for sdk_entries in ([], [sdk]):
        correlated = LogCorrelator(
            {
                "SDK access parse": sdk_entries,
                "Worker access parse": [worker],
                "Worker metrics parse": metrics,
            }
        ).correlate()

        for entry_type, map_name in metric_maps:
            values = getattr(correlated, map_name)[0]
            assert values[0][TupleField.ENTRY_TYPE] == entry_type.value


def test_result_builder_falls_back_to_remote_metric_endpoint() -> None:
    timestamp = datetime(2026, 7, 2, 1, 2, 3)
    trace_id = "trace-with-metric-endpoint"
    sdk = _raw_entry(
        timestamp=timestamp,
        trace_id=trace_id,
        elapsed_us=3000,
        entry_type=EntryType.SDK_GET.value,
    )
    worker = _raw_entry(
        timestamp=timestamp,
        trace_id=trace_id,
        elapsed_us=1000,
        entry_type=EntryType.WORKER_GET.value,
    )
    remote_rpc = _raw_entry(
        timestamp=timestamp,
        trace_id=trace_id,
        elapsed_us=616,
        entry_type=EntryType.REMOTE_WORKER_RPC.value,
        src_addr="192.168.102.119:31402",
        dst_addr="192.168.182.7:31402",
    )
    correlated = LogCorrelator(
        {
            "SDK access parse": [sdk],
            "Worker access parse": [worker],
            "Worker metrics parse": [remote_rpc],
        }
    ).correlate()

    results = ParseResultBuilder([sdk], [worker], correlated).build()

    assert len(results) == 1
    result = results[0]
    assert isinstance(result, LogParseResultDataclass)
    assert result.remote_worker_rpc == 0.616
    assert (result.src_ip, result.dst_ip) == (
        "192.168.102.119:31402",
        "192.168.182.7:31402",
    )


def test_empty_sdk_worker_correlation_falls_back_to_worker_results() -> None:
    timestamp = datetime(2026, 7, 2, 1, 2, 3)
    sdk = _raw_entry(
        timestamp=timestamp,
        trace_id="sdk-trace",
        elapsed_us=2000,
        entry_type=EntryType.SDK_GET.value,
    )
    worker = _raw_entry(
        timestamp=timestamp,
        trace_id="worker-trace",
        elapsed_us=1000,
        entry_type=EntryType.WORKER_GET.value,
        cluster_name="worker-cluster",
    )
    query_meta = _raw_entry(
        timestamp=timestamp,
        trace_id="worker-trace",
        elapsed_us=120,
        entry_type=EntryType.QUERY_META.value,
    )
    sdk_process = _raw_entry(
        timestamp=timestamp,
        trace_id="worker-trace",
        elapsed_us=340,
        entry_type=EntryType.SDK_PROCESS.value,
    )
    urma = _raw_entry(
        timestamp=timestamp,
        trace_id="",
        elapsed_us=560,
        entry_type=EntryType.URMA.value,
        src_addr="10.0.0.1:1",
        dst_addr="10.0.0.2:1",
        inflight_count=3,
    )
    correlated = LogCorrelator(
        {
            "SDK access parse": [sdk],
            "Worker access parse": [worker],
            "Worker query meta parse": [query_meta],
            "Worker metrics parse": [sdk_process],
            "Worker urma parse": [urma],
        }
    ).correlate()

    assert correlated.sdk_worker_map == {}
    assert correlated.worker_query_meta_map[0] == [query_meta]
    assert correlated.worker_sdk_process_map[0] == [sdk_process]
    assert correlated.worker_urma_map[0] == [urma]

    results = ParseResultBuilder(
        [sdk],
        [worker],
        correlated,
        log_file_id="file-id",
    ).build()

    assert len(results) == 1
    result = results[0]
    assert isinstance(result, LogParseResultDataclass)
    assert result.trace_id == "worker-trace"
    assert result.operation == "DS_POSIX_GET"
    assert result.total_latency == 1.0
    assert result.worker_query_meta_latency == 0.12
    assert result.sdk_process == 0.34
    assert result.urma_total_latency == 0.56
    assert (result.src_ip, result.dst_ip) == ("10.0.0.1:1", "10.0.0.2:1")


def test_large_trace_scope_is_not_copied_to_processes(monkeypatch) -> None:
    monkeypatch.setattr(worker_module, "MAX_PROCESS_SCAN_SCOPE_TRACE_IDS", 2)
    timestamp = datetime(2026, 7, 2)
    entries = [
        _raw_entry(
            timestamp=timestamp,
            trace_id=f"trace-{index}",
            elapsed_us=1,
            entry_type="SDK_GET",
        )
        for index in range(4)
    ]

    scope = KVCacheLogParseWorker._build_worker_access_scan_scope(
        {"SDK access parse": entries}
    )

    assert not scope["enabled"]
    assert scope["reason"] == "trace_scope_too_large"
    assert "trace_ids" not in scope
    assert scope["_stats"]["sdk_traces"] == 3


def test_sdk_urma_uses_shared_index_without_sdk_sized_map() -> None:
    timestamp = datetime(2026, 7, 2)
    sdk = _raw_entry(
        timestamp=timestamp,
        trace_id="trace",
        elapsed_us=1000,
        entry_type="SDK_GET",
    )
    urma = _raw_entry(
        timestamp=timestamp,
        trace_id="trace",
        elapsed_us=100,
        entry_type="URMA",
    )

    correlated = LogCorrelator(
        {
            "SDK access parse": [sdk],
            "Worker access parse": [],
            "Worker urma parse": [urma],
        }
    ).correlate()

    assert correlated.sdk_urma_map == {}
    assert correlated.sdk_urma_index[("10.0.0.1", "trace")] == [urma]


def test_unmatched_sdk_with_urma_endpoint_builds_full_result() -> None:
    timestamp = datetime(2026, 7, 2)
    sdk = _raw_entry(
        timestamp=timestamp,
        trace_id="trace",
        elapsed_us=3000,
        entry_type=EntryType.SDK_GET.value,
    )
    urma = _raw_entry(
        timestamp=timestamp,
        trace_id="trace",
        elapsed_us=560,
        entry_type=EntryType.URMA.value,
        src_addr="10.0.0.1:1",
        dst_addr="10.0.0.2:1",
        inflight_count=3,
    )
    correlated = LogCorrelator(
        {
            "SDK access parse": [sdk],
            "Worker access parse": [],
            "Worker urma parse": [urma],
        }
    ).correlate()

    results = ParseResultBuilder(
        [sdk],
        [],
        correlated,
        log_file_id="file-id",
    ).build()

    assert isinstance(results, LogParseResultBatch)
    assert results.all_sparse is False
    assert len(results) == 1
    result = results[0]
    assert isinstance(result, LogParseResultDataclass)
    assert result.log_id == "file-id"
    assert result.total_latency == 3.0
    assert result.c2w_latency is None
    assert result.c2w_urma_latency == 0.56
    assert result.urma_total_latency == 0.56
    assert result.urma_inflight_count == 3
    assert (result.src_ip, result.dst_ip) == ("10.0.0.1:1", "10.0.0.2:1")


def test_single_worker_trace_skips_sort_and_timestamp_index() -> None:
    timestamp = datetime(2026, 7, 2)
    sdk = _raw_entry(
        timestamp=timestamp,
        trace_id="trace",
        elapsed_us=1000,
        entry_type="SDK_GET",
    )
    # 唯一 trace 的 Worker 即使超出时间窗，旧逻辑最终也会唯一回退匹配。
    worker = _raw_entry(
        timestamp=timestamp + timedelta(hours=1),
        trace_id="trace",
        elapsed_us=500,
        entry_type="WORKER_GET",
    )
    correlator = LogCorrelator(
        {"SDK access parse": [sdk], "Worker access parse": [worker]}
    )

    assert correlator.index_manager.worker_ts_by_trace == {}
    assert correlator.index_manager.worker_by_trace_object == {}
    assert correlator.correlate().sdk_worker_map == {0: worker}


def test_multi_worker_trace_and_best_link_keep_previous_semantics() -> None:
    timestamp = datetime(2026, 7, 2)
    sdk = _raw_entry(
        timestamp=timestamp,
        trace_id="trace",
        elapsed_us=1000,
        entry_type="SDK_GET",
    )
    earlier = _raw_entry(
        timestamp=timestamp - timedelta(milliseconds=20),
        trace_id="trace",
        elapsed_us=500,
        entry_type="WORKER_GET",
    )
    nearest = _raw_entry(
        timestamp=timestamp + timedelta(milliseconds=10),
        trace_id="trace",
        elapsed_us=500,
        entry_type="WORKER_GET",
    )
    slow_link = _raw_entry(
        timestamp=timestamp,
        trace_id="trace",
        elapsed_us=100,
        entry_type="LINK",
    )
    best_link = _raw_entry(
        timestamp=timestamp,
        trace_id="trace",
        elapsed_us=200,
        entry_type="LINK",
    )
    correlator = LogCorrelator(
        {
            "SDK access parse": [sdk],
            "Worker access parse": [nearest, earlier],
            "Worker link parse": [slow_link, best_link],
        }
    )

    correlated = correlator.correlate()
    assert correlator.index_manager.worker_ts_by_trace["trace"] == [
        earlier[0], nearest[0]
    ]
    assert correlated.sdk_worker_map == {0: nearest}
    worker_idx = correlated.worker_idx_map[0]
    assert correlated.worker_link_map[worker_idx] == [best_link]


def test_result_dataclass_field_order_is_locked_for_fast_constructor() -> None:
    assert [field.name for field in fields(LogParseResultDataclass)] == [
        "total_latency", "is_anomalous", "id", "log_id",
        "aggregated_event_id", "anomalous_event_id", "pod_ip", "src_ip",
        "dst_ip", "cluster_name", "host", "anomaly_reason", "anomaly_score",
        "content", "data_size", "existed_status", "offset", "operation",
        "remark", "trace_id", "urma_inflight_count", "urma_link_latency",
        "urma_total_latency", "c2w_latency", "worker_query_meta_latency",
        "c2w_urma_latency", "w2w_urma_latency", "sdk_process", "sdk_rpc",
        "local_worker_cost", "local_worker_lock", "remote_worker_cost",
        "remote_worker_rpc", "master_process", "master_rpc_total", "timestamp",
        "created_at",
    ]
    assert [field.name for field in fields(SparseLogParseResultDataclass)] == [
        "total_latency", "is_anomalous", "id", "log_id",
        "aggregated_event_id", "anomalous_event_id", "pod_ip",
        "cluster_name", "anomaly_reason", "data_size", "existed_status",
        "operation", "remark", "trace_id", "c2w_urma_latency",
        "timestamp", "created_at",
    ]


def test_database_tuple_matches_insert_column_order() -> None:
    result = LogParseResultDataclass(
        total_latency=12.3, is_anomalous=True, id="id", log_id="log",
        aggregated_event_id="aggregate", anomalous_event_id="anomaly", trace_id="trace",
        timestamp="timestamp", src_ip="src", dst_ip="dst", pod_ip="pod",
        cluster_name="cluster", host="host", c2w_latency=1.0,
        worker_query_meta_latency=2.0, urma_total_latency=3.0, urma_link_latency=4.0,
        urma_inflight_count=5, c2w_urma_latency=6.0, w2w_urma_latency=7.0,
        operation="operation", data_size="data-size", offset=8, content="content",
        anomaly_reason="reason", anomaly_score=0.9, remark="remark", existed_status=True,
        created_at="created-at", sdk_process=9.0, sdk_rpc=10.0,
        local_worker_cost=11.0, local_worker_lock=12.0, remote_worker_cost=13.0,
        remote_worker_rpc=14.0, master_process=15.0, master_rpc_total=16.0,
    )
    assert _log_parse_result_to_db_tuple(result) == (
        "id", "log", "aggregate", "anomaly", "trace", "timestamp", "src", "dst",
        "pod", "cluster", "host", 12.3, 1.0, 2.0, 3.0, 4.0, 5, 6.0, 7.0,
        "operation", "data-size", 8, True, "content", "reason", 0.9, "remark",
        True, "created-at", 9.0, 10.0, 11.0, 12.0, 13.0, 14.0, 15.0, 16.0,
    )


def test_sparse_database_tuple_only_omits_null_fields() -> None:
    sparse = SparseLogParseResultDataclass(
        total_latency=12.3,
        is_anomalous=False,
        id="id",
        log_id="log",
        trace_id="trace",
        timestamp="timestamp",
        pod_ip="pod",
        cluster_name="cluster",
        c2w_urma_latency=6.0,
        operation="operation",
        data_size="data-size",
        remark="OK",
        created_at="created-at",
    )

    assert _can_use_sparse_insert(sparse)
    assert not _can_use_minimal_insert(sparse)
    assert _log_parse_result_to_sparse_db_tuple(sparse) == (
        "id", "log", "", "", "trace", "timestamp", "pod", "cluster",
        12.3, 6.0, "operation", "data-size", False, None, "OK", True,
        "created-at",
    )
    full = LogParseResultDataclass(
        total_latency=12.3,
        is_anomalous=False,
        id="id",
        log_id="log",
        trace_id="trace",
        timestamp="timestamp",
        pod_ip="pod",
        cluster_name="cluster",
        c2w_urma_latency=6.0,
        operation="operation",
        data_size="data-size",
        remark="OK",
        created_at="created-at",
    )
    assert _log_parse_result_to_db_tuple(sparse) == _log_parse_result_to_db_tuple(full)

    full.worker_query_meta_latency = 1.0
    assert not _can_use_sparse_insert(full)

    minimal = SparseLogParseResultDataclass(
        total_latency=1.0,
        is_anomalous=False,
        trace_id="minimal",
        remark="OK",
        created_at="created-at",
    )
    assert _can_use_minimal_insert(minimal)
    assert _log_parse_result_to_minimal_db_tuple(minimal) == (
        "", "", "minimal", None, None, None, 1.0, None, None, False,
        "OK", True, "created-at",
    )


def test_batch_manager_uses_positional_tuples(monkeypatch) -> None:
    results = [
        SparseLogParseResultDataclass(total_latency=0.0, is_anomalous=False),
        LogParseResultDataclass(total_latency=1.0, is_anomalous=False),
        SparseLogParseResultDataclass(total_latency=2.0, is_anomalous=False),
    ]
    results[1].c2w_latency = 1.0
    results[2].c2w_urma_latency = 2.0

    class FakeAsyncLock:
        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, traceback):
            return False

    class FakeConnection:
        def __init__(self):
            self.insert_sql = ""
            self.params = []

        def execute(self, sql):
            return None

        def executemany(self, sql, params):
            self.insert_sql = sql
            self.params.extend(params)

        def commit(self):
            return None

        def rollback(self):
            return None

    class FakeDatabase:
        def __init__(self):
            self._async_lock = FakeAsyncLock()
            self._conn = FakeConnection()

    database = FakeDatabase()
    monkeypatch.setattr(log_parse_result_manager_module, "AsyncSQLiteSingleton", lambda: database)
    stored = asyncio.run(
        LogParseResultManager.add_log_parse_results(results, batch_size=2)
    )
    assert stored
    assert LogParseResultManager.last_store_metrics["minimal_rows"] == 1
    assert LogParseResultManager.last_store_metrics["sparse_rows"] == 1
    assert LogParseResultManager.last_store_metrics["full_rows"] == 1
    assert LogParseResultManager.last_store_metrics["success"] is True
    assert database._conn.insert_sql.count("?") == 17
    assert database._conn.params == [
        _log_parse_result_to_minimal_db_tuple(results[0]),
        _log_parse_result_to_db_tuple(results[1]),
        _log_parse_result_to_sparse_db_tuple(results[2]),
    ]
    assert len({result.id[:20] for result in results}) == 1
    assert [int(result.id[20:], 16) for result in results] == [0, 1, 2]
    assert all(len(result.id) == 32 for result in results)


def test_store_result_passes_dataclasses_directly(monkeypatch) -> None:
    result = LogParseResultDataclass(total_latency=1.0, is_anomalous=False)
    captured = []

    async def fake_add_log_parse_results(results):
        captured.extend(results)
        return True

    monkeypatch.setattr(
        LogParseResultManager,
        "add_log_parse_results",
        staticmethod(fake_add_log_parse_results),
    )
    stored = asyncio.run(KVCacheLogParseWorker.store_result([result], [], [], []))
    assert stored
    assert captured == [result]


def test_generated_ids_keep_uuid_hex_shape() -> None:
    generated = generate_uuids_hex(3)
    assert len(generated) == 3
    assert len(set(generated)) == 3
    assert all(len(value) == 32 for value in generated)
    assert all(int(value, 16) >= 0 for value in generated)
