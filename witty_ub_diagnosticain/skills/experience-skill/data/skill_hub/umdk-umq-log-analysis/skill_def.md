---
name: umdk-umq-log-analysis
description: >
  提供 UMQ 日志的端到端分析流程，包括错误码、Buffer 状态码、异步事件、统计指标和典型故障模式。
  本 Skill 用于指导运维或开发人员从 UMQ 日志中定位消息队列问题。
license: MIT
compatibility: UMDK v26.06.0_CAM
metadata:
  author: umdk-log-analysis
  version: "1.0"
  keywords: [UMDK, UMQ, 日志分析, 错误码, Buffer 状态, 异步事件, 故障排查]
allowed-tools: Bash(grep:*) Bash(awk:*) Bash(cat:*)
---

# UMQ 日志分析 Skill

## 概述

UMQ 日志包含错误码、Buffer 状态码、异步事件等多维度信息。本 Skill 提供从日志收集到根因定位的完整流程。

## 约束

- 需理解 UMQ 日志配置和日志级别。
- 部分 UMQ 错误来自底层 URMA，需要结合 URMA 日志分析。
- 异步事件需要结合时间线和端口状态分析。

## 流程

1. 确认 UMQ 日志级别和输出方式。
2. 从日志中提取错误码（`UMQ_ERR_*`）、Buffer 状态（`UMQ_BUF_*`）和事件（`UMQ_EVENT_*`）。
3. 根据错误码类型分类：参数、资源、流控、网络、队列、硬件。
4. 结合 UMQ 统计指标（`umq_stats_type_t`、`umq_err_stats_type_t`）量化问题。
5. 对底层错误，结合 URMA 日志和 `urma_admin` 输出。
6. 整理问题现象、时间线、日志片段、统计结果。

## 能力

- 输出 UMQ 常见错误码、Buffer 状态、异步事件快速映射表。
- 输出按错误类型分类的排查分支。
- 输出日志与统计结合分析的方法。
- 输出问题上报模板。

## 规则

- 出现 `UMQ_ERR_EFLOWCTL` 时，优先检查流控配置和接收端消费速度。
- 出现 `UMQ_BUF_RNR_RETRY_CNT_EXC_ERR` 时，优先检查接收端 QBuf 资源。
- 出现 `UMQ_EVENT_PORT_DOWN` / `DEV_FATAL` / `ELR_ERR` 时，优先检查硬件和链路。
- 出现 `UMQ_ERR_ENOSR` 时，优先检查 Jetty/TP 资源配额。
- 参数类错误（`UMQ_ERR_EINVAL`）优先检查应用调用参数。

## 错误分类排查

```text
UMQ_ERR_EINVAL / *_PARAM_INVALID
  └── 检查应用调用参数和 API 使用顺序

UMQ_ERR_ENOSR / *_ALLOC / QH_LIMIT
  └── 检查资源配额、队列数量、内存

UMQ_ERR_EFLOWCTL / FLOW_CONTROL_UPDATE
  └── 检查发送窗口、接收端消费速度

UMQ_BUF_ACK_TIMEOUT_ERR / UMQ_ERR_ETIMEOUT
  └── 检查链路、对端、超时配置

UMQ_EVENT_PORT_DOWN / ELR_ERR / DEV_FATAL
  └── 检查硬件、链路、固件
```

## 与统计结合

| 日志现象 | 统计指标 | 分析方向 |
|----------|----------|----------|
| 发送失败 | `POST_SEND` 错误高 | 流控或参数 |
| 接收不到 | `POLL_RX` 错误高 | QBuf 或队列错误 |
| 资源不足 | `QBUF_ALLOC` 错误高 | 内存/资源配额 |
| 流控阻塞 | `ENQUEUE_POST_TX_BATCH` 错误高 | 窗口配置 |

## 辅助命令

```bash
# 查看 UMQ 相关日志
grep "\[UMQ\]" umdk.log

# 统计错误码出现次数
grep "UMQ_ERR_" umdk.log | awk -F'UMQ_ERR_' '{print $2}' | awk '{print $1}' | sort | uniq -c
```

## 问题上报模板

- UMDK 版本、UMQ 后端类型
- 日志片段（含错误码、Buffer 状态、事件）
- `umq_stats_infos_t` 统计结果
- 复现步骤和触发条件
- 对端环境信息（如适用）
