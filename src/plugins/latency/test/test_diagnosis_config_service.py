from unittest.mock import AsyncMock

import pytest
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from httpx import ASGITransport, AsyncClient

from latency.ENUM.general import DiagnosisConfigLogType
from latency.database.managers.diagnosis_config import DiagnosisConfigPGManager
from latency.database.managers.log_knowledge import LogKnowledgePGManager
from latency.exceptions import BadRequestBizException, NotFoundBizException
from latency.routers.diagnosis_config import router
from latency.schemas.config import (
    DiagnosisRuntimeConfig,
    KVCacheDiagnosisConfig,
    UBSocketDiagnosisConfig,
)
from latency.services.diagnosis_config import DiagnosisConfigService


def _runtime_config(
    kv_pattern: str = "kv.log",
    ubsocket_pattern: str = "ubsocket.log",
    threshold: float = 5.0,
) -> DiagnosisRuntimeConfig:
    return DiagnosisRuntimeConfig(
        log_filename_pattern={
            "ds_client_access_log_file": [kv_pattern],
            "ds_client_info_log_file": [kv_pattern],
            "ds_worker_access_log_file": [kv_pattern],
            "ds_worker_info_log_file": [kv_pattern],
            "resource_log_file": [kv_pattern],
            "brpc_log_file_patterns": [ubsocket_pattern],
        },
        log_analyzer_params={"total_p99_threshold_ms": threshold},
    )


def _kvcache_update() -> KVCacheDiagnosisConfig:
    return KVCacheDiagnosisConfig(
        log_filename_pattern={
            "ds_client_access_log_file": ["new-kv.log"],
            "ds_client_info_log_file": ["new-kv.log"],
            "ds_worker_access_log_file": ["new-kv.log"],
            "ds_worker_info_log_file": ["new-kv.log"],
            "resource_log_file": ["new-kv.log"],
        },
        log_analyzer_params={"total_p99_threshold_ms": 9.0},
    )


def _ubsocket_update() -> UBSocketDiagnosisConfig:
    return UBSocketDiagnosisConfig(
        log_filename_pattern={"brpc_log_file_patterns": ["new-ubsocket.log"]}
    )


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "operation",
    [
        lambda: DiagnosisConfigService.get(
            "missing-kb", DiagnosisConfigLogType.KVCACHE
        ),
        lambda: DiagnosisConfigService.update(
            "missing-kb", DiagnosisConfigLogType.KVCACHE, _kvcache_update()
        ),
        lambda: DiagnosisConfigService.reset(
            "missing-kb", DiagnosisConfigLogType.UBSOCKET
        ),
    ],
)
async def test_operations_reject_nonexistent_kb(monkeypatch, operation):
    kb_exists = AsyncMock(return_value=False)
    get_or_create = AsyncMock()
    upsert = AsyncMock()
    monkeypatch.setattr(LogKnowledgePGManager, "exists", kb_exists)
    monkeypatch.setattr(DiagnosisConfigPGManager, "get_or_create", get_or_create)
    monkeypatch.setattr(DiagnosisConfigPGManager, "upsert", upsert)

    with pytest.raises(NotFoundBizException, match="知识库不存在"):
        await operation()

    kb_exists.assert_awaited_once_with("missing-kb")
    get_or_create.assert_not_awaited()
    upsert.assert_not_awaited()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("log_type", "expected_config_type"),
    [
        (DiagnosisConfigLogType.KVCACHE, KVCacheDiagnosisConfig),
        (DiagnosisConfigLogType.UBSOCKET, UBSocketDiagnosisConfig),
    ],
)
async def test_get_returns_only_requested_config_group(
    monkeypatch, log_type, expected_config_type
):
    runtime = _runtime_config()
    monkeypatch.setattr(LogKnowledgePGManager, "exists", AsyncMock(return_value=True))
    monkeypatch.setattr(
        DiagnosisConfigPGManager, "get_or_create", AsyncMock(return_value=runtime)
    )

    result = await DiagnosisConfigService.get("existing-kb", log_type)

    assert result.log_type == log_type
    assert isinstance(result.config, expected_config_type)
    if log_type == DiagnosisConfigLogType.KVCACHE:
        assert "brpc_log_file_patterns" not in result.config.log_filename_pattern.model_dump()
    else:
        assert result.config.model_dump() == {
            "log_filename_pattern": {"brpc_log_file_patterns": ["ubsocket.log"]}
        }


@pytest.mark.asyncio
async def test_update_kvcache_preserves_ubsocket_config(monkeypatch):
    current = _runtime_config(ubsocket_pattern="keep-ubsocket.log")
    upsert = AsyncMock(side_effect=lambda _kb_id, config: config)
    monkeypatch.setattr(LogKnowledgePGManager, "exists", AsyncMock(return_value=True))
    monkeypatch.setattr(
        DiagnosisConfigPGManager, "get_or_create", AsyncMock(return_value=current)
    )
    monkeypatch.setattr(DiagnosisConfigPGManager, "upsert", upsert)

    result = await DiagnosisConfigService.update(
        "existing-kb", DiagnosisConfigLogType.KVCACHE, _kvcache_update()
    )

    saved = upsert.await_args.args[1]
    assert saved.log_filename_pattern.brpc_log_file_patterns == ["keep-ubsocket.log"]
    assert saved.log_filename_pattern.resource_log_file == ["new-kv.log"]
    assert saved.log_analyzer_params.total_p99_threshold_ms == 9.0
    assert isinstance(result.config, KVCacheDiagnosisConfig)


@pytest.mark.asyncio
@pytest.mark.parametrize("operation", ["update", "reset"])
async def test_ubsocket_update_and_reset_are_unsupported(monkeypatch, operation):
    get_or_create = AsyncMock()
    upsert = AsyncMock()
    monkeypatch.setattr(LogKnowledgePGManager, "exists", AsyncMock(return_value=True))
    monkeypatch.setattr(DiagnosisConfigPGManager, "get_or_create", get_or_create)
    monkeypatch.setattr(DiagnosisConfigPGManager, "upsert", upsert)

    with pytest.raises(
        BadRequestBizException, match="UBSocket日志解析暂不支持配置"
    ):
        if operation == "update":
            await DiagnosisConfigService.update(
                "existing-kb", DiagnosisConfigLogType.UBSOCKET, _ubsocket_update()
            )
        else:
            await DiagnosisConfigService.reset(
                "existing-kb", DiagnosisConfigLogType.UBSOCKET
            )

    get_or_create.assert_not_awaited()
    upsert.assert_not_awaited()


@pytest.mark.asyncio
async def test_reset_kvcache_preserves_ubsocket_config(monkeypatch):
    current = _runtime_config(
        kv_pattern="custom-kv.log",
        ubsocket_pattern="custom-ubsocket.log",
        threshold=9.0,
    )
    default = _runtime_config(
        kv_pattern="default-kv.log",
        ubsocket_pattern="default-ubsocket.log",
        threshold=5.0,
    )
    upsert = AsyncMock(side_effect=lambda _kb_id, config: config)
    monkeypatch.setattr(LogKnowledgePGManager, "exists", AsyncMock(return_value=True))
    monkeypatch.setattr(
        DiagnosisConfigPGManager, "get_or_create", AsyncMock(return_value=current)
    )
    monkeypatch.setattr(
        DiagnosisConfigPGManager, "get_default_config", lambda: default
    )
    monkeypatch.setattr(DiagnosisConfigPGManager, "upsert", upsert)

    await DiagnosisConfigService.reset(
        "existing-kb", DiagnosisConfigLogType.KVCACHE
    )

    saved = upsert.await_args.args[1]
    assert saved.log_filename_pattern.resource_log_file == ["default-kv.log"]
    assert saved.log_analyzer_params.total_p99_threshold_ms == 5.0
    assert saved.log_filename_pattern.brpc_log_file_patterns == [
        "custom-ubsocket.log"
    ]


@pytest.mark.asyncio
async def test_update_rejects_mismatched_log_type(monkeypatch):
    monkeypatch.setattr(LogKnowledgePGManager, "exists", AsyncMock(return_value=True))
    monkeypatch.setattr(
        DiagnosisConfigPGManager,
        "get_or_create",
        AsyncMock(return_value=_runtime_config()),
    )
    upsert = AsyncMock()
    monkeypatch.setattr(DiagnosisConfigPGManager, "upsert", upsert)

    with pytest.raises(BadRequestBizException, match="log_type 与配置项不匹配"):
        await DiagnosisConfigService.update(
            "existing-kb", DiagnosisConfigLogType.KVCACHE, _ubsocket_update()
        )

    upsert.assert_not_awaited()


@pytest.mark.asyncio
async def test_ubsocket_http_update_and_reset_return_unsupported_message():
    app = FastAPI()

    @app.exception_handler(BadRequestBizException)
    async def bad_request_handler(_request: Request, exc: BadRequestBizException):
        return JSONResponse(
            status_code=400,
            content={"code": 400, "message": exc.message, "result": None},
        )

    app.include_router(router)
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        responses = [
            await client.put(
                "/diagnosis_config/existing-kb",
                params={"log_type": "UBSocket"},
            ),
            await client.put(
                "/diagnosis_config/existing-kb",
                params={"log_type": "UBSocket"},
                json={},
            ),
            await client.post(
                "/diagnosis_config/existing-kb/reset",
                params={"log_type": "UBSocket"},
            ),
        ]

    for response in responses:
        assert response.status_code == 400
        assert response.json()["message"] == "UBSocket日志解析暂不支持配置"
