---
name: umdk-urma-cr-log-analysis
description: >
  专门用于分析 URMA 用户态 CR（Converged Resource）相关操作的日志，包括状态码含义、CR 创建/销毁/配置错误模式和根因排查。
  本 Skill 帮助用户从 URMA 日志中快速理解 CR 相关失败。
license: MIT
compatibility: UMDK v26.06.0_CAM
metadata:
  author: umdk-log-analysis
  version: "1.0"
  keywords: [UMDK, URMA, CR, 融合资源, 状态码, 日志分析, 故障排查]
allowed-tools: Bash(grep:*) Bash(awk:*) Bash(cat:*)
---

# URMA CR 日志分析 Skill

## 概述

CR（Converged Resource）是 URMA 中的重要资源抽象。CR 创建、销毁、配置和查询失败时，日志通常会输出 `urma_status_t` 状态码或失败描述。本 Skill 帮助从日志中快速定位 CR 相关问题。

## 约束

- 以 `urma_status_t` 枚举和 `urma_types.h` 中的状态码定义为依据。
- 需结合 URMA 通用日志格式规范解析字段。
- 部分 CR 错误可能来自底层 URPC 与内核驱动的交互。

## 流程

1. 过滤包含 `urma_create_cr`、`urma_destroy_cr`、`urma_cr_set_cfg`、`urma_cr_query` 等关键字的日志。
2. 提取状态码或 `failed to` 描述。
3. 根据状态码映射表判断问题类型（参数、资源、驱动、网络、权限）。
4. 检查 CR 属性（`tp`、`flag`、配置属性）是否合法。
5. 结合内核日志确认是否由底层驱动返回失败。
6. 整理 CR 操作的时间线和状态码变化。

## 能力

- 输出 `urma_status_t` 常见状态码快速映射表。
- 输出 CR 创建/销毁/配置错误的排查方向。
- 输出从日志中提取状态码和函数位置的方法。
- 输出 CR 问题上报时需要包含的关键信息。

## 规则

- `URMA_EINVAL` 优先检查 `cr_attr` 字段和传入参数。
- `URMA_ENODEV` 优先检查内核驱动是否加载、设备节点是否存在。
- `URMA_ENOMEM` 优先检查系统内存和 CR 数量是否过多。
- `URMA_ETIMEDOUT` 优先检查网络连通性和对端状态。
- 如果日志中出现 `udriver return fail`，必须同时检查 `dmesg` 中的内核日志。

## 状态码映射

| 状态码 | 含义 | 排查重点 |
|--------|------|----------|
| `URMA_EINVAL` | 参数非法 | cr_attr、flag、tp 等字段 |
| `URMA_ENOMEM` | 内存不足 | 系统内存、CR 数量 |
| `URMA_ENODEV` | 设备不存在 | 驱动加载、设备节点 |
| `URMA_ENOENT` | 资源未找到 | 句柄是否有效、是否已销毁 |
| `URMA_EBUSY` | 资源忙 | 并发访问、重复操作 |
| `URMA_ETIMEDOUT` | 超时 | 网络、对端、超时配置 |
| `URMA_EPERM` | 权限不足 | 用户权限、设备访问权限 |
| `URMA_EIO` | IO 错误 | 硬件/驱动通信 |
| `URMA_ENOSPC` | 空间不足 | 资源表、队列深度 |
| `URMA_EUNREACH` | 不可达 | 网络/对端 |

## 典型日志模式

```text
[URMA][liburma][thread_id=...][...][urma_create_cr[Line=...]]failed to create cr, ret: URMA_EINVAL
```

**排查：** 检查 `cr_attr` 参数。

```text
[URMA][liburma][thread_id=...][...][...]udriver return fail, status: -N
```

**排查：** 查看 `dmesg` 中对应时间点的内核错误。

```text
[URMA][liburma][thread_id=...][...][urma_destroy_cr]failed to find cr handle
```

**排查：** 检查是否重复销毁或使用了错误句柄。

## 问题上报关键信息

- UMDK 版本号
- 调用 CR 操作的 API 名称和参数
- 完整日志片段（包含状态码和函数名）
- `dmesg` 中对应时间的内核日志
- 是否可稳定复现
