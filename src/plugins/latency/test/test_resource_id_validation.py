import asyncio
from unittest.mock import AsyncMock

import httpx
import pytest
from fastapi import FastAPI
from pydantic import TypeAdapter, ValidationError

from latency.database.managers.resource_id import ResourceIdPGManager
from latency.exceptions import NotFoundBizException
from latency.routers import log_parse_result as log_parse_result_router
from latency.schemas.request import ListLogParseResultRequest
from latency.schemas.response import StopTaskMsg
from latency.services.log_parse_result import LogParseResultService
from latency.services.resource_id import ResourceIdService
from latency.common.id_validation import (
    BrpcEventIdPath,
    FailureModeIdPath,
    ResourceIdPath,
    ResourceIdQuery,
    StatusCodePath,
)

TASK_ID = "0198aaaa-1111-7111-8111-111111111111"
BATCH_ID = "0198bbbb-2222-7222-8222-222222222222"
VALID_KB_ID = "00000000-0000-0000-0000-000000000000"


def run(coroutine):
    return asyncio.run(coroutine)


def test_path_and_query_id_types_reject_illegal_characters_and_oversized_values():
    invalid_values = [
        (ResourceIdPath, "!@#"),
        (ResourceIdPath, ".."),
        (ResourceIdPath, "a" * 10_000),
        (ResourceIdQuery, "!@#"),
        (ResourceIdQuery, ".."),
        (ResourceIdQuery, "a" * 10_000),
        (FailureModeIdPath, "!@#"),
        (FailureModeIdPath, ".."),
        (FailureModeIdPath, "umq.failure"),
        (FailureModeIdPath, "umq:failure"),
        (FailureModeIdPath, "umq-failure"),
        (FailureModeIdPath, "a" * 10_000),
        (StatusCodePath, "!@#"),
        (StatusCodePath, ".."),
        (StatusCodePath, "a" * 10_000),
        (BrpcEventIdPath, "not-a-sha256"),
        (BrpcEventIdPath, "a" * 10_000),
    ]

    for annotation, value in invalid_values:
        with pytest.raises(ValidationError):
            TypeAdapter(annotation).validate_python(value)

    assert TypeAdapter(ResourceIdPath).validate_python("missing-id") == "missing-id"
    assert TypeAdapter(ResourceIdQuery).validate_python("missing-id") == "missing-id"
    failure_id = "kvcache_runtime_1000"
    assert TypeAdapter(FailureModeIdPath).validate_python(failure_id) == failure_id
    assert TypeAdapter(StatusCodePath).validate_python("K_ACCESS_7") == "K_ACCESS_7"
    assert TypeAdapter(BrpcEventIdPath).validate_python("a" * 64) == "a" * 64


def test_require_rejects_missing_id_with_actionable_detail(monkeypatch):
    find_missing = AsyncMock(return_value=["missing-kb"])
    monkeypatch.setattr(ResourceIdPGManager, "find_missing", find_missing)

    with pytest.raises(NotFoundBizException) as exc_info:
        run(ResourceIdService.require("kb", "missing-kb"))

    assert exc_info.value.message == "知识库不存在"
    assert exc_info.value.detail == "不存在的 ID: missing-kb"
    find_missing.assert_awaited_once_with("kb", ["missing-kb"])


def test_require_does_not_treat_empty_id_as_an_absent_optional_value(monkeypatch):
    find_missing = AsyncMock(return_value=[""])
    monkeypatch.setattr(ResourceIdPGManager, "find_missing", find_missing)

    with pytest.raises(NotFoundBizException):
        run(ResourceIdService.require("log", ""))

    find_missing.assert_awaited_once_with("log", [""])


def test_validate_request_checks_all_conventional_id_fields(monkeypatch):
    require = AsyncMock()
    require_trace_ids = AsyncMock()
    monkeypatch.setattr(ResourceIdService, "require", require)
    monkeypatch.setattr(ResourceIdService, "require_trace_ids", require_trace_ids)

    req = ListLogParseResultRequest(
        kb_id="kb-1",
        log_id="log-1",
        aggregated_event_id="event-1",
        trace_id="trace-1",
        trace_ids=["trace-2"],
    )
    run(ResourceIdService.validate_request(req))

    calls = {call.args for call in require.await_args_list}
    assert calls == {
        ("kb", "kb-1"),
        ("log", "log-1"),
        ("aggregated_event", "event-1"),
    }
    require_trace_ids.assert_awaited_once_with(["trace-2", "trace-1"])


def test_list_router_validates_ids_before_querying_service(monkeypatch):
    validate = AsyncMock(side_effect=NotFoundBizException(resource="知识库"))
    list_results = AsyncMock()
    monkeypatch.setattr(ResourceIdService, "validate_request", validate)
    monkeypatch.setattr(
        LogParseResultService,
        "list_log_parse_results",
        list_results,
    )

    req = ListLogParseResultRequest(kb_id="missing-kb")
    with pytest.raises(NotFoundBizException):
        run(log_parse_result_router.list_log_parse_results(req))

    validate.assert_awaited_once_with(req)
    list_results.assert_not_awaited()


@pytest.mark.parametrize("via_router", [False, True])
def test_log_file_list_rejects_missing_or_deleted_kb(monkeypatch, via_router):
    from latency.database.managers.log_file import LogFilePGManager
    from latency.routers import log_file as log_file_router
    from latency.schemas.request import ListLogFilesRequest
    from latency.services.log_file import LogFileService

    find_missing = AsyncMock(return_value=["deleted-kb"])
    list_files = AsyncMock(return_value=(0, []))
    monkeypatch.setattr(ResourceIdPGManager, "find_missing", find_missing)
    monkeypatch.setattr(LogFilePGManager, "list_log_files", list_files)
    list_handler = (
        log_file_router.list_log_files if via_router else LogFileService.list_log_files
    )

    with pytest.raises(NotFoundBizException, match="知识库不存在"):
        run(list_handler("deleted-kb", ListLogFilesRequest()))

    find_missing.assert_awaited_once_with("kb", ["deleted-kb"])
    list_files.assert_not_awaited()


def test_log_file_list_allows_existing_empty_kb(monkeypatch):
    from latency.database.managers.log_file import LogFilePGManager
    from latency.database.managers.task import TaskPGManager
    from latency.routers import log_file as log_file_router
    from latency.schemas.request import ListLogFilesRequest

    monkeypatch.setattr(ResourceIdPGManager, "find_missing", AsyncMock(return_value=[]))
    monkeypatch.setattr(LogFilePGManager, "list_log_files", AsyncMock(return_value=(0, [])))
    monkeypatch.setattr(
        TaskPGManager, "list_current_tasks_by_op_ids", AsyncMock(return_value=[])
    )

    response = run(log_file_router.list_log_files("empty-kb", ListLogFilesRequest()))

    assert response.result.total == 0


_BRPC_TIME_RANGE = (
    "start_time=2026-01-01%2000:00:00&end_time=2026-01-01%2000:01:00"
)


@pytest.fixture
def id_validation_app():
    from latency.routers import brpc_diagnosis as brpc_diagnosis_router
    from latency.routers import brpc_profiling as brpc_profiling_router
    from latency.routers import task as task_router

    app = FastAPI()
    app.include_router(task_router.router)
    app.include_router(brpc_diagnosis_router.router)
    app.include_router(brpc_profiling_router.router)
    app.include_router(log_parse_result_router.router)
    return app


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "method,path",
    [
        # task_id: previously completely unvalidated.
        ("GET", "/task/%20"),
        ("GET", "/task/%2e%2e"),
        ("GET", "/task/%24bad%20id"),
        ("GET", "/task/" + "a" * 65),
        ("PUT", "/task/stop/%20"),
        ("PUT", "/task/stop/" + "a" * 65),
        ("DELETE", "/task/%2e%2e"),
        # brpc-diagnosis task_id/batch_id: previously only min_length=1.
        ("GET", "/brpc-diagnosis/task/%20/batch"),
        ("GET", "/brpc-diagnosis/task/" + "a" * 65 + "/batch"),
        ("GET", "/brpc-diagnosis/batch/%20"),
        ("GET", "/brpc-diagnosis/batch/%2e%2e"),
        ("GET", "/brpc-diagnosis/batch/" + "a" * 65),
        (
            "GET",
            "/brpc-diagnosis/batch/%20/hits?pod_ip=10.0.0.1&thread_id=1",
        ),
        (
            "GET",
            "/brpc-diagnosis/batch/%24bad/thread-logs"
            "?pod_ip=10.0.0.1&thread_id=1",
        ),
        (
            "GET",
            f"/brpc-diagnosis/batch/%2e%2e/interface-timeline"
            f"?{_BRPC_TIME_RANGE}&window_size=1m",
        ),
        (
            "GET",
            f"/brpc-diagnosis/batch/%20/pod-events"
            f"?{_BRPC_TIME_RANGE}&window_size=1s",
        ),
        (
            "GET",
            f"/brpc-diagnosis/batch/%20/thread-events"
            f"?{_BRPC_TIME_RANGE}&window_size=1s",
        ),
        (
            "GET",
            f"/brpc-diagnosis/batch/%2e%2e/abnormal-threads?{_BRPC_TIME_RANGE}",
        ),
        (
            "GET",
            f"/brpc-diagnosis/batch/%20/abnormal-threads/{'a' * 64}"
            f"?pod_ip=10.0.0.1&thread_id=1&{_BRPC_TIME_RANGE}&window_size=1m",
        ),
        # log_parse_result options kb_id query: previously unvalidated.
        ("GET", "/log_parse_result/options?kb_id="),
        ("GET", "/log_parse_result/options?kb_id=%20"),
        ("GET", "/log_parse_result/options?kb_id=" + "a" * 65),
        # brpc_profiling log_id query: previously unvalidated.
        ("GET", f"/brpc_profiling/knowledge/{VALID_KB_ID}?log_id="),
        ("GET", f"/brpc_profiling/knowledge/{VALID_KB_ID}?log_id=%24bad"),
        ("GET", f"/brpc_profiling/knowledge/{VALID_KB_ID}?log_id=" + "a" * 65),
    ],
)
async def test_router_rejects_empty_special_or_overlong_ids_with_422(
    id_validation_app, method, path
):
    transport = httpx.ASGITransport(app=id_validation_app, raise_app_exceptions=False)
    async with httpx.AsyncClient(
        transport=transport, base_url="http://test"
    ) as client:
        response = await client.request(method, path)

    assert response.status_code == 422, (method, path, response.text)


@pytest.mark.asyncio
async def test_task_stop_validates_format_and_existence_before_service(
    id_validation_app, monkeypatch
):
    from latency.routers import task as task_router

    require = AsyncMock()
    stop_task = AsyncMock(return_value=StopTaskMsg(task_id=TASK_ID))
    monkeypatch.setattr(task_router.ResourceIdService, "require", require)
    monkeypatch.setattr(task_router.TaskService, "stop_task", stop_task)

    transport = httpx.ASGITransport(app=id_validation_app, raise_app_exceptions=False)
    async with httpx.AsyncClient(
        transport=transport, base_url="http://test"
    ) as client:
        response = await client.put(f"/task/stop/{TASK_ID}")

    assert response.status_code == 200, response.text
    require.assert_awaited_once_with("task", TASK_ID)
    stop_task.assert_awaited_once_with(TASK_ID)


@pytest.mark.asyncio
async def test_brpc_batch_by_task_validates_task_existence_before_service(
    id_validation_app, monkeypatch
):
    from latency.schemas.brpc_diagnosis import GetBrpcTaskBatchMsg
    from latency.routers import brpc_diagnosis as brpc_diagnosis_router

    require = AsyncMock()
    get_batch_by_task_id = AsyncMock(
        return_value=GetBrpcTaskBatchMsg(task_id=TASK_ID, batch_id=BATCH_ID)
    )
    monkeypatch.setattr(brpc_diagnosis_router.ResourceIdService, "require", require)
    monkeypatch.setattr(
        brpc_diagnosis_router.BrpcDiagnosisService,
        "get_batch_by_task_id",
        get_batch_by_task_id,
    )

    transport = httpx.ASGITransport(app=id_validation_app, raise_app_exceptions=False)
    async with httpx.AsyncClient(
        transport=transport, base_url="http://test"
    ) as client:
        response = await client.get(f"/brpc-diagnosis/task/{TASK_ID}/batch")

    assert response.status_code == 200, response.text
    require.assert_awaited_once_with("task", TASK_ID)
    get_batch_by_task_id.assert_awaited_once_with(TASK_ID)
