from unittest.mock import AsyncMock
from types import SimpleNamespace
import errno

import pytest

from latency.database.managers.task import TaskPGManager
from latency.ENUM.task import TaskTypeEnum
from latency.schemas.request import ParseConfig
from latency.task.task_handler import TaskHandler
from latency.task.worker.base import BaseWorker


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
    task = SimpleNamespace(
        id="task-id",
        op_id="log-id",
        task_type=TaskTypeEnum.KV_CACHE_LOG_PARSE_WORKER,
        task_config=None,
    )
    monkeypatch.setattr(
        TaskPGManager,
        "get_oldest_tasks_by_status",
        AsyncMock(return_value=[task]),
    )
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

    assert cleanup_calls == ["log-id"]
    mark_failed.assert_awaited_once_with(
        "task-id",
        "任务失败：服务器磁盘空间不足，请清理空间后重新提交",
    )


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
    monkeypatch.setattr(
        TaskHandler,
        "_preprocess_log_source",
        AsyncMock(return_value="/logs"),
    )
    run = AsyncMock(return_value=True)
    monkeypatch.setattr(BaseWorker, "run", run)

    await TaskHandler.handle_pending_tasks()

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
    monkeypatch.setattr(
        TaskHandler,
        "_preprocess_log_source",
        AsyncMock(return_value="/logs"),
    )
    run = AsyncMock(return_value=True)
    monkeypatch.setattr(BaseWorker, "run", run)

    await TaskHandler.handle_pending_tasks()

    run.assert_awaited_once_with(
        "brpc-task",
        log_dir="/logs",
        worker_kwargs={"start_time": "2026-08-11 10:20:30"},
    )
