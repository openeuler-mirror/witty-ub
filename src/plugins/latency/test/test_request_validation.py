import json
from unittest.mock import AsyncMock, patch

import httpx
import pytest
from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError

from latency.access.fastapi_server import request_validation_exception_handler
from latency.routers import log_file, log_knowledge
from latency.schemas.request import UpdateLogFileRequest
from latency.schemas.response import UpdateLogFileMsg


@pytest.fixture
def validation_app():
    app = FastAPI()
    app.include_router(log_file.router)
    app.include_router(log_knowledge.router)
    app.add_exception_handler(
        RequestValidationError,
        request_validation_exception_handler,
    )
    return app


@pytest.mark.asyncio
@pytest.mark.parametrize("content", [b"not-json", b""])
async def test_upload_rejects_invalid_or_empty_json_with_422(validation_app, content):
    transport = httpx.ASGITransport(app=validation_app, raise_app_exceptions=False)
    with patch(
        "latency.routers.log_file.ResourceIdService.require",
        new=AsyncMock(return_value=None),
    ):
        async with httpx.AsyncClient(
            transport=transport,
            base_url="http://test",
        ) as client:
            response = await client.post(
                "/log_file/00000000-0000-0000-0000-000000000000",
                content=content,
                headers={"content-type": "application/json"},
            )

    assert response.status_code == 422
    assert response.json()["detail"][0]["type"] == "json_invalid"


@pytest.mark.asyncio
async def test_plain_text_validation_error_is_json_serializable(validation_app):
    transport = httpx.ASGITransport(app=validation_app, raise_app_exceptions=False)
    async with httpx.AsyncClient(
        transport=transport,
        base_url="http://test",
    ) as client:
        response = await client.post(
            "/log_kb",
            content=b"plain text",
            headers={"content-type": "text/plain"},
        )

    assert response.status_code == 422
    assert response.json()["code"] == 422


def test_update_log_file_requires_every_field_except_name():
    schema = UpdateLogFileRequest.model_json_schema()

    assert set(schema["required"]) == {"source_type", "source", "log_type"}


def test_request_models_use_strict_types():
    with pytest.raises(ValueError):
        UpdateLogFileRequest.model_validate(
            {
                "name": 123,
                "source_type": "local",
                "source": "/tmp/example.log",
                "log_type": "KVCache",
            }
        )


@pytest.mark.parametrize("source", ["", "   ", "relative/example.log"])
def test_local_source_must_be_an_absolute_path(source):
    with pytest.raises(ValueError, match="source必须是绝对路径"):
        UpdateLogFileRequest.model_validate(
            {
                "source_type": "local",
                "source": source,
                "log_type": "KVCache",
            }
        )


def test_remote_source_is_not_validated_as_a_local_path():
    request = UpdateLogFileRequest.model_validate(
        {
            "source_type": "remote",
            "source": "https://example.com/logs.zip",
            "log_type": "KVCache",
        }
    )

    assert request.source == "https://example.com/logs.zip"


@pytest.mark.asyncio
async def test_update_log_file_accepts_enum_values_from_json(validation_app):
    transport = httpx.ASGITransport(app=validation_app, raise_app_exceptions=False)
    payload = {
        "source_type": "local",
        "source": "/tmp/example.log",
        "log_type": "KVCache",
    }
    with (
        patch(
            "latency.routers.log_file.ResourceIdService.require",
            new=AsyncMock(return_value=None),
        ),
        patch(
            "latency.routers.log_file.LogFileService.update_log_file",
            new=AsyncMock(return_value=UpdateLogFileMsg(log_file_id="unused")),
        ),
    ):
        async with httpx.AsyncClient(
            transport=transport,
            base_url="http://test",
        ) as client:
            response = await client.put(
                "/log_file/00000000-0000-0000-0000-000000000000",
                content=json.dumps(payload),
                headers={"content-type": "application/json"},
            )

    assert response.status_code == 200, response.text
