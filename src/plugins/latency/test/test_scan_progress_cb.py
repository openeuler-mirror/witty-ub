#!/usr/bin/env python3
"""Unit test: scan_all progress_cb (smooth scan sub-progress).

Verifies that ``ParallelFileScanner.scan_all`` invokes an optional
``progress_cb`` with monotonically increasing fractions ending at 1.0 when a
callback is provided (both the multiprocessing and asyncio branches), and does
not crash when the callback is None.
"""

import asyncio
import logging
from pathlib import Path

import pytest

from latency.parse import SdkAccessLogParser
from latency.parse.parallel_scanner.scanner import ParallelFileScanner
from latency.schemas.request import ParseConfig

logger = logging.getLogger(__name__)


def _make_log_dir(tmp_path: Path) -> Path:
    """3 个小文件目录, 行内容不命中解析器(不以 "2" 开头), 扫描极快."""
    log_dir = tmp_path / "logs"
    log_dir.mkdir()
    for i in range(3):
        (log_dir / f"ds_client_access_{i}.log").write_text(
            "garbage line 1\n"
            "garbage line 2\n",
            encoding="utf-8",
        )
    return log_dir


def _make_scanner(use_multiprocessing: bool) -> ParallelFileScanner:
    return ParallelFileScanner(
        max_processes=2,
        use_multiprocessing=use_multiprocessing,
    )


def _make_parsers() -> list:
    return [SdkAccessLogParser(ParseConfig())]


async def _scan_collect_fractions(scanner, log_dir, parsers):
    fractions = []

    async def cb(fraction: float) -> None:
        fractions.append(fraction)

    result = await scanner.scan_all(str(log_dir), parsers, progress_cb=cb)
    return fractions, result


def _assert_monotonic_to_one(fractions: list[float]) -> None:
    assert fractions, "progress_cb must be invoked at least once"
    assert fractions == sorted(fractions), "fractions must be monotonically increasing"
    assert all(0.0 < f <= 1.0 for f in fractions)
    assert fractions[-1] == pytest.approx(1.0)


@pytest.mark.parametrize("use_multiprocessing", [True, False])
def test_scan_all_progress_cb_monotonic(tmp_path, use_multiprocessing):
    log_dir = _make_log_dir(tmp_path)
    scanner = _make_scanner(use_multiprocessing)
    fractions, result = asyncio.run(
        _scan_collect_fractions(scanner, log_dir, _make_parsers())
    )
    _assert_monotonic_to_one(fractions)
    assert isinstance(result, dict)


def test_scan_all_multiprocessing_branch_used(tmp_path, monkeypatch):
    """3 个同尺寸文件 + max_processes=2 → BY_FILE_SIZE 拆分出 2 组,
    确保走的是 _scan_with_multiprocessing 分支(进度回调在 group 完成后触发)."""
    log_dir = _make_log_dir(tmp_path)
    scanner = _make_scanner(use_multiprocessing=True)

    async def spy(*args, **kwargs):
        raise AssertionError("asyncio branch should not be used")

    monkeypatch.setattr(scanner, "_scan_with_asyncio", spy)
    fractions, _ = asyncio.run(
        _scan_collect_fractions(scanner, log_dir, _make_parsers())
    )
    _assert_monotonic_to_one(fractions)


def test_scan_all_without_callback_does_not_crash(tmp_path):
    log_dir = _make_log_dir(tmp_path)
    scanner = _make_scanner(use_multiprocessing=False)
    result = asyncio.run(scanner.scan_all(str(log_dir), _make_parsers()))
    assert isinstance(result, dict)
