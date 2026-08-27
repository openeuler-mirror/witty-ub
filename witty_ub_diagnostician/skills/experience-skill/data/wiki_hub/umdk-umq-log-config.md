---
name: "UMDK UMQ 日志配置说明"
description: "介绍 UMQ 日志配置结构 umq_log_config_t、日志级别、日志标志位、自定义回调和速率限制能力。"
keywords:
  - UMDK
  - UMQ
  - 日志配置
  - umq_log_config_t
  - 日志级别
  - 速率限制
references:
  - name: "UMDK v26.06.0_CAM 源码：umq_types.h"
    type: offline
    source: "umdk-v26.06.0_CAM/src/urpc/include/umq/umq_types.h"
  - name: "UMDK v26.06.0_CAM 源码：umq_api.h"
    type: offline
    source: "umdk-v26.06.0_CAM/src/urpc/include/umq/umq_api.h"
  - name: "UMDK v26.06.0_CAM GitCode 仓库"
    type: online
    source: "https://gitcode.com/openeuler/umdk/tags/v26.06.0_CAM"
---

# UMDK UMQ 日志配置说明

## 概述

UMQ 提供独立的日志配置机制，通过 `umq_log_config_t` 结构设置日志级别、标志位和速率限制。UMQ 日志默认通过 URMA 日志基础设施或自定义回调输出。

## 日志配置结构

```c
typedef enum umq_log_level {
    UMQ_LOG_LEVEL_EMERG = 0,
    UMQ_LOG_LEVEL_ALERT,
    UMQ_LOG_LEVEL_CRIT,
    UMQ_LOG_LEVEL_ERR,
    UMQ_LOG_LEVEL_WARN,
    UMQ_LOG_LEVEL_NOTICE,
    UMQ_LOG_LEVEL_INFO,
    UMQ_LOG_LEVEL_DEBUG,
    UMQ_LOG_LEVEL_MAX,
} umq_log_level_t;

typedef struct umq_log_config {
    uint32_t log_flag;              // 日志标志位
    umq_log_level_t level;          // 日志级别
} umq_log_config_t;
```

## 日志标志位

| 标志位 | 含义 |
|--------|------|
| `UMQ_LOG_FLAG_FUNC` | 输出函数名 |
| `UMQ_LOG_FLAG_LEVEL` | 输出日志级别 |
| `UMQ_LOG_FLAG_RATE_LIMITED` | 启用速率限制 |
| `UMQ_LOG_FLAG_EXT_FUNC` | 输出扩展函数信息 |

## 日志级别

| 级别 | 含义 |
|------|------|
| `UMQ_LOG_LEVEL_EMERG` | 系统不可用 |
| `UMQ_LOG_LEVEL_ALERT` | 必须立即处理 |
| `UMQ_LOG_LEVEL_CRIT` | 严重错误 |
| `UMQ_LOG_LEVEL_ERR` | 错误 |
| `UMQ_LOG_LEVEL_WARN` | 警告 |
| `UMQ_LOG_LEVEL_NOTICE` | 正常但重要 |
| `UMQ_LOG_LEVEL_INFO` | 信息（默认） |
| `UMQ_LOG_LEVEL_DEBUG` | 调试 |

## 配置接口

```c
int umq_log_config_set(umq_log_config_t *config);
int umq_log_config_get(umq_log_config_t *config);
```

设置示例：

```c
umq_log_config_t config = {0};
config.log_flag = UMQ_LOG_FLAG_FUNC | UMQ_LOG_FLAG_LEVEL | UMQ_LOG_FLAG_RATE_LIMITED;
config.level = UMQ_LOG_LEVEL_DEBUG;
umq_log_config_set(&config);
```

## 自定义日志回调

UMQ 内部日志最终通过 URMA 日志基础设施输出。应用可通过 URMA 的 `urma_register_log_func()` 接管日志，从而将 UMQ 日志导入自有日志框架。

## 速率限制

启用 `UMQ_LOG_FLAG_RATE_LIMITED` 后，高频日志会被抑制，并输出 `rate limit` 摘要。适用于线上生产环境，避免日志风暴。

## 配置建议

| 场景 | 建议级别 | 标志位 |
|------|----------|--------|
| 生产环境 | `INFO` | `FUNC + LEVEL + RATE_LIMITED` |
| 问题定位 | `DEBUG` | `FUNC + LEVEL` |
| 性能敏感 | `WARN` | `LEVEL + RATE_LIMITED` |

## 注意事项

- 日志级别设置需在线程安全的前提下进行。
- 如果 `URMA_LOG_LEVEL` 环境变量或 URMA 日志回调被设置，UMQ 日志输出也会受其影响。
- `DEBUG` 级别日志量较大，建议仅在临时排障时开启。
- 不同 UMQ 后端（transport provider）对日志配置的支持可能略有差异。
