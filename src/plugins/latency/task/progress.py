"""Task progress helpers.

Task reports also contain performance diagnostics whose ``progress`` value is
an elapsed duration.  Those reports must never participate in UI progress.
"""

from latency.ENUM.task import TaskStatusEnum


NON_PROGRESS_REPORT_PREFIXES = ("[perf]", "[parse_log]", "[TASK]")
PREPROCESS_REPORT_MESSAGES = {
    "日志预处理完成",
    "复用已完成的日志预处理目录",
}
SUCCESS_STATUSES = {
    TaskStatusEnum.SUCCESSFUL,
    TaskStatusEnum.SUCCESSFUL_PENDING_REMOVE,
}


def task_progress(task) -> float:
    """Return a task's own 0-100 progress without mutating its reports."""
    return _task_progress(task)


def _is_non_progress_report(report) -> bool:
    return (report.message or "").strip().startswith(NON_PROGRESS_REPORT_PREFIXES)


def _is_preprocess_report(report) -> bool:
    return (report.message or "").strip() in PREPROCESS_REPORT_MESSAGES


def _task_progress(task, *, include_preprocess: bool = True) -> float:
    if not task:
        return 0.0
    if task.status in SUCCESS_STATUSES:
        return 100.0

    values = [
        min(100.0, max(0.0, float(report.progress)))
        for report in task.task_reports
        if not _is_non_progress_report(report)
        and (include_preprocess or not _is_preprocess_report(report))
    ]
    return max(values, default=0.0)


def _preprocess_progress(*tasks) -> float:
    values = [
        min(100.0, max(0.0, float(report.progress)))
        for task in tasks
        if task
        for report in task.task_reports
        if _is_preprocess_report(report)
    ]
    return max(values, default=0.0)


def parallel_overall_progress(*tasks) -> float:
    """Shared preprocessing progress plus average progress of parallel tasks."""
    if not tasks:
        return 0.0
    preprocess_progress = _preprocess_progress(*tasks)
    task_average = (
        sum(_task_progress(task, include_preprocess=False) for task in tasks)
        / len(tasks)
    )
    return min(
        100.0,
        preprocess_progress + (100.0 - preprocess_progress) * task_average / 100.0,
    )
