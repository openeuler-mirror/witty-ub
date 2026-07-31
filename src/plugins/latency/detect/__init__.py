"""异常检测模块

使用方式：

1. 使用已配置的检测器：
    detector = AnomalyDetector.from_config()
    events = await detector.detect(results)

2. 自定义检测器配置：
    configs = [
        MetricConfig(
            field_name="total_latency",
            threshold_ms=4.0,
            mode=DetectionMode.THRESHOLD_DIRECT
        )
    ]
    detector = AnomalyDetector(configs)
    events = await detector.detect(results)

3. 添加新检测器（解耦扩展）：
    @register_detector(DetectionMode.THRESHOLD_DIRECT)
    class ThresholdDirectDetector(DetectorBase):
        async def detect(self, results):
            # 实现检测逻辑
            pass
"""

from latency.detect.engine import AnomalyDetector, DetectionEngine
from latency.detect.detectors import (
    DetectorBase,
    ThresholdDirectDetector,
    register_detector,
    get_detector,
    DETECTOR_TYPES,
)
from latency.schemas.detect import (
    MetricConfig,
    DetectionResult,
)
from latency.ENUM.detect import DetectionMode

__all__ = [
    "DetectionMode",
    "MetricConfig",
    "DetectionResult",
    "DetectorBase",
    "ThresholdDirectDetector",
    "DetectionEngine",
    "AnomalyDetector",
    "register_detector",
    "get_detector",
    "DETECTOR_TYPES",
]
