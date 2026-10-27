# Copyright (c) Huawei Technologies Co., Ltd. 2023-2025. All rights reserved.
"""Case classification snapshot and label filtering tests."""
from __future__ import annotations

from pathlib import Path

import pytest

from latency.ENUM.case_library import DiagCaseStatus
from latency.database.managers.diag_case_library import (
    DiagCaseLibraryPGManager as Manager,
)
from latency.exceptions import (
    BadRequestBizException,
    ConflictBizException,
    UnprocessableBizException,
)
from latency.schemas.diag_case_library import (
    CreateDiagCaseDraftRequest,
    DiagCaseLibraryModel,
    SearchDiagCaseLibraryRequest,
)
from latency.services import label_taxonomy
from latency.services.diag_case_library import DiagCaseLibraryService
from latency.services.phenomenon_index import _select_bound_case
from latency.services.report_phenomenon import (
    compute_sidecar_hash,
    extract_report,
)
from latency.services.report_review import ReportReviewService, ReportSnapshot

SIDECAR_HASH = "a" * 64


def _labels(index: int = 0) -> tuple[str, str]:
    options = label_taxonomy.label_options()
    pair = options["pairs"][index]
    return pair["first_level_label"], pair["second_level_labels"][0]


def _request(**overrides) -> CreateDiagCaseDraftRequest:
    values = {
        "log_type": "KVCache",
        "source": "internal",
        "title": "GET 阻塞",
        "symptom_summary": "对象不存在时 GET 等待",
        "root_cause_summary": "订阅等待",
    }
    values.update(overrides)
    return CreateDiagCaseDraftRequest(**values)


def _snapshot(labels: tuple[str, str] | None = None) -> ReportSnapshot:
    first, second = labels or _labels()
    payload = {
        "report": {"title": "报告"},
        "basic_info": {"operation": "GET"},
        "faults": [
            {
                "id": "F01",
                "title": "GET 阻塞",
                "status": "confirmed",
                "category": "latency",
                "conclusion": {
                    "first_level_label": first,
                    "second_level_label": second,
                    "one_line_conclusion": "GET 等待",
                },
                "root_cause": {"confirmed_root_cause": "订阅等待"},
                "evidence_traces": [{"trace_id": "t-1", "status_code": "3"}],
                "solution": {"short_term": ["重启 Worker"]},
            }
        ],
    }
    return ReportSnapshot(
        report_id="report_r",
        kb_dir=None,
        html=Path("/tmp/report_r.html"),
        payload=payload,
        sidecar_hash=compute_sidecar_hash(payload),
        sidecar_state="ok",
        title="报告",
    )


def _patch_confirmed(monkeypatch, snapshot: ReportSnapshot) -> None:
    async def fake_require(report_id, expected_sidecar_hash=None):
        return snapshot

    monkeypatch.setattr(
        ReportReviewService, "require_confirmed", staticmethod(fake_require)
    )


def _patch_add_draft(monkeypatch) -> dict:
    captured: dict = {}

    async def add_draft(case):
        captured["case"] = case
        return case.id

    monkeypatch.setattr(
        Manager, "add_draft", staticmethod(add_draft)
    )
    return captured


# ---------------------------------------------------------------------------
# 独立案例的可选分类
# ---------------------------------------------------------------------------
def test_independent_case_can_leave_labels_empty():
    assert DiagCaseLibraryService._independent_labels(_request()) is None


def test_independent_case_stores_a_valid_label_snapshot():
    first, second = _labels()

    labels = DiagCaseLibraryService._independent_labels(
        _request(first_level_label=first, second_level_label=second)
    )

    assert labels["first_level_label"] == first
    assert labels["second_level_label"] == second
    assert labels["label_taxonomy_version"] == label_taxonomy.label_options()["version"]
    assert labels["source_label_hash"] == label_taxonomy.label_snapshot_hash(
        first, second, labels["label_taxonomy_version"]
    )


@pytest.mark.parametrize(
    "first_level_label, second_level_label, fragment",
    [
        (None, "某个二级", "second_without_first"),
        ("不存在的分类", "不存在-子类", "unknown_first_level_label"),
    ],
)
def test_independent_case_rejects_invalid_labels(
    first_level_label, second_level_label, fragment
):
    with pytest.raises(BadRequestBizException) as exc_info:
        DiagCaseLibraryService._independent_labels(
            _request(
                first_level_label=first_level_label,
                second_level_label=second_level_label,
            )
        )
    assert fragment in exc_info.value.detail


def test_independent_case_reports_a_missing_taxonomy(monkeypatch):
    def unavailable(*args, **kwargs):
        raise label_taxonomy.TaxonomyError("label_taxonomy_missing")

    monkeypatch.setattr(label_taxonomy, "validate_labels", unavailable)

    with pytest.raises(UnprocessableBizException) as exc_info:
        DiagCaseLibraryService._independent_labels(
            _request(first_level_label="任意", second_level_label="任意-子类")
        )
    assert "label_taxonomy_missing" in exc_info.value.detail


async def test_independent_draft_persists_the_snapshot(monkeypatch):
    first, second = _labels()
    captured = _patch_add_draft(monkeypatch)

    created = await DiagCaseLibraryService.create_draft(
        _request(first_level_label=first, second_level_label=second)
    )

    case = captured["case"]
    assert created.case_id == case.id
    assert case.first_level_label == first
    assert case.second_level_label == second
    assert case.label_taxonomy_version == label_taxonomy.label_options()["version"]
    assert len(case.source_label_hash or "") == 64


# ---------------------------------------------------------------------------
# 报告派生案例强制使用报告分类
# ---------------------------------------------------------------------------
async def test_report_bound_draft_overrides_client_labels(monkeypatch):
    server_first, server_second = _labels()
    client_first, client_second = _labels(index=1)
    snapshot = _snapshot((server_first, server_second))
    _patch_confirmed(monkeypatch, snapshot)
    captured = _patch_add_draft(monkeypatch)

    await DiagCaseLibraryService.create_draft(
        _request(
            report_id="report_r",
            source_fault_id="F01",
            expected_sidecar_hash=SIDECAR_HASH,
            first_level_label=client_first,
            second_level_label=client_second,
        )
    )

    case = captured["case"]
    assert case.first_level_label == server_first
    assert case.second_level_label == server_second
    assert case.label_taxonomy_version == label_taxonomy.label_options()["version"]
    assert case.source_sidecar_hash == snapshot.sidecar_hash
    assert case.source_label_hash == label_taxonomy.label_snapshot_hash(
        server_first, server_second, case.label_taxonomy_version
    )


async def test_draft_is_discarded_when_the_report_changes_during_insert(monkeypatch):
    snapshot = _snapshot()
    calls = {"count": 0}

    async def flaky(report_id, expected_sidecar_hash=None):
        calls["count"] += 1
        if calls["count"] >= 3:
            raise ConflictBizException(
                message="报告版本已变化", detail="页面所见版本与当前侧车不一致"
            )
        return snapshot

    monkeypatch.setattr(
        ReportReviewService, "require_confirmed", staticmethod(flaky)
    )
    captured = _patch_add_draft(monkeypatch)
    deleted: dict = {}

    async def delete_case(case_id):
        deleted["case_id"] = case_id

    monkeypatch.setattr(Manager, "delete_case", staticmethod(delete_case))

    with pytest.raises(ConflictBizException):
        await DiagCaseLibraryService.create_draft(
            _request(
                report_id="report_r",
                source_fault_id="F01",
                expected_sidecar_hash=SIDECAR_HASH,
            )
        )
    assert deleted["case_id"] == captured["case"].id


async def test_report_bound_draft_rejects_an_invalid_fault_classification(monkeypatch):
    snapshot = _snapshot()
    snapshot.payload["faults"][0]["conclusion"]["first_level_label"] = "不存在的分类"
    _patch_confirmed(monkeypatch, snapshot)
    _patch_add_draft(monkeypatch)

    with pytest.raises(UnprocessableBizException) as exc_info:
        await DiagCaseLibraryService.create_draft(
            _request(
                report_id="report_r",
                source_fault_id="F01",
                expected_sidecar_hash=SIDECAR_HASH,
            )
        )
    assert "unknown_first_level_label" in exc_info.value.detail


async def test_report_bound_draft_rejects_an_unavailable_taxonomy(monkeypatch):
    snapshot = _snapshot()
    _patch_confirmed(monkeypatch, snapshot)
    _patch_add_draft(monkeypatch)

    def unavailable(fault):
        return {
            "first_level_label": None,
            "second_level_label": None,
            "label_status": "unavailable",
            "label_error": "label_taxonomy_unavailable",
            "label_taxonomy_version": None,
        }

    monkeypatch.setattr(
        ReportReviewService, "labels_from_fault", staticmethod(unavailable)
    )

    with pytest.raises(UnprocessableBizException) as exc_info:
        await DiagCaseLibraryService.create_draft(
            _request(
                report_id="report_r",
                source_fault_id="F01",
                expected_sidecar_hash=SIDECAR_HASH,
            )
        )
    assert "label_taxonomy_unavailable" in exc_info.value.detail


# ---------------------------------------------------------------------------
# 分类筛选
# ---------------------------------------------------------------------------
def test_scan_binding_requires_the_label_snapshot_to_match():
    payload = _snapshot().payload
    doc = extract_report("report_r", payload).faults[0]
    first, second = _labels()
    version = label_taxonomy.label_options()["version"]
    valid_hash = label_taxonomy.label_snapshot_hash(first, second, version)

    changed = DiagCaseLibraryModel(
        id="case-changed",
        status=DiagCaseStatus.CONFIRMED,
        source_fault_id="F01",
        source_fault_hash=doc.source_fault_hash,
        source_label_hash="b" * 64,
        verification_json={"closed_loop": True},
    )
    valid = DiagCaseLibraryModel(
        id="case-valid",
        status=DiagCaseStatus.CONFIRMED,
        source_fault_id="F01",
        source_fault_hash=doc.source_fault_hash,
        source_label_hash=valid_hash,
        verification_json={"closed_loop": True},
    )
    legacy = DiagCaseLibraryModel(
        id="case-legacy",
        status=DiagCaseStatus.CONFIRMED,
        source_fault_id="F01",
        source_fault_hash=doc.source_fault_hash,
        verification_json={"closed_loop": True},
    )

    assert _select_bound_case(doc, [changed]) is None
    assert _select_bound_case(doc, [changed, valid]) is valid
    assert _select_bound_case(doc, [legacy]) is legacy


def _case(**overrides) -> DiagCaseLibraryModel:
    values = {
        "id": "case-1",
        "status": DiagCaseStatus.CONFIRMED,
        "title": "GET 阻塞",
        "symptom_summary": "GET 等待",
        "root_cause_summary": "订阅等待",
        "status_codes": ["3"],
        # 正式案例库只收录已闭环案例。
        "verification_json": {"closed_loop": True},
    }
    values.update(overrides)
    return DiagCaseLibraryModel(**values)


def test_filter_matches_first_and_second_level_labels():
    first, second = _labels()
    other_first, other_second = _labels(index=1)
    case = _case(first_level_label=first, second_level_label=second)

    assert Manager._matches_search_filters(
        case, SearchDiagCaseLibraryRequest(first_level_label=first)
    )
    assert Manager._matches_search_filters(
        case,
        SearchDiagCaseLibraryRequest(
            first_level_label=first, second_level_label=second
        ),
    )
    assert not Manager._matches_search_filters(
        case,
        SearchDiagCaseLibraryRequest(
            first_level_label=other_first, second_level_label=other_second
        ),
    )


def test_unclassified_only_selects_cases_without_labels():
    first, second = _labels()

    assert Manager._matches_search_filters(
        _case(), SearchDiagCaseLibraryRequest(unclassified_only=True)
    )
    assert not Manager._matches_search_filters(
        _case(first_level_label=first, second_level_label=second),
        SearchDiagCaseLibraryRequest(unclassified_only=True),
    )


def test_label_filter_still_respects_the_status_gate():
    first, second = _labels()
    draft = _case(
        status=DiagCaseStatus.DRAFT,
        first_level_label=first,
        second_level_label=second,
    )
    request = SearchDiagCaseLibraryRequest(first_level_label=first)

    assert not Manager._matches_search_filters(draft, request)
    assert Manager._matches_search_filters(
        draft, SearchDiagCaseLibraryRequest(scope="pending",
                                            first_level_label=first,
                                            include_status=[DiagCaseStatus.DRAFT])
    )


async def test_search_rejects_second_level_without_first():
    with pytest.raises(BadRequestBizException):
        await DiagCaseLibraryService.search_cases(
            SearchDiagCaseLibraryRequest(second_level_label="某个二级")
        )
