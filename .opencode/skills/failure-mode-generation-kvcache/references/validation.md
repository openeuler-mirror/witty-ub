# 完成闸门

写入最终 JSON 前读取并执行本文件。任何失败都不得静默忽略。

先运行 `scripts/validate_kvcache_pipeline.py` 做确定性检查；本文件中暂不能由脚本证明的自然语言质量和源码传播证据仍须人工复核。

## 中间产物

- status：`schema_version=1`，数量与 `status.h` 一致。
- runtime：`schema_version=5`；`candidate_id`、`group_id` 唯一；每个 entry 恰属一个 group；`sum(groups[].candidate_count)==total`；lane 汇总一致；每个非排除的 `dynamic_only` group 都有 `resolve_log_template`、`need_skill=true` 且位于 semantic lane。
- batch manifest：`scan_fingerprint` 与 runtime 一致；全部 semantic group 恰好出现一次；同一 `callable_key` 不跨批。
- state JSONL：header fingerprint 与 runtime 一致；每个 group 一条记录；最终没有 `pending` 或 `needs_review`。复用记录必须是一一对应的相同 `content_hash`。
- access：`schema_version=1`；全部 `AccessRecorderKey` 至少一个构造点；空构造点单列复核。
- callgraph：`schema_version=2`、`analysis.complete=true`；TU 无失败；函数、入口和边数量与源码规模相称。
- AST evidence：fingerprint 与 runtime 一致；只在 group `content_hash` 一致、`complete=true`、唯一非零 `auto_error_code` 时自动采用。TU 失败或不完整组回退人工分析。

## 错误码与根节点

- `kvcache_error_code_info.json` key 数量等于 status `total`，无遗漏、无多余、按数值升序。
- 每个值只含顺序固定的 `故障现象`、`故障原因`；两者均为一句话；现象以对应 `请求返回K_*，` 开头。
- K_OK 按 respMsg 非空特例处理。
- `code=0 + respMsg 非空` 根恰有一个，错误码为 `K_OK(0)`，并包含 `{"status_code": 0, "resp_msg_nonempty": true}` 匹配条件；其他节点不得使用 `K_OK(0)`，也不含 `匹配条件`。
- access 根数 = runtime 实际出现的非零 K_* 数 + 2；错误码值与 `error_definitions` 一致。
- 根名称为自然语言；根现象和原因与错误码信息表逐字一致。

## Runtime 节点

- 所有非基础设施物理候选都被一个 runtime group 节点或显式排除记录覆盖。
- 组内 `physical_sites` 全部保留在 checkpoint 证据中；不得因聚合丢分支。
- 每个 `resolve_log_template` 的 resolved 记录都包含 `log_template.stable_literals`、非空源码 `evidence`；无稳定字面量时还必须有 `match_enabled=false` 和非空 `reason`。
- 编号从 001 连续；字段顺序、类型、裸函数名、文件 basename、错误码和文案符合输出契约。
- 每个 runtime `故障名称` 唯一、≤20字并采用“具体操作时具体原因”，不得退化为“运行操作时”；`故障原因` 是包含触发条件、失败来源和影响的完整单句。
- 可匹配 runtime `故障现象` 严格采用“依次匹配`关键字`”格式；动态值和纯标点不得作为关键字。
- 普通 runtime 节点不得使用“无稳定关键字”；确实不可匹配的例外节点必须包含 `{"日志匹配":{"enabled":false,"reason":"..."}}`，其他节点不得包含该字段。
- 节点数组无重复；每个 runtime 节点至少有一个父节点。

## DAG

- 只有 access→最上层 runtime 和传播上游 runtime→下游 runtime 两类边。
- 每条 runtime→runtime 边都具备 caller 关系和源码传播证据。
- 所有引用有效、无重复、自引用和环。
- `failure_mode_tree.json.kvcache` 覆盖全部 access/runtime 编号；叶节点值为 `[]`。
- key 顺序与节点数组一致；共享节点可多父但只编号一次。

## 文件边界

- 对比写入前后，`failure_mode_tree.json` 的 `kvcache` 之外内容完全不变。
- `data/kvcache/kvcache_conn_fault_mode.json` 不变。
- JSON 可解析，字段顺序稳定，仓库不包含 `/tmp` 产物或分析 cache。
