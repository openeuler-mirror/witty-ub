# Copyright (c) Huawei Technologies Co., Ltd. 2023-2026. All rights reserved.
"""Read-only MCP tools for latency and connectivity fault investigation."""

from __future__ import annotations

import os
from typing import Any, Literal
from urllib.parse import quote

from mcp.server.fastmcp import FastMCP
from mcp.types import ToolAnnotations

from latency.access.latency_api_client import LatencyApiClient


mcp = FastMCP(
    "witty-ub-latency",
    instructions=(
        "Use these read-only tools to investigate parsed latency and connectivity "
        "fault data. Confirm that parsing completed before concluding that no fault "
        "exists. Empty query results are not proof that the system is healthy."
    ),
)

READ_ONLY_TOOL = ToolAnnotations(
    readOnlyHint=True,
    destructiveHint=False,
    idempotentHint=True,
    openWorldHint=True,
)


def _client() -> LatencyApiClient:
    return LatencyApiClient()


def _page(page_num: int, page_cnt: int) -> dict[str, int]:
    if page_num < 1:
        raise ValueError("page_num must be at least 1")
    if not 1 <= page_cnt <= 100:
        raise ValueError("page_cnt must be between 1 and 100")
    return {"page_num": page_num, "page_cnt": page_cnt}


def _without_none(payload: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in payload.items() if value is not None}


def _sort_fields(
    sort_fields: list[dict[str, str]] | None,
) -> list[dict[str, str]] | None:
    """Validate the common multi-column sort shape accepted by the APIs."""
    if sort_fields is None:
        return None
    validated: list[dict[str, str]] = []
    for item in sort_fields:
        field = item.get("field", "").strip()
        order = item.get("order", "desc").lower()
        if not field:
            raise ValueError("each sort field must have a non-empty field")
        if order not in {"asc", "desc"}:
            raise ValueError("sort field order must be asc or desc")
        validated.append({"field": field, "order": order})
    return validated


# API: POST /log_kb/list
@mcp.tool(
    annotations=READ_ONLY_TOOL,
    description=(
        "List log knowledge bases. Use this first to discover available knowledge "
        "base IDs. Returns knowledge base metadata including ID, name, description "
        "and creation time. Results are paginated."
    )
)
async def list_log_kbs(
    name: str | None = None,
    description: str | None = None,
    created_at_start: str | None = None,
    created_at_end: str | None = None,
    created_sorted_desc: bool = True,
    page_num: int = 1,
    page_cnt: int = 20,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "name": name,
        "description": description,
        "created_at_start": created_at_start,
        "created_at_end": created_at_end,
        "created_sorted_desc": created_sorted_desc,
        **_page(page_num, page_cnt),
    }
    return await _client().post("/log_kb/list", json=_without_none(payload))


# API: GET /log_kb/{kb_id}
@mcp.tool(
    annotations=READ_ONLY_TOOL,
    description=(
        "Get one log knowledge base by its ID. Returns full knowledge base metadata "
        "including name, description and creation time."
    )
)
async def get_log_kb(kb_id: str) -> dict[str, Any]:
    return await _client().get(f"/log_kb/{quote(kb_id, safe='')}")


# API: POST /log_file/list/{kb_id}
@mcp.tool(
    annotations=READ_ONLY_TOOL,
    description=(
        "List log files in an asset knowledge base. Use this first to discover log "
        "IDs, parse status, task IDs and available fault counts. A non-successful "
        "parse status means downstream results may be incomplete."
    )
)
async def list_log_files(
    kb_id: str,
    parse_status: str | None = None,
    page_num: int = 1,
    page_cnt: int = 20,
) -> dict[str, Any]:
    payload = _page(page_num, page_cnt)
    payload["parse_status"] = parse_status
    return await _client().post(
        f"/log_file/list/{quote(kb_id, safe='')}",
        json=_without_none(payload),
    )


# API: GET /task/{task_id}
@mcp.tool(
    annotations=READ_ONLY_TOOL,
    description=(
        "Get one parsing task and its progress, reports and completion status. Call "
        "this before treating empty analysis results as evidence that no fault exists."
    )
)
async def get_parse_task(task_id: str) -> dict[str, Any]:
    return await _client().get(f"/task/{quote(task_id, safe='')}")


# API: POST /aggregated_event/list
@mcp.tool(
    annotations=READ_ONLY_TOOL,
    description=(
        "List source/destination IP latency aggregates. Use this to find IP pairs "
        "with high latency or anomalous requests before drilling into log records. "
        "Supports GET/SET, log-event time, topology and multi-column sort filters."
    )
)
async def list_latency_events(
    kb_id: str,
    log_id: str | None = None,
    start_time: str | None = None,
    end_time: str | None = None,
    cluster_name: str | None = None,
    host: str | None = None,
    pod_ip: str | None = None,
    src_ip: str | None = None,
    dst_ip: str | None = None,
    operation: Literal["GET", "SET"] | None = None,
    stat_type: Literal["p99", "p95", "ave", "min", "max"] = "p99",
    sort_fields: list[dict[str, str]] | None = None,
    page_num: int = 1,
    page_cnt: int = 20,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "kb_id": kb_id,
        "log_id": log_id,
        "start_time": start_time,
        "end_time": end_time,
        "cluster_name": cluster_name,
        "host": host,
        "pod_ip": pod_ip,
        "src_ip": src_ip,
        "dst_ip": dst_ip,
        "operation": operation,
        "stat_type": stat_type,
        "sort_fields": _sort_fields(sort_fields)
        or [{"field": "total_latency", "order": "desc"}],
        **_page(page_num, page_cnt),
    }
    return await _client().post(
        "/aggregated_event/list", json=_without_none(payload)
    )


# API: POST /aggregated_event/list_time_window
@mcp.tool(
    annotations=READ_ONLY_TOOL,
    description=(
        "List latency aggregates grouped into time windows. Use this to identify "
        "when latency increased and compare source/destination IP pairs within the "
        "same interval."
    )
)
async def list_latency_time_windows(
    kb_id: str,
    start_time: str | None = None,
    end_time: str | None = None,
    cluster_name: str | None = None,
    host: str | None = None,
    pod_ip: str | None = None,
    src_ip: str | None = None,
    dst_ip: str | None = None,
    operation: Literal["GET", "SET"] | None = None,
    interval: Literal["second", "minute", "hour"] = "minute",
    stat_type: Literal["p99", "p95", "ave", "min", "max"] = "p99",
    sort_by: Literal["start_time", "total_latency"] = "start_time",
    sort_order: Literal["asc", "desc"] = "asc",
    sort_fields: list[dict[str, str]] | None = None,
    page_num: int = 1,
    page_cnt: int = 20,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "kb_id": kb_id,
        "start_time": start_time,
        "end_time": end_time,
        "cluster_name": cluster_name,
        "host": host,
        "pod_ip": pod_ip,
        "src_ip": src_ip,
        "dst_ip": dst_ip,
        "operation": operation,
        "interval": interval,
        "stat_type": stat_type,
        "sort_by": sort_by,
        "sort_order": sort_order,
        "sort_fields": _sort_fields(sort_fields),
        **_page(page_num, page_cnt),
    }
    return await _client().post(
        "/aggregated_event/list_time_window",
        json=_without_none(payload),
    )


# API: GET /log_parse_result/options
@mcp.tool(
    annotations=READ_ONLY_TOOL,
    description=(
        "Get available cluster and host filter values from parsed logs. Optionally "
        "limit the options to one knowledge base."
    )
)
async def get_log_parse_options(kb_id: str | None = None) -> dict[str, Any]:
    path = "/log_parse_result/options"
    if kb_id is not None:
        path = f"{path}?kb_id={quote(kb_id, safe='')}"
    return await _client().get(path)


# API: POST /log_parse_result/list
@mcp.tool(
    annotations=READ_ONLY_TOOL,
    description=(
        "List parsed log or trace records for a latency investigation. Filter by an "
        "aggregate event, one or more traces, operation, host or IP pair. Results "
        "contain the detailed latency components and anomaly markers used as "
        "diagnosis evidence. Defaults prioritize anomalous records but can be "
        "overridden for comparison with normal samples."
    )
)
async def list_log_parse_results(
    kb_id: str,
    log_id: str | None = None,
    aggregated_event_id: str | None = None,
    trace_id: str | None = None,
    trace_ids: list[str] | None = None,
    cluster_name: str | None = None,
    host: str | None = None,
    pod_ip: str | None = None,
    src_ip: str | None = None,
    dst_ip: str | None = None,
    start_time: str | None = None,
    end_time: str | None = None,
    created_at_start: str | None = None,
    created_at_end: str | None = None,
    operation: Literal["GET", "SET"] | None = None,
    is_anomalous: bool | None = True,
    sort_fields: list[dict[str, str]] | None = None,
    page_num: int = 1,
    page_cnt: int = 20,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "kb_id": kb_id,
        "log_id": log_id,
        "aggregated_event_id": aggregated_event_id,
        "trace_id": trace_id,
        "trace_ids": trace_ids,
        "cluster_name": cluster_name,
        "host": host,
        "pod_ip": pod_ip,
        "src_ip": src_ip,
        "dst_ip": dst_ip,
        "start_time": start_time,
        "end_time": end_time,
        "created_at_start": created_at_start,
        "created_at_end": created_at_end,
        "operation": operation,
        "is_anomalous": is_anomalous,
        "sort_fields": _sort_fields(sort_fields),
        **_page(page_num, page_cnt),
    }
    return await _client().post(
        "/log_parse_result/list", json=_without_none(payload)
    )


# API: POST /log_parse_result/metrics/latency
@mcp.tool(
    annotations=READ_ONLY_TOOL,
    description=(
        "Get latency metric time series for a knowledge base, host or IP pair. Use "
        "P99 for fault spikes and AVG for general trends. The response includes "
        "sampling metadata, so sampled data must not be described as raw full data."
    )
)
async def get_latency_metrics(
    kb_id: str,
    start_time: str | None = None,
    end_time: str | None = None,
    cluster_name: str | None = None,
    pod_ip: str | None = None,
    host: str | None = None,
    src_ip: str | None = None,
    dst_ip: str | None = None,
    operation: Literal["GET", "SET"] | None = None,
    sample_mode: Literal["none", "max", "avg", "min", "p99", "p95", "p9999"] = "p99",
    max_points: int = 1000,
) -> dict[str, Any]:
    if max_points != -1 and not 1 <= max_points <= 5000:
        raise ValueError("max_points must be -1 or between 1 and 5000")
    payload = _without_none(
        {
            "kb_id": kb_id,
            "start_time": start_time,
            "end_time": end_time,
            "cluster_name": cluster_name,
            "pod_ip": pod_ip,
            "host": host,
            "src_ip": src_ip,
            "dst_ip": dst_ip,
            "operation": operation,
            "sample_mode": sample_mode,
            "max_points": max_points,
            "sort_by": "timestamp",
            "sort_order": "asc",
        }
    )
    return await _client().post("/log_parse_result/metrics/latency", json=payload)


# API: POST /log_failure_event_result/list_time_aggregated_failure_events
@mcp.tool(
    annotations=READ_ONLY_TOOL,
    description=(
        "Aggregate connectivity fault codes by time window. Use this as the first "
        "connectivity-fault query to locate periods with concentrated failures."
    )
)
async def list_failure_time_windows(
    kb_id: str,
    start_time: str | None = None,
    end_time: str | None = None,
    cluster_name: str | None = None,
    host: str | None = None,
    pod_ip: str | None = None,
    src_ip: str | None = None,
    dst_ip: str | None = None,
    interval: Literal["second", "minute", "hour"] = "minute",
    sort_desc: bool = False,
    sort_fields: list[dict[str, str]] | None = None,
    page_num: int = 1,
    page_cnt: int = 20,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "kb_id": kb_id,
        "start_time": start_time,
        "end_time": end_time,
        "cluster_name": cluster_name,
        "host": host,
        "pod_ip": pod_ip,
        "src_ip": src_ip,
        "dst_ip": dst_ip,
        "interval": interval,
        "sort_by": "timestamp",
        "sort_desc": sort_desc,
        "sort_fields": _sort_fields(sort_fields),
        **_page(page_num, page_cnt),
    }
    return await _client().post(
        "/log_failure_event_result/list_time_aggregated_failure_events",
        json=_without_none(payload),
    )


# API: POST /log_failure_event_result/list_pod_aggregated_failure_events
@mcp.tool(
    annotations=READ_ONLY_TOOL,
    description=(
        "Aggregate connectivity fault codes by pod within a time range. Use this "
        "after locating a failure window to identify the pods contributing faults."
    )
)
async def list_failure_pod_aggregates(
    kb_id: str,
    start_time: str | None = None,
    end_time: str | None = None,
    sort_by: str = "all",
    sort_order: Literal["asc", "desc"] = "desc",
    sort_fields: list[dict[str, str]] | None = None,
    page_num: int = 1,
    page_cnt: int = 20,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "kb_id": kb_id,
        "start_time": start_time,
        "end_time": end_time,
        "sort_by": sort_by,
        "sort_desc": sort_order == "desc",
        "sort_fields": _sort_fields(sort_fields),
        **_page(page_num, page_cnt),
    }
    return await _client().post(
        "/log_failure_event_result/list_pod_aggregated_failure_events",
        json=_without_none(payload),
    )


# API: POST /log_failure_event_result/list_src_dst_aggregated_failure_events
@mcp.tool(
    annotations=READ_ONLY_TOOL,
    description=(
        "Aggregate connectivity fault codes by source/destination IP pair. Use "
        "this after locating a failure window to identify the affected path before "
        "drilling into traces."
    )
)
async def list_failure_src_dst_aggregates(
    kb_id: str,
    start_time: str | None = None,
    end_time: str | None = None,
    cluster_name: str | None = None,
    host: str | None = None,
    pod_ip: str | None = None,
    src_ip: str | None = None,
    dst_ip: str | None = None,
    sort_by: str = "all",
    sort_order: Literal["asc", "desc"] = "desc",
    sort_fields: list[dict[str, str]] | None = None,
    page_num: int = 1,
    page_cnt: int = 20,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "kb_id": kb_id,
        "start_time": start_time,
        "end_time": end_time,
        "cluster_name": cluster_name,
        "host": host,
        "pod_ip": pod_ip,
        "src_ip": src_ip,
        "dst_ip": dst_ip,
        "sort_by": sort_by,
        "sort_desc": sort_order == "desc",
        "sort_fields": _sort_fields(sort_fields),
        **_page(page_num, page_cnt),
    }
    return await _client().post(
        "/log_failure_event_result/list_src_dst_aggregated_failure_events",
        json=_without_none(payload),
    )


# API: POST /log_failure_event_result/metrics/err_code
@mcp.tool(
    annotations=READ_ONLY_TOOL,
    description=(
        "Get connectivity error-code metric time series for a knowledge base. "
        "Filter by error code, cluster, host, pod or time range to quantify fault "
        "frequency and correlate spikes."
    )
)
async def get_error_code_metrics(
    kb_id: str,
    src_ip: str | None = None,
    dst_ip: str | None = None,
    err_codes: list[str] | None = None,
    cluster_names: list[str] | None = None,
    host_names: list[str] | None = None,
    pod_names: list[str] | None = None,
    start_time: str | None = None,
    end_time: str | None = None,
    max_points: int = 1000,
) -> dict[str, Any]:
    if not 1 <= max_points <= 5000:
        raise ValueError("max_points must be between 1 and 5000")
    payload = _without_none(
        {
            "kb_id": kb_id,
            "src_ip": src_ip,
            "dst_ip": dst_ip,
            "err_codes": err_codes or [],
            "cluster_names": cluster_names or [],
            "host_names": host_names or [],
            "pod_names": pod_names or [],
            "start_time": start_time,
            "end_time": end_time,
            "max_points": max_points,
        }
    )
    return await _client().post(
        "/log_failure_event_result/metrics/err_code",
        json=payload,
    )


# API: POST /log_failure_event_result/list_trace_events
@mcp.tool(
    annotations=READ_ONLY_TOOL,
    description=(
        "List connectivity fault traces filtered by knowledge base, fault code, "
        "cluster, host, pod, IP pair, trace ID or time. Use returned trace IDs and "
        "failure-mode IDs to retrieve raw logs and knowledge evidence."
    )
)
async def list_failure_traces(
    kb_id: str,
    trace_ids: list[str] | None = None,
    status_codes: list[str] | None = None,
    cluster_names: list[str] | None = None,
    host_names: list[str] | None = None,
    pod_names: list[str] | None = None,
    src_ip: str | None = None,
    dst_ip: str | None = None,
    start_time: str | None = None,
    end_time: str | None = None,
    is_anomalous: bool | None = True,
    page_num: int = 1,
    page_cnt: int = 20,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "kb_id": kb_id,
        "trace_ids": trace_ids,
        "status_codes": status_codes or [],
        "cluster_names": cluster_names or [],
        "host_names": host_names or [],
        "pod_names": pod_names or [],
        "src_ip": src_ip,
        "dst_ip": dst_ip,
        "start_time": start_time,
        "end_time": end_time,
        "is_anomalous": is_anomalous,
        "sort_desc": True,
        **_page(page_num, page_cnt),
    }
    return await _client().post(
        "/log_failure_event_result/list_trace_events",
        json=_without_none(payload),
    )


# API: POST /log_failure_event_result/list_log_events
@mcp.tool(
    annotations=READ_ONLY_TOOL,
    description=(
        "Get raw fault log events for one or more trace IDs. These records are "
        "primary evidence; quote only the relevant fields and do not infer a root "
        "cause solely from a coincident log message."
    )
)
async def list_failure_logs(
    trace_ids: list[str],
    kb_id: str | None = None,
    log_id: str | None = None,
) -> dict[str, Any]:
    if not trace_ids:
        raise ValueError("trace_ids must contain at least one trace ID")
    if len(trace_ids) > 100:
        raise ValueError("trace_ids cannot contain more than 100 items")
    return await _client().post(
        "/log_failure_event_result/list_log_events",
        json=_without_none(
            {"kb_id": kb_id, "log_id": log_id, "trace_ids": trace_ids}
        ),
    )


# API: GET /failure_mode/status_code/{status_code}
@mcp.tool(
    annotations=READ_ONLY_TOOL,
    description=(
        "Explain a connectivity status code using the curated fault knowledge base. "
        "Returns the known symptom and root cause. A 404 means the code is unknown, "
        "not that the event is healthy."
    )
)
async def get_status_code_knowledge(status_code: str) -> dict[str, Any]:
    return await _client().get(
        f"/failure_mode/status_code/{quote(status_code, safe='')}"
    )


# API: GET /failure_mode/{failure_mode_id}
@mcp.tool(
    annotations=READ_ONLY_TOOL,
    description=(
        "Get a complete curated failure mode by ID, including symptom, root cause, "
        "solution, failure domain and child failure-mode relationships."
    )
)
async def get_failure_mode(failure_mode_id: str) -> dict[str, Any]:
    return await _client().get(
        f"/failure_mode/{quote(failure_mode_id, safe='')}"
    )


# API: POST /diagnosis_case/search
@mcp.tool(
    annotations=READ_ONLY_TOOL,
    description=(
        "Search persisted historical diagnosis cases before or during a fault "
        "investigation. Match by structured signals such as status codes, failure "
        "mode IDs, IPs, hosts, pods, clusters, abnormal latency components and key "
        "log phrases. A match is a hypothesis to verify against current evidence, "
        "not proof that the current fault has the same cause."
    )
)
async def search_diagnosis_cases(
    kb_id: str | None = None,
    fault_type: Literal["latency", "connectivity", "mixed", "unknown"] | None = None,
    status_codes: list[str] | None = None,
    failure_mode_ids: list[str] | None = None,
    src_ips: list[str] | None = None,
    dst_ips: list[str] | None = None,
    hosts: list[str] | None = None,
    pods: list[str] | None = None,
    clusters: list[str] | None = None,
    latency_components: list[str] | None = None,
    log_keywords: list[str] | None = None,
    min_confidence: float | None = None,
    page_num: int = 1,
    page_cnt: int = 10,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "kb_id": kb_id,
        "fault_type": fault_type,
        "status_codes": status_codes or [],
        "failure_mode_ids": failure_mode_ids or [],
        "src_ips": src_ips or [],
        "dst_ips": dst_ips or [],
        "hosts": hosts or [],
        "pods": pods or [],
        "clusters": clusters or [],
        "latency_components": latency_components or [],
        "log_keywords": log_keywords or [],
        "min_confidence": min_confidence,
        **_page(page_num, page_cnt),
    }
    return await _client().post(
        "/diagnosis_case/search", json=_without_none(payload)
    )


# API: GET /diagnosis_case/{case_id}
@mcp.tool(
    annotations=READ_ONLY_TOOL,
    description=(
        "Get one persisted historical diagnosis case by ID. Use it to inspect the "
        "stored symptom, root cause, recommendation, fingerprint and evidence "
        "references after search_diagnosis_cases returns a candidate."
    )
)
async def get_diagnosis_case(case_id: str) -> dict[str, Any]:
    return await _client().get(f"/diagnosis_case/{quote(case_id, safe='')}")


_MAX_READ_BYTES = 5 * 1024 * 1024


@mcp.tool(
    annotations=READ_ONLY_TOOL,
    description=(
        "Read the contents of a file from the local filesystem. Use this to inspect "
        "raw log files, configuration files or other text artifacts referenced during "
        "investigation. Files larger than 5 MB are rejected."
    )
)
async def read_file(file_path: str) -> dict[str, Any]:
    if not os.path.isfile(file_path):
        raise FileNotFoundError(f"File not found: {file_path}")
    size = os.path.getsize(file_path)
    if size > _MAX_READ_BYTES:
        raise ValueError(
            f"File too large ({size} bytes): exceeds {_MAX_READ_BYTES} byte limit"
        )
    with open(file_path, "r", encoding="utf-8", errors="replace") as fh:
        content = fh.read()
    return {"file_path": file_path, "size_bytes": size, "content": content}


class MCPServer:
    """MCP server entry point kept for compatibility with existing launchers."""

    @staticmethod
    def start() -> None:
        transport = os.getenv("LATENCY_MCP_TRANSPORT", "stdio")
        if transport not in {"stdio", "sse", "streamable-http"}:
            raise ValueError(
                "LATENCY_MCP_TRANSPORT must be stdio, sse or streamable-http"
            )
        mcp.run(transport=transport)


if __name__ == "__main__":
    MCPServer.start()
