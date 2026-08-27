---
name: "UMDK URPC 统计指标解读"
description: "介绍 URPC 框架统计类型 urpc_stats_type_t 的指标含义，以及如何结合日志分析队列、通道和性能问题。"
keywords:
  - UMDK
  - URPC
  - 统计指标
  - DFX
  - urpc_stats_type_t
  - 队列统计
references:
  - name: "UMDK v26.06.0_CAM 源码：urpc_framework_types.h"
    type: offline
    source: "umdk-v26.06.0_CAM/src/urpc/include/framework/urpc_framework_types.h"
  - name: "UMDK v26.06.0_CAM GitCode 仓库"
    type: online
    source: "https://gitcode.com/openeuler/umdk/tags/v26.06.0_CAM"
---

# UMDK URPC 统计指标解读

## 概述

URPC 框架提供 `urpc_stats_type_t` 统计类型，用于跟踪队列、请求、响应、收发等 80+ 项指标。通过统计可以量化定位队列资源、通信效率和错误分布。

## 统计类型说明

`urpc_stats_type_t` 覆盖以下维度：

| 维度 | 典型指标 | 说明 |
|------|----------|------|
| 请求/响应 | 发送请求数、接收响应数、ACK 数、READ 收发数 | 反映业务调用量 |
| 队列 | 队列创建/销毁数、队列深度使用、队列错误数 | 反映队列资源使用 |
| 通道 | 通道建立/断开数、通道错误数 | 反映连接状态 |
| 错误 | 各类错误码触发的次数 | 反映错误分布 |

## 获取方式

通过 `urpc_queue_stats_get()` 或框架提供的统计接口获取：

```c
urpc_stats_type_t stats[URPC_STATS_TYPE_MAX];
urpc_queue_stats_get(queue, stats, URPC_STATS_TYPE_MAX);
```

统计名称可通过 `urpc_queue_stats_name_get(type)` 获取。

## 与日志结合分析

| 异常 | 统计表现 | 排查方向 |
|------|----------|----------|
| 请求成功率低 | 请求数与响应数不匹配 | 检查超时、对端、队列错误 |
| 队列错误增加 | `URPC_ERR_EVENT_QUEUE_*` 相关统计增长 | 检查队列状态和日志 |
| 通道频繁断开 | 通道建立/断开次数异常 | 检查链路、会话、对端 |
| 重传/ACK 异常 | ACK 数与请求数不匹配 | 检查链路质量、丢包 |
| 资源不足 | 队列创建失败数增加 | 检查 Jetty/TP/JFC 资源 |

## 关键统计关注项

- **请求/响应计数**：用于计算成功率和吞吐量。
- **队列错误计数**：通常伴随 `URPC_ERR_EVENT_QUEUE_FAILURE` / `QUEUE_SHUTDOWN`。
- **通道故障计数**：通常伴随 `URPC_ERR_EVENT_CHANNEL_FAULT`。
- **CR 错误计数**：反映底层 URMA 传输错误。

## 使用建议

1. 先通过统计定位异常维度（请求、队列、通道、错误）。
2. 再结合日志找到具体错误码和函数位置。
3. 统计变化速率比绝对值更有意义。
4. 对于队列问题，建议同时查看队列深度和错误统计。

## 注意事项

- 统计类型在不同 URPC 版本中的枚举顺序可能变化，需按版本对应。
- 部分统计为 64 位计数器，需使用 `uint64_t` 数组接收。
- 统计接口返回的是累积值，分析时应计算采样间隔内的差值。
