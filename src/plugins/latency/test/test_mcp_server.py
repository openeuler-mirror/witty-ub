import asyncio

import httpx
import pytest
from mcp.shared.memory import create_connected_server_and_client_session

from latency.access.latency_api_client import LatencyApiClient, LatencyApiError
from latency.access import mcp_server
from latency.database.managers import src_dst_aggregated_event
from latency.schemas.request import ListSrcDstAggregatedEventRequest


def test_api_client_returns_json_payload():
    async def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "POST"
        assert request.url.path == "/log_file/list/kb-1"
        return httpx.Response(
            200,
            json={"code": 200, "message": "success", "result": {"total": 0}},
        )

    client = LatencyApiClient(
        base_url="http://latency.test",
        transport=httpx.MockTransport(handler),
    )

    payload = asyncio.run(
        client.post(
            "/log_file/list/kb-1",
            json={"page_num": 1, "page_cnt": 20},
        )
    )

    assert payload["result"]["total"] == 0


def test_api_client_converts_http_error():
    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(404, json={"detail": "not found"})

    client = LatencyApiClient(
        base_url="http://latency.test",
        transport=httpx.MockTransport(handler),
    )

    with pytest.raises(LatencyApiError, match="HTTP 404"):
        asyncio.run(client.get("/failure_mode/unknown"))


def test_list_failure_traces_maps_filters(monkeypatch):
    calls = []

    class FakeClient:
        async def post(self, path, *, json):
            calls.append((path, json))
            return {"code": 200, "result": {"total": 0}}

    monkeypatch.setattr(mcp_server, "_client", lambda: FakeClient())

    asyncio.run(
        mcp_server.list_failure_traces(
            kb_id="kb-1",
            trace_ids=["trace-1"],
            status_codes=["1004"],
            src_ip="10.0.0.1",
            dst_ip="10.0.0.2",
            start_time="2026-06-29 10:00:00",
            end_time="2026-06-29 11:00:00",
        )
    )

    assert calls == [
        (
            "/log_failure_event_result/list_trace_events",
            {
                "kb_id": "kb-1",
                "trace_ids": ["trace-1"],
                "status_codes": ["1004"],
                "cluster_names": [],
                "host_names": [],
                "pod_names": [],
                "src_ip": "10.0.0.1",
                "dst_ip": "10.0.0.2",
                "start_time": "2026-06-29 10:00:00",
                "end_time": "2026-06-29 11:00:00",
                "is_anomalous": True,
                "sort_desc": True,
                "page_num": 1,
                "page_cnt": 20,
            },
        )
    ]


def test_list_failure_logs_requires_trace_ids():
    with pytest.raises(ValueError, match="at least one"):
        asyncio.run(mcp_server.list_failure_logs([]))


def test_list_latency_events_maps_log_event_time_range(monkeypatch):
    calls = []

    class FakeClient:
        async def post(self, path, *, json):
            calls.append((path, json))
            return {"code": 200, "result": {"total": 0}}

    monkeypatch.setattr(mcp_server, "_client", lambda: FakeClient())

    asyncio.run(
        mcp_server.list_latency_events(
            "kb-1",
            start_time="2026-06-29 10:00:00",
            end_time="2026-06-29 11:00:00",
        )
    )

    assert calls == [
        (
            "/aggregated_event/list",
            {
                "kb_id": "kb-1",
                "start_time": "2026-06-29 10:00:00",
                "end_time": "2026-06-29 11:00:00",
                "stat_type": "p99",
                "sort_fields": [{"field": "total_latency", "order": "desc"}],
                "page_num": 1,
                "page_cnt": 20,
            },
        )
    ]


def test_log_parse_results_maps_supported_time_and_sort_filters(monkeypatch):
    calls = []

    class FakeClient:
        async def post(self, path, *, json):
            calls.append((path, json))
            return {"code": 200, "result": {"total": 0}}

    monkeypatch.setattr(mcp_server, "_client", lambda: FakeClient())

    asyncio.run(
        mcp_server.list_log_parse_results(
            "kb-1",
            start_time="2026-06-29 10:00:00",
            created_at_start="2026-07-01 10:00:00",
            sort_fields=[{"field": "timestamp", "order": "asc"}],
        )
    )

    payload = calls[0][1]
    assert payload["start_time"] == "2026-06-29 10:00:00"
    assert payload["created_at_start"] == "2026-07-01 10:00:00"
    assert payload["sort_fields"] == [{"field": "timestamp", "order": "asc"}]
    assert "exclude_normal" not in payload
    assert "sort_by" not in payload


def test_latency_metrics_allows_api_no_sampling_value(monkeypatch):
    calls = []

    class FakeClient:
        async def post(self, path, *, json):
            calls.append((path, json))
            return {"code": 200, "result": {"total": 0}}

    monkeypatch.setattr(mcp_server, "_client", lambda: FakeClient())

    asyncio.run(mcp_server.get_latency_metrics("kb-1", max_points=-1))

    assert calls[0][1]["max_points"] == -1


def test_latency_event_api_filters_log_event_timestamp(monkeypatch):
    queries = []

    class FakeDatabase:
        async def execute_query(self, sql, params):
            queries.append((sql, params.copy()))
            return [{"cnt": 0}] if "COUNT(*)" in sql else []

    monkeypatch.setattr(
        src_dst_aggregated_event,
        "AsyncSQLiteSingleton",
        lambda: FakeDatabase(),
    )

    request = ListSrcDstAggregatedEventRequest(
        kb_id="kb-1",
        start_time="2026-06-29 10:00:00",
        end_time="2026-06-29 11:00:00",
    )
    total, events = asyncio.run(
        src_dst_aggregated_event.SrcDstAggregatedEventManager.list_aggregated_events(
            request
        )
    )

    assert total == 0
    assert events == []
    assert queries
    sql, params = queries[0]
    assert "lpr.timestamp >= :start_time" in sql
    assert "lpr.timestamp <= :end_time" in sql
    assert "ae.created_at >= :start_time" not in sql
    assert params["start_time"] == "2026-06-29 10:00:00"
    assert params["end_time"] == "2026-06-29 11:00:00"


def test_new_read_tools_map_api_requests(monkeypatch):
    calls = []

    class FakeClient:
        async def get(self, path):
            calls.append(("GET", path, None))
            return {"code": 200, "result": {}}

        async def post(self, path, *, json):
            calls.append(("POST", path, json))
            return {"code": 200, "result": {}}

    monkeypatch.setattr(mcp_server, "_client", lambda: FakeClient())

    asyncio.run(mcp_server.get_log_parse_options("kb/1"))
    asyncio.run(
        mcp_server.list_latency_time_windows(
            "kb-1",
            src_ip="10.0.0.1",
            interval="hour",
            operation="GET",
            sort_fields=[{"field": "total_latency", "order": "desc"}],
        )
    )
    asyncio.run(
        mcp_server.list_failure_src_dst_aggregates(
            "kb-1",
            start_time="2026-06-29 10:00:00",
            cluster_name="cluster-1",
            src_ip="10.0.0.1",
            dst_ip="10.0.0.2",
            sort_fields=[{"field": "1004", "order": "asc"}],
        )
    )
    asyncio.run(
        mcp_server.list_failure_pod_aggregates(
            "kb-1",
            start_time="2026-06-29 10:00:00",
        )
    )
    asyncio.run(
        mcp_server.get_error_code_metrics(
            "kb-1",
            err_codes=["1004"],
            pod_names=["pod-1"],
        )
    )

    assert calls == [
        ("GET", "/log_parse_result/options?kb_id=kb%2F1", None),
        (
            "POST",
            "/aggregated_event/list_time_window",
            {
                "kb_id": "kb-1",
                "src_ip": "10.0.0.1",
                "operation": "GET",
                "interval": "hour",
                "stat_type": "p99",
                "sort_by": "start_time",
                "sort_order": "asc",
                "sort_fields": [{"field": "total_latency", "order": "desc"}],
                "page_num": 1,
                "page_cnt": 20,
            },
        ),
        (
            "POST",
            "/log_failure_event_result/list_src_dst_aggregated_failure_events",
            {
                "kb_id": "kb-1",
                "start_time": "2026-06-29 10:00:00",
                "cluster_name": "cluster-1",
                "src_ip": "10.0.0.1",
                "dst_ip": "10.0.0.2",
                "sort_by": "all",
                "sort_desc": True,
                "sort_fields": [{"field": "1004", "order": "asc"}],
                "page_num": 1,
                "page_cnt": 20,
            },
        ),
        (
            "POST",
            "/log_failure_event_result/list_pod_aggregated_failure_events",
            {
                "kb_id": "kb-1",
                "start_time": "2026-06-29 10:00:00",
                "sort_by": "all",
                "sort_desc": True,
                "page_num": 1,
                "page_cnt": 20,
            },
        ),
        (
            "POST",
            "/log_failure_event_result/metrics/err_code",
            {
                "kb_id": "kb-1",
                "err_codes": ["1004"],
                "cluster_names": [],
                "host_names": [],
                "pod_names": ["pod-1"],
                "max_points": 1000,
            },
        ),
    ]


def test_search_diagnosis_cases_maps_signals(monkeypatch):
    calls = []

    class FakeClient:
        async def post(self, path, *, json):
            calls.append((path, json))
            return {"code": 200, "result": {"total": 0, "matches": []}}

    monkeypatch.setattr(mcp_server, "_client", lambda: FakeClient())

    asyncio.run(
        mcp_server.search_diagnosis_cases(
            kb_id="kb-1",
            fault_type="latency",
            status_codes=["1004"],
            src_ips=["10.0.0.1"],
            latency_components=["urma_link_latency"],
            min_confidence=0.7,
        )
    )

    assert calls == [
        (
            "/diagnosis_case/search",
            {
                "kb_id": "kb-1",
                "fault_type": "latency",
                "status_codes": ["1004"],
                "failure_mode_ids": [],
                "src_ips": ["10.0.0.1"],
                "dst_ips": [],
                "hosts": [],
                "pods": [],
                "clusters": [],
                "latency_components": ["urma_link_latency"],
                "log_keywords": [],
                "min_confidence": 0.7,
                "page_num": 1,
                "page_cnt": 10,
            },
        )
    ]


def test_mcp_exposes_only_expected_read_tools():
    async def list_tool_names():
        async with create_connected_server_and_client_session(
            mcp_server.mcp
        ) as session:
            tools = await session.list_tools()
            return {tool.name for tool in tools.tools}

    assert asyncio.run(list_tool_names()) == {
        "list_log_kbs",
        "get_log_kb",
        "list_log_files",
        "get_parse_task",
        "list_latency_events",
        "list_latency_time_windows",
        "get_log_parse_options",
        "list_log_parse_results",
        "get_latency_metrics",
        "list_failure_time_windows",
        "list_failure_pod_aggregates",
        "list_failure_src_dst_aggregates",
        "get_error_code_metrics",
        "list_failure_traces",
        "list_failure_logs",
        "get_status_code_knowledge",
        "get_failure_mode",
        "search_diagnosis_cases",
        "get_diagnosis_case",
        "read_file",
    }
