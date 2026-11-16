# Copyright (c) Huawei Technologies Co., Ltd. 2023-2025. All rights reserved.
"""
latency.bucket — 分位桶统计模块（计划 latency-percentile-bucket-scale C0-C5）。

parse worker 在明细落库前，对内存中的解析结果按 10s/1min/10min/1h 四档粒度
并行计算桶内统计（avg/p99/p9999/pmax）及阶段分解代表请求，写入统计表。
"""
