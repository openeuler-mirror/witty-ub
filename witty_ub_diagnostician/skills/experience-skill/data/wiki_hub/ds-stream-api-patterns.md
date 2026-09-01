---
name: "yuanrong-datasystem Stream Cache 接口日志模式"
description: "汇总 openYuanrong datasystem Stream Cache 接口的访问日志模式、流缓存指标、关键参数、常见错误码和排查方法。"
keywords:
  - yuanrong-datasystem
  - datasystem
  - Stream Cache
  - DS_STREAM_CLIENT
  - producer
  - consumer
  - page
  - sc_metrics
references:
  - name: "yuanrong-datasystem 0.8.1.rc20 Stream Client 实现"
    type: offline
    source: "yuanrong-datasystem-0.8.1.rc20/src/datasystem/client/stream_cache/stream_client.cpp"
  - name: "yuanrong-datasystem 0.8.1.rc20 日志指南"
    type: offline
    source: "yuanrong-datasystem-0.8.1.rc20/docs/source_zh_cn/appendix/log_guide.md"
---

# yuanrong-datasystem Stream Cache 接口日志模式

## 概述

Stream Cache 提供流式数据发布/订阅能力。本文档汇总访问日志中的 action、sc_metrics 指标和典型错误模式。

## 1. 接口 action

| action | 说明 |
|--------|------|
| DS_STREAM_CLIENT_CREATE_PRODUCER | 创建 Producer |
| DS_STREAM_CLIENT_SUBSCRIBE | 订阅 Stream（创建 Consumer） |
| DS_STREAM_CLIENT_DELETE_STREAM | 删除 Stream |
| DS_STREAM_CLIENT_QUERY_GLOBAL_PRODUCERS_NUM | 查询全局 Producer 数 |
| DS_STREAM_CLIENT_QUERY_GLOBAL_CONSUMERS_NUM | 查询全局 Consumer 数 |

说明：具体 action 名称以访问日志实际输出为准。

## 2. 关键请求参数

| 参数 | 说明 |
|------|------|
| streamName | 流名称 |
| producerId / consumerId | 生产者/消费者 ID |
| timeout | 接口超时 |
| is_retry | 是否重试 |

## 3. 常见错误模式

### 3.1 Stream 不存在

```text
status_code=3000 action=DS_STREAM_CLIENT_SUBSCRIBE ...
```

说明：Stream 未创建或已删除。

### 3.2 Producer/Consumer 不存在

```text
status_code=3001 action=...
status_code=3002 action=...
```

说明：Producer/Consumer 已关闭或从未创建。

### 3.3 读到 Page 末尾

```text
status_code=3003 action=...
```

说明：Consumer 已读完当前 page 数据，需等待新数据。

### 3.4 Stream 正在重置

```text
status_code=3004 action=...
```

说明：Stream 正在重置或恢复中。

### 3.5 Worker 丢失

```text
status_code=3005 action=...
```

说明：相关 Worker 被判定为 lost/dead。

### 3.6 Stream 正在删除

```text
status_code=3007 action=...
```

说明：Stream 正在删除，新请求被拒绝。

### 3.7 Producer 阻塞

sc_metrics 中 `numLocalProdBlocked`/`numRemoteProdBlocked` 大于 0。

可能原因：Consumer 慢、page 满、远端 consumer 异常。

## 4. sc_metrics 关键指标

| 指标 | 说明 |
|------|------|
| numLocalProd | 本地 producer 数 |
| numRemoteProd | 远端 producer 数 |
| numLocalCon | 本地 consumer 数 |
| numRemoteCon | 远端 consumer 数 |
| numEleSent | 发送元素总数 |
| numEleRecv | 接收元素总数 |
| numEleAck | acked 元素数 |
| numPagesCreated | page 创建次数 |
| numPagesReleased | page 释放次数 |
| numPagesInUse | 正在使用的 page 数 |
| numPagesCached | 缓存的 page 数 |
| numLocalProdBlocked | 本地 producer 阻塞数 |
| numRemoteProdBlocked | 远端 producer 阻塞数 |
| numRemoteConBlocking | 远端 consumer 阻塞数 |
| streamState | 流状态 |
| numProdMaster | master 上 producer 数 |
| numConMaster | master 上 consumer 数 |

## 5. 解析示例

### 统计 Stream 错误码

```bash
awk -F'|' '$10 ~ /DS_STREAM_CLIENT/ && $9 != 0 {print $10, $9}' access.log | sort | uniq -c | sort -rn
```

### 提取阻塞 producer 的 stream

```bash
awk -F'|' '{
    split($8, a, "/");
    if (a[19] > 0 || a[20] > 0) print $1, a[1]
}' sc_metrics.log | head -20
```

## 注意事项

- Stream 元数据由 Master 管理，Master 异常会影响 stream 操作。
- 远端 producer/consumer 稳定性受 URMA/RDMA 连接影响。
- Stream 删除前需确保所有 producer/consumer 关闭。
- page 数量持续增长可能意味着资源泄漏。
- 阻塞模式下 producer 会随 consumer 速度变化而吞吐变化。
