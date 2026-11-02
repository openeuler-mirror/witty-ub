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


def _merge_scope_limits(existing: Any, note: str) -> str:
    current = _text(existing)
    return f"{current}；{note}" if current else note


def _text(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _unique_texts(values: list[Any]) -> list[str]:
    result: list[str] = []
    for value in values:
        item = _text(value)
        if item and item not in result:
            result.append(item)
    return result


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
            return items

    # !360 stores reproducible request provenance inside the deterministic
    # error/latency feature blocks.  These are valid API evidence anchors even
    # when no representative trace was returned.
    latency = _as_dict(fault.get("latency"))
    for stage in _as_list(latency.get("stages")):
        if not isinstance(stage, dict):
            continue
        features = _as_dict(stage.get("features"))
        source = _as_dict(features.get("source"))
        endpoint = _text(source.get("endpoint"))
        request = _as_dict(source.get("request"))
        if endpoint and request:
            items.append({
                "kind": "api",
                "ref": endpoint,
                "params": request,
                "excerpt": None,
                "note": _text(stage.get("name")) or _text(features.get("bucket_key")),
            })
        if len(items) >= 5:
            return items

    error = _as_dict(fault.get("error"))
    for breakdown in _as_list(error.get("breakdowns")):
        if not isinstance(breakdown, dict):
            continue
        source = _as_dict(breakdown.get("source"))
        endpoint = _text(source.get("endpoint"))
        for page in _as_list(source.get("pages")):
            request = _as_dict(page.get("request")) if isinstance(page, dict) else {}
            if endpoint and request:
                items.append({
                    "kind": "api",
                    "ref": endpoint,
                    "params": request,
                    "excerpt": None,
                    "note": f"{_text(breakdown.get('operation')) or 'N/A'} 错误码时间聚合",
                })
            if len(items) >= 5:
                return items
    return items


def _remediation(
    fault: dict[str, Any], payload: dict[str, Any], fault_id: str
) -> list[dict[str, Any]]:
    solution = _as_dict(fault.get("solution"))
    verifications = _unique_texts(_as_list(solution.get("verification")))
    items: list[dict[str, Any]] = []
    for action in _unique_texts(
        _as_list(solution.get("short_term")) + _as_list(solution.get("long_term"))
    ):
        item: dict[str, Any] = {"step": len(items) + 1, "action": action}
        if len(items) < len(verifications):
            item["expected"] = verifications[len(items)]
        items.append(item)

    for plan in _as_list(payload.get("action_plan")):
        if not isinstance(plan, dict):
            continue
        fault_ids = _unique_texts(_as_list(plan.get("fault_ids")))
        if fault_ids and fault_id not in fault_ids:
            continue
        action = _text(plan.get("action"))
        if not action or any(item["action"] == action for item in items):
            continue
        item = {"step": len(items) + 1, "action": action}
        expected = _text(plan.get("verify")) or _text(plan.get("expected_effect"))
        if expected:
            item["expected"] = expected
        items.append(item)
    return items


def _latency_features(
    fault: dict[str, Any],
) -> tuple[list[str], dict[str, Any] | None, list[str], list[str], list[str]]:
    """Map !360 per-stage features into the !361 case signal contract."""
    features_list: list[dict[str, Any]] = []
    for stage in _as_list(_as_dict(fault.get("latency")).get("stages")):
        if isinstance(stage, dict) and isinstance(stage.get("features"), dict):
            features_list.append(stage["features"])

    components = _unique_texts([item.get("bucket_key") for item in features_list])
    hosts: list[Any] = []
    src_ips: list[Any] = []
    dst_ips: list[Any] = []
    for features in features_list:
        for trace in _as_list(features.get("top_traces")):
            if not isinstance(trace, dict):
                continue
            hosts.append(trace.get("host"))
            src_ips.append(trace.get("src_ip"))
            dst_ips.append(trace.get("dst_ip"))

    operations = _unique_texts([item.get("operation") for item in features_list])
    snapshot: dict[str, Any] | None = None
    if features_list and len(operations) == 1:
        buckets = []
        for features in features_list:
            distribution = _as_dict(features.get("distribution"))
            buckets.append({
                "key": features.get("bucket_key"),
                "trace_cnt": features.get("trace_cnt", 0),
                "success_cnt": features.get("normal_cnt", 0),
                "fail_cnt": features.get("anomalous_cnt", 0),
                "p50_ms": distribution.get("p50_ms"),
                "p90_ms": distribution.get("p90_ms"),
                "max_ms": distribution.get("max_ms"),
                "metric_name": features.get("metric_name"),
                "note": features.get("note"),
            })
        snapshot = {
            "operation": operations[0],
            "buckets": buckets,
            "sample_cnt": max(
                (item.get("sample_cnt", 0) for item in features_list), default=0
            ),
            "truncated": any(item.get("truncated") is True for item in features_list),
        }
    return (
        components,
        snapshot,
        _unique_texts(hosts),
        _unique_texts(src_ips),
        _unique_texts(dst_ips),
    )


def _scoped_statistics(
    payload: dict[str, Any], fault_id: str, single_fault: bool
) -> tuple[list[str], list[str]]:
    statistics = _as_dict(payload.get("statistics"))

    def belongs(item: dict[str, Any]) -> bool:
        owner = _text(item.get("fault"))
        return owner == fault_id or (owner is None and single_fault)

    hosts = [
        item.get("host")
        for item in _as_list(statistics.get("top_hosts"))
        if isinstance(item, dict) and belongs(item)
    ]
    pods = [
        item.get("pod")
        for item in _as_list(statistics.get("top_pods"))
        if isinstance(item, dict) and belongs(item)
    ]
    return _unique_texts(hosts), _unique_texts(pods)


def _error_scope(fault: dict[str, Any]) -> tuple[str | None, list[str], list[str]]:
    clusters: list[Any] = []
    src_ips: list[Any] = []
    dst_ips: list[Any] = []
    for breakdown in _as_list(_as_dict(fault.get("error")).get("breakdowns")):
        if not isinstance(breakdown, dict):
            continue
        scope = _as_dict(breakdown.get("scope"))
        clusters.append(scope.get("cluster_name"))
        src_ips.append(scope.get("src_ip"))
        dst_ips.append(scope.get("dst_ip"))
    cluster_names = _unique_texts(clusters)
    return (
        cluster_names[0] if len(cluster_names) == 1 else None,
        _unique_texts(src_ips),
        _unique_texts(dst_ips),
    )


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
    )
    evidence = _evidence(fault)
    remediation = _remediation(fault, payload, fault_id)
    legacy_error_items = (
        _as_list(_as_dict(payload.get("statistics")).get("top_error_codes"))
        if len(faults) == 1
        else []
    )
    status_codes = report_phenomenon.valid_status_codes(fault, legacy_error_items)
    failure_mode_ids = report_phenomenon.valid_failure_mode_ids(fault)
    latency_components, stage_features, latency_hosts, latency_src, latency_dst = (
        _latency_features(fault)
    )
    stats_hosts, stats_pods = _scoped_statistics(payload, fault_id, len(faults) == 1)
    cluster_name, error_src, error_dst = _error_scope(fault)
    trace_hosts = _unique_texts([
        trace.get("host")
        for trace in _as_list(fault.get("evidence_traces"))
        if isinstance(trace, dict)
    ])
    trace_pods = _unique_texts([
        trace.get("pod")
        for trace in _as_list(fault.get("evidence_traces"))
        if isinstance(trace, dict)
    ])
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
        "cluster_name": cluster_name,
        "hosts": _unique_texts(stats_hosts + trace_hosts + latency_hosts),
        "pods": _unique_texts(stats_pods + trace_pods),
        "src_ips": _unique_texts(error_src + latency_src),
        "dst_ips": _unique_texts(error_dst + latency_dst),
        "node_type": None,
        "version_json": None,
        "scope_limits": None,
        # MIXED 表示整份报告同时覆盖 GET/SET，无法归属单一操作；检索时两种操作都能命中，
        # 不能退化成 NULL（NULL 既查不到也无法解释「为什么两种操作都相关」）。
        "operation": (
            operation
            if operation in {"GET", "SET", "N/A", "MIXED"}
            else None
        ),
        "fault_type": report_phenomenon.fault_category(fault),
        "status_codes": status_codes,
        "failure_mode_ids": failure_mode_ids,
        "latency_components": latency_components,
        "log_keywords": [],
        "stage_features_json": stage_features,
        "fault_shape": None,
        "time_window_json": (
            {
                "start": _text(basic.get("time_range_start")),
                "end": _text(basic.get("time_range_end")),
            }
            if _text(basic.get("time_range_start"))
            or _text(basic.get("time_range_end"))
            else None
        ),
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
    if not any((
        status_codes,
        failure_mode_ids,
        latency_components,
        draft["log_keywords"],
        draft["hosts"],
        draft["pods"],
        draft["src_ips"],
        draft["dst_ips"],
        draft["cluster_name"],
    )):
        missing.append("matchable_signal")
    if labels["status"] == "invalid":
        missing.append("label_invalid")
    if labels["status"] == "unavailable":
        missing.append("label_taxonomy_unavailable")

    # 字段不全的案例要能一眼看出「摘要为派生、结论需回看原报告」，
    # 否则与字段齐全的案例混在一起，读者无法分辨证据链是否完整。
    if missing:
        draft["scope_limits"] = _merge_scope_limits(
            draft.get("scope_limits"),
            "来源报告字段不完整（缺 "
            + "、".join(missing)
            + "）；摘要由报告其余内容派生，关键结论请回看来源定界文档。",
        )

    return CaseDraftPreview(
        report_id=report_id,
        source_fault_id=fault_id,
        expected_sidecar_hash=expected_sidecar_hash,
        source_fault_hash=report_phenomenon.compute_source_fault_hash(
            fault, fault_id, operation, status_codes
        ),
        labels=labels,
        draft=draft,
        missing_fields=missing,
    )
