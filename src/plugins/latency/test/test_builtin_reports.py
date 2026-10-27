# Copyright (c) Huawei Technologies Co., Ltd. 2023-2025. All rights reserved.
"""Built-in archive sync: hash gating, per-file failures and supersede."""
from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from latency.services import builtin_reports as module
from latency.services.builtin_reports import (
    STATUS_BUSY,
    STATUS_COMPLETED,
    STATUS_PARTIAL,
    archive_sha256,
    read_state,
    supersede_report,
    sync_builtin_reports,
    sync_builtin_reports_locked,
)

OLD_ID = "report_hist_" + "a" * 64
NEW_ID = "report_hist_" + "b" * 64


def _item(name: str, report_id: str | None, status: str = "imported", error: str | None = None):
    return SimpleNamespace(
        original_name=name, report_id=report_id, status=status, error=error
    )


@pytest.fixture
def env(tmp_path, monkeypatch):
    archive = tmp_path / "reports.zip"
    archive.write_bytes(b"archive-v1")
    state_path = tmp_path / "state" / "import-state.json"
    calls: list[Path] = []

    async def fake_import(source, options):
        calls.append(source)
        assert options.declared_verified is True
        assert options.build_cases is True
        return SimpleNamespace(
            items=[_item("one.json", NEW_ID), _item("two.json", None, "duplicate")],
            summary={"imported": 1, "duplicate": 1, "failed": 0},
        )

    monkeypatch.setattr(module, "import_reports", fake_import)
    monkeypatch.setattr(module, "report_root", lambda: tmp_path)
    return SimpleNamespace(
        archive=archive, state_path=state_path, calls=calls, tmp_path=tmp_path
    )


async def test_unchanged_archive_is_skipped_without_import(env):
    first = await sync_builtin_reports(env.archive, env.state_path, "importer")
    assert first["status"] == STATUS_COMPLETED
    assert first["report_count"] == 1
    assert len(env.calls) == 1

    second = await sync_builtin_reports(env.archive, env.state_path, "importer")
    assert second["status"] == "skipped"
    assert second["reason"] == "already_imported"
    assert len(env.calls) == 1

    state = read_state(env.state_path)
    assert state["archive_sha256"] == archive_sha256(env.archive)
    assert state["report_ids"] == [NEW_ID]


async def test_replaced_archive_reimports_and_supersedes_missing_report(env, monkeypatch):
    await sync_builtin_reports(env.archive, env.state_path, "importer")

    archived: list[str] = []
    deleted: list[str] = []

    async def fake_cases(report_id):
        return [SimpleNamespace(id="case-1", status="confirmed")]

    async def fake_archive(case_id, request):
        archived.append((case_id, request.archive_reason))
        return SimpleNamespace(case=None)

    async def fake_deleted(report_id):
        deleted.append(report_id)
        return {"disabled": 2}

    monkeypatch.setattr(module, "_cases_bound_to", fake_cases)
    monkeypatch.setattr(module.DiagCaseLibraryService, "archive_case", fake_archive)
    monkeypatch.setattr(
        module.PhenomenonIndexService, "handle_report_deleted", fake_deleted
    )
    for suffix in (".html", ".json", ".source.json"):
        (env.tmp_path / f"{OLD_ID}{suffix}").write_text("x", encoding="utf-8")
    (env.tmp_path / f"{NEW_ID}.html").write_text("keep", encoding="utf-8")
    state = read_state(env.state_path)
    state["report_ids"] = [OLD_ID]
    env.state_path.write_text(json.dumps(state), encoding="utf-8")

    env.archive.write_bytes(b"archive-v2")
    result = await sync_builtin_reports(env.archive, env.state_path, "importer")

    assert result["status"] == STATUS_COMPLETED
    assert len(env.calls) == 2
    assert [entry["report_id"] for entry in result["superseded"]] == [OLD_ID]
    assert result["superseded"][0]["archived_cases"] == ["case-1"]
    assert result["superseded"][0]["disabled_cards"] == 2
    assert archived[0][0] == "case-1"
    assert deleted == [OLD_ID]
    assert not (env.tmp_path / f"{OLD_ID}.html").exists()
    assert not (env.tmp_path / f"{OLD_ID}.source.json").exists()
    assert (env.tmp_path / f"{NEW_ID}.html").exists()
    assert read_state(env.state_path)["report_ids"] == [NEW_ID]


async def test_per_file_failure_is_recorded_and_not_retried(env, monkeypatch):
    async def failing_import(source, options):
        return SimpleNamespace(
            items=[
                _item("one.json", NEW_ID),
                _item("broken.json", "report_hist_" + "c" * 64, "failed", "renderer_rejected: bad"),
            ],
            summary={"imported": 1, "duplicate": 0, "failed": 1},
        )

    monkeypatch.setattr(module, "import_reports", failing_import)
    first = await sync_builtin_reports(env.archive, env.state_path, "importer")
    assert first["status"] == STATUS_PARTIAL
    assert first["failures"] == [{"file": "broken.json", "error": "renderer_rejected: bad"}]
    assert read_state(env.state_path)["status"] == STATUS_PARTIAL

    second = await sync_builtin_reports(env.archive, env.state_path, "importer")
    assert second["status"] == "skipped"

    forced = await sync_builtin_reports(
        env.archive, env.state_path, "importer", force=True
    )
    assert forced["status"] == STATUS_PARTIAL


async def test_unexpected_error_leaves_state_for_retry(env, monkeypatch):
    async def boom(source, options):
        raise RuntimeError("database unavailable")

    monkeypatch.setattr(module, "import_reports", boom)
    with pytest.raises(RuntimeError):
        await sync_builtin_reports(env.archive, env.state_path, "importer")
    assert not env.state_path.exists()


async def test_supersede_refuses_non_imported_report_ids(env):
    with pytest.raises(ValueError, match="refusing to supersede"):
        await supersede_report("../../etc/passwd", "importer")


async def test_busy_when_another_instance_holds_the_lock(env, monkeypatch):
    class FakeConnection:
        async def execute(self, statement, params):
            return SimpleNamespace(scalar=lambda: False)

    class FakeContext:
        async def __aenter__(self):
            return FakeConnection()

        async def __aexit__(self, *exc):
            return False

    monkeypatch.setattr(module.PGManager, "connection", staticmethod(lambda: FakeContext()))
    result = await sync_builtin_reports_locked(env.archive, env.state_path, "importer")
    assert result["status"] == STATUS_BUSY
    assert env.calls == []
