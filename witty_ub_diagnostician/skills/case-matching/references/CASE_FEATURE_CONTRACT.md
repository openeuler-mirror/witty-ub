# 案例特征契约（写入侧 ↔ 检索侧 ↔ 后续 RAG 共用）

本文件定义**一份案例文档长什么样**：结构化头（供精确过滤/打分）+ 正文（供语义检索）。
规则通道与将来的向量通道消费的是**同一份特征**，只是用法不同——结构化字段做过滤与加权打分，
文本化字段做 embedding 召回。任何一侧改了字段口径，两侧必须同时改。

本 Skill 只做检索侧；写入侧由 `diagnostic-report-generation` 沉淀案例时执行。

---

## 一、案例文档结构

同一份语义特征有两个物理承载：

- **`diag_case_library`（正解，本契约主体）**：只收人工确认过的案例，`status` 走
  `draft → confirmed → archived`，检索默认只返回 `confirmed`。
- `diagnosis_case`（legacy）：无准入关卡的旧表，字段更薄，检索侧只当线索用。

```
diag_case_library
├── 准入与留痕（legacy 无）
│   ├── status / revision
│   └── created_by / confirmed_by / confirmed_at / archived_by / archived_at / archive_reason
├── 结构化头（可过滤、可打分）
│   ├── log_type / source / source_url / kb_id（仅作来源标注，可空）/ kb_name
│   ├── operation（GET / SET / N/A，服务端过滤字段）/ fault_type / confidence
│   ├── status_codes[]              ← L1，权重 3.0
│   ├── failure_mode_ids[]          ← L1，权重 3.0
│   └── 信号列（写入时同步进 diag_case_library_signal）
│       ├── hosts / pods / src_ips / dst_ips / cluster_name   ← L3，权重 1.5
│       ├── latency_components[]                              ← L2，权重 1.5
│       └── log_keywords[]                                    ← L5，权重 1.0
├── 正文（不可过滤，供语义通道与人工阅读）
│   ├── title / symptom_summary / root_cause_summary / root_cause_detail
│   ├── stage_features_json（L2 阶段桶快照）/ fault_shape（L1 时间形状）
│   ├── version_json（L4 版本快照）/ scope_limits（不适用场景）
│   ├── time_window_json / node_type
│   ├── evidence_json[]（api|trace|log|sql 锚点）/ counter_evidence_json[]
│   ├── remediation_json[]（分步处置）/ verification_json（验证闭环）
│   ├── relations_json[]（案例关系）/ source_log_ids[]
│   └── search_text（喂 embedding 的正文，写入时生成，剔除 IP/集群噪声）
└── 元信息：hit_count / created_at / updated_at
```

legacy 把上述信号与正文压缩进 `fingerprint_json` + `symptom_summary` / `root_cause` /
`recommendation` 三段，无准入、无证据锚点、无验证闭环，也没有 `operation` 过滤字段。

## 二、字段归属与理由

| 特征 | 存放位置（library / legacy） | 为什么放这里 |
|---|---|---|
| 状态码、故障模式 ID | 同名顶层列 `status_codes` / `failure_mode_ids` | 服务端信号表直接建索引，权重最高（3.0） |
| IP / Pod / 主机 / 集群 | library：独立列 `src_ips` / `dst_ips` / `pods` / `hosts` / `cluster_name`；legacy：`fingerprint_json` 对应数组 | 两者都进信号表（`SIGNAL_FIELD_MAP`），权重 1.5 |
| 阶段桶 | library：`latency_components` 列（+ `stage_features_json` 快照）；legacy：`fingerprint_json.latency_components` | 值域 = `/stats/stages` 桶 key（见 FEATURE_SPEC.md） |
| 日志关键词 | library：`log_keywords` 列；legacy：`fingerprint_json.log_keywords` | 权重 1.0；须是现场观测到的原文短语 |
| `operation`（GET/SET） | library：`operation` 列 —— **服务端过滤字段**，同时是 1.5 权重的信号；legacy：`fingerprint_json.operation` | library 一提交即隔离 GET/SET；legacy 查询侧不构造该信号类型，写了也匹配不上，只能靠"分两次查询" |
| 时间形状 | `fault_shape`（library 列 / legacy `fingerprint_json.fault_shape`） | 无对应查询信号，只作正文标注 |
| 组件与版本 | library：`version_json`（kernel/os/urma/umq/ubsocket）+ `node_type`；legacy：`fingerprint_json.components` / `versions` | 无对应查询信号；作为可迁移性判据进正文 |
| 反证 | `counter_evidence_json`（两库同名） | 检索结果会带条数，便于"借力排除" |
| 准入与留痕 | library 独有：`status` / `revision` / `confirmed_by` / `confirmed_at` / `archive_reason` | 决定"这条经验是否被认可过"；检索默认只召回 `confirmed` |

**允许的扩展位置**：library 的信号由固定列派生（写入时同步进 `diag_case_library_signal`），
没有自由 signals 扩展位；legacy 的 `fingerprint_json.signals[]`（`{type, value, weight}`）
可承载自定义信号，但**只有查询侧也构造同名 type 时才会命中**，当前查询侧只支持上表的 9 种
type（含 `operation`）。不确定的自定义信号不要指望能匹配，写进正文更实在。

## 三、取值规范（两侧必须一致）

| 字段 | 规范 | 反例 |
|---|---|---|
| `status_codes` | 原始故障码字符串，`"1002"` | `"K_RPC_UNAVAILABLE"`（知识库里的名字不要混入） |
| `failure_mode_ids` | 故障模式 ID 原样，如 `kvcache_conn_fault_020_007` | 中文名 `"RPC 接收超时"` |
| `latency_components` | 桶 key，如 `urma`、`set_client` | 中文桶名 `"URMA 超时"` |
| `log_keywords` | 现场日志原文片段，保留大小写与下划线 | 意译、缩写 |
| IP / Pod / 集群 | 与 `/log_parse_result/options` 返回的取值逐字一致 | 自行规整的别名 |
| 匹配是大小写不敏感的 | 服务端与脚本都做 `strip().lower()` | 依赖大小写区分的写法 |

**已实测的口径漂移**：存量案例 `6ecb8748-5576-48b0-b47e-8ba4c242dc23` 的
`latency_components` 存的是展示名（`"ZMQ CLIENT_SEND"`、`"URMA"`），而检索侧提交的是
`/stats/stages` 桶 key（`set_client` / `set_worker` / `set_no_evidence`），导致 L2 信号
全部打空、`score_norm` 只有 0.73。因此：

- 新写入的案例必须用桶 key；library 的展示名写进 `root_cause_detail` 或
  `stage_features_json` 的桶 `note`，**不要污染 `latency_components`**；
  legacy 的展示名可以另存 `fingerprint_json.components`。
- 检索时 L2 **不能只看信号是否命中**：信号未命中但案例 `latency_components` 文本上属同族
  （如 `"URMA"` 对 `set_urma_timeout` / `urma`）时，按同族判定，并在输出中标注
  "取值口径不一致，按文本同族判定"。

## 四、写入侧最低要求（沉淀案例时）

### 4.1 确认闸门（`POST /{case_id}/confirm` 的硬条件，共 5 条）

闸门只判**「报告可信」**——是否有人看过报告并认可它，而不是「处置是否已验证」：

1. 案例处于 `draft` 态。
2. `evidence_json` 至少一条可复现锚点（`kind` + `ref`）。
3. `remediation_json` 至少一步分步处置（`step` + `action`）。
4. **至少一个可匹配信号**（`status_codes` / `failure_mode_ids` / IP / Pod / 主机 / 集群 /
   `latency_components` / `log_keywords`）；一条都没有的案例永远检索不到，`operation` 不计入。
5. `confirmed_by` 非空——这一条就是"人工点头"的留痕。

> **闸门不要求 `verification_json.observed_result`。** 报告出稿时处置尚未执行，此时拿不到实测结果；
> 把它当准入条件只会迫使 agent 臆造验证记录，比没有验证更坏。处置闭环是**正交维度**，
> 事后通过 `PATCH /diag_case_library/{case_id}` 补写。

### 4.2 内容物纪律（不全是闸门条件，但必须遵守）

1. `symptom_summary` / `root_cause_summary`（可加 `root_cause_detail`）必须能独立读懂，
   不依赖报告上下文。
2. `remediation_json` 的 `expected` 写清执行后应观察到什么，`risk` 写清步骤风险。
3. **`verification_json.observed_result` 只允许在处置执行 + 复测后填写，严禁在报告阶段臆造**；
   未执行就留空，并与 `closed_loop=false` 保持一致。
4. `counter_evidence_json` 如实记录已排除项——它是后来者最快的排除依据。
5. `scope_limits` 写清不适用场景，防止被跨域误套用。
6. `version_json` 只在有可靠来源时填，不得臆造。
7. `confidence` 必须反映验证程度：仅知识库解释支撑的不得给高置信度。
8. `source_log_ids` 填写来源日志 ID，便于回溯到原始样本。

**两阶段沉淀链路**（对话确认通道，不引入前端页面与审批流）：

1. 报告出稿 → agent 把报告路径与摘要交给用户；
2. 用户确认"报告 OK"→ `POST /diag_case_library` 建草稿 → `POST /{case_id}/confirm`
   （`confirmed_by` = 用户标识）→ 案例进入可检索集合；
3. 处置执行 + 复测后 → `PATCH /diag_case_library/{case_id}` 补 `verification_json`
   （`closed_loop` / `observed_result` / `verified_at`）。此时案例已是 `confirmed`：
   内容物冻结，该通道**只放行 `verification_json`**，`revision + 1` 留痕。

> 步骤 2 与 3 之间案例**已可被检索**，但 `closed_loop=false`：检索侧按"待验证处方"处理，
> `applicability` 上限 `adjust`（见 `case-matching/SKILL.md` 纪律 9）。闭环回填之所以能在
> 确认后进行，正是因为 PATCH 对 `confirmed` 放行了这一组事后证据字段；若发现报告阶段漏填
> 了内容物（症状/证据/处置/信号列），只能在确认前补齐——确认后内容物不再接受修改。

legacy（`diagnosis_case`）无确认闸门，上述条目全都不强制，这也是它只能当线索的原因。

## 五、语义通道接入位（后续 RAG）

`diag_case_library` 已预留 `search_text` / `embedding_model` / `embedded_at` 三列，
但**本轮不接向量库**：不生成向量、不做语义召回，`scripts/match_cases.py` 只走结构化检索。
接入时按下面的约定扩展，不需要改动现有结构化契约：

- **喂给 embedding 的文本** = 写入时生成的 `search_text`（`title` + `symptom_summary` +
  `root_cause_summary` + `root_cause_detail` + `operation` / `fault_shape` / `log_keywords` 原文），
  **不含** IP、主机、集群等纯标识类噪声——这些只做结构化过滤，不进正文。
- **过滤条件**仍用结构化头（`log_type` / `operation` / `fault_type` / `kb_id` / `status` /
  `status_codes` / `min_confidence`），先过滤再向量召回，避免跨域污染。
- **融合排序**：结构化 `score_norm` 与向量相似度分别归一后加权；两侧都必须保留
  "命中信号明细"，使 `applicability` 判定仍可解释。
- **回写按通道**：library 命中 → `POST /diag_case_library/{case_id}/hit`；
  legacy 命中 → `POST /diagnosis_case/{case_id}/hit`。端点不能串，否则热度记到别的表。

## 六、本契约不承诺的事

- 不改动 `POST /diagnosis_case/search` 的既有行为与打分（只增不改约束下，检索侧不做后端改造）。
- **跨知识库召回已支持**（library 通道）：`kb_id` 可空，检索范围 = 全部 `confirmed` 案例；
  legacy 通道仍要求 `kb_id` 必填且服务端校验存在性，检索范围 = 本次知识库 + 全局案例。
- 版本不参与打分：library 已有 `version_json` 承载，但查询侧不构造版本信号，
  版本只能作为 `applicability` 的可迁移性判据。