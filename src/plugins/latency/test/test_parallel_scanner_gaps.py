# -*- coding: utf-8 -*-
"""parallel_scanner 低覆盖模块补测：preprocessor / task_splitter / process_worker。

只补全量套件未覆盖的缺口（其余模块与已测分支勿重复），目标各 ≥80%：
- preprocessor: .gz 预解压 worker、递归扫描、临时目录生命周期
- task_splitter: BY_FILE_COUNT / BY_PARSER_COUNT 策略、未知策略、OSError 分支
- process_worker: 进程入口 cProfile 包装、spill/decoupled 分派、prefilter
  边界（自定义谓词/无关键词/批量过滤失败）、解耦队列错误路径、
  _parse_lines 异常隔离（pod_ip/match_line/迭代器）、序列化回环
"""
from __future__ import annotations

import gzip
import io
import logging
import os
import sys
from datetime import datetime
from pathlib import Path

import pytest

_TEST_DIR = Path(__file__).resolve().parent
_PROJECT_ROOT = _TEST_DIR.parent
sys.path.insert(0, str(_PROJECT_ROOT))

from latency.ENUM.ds_log import EntryType, TupleField
from latency.ENUM.task import TaskSplitStrategy
from latency.parse.base_parser import LogParser
from latency.parse.parallel_scanner import preprocessor
from latency.parse.parallel_scanner import process_worker as pw
from latency.parse.parallel_scanner.preprocessor import (
    LogPreprocessor,
    decompress_file_worker,
)
from latency.parse.parallel_scanner.task_splitter import (
    FileGroup,
    ScanTaskSplitter,
)
from latency.schemas.ds_log import LogEntry

_PW_LOGGER = "latency.parse.parallel_scanner.process_worker"

_SDK_LINE = (
    "2026-05-11T05:25:20.207278 | I | access_recorder.cpp:220 | "
    "searchctrwirelessub-24-00031 | 3941:3970 | trace-sdk-1 |  | 0 | "
    "DS_KV_CLIENT_GET | 773 | 8395125 | {Object_key:key-sdk-1,timeout:0} | resp"
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


def _write_log(tmp_path, name: str, lines: list[str]) -> str:
    path = tmp_path / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n")
    return str(path)


def _mk_parsers():
    from latency.parse.sdk_access_log_parser import SdkAccessLogParser
    from latency.parse.worker_access_log_parser import WorkerAccessLogParser
    from latency.parse.worker_info_parser import WorkerInfoParser

    return SdkAccessLogParser(None), WorkerAccessLogParser(None), WorkerInfoParser(None)


def _parsers_info(parsers) -> list[dict]:
    return [
        {
            "label": p.label,
            "class_name": p.__class__.__name__,
            "patterns": list(p.patterns),
        }
        for p in parsers
    ]


def _raise(exc: Exception):
    def _f(*args, **kwargs):
        raise exc

    return _f


class _StubParser(LogParser):
    """可控桩解析器：可按需让 extract_pod_ip / match_line 抛错。"""

    label = "stub parse"
    _keywords = ("HIT",)

    @property
    def patterns(self) -> list[str]:
        return []

    def extract_pod_ip(self, path: str) -> str:
        if getattr(self, "_pod_ip_error", False):
            raise ValueError("pod ip extraction failed")
        return "10.0.0.7"

    def match_line(self, line: str, pod_ip: str):
        seen = getattr(self, "seen_pod_ips", None)
        if seen is None:
            seen = self.seen_pod_ips = []
        seen.append(pod_ip)
        if getattr(self, "_match_error", False):
            raise ValueError("match_line exploded")
        if "HIT" not in line:
            return None
        return LogEntry(
            timestamp=datetime(2026, 5, 11, 5, 25, 20),
            trace_id="trace-stub",
            pod_ip=pod_ip,
            elapsed_us=1.0,
            entry_type=EntryType.SDK_GET,
        )


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


# ════════════════════════════════════════════════════════════════════
# task_splitter.py
# ════════════════════════════════════════════════════════════════════


def test_file_group_add_file_accumulates():
    g = FileGroup(group_id=0)
    g.add_file("a.log", [0, 1], 10)
    g.add_file("b.log", [2], 5)
    assert g.file_count == 2
    assert g.files == [("a.log", [0, 1]), ("b.log", [2])]
    assert g.total_size_bytes == 15
    assert g.total_parser_calls == 3


def test_split_by_file_count_round_robin(tmp_path):
    sdk, worker, _ = _mk_parsers()
    paths = []
    for i in range(5):
        p = tmp_path / f"f{i}.log"
        p.write_text("x" * (i + 1))
        paths.append(str(p))
    missing = "/nonexistent/missing.log"  # getsize → OSError → size 0
    fpm = {p: [sdk, worker] for p in paths}
    fpm[missing] = [sdk]

    splitter = ScanTaskSplitter(fpm, [sdk, worker], 2, TaskSplitStrategy.BY_FILE_COUNT)
    groups = splitter.split()

    assert 1 <= len(groups) <= 2
    all_files = [f for g in groups for f, _ in g.files]
    assert sorted(all_files) == sorted(paths + [missing])
    assert sum(g.total_size_bytes for g in groups) == sum(
        os.path.getsize(p) for p in paths
    )
    assert sum(g.total_parser_calls for g in groups) == 11  # 5×2 + 1×1


def test_split_by_parser_count_balances_calls(tmp_path):
    sdk, worker, _ = _mk_parsers()
    a, b, c, d = (tmp_path / n for n in ("a.log", "b.log", "c.log", "d.log"))
    for p in (a, b, c, d):
        p.write_text("x")
    missing = "/nonexistent/m.log"
    fpm = {
        str(a): [sdk, worker],   # cost 2
        str(d): [sdk, worker],   # cost 2
        str(b): [sdk],           # cost 1
        str(c): [worker],        # cost 1
        missing: [sdk],          # cost 1, size 0 (OSError)
    }

    splitter = ScanTaskSplitter(fpm, [sdk, worker], 2, TaskSplitStrategy.BY_PARSER_COUNT)
    groups = splitter.split()

    assert len(groups) == 2
    assert sorted(g.total_parser_calls for g in groups) == [3, 4]
    assert sum(g.file_count for g in groups) == 5
    assert sum(g.total_size_bytes for g in groups) == 4  # 4 个 1 字节真实文件


def test_split_unknown_strategy_raises():
    sdk, worker, _ = _mk_parsers()
    splitter = ScanTaskSplitter({}, [sdk, worker], 2)
    splitter.strategy = "bogus"
    with pytest.raises(ValueError, match="Unknown strategy"):
        splitter.split()


def test_split_by_file_size_missing_file_counts_as_zero():
    sdk, worker, _ = _mk_parsers()
    fpm = {"/nonexistent/a.log": [sdk], "/nonexistent/b.log": [worker]}
    splitter = ScanTaskSplitter(fpm, [sdk, worker], 2, TaskSplitStrategy.BY_FILE_SIZE)
    groups = splitter.split()

    # 两个文件 size 均为 0 → 贪心全部落在同一组
    assert len(groups) == 1
    assert groups[0].file_count == 2
    assert groups[0].total_size_bytes == 0
    assert groups[0].group_id == 0


# ════════════════════════════════════════════════════════════════════
# process_worker.py — 进程入口与分派
# ════════════════════════════════════════════════════════════════════


def test_process_worker_func_delegates_without_profile_env(monkeypatch, tmp_path):
    monkeypatch.delenv("WITTY_UB_CPROFILE_DIR", raising=False)
    path = _write_log(tmp_path, "plain.log", [_SDK_LINE])

    result = pw.process_worker_func([(path, [0])], 7, _parsers_info([_mk_parsers()[0]]), None, None, None)

    assert "columns" in result
    assert len(result["columns"]["tid"]) == 1


def test_process_worker_func_profiles_when_env_set(monkeypatch, tmp_path):
    profile_dir = tmp_path / "profiles"
    monkeypatch.setenv("WITTY_UB_CPROFILE_DIR", str(profile_dir))
    path = _write_log(tmp_path, "p.log", [_SDK_LINE])

    result = pw.process_worker_func([(path, [0])], 3, _parsers_info([_mk_parsers()[0]]), None, None, None)

    assert "columns" in result
    assert list(profile_dir.glob("worker-*-group-3-*.prof")), "cProfile 产物未落盘"


def test_process_worker_func_spilled_output(tmp_path):
    from latency.parse.parallel_scanner.columnar import COLUMNS_KEY

    path = _write_log(tmp_path, "sp.log", [_SDK_LINE])
    out = tmp_path / "spill"
    out.mkdir()

    result = pw._process_worker_func(
        [(path, [0])], 0, _parsers_info([_mk_parsers()[0]]), None, None, str(out)
    )

    assert "spill_paths" in result
    assert result["entry_counts"]["SDK access parse"] == 1
    assert pw._PERF_MARKER in result
    assert COLUMNS_KEY not in result  # spill 路径不走列式返回


def test_process_worker_func_decoupled_group(monkeypatch, tmp_path):
    monkeypatch.setattr(pw, "_should_decouple", lambda path: True)
    path = _write_log(tmp_path, "g.log", [_SDK_LINE])

    result = pw._process_worker_func(
        [(path, [0])], 0, _parsers_info([_mk_parsers()[0]]), None, None, None
    )

    assert len(result["columns"]["tid"]) == 1
    assert pw._PERF_MARKER in result  # 解耦路径记录了 io/parse 计时
    assert "g.log" in result[pw._PERF_MARKER]


# ════════════════════════════════════════════════════════════════════
# process_worker.py — _prefilter_lines 边界
# ════════════════════════════════════════════════════════════════════


def test_prefilter_unknown_custom_predicate_passes_all_through():
    class CustomPredicate:
        _line_may_match = staticmethod(lambda line: True)

    source = io.StringIO("2026 a\n2026 b\n")
    # 未知自定义谓词必须直通行，不允许丢行
    assert list(pw._prefilter_lines([CustomPredicate()], source)) == ["2026 a\n", "2026 b\n"]


def test_prefilter_no_keywords_passes_all_through():
    class NoKeywords:
        _keywords = ()

    source = io.StringIO("anything\n")
    assert list(pw._prefilter_lines([NoKeywords()], source)) == ["anything\n"]


def test_prefilter_batch_failure_falls_back_to_direct_scan(monkeypatch):
    import polars as pl

    lines = ["2026 noise line\n"] * 300  # 单批 ≥256 行才走 polars 过滤
    source = io.StringIO("".join(lines))
    monkeypatch.setattr(pl.DataFrame, "filter", _raise(RuntimeError("filter exploded")))

    assert list(pw._prefilter_lines([_mk_parsers()[0]], source)) == lines


# ════════════════════════════════════════════════════════════════════
# process_worker.py — 解析器重建 / 组扫描错误路径
# ════════════════════════════════════════════════════════════════════


def test_rebuild_parsers_unknown_class_warns(caplog):
    caplog.set_level(logging.WARNING, logger=_PW_LOGGER)
    parsers = pw._rebuild_parsers([{"class_name": "NopeParser", "patterns": []}], None)
    assert parsers == []
    assert "Unknown parser class: NopeParser" in caplog.text


def test_rebuild_parsers_sets_runtime_patterns():
    info = {"class_name": "SdkAccessLogParser", "patterns": ["*_custom.log"]}
    parsers = pw._rebuild_parsers([info], None)
    assert parsers[0]._runtime_patterns == ["*_custom.log"]


def test_scan_group_serial_continues_after_file_failure(monkeypatch, tmp_path, caplog):
    caplog.set_level(logging.WARNING, logger=_PW_LOGGER)
    bad = _write_log(tmp_path, "bad.log", [_SDK_LINE])
    good = _write_log(tmp_path, "good.log", [_SDK_LINE])
    real = pw._scan_file_multi

    def flaky(parsers, path):
        if path == bad:
            raise RuntimeError("scan exploded")
        return real(parsers, path)

    monkeypatch.setattr(pw, "_scan_file_multi", flaky)
    merged = pw._scan_group_serial([(bad, [0]), (good, [0])], [_mk_parsers()[0]], 0)

    assert len(merged["SDK access parse"]) == 1  # 好文件不受坏文件影响
    assert "Failed to scan" in caplog.text


def test_scan_group_decoupled_skips_unreadable_file(caplog):
    caplog.set_level(logging.WARNING, logger=_PW_LOGGER)
    merged = pw._scan_group_decoupled([("/nonexistent/x.log", [0])], [_mk_parsers()[0]], 0)
    assert dict(merged) == {}
    assert "Error reading /nonexistent/x.log" in caplog.text


def test_scan_group_decoupled_parse_failure_returns_empty(monkeypatch, tmp_path):
    path = _write_log(tmp_path, "g.log", [_SDK_LINE])
    monkeypatch.setattr(pw, "_parse_lines", _raise(RuntimeError("parse boom")))

    merged = pw._scan_group_decoupled([(path, [0])], [_mk_parsers()[0]], 0)

    assert merged["SDK access parse"] == []  # 失败文件仍要给出空 label 结果


# ════════════════════════════════════════════════════════════════════
# process_worker.py — IO 基元与单文件路径
# ════════════════════════════════════════════════════════════════════


def test_read_whole_file_error_paths(tmp_path, caplog):
    caplog.set_level(logging.WARNING, logger=_PW_LOGGER)
    ok = _write_log(tmp_path, "ok.log", ["hello"])
    truncated = tmp_path / "trunc.log.gz"
    truncated.write_bytes(gzip.compress(b"2026 x\n" * 10)[:-6])  # 截断 footer

    assert pw._read_whole_file(ok) == "hello\n"
    assert pw._read_whole_file(str(truncated)) is None  # EOFError → 跳过
    assert pw._read_whole_file(str(tmp_path / "missing.log")) is None  # 打开失败
    assert "Skipping corrupted file" in caplog.text
    assert "Error reading" in caplog.text


def test_iter_lines_variants():
    assert list(pw._iter_lines("a\nb\n")) == ["a\n", "b\n"]
    assert list(pw._iter_lines("a\nb")) == ["a\n", "b"]  # 无尾随换行
    assert list(pw._iter_lines("")) == []


def test_scan_file_multi_dispatches_decoupled_when_enabled(monkeypatch, tmp_path):
    monkeypatch.setattr(pw, "_should_decouple", lambda path: True)
    path = _write_log(tmp_path, "d.log", [_SDK_LINE])
    calls = []

    def fake(parsers, p):
        calls.append(p)
        return {}

    monkeypatch.setattr(pw, "_scan_file_multi_decoupled", fake)
    pw._scan_file_multi([_mk_parsers()[0]], path)  # 单解析器无 scan_file → 走分派
    assert calls == [path]


def test_scan_file_multi_sync_fast_path(tmp_path):
    path = _write_log(tmp_path, "w.log", [_URMA_LINE])
    result = pw._scan_file_multi_sync([_mk_parsers()[2]], path)
    assert any(k.startswith("Worker ") for k in result)  # scan_file 子 label


def test_scan_file_multi_sync_handles_parse_errors(monkeypatch, tmp_path, caplog):
    caplog.set_level(logging.WARNING, logger=_PW_LOGGER)
    path = _write_log(tmp_path, "s.log", [_SDK_LINE])
    parser = _mk_parsers()[0]

    monkeypatch.setattr(pw, "_parse_lines", _raise(EOFError("corrupt")))
    assert pw._scan_file_multi_sync([parser], path) == {"SDK access parse": []}
    assert "Skipping corrupted file" in caplog.text

    monkeypatch.setattr(pw, "_parse_lines", _raise(RuntimeError("boom")))
    assert pw._scan_file_multi_sync([parser], path) == {"SDK access parse": []}
    assert "Error reading" in caplog.text


def test_scan_file_polars_read_failure_falls_back(monkeypatch, tmp_path, caplog):
    import polars as pl

    caplog.set_level(logging.WARNING, logger=_PW_LOGGER)
    path = _write_log(tmp_path, "fb.log", [_SDK_LINE])
    monkeypatch.setattr(pl, "read_csv", _raise(OSError("disk error")))

    result = pw._scan_file_polars([_mk_parsers()[0]], path)

    assert len(result["SDK access parse"]) == 1  # 回退同步路径后正常解析
    assert "falling back to sync" in caplog.text


def test_scan_file_polars_empty_file_falls_back_to_sync(tmp_path):
    # 完全空文件：polars new_columns 抛 ShapeError → 回退同步路径
    empty = tmp_path / "empty.log"
    empty.write_text("")
    result = pw._scan_file_polars([_mk_parsers()[0]], str(empty))
    assert result == {"SDK access parse": []}


def test_scan_file_polars_zero_height_short_circuits(monkeypatch, tmp_path):
    import polars as pl

    path = _write_log(tmp_path, "zh.log", [_SDK_LINE])
    empty_df = pl.DataFrame({"line": []}, schema={"line": pl.String})
    monkeypatch.setattr(pl, "read_csv", lambda *a, **k: empty_df)

    result = pw._scan_file_polars([_mk_parsers()[0]], path)

    assert result == {"SDK access parse": []}


def test_scan_file_polars_keyword_filtered_empty(tmp_path):
    # 行首为 '2' 但不含任何关键词 → 关键词过滤后 0 行
    path = _write_log(tmp_path, "nf.log", ["2026-01-01T00:00:00 nothing interesting here"])
    result = pw._scan_file_polars([_mk_parsers()[0]], path)
    assert result == {"SDK access parse": []}


def test_scan_file_polars_no_timestamp_lines(tmp_path):
    # 无任何 '2' 开头行 → starts_with 过滤后 0 行，短路返回
    path = _write_log(tmp_path, "nt.log", ["garbage line", "noise"])
    result = pw._scan_file_polars([_mk_parsers()[0]], path)
    assert result == {"SDK access parse": []}


# ════════════════════════════════════════════════════════════════════
# process_worker.py — 单文件 IO/解析解耦
# ════════════════════════════════════════════════════════════════════


def test_scan_file_multi_decoupled_fast_path(tmp_path):
    path = _write_log(tmp_path, "w.log", [_URMA_LINE])
    result = pw._scan_file_multi_decoupled([_mk_parsers()[2]], path)
    assert any(k.startswith("Worker ") for k in result)


def test_scan_file_multi_decoupled_parses_entries(tmp_path):
    path = _write_log(tmp_path, "d.log", [_SDK_LINE, _SDK_LINE.replace("trace-sdk-1", "trace-sdk-2")])
    result = pw._scan_file_multi_decoupled([_mk_parsers()[0]], path)
    assert len(result["SDK access parse"]) == 2


@pytest.mark.filterwarnings("ignore::pytest.PytestUnhandledThreadExceptionWarning")
def test_scan_file_multi_decoupled_stop_sentinel_when_read_fails(monkeypatch, tmp_path):
    # IO 线程在读文件前崩溃 → 队列只收到 STOP 哨兵 → 解析线程给出空 label 结果。
    # （生产契约：_read_whole_file 吞掉一切异常；此处故意打破以覆盖 STOP-first 分支，
    # reader 线程的未捕获异常由 filterwarnings 抑制。）
    path = _write_log(tmp_path, "d.log", [_SDK_LINE])
    monkeypatch.setattr(pw, "_read_whole_file", _raise(RuntimeError("io boom")))
    result = pw._scan_file_multi_decoupled([_mk_parsers()[0]], path)
    assert result == {"SDK access parse": []}


def test_scan_file_multi_decoupled_none_buffer(monkeypatch, tmp_path):
    path = _write_log(tmp_path, "d.log", [_SDK_LINE])
    monkeypatch.setattr(pw, "_read_whole_file", lambda p: None)
    result = pw._scan_file_multi_decoupled([_mk_parsers()[0]], path)
    assert result == {"SDK access parse": []}


def test_scan_file_multi_decoupled_parse_failure(monkeypatch, tmp_path, caplog):
    caplog.set_level(logging.WARNING, logger=_PW_LOGGER)
    path = _write_log(tmp_path, "d.log", [_SDK_LINE])
    monkeypatch.setattr(pw, "_parse_lines", _raise(RuntimeError("parse boom")))
    result = pw._scan_file_multi_decoupled([_mk_parsers()[0]], path)
    assert result == {"SDK access parse": []}
    assert "Failed to scan" in caplog.text


# ════════════════════════════════════════════════════════════════════
# process_worker.py — _parse_lines 异常隔离与分支
# ════════════════════════════════════════════════════════════════════


def test_parse_lines_pod_ip_failure_defaults_to_empty(tmp_path, caplog):
    caplog.set_level(logging.WARNING, logger=_PW_LOGGER)
    path = _write_log(tmp_path, "pod.log", [])
    stub = _StubParser()
    stub._pod_ip_error = True

    result = pw._parse_lines([stub], path, ["2026 HIT line\n"])

    assert "Failed to extract pod_ip" in caplog.text
    assert stub.seen_pod_ips == [""]  # 失败兜底为空 pod_ip 且传入 match_line
    assert len(result["stub parse"]) == 1


def test_parse_lines_progress_logging(monkeypatch, tmp_path, caplog):
    caplog.set_level(logging.INFO, logger=_PW_LOGGER)
    monkeypatch.setattr(pw, "_PROGRESS_UPDATE_LINES", 2)
    path = _write_log(tmp_path, "prog.log", [])

    pw._parse_lines([_mk_parsers()[0]], path, [_SDK_LINE + "\n"] * 5)

    assert caplog.text.count("[Multi] scanning prog.log") == 2  # 第 2、4 行各一次


def test_parse_lines_skips_non_timestamp_lines(tmp_path):
    path = _write_log(tmp_path, "skip.log", [])
    result = pw._parse_lines([_mk_parsers()[0]], path, ["garbage\n", "", _SDK_LINE + "\n"])
    assert len(result["SDK access parse"]) == 1


def test_parse_lines_list_entries_routed_to_sink(tmp_path):
    from latency.parse.parallel_scanner.spill import EntrySpool

    parser = _mk_parsers()[2]  # WorkerInfoParser.match_line 返回 list
    path = _write_log(tmp_path, "w_runtime.log", [])

    with EntrySpool(tmp_path, 0) as spool:
        result = pw._parse_lines([parser], path, [_URMA_LINE + "\n"], entry_sink=spool)
        assert result["Worker info parse"] == []  # 条目走 sink 而非 results
        assert spool.size == 1
        finished = spool.finish()

    assert finished["entry_counts"]["Worker info parse"] == 1


def test_parse_lines_match_line_error_isolated(tmp_path, caplog):
    caplog.set_level(logging.WARNING, logger=_PW_LOGGER)
    path = _write_log(tmp_path, "boom.log", [])
    stub = _StubParser()
    stub._match_error = True

    result = pw._parse_lines([stub], path, ["2026 HIT here\n", _SDK_LINE + "\n"])

    assert result["stub parse"] == []
    assert "error on boom.log:1" in caplog.text


def test_parse_lines_survives_iterator_errors(tmp_path, caplog):
    caplog.set_level(logging.WARNING, logger=_PW_LOGGER)
    path = str(tmp_path / "iter.log")
    parser = _mk_parsers()[0]

    def gen_eof():
        yield _SDK_LINE + "\n"
        raise EOFError("corrupt stream")

    result = pw._parse_lines([parser], path, gen_eof())
    assert len(result["SDK access parse"]) == 1  # 异常前已解析的条目保留
    assert "Skipping corrupted file" in caplog.text

    def gen_err():
        raise RuntimeError("stream boom")
        yield  # pragma: no cover

    result = pw._parse_lines([parser], path, gen_err())
    assert result["SDK access parse"] == []
    assert "Error reading" in caplog.text


# ════════════════════════════════════════════════════════════════════
# process_worker.py — entry 序列化
# ════════════════════════════════════════════════════════════════════


def test_serialize_deserialize_roundtrip():
    entry = LogEntry(
        timestamp=datetime(2026, 5, 11, 5, 25, 20, 207278),
        trace_id="trace-1",
        pod_ip="10.0.0.9",
        elapsed_us=1234.0,
        entry_type=EntryType.SDK_GET,
        operation="GET",
        data_size="8395125",
        object_key="key-1",
        status_code=0,
        resp_msg="resp",
        cluster_name="c1",
        src_addr="1.1.1.1:1",
        dst_addr="2.2.2.2:2",
        inflight_count=3,
        request_size="1024",
        log_id="log-1",
    )
    assert pw._deserialize_entry(pw._serialize_entry(entry)) == entry


def test_deserialize_entry_type_string_conversion():
    t = list(
        pw._serialize_entry(
            LogEntry(
                timestamp=datetime(2026, 1, 1),
                trace_id="t",
                pod_ip="p",
                elapsed_us=1.0,
                entry_type=EntryType.SDK_GET,
            )
        )
    )
    t[TupleField.ENTRY_TYPE] = "URMA"
    assert pw._deserialize_entry(tuple(t)).entry_type is EntryType.URMA

    t[TupleField.ENTRY_TYPE] = "NOT_A_TYPE"
    assert pw._deserialize_entry(tuple(t)).entry_type is None
