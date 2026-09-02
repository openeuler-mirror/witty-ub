---
name: "yuanrong-datasystem 异构对象日志模式"
description: "汇总 openYuanrong datasystem 异构对象（Hetero Object）的接口日志模式、错误码、H2D/D2H/D2D/P2P 传输和典型问题排查方法。"
keywords:
  - yuanrong-datasystem
  - datasystem
  - 异构对象
  - Hetero
  - H2D
  - D2H
  - D2D
  - HCCL
  - P2P
  - NPU
references:
  - name: "yuanrong-datasystem 0.8.1.rc20 Hetero Client 实现"
    type: offline
    source: "yuanrong-datasystem-0.8.1.rc20/src/datasystem/client/hetero_cache/hetero_client.cpp"
  - name: "yuanrong-datasystem 0.8.1.rc20 错误码定义"
    type: offline
    source: "yuanrong-datasystem-0.8.1.rc20/include/datasystem/utils/status.h"
---

# yuanrong-datasystem 异构对象日志模式

## 概述

异构对象支持 CPU 内存与设备内存（昇腾 NPU、GPU）之间的数据交换，包括 H2D、D2H、D2D 和 P2P 传输。本文档汇总相关接口日志模式、错误码和排查方法。

## 1. 接口 action

| action | 说明 |
|--------|------|
| DS_HETERO_CLIENT_INIT | 初始化 |
| DS_HETERO_CLIENT_SHUTDOWN | 关闭 |
| DS_HETERO_CLIENT_MGETH2D | Host 到 Device 批量获取 |
| DS_HETERO_CLIENT_ASYNCMGETH2D | 异步 H2D |
| DS_HETERO_CLIENT_MSETD2H | Device 到 Host 批量设置 |
| DS_HETERO_CLIENT_ASYNCMSETD2H | 异步 D2H |
| DS_HETERO_CLIENT_DELETE | 删除 |
| DS_HETERO_CLIENT_DEVPUBLISH | 设备内存发布 |
| DS_HETERO_CLIENT_DEVSUBSCRIBE | 设备内存订阅 |
| DS_HETERO_CLIENT_DEVDELETE | 设备删除 |
| DS_HETERO_CLIENT_DEVMSET | 设备批量设置 |
| DS_HETERO_CLIENT_DEVMGET | 设备批量获取 |
| DS_HETERO_CLIENT_GETMETAINFO | 获取元信息 |
| DS_HETERO_CLIENT_EXIST | 判断是否存在 |
| DS_HETERO_CLIENT_GENERATEKEY | 生成 key |

## 2. 常见错误码

| 错误码 | 含义 | 排查方向 |
|--------|------|----------|
| K_ACL_ERROR=5000 | ACL 错误 | 昇腾驱动和 ACL 日志 |
| K_HCCL_ERROR=5001 | HCCL 错误 | HCCL 通信组、设备拓扑 |
| K_FUTURE_TIMEOUT=5002 | Future 超时 | 异步操作等待超时 |
| K_CUDA_ERROR=5003 | CUDA 错误 | NVIDIA 驱动、GPU 内存 |
| K_NCCL_ERROR=5004 | NCCL 错误 | NCCL 日志、GPU 拓扑 |

## 3. 常见错误模式

### 3.1 未编译支持异构对象

```text
Hetero function not compiled in.
```

说明：需要重新编译开启异构对象支持。

### 3.2 ACL 错误

```text
status_code=5000 action=DS_HETERO_CLIENT_MGETH2D ...
```

可能原因：昇腾 ACL 调用失败、设备内存不足、设备 ID 错误。

### 3.3 HCCL 错误

```text
status_code=5001 action=...
```

可能原因：HCCL 通信组初始化失败、卡间通信错误、拓扑不一致。

### 3.4 CUDA 错误

```text
status_code=5003 action=...
```

可能原因：CUDA API 失败、GPU 内存不足、驱动异常。

### 3.5 NCCL 错误

```text
status_code=5004 action=...
```

可能原因：NCCL 通信失败、GPU 卡间通信异常。

### 3.6 Future 超时

```text
status_code=5002 action=DS_HETERO_CLIENT_ASYNCMGETH2D ...
```

可能原因：异步设备操作未完成、设备队列阻塞、传输延迟。

## 4. P2P 传输

P2P 传输允许设备间直接访问。失败时可能回退到 Host 内存中转，日志中可能出现相关提示。

## 5. 解析示例

### 统计异构接口错误码

```bash
awk -F'|' '$10 ~ /DS_HETERO_CLIENT/ && $9 != 0 {print $10, $9}' access.log | sort | uniq -c | sort -rn
```

### 提取设备相关错误

```bash
awk -F'|' '$9 >= 5000 && $9 <= 5004' access.log
```

### 检查 P2P 日志

```bash
grep -i "P2P" datasystem_worker.INFO.log ds_client_*.INFO.log
```

## 注意事项

- 异构对象错误需要结合硬件驱动日志和设备监控信息。
- H2D/D2H 是大对象传输，耗时显著，需关注 cost 字段。
- 异步操作需正确等待 Future，避免资源泄漏。
- 多设备场景下，设备 ID 和拓扑配置错误是常见问题。
- P2P 传输失败会回退到 Host 中转，性能下降。
