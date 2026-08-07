"""T5 (Block D) unit tests: all-matching line routing + worker-info split.

Covers:
- _scan_file_multi routes shared-file lines to ALL matching parsers
  (Oracle P1-2: first-match-wins drops entries and breaks e2e parity)
- WorkerInfoParser src/dst fallback survives the merged keyword pre-filter
- _split_worker_info_entries appends bucket entries to fast-path sub-labels

T7: scope-filter tests removed (D3 — ``_filter_worker_access_by_scope`` /
``_filter_worker_info_by_scope`` deleted in T1; scan-time scope only).
"""

import sys
from pathlib import Path

_TEST_DIR = Path(__file__).resolve().parent
_PROJECT_ROOT = _TEST_DIR.parent
sys.path.insert(0, str(_PROJECT_ROOT))

_SDK_LINE = (
    "2026-05-11T05:25:20.207278 | I | access_recorder.cpp:220 | "
    "searchctrwirelessub-24-00031 | 3941:3970 | trace-sdk-1 |  | 0 | "
    "DS_KV_CLIENT_GET | 773 | 8395125 | {Object_key:key-sdk-1,timeout:0} | resp"
)
_WORKER_LINE = (
    "2026-05-11T05:25:21.087136 | I | access_recorder.cpp:220 | "
    "searchctrwirelessub-24-00031 | 3941:3968 | trace-worker-1 |  | 0 | "
    "DS_POSIX_GET | 417 | 8395125 | {Object_key:key-worker-1,timeout:0} | resp"
)
# handle=DS_POSIX_GET but req_msg contains an SDK keyword → both parsers match
# by keyword; all-matching must still route it to WorkerAccessParser.
_MIXED_LINE = (
    "2026-05-11T05:25:28.952002 | I | access_recorder.cpp:220 | "
    "searchctrwirelessub-24-00031 | 3941:3950 | trace-mixed-1 |  | 0 | "
    "DS_POSIX_GET | 189 | 8395125 | {Object_key:key-mixed-1,op:DS_KV_CLIENT_GET} | resp"
)
_URMA_LINE = (
    "2026-05-13T00:03:42.487820 | I | urma_manager.cpp:852 | "
    "6.62.223.31 | 112:409 | trace-urma-1 | model_kvcache_predictor |  "
    "[URMA_ELAPSED_TOTAL]: Waiting URMA jfc event done after "
    "urma_post_jetty_send_wr cost 1.27262ms, request id:2052374, "
    "src address:6.62.223.31:31501, target address:6.62.222.250:31501, "
    "dataSize:8395125, cpuid:2, status: code: [OK], msg: [DS_KV_CLIENT_GET], "
    "urma_inflight_wr_count: 1"
)
_SRC_DST_LINE = (
    "2026-05-13T00:00:00.018819 | I | worker_oc_service_get_impl.cpp:130 | "
    "6.62.223.31 | 112:403 | trace-srcdst-1 | model_kvcache_predictor |  "
    "handshake done, src 6.62.223.31:31501, dst 6.62.222.250:31501, ok"
)


def _mk_parsers():
    from latency.parse.sdk_access_log_parser import SdkAccessLogParser
    from latency.parse.worker_access_log_parser import WorkerAccessLogParser
    from latency.parse.worker_info_parser import WorkerInfoParser

    return SdkAccessLogParser(None), WorkerAccessLogParser(None), WorkerInfoParser(None)


def _write_log(tmp_path, name: str, lines: list[str]) -> str:
    path = tmp_path / name
    path.write_text("\n".join(lines) + "\n")
    return str(path)


def test_scan_file_multi_all_matching_shared_access(tmp_path):
    """Shared *_access.log: a mixed line must reach WorkerAccessParser even
    though the SDK keyword matches first (Oracle P1-2: no first-match-wins)."""
    from latency.parse.parallel_scanner.process_worker import _scan_file_multi

    sdk, worker, _ = _mk_parsers()
    path = _write_log(tmp_path, "shared_access.log", [_SDK_LINE, _MIXED_LINE, _WORKER_LINE])
    result = _scan_file_multi([sdk, worker], path)

    sdk_entries = result.get("SDK access parse", [])
    worker_entries = result.get("Worker access parse", [])
    assert len(sdk_entries) == 1  # only the pure SDK line parses to an SDK entry
    assert len(worker_entries) == 2  # mixed + pure worker line both routed
    worker_traces = {e.trace_id for e in worker_entries}
    assert "trace-mixed-1" in worker_traces
    assert "trace-worker-1" in worker_traces


def test_scan_file_multi_all_matching_shared_runtime(tmp_path):
    """Shared *_runtime.log: an info line containing an SDK keyword must still
    produce the WorkerInfo entry (SDK-first routing would drop it)."""
    from latency.parse.parallel_scanner.process_worker import _scan_file_multi

    sdk, _, info = _mk_parsers()
    path = _write_log(tmp_path, "shared_runtime.log", [_URMA_LINE])
    result = _scan_file_multi([sdk, info], path)

    info_entries = result.get("Worker info parse", [])
    assert len(info_entries) == 1
    assert info_entries[0].trace_id == "trace-urma-1"
    assert info_entries[0].entry_type.value == "URMA"
    # SDK parser saw the line but run-format plen<13 → no SDK entry
    assert not result.get("SDK access parse")


def test_scan_file_multi_src_dst_fallback(tmp_path):
    """src/dst fallback lines (no keywords) must still reach WorkerInfoParser
    through its _line_may_match extra matcher (else parity drifts)."""
    from latency.parse.parallel_scanner.process_worker import _scan_file_multi

    sdk, _, info = _mk_parsers()
    path = _write_log(tmp_path, "worker_runtime.log", [_SRC_DST_LINE])
    result = _scan_file_multi([sdk, info], path)

    info_entries = result.get("Worker info parse", [])
    assert len(info_entries) == 1
    assert info_entries[0].trace_id == "trace-srcdst-1"


def test_split_worker_info_entries_appends_to_existing_sublabels(tmp_path):
    """Bucket split must APPEND to fast-path sub-labels, not overwrite them."""
    from latency.task.worker.kv_cache_log_parse_worker import KVCacheLogParseWorker
    from latency.parse.worker_info_parser import WorkerInfoParser, URMA_LABEL

    parser = WorkerInfoParser(None)
    path = _write_log(tmp_path, "worker_runtime.log", [_URMA_LINE])
    fast_path = parser.scan_file(path)
    urma_fast = fast_path.get(URMA_LABEL, [])
    assert len(urma_fast) == 1

    parsed = {URMA_LABEL: list(urma_fast)}
    parsed["Worker info parse"] = list(urma_fast)  # same entry via bucket
    KVCacheLogParseWorker._split_worker_info_entries(parsed)
    assert "Worker info parse" not in parsed
    assert len(parsed[URMA_LABEL]) == 2  # fast-path 1 + bucket 1, not overwritten
