---
name: "yuanrong-datasystem Worker 错误模式"
description: "汇总 openYuanrong datasystem Worker 常见错误日志模式、错误码、根因与排查方向。"
keywords:
  - yuanrong-datasystem
  - datasystem
  - worker
  - 错误模式
  - status_code
  - lease
  - ETCD
  - 启动失败
  - ZMQ
references:
  - name: "yuanrong-datasystem 0.8.1.rc20 Worker 主入口"
    type: offline
    source: "yuanrong-datasystem-0.8.1.rc20/src/datasystem/worker/worker.cpp"
  - name: "yuanrong-datasystem 0.8.1.rc20 ETCD 存储实现"
    type: offline
    source: "yuanrong-datasystem-0.8.1.rc20/src/datasystem/common/kvstore/etcd/etcd_store.cpp"
  - name: "yuanrong-datasystem 0.8.1.rc20 错误码定义"
    type: offline
    source: "yuanrong-datasystem-0.8.1.rc20/include/datasystem/utils/status.h"
---

# yuanrong-datasystem Worker 错误模式

## 概述

Worker 错误通常发生在启动、集群注册、lease 保活、服务监听、Client 注册和后台线程运行阶段。本文档汇总常见错误模式、日志特征和排查方向。

## 1. 启动失败

### 1.1 地址参数错误

```text
Cannot get worker address.
Worker address is invalid
Bind address is invalid
Master address is invalid
```

可能原因：
- `worker_address`、`bind_address` 或 `master_address` 参数缺失或格式错误。

排查：
- 确认地址格式为 `ip:port`。
- 检查启动命令或配置文件。

### 1.2 日志目录不可写

```text
Failed to initialize log directory: ...
```

可能原因：
- `log_dir` 路径不存在或权限不足。
- 磁盘空间不足。

排查：
- 检查目录权限和磁盘空间。
- 使用默认日志目录验证。

### 1.3 RocksDB 初始化失败

```text
Failed to initialize the rocksdb database in advance.
Rocksdb has been initialized.
```

可能原因：
- 数据目录损坏或权限不足。
- 多进程同时初始化同一目录。

排查：
- 检查 `rocksdb_store_dir` 目录权限。
- 清理损坏的 RocksDB 数据目录（注意备份）。

## 2. 集群注册与 lease 失败

### 2.1 ETCD 不可达

```text
Could not initialize lease keepalive
etcd keep alive run failed, keep alive timer ElapsedMilliSecond: ...
```

可能原因：
- `etcd_address` 配置错误。
- ETCD 集群不可用。
- 网络不可达或防火墙限制。

排查：
- 检查 `etcd_address` 配置。
- 从 Worker 节点测试 ETCD 连通性。
- 检查 ETCD 集群健康状态。

### 2.2 lease TTL 异常

```text
Failed to refresh lease: the new ttl is 0.
```

可能原因：
- Worker 进程被挂起，无法及时续约。
- ETCD 集群时间或 lease 机制异常。
- 网络分区导致 lease 在 ETCD 端已过期。

排查：
- 检查是否出现 `Worker was hanged about ... ms`。
- 检查系统调度延迟（CPU 抢占、cgroup 限制）。
- 检查 ETCD 集群日志。

### 2.3 节点被标记为 timeout/dead

```text
Mark ... as timeout.
A timed out cluster node was demoted to become a failed node: ...
```

可能原因：
- 节点 lease 失效。
- 节点长时间未上报心跳。

排查：
- 检查该节点 Worker 进程是否存活。
- 检查网络和 ETCD 状态。
- 检查 `node_timeout_s` 和 `node_dead_timeout_s` 配置。

## 3. 服务监听失败

### 3.1 ZMQ 端口冲突

```text
ZMQ bind to tcp://... unsuccessful: Address already in use
```

可能原因：
- 上次 Worker 进程未完全退出，端口仍被占用。
- 其他进程占用了该端口。

排查：
- 使用 `ss -tlnp` 或 `lsof` 查找占用端口的进程。
- 等待上次进程完全退出或 kill 残留进程。
- 更换 `worker_address` 或相关端口。

### 3.2 服务初始化失败

```text
worker_->Init() failed
worker_->Start() failed
```

可能原因：
- 依赖组件初始化失败（如共享内存、RocksDB、RPC server）。
- 参数配置错误。

排查：
- 查看更详细的 ERROR 日志。
- 检查依赖组件状态。

## 4. Client 注册失败

### 4.1 Worker 不健康

```text
Register client failed because worker is exiting and unhealthy now
```

可能原因：
- Worker 正在关闭或处于不健康状态。
- Worker 初始化未完成。

排查：
- 检查 Worker 健康状态。
- 等待 Worker 启动完成后再连接。

### 4.2 版本不匹配

```text
Register client ... failed: version mismatch
```

可能原因：
- Client 与 Worker 版本不兼容。

排查：
- 统一 Client 和 Worker 版本。

## 5. 后台线程异常

### 5.1 Worker 进程挂起

```text
Worker was hanged about ... ms
```

可能原因：
- OS 调度延迟（CPU 抢占、内存回收、内核锁等）。
- cgroup CPU 限制或 throttling。
- 内核/驱动问题。

排查：
- 检查系统负载、CPU throttling、内存回收。
- 检查 dmesg、systemd 日志。
- 检查是否有 cgroup 限制。

### 5.2 URMA 连接异常

```text
[URMA_NEED_CONNECT] No existing connection for remoteAddress: ...
[URMA_MODIFY_JETTY_TO_ERROR] Mark Jetty ... invalid
Remove UrmaConnection for ...
```

可能原因：
- 远端 Worker 不可达或重启。
- URMA 网络/设备异常。
- Jetty 连接不稳定。

排查：
- 检查远端 Worker 状态。
- 检查 URMA 设备和链路。
- 查看 `ds-rdma-transport-diagnosis` Skill 详细分析。

## 6. 常见错误码

| 错误码 | 含义 | 排查方向 |
|--------|------|----------|
| K_INVALID=2 | 参数非法 | 检查启动参数和请求参数 |
| K_KVSTORE_ERROR=4 | KV 存储错误 | 检查 ETCD/Metastore 状态 |
| K_RUNTIME_ERROR=5 | 通用运行时错误 | 查看上下文日志 |
| K_OUT_OF_MEMORY=6 | 内存不足 | 检查共享内存、物理内存 |
| K_NOT_READY=8 | 资源未就绪 | 检查依赖组件是否启动完成 |
| K_NOT_LEADER_MASTER=14 | 非 leader master | 检查 master 选举 |
| K_SHUTTING_DOWN=21 | 正在关闭 | 正常或异常关闭 |
| K_WORKER_ABNORMAL=22 | Worker 异常 | 检查 Worker 健康状态 |
| K_RPC_DEADLINE_EXCEEDED=1001 | RPC 超时 | 检查网络、负载、线程池 |
| K_RPC_UNAVAILABLE=1002 | 对端不可用 | 检查对端是否存活 |
| K_URMA_NEED_CONNECT=1006 | 需要建立 URMA 连接 | 检查远端 Worker 和 URMA 链路 |

## 7. 排查命令

### 提取 Worker 启动失败原因

```bash
grep -E "ERROR|FATAL" datasystem_worker.INFO.log | head -20
```

### 检查 lease 状态

```bash
grep -E "Creating lease|Failed to refresh lease|etcd keep alive run failed|Mark.*as timeout" datasystem_worker.INFO.log
```

### 检查端口占用

```bash
ss -tlnp | grep 31501
lsof -i :31501
```

### 检查 Worker 是否被挂起

```bash
grep "Worker was hanged about" datasystem_worker.INFO.log
```

## 注意事项

- Worker 异常退出前通常有 ERROR 或 FATAL 日志，但 `kill -9` 或 OOM killer 终止时可能没有。
- lease 失效是 Worker 被集群移除的主要原因，常与进程挂起或网络问题相关。
- 多节点问题分析时，需要同时收集相关 Worker 和 Client 日志，按时间线串联。
- 非默认 gflags 可能引入异常行为，启动日志中的 `Worker non-default flags` 应重点关注。
