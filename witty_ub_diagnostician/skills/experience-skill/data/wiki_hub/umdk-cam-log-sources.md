---
name: "UMDK CAM 日志来源与问题排查入口"
description: "介绍 CAM 算子运行时日志来源（PyTorch/ACL/HCCL/CANN），以及常见错误（shape mismatch、环境变量、A2/A3 代际约束）的排查入口。"
keywords:
  - UMDK
  - CAM
  - 算子
  - PyTorch
  - ACL
  - HCCL
  - CANN
  - 日志来源
  - A2
  - A3
references:
  - name: "UMDK v26.06.0_CAM 文档：CAM API Guide.ch.md"
    type: offline
    source: "umdk-v26.06.0_CAM/doc/ch/cam/CAM API Guide.ch.md"
  - name: "UMDK v26.06.0_CAM GitCode 仓库"
    type: online
    source: "https://gitcode.com/openeuler/umdk/tags/v26.06.0_CAM"
---

# UMDK CAM 日志来源与问题排查入口

## 概述

CAM 算子运行在 PyTorch/ACL/HCCL 框架之上，UMDK 侧主要提供 Python API。CAM 相关日志通常来自 CANN/HCCL 日志体系，而不是 UMDK 自身。排查 CAM 问题时需要结合上层框架日志和 UMDK 接口约束。

## 主要日志来源

| 来源 | 日志类型 | 说明 |
|------|----------|------|
| **PyTorch** | Python 报错、堆栈 | 算子调用入口错误、shape mismatch |
| **ACL** | CANN 应用层日志 | 算子执行错误、内存错误 |
| **HCCL** | 集合通信日志 | 通信域、环境变量、通信错误 |
| **CANN** | 底层运行时日志 | 设备驱动、算子执行、内存访问 |
| **UMDK CAM** | Python API 约束 | 参数校验、A2/A3 代际约束 |

## 日志落盘位置

- PyTorch 报错通常输出到标准错误（stderr）。
- CANN/HCCL 日志默认路径：`$HOME/ascend/log`。
- 可通过环境变量 `ASCEND_LOG_PATH` 指定日志目录。
- 日志文件通常包括 `plog/plog-*.log`、`host/*.log`、`device/*.log`。

## 常见错误类型与排查入口

### 1. Shape mismatch / 张量形状不匹配

**典型报错：**

```text
RuntimeError: shape mismatch
```

**排查入口：**
- 检查 CAM API Guide 中对应接口的输入输出形状约束。
- 检查 `expand_x`、`topk_idx`、`topk_weights` 等张量形状是否匹配。
- 检查是否满足 `global_bs` 和 `expert_num` 相关约束。

### 2. A2/A3 代际约束错误

CAM 接口明确区分 A2 和 A3 代际：
- A2 接口：只支持 A2 环境调用。
- A3 接口：只支持 A3 环境调用。

**典型报错：**

```text
NotImplementedError: A2 is not supported
NotImplementedError: A3 is not supported
```

**排查入口：**
- 确认当前运行环境的代际。
- 确认调用的 CAM 接口与代际匹配。
- 检查 API Guide 中接口“约束和注意事项”章节的代际说明。

### 3. HCCL 环境变量配置错误

A2 接口需要配置：

```bash
export HCCL_INTRA_PCIE_ENABLE=1
export HCCL_INTRA_ROCE_ENABLE=0
```

A3 部分接口需要配置：

```bash
export HCCL_BUFFSIZE=4096
```

**典型报错：**

```text
HCCL error: env HCCL_BUFFSIZE not set
```

**排查入口：**
- 检查 API Guide 中对应接口的环境变量要求。
- 检查进程环境变量是否传递到位。
- 检查 HCCL 版本是否支持相关环境变量。

### 4. 量化模式错误

**典型报错：**

```text
TypeError: quant_mode must be 0 or 2
```

**排查入口：**
- 检查 `quant_mode` 是否按接口要求传入（非量化 0，量化 2）。
- 检查量化张量数据类型是否为 `int8`。
- 检查 `scales`、`dynamic_scales` 等量化参数形状是否正确。

### 5. 内存不足

**典型报错：**

```text
RuntimeError: out of memory
```

**排查入口：**
- 检查 `global_bs` 是否超出实际内存约束。
- 检查 `HCCL_BUFFSIZE` 是否配置过大。
- 检查是否有其他进程占用显存/内存。

## 排查流程

1. 收集 PyTorch 报错和堆栈。
2. 收集 CANN/HCCL 日志（`$HOME/ascend/log`）。
3. 对照 CAM API Guide 检查接口参数和约束。
4. 确认环境变量和代际配置。
5. 检查内存/显存使用情况。

## 辅助命令

```bash
# 查看 CANN 日志目录
ls -l $HOME/ascend/log

# 查看进程环境变量
cat /proc/<pid>/environ | tr '\0' '\n' | grep HCCL

# 查看昇腾设备状态
npu-smi info
```

## 问题上报信息

- PyTorch 报错和完整堆栈
- CANN/HCCL 日志文件
- 调用的 CAM 接口名称和参数
- 环境变量 `HCCL_BUFFSIZE`、`HCCL_INTRA_PCIE_ENABLE`、`HCCL_INTRA_ROCE_ENABLE`
- 运行环境代际（A2/A3）
- 昇腾驱动和 CANN 版本

## 注意事项

- CAM 问题通常不是 UMDK 日志能直接定位的，需要优先查看 CANN/HCCL 日志。
- UMDK 侧主要提供 API 约束说明，如果参数和约束符合，问题通常在 CANN/HCCL 层。
- 环境变量应在进程启动前设置，并确保传递到子进程。
