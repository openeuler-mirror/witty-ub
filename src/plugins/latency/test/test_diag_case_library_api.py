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
from latency.database.engine import PGManager
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
    UpdateDiagCaseRequest,
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
        ({"status_codes": []}, "可匹配信号"),
    ],
)
def test_confirm_gate_rejects_each_missing_item(overrides, fragment):
    errors = DiagCaseLibraryService._confirm_gate_errors(_draft(**overrides), "alice")
    assert any(fragment in error for error in errors)


def test_confirm_gate_does_not_require_verification_closure():
    """闸门只判「报告可信」：处置未执行时 verification_json 为空也可确认。"""
    assert DiagCaseLibraryService._confirm_gate_errors(
        _draft(verification_json=None), "alice"
    ) == []
    assert DiagCaseLibraryService._confirm_gate_errors(
        _draft(verification_json={"method": "重新压测", "closed_loop": False}), "alice"
    ) == []


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
            DiagCaseLibraryService.update_case(
                "missing-case", UpdateDiagCaseRequest(title="x")
            )
        )
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
# §4.4 / §4.5 案例更新（draft 改内容物；confirmed 只放行 verification_json）
# ------------------------------------------------------------
def _install_update_store(monkeypatch, cases):
    """内存替身：记录合并后的写入结果与走的通道，并模拟 revision + 1。"""
    captured: dict[str, DiagCaseLibraryModel] = {}
    channels: dict[str, str] = {}
    store = {case.id: case for case in cases}

    def _apply(case_id, case, channel):
        captured[case_id] = case
        channels[case_id] = channel
        snapshot = case.model_dump()
        snapshot["revision"] = store[case_id].revision + 1
        store[case_id] = DiagCaseLibraryModel.model_validate(snapshot)
        return True

    async def get_case(case_id):
        return store.get(case_id)

    async def update_draft(case_id, case):
        return _apply(case_id, case, "draft")

    async def update_verification(case_id, case):
        return _apply(case_id, case, "verification")

    monkeypatch.setattr(Manager, "get_case", get_case)
    monkeypatch.setattr(Manager, "update_draft", update_draft)
    monkeypatch.setattr(Manager, "update_verification", update_verification)
    return store, captured, channels


def test_update_case_is_partial_and_bumps_revision(monkeypatch):
    draft = _draft(verification_json=None)
    _, captured, channels = _install_update_store(monkeypatch, [draft])

    msg = run(
        DiagCaseLibraryService.update_case(
            draft.id,
            UpdateDiagCaseRequest(
                verification_json={
                    "method": "复测 SET 时延",
                    "observed_result": "SET 恢复正常",
                    "closed_loop": True,
                    "verified_at": "2026-09-21 10:00:00",
                }
            ),
        )
    )

    written = captured[draft.id]
    # 未传字段原样保留
    assert written.title == "SET 通断失败"
    assert written.status_codes == ["1004"]
    assert written.evidence_json[0].kind == "log"
    # 元信息不受 PATCH 影响
    assert written.case_no == "UB-CASE-000001"
    assert written.status == DiagCaseStatus.DRAFT
    # 传了的字段才更新，且 revision + 1
    assert written.verification_json.observed_result == "SET 恢复正常"
    assert written.verification_json.closed_loop is True
    assert msg.case.revision == 1
    assert channels[draft.id] == "draft"


def test_update_case_explicit_empty_list_clears_the_field(monkeypatch):
    draft = _draft()
    _, captured, _ = _install_update_store(monkeypatch, [draft])

    run(
        DiagCaseLibraryService.update_case(
            draft.id, UpdateDiagCaseRequest(status_codes=[])
        )
    )

    assert captured[draft.id].status_codes == []
    assert captured[draft.id].log_keywords == []  # 未传字段不动


def test_update_case_rejects_empty_body(monkeypatch):
    draft = _draft()
    _, captured, _ = _install_update_store(monkeypatch, [draft])

    with pytest.raises(BadRequestBizException):
        run(DiagCaseLibraryService.update_case(draft.id, UpdateDiagCaseRequest()))
    assert captured == {}


def test_update_case_rejects_archived_status(monkeypatch):
    """archived 内容与验证记录都冻结，连 verification_json 也不接受。"""
    archived = _confirmed("archived-case", status=DiagCaseStatus.ARCHIVED)
    _, captured, _ = _install_update_store(monkeypatch, [archived])

    for req in (
        UpdateDiagCaseRequest(title="新标题"),
        UpdateDiagCaseRequest(verification_json={"closed_loop": True}),
    ):
        with pytest.raises(ConflictBizException):
            run(DiagCaseLibraryService.update_case(archived.id, req))
    assert captured == {}


def test_update_case_on_confirmed_freezes_content_but_accepts_verification(monkeypatch):
    """confirmed：内容物冻结，只放行事后证据 verification_json（走另一种通道）。"""
    confirmed = _confirmed("confirmed-case", verification_json=None)
    _, captured, channels = _install_update_store(monkeypatch, [confirmed])

    with pytest.raises(ConflictBizException) as raised:
        run(
            DiagCaseLibraryService.update_case(
                confirmed.id, UpdateDiagCaseRequest(title="新标题")
            )
        )
    assert "title" in str(raised.value.detail)
    assert captured == {}

    msg = run(
        DiagCaseLibraryService.update_case(
            confirmed.id,
            UpdateDiagCaseRequest(
                verification_json={
                    "method": "复测 SET 时延",
                    "observed_result": "SET 恢复正常",
                    "closed_loop": True,
                    "verified_at": "2026-09-21 10:00:00",
                }
            ),
        )
    )

    assert channels[confirmed.id] == "verification"
    assert captured[confirmed.id].verification_json.closed_loop is True
    # 内容物仍是确认时的值
    assert captured[confirmed.id].title == "SET 通断失败"
    assert msg.case.revision == 1


def test_update_case_requires_source_url_for_external_source_on_merged_result(monkeypatch):
    """`source_url` 按「合并后」判定，只改 source 不会被既有 source_url 误伤。"""
    draft = _draft()
    _, captured, _ = _install_update_store(monkeypatch, [draft])

    with pytest.raises(BadRequestBizException):
        run(
            DiagCaseLibraryService.update_case(
                draft.id, UpdateDiagCaseRequest(source="community")
            )
        )
    assert captured == {}

    run(
        DiagCaseLibraryService.update_case(
            draft.id,
            UpdateDiagCaseRequest(
                source="community", source_url="https://example.com/case/9"
            ),
        )
    )
    assert captured[draft.id].source == DiagCaseSource.COMMUNITY

    # 已带 source_url 的 community 草稿，只改标题不应被拦。
    _, captured, _ = _install_update_store(monkeypatch, [captured[draft.id]])
    run(
        DiagCaseLibraryService.update_case(
            draft.id, UpdateDiagCaseRequest(title="标题订正")
        )
    )
    assert captured[draft.id].title == "标题订正"


def test_update_request_has_same_field_set_as_create_without_metadata():
    update_fields = set(UpdateDiagCaseRequest.model_fields)
    assert update_fields == set(CreateDiagCaseDraftRequest.model_fields) - {"created_by"}
    assert not update_fields & {
        "id",
        "case_no",
        "status",
        "revision",
        "confirmed_by",
        "confirmed_at",
        "archived_by",
        "archived_at",
        "archive_reason",
        "hit_count",
        "search_text",
    }


def test_updatable_columns_cover_content_but_no_metadata():
    """UPDATABLE_COLUMNS 与模型字段互补：漏列会静默丢更新。"""
    metadata = {
        "id",
        "case_no",
        "status",
        "revision",
        "created_by",
        "confirmed_by",
        "confirmed_at",
        "archived_by",
        "archived_at",
        "archive_reason",
        "search_text",
        "embedding_model",
        "embedded_at",
        "hit_count",
        "existed_status",
        "created_at",
        "updated_at",
    }
    assert set(Manager.UPDATABLE_COLUMNS) == set(
        DiagCaseLibraryModel.model_fields
    ) - metadata
    # 事后证据白名单必须落在内容物列内，否则 confirmed 通道会写不动。
    assert set(Manager.VERIFICATION_COLUMNS) <= set(Manager.UPDATABLE_COLUMNS)


class _FakeSession:
    """记录 execute 语句的替身，用于断言 UPDATE / 信号重建的 SQL 形状。"""

    def __init__(self):
        self.statements = []

    async def execute(self, statement):
        self.statements.append(statement)
        return type("_Result", (), {"rowcount": 1})()


class _FakeSessionContext:
    def __init__(self, session):
        self.session = session

    async def __aenter__(self):
        return self.session

    async def __aexit__(self, *args):
        return False


def test_replace_signals_deletes_then_reinserts_derived_rows():
    case = _draft(failure_mode_ids=["FM-URMA"], operation=DiagCaseOperation.SET)
    session = _FakeSession()

    run(Manager._replace_signals(session, case.id, case))

    assert len(session.statements) == 2
    assert "DELETE FROM diag_case_library_signal" in str(session.statements[0])
    assert "INSERT INTO diag_case_library_signal" in str(session.statements[1])


def test_update_draft_writes_content_columns_and_recomputes_signals(monkeypatch):
    case = _draft(latency_components=["set_client"])
    session = _FakeSession()
    monkeypatch.setattr(PGManager, "session", lambda: _FakeSessionContext(session))

    assert run(Manager.update_draft(case.id, case)) is True

    sql = str(session.statements[0])
    assert sql.startswith("UPDATE diag_case_library")
    values = dict(session.statements[0].compile().params)
    assert "search_text" in values
    assert {"source", "verification_json", "latency_components"} <= set(values)
    # 元信息列不得出现在 SET 子句中
    assert not {"case_no", "revision", "created_at", "hit_count"} & set(values)
    # 信号行按新特征重建（DELETE + INSERT）
    assert "DELETE FROM diag_case_library_signal" in str(session.statements[1])
    assert "diag_case_library_signal" in str(session.statements[2])


def test_update_verification_only_writes_the_closure_and_keeps_signals(monkeypatch):
    """confirmed 通道：只写 verification_json，不重算 search_text 与信号行。"""
    case = _confirmed("confirmed-case")
    session = _FakeSession()
    monkeypatch.setattr(PGManager, "session", lambda: _FakeSessionContext(session))

    assert run(Manager.update_verification(case.id, case)) is True

    values = dict(session.statements[0].compile().params)
    assert {"updated_at", "verification_json"} <= set(values)
    assert not {"title", "search_text", "status_codes", "latency_components"} & set(values)
    # 状态白名单含 confirmed（draft 与 confirmed 都可回填）
    assert set(values["status_1"]) == {"draft", "confirmed"}
    assert len(session.statements) == 1  # 不重建信号


def test_update_draft_returns_false_when_row_is_no_longer_draft(monkeypatch):
    """并发窗口：确认后 revision 不再被 PATCH 改写。"""
    case = _draft()
    session = _FakeSession()

    async def execute(statement):
        session.statements.append(statement)
        return type("_Result", (), {"rowcount": 0})()

    session.execute = execute
    monkeypatch.setattr(PGManager, "session", lambda: _FakeSessionContext(session))

    assert run(Manager.update_draft(case.id, case)) is False
    assert len(session.statements) == 1  # 未命中即不再重建信号


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