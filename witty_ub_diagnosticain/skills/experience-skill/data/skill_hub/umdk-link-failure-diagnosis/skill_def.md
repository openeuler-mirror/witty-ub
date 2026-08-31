---
name: umdk-link-failure-diagnosis
description: >
  基于 URMA 日志中的 PORT_DOWN、ELR_ERR、ACK_TIMEOUT、链路速率/宽度异常等模式，诊断链路、端口和传输层故障。
  本 Skill 结合 urma_admin 输出，提供从日志到根因的排查流程。
license: MIT
compatibility: UMDK v26.06.0_CAM
metadata:
  author: umdk-log-analysis
  version: "1.0"
  keywords: [UMDK, URMA, 链路故障, PORT_DOWN, ELR_ERR, ACK_TIMEOUT, 端口, 诊断]
allowed-tools: Bash(grep:*) Bash(awk:*) Bash(dmesg:*) Bash(cat:*)
---

# URMA 链路故障诊断 Skill

## 概述

链路故障是 URMA 常见问题之一，表现为端口状态变化、重传超时、建链失败等。本 Skill 通过日志模式和管理工具输出定位链路/端口/传输层问题。

## 约束

- 以 URMA 日志和 `urma_admin` 输出为主要输入。
- 部分链路问题需要结合硬件、固件、物理连接信息。
- 多路径/多端口场景需区分具体端口。

## 流程

1. 从日志中提取链路相关事件（`PORT_DOWN`、`ELR_ERR`、`ACK_TIMEOUT` 等）。
2. 使用 `urma_admin port show` 确认端口状态、链路宽度、速率。
3. 检查 `dmesg` 中的驱动/固件事件。
4. 根据事件类型进入对应排查分支。
5. 复现问题并验证修复。

## 能力

- 输出常见链路故障日志模式及含义。
- 输出 `urma_admin` 相关查询命令和关键字段解读。
- 输出链路故障排查分支树。
- 输出需要收集的辅助信息清单。

## 规则

- 出现 `PORT_DOWN` 时，优先检查物理连接和对端状态。
- 出现 `ACK_TIMEOUT` 时，优先检查网络可达性、链路质量、`ack_timeout` 配置。
- 出现 `ELR_ERR` 时，优先检查硬件/固件状态和 `dmesg`。
- 多端口环境下，必须结合端口号和日志时间戳定位具体端口。

## 常见日志模式

| 模式 | 含义 | 排查方向 |
|------|------|----------|
| `URMA_EVENT_PORT_DOWN` | 端口变为 DOWN | 物理连接、对端、固件 |
| `URMA_EVENT_ELR_ERR` | 实体级错误 | 硬件/固件异常、PCIe、散热 |
| `URMA_CR_ACK_TIMEOUT_ERR` | 重传超时 | 网络质量、ack_timeout、对端 |
| `link width dropped` | 链路宽度降级 | 线缆/模块、对端协商、硬件 |
| `speed dropped` | 链路速率降级 | 线缆/模块、端口配置、固件 |

## 排查分支

```text
PORT_DOWN
  ├── 物理连接是否松动？
  │     └── 是 → 重新插拔或更换线缆/光模块
  ├── 对端是否 DOWN？
  │     └── 是 → 检查对端设备
  ├── 驱动/固件是否报错？
  │     └── 是 → 查看 dmesg，必要时重启/升级驱动
  └── 其他 → 收集端口日志和固件日志上报

ACK_TIMEOUT
  ├── 网络是否可达？
  │     └── 否 → 检查路由/防火墙/对端
  ├── 链路质量是否差？
  │     └── 是 → 更换链路、调整网络
  ├── ack_timeout 是否过短？
  │     └── 是 → 调整 ack_timeout
  └── 对端是否繁忙？
        └── 是 → 检查对端资源

ELR_ERR
  ├── dmesg 是否有硬件错误？
  │     └── 是 → 检查散热/供电/PCIe
  ├── 固件版本是否已知有问题？
  │     └── 是 → 升级固件
  └── 其他 → 设备复位或重启
```

## 辅助命令

```bash
# 端口状态
urma_admin port show

# 内核日志
dmesg -T

# 链路统计（如系统支持）
ethtool -S <netdev>

# 设备信息
urma_admin dev show
```

## 问题上报模板

- 日志中 `PORT_DOWN` / `ELR_ERR` / `ACK_TIMEOUT` 的完整时间线
- `urma_admin port show` 输出
- `dmesg` 对应时间段输出
- 线缆/光模块型号
- 固件版本
- 复现步骤
