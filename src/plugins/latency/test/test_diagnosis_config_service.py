from unittest.mock import AsyncMock

import pytest

from latency.database.managers.diagnosis_config import DiagnosisConfigPGManager
from latency.database.managers.log_knowledge import LogKnowledgePGManager
from latency.exceptions import NotFoundBizException
from latency.schemas.config import DiagnosisRuntimeConfig
from latency.services.diagnosis_config import DiagnosisConfigService


def _config() -> DiagnosisRuntimeConfig:
    return DiagnosisRuntimeConfig(
        log_filename_pattern={
            "ds_client_access_log_file": ["*.log"],
            "ds_client_info_log_file": ["*.log"],
            "ds_worker_access_log_file": ["*.log"],
            "ds_worker_info_log_file": ["*.log"],
            "resource_log_file": ["*.log"],
        },
        log_analyzer_params={},
    )


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("operation", "manager_method"),
    [
        (lambda config: DiagnosisConfigService.get("missing-kb"), "get_or_create"),
        (
            lambda config: DiagnosisConfigService.update("missing-kb", config),
            "upsert",
        ),
        (lambda config: DiagnosisConfigService.reset("missing-kb"), "reset"),
    ],
)
async def test_operations_reject_nonexistent_kb(
    monkeypatch, operation, manager_method
):
    kb_exists = AsyncMock(return_value=False)
    config_operation = AsyncMock()
    monkeypatch.setattr(LogKnowledgePGManager, "exists", kb_exists)
    monkeypatch.setattr(DiagnosisConfigPGManager, manager_method, config_operation)

    with pytest.raises(NotFoundBizException, match="知识库不存在"):
        await operation(_config())

    kb_exists.assert_awaited_once_with("missing-kb")
    config_operation.assert_not_awaited()


@pytest.mark.asyncio
async def test_get_existing_kb_initializes_missing_config(monkeypatch):
    config = _config()
    kb_exists = AsyncMock(return_value=True)
    get_or_create = AsyncMock(return_value=config)
    monkeypatch.setattr(LogKnowledgePGManager, "exists", kb_exists)
    monkeypatch.setattr(DiagnosisConfigPGManager, "get_or_create", get_or_create)

    result = await DiagnosisConfigService.get("existing-kb")

    assert result is config
    kb_exists.assert_awaited_once_with("existing-kb")
    get_or_create.assert_awaited_once_with("existing-kb")
