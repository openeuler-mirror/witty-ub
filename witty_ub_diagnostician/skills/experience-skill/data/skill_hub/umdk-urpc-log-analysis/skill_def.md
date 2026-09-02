---
name: umdk-urpc-log-analysis
description: >
  提供 URPC 框架日志的端到端分析流程，包括错误码、队列事件、通道故障、CR 错误转换和统计指标。
  本 Skill 用于指导从 URPC 日志中定位框架层问题。
license: MIT
compatibility: UMDK v26.06.0_CAM
metadata:
  author: umdk-log-analysis
  version: "1.0"
  keywords: [UMDK, URPC, 日志分析, 错误码, 队列事件, 通道故障, 故障排查]
allowed-tools: Bash(grep:*) Bash(awk:*) Bash(cat:*)
---

# URPC 日志分析 Skill

## 概述

URPC 框架日志覆盖初始化、队列管理、通道管理、请求响应和异步事件。本 Skill 提供从日志到根因的系统化分析流程。

## 约束

- 需区分 URPC 框架错误和底层 URMA CR 错误。
- 队列事件通常需要重建队列才能恢复。
- 通道故障常与链路或会话状态相关。

## 流程

1. 确认 URPC 日志级别和配置。
2. 提取错误码（`URPC_ERR_*`）、事件（`URPC_ERR_EVENT_*`）和 CR 错误码。
3. 分类错误：初始化、参数、队列、通道、会话、传输、CR。
4. 结合 `urpc_stats_type_t` 统计量化问题。
5. 对底层 CR 错误，结合 URMA 日志分析。
6. 整理问题报告。

## 能力

- 输出 URPC 常见错误码和事件快速映射表。
- 输出按错误类型分类的排查分支。
- 输出日志与统计结合分析的方法。
- 输出队列重建和会话恢复建议。

## 规则

- `URPC_ERR_INIT_PART_FAIL` 优先检查 provider 加载和内核驱动。
- `URPC_ERR_EVENT_QUEUE_FAILURE` 通常需销毁重建队列。
- `URPC_ERR_EVENT_CHANNEL_FAULT` 优先检查链路和会话状态。
- `URPC_ERR_VERSION_ERR` 需要确认两端版本一致。
- `URPC_ERR_TIMEOUT` 和 CR 超时类错误需检查网络质量。

## 错误分类排查

```text
URPC_ERR_INIT_PART_FAIL
  └── 检查 provider 配置、内核驱动、固件

URPC_ERR_EVENT_QUEUE_FAILURE / QUEUE_SHUTDOWN
  └── 检查队列前置错误，必要时重建队列

URPC_ERR_EVENT_CHANNEL_FAULT / SESSION_CLOSE
  └── 检查链路、对端状态、会话生命周期

URPC_ERR_VERSION_ERR / URPC_HDR_ERR
  └── 检查两端版本、报文头完整性

URPC_ERR_CR_* / URPC_ERR_TRANSPORT_ERR
  └── 结合 URMA 日志和 urma_admin 输出分析
```

## 与 URMA 日志结合

URPC 日志中的 `URPC_ERR_TRANSPORT_ERR` 和 `URPC_ERR_CR_*` 错误，需要到 URMA 日志中查找：
- 对应 CR 状态码
- 端口事件（PORT_DOWN、ELR_ERR）
- 链路错误（ACK_TIMEOUT）

## 与统计结合

| 日志现象 | 统计指标 | 分析方向 |
|----------|----------|----------|
| 队列不可用 | 队列错误计数增加 | 队列状态损坏或资源不足 |
| 通道故障 | 通道断开计数增加 | 链路/会话问题 |
| 请求失败 | 请求/响应不匹配 | 超时、对端、队列错误 |
| 版本错误 | 版本错误计数增加 | 版本不一致 |

## 辅助命令

```bash
# 查看 URPC 错误日志
grep "URPC_ERR_" umdk.log

# 按错误码统计
grep "URPC_ERR_" umdk.log | awk -F'URPC_ERR_' '{print $2}' | awk '{print $1}' | sort | uniq -c
```

## 问题上报模板

- UMDK 版本、URPC 后端配置
- 日志片段（含错误码和事件）
- `urpc_stats_type_t` 统计结果
- 复现步骤和触发条件
- 对端版本信息（如适用）
