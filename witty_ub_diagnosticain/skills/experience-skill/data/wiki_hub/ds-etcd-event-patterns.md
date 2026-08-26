---
name: "yuanrong-datasystem ETCD 事件模式"
description: "汇总 openYuanrong datasystem 中 ETCD 相关事件日志模式，包括 lease、PUT/DELETE、WATCH、节点状态机和 scale down task 的日志特征。"
keywords:
  - yuanrong-datasystem
  - datasystem
  - ETCD
  - lease
  - WATCH
  - PUT
  - DELETE
  - scale down
  - cluster
references:
  - name: "yuanrong-datasystem 0.8.1.rc20 ETCD 存储实现"
    type: offline
    source: "yuanrong-datasystem-0.8.1.rc20/src/datasystem/common/kvstore/etcd/etcd_store.cpp"
  - name: "yuanrong-datasystem 0.8.1.rc20 ETCD keepalive"
    type: offline
    source: "yuanrong-datasystem-0.8.1.rc20/src/datasystem/common/kvstore/etcd/etcd_keep_alive.cpp"
  - name: "yuanrong-datasystem 0.8.1.rc20 集群管理文档"
    type: offline
    source: "yuanrong-datasystem-0.8.1.rc20/docs/source_zh_cn/design_document/cluster_management.md"
---

# yuanrong-datasystem ETCD 事件模式

## 概述

ETCD 是 openYuanrong datasystem 的核心元数据存储和集群协调组件。Worker 通过 ETCD 进行节点注册、lease 保活、元数据存储和事件监听。本文档汇总 ETCD 相关日志模式。

## 1. Lease 事件

### 1.1 申请 Lease

```text
Creating lease with expiry time: ...
```

说明：Worker 向 ETCD 申请 lease，`expiry time` 通常为 `node_timeout_s`。

### 1.2 创建 KeepAlive 对象

```text
Creating new lease KeepAlive object for lease ... with heartbeat interval timeout: ...
```

说明：创建 lease 保活对象，开始周期性续约。

### 1.3 启动监控线程

```text
Starting KeepAlive monitoring thread
```

说明：启动外层监控线程，负责在保活失败时重建 lease 和连接。

### 1.4 保活成功

```text
Keep alive thread completed with success rc
```

说明：正常关闭时，lease 保活线程成功退出。

### 1.5 保活失败

```text
Failed to refresh lease: the new ttl is 0.
etcd keep alive run failed, keep alive timer ElapsedMilliSecond: ...
```

可能原因：
- Worker 进程挂起。
- ETCD 集群异常。
- 网络分区导致 lease 过期。

## 2. KV 操作事件

### 2.1 PUT 注册节点

```text
Sending cluster node to etcd and establish lease.
```

说明：Worker 将节点信息写入 ETCD，并与 lease 绑定。

### 2.2 状态更新

```text
UpdateNodeState: ...
```

说明：Worker 更新节点状态（如 start、recover、failed）。

### 2.3 DELETE 事件

```text
Process event: prefix: CLUSTER, event msg: key: ..., event type: DELETE
```

说明：监听到节点删除事件，通常由 lease 过期或节点主动下线触发。

## 3. WATCH 事件

### 3.1 监听集群事件

```text
Process event: prefix: CLUSTER, event msg: key: ..., event type: PUT/DELETE
```

说明：Worker 或 Master 监听 ETCD 前缀事件，处理节点上下线。

### 3.2 节点加入

```text
Event Type: Add Node: ...
```

说明：新节点加入集群，会触发 hash ring 更新。

### 3.3 节点移除

```text
Event Type: Remove Node: ...
```

说明：节点从集群移除，可能触发元数据迁移或副本恢复。

## 4. 节点状态机

### 4.1 状态定义

| 状态 | 说明 |
|------|------|
| start | 节点首次启动 |
| restart | 节点重启 |
| recover | 节点恢复后（正常状态） |
| d_rst | ETCD 启动时不可用，进入延迟恢复状态 |
| timeout | 节点超时，未按时续约 |
| dead | 节点被判定为死亡 |

### 4.2 状态转换日志

```text
Mark ... as timeout.
A timed out cluster node was demoted to become a failed node: ...
```

说明：节点从 timeout 转换为 dead，会触发自动移除或缩容任务。

## 5. Scale Down Task 事件

### 5.1 提交任务

```text
Submit scale down task of ... with traceid ...
Write the scale down task of ... into etcd success with version ...
```

说明：当节点从 ring 中移除时，会提交 scale down task 进行元数据清理。

### 5.2 处理任务

```text
Begin to process voluntary scale down task
```

说明：节点开始执行自愿缩容任务。

### 5.3 任务冲突

```text
all scale down task is processing, no need to excute, skip
```

说明：已有 scale down 任务在执行，无需重复提交。

### 5.4 无处理节点

```text
no worker to handle scale down task, no need excute scale down task, erase del_node_info for ...
```

说明：没有可用节点处理缩容任务，可能删除 del_node_info 记录。

## 6. 网络故障事件

### 6.1 伪造 DELETE 事件

```text
Due to network failure, a fake node deletion event[key: ...] needs to be generated
```

说明：当 Worker 与 ETCD 断开时，本地生成伪造 DELETE 事件，触发状态更新。恢复后会重新注册。

## 7. 典型问题排查

### 7.1 Lease 频繁失效

排查：
- 检查 `Worker was hanged about ... ms` 日志。
- 检查系统负载和调度延迟。
- 检查 ETCD 集群健康状态。
- 检查 `heartbeat_interval_ms` 和 `node_timeout_s` 配置是否合理。

### 7.2 节点反复上下线

排查：
- 检查网络稳定性。
- 检查 lease TTL 设置。
- 检查是否有多个 Worker 使用相同 `worker_address`。

### 7.3 扩缩容任务卡住

排查：
- 检查 scale down task 写入日志。
- 检查是否有目标节点承担迁移。
- 检查 hash ring 版本是否一致。

## 8. 解析示例

### 统计 ETCD 事件类型

```bash
awk -F'|' '$10 ~ /DS_ETCD/ {print $10}' request_out.log | sort | uniq -c | sort -rn
```

### 提取 lease 相关日志

```bash
grep -E "Creating lease|Failed to refresh lease|etcd keep alive run failed" datasystem_worker.INFO.log
```

### 提取节点上下线事件

```bash
grep -E "Event Type: Add Node|Event Type: Remove Node" datasystem_worker.INFO.log
```

## 注意事项

- ETCD 事件分析应结合所有 Worker 和 Master 日志，按时间线串联。
- lease 失效是节点下线的根本原因，需要优先排查。
- 伪造 DELETE 事件只影响本地状态，不会真正删除 ETCD 中的数据。
- Metastore 方式下事件来源相同，但由主节点 Worker 内置服务提供。
