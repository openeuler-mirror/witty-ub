"""common/stage_timing.py 单测：冻结契约 + "打点绝不弄挂任务"。

契约（前端按此解析）::

    [timing] {"task_type":"<TaskTypeEnum 值>","finished_at":"2026-09-15T10:00:03.104",
     "total_s":11.885,"rows":1909790,
     "stages":[{"stage":"scan","label":"扫描","wall_s":2.304,"cpu_s":18.05,
                "cores":7.83,"start_s":0.0,"end_s":2.304,"detail":"..."}]}

覆盖：前缀/单行 JSON/键序（task_type 打头、started_at 第二、finished_at 第三）/中文
label/小数位；没测到的阶段不出现；
total_s == 各阶段 wall_s 之和；cpu 读不到 → null（不补 0）；cores = cpu/wall；
start_s/end_s = 相对 run() 起点的偏移且单调不回退（任务级打点见
test_task_stage_timing.py）；emit 走 reporter(task_id, msg, 0.0)；reporter 抛异常
不向上传播；阶段体内异常照常抛；未知阶段键被忽略；detail 单行化。

运行：cd src/plugins/latency && PYTHONPATH=<repo>/src/plugins \
  .venv/bin/python -m pytest test/test_stage_timing.py -q
"""
import json
from datetime import datetime

import pytest

from latency.common.stage_timing import (
    STAGE_LABELS,
    STAGE_ORDER,
    TIMING_MESSAGE_PREFIX,
    NullStageTimer,
    StageTimer,
    as_stage_timer,
    read_cpu_seconds,
)


class _CollectingReporter:
    """Async reporter collecting (task_id, message, progress) tuples."""

    def __init__(self, fail=False):
        self.calls = []
        self.fail = fail

    async def __call__(self, task_id, message, progress):
        self.calls.append((task_id, message, progress))
        if self.fail:
            raise RuntimeError("reporter down")


class _Scripted:
    """按脚本吐值：每次调用弹出一个（时钟 / CPU 读数的假身）。"""

    def __init__(self, values):
        self._values = list(values)

    def __call__(self):
        assert self._values, "scripted source exhausted"
        return self._values.pop(0)


def _parse(message):
    """按契约取负载：前缀严格 '[timing] '，其后是单行紧凑 JSON。"""
    assert message.startswith(TIMING_MESSAGE_PREFIX)
    return json.loads(message[len(TIMING_MESSAGE_PREFIX):])


# ── 契约：一条报告长什么样 ─────────────────────────────────────────────


def test_message_matches_frozen_contract():
    """前缀 / 单行 / 顶层键序（含 started_at / finished_at）/ label / 小数位 / rows 类型。"""
    clock = _Scripted([100.0, 102.304, 102.304, 102.804, 102.804, 103.104])
    # cpu 读数：scan 10.0→28.05；aggregate 读到 None（不读第二次）；store 5.0→5.25
    cpu = _Scripted([10.0, 28.05, None, 5.0, 5.25])
    timer = StageTimer(clock=clock, cpu_reader=cpu)

    with timer.stage("scan") as scope:
        scope.detail = "11 文件 / 1909790 行"
    with timer.stage("aggregate"):
        pass
    with timer.stage("store"):
        pass

    message = timer.to_message(rows=1909790)

    assert "\n" not in message and "\r" not in message
    assert message.startswith("[timing] ")
    payload = _parse(message)

    assert list(payload.keys()) == [
        "task_type", "started_at", "finished_at", "total_s", "rows", "stages",
    ]
    assert payload["task_type"] is None  # 没给 task_type 时如实给 null，不编一个
    # started_at = 开工时刻（StageTimer 构造点 = run() 起点），也是现场取的
    assert (
        datetime.fromisoformat(payload["started_at"]).isoformat(timespec="milliseconds")
        == payload["started_at"]
    )
    # finished_at = 发出这条报告的时刻（ISO 毫秒，与脚本化时钟无关）
    assert (
        datetime.fromisoformat(payload["finished_at"]).isoformat(timespec="milliseconds")
        == payload["finished_at"]
    )
    assert payload["rows"] == 1909790
    assert isinstance(payload["rows"], int)

    stages = payload["stages"]
    assert [s["stage"] for s in stages] == ["scan", "aggregate", "store"]  # 管线顺序
    assert [list(s.keys()) for s in stages] == [
        [
            "stage", "label", "wall_s", "cpu_s", "cores", "start_s", "end_s",
            "detail", "occurrences",
        ]
    ] * 3
    # 每个阶段只登记一次（with 块）→ 各一条 occurrence，位置与阶段级一致
    for stage in stages:
        assert [list(o.keys()) for o in stage["occurrences"]] == [
            ["start_s", "end_s", "wall_s", "detail"]
        ]
        assert stage["occurrences"][0]["wall_s"] == stage["wall_s"]
        assert stage["occurrences"][0]["start_s"] == stage["start_s"]
        assert stage["occurrences"][0]["end_s"] == stage["end_s"]
    # 阶段在时间轴上的位置：以计时器的时钟原点（第一段起点）为基准、3 位小数、不回退
    assert [s["start_s"] for s in stages] == [0.0, 2.304, 2.804]
    assert [s["end_s"] for s in stages] == [2.304, 2.804, 3.104]

    scan = stages[0]
    assert scan["label"] == "扫描"
    assert scan["wall_s"] == pytest.approx(2.304, abs=1e-9)
    assert scan["cpu_s"] == pytest.approx(18.05, abs=1e-9)
    assert scan["cores"] == pytest.approx(7.83, abs=0.01)
    assert scan["detail"] == "11 文件 / 1909790 行"

    # CPU 读不到 → null（不是 0 占位），cores 也随之 null
    assert stages[1]["label"] == "聚合"
    assert stages[1]["cpu_s"] is None
    assert stages[1]["cores"] is None

    assert stages[2]["label"] == "写库"
    assert stages[2]["wall_s"] == pytest.approx(0.3, abs=1e-9)
    assert stages[2]["cpu_s"] == pytest.approx(0.25, abs=1e-9)


def test_unmeasured_stages_are_absent_and_total_is_the_sum():
    """没测到的阶段不出现；total_s = 已测阶段 wall_s 之和。"""
    clock = _Scripted([0.0, 1.0, 1.0, 3.5])
    timer = StageTimer(clock=clock, cpu_reader=lambda: None)

    with timer.stage("scan"):
        pass
    with timer.stage("bucket"):
        pass

    payload = _parse(timer.to_message(rows=7))

    assert [s["stage"] for s in payload["stages"]] == ["scan", "bucket"]
    assert "trace_frame" not in json.dumps(payload)
    assert payload["total_s"] == pytest.approx(
        sum(s["wall_s"] for s in payload["stages"]), abs=5e-4
    )
    assert payload["total_s"] == pytest.approx(3.5, abs=1e-9)


def test_wall_s_is_rounded_to_three_decimals():
    clock = _Scripted([0.0, 0.123456, 0.123456, 0.123456 + 12.3456789])
    timer = StageTimer(clock=clock, cpu_reader=lambda: None)

    with timer.stage("scan"):
        pass
    with timer.stage("detail"):
        pass

    stages = _parse(timer.to_message(rows=0))["stages"]
    assert [s["wall_s"] for s in stages] == [0.123, 12.346]


def test_same_stage_registered_twice_accumulates():
    """store 同时覆盖"分桶表插入"和"主落库"：wall/cpu 累加，detail 取首个非空。"""
    clock = _Scripted([0.0, 1.0, 1.0, 2.5])
    cpu = _Scripted([0.0, 1.0, 1.0, 2.0])
    timer = StageTimer(clock=clock, cpu_reader=cpu)

    with timer.stage("store"):
        pass
    with timer.stage("store") as scope:
        scope.detail = "明细 1000 行 / 聚合 12 条 / 分桶 4 表"

    stage = _parse(timer.to_message(rows=1))["stages"][0]
    assert stage["wall_s"] == pytest.approx(2.5, abs=1e-9)
    assert stage["cpu_s"] == pytest.approx(2.0, abs=1e-9)
    assert stage["cores"] == pytest.approx(0.8, abs=1e-9)
    assert stage["detail"] == "明细 1000 行 / 聚合 12 条 / 分桶 4 表"


def test_repeated_detailed_stage_keeps_first_non_empty_detail():
    timer = StageTimer(clock=_Scripted([0.0, 1.0, 1.0, 2.0]), cpu_reader=lambda: None)
    with timer.stage("store") as first:
        first.detail = "第一次"
    with timer.stage("store") as second:
        second.detail = "第二次"

    assert _parse(timer.to_message(rows=0))["stages"][0]["detail"] == "第一次"


def test_detail_is_single_line():
    """JSON 内不得有换行：detail 里的换行被压成空格。"""
    timer = StageTimer(clock=_Scripted([0.0, 1.0]), cpu_reader=lambda: None)
    with timer.stage("scan") as scope:
        scope.detail = "11 文件\n/ 1909790 行\r\n"

    message = timer.to_message(rows=0)
    assert "\n" not in message and "\r" not in message
    assert _parse(message)["stages"][0]["detail"] == "11 文件 / 1909790 行"


def test_stage_labels_and_order_are_frozen():
    assert STAGE_LABELS == {
        "scan": "扫描",
        "trace_frame": "归并",
        "aggregate": "聚合",
        "detail": "明细",
        "bucket": "分桶",
        "store": "写库",
        "diagnose_prepare": "准备",
        "diagnose_tool": "运行定界工具",
        "diagnose_persist": "落失败事件",
        "trace_store_wait": "等待前序任务",
        "trace_store_collect": "生成 trace_id 集合",
        "trace_store_write": "落库",
    }
    assert STAGE_ORDER == (
        "scan",
        "trace_frame",
        "aggregate",
        "detail",
        "bucket",
        "store",
        "diagnose_prepare",
        "diagnose_tool",
        "diagnose_persist",
        "trace_store_wait",
        "trace_store_collect",
        "trace_store_write",
    )


def test_manual_add_registers_stage():
    """已有时序点用 add() 手工登记（含 cpu 读不到的情况）。"""
    timer = StageTimer()
    timer.add("trace_frame", wall_s=1.5, cpu_s=None, detail="11 条 trace")
    timer.add("scan", wall_s=2.0, cpu_s=8.0)

    stages = _parse(timer.to_message(rows=3))["stages"]
    assert [s["stage"] for s in stages] == ["scan", "trace_frame"]  # 按管线顺序，不按登记序
    assert stages[1]["cpu_s"] is None
    assert stages[0]["cpu_s"] == pytest.approx(8.0)
    assert stages[1]["detail"] == "11 条 trace"


def test_unknown_stage_key_is_ignored():
    """stage 键取值仅限 6 个：未知键不登记、不进 JSON，只记 warning。"""
    timer = StageTimer(clock=_Scripted([0.0, 1.0]), cpu_reader=lambda: None)
    with timer.stage("nope") as scope:  # 空块，不消耗时钟
        scope.detail = "x"
    timer.add("also-nope", wall_s=99.0)

    payload = _parse(timer.to_message(rows=0))
    assert payload["stages"] == []
    assert payload["total_s"] == 0.0


# ── 打点绝不弄挂任务 ───────────────────────────────────────────────────


async def test_emit_uses_base_report_signature():
    reporter = _CollectingReporter()
    timer = StageTimer(reporter=reporter, clock=_Scripted([0.0, 1.0]), cpu_reader=lambda: None)
    with timer.stage("scan"):
        pass

    message = await timer.emit("task-1", rows=42)

    task_id, sent, progress = reporter.calls[0]
    assert task_id == "task-1"
    assert sent == message
    assert progress == 0.0
    assert _parse(sent)["rows"] == 42


async def test_emit_swallows_reporter_failure():
    """/log_file/list 写库失败不能把任务弄挂：emit 只返回空串。"""
    reporter = _CollectingReporter(fail=True)
    timer = StageTimer(reporter=reporter, clock=_Scripted([0.0, 1.0]), cpu_reader=lambda: None)
    with timer.stage("scan"):
        pass

    assert await timer.emit("task-1", rows=1) == ""


def test_stage_body_exception_propagates_but_still_times():
    clock = _Scripted([0.0, 2.0])
    timer = StageTimer(clock=clock, cpu_reader=lambda: None)

    with pytest.raises(ValueError):
        with timer.stage("scan"):
            raise ValueError("boom")

    assert _parse(timer.to_message(rows=0))["stages"][0]["wall_s"] == pytest.approx(2.0)


def test_cpu_reader_failure_yields_null_not_zero():
    def _boom():
        raise RuntimeError("no /proc here")

    timer = StageTimer(clock=_Scripted([0.0, 1.0]), cpu_reader=_boom)
    with timer.stage("scan"):
        pass

    stage = _parse(timer.to_message(rows=0))["stages"][0]
    assert stage["cpu_s"] is None and stage["cores"] is None


def test_read_cpu_seconds_none_when_proc_missing(monkeypatch):
    """平台不支持（Windows 无 /proc、无 os.sysconf）时返回 None，不抛。"""
    import builtins

    real_open = builtins.open

    def _no_proc(file, *args, **kwargs):
        if str(file) == "/proc/self/stat":
            raise FileNotFoundError("no /proc")
        return real_open(file, *args, **kwargs)

    monkeypatch.setattr(builtins, "open", _no_proc)
    assert read_cpu_seconds() is None


def test_read_cpu_seconds_parses_proc_stat(monkeypatch):
    """utime(14) + stime(15) / SC_CLK_TCK；comm 含空格/括号也要切对。"""
    import builtins
    import io

    # 字段: 1 pid, 2 comm, 3 state, ... 14 utime=120, 15 stime=80
    fields = ["1234", "(my (odd) proc)", "R"]
    fields += ["0"] * 10  # 4..13
    fields += ["120", "80"]  # 14, 15
    raw = " ".join(fields).encode()

    real_open = builtins.open

    def _fake_open(file, *args, **kwargs):
        if str(file) == "/proc/self/stat":
            return io.BytesIO(raw)
        return real_open(file, *args, **kwargs)

    monkeypatch.setattr(builtins, "open", _fake_open)
    monkeypatch.setattr("os.sysconf", lambda name: 100, raising=False)

    assert read_cpu_seconds() == pytest.approx(2.0)


# ── 空计时器 ───────────────────────────────────────────────────────────


def test_as_stage_timer_falls_back_to_null_timer():
    null = as_stage_timer(None)
    assert isinstance(null, NullStageTimer)

    timer = StageTimer()
    assert as_stage_timer(timer) is timer


async def test_null_timer_is_noop():
    timer = NullStageTimer()
    with timer.stage("scan") as scope:
        scope.detail = "随便写"
    timer.add("scan", wall_s=9.9, detail="x")

    assert timer.to_message(rows=1) == ""
    assert await timer.emit("task-1", rows=1) == ""
