---
name: "yuanrong-datasystem 访问日志模式"
description: "汇总 openYuanrong datasystem 访问日志（access.log / ds_client_access_{pid}.log）的接口 action 前缀、status_code 含义、关键参数与典型异常模式。"
keywords:
  - yuanrong-datasystem
  - datasystem
  - 访问日志
  - access.log
  - status_code
  - DS_KV_CLIENT
  - DS_OBJECT_CLIENT
  - DS_OBJECT_POSIX
references:
  - name: "yuanrong-datasystem 0.8.1.rc20 日志指南"
    type: offline
    source: "yuanrong-datasystem-0.8.1.rc20/docs/source_zh_cn/appendix/log_guide.md"
  - name: "yuanrong-datasystem 0.8.1.rc20 错误码定义"
    type: offline
    source: "yuanrong-datasystem-0.8.1.rc20/include/datasystem/utils/status.h"
---

# yuanrong-datasystem 访问日志模式

## 概述

访问日志记录每一次访问客户端/服务端的请求，每个请求一条日志。字段包括 `status_code`、`action`、`cost`、`data_size`、`request_param` 和 `response_param`。通过分析访问日志，可以快速识别接口级错误和性能瓶颈。

## action 前缀约定

| 前缀 | 含义 | 示例 |
|------|------|------|
| `DS_KV_CLIENT` | KV Cache 客户端接口 | `DS_KV_CLIENT_Get`、`DS_KV_CLIENT_Set` |
| `DS_OBJECT_CLIENT` | Object Cache 客户端接口 | `DS_OBJECT_CLIENT_Create`、`DS_OBJECT_CLIENT_Publish` |
| `DS_OBJECT_POSIX` | Worker Object POSIX 接口 | `DS_OBJECT_POSIX_Read`、`DS_OBJECT_POSIX_Write` |
| `DS_STREAM_CLIENT` | Stream Cache 客户端接口 | `DS_STREAM_CLIENT_CreateProducer`、`DS_STREAM_CLIENT_CreateConsumer` |
| `DS_HETERO_CLIENT` | 异构对象客户端接口 | `DS_HETERO_CLIENT_Create`、`DS_HETERO_CLIENT_Get` |
| `DS_WORKER` | Worker 内部接口 | `DS_WORKER_Register` 等 |

## status_code 含义

- `0`：成功。
- `1–36`：通用错误（如 `K_DUPLICATED=1`、`K_INVALID=2`、`K_NOT_FOUND=3`、`K_OUT_OF_MEMORY=6`、`K_TIMEOUT=24/25`）。
- `1000–1010`：RPC/传输错误（如 `K_RPC_DEADLINE_EXCEEDED=1001`、`K_URMA_NEED_CONNECT=1006`）。
- `2000–2006`：Object Cache 错误（如 `K_OC_ALREADY_SEALED=2000`）。
- `3000–3010`：Stream Cache 错误（如 `K_SC_STREAM_NOT_FOUND=3000`）。
- `5000–5004`：异构对象错误（如 `K_CUDA_ERROR=5003`、`K_NCCL_ERROR=5004`）。

完整定义参考 `include/datasystem/utils/status.h`。

## 关键参数字段

| 参数 | 说明 | 常见场景 |
|------|------|----------|
| Object_key | 对象 ID | Create/Publish/Get/Delete |
| object_keys | 批量对象 KEY | BatchGet |
| Nested_keys | 嵌套引用 KEY | 嵌套对象操作 |
| keep | 是否手动管理生命周期 | 对象创建 |
| Write_mode | 写模式 | Set/Publish |
| consistency_type | 一致性类型 | Get/Set |
| is_seal | 是否封印 | Object 操作 |
| is_retry | 是否重试 | 所有接口 |
| ttl_second | TTL 秒数 | KV Set |
| sub_timeout | 订阅超时 | Get 订阅 |
| timeout | 接口超时 | 所有接口 |

## 典型异常模式

### 1. 高频超时（K_RPC_DEADLINE_EXCEEDED / K_WORKER_TIMEOUT / K_MASTER_TIMEOUT）

```text
status_code=1001 action=DS_KV_CLIENT_Get cost=...
```

可能原因：
- 目标 Worker 线程池满载，请求排队过长。
- 网络/传输层异常（URMA 连接失效、TCP 拥塞）。
- 目标节点被判定为 lost/dead，请求路由失败。

排查：
- 检查 `resource.log` 中线程池利用率。
- 检查运行日志中 URMA/ETCD 相关错误。
- 检查目标节点是否发生 lease 失效或 scale 事件。

### 2. 对象不存在（K_NOT_FOUND / K_OC_OBJECT_NOT_IN_USED）

```text
status_code=3 action=DS_OBJECT_CLIENT_Get ...
status_code=2001 action=DS_OBJECT_CLIENT_Get ...
```

可能原因：
- 对象确实未创建或已过期。
- 对象所在 Worker 已下线，元数据未迁移完成。
- L2 缓存配置错误或不可达。

排查：
- 核对 Object_key 和创建时间。
- 检查对象所在 Worker 是否在线。
- 检查 L2 缓存类型和路径配置。

### 3. 重复创建（K_DUPLICATED / K_OC_KEY_ALREADY_EXIST）

```text
status_code=1 action=DS_OBJECT_CLIENT_Create ...
status_code=2004 action=DS_OBJECT_CLIENT_Create ...
```

可能原因：
- 应用重复发布同一 key。
- 重试机制导致重复请求。
- `existence` 参数未正确设置。

排查：
- 检查 `is_retry` 参数和请求幂等性。
- 检查应用是否对同一 key 并发创建。

### 4. 资源不足（K_OUT_OF_MEMORY / K_NO_SPACE / K_LRU_HARD_LIMIT）

```text
status_code=6 action=DS_OBJECT_CLIENT_Publish ...
status_code=13 action=DS_KV_CLIENT_Set ...
status_code=34 action=DS_OBJECT_CLIENT_Publish ...
```

可能原因：
- 共享内存或 Spill 磁盘耗尽。
- LRU 硬限制触发。
- 大对象写入导致瞬间内存不足。

排查：
- 查看 `resource.log` 中 `shm_info`、`spill_disk_info` 使用率。
- 检查对象大小和缓存命中率。
- 考虑扩容或调整 `eviction_reserve_mem_threshold_mb`。

### 5. 版本不匹配（K_CLIENT_WORKER_VERSION_MISMATCH）

```text
status_code=28 action=DS_WORKER_Register ...
```

可能原因：
- Client 与 Worker 版本不兼容。
- 升级过程中存在新旧版本混部。

排查：
- 确认 Client 和 Worker 版本一致。
- 检查升级顺序和兼容性说明。

## 解析示例

### 统计高频失败接口

```bash
awk -F'|' '$9 != 0 {print $10, $9}' access.log | sort | uniq -c | sort -rn | head -20
```

### 统计耗时最高的 Get 请求

```bash
awk -F'|' '$10 == "DS_KV_CLIENT_Get" {print $11, $6}' access.log | sort -rn | head -20
```

### 提取所有 Publish 失败的请求

```bash
awk -F'|' '$10 ~ /DS_OBJECT_CLIENT_Publish/ && $9 != 0' access.log
```

## 注意事项

- 访问日志仅记录请求级信息，深入根因需结合运行日志和 `resource.log`。
- `cost` 字段单位为 us，适合量化接口延迟。
- `data_size` 主要用于 Publish 请求，分析大对象写入时非常有用。
- `request_param` 和 `response_param` 超长会被截断，可能无法获取完整参数。
