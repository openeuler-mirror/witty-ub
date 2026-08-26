---
name: "yuanrong-datasystem 共享内存日志模式"
description: "汇总 openYuanrong datasystem client-worker 共享内存通信的日志模式、字段含义和典型问题排查方法。"
keywords:
  - yuanrong-datasystem
  - datasystem
  - 共享内存
  - SCMTCP
  - UDS
  - mmap
  - fd 传递
  - client-worker
references:
  - name: "yuanrong-datasystem 0.8.1.rc20 Client-Worker 通用 API"
    type: offline
    source: "yuanrong-datasystem-0.8.1.rc20/src/datasystem/client/client_worker_common_api.cpp"
  - name: "yuanrong-datasystem 0.8.1.rc20 Worker 服务实现"
    type: offline
    source: "yuanrong-datasystem-0.8.1.rc20/src/datasystem/worker/worker_service_impl.cpp"
  - name: "yuanrong-datasystem 0.8.1.rc20 共享内存 mmap"
    type: offline
    source: "yuanrong-datasystem-0.8.1.rc20/src/datasystem/common/shared_memory/mmap/mem_mmap.cpp"
---

# yuanrong-datasystem 共享内存日志模式

## 概述

openYuanrong datasystem 默认通过共享内存（shared memory）实现 client-worker 零拷贝数据交换。本文档汇总共享内存 fd 传递、建立、使用和释放的日志模式。

## 1. 共享内存通道建立

### 1.1 Client 注册时启用共享内存

```text
Register client: ..., pod: ..., version: ..., socket fd: ..., shmEnabled: ...
Register client ... done, healthy: ...
```

说明：`shmEnabled` 表示该 Client 是否支持共享内存。

### 1.2 获取 fd 传递端点

```text
Try connect worker for shm fd transfer, endpoint: ...
```

说明：Client 尝试连接到 Worker 的 fd 传递端点（SCMTCP 或 UDS）。

### 1.3 连接成功

```text
Connects to local server ... successfully. Client fd ... Server fd ...
```

### 1.4 共享内存通道建立

```text
Client and worker support transfer data through shared memory and the fd send over SCMTCP, socketFd: ..., serverFd: ...
Client and worker support transfer data through shared memory and the fd send over UDS, socketFd: ..., serverFd: ...
```

## 2. fd 传递失败

### 2.1 无可用通道

```text
Both the uds socket path and shm_worker_port is empty, cannot transfer data through shm between client and worker.
```

可能原因：
- Worker 未启用 SCMTCP 或 UDS 通道。
- 部署配置中未设置 `shm_worker_port` 或 UDS 路径。

### 2.2 连接超时

```text
Client can not connect to server for shm fd transfer within allowed time (...ms).
```

可能原因：
- 网络/权限问题。
- Worker 负载高，响应慢。

### 2.3 fd 接收失败

```text
Recv fd failed
Fd ... has been released
```

可能原因：
- fd 在传递过程中被关闭。
- Client 或 Worker 进程异常退出。

## 3. 共享内存资源使用

### 3.1 资源日志字段

```text
shm_info: memoryUsage/physicalMemoryUsage/totalLimit/rate
Cache_Hit_Info: memHitNum/diskHitNum/l2HitNum/remoteHitNum/missNum
```

### 3.2 字段含义

| 字段 | 说明 |
|------|------|
| memoryUsage | 已分配内存大小（含 jemalloc 对齐开销） |
| physicalMemoryUsage | 已分配物理内存大小 |
| totalLimit | 共享内存总大小 |
| rate | 使用率 |
| memHitNum | 本地内存命中次数 |
| diskHitNum | 本地磁盘命中次数 |
| l2HitNum | 二级缓存命中次数 |
| remoteHitNum | 远端 worker 命中次数 |
| missNum | 未命中次数 |

## 4. mmap 相关日志

### 4.1 映射成功

具体日志依赖于 `mem_mmap.cpp` 实现，通常包含 mmap 地址和大小。

### 4.2 映射失败

```text
Failed to mmap ...
munmap failed ...
```

可能原因：
- 内存不足。
- 文件描述符无效。
- 映射大小超过限制。

## 5. 跨节点共享内存

跨节点 Client 访问 Worker 时，通常无法建立共享内存通道，数据会回退到：
- RPC（TCP）传输
- URMA/RDMA 传输（如果启用）

日志中可能看到：

```text
Both the uds socket path and shm_worker_port is empty, cannot transfer data through shm between client and worker.
```

## 6. 典型问题排查

### 6.1 共享内存未启用

排查：
- 检查 `ipc_through_shared_memory` 是否为 true。
- 检查 Worker 是否配置了 `shm_worker_port` 或 UDS 路径。
- 检查 Client 注册日志中 `shmEnabled` 是否为 true。

### 6.2 性能下降

排查：
- 检查 `resource.log` 中 `shm_info` 使用率是否接近上限。
- 检查 `Cache_Hit_Info` 中 `missNum` 是否增加。
- 检查是否大量请求回退到 RPC 传输。
- 检查 `payload_nocopy_threshold` 是否合理。

### 6.3 fd 传递失败

排查：
- 检查网络/权限。
- 检查 Worker 的 SCMTCP/UDS 配置。
- 检查 Client 和 Worker 是否在同一节点（UDS）或网络可达（SCMTCP）。

## 7. 解析示例

### 检查 Client 共享内存状态

```bash
grep "Register client:" datasystem_worker.INFO.log | head -10
```

### 检查 fd 传递成功日志

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

## 注意事项

- 共享内存 fd 传递失败不会导致 Client 注册失败，但会关闭零拷贝通道。
- 跨节点场景下共享内存不可用，应使用 RPC 或 RDMA 优化性能。
- 共享内存使用率接近上限时，会触发 LRU 淘汰，可能导致命中率下降。
- 分析性能问题时，应结合 `resource.log` 和访问日志共同分析。
- 大页（huge_tlb）启用时，需要系统配置大页支持。
