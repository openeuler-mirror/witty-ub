# Copyright (c) Huawei Technologies Co., Ltd. 2023-2025. All rights reserved.
"""Verification fill (optimistic lock + audit) and report-gated case confirmation."""
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
    NotFoundBizException,
)
from latency.schemas.diag_case_library import (
    ConfirmDiagCaseRequest,
    DiagCaseLibraryModel,
    EvidenceModel,
    RemediationStepModel,
    UpdateDiagCaseRequest,
    VerificationModel,
)
from latency.services import label_taxonomy
from latency.services.diag_case_library import DiagCaseLibraryService
from latency.services.report_phenomenon import (
    compute_sidecar_hash,
    compute_source_fault_hash,
)
from latency.services.report_review import ReportReviewService, ReportSnapshot

SIDECAR_HASH = "a" * 64


def _labels() -> tuple[str, str]:
    options = label_taxonomy.label_options()
    first = options["first_level_labels"][0]
    pair = next(
        item for item in options["pairs"] if item["first_level_label"] == first
    )
    return first, pair["second_level_labels"][0]


def _case(**overrides) -> DiagCaseLibraryModel:
    values = {
        "id": "case-1",
        "status": DiagCaseStatus.DRAFT,
        "title": "GET 阻塞",
        "symptom_summary": "GET 等待",
        "root_cause_summary": "订阅等待",
        "status_codes": ["3"],
        "evidence_json": [EvidenceModel(kind="trace", ref="t-1")],
        "remediation_json": [RemediationStepModel(step=1, action="重启 Worker")],
    }
    values.update(overrides)
    return DiagCaseLibraryModel(**values)


def _install_case(monkeypatch, store: dict) -> None:
    async def get_case(case_id):
        return store.get(case_id)

    monkeypatch.setattr(Manager, "get_case", staticmethod(get_case))


def _install_update(
    monkeypatch, method: str, store: dict, captured: dict
) -> None:
    async def update(case_id, case, *, expected_revision=None):
        captured["case_id"] = case_id
        captured["case"] = case
        captured["expected_revision"] = expected_revision
        case.revision += 1
        store[case_id] = case
        return True

    monkeypatch.setattr(Manager, method, staticmethod(update))


def _snapshot(**overrides) -> ReportSnapshot:
    first, second = _labels()
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
    values = {
        "report_id": "report_r",
        "kb_dir": None,
        "html": Path("/tmp/report_r.html"),
        "payload": payload,
        "sidecar_hash": compute_sidecar_hash(payload),
        "sidecar_state": "ok",
        "title": "报告",
    }
    values.update(overrides)
    return ReportSnapshot(**values)


def _bound_case(snapshot: ReportSnapshot, **overrides) -> DiagCaseLibraryModel:
    fault = snapshot.payload["faults"][0]
    conclusion = fault["conclusion"]
    version = label_taxonomy.label_options()["version"]
    values = {
        "id": "case-1",
        "report_id": snapshot.report_id,
        "source_fault_id": "F01",
        "source_fault_hash": compute_source_fault_hash(fault, "F01", "GET"),
        "source_sidecar_hash": snapshot.sidecar_hash,
        "first_level_label": conclusion["first_level_label"],
        "second_level_label": conclusion["second_level_label"],
        "source_label_hash": label_taxonomy.label_snapshot_hash(
            conclusion["first_level_label"],
            conclusion["second_level_label"],
            version,
        ),
    }
    values.update(overrides)
    return _case(**values)


# ---------------------------------------------------------------------------
# 乐观锁
# ---------------------------------------------------------------------------
async def test_update_rejects_a_stale_revision(monkeypatch):
    case = _case(revision=3)
    store = {case.id: case}
    _install_case(monkeypatch, store)

    with pytest.raises(ConflictBizException) as exc_info:
        await DiagCaseLibraryService.update_case(
            case.id, UpdateDiagCaseRequest(expected_revision=2, title="新标题")
        )
    assert "revision=2" in exc_info.value.detail
    assert store[case.id].title == "GET 阻塞"


async def test_update_requires_a_field_after_stripping_the_revision(monkeypatch):
    case = _case(revision=3)
    _install_case(monkeypatch, {case.id: case})

    with pytest.raises(BadRequestBizException):
        await DiagCaseLibraryService.update_case(
            case.id, UpdateDiagCaseRequest(expected_revision=3)
        )


async def test_verification_requires_the_page_revision(monkeypatch):
    case = _case(status=DiagCaseStatus.CONFIRMED, revision=2)
    _install_case(monkeypatch, {case.id: case})

    with pytest.raises(BadRequestBizException) as exc_info:
        await DiagCaseLibraryService.update_case(
            case.id,
            UpdateDiagCaseRequest(
                verification_json=VerificationModel(
                    method="复测", observed_result="恢复正常", closed_loop=True,
                    verified_by="bob",
                )
            ),
        )
    assert "expected_revision" in exc_info.value.detail


async def test_draft_update_passes_the_revision_and_keeps_it_optional(monkeypatch):
    case = _case(revision=3)
    store = {case.id: case}
    captured: dict = {}
    _install_case(monkeypatch, store)
    _install_update(monkeypatch, "update_draft", store, captured)

    refreshed = await DiagCaseLibraryService.update_case(
        case.id, UpdateDiagCaseRequest(expected_revision=3, title="新标题")
    )

    assert captured["expected_revision"] == 3
    assert captured["case"].title == "新标题"
    assert refreshed.case.title == "新标题"

    captured.clear()
    await DiagCaseLibraryService.update_case(
        case.id, UpdateDiagCaseRequest(title="再改一次")
    )
    assert captured["expected_revision"] is None


# ---------------------------------------------------------------------------
# 验证回填
# ---------------------------------------------------------------------------
async def test_closed_loop_requires_method_result_and_operator(monkeypatch):
    case = _case()
    _install_case(monkeypatch, {case.id: case})

    with pytest.raises(BadRequestBizException) as exc_info:
        await DiagCaseLibraryService.update_case(
            case.id,
            UpdateDiagCaseRequest(
                expected_revision=0,
                verification_json=VerificationModel(
                    closed_loop=True, method="复测 P99"
                ),
            ),
        )
    detail = exc_info.value.detail
    assert "observed_result" in detail
    assert "verified_by" in detail


async def test_closed_loop_fill_stamps_the_time_and_appends_history(monkeypatch):
    case = _case(status=DiagCaseStatus.CONFIRMED, revision=4)
    store = {case.id: case}
    captured: dict = {}
    _install_case(monkeypatch, store)
    _install_update(monkeypatch, "update_verification", store, captured)

    refreshed = await DiagCaseLibraryService.update_case(
        case.id,
        UpdateDiagCaseRequest(
            expected_revision=4,
            verification_json=VerificationModel(
                method="复测 P99",
                observed_result="P99 回到 120ms",
                closed_loop=True,
                verified_by="bob",
            ),
        ),
    )

    verification = captured["case"].verification_json
    assert verification.verified_at
    assert captured["expected_revision"] == 4
    history = captured["case"].verification_history_json
    assert history == [
        {
            "revision_from": 4,
            "revision_to": 5,
            "verified_by": "bob",
            "verified_at": verification.verified_at,
            "method": "复测 P99",
            "observed_result": "P99 回到 120ms",
            "closed_loop": True,
        }
    ]
    assert refreshed.case.revision == 5


async def test_non_closed_result_is_recorded_without_requiring_operator(monkeypatch):
    case = _case(status=DiagCaseStatus.CONFIRMED)
    store = {case.id: case}
    captured: dict = {}
    _install_case(monkeypatch, store)
    _install_update(monkeypatch, "update_verification", store, captured)

    await DiagCaseLibraryService.update_case(
        case.id,
        UpdateDiagCaseRequest(
            expected_revision=0,
            verification_json=VerificationModel(
                method="抽样观察", observed_result="仍有少量超时", closed_loop=False
            ),
        ),
    )

    verification = captured["case"].verification_json
    assert verification.verified_by is None
    assert verification.verified_at is None
    assert captured["case"].verification_history_json[-1]["closed_loop"] is False


async def test_confirmed_case_freezes_content_columns(monkeypatch):
    case = _case(status=DiagCaseStatus.CONFIRMED)
    _install_case(monkeypatch, {case.id: case})

    with pytest.raises(ConflictBizException) as exc_info:
        await DiagCaseLibraryService.update_case(
            case.id, UpdateDiagCaseRequest(title="新标题")
        )
    assert "内容物已冻结" in exc_info.value.message


async def test_archived_case_rejects_any_update(monkeypatch):
    case = _case(status=DiagCaseStatus.ARCHIVED)
    _install_case(monkeypatch, {case.id: case})

    with pytest.raises(ConflictBizException):
        await DiagCaseLibraryService.update_case(
            case.id, UpdateDiagCaseRequest(title="新标题")
        )


async def test_missing_case_is_not_found(monkeypatch):
    _install_case(monkeypatch, {})

    with pytest.raises(NotFoundBizException):
        await DiagCaseLibraryService.update_case(
            "case-absent", UpdateDiagCaseRequest(title="新标题")
        )


# ---------------------------------------------------------------------------
# 案例确认：来源报告校验 + 确认闸门
# ---------------------------------------------------------------------------
async def test_confirm_requires_a_confirmed_source_report(monkeypatch):
    case = _bound_case(_snapshot())
    _install_case(monkeypatch, {case.id: case})

    async def unconfirmed(report_id, expected_sidecar_hash=None):
        raise ConflictBizException(message="报告尚未确认", detail="未人工确认")

    monkeypatch.setattr(
        ReportReviewService, "require_confirmed", staticmethod(unconfirmed)
    )

    with pytest.raises(ConflictBizException) as exc_info:
        await DiagCaseLibraryService.confirm_case(
            case.id, ConfirmDiagCaseRequest(confirmed_by="alice")
        )
    assert "未人工确认" in exc_info.value.detail


async def test_confirm_rejects_a_changed_source_fault(monkeypatch):
    snapshot = _snapshot()
    case = _bound_case(snapshot, source_fault_hash="c" * 64)
    _install_case(monkeypatch, {case.id: case})

    async def confirmed(report_id, expected_sidecar_hash=None):
        return snapshot

    monkeypatch.setattr(
        ReportReviewService, "require_confirmed", staticmethod(confirmed)
    )

    with pytest.raises(ConflictBizException) as exc_info:
        await DiagCaseLibraryService.confirm_case(
            case.id, ConfirmDiagCaseRequest(confirmed_by="alice")
        )
    assert "源报告版本已变更" in exc_info.value.message


async def test_confirm_rejects_a_changed_classification(monkeypatch):
    snapshot = _snapshot()
    case = _bound_case(snapshot, source_label_hash="b" * 64)
    _install_case(monkeypatch, {case.id: case})

    async def confirmed(report_id, expected_sidecar_hash=None):
        return snapshot

    monkeypatch.setattr(
        ReportReviewService, "require_confirmed", staticmethod(confirmed)
    )

    with pytest.raises(ConflictBizException) as exc_info:
        await DiagCaseLibraryService.confirm_case(
            case.id, ConfirmDiagCaseRequest(confirmed_by="alice")
        )
    assert "源报告分类已变更" in exc_info.value.message


async def test_confirm_requires_the_report_version_seen_at_draft_time(monkeypatch):
    snapshot = _snapshot()
    case = _bound_case(snapshot, source_sidecar_hash="b" * 64)
    _install_case(monkeypatch, {case.id: case})

    async def confirmed(report_id, expected_sidecar_hash=None):
        if expected_sidecar_hash != snapshot.sidecar_hash:
            raise ConflictBizException(
                message="报告版本已变化", detail="页面所见版本与当前侧车不一致"
            )
        return snapshot

    monkeypatch.setattr(
        ReportReviewService, "require_confirmed", staticmethod(confirmed)
    )

    with pytest.raises(ConflictBizException) as exc_info:
        await DiagCaseLibraryService.confirm_case(
            case.id, ConfirmDiagCaseRequest(confirmed_by="alice")
        )
    assert "报告版本已变化" in exc_info.value.message


async def test_confirm_rejects_a_legacy_draft_without_the_report_version(monkeypatch):
    snapshot = _snapshot()
    case = _bound_case(snapshot, source_sidecar_hash=None)
    _install_case(monkeypatch, {case.id: case})

    with pytest.raises(ConflictBizException) as exc_info:
        await DiagCaseLibraryService.confirm_case(
            case.id, ConfirmDiagCaseRequest(confirmed_by="alice")
        )
    assert "缺少建案时报告版本" in exc_info.value.message


async def test_confirm_gate_reports_missing_fields(monkeypatch):
    case = _case(evidence_json=[])
    _install_case(monkeypatch, {case.id: case})

    with pytest.raises(BadRequestBizException) as exc_info:
        await DiagCaseLibraryService.confirm_case(
            case.id, ConfirmDiagCaseRequest(confirmed_by="alice")
        )
    assert "evidence_json" in exc_info.value.detail


async def test_confirm_passes_the_gate_and_records_the_operator(monkeypatch):
    snapshot = _snapshot()
    case = _bound_case(snapshot)
    store = {case.id: case}
    _install_case(monkeypatch, store)

    async def confirmed(report_id, expected_sidecar_hash=None):
        return snapshot

    async def manager_confirm(case_id, confirmed_by, confidence=None):
        store[case_id].status = DiagCaseStatus.CONFIRMED
        store[case_id].confirmed_by = confirmed_by
        return True

    monkeypatch.setattr(
        ReportReviewService, "require_confirmed", staticmethod(confirmed)
    )
    monkeypatch.setattr(Manager, "confirm_case", staticmethod(manager_confirm))

    msg = await DiagCaseLibraryService.confirm_case(
        case.id, ConfirmDiagCaseRequest(confirmed_by="alice", confidence=0.9)
    )

    assert msg.case.status == DiagCaseStatus.CONFIRMED
    assert msg.case.confirmed_by == "alice"


# ---------------------------------------------------------------------------
# 受控审核入口：操作人只认认证网关注入的请求头
# ---------------------------------------------------------------------------
async def test_trusted_mode_confirms_with_the_gateway_operator(monkeypatch):
    case = _case()
    store = {case.id: case}
    _install_case(monkeypatch, store)
    captured: dict = {}

    async def manager_confirm(case_id, confirmed_by, confidence=None):
        captured["confirmed_by"] = confirmed_by
        store[case_id].status = DiagCaseStatus.CONFIRMED
        return True

    monkeypatch.setattr(Manager, "confirm_case", staticmethod(manager_confirm))
    monkeypatch.setenv("WITTY_REQUIRE_TRUSTED_OPERATOR", "1")

    await DiagCaseLibraryService.confirm_case(
        case.id, ConfirmDiagCaseRequest(confirmed_by="body-user"), "gateway-user"
    )

    assert captured["confirmed_by"] == "gateway-user"

    with pytest.raises(BadRequestBizException) as exc_info:
        await DiagCaseLibraryService.confirm_case(
            case.id, ConfirmDiagCaseRequest(confirmed_by="body-user")
        )
    assert "可信操作人" in exc_info.value.message


async def test_trusted_mode_rejects_a_body_only_verification_operator(monkeypatch):
    case = _case(status=DiagCaseStatus.CONFIRMED)
    other = _case(id="case-2", status=DiagCaseStatus.CONFIRMED)
    store = {case.id: case, other.id: other}
    captured: dict = {}
    _install_case(monkeypatch, store)
    _install_update(monkeypatch, "update_verification", store, captured)
    monkeypatch.setenv("WITTY_REQUIRE_TRUSTED_OPERATOR", "1")

    await DiagCaseLibraryService.update_case(
        case.id,
        UpdateDiagCaseRequest(
            expected_revision=0,
            verification_json=VerificationModel(
                method="复测 P99",
                observed_result="P99 回到 120ms",
                closed_loop=True,
                verified_by="body-user",
            ),
        ),
        "gateway-user",
    )

    assert captured["case"].verification_json.verified_by == "gateway-user"

    with pytest.raises(BadRequestBizException) as exc_info:
        await DiagCaseLibraryService.update_case(
            other.id,
            UpdateDiagCaseRequest(
                expected_revision=0,
                verification_json=VerificationModel(
                    method="复测 P99",
                    observed_result="P99 回到 120ms",
                    closed_loop=True,
                    verified_by="body-user",
                ),
            ),
        )
    assert "可信操作人" in exc_info.value.message


async def test_trusted_mode_requires_the_gateway_for_a_non_closed_record(monkeypatch):
    case = _case(status=DiagCaseStatus.CONFIRMED)
    store = {case.id: case}
    captured: dict = {}
    _install_case(monkeypatch, store)
    _install_update(monkeypatch, "update_verification", store, captured)
    monkeypatch.setenv("WITTY_REQUIRE_TRUSTED_OPERATOR", "1")

    with pytest.raises(BadRequestBizException) as exc_info:
        await DiagCaseLibraryService.update_case(
            case.id,
            UpdateDiagCaseRequest(
                expected_revision=0,
                verification_json=VerificationModel(
                    method="抽样观察", observed_result="仍有少量超时", closed_loop=False
                ),
            ),
        )
    assert "可信操作人" in exc_info.value.message

    await DiagCaseLibraryService.update_case(
        case.id,
        UpdateDiagCaseRequest(
            expected_revision=0,
            verification_json=VerificationModel(
                method="抽样观察", observed_result="仍有少量超时", closed_loop=False
            ),
        ),
        "gateway-user",
    )
    assert captured["case"].verification_json.verified_by == "gateway-user"


async def test_trusted_mode_requires_the_gateway_to_clear_verification(monkeypatch):
    case = _case(status=DiagCaseStatus.CONFIRMED)
    _install_case(monkeypatch, {case.id: case})
    monkeypatch.setenv("WITTY_REQUIRE_TRUSTED_OPERATOR", "1")

    with pytest.raises(BadRequestBizException) as exc_info:
        await DiagCaseLibraryService.update_case(
            case.id,
            UpdateDiagCaseRequest(expected_revision=0, verification_json=None),
        )
    assert "可信操作人" in exc_info.value.message


async def test_trusted_mode_clear_records_the_gateway_operator(monkeypatch):
    case = _case(
        status=DiagCaseStatus.CONFIRMED,
        verification_json=VerificationModel(
            method="旧验证", observed_result="旧结果", closed_loop=False
        ),
    )
    store = {case.id: case}
    captured: dict = {}
    _install_case(monkeypatch, store)
    _install_update(monkeypatch, "update_verification", store, captured)
    monkeypatch.setenv("WITTY_REQUIRE_TRUSTED_OPERATOR", "1")

    await DiagCaseLibraryService.update_case(
        case.id,
        UpdateDiagCaseRequest(expected_revision=0, verification_json=None),
        "gateway-user",
    )

    assert captured["case"].verification_json is None
    assert captured["case"].verification_history_json[-1]["verified_by"] == "gateway-user"


async def test_verification_time_normalizes_client_offset_to_wall_clock(monkeypatch):
    case = _case(status=DiagCaseStatus.CONFIRMED)
    store = {case.id: case}
    captured: dict = {}
    _install_case(monkeypatch, store)
    _install_update(monkeypatch, "update_verification", store, captured)

    await DiagCaseLibraryService.update_case(
        case.id,
        UpdateDiagCaseRequest(
            expected_revision=0,
            verification_json=VerificationModel(
                method="复测 P99",
                observed_result="P99 回到 120ms",
                closed_loop=True,
                verified_by="bob",
                verified_at="2026-10-26T12:02:29Z",
            ),
        ),
    )

    assert captured["case"].verification_json.verified_at == "2026-10-26 20:02:29"
