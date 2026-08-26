---
name: umdk-log-parser-basics
description: >
  介绍 UMDK 用户态日志的通用解析方法，包括字段含义、正则提取、线程 ID 聚合、时间序列分析和常见问题。
  本 Skill 可用于帮助从 UMDK 日志中快速提取关键信息并定位异常。
license: MIT
compatibility: UMDK v26.06.0_CAM
metadata:
  author: umdk-log-analysis
  version: "1.0"
  keywords: [UMDK, URMA, 日志解析, 正则, thread_id, 日志分析, 时间序列]
allowed-tools: Bash(grep:*) Bash(awk:*) Bash(sed:*) Bash(cat:*)
---

# UMDK 日志解析基础 Skill

## 概述

UMDK 各组件日志通常具有 `[COMPONENT][libname][thread_id=...][tag][location]message` 的固定格式。本 Skill 提供从原始日志中提取关键字段、聚合相同线程、识别高频异常的方法。

## 约束

- 默认字段分隔符为 `|`，可通过 `URMA_LOG_SEPARATOR` 等环境变量修改。
- 若应用接管日志回调，日志格式由应用决定，可能不适用默认解析方法。
- 日志时间戳来自 rsyslog 或 journald，不在 `message` 字段内。

## 流程

1. 确认日志字段分隔符。
2. 使用正则或脚本提取 `thread_id`、`function`、`Line`、`message`。
3. 按 `thread_id` 和 `function` 聚合，定位高频错误。
4. 对错误日志按时间序列排序，观察发生顺序和频率。
5. 结合 `rate limit` 摘要判断是否存在日志风暴。

## 能力

- 输出 URMA 日志默认正则提取模式。
- 输出按线程/函数聚合的命令示例。
- 输出识别日志风暴和速率限制的方法。
- 输出常见解析问题及原因。

## 规则

- 解析前备份原始日志，避免修改。
- 使用 `grep -E` 过滤时先确认字段分隔符是否变化。
- 聚合统计时排除 `rate limit` 摘要行，以免重复计数。
- 时间序列分析应使用 syslog 时间戳，而不是日志内部字段。

## 正则示例

### 提取 thread_id、function 和 message

```bash
grep "\[URMA\]" urma.log | awk -F'|' '
{
    for(i=1;i<=NF;i++){
        if($i ~ /thread_id=/) tid=$i
        if($i ~ /\[/ && $i ~ /Line/) func=$i
    }
    msg=$(NF-0)
    print tid, func, msg
}'
```

### 按函数统计错误次数

```bash
grep "\[URMA\]" urma.log | grep -E "(error|fatal|Invalid|failed)" | \
  awk -F'|' '{for(i=1;i<=NF;i++) if($i ~ /\[/ && $i !~ /URMA/ && $i !~ /liburma/ && $i !~ /thread_id/) print $i}' | \
  sort | uniq -c | sort -rn | head -20
```

## 日志风暴判断

```text
rate limit: N logs suppressed in last Xs
```

出现该摘要时，说明对应日志点正在高频输出。应：
- 找到摘要前的原始错误日志。
- 检查是否陷入循环、重试、或资源未释放。
- 临时提升日志级别或限制重试频率。

## 常见问题

1. **字段分隔符不一致**：确认是否设置过 `URMA_LOG_SEPARATOR`。
2. **线程 ID 缺失**：可能是旧版本或自定义回调日志。
3. **时间戳不准确**：查看 syslog 时间戳，必要时开启 `rsyslog` 高精度时间戳。
