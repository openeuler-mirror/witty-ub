"""Task progress helpers.

Task reports also contain performance diagnostics whose ``progress`` value is
an elapsed duration.  Those reports must never participate in UI progress.
"""

from latency.ENUM.task import TaskStatusEnum


NON_PROGRESS_REPORT_PREFIXES = ("[perf]", "[parse_log]", "[TASK]")
SUCCESS_STATUSES = {
    TaskStatusEnum.SUCCESSFUL,
    TaskStatusEnum.SUCCESSFUL_PENDING_REMOVE,
}


def task_progress(task) -> float:
    """Return a task's own 0-100 progress without mutating its reports."""
    if not task:
        return 0.0
    if task.status in SUCCESS_STATUSES:
        return 100.0

    values = [
        min(100.0, max(0.0, float(report.progress)))
        for report in task.task_reports
        if not (report.message or "").strip().startswith(
            NON_PROGRESS_REPORT_PREFIXES
        )
    ]
    return max(values, default=0.0)


def parallel_overall_progress(*tasks) -> float:
    """Average parallel task progress; a missing task contributes zero."""
    if not tasks:
        return 0.0
    return sum(task_progress(task) for task in tasks) / len(tasks)
