from types import SimpleNamespace

import pytest

from latency.services.diagnostic_report import document_validation_status
from latency.routers.case_library import list_cases
from latency.services.case_service import CaseServiceManager
from latency.services.report_phenomenon import extract_legacy_doc
from latency.services.phenomenon_search import _CardState


@pytest.mark.parametrize(
    ("readable", "eligible", "validated", "expected"),
    [
        (True, 2, set(), "pending"),
        (True, 2, {"F01"}, "partial"),
        (True, 2, {"F01", "F02"}, "validated"),
        (False, 2, {"F01", "F02"}, "unavailable"),
        (True, None, set(), "unavailable"),
        (True, 0, set(), "pending"),
    ],
)
def test_document_status_only_uses_current_unique_faults(readable, eligible, validated, expected):
    assert document_validation_status(
        readable=readable, eligible=eligible, validated_faults=validated,
    ) == expected


async def test_real_task_cases_are_effective_without_human_verification(monkeypatch):
    import json
    records = [{
        "id": "task-case", "log_file_id": "log-1", "task_ids": ["task-1"],
        "case_category": "原分类", "root_cause_type": "原类型",
    }, {"id": "historical-case", "description": "保留旧材料"}]
    monkeypatch.setattr(CaseServiceManager, "list_cases", lambda: records)
    response = await list_cases()
    result = json.loads(response.body)["result"]
    assert result[0]["effective"] is True
    assert result[0]["source_kind"] == "task"
    assert result[0]["case_category"] == "原分类"
    assert "verification_json" not in result[0]
    assert result[1]["source_kind"] == "historical"
    assert "effective" not in records[0]


def test_task_card_is_effective_without_inventing_human_validation():
    record = {
        "id": "task-case", "log_file_id": "log-1", "task_ids": ["task-1"],
        "description": "GET 请求在连接中断后快速失败",
    }
    doc = extract_legacy_doc(record)
    assert doc is not None
    assert doc.verification == "task_observed"
    assert doc.case_id is None
    assert "verification_json" not in record
    state = _CardState(
        SimpleNamespace(
            kind="legacy_case", report_id=None, verification=doc.verification,
        ),
        case=None, report_available=False,
    )
    assert state.verification == "task_observed"
    assert state.case_active is False
