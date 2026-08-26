---
name: "UMDK DLock 日志格式说明"
description: "介绍 DLock 分布式锁日志的字段格式、日志级别、与 URMA 日志的关系、默认输出路径和配置方式。"
keywords:
  - UMDK
  - DLock
  - 分布式锁
  - 日志格式
  - 日志级别
  - dlock_log
  - URMA 日志
references:
  - name: "UMDK v26.06.0_CAM 源码：dlock_log.h"
    type: offline
    source: "umdk-v26.06.0_CAM/src/ulock/dlock/lib/include/dlock_log.h"
  - name: "UMDK v26.06.0_CAM 源码：dlock_types.h"
    type: offline
    source: "umdk-v26.06.0_CAM/src/ulock/dlock/lib/include/dlock_types.h"
  - name: "UMDK v26.06.0_CAM GitCode 仓库"
    type: online
    source: "https://gitcode.com/openeuler/umdk/tags/v26.06.0_CAM"
---

# UMDK DLock 日志格式说明

## 概述

DLock 是 UMDK 提供的分布式锁组件，其日志复用 URMA 日志基础设施。DLock 日志默认通过 `syslog()` 输出，并可通过 URMA 日志回调接管。

## 日志宏

DLock 提供四级日志宏：

```c
DLOCK_LOG_DEBUG(format, ...)
DLOCK_LOG_INFO(format, ...)
DLOCK_LOG_WARN(format, ...)
DLOCK_LOG_ERR(format, ...)
```

## 日志输出流程

`DLOCK_LOG` 宏会执行两次输出：
1. 调用 `dlock_log()` 函数，使用 `syslog()` 输出 DLock 格式日志。
2. 如果当前日志级别不被 URMA 日志丢弃，还会调用 `urma_log()` 输出，复用 URMA 日志格式。

因此，DLock 日志可能同时出现在 DLock 的 syslog 输出和 URMA 的 syslog 输出中。

## 日志级别

| 宏 | 对应 syslog 级别 | 含义 |
|----|----------------|------ |
| `DLOCK_LOG_DEBUG` | `LOG_DEBUG` | 调试信息 |
| `DLOCK_LOG_INFO` | `LOG_INFO` | 信息（默认） |
| `DLOCK_LOG_WARN` | `LOG_WARNING` | 警告 |
| `DLOCK_LOG_ERR` | `LOG_ERR` | 错误 |

日志级别可通过 `dlock_set_log_level(int log_level)` 设置，其内部映射到 URMA 日志级别。

## 默认格式

DLock 日志默认格式包含函数名和行号：

```c
void dlock_log(const char *func, int line, int priority, const char *format, ...)
```

典型输出可能包含：
- 日志级别
- 函数名
- 行号
- 日志正文

通过 URMA 二次输出时，会包含 URMA 标准字段：`[URMA][liburma][thread_id=...][...]`。

## 默认落盘路径

- DLock 直接输出通过 `syslog()` 到系统日志，常见路径为 `/var/log/messages` 或 `/var/log/syslog`。
- 若被 URMA 日志系统接管，则遵循 URMA 日志落盘路径。
- 产品环境可通过 `/etc/rsyslog.d/dlock.conf` 重定向到独立文件。

## 配置方式

### 编程接口

```c
void dlock_set_log_level(int log_level);
```

### 环境变量

由于 DLock 复用 URMA 日志，设置 `URMA_LOG_LEVEL` 环境变量也会影响 DLock 通过 URMA 输出的日志级别。

```bash
export URMA_LOG_LEVEL=debug
```

### 自定义日志回调

通过 URMA 的 `urma_register_log_func()` 注册回调，可将 DLock 二次输出日志导入自有日志框架。

## 日志收集配置示例

```conf
# /etc/rsyslog.d/dlock.conf
:msg, contains, "[DLOCK]" /var/log/umdk/dlock.log
:msg, contains, "[DLOCK]" ~
```

或收集 URMA 日志时同时收集 DLock 二次输出：

```conf
:msg, contains, "[URMA]" /var/log/umdk/urma.log
```

## 注意事项

- DLock 日志同时包含 DLock 自身格式和 URMA 格式，分析时需注意区分来源。
- `DLOCK_LOG_ERR` 级日志通常需要优先关注。
- 如果 DLock 日志未出现，需确认 `URMA_LOG_LEVEL` 和 DLock 自身日志级别设置。
- 多线程场景下，DLock 日志中的线程 ID 对定位问题很有帮助。
