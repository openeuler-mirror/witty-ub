---
name: failure-mode-generation-urma-for-brpc
description: 分析 URMA C 源码，为 brpc 诊断场景生成以公开 URMA API 为根、以 URMA_LOG_ERR 及四个 URMA_CHECK 参数检查宏调用点为具体节点的故障模式图；适用于需要解析 provider ops 间接调用、WR/CR 与 notifier 异步链、bond worker/health-check/failback 路径，并将关系写入 failure_mode_tree.json 的 urma4brpc key 的任务。
---

# URMA failure modes for brpc

## 目标

从 URMA 公开 API 出发，以可达路径中的直接 `URMA_LOG_ERR` 和指定参数检查宏调用点为具体故障节点，依据真实错误传播和异步对象/状态传播生成故障模式有向图。静态调用图只定位候选路径，不等同于故障关系。

## 输入和边界

- URMA 组件的源码路径。

禁止参考旧结果，包括项目中已存在的旧产物、git 历史提交和 `/tmp` 中的旧临时文件；必须重新运行本 skill 的脚本并从当前源码分析。

## 输出

- 将节点定义写入 `./data/urma/urma_failure_mode_for_brpc.json`。
- 将全部节点及直接下游关系写入 `./data/failure_mode_tree.json` 的 **`urma4brpc`** key。
- 禁止新增、覆盖或改名 `failure_mode_tree.json` 的 `urma` key。
- 更新关系文件时保留 `urma4brpc` 之外的所有 key 及内容。

节点只包含：

- `故障编号`：根节点先按 `/tmp/urma_api_callchains.json` 的 `roots` 顺序编号，再为具体节点连续编号，格式为 `urma4brpc_xxx`。
- `故障名称`：概括为“执行某操作时某原因”，不得复制函数名或日志原文充当名称。
- `故障现象`：格式为“依次匹配`关键字1`、`关键字2`”；按格式占位符切分并匹配日志中的全部非空字面量，去除字面量末尾的换行符。
- `错误码`：具体节点按 `/tmp/urma_log_err.json` 填写；确定的 URMA 宏（包括由 errno 映射得到的宏）写成 `URMA_EINVAL(22)`，空指针哨兵写字符串 `NULL` 或 `nullptr`，裸 `0/-1` 写 JSON number，无法静态确定或没有错误返回时写 JSON null。根节点写 JSON null。
- `故障原因`：根据日志分支条件、失败来源和函数作用说明直接原因；需要继续匹配下游时填“向下级匹配”。
- `解决办法`：具体节点默认“无”，根节点填“向下级匹配”。
- `函数名`：只填裸 C 函数名，不带文件、类型、provider 或其他限定。
- `文件名`：源码裸文件名，根据`find_urma_log_err.py`脚本输出的`file`字段填写，不得携带目录路径。

### `文件名`要求

1. `文件名`只允许填写源码裸文件名。例如脚本输出的`file`为`core/urma_cp_api.c`时，最终 JSON 的`文件名`填写其最后一级`urma_cp_api.c`。
2. 具体故障节点填写物理日志点所在文件。节点聚合身份由“裸文件名 + 裸函数名 + 完整`log_content`”共同确定；不同裸文件名中的同名、同日志函数必须拆分为不同节点。
3. 公共 API 根节点没有物理日志点，`文件名`填写该 API 在`core/include/urma_api.h`或`core/include/urma_types.h`中的声明文件裸名，并与`generate_urma_callchains.py`提取根节点时使用的头文件一致。

错误码数值固定使用脚本顶层 `error_definitions`，不得把宏后面的 errno 别名写入结果：`URMA_EAGAIN=11`、`URMA_ENOMEM=12`、`URMA_ENOPERM=1`、`URMA_ETIMEOUT=110`、`URMA_EINVAL=22`、`URMA_EEXIST=17`、`URMA_EINPROGRESS=115`、`URMA_FAIL=4096`、`URMA_SUCCESS=0`。

## 节点和聚合

每个根节点对应一个公开 API，没有物理日志点。根节点的故障名称概括 API 功能失败；故障现象、原因和解决办法均填“向下级匹配”，函数名填 API 裸名。

每个具体节点对应一个有效日志故障：

1. 日志提取脚本输出的每条 entry 对应一个候选日志点；普通 entry 来自函数内的物理 `URMA_LOG_ERR`。
2. 四个参数检查宏的每个函数内调用点对应一个候选日志点；脚本跳过前 60 行的四个宏定义。
3. 对四个参数检查宏，脚本直接把 `log_content` 归一为 `"Invalid parameter.\\n"`。生成 `故障现象` 时使用该 `log_content`（去除末尾换行符），不使用宏实参列表。
4. 同一裸文件名、同一裸函数中 `log_content` 完全相同的物理点或检查宏调用点聚合为一个节点；仅部分相同不得聚合，不同裸文件名中的日志点不得聚合。
5. 在全部 API 同步与异步路径间全局去重。共享节点只分配一个编号，但允许多个上游指向它。
6. 不可达日志不生成节点；所有具体节点必须至少从一个公开 API 根节点可达。

## 错误码规则

使用每条 entry 的 `error_code`、`error_source`、`error_expression` 和 `needs_skill` 判断错误传播。脚本追踪日志后的 `return`、简单变量赋值和 `goto`，同时追踪日志所在分支内日志之前或日志之后、退出之前对 `errno` 的明确赋值。

- `error_source=return` 表示错误由函数返回值承载；`errno` 表示存在明确的 `errno = ...` 赋值；`none` 表示明确执行 `return;`、`continue` 或 `break`，该路径没有错误返回；`unknown` 表示控制流无法静态确定。
- 同一路径同时明确设置 `errno` 并返回哨兵时，以 `errno` 为错误来源。例如 `errno = ENOMEM; return NULL;` 输出 `URMA_ENOMEM`，不输出 `NULL`。
- `error_expression` 使用脚本沿简单变量赋值和 goto 路径解析后的表达式；不得仅根据日志文字推断错误码。

按以下规则填写最终节点：

1. `error_code` 是 URMA 宏字符串时，从顶层 `error_definitions` 取十进制值并输出 `宏(value)`；即使源码返回 `-URMA_EINVAL`，仍输出 `URMA_EINVAL(22)`。
2. `error_code` 是字符串 `NULL` 或 `nullptr` 时原样输出，用于区分明确空指针失败和未知错误码。
3. `error_code` 是整数 `0` 或 `-1` 时直接输出 JSON number。脚本仍将这两种裸值标记为 `needs_skill=true`，因为它们不能仅凭数值对应到一个 URMA 错误宏。
4. `error_code` 为 null 时输出 JSON null；只有 `needs_skill=true` 的 entry 才继续结合源码二次分析。二次分析只能在证明为本节列出的 URMA 宏、`NULL`/`nullptr` 或裸 `0/-1` 时填写，否则保持 null。
5. `needs_skill=false` 仅适用于以下情况：表达式能唯一映射到一个 URMA 宏；函数明确返回 `NULL`/`nullptr` 且没有更具体的 errno；`error_source=none`；或四个检查宏按展开语义已确定结果。其他情况一律为 `true`。

errno 和状态传播规则：

- 显式 `EAGAIN/ENOMEM/EPERM/ETIMEDOUT/EINVAL/EEXIST/EINPROGRESS`，无论是否带负号，分别映射为 `URMA_EAGAIN/URMA_ENOMEM/URMA_ENOPERM/URMA_ETIMEOUT/URMA_EINVAL/URMA_EEXIST/URMA_EINPROGRESS`。
- 对 `errno = ...` 使用同一映射；能映射时 `error_source=errno` 且 `needs_skill=false`，不能映射的 `EIO` 等保留表达式并标记 `needs_skill=true`。
- UDMA 或 provider 操作的返回值按 `urma_status_t` 原样传播，不建立单独映射规则。若追踪后的表达式是确定的 URMA 宏，按该宏输出且 `needs_skill=false`；动态 `ret/status`、函数调用结果或 provider 私有状态无法静态确定具体宏时，`error_code` 保持 null 且 `needs_skill=true`。
- 明确执行 `return;`、`continue` 或 `break` 且没有 `errno` 赋值时，`error_code` 为 null、`error_source=none`、`needs_skill=false`；同一路径有明确 `errno` 赋值时仍以 `errno` 为准。

四个检查宏按展开语义直接确定：pointer 宏通过 `errno = EINVAL` 得到 `URMA_EINVAL(22)`，status 和 negative-status 宏通过 return 得到 `URMA_EINVAL(22)`；这些 entry 均为 `needs_skill=false`。

## 故障边判定

`A: [B]` 表示 A 日志会在 B 所代表的下游故障沿返回值、errno、输出参数、对象状态或异步状态传播时触发。它不是普通函数调用边。

逐个日志点执行：

1. 定位日志所在 `if/switch/goto`、提前返回、清理或回调分支。
2. 反向追踪触发条件中的变量，分类为本地产生、同步下游透传、异步对象/状态传播或失败被吞掉但可观测。
3. 仅当下游失败结果沿实际控制流到达日志条件时建立边；相邻调用、同一函数或调用图可达均不是充分证据。
4. 只连接对应失败路径上最近的下游日志节点。穿透无日志包装函数，但禁止越过最近节点连接所有后代。
5. 本地参数、状态、内存或系统调用失败且不依赖下游日志时，节点 value 为 `[]`。
6. 下游失败被忽略、覆盖、恢复或转成成功时，不连接虚假上游具体节点。若该日志仍属于 API 功能路径，由有证据的 API 根直接连接。
7. 一个条件混合本地状态和多个调用结果时，只连接能证明触发该分支的调用来源。

分析时为每个物理日志或参数检查宏调用点记录：`文件:行号`、日志/检查宏、有效函数、触发条件、来源分类、调用点、传播变量/状态、直接下游日志和代码证据。该记录仅用于自检。

## 根节点归属

从日志沿实际失败传播反向追踪：

- 途中最近的上游日志捕获该失败时，由该日志连接当前节点。
- 途中没有上游日志时，由对应公开 API 根连接。
- 同一共享节点可在不同路径上分别连接根节点或具体节点。
- provider 名称、资源方向、同一全局对象或同一文件不能单独证明 API 归属。
- 清理、销毁、回滚和重试日志必须枚举实际调用点；按进入该路径的 API 归属，不按被清理资源名称猜测。

为每个候选根记录完整证据链：`公开 API -> 调用/生产点 -> 返回值、对象或状态 -> 日志点`。无法写出完整链的根不得连接。

## URMA 间接调用和异步规则

### Provider ops

URMA 核心 API 大量调用 `ctx->ops`、`dev->ops` 或 provider ops。使用调用链 JSON 的 `provider_bindings` 和 `function_pointer` 边定位候选实现，同时遵守：

- designated initializer 只证明某字段可能绑定实现，不证明当前对象运行时选择了该 provider。
- 结合 provider 注册、设备匹配、context 创建及 `ops` 赋值证明具体实现可达。
- `unresolved_indirect_calls` 必须逐项复核。跨 DSO 驱动实现或运行时赋值不在当前仓中时，记录边界，不臆造下游日志。
- `urma_init` 的 `dlopen` 可触发 provider constructor，`urma_uninit`/卸载可触发 destructor；仅在动态加载/卸载路径有源码证据时纳入相应日志。

### WR、CR 和异步通知

确认异步关系必须同时具备生产、关联和消费证据：

1. API 提交或登记具体 WR、WR id、jetty/JFS/JFR、JFC、notifier、notify、CR、eventfd 或用户上下文。
2. 后台入口、provider 或后续 API 处理同一对象，或通过 id、handle、fd、context 字段建立明确关联。
3. 日志位于该对象的实际处理路径。
4. 若连接到后续 API 的具体日志，必须证明异步失败写入的状态会被该 API 读取并触发日志。

重点检查：

- `post_jfs_wr`、`post_jfr_wr`、`post_jetty_send_wr`、`post_jetty_recv_wr` 与 `poll_jfc`、`wait_jfc`、`get_async_event` 的 WR/CR 路径；
- async import/bind/unimport/unbind、notifier、`wait_notify`、`ack_notify` 和回调结果；
- bond worker、epoll/eventfd、netlink callback、timewheel、health-check、failover/failback 和重传。

`pthread_create` 或 callback registration 边只表示执行候选。必须继续证明线程/回调处理的数据源属于哪个 API。共享全局 context 或组件相同不够。

## 操作步骤

1. 提取日志：

```bash
python3 .opencode/skills/failure-mode-generation-urma-for-brpc/scripts/find_urma_log_err.py \
  <path-to-urma-source>
```

脚本默认写入 `/tmp/urma_log_err.json`。确认：

- `search_symbols` 恰好包含 `URMA_LOG_ERR` 和四个检查宏；
- `error_definitions` 包含本 skill 列出的九个 URMA 宏，且值全部为具体十进制数；
- `return_sentinels` 为 `NULL`、`nullptr`、裸 `0/-1`；
- 每条 entry 均包含 `error_code`、`error_source`、`error_expression` 和布尔值 `needs_skill`；
- 每条 entry 的`file`均为相对源码路径；生成故障模式的`文件名`时取该路径最后一级裸文件名；
- `needs_skill=false` 的 entry 必须已经唯一映射到 URMA 宏、明确返回空指针、明确没有错误返回，或属于已确定语义的检查宏；
- 没有头文件 entry，且 `core/urma_cp_api.c` 第 1～60 行没有 entry。

2. 生成候选调用链：

```bash
python3 .opencode/skills/failure-mode-generation-urma-for-brpc/scripts/generate_urma_callchains.py <path-to-urma-source>
```

读取 `/tmp/urma_api_callchains.json`。使用 `roots` 固定根节点顺序，使用 `functions`、`edges` 和 `provider_bindings` 定位候选路径，逐项人工复核 `unresolved_indirect_calls` 和 `analysis.limitations`。

3. 按“错误码规则”直接采用 `needs_skill=false` 的脚本结论；仅对 `needs_skill=true` 的 entry 做源码二次分析，不得覆盖脚本已确定的 URMA 宏、errno 映射或无错误返回结论。

4. 按节点、聚合、故障边、归属及 URMA 异步规则分析源码，生成 `data/urma/urma_failure_mode.json`。

5. 在 `data/failure_mode_tree.json` 中新增或覆盖 `urma4brpc`，保留其他内容。每个节点都必须作为 key 出现，叶子值为 `[]`。

6. 完成质量检查并修正问题。

## 质量检查

1. API 根与调用链 `roots` 数量、顺序完全一致；types header 恰好只含两个指定 API。
2. 所有纳入点来自本 skill 指定的五个 symbol；注释、字符串和字符字面量中的同名文本均已过滤；只扫描 `.c` 文件，`core/urma_cp_api.c` 第 1～60 行无节点，后续直接日志和检查宏调用均保留。
3. 每个节点字段完整、编号连续、函数名和文件名均为裸名，每个节点均有不含目录的`文件名`字段；同文件同函数同全文日志已聚合，不同文件日志未聚合，全局无重复节点；错误码格式和值符合“错误码规则”。逐项抽查直接 URMA 返回、`NULL`、`errno` 赋值、无错误返回和动态 `urma_status_t` 传播，确认其 `needs_skill` 分类正确。
4. 每条具体边都有控制流或异步对象/状态证据，且只连接最近下游日志；调用图边未被直接投影。
5. 所有具体节点从至少一个根可达；关系引用有效、无重复、无自引用，所有 value 均为数组。
6. `failure_mode_tree.json` 使用 `urma4brpc`，不存在对 `urma` key 的修改；对比更新前后确认其他 key 内容不变。
7. 已复核全部 `unresolved_indirect_calls`、provider 运行时选择、provider constructor/destructor、notifier 与 WR/CR 异步路径。
