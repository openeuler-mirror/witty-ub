---
name: "UMDK DLock 调试统计码解读"
description: "介绍 DLock 调试统计码 debug_stats_code_t 的 46 个指标含义，以及如何结合日志分析分布式锁竞争、内存、网络和对象问题。"
keywords:
  - UMDK
  - DLock
  - 分布式锁
  - 调试统计
  - debug_stats_code_t
  - DFX
references:
  - name: "UMDK v26.06.0_CAM 源码：dlock_types.h"
    type: offline
    source: "umdk-v26.06.0_CAM/src/ulock/dlock/lib/include/dlock_types.h"
  - name: "UMDK v26.06.0_CAM GitCode 仓库"
    type: online
    source: "https://gitcode.com/openeuler/umdk/tags/v26.06.0_CAM"
---

# UMDK DLock 调试统计码解读

## 概述

DLock 通过 `struct debug_stats` 维护 46 个调试统计码，用于量化分布式锁操作中的竞争、失败、资源、网络等事件。`debug_stats_code_t` 定义了每个统计指标的含义。

## 统计码分类

### 通用错误

| 统计码 | 含义 |
|--------|------|
| `DEBUG_STATS_EAGAIN` | 资源临时不可用 |
| `DEBUG_STATS_NO_URMA_BUF` | 无 URMA 注册缓冲区 |
| `DEBUG_STATS_ENOMEM` | 内存分配失败 |
| `DEBUG_STATS_ETIMEOUT` | 操作超时 |
| `DEBUG_STATS_FAIL` | 通用失败 |
| `DEBUG_STATS_NOT_READY` | 未就绪 |
| `DEBUG_STATS_NO_ASYNC` | 无异步结果 |
| `DEBUG_STATS_ASYNC_AGAIN` | 异步操作需重试 |

### 参数错误

| 统计码 | 含义 |
|--------|------|
| `DEBUG_STATS_EINVAL_LOCK_OP` | 锁操作类型非法 |
| `DEBUG_STATS_EINVAL_LOCK_TYPE` | 锁类型非法 |
| `DEBUG_STATS_EINVAL_LOCK_OFFSET` | 锁偏移非法 |
| `DEBUG_STATS_EINVAL_LOCK_RET` | 锁返回值非法 |
| `DEBUG_STATS_ETICKET` | ticket 非法 |
| `DEBUG_STATS_EASYNC` | 异步操作错误 |
| `DEBUG_STATS_INVALID_LOCK_STATE` | 锁状态非法（如共享模式下尝试独占） |
| `DEBUG_STATS_TICKET_TO_UNLOCK` | 获取 ticket 后未先 unlock 就释放 |

### 锁操作结果

| 统计码 | 含义 |
|--------|------|
| `DEBUG_STATS_LOCK_NOT_GET` | 锁未获取 |
| `DEBUG_STATS_ALREADY_LOCKED` | 重复加锁 |
| `DEBUG_STATS_ALREADY_UNLOCKED` | 重复解锁 |
| `DEBUG_STATS_ATOMIC_TRYLOCK_FAIL` | 原子锁尝试加锁失败 |
| `DEBUG_STATS_ATOMIC_UNLOCK_FAIL` | 原子锁解锁失败 |
| `DEBUG_STATS_ATOMIC_EXTEND_FAIL` | 原子锁续约失败 |
| `DEBUG_STATS_RW_TRYLOCK_EX_FAIL` | 读写锁独占加锁失败 |
| `DEBUG_STATS_RW_UNLOCK_EX_FAIL` | 读写锁独占解锁失败 |
| `DEBUG_STATS_RW_TRYLOCK_SH_FAIL` | 读写锁共享加锁失败 |
| `DEBUG_STATS_RW_UNLOCK_SH_FAIL` | 读写锁共享解锁失败 |
| `DEBUG_STATS_FAIR_QUEUE_LIMIT` | 公平锁队列达到限制 |
| `DEBUG_STATS_FAIR_UNLOCK_EX_FAIL` | 公平锁独占解锁失败 |
| `DEBUG_STATS_FAIR_UNLOCK_SH_FAIL` | 公平锁共享解锁失败 |
| `DEBUG_STATS_FAIR_EX_TICKET_PASSED` | 公平锁独占 ticket 已过期 |
| `DEBUG_STATS_FAIR_SH_TICKET_PASSED` | 公平锁共享 ticket 已过期 |

### 网络与通信

| 统计码 | 含义 |
|--------|------|
| `DEBUG_STATS_NETWORK_FAIL` | post_send 或 post_recv 失败 |
| `DEBUG_STATS_SEND_FAIL` | 服务端 post_send 失败 |
| `DEBUG_STATS_BAD_RESPONSE` | 响应异常 |
| `DEBUG_STATS_CLIENT_DISCONNECT` | 客户端异常断开 |
| `DEBUG_STATS_REPLICA_INIT_FAIL` | 副本初始化失败 |

### 安全与对象

| 统计码 | 含义 |
|--------|------|
| `DEBUG_STATS_ENCRYPT_FAIL` | 加密失败 |
| `DEBUG_STATS_DECRYPT_FAIL` | 解密失败 |
| `DEBUG_STATS_CLIENT_ID_VERIFY_FAIL` | 客户端 ID 校验失败 |
| `DEBUG_STATS_BAD_REQUEST` | 请求异常 |
| `DEBUG_STATS_OBJECT_NOT_GET` | 对象未获取 |
| `DEBUG_STATS_OBJECT_CAS_FAILED` | 对象 CAS 失败 |

### 初始化状态

| 统计码 | 含义 |
|--------|------|
| `DEBUG_STATS_CLIENT_NOT_INIT` | 客户端未初始化 |
| `DEBUG_STATS_CLIENTMGR_NOT_INIT` | 客户端管理器未初始化 |
| `DEBUG_STATS_SERVER_NOT_INIT` | 服务端未初始化 |

## 使用方式

`struct debug_stats` 包含 `uint64_t stats[DEBUG_STATS_MAX]` 数组，通过下标访问：

```c
struct debug_stats *stats = ...;
printf("atomic trylock fail: %lu\n", stats->stats[DEBUG_STATS_ATOMIC_TRYLOCK_FAIL]);
```

## 与日志结合分析

| 日志现象 | 相关统计码 | 分析方向 |
|----------|------------|----------|
| 加锁失败 | `DEBUG_STATS_ATOMIC_TRYLOCK_FAIL` / `DEBUG_STATS_RW_TRYLOCK_EX_FAIL` | 锁竞争或超时 |
| 公平锁排队失败 | `DEBUG_STATS_FAIR_QUEUE_LIMIT` | 队列限制或锁持有时间过长 |
| 通信失败 | `DEBUG_STATS_NETWORK_FAIL` / `DEBUG_STATS_SEND_FAIL` | URMA 链路问题 |
| 客户端断开 | `DEBUG_STATS_CLIENT_DISCONNECT` | 客户端异常或超时 |
| 对象 CAS 失败 | `DEBUG_STATS_OBJECT_CAS_FAILED` | 并发冲突 |
| 内存不足 | `DEBUG_STATS_ENOMEM` | 系统内存或资源泄漏 |

## 注意事项

- 统计是累积值，分析时应计算采样间隔内的差值。
- 锁竞争类统计高不一定异常，需结合业务并发模型判断。
- 网络类统计增加时，必须同时检查 URMA 日志。
- 安全类统计失败时，检查 SSL/TLS 配置和证书。
