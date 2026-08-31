---
name: "UMDK UMQ 统计指标解读"
description: "介绍 UMQ 性能统计（umq_stats_type_t）和错误统计（umq_err_stats_type_t）的指标含义，以及如何结合日志分析性能和异常。"
keywords:
  - UMDK
  - UMQ
  - 统计指标
  - DFX
  - umq_stats_type_t
  - umq_err_stats_type_t
  - 性能统计
references:
  - name: "UMDK v26.06.0_CAM 源码：umq_types.h"
    type: offline
    source: "umdk-v26.06.0_CAM/src/urpc/include/umq/umq_types.h"
  - name: "UMDK v26.06.0_CAM GitCode 仓库"
    type: online
    source: "https://gitcode.com/openeuler/umdk/tags/v26.06.0_CAM"
---

# UMDK UMQ 统计指标解读

## 概述

UMQ 提供 `umq_stats_type_t` 性能统计和 `umq_err_stats_type_t` 错误统计。通过统计指标可以量化消息收发、读操作和各类错误，结合日志可快速定位性能瓶颈。

## 性能统计

| 指标 | 含义 |
|------|------|
| `UMQ_STATS_TYPE_SEND` | 发送消息数 |
| `UMQ_STATS_TYPE_RECEIVE` | 接收消息数 |
| `UMQ_STATS_TYPE_READ` | Read 操作数 |

## 错误统计

### Post 相关

| 指标 | 含义 |
|------|------|
| `UMQ_ERR_STATS_TYPE_POST_PARAM_INVALID` | post 参数非法次数 |
| `UMQ_ERR_STATS_TYPE_POST_SEND` | post send 失败次数 |
| `UMQ_ERR_STATS_TYPE_POST_RECV` | post recv 失败次数 |
| `UMQ_ERR_STATS_TYPE_POST_IO_DIRECTION_INVALID` | IO 方向非法次数 |
| `UMQ_ERR_STATS_TYPE_POST_DATA_SIZE_INVALID` | qbuf 数据大小非法次数 |
| `UMQ_ERR_STATS_TYPE_POST_SGE_NUM_INVALID` | SGE 数量非法次数 |
| `UMQ_ERR_STATS_TYPE_POST_WR_COUNT_INVALID` | WR 数量非法次数 |
| `UMQ_ERR_STATS_TYPE_POST_BIG_DATA` | post 大数据次数 |

### Poll 相关

| 指标 | 含义 |
|------|------|
| `UMQ_ERR_STATS_TYPE_POLL_PARAM_INVALID` | poll 参数非法次数 |
| `UMQ_ERR_STATS_TYPE_POLL_TX` | poll tx 失败次数 |
| `UMQ_ERR_STATS_TYPE_POLL_RX` | poll rx 失败次数 |
| `UMQ_ERR_STATS_TYPE_POLL_IO_DIRECTION_INVALID` | poll IO 方向非法次数 |

### Read 相关

| 指标 | 含义 |
|------|------|
| `UMQ_ERR_STATS_TYPE_READ` | read 失败次数 |
| `UMQ_ERR_STATS_TYPE_READ_BIND_CTX_INVALID` | read 绑定 ctx 非法次数 |
| `UMQ_ERR_STATS_TYPE_READ_TSEG_INVALID` | read TSeg 非法次数 |

### Enqueue/Dequeue 相关

| 指标 | 含义 |
|------|------|
| `UMQ_ERR_STATS_TYPE_ENQUEUE_PARAM_INVALID` | enqueue 参数非法次数 |
| `UMQ_ERR_STATS_TYPE_ENQUEUE_DATA_NUM_INVALID` | enqueue 数据数量非法次数 |
| `UMQ_ERR_STATS_TYPE_ENQUEUE_POST_TX_BATCH` | enqueue post tx batch 失败次数 |
| `UMQ_ERR_STATS_TYPE_ENQUEUE_SGE_NUM_INVALID` | enqueue SGE 数量非法次数 |
| `UMQ_ERR_STATS_TYPE_DEQUEUE_PARAM_INVALID` | dequeue 参数非法次数 |
| `UMQ_ERR_STATS_TYPE_DEQUEUE_BIND_CTX_INVALID` | dequeue 绑定 ctx 非法次数 |
| `UMQ_ERR_STATS_TYPE_DEQUEUE_SHM_QBUF` | dequeue shm qbuf 次数 |

### QBuf 分配

| 指标 | 含义 |
|------|------|
| `UMQ_ERR_STATS_TYPE_QBUF_ALLOC` | qbuf 分配失败次数 |
| `UMQ_ERR_STATS_TYPE_RX_BUF_CTX_ALLOC` | rx buf ctx 分配失败次数 |

## 使用方式

通过 `umq_dfx_cmd_t` 发起统计命令：

```c
umq_dfx_cmd_t cmd;
cmd.module_id = UMQ_DFX_MODULE_STATS;
cmd.stats_cmd_id = UMQ_STATS_CMD_GET_RESULT;
// 调用 umq_dfx 接口获取 umq_stats_infos_t
```

## 与日志结合分析

| 异常 | 表现 | 排查方向 |
|------|------|----------|
| 发送性能低 | SEND 远低于预期 | 检查链路、流控、CPU 绑定 |
| 接收丢消息 | RECEIVE 不增长，POST_SEND/POST_RECV 错误高 | 检查接收端 QBuf、dequeue 速度 |
| 流控阻塞 | POST_SEND/ENQUEUE_POST_TX_BATCH 错误高 | 检查接收窗口、流控配置 |
| 资源不足 | QBUF_ALLOC / RX_BUF_CTX_ALLOC 错误高 | 增加 QBuf 池或检查内存 |
| 参数错误 | POST_PARAM_INVALID / POLL_PARAM_INVALID 高 | 检查应用调用参数 |

## 注意事项

- 统计命令需要先 `START`，停止或获取结果前建议 `STOP`。
- 统计是累积值，分析时应关注变化速率而不是绝对值。
- 错误统计和日志应结合查看，日志提供具体调用点，统计提供全局趋势。
