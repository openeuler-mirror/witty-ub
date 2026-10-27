# Copyright (c) Huawei Technologies Co., Ltd. 2023-2025. All rights reserved.
"""Unit tests for the pure phenomenon extractor."""
from __future__ import annotations

import copy

import pytest
from pydantic import ValidationError

from latency.ENUM.phenomenon import VerificationLevel
from latency.schemas.diag_case_library import (
    CreateDiagCaseDraftRequest,
    DiagCaseLibraryModel,
    VerificationModel,
)
from latency.services.report_phenomenon import (
    TEXT_HARD_LIMIT,
    IdentityScrubber,
    compute_sidecar_hash,
    compute_source_fault_hash,
    extract_case_doc,
    extract_legacy_doc,
    extract_report,
    sha256_hex,
)

REPORT_ID = "report_kb_20261021_101500"


def _fault(fault_id: str = "F01", **overrides) -> dict:
    fault = {
        "id": fault_id,
        "title": "GET 负向查询阻塞于对象订阅超时",
        "status": "confirmed",
        "category": "latency",
        "conclusion": {
            "one_line_conclusion": "GET 在 10.1.2.3 主机 node-1 上等待约 1.8 秒",
            "key_findings": ["耗时集中在 Worker 内部", "P99 行政约 1.8s"],
            "fault_domain": "KVCache GET",
            "fault_component": "对象订阅",
        },
        "root_cause": {"confirmed_root_cause": "对象不存在时阻塞在订阅等待"},
        "evidence_traces": [
            {"status_code": "3", "failure_mode_id": "kvcache_access_003"},
            {"status_code": "0"},
            {"status_code": None},
            {
                "status_code": "3",
                "failure_mode_id": "11111111-2222-3333-4444-555555555555",
            },
        ],
        "knowledge_matches": [
            {"id": "kvcache_access_003"},
            {"id": "11111111-2222-3333-4444-555555555555"},
        ],
        "solution": {"short_term": ["重启 Worker"]},
    }
    fault.update(overrides)
    return fault


def _sidecar(faults: list[dict], **overrides) -> dict:
    payload = {
        "report": {
            "report_id": "diag-internal-id",
            "title": "KVCache 时延诊断报告",
            "generated_at": "2026-10-21 10:15:00",
        },
        "basic_info": {
            "kb_id": "kb-1",
            "kb_name": "YXH LOGS",
            "operation": "GET",
            "log_file": "/var/log/a.log",
            "time_range_start": "2026-10-21 09:00:00",
            "time_range_end": "2026-10-21 10:00:00",
        },
        "faults": faults,
        "statistics": {
            "stage_breakdowns": [{"operation": "GET"}],
            "top_hosts": [{"host": "node-1", "count": 1018}],
        },
    }
    payload.update(overrides)
    return payload


def test_two_faults_two_cards_and_excluded_skipped():
    payload = _sidecar(
        [
            _fault("F01"),
            _fault("F02", title="URMA 传输失败", category="error"),
            _fault("F03", status="excluded"),
        ]
    )
    extraction = extract_report(REPORT_ID, payload)

    assert [doc.source_fault_id for doc in extraction.faults] == ["F01", "F02"]
    assert extraction.faults[0].doc_id == f"report:{REPORT_ID}:F01"
    assert extraction.faults[0].verification == VerificationLevel.REPORT_ONLY.value
    assert extraction.faults[1].fault_type == "connectivity"
    assert extraction.operation == "GET"
    assert extraction.fault_count == 3
    assert extraction.fault_errors == []


def test_suspected_fault_and_missing_duplicate_ids_become_synthetic():
    payload = _sidecar(
        [
            _fault("F01", status="suspected"),
            _fault("F01", status="confirmed"),
            _fault(None, status="confirmed"),
        ]
    )
    extraction = extract_report(REPORT_ID, payload)

    assert extraction.faults[0].verification == VerificationLevel.SUSPECTED.value
    assert [doc.source_fault_id for doc in extraction.faults] == [
        f"auto:{extraction.sidecar_hash[:16]}:01",
        f"auto:{extraction.sidecar_hash[:16]}:02",
        f"auto:{extraction.sidecar_hash[:16]}:03",
    ]


def test_status_codes_and_failure_mode_ids_are_filtered():
    extraction = extract_report(REPORT_ID, _sidecar([_fault("F01")]))
    doc = extraction.faults[0]

    assert doc.status_codes == ["3"]
    assert doc.failure_mode_ids == ["kvcache_access_003"]


def test_status_codes_prefer_per_fault_error_distribution():
    fault = _fault(
        "F01",
        error={
            "breakdowns": [
                {
                    "code_distribution": {
                        "items": [
                            {"code": "-1002", "count": 7},
                            {"code": "-1009", "count": 0},
                        ]
                    }
                }
            ]
        },
    )
    extraction = extract_report(REPORT_ID, _sidecar([fault]))

    assert extraction.faults[0].status_codes == ["-1002", "3"]


def test_single_fault_legacy_report_uses_top_error_codes_as_fallback():
    fault = _fault("F01", evidence_traces=[])
    payload = _sidecar(
        [fault],
        statistics={"top_error_codes": [{"code": "-1005", "pct": "80"}]},
    )

    extraction = extract_report(REPORT_ID, payload)

    assert extraction.faults[0].status_codes == ["-1005"]


def test_identity_values_are_scrubbed_from_text():
    extraction = extract_report(REPORT_ID, _sidecar([_fault("F01")]))
    text = extraction.faults[0].text

    assert "10.1.2.3" not in text
    assert "node-1" not in text
    assert "/var/log" not in text
    assert "[IP]" in text
    assert "[主机]" in text
    assert "kvcache_access_003" not in text


def test_residual_identity_rejects_only_that_fault():
    unsafe = _fault(
        "F03",
        status="suspected",
        conclusion={"one_line_conclusion": "trace abcdef0123456789 host/worker"},
    )
    extraction = extract_report(REPORT_ID, _sidecar([_fault("F01"), unsafe]))

    assert [doc.source_fault_id for doc in extraction.faults] == ["F01"]
    assert extraction.fault_errors == [
        {"fault_id": "F03", "error": "identity_residual"}
    ]


def test_html_content_is_rejected():
    unsafe = _fault("F01", conclusion={"one_line_conclusion": "<html>bad</html>"})
    extraction = extract_report(REPORT_ID, _sidecar([unsafe]))
    assert extraction.faults == []
    assert extraction.fault_errors[0]["error"] == "html_content"


def test_operation_mixed_when_stage_operations_conflict():
    payload = _sidecar(
        [_fault("F01")],
        statistics={
            "stage_breakdowns": [{"operation": "GET"}, {"operation": "SET"}],
            "top_hosts": [],
        },
    )
    extraction = extract_report(REPORT_ID, payload)
    assert extraction.operation == "MIXED"


def test_source_fault_hash_tracks_only_applicability_fields():
    payload = _sidecar([_fault("F01")])
    base_hash = extract_report(REPORT_ID, payload).faults[0].source_fault_hash

    cosmetic = copy.deepcopy(payload)
    cosmetic["faults"][0]["solution"]["short_term"] = ["换一种处置顺序"]
    cosmetic["basic_info"]["time_range_start"] = "2026-10-21 08:00:00"
    assert (
        extract_report(REPORT_ID, cosmetic).faults[0].source_fault_hash == base_hash
    )

    changed_operation = copy.deepcopy(payload)
    changed_operation["basic_info"]["operation"] = "SET"
    assert (
        extract_report(REPORT_ID, changed_operation).faults[0].source_fault_hash
        != base_hash
    )


def test_hashes_are_deterministic_and_canonical():
    payload = _sidecar([_fault("F01")])
    reordered = copy.deepcopy(payload)
    reordered = dict(reversed(list(reordered.items())))

    assert compute_sidecar_hash(payload) == compute_sidecar_hash(reordered)
    fault = payload["faults"][0]
    assert compute_source_fault_hash(fault, "F01", "GET") == compute_source_fault_hash(
        copy.deepcopy(fault), "F01", "GET"
    )
    assert sha256_hex("abc") == (
        "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad"
    )


def test_text_respects_hard_limit():
    long_fault = _fault(
        "F01",
        title="长标题" * 200,
        conclusion={
            "one_line_conclusion": "现象" * 800,
            "key_findings": ["发现" * 300, "补充" * 300, "更多" * 300],
        },
    )
    extraction = extract_report(REPORT_ID, _sidecar([long_fault]))
    assert len(extraction.faults[0].text) <= TEXT_HARD_LIMIT


def test_legacy_placeholder_is_skipped_but_readable_case_is_indexed():
    assert extract_legacy_doc(
        {"id": "1", "description": "自动导入: dfx_write_remote_tcp_dalay"}
    ) is None

    doc = extract_legacy_doc(
        {
            "id": "2",
            "description": "远端写入偶发超时，重试后恢复",
            "case_category": "网络/TCP故障",
            "root_cause_type": "远端写入TCP延迟",
            "task_names": ["lingqu_kvcache_x.zip"],
        }
    )
    assert doc is not None
    assert doc.doc_id == "legacy:2"
    assert doc.verification == VerificationLevel.LEGACY_UNVERIFIED.value
    assert "远端写入偶发超时" in doc.text
    assert "网络/TCP故障" in doc.text
    assert "lingqu_kvcache_x.zip" not in doc.text


def test_case_doc_excludes_root_cause_detail_and_remediation():
    case = DiagCaseLibraryModel(
        id="case-1",
        case_no="UB-CASE-000001",
        status="confirmed",
        title="SET 首包超时",
        symptom_summary="SET 请求在客户端等待超过 2 秒",
        root_cause_summary="建链队列拥塞",
        root_cause_detail="这里是根因机理长文，不应进入检索文本",
        operation="SET",
        fault_type="latency",
        latency_components=["set_client"],
        log_keywords=["Connect Timeout"],
        remediation_json=[],
        verification_json=VerificationModel(closed_loop=True),
    )
    doc = extract_case_doc(case)

    assert doc.doc_id == "case:case-1"
    assert doc.verification == VerificationLevel.VERIFIED.value
    assert "SET 首包超时" in doc.text
    assert "set_client" in doc.text
    assert "Connect Timeout" in doc.text
    assert "根因机理长文" not in doc.text
    assert "重启" not in doc.text


def test_scrubber_handles_ipv6_path_and_long_trace():
    scrubber = IdentityScrubber()
    text = scrubber.clean(
        "节点 fd00::1 访问 /var/log/x.log trace 0123456789abcdef "
        "时间 2026-10-21 10:15:00"
    )
    assert "[IP]" in text
    assert "[文件]" in text
    assert "[TRACE]" in text
    assert "[时间]" in text


def test_binding_request_requires_pair():
    base = {
        "log_type": "KVCache",
        "source": "internal",
        "title": "案例",
        "symptom_summary": "现象",
        "root_cause_summary": "根因",
    }
    with pytest.raises(ValidationError):
        CreateDiagCaseDraftRequest(**base, report_id="r1")
    with pytest.raises(ValidationError):
        CreateDiagCaseDraftRequest(**base, source_fault_id="F01")
    request = CreateDiagCaseDraftRequest(
        **base,
        report_id="r1",
        source_fault_id="F01",
        expected_sidecar_hash="a" * 64,
    )
    assert request.report_id == "r1"
    assert request.source_fault_id == "F01"
