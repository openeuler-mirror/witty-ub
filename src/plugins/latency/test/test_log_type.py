import pytest
import httpx
from fastapi import FastAPI
from pydantic import ValidationError

from latency.ENUM.general import DiagnosisConfigLogType
from latency.schemas.log import LogFileModel
from latency.schemas.request import UpLoadLogFileConfig, UpLoadLogFilesRequest


def test_log_file_model_default_log_type():
    assert LogFileModel().log_type is DiagnosisConfigLogType.KVCACHE


def test_upload_config_requires_log_type():
    with pytest.raises(ValidationError):
        UpLoadLogFileConfig(name="logs", source_type="local", source="/tmp/logs")


@pytest.mark.parametrize("log_type", list(DiagnosisConfigLogType))
def test_upload_log_type_round_trip(log_type):
    config = UpLoadLogFileConfig(
        source_type="local", source="/tmp/logs", log_type=log_type.value
    )
    assert config.log_type is log_type
    assert config.model_dump(mode="json")["log_type"] == log_type.value


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("kvcache", "KVCache"), ("kv-cache", "KVCache"), ("KV-Cache", "KVCache"),
        ("kv_cache", "KVCache"), ("KVCACHE", "KVCache"), (" KVCache", "KVCache"),
        ("ubsocket", "UBSocket"), ("UBSOCKET", "UBSocket"), ("UbSocket", "UBSocket"),
        ("UBSocket ", "UBSocket"),
    ],
)
def test_normalize_upload_log_type_aliases(raw, expected):
    """前端/脚本发过 kv-cache、kvcache 这类写法，统一归一化到规范取值。"""
    config = UpLoadLogFileConfig(
        source_type="local", source="/tmp/logs", log_type=raw
    )
    assert config.log_type.value == expected


@pytest.mark.parametrize("log_type", ["brpc", "BRPC", "Other", "", None])
def test_reject_truly_invalid_upload_log_type(log_type):
    """真正不认识的值仍然必须拒。"""
    with pytest.raises(ValidationError):
        UpLoadLogFileConfig(
            source_type="local", source="/tmp/logs", log_type=log_type
        )


@pytest.mark.asyncio
@pytest.mark.parametrize("log_type", ["brpc", "Other"])
async def test_api_rejects_truly_invalid_log_type(log_type):
    app = FastAPI()

    @app.post("/upload")
    async def upload(request: UpLoadLogFilesRequest):
        return request

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.post(
            "/upload",
            json={
                "upload_log_file_configs": [
                    {"source_type": "local", "source": "/tmp/logs", "log_type": log_type}
                ]
            },
        )
    assert response.status_code == 422
    assert response.json()["detail"][0]["loc"] == [
        "body", "upload_log_file_configs", 0, "log_type"
    ]


@pytest.mark.parametrize(
    "payload",
    [
        {},
        {"upload_log_file_configs": []},
        {"upload_log_file_configs": [{}]},
        {"upload_log_file_configs": [{"source_type": "local"}]},
        {"upload_log_file_configs": [{"source": "/tmp/logs"}]},
        {"upload_log_file_configs": [{"source_type": "local", "log_type": "KVCache"}]},
        {"upload_log_file_configs": [{"source": "/tmp/logs", "log_type": "KVCache"}]},
    ],
)
@pytest.mark.asyncio
async def test_reject_empty_or_incomplete_upload_configs(payload):
    with pytest.raises(ValidationError):
        UpLoadLogFilesRequest.model_validate(payload)

    app = FastAPI()

    @app.post("/upload")
    async def upload(request: UpLoadLogFilesRequest):
        return request

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.post("/upload", json=payload)
    assert response.status_code == 422
