---
name: umdk-urma-log-analysis
description: >
  提供 URMA 用户态日志的端到端分析流程，包括日志收集、格式解析、错误模式识别、根因排查和上报信息整理。
  本 Skill 用于指导运维或开发人员从 URMA 日志中定位用户态问题。
license: MIT
compatibility: UMDK v26.06.0_CAM
metadata:
  author: umdk-log-analysis
  version: "1.0"
  keywords: [UMDK, URMA, 日志分析, 故障排查, 错误模式, 根因分析]
allowed-tools: Bash(grep:*) Bash(awk:*) Bash(cat:*) Bash(dmesg:*)
---

# URMA 日志分析 Skill

## 概述

URMA 用户态日志是定位 API 调用失败、资源异常和性能问题的重要线索。本 Skill 提供从日志收集到根因分析的完整流程。

## 约束

- 需配合 URMA 日志格式规范使用。
- 内核态问题需同时查看 `dmesg` 和内核日志。
- 部分错误可能是上层应用误用 API 导致，需结合代码审查。

## 流程

1. 确认日志收集路径正确，日志级别适当。
2. 解析日志，提取关键字段（thread_id、function、Line、message）。
3. 识别错误级别（fatal/error）和常见错误模式。
4. 按线程/函数聚合，找到高频错误和发生顺序。
5. 结合内核日志、系统日志、应用日志交叉验证。
6. 对分布式/集群场景，还需结合 etcd 事件、ZMQ 端口、metadata 迁移、worker 健康检查等应用日志。
7. 整理问题现象、时间线、日志片段、环境信息，形成报告。

## 能力

- 输出 URMA 常见错误模式排查表。
- 输出日志聚合与统计方法。
- 输出需要同时收集的辅助信息清单（dmesg、/var/log/messages、配置）。
- 输出问题上报模板。

## 规则

- 先确认日志级别和收集范围，避免遗漏 debug 日志。
- 对 `Invalid parameter` / `NULL pointer` 类错误优先检查上层调用。
- 对 `failed to create context` / `init device` 类错误优先检查驱动和权限。
- 对 `rate limit` 摘要优先定位原始错误点。
- 上报问题时必须包含组件版本、操作系统版本、日志文件、复现步骤。

## 常见错误模式排查

| 模式 | 含义 | 排查方向 |
|------|------|----------|
| `Invalid parameter` | 参数非法 | 检查 API 入参 |
| `NULL pointer` | 空指针 | 检查前置 API 是否成功 |
| `no mem` | 内存分配失败 | 检查系统内存和资源数量 |
| `failed to create context` | 上下文创建失败 | 检查驱动/设备/权限 |
| `failed to find` | 资源未找到 | 检查资源 ID 和生命周期 |
| `timeout` | 超时 | 检查网络、对端、超时配置 |
| `rate limit` | 日志风暴 | 定位高频错误根因 |

## 辅助信息收集

```bash
# 内核日志
dmesg -T > dmesg.log

# 系统日志
journalctl -xe --since "1 hour ago" > system.log

# 模块/设备
lsmod | grep urma > modules.log
ls -l /dev/urma* /dev/infiniband/* > devices.log

# 版本信息
cat /etc/os-release
```

## 问题上报模板

```markdown
## 问题概述
简要描述异常现象。

## 环境信息
- OS 版本：
- UMDK 版本：
- 硬件型号：
- 日志级别：

## 复现步骤
1. ...
2. ...

## 关键日志片段
```text
[粘贴相关日志]
```

## 已尝试的排查
- [ ] 检查日志级别
- [ ] 检查驱动加载
- [ ] 检查权限
- [ ] 检查参数
```
