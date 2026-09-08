import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from latency.task.worker.base import BaseWorker
from latency.task.worker.brpc_log_parse_worker import BrpcLogParseWorker
import latency.task.worker.brpc_log_parse_worker as worker_module


def _run(coroutine):
    return asyncio.run(coroutine)


def _configure_retry_limit(monkeypatch, retry_limit: int) -> None:
    config = SimpleNamespace(
        get_config=lambda: SimpleNamespace(
            task=SimpleNamespace(task_retry_times=retry_limit)
        )
    )
    monkeypatch.setattr(worker_module, "Config", lambda: config)


def test_reinit_retries_before_limit(monkeypatch):
    task = SimpleNamespace(id="task-id", op_id="log-id", retry_times=2)
    get_task = AsyncMock(return_value=task)
    delete_results = AsyncMock()
    report = AsyncMock()
    _configure_retry_limit(monkeypatch, retry_limit=3)
    monkeypatch.setattr(worker_module.TaskPGManager, "get_task_by_task_id", get_task)
    monkeypatch.setattr(
        worker_module.BrpcProfilingResultPGManager,
        "delete_by_log_id",
        delete_results,
    )
    monkeypatch.setattr(BaseWorker, "report", report)

    assert _run(BrpcLogParseWorker.reinit("task-id")) is True

    delete_results.assert_awaited_once_with("log-id")
    report.assert_awaited_once_with("task-id", "UBSocket task reinitialized", 0.0)


def test_reinit_stops_at_retry_limit(monkeypatch):
    task = SimpleNamespace(id="task-id", op_id="log-id", retry_times=3)
    get_task = AsyncMock(return_value=task)
    delete_results = AsyncMock()
    report = AsyncMock()
    _configure_retry_limit(monkeypatch, retry_limit=3)
    monkeypatch.setattr(worker_module.TaskPGManager, "get_task_by_task_id", get_task)
    monkeypatch.setattr(
        worker_module.BrpcProfilingResultPGManager,
        "delete_by_log_id",
        delete_results,
    )
    monkeypatch.setattr(BaseWorker, "report", report)

    assert _run(BrpcLogParseWorker.reinit("task-id")) is False

    delete_results.assert_not_awaited()
    report.assert_not_awaited()


def test_parse_log_fails_when_results_are_not_stored(monkeypatch, tmp_path):
    profiling_file = tmp_path / "ubsocket_profiling.txt"
    profiling_file.write_text("timeStamp: 2026-01-01T00:00:00\n", encoding="utf-8")
    record = SimpleNamespace()

    monkeypatch.setattr(
        worker_module.LogFilePGManager,
        "get_log_file_by_log_file_id",
        AsyncMock(return_value=SimpleNamespace(file_path=str(profiling_file))),
    )
    monkeypatch.setattr(
        worker_module,
        "BrpcProfilingParser",
        lambda: SimpleNamespace(parse_file=lambda path: [record]),
    )
    monkeypatch.setattr(
        worker_module.BrpcProfilingResultPGManager,
        "add_profiling_results",
        AsyncMock(return_value=False),
    )

    with pytest.raises(RuntimeError, match="Failed to store UBSocket profiling results"):
        _run(BrpcLogParseWorker.parse_log("log-id"))


def test_run_refreshes_asset_update_time_on_success(monkeypatch):
    task = SimpleNamespace(id="task-id", op_id="log-id", kb_id="kb-id")
    events = []
    get_task = AsyncMock(return_value=task)
    update_task = AsyncMock(
        side_effect=lambda task_id, values: events.append(
            ("update", values["status"])
        )
        or 1
    )
    report = AsyncMock(
        side_effect=lambda task_id, message, progress: events.append(
            ("report", progress)
        )
        or True
    )
    parse_log = AsyncMock(return_value=12)
    touch_log_kb = AsyncMock(return_value=1)

    monkeypatch.setattr(worker_module.TaskPGManager, "get_task_by_task_id", get_task)
    monkeypatch.setattr(worker_module.TaskPGManager, "update_task", update_task)
    monkeypatch.setattr(BaseWorker, "report", report)
    monkeypatch.setattr(BrpcLogParseWorker, "parse_log", parse_log)
    monkeypatch.setattr(
        worker_module.LogKnowledgePGManager,
        "touch_log_kb",
        touch_log_kb,
    )

    assert _run(BrpcLogParseWorker.run("task-id")) is True

    touch_log_kb.assert_awaited_once_with("kb-id")
    assert update_task.await_args_list[-1].args == (
        "task-id",
        {"status": "successful_pending_remove"},
    )
    assert events.index(("update", "successful_pending_remove")) < events.index(
        ("report", 100.0)
    )


def test_run_refreshes_asset_update_time_when_profiling_is_empty(monkeypatch):
    task = SimpleNamespace(id="task-id", op_id="log-id", kb_id="kb-id")
    update_task = AsyncMock(return_value=1)
    touch_log_kb = AsyncMock(return_value=1)

    monkeypatch.setattr(
        worker_module.TaskPGManager,
        "get_task_by_task_id",
        AsyncMock(return_value=task),
    )
    monkeypatch.setattr(worker_module.TaskPGManager, "update_task", update_task)
    monkeypatch.setattr(BaseWorker, "report", AsyncMock(return_value=True))
    monkeypatch.setattr(BrpcLogParseWorker, "parse_log", AsyncMock(return_value=0))
    monkeypatch.setattr(
        worker_module.LogKnowledgePGManager,
        "touch_log_kb",
        touch_log_kb,
    )

    assert _run(BrpcLogParseWorker.run("task-id")) is True

    touch_log_kb.assert_awaited_once_with("kb-id")
