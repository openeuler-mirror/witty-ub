from datetime import datetime
from contextlib import asynccontextmanager
from types import SimpleNamespace

import pytest

from latency.database.engine import PGManager
from latency.database.managers.log_file import LogFilePGManager
from latency.database.managers.log_knowledge import LogKnowledgePGManager


def _normalize(statement) -> str:
    return " ".join(str(statement).split())


class _StatementRecorder:
    def __init__(self):
        self.statements: list[tuple[str, dict[str, str] | None]] = []
        self.kb_id: str | None = "kb-1"
        self.missing_log_file = False

    async def execute(self, statement, params=None):
        sql = _normalize(statement)
        self.statements.append((sql, params))
        if sql.startswith("SELECT"):
            return SimpleNamespace(
                scalar_one_or_none=lambda: None
                if self.missing_log_file
                else self.kb_id
            )
        rowcount = 0 if (
            self.missing_log_file and sql == "DELETE FROM log_file WHERE id = :log_id"
        ) else 1
        return SimpleNamespace(rowcount=rowcount)


def _make_fake_session(recorder: _StatementRecorder):
    @asynccontextmanager
    async def fake_session():
        yield recorder

    return fake_session


@pytest.fixture()
def recorder(monkeypatch):
    rec = _StatementRecorder()
    monkeypatch.setattr(PGManager, "session", _make_fake_session(rec))
    return rec


async def test_hard_delete_log_file_removes_all_related_rows(recorder):
    deleted = await LogFilePGManager.hard_delete_log_file_with_related_data(
        "log-to-delete"
    )

    assert deleted is True
    sql_statements = [sql for sql, _ in recorder.statements]
    combined_sql = "\n".join(sql_statements)

    for table in (
        "diagnosis_case_signal",
        "diagnosis_case",
        "brpc_diag_hit",
        "brpc_diag_batch",
        "task_report",
        "task",
        *LogFilePGManager._DERIVED_TABLES_BY_LOG_ID,
        "log_file",
    ):
        assert any(f"DELETE FROM {table}" in sql for sql in sql_statements)

    # Only the two intended UPDATEs may run: stripping the log id from
    # multi-source diagnosis cases and refreshing the KB counters.
    update_statements = [sql for sql in sql_statements if sql.startswith("UPDATE")]
    assert update_statements, "expected the strip + refresh UPDATEs to run"
    for sql in update_statements:
        assert sql.startswith(
            ("UPDATE diagnosis_case", "UPDATE log_knowledge")
        ), f"unexpected UPDATE: {sql}"
    assert sum(sql.startswith("UPDATE diagnosis_case") for sql in update_statements) == 1
    assert sum(sql.startswith("UPDATE log_knowledge") for sql in update_statements) == 1

    # The KB is read before its log_file row is deleted.
    assert sql_statements[0] == "SELECT kb_id FROM log_file WHERE id = :log_id"

    assert sql_statements.index("DELETE FROM brpc_diag_hit WHERE batch_id IN (SELECT batch_id FROM brpc_diag_batch WHERE task_id IN (SELECT id FROM task WHERE op_id = :log_id))") < sql_statements.index("DELETE FROM brpc_diag_batch WHERE task_id IN (SELECT id FROM task WHERE op_id = :log_id)")
    assert sql_statements.index("DELETE FROM task_report WHERE task_id IN (SELECT id FROM task WHERE op_id = :log_id)") < sql_statements.index("DELETE FROM task WHERE op_id = :log_id")

    # Single-source cases must be fully deleted before multi-source cases
    # are stripped, otherwise the strip would leave empty cases behind.
    delete_case_index = next(
        i for i, sql in enumerate(sql_statements) if sql.startswith("DELETE FROM diagnosis_case ")
    )
    strip_index = next(
        i for i, sql in enumerate(sql_statements) if sql.startswith("UPDATE diagnosis_case SET source_log_ids")
    )
    assert delete_case_index < strip_index
    assert "NOT EXISTS" in sql_statements[delete_case_index]
    assert "jsonb_agg" in sql_statements[strip_index]

    # KB counters are refreshed after the log_file row is gone so the
    # aggregation already excludes it.
    log_file_delete_index = sql_statements.index("DELETE FROM log_file WHERE id = :log_id")
    refresh_index = next(
        i for i, sql in enumerate(sql_statements) if sql.startswith("UPDATE log_knowledge")
    )
    assert log_file_delete_index < refresh_index
    assert sql_statements[-1].startswith("UPDATE log_knowledge")

    log_scoped = [
        params
        for sql, params in recorder.statements
        if not sql.startswith("UPDATE")
    ]
    assert all(params == {"log_id": "log-to-delete"} for params in log_scoped)
    refresh_params = recorder.statements[refresh_index][1]
    assert refresh_params["kb_id"] == "kb-1"
    assert isinstance(refresh_params["server_updated_at"], datetime)
    assert isinstance(recorder.statements[strip_index][1]["server_updated_at"], datetime)


async def test_hard_delete_reports_missing_log_file(recorder):
    recorder.missing_log_file = True

    deleted = await LogFilePGManager.hard_delete_log_file_with_related_data(
        "missing-log"
    )

    assert deleted is False
    sql_statements = [sql for sql, _ in recorder.statements]
    # Without a KB the refresh must not run at all.
    assert not any(sql.startswith("UPDATE log_knowledge") for sql in sql_statements)
    assert sql_statements[-1] == "DELETE FROM log_file WHERE id = :log_id"


async def test_refresh_kb_counters_aggregates_active_log_files(recorder):
    rowcount = await LogKnowledgePGManager.refresh_kb_counters("kb-9")

    assert rowcount == 1
    assert len(recorder.statements) == 1
    sql, params = recorder.statements[0]
    assert sql.startswith("UPDATE log_knowledge")
    assert "FROM log_file" in sql
    assert "existed_status IS TRUE" in sql
    assert "SUM(COALESCE(anomalous_count, 0))" in sql
    assert "SUM(COALESCE(failure_count, 0))" in sql
    assert "COUNT(*)" in sql
    assert params["kb_id"] == "kb-9"
    assert isinstance(params["server_updated_at"], datetime)
