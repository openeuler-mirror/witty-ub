from dataclasses import dataclass

from latency.ENUM.detect import DetectionMode


@dataclass(slots=True)
class MetricConfig:
    """单个指标的检测配置"""
    field_name: str
    threshold_ms: float
    mode: DetectionMode = DetectionMode.THRESHOLD_DIRECT
    enabled: bool = True


@dataclass(slots=True)
class DetectionResult:
    """单个检测器的结果"""
    metric_name: str
    anomalous_indices: list[int]
    reasons: dict[int, list[str]]
