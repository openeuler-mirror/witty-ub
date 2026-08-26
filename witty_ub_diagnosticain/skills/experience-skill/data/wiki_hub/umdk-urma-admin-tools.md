---
name: "UMDK URMA 管理工具 urma_admin 使用指南"
description: "介绍 URMA 管理工具 urma_admin 的常用查询命令、输出字段含义，以及如何结合日志定位设备、端口、拓扑和 UPI 问题。"
keywords:
  - UMDK
  - URMA
  - urma_admin
  - 管理工具
  - 端口状态
  - 拓扑查询
  - DFX
references:
  - name: "UMDK v26.06.0_CAM 文档：URMA User Guide 6.4"
    type: offline
    source: "umdk-v26.06.0_CAM/doc/ch/urma/URMA User Guide.ch.md"
  - name: "UMDK v26.06.0_CAM 源码：urma_admin"
    type: offline
    source: "umdk-v26.06.0_CAM/src/urma/tools/urma_admin/"
  - name: "UMDK v26.06.0_CAM GitCode 仓库"
    type: online
    source: "https://gitcode.com/openeuler/umdk/tags/v26.06.0_CAM"
---

# UMDK URMA 管理工具 urma_admin 使用指南

## 概述

`urma_admin` 是 URMA 提供的用户态管理工具，用于查询设备属性、端口状态、TP 信息、拓扑、UPI 等。在日志分析过程中，经常需要结合 `urma_admin` 的输出确认硬件状态。

## 基本用法

```bash
urma_admin <command> [options]
```

常用命令：

| 命令 | 作用 |
|------|------|
| `urma_admin dev show` | 显示所有 URMA 设备 |
| `urma_admin port show` | 显示所有端口状态 |
| `urma_admin tp show` | 显示 TP（Transport Point）信息 |
| `urma_admin jetty show` | 显示 Jetty 信息 |
| `urma_admin jfs show` | 显示 JFS（Jetty File Service）信息 |
| `urma_admin jfc show` | 显示 JFC（Jetty File Completion）信息 |
| `urma_admin upi show` | 显示 UPI（Unit Port Information）信息 |
| `urma_admin topo show` | 显示拓扑信息 |

## 设备信息查询

```bash
urma_admin dev show
```

输出关键字段：

| 字段 | 含义 |
|------|------|
| `dev_name` | 设备名 |
| `dev_id` | 设备 ID |
| `fw_ver` | 固件版本 |
| `node_guid` | 节点 GUID |

## 端口状态查询

```bash
urma_admin port show
```

输出关键字段：

| 字段 | 含义 |
|------|------|
| `port_num` | 端口号 |
| `state` | 端口状态：DOWN / INIT / ACTIVE |
| `link_width` | 链路宽度：X1 / X2 / X4 / X8 / X16 / X32 |
| `speed` | 链路速率 |
| `mtu` | 最大传输单元 |

## 状态说明

| 状态 | 含义 |
|------|------|
| `DOWN` | 端口未连接或已断开 |
| `INIT` | 端口初始化中 |
| `ACTIVE` | 端口正常工作中 |

## 与日志结合排查

### 日志出现 PORT_DOWN 事件

```text
[URMA][liburma][...][...]URMA_EVENT_PORT_DOWN
```

排查步骤：

1. 执行 `urma_admin port show`，确认对应端口状态是否为 `DOWN`。
2. 检查物理连接（网线、光模块、对端状态）。
3. 检查 `dmesg` 中是否有驱动检测到的链路中断或复位。
4. 检查固件版本是否存在已知链路问题。

### 日志出现 ACK_TIMEOUT

```text
[URMA][...][...]status: URMA_CR_ACK_TIMEOUT_ERR
```

排查步骤：

1. 执行 `urma_admin port show`，确认链路状态、速率、宽度。
2. 检查对端是否可达，网络是否有丢包或拥塞。
3. 使用 `urma_ping` 或 `urma_perftest` 验证连通性。
4. 检查 `ack_timeout` 配置是否合理。

### 日志出现 ELR_ERR

```text
[URMA][...][...]URMA_EVENT_ELR_ERR
```

排查步骤：

1. 检查 `urma_admin dev show` 中的设备状态。
2. 检查 `dmesg` 中是否有硬件错误、固件异常或热复位事件。
3. 确认设备散热、供电、PCIe 链路是否正常。
4. 必要时重启驱动或系统恢复。

## 拓扑查询

```bash
urma_admin topo show
```

用于查看当前节点与其他节点的连接关系。建链失败时，可通过拓扑信息确认：
- 对端设备是否在线
- 路由/交换路径是否正确
- 是否存在多个可达路径

## UPI 查询

```bash
urma_admin upi show
```

UPI（Unit Port Information）包含端口与业务实体的绑定信息。JFC/JFS/Jetty 问题排查时可用来确认：
- 资源是否已绑定到正确的端口
- 是否存在资源泄漏或重复绑定

## 注意事项

- `urma_admin` 需要 root 权限或特定设备访问权限。
- 部分命令在不同硬件后端（UDMA/UB 等）上输出字段可能略有差异。
- 管理工具输出应以日志时间点为参考，避免使用过旧的查询结果。
- 建议将 `urma_admin` 输出与日志时间点一起保存，便于问题回溯。
