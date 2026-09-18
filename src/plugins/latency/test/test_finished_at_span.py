# Copyright (c) Huawei Technologies Co., Ltd. 2023-2025. All rights reserved.
"""任务跨度的右端口径：``finished_at`` / ``registered_delay_s``。

背景：泳道右端原来只能拿 ``task.completed_at``，而它由调度器**下一拍（1 秒轮询）**
才写进库，比任务真实干完晚最多 ~1s，图上就多出一段说不清的收尾。现在 worker 在
``run()`` 结尾 emit 的 ``[timing]`` 里带 ``finished_at``（发出时刻），服务层用它当跨
度右端，并把 ``completed_at - finished_at`` 单独报成 ``registered_delay_s``。

覆盖：
  1. 报告 payload 里有 ``finished_at``（ISO 毫秒，现场取），且 emit 走同一条路。
  2. ``end`` 优先取 ``finished_at``，其次 ``completed_at``，最后退回报告入库时间。
  3. ``registered_delay_s`` = completed_at − finished_at；缺任一端 → null。
  4. 老报告（无 finished_at）与老调用形式（组只给两项）都不报错，口径不变。
  5. ``started_at``：worker 真正开工的时刻，透传进 task_spans；老报告/坏值 → null。

运行：
  cd src/plugins/latency && PYTHONPATH=<repo>/src/plugins     <venv>/bin/python -m pytest test/test_finished_at_span.py -q
"""
from __future__ import annotations

import asyncio
import json
from datetime import datetime, timedelta

from latency.ENUM.task import TaskTypeEnum
from latency.common.stage_timing import StageTimer
from latency.schemas.task import TaskReportModel
from latency.services.log_file import _extract_task_timings

PARSE = TaskTypeEnum.KV_CACHE_LOG_PARSE_WORKER.value
DIAG = TaskTypeEnum.KV_CACHE_LOG_EVENT_DIAGNOSIS_WORKER.value

PREFIX = "[timing] "
BASE_TIME = datetime(2026, 9, 15, 10, 0, 0)


def _report(message, seconds_ago: int = 0, task_id: str = "t"):
    return TaskReportModel(
        task_id=task_id,
        progress=100.0,
        message=message,
        created_at=BASE_TIME - timedelta(seconds=seconds_ago),
    )


def _timing(task_type, finished_at=None, total_s=1.0, stage="scan", started_at=None):
    payload = {
        "task_type": task_type,
        "total_s": total_s,
        "rows": 0,
        "stages": [{"stage": stage, "label": "x", "wall_s": total_s}],
    }
    if finished_at is not None:
        payload["finished_at"] = finished_at
    if started_at is not None:
        payload["started_at"] = started_at
    return PREFIX + json.dumps(payload, ensure_ascii=False, separators=(",", ":"))


def _parse(message: str) -> dict:
    return json.loads(message[len(PREFIX):])


def _iso(dt: datetime) -> str:
    return dt.isoformat(timespec="milliseconds")


# ── 1. 报告里的 finished_at ─────────────────────────────────────────────
def test_to_message_carries_finished_at_millis():
    timer = StageTimer(clock=lambda: 0.5, cpu_reader=lambda: None, started_at=0.0, task_type=PARSE)
    with timer.stage("scan"):
        pass

    payload = _parse(timer.to_message(rows=7))

    # 契约：started_at 第二、finished_at 第三（键序冻结）
    assert list(payload.keys())[:3] == ["task_type", "started_at", "finished_at"]
    finished = datetime.fromisoformat(payload["finished_at"])
    assert payload["finished_at"] == _iso(finished)  # 毫秒精度、无时区后缀
    assert abs((datetime.now() - finished).total_seconds()) < 60  # 现场取的，不是脚本化时钟


def test_emit_payload_has_finished_at_and_final_stage_ends_before_it():
    """emit 传的时刻 = run() 结尾，因此 finished_at 不会早于最后一段的结束。"""
    sent = {}

    async def reporter(task_id, message, progress):
        sent["message"] = message
        sent["progress"] = progress
        return True

    timer = StageTimer(reporter=reporter, cpu_reader=lambda: None, started_at=0.0, task_type=DIAG)
    with timer.stage("diagnose_tool"):
        pass
    asyncio.run(timer.emit("t-diag", rows=0))

    payload = _parse(sent["message"])
    finished = datetime.fromisoformat(payload["finished_at"])
    assert abs((datetime.now() - finished).total_seconds()) < 60
    assert payload["finished_at"] == _iso(finished)
    assert sent["progress"] == 0.0


# ── 2/3. 服务层的 end 口径与 registered_delay_s ─────────────────────────
def test_end_prefers_finished_at_over_completed_at():
    finished = BASE_TIME - timedelta(seconds=14.1)   # 任务真干完
    completed = BASE_TIME                            # 调度器下一拍才登记
    groups = [
        (
            DIAG,
            [
                _report("运行任务", seconds_ago=90, task_id="t-diag"),
                _report(_timing(DIAG, _iso(finished)), seconds_ago=14, task_id="t-diag"),
            ],
            completed,
        ),
    ]

    _, task_spans = _extract_task_timings(groups)

    span = task_spans[0]
    assert span["end"] == _iso(finished)
    assert span["duration_s"] == 75.9  # = finished - start(90s ago)，按新 end 重算
    assert span["registered_delay_s"] == 14.1


def test_registered_delay_is_null_when_task_not_completed():
    finished = BASE_TIME - timedelta(seconds=3)
    groups = [
        (DIAG, [_report(_timing(DIAG, _iso(finished)), seconds_ago=3)], None),
    ]

    _, task_spans = _extract_task_timings(groups)

    assert task_spans[0]["end"] == _iso(finished)
    assert task_spans[0]["registered_delay_s"] is None


def test_old_report_falls_back_to_completed_at():
    """老报告没有 finished_at：end 退回任务的 completed_at，登记延迟报不出来。"""
    completed = BASE_TIME - timedelta(seconds=1)
    groups = [
        (
            DIAG,
            [
                _report("运行任务", seconds_ago=80, task_id="t-diag"),
                _report(_timing(DIAG), seconds_ago=20, task_id="t-diag"),
            ],
            completed,
        ),
    ]

    _, task_spans = _extract_task_timings(groups)

    assert task_spans[0]["end"] == _iso(completed)
    assert task_spans[0]["duration_s"] == 79.0
    assert task_spans[0]["registered_delay_s"] is None


def test_two_element_group_keeps_old_behaviour():
    """老调用形式（组只给 task_type + reports）：end 仍是那条报告的入库时间。"""
    groups = [
        (
            PARSE,
            [
                _report("解析中", seconds_ago=90),
                _report(_timing(PARSE), seconds_ago=40),
            ],
        ),
    ]

    stage_timings, task_spans = _extract_task_timings(groups)

    assert list(stage_timings) == [PARSE]
    assert task_spans[0]["start"] == _iso(BASE_TIME - timedelta(seconds=90))
    assert task_spans[0]["end"] == _iso(BASE_TIME - timedelta(seconds=40))
    assert task_spans[0]["duration_s"] == 50.0
    assert task_spans[0]["registered_delay_s"] is None


def test_completed_at_accepts_iso_string_and_broken_finished_at_is_ignored():
    completed = _iso(BASE_TIME)
    groups = [
        (
            PARSE,
            [_report(_timing(PARSE, "not-a-timestamp"), seconds_ago=30)],
            completed,
        ),
    ]

    _, task_spans = _extract_task_timings(groups)

    assert task_spans[0]["end"] == completed       # 坏 finished_at 当没有
    assert task_spans[0]["registered_delay_s"] is None
    assert task_spans[0]["duration_s"] == 30.0
# ── 5. started_at：worker 真正开工的时刻（前端泳道锚点） ────────────────────
def test_to_message_started_at_is_the_run_origin():
    """started_at 现场取（= 构造计时器那一刻），ISO 毫秒，与 finished_at 同源。"""
    timer = StageTimer(clock=lambda: 0.5, cpu_reader=lambda: None, started_at=0.0, task_type=PARSE)
    with timer.stage("scan"):
        pass

    payload = _parse(timer.to_message(rows=1))

    assert list(payload.keys())[:3] == ["task_type", "started_at", "finished_at"]
    started = datetime.fromisoformat(payload["started_at"])
    assert payload["started_at"] == _iso(started)                 # 毫秒精度
    assert abs((datetime.now() - started).total_seconds()) < 60   # 现场取的，不是脚本化时钟
    assert datetime.fromisoformat(payload["finished_at"]) >= started


def test_started_at_can_be_injected_deterministically():
    """构造时可显式给开工时刻（测试/回放用），不被现场时钟覆盖。"""
    timer = StageTimer(
        clock=lambda: 0.5,
        cpu_reader=lambda: None,
        started_at=0.0,
        task_type=PARSE,
        wall_run_started_at=BASE_TIME,
    )
    with timer.stage("scan"):
        pass

    assert _parse(timer.to_message())["started_at"] == _iso(BASE_TIME)


def test_span_carries_started_at_from_report():
    """服务层把 started_at 透传进 task_spans；它与 start（任务创建）不是一个点。"""
    created = BASE_TIME - timedelta(seconds=30)      # 最早一条报告 ≈ 任务创建
    run_start = BASE_TIME - timedelta(seconds=28.1)  # 开工：晚 1.9s = 等调度 + 冷启动
    finished = BASE_TIME - timedelta(seconds=20)
    groups = [
        (
            PARSE,
            [
                _report("Task initialized", seconds_ago=30),
                _report(
                    _timing(PARSE, _iso(finished), started_at=_iso(run_start)),
                    seconds_ago=20,
                ),
            ],
            BASE_TIME,
        ),
    ]

    _, task_spans = _extract_task_timings(groups)

    span = task_spans[0]
    assert span["start"] == _iso(created)
    assert span["started_at"] == _iso(run_start)
    assert round((run_start - created).total_seconds(), 3) == 1.9
    assert span["end"] == _iso(finished)


def test_span_started_at_null_for_old_report():
    """老报告没有 started_at → null，前端回退到 start（行为与改造前一致）。"""
    _, task_spans = _extract_task_timings([
        (PARSE, [_report(_timing(PARSE, _iso(BASE_TIME)), seconds_ago=5)]),
    ])

    assert task_spans[0]["started_at"] is None


def test_span_started_at_ignores_broken_value():
    """坏值当没有：不抛异常，给 null。"""
    _, task_spans = _extract_task_timings([
        (
            PARSE,
            [_report(_timing(PARSE, _iso(BASE_TIME), started_at="not-a-timestamp"), seconds_ago=5)],
        ),
    ])

    assert task_spans[0]["started_at"] is None
