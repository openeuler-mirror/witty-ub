from unittest.mock import AsyncMock, call
from types import SimpleNamespace
import asyncio
import errno

import pytest

from latency.database.managers.task import TaskPGManager
from latency.ENUM.task import TaskStatusEnum, TaskTypeEnum
from latency.schemas.request import ParseConfig
from latency.task.task_handler import TaskHandler
from latency.task.worker.base import BaseWorker


@pytest.fixture(autouse=True)
def _reset_dispatch_state():
    TaskHandler._dispatching_task_ids.clear()
    TaskHandler._preprocess_inflight.clear()
    yield
    TaskHandler._dispatching_task_ids.clear()
    TaskHandler._preprocess_inflight.clear()


async def _drain_pending_dispatch():
    """handle_pending_tasks 后台派发：等待本轮派发协程全部结束。"""
    dispatch_tasks = list(TaskHandler._dispatch_tasks)
    if dispatch_tasks:
        await asyncio.gather(*dispatch_tasks)


def _make_task(**overrides):
    task = SimpleNamespace(
        id="task-id",
        op_id="log-id",
        task_type=TaskTypeEnum.KV_CACHE_LOG_PARSE_WORKER,
        task_config=None,
    )
    task.__dict__.update(overrides)
    return task


def _mock_dispatch_claim(monkeypatch, claimed=True, running_status=None):
    """派发协程依赖的状态迁移/回查 mock。"""
    transitions = AsyncMock(return_value=claimed)
    monkeypatch.setattr(
        TaskPGManager,
        "transition_task_status",
        transitions,
    )
    if running_status is None:
        running_status = TaskStatusEnum.RUNNING
    monkeypatch.setattr(
        TaskPGManager,
        "get_task_by_task_id",
        AsyncMock(return_value=SimpleNamespace(status=running_status)),
    )
    return transitions


@pytest.mark.asyncio
async def test_init_task_queue_routes_interrupted_tasks_through_retry(monkeypatch):
    recover = AsyncMock(return_value=True)
    monkeypatch.setattr(
        TaskPGManager,
        "mark_interrupted_running_tasks_for_retry",
        recover,
    )

    await TaskHandler.init_task_queue()

    recover.assert_awaited_once_with()


@pytest.mark.asyncio
async def test_init_task_persists_parse_config(monkeypatch):
    monkeypatch.setattr(BaseWorker, "init", AsyncMock(return_value="task-id"))
    update = AsyncMock(return_value=True)
    monkeypatch.setattr(TaskPGManager, "update_task", update)

    await TaskHandler.init_task(
        TaskTypeEnum.KV_CACHE_LOG_PARSE_WORKER,
        "log-id",
        ParseConfig(
            start_time="2026-08-11 10:20:30",
            end_time="2026-08-11 11:20:30",
            min_elapsed_ms=20,
        ),
    )

    update.assert_awaited_once_with(
        "task-id",
        {
            "task_config": {
                "start_time": "2026-08-11 10:20:30",
                "end_time": "2026-08-11 11:20:30",
                "min_elapsed_ms": 20,
            }
        },
    )


@pytest.mark.asyncio
async def test_init_task_propagates_initialization_failure(monkeypatch):
    failure = RuntimeError("database unavailable")
    monkeypatch.setattr(BaseWorker, "init", AsyncMock(side_effect=failure))

    with pytest.raises(RuntimeError, match="database unavailable"):
        await TaskHandler.init_task(
            TaskTypeEnum.KV_CACHE_LOG_PARSE_WORKER,
            "log-id",
        )


@pytest.mark.asyncio
async def test_disk_full_during_preprocess_marks_task_failed(monkeypatch):
    task = _make_task()
    monkeypatch.setattr(
        TaskPGManager,
        "get_oldest_tasks_by_status",
        AsyncMock(return_value=[task]),
    )
    _mock_dispatch_claim(monkeypatch)
    monkeypatch.setattr(
        TaskHandler,
        "_preprocess_log_source",
        AsyncMock(side_effect=OSError(errno.ENOSPC, "No space left on device")),
    )
    mark_failed = AsyncMock(return_value=True)
    monkeypatch.setattr(TaskPGManager, "mark_failed_with_report", mark_failed)

    from latency.task import log_preprocessor

    cleanup_calls = []
    monkeypatch.setattr(
        log_preprocessor,
        "cleanup_preprocess_dir",
        lambda log_id: cleanup_calls.append(log_id),
    )

    await TaskHandler.handle_pending_tasks()
    await _drain_pending_dispatch()

    assert cleanup_calls == ["log-id"]
    mark_failed.assert_awaited_once_with(
        "task-id",
        "任务失败：服务器磁盘空间不足，请清理空间后重新提交",
    )


@pytest.mark.asyncio
async def test_preprocess_failure_marks_task_for_retry(monkeypatch):
    task = _make_task()
    monkeypatch.setattr(
        TaskPGManager,
        "get_oldest_tasks_by_status",
        AsyncMock(return_value=[task]),
    )
    _mock_dispatch_claim(monkeypatch)
    monkeypatch.setattr(
        TaskHandler,
        "_preprocess_log_source",
        AsyncMock(side_effect=FileNotFoundError("/data/logs.zip")),
    )
    mark_failed = AsyncMock(return_value=True)
    monkeypatch.setattr(TaskPGManager, "mark_failed_with_report", mark_failed)
    run = AsyncMock(return_value=True)
    monkeypatch.setattr(BaseWorker, "run", run)

    await TaskHandler.handle_pending_tasks()
    await _drain_pending_dispatch()

    run.assert_not_awaited()
    mark_failed.assert_awaited_once()
    args, kwargs = mark_failed.await_args
    assert args[0] == "task-id"
    assert args[1].startswith("任务失败：日志预处理或启动失败")
    assert kwargs["status"] == TaskStatusEnum.FAILED_PENDING_REMOVE


@pytest.mark.asyncio
async def test_dispatch_reverts_to_pending_when_worker_start_fails(monkeypatch):
    task = _make_task()
    monkeypatch.setattr(
        TaskPGManager,
        "get_oldest_tasks_by_status",
        AsyncMock(return_value=[task]),
    )
    transitions = _mock_dispatch_claim(monkeypatch)
    monkeypatch.setattr(
        TaskHandler,
        "_preprocess_log_source",
        AsyncMock(return_value="/logs"),
    )
    monkeypatch.setattr(BaseWorker, "run", AsyncMock(return_value=False))

    await TaskHandler.handle_pending_tasks()
    await _drain_pending_dispatch()

    assert transitions.await_args_list == [
        call("task-id", TaskStatusEnum.PENDING, TaskStatusEnum.RUNNING),
        call("task-id", TaskStatusEnum.RUNNING, TaskStatusEnum.PENDING),
    ]


@pytest.mark.asyncio
async def test_dispatch_skips_task_stopped_before_dispatch(monkeypatch):
    task = _make_task()
    monkeypatch.setattr(
        TaskPGManager,
        "get_oldest_tasks_by_status",
        AsyncMock(return_value=[task]),
    )
    _mock_dispatch_claim(monkeypatch, claimed=False)
    preprocess = AsyncMock(return_value="/logs")
    monkeypatch.setattr(TaskHandler, "_preprocess_log_source", preprocess)

    await TaskHandler.handle_pending_tasks()
    await _drain_pending_dispatch()

    preprocess.assert_not_awaited()


@pytest.mark.asyncio
async def test_dispatch_skips_task_cancelled_during_preprocess(monkeypatch):
    task = _make_task()
    monkeypatch.setattr(
        TaskPGManager,
        "get_oldest_tasks_by_status",
        AsyncMock(return_value=[task]),
    )
    _mock_dispatch_claim(
        monkeypatch,
        running_status=TaskStatusEnum.CANCELLED,
    )
    monkeypatch.setattr(
        TaskHandler,
        "_preprocess_log_source",
        AsyncMock(return_value="/logs"),
    )
    run = AsyncMock(return_value=True)
    monkeypatch.setattr(BaseWorker, "run", run)

    await TaskHandler.handle_pending_tasks()
    await _drain_pending_dispatch()

    run.assert_not_awaited()


@pytest.mark.asyncio
async def test_handle_pending_tasks_skips_dispatching_task(monkeypatch):
    task = _make_task()
    monkeypatch.setattr(
        TaskPGManager,
        "get_oldest_tasks_by_status",
        AsyncMock(return_value=[task]),
    )
    transitions = _mock_dispatch_claim(monkeypatch)
    TaskHandler._dispatching_task_ids.add("task-id")

    await TaskHandler.handle_pending_tasks()
    await _drain_pending_dispatch()

    transitions.assert_not_awaited()


@pytest.mark.asyncio
async def test_kv_cache_retry_uses_persisted_parse_config(monkeypatch):
    task = SimpleNamespace(
        id="kv-task",
        task_type=TaskTypeEnum.KV_CACHE_LOG_PARSE_WORKER,
        task_config={
            "start_time": "2026-08-11 10:20:30",
            "end_time": "2026-08-11 11:20:30",
            "min_elapsed_ms": 20,
        },
    )
    monkeypatch.setattr(
        TaskPGManager,
        "get_oldest_tasks_by_status",
        AsyncMock(return_value=[task]),
    )
    _mock_dispatch_claim(monkeypatch)
    monkeypatch.setattr(
        TaskHandler,
        "_preprocess_log_source",
        AsyncMock(return_value="/logs"),
    )
    run = AsyncMock(return_value=True)
    monkeypatch.setattr(BaseWorker, "run", run)

    await TaskHandler.handle_pending_tasks()
    await _drain_pending_dispatch()

    config = run.await_args.kwargs["worker_kwargs"]["parse_config"]
    assert config == ParseConfig(
        start_time="2026-08-11 10:20:30",
        end_time="2026-08-11 11:20:30",
        min_elapsed_ms=20,
    )


@pytest.mark.asyncio
async def test_brpc_retry_uses_persisted_start_time(monkeypatch):
    task = SimpleNamespace(
        id="brpc-task",
        task_type=TaskTypeEnum.BRPC_LOG_DIAGNOSIS_WORKER,
        task_config={
            "start_time": "2026-08-11 10:20:30",
            "end_time": None,
            "min_elapsed_ms": None,
        },
    )
    monkeypatch.setattr(
        TaskPGManager,
        "get_oldest_tasks_by_status",
        AsyncMock(return_value=[task]),
    )
    _mock_dispatch_claim(monkeypatch)
    monkeypatch.setattr(
        TaskHandler,
        "_preprocess_log_source",
        AsyncMock(return_value="/logs"),
    )
    run = AsyncMock(return_value=True)
    monkeypatch.setattr(BaseWorker, "run", run)

    await TaskHandler.handle_pending_tasks()
    await _drain_pending_dispatch()

    run.assert_awaited_once_with(
        "brpc-task",
        log_dir="/logs",
        worker_kwargs={"start_time": "2026-08-11 10:20:30"},
    )
