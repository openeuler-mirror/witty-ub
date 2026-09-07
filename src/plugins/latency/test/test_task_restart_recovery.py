from unittest.mock import AsyncMock
from types import SimpleNamespace

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
