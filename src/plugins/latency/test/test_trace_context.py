"""Tests for raw trace-context log matching.

Latency parsers prefer an explicit ``trace_id=...`` inside the message over the
format column, so a latency anomaly's ``log_parse_result.trace_id`` can differ
from the raw line's 6th column. Raw context matching must therefore fall back to
the resolved trace id, otherwise latency-only traces show no running logs.
"""

from latency.common.trace_context import (
    build_trace_context_event,
    match_trace_context_trace_id,
)

SDK_ACCESS_LINE = (
    "2026-05-11T00:08:27.123456 | I | access.cpp:1 | sdk-pod | 1:2 | "
    "sdk-wrapper-trace | cluster | 0 | DS_KV_CLIENT_GET | 2000 | 4096 | "
    "Object_key:[object-key], trace_id=real-trace | ok"
)

WORKER_INFO_LINE = (
    "2026-05-11T00:08:27.123456 | I | rpc.cpp:1 | 192.168.102.119 | 1:2 | "
    "wrapper-trace | cluster | [ZMQ_RPC_FRAMEWORK_SLOW] "
    "trace_id=38d88464-1cba-472a-b717-cb8ea9f3591b framework_us=281"
)


def test_match_prefers_format_column_trace_id():
    raw = "sdk-wrapper-trace"
    assert (
        match_trace_context_trace_id(raw, SDK_ACCESS_LINE, {"sdk-wrapper-trace"})
        == "sdk-wrapper-trace"
    )


def test_match_falls_back_to_explicit_message_trace_id():
    raw = "sdk-wrapper-trace"
    assert (
        match_trace_context_trace_id(raw, SDK_ACCESS_LINE, {"real-trace"})
        == "real-trace"
    )


def test_match_falls_back_to_explicit_trace_id_in_runtime_log():
    raw = "wrapper-trace"
    resolved = "38d88464-1cba-472a-b717-cb8ea9f3591b"
    assert match_trace_context_trace_id(raw, WORKER_INFO_LINE, {resolved}) == resolved


def test_match_returns_empty_when_no_trace_matches():
    assert match_trace_context_trace_id("wrapper-trace", SDK_ACCESS_LINE, {"other"}) == ""


def test_build_trace_context_event_uses_resolved_trace_id():
    event = build_trace_context_event(
        log_id="log-1",
        log_dir="/logs",
        path="/logs/pod/sdk_access.log",
        line_no=1,
        line=SDK_ACCESS_LINE + "\n",
        trace_ids={"real-trace"},
    )
    assert event is not None
    assert event.trace_id == "real-trace"
