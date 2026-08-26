---
name: "UMDK URMA 日志格式说明"
description: "介绍 URMA 用户态日志的字段格式、日志级别、环境变量、日志接管回调与默认输出路径，用于日志解析与故障排查。"
keywords:
  - UMDK
  - URMA
  - 日志格式
  - liburma
  - syslog
  - 日志级别
  - URMA_LOG_LEVEL
references:
  - name: "UMDK v26.06.0_CAM 源码：urma_log.c"
    type: offline
    source: "umdk-v26.06.0_CAM/src/urma/lib/urma/core/urma_log.c"
  - name: "UMDK v26.06.0_CAM 源码：urma_log.h"
    type: offline
    source: "umdk-v26.06.0_CAM/src/urma/lib/urma/core/include/urma_log.h"
  - name: "UMDK v26.06.0_CAM 文档：URMA User Guide 6.5.1"
    type: offline
    source: "umdk-v26.06.0_CAM/doc/ch/urma/URMA User Guide.ch.md"
  - name: "UMDK v26.06.0_CAM GitCode 仓库"
    type: online
    source: "https://gitcode.com/openeuler/umdk/tags/v26.06.0_CAM"
---

# UMDK URMA 日志格式说明

## 概述

URMA 用户态日志默认通过 Linux `syslog()` 输出，由系统 rsyslog 接管。应用可以通过 `urma_register_log_func()` 注册自定义回调，将日志重定向到自有框架中。

## 默认日志格式

URMA 日志默认包含以下字段（字段分隔符默认为 `|`）：

```text
[URMA][liburma][thread_id=<tid>][<thread_tag>][<function>[Line=<line>]]<message>
```

如果使用带文件位置的宏（如 `URMA_LOG_LOC_*`），格式为：

```text
[URMA][liburma][thread_id=<tid>][<thread_tag>][<file>:<function>:<line>]<message>
```

### 字段说明

| 字段 | 示例 | 含义 |
|------|------|------|
| `URMA` | `URMA` | 固定组件标签 |
| `liburma` | `liburma` | 库名标识 |
| `thread_id` | `thread_id=12345` | 当前线程 ID（通过 `gettid` 获取） |
| `thread_tag` | `-` | 线程标签，可通过 `urma_log_set_thread_tag()` 设置，默认 `-` |
| `function` / `file` | `urma_create_context` | 输出日志的函数名或文件名 |
| `Line` | `Line=123` | 日志输出位置行号 |
| `message` | `Invalid parameter.` | 日志正文 |

### 示例

```text
[URMA][liburma][thread_id=12345][-][urma_create_context[Line=123]]Invalid parameter.
```

## 日志级别

URMA 用户态日志级别与字符串映射如下：

| 字符串 | 内部级别 | 含义 |
|--------|----------|------|
| `fatal` | `URMA_VLOG_LEVEL_CRIT` | 致命错误 |
| `error` | `URMA_VLOG_LEVEL_ERR` | 错误 |
| `warning` | `URMA_VLOG_LEVEL_WARNING` | 警告 |
| `info` | `URMA_VLOG_LEVEL_INFO` | 信息（默认） |
| `debug` | `URMA_VLOG_LEVEL_DEBUG` | 调试 |

说明：`EMERG` / `ALERT` / `NOTICE` 等级别在打印时统一显示为 `Unknown` 或 `fatal`。

## 日志配置方式

### 1. 环境变量 `URMA_LOG_LEVEL`

启动进程前设置环境变量，例如：

```bash
export URMA_LOG_LEVEL=debug
./your_urma_app
```

有效值：`fatal`、`error`、`warning`、`info`、`debug`。

### 2. 环境变量 `URMA_LOG_SEPARATOR`

自定义字段分隔符，默认 `|`。有效字符集合为：

```text
|,;:-/.~#
```

例如：

```bash
export URMA_LOG_SEPARATOR=";"
```

### 3. 编程接口

```c
typedef void (*urma_log_cb_t)(int level, char *message);
urma_status_t urma_register_log_func(urma_log_cb_t func);
urma_status_t urma_unregister_log_func(void);

urma_vlog_level_t urma_log_get_level(void);
void urma_log_set_level(urma_vlog_level_t level);

const char *urma_log_get_thread_tag(void);
void urma_log_set_thread_tag(const char *tag);
```

## 速率限制

URMA 日志支持按调用点进行速率限制。当某条日志在窗口期内输出超过配额时，会暂时抑制，并在窗口结束时输出摘要：

```text
[URMA][liburma][thread_id=...][...][...]rate limit: N logs suppressed in last Xs
```

含义：过去 `X` 秒内，该调用点有 `N` 条日志被抑制，通常说明该错误正在高频发生。

## 默认落盘路径

- 默认由 rsyslog 输出到系统日志，常见路径为 `/var/log/messages` 或 `/var/log/syslog`（取决于系统配置）。
- 产品可通过 `/etc/rsyslog.d/urma.conf` 将 URMA 日志重定向到独立文件，例如：

```conf
:programname, contains, "URMA" /var/log/urma/urma.log
```

- 日志切割与保留建议通过 `/etc/logrotate.d/urma` 配置。

## 注意事项

- 当日志级别设置为 `info` 时，`debug` 级别的日志不会输出。
- 如果自定义日志回调函数，需确保线程安全。
- 日志中的 `thread_id` 对多线程问题定位非常有用。
- 出现大量 `rate limit` 摘要时，应优先排查触发高频日志的错误根因。
