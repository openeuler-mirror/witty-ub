---
name: connect-ubsocket-umq
description: 分析 UBSocket 对 UMQ 公共 API 的物理调用，依据返回值、errno、输出、状态码及同步或异步控制流，把最近的 UBSocket 日志故障节点或公共 API 根节点连接到 UMQ 公共 API 根节点。用于生成、更新或复核 data/failure_mode_tree.json 中 UBSocket 到 UMQ 的跨组件故障边，并处理无日志上提和明确特例。
---

# Connect UBSocket UMQ

## 核心语义

从 UBSocket 的 `Connect`、`Accept`、`ReadV`、`WriteV` 路径分析每个 UMQ 公共 API 物理调用点。边的源是最近的
UBSocket 具体错误日志；途中没有日志但失败返回公共 API 时，源可以是对应 UBSocket 根。目标只能是被调用的 UMQ 公共 API 根：

```text
UBSocket 日志节点或 API 根 -> UMQ 公共 API 根
```

调用关系本身不生成普通边。必须证明 UMQ 失败通过返回值、errno、输出、状态码或等价状态触发源日志或返回 UBSocket API。
返回结果被忽略、恢复、吞掉、覆盖或转换为成功时不连接。穿透无日志包装函数，只连接最近日志，禁止越过 UMQ 根直连其后代。

四个 UBSocket 根固定为：

- `ubsocket_001`：`SocketBase::Connect`
- `ubsocket_002`：`SocketBase::Accept`
- `ubsocket_003`：`SocketBase::ReadV`
- `ubsocket_004`：`SocketBase::WriteV`

## 输入与输出

输入：

- UBSocket 与 UMQ 源码路径；
- `data/ubsocket/ubsocket_failure_mode.json`；
- `data/umq/umq_failure_mode.json`；
- `data/failure_mode_tree.json`。

输出：

- `/tmp/ubsocket_umq_calls.json`：物理调用点；
- `/tmp/ubsocket_umq_edge_analysis.json`：逐调用点分析记录；
- `failure_mode_tree.json.ubsocket`：只向已有源节点的 value 末尾追加确认的 `umq_xxx`。

不得修改节点定义、`failure_mode_tree.json.umq` 或其他顶层对象。UMQ 编号只作为 `ubsocket` value 中的下游引用，
不得新增为 `ubsocket` 的 key。

禁止参考旧连接结果、git 历史提交和 `/tmp` 旧产物。必须从当前源码重新生成下列分析文件。
UBSocket 和 UMQ 节点生成 skill 是输入产物的上游定义者；本连接 skill 已包含所需接口规则，默认无需完整加载它们。

## 流程

### 1. 重新生成候选产物

```bash
python3 .opencode/skills/connect-ubsocket-umq/scripts/find_ubsocket_umq_calls.py \
  <ubsocket源码路径> <umq源码路径>
python3 .opencode/skills/failure-mode-generation-ubsocket/scripts/find_ubsocket_log_err.py \
  <ubsocket的csrc路径>
python3 .opencode/skills/failure-mode-generation-ubsocket/scripts/generate_ubsocket_callchains.py \
  <ubsocket源码路径>
python3 .opencode/skills/failure-mode-generation-umq/scripts/generate_umq_callchains.py \
  <umq源码路径>
```

检查四个产物的源码根与输入一致：`ubsocket_umq_calls.json`、`ubsocket_log_err.json`、
`ubsocket_api_callchains.json`、`umq_api_callchains.json`。调用链必须报告分析完成；相关未解析调用必须结合源码复核。

逐项验证 `calls[]` 的 `file/line/column/parent/parent_qualified/child/style`。不得按 `(parent, child)` 去重；
同一函数不同位置或分支的调用分别分析。检查宏别名、函数指针、模板、动态加载表等脚本可能未覆盖的间接 UMQ 调用，
发现遗漏时补入人工分析记录并计数。

计算四个产物的 SHA-256 写入分析记录。写树前确认哈希未变化；变化时重新生成并重做受影响分析，无需重复运行全部命令两次。

### 2. 校验节点映射

按 `/tmp/umq_api_callchains.json.roots` 顺序从 `umq_001` 建立根映射。每个目标必须：

- 同时存在于 UMQ 节点定义和 `failure_mode_tree.json.umq`；
- 节点定义中的裸 `函数名` 与 root 完全一致；
- 与调用点的 `child` 一致；
- 是 UMQ 公共 API 根，而不是同名具体日志节点。

用裸函数名及 `故障现象` 的全部日志关键字，把 `/tmp/ubsocket_log_err.json` 的物理日志唯一映射到 UBSocket 具体节点。
同全文日志的多个物理点可以映射到聚合节点；不得只凭函数名选择。零匹配或无法消歧时标记证据不足。

### 3. 确定调用上下文与 API 归属

用调用点 `parent_qualified` 与 `/tmp/ubsocket_api_callchains.json.call_chains[].functions[].qualified_name` 完整匹配同步候选，
并以文件、函数签名、命名空间和类作用域消歧；禁止只匹配裸名或后缀。调用链只用于定位候选，不是故障边证据。

同步匹配为零时，不得立即判为链外。继续检查模板实例、callback、虚函数、函数指针、线程入口、事件 runner 和异步数据归属。
同一物理调用点被多个上下文复用时，分别分析各上下文的 API 归属、实参、结果处理和日志条件，一个调用点可以产生多个源不同的边。
现有故障树只用于发现归属冲突，不能反向证明源码归属。

若涉及异步对象、线程、runner、callback、模板展开或 `silent_poll_err` 等日志控制变量，完整读取
[异步与上下文规则](references/async-and-context.md) 后再判定；简单同步路径不要加载该参考。

### 4. 判定故障传播

| 结论 | 条件 | 源节点 |
| --- | --- | --- |
| 直接捕获 | UMQ 失败直接触发调用函数内错误日志 | 对应具体日志节点 |
| 无日志上提 | 失败经无日志函数传播后触发最近上游日志 | 最近具体日志节点 |
| API 根上提 | 失败返回所属 UBSocket API，途中没有错误日志 | 对应 `ubsocket_001`～`004` |
| 无边 | 失败被忽略、恢复、吞掉、覆盖、转成功，或与日志无依赖 | 无 |
| 链外调用 | 同步、异步及间接上下文均已解析且不属于四个 API | 无 |
| 证据不足 | 调用、归属、传播或日志映射无法确定 | 无，不得猜测 |
| 特例 | 命中下表的精确函数、调用点和归属条件 | 按特例指定 |

若同一 UMQ 失败先触发较近日志、再触发上层日志，只连接最近日志到 UMQ 根；上层传播使用已有 UBSocket 内部边。
一个函数有多个错误日志时，只连接由该物理调用失败实际触发的日志，禁止按函数名连接所有日志。

以下特例覆盖普通传播规则，但仍须证明物理调用点和 API 归属：

| 特例 | 规则 |
| --- | --- |
| `UmqApi::umq_ack_interrupt` | 即使返回 `void` 且调用方没有产生日志，也在已证明可达该调用点的 `ReadV`、`WriteV` 根（`ubsocket_003/004`）value 中追加对应 UMQ 根。 |
| `UmqPollAndRefillRx` 中的 `UmqApi::umq_buf_alloc` | `nullptr` 通过 `rx_queue_avail_num_` 等状态影响后续补充接收缓冲区；沿当前源码状态读写唯一确定最近错误日志并连接。当前路径若不能唯一证明到 `PollRx/GetQbuf` 等具体日志，标记证据不足；不得使用“推荐节点”或硬编码编号。 |

其他位置的 `umq_buf_alloc` 按普通规则处理。特例分析必须记录命中的函数、调用点、上下文和状态影响证据。

### 5. 记录并写入

生成 `/tmp/ubsocket_umq_edge_analysis.json`：

```json
{
  "call_count": 0,
  "supplemental_call_count": 0,
  "analyzed_count": 0,
  "artifact_sha256": {},
  "confirmed_edges": [],
  "entries": []
}
```

`entries` 按 `file/line/column` 排序，覆盖脚本调用点及人工补充调用点。每条记录物理位置、调用者、UMQ API、目标根、
所有同步/异步上下文、包装展开、传播变量或状态、日志控制条件、结论、源节点或无边原因及源码证据；特例注明命中条目。
必须满足 `analyzed_count == call_count + supplemental_call_count == entries.length`，`confirmed_edges` 为可生成边的
`{source, target}` 去重汇总。

先基于原树生成 `/tmp/failure_mode_tree.connected.json` 并校验，再把相同追加应用到正式文件：

- 保留所有 key、原有边和数组相对顺序，只在对应 `ubsocket` value 末尾追加并去重；
- source 必须存在于 `failure_mode_tree.json.ubsocket`，target 必须是有效 UMQ 根；
- 新增边必须与 `confirmed_edges` 完全一致，无重复、自引用或越过最近日志；
- 四个分析产物哈希必须与记录一致；
- 结构化差异只能是已有 `ubsocket` value 新增确认的 UMQ 根编号。

任何校验失败时不得修改正式文件。
