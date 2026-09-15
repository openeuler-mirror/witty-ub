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
from latency.common.disk_space import DiskCapacity, disk_capacity
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
async def test_health_check_reports_read_only_mode_when_disk_is_low(monkeypatch):
    @asynccontextmanager
    async def available_connection():
        class Connection:
            async def execute(self, _statement):
                return None

        yield Connection()

    monkeypatch.setattr(PGManager, "connection", available_connection)
    monkeypatch.setattr(
        "latency.access.fastapi_server.disk_capacity",
        lambda: DiskCapacity("warning", 128, 4096, 1024, 256, 2048),
    )

    response = await health_check()

    assert response == {
        "status": "ok",
        "writable": False,
        "disk_mode": "warning",
        "free_disk_bytes": 128,
        "minimum_free_disk_bytes": 1024,
        "critical_free_disk_bytes": 256,
        "recovery_free_disk_bytes": 2048,
        "message": "服务器磁盘空间不足，当前仅开放查询和删除操作",
    }


def test_disk_capacity_uses_configured_thresholds(monkeypatch):
    monkeypatch.setenv("WITTY_MIN_FREE_DISK_BYTES", "100")
    monkeypatch.setenv("WITTY_CRITICAL_FREE_DISK_BYTES", "50")
    monkeypatch.setenv("WITTY_RECOVERY_FREE_DISK_BYTES", "150")
    monkeypatch.setattr(
        "latency.common.disk_space.shutil.disk_usage",
        lambda _path: type("Usage", (), {"free": 49, "total": 1000})(),
    )

    capacity = disk_capacity()
    assert capacity.mode == "critical"
    assert (capacity.warning_bytes, capacity.critical_bytes, capacity.recovery_bytes) == (100, 50, 150)


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
