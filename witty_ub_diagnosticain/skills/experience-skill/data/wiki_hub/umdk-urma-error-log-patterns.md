---
name: "UMDK URMA 错误日志模式"
description: "整理 URMA 用户态常见错误日志的关键模式、含义与初步排查方向，包括参数校验、初始化、资源分配、网络通信等错误类型。"
keywords:
  - UMDK
  - URMA
  - 错误日志
  - 故障模式
  - Invalid parameter
  - NULL pointer
  - no mem
  - failed to
references:
  - name: "UMDK v26.06.0_CAM 源码：urma_log.c"
    type: offline
    source: "umdk-v26.06.0_CAM/src/urma/lib/urma/core/urma_log.c"
  - name: "UMDK v26.06.0_CAM 源码：URMA 用户态头文件"
    type: offline
    source: "umdk-v26.06.0_CAM/src/urma/lib/urma/core/include/"
  - name: "UMDK v26.06.0_CAM 文档：URMA User Guide 6.5"
    type: offline
    source: "umdk-v26.06.0_CAM/doc/ch/urma/URMA User Guide.ch.md"
  - name: "UMDK v26.06.0_CAM GitCode 仓库"
    type: online
    source: "https://gitcode.com/openeuler/umdk/tags/v26.06.0_CAM"
---

# UMDK URMA 错误日志模式

## 概述

URMA 用户态错误日志通常出现在 `error` 或 `fatal` 级别。通过识别日志中的关键模式，可以快速定位问题类型并缩小排查范围。

## 常见错误模式

### 1. 参数校验失败

```text
[URMA][liburma][thread_id=...][...][...]Invalid parameter.
[URMA][liburma][thread_id=...][...][...]invalid parameter: <attr>
```

**含义：** 传入 API 的参数非法，如空指针、越界、不一致的句柄等。

**排查方向：**
- 检查调用时传入的指针是否为 NULL。
- 检查结构体字段是否按规范初始化。
- 检查参数取值范围是否在定义内。
- 检查是否混合使用了不同版本的 API 或句柄。

### 2. 空指针/空资源

```text
[URMA][liburma][thread_id=...][...][...]NULL pointer.
[URMA][liburma][thread_id=...][...][...]... is null
```

**含义：** 期望的非空指针或资源为 NULL。

**排查方向：**
- 确认前置 API 是否成功返回。
- 检查依赖对象是否被提前释放。
- 检查多线程环境下的资源生命周期。

### 3. 内存分配失败

```text
[URMA][liburma][thread_id=...][...][...]no mem
[URMA][liburma][thread_id=...][...][...]failed to allocate memory
```

**含义：** 内存分配失败，可能系统内存不足或达到限制。

**排查方向：**
- 检查系统内存使用情况：`free -h`、`cat /proc/meminfo`
- 检查进程是否设置了过小的内存限制。
- 检查是否存在内存泄漏或大量资源未释放。
- 检查是否创建了过量的 QP、CQ、内存域等对象。

### 4. 初始化/上下文创建失败

```text
[URMA][liburma][thread_id=...][...][...]failed to create context
[URMA][liburma][thread_id=...][...][...]failed to init device
```

**含义：** 设备或上下文初始化失败，通常与内核态驱动、硬件或权限有关。

**排查方向：**
- 检查内核态 UMDK 驱动是否加载：`lsmod | grep urma`
- 检查设备节点是否存在：`/dev/urma*`、`/dev/infiniband/*`
- 检查当前用户是否有访问设备权限。
- 检查 dmesg 中是否有内核态错误。

### 5. 资源查找/绑定失败

```text
[URMA][liburma][thread_id=...][...][...]failed to find ...
[URMA][liburma][thread_id=...][...][...]failed to bind ...
```

**含义：** 指定的资源未找到，或资源绑定失败。

**排查方向：**
- 确认资源 ID、名称是否正确。
- 检查资源是否已创建或已释放。
- 检查资源所属进程/上下文是否一致。

### 6. 网络/通信相关错误

```text
[URMA][liburma][thread_id=...][...][...]failed to connect
[URMA][liburma][thread_id=...][...][...]timeout
```

**含义：** 连接建立失败或通信超时。

**排查方向：**
- 检查网络配置、IP 地址、端口是否可达。
- 检查防火墙或安全组规则。
- 检查对端服务是否正常。
- 检查是否配置了合理的超时时间。

### 7. 内部状态不一致

```text
[URMA][liburma][thread_id=...][...][...]invalid state
[URMA][liburma][thread_id=...][...][...]state mismatch
```

**含义：** 对象状态不符合操作要求。

**排查方向：**
- 检查操作顺序是否符合 API 状态机。
- 检查是否并发访问导致状态错乱。
- 检查是否有异常路径未正确清理。

### 8. Jetty 被标记为无效 / 连接被清理

```text
[URMA_MODIFY_JETTY_TO_ERROR] Mark Jetty <id> invalid, remoteAddress=<ip:port>, remoteInstanceId=<uuid>
Retired jetty id <id> to pending delete
Remove UrmaConnection for <ip:port>
[URMA_NEED_CONNECT] No existing connection for remoteAddress: <ip:port>, ..., requires creation.
[URMA_NEED_CONNECT] CheckConnectionStable failed, remoteAddress=<ip:port>, rc=code: [Urma needs to reconnet], ...
```

**含义：** 对端节点被移除或连接失效，本地 Jetty 被置为错误状态并清理；后续访问需重建 URMA 连接。

**排查方向：**
- 检查对端节点是否因 etcd 租约失效、进程崩溃、端口冲突或健康检查失败而被移出集群。
- 检查集群事件（ADD/DELETE）时间线，确认节点状态变化是否早于 Jetty 失效。
- 检查网络连通性、防火墙、URMA 端口是否可达。
- 如果频繁重建，检查节点间网络抖动或节点反复上下线。

### 9. 速率限制摘要

```text
[URMA][liburma][thread_id=...][...][...]rate limit: N logs suppressed in last Xs
```

**含义：** 该日志点在过去 X 秒被抑制了 N 条。

**排查方向：**
- 找到该日志点对应的原始错误，通常是某条错误在循环中高频触发。
- 优先解决高频错误根因，而不是仅关注摘要本身。

## 排查通用流程

1. 查看错误日志中的 `function` / `Line` 字段，定位报错代码位置。
2. 检查日志级别，必要时开启 `debug` 级别复现。
3. 结合时间线，确认错误发生前后是否有配置变更、重启或资源变更。
4. 同时检查内核态日志（`dmesg`）和系统日志（`/var/log/messages`）。
5. 对参数类错误，优先检查上层调用；对资源/通信类错误，优先检查环境和驱动。

## 注意事项

- 错误日志中的线程 ID 可帮助定位多线程问题。
- 出现 `rate limit` 时，需先定位抑制前的原始错误。
- 如果日志回调被接管，原始日志可能不在 syslog 中，需到应用日志中查找。
