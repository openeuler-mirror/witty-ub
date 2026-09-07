from unittest.mock import AsyncMock, MagicMock

from latency.database.engine import PGManager

import pytest

from latency.database.managers.diagnosis_config import DiagnosisConfigPGManager
from latency.database.managers.log_knowledge import LogKnowledgePGManager
from latency.exceptions import ConflictBizException
from latency.schemas.request import CreateLogKnowledgeRequest
from latency.services.log_knowledge import LogKnowledgeService


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
