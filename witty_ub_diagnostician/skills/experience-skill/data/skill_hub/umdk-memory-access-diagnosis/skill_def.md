---
name: umdk-memory-access-diagnosis
description: >
  基于 URMA 日志中的 LOC_ACCESS_ERR、REM_ACCESS_ABORT_ERR、data poison、WR_FLUSH_ERR 等模式，诊断内存注册、权限和访问问题。
  本 Skill 帮助用户定位本地内存访问错误、远端内存访问异常和 Segment 权限问题。
license: MIT
compatibility: UMDK v26.06.0_CAM
metadata:
  author: umdk-log-analysis
  version: "1.0"
  keywords: [UMDK, URMA, 内存访问, LOC_ACCESS, REM_ACCESS, data poison, WR_FLUSH, 内存注册]
allowed-tools: Bash(grep:*) Bash(awk:*) Bash(cat:*)
---

# URMA 内存访问故障诊断 Skill

## 概述

URMA 完成记录（CR）中的 `LOC_ACCESS_ERR`、`REM_ACCESS_ABORT_ERR` 等状态码，以及日志中的 `data poison` 等模式，通常与内存注册、访问权限、地址越界或远端内存异常有关。

## 约束

- 需结合 CR 状态码和日志中的函数位置进行分析。
- 本地访问错误通常与 MR（Memory Region）注册、地址、长度、权限有关。
- 远端访问错误通常与对端 MR 权限、地址、状态或网络传输异常有关。

## 流程

1. 从日志或 CR 中提取状态码：`LOC_ACCESS_ERR`、`REM_ACCESS_ABORT_ERR`、`LOC_LEN_ERR` 等。
2. 确定出错的 WR 操作类型（Send/Write/Read/Atomic）。
3. 检查本地 MR 注册参数（地址、长度、权限、页面对齐）。
4. 如果是远端访问错误，检查对端 MR 权限和状态。
5. 检查是否有 `data poison` 或 `WR_FLUSH_ERR` 等异常事件。
6. 复现并验证修复。

## 能力

- 输出 URMA CR 中内存访问相关状态码的含义。
- 输出本地和远端内存访问错误的排查分支。
- 输出 MR 注册检查清单。
- 输出与 UMQ/URPC Buffer 状态的关联分析。

## 规则

- `URMA_CR_LOC_ACCESS_ERR` 优先检查本地 MR 地址、长度、权限。
- `URMA_CR_REM_ACCESS_ABORT_ERR` 优先检查对端 MR 和链路状态。
- `URMA_CR_LOC_LEN_ERR` 优先检查 WR 的本地数据长度是否超过限制。
- 出现 `WR_FLUSH_ERR` 时，说明 Jetty/JFS 已处于错误状态，需检查前置错误。
- `data poison` 相关日志需检查内存是否被污染或 DMA 传输异常。

## 状态码映射

| 状态码 | 含义 | 排查重点 |
|--------|------|----------|
| `URMA_CR_LOC_LEN_ERR` | 本地数据长度过长 | WR 长度、协议限制 |
| `URMA_CR_LOC_ACCESS_ERR` | 本地内存访问错误 | MR 地址、长度、权限 |
| `URMA_CR_REM_ACCESS_ABORT_ERR` | 远端内存访问异常 | 对端 MR、对端状态 |
| `URMA_CR_WR_FLUSH_ERR` | WR 被 flush，Jetty 处于错误状态 | 前置错误、Jetty 状态 |
| `URMA_CR_WR_FLUSH_ERR_DONE` | 硬件构造 fake CQE | 需要清理资源，user_ctx 无效 |

## 排查分支

### 本地访问错误

```text
URMA_CR_LOC_ACCESS_ERR
  ├── MR 地址是否有效？
  │     └── 否 → 检查内存注册地址和生命周期
  ├── 访问长度是否超出 MR 范围？
  │     └── 是 → 调整 WR 长度或重新注册 MR
  ├── MR 权限是否匹配操作？
  │     └── 否 → 检查注册权限（本地写/远端读/远端写等）
  └── 页面对齐/注册方式是否有问题？
        └── 是 → 检查页面对齐和注册标志
```

### 远端访问错误

```text
URMA_CR_REM_ACCESS_ABORT_ERR
  ├── 对端 MR 是否有效？
  │     └── 否 → 检查对端内存注册和生命周期
  ├── 对端 MR 权限是否允许该操作？
  │     └── 否 → 检查对端 MR 权限
  ├── 对端是否出现 WR_FLUSH_ERR/PORT_DOWN？
  │     └── 是 → 检查对端日志和状态
  └── 链路是否异常？
        └── 是 → 按链路故障诊断处理
```

## 关联分析

UMQ 中对应的 Buffer 状态：

| UMQ Buffer 状态 | 对应 URMA CR | 含义 |
|-----------------|--------------|------|
| `UMQ_BUF_LOC_ACCESS_ERR` | `URMA_CR_LOC_ACCESS_ERR` | 本地内存访问错误 |
| `UMQ_BUF_REM_ACCESS_ABORT_ERR` | `URMA_CR_REM_ACCESS_ABORT_ERR` | 远端内存访问异常 |

## 辅助检查清单

- [ ] 本地 MR 地址、长度、权限是否正确
- [ ] 远端 MR 地址、长度、权限是否正确
- [ ] WR 操作类型与 MR 权限是否匹配
- [ ] 访问长度是否超出 MR 或协议限制
- [ ] 对端状态是否正常（是否有 WR_FLUSH、PORT_DOWN）
- [ ] 内存是否被其他线程释放或修改
- [ ] 页面对齐和注册标志是否正确

## 问题上报关键信息

- 完整 CR 状态码和日志片段
- 出错 WR 的操作类型和参数
- 本地 MR 注册参数（地址、长度、权限）
- 对端 MR 注册参数（如可获取）
- 是否有前置错误（如 WR_FLUSH、PORT_DOWN）
