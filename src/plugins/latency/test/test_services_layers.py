"""Services 层单元测试：覆盖 services/ 下各服务模块的分支与异常路径。

策略：
- 通过 monkeypatch 替换模块级导入的 Manager 类方法/函数，避免依赖数据库。
- 用 asyncio.run 直调静态异步方法（pytest.ini 为 asyncio_mode=auto，同步测试亦可）。
- 只加测试，不改生产代码；已知生产 bug 用测试注释标明。
"""

import asyncio
import io
import json
import os
import socket
import zipfile
from contextlib import asynccontextmanager
from datetime import datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

import latency.services.log_file as log_file_module
import latency.services.log_failure_event_result as failure_event_module
import latency.services.log_knowledge as log_knowledge_module
import latency.services.log_parse_result as log_parse_result_module
import latency.services.src_dst_aggregated_event as src_dst_module
from latency.ENUM.general import DiagnosisConfigLogType, SourceType
from latency.ENUM.task import TaskStatusEnum, TaskTypeEnum
from latency.database.managers.anomalous_event import AnomalousEventPGManager
from latency.database.managers.anomalous_event_chain import (
    AnomalousEventChainPGManager,
)
from latency.database.managers.diagnosis_case import DiagnosisCasePGManager
from latency.database.managers.failure_mode_knowledge import (
    FailureModeKnowledgePGManager,
)
from latency.database.managers.log_failure_event import LogFailureEventPGManager
from latency.database.managers.log_file import LogFilePGManager
from latency.database.managers.log_knowledge import LogKnowledgePGManager
from latency.database.managers.log_parse_result import LogParseResultPGManager
from latency.database.managers.src_dst_aggregated_event import (
    SrcDstAggregatedEventPGManager,
)
from latency.database.managers.task import TaskPGManager
from latency.database.managers.task_report import TaskReportPGManager
from latency.database.managers.time_window_aggregated_event import (
    TimeWindowAggregatedEventPGManager,
)
from latency.exceptions import (
    BadRequestBizException,
    ConflictBizException,
    NotFoundBizException,
)
from latency.schemas.diagnosis_case import DiagnosisCaseModel
from latency.schemas.log import (
    AnomalousEventChainModel,
    AnomalousEventModel,
    LogFileModel,
    SrcDstAggregatedEventDataclass,
    SrcDstAggregatedEventModel,
    TimeWindowAggregatedEventModel,
)
from latency.schemas.log_failure_event import ErrCodeMetricItem, LogFailureEventModel
from latency.schemas.log_failure_event import TraceFailureEventModel
from latency.schemas.task import TaskModel, TaskReportModel
from latency.services.anomalous_event import AnomalousEventService
from latency.services.anomalous_event_chain import AnomalousEventChainService
from latency.services.diagnosis_case import DiagnosisCaseService
from latency.services.failure_mode_knowledge import FailureModeKnowledge
from latency.services.log_file import LogFileService
from latency.services.log_failure_event_result import LogFailureEventResultService
from latency.services.log_knowledge import LogKnowledgeService
from latency.services.log_parse_result import LogParseResultService
from latency.services.src_dst_aggregated_event import SrcDstAggregatedEventService
from latency.services.task import TaskService
from latency.task.task_handler import TaskHandler
from latency.task.worker.base import BaseWorker
from latency.schemas.request import (
    CreateDiagnosisCaseRequest,
    CreateTaskRequest,
    GetErrCodeMetricsRequest,
    GetLatencyMetricsRequest,
    ListLogFailureEventResultRequest,
    ListLogKnowledgeRequest,
    ListPodAggregatedFailureEventRequest,
    ListSrcDstAggregatedFailureEventRequest,
    ListSrcDstAggregatedEventRequest,
    ListTasksRequest,
    ListTimeAggregatedFailureEventRequest,
    ListTimeWindowAggregatedEventRequest,
    ListTraceFailureEventResultRequest,
    ListTracesByHostRequest,
    ParseConfig,
    SearchDiagnosisCasesRequest,
    UpLoadLogFileConfig,
    UpLoadLogFilesRequest,
    UpdateLogKnowledgeRequest,
    UpdateLogFileRequest,
    ListLogFilesRequest,
)


def run(coro):
    return asyncio.run(coro)


def make_task_model(task_id="task-1", status=TaskStatusEnum.RUNNING, created_at=None):
    return TaskModel(
        id=task_id,
        kb_id="kb-1",
        op_id="op-1",
        task_name="解析任务",
        task_type=TaskTypeEnum.KV_CACHE_LOG_PARSE_WORKER,
        status=status,
        created_at=created_at or datetime(2026, 8, 1),
        retry_times=0,
        existed_status=True,
        task_reports=[],
    )


def make_report(task_id="task-1", hour=10, progress=10.0, message="Log parsing: scanning done"):
    return SimpleNamespace(
        task_id=task_id,
        created_at=datetime(2026, 8, 1, hour),
        message=message,
        progress=progress,
    )


# ---------------------------------------------------------------------------
# services/task.py
# ---------------------------------------------------------------------------


def test_task_service_create_task_success_and_missing_op(monkeypatch):
    init_task = AsyncMock(return_value="task-1")
    monkeypatch.setattr(TaskHandler, "init_task", init_task)

    req = CreateTaskRequest(
        task_type=TaskTypeEnum.KV_CACHE_LOG_PARSE_WORKER,
        op_id="op-1",
        kb_id="kb-1",
    )
    msg = run(TaskService.create_task(req))
    assert msg.task_id == "task-1"
    init_task.assert_awaited_once_with(
        task_type=TaskTypeEnum.KV_CACHE_LOG_PARSE_WORKER, op_id="op-1"
    )

    init_task.return_value = None
    init_task.reset_mock()
    with pytest.raises(NotFoundBizException):
        run(TaskService.create_task(req))
    init_task.assert_awaited_once()


def test_task_service_stop_task_status_matrix(monkeypatch):
    get_task = AsyncMock()
    stop_task = AsyncMock(return_value="task-1")
    monkeypatch.setattr(TaskPGManager, "get_task_by_task_id", get_task)
    monkeypatch.setattr(TaskHandler, "stop_task", stop_task)

    # 任务不存在
    get_task.return_value = None
    with pytest.raises(NotFoundBizException):
        run(TaskService.stop_task("missing"))
    # 已删除（existed_status=False）
    get_task.return_value = SimpleNamespace(existed_status=False, status=TaskStatusEnum.PENDING)
    with pytest.raises(NotFoundBizException):
        run(TaskService.stop_task("task-1"))
    # 已成功的任务不可停止 -> Conflict
    get_task.return_value = SimpleNamespace(existed_status=True, status=TaskStatusEnum.SUCCESSFUL)
    with pytest.raises(ConflictBizException):
        run(TaskService.stop_task("task-1"))
    stop_task.assert_not_awaited()

    # PENDING / RUNNING 可停止
    for status in (TaskStatusEnum.PENDING, TaskStatusEnum.RUNNING):
        get_task.return_value = SimpleNamespace(existed_status=True, status=status)
        msg = run(TaskService.stop_task("task-1"))
        assert msg.task_id == "task-1"
    assert stop_task.await_count == 2


def test_task_service_delete_task(monkeypatch):
    get_task = AsyncMock()
    delete_task = AsyncMock(return_value="task-1")
    monkeypatch.setattr(TaskPGManager, "get_task_by_task_id", get_task)
    monkeypatch.setattr(TaskHandler, "delete_task", delete_task)

    get_task.return_value = None
    with pytest.raises(NotFoundBizException):
        run(TaskService.delete_task("missing"))

    get_task.return_value = SimpleNamespace(existed_status=False, status=TaskStatusEnum.PENDING)
    with pytest.raises(NotFoundBizException):
        run(TaskService.delete_task("task-1"))

    get_task.return_value = SimpleNamespace(existed_status=True, status=TaskStatusEnum.PENDING)
    msg = run(TaskService.delete_task("task-1"))
    assert msg.task_id == "task-1"

    delete_task.return_value = None
    with pytest.raises(NotFoundBizException):
        run(TaskService.delete_task("task-1"))


def test_task_service_list_tasks_filters_sorts_and_paginates(monkeypatch):
    older = make_task_model("t-old", TaskStatusEnum.PENDING, datetime(2026, 8, 1))
    newer = make_task_model("t-new", TaskStatusEnum.RUNNING, datetime(2026, 8, 3))
    deleted = make_task_model("t-del", TaskStatusEnum.FAILED, datetime(2026, 8, 2))
    deleted.existed_status = False
    other_type = make_task_model("t-type", TaskStatusEnum.SUCCESSFUL, datetime(2026, 8, 4))
    other_type.task_type = TaskTypeEnum.STORE_TRACE_CONTEXT_LOGS_WORKER
    other_type.kb_id = "kb-2"
    monkeypatch.setattr(
        TaskPGManager,
        "list_all_tasks",
        AsyncMock(return_value=[newer, older, deleted, other_type]),
    )
    list_reports = AsyncMock(
        return_value=[make_report("t-new", hour=10), make_report("t-new", hour=9, progress=20.0)]
    )
    monkeypatch.setattr(TaskReportPGManager, "list_task_reports_by_task_ids", list_reports)

    req = ListTasksRequest(kb_id="kb-1", created_sorted_desc=True, page_cnt=10, page_num=1)
    msg = run(TaskService.list_tasks(req))
    assert msg.total == 2
    assert [t.id for t in msg.tasks] == ["t-new", "t-old"]
    # reports 按创建时间倒序挂载
    assert [r.progress for r in msg.tasks[0].task_reports] == [10.0, 20.0]
    # 过滤 task_type / status / op_id
    req = ListTasksRequest(
        kb_id="kb-1",
        task_type=TaskTypeEnum.KV_CACHE_LOG_PARSE_WORKER,
        status=TaskStatusEnum.PENDING,
        op_id="op-1",
        created_sorted_desc=False,
    )
    msg = run(TaskService.list_tasks(req))
    assert msg.total == 1
    assert msg.tasks[0].id == "t-old"
    # 分页
    req = ListTasksRequest(kb_id="kb-1", page_num=2, page_cnt=1, created_sorted_desc=True)
    msg = run(TaskService.list_tasks(req))
    assert msg.total == 2
    assert [t.id for t in msg.tasks] == ["t-old"]


def test_task_service_list_tasks_created_at_filters(monkeypatch):
    """created_at 过滤分支。

    生产 bug（勿修，仅记录）：ListTasksRequest.created_at_start 是 TimeStr 字符串，
    而 TaskModel.created_at 是 datetime，真实数据下 `task.created_at < req.created_at_start`
    会抛 TypeError。这里用字符串 created_at 的桩对象驱动过滤逻辑本身。
    """
    stub = TaskModel.model_construct(
        id="t-1",
        status=TaskStatusEnum.RUNNING,
        task_type=TaskTypeEnum.KV_CACHE_LOG_PARSE_WORKER,
        op_id="op-1",
        kb_id="kb-1",
        created_at="2026-08-01 00:00:00",
        retry_times=0,
        existed_status=True,
        task_reports=[],
    )
    monkeypatch.setattr(TaskPGManager, "list_all_tasks", AsyncMock(return_value=[stub]))
    monkeypatch.setattr(
        TaskReportPGManager, "list_task_reports_by_task_ids", AsyncMock(return_value=[])
    )

    # created_at_start 过滤：任务早于起始时间 -> 被剔除
    req = ListTasksRequest(kb_id="kb-1", created_at_start="2026-08-02 00:00:00")
    msg = run(TaskService.list_tasks(req))
    assert msg.total == 0

    # created_at_end 过滤：任务晚于结束时间 -> 被剔除
    req = ListTasksRequest(kb_id="kb-1", created_at_end="2026-07-31 00:00:00")
    msg = run(TaskService.list_tasks(req))
    assert msg.total == 0

    # 任务在时间范围内 -> 保留
    req = ListTasksRequest(
        kb_id="kb-1",
        created_at_start="2026-07-31 00:00:00",
        created_at_end="2026-08-02 00:00:00",
    )
    msg = run(TaskService.list_tasks(req))
    assert msg.total == 1

    # 真实 TaskModel（datetime）与字符串过滤值直接比较抛 TypeError，记录该 bug
    monkeypatch.setattr(
        TaskPGManager, "list_all_tasks", AsyncMock(return_value=[make_task_model()])
    )
    req = ListTasksRequest(kb_id="kb-1", created_at_start="2026-08-02 00:00:00")
    with pytest.raises(TypeError):
        run(TaskService.list_tasks(req))


def test_task_service_get_task_by_id(monkeypatch):
    get_task = AsyncMock()
    monkeypatch.setattr(TaskPGManager, "get_task_by_task_id", get_task)
    list_reports = AsyncMock(
        return_value=[make_report("task-1", hour=10), make_report("task-1", hour=9, progress=20.0)]
    )
    monkeypatch.setattr(TaskReportPGManager, "list_task_reports_by_task_ids", list_reports)

    get_task.return_value = None
    with pytest.raises(NotFoundBizException):
        run(TaskService.get_task_by_id("missing"))

    task = make_task_model()
    get_task.return_value = task
    msg = run(TaskService.get_task_by_id("task-1"))
    assert msg.task.id == "task-1"
    assert [r.progress for r in msg.task.task_reports] == [10.0, 20.0]


# ---------------------------------------------------------------------------
# services/src_dst_aggregated_event.py
# ---------------------------------------------------------------------------


def make_cached_event(src_ip="1.1.1.1", dst_ip="2.2.2.2", operation="DS_KV_CLIENT_GET"):
    return SrcDstAggregatedEventDataclass(
        id="agg-1", src_ip=src_ip, dst_ip=dst_ip, log_id="log-1",
        kb_id="kb-1", operation=operation, log_parse_result_cnt=3,
        anomaly_log_parse_result_cnt=1, anomaly_cnt=1,
        ave_total_latency=1.0, p99_total_latency=2.0,
    )


def test_list_aggregated_events_cache_hit_by_log_id(monkeypatch):
    monkeypatch.setattr(
        src_dst_module, "get_aggregated_events", lambda log_id: [make_cached_event()]
    )
    monkeypatch.setattr(
        src_dst_module, "find_aggregated_by_kb_id", lambda kb_id: [make_cached_event()]
    )
    pg_list = AsyncMock(return_value=(0, []))
    monkeypatch.setattr(SrcDstAggregatedEventPGManager, "list_aggregated_events", pg_list)

    req = ListSrcDstAggregatedEventRequest(kb_id="kb-1", log_id="log-1", page_cnt=10, page_num=1)
    msg = run(SrcDstAggregatedEventService.list_aggregated_events(req))
    assert msg.total == 1
    assert msg.events[0].src_ip == "1.1.1.1"
    assert msg.events[0].operation == "DS_KV_CLIENT_GET"
    pg_list.assert_not_awaited()


def test_list_aggregated_events_log_id_falls_back_to_kb_cache(monkeypatch):
    # log_id 缓存未命中 -> 反查日志文件 -> 用 kb 缓存
    monkeypatch.setattr(src_dst_module, "get_aggregated_events", lambda log_id: None)
    cached = [make_cached_event()]
    find_calls = []

    def fake_find(kb_id):
        find_calls.append(kb_id)
        return cached

    monkeypatch.setattr(src_dst_module, "find_aggregated_by_kb_id", fake_find)
    monkeypatch.setattr(
        src_dst_module,
        "LogFilePGManager",
        SimpleNamespace(
            get_log_file_by_log_file_id=AsyncMock(
                return_value=SimpleNamespace(kb_id="kb-1")
            )
        ),
    )
    pg_list = AsyncMock(return_value=(0, []))
    monkeypatch.setattr(SrcDstAggregatedEventPGManager, "list_aggregated_events", pg_list)

    # 回退分支要求 req.kb_id 为空（log_id 反查知识库）
    req = ListSrcDstAggregatedEventRequest(kb_id="", log_id="log-1", page_cnt=10, page_num=1)
    msg = run(SrcDstAggregatedEventService.list_aggregated_events(req))
    assert msg.total == 1
    assert find_calls == ["kb-1"]

    # 反查到的日志文件无 kb_id -> 继续查库
    monkeypatch.setattr(
        src_dst_module,
        "LogFilePGManager",
        SimpleNamespace(
            get_log_file_by_log_file_id=AsyncMock(return_value=SimpleNamespace(kb_id=""))
        ),
    )
    run(SrcDstAggregatedEventService.list_aggregated_events(req))
    assert pg_list.await_count == 1

    # 日志文件本身不存在 -> 查库
    monkeypatch.setattr(
        src_dst_module,
        "LogFilePGManager",
        SimpleNamespace(get_log_file_by_log_file_id=AsyncMock(return_value=None)),
    )
    run(SrcDstAggregatedEventService.list_aggregated_events(req))
    assert pg_list.await_count == 2


def test_list_aggregated_events_kb_cache_and_db(monkeypatch):
    monkeypatch.setattr(
        src_dst_module, "find_aggregated_by_kb_id", lambda kb_id: [make_cached_event()]
    )
    req = ListSrcDstAggregatedEventRequest(kb_id="kb-1", page_cnt=10, page_num=1)
    msg = run(SrcDstAggregatedEventService.list_aggregated_events(req))
    assert msg.total == 1

    # kb 缓存未命中 -> 查库
    monkeypatch.setattr(src_dst_module, "find_aggregated_by_kb_id", lambda kb_id: None)
    pg_list = AsyncMock(
        return_value=(
            2,
            [SrcDstAggregatedEventModel(src_ip="1.1.1.1", dst_ip="2.2.2.2", log_id="log-1")],
        )
    )
    monkeypatch.setattr(SrcDstAggregatedEventPGManager, "list_aggregated_events", pg_list)
    msg = run(SrcDstAggregatedEventService.list_aggregated_events(req))
    assert msg.total == 2
    assert msg.events[0].src_ip == "1.1.1.1"


def test_filter_aggregated_in_memory_supports_all_filters():
    events = [
        SrcDstAggregatedEventModel(
            src_ip="10.0.0.1", dst_ip="10.0.0.2", log_id="log-1",
            operation="DS_KV_CLIENT_GET", created_at="2026-08-02 10:00:00.000",
        ),
        SrcDstAggregatedEventModel(
            src_ip="10.0.0.3", dst_ip="10.0.0.4", log_id="log-1",
            operation="ds_client_create", created_at="2026-08-01 09:00:00.000",
        ),
        SrcDstAggregatedEventModel(
            src_ip="192.168.1.1", dst_ip="10.0.0.9", log_id="log-1",
            operation="other_op", created_at="2026-08-03 12:00:00.000",
        ),
    ]
    base = dict(kb_id="kb-1", page_cnt=10, page_num=1)

    req = ListSrcDstAggregatedEventRequest(**base, src_ip="10.0.0")
    assert len(SrcDstAggregatedEventService._filter_aggregated_in_memory(events, req)) == 2

    req = ListSrcDstAggregatedEventRequest(**base, dst_ip="10.0.0.9")
    assert len(SrcDstAggregatedEventService._filter_aggregated_in_memory(events, req)) == 1

    req = ListSrcDstAggregatedEventRequest(**base, operation="get")
    assert len(SrcDstAggregatedEventService._filter_aggregated_in_memory(events, req)) == 1

    req = ListSrcDstAggregatedEventRequest(**base, operation="set")
    assert len(SrcDstAggregatedEventService._filter_aggregated_in_memory(events, req)) == 1

    req = ListSrcDstAggregatedEventRequest(**base, operation="other_op")
    assert len(SrcDstAggregatedEventService._filter_aggregated_in_memory(events, req)) == 1

    req = ListSrcDstAggregatedEventRequest(**base, start_time="2026-08-01 10:00:00")
    assert len(SrcDstAggregatedEventService._filter_aggregated_in_memory(events, req)) == 2

    req = ListSrcDstAggregatedEventRequest(**base, end_time="2026-08-01 10:00:00")
    assert len(SrcDstAggregatedEventService._filter_aggregated_in_memory(events, req)) == 1

    # 生产 bug（勿修，仅记录）：SrcDstAggregatedEventModel 没有 cluster_name/host 字段，
    # 设置这两个过滤条件会抛 AttributeError。
    req = ListSrcDstAggregatedEventRequest(**base, cluster_name="cluster-a")
    with pytest.raises(AttributeError):
        SrcDstAggregatedEventService._filter_aggregated_in_memory(events, req)
    req = ListSrcDstAggregatedEventRequest(**base, host="host-a")
    with pytest.raises(AttributeError):
        SrcDstAggregatedEventService._filter_aggregated_in_memory(events, req)


def test_list_aggregated_events_paginates_cached_results(monkeypatch):
    cached = [
        make_cached_event(src_ip=f"10.0.0.{i}", operation="GET") for i in range(5)
    ]
    monkeypatch.setattr(src_dst_module, "get_aggregated_events", lambda log_id: cached)
    req = ListSrcDstAggregatedEventRequest(
        kb_id="kb-1", log_id="log-1", src_ip="10.0.0", page_cnt=2, page_num=2
    )
    msg = run(SrcDstAggregatedEventService.list_aggregated_events(req))
    assert msg.total == 5
    assert len(msg.events) == 2
    assert msg.events[0].src_ip == "10.0.0.2"


def test_get_aggregated_event_by_id_not_found_paths(monkeypatch):
    get_event = AsyncMock()
    monkeypatch.setattr(SrcDstAggregatedEventPGManager, "get_aggregated_event_by_id", get_event)

    get_event.return_value = None
    with pytest.raises(NotFoundBizException):
        run(SrcDstAggregatedEventService.get_aggregated_event_by_id("missing"))

    get_event.return_value = SimpleNamespace(existed_status=False)
    with pytest.raises(NotFoundBizException):
        run(SrcDstAggregatedEventService.get_aggregated_event_by_id("agg-1"))

    model = SrcDstAggregatedEventModel(src_ip="1.1.1.1", dst_ip="2.2.2.2", log_id="log-1")
    get_event.return_value = model
    msg = run(SrcDstAggregatedEventService.get_aggregated_event_by_id("agg-1"))
    assert msg.event is model


def test_list_time_window_events_builds_ip_pairs(monkeypatch):
    rows = [
        {
            "start_time": "2026-08-01 00:00:00",
            "end_time": "2026-08-01 00:01:00",
            "total_cnt": 5,
            "ip_pairs": [
                {"src_ip": "1.1.1.1", "dst_ip": "2.2.2.2", "log_parse_result_cnt": 5},
                {"src_ip": "3.3.3.3", "dst_ip": "4.4.4.4"},
            ],
        },
        {"start_time": "2026-08-01 00:01:00", "end_time": "2026-08-01 00:02:00"},
    ]
    monkeypatch.setattr(
        TimeWindowAggregatedEventPGManager,
        "list_time_window_events",
        AsyncMock(return_value=(2, rows)),
    )
    req = ListTimeWindowAggregatedEventRequest(kb_id="kb-1")
    msg = run(SrcDstAggregatedEventService.list_time_window_events(req))
    assert msg.total == 2
    assert msg.events[0].ip_pairs[0].src_ip == "1.1.1.1"
    assert msg.events[0].total_cnt == 5
    assert msg.events[1].ip_pairs == []


# ---------------------------------------------------------------------------
# services/log_failure_event_result.py
# ---------------------------------------------------------------------------


def make_failure_event(**overrides):
    payload = dict(
        log_id="log-1",
        log_file="brpc.log",
        raw_text="raw",
        host_name="host-1",
        timestamp="2026-08-01 00:00:00",
        level="ERROR",
        filename="a.cc",
        pod_name="pod-1",
        pid="1",
        tid="2",
        trace_id="trace-1",
        cluster_name="cluster-1",
        message="boom",
        status_code="1004",
        failure_mode=["umq.failure"],
    )
    payload.update(overrides)
    return LogFailureEventModel(**payload)


def test_normalize_unknown_host_name():
    normalize = LogFailureEventResultService._normalize_unknown_host_name
    assert normalize(None) is None
    assert normalize("UNKNOWN") is None
    assert normalize("  unknown  ") is None
    assert normalize("   ") is None
    assert normalize("host-1") == "host-1"


def test_list_log_failure_event_result_normalizes_and_backfills(monkeypatch):
    list_events = AsyncMock()
    monkeypatch.setattr(LogFailureEventPGManager, "list_log_failure_events", list_events)

    # total>0：不触发回填
    list_events.return_value = (
        2,
        [make_failure_event(), make_failure_event(log_id="log-2", host_name="UNKNOWN")],
    )
    req = ListLogFailureEventResultRequest(kb_id="kb-1", trace_ids=["trace-1"])
    msg = run(LogFailureEventResultService.list_log_failure_event_result(req))
    assert msg.total == 2
    assert msg.log_failure_event_results[0].host_name == "host-1"
    assert msg.log_failure_event_results[1].host_name is None
    assert list_events.await_count == 1

    # total==0 且无 trace_ids：不回填
    list_events.reset_mock()
    list_events.return_value = (0, [])
    req = ListLogFailureEventResultRequest(kb_id="kb-1", trace_ids=[])
    msg = run(LogFailureEventResultService.list_log_failure_event_result(req))
    assert msg.total == 0
    assert list_events.await_count == 1

    # total==0 且有 trace_ids：回填后重查
    list_events.reset_mock()
    collect_calls = []

    async def fake_collect(**kwargs):
        collect_calls.append(kwargs)
        return 2

    monkeypatch.setattr(failure_event_module, "collect_trace_context_logs", fake_collect)
    monkeypatch.setattr(
        failure_event_module,
        "LogFilePGManager",
        SimpleNamespace(
            list_log_file_paths=AsyncMock(
                return_value=[("log-1", "/data/brpc.log"), ("log-2", "/data/x.log")]
            )
        ),
    )
    list_events.side_effect = [(0, []), (2, [make_failure_event()])]
    req = ListLogFailureEventResultRequest(
        kb_id="kb-1", trace_ids=[" trace-1 ", "", "trace-2"]
    )
    msg = run(LogFailureEventResultService.list_log_failure_event_result(req))
    assert msg.total == 2
    assert list_events.await_count == 2
    assert len(collect_calls) == 2
    assert collect_calls[0]["trace_ids"] == {"trace-1", "trace-2"}
    assert collect_calls[0]["clear_existing"] is False
    assert collect_calls[0]["log_id"] == "log-1"


def test_backfill_trace_context_logs_guards(monkeypatch):
    # 无 kb_id 且无 log_id -> 0
    req = ListLogFailureEventResultRequest(kb_id="", trace_ids=["trace-1"])
    assert run(LogFailureEventResultService._backfill_trace_context_logs(req)) == 0

    # trace_ids 全空白 -> 0
    req = ListLogFailureEventResultRequest(kb_id="kb-1", trace_ids=["  "])
    assert run(LogFailureEventResultService._backfill_trace_context_logs(req)) == 0

    # 无可回填文件
    monkeypatch.setattr(
        failure_event_module,
        "LogFilePGManager",
        SimpleNamespace(list_log_file_paths=AsyncMock(return_value=[])),
    )
    req = ListLogFailureEventResultRequest(kb_id="kb-1", trace_ids=["trace-1"])
    assert run(LogFailureEventResultService._backfill_trace_context_logs(req)) == 0


def test_list_trace_failure_event_result_normalizes_host_names(monkeypatch):
    event = TraceFailureEventModel(
        trace_id="trace-1",
        log_id="log-1",
        pod_names=["pod-1"],
        host_names=["UNKNOWN", "host-1"],
        cluster_names=["cluster-1"],
        timestamp="2026-08-01 00:00:00",
    )
    monkeypatch.setattr(
        LogFailureEventPGManager,
        "list_trace_failure_events",
        AsyncMock(return_value=(1, [event])),
    )
    req = ListTraceFailureEventResultRequest(kb_id="kb-1")
    msg = run(LogFailureEventResultService.list_trace_failure_event_result(req))
    assert msg.total == 1
    assert msg.trace_failure_event_results[0].host_names == [None, "host-1"]


def test_aggregated_failure_event_and_err_code_metrics(monkeypatch):
    monkeypatch.setattr(
        LogFailureEventPGManager,
        "list_time_aggregated_failure_events",
        AsyncMock(
            return_value=(
                1,
                ["1004"],
                [{"start_time": "s", "end_time": "e", "status_code_cnt": {"1004": 3}}],
            )
        ),
    )
    req = ListTimeAggregatedFailureEventRequest(kb_id="kb-1")
    msg = run(LogFailureEventResultService.list_time_aggregated_failure_event_result(req))
    assert msg.total == 1
    assert msg.err_codes == ["1004"]
    assert msg.events[0].status_code_cnt == {"1004": 3}

    monkeypatch.setattr(
        LogFailureEventPGManager,
        "list_pod_aggregated_failure_events",
        AsyncMock(
            return_value=(1, [{"pod_name": "pod-1", "status_code_cnt": {"1004": 1}}])
        ),
    )
    req = ListPodAggregatedFailureEventRequest(kb_id="kb-1")
    msg = run(LogFailureEventResultService.list_pod_aggregated_failure_event_result(req))
    assert msg.events[0].pod_name == "pod-1"

    monkeypatch.setattr(
        LogFailureEventPGManager,
        "list_src_dst_aggregated_failure_events",
        AsyncMock(
            return_value=(
                1,
                [{"src_ip": "1.1.1.1", "dst_ip": "2.2.2.2", "status_code_cnt": {"1004": 2}}],
            )
        ),
    )
    req = ListSrcDstAggregatedFailureEventRequest(kb_id="kb-1")
    msg = run(LogFailureEventResultService.list_src_dst_aggregated_failure_event_result(req))
    assert msg.events[0].src_ip == "1.1.1.1"

    monkeypatch.setattr(
        LogFailureEventPGManager,
        "get_err_code_metrics",
        AsyncMock(
            return_value=(
                1,
                {"1004": [ErrCodeMetricItem(time="2026-08-01 00:00:00", err_cnt=2)]},
            )
        ),
    )
    req = GetErrCodeMetricsRequest(
        kb_id="kb-1",
        start_time="2026-08-01 00:00:00",
        end_time="2026-08-02 00:00:00",
    )
    msg = run(LogFailureEventResultService.get_err_code_metrics(req))
    assert msg.total == 1
    assert msg.metrics["1004"][0].err_cnt == 2
    assert msg.time_range == {
        "start_time": "2026-08-01 00:00:00",
        "end_time": "2026-08-02 00:00:00",
    }


# ---------------------------------------------------------------------------
# services/log_knowledge.py
# ---------------------------------------------------------------------------


def test_delete_log_kb_by_kb_id_not_found(monkeypatch):
    monkeypatch.setattr(
        LogKnowledgePGManager, "get_log_kb_by_kb_id", AsyncMock(return_value=None)
    )
    with pytest.raises(NotFoundBizException):
        run(LogKnowledgeService.delete_log_kb_by_kb_id("missing-kb"))


def test_delete_log_kb_survives_failed_task_stops(monkeypatch):
    monkeypatch.setattr(
        LogKnowledgePGManager,
        "get_log_kb_by_kb_id",
        AsyncMock(return_value=SimpleNamespace(kb_id="kb-1")),
    )
    monkeypatch.setattr(
        TaskPGManager,
        "list_tasks_by_kb_id",
        AsyncMock(return_value=[SimpleNamespace(id="t-1"), SimpleNamespace(id="t-2")]),
    )
    # 第一个任务 stop 返回 False，第二个任务 stop 抛异常，删除仍然继续
    monkeypatch.setattr(BaseWorker, "stop", AsyncMock(side_effect=[False, Exception("kill failed")]))
    update_log_kb = AsyncMock(return_value=1)
    monkeypatch.setattr(LogKnowledgePGManager, "update_log_kb", update_log_kb)
    monkeypatch.setattr(
        LogFilePGManager, "list_log_file_ids", AsyncMock(return_value=[])
    )
    delete_config = AsyncMock()
    monkeypatch.setattr(log_knowledge_module.DiagnosisConfigPGManager, "delete", delete_config)

    msg = run(LogKnowledgeService.delete_log_kb_by_kb_id("kb-1"))
    assert msg.kb_id == "kb-1"
    update_log_kb.assert_awaited_once_with("kb-1", {"existed_status": False})
    delete_config.assert_awaited_once_with("kb-1")


def test_delete_log_kb_cleans_directories(monkeypatch, tmp_path):
    monkeypatch.setattr(
        LogKnowledgePGManager,
        "get_log_kb_by_kb_id",
        AsyncMock(return_value=SimpleNamespace(kb_id="kb-1")),
    )
    monkeypatch.setattr(TaskPGManager, "list_tasks_by_kb_id", AsyncMock(return_value=[]))
    monkeypatch.setattr(LogKnowledgePGManager, "update_log_kb", AsyncMock(return_value=1))
    monkeypatch.setattr(
        LogFilePGManager, "list_log_file_ids", AsyncMock(return_value=["lf-0001-x", "lf-0002-y"])
    )
    monkeypatch.setattr(
        log_knowledge_module.DiagnosisConfigPGManager, "delete", AsyncMock()
    )
    cleanup_calls = []
    monkeypatch.setattr(
        log_knowledge_module,
        "cleanup_preprocess_dir",
        lambda log_file_id: cleanup_calls.append(log_file_id) or "/tmp/pre",
    )
    monkeypatch.setattr(log_knowledge_module, "witty_dir", str(tmp_path))
    (tmp_path / "log_lf-0001-").mkdir()

    msg = run(LogKnowledgeService.delete_log_kb_by_kb_id("kb-1"))
    assert msg.kb_id == "kb-1"
    assert cleanup_calls == ["lf-0001-x", "lf-0002-y"]
    assert not (tmp_path / "log_lf-0001-").exists()
    # 第二个日志文件的诊断目录不存在 -> 静默跳过
    monkeypatch.setattr(LogFilePGManager, "list_log_file_ids", AsyncMock(return_value=["lf-0002-y"]))
    run(LogKnowledgeService.delete_log_kb_by_kb_id("kb-1"))

    # rmtree 失败 -> 记日志但不影响删除结果
    monkeypatch.setattr(LogFilePGManager, "list_log_file_ids", AsyncMock(return_value=["lf-0001-x"]))
    (tmp_path / "log_lf-0001-").mkdir()

    def raise_rmtree(path):
        raise OSError("permission denied")

    monkeypatch.setattr(log_knowledge_module.shutil, "rmtree", raise_rmtree)
    monkeypatch.setattr(
        log_knowledge_module, "cleanup_preprocess_dir", lambda log_file_id: None
    )
    msg = run(LogKnowledgeService.delete_log_kb_by_kb_id("kb-1"))
    assert msg.kb_id == "kb-1"


def test_delete_log_kb_rowcount_zero(monkeypatch):
    monkeypatch.setattr(
        LogKnowledgePGManager,
        "get_log_kb_by_kb_id",
        AsyncMock(return_value=SimpleNamespace(kb_id="kb-1")),
    )
    monkeypatch.setattr(TaskPGManager, "list_tasks_by_kb_id", AsyncMock(return_value=[]))
    monkeypatch.setattr(LogKnowledgePGManager, "update_log_kb", AsyncMock(return_value=0))
    with pytest.raises(NotFoundBizException):
        run(LogKnowledgeService.delete_log_kb_by_kb_id("kb-1"))


def test_update_log_kb_and_query_apis(monkeypatch):
    get_kb = AsyncMock()
    monkeypatch.setattr(LogKnowledgePGManager, "get_log_kb_by_kb_id", get_kb)

    get_kb.return_value = None
    with pytest.raises(NotFoundBizException):
        run(
            LogKnowledgeService.update_log_kb(
                "kb-1", UpdateLogKnowledgeRequest(name="new-name")
            )
        )

    get_kb.return_value = SimpleNamespace(kb_id="kb-1")
    update_kb = AsyncMock(return_value=1)
    monkeypatch.setattr(LogKnowledgePGManager, "update_log_kb", update_kb)
    msg = run(
        LogKnowledgeService.update_log_kb(
            "kb-1", UpdateLogKnowledgeRequest(name="new-name")
        )
    )
    assert msg.kb_id == "kb-1"
    update_kb.assert_awaited_once_with("kb-1", {"name": "new-name"})

    update_kb.return_value = 0
    msg = run(
        LogKnowledgeService.update_log_kb(
            "kb-1", UpdateLogKnowledgeRequest(description="d")
        )
    )
    assert msg.kb_id is None

    # list
    from latency.schemas.log import LogKnowledgeModel

    kb_model = LogKnowledgeModel(name="kb", description="d")
    monkeypatch.setattr(LogKnowledgePGManager, "count_log_kbs", AsyncMock(return_value=1))
    monkeypatch.setattr(LogKnowledgePGManager, "list_log_kbs", AsyncMock(return_value=[kb_model]))
    msg = run(LogKnowledgeService.list_log_kbs(ListLogKnowledgeRequest()))
    assert msg.total == 1
    assert msg.kbs[0].name == "kb"

    # get
    get_kb.return_value = None
    with pytest.raises(NotFoundBizException):
        run(LogKnowledgeService.get_log_kb_by_kb_id("missing"))
    get_kb.return_value = kb_model
    msg = run(LogKnowledgeService.get_log_kb_by_kb_id("kb-1"))
    assert msg.kb is kb_model


# ---------------------------------------------------------------------------
# services/log_parse_result.py
# ---------------------------------------------------------------------------


def make_parse_result(**overrides):
    payload = dict(is_anomalous=True, total_latency=1.5)
    payload.update(overrides)
    from latency.schemas.log import LogParseResultModel

    return LogParseResultModel(**payload)


def test_log_parse_result_list_and_get(monkeypatch):
    monkeypatch.setattr(
        LogParseResultPGManager,
        "list_log_parse_results",
        AsyncMock(return_value=(1, [make_parse_result()])),
    )
    from latency.schemas.request import ListLogParseResultRequest

    msg = run(
        LogParseResultService.list_log_parse_results(
            ListLogParseResultRequest(kb_id="kb-1")
        )
    )
    assert msg.total == 1
    assert msg.log_parse_results[0].is_anomalous is True

    get_result = AsyncMock()
    monkeypatch.setattr(LogParseResultPGManager, "get_log_parse_result_by_id", get_result)

    get_result.return_value = None
    with pytest.raises(NotFoundBizException):
        run(LogParseResultService.get_log_parse_result_by_id("missing"))

    get_result.return_value = SimpleNamespace(existed_status=False)
    with pytest.raises(NotFoundBizException):
        run(LogParseResultService.get_log_parse_result_by_id("r-1"))

    model = make_parse_result()
    get_result.return_value = model
    msg = run(LogParseResultService.get_log_parse_result_by_id("r-1"))
    assert msg.log_parse_result is model


def test_list_traces_by_host_and_options(monkeypatch):
    trace = {
        "trace_id": "t-1",
        "pod_id": "pod-1",
        "time": "2026-08-01 00:00:00",
        "sdk_ms": 1.0,
        "req_delay_ms": 2.0,
        "rsp_delay_ms": 3.0,
    }
    monkeypatch.setattr(
        LogParseResultPGManager,
        "list_traces_by_host",
        AsyncMock(return_value=(1, [trace])),
    )
    msg = run(
        LogParseResultService.list_traces_by_host(
            ListTracesByHostRequest(host="h-1", kb_id="kb-1")
        )
    )
    assert msg.total == 1
    assert msg.traces[0].trace_id == "t-1"

    monkeypatch.setattr(
        LogParseResultPGManager, "get_cluster_list", AsyncMock(return_value=["c-1"])
    )
    monkeypatch.setattr(
        LogParseResultPGManager, "get_host_list", AsyncMock(return_value=["h-1"])
    )
    msg = run(LogParseResultService.get_log_parse_options("kb-1"))
    assert msg.clusters == ["c-1"]
    assert msg.hosts == ["h-1"]


def test_latency_metrics_bucket_mode_passes_rows_through(monkeypatch):
    rows = [{"time": "2026-08-01 00:00:00", "total_latency": 5}]
    monkeypatch.setattr(
        LogParseResultPGManager, "get_latency_metrics", AsyncMock(return_value=(7, rows))
    )
    sample = AsyncMock()
    monkeypatch.setattr(
        log_parse_result_module.LatencyMetricsSampler, "sample", staticmethod(sample)
    )
    req = GetLatencyMetricsRequest(
        kb_id="kb-1",
        start_time="2026-08-01 00:00:00",
        end_time="2026-08-02 00:00:00",
    )
    msg = run(LogParseResultService.get_latency_metrics(req))
    assert msg.total == 7
    assert msg.metrics == rows
    assert msg.sampling_info == {
        "mode": "p99",
        "window_ms": 0,
        "original_count": 7,
        "sampled_count": 1,
    }
    assert msg.time_range == {
        "start_time": "2026-08-01 00:00:00",
        "end_time": "2026-08-02 00:00:00",
    }
    sample.assert_not_called()


def test_latency_metrics_non_bucket_mode_uses_sampler(monkeypatch):
    rows = [{"time": "2026-08-01 00:00:00", "total_latency": 5}]
    monkeypatch.setattr(
        LogParseResultPGManager, "get_latency_metrics", AsyncMock(return_value=(9, rows))
    )
    captured = {}

    def fake_sample(**kwargs):
        captured.update(kwargs)
        return [{"time": "sampled"}], {"mode": "avg"}

    monkeypatch.setattr(
        log_parse_result_module.LatencyMetricsSampler, "sample", staticmethod(fake_sample)
    )
    req = GetLatencyMetricsRequest(kb_id="kb-1", max_points=500)
    # schema 要求 bucket_seconds>=1，非桶分支需要手动置空（接口层不可达）
    req.bucket_seconds = None
    msg = run(LogParseResultService.get_latency_metrics(req))
    assert captured == {
        "metrics": rows,
        "max_points": 500,
        "sample_mode": req.sample_mode,
        "original_count": 9,
    }
    assert msg.metrics == [{"time": "sampled"}]
    assert msg.sampling_info == {"mode": "avg"}


# ---------------------------------------------------------------------------
# services/diagnosis_case.py
# ---------------------------------------------------------------------------


def test_create_case_returns_id_or_none(monkeypatch):
    add_case = AsyncMock(return_value="case-1")
    monkeypatch.setattr(DiagnosisCasePGManager, "add_case", add_case)
    req = CreateDiagnosisCaseRequest(
        kb_id="kb-1", symptom_summary="s", root_cause="r", recommendation="rec"
    )
    msg = run(DiagnosisCaseService.create_case(req))
    assert msg.case_id == "case-1"
    assert add_case.await_args.args[0].symptom_summary == "s"

    add_case.return_value = ""
    msg = run(DiagnosisCaseService.create_case(req))
    assert msg.case_id is None


def test_get_search_and_mark_case(monkeypatch):
    get_case = AsyncMock()
    monkeypatch.setattr(DiagnosisCasePGManager, "get_case", get_case)

    get_case.return_value = None
    with pytest.raises(NotFoundBizException):
        run(DiagnosisCaseService.get_case("missing"))

    get_case.return_value = SimpleNamespace(existed_status=False)
    with pytest.raises(NotFoundBizException):
        run(DiagnosisCaseService.get_case("case-1"))

    case = DiagnosisCaseModel(
        kb_id="kb-1", symptom_summary="s", root_cause="r", recommendation="rec"
    )
    get_case.return_value = case
    msg = run(DiagnosisCaseService.get_case("case-1"))
    assert msg.case is case

    monkeypatch.setattr(
        DiagnosisCasePGManager,
        "search_cases",
        AsyncMock(return_value=(1, [])),
    )
    msg = run(
        DiagnosisCaseService.search_cases(SearchDiagnosisCasesRequest(kb_id="kb-1"))
    )
    assert msg.total == 1

    mark_hit = AsyncMock()
    monkeypatch.setattr(DiagnosisCasePGManager, "mark_case_hit", mark_hit)
    msg = run(DiagnosisCaseService.mark_case_hit("case-1"))
    mark_hit.assert_awaited_once_with("case-1")
    assert msg.case is case


# ---------------------------------------------------------------------------
# services/failure_mode_knowledge.py
# ---------------------------------------------------------------------------


def _write_failure_mode_data(root):
    data = root / "data"
    (data / "kvcache").mkdir(parents=True)
    (data / "kvcache" / "kvcache_error_code_info.json").write_text(
        json.dumps({"1004": {"故障现象": "超时", "故障原因": "链路抖动"}}),
        encoding="utf-8",
    )
    (data / "kvcache" / "kvcache_failure_mode.json").write_text(
        json.dumps(
            [
                {
                    "故障编号": "kvcache_runtime_1000",
                    "故障名称": "运行时故障",
                    "故障现象": "超时",
                    "故障原因": "抖动",
                    "解决办法": "重启",
                    "故障域": "KVCache",
                    "错误码": 1004,
                }
            ]
        ),
        encoding="utf-8",
    )
    (data / "urma").mkdir()
    (data / "urma" / "urma_failure_mode.json").write_text(
        json.dumps(
            [
                {
                    "故障编号": "urma_link_1",
                    "故障名称": "建链失败",
                    "故障现象": "建链超时",
                    "故障原因": "网络",
                    "解决办法": "检查网络",
                    "故障域": "urma",
                    "错误码": None,
                }
            ]
        ),
        encoding="utf-8",
    )
    (data / "failure_mode_tree.json").write_text(
        json.dumps(
            {
                "kvcache": {"kvcache_runtime_1000": ["kvcache_failure_unknown"]},
                "urma": {"urma_link_1": []},
            }
        ),
        encoding="utf-8",
    )
    return data


def test_init_failure_mode_knowledge_reads_data_files(monkeypatch, tmp_path):
    _write_failure_mode_data(tmp_path)
    monkeypatch.setenv("WITTY_DIR", str(tmp_path))
    add_status = AsyncMock()
    add_modes = AsyncMock()
    monkeypatch.setattr(
        FailureModeKnowledgePGManager, "add_status_code_knowledge", add_status
    )
    monkeypatch.setattr(
        FailureModeKnowledgePGManager, "add_failure_mode_knowledge", add_modes
    )

    modes = run(FailureModeKnowledge.init_failure_mode_knowledge())

    status_rows = add_status.await_args.args[0]
    assert len(status_rows) == 1
    assert status_rows[0].status_code == "1004"
    assert status_rows[0].symptom == "超时"

    saved = add_modes.await_args.args[0]
    by_id = {m.id: m for m in saved}
    assert set(by_id) == {
        "kvcache_runtime_1000",
        "kvcache_failure_unknown",
        "urma_link_1",
    }
    # 树关系映射为逗号分隔的 children id 串
    assert by_id["kvcache_runtime_1000"].children_failure_mode_ids == "kvcache_failure_unknown"
    assert by_id["urma_link_1"].children_failure_mode_ids == ""
    # 错误码 int 被转成字符串
    assert by_id["kvcache_runtime_1000"].error_code == "1004"
    # 未知故障兜底被加入
    assert by_id["kvcache_failure_unknown"].name == "未知故障"


def test_init_failure_mode_knowledge_missing_files(monkeypatch, tmp_path):
    monkeypatch.delenv("WITTY_DIR", raising=False)
    add_status = AsyncMock()
    add_modes = AsyncMock()
    monkeypatch.setattr(
        FailureModeKnowledgePGManager, "add_status_code_knowledge", add_status
    )
    monkeypatch.setattr(
        FailureModeKnowledgePGManager, "add_failure_mode_knowledge", add_modes
    )

    modes = run(FailureModeKnowledge.init_failure_mode_knowledge())
    # 所有数据文件均不存在（默认 /var/witty-ub 下无数据），仅剩未知故障兜底
    assert [m.id for m in modes] == ["kvcache_failure_unknown"]
    add_status.assert_not_awaited()
    saved = add_modes.await_args.args[0]
    assert len(saved) == 1


def test_init_failure_mode_knowledge_rejects_bad_status_code_file(monkeypatch, tmp_path):
    data = tmp_path / "data"
    (data / "kvcache").mkdir(parents=True)
    # 顶层为 list 而非 dict -> ValueError 分支被吞掉并记录
    (data / "kvcache" / "kvcache_error_code_info.json").write_text(
        json.dumps([{"status_code": "1004"}]), encoding="utf-8"
    )
    monkeypatch.setenv("WITTY_DIR", str(tmp_path))
    add_status = AsyncMock()
    add_modes = AsyncMock()
    monkeypatch.setattr(
        FailureModeKnowledgePGManager, "add_status_code_knowledge", add_status
    )
    monkeypatch.setattr(
        FailureModeKnowledgePGManager, "add_failure_mode_knowledge", add_modes
    )

    modes = run(FailureModeKnowledge.init_failure_mode_knowledge())
    add_status.assert_not_awaited()
    assert [m.id for m in modes] == ["kvcache_failure_unknown"]


def test_failure_mode_knowledge_getters(monkeypatch):
    from latency.schemas.failure_mode import FailureModeModel, StatusCodeKnowledgeModel

    mode = FailureModeModel(
        id="kvcache_failure_unknown",
        name="未知故障",
        symptom="s",
        root_cause="r",
        solution="sol",
        failure_domain="KVCache",
        children_failure_mode_ids="",
    )
    get_mode = AsyncMock(return_value=mode)
    monkeypatch.setattr(FailureModeKnowledgePGManager, "get_failure_mode_by_id", get_mode)
    msg = run(FailureModeKnowledge.get_failure_mode_knowledege_by_id("kvcache_failure_unknown"))
    assert msg.failure_mode is mode

    info = StatusCodeKnowledgeModel(status_code="1004", symptom="s", root_cause="r")
    get_info = AsyncMock(return_value=info)
    monkeypatch.setattr(FailureModeKnowledgePGManager, "get_status_code_knowledge", get_info)
    msg = run(FailureModeKnowledge.get_status_code_knowledge("1004"))
    assert msg.status_code_info is info


# ---------------------------------------------------------------------------
# services/anomalous_event.py & services/anomalous_event_chain.py
# ---------------------------------------------------------------------------


def test_anomalous_event_service_paths(monkeypatch):
    get_event = AsyncMock()
    monkeypatch.setattr(AnomalousEventPGManager, "get_anomalous_event_by_id", get_event)

    get_event.return_value = None
    with pytest.raises(NotFoundBizException):
        run(AnomalousEventService.get_anomalous_event_by_id("missing"))

    get_event.return_value = SimpleNamespace(existed_status=False)
    with pytest.raises(NotFoundBizException):
        run(AnomalousEventService.get_anomalous_event_by_id("e-1"))

    event = AnomalousEventModel(anomaly_reason="latency")
    get_event.return_value = event
    msg = run(AnomalousEventService.get_anomalous_event_by_id("e-1"))
    assert msg.event is event

    monkeypatch.setattr(
        AnomalousEventPGManager,
        "list_anomalous_events_by_log_id",
        AsyncMock(return_value=[event]),
    )
    msg = run(AnomalousEventService.list_anomalous_events_by_log_id("log-1"))
    assert msg.total == 1

    monkeypatch.setattr(
        AnomalousEventPGManager,
        "list_anomalous_events",
        AsyncMock(return_value=(2, [event])),
    )
    from latency.schemas.request import ListAnomalousEventRequest

    msg = run(
        AnomalousEventService.list_anomalous_events(
            ListAnomalousEventRequest(kb_id="kb-1")
        )
    )
    assert msg.total == 2


def test_anomalous_event_chain_service_paths(monkeypatch):
    chain = AnomalousEventChainModel(log_id="log-1", anomalous_event_id="e-1")
    monkeypatch.setattr(
        AnomalousEventChainPGManager,
        "list_event_chains",
        AsyncMock(return_value=(1, [chain])),
    )
    from latency.schemas.request import ListAnomalousEventChainRequest

    msg = run(
        AnomalousEventChainService.list_event_chains(
            ListAnomalousEventChainRequest(kb_id="kb-1")
        )
    )
    assert msg.total == 1
    assert msg.event_chains[0].log_id == "log-1"

    monkeypatch.setattr(
        AnomalousEventChainPGManager,
        "list_event_chains_by_log_id",
        AsyncMock(return_value=[chain]),
    )
    assert run(AnomalousEventChainService.list_event_chains_by_log_id("log-1")) == [chain]


# ---------------------------------------------------------------------------
# services/log_file.py
# ---------------------------------------------------------------------------


def make_current_task(task_id, op_id, status, task_type=TaskTypeEnum.KV_CACHE_LOG_PARSE_WORKER, retry_times=0):
    return SimpleNamespace(
        id=task_id, op_id=op_id, status=status, task_type=task_type,
        retry_times=retry_times, task_reports=[],
    )


def make_fake_pg_manager(tasks=None, session_error=False):
    if session_error:
        @asynccontextmanager
        async def error_cm():
            raise RuntimeError("db down")
            yield
        return SimpleNamespace(session=lambda: error_cm())

    result_obj = SimpleNamespace(scalars=lambda: SimpleNamespace(all=lambda: tasks or []))
    session_obj = SimpleNamespace(execute=AsyncMock(return_value=result_obj))

    @asynccontextmanager
    async def session_cm():
        yield session_obj

    return SimpleNamespace(session=lambda: session_cm())


def _fake_list_current(tasks_by_type):
    async def fake(op_ids, task_type=None):
        if task_type is None:
            return tasks_by_type.get(None, [])
        return [t for t in tasks_by_type.get(task_type, []) if t.op_id in op_ids]
    return fake


def test_validate_remote_url_rules(monkeypatch):
    def fake_getaddrinfo(ips):
        def _inner(host, port):
            return [(2, 1, 6, "", (ip, 1)) for ip in ips]
        return _inner

    # scheme 不允许
    monkeypatch.setattr(log_file_module.socket, "getaddrinfo", fake_getaddrinfo(["8.8.8.8"]))
    assert log_file_module._validate_remote_url("ftp://example.com/a.zip") is False
    # 无 hostname
    assert log_file_module._validate_remote_url("http:///a.zip") is False
    # 私网 / 回环 / 链路本地 / 保留地址
    for ip in ("10.0.0.1", "127.0.0.1", "169.254.1.1", "240.0.0.1"):
        monkeypatch.setattr(log_file_module.socket, "getaddrinfo", fake_getaddrinfo([ip]))
        assert log_file_module._validate_remote_url(f"http://{ip}/a.zip") is False
    # 公网地址（其中一个记录不可路由不阻止）
    monkeypatch.setattr(
        log_file_module.socket, "getaddrinfo", fake_getaddrinfo(["8.8.8.8", "10.0.0.1"])
    )
    assert log_file_module._validate_remote_url("http://example.com/a.zip") is False
    monkeypatch.setattr(log_file_module.socket, "getaddrinfo", fake_getaddrinfo(["8.8.8.8"]))
    assert log_file_module._validate_remote_url("http://example.com/a.zip") is True
    assert log_file_module._validate_remote_url("https://example.com/a.zip") is True

    # DNS 解析失败
    def raise_gaierror(host, port):
        raise socket.gaierror("dns failed")

    monkeypatch.setattr(log_file_module.socket, "getaddrinfo", raise_gaierror)
    assert log_file_module._validate_remote_url("http://example.com/a.zip") is False

    # getaddrinfo 返回了非法 IP 字符串
    monkeypatch.setattr(log_file_module.socket, "getaddrinfo", fake_getaddrinfo(["999.999.999.999"]))
    assert log_file_module._validate_remote_url("http://example.com/a.zip") is False


def test_is_profiling_log(tmp_path):
    profiling = tmp_path / "profiling.log"
    profiling.write_text("timeStamp: 1786000061000000 xxx\n", encoding="utf-8")
    assert log_file_module._is_profiling_log(profiling) is True

    normal = tmp_path / "normal.log"
    normal.write_text("2026-08-01 INFO started\n", encoding="utf-8")
    assert log_file_module._is_profiling_log(normal) is False

    assert log_file_module._is_profiling_log(tmp_path / "missing.log") is False
    # 目录不是可读文件 -> IOError 分支
    assert log_file_module._is_profiling_log(tmp_path) is False


def test_mask_counts_until_complete():
    running = LogFileModel(overall_status="running", anomaly_cnt=3, trace_failure_event_cnt=2)
    LogFileService._mask_counts_until_complete(running)
    assert running.anomaly_cnt == 0
    assert running.trace_failure_event_cnt == 0

    for status in (TaskStatusEnum.SUCCESSFUL.value, TaskStatusEnum.SUCCESSFUL_PENDING_REMOVE.value):
        done = LogFileModel(overall_status=status, anomaly_cnt=3, trace_failure_event_cnt=2)
        LogFileService._mask_counts_until_complete(done)
        assert done.anomaly_cnt == 3
        assert done.trace_failure_event_cnt == 2


def test_aggregate_task_status_matrix():
    aggregate = LogFileService._aggregate_task_status
    assert aggregate() == "unknown"
    assert aggregate(None, None) == "unknown"

    def task(status, retry_times=0):
        return SimpleNamespace(status=status, retry_times=retry_times)

    assert aggregate(task(TaskStatusEnum.FAILED_PENDING_REMOVE)) == "retrying"
    assert aggregate(task(TaskStatusEnum.RUNNING, retry_times=2)) == "retrying"
    assert aggregate(task(TaskStatusEnum.PENDING, retry_times=1)) == "retrying"
    assert aggregate(task(TaskStatusEnum.RUNNING)) == "running"
    assert aggregate(task(TaskStatusEnum.PENDING)) == "pending"
    assert aggregate(task(TaskStatusEnum.FAILED)) == "failed"
    assert aggregate(task(TaskStatusEnum.CANCELLED)) == "cancelled"
    assert aggregate(task(TaskStatusEnum.SUCCESSFUL_PENDING_REMOVE)) == "successful_pending_remove"
    assert aggregate(task(TaskStatusEnum.SUCCESSFUL)) == "successful"
    # 优先级组合
    assert aggregate(task(TaskStatusEnum.FAILED), task(TaskStatusEnum.SUCCESSFUL)) == "failed"
    assert aggregate(task(TaskStatusEnum.SUCCESSFUL), task(TaskStatusEnum.PENDING)) == "pending"


def test_select_visible_task_matrix():
    select = LogFileService._select_visible_task
    failed = SimpleNamespace(status=TaskStatusEnum.FAILED)
    running = SimpleNamespace(status=TaskStatusEnum.RUNNING)
    successful = SimpleNamespace(status=TaskStatusEnum.SUCCESSFUL)
    store = SimpleNamespace(status=TaskStatusEnum.SUCCESSFUL)

    assert select(None, None, None) is None
    # 无解析任务 -> 诊断/存储任务可见
    assert select(None, running, None) is running
    assert select(None, None, store) is store
    # 无诊断任务 -> 解析任务可见
    assert select(running, None, None) is running
    # 解析未成功 -> 解析任务可见
    assert select(failed, successful, store) is failed
    assert select(running, successful, store) is running
    # 解析成功但诊断失败/未成功 -> 诊断任务可见
    assert select(successful, failed, None) is failed
    assert select(successful, running, None) is running
    # 全部成功且有存储任务 -> 存储任务可见
    assert select(successful, successful, store) is store
    # 全部成功且无存储任务 -> 诊断任务可见
    assert select(successful, successful, None) is successful


def test_select_brpc_visible_task_matrix():
    select = LogFileService._select_brpc_visible_task
    running = SimpleNamespace(status=TaskStatusEnum.RUNNING)
    pending = SimpleNamespace(status=TaskStatusEnum.PENDING)
    failed = SimpleNamespace(status=TaskStatusEnum.FAILED)
    cancelled = SimpleNamespace(status=TaskStatusEnum.CANCELLED)
    successful = SimpleNamespace(status=TaskStatusEnum.SUCCESSFUL)

    assert select(None, None) is None
    assert select(running, pending) is running
    assert select(pending, running) is running  # RUNNING 优先，返回诊断任务
    assert select(failed, pending) is pending
    assert select(cancelled, failed) is cancelled
    assert select(successful, failed) is failed
    assert select(successful, successful) is successful


def test_populate_brpc_counts_swallows_errors(monkeypatch):
    from latency.database.managers.brpc_diagnosis import BrpcDiagnosisPGManager
    from latency.database.managers.brpc_profiling_result import (
        BrpcProfilingResultPGManager,
    )

    model = LogFileModel(id="lf-1")
    parse = make_current_task("t-1", "lf-1", TaskStatusEnum.SUCCESSFUL, TaskTypeEnum.BRPC_LOG_PARSE_WORKER)
    diag = make_current_task("t-2", "lf-1", TaskStatusEnum.SUCCESSFUL, TaskTypeEnum.BRPC_LOG_DIAGNOSIS_WORKER)
    monkeypatch.setattr(log_file_module, "PGManager", make_fake_pg_manager(session_error=True))
    monkeypatch.setattr(
        BrpcProfilingResultPGManager,
        "count_files_by_log_id",
        AsyncMock(side_effect=RuntimeError("query failed")),
    )
    run(LogFileService._populate_brpc_counts(model, parse, diag))
    # 两个统计查询失败都不向外抛异常，计数保持原值
    assert model.anomaly_cnt == 0
    assert model.trace_failure_event_cnt == 0


def test_get_upload_path_and_remove_local_file(monkeypatch, tmp_path):
    monkeypatch.setattr(log_file_module.os, "makedirs", lambda *args, **kwargs: None)
    path = LogFileService.get_upload_path("a.zip")
    assert path.endswith(os.path.join("file_upload", "a.zip"))

    # 正常删除
    target = tmp_path / "tmp.zip"
    target.write_bytes(b"data")
    LogFileService.remove_local_file(str(target))
    assert not target.exists()
    # 不存在的文件静默跳过
    LogFileService.remove_local_file(str(tmp_path / "missing.zip"))
    # 删除失败仅记录日志
    target = tmp_path / "keep.zip"
    target.write_bytes(b"data")

    def raise_remove(path):
        raise OSError("read-only")

    monkeypatch.setattr(log_file_module.os, "remove", raise_remove)
    LogFileService.remove_local_file(str(target))
    assert target.exists()


def test_get_readable_dir_size_skips_unreadable_files(monkeypatch, tmp_path):
    (tmp_path / "a.log").write_bytes(b"123")
    (tmp_path / "b.log").write_bytes(b"12345")
    (tmp_path / "bad.bin").write_bytes(b"12345678")
    real_getsize = os.path.getsize

    def fake_getsize(path):
        if str(path).endswith("bad.bin"):
            raise OSError("permission denied")
        return real_getsize(path)

    monkeypatch.setattr(log_file_module.os.path, "getsize", fake_getsize)
    size = run(LogFileService.get_readable_dir_size(str(tmp_path)))
    assert size == 8


def _patch_upload_targets(monkeypatch, tmp_path=None):
    monkeypatch.setattr(
        log_file_module.os, "makedirs", lambda *args, **kwargs: None
    )
    if tmp_path is not None:

        def fake_get_upload_path(*paths):
            return os.path.join(str(tmp_path), *paths)

        monkeypatch.setattr(
            LogFileService, "get_upload_path", staticmethod(fake_get_upload_path)
        )
    # add_log_files 按传入模型回显真实 id，供任务初始化循环查表
    add_log_files = AsyncMock(side_effect=lambda models: [m.id for m in models])
    monkeypatch.setattr(LogFilePGManager, "add_log_files", add_log_files)
    init_task = AsyncMock(return_value="task-1")
    monkeypatch.setattr(TaskHandler, "init_task", init_task)
    return add_log_files, init_task


def _upload_req(configs, parse_config=None):
    return UpLoadLogFilesRequest(
        upload_log_file_configs=configs, parse_config=parse_config
    )


def _local_config(source, log_type=DiagnosisConfigLogType.KVCACHE, name=None):
    return UpLoadLogFileConfig(
        source_type=SourceType.LOCAL, source=str(source), log_type=log_type, name=name
    )


def test_upload_local_directory_creates_kv_cache_tasks(monkeypatch, tmp_path):
    log_dir = tmp_path / "logs"
    log_dir.mkdir()
    (log_dir / "a.log").write_bytes(b"123")
    (log_dir / "b.log").write_bytes(b"12345")
    add_log_files, init_task = _patch_upload_targets(monkeypatch)
    parse_config = ParseConfig(start_time="2026-08-01 00:00:00")

    msg = run(
        LogFileService.upload_log_files(
            "kb-1",
            _upload_req(
                [_local_config(log_dir, name="logs.zip")], parse_config=parse_config
            ),
        )
    )
    model = add_log_files.await_args.args[0][0]
    assert msg.log_file_ids == [model.id]
    assert model.file_path == str(log_dir)
    assert model.file_size == 8
    assert model.name == "logs.zip"

    call_types = [c.kwargs["task_type"] for c in init_task.await_args_list]
    assert call_types == [
        TaskTypeEnum.KV_CACHE_LOG_PARSE_WORKER,
        TaskTypeEnum.KV_CACHE_LOG_EVENT_DIAGNOSIS_WORKER,
        TaskTypeEnum.STORE_TRACE_CONTEXT_LOGS_WORKER,
    ]
    assert all(c.kwargs["op_id"] == model.id for c in init_task.await_args_list)
    assert init_task.await_args_list[0].kwargs["parse_config"] is parse_config


def test_upload_local_file_and_unnamed_directory_source(monkeypatch, tmp_path):
    add_log_files, init_task = _patch_upload_targets(monkeypatch)

    # 普通文件
    plain = tmp_path / "plain.log"
    plain.write_bytes(b"abcdef")
    msg = run(
        LogFileService.upload_log_files(
            "kb-1", _upload_req([_local_config(plain)])
        )
    )
    model = add_log_files.await_args.args[0][0]
    assert model.file_size == 6
    assert model.name == "plain.log"  # 未命名时取 source basename

    # 有效压缩包
    archive = tmp_path / "logs.zip"
    with zipfile.ZipFile(archive, "w") as zf:
        zf.writestr("a.log", "123")
    msg = run(
        LogFileService.upload_log_files(
            "kb-1", _upload_req([_local_config(archive, log_type=DiagnosisConfigLogType.UBSOCKET)])
        )
    )
    assert msg.log_file_ids == [add_log_files.await_args.args[0][-1].id]
    assert [c.kwargs["task_type"] for c in init_task.await_args_list[-2:]] == [
        TaskTypeEnum.BRPC_LOG_PARSE_WORKER,
        TaskTypeEnum.BRPC_LOG_DIAGNOSIS_WORKER,
    ]


@pytest.mark.skipif(
    hasattr(os, "geteuid") and os.geteuid() == 0,
    reason="root 用户下 chmod 权限检查无效",
)
def test_upload_local_bad_paths_rejected(monkeypatch, tmp_path):
    _patch_upload_targets(monkeypatch)

    # 路径不存在
    with pytest.raises(BadRequestBizException, match="路径不存在"):
        run(
            LogFileService.upload_log_files(
                "kb-1", _upload_req([_local_config(tmp_path / "nope.log")])
            )
        )
    # 既不是文件也不是目录
    with pytest.raises(BadRequestBizException, match="既不是文件也不是目录"):
        run(LogFileService.upload_log_files("kb-1", _upload_req([_local_config("/dev/null")])))
    # 无效压缩包
    bad_zip = tmp_path / "bad.zip"
    bad_zip.write_bytes(b"not a zip archive")
    with pytest.raises(BadRequestBizException, match="不是有效的"):
        run(
            LogFileService.upload_log_files(
                "kb-1", _upload_req([_local_config(bad_zip)])
            )
        )
    # 文件不可读
    locked_file = tmp_path / "locked.log"
    locked_file.write_bytes(b"x")
    locked_file.chmod(0o000)
    with pytest.raises(BadRequestBizException, match="文件不可读"):
        run(
            LogFileService.upload_log_files("kb-1", _upload_req([_local_config(locked_file)]))
        )
    # 目录不可读
    locked_dir = tmp_path / "locked_dir"
    locked_dir.mkdir()
    (locked_dir / "a.log").write_bytes(b"x")
    locked_dir.chmod(0o000)
    with pytest.raises(BadRequestBizException, match="目录不可读"):
        run(LogFileService.upload_log_files("kb-1", _upload_req([_local_config(locked_dir)])))


def test_upload_local_unsupported_source_type_rejected(monkeypatch):
    add_log_files, _ = _patch_upload_targets(monkeypatch)
    # schema 层无法构造非法 source_type，用 model_construct 直达服务分支
    req = UpLoadLogFilesRequest.model_construct(
        upload_log_file_configs=[
            SimpleNamespace(source_type="weird", source="/tmp/x", log_type=DiagnosisConfigLogType.KVCACHE, name=None)
        ]
    )
    with pytest.raises(BadRequestBizException, match="不支持的日志文件来源类型"):
        run(LogFileService.upload_log_files("kb-1", req))
    add_log_files.assert_not_awaited()


class _FakeRemoteResponse:
    def __init__(self, payload):
        self._payload = payload

    def raise_for_status(self):
        pass

    async def read(self):
        return self._payload


class _FakeRemoteGet:
    def __init__(self, payload):
        self._payload = payload

    async def __aenter__(self):
        return _FakeRemoteResponse(self._payload)

    async def __aexit__(self, *exc):
        return False


class _FakeRemoteSession:
    def __init__(self, payload):
        self._payload = payload

    def get(self, *args, **kwargs):
        return _FakeRemoteGet(self._payload)

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return False


class _FailingRemoteSession:
    async def __aenter__(self):
        raise OSError("connect refused")

    async def __aexit__(self, *exc):
        return False


def test_upload_remote_invalid_url_and_suffix(monkeypatch):
    add_log_files, _ = _patch_upload_targets(monkeypatch)
    monkeypatch.setattr(log_file_module, "_validate_remote_url", lambda url: False)
    with pytest.raises(BadRequestBizException, match="不允许的远程日志URL"):
        run(
            LogFileService.upload_log_files(
                "kb-1",
                _upload_req(
                    [
                        UpLoadLogFileConfig(
                            source_type=SourceType.REMOTE,
                            source="http://10.0.0.1/a.zip",
                            log_type=DiagnosisConfigLogType.KVCACHE,
                        )
                    ]
                ),
            )
        )

    # URL 无支持的压缩后缀
    monkeypatch.setattr(log_file_module, "_validate_remote_url", lambda url: True)
    with pytest.raises(BadRequestBizException, match="仅支持以下压缩格式"):
        run(
            LogFileService.upload_log_files(
                "kb-1",
                _upload_req(
                    [
                        UpLoadLogFileConfig(
                            source_type=SourceType.REMOTE,
                            source="http://example.com/a.log",
                            log_type=DiagnosisConfigLogType.KVCACHE,
                        )
                    ]
                ),
            )
        )
    add_log_files.assert_not_awaited()


def test_upload_remote_download_failure_and_bad_archive(monkeypatch, tmp_path):
    add_log_files, _ = _patch_upload_targets(monkeypatch, tmp_path)
    monkeypatch.setattr(log_file_module, "_validate_remote_url", lambda url: True)
    removed = []
    monkeypatch.setattr(
        LogFileService, "remove_local_file", staticmethod(lambda p: removed.append(p))
    )

    # 下载失败
    monkeypatch.setattr(
        log_file_module.aiohttp, "ClientSession", lambda *a, **k: _FailingRemoteSession()
    )
    with pytest.raises(BadRequestBizException, match="下载远程日志文件失败"):
        run(
            LogFileService.upload_log_files(
                "kb-1",
                _upload_req(
                    [
                        UpLoadLogFileConfig(
                            source_type=SourceType.REMOTE,
                            source="http://example.com/a.zip",
                            log_type=DiagnosisConfigLogType.KVCACHE,
                        )
                    ]
                ),
            )
        )
    assert len(removed) == 1
    add_log_files.assert_not_awaited()

    # 下载成功但不是有效压缩包
    monkeypatch.setattr(
        log_file_module.aiohttp,
        "ClientSession",
        lambda *a, **k: _FakeRemoteSession(b"not a zip"),
    )
    monkeypatch.setattr(log_file_module, "is_valid_archive_file", lambda path: False)
    with pytest.raises(BadRequestBizException, match="不是有效的"):
        run(
            LogFileService.upload_log_files(
                "kb-1",
                _upload_req(
                    [
                        UpLoadLogFileConfig(
                            source_type=SourceType.REMOTE,
                            source="http://example.com/a.zip",
                            log_type=DiagnosisConfigLogType.KVCACHE,
                        )
                    ]
                ),
            )
        )
    assert len(removed) == 2


def test_upload_remote_archive_creates_brpc_tasks(monkeypatch, tmp_path):
    add_log_files, init_task = _patch_upload_targets(monkeypatch, tmp_path)
    monkeypatch.setattr(log_file_module, "_validate_remote_url", lambda url: True)
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as zf:
        zf.writestr("brpc.log", "timeStamp: x\n")
    monkeypatch.setattr(
        log_file_module.aiohttp,
        "ClientSession",
        lambda *a, **k: _FakeRemoteSession(buffer.getvalue()),
    )
    monkeypatch.setattr(log_file_module, "is_valid_archive_file", lambda path: True)

    msg = run(
        LogFileService.upload_log_files(
            "kb-1",
            _upload_req(
                [
                    UpLoadLogFileConfig(
                        source_type=SourceType.REMOTE,
                        source="http://example.com/brpc.zip",
                        log_type=DiagnosisConfigLogType.UBSOCKET,
                    )
                ]
            ),
        )
    )
    model = add_log_files.await_args.args[0][0]
    assert msg.log_file_ids == [model.id]
    assert model.file_path.endswith(".zip") and (model.id + ".zip") in model.file_path
    assert model.file_size == len(buffer.getvalue())
    assert [c.kwargs["task_type"] for c in init_task.await_args_list] == [
        TaskTypeEnum.BRPC_LOG_PARSE_WORKER,
        TaskTypeEnum.BRPC_LOG_DIAGNOSIS_WORKER,
    ]


def test_upload_file_object_flow(monkeypatch, tmp_path):
    from fastapi import UploadFile

    add_log_files, init_task = _patch_upload_targets(monkeypatch, tmp_path)

    def upload_config(log_type, content, filename):
        return UpLoadLogFileConfig(
            source_type=SourceType.UPLOAD,
            source=UploadFile(io.BytesIO(content), filename=filename),
            log_type=log_type,
        )

    # 有效 ZIP（KVCACHE）
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w") as zf:
        zf.writestr("a.log", "123")
    monkeypatch.setattr(log_file_module.ZipHandler, "is_zip_file", staticmethod(lambda path: True))
    run(
        LogFileService.upload_log_files(
            "kb-1",
            _upload_req([upload_config(DiagnosisConfigLogType.KVCACHE, zip_buffer.getvalue(), "kv.zip")]),
        )
    )
    model = add_log_files.await_args.args[0][0]
    assert model.file_size == len(zip_buffer.getvalue())

    # 纯文本 UBSocket：非 ZIP 也可直接使用
    monkeypatch.setattr(log_file_module.ZipHandler, "is_zip_file", staticmethod(lambda path: False))
    run(
        LogFileService.upload_log_files(
            "kb-1",
            _upload_req(
                [upload_config(DiagnosisConfigLogType.UBSOCKET, b"timeStamp: x\n", "brpc.log")]
            ),
        )
    )
    models = add_log_files.await_args.args[0]
    assert models[-1].file_size == len(b"timeStamp: x\n")

    # 纯文本 KVCache：跳过该文件
    add_log_files.reset_mock()
    run(
        LogFileService.upload_log_files(
            "kb-1",
            _upload_req(
                [upload_config(DiagnosisConfigLogType.KVCACHE, b"plain", "kv.log")]
            ),
        )
    )
    assert add_log_files.await_args.args[0] == []

    # 未命名上传对象：name 回退为 "unnamed"
    run(
        LogFileService.upload_log_files(
            "kb-1",
            _upload_req(
                [upload_config(DiagnosisConfigLogType.UBSOCKET, b"timeStamp: x\n", "")]
            ),
        )
    )
    assert add_log_files.await_args.args[0][-1].name == "unnamed"


@pytest.mark.filterwarnings("ignore::RuntimeWarning")
def test_upload_save_failure_skips_file(monkeypatch, tmp_path):
    from fastapi import UploadFile

    add_log_files, init_task = _patch_upload_targets(monkeypatch, tmp_path)

    async def failing_open(*args, **kwargs):
        raise OSError("disk full")

    monkeypatch.setattr(log_file_module.aiofiles, "open", failing_open)
    msg = run(
        LogFileService.upload_log_files(
            "kb-1",
            _upload_req(
                [
                    UpLoadLogFileConfig(
                        source_type=SourceType.UPLOAD,
                        source=UploadFile(io.BytesIO(b"data"), filename="a.zip"),
                        log_type=DiagnosisConfigLogType.KVCACHE,
                    )
                ]
            ),
        )
    )
    assert msg.log_file_ids == []
    add_log_files.assert_awaited_once_with([])
    init_task.assert_not_awaited()


def test_upload_task_init_failure_cleans_up(monkeypatch, tmp_path):
    log_dir = tmp_path / "logs"
    log_dir.mkdir()
    (log_dir / "a.log").write_bytes(b"123")
    add_log_files, init_task = _patch_upload_targets(monkeypatch)
    init_task.side_effect = [None, Exception("init failed"), None]
    hard_delete = AsyncMock(side_effect=[Exception("cleanup failed"), True])
    monkeypatch.setattr(
        LogFilePGManager, "hard_delete_log_file_with_related_data", hard_delete
    )

    with pytest.raises(Exception, match="init failed"):
        run(
            LogFileService.upload_log_files(
                "kb-1", _upload_req([_local_config(log_dir), _local_config(log_dir)])
            )
        )
    ids = [m.id for m in add_log_files.await_args.args[0]]
    assert hard_delete.await_count == 2
    assert [c.args[0] for c in hard_delete.await_args_list] == ids


def test_delete_log_file_not_found(monkeypatch):
    get_file = AsyncMock()
    monkeypatch.setattr(LogFilePGManager, "get_log_file_by_log_file_id", get_file)

    get_file.return_value = None
    with pytest.raises(NotFoundBizException):
        run(LogFileService.delete_log_file_by_log_file_id("missing"))

    get_file.return_value = SimpleNamespace(existed_status=False)
    with pytest.raises(NotFoundBizException):
        run(LogFileService.delete_log_file_by_log_file_id("lf-1"))


def test_delete_log_file_stops_running_task_or_fails(monkeypatch):
    get_file = AsyncMock(return_value=SimpleNamespace(existed_status=True))
    monkeypatch.setattr(LogFilePGManager, "get_log_file_by_log_file_id", get_file)
    hard_delete = AsyncMock(return_value=True)
    monkeypatch.setattr(
        LogFilePGManager, "hard_delete_log_file_with_related_data", hard_delete
    )
    stop = AsyncMock(return_value=True)
    monkeypatch.setattr(BaseWorker, "stop", stop)

    # RUNNING 任务停止失败 -> RuntimeError，且不删库
    running = make_current_task("t-1", "lf-1", TaskStatusEnum.RUNNING.value)
    monkeypatch.setattr(log_file_module, "PGManager", make_fake_pg_manager(tasks=[running]))
    stop.return_value = False
    with pytest.raises(RuntimeError, match="进程树未能确认终止"):
        run(LogFileService.delete_log_file_by_log_file_id("lf-1"))
    hard_delete.assert_not_awaited()

    # PENDING 任务停止成功 -> 正常删除
    stop.reset_mock()
    stop.return_value = True
    pending = make_current_task("t-1", "lf-1", TaskStatusEnum.PENDING.value)
    monkeypatch.setattr(log_file_module, "PGManager", make_fake_pg_manager(tasks=[pending]))
    monkeypatch.setattr(log_file_module, "cleanup_preprocess_dir", lambda lf: None)
    monkeypatch.setattr(log_file_module, "witty_dir", "/nonexistent-witty")
    msg = run(LogFileService.delete_log_file_by_log_file_id("lf-1"))
    assert msg.log_file_ids == ["lf-1"]
    stop.assert_awaited_once_with("t-1")

    # 硬删除返回 0 -> NotFound
    hard_delete.return_value = 0
    with pytest.raises(NotFoundBizException):
        run(LogFileService.delete_log_file_by_log_file_id("lf-1"))


def test_delete_log_file_cleans_directories(monkeypatch, tmp_path):
    get_file = AsyncMock(return_value=SimpleNamespace(existed_status=True))
    monkeypatch.setattr(LogFilePGManager, "get_log_file_by_log_file_id", get_file)
    monkeypatch.setattr(
        LogFilePGManager,
        "hard_delete_log_file_with_related_data",
        AsyncMock(return_value=True),
    )
    # SUCCESSFUL 任务无需停止
    done = make_current_task("t-1", "lf-000001-x", TaskStatusEnum.SUCCESSFUL.value)
    stop = AsyncMock(return_value=True)
    monkeypatch.setattr(BaseWorker, "stop", stop)
    monkeypatch.setattr(log_file_module, "PGManager", make_fake_pg_manager(tasks=[done]))
    monkeypatch.setattr(log_file_module, "cleanup_preprocess_dir", lambda lf: "/tmp/pre")
    monkeypatch.setattr(log_file_module, "witty_dir", str(tmp_path))
    diag_dir = tmp_path / "log_lf-00000"
    diag_dir.mkdir()

    msg = run(LogFileService.delete_log_file_by_log_file_id("lf-000001-x"))
    assert msg.log_file_ids == ["lf-000001-x"]
    stop.assert_not_awaited()
    assert not diag_dir.exists()

    # 清理诊断目录失败：仅记录日志
    diag_dir.mkdir()

    def raise_rmtree(path):
        raise OSError("busy")

    monkeypatch.setattr(log_file_module.shutil, "rmtree", raise_rmtree)
    monkeypatch.setattr(log_file_module, "cleanup_preprocess_dir", lambda lf: None)
    msg = run(LogFileService.delete_log_file_by_log_file_id("lf-000001-x"))
    assert msg.log_file_ids == ["lf-000001-x"]


def test_update_log_file(monkeypatch):
    get_file = AsyncMock()
    monkeypatch.setattr(LogFilePGManager, "get_log_file_by_log_file_id", get_file)
    update_file = AsyncMock(return_value=1)
    monkeypatch.setattr(LogFilePGManager, "update_log_file", update_file)

    req = UpdateLogFileRequest(
        source_type=SourceType.LOCAL, source="/tmp/a.log", log_type=DiagnosisConfigLogType.KVCACHE
    )

    get_file.return_value = None
    with pytest.raises(NotFoundBizException):
        run(LogFileService.update_log_file("missing", req))

    get_file.return_value = SimpleNamespace(existed_status=False)
    with pytest.raises(NotFoundBizException):
        run(LogFileService.update_log_file("lf-1", req))

    get_file.return_value = SimpleNamespace(existed_status=True)
    msg = run(LogFileService.update_log_file("lf-1", req))
    assert msg.log_file_id == "lf-1"

    update_file.return_value = 0
    msg = run(LogFileService.update_log_file("lf-1", req))
    assert msg.log_file_id is None


def test_run_or_stop_log_parse(monkeypatch):
    get_file = AsyncMock(return_value=SimpleNamespace(existed_status=True))
    monkeypatch.setattr(LogFilePGManager, "get_log_file_by_log_file_id", get_file)
    init_task = AsyncMock(return_value="t-new")
    monkeypatch.setattr(TaskHandler, "init_task", init_task)
    get_current = AsyncMock()
    monkeypatch.setattr(TaskPGManager, "get_current_task_by_op_id", get_current)
    stop_task = AsyncMock(return_value="t-old")
    monkeypatch.setattr(TaskHandler, "stop_task", stop_task)

    get_file.return_value = None
    with pytest.raises(NotFoundBizException):
        run(LogFileService.run_or_stop_log_parse_by_log_file_id("missing", run=True))

    # KVCACHE：直接启动解析任务
    get_file.return_value = SimpleNamespace(
        existed_status=True, log_type=DiagnosisConfigLogType.KVCACHE
    )
    msg = run(LogFileService.run_or_stop_log_parse_by_log_file_id("lf-1", run=True))
    assert msg.task_id == "t-new"
    assert init_task.await_args.kwargs["task_type"] == TaskTypeEnum.KV_CACHE_LOG_PARSE_WORKER

    # UBSocket：无当前任务 -> 解析任务；当前为诊断任务 -> 复用诊断任务
    get_file.return_value = SimpleNamespace(
        existed_status=True, log_type=DiagnosisConfigLogType.UBSOCKET
    )
    get_current.return_value = None
    run(LogFileService.run_or_stop_log_parse_by_log_file_id("lf-1", run=True))
    assert init_task.await_args.kwargs["task_type"] == TaskTypeEnum.BRPC_LOG_PARSE_WORKER

    get_current.return_value = make_current_task(
        "t-diag", "lf-1", TaskStatusEnum.SUCCESSFUL, TaskTypeEnum.BRPC_LOG_DIAGNOSIS_WORKER
    )
    run(LogFileService.run_or_stop_log_parse_by_log_file_id("lf-1", run=True))
    assert init_task.await_args.kwargs["task_type"] == TaskTypeEnum.BRPC_LOG_DIAGNOSIS_WORKER

    get_current.return_value = make_current_task(
        "t-other", "lf-1", TaskStatusEnum.SUCCESSFUL, TaskTypeEnum.KV_CACHE_LOG_PARSE_WORKER
    )
    run(LogFileService.run_or_stop_log_parse_by_log_file_id("lf-1", run=True))
    assert init_task.await_args.kwargs["task_type"] == TaskTypeEnum.BRPC_LOG_PARSE_WORKER

    # log_type 缺省 -> KVCACHE
    model = SimpleNamespace(existed_status=True, log_type=None)
    get_file.return_value = model
    run(LogFileService.run_or_stop_log_parse_by_log_file_id("lf-1", run=True))
    assert init_task.await_args.kwargs["task_type"] == TaskTypeEnum.KV_CACHE_LOG_PARSE_WORKER

    # run=False：停止运行中的任务
    get_file.return_value = SimpleNamespace(
        existed_status=True, log_type=DiagnosisConfigLogType.KVCACHE
    )
    get_current.return_value = make_current_task(
        "t-run", "lf-1", TaskStatusEnum.RUNNING, TaskTypeEnum.KV_CACHE_LOG_PARSE_WORKER
    )
    msg = run(LogFileService.run_or_stop_log_parse_by_log_file_id("lf-1", run=False))
    assert msg.task_id == "t-run"
    stop_task.assert_awaited_once_with("t-run")

    # run=False：无当前任务或任务已结束 -> task_id None
    get_current.return_value = None
    msg = run(LogFileService.run_or_stop_log_parse_by_log_file_id("lf-1", run=False))
    assert msg.task_id is None

    get_current.return_value = make_current_task(
        "t-fail", "lf-1", TaskStatusEnum.FAILED, TaskTypeEnum.KV_CACHE_LOG_PARSE_WORKER
    )
    msg = run(LogFileService.run_or_stop_log_parse_by_log_file_id("lf-1", run=False))
    assert msg.task_id is None


def test_run_brpc_diagnosis_by_log_file_id(monkeypatch):
    get_file = AsyncMock(return_value=SimpleNamespace(existed_status=True))
    monkeypatch.setattr(LogFilePGManager, "get_log_file_by_log_file_id", get_file)
    get_current = AsyncMock()
    monkeypatch.setattr(TaskPGManager, "get_current_task_by_op_id", get_current)
    init_task = AsyncMock(return_value="t-9")
    monkeypatch.setattr(TaskHandler, "init_task", init_task)

    get_file.return_value = None
    with pytest.raises(NotFoundBizException):
        run(
            LogFileService.run_brpc_diagnosis_by_log_file_id(
                "missing", RunBrpcDiagnosisRequestStub()
            )
        )

    # 诊断任务未结束 -> Conflict
    get_file.return_value = SimpleNamespace(existed_status=True)
    get_current.return_value = make_current_task(
        "t-run", "lf-1", TaskStatusEnum.RUNNING, TaskTypeEnum.BRPC_LOG_DIAGNOSIS_WORKER
    )
    with pytest.raises(ConflictBizException, match="尚未结束"):
        run(
            LogFileService.run_brpc_diagnosis_by_log_file_id(
                "lf-1", RunBrpcDiagnosisRequestStub()
            )
        )

    # 正常创建
    get_current.return_value = None
    msg = run(
        LogFileService.run_brpc_diagnosis_by_log_file_id(
            "lf-1", RunBrpcDiagnosisRequestStub()
        )
    )
    assert msg.task_id == "t-9"
    assert init_task.await_args.kwargs["task_type"] == TaskTypeEnum.BRPC_LOG_DIAGNOSIS_WORKER

    # init_task 失败 -> BadRequest
    init_task.return_value = None
    with pytest.raises(BadRequestBizException, match="创建 UBSocket 诊断任务失败"):
        run(
            LogFileService.run_brpc_diagnosis_by_log_file_id(
                "lf-1", RunBrpcDiagnosisRequestStub()
            )
        )


def RunBrpcDiagnosisRequestStub():
    from latency.schemas.request import RunBrpcDiagnosisRequest

    return RunBrpcDiagnosisRequest(start_time="2026-08-01 00:00:00")


def test_list_log_files_kv_cache_with_reports_and_fallback(monkeypatch):
    require = AsyncMock()
    monkeypatch.setattr(log_file_module.ResourceIdService, "require", require)
    monkeypatch.setattr(
        log_file_module, "parallel_overall_progress", lambda *tasks: 33.0
    )
    m_parse = LogFileModel(id="lf-kv", kb_id="kb-1", log_type=DiagnosisConfigLogType.KVCACHE, anomaly_cnt=3)
    m_fallback = LogFileModel(id="lf-fb", kb_id="kb-1", log_type=DiagnosisConfigLogType.KVCACHE)
    monkeypatch.setattr(
        LogFilePGManager,
        "list_log_files",
        AsyncMock(return_value=(2, [m_parse, m_fallback])),
    )
    parse_task = make_current_task("t-parse", "lf-kv", TaskStatusEnum.RUNNING)
    fallback_task = make_current_task("t-fb", "lf-fb", TaskStatusEnum.FAILED)
    monkeypatch.setattr(
        TaskPGManager,
        "list_current_tasks_by_op_ids",
        _fake_list_current(
            {
                TaskTypeEnum.KV_CACHE_LOG_PARSE_WORKER: [parse_task],
                None: [fallback_task],
            }
        ),
    )
    report = make_report("t-parse", hour=10)
    monkeypatch.setattr(
        TaskReportPGManager,
        "list_task_reports_by_task_ids",
        AsyncMock(return_value=[report]),
    )

    msg = run(LogFileService.list_log_files("kb-1", ListLogFilesRequest()))
    require.assert_awaited_once_with("kb", "kb-1")
    assert msg.total == 2
    assert m_parse.overall_progress == 33.0
    assert m_parse.overall_status == "running"
    assert m_parse.anomaly_cnt == 0  # 未成功 -> 计数被遮蔽
    assert m_parse.task is parse_task
    assert m_parse.task.task_reports == [report]
    # 无典型任务 -> 回退任务作为可见任务，状态取回退任务
    assert m_fallback.task is fallback_task
    assert m_fallback.overall_status == "failed"


def test_list_log_files_brpc_populates_counts(monkeypatch):
    from latency.database.managers.brpc_diagnosis import BrpcDiagnosisPGManager
    from latency.database.managers.brpc_profiling_result import (
        BrpcProfilingResultPGManager,
    )

    monkeypatch.setattr(log_file_module.ResourceIdService, "require", AsyncMock())
    monkeypatch.setattr(log_file_module, "parallel_overall_progress", lambda *tasks: 66.0)
    model = LogFileModel(id="lf-brpc", kb_id="kb-1", log_type=DiagnosisConfigLogType.UBSOCKET)
    monkeypatch.setattr(
        LogFilePGManager, "list_log_files", AsyncMock(return_value=(1, [model]))
    )
    parse_task = make_current_task(
        "t-bparse", "lf-brpc", TaskStatusEnum.SUCCESSFUL, TaskTypeEnum.BRPC_LOG_PARSE_WORKER
    )
    diag_task = make_current_task(
        "t-bdiag", "lf-brpc", TaskStatusEnum.SUCCESSFUL, TaskTypeEnum.BRPC_LOG_DIAGNOSIS_WORKER
    )
    monkeypatch.setattr(
        TaskPGManager,
        "list_current_tasks_by_op_ids",
        _fake_list_current(
            {
                TaskTypeEnum.BRPC_LOG_PARSE_WORKER: [parse_task],
                TaskTypeEnum.BRPC_LOG_DIAGNOSIS_WORKER: [diag_task],
            }
        ),
    )
    monkeypatch.setattr(
        TaskReportPGManager,
        "list_task_reports_by_task_ids",
        AsyncMock(return_value=[]),
    )
    monkeypatch.setattr(
        BrpcProfilingResultPGManager,
        "count_files_by_log_id",
        AsyncMock(return_value=3),
    )
    batch = SimpleNamespace(hit_count=7)
    get_batch = AsyncMock(return_value=batch)
    monkeypatch.setattr(BrpcDiagnosisPGManager, "get_batch_by_task_id", get_batch)
    monkeypatch.setattr(log_file_module, "PGManager", make_fake_pg_manager())

    msg = run(LogFileService.list_log_files("kb-1", ListLogFilesRequest()))
    assert msg.total == 1
    assert model.anomaly_cnt == 3
    assert model.trace_failure_event_cnt == 7
    assert model.overall_status == "successful"
    assert model.overall_progress == 66.0
    # 两个任务都成功时展示诊断任务
    assert model.task is diag_task
    get_batch.assert_awaited_once()
    assert get_batch.await_args.args[1] == "t-bdiag"


def _fake_get_current(by_type, fallback=None):
    async def fake(op_id, task_type=None):
        if task_type is None:
            return fallback
        return by_type.get(task_type)

    return fake


def test_get_log_file_by_log_file_id(monkeypatch):
    get_file = AsyncMock()
    monkeypatch.setattr(LogFilePGManager, "get_log_file_by_log_file_id", get_file)

    get_file.return_value = None
    with pytest.raises(NotFoundBizException):
        run(LogFileService.get_log_file_by_log_file_id("missing"))

    get_file.return_value = SimpleNamespace(existed_status=False)
    with pytest.raises(NotFoundBizException):
        run(LogFileService.get_log_file_by_log_file_id("lf-1"))

    # UBSocket：解析/诊断任务均成功 -> 计数填充，展示诊断任务
    monkeypatch.setattr(
        log_file_module, "parallel_overall_progress", lambda *tasks: 50.0
    )
    from latency.database.managers.brpc_diagnosis import BrpcDiagnosisPGManager
    from latency.database.managers.brpc_profiling_result import (
        BrpcProfilingResultPGManager,
    )

    ub_model = LogFileModel(id="lf-brpc", kb_id="kb-1", log_type=DiagnosisConfigLogType.UBSOCKET)
    get_file.return_value = ub_model
    parse_task = make_current_task(
        "t-bparse", "lf-brpc", TaskStatusEnum.SUCCESSFUL, TaskTypeEnum.BRPC_LOG_PARSE_WORKER
    )
    diag_task = make_current_task(
        "t-bdiag", "lf-brpc", TaskStatusEnum.SUCCESSFUL, TaskTypeEnum.BRPC_LOG_DIAGNOSIS_WORKER
    )
    monkeypatch.setattr(
        TaskPGManager,
        "get_current_task_by_op_id",
        _fake_get_current(
            {
                TaskTypeEnum.BRPC_LOG_PARSE_WORKER: parse_task,
                TaskTypeEnum.BRPC_LOG_DIAGNOSIS_WORKER: diag_task,
            }
        ),
    )
    monkeypatch.setattr(
        TaskReportPGManager,
        "list_task_reports_by_task_ids",
        AsyncMock(return_value=[]),
    )
    monkeypatch.setattr(
        BrpcProfilingResultPGManager, "count_files_by_log_id", AsyncMock(return_value=5)
    )
    monkeypatch.setattr(
        BrpcDiagnosisPGManager,
        "get_batch_by_task_id",
        AsyncMock(return_value=SimpleNamespace(hit_count=9)),
    )
    monkeypatch.setattr(log_file_module, "PGManager", make_fake_pg_manager())
    msg = run(LogFileService.get_log_file_by_log_file_id("lf-brpc"))
    assert msg.log_file is ub_model
    assert ub_model.anomaly_cnt == 5
    assert ub_model.trace_failure_event_cnt == 9
    assert ub_model.overall_status == "successful"
    assert ub_model.task is diag_task

    # KVCache：解析任务运行中
    kv_model = LogFileModel(id="lf-kv", kb_id="kb-1", log_type=DiagnosisConfigLogType.KVCACHE, anomaly_cnt=2)
    get_file.return_value = kv_model
    parse_task = make_current_task("t-parse", "lf-kv", TaskStatusEnum.RUNNING)
    monkeypatch.setattr(
        TaskPGManager,
        "get_current_task_by_op_id",
        _fake_get_current({TaskTypeEnum.KV_CACHE_LOG_PARSE_WORKER: parse_task}),
    )
    msg = run(LogFileService.get_log_file_by_log_file_id("lf-kv"))
    assert kv_model.overall_status == "running"
    assert kv_model.anomaly_cnt == 0
    assert kv_model.task is parse_task

    # 无任何任务 -> unknown 并遮蔽计数
    empty_model = LogFileModel(id="lf-none", kb_id="kb-1", log_type=DiagnosisConfigLogType.KVCACHE, anomaly_cnt=2)
    get_file.return_value = empty_model
    monkeypatch.setattr(
        TaskPGManager, "get_current_task_by_op_id", _fake_get_current({}, fallback=None)
    )
    msg = run(LogFileService.get_log_file_by_log_file_id("lf-none"))
    assert empty_model.overall_status == "unknown"
    assert empty_model.anomaly_cnt == 0
    assert empty_model.task is None

    # 类型化任务均缺失 -> 回退任务
    fb_model = LogFileModel(id="lf-fb", kb_id="kb-1", log_type=DiagnosisConfigLogType.KVCACHE)
    get_file.return_value = fb_model
    fallback_task = make_current_task("t-fb", "lf-fb", TaskStatusEnum.FAILED)
    monkeypatch.setattr(
        TaskPGManager,
        "get_current_task_by_op_id",
        _fake_get_current({}, fallback=fallback_task),
    )
    msg = run(LogFileService.get_log_file_by_log_file_id("lf-fb"))
    assert fb_model.overall_status == "failed"
    assert fb_model.task is fallback_task
