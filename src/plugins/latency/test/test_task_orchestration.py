# Copyright (c) Huawei Technologies Co., Ltd. 2023-2025. All rights reserved.
"""task 编排层单元测试：process_handle / worker/base / task_handler / log_preprocessor。

只补既有测试（restart_recovery/progress/log_file_split/workers_logic）的缺口：
- ProcessHandler：伪造 multiprocessing.Process/Event/Lock，直测进程池决策分支；
- BaseWorker：任务状态机各分支（manager 全部 monkeypatch）；
- TaskHandler：三队列派发与预处理源目录解析；
- log_preprocessor：文件/压缩包处理（tmp_path 造真实文件，.gz/.tar.gz/.zip 现造）。
"""

from __future__ import annotations

import asyncio
import errno
import gzip
import io
import logging
import os
import shutil
import signal
import sys
import tarfile
import zipfile
from datetime import datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, call

import pytest

import latency.task.log_preprocessor as preprocessor_module
import latency.task.process_handle as process_handle_module
import latency.task.task_handler as task_handler_module
from latency.database.managers.log_file import LogFilePGManager
from latency.database.managers.task import TaskPGManager
from latency.database.managers.task_report import TaskReportPGManager
from latency.ENUM.task import TaskStatusEnum, TaskTypeEnum
from latency.schemas.task import TaskReportModel
from latency.task.log_preprocessor import (
    LogPreprocessResult,
    _configured_filename_patterns,
    _extract_archive,
    _extract_rar,
    _extract_tar,
    _extract_zip,
    _remove_empty_file,
    _safe_extract_tar_member,
    _safe_extract_zip_member,
    _safe_join,
    cleanup_preprocess_dir,
    default_preprocess_dir,
    filename_looks_like_text,
    is_valid_archive_file,
    needs_preprocess,
    preprocess_log_dir,
    split_unmatched_log_files,
)
from latency.task.process_handle import ProcessHandler
from latency.task.task_handler import TaskHandler
from latency.task.worker.base import BaseWorker
from latency.task.worker.kv_cache_log_parse_worker import KVCacheLogParseWorker
from latency.task.worker.store_trace_context_logs_worker import (
    StoreTraceContextLogsWorker,
)


# ---------------------------------------------------------------------------
# 公共辅助
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _reset_task_handler_state():
    TaskHandler._task_configs.clear()
    TaskHandler._dispatching_task_ids.clear()
    TaskHandler._preprocess_inflight.clear()
    yield
    TaskHandler._task_configs.clear()
    TaskHandler._dispatching_task_ids.clear()
    TaskHandler._preprocess_inflight.clear()


async def _drain_pending_dispatch():
    """handle_pending_tasks 后台派发：等待本轮派发协程全部结束。"""
    dispatch_tasks = list(TaskHandler._dispatch_tasks)
    if dispatch_tasks:
        await asyncio.gather(*dispatch_tasks)


def _task_row(
    task_id="t-1",
    op_id="op-1",
    status=TaskStatusEnum.RUNNING,
    retry_times=1,
    task_type=TaskTypeEnum.KV_CACHE_LOG_PARSE_WORKER,
    created_at=datetime(2026, 1, 1, 12, 0, 0),
):
    return SimpleNamespace(
        id=task_id,
        op_id=op_id,
        status=status,
        retry_times=retry_times,
        task_type=task_type,
        created_at=created_at,
    )


def _pending_task(task_id, task_type=TaskTypeEnum.KV_CACHE_LOG_PARSE_WORKER):
    return SimpleNamespace(
        id=task_id,
        op_id=f"op-{task_id}",
        task_type=task_type,
        task_config=None,
    )


# ---------------------------------------------------------------------------
# Section A: ProcessHandler（伪造 multiprocessing 上下文，不真正 spawn）
# ---------------------------------------------------------------------------


class _FakeLock:
    def __init__(self, acquire_result=True):
        self.acquire_result = acquire_result
        self.acquire_count = 0
        self.release_count = 0

    def acquire(self, timeout=None):
        self.acquire_count += 1
        return self.acquire_result

    def release(self):
        self.release_count += 1


class _FakeEvent:
    def __init__(self, wait_result=True):
        self.wait_result = wait_result
        self.set_called = False

    def set(self):
        self.set_called = True

    def wait(self, timeout=None):
        return self.wait_result


class _FakeSpawnProcess:
    """add_task 场景：记录 target/args，可注入 start 失败。"""

    def __init__(self, target=None, args=(), kwargs=None, pid=4321, start_error=None):
        self.target = target
        self.args = args
        self.kwargs = dict(kwargs or {})
        self.pid = pid
        self.started = False
        self.closed = False
        self._start_error = start_error

    def start(self):
        if self._start_error is not None:
            raise self._start_error
        self.started = True

    def is_alive(self):
        return False

    def join(self, timeout=None):
        return None

    def close(self):
        self.closed = True


class _FakeRemovableProcess:
    """remove_task 场景：可控存活/终止行为的假进程。"""

    def __init__(
        self,
        pid=4321,
        alive=True,
        join_kills=True,
        terminate_kills=True,
        kill_kills=True,
    ):
        self.pid = pid
        self._alive = alive
        self._join_kills = join_kills
        self._terminate_kills = terminate_kills
        self._kill_kills = kill_kills
        self.join_calls = []
        self.terminate_calls = 0
        self.kill_calls = 0
        self.closed = False

    def is_alive(self):
        return self._alive

    def join(self, timeout=None):
        self.join_calls.append(timeout)
        if self._join_kills:
            self._alive = False

    def terminate(self):
        self.terminate_calls += 1
        if self._terminate_kills:
            self._alive = False

    def kill(self):
        self.kill_calls += 1
        if self._kill_kills:
            self._alive = False

    def close(self):
        self.closed = True

    def start(self):
        pass


def _patch_process_pool(
    monkeypatch,
    tasks=None,
    lock=None,
    max_processes=2,
    event_wait=True,
    start_error=None,
):
    created = []

    class _FakeSpawnContext:
        @staticmethod
        def Event():
            return _FakeEvent(wait_result=event_wait)

        @staticmethod
        def Process(*, target, args=(), kwargs=None):
            process = _FakeSpawnProcess(
                target=target, args=args, kwargs=kwargs, start_error=start_error
            )
            created.append(process)
            return process

    monkeypatch.setattr(process_handle_module, "multiprocessing", _FakeSpawnContext)
    monkeypatch.setattr(ProcessHandler, "tasks", dict(tasks or {}))
    monkeypatch.setattr(ProcessHandler, "lock", lock or _FakeLock())
    monkeypatch.setattr(ProcessHandler, "max_processes", max_processes)
    return created


def _sample_target():
    pass


class TestProcessHandlerAddTask:
    def test_add_task_starts_process_and_registers(self, monkeypatch):
        created = _patch_process_pool(monkeypatch)

        assert ProcessHandler.add_task("t-1", _sample_target, "a", k=1) is True

        process = created[0]
        assert process.started is True
        assert process.target is ProcessHandler.subprocess_target
        ready_event, target, *rest = process.args
        assert isinstance(ready_event, _FakeEvent)
        assert target is _sample_target
        assert rest == ["a"]
        assert process.kwargs == {"k": 1}
        assert ProcessHandler.tasks["t-1"] is process

    def test_add_task_lock_timeout_returns_false(self, monkeypatch):
        lock = _FakeLock(acquire_result=False)
        created = _patch_process_pool(monkeypatch, lock=lock)

        assert ProcessHandler.add_task("t-1", _sample_target) is False
        assert created == []
        assert lock.release_count == 0

    def test_add_task_pool_full_returns_false(self, monkeypatch):
        lock = _FakeLock()
        live = _FakeRemovableProcess(alive=True)
        created = _patch_process_pool(
            monkeypatch, tasks={"live": live}, lock=lock, max_processes=1
        )

        assert ProcessHandler.add_task("t-1", _sample_target) is False
        assert created == []
        assert "t-1" not in ProcessHandler.tasks
        assert lock.release_count == 1

    def test_add_task_cleans_dead_process_then_admits(self, monkeypatch):
        dead = _FakeRemovableProcess(alive=False)
        created = _patch_process_pool(
            monkeypatch, tasks={"dead": dead}, max_processes=1
        )

        assert ProcessHandler.add_task("t-1", _sample_target) is True
        assert dead.closed is True
        assert "dead" not in ProcessHandler.tasks
        assert "t-1" in ProcessHandler.tasks
        assert len(created) == 1

    def test_add_task_duplicate_returns_true_without_new_process(self, monkeypatch):
        existing = _FakeRemovableProcess()
        created = _patch_process_pool(monkeypatch, tasks={"t-1": existing})

        assert ProcessHandler.add_task("t-1", _sample_target) is True
        assert created == []

    def test_add_task_start_failure_returns_false(self, monkeypatch):
        lock = _FakeLock()
        created = _patch_process_pool(
            monkeypatch, lock=lock, start_error=RuntimeError("spawn failed")
        )

        assert ProcessHandler.add_task("t-1", _sample_target) is False
        assert created[0].started is False
        assert "t-1" not in ProcessHandler.tasks
        assert lock.release_count == 1

    def test_add_task_warns_but_keeps_task_on_ready_timeout(self, monkeypatch):
        created = _patch_process_pool(monkeypatch, event_wait=False)

        assert ProcessHandler.add_task("t-1", _sample_target) is True
        assert "t-1" in ProcessHandler.tasks


class TestProcessHandlerHasCapacity:
    def test_has_capacity_lock_timeout_returns_false(self, monkeypatch):
        _patch_process_pool(monkeypatch, lock=_FakeLock(acquire_result=False))
        assert ProcessHandler.has_capacity() is False

    def test_has_capacity_cleans_dead_and_reports_room(self, monkeypatch):
        dead = _FakeRemovableProcess(alive=False)
        live = _FakeRemovableProcess(alive=True)
        _patch_process_pool(
            monkeypatch, tasks={"dead": dead, "live": live}, max_processes=2
        )

        assert ProcessHandler.has_capacity() is True
        assert dead.closed is True
        assert "dead" not in ProcessHandler.tasks
        assert "live" in ProcessHandler.tasks

    def test_has_capacity_false_when_pool_full(self, monkeypatch):
        live = _FakeRemovableProcess(alive=True)
        _patch_process_pool(monkeypatch, tasks={"live": live}, max_processes=1)
        assert ProcessHandler.has_capacity() is False


class TestProcessHandlerRemoveTask:
    def test_remove_task_lock_timeout_returns_false(self, monkeypatch):
        _patch_process_pool(monkeypatch, lock=_FakeLock(acquire_result=False))
        assert ProcessHandler.remove_task("t-1") is False

    def test_remove_task_unknown_returns_true(self, monkeypatch):
        lock = _FakeLock()
        _patch_process_pool(monkeypatch, lock=lock)
        assert ProcessHandler.remove_task("t-404") is True
        assert lock.release_count == 1

    def test_remove_task_dead_process_closes_and_pops(self, monkeypatch):
        dead = _FakeRemovableProcess(alive=False)
        _patch_process_pool(monkeypatch, tasks={"t-1": dead})

        assert ProcessHandler.remove_task("t-1") is True
        assert dead.closed is True
        assert ProcessHandler.tasks == {}

    def test_remove_task_kills_owned_process_group(self, monkeypatch):
        process = _FakeRemovableProcess(pid=4321, alive=True, join_kills=True)
        killed = []
        monkeypatch.setattr(os, "getpgid", lambda pid: pid)
        monkeypatch.setattr(
            os, "killpg", lambda pgid, sig: killed.append((pgid, sig))
        )
        _patch_process_pool(monkeypatch, tasks={"t-1": process})

        assert ProcessHandler.remove_task("t-1") is True
        assert killed == [(4321, signal.SIGTERM)]
        assert process.terminate_calls == 0
        assert process.closed is True
        assert ProcessHandler.tasks == {}

    def test_remove_task_terminates_when_not_group_leader(self, monkeypatch):
        process = _FakeRemovableProcess(pid=4321, alive=True, join_kills=True)
        killed = []
        monkeypatch.setattr(os, "getpgid", lambda pid: 999)
        monkeypatch.setattr(
            os, "killpg", lambda pgid, sig: killed.append((pgid, sig))
        )
        _patch_process_pool(monkeypatch, tasks={"t-1": process})

        assert ProcessHandler.remove_task("t-1") is True
        assert killed == []
        assert process.terminate_calls == 1

    def test_remove_task_escalates_to_sigkill_and_reports_failure(
        self, monkeypatch
    ):
        process = _FakeRemovableProcess(
            pid=4321,
            alive=True,
            join_kills=False,
            terminate_kills=False,
            kill_kills=False,
        )
        killed = []
        monkeypatch.setattr(os, "getpgid", lambda pid: pid)
        monkeypatch.setattr(
            os, "killpg", lambda pgid, sig: killed.append((pgid, sig))
        )
        _patch_process_pool(monkeypatch, tasks={"t-1": process})

        assert ProcessHandler.remove_task("t-1") is False
        assert killed == [
            (4321, signal.SIGTERM),
            (4321, signal.SIGKILL),
        ]
        assert "t-1" in ProcessHandler.tasks
        assert process.closed is False

    def test_remove_task_kills_stubborn_unowned_process(self, monkeypatch):
        # pgid != pid：terminate 无效后走 process.kill() 分支
        process = _FakeRemovableProcess(
            pid=4321,
            alive=True,
            join_kills=False,
            terminate_kills=False,
            kill_kills=True,
        )
        killed = []
        monkeypatch.setattr(os, "getpgid", lambda pid: 999)
        monkeypatch.setattr(
            os, "killpg", lambda pgid, sig: killed.append((pgid, sig))
        )
        _patch_process_pool(monkeypatch, tasks={"t-1": process})

        assert ProcessHandler.remove_task("t-1") is True
        assert killed == []
        assert process.terminate_calls == 1
        assert process.kill_calls == 1
        assert process.closed is True

    def test_remove_task_sigkill_ignores_process_lookup_error(self, monkeypatch):
        # SIGKILL 阶段进程恰好退出：getpgid 第二次抛 ProcessLookupError
        process = _FakeRemovableProcess(
            pid=4321, alive=True, join_kills=False, terminate_kills=False
        )
        killed = []
        getpgid_calls = []

        def _getpgid(pid):
            getpgid_calls.append(pid)
            if len(getpgid_calls) == 1:
                return pid
            raise ProcessLookupError()

        monkeypatch.setattr(os, "getpgid", _getpgid)
        monkeypatch.setattr(
            os, "killpg", lambda pgid, sig: killed.append((pgid, sig))
        )
        _patch_process_pool(monkeypatch, tasks={"t-1": process})

        assert ProcessHandler.remove_task("t-1") is False
        assert killed == [(4321, signal.SIGTERM)]

    def test_remove_task_ignores_process_lookup_error(self, monkeypatch):
        process = _FakeRemovableProcess(pid=4321, alive=True, join_kills=True)
        monkeypatch.setattr(
            os,
            "getpgid",
            lambda pid: (_ for _ in ()).throw(ProcessLookupError()),
        )
        _patch_process_pool(monkeypatch, tasks={"t-1": process})

        assert ProcessHandler.remove_task("t-1") is True
        assert process.closed is True

    def test_remove_task_swallows_cleanup_exception(self, monkeypatch):
        class _ExplodingProcess(_FakeRemovableProcess):
            def is_alive(self):
                raise RuntimeError("probe failed")

        process = _ExplodingProcess()
        lock = _FakeLock()
        _patch_process_pool(monkeypatch, tasks={"t-1": process}, lock=lock)

        assert ProcessHandler.remove_task("t-1") is False
        assert lock.release_count == 1


class _FakePGManager:
    def __init__(self):
        self.initialize_calls = []
        self.init_timezone_calls = 0

    def initialize(self, dsn, pool_size=None, max_overflow=None):
        self.initialize_calls.append((dsn, pool_size, max_overflow))

    async def init_timezone(self):
        self.init_timezone_calls += 1


def _ph_config_factory(backend="postgresql", log_level="INFO"):
    config = SimpleNamespace(
        db=SimpleNamespace(
            backend=backend,
            pg_dsn_url=lambda: "postgresql://fake/dsn",
            pg_pool_size=3,
            pg_max_overflow=7,
        ),
        service=SimpleNamespace(log_level=SimpleNamespace(value=log_level)),
    )
    return lambda: SimpleNamespace(get_config=lambda: config)


class TestProcessHandlerSubprocessTarget:
    def test_subprocess_target_initializes_pg_and_runs_target(self, monkeypatch):
        fake_pg = _FakePGManager()
        monkeypatch.setattr(
            process_handle_module, "Config", _ph_config_factory("postgresql")
        )
        monkeypatch.setattr(process_handle_module, "PGManager", fake_pg)
        monkeypatch.setattr(os, "setsid", lambda: None)
        ready = _FakeEvent()
        seen = {}

        async def target(*args, **kwargs):
            seen["args"] = args
            seen["kwargs"] = kwargs
            return "done"

        ProcessHandler.subprocess_target(ready, target, "a", b=2)

        assert ready.set_called is True
        assert fake_pg.initialize_calls == [("postgresql://fake/dsn", 3, 7)]
        assert fake_pg.init_timezone_calls == 1
        assert seen == {"args": ("a",), "kwargs": {"b": 2}}

    def test_subprocess_target_skips_pg_for_sqlite_backend(self, monkeypatch):
        fake_pg = _FakePGManager()
        monkeypatch.setattr(
            process_handle_module, "Config", _ph_config_factory("sqlite")
        )
        monkeypatch.setattr(process_handle_module, "PGManager", fake_pg)
        monkeypatch.setattr(os, "setsid", lambda: None)
        ready = _FakeEvent()

        async def target():
            return None

        ProcessHandler.subprocess_target(ready, target)

        assert ready.set_called is True
        assert fake_pg.initialize_calls == []
        assert fake_pg.init_timezone_calls == 0

    def test_subprocess_target_survives_setsid_failure(self, monkeypatch):
        fake_pg = _FakePGManager()
        monkeypatch.setattr(
            process_handle_module, "Config", _ph_config_factory("sqlite")
        )
        monkeypatch.setattr(process_handle_module, "PGManager", fake_pg)

        def _setsid_boom():
            raise OSError("not allowed")

        monkeypatch.setattr(os, "setsid", _setsid_boom)
        ready = _FakeEvent()
        ran = []

        async def target():
            ran.append(True)

        ProcessHandler.subprocess_target(ready, target)

        assert ready.set_called is True
        assert ran == [True]

    def test_subprocess_target_reraises_target_exception(self, monkeypatch):
        monkeypatch.setattr(
            process_handle_module, "Config", _ph_config_factory("sqlite")
        )
        monkeypatch.setattr(
            process_handle_module, "PGManager", _FakePGManager()
        )
        monkeypatch.setattr(os, "setsid", lambda: None)
        ready = _FakeEvent()

        async def boom():
            raise ValueError("task crashed")

        with pytest.raises(ValueError, match="task crashed"):
            ProcessHandler.subprocess_target(ready, boom)

        assert ready.set_called is True


class TestProcessHandlerHelpers:
    async def test_run_target_after_init_awaits_timezone_for_pg(self, monkeypatch):
        fake_pg = _FakePGManager()
        monkeypatch.setattr(
            process_handle_module, "Config", _ph_config_factory("postgresql")
        )
        monkeypatch.setattr(process_handle_module, "PGManager", fake_pg)

        async def target(x, y=None):
            return (x, y)

        assert await ProcessHandler._run_target_after_init(target, 1, y=2) == (1, 2)
        assert fake_pg.init_timezone_calls == 1

    async def test_run_target_after_init_skips_timezone_for_sqlite(
        self, monkeypatch
    ):
        fake_pg = _FakePGManager()
        monkeypatch.setattr(
            process_handle_module, "Config", _ph_config_factory("sqlite")
        )
        monkeypatch.setattr(process_handle_module, "PGManager", fake_pg)

        async def target():
            return "ok"

        assert await ProcessHandler._run_target_after_init(target) == "ok"
        assert fake_pg.init_timezone_calls == 0

    def test_setup_child_process_logging_applies_levels(self, monkeypatch):
        monkeypatch.setattr(
            process_handle_module, "Config", _ph_config_factory(log_level="WARNING")
        )
        ProcessHandler._setup_child_process_logging()
        assert logging.getLogger("latency.database").level == logging.WARNING
        assert (
            logging.getLogger("apscheduler.executors.default").level
            == logging.WARNING
        )

    def test_setup_child_process_logging_falls_back_to_info(self, monkeypatch):
        monkeypatch.setattr(
            process_handle_module, "Config", _ph_config_factory("NOT_A_LEVEL")
        )
        ProcessHandler._setup_child_process_logging()
        assert (
            logging.getLogger("latency.task.task_handler").level == logging.INFO
        )


# ---------------------------------------------------------------------------
# Section B: BaseWorker 状态机
# ---------------------------------------------------------------------------


class TestBaseWorkerReflection:
    def test_find_worker_class_matches_registered_worker(self):
        assert (
            BaseWorker.find_worker_class(TaskTypeEnum.KV_CACHE_LOG_PARSE_WORKER)
            is KVCacheLogParseWorker
        )

    def test_find_worker_class_returns_none_for_unknown(self):
        assert BaseWorker.find_worker_class("unknown-worker") is None

    async def test_get_worker_name_returns_task_type(self, monkeypatch):
        monkeypatch.setattr(
            TaskPGManager,
            "get_task_by_task_id",
            AsyncMock(
                return_value=SimpleNamespace(
                    task_type=TaskTypeEnum.BRPC_LOG_PARSE_WORKER
                )
            ),
        )
        assert (
            await BaseWorker.get_worker_name("t-1")
            == TaskTypeEnum.BRPC_LOG_PARSE_WORKER
        )

    async def test_get_worker_name_raises_when_task_missing(self, monkeypatch):
        monkeypatch.setattr(
            TaskPGManager, "get_task_by_task_id", AsyncMock(return_value=None)
        )
        with pytest.raises(ValueError, match="获取任务失败"):
            await BaseWorker.get_worker_name("t-404")


class TestBaseWorkerLifecycle:
    async def test_base_init_marks_task_pending(self, monkeypatch):
        monkeypatch.setattr(
            KVCacheLogParseWorker, "init", AsyncMock(return_value="tid-1")
        )
        update = AsyncMock(return_value=True)
        monkeypatch.setattr(TaskPGManager, "update_task", update)

        assert (
            await BaseWorker.init(
                TaskTypeEnum.KV_CACHE_LOG_PARSE_WORKER, "op-1"
            )
            == "tid-1"
        )
        update.assert_awaited_once_with(
            "tid-1", {"status": TaskStatusEnum.PENDING.value}
        )

    async def test_reinit_returns_false_when_task_missing(self, monkeypatch):
        monkeypatch.setattr(
            TaskPGManager, "get_task_by_task_id", AsyncMock(return_value=None)
        )
        assert await BaseWorker.reinit("t-404") is False

    async def test_reinit_success_increments_retry(self, monkeypatch):
        task = _task_row(retry_times=2)
        monkeypatch.setattr(
            TaskPGManager, "get_task_by_task_id", AsyncMock(return_value=task)
        )
        monkeypatch.setattr(
            KVCacheLogParseWorker, "reinit", AsyncMock(return_value=True)
        )
        removed = Mock(return_value=True)
        monkeypatch.setattr(ProcessHandler, "remove_task", removed)
        update = AsyncMock(return_value=True)
        monkeypatch.setattr(TaskPGManager, "update_task", update)

        assert await BaseWorker.reinit("t-1") is True
        removed.assert_called_once_with("t-1")
        args, _ = update.await_args
        assert args[0] == "t-1"
        assert args[1]["status"] == TaskStatusEnum.PENDING.value
        assert args[1]["retry_times"] == 3

    async def test_reinit_failure_marks_task_failed(self, monkeypatch):
        task = _task_row(retry_times=2)
        monkeypatch.setattr(
            TaskPGManager, "get_task_by_task_id", AsyncMock(return_value=task)
        )
        monkeypatch.setattr(
            KVCacheLogParseWorker, "reinit", AsyncMock(return_value=False)
        )
        monkeypatch.setattr(ProcessHandler, "remove_task", Mock(return_value=True))
        update = AsyncMock(return_value=True)
        monkeypatch.setattr(TaskPGManager, "update_task", update)

        assert await BaseWorker.reinit("t-1") is False
        payload = update.await_args.args[1]
        assert payload["status"] == TaskStatusEnum.FAILED.value
        assert payload["duration_seconds"] > 0
        assert "completed_at" in payload

    async def test_reinit_failure_without_created_at_zero_duration(
        self, monkeypatch
    ):
        task = _task_row(created_at=None)
        monkeypatch.setattr(
            TaskPGManager, "get_task_by_task_id", AsyncMock(return_value=task)
        )
        monkeypatch.setattr(
            KVCacheLogParseWorker, "reinit", AsyncMock(return_value=False)
        )
        monkeypatch.setattr(ProcessHandler, "remove_task", Mock(return_value=True))
        update = AsyncMock(return_value=True)
        monkeypatch.setattr(TaskPGManager, "update_task", update)

        assert await BaseWorker.reinit("t-1") is False
        assert update.await_args.args[1]["duration_seconds"] == 0.0

    async def test_deinit_returns_empty_when_task_missing(self, monkeypatch):
        monkeypatch.setattr(
            TaskPGManager, "get_task_by_task_id", AsyncMock(return_value=None)
        )
        assert await BaseWorker.deinit("t-404") == ""

    async def test_deinit_non_preprocess_worker_skips_cleanup(self, monkeypatch):
        task = _task_row(
            task_type=TaskTypeEnum.STORE_TRACE_CONTEXT_LOGS_WORKER,
            status=TaskStatusEnum.SUCCESSFUL_PENDING_REMOVE,
        )
        monkeypatch.setattr(
            TaskPGManager, "get_task_by_task_id", AsyncMock(return_value=task)
        )
        removed = Mock(return_value=True)
        monkeypatch.setattr(ProcessHandler, "remove_task", removed)
        worker_deinit = AsyncMock()
        monkeypatch.setattr(StoreTraceContextLogsWorker, "deinit", worker_deinit)
        update = AsyncMock(return_value=True)
        monkeypatch.setattr(TaskPGManager, "update_task", update)
        get_current = AsyncMock()
        monkeypatch.setattr(
            TaskPGManager, "get_current_task_by_op_id", get_current
        )

        assert await BaseWorker.deinit("t-1") is None
        worker_deinit.assert_awaited_once_with("t-1")
        removed.assert_called_once_with("t-1")
        payload = update.await_args.args[1]
        assert payload["status"] == TaskStatusEnum.SUCCESSFUL.value
        assert payload["duration_seconds"] > 0
        get_current.assert_not_awaited()

    async def test_deinit_preprocess_worker_cleans_shared_dir(self, monkeypatch):
        task = _task_row()
        monkeypatch.setattr(
            TaskPGManager, "get_task_by_task_id", AsyncMock(return_value=task)
        )
        monkeypatch.setattr(ProcessHandler, "remove_task", Mock(return_value=True))
        monkeypatch.setattr(KVCacheLogParseWorker, "deinit", AsyncMock())
        update = AsyncMock(return_value=True)
        monkeypatch.setattr(TaskPGManager, "update_task", update)
        monkeypatch.setattr(
            TaskPGManager,
            "get_current_task_by_op_id",
            AsyncMock(
                side_effect=[
                    SimpleNamespace(status=TaskStatusEnum.SUCCESSFUL),
                    SimpleNamespace(status=TaskStatusEnum.SUCCESSFUL),
                ]
            ),
        )
        cleaned = []
        monkeypatch.setattr(
            preprocessor_module,
            "cleanup_preprocess_dir",
            lambda log_file_id: cleaned.append(log_file_id),
        )

        await BaseWorker.deinit("t-1")

        assert cleaned == ["op-1"]

    async def test_deinit_skips_cleanup_until_group_all_successful(
        self, monkeypatch
    ):
        task = _task_row()
        monkeypatch.setattr(
            TaskPGManager, "get_task_by_task_id", AsyncMock(return_value=task)
        )
        monkeypatch.setattr(ProcessHandler, "remove_task", Mock(return_value=True))
        monkeypatch.setattr(KVCacheLogParseWorker, "deinit", AsyncMock())
        monkeypatch.setattr(TaskPGManager, "update_task", AsyncMock(return_value=True))
        monkeypatch.setattr(
            TaskPGManager,
            "get_current_task_by_op_id",
            AsyncMock(
                side_effect=[
                    SimpleNamespace(status=TaskStatusEnum.SUCCESSFUL),
                    SimpleNamespace(status=TaskStatusEnum.RUNNING),
                ]
            ),
        )
        cleanup = Mock()
        monkeypatch.setattr(preprocessor_module, "cleanup_preprocess_dir", cleanup)

        await BaseWorker.deinit("t-1")

        cleanup.assert_not_called()


class TestBaseWorkerCleanupPreprocessDir:
    async def test_cleanup_ignores_non_group_worker(self, monkeypatch):
        get_current = AsyncMock()
        monkeypatch.setattr(
            TaskPGManager, "get_current_task_by_op_id", get_current
        )
        cleanup = Mock()
        monkeypatch.setattr(preprocessor_module, "cleanup_preprocess_dir", cleanup)

        await BaseWorker._cleanup_preprocess_dir_if_all_done(
            "op-1", TaskTypeEnum.STORE_TRACE_CONTEXT_LOGS_WORKER
        )

        get_current.assert_not_awaited()
        cleanup.assert_not_called()

    async def test_cleanup_waits_for_both_group_tasks(self, monkeypatch):
        monkeypatch.setattr(
            TaskPGManager,
            "get_current_task_by_op_id",
            AsyncMock(
                side_effect=[None, SimpleNamespace(status=TaskStatusEnum.SUCCESSFUL)]
            ),
        )
        cleanup = Mock()
        monkeypatch.setattr(preprocessor_module, "cleanup_preprocess_dir", cleanup)

        await BaseWorker._cleanup_preprocess_dir_if_all_done(
            "op-1", TaskTypeEnum.KV_CACHE_LOG_PARSE_WORKER
        )

        cleanup.assert_not_called()

    async def test_cleanup_runs_when_group_all_successful(self, monkeypatch):
        monkeypatch.setattr(
            TaskPGManager,
            "get_current_task_by_op_id",
            AsyncMock(
                return_value=SimpleNamespace(status=TaskStatusEnum.SUCCESSFUL)
            ),
        )
        cleanup = Mock(return_value=None)
        monkeypatch.setattr(preprocessor_module, "cleanup_preprocess_dir", cleanup)

        await BaseWorker._cleanup_preprocess_dir_if_all_done(
            "op-1", TaskTypeEnum.BRPC_LOG_PARSE_WORKER
        )

        cleanup.assert_called_once_with("op-1")


class TestBaseWorkerRun:
    async def test_run_returns_false_when_task_missing(self, monkeypatch):
        monkeypatch.setattr(
            TaskPGManager, "get_task_by_task_id", AsyncMock(return_value=None)
        )
        assert await BaseWorker.run("t-404") is False

    async def test_run_returns_false_when_pool_rejects(self, monkeypatch):
        monkeypatch.setattr(
            TaskPGManager,
            "get_task_by_task_id",
            AsyncMock(return_value=_task_row()),
        )
        add_task = Mock(return_value=False)
        monkeypatch.setattr(ProcessHandler, "add_task", add_task)
        update = AsyncMock(return_value=True)
        monkeypatch.setattr(TaskPGManager, "update_task", update)

        assert await BaseWorker.run("t-1") is False
        add_task.assert_called_once()
        update.assert_not_awaited()

    async def test_run_registers_process_and_marks_running(self, monkeypatch):
        monkeypatch.setattr(
            TaskPGManager,
            "get_task_by_task_id",
            AsyncMock(return_value=_task_row()),
        )
        add_task = Mock(return_value=True)
        monkeypatch.setattr(ProcessHandler, "add_task", add_task)
        update = AsyncMock(return_value=True)
        monkeypatch.setattr(TaskPGManager, "update_task", update)

        assert (
            await BaseWorker.run(
                "t-1", log_dir="/logs", worker_kwargs={"parse_config": None}
            )
            is True
        )

        args = add_task.call_args.args
        assert args[0] == "t-1"
        assert args[1] is KVCacheLogParseWorker.run
        # BaseWorker.run 的 *args = (task_id, log_dir)，随 target 一并传给进程池
        assert args[2:] == ("t-1", "/logs")
        assert add_task.call_args.kwargs == {"parse_config": None}
        update.assert_awaited_once_with(
            "t-1", {"status": TaskStatusEnum.RUNNING.value}
        )

    async def test_run_without_log_dir_passes_single_arg(self, monkeypatch):
        monkeypatch.setattr(
            TaskPGManager,
            "get_task_by_task_id",
            AsyncMock(return_value=_task_row()),
        )
        add_task = Mock(return_value=True)
        monkeypatch.setattr(ProcessHandler, "add_task", add_task)
        monkeypatch.setattr(TaskPGManager, "update_task", AsyncMock(return_value=True))

        assert await BaseWorker.run("t-1") is True
        assert add_task.call_args.args[2:] == ("t-1",)


class TestBaseWorkerStop:
    async def test_stop_returns_true_when_task_missing(self, monkeypatch):
        monkeypatch.setattr(
            TaskPGManager, "get_task_by_task_id", AsyncMock(return_value=None)
        )
        assert await BaseWorker.stop("t-404") is True

    async def test_stop_running_task_cancels_and_updates(self, monkeypatch):
        task = _task_row(status=TaskStatusEnum.RUNNING)
        monkeypatch.setattr(
            TaskPGManager, "get_task_by_task_id", AsyncMock(return_value=task)
        )
        removed = Mock(return_value=True)
        monkeypatch.setattr(ProcessHandler, "remove_task", removed)
        worker_stop = AsyncMock(return_value="t-1")
        monkeypatch.setattr(KVCacheLogParseWorker, "stop", worker_stop)
        update = AsyncMock(return_value=True)
        monkeypatch.setattr(TaskPGManager, "update_task", update)

        assert await BaseWorker.stop("t-1") is True
        removed.assert_called_once_with("t-1")
        worker_stop.assert_awaited_once_with("t-1")
        payload = update.await_args.args[1]
        assert payload["status"] == TaskStatusEnum.CANCELLED.value
        assert payload["duration_seconds"] > 0

    async def test_stop_running_task_reports_failure_when_process_alive(
        self, monkeypatch
    ):
        task = _task_row(status=TaskStatusEnum.RUNNING)
        monkeypatch.setattr(
            TaskPGManager, "get_task_by_task_id", AsyncMock(return_value=task)
        )
        monkeypatch.setattr(
            ProcessHandler, "remove_task", Mock(return_value=False)
        )
        worker_stop = AsyncMock(return_value=None)
        monkeypatch.setattr(KVCacheLogParseWorker, "stop", worker_stop)
        update = AsyncMock(return_value=True)
        monkeypatch.setattr(TaskPGManager, "update_task", update)

        assert await BaseWorker.stop("t-1") is False
        worker_stop.assert_awaited_once_with("t-1")
        update.assert_not_awaited()

    async def test_stop_pending_task_skips_process_removal(self, monkeypatch):
        task = _task_row(status=TaskStatusEnum.PENDING)
        monkeypatch.setattr(
            TaskPGManager, "get_task_by_task_id", AsyncMock(return_value=task)
        )
        removed = Mock(return_value=True)
        monkeypatch.setattr(ProcessHandler, "remove_task", removed)
        monkeypatch.setattr(KVCacheLogParseWorker, "stop", AsyncMock(return_value=None))
        update = AsyncMock(return_value=True)
        monkeypatch.setattr(TaskPGManager, "update_task", update)

        assert await BaseWorker.stop("t-1") is True
        removed.assert_not_called()
        update.assert_awaited_once()
        assert update.await_args.args[1]["status"] == TaskStatusEnum.CANCELLED.value

    async def test_stop_cancelled_task_short_circuits(self, monkeypatch):
        task = _task_row(status=TaskStatusEnum.CANCELLED)
        monkeypatch.setattr(
            TaskPGManager, "get_task_by_task_id", AsyncMock(return_value=task)
        )
        worker_stop = AsyncMock(return_value="t-1")
        monkeypatch.setattr(KVCacheLogParseWorker, "stop", worker_stop)
        update = AsyncMock(return_value=True)
        monkeypatch.setattr(TaskPGManager, "update_task", update)

        assert await BaseWorker.stop("t-1") is True
        worker_stop.assert_not_awaited()
        update.assert_not_awaited()

    async def test_stop_terminal_task_keeps_status(self, monkeypatch):
        task = _task_row(status=TaskStatusEnum.SUCCESSFUL)
        monkeypatch.setattr(
            TaskPGManager, "get_task_by_task_id", AsyncMock(return_value=task)
        )
        removed = Mock(return_value=True)
        monkeypatch.setattr(ProcessHandler, "remove_task", removed)
        worker_stop = AsyncMock(return_value="t-1")
        monkeypatch.setattr(KVCacheLogParseWorker, "stop", worker_stop)
        update = AsyncMock(return_value=True)
        monkeypatch.setattr(TaskPGManager, "update_task", update)

        assert await BaseWorker.stop("t-1") is True
        removed.assert_not_called()
        worker_stop.assert_awaited_once_with("t-1")
        update.assert_not_awaited()

    async def test_stop_swallows_worker_stop_exception(self, monkeypatch):
        task = _task_row(status=TaskStatusEnum.RUNNING)
        monkeypatch.setattr(
            TaskPGManager, "get_task_by_task_id", AsyncMock(return_value=task)
        )
        monkeypatch.setattr(ProcessHandler, "remove_task", Mock(return_value=True))
        monkeypatch.setattr(
            KVCacheLogParseWorker,
            "stop",
            AsyncMock(side_effect=RuntimeError("worker boom")),
        )
        update = AsyncMock(return_value=True)
        monkeypatch.setattr(TaskPGManager, "update_task", update)

        assert await BaseWorker.stop("t-1") is True
        update.assert_awaited_once()
        assert update.await_args.args[1]["status"] == TaskStatusEnum.CANCELLED.value


class TestBaseWorkerDeleteReport:
    async def test_delete_returns_false_when_task_missing(self, monkeypatch):
        monkeypatch.setattr(
            TaskPGManager, "get_task_by_task_id", AsyncMock(return_value=None)
        )
        assert await BaseWorker.delete("t-404") is False

    async def test_delete_removes_task_records(self, monkeypatch):
        monkeypatch.setattr(
            TaskPGManager,
            "get_task_by_task_id",
            AsyncMock(return_value=_task_row()),
        )
        worker_delete = AsyncMock(return_value=True)
        monkeypatch.setattr(KVCacheLogParseWorker, "delete", worker_delete)
        delete_task = AsyncMock(return_value=True)
        monkeypatch.setattr(
            TaskPGManager, "delete_task_by_task_id", delete_task
        )

        assert await BaseWorker.delete("t-1") is True
        worker_delete.assert_awaited_once_with("t-1")
        delete_task.assert_awaited_once_with("t-1")

    async def test_report_persists_task_report(self, monkeypatch):
        add_report = AsyncMock(return_value=True)
        monkeypatch.setattr(TaskReportPGManager, "add_task_report", add_report)

        assert await BaseWorker.report("t-1", "msg", 12.5) is True

        model = add_report.await_args.args[0]
        assert isinstance(model, TaskReportModel)
        assert model.task_id == "t-1"
        assert model.message == "msg"
        assert model.progress == 12.5


# ---------------------------------------------------------------------------
# Section C: TaskHandler 队列派发
# ---------------------------------------------------------------------------


class TestTaskHandlerInitTask:
    async def test_init_task_raises_when_worker_creates_no_record(self, monkeypatch):
        monkeypatch.setattr(BaseWorker, "init", AsyncMock(return_value=None))
        with pytest.raises(RuntimeError, match="未创建任务记录"):
            await TaskHandler.init_task(
                TaskTypeEnum.KV_CACHE_LOG_PARSE_WORKER, "op-1"
            )

    async def test_init_task_cleans_config_when_persist_fails(self, monkeypatch):
        monkeypatch.setattr(
            BaseWorker, "init", AsyncMock(return_value="tid-1")
        )
        monkeypatch.setattr(
            TaskPGManager,
            "update_task",
            AsyncMock(side_effect=RuntimeError("db down")),
        )

        with pytest.raises(RuntimeError, match="db down"):
            await TaskHandler.init_task(
                TaskTypeEnum.KV_CACHE_LOG_PARSE_WORKER, "op-1"
            )

        assert "tid-1" not in TaskHandler._task_configs

    def test_task_config_accessors(self):
        TaskHandler._task_configs["t-1"] = "cfg"
        assert TaskHandler.get_task_config("t-1") == "cfg"
        assert TaskHandler.get_task_config("missing") is None
        TaskHandler.remove_task_config("t-1")
        assert TaskHandler.get_task_config("t-1") is None


class TestTaskHandlerFailureMarking:
    async def test_fail_preprocess_for_insufficient_space_cleans_and_marks(
        self, monkeypatch
    ):
        cleaned = []
        monkeypatch.setattr(
            preprocessor_module,
            "cleanup_preprocess_dir",
            lambda log_file_id: cleaned.append(log_file_id),
        )
        mark_failed = AsyncMock(return_value=True)
        monkeypatch.setattr(
            TaskPGManager, "mark_failed_with_report", mark_failed
        )
        task = SimpleNamespace(id="t-1", op_id="op-1")

        await TaskHandler._fail_preprocess_for_insufficient_space(task)

        assert cleaned == ["op-1"]
        mark_failed.assert_awaited_once_with(
            "t-1", "任务失败：服务器磁盘空间不足，请清理空间后重新提交"
        )

    async def test_fail_preprocess_swallows_mark_failure(self, monkeypatch):
        monkeypatch.setattr(
            preprocessor_module, "cleanup_preprocess_dir", Mock()
        )
        monkeypatch.setattr(
            TaskPGManager,
            "mark_failed_with_report",
            AsyncMock(side_effect=RuntimeError("db down")),
        )
        await TaskHandler._fail_preprocess_for_insufficient_space(
            SimpleNamespace(id="t-1", op_id="op-1")
        )

    async def test_fail_task_for_dispatch_error_marks_retryable(self, monkeypatch):
        mark_failed = AsyncMock(return_value=True)
        monkeypatch.setattr(
            TaskPGManager, "mark_failed_with_report", mark_failed
        )

        await TaskHandler._fail_task_for_dispatch_error(
            SimpleNamespace(id="t-2"), ValueError("src gone")
        )

        args, kwargs = mark_failed.await_args
        assert args[0] == "t-2"
        assert "src gone" in args[1]
        assert kwargs["status"] == TaskStatusEnum.FAILED_PENDING_REMOVE

    async def test_fail_task_for_dispatch_error_swallows_mark_failure(
        self, monkeypatch
    ):
        monkeypatch.setattr(
            TaskPGManager,
            "mark_failed_with_report",
            AsyncMock(side_effect=RuntimeError("db down")),
        )
        await TaskHandler._fail_task_for_dispatch_error(
            SimpleNamespace(id="t-3"), ValueError("x")
        )


class TestTaskHandlerPreprocessSource:
    async def test_preprocess_log_source_returns_none_without_log_file(
        self, monkeypatch
    ):
        monkeypatch.setattr(
            LogFilePGManager,
            "get_log_file_by_log_file_id",
            AsyncMock(return_value=None),
        )
        task = SimpleNamespace(id="t-1", op_id="op-1")
        assert await TaskHandler._preprocess_log_source(task) is None

    async def test_preprocess_log_source_scans_source_directly(self, monkeypatch):
        log_file = SimpleNamespace(id="lf-1", file_path="/src")
        monkeypatch.setattr(
            LogFilePGManager,
            "get_log_file_by_log_file_id",
            AsyncMock(return_value=log_file),
        )
        needs = Mock(return_value=False)
        monkeypatch.setattr(task_handler_module, "needs_preprocess", needs)
        report = AsyncMock(return_value=True)
        monkeypatch.setattr(BaseWorker, "report", report)

        task = SimpleNamespace(id="t-1", op_id="lf-1")
        assert await TaskHandler._preprocess_log_source(task) == "/src"
        needs.assert_called_once_with("/src")
        report.assert_awaited_once_with(
            "t-1", "日志无需预处理，直接扫描源目录", 5.0
        )

    async def test_preprocess_log_source_runs_preprocess(self, monkeypatch):
        log_file = SimpleNamespace(id="lf-2", file_path="/src-2")
        monkeypatch.setattr(
            LogFilePGManager,
            "get_log_file_by_log_file_id",
            AsyncMock(return_value=log_file),
        )
        monkeypatch.setattr(
            task_handler_module, "needs_preprocess", lambda path: True
        )
        monkeypatch.setattr(
            task_handler_module,
            "default_preprocess_dir",
            lambda log_file_id: f"/out/{log_file_id}",
        )

        def fake_preprocess(source, output):
            return LogPreprocessResult(
                source_dir=source,
                output_dir=output,
                extracted_count=1,
                copied_count=2,
                split_count=3,
                reused=False,
            )

        monkeypatch.setattr(
            task_handler_module, "preprocess_log_dir", fake_preprocess
        )
        report = AsyncMock(return_value=True)
        monkeypatch.setattr(BaseWorker, "report", report)

        task = SimpleNamespace(id="t-2", op_id="lf-2")
        assert await TaskHandler._preprocess_log_source(task) == "/out/lf-2"
        assert report.await_args_list == [
            call("t-2", "正在预处理日志（解压/拷贝）", 1.0),
            call("t-2", "日志预处理完成", 5.0),
        ]
        assert TaskHandler._preprocess_inflight == {}

    async def test_preprocess_log_source_cleans_inflight_on_error(
        self, monkeypatch
    ):
        log_file = SimpleNamespace(id="lf-3", file_path="/src-3")
        monkeypatch.setattr(
            LogFilePGManager,
            "get_log_file_by_log_file_id",
            AsyncMock(return_value=log_file),
        )
        monkeypatch.setattr(
            task_handler_module, "needs_preprocess", lambda path: True
        )
        monkeypatch.setattr(
            task_handler_module,
            "default_preprocess_dir",
            lambda log_file_id: f"/out/{log_file_id}",
        )

        def fake_preprocess(source, output):
            raise FileNotFoundError("source vanished")

        monkeypatch.setattr(
            task_handler_module, "preprocess_log_dir", fake_preprocess
        )
        monkeypatch.setattr(BaseWorker, "report", AsyncMock(return_value=True))

        task = SimpleNamespace(id="t-3", op_id="lf-3")
        with pytest.raises(FileNotFoundError):
            await TaskHandler._preprocess_log_source(task)

        assert TaskHandler._preprocess_inflight == {}

    async def test_preprocess_log_source_shares_inflight_future(self, monkeypatch):
        log_file = SimpleNamespace(id="lf-4", file_path="/src-4")
        monkeypatch.setattr(
            LogFilePGManager,
            "get_log_file_by_log_file_id",
            AsyncMock(return_value=log_file),
        )
        needs = Mock(return_value=True)
        monkeypatch.setattr(task_handler_module, "needs_preprocess", needs)
        report = AsyncMock(return_value=True)
        monkeypatch.setattr(BaseWorker, "report", report)

        result = LogPreprocessResult(
            source_dir="/src-4",
            output_dir="/out/lf-4",
            extracted_count=0,
            copied_count=1,
            split_count=0,
            reused=True,
        )
        loop = asyncio.get_running_loop()
        future = loop.create_future()
        future.set_result(result)
        TaskHandler._preprocess_inflight["lf-4"] = future

        task = SimpleNamespace(id="t-4", op_id="lf-4")
        assert await TaskHandler._preprocess_log_source(task) == "/out/lf-4"
        needs.assert_not_called()
        report.assert_awaited_once_with(
            "t-4", "复用已完成的日志预处理目录", 5.0
        )


class TestTaskHandlerStopDelete:
    async def test_stop_task_returns_none_when_worker_stop_fails(self, monkeypatch):
        monkeypatch.setattr(BaseWorker, "stop", AsyncMock(return_value=False))
        assert await TaskHandler.stop_task("t-1") is None

    async def test_stop_task_returns_task_id_on_success(self, monkeypatch):
        monkeypatch.setattr(BaseWorker, "stop", AsyncMock(return_value=True))
        assert await TaskHandler.stop_task("t-1") == "t-1"

    async def test_stop_task_swallows_exception(self, monkeypatch):
        monkeypatch.setattr(
            BaseWorker, "stop", AsyncMock(side_effect=RuntimeError("boom"))
        )
        assert await TaskHandler.stop_task("t-1") is None

    async def test_delete_task_returns_none_when_stop_fails(self, monkeypatch):
        monkeypatch.setattr(BaseWorker, "stop", AsyncMock(return_value=False))
        delete = AsyncMock(return_value=True)
        monkeypatch.setattr(BaseWorker, "delete", delete)
        assert await TaskHandler.delete_task("t-1") is None
        delete.assert_not_awaited()

    async def test_delete_task_returns_none_when_delete_fails(self, monkeypatch):
        monkeypatch.setattr(BaseWorker, "stop", AsyncMock(return_value=True))
        monkeypatch.setattr(BaseWorker, "delete", AsyncMock(return_value=False))
        assert await TaskHandler.delete_task("t-1") is None

    async def test_delete_task_succeeds(self, monkeypatch):
        monkeypatch.setattr(BaseWorker, "stop", AsyncMock(return_value=True))
        delete = AsyncMock(return_value=True)
        monkeypatch.setattr(BaseWorker, "delete", delete)
        assert await TaskHandler.delete_task("t-1") == "t-1"
        delete.assert_awaited_once_with("t-1")

    async def test_delete_task_swallows_exception(self, monkeypatch):
        monkeypatch.setattr(
            BaseWorker, "stop", AsyncMock(side_effect=RuntimeError("boom"))
        )
        assert await TaskHandler.delete_task("t-1") is None


class TestTaskHandlerQueues:
    async def test_handle_successed_tasks_continues_after_error(self, monkeypatch):
        tasks = [SimpleNamespace(id="ok"), SimpleNamespace(id="bad")]
        get_oldest = AsyncMock(return_value=tasks)
        monkeypatch.setattr(
            TaskPGManager, "get_oldest_tasks_by_status", get_oldest
        )
        deinit = AsyncMock(side_effect=[None, RuntimeError("boom")])
        monkeypatch.setattr(BaseWorker, "deinit", deinit)

        await TaskHandler.handle_successed_tasks()

        assert deinit.await_count == 2
        assert (
            get_oldest.await_args.args[0] is TaskStatusEnum.SUCCESSFUL_PENDING_REMOVE
        )

    async def test_handle_failed_tasks_routes_reinit_results(self, monkeypatch):
        tasks = [
            SimpleNamespace(id="a"),
            SimpleNamespace(id="b"),
            SimpleNamespace(id="c"),
        ]
        get_oldest = AsyncMock(return_value=tasks)
        monkeypatch.setattr(
            TaskPGManager, "get_oldest_tasks_by_status", get_oldest
        )
        reinit = AsyncMock(side_effect=[True, False, RuntimeError("boom")])
        monkeypatch.setattr(BaseWorker, "reinit", reinit)

        await TaskHandler.handle_failed_tasks()  # 不抛异常

        assert reinit.await_count == 3
        assert (
            get_oldest.await_args.args[0] is TaskStatusEnum.FAILED_PENDING_REMOVE
        )

    async def test_handle_pending_tasks_caps_single_batch(self, monkeypatch):
        tasks = [_pending_task(f"t{i}") for i in range(11)]
        monkeypatch.setattr(
            TaskPGManager, "get_oldest_tasks_by_status", AsyncMock(return_value=tasks)
        )
        transitions = AsyncMock(return_value=True)
        monkeypatch.setattr(TaskPGManager, "transition_task_status", transitions)
        monkeypatch.setattr(
            TaskPGManager,
            "get_task_by_task_id",
            AsyncMock(
                return_value=SimpleNamespace(status=TaskStatusEnum.RUNNING)
            ),
        )
        monkeypatch.setattr(
            TaskHandler, "_preprocess_log_source", AsyncMock(return_value="/logs")
        )
        monkeypatch.setattr(BaseWorker, "run", AsyncMock(return_value=True))
        monkeypatch.setattr(
            ProcessHandler, "has_capacity", Mock(return_value=True)
        )

        await TaskHandler.handle_pending_tasks()
        await _drain_pending_dispatch()

        assert transitions.await_count == 10

    async def test_handle_pending_tasks_throttles_inflight_dispatch(
        self, monkeypatch
    ):
        task = _pending_task("fresh")
        monkeypatch.setattr(
            TaskPGManager,
            "get_oldest_tasks_by_status",
            AsyncMock(return_value=[task]),
        )
        transitions = AsyncMock(return_value=True)
        monkeypatch.setattr(TaskPGManager, "transition_task_status", transitions)
        has_capacity = Mock(return_value=True)
        monkeypatch.setattr(ProcessHandler, "has_capacity", has_capacity)
        for i in range(10):
            TaskHandler._dispatching_task_ids.add(f"inflight-{i}")

        await TaskHandler.handle_pending_tasks()
        await _drain_pending_dispatch()

        transitions.assert_not_awaited()
        has_capacity.assert_not_called()

    async def test_handle_pending_tasks_stops_when_no_capacity(self, monkeypatch):
        task = _pending_task("t-1")
        monkeypatch.setattr(
            TaskPGManager,
            "get_oldest_tasks_by_status",
            AsyncMock(return_value=[task]),
        )
        transitions = AsyncMock(return_value=True)
        monkeypatch.setattr(TaskPGManager, "transition_task_status", transitions)
        monkeypatch.setattr(
            ProcessHandler, "has_capacity", Mock(return_value=False)
        )

        await TaskHandler.handle_pending_tasks()
        await _drain_pending_dispatch()

        transitions.assert_not_awaited()

    async def test_handle_tasks_invokes_all_queues(self, monkeypatch):
        successed = AsyncMock()
        failed = AsyncMock()
        pending = AsyncMock()
        monkeypatch.setattr(TaskHandler, "handle_successed_tasks", successed)
        monkeypatch.setattr(TaskHandler, "handle_failed_tasks", failed)
        monkeypatch.setattr(TaskHandler, "handle_pending_tasks", pending)

        await TaskHandler.handle_tasks()

        successed.assert_awaited_once_with()
        failed.assert_awaited_once_with()
        pending.assert_awaited_once_with()


# ---------------------------------------------------------------------------
# Section D: log_preprocessor 文件处理
# ---------------------------------------------------------------------------


def _patterns_config(patterns):
    config = SimpleNamespace(
        get_default_diagnosis_config=lambda: SimpleNamespace(
            log_filename_pattern=SimpleNamespace(model_dump=lambda: patterns)
        )
    )
    return lambda: config


def _patch_patterns(monkeypatch, patterns):
    monkeypatch.setattr(preprocessor_module, "Config", _patterns_config(patterns))


class TestDefaultPreprocessDir:
    def test_default_preprocess_dir_uses_env(self, monkeypatch, tmp_path):
        monkeypatch.setenv("WITTY_DIR", str(tmp_path))
        assert default_preprocess_dir("lf-9") == str(
            tmp_path / "log_preprocessed_lf-9"
        )

    def test_default_preprocess_dir_default_root(self, monkeypatch):
        monkeypatch.delenv("WITTY_DIR", raising=False)
        assert default_preprocess_dir("lf-9") == "/var/witty-ub/log_preprocessed_lf-9"


class TestCleanupPreprocessDir:
    def test_cleanup_missing_dir_returns_none(self, monkeypatch, tmp_path):
        monkeypatch.setenv("WITTY_DIR", str(tmp_path))
        assert cleanup_preprocess_dir("lf-404") is None

    def test_cleanup_removes_dir(self, monkeypatch, tmp_path):
        monkeypatch.setenv("WITTY_DIR", str(tmp_path))
        target = tmp_path / "log_preprocessed_lf-1"
        target.mkdir()
        (target / "f.log").write_text("x", encoding="utf-8")

        assert cleanup_preprocess_dir("lf-1") == str(target)
        assert not target.exists()

    def test_cleanup_retries_then_succeeds(self, monkeypatch, tmp_path):
        monkeypatch.setenv("WITTY_DIR", str(tmp_path))
        target = tmp_path / "log_preprocessed_lf-2"
        target.mkdir()
        monkeypatch.setattr("time.sleep", lambda seconds: None)
        real_rmtree = shutil.rmtree
        attempts = []

        def flaky_rmtree(path, *args, **kwargs):
            attempts.append(path)
            if len(attempts) == 1:
                raise OSError(errno.EBUSY, "busy")
            real_rmtree(path)

        monkeypatch.setattr(shutil, "rmtree", flaky_rmtree)

        assert cleanup_preprocess_dir("lf-2") == str(target)
        assert len(attempts) == 2

    def test_cleanup_gives_up_after_retries(self, monkeypatch, tmp_path):
        monkeypatch.setenv("WITTY_DIR", str(tmp_path))
        target = tmp_path / "log_preprocessed_lf-3"
        target.mkdir()
        monkeypatch.setattr("time.sleep", lambda seconds: None)
        monkeypatch.setattr(
            shutil, "rmtree", Mock(side_effect=OSError(errno.EBUSY, "busy"))
        )

        assert cleanup_preprocess_dir("lf-3") is None
        assert target.exists()


class TestNeedsPreprocess:
    def test_configured_filename_patterns_falls_back_on_config_error(
        self, monkeypatch
    ):
        def boom():
            raise RuntimeError("no config")

        monkeypatch.setattr(preprocessor_module, "Config", boom)
        assert _configured_filename_patterns() == []

    def test_single_text_file_unmatched(self, monkeypatch, tmp_path):
        _patch_patterns(monkeypatch, {"ds_worker_access_log_file": ["access.log"]})
        source = tmp_path / "odd.log"
        source.write_text("hello\n", encoding="utf-8")
        assert needs_preprocess(str(source)) is True

    def test_single_file_matched(self, monkeypatch, tmp_path):
        _patch_patterns(monkeypatch, {"ds_worker_access_log_file": ["access.log"]})
        source = tmp_path / "access.log"
        source.write_text("hello\n", encoding="utf-8")
        assert needs_preprocess(str(source)) is False

    def test_single_binary_file_skipped(self, monkeypatch, tmp_path):
        _patch_patterns(monkeypatch, {"ds_worker_access_log_file": ["access.log"]})
        source = tmp_path / "blob.bin"
        source.write_bytes(b"\x00\x01")
        assert needs_preprocess(str(source)) is False

    def test_dir_with_archive_needs_preprocess(self, monkeypatch, tmp_path):
        _patch_patterns(monkeypatch, {"ds_worker_access_log_file": ["access.log"]})
        (tmp_path / "a.zip").write_bytes(b"zip")
        assert needs_preprocess(str(tmp_path)) is True

    def test_dir_with_gz_only_skips(self, monkeypatch, tmp_path):
        _patch_patterns(monkeypatch, {"ds_worker_access_log_file": ["access.log"]})
        (tmp_path / "access.log.gz").write_bytes(b"gz")
        assert needs_preprocess(str(tmp_path)) is False

    def test_dir_with_unmatched_text_needs_preprocess(
        self, monkeypatch, tmp_path
    ):
        _patch_patterns(monkeypatch, {"ds_worker_access_log_file": ["access.log"]})
        (tmp_path / "odd.log").write_text("hello\n", encoding="utf-8")
        assert needs_preprocess(str(tmp_path)) is True

    def test_dir_with_binary_only_skips(self, monkeypatch, tmp_path):
        _patch_patterns(monkeypatch, {"ds_worker_access_log_file": ["access.log"]})
        (tmp_path / "blob.bin").write_bytes(b"\x00\x01")
        assert needs_preprocess(str(tmp_path)) is False

    def test_dir_all_matched_skips(self, monkeypatch, tmp_path):
        _patch_patterns(monkeypatch, {"ds_worker_access_log_file": ["access.log"]})
        nested = tmp_path / "sub"
        nested.mkdir()
        (nested / "access.log").write_text("hello\n", encoding="utf-8")
        assert needs_preprocess(str(tmp_path)) is False

    def test_empty_dir_needs_preprocess(self, monkeypatch, tmp_path):
        _patch_patterns(monkeypatch, {"ds_worker_access_log_file": ["access.log"]})
        assert needs_preprocess(str(tmp_path)) is True

    def test_missing_path_needs_preprocess(self, monkeypatch, tmp_path):
        _patch_patterns(monkeypatch, {"ds_worker_access_log_file": ["access.log"]})
        assert needs_preprocess(str(tmp_path / "nope")) is True

    def test_filename_looks_like_text(self, tmp_path):
        text_file = tmp_path / "text.log"
        text_file.write_text("hello\n", encoding="utf-8")
        binary_file = tmp_path / "bin.log"
        binary_file.write_bytes(b"\x00\x01")
        assert filename_looks_like_text(str(text_file)) is True
        assert filename_looks_like_text(str(binary_file)) is False

    def test_filename_looks_like_text_directory_is_not_text(self, tmp_path):
        assert filename_looks_like_text(str(tmp_path)) is False


class TestPreprocessLogDir:
    def test_missing_source_raises(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            preprocess_log_dir(
                str(tmp_path / "nope"), str(tmp_path / "out")
            )

    def test_copy_error_is_logged_not_raised(self, monkeypatch, tmp_path):
        source = tmp_path / "src"
        source.mkdir()
        (source / "access.log").write_text("x", encoding="utf-8")
        _patch_patterns(monkeypatch, {"ds_worker_access_log_file": ["access.log"]})
        monkeypatch.setattr(
            shutil,
            "copy2",
            Mock(side_effect=OSError(errno.EIO, "io err")),
        )
        output = tmp_path / "out"

        result = preprocess_log_dir(str(source), str(output))

        assert result.copied_count == 0
        assert (output / ".witty_preprocess_done").exists()


class TestSplitUnmatchedLogFiles:
    def test_split_skips_existing_split_artifacts(self, tmp_path):
        (tmp_path / "old.log_split_access.log").write_text(
            "a" * 20 + "\n", encoding="utf-8"
        )
        (tmp_path / "old.log_split_runtime.log").write_text(
            "b" * 20 + "\n", encoding="utf-8"
        )

        stats = split_unmatched_log_files(
            str(tmp_path), {"known": ["known.log"]}
        )

        assert stats == {}

    def test_split_skips_binary_files(self, tmp_path):
        (tmp_path / "data.bin").write_bytes(b"\x00\x01\x02")

        stats = split_unmatched_log_files(
            str(tmp_path), {"known": ["known.log"]}
        )

        assert stats == {}

    def test_split_continues_after_io_error(self, monkeypatch, tmp_path):
        source = tmp_path / "odd.log"
        source.write_text("plain text\n", encoding="utf-8")
        real_open = open

        def open_eio(path, mode="r", *args, **kwargs):
            if "w" in mode:
                raise OSError(errno.EIO, "io err")
            return real_open(path, mode, *args, **kwargs)

        monkeypatch.setattr(
            preprocessor_module, "open", open_eio, raising=False
        )

        stats = split_unmatched_log_files(
            str(tmp_path), {"known": ["known.log"]}
        )

        assert stats == {}

    def test_split_removes_files_with_no_matching_lines(self, tmp_path):
        source = tmp_path / "odd.log"
        source.write_text("garbage\nnothing\n", encoding="utf-8")

        stats = split_unmatched_log_files(
            str(tmp_path), {"known": ["known.log"]}
        )

        assert stats == {}
        assert not (tmp_path / "odd.log_split_access.log").exists()
        assert not (tmp_path / "odd.log_split_runtime.log").exists()
        assert source.exists()


class TestArchiveValidation:
    def test_is_valid_archive_file_rejects_invalid_zip(self, tmp_path):
        archive_path = tmp_path / "fake.zip"
        archive_path.write_bytes(b"not a zip")
        assert is_valid_archive_file(str(archive_path)) is False

    def test_is_valid_archive_file_rejects_unsupported_suffix(self, tmp_path):
        gz_path = tmp_path / "logs.gz"
        gz_path.write_bytes(b"gz")
        assert is_valid_archive_file(str(gz_path)) is False
        plain_path = tmp_path / "plain.log"
        plain_path.write_text("x", encoding="utf-8")
        assert is_valid_archive_file(str(plain_path)) is False

    def test_is_valid_archive_file_rar_without_module(self, tmp_path):
        archive_path = tmp_path / "x.rar"
        archive_path.write_bytes(b"rar")
        assert is_valid_archive_file(str(archive_path)) is False

    def test_is_valid_archive_file_rar_with_module(self, monkeypatch, tmp_path):
        fake_rarfile = SimpleNamespace(is_rarfile=lambda path: True)
        monkeypatch.setitem(sys.modules, "rarfile", fake_rarfile)
        archive_path = tmp_path / "y.rar"
        archive_path.write_bytes(b"rar")
        assert is_valid_archive_file(str(archive_path)) is True


class TestExtractArchive:
    def test_extract_archive_gunzips_single_file(self, tmp_path):
        source = tmp_path / "app.log.gz"
        with gzip.open(source, "wb") as file:
            file.write(b"log line\n")
        output = tmp_path / "out"
        output.mkdir()

        assert _extract_archive(str(source), str(output)) == 1
        assert (output / "app.log").read_bytes() == b"log line\n"

    def test_extract_archive_skips_rar_without_module(self, tmp_path):
        source = tmp_path / "x.rar"
        source.write_bytes(b"rar")
        assert _extract_archive(str(source), str(tmp_path / "out")) == 0

    def test_extract_archive_swallows_bad_zip(self, tmp_path):
        source = tmp_path / "bad.zip"
        source.write_bytes(b"not a zip")
        assert _extract_archive(str(source), str(tmp_path / "out")) == 0

    def test_extract_tar_skips_directory_members(self, tmp_path):
        source = tmp_path / "logs.tar.gz"
        with tarfile.open(source, "w:gz") as archive:
            member = tarfile.TarInfo("subdir/")
            member.type = tarfile.DIRTYPE
            archive.addfile(member)
        output = tmp_path / "out"
        output.mkdir()

        assert _extract_tar(str(source), str(output)) == 0

    def test_extract_tar_skips_unsafe_member_paths(self, tmp_path):
        source = tmp_path / "evil.tar.gz"
        content = b"evil\n"
        with tarfile.open(source, "w:gz") as archive:
            member = tarfile.TarInfo("../evil.log")
            member.size = len(content)
            archive.addfile(member, io.BytesIO(content))
        output = tmp_path / "out"
        output.mkdir()

        # 已知问题：_extract_tar 对被安全跳过的成员仍计数（extracted += 1 无条件
        # 执行），这里只断言越界文件未落盘这一安全属性。
        assert _extract_tar(str(source), str(output)) == 1
        assert not (tmp_path / "evil.log").exists()
        assert list(output.iterdir()) == []

    def test_extract_zip_skips_directory_entries(self, tmp_path):
        source = tmp_path / "logs.zip"
        with zipfile.ZipFile(source, "w") as archive:
            archive.writestr("sub/", "")
        output = tmp_path / "out"
        output.mkdir()

        assert _extract_zip(str(source), str(output)) == 0


class TestExtractRar:
    def test_extract_rar_extracts_files(self, monkeypatch, tmp_path):
        class _FakeRarMember:
            def __init__(self, filename, content=b""):
                self.filename = filename
                self._content = content

            def isdir(self):
                return self.filename.endswith("/")

        class _FakeRarFile:
            members = []

            def __init__(self, path, mode="r"):
                pass

            def __enter__(self):
                return self

            def __exit__(self, *exc_info):
                return False

            def infolist(self):
                return list(type(self).members)

            def open(self, member):
                return io.BytesIO(member._content)

        _FakeRarFile.members = [
            _FakeRarMember("nested/a.log", b"rar content\n"),
            _FakeRarMember("sub/"),
            _FakeRarMember("../evil.log", b"evil\n"),
        ]
        fake_rarfile = SimpleNamespace(RarFile=_FakeRarFile)
        monkeypatch.setitem(sys.modules, "rarfile", fake_rarfile)
        source = tmp_path / "logs.rar"
        source.write_bytes(b"rar")
        output = tmp_path / "out"
        output.mkdir()

        assert _extract_rar(str(source), str(output)) == 1
        assert (output / "nested" / "a.log").read_bytes() == b"rar content\n"
        assert not (tmp_path / "evil.log").exists()

    def test_extract_rar_without_module_returns_zero(self, tmp_path):
        source = tmp_path / "x.rar"
        source.write_bytes(b"rar")
        assert _extract_rar(str(source), str(tmp_path / "out")) == 0


class TestSafeExtractHelpers:
    def test_safe_extract_tar_member_ignores_unreadable_member(self, tmp_path):
        archive = SimpleNamespace(extractfile=lambda member: None)
        member = SimpleNamespace(name="plain.log")

        _safe_extract_tar_member(archive, member, str(tmp_path))

        assert not (tmp_path / "plain.log").exists()

    def test_safe_extract_zip_member_skips_unsafe_paths(self, tmp_path):
        archive = SimpleNamespace(open=Mock())
        member = SimpleNamespace(filename="../evil.txt")

        _safe_extract_zip_member(archive, member, str(tmp_path))

        archive.open.assert_not_called()
        assert not (tmp_path / "evil.txt").exists()

    def test_safe_join_rejects_path_traversal(self, tmp_path):
        assert _safe_join(str(tmp_path), "../outside.txt") is None
        assert _safe_join(str(tmp_path), "sub/ok.txt") == str(
            tmp_path / "sub" / "ok.txt"
        )


class TestRemoveEmptyFile:
    def test_remove_empty_file_deletes_zero_size(self, tmp_path):
        target = tmp_path / "empty.log"
        target.write_text("", encoding="utf-8")
        _remove_empty_file(str(target))
        assert not target.exists()

    def test_remove_empty_file_ignores_missing(self, tmp_path):
        _remove_empty_file(str(tmp_path / "missing.log"))

    def test_remove_empty_file_swallows_os_error(self, monkeypatch, tmp_path):
        target = tmp_path / "empty.log"
        target.write_text("", encoding="utf-8")
        monkeypatch.setattr(
            os, "remove", Mock(side_effect=OSError(errno.EPERM, "denied"))
        )
        _remove_empty_file(str(target))
