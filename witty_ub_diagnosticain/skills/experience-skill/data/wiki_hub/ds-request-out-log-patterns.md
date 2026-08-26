---
name: "yuanrong-datasystem 请求第三方日志模式"
description: "汇总 openYuanrong datasystem 请求第三方日志（request_out.log）中 ETCD gRPC 请求的 action、status_code、关键参数与典型异常模式。"
keywords:
  - yuanrong-datasystem
  - datasystem
  - request_out
  - ETCD
  - gRPC
  - lease
  - cluster
  - status_code
references:
  - name: "yuanrong-datasystem 0.8.1.rc20 日志指南"
    type: offline
    source: "yuanrong-datasystem-0.8.1.rc20/docs/source_zh_cn/appendix/log_guide.md"
  - name: "yuanrong-datasystem 0.8.1.rc20 ETCD keepalive"
    type: offline
    source: "yuanrong-datasystem-0.8.1.rc20/src/datasystem/common/kvstore/etcd/etcd_keep_alive.cpp"
  - name: "yuanrong-datasystem 0.8.1.rc20 集群管理"
    type: offline
    source: "yuanrong-datasystem-0.8.1.rc20/docs/source_zh_cn/design_document/cluster_management.md"
---

# yuanrong-datasystem 请求第三方日志模式

## 概述

请求第三方日志（request_out.log）记录 Worker 访问外部组件的请求，当前主要接入 ETCD gRPC。通过分析 request_out 日志，可以定界 openYuanrong datasystem 与 ETCD 之间的交互是否正常。

## 日志字段

与访问日志格式一致：

```text
time | level | filename | pod_name | pid:tid | trace_id | cluster_name | status_code | action | cost | data_size | request_param | response_param
```

- `status_code`：0 成功，非 0 失败。
- `action`：ETCD 请求类型，如 `DS_ETCD_LEASE_GRANT`、`DS_ETCD_PUT`、`DS_ETCD_GET`、`DS_ETCD_DELETE`、`DS_ETCD_WATCH`。
- `request_param`：通常包含 `key` 字段。
- `cost`：请求耗时，单位 us。

## 常见 ETCD action

| action | 说明 | 典型场景 |
|--------|------|----------|
| `DS_ETCD_LEASE_GRANT` | 申请 lease | Worker 启动、续约失败重建 |
| `DS_ETCD_LEASE_KEEPALIVE` | lease 保活 | 心跳保活 |
| `DS_ETCD_PUT` | 写入 KV | 注册节点、写入 scale down task |
| `DS_ETCD_GET` | 读取 KV | 获取节点列表、元数据 |
| `DS_ETCD_DELETE` | 删除 KV | 节点下线、lease 过期 |
| `DS_ETCD_WATCH` | 监听前缀 | 监听集群事件、节点变化 |

## 典型日志模式

### 1. lease 申请成功

```text
action=DS_ETCD_LEASE_GRANT status_code=0 cost=...
```

Worker 成功从 ETCD 获取 lease，开始注册节点。

### 2. lease 保活失败

```text
action=DS_ETCD_LEASE_KEEPALIVE status_code=... cost=...
```

可能原因：
- ETCD 网络延迟或不可用。
- Worker 进程挂起（OS 调度延迟），导致保活无法及时发送。
- lease TTL 被置为 0（ETCD 返回 `the new ttl is 0`）。

排查：
- 检查运行日志 `etcd keep alive run failed` 相关错误。
- 检查 `cost` 是否异常增大。
- 检查系统负载和调度延迟。

### 3. PUT 写入节点信息

```text
action=DS_ETCD_PUT status_code=0 cost=... request_param=key=...
```

Worker 将自身节点信息写入 ETCD，建立集群成员关系。

### 4. WATCH 事件触发

```text
action=DS_ETCD_WATCH status_code=0 cost=...
```

Master 或 Worker 通过 WATCH 监听集群事件，如节点上下线。

### 5. GET 节点列表

```text
action=DS_ETCD_GET status_code=0 cost=... request_param=key=...
```

用于获取当前集群节点列表或元数据。

## 典型异常模式

### 1. ETCD 不可达（K_RPC_UNAVAILABLE）

```text
action=DS_ETCD_LEASE_KEEPALIVE status_code=1002 cost=...
```

可能原因：
- ETCD 集群异常。
- Worker 与 ETCD 网络断开。
- DNS 解析失败或地址配置错误。

排查：
- 检查 `etcd_address` gflag 是否正确。
- 从 Worker 节点测试 ETCD 连通性。
- 检查 ETCD 集群健康状态。

### 2. ETCD 请求超时（K_RPC_DEADLINE_EXCEEDED）

```text
action=DS_ETCD_PUT status_code=1001 cost=...
```

可能原因：
- ETCD 负载高或网络拥塞。
- 请求参数过大（如批量写入）。

排查：
- 检查 ETCD 集群 QPS 和延迟。
- 拆分大批量请求。
- 调整 gRPC 超时配置。

### 3. lease TTL 异常

运行日志中常见：

```text
Failed to refresh lease: the new ttl is 0.
etcd keep alive run failed, keep alive timer ElapsedMilliSecond: ...
```

对应 request_out 中可能出现多次失败的 `DS_ETCD_LEASE_KEEPALIVE`。

可能原因：
- Worker 进程被挂起，导致 lease 无法续约。
- ETCD 集群时间/lease 机制异常。
- 网络分区导致 lease 在 ETCD 端已过期。

排查：
- 检查运行日志中 `Worker was hanged about ... ms`。
- 检查系统调度延迟（如 CPU 抢占、cgroup 限制）。
- 检查 ETCD 集群日志。

## 解析示例

### 统计 ETCD 请求失败类型

```bash
awk -F'|' '$10 ~ /DS_ETCD/ && $9 != 0 {print $10, $9}' request_out.log | sort | uniq -c | sort -rn
```

### 提取 lease 相关请求耗时趋势

```bash
awk -F'|' '$10 ~ /DS_ETCD_LEASE/ {print $1, $10, $11}' request_out.log | tail -100
```

### 查找 ETCD 请求耗时异常点

```bash
awk -F'|' '$10 ~ /DS_ETCD/ && $11 > 1000000 {print $1, $10, $11, $9}' request_out.log
```

## 注意事项

- request_out.log 主要反映 Worker 与 ETCD 的交互，不包含 Client 与 Worker 的交互。
- lease 相关错误通常会导致节点被标记为 timeout/dead，进而触发集群重平衡。
- 分析时应结合运行日志中 `etcd_keep_alive.cpp` 和 `cluster_manager.cpp` 的输出。
- ETCD 请求 `cost` 持续升高，可能是集群不稳定的前兆。
