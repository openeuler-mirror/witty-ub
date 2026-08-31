---
name: ds-resource-metrics-diagnosis
description: >
  介绍 openYuanrong datasystem 资源指标日志（resource.log）和流缓存指标日志（sc_metrics.log）的分析方法，
  覆盖共享内存、Spill 磁盘、线程池、队列、缓存命中率、ETCD/OBS 成功率、流缓存状态等关键指标。
license: MIT
compatibility: yuanrong-datasystem 0.8.1.rc20
metadata:
  author: yuanrong-datasystem-log-analysis
  version: "1.0"
  keywords: [yuanrong-datasystem, datasystem, 资源指标, resource.log, sc_metrics, 共享内存, Spill, 线程池, 缓存命中率]
allowed-tools: Bash(grep:*) Bash(awk:*) Bash(sed:*) Bash(cat:*)
---

# yuanrong-datasystem 资源指标诊断 Skill

## 概述

资源指标日志（resource.log）和流缓存指标日志（sc_metrics.log）是容量规划、性能调优和瓶颈定位的核心数据来源。本文档介绍如何从这些指标中识别资源瓶颈和异常。

## 约束

- resource.log 需要 `log_monitor=true` 且 `log_monitor_exporter=harddisk`。
- sc_metrics.log 需要 `log_monitor=true`。
- 指标采集间隔由 `log_monitor_interval_ms` 控制，默认 10s。
- 资源日志中 trace_id 通常为空。

## 流程

1. 确认资源日志已开启并收集到文件。
2. 检查共享内存（shm_info）和 Spill 磁盘（spill_disk_info）使用率趋势。
3. 检查各线程池利用率（idle/current/max/waiting/rate）。
4. 检查 ETCD/OBS 请求成功率。
5. 检查缓存命中率（Cache_Hit_Info）。
6. 检查流缓存指标（sc_metrics）中的 page、producer/consumer、阻塞情况。
7. 结合访问日志定位高耗时或失败请求。

## 能力

- 输出 resource.log 各字段的含义和格式。
- 输出 sc_metrics.log 各字段的含义。
- 输出资源瓶颈（内存、磁盘、线程池、队列）的判断方法。
- 输出缓存命中率下降的分析方法。
- 输出 ETCD/OBS 请求成功率下降的分析方法。
- 输出流缓存阻塞和 page 泄漏的判断方法。

## 规则

- 资源日志应长期保留，用于容量趋势分析。
- 资源使用率超过阈值（如 80%）时应关注，接近 100% 时会触发错误。
- 线程池利用率持续高位且 waitingTask 多，说明处理能力不足。
- 缓存命中率下降时，应检查是否缓存容量不足或访问模式变化。
- ETCD/OBS 成功率下降时，应检查外部组件状态。

## 关键指标详解

### 共享内存（shm_info）

格式：`memoryUsage/physicalMemoryUsage/totalLimit/rate`

- memoryUsage：已分配内存（含对齐开销）。
- physicalMemoryUsage：物理内存使用。
- totalLimit：总大小。
- rate：使用率。

### Spill 磁盘（spill_disk_info）

格式：`spaceUsage/physicalSpaceUsage/totalLimit/rate`

- spaceUsage：已使用 Spill 空间。
- physicalSpaceUsage：物理磁盘使用。
- totalLimit：总大小。
- rate：使用率。

### 线程池

格式：`idleNum/currentTotalNum/MaxThreadNum/waitingTaskNum/rate`

覆盖：WorkerOcService、WorkerWorkerOcService、MasterWorkerOcService、MasterOcService、Master AsyncTask、ClientWorkerSCService、WorkerWorkerSCService、MasterWorkerSCService、MasterSCService。

### 队列与成功率

- write_ETCD_queue：写 ETCD 队列。
- ETCDrequest_success_rate：ETCD 请求成功率。
- OBSrequest_success_rate：OBS 请求成功率。
- remote_stream_push_success_rate：远端流推送成功率。

### 缓存命中率（Cache_Hit_Info）

格式：`memHitNum/diskHitNum/l2HitNum/remoteHitNum/missNum`

### 流缓存指标（sc_metric）

包含 streamName、生产者/消费者数量、page 使用、内存使用、streamState 等。

## 典型异常模式

### 1. 共享内存使用率持续升高

```text
shm_info: 900000000000/920000000000/1000000000000/90.0
```

可能原因：缓存对象增长、LRU 未触发、大对象写入。

排查：检查 object_nums、Cache_Hit_Info、L2 缓存配置。

### 2. Spill 磁盘使用率升高

说明内存不足，大量对象 spill 到磁盘。应检查 `shm_info` 和 `spill_directory`。

### 3. 线程池满载

```text
WorkerOcService_threadpool: 0/32/32/1000/100.0
```

说明处理能力不足，应检查访问日志中高耗时 action 和线程池配置。

### 4. ETCD 请求成功率下降

可能原因：ETCD 负载高、网络延迟、lease 频繁失效。

排查：检查 request_out.log 和 ETCD 集群状态。

### 5. 缓存命中率低

说明缓存容量不足或访问模式不适合缓存，应检查 `shm_info`、L2 缓存和 TTL。

### 6. Stream 阻塞或 page 泄漏

sc_metrics 中 `numLocalProdBlocked`/`numRemoteProdBlocked` 高或 `numPagesInUse` 持续增长。

## 解析示例

### 提取共享内存使用率

```bash
awk -F'|' '{print $1, $8}' resource.log | tail -100
```

### 提取线程池利用率

```bash
awk -F'|' '{print $1, $13}' resource.log | tail -100
```

### 提取 ETCD 成功率

```bash
awk -F'|' '{print $1, $17}' resource.log | tail -100
```

### 提取缓存命中率

```bash
awk -F'|' '{print $1, $30}' resource.log | tail -100
```

### 提取存在阻塞的 stream

```bash
awk -F'|' '{
    split($8, a, "/");
    if (a[19] > 0 || a[20] > 0) print $1, a[1]
}' sc_metrics.log | head -20
```

## 注意事项

- 资源日志是性能基线的重要依据，建议长期保留。
- 指标分析应结合访问日志和运行日志，避免单一指标误判。
- 资源使用率接近 100% 时，通常会触发错误，需要提前预警。
- 流缓存指标应结合远端流推送成功率共同分析。
