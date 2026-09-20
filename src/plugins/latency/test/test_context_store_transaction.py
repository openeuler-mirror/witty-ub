"""Trace aggregate streaming preserves the original all-or-nothing COPY."""

from contextlib import asynccontextmanager
from types import SimpleNamespace
import time

import pytest

from latency.database.engine import PGManager
from latency.database.managers.log_failure_event import LogFailureEventPGManager
from latency.task.worker import store_trace_context_logs_worker as module


@pytest.mark.asyncio
@pytest.mark.parametrize("fail", [False, True])
async def test_trace_aggregate_stream_uses_one_transaction_and_copy(monkeypatch, fail):
    events = []
    converted = []
    copied = []

    class State:
        def event(self, log_id, trace_id, _cache):
            converted.append(trace_id)
            return {
                "id": trace_id, "log_id": log_id, "trace_id": trace_id,
                "timestamp": "2026-09-18 00:00:00", "pod_names": ["pod"],
                "host_names": ["Unknown"], "cluster_names": ["cluster"],
                "src_ip": "", "dst_ip": "", "status_code": [],
                "failure_mode": [], "operation": "GET",
            }

    class Driver:
        async def copy_records_to_table(self, table, *, records, columns):
            events.append("copy")
            assert table == "trace_failure_event"
            assert not converted, "trace events must be converted as COPY consumes them"
            record = next(records)
            assert converted == ["t0"]
            copied.append(record[2])
            if fail:
                raise RuntimeError("COPY interrupted")
            for record in records:
                copied.append(record[2])

    class Connection:
        async def get_raw_connection(self):
            return SimpleNamespace(driver_connection=Driver())

    @asynccontextmanager
    async def connection():
        events.append("begin")
        try:
            yield Connection()
        except Exception:
            events.append("rollback")
            raise
        else:
            events.append("commit")

    monkeypatch.setattr(PGManager, "connection", connection)
    monkeypatch.setattr(LogFailureEventPGManager, "_COPY_THRESHOLD", 1)
    monkeypatch.setattr(module, "_CONTEXT_BATCH_ROWS", 2)
    states = {f"t{index}": State() for index in range(5)}
    operation = module.StoreTraceContextLogsWorker._write_trace_failure_events(
        states, {}, 50, 50, time.perf_counter(), None, 100.0, log_id="log"
    )
    if fail:
        with pytest.raises(RuntimeError, match="COPY interrupted"):
            await operation
        assert events == ["begin", "copy", "rollback"]
        assert copied == converted == ["t0"]
    else:
        await operation
        assert events == ["begin", "copy", "commit"]
        assert copied == converted == ["t0", "t1", "t2", "t3", "t4"]
        assert not states
