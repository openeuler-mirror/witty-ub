# Copyright (c) Huawei Technologies Co., Ltd. 2023-2025. All rights reserved.
"""task/worker 下 5 个具体 worker 的单元测试。

只测各 worker 自身逻辑：纯逻辑函数直接调，编排路径用假 manager 走通。
不覆盖 task/worker/base.py、task_handler 等文件（另有覆盖）。
"""

from __future__ import annotations

import asyncio
import os
import subprocess
import time
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, Mock

import pytest

from latency.ENUM.ds_log import EntryType, TupleField
from latency.ENUM.task import TaskStatusEnum, TaskTypeEnum
from latency.parse.parallel_scanner.columnar import entries_to_columns
from latency.parse.parallel_scanner.trace_frame import build_trace_frame
from latency.parse.worker_info_parser import (
    LOCAL_WORKER_COST_LABEL,
    QUERY_META_LABEL,
    REMOTE_PULL_LABEL,
    URMA_LABEL,
)
from latency.task.worker.base import BaseWorker
import latency.task.worker.kv_cache_log_parse_worker as kv_module
from latency.task.worker.kv_cache_log_parse_worker import KVCacheLogParseWorker
import latency.task.worker.store_trace_context_logs_worker as store_module
from latency.task.worker.store_trace_context_logs_worker import (
    ContextStoreError,
    StoreTraceContextLogsWorker,
    cleanup_temp_dirs,
)
import latency.task.worker.kv_cache_log_event_diagnosis_worker as event_module
from latency.task.worker.kv_cache_log_event_diagnosis_worker import (
    KVCacheLogEventDiagnosisWorker,
)
import latency.task.worker.brpc_log_diagnosis_worker as brpc_diag_module
from latency.task.worker.brpc_log_diagnosis_worker import (
    BrpcDiagnosisWorkerError,
    BrpcLogDiagnosisWorker,
)
import latency.task.worker.brpc_log_parse_worker as brpc_parse_module
from latency.task.worker.brpc_log_parse_worker import BrpcLogParseWorker


# ---------------------------------------------------------------------------
# 公共辅助
# ---------------------------------------------------------------------------

def _run(coro):
    return asyncio.run(coro)


def _entry(tid, op="GET", elapsed_us=1000, ts="2025-01-01T00:00:00",
           src=None, dst=None, entry_type=None, status=0, pod=None):
    return (ts, op, elapsed_us, None, None, tid, pod, status, None,
            entry_type, None, src, dst, None, None, "log1")


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
    """4 个合法 trace（t5 无 SDK 被跳过）：与 test_trace_frame 同构。"""
    raw = {
        "t1": {
            "SDK access parse": [_sdk("t1", elapsed_us=1000)],
            "Worker urma parse": [_urma("t1", "10.0.0.1", "10.0.0.2")],
            "Worker access parse": [_worker_access("t1", 300)],
        },
        "t2": {
            "SDK access parse": [_sdk("t2", op="SET", elapsed_us=5000)],
            "Worker remote pull parse": [_remote_pull("t2", "10.1.0.1", "10.1.0.2")],
        },
        "t3": {
            "SDK access parse": [_sdk("t3", elapsed_us=2500, status=3)],
            "Worker access parse": [_worker_access("t3", 2500)],
        },
        "t4": {"SDK access parse": [_sdk("t4", elapsed_us=1500)]},
    }
    by_label: dict[str, list] = {}
    for labels in raw.values():
        for label, entries in labels.items():
            by_label.setdefault(label, []).extend(entries)
    return by_label


def _df():
    """4 trace 的 df_trace（t2 total 5.0ms 达阈值）。"""
    return build_trace_frame(entries_to_columns(_fixture_raw()))


def _fake_config(retry_times: int = 3):
    config = SimpleNamespace(
        get_config=lambda: SimpleNamespace(
            task=SimpleNamespace(task_retry_times=retry_times)
        ),
        get_diagnosis_config=lambda: SimpleNamespace(
            log_filename_pattern=SimpleNamespace(
                ds_client_access_log_file=[],
                ds_client_info_log_file=[],
                ds_worker_access_log_file=[],
                ds_worker_info_log_file=[],
            )
        ),
    )
    return lambda: config


class _FakeScanner:
    def __init__(self, scan_result: dict):
        self.scan_all = AsyncMock(return_value=scan_result)
        self.metrics = SimpleNamespace(
            build_map_time_ms=1.0,
            split_time_ms=2.0,
            scan_time_ms=3.0,
            total_files=4,
            total_processes=2,
            total_entries=10,
        )


def _mode(mode_id, children=None, error_code="K_NAME(1004)"):
    return SimpleNamespace(
        id=mode_id,
        children_failure_mode_ids=children,
        error_code=error_code,
    )


def _task(task_id="task-1", op_id="log-1", status=TaskStatusEnum.RUNNING,
          retry_times=0, task_type=TaskTypeEnum.KV_CACHE_LOG_PARSE_WORKER,
          kb_id="kb-1"):
    return SimpleNamespace(
        id=task_id,
        op_id=op_id,
        kb_id=kb_id,
        retry_times=retry_times,
        status=status,
        task_type=task_type,
    )


# ---------------------------------------------------------------------------
# Section A: KVCacheLogParseWorker
# ---------------------------------------------------------------------------


class TestKVCacheLogParseWorkerInitReinit:
    def _patch_reset_managers(self, monkeypatch):
        """reinit/stop 前置清理 5 张表，全部 mock 成空操作。"""
        for mgr, methods in (
            (kv_module.LogParseResultPGManager,
             ["update_log_parse_results_existed_status_by_log_id"]),
            (kv_module.AnomalousEventPGManager,
             ["update_anomalous_events_existed_status_by_log_id"]),
            (kv_module.AnomalousEventChainPGManager,
             ["update_event_chains_existed_status_by_log_id"]),
            (kv_module.SrcDstAggregatedEventPGManager,
             ["update_aggregated_events_existed_status_by_log_id"]),
            (kv_module.TaskReportPGManager,
             ["update_task_reports_existed_status_by_task_id"]),
            (kv_module.TimeWindowAggregatedEventPGManager,
             ["delete_by_log_id"]),
        ):
            for meth in methods:
                monkeypatch.setattr(mgr, meth, AsyncMock())

    def test_init_returns_none_without_log_file(self, monkeypatch):
        monkeypatch.setattr(
            kv_module.LogFilePGManager,
            "get_log_file_by_log_file_id",
            AsyncMock(return_value=None),
        )
        assert _run(KVCacheLogParseWorker.init("log-1")) is None

    def test_init_returns_none_without_kb(self, monkeypatch):
        monkeypatch.setattr(
            kv_module.LogFilePGManager,
            "get_log_file_by_log_file_id",
            AsyncMock(return_value=SimpleNamespace(kb_id="kb-1", name="f")),
        )
        monkeypatch.setattr(
            kv_module.LogKnowledgePGManager,
            "get_log_kb_by_kb_id",
            AsyncMock(return_value=None),
        )
        assert _run(KVCacheLogParseWorker.init("log-1")) is None

    def test_init_creates_task(self, monkeypatch):
        monkeypatch.setattr(
            kv_module.LogFilePGManager,
            "get_log_file_by_log_file_id",
            AsyncMock(return_value=SimpleNamespace(kb_id="kb-1", name="f")),
        )
        monkeypatch.setattr(
            kv_module.LogKnowledgePGManager,
            "get_log_kb_by_kb_id",
            AsyncMock(return_value=SimpleNamespace(id="kb-1")),
        )
        add_task = AsyncMock()
        report = AsyncMock()
        monkeypatch.setattr(kv_module.TaskPGManager, "add_task", add_task)
        monkeypatch.setattr(BaseWorker, "report", report)

        task_id = _run(KVCacheLogParseWorker.init("log-1"))

        assert task_id == add_task.await_args.args[0].id
        created = add_task.await_args.args[0]
        assert created.task_type == TaskTypeEnum.KV_CACHE_LOG_PARSE_WORKER
        assert created.status == TaskStatusEnum.PENDING
        report.assert_awaited_once()

    def test_reinit_returns_false_without_task(self, monkeypatch):
        monkeypatch.setattr(
            kv_module.TaskPGManager,
            "get_task_by_task_id",
            AsyncMock(return_value=None),
        )
        assert _run(KVCacheLogParseWorker.reinit("task-1")) is False

    def test_reinit_stops_when_retry_exceeded(self, monkeypatch):
        task = _task(retry_times=4)
        monkeypatch.setattr(
            kv_module.TaskPGManager,
            "get_task_by_task_id",
            AsyncMock(return_value=task),
        )
        report = AsyncMock()
        monkeypatch.setattr(kv_module, "Config", _fake_config(retry_times=3))
        monkeypatch.setattr(BaseWorker, "report", report)
        self._patch_reset_managers(monkeypatch)

        assert _run(KVCacheLogParseWorker.reinit("task-1")) is False
        report.assert_not_awaited()

    def test_reinit_ok_within_limit(self, monkeypatch):
        task = _task(retry_times=1)
        monkeypatch.setattr(
            kv_module.TaskPGManager,
            "get_task_by_task_id",
            AsyncMock(return_value=task),
        )
        report = AsyncMock()
        monkeypatch.setattr(kv_module, "Config", _fake_config(retry_times=3))
        monkeypatch.setattr(BaseWorker, "report", report)
        self._patch_reset_managers(monkeypatch)

        assert _run(KVCacheLogParseWorker.reinit("task-1")) is True
        report.assert_awaited_once_with("task-1", "Task reinitialized", 0.0)


class TestKVCacheLogParseWorkerPureLogic:
    def test_split_worker_info_entries_tuple_and_append(self):
        urma_tuple = _entry("t1", entry_type=EntryType.URMA.value)
        unknown_tuple = _entry("t9", entry_type="UNKNOWN_KIND")
        parsed = {
            "Worker info parse": [urma_tuple, unknown_tuple],
            URMA_LABEL: [_entry("t2", entry_type=EntryType.URMA.value)],
        }
        KVCacheLogParseWorker._split_worker_info_entries(parsed)
        assert "Worker info parse" not in parsed
        # 未知 entry_type 被丢弃，已知条目追加不覆盖
        assert len(parsed[URMA_LABEL]) == 2

    def test_split_worker_info_entries_object_form(self):
        obj_enum = SimpleNamespace(entry_type=EntryType.URMA)
        obj_str = SimpleNamespace(entry_type=EntryType.LINK.value)
        parsed = {"Worker info parse": [obj_enum, obj_str]}
        KVCacheLogParseWorker._split_worker_info_entries(parsed)
        from latency.parse.worker_info_parser import LINK_LABEL
        assert len(parsed[URMA_LABEL]) == 1
        assert len(parsed[LINK_LABEL]) == 1

    def test_split_worker_info_entries_no_info(self):
        parsed = {"SDK access parse": [_entry("t1")]}
        KVCacheLogParseWorker._split_worker_info_entries(parsed)
        assert set(parsed) == {"SDK access parse"}

    def test_trace_ids_tuple_object_empty(self):
        assert KVCacheLogParseWorker._trace_ids([]) == set()
        tuples = [_entry("t1"), _entry("t2"), _entry("")]
        assert KVCacheLogParseWorker._trace_ids(tuples) == {"t1", "t2"}
        objs = [SimpleNamespace(trace_id="t3"), SimpleNamespace(trace_id="")]
        assert KVCacheLogParseWorker._trace_ids(objs) == {"t3"}

    def test_build_trace_overlap_stats(self):
        parsed = {
            "SDK access parse": [_entry("s1"), _entry("s2")],
            "Worker access parse": [_entry("s1"), _entry("w3")],
            URMA_LABEL: [_entry("s1")],
            REMOTE_PULL_LABEL: [_entry("w3")],
            QUERY_META_LABEL: [_entry("q1")],
            LOCAL_WORKER_COST_LABEL: [_entry("s1")],
        }
        stats = KVCacheLogParseWorker._build_trace_overlap_stats(parsed)
        assert stats == {
            "sdk_trace_ids": 2,
            "worker_trace_ids": 2,
            "urma_trace_ids": 1,
            "remote_pull_trace_ids": 1,
            "query_meta_trace_ids": 1,
            "timed_trace_ids": 1,
            "sdk_worker_trace_overlap": 1,
            "worker_urma_trace_overlap": 1,
            "worker_remote_pull_trace_overlap": 1,
            "worker_query_meta_trace_overlap": 0,
            "worker_timed_trace_overlap": 1,
        }

    def test_bucket_epoch_and_format(self):
        assert KVCacheLogParseWorker._bucket_epoch_10s("2025-01-01T00:00:00") == 1735689600
        assert KVCacheLogParseWorker._bucket_epoch_10s("not-a-timestamp") is None
        assert (
            KVCacheLogParseWorker._format_bucket_epoch(1735689600)
            == "2025-01-01 00:00:00"
        )

    def test_expand_worker_access_patterns(self):
        expanded = kv_module._expand_worker_access_patterns(
            ["access.log", "access.log", "access.log.gz", "", "other.log"]
        )
        assert expanded == [
            "access.log",
            "access*.log",
            "access.log.gz",
            "access*.log.gz",
            "other.log",
        ]

    def test_trace_row_count_polars_and_dict(self):
        assert kv_module._trace_row_count(SimpleNamespace(height=4)) == 4
        assert kv_module._trace_row_count({"a": 1, "b": 2, "c": 3}) == 3

    def test_make_field_row_variants(self):
        flat = {
            "tid": "t1", "total_ms": 1.0, "total_latency": 1.0,
            "src": "1.1.1.1", "dst": "2.2.2.2", "op": "GET",
            "operation": "GET", "op_key": "GET",
            "bucket_epoch": 1735689600, "log_id": "log-1",
            "status_code": 0, "timestamp": "2025-01-01 00:00:00",
            "pod_ip": ["10.0.0.1", "10.0.0.2"],
            "cluster_name": ["cA", "cB"], "data_size": "128",
            "inflight_count": 7, "c2w_urma_latency": 0.4,
        }
        row = KVCacheLogParseWorker._make_field_row(
            flat, log_file_id="log-x", is_anomalous=True
        )
        assert row.trace_id == "t1"
        assert row.log_id == "log-x"
        assert row.is_anomalous is True
        assert row.pod_ips == ["10.0.0.1", "10.0.0.2"]
        assert row.cluster_name == "cA, cB"
        assert row.data_size == "128"
        assert row.urma_inflight_count == 7
        assert row.c2w_latency == 0.4
        assert row.created_at

        scalar = dict(flat, pod_ip="10.0.0.3", cluster_name="cC",
                      inflight_count="bad", data_size=None)
        row2 = KVCacheLogParseWorker._make_field_row(scalar)
        assert row2.pod_ips == ["10.0.0.3"]
        assert row2.cluster_name == "cC"
        assert row2.data_size is None
        assert row2.urma_inflight_count is None

        empty = dict(flat, pod_ip=None, cluster_name=None)
        row3 = KVCacheLogParseWorker._make_field_row(empty)
        assert row3.pod_ips is None
        assert row3.cluster_name is None


class TestKVCacheLogParseWorkerParseLog:
    def test_requires_log_id_or_dir(self, monkeypatch):
        with pytest.raises(ValueError):
            _run(KVCacheLogParseWorker.parse_log())
        monkeypatch.setattr(
            kv_module.LogFilePGManager,
            "get_log_file_by_log_file_id",
            AsyncMock(return_value=None),
        )
        with pytest.raises(ValueError):
            _run(KVCacheLogParseWorker.parse_log(log_id="log-404"))

    def test_log_dir_branch_uses_global_config_and_scanner(self, monkeypatch, tmp_path):
        log_dir = tmp_path / "logs"
        log_dir.mkdir()
        df = _df()
        scanner = _FakeScanner({"trace_frame": df, "entry_counts": {}})
        monkeypatch.setattr(
            KVCacheLogParseWorker, "_new_parallel_scanner", lambda: scanner
        )
        monkeypatch.setattr(
            kv_module, "Config",
            _fake_config(retry_times=3),
        )
        monkeypatch.setattr(BaseWorker, "report", AsyncMock())

        result = _run(
            KVCacheLogParseWorker.parse_log(log_dir=str(log_dir), task_id="task-1")
        )
        assert result.height == 4
        scanner.scan_all.assert_awaited_once()

    def test_log_id_branch_reads_log_file_and_kb_config(self, monkeypatch, tmp_path):
        log_dir = tmp_path / "logs"
        log_dir.mkdir()
        df = _df()
        scanner = _FakeScanner({"trace_frame": df, "entry_counts": {}})
        monkeypatch.setattr(
            KVCacheLogParseWorker, "_new_parallel_scanner", lambda: scanner
        )
        monkeypatch.setattr(
            kv_module.LogFilePGManager,
            "get_log_file_by_log_file_id",
            AsyncMock(return_value=SimpleNamespace(kb_id="kb-1", file_path=str(log_dir))),
        )
        monkeypatch.setattr(
            "latency.database.managers.diagnosis_config.DiagnosisConfigPGManager.get_or_create",
            AsyncMock(return_value=SimpleNamespace(log_filename_pattern=SimpleNamespace(
                ds_client_access_log_file=[], ds_client_info_log_file=[],
                ds_worker_access_log_file=[], ds_worker_info_log_file=[],
            ))),
        )

        result = _run(KVCacheLogParseWorker.parse_log(log_id="log-1"))
        assert result.height == 4
        # 未传 log_dir 时使用 log_file.file_path
        assert scanner.scan_all.await_args.args[0] == str(log_dir)

    def test_missing_columnar_output_raises(self, monkeypatch, tmp_path):
        scanner = _FakeScanner({})
        monkeypatch.setattr(
            KVCacheLogParseWorker, "_new_parallel_scanner", lambda: scanner
        )
        monkeypatch.setattr(
            kv_module, "Config", _fake_config(retry_times=3)
        )
        with pytest.raises(RuntimeError):
            _run(KVCacheLogParseWorker.parse_log(log_dir=str(tmp_path)))

    def test_columns_branch_builds_trace_frame(self, monkeypatch, tmp_path):
        fake_df = _df()
        column_rows = {"tid": ["t1"], "_label": ["SDK access parse"]}
        scanner = _FakeScanner({"columns": column_rows})
        monkeypatch.setattr(
            KVCacheLogParseWorker, "_new_parallel_scanner", lambda: scanner
        )
        monkeypatch.setattr(
            kv_module, "Config", _fake_config(retry_times=3)
        )
        # master 的 build_trace_frame 签名带 threshold_ms kwarg（trace_frame.py:446）
        monkeypatch.setattr(
            kv_module, "build_trace_frame", lambda rows, threshold_ms=None: fake_df
        )

        result = _run(KVCacheLogParseWorker.parse_log(log_dir=str(tmp_path)))
        assert result is fake_df


class TestKVCacheLogParseWorkerStoreResult:
    def _detail_row(self, tid="t2"):
        return KVCacheLogParseWorker._make_field_row(
            {"tid": tid, "total_ms": 1.0, "total_latency": 1.0},
            is_anomalous=True,
        )

    def test_store_all_success(self, monkeypatch):
        add_detail = AsyncMock(return_value=True)
        add_sd = AsyncMock(return_value=2)
        add_tw = AsyncMock(return_value=3)
        monkeypatch.setattr(
            kv_module.LogParseResultPGManager,
            "add_log_parse_results",
            add_detail,
        )
        monkeypatch.setattr(
            kv_module.SrcDstAggregatedEventPGManager,
            "add_aggregated_events",
            add_sd,
        )
        monkeypatch.setattr(
            kv_module.TimeWindowAggregatedEventPGManager,
            "add_events",
            add_tw,
        )
        sd = [SimpleNamespace(kb_id=None)]
        tw = [SimpleNamespace(kb_id=None), SimpleNamespace(kb_id=None)]

        ok = _run(KVCacheLogParseWorker.store_result(
            [self._detail_row()], sd, tw, kb_id="kb-9",
        ))
        assert ok is True
        assert sd[0].kb_id == "kb-9"
        assert tw[0].kb_id == "kb-9"
        add_detail.assert_awaited_once()
        add_sd.assert_awaited_once()
        add_tw.assert_awaited_once()

    def test_store_detail_failure_marks_failed(self, monkeypatch):
        monkeypatch.setattr(
            kv_module.LogParseResultPGManager,
            "add_log_parse_results",
            AsyncMock(return_value=False),
        )
        ok = _run(KVCacheLogParseWorker.store_result([self._detail_row()], [], None))
        assert ok is False

    def test_store_src_dst_exception_marks_failed(self, monkeypatch):
        monkeypatch.setattr(
            kv_module.LogParseResultPGManager,
            "add_log_parse_results",
            AsyncMock(return_value=True),
        )
        monkeypatch.setattr(
            kv_module.SrcDstAggregatedEventPGManager,
            "add_aggregated_events",
            AsyncMock(side_effect=RuntimeError("pg down")),
        )
        monkeypatch.setattr(
            kv_module.TimeWindowAggregatedEventPGManager,
            "add_events",
            AsyncMock(return_value=0),
        )
        ok = _run(KVCacheLogParseWorker.store_result([self._detail_row()], [SimpleNamespace(kb_id=None)], []))
        assert ok is False

    def test_store_empty_inputs_succeed(self):
        assert _run(KVCacheLogParseWorker.store_result([], [], None)) is True


class TestKVCacheLogParseWorkerDetailBatches:
    # 说明：master 已把 _iter_detail_batches 重构为 _iter_detail_frames
    # （trace_index + top1000_tids + threshold_ms + anomalous_only_count，
    # 异常不再由显式集合传入，而是阈值推导），_store_detail_batches 委托
    # LogParseResultPGManager.add_log_parse_result_batches 的写法已删，
    # 改为 _store_detail_frames 直连 PGManager COPY（由
    # test_compact_trace_frames.py 的 bounded COPY 用例覆盖），对应用例删除。
    _TOP = {"t1", "t2", "t3", "t4"}

    def test_iter_detail_frames_top_and_anomaly(self):
        df = _df()
        agg_map = {("10.1.0.1", "10.1.0.2", "SET"): "agg-2"}
        frames = list(KVCacheLogParseWorker._iter_detail_frames(
            df, self._TOP, 5.0, agg_map, "log-x", 0,
        ))
        rows = [row for frame in frames for row in frame.iter_rows(named=True)]
        # 4 trace 全部进 top_k(1000)，t2（total_ms=5.0 达阈值）是异常
        assert len(rows) == 4
        by_tid = {row["tid"]: row for row in rows}
        assert by_tid["t2"]["is_anomalous"] is True
        assert by_tid["t2"]["aggregated_event_id"] == "agg-2"
        assert by_tid["t2"]["log_id"] == "log-x"
        assert by_tid["t1"]["is_anomalous"] is False
        assert by_tid["t1"]["aggregated_event_id"] == ""

    def test_iter_detail_frames_batch_size_splits(self):
        df = _df()
        frames = list(KVCacheLogParseWorker._iter_detail_frames(
            df, self._TOP, 5.0, {}, "log-x", 0, batch_size=1,
        ))
        assert len(frames) == 4
        assert all(frame.height == 1 for frame in frames)

    def test_iter_detail_frames_invalid_batch_size(self):
        df = _df()
        with pytest.raises(ValueError):
            list(KVCacheLogParseWorker._iter_detail_frames(
                df, self._TOP, 5.0, {}, "log-x", 0, batch_size=0,
            ))


class TestKVCacheLogParseWorkerRun:
    def _wire_run(self, monkeypatch, *, parse_result=None, parse_exc=None,
                  store_ok=True):
        task = _task()
        monkeypatch.setattr(
            kv_module.TaskPGManager,
            "get_task_by_task_id",
            AsyncMock(return_value=task),
        )
        monkeypatch.setattr(
            kv_module.TaskPGManager, "update_task", AsyncMock()
        )
        monkeypatch.setattr(
            kv_module.LogFilePGManager,
            "get_log_file_by_log_file_id",
            AsyncMock(return_value=SimpleNamespace(kb_id="kb-1")),
        )
        monkeypatch.setattr(
            kv_module.LogFilePGManager, "update_log_file", AsyncMock()
        )
        monkeypatch.setattr(
            kv_module.LogKnowledgePGManager, "refresh_kb_counters", AsyncMock()
        )
        monkeypatch.setattr(
            "latency.database.managers.diagnosis_config.DiagnosisConfigPGManager.get_or_create",
            AsyncMock(return_value=SimpleNamespace(log_analyzer_params=None)),
        )
        df = parse_result if parse_result is not None else _df()
        parse_log = AsyncMock(return_value=df)
        if parse_exc is not None:
            parse_log = AsyncMock(side_effect=parse_exc)
        monkeypatch.setattr(KVCacheLogParseWorker, "parse_log", parse_log)
        sd_events = [SimpleNamespace(kb_id=None)]
        agg_map = {("10.1.0.1", "10.1.0.2", "SET"): "agg-2"}
        tw_events = [SimpleNamespace(kb_id=None)]
        monkeypatch.setattr(
            KVCacheLogParseWorker,
            "_aggregate_three_way",
            AsyncMock(return_value=(sd_events, agg_map, tw_events, {"t2"}, df)),
        )
        # master run() 不再单独调 _store_detail_*：明细帧迭代器经
        # store_result(detail_frames=...) 一并写入（store_result 已 mock）。
        monkeypatch.setattr(
            KVCacheLogParseWorker,
            "_store_bucket_stats_degraded",
            AsyncMock(return_value={}),
        )
        monkeypatch.setattr(
            KVCacheLogParseWorker,
            "store_result",
            AsyncMock(return_value=store_ok),
        )
        # master 失败路径改走 TaskPGManager.mark_failed_with_report（直连
        # PGManager.session 写失败报告），不再走 update_task({"status": ...})。
        mark_failed = AsyncMock()
        monkeypatch.setattr(
            kv_module.TaskPGManager, "mark_failed_with_report", mark_failed
        )
        report = AsyncMock()
        monkeypatch.setattr(BaseWorker, "report", report)
        update_task = AsyncMock()
        monkeypatch.setattr(kv_module.TaskPGManager, "update_task", update_task)
        return update_task, report, mark_failed

    def test_run_success_path(self, monkeypatch):
        update_task, report, mark_failed = self._wire_run(monkeypatch)
        assert _run(KVCacheLogParseWorker.run("task-1")) is True
        assert update_task.await_args_list[-1].args[1] == {
            "status": TaskStatusEnum.SUCCESSFUL_PENDING_REMOVE.value
        }
        mark_failed.assert_not_awaited()

    def test_run_empty_traces_marks_failed(self, monkeypatch):
        update_task, report, mark_failed = self._wire_run(
            monkeypatch, parse_result=SimpleNamespace(height=0)
        )
        assert _run(KVCacheLogParseWorker.run("task-1")) is False
        assert mark_failed.await_args.kwargs["status"] == (
            TaskStatusEnum.FAILED_PENDING_REMOVE
        )

    def test_run_cancelled_after_scan_stops(self, monkeypatch):
        running = _task()
        cancelled = _task(status=TaskStatusEnum.CANCELLED)
        get_task = AsyncMock(side_effect=[running, cancelled, cancelled, cancelled])
        update_task, report, mark_failed = self._wire_run(monkeypatch)
        monkeypatch.setattr(
            kv_module.TaskPGManager, "get_task_by_task_id", get_task
        )
        assert _run(KVCacheLogParseWorker.run("task-1")) is False
        # 取消路径直接返回，不写 FAILED 也不写 SUCCESS
        assert all(
            "status" not in c.args[1] or c.args[1]["status"] == TaskStatusEnum.RUNNING.value
            for c in update_task.await_args_list
        )
        mark_failed.assert_not_awaited()

    def test_run_parse_exception_marks_failed(self, monkeypatch):
        update_task, report, mark_failed = self._wire_run(
            monkeypatch, parse_exc=RuntimeError("scan died")
        )
        assert _run(KVCacheLogParseWorker.run("task-1")) is False
        assert mark_failed.await_args.kwargs["status"] == (
            TaskStatusEnum.FAILED_PENDING_REMOVE
        )

    def test_run_store_failure_marks_failed(self, monkeypatch):
        update_task, report, mark_failed = self._wire_run(
            monkeypatch, store_ok=False
        )
        assert _run(KVCacheLogParseWorker.run("task-1")) is False
        assert mark_failed.await_args.kwargs["status"] == (
            TaskStatusEnum.FAILED_PENDING_REMOVE
        )

    def test_run_task_missing_returns_false(self, monkeypatch):
        monkeypatch.setattr(
            kv_module.TaskPGManager,
            "get_task_by_task_id",
            AsyncMock(return_value=None),
        )
        assert _run(KVCacheLogParseWorker.run("task-404")) is False


class TestKVCacheLogParseWorkerStopDelete:
    def test_stop_pending_task_cancels(self, monkeypatch):
        task = _task(status=TaskStatusEnum.PENDING)
        monkeypatch.setattr(
            kv_module.TaskPGManager,
            "get_task_by_task_id",
            AsyncMock(return_value=task),
        )
        update_task = AsyncMock()
        monkeypatch.setattr(kv_module.TaskPGManager, "update_task", update_task)
        for mgr, meth in (
            (kv_module.LogParseResultPGManager,
             "update_log_parse_results_existed_status_by_log_id"),
            (kv_module.AnomalousEventPGManager,
             "update_anomalous_events_existed_status_by_log_id"),
            (kv_module.AnomalousEventChainPGManager,
             "update_event_chains_existed_status_by_log_id"),
            (kv_module.SrcDstAggregatedEventPGManager,
             "update_aggregated_events_existed_status_by_log_id"),
            (kv_module.TaskReportPGManager,
             "update_task_reports_existed_status_by_task_id"),
        ):
            monkeypatch.setattr(mgr, meth, AsyncMock())

        assert _run(KVCacheLogParseWorker.stop("task-1")) == "task-1"
        update_task.assert_awaited_once_with(
            "task-1", {"status": TaskStatusEnum.CANCELLED.value}
        )

    def test_stop_finished_task_returns_none(self, monkeypatch):
        task = _task(status=TaskStatusEnum.SUCCESSFUL_PENDING_REMOVE)
        monkeypatch.setattr(
            kv_module.TaskPGManager,
            "get_task_by_task_id",
            AsyncMock(return_value=task),
        )
        assert _run(KVCacheLogParseWorker.stop("task-1")) is None

    def test_stop_missing_task_returns_none(self, monkeypatch):
        monkeypatch.setattr(
            kv_module.TaskPGManager,
            "get_task_by_task_id",
            AsyncMock(return_value=None),
        )
        assert _run(KVCacheLogParseWorker.stop("task-404")) is None

    def test_delete_single_same_type_task_cleans_all(self, monkeypatch):
        task = _task()
        monkeypatch.setattr(
            kv_module.TaskPGManager,
            "get_task_by_task_id",
            AsyncMock(return_value=task),
        )
        monkeypatch.setattr(
            kv_module.TaskPGManager,
            "list_tasks_by_op_id",
            AsyncMock(return_value=[task]),
        )
        deletes = []
        for mgr, meth in (
            (kv_module.LogParseResultPGManager,
             "delete_log_parse_results_by_log_id"),
            (kv_module.AnomalousEventPGManager,
             "delete_anomalous_events_by_log_id"),
            (kv_module.AnomalousEventChainPGManager,
             "delete_event_chains_by_log_id"),
            (kv_module.SrcDstAggregatedEventPGManager,
             "delete_aggregated_events_by_log_id"),
            (kv_module.LogFailureEventPGManager,
             "delete_log_failure_events_by_log_id"),
            (kv_module.LogFailureEventPGManager,
             "delete_trace_failure_events_by_log_id"),
        ):
            mock = AsyncMock()
            monkeypatch.setattr(mgr, meth, mock)
            deletes.append(mock)

        assert _run(KVCacheLogParseWorker.delete("task-1")) == "task-1"
        for mock in deletes:
            mock.assert_awaited_once_with("log-1")

    def test_delete_shared_log_keeps_data(self, monkeypatch):
        task = _task()
        other = _task(task_id="task-2")
        monkeypatch.setattr(
            kv_module.TaskPGManager,
            "get_task_by_task_id",
            AsyncMock(return_value=task),
        )
        monkeypatch.setattr(
            kv_module.TaskPGManager,
            "list_tasks_by_op_id",
            AsyncMock(return_value=[task, other]),
        )
        delete_results = AsyncMock()
        monkeypatch.setattr(
            kv_module.LogParseResultPGManager,
            "delete_log_parse_results_by_log_id",
            delete_results,
        )
        assert _run(KVCacheLogParseWorker.delete("task-1")) == "task-1"
        delete_results.assert_not_awaited()

    def test_delete_missing_task_returns_empty(self, monkeypatch):
        monkeypatch.setattr(
            kv_module.TaskPGManager,
            "get_task_by_task_id",
            AsyncMock(return_value=None),
        )
        assert _run(KVCacheLogParseWorker.delete("task-404")) == ""


# ---------------------------------------------------------------------------
# Section B: StoreTraceContextLogsWorker
# ---------------------------------------------------------------------------

_RAW_9 = (
    "2026-01-01T00:00:00 | INFO | f.cpp | pod-1 | 12:34 | t1 | clusterA "
    "| message tail here"
)


class TestStoreTraceContextLogsGenerate:
    def test_missing_dir_returns_empty(self, tmp_path):
        ids, modes = _run(StoreTraceContextLogsWorker._generate_trace_id_set_diagnosis(
            str(tmp_path / "missing")
        ))
        assert ids == set()
        assert modes == {}

    def test_parses_failure_trace_log(self, tmp_path):
        out = tmp_path / "out"
        out.mkdir()
        raw_ok = "2026-01-01T00:00:00 | E | f | pod | 1:2 | t1 | cl | boom"
        raw_no_trace = "2026-01-01T00:00:00 | E | f | pod | 1:2 |  | cl | boom"
        (out / "failure_trace.log").write_text(
            "\n"
            "modeA, modeB |" + raw_ok + "\n"
            "modeA |only-one-field\n"
            "modeC |" + raw_no_trace + "\n",
            encoding="utf-8",
        )
        ids, modes = _run(StoreTraceContextLogsWorker._generate_trace_id_set_diagnosis(
            str(out)
        ))
        assert ids == {"t1"}
        assert modes[raw_ok] == ["modeA", "modeB"]
        # modeA 行只拆出 1 个 part，仍进 map（trace_id 列不足 6 段才不入 set）
        assert modes["only-one-field"] == ["modeA"]
        # modeC 行 trace_id 为空：进 map 但不进 trace_id_set
        assert modes[raw_no_trace] == ["modeC"]


class TestStoreTraceContextLogsStore:
    def _wire_common(self, monkeypatch, *, access_patterns=None):
        # master 默认走 polars CSV COPY 路径（add_log_failure_event_csv）；
        # 本组用例断言的是逐行 dict 契约，切回 WITTY_STORE_POLARS=0 的
        # legacy 路径（add_log_failure_event_raw），polars 路径另由
        # test_context_store_bounded.py 覆盖。
        monkeypatch.setenv("WITTY_STORE_POLARS", "0")
        monkeypatch.setattr(
            KVCacheLogEventDiagnosisWorker,
            "parse_filepath_config",
            AsyncMock(return_value={
                "ds_worker_access_log_file": access_patterns or [],
                "ds_client_access_log_file": [],
            }),
        )
        monkeypatch.setattr(
            KVCacheLogEventDiagnosisWorker,
            "parse_filepath_config",
            AsyncMock(return_value={
                "ds_worker_access_log_file": access_patterns or [],
                "ds_client_access_log_file": [],
            }),
        )
        monkeypatch.setattr(
            store_module.LogFilePGManager,
            "get_log_file_by_log_file_id",
            AsyncMock(return_value=None),
        )
        monkeypatch.setattr(
            store_module.FailureModeKnowledgePGManager,
            "get_all_failure_modes",
            AsyncMock(return_value={}),
        )

    def test_no_trace_ids_returns_early(self, monkeypatch, tmp_path):
        get_log_file = AsyncMock()
        monkeypatch.setattr(
            store_module.LogFilePGManager,
            "get_log_file_by_log_file_id",
            get_log_file,
        )
        _run(StoreTraceContextLogsWorker._store_trace_context_logs(
            str(tmp_path), "log-1", set(), {},
        ))
        get_log_file.assert_not_awaited()

    def test_runtime_log_full_flow(self, monkeypatch, tmp_path):
        self._wire_common(monkeypatch)
        out = tmp_path / "out"
        out.mkdir()
        raw_miss = "2026-01-01T00:00:00 | INFO | f.cpp | pod-2 | 1:2 | zz | cl | x"
        (out / "app.log").write_text(
            "\n"
            + _RAW_9 + "\n"
            + "short | line | only\n"
            + raw_miss + "\n",
            encoding="utf-8",
        )
        raw_batches = []
        trace_batches = []
        add_raw = AsyncMock(side_effect=lambda b: raw_batches.append(list(b)))
        add_trace = AsyncMock(side_effect=lambda b: trace_batches.append(list(b)))
        monkeypatch.setattr(
            store_module.LogFailureEventPGManager,
            "add_log_failure_event_raw",
            add_raw,
        )
        monkeypatch.setattr(
            store_module.LogFailureEventPGManager,
            "add_trace_failure_event_raw",
            add_trace,
        )
        report = AsyncMock()
        monkeypatch.setattr(BaseWorker, "report", report)

        _run(StoreTraceContextLogsWorker._store_trace_context_logs(
            str(out), "log-9", {"t1"}, {_RAW_9: ["modeA"]},
            task_id="task-1", progress_base=20.0, progress_end=45.0,
        ))

        assert add_raw.await_count == 1
        batch = raw_batches[0]
        assert len(batch) == 1
        event = batch[0]
        assert event["log_id"] == "log-9"
        assert event["log_file"] == "app.log"
        assert event["raw_text"] == _RAW_9
        assert event["trace_id"] == "t1"
        assert event["timestamp"] == "2026-01-01 00:00:00"
        assert event["pid"] == "12"
        assert event["tid"] == "34"
        assert event["pod_name"] == "pod-1"
        assert event["cluster_name"] == "clusterA"
        assert event["status_code"] == ""
        assert event["message"] == "message tail here"
        assert event["failure_mode"] == ["modeA"]

        assert add_trace.await_count == 1
        trace_events = trace_batches[0]
        assert len(trace_events) == 1
        trace_event = trace_events[0]
        assert trace_event["trace_id"] == "t1"
        assert trace_event["pod_names"] == ["pod-1"]
        assert trace_event["host_names"] == ["Unknown"]
        assert trace_event["cluster_names"] == ["clusterA"]
        assert trace_event["failure_mode"] == ["modeA"]
        assert trace_event["status_code"] == []
        assert "_access_failure_modes" not in trace_event
        assert any(c.args[2] == 45.0 for c in report.await_args_list)

    def test_access_log_status_code_and_skip(self, monkeypatch, tmp_path):
        self._wire_common(monkeypatch, access_patterns=["access*.log"])
        out = tmp_path / "out"
        out.mkdir()
        raw_ok = "2026-01-01T00:00:00 | E | f.c | pod | 1:2 | t1 | cl | 500 | oops"
        raw_short = "a | b | c | d | e | t1 | g"
        (out / "access.log").write_text(
            raw_ok + "\n" + raw_short + "\n", encoding="utf-8",
        )
        monkeypatch.setattr(
            store_module.FailureModeKnowledgePGManager,
            "get_all_failure_modes",
            AsyncMock(return_value={"modeA": _mode("modeA", error_code="K_X(500)")}),
        )
        raw_batches = []
        trace_batches = []
        add_raw = AsyncMock(side_effect=lambda b: raw_batches.append(list(b)))
        add_trace = AsyncMock(side_effect=lambda b: trace_batches.append(list(b)))
        monkeypatch.setattr(
            store_module.LogFailureEventPGManager,
            "add_log_failure_event_raw",
            add_raw,
        )
        monkeypatch.setattr(
            store_module.LogFailureEventPGManager,
            "add_trace_failure_event_raw",
            add_trace,
        )

        _run(StoreTraceContextLogsWorker._store_trace_context_logs(
            str(out), "log-9", {"t1"}, {raw_ok: ["modeA"]},
        ))

        batch = raw_batches[0]
        assert len(batch) == 1
        assert batch[0]["status_code"] == "500"
        assert batch[0]["message"] == "500 | oops"
        trace_events = trace_batches[0]
        assert trace_events[0]["status_code"] == ["500"]
        assert trace_events[0]["failure_mode"] == ["modeA"]

    def test_write_failure_wrapped_as_context_store_error(self, monkeypatch, tmp_path):
        self._wire_common(monkeypatch)
        out = tmp_path / "out"
        out.mkdir()
        (out / "app.log").write_text(_RAW_9 + "\n", encoding="utf-8")
        monkeypatch.setattr(
            store_module.LogFailureEventPGManager,
            "add_log_failure_event_raw",
            AsyncMock(side_effect=RuntimeError("db down")),
        )

        with pytest.raises(ContextStoreError):
            _run(StoreTraceContextLogsWorker._store_trace_context_logs(
                str(out), "log-9", {"t1"}, {},
            ))


class TestStoreTraceContextLogsLifecycle:
    def test_init_returns_none_without_log_file(self, monkeypatch):
        monkeypatch.setattr(
            store_module.LogFilePGManager,
            "get_log_file_by_log_file_id",
            AsyncMock(return_value=None),
        )
        assert _run(StoreTraceContextLogsWorker.init("log-1")) is None

    def test_init_creates_task(self, monkeypatch):
        monkeypatch.setattr(
            store_module.LogFilePGManager,
            "get_log_file_by_log_file_id",
            AsyncMock(return_value=SimpleNamespace(kb_id="kb-1", name="f")),
        )
        add_task = AsyncMock()
        monkeypatch.setattr(store_module.TaskPGManager, "add_task", add_task)
        monkeypatch.setattr(BaseWorker, "report", AsyncMock())
        task_id = _run(StoreTraceContextLogsWorker.init("log-1"))
        assert task_id == add_task.await_args.args[0].id

    def test_reinit_no_task_and_retry_exceeded_and_ok(self, monkeypatch):
        monkeypatch.setattr(
            store_module.TaskPGManager,
            "get_task_by_task_id",
            AsyncMock(return_value=None),
        )
        assert _run(StoreTraceContextLogsWorker.reinit("task-1")) is False

        report = AsyncMock()
        monkeypatch.setattr(
            store_module.TaskPGManager,
            "get_task_by_task_id",
            AsyncMock(return_value=_task(retry_times=4)),
        )
        monkeypatch.setattr(store_module, "Config", _fake_config(retry_times=3))
        monkeypatch.setattr(BaseWorker, "report", report)
        assert _run(StoreTraceContextLogsWorker.reinit("task-1")) is False
        report.assert_not_awaited()

        monkeypatch.setattr(
            store_module.TaskPGManager,
            "get_task_by_task_id",
            # master 语义：retry_times >= task_retry_times 即拒绝重试，
            # 允许重试需严格小于上限（此处 2 < 3）
            AsyncMock(return_value=_task(retry_times=2)),
        )
        assert _run(StoreTraceContextLogsWorker.reinit("task-1")) is True
        report.assert_awaited_once()

    def test_deinit_passthrough(self):
        assert _run(StoreTraceContextLogsWorker.deinit("task-1")) == "task-1"

    def test_wait_for_worker_success_states(self, monkeypatch):
        monkeypatch.setattr(store_module, "MONITOR_INTERVAL_SECONDS", 0)
        monkeypatch.setattr(BaseWorker, "report", AsyncMock())
        success_task = _task(status=TaskStatusEnum.SUCCESSFUL_PENDING_REMOVE)
        get_current = AsyncMock(
            side_effect=[None, success_task]
        )
        monkeypatch.setattr(
            store_module.TaskPGManager,
            "get_current_task_by_op_id",
            get_current,
        )
        assert _run(StoreTraceContextLogsWorker._wait_for_worker_success(
            "log-1", TaskTypeEnum.KV_CACHE_LOG_EVENT_DIAGNOSIS_WORKER,
            "diagnosis", "task-1", 20.0,
        )) is True

        failed_task = _task(status=TaskStatusEnum.FAILED_PENDING_REMOVE)
        monkeypatch.setattr(
            store_module.TaskPGManager,
            "get_current_task_by_op_id",
            AsyncMock(return_value=failed_task),
        )
        assert _run(StoreTraceContextLogsWorker._wait_for_worker_success(
            "log-1", TaskTypeEnum.KV_CACHE_LOG_EVENT_DIAGNOSIS_WORKER,
            "diagnosis", "task-1", 20.0,
        )) is False


class TestStoreTraceContextLogsRun:
    def _wire_run(self, monkeypatch, tmp_path, *, diagnosis_done=True,
                  parse_done=True, tasks=None, log_file="default"):
        task = _task(task_id="task-1", op_id="log-op",
                     task_type=TaskTypeEnum.STORE_TRACE_CONTEXT_LOGS_WORKER)
        get_task = AsyncMock(return_value=task)
        if tasks is not None:
            get_task = AsyncMock(side_effect=tasks)
        monkeypatch.setattr(
            store_module.TaskPGManager, "get_task_by_task_id", get_task
        )
        update_task = AsyncMock()
        monkeypatch.setattr(store_module.TaskPGManager, "update_task", update_task)
        if log_file == "default":
            log_file = SimpleNamespace(id="abcdefgh", kb_id="kb-1")
        monkeypatch.setattr(
            store_module.LogFilePGManager,
            "get_log_file_by_log_file_id",
            AsyncMock(return_value=log_file),
        )
        monkeypatch.setattr(store_module, "witty_dir", str(tmp_path))
        out_dir = tmp_path / "log_abcdefgh"
        out_dir.mkdir()
        (out_dir / "failure_trace.log").write_text("m | x\n", encoding="utf-8")
        wait = AsyncMock(side_effect=[diagnosis_done, parse_done])
        monkeypatch.setattr(
            StoreTraceContextLogsWorker, "_wait_for_worker_success", wait
        )
        generate = AsyncMock(return_value=({"t1"}, {"raw": ["modeA"]}))
        monkeypatch.setattr(
            StoreTraceContextLogsWorker,
            "_generate_trace_id_set_diagnosis",
            generate,
        )
        store_logs = AsyncMock()
        monkeypatch.setattr(
            StoreTraceContextLogsWorker, "_store_trace_context_logs", store_logs
        )
        monkeypatch.setattr(
            store_module.LogParseResultPGManager,
            "list_anomalous_trace_ids_by_log_id",
            AsyncMock(return_value={"t9"}),
        )
        update_log_file = AsyncMock()
        monkeypatch.setattr(
            store_module.LogFilePGManager, "update_log_file", update_log_file
        )
        monkeypatch.setattr(
            store_module.LogKnowledgePGManager,
            "refresh_kb_counters",
            AsyncMock(),
        )
        # master 失败路径改走 TaskPGManager.mark_failed_with_report（直连
        # PGManager.session 写失败报告），不再走 update_task({"status": ...})。
        mark_failed = AsyncMock()
        monkeypatch.setattr(
            store_module.TaskPGManager, "mark_failed_with_report", mark_failed
        )
        monkeypatch.setattr(BaseWorker, "report", AsyncMock())
        return update_task, store_logs, update_log_file, mark_failed

    def test_run_success_path(self, monkeypatch, tmp_path):
        update_task, store_logs, update_log_file, mark_failed = self._wire_run(
            monkeypatch, tmp_path
        )
        assert _run(StoreTraceContextLogsWorker.run("task-1")) is True
        assert store_logs.await_count == 2
        second = store_logs.await_args_list[1]
        # 第二次落库：异常 trace 集合已剔除诊断 trace，无 failure 映射
        assert second.kwargs["trace_id_set"] == {"t9"}
        assert second.kwargs["trace_failure_id"] is None
        assert update_log_file.await_args.args[1] == {
            "failure_count": 1, "trace_failure_event_cnt": 1,
        }
        assert update_task.await_args_list[-1].args[1] == {
            "status": TaskStatusEnum.SUCCESSFUL_PENDING_REMOVE.value
        }
        mark_failed.assert_not_awaited()

    def test_run_diagnosis_dependency_failed(self, monkeypatch, tmp_path):
        update_task, _, _, mark_failed = self._wire_run(
            monkeypatch, tmp_path, diagnosis_done=False
        )
        assert _run(StoreTraceContextLogsWorker.run("task-1")) is False
        assert mark_failed.await_args.kwargs["status"] == (
            TaskStatusEnum.FAILED_PENDING_REMOVE
        )

    def test_run_parse_dependency_failed(self, monkeypatch, tmp_path):
        update_task, store_logs, _, mark_failed = self._wire_run(
            monkeypatch, tmp_path, parse_done=False
        )
        assert _run(StoreTraceContextLogsWorker.run("task-1")) is False
        assert store_logs.await_count == 1
        assert mark_failed.await_args.kwargs["status"] == (
            TaskStatusEnum.FAILED_PENDING_REMOVE
        )

    def test_run_cancelled_between_stages(self, monkeypatch, tmp_path):
        task = _task(task_id="task-1", op_id="log-op",
                     task_type=TaskTypeEnum.STORE_TRACE_CONTEXT_LOGS_WORKER)
        cancelled = _task(
            task_id="task-1", status=TaskStatusEnum.CANCELLED,
            task_type=TaskTypeEnum.STORE_TRACE_CONTEXT_LOGS_WORKER,
        )
        update_task, store_logs, _, _ = self._wire_run(
            monkeypatch, tmp_path, tasks=[task, cancelled]
        )
        assert _run(StoreTraceContextLogsWorker.run("task-1")) is False
        store_logs.assert_not_awaited()

    def test_run_log_file_missing(self, monkeypatch, tmp_path):
        update_task, store_logs, _, mark_failed = self._wire_run(
            monkeypatch, tmp_path, log_file=None
        )
        assert _run(StoreTraceContextLogsWorker.run("task-1")) is False
        store_logs.assert_not_awaited()
        assert mark_failed.await_args.kwargs["status"] == (
            TaskStatusEnum.FAILED_PENDING_REMOVE
        )

    def test_run_task_missing(self, monkeypatch):
        monkeypatch.setattr(
            store_module.TaskPGManager,
            "get_task_by_task_id",
            AsyncMock(return_value=None),
        )
        assert _run(StoreTraceContextLogsWorker.run("task-404")) is False

    def test_stop_and_delete(self, monkeypatch):
        pending = _task(status=TaskStatusEnum.PENDING)
        monkeypatch.setattr(
            store_module.TaskPGManager,
            "get_task_by_task_id",
            AsyncMock(return_value=pending),
        )
        update_task = AsyncMock()
        monkeypatch.setattr(store_module.TaskPGManager, "update_task", update_task)
        assert _run(StoreTraceContextLogsWorker.stop("task-1")) == "task-1"
        update_task.assert_awaited_once_with(
            "task-1", {"status": TaskStatusEnum.CANCELLED.value}
        )

        monkeypatch.setattr(
            store_module.TaskPGManager,
            "get_task_by_task_id",
            AsyncMock(return_value=_task(status=TaskStatusEnum.SUCCESSFUL)),
        )
        assert _run(StoreTraceContextLogsWorker.stop("task-1")) is None

        assert _run(StoreTraceContextLogsWorker.delete("task-1")) == "task-1"


class TestCleanupTempDirs:
    def test_removes_output_and_preprocess(self, monkeypatch, tmp_path):
        out = tmp_path / "diag_out"
        out.mkdir()
        (out / "f.log").write_text("x", encoding="utf-8")
        cleaned = Mock()
        monkeypatch.setattr(store_module, "cleanup_preprocess_dir", cleaned)

        cleanup_temp_dirs(str(out), "log-op")

        assert not out.exists()
        cleaned.assert_called_once_with("log-op")

    def test_missing_output_and_rmtree_failure(self, monkeypatch, tmp_path):
        cleaned = Mock()
        monkeypatch.setattr(store_module, "cleanup_preprocess_dir", cleaned)
        cleanup_temp_dirs("", "log-op")
        cleanup_temp_dirs(str(tmp_path / "missing"), "")
        cleaned.assert_called_once_with("log-op")

        out = tmp_path / "out"
        out.mkdir()
        monkeypatch.setattr(
            store_module.shutil, "rmtree",
            Mock(side_effect=OSError("permission")),
        )
        cleanup_temp_dirs(str(out), "")
        assert out.exists()


# ---------------------------------------------------------------------------
# Section C: KVCacheLogEventDiagnosisWorker
# ---------------------------------------------------------------------------


class _FakeSession:
    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return False

    async def execute(self, *args, **kwargs):
        pass


class _FakePGManager:
    @staticmethod
    def session():
        return _FakeSession()


class TestEventDiagnosisPureLogic:
    def test_remove_duplicates_keeps_order(self):
        assert _run(KVCacheLogEventDiagnosisWorker.remove_duplicates(
            ["a", "b", "a", "c"]
        )) == ["a", "b", "c"]

    def test_matches_any(self):
        assert KVCacheLogEventDiagnosisWorker._matches_any(
            "access_1.log", ["access*.log"]
        )
        assert not KVCacheLogEventDiagnosisWorker._matches_any(
            "info.log", ["access*.log"], 
        )
        assert not KVCacheLogEventDiagnosisWorker._matches_any(
            "info.log", [],
        )

    def test_extract_src_dst_ip_patterns(self):
        extract = KVCacheLogEventDiagnosisWorker._extract_src_dst_ip
        assert extract("src=1.2.3.4 dst=5.6.7.8") == ("1.2.3.4", "5.6.7.8")
        assert extract("src address:1.2.3.4 target address:5.6.7.8") == ("1.2.3.4", "5.6.7.8")
        assert extract("srcAddress = 1.2.3.4 targetAddress = 5.6.7.8") == ("1.2.3.4", "5.6.7.8")
        assert extract("no ip here") == ("", "")
        assert extract("src=1.2.3.4 only") == ("", "")

    def test_extract_operation(self):
        extract = KVCacheLogEventDiagnosisWorker._extract_operation
        assert extract("a|b|c|d|e|f|g|h|DS_KV_CLIENT_GET") == "GET"
        assert extract("a|b|c|d|e|f|g|h|DS_POSIX_CREATE") == "SET"
        assert extract("a|b|c|d|e|f|g|h|UNKNOWN_OP") == ""
        assert extract("a|b|c") == ""

    def test_normalize_failure_mode_error_code(self):
        normalize = KVCacheLogEventDiagnosisWorker._normalize_failure_mode_error_code
        assert normalize(None) == ""
        assert normalize("K_OK(0)") == "0"
        assert normalize("K_OK(+00)") == "0"
        assert normalize("K_NAME(1004)") == "1004"
        assert normalize("1004") == ""
        assert normalize("NULL") == ""
        assert normalize("N/A") == ""
        assert normalize("-") == ""
        assert normalize("K_NAME(0)") == ""
        assert normalize("K_NAME(1004) extra") == "K_NAME(1004) extra"
        assert normalize(1004) == ""

    def test_failure_mode_error_codes(self):
        cache = {
            "a": _mode("a", error_code="K_X(500)"),
            "b": _mode("b", error_code=None),
            "c": _mode("c", error_code="K_X(500)"),
        }
        codes = KVCacheLogEventDiagnosisWorker._failure_mode_error_codes(
            ["a", "b", "c", "missing"], cache
        )
        assert codes == ["500"]

    def test_is_child_failure_mode_bfs_and_cycle(self):
        cache = {
            "a": _mode("a", children="b,c"),
            "b": _mode("b", children="a"),  # 环
            "c": _mode("c"),
        }
        assert KVCacheLogEventDiagnosisWorker._is_child_failure_mode("a", "c", cache)
        assert KVCacheLogEventDiagnosisWorker._is_child_failure_mode("a", "b", cache)
        assert not KVCacheLogEventDiagnosisWorker._is_child_failure_mode("a", "d", cache)
        assert not KVCacheLogEventDiagnosisWorker._is_child_failure_mode("", "a", cache)
        assert not KVCacheLogEventDiagnosisWorker._is_child_failure_mode("a", "", cache)

    def test_leaf_failure_modes_keeps_deepest(self):
        cache = {
            "parent": _mode("parent", children="child"),
            "child": _mode("child"),
        }
        leaf = KVCacheLogEventDiagnosisWorker._leaf_failure_modes(
            ["parent", "child", "", "child"], cache
        )
        assert leaf == ["child"]
        # 无父子关系时保序去重
        assert KVCacheLogEventDiagnosisWorker._leaf_failure_modes(
            ["x", "y", "x"], {}
        ) == ["x", "y"]

    def test_merge_trace_failure_event_new_access(self):
        cache = {
            "parent": _mode("parent", children="child", error_code="K_P(1004)"),
            "child": _mode("child", error_code="K_C(200)"),
        }
        raw = "2026-01-02 | E | f | pod-1 | 1:2 | t1 | cl | msg src=1.2.3.4 dst=5.6.7.8"
        event = {
            "trace_id": "t1", "log_id": "log-1", "raw_text": raw,
            "pod_name": "pod-1", "host_name": "h-1", "cluster_name": "c-1",
            "timestamp": "2026-01-02 00:00:00", "status_code": "0",
            "failure_mode": ["parent", "child"],
        }
        mapping: dict = {}
        KVCacheLogEventDiagnosisWorker._merge_trace_failure_event(mapping, event, cache)
        merged = mapping["t1"]
        assert merged["src_ip"] == "1.2.3.4"
        assert merged["dst_ip"] == "5.6.7.8"
        assert merged["pod_names"] == ["pod-1"]
        assert merged["failure_mode"] == ["child"]  # 父子同现留子
        assert merged["_access_failure_modes"] == ["child"]
        assert merged["status_code"] == ["200"]
        assert merged["operation"] == ""

    def test_merge_trace_failure_event_updates_existing(self):
        cache = {
            "parent": _mode("parent", children="child", error_code="K_P(1004)"),
            "child": _mode("child", error_code="K_C(200)"),
        }
        first = {
            "trace_id": "t1", "log_id": "log-1",
            "raw_text": "a|b|c|d|e|f|g|h|DS_KV_CLIENT_GET",
            "pod_name": "pod-1", "host_name": "h-1", "cluster_name": "c-1",
            "timestamp": "2026-01-02 00:00:00", "status_code": "",
            "failure_mode": ["child"],
        }
        second = {
            "trace_id": "t1", "log_id": "log-1",
            "raw_text": "a|b|c|d|e|f|g|h|DS_POSIX_CREATE src=9.9.9.9 dst=8.8.8.8",
            "pod_name": "pod-2", "host_name": "h-1", "cluster_name": "c-2",
            "timestamp": "2026-01-01 00:00:00", "status_code": "500",
            "failure_mode": ["parent"],
        }
        mapping: dict = {}
        KVCacheLogEventDiagnosisWorker._merge_trace_failure_event(mapping, first, cache)
        KVCacheLogEventDiagnosisWorker._merge_trace_failure_event(mapping, second, cache)
        merged = mapping["t1"]
        assert merged["pod_names"] == ["pod-1", "pod-2"]
        assert merged["host_names"] == ["h-1"]
        assert merged["cluster_names"] == ["c-1", "c-2"]
        assert merged["timestamp"] == "2026-01-01 00:00:00"
        assert merged["src_ip"] == "9.9.9.9"
        assert merged["dst_ip"] == "8.8.8.8"
        assert merged["operation"] == "GET"  # 首次已解析出 GET，后续不覆盖
        assert merged["failure_mode"] == ["child"]
        # 第二行是 access 命中 parent → 聚合故障码取 parent 的 1004
        assert merged["status_code"] == ["1004"]

    def test_count_log_failure_events(self, tmp_path):
        runtime = tmp_path / "app.log"
        runtime.write_text(
            "2026-01-01 | E | f | pod | 1:2 | t1 | cl | msg\n"
            "short | line\n",
            encoding="utf-8",
        )
        access = tmp_path / "access.log"
        access.write_text(
            "2026-01-01 | E | f | pod | 1:2 | t1 | cl | 500 | msg\n"
            "2026-01-01 | E | f | pod | 1:2 | t1 | cl\n"
            "2026-01-01 | E | f | pod | 1:2 | zz | cl | 500 | msg\n",
            encoding="utf-8",
        )
        total = KVCacheLogEventDiagnosisWorker._count_log_failure_events(
            [
                ("app.log", str(runtime)),
                ("access.log", str(access)),
                ("gone.log", str(tmp_path / "gone.log")),
            ],
            {"t1"},
            ["access*.log"],
            [],
        )
        assert total == 2


class TestEventDiagnosisLifecycle:
    def test_init_returns_none_without_log_file(self, monkeypatch):
        monkeypatch.setattr(
            event_module.LogFilePGManager,
            "get_log_file_by_log_file_id",
            AsyncMock(return_value=None),
        )
        assert _run(KVCacheLogEventDiagnosisWorker.init("log-1")) is None

    def test_init_creates_task(self, monkeypatch):
        monkeypatch.setattr(
            event_module.LogFilePGManager,
            "get_log_file_by_log_file_id",
            AsyncMock(return_value=SimpleNamespace(
                kb_id="kb-1", file_path="/logs",
            )),
        )
        add_task = AsyncMock()
        monkeypatch.setattr(event_module.TaskPGManager, "add_task", add_task)
        monkeypatch.setattr(BaseWorker, "report", AsyncMock())
        task_id = _run(KVCacheLogEventDiagnosisWorker.init("log-1"))
        assert task_id == add_task.await_args.args[0].id

    def test_reinit_no_task_at_limit_and_ok(self, monkeypatch):
        monkeypatch.setattr(
            event_module.TaskPGManager,
            "get_task_by_task_id",
            AsyncMock(return_value=None),
        )
        assert _run(KVCacheLogEventDiagnosisWorker.reinit("task-1")) is False

        report = AsyncMock()
        monkeypatch.setattr(event_module, "Config", _fake_config(retry_times=3))
        monkeypatch.setattr(BaseWorker, "report", report)
        monkeypatch.setattr(
            event_module.TaskPGManager,
            "get_task_by_task_id",
            AsyncMock(return_value=_task(retry_times=3)),
        )
        assert _run(KVCacheLogEventDiagnosisWorker.reinit("task-1")) is False
        report.assert_not_awaited()

        monkeypatch.setattr(
            event_module.TaskPGManager,
            "get_task_by_task_id",
            AsyncMock(return_value=_task(retry_times=2)),
        )
        assert _run(KVCacheLogEventDiagnosisWorker.reinit("task-1")) is True
        report.assert_awaited_once()

    def test_parse_filepath_config_branches(self, monkeypatch):
        # KB 配置分支
        monkeypatch.setattr(
            event_module.DiagnosisConfigPGManager,
            "get_or_create",
            AsyncMock(return_value=SimpleNamespace(
                log_filename_pattern=SimpleNamespace(
                    model_dump=lambda: {"ds_worker_access_log_file": ["kb-pat"]}
                )
            )),
        )
        args = _run(KVCacheLogEventDiagnosisWorker.parse_filepath_config("kb-1"))
        assert args == {"ds_worker_access_log_file": ["kb-pat"]}

        # 异常时内置默认
        monkeypatch.setattr(
            event_module.DiagnosisConfigPGManager,
            "get_or_create",
            AsyncMock(side_effect=RuntimeError("pg down")),
        )
        default = _run(KVCacheLogEventDiagnosisWorker.parse_filepath_config("kb-1"))
        assert "ds_worker_access_log_file" in default
        assert default["ds_worker_access_log_file"] == ["access*.log", "*_access.log", "*_split_access.log"]

        # 无 kb_id 走全局 Config
        global_args = _run(KVCacheLogEventDiagnosisWorker.parse_filepath_config(None))
        assert isinstance(global_args, dict)
        assert "ds_worker_access_log_file" in global_args

    def test_run_diagnosis_tool_success(self, monkeypatch):
        monkeypatch.setattr(
            KVCacheLogEventDiagnosisWorker,
            "parse_filepath_config",
            AsyncMock(return_value={
                "ds_worker_access_log_file": ["access*.log"],
                "ds_client_info_log_file": [],
                "brpc_log_file_patterns": ["brpc-pat"],
            }),
        )
        monkeypatch.setattr(event_module, "Config", _fake_config())
        run_mock = Mock(return_value=SimpleNamespace(
            returncode=0, stdout="ok", stderr="",
        ))
        monkeypatch.setattr(event_module.subprocess, "run", run_mock)
        monkeypatch.setattr(BaseWorker, "report", AsyncMock())

        task = _task()
        assert _run(KVCacheLogEventDiagnosisWorker.run_diagnosis_tool(
            "/logs", task, "rand123", kb_id="kb-1",
        )) is True
        cmd = run_mock.call_args.args[0]
        assert cmd[1:7] == [
            "--ds-log-path", "/logs",
            "--start-time", "2020-01-01 00:00:00",
            "--end-time", "2099-12-31 23:59:59",
        ]
        assert "--ds-worker-access-log-file" in cmd
        assert cmd[cmd.index("--ds-worker-access-log-file") + 1] == "access*.log"
        assert "--random-str" in cmd
        # brpc_log_file_patterns 不透传
        assert "brpc-pat" not in cmd

    def test_run_diagnosis_tool_failures(self, monkeypatch):
        monkeypatch.setattr(
            KVCacheLogEventDiagnosisWorker,
            "parse_filepath_config",
            AsyncMock(return_value={"ds_worker_access_log_file": []}),
        )
        # master 失败路径改走 TaskPGManager.mark_failed_with_report（直连
        # PGManager.session 写失败报告），不再走 update_task({"status": ...})。
        mark_failed = AsyncMock()
        monkeypatch.setattr(
            event_module.TaskPGManager, "mark_failed_with_report", mark_failed
        )
        monkeypatch.setattr(BaseWorker, "report", AsyncMock())
        task = _task()

        # 非零返回码
        monkeypatch.setattr(event_module.subprocess, "run", Mock(
            return_value=SimpleNamespace(returncode=1, stdout="", stderr="boom")
        ))
        assert _run(KVCacheLogEventDiagnosisWorker.run_diagnosis_tool(
            "/logs", task, "rand"
        )) is False

        # 输出包含 [ERROR]
        monkeypatch.setattr(event_module.subprocess, "run", Mock(
            return_value=SimpleNamespace(
                returncode=0, stdout="[ERROR] bad\nok", stderr="",
            )
        ))
        assert _run(KVCacheLogEventDiagnosisWorker.run_diagnosis_tool(
            "/logs", task, "rand"
        )) is False

        # 超时与通用异常
        monkeypatch.setattr(event_module.subprocess, "run", Mock(
            side_effect=[
                subprocess.TimeoutExpired(cmd="x", timeout=1),
                RuntimeError("spawn failed"),
            ]
        ))
        assert _run(KVCacheLogEventDiagnosisWorker.run_diagnosis_tool(
            "/logs", task, "rand"
        )) is False
        assert _run(KVCacheLogEventDiagnosisWorker.run_diagnosis_tool(
            "/logs", task, "rand"
        )) is False
        assert mark_failed.await_count == 4
        assert all(
            c.kwargs["status"] == TaskStatusEnum.FAILED_PENDING_REMOVE
            for c in mark_failed.await_args_list
        )

    def test_stop_returns_none_and_delete_passthrough(self, monkeypatch):
        monkeypatch.setattr(
            event_module.TaskPGManager,
            "get_task_by_task_id",
            AsyncMock(return_value=SimpleNamespace()),
        )
        assert _run(KVCacheLogEventDiagnosisWorker.stop("task-1")) is None
        assert _run(KVCacheLogEventDiagnosisWorker.delete("task-1")) == "task-1"


class TestEventDiagnosisRun:
    def _wire_run(self, monkeypatch, tmp_path, *, tool_ok=True, tasks=None,
                  log_file="default"):
        task = _task(task_id="task-1", op_id="log-1",
                     task_type=TaskTypeEnum.KV_CACHE_LOG_EVENT_DIAGNOSIS_WORKER)
        get_task = AsyncMock(return_value=task)
        if tasks is not None:
            get_task = AsyncMock(side_effect=tasks)
        monkeypatch.setattr(
            event_module.TaskPGManager, "get_task_by_task_id", get_task
        )
        monkeypatch.setattr(
            event_module.TaskPGManager, "update_task", AsyncMock()
        )
        if log_file == "default":
            log_file = SimpleNamespace(
                id="abcdefgh", kb_id="kb-1", file_path=str(tmp_path),
            )
        monkeypatch.setattr(
            event_module.LogFilePGManager,
            "get_log_file_by_log_file_id",
            AsyncMock(return_value=log_file),
        )
        tool = AsyncMock(return_value=tool_ok)
        monkeypatch.setattr(
            KVCacheLogEventDiagnosisWorker, "run_diagnosis_tool", tool
        )
        monkeypatch.setattr(event_module, "witty_dir", str(tmp_path))
        out_dir = tmp_path / "log_abcdefgh"
        out_dir.mkdir()
        (out_dir / "failure_trace.log").write_text("m | x\n", encoding="utf-8")
        monkeypatch.setattr(
            "latency.database.engine.PGManager", _FakePGManager
        )
        report = AsyncMock()
        monkeypatch.setattr(BaseWorker, "report", report)
        update_task = AsyncMock()
        monkeypatch.setattr(
            event_module.TaskPGManager, "update_task", update_task
        )
        # master 失败路径改走 TaskPGManager.mark_failed_with_report（直连
        # PGManager.session 写失败报告），不再走 update_task({"status": ...})。
        mark_failed = AsyncMock()
        monkeypatch.setattr(
            event_module.TaskPGManager, "mark_failed_with_report", mark_failed
        )
        monkeypatch.setattr(asyncio, "sleep", AsyncMock())
        return update_task, report, mark_failed

    def test_run_success_path_with_kb_update(self, monkeypatch, tmp_path):
        update_task, report, mark_failed = self._wire_run(monkeypatch, tmp_path)
        assert _run(KVCacheLogEventDiagnosisWorker.run("task-1")) is True
        assert update_task.await_args_list[-1].args[1] == {
            "status": TaskStatusEnum.SUCCESSFUL_PENDING_REMOVE.value
        }
        assert any(c.args[2] == 100.0 for c in report.await_args_list)

    def test_run_retries_get_task_after_pg_glitch(self, monkeypatch, tmp_path):
        task = _task(task_id="task-1", op_id="log-1",
                     task_type=TaskTypeEnum.KV_CACHE_LOG_EVENT_DIAGNOSIS_WORKER)
        update_task, _, _ = self._wire_run(
            monkeypatch, tmp_path, tasks=[RuntimeError("pg glitch"), task, task]
        )
        assert _run(KVCacheLogEventDiagnosisWorker.run("task-1")) is True
        assert update_task.await_args_list[-1].args[1] == {
            "status": TaskStatusEnum.SUCCESSFUL_PENDING_REMOVE.value
        }

    def test_run_get_task_retry_exhausted(self, monkeypatch, tmp_path):
        update_task, _, _ = self._wire_run(
            monkeypatch, tmp_path, tasks=[RuntimeError("pg down")] * 6
        )
        assert _run(KVCacheLogEventDiagnosisWorker.run("task-1")) is False
        update_task.assert_not_awaited()

    def test_run_tool_failed_returns_false(self, monkeypatch, tmp_path):
        update_task, _, _ = self._wire_run(monkeypatch, tmp_path, tool_ok=False)
        assert _run(KVCacheLogEventDiagnosisWorker.run("task-1")) is False

    def test_run_output_dir_missing(self, monkeypatch, tmp_path):
        update_task, report, mark_failed = self._wire_run(monkeypatch, tmp_path)
        import shutil as _shutil
        _shutil.rmtree(tmp_path / "log_abcdefgh")
        assert _run(KVCacheLogEventDiagnosisWorker.run("task-1")) is False
        assert mark_failed.await_args.kwargs["status"] == (
            TaskStatusEnum.FAILED_PENDING_REMOVE
        )

    def test_run_cancelled_after_tool(self, monkeypatch, tmp_path):
        task = _task(task_id="task-1", op_id="log-1",
                     task_type=TaskTypeEnum.KV_CACHE_LOG_EVENT_DIAGNOSIS_WORKER)
        cancelled = _task(
            task_id="task-1", status=TaskStatusEnum.CANCELLED,
            task_type=TaskTypeEnum.KV_CACHE_LOG_EVENT_DIAGNOSIS_WORKER,
        )
        update_task, _, _ = self._wire_run(
            monkeypatch, tmp_path, tasks=[task, cancelled]
        )
        assert _run(KVCacheLogEventDiagnosisWorker.run("task-1")) is False
        assert all(
            c.args[1] != {"status": TaskStatusEnum.SUCCESSFUL_PENDING_REMOVE.value}
            for c in update_task.await_args_list
        )

    def test_run_log_file_missing(self, monkeypatch, tmp_path):
        update_task, _, mark_failed = self._wire_run(
            monkeypatch, tmp_path, log_file=None
        )
        assert _run(KVCacheLogEventDiagnosisWorker.run("task-1")) is False
        assert mark_failed.await_args.kwargs["status"] == (
            TaskStatusEnum.FAILED_PENDING_REMOVE
        )


# ---------------------------------------------------------------------------
# Section D: BrpcLogDiagnosisWorker
# ---------------------------------------------------------------------------


class TestBrpcDiagnosisValidation:
    def test_validate_start_time(self):
        assert (
            BrpcLogDiagnosisWorker._validate_start_time("2026-01-01 00:00:00")
            == "2026-01-01 00:00:00"
        )
        with pytest.raises(BrpcDiagnosisWorkerError):
            BrpcLogDiagnosisWorker._validate_start_time("2026-1-1 00:00:00")
        with pytest.raises(BrpcDiagnosisWorkerError):
            BrpcLogDiagnosisWorker._validate_start_time("bad")
        with pytest.raises(BrpcDiagnosisWorkerError):
            BrpcLogDiagnosisWorker._validate_start_time(None)

    def test_timeout_seconds(self, monkeypatch):
        monkeypatch.delenv("BRPC_DIAG_TIMEOUT_SECONDS", raising=False)
        assert BrpcLogDiagnosisWorker._timeout_seconds() == 3600.0
        monkeypatch.setenv("BRPC_DIAG_TIMEOUT_SECONDS", "60")
        assert BrpcLogDiagnosisWorker._timeout_seconds() == 60.0
        monkeypatch.setenv("BRPC_DIAG_TIMEOUT_SECONDS", "abc")
        with pytest.raises(BrpcDiagnosisWorkerError):
            BrpcLogDiagnosisWorker._timeout_seconds()
        monkeypatch.setenv("BRPC_DIAG_TIMEOUT_SECONDS", "0")
        with pytest.raises(BrpcDiagnosisWorkerError):
            BrpcLogDiagnosisWorker._timeout_seconds()

    def test_pid_path_rejects_invalid_task_id(self):
        with pytest.raises(BrpcDiagnosisWorkerError):
            BrpcLogDiagnosisWorker._pid_path("bad task!")
        assert BrpcLogDiagnosisWorker._pid_path("task_Ok-01").name == ".worker_task_Ok-01.pid"

    def test_resolve_start_time_branches(self, monkeypatch):
        monkeypatch.setattr(
            "latency.task.task_handler.TaskHandler.get_task_config",
            staticmethod(lambda task_id: None),
        )
        assert BrpcLogDiagnosisWorker._resolve_start_time("task-1") is None

        monkeypatch.setattr(
            "latency.task.task_handler.TaskHandler.get_task_config",
            staticmethod(lambda task_id: SimpleNamespace(
                start_time=None, end_time="2099-12-31 23:59:59",
            )),
        )
        assert BrpcLogDiagnosisWorker._resolve_start_time("task-1") is None

        monkeypatch.setattr(
            "latency.task.task_handler.TaskHandler.get_task_config",
            staticmethod(lambda task_id: SimpleNamespace(
                start_time="2026-01-01 00:00:00", end_time="2099-12-31 23:59:59",
            )),
        )
        assert (
            BrpcLogDiagnosisWorker._resolve_start_time("task-1")
            == "2026-01-01 00:00:00"
        )


class _FastClock:
    """跳过 _terminate_pid 的 5 秒死亡轮询。"""

    def __init__(self):
        self._t = 100.0

    def monotonic(self):
        self._t += 2.0
        return self._t

    def sleep(self, seconds):
        # 死亡轮询必须真实等待（SIGTERM 生效需要时间），仅 monotonic 快进跳过 5s 循环。
        time.sleep(seconds)


def _spawn_diag_tool(task_id="task-77", with_task_arg=True):
    """模拟真实 witty-ub-brpc-diag 二进制：exec -a 让 /proc/cmdline 的
    argv[0] basename 即工具名（脚本 + shebang 的 argv[0] 是解释器）。"""
    script = 'exec -a witty-ub-brpc-diag python3 -c "import time; time.sleep(30)"'
    if with_task_arg:
        script += f" --task-id {task_id}"
    return subprocess.Popen(
        ["bash", "-c", script],
        start_new_session=True,
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )


def _wait_for_exec(proc, task_id):
    """bash 需要时间 exec 成目标进程，轮询直到 cmdline 就绪。"""
    for _ in range(60):
        if BrpcLogDiagnosisWorker._pid_matches_task(proc.pid, task_id):
            return True
        time.sleep(0.05)
    return False


class TestBrpcDiagnosisProcessManagement:
    def test_pid_matches_task(self):
        proc = _spawn_diag_tool()
        try:
            assert _wait_for_exec(proc, "task-77")
            assert not BrpcLogDiagnosisWorker._pid_matches_task(proc.pid, "other")
            assert not BrpcLogDiagnosisWorker._pid_matches_task(99999999, "task-77")
        finally:
            proc.terminate()
            proc.wait()
        # 进程退出后 /proc 条目消失
        assert not BrpcLogDiagnosisWorker._pid_matches_task(proc.pid, "task-77")

    def test_pid_matches_task_requires_task_arg(self):
        proc = _spawn_diag_tool(with_task_arg=False)
        try:
            time.sleep(0.3)
            assert not BrpcLogDiagnosisWorker._pid_matches_task(proc.pid, "task-77")
        finally:
            proc.terminate()
            proc.wait()

    def test_register_and_unregister_process(self, monkeypatch, tmp_path):
        monkeypatch.setenv("WITTY_DIR", str(tmp_path))
        BrpcLogDiagnosisWorker._processes.clear()
        process = SimpleNamespace(pid=4242)
        BrpcLogDiagnosisWorker._register_process("task-1", process)
        # master 的 pid 目录已从 brpc-diag 改为 brpc-tmp（_output_dir）
        pid_path = tmp_path / "brpc-tmp" / ".worker_task-1.pid"
        assert pid_path.read_text(encoding="ascii") == "4242"
        assert BrpcLogDiagnosisWorker._processes["task-1"] is process

        # pid 不匹配不清理
        BrpcLogDiagnosisWorker._unregister_process("task-1", pid=999)
        assert pid_path.exists()
        assert "task-1" in BrpcLogDiagnosisWorker._processes

        BrpcLogDiagnosisWorker._unregister_process("task-1", pid=4242)
        assert not pid_path.exists()
        assert "task-1" not in BrpcLogDiagnosisWorker._processes

        # 非法 task_id 不抛
        BrpcLogDiagnosisWorker._unregister_process("bad task!")

    def test_terminate_pid_stale_or_invalid(self, monkeypatch, tmp_path):
        monkeypatch.setenv("WITTY_DIR", str(tmp_path))
        # master 的 pid 目录已从 brpc-diag 改为 brpc-tmp（_output_dir）
        pid_dir = tmp_path / "brpc-tmp"
        pid_dir.mkdir()
        pid_path = pid_dir / ".worker_task-1.pid"

        # 无 pid 文件
        assert not BrpcLogDiagnosisWorker._terminate_pid("task-1")
        # 非数字内容
        pid_path.write_text("abc", encoding="ascii")
        assert not BrpcLogDiagnosisWorker._terminate_pid("task-1")
        assert pid_path.exists()
        # 陈旧 pid（不存在的进程）
        pid_path.write_text("999999999", encoding="ascii")
        assert not BrpcLogDiagnosisWorker._terminate_pid("task-1")
        assert not pid_path.exists()  # 陈旧 pid 文件被清理

    def test_terminate_pid_kills_live_process_group(self, monkeypatch, tmp_path):
        monkeypatch.setenv("WITTY_DIR", str(tmp_path))
        proc = _spawn_diag_tool()
        assert _wait_for_exec(proc, "task-77")
        # master 的 pid 目录已从 brpc-diag 改为 brpc-tmp（_output_dir）
        pid_dir = tmp_path / "brpc-tmp"
        pid_dir.mkdir()
        (pid_dir / ".worker_task-77.pid").write_text(
            str(proc.pid), encoding="ascii"
        )
        monkeypatch.setattr(brpc_diag_module, "time", _FastClock())
        try:
            assert BrpcLogDiagnosisWorker._terminate_pid("task-77") is True
            assert proc.poll() is not None
        finally:
            proc.wait()
        assert not (pid_dir / ".worker_task-77.pid").exists()

    def test_terminate_popen_variants(self, monkeypatch):
        # 已退出：直接返回
        done = Mock(poll=Mock(return_value=0))
        BrpcLogDiagnosisWorker._terminate_popen(done)
        done.terminate.assert_not_called()

        # SIGTERM 后超时则 SIGKILL
        proc = Mock(
            poll=Mock(return_value=None),
            terminate=Mock(),
            wait=Mock(side_effect=[subprocess.TimeoutExpired(cmd="x", timeout=5), None]),
            kill=Mock(),
        )
        BrpcLogDiagnosisWorker._terminate_popen(proc)
        proc.terminate.assert_called_once()
        proc.kill.assert_called_once()

        # 进程已消失
        gone = Mock(
            poll=Mock(return_value=None),
            terminate=Mock(),
            wait=Mock(),
            kill=Mock(),
        )
        gone.terminate.side_effect = None
        BrpcLogDiagnosisWorker._terminate_popen(gone)
        gone.terminate.assert_called_once()


class TestBrpcDiagnosisResultPaths:
    _BATCH_DIR = Path(__file__).parent / "fixtures" / "brpc_diag" / "valid"

    def _write_batch(self, tmp_path, task_id="task-normal", first_line=None):
        # master 的 batch 目录已从 brpc-diag 改为 brpc-tmp（_output_dir）
        out = tmp_path / "brpc-tmp"
        out.mkdir(exist_ok=True)
        if first_line is None:
            first_line = (
                self._BATCH_DIR / "batch_task-normal.jsonl"
            ).read_text(encoding="utf-8").splitlines()[0]
        (out / f"batch_{task_id}.jsonl").write_text(
            first_line + "\n", encoding="utf-8"
        )
        return out

    def test_result_paths_success(self, monkeypatch, tmp_path):
        monkeypatch.setenv("WITTY_DIR", str(tmp_path))
        out = self._write_batch(tmp_path)
        import json
        schema_id = json.loads(
            (out / "batch_task-normal.jsonl").read_text(encoding="utf-8").splitlines()[0]
        )["schema_id"]
        # master 的 schema 缓存独立到 WITTY_DIR/cache（_schema_dir）
        schema_path = tmp_path / "cache" / f"schema_{schema_id}.json"
        schema_path.parent.mkdir(parents=True, exist_ok=True)
        schema_path.write_text("{}", encoding="utf-8")

        got_schema, got_batch = BrpcLogDiagnosisWorker._result_paths("task-normal")
        assert got_batch == out / "batch_task-normal.jsonl"
        assert got_schema == schema_path

    def test_result_paths_error_branches(self, monkeypatch, tmp_path):
        monkeypatch.setenv("WITTY_DIR", str(tmp_path))
        # batch 不存在
        with pytest.raises(BrpcDiagnosisWorkerError):
            BrpcLogDiagnosisWorker._result_paths("task-normal")

        # 首行非法 JSON
        self._write_batch(tmp_path, first_line="not-json")
        with pytest.raises(BrpcDiagnosisWorkerError):
            BrpcLogDiagnosisWorker._result_paths("task-normal")

        # task_id 不匹配：batch 文件存在但内容 task_id 与查询不符
        valid_first_line = (
            self._BATCH_DIR / "batch_task-normal.jsonl"
        ).read_text(encoding="utf-8").splitlines()[0]
        (tmp_path / "brpc-tmp" / "batch_task-other.jsonl").write_text(
            valid_first_line + "\n", encoding="utf-8"
        )
        with pytest.raises(BrpcDiagnosisWorkerError):
            BrpcLogDiagnosisWorker._result_paths("task-other")

        # schema 文件缺失
        with pytest.raises(BrpcDiagnosisWorkerError):
            BrpcLogDiagnosisWorker._result_paths("task-normal")


class TestBrpcDiagnosisLifecycle:
    def test_init_reinit_deinit_delete(self, monkeypatch):
        monkeypatch.setattr(
            brpc_diag_module.LogFilePGManager,
            "get_log_file_by_log_file_id",
            AsyncMock(return_value=None),
        )
        assert _run(BrpcLogDiagnosisWorker.init("log-1")) is None

        monkeypatch.setattr(
            brpc_diag_module.LogFilePGManager,
            "get_log_file_by_log_file_id",
            AsyncMock(return_value=SimpleNamespace(
                kb_id="kb-1", file_path="/logs",
            )),
        )
        add_task = AsyncMock()
        monkeypatch.setattr(brpc_diag_module.TaskPGManager, "add_task", add_task)
        monkeypatch.setattr(BaseWorker, "report", AsyncMock())
        assert _run(BrpcLogDiagnosisWorker.init("log-1")) == add_task.await_args.args[0].id

        # reinit：task 缺失 / 达上限 / 正常
        monkeypatch.setattr(
            brpc_diag_module.TaskPGManager,
            "get_task_by_task_id",
            AsyncMock(return_value=None),
        )
        assert _run(BrpcLogDiagnosisWorker.reinit("task-1")) is False

        report = AsyncMock()
        monkeypatch.setattr(brpc_diag_module, "Config", _fake_config(retry_times=3))
        monkeypatch.setattr(BaseWorker, "report", report)
        monkeypatch.setattr(
            brpc_diag_module.TaskPGManager,
            "get_task_by_task_id",
            AsyncMock(return_value=_task(retry_times=3)),
        )
        assert _run(BrpcLogDiagnosisWorker.reinit("task-1")) is False
        report.assert_not_awaited()

        monkeypatch.setattr(
            brpc_diag_module.TaskPGManager,
            "get_task_by_task_id",
            AsyncMock(return_value=_task(retry_times=1)),
        )
        assert _run(BrpcLogDiagnosisWorker.reinit("task-1")) is True

        # deinit 清理进程注册表
        BrpcLogDiagnosisWorker._processes["task-1"] = SimpleNamespace(pid=1)
        assert _run(BrpcLogDiagnosisWorker.deinit("task-1")) == "task-1"
        assert "task-1" not in BrpcLogDiagnosisWorker._processes

        # delete 委托 stop（无进程/无 pid 文件 → 未终止）
        monkeypatch.delenv("WITTY_DIR", raising=False)
        assert _run(BrpcLogDiagnosisWorker.delete("task-1")) == "task-1"

    def test_mark_failed_tolerates_manager_errors(self, monkeypatch):
        monkeypatch.setattr(BaseWorker, "report", AsyncMock())
        monkeypatch.setattr(
            brpc_diag_module.TaskPGManager,
            "update_task",
            AsyncMock(side_effect=RuntimeError("pg down")),
        )
        _run(BrpcLogDiagnosisWorker._mark_failed("task-1", "boom"))  # 不抛

        monkeypatch.setattr(
            BaseWorker, "report",
            AsyncMock(side_effect=RuntimeError("report down")),
        )
        _run(BrpcLogDiagnosisWorker._mark_failed("task-1", "boom"))  # 不抛

    def test_run_invalid_start_time_marks_failed(self, monkeypatch, tmp_path):
        log_file = tmp_path / "ub.log"
        log_file.write_text("x\n", encoding="utf-8")
        monkeypatch.setattr(
            brpc_diag_module.TaskPGManager,
            "get_task_by_task_id",
            AsyncMock(return_value=_task(
                task_type=TaskTypeEnum.BRPC_LOG_DIAGNOSIS_WORKER,
            )),
        )
        update_task = AsyncMock()
        monkeypatch.setattr(
            brpc_diag_module.TaskPGManager, "update_task", update_task
        )
        monkeypatch.setattr(
            brpc_diag_module.LogFilePGManager,
            "get_log_file_by_log_file_id",
            AsyncMock(return_value=SimpleNamespace(
                kb_id="kb-1", file_path=str(log_file),
            )),
        )
        monkeypatch.setattr(BaseWorker, "report", AsyncMock())
        # master 失败路径改走 _mark_failed -> TaskPGManager.mark_failed_with_report
        # （直连 PGManager.session 写失败报告），不再走 update_task({"status": ...})。
        mark_failed = AsyncMock()
        monkeypatch.setattr(
            brpc_diag_module.TaskPGManager,
            "mark_failed_with_report",
            mark_failed,
        )

        assert _run(BrpcLogDiagnosisWorker.run(
            "task-1", log_dir=str(log_file), start_time="bad-format",
        )) is False
        assert mark_failed.await_args.kwargs["status"] == (
            TaskStatusEnum.FAILED_PENDING_REMOVE
        )


# ---------------------------------------------------------------------------
# Section E: BrpcLogParseWorker
# ---------------------------------------------------------------------------


class TestBrpcLogParseWorkerPureLogic:
    def test_is_profiling_log(self, tmp_path):
        good = tmp_path / "ubsocket_profiling_a.txt"
        good.write_text("timeStamp: 2026-01-01T00:00:00\n", encoding="utf-8")
        bad = tmp_path / "other.log"
        bad.write_text("hello world\n", encoding="utf-8")
        assert brpc_parse_module._is_profiling_log(str(good))
        assert not brpc_parse_module._is_profiling_log(str(bad))
        assert not brpc_parse_module._is_profiling_log(str(tmp_path / "missing.log"))

    def test_init_branches(self, monkeypatch):
        monkeypatch.setattr(
            brpc_parse_module.LogFilePGManager,
            "get_log_file_by_log_file_id",
            AsyncMock(return_value=None),
        )
        assert _run(BrpcLogParseWorker.init("log-1")) is None

        monkeypatch.setattr(
            brpc_parse_module.LogFilePGManager,
            "get_log_file_by_log_file_id",
            AsyncMock(return_value=SimpleNamespace(kb_id="kb-1", name="f")),
        )
        monkeypatch.setattr(
            brpc_parse_module.LogKnowledgePGManager,
            "get_log_kb_by_kb_id",
            AsyncMock(return_value=None),
        )
        assert _run(BrpcLogParseWorker.init("log-1")) is None

        monkeypatch.setattr(
            brpc_parse_module.LogKnowledgePGManager,
            "get_log_kb_by_kb_id",
            AsyncMock(return_value=SimpleNamespace(id="kb-1")),
        )
        add_task = AsyncMock()
        monkeypatch.setattr(brpc_parse_module.TaskPGManager, "add_task", add_task)
        monkeypatch.setattr(BaseWorker, "report", AsyncMock())
        assert _run(BrpcLogParseWorker.init("log-1")) == add_task.await_args.args[0].id


class TestBrpcLogParseWorkerParseLog:
    def _patch_parser(self, monkeypatch, records):
        monkeypatch.setattr(
            brpc_parse_module,
            "BrpcProfilingParser",
            lambda: SimpleNamespace(parse_file=lambda path: records),
        )

    def test_requires_id_or_dir(self, monkeypatch):
        with pytest.raises(ValueError):
            _run(BrpcLogParseWorker.parse_log())
        monkeypatch.setattr(
            brpc_parse_module.LogFilePGManager,
            "get_log_file_by_log_file_id",
            AsyncMock(return_value=None),
        )
        with pytest.raises(ValueError):
            _run(BrpcLogParseWorker.parse_log(log_id="log-404"))

    def test_direct_file_without_log_id_skips_store(self, monkeypatch, tmp_path):
        profiling = tmp_path / "ubsocket_profiling.txt"
        profiling.write_text("timeStamp: 2026-01-01T00:00:00\n", encoding="utf-8")
        self._patch_parser(monkeypatch, [SimpleNamespace(), SimpleNamespace()])
        add_results = AsyncMock()
        monkeypatch.setattr(
            brpc_parse_module.BrpcProfilingResultPGManager,
            "add_profiling_results",
            add_results,
        )

        count = _run(BrpcLogParseWorker.parse_log(log_dir=str(profiling)))
        assert count == 2
        add_results.assert_not_awaited()

    def test_dir_scan_collects_profiling_files_only(self, monkeypatch, tmp_path):
        logs = tmp_path / "logs"
        (logs / "nested").mkdir(parents=True)
        (logs / "ub_a.txt").write_text("timeStamp: x\n", encoding="utf-8")
        (logs / "plain.log").write_text("nope\n", encoding="utf-8")
        (logs / "nested" / "ub_b.txt").write_text("timeStamp: x\n", encoding="utf-8")
        self._patch_parser(monkeypatch, [SimpleNamespace()])
        add_results = AsyncMock()
        monkeypatch.setattr(
            brpc_parse_module.BrpcProfilingResultPGManager,
            "add_profiling_results",
            add_results,
        )

        count = _run(BrpcLogParseWorker.parse_log(log_dir=str(logs)))
        assert count == 2
        add_results.assert_not_awaited()

        empty_dir = tmp_path / "empty"
        empty_dir.mkdir()
        assert _run(BrpcLogParseWorker.parse_log(log_dir=str(empty_dir))) == 0

    def test_log_id_resolves_file_path_and_stores(self, monkeypatch, tmp_path):
        profiling = tmp_path / "ub.txt"
        profiling.write_text("timeStamp: x\n", encoding="utf-8")
        monkeypatch.setattr(
            brpc_parse_module.LogFilePGManager,
            "get_log_file_by_log_file_id",
            AsyncMock(return_value=SimpleNamespace(file_path=str(profiling))),
        )
        self._patch_parser(monkeypatch, [SimpleNamespace()])
        add_results = AsyncMock(return_value=True)
        monkeypatch.setattr(
            brpc_parse_module.BrpcProfilingResultPGManager,
            "add_profiling_results",
            add_results,
        )

        assert _run(BrpcLogParseWorker.parse_log(log_id="log-1")) == 1
        add_results.assert_awaited_once_with("log-1", [add_results.await_args.args[1]][0])
        assert len(add_results.await_args.args[1]) == 1

    def test_store_failure_raises_runtime_error(self, monkeypatch, tmp_path):
        profiling = tmp_path / "ub.txt"
        profiling.write_text("timeStamp: x\n", encoding="utf-8")
        monkeypatch.setattr(
            brpc_parse_module.LogFilePGManager,
            "get_log_file_by_log_file_id",
            AsyncMock(return_value=SimpleNamespace(file_path=str(profiling))),
        )
        self._patch_parser(monkeypatch, [SimpleNamespace()])
        monkeypatch.setattr(
            brpc_parse_module.BrpcProfilingResultPGManager,
            "add_profiling_results",
            AsyncMock(return_value=False),
        )

        with pytest.raises(RuntimeError):
            _run(BrpcLogParseWorker.parse_log(log_id="log-1"))


class TestBrpcLogParseWorkerRunStopDelete:
    def _wire_run(self, monkeypatch, *, task=None, parse_result=3, parse_exc=None):
        task = task or _task(
            task_id="task-1", op_id="log-1", kb_id="kb-1",
            task_type=TaskTypeEnum.BRPC_LOG_PARSE_WORKER,
        )
        monkeypatch.setattr(
            brpc_parse_module.TaskPGManager,
            "get_task_by_task_id",
            AsyncMock(return_value=task),
        )
        update_task = AsyncMock()
        monkeypatch.setattr(
            brpc_parse_module.TaskPGManager, "update_task", update_task
        )
        parse_log = AsyncMock(return_value=parse_result)
        if parse_exc is not None:
            parse_log = AsyncMock(side_effect=parse_exc)
        monkeypatch.setattr(BrpcLogParseWorker, "parse_log", parse_log)
        touch_kb = AsyncMock()
        monkeypatch.setattr(
            brpc_parse_module.LogKnowledgePGManager, "touch_log_kb", touch_kb
        )
        # master 失败路径改走 TaskPGManager.mark_failed_with_report（直连
        # PGManager.session 写失败报告），不再走 update_task({"status": ...})。
        mark_failed = AsyncMock()
        monkeypatch.setattr(
            brpc_parse_module.TaskPGManager,
            "mark_failed_with_report",
            mark_failed,
        )
        monkeypatch.setattr(BaseWorker, "report", AsyncMock())
        return update_task, parse_log, touch_kb, mark_failed

    def test_run_success_path(self, monkeypatch):
        update_task, parse_log, touch_kb, mark_failed = self._wire_run(monkeypatch)
        assert _run(BrpcLogParseWorker.run("task-1")) is True
        assert update_task.await_args_list[-1].args[1] == {
            "status": TaskStatusEnum.SUCCESSFUL_PENDING_REMOVE.value
        }
        parse_log.assert_awaited_once()
        touch_kb.assert_awaited_once_with("kb-1")
        mark_failed.assert_not_awaited()

    def test_run_zero_records_marks_skip(self, monkeypatch):
        update_task, parse_log, touch_kb, mark_failed = self._wire_run(
            monkeypatch, parse_result=0
        )
        assert _run(BrpcLogParseWorker.run("task-1")) is True
        assert update_task.await_args_list[-1].args[1] == {
            "status": TaskStatusEnum.SUCCESSFUL_PENDING_REMOVE.value
        }
        touch_kb.assert_awaited_once()

    def test_run_task_missing(self, monkeypatch):
        self._wire_run(monkeypatch, task=None)
        monkeypatch.setattr(
            brpc_parse_module.TaskPGManager,
            "get_task_by_task_id",
            AsyncMock(return_value=None),
        )
        assert _run(BrpcLogParseWorker.run("task-404")) is False

    def test_run_parse_exception_marks_failed(self, monkeypatch):
        update_task, _, _, mark_failed = self._wire_run(
            monkeypatch, parse_exc=RuntimeError("parse died")
        )
        assert _run(BrpcLogParseWorker.run("task-1")) is False
        assert mark_failed.await_args.kwargs["status"] == (
            TaskStatusEnum.FAILED_PENDING_REMOVE
        )

    def test_stop_and_delete(self, monkeypatch):
        pending = _task(
            status=TaskStatusEnum.PENDING, op_id="log-1",
            task_type=TaskTypeEnum.BRPC_LOG_PARSE_WORKER,
        )
        monkeypatch.setattr(
            brpc_parse_module.TaskPGManager,
            "get_task_by_task_id",
            AsyncMock(return_value=pending),
        )
        update_task = AsyncMock()
        monkeypatch.setattr(
            brpc_parse_module.TaskPGManager, "update_task", update_task
        )
        delete_results = AsyncMock()
        monkeypatch.setattr(
            brpc_parse_module.BrpcProfilingResultPGManager,
            "delete_by_log_id",
            delete_results,
        )

        assert _run(BrpcLogParseWorker.stop("task-1")) == "task-1"
        delete_results.assert_awaited_once_with("log-1")
        update_task.assert_awaited_once_with(
            "task-1", {"status": TaskStatusEnum.CANCELLED.value}
        )

        monkeypatch.setattr(
            brpc_parse_module.TaskPGManager,
            "get_task_by_task_id",
            AsyncMock(return_value=_task(
                status=TaskStatusEnum.SUCCESSFUL,
                task_type=TaskTypeEnum.BRPC_LOG_PARSE_WORKER,
            )),
        )
        assert _run(BrpcLogParseWorker.stop("task-1")) is None

        monkeypatch.setattr(
            brpc_parse_module.TaskPGManager,
            "get_task_by_task_id",
            AsyncMock(return_value=None),
        )
        assert _run(BrpcLogParseWorker.stop("task-404")) is None
        assert _run(BrpcLogParseWorker.delete("task-404")) == ""

        monkeypatch.setattr(
            brpc_parse_module.TaskPGManager,
            "get_task_by_task_id",
            AsyncMock(return_value=pending),
        )
        assert _run(BrpcLogParseWorker.delete("task-1")) == "task-1"
        assert delete_results.await_count == 2
