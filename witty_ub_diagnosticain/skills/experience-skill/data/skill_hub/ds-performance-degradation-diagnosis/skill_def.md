---
name: ds-performance-degradation-diagnosis
description: >
  介绍 openYuanrong datasystem 性能下降（时延/吞吐/抖动）的日志分析方法，覆盖 CPU、内存、NUMA、
  大页、缓存命中率、线程池、调度延迟、传输层回退等典型性能瓶颈。
license: MIT
compatibility: yuanrong-datasystem 0.8.1.rc20
metadata:
  author: yuanrong-datasystem-log-analysis
  version: "1.0"
  keywords: [yuanrong-datasystem, datasystem, 性能, 时延, 吞吐, 抖动, 调优, NUMA, 大页, 缓存命中率]
allowed-tools: Bash(grep:*) Bash(awk:*) Bash(sed:*) Bash(cat:*)
---

# yuanrong-datasystem 性能下降诊断 Skill

## 概述

openYuanrong datasystem 性能下降可能表现为接口时延升高、吞吐下降或抖动增加。性能问题通常与资源瓶颈、线程池满载、缓存命中率低、传输层回退、调度延迟或 NUMA/大页配置相关。分析性能问题需要结合访问日志、资源日志、系统监控和源码配置。

## 约束

- 性能分析需要同时关注 Client 和 Worker 两侧的日志和监控。
- 资源日志（resource.log）是判断资源瓶颈的关键。
- 访问日志中的 `cost` 字段可量化接口延迟。
- 系统级监控（CPU、内存、磁盘、网络、调度延迟）不可或缺。

## 流程

1. 确认性能下降的具体表现（时延/吞吐/抖动）。
2. 在访问日志中按 action 统计耗时分布，找出高耗时接口。
3. 检查资源日志中共享内存、Spill 磁盘、线程池、队列、缓存命中率。
4. 检查是否大量回退到 TCP 传输（URMA/RDMA 连接失效）。
5. 检查系统调度延迟（`Worker was hanged about`、CPU throttling、内存回收）。
6. 检查 NUMA/大页配置是否合理。
7. 结合压测基线判断性能下降幅度。

## 能力

- 输出按 action 统计耗时的命令示例。
- 输出资源瓶颈与性能下降的关系。
- 输出传输层回退对性能的影响判断。
- 输出调度延迟和系统级瓶颈的判断方法。
- 输出 NUMA/大页/线程池/缓存命中率调优方向。

## 规则

- 性能分析应从整体到局部，先确认资源是否瓶颈，再分析具体接口。
- 单一高耗时请求可能是长尾，持续性高耗时才是性能问题。
- 缓存命中率下降会显著增加远端访问和磁盘访问，导致时延上升。
- 传输层回退 TCP 会显著降低吞吐，应优先保证 URMA/RDMA 稳定。
- 系统调度延迟（如 CPU throttling）会导致所有请求超时增加。

## 关键性能指标

### 访问日志耗时

- `cost` 字段，单位 us。
- 可按 action 统计 P50/P90/P99 或平均值。

### 资源日志指标

- `shm_info`：共享内存使用率。
- `spill_disk_info`：Spill 磁盘使用率。
- `*_threadpool`：线程池利用率、等待任务数。
- `Cache_Hit_Info`：缓存命中率。
- `ETCDrequest_success_rate`：ETCD 请求成功率。
- `remote_stream_push_success_rate`：远端流推送成功率。

### 系统级指标

- CPU 利用率、CPU throttling、调度延迟。
- 内存使用、内存回收、swap 使用。
- 网络带宽、延迟、丢包。
- 磁盘 I/O、iowait。
- NUMA 本地内存访问比例。
- 大页配置和命中率。

## 典型性能瓶颈

### 1. 共享内存不足

表现：写入失败（K_OUT_OF_MEMORY/K_LRU_HARD_LIMIT）、命中率下降、Spill 磁盘使用升高。

排查：查看 `shm_info`、Cache_Hit_Info、对象数量。

### 2. 线程池满载

表现：请求排队等待、接口耗时高、超时增加。

排查：查看线程池利用率、等待任务数、高耗时 action。

### 3. 缓存命中率低

表现：Get 请求耗时高、远端访问增加、磁盘 I/O 增加。

排查：查看 Cache_Hit_Info、shm_info、L2 缓存配置。

### 4. 传输层回退 TCP

表现：worker-worker 访问慢、URMA 日志频繁连接重建。

排查：查看 URMA 日志、enable_transport_fallback、远端 Worker 状态。

### 5. 调度延迟

表现：所有请求超时增加、lease 失效、URMA 超时。

排查：查看 `Worker was hanged about`、系统调度延迟、CPU throttling。

### 6. NUMA/大页配置不当

表现：内存访问延迟高、大页分配失败。

排查：检查 `shared_memory_distribution_policy`、`enable_huge_tlb`、系统 NUMA 和大页配置。

## 解析示例

### 按 action 统计耗时分布

```bash
awk -F'|' '$10 == "DS_KV_CLIENT_GET" {print $11}' access.log | sort -n | awk '
{
    a[i++]=$1;
    sum+=$1;
}
END {
    print "avg", sum/NR;
    print "p50", a[int(NR*0.5)];
    print "p90", a[int(NR*0.9)];
    print "p99", a[int(NR*0.99)];
}'
```

### 检查资源使用率趋势

```bash
awk -F'|' '{print $1, $8, $13, $30}' resource.log | tail -100
```

### 检查 URMA 连接重建频率

```bash
grep "\[URMA_NEED_CONNECT\]" datasystem_worker.INFO.log | wc -l
```

### 检查进程挂起

```bash
grep "Worker was hanged about" datasystem_worker.INFO.log
```

## 调优方向

| 问题 | 调优方向 |
|------|----------|
| 共享内存不足 | 扩容内存、调整淘汰策略、启用 L2 缓存 |
| 线程池满载 | 增加 `oc_thread_num`/`sc_thread_num`、优化请求处理 |
| 缓存命中率低 | 增加缓存容量、调整 TTL、优化访问模式 |
| 传输层回退 | 修复 URMA/RDMA 连接、确保远端 Worker 稳定 |
| 调度延迟 | 优化 CPU 绑定、减少 cgroup 限制、避免内存回收 |
| NUMA 本地访问低 | 配置 NUMA 亲和性、调整 shared_memory_distribution_policy |
| 大页不足 | 系统配置大页、启用 enable_huge_tlb |

## 注意事项

- 性能调优前应建立性能基线，避免盲目调整。
- 系统级问题（如 CPU throttling）会放大所有上层问题，需要优先排查。
- 大页和 NUMA 配置需要系统支持，配置不当可能导致性能更差。
- 性能问题往往是多因素叠加，需要综合分析。
