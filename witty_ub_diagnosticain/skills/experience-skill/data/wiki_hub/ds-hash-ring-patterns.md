---
name: "yuanrong-datasystem Hash Ring 模式"
description: "汇总 openYuanrong datasystem 一致性哈希（Hash Ring）的日志模式、版本更新、addnode/delnode、元数据迁移与扩缩容场景。"
keywords:
  - yuanrong-datasystem
  - datasystem
  - hash ring
  - 一致性哈希
  - 元数据迁移
  - scale up
  - scale down
  - addnode
  - delnode
references:
  - name: "yuanrong-datasystem 0.8.1.rc20 Hash Ring 实现"
    type: offline
    source: "yuanrong-datasystem-0.8.1.rc20/src/datasystem/worker/hash_ring/hash_ring.cpp"
  - name: "yuanrong-datasystem 0.8.1.rc20 Hash Ring 任务执行器"
    type: offline
    source: "yuanrong-datasystem-0.8.1.rc20/src/datasystem/worker/hash_ring/hash_ring_task_executor.cpp"
---

# yuanrong-datasystem Hash Ring 模式

## 概述

openYuanrong datasystem 使用一致性哈希（Hash Ring）决定对象/流在 Worker 集群中的分布。节点上下线会触发 hash ring 更新，并可能伴随元数据迁移。本文档汇总相关日志模式。

## 1. Hash Ring 更新

### 1.1 更新日志

```text
Update ring of version ... . add_node_info: ... del_node_info: ...
```

字段说明：
- `version`：当前 ring 版本号，每次更新递增。
- `add_node_info`：本次新增的节点信息。
- `del_node_info`：本次删除的节点信息。

### 1.2 版本一致性

所有 Worker 应最终达到相同的 ring 版本。如果版本不一致，可能导致：
- 请求路由错误。
- 对象/流定位失败。
- 元数据迁移混乱。

## 2. 节点事件

### 2.1 节点加入

```text
Event Type: Add Node: ...
```

说明：新节点加入集群，触发 hash ring 更新和可能的元数据迁移。

### 2.2 节点移除

```text
Event Type: Remove Node: ...
```

说明：节点从集群移除，触发数据迁移或副本恢复。

## 3. 元数据迁移

### 3.1 提交迁移任务

```text
Submit async task to migrate meta.
```

说明：hash ring 更新后，提交异步任务迁移元数据。

### 3.2 开始迁移

```text
Start migrate task from ... to ... with traceId ...
Start migrate task from ... srcdbName ... to ... dest dbname ... with traceId ...
```

说明：从源节点迁移元数据到目标节点，可能涉及不同 RocksDB 实例。

### 3.3 迁移完成

```text
Finish migrate task from ... to ... cost ... ms.
Finish migrate task from ... srcdbName ... to ... dest dbname ... cost ... ms.
```

### 3.4 迁移失败

```text
Fill metadata for migration failed. ... worker don't receive addnode info
GetMigrateMetadataResult failed. ...
```

可能原因：
- 目标节点未收到 addnode 信息。
- 目标节点状态未 READY。
- 源节点与目标节点网络断开。
- 迁移任务超时。

## 4. Scale Up

### 4.1 新节点加入

```text
Event Type: Add Node: ...
Update ring of version ... . add_node_info: [new_node] del_node_info: []
```

### 4.2 数据迁移

新节点加入后，部分数据会从其他节点迁移到新节点，以平衡负载。

## 5. Scale Down

### 5.1 提交缩容任务

```text
Submit scale down task of ... with traceid ...
Write the scale down task of ... into etcd success with version ...
```

### 5.2 开始处理

```text
Begin to process voluntary scale down task
```

### 5.3 任务冲突

```text
all scale down task is processing, no need to excute, skip
```

说明：已有 scale down 任务在执行，无需重复提交。

### 5.4 无处理节点

```text
no worker to handle scale down task, no need excute scale down task, erase del_node_info for ...
```

说明：没有可用节点处理缩容任务。

### 5.5 顺序约束

```text
scale down task must before scale up finish, recover may be failed if scale down begin
```

说明：scale down 任务必须在 scale up 完成之前执行，否则恢复可能失败。

## 6. 节点状态机

### 6.1 状态转换

```text
ChangeStateTo(FAIL, "There is a running scale down task on this node.")
```

说明：节点状态因运行中的 scale down 任务而转换为 FAIL。

### 6.2 自动移除 Dead 节点

当 `auto_del_dead_node=true` 时，dead 节点会自动从 hash ring 移除，触发 del_node_info 和迁移。

## 7. 典型问题排查

### 7.1 Hash Ring 版本不一致

排查：
- 对比所有 Worker 的 `Update ring of version` 日志。
- 检查网络分区或 ETCD 事件丢失。
- 检查是否有节点未收到 WATCH 事件。

### 7.2 迁移任务卡住

排查：
- 检查是否有 "Start migrate task" 但没有 "Finish migrate task"。
- 检查目标节点是否收到 addnode 信息。
- 检查源节点和目标节点网络连通性。

### 7.3 缩容无法完成

排查：
- 检查 "Submit scale down task" 是否成功。
- 检查是否有 "Begin to process voluntary scale down task"。
- 检查是否有可用节点处理缩容。

## 8. 解析示例

### 提取 ring 版本变化

```bash
grep "Update ring of version" datasystem_worker.INFO.log
```

### 提取迁移任务

```bash
grep -E "Submit async task to migrate meta|Start migrate task|Finish migrate task" datasystem_worker.INFO.log
```

### 提取缩容相关日志

```bash
grep -E "Submit scale down task|Write the scale down task|Begin to process voluntary scale down task" datasystem_worker.INFO.log
```

## 注意事项

- hash ring 版本不一致是路由错误和数据不一致的根本原因，需要优先确认。
- 元数据迁移期间，相关请求可能延迟或返回 `K_TRY_AGAIN`。
- scale down 任务顺序约束需要严格遵守，避免恢复失败。
- 分析迁移问题时，需要同时查看源节点、目标节点和 Master 的日志。
