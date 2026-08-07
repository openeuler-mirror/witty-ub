#!/usr/bin/env python3
"""T7 (Block F2) unit tests: IO-aware concurrency gating in the parallel scanner.

Covers (acceptance of perf-overhaul-io-aware T7):
- io_concurrency_for mapping: hdd=3 / ssd=nvme=cpu_count / unknown=3
  (monkeypatch detect_disk_type)
- Multiprocessing path uses BOUNDED submission: at most `cap` groups in-flight
  concurrently, refill-on-completion (parent asyncio.Semaphore is a no-op
  there — P1-4 Oracle). Verified with a fake executor recording concurrency peak.
- Asyncio fallback path gates _scan_file_multi to_thread calls with
  asyncio.Semaphore(cap): concurrency peak <= cap even without the multiprocessing
  ProcessPoolExecutor bound.
- 160 tiny-file batch completes without deadlock (asyncio.wait_for guard in test,
  pytest-level timeout not required).

Run: cd src/plugins/latency && PYTHONPATH=/home/li/witty-ub_8632/src/plugins \
  .venv/bin/python -m pytest test/test_io_semaphore.py -v -p no:cacheprovider
"""
from __future__ import annotations

import asyncio
import os
import sys
import threading
import time
from concurrent.futures import Future
from pathlib import Path

import pytest

_TEST_DIR = Path(__file__).resolve().parent
_PROJECT_ROOT = _TEST_DIR.parent
sys.path.insert(0, str(_PROJECT_ROOT))

from latency.common import disk  # noqa: E402
from latency.parse.parallel_scanner import process_worker as pw  # noqa: E402
from latency.parse.parallel_scanner.scanner import ParallelFileScanner  # noqa: E402
from latency.parse.parallel_scanner.task_splitter import FileGroup  # noqa: E402
from latency.parse.sdk_access_log_parser import SdkAccessLogParser  # noqa: E402

_SDK_LINE = (
    "2026-05-11T05:25:20.207278 | I | access_recorder.cpp:220 | "
    "searchctrwirelessub-24-00031 | 3941:3970 | trace-sdk-1 |  | 0 | "
    "DS_KV_CLIENT_GET | 773 | 8395125 | {Object_key:key-sdk-1,timeout:0} | resp"
)
_SDK_LINE_2 = _SDK_LINE.replace("trace-sdk-1", "trace-sdk-2").replace(
    "3941:3970", "3941:3971"
)
_SDK_LINE_3 = _SDK_LINE.replace("trace-sdk-1", "trace-sdk-3").replace(
    "3941:3970", "3941:3972"
)


class _FakeExecutor:
    """仅实现 submit() 的假 executor: 后台线程延时完成, 记录并发峰值。

    用于验证"有界提交": 真实 ProcessPoolExecutor 会 fork 子进程, 无法在
    单测里观察 in-flight 数量; 假 executor 把 in-flight 定义为
    submitted-但-未-完成 的 future 数量。
    """

    def __init__(self, delay: float = 0.02):
        self.delay = delay
        self.lock = threading.Lock()
        self.in_flight = 0
        self.peak = 0

    def submit(self, fn, *args, **kwargs):
        with self.lock:
            self.in_flight += 1
            self.peak = max(self.peak, self.in_flight)
        fut: Future = Future()

        def _complete() -> None:
            time.sleep(self.delay)
            with self.lock:
                self.in_flight -= 1
            fut.set_result({})  # 不真正调用 fn: 只测提交并发

        threading.Thread(target=_complete, daemon=True).start()
        return fut


class _ConcurrencyTracker:
    """线程安全的并发峰值记录器, 用作 _scan_file_multi 的替身。"""

    def __init__(self, delay: float = 0.02):
        self.delay = delay
        self.lock = threading.Lock()
        self.in_flight = 0
        self.peak = 0

    def __call__(self, parsers, path):
        with self.lock:
            self.in_flight += 1
            self.peak = max(self.peak, self.in_flight)
        try:
            time.sleep(self.delay)
            return {}
        finally:
            with self.lock:
                self.in_flight -= 1


def _mk_groups(n_groups: int, files_per_group: int, path: str) -> list[FileGroup]:
    """构造 n_groups 个 FileGroup, 每个含 files_per_group 个 (path, [0]) 项。"""
    groups = []
    for g in range(n_groups):
        group = FileGroup(group_id=g)
        for _ in range(files_per_group):
            group.files.append((path, [0]))
        groups.append(group)
    return groups


# ════════════════════════════════════════════════════════════════════
# 1. io_concurrency_for 映射 (T3 已实现, 此处锁定 T7 依赖的契约)
# ════════════════════════════════════════════════════════════════════


def test_io_concurrency_mapping(monkeypatch):
    disk.detect_disk_type.cache_clear()
    cpu = os.cpu_count() or 3
    cases = {"hdd": 3, "ssd": cpu, "nvme": cpu, "unknown": 3}
    for disk_type, expected in cases.items():
        monkeypatch.setattr(disk, "detect_disk_type", lambda p, dt=disk_type: dt)
        assert disk.io_concurrency_for("/some/log/dir") == expected, (
            f"io_concurrency_for({disk_type}) != {expected}"
        )


def test_io_concurrency_mapping_uses_detect_disk_type(monkeypatch):
    """io_concurrency_for 必须走 detect_disk_type(monkeypatch 可观测)。"""
    disk.detect_disk_type.cache_clear()
    seen = []
    monkeypatch.setattr(disk, "detect_disk_type", lambda p: seen.append(p) or "hdd")
    assert disk.io_concurrency_for("/observed/dir") == 3
    assert seen == ["/observed/dir"]


# ════════════════════════════════════════════════════════════════════
# 2. Multiprocessing 路径: 有界提交 (BOUNDED submission), 峰值 <= cap
# ════════════════════════════════════════════════════════════════════


def test_multiprocessing_bounded_submission_peak_le_cap():
    """20 groups, cap=3: 同时 in-flight 的组数必须 <= 3 (而非全量提交)。"""
    scanner = ParallelFileScanner(max_processes=8, use_multiprocessing=True)
    fake = _FakeExecutor(delay=0.02)
    groups = _mk_groups(20, 1, "/nonexistent/file.log")

    results = asyncio.run(
        scanner._submit_bounded_multiprocessing(
            fake, groups, parsers_info=[], parse_config_dict=None,
            scan_scope=None, max_concurrent=3,
        )
    )

    assert len(results) == 20
    assert fake.peak <= 3, f"bounded submission peak {fake.peak} > cap 3"
    assert fake.peak >= 1, "bounded submission did not run anything"
    # 顺序保持: _merge_results 不依赖顺序, 但返回类型/长度与原实现一致
    assert all(r == {} for r in results)


def test_multiprocessing_bounded_submission_cap_2():
    """不同 cap (2) 也生效: 峰值受提交窗口限制。"""
    scanner = ParallelFileScanner(max_processes=8, use_multiprocessing=True)
    fake = _FakeExecutor(delay=0.02)
    groups = _mk_groups(12, 1, "/nonexistent/file.log")

    results = asyncio.run(
        scanner._submit_bounded_multiprocessing(
            fake, groups, parsers_info=[], parse_config_dict=None,
            scan_scope=None, max_concurrent=2,
        )
    )

    assert len(results) == 12
    assert fake.peak <= 2, f"peak {fake.peak} > cap 2"


def test_multiprocessing_bounded_submission_single_group():
    """单 group 时 cap 不应放大并发; 结果仍为 1 项。"""
    scanner = ParallelFileScanner(max_processes=8, use_multiprocessing=True)
    fake = _FakeExecutor(delay=0.02)
    groups = _mk_groups(1, 3, "/nonexistent/file.log")

    results = asyncio.run(
        scanner._submit_bounded_multiprocessing(
            fake, groups, parsers_info=[], parse_config_dict=None,
            scan_scope=None, max_concurrent=3,
        )
    )

    assert len(results) == 1
    assert fake.peak <= 1


# ════════════════════════════════════════════════════════════════════
# 3. Asyncio 降级路径: Semaphore 包 _scan_file_multi 的 to_thread
# ════════════════════════════════════════════════════════════════════


def test_asyncio_path_semaphore_peak_le_cap(monkeypatch, tmp_path):
    """32 file-tasks, cap=3 (hdd): _scan_file_multi 并发峰值必须 <= 3。

    io_concurrency=None + log_dir → 走 io_concurrency_for(log_dir) 重算,
    间接验证 scan_all 到 _scan_with_asyncio 的 cap 传递契约。
    """
    disk.detect_disk_type.cache_clear()
    monkeypatch.setattr(disk, "detect_disk_type", lambda p: "hdd")

    tracker = _ConcurrencyTracker(delay=0.02)
    monkeypatch.setattr(pw, "_scan_file_multi", tracker)

    scanner = ParallelFileScanner(use_multiprocessing=False)
    parser = SdkAccessLogParser(None)
    groups = _mk_groups(8, 4, str(tmp_path / "a.log"))

    results = asyncio.run(
        scanner._scan_with_asyncio(
            groups, [parser], scan_scope=None,
            io_concurrency=None, log_dir=str(tmp_path),
        )
    )

    assert len(results) == 8
    assert tracker.peak <= 3, f"asyncio to_thread peak {tracker.peak} > cap 3"
    assert tracker.peak >= 1, "asyncio path did not run anything"


def test_asyncio_path_explicit_cap_used(monkeypatch, tmp_path):
    """显式 io_concurrency=2 时 cap 生效 (不依赖磁盘检测)。"""
    tracker = _ConcurrencyTracker(delay=0.02)
    monkeypatch.setattr(pw, "_scan_file_multi", tracker)

    scanner = ParallelFileScanner(use_multiprocessing=False)
    parser = SdkAccessLogParser(None)
    groups = _mk_groups(6, 3, str(tmp_path / "a.log"))

    results = asyncio.run(
        scanner._scan_with_asyncio(
            groups, [parser], scan_scope=None,
            io_concurrency=2, log_dir=str(tmp_path),
        )
    )

    assert len(results) == 6
    assert tracker.peak <= 2, f"peak {tracker.peak} > explicit cap 2"


def test_asyncio_path_no_deadlock_with_io_semaphore(monkeypatch, tmp_path):
    """Semaphore 门控下 100 file-tasks 正常完成 (无死锁、无丢失)。"""
    tracker = _ConcurrencyTracker(delay=0.005)
    monkeypatch.setattr(pw, "_scan_file_multi", tracker)

    scanner = ParallelFileScanner(use_multiprocessing=False)
    parser = SdkAccessLogParser(None)
    groups = _mk_groups(10, 10, str(tmp_path / "a.log"))

    results = asyncio.run(
        scanner._scan_with_asyncio(
            groups, [parser], scan_scope=None,
            io_concurrency=4, log_dir=str(tmp_path),
        )
    )

    assert len(results) == 10
    assert tracker.peak <= 4


# ════════════════════════════════════════════════════════════════════
# 4. 160 小文件批次: 真实 multiprocessing 无死锁
# ════════════════════════════════════════════════════════════════════


def test_multiprocessing_160_small_files_no_deadlock(tmp_path):
    """160 个小文件 (每文件 3 行), cap=3: 有界提交 + 补位必须无死锁完成。

    用 asyncio.wait_for 兜底超时 (50s), 即使本机无 pytest-timeout 也不会挂死。
    总数据量 << 100KB, 不触发重型集成路径。
    """
    from latency.parse.sdk_access_log_parser import SdkAccessLogParser

    scanner = ParallelFileScanner(max_processes=8, use_multiprocessing=True)
    parser = SdkAccessLogParser(None)
    lines = [_SDK_LINE, _SDK_LINE_2, _SDK_LINE_3]

    groups: list[FileGroup] = []
    for i in range(160):
        p = tmp_path / f"file_{i:03d}.log"
        p.write_text("\n".join(lines) + "\n")
        groups.append(FileGroup(group_id=i, files=[(str(p), [0])]))

    total_bytes = sum(
        os.path.getsize(str(tmp_path / f"file_{i:03d}.log")) for i in range(160)
    )
    assert total_bytes < 100_000, f"test data too large: {total_bytes} bytes"

    async def _run():
        return await asyncio.wait_for(
            scanner._scan_with_multiprocessing(
                groups, [parser], str(tmp_path), None, None,
                io_concurrency=3,
            ),
            timeout=50,
        )

    results = asyncio.run(_run())
    assert len(results) == 160, f"expected 160 group results, got {len(results)}"
    # 每个 group 都解析出 SDK 条目 (验证 worker 真的跑了, 不只是空结果)
    sdk_counts = [len(r.get("SDK access parse", [])) for r in results]
    assert all(c == 3 for c in sdk_counts), "worker parse output drift"
