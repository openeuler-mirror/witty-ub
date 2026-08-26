---
name: umdk-performance-degradation-diagnosis
description: >
  结合 urma_perftest 结果、UMQ/URPC 统计指标和日志中的重传/超时/流控信息，分析 UMDK 性能下降原因。
  本 Skill 提供从性能数据到根因的系统化排查流程。
license: MIT
compatibility: UMDK v26.06.0_CAM
metadata:
  author: umdk-log-analysis
  version: "1.0"
  keywords: [UMDK, URMA, UMQ, URPC, 性能下降, 带宽, 时延, 重传, 超时, 流控]
allowed-tools: Bash(grep:*) Bash(awk:*) Bash(cat:*)
---

# UMDK 性能下降诊断 Skill

## 概述

UMDK 性能下降可能由链路质量、流控、资源不足、队列配置、CPU 调度、内存访问等多因素导致。本 Skill 结合性能测试工具、统计指标和日志分析定位性能瓶颈。

## 约束

- 性能问题需要基线数据对比。
- 需区分带宽型、时延型、抖动型问题。
- 日志中的重传/超时/流控信息是重要线索。

## 流程

1. 使用 `urma_perftest` 建立性能基线。
2. 复现问题并收集性能数据（带宽、时延、抖动）。
3. 收集 UMQ/URPC 统计指标（`umq_stats_type_t`、`urpc_stats_type_t`）。
4. 收集日志中的重传、超时、流控、端口事件。
5. 根据数据类型定位瓶颈维度：链路、协议、资源、调度、内存。
6. 调整配置并验证修复效果。

## 能力

- 输出性能问题分类和对应排查方向。
- 输出 `urma_perftest` 关键指标解读。
- 输出 UMQ/URPC 统计指标与性能问题的关联。
- 输出常见性能优化建议。

## 规则

- 带宽低于预期时，优先检查链路宽度、速率、重传和流控。
- 时延抖动大时，优先检查 CPU 绑定、中断聚合、RNR、队列深度。
- 性能随时间下降时，优先检查资源泄漏、队列错误、温度/散热。
- 必须对比正常基线和异常数据，避免孤立判断。

## 性能问题分类

| 现象 | 可能原因 | 排查重点 |
|------|----------|----------|
| 带宽低 | 链路降级、重传、流控、队列深度不足 | 端口状态、ACK_TIMEOUT、流控统计 |
| 时延高 | 网络距离、CPU 调度、轮询/事件模式 | NUMA、CPU 绑定、中断 |
| 时延抖动大 | 中断聚合、RNR、队列错误、资源竞争 | 队列统计、RNR 错误 |
| 性能随时间下降 | 资源泄漏、队列错误、热降频 | 资源统计、温度日志 |
| 单流性能低 | 单队列限制、协议开销 | 队列配置、批量发送 |
| 多流性能低 | 资源竞争、锁竞争、多队列扩展性 | 队列数量、并发模型 |
| 线程/进程被挂起数秒到数十秒 | OS 调度延迟、CPU 饥饿、容器/虚拟机冻结、Cgroup 限制 | 调度延迟、CPU 使用率、steal time、ZmqEpoll EINTR |


## 关键日志模式

| 日志 | 含义 | 性能影响 |
|------|------|----------|
| `URMA_CR_ACK_TIMEOUT_ERR` | 重传超时 | 带宽下降、时延增加 |
| `URMA_CR_RNR_RETRY_CNT_EXC_ERR` | 接收端无缓冲 | 发送阻塞、时延增加 |
| `UMQ_ERR_EFLOWCTL` | 流控阻塞 | 发送速率受限 |
| `URMA_EVENT_PORT_DOWN` / `ELR_ERR` | 链路/硬件异常 | 通信中断或严重降速 |
| `rate limit` 摘要 | 高频错误 | 可能伴随性能问题 |
| `JETTY_LIMIT` / `QH_LIMIT` | 资源不足 | 无法扩展并发 |
| `[URMA_ELAPSED_THREAD_SHED]: urma_poll_jfc thread wake up after nanosleep(1us) cost Xus` | URMA 轮询线程被调度延迟阻塞 X 微秒 | 该线程无法及时处理事件，可能导致时延尖峰、连接/租约超时 |
| `Worker was hanged about X ms` | 应用检测到进程卡死 X 毫秒 | 通常由 OS 调度延迟或主线程阻塞导致，可能触发进程自重启 |
| `ZmqEpoll HandleEvent failed: ... epoll_wait is EINTR` | ZMQ epoll 被信号中断 | 常见于进程被挂起/恢复后，可能伴随调度延迟 |

### 调度延迟导致的长时间挂起

当日志中出现如下组合时，应优先排查系统调度层面：

```text
[URMA_ELAPSED_THREAD_SHED]: urma_poll_jfc thread wake up after nanosleep(1us) cost 2.00867e+07us, cpuid: 135, suggest: check OS scheduling overhead
etcd keep alive run failed, keep alive timer ElapsedMilliSecond: 20820.8
Failed to refresh lease: the new ttl is 0.
Worker was hanged about 20329.91 ms
ZmqEpoll HandleEvent failed: ... epoll_wait is EINTR
```

**排查方向：**
- 检查该时间段内 CPU 使用率、负载、steal time（`top`、`vmstat 1`、`cat /proc/stat`）。
- 检查是否存在 CPU 超售、Cgroup CPU quota 限制、容器 pause/resume。
- 检查系统日志是否有 OOM、进程冻结、Cgroup 相关事件。
- 检查是否启用了 CPU 节能模式或动态调频导致频率骤降。
- 检查进程内是否有长时间持有锁或阻塞系统调用的线程。


## 与统计结合

| 统计 | 关注点 |
|------|--------|
| `UMQ_STATS_TYPE_SEND/RECEIVE` | 实际收发速率 |
| `UMQ_ERR_STATS_TYPE_*` | 错误分布 |
| `urpc_stats_type_t` 请求/响应 | 成功率和吞吐量 |
| `urpc_stats_type_t` 队列/通道 | 资源使用和健康度 |

## 排查步骤

```text
性能低于基线
  ├── urma_perftest 是否正常？
  │     └── 否 → 链路/硬件问题
  ├── 是否有 ACK_TIMEOUT / RNR / 流控？
  │     └── 是 → 网络/流控/接收端问题
  ├── 队列/资源是否达到上限？
  │     └── 是 → 资源不足或泄漏
  ├── CPU/NUMA 绑定是否合理？
  │     └── 否 → 优化亲和性
  └── 是否随时间下降？
        └── 是 → 检查泄漏、热降频、错误累积
```

## 优化建议

1. **链路优化**：确保链路宽度/速率匹配，使用高质量线缆/光模块。
2. **队列优化**：根据并发数配置足够的队列深度和关联资源。
3. **CPU 优化**：绑定 NUMA 节点和核心，减少跨 NUMA 访问。
4. **流控优化**：平衡窗口大小和接收端处理能力。
5. **中断优化**：高吞吐场景使用轮询，低时延场景优化中断聚合。
6. **内存优化**：确保 MR 注册在本地 NUMA 节点，使用大页。

## 辅助命令

```bash
# 建立带宽基线
urma_perftest bw -s 65536 -n 1000 --server <peer_ip>

# 建立时延基线
urma_perftest lat -s 8 -n 1000 --server <peer_ip>

# 查看端口状态
urma_admin port show
```

## 问题上报模板

- 性能测试命令和结果（正常 vs 异常）
- UMQ/URPC 统计结果
- 日志中的重传/超时/流控/错误事件
- 链路配置（宽度、速率、ack_timeout）
- 队列和资源配置
- CPU/NUMA 绑定方式
- 复现步骤

## 注意事项

- 性能问题通常不是单一原因，需综合多项数据判断。
- 基线测试应在相同环境、相同配置下进行。
- 长时间运行后性能下降，需重点关注资源泄漏和热降频。
