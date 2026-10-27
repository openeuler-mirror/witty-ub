from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from latency.ENUM.case_library import DiagCaseStatus
from latency.database.managers.diag_case_library import DiagCaseLibraryPGManager as Manager
from latency.schemas.diag_case_library import DiagCaseLibraryModel, SearchDiagCaseLibraryRequest
from latency.services.report_import import derive_report_id, normalize_import_payload
from latency.services.diag_case_library import DiagCaseLibraryService
from latency.services.report_review import ReportReviewService
from latency.exceptions import BadRequestBizException, ConflictBizException


def case(status, closed_loop):
    return DiagCaseLibraryModel(
        title="测试案例", symptom_summary="请求失败", root_cause_summary="已定位原因",
        status=status, verification_json={"closed_loop": closed_loop},
    )


def test_formal_library_rejects_all_unverified_even_with_explicit_statuses():
    request = SearchDiagCaseLibraryRequest(include_status=["draft", "confirmed", "archived"])
    assert not Manager._matches_search_filters(case(DiagCaseStatus.DRAFT, True), request)
    assert not Manager._matches_search_filters(case(DiagCaseStatus.CONFIRMED, False), request)
    assert not Manager._matches_search_filters(case(DiagCaseStatus.ARCHIVED, True), request)
    assert Manager._matches_search_filters(case(DiagCaseStatus.CONFIRMED, True), request)


def test_pending_is_separate_from_formal_and_archived():
    request = SearchDiagCaseLibraryRequest(scope="pending", include_status=["draft", "confirmed", "archived"])
    assert Manager._matches_search_filters(case(DiagCaseStatus.DRAFT, False), request)
    assert Manager._matches_search_filters(case(DiagCaseStatus.CONFIRMED, False), request)
    assert not Manager._matches_search_filters(case(DiagCaseStatus.CONFIRMED, True), request)
    assert not Manager._matches_search_filters(case(DiagCaseStatus.ARCHIVED, False), request)


def test_external_report_identity_does_not_depend_on_filename():
    payload = {"report": {"title": "外部报告"}, "conclusion": {"one_line_conclusion": "请求失败"}}
    assert derive_report_id("first.json", payload) == derive_report_id("renamed.json", payload)
    normalized = normalize_import_payload(payload)
    assert "faults" not in payload
    assert normalized["faults"][0]["id"] == "F01"
    assert normalized["import_normalization"]["original_layout"] == "flat"


async def test_invalid_fault_does_not_write_report_approval(monkeypatch):
    snapshot = SimpleNamespace(
        sidecar_state="ok", sidecar_hash="a" * 64, payload={"faults": [{"id": "F01"}]},
    )
    confirm = AsyncMock()
    monkeypatch.setattr(ReportReviewService, "_unique_report", lambda _: snapshot)
    monkeypatch.setattr(ReportReviewService, "confirm", confirm)
    with pytest.raises(BadRequestBizException):
        await DiagCaseLibraryService.verify_report_fault(
            "report_test", "F99", "a" * 64, "operator", "真实观察",
        )
    confirm.assert_not_awaited()


async def test_stale_report_cannot_be_approved_by_validation_action(monkeypatch):
    snapshot = SimpleNamespace(sidecar_state="ok", sidecar_hash="b" * 64)
    confirm = AsyncMock()
    monkeypatch.setattr(ReportReviewService, "_unique_report", lambda _: snapshot)
    monkeypatch.setattr(ReportReviewService, "confirm", confirm)
    with pytest.raises(ConflictBizException):
        await DiagCaseLibraryService.verify_report_fault(
            "report_test", "F01", "a" * 64, "operator", "真实观察",
        )
    confirm.assert_not_awaited()
