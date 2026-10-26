# Copyright (c) Huawei Technologies Co., Ltd. 2023-2025. All rights reserved.
"""Report-level human confirmation and case → report navigation tests.

Reports live in a pytest ``tmp_path`` (``WITTY_REPORT_DIR``); the PostgreSQL
index row is replaced by an in-memory fake so no database is required.
"""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace

import httpx
import pytest
from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError

from latency.access.fastapi_server import (
    bad_request_exception_handler,
    conflict_exception_handler,
    not_found_exception_handler,
    request_validation_exception_handler,
    unprocessable_exception_handler,
)
from latency.database.engine import PGManager
from latency.database.managers.phenomenon_index import PhenomenonIndexPGManager
from latency.exceptions import (
    BadRequestBizException,
    ConflictBizException,
    NotFoundBizException,
    UnprocessableBizException,
)
from latency.routers import diagnostic_report as diagnostic_report_router
from latency.schemas.diag_case_library import DiagCaseLibraryModel
from latency.schemas.diagnostic_report import (
    DiagnosticCaseRefModel,
    DiagnosticReportDetailItem,
    FaultSummaryModel,
    GetDiagnosticReportMsg,
)
from latency.services import label_taxonomy
from latency.services.diagnostic_report import DiagnosticReportService
from latency.services.report_phenomenon import (
    compute_sidecar_hash,
    compute_source_fault_hash,
)
from latency.services.report_review import (
    ReportReviewService,
    require_operator,
)

REPORT_ID = "report_kb_20261021_101500"
KB_DIR = "kb-1"
SIDECAR_HASH = "a" * 64
HTML_BODY = "<html><body>report</body></html>"


def _labels() -> tuple[str, str]:
    options = label_taxonomy.label_options()
    first = options["first_level_labels"][0]
    pair = next(
        item for item in options["pairs"] if item["first_level_label"] == first
    )
    return first, pair["second_level_labels"][0]


def _sidecar(report_id: str = REPORT_ID) -> dict:
    first, second = _labels()
    return {
        "report": {"title": "KVCache 时延诊断报告", "generated_at": "2026-10-21 10:15:00"},
        "basic_info": {
            "kb_id": KB_DIR,
            "kb_name": "YXH LOGS",
            "operation": "GET",
        },
        "faults": [
            {
                "id": "F01",
                "title": "GET 阻塞",
                "status": "confirmed",
                "category": "latency",
                "conclusion": {
                    "first_level_label": first,
                    "second_level_label": second,
                    "one_line_conclusion": "GET 等待约 1.8 秒",
                },
                "root_cause": {"confirmed_root_cause": "订阅等待"},
                "evidence_traces": [{"trace_id": "t-1", "status_code": "3"}],
                "solution": {"short_term": ["重启 Worker"]},
            }
        ],
    }


def _write_report(
    root: Path,
    name: str = REPORT_ID,
    *,
    kb_dir: str | None = KB_DIR,
    sidecar: dict | None | bool = True,
) -> Path:
    directory = root / kb_dir if kb_dir else root
    directory.mkdir(parents=True, exist_ok=True)
    html = directory / f"{name}.html"
    html.write_text(HTML_BODY, encoding="utf-8")
    if sidecar is True:
        sidecar = _sidecar(name)
    if isinstance(sidecar, dict):
        html.with_suffix(".json").write_text(
            json.dumps(sidecar, ensure_ascii=False), encoding="utf-8"
        )
    return html


def _row(**overrides) -> SimpleNamespace:
    values = {
        "report_id": REPORT_ID,
        "index_status": "pending",
        "index_error": None,
        "report_available": True,
        "confirmed_by": None,
        "confirmed_at": None,
        "confirmed_sidecar_hash": None,
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def _install_report_index(monkeypatch, row):
    async def get_report_index(report_id):
        return row

    monkeypatch.setattr(
        PhenomenonIndexPGManager, "get_report_index", staticmethod(get_report_index)
    )


@pytest.fixture(autouse=True)
def report_dir(tmp_path, monkeypatch) -> Path:
    root = tmp_path / "reports"
    root.mkdir()
    monkeypatch.setenv("WITTY_REPORT_DIR", str(root))
    return root


# ---------------------------------------------------------------------------
# 操作人
# ---------------------------------------------------------------------------
def test_operator_header_wins_over_body_value():
    assert require_operator("body-user", "header-user") == "header-user"
    assert require_operator("  body-user  ", None) == "body-user"
    assert require_operator(None, "  header-user  ") == "header-user"


def test_operator_is_required():
    with pytest.raises(BadRequestBizException):
        require_operator(None, None)
    with pytest.raises(BadRequestBizException):
        require_operator("   ", "")


def test_operator_length_is_bounded():
    with pytest.raises(BadRequestBizException):
        require_operator("x" * 65, None)


def test_trusted_mode_accepts_only_the_gateway_header(monkeypatch):
    monkeypatch.setenv("WITTY_REQUIRE_TRUSTED_OPERATOR", "1")

    assert require_operator("body-user", "gateway-user") == "gateway-user"
    with pytest.raises(BadRequestBizException) as exc_info:
        require_operator("body-user", None)
    assert "可信操作人" in exc_info.value.message


# ---------------------------------------------------------------------------
# 整份报告审核状态
# ---------------------------------------------------------------------------
async def test_review_status_is_unconfirmed_without_a_stored_row(report_dir, monkeypatch):
    _write_report(report_dir)
    _install_report_index(monkeypatch, None)

    state = await ReportReviewService.review_status(REPORT_ID)

    assert state["review_status"] == "unconfirmed"
    assert state["current_sidecar_hash"] == compute_sidecar_hash(_sidecar())
    assert state["review_confirmed_by"] is None


async def test_review_status_is_confirmed_when_hash_matches(report_dir, monkeypatch):
    _write_report(report_dir)
    confirmed_at = datetime(2026, 10, 21, 11, 0, 0)
    _install_report_index(
        monkeypatch,
        _row(
            confirmed_by="alice",
            confirmed_at=confirmed_at,
            confirmed_sidecar_hash=compute_sidecar_hash(_sidecar()),
        ),
    )

    state = await ReportReviewService.review_status(REPORT_ID)

    assert state["review_status"] == "confirmed"
    assert state["review_confirmed_by"] == "alice"
    assert state["review_confirmed_at"] == confirmed_at


async def test_review_status_is_stale_when_the_sidecar_changed(report_dir, monkeypatch):
    _write_report(report_dir)
    _install_report_index(
        monkeypatch,
        _row(confirmed_by="alice", confirmed_sidecar_hash="b" * 64),
    )

    state = await ReportReviewService.review_status(REPORT_ID)

    assert state["review_status"] == "stale"


async def test_review_status_is_unavailable_without_a_sidecar(report_dir, monkeypatch):
    _write_report(report_dir, sidecar=None)
    _install_report_index(monkeypatch, _row(confirmed_sidecar_hash=SIDECAR_HASH))

    state = await ReportReviewService.review_status(REPORT_ID)

    assert state["review_status"] == "unavailable"
    assert state["current_sidecar_hash"] is None


async def test_duplicate_report_ids_are_rejected(report_dir):
    _write_report(report_dir, kb_dir="kb-a")
    _write_report(report_dir, kb_dir="kb-b")

    with pytest.raises(ConflictBizException):
        ReportReviewService._unique_report(REPORT_ID)


# ---------------------------------------------------------------------------
# 确认动作
# ---------------------------------------------------------------------------
async def test_confirm_rejects_a_stale_page_hash(report_dir, monkeypatch):
    _write_report(report_dir)

    with pytest.raises(ConflictBizException):
        await ReportReviewService.confirm(REPORT_ID, "b" * 64, "alice")


async def test_confirm_rejects_a_missing_sidecar(report_dir):
    _write_report(report_dir, sidecar=None)

    with pytest.raises(UnprocessableBizException):
        await ReportReviewService.confirm(REPORT_ID, SIDECAR_HASH, "alice")


async def test_confirm_records_the_operator_and_keeps_the_sidecar_intact(
    report_dir, monkeypatch
):
    html = _write_report(report_dir)
    captured: dict = {}

    async def upsert(values, session=None):
        captured.update(values)

    async def get_report_index(report_id):
        return SimpleNamespace(
            confirmed_by=captured.get("confirmed_by"),
            confirmed_at=captured.get("confirmed_at"),
            confirmed_sidecar_hash=captured.get("confirmed_sidecar_hash"),
        )

    monkeypatch.setattr(
        PhenomenonIndexPGManager, "upsert_report_index", staticmethod(upsert)
    )
    monkeypatch.setattr(
        PhenomenonIndexPGManager, "get_report_index", staticmethod(get_report_index)
    )
    before = html.with_suffix(".json").read_text(encoding="utf-8")

    state = await ReportReviewService.confirm(
        REPORT_ID, compute_sidecar_hash(_sidecar()), "alice"
    )

    assert state["review_status"] == "confirmed"
    assert captured["confirmed_by"] == "alice"
    assert captured["confirmed_sidecar_hash"] == compute_sidecar_hash(_sidecar())
    assert captured["sidecar_hash"] == compute_sidecar_hash(_sidecar())
    assert captured["report_available"] is True
    assert html.with_suffix(".json").read_text(encoding="utf-8") == before


async def test_require_confirmed_blocks_unconfirmed_and_stale_reports(
    report_dir, monkeypatch
):
    _write_report(report_dir)
    _install_report_index(monkeypatch, None)

    with pytest.raises(ConflictBizException) as exc_info:
        await ReportReviewService.require_confirmed(REPORT_ID)
    assert exc_info.value.message == "报告尚未确认"

    _install_report_index(
        monkeypatch,
        _row(confirmed_by="alice", confirmed_sidecar_hash="b" * 64),
    )
    with pytest.raises(ConflictBizException) as exc_info:
        await ReportReviewService.require_confirmed(REPORT_ID)
    assert "需要重新人工确认" in exc_info.value.detail


async def test_require_confirmed_returns_the_snapshot(report_dir, monkeypatch):
    _write_report(report_dir)
    _install_report_index(
        monkeypatch,
        _row(confirmed_sidecar_hash=compute_sidecar_hash(_sidecar())),
    )

    snapshot = await ReportReviewService.require_confirmed(
        REPORT_ID, compute_sidecar_hash(_sidecar())
    )

    assert snapshot.report_id == REPORT_ID
    assert snapshot.sidecar_state == "ok"
    assert snapshot.sidecar_hash == compute_sidecar_hash(_sidecar())


async def test_require_confirmed_rejects_another_page_version(report_dir, monkeypatch):
    _write_report(report_dir)
    _install_report_index(
        monkeypatch,
        _row(confirmed_sidecar_hash=compute_sidecar_hash(_sidecar())),
    )

    with pytest.raises(ConflictBizException) as exc_info:
        await ReportReviewService.require_confirmed(REPORT_ID, "b" * 64)
    assert exc_info.value.message == "报告版本已变化"


async def test_require_confirmed_rejects_missing_sidecar(report_dir):
    _write_report(report_dir, sidecar=None)

    with pytest.raises(UnprocessableBizException) as exc_info:
        await ReportReviewService.require_confirmed(REPORT_ID)
    assert "sidecar_missing" in exc_info.value.detail


# ---------------------------------------------------------------------------
# 案例 → 报告导航
# ---------------------------------------------------------------------------
def _bound_case(payload: dict, **overrides) -> DiagCaseLibraryModel:
    fault = payload["faults"][0]
    values = {
        "id": "case-1",
        "report_id": REPORT_ID,
        "source_fault_id": "F01",
        "source_fault_hash": compute_source_fault_hash(fault, "F01", "GET"),
        "first_level_label": fault["conclusion"]["first_level_label"],
        "second_level_label": fault["conclusion"]["second_level_label"],
        "source_label_hash": label_taxonomy.label_snapshot_hash(
            fault["conclusion"]["first_level_label"],
            fault["conclusion"]["second_level_label"],
            label_taxonomy.label_options()["version"],
        ),
    }
    values.update(overrides)
    return DiagCaseLibraryModel(**values)


async def test_source_navigation_for_an_independent_case():
    case = DiagCaseLibraryModel(id="case-1")

    source = await ReportReviewService.describe_case_source(case)

    assert source["status"] == "independent"
    assert source["get_report"] is None
    assert source["get_fault"] is None
    assert source["classification_status"] == "unclassified"


async def test_source_navigation_marks_a_deleted_report():
    case = DiagCaseLibraryModel(
        id="case-1", report_id="report_gone", source_fault_id="F01"
    )

    source = await ReportReviewService.describe_case_source(case)

    assert source["status"] == "deleted"
    assert source["report_id"] == "report_gone"
    assert source["get_report"] is None


async def test_source_navigation_marks_a_missing_sidecar_unavailable(
    report_dir, monkeypatch
):
    _write_report(report_dir, sidecar=None)
    case = DiagCaseLibraryModel(
        id="case-1", report_id=REPORT_ID, source_fault_id="F01"
    )

    source = await ReportReviewService.describe_case_source(case)

    assert source["status"] == "unavailable"
    assert source["review_status"] == "unavailable"


async def test_source_navigation_marks_a_vanished_fault_stale(report_dir, monkeypatch):
    _write_report(report_dir)
    case = DiagCaseLibraryModel(
        id="case-1",
        report_id=REPORT_ID,
        source_fault_id="F99",
        source_fault_hash="c" * 64,
    )

    source = await ReportReviewService.describe_case_source(case)

    assert source["status"] == "stale"
    assert source["get_report"] is None


async def test_source_navigation_links_back_to_a_current_fault(report_dir, monkeypatch):
    payload = _sidecar()
    _write_report(report_dir, sidecar=payload)
    _install_report_index(
        monkeypatch,
        _row(confirmed_by="alice", confirmed_sidecar_hash=compute_sidecar_hash(payload)),
    )
    case = _bound_case(payload)

    source = await ReportReviewService.describe_case_source(case)

    assert source["status"] == "valid"
    assert source["review_status"] == "confirmed"
    assert source["classification_status"] == "valid"
    assert source["get_report"] == f"/diagnostic_report/{REPORT_ID}"
    assert source["get_fault"] == f"/diagnostic_report/{REPORT_ID}/faults/F01"
    assert source["source_fault_title"] == "GET 阻塞"
    assert source["current_first_level_label"] == case.first_level_label


async def test_source_navigation_detects_a_changed_classification(report_dir, monkeypatch):
    payload = _sidecar()
    _write_report(report_dir, sidecar=payload)
    _install_report_index(
        monkeypatch,
        _row(confirmed_by="alice", confirmed_sidecar_hash=compute_sidecar_hash(payload)),
    )
    case = _bound_case(payload, source_label_hash="b" * 64)

    source = await ReportReviewService.describe_case_source(case)

    assert source["classification_status"] == "changed"
    assert source["status"] == "stale"
    assert source["get_report"] is None


async def test_source_navigation_treats_an_unclassified_case_as_valid(
    report_dir, monkeypatch
):
    payload = _sidecar()
    _write_report(report_dir, sidecar=payload)
    _install_report_index(
        monkeypatch,
        _row(confirmed_by="alice", confirmed_sidecar_hash=compute_sidecar_hash(payload)),
    )
    case = _bound_case(payload, source_label_hash=None, first_level_label=None,
                       second_level_label=None)

    source = await ReportReviewService.describe_case_source(case)

    assert source["status"] == "valid"
    assert source["classification_status"] == "unclassified"


# ---------------------------------------------------------------------------
# 路由层
# ---------------------------------------------------------------------------
class _EmptyResult:
    def scalars(self):
        return self

    def all(self):
        return []


class _FakeSession:
    async def execute(self, statement):
        return _EmptyResult()


class _FakeSessionContext:
    async def __aenter__(self):
        return _FakeSession()

    async def __aexit__(self, *args):
        return False


@pytest.fixture
def api_app():
    app = FastAPI()
    app.include_router(diagnostic_report_router.router)
    app.add_exception_handler(RequestValidationError, request_validation_exception_handler)
    app.add_exception_handler(NotFoundBizException, not_found_exception_handler)
    app.add_exception_handler(ConflictBizException, conflict_exception_handler)
    app.add_exception_handler(BadRequestBizException, bad_request_exception_handler)
    app.add_exception_handler(UnprocessableBizException, unprocessable_exception_handler)
    return app


@pytest.fixture
async def client(api_app):
    transport = httpx.ASGITransport(app=api_app, raise_app_exceptions=False)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


async def test_labels_endpoint_returns_the_dictionary(client):
    response = await client.get("/diagnostic_report/labels")

    assert response.status_code == 200
    result = response.json()["result"]
    assert len(result["version"]) == 64
    assert result["first_level_labels"]
    assert result["pairs"][0]["first_level_label"] == result["first_level_labels"][0]


async def test_confirm_endpoint_requires_an_operator(client, report_dir, monkeypatch):
    _write_report(report_dir)

    response = await client.post(
        f"/diagnostic_report/{REPORT_ID}/confirm",
        json={"expected_sidecar_hash": compute_sidecar_hash(_sidecar())},
    )

    assert response.status_code == 400


async def test_confirm_endpoint_accepts_the_header_operator(
    client, report_dir, monkeypatch
):
    _write_report(report_dir)
    captured: dict = {}

    async def fake_confirm(report_id, expected_sidecar_hash, operator):
        captured.update(
            {
                "report_id": report_id,
                "expected_sidecar_hash": expected_sidecar_hash,
                "operator": operator,
            }
        )

    async def fake_get_report(report_id):
        item = DiagnosticReportDetailItem(
            report_id=report_id,
            file_name=f"{report_id}.html",
            has_sidecar=True,
            review_status="confirmed",
            review_confirmed_by=captured.get("operator"),
        )
        return GetDiagnosticReportMsg(report=item)

    monkeypatch.setattr(
        ReportReviewService, "confirm", staticmethod(fake_confirm)
    )
    monkeypatch.setattr(
        DiagnosticReportService, "get_report", staticmethod(fake_get_report)
    )

    response = await client.post(
        f"/diagnostic_report/{REPORT_ID}/confirm",
        json={"expected_sidecar_hash": compute_sidecar_hash(_sidecar())},
        headers={"X-Witty-Operator": "header-user"},
    )

    assert response.status_code == 200
    assert captured["operator"] == "header-user"
    assert response.json()["result"]["review_status"] == "confirmed"


async def test_confirm_endpoint_returns_confirmed_after_the_real_service(
    client, report_dir, monkeypatch
):
    payload = _sidecar()
    _write_report(report_dir, sidecar=payload)
    row = _row(
        confirmed_by="alice",
        confirmed_at=datetime(2026, 10, 21, 11, 0, 0),
        confirmed_sidecar_hash=compute_sidecar_hash(payload),
    )

    async def get_report_index(report_id):
        return row

    async def get_report_indexes(report_ids):
        return {REPORT_ID: row}

    async def status_counts(report_ids):
        return {}

    async def upsert(values, session=None):
        return None

    monkeypatch.setattr(
        PhenomenonIndexPGManager, "get_report_index", staticmethod(get_report_index)
    )
    monkeypatch.setattr(
        PhenomenonIndexPGManager,
        "get_report_indexes",
        staticmethod(get_report_indexes),
    )
    monkeypatch.setattr(
        PhenomenonIndexPGManager,
        "card_status_counts_for_reports",
        staticmethod(status_counts),
    )
    monkeypatch.setattr(
        PhenomenonIndexPGManager, "upsert_report_index", staticmethod(upsert)
    )
    monkeypatch.setattr(PGManager, "session", lambda: _FakeSessionContext())

    response = await client.post(
        f"/diagnostic_report/{REPORT_ID}/confirm",
        json={
            "expected_sidecar_hash": compute_sidecar_hash(payload),
            "reviewed_by": "body-user",
        },
    )

    assert response.status_code == 200
    result = response.json()["result"]
    assert result["review_status"] == "confirmed"
    assert result["review_confirmed_by"] == "alice"


async def test_confirm_endpoint_rejects_a_stale_hash(client, report_dir):
    _write_report(report_dir)

    response = await client.post(
        f"/diagnostic_report/{REPORT_ID}/confirm",
        json={"expected_sidecar_hash": "b" * 64, "reviewed_by": "alice"},
    )

    assert response.status_code == 409


@pytest.mark.parametrize(
    "payload",
    [
        {},
        {"expected_sidecar_hash": "not-a-hash", "reviewed_by": "alice"},
        {"expected_sidecar_hash": "a" * 63, "reviewed_by": "alice"},
    ],
)
async def test_confirm_endpoint_validates_the_sidecar_hash(client, payload):
    response = await client.post(
        f"/diagnostic_report/{REPORT_ID}/confirm", json=payload
    )

    assert response.status_code == 422


async def test_single_fault_read_hides_sibling_faults(report_dir, monkeypatch):
    payload = _sidecar()
    payload["faults"].append(
        {**payload["faults"][0], "id": "F02", "title": "SET 超时"}
    )
    _write_report(report_dir, sidecar=payload)
    detail = DiagnosticReportDetailItem(
        report_id=REPORT_ID,
        file_name=f"{REPORT_ID}.html",
        has_sidecar=True,
        case_refs=[
            DiagnosticCaseRefModel(
                case_id="case-f01",
                source_fault_id="F01",
                status="confirmed",
                verification="verified",
                binding_status="valid",
            ),
            DiagnosticCaseRefModel(
                case_id="case-f02",
                source_fault_id="F02",
                status="confirmed",
                verification="verified",
                binding_status="valid",
            ),
        ],
        fault_summaries=[
            FaultSummaryModel(fault_id="F01", title="GET 阻塞"),
            FaultSummaryModel(fault_id="F02", title="SET 超时"),
        ],
    )

    async def fake_decorate(items, payloads, *, with_case_refs=False):
        return [detail]

    monkeypatch.setattr(
        DiagnosticReportService, "_decorate_items", staticmethod(fake_decorate)
    )

    msg = await DiagnosticReportService.get_fault(REPORT_ID, "F01")

    assert msg.fault["id"] == "F01"
    assert [item.fault_id for item in msg.report.fault_summaries] == ["F01"]
    assert [item.source_fault_id for item in msg.report.case_refs] == ["F01"]
    assert [item.source_fault_id for item in msg.case_refs] == ["F01"]
    assert "F02" not in json.dumps(msg.model_dump(), ensure_ascii=False)
