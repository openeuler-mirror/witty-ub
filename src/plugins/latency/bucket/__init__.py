# Copyright (c) Huawei Technologies Co., Ltd. 2023-2025. All rights reserved.
"""
latency.bucket — 分位桶统计模块（计划 latency-percentile-bucket-scale C0-C5）。

parse worker 在明细落库前，对内存中的解析结果按 10s/1min/10min/1h 四档粒度
并行计算“分位代表请求”（median/p95/p99/p9999/pmax），写入 4 张统计表。
"""
