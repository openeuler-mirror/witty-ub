from __future__ import annotations

from typing import Dict, List, Type

from latency.common.stats import percentile_from_sorted
from latency.schemas.detect import DetectionResult, MetricConfig, WindowConfig
from latency.schemas.log import LogParseResultModel
from latency.ENUM.detect import DetectionMode


class DetectorBase:
    """检测器基类"""

    def __init__(self, metric_config: MetricConfig):
        self.config = metric_config

    async def detect(
        self,
        results: List[LogParseResultModel],
        values: list[float | None] | None = None,
    ) -> DetectionResult:
        """检测接口"""
        raise NotImplementedError


# 检测器注册器
_detector_registry: Dict[DetectionMode, Type[DetectorBase]] = {}


def register_detector(mode: DetectionMode):
    """装饰器：注册检测器类"""
    def decorator(cls: Type[DetectorBase]) -> Type[DetectorBase]:
        _detector_registry[mode] = cls
        return cls
    return decorator


def get_detector(mode: DetectionMode, config: MetricConfig) -> DetectorBase:
    """工厂方法：根据检测模式获取检测器实例"""
    if mode not in _detector_registry:
        raise ValueError(f"Unknown detection mode: {mode}")
    return _detector_registry[mode](config)


@register_detector(DetectionMode.SLIDING_WINDOW_P99)
class SlidingWindowP99Detector(DetectorBase):
    """滑动窗口P99检测器"""

    async def detect(
        self,
        results: List[LogParseResultModel],
        values: list[float | None] | None = None,
    ) -> DetectionResult:
        cfg = self.config.window_config
        field_name = self.config.field_name
        threshold_ms = self.config.threshold_ms

        n = len(results)
        half_w = cfg.window_size // 2

        if values is None:
            values = [getattr(r, field_name, None) for r in results]
        degraded_windows: List[tuple[int, int, float]] = []

        for center in range(0, n, cfg.window_step):
            start = max(0, center - half_w)
            end = min(n - 1, center + half_w)
            window_values = [v for v in values[start:end+1] if v is not None]
            if not window_values:
                continue
            window_values.sort()
            p99 = percentile_from_sorted(window_values, 99)
            if p99 is not None and p99 > threshold_ms:
                degraded_windows.append((start, end, p99))

        degraded_windows.sort()
        merged = []
        for start, end, p99 in degraded_windows:
            if merged and start <= merged[-1][1] + 1:
                merged[-1] = (merged[-1][0], max(merged[-1][1], end), max(merged[-1][2], p99))
            else:
                merged.append((start, end, p99))

        trimmed = []
        for start, end, p99 in merged:
            clip_start = start
            for i in range(start, end + 1):
                if values[i] is not None and values[i] > threshold_ms:
                    clip_start = i
                    break
            clip_end = end
            for i in range(end, clip_start - 1, -1):
                if values[i] is not None and values[i] > threshold_ms:
                    clip_end = i
                    break
            trimmed.append((clip_start, clip_end, p99))

        anomalous_indices = []
        reasons = {}

        for zone_start, zone_end, p99 in trimmed:
            zone_len = zone_end - zone_start + 1
            exceeded = sum(1 for i in range(zone_start, zone_end + 1)
                         if values[i] is not None and values[i] > threshold_ms)
            density = exceeded / zone_len if zone_len > 0 else 0.0
            is_bulk = density >= cfg.density_threshold

            for idx in range(zone_start, zone_end + 1):
                if is_bulk or (values[idx] is not None and values[idx] > threshold_ms):
                    anomalous_indices.append(idx)
                    if values[idx] is not None:
                        reason = f"{field_name}={values[idx]:.3f}ms > threshold {threshold_ms}ms"
                    else:
                        reason = f"in bulk degraded zone ({field_name} P99={p99:.3f}ms)"
                    if is_bulk and values[idx] is not None and values[idx] <= threshold_ms:
                        reason = f"in bulk degraded zone ({field_name} P99={p99:.3f}ms)"
                    reasons[idx] = reasons.get(idx, []) + [reason]

        return DetectionResult(
            metric_name=field_name,
            anomalous_indices=anomalous_indices,
            reasons=reasons
        )


@register_detector(DetectionMode.THRESHOLD_DIRECT)
class ThresholdDirectDetector(DetectorBase):
    """直接阈值检测器"""

    async def detect(
        self,
        results: List[LogParseResultModel],
        values: list[float | None] | None = None,
    ) -> DetectionResult:
        field_name = self.config.field_name
        threshold_ms = self.config.threshold_ms

        if values is None:
            values = [getattr(r, field_name, None) for r in results]

        anomalous_indices = []
        reasons = {}

        for idx, value in enumerate(values):
            if value is not None and value > threshold_ms:
                anomalous_indices.append(idx)
                reasons[idx] = [f"{field_name}={value:.3f}ms > threshold {threshold_ms}ms"]

        return DetectionResult(
            metric_name=field_name,
            anomalous_indices=anomalous_indices,
            reasons=reasons
        )


# 预定义的检测器类型导出
DETECTOR_TYPES = {
    DetectionMode.SLIDING_WINDOW_P99: SlidingWindowP99Detector,
    DetectionMode.THRESHOLD_DIRECT: ThresholdDirectDetector,
}
