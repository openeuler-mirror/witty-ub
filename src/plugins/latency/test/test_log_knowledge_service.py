from unittest.mock import AsyncMock, MagicMock

from latency.database.engine import PGManager

import pytest

from latency.database.managers.diagnosis_config import DiagnosisConfigPGManager
from latency.database.managers.log_knowledge import LogKnowledgePGManager
from latency.database.managers.log_file import LogFilePGManager
from latency.database.managers.task import TaskPGManager
from latency.exceptions import ConflictBizException
from latency.schemas.request import CreateLogKnowledgeRequest
from latency.services.log_knowledge import LogKnowledgeService
from latency.task.worker.base import BaseWorker


@pytest.fixture
def transaction_session(monkeypatch):
    session = AsyncMock()
    session.__aenter__.return_value = session
    monkeypatch.setattr(PGManager, "_session_maker", MagicMock(return_value=session))
    return session


@pytest.mark.asyncio
async def test_create_log_kb_rejects_duplicate_active_name(monkeypatch, transaction_session):
    add_log_kb = AsyncMock(return_value=None)
    reset_config = AsyncMock()
    monkeypatch.setattr(LogKnowledgePGManager, "add_log_kb", add_log_kb)
    monkeypatch.setattr(DiagnosisConfigPGManager, "reset", reset_config)

    with pytest.raises(ConflictBizException, match="资产库名称已存在"):
        await LogKnowledgeService.create_log_kb(
            CreateLogKnowledgeRequest(name="重复名称", description="测试")
        )

    add_log_kb.assert_awaited_once()
    reset_config.assert_not_awaited()


@pytest.mark.asyncio
async def test_create_log_kb_initializes_config_after_unique_insert(monkeypatch, transaction_session):
    add_log_kb = AsyncMock(return_value="kb-id")
    reset_config = AsyncMock()
    monkeypatch.setattr(LogKnowledgePGManager, "add_log_kb", add_log_kb)
    monkeypatch.setattr(DiagnosisConfigPGManager, "reset", reset_config)

    result = await LogKnowledgeService.create_log_kb(
        CreateLogKnowledgeRequest(name=" 唯一名称 ", description="测试")
    )

    assert result.kb_id == "kb-id"
    assert add_log_kb.await_args.args[0].name == "唯一名称"
    reset_config.assert_awaited_once_with("kb-id", session=transaction_session)
    transaction_session.commit.assert_awaited_once()
    transaction_session.rollback.assert_not_awaited()


@pytest.mark.asyncio
async def test_config_write_failure_rolls_back_creation(monkeypatch, transaction_session):
    # Exercise both real managers and the real transaction context. Fail only
    # when the config INSERT follows the asset INSERT.
    from latency.schemas.config import DiagnosisRuntimeConfig

    monkeypatch.setattr(
        DiagnosisConfigPGManager, "get_default_config", lambda: DiagnosisRuntimeConfig(
            log_filename_pattern={
                field: ["test.log"] for field in (
                    "ds_client_access_log_file", "ds_client_info_log_file",
                    "ds_worker_access_log_file", "ds_worker_info_log_file",
                    "resource_log_file",
                )
            }, log_analyzer_params={}
        )
    )
    transaction_session.scalar.return_value = None
    writes = []

    async def execute(statement, *args, **kwargs):
        table = getattr(statement, "table", None)
        if table is not None:
            writes.append(table.name)
            if table.name == "diagnosis_config":
                raise OSError(28, "No space left on device")
        return MagicMock()

    transaction_session.execute.side_effect = execute
    with pytest.raises(OSError, match="No space left on device"):
        await LogKnowledgeService.create_log_kb(
            CreateLogKnowledgeRequest(name="full_test", description="磁盘满")
        )
    assert writes == ["log_knowledge", "diagnosis_config"]
    transaction_session.commit.assert_not_awaited()
    transaction_session.rollback.assert_awaited_once()


@pytest.mark.asyncio
async def test_commit_failure_does_not_return_success(monkeypatch, transaction_session):
    monkeypatch.setattr(LogKnowledgePGManager, "add_log_kb", AsyncMock(return_value="kb-id"))
    monkeypatch.setattr(DiagnosisConfigPGManager, "reset", AsyncMock())
    transaction_session.commit.side_effect = OSError(28, "No space left on device")

    with pytest.raises(OSError, match="No space left on device"):
        await LogKnowledgeService.create_log_kb(
            CreateLogKnowledgeRequest(name="full_test", description="磁盘满")
        )
    transaction_session.rollback.assert_awaited_once()


@pytest.mark.asyncio
async def test_delete_kb_cascades_logs_tasks_and_asset_after_stopping_workers(
    monkeypatch,
):
    actions = []
    tasks = [MagicMock(id="task-1"), MagicMock(id="task-2")]

    async def stop_task(task_id):
        actions.append(("stop", task_id))
        return True

    async def delete_log(log_id):
        actions.append(("delete-log", log_id))
        return True

    monkeypatch.setattr(
        LogKnowledgePGManager,
        "get_log_kb_by_kb_id",
        AsyncMock(return_value=MagicMock(id="kb-id")),
    )
    monkeypatch.setattr(
        TaskPGManager, "list_tasks_by_kb_id", AsyncMock(return_value=tasks)
    )
    monkeypatch.setattr(BaseWorker, "stop", stop_task)
    monkeypatch.setattr(
        LogFilePGManager, "list_log_file_ids", AsyncMock(return_value=["log-1", "log-2"])
    )
    monkeypatch.setattr(
        LogFilePGManager, "hard_delete_log_file_with_related_data", delete_log
    )
    delete_tasks = AsyncMock()
    monkeypatch.setattr(TaskPGManager, "hard_delete_tasks_by_kb_id", delete_tasks)
    delete_config = AsyncMock()
    monkeypatch.setattr(DiagnosisConfigPGManager, "delete", delete_config)
    delete_kb = AsyncMock(return_value=True)
    monkeypatch.setattr(LogKnowledgePGManager, "delete_log_kb_by_kb_id", delete_kb)

    result = await LogKnowledgeService.delete_log_kb_by_kb_id("kb-id")

    assert result.kb_id == "kb-id"
    assert actions == [
        ("stop", "task-1"),
        ("stop", "task-2"),
        ("delete-log", "log-1"),
        ("delete-log", "log-2"),
    ]
    LogFilePGManager.list_log_file_ids.assert_awaited_once_with(
        kb_id="kb-id", include_inactive=True
    )
    delete_tasks.assert_awaited_once_with("kb-id")
    delete_config.assert_awaited_once_with("kb-id")
    delete_kb.assert_awaited_once_with("kb-id")


@pytest.mark.asyncio
async def test_delete_kb_aborts_cascade_when_a_worker_cannot_stop(monkeypatch):
    monkeypatch.setattr(
        LogKnowledgePGManager,
        "get_log_kb_by_kb_id",
        AsyncMock(return_value=MagicMock(id="kb-id")),
    )
    monkeypatch.setattr(
        TaskPGManager,
        "list_tasks_by_kb_id",
        AsyncMock(return_value=[MagicMock(id="task-running")]),
    )
    monkeypatch.setattr(BaseWorker, "stop", AsyncMock(return_value=False))
    delete_logs = AsyncMock()
    monkeypatch.setattr(LogFilePGManager, "list_log_file_ids", delete_logs)

    with pytest.raises(RuntimeError, match="取消删除"):
        await LogKnowledgeService.delete_log_kb_by_kb_id("kb-id")

    delete_logs.assert_not_awaited()
