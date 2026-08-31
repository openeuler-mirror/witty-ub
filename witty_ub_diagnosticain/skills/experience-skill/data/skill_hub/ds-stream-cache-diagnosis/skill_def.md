---
name: ds-stream-cache-diagnosis
description: >
  介绍 openYuanrong datasystem Stream Cache 的日志分析方法，覆盖 Producer/Consumer、Pub/Sub、流状态、
  page 管理、阻塞/ACK、流缓存指标和远端传输异常。
license: MIT
compatibility: yuanrong-datasystem 0.8.1.rc20
metadata:
  author: yuanrong-datasystem-log-analysis
  version: "1.0"
  keywords: [yuanrong-datasystem, datasystem, Stream Cache, producer, consumer, page, sc_metrics, 阻塞]
allowed-tools: Bash(grep:*) Bash(awk:*) Bash(sed:*) Bash(cat:*)
---

# yuanrong-datasystem Stream Cache 诊断 Skill

## 概述

Stream Cache 提供流式数据发布/订阅能力，包括 Producer/Consumer、CreateProducer/Subscribe、Send/Receive 等接口。分析 Stream Cache 日志需要关注访问日志中的 `DS_STREAM_CLIENT_*` action、sc_metrics 日志、流状态相关错误码（3000–3010）以及资源日志中的线程池状态。

## 约束

- Stream 由 Master 协调元数据，Worker 作为本地或远端参与者。
- Producer 发送数据到 page，Consumer 从 page 读取数据。
- 流支持阻塞模式，当 page 满或 consumer 慢时 producer 会阻塞。
- 远端 producer/consumer 依赖 URMA/RDMA 或 TCP 传输。

## 流程

1. 在访问日志中过滤 `DS_STREAM_CLIENT_*` action。
2. 关注 `status_code` 非 0 的请求，特别是流相关错误码（3000–3010）。
3. 检查 sc_metrics 日志中 stream 的生产者/消费者数量、page 使用、阻塞情况。
4. 分析 producer 发送阻塞和 consumer 接收慢的问题。
5. 检查远端流推送成功率（`remote_stream_push_success_rate`）。
6. 检查相关线程池（ClientWorkerSCService、WorkerWorkerSCService、MasterSCService）利用率。

## 能力

- 输出 Stream Cache 接口 action 列表和常见错误码。
- 输出 sc_metrics 日志的解读方法。
- 输出 producer 阻塞、consumer 慢、page 泄漏的排查方向。
- 输出流状态异常（stream not found、already closed、in reset）的判断方法。
- 输出远端流推送失败的排查方向。

## 规则

- Stream 删除前需要确保所有 producer/consumer 已关闭。
- 远端 producer/consumer 依赖网络/传输层，异常时会触发连接重建。
- page 泄漏会导致共享内存持续增长，需要关注 `numPagesInUse` 和 `numPagesCached`。
- 阻塞模式下的 producer 需要 consumer 及时处理，否则会阻塞发送。

## 接口 action 列表

| action | 说明 |
|--------|------|
| DS_STREAM_CLIENT_CREATE_PRODUCER | 创建 Producer |
| DS_STREAM_CLIENT_SUBSCRIBE | 订阅 Stream（创建 Consumer） |
| DS_STREAM_CLIENT_DELETE_STREAM | 删除 Stream |
| DS_STREAM_CLIENT_QUERY_GLOBAL_PRODUCERS_NUM | 查询全局 Producer 数 |
| DS_STREAM_CLIENT_QUERY_GLOBAL_CONSUMERS_NUM | 查询全局 Consumer 数 |

说明：具体 action 名称以访问日志实际输出为准。

## 关键请求参数

| 参数 | 说明 |
|------|------|
| streamName | 流名称 |
| producerId / consumerId | 生产者/消费者 ID |
| timeout | 接口超时 |
| is_retry | 是否重试 |

## 常见错误模式

### 1. Stream 不存在（K_SC_STREAM_NOT_FOUND=3000）

```text
status_code=3000 action=DS_STREAM_CLIENT_SUBSCRIBE ...
```

可能原因：
- Stream 未创建或已删除。
- 订阅时流名称错误。

排查：
- 确认 Stream 是否已创建。
- 检查流名称是否正确。

### 2. Producer/Consumer 不存在（K_SC_PRODUCER_NOT_FOUND=3001 / K_SC_CONSUMER_NOT_FOUND=3002）

```text
status_code=3001 action=...
status_code=3002 action=...
```

可能原因：
- Producer/Consumer 已关闭或从未创建。
- Worker 重启后元数据丢失。

排查：
- 确认 Producer/Consumer 生命周期。
- 检查 Worker 是否重启。

### 3. 读到 Page 末尾（K_SC_END_OF_PAGE=3003）

```text
status_code=3003 action=...
```

可能原因：
- Consumer 已读取完当前 page 的数据。
- 需要等待 producer 发送新数据或新 page。

排查：
- 检查 producer 是否仍在发送数据。
- 检查是否使用阻塞模式。

### 4. Stream 正在重置（K_SC_STREAM_IN_RESET_STATE=3004）

```text
status_code=3004 action=...
```

可能原因：
- Stream 正在重置或恢复中。
- 远端 Worker 发生切换或重启。

排查：
- 等待重置完成。
- 检查相关 Worker 日志。

### 5. Worker 丢失（K_SC_WORKER_WAS_LOST=3005）

```text
status_code=3005 action=...
```

可能原因：
- Stream 相关的 Worker 被判定为 lost/dead。
- 网络分区导致 Worker 不可达。

排查：
- 检查集群管理日志中的节点事件。
- 检查 Worker 是否存活。

### 6. Stream 正在删除（K_SC_STREAM_DELETE_IN_PROGRESS=3007）

```text
status_code=3007 action=...
```

可能原因：
- Stream 正在删除，新请求被拒绝。

排查：
- 等待删除完成。
- 检查删除发起原因。

### 7. Producer 阻塞

sc_metrics 日志中：

```text
numLocalProdBlocked > 0 或 numRemoteProdBlocked > 0
```

可能原因：
- Consumer 消费慢。
- page 或缓存满。
- 远端 consumer 网络异常。

排查：
- 检查 `numEleSent` 与 `numEleRecv` 差距。
- 检查 `numRemoteConBlocking`。
- 检查 consumer 端状态。

## 解析示例

### 统计 Stream 接口错误码

```bash
awk -F'|' '$10 ~ /DS_STREAM_CLIENT/ && $9 != 0 {print $10, $9}' access.log | sort | uniq -c | sort -rn
```

### 提取存在阻塞 producer 的 stream

```bash
grep sc_metrics.log | awk -F'|' '{
    split($8, a, "/");
    if (a[19] > 0 || a[20] > 0) print $1, a[1]
}' | head -20
```

### 检查远端流推送成功率

```bash
awk -F'|' '{print $1, $27}' resource.log | tail -100
```

## 注意事项

- Stream 元数据由 Master 管理，Master 异常会影响 stream 创建/删除。
- 远端 producer/consumer 的稳定性受 URMA/RDMA 连接影响。
- Stream 删除时如果有未关闭的 producer/consumer，可能导致资源泄漏。
- page 数量异常增长时，应检查 producer/consumer 是否匹配。
- 阻塞模式下的 producer 在 consumer 慢时会有明显的吞吐下降。
