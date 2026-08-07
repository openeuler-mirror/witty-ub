"""Weighted, monotonic, rate-limited stage progress reporting.

Independent "stage registry + weight table": the pipeline body only drives
progress via ``StageProgress.report(stage, fraction)``, so stage names and
weights can be re-balanced later (T3/T5) without touching ``run()``.

Progress is persisted through ``BaseWorker.report`` with a ``[polars]``
message prefix so the UI filter (``latency.task.progress``) can match it;
readable per-stage detail logs follow the ``[perf]`` convention and are
excluded from UI progress.
"""

import logging
import time

from latency.task.worker.base import BaseWorker

logger = logging.getLogger(__name__)

# 阶段注册表 + 权重表(独立于 run()): 权重按实测耗时占比, 合计 100.
#   scan≈45%  trace_frame≈15%  aggregate≈15%  bucket≈10%  detail≈5%  store≈10%
DEFAULT_STAGES: list[tuple[str, float]] = [
    ("scan", 45.0),
    ("trace_frame", 15.0),
    ("aggregate", 15.0),
    ("bucket", 10.0),
    ("detail", 5.0),
    ("store", 10.0),
]

# 进度消息前缀: 已加入 progress.expected_prefixes, 不被 UI 过滤
PROGRESS_MESSAGE_PREFIX = "[polars]"

# 限流: progress 增量 ≥1% 或距上次上报 ~2s 才写 DB
MIN_PROGRESS_DELTA = 1.0
MIN_REPORT_INTERVAL = 2.0


class StageProgress:
    """Weighted monotonic progress reporter with rate-limited DB writes.

    Args:
        task_id: task id reported through ``reporter``.
        stages: override the default stage registry as ``[(label, weight)]``;
            weights are normalized so they need not sum to 100.
        reporter: ``async (task_id, message, progress) -> None``; defaults to
            ``BaseWorker.report``.  Inject a fake in tests.
        now_fn: ``() -> float`` monotonic seconds; inject a fake clock in tests.
    """

    def __init__(self, task_id, stages=None, reporter=None, now_fn=None):
        self.task_id = task_id
        stage_list = list(stages) if stages else list(DEFAULT_STAGES)
        total = sum(weight for _, weight in stage_list) or 1.0
        self._weights = {
            label: weight / total * 100.0 for label, weight in stage_list
        }
        self._offsets: dict[str, float] = {}
        acc = 0.0
        for label, weight in self._weights.items():
            self._offsets[label] = acc
            acc += weight
        self._value = 0.0
        self._last_reported = 0.0
        self._last_report_time = 0.0
        self._reporter = reporter if reporter is not None else BaseWorker.report
        self._now = now_fn or time.monotonic

    def overall(self, stage, fraction) -> float:
        """Overall progress after a stage update, monotonic and clamped [0, 100]."""
        if stage not in self._offsets:
            raise ValueError(
                f"unknown stage {stage!r}; registered stages: {list(self._offsets)}"
            )
        frac = min(1.0, max(0.0, float(fraction)))
        candidate = self._offsets[stage] + frac * self._weights[stage]
        self._value = min(100.0, max(self._value, candidate))
        return self._value

    def _should_report(self, value, now) -> bool:
        if value <= self._last_reported:
            return False
        if value - self._last_reported >= MIN_PROGRESS_DELTA:
            return True
        return now - self._last_report_time >= MIN_REPORT_INTERVAL

    async def report(self, stage, fraction, detail: str = "") -> float:
        """Report progress within a stage; DB-writes only when rate-limited."""
        value = self.overall(stage, fraction)
        now = self._now()
        if self._should_report(value, now):
            message = f"{PROGRESS_MESSAGE_PREFIX}[{stage}] progress={value:.1f}%"
            if detail:
                message = f"{message} {detail}"
            await self._reporter(self.task_id, message, value)
            self._last_reported = value
            self._last_report_time = now
        return value

    async def stage_log(self, stage, detail, elapsed_ms=None) -> None:
        """Readable per-stage log following the ``[perf]`` convention."""
        elapsed = f" elapsed={elapsed_ms:.0f}ms" if elapsed_ms is not None else ""
        logger.info("[polars][%s] %s%s", stage, detail, elapsed)
        await self._reporter(
            self.task_id, f"[perf][polars.{stage}] {detail}{elapsed}", 0.0
        )
