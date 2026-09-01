---
name: "UMDK URPC 日志配置说明"
description: "介绍 URPC 框架日志配置结构 urpc_log_config_t、日志级别、日志标志位和自定义回调能力。"
keywords:
  - UMDK
  - URPC
  - 日志配置
  - urpc_log_config_t
  - 日志级别
  - 速率限制
references:
  - name: "UMDK v26.06.0_CAM 源码：urpc_framework_types.h"
    type: offline
    source: "umdk-v26.06.0_CAM/src/urpc/include/framework/urpc_framework_types.h"
  - name: "UMDK v26.06.0_CAM 源码：urpc_framework_api.h"
    type: offline
    source: "umdk-v26.06.0_CAM/src/urpc/include/framework/urpc_framework_api.h"
  - name: "UMDK v26.06.0_CAM GitCode 仓库"
    type: online
    source: "https://gitcode.com/openeuler/umdk/tags/v26.06.0_CAM"
---

# UMDK URPC 日志配置说明

## 概述

URPC 框架提供独立的日志配置机制，通过 `urpc_log_config_t` 结构设置日志级别、标志位和速率限制。URPC 日志默认输出到 URMA 日志系统或自定义回调。

## 日志配置结构

```c
typedef enum urpc_log_level {
    URPC_LOG_LEVEL_EMERG = 0,
    URPC_LOG_LEVEL_ALERT,
    URPC_LOG_LEVEL_CRIT,
    URPC_LOG_LEVEL_ERR,
    URPC_LOG_LEVEL_WARN,
    URPC_LOG_LEVEL_NOTICE,
    URPC_LOG_LEVEL_INFO,
    URPC_LOG_LEVEL_DEBUG,
    URPC_LOG_LEVEL_MAX,
} urpc_log_level_t;

typedef struct urpc_log_config {
    uint32_t log_flag;              // 日志标志位
    urpc_log_level_t level;          // 日志级别
} urpc_log_config_t;
```

## 日志标志位

| 标志位 | 含义 |
|--------|------|
| `URPC_LOG_FLAG_FUNC` | 输出函数名 |
| `URPC_LOG_FLAG_LEVEL` | 输出日志级别 |
| `URPC_LOG_FLAG_RATE_LIMITED` | 启用速率限制 |

## 日志级别

| 级别 | 含义 |
|------|------|
| `URPC_LOG_LEVEL_EMERG` | 系统不可用 |
| `URPC_LOG_LEVEL_ALERT` | 必须立即处理 |
| `URPC_LOG_LEVEL_CRIT` | 严重错误 |
| `URPC_LOG_LEVEL_ERR` | 错误 |
| `URPC_LOG_LEVEL_WARN` | 警告 |
| `URPC_LOG_LEVEL_NOTICE` | 正常但重要 |
| `URPC_LOG_LEVEL_INFO` | 信息（默认） |
| `URPC_LOG_LEVEL_DEBUG` | 调试 |

## 配置接口

```c
int urpc_log_config_set(urpc_log_config_t *config);
int urpc_log_config_get(urpc_log_config_t *config);
```

设置示例：

```c
urpc_log_config_t config = {0};
config.log_flag = URPC_LOG_FLAG_FUNC | URPC_LOG_FLAG_LEVEL | URPC_LOG_FLAG_RATE_LIMITED;
config.level = URPC_LOG_LEVEL_DEBUG;
urpc_log_config_set(&config);
```

## 自定义日志回调

URPC 内部日志通过 URMA 日志基础设施输出。应用可通过 URMA 的 `urma_register_log_func()` 接管日志，实现统一日志收集。

## 速率限制

启用 `URPC_LOG_FLAG_RATE_LIMITED` 后，高频日志会被抑制。适用于高吞吐场景，避免日志磁盘被打满。

## 配置建议

| 场景 | 建议级别 | 标志位 |
|------|----------|--------|
| 生产环境 | `INFO` | `FUNC + LEVEL + RATE_LIMITED` |
| 问题定位 | `DEBUG` | `FUNC + LEVEL` |
| 高吞吐场景 | `WARN` | `LEVEL + RATE_LIMITED` |

## 注意事项

- 与 UMQ 类似，URPC 日志最终受 URMA 日志系统和回调控制。
- `DEBUG` 级别会显著增加日志量，建议临时开启。
- 队列相关错误（QUEUE_FAILURE、QUEUE_SHUTDOWN 等）通常以 ERR/CRIT 级别输出，应重点监控。
