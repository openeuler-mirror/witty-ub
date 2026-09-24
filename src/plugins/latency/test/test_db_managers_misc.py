# Copyright (c) Huawei Technologies Co., Ltd. 2023-2025. All rights reserved.
"""Unit tests for database layer misc managers and init helpers.

Fake sessions/connections mirror the approach of test_brpc_diagnosis_database.py:
manager methods run against recording fakes so both the SQL-construction and
the result-mapping branches execute without a live PostgreSQL.
"""
from __future__ import annotations

from contextlib import asynccontextmanager
from datetime import datetime
from types import SimpleNamespace

import pytest

from latency.database import init as init_module
from latency.database.engine import PGManager
from latency.database.managers.anomalous_event import AnomalousEventPGManager
from latency.database.managers.anomalous_event_chain import (
    AnomalousEventChainPGManager,
)
from latency.database.managers.brpc_profiling_result import (
    BrpcProfilingResultPGManager,
)
from latency.database.managers.diagnosis_case import DiagnosisCasePGManager
from latency.database.managers.diagnosis_config import DiagnosisConfigPGManager
from latency.database.managers.failure_mode_knowledge import (
    FailureModeKnowledgePGManager,
)
from latency.database.managers.log_file import LogFilePGManager
from latency.database.managers.log_knowledge import LogKnowledgePGManager
from latency.database.managers.resource_id import ResourceIdPGManager
from latency.database.managers.task import TaskPGManager
from latency.database.managers.task_report import TaskReportPGManager
from latency.ENUM.task import TaskStatusEnum, TaskTypeEnum
from latency.parse.brpc_profiling_parser import BrpcProfilingRecord
from latency.schemas.diagnosis_case import DiagnosisCaseModel
from latency.schemas.failure_mode import (
    FailureModeModel,
    StatusCodeKnowledgeModel,
)
from latency.schemas.log import (
    AnomalousEventChainModel,
    AnomalousEventDataclass,
    AnomalousEventModel,
    LogFileModel,
    LogKnowledgeModel,
)
from latency.schemas.request import (
    ListAnomalousEventChainRequest,
    ListAnomalousEventRequest,
    ListLogFilesRequest,
    ListLogKnowledgeRequest,
    SearchDiagnosisCasesRequest,
)
from latency.schemas.task import TaskModel, TaskReportModel


# ---------------------------------------------------------------------------
# Fake session / connection infrastructure
# ---------------------------------------------------------------------------


class FakeResult:
    """Mimics the subset of SQLAlchemy Result used by the managers."""

    def __init__(self, rows=None, scalar_value=None, rowcount=0):
        self._rows = rows if rows is not None else []
        self._scalar_value = scalar_value
        self._rowcount = rowcount

    def scalars(self):
        return self

    def mappings(self):
        return self

    def all(self):
        return self._rows

    def first(self):
        return self._rows[0] if self._rows else None

    def scalar(self):
        return self._scalar_value

    def scalar_one_or_none(self):
        return self._scalar_value

    @property
    def rowcount(self):
        return self._rowcount

    def __iter__(self):
        return iter(self._rows)


class FakeSession:
    """Records execute calls and replays queued results in FIFO order."""

    def __init__(self, results=None, default=None):
        self.executed = []
        self.added = []
        self.commit_count = 0
        self._results = list(results or [])
        self._default = default if default is not None else FakeResult()
        self.get_rows = {}

    async def execute(self, statement, params=None):
        self.executed.append((statement, params))
        if self._results:
            item = self._results.pop(0)
            if isinstance(item, BaseException):
                raise item
            return item
        return self._default

    async def scalar(self, statement, params=None):
        result = await self.execute(statement, params)
        return result.scalar()

    async def get(self, entity, key):
        return self.get_rows.get(key)

    def add_all(self, rows):
        self.added.extend(rows)

    async def commit(self):
        self.commit_count += 1

    async def rollback(self):
        pass


class ExecErrorSession(FakeSession):
    """Session whose every execute raises; used for error branches."""

    def __init__(self, error=None):
        super().__init__()
        self.error = error or RuntimeError("db down")

    async def execute(self, statement, params=None):
        self.executed.append((statement, params))
        raise self.error


class AddAllErrorSession(FakeSession):
    """Session whose add_all raises; used for write failure branches."""

    def __init__(self, error=None):
        super().__init__()
        self.error = error or RuntimeError("write failed")

    def add_all(self, rows):
        raise self.error


@pytest.fixture()
def patch_session(monkeypatch):
    """Factory fixture patching PGManager.session to yield a FakeSession."""

    def _patch(fake_session):
        @asynccontextmanager
        async def _ctx():
            yield fake_session

        monkeypatch.setattr(PGManager, "session", _ctx)
        return fake_session

    return _patch


class RecordingConn:
    """Connection double for engine-level migration helpers in init.py."""

    def __init__(self, info_rows=None, scalar_value=None):
        self.statements = []
        self.info_rows = info_rows
        self.scalar_value = scalar_value

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc_info):
        return False

    async def execute(self, statement, params=None):
        self.statements.append((statement, params))
        if "information_schema" in str(statement):
            return FakeResult(rows=self.info_rows or [], scalar_value=self.scalar_value)
        return FakeResult()

    async def scalar(self, statement, params=None):
        self.statements.append((statement, params))
        return self.scalar_value

    async def run_sync(self, fn, *args, **kwargs):
        self.statements.append(("run_sync", fn))
        return None


@pytest.fixture()
def patch_engine(monkeypatch):
    """Factory fixture patching PGManager.engine to return a fake engine."""

    def _patch(conn):
        engine = SimpleNamespace(begin=lambda: conn)
        monkeypatch.setattr(PGManager, "engine", lambda: engine)
        return conn

    return _patch


def sql_text(statement) -> str:
    return " ".join(str(statement).split())


# ---------------------------------------------------------------------------
# database/init.py — month iteration and migration helpers
# ---------------------------------------------------------------------------


def test_month_iter_yields_month_starts_inclusive():
    months = list(
        init_module._month_iter(datetime(2024, 11, 15), datetime(2025, 2, 20))
    )
    assert months == [
        datetime(2024, 11, 1),
        datetime(2024, 12, 1),
        datetime(2025, 1, 1),
        datetime(2025, 2, 1),
    ]


def test_month_iter_single_month():
    months = list(
        init_module._month_iter(datetime(2024, 6, 10), datetime(2024, 6, 28))
    )
    assert months == [datetime(2024, 6, 1)]


async def test_create_time_window_partition_december_rolls_to_next_year(patch_engine):
    conn = patch_engine(RecordingConn())
    await init_module._create_time_window_partition(conn, datetime(2024, 12, 1))
    sql = sql_text(conn.statements[0][0])
    assert "CREATE TABLE IF NOT EXISTS time_window_aggregated_202412" in sql
    assert "FOR VALUES FROM ('2024-12-01 00:00:00') TO ('2025-01-01 00:00:00')" in sql


async def test_create_time_window_partition_mid_year(patch_engine):
    conn = patch_engine(RecordingConn())
    await init_module._create_time_window_partition(conn, datetime(2024, 6, 1))
    sql = sql_text(conn.statements[0][0])
    assert "time_window_aggregated_202406" in sql
    assert "TO ('2024-07-01 00:00:00')" in sql


async def test_ensure_missing_columns_runs_one_alter_per_entry(patch_engine):
    conn = patch_engine(RecordingConn())
    await init_module._ensure_missing_columns()
    assert len(conn.statements) == len(init_module._MISSING_COLUMN_DDL)
    sqls = [sql_text(s) for s, _ in conn.statements]
    assert sqls[0] == "ALTER TABLE task ADD COLUMN IF NOT EXISTS task_config JSONB"
    assert all(s.startswith("ALTER TABLE") for s in sqls)


async def test_backfill_brpc_batch_hit_count(patch_engine):
    conn = patch_engine(RecordingConn())
    await init_module._backfill_brpc_batch_hit_count()
    sqls = [sql_text(s) for s, _ in conn.statements]
    assert len(sqls) == 2
    assert "UPDATE brpc_diag_batch AS batch" in sqls[0]
    assert "ALTER COLUMN hit_count SET NOT NULL" in sqls[1]


async def test_backfill_brpc_batch_time_range(patch_engine):
    conn = patch_engine(RecordingConn())
    await init_module._backfill_brpc_batch_time_range()
    sqls = [sql_text(s) for s, _ in conn.statements]
    assert len(sqls) == 2
    assert "start_timestamp = bounds.start_timestamp" in sqls[0]
    assert "WHERE hit_count = 0" in sqls[1]


async def test_backfill_brpc_unique_interfaces(patch_engine):
    conn = patch_engine(RecordingConn())
    await init_module._backfill_brpc_unique_interfaces()
    sql = sql_text(conn.statements[0][0])
    assert "interface_resolution = 'static_unique'" in sql
    assert "HAVING COUNT(*) = 1" in sql


async def test_backfill_brpc_interface_buckets_covers_all_windows(patch_engine):
    conn = patch_engine(RecordingConn())
    await init_module._backfill_brpc_interface_buckets()
    assert len(conn.statements) == 4
    windows = [params["window_seconds"] for _, params in conn.statements]
    assert windows == [10, 60, 600, 3600]
    for (stmt, params), window in zip(conn.statements, windows):
        assert params["window_us"] == window * 1_000_000
        assert "brpc_diag_interface_bucket" in sql_text(stmt)


async def test_migrate_asset_timestamps_no_legacy_columns(patch_engine):
    conn = patch_engine(RecordingConn(info_rows=[]))
    await init_module.migrate_asset_timestamps()
    # Only the information_schema probe ran: no ALTER and no scalar call.
    assert len(conn.statements) == 1


async def test_migrate_asset_timestamps_alters_legacy_columns(
    patch_engine, monkeypatch
):
    monkeypatch.setattr(init_module, "legacy_asset_timezone", lambda: "UTC")
    conn = patch_engine(
        RecordingConn(
            info_rows=[("log_knowledge", "created_at"), ("log_file", "updated_at")],
            scalar_value="'UTC'",
        )
    )
    await init_module.migrate_asset_timestamps()
    # probe + zone literal scalar + two ALTER statements
    assert len(conn.statements) == 4
    alters = [sql_text(s) for s, _ in conn.statements[2:]]
    assert 'ALTER TABLE public."log_knowledge" ALTER COLUMN "created_at"' in alters[0]
    assert "AT TIME ZONE 'UTC'" in alters[0]
    assert 'ALTER TABLE public."log_file" ALTER COLUMN "updated_at"' in alters[1]


async def test_migrate_timestamptz_to_timestamp_skips_asset_columns(patch_engine):
    conn = patch_engine(
        RecordingConn(
            info_rows=[
                ("log_parse_result", "timestamp"),
                ("log_knowledge", "created_at"),
                ("log_file", "updated_at"),
            ]
        )
    )
    await init_module.migrate_timestamptz_to_timestamp()
    # probe + a single ALTER for the only non-asset column
    assert len(conn.statements) == 2
    sql = sql_text(conn.statements[1][0])
    assert "ALTER TABLE log_parse_result" in sql
    assert "TYPE timestamp without time zone" in sql


async def test_create_log_parse_result_partitions(patch_engine):
    conn = patch_engine(RecordingConn())
    await init_module.create_log_parse_result_partitions()
    assert len(conn.statements) == 32
    first = sql_text(conn.statements[0][0])
    last = sql_text(conn.statements[-1][0])
    assert "log_parse_result_p0" in first and "REMAINDER 0" in first
    assert "log_parse_result_p31" in last and "REMAINDER 31" in last


async def test_migrate_yuanrong_metric_columns(patch_engine):
    conn = patch_engine(RecordingConn())
    await init_module.migrate_yuanrong_metric_columns()
    sqls = [sql_text(s) for s, _ in conn.statements]
    # 24 float columns + request_mode + urma_inflight_max
    assert len(sqls) == 26
    assert "ALTER TABLE log_parse_result ADD COLUMN IF NOT EXISTS total_latency_us DOUBLE PRECISION" in sqls[0]
    assert any("ADD COLUMN IF NOT EXISTS request_mode VARCHAR" in s for s in sqls)
    assert any("ADD COLUMN IF NOT EXISTS urma_inflight_max INTEGER" in s for s in sqls)


async def test_create_latency_bucket_partitions(patch_engine):
    conn = patch_engine(RecordingConn())
    await init_module.create_latency_bucket_partitions()
    assert len(conn.statements) == len(init_module.LATENCY_BUCKET_TABLES) * 32
    sqls = [sql_text(s) for s, _ in conn.statements]
    for table in init_module.LATENCY_BUCKET_TABLES:
        assert any(f"{table}_p0" in s for s in sqls)


async def test_migrate_yuanrong_bucket_columns(patch_engine):
    conn = patch_engine(RecordingConn())
    await init_module.migrate_yuanrong_bucket_columns()
    sqls = [sql_text(s) for s, _ in conn.statements]
    # 4 tables * (24 float + request_mode + urma_inflight_max)
    assert len(sqls) == 4 * 26
    for table in init_module.LATENCY_BUCKET_TABLES:
        assert any(f"ALTER TABLE {table} ADD COLUMN IF NOT EXISTS" in s for s in sqls)


async def test_create_time_window_partitions_starts_one_year_back(patch_engine):
    conn = patch_engine(RecordingConn())
    await init_module.create_time_window_partitions(datetime(2026, 3, 15), months=3)
    sqls = [sql_text(s) for s, _ in conn.statements]
    # start-365d => 2025-03; months=3 window end 2025-06 inclusive => 4 months
    assert len(sqls) == 4
    assert "time_window_aggregated_202503" in sqls[0]
    assert "time_window_aggregated_202506" in sqls[-1]


async def test_ensure_time_window_partitions_spans_request_range(patch_engine):
    conn = patch_engine(RecordingConn())
    await init_module.ensure_time_window_partitions(
        datetime(2025, 11, 5), datetime(2026, 2, 10)
    )
    sqls = [sql_text(s) for s, _ in conn.statements]
    assert len(sqls) == 4
    assert "time_window_aggregated_202512" in sqls[1]
    assert "TO ('2026-01-01 00:00:00')" in sqls[1]


async def test_migrate_brpc_log_type_column(patch_engine):
    conn = patch_engine(RecordingConn())
    await init_module.migrate_brpc_log_type_column()
    sqls = [sql_text(s) for s, _ in conn.statements]
    assert len(sqls) == 3
    assert "ADD COLUMN IF NOT EXISTS log_type VARCHAR DEFAULT 'KVCache'" in sqls[0]
    assert "ALTER COLUMN log_type SET DEFAULT 'KVCache'" in sqls[1]
    assert "UPDATE log_file" in sqls[2]


async def test_drop_legacy_log_file_parse_status(patch_engine):
    conn = patch_engine(RecordingConn())
    await init_module.drop_legacy_log_file_parse_status()
    assert sql_text(conn.statements[0][0]) == (
        "ALTER TABLE log_file DROP COLUMN IF EXISTS parse_status"
    )


async def test_migrate_trace_status_code_skips_when_already_array(patch_engine):
    conn = patch_engine(RecordingConn(info_rows=[("ARRAY",)], scalar_value="ARRAY"))
    await init_module.migrate_trace_failure_event_status_code_to_array()
    assert len(conn.statements) == 1  # only the column-type probe


async def test_migrate_trace_status_code_alters_when_not_array(patch_engine):
    conn = patch_engine(
        RecordingConn(
            info_rows=[("character varying",)],
            scalar_value="character varying",
        )
    )
    await init_module.migrate_trace_failure_event_status_code_to_array()
    assert len(conn.statements) == 2
    sql = sql_text(conn.statements[1][0])
    assert "ALTER COLUMN status_code TYPE VARCHAR[]" in sql


async def test_backfill_trace_failure_event_status_codes(patch_engine):
    conn = patch_engine(RecordingConn())
    await init_module.backfill_trace_failure_event_status_codes()
    assert len(conn.statements) == 1
    sql = sql_text(conn.statements[0][0])
    assert sql.startswith("WITH failure_mode_codes AS")
    assert "UPDATE trace_failure_event AS trace_event" in sql


async def test_create_manual_indexes_covers_all_groups(patch_engine):
    conn = patch_engine(RecordingConn())
    await init_module.create_manual_indexes()
    sqls = [sql_text(s) for s, _ in conn.statements]
    expected = 12 + len(init_module.LATENCY_BUCKET_TABLES) + len(init_module.BRPC_DIAG_INDEX_DDL)
    assert len(sqls) == expected
    assert any("idx_lpr_pod_ips" in s for s in sqls)
    assert any("ix_latency_bucket_1h_query" in s for s in sqls)
    assert any("idx_brpc_diag_hit_batch_timestamp" in s for s in sqls)


async def test_init_postgresql_database_runs_every_migration_step(
    patch_engine, monkeypatch
):
    conn = patch_engine(RecordingConn())
    called = []

    def _make_stub(name):
        async def _stub(*args, **kwargs):
            called.append(name)

        return _stub

    steps = [
        "_ensure_missing_columns",
        "_backfill_brpc_batch_hit_count",
        "_backfill_brpc_batch_time_range",
        "_backfill_brpc_unique_interfaces",
        "_backfill_brpc_interface_buckets",
        "migrate_asset_timestamps",
        "migrate_timestamptz_to_timestamp",
        "migrate_yuanrong_metric_columns",
        "migrate_brpc_log_type_column",
        "drop_legacy_log_file_parse_status",
        "migrate_trace_failure_event_status_code_to_array",
        "create_log_parse_result_partitions",
        "create_time_window_partitions",
        "create_latency_bucket_partitions",
        "migrate_yuanrong_bucket_columns",
        "create_manual_indexes",
    ]
    for name in steps:
        monkeypatch.setattr(init_module, name, _make_stub(name))

    await init_module.init_postgresql_database()
    # create_all ran via run_sync, then every migration step in order
    assert conn.statements and conn.statements[0][0] == "run_sync"
    assert called == steps


# ---------------------------------------------------------------------------
# database/engine.py — guard rails and lifecycle
# ---------------------------------------------------------------------------


async def test_session_raises_when_not_initialized(monkeypatch):
    monkeypatch.setattr(PGManager, "_session_maker", None)
    with pytest.raises(RuntimeError, match="PGManager not initialized"):
        async with PGManager.session():
            pass


async def test_connection_raises_when_not_initialized(monkeypatch):
    monkeypatch.setattr(PGManager, "_engine", None)
    with pytest.raises(RuntimeError, match="PGManager not initialized"):
        async with PGManager.connection():
            pass


def test_engine_raises_when_not_initialized(monkeypatch):
    monkeypatch.setattr(PGManager, "_engine", None)
    with pytest.raises(RuntimeError, match="PGManager not initialized"):
        PGManager.engine()


async def test_close_disposes_engine_and_resets_state(monkeypatch):
    disposed = []

    class _Engine:
        async def dispose(self):
            disposed.append(True)

    monkeypatch.setattr(PGManager, "_engine", _Engine())
    await PGManager.close()
    assert disposed == [True]
    assert PGManager._engine is None


async def test_close_without_engine_is_noop(monkeypatch):
    monkeypatch.setattr(PGManager, "_engine", None)
    await PGManager.close()
    assert PGManager._engine is None


async def test_init_timezone_is_noop():
    await PGManager.init_timezone()


def test_initialize_rewrites_postgresql_dsn(monkeypatch):
    import latency.database.engine as engine_module

    captured = {}

    def _fake_create(dsn, **kwargs):
        captured["dsn"] = dsn
        captured["kwargs"] = kwargs
        return SimpleNamespace(url="fake")

    monkeypatch.setattr(PGManager, "_engine", None)
    monkeypatch.setattr(PGManager, "_session_maker", None)
    monkeypatch.setattr(engine_module, "create_async_engine", _fake_create)
    monkeypatch.setattr(
        engine_module, "async_sessionmaker", lambda **kwargs: SimpleNamespace()
    )

    PGManager.initialize("postgresql://user:pw@localhost/db", pool_size=3)
    assert captured["dsn"] == "postgresql+asyncpg://user:pw@localhost/db"
    assert captured["kwargs"]["pool_size"] == 3
    assert PGManager._engine.url == "fake"


def test_initialize_is_idempotent(monkeypatch):
    existing = SimpleNamespace(url="existing")
    monkeypatch.setattr(PGManager, "_engine", existing)
    PGManager.initialize("postgresql://localhost/db")
    assert PGManager._engine is existing


async def test_session_commits_and_rolls_back(monkeypatch):
    events = []

    class _Session:
        async def commit(self):
            events.append("commit")

        async def rollback(self):
            events.append("rollback")

    @asynccontextmanager
    async def _maker():
        yield _Session()

    monkeypatch.setattr(PGManager, "_session_maker", lambda: _maker())

    async with PGManager.session():
        pass
    assert events == ["commit"]

    with pytest.raises(ValueError, match="boom"):
        async with PGManager.session():
            raise ValueError("boom")
    assert events == ["commit", "rollback"]


async def test_connection_yields_engine_connection(monkeypatch):
    sentinel = SimpleNamespace(name="conn")

    @asynccontextmanager
    async def _begin():
        yield sentinel

    monkeypatch.setattr(
        PGManager, "_engine", SimpleNamespace(begin=lambda: _begin())
    )
    async with PGManager.connection() as conn:
        assert conn is sentinel


def test_engine_returns_initialized_engine(monkeypatch):
    sentinel = SimpleNamespace(name="engine")
    monkeypatch.setattr(PGManager, "_engine", sentinel)
    assert PGManager.engine() is sentinel


# ---------------------------------------------------------------------------
# TaskPGManager
# ---------------------------------------------------------------------------


def _task_row(task_id="t1", **overrides):
    row = SimpleNamespace(
        id=task_id,
        kb_id="kb-1",
        op_id="log-1",
        retry_times=1,
        task_name="parse",
        task_type=TaskTypeEnum.KV_CACHE_LOG_PARSE_WORKER.value,
        status=TaskStatusEnum.PENDING.value,
        task_config={"start_time": "2026-01-01 00:00:00"},
        existed_status=True,
        created_at=datetime(2026, 1, 1, 10, 0, 0),
        completed_at=None,
        duration_seconds=None,
    )
    for key, value in overrides.items():
        setattr(row, key, value)
    return row


def _task_model(task_id="t1", **overrides):
    data = dict(
        id=task_id,
        kb_id="kb-1",
        op_id="log-1",
        task_name="parse",
        task_type=TaskTypeEnum.KV_CACHE_LOG_PARSE_WORKER,
        status=TaskStatusEnum.PENDING,
        task_config={"k": "v"},
        existed_status=True,
        duration_seconds=2.5,
    )
    data.update(overrides)
    return TaskModel(**data)


async def test_add_task_executes_insert(patch_session):
    session = patch_session(FakeSession())
    assert await TaskPGManager.add_task(_task_model()) is True
    assert len(session.executed) == 1
    params = session.executed[0][1]
    assert isinstance(params, list) and params[0]["task_type"] == "kv_cache_log_parse_worker"
    assert params[0]["status"] == "pending"
    assert params[0]["task_config"] == {"k": "v"}
    assert params[0]["duration_seconds"] == 2.5


async def test_add_tasks_empty_returns_empty(patch_session):
    session = patch_session(FakeSession())
    assert await TaskPGManager.add_tasks([]) == []
    assert session.executed == []


async def test_add_tasks_returns_ids(patch_session):
    session = patch_session(FakeSession())
    ids = await TaskPGManager.add_tasks([_task_model("t1"), _task_model("t2")])
    assert ids == ["t1", "t2"]
    assert len(session.executed) == 1


async def test_delete_task_by_task_id(patch_session):
    session = patch_session(FakeSession())
    assert await TaskPGManager.delete_task_by_task_id("t1") is True
    sql, params = session.executed[0]
    assert sql_text(sql) == "DELETE FROM task WHERE id = :id"
    assert params == {"id": "t1"}


async def test_delete_tasks_by_task_ids_empty(patch_session):
    session = patch_session(FakeSession())
    assert await TaskPGManager.delete_tasks_by_task_ids([]) is False
    assert session.executed == []


async def test_delete_tasks_by_task_ids(patch_session):
    session = patch_session(FakeSession())
    assert await TaskPGManager.delete_tasks_by_task_ids(["a", "b"]) is True
    sql, params = session.executed[0]
    assert "id = ANY(:ids)" in sql_text(sql)
    assert params == {"ids": ["a", "b"]}


async def test_delete_tasks_by_status(patch_session):
    session = patch_session(FakeSession())
    assert await TaskPGManager.delete_tasks_by_status("pending") is True
    sql, params = session.executed[0]
    assert "WHERE status = :status" in sql_text(sql)
    assert params == {"status": "pending"}


async def test_update_task_with_no_allowed_keys(patch_session):
    session = patch_session(FakeSession())
    assert await TaskPGManager.update_task("t1", {"not_a_column": 1}) is True
    assert session.executed == []


async def test_update_task_builds_set_clause(patch_session):
    session = patch_session(FakeSession())
    assert await TaskPGManager.update_task("t1", {"status": "running"}) is True
    sql, params = session.executed[0]
    assert sql_text(sql) == "UPDATE task SET status = :status WHERE id = :id"
    assert params == {"id": "t1", "status": "running"}


async def test_mark_failed_with_report_writes_report_row(patch_session):
    session = patch_session(FakeSession(results=[FakeResult(rowcount=1)]))
    assert await TaskPGManager.mark_failed_with_report("t1", "boom") is True
    assert len(session.executed) == 2
    sql, params = session.executed[0]
    assert "SET status = :status" in sql_text(sql)
    report_params = session.executed[1][1]
    assert report_params[0]["task_id"] == "t1"
    assert report_params[0]["progress"] == 100.0
    assert report_params[0]["message"] == "boom"
    assert report_params[0]["existed_status"] is True


async def test_mark_failed_with_report_rowcount_zero(patch_session):
    session = patch_session(FakeSession(default=FakeResult(rowcount=0)))
    assert await TaskPGManager.mark_failed_with_report("t1", "boom") is False


async def test_transition_task_status_true(patch_session):
    session = patch_session(FakeSession(default=FakeResult(rowcount=1)))
    assert await TaskPGManager.transition_task_status(
        "t1", TaskStatusEnum.PENDING, TaskStatusEnum.RUNNING
    ) is True
    sql, params = session.executed[0]
    assert "WHERE id = :id AND status = :from_status" in sql_text(sql)
    assert params["from_status"] == "pending"
    assert params["to_status"] == "running"


async def test_transition_task_status_false(patch_session):
    session = patch_session(FakeSession(default=FakeResult(rowcount=0)))
    assert await TaskPGManager.transition_task_status(
        "t1", TaskStatusEnum.PENDING, TaskStatusEnum.RUNNING
    ) is False


async def test_mark_interrupted_running_tasks_for_retry(patch_session):
    session = patch_session(FakeSession())
    assert await TaskPGManager.mark_interrupted_running_tasks_for_retry() is True
    sql, params = session.executed[0]
    assert "UPDATE task SET status = :retry_status" in sql_text(sql)
    assert params["retry_status"] == TaskStatusEnum.FAILED_PENDING_REMOVE.value
    assert params["running_status"] == TaskStatusEnum.RUNNING.value


async def test_list_tasks_by_task_ids_empty(patch_session):
    session = patch_session(FakeSession())
    assert await TaskPGManager.list_tasks_by_task_ids([]) == []


async def test_list_tasks_by_task_ids_maps_rows(patch_session):
    session = patch_session(FakeSession(default=FakeResult(rows=[_task_row()])))
    result = await TaskPGManager.list_tasks_by_task_ids(["t1"])
    assert len(result) == 1
    task = result[0]
    assert task.id == "t1"
    assert task.task_type is TaskTypeEnum.KV_CACHE_LOG_PARSE_WORKER
    assert task.status is TaskStatusEnum.PENDING
    assert task.task_config == {"start_time": "2026-01-01 00:00:00"}


async def test_list_tasks_by_task_ids_defaults_for_null_columns(patch_session):
    row = _task_row(
        kb_id=None, retry_times=None, task_name=None, existed_status=None
    )
    session = patch_session(FakeSession(default=FakeResult(rows=[row])))
    result = await TaskPGManager.list_tasks_by_task_ids(["t1"])
    assert result[0].kb_id == ""
    assert result[0].retry_times == 0
    assert result[0].task_name == ""
    assert result[0].existed_status is True


async def test_list_all_tasks(patch_session):
    session = patch_session(
        FakeSession(default=FakeResult(rows=[_task_row("t1"), _task_row("t2")]))
    )
    result = await TaskPGManager.list_all_tasks()
    assert [t.id for t in result] == ["t1", "t2"]


async def test_get_task_by_task_id_missing(patch_session):
    session = patch_session(FakeSession())
    assert await TaskPGManager.get_task_by_task_id("missing") is None


async def test_get_task_by_task_id(patch_session):
    session = patch_session(
        FakeSession(default=FakeResult(scalar_value=_task_row()))
    )
    result = await TaskPGManager.get_task_by_task_id("t1")
    assert result is not None and result.id == "t1"


async def test_list_tasks_by_kb_id_with_status_filter(patch_session):
    session = patch_session(FakeSession(default=FakeResult(rows=[_task_row()])))
    result = await TaskPGManager.list_tasks_by_kb_id(
        "kb-1", [TaskStatusEnum.PENDING]
    )
    assert len(result) == 1


async def test_list_tasks_by_kb_id_without_status(patch_session):
    session = patch_session(FakeSession(default=FakeResult(rows=[])))
    assert await TaskPGManager.list_tasks_by_kb_id("kb-1") == []


async def test_list_tasks_by_status_empty(patch_session):
    session = patch_session(FakeSession())
    assert await TaskPGManager.list_tasks_by_status([]) == []


async def test_list_tasks_by_status(patch_session):
    session = patch_session(FakeSession(default=FakeResult(rows=[_task_row()])))
    result = await TaskPGManager.list_tasks_by_status([TaskStatusEnum.PENDING])
    assert len(result) == 1


async def test_get_oldest_tasks_by_status(patch_session):
    session = patch_session(FakeSession(default=FakeResult(rows=[_task_row()])))
    result = await TaskPGManager.get_oldest_tasks_by_status(
        TaskStatusEnum.PENDING, limit=5
    )
    assert len(result) == 1


async def test_list_current_tasks_by_op_ids_empty(patch_session):
    session = patch_session(FakeSession())
    assert await TaskPGManager.list_current_tasks_by_op_ids([]) == []


async def test_list_current_tasks_by_op_ids(patch_session):
    session = patch_session(FakeSession(default=FakeResult(rows=[_task_row()])))
    result = await TaskPGManager.list_current_tasks_by_op_ids(["log-1"])
    assert len(result) == 1
    # filtered variant builds the same result mapping
    result = await TaskPGManager.list_current_tasks_by_op_ids(
        ["log-1"], TaskTypeEnum.KV_CACHE_LOG_PARSE_WORKER
    )
    assert len(result) == 1


async def test_get_current_task_by_op_id_missing(patch_session):
    session = patch_session(FakeSession())
    assert await TaskPGManager.get_current_task_by_op_id("log-1") is None


async def test_get_current_task_by_op_id(patch_session):
    session = patch_session(
        FakeSession(default=FakeResult(scalar_value=_task_row()))
    )
    result = await TaskPGManager.get_current_task_by_op_id("log-1")
    assert result is not None and result.op_id == "log-1"
    result = await TaskPGManager.get_current_task_by_op_id(
        "log-1", TaskTypeEnum.KV_CACHE_LOG_PARSE_WORKER
    )
    assert result is not None


async def test_list_tasks_by_op_id(patch_session):
    session = patch_session(FakeSession(default=FakeResult(rows=[_task_row()])))
    result = await TaskPGManager.list_tasks_by_op_id("log-1")
    assert len(result) == 1


# ---------------------------------------------------------------------------
# TaskReportPGManager
# ---------------------------------------------------------------------------


def _report_model(task_id="t1", **overrides):
    data = dict(task_id=task_id, progress=50.0, message="halfway")
    data.update(overrides)
    return TaskReportModel(**data)


async def test_add_task_report(patch_session):
    session = patch_session(FakeSession())
    assert await TaskReportPGManager.add_task_report(_report_model()) is True
    params = session.executed[0][1]
    assert params[0]["task_id"] == "t1"
    assert params[0]["progress"] == 50.0


async def test_add_task_reports_empty(patch_session):
    session = patch_session(FakeSession())
    assert await TaskReportPGManager.add_task_reports([]) == []


async def test_add_task_reports_returns_task_ids(patch_session):
    session = patch_session(FakeSession())
    ids = await TaskReportPGManager.add_task_reports(
        [_report_model("t1"), _report_model("t2")]
    )
    assert ids == ["t1", "t2"]


async def test_update_task_reports_existed_status(patch_session):
    session = patch_session(FakeSession())
    assert (
        await TaskReportPGManager.update_task_reports_existed_status_by_task_id(
            "t1", 0
        )
        is True
    )
    sql, params = session.executed[0]
    assert "SET existed_status = :existed_status" in sql_text(sql)
    assert params == {"task_id": "t1", "existed_status": False}


async def test_list_task_reports_empty(patch_session):
    session = patch_session(FakeSession())
    assert await TaskReportPGManager.list_task_reports_by_task_ids([]) == []


async def test_list_task_reports_maps_rows(patch_session):
    row = {
        "task_id": "t1",
        "progress": 42.0,
        "message": "msg",
        "existed_status": True,
        "created_at": datetime(2026, 1, 1),
    }
    session = patch_session(FakeSession(default=FakeResult(rows=[row])))
    result = await TaskReportPGManager.list_task_reports_by_task_ids(["t1"])
    assert len(result) == 1
    assert result[0].task_id == "t1"
    assert result[0].progress == 42.0


async def test_delete_task_reports_empty_short_circuits(patch_session):
    session = patch_session(FakeSession())
    assert await TaskReportPGManager.delete_task_reports_by_task_ids([]) is True
    assert session.executed == []


async def test_delete_task_reports_soft_deletes(patch_session):
    session = patch_session(FakeSession())
    assert await TaskReportPGManager.delete_task_reports_by_task_ids(["t1"]) is True
    sql, params = session.executed[0]
    assert "SET existed_status = FALSE" in sql_text(sql)
    assert params == {"task_ids": ["t1"]}


# ---------------------------------------------------------------------------
# BrpcProfilingResultPGManager
# ---------------------------------------------------------------------------


def _profiling_record(**overrides):
    data = dict(
        timestamp=datetime(2026, 1, 1, 0, 0, 0),
        interface_name="iface",
        source_file="prof.log",
        success_count=10,
        failure_count=2,
        total_ns=1000,
        avg_ns=100,
        max_ns=200,
        min_ns=50,
        p50_ns=90,
        p90_ns=120,
        p95_ns=150,
        p99_ns=190,
        p999_ns=200,
    )
    data.update(overrides)
    return BrpcProfilingRecord(**data)


async def test_add_profiling_results_empty_is_noop(patch_session):
    session = patch_session(FakeSession())
    assert await BrpcProfilingResultPGManager.add_profiling_results("log-1", []) is True
    assert session.executed == [] and session.added == []


async def test_add_profiling_results_adds_models(patch_session):
    session = patch_session(FakeSession())
    result = await BrpcProfilingResultPGManager.add_profiling_results(
        "log-1", [_profiling_record(), _profiling_record(interface_name="other")]
    )
    assert result is True
    assert len(session.added) == 2
    assert session.commit_count == 1
    model = session.added[0]
    assert model.log_id == "log-1"
    assert model.source_file == "prof.log"
    assert model.interface_name == "iface"
    assert model.p50_ns == 90
    assert model.id  # uuid generated


async def test_add_profiling_results_reraises_write_failure(patch_session):
    session = patch_session(AddAllErrorSession(RuntimeError("disk full")))
    with pytest.raises(RuntimeError, match="disk full"):
        await BrpcProfilingResultPGManager.add_profiling_results(
            "log-1", [_profiling_record()]
        )


async def test_delete_by_log_id_success(patch_session):
    session = patch_session(FakeSession())
    assert await BrpcProfilingResultPGManager.delete_by_log_id("log-1") is True
    assert "DELETE FROM brpc_profiling_result" in sql_text(session.executed[0][0])


async def test_delete_by_log_id_failure_returns_false(patch_session):
    patch_session(ExecErrorSession())
    assert await BrpcProfilingResultPGManager.delete_by_log_id("log-1") is False


async def test_count_by_log_id(patch_session):
    session = patch_session(FakeSession(default=FakeResult(scalar_value=7)))
    assert await BrpcProfilingResultPGManager.count_by_log_id("log-1") == 7


async def test_count_by_log_id_error_returns_zero(patch_session):
    patch_session(ExecErrorSession())
    assert await BrpcProfilingResultPGManager.count_by_log_id("log-1") == 0


async def test_count_files_by_log_id(patch_session):
    session = patch_session(FakeSession(default=FakeResult(scalar_value=3)))
    assert await BrpcProfilingResultPGManager.count_files_by_log_id("log-1") == 3


async def test_count_files_by_log_id_error_returns_zero(patch_session):
    patch_session(ExecErrorSession())
    assert await BrpcProfilingResultPGManager.count_files_by_log_id("log-1") == 0


async def test_get_file_names_by_log_id(patch_session):
    session = patch_session(
        FakeSession(default=FakeResult(rows=[("a.log",), ("",)]))
    )
    result = await BrpcProfilingResultPGManager.get_file_names_by_log_id("log-1")
    assert result == ["a.log", ""]


async def test_get_file_names_by_log_id_error_returns_empty(patch_session):
    patch_session(ExecErrorSession())
    assert await BrpcProfilingResultPGManager.get_file_names_by_log_id("log-1") == []


async def test_get_timestamps_by_log_id_filters_none(patch_session):
    ts = datetime(2026, 1, 1)
    session = patch_session(FakeSession(default=FakeResult(rows=[(ts,), (None,)])))
    result = await BrpcProfilingResultPGManager.get_timestamps_by_log_id("log-1")
    assert result == [ts]


async def test_get_timestamps_by_log_id_error_returns_empty(patch_session):
    patch_session(ExecErrorSession())
    assert await BrpcProfilingResultPGManager.get_timestamps_by_log_id("log-1") == []


async def test_get_all_by_log_id(patch_session):
    row = SimpleNamespace(id="r1")
    session = patch_session(FakeSession(default=FakeResult(rows=[row])))
    result = await BrpcProfilingResultPGManager.get_all_by_log_id("log-1")
    assert result == [row]
    # source_file filter branch
    result = await BrpcProfilingResultPGManager.get_all_by_log_id(
        "log-1", source_file="a.log"
    )
    assert result == [row]


async def test_get_all_by_log_id_error_returns_empty(patch_session):
    patch_session(ExecErrorSession())
    assert await BrpcProfilingResultPGManager.get_all_by_log_id("log-1") == []


async def test_get_file_options_by_kb_id(patch_session):
    rows = [
        {"log_id": "log-1", "log_name": "a.log", "source_file": "src.log"},
        {"log_id": "log-1", "log_name": "a.log", "source_file": ""},
    ]
    session = patch_session(FakeSession(default=FakeResult(rows=rows)))
    result = await BrpcProfilingResultPGManager.get_file_options_by_kb_id("kb-1")
    assert result == rows


async def test_get_all_by_kb_id(patch_session):
    row = SimpleNamespace(id="r1")
    session = patch_session(FakeSession(default=FakeResult(rows=[row])))
    assert await BrpcProfilingResultPGManager.get_all_by_kb_id("kb-1") == [row]
    result = await BrpcProfilingResultPGManager.get_all_by_kb_id(
        "kb-1", source_file="a.log", log_id="log-1"
    )
    assert result == [row]


async def test_get_by_log_id_and_timestamp(patch_session):
    row = SimpleNamespace(id="r1")
    session = patch_session(FakeSession(default=FakeResult(rows=[row])))
    result = await BrpcProfilingResultPGManager.get_by_log_id_and_timestamp(
        "log-1", datetime(2026, 1, 1)
    )
    assert result == [row]


async def test_get_by_log_id_and_timestamp_error_returns_empty(patch_session):
    patch_session(ExecErrorSession())
    result = await BrpcProfilingResultPGManager.get_by_log_id_and_timestamp(
        "log-1", datetime(2026, 1, 1)
    )
    assert result == []


# ---------------------------------------------------------------------------
# DiagnosisCasePGManager
# ---------------------------------------------------------------------------


def _case_row(case_id="c1", existed=True, **overrides):
    row = SimpleNamespace(
        id=case_id,
        kb_id="kb-1",
        fault_type="latency",
        title="title",
        symptom_summary="summary",
        root_cause="root",
        recommendation="rec",
        confidence=0.9,
        failure_mode_ids=["FM-1"],
        status_codes=["1004"],
        fingerprint_json={"src_ips": ["10.0.0.1"]},
        evidence_refs_json=[],
        counter_evidence_json=[],
        source_log_ids=["log-1"],
        hit_count=3,
        existed_status=existed,
        first_seen_at=datetime(2026, 1, 1),
        last_seen_at=datetime(2026, 1, 2),
        created_at=datetime(2026, 1, 1),
        updated_at=datetime(2026, 1, 3),
    )
    for key, value in overrides.items():
        setattr(row, key, value)
    return row


def _case_model(case_id="case-1", **overrides):
    data = dict(
        id=case_id,
        kb_id="kb-1",
        fault_type="latency",
        symptom_summary="summary",
        root_cause="root",
        recommendation="rec",
        confidence=0.8,
    )
    data.update(overrides)
    return DiagnosisCaseModel(**data)


async def test_add_case_inserts_case_and_signals(patch_session):
    session = patch_session(FakeSession())
    case = _case_model(
        status_codes=["1004"],
        failure_mode_ids=["FM-1"],
        source_log_ids=["log-1"],
        fingerprint_json={"src_ips": ["10.0.0.1"], "hosts": ["host-a"]},
    )
    case_id = await DiagnosisCasePGManager.add_case(case)
    assert case_id == "case-1"
    # insert case, delete old signals, insert new signals
    assert len(session.executed) == 3
    delete_sql, delete_params = session.executed[1]
    assert sql_text(delete_sql) == (
        "DELETE FROM diagnosis_case_signal WHERE case_id = :case_id"
    )
    assert delete_params == {"case_id": "case-1"}


async def test_add_case_without_signals_skips_signal_insert(patch_session):
    session = patch_session(FakeSession())
    case_id = await DiagnosisCasePGManager.add_case(_case_model())
    assert case_id == "case-1"
    assert len(session.executed) == 2


async def test_get_case_missing_returns_none(patch_session):
    session = patch_session(FakeSession())
    assert await DiagnosisCasePGManager.get_case("missing") is None


async def test_get_case_inactive_returns_none(patch_session):
    session = patch_session(FakeSession())
    session.get_rows["c1"] = _case_row(existed=False)
    assert await DiagnosisCasePGManager.get_case("c1") is None


async def test_get_case_maps_row(patch_session):
    session = patch_session(FakeSession())
    session.get_rows["c1"] = _case_row()
    result = await DiagnosisCasePGManager.get_case("c1")
    assert result is not None
    assert result.id == "c1"
    assert result.fault_type == "latency"
    assert result.status_codes == ["1004"]
    assert result.created_at  # formatted string


async def test_mark_case_hit_true(patch_session):
    session = patch_session(FakeSession(default=FakeResult(rowcount=1)))
    assert await DiagnosisCasePGManager.mark_case_hit("c1") is True


async def test_mark_case_hit_false(patch_session):
    session = patch_session(FakeSession(default=FakeResult(rowcount=0)))
    assert await DiagnosisCasePGManager.mark_case_hit("c1") is False


async def test_search_cases_no_rows(patch_session):
    session = patch_session(FakeSession(default=FakeResult(rows=[])))
    total, matches = await DiagnosisCasePGManager.search_cases(
        SearchDiagnosisCasesRequest(kb_id="kb-1")
    )
    assert total == 0 and matches == []


async def test_search_cases_without_query_signals_paginates(patch_session):
    session = patch_session(
        FakeSession(default=FakeResult(rows=[_case_row("c1"), _case_row("c2")]))
    )
    req = SearchDiagnosisCasesRequest(kb_id="kb-1", page_num=2, page_cnt=1)
    total, matches = await DiagnosisCasePGManager.search_cases(req)
    assert total == 2
    assert len(matches) == 1
    assert matches[0].match_score == 0.0
    assert matches[0].matched_signals == []


async def test_search_cases_scores_matching_signals(patch_session):
    case_row = _case_row("c1", confidence=0.9, hit_count=1)
    signal_rows = [
        SimpleNamespace(case_id="c1", signal_type="status_code", signal_value="1004", weight=3.0),
        SimpleNamespace(case_id="c1", signal_type="src_ip", signal_value="10.0.0.1", weight=1.0),
        SimpleNamespace(case_id="c1", signal_type="status_code", signal_value="9999", weight=3.0),
    ]
    session = patch_session(
        FakeSession(
            results=[
                FakeResult(rows=[case_row]),
                FakeResult(rows=signal_rows),
            ]
        )
    )
    req = SearchDiagnosisCasesRequest(
        kb_id="kb-1", status_codes=["1004"], src_ips=["10.0.0.1"]
    )
    total, matches = await DiagnosisCasePGManager.search_cases(req)
    assert total == 1
    match = matches[0]
    # min(3.0, 3.0) + min(1.0, 1.5) = 4.0; the unmatched signal is ignored
    assert match.match_score == pytest.approx(4.0)
    assert len(match.matched_signals) == 2


async def test_search_cases_sorts_by_score_descending(patch_session):
    signal_rows = [
        SimpleNamespace(case_id="c1", signal_type="status_code", signal_value="1004", weight=3.0),
        SimpleNamespace(case_id="c2", signal_type="src_ip", signal_value="10.0.0.1", weight=1.0),
    ]
    session = patch_session(
        FakeSession(
            results=[
                FakeResult(rows=[_case_row("c1"), _case_row("c2")]),
                FakeResult(rows=signal_rows),
            ]
        )
    )
    req = SearchDiagnosisCasesRequest(
        kb_id="kb-1", status_codes=["1004"], src_ips=["10.0.0.1"]
    )
    total, matches = await DiagnosisCasePGManager.search_cases(req)
    assert total == 2
    assert matches[0].case.id == "c1"
    assert matches[0].match_score > matches[1].match_score


# ---------------------------------------------------------------------------
# LogFilePGManager
# ---------------------------------------------------------------------------

from latency.ENUM.general import DiagnosisConfigLogType


def _log_file_model(**overrides):
    data = dict(
        id="lf-1",
        kb_id="kb-1",
        name="app.log",
        file_path="/data/app.log",
        file_size=1024,
        created_at="2026-01-01T00:30:00.123+00:00",
    )
    data.update(overrides)
    return LogFileModel(**data)


def _log_file_row(**overrides):
    row = SimpleNamespace(
        id="lf-1",
        kb_id="kb-1",
        name="app.log",
        file_path="/data/app.log",
        size=1024,
        anomalous_count=2,
        failure_count=None,
        log_type=DiagnosisConfigLogType.KVCACHE,
        existed_status=True,
        created_at=datetime(2026, 1, 1, 8, 30, 0, 123000),
    )
    for key, value in overrides.items():
        setattr(row, key, value)
    return row


async def test_add_log_file_executes_insert(patch_session):
    session = patch_session(FakeSession())
    assert await LogFilePGManager.add_log_file(_log_file_model()) is True
    assert len(session.executed) == 1
    params = session.executed[0][1]
    assert isinstance(params, list)
    mapping = params[0]
    assert mapping["id"] == "lf-1"
    assert mapping["size"] == 1024
    assert mapping["total_count"] == 0
    assert mapping["anomalous_count"] == 0
    assert mapping["failure_count"] == 0
    assert mapping["existed_status"] is True
    assert mapping["created_at"].tzinfo is not None


async def test_add_log_files_empty_returns_empty(patch_session):
    session = patch_session(FakeSession())
    assert await LogFilePGManager.add_log_files([]) == []
    assert session.executed == []


async def test_add_log_files_returns_ids(patch_session):
    session = patch_session(FakeSession())
    ids = await LogFilePGManager.add_log_files(
        [_log_file_model(id="lf-1"), _log_file_model(id="lf-2")]
    )
    assert ids == ["lf-1", "lf-2"]
    assert len(session.executed[0][1]) == 2


async def test_delete_log_file_by_id_rowcount_zero(patch_session):
    session = patch_session(FakeSession())
    assert await LogFilePGManager.delete_log_file_by_log_file_id("lf-1") is False
    sql, params = session.executed[0]
    assert sql_text(sql) == "DELETE FROM log_file WHERE id = :id"
    assert params == {"id": "lf-1"}


async def test_delete_log_file_by_id_rowcount_positive(patch_session):
    session = patch_session(FakeSession(default=FakeResult(rowcount=3)))
    assert await LogFilePGManager.delete_log_file_by_log_file_id("lf-1") is True


async def test_update_log_file_unknown_keys_only(patch_session):
    session = patch_session(FakeSession())
    count = await LogFilePGManager.update_log_file("lf-1", {"bogus": 1})
    assert count == 0
    assert session.executed == []


async def test_update_log_file_builds_set_clause(patch_session):
    session = patch_session(FakeSession(default=FakeResult(rowcount=1)))
    count = await LogFilePGManager.update_log_file(
        "lf-1",
        {"name": "new.log", "created_at": "2026-01-02T00:00:00+00:00", "bogus": 2},
    )
    assert count == 1
    sql, params = session.executed[0]
    sql = sql_text(sql)
    assert sql.startswith("UPDATE log_file SET name = :name, created_at = :created_at")
    assert sql.endswith("updated_at = :server_updated_at WHERE id = :id")
    assert params["id"] == "lf-1"
    assert params["name"] == "new.log"
    assert isinstance(params["created_at"], datetime)
    assert "server_updated_at" in params


async def test_list_log_files_maps_rows(patch_session):
    session = patch_session(
        FakeSession(
            results=[FakeResult(scalar_value=7)],
            default=FakeResult(rows=[_log_file_row()]),
        )
    )
    total, files = await LogFilePGManager.list_log_files(
        "kb-1", ListLogFilesRequest()
    )
    assert total == 7
    assert len(files) == 1
    model = files[0]
    assert model.id == "lf-1"
    assert model.kb_id == "kb-1"
    assert model.file_size == 1024
    assert model.anomaly_cnt == 2
    assert model.trace_failure_event_cnt == 0  # failure_count None -> 0
    assert model.log_type == DiagnosisConfigLogType.KVCACHE
    assert model.created_at == "2026-01-01 08:30:00.123"


async def test_list_log_files_empty(patch_session):
    session = patch_session(
        FakeSession(
            results=[FakeResult(scalar_value=0)], default=FakeResult(rows=[])
        )
    )
    total, files = await LogFilePGManager.list_log_files(
        "kb-1", ListLogFilesRequest()
    )
    assert (total, files) == (0, [])
    assert len(session.executed) == 2


async def test_list_log_files_filters_and_ascending_order(patch_session):
    session = patch_session(
        FakeSession(
            results=[FakeResult(scalar_value=1)], default=FakeResult(rows=[])
        )
    )
    req = ListLogFilesRequest(
        name="app",
        created_at_start="2026-01-01 00:00:00",
        created_at_end="2026-02-01 00:00:00",
        created_sorted_desc=False,
        page_num=2,
        page_cnt=5,
    )
    await LogFilePGManager.list_log_files("kb-1", req)
    assert len(session.executed) == 2
    sql = sql_text(session.executed[1][0])
    assert "lower(log_file.name) LIKE" in sql
    order_part = sql.split("ORDER BY", 1)[1]
    assert "DESC" not in order_part


async def test_list_log_files_descending_order(patch_session):
    session = patch_session(
        FakeSession(
            results=[FakeResult(scalar_value=0)], default=FakeResult(rows=[])
        )
    )
    await LogFilePGManager.list_log_files(
        "kb-1", ListLogFilesRequest(created_sorted_desc=True)
    )
    order_part = sql_text(session.executed[1][0]).split("ORDER BY", 1)[1]
    assert "DESC" in order_part


async def test_get_log_file_by_id_missing(patch_session):
    patch_session(FakeSession(default=FakeResult(scalar_value=None)))
    assert await LogFilePGManager.get_log_file_by_log_file_id("lf-x") is None


async def test_get_log_file_by_id_maps_row(patch_session):
    patch_session(
        FakeSession(default=FakeResult(scalar_value=_log_file_row()))
    )
    model = await LogFilePGManager.get_log_file_by_log_file_id("lf-1")
    assert model is not None
    assert model.file_size == 1024
    assert model.anomaly_cnt == 2


async def test_list_log_file_ids_with_filters(patch_session):
    session = patch_session(
        FakeSession(default=FakeResult(rows=["lf-2", "lf-1"]))
    )
    ids = await LogFilePGManager.list_log_file_ids(kb_id="kb-1", log_id="lf-2")
    assert ids == ["lf-2", "lf-1"]
    sql = sql_text(session.executed[0][0])
    assert "log_file.kb_id =" in sql
    assert "log_file.id =" in sql


async def test_list_log_file_ids_without_filters(patch_session):
    patch_session(FakeSession(default=FakeResult(rows=[])))
    assert await LogFilePGManager.list_log_file_ids() == []


async def test_list_log_file_paths(patch_session):
    session = patch_session(
        FakeSession(
            default=FakeResult(
                rows=[
                    {"id": "lf-1", "file_path": "/a"},
                    {"id": "lf-2", "file_path": "/b"},
                ]
            )
        )
    )
    paths = await LogFilePGManager.list_log_file_paths(kb_id="kb-1")
    assert paths == [("lf-1", "/a"), ("lf-2", "/b")]


# ---------------------------------------------------------------------------
# LogKnowledgePGManager
# ---------------------------------------------------------------------------


def _log_kb_model(**overrides):
    data = dict(
        id="kb-1",
        name="asset-kb",
        description="desc",
        task_cnt=3,
        anomaly_cnt=1,
        created_at="2026-01-01T00:30:00.123+00:00",
        updated_at="2026-01-01T00:30:00.123+00:00",
    )
    data.update(overrides)
    return LogKnowledgeModel(**data)


def _log_kb_row(**overrides):
    row = SimpleNamespace(
        id="kb-1",
        name="asset-kb",
        description="desc",
        image_bytes=None,
        total_count=3,
        anomalous_count=1,
        existed_status=True,
        created_at=datetime(2026, 1, 1, 8, 30, 0, 123000),
        updated_at=datetime(2026, 1, 1, 8, 30, 0, 123000),
    )
    for key, value in overrides.items():
        setattr(row, key, value)
    return row


async def test_kb_exists_true(patch_session):
    patch_session(FakeSession(default=FakeResult(scalar_value="kb-1")))
    assert await LogKnowledgePGManager.exists("kb-1") is True


async def test_kb_exists_false(patch_session):
    patch_session(FakeSession(default=FakeResult(scalar_value=None)))
    assert await LogKnowledgePGManager.exists("kb-x") is False


async def test_add_log_kb_locks_checks_then_inserts(patch_session):
    session = patch_session(FakeSession())
    result = await LogKnowledgePGManager.add_log_kb(_log_kb_model())
    assert result == "kb-1"
    assert len(session.executed) == 3
    assert "pg_advisory_xact_lock" in sql_text(session.executed[0][0])
    insert_sql = sql_text(session.executed[2][0])
    assert insert_sql.startswith("INSERT INTO log_knowledge")
    params = session.executed[2][1]
    assert params[0]["name"] == "asset-kb"
    assert params[0]["total_count"] == 3
    assert params[0]["anomalous_count"] == 1


async def test_add_log_kb_duplicate_active_name_returns_none(patch_session):
    session = patch_session(
        FakeSession(
            results=[FakeResult(), FakeResult(scalar_value="kb-existing")]
        )
    )
    result = await LogKnowledgePGManager.add_log_kb(
        _log_kb_model(name="taken")
    )
    assert result is None
    assert len(session.executed) == 2  # lock + existence check, no insert
    assert "pg_advisory_xact_lock" in sql_text(session.executed[0][0])


async def test_add_log_kb_without_name_skips_lock(patch_session):
    session = patch_session(FakeSession())
    model = LogKnowledgeModel.model_construct(
        id="kb-anon",
        name=None,
        description="d",
        image_bytes=None,
        task_cnt=0,
        log_file_cnt=0,
        anomaly_cnt=0,
        existed_status=True,
        created_at="2026-01-01T00:30:00.123+00:00",
        updated_at="2026-01-01T00:30:00.123+00:00",
    )
    assert await LogKnowledgePGManager.add_log_kb(model) == "kb-anon"
    assert len(session.executed) == 1  # straight insert
    assert sql_text(session.executed[0][0]).startswith("INSERT INTO log_knowledge")


async def test_add_log_kb_with_explicit_session():
    session = FakeSession()
    result = await LogKnowledgePGManager.add_log_kb(_log_kb_model(), session=session)
    assert result == "kb-1"
    assert len(session.executed) == 3
    assert sql_text(session.executed[2][0]).startswith("INSERT INTO log_knowledge")


async def test_add_log_kbs_empty_returns_empty(patch_session):
    session = patch_session(FakeSession())
    assert await LogKnowledgePGManager.add_log_kbs([]) == []
    assert session.executed == []


async def test_add_log_kbs_returns_ids(patch_session):
    session = patch_session(FakeSession())
    ids = await LogKnowledgePGManager.add_log_kbs(
        [_log_kb_model(id="kb-1"), _log_kb_model(id="kb-2")]
    )
    assert ids == ["kb-1", "kb-2"]
    assert len(session.executed) == 1


async def test_delete_log_kb_by_kb_id(patch_session):
    session = patch_session(FakeSession())
    assert await LogKnowledgePGManager.delete_log_kb_by_kb_id("kb-1") is True
    sql, params = session.executed[0]
    assert sql_text(sql) == "DELETE FROM log_knowledge WHERE id = :id"
    assert params == {"id": "kb-1"}


async def test_update_log_kb_unknown_keys_only(patch_session):
    session = patch_session(FakeSession())
    assert await LogKnowledgePGManager.update_log_kb("kb-1", {"nope": 1}) == 0
    assert session.executed == []


async def test_update_log_kb_builds_set_clause(patch_session):
    session = patch_session(FakeSession(default=FakeResult(rowcount=1)))
    count = await LogKnowledgePGManager.update_log_kb(
        "kb-1", {"name": "renamed", "bogus": 3}
    )
    assert count == 1
    sql, params = session.executed[0]
    sql = sql_text(sql)
    assert sql == (
        "UPDATE log_knowledge SET name = :name, updated_at = :server_updated_at "
        "WHERE id = :id"
    )
    assert params["name"] == "renamed"
    assert params["id"] == "kb-1"


async def test_touch_log_kb(patch_session):
    session = patch_session(FakeSession(default=FakeResult(rowcount=1)))
    assert await LogKnowledgePGManager.touch_log_kb("kb-1") == 1
    sql, params = session.executed[0]
    assert sql_text(sql) == (
        "UPDATE log_knowledge SET updated_at = :server_updated_at WHERE id = :id"
    )
    assert params["id"] == "kb-1"


async def test_refresh_kb_counters_with_session():
    session = FakeSession(default=FakeResult(rowcount=1))
    assert await LogKnowledgePGManager.refresh_kb_counters("kb-1", session=session) == 1
    sql, params = session.executed[0]
    assert "UPDATE log_knowledge AS kb" in sql_text(sql)
    assert params["kb_id"] == "kb-1"


async def test_count_log_kbs_with_filters(patch_session):
    session = patch_session(FakeSession(default=FakeResult(scalar_value=5)))
    req = ListLogKnowledgeRequest(
        name="asset",
        description="desc",
        created_at_start="2026-01-01 00:00:00",
        created_at_end="2026-02-01 00:00:00",
    )
    assert await LogKnowledgePGManager.count_log_kbs(req) == 5
    sql = sql_text(session.executed[0][0])
    assert "count" in sql
    assert "log_knowledge.existed_status" in sql


async def test_count_log_kbs_none_scalar_returns_zero(patch_session):
    patch_session(FakeSession(default=FakeResult(scalar_value=None)))
    assert await LogKnowledgePGManager.count_log_kbs(ListLogKnowledgeRequest()) == 0


async def test_list_log_kbs_maps_rows(patch_session):
    session = patch_session(
        FakeSession(
            default=FakeResult(
                rows=[
                    {
                        "id": "kb-1",
                        "name": "asset-kb",
                        "description": "desc",
                        "total_count": 3,
                        "anomalous_count": 1,
                        "existed_status": True,
                        "created_at": datetime(2026, 1, 1, 8, 30, 0, 123000),
                        "updated_at": datetime(2026, 1, 2, 8, 30, 0, 123000),
                    }
                ]
            )
        )
    )
    kbs = await LogKnowledgePGManager.list_log_kbs(ListLogKnowledgeRequest())
    assert len(kbs) == 1
    model = kbs[0]
    assert model.id == "kb-1"
    assert model.task_cnt == 3
    assert model.log_file_cnt == 0
    assert model.anomaly_cnt == 1
    assert model.created_at == "2026-01-01 08:30:00.123"
    assert model.updated_at == "2026-01-02 08:30:00.123"


async def test_list_log_kbs_empty(patch_session):
    patch_session(FakeSession(default=FakeResult(rows=[])))
    assert await LogKnowledgePGManager.list_log_kbs(ListLogKnowledgeRequest()) == []


async def test_get_log_kb_missing_returns_none(patch_session):
    patch_session(FakeSession(default=FakeResult(scalar_value=None)))
    assert await LogKnowledgePGManager.get_log_kb_by_kb_id("kb-x") is None


async def test_get_log_kb_maps_row(patch_session):
    patch_session(FakeSession(default=FakeResult(scalar_value=_log_kb_row())))
    model = await LogKnowledgePGManager.get_log_kb_by_kb_id("kb-1")
    assert model is not None
    assert model.task_cnt == 3
    assert model.anomaly_cnt == 1
    assert model.name == "asset-kb"


# ---------------------------------------------------------------------------
# AnomalousEventPGManager
# ---------------------------------------------------------------------------

from latency.schemas.parse_config import SortField


def _event_dataclass(event_id="evt-1", **overrides):
    data = dict(
        id=event_id,
        log_id="log-1",
        aggregated_event_id="agg-1",
        start_log_parse_offset=0,
        end_log_parse_offset=10,
        anomaly_reason="latency spike",
        existed_status=True,
        created_at="2026-01-01 08:30:00.123",
    )
    data.update(overrides)
    return AnomalousEventDataclass(**data)


def _event_row_dict(event_id="evt-1"):
    return {
        "id": event_id,
        "log_id": "log-1",
        "aggregated_event_id": "agg-1",
        "start_log_parse_offset": 0,
        "end_log_parse_offset": 10,
        "anomaly_reason": "latency spike",
        "existed_status": True,
        "created_at": datetime(2026, 1, 1, 8, 30, 0, 123000),
    }


class FakeAsyncpgConn:
    """asyncpg connection double recording COPY calls."""

    def __init__(self):
        self.copies = []

    async def copy_records_to_table(self, table_name, records=None, columns=None):
        self.copies.append((table_name, list(records), list(columns)))


class FakeCopyConnection:
    def __init__(self, driver):
        self.driver = driver

    async def get_raw_connection(self):
        return SimpleNamespace(driver_connection=self.driver)


@pytest.fixture()
def patch_connection(monkeypatch):
    """Factory fixture patching PGManager.connection to yield a fake conn."""

    def _patch(conn):
        @asynccontextmanager
        async def _ctx():
            yield conn

        monkeypatch.setattr(PGManager, "connection", _ctx)
        return conn

    return _patch


async def test_add_anomalous_event_executes_insert(patch_session):
    session = patch_session(FakeSession())
    event = AnomalousEventModel(
        id="evt-1", log_id="log-1", anomaly_reason="spike"
    )
    assert await AnomalousEventPGManager.add_anomalous_event(event) is True
    assert len(session.executed) == 1
    params = session.executed[0][1]
    assert params[0]["id"] == "evt-1"
    assert params[0]["anomaly_reason"] == "spike"
    assert params[0]["existed_status"] is True


async def test_add_anomalous_events_empty_returns_empty(patch_session):
    session = patch_session(FakeSession())
    assert await AnomalousEventPGManager.add_anomalous_events([]) == []
    assert session.executed == []


async def test_add_anomalous_events_inserts_per_batch(patch_session):
    session = patch_session(FakeSession())
    events = [_event_dataclass("e1"), _event_dataclass("e2"), _event_dataclass("e3")]
    ids = await AnomalousEventPGManager.add_anomalous_events(events, batch_size=2)
    assert ids == ["e1", "e2", "e3"]
    assert len(session.executed) == 2
    assert len(session.executed[0][1]) == 2
    assert len(session.executed[1][1]) == 1


async def test_add_anomalous_events_uses_copy_above_threshold(patch_connection):
    driver = FakeAsyncpgConn()
    patch_connection(FakeCopyConnection(driver))
    events = [_event_dataclass(f"e{i}") for i in range(1000)]
    ids = await AnomalousEventPGManager.add_anomalous_events(events)
    assert ids == [f"e{i}" for i in range(1000)]
    assert len(driver.copies) == 1
    table, records, columns = driver.copies[0]
    assert table == "anomalous_event"
    assert columns == AnomalousEventPGManager._COPY_COLUMNS
    assert len(records) == 1000
    assert records[0][0] == "e0"
    assert records[0][1] == "log-1"
    assert records[0][5] == "latency spike"


async def test_delete_anomalous_events_by_log_id(patch_session):
    session = patch_session(FakeSession())
    assert await AnomalousEventPGManager.delete_anomalous_events_by_log_id("log-1") is True
    sql, params = session.executed[0]
    assert sql_text(sql) == "DELETE FROM anomalous_event WHERE log_id = :log_id"
    assert params == {"log_id": "log-1"}


async def test_update_anomalous_events_existed_status(patch_session):
    session = patch_session(FakeSession())
    result = await AnomalousEventPGManager.update_anomalous_events_existed_status_by_log_id(
        "log-1", 0
    )
    assert result is True
    sql, params = session.executed[0]
    assert sql_text(sql) == (
        "UPDATE anomalous_event SET existed_status = :existed_status "
        "WHERE log_id = :log_id"
    )
    assert params == {"log_id": "log-1", "existed_status": False}


async def test_list_anomalous_events_by_log_id_maps_rows(patch_session):
    patch_session(FakeSession(default=FakeResult(rows=[_event_row_dict()])))
    events = await AnomalousEventPGManager.list_anomalous_events_by_log_id("log-1")
    assert len(events) == 1
    assert events[0].id == "evt-1"
    assert events[0].anomaly_reason == "latency spike"
    assert events[0].created_at == "2026-01-01 08:30:00.123"


async def test_list_anomalous_events_by_log_id_empty(patch_session):
    patch_session(FakeSession(default=FakeResult(rows=[])))
    assert await AnomalousEventPGManager.list_anomalous_events_by_log_id("log-x") == []


async def test_get_anomalous_event_by_id_missing(patch_session):
    patch_session(FakeSession(default=FakeResult(rows=[])))
    assert await AnomalousEventPGManager.get_anomalous_event_by_id("evt-x") is None


async def test_get_anomalous_event_by_id_found(patch_session):
    patch_session(FakeSession(default=FakeResult(rows=[_event_row_dict()])))
    event = await AnomalousEventPGManager.get_anomalous_event_by_id("evt-1")
    assert event is not None
    assert event.aggregated_event_id == "agg-1"


async def test_list_anomalous_events_default_order(patch_session):
    session = patch_session(
        FakeSession(
            results=[FakeResult(scalar_value=2)],
            default=FakeResult(rows=[_event_row_dict("e1"), _event_row_dict("e2")]),
        )
    )
    req = ListAnomalousEventRequest(kb_id="kb-1")
    total, events = await AnomalousEventPGManager.list_anomalous_events(req)
    assert total == 2
    assert [e.id for e in events] == ["e1", "e2"]
    sql = sql_text(session.executed[1][0])
    assert "ORDER BY anomalous_event.created_at DESC" in sql


async def test_list_anomalous_events_filters_and_custom_sort(patch_session):
    session = patch_session(
        FakeSession(
            results=[FakeResult(scalar_value=0)], default=FakeResult(rows=[])
        )
    )
    req = ListAnomalousEventRequest(
        kb_id="kb-1",
        log_id="log-1",
        aggregated_event_id="agg-1",
        sort_fields=[
            SortField(field="anomaly_reason", order="asc"),
            SortField(field="bogus_field", order="desc"),
        ],
    )
    total, events = await AnomalousEventPGManager.list_anomalous_events(req)
    assert (total, events) == (0, [])
    sql = sql_text(session.executed[1][0])
    assert "JOIN log_file" in sql
    order_part = sql.split("ORDER BY", 1)[1]
    assert "anomalous_event.anomaly_reason" in order_part
    assert "DESC" not in order_part
    assert "bogus_field" not in sql


# ---------------------------------------------------------------------------
# AnomalousEventChainPGManager
# ---------------------------------------------------------------------------


def _chain_model(chain_id="ch-1", **overrides):
    data = dict(
        id=chain_id,
        log_id="log-1",
        anomalous_event_id="evt-1",
        name="chain",
        description="chain desc",
        anomaly_code="E001",
        offset=2,
        existed_status=True,
        created_at="2026-01-01 08:30:00.123",
    )
    data.update(overrides)
    return AnomalousEventChainModel(**data)


def _chain_row(**overrides):
    row = SimpleNamespace(
        id="ch-1",
        log_id="log-1",
        anomalous_event_id="evt-1",
        name="chain",
        description="chain desc",
        anomaly_code="E001",
        offset=2,
        existed_status=True,
        created_at=datetime(2026, 1, 1, 8, 30, 0, 123000),
    )
    for key, value in overrides.items():
        setattr(row, key, value)
    return row


async def test_add_event_chains_empty_returns_empty(patch_session):
    session = patch_session(FakeSession())
    assert await AnomalousEventChainPGManager.add_event_chains([]) == []
    assert session.executed == []


async def test_add_event_chains_inserts_mappings(patch_session):
    session = patch_session(FakeSession())
    ids = await AnomalousEventChainPGManager.add_event_chains(
        [_chain_model("ch-1"), _chain_model("ch-2")]
    )
    assert ids == ["ch-1", "ch-2"]
    assert len(session.executed) == 1
    params = session.executed[0][1]
    assert params[0]["anomaly_code"] == "E001"
    assert params[0]["offset"] == 2


async def test_add_event_chains_uses_copy_above_threshold(patch_connection):
    driver = FakeAsyncpgConn()
    patch_connection(FakeCopyConnection(driver))
    chains = [_chain_model(f"ch{i}") for i in range(1000)]
    ids = await AnomalousEventChainPGManager.add_event_chains(chains)
    assert ids == [f"ch{i}" for i in range(1000)]
    assert len(driver.copies) == 1
    table, records, columns = driver.copies[0]
    assert table == "anomalous_event_chain"
    assert columns == AnomalousEventChainPGManager._COPY_COLUMNS
    assert len(records) == 1000
    assert records[0][3] == "chain"


async def test_update_event_chains_existed_status(patch_session):
    session = patch_session(FakeSession())
    result = await AnomalousEventChainPGManager.update_event_chains_existed_status_by_log_id(
        "log-1", 1
    )
    assert result is True
    sql, params = session.executed[0]
    assert sql_text(sql) == (
        "UPDATE anomalous_event_chain SET existed_status = :existed_status "
        "WHERE log_id = :log_id"
    )
    assert params == {"log_id": "log-1", "existed_status": True}


async def test_delete_event_chains_by_log_id(patch_session):
    session = patch_session(FakeSession())
    assert await AnomalousEventChainPGManager.delete_event_chains_by_log_id("log-1") is True
    sql, params = session.executed[0]
    assert sql_text(sql) == "DELETE FROM anomalous_event_chain WHERE log_id = :log_id"


async def test_list_event_chains_with_kb_join(patch_session):
    session = patch_session(
        FakeSession(
            results=[FakeResult(scalar_value=2)],
            default=FakeResult(rows=[_chain_row(), _chain_row(id="ch-2")]),
        )
    )
    req = ListAnomalousEventChainRequest(kb_id="kb-1", log_id="log-1")
    total, chains = await AnomalousEventChainPGManager.list_event_chains(req)
    assert total == 2
    assert [c.id for c in chains] == ["ch-1", "ch-2"]
    assert chains[0].anomaly_code == "E001"
    sql = sql_text(session.executed[1][0])
    assert "JOIN log_file" in sql


async def test_list_event_chains_empty(patch_session):
    session = patch_session(
        FakeSession(
            results=[FakeResult(scalar_value=0)], default=FakeResult(rows=[])
        )
    )
    req = ListAnomalousEventChainRequest(kb_id="kb-1")
    assert await AnomalousEventChainPGManager.list_event_chains(req) == (0, [])
    assert len(session.executed) == 2


async def test_list_event_chains_by_log_id_maps_rows(patch_session):
    patch_session(FakeSession(default=FakeResult(rows=[_chain_row()])))
    chains = await AnomalousEventChainPGManager.list_event_chains_by_log_id("log-1")
    assert len(chains) == 1
    assert chains[0].id == "ch-1"
    assert chains[0].description == "chain desc"


async def test_get_event_chain_by_id_missing(patch_session):
    patch_session(FakeSession(default=FakeResult(scalar_value=None)))
    assert await AnomalousEventChainPGManager.get_event_chain_by_id("ch-x") is None


async def test_get_event_chain_by_id_found(patch_session):
    patch_session(FakeSession(default=FakeResult(scalar_value=_chain_row())))
    chain = await AnomalousEventChainPGManager.get_event_chain_by_id("ch-1")
    assert chain is not None
    assert chain.offset == 2


# ---------------------------------------------------------------------------
# FailureModeKnowledgePGManager
# ---------------------------------------------------------------------------


def _status_code_item(code="1004", **overrides):
    data = dict(status_code=code, symptom="symptom", root_cause="root cause")
    data.update(overrides)
    return StatusCodeKnowledgeModel(**data)


def _failure_mode_item(mode_id="FM-1", **overrides):
    data = dict(
        id=mode_id,
        name="mode",
        symptom="symptom",
        root_cause="root cause",
        solution="solution",
        failure_domain="domain",
        children_failure_mode_ids="",
        error_code=None,
    )
    data.update(overrides)
    return FailureModeModel(**data)


async def test_get_status_code_knowledge_missing(patch_session):
    session = patch_session(FakeSession())
    assert await FailureModeKnowledgePGManager.get_status_code_knowledge("404") is None
    assert session.get_rows == {}


async def test_get_status_code_knowledge_maps_row(patch_session):
    session = patch_session(FakeSession())
    session.get_rows["1004"] = SimpleNamespace(
        status_code="1004", symptom=None, root_cause="rc"
    )
    model = await FailureModeKnowledgePGManager.get_status_code_knowledge("1004")
    assert model.status_code == "1004"
    assert model.symptom == ""
    assert model.root_cause == "rc"


async def test_add_status_code_knowledge_empty(patch_session):
    session = patch_session(FakeSession())
    assert await FailureModeKnowledgePGManager.add_status_code_knowledge([]) == []
    assert session.executed == []


async def test_add_status_code_knowledge_upserts(patch_session):
    session = patch_session(FakeSession())
    ids = await FailureModeKnowledgePGManager.add_status_code_knowledge(
        [_status_code_item("1004"), _status_code_item("1005")]
    )
    assert ids == ["1004", "1005"]
    sql = sql_text(session.executed[0][0])
    assert sql.startswith("INSERT INTO status_code_knowledge")
    assert "ON CONFLICT (status_code) DO UPDATE" in sql


async def test_get_failure_mode_by_id_missing(patch_session):
    patch_session(FakeSession())
    assert await FailureModeKnowledgePGManager.get_failure_mode_by_id("FM-x") is None


async def test_get_failure_mode_by_id_maps_row(patch_session):
    session = patch_session(FakeSession())
    session.get_rows["FM-1"] = SimpleNamespace(
        id="FM-1",
        name=None,
        symptom=None,
        root_cause=None,
        solution="sol",
        failure_domain=None,
        children_failure_mode_ids=None,
        error_code=None,
    )
    model = await FailureModeKnowledgePGManager.get_failure_mode_by_id("FM-1")
    assert model.id == "FM-1"
    assert model.name == ""
    assert model.solution == "sol"
    assert model.children_failure_mode_ids == ""
    assert model.error_code is None


async def test_get_all_failure_modes(patch_session):
    patch_session(
        FakeSession(
            default=FakeResult(
                rows=[
                    SimpleNamespace(
                        id="FM-1", name="a", symptom="s", root_cause="r",
                        solution="so", failure_domain="d",
                        children_failure_mode_ids="", error_code="E1",
                    ),
                    SimpleNamespace(
                        id="FM-2", name="b", symptom="s", root_cause="r",
                        solution="so", failure_domain="d",
                        children_failure_mode_ids="", error_code=None,
                    ),
                ]
            )
        )
    )
    modes = await FailureModeKnowledgePGManager.get_all_failure_modes()
    assert set(modes) == {"FM-1", "FM-2"}
    assert modes["FM-1"].error_code == "E1"
    assert modes["FM-2"].name == "b"


async def test_add_failure_mode_knowledge_empty(patch_session):
    session = patch_session(FakeSession())
    assert await FailureModeKnowledgePGManager.add_failure_mode_knowledge([]) == []
    assert session.executed == []


async def test_add_failure_mode_knowledge_upserts(patch_session):
    session = patch_session(FakeSession())
    ids = await FailureModeKnowledgePGManager.add_failure_mode_knowledge(
        [_failure_mode_item("FM-1"), _failure_mode_item("FM-2")]
    )
    assert ids == ["FM-1", "FM-2"]
    sql = sql_text(session.executed[0][0])
    assert sql.startswith("INSERT INTO failure_mode_knowledge")
    assert "ON CONFLICT (id) DO UPDATE" in sql


# ---------------------------------------------------------------------------
# ResourceIdPGManager
# ---------------------------------------------------------------------------


def test_unique_preserves_first_occurrence_order():
    assert ResourceIdPGManager._unique(["a", "b", "a", "c", "b"]) == ["a", "b", "c"]


async def test_find_missing_empty_values(patch_session):
    session = patch_session(FakeSession())
    assert await ResourceIdPGManager.find_missing("kb", []) == []
    assert session.executed == []


async def test_find_missing_reports_absent_kb(patch_session):
    session = patch_session(FakeSession(default=FakeResult(rows=["kb-1"])))
    missing = await ResourceIdPGManager.find_missing("kb", ["kb-1", "kb-2", "kb-1"])
    assert missing == ["kb-2"]
    sql = sql_text(session.executed[0][0])
    assert "log_knowledge.id" in sql
    assert "existed_status" in sql


async def test_find_missing_batch_has_no_existence_condition(patch_session):
    session = patch_session(FakeSession(default=FakeResult(rows=["b1"])))
    assert await ResourceIdPGManager.find_missing("batch", ["b1", "b2"]) == ["b2"]
    sql = sql_text(session.executed[0][0])
    assert "brpc_diag_batch" in sql


async def test_find_missing_unknown_resource_raises(patch_session):
    patch_session(FakeSession())
    with pytest.raises(KeyError):
        await ResourceIdPGManager.find_missing("nope", ["x"])


async def test_find_missing_failure_mode_accepts_both_sources(patch_session):
    session = patch_session(
        FakeSession(results=[FakeResult(rows=["fm-1"]), FakeResult(rows=["fm-2"])])
    )
    missing = await ResourceIdPGManager.find_missing(
        "failure_mode", ["fm-1", "fm-2", "fm-3"]
    )
    assert missing == ["fm-3"]
    assert len(session.executed) == 2
    assert "failure_mode_knowledge" in sql_text(session.executed[0][0])
    assert "brpc_diag_node" in sql_text(session.executed[1][0])


async def test_find_missing_failure_mode_ids_empty(patch_session):
    session = patch_session(FakeSession())
    assert await ResourceIdPGManager.find_missing_failure_mode_ids([]) == []
    assert session.executed == []


async def test_find_missing_trace_ids_checks_all_tables(patch_session):
    session = patch_session(
        FakeSession(
            results=[
                FakeResult(rows=["t1"]),
                FakeResult(rows=["t2"]),
                FakeResult(rows=["t3"]),
            ]
        )
    )
    assert await ResourceIdPGManager.find_missing_trace_ids(["t1", "t2", "t3"]) == []
    assert len(session.executed) == 3
    assert "log_parse_result" in sql_text(session.executed[0][0])
    assert "trace_failure_event" in sql_text(session.executed[1][0])
    assert "log_failure_event" in sql_text(session.executed[2][0])


async def test_find_missing_trace_ids_reports_absent(patch_session):
    session = patch_session(
        FakeSession(
            results=[FakeResult(rows=["t1"]), FakeResult(rows=[]), FakeResult(rows=[])]
        )
    )
    assert await ResourceIdPGManager.find_missing_trace_ids(["t1", "t2"]) == ["t2"]


async def test_find_missing_trace_ids_empty(patch_session):
    session = patch_session(FakeSession())
    assert await ResourceIdPGManager.find_missing_trace_ids([]) == []
    assert session.executed == []


# ---------------------------------------------------------------------------
# DiagnosisConfigPGManager
# ---------------------------------------------------------------------------

import latency.database.managers.diagnosis_config as diagnosis_config_module
from latency.schemas.config import (
    DSLogAnalyzerConfig,
    DiagnosisRuntimeConfig,
    LogFilenamePatternConfig,
)


def _runtime_config():
    return DiagnosisRuntimeConfig(
        log_filename_pattern=LogFilenamePatternConfig(
            ds_client_access_log_file=["a.log"],
            ds_client_info_log_file=["b.log"],
            ds_worker_access_log_file=["c.log"],
            ds_worker_info_log_file=["d.log"],
            resource_log_file=["e.log"],
            brpc_log_file_patterns=["brpc.log"],
        ),
        log_analyzer_params=DSLogAnalyzerConfig(),
    )


def test_get_default_config_returns_runtime_config(monkeypatch):
    config = _runtime_config()
    monkeypatch.setattr(
        diagnosis_config_module,
        "Config",
        lambda: SimpleNamespace(get_default_diagnosis_config=lambda: config),
    )
    assert DiagnosisConfigPGManager.get_default_config() is config


async def test_get_or_create_returns_existing_row(patch_session):
    config = _runtime_config()
    session = patch_session(
        FakeSession(default=FakeResult(scalar_value=config.model_dump(mode="json")))
    )
    result = await DiagnosisConfigPGManager.get_or_create("kb-1")
    assert result == config
    assert len(session.executed) == 1  # no upsert for an existing row


async def test_get_or_create_inserts_default_when_missing(patch_session, monkeypatch):
    config = _runtime_config()
    monkeypatch.setattr(
        DiagnosisConfigPGManager, "get_default_config", staticmethod(lambda: config)
    )
    session = patch_session(
        FakeSession(results=[FakeResult(scalar_value=None)])
    )
    result = await DiagnosisConfigPGManager.get_or_create("kb-1")
    assert result == config
    assert len(session.executed) == 2
    sql = sql_text(session.executed[1][0])
    assert sql.startswith("INSERT INTO diagnosis_config")
    assert "ON CONFLICT (kb_id) DO UPDATE" in sql


async def test_upsert_with_explicit_session():
    session = FakeSession()
    config = _runtime_config()
    returned = await DiagnosisConfigPGManager.upsert("kb-1", config, session=session)
    assert returned == config
    assert returned is not config  # deep copy
    assert len(session.executed) == 1
    sql = sql_text(session.executed[0][0])
    assert sql.startswith("INSERT INTO diagnosis_config")


async def test_upsert_opens_own_session(patch_session):
    session = patch_session(FakeSession())
    config = _runtime_config()
    returned = await DiagnosisConfigPGManager.upsert("kb-1", config)
    assert returned == config
    assert len(session.executed) == 1


async def test_reset_upserts_default_config(monkeypatch):
    config = _runtime_config()
    monkeypatch.setattr(
        DiagnosisConfigPGManager, "get_default_config", staticmethod(lambda: config)
    )
    session = FakeSession()
    returned = await DiagnosisConfigPGManager.reset("kb-1", session=session)
    assert returned == config
    assert len(session.executed) == 1
    assert sql_text(session.executed[0][0]).startswith("INSERT INTO diagnosis_config")


async def test_delete_config_returns_true_on_rowcount(patch_session):
    session = patch_session(FakeSession(default=FakeResult(rowcount=1)))
    assert await DiagnosisConfigPGManager.delete("kb-1") is True
    assert "DELETE FROM diagnosis_config" in sql_text(session.executed[0][0])


async def test_delete_config_returns_false_on_zero(patch_session):
    patch_session(FakeSession(default=FakeResult(rowcount=0)))
    assert await DiagnosisConfigPGManager.delete("kb-x") is False
