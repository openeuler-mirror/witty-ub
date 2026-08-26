---
name: "yuanrong-datasystem 资源日志模式"
description: "详细解读 openYuanrong datasystem 资源日志（resource.log）的各字段含义、格式、典型异常阈值与资源瓶颈分析方法。"
keywords:
  - yuanrong-datasystem
  - datasystem
  - 资源日志
  - resource.log
  - 共享内存
  - Spill 磁盘
  - 线程池
  - 缓存命中率
references:
  - name: "yuanrong-datasystem 0.8.1.rc20 日志指南"
    type: offline
    source: "yuanrong-datasystem-0.8.1.rc20/docs/source_zh_cn/appendix/log_guide.md"
  - name: "yuanrong-datasystem 0.8.1.rc20 资源指标采集"
    type: offline
    source: "yuanrong-datasystem-0.8.1.rc20/src/datasystem/common/metrics/res_metric_collector.cpp"
---

# yuanrong-datasystem 资源日志模式

## 概述

资源日志（resource.log）定时输出 Worker 运行时关键资源信息，包括共享内存、Spill 磁盘、线程池、队列、缓存命中率等。是容量规划、性能调优、资源瓶颈定位的核心数据来源。

## 日志字段

```text
time | level | filename | pod_name | pid:tid | trace_id | cluster_name | shm_info | spill_disk_info | client_nums | object_nums | object_total_datasize | WorkerOcService_threadpool | WorkerWorkerOcService_threadpool | MasterWorkerOcService_threadpool | MasterOcService_threadpool | write_ETCD_queue | ETCDrequest_success_rate | OBSrequest_success_rate | Master_AsyncTask_threadpool | stream_nums | ClientWorkerSCService_threadpool | WorkerWorkerSCService_threadpool | MasterWorkerSCService_threadpool | MasterSCService_threadpool | remote_stream_push_success_rate | shared_disk_info | scLocalCache_info | Cache_Hit_Info
```

## 字段详细说明

### 共享内存（shm_info）

格式：`memoryUsage/physicalMemoryUsage/totalLimit/rate`

| 子字段 | 说明 |
|--------|------|
| memoryUsage | 已分配的内存大小，是已缓存对象大小总和（含 jemalloc 对齐开销） |
| physicalMemoryUsage | 已分配的物理内存大小 |
| totalLimit | 共享内存总大小 |
| rate | 共享内存使用率，保留 3 位有效数字，单位 % |

- 单位 Byte，按 1T 限制大小，每个子字段 13 Byte。

### Spill 磁盘（spill_disk_info）

格式：`spaceUsage/physicalSpaceUsage/totalLimit/rate`

| 子字段 | 说明 |
|--------|------|
| spaceUsage | 已使用的磁盘大小，是已 Spill 对象大小总和 |
| physicalSpaceUsage | 已使用的物理磁盘大小 |
| totalLimit | Spill 磁盘总大小 |
| rate | Spill 磁盘使用率，单位 % |

### 客户端与对象统计

| 字段 | 说明 |
|------|------|
| client_nums | 已和 Worker 成功建立连接的 Client 数，最大 10000 |
| object_nums | Worker 已缓存对象数，按 1 亿限制 |
| object_total_datasize | Worker 已缓存对象大小，按 1T 限制，长度 13 Byte |

### 线程池信息

所有线程池字段格式：`idleNum/currentTotalNum/MaxThreadNum/waitingTaskNum/rate`

| 子字段 | 说明 |
|--------|------|
| idleNum | 空闲线程数 |
| currentTotalNum | 当前正在运行任务的线程数 |
| MaxThreadNum | 线程池最大可申请的线程数 |
| waitingTaskNum | 正在等待的任务数 |
| rate | 线程利用率，单位 % |

覆盖线程池：

- WorkerOcService
- WorkerWorkerOcService
- MasterWorkerOcService
- MasterOcService
- Master AsyncTask
- ClientWorkerSCService
- WorkerWorkerSCService
- MasterWorkerSCService
- MasterSCService

### 队列与成功率

| 字段 | 说明 |
|------|------|
| write_ETCD_queue | 写 ETCD 队列使用情况 |
| ETCDrequest_success_rate | ETCD 请求成功率，单位 % |
| OBSrequest_success_rate | OBS 请求成功率，单位 % |
| remote_stream_push_success_rate | 远端流推送成功率，单位 % |

### 共享磁盘与 scLocalCache

| 字段 | 说明 |
|------|------|
| shared_disk_info | `usage/physicaleUsage/totalLimit/rate`，共享磁盘使用信息 |
| scLocalCache_info | `usedSize/reservedSize/totalLimit/usedRate`，流缓存本地缓存使用信息 |

### 缓存命中率（Cache_Hit_Info）

格式：`memHitNum/diskHitNum/l2HitNum/remoteHitNum/missNum`

| 子字段 | 说明 |
|--------|------|
| memHitNum | 本地内存命中次数 |
| diskHitNum | 本地磁盘命中次数 |
| l2HitNum | 二级缓存命中次数 |
| remoteHitNum | 远端 worker 命中次数 |
| missNum | 未命中次数 |

## 典型异常模式

### 1. 共享内存使用率持续升高

```text
shm_info: 900000000000/920000000000/1000000000000/90.0
```

可能原因：
- 缓存对象持续增长，未被淘汰。
- 大对象写入导致瞬间占用高。
- LRU 淘汰策略未触发或配置不当。

排查：
- 查看 `object_nums` 和 `object_total_datasize` 变化。
- 检查 `Cache_Hit_Info` 是否 missNum 激增。
- 检查是否启用 `spill_to_remote_worker` 或 L2 缓存。

### 2. Spill 磁盘使用率升高

```text
spill_disk_info: 800000000000/820000000000/1000000000000/80.0
```

可能原因：
- 内存不足，大量对象被 spill 到磁盘。
- Spill 磁盘空间配置不足。

排查：
- 检查 `shm_info` 使用率是否接近上限。
- 检查 `spill_directory` 路径和磁盘空间。
- 考虑扩容内存或调整淘汰策略。

### 3. 线程池利用率高、等待任务多

```text
WorkerOcService_threadpool: 0/32/32/1000/100.0
```

可能原因：
- 请求量过大，线程池满载。
- 某些请求阻塞（如等待远端对象、ETCD 响应）。
- 线程数配置不足。

排查：
- 检查访问日志中哪些 action 耗时高。
- 检查是否有线程阻塞在 ETCD/URMA/锁上。
- 考虑调整 `oc_thread_num`/`sc_thread_num`。

### 4. ETCD 请求成功率下降

```text
ETCDrequest_success_rate: 95.0
```

可能原因：
- ETCD 集群负载高或不稳定。
- 网络延迟或抖动。
- lease 频繁失效导致重连。

排查：
- 查看 request_out.log 中 ETCD 请求失败类型。
- 检查 ETCD 集群健康状态。
- 检查 Worker 与 ETCD 网络质量。

### 5. 缓存命中率低

```text
Cache_Hit_Info: 1000/500/0/2000/5000
```

可能原因：
- 缓存容量不足，频繁淘汰。
- 访问模式随机，缓存效果差。
- L2 缓存未命中或配置错误。

排查：
- 查看 `shm_info` 和 `spill_disk_info` 使用率。
- 检查 L2 缓存类型和路径配置。
- 分析访问模式，调整缓存大小或 TTL。

## 解析示例

### 提取共享内存使用率趋势

```bash
awk -F'|' '{print $1, $8}' resource.log | tail -100
```

### 提取 WorkerOcService 线程池利用率

```bash
awk -F'|' '{print $1, $13}' resource.log | tail -100
```

### 提取缓存命中率

```bash
awk -F'|' '{print $1, $30}' resource.log | tail -100
```

### 提取 ETCD 请求成功率

```bash
awk -F'|' '{print $1, $17}' resource.log | tail -100
```

## 注意事项

- 资源日志采集间隔由 `log_monitor_interval_ms` 控制，默认 10s。
- 资源日志中 `trace_id` 通常为空，不适合按 trace 聚合。
- 部分字段（如 `shm_info` 各子字段）按固定长度 13 Byte 输出，解析时按 `/` 分隔。
- 资源日志是性能基线和容量规划的重要依据，建议长期保留。
