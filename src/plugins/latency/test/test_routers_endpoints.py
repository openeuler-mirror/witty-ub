"""Routers 层单元测试：FastAPI 端点、参数校验与业务异常处理器。

策略：
- 每个用例自建 FastAPI app，注册全部 router 与三个业务异常 handler（对齐
  access/fastapi_server.py 的 JSON 格式）。
- monkeypatch ResourceIdService.require/validate_request 为空实现，再
  monkeypatch 各 Service 类静态方法返回最小 Msg，隔离数据库与任务系统。
- 负路径覆盖路径参数正则（422）、请求体校验（422）、NotFound/Conflict/
  BadRequest 业务异常透传（404/409/400）。
"""

import io
import json
from datetime import datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from fastapi import FastAPI, HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.testclient import TestClient
from starlette.datastructures import UploadFile

from latency.ENUM.general import DiagnosisConfigLogType
from latency.database.managers.brpc_profiling_result import (
    BrpcProfilingResultPGManager,
)
from latency.exceptions import (
    BadRequestBizException,
    ConflictBizException,
    NotFoundBizException,
)
from latency.routers.anomalous_event import router as anomalous_event_router
from latency.routers.anomalous_event_chain import (
    router as anomalous_event_chain_router,
)
from latency.routers.brpc_diagnosis import (
    _build_metric_sort_fields,
    router as brpc_diagnosis_router,
)
from latency.routers.brpc_profiling import (
    _build_profiling_response,
    router as brpc_profiling_router,
)
from latency.routers.diagnosis_case import router as diagnosis_case_router
from latency.routers.diagnosis_config import router as diagnosis_config_router
from latency.routers.failure_mode_knowledge import router as failure_mode_router
from latency.routers.log_failure_event_result import (
    router as log_failure_event_result_router,
)
from latency.routers.log_file import router as log_file_router
from latency.routers.log_file import upload_log_files as upload_log_files_endpoint
from latency.routers.log_knowledge import router as log_knowledge_router
from latency.routers.log_parse_result import router as log_parse_result_router
from latency.routers.src_dst_aggregated_event import router as src_dst_router
from latency.routers.task import router as task_router
from latency.schemas.brpc_diagnosis import (
    BrpcAbnormalThread,
    BrpcDiagBatchMetadata,
    BrpcFailureGraph,
    BrpcKnowledgeScopeMsg,
    BrpcMetricSortField,
    BrpcPodAggregatedEvent,
    BrpcThreadAggregatedEvent,
    BrpcInterfaceTimelineSeries,
    GetBrpcAbnormalThreadDetailMsg,
    GetBrpcBatchMsg,
    GetBrpcInterfaceTimelineMsg,
    GetBrpcPodEventDetailMsg,
    GetBrpcTaskBatchMsg,
    GetBrpcThreadEventDetailMsg,
    ListBrpcAbnormalThreadsMsg,
    ListBrpcDiagHitsMsg,
    ListBrpcPodEventsMsg,
    ListBrpcThreadEventsMsg,
    format_brpc_api_time,
    parse_brpc_query_timestamp,
)
from latency.schemas.config import (
    DSLogAnalyzerConfig,
    DiagnosisConfigResult,
    KVCacheDiagnosisConfig,
    KVCacheLogFilenamePatternConfig,
    UBSocketDiagnosisConfig,
    UBSocketLogFilenamePatternConfig,
)
from latency.schemas.failure_mode import FailureModeModel, StatusCodeKnowledgeModel
from latency.schemas.response import (
    CreateDiagnosisCaseMsg,
    CreateLogKnowledgeMsg,
    CreateTaskMsg,
    DeleteLogFilesMsg,
    DeleteLogKnowledgeMsg,
    DeleteTaskMsg,
    GetAnomalousEventMsg,
    GetDiagnosisCaseMsg,
    GetErrCodeMetricsMsg,
    GetFailureModeMsg,
    GetLatencyMetricsMsg,
    GetLogFileMsg,
    GetLogKnowledgeMsg,
    GetLogParseOptionsMsg,
    GetLogParseResultMsg,
    GetSrcDstAggregatedEventMsg,
    GetStatusCodeKnowledgeMsg,
    GetTaskMsg,
    ListAnomalousEventChainsMsg,
    ListAnomalousEventsMsg,
    ListLogFailureEventResultMsg,
    ListLogFilesMsg,
    ListLogKnowledgeMsg,
    ListLogParseResultsMsg,
    ListPodAggregatedFailureEventMsg,
    ListSrcDstAggregatedFailureEventMsg,
    ListSrcDstAggregatedEventMsg,
    ListTasksMsg,
    ListTimeAggregatedFailureEventMsg,
    ListTimeWindowAggregatedEventMsg,
    ListTraceFailureEventResultMsg,
    ListTracesByHostMsg,
    RunBrpcDiagnosisMsg,
    RunOrStopLogParseMsg,
    SearchDiagnosisCasesMsg,
    StopTaskMsg,
    UpdateLogFileMsg,
    UpdateLogKnowledgeMsg,
    UploadLogFilesMsg,
)
from latency.services.anomalous_event import AnomalousEventService
from latency.services.anomalous_event_chain import AnomalousEventChainService
from latency.services.brpc_diagnosis import BrpcDiagnosisService
from latency.services.diagnosis_case import DiagnosisCaseService
from latency.services.diagnosis_config import DiagnosisConfigService
from latency.services.log_failure_event_result import LogFailureEventResultService
from latency.services.log_file import LogFileService
from latency.services.log_knowledge import LogKnowledgeService
from latency.services.failure_mode_knowledge import FailureModeKnowledge
from latency.services.log_parse_result import LogParseResultService
from latency.services.resource_id import ResourceIdService
from latency.services.src_dst_aggregated_event import SrcDstAggregatedEventService
from latency.services.task import TaskService

ALL_ROUTERS = (
    task_router,
    log_file_router,
    log_knowledge_router,
    diagnosis_case_router,
    failure_mode_router,
    diagnosis_config_router,
    anomalous_event_router,
    anomalous_event_chain_router,
    src_dst_router,
    log_failure_event_result_router,
    log_parse_result_router,
    brpc_profiling_router,
    brpc_diagnosis_router,
)

# 与 access/fastapi_server.py 相同的业务异常 -> HTTP 状态码映射


async def not_found_handler(request, exc):
    return JSONResponse(
        status_code=404,
        content={"code": 404, "message": exc.message, "result": None, "detail": exc.detail},
    )


async def conflict_handler(request, exc):
    return JSONResponse(
        status_code=409,
        content={"code": 409, "message": exc.message, "result": None, "detail": exc.detail},
    )


async def bad_request_handler(request, exc):
    return JSONResponse(
        status_code=400,
        content={"code": 400, "message": exc.message, "result": None, "detail": exc.detail},
    )


def make_client(monkeypatch, require=None):
    app = FastAPI()
    for router in ALL_ROUTERS:
        app.include_router(router)
    app.add_exception_handler(NotFoundBizException, not_found_handler)
    app.add_exception_handler(ConflictBizException, conflict_handler)
    app.add_exception_handler(BadRequestBizException, bad_request_handler)
    monkeypatch.setattr(ResourceIdService, "require", require or AsyncMock())
    monkeypatch.setattr(ResourceIdService, "validate_request", AsyncMock())
    return TestClient(app)


# ---------------------------------------------------------------------------
# routers/task.py
# ---------------------------------------------------------------------------


def test_task_router_endpoints(monkeypatch):
    client = make_client(monkeypatch)
    create_task = AsyncMock(return_value=CreateTaskMsg(task_id="t-1"))
    stop_task = AsyncMock(return_value=StopTaskMsg(task_id="t-1"))
    delete_task = AsyncMock(return_value=DeleteTaskMsg(task_id="t-1"))
    list_tasks = AsyncMock(return_value=ListTasksMsg(total=0))
    get_task = AsyncMock(return_value=GetTaskMsg())
    monkeypatch.setattr(TaskService, "create_task", create_task)
    monkeypatch.setattr(TaskService, "stop_task", stop_task)
    monkeypatch.setattr(TaskService, "delete_task", delete_task)
    monkeypatch.setattr(TaskService, "list_tasks", list_tasks)
    monkeypatch.setattr(TaskService, "get_task_by_id", get_task)

    resp = client.post(
        "/task/create",
        json={
            "task_type": "kv_cache_log_parse_worker",
            "op_id": "op-1",
            "kb_id": "kb-1",
        },
    )
    assert resp.status_code == 200
    assert resp.json()["result"] == {"task_id": "t-1"}
    assert create_task.await_args.args[0].op_id == "op-1"
    assert create_task.await_args.args[0].kb_id == "kb-1"

    resp = client.put("/task/stop/t-1")
    assert resp.status_code == 200
    assert resp.json()["result"] == {"task_id": "t-1"}
    stop_task.assert_awaited_once_with("t-1")

    resp = client.delete("/task/t-1")
    assert resp.status_code == 200
    delete_task.assert_awaited_once_with("t-1")

    resp = client.post("/task/list", json={"kb_id": "kb-1"})
    assert resp.status_code == 200
    assert resp.json()["result"] == {"total": 0, "tasks": []}
    assert list_tasks.await_args.args[0].kb_id == "kb-1"

    resp = client.get("/task/t-1")
    assert resp.status_code == 200
    assert resp.json()["result"] == {"task": None}
    get_task.assert_awaited_once_with("t-1")


def test_task_router_validation_and_errors(monkeypatch):
    client = make_client(monkeypatch)
    # 路径参数不满足 ResourceIdPath 正则
    assert client.put("/task/stop/bad!id").status_code == 422
    assert client.delete("/task/bad!id").status_code == 422
    # 缺少必填 body / 非法时间与分页
    assert client.post("/task/create", json={"task_type": "kv_cache_log_parse_worker"}).status_code == 422
    assert client.post("/task/list", json={"kb_id": "kb-1", "created_at_start": "2026-01-01"}).status_code == 422
    assert client.post("/task/list", json={"kb_id": "kb-1", "page_num": 0}).status_code == 422

    # 业务异常透传：404 / 409
    monkeypatch.setattr(TaskService, "get_task_by_id", AsyncMock(side_effect=NotFoundBizException(resource="任务")))
    resp = client.get("/task/missing")
    assert resp.status_code == 404
    assert resp.json() == {"code": 404, "message": "任务不存在", "result": None, "detail": ""}

    monkeypatch.setattr(
        TaskService,
        "stop_task",
        AsyncMock(side_effect=ConflictBizException(message="任务状态为successful，不可停止")),
    )
    resp = client.put("/task/stop/t-done")
    assert resp.status_code == 409
    assert resp.json()["message"] == "任务状态为successful，不可停止"


# ---------------------------------------------------------------------------
# routers/log_knowledge.py
# ---------------------------------------------------------------------------


def test_log_kb_router_endpoints(monkeypatch):
    client = make_client(monkeypatch)
    create_kb = AsyncMock(return_value=CreateLogKnowledgeMsg(kb_id="kb-1"))
    delete_kb = AsyncMock(return_value=DeleteLogKnowledgeMsg(kb_id="kb-1"))
    update_kb = AsyncMock(return_value=UpdateLogKnowledgeMsg(kb_id="kb-1"))
    get_kb = AsyncMock(return_value=GetLogKnowledgeMsg())
    list_kbs = AsyncMock(return_value=ListLogKnowledgeMsg(total=0))
    monkeypatch.setattr(LogKnowledgeService, "create_log_kb", create_kb)
    monkeypatch.setattr(LogKnowledgeService, "delete_log_kb_by_kb_id", delete_kb)
    monkeypatch.setattr(LogKnowledgeService, "update_log_kb", update_kb)
    monkeypatch.setattr(LogKnowledgeService, "get_log_kb_by_kb_id", get_kb)
    monkeypatch.setattr(LogKnowledgeService, "list_log_kbs", list_kbs)

    resp = client.post("/log_kb", json={"name": "kb", "description": "d"})
    assert resp.status_code == 200
    assert resp.json()["result"] == {"kb_id": "kb-1"}
    assert create_kb.await_args.args[0].name == "kb"

    resp = client.delete("/log_kb/kb-1")
    assert resp.status_code == 200
    delete_kb.assert_awaited_once_with("kb-1")

    resp = client.put("/log_kb/kb-1", json={"name": "new"})
    assert resp.status_code == 200
    update_kb.assert_awaited_once()

    resp = client.get("/log_kb/kb-1")
    assert resp.status_code == 200
    assert resp.json()["result"] == {"kb": None}
    get_kb.assert_awaited_once_with("kb-1")

    # list 不经过 ResourceIdService
    resp = client.post("/log_kb/list", json={})
    assert resp.status_code == 200
    assert resp.json()["result"] == {"total": 0, "kbs": []}

    # 缺少必填字段
    assert client.post("/log_kb", json={"name": "kb"}).status_code == 422
    assert client.delete("/log_kb/bad!id").status_code == 422

    # require 抛 NotFound -> 404
    monkeypatch.setattr(
        ResourceIdService, "require", AsyncMock(side_effect=NotFoundBizException(resource="知识库"))
    )
    assert client.get("/log_kb/missing").status_code == 404


# ---------------------------------------------------------------------------
# routers/diagnosis_case.py
# ---------------------------------------------------------------------------


def test_diagnosis_case_router_endpoints(monkeypatch):
    client = make_client(monkeypatch)
    create_case = AsyncMock(return_value=CreateDiagnosisCaseMsg(case_id="case-1"))
    get_case = AsyncMock(return_value=GetDiagnosisCaseMsg())
    search_cases = AsyncMock(return_value=SearchDiagnosisCasesMsg(total=0))
    mark_hit = AsyncMock(return_value=GetDiagnosisCaseMsg())
    monkeypatch.setattr(DiagnosisCaseService, "create_case", create_case)
    monkeypatch.setattr(DiagnosisCaseService, "get_case", get_case)
    monkeypatch.setattr(DiagnosisCaseService, "search_cases", search_cases)
    monkeypatch.setattr(DiagnosisCaseService, "mark_case_hit", mark_hit)

    body = {
        "kb_id": "kb-1",
        "symptom_summary": "慢",
        "root_cause": "网络抖动",
        "recommendation": "重启",
    }
    resp = client.post("/diagnosis_case", json=body)
    assert resp.status_code == 200
    assert resp.json()["result"] == {"case_id": "case-1"}
    assert create_case.await_args.args[0].root_cause == "网络抖动"

    resp = client.get("/diagnosis_case/case-1")
    assert resp.status_code == 200
    assert resp.json()["result"] == {"case": None}
    get_case.assert_awaited_once_with("case-1")

    resp = client.post("/diagnosis_case/search", json={"kb_id": "kb-1"})
    assert resp.status_code == 200
    assert resp.json()["result"] == {"total": 0, "matches": []}
    search_cases.assert_awaited_once()

    resp = client.post("/diagnosis_case/case-1/hit")
    assert resp.status_code == 200
    mark_hit.assert_awaited_once_with("case-1")

    # 必填字段缺失 -> 422
    assert client.post("/diagnosis_case", json={"kb_id": "kb-1"}).status_code == 422
    assert client.get("/diagnosis_case/bad!id").status_code == 422


# ---------------------------------------------------------------------------
# routers/failure_mode_knowledge.py
# ---------------------------------------------------------------------------


def test_failure_mode_router_endpoints(monkeypatch):
    client = make_client(monkeypatch)

    # 知识缺失 -> 404（service 返回 None 字段时路由转 HTTPException）
    monkeypatch.setattr(
        FailureModeKnowledge,
        "get_status_code_knowledge",
        AsyncMock(return_value=GetStatusCodeKnowledgeMsg()),
    )
    resp = client.get("/failure_mode/status_code/504")
    assert resp.status_code == 404
    assert resp.json() == {"detail": "未找到故障码 504"}

    knowledge = FailureModeKnowledge
    monkeypatch.setattr(
        knowledge,
        "get_status_code_knowledge",
        AsyncMock(
            return_value=GetStatusCodeKnowledgeMsg(
                status_code_info=StatusCodeKnowledgeModel(
                    status_code="504", symptom="超时", root_cause="网关积压"
                )
            )
        ),
    )
    resp = client.get("/failure_mode/status_code/504")
    assert resp.status_code == 200
    assert resp.json()["result"]["status_code_info"] == {
        "status_code": "504",
        "symptom": "超时",
        "root_cause": "网关积压",
    }

    monkeypatch.setattr(
        knowledge,
        "get_failure_mode_knowledege_by_id",
        AsyncMock(return_value=GetFailureModeMsg()),
    )
    # FailureModeIdPath 不允许连字符，合法样例用下划线
    resp = client.get("/failure_mode/fm_1")
    assert resp.status_code == 404
    assert resp.json() == {"detail": "未找到故障模式 fm_1"}

    monkeypatch.setattr(
        knowledge,
        "get_failure_mode_knowledege_by_id",
        AsyncMock(
            return_value=GetFailureModeMsg(
                failure_mode=FailureModeModel(
                    id="fm_1",
                    name="超时",
                    symptom="慢",
                    root_cause="拥塞",
                    solution="限流",
                    failure_domain="network",
                    children_failure_mode_ids="",
                )
            )
        ),
    )
    resp = client.get("/failure_mode/fm_1")
    assert resp.status_code == 200
    assert resp.json()["result"]["failure_mode"]["id"] == "fm_1"
    # 连字符不在 FailureModeIdPath 允许范围内 -> 422
    assert client.get("/failure_mode/fm-1").status_code == 422

    # 非法 ID -> 422
    assert client.get("/failure_mode/bad!id").status_code == 422
    assert client.get("/failure_mode/status_code/bad!code").status_code == 422


# ---------------------------------------------------------------------------
# routers/anomalous_event.py
# ---------------------------------------------------------------------------


def test_anomalous_event_router_endpoints(monkeypatch):
    client = make_client(monkeypatch)
    get_event = AsyncMock(return_value=GetAnomalousEventMsg())
    list_events = AsyncMock(return_value=ListAnomalousEventsMsg(total=0))
    list_by_log = AsyncMock(return_value=ListAnomalousEventsMsg(total=2))
    monkeypatch.setattr(AnomalousEventService, "get_anomalous_event_by_id", get_event)
    monkeypatch.setattr(AnomalousEventService, "list_anomalous_events", list_events)
    monkeypatch.setattr(
        AnomalousEventService, "list_anomalous_events_by_log_id", list_by_log
    )

    resp = client.get("/anomalous_event/ev-1")
    assert resp.status_code == 200
    assert resp.json()["result"] == {"event": None}
    get_event.assert_awaited_once_with("ev-1")

    resp = client.post(
        "/anomalous_event/list", json={"kb_id": "kb-1", "log_id": "lf-1"}
    )
    assert resp.status_code == 200
    assert resp.json()["result"] == {"total": 0, "events": []}
    assert list_events.await_args.args[0].log_id == "lf-1"

    resp = client.get("/anomalous_event/log/lf-1")
    assert resp.status_code == 200
    assert resp.json()["result"]["total"] == 2
    list_by_log.assert_awaited_once_with("lf-1")

    # 合法 sort_fields 可通过
    resp = client.post(
        "/anomalous_event/list",
        json={
            "kb_id": "kb-1",
            "sort_fields": [{"field": "created_at", "order": "desc"}],
        },
    )
    assert resp.status_code == 200

    # 校验失败：路径正则 / 必填字段 / 分页下限
    assert client.get("/anomalous_event/bad!id").status_code == 422
    assert client.get("/anomalous_event/log/bad!id").status_code == 422
    assert client.post("/anomalous_event/list", json={}).status_code == 422
    assert (
        client.post(
            "/anomalous_event/list", json={"kb_id": "kb-1", "page_num": 0}
        ).status_code
        == 422
    )

    monkeypatch.setattr(
        AnomalousEventService,
        "get_anomalous_event_by_id",
        AsyncMock(side_effect=NotFoundBizException(resource="异常事件")),
    )
    resp = client.get("/anomalous_event/missing")
    assert resp.status_code == 404
    assert resp.json()["message"] == "异常事件不存在"


# ---------------------------------------------------------------------------
# routers/anomalous_event_chain.py
# ---------------------------------------------------------------------------


def test_anomalous_event_chain_router_endpoints(monkeypatch):
    client = make_client(monkeypatch)
    list_chains = AsyncMock(return_value=ListAnomalousEventChainsMsg(total=0))
    monkeypatch.setattr(AnomalousEventChainService, "list_event_chains", list_chains)

    resp = client.post("/anomalous_event_chain/list", json={"kb_id": "kb-1"})
    assert resp.status_code == 200
    assert resp.json()["result"] == {"total": 0, "event_chains": []}
    assert list_chains.await_args.args[0].kb_id == "kb-1"

    resp = client.post(
        "/anomalous_event_chain/list", json={"kb_id": "kb-1", "log_id": "lf-1"}
    )
    assert resp.status_code == 200
    assert list_chains.await_count == 2

    assert client.post("/anomalous_event_chain/list", json={}).status_code == 422
    assert (
        client.post(
            "/anomalous_event_chain/list", json={"kb_id": "kb-1", "page_num": 0}
        ).status_code
        == 422
    )


# ---------------------------------------------------------------------------
# routers/src_dst_aggregated_event.py（前缀 /aggregated_event）
# ---------------------------------------------------------------------------


def test_aggregated_event_router_endpoints(monkeypatch):
    client = make_client(monkeypatch)
    list_events = AsyncMock(return_value=ListSrcDstAggregatedEventMsg(total=0))
    get_event = AsyncMock(return_value=GetSrcDstAggregatedEventMsg())
    list_windows = AsyncMock(return_value=ListTimeWindowAggregatedEventMsg(total=0))
    monkeypatch.setattr(
        SrcDstAggregatedEventService, "list_aggregated_events", list_events
    )
    monkeypatch.setattr(
        SrcDstAggregatedEventService, "get_aggregated_event_by_id", get_event
    )
    monkeypatch.setattr(
        SrcDstAggregatedEventService, "list_time_window_events", list_windows
    )

    resp = client.post(
        "/aggregated_event/list", json={"kb_id": "kb-1", "src_ip": "10.0.0.1"}
    )
    assert resp.status_code == 200
    assert resp.json()["result"] == {"total": 0, "events": []}
    assert list_events.await_args.args[0].src_ip == "10.0.0.1"

    resp = client.get("/aggregated_event/ev-1")
    assert resp.status_code == 200
    assert resp.json()["result"] == {"event": None}
    get_event.assert_awaited_once_with("ev-1")

    resp = client.post("/aggregated_event/list_time_window", json={"kb_id": "kb-1"})
    assert resp.status_code == 200
    assert resp.json()["result"] == {"total": 0, "events": []}
    list_windows.assert_awaited_once()

    # 校验失败：时间格式 / 路径正则 / 必填字段 / 分页下限
    assert (
        client.post(
            "/aggregated_event/list",
            json={"kb_id": "kb-1", "start_time": "2026-01-01"},
        ).status_code
        == 422
    )
    assert client.get("/aggregated_event/bad!id").status_code == 422
    assert client.post("/aggregated_event/list", json={}).status_code == 422
    assert (
        client.post(
            "/aggregated_event/list_time_window", json={"kb_id": "kb-1", "page_num": 0}
        ).status_code
        == 422
    )

    monkeypatch.setattr(
        SrcDstAggregatedEventService,
        "get_aggregated_event_by_id",
        AsyncMock(side_effect=NotFoundBizException(resource="聚合事件")),
    )
    resp = client.get("/aggregated_event/missing")
    assert resp.status_code == 404
    assert resp.json()["message"] == "聚合事件不存在"


# ---------------------------------------------------------------------------
# routers/log_failure_event_result.py
# ---------------------------------------------------------------------------


def test_log_failure_event_result_router_endpoints(monkeypatch):
    client = make_client(monkeypatch)
    mocks = {
        "list_log_failure_event_result": AsyncMock(
            return_value=ListLogFailureEventResultMsg(total=0)
        ),
        "list_trace_failure_event_result": AsyncMock(
            return_value=ListTraceFailureEventResultMsg(total=0)
        ),
        "list_time_aggregated_failure_event_result": AsyncMock(
            return_value=ListTimeAggregatedFailureEventMsg(
                total=0, err_codes=["1004"]
            )
        ),
        "list_pod_aggregated_failure_event_result": AsyncMock(
            return_value=ListPodAggregatedFailureEventMsg(total=0)
        ),
        "list_src_dst_aggregated_failure_event_result": AsyncMock(
            return_value=ListSrcDstAggregatedFailureEventMsg(total=0)
        ),
        "get_err_code_metrics": AsyncMock(return_value=GetErrCodeMetricsMsg(total=0)),
    }
    for name, mock in mocks.items():
        monkeypatch.setattr(LogFailureEventResultService, name, mock)

    resp = client.post(
        "/log_failure_event_result/list_log_events",
        json={"kb_id": "kb-1", "trace_ids": ["tr-1"]},
    )
    assert resp.status_code == 200
    assert resp.json()["result"] == {"total": 0, "log_failure_event_results": []}
    assert mocks["list_log_failure_event_result"].await_args.args[0].trace_ids == [
        "tr-1"
    ]

    resp = client.post(
        "/log_failure_event_result/list_trace_events",
        json={"kb_id": "kb-1", "src_ip": "1.1.1.1"},
    )
    assert resp.status_code == 200
    assert resp.json()["result"] == {"total": 0, "trace_failure_event_results": []}
    assert (
        mocks["list_trace_failure_event_result"].await_args.kwargs["req"].src_ip
        == "1.1.1.1"
    )

    resp = client.post(
        "/log_failure_event_result/list_time_aggregated_failure_events",
        json={"kb_id": "kb-1"},
    )
    assert resp.status_code == 200
    assert resp.json()["result"] == {"total": 0, "err_codes": ["1004"], "events": []}
    assert (
        mocks["list_time_aggregated_failure_event_result"].await_args.kwargs[
            "req"
        ].kb_id
        == "kb-1"
    )

    resp = client.post(
        "/log_failure_event_result/list_pod_aggregated_failure_events",
        json={"kb_id": "kb-1", "sort_by": "1004"},
    )
    assert resp.status_code == 200
    assert resp.json()["result"] == {"total": 0, "events": []}
    assert (
        mocks["list_pod_aggregated_failure_event_result"].await_args.kwargs[
            "req"
        ].sort_by
        == "1004"
    )

    resp = client.post(
        "/log_failure_event_result/list_src_dst_aggregated_failure_events",
        json={"kb_id": "kb-1", "dst_ip": "2.2.2.2"},
    )
    assert resp.status_code == 200
    assert resp.json()["result"] == {"total": 0, "events": []}
    assert (
        mocks["list_src_dst_aggregated_failure_event_result"].await_args.kwargs[
            "req"
        ].dst_ip
        == "2.2.2.2"
    )

    resp = client.post(
        "/log_failure_event_result/metrics/err_code",
        json={"kb_id": "kb-1", "err_codes": ["1004"]},
    )
    assert resp.status_code == 200
    assert resp.json()["result"] == {"total": 0, "metrics": {}, "time_range": {}}
    assert mocks["get_err_code_metrics"].await_args.args[0].err_codes == ["1004"]

    # 校验失败：必填字段 / 分页下限 / 时间格式
    assert (
        client.post("/log_failure_event_result/list_log_events", json={}).status_code
        == 422
    )
    assert (
        client.post(
            "/log_failure_event_result/list_trace_events",
            json={"kb_id": "kb-1", "page_num": 0},
        ).status_code
        == 422
    )
    assert (
        client.post(
            "/log_failure_event_result/list_time_aggregated_failure_events",
            json={"kb_id": "kb-1", "start_time": "bad"},
        ).status_code
        == 422
    )
    assert (
        client.post(
            "/log_failure_event_result/list_pod_aggregated_failure_events",
            json={"kb_id": "kb-1", "end_time": "2026-01-01"},
        ).status_code
        == 422
    )
    assert (
        client.post("/log_failure_event_result/metrics/err_code", json={}).status_code
        == 422
    )


# ---------------------------------------------------------------------------
# routers/log_parse_result.py
# ---------------------------------------------------------------------------


def test_log_parse_result_router_endpoints(monkeypatch):
    client = make_client(monkeypatch)
    list_results = AsyncMock(return_value=ListLogParseResultsMsg(total=0))
    get_result = AsyncMock(return_value=GetLogParseResultMsg())
    list_traces = AsyncMock(return_value=ListTracesByHostMsg(total=0))
    metrics = AsyncMock(return_value=GetLatencyMetricsMsg(total=0))
    options = AsyncMock(
        return_value=GetLogParseOptionsMsg(clusters=["c1"], hosts=["h1"])
    )
    monkeypatch.setattr(LogParseResultService, "list_log_parse_results", list_results)
    monkeypatch.setattr(LogParseResultService, "get_log_parse_result_by_id", get_result)
    monkeypatch.setattr(LogParseResultService, "list_traces_by_host", list_traces)
    monkeypatch.setattr(LogParseResultService, "get_latency_metrics", metrics)
    monkeypatch.setattr(LogParseResultService, "get_log_parse_options", options)

    resp = client.post("/log_parse_result/list", json={"kb_id": "kb-1"})
    assert resp.status_code == 200
    assert resp.json()["result"] == {"total": 0, "log_parse_results": []}
    assert list_results.await_args.args[0].kb_id == "kb-1"

    resp = client.get("/log_parse_result/options?kb_id=kb-1")
    assert resp.status_code == 200
    assert resp.json()["result"] == {"clusters": ["c1"], "hosts": ["h1"]}
    options.assert_awaited_once_with("kb-1")

    resp = client.get("/log_parse_result/lpr-1")
    assert resp.status_code == 200
    assert resp.json()["result"] == {"log_parse_result": None}
    get_result.assert_awaited_once_with("lpr-1")

    resp = client.post(
        "/log_parse_result/traces/host/list", json={"host": "h1", "kb_id": "kb-1"}
    )
    assert resp.status_code == 200
    assert resp.json()["result"] == {"total": 0, "traces": []}
    assert list_traces.await_args.args[0].host == "h1"

    resp = client.post(
        "/log_parse_result/metrics/latency",
        json={"kb_id": "kb-1", "sample_mode": "p99"},
    )
    assert resp.status_code == 200
    assert resp.json()["result"] == {
        "total": 0,
        "metrics": [],
        "time_range": {},
        "sampling_info": {},
    }
    assert metrics.await_args.args[0].sample_mode.value == "p99"

    # 校验失败：必填字段 / 查询与路径参数 / 桶粒度下限
    assert client.post("/log_parse_result/list", json={}).status_code == 422
    assert (
        client.post(
            "/log_parse_result/traces/host/list", json={"kb_id": "kb-1"}
        ).status_code
        == 422
    )
    assert client.get("/log_parse_result/options").status_code == 422
    assert client.get("/log_parse_result/options?kb_id=bad!id").status_code == 422
    assert client.get("/log_parse_result/bad!id").status_code == 422
    assert (
        client.post(
            "/log_parse_result/metrics/latency",
            json={"kb_id": "kb-1", "bucket_seconds": 0},
        ).status_code
        == 422
    )
    assert (
        client.post(
            "/log_parse_result/list",
            json={"kb_id": "kb-1", "created_at_start": "2026-01-01"},
        ).status_code
        == 422
    )

    monkeypatch.setattr(
        LogParseResultService,
        "get_log_parse_result_by_id",
        AsyncMock(side_effect=NotFoundBizException(resource="日志解析结果")),
    )
    resp = client.get("/log_parse_result/missing")
    assert resp.status_code == 404
    assert resp.json()["message"] == "日志解析结果不存在"


# ---------------------------------------------------------------------------
# routers/diagnosis_config.py
# ---------------------------------------------------------------------------


def _kv_cache_result():
    return DiagnosisConfigResult(
        log_type=DiagnosisConfigLogType.KVCACHE,
        config=KVCacheDiagnosisConfig(
            log_filename_pattern=KVCacheLogFilenamePatternConfig(
                ds_client_access_log_file=["a.log"],
                ds_client_info_log_file=["b.log"],
                ds_worker_access_log_file=["c.log"],
                ds_worker_info_log_file=["d.log"],
                resource_log_file=["e.log"],
            ),
            log_analyzer_params=DSLogAnalyzerConfig(),
        ),
    )


def test_diagnosis_config_router_endpoints(monkeypatch):
    client = make_client(monkeypatch)
    get_cfg = AsyncMock(return_value=_kv_cache_result())
    update_cfg = AsyncMock(
        side_effect=lambda kb_id, log_type, req: DiagnosisConfigResult(
            log_type=log_type, config=req
        )
    )
    reset_cfg = AsyncMock(return_value=_kv_cache_result())
    monkeypatch.setattr(DiagnosisConfigService, "get", get_cfg)
    monkeypatch.setattr(DiagnosisConfigService, "update", update_cfg)
    monkeypatch.setattr(DiagnosisConfigService, "reset", reset_cfg)

    resp = client.get("/diagnosis_config/kb-1?log_type=KVCache")
    assert resp.status_code == 200
    assert resp.json()["result"]["log_type"] == "KVCache"
    get_cfg.assert_awaited_once_with("kb-1", DiagnosisConfigLogType.KVCACHE)

    # GET 对 UBSocket 不受限，仅 PUT/RESET 受依赖保护
    resp = client.get("/diagnosis_config/kb-1?log_type=UBSocket")
    assert resp.status_code == 200
    assert get_cfg.await_args.args[1] == DiagnosisConfigLogType.UBSOCKET

    put_body = {
        "log_filename_pattern": {
            "ds_client_access_log_file": ["a.log"],
            "ds_client_info_log_file": ["b.log"],
            "ds_worker_access_log_file": ["c.log"],
            "ds_worker_info_log_file": ["d.log"],
            "resource_log_file": ["e.log"],
        },
        "log_analyzer_params": {
            "sliding_window_sizes": [100, 200],
            "sliding_window_steps": [20, 30],
        },
    }
    resp = client.put("/diagnosis_config/kb-1?log_type=KVCache", json=put_body)
    assert resp.status_code == 200
    assert resp.json()["result"]["config"]["log_analyzer_params"][
        "sliding_window_sizes"
    ] == [100, 200]
    assert update_cfg.await_args.args[0] == "kb-1"
    assert update_cfg.await_args.args[1] == DiagnosisConfigLogType.KVCACHE
    assert update_cfg.await_args.args[2].log_analyzer_params.sliding_window_sizes == [
        100,
        200,
    ]

    resp = client.post("/diagnosis_config/kb-1/reset?log_type=KVCache")
    assert resp.status_code == 200
    reset_cfg.assert_awaited_once_with("kb-1", DiagnosisConfigLogType.KVCACHE)

    # 依赖在 body 校验前执行：UBSocket -> 400（即使 body 也不合法）
    resp = client.put("/diagnosis_config/kb-1?log_type=UBSocket", json={})
    assert resp.status_code == 400
    assert resp.json()["message"] == "UBSocket日志解析暂不支持配置"

    resp = client.post("/diagnosis_config/kb-1/reset?log_type=UBSocket")
    assert resp.status_code == 400
    assert resp.json()["message"] == "UBSocket日志解析暂不支持配置"

    # 非法枚举与路径参数 -> 422
    assert client.get("/diagnosis_config/kb-1?log_type=foo").status_code == 422
    assert (
        client.put("/diagnosis_config/kb-1?log_type=foo", json=put_body).status_code
        == 422
    )
    assert (
        client.post("/diagnosis_config/kb-1/reset?log_type=foo").status_code == 422
    )
    assert (
        client.get("/diagnosis_config/bad!id?log_type=KVCache").status_code == 422
    )


# ---------------------------------------------------------------------------
# routers/log_file.py
# ---------------------------------------------------------------------------


def test_log_file_router_endpoints(monkeypatch):
    client = make_client(monkeypatch)
    upload = AsyncMock(return_value=UploadLogFilesMsg(log_file_ids=["lf-1"]))
    run_brpc = AsyncMock(return_value=RunBrpcDiagnosisMsg(task_id="t-1"))
    delete_file = AsyncMock(return_value=DeleteLogFilesMsg(log_file_ids=["lf-1"]))
    update_file = AsyncMock(return_value=UpdateLogFileMsg(log_file_id="lf-1"))
    run_or_stop = AsyncMock(return_value=RunOrStopLogParseMsg(task_id="t-1"))
    list_files = AsyncMock(return_value=ListLogFilesMsg(total=0))
    get_file = AsyncMock(return_value=GetLogFileMsg())
    monkeypatch.setattr(LogFileService, "upload_log_files", upload)
    monkeypatch.setattr(
        LogFileService, "run_brpc_diagnosis_by_log_file_id", run_brpc
    )
    monkeypatch.setattr(LogFileService, "delete_log_file_by_log_file_id", delete_file)
    monkeypatch.setattr(LogFileService, "update_log_file", update_file)
    monkeypatch.setattr(
        LogFileService, "run_or_stop_log_parse_by_log_file_id", run_or_stop
    )
    monkeypatch.setattr(LogFileService, "list_log_files", list_files)
    monkeypatch.setattr(LogFileService, "get_log_file_by_log_file_id", get_file)

    # JSON 上传分支（remote 类型，无需上传文件）
    resp = client.post(
        "/log_file/kb-1",
        json={
            "upload_log_file_configs": [
                {
                    "source_type": "remote",
                    "source": "http://example.com/a.log",
                    "log_type": "KVCache",
                }
            ]
        },
    )
    assert resp.status_code == 200
    assert resp.json() == {
        "code": 200,
        "message": "日志解析任务已受理",
        "result": {"log_file_ids": ["lf-1"]},
    }
    assert upload.await_args.args[0] == "kb-1"
    assert upload.await_args.args[1].upload_log_file_configs[0].source == (
        "http://example.com/a.log"
    )

    # JSON body 非法 -> RequestValidationError(422)
    resp = client.post(
        "/log_file/kb-1",
        content=b"{bad json",
        headers={"content-type": "application/json"},
    )
    assert resp.status_code == 422

    # JSON schema 校验失败：空配置列表 / local 非绝对路径 -> 422
    assert (
        client.post("/log_file/kb-1", json={"upload_log_file_configs": []}).status_code
        == 422
    )
    assert (
        client.post(
            "/log_file/kb-1",
            json={
                "upload_log_file_configs": [
                    {"source_type": "local", "source": "a.log", "log_type": "KVCache"}
                ]
            },
        ).status_code
        == 422
    )

    resp = client.post(
        "/log_file/lf-1/brpc-diagnosis",
        json={"start_time": "2026-01-01 00:00:00"},
    )
    assert resp.status_code == 200
    assert resp.json()["result"] == {"task_id": "t-1"}
    assert run_brpc.await_args.args[0] == "lf-1"
    assert run_brpc.await_args.args[1].start_time == "2026-01-01 00:00:00"

    resp = client.delete("/log_file/lf-1")
    assert resp.status_code == 200
    assert resp.json()["result"] == {"log_file_ids": ["lf-1"]}
    delete_file.assert_awaited_once_with("lf-1")

    resp = client.put(
        "/log_file/lf-1",
        json={
            "source_type": "local",
            "source": "/tmp/a.log",
            "log_type": "KVCache",
        },
    )
    assert resp.status_code == 200
    assert resp.json()["result"] == {"log_file_id": "lf-1"}
    assert update_file.await_args.args[0] == "lf-1"
    assert update_file.await_args.args[1].source == "/tmp/a.log"

    resp = client.put("/log_file/run/lf-1")
    assert resp.status_code == 200
    assert resp.json()["result"] == {"task_id": "t-1"}
    run_or_stop.assert_awaited_once_with("lf-1", True)

    resp = client.put("/log_file/run/lf-1?run=false")
    assert resp.status_code == 200
    assert run_or_stop.await_args.args == ("lf-1", False)

    # list 不经过 ResourceIdService
    resp = client.post("/log_file/list/kb-1", json={"name": "a"})
    assert resp.status_code == 200
    assert resp.json()["result"] == {"total": 0, "log_files": []}
    assert list_files.await_args.args[0] == "kb-1"
    assert list_files.await_args.args[1].name == "a"

    resp = client.get("/log_file/lf-1")
    assert resp.status_code == 200
    assert resp.json()["result"] == {"log_file": None}
    get_file.assert_awaited_once_with("lf-1")

    # 校验失败：路径正则 / start_time 格式
    assert client.get("/log_file/bad!id").status_code == 422
    assert client.delete("/log_file/bad!id").status_code == 422
    assert (
        client.post(
            "/log_file/lf-1/brpc-diagnosis", json={"start_time": "2026-01-01"}
        ).status_code
        == 422
    )

    monkeypatch.setattr(
        LogFileService,
        "get_log_file_by_log_file_id",
        AsyncMock(side_effect=NotFoundBizException(resource="日志文件")),
    )
    resp = client.get("/log_file/missing")
    assert resp.status_code == 404
    assert resp.json()["message"] == "日志文件不存在"


class _FakeForm(dict):
    def getlist(self, key):
        return self.get(key, [])


class _FakeMultipartRequest:
    """python-multipart 未安装于测试环境，用轻量 Request 桩驱动 multipart 分支。"""

    def __init__(self, form):
        self.headers = {"content-type": "multipart/form-data; boundary=x"}
        self._form = _FakeForm(form)

    async def form(self):
        return self._form


async def test_log_file_upload_multipart_branches(monkeypatch):
    upload = AsyncMock(return_value=UploadLogFilesMsg(log_file_ids=["lf-1"]))
    monkeypatch.setattr(LogFileService, "upload_log_files", upload)
    monkeypatch.setattr(ResourceIdService, "require", AsyncMock())

    upload_cfg = [{"source_type": "upload", "log_type": "KVCache"}]
    real_file = lambda: UploadFile(file=io.BytesIO(b"data"), filename="a.log")

    # upload_log_file_configs 缺失（非字符串） -> 400
    with pytest.raises(HTTPException) as exc_info:
        await upload_log_files_endpoint(
            "kb-1", _FakeMultipartRequest(form={"file": [real_file()]})
        )
    assert exc_info.value.status_code == 400
    assert exc_info.value.detail == "缺少上传文件配置"

    # upload_log_file_configs 非法 JSON -> 400
    with pytest.raises(HTTPException) as exc_info:
        await upload_log_files_endpoint(
            "kb-1",
            _FakeMultipartRequest(
                form={"upload_log_file_configs": "not-json", "file": [real_file()]}
            ),
        )
    assert exc_info.value.detail == "上传文件配置不是有效JSON"

    # upload 配置缺少上传文件 -> 400
    with pytest.raises(HTTPException) as exc_info:
        await upload_log_files_endpoint(
            "kb-1",
            _FakeMultipartRequest(form={"upload_log_file_configs": json.dumps(upload_cfg)}),
        )
    assert exc_info.value.detail == "缺少上传文件"

    # 非文件对象充当上传文件 -> 400
    with pytest.raises(HTTPException) as exc_info:
        await upload_log_files_endpoint(
            "kb-1",
            _FakeMultipartRequest(
                form={
                    "upload_log_file_configs": json.dumps(upload_cfg),
                    "file": ["plain-string"],
                }
            ),
        )
    assert exc_info.value.detail == "上传文件格式不正确"

    # parse_config 非法 JSON -> 400
    with pytest.raises(HTTPException) as exc_info:
        await upload_log_files_endpoint(
            "kb-1",
            _FakeMultipartRequest(
                form={
                    "upload_log_file_configs": json.dumps(upload_cfg),
                    "file": [real_file()],
                    "parse_config": "not-json",
                }
            ),
        )
    assert exc_info.value.detail == "解析配置不是有效JSON"

    # 正常 multipart 上传：注入文件对象并回填文件名
    resp_msg = await upload_log_files_endpoint(
        "kb-1",
        _FakeMultipartRequest(
            form={
                "upload_log_file_configs": json.dumps(upload_cfg),
                "file": [real_file()],
            }
        ),
    )
    assert resp_msg.message == "日志解析任务已受理"
    req = upload.await_args.args[1]
    assert req.upload_log_file_configs[0].name == "a.log"
    assert isinstance(req.upload_log_file_configs[0].source, UploadFile)
    assert req.parse_config is None

    # 配置自带 name 时保留；parse_config 合法时透传
    await upload_log_files_endpoint(
        "kb-1",
        _FakeMultipartRequest(
            form={
                "upload_log_file_configs": json.dumps(
                    [
                        {
                            "source_type": "upload",
                            "log_type": "KVCache",
                            "name": "kept.log",
                        }
                    ]
                ),
                "file": [real_file()],
                "parse_config": json.dumps({"min_elapsed_ms": 5}),
            }
        ),
    )
    req = upload.await_args.args[1]
    assert req.upload_log_file_configs[0].name == "kept.log"
    assert req.parse_config.min_elapsed_ms == 5

    # 配置不满足 schema -> RequestValidationError
    with pytest.raises(RequestValidationError):
        await upload_log_files_endpoint(
            "kb-1",
            _FakeMultipartRequest(
                form={
                    "upload_log_file_configs": json.dumps(
                        [{"source_type": "remote"}]
                    ),
                    "file": [real_file()],
                }
            ),
        )


# ---------------------------------------------------------------------------
# routers/brpc_profiling.py
# ---------------------------------------------------------------------------


def _profiling_record(**overrides):
    base = dict(
        interface_name="Send",
        timestamp=datetime(2026, 8, 6, 15, 7, 41),
        log_id="lf-000001-x",
        source_file="brpc.log",
        success_count=10,
        failure_count=2,
        total_ns=100,
        avg_ns=50,
        max_ns=90,
        min_ns=10,
        p50_ns=40,
        p90_ns=80,
        p95_ns=85,
        p99_ns=88,
        p999_ns=89,
    )
    base.update(overrides)
    return SimpleNamespace(**base)


def test_brpc_profiling_router_endpoints(monkeypatch):
    client = make_client(monkeypatch)
    records = [
        _profiling_record(),
        _profiling_record(interface_name="Recv", timestamp=None),
    ]
    file_options = AsyncMock(
        return_value=[{"log_id": "lf-1", "source_file": "brpc.log"}]
    )
    by_kb = AsyncMock(return_value=records)
    file_names = AsyncMock(return_value=["brpc.log"])
    by_log = AsyncMock(return_value=records)
    monkeypatch.setattr(
        BrpcProfilingResultPGManager, "get_file_options_by_kb_id", file_options
    )
    monkeypatch.setattr(BrpcProfilingResultPGManager, "get_all_by_kb_id", by_kb)
    monkeypatch.setattr(
        BrpcProfilingResultPGManager, "get_file_names_by_log_id", file_names
    )
    monkeypatch.setattr(BrpcProfilingResultPGManager, "get_all_by_log_id", by_log)

    # knowledge 端点：未显式指定时自动选择 files[0]
    resp = client.get("/brpc_profiling/knowledge/kb-1")
    assert resp.status_code == 200
    result = resp.json()["result"]
    assert result["interface_names"] == ["Recv", "Send"]
    assert result["file_names"] == []
    assert result["files"] == [{"log_id": "lf-1", "source_file": "brpc.log"}]
    assert len(result["rows"]) == 2
    assert result["rows"][0]["timestamp"] == "2026-08-06T15:07:41"
    assert result["rows"][0]["interface_name"] == "Send"
    assert result["rows"][1]["timestamp"] is None
    assert by_kb.await_args.args == ("kb-1",)
    assert by_kb.await_args.kwargs == {"source_file": "brpc.log", "log_id": "lf-1"}

    # 显式传 log_id 时不自动选择文件
    resp = client.get("/brpc_profiling/knowledge/kb-1?log_id=lf-2")
    assert resp.status_code == 200
    assert by_kb.await_args.kwargs == {"source_file": None, "log_id": "lf-2"}

    # log 端点
    resp = client.get("/brpc_profiling/lf-1")
    assert resp.status_code == 200
    assert resp.json()["result"]["file_names"] == ["brpc.log"]
    assert by_log.await_args.args == ("lf-1",)
    assert by_log.await_args.kwargs == {"source_file": None}

    resp = client.get("/brpc_profiling/lf-1?source_file=brpc.log")
    assert resp.status_code == 200
    assert by_log.await_args.kwargs == {"source_file": "brpc.log"}

    # 校验失败：路径正则 / 空 log_id 查询参数
    assert client.get("/brpc_profiling/bad!id").status_code == 422
    assert client.get("/brpc_profiling/knowledge/kb-1?log_id=").status_code == 422

    # 无记录 -> 404
    monkeypatch.setattr(
        BrpcProfilingResultPGManager, "get_all_by_log_id", AsyncMock(return_value=[])
    )
    resp = client.get("/brpc_profiling/lf-1")
    assert resp.status_code == 404
    assert resp.json()["message"] == "UBSocket profiling 数据不存在"


def test_build_profiling_response_direct():
    resp = _build_profiling_response(
        [_profiling_record()], file_names=None, files=None
    )
    assert resp.result.file_names == []
    assert resp.result.files == []
    assert resp.result.interface_names == ["Send"]

    with pytest.raises(NotFoundBizException):
        _build_profiling_response([])


# ---------------------------------------------------------------------------
# routers/brpc_diagnosis.py
# ---------------------------------------------------------------------------

_BATCH_ID = "0198aaaa-1111-7111-8111-111111111111"
_EVENT_ID = "a" * 64
_TS = 1_786_000_061_000_000
_TS_END = 1_786_000_062_000_000


def test_brpc_diagnosis_knowledge_scope_and_timeline(monkeypatch):
    client = make_client(monkeypatch)
    get_scope = AsyncMock(
        return_value=BrpcKnowledgeScopeMsg(
            kb_id="kb-1",
            batch_count=1,
            hit_count=2,
            start_time=_TS,
            end_time=_TS_END,
        )
    )
    get_timeline = AsyncMock(
        return_value=GetBrpcInterfaceTimelineMsg(
            batch_id=_BATCH_ID,
            start_time=_TS,
            end_time=_TS_END,
            window_size="1m",
        )
    )
    monkeypatch.setattr(BrpcDiagnosisService, "get_knowledge_scope", get_scope)
    monkeypatch.setattr(
        BrpcDiagnosisService, "get_knowledge_interface_timeline", get_timeline
    )

    resp = client.get("/brpc-diagnosis/knowledge/kb-1/scope")
    assert resp.status_code == 200
    assert resp.json()["result"] == {
        "kb_id": "kb-1",
        "batch_count": 1,
        "hit_count": 2,
        "start_time": "2026-08-06 15:07:41",
        "end_time": "2026-08-06 15:07:42",
    }
    get_scope.assert_awaited_once_with("kb-1")

    resp = client.get(
        "/brpc-diagnosis/knowledge/kb-1/interface-timeline",
        params={
            "start_time": "2026-08-06 15:07:41",
            "end_time": "2026-08-06 15:07:42",
            "window_size": "1m",
            "component": "umq",
            "interface_id": "umq.interface.send",
            "pod_ip": "10.0.0.1",
            "pod_name": "pod-a",
        },
    )
    assert resp.status_code == 200
    assert resp.json()["result"]["batch_id"] == _BATCH_ID
    assert get_timeline.await_args.kwargs == {
        "kb_id": "kb-1",
        "start_timestamp": _TS,
        "end_timestamp": _TS_END,
        "window_size": "1m",
        "component": "umq",
        "interface_id": "umq.interface.send",
        "pod_ip": "10.0.0.1",
        "pod_name": "pod-a",
    }

    # component 缺省
    client.get(
        "/brpc-diagnosis/knowledge/kb-1/interface-timeline",
        params={
            "start_time": "2026-08-06 15:07:41",
            "end_time": "2026-08-06 15:07:42",
            "window_size": "10s",
        },
    )
    assert get_timeline.await_args.kwargs["component"] is None
    assert get_timeline.await_args.kwargs["window_size"] == "10s"

    # 校验失败：坏时间格式 / 坏 window_size / 缺必填参数 / 非法路径
    assert (
        client.get(
            "/brpc-diagnosis/knowledge/kb-1/interface-timeline",
            params={
                "start_time": "2026-08-06T15:07:41",
                "end_time": "2026-08-06 15:07:42",
                "window_size": "1m",
            },
        ).status_code
        == 422
    )
    assert (
        client.get(
            "/brpc-diagnosis/knowledge/kb-1/interface-timeline",
            params={
                "start_time": "2026-08-06 15:07:41",
                "end_time": "2026-08-06 15:07:42",
                "window_size": "2m",
            },
        ).status_code
        == 422
    )
    assert (
        client.get(
            "/brpc-diagnosis/knowledge/kb-1/interface-timeline",
            params={"start_time": "2026-08-06 15:07:41", "window_size": "1m"},
        ).status_code
        == 422
    )
    assert client.get("/brpc-diagnosis/knowledge/bad!id/scope").status_code == 422


def test_brpc_diagnosis_knowledge_event_lists(monkeypatch):
    client = make_client(monkeypatch)
    list_pod = AsyncMock(return_value=ListBrpcPodEventsMsg(batch_id=_BATCH_ID, total=1))
    list_thread = AsyncMock(
        return_value=ListBrpcThreadEventsMsg(batch_id=_BATCH_ID, total=2)
    )
    list_abnormal = AsyncMock(
        return_value=ListBrpcAbnormalThreadsMsg(batch_id=_BATCH_ID, total=3)
    )
    monkeypatch.setattr(
        BrpcDiagnosisService, "list_knowledge_pod_events", list_pod
    )
    monkeypatch.setattr(
        BrpcDiagnosisService, "list_knowledge_thread_events", list_thread
    )
    monkeypatch.setattr(
        BrpcDiagnosisService, "list_knowledge_abnormal_threads", list_abnormal
    )
    time_params = {
        "start_time": "2026-08-06 15:07:41",
        "end_time": "2026-08-06 15:07:42",
        "window_size": "1m",
    }

    resp = client.get(
        "/brpc-diagnosis/knowledge/kb-1/pod-events",
        params={
            **time_params,
            "sort_field": ["total_interface_hit_count", "ubsocket_001"],
            "sort_direction": ["desc", "asc"],
            "page_num": 2,
            "page_cnt": 5,
            "pod_ip": "10.0.0.1",
            "pod_name": "pod-a",
        },
    )
    assert resp.status_code == 200
    assert resp.json()["result"]["total"] == 1
    kwargs = list_pod.await_args.kwargs
    assert kwargs["kb_id"] == "kb-1"
    assert kwargs["start_timestamp"] == _TS
    assert kwargs["end_timestamp"] == _TS_END
    assert kwargs["window_size"] == "1m"
    assert kwargs["page_num"] == 2
    assert kwargs["page_cnt"] == 5
    assert kwargs["pod_ip"] == "10.0.0.1"
    assert kwargs["pod_name"] == "pod-a"
    assert kwargs["metric_sort_fields"] == [
        BrpcMetricSortField(field="total_interface_hit_count", order="desc"),
        BrpcMetricSortField(field="ubsocket_001", order="asc"),
    ]

    resp = client.get(
        "/brpc-diagnosis/knowledge/kb-1/thread-events",
        params={
            **time_params,
            "sort_order": "desc",
            "window_size": "1s",
        },
    )
    assert resp.status_code == 200
    assert resp.json()["result"]["total"] == 2
    kwargs = list_thread.await_args.kwargs
    assert kwargs["sort_order"] == "desc"
    assert kwargs["window_size"] == "1s"
    assert kwargs["metric_sort_fields"] == []
    assert kwargs["page_num"] == 1
    assert kwargs["page_cnt"] == 10
    assert kwargs["pod_ip"] is None
    assert kwargs["pod_name"] is None

    resp = client.get(
        "/brpc-diagnosis/knowledge/kb-1/abnormal-threads",
        params={
            "start_time": "2026-08-06 15:07:41",
            "end_time": "2026-08-06 15:07:42",
            "search": "umq",
            "page_cnt": 20,
        },
    )
    assert resp.status_code == 200
    assert resp.json()["result"]["total"] == 3
    kwargs = list_abnormal.await_args.kwargs
    assert kwargs["search"] == "umq"
    assert kwargs["page_cnt"] == 20
    assert kwargs["metric_sort_fields"] == []

    # 校验失败：page_num=0 / 空 search / 排序参数不匹配
    assert (
        client.get(
            "/brpc-diagnosis/knowledge/kb-1/pod-events",
            params={**time_params, "page_num": 0},
        ).status_code
        == 422
    )
    assert (
        client.get(
            "/brpc-diagnosis/knowledge/kb-1/abnormal-threads",
            params={
                "start_time": "2026-08-06 15:07:41",
                "end_time": "2026-08-06 15:07:42",
                "search": "",
            },
        ).status_code
        == 422
    )
    resp = client.get(
        "/brpc-diagnosis/knowledge/kb-1/pod-events",
        params={**time_params, "sort_field": ["a", "b"], "sort_direction": ["asc"]},
    )
    assert resp.status_code == 422
    assert resp.json() == {"detail": "sort_field 和 sort_direction 必须一一对应"}


def test_brpc_diagnosis_batch_and_hits(monkeypatch):
    client = make_client(monkeypatch)
    get_by_task = AsyncMock(
        return_value=GetBrpcTaskBatchMsg(task_id="t-1", batch_id=_BATCH_ID)
    )
    get_batch = AsyncMock(
        return_value=GetBrpcBatchMsg(
            batch=BrpcDiagBatchMetadata(
                batch_id=_BATCH_ID,
                task_id="t-1",
                schema_id="b" * 64,
                created_at_timestamp=_TS_END,
                start_timestamp=_TS,
                end_timestamp=_TS_END,
                hit_count=2,
            )
        )
    )
    list_hits = AsyncMock(return_value=ListBrpcDiagHitsMsg(batch_id=_BATCH_ID, total=0))
    thread_logs = AsyncMock(return_value=ListBrpcDiagHitsMsg(batch_id=_BATCH_ID, total=1))
    monkeypatch.setattr(BrpcDiagnosisService, "get_batch_by_task_id", get_by_task)
    monkeypatch.setattr(BrpcDiagnosisService, "get_batch", get_batch)
    monkeypatch.setattr(BrpcDiagnosisService, "list_hits", list_hits)
    monkeypatch.setattr(BrpcDiagnosisService, "list_thread_logs", thread_logs)

    resp = client.get("/brpc-diagnosis/task/t-1/batch")
    assert resp.status_code == 200
    assert resp.json()["result"] == {"task_id": "t-1", "batch_id": _BATCH_ID}
    get_by_task.assert_awaited_once_with("t-1")

    resp = client.get(f"/brpc-diagnosis/batch/{_BATCH_ID}")
    assert resp.status_code == 200
    batch_json = resp.json()["result"]["batch"]
    assert batch_json["batch_id"] == _BATCH_ID
    assert batch_json["created_at_time"] == "2026-08-06 15:07:42"
    assert "created_at_us" not in batch_json
    assert batch_json["hit_count"] == 2
    get_batch.assert_awaited_once_with(_BATCH_ID)

    resp = client.get(
        f"/brpc-diagnosis/batch/{_BATCH_ID}/hits",
        params={
            "pod_ip": "10.0.0.1",
            "thread_id": 9,
            "page_num": 2,
            "page_cnt": 50,
            "start_time": "2026-08-06 15:07:41",
            "end_time": "2026-08-06 15:07:42",
            "pod_name": "pod-a",
        },
    )
    assert resp.status_code == 200
    assert resp.json()["result"]["total"] == 0
    assert list_hits.await_args.kwargs == {
        "batch_id": _BATCH_ID,
        "pod_ip": "10.0.0.1",
        "thread_id": 9,
        "page_num": 2,
        "page_cnt": 50,
        "start_timestamp": _TS,
        "end_timestamp": _TS_END,
        "pod_name": "pod-a",
    }

    # thread-logs 只带时间范围（分页在服务内固定）
    resp = client.get(
        f"/brpc-diagnosis/batch/{_BATCH_ID}/thread-logs",
        params={
            "pod_ip": "10.0.0.1",
            "thread_id": 9,
            "start_time": "2026-08-06 15:07:41",
        },
    )
    assert resp.status_code == 200
    assert resp.json()["result"]["total"] == 1
    assert thread_logs.await_args.kwargs == {
        "batch_id": _BATCH_ID,
        "pod_ip": "10.0.0.1",
        "thread_id": 9,
        "start_timestamp": _TS,
        "end_timestamp": None,
    }

    # 校验失败：缺 pod_ip / thread_id / 非整数 thread_id / 空 pod_ip
    assert (
        client.get(f"/brpc-diagnosis/batch/{_BATCH_ID}/hits", params={"thread_id": 9}).status_code
        == 422
    )
    assert (
        client.get(
            f"/brpc-diagnosis/batch/{_BATCH_ID}/hits",
            params={"pod_ip": "10.0.0.1", "thread_id": "x"},
        ).status_code
        == 422
    )
    assert (
        client.get(
            f"/brpc-diagnosis/batch/{_BATCH_ID}/hits",
            params={"pod_ip": "", "thread_id": 9},
        ).status_code
        == 422
    )
    assert (
        client.get(f"/brpc-diagnosis/batch/{_BATCH_ID}/thread-logs", params={}).status_code
        == 422
    )


def test_brpc_diagnosis_batch_events_and_details(monkeypatch):
    client = make_client(monkeypatch)
    get_timeline = AsyncMock(
        return_value=GetBrpcInterfaceTimelineMsg(
            batch_id=_BATCH_ID,
            start_time=_TS,
            end_time=_TS_END,
            window_size="10s",
        )
    )
    list_pod = AsyncMock(return_value=ListBrpcPodEventsMsg(batch_id=_BATCH_ID, total=1))
    get_pod_detail = AsyncMock(
        return_value=GetBrpcPodEventDetailMsg(
            event=BrpcPodAggregatedEvent(
                event_id=_EVENT_ID,
                batch_id=_BATCH_ID,
                window_start_time=_TS,
                window_end_time=_TS_END,
                pod_ip="10.0.0.1",
                pod_name=None,
            ),
            failure_graph=BrpcFailureGraph(),
            hit_total=0,
        )
    )
    list_thread = AsyncMock(
        return_value=ListBrpcThreadEventsMsg(batch_id=_BATCH_ID, total=2)
    )
    get_thread_detail = AsyncMock(
        return_value=GetBrpcThreadEventDetailMsg(
            event=BrpcThreadAggregatedEvent(
                event_id=_EVENT_ID,
                batch_id=_BATCH_ID,
                window_start_time=_TS,
                window_end_time=_TS_END,
                pod_ip="10.0.0.1",
                pod_name="pod-a",
                thread_id=9,
            ),
            failure_graph=BrpcFailureGraph(),
            hit_total=0,
        )
    )
    list_abnormal = AsyncMock(
        return_value=ListBrpcAbnormalThreadsMsg(batch_id=_BATCH_ID, total=3)
    )
    get_abnormal_detail = AsyncMock(
        return_value=GetBrpcAbnormalThreadDetailMsg(
            thread=BrpcAbnormalThread(
                thread_key=_EVENT_ID,
                batch_id=_BATCH_ID,
                pod_ip="10.0.0.1",
                pod_name="pod-a",
                thread_id=9,
                first_hit_time=_TS,
                last_hit_time=_TS_END,
                total_interface_hit_count=3,
            ),
            start_time=_TS,
            end_time=_TS_END,
            window_size="1m",
            failure_graph=BrpcFailureGraph(),
            hit_total=0,
        )
    )
    monkeypatch.setattr(BrpcDiagnosisService, "get_interface_timeline", get_timeline)
    monkeypatch.setattr(BrpcDiagnosisService, "list_pod_events", list_pod)
    monkeypatch.setattr(BrpcDiagnosisService, "get_pod_event_detail", get_pod_detail)
    monkeypatch.setattr(BrpcDiagnosisService, "list_thread_events", list_thread)
    monkeypatch.setattr(
        BrpcDiagnosisService, "get_thread_event_detail", get_thread_detail
    )
    monkeypatch.setattr(BrpcDiagnosisService, "list_abnormal_threads", list_abnormal)
    monkeypatch.setattr(
        BrpcDiagnosisService, "get_abnormal_thread_detail", get_abnormal_detail
    )

    time_params = {
        "start_time": "2026-08-06 15:07:41",
        "end_time": "2026-08-06 15:07:42",
        "window_size": "1m",
    }

    resp = client.get(
        f"/brpc-diagnosis/batch/{_BATCH_ID}/interface-timeline",
        params={**time_params, "window_size": "10s", "component": "umq"},
    )
    assert resp.status_code == 200
    assert resp.json()["result"]["window_size"] == "10s"
    assert get_timeline.await_args.kwargs["batch_id"] == _BATCH_ID
    assert get_timeline.await_args.kwargs["component"] == "umq"
    assert get_timeline.await_args.kwargs["start_timestamp"] == _TS

    resp = client.get(
        f"/brpc-diagnosis/batch/{_BATCH_ID}/pod-events",
        params={
            **time_params,
            "sort_order": "desc",
            "sort_field": ["ubsocket_001"],
            "sort_direction": ["asc"],
            "page_cnt": 7,
            "pod_ip": "10.0.0.1",
        },
    )
    assert resp.status_code == 200
    assert resp.json()["result"]["total"] == 1
    kwargs = list_pod.await_args.kwargs
    assert kwargs["sort_order"] == "desc"
    assert kwargs["page_cnt"] == 7
    assert kwargs["metric_sort_fields"] == [
        BrpcMetricSortField(field="ubsocket_001", order="asc")
    ]

    resp = client.get(
        f"/brpc-diagnosis/batch/{_BATCH_ID}/pod-events/{_EVENT_ID}",
        params={
            "window_start_time": "2026-08-06 15:07:41",
            "window_end_time": "2026-08-06 15:07:42",
            "pod_ip": "10.0.0.1",
            "page_num": 2,
            "page_cnt": 8,
        },
    )
    assert resp.status_code == 200
    result = resp.json()["result"]
    assert result["event"]["event_id"] == _EVENT_ID
    assert result["event"]["window_start_time"] == "2026-08-06 15:07:41"
    assert result["event"]["pod_name"] is None
    assert result["failure_graph"] == {"nodes": [], "edges": []}
    assert result["hit_total"] == 0
    assert get_pod_detail.await_args.kwargs == {
        "event_id": _EVENT_ID,
        "batch_id": _BATCH_ID,
        "window_start_timestamp": _TS,
        "window_end_timestamp": _TS_END,
        "pod_ip": "10.0.0.1",
        "page_num": 2,
        "page_cnt": 8,
        "pod_name": None,
    }

    resp = client.get(
        f"/brpc-diagnosis/batch/{_BATCH_ID}/thread-events",
        params=time_params,
    )
    assert resp.status_code == 200
    assert resp.json()["result"]["total"] == 2
    assert list_thread.await_args.kwargs["window_size"] == "1m"

    resp = client.get(
        f"/brpc-diagnosis/batch/{_BATCH_ID}/thread-events/{_EVENT_ID}",
        params={
            "window_start_time": "2026-08-06 15:07:41",
            "window_end_time": "2026-08-06 15:07:42",
            "pod_ip": "10.0.0.1",
            "thread_id": 9,
            "pod_name": "pod-a",
        },
    )
    assert resp.status_code == 200
    assert resp.json()["result"]["event"]["thread_id"] == 9
    assert get_thread_detail.await_args.kwargs["thread_id"] == 9
    assert get_thread_detail.await_args.kwargs["pod_name"] == "pod-a"

    resp = client.get(
        f"/brpc-diagnosis/batch/{_BATCH_ID}/abnormal-threads",
        params={
            **time_params,
            "search": "pod",
            "sort_field": ["total_interface_hit_count"],
            "sort_direction": ["desc"],
        },
    )
    assert resp.status_code == 200
    assert resp.json()["result"]["total"] == 3
    kwargs = list_abnormal.await_args.kwargs
    assert kwargs["search"] == "pod"
    assert kwargs["page_cnt"] == 100

    resp = client.get(
        f"/brpc-diagnosis/batch/{_BATCH_ID}/abnormal-threads/{_EVENT_ID}",
        params={
            "pod_ip": "10.0.0.1",
            "thread_id": 9,
            **time_params,
            "window_size": "1m",
        },
    )
    assert resp.status_code == 200
    result = resp.json()["result"]
    assert result["thread"]["thread_key"] == _EVENT_ID
    assert result["thread"]["first_hit_time"] == "2026-08-06 15:07:41"
    assert result["thread"]["total_interface_hit_count"] == 3
    assert result["window_size"] == "1m"
    assert get_abnormal_detail.await_args.kwargs["thread_key"] == _EVENT_ID
    assert get_abnormal_detail.await_args.kwargs["window_size"] == "1m"

    # 校验失败：非 64 位十六进制 event_id/thread_key / 聚合窗口大小非法
    assert (
        client.get(
            f"/brpc-diagnosis/batch/{_BATCH_ID}/pod-events/zz",
            params={
                "window_start_time": "2026-08-06 15:07:41",
                "window_end_time": "2026-08-06 15:07:42",
                "pod_ip": "10.0.0.1",
            },
        ).status_code
        == 422
    )
    assert (
        client.get(
            f"/brpc-diagnosis/batch/{_BATCH_ID}/abnormal-threads/bad-key",
            params={
                "pod_ip": "10.0.0.1",
                "thread_id": 9,
                **time_params,
            },
        ).status_code
        == 422
    )
    assert (
        client.get(
            f"/brpc-diagnosis/batch/{_BATCH_ID}/pod-events",
            params={**time_params, "window_size": "10s"},
        ).status_code
        == 422
    )


def test_build_metric_sort_fields_matrix():
    # 正常配对构造
    fields = _build_metric_sort_fields(["a", "b"], ["asc", "desc"])
    assert [f.field for f in fields] == ["a", "b"]
    assert [f.order for f in fields] == ["asc", "desc"]

    # 空入参 -> 空列表
    assert _build_metric_sort_fields(None, None) == []
    assert _build_metric_sort_fields([], []) == []

    # 数量不匹配
    with pytest.raises(HTTPException) as exc_info:
        _build_metric_sort_fields(["a"], [])
    assert exc_info.value.detail == "sort_field 和 sort_direction 必须一一对应"

    # 超过 50 个
    with pytest.raises(HTTPException) as exc_info:
        _build_metric_sort_fields([f"f{i}" for i in range(51)], ["asc"] * 51)
    assert exc_info.value.detail == "排序字段不能超过 50 个"

    # 重复字段
    with pytest.raises(HTTPException) as exc_info:
        _build_metric_sort_fields(["a", "a"], ["asc", "desc"])
    assert exc_info.value.detail == "排序字段不能重复"

    # 空字段 / 超长字段
    with pytest.raises(HTTPException) as exc_info:
        _build_metric_sort_fields([""], ["asc"])
    assert exc_info.value.detail == "排序字段长度必须为 1 到 256 个字符"

    with pytest.raises(HTTPException) as exc_info:
        _build_metric_sort_fields(["x" * 257], ["asc"])
    assert exc_info.value.detail == "排序字段长度必须为 1 到 256 个字符"
