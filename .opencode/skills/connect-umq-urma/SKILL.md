---
name: connect-umq-urma
description: 分析 UMQ 对 URMA 公共 API 的直接或动态函数表调用，采用 API 边界故障注入语义，把能在 UMQ 侧传播到具体错误日志的返回值、errno、输出或异步失败状态连接到 urma_NNN 公共 API 根节点，并处理 urma_ack_jfc 的明确 void 特例。用于生成、更新或复核 data/failure_mode_tree.json 中 UMQ 到 URMA 的跨组件故障边。
---

# Connect UMQ URMA

## 核心语义

普通边的源是 UMQ 具体日志故障节点，目标是 `urma_NNN` 公共 API 根节点：

```text
URMA API 边界注入失败 -> UMQ 观察并传播失败 -> 最近的 UMQ 具体错误日志
```

只要 UMQ 检查并传播 URMA API 的返回值、errno、输出或异步状态，就认为该 API 边界可以故障，并生成跨组件边。
不得因为当前 URMA 实现恒成功、当前实参排除了已有失败分支、根节点没有具体子节点，或 URMA 内部故障分支不可达而拒绝边。
这条边界注入规则优先于 UMQ、URMA 节点生成 skill 中关于组件内部实际失败路径的规则，但不改变两侧组件内部故障边。

调用关系本身不生成边。以下情况不连接：

- 返回结果或状态被忽略、覆盖、恢复或转换为成功；
- `void` API 没有被 UMQ 观察的 errno、输出或异步失败状态，且未命中下述明确特例；
- 失败只返回到 UMQ 公共 API，途中没有可映射的具体错误日志；
- 已证明调用不属于任何 UMQ 公共 API 的同步或异步路径。

同一失败先触发较近日志、再触发更上层日志时，只由最近的 UMQ 日志节点连接 URMA 根；上层传播由已有 UMQ 内部边表示。

回归示例：`urma_register_log_func`、`urma_register_loc_log_func`、`urma_unregister_log_func` 的返回值经无日志包装函数触发
`umq_framework_init` 的 `"log config set failed"` 时，该日志节点必须连接三个 URMA 根，即使当前实现不会失败。
`urma_log_set_level` 的结果被忽略且没有其他可观察失败状态时不连接。

### 明确特例

以下特例显式覆盖“源必须是 UMQ 具体日志节点”和“未观察 `void` API 状态则不连接”的普通规则，但仍须证明物理调用点、
UMQ 公共 API 归属及目标 URMA 根映射：

| 特例 | 规则 |
| --- | --- |
| `urma_ack_jfc` | 仅限 `umq_ub/core/private/umq_ub.c` 中 `umq_ub_wait_rx_interrupt`、`umq_ub_wait_tx_interrupt`、`umq_ub_wait_tp_handle_tx_interrupt` 的三个物理调用点。即使该 API 返回 `void` 且 UMQ 调用方没有产生日志，也把已证明可达这些调用点的 `umq_wait_interrupt`、`umq_get_cq_event` 根节点连接到 `urma_ack_jfc` 的根节点。该特例表示 URMA API 内部能够记录自身参数或 ops 缺失故障，而不是声称 UMQ 观察了返回状态。 |

其他 `void` URMA API 和其他位置的 `urma_ack_jfc` 仍按普通规则处理。特例不得扩展到仅共享 JFC/JFCE、设备或线程但未证明
可达物理调用点的 UMQ API。

## 输入与输出

输入：

- UMQ 源码路径；
- URMA `lib/urma` 源码路径；
- `data/umq/umq_failure_mode.json`；
- `data/urma/urma_failure_mode.json`；
- `data/failure_mode_tree.json`。

输出：

- `/tmp/umq_urma_calls.json`：物理调用点；
- `/tmp/umq_urma_edge_analysis.json`：逐调用点分析记录；
- `failure_mode_tree.json.umq`：只在已有 UMQ 具体节点的 value 末尾追加确认的 `urma_NNN`。

不得修改节点定义文件、`failure_mode_tree.json.urma` 或其他顶层对象。`urma_NNN` 只作为 value 中的下游引用，
不得新增为 `umq` 的 key。

禁止参考旧连接结果、git 历史提交和 `/tmp` 中的旧产物。必须从当前源码重新生成下列分析文件。
UMQ 和 URMA 节点生成 skill 是这些输入的上游定义者；执行本连接 skill 时无需完整加载它们，以下流程已包含所需连接规则。

## 流程

### 1. 重新生成候选产物

运行：

```bash
python3 .opencode/skills/connect-umq-urma/scripts/find_umq_urma_calls.py \
  <UMQ源码路径> <URMA的lib/urma源码路径>
python3 .opencode/skills/failure-mode-generation-umq/scripts/find_umq_log_err.py <UMQ源码路径>
python3 .opencode/skills/failure-mode-generation-umq/scripts/generate_umq_callchains.py <UMQ源码路径>
python3 .opencode/skills/failure-mode-generation-urma/scripts/generate_urma_callchains.py \
  <URMA的lib/urma源码路径>
```

检查：

- 四个输出的源码路径与本次输入一致：`umq_urma_calls.json`、`umq_log_err.json`、`umq_api_callchains.json`、`urma_api_callchains.json`；
- 两个调用链的 `analysis.complete=true`、`missing_roots=[]`；逐项复核相关 `unresolved_indirect_calls`；
- `calls[]` 的 `file/line/column/parent/child/style` 能定位真实调用，`target_root_id` 存在；
- `called_without_loaded_symbol`、`loaded_public_but_uncalled`、`excluded_non_root_calls` 等异常均有解释；
- 不按 `(parent, child)` 去重物理调用点，同一函数中的重复调用和不同分支分别分析。

计算四个文件的 SHA-256 写入分析记录。正式写树前只需确认哈希未变化；变化时重新生成并重做受影响分析，无需机械地重复运行全部命令两次。

### 2. 校验节点映射

按 `/tmp/urma_api_callchains.json.roots` 顺序从 `urma_001` 建立 URMA 根映射。每个目标必须：

- 同时存在于 URMA 节点定义和 `failure_mode_tree.json.urma`；
- 节点定义中的裸 `函数名` 与 root 完全一致；
- 与 `calls[].target_root_id` 一致；
- 是公共 API 根，而不是同名具体日志节点；根的 value 允许为空。

普通跨组件源必须是同时存在于 UMQ 节点定义和 `failure_mode_tree.json.umq` 的具体节点，不能是 UMQ API 根。
命中特例时，源必须精确为已证明可达调用点的公共 API 根，不得选择其他根或虚构具体日志节点。
用裸函数名及 `故障现象` 的全部日志关键字唯一映射 `/tmp/umq_log_err.json` 物理日志；零匹配或无法消歧时标记证据不足。

### 3. 确定调用上下文与最近日志

从每个 `calls[]` 调用点出发，用 UMQ 调用链定位同步公共 API 归属，并用文件、函数起始行和函数体消歧同名函数。
调用链只提供候选；结合函数指针绑定、动态函数表、宏和 inline 包装补齐路径。

从 URMA 调用结果沿 UMQ 控制流向上追踪返回值、errno、输出或等价状态。穿透无日志包装函数，直到失败被处理或到达最近具体错误日志。
同一物理调用点被多个上下文复用时，分别分析每个上下文，可以从一个 `calls[]` 产生多个源节点不同的确认边。
现有故障树只能帮助发现冲突，不能反向证明源码归属。

若路径涉及 callback、线程、队列、WR/CR、JFC/JFCE、notifier 或 async event，完整读取
[异步传播规则](references/async-propagation.md) 后再判定；纯同步路径不要加载该参考。

### 4. 逐调用点判定

| 结论 | 条件 | 处理 |
| --- | --- | --- |
| 直接捕获 | 边界注入失败直接触发调用函数内的 UMQ 日志 | 该日志节点连接 URMA 根 |
| 无日志上提 | 失败经无日志函数传播后触发最近上游 UMQ 日志 | 最近日志节点连接 URMA 根 |
| 无边 | 所有失败通道均被忽略、覆盖、恢复、转成功，或没有具体日志捕获 | 不写边并记录原因 |
| 链外调用 | 已证明不属于任何 UMQ 公共 API 路径 | 不写边并记录归属证据 |
| 证据不足 | 调用、归属、传播或日志映射无法确定 | 不猜测、不写边 |
| 特例 | 命中上述特例函数、调用点和归属条件 | 对每个已证明可达的指定 UMQ API 根连接 |

同步返回型 API 只分析 UMQ 如何处理注入的非成功结果，不检查当前 URMA 实现能否产生该结果。
异步 API 仍必须证明注入状态经过对象生产、关联和消费到达日志。
每个调用点必须分别枚举返回值、errno 及每个输出参数的全部检查分支；一个通道不成边不能代表整个调用点无边，只要任一通道传播到具体日志就生成边。只有全部通道逐项排除后才能判定“无边”。
`urma_ack_jfc` 特例不要求普通返回传播或 UMQ 日志，但必须读取 URMA 实现，确认其内部错误日志仍存在，并完整证明
`UMQ API -> JFCE wait -> temp_jfc/nevents -> 特例物理调用点` 的对象关联。任一证据缺失时标记证据不足，不得套用特例。

### 5. 记录并写入

生成 `/tmp/umq_urma_edge_analysis.json`，至少包含：

```json
{
  "call_count": 0,
  "analyzed_count": 0,
  "artifact_sha256": {},
  "root_coverage": {},
  "confirmed_edges": [],
  "excluded_non_root_calls": [],
  "entries": []
}
```

`entries` 与 `calls[]` 一一对应并按位置排序。每条记录调用位置、目标根、所有同步/异步上下文、包装路径、边界注入通道、
传播变量或状态、最近日志、结论及源码证据。若一个调用点有多个上下文，在同一 entry 中分别记录。
特例 entry 必须记录命中的特例条目、URMA 内部日志位置、三个允许的物理调用点之一、JFCE/JFC 对象关联以及每个源根的完整可达路径；
其 `nearest_logs` 可为空，但不能伪造 UMQ 日志。
`confirmed_edges` 汇总去重后的 `{source, target}`；`root_coverage` 覆盖每个 URMA root，记录调用点、确认边、无边和证据不足数量，
未调用根记录 `not_called` 及复核依据。必须满足 `call_count == analyzed_count == entries.length`。

先基于原树生成 `/tmp/failure_mode_tree.connected.json` 并校验，再把相同追加应用到正式文件：

- 保留所有 key、原有边和数组相对顺序，只在对应 UMQ value 末尾追加并去重；
- 不新增、删除或重排 `umq` key，不修改其他对象和节点定义；
- 每条新增边与 `confirmed_edges` 完全一致；普通 source 是 UMQ 具体日志节点，特例 source 是已证明可达的 UMQ 公共 API 根；target 必须是对应 URMA 根，且无重复或自引用；
- 写入前四个分析产物哈希仍与记录一致；
- 结构化差异只能是已有 `umq` value 新增确认的 URMA 根编号。

任何校验失败时不得修改正式文件。
