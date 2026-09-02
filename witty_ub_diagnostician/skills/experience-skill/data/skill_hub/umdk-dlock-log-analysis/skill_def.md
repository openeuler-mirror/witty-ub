---
name: umdk-dlock-log-analysis
description: >
  提供 DLock 分布式锁日志的端到端分析流程，包括状态码、调试统计码、典型错误日志和根因排查。
  本 Skill 用于指导从 DLock 日志中定位服务端、客户端、加解锁和对象操作问题。
license: MIT
compatibility: UMDK v26.06.0_CAM
metadata:
  author: umdk-log-analysis
  version: "1.0"
  keywords: [UMDK, DLock, 分布式锁, 日志分析, 状态码, 调试统计, 故障排查]
allowed-tools: Bash(grep:*) Bash(awk:*) Bash(cat:*)
---

# DLock 日志分析 Skill

## 概述

DLock 分布式锁日志涉及服务端、客户端、网络通信、加解锁和对象操作。本 Skill 提供系统化的日志分析流程。

## 约束

- DLock 日志复用 URMA 日志，部分日志可能以 URMA 格式输出。
- 服务端和客户端日志需要结合分析。
- 部分错误来自底层 URMA 通信，需结合 URMA 日志。

## 流程

1. 确认 DLock 日志级别和输出方式。
2. 从日志中提取状态码（`dlock_status_t`）和调试统计码（`debug_stats_code_t`）。
3. 根据错误类型分类：初始化、参数、加解锁、内存、网络、对象、副本。
4. 结合服务端和客户端日志交叉验证。
5. 对网络相关错误，结合 URMA 日志和 `urma_admin`。
6. 整理问题报告。

## 能力

- 输出 DLock 常见状态码和调试统计码快速映射表。
- 输出按错误类型分类的排查分支。
- 输出服务端/客户端日志对比分析方法。
- 输出问题上报模板。

## 规则

- `DLOCK_SERVER_NOT_INIT` / `server init failed` 优先检查服务端配置和设备状态。
- `DLOCK_CLIENT_NOT_INIT` 优先检查客户端初始化顺序。
- `DLOCK_LOCK_NOT_GET` / `trylock fail` 优先检查锁竞争和超时配置。
- `DLOCK_ENOMEM` / `no memory left` 优先检查系统内存和资源泄漏。
- `xchg_control_msg send error` / `post_send failed` 优先检查 URMA 链路。
- 对象 CAS 失败优先检查并发冲突和对象生命周期。

## 错误分类排查

```text
server init failed
  └── 检查配置、设备、端口、SSL 证书、副本配置

client not init
  └── 检查客户端初始化顺序和参数

trylock fail / LOCK_NOT_GET
  └── 检查锁竞争、公平锁队列、超时、网络

no memory left / ENOMEM
  └── 检查系统内存、DLock 资源数量、泄漏

post_send / xchg_control_msg 失败
  └── 检查 URMA 链路、Jetty 状态、对端状态

object CAS failed / OBJECT_NOT_GET
  └── 检查对象生命周期、并发、所有者
```

## 与统计结合

| 日志现象 | 统计码 | 方向 |
|----------|--------|------|
| 加锁竞争激烈 | `DEBUG_STATS_ATOMIC_TRYLOCK_FAIL` 高 | 锁竞争或超时太短 |
| 网络失败 | `DEBUG_STATS_NETWORK_FAIL` 高 | 检查 URMA 链路 |
| 客户端断开 | `DEBUG_STATS_CLIENT_DISCONNECT` 高 | 检查客户端异常或超时 |
| 公平锁队列满 | `DEBUG_STATS_FAIR_QUEUE_LIMIT` 高 | 增加队列限制或优化加锁策略 |
| 内存不足 | `DEBUG_STATS_ENOMEM` 高 | 检查内存和资源泄漏 |

## 辅助命令

```bash
# 查看 DLock 错误日志
grep "DLOCK_LOG_ERR\|DLOCK_LOG_WARN" umdk.log

# 查看 DLock 状态码
grep "DLOCK_" umdk.log | awk -F'DLOCK_' '{print $2}' | awk '{print $1}' | sort | uniq -c
```

## 问题上报模板

- DLock 版本、服务端/客户端部署方式
- 服务端和客户端日志片段
- 调试统计码结果
- 复现步骤和触发条件
- 底层 URMA 日志（如适用）
