# Runtime 日志分析与故障关系

生成或更新 runtime 节点及 `failure_mode_tree.json.kvcache` 时读取本文件。

## 候选、分流与聚合

`find_kvcache_runtime_err.py` 的 schema 5 同时输出 `entries` 和 `groups`：

- `entries` 是物理点覆盖清单，包含完整语句、callable、稳定字面量、错误码表达式和源码位置；不得直接作为逐点工作队列。
- `groups` 是分析和建节点的工作单元。身份为完整相对路径、callable（签名和起始行）、ERROR/FATAL 级别和实际输出模板。
- `deterministic` 组的模板和错误码都已由脚本确定；仍须生成故障名称、原因、域及关系。
- `semantic` 组按 callable 批次执行 `skill_analysis`。任务可包含 `resolve_status_code` 和 `resolve_log_template`；只要任一任务存在，`need_skill=true`。
- `excluded_infrastructure` 组保留物理点记录，不生成节点。

同一组须合并全部已证实的触发分支和直接下游。组内错误码不唯一时写 `null`。`template_confidence=dynamic_only` 已把规范化语句纳入身份，宁可少聚合也不得误合并。不同路径、callable 或仅部分相同模板不得合并。

所有函数一视同仁，不要求从公共 API 可达。RPC handler、后台线程、定时任务、异步回调、静态初始化和无 caller 函数都在范围内。纯日志、指标、性能或 trace 基础设施（如 `logging.cpp`、`failure_handler.cpp`、`inject_point.h`）不生成 runtime 节点。

## 日志模板

脚本先保守解析直接字面量、直线数据流中的局部 `std::string`/字符串流拼接和可定位的具名常量。`template_confidence=exact` 时直接使用 `stable_literals`，不得重复逐点进源码恢复。

无法由脚本证明模板时必须输出 `template_confidence=dynamic_only`，追加以下任务并进入 semantic lane，不得仅因错误码已确定而跳过：

```json
{
  "task": "resolve_log_template",
  "expression": "rc.GetMsg()",
  "reason": "需要追踪日志消息来源并恢复稳定关键字"
}
```

处理 `resolve_log_template` 或宏语义不明时：

1. 展开包装宏直到公开的 `LOG/DLOG/SLOW_LOG` 或 FATAL 检查宏；物理点仍归调用者。
2. 按输出顺序保留全部稳定字面量。格式占位符、流式运行时值和 `Status::ToString()` 等动态内容是分隔符。
3. 保留大小写、标点和包装宏固定文本，例如 `Detail:`；不包含时间戳、级别和源码位置前缀。
4. `CHECK*` 使用 `Check failed:` 及字符串化条件/比较表达式；节流计数和时间条件不是消息关键字。
5. 追踪局部赋值、字符串流、`FormatString`、具名常量、Status 构造/包装和必要的上游 callable；变量名以及 `Status::ToString()` 的通用 `code/msg` 外壳不得充当关键字。
6. 原则上必须恢复至少一个业务稳定字面量。穷尽当前源码中的消息来源后仍无法恢复时，分析结果的 `log_template` 必须包含空 `stable_literals`、非空 `evidence` 和 `reason`，并设置 `match_enabled=false`。

日志模板任务结果格式：

```json
{
  "log_template": {
    "stable_literals": ["Open ", " failed"],
    "normalized_template": "Open <dynamic> failed<dynamic>",
    "evidence": ["common/example.cpp:42 的 err 由同一分支内字符串流构造"],
    "match_enabled": true
  }
}
```

确实不可匹配时，`stable_literals=[]`、`match_enabled=false`，并增加非空 `reason`。不得仅根据脚本的 `dynamic_only` 直接得出不可匹配结论。

可匹配节点的最终 `故障现象` 写成“依次匹配`关键字1`、`关键字2`”。确实不可匹配的例外节点才写“无稳定关键字（按文件名、函数名和ERROR/FATAL级别定位）”，并按输出契约禁用日志匹配。

## Status 错误码证据

按以下优先级使用证据：

1. runtime group 已给出非零 `error_code`：直接采用。
2. `/tmp/kvcache_status_ast.json` 对同一 `content_hash` 给出 `complete=true` 且 `auto_error_code` 为唯一非零 K_*：直接采用，并保留 `candidate_evidence`。
3. 其他 semantic 组才人工追踪 `skill_analysis`。

人工追踪从 `error_code_expression` 和失败分支反查定义、赋值、返回、清理覆盖、Status 复制、`GetCode()`、映射函数、lambda 捕获及输出参数。只有整个日志触发路径能唯一归一为一个非零 K_* 时填写该码。多 K_*、动态 Status、K_OK、裸整数、errno、CUDA/HCCL/URMA/RPC 私有码或未显式转换的外部枚举均写 `null`；数值偶然相同不能映射。

AST 证据是保守加速器：`complete=false`、无调用点、多个可能码或 TU 失败时不得猜测；回退到源码分析。错误码描述当前日志报告或紧随其后的失败结果，不得混入只用于进入外层分支的状态。

宏语义：

- `LOG_IF_ERROR`、`DLOG_IF_ERROR` 记录失败但不返回；`LOG_IF_ERROR_EXCEPT` 还排除指定码。通常属于失败被吞掉，除非后续保存等价状态。
- `ASSIGN_IF_NOT_OK_PRINT_ERROR_MSG` 同时写 `lastRc_`，继续追踪该变量。
- `RETURN_IF_NOT_OK_API` 的日志报告 `SendStatus` 二次失败，返回值仍是原始 Status；两条因果链必须分开。
- `RETRY_ON_EINTR` 最终报告 errno，错误码为 `null`。
- FATAL 检查终止进程，错误码通常为 `null`。
- DLOG/DCHECK 仍保留，并在原因中写明可输出配置条件。
- 采样、计数和节流只控制是否输出，不创造故障因果。

## 局部调用图

全量调用图来自 Clang Static Analyzer，不以公共 API 为根。它按 Clang 限定名聚合重载；运行时函数指针、部分回调、跨 TU 实例化和虚调用可能缺边。无 caller 仅代表静态图顶层入口。

不得把 `/tmp/kvcache_callchains.json` 整体载入模型上下文。对当前 group 或 batch 运行 `query_kvcache_callgraph.py`，只读取局部 slice。`root_matches[].ambiguous=true` 时结合 callable 和源码消歧。调用边本身不证明错误传播。

## 故障 DAG

关系只有两类：

```text
access 根 -> 最上层 runtime 节点 -> 更下游 runtime 节点
```

对 runtime 节点 N 所在函数 F：

1. 沿局部图的 callers 自下而上查找最近的函数 G。只有 G 的某个日志节点确实在调用 F 的返回路径上记录、包装或透传该失败时，才建立 G→N。中间有更近的传播日志节点时优先最近层；多条独立 caller 链可有多父。
2. caller 链上没有传播该失败的上游节点时，N 是最上层节点，按错误码/severity 挂 access 根。
3. 禁止仅凭调用边挂接，禁止用虚假边消灭孤立点。
4. 共享 runtime 节点只编号一次，可以多父。
5. 若最近传播边会成环，继续向上寻找不成环的节点；仍无则按最上层节点处理。

最上层节点归因：

| 情况 | access 根 |
| --- | --- |
| 唯一非零 K_* 且已有对应根 | 对应 K_* 根 |
| 唯一 K_* 但入口根缺失 | 记录脚本遗漏，不臆造边 |
| `null` + FATAL | 进程级 FATAL 特殊根 |
| `null` + ERROR | code=0 + respMsg 非空特殊根 |

每个 runtime 节点必须至少有一个 access 根或上游 runtime 父节点。树中保留所有 runtime key，叶子值为 `[]`。

## Runtime 故障域

按物理点子系统填写，可与 access K_* 根不同：用户、OS、三方 etcd、KVCache、URMA、硬件、RPC/网络。典型区分：

| runtime 点 | 故障域 |
| --- | --- |
| URMA 链路重建、JFS 重建、降级、软件超时 | URMA |
| poll error、异常 CQE/驱动硬件状态 | 硬件 |
| mmap、mlock、fd、磁盘等系统资源 | OS |
| etcd timeout/unavailable | 三方 etcd |
| RPC 超时、TLS、ZMQ 发送接收 | RPC/网络 |
| 进程内状态机、worker、缓存逻辑 | KVCache |

每个组的分析记录至少保留：物理位置、宏、callable、实际模板、触发条件、Status 来源、错误码证据、真实输出点、同步/异步/RPC 分类、故障域、父节点及传播证据或排除理由。记录写入 JSONL checkpoint 的 `result`，不写入最终节点数组。
