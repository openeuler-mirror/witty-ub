---
name: "yuanrong-datasystem 日志格式说明"
description: "介绍 openYuanrong datasystem 六类日志的字段格式、字段含义、trace_id 传播、字段截断规则与解析方法，用于日志解析与故障排查。"
keywords:
  - yuanrong-datasystem
  - datasystem
  - 日志格式
  - 运行日志
  - 访问日志
  - request_out
  - 资源日志
  - sc_metrics
  - trace_id
references:
  - name: "yuanrong-datasystem 0.8.1.rc20 日志指南"
    type: offline
    source: "yuanrong-datasystem-0.8.1.rc20/docs/source_zh_cn/appendix/log_guide.md"
  - name: "yuanrong-datasystem 0.8.1.rc20 错误码定义"
    type: offline
    source: "yuanrong-datasystem-0.8.1.rc20/include/datasystem/utils/status.h"
  - name: "yuanrong-datasystem 0.8.1.rc20 GitCode 仓库"
    type: online
    source: "https://gitcode.com/openeuler/yuanrong-datasystem/tree/0.8.1.rc20"
---

# yuanrong-datasystem 日志格式说明

## 概述

openYuanrong datasystem 的日志分为 6 类，每类日志字段固定、以 `|` 分隔，便于脚本解析和聚合分析。所有日志均包含时间戳、日志级别、源文件位置、进程/线程 ID、trace_id 和组件名等通用字段。

## 通用字段格式

所有日志的前 7 个字段相同：

```text
time | level | filename | pod_name | pid:tid | trace_id | cluster_name | ...
```

| 字段 | 长度 | 说明 |
|------|------|------|
| time | 26 | ISO8601 时间戳，示例：`2023-06-02T14:58:32.081156` |
| level | 1 | `debug`/`info`/`warn`/`error`/`fatal` |
| filename | 128 | 源文件及行号，示例：`oc_metadata_manager.cpp:733`，超长截断 |
| pod_name | 128 | 所属 Pod 名，示例：`ds-worker-hs5qm`，超长截断 |
| pid:tid | 11 | 进程 ID:线程 ID，示例：`9:177` |
| trace_id | 36 | 请求 trace ID，后台线程日志可能为空 |
| cluster_name | 128 | 组件名，示例：`ds-worker`，超长截断 |

## 六类日志格式

### 1. 运行日志

```text
time | level | filename | pod_name | pid:tid | trace_id | cluster_name | message
```

- 记录组件运行时的 INFO/WARNING/ERROR/FATAL 信息。
- 更细粒度调试可通过 VLOG 与 gflags（如 `--v`）控制。
- 日志路径：`{log_dir}/{log_filename}.INFO.log`（及 `.WARNING`、`.ERROR` 等轮转文件）。

### 2. 访问日志

```text
time | level | filename | pod_name | pid:tid | trace_id | cluster_name | status_code | action | cost | data_size | request_param | response_param
```

| 字段 | 长度 | 说明 |
|------|------|------|
| status_code | 5 | 请求状态，0 成功，其他失败 |
| action | 64 | 接口名，如 `DS_KV_CLIENT_Get`、`DS_OBJECT_CLIENT_Publish` |
| cost | 16 | 请求耗时，单位 us |
| data_size | 16 | Publish 请求接收到的 Payload 大小 |
| request_param | 2560 | 关键请求参数，超长截断 |
| response_param | 1024 | 响应信息，超长截断 |

- 日志路径：`{log_dir}/access.log`。
- 需开启 `log_monitor`。

### 3. 请求第三方日志（request_out）

```text
time | level | filename | pod_name | pid:tid | trace_id | cluster_name | status_code | action | cost | data_size | request_param | response_param
```

- 字段与访问日志一致。
- 当前主要接入 ETCD gRPC 请求，action 如 `DS_ETCD_LEASE_GRANT`、`DS_ETCD_PUT`。
- 日志路径：`{log_dir}/request_out.log`。
- 需开启 `log_monitor`。

### 4. 资源日志

```text
time | level | filename | pod_name | pid:tid | trace_id | cluster_name | shm_info | spill_disk_info | client_nums | object_nums | object_total_datasize | WorkerOcService_threadpool | WorkerWorkerOcService_threadpool | MasterWorkerOcService_threadpool | MasterOcService_threadpool | write_ETCD_queue | ETCDrequest_success_rate | OBSrequest_success_rate | Master_AsyncTask_threadpool | stream_nums | ClientWorkerSCService_threadpool | WorkerWorkerSCService_threadpool | MasterWorkerSCService_threadpool | MasterSCService_threadpool | remote_stream_push_success_rate | shared_disk_info | scLocalCache_info | Cache_Hit_Info
```

| 字段 | 说明 |
|------|------|
| shm_info | `memoryUsage/physicalMemoryUsage/totalLimit/rate`，单位 Byte |
| spill_disk_info | `spaceUsage/physicalSpaceUsage/totalLimit/rate`，单位 Byte |
| client_nums | 已建立连接的 Client 数 |
| object_nums | Worker 已缓存对象数 |
| object_total_datasize | Worker 已缓存对象总大小 |
| *_threadpool | `idleNum/currentTotalNum/MaxThreadNum/waitingTaskNum/rate` |
| write_ETCD_queue | 写 ETCD 队列使用情况 |
| ETCDrequest_success_rate | ETCD 请求成功率 |
| OBSrequest_success_rate | OBS 请求成功率 |
| remote_stream_push_success_rate | 远端流推送成功率 |
| shared_disk_info | 共享磁盘使用信息 |
| scLocalCache_info | scLocalCache 使用信息 |
| Cache_Hit_Info | `memHitNum/diskHitNum/l2HitNum/remoteHitNum/missNum` |

- 日志路径：`{log_dir}/resource.log`。
- 需开启 `log_monitor` 且 `log_monitor_exporter=harddisk`。

### 5. 流缓存指标日志（sc_metrics）

```text
time | level | filename | pod_name | pid:tid | trace_id | cluster_name | sc_metric
```

- `sc_metric` 包含 streamName、本地/远端生产者/消费者数量、page 创建释放次数、内存使用、streamState 等。
- 日志路径：`{log_dir}/sc_metrics.log`。
- 需开启 `log_monitor`。

### 6. 容器/进程日志

```text
time | level | filename | pod_name | pid:tid | trace_id | cluster_name | message
```

- 记录容器运行日志，管理和监控 worker 进程的生命周期。
- 日志路径：`{log_dir}/container.log`。

## 关键请求参数字段

访问日志中 `request_param` 常见字段：

| 参数 | 说明 |
|------|------|
| Object_key | 对象 ID，最长 255 Byte |
| object_keys | 多个对象 KEY，JSON 格式，总长上限约 1KB |
| Nested_keys | 嵌套引用对象 KEY |
| keep | 是否手动管理对象生命周期，true/false |
| Write_mode | 写模式，影响数据可靠性 |
| consistency_type | 数据一致性模式 |
| is_seal | 是否不可修改，0/1 |
| is_retry | 是否重试场景，0/1 |
| ttl_second | TTL 时间 |
| existence | Key 存在时是否允许继续操作 |
| sub_timeout | Get 请求订阅时间 |
| timeout | 接口超时时间 |

## 解析示例

### 提取运行日志中的 ERROR 并按文件聚合

```bash
awk -F'|' '$3 == "error" {print $4}' datasystem_worker.INFO.log | sort | uniq -c | sort -rn | head -20
```

### 按 trace_id 提取失败访问请求

```bash
awk -F'|' '$9 != 0 {print $6, $10, $11, $9}' access.log | sort | uniq -c | sort -rn | head -20
```

### 提取资源日志中共享内存使用率

```bash
awk -F'|' '{print $1, $8}' resource.log | tail -100
```

## 注意事项

- 字段分隔符固定为 `|`，不随环境变量变化。
- `filename`、`pod_name`、`request_param`、`response_param` 等字段超长会被截断。
- `trace_id` 在跨 client/worker 的 RPC 中传播，可用于串联请求链路；但资源日志、sc_metrics 和后台线程日志通常不带 trace_id。
- 时间戳使用行首 ISO8601 格式，适合时间序列分析。
