# Copyright (c) Huawei Technologies Co., Ltd. 2023-2026. All rights reserved.
"""Agent-specific input rules layered on top of the backend OpenAPI contract."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping


class McpContractError(RuntimeError):
    """Raised when Agent-specific rules do not match the OpenAPI operations."""


@dataclass(frozen=True)
class McpInputPolicy:
    """MCP-only requirements, defaults and JSON Schema refinements."""

    required: frozenset[str] = frozenset()
    defaults: Mapping[str, Any] = field(default_factory=dict)
    default_if_empty: frozenset[str] = frozenset()
    property_overrides: Mapping[str, Mapping[str, Any]] = field(
        default_factory=dict
    )


PAGINATION_PROPERTY_OVERRIDES: Mapping[str, Mapping[str, Any]] = {
    "page_num": {"minimum": 1},
    "page_cnt": {"minimum": 1, "maximum": 100},
}

COMMON_DEFINITION_OVERRIDES: Mapping[str, Mapping[str, Any]] = {
    "SortField": {
        "properties": {
            "field": {"minLength": 1},
            "order": {"enum": ["asc", "desc"]},
        }
    }
}

_OPERATION = {"enum": ["GET", "SET"]}
_STAT_TYPE = {"enum": ["p99", "p95", "ave", "min", "max"]}
_INTERVAL = {"enum": ["second", "minute", "hour"]}

MCP_INPUT_POLICIES: Mapping[str, McpInputPolicy] = {
    "list_latency_events": McpInputPolicy(
        required=frozenset({"kb_id"}),
        defaults={
            "stat_type": "p99",
            "sort_fields": [{"field": "total_latency", "order": "desc"}],
        },
        default_if_empty=frozenset({"sort_fields"}),
        property_overrides={
            "operation": _OPERATION,
            "stat_type": _STAT_TYPE,
        },
    ),
    "list_latency_events_by_time_windows": McpInputPolicy(
        required=frozenset({"kb_id"}),
        defaults={"stat_type": "p99"},
        property_overrides={
            "operation": _OPERATION,
            "stat_type": _STAT_TYPE,
            "interval": _INTERVAL,
            "sort_by": {"enum": ["start_time", "total_latency"]},
            "sort_order": {"enum": ["asc", "desc"]},
        },
    ),
    "list_latency_traces": McpInputPolicy(
        required=frozenset({"kb_id"}),
        defaults={"is_anomalous": True},
        property_overrides={"operation": _OPERATION},
    ),
    "get_latency_metrics": McpInputPolicy(
        required=frozenset({"kb_id"}),
        property_overrides={
            "operation": _OPERATION,
            "max_points": {
                "anyOf": [
                    {"const": -1},
                    {"type": "integer", "minimum": 1, "maximum": 5000},
                ]
            },
        },
    ),
    "list_connectivity_events_by_time_windows": McpInputPolicy(
        required=frozenset({"kb_id"}),
        property_overrides={"interval": _INTERVAL},
    ),
    "list_connectivity_events_by_pods": McpInputPolicy(
        required=frozenset({"kb_id"}),
    ),
    "list_connectivity_events": McpInputPolicy(
        required=frozenset({"kb_id"}),
    ),
    "list_connectivity_traces": McpInputPolicy(
        defaults={"is_anomalous": True},
    ),
    "get_connectivity_metrics": McpInputPolicy(
        property_overrides={
            "max_points": {"minimum": 1, "maximum": 5000},
        },
    ),
    "list_connectivity_trace_logs": McpInputPolicy(
        required=frozenset({"trace_ids"}),
        property_overrides={
            "trace_ids": {"minItems": 1, "maxItems": 100},
        },
    ),
    "list_diagnosis_cases": McpInputPolicy(
        property_overrides={
            "fault_type": {
                "enum": ["latency", "connectivity", "mixed", "unknown"]
            },
        },
    ),
}

MCP_TOOL_DESCRIPTIONS: Mapping[str, str] = {
    "list_log_knowledge_bases": (
        "List log knowledge bases. Use this first to discover available knowledge "
        "base IDs. Returns metadata including ID, name, description and creation "
        "time. Results are paginated."
    ),
    "get_log_knowledge_base": (
        "Get one log knowledge base by ID. Use it to verify the selected data set "
        "before investigating its logs."
    ),
    "list_log_files": (
        "List log files in a knowledge base. Use this to discover log IDs, parse "
        "status, task IDs and fault counts. A non-successful parse status means "
        "downstream results may be incomplete."
    ),
    "get_log_file": (
        "Get one log file by ID, including its knowledge base, source, parse "
        "status, task information and fault statistics."
    ),
    "list_parse_tasks": (
        "List parsing tasks by knowledge base, status, type or creation time. Use "
        "this to inspect parsing progress when a log file has no direct task ID."
    ),
    "get_parse_task": (
        "Get one parsing task and its progress, reports and completion status. "
        "Call this before treating empty analysis results as evidence that no "
        "fault exists."
    ),
    "list_latency_events": (
        "List source/destination IP latency aggregates. Use this to find IP pairs "
        "with high latency or anomalous requests before drilling into traces. "
        "Supports operation, log-event time, topology and multi-column filters."
    ),
    "get_latency_event": (
        "Get one source/destination latency aggregate by ID. Use it to inspect the "
        "selected path and aggregate latency components before trace drill-down."
    ),
    "list_latency_events_by_time_windows": (
        "List latency aggregates grouped into time windows. Use this to identify "
        "when latency increased and compare source/destination IP pairs within the "
        "same interval."
    ),
    "list_clusters_hosts": (
        "List cluster and host filter values that actually exist in parsed logs. "
        "Use this before filtering by cluster or host instead of guessing names."
    ),
    "list_latency_traces": (
        "List parsed latency traces. Filter by aggregate event, trace ID, operation, "
        "host, pod or IP pair. Results contain detailed latency components and "
        "anomaly markers used as diagnosis evidence."
    ),
    "get_latency_trace": (
        "Get one parsed latency trace by result ID, including detailed latency "
        "components, topology fields, trace ID and anomaly markers."
    ),
    "get_latency_metrics": (
        "Get latency metric time series for a knowledge base, host or IP pair. Use "
        "P99 for fault spikes and AVG for general trends. Respect the returned "
        "sampling metadata and do not describe sampled points as full raw data."
    ),
    "list_connectivity_events_by_time_windows": (
        "Aggregate connectivity fault codes by time window. Use this first to "
        "locate periods with concentrated connectivity failures."
    ),
    "list_connectivity_events_by_pods": (
        "Aggregate connectivity fault codes by pod within a time range. Use this "
        "only when the investigation needs to identify pods contributing faults."
    ),
    "list_connectivity_events": (
        "Aggregate connectivity fault codes by source/destination IP pair. Use "
        "this after locating a failure window to identify affected paths before "
        "drilling into traces."
    ),
    "get_connectivity_metrics": (
        "Get connectivity error-code time series for a knowledge base. Filter by "
        "error code, cluster, host, pod, IP pair or time range to quantify fault "
        "frequency and correlate spikes."
    ),
    "list_connectivity_traces": (
        "List connectivity fault traces by knowledge base, fault code, topology, "
        "IP pair, trace ID or time. Use returned trace IDs and failure-mode IDs to "
        "retrieve raw logs and knowledge evidence."
    ),
    "list_connectivity_trace_logs": (
        "Get raw connectivity fault log events for one or more trace IDs. These "
        "records are primary evidence; quote only relevant fields and do not infer "
        "a root cause solely from coincident log messages."
    ),
    "get_status_code_knowledge": (
        "Explain a connectivity status code using the curated fault knowledge "
        "base. A not-found response means the code is unknown, not that the event "
        "is healthy."
    ),
    "get_failure_mode": (
        "Get a complete curated failure mode by ID, including symptom, root cause, "
        "solution, failure domain and child failure-mode relationships."
    ),
    "list_diagnosis_cases": (
        "Search historical diagnosis cases using current signals such as status "
        "codes, failure modes, IPs, hosts, pods, clusters, latency components and "
        "log phrases. A match is a hypothesis to verify, not proof."
    ),
    "get_diagnosis_case": (
        "Get one historical diagnosis case by ID. Inspect its symptom, root cause, "
        "recommendation, fingerprint and evidence references after case search."
    ),
}


def get_mcp_input_policy(operation_id: str) -> McpInputPolicy:
    """Return an operation policy, or an empty policy when none is needed."""
    return MCP_INPUT_POLICIES.get(operation_id, McpInputPolicy())


def get_mcp_tool_description(
    operation_id: str,
    fallback: str,
) -> str:
    """Return the Agent-oriented description for a dynamic MCP tool."""
    return MCP_TOOL_DESCRIPTIONS.get(operation_id, fallback)


def verify_mcp_input_policy_operations(operation_ids: set[str]) -> None:
    """Fail when an Agent policy references an unavailable operation ID."""
    missing = sorted(MCP_INPUT_POLICIES.keys() - operation_ids)
    if missing:
        raise McpContractError(
            "Agent input policies reference unavailable operations: "
            + ", ".join(missing)
        )


def verify_mcp_tool_description_operations(operation_ids: set[str]) -> None:
    """Fail when descriptions are missing or reference unavailable operations."""
    stale = sorted(MCP_TOOL_DESCRIPTIONS.keys() - operation_ids)
    missing = sorted(operation_ids - MCP_TOOL_DESCRIPTIONS.keys())
    messages = []
    if stale:
        messages.append(
            "descriptions for unavailable operations: " + ", ".join(stale)
        )
    if missing:
        messages.append(
            "operations without Agent descriptions: " + ", ".join(missing)
        )
    if messages:
        raise McpContractError(
            "Agent tool description contract mismatch: " + "; ".join(messages)
        )
