# Copyright (c) Huawei Technologies Co., Ltd. 2023-2025. All rights reserved.
"""三个任务的 [timing] 打点契约 + 服务层分组取数（stage_timings / task_spans）。

契约（前端按此渲染）::

    [timing] {"task_type":"<TaskTypeEnum 值>","total_s":80.2,"rows":0,
     "stages":[{"stage":"diagnose_tool","label":"运行定界工具","wall_s":78.9,
                "cpu_s":null,"cores":null,"start_s":0.4,"end_s":79.3,"detail":"…"}]}

覆盖：
  1. 顶层 task_type；每阶段 start_s / end_s = 相对 run() 起点的偏移，单调不回退。
  2. 三组阶段键与固定中文 label（诊断三段 / 落库三段 / 解析六段）。
  3. 服务层按 task_type 分组各取一条 —— 最后 emit 的 store 任务不顶掉解析那条。
  4. 两个接口都下发 stage_timings / task_spans，且 parse_timing 仍在。

运行：
  cd src/plugins/latency && PYTHONPATH=<repo>/src/plugins     <venv>/bin/python -m pytest test/test_task_stage_timing.py -q
"""
from __future__ import annotations

import json
from datetime import datetime, timedelta

from latency.ENUM.task import TaskStatusEnum, TaskTypeEnum
from latency.schemas.log import LogFileModel
from latency.schemas.request import ListLogFilesRequest
from latency.schemas.task import TaskModel, TaskReportModel
from latency.services import log_file as log_file_module
from latency.services.log_file import (
    LogFileService,
    _extract_task_timings,
    _extract_parse_timing,
)

PARSE = TaskTypeEnum.KV_CACHE_LOG_PARSE_WORKER.value
DIAG = TaskTypeEnum.KV_CACHE_LOG_EVENT_DIAGNOSIS_WORKER.value
STORE = TaskTypeEnum.STORE_TRACE_CONTEXT_LOGS_WORKER.value

PREFIX = "[timing] "
BASE_TIME = datetime(2026, 9, 15, 10, 0, 0)


class _Scripted:
    def __init__(self, values):
        self._values = list(values)

    def __call__(self):
        assert self._values, "scripted source exhausted"
        return self._values.pop(0)


def _timing(messages_timing):
    return PREFIX + json.dumps(messages_timing, ensure_ascii=False, separators=(",", ":"))


def _report(message, seconds_ago: int = 0, task_id: str = "t"):
    return TaskReportModel(
        task_id=task_id,
        progress=100.0,
        message=message,
        created_at=BASE_TIME - timedelta(seconds=seconds_ago),
    )


def _parse(message):
    return json.loads(message[len(PREFIX):])


# ── 1. 报告本身：task_type + 阶段偏移 ─────────────────────────────────────
def test_report_carries_task_type_and_stage_offsets():
    from latency.common.stage_timing import StageTimer

    # run() 起点 = 100.0（started_at），第一段起点 100.4（run 入口到第一段之间）
    timer = StageTimer(
        clock=_Scripted([100.4, 178.9, 178.9, 179.3, 180.0]),  # 末值给 to_message 的端到端
        cpu_reader=lambda: None,
        started_at=100.0,
        task_type=TaskTypeEnum.KV_CACHE_LOG_EVENT_DIAGNOSIS_WORKER,
    )
    with timer.stage("diagnose_prepare"):
        pass
    with timer.stage("diagnose_tool") as scope:
        scope.detail = "witty-ub-diag-tool"

    payload = _parse(timer.to_message(rows=0))

    assert list(payload.keys())[0] == "task_type"
    assert payload["task_type"] == "kv_cache_log_event_diagnosis_worker"
    assert [s["stage"] for s in payload["stages"]] == ["diagnose_prepare", "diagnose_tool"]
    assert [s["label"] for s in payload["stages"]] == ["准备", "运行定界工具"]
    assert payload["stages"][0]["start_s"] == 0.4
    assert payload["stages"][0]["end_s"] == 78.9
    assert payload["stages"][1]["start_s"] == 78.9
    assert payload["stages"][1]["end_s"] == 79.3
    assert payload["stages"][1]["start_s"] >= payload["stages"][0]["end_s"]  # 不回退


def test_task_type_null_when_not_given_and_started_at_absent():
    from latency.common.stage_timing import StageTimer

    timer = StageTimer(clock=_Scripted([5.0, 6.0]), cpu_reader=lambda: None)
    with timer.stage("trace_store_write"):
        pass

    payload = _parse(timer.to_message(rows=0))
    assert payload["task_type"] is None
    assert payload["stages"][0]["start_s"] == 0.0  # 没给起点 → 以首次登记为 0
    assert payload["stages"][0]["end_s"] == 1.0


def test_offsets_are_monotonic_even_when_registered_out_of_order():
    from latency.common.stage_timing import StageTimer

    timer = StageTimer(started_at=0.0, task_type=STORE, cpu_reader=lambda: None)
    # 手工登记：故意把后一段的时间点填得比前一段早
    timer.add("trace_store_write", wall_s=2.0, start=10.0, end=12.0)
    timer.add("trace_store_collect", wall_s=1.0, start=5.0, end=6.0)

    stages = _parse(timer.to_message(rows=0))["stages"]
    by_key = {s["stage"]: s for s in stages}
    # collect 在管线顺序里排在 write 之前，两个时间点分别是 5/6 与 10/12
    assert by_key["trace_store_collect"]["start_s"] == 5.0
    assert by_key["trace_store_collect"]["end_s"] == 6.0
    assert by_key["trace_store_write"]["start_s"] == 10.0
    assert by_key["trace_store_write"]["end_s"] == 12.0
    assert [s["start_s"] for s in stages] == sorted(s["start_s"] for s in stages)


def test_add_without_explicit_times_still_gets_a_position():
    from latency.common.stage_timing import StageTimer

    timer = StageTimer(started_at=0.0, task_type=STORE, cpu_reader=lambda: None)
    timer.add("trace_store_wait", wall_s=1.5)
    timer.add("trace_store_write", wall_s=0.25)

    stages = _parse(timer.to_message(rows=0))["stages"]
    assert all(s["start_s"] is not None and s["end_s"] is not None for s in stages)
    assert all(s["end_s"] >= s["start_s"] for s in stages)          # 阶段自身不倒退
    assert [s["start_s"] for s in stages] == sorted(s["start_s"] for s in stages)
    assert [s["end_s"] for s in stages] == sorted(s["end_s"] for s in stages)


def test_repeated_stage_covers_both_occurrences_without_shifting_the_next_stage():
    """落库任务的三段各登记两次（等诊断→落库，然后再等解析→再落库）。

    真实数据上踩到过：把 start 硬推到上一段 end 之后，会画出"落库 wall 0.574s、
    跨度 0.003s"这种自相矛盾的位置。口径改为跨度覆盖全部登记 + 各自不回退。
    """
    from latency.common.stage_timing import StageTimer

    timer = StageTimer(started_at=0.0, task_type=STORE, cpu_reader=lambda: None)
    # 相位一
    timer.add("trace_store_wait", wall_s=2.03, start=0.05, end=2.08)
    timer.add("trace_store_collect", wall_s=0.003, start=2.08, end=2.083)
    timer.add("trace_store_write", wall_s=0.574, start=2.083, end=2.657)
    # 相位二
    timer.add("trace_store_wait", wall_s=0.001, start=2.657, end=2.658)
    timer.add("trace_store_collect", wall_s=0.001, start=2.658, end=2.659)
    timer.add("trace_store_write", wall_s=0.001, start=2.659, end=2.66)

    stages = _parse(timer.to_message(rows=0))["stages"]
    by_key = {s["stage"]: s for s in stages}
    wait = by_key["trace_store_wait"]
    collect = by_key["trace_store_collect"]
    write = by_key["trace_store_write"]

    assert (wait["start_s"], wait["end_s"]) == (0.05, 2.658)
    assert (collect["start_s"], collect["end_s"]) == (2.08, 2.659)
    assert (write["start_s"], write["end_s"]) == (2.083, 2.66)
    # 跨度覆盖每次登记 → 跨度 ≥ 累加 wall
    for stage in (wait, collect, write):
        assert stage["wall_s"] <= round(stage["end_s"] - stage["start_s"], 3)
    # 不回退：start 序列 / end 序列各自非递减（重叠是真实形状，允许）
    assert [s["start_s"] for s in stages] == sorted(s["start_s"] for s in stages)
    assert [s["end_s"] for s in stages] == sorted(s["end_s"] for s in stages)


def test_repeated_stage_keeps_each_occurrence_separately():
    """同一阶段登记两次 → occurrences 各留一条（真机 demo6 的形状）。

    合并跨度把两轮等待并成 0.053→2.094 一条，图上压住了中间的落库块；
    occurrences 保留"等定界"和"等解析"各自的真实起止与详情。
    """
    from latency.common.stage_timing import StageTimer

    timer = StageTimer(started_at=0.0, task_type=STORE, cpu_reader=lambda: None)
    timer.add("trace_store_wait", wall_s=1.007, detail="等故障定界完成", start=0.053, end=1.06)
    timer.add("trace_store_collect", wall_s=0.003, detail="定界产出 0 个故障 trace", start=1.065, end=1.068)
    timer.add("trace_store_write", wall_s=0.5, detail="故障 trace 0 条落库", start=1.066, end=1.566)
    timer.add("trace_store_wait", wall_s=1.024, detail="等解析完成", start=1.57, end=2.594)
    timer.add("trace_store_collect", wall_s=0.003, detail="解析新增时延异常 3 个 trace_id", start=2.594, end=2.597)
    timer.add("trace_store_write", wall_s=0.501, detail="时延异常 trace 3 条落库", start=2.597, end=3.098)

    stages = {s["stage"]: s for s in _parse(timer.to_message())["stages"]}
    wait = stages["trace_store_wait"]

    assert [o["start_s"] for o in wait["occurrences"]] == [0.053, 1.57]
    assert [o["end_s"] for o in wait["occurrences"]] == [1.06, 2.594]
    assert [o["wall_s"] for o in wait["occurrences"]] == [1.007, 1.024]
    assert [o["detail"] for o in wait["occurrences"]] == ["等故障定界完成", "等解析完成"]
    assert list(wait["occurrences"][0].keys()) == ["start_s", "end_s", "wall_s", "detail"]
    # 阶段级仍然是并集跨度 + 累加 wall（老前端契约不变）
    assert (wait["start_s"], wait["end_s"]) == (0.053, 2.594)
    assert wait["wall_s"] == 2.031  # 1.007 + 1.024，累加后 3 位小数
    # 两轮三段的详情都各自留着，不再被第一轮吞掉
    assert [o["detail"] for o in stages["trace_store_write"]["occurrences"]] == [
        "故障 trace 0 条落库", "时延异常 trace 3 条落库",
    ]
    assert sum(len(s["occurrences"]) for s in stages.values()) == 6


def test_single_registration_gets_exactly_one_occurrence():
    from latency.common.stage_timing import StageTimer

    timer = StageTimer(started_at=0.0, task_type=PARSE, cpu_reader=lambda: None)
    timer.add("scan", wall_s=2.5, detail="613 文件 / 101831 行", start=0.006, end=2.506)

    stages = _parse(timer.to_message())["stages"]
    assert len(stages) == 1
    assert stages[0]["occurrences"] == [
        {"start_s": 0.006, "end_s": 2.506, "wall_s": 2.5, "detail": "613 文件 / 101831 行"}
    ]


def test_three_task_stage_keys_and_labels_are_frozen():
    from latency.common.stage_timing import STAGE_LABELS, STAGE_ORDER

    assert STAGE_LABELS["diagnose_prepare"] == "准备"
    assert STAGE_LABELS["diagnose_tool"] == "运行定界工具"
    assert STAGE_LABELS["diagnose_persist"] == "落失败事件"
    assert STAGE_LABELS["trace_store_wait"] == "等待前序任务"
    assert STAGE_LABELS["trace_store_collect"] == "生成 trace_id 集合"
    assert STAGE_LABELS["trace_store_write"] == "落库"
    # 解析六段原样保留（前端老契约）
    assert [STAGE_LABELS[k] for k in STAGE_ORDER[:6]] == [
        "扫描", "归并", "聚合", "明细", "分桶", "写库",
    ]
    assert set(STAGE_ORDER) == set(STAGE_LABELS)


def test_diagnosis_and_store_stage_keys_are_whitelisted():
    """白名单没扩就会静默丢弃：三组键都必须能真的登记下来。"""
    from latency.common.stage_timing import StageTimer

    timer = StageTimer(started_at=0.0, cpu_reader=lambda: None, task_type=DIAG)
    for key, wall in (
        ("diagnose_prepare", 0.1),
        ("diagnose_tool", 1.0),
        ("diagnose_persist", 0.2),
    ):
        timer.add(key, wall_s=wall)
    timer2 = StageTimer(started_at=0.0, cpu_reader=lambda: None, task_type=STORE)
    for key, wall in (
        ("trace_store_wait", 1.0),
        ("trace_store_collect", 0.5),
        ("trace_store_write", 2.0),
    ):
        timer2.add(key, wall_s=wall)

    assert [s["stage"] for s in _parse(timer.to_message())["stages"]] == [
        "diagnose_prepare", "diagnose_tool", "diagnose_persist",
    ]
    assert [s["stage"] for s in _parse(timer2.to_message())["stages"]] == [
        "trace_store_wait", "trace_store_collect", "trace_store_write",
    ]


# ── 2. 服务层：按 task_type 分组各取一条 ──────────────────────────────────
def _payload(task_type: str, total_s: float, stage: str) -> dict:
    return {
        "task_type": task_type,
        "total_s": total_s,
        "rows": 0,
        "stages": [{"stage": stage, "label": "x", "wall_s": total_s}],
    }


def test_groups_by_task_type_not_by_global_newest():
    """三个任务并发：最后 emit 的 store 任务不能把解析那条顶掉。"""
    parse_payload = _payload(PARSE, 11.885, "scan")
    diag_payload = _payload(DIAG, 80.2, "diagnose_tool")
    store_payload = _payload(STORE, 12.0, "trace_store_write")
    groups = [
        (PARSE, [_report(_timing(parse_payload), seconds_ago=300, task_id="t-parse")]),
        (DIAG, [_report(_timing(diag_payload), seconds_ago=60, task_id="t-diag")]),
        (STORE, [_report(_timing(store_payload), seconds_ago=1, task_id="t-store")]),
    ]

    stage_timings, task_spans = _extract_task_timings(groups)

    assert set(stage_timings) == {PARSE, DIAG, STORE}
    assert stage_timings[PARSE] == parse_payload
    assert stage_timings[DIAG] == diag_payload
    assert stage_timings[STORE] == store_payload
    assert [span["task_type"] for span in task_spans] == [PARSE, DIAG, STORE]


def test_task_spans_have_iso_start_end_and_duration():
    groups = [
        (
            DIAG,
            [
                _report("运行任务", seconds_ago=90, task_id="t-diag"),
                _report("运行定界工具", seconds_ago=80, task_id="t-diag"),
                _report(_timing(_payload(DIAG, 80.2, "diagnose_tool")), seconds_ago=10, task_id="t-diag"),
            ],
        ),
    ]

    _, task_spans = _extract_task_timings(groups)

    span = task_spans[0]
    assert span["task_type"] == DIAG
    assert span["start"] == (BASE_TIME - timedelta(seconds=90)).isoformat(timespec="milliseconds")
    assert span["end"] == (BASE_TIME - timedelta(seconds=10)).isoformat(timespec="milliseconds")
    assert span["duration_s"] == 80.0
    assert datetime.fromisoformat(span["start"]) < datetime.fromisoformat(span["end"])


def test_group_without_timing_report_is_absent():
    groups = [
        (PARSE, [_report("解析完成", seconds_ago=30, task_id="t-parse")]),
        (STORE, [_report(_timing(_payload(STORE, 3.0, "trace_store_write")), seconds_ago=1)]),
    ]
    stage_timings, task_spans = _extract_task_timings(groups)

    assert set(stage_timings) == {STORE}
    assert [span["task_type"] for span in task_spans] == [STORE]


def test_group_with_broken_newest_timing_falls_back_to_expected_type_key():
    """老报告没有 task_type 字段 → 用调用方给的预期任务类型当键。"""
    groups = [
        (DIAG, [_report(PREFIX + json.dumps({"total_s": 1.0, "stages": []}), seconds_ago=1)]),
    ]
    stage_timings, _ = _extract_task_timings(groups)

    assert list(stage_timings) == [DIAG]


def test_empty_groups_give_none():
    assert _extract_task_timings([]) == (None, None)
    assert _extract_task_timings(None) == (None, None)
    # 老入口仍在，且口径不变
    assert _extract_parse_timing([]) is None
    assert _extract_parse_timing([_report(PREFIX + "{broken", seconds_ago=1)]) is None


# ── 3. 接口装配 ───────────────────────────────────────────────────────────
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
        return [t for t in tasks if t.task_type == task_type and t.op_id in ids]

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


def _all_three_tasks():
    return [
        _task("t-parse", TaskTypeEnum.KV_CACHE_LOG_PARSE_WORKER, TaskStatusEnum.SUCCESSFUL),
        _task("t-diag", TaskTypeEnum.KV_CACHE_LOG_EVENT_DIAGNOSIS_WORKER, TaskStatusEnum.SUCCESSFUL),
        _task("t-store", TaskTypeEnum.STORE_TRACE_CONTEXT_LOGS_WORKER, TaskStatusEnum.SUCCESSFUL),
    ]


def _reports_of_three_tasks():
    return {
        "t-parse": [
            _report("解析中 50%", seconds_ago=200, task_id="t-parse"),
            _report(_timing(_payload(PARSE, 11.885, "scan")), seconds_ago=120, task_id="t-parse"),
        ],
        "t-diag": [
            _report("运行任务", seconds_ago=110, task_id="t-diag"),
            _report(_timing(_payload(DIAG, 80.2, "diagnose_tool")), seconds_ago=70, task_id="t-diag"),
        ],
        "t-store": [
            _report("Task running", seconds_ago=60, task_id="t-store"),
            _report(_timing(_payload(STORE, 12.0, "trace_store_write")), seconds_ago=1, task_id="t-store"),
        ],
    }


async def test_list_log_files_exposes_three_task_timings(monkeypatch):
    _install_fakes(monkeypatch, _all_three_tasks(), _reports_of_three_tasks())

    msg = await LogFileService.list_log_files("kb-1", ListLogFilesRequest())
    got = msg.log_files[0]

    assert set(got.stage_timings) == {PARSE, DIAG, STORE}
    assert got.stage_timings[PARSE]["total_s"] == 11.885  # 没被后 emit 的 store 顶掉
    assert len(got.task_spans) == 3
    assert got.parse_timing == got.stage_timings[PARSE]
    assert {span["task_type"] for span in got.task_spans} == {PARSE, DIAG, STORE}


async def test_get_log_file_by_id_exposes_three_task_timings(monkeypatch):
    _install_fakes(monkeypatch, _all_three_tasks(), _reports_of_three_tasks())

    msg = await LogFileService.get_log_file_by_log_file_id("log-1")
    got = msg.log_file

    assert set(got.stage_timings) == {PARSE, DIAG, STORE}
    assert got.stage_timings[STORE]["total_s"] == 12.0
    assert len(got.task_spans) == 3
    assert got.parse_timing == got.stage_timings[PARSE]
    # 两个接口口径一致
    assert got.task_spans == msg.log_file.task_spans


async def test_fields_default_to_none_and_serialize(monkeypatch):
    reports = {
        "t-parse": [_report("解析完成", seconds_ago=30, task_id="t-parse")],
        "t-diag": [_report("完成", seconds_ago=20, task_id="t-diag")],
        "t-store": [_report("完成", seconds_ago=1, task_id="t-store")],
    }
    _install_fakes(monkeypatch, _all_three_tasks(), reports)

    msg = await LogFileService.list_log_files("kb-1", ListLogFilesRequest())
    got = msg.log_files[0]

    assert got.stage_timings is None and got.task_spans is None
    assert got.parse_timing is None
    dumped = got.model_dump()
    assert dumped["stage_timings"] is None and dumped["task_spans"] is None
    # 可直接 json.dumps（字段是纯 dict / list）
    assert json.loads(json.dumps(dumped, default=str))["parse_timing"] is None
