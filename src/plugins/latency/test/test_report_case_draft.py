# Copyright (c) Huawei Technologies Co., Ltd. 2023-2025. All rights reserved.
"""Report fault → case draft preview contract tests."""
from __future__ import annotations

import copy

import pytest

from latency.services import label_taxonomy
from latency.services.report_case_draft import build_draft_from_fault
from latency.services.report_phenomenon import compute_source_fault_hash

REPORT_ID = "report_kb_20261021_101500"
SIDECAR_HASH = "a" * 64


def _labels() -> tuple[str, str]:
    options = label_taxonomy.label_options()
    first = options["first_level_labels"][0]
    pair = next(
        item for item in options["pairs"] if item["first_level_label"] == first
    )
    return first, pair["second_level_labels"][0]


def _payload() -> dict:
    first, second = _labels()
    return {
        "report": {"title": "KVCache 时延诊断报告"},
        "basic_info": {
            "kb_id": "kb-1",
            "kb_name": "YXH LOGS",
            "operation": "GET",
            "log_id": "log-9",
        },
        "faults": [
            {
                "id": "F01",
                "title": "GET 阻塞于对象订阅超时",
                "status": "confirmed",
                "category": "latency",
                "confidence": 85,
                "conclusion": {
                    "first_level_label": first,
                    "second_level_label": second,
                    "one_line_conclusion": "GET 等待约 1.8 秒",
                    "key_findings": ["耗时集中在 Worker", "P99 约 1.8s"],
                },
                "root_cause": {
                    "confirmed_root_cause": "对象不存在时阻塞在订阅等待",
                    "reasoning_chain": [
                        {
                            "step_label": "S1",
                            "title": "排除网络",
                            "description": "链路无丢包",
                            "evidence": "ping ok",
                            "excluded": True,
                        },
                        {
                            "step_label": "S2",
                            "title": "对象缺失",
                            "description": "对象不存在导致等待",
                            "evidence": "trace t-1",
                            "excluded": False,
                        },
                    ],
                },
                "evidence_traces": [
                    {
                        "trace_id": "t-1",
                        "status_code": "3",
                        "pod": "pod-a",
                        "why": "订阅超时",
                    },
                    {"status_code": "3"},
                    {"status_code": "0"},
                ],
                "knowledge_matches": [{"id": "kvcache_access_003"}],
                "solution": {"short_term": ["重启 Worker", "观察 10 分钟"]},
            }
        ],
    }


def test_full_fault_maps_to_a_ready_draft():
    payload = _payload()

    preview = build_draft_from_fault(REPORT_ID, payload, "F01", SIDECAR_HASH)

    assert preview.ready is True
    assert preview.missing_fields == []
    assert preview.expected_sidecar_hash == SIDECAR_HASH
    assert preview.source_fault_hash == compute_source_fault_hash(
        payload["faults"][0], "F01", "GET"
    )

    draft = preview.draft
    assert draft["title"] == "GET 阻塞于对象订阅超时"
    assert draft["symptom_summary"] == "GET 等待约 1.8 秒；耗时集中在 Worker；P99 约 1.8s"
    assert draft["root_cause_summary"] == "对象不存在时阻塞在订阅等待"
    assert "对象缺失：对象不存在导致等待（证据：trace t-1）" in draft["root_cause_detail"]
    assert "排除网络" not in draft["root_cause_detail"]
    assert draft["evidence_json"] == [
        {
            "kind": "trace",
            "ref": "t-1",
            "params": {},
            "excerpt": "订阅超时",
            "note": "pod-a",
        }
    ]
    assert draft["remediation_json"] == [
        {"step": 1, "action": "重启 Worker"},
        {"step": 2, "action": "观察 10 分钟"},
    ]
    assert draft["counter_evidence_json"] == [
        {
            "step_label": "S1",
            "title": "排除网络",
            "description": "链路无丢包",
            "evidence": "ping ok",
        }
    ]
    assert draft["status_codes"] == ["3"]
    assert draft["failure_mode_ids"] == ["kvcache_access_003"]
    assert draft["operation"] == "GET"
    assert draft["fault_type"] == "latency"
    assert draft["confidence"] == 0.85
    assert draft["kb_id"] == "kb-1"
    assert draft["kb_name"] == "YXH LOGS"
    assert draft["source_log_ids"] == ["log-9"]
    assert draft["log_type"] == "KVCache"
    assert draft["source"] == "internal"


def test_labels_are_copied_from_the_fault_with_a_snapshot_hash():
    first, second = _labels()

    preview = build_draft_from_fault(REPORT_ID, _payload(), "F01", SIDECAR_HASH)

    assert preview.labels["status"] == "pair"
    assert preview.labels["first_level_label"] == first
    assert preview.labels["second_level_label"] == second
    assert preview.labels["taxonomy_version"] == label_taxonomy.label_options()["version"]
    assert preview.labels["snapshot_hash"] == label_taxonomy.label_snapshot_hash(
        first, second, preview.labels["taxonomy_version"]
    )


def test_unclassified_fault_is_reported_but_does_not_block_draft_creation():
    payload = _payload()
    del payload["faults"][0]["conclusion"]["first_level_label"]
    del payload["faults"][0]["conclusion"]["second_level_label"]

    preview = build_draft_from_fault(REPORT_ID, payload, "F01", SIDECAR_HASH)

    assert preview.labels["status"] == "empty"
    assert preview.missing_fields == []
    assert preview.ready is True


@pytest.mark.parametrize(
    "mutate, fragment",
    [
        (lambda payload: payload["faults"][0].update(evidence_traces=[]), "evidence_json"),
        (
            lambda payload: payload["faults"][0]["solution"].update(short_term=[]),
            "remediation_json",
        ),
        (
            lambda payload: payload["faults"][0].update(
                evidence_traces=[], knowledge_matches=[]
            ),
            "matchable_signal",
        ),
        (
            lambda payload: payload["faults"][0]["conclusion"].update(
                first_level_label="不存在的分类"
            ),
            "label_invalid",
        ),
    ],
)
def test_missing_gate_fields_are_reported_not_fabricated(mutate, fragment):
    payload = _payload()
    mutate(payload)

    preview = build_draft_from_fault(REPORT_ID, payload, "F01", SIDECAR_HASH)

    assert preview.ready is False
    assert fragment in preview.missing_fields


def test_taxonomy_unavailable_is_reported(monkeypatch):
    def unavailable(*args, **kwargs):
        raise label_taxonomy.TaxonomyError("label_taxonomy_missing")

    monkeypatch.setattr(label_taxonomy, "validate_labels", unavailable)

    preview = build_draft_from_fault(REPORT_ID, _payload(), "F01", SIDECAR_HASH)

    assert preview.labels["status"] == "unavailable"
    assert preview.labels["snapshot_hash"] is None
    assert "label_taxonomy_unavailable" in preview.missing_fields


@pytest.mark.parametrize(
    "fault_id, fault_override, error",
    [
        ("F99", {}, "fault_not_found"),
        ("auto:abc:01", {"id": "auto:abc:01"}, "fault_not_stable"),
        ("F01", {"status": "excluded"}, "fault_excluded"),
    ],
)
def test_unusable_faults_are_rejected(fault_id, fault_override, error):
    payload = _payload()
    payload["faults"][0].update(fault_override)

    with pytest.raises(ValueError) as exc_info:
        build_draft_from_fault(REPORT_ID, payload, fault_id, SIDECAR_HASH)
    assert str(exc_info.value) == error


def test_flat_single_fault_report_uses_the_synthetic_id_and_is_rejected():
    payload = _payload()
    flat = {key: value for key, value in payload.items() if key != "faults"}
    flat.update(
        {
            "title": payload["faults"][0]["title"],
            "status": "confirmed",
            "category": "latency",
            "conclusion": payload["faults"][0]["conclusion"],
            "root_cause": payload["faults"][0]["root_cause"],
            "evidence_traces": payload["faults"][0]["evidence_traces"],
            "knowledge_matches": payload["faults"][0]["knowledge_matches"],
            "solution": payload["faults"][0]["solution"],
        }
    )

    with pytest.raises(ValueError) as exc_info:
        build_draft_from_fault(REPORT_ID, flat, "F01", SIDECAR_HASH)
    assert str(exc_info.value) == "fault_not_found"


def test_confidence_accepts_text_percent_and_clamps():
    for value, expected in ((85, 0.85), (0.42, 0.42), ("85%", 0.85), (150, 1.0), ("x", 0.0)):
        payload = copy.deepcopy(_payload())
        payload["faults"][0]["confidence"] = value
        preview = build_draft_from_fault(REPORT_ID, payload, "F01", SIDECAR_HASH)
        assert preview.draft["confidence"] == pytest.approx(expected)
