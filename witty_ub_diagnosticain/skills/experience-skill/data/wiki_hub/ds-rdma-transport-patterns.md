---
name: "yuanrong-datasystem RDMA/URMA 传输日志模式"
description: "汇总 openYuanrong datasystem 中 RDMA/URMA 与 TCP 传输层的日志模式、错误码和典型问题排查方法。"
keywords:
  - yuanrong-datasystem
  - datasystem
  - RDMA
  - URMA
  - TCP
  - 传输层
  - Jetty
  - 连接重建
references:
  - name: "yuanrong-datasystem 0.8.1.rc20 URMA 管理器"
    type: offline
    source: "yuanrong-datasystem-0.8.1.rc20/src/datasystem/common/rdma/urma_manager.cpp"
  - name: "yuanrong-datasystem 0.8.1.rc20 Worker-Worker 传输 API"
    type: offline
    source: "yuanrong-datasystem-0.8.1.rc20/src/datasystem/worker/object_cache/worker_worker_transport_api.cpp"
  - name: "yuanrong-datasystem 0.8.1.rc20 ZMQ Socket 实现"
    type: offline
    source: "yuanrong-datasystem-0.8.1.rc20/src/datasystem/common/rpc/zmq/zmq_socket_ref.cpp"
---

# yuanrong-datasystem RDMA/URMA 传输日志模式

## 概述

openYuanrong datasystem 的 worker-worker 高速传输层支持 URMA/RDMA，失败时可回退 TCP。本文档汇总传输层日志模式，帮助定位连接建立、连接失效、端口冲突和调度挂起等问题。

## 1. 连接建立

### 1.1 需要新建连接

```text
[URMA_NEED_CONNECT] No existing connection for remoteAddress: ..., remoteInstanceId=..., requires creation.
```

说明：本地没有到远端 Worker 的 URMA 连接，需要新建。

### 1.2 连接交换开始

```text
[URMA_NEED_CONNECT] WorkerWorkerExchangeUrmaConnectInfo start, peerAddress=...
```

### 1.3 连接交换成功

```text
[URMA_NEED_CONNECT] Worker-worker transport connection exchange success, elapsed ms: ...
[URMA_NEED_CONNECT] WorkerWorkerExchangeUrmaConnectInfo finish, elapsed ms: ...
```

## 2. 连接检查失败

### 2.1 连接不存在

```text
[URMA_NEED_CONNECT] No existing connection for remoteAddress: ..., remoteInstanceId=..., requires creation.
```

### 2.2 连接陈旧

```text
[URMA_NEED_CONNECT] Connection stale for remoteAddress: ..., cachedRemoteInstanceId=..., requestRemoteInstanceId=..., need reconnect.
```

说明：远端 Worker 实例 ID 发生变化（如重启），需要重新连接。

### 2.3 连接不稳定

```text
[URMA_NEED_CONNECT] Connection unstable for remoteAddress: ..., remoteInstanceId=UNKNOWN, need to reconnect.
[URMA_NEED_CONNECT] CheckConnectionStable failed, remoteAddress=..., rc=...
```

## 3. Jetty 失效与重建

### 3.1 标记 Jetty 失效

```text
[URMA_RECREATE_JETTY] Mark Jetty ... invalid, remoteAddress=..., remoteInstanceId=...
[URMA_MODIFY_JETTY_TO_ERROR] Mark Jetty ... invalid, remoteAddress=..., remoteInstanceId=...
```

说明：Jetty 是 URMA 连接端点，失效后会触发重建或连接移除。

### 3.2 移除连接

```text
Remove UrmaConnection for ...
```

### 3.3 导入远端 Jetty

```text
Start import remote jetty, remote urma info: ..., local address: ...
```

## 4. 远端重连

### 4.1 触发重连

```text
[URMA_NEED_CONNECT] TryReconnectRemoteWorker triggered, remoteAddress=...
```

### 4.2 重连完成

```text
[URMA_NEED_CONNECT] TryReconnectRemoteWorker finished, remoteAddress=...
```

## 5. ZMQ 端口冲突

### 5.1 绑定失败

```text
ZMQ bind to tcp://... unsuccessful: Address already in use
```

可能原因：
- 上次 Worker 进程未完全退出。
- 其他进程占用了该端口。

排查：
- 使用 `ss -tlnp` 或 `lsof` 检查端口占用。
- 清理残留进程或更换端口。

## 6. 进程调度挂起

### 6.1 Worker 挂起

```text
Worker was hanged about ... ms
```

说明：Worker 进程被 OS 调度挂起，影响所有线程包括 URMA poll 线程。

### 6.2 URMA poll 线程调度延迟

```text
[URMA_ELAPSED_THREAD_SHED]: urma_poll_jfc thread wake up after nanosleep(1us) cost ...us, ...
```

说明：URMA poll 线程实际睡眠时间远长于预期，通常由 CPU 调度延迟导致。

## 7. 常见错误码

| 错误码 | 含义 | 排查方向 |
|--------|------|----------|
| K_URMA_ERROR=1004 | URMA 通用错误 | 检查 URMA 设备和链路 |
| K_RDMA_ERROR=1005 | RDMA 通用错误 | 检查 RDMA 设备和链路 |
| K_URMA_NEED_CONNECT=1006 | 需要建立 URMA 连接 | 检查远端 Worker 是否可达 |
| K_RDMA_NEED_CONNECT=1007 | 需要建立 RDMA 连接 | 检查远端 Worker 是否可达 |
| K_URMA_TRY_AGAIN=1008 | URMA 暂时失败 | 检查设备状态和远端节点 |
| K_URMA_CONNECT_FAILED=1009 | URMA 连接失败 | 检查地址、设备、网络 |
| K_URMA_WAIT_TIMEOUT=1010 | URMA 等待超时 | 检查网络延迟和远端状态 |
| K_RPC_DEADLINE_EXCEEDED=1001 | RPC 超时 | 检查网络、负载、线程池 |
| K_RPC_UNAVAILABLE=1002 | 对端不可用 | 检查远端 Worker 是否存活 |

## 8. 典型问题排查

### 8.1 连接频繁重建

排查：
- 检查远端 Worker 是否稳定。
- 检查 URMA 设备和链路是否稳定。
- 检查网络是否有抖动或丢包。
- 检查 `urma_poll_size` 和 `urma_mode` 配置。

### 8.2 传输性能下降

排查：
- 检查是否大量回退到 TCP（`enable_transport_fallback`）。
- 检查 URMA 连接是否频繁失效和重建。
- 检查 `resource.log` 中相关线程池利用率。

### 8.3 端口冲突导致服务无法启动

排查：
- 查找 `ZMQ bind ... unsuccessful` 日志。
- 使用 ss/lsof 定位占用进程。
- 清理残留进程或更换端口配置。

## 9. 解析示例

### 提取 URMA 连接相关日志

```bash
grep "\[URMA_NEED_CONNECT\]" datasystem_worker.INFO.log | head -50
```

### 提取 Jetty 失效事件

```bash
grep -E "\[URMA_MODIFY_JETTY_TO_ERROR\]|\[URMA_RECREATE_JETTY\]" datasystem_worker.INFO.log
```

### 检查 ZMQ 端口冲突

```bash
grep "ZMQ bind to tcp://.*unsuccessful: Address already in use" datasystem_worker.INFO.log
```

## 注意事项

- URMA/RDMA 连接建立是按需的，首次访问远端 Worker 时才会触发。
- 远端 Worker 重启后，所有与其有连接的 Worker 都需要重建连接。
- 连接重建期间请求可能延迟或失败，应用层应做好重试。
- 进程挂起问题需要从 OS 层面排查，不是传输层本身的错误。
- 分析时应同时收集对端 Worker 的日志和 URMA 驱动日志。
