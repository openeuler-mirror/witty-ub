from enum import StrEnum


class DetectionMode(StrEnum):
    """检测模式枚举"""
    
    # 滑动窗口百分位数检测
    SLIDING_WINDOW_P99 = "sliding_window_p99"
    SLIDING_WINDOW_P95 = "sliding_window_p95"
    SLIDING_WINDOW_P90 = "sliding_window_p90"
    
    # 直接阈值检测
    THRESHOLD_DIRECT = "threshold_direct"
    
    # 趋势异常检测
    TREND_ANOMALY = "trend_anomaly"
    
    # 速率异常检测（突发检测）
    RATE_ANOMALY = "rate_anomaly"
    
    # 统计离群值检测
    STATISTICAL_OUTLIER = "statistical_outlier"
