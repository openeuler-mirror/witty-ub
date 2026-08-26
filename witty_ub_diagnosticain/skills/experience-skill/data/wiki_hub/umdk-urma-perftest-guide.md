---
name: "UMDK URMA 性能测试工具 urma_perftest 使用指南"
description: "介绍 URMA 性能测试工具 urma_perftest 的常用测试类型、参数和结果解读，以及如何结合日志分析性能问题。"
keywords:
  - UMDK
  - URMA
  - urma_perftest
  - 性能测试
  - 带宽
  - 时延
  - DFX
references:
  - name: "UMDK v26.06.0_CAM 文档：URMA User Guide 6.4.1"
    type: offline
    source: "umdk-v26.06.0_CAM/doc/ch/urma/URMA User Guide.ch.md"
  - name: "UMDK v26.06.0_CAM 源码：urma_perftest"
    type: offline
    source: "umdk-v26.06.0_CAM/src/urma/tools/urma_perftest/"
  - name: "UMDK v26.06.0_CAM GitCode 仓库"
    type: online
    source: "https://gitcode.com/openeuler/umdk/tags/v26.06.0_CAM"
---

# UMDK URMA 性能测试工具 urma_perftest 使用指南

## 概述

`urma_perftest` 是 URMA 提供的性能测试工具，用于测量带宽、时延、消息速率等指标。性能问题排查时，可通过 `urma_perftest` 复现问题，并与日志中的异常事件关联。

## 基本用法

```bash
urma_perftest <test> [options] --server <server_addr>
```

常用测试类型：

| 测试类型 | 说明 |
|----------|------|
| `bw` | 带宽测试（Bandwidth） |
| `lat` | 时延测试（Latency） |
| `bidir_bw` | 双向带宽测试 |
| `read_lat` | Read 操作时延 |
| `write_lat` | Write 操作时延 |
| `send_lat` | Send 操作时延 |

## 常用参数

| 参数 | 说明 |
|------|------|
| `-d` / `--device` | 指定设备名 |
| `-p` / `--port` | 指定端口号 |
| `-s` / `--size` | 消息大小（字节） |
| `-n` / `--iterations` | 迭代次数 |
| `-t` / `--tx_depth` | 发送队列深度 |
| `-r` / `--rx_depth` | 接收队列深度 |
| `--ack_timeout` | ACK 超时时间（默认 15） |
| `--use_inline` | 使用 inline 发送 |
| `--use_event` | 使用事件通知 |
| `--report_gbits` | 以 Gbps 报告带宽 |

## 结果解读

### 带宽测试

```text
#bytes #iterations    BW peak[Gb/sec]    BW average[Gb/sec]   MsgRate[Mpps]
65536  1000           100.00             98.50                0.18
```

关键字段：

| 字段 | 含义 |
|------|------|
| `BW peak` | 峰值带宽 |
| `BW average` | 平均带宽 |
| `MsgRate` | 消息速率（百万消息/秒） |

### 时延测试

```text
#bytes #iterations    t_min[usec]    t_max[usec]    t_avg[usec]
8      1000           1.20           5.60           1.50
```

关键字段：

| 字段 | 含义 |
|------|------|
| `t_min` | 最小时延 |
| `t_max` | 最大时延 |
| `t_avg` | 平均时延 |

## 与日志结合分析

### 带宽低于预期

日志检查项：
- 是否有 `URMA_CR_ACK_TIMEOUT_ERR`（重传超时）
- 是否有 `URMA_CR_WR_FLUSH_ERR`（Jetty 错误状态）
- 是否有 `URMA_EVENT_PORT_DOWN` 或 `ELR_ERR`
- 是否有 `rate limit` 摘要（日志风暴）

排查方向：
- 检查链路宽度、速率是否与预期一致（`urma_admin port show`）
- 检查消息大小、队列深度配置是否最优
- 检查是否启用 inline 或走慢路径
- 检查网络是否丢包或拥塞

### 时延抖动大

日志检查项：
- 检查 `t_max` 与 `t_avg` 差异是否由异常事件导致
- 检查是否有 `URMA_CR_RNR_RETRY_CNT_EXC_ERR`（接收端无缓冲）
- 检查 CPU 调度、NUMA 亲和性是否配置合理

排查方向：
- 绑定 NUMA 节点和 CPU 核心
- 检查中断聚合设置
- 使用事件通知 vs 轮询模式的差异

### 测试失败

日志检查项：
- 检查是否有 `URMA_EVENT_PORT_DOWN`
- 检查对端是否启动服务
- 检查 `ack_timeout` 是否过短
- 检查网络路由是否可达

## 常用命令示例

### 带宽测试

服务端：

```bash
urma_perftest bw --server 0.0.0.0
```

客户端：

```bash
urma_perftest bw -d urma0 -p 1 -s 65536 -n 1000 --server 192.168.1.1
```

### 时延测试

服务端：

```bash
urma_perftest lat --server 0.0.0.0
```

客户端：

```bash
urma_perftest lat -s 8 -n 1000 --server 192.168.1.1
```

## 注意事项

- 服务端和客户端的测试类型、消息大小、迭代次数应一致。
- 确保两端设备、端口状态正常（`urma_admin port show`）。
- 大流量测试时建议开启独立日志目录和日志轮转。
- 性能测试前应确保系统无其他高负载进程。
- 对端地址应使用 UPI 或网络可直达地址，具体取决于配置。
