"""Only GET/SET traces and their complete diagnostic context are persisted."""

from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from latency.task.worker import store_trace_context_logs_worker as module


GET_OPS = [
    "DS_KV_CLIENT_GET", "DS_OBJECT_CLIENT_GET", "DS_POSIX_GET", "DS_POSIX_QUERY_AND_GET",
]
SET_OPS = ["DS_KV_CLIENT_SET", "DS_POSIX_CREATE", "DS_POSIX_PUBLISH"]
OTHER_OPS = ["DS_KV_CLIENT_EXIST", "DS_HETERO_CLIENT_INIT", "DS_POSIX_DELETE_ALL_COPY", "UNKNOWN"]


@pytest.mark.asyncio
@pytest.mark.parametrize("legacy", [False, True])
@pytest.mark.parametrize("supported", [False, True])
async def test_filter_before_any_write_preserves_supported_context(tmp_path, monkeypatch, legacy, supported):
    monkeypatch.setenv("WITTY_STORE_POLARS", "0" if legacy else "1")
    # Access records and runtime context span files and batches, with runtime
    # context preceding operation evidence. Selection must be per whole trace.
    monkeypatch.setattr(module, "_CONTEXT_BATCH_ROWS", 2)
    worker = module.StoreTraceContextLogsWorker
    ops = (GET_OPS + SET_OPS if supported else []) + OTHER_OPS
    runtime = [
        f"2026-10-12T14:49:00 | E | worker.cpp | pod | 1:2 | {op} | cluster | runtime failure"
        for op in ops + ["runtime-only"]
    ]
    access = [
        f"2026-10-12T14:50:00 | I | access.cpp | pod | 1:2 | {op} | cluster | 1001 | {op} | 100 | 0 | {{}} | timeout"
        for op in ops
    ]
    (tmp_path / "runtime.log").write_text("\n".join(runtime) + "\n")
    (tmp_path / "access.log").write_text("\n".join(access) + "\n")
    # A runtime payload resembling an access operation must not qualify a trace.
    with (tmp_path / "runtime.log").open("a") as stream:
        stream.write("2026-10-12T14:50:00 | I | file | pod | 1:2 | runtime-only | cluster | message | DS_KV_CLIENT_GET\n")
    monkeypatch.setattr(module.LogFilePGManager, "get_log_file_by_log_file_id", AsyncMock(return_value=None))
    monkeypatch.setattr(module.KVCacheLogEventDiagnosisWorker, "parse_filepath_config", AsyncMock(return_value={
        "ds_worker_access_log_file": ["access.log"],
    }))
    monkeypatch.setattr(module.FailureModeKnowledgePGManager, "get_all_failure_modes", AsyncMock(return_value={
        "mode": SimpleNamespace(children_failure_mode_ids="", error_code="K_TIMEOUT(1001)"),
    }))
    raw_traces = []
    raw_texts = []
    events = []
    roles = []

    async def write_raw(rows):
        raw_traces.extend(row["trace_id"] for row in rows)
        raw_texts.extend(row["raw_text"] for row in rows)

    async def write_csv(chunks):
        from test_context_store_bounded import _csv_records

        async for chunk in chunks:
            rows = [dict(zip(module.LogFailureEventPGManager._LOG_FAILURE_COPY_COLUMNS, row))
                    for row in _csv_records(chunk)]
            await write_raw(rows)

    async def write_events(rows):
        events.extend(rows)

    async def write_roles(rows):
        roles.extend(rows)

    raw = AsyncMock(side_effect=write_raw)
    csv = AsyncMock(side_effect=write_csv)
    trace = AsyncMock(side_effect=write_events)
    role = AsyncMock(side_effect=write_roles)
    monkeypatch.setattr(module.LogFailureEventPGManager, "add_log_failure_event_raw", raw)
    monkeypatch.setattr(module.LogFailureEventPGManager, "add_log_failure_event_csv", csv)
    monkeypatch.setattr(module.LogFailureEventPGManager, "add_trace_failure_event_raw", trace)
    monkeypatch.setattr(module.PodRolePGManager, "add_pod_role_raw", role)
    stored = await worker._store_trace_context_logs(
        str(tmp_path), "log", set(ops) | {"runtime-only"}, {line: ["mode"] for line in runtime},
    )
    expected = set(GET_OPS + SET_OPS) if supported else set()
    assert stored == expected
    assert set(raw_traces) == expected
    assert len(raw_traces) == 2 * len(expected)
    assert {event["trace_id"] for event in events} == expected
    assert {event["trace_id"] for event in roles} == expected
    for event in events:
        assert event["operation"] == ("GET" if event["trace_id"] in GET_OPS else "SET")
        assert event["failure_mode"] == ["mode"]
    assert set(runtime[:len(expected)]) <= set(raw_texts)
    if not supported:
        for writer in (raw, csv, trace, role):
            writer.assert_not_awaited()

