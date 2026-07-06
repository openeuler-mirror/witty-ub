from types import SimpleNamespace

from latency.ENUM.task import TaskStatusEnum
from latency.task.progress import parallel_overall_progress, task_progress


def _task(progress_reports, status=TaskStatusEnum.RUNNING):
    return SimpleNamespace(
        status=status,
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
    diagnosis_task = _task([(40.0, "诊断工具运行完成")])

    assert parallel_overall_progress(parse_task, diagnosis_task) == 60.0


def test_missing_parallel_task_contributes_zero():
    parse_task = _task([(100.0, "Task completed successfully")])

    assert parallel_overall_progress(parse_task, None) == 50.0
