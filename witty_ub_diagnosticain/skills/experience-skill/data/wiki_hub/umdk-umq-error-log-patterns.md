---
name: "UMDK UMQ 错误日志模式"
description: "整理 UMQ 用户态常见错误码、Buffer 状态码、异步事件在日志中的典型模式、含义与排查方向。"
keywords:
  - UMDK
  - UMQ
  - 错误码
  - Buffer 状态
  - 异步事件
  - UMQ_ERR
  - UMQ_BUF
  - UMQ_EVENT
references:
  - name: "UMDK v26.06.0_CAM 源码：umq_errno.h"
    type: offline
    source: "umdk-v26.06.0_CAM/src/urpc/include/umq/umq_errno.h"
  - name: "UMDK v26.06.0_CAM 源码：umq_types.h"
    type: offline
    source: "umdk-v26.06.0_CAM/src/urpc/include/umq/umq_types.h"
  - name: "UMDK v26.06.0_CAM GitCode 仓库"
    type: online
    source: "https://gitcode.com/openeuler/umdk/tags/v26.06.0_CAM"
---

# UMDK UMQ 错误日志模式

## 概述

UMQ 错误码、Buffer 状态码和异步事件共同反映了消息队列的运行状态。理解这些日志模式有助于快速定位 UMQ 消息发送、接收、流控和队列问题。

## 错误码模式

| 错误码 | 含义 | 典型场景 |
|--------|------|----------|
| `UMQ_ERR_EPERM` | 权限不足 | 未初始化或越权操作 |
| `UMQ_ERR_EAGAIN` | 重试 | 资源临时不可用 |
| `UMQ_ERR_ENOMEM` | 内存不足 | 内存或队列资源耗尽 |
| `UMQ_ERR_EBUSY` | 资源忙 | 队列或对象被占用 |
| `UMQ_ERR_EEXIST` | 已存在 | 重复创建 |
| `UMQ_ERR_EINVAL` | 参数非法 | 入参错误 |
| `UMQ_ERR_ENODEV` | 设备不存在 | 设备未初始化 |
| `UMQ_ERR_ENOSR` | 流资源不足 | Jetty/TP 资源耗尽 |
| `UMQ_ERR_ENOBUFS` | 缓冲区不足 | 队列缓冲不足 |
| `UMQ_ERR_ETIMEOUT` | 超时 | 操作或等待超时 |
| `UMQ_ERR_ETSEG_NON_IMPORTED` | TSeg 未导入 | 远端 TSeg 未导入本地 |
| `UMQ_ERR_EFLOWCTL` | 流控错误 | 发送窗口被阻塞 |

## Buffer 状态码模式

| 状态码 | 含义 | 排查方向 |
|--------|------|----------|
| `UMQ_BUF_SUCCESS` | 成功 | 正常 |
| `UMQ_BUF_LOC_LEN_ERR` | 本地数据过长 | 检查数据长度 |
| `UMQ_BUF_LOC_ACCESS_ERR` | 本地内存访问错误 | 检查本地 MR |
| `UMQ_BUF_REM_ACCESS_ABORT_ERR` | 远端访问异常 | 检查对端 MR/状态 |
| `UMQ_BUF_ACK_TIMEOUT_ERR` | ACK 超时 | 检查链路/对端 |
| `UMQ_BUF_RNR_RETRY_CNT_EXC_ERR` | RNR 重试超限 | 接收端缓冲不足 |
| `UMQ_BUF_WR_FLUSH_ERR` | WR 被 flush | 队列处于错误状态 |
| `UMQ_BUF_WR_FLUSH_ERR_DONE` | 硬件 fake CQE | 清理资源 |
| `UMQ_BUF_LOC_DATA_POISON` | 本地数据 poison | 检查内存/数据完整性 |
| `UMQ_BUF_REM_DATA_POISON` | 远端数据 poison | 检查对端内存/数据 |
| `UMQ_BUF_FLOW_CONTROL_UPDATE` | 流控窗口更新 | 非错误，正常事件 |

## 异步事件模式

| 事件 | 含义 | 排查方向 |
|------|------|----------|
| `UMQ_EVENT_QH_ERR` | Queue Handle 错误 | 检查队列状态 |
| `UMQ_EVENT_QH_LIMIT` | Queue Handle 资源不足 | 检查资源配额 |
| `UMQ_EVENT_QH_RQ_ERR` | RQ 错误 | 检查接收队列 |
| `UMQ_EVENT_QH_RQ_LIMIT` | RQ 资源不足 | 检查 RQ 深度 |
| `UMQ_EVENT_QH_RQ_CQ_ERR` | RQ CQ 错误 | 检查完成队列 |
| `UMQ_EVENT_QH_SQ_CQ_ERR` | SQ CQ 错误 | 检查发送完成队列 |
| `UMQ_EVENT_PORT_ACTIVE` | 端口激活 | 正常事件 |
| `UMQ_EVENT_PORT_DOWN` | 端口断开 | 检查链路 |
| `UMQ_EVENT_DEV_FATAL` | 设备致命错误 | 检查硬件/固件 |
| `UMQ_EVENT_EID_CHANGE` | EID 变化 | 检查管理面配置 |
| `UMQ_EVENT_ELR_ERR` | 实体级错误 | 检查硬件/固件 |
| `UMQ_EVENT_ELR_DONE` | 实体 flush 完成 | 正常事件 |

## 典型日志模式

### 发送失败

```text
[UMQ][...]post send failed, err: UMQ_ERR_EFLOWCTL
```

排查：发送端被流控阻塞，检查接收端消费速度和窗口大小。

### 接收失败

```text
[UMQ][...]poll rx failed, status: UMQ_BUF_RNR_RETRY_CNT_EXC_ERR
```

排查：接收端没有足够 QBuf，检查 `dequeue` 速度和 QBuf 分配。

### 资源不足

```text
[UMQ][...]create umqh failed, err: UMQ_ERR_ENOSR
```

排查：Jetty/TP 资源耗尽，检查已创建队列数量和系统资源。

## 注意事项

- `UMQ_BUF_FLOW_CONTROL_UPDATE` 是正常事件，不是错误。
- `UMQ_EVENT_ELR_ERR` 通常伴随硬件/固件错误，需检查 `dmesg`。
- `UMQ_ERR_EFLOWCTL` 需要结合流控统计一起分析。
