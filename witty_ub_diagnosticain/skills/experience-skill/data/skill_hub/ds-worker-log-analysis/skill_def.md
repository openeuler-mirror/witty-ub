---
name: ds-worker-log-analysis
description: >
  介绍 openYuanrong datasystem Worker 运行日志（datasystem_worker.INFO.log）的分析方法，
  覆盖 Worker 启动、参数加载、注册到集群、服务启动、后台线程、异常退出与重启恢复。
license: MIT
compatibility: yuanrong-datasystem 0.8.1.rc20
metadata:
  author: yuanrong-datasystem-log-analysis
  version: "1.0"
  keywords: [yuanrong-datasystem, datasystem, worker, 日志分析, 启动, 注册, ETCD, lease, 异常退出]
allowed-tools: Bash(grep:*) Bash(awk:*) Bash(sed:*) Bash(cat:*)
---

# yuanrong-datasystem Worker 日志分析 Skill

## 概述

Worker 运行日志（`datasystem_worker.INFO.log`）是定位服务端问题的核心。日志覆盖启动、参数加载、集群注册、服务监听、客户端注册、后台线程、异常退出与重启恢复等完整生命周期。

## 约束

- Worker 启动依赖 `worker_address`、`bind_address`、`master_address`、`etcd_address` 等参数。
- 日志目录默认为 `~/.datasystem/logs/worker`，可通过 `log_dir` 覆盖。
- Worker 进程退出时可能触发 lease 失效，导致集群重平衡。
- 重启 Worker 时会根据本地状态判断是否需要进行恢复/协调。

## 流程

1. 检查 Worker 启动日志，确认版本、地址、master/etcd 地址。
2. 检查 `Worker non-default flags` 中的非默认配置，确认关键参数。
3. 检查 ETCD/Metastore 注册流程（`Sending cluster node to etcd`、`Creating lease`）。
4. 检查服务启动成功（`worker_->Init()`、`worker_->Start()`）。
5. 检查 Client 注册情况（`Register client: ...`）。
6. 异常退出时，检查最后 ERROR/FATAL 日志、lease 失效、信号处理。

## 能力

- 输出 Worker 启动与参数加载的日志模式。
- 输出 Worker 注册到集群和 lease 保活的日志模式。
- 输出 Client 注册与服务启动的日志模式。
- 输出 Worker 异常退出、重启恢复的日志模式。
- 输出常见 Worker 错误码与排查方向。

## 规则

- 分析 Worker 日志时应同时查看同节点的 `container.log` 和系统日志（如 dmesg、systemd）。
- 注意 Worker 启动时间，区分正常重启和异常退出后的重启。
- 非默认 gflags 可能引入异常行为，启动日志中需重点关注。
- 异常退出前通常有 ERROR 或 FATAL 日志，但进程被 kill -9 时可能没有。

## 关键日志模式

### 启动与参数

```text
Git Commit: ... ; Git Branch: ...
Worker non-default flags:
GOT MASTER ADDRESS: ... at worker: ... bind on: ...
Using external etcd: ...
AsyncResourceReleaser initialized
```

### 集群注册与 lease

```text
Starting KeepAlive monitoring thread
Creating lease with expiry time: ...
Sending cluster node to etcd and establish lease.
Creating new lease KeepAlive object for lease ... with heartbeat interval timeout: ...
```

### 服务启动

```text
Did not restart so no need to reconcile. Set health file.
```

说明：Worker 首次启动或正常重启时不需要协调，直接设置健康文件。

### Client 注册

```text
Register client: ..., pod: ..., version: ..., socket fd: ..., shmEnabled: ...
Register client ... done, healthy: ...
Register client failed because worker is exiting and unhealthy now
```

### 异常退出

```text
Failed to refresh lease: the new ttl is 0.
etcd keep alive run failed, keep alive timer ElapsedMilliSecond: ...
ZMQ bind to tcp://... unsuccessful: Address already in use
Worker was hanged about ... ms
```

## 解析示例

### 提取 Worker 启动时间线

```bash
grep -E "Git Commit|GOT MASTER ADDRESS|Worker non-default flags|Sending cluster node|Did not restart" datasystem_worker.INFO.log
```

### 提取注册失败的 Client

```bash
grep "Register client failed" datasystem_worker.INFO.log
```

### 提取 Worker 异常退出前最后 20 条 ERROR

```bash
grep -E "ERROR|FATAL" datasystem_worker.INFO.log | tail -20
```

### 检查 lease 是否失效

```bash
grep -E "Failed to refresh lease|etcd keep alive run failed" datasystem_worker.INFO.log
```

## 常见错误码

| 错误码 | 含义 | 排查方向 |
|--------|------|----------|
| K_INVALID=2 | 参数非法 | 检查 worker_address/bind_address/master_address/etcd_address |
| K_RUNTIME_ERROR=5 | 通用运行时错误 | 查看上下文 |
| K_NOT_READY=8 | 资源未就绪 | 检查依赖服务（ETCD/Metastore/RocksDB） |
| K_KVSTORE_ERROR=4 | KV 存储错误 | 检查 ETCD/Metastore 连接和状态 |
| K_WORKER_ABNORMAL=22 | Worker 异常 | 检查 Worker 健康状态和日志 |
| K_SHUTTING_DOWN=21 | 正在关闭 | 正常或异常关闭流程 |
| K_RPC_UNAVAILABLE=1002 | 对端不可用 | 检查 ETCD/Metastore/其他 Worker 可达性 |
| K_RPC_DEADLINE_EXCEEDED=1001 | RPC 超时 | 检查网络、负载、线程池 |

## 注意事项

- Worker 启动失败时，常见原因是地址参数错误或 ETCD/Metastore 不可达。
- `Worker was hanged about ... ms` 表示进程被 OS 调度挂起，可能导致 lease 失效。
- `ZMQ bind ... Address already in use` 表示端口冲突，通常是上次进程未完全退出。
- 重启恢复逻辑（reconcile）在进程异常退出后可能触发，需要更长的启动时间。
