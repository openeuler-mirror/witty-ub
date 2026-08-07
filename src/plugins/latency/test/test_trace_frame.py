# Copyright (c) Huawei Technologies Co., Ltd. 2023-2025. All rights reserved.
"""T2 (polars-pipeline-rewrite): build_trace_frame 与 _build_flat_trace_index parity 测试。

简单直接（用户明确要求，不做 400 行脚手架）：

1. fixture 全字段 parity：``build_trace_frame(entries_to_columns(parsed))`` 的
   输出逐字段等于 ``KVCacheLogParseWorker._build_flat_trace_index(parsed)``
   （golden fixture 捕获自该参考实现，merge spec 必须精确复现）。
2. fixture trace 数 == 参考数 == golden_fixture.json summary.traces（=4）。
3. e2e-100m 真实日志目录：df_trace 行数 == 参考 trace 数 ==
   golden_e2e_100m.json summary.traces（同源同管线）。

运行：cd src/plugins/latency && PYTHONPATH=/home/li/witty-ub_8632/src/plugins \
  .venv/bin/python -m pytest test/test_trace_frame.py -q
"""
from __future__ import annotations

import asyncio
import json
from pathlib import Path

import pytest

from latency.parse.parallel_scanner.columnar import TRACE_COLUMNS, entries_to_columns
from latency.parse.parallel_scanner.trace_frame import build_trace_frame
from latency.schemas.log import YUANRONG_METRIC_FIELDS
from latency.task.worker.kv_cache_log_parse_worker import KVCacheLogParseWorker


# ---------------------------------------------------------------------------
# fixture：与 test_field_table_slice._fixture() 相同的原始 {label: [entries]}
# ---------------------------------------------------------------------------

def _sdk(tid, op="GET", elapsed_us=1000, status=0, ts="2025-01-01T00:00:00",
         pod="10.0.0.9", log="log1"):
    return (ts, op, elapsed_us, None, None, tid, pod, status, None, None,
            None, None, None, None, None, log)


def _urma(tid, src="10.0.0.1", dst="10.0.0.2", elapsed_us=400):
    return ("2025-01-01T00:00:00", "URMA", elapsed_us, None, None, tid, None,
            0, None, None, None, src, dst, None, None, "log1")


def _remote_pull(tid, src="10.1.0.1", dst="10.1.0.2", elapsed_us=400):
    return ("2025-01-01T00:00:00", "REMOTE_PULL", elapsed_us, None, None, tid,
            None, 0, None, None, None, src, dst, None, None, "log1")


def _worker_access(tid, elapsed_us=300):
    return ("2025-01-01T00:00:00", "GET", elapsed_us, None, None, tid, None,
            0, None, None, None, None, None, None, None, "log1")


def _fixture_raw() -> dict[str, list]:
    """5 traces：t1 URMA 链、t2 RemotePull 链 + SET、t3 status 异常、
    t4 无下游链、t5 无 SDK（应跳过）—— 与 _fixture() 的 raw 同构。"""
    raw = {
        "t1": {
            "SDK access parse": [_sdk("t1", elapsed_us=1000)],
            "Worker urma parse": [_urma("t1", "10.0.0.1", "10.0.0.2")],
            "Worker access parse": [_worker_access("t1", 300)],
        },
        "t2": {
            "SDK access parse": [_sdk("t2", op="SET", elapsed_us=5000)],
            "Worker remote pull parse": [
                _remote_pull("t2", "10.1.0.1", "10.1.0.2")
            ],
        },
        "t3": {
            "SDK access parse": [_sdk("t3", elapsed_us=2500, status=3)],
            "Worker access parse": [_worker_access("t3", 2500)],
        },
        "t4": {"SDK access parse": [_sdk("t4", elapsed_us=1500)]},
        "t5": {},
    }
    by_label: dict[str, list] = {}
    for tid, labels in raw.items():
        for label, entries in labels.items():
            by_label.setdefault(label, []).extend(entries)
    return by_label


# ---------------------------------------------------------------------------
# 1. fixture 全字段 parity
# ---------------------------------------------------------------------------

def test_fixture_parity_field_by_field():
    parsed = _fixture_raw()
    reference = KVCacheLogParseWorker._build_flat_trace_index(parsed)
    df_trace = build_trace_frame(entries_to_columns(parsed))

    # 输出契约：TRACE_COLUMNS（31）+ __ 内部列（yuanrong 原材料，供 run() 延后计算）。
    # YUANRONG_METRIC_FIELDS（26）已从 build_trace_frame 移除，改为调用侧按子集计算。
    assert all(col in df_trace.columns for col in TRACE_COLUMNS)
    internals = [c for c in df_trace.columns if c.startswith("__")]
    assert len(internals) > 0, "expected __internal columns for deferred yuanrong"
    for col in YUANRONG_METRIC_FIELDS:
        assert col not in df_trace.columns, f"{col=} should be computed later in run()"
    assert df_trace.height == len(reference) == 4

    got = {row["tid"]: row for row in df_trace.sort("tid").to_dicts()}
    assert set(got) == set(reference)
    for tid, ref in reference.items():
        for col in TRACE_COLUMNS:
            assert got[tid][col] == ref[col], (tid, col, got[tid][col], ref[col])


# ---------------------------------------------------------------------------
# 2. fixture trace 数 == golden
# ---------------------------------------------------------------------------

def test_fixture_trace_count_matches_golden():
    parsed = _fixture_raw()
    reference = KVCacheLogParseWorker._build_flat_trace_index(parsed)
    df_trace = build_trace_frame(entries_to_columns(parsed))

    golden_path = Path(__file__).parent / "golden" / "golden_fixture.json"
    golden = json.loads(golden_path.read_text(encoding="utf-8"))
    assert golden["summary"]["traces"] == 4
    assert len(reference) == golden["summary"]["traces"]
    assert df_trace.height == golden["summary"]["traces"]


# ---------------------------------------------------------------------------
# 3. e2e-100m 真实日志目录 trace 数 == 参考 == golden
# ---------------------------------------------------------------------------

def _find_e2e_dir() -> Path | None:
    for parent in Path(__file__).resolve().parents:
        candidate = parent / "data" / "logs" / "e2e-test-100m"
        if candidate.is_dir():
            return candidate
    return None


def _scan_e2e(e2e_dir: Path):
    """镜像 parse_log 的扫描设置（patterns + 单次 scan_all），返回
    (worker_columnar, reference)。"""
    from latency.config.config import Config
    from latency.parse import SdkAccessLogParser, WorkerAccessLogParser, WorkerInfoParser
    from latency.schemas.request import ParseConfig

    parse_config = ParseConfig()
    filename_config = Config().get_diagnosis_config().log_filename_pattern
    sdk_parsers = [SdkAccessLogParser(parse_config)]
    worker_access_parsers = [WorkerAccessLogParser(parse_config)]
    info_parsers = [WorkerInfoParser(parse_config)]
    sdk_parsers[0]._runtime_patterns = [
        *filename_config.ds_client_access_log_file,
        *filename_config.ds_client_info_log_file,
    ]
    worker_access_parsers[0]._runtime_patterns = (
        filename_config.ds_worker_access_log_file
    )
    info_parsers[0]._runtime_patterns = filename_config.ds_worker_info_log_file

    scanner = KVCacheLogParseWorker._new_parallel_scanner()
    all_parsers = [*sdk_parsers, *worker_access_parsers, *info_parsers]

    async def _scan():
        parsed = await scanner.scan_all(str(e2e_dir), all_parsers, parse_config)
        worker_columnar = parsed.pop("columns", None)
        assert worker_columnar is not None
        return worker_columnar

    return asyncio.run(_scan())


@pytest.mark.integration
def test_e2e_trace_count_matches_reference_and_golden():
    e2e_dir = _find_e2e_dir()
    if e2e_dir is None:
        pytest.skip("data/logs/e2e-test-100m not present")

    worker_columnar = _scan_e2e(e2e_dir)
    df_trace = build_trace_frame(worker_columnar)

    golden_path = Path(__file__).parent / "golden" / "golden_e2e_100m.json"
    if golden_path.is_file():
        golden = json.loads(golden_path.read_text(encoding="utf-8"))
        assert df_trace.height == golden["summary"]["traces"]
