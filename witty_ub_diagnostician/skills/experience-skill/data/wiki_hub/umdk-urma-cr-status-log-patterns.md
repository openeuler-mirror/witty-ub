---
name: "UMDK URMA CR 操作状态码日志模式"
description: "整理 URMA 用户态 CR（Converged Resource，融合资源）相关操作的状态码含义、常见错误日志与日志分析要点。"
keywords:
  - UMDK
  - URMA
  - CR
  - 融合资源
  - 状态码
  - urma_status_t
  - 错误码
  - 日志分析
references:
  - name: "UMDK v26.06.0_CAM 源码：urma_types.h"
    type: offline
    source: "umdk-v26.06.0_CAM/src/urma/lib/urma/api/include/urma_types.h"
  - name: "UMDK v26.06.0_CAM 源码：urma_core.h"
    type: offline
    source: "umdk-v26.06.0_CAM/src/urma/lib/urma/core/include/urma_core.h"
  - name: "UMDK v26.06.0_CAM 文档：URMA User Guide"
    type: offline
    source: "umdk-v26.06.0_CAM/doc/ch/urma/URMA User Guide.ch.md"
  - name: "UMDK v26.06.0_CAM GitCode 仓库"
    type: online
    source: "https://gitcode.com/openeuler/umdk/tags/v26.06.0_CAM"
---

# UMDK URMA CR 操作状态码日志模式

## 概述

URMA 中 `urma_status_t` 枚举定义了用户态 API 的通用返回状态。CR（Converged Resource）相关操作在日志中通常会输出对应的状态码字符串或状态码数值。理解这些状态码有助于从日志中快速判断失败原因。

## 常见状态码含义

| 状态码 | 含义 | 典型场景 |
|--------|------|----------|
| `URMA_SUCCESS` | 成功 | 操作正常完成 |
| `URMA_FAIL` | 通用失败 | 未分类的错误 |
| `URMA_EINVAL` | 参数非法 | 传入 NULL、越界、不匹配句柄等 |
| `URMA_ENOMEM` | 内存不足 | 分配内存/资源失败 |
| `URMA_ENODEV` | 设备不存在 | 设备未初始化或驱动未加载 |
| `URMA_ENOENT` | 资源不存在 | 找不到指定资源 |
| `URMA_EBUSY` | 资源忙 | 资源被占用或并发冲突 |
| `URMA_EAGAIN` | 重试 | 临时失败，可稍后重试 |
| `URMA_ETIMEDOUT` | 超时 | 连接或操作超时 |
| `URMA_EPERM` | 权限不足 | 无权限访问设备或资源 |
| `URMA_EIO` | IO 错误 | 硬件/驱动通信失败 |
| `URMA_ENOSPC` | 空间不足 | 资源表、队列深度等耗尽 |
| `URMA_EUNREACH` | 不可达 | 网络/对端不可达 |

## 状态码在日志中的常见形式

### 1. 直接打印状态码名称

```text
[URMA][liburma][thread_id=...][...][urma_create_cr[Line=...]]failed to create cr, ret: URMA_EINVAL
```

**排查方向：** 检查 `urma_create_cr` 入参，确认 `cr_attr` 各字段已正确初始化。

### 2. 打印状态码数值

```text
[URMA][liburma][thread_id=...][...][...]return status: -22
```

说明：`-22` 通常对应 `EINVAL`。

**排查方向：** 将数值映射到状态码定义，通常负数取绝对值对应 `errno` 含义。

### 3. CR 创建/销毁相关

```text
[URMA][liburma][thread_id=...][...][urma_create_cr]failed to create cr
[URMA][liburma][thread_id=...][...][urma_destroy_cr]failed to find cr handle
```

**排查方向：**
- 确认 `context` 是否已正确创建。
- 确认 `cr_attr` 中 `tp`（transport type）、`flag` 等字段是否合法。
- 检查是否重复销毁或使用了已销毁的句柄。

### 4. CR 配置/查询相关

```text
[URMA][liburma][thread_id=...][...][urma_cr_set_cfg]invalid config attr
[URMA][liburma][thread_id=...][...][urma_cr_query]failed to query cr status
```

**排查方向：**
- 检查配置属性是否支持当前 CR 类型。
- 检查查询时传入的句柄是否有效。

### 5. 与底层 URPC 交互失败

```text
[URMA][liburma][thread_id=...][...][...]failed to send req to udriver
[URMA][liburma][thread_id=...][...][...]udriver return fail
```

**排查方向：**
- 检查内核态驱动是否正常运行。
- 检查 `/dev/urma*` 设备节点是否可访问。
- 查看 `dmesg` 中是否有内核态错误。

## 状态码快速映射表

```
-EINVAL   -> 参数问题
-ENOMEM   -> 内存/资源不足
-ENODEV   -> 驱动/设备问题
-ENOENT   -> 资源未找到
-EBUSY    -> 并发/占用问题
-EAGAIN   -> 临时失败，可重试
-ETIMEDOUT-> 超时
-EPERM    -> 权限问题
-EIO      -> 硬件/驱动通信
-ENOSPC   -> 资源表耗尽
-EUNREACH -> 网络/对端问题
```

## 日志分析建议

1. 先找到错误日志中返回的状态码。
2. 根据状态码确定问题类型（参数、资源、驱动、网络、权限等）。
3. 结合 `function` 和 `Line` 字段定位到具体 API。
4. 在对应 API 的调用链上向前回溯，检查入参和前置状态。
5. 对于 `URMA_FAIL` 等通用错误，开启 `debug` 日志获取更详细的上下文。

## 注意事项

- 状态码字符串在不同版本中可能略有差异，必要时查看源码中的枚举定义。
- 部分日志会同时打印内核态返回的错误码，需要结合内核日志分析。
- 如果日志被应用层接管，状态码可能以格式化后的形式出现，需保留原始日志字段。
