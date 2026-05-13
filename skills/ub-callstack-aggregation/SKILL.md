---
name: "ub-callstack-aggregation"
description: "聚合 ubsocket/umq/liburma/libudma 的函数调用图，并补充跨组件调用边。"
---

# ub-callstack-aggregation

## 目标

将指定组件集合各自的 `callstack.json` 聚合为一张统一调用图，并补充跨组件调用边：

- `ubsocket`
- `umq`
- `liburma`
- `libudma`

跨组件边的识别方法：

1. 以各组件 `callstack.json` 的 `nodes` 作为候选函数集合
2. 逐节点按函数名回溯到源码函数体
3. 在函数体中提取调用表达式
4. 将调用名匹配到“其他组件”的函数节点，形成 `src -> dst`

## 输入

组件集合输入（至少 1 个组件，支持任意子集）：

- 每个被聚合组件都必须成对提供：
  - `--<component>-src`
  - `--<component>-callstack`
- `<component>` 必须是以下之一：
  - `ubsocket`
  - `umq`
  - `liburma`
  - `libudma`

约束规则：

1. 不需要聚合的组件可以不传
2. 对于需要聚合的组件，`src` 与 `callstack` 缺一不可
3. 至少传入 1 个组件；若传入多个组件，则允许生成跨组件调用边

## 输出

输出目录：`/var/witty-ub/callstack-analysis`

输出文件：

- `overall_callstack.json`：聚合后的统一调用图

### overall_callstack.json 结构

```json
{
  "nodes": [
    {
      "name": "umq_send",
      "component": "umq"
    }
  ],
  "edges": [
    {
      "src": "rpc_entry",
      "dst": "urma_cmd_xxx"
    }
  ]
}
```

字段规则：

- `nodes`：函数节点列表，只允许包含 `name` 和 `component`
- `edges`：调用边列表，只允许包含 `src` 和 `dst`
- `nodes[].name`：裸函数名
- `nodes[].component`：函数所属组件
- `edges[].src/dst`：裸函数名，必须引用已存在的 `nodes[].name`
- 不得输出 `id`、`file`、`confidence`、`kind`、`evidence`、行号等额外字段
- 若存在同名函数，按函数名简单合并为一个节点；边也按函数名聚合

## 实现脚本

脚本位置：`skill/ub-callstack-aggregation/scripts/aggregate_callstack.py`

### 运行示例

```bash
python3 skill/ub-callstack-aggregation/scripts/aggregate_callstack.py \
  --liburma-src /path/to/liburma \
  --liburma-callstack /var/witty-ub/callstack-analysis/liburma/callstack.json \
  --libudma-src /path/to/libudma \
  --libudma-callstack /var/witty-ub/callstack-analysis/libudma/callstack.json
```

## 匹配规则

### 函数体定位

- 按 `nodes[].name` 在组件源码路径中定位函数定义并提取函数体（支持 `Class::Func` 与短名 `Func`）
- 若函数名命中多个定义且无法唯一判定，保留全部候选用于后续跨组件匹配，但最终输出仍按函数名合并节点和边
- 若无法提取函数体，跳过该节点，不阻塞整体输出
- 注意：若传入的“源码路径”目录里只有 `callstack.json` 而没有真实源码文件，跨组件连边会为空

### 调用提取

- 识别 `foo(...)`、`ns::foo(...)`、`obj->foo(...)`、`obj.foo(...)` 样式
- 过滤注释与字符串中的伪命中
- 过滤关键字与控制语句（如 `if/for/while/switch/return/sizeof`）
- 宏调用不建边

### 跨组件匹配

- 仅在“调用者组件 != 被调组件”时建立跨组件边
- 优先使用完整名匹配（如 `Class::Func`），其次使用短名匹配（如 `Func`）
- 唯一匹配或多候选匹配都只输出函数名边
- 多候选匹配时，按函数名聚合重复边

## 失败与回退策略

- 已传入组件的 callstack 解析失败：终止并报错（输入不完整时无法可靠聚合）
- 参数中出现 `src/callstack` 不成对：终止并报错
- 单个函数体解析失败：记录到统计信息并跳过
- 同名多定义无法判定：按函数名简单合并节点和边

## 质量自检清单

- 已传入组件节点是否全部进入聚合图
- `nodes` 是否只包含 `name` 和 `component`
- `nodes[].name` 是否已按函数名去重合并
- `edges` 是否只包含 `src` 和 `dst`
- `edges[].src/dst` 是否全部可回溯到 `nodes[].name`
- 是否没有输出 `id`、`file`、`confidence`、`kind`、`evidence`、行号等额外字段
- 是否输出了 `stats.json` 便于快速评估质量
