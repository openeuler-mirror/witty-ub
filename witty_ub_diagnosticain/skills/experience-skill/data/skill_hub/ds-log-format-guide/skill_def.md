---
name: ds-log-format-guide
description: >
  介绍 openYuanrong datasystem 各类日志的字段格式、日志级别、trace_id 传播、字段截断规则，
  帮助从原始日志中快速提取关键信息并定位异常。
license: MIT
compatibility: yuanrong-datasystem 0.8.1.rc20
metadata:
  author: yuanrong-datasystem-log-analysis
  version: "1.0"
  keywords: [yuanrong-datasystem, datasystem, 日志格式, 字段解析, trace_id, 访问日志, 资源日志, sc_metrics]
allowed-tools: Bash(grep:*) Bash(awk:*) Bash(sed:*) Bash(cat:*)
---

# yuanrong-datasystem 日志格式解析 Skill

## 概述

openYuanrong datasystem 的日志分为 6 类：运行日志、访问日志、请求第三方日志（request_out）、资源日志、流缓存指标日志（sc_metrics）和容器/进程日志。每类日志字段固定、以 `|` 分隔，便于脚本解析。

## 约束

- 日志字段分隔符为 `|`，不随环境变量变化。
- 部分字段（filename、pod_name、request param、response param）超长会被截断。
- 时间戳为 ISO8601 格式，位于行首。
- trace_id 在跨 client/worker 的 RPC 中传播，用于串联同一次请求。

## 流程

1. 识别日志文件类型（运行、访问、request_out、resource、sc_metrics、container）。
2. 使用 awk 按 `|` 分隔，按列号提取字段。
3. 以 `trace_id` 为 key 聚合相关日志，还原请求链路。
4. 关注 `status_code` 非 0 的访问/第三方日志，定位失败请求。
5. 对资源日志和 sc_metrics 日志按时间序列分析，观察资源变化趋势。

## 能力

- 输出 6 类日志的字段顺序和含义。
- 输出按 trace_id 聚合的命令示例。
- 输出识别日志截断和缺失字段的方法。
- 输出常见日志格式问题及原因。

## 规则

- 解析前备份原始日志，避免修改。
- 使用 `awk -F'|'` 解析时，注意字段内可能包含空格或 JSON 子串。
- 聚合统计时排除无 trace_id 的后台线程日志，避免噪音。
- 时间序列分析使用行首 ISO8601 时间戳，而不是日志内部字段。

## 日志字段总览

| 字段 | 长度 | 说明 |
|------|------|------|
| time | 26 | ISO8601，示例：`2023-06-02T14:58:32.081156` |
| level | 1 | `debug`/`info`/`warn`/`error`/`fatal` |
| filename | 128 | 源文件及行号，示例：`oc_metadata_manager.cpp:733` |
| pod_name | 128 | 所属 Pod 名，示例：`ds-worker-hs5qm` |
| pid:tid | 11 | 进程 ID:线程 ID，示例：`9:177` |
| trace_id | 36 | 请求 trace ID，后台线程可能为空 |
| cluster_name | 128 | 组件名，示例：`ds-worker` |
| message | 1024 | 自定义消息内容 |

## 各类日志字段顺序

### 运行日志

```text
time | level | filename | pod_name | pid:tid | trace_id | cluster_name | message
```

### 访问日志

```text
time | level | filename | pod_name | pid:tid | trace_id | cluster_name | status_code | action | cost | data_size | request_param | response_param
```

- `status_code`：0 成功，其他失败（参见 StatusCode 表）。
- `action`：接口名，如 `DS_KV_CLIENT_Get`、`DS_OBJECT_CLIENT_Publish`、`DS_ETCD_LEASE_GRANT`。
- `cost`：请求耗时，单位 us。
- `data_size`：Publish 等请求接收到的 Payload 大小。

### 请求第三方日志（request_out）

字段与访问日志一致，当前主要接入 ETCD gRPC 请求。

### 资源日志

```text
time | level | filename | pod_name | pid:tid | trace_id | cluster_name | shm_info | spill_disk_info | client_nums | object_nums | object_total_datasize | WorkerOcService_threadpool | WorkerWorkerOcService_threadpool | MasterWorkerOcService_threadpool | MasterOcService_threadpool | write_ETCD_queue | ETCDrequest_success_rate | OBSrequest_success_rate | Master_AsyncTask_threadpool | stream_nums | ClientWorkerSCService_threadpool | WorkerWorkerSCService_threadpool | MasterWorkerSCService_threadpool | MasterSCService_threadpool | remote_stream_push_success_rate | shared_disk_info | scLocalCache_info | Cache_Hit_Info
```

- `shm_info`：`memoryUsage/physicalMemoryUsage/totalLimit/rate`，单位 Byte，按 1T 限制、每项 13 Byte。
- `spill_disk_info`：`spaceUsage/physicalSpaceUsage/totalLimit/rate`，格式同上。
- `*_threadpool`：`idleNum/currentTotalNum/MaxThreadNum/waitingTaskNum/rate`。
- `Cache_Hit_Info`：`memHitNum/diskHitNum/l2HitNum/remoteHitNum/missNum`。

### 流缓存指标日志（sc_metrics）

```text
time | level | filename | pod_name | pid:tid | trace_id | cluster_name | sc_metric
```

- `sc_metric` 包含 `streamName`、生产者/消费者数量、page 数量、内存使用、streamState 等。

## 解析示例

### 按 trace_id 提取访问日志中的错误

```bash
awk -F'|' '$9 != 0 {print $6, $10, $11, $9}' access.log | sort | uniq -c | sort -rn | head -20
```

说明：提取 `trace_id`（第 6 列）、`action`（第 10 列）、`cost`（第 11 列）、`status_code`（第 9 列），统计高频错误。

### 提取资源日志中共享内存使用率

```bash
awk -F'|' '{print $1, $8}' resource.log | head -20
```

说明：第 1 列时间，第 8 列 `shm_info`。

## 常见问题

1. **字段数量不一致**：访问日志/资源日志字段较多，可能因版本或配置差异缺少某些列；先检查日志文件类型。
2. **trace_id 为空**：后台线程日志、资源日志、sc_metrics 通常不带 trace_id，不适合用 trace_id 聚合。
3. **status_code 字符串与数值混用**：运行日志中 StatusCode 常以数字或宏名出现，需对照 `include/datasystem/utils/status.h` 转换。
4. **字段被截断**：`request_param`/`response_param` 超长时会被截断，无法完整还原参数。
