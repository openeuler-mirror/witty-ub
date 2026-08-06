from __future__ import annotations

from typing import Dict, List, Type

from latency.schemas.detect import DetectionResult, MetricConfig
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
        values_complete: bool | None = None,
        exceeded_indices: list[int] | None = None,
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


@register_detector(DetectionMode.THRESHOLD_DIRECT)
class ThresholdDirectDetector(DetectorBase):
    """直接阈值检测器：单条数据超过阈值即标记为异常"""

    async def detect(
        self,
        results: List[LogParseResultModel],
        values: list[float | None] | None = None,
        values_complete: bool | None = None,
        exceeded_indices: list[int] | None = None,
    ) -> DetectionResult:
        field_name = self.config.field_name
        threshold_ms = self.config.threshold_ms

        if values is None:
            values = [getattr(r, field_name, None) for r in results]

        anomalous_indices = []
        reasons = {}

        indices = exceeded_indices if exceeded_indices is not None else range(len(values))
        for idx in indices:
            value = values[idx]
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
    DetectionMode.THRESHOLD_DIRECT: ThresholdDirectDetector,
}
