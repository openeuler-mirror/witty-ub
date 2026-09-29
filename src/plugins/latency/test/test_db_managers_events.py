# Copyright (c) Huawei Technologies Co., Ltd. 2023-2025. All rights reserved.
"""事件类 PG manager 单测（log_failure_event / log_parse_result /
time_window_aggregated_event / src_dst_aggregated_event）。

沿用 test_brpc_diagnosis_database.py / test_log_file_hard_delete.py 的假会话打法：
- manager 方法里的 SQL 构建行因方法被调用而覆盖；
- 结果映射行靠假会话返回假行触发；
- PGManager.session / PGManager.connection 用 monkeypatch 替换，无需真实数据库。
"""
from __future__ import annotations

import ipaddress
from contextlib import asynccontextmanager
from datetime import datetime, timedelta
from types import SimpleNamespace

import pytest

from latency.ENUM.sampling import SampleMode
from latency.database.managers import time_window_aggregated_event as tw_manager_module
from latency.database.engine import PGManager
from latency.database.managers.log_failure_event import LogFailureEventPGManager
from latency.database.managers.log_parse_result import LogParseResultPGManager
from latency.database.managers.src_dst_aggregated_event import (
    SrcDstAggregatedEventPGManager,
)
from latency.database.managers.time_window_aggregated_event import (
    TimeWindowAggregatedEventPGManager,
)
from latency.database.models import LogFailureEvent, TraceFailureEvent
from latency.database.utils import COPY_COLUMNS
from latency.exceptions.biz_exceptions import BadRequestBizException
from latency.schemas.log import (
    LogParseResultDataclass,
    SrcDstAggregatedEventDataclass,
    TimeWindowAggregatedEventDataclass,
    YUANRONG_METRIC_FIELDS,
)
from latency.schemas.log_failure_event import LogFailureEventModel, TraceFailureEventModel
from latency.schemas.request import (
    GetErrCodeMetricsRequest,
    GetLatencyMetricsRequest,
    ListLogFailureEventResultRequest,
    ListLogParseResultRequest,
    ListPodAggregatedFailureEventRequest,
    ListSrcDstAggregatedEventRequest,
    ListSrcDstAggregatedFailureEventRequest,
    ListTimeAggregatedFailureEventRequest,
    ListTimeWindowAggregatedEventRequest,
    ListTraceFailureEventResultRequest,
    ListTracesByHostRequest,
    SortField,
)

DT = datetime(2025, 1, 1, 12, 0, 0)
BASE_EPOCH = 1735689600  # 2025-01-01 00:00:00 UTC


# ---------------------------------------------------------------------------
# 假会话 / 假连接基础设施
# ---------------------------------------------------------------------------
class FakeResult:
    """session.execute() 返回值的假对象，覆盖 scalars/mappings/scalar 用法。"""

    def __init__(self, rows=(), scalar=None, rowcount=0):
        self._rows = list(rows)
        self._scalar = scalar
        self.rowcount = rowcount

    def scalars(self):
        return self

    def mappings(self):
        return self

    def all(self):
        return list(self._rows)

    def scalar(self):
        if self._scalar is not None:
            return self._scalar
        return self._rows[0] if self._rows else None

    def scalar_one(self):
        return self.scalar()

    def scalar_one_or_none(self):
        return self.scalar()

    def one_or_none(self):
        return self._rows[0] if self._rows else None


class FakeRow:
    """带 _mapping 的行（对应 execute().all() 后 r._mapping 用法）。"""

    def __init__(self, mapping):
        self._mapping = dict(mapping)


class FakeStreamResult:
    def __init__(self, rows):
        self._rows = list(rows)
        self.closed = False

    def __aiter__(self):
        return self._iter()

    async def _iter(self):
        for row in self._rows:
            yield row

    async def close(self):
        self.closed = True


class FakeAsyncpgConnection:
    def __init__(self, error=None):
        self.copy_calls = []
        self.error = error

    async def copy_records_to_table(self, table, records, columns):
        if self.error is not None:
            raise self.error
        self.copy_calls.append((table, list(records), list(columns)))


class FakeConnection:
    def __init__(self, asyncpg_conn=None):
        self.executed = []
        self.asyncpg = asyncpg_conn if asyncpg_conn is not None else FakeAsyncpgConnection()

    async def execute(self, statement, parameters=None):
        self.executed.append((statement, parameters))

    async def get_raw_connection(self):
        return SimpleNamespace(driver_connection=self.asyncpg)


class FakeSession:
    """按调用顺序弹出脚本化响应的假 AsyncSession。"""

    def __init__(self, responses=(), get_handler=None, stream_rows=None):
        self.responses = list(responses)
        self.executed = []
        self.added = []
        self.get_calls = []
        self.streamed = []
        self.get_handler = get_handler
        self.stream_rows = list(stream_rows or [])

    async def execute(self, statement, parameters=None):
        self.executed.append((statement, parameters))
        if self.responses:
            resp = self.responses.pop(0)
            if isinstance(resp, Exception):
                raise resp
            return resp
        return FakeResult()

    def add_all(self, objs):
        self.added.extend(objs)

    async def get(self, row_type, key):
        self.get_calls.append((row_type, key))
        if self.get_handler is not None:
            return self.get_handler(row_type, key)
        return None

    async def stream(self, statement):
        self.streamed.append(statement)
        return FakeStreamResult(self.stream_rows)


def install_session(monkeypatch, session):
    @asynccontextmanager
    async def _fake_session():
        yield session

    monkeypatch.setattr(PGManager, "session", _fake_session)
    return session


def install_connection(monkeypatch, conn):
    @asynccontextmanager
    async def _fake_connection():
        yield conn

    monkeypatch.setattr(PGManager, "connection", _fake_connection)
    return conn


# ---------------------------------------------------------------------------
# 数据构造器
# ---------------------------------------------------------------------------
def make_log_failure_model(**overrides):
    data = dict(
        log_id="log-1",
        log_file="app.log",
        raw_text="raw",
        host_name="host-1",
        timestamp="2025-01-01 12:00:00",
        level="ERROR",
        filename="f.py",
        pod_name="pod-1",
        pid="1",
        tid="2",
        trace_id="tr-1",
        cluster_name="cl-1",
        message="msg",
        status_code="1004",
        failure_mode=["mode_a", "mode_b"],
    )
    data.update(overrides)
    return LogFailureEventModel(**data)


def make_trace_model(**overrides):
    data = dict(
        trace_id="tr-1",
        log_id="log-1",
        pod_names=["pod-1"],
        src_ip="10.0.0.1",
        dst_ip="10.0.0.2",
        host_names=["host-1"],
        cluster_names=["cl-1"],
        timestamp="2025-01-01 12:00:00",
        status_code=["1004"],
        failure_mode=["mode_a"],
        operation="GET",
    )
    data.update(overrides)
    return TraceFailureEventModel(**data)


def make_log_failure_row(**overrides):
    data = dict(
        id="row-1",
        log_id="log-1",
        log_file="app.log",
        raw_text="raw",
        host_name="host-1",
        timestamp=DT,
        level="ERROR",
        filename="f.py",
        pod_name="pod-1",
        pid="1",
        tid="2",
        trace_id="tr-1",
        cluster_name="cl-1",
        message="msg",
        status_code="1004",
        failure_mode="mode_a,mode_b",
    )
    data.update(overrides)
    return SimpleNamespace(**data)


def make_trace_row(**overrides):
    data = dict(
        id="row-1",
        log_id="log-1",
        trace_id="tr-1",
        pod_names=["pod-1"],
        src_ip="10.0.0.1",
        dst_ip="10.0.0.2",
        host_names=["host-1"],
        cluster_names=["cl-1"],
        timestamp=DT,
        status_code=["1004"],
        failure_mode="mode_a",
        operation="GET",
    )
    data.update(overrides)
    return SimpleNamespace(**data)


def make_log_parse_result_row(**overrides):
    data = dict(
        id="r-1",
        log_id="log-1",
        aggregated_event_id="agg-1",
        anomalous_event_id="an-1",
        trace_id="tr-1",
        timestamp=DT,
        src_ip="10.0.0.1",
        dst_ip="10.0.0.2",
        pod_ips=["pod-1"],
        cluster_name="cl-1",
        host="host-1",
        total_latency=9.0,
        c2w_latency=1.0,
        worker_query_meta_latency=2.0,
        urma_total_latency=3.0,
        urma_link_latency=4.0,
        urma_inflight_count=5,
        c2w_urma_latency=6.0,
        w2w_urma_latency=7.0,
        operation="GET",
        data_size="1KB",
        offset=3,
        is_anomalous=True,
        content="content",
        anomaly_reason="reason",
        anomaly_score=0.5,
        remark="remark",
        existed_status=True,
        created_at=DT,
        sdk_process=1.0,
        sdk_rpc=1.0,
        local_worker_cost=1.0,
        local_worker_lock=1.0,
        remote_worker_cost=1.0,
        remote_worker_rpc=1.0,
        master_process=1.0,
        master_rpc_total=1.0,
        create_latency=1.0,
        publish_latency=1.0,
        worker_total_latency=1.0,
    )
    data.update(overrides)
    return SimpleNamespace(**data)


SRC_DST_FIELD_NAMES = (
    "total_latency",
    "query_meta_latency",
    "urma_total_latency",
    "urma_link_latency",
    "c2w_urma_latency",
    "w2w_urma_latency",
)


def make_src_dst_stats_mapping(**overrides):
    mapping = {
        "id": "a-1",
        "src_ip": "10.0.0.1",
        "dst_ip": "10.0.0.2",
        "log_id": "log-1",
        "existed_status": True,
        "created_at": DT,
        "operation": "GET",
        "log_parse_result_cnt": 10,
        "anomaly_log_parse_result_cnt": 2,
        "anomaly_cnt": 2,
    }
    for name in SRC_DST_FIELD_NAMES:
        for st in ("ave", "min", "max", "p95", "p99"):
            mapping[f"{st}_{name}"] = 1.0
    mapping.update(overrides)
    return mapping


def make_src_dst_agg_row(**overrides):
    data = dict(
        id="a-1",
        src_ip="10.0.0.1",
        dst_ip="10.0.0.2",
        operation="GET",
        log_id="log-1",
        log_parse_result_cnt=3,
        anomaly_log_parse_result_cnt=1,
        anomaly_cnt=1,
        existed_status=True,
        created_at=DT,
    )
    data.update(overrides)
    return SimpleNamespace(**data)


def make_parse_storage(**overrides):
    data = dict(
        total_latency=1.5,
        is_anomalous=False,
        log_id="log-1",
        timestamp="2025-01-01 12:00:00",
        src_ip="10.0.0.1",
        dst_ip="10.0.0.2",
        pod_ips=["pod-1"],
        trace_id="tr-1",
        operation="GET",
        content="content",
        existed_status=True,
    )
    data.update(overrides)
    return LogParseResultDataclass(**data)


# ===========================================================================
# 1. log_failure_event
# ===========================================================================
def test_ip_eq_branches():
    assert LogFailureEventPGManager._ip_eq(TraceFailureEvent.src_ip, None) is None
    empty = LogFailureEventPGManager._ip_eq(TraceFailureEvent.src_ip, "")
    assert empty is not None
    cond = LogFailureEventPGManager._ip_eq(TraceFailureEvent.src_ip, "10.0.0.1")
    assert cond is not None


def test_array_overlap_branches():
    overlap = LogFailureEventPGManager._array_overlap
    assert overlap(TraceFailureEvent.pod_names, None) is None
    assert overlap(TraceFailureEvent.pod_names, []) is None
    assert overlap(TraceFailureEvent.pod_names, ["", ""]) is None
    assert overlap(TraceFailureEvent.pod_names, ["pod-1", ""]) is not None


def test_log_ids_for_kb_placeholder():
    assert LogFailureEventPGManager._log_ids_for_kb("") is None
    assert LogFailureEventPGManager._log_ids_for_kb("kb-1") is None


def test_normalize_failure_mode_column():
    normalize = LogFailureEventPGManager._normalize_failure_mode_column
    assert normalize(["a", " b ", "", None, 5]) == "a,b"
    assert normalize(None) == ""
    assert normalize("") == ""
    assert normalize("x") == "x"


async def test_add_log_failure_event_empty(monkeypatch):
    session = install_session(monkeypatch, FakeSession())
    assert await LogFailureEventPGManager.add_log_failure_event([]) == []
    assert session.added == []


async def test_add_log_failure_event_models(monkeypatch):
    session = install_session(monkeypatch, FakeSession())
    events = [
        make_log_failure_model(id="e-1"),
        make_log_failure_model(id="", host_name=None, failure_mode=["mode_c"]),
    ]
    ids = await LogFailureEventPGManager.add_log_failure_event(events)
    assert len(ids) == 2
    assert ids[0] == "e-1"
    assert ids[1] != ""
    objs = session.added
    assert all(isinstance(o, LogFailureEvent) for o in objs)
    assert objs[0].host_name == "host-1"
    assert objs[1].host_name == "Unknown"
    assert objs[0].failure_mode == "mode_a,mode_b"
    assert objs[1].failure_mode == "mode_c"
    assert objs[0].timestamp == DT


async def test_add_log_failure_event_raw_small(monkeypatch):
    session = install_session(monkeypatch, FakeSession())
    dicts = [
        {"id": "r-1", "log_id": "log-1", "timestamp": "2025-01-01 12:00:00", "failure_mode": ["a"]},
        {"log_id": "log-1", "failure_mode": None, "host_name": "h-1"},
    ]
    ids = await LogFailureEventPGManager.add_log_failure_event_raw(dicts)
    assert len(ids) == 2
    objs = session.added
    assert objs[0].id == "r-1"
    assert objs[1].id != ""
    assert objs[1].failure_mode == ""
    assert objs[1].host_name == "h-1"
    assert objs[1].level == ""
    assert objs[1].raw_text == ""
    assert objs[1].timestamp is None


async def test_add_log_failure_event_raw_copy(monkeypatch):
    asyncpg = FakeAsyncpgConnection()
    install_connection(monkeypatch, FakeConnection(asyncpg))
    results = [
        {"id": f"r-{i}", "log_id": "log-1", "timestamp": "2025-01-01 12:00:00", "failure_mode": ["a"]}
        for i in range(1000)
    ]
    ids = await LogFailureEventPGManager.add_log_failure_event_raw(results)
    assert len(ids) == 1000
    assert ids[0] == "r-0"
    table, records, columns = asyncpg.copy_calls[0]
    assert table == "log_failure_event"
    assert len(records) == 1000
    assert columns == LogFailureEventPGManager._LOG_FAILURE_COPY_COLUMNS
    assert records[0][0] == "r-0"
    assert records[0][5] == DT
    assert records[0][4] == "Unknown"


async def test_add_log_failure_event_if_not_exist(monkeypatch):
    session = install_session(monkeypatch, FakeSession())
    assert await LogFailureEventPGManager.add_log_failure_event_if_not_exist([]) == []
    events = [make_log_failure_model(id="e-1"), make_log_failure_model(id="")]
    ids = await LogFailureEventPGManager.add_log_failure_event_if_not_exist(events)
    assert ids[0] == "e-1"
    assert ids[1] != ""
    assert len(session.executed) == 1


async def test_update_failure_mode_by_raw_log(monkeypatch):
    session = install_session(
        monkeypatch, FakeSession(responses=[FakeResult(rowcount=2)])
    )
    assert await LogFailureEventPGManager.update_failure_mode_by_raw_log(
        "log-1", "raw", "m"
    ) is True
    sql = str(session.executed[0][0])
    assert "UPDATE log_failure_event" in sql
    assert session.executed[0][1] == {"log_id": "log-1", "raw_text": "raw", "failure_mode": "m"}

    install_session(monkeypatch, FakeSession(responses=[FakeResult(rowcount=0)]))
    assert await LogFailureEventPGManager.update_failure_mode_by_raw_log(
        "log-1", "raw", "m"
    ) is False


async def test_delete_failure_events_by_log_id(monkeypatch):
    session = install_session(monkeypatch, FakeSession())
    assert await LogFailureEventPGManager.delete_unclassified_log_events_by_log_id("log-1") is True
    assert await LogFailureEventPGManager.delete_log_failure_events_by_log_id("log-1") is True
    assert await LogFailureEventPGManager.delete_trace_failure_events_by_log_id("log-1") is True
    sqls = [str(s) for s, _ in session.executed]
    assert "failure_mode IS NULL" in sqls[0]
    assert "DELETE FROM log_failure_event WHERE log_id = :log_id" in sqls[1]
    assert "DELETE FROM trace_failure_event WHERE log_id = :log_id" in sqls[2]


async def test_add_trace_failure_event_models(monkeypatch):
    session = install_session(monkeypatch, FakeSession())
    events = [
        make_trace_model(id="", trace_id="tr-1"),
        make_trace_model(
            id="t-2",
            trace_id="tr-2",
            src_ip="",
            dst_ip="",
            pod_names=[],
            host_names=[],
            cluster_names=[],
            status_code=[],
            failure_mode=[],
            operation="",
        ),
    ]
    ids = await LogFailureEventPGManager.add_trace_failure_event(events)
    assert ids == ["tr-1", "tr-2"]
    objs = session.added
    assert all(isinstance(o, TraceFailureEvent) for o in objs)
    assert objs[0].id != ""
    assert objs[1].id == "t-2"
    assert objs[1].src_ip is None
    assert objs[1].pod_names == []
    assert objs[1].failure_mode == ""
    assert objs[1].operation == ""


async def test_add_trace_failure_event_raw_small(monkeypatch):
    session = install_session(monkeypatch, FakeSession())
    dicts = [
        {
            "log_id": "log-1",
            "trace_id": "tr-9",
            "pod_names": "pod-1, pod-2",
            "host_names": "h1",
            "cluster_names": 123,
            "status_code": "1004, 1004,1009",
            "src_ip": None,
            "dst_ip": None,
            "failure_mode": ["a"],
            "operation": None,
        }
    ]
    ids = await LogFailureEventPGManager.add_trace_failure_event_raw(dicts)
    assert ids == ["tr-9"]
    obj = session.added[0]
    assert obj.pod_names == ["pod-1", "pod-2"]
    assert obj.host_names == ["h1"]
    assert obj.cluster_names == []
    assert obj.status_code == ["1004", "1004", "1009"]
    assert obj.failure_mode == "a"
    assert obj.src_ip is None


async def test_add_trace_failure_event_raw_copy(monkeypatch):
    asyncpg = FakeAsyncpgConnection()
    install_connection(monkeypatch, FakeConnection(asyncpg))
    results = [
        {"log_id": "log-1", "trace_id": f"tr-{i}", "pod_names": ["p"], "host_names": ["h"], "cluster_names": ["c"], "status_code": ["1004", "1004"]}
        for i in range(1000)
    ]
    ids = await LogFailureEventPGManager.add_trace_failure_event_raw(results)
    assert len(ids) == 1000
    assert ids[0] == "tr-0"
    table, records, columns = asyncpg.copy_calls[0]
    assert table == "trace_failure_event"
    assert len(records) == 1000
    assert columns == LogFailureEventPGManager._TRACE_FAILURE_COPY_COLUMNS


async def test_log_ids_for_kb_id(monkeypatch):
    install_session(monkeypatch, FakeSession())
    assert await LogFailureEventPGManager._log_ids_for_kb_id("") == []
    session = install_session(
        monkeypatch, FakeSession(responses=[FakeResult(rows=["log-1", "log-2"])])
    )
    assert await LogFailureEventPGManager._log_ids_for_kb_id("kb-1") == ["log-1", "log-2"]


def test_build_trace_base_stmt():
    stmt = LogFailureEventPGManager._build_trace_base_stmt(object())
    assert stmt is not None


# ---------------------------------------------------------------------------
# log_failure_event 读侧
# ---------------------------------------------------------------------------
async def test_list_trace_failure_events_kb_without_logs(monkeypatch):
    install_session(monkeypatch, FakeSession(responses=[FakeResult(rows=[])]))
    req = ListTraceFailureEventResultRequest(kb_id="kb-x")
    assert await LogFailureEventPGManager.list_trace_failure_events(req) == (0, [])


async def test_list_trace_failure_events_full(monkeypatch):
    rows = [
        make_trace_row(),
        make_trace_row(
            id="row-2",
            trace_id="tr-2",
            failure_mode=None,
            timestamp=datetime(2025, 1, 1, 12, 0, 5, 700000),
        ),
    ]
    session = install_session(
        monkeypatch,
        FakeSession(
            responses=[
                FakeResult(rows=["log-1"]),
                FakeResult(rows=[2]),
                FakeResult(rows=rows),
            ]
        ),
    )
    req = ListTraceFailureEventResultRequest(
        kb_id="kb-1",
        trace_ids=["tr-1", "tr-2"],
        pod_names=["pod-1"],
        host_names=["host-1"],
        cluster_names=["cl-1"],
        status_codes=["1004"],
        src_ip="10.0.0.1",
        dst_ip="10.0.0.2",
        is_anomalous=True,
        start_time="2025-01-01 11:00:00",
        end_time="2025-01-01 13:00:00",
        operation="GET",
        sort_desc=True,
        page_cnt=10,
        page_num=1,
    )
    total, events = await LogFailureEventPGManager.list_trace_failure_events(req)
    assert total == 2 and len(events) == 2
    assert events[0].id == "row-1"
    assert events[0].failure_mode == ["mode_a"]
    assert events[0].src_ip == "10.0.0.1"
    assert events[0].timestamp.startswith("2025-01-01 12:00:00")
    assert events[1].failure_mode == []
    assert events[1].timestamp.startswith("2025-01-01 12:00:05.7")
    assert len(session.executed) == 3


async def test_list_trace_failure_events_not_anomalous(monkeypatch):
    install_session(
        monkeypatch,
        FakeSession(
            responses=[
                FakeResult(rows=["log-1"]),
                FakeResult(rows=[0]),
                FakeResult(rows=[make_trace_row(failure_mode="")]),
            ]
        ),
    )
    req = ListTraceFailureEventResultRequest(kb_id="kb-1", is_anomalous=False)
    total, events = await LogFailureEventPGManager.list_trace_failure_events(req)
    assert total == 0 and len(events) == 1
    assert events[0].failure_mode == []


async def test_list_trace_failure_events_error(monkeypatch):
    install_session(
        monkeypatch,
        FakeSession(responses=[FakeResult(rows=["log-1"]), RuntimeError("boom")]),
    )
    req = ListTraceFailureEventResultRequest(kb_id="kb-1")
    assert await LogFailureEventPGManager.list_trace_failure_events(req) == (0, [])


async def test_list_log_failure_events_kb_without_logs(monkeypatch):
    install_session(monkeypatch, FakeSession(responses=[FakeResult(rows=[])]))
    req = ListLogFailureEventResultRequest(kb_id="kb-x")
    assert await LogFailureEventPGManager.list_log_failure_events(req) == (0, [])


async def test_list_log_failure_events_full(monkeypatch):
    rows = [
        make_log_failure_row(),
        # master：结果按 raw_text 去重，两行需不同 raw_text 才都会保留
        make_log_failure_row(
            id="row-2", failure_mode=None, timestamp=None, raw_text="raw-2"
        ),
    ]
    install_session(
        monkeypatch,
        FakeSession(
            responses=[
                FakeResult(rows=["log-1"]),
                FakeResult(rows=rows),
            ]
        ),
    )
    req = ListLogFailureEventResultRequest(
        kb_id="kb-1", log_id="log-2", trace_ids=["tr-1"]
    )
    total, events = await LogFailureEventPGManager.list_log_failure_events(req)
    assert total == 2
    # master：去重后按 timestamp 排序，timestamp=None（格式化为 ""）排最前
    assert events[0].id == "row-2"
    assert events[0].failure_mode == []
    assert events[0].timestamp == ""
    assert events[1].id == "row-1"
    assert events[1].failure_mode == ["mode_a", "mode_b"]


async def test_get_err_code_metrics_kb_without_logs(monkeypatch):
    install_session(monkeypatch, FakeSession(responses=[FakeResult(rows=[])]))
    req = GetErrCodeMetricsRequest(kb_id="kb-x")
    assert await LogFailureEventPGManager.get_err_code_metrics(req) == (0, {})


async def test_get_err_code_metrics_no_rows(monkeypatch):
    install_session(
        monkeypatch,
        FakeSession(responses=[FakeResult(rows=["log-1"]), FakeResult(rows=[])]),
    )
    req = GetErrCodeMetricsRequest(kb_id="kb-1")
    assert await LogFailureEventPGManager.get_err_code_metrics(req) == (0, {})


async def test_get_err_code_metrics_no_timestamps(monkeypatch):
    install_session(
        monkeypatch,
        FakeSession(
            responses=[
                FakeResult(rows=["log-1"]),
                FakeResult(rows=[make_trace_row(timestamp=None)]),
            ]
        ),
    )
    req = GetErrCodeMetricsRequest(kb_id="kb-1")
    assert await LogFailureEventPGManager.get_err_code_metrics(req) == (0, {})


async def test_get_err_code_metrics_basic(monkeypatch):
    # 无时间戳行跳过；status_code 为空串时按 UNKNOWN 计数
    rows = [
        make_trace_row(),
        make_trace_row(id="r-2", timestamp=None, status_code=[]),
        make_trace_row(id="r-3", status_code=[""], failure_mode="x"),
    ]
    install_session(
        monkeypatch,
        FakeSession(
            responses=[
                FakeResult(rows=["log-1"]),
                FakeResult(rows=rows),
            ]
        ),
    )
    req = GetErrCodeMetricsRequest(
        kb_id="kb-1",
        err_codes=["1004"],
        pod_names=["pod-1"],
        host_names=["host-1"],
        cluster_names=["cl-1"],
        src_ip="10.0.0.1",
        dst_ip="10.0.0.2",
        start_time="2025-01-01 11:00:00",
        end_time="2025-01-01 13:00:00",
        operation="GET",
    )
    total, result = await LogFailureEventPGManager.get_err_code_metrics(req)
    assert total == 1
    assert result["1004"] == [{"time": "2025-01-01 12:00:00", "err_cnt": 1}]
    assert result["UNKNOWN"] == [{"time": "2025-01-01 12:00:00", "err_cnt": 1}]


async def test_get_err_code_metrics_time_bounds(monkeypatch):
    # 12:00:05.7 落在 12:00:06 桶（±0.5s 窗口）
    row = make_trace_row(timestamp=datetime(2025, 1, 1, 12, 0, 5, 700000))
    install_session(
        monkeypatch,
        FakeSession(
            responses=[
                FakeResult(rows=["log-1"]),
                FakeResult(rows=[row]),
            ]
        ),
    )
    req = GetErrCodeMetricsRequest(
        kb_id="kb-1",
        start_time="2025-01-01 11:00:00",
        end_time="2025-01-01 13:00:00",
    )
    total, result = await LogFailureEventPGManager.get_err_code_metrics(req)
    assert total == 1
    assert result["1004"] == [{"time": "2025-01-01 12:00:06", "err_cnt": 1}]


async def test_get_err_code_metrics_sampling_peaks(monkeypatch):
    counts = [1, 5, 1, 5, 1, 5]
    rows = [
        make_trace_row(
            id=f"r-{i}",
            timestamp=DT + timedelta(seconds=i),
            status_code=["1004"] * cnt,
            failure_mode="mode_a",
        )
        for i, cnt in enumerate(counts)
    ]
    install_session(
        monkeypatch,
        FakeSession(
            responses=[
                FakeResult(rows=["log-1"]),
                FakeResult(rows=rows),
            ]
        ),
    )
    req = GetErrCodeMetricsRequest(kb_id="kb-1", max_points=2)
    total, result = await LogFailureEventPGManager.get_err_code_metrics(req)
    assert total == 2
    assert result["1004"] == [
        {"time": "2025-01-01 12:00:01", "err_cnt": 5},
        {"time": "2025-01-01 12:00:03", "err_cnt": 5},
    ]


async def test_get_err_code_metrics_sampling_fill(monkeypatch):
    counts = [1, 1, 5, 1, 1, 4]
    rows = [
        make_trace_row(
            id=f"r-{i}",
            timestamp=DT + timedelta(seconds=i),
            status_code=["1004"] * cnt,
            failure_mode="mode_a",
        )
        for i, cnt in enumerate(counts)
    ]
    install_session(
        monkeypatch,
        FakeSession(
            responses=[
                FakeResult(rows=["log-1"]),
                FakeResult(rows=rows),
            ]
        ),
    )
    req = GetErrCodeMetricsRequest(kb_id="kb-1", max_points=3)
    total, result = await LogFailureEventPGManager.get_err_code_metrics(req)
    assert total == 3
    assert result["1004"] == [
        {"time": "2025-01-01 12:00:00", "err_cnt": 1},
        {"time": "2025-01-01 12:00:02", "err_cnt": 5},
        {"time": "2025-01-01 12:00:05", "err_cnt": 4},
    ]


async def test_get_err_code_metrics_error(monkeypatch):
    install_session(
        monkeypatch,
        FakeSession(responses=[FakeResult(rows=["log-1"]), RuntimeError("boom")]),
    )
    req = GetErrCodeMetricsRequest(kb_id="kb-1")
    assert await LogFailureEventPGManager.get_err_code_metrics(req) == (0, {})


async def test_list_time_aggregated_kb_without_logs(monkeypatch):
    install_session(monkeypatch, FakeSession(responses=[FakeResult(rows=[])]))
    req = ListTimeAggregatedFailureEventRequest(kb_id="kb-x")
    assert await LogFailureEventPGManager.list_time_aggregated_failure_events(req) == (
        0,
        ["all"],
        [],
    )


async def test_list_time_aggregated_no_rows(monkeypatch):
    install_session(
        monkeypatch,
        FakeSession(responses=[FakeResult(rows=["log-1"]), FakeResult(rows=[])]),
    )
    req = ListTimeAggregatedFailureEventRequest(kb_id="kb-1")
    assert await LogFailureEventPGManager.list_time_aggregated_failure_events(req) == (
        0,
        ["all"],
        [],
    )


async def test_list_time_aggregated_full(monkeypatch):
    # "1004"/"abc" 混合码触发 sorted 回退；字符串 time_bucket 走 strptime 分支
    rows = [
        {"time_bucket": DT, "status_code": "1004", "cnt": 3},
        {"time_bucket": DT + timedelta(minutes=1), "status_code": "1009", "cnt": 2},
        {"time_bucket": "2025-01-01 12:02:00", "status_code": "abc", "cnt": 1},
    ]
    install_session(
        monkeypatch,
        FakeSession(
            responses=[FakeResult(rows=["log-1"]), FakeResult(rows=rows)]
        ),
    )
    req = ListTimeAggregatedFailureEventRequest(
        kb_id="kb-1",
        cluster_name="cl-1",
        host="host-1",
        pod_ip="pod-1",
        src_ip="10.0.0.1",
        dst_ip="10.0.0.2",
        start_time="2025-01-01 11:00:00",
        end_time="2025-01-01 13:00:00",
        interval="minute",
        operation="GET",
        sort_by="timestamp",
        sort_desc=False,
        page_cnt=2,
        page_num=2,
    )
    total, err_codes, results = (
        await LogFailureEventPGManager.list_time_aggregated_failure_events(req)
    )
    assert total == 3
    assert err_codes == ["all", "1004", "1009", "abc"]
    assert len(results) == 1
    assert results[0]["start_time"] == "2025-01-01 12:02:00"
    assert results[0]["end_time"] == "2025-01-01 12:03:00"
    assert results[0]["status_code_cnt"] == {"all": 1, "abc": 1}


async def test_list_time_aggregated_sort_fields(monkeypatch):
    rows = [
        {"time_bucket": DT, "status_code": "1004", "cnt": 1},
        {"time_bucket": DT + timedelta(minutes=1), "status_code": "1004", "cnt": 5},
    ]
    install_session(
        monkeypatch,
        FakeSession(
            responses=[FakeResult(rows=["log-1"]), FakeResult(rows=rows)]
        ),
    )
    req = ListTimeAggregatedFailureEventRequest(
        kb_id="kb-1",
        sort_fields=[
            SortField(field="weird", order="desc"),
            SortField(field="all", order="desc"),
            SortField(field="1004", order="asc"),
        ],
    )
    total, err_codes, results = (
        await LogFailureEventPGManager.list_time_aggregated_failure_events(req)
    )
    assert total == 2
    # reversed 应用：先按 1004 asc，再按 all desc，最终 all desc 为主键
    assert results[0]["start_time"] == "2025-01-01 12:01:00"
    assert results[0]["status_code_cnt"] == {"all": 5, "1004": 5}


async def test_list_time_aggregated_sort_by_all(monkeypatch):
    rows = [
        {"time_bucket": DT, "status_code": "1004", "cnt": 1},
        {"time_bucket": DT + timedelta(minutes=1), "status_code": "1004", "cnt": 5},
    ]
    install_session(
        monkeypatch,
        FakeSession(
            responses=[FakeResult(rows=["log-1"]), FakeResult(rows=rows)]
        ),
    )
    req = ListTimeAggregatedFailureEventRequest(kb_id="kb-1", sort_by="all", sort_desc=True)
    total, _, results = (
        await LogFailureEventPGManager.list_time_aggregated_failure_events(req)
    )
    assert total == 2
    assert results[0]["start_time"] == "2025-01-01 12:01:00"


async def test_list_time_aggregated_sort_by_code(monkeypatch):
    rows = [
        {"time_bucket": DT, "status_code": "1009", "cnt": 1},
        {"time_bucket": DT + timedelta(minutes=1), "status_code": "1004", "cnt": 1},
    ]
    install_session(
        monkeypatch,
        FakeSession(
            responses=[FakeResult(rows=["log-1"]), FakeResult(rows=rows)]
        ),
    )
    req = ListTimeAggregatedFailureEventRequest(kb_id="kb-1", sort_by="1009", sort_desc=True)
    total, _, results = (
        await LogFailureEventPGManager.list_time_aggregated_failure_events(req)
    )
    assert total == 2
    assert results[0]["start_time"] == "2025-01-01 12:00:00"


async def test_list_time_aggregated_error(monkeypatch):
    install_session(monkeypatch, FakeSession(responses=[RuntimeError("boom")]))
    req = ListTimeAggregatedFailureEventRequest(kb_id="kb-1")
    assert await LogFailureEventPGManager.list_time_aggregated_failure_events(req) == (
        0,
        ["all"],
        [],
    )


async def test_list_pod_aggregated_kb_without_logs(monkeypatch):
    install_session(monkeypatch, FakeSession(responses=[FakeResult(rows=[])]))
    req = ListPodAggregatedFailureEventRequest(kb_id="kb-x")
    assert await LogFailureEventPGManager.list_pod_aggregated_failure_events(req) == (0, [])


async def test_list_pod_aggregated_full(monkeypatch):
    rows = [
        {"pod_names": ["pod-1", " pod-2 ", ""], "status_code": "1004", "cnt": 2},
        {"pod_names": ["pod-1"], "status_code": "1009", "cnt": 1},
        {"pod_names": None, "status_code": "", "cnt": 5},
    ]
    install_session(
        monkeypatch,
        FakeSession(
            responses=[FakeResult(rows=["log-1"]), FakeResult(rows=rows)]
        ),
    )
    req = ListPodAggregatedFailureEventRequest(
        kb_id="kb-1",
        start_time="2025-01-01 11:00:00",
        end_time="2025-01-01 13:00:00",
        operation="GET",
    )
    total, results = await LogFailureEventPGManager.list_pod_aggregated_failure_events(req)
    assert total == 2
    assert results[0]["pod_name"] == "pod-1"
    assert results[0]["status_code_cnt"] == {"all": 3, "1004": 2, "1009": 1}
    assert results[1]["pod_name"] == "pod-2"
    assert results[1]["status_code_cnt"] == {"all": 2, "1004": 2}


async def test_list_pod_aggregated_sort_by_code(monkeypatch):
    rows = [
        {"pod_names": ["pod-1"], "status_code": "1004", "cnt": 1},
        {"pod_names": ["pod-2"], "status_code": "1009", "cnt": 1},
    ]
    install_session(
        monkeypatch,
        FakeSession(
            responses=[FakeResult(rows=["log-1"]), FakeResult(rows=rows)]
        ),
    )
    req = ListPodAggregatedFailureEventRequest(kb_id="kb-1", sort_by="1009")
    total, results = await LogFailureEventPGManager.list_pod_aggregated_failure_events(req)
    assert total == 2
    assert results[0]["pod_name"] == "pod-2"


async def test_list_pod_aggregated_sort_fields_pagination(monkeypatch):
    rows = [
        {"pod_names": ["pod-1"], "status_code": "1004", "cnt": 1},
        {"pod_names": ["pod-2"], "status_code": "1004", "cnt": 3},
    ]
    install_session(
        monkeypatch,
        FakeSession(
            responses=[FakeResult(rows=["log-1"]), FakeResult(rows=rows)]
        ),
    )
    req = ListPodAggregatedFailureEventRequest(
        kb_id="kb-1",
        sort_fields=[
            SortField(field="weird", order="desc"),
            SortField(field="1004", order="desc"),
        ],
        page_cnt=1,
        page_num=2,
    )
    total, results = await LogFailureEventPGManager.list_pod_aggregated_failure_events(req)
    assert total == 2
    assert len(results) == 1
    # desc 排序后 [pod-2(3), pod-1(1)]，第 2 页取 pod-1
    assert results[0]["pod_name"] == "pod-1"


async def test_list_pod_aggregated_error(monkeypatch):
    install_session(monkeypatch, FakeSession(responses=[RuntimeError("boom")]))
    req = ListPodAggregatedFailureEventRequest(kb_id="kb-1")
    assert await LogFailureEventPGManager.list_pod_aggregated_failure_events(req) == (0, [])


async def test_list_src_dst_aggregated_kb_without_logs(monkeypatch):
    install_session(monkeypatch, FakeSession(responses=[FakeResult(rows=[])]))
    req = ListSrcDstAggregatedFailureEventRequest(kb_id="kb-x")
    assert (
        await LogFailureEventPGManager.list_src_dst_aggregated_failure_events(req)
        == (0, [])
    )


async def test_list_src_dst_aggregated_full(monkeypatch):
    rows = [
        {"src_ip_str": "10.0.0.1", "dst_ip_str": "10.0.0.2", "status_code": "1004", "cnt": 2},
        {"src_ip_str": "10.0.0.1", "dst_ip_str": "10.0.0.2", "status_code": "1009", "cnt": 1},
        {"src_ip_str": "", "dst_ip_str": "", "status_code": "x1", "cnt": 1},
    ]
    install_session(
        monkeypatch,
        FakeSession(
            responses=[FakeResult(rows=["log-1"]), FakeResult(rows=rows)]
        ),
    )
    req = ListSrcDstAggregatedFailureEventRequest(
        kb_id="kb-1",
        cluster_name="cl-1",
        host="host-1",
        pod_ip="pod-1",
        src_ip="10.0.0.1",
        dst_ip="10.0.0.2",
        start_time="2025-01-01 11:00:00",
        end_time="2025-01-01 13:00:00",
        operation="GET",
    )
    total, results = (
        await LogFailureEventPGManager.list_src_dst_aggregated_failure_events(req)
    )
    assert total == 2
    assert results[0]["src_ip"] == "10.0.0.1"
    assert results[0]["dst_ip"] == "10.0.0.2"
    assert results[0]["status_code_cnt"] == {"all": 3, "1004": 2, "1009": 1}
    assert results[1]["src_ip"] == ""
    assert results[1]["status_code_cnt"] == {"all": 1, "x1": 1}


async def test_list_src_dst_aggregated_sort_by_code(monkeypatch):
    rows = [
        {"src_ip_str": "10.0.0.1", "dst_ip_str": "10.0.0.2", "status_code": "1004", "cnt": 1},
        {"src_ip_str": "10.0.0.3", "dst_ip_str": "10.0.0.4", "status_code": "1009", "cnt": 1},
    ]
    install_session(
        monkeypatch,
        FakeSession(
            responses=[FakeResult(rows=["log-1"]), FakeResult(rows=rows)]
        ),
    )
    req = ListSrcDstAggregatedFailureEventRequest(kb_id="kb-1", sort_by="1009")
    total, results = (
        await LogFailureEventPGManager.list_src_dst_aggregated_failure_events(req)
    )
    assert total == 2
    assert results[0]["src_ip"] == "10.0.0.3"


async def test_list_src_dst_aggregated_sort_fields_pagination(monkeypatch):
    rows = [
        {"src_ip_str": "10.0.0.1", "dst_ip_str": "10.0.0.2", "status_code": "1004", "cnt": 1},
        {"src_ip_str": "10.0.0.3", "dst_ip_str": "10.0.0.4", "status_code": "1004", "cnt": 3},
    ]
    install_session(
        monkeypatch,
        FakeSession(
            responses=[FakeResult(rows=["log-1"]), FakeResult(rows=rows)]
        ),
    )
    req = ListSrcDstAggregatedFailureEventRequest(
        kb_id="kb-1",
        sort_fields=[
            SortField(field="weird", order="desc"),
            SortField(field="1004", order="desc"),
        ],
        page_cnt=1,
        page_num=2,
    )
    total, results = (
        await LogFailureEventPGManager.list_src_dst_aggregated_failure_events(req)
    )
    assert total == 2
    assert len(results) == 1
    # desc 排序后 [10.0.0.3(3), 10.0.0.1(1)]，第 2 页取 10.0.0.1
    assert results[0]["src_ip"] == "10.0.0.1"


async def test_list_src_dst_aggregated_error(monkeypatch):
    install_session(monkeypatch, FakeSession(responses=[RuntimeError("boom")]))
    req = ListSrcDstAggregatedFailureEventRequest(kb_id="kb-1")
    assert (
        await LogFailureEventPGManager.list_src_dst_aggregated_failure_events(req)
        == (0, [])
    )


# ===========================================================================
# 2. log_parse_result
# ===========================================================================
async def test_add_log_parse_results_empty(monkeypatch):
    LogParseResultPGManager.last_store_metrics = {"stale": True}
    assert await LogParseResultPGManager.add_log_parse_results([]) is True
    assert LogParseResultPGManager.last_store_metrics == {}


async def test_add_log_parse_results_copy(monkeypatch):
    asyncpg = FakeAsyncpgConnection()
    install_connection(monkeypatch, FakeConnection(asyncpg))
    results = [
        make_parse_storage(id="r-0", total_latency=1.0),
        make_parse_storage(id="r-1", total_latency=2.0),
        make_parse_storage(id="r-2", total_latency=3.0),
    ]
    assert await LogParseResultPGManager.add_log_parse_results(results, batch_size=2) is True
    metrics = LogParseResultPGManager.last_store_metrics
    assert metrics["rows"] == 3
    assert metrics["batch_count"] == 2
    assert metrics["success"] is True
    assert len(asyncpg.copy_calls) == 2
    table, records, columns = asyncpg.copy_calls[0]
    assert table == "log_parse_result"
    assert columns == COPY_COLUMNS
    assert len(records) == 2
    assert records[0][0] == "r-0"
    assert records[0][5] == DT
    assert len(asyncpg.copy_calls[1][1]) == 1


async def test_add_log_parse_results_error(monkeypatch):
    asyncpg = FakeAsyncpgConnection(error=RuntimeError("copy failed"))
    install_connection(monkeypatch, FakeConnection(asyncpg))
    assert await LogParseResultPGManager.add_log_parse_results([make_parse_storage()]) is False
    metrics = LogParseResultPGManager.last_store_metrics
    assert metrics["success"] is False
    assert metrics["error"] == "copy failed"


async def test_add_log_parse_result_batches(monkeypatch):
    asyncpg = FakeAsyncpgConnection()
    install_connection(monkeypatch, FakeConnection(asyncpg))

    def batches():
        yield [make_parse_storage(id="b1-r1"), make_parse_storage(id="b1-r2")]
        yield []
        yield [make_parse_storage(id="b2-r1")]

    rows = await LogParseResultPGManager.add_log_parse_result_batches(batches())
    assert rows == 3
    metrics = LogParseResultPGManager.last_store_metrics
    assert metrics["rows"] == 3
    assert metrics["batch_count"] == 2
    assert metrics["success"] is True
    table, records, columns = asyncpg.copy_calls[0]
    assert table == "log_parse_result"
    assert columns == COPY_COLUMNS
    assert [r[0] for r in records] == ["b1-r1", "b1-r2", "b2-r1"]


async def test_add_log_parse_result_batches_error(monkeypatch):
    asyncpg = FakeAsyncpgConnection(error=RuntimeError("copy failed"))
    install_connection(monkeypatch, FakeConnection(asyncpg))

    def batches():
        yield [make_parse_storage(id="b1-r1")]
        yield [make_parse_storage(id="b2-r1")]

    with pytest.raises(RuntimeError):
        await LogParseResultPGManager.add_log_parse_result_batches(batches())
    assert LogParseResultPGManager.last_store_metrics["success"] is False
    assert LogParseResultPGManager.last_store_metrics["rows"] == 0


async def test_delete_and_update_log_parse_results(monkeypatch):
    session = install_session(monkeypatch, FakeSession())
    assert await LogParseResultPGManager.delete_by_log_id("log-1") is True
    assert await LogParseResultPGManager.delete_log_parse_results_by_log_id("log-1") is True
    assert (
        await LogParseResultPGManager.update_log_parse_results_existed_status_by_log_id(
            "log-1", 1
        )
        is True
    )
    sqls = [str(s) for s, _ in session.executed]
    assert (
        sqls[0]
        == "UPDATE log_parse_result SET existed_status = FALSE WHERE log_id = :log_id"
    )
    assert sqls[1] == sqls[0]
    assert "existed_status = :existed_status" in sqls[2]
    assert session.executed[2][1] == {"log_id": "log-1", "existed_status": True}


async def test_delete_latency_bucket_stats_by_log_id(monkeypatch):
    session = install_session(monkeypatch, FakeSession())
    assert await LogParseResultPGManager.delete_latency_bucket_stats_by_log_id("log-1") is True
    assert len(session.executed) == 4
    sqls = [str(s) for s, _ in session.executed]
    assert sqls[0] == "DELETE FROM latency_bucket_10s WHERE log_id = :log_id"
    assert sqls[1] == "DELETE FROM latency_bucket_1min WHERE log_id = :log_id"
    assert sqls[2] == "DELETE FROM latency_bucket_10min WHERE log_id = :log_id"
    assert sqls[3] == "DELETE FROM latency_bucket_1h WHERE log_id = :log_id"


async def test_list_anomalous_trace_ids(monkeypatch):
    session = install_session(
        monkeypatch, FakeSession(stream_rows=[("t1 ",), ("",), ("t2",)])
    )
    result = await LogParseResultPGManager.list_anomalous_trace_ids_by_log_id("log-1")
    assert result == {"t1", "t2"}
    assert len(session.streamed) == 1


def test_build_stats_select_exprs():
    exprs = LogParseResultPGManager._build_stats_select_exprs(["total_latency"])
    names = [getattr(e, "name", None) for e in exprs]
    assert names == [
        "cnt",
        "ave_total_latency",
        "min_total_latency",
        "max_total_latency",
        "p95_total_latency",
        "p99_total_latency",
        "p9999_total_latency",
    ]


async def test_get_src_dst_aggregates(monkeypatch):
    mapping = {
        "log_id": "log-1",
        "src_ip": "10.0.0.1",
        "dst_ip": "10.0.0.2",
        "anomaly_cnt": 2,
        "ave_total_latency": 1.0,
        "p99_total_latency": 2.0,
    }
    install_session(
        monkeypatch, FakeSession(responses=[FakeResult(rows=[FakeRow(mapping)])])
    )
    rows = await LogParseResultPGManager.get_src_dst_aggregates("log-1", ["total_latency"])
    assert rows == [mapping]
    # field_names 传空列表回退默认字段 + 空结果
    install_session(monkeypatch, FakeSession(responses=[FakeResult(rows=[])]))
    assert await LogParseResultPGManager.get_src_dst_aggregates("log-1") == []


async def test_get_time_window_aggregates(monkeypatch):
    mapping = {
        "log_id": "log-1",
        "src_ip": None,
        "dst_ip": None,
        "time_bucket": DT,
        "anomaly_cnt": 0,
        "cnt": 1,
    }
    install_session(
        monkeypatch, FakeSession(responses=[FakeResult(rows=[FakeRow(mapping)])])
    )
    rows = await LogParseResultPGManager.get_time_window_aggregates(
        "log-1", "2025-01-01 11:00:00", "2025-01-01 13:00:00", None
    )
    assert rows == [mapping]


async def test_get_latency_metrics_curve(monkeypatch):
    mapping = {"time": DT, "cnt": 2, "total_latency": 1.5}
    install_session(
        monkeypatch, FakeSession(responses=[FakeResult(rows=[FakeRow(mapping)])])
    )
    rows = await LogParseResultPGManager.get_latency_metrics_curve(
        "log-1", "total_latency", "avg", "2025-01-01 11:00:00", "2025-01-01 13:00:00"
    )
    assert rows == [mapping]
    # max 模式 + 无时间边界
    install_session(
        monkeypatch, FakeSession(responses=[FakeResult(rows=[FakeRow(mapping)])])
    )
    assert (
        await LogParseResultPGManager.get_latency_metrics_curve(
            "log-1", "total_latency", "max"
        )
        == [mapping]
    )
    # 未知模式回退 p99
    install_session(monkeypatch, FakeSession(responses=[FakeResult(rows=[])]))
    assert (
        await LogParseResultPGManager.get_latency_metrics_curve(
            "log-1", "total_latency", "bogus"
        )
        == []
    )


async def test_list_log_parse_results_full(monkeypatch):
    rows = [
        make_log_parse_result_row(),
        make_log_parse_result_row(id="r-2", src_ip=None, timestamp=None),
    ]
    session = install_session(
        monkeypatch,
        FakeSession(responses=[FakeResult(rows=[5]), FakeResult(rows=rows)]),
    )
    req = ListLogParseResultRequest(
        kb_id="kb-1",
        log_id="log-1",
        aggregated_event_id="agg-1",
        trace_id="tr-1",
        trace_ids=["tr-1", "tr-2"],
        src_ip="10.0.0.",
        dst_ip="",
        pod_ip="pod-1",
        host="host",
        cluster_name="cl-1",
        is_anomalous=True,
        start_time="2025-01-01 11:00:00",
        end_time="2025-01-01 13:00:00",
        created_at_start="2025-01-01 11:00:00",
        created_at_end="2025-01-01 13:00:00",
        operation="SET",
        sort_fields=[
            SortField(field="total_latency", order="asc"),
            SortField(field="weird", order="desc"),
        ],
        page_cnt=10,
        page_num=1,
    )
    total, results = await LogParseResultPGManager.list_log_parse_results(req)
    assert total == 5
    assert len(results) == 2
    assert results[0].id == "r-1"
    assert results[0].src_ip == "10.0.0.1"
    assert results[0].timestamp.startswith("2025-01-01 12:00:00")
    assert results[1].src_ip is None
    assert results[1].timestamp is None
    assert len(session.executed) == 2


async def test_list_log_parse_results_get_operation(monkeypatch):
    install_session(
        monkeypatch,
        FakeSession(responses=[FakeResult(rows=[0]), FakeResult(rows=[])]),
    )
    req = ListLogParseResultRequest(kb_id="kb-1", operation="GET")
    total, results = await LogParseResultPGManager.list_log_parse_results(req)
    assert total == 0 and results == []


async def test_get_log_parse_result_by_id(monkeypatch):
    install_session(
        monkeypatch,
        FakeSession(responses=[FakeResult(rows=[make_log_parse_result_row()])]),
    )
    model = await LogParseResultPGManager.get_log_parse_result_by_id("r-1")
    assert model is not None
    assert model.id == "r-1"
    assert model.src_ip == "10.0.0.1"
    assert model.timestamp.startswith("2025-01-01 12:00:00")

    install_session(monkeypatch, FakeSession(responses=[FakeResult(rows=[])]))
    assert await LogParseResultPGManager.get_log_parse_result_by_id("missing") is None


async def test_list_traces_by_host(monkeypatch):
    def make_trace_mapping(**overrides):
        data = {
            "id": "r-1",
            "trace_id": "tr-1",
            "pod_ips": ["pod-1"],
            "cluster_name": "cl-1",
            "host": "host-1",
            "time": DT,
            "operation": "GET",
            "total_latency": 9.0,
            "urma_total_latency": 3.0,
            "c2w_latency": 1.0,
            "worker_query_meta_latency": 2.0,
            "w2w_urma_latency": 7.0,
            "is_anomalous": True,
            "anomaly_reason": "reason",
            "req_delay_ms": 1.0,
            "rsp_delay_ms": 8.0,
            "sdk_ms": 9.0,
            "pod_id": ["pod-1"],
        }
        data.update(overrides)
        return data

    rows = [
        make_trace_mapping(),
        make_trace_mapping(id="r-2", pod_id=None, time=None),
    ]
    install_session(
        monkeypatch,
        FakeSession(responses=[FakeResult(rows=[2]), FakeResult(rows=rows)]),
    )
    req = ListTracesByHostRequest(
        host="host-1",
        kb_id="kb-1",
        start_time="2025-01-01 11:00:00",
        end_time="2025-01-01 13:00:00",
        operation="GET",
        is_anomalous=True,
        sort_by="timestamp",
        sort_order="desc",
    )
    total, results = await LogParseResultPGManager.list_traces_by_host(req)
    assert total == 2 and len(results) == 2
    assert results[0]["pod_id"] == "pod-1"
    assert results[0]["time"].startswith("2025-01-01 12:00:00")
    assert results[1]["pod_id"] == ""
    assert results[1]["time"] is None

    # SET 过滤分支 + 无效 sort_by 回退 timestamp
    install_session(
        monkeypatch,
        FakeSession(responses=[FakeResult(rows=[0]), FakeResult(rows=[])]),
    )
    req_set = ListTracesByHostRequest(
        host="h", kb_id="kb-1", operation="SET", sort_by="weird", sort_order="asc"
    )
    assert await LogParseResultPGManager.list_traces_by_host(req_set) == (0, [])


def test_has_ip_dimension_filters():
    from latency.database.managers.log_parse_result import _has_ip_dimension_filters

    def req(**kw):
        base = dict(cluster_name=None, host=None, pod_ip=None, src_ip=None, dst_ip=None)
        base.update(kw)
        return SimpleNamespace(**base)

    assert _has_ip_dimension_filters(req()) is False
    assert _has_ip_dimension_filters(req(src_ip="")) is False
    assert _has_ip_dimension_filters(req(cluster_name="cl")) is True
    assert _has_ip_dimension_filters(req(host="h")) is True
    assert _has_ip_dimension_filters(req(pod_ip="p")) is True
    assert _has_ip_dimension_filters(req(src_ip="10.0.0.1")) is True
    assert _has_ip_dimension_filters(req(dst_ip="10.0.0.2")) is True


async def test_get_latency_metrics_guards(monkeypatch):
    with pytest.raises(BadRequestBizException):
        req = GetLatencyMetricsRequest(kb_id="kb-1", bucket_seconds=30, log_id="log-1")
        await LogParseResultPGManager.get_latency_metrics(req)
    with pytest.raises(BadRequestBizException):
        req = GetLatencyMetricsRequest(
            kb_id="kb-1", bucket_seconds=60, sample_mode=SampleMode.MIN, log_id="log-1"
        )
        await LogParseResultPGManager.get_latency_metrics(req)
    with pytest.raises(BadRequestBizException):
        req = GetLatencyMetricsRequest(
            kb_id="kb-1", bucket_seconds=60, log_id="log-1", host="host-1"
        )
        await LogParseResultPGManager.get_latency_metrics(req)
    # master：缺少 log_id 直接 400（时延曲线按单个日志文件查询）
    req = GetLatencyMetricsRequest(kb_id="kb-1", bucket_seconds=60)
    with pytest.raises(BadRequestBizException):
        await LogParseResultPGManager.get_latency_metrics(req)


async def test_get_latency_metrics_happy(monkeypatch):
    row = SimpleNamespace(
        bucket=DT,
        src_ip="10.0.0.1",
        dst_ip="10.0.0.2",
        trace_id="tr-1",
        request_mode="mode",
    )
    install_session(monkeypatch, FakeSession(responses=[FakeResult(rows=[row])]))
    req = GetLatencyMetricsRequest(
        kb_id="kb-1",
        log_id="log-1",
        bucket_seconds=10,
        sample_mode=SampleMode.AVG,
        operation="GET",
        start_time="2025-01-01 11:00:00",
        end_time="2025-01-01 13:00:00",
    )
    total, rows = await LogParseResultPGManager.get_latency_metrics(req)
    assert total == 1 and len(rows) == 1
    assert rows[0]["time"].startswith("2025-01-01 12:00:00")
    assert rows[0]["src_ip"] == "10.0.0.1"
    assert rows[0]["dst_ip"] == "10.0.0.2"
    assert rows[0]["trace_id"] == "tr-1"
    assert rows[0]["total_latency"] is None
    assert rows[0]["urma_inflight_max"] is None
    assert rows[0]["request_mode"] == "mode"


async def test_get_cluster_and_host_list(monkeypatch):
    install_session(monkeypatch, FakeSession(responses=[FakeResult(rows=["cl-1", ""])]))
    assert await LogParseResultPGManager.get_cluster_list("kb-1") == ["cl-1"]
    install_session(monkeypatch, FakeSession(responses=[FakeResult(rows=["host-1"])]))
    assert await LogParseResultPGManager.get_host_list() == ["host-1"]


# ===========================================================================
# 3. time_window_aggregated_event
# ===========================================================================
def make_tw_event(**overrides):
    data = dict(
        id="tw-1",
        kb_id="kb-1",
        log_id="log-1",
        time_bucket="2025-01-01 12:00:00",
        src_ip="10.0.0.1",
        dst_ip="10.0.0.2",
        operation="GET",
        log_parse_result_cnt=10,
        anomaly_cnt=2,
        ave_total_latency=5.0,
        latency_sum=50.0,
        min_total_latency=1.0,
        max_total_latency=9.0,
        p95_total_latency=8.0,
        p99_total_latency=9.5,
    )
    data.update(overrides)
    return TimeWindowAggregatedEventDataclass(**data)


def make_tw_list_row(**overrides):
    data = dict(
        bucket_epoch=BASE_EPOCH,
        src_ip="10.0.0.1",
        dst_ip="10.0.0.2",
        total_cnt=1,
        anomaly_cnt=1,
        ave=1.0,
        min_lat=1.0,
        max_lat=1.0,
        p95=1.0,
        p99=1.0,
    )
    data.update(overrides)
    return SimpleNamespace(**data)


def test_event_to_mapping_and_copy_tuple():
    event = make_tw_event()
    mapping = TimeWindowAggregatedEventPGManager._event_to_mapping(event)
    assert mapping["id"] == "tw-1"
    assert mapping["time_bucket"] == DT
    assert mapping["src_ip"] == ipaddress.ip_address("10.0.0.1")
    assert mapping["operation"] == "GET"
    assert mapping["existed_status"] is True
    tup = TimeWindowAggregatedEventPGManager._event_to_copy_tuple(event)
    assert tup[0] == "tw-1"
    assert tup[1] == DT
    assert tup[16] is not None
    # created_at 为空时兜底 datetime.now()
    tup2 = TimeWindowAggregatedEventPGManager._event_to_copy_tuple(
        make_tw_event(created_at="")
    )
    assert tup2[16] is not None


async def test_add_events_empty():
    assert await TimeWindowAggregatedEventPGManager.add_events([]) == []


async def test_add_events_insert(monkeypatch):
    calls = []

    async def fake_ensure(start, end):
        calls.append((start, end))

    monkeypatch.setattr(tw_manager_module, "ensure_time_window_partitions", fake_ensure)
    conn = install_connection(monkeypatch, FakeConnection())
    events = [
        make_tw_event(id="tw-1"),
        make_tw_event(id="tw-2", time_bucket="2025-01-01 12:10:00"),
    ]
    ids = await TimeWindowAggregatedEventPGManager.add_events(events)
    assert ids == ["tw-1", "tw-2"]
    assert calls and calls[0][0] == DT
    stmt, params = conn.executed[0]
    assert str(stmt).startswith("INSERT INTO time_window_aggregated")
    assert len(params) == 2
    assert params[0]["id"] == "tw-1"
    assert params[0]["time_bucket"] == DT


async def test_add_events_insert_without_valid_bucket(monkeypatch):
    calls = []

    async def fake_ensure(start, end):
        calls.append((start, end))

    monkeypatch.setattr(tw_manager_module, "ensure_time_window_partitions", fake_ensure)
    conn = install_connection(monkeypatch, FakeConnection())
    ids = await TimeWindowAggregatedEventPGManager.add_events(
        [make_tw_event(id="tw-1", time_bucket="")]
    )
    assert ids == ["tw-1"]
    assert calls == []
    assert len(conn.executed) == 1


async def test_add_events_copy(monkeypatch):
    async def fake_ensure(start, end):
        return None

    monkeypatch.setattr(tw_manager_module, "ensure_time_window_partitions", fake_ensure)
    asyncpg = FakeAsyncpgConnection()
    install_connection(monkeypatch, FakeConnection(asyncpg))
    events = [make_tw_event(id=f"tw-{i}") for i in range(1000)]
    ids = await TimeWindowAggregatedEventPGManager.add_events(events)
    assert len(ids) == 1000
    assert ids[0] == "tw-0"
    table, records, columns = asyncpg.copy_calls[0]
    assert table == "time_window_aggregated"
    assert len(records) == 1000
    assert columns == TimeWindowAggregatedEventPGManager._TIME_WINDOW_COPY_COLUMNS
    assert records[0][0] == "tw-0"


async def test_delete_time_window_events(monkeypatch):
    conn = install_connection(monkeypatch, FakeConnection())
    assert await TimeWindowAggregatedEventPGManager.delete_by_log_id("log-1") is True
    assert await TimeWindowAggregatedEventPGManager.delete_by_kb_id("kb-1") is True
    sqls = [str(s) for s, _ in conn.executed]
    assert "UPDATE time_window_aggregated SET existed_status = FALSE" in sqls[0]
    assert "WHERE log_id = :log_id" in sqls[0]
    assert "WHERE kb_id = :kb_id" in sqls[1]


def test_format_ip_helper():
    fmt = TimeWindowAggregatedEventPGManager._format_ip
    assert fmt("10.0.0.1") == "10.0.0.1"
    assert fmt(None) == ""
    assert fmt(ipaddress.ip_address("10.0.0.1")) == "10.0.0.1"


def test_normalize_interval():
    normalize = TimeWindowAggregatedEventPGManager._normalize_interval
    assert normalize("second") == 10
    assert normalize("MINUTE") == 60
    assert normalize("hour") == 3600
    assert normalize("weird") == 60
    assert normalize(10) == 10
    assert normalize(600) == 600
    assert normalize(30) == 10
    assert normalize(5000) == 3600
    assert normalize(None) == 60


def test_epoch_to_str():
    result = TimeWindowAggregatedEventPGManager._epoch_to_str(BASE_EPOCH)
    assert result == "2025-01-01 00:00:00"


async def test_get_time_window_events(monkeypatch):
    mapping = {
        "log_id": "log-1",
        "src_ip": "10.0.0.1",
        "dst_ip": None,
        "time_bucket": DT,
        "log_parse_result_cnt": 5,
        "anomaly_cnt": 1,
    }
    install_session(
        monkeypatch, FakeSession(responses=[FakeResult(rows=[FakeRow(mapping)])])
    )
    rows = await TimeWindowAggregatedEventPGManager.get_time_window_events(
        "log-1",
        kb_id="kb-1",
        start_time="2025-01-01 11:00:00",
        end_time="2025-01-01 13:00:00",
        src_ip="10.0.0.1",
        dst_ip="10.0.0.2",
        cluster_name="cl-1",
        host="host-1",
        pod_ip="pod-1",
        operation="GET",
    )
    assert rows[0]["src_ip"] == "10.0.0.1"
    assert rows[0]["dst_ip"] == ""
    assert rows[0]["log_parse_result_cnt"] == 5
    # SET 过滤分支 + 空结果
    install_session(monkeypatch, FakeSession(responses=[FakeResult(rows=[])]))
    assert (
        await TimeWindowAggregatedEventPGManager.get_time_window_events(
            "log-1", operation="SET"
        )
        == []
    )


def test_rows_to_events_sorting():
    rows = [
        make_tw_list_row(bucket_epoch=100, total_cnt=5, anomaly_cnt=1, ave=1.0),
        make_tw_list_row(bucket_epoch=200, total_cnt=50, anomaly_cnt=9, ave=2.0),
    ]
    # 默认按 start_time 升序
    req = ListTimeWindowAggregatedEventRequest(kb_id="kb-1")
    total, events = TimeWindowAggregatedEventPGManager._rows_to_events(rows, 10, req)
    assert total == 2
    assert events[0]["start_time"] == "1970-01-01 00:01:40"
    assert events[1]["start_time"] == "1970-01-01 00:03:20"
    # sort_fields 优先，且分页
    req = ListTimeWindowAggregatedEventRequest(
        kb_id="kb-1",
        sort_fields=[SortField(field="total_cnt", order="desc")],
        page_cnt=1,
        page_num=1,
    )
    total, events = TimeWindowAggregatedEventPGManager._rows_to_events(rows, 10, req)
    assert total == 2 and len(events) == 1
    assert events[0]["total_cnt"] == 50
    # anomaly_cnt 排序 + 分页第 2 页
    req = ListTimeWindowAggregatedEventRequest(
        kb_id="kb-1", sort_by="anomaly_cnt", sort_order="desc", page_cnt=1, page_num=2
    )
    total, events = TimeWindowAggregatedEventPGManager._rows_to_events(rows, 10, req)
    assert total == 2 and len(events) == 1
    assert events[0]["anomaly_cnt"] == 1
    # 未知排序字段回退 0
    req = ListTimeWindowAggregatedEventRequest(kb_id="kb-1", sort_by="weird")
    total, events = TimeWindowAggregatedEventPGManager._rows_to_events(rows, 10, req)
    assert total == 2


async def test_list_time_window_events_full(monkeypatch):
    p99s = {
        f"p99_{name}": 1.5
        for name in YUANRONG_METRIC_FIELDS
        if name != "request_mode"
    }
    rows = [
        make_tw_list_row(total_cnt=10, anomaly_cnt=2, ave=5.0, min_lat=1.0, max_lat=9.0, p95=8.0, p99=9.5),
        make_tw_list_row(total_cnt=2, anomaly_cnt=0, ave=None, min_lat=None, max_lat=None, p95=None, p99=None),
        make_tw_list_row(
            dst_ip="10.0.0.3", total_cnt=5, anomaly_cnt=1, ave=2.0, min_lat=0.5, max_lat=3.0, p95=2.5, p99=3.0
        ),
        make_tw_list_row(bucket_epoch=BASE_EPOCH + 600, total_cnt=1, anomaly_cnt=1, ave=4.0),
    ]
    pair_rows = [
        SimpleNamespace(bucket_epoch=BASE_EPOCH, src_ip="10.0.0.1", dst_ip="10.0.0.2", **p99s),
        SimpleNamespace(bucket_epoch=BASE_EPOCH, src_ip="9.9.9.9", dst_ip="8.8.8.8", **p99s),
        SimpleNamespace(bucket_epoch=BASE_EPOCH + 99999, src_ip="10.0.0.1", dst_ip="10.0.0.2", **p99s),
    ]
    parent_rows = [
        SimpleNamespace(bucket_epoch=BASE_EPOCH, **p99s),
        SimpleNamespace(bucket_epoch=BASE_EPOCH + 99999, **p99s),
    ]
    session = install_session(
        monkeypatch,
        FakeSession(
            responses=[
                FakeResult(rows=rows),
                FakeResult(rows=pair_rows),
                FakeResult(rows=parent_rows),
            ]
        ),
    )
    req = ListTimeWindowAggregatedEventRequest(
        kb_id="kb-1",
        cluster_name="cl-1",
        host="host-1",
        pod_ip="pod-1",
        start_time="2025-01-01 00:00:00",
        end_time="2025-01-02 00:00:00",
        src_ip="10.0.0.",
        dst_ip="10.0.0.",
        operation="GET",
        interval=600,
        sort_by="start_time",
        sort_order="asc",
        page_cnt=10,
        page_num=1,
    )
    total, events = await TimeWindowAggregatedEventPGManager.list_time_window_events(req)
    assert total == 2 and len(events) == 2
    first = events[0]
    assert first["start_time"] == "2025-01-01 00:00:00"
    assert first["end_time"] == "2025-01-01 00:10:00"
    assert first["total_cnt"] == 17
    assert first["anomaly_cnt"] == 3
    assert abs(first["ave_total_latency"] - 4.0) < 1e-9
    assert first["min_total_latency"] == 0.5
    assert first["max_total_latency"] == 9.0
    assert first["p99_total_latency"] == 9.5
    assert first["p99_total_latency_us"] == 1.5
    assert len(first["ip_pairs"]) == 2
    pair = first["ip_pairs"][0]
    assert pair["src_ip"] == "10.0.0.1" and pair["dst_ip"] == "10.0.0.2"
    assert pair["log_parse_result_cnt"] == 12
    assert abs(pair["ave_total_latency"] - 5.0) < 1e-9
    assert pair["p99_total_latency"] == 9.5
    assert pair["p99_total_latency_us"] == 1.5
    assert events[1]["total_cnt"] == 1
    assert len(session.executed) == 3


async def test_list_time_window_events_set_operation(monkeypatch):
    rows = [make_tw_list_row()]
    install_session(
        monkeypatch,
        FakeSession(
            responses=[
                FakeResult(rows=rows),
                FakeResult(rows=[]),
                FakeResult(rows=[]),
            ]
        ),
    )
    req = ListTimeWindowAggregatedEventRequest(kb_id="kb-1", operation="SET")
    total, events = await TimeWindowAggregatedEventPGManager.list_time_window_events(req)
    assert total == 1 and len(events) == 1
    assert events[0]["total_cnt"] == 1


async def test_list_time_window_events_empty(monkeypatch):
    session = install_session(monkeypatch, FakeSession(responses=[FakeResult(rows=[])]))
    req = ListTimeWindowAggregatedEventRequest(kb_id="kb-1")
    total, events = await TimeWindowAggregatedEventPGManager.list_time_window_events(req)
    assert total == 0 and events == []
    assert len(session.executed) == 1


# ===========================================================================
# 4. src_dst_aggregated_event
# ===========================================================================
def make_src_dst_event(**overrides):
    data = dict(
        id="a-1",
        kb_id="kb-1",
        src_ip="10.0.0.1",
        dst_ip="10.0.0.2",
        operation="GET",
        log_id="log-1",
        log_parse_result_cnt=3,
        anomaly_log_parse_result_cnt=1,
        anomaly_cnt=1,
    )
    data.update(overrides)
    return SrcDstAggregatedEventDataclass(**data)


def test_src_dst_format_row():
    row = {"src_ip": "10.0.0.1", "dst_ip": None, "other": 1}
    out = SrcDstAggregatedEventPGManager._format_row(row)
    assert out["src_ip"] == "10.0.0.1"
    assert out["dst_ip"] == ""
    assert out["other"] == 1


def test_src_dst_event_to_mapping_and_copy_tuple():
    event = make_src_dst_event()
    mapping = SrcDstAggregatedEventPGManager._event_to_mapping(event)
    assert mapping["id"] == "a-1"
    assert mapping["kb_id"] == "kb-1"
    assert mapping["src_ip"] == ipaddress.ip_address("10.0.0.1")
    assert mapping["operation"] == "GET"
    assert mapping["existed_status"] is True
    tup = SrcDstAggregatedEventPGManager._event_to_copy_tuple(event)
    assert tup[0] == "a-1"
    assert tup[10] is not None
    tup2 = SrcDstAggregatedEventPGManager._event_to_copy_tuple(
        make_src_dst_event(created_at="")
    )
    assert tup2[10] is None


async def test_add_aggregated_events_empty(monkeypatch):
    conn = install_connection(monkeypatch, FakeConnection())
    await SrcDstAggregatedEventPGManager.add_aggregated_events([])
    assert conn.executed == []


async def test_add_aggregated_events_insert(monkeypatch):
    conn = install_connection(monkeypatch, FakeConnection())
    events = [make_src_dst_event(id="a-1"), make_src_dst_event(id="a-2")]
    await SrcDstAggregatedEventPGManager.add_aggregated_events(events)
    stmt, params = conn.executed[0]
    assert str(stmt).startswith("INSERT INTO src_dst_aggregated_event")
    assert len(params) == 2
    assert params[0]["id"] == "a-1"


async def test_add_aggregated_events_copy(monkeypatch):
    asyncpg = FakeAsyncpgConnection()
    install_connection(monkeypatch, FakeConnection(asyncpg))
    events = [make_src_dst_event(id=f"a-{i}") for i in range(1000)]
    await SrcDstAggregatedEventPGManager.add_aggregated_events(events)
    table, records, columns = asyncpg.copy_calls[0]
    assert table == "src_dst_aggregated_event"
    assert len(records) == 1000
    assert columns == SrcDstAggregatedEventPGManager._COPY_COLUMNS
    assert records[0][0] == "a-0"


def test_stat_expr_and_stats_columns():
    from latency.database.models import LogParseResult

    expr = SrcDstAggregatedEventPGManager._stat_expr
    assert expr(LogParseResult.total_latency, "p95") is not None
    assert expr(LogParseResult.total_latency, "p99") is not None
    assert expr(LogParseResult.total_latency, "ave") is not None
    assert expr(LogParseResult.total_latency, "max") is not None
    cols = SrcDstAggregatedEventPGManager._stats_columns(
        {"total_latency": LogParseResult.total_latency}
    )
    assert sorted(c.name for c in cols) == sorted(
        [
            "ave_total_latency",
            "min_total_latency",
            "max_total_latency",
            "p95_total_latency",
            "p99_total_latency",
        ]
    )


def test_build_stats_subquery():
    req = ListSrcDstAggregatedEventRequest(
        kb_id="kb-1",
        log_id="log-1",
        cluster_name="cl-1",
        host="host-1",
        pod_ip="pod-1",
        src_ip="10.0.0.",
        dst_ip="10.0.0.",
        start_time="2025-01-01 11:00:00",
        end_time="2025-01-01 13:00:00",
        operation="GET",
    )
    subq = SrcDstAggregatedEventPGManager._build_stats_subquery(req)
    col_names = {c.name for c in subq.columns}
    assert "ave_total_latency" in col_names
    assert "anomaly_cnt" in col_names
    assert "operation" in col_names
    # SET 过滤分支
    req_set = ListSrcDstAggregatedEventRequest(kb_id="", log_id="log-1", operation="SET")
    assert SrcDstAggregatedEventPGManager._build_stats_subquery(req_set) is not None


async def test_list_aggregated_events_kb_fastpath(monkeypatch):
    agg_rows = [make_src_dst_agg_row()]
    session = install_session(
        monkeypatch,
        FakeSession(responses=[FakeResult(rows=[3]), FakeResult(rows=agg_rows)]),
    )
    req = ListSrcDstAggregatedEventRequest(kb_id="kb-1", operation="GET")
    total, out = await SrcDstAggregatedEventPGManager.list_aggregated_events(req)
    assert total == 3
    assert out[0]["id"] == "a-1"
    assert out[0]["src_ip"] == "10.0.0.1"
    assert out[0]["dst_ip"] == "10.0.0.2"
    assert out[0]["operation"] == "GET"
    assert out[0]["created_at"].startswith("2025-01-01 12:00:00")
    assert out[0]["ave_total_latency"] is None
    assert len(session.executed) == 2
    assert session.get_calls == []

    # SET 过滤分支
    install_session(
        monkeypatch,
        FakeSession(responses=[FakeResult(rows=[0]), FakeResult(rows=[])]),
    )
    req_set = ListSrcDstAggregatedEventRequest(kb_id="kb-1", operation="SET")
    assert await SrcDstAggregatedEventPGManager.list_aggregated_events(req_set) == (0, [])


async def test_list_aggregated_events_log_file_fastpath(monkeypatch):
    from latency.database.models import LogFile

    def get_handler(row_type, key):
        assert key == "log-1"
        return SimpleNamespace(kb_id="kb-2")

    session = install_session(
        monkeypatch,
        FakeSession(
            get_handler=get_handler,
            responses=[FakeResult(rows=[1]), FakeResult(rows=[make_src_dst_agg_row()])],
        ),
    )
    req = ListSrcDstAggregatedEventRequest(kb_id="", log_id="log-1")
    total, out = await SrcDstAggregatedEventPGManager.list_aggregated_events(req)
    # 请求的 kb_id 被改写为日志文件所属知识库
    assert req.kb_id == "kb-2"
    assert total == 1
    assert out[0]["id"] == "a-1"
    assert session.get_calls and session.get_calls[0][0] is LogFile


async def test_list_aggregated_events_subquery(monkeypatch):
    mapping = make_src_dst_stats_mapping()
    session = install_session(
        monkeypatch,
        FakeSession(
            responses=[FakeResult(rows=[2]), FakeResult(rows=[FakeRow(mapping)])]
        ),
    )
    req = ListSrcDstAggregatedEventRequest(
        kb_id="kb-1",
        log_id="log-1",
        src_ip="10.0.0.",
        dst_ip="10.0.0.",
        stat_type="max",
        sort_fields=[
            SortField(field="total_latency", order="asc"),
            SortField(field="weird", order="desc"),
        ],
        page_cnt=10,
        page_num=1,
    )
    total, out = await SrcDstAggregatedEventPGManager.list_aggregated_events(req)
    assert total == 2
    assert out[0]["id"] == "a-1"
    assert out[0]["src_ip"] == "10.0.0.1"
    assert out[0]["operation"] == "GET"
    assert out[0]["ave_total_latency"] == 1.0
    assert out[0]["max_total_latency"] == 1.0
    assert out[0]["created_at"].startswith("2025-01-01 12:00:00")
    assert len(session.executed) == 2

    # 非法 stat_type 回退 ave
    install_session(
        monkeypatch,
        FakeSession(responses=[FakeResult(rows=[0]), FakeResult(rows=[])]),
    )
    req_bogus = ListSrcDstAggregatedEventRequest(
        kb_id="kb-1", log_id="log-1", stat_type="bogus"
    )
    assert await SrcDstAggregatedEventPGManager.list_aggregated_events(req_bogus) == (0, [])


async def test_get_aggregated_event_by_id_not_found(monkeypatch):
    session = install_session(monkeypatch, FakeSession())
    assert await SrcDstAggregatedEventPGManager.get_aggregated_event_by_id("missing") is None
    assert session.get_calls and session.get_calls[0][1] == "missing"


async def test_get_aggregated_event_by_id_deleted(monkeypatch):
    install_session(
        monkeypatch,
        FakeSession(
            get_handler=lambda row_type, key: SimpleNamespace(existed_status=False)
        ),
    )
    assert await SrcDstAggregatedEventPGManager.get_aggregated_event_by_id("a-1") is None


async def test_get_aggregated_event_by_id_no_stats(monkeypatch):
    agg = SimpleNamespace(
        id="a-1",
        log_id="log-1",
        src_ip="10.0.0.1",
        dst_ip="10.0.0.2",
        existed_status=True,
        created_at=DT,
    )
    install_session(
        monkeypatch,
        FakeSession(
            get_handler=lambda row_type, key: agg,
            responses=[FakeResult(rows=[])],
        ),
    )
    assert await SrcDstAggregatedEventPGManager.get_aggregated_event_by_id("a-1") is None


async def test_get_aggregated_event_by_id_found(monkeypatch):
    agg = SimpleNamespace(
        id="a-1",
        log_id="log-1",
        src_ip="10.0.0.1",
        dst_ip="10.0.0.2",
        existed_status=True,
        created_at=DT,
    )
    session = install_session(
        monkeypatch,
        FakeSession(
            get_handler=lambda row_type, key: agg,
            responses=[FakeResult(rows=[FakeRow(make_src_dst_stats_mapping())])],
        ),
    )
    data = await SrcDstAggregatedEventPGManager.get_aggregated_event_by_id("a-1")
    assert data is not None
    assert data["id"] == "a-1"
    assert data["src_ip"] == "10.0.0.1"
    assert data["existed_status"] is True
    assert data["ave_total_latency"] == 1.0
    assert data["operation"] == "GET"
    assert len(session.executed) == 1


async def test_delete_and_update_src_dst_events(monkeypatch):
    conn = install_connection(monkeypatch, FakeConnection())
    assert (
        await SrcDstAggregatedEventPGManager.delete_aggregated_events_by_log_id("log-1")
        is True
    )
    assert (
        await SrcDstAggregatedEventPGManager.update_aggregated_events_existed_status_by_log_id(
            "log-1", 0
        )
        is True
    )
    sqls = [str(s) for s, _ in conn.executed]
    assert "UPDATE src_dst_aggregated_event" in sqls[0]
    assert "SET existed_status = FALSE" in sqls[0]
    assert "SET existed_status = :existed_status" in sqls[1]
    assert conn.executed[1][1] == {"log_id": "log-1", "existed_status": False}
