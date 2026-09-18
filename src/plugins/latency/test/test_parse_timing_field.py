# Copyright (c) Huawei Technologies Co., Ltd. 2023-2025. All rights reserved.
"""parse_timing 字段单测：解析用时（[timing] 报告）提取到 LogFileModel。

契约（前端按此读取）：
  LogFileModel.parse_timing = 该文件 parse 任务（kv_cache_log_parse_worker）
  报告里 message 以 "[timing] " 开头的最新一条的 JSON 对象本身；没有/非法 -> None。

运行：
  cd src/plugins/latency && PYTHONPATH=<repo>/src/plugins     <venv>/bin/python -m pytest test/test_parse_timing_field.py -v
"""
from __future__ import annotations

import json
from datetime import datetime, timedelta

from latency.ENUM.general import DiagnosisConfigLogType
from latency.ENUM.task import TaskStatusEnum, TaskTypeEnum
from latency.schemas.log import LogFileModel
from latency.schemas.request import ListLogFilesRequest
from latency.schemas.task import TaskModel, TaskReportModel
from latency.services import log_file as log_file_module
from latency.services.log_file import LogFileService, _extract_parse_timing

PREFIX = "[timing] "
TASK_ID = "task-parse-1"
BASE_TIME = datetime(2026, 9, 15, 10, 0, 0)

TIMING_OLD = {
    "total_s": 9.5,
    "rows": 100,
    "stages": [{"stage": "scan", "label": "扫描", "wall_s": 1.0}],
}
TIMING_NEW = {
    "total_s": 11.885,
    "rows": 1909790,
    "stages": [
        {"stage": "scan", "label": "扫描", "wall_s": 2.304, "cpu_s": 18.05},
        {"stage": "write", "label": "写库", "wall_s": 0.4},
    ],
}


def _timing_message(payload: dict) -> str:
    return PREFIX + json.dumps(payload, ensure_ascii=False, separators=(",", ":"))


def _report(message, seconds_ago: int = 0, task_id: str = TASK_ID):
    """seconds_ago 越小 = 越新。"""
    return TaskReportModel(
        task_id=task_id,
        progress=100.0,
        message=message,
        created_at=BASE_TIME - timedelta(seconds=seconds_ago),
    )


# --------------------------------------------------------------------------
# 1. 有该报告：取最新一条，JSON 正常
# --------------------------------------------------------------------------
def test_extracts_newest_timing_report():
    reports = [
        _report("解析中 50%", seconds_ago=60),
        _report(_timing_message(TIMING_OLD), seconds_ago=30),
        _report("存储 trace 上下文完成", seconds_ago=20),
        _report(_timing_message(TIMING_NEW), seconds_ago=10),
    ]
    assert _extract_parse_timing(reports) == TIMING_NEW


def test_newest_by_created_at_not_by_list_order():
    # 故意倒着传（旧->新），证明按 created_at 取最新而不是列表顺序
    reports = [
        _report(_timing_message(TIMING_NEW), seconds_ago=10),
        _report(_timing_message(TIMING_OLD), seconds_ago=30),
    ]
    assert _extract_parse_timing(reports) == TIMING_NEW


def test_payload_is_the_json_object_itself():
    got = _extract_parse_timing([_report(_timing_message(TIMING_NEW))])
    assert got is not None
    assert got["total_s"] == 11.885
    assert got["rows"] == 1909790
    assert got["stages"][0]["stage"] == "scan"


def test_ignores_non_timing_messages():
    reports = [
        _report("任务完成", seconds_ago=5),
        _report(_timing_message(TIMING_OLD), seconds_ago=50),
    ]
    assert _extract_parse_timing(reports) == TIMING_OLD


# --------------------------------------------------------------------------
# 2. 无该报告
# --------------------------------------------------------------------------
def test_no_timing_report_returns_none():
    reports = [
        _report("解析中 10%", seconds_ago=30),
        _report("解析完成", seconds_ago=5),
    ]
    assert _extract_parse_timing(reports) is None


def test_empty_and_none_reports_return_none():
    assert _extract_parse_timing([]) is None
    assert _extract_parse_timing(None) is None


def test_message_none_and_missing_message_ignored():
    class _Bare:
        created_at = BASE_TIME

    reports = [_report(None), _Bare()]
    assert _extract_parse_timing(reports) is None


# --------------------------------------------------------------------------
# 3. JSON 坏（前缀对，内容截断）
# --------------------------------------------------------------------------
def test_broken_json_returns_none():
    assert _extract_parse_timing([_report(PREFIX + '{"total_s": 11.885, "stages": [')]) is None
    assert _extract_parse_timing([_report(PREFIX + '{"total_s": undefined}')]) is None


def test_newest_timing_report_broken_json_returns_none():
    # 契约：只看最新一条；坏掉即 None，不回退到更旧的那条
    reports = [
        _report(_timing_message(TIMING_OLD), seconds_ago=30),
        _report(PREFIX + "{broken", seconds_ago=5),
    ]
    assert _extract_parse_timing(reports) is None


# --------------------------------------------------------------------------
# 4. 前缀对但内容不是 JSON
# --------------------------------------------------------------------------
def test_prefix_but_not_json_returns_none():
    assert _extract_parse_timing([_report(PREFIX + "解析完成")]) is None
    assert _extract_parse_timing([_report(PREFIX)]) is None
    assert _extract_parse_timing([_report(PREFIX + "total_s=11.885")]) is None


def test_valid_json_but_not_object_returns_none():
    assert _extract_parse_timing([_report(PREFIX + "[1, 2, 3]")]) is None
    assert _extract_parse_timing([_report(PREFIX + "123")]) is None
    assert _extract_parse_timing([_report(PREFIX + '"11.885"')]) is None
    assert _extract_parse_timing([_report(PREFIX + "null")]) is None


def test_prefix_must_include_trailing_space():
    assert _extract_parse_timing([_report("[timing]" + json.dumps(TIMING_NEW))]) is None
    assert _extract_parse_timing([_report(" [timing] " + json.dumps(TIMING_NEW))]) is None


# --------------------------------------------------------------------------
# 5. 模型字段：默认 None、可挂对象、随序列化下发
# --------------------------------------------------------------------------
def test_log_file_model_field_default_and_roundtrip():
    model = LogFileModel(id="log-1", kb_id="kb-1", name="a.log")
    assert model.parse_timing is None
    assert model.model_dump()["parse_timing"] is None

    model.parse_timing = _extract_parse_timing([_report(_timing_message(TIMING_NEW))])
    dumped = model.model_dump()
    assert dumped["parse_timing"]["total_s"] == 11.885
    assert dumped["parse_timing"]["stages"][1]["stage"] == "write"
    # 序列化后仍是可直接 json.dumps 的纯 dict
    assert json.loads(json.dumps(dumped))["parse_timing"]["rows"] == 1909790


# --------------------------------------------------------------------------
# 6. 接口装配：可见任务已切到 store 任务时，parse_timing 仍然下发
# --------------------------------------------------------------------------
def _task(task_id: str, task_type: TaskTypeEnum, status: TaskStatusEnum) -> TaskModel:
    return TaskModel(
        id=task_id,
        kb_id="kb-1",
        op_id="log-1",
        task_name=task_type.value,
        task_type=task_type,
        status=status,
    )


def _install_fakes(monkeypatch, tasks, reports_by_task_id):
    """把 4 个 PG 入口换成内存假实现，只验证服务层的字段装配。"""

    async def _require(*args, **kwargs):
        return True

    async def _list_log_files(kb_id, req):
        return (1, [LogFileModel(id="log-1", kb_id="kb-1", name="a.log")])

    async def _get_log_file_by_id(log_file_id):
        return LogFileModel(id=log_file_id, kb_id="kb-1", name="a.log")

    async def _list_current_tasks_by_op_ids(op_ids, task_type=None):
        if task_type is None:
            return []
        ids = set(op_ids)
        return [
            task
            for task in tasks
            if task.task_type == task_type and task.op_id in ids
        ]

    async def _get_current_task_by_op_id(op_id, task_type=None):
        for task in tasks:
            if task.op_id == op_id and (task_type is None or task.task_type == task_type):
                return task
        return None

    async def _list_reports(task_ids):
        return [r for tid in task_ids for r in reports_by_task_id.get(tid, [])]

    monkeypatch.setattr(log_file_module.ResourceIdService, "require", staticmethod(_require))
    monkeypatch.setattr(log_file_module.LogFilePGManager, "list_log_files", staticmethod(_list_log_files))
    monkeypatch.setattr(
        log_file_module.LogFilePGManager, "get_log_file_by_log_file_id", staticmethod(_get_log_file_by_id)
    )
    monkeypatch.setattr(
        log_file_module.TaskPGManager, "list_current_tasks_by_op_ids", staticmethod(_list_current_tasks_by_op_ids)
    )
    monkeypatch.setattr(
        log_file_module.TaskPGManager, "get_current_task_by_op_id", staticmethod(_get_current_task_by_op_id)
    )
    monkeypatch.setattr(
        log_file_module.TaskReportPGManager, "list_task_reports_by_task_ids", staticmethod(_list_reports)
    )


def _completed_parse_running_store():
    """解析+诊断成功、store 还在跑 —— 可见任务因此是 store 任务。"""
    return [
        _task("t-parse", TaskTypeEnum.KV_CACHE_LOG_PARSE_WORKER, TaskStatusEnum.SUCCESSFUL),
        _task("t-diag", TaskTypeEnum.KV_CACHE_LOG_EVENT_DIAGNOSIS_WORKER, TaskStatusEnum.SUCCESSFUL),
        _task("t-store", TaskTypeEnum.STORE_TRACE_CONTEXT_LOGS_WORKER, TaskStatusEnum.RUNNING),
    ]


def _reports_with_timing():
    return {
        "t-parse": [
            _report("解析中 50%", seconds_ago=90, task_id="t-parse"),
            _report(_timing_message(TIMING_NEW), seconds_ago=30, task_id="t-parse"),
        ],
        "t-store": [_report("存储中", seconds_ago=1, task_id="t-store")],
    }


async def test_list_log_files_exposes_parse_timing_after_visible_task_switched(monkeypatch):
    _install_fakes(monkeypatch, _completed_parse_running_store(), _reports_with_timing())

    msg = await LogFileService.list_log_files("kb-1", ListLogFilesRequest())
    got = msg.log_files[0]
    assert got.task is not None and got.task.id == "t-store"
    assert got.parse_timing == TIMING_NEW


async def test_list_log_files_without_timing_report_is_none(monkeypatch):
    reports = {
        "t-parse": [_report("解析完成", seconds_ago=30, task_id="t-parse")],
        "t-store": [_report("存储中", seconds_ago=1, task_id="t-store")],
    }
    _install_fakes(monkeypatch, _completed_parse_running_store(), reports)

    msg = await LogFileService.list_log_files("kb-1", ListLogFilesRequest())
    assert msg.log_files[0].task.id == "t-store"
    assert msg.log_files[0].parse_timing is None


async def test_get_log_file_by_id_exposes_parse_timing(monkeypatch):
    _install_fakes(monkeypatch, _completed_parse_running_store(), _reports_with_timing())

    msg = await LogFileService.get_log_file_by_log_file_id("log-1")
    assert msg.log_file.task is not None and msg.log_file.task.id == "t-store"
    assert msg.log_file.parse_timing == TIMING_NEW


async def test_ubsocket_log_has_no_kvcache_parse_timing(monkeypatch):
    ubsocket_log = LogFileModel(
        id="log-1", kb_id="kb-1", name="b.log", log_type=DiagnosisConfigLogType.UBSOCKET
    )

    async def _require(*args, **kwargs):
        return True

    async def _get_log_file_by_id(log_file_id):
        return ubsocket_log

    tasks = [
        _task("t-brpc-parse", TaskTypeEnum.BRPC_LOG_PARSE_WORKER, TaskStatusEnum.SUCCESSFUL),
        _task("t-brpc-diag", TaskTypeEnum.BRPC_LOG_DIAGNOSIS_WORKER, TaskStatusEnum.RUNNING),
    ]

    async def _get_current_task_by_op_id(op_id, task_type=None):
        for task in tasks:
            if task.op_id == op_id and (task_type is None or task.task_type == task_type):
                return task
        return None

    async def _list_reports(task_ids):
        # 即便 UBSocket 的解析任务恰好发过 [timing]，KVCache 口径也不采纳
        return [_report(_timing_message(TIMING_NEW), task_id="t-brpc-parse")]

    monkeypatch.setattr(log_file_module.ResourceIdService, "require", staticmethod(_require))
    monkeypatch.setattr(
        log_file_module.LogFilePGManager, "get_log_file_by_log_file_id", staticmethod(_get_log_file_by_id)
    )
    monkeypatch.setattr(
        log_file_module.TaskPGManager, "get_current_task_by_op_id", staticmethod(_get_current_task_by_op_id)
    )
    monkeypatch.setattr(
        log_file_module.TaskReportPGManager, "list_task_reports_by_task_ids", staticmethod(_list_reports)
    )

    msg = await LogFileService.get_log_file_by_log_file_id("log-1")
    assert msg.log_file.parse_timing is None


# --------------------------------------------------------------------------
# 7. 接口字段不因异常而失败
# --------------------------------------------------------------------------
async def test_broken_timing_report_does_not_break_endpoint(monkeypatch):
    reports = {
        "t-parse": [_report(PREFIX + "{oops", seconds_ago=30, task_id="t-parse")],
    }
    _install_fakes(monkeypatch, _completed_parse_running_store(), reports)

    msg = await LogFileService.list_log_files("kb-1", ListLogFilesRequest())
    assert msg.log_files[0].parse_timing is None
    assert msg.log_files[0].task.id == "t-store"
