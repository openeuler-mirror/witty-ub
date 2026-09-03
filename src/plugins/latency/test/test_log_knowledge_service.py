from unittest.mock import AsyncMock

import pytest

from latency.database.managers.diagnosis_config import DiagnosisConfigPGManager
from latency.database.managers.log_knowledge import LogKnowledgePGManager
from latency.exceptions import ConflictBizException
from latency.schemas.request import CreateLogKnowledgeRequest
from latency.services.log_knowledge import LogKnowledgeService


@pytest.mark.asyncio
async def test_create_log_kb_rejects_duplicate_active_name(monkeypatch):
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
async def test_create_log_kb_initializes_config_after_unique_insert(monkeypatch):
    add_log_kb = AsyncMock(return_value="kb-id")
    reset_config = AsyncMock()
    monkeypatch.setattr(LogKnowledgePGManager, "add_log_kb", add_log_kb)
    monkeypatch.setattr(DiagnosisConfigPGManager, "reset", reset_config)

    result = await LogKnowledgeService.create_log_kb(
        CreateLogKnowledgeRequest(name=" 唯一名称 ", description="测试")
    )

    assert result.kb_id == "kb-id"
    assert add_log_kb.await_args.args[0].name == "唯一名称"
    reset_config.assert_awaited_once_with("kb-id")
