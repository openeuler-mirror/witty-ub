---
name: umdk-log-level-config
description: >
  介绍 UMDK 各组件（URMA、URPC、UMQ、DLock、CAM）日志级别的配置方式，包括环境变量、编程接口、运行期切换和级别映射关系。
  本 Skill 用于指导用户如何按场景选择日志级别并排查日志级别不生效的问题。
license: MIT
compatibility: UMDK v26.06.0_CAM
metadata:
  author: umdk-log-analysis
  version: "1.0"
  keywords: [UMDK, URMA, URPC, UMQ, DLock, CAM, 日志级别, URMA_LOG_LEVEL, debug, info]
allowed-tools: Bash(cat:*) Bash(ls:*) Bash(echo:*)
---

# UMDK 日志级别配置 Skill

## 概述

UMDK 组件通常支持通过环境变量或 API 配置日志级别。合理的日志级别设置可以平衡日志详细程度与性能开销。

## 约束

- 环境变量需在进程启动前设置，子进程继承父进程环境变量。
- 部分组件可能不支持所有级别，具体以源码枚举为准。
- `debug` 级别日志量通常远大于 `info`，长期开启可能影响性能。

## 流程

1. 确认目标组件支持的日志级别枚举（`fatal` / `error` / `warning` / `info` / `debug` 等）。
2. 根据环境变量规则在启动前设置级别。
3. 验证日志中是否按预期输出对应级别的日志。
4. 对于需要动态调整的场景，使用组件提供的 API。

## 能力

- 输出 URMA 日志级别映射表和默认级别。
- 输出环境变量配置方法。
- 输出编程接口 `urma_log_set_level()` 等用法。
- 输出日志级别不生效时的排查步骤。

## 规则

- 生产环境保持默认 `info` 或 `warning`，仅在排障时开启 `debug`。
- 环境变量名称通常以组件名前缀命名，例如 `URMA_LOG_LEVEL`。
- 设置 `debug` 后应同步检查磁盘空间和日志轮转策略。
- 如果应用接管了日志回调，环境变量可能不再生效，需由应用自身控制。

## 常见日志级别映射

| 字符串 | 典型枚举值 | 用途 |
|--------|------------|------|
| `fatal` | CRIT/EMERG | 致命错误 |
| `error` | ERR | 错误 |
| `warning` | WARNING | 警告 |
| `info` | INFO | 通用信息（默认） |
| `debug` | DEBUG | 调试信息 |

## 配置示例

### 环境变量

```bash
export URMA_LOG_LEVEL=debug
export URMA_LOG_SEPARATOR="|"
```

### 编程接口

```c
urma_log_set_level(URMA_VLOG_LEVEL_DEBUG);
urma_log_set_thread_tag("worker-0");
```

## 不生效排查

1. 检查环境变量是否设置正确：`echo $URMA_LOG_LEVEL`
2. 检查进程是否已加载环境变量：`cat /proc/<pid>/environ | tr '\0' '\n' | grep LOG_LEVEL`
3. 检查应用是否接管了日志回调（调用 `urma_register_log_func`）。
4. 检查日志输出目标是否被 rsyslog 过滤。
