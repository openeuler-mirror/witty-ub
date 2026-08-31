---
name: connect-kvcache-urma
description: 分析 yuanrong-datasystem KVCache 通过 ds_urma_* shim 对 URMA 源码接口的物理调用，基于全量调用图把 urma_NNN 接口节点接到实际调用它的 KVCache 日志节点，或上提到沿 caller 链最近产生日志的地方；失败仅在 access 边界可观测时终选 access 入口根。用于生成、更新或复核 data/failure_mode_tree.json 中 KVCache 到 URMA 的跨组件故障边。
---

# Connect KVCache URMA

## 核心语义

DataSystem 通过 `common/rdma/urma_dlopen_util.h` 中的 `ds_urma_*` shim 调用 URMA。物理调用写作
`ds_urma_xxx(...)`。这里必须严格区分函数名和故障节点编号：

- `ds_urma_xxx`：KVCache 源码中的 shim 函数名；
- `urma_xxx`：`urma_api.h` 中以语义名称结尾的源码接口函数名；
- `urma_NNN`：匹配 `^urma_[0-9]{3}$` 的故障接口节点编号，也是唯一允许作为跨组件边 target 的编号。

```text
URMA API 边界注入失败 -> KVCache 观察并传播失败 ->
调用点所在函数的日志节点（直接观测）；否则沿全量调用图最近的
upstream 日志节点（上提）；否则 access 入口根（终选）
```

普通边的源优先级遵循**就近原则，不得越级**：

1. **调用点直接观测**：调用 `ds_urma_*` 的函数本身记录该失败（错误日志，含 `RETURN_STATUS` 系构造状态并记录的点）；
2. **最近日志上提**：调用函数未记录，沿全量调用图 caller 链最近的、报告或传播该失败的上游函数日志节点；
3. **access 入口根上提**（终选）：整条 caller 链没有日志，但失败以确定的 `K_*` 到达 access 边界（公共 API 返回或 RPC 响应状态码），按错误码匹配 access 入口根。

target 只能是实际调用对应的 `urma_NNN` 接口节点，也不能越过接口节点连接 URMA 内部节点。最上游的观察点连接
`urma_NNN` 后，更上层日志通过 KVCache 内部（runtime→runtime）边向下汇聚，不再重复连接接口节点。

调用关系本身不生成边。必须证明 URMA 边界的失败返回、空指针、负值、输出参数、errno 或异步完成状态触发所选源节点的
日志或 access 边界状态码。返回或状态被忽略、恢复、覆盖、转为成功时不连接。

对同步返回型 API 使用边界故障注入语义：分析 KVCache 如何处理可能的失败值，不以当前 URMA 实现是否能产生该值作为拒绝边的
理由。`void` API 只有在 KVCache 观察 errno、输出或关联的异步失败状态时才按普通规则连接。不得把
`connect-umq-urma` 中限定于 UMQ 三个物理调用点的 `urma_ack_jfc` 特例迁移到 KVCache。

## 输入与输出

输入：

- yuanrong-datasystem 仓库根（kvcache 侧脚本统一下探到 `src/datasystem`）；
- URMA `lib/urma` 源码路径（仅用于解析 `urma_api.h` 公共接口声明，不分析 URMA 内部调用链）；
- `data/kvcache/kvcache_failure_mode.json`；
- `data/urma/urma_failure_mode.json`，只使用其中 `故障编号` 为 `urma_NNN` 的接口根节点；
- `data/failure_mode_tree.json`。

输出：

- `/tmp/kvcache_urma_calls.json`：`ds_urma_*` 物理调用点、`urma_xxx` 函数名及 `urma_NNN` 节点映射；
- `/tmp/kvcache_urma_edge_analysis.json`：逐调用点传播分析；
- `failure_mode_tree.json.kvcache`：只向已有 KVCache 源节点的 value 末尾追加确认的 `urma_NNN`。

不得修改节点定义、`failure_mode_tree.json.urma` 或其他顶层对象。只有存在于 URMA 节点定义和树中的
`urma_NNN` 编号可作为 `kvcache` value 中的下游引用，不得新增为 `kvcache` 的 key。

禁止参考旧连接结果、git 历史提交和 `/tmp` 旧产物。必须从当前源码重新生成下列候选产物；节点生成 skill 是上游定义者，
执行本连接 skill 时默认无需完整加载其说明。

## 流程

### 1. 重新生成候选产物

```bash
python3 .opencode/skills/connect-kvcache-urma/scripts/find_kvcache_urma_calls.py \
  <yuanrong-datasystem-repo-root> <URMA的lib/urma源码或仓库路径>
python3 .opencode/skills/failure-mode-generation-kvcache/scripts/find_kvcache_runtime_err.py \
  <yuanrong-datasystem-repo-root>
python3 .opencode/skills/failure-mode-generation-kvcache/scripts/generate_kvcache_callchains.py \
  <yuanrong-datasystem-repo-root>
```

本 skill **不运行 URMA 调用链脚本**：跨组件边只到 `urma_NNN` 接口根，从不遍历 URMA 内部；接口映射以
`urma_api.h` 声明（`find_kvcache_urma_calls.py` 自行解析）和 `urma_failure_mode.json` 接口根定义为准。

检查：

- `kvcache_urma_calls.json` 的 `kvcache_path`、`urma_path` 和 `shim_header` 与输入源码一致；
- `kvcache_callchains.json.source_root` 是本次 DataSystem 仓库、`schema_version=2`、`analysis.complete=true`，
  全部 translation unit 成功，`functions`/`entry_count`/`edges` 与 `src/datasystem` 规模相称，抽查若干
  `entry=true` 函数确为 RPC handler、后台线程入口或公共 API 实现；
- `kvcache_runtime_err.json` 是本次源码重跑结果（`source_root` 为 `<repo>/src/datasystem`），所有 entry 均为
  `candidate_kind=emitted_log`，并用相对文件和行号抽样定位当前源码；该清单就是"产生日志的地方"的权威全集，
  最近日志上提的搜索空间以它为准；
- 顶层 `target_component` 必须为 `urma`；`calls[]` 的
  `file/line/column/parent/parent_qualified/shim/child/style/target_component/target_root_id` 均能定位真实调用；
- `excluded_non_root_calls` 逐项有解释。`ds_urma_mock_dlopen_ops` 不是公共 shim；只在 `urma_perf.h` 中声明且没有
  `urma_NNN` 接口节点的性能接口不得虚构目标节点。

不得按 `(parent, child)` 去重；同一函数不同位置、分支或上下文的物理调用分别分析。检查宏、别名、函数指针、模板、callback
注册和动态绑定是否形成脚本未覆盖的间接 `ds_urma_*` 调用，发现时作为人工补充调用点记录。

计算三个候选产物的 SHA-256 写入分析记录。正式写树前确认哈希未变化；变化时重新生成并重做受影响分析。

### 2. 校验节点映射

对每个有效调用点执行全部校验：

1. `shim` 必须在当前 `urma_dlopen_util.h` 声明，去掉 `ds_` 后与 `child` 完全一致；
2. `child` 必须是 `urma_api.h` 声明的公共接口；calls 产物已按声明过滤，非公共目标只出现在
   `excluded_non_root_calls`；
3. `target_root_id` 必须匹配 `^urma_[0-9]{3}$`，并同时存在于 `urma_failure_mode.json` 和
   `failure_mode_tree.json.urma`。`target_root_id` 是按 `urma_api.h` 声明顺序生成的候选编号；与节点表不一致时，
   以 `urma_failure_mode.json` 中 `函数名` 与 `child` 完全一致、`文件名` 为公共头文件的接口根编号为准，并记录差异；
4. 目标节点的 `函数名` 与 `child` 完全一致，`文件名` 是公共头文件，且该节点是接口根而非同名具体日志节点。

源节点从 `kvcache_failure_mode.json` 中选择，且必须同时存在于 `failure_mode_tree.json.kvcache`：

- **runtime 子节点**（`kvcache_runtime_NNN`）：用物理日志的裸文件名、有效函数/重载和 `故障现象` 的全部稳定关键字唯一映射 `/tmp/kvcache_runtime_err.json` 中 `candidate_kind=emitted_log` 的 entry；不得只凭裸函数名或错误码选择。
- **access 入口根**（`kvcache_access_NNN`）：仅用于"access 入口根上提"场景（见步骤 4），按失败返回的 K_* 错误码匹配对应入口根。

零匹配或不能消歧时标记证据不足。

### 3. 确定上游归属（最近日志上提）

用调用点 `parent_qualified` 与 `/tmp/kvcache_callchains.json.functions[].qualified_name` 匹配定位函数节点；两套
解析器对匿名命名空间、lambda、重载的命名可能不同，不匹配时用裸函数名、物理文件和源码阅读消歧，不得只凭裸名认定。

自下而上沿 `callers`（含传递闭包）枚举上游函数；对每个带 runtime 日志节点的上游函数，用源码验证其日志是否报告或传播
该 URMA 失败——调用返回路径上的 `RETURN_IF_NOT_OK` 系宏、`LOG_IF_ERROR`、状态透传后再记录等；距离最近的验证通过者
为上提源。调用图边缺失时（函数指针、回调、跨 TU 实例化），结合源码人工补链并记录。静态调用图只用于定位候选，不证明
失败传播。

调用点位于后台轮询、资源析构、请求/完成对象、重试、URMA-to-TCP 回退或日志控制变量上下文时，caller 链可能不含真正的
观察者，完整阅读 [异步、生命周期与回退规则](references/async-lifetime-and-fallback.md) 后按生产/关联/消费/观察四步
证明，观察目标为最近日志节点或 access 边界；纯同步直接返回路径不要加载该参考。

同一物理调用点被多条执行路径复用时，分别记录每个上下文的对象关联、失败通道、最近日志和源节点，一个物理点可以确认多条
源不同的边。失败最终以状态码返回 RPC 响应或公共 API 且途中无日志时，直接按"access 入口根上提"处理，无需再向
KVClient 公共 API 做归属分析。

### 4. 逐调用点判定故障传播

对非 `void` API 分别枚举返回值、errno 和每个输出参数的检查分支；一个通道不成边不能代表整个调用点无边。只有全部通道均被
排除后才能判定"无边"。异步完成错误必须证明同一请求或对象的生产、关联、消费和日志触发。

| 结论 | 条件 | 处理 |
| --- | --- | --- |
| 调用点直接观测 | URMA 边界失败在调用函数内触发状态故障（`RETURN_STATUS` 系）或错误日志 | 该 `kvcache_runtime_NNN` 日志节点连接对应 `urma_NNN` 接口节点；更上层传播用 KVCache 内部边 |
| 最近日志上提 | 调用函数未记录，沿全量调用图最近的 upstream 函数日志报告或传播该失败 | 该 `kvcache_runtime_NNN` 日志节点连接对应 `urma_NNN` 接口节点 |
| access 入口根上提 | 整条 caller 链没有日志，失败以确定的 K_* 到达 access 边界（公共 API 返回或 RPC 响应状态码） | 按 K_* 匹配的 `kvcache_access_NNN` 入口根连接对应 `urma_NNN` 接口节点 |
| 仅日志可观测 | 失败触发调用函数日志后被吞掉、恢复或成功回退 | 该 `kvcache_runtime_NNN` 日志节点连接对应 `urma_NNN` 接口节点，但不继续向上 |
| 无边 | 全部失败通道被忽略、覆盖、恢复、转成功，或 `void` API 无可观察失败状态 | 不写边并记录逐通道原因 |
| 证据不足 | 调用、归属、传播或日志映射无法确定 | 不猜测、不写边 |

每个跨组件调用点必须出现在分析记录中并给出明确结论：凡存在任一可观察失败通道（返回、errno、输出、异步状态）且能定位
观察点的调用点，必须产出一条边（直接观测 / 最近日志上提 / access 入口根上提三选一）；结论为无边时必须逐通道给出不可
观察证据。不得为完全不可观察的调用点（如 `void` 且无关联状态、析构忽略返回）强行挂到最近日志——那会制造虚假诊断边。

清理、回滚或析构中的 URMA 调用必须按其自身结果判定；不能因为它由另一个主失败触发，就把主失败日志自动连接到清理路径对应的 access 入口根。
现有故障树只用于发现归属冲突，不能反向证明源码路径。

### 5. 记录并写入

生成 `/tmp/kvcache_urma_edge_analysis.json`，至少包含：

```json
{
  "call_count": 0,
  "supplemental_call_count": 0,
  "analyzed_count": 0,
  "artifact_sha256": {},
  "root_coverage": {},
  "confirmed_edges": [],
  "excluded_non_root_calls": [],
  "entries": []
}
```

`entries` 按 `file/line/column` 排序，覆盖脚本调用点及人工补充调用点。每条记录物理位置、调用者、shim、URMA API 与目标根、
所有上下文、失败通道（返回/errno/输出/异步）、传播变量或对象、重试/回退条件、最近日志节点、结论、源节点或无边原因及
源码证据。一个调用点有多个上下文时在同一 entry 分别记录。

必须满足：

- `analyzed_count == call_count + supplemental_call_count == entries.length`，即每个跨组件调用点都有结论；
- `excluded_non_root_calls` 与调用点产物一致，并记录为何没有有效 `urma_NNN` 接口节点；
- `confirmed_edges` 是可生成边的 `{source, target}` 去重汇总；
- `root_coverage` 以 `urma_failure_mode.json` 中公共头文件的 `urma_NNN` 接口根为 key 覆盖全部接口，并与 calls 产物的
  `called_root_ids`/`uncalled_roots` 交叉校验，记录调用点数、确认边数、无边数和证据不足数；未调用节点标记
  `not_called`。没有 `urma_NNN` 接口节点的 shim 调用只进入 `excluded_non_root_calls`，不得加入 `root_coverage`。

先基于原树生成 `/tmp/failure_mode_tree.connected.json` 并校验，再把相同追加应用到正式文件：

- 保留所有 key、原有边和数组相对顺序，只在已有 `kvcache` source 的 value 末尾追加并去重；
- 普通 source 是最接近边界的已映射 `kvcache_runtime_NNN` 日志节点；access 入口根上提 source 是按 K_* 错误码匹配的 `kvcache_access_NNN`；target 是有效
  `urma_NNN` 接口节点，且必须匹配 `^urma_[0-9]{3}$`；
- 新增边必须与 `confirmed_edges` 完全一致，无重复、自引用或越过最近日志节点；
- 写入前三个候选产物哈希仍与记录一致；
- 结构化差异只能是已有 `failure_mode_tree.json.kvcache` value 新增确认的 `urma_NNN` 编号；
- `failure_mode_tree.json.urma` 及其他非 `kvcache` 顶层对象必须逐字节语义等价。

任何校验失败时不得修改正式文件。
