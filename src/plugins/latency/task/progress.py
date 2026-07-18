"""Task progress helpers.

Task reports also contain performance diagnostics whose ``progress`` value is
an elapsed duration.  Those reports must never participate in UI progress.
"""

from latency.ENUM.task import TaskStatusEnum, TaskTypeEnum


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

    # 根据任务类型确定进度消息前缀（支持中英文，前缀匹配）
    expected_prefixes = {
        TaskTypeEnum.KV_CACHE_LOG_PARSE_WORKER: {
            "Log parse",        # English
            "日志解析",          # Chinese
        },
        TaskTypeEnum.KV_CACHE_LOG_EVENT_DIAGNOSIS_WORKER: {
            "Anomaly detection",     # English
            "Aggregate events",      # English
            "Fault matching",        # English
            "运行诊断",               # Chinese
            "诊断工具",               # Chinese
            "运行定界",               # Chinese
            "定界工具",               # Chinese
            "故障事件",               # Chinese
            "Trace故障",             # Chinese
        },
        TaskTypeEnum.STORE_TRACE_CONTEXT_LOGS_WORKER: {
            "Results stored",              # English
            "Trace context logs stored",   # English
            "Trace上下文落库",             # Chinese
        },
    }.get(task.task_type)

    values = []
    for report in task.task_reports:
        # 排除性能报告
        if _is_non_progress_report(report):
            continue
        # 排除预处理报告（当 include_preprocess=False 时）
        if not include_preprocess and _is_preprocess_report(report):
            continue
        # 如果有预期前缀，只保留匹配前缀的消息（排除关于等待其他任务的报告）
        if expected_prefixes:
            message = (report.message or "").strip()
            if message and not any(
                message.startswith(prefix) for prefix in expected_prefixes
            ):
                continue
        values.append(min(100.0, max(0.0, float(report.progress))))

    return max(values, default=0.0)  # 取最大值


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
    preprocess_weight = min(preprocess_progress, 5.0)  # 预处理进度最大占5%
    # 取三个任务进度的平均值
    task_progress_values = [_task_progress(task, include_preprocess=False) for task in tasks]
    task_average = sum(task_progress_values) / len(task_progress_values) if task_progress_values else 0.0
    return min(
        100.0,
        preprocess_weight + (100.0 - preprocess_weight) * task_average / 100.0,
    )
