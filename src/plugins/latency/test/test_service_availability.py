import json
from contextlib import asynccontextmanager

import pytest
from sqlalchemy.exc import OperationalError
from starlette.requests import Request

from latency.access.fastapi_server import (
    DATABASE_UNAVAILABLE_MESSAGE,
    database_exception_handler,
    health_check,
)
from latency.database.engine import PGManager


@pytest.mark.asyncio
async def test_health_check_reports_database_unavailable(monkeypatch):
    @asynccontextmanager
    async def unavailable_connection():
        raise RuntimeError("database unavailable")
        yield

    monkeypatch.setattr(PGManager, "connection", unavailable_connection)

    response = await health_check()

    assert response.status_code == 503
    assert json.loads(response.body) == {
        "status": "unavailable",
        "code": 503,
        "message": DATABASE_UNAVAILABLE_MESSAGE,
        "retryable": True,
    }


@pytest.mark.asyncio
async def test_database_errors_return_retryable_service_unavailable():
    request = Request(
        {
            "type": "http",
            "method": "POST",
            "path": "/log_kb/list",
            "headers": [],
        }
    )
    error = OperationalError("SELECT 1", {}, Exception("connection refused"))

    response = await database_exception_handler(request, error)

    assert response.status_code == 503
    assert json.loads(response.body) == {
        "code": 503,
        "message": DATABASE_UNAVAILABLE_MESSAGE,
        "result": None,
        "retryable": True,
    }
