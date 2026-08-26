---
name: umdk-cam-error-log-analysis
description: >
  根据 CAM 算子报错（shape mismatch、环境变量缺失、A2/A3 代际不兼容、量化模式错误）反查接口约束，并指导如何收集 CANN/HCCL 日志。
  本 Skill 用于帮助定位 CAM 算子调用失败问题。
license: MIT
compatibility: UMDK v26.06.0_CAM
metadata:
  author: umdk-log-analysis
  version: "1.0"
  keywords: [UMDK, CAM, 算子, PyTorch, ACL, HCCL, CANN, shape mismatch, A2, A3, 量化]
allowed-tools: Bash(grep:*) Bash(awk:*) Bash(cat:*) Bash(ls:*)
---

# CAM 错误日志分析 Skill

## 概述

CAM 算子错误通常表现为 PyTorch 报错、CANN/HCCL 日志错误或昇腾设备异常。本 Skill 提供从报错到接口约束的排查流程。

## 约束

- CAM 主要依赖 CANN/HCCL 运行时，UMDK 侧仅提供 Python API 约束。
- 排查必须结合 CAM API Guide 中的参数约束和注意事项。
- 环境变量问题常被忽略，应优先确认。

## 流程

1. 收集 PyTorch 报错和堆栈。
2. 识别错误类型：shape mismatch、代际错误、环境变量、量化、内存等。
3. 对照 CAM API Guide 检查对应接口的约束。
4. 检查环境变量配置。
5. 收集 CANN/HCCL 日志进一步分析。
6. 确认昇腾设备状态和驱动版本。

## 能力

- 输出 CAM 常见错误类型和排查方向。
- 输出 A2/A3 代际约束检查清单。
- 输出 HCCL 环境变量配置要求。
- 输出 CANN/HCCL 日志收集方法。

## 规则

- 出现 `shape mismatch` 时，优先按 API Guide 核对每个张量形状。
- 出现 `not supported in A2/A3` 类错误时，优先确认代际和接口版本匹配。
- 出现 HCCL 相关错误时，优先检查环境变量 `HCCL_BUFFSIZE`、`HCCL_INTRA_PCIE_ENABLE`、`HCCL_INTRA_ROCE_ENABLE`。
- 出现量化错误时，优先检查 `quant_mode` 和数据类型。
- 出现内存错误时，优先检查 `global_bs` 和设备内存使用情况。

## 错误分类排查

```text
shape mismatch
  └── 对照 API Guide 检查输入输出张量形状

A2/A3 不支持
  └── 确认运行环境代际和接口版本匹配

HCCL 环境变量错误
  └── 检查 HCCL_BUFFSIZE、HCCL_INTRA_PCIE_ENABLE、HCCL_INTRA_ROCE_ENABLE

量化错误
  └── 检查 quant_mode、数据类型、scales 形状

内存不足
  └── 检查 global_bs、设备内存、HCCL_BUFFSIZE
```

## 常见环境变量

| 环境变量 | 适用场景 | 典型值 |
|----------|----------|--------|
| `HCCL_BUFFSIZE` | A2/A3 部分接口 | 4096 或按公式计算 |
| `HCCL_INTRA_PCIE_ENABLE` | A2 接口 | 1 |
| `HCCL_INTRA_ROCE_ENABLE` | A2 接口 | 0 |
| `ASCEND_LOG_PATH` | 日志目录 | `$HOME/ascend/log` |

## 与 CANN/HCCL 日志结合

UMDK 侧通常无法直接输出 CAM 算子内部错误，需要查看：
- `plog/plog-*.log`
- `host/*.log`
- `device/*.log`

关键搜索词：
- `CAM`
- `shape`
- `HCCL`
- `ACL`
- `memory`
- `invalid parameter`

## 辅助命令

```bash
# 查看 CAM 相关报错
grep -i "cam\|shape\|hccl\|acl" $HOME/ascend/log/plog/*.log

# 查看环境变量
env | grep HCCL

# 查看昇腾设备状态
npu-smi info
```

## 问题上报模板

- PyTorch 报错和堆栈
- 调用的 CAM 接口及参数
- 环境变量 `env | grep -E "HCCL|ASCEND"`
- 运行环境代际（A2/A3）
- CANN/HCCL 版本
- 昇腾驱动版本
- 相关日志文件路径

## 注意事项

- 如果接口参数和约束都符合，问题可能在 CANN/HCCL 层，需要升级或联系相关团队。
- 环境变量未设置时，可能报参数缺失或通信错误，不一定是代码问题。
- 多机场景下，HCCL 环境变量应在所有节点一致配置。
