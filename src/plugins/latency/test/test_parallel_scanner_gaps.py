# -*- coding: utf-8 -*-
"""parallel_scanner 低覆盖模块补测：preprocessor。

只补全量套件未覆盖的缺口（其余模块与已测分支勿重复），目标 ≥80%：
- preprocessor: .gz 预解压 worker、递归扫描、临时目录生命周期、
  decompress_all 并行解压映射、get_effective_path 兜底、cleanup 失败告警

说明：原文件还包含 task_splitter 与 process_worker 专节（约 42 个用例），
两者依赖的模块已在 master 的 polars 重构（1b398771）中移除，用例随之删除。
"""
from __future__ import annotations

import gzip
import logging
import os
import sys
from pathlib import Path

import pytest

_TEST_DIR = Path(__file__).resolve().parent
_PROJECT_ROOT = _TEST_DIR.parent
sys.path.insert(0, str(_PROJECT_ROOT))

from latency.parse.parallel_scanner import preprocessor
from latency.parse.parallel_scanner.preprocessor import (
    LogPreprocessor,
    decompress_file_worker,
)


def _raise(exc: Exception):
    def _f(*args, **kwargs):
        raise exc

    return _f


# ════════════════════════════════════════════════════════════════════
# preprocessor.py
# ════════════════════════════════════════════════════════════════════


def _write_gz(directory: Path, name: str, text: str) -> Path:
    path = directory / name
    path.parent.mkdir(parents=True, exist_ok=True)
    with gzip.open(path, "wt", encoding="utf-8") as f:
        f.write(text)
    return path


def test_decompress_file_worker_success(tmp_path):
    gz = _write_gz(tmp_path / "SDK_10.0.0.9", "ds_client_access.log.gz", "2026 hello\n")
    out_dir = tmp_path / "out"

    gz_path, log_path = decompress_file_worker(str(gz), str(out_dir))

    assert gz_path == str(gz)
    dest = out_dir / "SDK_10.0.0.9" / "ds_client_access.log"
    assert log_path == str(dest)
    assert dest.read_text() == "2026 hello\n"


def test_decompress_file_worker_keeps_non_gz_filename(tmp_path):
    gz = _write_gz(tmp_path, "plain.log", "payload")
    _, log_path = decompress_file_worker(str(gz), str(tmp_path / "out"))
    assert os.path.basename(log_path) == "plain.log"  # 非 .gz 后缀原样保留
    assert Path(log_path).read_text() == "payload"


def test_decompress_file_worker_corrupt_returns_empty(tmp_path, caplog):
    caplog.set_level(logging.ERROR, logger="latency.parse.parallel_scanner.preprocessor")
    gz = tmp_path / "bad.log.gz"
    gz.write_bytes(b"definitely not gzip")

    gz_path, log_path = decompress_file_worker(str(gz), str(tmp_path / "out"))

    assert gz_path == str(gz)
    assert log_path == ""
    assert not (tmp_path / "out" / "bad.log").exists()
    assert "Failed to decompress" in caplog.text


def test_preprocessor_init_defaults():
    p = LogPreprocessor()
    try:
        assert p.need_cleanup is True
        assert os.path.isdir(p.temp_dir)
        assert p.max_workers == (os.cpu_count() or 4)
        assert p.path_mapping == {}
    finally:
        p.cleanup()
    assert not os.path.exists(p.temp_dir)


def test_preprocessor_init_custom(tmp_path):
    custom = str(tmp_path / "custom")
    p = LogPreprocessor(temp_dir=custom, max_workers=3)
    assert p.need_cleanup is False
    assert p.temp_dir == custom
    assert p.max_workers == 3
    assert LogPreprocessor(temp_dir=custom, max_workers=0).max_workers == (os.cpu_count() or 4)


async def test_decompress_all_without_gz_returns_empty(tmp_path):
    p = LogPreprocessor(temp_dir=str(tmp_path / "out"))
    assert await p.decompress_all(str(tmp_path)) == {}


async def test_decompress_all_maps_paths(tmp_path, monkeypatch):
    from concurrent.futures import ThreadPoolExecutor

    # 进程池在测试进程内执行，保证覆盖率可采集
    monkeypatch.setattr(preprocessor, "ProcessPoolExecutor", ThreadPoolExecutor)
    a = _write_gz(tmp_path / "logs" / "SDK_1", "a.log.gz", "aaa\n" * 100)
    b = _write_gz(tmp_path / "logs" / "SDK_2", "b.log.gz", "bbb")

    p = LogPreprocessor(temp_dir=str(tmp_path / "out"))
    mapping = await p.decompress_all(str(tmp_path / "logs"))

    assert set(mapping) == {str(a), str(b)}
    assert all(os.path.exists(v) for v in mapping.values())
    assert (tmp_path / "out" / "SDK_1" / "a.log").read_text() == "aaa\n" * 100
    assert (tmp_path / "out" / "SDK_2" / "b.log").read_text() == "bbb"
    assert p.get_effective_path(str(a)) == mapping[str(a)]
    assert p.get_effective_path(str(b)) == mapping[str(b)]


def test_scan_gz_files_recursive_and_oserror(tmp_path):
    logs = tmp_path / "logs"
    good = _write_gz(logs / "sub", "good.log.gz", "x")
    (logs / "sub" / "plain.log").write_text("no")
    broken = logs / "broken.log.gz"
    os.symlink(str(tmp_path / "missing.gz"), str(broken))  # getsize → OSError

    p = LogPreprocessor(temp_dir=str(tmp_path / "out"))
    found = p._scan_gz_files(str(logs))

    assert [path for path, _ in found] == [str(good)]
    assert found[0][1] == os.path.getsize(str(good))


def test_get_effective_path_fallback():
    p = LogPreprocessor(temp_dir="/tmp/xyz-unlikely")
    p.path_mapping["/a/b.log.gz"] = "/tmp/xyz-unlikely/a/b.log"
    assert p.get_effective_path("/a/b.log.gz") == "/tmp/xyz-unlikely/a/b.log"
    assert p.get_effective_path("/a/c.log") == "/a/c.log"


def test_cleanup_owned_dir_removed_guest_kept(tmp_path):
    owned = LogPreprocessor()
    assert os.path.isdir(owned.temp_dir)
    owned.cleanup()
    assert not os.path.exists(owned.temp_dir)
    owned.cleanup()  # 目录已不存在 → 幂等 no-op

    keep = tmp_path / "keep"
    keep.mkdir()
    LogPreprocessor(temp_dir=str(keep)).cleanup()
    assert keep.exists()  # need_cleanup=False → 不动外部目录


def test_cleanup_rmtree_failure_warns(monkeypatch, caplog, tmp_path):
    caplog.set_level(logging.WARNING, logger="latency.parse.parallel_scanner.preprocessor")
    (tmp_path / "d").mkdir()
    p = LogPreprocessor(temp_dir=str(tmp_path / "d"))
    p.need_cleanup = True
    monkeypatch.setattr(preprocessor.shutil, "rmtree", _raise(OSError("disk locked")))

    p.cleanup()  # 不得向上抛

    assert "Failed to cleanup temp dir" in caplog.text
