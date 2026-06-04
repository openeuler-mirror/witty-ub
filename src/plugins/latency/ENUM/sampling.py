# Copyright (c) Huawei Technologies Co., Ltd. 2023-2024. All rights reserved.

from enum import Enum


class SampleMode(str, Enum):
    """采样模式枚举
    
    用于控制延迟指标时间序列数据的采样策略，以减少前端渲染压力。
    """
    NONE = "none"              # 不采样，返回全部数据
    MAX = "max"                # 时间窗口内取最大值（保留峰值特征，推荐用于性能监控）
    AVG = "avg"                # 时间窗口内取平均值（平滑波动，用于趋势分析）
    MIN = "min"                # 时间窗口内取最小值（了解最佳性能表现）
    P99 = "p99"                # 时间窗口内取 99 百分位（SLA 监控）
    P95 = "p95"                # 时间窗口内取 95 百分位（常用性能指标）
    P9999 = "p9999"            # 时间窗口内取 99.99 百分位（严格 SLA 监控）
