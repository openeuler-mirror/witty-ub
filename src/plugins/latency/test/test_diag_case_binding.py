# Copyright (c) Huawei Technologies Co., Ltd. 2023-2025. All rights reserved.
"""Case ↔ report fault binding contract tests."""
from __future__ import annotations

from pathlib import Path

import pytest

from latency.ENUM.case_library import DiagCaseStatus
from latency.exceptions import (
    BadRequestBizException,
    ConflictBizException,
    UnprocessableBizException,
)
from latency.schemas.diag_case_library import (
    ConfirmDiagCaseRequest,
    CreateDiagCaseDraftRequest,
    DiagCaseLibraryModel,
    EvidenceModel,
    RemediationStepModel,
)
from latency.services.diag_case_library import DiagCaseLibraryService
from latency.services.report_phenomenon import compute_sidecar_hash, sha256_hex
from latency.services.report_review import ReportReviewService, ReportSnapshot

SIDECAR_HASH = "a" * 64


def _request(**overrides) -> CreateDiagCaseDraftRequest:
    values = {
        "log_type": "KVCache",
        "source": "internal",
        "title": "GET 阻塞",
        "symptom_summary": "对象不存在时 GET 等待",
        "root_cause_summary": "订阅等待",
        "report_id": "report_r",
        "source_fault_id": "F01",
        "expected_sidecar_hash": SIDECAR_HASH,
    }
    values.update(overrides)
    return CreateDiagCaseDraftRequest(**values)


def _snapshot(fault_id: str = "F01") -> ReportSnapshot:
    payload = {
        "report": {"title": "报告"},
        "faults": [
            {
                "id": fault_id,
                "title": "GET 阻塞",
                "status": "confirmed",
                "category": "error",
                "conclusion": {
                    "first_level_label": "Worker故障",
                    "second_level_label": "Worker故障-进程退出",
                    "one_line_conclusion": "GET 等待",
                },
                "root_cause": {"confirmed_root_cause": "订阅等待"},
                "solution": {"short_term": ["重启 Worker"]},
                "evidence_traces": [{"trace_id": "t-1", "status_code": "3"}],
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


async def _patch_confirmed(monkeypatch, snapshot: ReportSnapshot) -> None:
    async def fake_require(report_id, expected_sidecar_hash=None):
        return snapshot

    monkeypatch.setattr(
        ReportReviewService, "require_confirmed", staticmethod(fake_require)
    )


async def test_binding_rejects_synthetic_fault_id(monkeypatch):
    await _patch_confirmed(monkeypatch, _snapshot())
    with pytest.raises(BadRequestBizException):
        await DiagCaseLibraryService._resolve_binding(
            _request(source_fault_id="auto:abc:01")
        )


async def test_binding_rejects_unreadable_report(monkeypatch):
    async def fake_require(report_id, expected_sidecar_hash=None):
        raise UnprocessableBizException(
            message="报告数据不完整", detail="sidecar_missing: 侧车 JSON 不存在"
        )

    monkeypatch.setattr(
        ReportReviewService, "require_confirmed", staticmethod(fake_require)
    )
    with pytest.raises(UnprocessableBizException) as exc_info:
        await DiagCaseLibraryService._resolve_binding(_request())
    assert "sidecar_missing" in exc_info.value.detail


async def test_binding_returns_server_fingerprint(monkeypatch):
    await _patch_confirmed(monkeypatch, _snapshot())
    binding = await DiagCaseLibraryService._resolve_binding(_request())
    assert binding is not None
    assert binding["doc"].source_fault_hash
    assert binding["labels"]["second_level_label"] == "Worker故障-进程退出"
    assert len(binding["snapshot_hash"] or "") == 64
    assert binding["sidecar_hash"] == _snapshot().sidecar_hash
    assert len(binding["sidecar_hash"] or "") == 64


async def test_confirm_rejects_changed_source_fault(monkeypatch):
    case = DiagCaseLibraryModel(
        id="case-1",
        status=DiagCaseStatus.DRAFT,
        report_id="report_r",
        source_fault_id="F01",
        source_fault_hash="old-hash",
        source_sidecar_hash=SIDECAR_HASH,
        evidence_json=[EvidenceModel(kind="trace", ref="trace-1")],
        remediation_json=[RemediationStepModel(step=1, action="重启 Worker")],
        status_codes=["3"],
    )
    snapshot = _snapshot()
    captured: dict = {}

    async def fake_get(case_id):
        return case

    async def fake_require(report_id, expected_sidecar_hash=None):
        captured["expected_sidecar_hash"] = expected_sidecar_hash
        return snapshot

    monkeypatch.setattr(
        "latency.database.managers.diag_case_library.DiagCaseLibraryPGManager.get_case",
        fake_get,
    )
    monkeypatch.setattr(
        ReportReviewService, "require_confirmed", staticmethod(fake_require)
    )
    with pytest.raises(ConflictBizException) as exc_info:
        await DiagCaseLibraryService.confirm_case(
            "case-1", ConfirmDiagCaseRequest(confirmed_by="ops")
        )
    assert captured["expected_sidecar_hash"] == SIDECAR_HASH
    assert "版本" in exc_info.value.message


def test_static_routes_are_registered_before_dynamic_ones():
    from latency.routers.case_library import router as case_router
    from latency.routers.phenomenon import router as phenomenon_router

    case_get_paths = [
        route.path for route in case_router.routes if "GET" in (route.methods or ())
    ]
    assert case_get_paths.index("/case_library/list") < case_get_paths.index(
        "/case_library/{case_id}"
    )
    assert case_get_paths.index("/case_library/categories") < case_get_paths.index(
        "/case_library/{case_id}"
    )

    phenomenon_paths = [route.path for route in phenomenon_router.routes]
    dynamic = "/phenomenon/{doc_id:path}"
    assert phenomenon_paths.index("/phenomenon/search") < phenomenon_paths.index(
        dynamic
    )
    assert phenomenon_paths.index("/phenomenon/index") < phenomenon_paths.index(
        dynamic
    )
