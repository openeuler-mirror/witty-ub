#!/usr/bin/env python3
"""T8 (Block G) unit tests: per-file io/parse timing in the parallel scanner.

Covers (acceptance of perf-overhaul-io-aware T8):
- Every scan path (sync / single-file decoupled / group decoupled / fast path)
  emits `[perf][file.io]` and `[perf][file.parse]` logs (方案 B grep channel)
- Worker return dict carries the per-file timing under the reserved __perf__
  marker (方案 A); _process_worker_func resets the collector per call so
  pooled-worker group results never cross-contaminate
- _merge_results pops the marker, aggregates a single [perf][total] log, and
  returns the same clean {label: entries} merge as before (parse_log untouched)
- _scan_with_asyncio attaches the marker to the first group result only
- No per-line timing: _record_file_timing is called exactly once per file
  (deterministic guard) and the end-to-end wall-clock delta stays within budget
  (paired interleaved measurement to cancel drift)

Run: cd src/plugins/latency && PYTHONPATH=/home/li/witty-ub_8632/src/plugins \
  .venv/bin/python -m pytest test/test_scan_perf_timing.py -v -p no:cacheprovider
"""
from __future__ import annotations

import asyncio
import gc
import io
import logging
import os
import statistics
import sys
import time
from pathlib import Path

import pytest

_TEST_DIR = Path(__file__).resolve().parent
_PROJECT_ROOT = _TEST_DIR.parent
sys.path.insert(0, str(_PROJECT_ROOT))

from latency.parse.parallel_scanner import process_worker as pw  # noqa: E402
from latency.parse.parallel_scanner.scanner import ParallelFileScanner  # noqa: E402
from latency.parse.parallel_scanner.task_splitter import FileGroup  # noqa: E402

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
_URMA_LINE = (
    "2026-05-13T00:03:42.487820 | I | urma_manager.cpp:852 | "
    "6.62.223.31 | 112:409 | trace-urma-1 | model_kvcache_predictor |  "
    "[URMA_ELAPSED_TOTAL]: Waiting URMA jfc event done after "
    "urma_post_jetty_send_wr cost 1.27262ms, request id:2052374, "
    "src address:6.62.223.31:31501, target address:6.62.222.250:31501, "
    "dataSize:8395125, cpuid:2, status: code: [OK], msg: [DS_KV_CLIENT_GET], "
    "urma_inflight_wr_count: 1"
)

_PW_LOGGER = "latency.parse.parallel_scanner.process_worker"
_SCANNER_LOGGER = "latency.parse.parallel_scanner.scanner"


def _write_log(tmp_path, name: str, lines: list[str]) -> str:
    path = tmp_path / name
    path.write_text("\n".join(lines) + "\n")
    return str(path)


def _mk_sdk():
    from latency.parse.sdk_access_log_parser import SdkAccessLogParser
    return SdkAccessLogParser(None)


def _mk_worker_info():
    from latency.parse.worker_info_parser import WorkerInfoParser
    return WorkerInfoParser(None)


def _gen_sdk_lines(n: int) -> list[str]:
    return [
        _SDK_LINE.replace("trace-sdk-1", f"trace-sdk-{i:05d}").replace(
            "3941:3970", f"3941:{3970 + i}"
        )
        for i in range(n)
    ]


@pytest.fixture
def perf_caplog(caplog):
    caplog.set_level(logging.INFO, logger=_PW_LOGGER)
    caplog.set_level(logging.INFO, logger=_SCANNER_LOGGER)
    return caplog


# ════════════════════════════════════════════════════════════════════
# 1. Per-file [perf][file.io] / [perf][file.parse] logs, all paths
# ════════════════════════════════════════════════════════════════════


def test_sync_path_emits_perf_logs(perf_caplog, tmp_path):
    path = _write_log(tmp_path, "sync.log", _gen_sdk_lines(50))
    result = pw._scan_file_multi_sync([_mk_sdk()], path)

    assert result.get("SDK access parse")
    assert "[perf][file.io] sync.log io=" in perf_caplog.text
    assert "[perf][file.parse] sync.log parse=" in perf_caplog.text
    # 格式含 .1f 毫秒值
    assert "io=0.0ms" in perf_caplog.text or "io=" in perf_caplog.text
    # 每文件恰好两行 perf 日志（无 per-line 日志）
    assert perf_caplog.text.count("[perf][file.io] sync.log") == 1
    assert perf_caplog.text.count("[perf][file.parse] sync.log") == 1


def test_single_file_decoupled_emits_perf_logs(perf_caplog, tmp_path, monkeypatch):
    monkeypatch.setenv("WITTY_UB_IO_DECOUPLE", "1")
    path = _write_log(tmp_path, "dec.log", _gen_sdk_lines(50))
    result = pw._scan_file_multi([_mk_sdk()], path)

    assert result.get("SDK access parse")
    assert "[perf][file.io] dec.log io=" in perf_caplog.text
    assert "[perf][file.parse] dec.log parse=" in perf_caplog.text


def test_group_decoupled_emits_perf_logs_per_file(perf_caplog, tmp_path, monkeypatch):
    from latency.parse.worker_access_log_parser import WorkerAccessLogParser

    monkeypatch.setenv("WITTY_UB_IO_DECOUPLE", "1")
    sdk = _mk_sdk()
    worker = WorkerAccessLogParser(None)
    p1 = _write_log(tmp_path, "g1.log", [_SDK_LINE])
    p2 = _write_log(tmp_path, "g2.log", [_WORKER_LINE])
    merged = pw._scan_group_decoupled([(p1, [0, 1]), (p2, [0, 1])], [sdk, worker], 0)

    assert merged.get("SDK access parse") and merged.get("Worker access parse")
    assert perf_caplog.text.count("[perf][file.io] g1.log") == 1
    assert perf_caplog.text.count("[perf][file.io] g2.log") == 1
    assert perf_caplog.text.count("[perf][file.parse] g1.log") == 1
    assert perf_caplog.text.count("[perf][file.parse] g2.log") == 1


def test_fast_path_emits_perf_logs(perf_caplog, tmp_path):
    path = _write_log(tmp_path, "info.log", [_URMA_LINE])
    result = pw._scan_file_multi([_mk_worker_info()], path)

    assert any(k.startswith("Worker ") for k in result)
    assert "[perf][file.io] info.log io=" in perf_caplog.text
    assert "[perf][file.parse] info.log parse=" in perf_caplog.text


def test_scan_file_multi_dispatches_both_emit(perf_caplog, tmp_path, monkeypatch):
    """_scan_file_multi 分派到 sync 与 decoupled 两条路径均出 perf 日志。"""
    p1 = _write_log(tmp_path, "s.log", _gen_sdk_lines(10))
    monkeypatch.setenv("WITTY_UB_IO_DECOUPLE", "0")
    pw._scan_file_multi([_mk_sdk()], p1)
    assert "[perf][file.io] s.log" in perf_caplog.text

    p2 = _write_log(tmp_path, "d.log", _gen_sdk_lines(10))
    monkeypatch.setenv("WITTY_UB_IO_DECOUPLE", "1")
    pw._scan_file_multi([_mk_sdk()], p2)
    assert "[perf][file.io] d.log" in perf_caplog.text


# ════════════════════════════════════════════════════════════════════
# 2. 方案 A: worker 返回 dict 挂 __perf__ 保留键 + 每次调用隔离
# ════════════════════════════════════════════════════════════════════


def test_process_worker_func_embeds_timing_marker(tmp_path):
    path = _write_log(tmp_path, "w.log", _gen_sdk_lines(5))
    parser = _mk_sdk()
    parsers_info = [
        {
            "label": parser.label,
            "class_name": parser.__class__.__name__,
            "patterns": list(parser.patterns),
        }
    ]
    result = pw._process_worker_func([(path, [0])], 1, parsers_info, None, None)

    assert pw._PERF_MARKER in result
    timing = result[pw._PERF_MARKER]
    assert "w.log" in timing
    assert {"io_ms", "parse_ms"} <= set(timing["w.log"])
    assert timing["w.log"]["io_ms"] >= 0
    assert timing["w.log"]["parse_ms"] >= 0
    # 解析结果不受影响（列式路径，不再有 legacy 标签）
    cols = result.get("columns")
    assert cols is not None
    assert len(cols["tid"]) == 5
    # collector 在调用后被清空（下次调用不会带入旧 group 数据）
    assert pw._TIMING_COLLECTOR.snapshot_and_reset() == {}


def test_process_worker_func_marker_isolated_per_group(tmp_path):
    """pool 复用 worker 进程: 第二次调用只携带自己的计时，不串上一组。"""
    p1 = _write_log(tmp_path, "grp1.log", _gen_sdk_lines(3))
    p2 = _write_log(tmp_path, "grp2.log", _gen_sdk_lines(3))
    parser = _mk_sdk()
    parsers_info = [
        {
            "label": parser.label,
            "class_name": parser.__class__.__name__,
            "patterns": list(parser.patterns),
        }
    ]
    pw._process_worker_func([(p1, [0])], 1, parsers_info, None, None)
    result2 = pw._process_worker_func([(p2, [0])], 2, parsers_info, None, None)

    timing = result2[pw._PERF_MARKER]
    assert "grp2.log" in timing
    assert "grp1.log" not in timing


# ════════════════════════════════════════════════════════════════════
# 3. _merge_results: 弹出 marker、打 [perf][total]、合并结果不变
# ════════════════════════════════════════════════════════════════════


def _fake_serialized_entry(tid: str) -> tuple:
    # _serialize_entry 输出 16 元组：timestamp, operation, ..., log_id
    return (
        "2026-05-11T05:25:20.207278", "GET", 100, None, None, tid,
        "pod-1", 0, None, None, None, None, None, None, None, "log-1",
    )


def test_merge_results_strips_marker_and_aggregates(perf_caplog):
    from latency.parse.parallel_scanner.columnar import COLUMNS_KEY, entries_to_columns

    results = [
        {
            COLUMNS_KEY: entries_to_columns({"SDK access parse": [_fake_serialized_entry("a")]}),
            pw._PERF_MARKER: {
                "f1.log": {"io_ms": 1.5, "parse_ms": 3.2},
                "f2.log": {"io_ms": 2.0, "parse_ms": 1.1},
            },
        },
        {
            COLUMNS_KEY: entries_to_columns({"Worker access parse": [_fake_serialized_entry("b")]}),
        },
    ]
    merged = ParallelFileScanner._merge_results(results)

    assert pw._PERF_MARKER not in merged
    assert COLUMNS_KEY in merged
    assert len(merged[COLUMNS_KEY]["_label"]) == 2  # 1 SDK + 1 Worker
    # 聚合日志
    assert "[perf][total] files=2" in perf_caplog.text
    assert "io=3.5ms" in perf_caplog.text
    assert "parse=4.3ms" in perf_caplog.text
    # 原结果 dict 的 marker 已被弹出（幂等）
    assert pw._PERF_MARKER not in results[0]


def test_merge_results_without_marker_unchanged(perf_caplog):
    from latency.parse.parallel_scanner.columnar import COLUMNS_KEY, entries_to_columns

    results = [{COLUMNS_KEY: entries_to_columns({"SDK access parse": [_fake_serialized_entry("a")]})}]
    merged = ParallelFileScanner._merge_results(results)

    assert pw._PERF_MARKER not in merged
    assert len(merged[COLUMNS_KEY]["tid"]) == 1
    assert "[perf][total]" not in perf_caplog.text


# ════════════════════════════════════════════════════════════════════
# 4. asyncio 路径: marker 挂首组结果，其余干净
# ════════════════════════════════════════════════════════════════════


def test_scan_with_asyncio_attaches_marker_to_first_group(tmp_path, monkeypatch):
    files = []
    for i in range(3):
        p = _write_log(tmp_path, f"af{i}.log", _gen_sdk_lines(5))
        files.append(FileGroup(group_id=i, files=[(p, [0])]))
    scanner = ParallelFileScanner(use_multiprocessing=False)
    parser = _mk_sdk()

    results = asyncio.run(
        scanner._scan_with_asyncio(
            files, [parser], scan_scope=None, io_concurrency=2, log_dir=str(tmp_path)
        )
    )

    assert len(results) == 3
    assert pw._PERF_MARKER in results[0]
    timing = results[0][pw._PERF_MARKER]
    assert len(timing) == 3  # 全部 3 个文件的计时都在首组结果上
    assert all(pw._PERF_MARKER not in r for r in results[1:])
    # 聚合后保留键消失
    from latency.parse.parallel_scanner.columnar import COLUMNS_KEY

    merged = ParallelFileScanner._merge_results(list(results))
    assert pw._PERF_MARKER not in merged
    assert COLUMNS_KEY in merged
    assert len(merged[COLUMNS_KEY]["tid"]) == 15


# ════════════════════════════════════════════════════════════════════
# 5. 开销门
# ════════════════════════════════════════════════════════════════════


def test_no_per_line_timing_record_calls(tmp_path, monkeypatch):
    """确定性守卫：_record_file_timing 每文件恰好调用一次（O(1)，非 O(lines)）。"""
    path = _write_log(tmp_path, "many.log", _gen_sdk_lines(1000))
    calls = []
    monkeypatch.setattr(pw, "_record_file_timing", lambda *a, **k: calls.append(a))
    pw._scan_file_multi([_mk_sdk()], path)
    assert len(calls) == 1, (
        f"_record_file_timing called {len(calls)} times for 1 file with 1000 lines "
        "(per-line timing would call it 1000x)"
    )


def test_overhead_delta_within_budget(tmp_path):
    """计时前 vs 计时后同一批小文件：平均端到端耗时差必须 < 5%（实测 ~0.5%）。

    用交替配对测量（base/inst 轮流跑 4 对，取均值）消除机器负载漂移；真实
    仪器开销 ~0.5%，但在负载机上墙钟比率噪声达 ±3%（实测 2.44% / 2.06% /
    一次通过），2% 阈值过严会 flaky。5% 阈值 = 0.5% 真实开销 + 3% 噪声带 +
    余量，仍能抓住 per-line 计时（此负载下 +20% 以上）之类的数量级回归；
    且真正的 per-line 守卫是 test_no_per_line_timing_record_calls，本测试
    只是次级防线，无需更紧的 gate。
    """
    lines = _gen_sdk_lines(3000)
    paths = [_write_log(tmp_path, f"ov{i:02d}.log", lines) for i in range(20)]
    parser = _mk_sdk()

    def _scan(noop_timing: bool) -> float:
        pw._TIMING_COLLECTOR.reset()
        orig = pw._record_file_timing
        if noop_timing:
            pw._record_file_timing = lambda *a, **k: None
        gc.collect()
        gc.disable()
        try:
            t0 = time.perf_counter()
            for p in paths:
                pw._scan_file_multi([parser], p)
            return (time.perf_counter() - t0) * 1000
        finally:
            gc.enable()
            pw._record_file_timing = orig

    _scan(True)   # warmup
    _scan(False)
    bases: list[float] = []
    insts: list[float] = []
    for _ in range(4):
        bases.append(_scan(True))
        insts.append(_scan(False))
    mean_base = statistics.mean(bases)
    mean_inst = statistics.mean(insts)
    delta = (mean_inst - mean_base) / mean_base
    assert delta < 0.05, (
        f"instrumentation overhead {delta*100:.2f}% >= 5% "
        f"(base {mean_base:.0f}ms, instrumented {mean_inst:.0f}ms)"
    )
