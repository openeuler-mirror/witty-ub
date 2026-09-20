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
| POST | `/diag_case_library/{case_id}/confirm` | `confirm_diag_case` | `draft→confirmed`，校验确认闸门 |
| POST | `/diag_case_library/{case_id}/archive` | `archive_diag_case` | `draft\|confirmed→archived` |
| POST | `/diag_case_library/search` | `search_diag_cases` | 默认只返回 `confirmed` |
| POST | `/diag_case_library/{case_id}/hit` | `hit_diag_case` | `hit_count + 1` |

### 4.1 写入（草稿）

必填：`log_type`、`source`、`title`、`symptom_summary`、`root_cause_summary`。
`source` 为 `community` / `online` 时 `source_url` 必填（pydantic `model_validator`）。
`search_text` 与 `case_no` 由服务端生成，不接受外部传入。
`kb_id` 非空时才走 `ResourceIdService` 存在性校验；为空表示全局案例。

### 4.2 确认闸门（`confirm`）

`confirm` 必须校验下列条件，任一不满足返回业务异常并说明缺什么：

1. 当前 `status == draft`（否则 409 语义的业务异常）。
2. `evidence_json` 非空。
3. `remediation_json` 非空。
4. `verification_json` 存在且 `observed_result` 非空。
5. 至少一个可匹配信号（`status_codes` / `failure_mode_ids` / `latency_components` /
   `log_keywords` / `hosts` / `pods` / IP / `cluster_name` 至少有一项非空），否则该案例永远检索不到。
6. `confirmed_by` 非空。

通过后置 `status=confirmed`、`confirmed_by/at`、`revision += 1`、`confidence` 取请求值（缺省沿用草稿值）。

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
- 确认闸门：缺 evidence / 缺 remediation / 缺 verification.observed_result / 无可匹配信号 /
  缺 `confirmed_by` 逐项被拒。
- 检索：默认只返回 `confirmed`（草稿与归档不出现在结果里）；`include_status` 显式放开；
  `operation` 过滤生效（GET 查询不返回 SET 案例）；`kb_id` 为空时能召回其他知识库案例；
  `min_confidence` 生效；`score_norm` 在 0~1 且单调随命中增加。
- 写入：`source=online` 缺 `source_url` 返回 422；`case_no` 唯一且递增；`search_text` 自动生成。
- 边界：不存在 `case_id` → 404 语义；分页越界返回空列表但 `total` 正确。

### 8.2 契约测试（`test/test_diagnosis_api_contract.py`）

`EXPECTED_DIAGNOSIS_OPERATIONS` 追加 6 个新 operationId（见 §4 表格），并断言既有
`/diagnosis_case*` 条目**保持不变**。

### 8.3 node48 真实数据验收

1. 用 jingpai kb 的 SET 通断真实特征建一条草稿（`latency_components` 用桶 key `set_client` /
   `set_worker`，`log_keywords` 取现场原文），确认后检索，检查 `score_norm` 与命中信号级别。
2. 建一条 `operation=GET` 草稿，验证 GET 查询不召回 SET 案例。
3. 建一条 `kb_id` 为空的全局案例，验证跨库召回成立（这是既有接口做不到的）。
4. SQL 复核：`diag_case_library_signal` 的信号值与主表特征一致，无展示名混入。
5. 回归：`/diagnosis_case/search` 与 `/diagnosis_case/{id}` 响应与改造前逐字段一致。

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

| 批次 | 内容 |
|---|---|
| 1 | 本设计文档冻结 |
| 2 | 枚举 + ORM + schemas + manager + service + router + 路由注册 + resource_id key + 索引 |
| 3 | 单测 + 契约测试 + node48 真实数据验收，回填 §8.4 |
| 4 | `case-matching` skill 调整：DB 通道降级、输出标注"来源=未确认"、指向新库 |