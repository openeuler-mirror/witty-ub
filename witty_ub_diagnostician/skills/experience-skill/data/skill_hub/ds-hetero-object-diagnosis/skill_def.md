---
name: ds-hetero-object-diagnosis
description: >
  介绍 openYuanrong datasystem 异构对象（Hetero Object）的日志分析方法，覆盖 H2D/D2H/D2D 传输、
  P2P 传输、HCCL 卡间直通、昇腾 NPU 相关错误码和典型问题。
license: MIT
compatibility: yuanrong-datasystem 0.8.1.rc20
metadata:
  author: yuanrong-datasystem-log-analysis
  version: "1.0"
  keywords: [yuanrong-datasystem, datasystem, 异构对象, Hetero, H2D, D2H, D2D, HCCL, P2P, NPU]
allowed-tools: Bash(grep:*) Bash(awk:*) Bash(sed:*) Bash(cat:*)
---

# yuanrong-datasystem 异构对象诊断 Skill

## 概述

异构对象（Hetero Object）支持 CPU 内存与设备内存（如昇腾 NPU、GPU）之间的数据交换，包括 H2D（Host to Device）、D2H（Device to Host）、D2D（Device to Device）和 P2P 传输。分析异构对象日志需要关注 `DS_HETERO_CLIENT_*` action、设备相关错误码（5000–5004）和 HCCL/P2P 传输日志。

## 约束

- 异构对象需要编译时开启 `WITH_HETERO` 等宏。
- 设备内存操作依赖具体硬件驱动（如 HCCL、CUDA、NCCL）。
- P2P 传输需要设备间支持直接访问。
- 异构对象接口与 Object Cache 共享底层对象存储。

## 流程

1. 确认是否编译支持异构对象（`IsCompileWithHetero`）。
2. 在访问日志中过滤 `DS_HETERO_CLIENT_*` action。
3. 关注设备相关错误码（K_ACL_ERROR=5000、K_HCCL_ERROR=5001、K_CUDA_ERROR=5003、K_NCCL_ERROR=5004）。
4. 检查 H2D/D2H/D2D 操作日志和耗时。
5. 检查 P2P 传输和 HCCL 通信组初始化日志。
6. 检查设备内存使用情况和 OOM 相关错误。

## 能力

- 输出异构对象接口 action 列表和常见错误码。
- 输出 H2D/D2H/D2D 传输问题的排查方向。
- 输出 HCCL/P2P 初始化失败和通信错误的排查方向。
- 输出设备内存不足和 Future 超时的判断方法。

## 规则

- 异构对象功能需要编译时开启，未开启时接口会返回错误。
- 设备操作错误通常伴随驱动错误码，需要结合驱动日志分析。
- P2P 传输需要设备拓扑支持，否则可能回退到通过 Host 内存中转。
- 异步操作（AsyncMGetH2D/AsyncMSetD2H）需要关注 Future 超时。

## 接口 action 列表

| action | 说明 |
|--------|------|
| DS_HETERO_CLIENT_INIT | 初始化 HeteroClient |
| DS_HETERO_CLIENT_SHUTDOWN | 关闭 HeteroClient |
| DS_HETERO_CLIENT_MGETH2D | Host 到 Device 批量获取 |
| DS_HETERO_CLIENT_ASYNCMGETH2D | 异步 H2D 批量获取 |
| DS_HETERO_CLIENT_MSETD2H | Device 到 Host 批量设置 |
| DS_HETERO_CLIENT_ASYNCMSETD2H | 异步 D2H 批量设置 |
| DS_HETERO_CLIENT_DELETE | 删除异构对象 |
| DS_HETERO_CLIENT_DEVPUBLISH | 设备内存发布 |
| DS_HETERO_CLIENT_DEVSUBSCRIBE | 设备内存订阅 |
| DS_HETERO_CLIENT_DEVDELETE | 设备删除 |
| DS_HETERO_CLIENT_DEVMSET | 设备批量设置 |
| DS_HETERO_CLIENT_DEVMGET | 设备批量获取 |
| DS_HETERO_CLIENT_GETMETAINFO | 获取元信息 |
| DS_HETERO_CLIENT_EXIST | 判断是否存在 |
| DS_HETERO_CLIENT_GENERATEKEY | 生成 key |

## 常见错误模式

### 1. 未编译支持异构对象

```text
Hetero function not compiled in.
```

说明：当前版本未编译异构对象支持，需要重新编译开启相关选项。

### 2. ACL 错误（K_ACL_ERROR=5000）

```text
status_code=5000 action=DS_HETERO_CLIENT_MGETH2D ...
```

可能原因：
- 昇腾 ACL 调用失败。
- 设备内存操作失败。

排查：
- 检查昇腾驱动和 ACL 日志。
- 检查设备内存是否足够。
- 检查设备 ID 是否正确。

### 3. HCCL 错误（K_HCCL_ERROR=5001）

```text
status_code=5001 action=... 
```

可能原因：
- HCCL 通信组初始化失败。
- 卡间通信错误。
- 多卡拓扑不一致。

排查：
- 检查 HCCL 通信组配置。
- 检查设备拓扑和链路。
- 检查昇腾驱动和固件版本。

### 4. CUDA 错误（K_CUDA_ERROR=5003）

```text
status_code=5003 action=... 
```

可能原因：
- CUDA API 调用失败。
- GPU 内存不足。
- CUDA 驱动异常。

排查：
- 检查 NVIDIA 驱动和 CUDA 日志。
- 检查 GPU 内存使用情况。

### 5. NCCL 错误（K_NCCL_ERROR=5004）

```text
status_code=5004 action=... 
```

可能原因：
- NCCL 通信失败。
- GPU 卡间通信异常。

排查：
- 检查 NCCL 日志和环境变量。
- 检查 GPU 拓扑和 NVLink 状态。

### 6. Future 超时（K_FUTURE_TIMEOUT=5002）

```text
status_code=5002 action=DS_HETERO_CLIENT_ASYNCMGETH2D ...
```

可能原因：
- 异步操作未完成。
- 设备操作阻塞或排队过长。
- 网络/传输层延迟。

排查：
- 检查设备队列深度。
- 增加 Future 等待超时。
- 检查设备内存和传输带宽。

## 解析示例

### 统计异构接口错误码

```bash
awk -F'|' '$10 ~ /DS_HETERO_CLIENT/ && $9 != 0 {print $10, $9}' access.log | sort | uniq -c | sort -rn
```

### 提取设备相关错误

```bash
awk -F'|' '$9 >= 5000 && $9 <= 5004' access.log
```

### 检查 P2P 传输日志

```bash
grep -i "P2P" datasystem_worker.INFO.log ds_client_*.INFO.log
```

## 注意事项

- 异构对象错误通常需要结合硬件驱动日志和设备监控信息。
- H2D/D2H 操作是耗时操作，大对象传输可能显著影响性能。
- 异步操作需要正确等待 Future 完成，避免资源泄漏。
- P2P 传输失败时会回退到 Host 中转，性能会下降。
- 多设备场景下，设备 ID 和拓扑配置错误是常见问题。
