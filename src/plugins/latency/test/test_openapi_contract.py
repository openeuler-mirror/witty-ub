import asyncio
from collections import Counter
from typing import Any

from fastapi import FastAPI
import httpx
from jsonschema import Draft202012Validator

from latency.access.mcp_contract import (
    MCP_INPUT_POLICIES,
    MCP_TOOL_DESCRIPTIONS,
    verify_mcp_input_policy_operations,
    verify_mcp_tool_description_operations,
)
from latency.access.openapi_adapter import OpenApiAdapter
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


EXPECTED_MCP_OPERATIONS = {
    "list_log_knowledge_bases": ("POST", "/log_kb/list"),
    "get_diagnosis_case": ("GET", "/diagnosis_case/{case_id}"),
    "get_failure_mode": ("GET", "/failure_mode/{failure_mode_id}"),
    "get_log_file": ("GET", "/log_file/{log_file_id}"),
    "get_log_knowledge_base": ("GET", "/log_kb/{kb_id}"),
    "get_latency_event": ("GET", "/aggregated_event/{event_id}"),
    "get_latency_metrics": ("POST", "/log_parse_result/metrics/latency"),
    "get_latency_trace": ("GET", "/log_parse_result/{result_id}"),
    "get_parse_task": ("GET", "/task/{task_id}"),
    "get_status_code_knowledge": (
        "GET",
        "/failure_mode/status_code/{status_code}",
    ),
    "list_log_files": ("POST", "/log_file/list/{kb_id}"),
    "list_parse_tasks": ("POST", "/task/list"),
    "get_connectivity_metrics": (
        "POST",
        "/log_failure_event_result/metrics/err_code",
    ),
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
    for router in (
        log_file.router,
        log_knowledge.router,
        log_parse_result.router,
        src_dst_aggregated_event.router,
        task.router,
        failure_mode_knowledge.router,
        log_failure_event_result.router,
        diagnosis_case.router,
    ):
        app.include_router(router)
    return app.openapi()


def test_mcp_openapi_operations_are_stable_unique_and_read_only() -> None:
    operations: dict[str, tuple[str, str]] = {}
    operation_ids: list[str] = []

    for path, path_item in _openapi_schema()["paths"].items():
        for method, operation in path_item.items():
            if not isinstance(operation, dict):
                continue
            if not operation.get("x-mcp-enabled", False):
                continue

            operation_id = operation["operationId"]
            operation_ids.append(operation_id)
            operations[operation_id] = (method.upper(), path)
            assert operation["x-mcp-read-only"] is True

    counts = Counter(operation_ids)
    assert not {
        operation_id: count
        for operation_id, count in counts.items()
        if count > 1
    }
    assert operations == EXPECTED_MCP_OPERATIONS


def test_all_exposed_operations_produce_valid_mcp_input_schemas() -> None:
    schema = _openapi_schema()

    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=schema)

    adapter = OpenApiAdapter(
        openapi_url="http://latency.test/openapi.json",
        base_url="http://latency.test",
        transport=httpx.MockTransport(handler),
    )
    asyncio.run(adapter.load())

    assert set(adapter.operations) == set(EXPECTED_MCP_OPERATIONS)
    verify_mcp_input_policy_operations(set(adapter.operations))
    verify_mcp_tool_description_operations(set(adapter.operations))
    assert set(MCP_INPUT_POLICIES) <= set(adapter.operations)
    assert set(MCP_TOOL_DESCRIPTIONS) == set(adapter.operations)
    input_schemas = {
        operation_id: adapter.build_input_schema(operation_id)
        for operation_id in adapter.operations
    }
    for input_schema in input_schemas.values():
        Draft202012Validator.check_schema(input_schema)
        properties = input_schema["properties"]
        if "page_cnt" in properties:
            assert properties["page_cnt"]["minimum"] == 1
            assert properties["page_cnt"]["maximum"] == 100
        if "page_num" in properties:
            assert properties["page_num"]["minimum"] == 1

    latency_events = input_schemas["list_latency_events"]
    assert "kb_id" in latency_events["required"]
    assert latency_events["properties"]["stat_type"]["default"] == "p99"
    assert latency_events["properties"]["sort_fields"]["default"] == [
        {"field": "total_latency", "order": "desc"}
    ]

    latency_traces = input_schemas["list_latency_traces"]
    assert "kb_id" in latency_traces["required"]
    assert latency_traces["properties"]["is_anomalous"]["default"] is True

    connectivity_traces = input_schemas["list_connectivity_traces"]
    assert (
        connectivity_traces["properties"]["is_anomalous"]["default"] is True
    )

    trace_logs = input_schemas["list_connectivity_trace_logs"]
    assert "trace_ids" in trace_logs["required"]
    assert trace_logs["properties"]["trace_ids"]["minItems"] == 1
    assert trace_logs["properties"]["trace_ids"]["maxItems"] == 100


def test_agent_rules_do_not_change_shared_backend_request_models() -> None:
    latency_events = ListSrcDstAggregatedEventRequest(page_cnt=1000)
    latency_traces = ListLogParseResultRequest(page_cnt=1000)
    connectivity_traces = ListTraceFailureEventResultRequest(
        kb_id="kb-1",
        page_cnt=1000,
    )

    assert latency_events.kb_id is None
    assert latency_events.stat_type == "ave"
    assert latency_traces.kb_id is None
    assert latency_traces.is_anomalous is None
    assert connectivity_traces.is_anomalous is None
