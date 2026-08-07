#!/usr/bin/env python3
"""T6 (Block E) unit tests: IO/parse decoupling in the scan worker.

Covers (acceptance of perf-overhaul-io-aware T6):
- _scan_file_multi_decoupled produces identical parse results to the sync
  path (parity by construction: both reuse _parse_lines; log_id normalized)
- Slow-IO simulation (per-read delay wrapper) shows decoupled >= 50x vs sync
  (Oracle: file-level queue maxsize=2, NOT line-level queue)
- Fast-IO overhead stays < 1.5x (the reason decoupling is gated to HDD only)
- Peak memory within the 3x-file budget (io.StringIO, no splitlines double copy)
- HDD-only enablement (_should_decouple) with WITTY_UB_IO_DECOUPLE override
- Single-parser scan_file fast path (WorkerInfoParser) is untouched

Run: cd src/plugins/latency && PYTHONPATH=/home/li/witty-ub_8632/src/plugins \
  .venv/bin/python -m pytest test/test_scan_io_decouple.py -v -p no:cacheprovider
"""
from __future__ import annotations

import os
import sys
import time
import tracemalloc
from datetime import datetime
from pathlib import Path

import pytest

_TEST_DIR = Path(__file__).resolve().parent
_PROJECT_ROOT = _TEST_DIR.parent
sys.path.insert(0, str(_PROJECT_ROOT))

from latency.ENUM.ds_log import EntryType, TupleField  # noqa: E402
from latency.parse.base_parser import LogParser  # noqa: E402
from latency.parse.parallel_scanner import process_worker as pw  # noqa: E402
from latency.schemas.ds_log import LogEntry  # noqa: E402

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


class _HitParser(LogParser):
    """廉价解析器: 命中 HIT 关键字即产出 entry(解析成本可忽略, 用于 IO 基准)。"""

    label = "hit parse"
    _keywords = ("HIT",)

    @property
    def patterns(self) -> list[str]:
        return []

    def match_line(self, line: str, pod_ip: str) -> LogEntry | None:
        if "HIT" not in line:
            return None
        return LogEntry(
            timestamp=datetime.fromisoformat("2026-05-11T05:25:20.207278"),
            trace_id="trace-hit",
            pod_ip=pod_ip,
            elapsed_us=1.0,
            entry_type=EntryType.SDK_GET,
        )


class _NullParser(LogParser):
    """不命中任何行: 解析零产出, 用于隔离文件缓冲的峰值内存(与结果集无关)。"""

    label = "null parse"
    _keywords = ("NEVER_MATCH",)

    @property
    def patterns(self) -> list[str]:
        return []

    def match_line(self, line: str, pod_ip: str) -> LogEntry | None:
        return None


class _SlowReader:
    """模拟机械盘: 每个 read/readline 前 sleep(寻道+旋转延迟)。

    同步路径用 readline 逐行(每行一次寻道); 解耦 IO 线程用 read(1MB)大块
    (每块一次寻道)——与 /tmp/opencode/slow_io_bench.py 的模型一致。
    """

    def __init__(self, fh, delay_us: float):
        self._fh = fh
        self._delay = delay_us / 1e6

    def _sleep(self):
        # delay=0 时完全直通(time.sleep(0) 实测 ~87µs/次, 会污染快 IO 基准)
        if self._delay:
            time.sleep(self._delay)

    def read(self, *args, **kwargs):
        self._sleep()
        return self._fh.read(*args, **kwargs)

    def readline(self, *args, **kwargs):
        self._sleep()
        return self._fh.readline(*args, **kwargs)

    def __next__(self):
        line = self.readline()
        if not line:
            raise StopIteration
        return line

    def __iter__(self):
        return self

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return self._fh.__exit__(*exc)

    def __getattr__(self, name):
        return getattr(self._fh, name)


def _write_log(tmp_path, name: str, lines: list[str]) -> str:
    path = tmp_path / name
    path.write_text("\n".join(lines) + "\n")
    return str(path)


def _mk_parsers():
    from latency.parse.sdk_access_log_parser import SdkAccessLogParser
    from latency.parse.worker_access_log_parser import WorkerAccessLogParser
    from latency.parse.worker_info_parser import WorkerInfoParser

    return SdkAccessLogParser(None), WorkerAccessLogParser(None), WorkerInfoParser(None)


def _gen_hit_lines(n: int) -> list[str]:
    return [
        f"2026-05-11T05:25:20.207278 | I | a.cpp:1 | pod-1 | 1:{i} | "
        f"trace-hit-{i:06d} | c-1 | 0 | HIT | 1 | 1 | {{k:{i}}} | resp"
        for i in range(n)
    ]


def _counts(result: dict[str, list]) -> dict[str, int]:
    return {label: len(entries) for label, entries in result.items() if entries}


def _normalized(entry):
    """log_id 是每次 LogFileModel 实例化的 uuid —— 归一化后再比较。"""
    t = list(pw._serialize_entry(entry))
    t[TupleField.LOG_ID] = None
    return tuple(t)


def _assert_same_results(sync_result, dec_result):
    assert _counts(sync_result) == _counts(dec_result), (
        f"count drift: {_counts(sync_result)} vs {_counts(dec_result)}"
    )
    for label in sync_result:
        if not sync_result[label]:
            continue
        assert sorted(map(_normalized, sync_result[label])) == sorted(
            map(_normalized, dec_result.get(label, []))
        ), f"entry drift in {label}"


# ════════════════════════════════════════════════════════════════════
# 1. Parity: decoupled results identical to sync (real parsers, shared files)
# ════════════════════════════════════════════════════════════════════


def test_decoupled_matches_sync_on_shared_access(tmp_path):
    sdk, worker, _ = _mk_parsers()
    path = _write_log(tmp_path, "shared_access.log", [_SDK_LINE, _MIXED_LINE, _WORKER_LINE])
    sync = pw._scan_file_multi_sync([sdk, worker], path)
    dec = pw._scan_file_multi_decoupled([sdk, worker], path)
    _assert_same_results(sync, dec)
    assert len(dec.get("SDK access parse", [])) == 1
    assert len(dec.get("Worker access parse", [])) == 2


def test_decoupled_matches_sync_on_shared_runtime(tmp_path):
    sdk, _, info = _mk_parsers()
    path = _write_log(tmp_path, "shared_runtime.log", [_URMA_LINE])
    sync = pw._scan_file_multi_sync([sdk, info], path)
    dec = pw._scan_file_multi_decoupled([sdk, info], path)
    _assert_same_results(sync, dec)
    assert len(dec.get("Worker info parse", [])) == 1
    assert dec["Worker info parse"][0].trace_id == "trace-urma-1"


def test_group_decoupled_matches_serial(tmp_path):
    """组级解耦(_scan_group_decoupled)与串行循环结果一致(生产多进程路径)。"""
    sdk, worker, info = _mk_parsers()
    parsers = [sdk, worker, info]
    shared_access = _write_log(
        tmp_path, "shared_access.log", [_SDK_LINE, _MIXED_LINE, _WORKER_LINE]
    )
    shared_runtime = _write_log(tmp_path, "shared_runtime.log", [_URMA_LINE])
    files = [(shared_access, [0, 1]), (shared_runtime, [0, 2])]

    dec = pw._scan_group_decoupled(files, parsers, 0)
    ser = pw._scan_group_serial(files, parsers, 0)
    assert _counts(dec) == _counts(ser)
    for label in ser:
        if not ser[label]:
            continue
        assert sorted(map(_normalized, ser[label])) == sorted(
            map(_normalized, dec.get(label, []))
        ), f"group entry drift in {label}"


# ════════════════════════════════════════════════════════════════════
# 2. Slow-IO simulation: decoupled >= 50x faster than sync
# ════════════════════════════════════════════════════════════════════


@pytest.mark.parametrize("delay_us", [300])
def test_slow_io_decoupled_ge_50x(delay_us, monkeypatch, tmp_path):
    """慢 IO(每行 300µs 寻道): 解耦(大块读)必须 >= 50x 同步(逐行读)。

    同步 = 6000 行 × 300µs ≈ 1.8s; 解耦 = 1 次 1MB 块读 × 300µs + 解析 ≈ ms 级。
    """
    from latency.common import ds_log_io as ds_io

    lines = _gen_hit_lines(6000)
    path = _write_log(tmp_path, "slow.log", lines)
    parser = _HitParser()

    real_open = ds_io.open_log

    def _slow_open_log(p: str):
        return _SlowReader(real_open(p), delay_us)

    monkeypatch.setattr(pw, "open_log", _slow_open_log)

    t0 = time.perf_counter()
    sync_result = pw._scan_file_multi_sync([parser], path)
    sync_t = time.perf_counter() - t0

    t0 = time.perf_counter()
    dec_result = pw._scan_file_multi_decoupled([parser], path)
    dec_t = time.perf_counter() - t0

    # parity 保持: 慢 IO 模拟下计数一致
    assert _counts(sync_result) == _counts(dec_result) == {parser.label: 6000}
    assert dec_t > 0
    ratio = sync_t / dec_t
    assert ratio >= 50, f"slow-IO speedup {ratio:.1f}x < 50x (sync {sync_t:.3f}s, decoupled {dec_t:.3f}s)"


# ════════════════════════════════════════════════════════════════════
# 3. Fast-IO overhead < 1.5x (reason for HDD-only gating)
# ════════════════════════════════════════════════════════════════════


def test_fast_io_decoupled_overhead_lt_1_5x(monkeypatch, tmp_path):
    """快 IO(delay=0): 解耦开销必须 < 1.5x 同步, 否则 SSD 不应启用解耦。"""
    from latency.common import ds_log_io as ds_io

    lines = _gen_hit_lines(100_000)
    path = _write_log(tmp_path, "fast.log", lines)
    parser = _HitParser()

    real_open = ds_io.open_log

    def _no_delay_open_log(p: str):
        return _SlowReader(real_open(p), 0.0)

    monkeypatch.setattr(pw, "open_log", _no_delay_open_log)

    t0 = time.perf_counter()
    pw._scan_file_multi_sync([parser], path)
    sync_t = time.perf_counter() - t0

    t0 = time.perf_counter()
    dec_result = pw._scan_file_multi_decoupled([parser], path)
    dec_t = time.perf_counter() - t0

    assert _counts(dec_result) == {parser.label: 100_000}
    ratio = dec_t / sync_t
    assert ratio < 1.5, f"fast-IO overhead {ratio:.2f}x >= 1.5x (sync {sync_t*1e3:.1f}ms, decoupled {dec_t*1e3:.1f}ms)"


# ════════════════════════════════════════════════════════════════════
# 4. Memory budget: peak <= 3x file size (StringIO, no splitlines copy)
# ════════════════════════════════════════════════════════════════════


def test_decoupled_memory_within_3x_file(tmp_path):
    """文件缓冲峰值内存 <= 3×文件大小（queue 2× + 解析中 1× 的上限）。

    用 _NullParser（零产出）隔离缓冲成本——解析结果对象不属于文件缓冲预算。
    """
    lines = _gen_hit_lines(25_000)
    path = _write_log(tmp_path, "big.log", lines)
    file_size = os.path.getsize(path)
    parser = _NullParser()

    tracemalloc.start()
    try:
        result = pw._scan_file_multi_decoupled([parser], path)
        _, peak = tracemalloc.get_traced_memory()
    finally:
        tracemalloc.stop()

    assert _counts(result) == {}
    assert peak < 3 * file_size, (
        f"peak {peak/1e6:.1f}MB >= 3x file {file_size/1e6:.1f}MB"
    )


# ════════════════════════════════════════════════════════════════════
# 5. HDD-only enablement (_should_decouple + dispatch)
# ════════════════════════════════════════════════════════════════════


def test_should_decouple_always_false():
    """IO/解析解耦已关闭——所有磁盘类型统一走同步路径。"""
    assert pw._should_decouple("/some/dir/file.log") is False


def test_should_decouple_always_false_any_path():
    assert pw._should_decouple("/mnt/hdd/file.log") is False
    assert pw._should_decouple("/mnt/ssd/file.log") is False


def test_scan_file_multi_dispatches_on_disk_type(monkeypatch, tmp_path):
    from latency.parse.sdk_access_log_parser import SdkAccessLogParser

    parser = SdkAccessLogParser(None)
    path = _write_log(tmp_path, "a.log", [_SDK_LINE])

    calls = {"sync": 0, "decoupled": 0}

    def _fake_sync(parsers, p):
        calls["sync"] += 1
        return {}

    def _fake_decoupled(parsers, p):
        calls["decoupled"] += 1
        return {}

    monkeypatch.setattr(pw, "_scan_file_multi_sync", _fake_sync)
    monkeypatch.setattr(pw, "_scan_file_multi_decoupled", _fake_decoupled)

    pw._scan_file_multi([parser], str(path))

    assert calls == {"sync": 1, "decoupled": 0}


def test_single_parser_fast_path_precedes_dispatch(monkeypatch, tmp_path):
    """单解析器快路径(WorkerInfoParser.scan_file)优先于解耦分派, 不被改动。"""
    from latency.parse.worker_info_parser import WorkerInfoParser

    parser = WorkerInfoParser(None)
    path = _write_log(tmp_path, "worker_runtime.log", [_URMA_LINE])

    def _boom(*args, **kwargs):
        raise AssertionError("dispatch reached — fast path must short-circuit")

    monkeypatch.setattr(pw, "_scan_file_multi_sync", _boom)
    monkeypatch.setattr(pw, "_scan_file_multi_decoupled", _boom)
    monkeypatch.setenv("WITTY_UB_IO_DECOUPLE", "1")

    result = pw._scan_file_multi([parser], path)
    assert "Worker info parse" not in result  # scan_file 返回子 label, 非 bucket
    assert any(k.startswith("Worker ") for k in result)
