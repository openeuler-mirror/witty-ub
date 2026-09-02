---
name: umdk-flow-control-diagnosis
description: >
  基于 UMQ 日志中的 UMQ_ERR_EFLOWCTL、UMQ_BUF_FLOW_CONTROL_UPDATE、fake buf、发送阻塞等模式，诊断 UMQ 流控问题。
  本 Skill 结合统计指标和队列状态，提供流控问题的排查流程。
license: MIT
compatibility: UMDK v26.06.0_CAM
metadata:
  author: umdk-log-analysis
  version: "1.0"
  keywords: [UMDK, UMQ, 流控, flow control, UMQ_ERR_EFLOWCTL, FLOW_CONTROL_UPDATE, 发送阻塞]
allowed-tools: Bash(grep:*) Bash(awk:*) Bash(cat:*)
---

# UMDK 流控诊断 Skill

## 概述

UMQ 使用流控机制防止发送端压垮接收端。当接收端处理速度跟不上发送速度时，会触发 `UMQ_ERR_EFLOWCTL` 或 `UMQ_BUF_FLOW_CONTROL_UPDATE` 事件。本 Skill 帮助诊断流控相关问题。

## 约束

- 流控问题通常是端到端问题，需要同时看发送端和接收端。
- 流控窗口大小影响吞吐量和延迟。
- 接收端 QBuf 不足是流控阻塞的常见原因。

## 流程

1. 从日志中提取流控相关模式（`UMQ_ERR_EFLOWCTL`、`FLOW_CONTROL_UPDATE`、`fake buf`）。
2. 查看发送端和接收端 UMQ 统计（SEND/RECEIVE/QBuf 分配）。
3. 检查接收端消费速度是否跟得上发送速度。
4. 检查流控窗口大小和配置。
5. 调整发送速率、窗口大小或接收端资源。
6. 验证修复效果。

## 能力

- 输出流控相关日志模式和含义。
- 输出发送端/接收端关键统计指标。
- 输出流控阻塞的根因分类。
- 输出流控参数调整建议。

## 规则

- `UMQ_ERR_EFLOWCTL` 优先检查接收端消费速度和窗口大小。
- `UMQ_BUF_FLOW_CONTROL_UPDATE` 是正常窗口更新事件，不是错误。
- `fake buf` 状态通常与流控或 flush 相关，需结合上下文判断。
- 流控问题不能只调窗口，需要同时提升接收端处理能力。
- 长期流控阻塞可能导致发送端超时或队列错误。

## 流控相关模式

| 模式 | 含义 | 排查方向 |
|------|------|----------|
| `UMQ_ERR_EFLOWCTL` | 流控错误，发送被阻塞 | 接收端处理速度、窗口大小 |
| `UMQ_BUF_FLOW_CONTROL_UPDATE` | 流控窗口更新 | 正常事件，观察窗口变化 |
| `fake buf` | 硬件/流控构造的 buf | 结合 flush 或窗口事件分析 |
| `UMQ_BUF_WR_FLUSH_ERR_DONE` | flush 完成 | 检查是否因流控触发 |

## 根因分类

```text
发送端被流控阻塞
  ├── 接收端消费速度太慢？
  │     └── 是 → 优化接收端处理或增加接收资源
  ├── 流控窗口太小？
  │     └── 是 → 调整窗口大小
  ├── 接收端 QBuf 不足？
  │     └── 是 → 增加 QBuf 池
  └── 发送端突发流量过大？
        └── 是 → 调整发送策略
```

## 与统计结合

| 指标 | 发送端 | 接收端 |
|------|--------|--------|
| SEND / RECEIVE | 发送消息数 | 接收消息数 |
| POST_SEND / POST_RECV | 发送失败次数 | 接收失败次数 |
| QBUF_ALLOC | 分配失败次数 | 分配失败次数 |
| ENQUEUE_POST_TX_BATCH | 批量发送失败 | - |
| DEQUEUE_SHM_QBUF | - | 共享内存 QBuf 消费 |

## 排查建议

1. 确认发送端 `SEND` 和接收端 `RECEIVE` 是否匹配。
2. 如果 `SEND` 远大于 `RECEIVE`，说明接收端处理跟不上。
3. 检查接收端 `DEQUEUE` 速度是否足够。
4. 检查 `QBUF_ALLOC` 是否在接收端持续失败。
5. 调整流控窗口时，需同时评估时延和吞吐量。

## 辅助命令

```bash
# 查看 UMQ 流控相关日志
grep "UMQ_ERR_EFLOWCTL\|FLOW_CONTROL_UPDATE\|fake buf" umdk.log

# 查看发送端统计
umq 统计接口获取 UMQ_STATS_TYPE_SEND / UMQ_STATS_TYPE_RECEIVE
```

## 问题上报模板

- 发送端和接收端日志片段
- 两端 UMQ 统计指标
- 流控窗口配置
- 接收端 QBuf 配置
- 复现步骤和触发条件
