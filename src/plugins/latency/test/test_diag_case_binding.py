# Copyright (c) Huawei Technologies Co., Ltd. 2023-2025. All rights reserved.
"""Case ↔ report fault binding contract tests."""
from __future__ import annotations

import pytest

from latency.ENUM.case_library import DiagCaseStatus
from latency.exceptions import BadRequestBizException, ConflictBizException
from latency.schemas.diag_case_library import (
    ConfirmDiagCaseRequest,
    CreateDiagCaseDraftRequest,
    DiagCaseLibraryModel,
    EvidenceModel,
    RemediationStepModel,
)
from latency.services.diag_case_library import DiagCaseLibraryService
from latency.services.phenomenon_index import PhenomenonIndexService
from latency.services.report_phenomenon import PhenomenonDoc, sha256_hex


def _request(**overrides) -> CreateDiagCaseDraftRequest:
    values = {
        "log_type": "KVCache",
        "source": "internal",
        "title": "GET 阻塞",
        "symptom_summary": "对象不存在时 GET 等待",
        "root_cause_summary": "订阅等待",
        "report_id": "report_r",
        "source_fault_id": "F01",
    }
    values.update(overrides)
    return CreateDiagCaseDraftRequest(**values)


def _doc(fault_id: str = "F01", source_hash: str = "hash-a") -> PhenomenonDoc:
    return PhenomenonDoc(
        doc_id=f"report:report_r:{fault_id}",
        kind="report",
        content_source="report",
        title="GET 阻塞",
        symptom="对象不存在时 GET 等待",
        text="GET 阻塞",
        content_hash=sha256_hex("GET 阻塞"),
        verification="report_only",
        report_id="report_r",
        source_fault_id=fault_id,
        source_fault_hash=source_hash,
    )


async def test_binding_rejects_synthetic_fault_id(monkeypatch):
    async def fake(report_id, fault_id):
        return _doc("auto:abc:01"), None

    monkeypatch.setattr(
        PhenomenonIndexService, "resolve_current_fault", staticmethod(fake)
    )
    with pytest.raises(BadRequestBizException):
        await DiagCaseLibraryService._resolve_binding(_request())


async def test_binding_rejects_unreadable_report(monkeypatch):
    async def fake(report_id, fault_id):
        return None, "sidecar_missing"

    monkeypatch.setattr(
        PhenomenonIndexService, "resolve_current_fault", staticmethod(fake)
    )
    with pytest.raises(BadRequestBizException) as exc_info:
        await DiagCaseLibraryService._resolve_binding(_request())
    assert "sidecar_missing" in exc_info.value.detail


async def test_binding_returns_server_fingerprint(monkeypatch):
    async def fake(report_id, fault_id):
        return _doc(), None

    monkeypatch.setattr(
        PhenomenonIndexService, "resolve_current_fault", staticmethod(fake)
    )
    doc = await DiagCaseLibraryService._resolve_binding(_request())
    assert doc is not None
    assert doc.source_fault_hash == "hash-a"


async def test_confirm_rejects_changed_source_fault(monkeypatch):
    case = DiagCaseLibraryModel(
        id="case-1",
        status=DiagCaseStatus.DRAFT,
        report_id="report_r",
        source_fault_id="F01",
        source_fault_hash="old-hash",
        evidence_json=[EvidenceModel(kind="trace", ref="trace-1")],
        remediation_json=[RemediationStepModel(step=1, action="重启 Worker")],
        status_codes=["3"],
    )

    async def fake_get(case_id):
        return case

    async def fake_resolve(report_id, fault_id):
        return _doc(source_hash="new-hash"), None

    monkeypatch.setattr(
        "latency.database.managers.diag_case_library.DiagCaseLibraryPGManager.get_case",
        fake_get,
    )
    monkeypatch.setattr(
        PhenomenonIndexService, "resolve_current_fault", staticmethod(fake_resolve)
    )
    with pytest.raises(ConflictBizException) as exc_info:
        await DiagCaseLibraryService.confirm_case(
            "case-1", ConfirmDiagCaseRequest(confirmed_by="ops")
        )
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
