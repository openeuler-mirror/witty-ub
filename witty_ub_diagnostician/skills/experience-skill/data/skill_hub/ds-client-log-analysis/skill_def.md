---
name: ds-client-log-analysis
description: >
  介绍 openYuanrong datasystem 客户端日志（ds_client_{pid}.INFO.log / ds_client_access_{pid}.log）的分析方法，
  覆盖 SDK 初始化、连接 Worker、注册 Client、共享内存 fd 传递、请求重试和常见错误码。
license: MIT
compatibility: yuanrong-datasystem 0.8.1.rc20
metadata:
  author: yuanrong-datasystem-log-analysis
  version: "1.0"
  keywords: [yuanrong-datasystem, datasystem, client, SDK, 日志分析, 注册, 重连, 共享内存, 错误码]
allowed-tools: Bash(grep:*) Bash(awk:*) Bash(sed:*) Bash(cat:*)
---

# yuanrong-datasystem Client 日志分析 Skill

## 概述

Client 日志分为运行日志（`ds_client_{pid}.INFO.log`）和访问日志（`ds_client_access_{pid}.log`）。运行日志记录 SDK 初始化、连接 Worker、注册 Client、共享内存 fd 传递、心跳、重连等过程；访问日志记录接口请求与响应。

## 约束

- Client 与 Worker 版本需兼容，否则注册会失败（`K_CLIENT_WORKER_VERSION_MISMATCH`）。
- 共享内存 fd 传递依赖 SCMTCP 或 UDS，失败时通常回退到 RPC 传输。
- Client 日志文件名可通过环境变量覆盖。
- 连接异常时 Client 会按 `client_reconnect_wait_s` 等待后重连。

## 流程

1. 确认 Client 启动时间、PID 和版本信息。
2. 检查 `Connects to local server`/`Register client` 日志，确认连接 Worker 成功。
3. 检查共享内存 fd 传递是否成功（`Client and worker support transfer data through shared memory`）。
4. 结合访问日志分析接口错误码、耗时和重试情况。
5. 出现连接断开时，检查重连日志和 Worker 状态。

## 能力

- 输出 Client 启动/初始化日志模式。
- 输出 Client-Worker 连接与注册流程日志模式。
- 输出共享内存 fd 传递失败/成功的判断方法。
- 输出常见 Client 错误码与排查方向。
- 输出按 trace_id 串联 Client 与 Worker 日志的方法。

## 规则

- 分析 Client 日志时，应同时获取对应 Worker 日志和访问日志。
- 注意区分本地 Client（embedded）和远程 Client（standalone）的日志差异。
- 共享内存 fd 传递失败不一定会导致注册失败，但可能影响零拷贝性能。
- 重连日志中的错误码可能为 `K_RPC_UNAVAILABLE`、`K_WORKER_TIMEOUT` 等。

## 关键日志模式

### 初始化与连接

```text
Client start to connect worker
The total timeout is ... ms, single rpc timeout is ... ms
Try connect worker for shm fd transfer, endpoint: ...
Connects to local server ... successfully. Client fd ... Server fd ...
Client and worker support transfer data through shared memory and the fd send over ...
Register client to worker through the ... successfully, client id: ...
Sync client log_rate_limit from worker register response: ...
```

### 注册失败

```text
Register client failed: ...
Register client ... failed: ...
```

常见原因：
- Worker 正在退出（`Register client failed because worker is exiting and unhealthy now`）。
- Client 与 Worker 版本不匹配（`K_CLIENT_WORKER_VERSION_MISMATCH`）。
- Worker 不可达或网络异常。

### 共享内存 fd 传递

```text
Both the uds socket path and shm_worker_port is empty, cannot transfer data through shm between client and worker.
Client can not connect to server for shm fd transfer within allowed time ...
```

可能原因：
- Worker 的 `shm_worker_port` 未配置或 UDS 路径未创建。
- 网络/权限问题导致无法连接 fd 传递通道。

### 重连

```text
Client ... sends exit notice to worker.
```

- 正常销毁时 Client 会通知 Worker 断开。
- 异常退出时可能没有该日志，Worker 端通过 `client_dead_timeout_s` 检测 Client 死亡。

## 解析示例

### 提取 Client 注册失败原因

```bash
grep "Register client failed\|Register client.*failed" ds_client_*.INFO.log
```

### 按 trace_id 提取失败请求

```bash
awk -F'|' '$9 != 0 {print $6, $10, $9}' ds_client_access_*.log | sort | uniq -c | sort -rn | head -20
```

### 检查共享内存是否启用

```bash
grep "Client and worker support transfer data through shared memory" ds_client_*.INFO.log | head -5
```

## 常见错误码

| 错误码 | 含义 | 排查方向 |
|--------|------|----------|
| K_INVALID=2 | 参数非法 | 检查请求参数 |
| K_NOT_FOUND=3 | 对象/资源不存在 | 检查 key 是否创建、Worker 是否在线 |
| K_NOT_READY=8 | 资源未就绪 | 检查 Worker 是否启动完成、是否在初始化 |
| K_CLIENT_WORKER_VERSION_MISMATCH=28 | 版本不匹配 | 统一 Client 与 Worker 版本 |
| K_CLIENT_WORKER_DISCONNECT=23 | 连接断开 | 检查网络、Worker 状态、心跳 |
| K_RPC_DEADLINE_EXCEEDED=1001 | RPC 超时 | 检查 Worker 负载、网络延迟 |
| K_URMA_NEED_CONNECT=1006 | 需要建立 URMA 连接 | 检查远端 Worker 是否可达 |

## 注意事项

- Client 日志可能分散在多个 `ds_client_{pid}.INFO.log` 文件中，对应不同进程。
- Embedded Client 与 Worker 在同一进程，日志可能混合在 Worker 日志中。
- 分析时应确认 Client 连接的 Worker 地址，再到对应 Worker 日志中查找。
