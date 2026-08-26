---
name: "UMDK DLock 错误日志模式"
description: "整理 DLock 常见状态码、调试统计码和典型错误日志模式，包括服务端/客户端初始化、加解锁、内存、网络和对象操作错误。"
keywords:
  - UMDK
  - DLock
  - 分布式锁
  - 错误码
  - dlock_status_t
  - debug_stats_code_t
  - 日志模式
references:
  - name: "UMDK v26.06.0_CAM 源码：dlock_types.h"
    type: offline
    source: "umdk-v26.06.0_CAM/src/ulock/dlock/lib/include/dlock_types.h"
  - name: "UMDK v26.06.0_CAM 源码：dlock_server.cpp"
    type: offline
    source: "umdk-v26.06.0_CAM/src/ulock/dlock/lib/server/dlock_server.cpp"
  - name: "UMDK v26.06.0_CAM GitCode 仓库"
    type: online
    source: "https://gitcode.com/openeuler/umdk/tags/v26.06.0_CAM"
---

# UMDK DLock 错误日志模式

## 概述

DLock 错误日志主要分布在服务端、客户端、Jetty 管理、加解锁和对象操作路径。通过识别状态码和日志关键词，可快速定位问题类型。

## 状态码

| 状态码 | 含义 | 典型场景 |
|--------|------|----------|
| `DLOCK_SUCCESS` | 成功 | 操作完成 |
| `DLOCK_EAGAIN` | 资源临时不可用 | 可重试 |
| `DLOCK_ENOMEM` | 内存分配失败 | 系统内存不足 |
| `DLOCK_ETIMEOUT` | 操作超时 | 网络或对端超时 |
| `DLOCK_EINVAL` | 参数非法 | 入参错误 |
| `DLOCK_CLIENT_NOT_INIT` | 客户端未初始化 | 调用顺序错误 |
| `DLOCK_LOCK_NOT_GET` | 锁未获取 | 加锁失败 |
| `DLOCK_ALREADY_LOCKED` | 已加锁 | 重复加锁 |
| `DLOCK_ALREADY_UNLOCKED` | 已解锁 | 重复解锁 |
| `DLOCK_BAD_RESPONSE` | 响应异常 | 服务端/网络问题 |
| `DLOCK_SERVER_NOT_INIT` | 服务端未初始化 | 服务端启动失败 |
| `DLOCK_SERVER_NO_RESOURCE` | 服务端资源不足 | 服务端资源耗尽 |
| `DLOCK_OBJECT_NOT_GET` | 对象未获取 | 对象操作失败 |
| `DLOCK_OBJECT_CAS_FAILED` | 对象 CAS 失败 | 并发冲突 |

## 调试统计码

| 统计码 | 含义 |
|--------|------|
| `DEBUG_STATS_EAGAIN` | 资源临时不可用 |
| `DEBUG_STATS_NO_URMA_BUF` | 无 URMA 注册缓冲区 |
| `DEBUG_STATS_ENOMEM` | 内存分配失败 |
| `DEBUG_STATS_ETIMEOUT` | 操作超时 |
| `DEBUG_STATS_ATOMIC_TRYLOCK_FAIL` | 原子锁尝试加锁失败 |
| `DEBUG_STATS_RW_TRYLOCK_EX_FAIL` | 读写锁独占加锁失败 |
| `DEBUG_STATS_FAIR_QUEUE_LIMIT` | 公平锁队列达到限制 |
| `DEBUG_STATS_NETWORK_FAIL` | post_send/post_recv 失败 |
| `DEBUG_STATS_CLIENT_DISCONNECT` | 客户端异常断开 |
| `DEBUG_STATS_REPLICA_INIT_FAIL` | 副本初始化失败 |
| `DEBUG_STATS_ENCRYPT_FAIL` | 加密失败 |
| `DEBUG_STATS_DECRYPT_FAIL` | 解密失败 |
| `DEBUG_STATS_CLIENT_ID_VERIFY_FAIL` | 客户端 ID 校验失败 |

## 典型错误日志模式

### 服务端初始化失败

```text
[DLOCK][...]server init failed, ret: <status>
```

排查：检查配置参数、设备状态、端口配置、SSL 证书等。

### 客户端未初始化

```text
[DLOCK][...]client not init
```

排查：检查 DLock 客户端初始化顺序，确认 `init` 是否成功。

### 锁获取失败

```text
[DLOCK][...]trylock fail, ret: DLOCK_LOCK_NOT_GET
```

排查：锁已被占用、公平锁排队、参数错误、网络超时。

### 内存不足

```text
[DLOCK][...]no memory left
[DLOCK][...]malloc error (errno=...)
```

排查：检查系统内存、DLock 资源数量、是否有资源泄漏。

### 网络失败

```text
[DLOCK][...]xchg_control_msg, send error (errno=...)
[DLOCK][...]post_send failed
```

排查：检查 URMA 链路、对端状态、Jetty 状态。

### 对象操作失败

```text
[DLOCK][...]object CAS failed
[DLOCK][...]object not get
```

排查：检查对象是否已创建、所有者是否匹配、并发冲突。

### 票据过期

```text
[DLOCK][...]DLOCK_TICKET_TO_UNLOCK
```

排查：获取 ticket 后未释放，需要先 unlock 再释放。

## 注意事项

- `DLOCK_EAGAIN` 在加锁场景可能是正常竞争失败，可重试。
- `DLOCK_ETIMEOUT` 需要结合网络日志和 URMA 事件分析。
- `DEBUG_STATS_NETWORK_FAIL` 增加时，优先检查底层 URMA 通信。
- 服务端和客户端日志应结合分析，单端日志可能无法定位根因。
