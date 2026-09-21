# 超节点诊断案例库（/diag_case_library）设计

## 1. 背景与动机

现有 `diagnosis_case` 表是"随手可写"的案例池：`POST /diagnosis_case` 无准入校验，表里没有
状态字段，内容物只有 4 个文本字段 + 4 个 JSONB；检索 `POST /diagnosis_case/search` 的
`kb_id` 必填且服务端校验知识库存在，无法跨库召回。

用它做"案例检索"会有三个硬伤：

1. **检索结果不保证是我们确认过的案例**——任何人都能写入，无审核留痕。
2. **内容物不足**——没有验证闭环、没有分步处置、没有版本、没有可供 embedding 的正文。
3. **检索范围被知识库锁死**——跨库案例永远召不到，而语义检索天然要跨库。

因此新建一套**独立的**超节点诊断案例库：只沉淀人工确认过的案例，检索默认只返回已确认案例，
并为后续 RAG 向量通道预留字段位。

## 2. 目标与非目标

### 目标

- 表级闸门：`draft → confirmed → archived` 状态机，`confirmed_by` / `confirmed_at` 留痕。
- 内容物加厚：结构化证据、根因摘要+机理、分步处置、**验证闭环**、案例关系、embedding 正文。
- 检索跨库：`kb_id` 降级为**可选来源标注**，默认只返回 `confirmed`。
- `operation`（GET / SET）成为可过滤字段，GET 与 SET 不再依赖"分两次查询"隔离。
- 补上 `FEATURE_SPEC.md` 中标注的 L4 版本缺口（`version_json`）。

### 非目标

- **不改动** `diagnosis_case` 表、`/diagnosis_case*` 端点、`DiagnosisCasePGManager` 的任何行为。
- 本轮不接向量库：只落 `search_text` 与 `embedding_model` / `embedded_at` 预留位，检索走结构化通道。
- 不做案例自动沉淀：写入由人工或 agent 显式调用 API 完成。
- 不做案例间自动聚类 / 去重。

## 3. 数据模型

### 3.1 枚举

新增 `latency/ENUM/case_library.py`：

| 枚举 | 取值 |
|---|---|
| `DiagCaseStatus` | `draft` / `confirmed` / `archived` |
| `DiagCaseSource` | `internal` / `community` / `online` |
| `DiagCaseOperation` | `GET` / `SET` / `N/A` |

`log_type` 复用现有 `DiagnosisConfigLogType`（`KVCache` / `UBSocket`），与 `log_file.log_type` 同口径，
**不新造一套**。

### 3.2 主表 `diag_case_library`

| 分组 | 字段 | 类型 | 说明 |
|---|---|---|---|
| 身份 | `id` | String PK | uuid |
| | `case_no` | String unique | 可读编号 `UB-CASE-000123`，写入时生成 |
| 状态机 | `status` | String | `DiagCaseStatus`，默认 `draft` |
| | `revision` | Integer | 案例修订号，每次复核 +1 |
| | `created_by` / `confirmed_by` / `archived_by` | String | 操作人（或 agent）标识 |
| | `confirmed_at` / `archived_at` | TIMESTAMP | 关卡留痕 |
| | `archive_reason` | Text | 归档原因 |
| 来源 | `source` | String | `DiagCaseSource` |
| | `source_url` | Text | `community` / `online` 必填 |
| | `title` | String | 案例标题 |
| 归属 | `log_type` | String | `KVCache` / `UBSocket` |
| | `kb_id` / `kb_name` | String | **可空**，仅作来源标注 |
| | `cluster_name` | String | |
| | `hosts` / `pods` / `src_ips` / `dst_ips` | JSONB | L0 拓扑数组 |
| | `node_type` | String | 超节点形态，可空 |
| | `version_json` | JSONB | `{kernel, os, urma, umq, ubsocket}`，补 L4 缺口 |
| | `scope_limits` | Text | 不适用场景，防误套用 |
| 特征 | `operation` | String | `GET` / `SET` / `N/A` |
| | `fault_type` | String | `latency` / `connectivity` / `mixed` / `unknown` |
| | `status_codes` | JSONB | 权重 3.0 |
| | `failure_mode_ids` | JSONB | 权重 3.0 |
| | `latency_components` | JSONB | 桶 key，权重 1.5 |
| | `log_keywords` | JSONB | 权重 1.0 |
| | `stage_features_json` | JSONB | L2 桶分布快照 |
| | `fault_shape` | String | 突发单点 / 短时簇发 / 持续劣化 |
| | `time_window_json` | JSONB | `{start, end}` |
| | `confidence` | Float | 结论验证强度 0~1，支持 `min_confidence` 过滤 |
| 内容物 | `symptom_summary` | Text | 现象摘要，独立可读 |
| | `evidence_json` | JSONB | 证据锚点 |
| | `root_cause_summary` | Text | 一句话根因 |
| | `root_cause_detail` | Text | 机理长文 |
| | `counter_evidence_json` | JSONB | 已排除项 |
| | `remediation_json` | JSONB | 分步处置 |
| | `verification_json` | JSONB | 验证闭环 |
| | `relations_json` | JSONB | 关联案例 |
| RAG 预留 | `search_text` | Text | 写入时按 `CASE_FEATURE_CONTRACT.md` 规则拼接 |
| | `embedding_model` / `embedded_at` | String / TIMESTAMP | 本轮不写值 |
| 元信息 | `source_log_ids` | JSONB | 来源日志 ID |
| | `hit_count` | Integer | 采纳次数 |
| | `existed_status` | Boolean | 软删开关，默认 TRUE |
| | `created_at` / `updated_at` | TIMESTAMP | |

### 3.3 信号表 `diag_case_library_signal`

与现有 `diagnosis_case_signal` 同构：`(case_id, signal_type, signal_value)` 复合主键 + `weight`。
由主表特征派生，`operation` 之外的字段与现有 `SIGNAL_FIELD_MAP` 口径一致：

| signal_type | 来源字段 | 权重 |
|---|---|---|
| `status_code` | `status_codes[]` | 3.0 |
| `failure_mode_id` | `failure_mode_ids[]` | 3.0 |
| `src_ip` / `dst_ip` | `src_ips[]` / `dst_ips[]` | 1.5 |
| `host` / `pod` / `cluster` | `hosts[]` / `pods[]` / `cluster_name` | 1.5 |
| `latency_component` | `latency_components[]` | 1.5 |
| `log_keyword` | `log_keywords[]` | 1.0 |
| `operation` | `operation` | 1.5 |

### 3.4 结构化 JSON 契约（强约束，pydantic 模型校验）

```
stage_features_json
{ "operation": "SET",
  "buckets": [ { "key", "trace_cnt", "success_cnt", "fail_cnt",
                 "p50_ms", "p90_ms", "max_ms", "metric_name", "note" } ],
  "sample_cnt": 40, "truncated": false }

evidence_json[]
{ "kind": "api" | "trace" | "log" | "sql",
  "ref": "POST /stats/stages" | "trace_id=..." | "/path/file.log:1234",
  "params": {...},        // kind=api 时可空
  "excerpt": "原文片段",
  "note": "这条证据说明什么" }

remediation_json[]
{ "step": 1, "action": "...", "expected": "执行后应观察到...", "risk": "..." }

verification_json
{ "method": "...", "observed_result": "...", "closed_loop": true,
  "verified_at": "YYYY-MM-DD HH:MM:SS", "notes": "..." }

relations_json[]
{ "case_no": "UB-CASE-000012",
  "relation": "same_fault" | "upstream" | "downstream" | "false_positive",
  "note": "..." }

version_json
{ "kernel": "...", "os": "...", "urma": "...", "umq": "...", "ubsocket": "..." }

time_window_json
{ "start": "YYYY-MM-DD HH:MM:SS", "end": "YYYY-MM-DD HH:MM:SS" }
```

### 3.5 索引

在 `database/init.py::create_manual_indexes` 追加（沿用 `IF NOT EXISTS` 风格）：

```sql
CREATE UNIQUE INDEX IF NOT EXISTS ux_dcl_case_no ON diag_case_library (case_no);
CREATE INDEX IF NOT EXISTS ix_dcl_status ON diag_case_library (status) WHERE existed_status = TRUE;
CREATE INDEX IF NOT EXISTS ix_dcl_op_ft ON diag_case_library (operation, fault_type) WHERE existed_status = TRUE;
CREATE INDEX IF NOT EXISTS ix_dcl_signal_lookup ON diag_case_library_signal (signal_type, signal_value);
```

## 4. 端点规格

统一前缀 `/diag_case_library`，响应沿用 `ResponseBase`（`code` / `message` / `result`）。

| 方法 | 路径 | operationId | 说明 |
|---|---|---|---|
| POST | `/diag_case_library` | `create_diag_case_draft` | 建草稿，`status=draft`，返回 `case_no` |
| GET | `/diag_case_library/{case_id}` | `get_diag_case` | 详情 |
| PATCH | `/diag_case_library/{case_id}` | `update_diag_case` | 局部更新：`draft` 改内容物；`confirmed` 只放行 `verification_json`；`archived` 拒绝 |
| POST | `/diag_case_library/{case_id}/confirm` | `confirm_diag_case` | `draft→confirmed`，校验确认闸门 |
| POST | `/diag_case_library/{case_id}/archive` | `archive_diag_case` | `draft\|confirmed→archived` |
| POST | `/diag_case_library/search` | `search_diag_cases` | 默认只返回 `confirmed` |
| POST | `/diag_case_library/{case_id}/hit` | `hit_diag_case` | `hit_count + 1` |

### 4.1 写入（草稿）

必填：`log_type`、`source`、`title`、`symptom_summary`、`root_cause_summary`。
`source` 为 `community` / `online` 时 `source_url` 必填（pydantic `model_validator`）。
`search_text` 与 `case_no` 由服务端生成，不接受外部传入。
`kb_id` 非空时才走 `ResourceIdService` 存在性校验；为空表示全局案例。

### 4.2 确认闸门（`confirm`）—— 只判「报告可信」

**设计前提**：`confirmed` 的语义是**「人看过报告并认可其可信度」**，不是「处置已验证」。
处置是否真正闭环是**另一个正交维度**（见 §4.5），不参与本闸门。

`confirm` 必须校验下列条件，任一不满足返回业务异常并说明缺什么：

1. 当前 `status == draft`（否则 409 语义的业务异常）。
2. `evidence_json` 非空（≥1 条可复现锚点）。
3. `remediation_json` 非空（≥1 步分步处置）。
4. 至少一个可匹配信号（`status_codes` / `failure_mode_ids` / `latency_components` /
   `log_keywords` / `hosts` / `pods` / IP / `cluster_name` 至少有一项非空），否则该案例永远检索不到。
5. `confirmed_by` 非空 —— **这一条即「人工点头」的留痕**。

通过后置 `status=confirmed`、`confirmed_by/at`、`revision += 1`、`confidence` 取请求值（缺省沿用草稿值）。

> **闸门不要求 `verification_json.observed_result`**（早期版本曾把它列为硬条件，现已移出）。
> 报告出稿时处置尚未执行，此时不可能有实测结果；把实测结果作为准入条件只会迫使 agent
> 臆造验证记录，比没有验证更坏。验证的定位见 §4.5。

### 4.3 检索

请求字段（全部可选，除分页外）：

`operation`、`log_type`、`fault_type`、`kb_id`、`status_codes[]`、`failure_mode_ids[]`、
`src_ips[]`、`dst_ips[]`、`hosts[]`、`pods[]`、`clusters[]`、`latency_components[]`、
`log_keywords[]`、`min_confidence`、`include_status[]`（默认 `["confirmed"]`）、`page_cnt`、`page_num`。

- `kb_id` 为空 → 不过滤，实现跨库召回；非空 → 只做来源过滤（仍附带全局案例）。
- 打分沿用现有口径：`min(案例权重, 查询权重)` 求和得 `match_score`（未归一化），
  再除以查询侧权重和得 `score_norm`（0~1，跨查询可比）。
- 排序：`score_norm` → `confidence` → `hit_count` → `updated_at`。
- 零信号查询时返回该状态下的全部案例，`match_score = score_norm = 0`。

响应 `matches[]`：`{case, match_score, score_norm, matched_signals[]}`。

### 4.4 案例更新（`PATCH /diag_case_library/{case_id}`）

两阶段沉淀必需的通道：**报告出稿 → 人工确认 → 处置执行 → 复测补 `verification_json`**。
没有它，草稿建完后无法追加验证信息，闭环链路在接口层面走不通。

请求体与 §4.1 建草稿同字段集，**全部可选**（局部更新，未传字段不动；显式传空数组即清空该字段）。
接受的字段按当前状态分档：

| 当前状态 | 接受的字段 | 落库行为 | 拒绝 |
|---|---|---|---|
| `draft` | 全部内容物列（§4.1 字段集） | 写内容物列，**重算 `search_text` 与 `diag_case_library_signal` 行** | — |
| `confirmed` | 仅 `verification_json` | 只写这一列，**不重算** `search_text` 与信号行 | 其余字段返回 409 语义业务异常 |
| `archived` | —（无） | — | 任何字段均返回 409 语义业务异常 |

- 每次成功更新 `revision += 1` 留痕。
- `confirmed` 放行 `verification_json` 的设计理由：确认闸门（§4.2）只判报告可信，处置闭环是
  **事后**证据，其填写时点必然晚于确认（§4.5 链路步 3）。若 PATCH 只允许 `draft`，
  闭环维度永远无法落库。
- **内容物冻结**：`confirmed` 下症状 / 根因 / 证据 / 处置 / 信号列都不接受修改，
  防止「确认过的内容被悄悄改写」破坏可信度。
- **信号行不因事后证据而变**：`verification_json` 不参与检索信号，重建信号行纯属浪费且会
  放大并发面，故该通道只写一列。
- `case_no` / `status` / `revision` / `created_by` / `confirmed_by` / `confirmed_at` /
  `archived_*` / `hit_count` / `search_text` 等元信息字段**不在可更新集合内**（`UPDATABLE_COLUMNS`
  有单测断言其与模型字段互补）。
- 空请求体（未传任何字段）返回 400 语义业务异常——避免无意义的 `revision += 1`。

### 4.5 验证闭环（正交维度，不参与闸门）

| 维度 | 字段 | 谁填 | 何时 | 作用 |
|---|---|---|---|---|
| 报告可信确认 | `status: draft→confirmed` + `confirmed_by/at` | **人**（看完报告点头） | 报告出稿后 | 决定能否被检索召回 |
| 处置闭环验证 | `verification_json.closed_loop` / `verified_at` / `observed_result` | 人或 agent，**事后** | 处置执行 + 复测后 | 决定是否为「已被证实」的黄金案例 |

纪律（同步写入 `case-matching` 与 `diagnostic-report-generation` skill）：

- `observed_result` **只允许在处置执行后填写**，严禁在报告阶段臆造。
- 回填通道固定为 §4.4 的 `PATCH /diag_case_library/{case_id}`，**在 `confirmed` 态进行**
  （内容物已冻结，只放行 `verification_json`）。填写时点必然晚于确认，故 PATCH 不能对
  `confirmed` 关门，否则本维度永远落不了库。
- 检索侧按 `closed_loop` 区分：`true` 标注「已验证」并排序加权；`false` 或字段缺失均视为
  「待验证处方」，`applicability` **上限为 `adjust`**，不得给 `direct`。
- 人工确认的交互通道本轮走**对话确认**（agent 给出报告路径与摘要 → 用户在对话里点头 →
  agent 调 `confirm`），不引入前端页面与审批流。

## 5. 与现有 `/diagnosis_case` 的关系

**只增不改**。两套体系并存，互不调用：

| | `diagnosis_case`（既有） | `diag_case_library`（新增） |
|---|---|---|
| 准入 | 无 | `draft → confirmed` 人工闸门 |
| 检索默认范围 | 全部 | 仅 `confirmed` |
| `kb_id` | 必填 | 可选 |
| `operation` 过滤 | 无 | 有 |
| 验证闭环 / 处置步骤 | 无 | 有 |
| embedding 预留 | 无 | 有 |

唯一被触碰的既有文件只有两处，且均为**新增一行/一个 key**：

- `access/fastapi_server.py`：`app.include_router(diag_case_library.router)`。
- `database/managers/resource_id.py`：`_RESOURCE_COLUMNS` 加 `"diag_case"`，
  `services/resource_id.py::_RESOURCE_NAMES` 加同名展示名。
- `database/init.py::create_manual_indexes`：追加 §3.5 的索引 DDL。

## 6. 错误处理与边界

| 场景 | 行为 |
|---|---|
| `case_id` 不存在 / `existed_status=False` | `NotFoundBizException(resource="诊断案例")` |
| `confirm` 时状态非 `draft` | 业务异常，提示当前状态 |
| `PATCH` 时状态为 `archived` | 业务异常：已归档，内容与验证记录均冻结 |
| `PATCH` 内容物但状态为 `confirmed` | 业务异常：内容物已冻结，只开放 `verification_json`（提示被拒字段名） |
| `PATCH` 请求体为空 | 业务异常：至少需要一个待更新字段 |
| `archive` 已归档案例 | 幂等返回当前案例 |
| `kb_id` 非空但知识库不存在 | `NotFoundBizException`（复用 ResourceIdService） |
| `source=online` 缺 `source_url` | 422（pydantic 校验） |
| 分页越界 | 返回空 `matches`，`total` 仍为真实命中数 |
| 信号值大小写 | 服务端 `strip().lower()`，与既有 `_normalize_signal_value` 一致 |

## 7. RAG 预留位

- `search_text`：写入时按 `CASE_FEATURE_CONTRACT.md` §五 规则拼接
  （`title` + `symptom_summary` + `root_cause_summary/detail` + `operation` + `fault_shape` +
  `components` + `versions` + `log_keywords` 原文），**不含** IP / 集群等纯标识噪声。
- `embedding_model` / `embedded_at`：本轮留空，接入向量通道时回填。
- 向量通道接入后，过滤仍用结构化头（`status=confirmed` + `log_type` + `fault_type`），
  先过滤再召回；结构化 `score_norm` 与向量相似度分别归一后加权融合。

## 8. 测试与验收

### 8.1 单测（`test/test_diag_case_library_api.py`）

- 状态机：`draft → confirmed → archived` 全路径；非法迁移（`confirmed → confirm`、
  `archived → confirm`）被拒。
- 确认闸门：缺 evidence / 缺 remediation / 无可匹配信号 / 缺 `confirmed_by` 逐项被拒；
  `verification_json` 为空**不**被拒（§4.2 只判报告可信）。
- 案例更新（§4.4 / §4.5）：局部更新只改传入字段（显式传空数组才算清空）；`revision + 1`；
  元信息（`case_no` / `status` / `revision` / 留痕 / 计数）不可改且不在请求模型内；
  `draft` 态重建信号行、`confirmed` 态只写 `verification_json` 且不动 `search_text` 与信号行；
  `confirmed` 下改内容物被拒（提示字段名）；`archived` 下连 `verification_json` 也被拒；
  空请求体被拒；`source_url` 按合并结果判定；并发窗口下非 draft 行不被改写（返回 False）；
  `VERIFICATION_COLUMNS ⊆ UPDATABLE_COLUMNS`。
- 检索：默认只返回 `confirmed`（草稿与归档不出现在结果里）；`include_status` 显式放开；
  `operation` 过滤生效（GET 查询不返回 SET 案例）；`kb_id` 为空时能召回其他知识库案例；
  `min_confidence` 生效；`score_norm` 在 0~1 且单调随命中增加。
- 写入：`source=online` 缺 `source_url` 返回 422；`case_no` 唯一且递增；`search_text` 自动生成。
- 边界：不存在 `case_id` → 404 语义；分页越界返回空列表但 `total` 正确。

### 8.2 契约测试（`test/test_diagnosis_api_contract.py`）

`EXPECTED_DIAGNOSIS_OPERATIONS` 追加 7 个新 operationId（见 §4 表格，含 `PATCH`），并断言既有
`/diagnosis_case*` 条目**保持不变**。

### 8.3 node48 真实数据验收

1. 用 jingpai kb 的 SET 通断真实特征建一条草稿（`latency_components` 用桶 key `set_client` /
   `set_worker`，`log_keywords` 取现场原文），确认后检索，检查 `score_norm` 与命中信号级别。
2. 建一条 `operation=GET` 草稿，验证 GET 查询不召回 SET 案例。
3. 建一条 `kb_id` 为空的全局案例，验证跨库召回成立（这是既有接口做不到的）。
4. SQL 复核：`diag_case_library_signal` 的信号值与主表特征一致，无展示名混入。
5. 回归：`/diagnosis_case/search` 与 `/diagnosis_case/{id}` 响应与改造前逐字段一致。
6. 两阶段沉淀链路：报告阶段建草稿 → **不带 `verification_json`** 直接 `confirm`（闸门应放行，
   案例立即进入可检索集合）→ 处置执行 + 复测后 `PATCH` 补 `verification_json`（`confirmed` 态
   放行、只写一列、`revision + 1`、`search_text` 与信号行不变）→ 检索仍命中且 `closed_loop=true`；
   同时验证 `confirmed` 态改内容物被拒、`archived` 态连 `verification_json` 也被拒。

### 8.4 验收记录

**单测**（2026-09-20）：

```
$ cd src/plugins && PYTHONPATH=$PWD python3 -m pytest \
    latency/test/test_diag_case_library_api.py latency/test/test_diagnosis_case.py \
    latency/test/test_diagnosis_api_contract.py latency/test/test_resource_id_validation.py \
    latency/test/test_request_validation.py -q
78 passed
```

新增 24 个用例覆盖信号权重/归一化、`search_text` 噪声剔除、确认闸门 6 项、状态机全路径与非法迁移、
检索默认范围、`operation` 隔离、跨库召回、`min_confidence`、分页越界、来源链接校验。

**批次 5 单测**（2026-09-21，同一命令）：

```
89 passed
```

用例 36 个（+12）：闸门去掉 `observed_result` 硬条件（`verification` 为空 / 只有 `method` 均可确认）、
更新的局部语义与显式清空、`revision + 1`、`confirmed` 态只放行 `verification_json` 且走独立通道、
`confirmed` 下改内容物被拒（提示字段名）、`archived` 下连 `verification_json` 也被拒、空请求体被拒、
`source_url` 按合并结果判定、更新请求字段集 = 建草稿字段集 − `created_by`、
`UPDATABLE_COLUMNS` 与模型字段互补且 `VERIFICATION_COLUMNS ⊆ UPDATABLE_COLUMNS`、
draft 通道信号行重建（DELETE + INSERT）与 UPDATE 语句的 SET 列不含元信息、
confirmed 通道只写一列且不重建信号、并发未命中不重建信号。

**批次 5 node48 真实 PG 验收**（2026-09-21，库 `witty-ub` @ 127.0.0.1:15432，kb jingpai）：

| # | 检查项 | 实测结果 |
|---|---|---|
| 1 | 建草稿 | `case_no=UB-CASE-000009`，`status=draft` |
| 2 | 闸门放宽 | `verification_json=None` 时 `confirm` 通过：`status=confirmed`、`revision=1` |
| 3 | 确认即可检索 | 确认后同一查询命中，`score_norm=1.0`，`verification=None`（「待验证处方」） |
| 4 | confirmed 改内容物 | `ConflictBizException`：confirmed 案例只开放 `verification_json`，不接受修改：title |
| 5 | confirmed 补闭环 | `verification_json` 放行：`revision=2`、`closed_loop=true`、`observed=SET P90 从 12ms 回落到 1.2ms`、`title` 未变 |
| 6 | 事后证据不动检索态 | `search_text_same=True`、信号行前后完全一致 |
| 7 | 闭环后可检索 | 同一查询仍命中，返回 `closed_loop=true` |
| 8 | draft 态内容 PATCH | 只传 `verification_json` + `log_keywords`：`title` 未变、`revision=1`、`closed_loop=true` |
| 9 | `search_text` 重算 | 80 → 95 字符，新关键词 `urma link down` 已入正文 |
| 10 | 信号行重建 | 5 条信号全部为桶 key / 真实码：`latency_component=set_client`、`log_keyword` ×2、`operation=set`、`status_code=1004`，无 `None` 污染 |
| 11 | 草稿不可检索 | PATCH 后未确认时，同一查询不返回该草稿（符合 §4.3 默认只返回 confirmed） |
| 12 | 显式清空 | `status_codes=[]` → `status_code` 信号 0 条 |
| 13 | archived 全冻结 | 归档后 `PATCH verification_json` 被拒：诊断案例已归档，不可修改 |
| 14 | 清理 | 临时行与信号行已删除 |

**node48 真实 PG 验收**（2026-09-20，库 `witty-ub` @ 127.0.0.1:15432，真实 kb
`3533f5b6-7a8f-48a8-9d84-7007cc9a0663`（jingpai）与 `641f11a3-…`（node48-align））：

| # | 检查项 | 实测结果 |
|---|---|---|
| 1 | 增量 DDL（表 + 序列 + 索引） | 通过，`Base.metadata.create_all` + `DIAG_CASE_LIBRARY_DDL` |
| 2 | 真实特征来源 | `status_codes=1002/1001`、`failure_mode_ids=kvcache_conn_fault_020/_020_007`（取自现场 `diagnosis_case`） |
| 3 | 建草稿 | `case_no=UB-CASE-000001`（`nextval` 生成），`status=draft`、`revision=0`，`search_text` 自动生成 228 字符，`version_json` 落库 `{kernel:5.10, urma:2.4}` |
| 4 | 确认闸门 | 空 `confirmed_by` → `BadRequestBizException`；正常确认 → `status=confirmed`、`revision=1`、`confidence=0.9`；二次确认 → `ConflictBizException` |
| 5 | 检索（SET 查询） | `total=1`，`score_norm=1.0`，命中 5 个信号 |
| 6 | `operation` 隔离 | GET 查询 `total=0`（SET 案例不被召回） |
| 7 | 跨库召回 | **不传 `kb_id`** 时召回到属于其他知识库的案例（既有接口做不到） |
| 8 | 零信号查询 | 返回全部 `confirmed` 案例，`score_norm=0.0` |
| 9 | hit / archive | `hit_count` 1；归档后查询 `total=0` |
| 10 | 信号表口径 | 10 条信号，全部为桶 key（`set_client`/`set_worker`）+ 真实故障码/模式，无展示名、无 `None` 污染 |
| 11 | 回归 | `diagnosis_case` 行数不变（1），既有端点与用例全绿 |

验收用临时行已清理，新增表 / 序列 / 索引保留。

**HTTP 层端到端**（2026-09-20，FastAPI 路由挂载 + `TestClient`，引擎指向同一真实库）：

| 调用 | 结果 |
|---|---|
| `POST /diag_case_library` | 200，`case_no=UB-CASE-000003` |
| `POST /search`（草稿期） | `total=0`（草稿不可检索） |
| `POST /search {operation:GET}`（草稿期） | `total=0` |
| `POST /{id}/confirm` | 200，`status=confirmed` |
| 二次 `confirm` | `ConflictBizException`（状态非 draft） |
| `POST /search`（确认后） | `total=1`，`score_norm=1.0`，响应字段严格为 `case/match_score/matched_signals/score_norm` |
| `GET /{id}` | 200，`case_no=UB-CASE-000003` |
| `POST /{id}/hit` | `hit_count=1` |
| `POST /{id}/archive` | `status=archived`，归档后 `total=0` |
| `GET /{不存在id}` | `NotFoundBizException: 诊断案例不存在` |
| `POST` with `source=online` 缺 `source_url` | 422（pydantic 拦截） |
| `POST` with 不存在的 `kb_id` | `NotFoundBizException: 知识库不存在` |

**case-matching skill 通道切换验收**（`scripts/match_cases.py`）：

- `--source library`（默认）指向 `/diag_case_library/search`；`kb_id` 可省略，`operation` 走服务端过滤，
  本地归一化分母把 `operation`（1.5）计入，与服务端口径一致。
- `--source legacy` 指向 `/diagnosis_case/search`，`kb_id` 缺失即报错退出码 2，输出打印
  `警告: 来源=diagnosis_case（未经人工确认）`；`--json` 落盘含 `source` / `source_confirmed` / `source_label`。
- 实测 legacy 通道对现场 jingpai 特征仍可命中既有案例（`score_norm=0.7647`），验证降级通道未坏。
- 新库端点尚未部署进运行中的 witty-ub 容器，故容器内 `--source library` 目前返回 404；
  重建镜像后即生效（表与索引已就绪）。

## 9. 实施批次

| 批次 | 内容 | 状态 |
|---|---|---|
| 1 | 本设计文档冻结 | ✅ |
| 2 | 枚举 + ORM + schemas + manager + service + router + 路由注册 + resource_id key + 索引 | ✅ |
| 3 | 单测 + 契约测试 + node48 真实数据验收，回填 §8.4 | ✅ |
| 4 | `case-matching` skill 调整：DB 通道降级、输出标注"来源=未确认"、指向新库 | ✅ |
| 5 | 闸门改为只判「报告可信」+ 新增 `PATCH` 更新端点（`draft` 改内容物 / `confirmed` 只回填 `verification_json` / `archived` 拒绝）+ 单测（§4.4 / §4.5） | ✅ |
| 6 | 案例生成侧对齐：`diagnostic-report-generation` 的桥接数据改为新库草稿契约（§10） | 进行中 |
| 7 | 重建镜像部署（当前容器无新端点） | 待办 |

（批次 2/3 提交：`06895217` / `92c43f95`；批次 4：`aa4e9ac4`；批次 5 见 §8.4 验收记录。）

## 10. 案例生成侧对齐（批次 6）

`diagnostic-report-generation` 目前产出的 `diagnosis_case_bridge` 仍**一一映射旧表**
`DiagnosisCaseModel`（`root_cause` / `recommendation` / `fingerprint_json` /
`evidence_refs_json`），**过不了 §4.2 闸门**——没有 `evidence_json`（带 `kind` 的锚点）、
没有 `remediation_json`（分步处置）。对齐要求：

| 旧字段 | 新库字段 | 说明 |
|---|---|---|
| `root_cause`（拼接长文） | `root_cause_summary` + `root_cause_detail` | 一句话根因与机理长文拆开 |
| `recommendation`（自由文本） | `remediation_json[]` | 必须拆成 `{step, action, expected, risk}` 分步 |
| `evidence_refs_json[]` | `evidence_json[]` | 补 `kind`（api/trace/log/sql）与 `params` |
| `fingerprint_json.*` | 各独立信号列 | `hosts` / `pods` / `src_ips` / `dst_ips` / `cluster_name` / `latency_components` / `log_keywords` |
| —（无） | `operation` / `stage_features_json` | 由 `/stats/stages` 快照提供 |
| —（无） | `scope_limits` | 报告须声明不适用场景，防跨域误套用 |
| —（无） | `version_json` | 有可靠来源才填，不得臆造 |
| —（无） | `verification_json` | **报告阶段留空**，事后经 §4.4 `PATCH` 补 |
| `confidence` | `confidence` | 沿用（`≥0` 且 `≤1`） |

沉淀链路（对话确认通道）：

1. 诊断完成 → 渲染报告 → agent 把报告路径与摘要交给用户
2. 用户确认「报告 OK」→ agent 调 `POST /diag_case_library` 建草稿 → 再调 `/{case_id}/confirm`
   （`confirmed_by` = 用户标识），案例进入可检索集合
3. 处置执行 + 复测后 → 调 `PATCH /diag_case_library/{case_id}` 补 `verification_json`
   （`closed_loop` / `observed_result` / `verified_at`）。此时案例已是 `confirmed`，
   内容物冻结、该通道只放行 `verification_json`（§4.4），`revision + 1` 留痕。

> 步骤 2 与 3 之间案例**已可被检索**，但 `closed_loop=false`，检索侧须标注「待验证处方」，
> `applicability` 上限 `adjust`。