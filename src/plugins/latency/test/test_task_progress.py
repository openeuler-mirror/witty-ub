from types import SimpleNamespace

from pytest import approx

from latency.ENUM.task import TaskStatusEnum, TaskTypeEnum
from latency.common.stage_progress import StageProgress
from latency.task.progress import parallel_overall_progress, task_progress


def _task(
    progress_reports,
    status=TaskStatusEnum.RUNNING,
    task_type=TaskTypeEnum.KV_CACHE_LOG_PARSE_WORKER,
):
    return SimpleNamespace(
        status=status,
        task_type=task_type,
        task_reports=[
            SimpleNamespace(progress=progress, message=message)
            for progress, message in progress_reports
        ],
    )


def test_task_progress_ignores_performance_durations():
    task = _task(
        [
            (40.0, "Log parse completed"),
            (180.0, "[perf][scan.summary] total=180s"),
            (175.0, "[parse_log] Scan+deserialize"),
            (160.0, "[TASK] Parse log"),
        ]
    )

    assert task_progress(task) == 40.0


def test_successful_task_is_complete():
    task = _task([], TaskStatusEnum.SUCCESSFUL_PENDING_REMOVE)

    assert task_progress(task) == 100.0


def test_parallel_progress_averages_both_tasks():
    parse_task = _task([(80.0, "Results stored")])
    diagnosis_task = _task(
        [(40.0, "诊断工具运行完成")],
        task_type=TaskTypeEnum.KV_CACHE_LOG_EVENT_DIAGNOSIS_WORKER,
    )

    assert parallel_overall_progress(parse_task, diagnosis_task) == 60.0


def test_missing_parallel_task_contributes_zero():
    parse_task = _task([(100.0, "Log parse completed")])

    assert parallel_overall_progress(parse_task, None) == 50.0


def test_parallel_progress_counts_preprocess_as_shared_stage():
    parse_task = _task([(10.0, "日志预处理完成")])
    diagnosis_task = _task(
        [(10.0, "复用已完成的日志预处理目录")],
        task_type=TaskTypeEnum.KV_CACHE_LOG_EVENT_DIAGNOSIS_WORKER,
    )

    # 当前数学: 预处理进度封顶 5%, 其余任务进度为 0 → 5.0
    assert parallel_overall_progress(parse_task, diagnosis_task) == 5.0


def test_parallel_progress_scales_task_average_after_preprocess():
    parse_task = _task(
        [
            (10.0, "日志预处理完成"),
            (20.0, "Log parse completed"),
        ]
    )
    diagnosis_task = _task(
        [
            (10.0, "复用已完成的日志预处理目录"),
            (20.0, "运行定界工具"),
        ],
        task_type=TaskTypeEnum.KV_CACHE_LOG_EVENT_DIAGNOSIS_WORKER,
    )

    # 当前数学: 预处理 10 → 封顶 5%; 任务均值 (20+20)/2=20 → 5+95*0.2=24.0
    assert parallel_overall_progress(parse_task, diagnosis_task) == 24.0


def test_parse_worker_progress_gradient():
    parse_task = _task(
        [
            (0.0, "Task initialized"),
            (5.0, "Task running"),
            (20.0, "Log parse completed"),
            (30.0, "Anomaly detection done"),
            (40.0, "Aggregate events done"),
            (50.0, "Fault matching done"),
            (70.0, "Results stored"),
            (85.0, "Trace context logs stored: 10"),
            (100.0, "Task completed successfully"),
        ]
    )

    assert [report.progress for report in parse_task.task_reports] == [
        0.0,
        5.0,
        20.0,
        30.0,
        40.0,
        50.0,
        70.0,
        85.0,
        100.0,
    ]


# ── StageProgress: 权重化 / 单调 / 限流 / 前缀可见性 ─────────────────


class _CollectingReporter:
    """Async reporter collecting (task_id, message, progress) tuples."""

    def __init__(self):
        self.calls = []

    async def __call__(self, task_id, message, progress):
        self.calls.append((task_id, message, progress))


class _FakeClock:
    """Injectable monotonic clock for deterministic rate-limit tests."""

    def __init__(self):
        self.t = 0.0

    def __call__(self):
        return self.t


async def test_stage_progress_is_monotonic_across_full_run():
    reporter = _CollectingReporter()
    sp = StageProgress("t1", reporter=reporter)

    values = []
    for stage, fraction in [
        ("scan", 0.0),
        ("scan", 0.5),
        ("scan", 1.0),
        ("trace_frame", 1.0),
        ("aggregate", 0.25),
        ("aggregate", 1.0),
        ("bucket", 1.0),
        ("detail", 1.0),
        ("store", 1.0),
    ]:
        values.append(await sp.report(stage, fraction))

    assert values == sorted(values), "progress must never regress during a run"
    assert values[-1] == 100.0


async def test_stage_progress_weights_follow_registry():
    reporter = _CollectingReporter()
    sp = StageProgress("t1", reporter=reporter)

    assert await sp.report("scan", 1.0) == 45.0
    assert await sp.report("trace_frame", 1.0) == 60.0
    assert await sp.report("aggregate", 1.0) == 75.0
    assert await sp.report("bucket", 1.0) == 85.0
    assert await sp.report("detail", 1.0) == 90.0
    assert await sp.report("store", 1.0) == 100.0


async def test_stage_progress_never_regresses_on_out_of_order_stages():
    sp = StageProgress("t1", reporter=_CollectingReporter())

    v1 = await sp.report("trace_frame", 1.0)  # 60.0
    v2 = await sp.report("scan", 0.0)  # 自然值 0.0, 单调 max() 后保持 60.0
    v3 = await sp.report("aggregate", 0.2)  # 63.0

    assert v1 == 60.0
    assert v2 == 60.0
    assert v3 == 63.0
    assert v1 <= v2 <= v3


async def test_stage_progress_rate_limits_db_writes():
    clock = _FakeClock()
    reporter = _CollectingReporter()
    sp = StageProgress("t1", reporter=reporter, now_fn=clock)

    # <1% 且 <2s → 不写 DB
    await sp.report("scan", 0.02)  # 0.9%
    assert reporter.calls == []

    # ≥1% → 写 DB
    clock.t = 0.5
    await sp.report("scan", 0.1)  # 4.5%
    assert len(reporter.calls) == 1
    assert reporter.calls[0][2] == 4.5

    # <1% 且 <2s(距上次 0.5s) → 不写
    clock.t = 1.0
    await sp.report("scan", 0.11)  # 4.95%
    assert len(reporter.calls) == 1

    # <1% 但 ≥2s(距上次 2.5s) → 写
    clock.t = 3.0
    await sp.report("scan", 0.12)  # 5.4%
    assert len(reporter.calls) == 2
    assert reporter.calls[1][2] == approx(5.4)


async def test_stage_progress_message_format():
    reporter = _CollectingReporter()
    sp = StageProgress("task-1", reporter=reporter)

    await sp.report("scan", 1.0)

    task_id, message, progress = reporter.calls[0]
    assert task_id == "task-1"
    assert message.startswith("[polars][scan]")
    assert "progress=45.0%" in message
    assert progress == 45.0


async def test_stage_log_follows_perf_convention():
    reporter = _CollectingReporter()
    sp = StageProgress("task-1", reporter=reporter)

    await sp.stage_log("trace_frame", "rows=1000 merge=12ms")

    task_id, message, progress = reporter.calls[0]
    assert task_id == "task-1"
    assert message.startswith("[perf][polars.trace_frame]")
    assert "rows=1000 merge=12ms" in message
    assert progress == 0.0  # [perf] 约定: 不参与 UI 进度


def test_polars_progress_messages_visible_in_task_progress():
    task = _task([(45.0, "[polars][scan] progress=45.0%")])

    assert task_progress(task) == 45.0


def test_perf_reports_still_excluded_with_polars_present():
    task = _task(
        [
            (45.0, "[polars][scan] progress=45.0%"),
            (180.0, "[perf][polars.agg] sd=1 tw=2 anom=3 elapsed=180ms"),
            (175.0, "[parse_log] Scan+deserialize: 175s"),
            (160.0, "[TASK] Parse log"),
        ]
    )

    assert task_progress(task) == 45.0


def test_parallel_progress_with_polars_reports_unchanged():
    parse_task = _task([(80.0, "[polars][store] progress=80.0%")])
    diagnosis_task = _task(
        [(40.0, "诊断工具运行完成")],
        task_type=TaskTypeEnum.KV_CACHE_LOG_EVENT_DIAGNOSIS_WORKER,
    )

    assert parallel_overall_progress(parse_task, diagnosis_task) == 60.0
