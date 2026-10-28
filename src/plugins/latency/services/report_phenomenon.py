# Copyright (c) Huawei Technologies Co., Ltd. 2023-2025. All rights reserved.
"""Deterministic phenomenon extraction for reports, new cases and legacy cases.

This module is deliberately pure: it never touches PostgreSQL, the file system or
the network.  The same input must always produce byte-identical ``text`` and
``content_hash`` so cards can be rebuilt safely.
"""
from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Iterable
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from latency.ENUM.phenomenon import (
    BindingStatus,
    PhenomenonContentSource,
    PhenomenonKind,
    VerificationLevel,
)

TEXT_HARD_LIMIT = 1200
HISTORICAL_REPORT_PREFIX = "report_hist_"
SYMPTOM_LIMIT = 400
KEY_FINDINGS_LIMIT = 3

STABLE_FAULT_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]{0,63}$")
FAILURE_MODE_ID_RE = re.compile(r"^[a-z][a-z0-9]*(?:_[a-z0-9]+){2,}$")
UUID_RE = re.compile(
    r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-"
    r"[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$"
)
AUTO_IMPORT_PLACEHOLDER_RE = re.compile(r"^自动导入\s*[:：]\s*\S+\s*$")

_HTML_MARKERS = ("<!doctype", "<html", "<script", "<style")
_IPV4_RE = re.compile(r"(?<![\d.])(?:\d{1,3}\.){3}\d{1,3}(?![\d.])")
_IPV6_RE = re.compile(
    r"(?<![\w:])(?:[0-9A-Fa-f]{0,4}:){2,7}[0-9A-Fa-f]{0,4}(?![\w:])"
)
_LONG_HEX_RE = re.compile(r"\b[0-9A-Fa-f]{16,}\b")
_TIMESTAMP_RE = re.compile(
    r"\b\d{4}-\d{2}-\d{2}(?:[ T]\d{2}:\d{2}:\d{2}(?:\.\d+)?)?\b"
)
_URL_RE = re.compile(r"https?://\S+")
_ABS_PATH_RE = re.compile(r"(?<![\w./])/(?:[\w.\-]+/)*[\w.\-]+")
# 只匹配真正的 K8s 资源引用（pod/<dns-label>），用于抓没被词表替换掉的身份。
# 中文分类标签（Pod/容器生命周期）、自然语言并列（pod/host）都不是身份引用，
# 早先的 \b(?:pod|host)/ 会把它们一起拦下，导致整条卡片被判 identity_residual。
_POD_HOST_PREFIX_RE = re.compile(
    r"(?i)\b(?:pod|host)/(?=[a-z0-9][a-z0-9-]*[a-z0-9])(?!(?:pod|host)\b)"
)

MARKERS = {
    "host": "[主机]",
    "pod": "[POD]",
    "ip": "[IP]",
    "cluster": "[集群]",
    "file": "[文件]",
    "task": "[任务]",
    "trace": "[TRACE]",
}


class PhenomenonContentError(ValueError):
    """Extracted text is not safe or valid for upload."""

    def __init__(self, code: str, detail: str = ""):
        self.code = code
        self.detail = detail
        super().__init__(f"{code}: {detail}" if detail else code)


@dataclass(slots=True)
class PhenomenonDoc:
    """Card contract without persistence columns."""

    doc_id: str
    kind: str
    content_source: str
    title: str
    symptom: str
    text: str
    content_hash: str
    verification: str
    fault_type: str = "unknown"
    root_cause_summary: str | None = None
    report_id: str | None = None
    source_fault_id: str | None = None
    source_fault_hash: str | None = None
    first_level_label: str | None = None
    second_level_label: str | None = None
    case_id: str | None = None
    case_no: str | None = None
    legacy_case_id: str | None = None
    log_type: str | None = None
    operation: str | None = None
    status_codes: list[str] = field(default_factory=list)
    failure_mode_ids: list[str] = field(default_factory=list)
    binding_status: str = BindingStatus.NONE.value


@dataclass(slots=True)
class ReportExtraction:
    """Report-level metadata plus one card per indexable fault."""

    report_id: str
    kb_id: str | None
    kb_name: str | None
    title: str | None
    generated_at: str | None
    operation: str | None
    time_range_start: str | None
    time_range_end: str | None
    fault_count: int | None
    sidecar_hash: str
    faults: list[PhenomenonDoc]
    fault_errors: list[dict[str, str]] = field(default_factory=list)


def canonical_json(value: Any) -> str:
    """Stable JSON serialization used by every hash in this module."""
    return json.dumps(
        value,
        ensure_ascii=False,
        allow_nan=False,
        sort_keys=True,
        separators=(",", ":"),
    )


def sha256_hex(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def compute_sidecar_hash(payload: Any) -> str:
    return sha256_hex(canonical_json(payload))


def _safe_clean(scrubber: IdentityScrubber, value: str | None) -> str | None:
    """Best-effort cleaning for local-only metadata that is never uploaded."""
    try:
        return scrubber.clean(value)
    except PhenomenonContentError:
        return None


def _plain(value: Any) -> Any:
    return value.value if isinstance(value, Enum) else value


def _as_dict(value: Any) -> dict:
    return value if isinstance(value, dict) else {}


def _as_list(value: Any) -> list:
    return value if isinstance(value, list) else []


def _raw_text(value: Any) -> str | None:
    """Keep report-provided label strings untouched for later validation."""
    return value if isinstance(value, str) else None


def _text(value: Any) -> str | None:
    if value is None:
        return None
    text = str(_plain(value)).strip()
    return text or None


def _sentence(value: str) -> str:
    text = re.sub(r"\s+", " ", value).strip()
    return text.rstrip("。；;，, ")


def _join_sentences(parts: Iterable[str | None]) -> str:
    cleaned = []
    for part in parts:
        if not part:
            continue
        sentence = _sentence(str(part))
        if sentence:
            cleaned.append(sentence)
    return "。".join(cleaned) + ("。" if cleaned else "")


def _truncate_at_sentence(text: str, limit: int) -> str:
    if len(text) <= limit:
        return text
    head = text[:limit]
    for separator in ("。", "；", ";", "，", ","):
        index = head.rfind(separator)
        if index >= limit // 2:
            return head[: index + 1]
    # The ellipsis counts toward the hard limit.
    return head[: limit - 1].rstrip() + "…"


def _limit_text(required: list[str | None], optional: list[str | None]) -> str:
    """Build text, dropping low-priority parts before hard truncation."""
    text = _join_sentences(required + optional)
    while len(text) > TEXT_HARD_LIMIT and optional:
        optional.pop()
        text = _join_sentences(required + optional)
    if len(text) > TEXT_HARD_LIMIT:
        text = _truncate_at_sentence(text, TEXT_HARD_LIMIT)
    return text


class IdentityScrubber:
    """Two-layer identity filter."""

    _VALUE_KEYS = {
        "host": "host",
        "hosts": "host",
        "top_hosts": "host",
        "pod": "pod",
        "pods": "pod",
        "top_pods": "pod",
        "src_ip": "ip",
        "src_ips": "ip",
        "dst_ip": "ip",
        "dst_ips": "ip",
        "cluster_name": "cluster",
        "clusters": "cluster",
        "log_file": "file",
        "log_file_name": "file",
        "task_names": "task",
        "trace_id": "trace",
    }

    def __init__(self, replacements: dict[str, str] | None = None):
        self._replacements = dict(replacements or {})

    @classmethod
    def from_payload(cls, payload: Any) -> IdentityScrubber:
        replacements: dict[str, str] = {}
        cls._collect(payload, replacements, depth=0)
        # Longest first so a host name is not partially replaced by a shorter one.
        ordered = sorted(replacements.items(), key=lambda item: len(item[0]), reverse=True)
        return cls(dict(ordered))

    @classmethod
    def _collect(cls, node: Any, out: dict[str, str], depth: int) -> None:
        if depth > 8 or node is None:
            return
        if isinstance(node, dict):
            for key, value in node.items():
                marker = cls._VALUE_KEYS.get(str(key).lower())
                if marker:
                    cls._add_values(value, marker, out)
                else:
                    cls._collect(value, out, depth + 1)
        elif isinstance(node, list):
            for item in node:
                cls._collect(item, out, depth + 1)

    _DICT_KEYS = {
        "host": ("host", "host_name", "name"),
        "pod": ("pod", "pod_name", "name"),
        "ip": ("ip", "src_ip", "dst_ip"),
        "file": ("path", "file", "name"),
        "cluster": ("cluster", "cluster_name", "name"),
        "task": ("name", "task_name"),
        "trace": ("trace_id", "id"),
    }

    @classmethod
    def _add_values(cls, value: Any, marker: str, out: dict[str, str]) -> None:
        if isinstance(value, (list, tuple, set)):
            for item in value:
                cls._add_values(item, marker, out)
            return
        if isinstance(value, dict):
            keys = cls._DICT_KEYS.get(marker, ())
            for key in keys:
                if key in value:
                    cls._add_values(value[key], marker, out)
            return
        text = _text(value)
        if not text:
            return
        for token in re.split(r"[,，;；\s]+", text):
            token = token.strip()
            # Numbers are counts / shares, not identities; single characters are
            # too ambiguous for exact replacement.
            if len(token) >= 3 and not token.isdigit():
                out.setdefault(token, MARKERS[marker])

    def clean(self, value: str | None) -> str | None:
        if value is None:
            return None
        text = str(value)
        if any(marker in text.lower() for marker in _HTML_MARKERS):
            raise PhenomenonContentError("html_content", "text contains HTML tags")
        for token, marker in self._replacements.items():
            if token and token in text:
                text = text.replace(token, marker)

        text = _URL_RE.sub("[链接]", text)
        text = _TIMESTAMP_RE.sub("[时间]", text)
        text = _LONG_HEX_RE.sub(MARKERS["trace"], text)
        text = _IPV4_RE.sub(self._scrub_ipv4, text)
        text = _IPV6_RE.sub(self._scrub_ipv6, text)
        text = _ABS_PATH_RE.sub(MARKERS["file"], text)

        if self._has_residual_identity(text):
            raise PhenomenonContentError(
                "identity_residual", "unscrubbed identity pattern remains"
            )
        return re.sub(r"\s+", " ", text).strip()

    @staticmethod
    def _scrub_ipv4(match: re.Match) -> str:
        octets = match.group(0).split(".")
        if all(octet.isdigit() and int(octet) <= 255 for octet in octets):
            return MARKERS["ip"]
        return match.group(0)

    @staticmethod
    def _scrub_ipv6(match: re.Match) -> str:
        value = match.group(0)
        # Bare clock values such as 12:34:56 must not be treated as IPv6.
        if "::" in value or re.search(r"[A-Fa-f]", value):
            return MARKERS["ip"]
        return value

    @staticmethod
    def _has_residual_identity(text: str) -> bool:
        if _POD_HOST_PREFIX_RE.search(text):
            return True
        if _IPV4_RE.search(text):
            return True
        if any(
            "::" in match.group(0) or re.search(r"[A-Fa-f]", match.group(0))
            for match in _IPV6_RE.finditer(text)
        ):
            return True
        if _LONG_HEX_RE.search(text):
            return True
        if _ABS_PATH_RE.search(text):
            return True
        return False


def _operation_from_label(value: str | None) -> str | None:
    """Parse a report-level operation label; only the head before ``（`` counts."""
    if not value:
        return None
    head = re.split(r"[（(]", str(value).upper(), maxsplit=1)[0]
    ops = {op for op in ("GET", "SET") if op in head}
    if len(ops) > 1:
        return "MIXED"
    return ops.pop() if ops else None


def _fault_operation(payload: dict) -> str | None:
    """Report-level operation; multiple sampled stage operations collapse to MIXED."""
    report = _as_dict(payload.get("report"))
    basic = _as_dict(payload.get("basic_info"))
    label = _text(basic.get("operation") or report.get("operation"))

    statistics = _as_dict(payload.get("statistics"))
    stage_ops = {
        str(_plain(item.get("operation"))).upper()
        for item in _as_list(statistics.get("stage_breakdowns"))
        if isinstance(item, dict)
        and item.get("operation")
        and _as_list(item.get("stages"))
    }
    stage_ops &= {"GET", "SET"}
    if len(stage_ops) > 1:
        return "MIXED"
    if stage_ops:
        return stage_ops.pop()
    return _operation_from_label(label)


def _fault_category(fault: dict) -> str:
    category = _text(fault.get("category"))
    return {
        "error": "connectivity",
        "latency": "latency",
        "mixed": "mixed",
        "connectivity": "connectivity",
    }.get((category or "").lower(), "unknown")


def _valid_status_codes(
    fault: dict, fallback_items: list[dict[str, Any]] | None = None
) -> list[str]:
    """Return observed non-zero status codes in report-contract priority order.

    New reports keep per-fault distributions in ``fault.error.breakdowns``.
    ``evidence_traces`` remains a useful secondary source, while report-level
    ``statistics.top_error_codes`` is accepted only when the caller has
    established that the report contains a single fault.
    """
    codes: list[str] = []
    error = _as_dict(fault.get("error"))
    for breakdown in _as_list(error.get("breakdowns")):
        if not isinstance(breakdown, dict):
            continue
        distribution = _as_dict(breakdown.get("code_distribution"))
        for item in _as_list(distribution.get("items")):
            if not isinstance(item, dict):
                continue
            code = _text(item.get("code"))
            count = item.get("count")
            if (
                code is not None
                and code != "0"
                and isinstance(count, (int, float))
                and not isinstance(count, bool)
                and count > 0
                and code not in codes
            ):
                codes.append(code)
    for trace in _as_list(fault.get("evidence_traces")):
        if not isinstance(trace, dict):
            continue
        code = _text(trace.get("status_code"))
        if code is None or code == "0":
            continue
        if code not in codes:
            codes.append(code)
    for item in fallback_items or []:
        if not isinstance(item, dict):
            continue
        code = _text(item.get("code"))
        if code is not None and code != "0" and code not in codes:
            codes.append(code)
    return codes


def _valid_failure_mode_ids(fault: dict) -> list[str]:
    ids: list[str] = []
    for trace in _as_list(fault.get("evidence_traces")):
        if not isinstance(trace, dict):
            continue
        value = _text(trace.get("failure_mode_id"))
        if (
            value
            and value not in ids
            and not UUID_RE.match(value)
            and FAILURE_MODE_ID_RE.match(value)
        ):
            ids.append(value)
    for match in _as_list(fault.get("knowledge_matches")):
        if not isinstance(match, dict):
            continue
        value = _text(match.get("id"))
        if (
            value
            and value not in ids
            and not UUID_RE.match(value)
            and FAILURE_MODE_ID_RE.match(value)
        ):
            ids.append(value)
    return ids


def _source_fault_hash_payload(
    fault: dict,
    fault_id: str,
    operation: str | None,
    status_codes: list[str] | None = None,
) -> dict:
    conclusion = _as_dict(fault.get("conclusion"))
    root_cause = _as_dict(fault.get("root_cause"))
    return {
        "id": fault_id,
        "title": _text(fault.get("title")),
        "status": _text(fault.get("status")),
        "category": _text(fault.get("category")),
        "operation": operation,
        "conclusion.one_line_conclusion": _text(conclusion.get("one_line_conclusion")),
        "conclusion.key_findings": [
            str(item) for item in _as_list(conclusion.get("key_findings")) if item
        ],
        "conclusion.fault_domain": _text(conclusion.get("fault_domain")),
        "conclusion.fault_component": _text(conclusion.get("fault_component")),
        "root_cause.confirmed_root_cause": _text(root_cause.get("confirmed_root_cause")),
        # Keep the historical key name so reports whose effective signal did
        # not change retain their existing binding hash.
        "evidence_traces.status_code": status_codes or _valid_status_codes(fault),
        "evidence_traces.failure_mode_id": _valid_failure_mode_ids(fault),
    }


def compute_source_fault_hash(
    fault: dict,
    fault_id: str,
    operation: str | None,
    status_codes: list[str] | None = None,
) -> str:
    return sha256_hex(
        canonical_json(
            _source_fault_hash_payload(fault, fault_id, operation, status_codes)
        )
    )


def _stable_fault_ids(faults: list[dict], sidecar_hash: str) -> list[str]:
    raw_ids = [_text(fault.get("id")) for fault in faults]
    counts: dict[str, int] = {}
    for value in raw_ids:
        if value:
            counts[value] = counts.get(value, 0) + 1

    ids: list[str] = []
    auto_index = 0
    for value in raw_ids:
        stable = (
            value
            and STABLE_FAULT_ID_RE.match(value)
            and not value.startswith("auto:")
            and counts.get(value, 0) == 1
        )
        if stable:
            ids.append(value)
            continue
        auto_index += 1
        ids.append(f"auto:{sidecar_hash[:16]}:{auto_index:02d}")
    return ids


def _normalise_faults(payload: dict) -> list[dict]:
    faults = [item for item in _as_list(payload.get("faults")) if isinstance(item, dict)]
    if faults:
        return faults
    # 旧版扁平单故障报告：顶层直接是 conclusion / root_cause / solution。
    if payload.get("conclusion") or payload.get("root_cause"):
        return [
            {
                "id": None,
                "title": _as_dict(payload.get("report")).get("title"),
                "status": "confirmed",
                "category": payload.get("fault_type") or payload.get("category"),
                "conclusion": payload.get("conclusion"),
                "root_cause": payload.get("root_cause"),
                "evidence_traces": payload.get("evidence_traces") or [],
                "knowledge_matches": payload.get("knowledge_matches") or [],
            }
        ]
    return []


def normalise_faults(payload: dict) -> list[dict]:
    """Public wrapper for fault normalisation used by report-derived cases."""
    return _normalise_faults(payload)


def stable_fault_ids(payload: dict) -> list[str]:
    """Public wrapper for the stable per-fault IDs, aligned with ``faults``.

    Flat historical reports produce ``auto:`` keys, which cannot be bound to a
    case; callers must skip those explicitly instead of guessing an index.
    """
    return _stable_fault_ids(
        _normalise_faults(payload), compute_sidecar_hash(payload)
    )


def fault_conclusion(fault: dict) -> dict:
    return _as_dict(fault.get("conclusion"))


def fault_operation(payload: dict) -> str | None:
    return _fault_operation(payload)


def fault_category(fault: dict) -> str:
    return _fault_category(fault)


def valid_status_codes(
    fault: dict, fallback_items: list[dict[str, Any]] | None = None
) -> list[str]:
    return _valid_status_codes(fault, fallback_items)


def valid_failure_mode_ids(fault: dict) -> list[str]:
    return _valid_failure_mode_ids(fault)


def _fault_symptom(scrubber: IdentityScrubber, conclusion: dict) -> str:
    findings = [
        str(item)
        for item in _as_list(conclusion.get("key_findings"))[:KEY_FINDINGS_LIMIT]
        if item
    ]
    symptom = _join_sentences([conclusion.get("one_line_conclusion"), *findings])
    cleaned = scrubber.clean(symptom) or ""
    return _truncate_at_sentence(cleaned, SYMPTOM_LIMIT)


def extract_report(
    report_id: str,
    payload: dict,
    *,
    kb_dir: str | None = None,
) -> ReportExtraction:
    """Extract one card per non-excluded fault from a report sidecar."""
    sidecar_hash = compute_sidecar_hash(payload)
    report = _as_dict(payload.get("report"))
    basic = _as_dict(payload.get("basic_info"))
    operation = _fault_operation(payload)
    scrubber = IdentityScrubber.from_payload(payload)

    raw_faults = _normalise_faults(payload)
    fault_ids = _stable_fault_ids(raw_faults, sidecar_hash)
    docs: list[PhenomenonDoc] = []
    fault_errors: list[dict[str, str]] = []
    for fault, fault_id in zip(raw_faults, fault_ids, strict=False):
        status = (_text(fault.get("status")) or "suspected").lower()
        if status == "excluded":
            continue
        try:
            title = scrubber.clean(_text(fault.get("title"))) or report_id
            conclusion = _as_dict(fault.get("conclusion"))
            symptom = _fault_symptom(scrubber, conclusion) or title
            domain = scrubber.clean(_text(conclusion.get("fault_domain")))
            component = scrubber.clean(_text(conclusion.get("fault_component")))
            legacy_codes = (
                _as_list(_as_dict(payload.get("statistics")).get("top_error_codes"))
                if len(raw_faults) == 1
                else []
            )
            status_codes = _valid_status_codes(fault, legacy_codes)
            failure_mode_ids = _valid_failure_mode_ids(fault)
            status_part = f"状态码 {', '.join(status_codes)}" if status_codes else None
            text = _limit_text(
                [title, symptom],
                [domain, component, status_part],
            )
            if not text:
                raise PhenomenonContentError(
                    "empty_text", f"fault {fault_id} has no text"
                )
        except PhenomenonContentError as exc:
            # 单条故障文本不合规时拒绝该卡片，但不阻断同报告其它故障。
            fault_errors.append({"fault_id": fault_id, "error": exc.code})
            continue

        verification = (
            VerificationLevel.REPORT_ONLY
            if status == "confirmed"
            else VerificationLevel.SUSPECTED
        )
        docs.append(
            PhenomenonDoc(
                doc_id=f"report:{report_id}:{fault_id}",
                kind=PhenomenonKind.REPORT.value,
                content_source=PhenomenonContentSource.REPORT.value,
                title=title,
                symptom=symptom,
                text=text,
                content_hash=sha256_hex(text),
                verification=verification.value,
                fault_type=_fault_category(fault),
                root_cause_summary=_safe_clean(
                    scrubber,
                    _text(_as_dict(fault.get("root_cause")).get("confirmed_root_cause")),
                ),
                report_id=report_id,
                source_fault_id=fault_id,
                source_fault_hash=compute_source_fault_hash(
                    fault, fault_id, operation, status_codes
                ),
                first_level_label=_raw_text(conclusion.get("first_level_label")),
                second_level_label=_raw_text(conclusion.get("second_level_label")),
                operation=operation,
                status_codes=status_codes,
                failure_mode_ids=failure_mode_ids,
            )
        )

    return ReportExtraction(
        report_id=report_id,
        kb_id=(
            None
            if report_id.startswith(HISTORICAL_REPORT_PREFIX)
            else (_text(basic.get("kb_id")) or kb_dir)
        ),
        kb_name=(
            None
            if report_id.startswith(HISTORICAL_REPORT_PREFIX)
            else _text(basic.get("kb_name"))
        ),
        title=_safe_clean(scrubber, _text(report.get("title"))),
        generated_at=_text(report.get("generated_at")),
        operation=operation,
        time_range_start=_text(basic.get("time_range_start")),
        time_range_end=_text(basic.get("time_range_end")),
        fault_count=len(raw_faults) or None,
        sidecar_hash=sidecar_hash,
        faults=docs,
        fault_errors=fault_errors,
    )


def case_scrubber(case: Any) -> IdentityScrubber:
    """Known identity values carried by a case record."""
    def value(name: str) -> Any:
        return getattr(case, name, None) if not isinstance(case, dict) else case.get(name)

    payload = {
        "hosts": value("hosts"),
        "pods": value("pods"),
        "src_ips": value("src_ips"),
        "dst_ips": value("dst_ips"),
        "cluster_name": value("cluster_name"),
    }
    return IdentityScrubber.from_payload(payload)


def extract_case_doc(case: Any) -> PhenomenonDoc:
    """Build the independent ``case:<id>`` card for a confirmed case."""
    def value(name: str, default: Any = None) -> Any:
        return getattr(case, name, default) if not isinstance(case, dict) else case.get(name)

    scrubber = case_scrubber(case)
    case_id = str(value("id"))
    title = scrubber.clean(_text(value("title")) or _text(value("symptom_summary"))) or case_id
    symptom = _truncate_at_sentence(
        scrubber.clean(_text(value("symptom_summary"))) or "", SYMPTOM_LIMIT
    )
    components = [
        scrubber.clean(_text(item))
        for item in _as_list(value("latency_components"))
        if _text(item)
    ]
    keywords = [
        scrubber.clean(_text(item))
        for item in _as_list(value("log_keywords"))
        if _text(item)
    ]
    operation = _text(value("operation"))
    fault_shape = scrubber.clean(_text(value("fault_shape")))
    text = _limit_text(
        [title, symptom],
        [operation, fault_shape, *components, *keywords],
    )
    if not text:
        raise PhenomenonContentError("empty_text", f"case {case_id} has no text")

    verification_json = value("verification_json") or {}
    closed_loop = bool(
        verification_json.get("closed_loop")
        if isinstance(verification_json, dict)
        else getattr(verification_json, "closed_loop", False)
    )
    source_fault_hash = _text(value("source_fault_hash"))
    return PhenomenonDoc(
        doc_id=f"case:{case_id}",
        kind=PhenomenonKind.CASE.value,
        content_source=PhenomenonContentSource.CASE.value,
        title=title,
        symptom=symptom,
        text=text,
        content_hash=sha256_hex(text),
        verification=(
            VerificationLevel.VERIFIED.value
            if closed_loop
            else VerificationLevel.CONFIRMED_UNVERIFIED.value
        ),
        fault_type=_text(value("fault_type")) or "unknown",
        root_cause_summary=_safe_clean(scrubber, _text(value("root_cause_summary"))),
        case_id=case_id,
        case_no=_text(value("case_no")),
        source_fault_hash=source_fault_hash,
        log_type=_text(value("log_type")),
        operation=operation,
        status_codes=[str(item) for item in _as_list(value("status_codes"))],
        failure_mode_ids=[str(item) for item in _as_list(value("failure_mode_ids"))],
        binding_status=BindingStatus.NONE.value,
    )


def is_readable_legacy_description(description: Any) -> bool:
    text = _text(description)
    if not text:
        return False
    return not AUTO_IMPORT_PLACEHOLDER_RE.match(text)


def extract_legacy_doc(case: dict) -> PhenomenonDoc | None:
    """Thin card for an old file case; None when the description is unusable."""
    description = _text(case.get("description"))
    if not is_readable_legacy_description(description):
        return None

    legacy_id = _text(case.get("id"))
    if not legacy_id:
        return None

    scrubber = IdentityScrubber.from_payload(
        {
            "task_names": case.get("task_names"),
            "log_file_name": case.get("log_file_name"),
        }
    )
    title = _truncate_at_sentence(
        scrubber.clean(description) or legacy_id, SYMPTOM_LIMIT
    )
    category = scrubber.clean(_text(case.get("case_category")))
    root_cause_type = scrubber.clean(_text(case.get("root_cause_type")))
    text = _limit_text([title], [category, root_cause_type])
    if not text:
        return None

    features = _as_dict(case.get("features"))
    fault_category = _text(features.get("fault_category") or case.get("fault_category"))
    fault_type = {
        "latency": "latency",
        "error": "connectivity",
        "connectivity": "connectivity",
        "mixed": "mixed",
    }.get((fault_category or "").lower(), "unknown")
    return PhenomenonDoc(
        doc_id=f"legacy:{legacy_id}",
        kind=PhenomenonKind.LEGACY_CASE.value,
        content_source=PhenomenonContentSource.LEGACY_CASE.value,
        title=title,
        symptom=title,
        text=text,
        content_hash=sha256_hex(text),
        verification=(
            VerificationLevel.TASK_OBSERVED.value
            if case.get("log_file_id") or case.get("task_ids")
            else VerificationLevel.LEGACY_UNVERIFIED.value
        ),
        fault_type=fault_type,
        legacy_case_id=legacy_id,
    )


def verification_from_case(case: Any) -> str:
    """Derive the trust label from a case's own closure state."""
    verification_json = (
        getattr(case, "verification_json", None)
        if not isinstance(case, dict)
        else case.get("verification_json")
    )
    closed_loop = bool(
        verification_json.get("closed_loop")
        if isinstance(verification_json, dict)
        else getattr(verification_json, "closed_loop", False)
    )
    return (
        VerificationLevel.VERIFIED.value
        if closed_loop
        else VerificationLevel.CONFIRMED_UNVERIFIED.value
    )
