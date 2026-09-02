---
name: ds-cluster-management-diagnosis
description: >
  介绍 openYuanrong datasystem 集群管理（ETCD/Metastore）的日志分析方法，覆盖节点发现、lease 保活、watch 事件、
  节点状态机（timeout/dead）、扩缩容和典型脑裂场景。
license: MIT
compatibility: yuanrong-datasystem 0.8.1.rc20
metadata:
  author: yuanrong-datasystem-log-analysis
  version: "1.0"
  keywords: [yuanrong-datasystem, datasystem, 集群管理, ETCD, Metastore, lease, 节点发现, 扩缩容]
allowed-tools: Bash(grep:*) Bash(awk:*) Bash(sed:*) Bash(cat:*)
---

# yuanrong-datasystem 集群管理诊断 Skill

## 概述

openYuanrong datasystem 支持 ETCD 和 Metastore 两种集群管理方式。集群管理负责节点发现、健康检测、故障恢复和在线扩缩容。分析集群管理日志需要关注 lease 保活、watch 事件、节点状态转换和扩缩容任务。

## 约束

- ETCD 方式需要外部 ETCD 集群；Metastore 方式由主节点 Worker 内置提供。
- 节点通过 lease 保活，lease 失效会导致节点被移除。
- 节点状态包括 ACTIVE、TIMEOUT、FAILED、JOINING 等。
- 扩缩容会触发 hash ring 更新和元数据迁移。

## 流程

1. 确认集群管理方式（ETCD 或 Metastore）。
2. 检查各 Worker 的 lease 创建和保活日志。
3. 检查 watch 事件（Add Node / Remove Node）。
4. 分析节点状态转换（timeout → dead）。
5. 检查 scale up/down 任务提交和执行情况。
6. 结合 request_out.log 分析 ETCD 请求成功率。

## 能力

- 输出 ETCD/Metastore 部署差异和日志特征。
- 输出 lease 创建、保活、失效的日志模式。
- 输出 watch 事件和节点状态转换的日志模式。
- 输出扩缩容任务的日志模式。
- 输出集群脑裂/网络分区的判断方法。

## 规则

- 分析集群问题时，需要同时收集所有 Worker 和 Master 的日志。
- lease 失效通常与 Worker 进程挂起或网络问题相关，需结合系统日志。
- 节点被标记为 dead 后，会触发元数据迁移，应检查迁移是否成功。
- 扩缩容失败时，常见原因是目标节点未收到 addnode 信息或迁移失败。

## 集群管理方式

### ETCD 方式

- 外部 ETCD 集群，Worker 通过 gRPC 通信。
- 日志特征：`Using external etcd: ...`、`DS_ETCD_*` action。
- 适用：已有 ETCD、多集群共享、高可用要求高的场景。

### Metastore 方式

- 内置在主节点 Worker 中，从节点连接到主节点 Metastore。
- 关键参数：`start_metastore_service`、`metastore_address`。
- 适用：快速部署、资源受限、简化运维的场景。

## 关键日志模式

### lease 生命周期

```text
Creating lease with expiry time: ...
Creating new lease KeepAlive object for lease ... with heartbeat interval timeout: ...
Sending cluster node to etcd and establish lease.
Failed to refresh lease: the new ttl is 0.
etcd keep alive run failed, keep alive timer ElapsedMilliSecond: ...
Starting KeepAlive monitoring thread
Keep alive thread completed with success rc
```

### 节点状态转换

```text
Mark ... as timeout.
A timed out cluster node was demoted to become a failed node: ...
```

### Watch 事件

```text
Process event: prefix: CLUSTER, event msg: key: ..., event type: PUT/DELETE
Event Type: Add Node: ...
Event Type: Remove Node: ...
```

### 扩缩容任务

```text
Write the scale down task of ... into etcd success with version ...
Submit scale down task of ... with traceid ...
Submit async task to migrate meta.
Start migrate task from ... to ... with traceId ...
Finish migrate task from ... to ... cost ... ms
```

### 网络故障模拟

```text
Due to network failure, a fake node deletion event[key: ...] needs to be generated
```

说明：当 Worker 与 ETCD 连接断开时，会生成一个伪造的 DELETE 事件，触发本地集群状态更新。

## 解析示例

### 检查所有节点 lease 状态

```bash
grep -E "Creating lease|Failed to refresh lease|etcd keep alive run failed" */datasystem_worker.INFO.log
```

### 统计 Add/Remove Node 事件

```bash
grep -E "Event Type: Add Node|Event Type: Remove Node" */datasystem_worker.INFO.log
```

### 检查节点被标记为 dead 的时间线

```bash
grep "A timed out cluster node was demoted to become a failed node" */datasystem_worker.INFO.log
```

### 检查扩缩容任务

```bash
grep -E "Submit scale down task|Start migrate task|Finish migrate task" */datasystem_worker.INFO.log
```

## 常见错误码

| 错误码 | 含义 | 排查方向 |
|--------|------|----------|
| K_KVSTORE_ERROR=4 | KV 存储错误 | 检查 ETCD/Metastore 状态 |
| K_NOT_LEADER_MASTER=14 | 非 leader master | 检查 master 选举 |
| K_TRY_AGAIN=19 | 稍后重试 | 集群正在变更，稍后重试 |
| K_DATA_INCONSISTENCY=20 | 数据不一致 | 检查 hash ring 版本和元数据 |
| K_SHUTTING_DOWN=21 | 正在关闭 | 节点正在下线 |
| K_WORKER_ABNORMAL=22 | Worker 异常 | 检查 Worker 状态 |
| K_RETRY_IF_LEAVING=30 | 节点正在离开 | 等待节点完全下线或重试 |
| K_SCALE_DOWN=31 | 节点正在缩容 | 等待缩容完成 |
| K_SCALING=32 | 正在扩缩容 | 等待扩缩容完成 |
| K_RPC_DEADLINE_EXCEEDED=1001 | RPC 超时 | 检查网络、ETCD 负载 |
| K_RPC_UNAVAILABLE=1002 | 对端不可用 | 检查 ETCD/Metastore 是否可达 |

## 注意事项

- 集群脑裂通常表现为多个 Worker 互相认为对方已下线，但各自 lease 仍在更新。
- 网络分区时，Worker 与 ETCD 断开会触发伪造 DELETE 事件，恢复后会重新注册。
- 扩缩容期间请求可能返回 `K_TRY_AGAIN`、`K_SCALING` 等，需要应用层重试。
- Metastore 方式下，主节点异常会影响整个集群，需要重点监控主节点健康。
