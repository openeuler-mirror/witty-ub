---
name: "yuanrong-datasystem 流缓存指标日志模式"
description: "详细解读 openYuanrong datasystem 流缓存指标日志（sc_metrics.log）的字段格式、stream 状态、生产者/消费者统计与典型异常模式。"
keywords:
  - yuanrong-datasystem
  - datasystem
  - 流缓存
  - sc_metrics
  - stream
  - producer
  - consumer
  - page
references:
  - name: "yuanrong-datasystem 0.8.1.rc20 日志指南"
    type: offline
    source: "yuanrong-datasystem-0.8.1.rc20/docs/source_zh_cn/appendix/log_guide.md"
  - name: "yuanrong-datasystem 0.8.1.rc20 Stream 服务实现"
    type: offline
    source: "yuanrong-datasystem-0.8.1.rc20/src/datasystem/worker/stream_cache/client_worker_sc_service_impl.cpp"
---

# yuanrong-datasystem 流缓存指标日志模式

## 概述

流缓存指标日志（sc_metrics.log）记录 Worker 上 stream 的运行数据，包括 stream 名称、生产者/消费者数量、page 使用情况、内存使用、stream 状态等。是分析流缓存性能、阻塞、资源泄漏的主要数据来源。

## 日志字段

```text
time | level | filename | pod_name | pid:tid | trace_id | cluster_name | sc_metric
```

其中 `sc_metric` 是流缓存运行数据的核心字段，包含一个 stream 的完整指标。

## sc_metric 字段格式

```text
streamName ["exit"] / numLocalProd / numRemoteProd / numLocalCon / numRemoteCon / sharedMemUsed / localMemUsed / numEleSent / numEleRecv / numEleAck / numSendReq / numRecvReq / numPagesCreated / numPagesReleased / numPagesInUse / numPagesCached / numBigPagesCreated / numBigPagesReleased / numLocalProdBlocked / numRemoteProdBlocked / numRemoteConBlocking / retainData / streamState / numProdMaster / numConMaster
```

## 字段详细说明

| 字段 | 说明 |
|------|------|
| streamName | stream 名字；带有 `"exit"` 表示 stream 正在关闭 |
| numLocalProd | 本地 producer 数量 |
| numRemoteProd | 远端 producer 数量（至少有一个 producer 的远端 worker 数） |
| numLocalCon | 本地 consumer 数量 |
| numRemoteCon | 远端 consumer 数量 |
| sharedMemUsed | stream 使用共享内存大小，单位 Byte |
| localMemUsed | stream 使用本地内存大小，单位 Byte |
| numEleSent | 本地所有 producer 发送的元素总数 |
| numEleRecv | 本地所有 consumer 接收的元素总数（无本地 consumer 时为 0） |
| numEleAck | element acked 数量 |
| numSendReq | client 调用 producer.send() 次数 |
| numRecvReq | client 调用 consumer.receive() 次数 |
| numPagesCreated | page 创建次数 |
| numPagesReleased | page 释放次数 |
| numPagesInUse | page in use 数量 |
| numPagesCached | page cached 数量 |
| numBigPagesCreated | big element page 创建次数 |
| numBigPagesReleased | big element page 释放次数 |
| numLocalProdBlocked | 本地 producer blocked 数量 |
| numRemoteProdBlocked | 远端 producer blocked 数量 |
| numRemoteConBlocking | 远端 consumer blocking 数量 |
| retainData | retain data state |
| streamState | stream state |
| numProdMaster | master 上 producer 数量 |
| numConMaster | master 上 consumer 数量 |

注意：
- 如果 Worker 不是 stream 的 master，则 `numProdMaster`/`numConMaster` 无数据。
- 如果 Worker 只有 master 数据，则 `numLocalProd`–`numRemoteConBlocking` 无数据。

## 典型异常模式

### 1. Producer 发送阻塞

```text
numLocalProdBlocked > 0 或 numRemoteProdBlocked > 0
```

可能原因：
- Consumer 消费速度慢，page 或缓存满。
- 远端 consumer 网络/传输异常，ack 未返回。
- stream 缓冲区大小配置不足。

排查：
- 检查 `numEleSent` 与 `numEleRecv` 的差距。
- 检查 `numRemoteConBlocking` 是否升高。
- 检查 consumer 端是否出现 `K_SC_END_OF_PAGE` 或 `K_SC_STREAM_RESOURCE_ERROR`。

### 2. Consumer 接收阻塞

```text
numRemoteConBlocking > 0
```

可能原因：
- 远端 producer 发送慢或阻塞。
- 网络/传输层异常。
- consumer 本地处理慢。

排查：
- 检查 producer 端 `numLocalProdBlocked`。
- 检查 URMA/RDMA 连接状态。
- 检查 consumer 端线程池利用率。

### 3. Page 泄漏

```text
numPagesCreated - numPagesReleased >> numPagesInUse + numPagesCached
```

可能原因：
- page 释放逻辑异常。
- stream 关闭时未清理资源。
- 异常退出导致 page 未释放。

排查：
- 检查 `streamName` 是否带 `"exit"` 但资源未下降。
- 检查 stream 关闭流程日志。
- 结合 `resource.log` 查看共享内存持续增长。

### 4. Stream 关闭异常

```text
streamName="xxx exit" 但资源未释放
```

可能原因：
- 关闭流程被中断。
- 关闭时依赖的外部资源（如 ETCD、远端连接）不可用。
- 关闭超时。

排查：
- 检查运行日志中 stream 关闭相关错误。
- 检查 `numLocalProd`/`numLocalCon` 是否已降为 0。
- 检查远端 worker 是否已下线。

### 5. Master 与 Worker 数据不一致

```text
numProdMaster/numConMaster 与 numLocalProd/numLocalCon 差异大
```

可能原因：
- Master 元数据与 Worker 实际状态不一致。
- 节点上下线事件未同步。
- hash ring 版本不一致。

排查：
- 检查 ETCD 中 stream 元数据。
- 检查运行日志中 hash ring 更新事件。
- 检查 Master 与 Worker 的日志时间线。

## 解析示例

### 提取所有正在关闭的 stream

```bash
grep '"exit"' sc_metrics.log | head -20
```

### 提取存在 blocked producer 的 stream

```bash
awk -F'|' '$19 != 0 || $20 != 0' sc_metrics.log | head -20
```

说明：字段位置需根据实际日志格式确认，这里假设按字段索引提取。

### 统计 page 创建/释放比例异常

```bash
awk -F'|' '{
    split($8, a, "/");
    if (a[14] - a[15] != a[16] + a[17]) print $1, a[1], a[14], a[15], a[16], a[17]
}' sc_metrics.log | head -20
```

## 注意事项

- sc_metrics 日志由 `log_monitor` 控制开启，默认与资源日志一同输出。
- `sc_metric` 字段较长，解析时建议按 `/` 分隔。
- 如果 Worker 不是 stream 的 master，部分字段为空，解析时需注意缺失字段。
- 分析流缓存问题时，应结合 `resource.log` 中的线程池和内存使用数据。
