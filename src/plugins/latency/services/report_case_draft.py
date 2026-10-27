# Copyright (c) Huawei Technologies Co., Ltd. 2023-2025. All rights reserved.
"""Deterministic mapping from a confirmed report fault to a case draft.

The generated draft never invents evidence or remediation. Fields without
source data are reported in ``missing_fields`` so the caller can see why the
confirm gate cannot pass yet.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from latency.services import label_taxonomy, report_phenomenon
from latency.services.report_phenomenon import _as_dict, _as_list


@dataclass(slots=True)
class CaseDraftPreview:
    report_id: str
    source_fault_id: str
    expected_sidecar_hash: str
    source_fault_hash: str
    labels: dict[str, Any]
    draft: dict[str, Any]
    missing_fields: list[str] = field(default_factory=list)

    @property
    def ready(self) -> bool:
        return not self.missing_fields


def _text(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _confidence(value: Any) -> float:
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        number = float(value)
        return max(0.0, min(1.0, number / 100 if number > 1 else number))
    text = _text(value)
    if not text:
        return 0.0
    try:
        number = float(text.rstrip("%"))
    except ValueError:
        return 0.0
    return max(0.0, min(1.0, number / 100 if number > 1 or text.endswith("%") else number))


def _symptom(conclusion: dict[str, Any], title: str | None) -> str | None:
    parts = [_text(conclusion.get("one_line_conclusion"))]
    parts.extend(
        str(item) for item in _as_list(conclusion.get("key_findings"))[:5] if item
    )
    text = "；".join(item for item in parts if item)
    return text or title


def _root_cause_detail(root_cause: dict[str, Any]) -> str | None:
    steps: list[str] = []
    for step in _as_list(root_cause.get("reasoning_chain")):
        if not isinstance(step, dict) or step.get("excluded"):
            continue
        title = _text(step.get("title"))
        description = _text(step.get("description"))
        evidence = _text(step.get("evidence"))
        if not description:
            continue
        line = f"{title}：{description}" if title else description
        if evidence:
            line = f"{line}（证据：{evidence}）"
        steps.append(line)
    return "\n".join(steps) or None


def _evidence(fault: dict[str, Any]) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    for trace in _as_list(fault.get("evidence_traces")):
        if not isinstance(trace, dict):
            continue
        trace_id = _text(trace.get("trace_id"))
        if not trace_id:
            continue
        items.append(
            {
                "kind": "trace",
                "ref": trace_id,
                "params": {},
                "excerpt": _text(trace.get("why")) or _text(trace.get("status_code")),
                "note": _text(trace.get("pod")),
            }
        )
        if len(items) >= 5:
            break
    return items


def _remediation(fault: dict[str, Any]) -> list[dict[str, Any]]:
    solution = _as_dict(fault.get("solution"))
    actions = [
        str(item).strip()
        for item in _as_list(solution.get("short_term"))
        if str(item).strip()
    ]
    return [
        {"step": index, "action": action}
        for index, action in enumerate(actions, start=1)
    ]


def _labels(fault: dict[str, Any]) -> dict[str, Any]:
    conclusion = report_phenomenon.fault_conclusion(fault)
    try:
        validation = label_taxonomy.validate_labels(
            conclusion.get("first_level_label"),
            conclusion.get("second_level_label"),
        )
    except label_taxonomy.TaxonomyError:
        return {
            "first_level_label": None,
            "second_level_label": None,
            "status": "unavailable",
            "error": "label_taxonomy_unavailable",
            "taxonomy_version": None,
            "snapshot_hash": None,
        }
    snapshot_hash = (
        label_taxonomy.label_snapshot_hash(
            validation.first_level_label,
            validation.second_level_label,
            validation.taxonomy_version or "",
        )
        if validation.taxonomy_version
        else None
    )
    return {
        "first_level_label": validation.first_level_label,
        "second_level_label": validation.second_level_label,
        "status": validation.status,
        "error": validation.error,
        "taxonomy_version": validation.taxonomy_version,
        "snapshot_hash": snapshot_hash,
    }


def build_draft_from_fault(
    report_id: str,
    payload: dict[str, Any],
    fault_id: str,
    expected_sidecar_hash: str,
) -> CaseDraftPreview:
    faults = report_phenomenon.normalise_faults(payload)
    fault = next(
        (
            item
            for item in faults
            if str(item.get("id") or "") == fault_id
        ),
        None,
    )
    if fault is None:
        raise ValueError("fault_not_found")
    if fault_id.startswith("auto:") or not fault_id:
        raise ValueError("fault_not_stable")
    if str(fault.get("status") or "").lower() == "excluded":
        raise ValueError("fault_excluded")

    basic = _as_dict(payload.get("basic_info"))
    report = _as_dict(payload.get("report"))
    conclusion = report_phenomenon.fault_conclusion(fault)
    root_cause = _as_dict(fault.get("root_cause"))
    operation = report_phenomenon.fault_operation(payload)
    title = _text(fault.get("title")) or _text(report.get("title")) or fault_id
    symptom = _symptom(conclusion, title)
    root_cause_summary = (
        _text(root_cause.get("confirmed_root_cause"))
        or _text(conclusion.get("one_line_conclusion"))
        or title
    )
    evidence = _evidence(fault)
    remediation = _remediation(fault)
    status_codes = report_phenomenon.valid_status_codes(fault)
    failure_mode_ids = report_phenomenon.valid_failure_mode_ids(fault)
    labels = _labels(fault)

    draft = {
        "log_type": "KVCache",
        "source": "internal",
        "source_url": None,
        "title": title,
        "symptom_summary": symptom,
        "root_cause_summary": root_cause_summary,
        "root_cause_detail": _root_cause_detail(root_cause),
        "created_by": None,
        "kb_id": _text(basic.get("kb_id")),
        "kb_name": _text(basic.get("kb_name")),
        "cluster_name": None,
        "hosts": [],
        "pods": [],
        "src_ips": [],
        "dst_ips": [],
        "node_type": None,
        "version_json": None,
        "scope_limits": None,
        "operation": operation if operation in {"GET", "SET"} else None,
        "fault_type": report_phenomenon.fault_category(fault),
        "status_codes": status_codes,
        "failure_mode_ids": failure_mode_ids,
        "latency_components": [],
        "log_keywords": [],
        "stage_features_json": None,
        "fault_shape": None,
        "time_window_json": None,
        "confidence": _confidence(fault.get("confidence")),
        "evidence_json": evidence,
        "counter_evidence_json": [
            {
                "step_label": step.get("step_label"),
                "title": step.get("title"),
                "description": step.get("description"),
                "evidence": step.get("evidence"),
            }
            for step in _as_list(root_cause.get("reasoning_chain"))
            if isinstance(step, dict) and step.get("excluded")
        ],
        "remediation_json": remediation,
        "verification_json": None,
        "relations_json": [],
        "source_log_ids": [
            str(basic.get("log_id"))
        ] if _text(basic.get("log_id")) else [],
        "verification_history_json": [],
    }

    missing: list[str] = []
    if not symptom:
        missing.append("symptom_summary")
    if not root_cause_summary:
        missing.append("root_cause_summary")
    if not evidence:
        missing.append("evidence_json")
    if not remediation:
        missing.append("remediation_json")
    if not (status_codes or failure_mode_ids):
        missing.append("matchable_signal")
    if labels["status"] == "invalid":
        missing.append("label_invalid")
    if labels["status"] == "unavailable":
        missing.append("label_taxonomy_unavailable")

    return CaseDraftPreview(
        report_id=report_id,
        source_fault_id=fault_id,
        expected_sidecar_hash=expected_sidecar_hash,
        source_fault_hash=report_phenomenon.compute_source_fault_hash(
            fault, fault_id, operation
        ),
        labels=labels,
        draft=draft,
        missing_fields=missing,
    )
