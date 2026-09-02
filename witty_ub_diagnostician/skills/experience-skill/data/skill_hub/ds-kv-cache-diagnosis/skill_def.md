---
name: ds-kv-cache-diagnosis
description: >
  介绍 openYuanrong datasystem KV Cache 的日志分析方法，覆盖 DS_KV_CLIENT Create/Set/Get/Del/Exist/Expire 等接口、
  一致性、TTL、LRU 淘汰、WriteMode 和批量操作异常。
license: MIT
compatibility: yuanrong-datasystem 0.8.1.rc20
metadata:
  author: yuanrong-datasystem-log-analysis
  version: "1.0"
  keywords: [yuanrong-datasystem, datasystem, KV Cache, DS_KV_CLIENT, TTL, LRU, WriteMode, 一致性]
allowed-tools: Bash(grep:*) Bash(awk:*) Bash(sed:*) Bash(cat:*)
---

# yuanrong-datasystem KV Cache 诊断 Skill

## 概述

KV Cache 提供类似键值存储的接口（Create/Set/Get/Del/Exist/Expire/MSet/MGet 等）。分析 KV Cache 日志需要关注访问日志中的 `DS_KV_CLIENT_*` action、StatusCode、耗时和请求参数，以及资源日志中的缓存命中率。

## 约束

- KV 接口支持 WriteMode 和 ConsistencyType 配置，影响数据可靠性和一致性。
- TTL 过期后对象会被清理。
- 缓存容量不足时会触发 LRU 淘汰（软限制/硬限制）。
- 批量操作（MSet/MGet）的日志中 `object_keys` 字段可能显示总数和部分 key。

## 流程

1. 在访问日志中过滤 `DS_KV_CLIENT_*` action。
2. 关注 `status_code` 非 0 的请求，按错误码分类。
3. 分析高耗时请求（`cost` 大），结合资源日志判断是否为资源瓶颈。
4. 检查 TTL 相关失败和 LRU 淘汰触发情况。
5. 对批量操作失败，检查是否有部分 key 失败。
6. 结合 `Cache_Hit_Info` 判断缓存命中情况。

## 能力

- 输出 KV Cache 接口 action 列表和常见错误码。
- 输出 TTL 过期和 LRU 淘汰的日志判断方法。
- 输出批量操作失败和部分失败的分析方法。
- 输出一致性和 WriteMode 相关问题排查方向。
- 输出缓存命中率与 KV 性能的关系分析。

## 规则

- KV Cache 访问日志中 status_code=0 表示成功，非 0 需要结合 StatusCode 表分析。
- 高耗时请求可能由资源不足、远端访问、网络延迟或 LRU 淘汰导致。
- MSet/MGet 部分失败时，应检查响应参数中的 failedKeys。
- TTL 设置不合理可能导致数据提前过期或长期占用内存。

## 接口 action 列表

| action | 说明 |
|--------|------|
| DS_KV_CLIENT_CREATE | 创建 KV buffer |
| DS_KV_CLIENT_SET | 设置/写入 KV 值 |
| DS_KV_CLIENT_MSET | 批量设置 |
| DS_KV_CLIENT_GET | 读取单个/多个 KV |
| DS_KV_CLIENT_DELETE | 删除 KV |
| DS_KV_CLIENT_EXIST | 判断 KV 是否存在 |
| DS_KV_CLIENT_EXPIRE | 设置 TTL |
| DS_KV_CLIENT_QUERY_SIZE | 查询 KV 大小 |
| DS_KV_CLIENT_HEALTH_CHECK | 健康检查 |

## 关键请求参数

| 参数 | 说明 |
|------|------|
| Object_key | 对象/键 ID |
| object_keys | 批量键列表 |
| Write_mode | 写模式，影响可靠性 |
| consistency_type | 一致性模式 |
| ttl_second | TTL 秒数 |
| is_retry | 是否重试 |
| sub_timeout | Get 订阅超时 |

## 常见错误模式

### 1. 键不存在（K_NOT_FOUND=3）

```text
status_code=3 action=DS_KV_CLIENT_GET ...
```

可能原因：
- 键未创建或已过期。
- 键被 LRU 淘汰。
- 键所在 Worker 已下线。

排查：
- 检查键是否已创建和 TTL。
- 检查 LRU 淘汰日志。
- 检查 Worker 是否在线。

### 2. 重复创建（K_DUPLICATED=1 / K_OC_KEY_ALREADY_EXIST=2004）

```text
status_code=1 action=DS_KV_CLIENT_CREATE ...
```

可能原因：
- 重复创建同一 key。
- 应用重试导致重复请求。

排查：
- 检查 `is_retry` 参数。
- 确认应用幂等性。

### 3. 超时（K_RPC_DEADLINE_EXCEEDED=1001 / K_WORKER_TIMEOUT=24）

```text
status_code=1001 action=DS_KV_CLIENT_GET cost=...
```

可能原因：
- Worker 负载高。
- 网络延迟。
- 远端 Worker 访问慢。

排查：
- 检查 Worker 线程池利用率。
- 检查网络延迟。
- 检查是否频繁访问远端数据。

### 4. 资源不足（K_OUT_OF_MEMORY=6 / K_LRU_HARD_LIMIT=34）

```text
status_code=6 action=DS_KV_CLIENT_SET ...
status_code=34 action=DS_KV_CLIENT_SET ...
```

可能原因：
- 共享内存耗尽。
- LRU 硬限制触发。

排查：
- 查看 `resource.log` 中 `shm_info`。
- 检查 `eviction_reserve_mem_threshold_mb`。
- 考虑扩容或调整缓存策略。

### 5. TTL 相关

```text
status_code=3 action=DS_KV_CLIENT_GET ...
```

结合日志时间判断是否为 TTL 过期导致。

## 解析示例

### 统计 KV 接口错误码

```bash
awk -F'|' '$10 ~ /DS_KV_CLIENT/ && $9 != 0 {print $10, $9}' access.log | sort | uniq -c | sort -rn
```

### 提取 KV Get 高耗时请求

```bash
awk -F'|' '$10 == "DS_KV_CLIENT_GET" {print $11, $6}' access.log | sort -rn | head -20
```

### 检查缓存命中率

```bash
awk -F'|' '{print $1, $30}' resource.log | tail -100
```

## 注意事项

- KV Cache 与 Object Cache 共享底层存储资源，资源竞争会影响双方性能。
- WriteMode 影响写入可靠性，某些 WriteMode 下写入可能未同步到远端或磁盘。
- MSet/MGet 的批量大小会影响单次请求耗时，过大可能导致超时。
- TTL 过期是异步清理，过期后可能短暂仍可读取。
