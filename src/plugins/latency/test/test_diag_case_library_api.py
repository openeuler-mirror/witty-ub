"""Unit tests for the supernode diagnosis case library (/diag_case_library).

Pure unit tests: no PostgreSQL is required.  Matching semantics live in the
manager's ``@staticmethod`` helpers so they can be exercised in memory.
"""

import asyncio
from unittest.mock import AsyncMock

import pytest
from pydantic import ValidationError

from latency.ENUM.case_library import (
    DiagCaseOperation,
    DiagCaseSource,
    DiagCaseStatus,
)
from latency.database.managers.diag_case_library import (
    DiagCaseLibraryPGManager as Manager,
)
from latency.exceptions import (
    BadRequestBizException,
    ConflictBizException,
    NotFoundBizException,
)
from latency.schemas.diag_case_library import (
    ArchiveDiagCaseRequest,
    ConfirmDiagCaseRequest,
    CreateDiagCaseDraftRequest,
    DiagCaseLibraryModel,
    SearchDiagCaseLibraryRequest,
)
from latency.services.diag_case_library import DiagCaseLibraryService


def run(coroutine):
    return asyncio.run(coroutine)


def _draft(**overrides) -> DiagCaseLibraryModel:
    payload = dict(
        id="case-draft",
        case_no="UB-CASE-000001",
        status=DiagCaseStatus.DRAFT,
        source=DiagCaseSource.INTERNAL,
        title="SET 通断失败",
        log_type="KVCache",
        fault_type="latency",
        symptom_summary="SET 请求大面积超时",
        root_cause_summary="URMA 链路建链慢",
        evidence_json=[{"kind": "log", "ref": "set.log:1234"}],
        remediation_json=[{"step": 1, "action": "重启 umq"}],
        verification_json={"method": "rerun", "observed_result": "SET 恢复正常"},
        status_codes=["1004"],
        created_at="2026-09-20 10:00:00.000",
        updated_at="2026-09-20 10:00:00.000",
    )
    payload.update(overrides)
    return DiagCaseLibraryModel(**payload)


def _confirmed(case_id: str, **overrides) -> DiagCaseLibraryModel:
    overrides.setdefault("status", DiagCaseStatus.CONFIRMED)
    return _draft(id=case_id, **overrides)


def _rank(cases, req):
    signals = {case.id: Manager._signals_for_case(case) for case in cases}
    return Manager._rank_search(cases, signals, req)


# ------------------------------------------------------------
# 信号 / 正文 / 打分
# ------------------------------------------------------------
def test_case_signals_follow_weights_and_are_normalized():
    case = _draft(
        failure_mode_ids=["FM-URMA"],
        src_ips=["10.0.0.1"],
        dst_ips=["10.0.0.2"],
        hosts=["host-a"],
        pods=["pod-a"],
        cluster_name="cluster-a",
        latency_components=["set_client"],
        log_keywords=["Connect Timeout"],
        operation=DiagCaseOperation.SET,
    )

    pairs = {
        (signal.signal_type, signal.signal_value): signal.weight
        for signal in Manager._signals_for_case(case)
    }

    assert pairs[("status_code", "1004")] == 3.0
    assert pairs[("failure_mode_id", "fm-urma")] == 3.0
    assert pairs[("src_ip", "10.0.0.1")] == 1.5
    assert pairs[("dst_ip", "10.0.0.2")] == 1.5
    assert pairs[("host", "host-a")] == 1.5
    assert pairs[("pod", "pod-a")] == 1.5
    assert pairs[("cluster", "cluster-a")] == 1.5
    assert pairs[("latency_component", "set_client")] == 1.5
    assert pairs[("log_keyword", "connect timeout")] == 1.0
    assert pairs[("operation", "set")] == 1.5


def test_search_text_is_generated_and_excludes_identity_noise():
    case = _draft(
        root_cause_detail="URMA 建链排队导致首包超时",
        fault_shape="持续劣化",
        latency_components=["set_client"],
        log_keywords=["Connect Timeout"],
        version_json={"kernel": "5.10", "urma": "2.4"},
        operation=DiagCaseOperation.SET,
        src_ips=["10.0.0.1"],
        dst_ips=["10.0.0.2"],
        hosts=["host-a"],
        cluster_name="cluster-a",
    )

    text = Manager._build_search_text(case)

    assert "SET 通断失败" in text
    assert "SET 请求大面积超时" in text
    assert "URMA 建链排队导致首包超时" in text
    assert "持续劣化" in text
    assert "set_client" in text
    assert "Connect Timeout" in text
    assert "5.10" in text and "2.4" in text
    # 纯标识噪声不得进入 embedding 正文，避免跨集群召回被污染。
    assert "10.0.0.1" not in text
    assert "10.0.0.2" not in text
    assert "host-a" not in text
    assert "cluster-a" not in text


def test_score_norm_is_bounded_and_monotonic_with_hits():
    query = Manager._signals_for_search(
        SearchDiagCaseLibraryRequest(
            status_codes=["1004"], log_keywords=["connect timeout"]
        )
    )
    both = _draft(status_codes=["1004"], log_keywords=["connect timeout"])
    keyword_only = _draft(status_codes=[], log_keywords=["connect timeout"])
    nothing = _draft(status_codes=[], log_keywords=[])

    both_match, both_norm, both_matched = Manager._score(
        Manager._signals_for_case(both), query
    )
    _, keyword_norm, keyword_matched = Manager._score(
        Manager._signals_for_case(keyword_only), query
    )
    none_match, none_norm, none_matched = Manager._score(
        Manager._signals_for_case(nothing), query
    )

    assert both_match == 4.0
    assert 0.0 <= none_norm <= keyword_norm <= both_norm <= 1.0
    assert keyword_norm < both_norm
    assert len(keyword_matched) == 1
    assert len(both_matched) == 2
    assert none_match == 0.0
    assert none_matched == []


# ------------------------------------------------------------
# §4.2 确认闸门
# ------------------------------------------------------------
def test_confirm_gate_accepts_complete_draft():
    assert DiagCaseLibraryService._confirm_gate_errors(_draft(), "alice") == []


@pytest.mark.parametrize(
    "overrides, fragment",
    [
        ({"evidence_json": []}, "evidence_json"),
        ({"remediation_json": []}, "remediation_json"),
        ({"verification_json": None}, "observed_result"),
        (
            {"verification_json": {"method": "m", "observed_result": "   "}},
            "observed_result",
        ),
        ({"status_codes": []}, "可匹配信号"),
    ],
)
def test_confirm_gate_rejects_each_missing_item(overrides, fragment):
    errors = DiagCaseLibraryService._confirm_gate_errors(_draft(**overrides), "alice")
    assert any(fragment in error for error in errors)


def test_confirm_gate_requires_confirmed_by():
    errors = DiagCaseLibraryService._confirm_gate_errors(_draft(), "   ")
    assert any("confirmed_by" in error for error in errors)


def test_confirm_gate_rejects_non_draft_status():
    errors = DiagCaseLibraryService._confirm_gate_errors(
        _draft(status=DiagCaseStatus.CONFIRMED), "alice"
    )
    assert any("draft" in error for error in errors)


def test_confirm_gate_does_not_count_operation_as_matchable_signal():
    errors = DiagCaseLibraryService._confirm_gate_errors(
        _draft(status_codes=[], operation=DiagCaseOperation.GET), "alice"
    )
    assert any("可匹配信号" in error for error in errors)


# ------------------------------------------------------------
# 状态机（service 编排，manager 用内存替身）
# ------------------------------------------------------------
def _install_state_store(monkeypatch, cases):
    store = {case.id: case for case in cases}

    async def get_case(case_id):
        return store.get(case_id)

    async def confirm_case(case_id, confirmed_by, confidence=None):
        case = store[case_id]
        case.status = DiagCaseStatus.CONFIRMED
        case.confirmed_by = confirmed_by
        if confidence is not None:
            case.confidence = confidence
        case.revision += 1
        return True

    async def archive_case(case_id, archived_by=None, archive_reason=None):
        case = store[case_id]
        case.status = DiagCaseStatus.ARCHIVED
        case.archived_by = archived_by
        case.archive_reason = archive_reason
        return True

    monkeypatch.setattr(Manager, "get_case", get_case)
    monkeypatch.setattr(Manager, "confirm_case", confirm_case)
    monkeypatch.setattr(Manager, "archive_case", archive_case)
    return store


def test_status_machine_full_path_and_illegal_transitions(monkeypatch):
    case = _draft()
    _install_state_store(monkeypatch, [case])

    confirmed = run(
        DiagCaseLibraryService.confirm_case(
            case.id, ConfirmDiagCaseRequest(confirmed_by="alice", confidence=0.9)
        )
    )
    assert confirmed.case.status == DiagCaseStatus.CONFIRMED
    assert confirmed.case.confirmed_by == "alice"
    assert confirmed.case.confidence == 0.9
    assert confirmed.case.revision == 1

    with pytest.raises(ConflictBizException):
        run(
            DiagCaseLibraryService.confirm_case(
                case.id, ConfirmDiagCaseRequest(confirmed_by="bob")
            )
        )

    archived = run(
        DiagCaseLibraryService.archive_case(
            case.id, ArchiveDiagCaseRequest(archived_by="bob", archive_reason="已过时")
        )
    )
    assert archived.case.status == DiagCaseStatus.ARCHIVED
    assert archived.case.archive_reason == "已过时"

    with pytest.raises(ConflictBizException):
        run(
            DiagCaseLibraryService.confirm_case(
                case.id, ConfirmDiagCaseRequest(confirmed_by="bob")
            )
        )

    # 已归档案例的归档是幂等的。
    idempotent = run(
        DiagCaseLibraryService.archive_case(case.id, ArchiveDiagCaseRequest())
    )
    assert idempotent.case.status == DiagCaseStatus.ARCHIVED


def test_confirm_rejects_incomplete_draft_with_bad_request(monkeypatch):
    case = _draft(evidence_json=[])
    _install_state_store(monkeypatch, [case])

    with pytest.raises(BadRequestBizException):
        run(
            DiagCaseLibraryService.confirm_case(
                case.id, ConfirmDiagCaseRequest(confirmed_by="alice")
            )
        )


def test_missing_case_id_has_not_found_semantics(monkeypatch):
    monkeypatch.setattr(Manager, "get_case", AsyncMock(return_value=None))

    with pytest.raises(NotFoundBizException):
        run(DiagCaseLibraryService.get_case("missing-case"))
    with pytest.raises(NotFoundBizException):
        run(
            DiagCaseLibraryService.confirm_case(
                "missing-case", ConfirmDiagCaseRequest(confirmed_by="alice")
            )
        )
    with pytest.raises(NotFoundBizException):
        run(
            DiagCaseLibraryService.archive_case(
                "missing-case", ArchiveDiagCaseRequest()
            )
        )
    with pytest.raises(NotFoundBizException):
        run(DiagCaseLibraryService.mark_hit("missing-case"))


# ------------------------------------------------------------
# §4.3 检索语义
# ------------------------------------------------------------
def test_search_defaults_to_confirmed_only():
    draft = _confirmed("draft-case", status=DiagCaseStatus.DRAFT)
    confirmed = _confirmed("confirmed-case")
    archived = _confirmed("archived-case", status=DiagCaseStatus.ARCHIVED)

    total, matches = _rank(
        [draft, confirmed, archived], SearchDiagCaseLibraryRequest(status_codes=["1004"])
    )
    assert total == 1
    assert [match.case.id for match in matches] == ["confirmed-case"]

    total_all, matches_all = _rank(
        [draft, confirmed, archived],
        SearchDiagCaseLibraryRequest(
            status_codes=["1004"],
            include_status=["draft", "confirmed", "archived"],
        ),
    )
    assert total_all == 3
    assert {match.case.id for match in matches_all} == {
        "draft-case",
        "confirmed-case",
        "archived-case",
    }


def test_search_operation_filter_excludes_other_operation():
    set_case = _confirmed("set-case", operation=DiagCaseOperation.SET)
    get_case = _confirmed("get-case", operation=DiagCaseOperation.GET)

    total, matches = _rank(
        [set_case, get_case],
        SearchDiagCaseLibraryRequest(operation="GET", status_codes=["1004"]),
    )

    assert total == 1
    assert matches[0].case.id == "get-case"


def test_search_without_kb_id_recalls_other_knowledge_base_cases():
    local = _confirmed("local-case", kb_id="kb-1")
    other = _confirmed("other-case", kb_id="kb-2")
    global_case = _confirmed("global-case", kb_id=None)

    scoped_total, scoped = _rank(
        [local, other, global_case],
        SearchDiagCaseLibraryRequest(kb_id="kb-1", status_codes=["1004"]),
    )
    assert scoped_total == 2
    assert {match.case.id for match in scoped} == {"local-case", "global-case"}

    total, matches = _rank(
        [local, other, global_case], SearchDiagCaseLibraryRequest(status_codes=["1004"])
    )
    assert total == 3
    assert {match.case.id for match in matches} == {
        "local-case",
        "other-case",
        "global-case",
    }


def test_search_min_confidence_filters_low_confidence_cases():
    low = _confirmed("low-case", confidence=0.2)
    high = _confirmed("high-case", confidence=0.9)

    total, matches = _rank(
        [low, high],
        SearchDiagCaseLibraryRequest(status_codes=["1004"], min_confidence=0.5),
    )

    assert total == 1
    assert matches[0].case.id == "high-case"


def test_search_zero_signal_query_returns_all_with_zero_score():
    confirmed = _confirmed("confirmed-case")

    total, matches = _rank([confirmed], SearchDiagCaseLibraryRequest())

    assert total == 1
    assert matches[0].match_score == 0.0
    assert matches[0].score_norm == 0.0


def test_search_pagination_beyond_last_page_keeps_real_total():
    cases = [_confirmed(f"case-{index}") for index in range(3)]

    total, matches = _rank(
        cases,
        SearchDiagCaseLibraryRequest(status_codes=["1004"], page_cnt=2, page_num=5),
    )

    assert total == 3
    assert matches == []


# ------------------------------------------------------------
# 写入
# ------------------------------------------------------------
def test_case_no_is_unique_and_increasing():
    numbers = [Manager._format_case_no(value) for value in (1, 2, 123)]
    assert numbers == ["UB-CASE-000001", "UB-CASE-000002", "UB-CASE-000123"]
    assert len(set(numbers)) == len(numbers)


def test_create_draft_forces_draft_status_and_returns_generated_case_no(monkeypatch):
    captured = {}

    async def add_draft(case):
        captured["case"] = case
        captured["case_no_at_entry"] = case.case_no
        case.case_no = "UB-CASE-000042"
        return case.id

    monkeypatch.setattr(Manager, "add_draft", add_draft)

    msg = run(
        DiagCaseLibraryService.create_draft(
            CreateDiagCaseDraftRequest(
                log_type="KVCache",
                source="internal",
                title="SET 通断失败",
                symptom_summary="SET 请求大面积超时",
                root_cause_summary="URMA 链路建链慢",
                status_codes=["1004"],
            )
        )
    )

    assert captured["case"].status == DiagCaseStatus.DRAFT
    assert captured["case_no_at_entry"] is None  # 编号只能由服务端生成
    assert captured["case"].search_text is None
    assert msg.case_no == "UB-CASE-000042"
    assert msg.case_id == captured["case"].id


@pytest.mark.parametrize("source", ["online", "community"])
def test_create_request_requires_source_url_for_external_sources(source):
    payload = dict(
        log_type="KVCache",
        source=source,
        title="t",
        symptom_summary="s",
        root_cause_summary="r",
    )
    with pytest.raises(ValidationError):
        CreateDiagCaseDraftRequest(**payload)

    accepted = CreateDiagCaseDraftRequest(
        source_url="https://example.com/case/1", **payload
    )
    assert accepted.source.value == source


def test_create_request_rejects_unknown_log_type_and_bad_confidence():
    base = dict(
        source="internal",
        title="t",
        symptom_summary="s",
        root_cause_summary="r",
    )
    with pytest.raises(ValidationError):
        CreateDiagCaseDraftRequest(log_type="brpc", **base)
    with pytest.raises(ValidationError):
        CreateDiagCaseDraftRequest(log_type="KVCache", confidence=1.5, **base)


def test_search_request_defaults_and_enum_coercion():
    default = SearchDiagCaseLibraryRequest()
    assert default.include_status == [DiagCaseStatus.CONFIRMED]
    assert default.page_cnt == 10 and default.page_num == 1

    explicit = SearchDiagCaseLibraryRequest(
        operation="GET", log_type="UBSocket", include_status=["draft", "confirmed"]
    )
    assert explicit.operation == DiagCaseOperation.GET
    assert explicit.include_status == [
        DiagCaseStatus.DRAFT,
        DiagCaseStatus.CONFIRMED,
    ]


def test_mark_hit_increments_and_returns_refreshed_case(monkeypatch):
    case = _confirmed("confirmed-case")
    store = {case.id: case}

    async def get_case(case_id):
        return store.get(case_id)

    async def mark_hit(case_id):
        store[case_id].hit_count += 1
        return True

    monkeypatch.setattr(Manager, "get_case", get_case)
    monkeypatch.setattr(Manager, "mark_hit", mark_hit)

    msg = run(DiagCaseLibraryService.mark_hit(case.id))

    assert msg.case.hit_count == 1