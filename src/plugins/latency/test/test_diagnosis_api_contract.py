"""Contract tests for the read-only HTTP APIs used by the diagnosis agent."""

from collections import Counter
from typing import Any

from fastapi import FastAPI

from latency.routers import (
    diagnosis_case,
    failure_mode_knowledge,
    log_failure_event_result,
    log_file,
    log_knowledge,
    log_parse_result,
    src_dst_aggregated_event,
    task,
)
from latency.schemas.request import (
    ListLogParseResultRequest,
    ListSrcDstAggregatedEventRequest,
    ListTraceFailureEventResultRequest,
)


EXPECTED_DIAGNOSIS_OPERATIONS = {
    "list_log_knowledge_bases": ("POST", "/log_kb/list"),
    "get_diagnosis_case": ("GET", "/diagnosis_case/{case_id}"),
    "get_failure_mode": ("GET", "/failure_mode/{failure_mode_id}"),
    "get_log_file": ("GET", "/log_file/{log_file_id}"),
    "get_log_knowledge_base": ("GET", "/log_kb/{kb_id}"),
    "get_latency_event": ("GET", "/aggregated_event/{event_id}"),
    "get_latency_metrics": ("POST", "/log_parse_result/metrics/latency"),
    "get_latency_trace": ("GET", "/log_parse_result/{result_id}"),
    "get_parse_task": ("GET", "/task/{task_id}"),
    "get_status_code_knowledge": ("GET", "/failure_mode/status_code/{status_code}"),
    "list_log_files": ("POST", "/log_file/list/{kb_id}"),
    "list_parse_tasks": ("POST", "/task/list"),
    "get_connectivity_metrics": ("POST", "/log_failure_event_result/metrics/err_code"),
    "list_clusters_hosts": ("GET", "/log_parse_result/options"),
    "list_connectivity_events": (
        "POST",
        "/log_failure_event_result/list_src_dst_aggregated_failure_events",
    ),
    "list_connectivity_events_by_pods": (
        "POST",
        "/log_failure_event_result/list_pod_aggregated_failure_events",
    ),
    "list_connectivity_events_by_time_windows": (
        "POST",
        "/log_failure_event_result/list_time_aggregated_failure_events",
    ),
    "list_connectivity_trace_logs": (
        "POST",
        "/log_failure_event_result/list_log_events",
    ),
    "list_connectivity_traces": (
        "POST",
        "/log_failure_event_result/list_trace_events",
    ),
    "list_diagnosis_cases": ("POST", "/diagnosis_case/search"),
    "list_latency_events": ("POST", "/aggregated_event/list"),
    "list_latency_events_by_time_windows": (
        "POST",
        "/aggregated_event/list_time_window",
    ),
    "list_latency_traces": ("POST", "/log_parse_result/list"),
}


def _openapi_schema() -> dict[str, Any]:
    app = FastAPI()
    for api_router in (
        log_file.router,
        log_knowledge.router,
        log_parse_result.router,
        src_dst_aggregated_event.router,
        task.router,
        failure_mode_knowledge.router,
        log_failure_event_result.router,
        diagnosis_case.router,
    ):
        app.include_router(api_router)
    return app.openapi()


def test_agent_diagnosis_api_operations_are_stable_and_unique() -> None:
    operations: dict[str, tuple[str, str]] = {}
    operation_ids: list[str] = []

    for path, path_item in _openapi_schema()["paths"].items():
        for method, operation in path_item.items():
            if not isinstance(operation, dict):
                continue
            operation_id = operation.get("operationId")
            if operation_id not in EXPECTED_DIAGNOSIS_OPERATIONS:
                continue
            operation_ids.append(operation_id)
            operations[operation_id] = (method.upper(), path)
            assert operation.get("description")

    counts = Counter(operation_ids)
    assert not {name: count for name, count in counts.items() if count > 1}
    assert operations == EXPECTED_DIAGNOSIS_OPERATIONS


def test_brpc_diagnosis_start_endpoint_is_explicit_and_mutating() -> None:
    operation = _openapi_schema()["paths"][
        "/log_file/{log_file_id}/brpc-diagnosis"
    ]["post"]

    assert operation["operationId"] == "run_brpc_log_diagnosis"
    assert operation.get("x-mcp-enabled", False) is False
    assert operation["requestBody"]["required"] is True


def test_documented_agent_rules_do_not_change_backend_request_models() -> None:
    latency_events = ListSrcDstAggregatedEventRequest(kb_id="kb-1", page_cnt=1000)
    latency_traces = ListLogParseResultRequest(kb_id="kb-1", page_cnt=1000)
    connectivity_traces = ListTraceFailureEventResultRequest(
        kb_id="kb-1",
        page_cnt=1000,
    )

    assert ListSrcDstAggregatedEventRequest.model_fields["kb_id"].is_required()
    assert ListLogParseResultRequest.model_fields["kb_id"].is_required()
    assert latency_events.stat_type == "ave"
    assert latency_traces.is_anomalous is None
    assert connectivity_traces.is_anomalous is None
