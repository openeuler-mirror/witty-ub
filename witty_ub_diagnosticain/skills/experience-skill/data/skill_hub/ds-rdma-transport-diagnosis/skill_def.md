---
name: ds-rdma-transport-diagnosis
description: >
  介绍 openYuanrong datasystem 中 RDMA/URMA 与 TCP 传输层的日志分析方法，覆盖 worker-worker 连接建立、
  Jetty 管理、连接失效重建、端口冲突和调度延迟挂起等典型问题。
license: MIT
compatibility: yuanrong-datasystem 0.8.1.rc20
metadata:
  author: yuanrong-datasystem-log-analysis
  version: "1.0"
  keywords: [yuanrong-datasystem, datasystem, RDMA, URMA, TCP, 传输层, Jetty, 连接重建, 端口冲突]
allowed-tools: Bash(grep:*) Bash(awk:*) Bash(sed:*) Bash(cat:*)
---

# yuanrong-datasystem RDMA/URMA 传输层诊断 Skill

## 概述

openYuanrong datasystem 的 worker-worker 传输支持 URMA/RDMA 和 TCP。URMA/RDMA 提供高速传输，但依赖 URMA 设备和链路稳定性；TCP 作为回退路径。传输层问题通常表现为连接建立失败、Jetty 失效、连接重建循环或进程挂起。

## 约束

- `enable_urma` 和 `enable_rdma` 控制是否启用高速传输，`enable_transport_fallback` 控制失败时是否回退 TCP。
- `urma_mode` 可为 "UB" 或 "IB"，影响设备选择。
- ZMQ 用于 RPC 和基础通信，端口冲突会导致服务启动失败。
- 传输层连接状态与 Worker 生命周期强相关，远端 Worker 重启会触发连接重建。

## 流程

1. 确认传输层配置（`enable_urma`、`enable_rdma`、`urma_mode`、`enable_transport_fallback`）。
2. 检查 worker-worker 连接建立日志（`[URMA_NEED_CONNECT]`、`WorkerWorkerExchangeUrmaConnectInfo`）。
3. 检查 Jetty 状态变化（`[URMA_MODIFY_JETTY_TO_ERROR]`、`Mark Jetty ... invalid`）。
4. 检查连接重建循环（`TryReconnectRemoteWorker`）。
5. 检查 ZMQ 端口绑定冲突（`ZMQ bind ... Address already in use`）。
6. 检查进程挂起（`Worker was hanged about ... ms`）。

## 能力

- 输出 URMA/RDMA 连接建立的日志模式。
- 输出 Jetty 失效与连接重建的日志模式。
- 输出 ZMQ 端口冲突和绑定失败的日志模式。
- 输出进程调度挂起与传输层超时的关系。
- 输出传输层回退 TCP 的判断方法。

## 规则

- 分析 URMA/RDMA 问题时，需要同时检查 URMA 驱动/设备日志和系统日志。
- Jetty 失效通常由远端 Worker 重启或网络抖动触发，需要观察是否自动恢复。
- 连接重建循环可能消耗大量 CPU，需要检查远端 Worker 状态。
- 端口冲突时，必须清理残留进程或更换端口。

## 关键日志模式

### 连接建立

```text
[URMA_NEED_CONNECT] No existing connection for remoteAddress: ..., remoteInstanceId=..., requires creation.
[URMA_NEED_CONNECT] WorkerWorkerExchangeUrmaConnectInfo start, peerAddress=...
[URMA_NEED_CONNECT] Worker-worker transport connection exchange success, elapsed ms: ...
[URMA_NEED_CONNECT] WorkerWorkerExchangeUrmaConnectInfo finish, elapsed ms: ...
```

### 连接检查失败

```text
[URMA_NEED_CONNECT] CheckConnectionStable failed, remoteAddress=..., rc=...
[URMA_NEED_CONNECT] Connection stale for remoteAddress: ..., cachedRemoteInstanceId=..., requestRemoteInstanceId=..., need reconnect.
[URMA_NEED_CONNECT] Connection unstable for remoteAddress: ..., remoteInstanceId=UNKNOWN, need to reconnect.
```

### Jetty 失效与重建

```text
[URMA_RECREATE_JETTY] Mark Jetty ... invalid, remoteAddress=..., remoteInstanceId=...
[URMA_MODIFY_JETTY_TO_ERROR] Mark Jetty ... invalid, remoteAddress=..., remoteInstanceId=...
Remove UrmaConnection for ...
Start import remote jetty, remote urma info: ...
```

### 远端重连

```text
[URMA_NEED_CONNECT] TryReconnectRemoteWorker triggered, remoteAddress=...
[URMA_NEED_CONNECT] TryReconnectRemoteWorker finished, remoteAddress=...
```

### ZMQ 端口冲突

```text
ZMQ bind to tcp://... unsuccessful: Address already in use
```

### 进程挂起

```text
Worker was hanged about ... ms
[URMA_ELAPSED_THREAD_SHED]: urma_poll_jfc thread wake up after nanosleep(1us) cost ...us, ...
```

## 解析示例

### 提取 URMA 连接建立与失败

```bash
grep -E "\[URMA_NEED_CONNECT\]" datasystem_worker.INFO.log | head -50
```

### 提取 Jetty 失效事件

```bash
grep -E "\[URMA_MODIFY_JETTY_TO_ERROR\]|\[URMA_RECREATE_JETTY\]|Remove UrmaConnection" datasystem_worker.INFO.log
```

### 检查 ZMQ 端口冲突

```bash
grep "ZMQ bind to tcp://.*unsuccessful: Address already in use" datasystem_worker.INFO.log
```

### 检查远端 Worker 重连情况

```bash
grep "TryReconnectRemoteWorker" datasystem_worker.INFO.log
```

## 常见错误码

| 错误码 | 含义 | 排查方向 |
|--------|------|----------|
| K_URMA_ERROR=1004 | URMA 通用错误 | 检查 URMA 设备和链路 |
| K_RDMA_ERROR=1005 | RDMA 通用错误 | 检查 RDMA 设备和链路 |
| K_URMA_NEED_CONNECT=1006 | 需要建立 URMA 连接 | 检查远端 Worker 是否可达 |
| K_RDMA_NEED_CONNECT=1007 | 需要建立 RDMA 连接 | 检查远端 Worker 是否可达 |
| K_URMA_TRY_AGAIN=1008 | URMA 暂时失败，需重试 | 检查设备状态和远端节点 |
| K_URMA_CONNECT_FAILED=1009 | URMA 连接失败 | 检查地址、设备、网络 |
| K_URMA_WAIT_TIMEOUT=1010 | URMA 等待超时 | 检查网络延迟和远端状态 |
| K_RPC_DEADLINE_EXCEEDED=1001 | RPC 超时 | 检查网络、负载、线程池 |
| K_RPC_UNAVAILABLE=1002 | 对端不可用 | 检查远端 Worker 是否存活 |

## 注意事项

- URMA/RDMA 连接建立失败时，如果 `enable_transport_fallback=true`，通常会回退到 TCP，但性能会下降。
- Jetty 失效后，系统会尝试重建，重建过程中请求可能延迟或失败。
- 远端 Worker 重启后，所有与之有连接的 Worker 都需要重建连接。
- `Worker was hanged about` 是调度问题，可能导致所有连接同时超时，包括 URMA 和 ETCD。
- 分析时应同时收集对端 Worker 的日志。
