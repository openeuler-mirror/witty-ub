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
            mode=DetectionMode.SLIDING_WINDOW_P99
        )
    ]
    detector = AnomalyDetector(configs)
    events = await detector.detect(results)

3. 添加新检测器（解耦扩展）：
    @register_detector(DetectionMode.SLIDING_WINDOW_P95)
    class SlidingWindowP95Detector(DetectorBase):
        async def detect(self, results):
            # 实现检测逻辑
            pass
"""

from latency.detect.engine import AnomalyDetector, DetectionEngine
from latency.detect.detectors import (
    DetectorBase,
    SlidingWindowP99Detector,
    ThresholdDirectDetector,
    register_detector,
    get_detector,
    DETECTOR_TYPES,
)
from latency.schemas.detect import (
    WindowConfig,
    MetricConfig,
    DetectionResult,
)
from latency.ENUM.detect import DetectionMode

__all__ = [
    "DetectionMode",
    "WindowConfig",
    "MetricConfig",
    "DetectionResult",
    "DetectorBase",
    "SlidingWindowP99Detector",
    "ThresholdDirectDetector",
    "DetectionEngine",
    "AnomalyDetector",
    "register_detector",
    "get_detector",
    "DETECTOR_TYPES",
]