# Copyright (c) Huawei Technologies Co., Ltd. 2023-2025. All rights reserved.
"""access/fastapi_server 浅测：异常处理器 / 路由注册 / health_check / 启动流程。

不监听真实端口、不真连数据库：PGManager / Config / TaskHandler / scheduler
等依赖全部 monkeypatch；TestClient 仅走 app 对象（不触发 lifespan）。
"""
from __future__ import annotations

import json
import logging
import os
import shutil
from contextlib import asynccontextmanager
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient
from pydantic import BaseModel, ValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.routing import Mount

from latency.access import fastapi_server
from latency.exceptions import (
    BadRequestBizException,
    ConflictBizException,
    NotFoundBizException,
)


def _fake_request() -> SimpleNamespace:
    return SimpleNamespace(method="GET", url=SimpleNamespace(path="/some/path"))


def _body(response) -> dict:
    return json.loads(response.body)


# ---------------------------------------------------------------------------
# 异常处理器（未覆盖的 404/409/400/422 分支）
# ---------------------------------------------------------------------------

class TestExceptionHandlers:
    async def test_not_found_handler_returns_404(self):
        from latency.access.fastapi_server import not_found_exception_handler

        resp = await not_found_exception_handler(
            _fake_request(), NotFoundBizException("任务")
        )
        assert resp.status_code == 404
        assert _body(resp) == {
            "code": 404, "message": "任务不存在", "result": None, "detail": "",
        }

    async def test_conflict_handler_returns_409(self):
        from latency.access.fastapi_server import conflict_exception_handler

        resp = await conflict_exception_handler(
            _fake_request(), ConflictBizException("重复创建")
        )
        assert resp.status_code == 409
        body = _body(resp)
        assert body["code"] == 409
        assert body["message"] == "重复创建"
        assert body["detail"] == ""

    async def test_bad_request_handler_returns_400(self):
        from latency.access.fastapi_server import bad_request_exception_handler

        resp = await bad_request_exception_handler(
            _fake_request(), BadRequestBizException("参数非法")
        )
        assert resp.status_code == 400
        assert _body(resp)["message"] == "参数非法"

    async def test_pydantic_validation_handler_returns_422(self):
        from latency.access.fastapi_server import validation_exception_handler

        class _Model(BaseModel):
            x: int

        try:
            _Model(x="not-an-int")
            raise AssertionError("unreachable")
        except ValidationError as exc:
            resp = await validation_exception_handler(_fake_request(), exc)

        assert resp.status_code == 422
        body = _body(resp)
        assert body["code"] == 422
        assert body["message"] == "请求参数校验失败"
        assert "x" in body["detail"]

    async def test_starlette_http_exception_handler_passthrough(self):
        from latency.access.fastapi_server import starlette_http_exception_handler

        resp = await starlette_http_exception_handler(
            _fake_request(), StarletteHTTPException(status_code=404, detail="nope")
        )
        assert resp.status_code == 404
        assert _body(resp) == {"code": 404, "message": "nope", "result": None}


# ---------------------------------------------------------------------------
# serve_index / health_check
# ---------------------------------------------------------------------------

class TestServeIndex:
    def test_returns_json_message_without_web_index(self, monkeypatch):
        # 强制 index.html 不存在（不依赖仓库当前是否有 web 目录）
        real_exists = os.path.exists

        def fake_exists(p):
            if str(p).endswith("index.html"):
                return False
            return real_exists(p)

        monkeypatch.setattr(os.path, "exists", fake_exists)
        resp = TestClient(fastapi_server.app).get("/")
        assert resp.status_code == 200
        assert resp.json() == {"message": "Witty-ub API Server"}

    def test_serves_index_html_when_web_dir_present(self):
        web_dir = os.path.join(
            os.path.dirname(os.path.dirname(fastapi_server.__file__)), "web"
        )
        os.makedirs(web_dir, exist_ok=True)
        index_path = os.path.join(web_dir, "index.html")
        try:
            with open(index_path, "w", encoding="utf-8") as f:
                f.write("<html>witty-index</html>")
            resp = TestClient(fastapi_server.app).get("/")
            assert resp.status_code == 200
            assert "witty-index" in resp.text
        finally:
            shutil.rmtree(web_dir, ignore_errors=True)


class TestHealthCheck:
    @staticmethod
    def _patch_ok_connection(monkeypatch):
        from latency.database.engine import PGManager

        executed = []

        class _Conn:
            async def execute(self, stmt):
                executed.append(stmt)

        @asynccontextmanager
        async def ok_connection():
            yield _Conn()

        monkeypatch.setattr(PGManager, "connection", ok_connection)
        return executed

    async def test_returns_ok_when_database_reachable(self, monkeypatch):
        from latency.access.fastapi_server import health_check

        executed = self._patch_ok_connection(monkeypatch)
        result = await health_check()
        # master：health 附带磁盘水位信息（可写状态/剩余空间/阈值）
        assert result["status"] == "ok"
        assert result["writable"] is True
        assert result["disk_mode"] == "normal"
        assert result["free_disk_bytes"] >= 0
        assert "minimum_free_disk_bytes" in result
        assert result["message"] is None
        assert len(executed) == 1
        assert str(executed[0]).startswith("SELECT 1")

    async def test_unavailable_returns_503_json_response(self, monkeypatch):
        from sqlalchemy.exc import SQLAlchemyError

        from latency.access.fastapi_server import DATABASE_UNAVAILABLE_MESSAGE, health_check
        from latency.database.engine import PGManager

        class _Conn:
            async def execute(self, stmt):
                raise SQLAlchemyError("connection refused")

        @asynccontextmanager
        async def bad_connection():
            yield _Conn()

        monkeypatch.setattr(PGManager, "connection", bad_connection)
        resp = await health_check()
        assert resp.status_code == 503
        assert _body(resp) == {
            "status": "unavailable",
            "code": 503,
            "message": DATABASE_UNAVAILABLE_MESSAGE,
            "retryable": True,
        }


# ---------------------------------------------------------------------------
# configure()：路由注册 / 静态目录挂载
# ---------------------------------------------------------------------------

class TestConfigure:
    async def test_includes_all_routers(self):
        before = len(fastapi_server.app.routes)
        await fastapi_server.configure()
        assert len(fastapi_server.app.routes) > before

        # 注册后的路由可命中（DB 未初始化 → 500，但绝不是 404）
        client = TestClient(fastapi_server.app, raise_server_exceptions=False)
        assert client.get("/task/list").status_code != 404
        # 未注册路径仍 404
        assert client.get("/definitely/not/registered").status_code == 404

    async def test_mounts_static_when_web_dir_exists(self):
        web_dir = os.path.join(
            os.path.dirname(os.path.dirname(fastapi_server.__file__)), "web"
        )
        os.makedirs(web_dir, exist_ok=True)
        try:
            await fastapi_server.configure()
            mounts = [r for r in fastapi_server.app.routes if isinstance(r, Mount)]
            assert any(m.name == "static" for m in mounts)
        finally:
            shutil.rmtree(web_dir, ignore_errors=True)


# ---------------------------------------------------------------------------
# mk_dirs / startup_event（依赖全部 mock）
# ---------------------------------------------------------------------------

class TestStartupEvent:
    @staticmethod
    def _patch_dependencies(monkeypatch, tmp_path, calls):
        class _FakeConfig:
            def get_config(self):
                return SimpleNamespace(
                    db=SimpleNamespace(
                        pg_dsn_url=lambda: "postgresql://u:p@127.0.0.1:5432/db",
                        pg_pool_size=5,
                        pg_max_overflow=7,
                    )
                )

        monkeypatch.setattr(fastapi_server, "Config", _FakeConfig)

        class _FakePGManager:
            initialized = []

            @staticmethod
            def initialize(dsn, pool_size=None, max_overflow=None):
                _FakePGManager.initialized.append((dsn, pool_size, max_overflow))

            @staticmethod
            async def init_timezone():
                calls.append("init_timezone")

        monkeypatch.setattr(fastapi_server, "PGManager", _FakePGManager)

        async def fake_init_postgresql_database():
            calls.append("init_db")

        monkeypatch.setattr(
            fastapi_server, "init_postgresql_database", fake_init_postgresql_database
        )

        class _FakeKnowledge:
            async def init_failure_mode_knowledge(self):
                calls.append("knowledge")

        monkeypatch.setattr(fastapi_server, "FailureModeKnowledge", _FakeKnowledge)

        async def fake_backfill():
            calls.append("backfill")

        monkeypatch.setattr(
            fastapi_server,
            "backfill_trace_failure_event_status_codes",
            fake_backfill,
        )

        class _FakeTaskHandler:
            @staticmethod
            async def init_task_queue():
                calls.append("task_queue")

            @staticmethod
            async def handle_tasks():
                raise AssertionError("不应在启动期执行")

            @staticmethod
            async def reap_finished_processes():
                # master：收尸独立成 interval job（join 子进程）
                calls.append("reap")

        monkeypatch.setattr(fastapi_server, "TaskHandler", _FakeTaskHandler)

        class _FakeScheduler:
            def __init__(self):
                self.jobs = []

            def add_job(self, fn, *args, **kwargs):
                self.jobs.append((fn, args, kwargs))

            def start(self):
                calls.append("scheduler_start")

        scheduler = _FakeScheduler()
        monkeypatch.setattr(fastapi_server, "scheduler", scheduler)

        # mk_dirs 写入 tmp 目录（绝对路径在 os.path.join 中胜出）
        monkeypatch.setattr(
            fastapi_server,
            "FilePath",
            [SimpleNamespace(value=str(tmp_path / "exists")), SimpleNamespace(value=str(tmp_path / "created"))],
        )
        (tmp_path / "exists").mkdir()
        return _FakePGManager, scheduler, _FakeTaskHandler

    async def test_startup_initializes_backend_and_scheduler(self, tmp_path, monkeypatch):
        calls = []
        fake_pg, scheduler, fake_task = self._patch_dependencies(
            monkeypatch, tmp_path, calls
        )

        await fastapi_server.startup_event()

        assert fake_pg.initialized == [("postgresql://u:p@127.0.0.1:5432/db", 5, 7)]
        assert calls == [
            "init_timezone", "init_db", "knowledge", "backfill",
            "task_queue", "scheduler_start",
        ]
        # mk_dirs：已存在目录跳过、缺失目录创建
        assert (tmp_path / "exists").is_dir()
        assert (tmp_path / "created").is_dir()
        # 调度任务注册：handle_tasks 每秒执行、单实例、合并积压；
        # master：收尸（reap_finished_processes）独立成第二个 interval job
        assert len(scheduler.jobs) == 2
        fn, args, kwargs = scheduler.jobs[0]
        assert fn is fake_task.handle_tasks
        assert args == ("interval",)
        assert kwargs == {"seconds": 1, "max_instances": 1, "coalesce": True}
        fn, args, kwargs = scheduler.jobs[1]
        assert fn is fake_task.reap_finished_processes
        assert args == ("interval",)
        assert kwargs == {"seconds": 1, "max_instances": 1, "coalesce": True}


# ---------------------------------------------------------------------------
# _setup_logging / main
# ---------------------------------------------------------------------------

class TestSetupLogging:
    def test_applies_configured_level(self, monkeypatch):
        recorded = {}

        def fake_basic_config(**kwargs):
            recorded.update(kwargs)

        monkeypatch.setattr(logging, "basicConfig", fake_basic_config)

        class _FakeConfig:
            def get_config(self):
                return SimpleNamespace(
                    service=SimpleNamespace(log_level=SimpleNamespace(value="WARNING"))
                )

        monkeypatch.setattr(fastapi_server, "Config", _FakeConfig)

        names = [
            "latency.task.task_handler",
            "latency.database",
            "apscheduler.executors.default",
        ]
        saved = {name: logging.getLogger(name).level for name in names}
        try:
            fastapi_server._setup_logging()
            assert recorded["level"] == logging.WARNING
            assert logging.getLogger("latency.task.task_handler").level == logging.INFO
            assert logging.getLogger("latency.database").level == logging.WARNING
        finally:
            for name, level in saved.items():
                logging.getLogger(name).setLevel(level)


class TestMain:
    @staticmethod
    def _patch_run(monkeypatch, ssl_enable):
        calls = {}

        def fake_run(app, **kwargs):
            calls["app"] = app
            calls.update(kwargs)

        monkeypatch.setattr(fastapi_server.uvicorn, "run", fake_run)
        monkeypatch.setattr(fastapi_server, "_setup_logging", lambda: None)

        class _FakeConfig:
            def get_config(self):
                service = SimpleNamespace(
                    ssl_enable=ssl_enable,
                    uvicorn_ip="127.0.0.1",
                    uvicorn_port="8123",
                )
                if ssl_enable:
                    service.ssl_certfile = "/tmp/cert.pem"
                    service.ssl_keyfile = "/tmp/key.pem"
                return SimpleNamespace(service=service)

        monkeypatch.setattr(fastapi_server, "Config", _FakeConfig)
        return calls

    def test_runs_uvicorn_without_ssl(self, monkeypatch):
        calls = self._patch_run(monkeypatch, ssl_enable=False)
        fastapi_server.main()
        assert calls["app"] is fastapi_server.app
        assert calls["host"] == "127.0.0.1"
        assert calls["port"] == 8123
        assert calls["proxy_headers"] is True
        assert calls["forwarded_allow_ips"] == "*"
        assert "ssl_certfile" not in calls
        assert "ssl_keyfile" not in calls

    def test_runs_uvicorn_with_ssl(self, monkeypatch):
        calls = self._patch_run(monkeypatch, ssl_enable=True)
        fastapi_server.main()
        assert calls["ssl_certfile"] == "/tmp/cert.pem"
        assert calls["ssl_keyfile"] == "/tmp/key.pem"

    def test_exits_with_code_1_on_startup_error(self, monkeypatch):
        def boom():
            raise RuntimeError("config broken")

        monkeypatch.setattr(fastapi_server, "_setup_logging", boom)
        with pytest.raises(SystemExit) as exc_info:
            fastapi_server.main()
        assert exc_info.value.code == 1
