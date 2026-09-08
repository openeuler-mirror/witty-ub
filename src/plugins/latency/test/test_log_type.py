import pytest
import httpx
from fastapi import FastAPI
from pydantic import ValidationError

from latency.ENUM.general import DiagnosisConfigLogType
from latency.schemas.log import LogFileModel
from latency.schemas.request import UpLoadLogFileConfig, UpLoadLogFilesRequest


@pytest.mark.parametrize("model", [UpLoadLogFileConfig, LogFileModel])
def test_default_log_type(model):
    assert model().log_type is DiagnosisConfigLogType.KVCACHE


@pytest.mark.parametrize("log_type", list(DiagnosisConfigLogType))
def test_upload_log_type_round_trip(log_type):
    config = UpLoadLogFileConfig(log_type=log_type.value)
    assert config.log_type is log_type
    assert config.model_dump(mode="json")["log_type"] == log_type.value


@pytest.mark.parametrize(
    "log_type",
    ["kvcache", "kv-cache", "KV-Cache", "kv_cache", "KVCACHE",
     "ubsocket", "UBSOCKET", "UbSocket", "brpc", "BRPC", "Other", "", None,
     " KVCache", "UBSocket "],
)
@pytest.mark.asyncio
async def test_reject_invalid_upload_log_type(log_type):
    with pytest.raises(ValidationError):
        UpLoadLogFileConfig(log_type=log_type)

    app = FastAPI()

    @app.post("/upload")
    async def upload(request: UpLoadLogFilesRequest):
        return request

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.post(
            "/upload", json={"upload_log_file_configs": [{"log_type": log_type}]}
        )
    assert response.status_code == 422
    assert response.json()["detail"][0]["loc"] == [
        "body", "upload_log_file_configs", 0, "log_type"
    ]
