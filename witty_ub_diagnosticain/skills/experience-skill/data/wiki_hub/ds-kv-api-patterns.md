---
name: "yuanrong-datasystem KV Cache 接口日志模式"
description: "汇总 openYuanrong datasystem KV Cache 接口的访问日志模式、关键参数、常见错误码和排查方法。"
keywords:
  - yuanrong-datasystem
  - datasystem
  - KV Cache
  - DS_KV_CLIENT
  - Set
  - Get
  - MSet
  - MGet
  - TTL
  - LRU
references:
  - name: "yuanrong-datasystem 0.8.1.rc20 KV Client 实现"
    type: offline
    source: "yuanrong-datasystem-0.8.1.rc20/src/datasystem/client/kv_cache/kv_client.cpp"
  - name: "yuanrong-datasystem 0.8.1.rc20 日志指南"
    type: offline
    source: "yuanrong-datasystem-0.8.1.rc20/docs/source_zh_cn/appendix/log_guide.md"
---

# yuanrong-datasystem KV Cache 接口日志模式

## 概述

KV Cache 提供键值存储接口，包括 Create/Set/Get/Del/Exist/Expire 等。本文档汇总访问日志中的 action、关键参数和典型错误模式。

## 1. 接口 action

| action | 说明 |
|--------|------|
| DS_KV_CLIENT_CREATE | 创建 KV buffer |
| DS_KV_CLIENT_SET | 设置/写入值 |
| DS_KV_CLIENT_MSET | 批量设置 |
| DS_KV_CLIENT_GET | 读取单个/多个 KV |
| DS_KV_CLIENT_DELETE | 删除 |
| DS_KV_CLIENT_EXIST | 判断是否存在 |
| DS_KV_CLIENT_EXPIRE | 设置 TTL |
| DS_KV_CLIENT_QUERY_SIZE | 查询大小 |
| DS_KV_CLIENT_HEALTH_CHECK | 健康检查 |

## 2. 关键请求参数

| 参数 | 说明 |
|------|------|
| Object_key | 键 ID |
| object_keys | 批量键列表（JSON） |
| Write_mode | 写模式，影响可靠性 |
| consistency_type | 一致性模式 |
| ttl_second | TTL 秒数 |
| is_retry | 是否重试 |
| sub_timeout | Get 订阅超时 |
| timeout | 接口超时 |

## 3. 常见错误模式

### 3.1 键不存在

```text
status_code=3 action=DS_KV_CLIENT_GET ...
```

可能原因：未创建、已过期、LRU 淘汰、Worker 下线。

### 3.2 重复创建

```text
status_code=1 action=DS_KV_CLIENT_CREATE ...
```

可能原因：重复创建同一 key、重试导致重复。

### 3.3 超时

```text
status_code=1001 action=DS_KV_CLIENT_GET cost=...
status_code=24 action=DS_KV_CLIENT_GET ...
```

可能原因：Worker 负载高、网络延迟、远端访问慢。

### 3.4 资源不足

```text
status_code=6 action=DS_KV_CLIENT_SET ...
status_code=34 action=DS_KV_CLIENT_SET ...
status_code=13 action=DS_KV_CLIENT_SET ...
```

可能原因：共享内存耗尽、LRU 硬限制、Spill 磁盘不足。

## 4. 批量操作

### 4.1 MSet/MGet 部分失败

访问日志中 `object_keys` 可能只显示部分 key 和总数，具体失败 key 需要查看 response_param 或运行日志。

## 5. 解析示例

### 统计 KV 错误码

```bash
awk -F'|' '$10 ~ /DS_KV_CLIENT/ && $9 != 0 {print $10, $9}' access.log | sort | uniq -c | sort -rn
```

### 提取高耗时 KV Get

```bash
awk -F'|' '$10 == "DS_KV_CLIENT_GET" {print $11, $6}' access.log | sort -rn | head -20
```

## 注意事项

- KV Cache 与 Object Cache 共享 Worker 资源，需整体监控。
- WriteMode 影响写入可靠性，不同模式下的持久化程度不同。
- TTL 过期是异步清理，过期后可能短暂可读取。
- 批量操作过大可能导致超时，建议分批执行。
