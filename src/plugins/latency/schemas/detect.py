from dataclasses import dataclass, field

from latency.ENUM.detect import DetectionMode


@dataclass(slots=True)
class WindowConfig:
    """窗口配置"""
    window_size: int = 500
    window_step: int = 50
    density_threshold: float = 0.5


@dataclass(slots=True)
class MetricConfig:
    """单个指标的检测配置"""
    field_name: str
    threshold_ms: float
    window_config: WindowConfig = field(default_factory=WindowConfig)
    mode: DetectionMode = DetectionMode.SLIDING_WINDOW_P99
    enabled: bool = True


@dataclass(slots=True)
class DetectionResult:
    """单个检测器的结果"""
    metric_name: str
    anomalous_indices: list[int]
    reasons: dict[int, list[str]]
