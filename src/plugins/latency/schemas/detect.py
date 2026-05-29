from pydantic import BaseModel, Field
from typing import Optional
from latency.ENUM.detect import DetectionMode


class WindowConfig(BaseModel):
    """窗口配置"""
    window_size: int = Field(default=500, description="窗口大小（条目数）")
    window_step: int = Field(default=50, description="窗口步长（条目数）")
    density_threshold: float = Field(default=0.5, description="区间异常密度阈值")


class MetricConfig(BaseModel):
    """单个指标的检测配置"""
    field_name: str = Field(description="指标字段名")
    threshold_ms: float = Field(description="阈值（毫秒）")
    window_config: WindowConfig = Field(default_factory=WindowConfig, description="窗口配置")
    mode: DetectionMode = Field(default=DetectionMode.SLIDING_WINDOW_P99, description="检测模式")
    enabled: bool = Field(default=True, description="是否启用")


class DetectionResult(BaseModel):
    """单个检测器的结果"""
    metric_name: str = Field(description="指标名称")
    anomalous_indices: list[int] = Field(description="异常条目索引列表")
    reasons: dict[int, list[str]] = Field(description="索引到原因列表的映射")
