---
name: "yuanrong-datasystem Client 错误模式"
description: "汇总 openYuanrong datasystem 客户端（SDK）常见错误日志模式、错误码、根因与排查方向。"
keywords:
  - yuanrong-datasystem
  - datasystem
  - client
  - SDK
  - 错误模式
  - status_code
  - 注册失败
  - 重连
references:
  - name: "yuanrong-datasystem 0.8.1.rc20 Client 连接实现"
    type: offline
    source: "yuanrong-datasystem-0.8.1.rc20/src/datasystem/client/client_worker_common_api.cpp"
  - name: "yuanrong-datasystem 0.8.1.rc20 错误码定义"
    type: offline
    source: "yuanrong-datasystem-0.8.1.rc20/include/datasystem/utils/status.h"
---

# yuanrong-datasystem Client 错误模式

## 概述

Client 错误通常发生在初始化、连接 Worker、注册、接口调用和共享内存通信阶段。本文档汇总常见错误模式、日志特征和排查方向。

## 1. 初始化与连接失败

### 1.1 无法获取 Worker 地址

```text
The total timeout is ... ms, single rpc timeout is ... ms
Get socket path failed.
```

可能原因：
- Worker 地址配置错误。
- Worker 尚未启动或监听失败。
- 网络不可达。

排查：
- 确认 `worker_address` 或 `hostPort` 配置。
- 检查 Worker 是否启动并监听对应端口。
- 从 Client 节点测试 Worker 端口连通性。

### 1.2 连接 Worker 超时

```text
Client can not connect to server for shm fd transfer within allowed time (...ms).
```

可能原因：
- Worker 负载高，响应慢。
- 网络延迟或丢包。
- 防火墙/安全组限制。

排查：
- 增加 connect timeout。
- 检查 Worker 线程池利用率。
- 检查网络质量和防火墙策略。

## 2. 注册失败

### 2.1 Worker 正在退出

```text
Register client failed because worker is exiting and unhealthy now
```

可能原因：
- Worker 正在优雅关闭或异常退出。
- Worker 健康检查失败。

排查：
- 检查 Worker 日志中的退出原因。
- 等待 Worker 重启后重新连接。

### 2.2 版本不匹配

```text
status_code=28 action=...
```

可能原因：
- Client 与 Worker 版本不兼容。
- 升级过程中版本混部。

排查：
- 统一 Client 和 Worker 版本。
- 查看版本兼容性说明。

### 2.3 参数非法

```text
status_code=2 action=...
```

可能原因：
- 请求参数超出范围或为空。
- 对象 key 格式非法。

排查：
- 检查请求参数。
- 确认对象 key 长度和命名规则。

## 3. 共享内存通信失败

### 3.1 共享内存未启用

```text
Both the uds socket path and shm_worker_port is empty, cannot transfer data through shm between client and worker.
```

可能原因：
- Worker 未启用共享内存 fd 传递通道。
- 部署配置中未设置 `shm_worker_port` 或 UDS 路径。

排查：
- 检查 Worker 配置是否启用 SCMTCP 或 UDS。
- 确认 `ipc_through_shared_memory` 为 true。

### 3.2 fd 传递失败

```text
Recv fd failed
Fd ... has been released
```

可能原因：
- fd 在传递过程中被关闭或释放。
- Client 或 Worker 进程异常退出。

排查：
- 检查 Client 和 Worker 进程是否存活。
- 查看共享内存 mmap 相关日志。

## 4. 接口请求错误

### 4.1 对象/资源不存在（K_NOT_FOUND=3）

可能原因：
- 对象确实未创建。
- 对象所在 Worker 已下线或元数据未迁移。

排查：
- 确认对象是否已创建。
- 检查对象所在 Worker 状态。
- 检查 L2 缓存配置。

### 4.2 超时（K_RPC_DEADLINE_EXCEEDED=1001 / K_WORKER_TIMEOUT=24）

可能原因：
- Worker 负载高。
- 网络延迟。
- 远端对象获取慢。

排查：
- 检查 Worker 线程池和队列。
- 检查网络质量。
- 增加接口超时时间。

### 4.3 资源不足（K_OUT_OF_MEMORY=6 / K_NO_SPACE=13 / K_LRU_HARD_LIMIT=34）

可能原因：
- Worker 共享内存或 Spill 磁盘耗尽。
- 缓存对象过多触发 LRU 硬限制。

排查：
- 查看 `resource.log` 中资源使用情况。
- 调整缓存容量或淘汰策略。
- 考虑扩容。

### 4.4 连接断开（K_CLIENT_WORKER_DISCONNECT=23）

可能原因：
- Client 与 Worker 之间的网络断开。
- Worker 异常退出。
- Client 心跳超时。

排查：
- 检查网络连接。
- 检查 Worker 是否存活。
- 检查 `client_dead_timeout_s` 和心跳配置。

## 5. 重连与恢复

### 5.1 正常断开通知

```text
Client ... sends exit notice to worker.
```

说明 Client 正常销毁，会通知 Worker 清理资源。

### 5.2 异常断开

如果未看到 `sends exit notice`，可能是 Client 异常退出或崩溃。Worker 会在 `client_dead_timeout_s` 后清理资源。

## 6. 排查命令

### 统计 Client 错误码

```bash
awk -F'|' '$9 != 0 {print $9}' ds_client_access_*.log | sort | uniq -c | sort -rn
```

### 提取注册失败日志

```bash
grep -E "Register client failed|Register client.*failed" ds_client_*.INFO.log
```

### 检查共享内存状态

```bash
grep -E "support transfer data through shared memory|shm_worker_port|Fd.*has been released" ds_client_*.INFO.log
```

## 注意事项

- Client 日志分散在多个 `ds_client_{pid}.INFO.log` 文件中，分析前需确认对应进程。
- Embedded Client 与 Worker 同进程，日志可能混合在 Worker 日志中。
- 共享内存 fd 传递失败时，通常会自动回退到 RPC 传输，但会影响性能。
- 版本不匹配错误通常优先出现在注册阶段，而不是请求阶段。
