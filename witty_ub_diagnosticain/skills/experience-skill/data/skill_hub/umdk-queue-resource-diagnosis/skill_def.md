---
name: umdk-queue-resource-diagnosis
description: >
  基于 UMQ/URPC 日志中的 ENOSR、ENOMEM、EBUSY、QH_LIMIT、JETTY_LIMIT、JFR_LIMIT 等模式，诊断队列、TP、Jetty、JFC/JFR 资源不足问题。
  本 Skill 结合统计指标和管理工具输出，提供资源类问题的排查流程。
license: MIT
compatibility: UMDK v26.06.0_CAM
metadata:
  author: umdk-log-analysis
  version: "1.0"
  keywords: [UMDK, UMQ, URPC, 队列资源, ENOSR, ENOMEM, QH_LIMIT, JETTY_LIMIT, 资源不足]
allowed-tools: Bash(grep:*) Bash(awk:*) Bash(cat:*) Bash(urma_admin:*)
---

# UMDK 队列资源诊断 Skill

## 概述

UMDK 中 Jetty、TP、JFC、JFR、QH 等资源都有配额限制。当创建队列或资源失败时，日志中会出现 `ENOSR`、`ENOMEM`、`EBUSY` 或 `*_LIMIT` 类事件。本 Skill 提供资源不足问题的诊断流程。

## 约束

- 资源配额通常受硬件、固件和系统配置限制。
- 不同 UMDK 后端（UDMA/UB）可能有不同资源上限。
- 资源泄漏会导致可用资源逐渐减少。

## 流程

1. 从日志中提取资源不足相关错误（`ENOSR`、`ENOMEM`、`EBUSY`、`*_LIMIT`）。
2. 使用 `urma_admin` 查看当前设备、端口、TP、Jetty 使用情况。
3. 统计资源创建/销毁数量，确认是否存在泄漏。
4. 检查资源配置是否合理（队列深度、关联数量）。
5. 调整资源配额或释放未使用资源。
6. 验证修复效果。

## 能力

- 输出 UMDK 中常见资源类型和限制来源。
- 输出资源不足日志模式及排查方向。
- 输出 `urma_admin` 相关查询命令。
- 输出资源泄漏检测方法。

## 规则

- `UMQ_ERR_ENOSR` / `URPC_ERR_ENOSR` 优先检查 Jetty/TP 资源配额。
- `*_LIMIT` 事件说明该资源类型已触发上限，需增加配额或减少使用。
- `EBUSY` 可能由资源被占用或并发冲突导致，不一定是配额不足。
- `ENOMEM` 需区分系统内存不足和 UMDK 内部资源池耗尽。
- 资源泄漏排查应关注是否有对象被创建但未销毁。

## 资源类型与日志模式

| 资源 | 日志关键词 | 排查工具/命令 |
|------|----------|---------------|
| Jetty | `JETTY_LIMIT`、`JETTY_ERROR` | `urma_admin jetty show` |
| JFS | `JFS_LIMIT` | `urma_admin jfs show` |
| JFC | `JFC_ERROR`、`JFC_LIMIT` | `urma_admin jfc show` |
| JFR | `JFR_LIMIT` | `urma_admin jfr show` |
| TP | `TP` 相关 | `urma_admin tp show` |
| QH | `QH_LIMIT`、`QH_RQ_LIMIT` | UMQ 统计 |

## 排查分支

```text
资源创建失败
  ├── 是否达到硬件/固件上限？
  │     └── 是 → 增加配额或减少使用
  ├── 是否存在资源泄漏？
  │     └── 是 → 修复未释放资源
  ├── 队列深度/关联数配置是否合理？
  │     └── 否 → 按推荐公式配置
  └── 系统内存是否不足？
        └── 是 → 释放内存或扩容
```

## 推荐配置

URMA API Guide 推荐 JFC 队列深度：

```text
JFC 队列深度 >= 关联 jetty 的队列深度总和 / 每多少个 WR 生成一个 CR + 关联 jetty 数
```

## 与统计结合

| 日志 | 统计 | 方向 |
|------|------|------|
| QH_LIMIT | UMQ 队列错误统计 | 增加 QH 配额或减少队列数 |
| JETTY_LIMIT | urpc_stats 中 Jetty 相关统计 | 增加 Jetty 配额或减少使用 |
| ENOSR | 创建失败计数 | 检查资源池配置 |

## 辅助命令

```bash
urma_admin jetty show
urma_admin jfs show
urma_admin jfc show
urma_admin tp show
```

## 问题上报模板

- 资源类型和错误日志
- `urma_admin` 相关输出
- 资源创建/销毁统计
- 当前资源配置和系统内存情况
- 复现步骤
