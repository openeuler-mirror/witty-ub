---
name: ds-hash-ring-metadata-diagnosis
description: >
  介绍 openYuanrong datasystem 一致性哈希（Hash Ring）与元数据迁移的日志分析方法，覆盖 hash ring 更新、
  addnode/delnode 事件、scale up/down、元数据迁移任务与状态机转换。
license: MIT
compatibility: yuanrong-datasystem 0.8.1.rc20
metadata:
  author: yuanrong-datasystem-log-analysis
  version: "1.0"
  keywords: [yuanrong-datasystem, datasystem, hash ring, 一致性哈希, 元数据迁移, scale up, scale down, addnode, delnode]
allowed-tools: Bash(grep:*) Bash(awk:*) Bash(sed:*) Bash(cat:*)
---

# yuanrong-datasystem Hash Ring 与元数据迁移诊断 Skill

## 概述

openYuanrong datasystem 使用一致性哈希（Hash Ring）管理对象/流在集群中的分布。节点上下线会触发 hash ring 更新和元数据迁移，分析相关日志对于定位数据不一致、迁移失败、扩缩容卡顿等问题至关重要。

## 约束

- Hash ring 版本号在更新时递增，可通过 `Update ring of version` 日志确认。
- add_node_info 和 del_node_info 描述了 ring 的变更内容。
- scale down 任务必须在 scale up 完成之前执行，否则恢复可能失败。
- 元数据迁移涉及本地 RocksDB 数据在不同 Worker 间搬迁。

## 流程

1. 检查 `Update ring of version` 日志，确认 ring 版本变化。
2. 检查 `Add Node`/`Remove Node` 事件，确认节点上下线。
3. 检查 `Submit async task to migrate meta` 和迁移任务日志。
4. 检查 `Submit scale down task` 和 `Write the scale down task` 日志。
5. 分析迁移失败原因（如目标节点未收到 addnode 信息）。
6. 检查节点状态机（ACTIVE/JOINING/FAILED）和 `auto_del_dead_node` 行为。

## 能力

- 输出 hash ring 更新和节点事件的日志模式。
- 输出元数据迁移任务的日志模式。
- 输出 scale up/down 任务的日志模式。
- 输出迁移失败常见原因和排查方向。
- 输出节点状态机转换的日志模式。

## 规则

- hash ring 版本不一致是数据路由错误的常见原因，需要确认所有节点版本一致。
- 迁移任务失败时，应检查源节点和目标节点的日志，按时间线串联。
- scale down 任务卡住时，可能导致缩容无法完成，需要检查任务执行状态。
- `auto_del_dead_node=true` 时，dead 节点会自动从 ring 中移除，触发元数据迁移。

## 关键日志模式

### Hash Ring 更新

```text
Update ring of version ... . add_node_info: ... del_node_info: ...
```

- `version`：ring 版本号。
- `add_node_info`：新增节点信息。
- `del_node_info`：删除节点信息。

### 节点事件

```text
Event Type: Add Node: ...
Event Type: Remove Node: ...
```

### 元数据迁移

```text
Submit async task to migrate meta.
Start migrate task from ... to ... with traceId ...
Fill metadata for migration failed. ... worker don't receive addnode info
GetMigrateMetadataResult failed. ...
Finish migrate task from ... to ... cost ... ms
```

### Scale Down 任务

```text
Submit scale down task of ... with traceid ...
Write the scale down task of ... into etcd success with version ...
all scale down task is processing, no need to excute, skip
no worker to handle scale down task, no need excute scale down task, erase del_node_info for ...
restore scale down task failed.
Begin to process voluntary scale down task
```

### 状态机转换

```text
ChangeStateTo(FAIL, "There is a running scale down task on this node.")
```

## 解析示例

### 提取 ring 版本更新历史

```bash
grep "Update ring of version" datasystem_worker.INFO.log
```

### 提取迁移任务时间线

```bash
grep -E "Start migrate task|Finish migrate task|Fill metadata for migration failed" datasystem_worker.INFO.log
```

### 提取 scale down 任务

```bash
grep -E "Submit scale down task|Write the scale down task|Begin to process voluntary scale down task" datasystem_worker.INFO.log
```

### 检查迁移失败原因

```bash
grep -E "Fill metadata for migration failed|GetMigrateMetadataResult failed|restore scale down task failed" datasystem_worker.INFO.log
```

## 常见错误与原因

| 问题 | 日志特征 | 可能原因 |
|------|----------|----------|
| 迁移失败 | `Fill metadata for migration failed. ... worker don't receive addnode info` | 目标节点未收到 addnode 信息或状态未 READY |
| 缩容卡住 | `all scale down task is processing, no need to excute, skip` | 已有 scale down 任务在执行 |
| 无节点处理缩容 | `no worker to handle scale down task` | 无存活节点可承担迁移目标 |
| 恢复失败 | `scale down task must before scale up finish, recover may be failed` | scale down 与 scale up 顺序冲突 |
| 状态机异常 | `ChangeStateTo(FAIL, ...)` | 节点状态异常，无法处理任务 |

## 注意事项

- hash ring 版本不一致会导致请求路由错误，需要确保所有节点最终达到相同版本。
- 元数据迁移期间，相关对象/流访问可能延迟或返回 `K_TRY_AGAIN`。
- 缩容完成后，原节点数据会迁移到其他节点，需要确认迁移完成再下线节点。
- 分析迁移问题时，需要同时查看源节点、目标节点和 Master 的日志。
