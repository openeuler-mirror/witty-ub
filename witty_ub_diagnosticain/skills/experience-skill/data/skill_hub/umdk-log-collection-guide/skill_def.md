---
name: umdk-log-collection-guide
description: >
  指导用户如何收集、重定向、轮转和保留 UMDK 各组件（URMA、URPC、UMQ、DLock、CAM）的用户态日志。
  本 Skill 适用于 openEuler 等 Linux 系统，覆盖 rsyslog、logrotate、环境变量、日志回调接管等场景。
  通过本 Skill 可以输出标准化的日志收集配置和检查清单。
license: MIT
compatibility: openEuler 22.03/24.03 with rsyslog >= 8.0
metadata:
  author: umdk-log-analysis
  version: "1.0"
  keywords: [UMDK, URMA, URPC, UMQ, DLock, CAM, 日志收集, rsyslog, logrotate, 日志重定向]
allowed-tools: Bash(cat:*) Bash(ls:*) Bash(systemctl:*)
---

# UMDK 日志收集指南 Skill

## 概述

UMDK 各组件（URMA、URPC、UMQ、DLock、CAM）的用户态日志通常通过 `syslog()` 输出。本 Skill 提供标准化的收集方案，包括独立日志目录、rsyslog 重定向、logrotate 轮转和权限配置。

## 约束

- 仅适用于使用默认 syslog 输出的 UMDK 组件。
- 如果应用已接管日志回调，则需按应用自身日志系统收集。
- 环境变量 `*_LOG_LEVEL` 的生效取决于各组件是否支持。

## 流程

1. 确认目标组件的日志默认输出方式（syslog / 文件 / 回调）。
2. 创建 `/var/log/umdk/` 或组件专属目录。
3. 配置 `/etc/rsyslog.d/umdk-*.conf` 按标签重定向日志。
4. 配置 `/etc/logrotate.d/umdk-*` 日志轮转。
5. 重启 rsyslog 并验证日志是否写入。
6. 根据排障需要调整日志级别。

## 能力

- 输出 URMA / URPC / UMQ / DLock / CAM 的 rsyslog 配置示例。
- 输出对应的 logrotate 配置示例。
- 输出日志级别调整建议（`info` / `debug`）。
- 输出日志收集检查清单。

## 规则

- 日志目录权限建议 `755`，文件权限建议 `640`。
- 生产环境建议 `daily` 轮转并保留至少 30 天。
- `debug` 级别仅在临时排障时开启，避免长期运行。
- 配置变更后必须重启 rsyslog 或执行 `HUP` 信号重载。

## 配置示例

### URMA rsyslog 配置

```conf
:msg, contains, "[URMA]" /var/log/umdk/urma.log
:msg, contains, "[URMA]" ~
```

### UMDK 通用 logrotate 配置

```conf
/var/log/umdk/*.log {
    daily
    rotate 30
    missingok
    notifempty
    compress
    delaycompress
    sharedscripts
    postrotate
        /bin/kill -HUP $(cat /var/run/syslogd.pid 2>/dev/null) 2>/dev/null || true
    endscript
}
```
