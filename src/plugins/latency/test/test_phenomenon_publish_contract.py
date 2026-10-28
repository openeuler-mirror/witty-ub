# Copyright (c) Huawei Technologies Co., Ltd. 2023-2025. All rights reserved.
"""Publish state-machine counter-examples found by acceptance.

Each test reproduces one regression: candidate version binding, forced rebuild
and KB switching, case text scrubbing, incomplete scans, multi-version case
selection, RAG delete error classification, expired leases and hard limits.
"""
from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from datetime import timedelta
from pathlib import Path
from types import SimpleNamespace

import pytest

from latency.access import phenomenon_cli
from latency.database.engine import PGManager
from latency.database.managers import phenomenon_index as manager_module
from latency.database.managers.phenomenon_index import PhenomenonIndexPGManager
from latency.database.models import PhenomenonIndex, RagDocCleanupTask
from latency.ENUM.phenomenon import PhenomenonIndexStatus, RagCleanupStatus
from latency.exceptions import DependencyUnavailableBizException
from latency.schemas.phenomenon import SearchPhenomenonRequest
from latency.services import phenomenon_index as service
from latency.services import phenomenon_search as search_module
from latency.services.phenomenon_index import PhenomenonIndexService, _scan_paired_reports
from latency.services.phenomenon_search import PhenomenonSearchService
from latency.services.rag_client import RAGClient, RAGContractError
from latency.services.report_phenomenon import (
    TEXT_HARD_LIMIT,
    _truncate_at_sentence,
    extract_case_doc,
    sha256_hex,
)


class _AsyncValue:
    def __init__(self, value):
        self._value = value
        self.calls = []

    async def __call__(self, *args, **kwargs):
        self.calls.append((args, kwargs))
        return self._value


class _FakeResult:
    def __init__(self, row=None, rows=None):
        self._row = row
        self._rows = rows if rows is not None else []

    def scalars(self):
        return self

    def first(self):
        return self._row

    def all(self):
        return self._rows


class _FakeSession:
    """Mimics the subset of AsyncSession the manager touches."""

    def __init__(self, row=None, rows=None, scalars=None, statements=None):
        self._row = row
        self._rows = rows if rows is not None else []
        self._scalars = list(scalars or [])
        self.statements = statements if statements is not None else []
        self.gets = []
        self.added = []

    async def execute(self, statement):
        self.statements.append(statement)
        return _FakeResult(self._row, self._rows)

    async def get(self, model, key):
        self.gets.append((model, key))
        return self._row

    async def scalar(self, statement, params=None):
        self.statements.append(statement)
        if self._scalars:
            return self._scalars.pop(0)
        return None

    def add(self, instance):
        self.added.append(instance)


def _install_session(monkeypatch, session):
    @asynccontextmanager
    async def _session():
        yield session

    monkeypatch.setattr(PGManager, "session", classmethod(lambda cls: _session()))


def _install_scope(monkeypatch, session):
    @asynccontextmanager
    async def _scope(session_arg=None):
        yield session

    monkeypatch.setattr(manager_module, "session_scope", _scope)


# --------------------------------------------------------------- candidates
@pytest.mark.asyncio
async def test_register_persists_candidate_version_hashes(monkeypatch):
    row = PhenomenonIndex(
        doc_id="case:c1",
        content_hash=sha256_hex("text"),
        source_fault_hash="fp",
        enabled=True,
        lease_owner="w",
        lease_token="t",
        lease_expires_at=service._now() + timedelta(seconds=60),
    )
    session = _FakeSession(row=row, scalars=[True, 0])
    _install_session(monkeypatch, session)

    ok = await PhenomenonIndexPGManager.register_pending_candidate(
        "case:c1", "w", "t", "kb-1", "doc-1", row.content_hash, "fp"
    )

    assert ok is True
    assert row.pending_content_hash == row.content_hash
    assert row.pending_source_fault_hash == "fp"


@pytest.mark.asyncio
async def test_mark_parsing_rejects_desired_version_change(monkeypatch):
    row = SimpleNamespace(
        enabled=True,
        lease_owner="w",
        lease_token="t",
        lease_expires_at=service._now() + timedelta(seconds=60),
        pending_rag_kb_id="kb-1",
        pending_rag_doc_id="doc-1",
        pending_content_hash=sha256_hex("old"),
        pending_source_fault_hash="old-fp",
        content_hash=sha256_hex("new"),
        source_fault_hash="new-fp",
    )
    _install_session(monkeypatch, _FakeSession(row=row))

    assert not await PhenomenonIndexPGManager.mark_parsing(
        "case:c1", "w", "t", "kb-1", "doc-1"
    )


@pytest.mark.asyncio
async def test_switch_rejects_candidate_from_another_version(monkeypatch):
    row = SimpleNamespace(
        doc_id="case:c1",
        enabled=True,
        lease_owner="w",
        lease_token="t",
        lease_expires_at=service._now() + timedelta(seconds=60),
        content_hash=sha256_hex("new"),
        source_fault_hash="new-fp",
        pending_rag_kb_id="kb-1",
        pending_rag_doc_id="doc-1",
        pending_content_hash=sha256_hex("old"),
        pending_source_fault_hash="new-fp",
    )
    _install_session(monkeypatch, _FakeSession(row=row, scalars=[True]))

    result = await PhenomenonIndexPGManager.switch_published(
        "case:c1", "w", "t", "kb-1", "doc-1", row.content_hash, "new-fp"
    )

    assert result.status == "candidate_version_mismatch"
    assert not hasattr(row, "published_text")


@pytest.mark.asyncio
async def test_poll_parsing_switches_with_the_uploaded_version(monkeypatch):
    switch = _AsyncValue(SimpleNamespace(status="switched", cleanup_pairs=[]))
    refresh = _AsyncValue(None)
    monkeypatch.setattr(
        PhenomenonIndexPGManager, "switch_published", staticmethod(switch)
    )
    monkeypatch.setattr(
        PhenomenonIndexService, "_refresh_after_publish", staticmethod(refresh)
    )

    card = SimpleNamespace(
        doc_id="report:r:F01",
        lease_owner="w",
        lease_token="t",
        pending_rag_doc_id="doc-1",
        pending_rag_kb_id="kb-1",
        pending_content_hash=sha256_hex("uploaded"),
        pending_source_fault_hash="uploaded-fp",
        content_hash=sha256_hex("refreshed"),
        source_fault_hash="refreshed-fp",
        next_retry_at=None,
        report_id="r",
    )
    client = SimpleNamespace(parse_status=_AsyncValue("success"))

    await PhenomenonIndexService._poll_parsing(card, client, "kb-1")

    assert switch.calls
    args = switch.calls[0][0]
    assert args[5] == sha256_hex("uploaded")
    assert args[6] == "uploaded-fp"


# --------------------------------------------------------------- force / KB
@pytest.mark.asyncio
async def test_force_clears_reusable_snapshot_hash(monkeypatch):
    content_hash = sha256_hex("text")
    row = PhenomenonIndex(
        doc_id="case:c1",
        content_hash=content_hash,
        source_fault_hash="fp",
        indexed_content_hash=content_hash,
        published_text="text",
        published_title="标题",
        published_symptom="现象",
        published_source_fault_hash="fp",
        searchable=True,
        enabled=True,
        kind="case",
        content_source="case",
        title="标题",
        symptom="现象",
        text="text",
        verification="confirmed_unverified",
        binding_status="none",
        fault_type="latency",
        operation=None,
        log_type=None,
        status_codes=[],
        failure_mode_ids=[],
    )
    _install_scope(monkeypatch, _FakeSession(row=row))
    doc = SimpleNamespace(
        doc_id="case:c1",
        kind="case",
        content_source="case",
        report_id=None,
        source_fault_id=None,
        source_fault_hash="fp",
        case_id="c1",
        case_no=None,
        legacy_case_id=None,
        title="标题",
        symptom="现象",
        root_cause_summary=None,
        log_type=None,
        operation=None,
        fault_type="latency",
        status_codes=[],
        failure_mode_ids=[],
        verification="confirmed_unverified",
        binding_status="none",
        text="text",
        content_hash=content_hash,
    )

    result = await PhenomenonIndexPGManager.upsert_expected(doc, force=True)

    assert result.queued is True
    assert row.indexed_content_hash is None


@pytest.mark.asyncio
async def test_publish_uploads_when_target_kb_changed(monkeypatch):
    metadata = _AsyncValue("published")
    upload = _AsyncValue("doc-new")
    monkeypatch.setattr(
        PhenomenonIndexPGManager, "metadata_publish", staticmethod(metadata)
    )
    monkeypatch.setattr(
        PhenomenonIndexPGManager, "register_pending_candidate", staticmethod(_AsyncValue(True))
    )
    monkeypatch.setattr(
        PhenomenonIndexPGManager, "mark_parsing", staticmethod(_AsyncValue(True))
    )
    monkeypatch.setattr(
        PhenomenonIndexPGManager, "get_card", staticmethod(_AsyncValue(None))
    )
    poll = _AsyncValue(None)
    monkeypatch.setattr(
        PhenomenonIndexService, "_poll_parsing", staticmethod(poll)
    )

    content_hash = sha256_hex("正文")
    card = SimpleNamespace(
        doc_id="case:c1",
        lease_owner="w",
        lease_token="t",
        content_hash=content_hash,
        source_fault_hash="fp",
        indexed_content_hash=content_hash,
        published_source_fault_hash="fp",
        rag_kb_id="kb-old",
        rag_doc_id="doc-old",
        text="正文",
    )
    client = SimpleNamespace(upload_text=upload)

    await PhenomenonIndexService._publish_card(card, client, "kb-new")

    assert metadata.calls == []
    assert upload.calls
    assert upload.calls[0][0][0] == "kb-new"


@pytest.mark.asyncio
async def test_publish_uploads_when_force_cleared_the_hash(monkeypatch):
    metadata = _AsyncValue("published")
    upload = _AsyncValue("doc-new")
    monkeypatch.setattr(
        PhenomenonIndexPGManager, "metadata_publish", staticmethod(metadata)
    )
    monkeypatch.setattr(
        PhenomenonIndexPGManager, "register_pending_candidate", staticmethod(_AsyncValue(True))
    )
    monkeypatch.setattr(
        PhenomenonIndexPGManager, "mark_parsing", staticmethod(_AsyncValue(True))
    )
    monkeypatch.setattr(
        PhenomenonIndexPGManager, "get_card", staticmethod(_AsyncValue(None))
    )
    monkeypatch.setattr(
        PhenomenonIndexService, "_poll_parsing", staticmethod(_AsyncValue(None))
    )

    card = SimpleNamespace(
        doc_id="case:c1",
        lease_owner="w",
        lease_token="t",
        content_hash=sha256_hex("正文"),
        source_fault_hash="fp",
        indexed_content_hash=None,
        published_source_fault_hash="fp",
        rag_kb_id="kb-1",
        rag_doc_id="doc-old",
        text="正文",
    )
    client = SimpleNamespace(upload_text=upload)

    await PhenomenonIndexService._publish_card(card, client, "kb-1")

    assert metadata.calls == []
    assert upload.calls


# ------------------------------------------------------------------- cases
def test_case_fault_shape_is_scrubbed():
    case = SimpleNamespace(
        id="case-1",
        case_no="C1",
        status="confirmed",
        title="GET 等待",
        symptom_summary="请求等待",
        fault_shape="在 10.1.2.3 与 fd00::1 上呈尖峰",
        operation="GET",
        fault_type="latency",
        latency_components=[],
        log_keywords=[],
        verification_json={},
        source_fault_hash="fp",
        root_cause_summary=None,
    )
    doc = extract_case_doc(case)

    assert "10.1.2.3" not in doc.text
    assert "fd00::1" not in doc.text
    assert "[IP]" in doc.text


@pytest.mark.asyncio
async def test_index_report_binds_the_matching_case_version(tmp_path, monkeypatch):
    html = tmp_path / "report_r.html"
    html.write_text("<html></html>", encoding="utf-8")
    html.with_suffix(".json").write_text("{}", encoding="utf-8")
    doc = service.PhenomenonDoc(
        doc_id="report:r:F01",
        kind="report",
        content_source="report",
        title="GET 等待",
        symptom="请求等待",
        text="GET 等待",
        content_hash=sha256_hex("GET 等待"),
        verification="report_only",
        report_id="r",
        source_fault_id="F01",
        source_fault_hash="new-hash",
    )
    extraction = SimpleNamespace(
        faults=[doc],
        fault_errors=[],
        kb_id="kb-1",
        kb_name="KB",
        title="报告",
        generated_at=None,
        operation="GET",
        time_range_start=None,
        time_range_end=None,
        fault_count=1,
        sidecar_hash="sidecar",
    )
    old_case = SimpleNamespace(
        id="case-old",
        status="confirmed",
        source_fault_id="F01",
        source_fault_hash="old-hash",
        case_no="C1",
        verification_json={"closed_loop": True},
    )
    new_case = SimpleNamespace(
        id="case-new",
        status="confirmed",
        source_fault_id="F01",
        source_fault_hash="new-hash",
        case_no="C2",
        verification_json={"closed_loop": True},
    )
    upserts = _AsyncValue(SimpleNamespace(queued=True))
    ensured = _AsyncValue(None)
    monkeypatch.setattr(
        service.extractor, "extract_report", lambda *a, **k: extraction
    )
    monkeypatch.setattr(
        PhenomenonIndexService, "_bound_cases", staticmethod(_AsyncValue([old_case, new_case]))
    )
    monkeypatch.setattr(
        PhenomenonIndexPGManager, "upsert_expected", staticmethod(upserts)
    )
    monkeypatch.setattr(
        PhenomenonIndexService, "_ensure_independent_case", staticmethod(ensured)
    )
    monkeypatch.setattr(
        PhenomenonIndexService, "_disable_independent_case", staticmethod(_AsyncValue(None))
    )
    monkeypatch.setattr(
        PhenomenonIndexPGManager, "get_cards_by_report", staticmethod(_AsyncValue([]))
    )
    monkeypatch.setattr(
        PhenomenonIndexPGManager, "upsert_report_index", staticmethod(_AsyncValue(None))
    )
    monkeypatch.setattr(
        PhenomenonIndexService, "refresh_report_status", staticmethod(_AsyncValue("indexed"))
    )

    await PhenomenonIndexService.index_report("r", html=html, kb_dir="kb-1")

    assert upserts.calls
    bound = upserts.calls[0][0][0]
    assert bound.case_id == "case-new"
    assert ensured.calls
    assert ensured.calls[0][0][0].id == "case-old"


# -------------------------------------------------------------------- scan
def test_unreadable_subdirectory_marks_scan_incomplete(tmp_path, monkeypatch):
    (tmp_path / "report_ok.html").write_text("<html></html>", encoding="utf-8")
    (tmp_path / "blocked").mkdir()
    original_glob = Path.glob

    def fake_glob(self, pattern):
        if self.name == "blocked":
            raise PermissionError("denied")
        return original_glob(self, pattern)

    monkeypatch.setattr(Path, "glob", fake_glob)

    complete, _reports = _scan_paired_reports(tmp_path)

    assert complete is False


# -------------------------------------------------------------------- RAG
@pytest.mark.asyncio
async def test_delete_document_only_tolerates_missing(monkeypatch):
    client = RAGClient("http://rag")

    async def raise_400(method, path, **kwargs):
        raise RAGContractError("bad request", status_code=400)

    monkeypatch.setattr(client, "_request", raise_400)
    with pytest.raises(RAGContractError):
        await client.delete_document("doc-1")

    async def raise_404(method, path, **kwargs):
        raise RAGContractError("gone", status_code=404)

    monkeypatch.setattr(client, "_request", raise_404)
    assert await client.delete_document("doc-1") is True

    async def already_absent(method, path, **kwargs):
        return {"success": False}

    async def raise_gone(doc_id):
        raise RAGContractError("gone", status_code=404)

    monkeypatch.setattr(client, "_request", already_absent)
    monkeypatch.setattr(client, "get_document", raise_gone)
    assert await client.delete_document("doc-1") is True


@pytest.mark.asyncio
async def test_delete_document_false_result_is_retried_when_doc_survives(monkeypatch):
    client = RAGClient("http://rag")

    async def success_false(method, path, **kwargs):
        return {"success": False}

    async def still_there(doc_id):
        return {"id": doc_id, "parse_status": "success"}

    monkeypatch.setattr(client, "_request", success_false)
    monkeypatch.setattr(client, "get_document", still_there)

    with pytest.raises(RAGContractError):
        await client.delete_document("doc-1")


@pytest.mark.asyncio
async def test_delete_document_false_result_accepts_deleted_status(monkeypatch):
    client = RAGClient("http://rag")

    async def success_false(method, path, **kwargs):
        return {"success": False}

    async def deleted(doc_id):
        return {"id": doc_id, "status": "deleted"}

    monkeypatch.setattr(client, "_request", success_false)
    monkeypatch.setattr(client, "get_document", deleted)

    assert await client.delete_document("doc-1") is True


# ------------------------------------------------------------------ leases
@pytest.mark.asyncio
async def test_publish_failure_requires_a_live_lease(monkeypatch):
    session = _FakeSession()
    _install_session(monkeypatch, session)

    await PhenomenonIndexPGManager.record_publish_failure(
        "case:c1", "w", "t", error="boom", next_retry_at=None, terminal=True
    )

    assert session.statements
    clause = str(session.statements[0].whereclause)
    assert "lease_expires_at" in clause
    assert ">=" in clause


# --------------------------------------------------------------- KB init
class _FakeRagKbClient:
    def __init__(self, kb: dict | None = None):
        self._kb = kb or {}
        self.created: list[str] = []

    async def get_kb(self, kb_id: str) -> dict:
        return self._kb

    async def create_document_kb(self, name: str) -> str:
        self.created.append(name)
        return "kb-new"


@pytest.mark.asyncio
async def test_init_kb_validates_configured_kb(monkeypatch):
    client = _FakeRagKbClient({"meta_data_type": "document"})
    monkeypatch.setattr(RAGClient, "from_env", classmethod(lambda cls: client))
    monkeypatch.setenv("RAG_PHENOMENON_KB_ID", "kb-1")

    result = await phenomenon_cli._init_kb("witty-ub-phenomenon")

    assert result == {"kb_id": "kb-1", "created": False, "kb_type": "document"}
    assert client.created == []


@pytest.mark.asyncio
async def test_init_kb_rejects_non_document_kb(monkeypatch):
    client = _FakeRagKbClient({"meta_data_type": "faq"})
    monkeypatch.setattr(RAGClient, "from_env", classmethod(lambda cls: client))
    monkeypatch.setenv("RAG_PHENOMENON_KB_ID", "kb-1")

    with pytest.raises(RAGContractError):
        await phenomenon_cli._init_kb("witty-ub-phenomenon")


@pytest.mark.asyncio
async def test_init_kb_creates_when_id_is_unset(monkeypatch):
    client = _FakeRagKbClient()
    monkeypatch.setattr(RAGClient, "from_env", classmethod(lambda cls: client))
    monkeypatch.delenv("RAG_PHENOMENON_KB_ID", raising=False)

    result = await phenomenon_cli._init_kb("witty-ub-phenomenon")

    assert result["kb_id"] == "kb-new"
    assert result["created"] is True
    assert result["env"] == "RAG_PHENOMENON_KB_ID=kb-new"
    assert client.created == ["witty-ub-phenomenon"]


# --------------------------------------------------------------- force scope
@pytest.mark.asyncio
async def test_index_scope_case_forwards_force(monkeypatch):
    sync = _AsyncValue({"queued_count": 1, "status": "merged"})
    monkeypatch.setattr(PhenomenonIndexService, "sync_case", staticmethod(sync))

    result = await PhenomenonIndexService.index_scope(
        "case", case_id="c1", force=True
    )

    assert result["queued_count"] == 1
    assert sync.calls[0][1]["force"] is True


@pytest.mark.asyncio
async def test_index_scope_legacy_all_forwards_force(monkeypatch):
    legacy = _AsyncValue(2)
    monkeypatch.setattr(
        PhenomenonIndexService, "index_legacy_all", staticmethod(legacy)
    )

    result = await PhenomenonIndexService.index_scope("legacy_all", force=True)

    assert result["queued_count"] == 2
    assert legacy.calls[0][1]["force"] is True


@pytest.mark.asyncio
async def test_all_scope_forwards_force_to_case_sync(monkeypatch):
    monkeypatch.setattr(
        service.DiagnosticReportService,
        "_collect",
        staticmethod(lambda root, kb_id: []),
    )
    sync = _AsyncValue({"queued_count": 1, "status": "merged"})
    monkeypatch.setattr(PhenomenonIndexService, "sync_case", staticmethod(sync))
    _install_session(monkeypatch, _FakeSession(rows=[("c1",)]))

    await PhenomenonIndexService.index_scope("all", force=True)

    assert sync.calls
    assert sync.calls[0][0][0] == "c1"
    assert sync.calls[0][1]["force"] is True


@pytest.mark.asyncio
async def test_sync_case_force_rebuilds_independent_card(monkeypatch):
    case = SimpleNamespace(
        id="c1", status="confirmed", report_id=None, source_fault_id=None,
        verification_json={"closed_loop": True},
    )
    monkeypatch.setattr(
        PhenomenonIndexService, "_get_case", staticmethod(_AsyncValue(case))
    )
    ensured = _AsyncValue(True)
    monkeypatch.setattr(
        PhenomenonIndexService, "_ensure_independent_case", staticmethod(ensured)
    )
    monkeypatch.setattr(
        PhenomenonIndexService, "_remove_case_pointer", staticmethod(_AsyncValue(None))
    )

    result = await PhenomenonIndexService.sync_case("c1", force=True)

    assert result["queued_count"] == 1
    assert ensured.calls[0][1]["force"] is True


@pytest.mark.asyncio
async def test_independent_case_upsert_receives_force(monkeypatch):
    upsert = _AsyncValue(SimpleNamespace(queued=True))
    monkeypatch.setattr(
        PhenomenonIndexPGManager, "upsert_expected", staticmethod(upsert)
    )
    case = SimpleNamespace(
        id="c1",
        case_no="C1",
        title="GET 等待",
        symptom_summary="请求等待",
        status_codes=[],
        failure_mode_ids=[],
        verification_json={},
    )

    queued = await PhenomenonIndexService._ensure_independent_case(
        case, stale=False, force=True
    )

    assert queued is True
    assert upsert.calls[0][1]["force"] is True


@pytest.mark.asyncio
async def test_sync_legacy_forwards_force(monkeypatch):
    monkeypatch.setattr(
        service,
        "_read_json",
        lambda path, max_bytes: {"id": "L1", "description": "远端写入偶发超时"},
    )
    upsert = _AsyncValue(SimpleNamespace(queued=True))
    monkeypatch.setattr(
        PhenomenonIndexPGManager, "upsert_expected", staticmethod(upsert)
    )

    result = await PhenomenonIndexService.sync_legacy("L1", force=True)

    assert result["queued_count"] == 1
    assert upsert.calls[0][1]["force"] is True


@pytest.mark.asyncio
async def test_index_legacy_all_forwards_force(monkeypatch):
    monkeypatch.setattr(service.os, "listdir", lambda path: ["L1.json"])
    sync = _AsyncValue({"queued_count": 1})
    monkeypatch.setattr(
        PhenomenonIndexService, "sync_legacy", staticmethod(sync)
    )

    queued = await PhenomenonIndexService.index_legacy_all(force=True)

    assert queued == 1
    assert sync.calls[0][1]["force"] is True


# ------------------------------------------------------------------ search budget
@pytest.mark.asyncio
async def test_search_enforces_absolute_budget(monkeypatch):
    monkeypatch.setattr(search_module.settings, "search_enabled", lambda: True)
    monkeypatch.setattr(
        search_module, "_rag_targets", lambda: (SimpleNamespace(), "kb")
    )
    monkeypatch.setattr(search_module, "SEARCH_BUDGET_SECONDS", 0.05)

    async def slow_search(req, client, kb_id):
        await asyncio.sleep(0.2)
        raise AssertionError("search must be cut at the absolute budget")

    monkeypatch.setattr(
        PhenomenonSearchService, "_search", staticmethod(slow_search)
    )

    with pytest.raises(DependencyUnavailableBizException):
        await PhenomenonSearchService.search(
            SearchPhenomenonRequest(query="GET 阻塞", top_k=5)
        )


# ------------------------------------------------------------------ CLI
@pytest.mark.asyncio
async def test_cli_legacy_all_forwards_force(monkeypatch):
    import argparse

    args = argparse.Namespace(
        init_kb=False,
        self_check=False,
        reconcile=False,
        all=False,
        report_id=None,
        case_id=None,
        legacy_all=True,
        force=True,
        kb_name="witty-ub-phenomenon",
    )
    db_config = SimpleNamespace(
        pg_dsn_url=lambda: "postgresql://unused",
        pg_pool_size=1,
        pg_max_overflow=0,
    )
    monkeypatch.setattr(
        phenomenon_cli,
        "Config",
        lambda: SimpleNamespace(get_config=lambda: SimpleNamespace(db=db_config)),
    )
    monkeypatch.setattr(
        phenomenon_cli.PGManager, "initialize", classmethod(lambda cls, *a, **k: None)
    )
    monkeypatch.setattr(
        phenomenon_cli, "init_postgresql_database", _AsyncValue(None)
    )
    scope = _AsyncValue({"queued_count": 1})
    monkeypatch.setattr(
        PhenomenonIndexService, "index_scope", staticmethod(scope)
    )

    result = await phenomenon_cli._run(args)

    assert result["queued_count"] == 1
    assert scope.calls[0][0][0] == "legacy_all"
    assert scope.calls[0][1]["force"] is True


def test_search_timeout_catches_py310_asyncio_alias():
    import inspect

    source = inspect.getsource(PhenomenonSearchService.search)
    assert "except asyncio.TimeoutError" in source


# --------------------------------------------------------------- lifecycle
@pytest.mark.asyncio
async def test_status_counts_ignore_disabled_cards(monkeypatch):
    session = _FakeSession(rows=[])
    _install_session(monkeypatch, session)

    assert await PhenomenonIndexPGManager.card_status_counts("report:r") == {}
    assert await PhenomenonIndexPGManager.card_status_counts_for_reports(
        ["report:r"]
    ) == {}

    for statement in session.statements:
        sql = str(statement.compile(compile_kwargs={"literal_binds": True}))
        assert "phenomenon_index.enabled IS true" in sql
        assert "index_status !=" not in sql


@pytest.mark.asyncio
async def test_disable_card_without_documents_becomes_deleted(monkeypatch):
    row = PhenomenonIndex(
        doc_id="case:c1",
        enabled=True,
        searchable=True,
        index_status=PhenomenonIndexStatus.INDEXED.value,
    )
    session = _FakeSession(row=row)
    _install_scope(monkeypatch, session)

    released = await PhenomenonIndexPGManager.disable_card("case:c1")

    assert released == []
    assert row.enabled is False
    assert row.index_status == PhenomenonIndexStatus.DELETED.value


@pytest.mark.asyncio
async def test_disable_card_waits_for_remote_cleanup(monkeypatch):
    row = PhenomenonIndex(
        doc_id="report:r:F01",
        enabled=True,
        searchable=True,
        index_status=PhenomenonIndexStatus.INDEXED.value,
        rag_kb_id="kb",
        rag_doc_id="doc",
    )
    session = _FakeSession(row=row)
    _install_scope(monkeypatch, session)

    released = await PhenomenonIndexPGManager.disable_card("report:r:F01")

    assert released == [("kb", "doc")]
    assert row.index_status == PhenomenonIndexStatus.INDEXED.value
    cleanup = str(
        session.statements[-1].compile(compile_kwargs={"literal_binds": True})
    )
    assert "'report:r:F01'" in cleanup


@pytest.mark.asyncio
async def test_finish_cleanup_marks_disabled_card_deleted(monkeypatch):
    task = RagDocCleanupTask(
        id=7,
        rag_kb_id="kb",
        rag_doc_id="doc",
        doc_id="report:r:F01",
        reason="expired",
        status=RagCleanupStatus.DELETING.value,
        lease_owner="worker",
        retry_count=0,
    )
    session = _FakeSession(row=task)
    _install_session(monkeypatch, session)

    assert await PhenomenonIndexPGManager.finish_cleanup(
        7, "worker", success=True
    )

    statement = session.statements[-1]
    assert statement.table.name == "phenomenon_index"
    sql = str(statement.compile(compile_kwargs={"literal_binds": True}))
    assert "'deleted'" in sql
    assert "enabled IS false" in sql
    assert "rag_doc_id IS NULL" in sql
    assert "pending_rag_doc_id IS NULL" in sql


# ------------------------------------------------------------------- limit
def test_truncation_counts_the_ellipsis():
    text = "字" * (TEXT_HARD_LIMIT + 200)

    truncated = _truncate_at_sentence(text, TEXT_HARD_LIMIT)

    assert len(truncated) <= TEXT_HARD_LIMIT
    assert truncated.endswith("…")


@pytest.mark.asyncio
async def test_reconcile_ignores_deleted_remote_tombstones(monkeypatch):
    observed: list[str] = []

    async def promote(_seconds=600):
        return 0

    async def no_cards(*_args, **_kwargs):
        return []

    async def no_pairs():
        return []

    async def observe(_kb_id, rag_doc_id):
        observed.append(rag_doc_id)

    def rag_targets():
        return None, "kb"

    async def remote_docs(_client, _kb_id):
        return [
            {"id": "active-doc", "name": "phenomenon_a.txt", "status": "existed"},
            {"id": "deleted-doc", "name": "phenomenon_b.txt", "status": "deleted"},
        ]

    monkeypatch.setattr(
        PhenomenonIndexPGManager, "promote_observing", staticmethod(promote)
    )
    monkeypatch.setattr(
        PhenomenonIndexPGManager, "cards_with_source_drift", staticmethod(no_cards)
    )
    monkeypatch.setattr(
        PhenomenonIndexPGManager, "cards_with_invalid_mapping", staticmethod(no_cards)
    )
    monkeypatch.setattr(
        PhenomenonIndexPGManager, "stuck_parsing_cards", staticmethod(no_cards)
    )
    monkeypatch.setattr(
        PhenomenonIndexPGManager, "observe_orphan", staticmethod(observe)
    )
    monkeypatch.setattr(
        PhenomenonIndexPGManager, "list_mapped_pairs", staticmethod(no_pairs)
    )
    monkeypatch.setattr(
        PhenomenonIndexService, "_rag_targets", staticmethod(rag_targets)
    )
    monkeypatch.setattr(
        PhenomenonIndexService, "_list_all_remote_docs", staticmethod(remote_docs)
    )

    async def no_repair():
        return {"repaired": 0, "signals_dropped": 0}

    monkeypatch.setattr(
        PhenomenonIndexService, "_repair_case_derived", staticmethod(no_repair)
    )

    stats = await PhenomenonIndexService.reconcile()

    assert stats["orphans"] == 1
    assert observed == ["active-doc"]


@pytest.mark.asyncio
async def test_reconcile_retires_mappings_left_in_a_previous_kb(monkeypatch):
    """换知识库后旧映射命中不到，必须以当前知识库为准退役并重新发布。"""
    cleared: list[tuple[str, str, bool]] = []
    searchable: list[tuple[str, bool]] = []

    async def promote(_seconds=600):
        return 0

    async def no_cards(*_args, **_kwargs):
        return []

    async def pairs():
        return [
            ("report:r", "old-kb", "old-doc"),
            ("report:kept", "kb", "kept-doc"),
        ]

    async def card_for(kb, rag_doc_id):
        return SimpleNamespace(doc_id="report:r", enabled=True)

    async def set_searchable(doc_id, flag):
        searchable.append((doc_id, flag))

    async def clear_mapping(doc_id, *, error, requeue):
        cleared.append((doc_id, error, requeue))

    async def observe(*_args, **_kwargs):
        return None

    def rag_targets():
        return None, "kb"

    async def remote_docs(_client, _kb_id):
        return [{"id": "kept-doc", "name": "phenomenon_kept.txt", "status": "existed"}]

    monkeypatch.setattr(
        PhenomenonIndexPGManager, "promote_observing", staticmethod(promote)
    )
    monkeypatch.setattr(
        PhenomenonIndexPGManager, "cards_with_source_drift", staticmethod(no_cards)
    )
    monkeypatch.setattr(
        PhenomenonIndexPGManager, "cards_with_invalid_mapping", staticmethod(no_cards)
    )
    monkeypatch.setattr(
        PhenomenonIndexPGManager, "stuck_parsing_cards", staticmethod(no_cards)
    )
    monkeypatch.setattr(
        PhenomenonIndexPGManager, "observe_orphan", staticmethod(observe)
    )
    monkeypatch.setattr(PhenomenonIndexPGManager, "list_mapped_pairs", staticmethod(pairs))
    monkeypatch.setattr(
        PhenomenonIndexPGManager, "get_card_by_rag_doc", staticmethod(card_for)
    )
    monkeypatch.setattr(
        PhenomenonIndexPGManager, "set_searchable", staticmethod(set_searchable)
    )
    monkeypatch.setattr(
        PhenomenonIndexPGManager, "clear_mapping", staticmethod(clear_mapping)
    )
    monkeypatch.setattr(
        PhenomenonIndexService, "_rag_targets", staticmethod(rag_targets)
    )
    monkeypatch.setattr(
        PhenomenonIndexService, "_list_all_remote_docs", staticmethod(remote_docs)
    )

    async def no_repair():
        return {"repaired": 0, "signals_dropped": 0}

    monkeypatch.setattr(
        PhenomenonIndexService, "_repair_case_derived", staticmethod(no_repair)
    )

    stats = await PhenomenonIndexService.reconcile()

    assert stats["stale_kb"] == 1
    assert stats["missing"] == 0
    assert stats["orphans"] == 0
    assert cleared == [("report:r", "kb_changed", True)]
    assert searchable == [("report:r", False)]


@pytest.mark.asyncio
async def test_repair_case_derived_aligns_operation_and_fingerprint(monkeypatch):
    """案例的 operation 与指纹都按源报告重算；已对齐的不重复写。"""
    from latency.database.managers.diag_case_library import DiagCaseLibraryPGManager

    seen: list[tuple[str, str | None, str]] = []

    async def refresh(case_id, operation, source_fault_hash):
        seen.append((case_id, operation, source_fault_hash))
        return SimpleNamespace(id=case_id)

    async def drop_signals():
        return 7

    set_only = {
        "report": {"title": "r"},
        "basic_info": {"operation": "SET"},
        "faults": [{"id": "F01", "title": "SET 超时", "status": "confirmed",
                    "conclusion": {"one_line_conclusion": "SET 超时"}}],
        "statistics": {"stage_breakdowns": [
            {"operation": "GET", "stages": []},
            {"operation": "SET", "stages": [{"name": "set_client"}]},
        ]},
    }
    expected = service.extractor.compute_source_fault_hash(
        set_only["faults"][0], "F01", "SET"
    )

    async def bound():
        return [
            SimpleNamespace(
                id="case-1", report_id="report_a", source_fault_id="F01",
                operation="MIXED", source_fault_hash="stale-hash",
            ),
            # 已对齐：operation 与指纹都与重算结果一致，不应被写。
            SimpleNamespace(
                id="case-2", report_id="report_b", source_fault_id="F01",
                operation="SET", source_fault_hash=expected,
            ),
        ]

    async def same_case():
        return None

    def load(report_id):
        return set_only, None, None

    monkeypatch.setattr(
        DiagCaseLibraryPGManager, "cases_with_report_binding", staticmethod(bound)
    )
    monkeypatch.setattr(
        DiagCaseLibraryPGManager, "refresh_case_derived", staticmethod(refresh)
    )
    monkeypatch.setattr(
        DiagCaseLibraryPGManager, "drop_operation_signals", staticmethod(drop_signals)
    )
    monkeypatch.setattr(service, "_load_report_payload", load)

    stats = await PhenomenonIndexService._repair_case_derived()

    assert stats == {"repaired": 1, "signals_dropped": 7}
    assert seen == [("case-1", "SET", expected)]
