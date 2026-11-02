"""Latency trace pods must include pods visible in the runtime log context."""

from contextlib import asynccontextmanager
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from sqlalchemy import create_engine

from latency.database.engine import PGManager
from latency.database.managers.log_parse_result import LogParseResultPGManager
from latency.schemas.log import LogParseResultModel
from latency.schemas.request import ListLogParseResultRequest
from latency.services.log_parse_result import LogParseResultService


@pytest.fixture
def context_db(monkeypatch):
    engine = create_engine("sqlite://")
    with engine.begin() as connection:
        connection.exec_driver_sql("CREATE TABLE log_file (id TEXT, kb_id TEXT)")
        connection.exec_driver_sql(
            "CREATE TABLE log_failure_event (log_id TEXT, trace_id TEXT, pod_name TEXT)"
        )
        connection.exec_driver_sql(
            "INSERT INTO log_file VALUES (?, ?)",
            [("log-1", "kb-1"), ("log-2", "kb-1"), ("log-3", "kb-2")],
        )
        connection.exec_driver_sql(
            "INSERT INTO log_failure_event VALUES (?, ?, ?)",
            [
                ("log-1", "trace-1", "10.0.0.1"),
                ("log-1", "trace-1", " 10.0.0.2 "),  # ordinary runtime log
                ("log-1", "trace-1", "10.0.0.2"),
                ("log-1", "trace-1", " "),
                ("log-1", "trace-1", None),
                ("log-2", "trace-1", "worker-pod-3"),
                ("log-3", "trace-1", "other-kb-pod"),
                ("log-1", "unrelated-trace", "unrelated-pod"),
            ],
        )
        statements = []

        async def execute(stmt):
            statements.append(stmt)
            return connection.execute(stmt)

        @asynccontextmanager
        async def session():
            yield SimpleNamespace(execute=execute)

        monkeypatch.setattr(PGManager, "session", session)
        yield statements
    engine.dispose()


def _result(**overrides):
    return LogParseResultModel(**(dict(
        id="result-1", log_id="log-1", trace_id="trace-1",
        pod_ips=["10.0.0.1"], is_anomalous=True, total_latency=12.0,
    ) | overrides))


@pytest.mark.asyncio
@pytest.mark.parametrize("scope,expected", [
    ({"kb_id": "kb-1"}, ["10.0.0.1", "10.0.0.2", "worker-pod-3"]),
    ({"kb_id": "kb-1", "log_id": "log-1"}, ["10.0.0.1", "10.0.0.2"]),
])
async def test_list_includes_runtime_pods_within_scope(monkeypatch, context_db, scope, expected):
    results = [_result(), _result(id="result-2", trace_id="no-context", pod_ips=["sdk-pod"])]
    monkeypatch.setattr(LogParseResultPGManager, "list_log_parse_results",
                        AsyncMock(return_value=(25, results)))

    response = await LogParseResultService.list_log_parse_results(
        ListLogParseResultRequest(**scope)
    )

    assert response.log_parse_results[0].pod_ips == expected
    assert response.log_parse_results[1].pod_ips == ["sdk-pod"]
    assert response.total == 25
    assert response.log_parse_results[0].total_latency == 12.0
    assert len(context_db) == 1  # one query for the entire page


@pytest.mark.asyncio
async def test_list_retains_parser_pods_and_fills_missing_values(monkeypatch, context_db):
    results = [_result(pod_ips=["parser-only-pod", "10.0.0.1"]), _result(pod_ips=None)]
    monkeypatch.setattr(LogParseResultPGManager, "list_log_parse_results",
                        AsyncMock(return_value=(2, results)))
    response = await LogParseResultService.list_log_parse_results(
        ListLogParseResultRequest(kb_id="kb-1", log_id="log-1")
    )
    assert response.log_parse_results[0].pod_ips == ["10.0.0.1", "10.0.0.2", "parser-only-pod"]
    assert response.log_parse_results[1].pod_ips == ["10.0.0.1", "10.0.0.2"]


@pytest.mark.asyncio
@pytest.mark.parametrize("results", [[], [_result(trace_id=None)]])
async def test_no_context_query_without_trace_ids(monkeypatch, context_db, results):
    monkeypatch.setattr(LogParseResultPGManager, "list_log_parse_results",
                        AsyncMock(return_value=(len(results), results)))
    await LogParseResultService.list_log_parse_results(ListLogParseResultRequest(kb_id="kb-1"))
    assert context_db == []


def test_client_rpc_pod_survives_scan_and_trace_merge():
    import polars as pl
    from latency.parse import ClientInfoParser
    from latency.parse.parallel_scanner.scan_vector_access import access_label_columns
    from latency.parse.parallel_scanner.columnar import entries_to_columns
    from latency.parse.parallel_scanner.trace_frame import build_trace_frame
    from test_scan_memory import _rpc
    from test_trace_frame import _sdk

    line = _rpc("trace-1").replace("| pod |", "| rpc-pod |")
    scanned = access_label_columns(
        pl.DataFrame({"line": [line]}), ["client.log"], [[ClientInfoParser()]],
        file_rank={"client.log": 0},
    )
    assert scanned["pod_ip"].to_list() == ["rpc-pod"]
    sdk = pl.DataFrame(entries_to_columns({"SDK access parse": [_sdk("trace-1")]}))
    merged = build_trace_frame(pl.concat([sdk, scanned], how="diagonal_relaxed"))
    assert merged["pod_ip"].to_list() == [["10.0.0.9", "rpc-pod"]]


def test_client_rpc_reference_projection_retains_pod_and_cluster():
    from latency.ENUM.ds_log import EntryType
    from latency.parse.parallel_scanner.columnar import entries_to_columns
    from latency.parse.labels import CLIENT_INFO_BUCKET_LABEL
    from test_trace_frame import _sdk

    entry = list(_sdk("trace-1", pod="rpc-pod"))
    entry[9] = EntryType.CLIENT_RPC.value
    entry[10] = "rpc-cluster"
    columns = entries_to_columns({CLIENT_INFO_BUCKET_LABEL: [tuple(entry)]})
    assert columns["pod_ip"] == ["rpc-pod"]
    assert columns["cluster_name"] == ["rpc-cluster"]
