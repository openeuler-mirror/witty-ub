---
name: "UMDK URPC 错误日志模式"
description: "整理 URPC 框架常见错误码、队列事件、通道故障在日志中的典型模式、含义与排查方向。"
keywords:
  - UMDK
  - URPC
  - 错误码
  - 队列事件
  - 通道故障
  - URPC_ERR
  - QUEUE_FAILURE
  - CHANNEL_FAULT
references:
  - name: "UMDK v26.06.0_CAM 源码：urpc_framework_errno.h"
    type: offline
    source: "umdk-v26.06.0_CAM/src/urpc/include/framework/urpc_framework_errno.h"
  - name: "UMDK v26.06.0_CAM 源码：urpc_framework_types.h"
    type: offline
    source: "umdk-v26.06.0_CAM/src/urpc/include/framework/urpc_framework_types.h"
  - name: "UMDK v26.06.0_CAM GitCode 仓库"
    type: online
    source: "https://gitcode.com/openeuler/umdk/tags/v26.06.0_CAM"
---

# UMDK URPC 错误日志模式

## 概述

URPC 框架错误码覆盖初始化失败、参数错误、队列错误、通道故障、CR 错误和异步事件。通过识别日志中的错误码和事件，可以快速定位 URPC 层问题。

## 框架错误码模式

| 错误码 | 含义 | 典型场景 |
|--------|------|----------|
| `URPC_ERR_TRANSPORT_ERR` | 传输层错误 | URMA 返回失败 |
| `URPC_ERR_SERVER_DROP` | 服务端丢弃 | 服务端资源或策略丢弃 |
| `URPC_ERR_SESSION_CLOSE` | 会话关闭 | 对端关闭会话 |
| `URPC_ERR_TIMEOUT` | 超时 | 请求超时 |
| `URPC_ERR_REM_LEN_ERR` | 远端长度错误 | 对端数据长度不匹配 |
| `URPC_ERR_CIPHER_ERR` | 加密错误 | 安全相关失败 |
| `URPC_ERR_FUNC_NULL` | 函数指针为空 | 未注册回调 |
| `URPC_ERR_INIT_PART_FAIL` | 部分 Provider 初始化失败 | 某些后端加载失败 |
| `URPC_ERR_LOCAL_QUEUE_ERR` | 本地队列错误 | 本地队列状态异常 |
| `URPC_ERR_REMOTE_QUEUE_ERR` | 远端队列错误 | 对端队列状态异常 |
| `URPC_ERR_VERSION_ERR` | 版本不匹配 | 两端协议版本不一致 |
| `URPC_ERR_URPC_HDR_ERR` | URPC 头错误 | 报文头损坏或解析失败 |
| `URPC_ERR_JFC_ERROR` | JFC 错误 | 完成队列错误 |
| `URPC_ERR_JETTY_ERROR` | Jetty 错误 | Jetty 不可用 |

## 通用 errno 映射

| 错误码 | 含义 |
|--------|------|
| `URPC_ERR_EPERM` | 权限不足 |
| `URPC_ERR_EAGAIN` | 重试 |
| `URPC_ERR_ENOMEM` | 内存不足 |
| `URPC_ERR_EBUSY` | 资源忙 |
| `URPC_ERR_EEXIST` | 已存在 |
| `URPC_ERR_EINVAL` | 参数非法 |

## CR 状态错误码

URPC 将 URMA CR 状态转换为错误码：

| 错误码 | 对应 URMA CR | 含义 |
|--------|--------------|------|
| `URPC_ERR_CR_LOC_LEN_ERR` | `URMA_CR_LOC_LEN_ERR` | 本地数据过长 |
| `URPC_ERR_CR_LOC_ACCESS_ERR` | `URMA_CR_LOC_ACCESS_ERR` | 本地访问错误 |
| `URPC_ERR_CR_REM_ACCESS_ABORT_ERR` | `URMA_CR_REM_ACCESS_ABORT_ERR` | 远端访问异常 |
| `URPC_ERR_CR_ACK_TIMEOUT_ERR` | `URMA_CR_ACK_TIMEOUT_ERR` | ACK 超时 |
| `URPC_ERR_CR_RNR_RETRY_CNT_EXC_ERR` | `URMA_CR_RNR_RETRY_CNT_EXC_ERR` | RNR 重试超限 |
| `URPC_ERR_CR_WR_FLUSH_ERR` | `URMA_CR_WR_FLUSH_ERR` | WR 被 flush |
| `URPC_ERR_CR_LOC_DATA_POISON` | - | 本地数据 poison |
| `URPC_ERR_CR_REM_DATA_POISON` | - | 远端数据 poison |

## 队列事件

| 事件 | 含义 | 排查方向 |
|------|------|----------|
| `URPC_ERR_EVENT_QUEUE_FAILURE` | 队列故障 | 队列状态损坏，通常需销毁重建 |
| `URPC_ERR_EVENT_QUEUE_SHUTDOWN` | 队列关闭 | 检查是否主动关闭或远端触发 |
| `URPC_ERR_EVENT_REQ_TIMEOUT` | 请求超时 | 检查网络/对端/超时配置 |
| `URPC_ERR_EVENT_CHANNEL_FAULT` | 通道故障 | 检查链路/会话/对端 |
| `URPC_ERR_EVENT_JFC_ERR` | JFC 错误 | 检查完成队列配置 |
| `URPC_ERR_EVENT_JFR_LIMIT` | JFR 资源限制 | 增加接收队列资源 |
| `URPC_ERR_EVENT_JETTY_ERR` | Jetty 错误 | Jetty 不可用 |
| `URPC_ERR_EVENT_JETTY_LIMIT` | Jetty 资源限制 | 增加 Jetty 资源 |

## 典型日志模式

### 初始化失败

```text
[URPC][...]urpc_init failed, err: URPC_ERR_INIT_PART_FAIL
```

排查：检查各 transport provider 是否正确加载，`dmesg` 中是否有驱动错误。

### 队列不可用

```text
[URPC][...]queue error: URPC_ERR_EVENT_QUEUE_FAILURE
```

排查：队列状态损坏，通常需要销毁并重建队列，检查前置错误。

### 通道故障

```text
[URPC][...]channel fault: URPC_ERR_EVENT_CHANNEL_FAULT
```

排查：检查链路状态、对端状态、会话是否被关闭。

### 版本不匹配

```text
[URPC][...]version mismatch: URPC_ERR_VERSION_ERR
```

排查：确认两端 UMDK/URPC 版本一致。

## 注意事项

- `URPC_ERR_EVENT_QUEUE_FAILURE` 通常是不可恢复错误，需重建队列。
- `URPC_ERR_TIMEOUT` 和 `URPC_ERR_CR_ACK_TIMEOUT_ERR` 都需要检查链路质量。
- 出现 `URPC_ERR_INIT_PART_FAIL` 时，应检查 provider 配置和内核驱动。
- 通道故障常与 `URPC_ERR_SESSION_CLOSE` 一起出现，需区分是主动关闭还是异常断开。
