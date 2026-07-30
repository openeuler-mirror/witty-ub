from enum import StrEnum


class DetectionMode(StrEnum):
    """检测模式枚举"""

    # 直接阈值检测：单条数据超过阈值即标记为异常
    THRESHOLD_DIRECT = "threshold_direct"
