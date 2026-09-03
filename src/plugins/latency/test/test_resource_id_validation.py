import asyncio
from unittest.mock import AsyncMock

import pytest

from latency.database.managers.resource_id import ResourceIdPGManager
from latency.exceptions import NotFoundBizException
from latency.routers import log_parse_result as log_parse_result_router
from latency.schemas.request import ListLogParseResultRequest
from latency.services.log_parse_result import LogParseResultService
from latency.services.resource_id import ResourceIdService


def run(coroutine):
    return asyncio.run(coroutine)


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
