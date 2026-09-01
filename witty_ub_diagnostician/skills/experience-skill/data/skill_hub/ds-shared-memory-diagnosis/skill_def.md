---
name: ds-shared-memory-diagnosis
description: >
  介绍 openYuanrong datasystem 中 client-worker 共享内存通信的日志分析方法，覆盖 SCMTCP/UDS fd 传递、
  mmap 映射、共享内存生命周期、跨节点访问和本地/远端命中判断。
license: MIT
compatibility: yuanrong-datasystem 0.8.1.rc20
metadata:
  author: yuanrong-datasystem-log-analysis
  version: "1.0"
  keywords: [yuanrong-datasystem, datasystem, 共享内存, SCMTCP, UDS, mmap, fd 传递, client-worker]
allowed-tools: Bash(grep:*) Bash(awk:*) Bash(sed:*) Bash(cat:*)
---

# yuanrong-datasystem 共享内存诊断 Skill

## 概述

openYuanrong datasystem 默认通过共享内存（shared memory）在 client 与 worker 之间交换数据，实现零拷贝。共享内存通道建立依赖 SCMTCP 或 UDS 进行 fd 传递，失败时回退到 RPC 传输。分析共享内存日志对于定位零拷贝失效、性能下降和跨节点访问问题非常重要。

## 约束

- `ipc_through_shared_memory` 控制是否启用共享内存，默认 true。
- `shared_memory_distribution_policy` 控制 NUMA 分布策略。
- SCMTCP 用于跨节点（或同节点 TCP），UDS 用于同节点 Unix Domain Socket。
- 大对象/零拷贝受 `payload_nocopy_threshold` 和 `shm_threshold` 影响。
- fd 传递失败不会导致 Client 注册失败，但会关闭零拷贝通道。

## 流程

1. 检查 Client 是否支持共享内存（`Register client: ..., shmEnabled: ...`）。
2. 检查 fd 传递通道是否建立（`Connects to local server ...`、`Client and worker support transfer data through shared memory`）。
3. 检查共享内存映射和使用情况（`resource.log` 中 `shm_info`）。
4. 检查 mmap 相关错误和 fd 释放日志（`Fd ... has been released`）。
5. 跨节点访问时，检查是否回退到 RPC 或 URMA/RDMA。
6. 性能下降时，检查共享内存命中率和零拷贝阈值。

## 能力

- 输出 Client-Worker 共享内存建立流程的日志模式。
- 输出 SCMTCP/UDS fd 传递失败的日志模式。
- 输出共享内存资源使用和命中率的分析方法。
- 输出跨节点共享内存不可用的判断方法。
- 输出共享内存与性能下降的关系分析。

## 规则

- 分析共享内存问题时，应同时查看 Client 和 Worker 的日志。
- 共享内存 fd 传递失败常见原因是网络/权限问题或 Worker 未配置 fd 通道。
- 共享内存使用率接近上限会触发 LRU 淘汰或 spill，影响性能。
- 跨节点场景下，共享内存通常不可用，会回退到 RPC/RDMA。

## 关键日志模式

### Client 注册与共享内存支持

```text
Register client: ..., pod: ..., version: ..., socket fd: ..., shmEnabled: ...
Register client ... done, healthy: ...
```

### fd 传递通道建立

```text
Try connect worker for shm fd transfer, endpoint: ...
Connects to local server ... successfully. Client fd ... Server fd ...
Client and worker support transfer data through shared memory and the fd send over SCMTCP, socketFd: ..., serverFd: ...
Client and worker support transfer data through shared memory and the fd send over UDS, socketFd: ..., serverFd: ...
```

### fd 传递失败

```text
Both the uds socket path and shm_worker_port is empty, cannot transfer data through shm between client and worker.
Client can not connect to server for shm fd transfer within allowed time (...ms).
Recv fd failed
Fd ... has been released
```

### 共享内存资源

```text
shm_info: memoryUsage/physicalMemoryUsage/totalLimit/rate
Cache_Hit_Info: memHitNum/diskHitNum/l2HitNum/remoteHitNum/missNum
```

### mmap 相关

```text
Failed to mmap ...
munmap failed ...
```

说明：具体日志取决于 `mem_mmap.cpp` 实现。

## 解析示例

### 检查 Client 是否启用了共享内存

```bash
grep "Register client:" datasystem_worker.INFO.log | head -10
```

### 检查共享内存 fd 传递成功情况

```bash
grep "Client and worker support transfer data through shared memory" ds_client_*.INFO.log
```

### 检查共享内存使用率

```bash
awk -F'|' '{print $1, $8}' resource.log | tail -100
```

### 检查缓存命中率

```bash
awk -F'|' '{print $1, $30}' resource.log | tail -100
```

## 常见错误码

| 错误码 | 含义 | 排查方向 |
|--------|------|----------|
| K_INVALID=2 | 参数非法 | 检查共享内存相关参数 |
| K_OUT_OF_MEMORY=6 | 内存不足 | 检查共享内存配额和物理内存 |
| K_NO_SPACE=13 | 空间不足 | 检查共享内存总限制 |
| K_NOT_READY=8 | 资源未就绪 | 检查共享内存是否初始化完成 |
| K_CLIENT_WORKER_DISCONNECT=23 | 连接断开 | 检查 fd 通道和心跳 |
| K_RPC_DEADLINE_EXCEEDED=1001 | RPC 超时 | 共享内存不可用，回退 RPC 超时 |

## 注意事项

- 共享内存 fd 传递依赖额外的端口（SCMTCP）或 UDS 路径，部署时需要确保可达。
- `payload_nocopy_threshold` 决定多大对象触发零拷贝，过小可能导致频繁拷贝，过大可能导致共享内存压力。
- 跨节点 Client 访问 Worker 时，共享内存通常不可用，数据会通过 RPC 或 URMA/RDMA 传输。
- 共享内存使用率持续升高时，可能触发 LRU 淘汰，导致命中率下降。
- 分析性能问题时，应结合 `resource.log` 中的 `shm_info` 和 `Cache_Hit_Info`。
