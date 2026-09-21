# 诊断报告 JSON Schema 参考

本文件为 `diagnostic-report-generation` Skill 提供字段级契约：

- §1 / §2 为**旧版报告正文结构**，仅供追溯；报告正文的权威契约现由
  `scripts/render_report.py --spec <板块>` 与 `references/REPORT_BLOCKS.md` 承载。
- §3 为**案例沉淀契约**，已对齐超节点诊断案例库
  （`latency/schemas/diag_case_library.py::CreateDiagCaseDraftRequest`）。

---

## 1. 顶层结构

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "Witty-UB Diagnostic Report",
  "type": "object",
  "required": ["report", "case_draft"],
  "properties": {
    "report": { "$ref": "#/$defs/ReportBody" },
    "case_draft": { "$ref": "#/$defs/CaseDraft" }
  }
}
```

---

## 2. ReportBody（八章节，旧版，仅追溯）

> 报告正文契约已迁至 `render_report.py --spec` + `REPORT_BLOCKS.md`（九板块）；
> 本节保留旧版章节字段供历史报告追溯，**新报告不要按本节组织数据**。

### 2.0 chapter_0_experience_refs（经验库引用标注，强制章节）

| 字段 | 类型 | Required | 约束 |
|------|------|----------|------|
| `experience_refs` | array | ✅ | 可为空数组（无引用时）；不得为 null |
| `experience_refs[*].experience_id` | string | ✅ | UUID；全局唯一 |
| `experience_refs[*].experience_type` | string | ✅ | 枚举: `SKILL`, `WIKI` |
| `experience_refs[*].name` | string | ✅ | 非空 |
| `experience_refs[*].source_path` | string | ✅ | 非空；格式 `data/{skill_hub|wiki_hub}/...` |
| `experience_refs[*].keywords_matched` | string[] | ✅ | 非空数组（最少1个关键词） |
| `experience_refs[*].search_query_used` | string | ✅ | 非空；可复现检索 |
| `experience_refs[*].used_in_stage` | string | ✅ | 枚举: `stage_0_pre_search`, `stage_5_post_search`, `stage_6_post_search`, `stage_4_root_cause`, `stage_4_trace_drill`, `stage_5_knowledge`, `stage_5_post_search`, `recommendation` |
| `experience_refs[*].adoption_status` | string | ✅ | 枚举: `adopted_as_evidence`, `adopted_as_suggestion`, `considered_not_adopted` |
| `experience_refs[*].conflict_with_curated_knowledge` | boolean | ✅ | 默认 false；true 时 conflict_detail 必填 |
| `experience_refs[*].conflict_detail` | string | ❌ | conflict=true 时必填；≤ 200 字 |
| `experience_refs[*].content_quoted` | string | ✅ | ≤ 200 字；原文片段非大意 |
| `experience_refs[*].how_used_in_diagnosis` | string | ✅ | ≤ 100 字 |
| `experience_refs[*].confidence_on_reference` | number | ✅ | [0.0, 1.0]；精度 0.01 |
| `experience_refs[*].confidence_reason` | string | ✅ | ≤ 100 字 |
| `summary` | object | ✅ | — |
| `summary.total_references` | integer | ✅ | = `len(experience_refs)` |
| `summary.adopted_as_evidence_count` | integer | ✅ | ≥0；三项计数之和 = total_references |
| `summary.adopted_as_suggestion_count` | integer | ✅ | ≥0；同上 |
| `summary.considered_not_adopted_count` | integer | ✅ | ≥0；同上 |
| `summary.conflicted_with_curated_count` | integer | ✅ | ≥0；= `sum(x.conflict=true for x in experience_refs)` |
| `summary.reference_coverage_note` | string | ✅ | 长度 10 ~ 200 字 |

**唯一性约束**：同一 `experience_id` 在 `experience_refs` 数组中不得重复出现
（同一经验在不同阶段使用时，在 `used_in_stage` 中用逗号分隔多阶段，或用多条
不同 experience_id——推荐前者，单条记录多阶段标签）。

---

### 2.1 chapter_1_overview

| 字段 | 类型 | Required | 约束 |
|------|------|----------|------|
| `report_id` | string | ✅ | 正则: `^RPT-\d{8}-[A-Z0-9]{4}$` |
| `title` | string | ✅ | 长度: 10 ~ 100 |
| `fault_type` | string | ✅ | 枚举: `latency`, `connectivity`, `mixed`, `unknown` |
| `summary` | string | ✅ | 长度: 10 ~ 200 |
| `kb_id` | string | ✅ | 非空 |
| `kb_name` | string | ✅ | 非空 |
| `time_range` | object | ✅ | — |
| `time_range.start` | string | ✅ | 正则: `^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}$` |
| `time_range.end` | string | ✅ | 同上; 且 `end >= start` |
| `affected_scope` | object | ✅ | — |
| `affected_scope.clusters` | string[] | ✅ | 可空数组 |
| `affected_scope.hosts` | string[] | ✅ | 可空数组 |
| `affected_scope.pods` | string[] | ✅ | 可空数组 |
| `affected_scope.src_ips` | string[] | ✅ | 可空数组 |
| `affected_scope.dst_ips` | string[] | ✅ | 可空数组 |
| `affected_scope.note` | string | ❌ | ≤ 200 字 |
| `schema_version` | string | ✅ | 固定: `"1.0"` |

---

### 2.2 chapter_2_data_integrity

| 字段 | 类型 | Required | 约束 |
|------|------|----------|------|
| `parse_overview` | object | ✅ | — |
| `parse_overview.total_files` | integer | ✅ | ≥ 0 |
| `parse_overview.success_files` | integer | ✅ | ≥ 0 |
| `parse_overview.running_files` | integer | ✅ | ≥ 0 |
| `parse_overview.failed_files` | integer | ✅ | ≥ 0 |
| `parse_overview.unknown_files` | integer | ✅ | ≥ 0 |
| 计数约束 | — | ✅ | `success + running + failed + unknown == total` |
| `file_details` | array | ✅ | 长度 = total_files |
| `file_details[*].log_id` | string | ✅ | 唯一 |
| `file_details[*].log_name` | string | ✅ | 非空 |
| `file_details[*].overall_status` | string | ✅ | 枚举: `successful`, `running`, `retrying`, `failed`, `pending`, `cancelled`, `unknown` |
| `file_details[*].task_id` | string/null | ❌ | — |
| `file_details[*].fault_count_total` | integer | ✅ | ≥ 0 |
| `integrity_rating` | string | ✅ | 枚举: `FULL`, `PARTIAL`, `INSUFFICIENT` |
| `integrity_statement` | string | ✅ | 长度: 10 ~ 300 |

---

### 2.3 chapter_3_fingerprint

| 字段 | 类型 | Required | 约束 |
|------|------|----------|------|
| `symptom_detailed` | string | ✅ | 长度: 20 ~ 500 |
| `structured_signals` | object | ✅ | — |
| `structured_signals.status_codes` | string[] | ✅ | 可空; 去重 |
| `structured_signals.failure_mode_ids` | string[] | ✅ | 可空; 去重 |
| `structured_signals.src_ips` | string[] | ✅ | 可空; 去重 |
| `structured_signals.dst_ips` | string[] | ✅ | 可空; 去重 |
| `structured_signals.hosts` | string[] | ✅ | 可空; 去重 |
| `structured_signals.pods` | string[] | ✅ | 可空; 去重 |
| `structured_signals.clusters` | string[] | ✅ | 可空; 去重 |
| `structured_signals.latency_components` | string[] | ✅ | 可空; 去重 |
| `structured_signals.log_keywords` | string[] | ✅ | 可空; 去重 |
| `top_findings` | array | ✅ | 长度 3 ~ 10 |
| `top_findings[*].finding` | string | ✅ | ≤ 200 字 |
| `top_findings[*].evidence_source` | string | ✅ | 正则: `^[a-z_]+\.[a-z_.]+$` |
| `top_findings[*].severity` | string | ✅ | 枚举: `CRITICAL`, `HIGH`, `MEDIUM`, `LOW` |

**信号约束**: `latency_components` 非空 ⟺ fault_type ∈ {`latency`, `mixed`};
`status_codes` 非空 ⟺ fault_type ∈ {`connectivity`, `mixed`}。

---

### 2.4 chapter_4_root_cause

| 字段 | 类型 | Required | 约束 |
|------|------|----------|------|
| `root_causes` | array | ✅ | 长度 1 ~ 5 |
| `root_causes[*].rank` | integer | ✅ | 从 1 开始连续编号 |
| `root_causes[*].cause_summary` | string | ✅ | 长度 10 ~ 200 |
| `root_causes[*].cause_detailed` | string | ✅ | 长度 50 ~ 1000 |
| `root_causes[*].confidence` | number | ✅ | [0.0, 1.0], 精度 0.01 |
| `root_causes[*].confidence_reason` | string | ✅ | ≤ 200 字 |
| `root_causes[*].primary_evidence` | array | ✅ | 长度 ≥ 2 |
| `root_causes[*].primary_evidence[*].ref` | string | ✅ | 正则 `^E-\d{2}$` |
| `root_causes[*].primary_evidence[*].description` | string | ✅ | ≤ 200 字 |
| `root_causes[*].primary_evidence[*].source_tool` | string | ✅ | 非空 |
| `root_causes[*].primary_evidence[*].source_field` | string | ✅ | 非空 |
| `root_causes[*].primary_evidence[*].raw_snippet` | string | ✅ | ≤ 500 字 |
| `root_causes[*].counter_checks` | array | ✅ | 长度 ≥ 1 |
| `root_causes[*].counter_checks[*].ref` | string | ✅ | 正则 `^C-\d{2}$` |
| `root_causes[*].counter_checks[*].check` | string | ✅ | ≤ 200 字 |
| `root_causes[*].counter_checks[*].result` | string | ✅ | 枚举 `EXCLUDED`, `INCONCLUSIVE`, `CONFIRMED_ALTERNATIVE` |
| `root_causes[*].counter_checks[*].detail` | string | ✅ | ≤ 200 字 |
| `final_root_cause_summary` | string | ✅ | 长度 10 ~ 100 |

**排序约束**: `root_causes` 数组必须按 `confidence` **严格降序**排列。
**首尾一致**: `root_causes[0].cause_summary` 语义必须与 `final_root_cause_summary` 一致。

---

### 2.5 chapter_5_recommendations

| 字段 | 类型 | Required | 约束 |
|------|------|----------|------|
| `short_term` | array | ✅ | 长度 ≥ 1（当根因已知时） |
| `short_term[*].action` | string | ✅ | 祈使句；≤ 200 字 |
| `short_term[*].urgency` | string | ✅ | 枚举 `IMMEDIATE`, `HOURS`, `DAYS` |
| `short_term[*].expected_effect` | string | ✅ | ≤ 200 字 |
| `short_term[*].risk` | string | ✅ | 枚举 `NONE`, `LOW`, `MEDIUM`, `HIGH` |
| `short_term[*].risk_detail` | string | ❌ | `risk=HIGH` 时 required |
| `long_term` | array | ✅ | 长度 ≥ 1（当根因已知时） |
| `long_term[*].action` | string | ✅ | 祈使句；≤ 300 字 |
| `long_term[*].owner` | string | ✅ | 非空 |
| `long_term[*].timeframe` | string | ✅ | 枚举 `WEEKS`, `MONTHS`, `QUARTERS` |
| `long_term[*].expected_effect` | string | ✅ | ≤ 200 字 |
| `verification_steps` | string[] | ✅ | 长度 ≥ 3；每条可操作 |

---

### 2.6 chapter_6_relations

| 字段 | 类型 | Required | 约束 |
|------|------|----------|------|
| `failure_modes` | array | ✅ | 可空 |
| `failure_modes[*].failure_mode_id` | string | ✅ | 非空 |
| `failure_modes[*].symptom` | string/null | ✅ | — |
| `failure_modes[*].matched` | boolean | ✅ | — |
| `failure_modes[*].match_reason` | string | ✅ | ≤ 300 字 |
| `status_code_knowledge` | array | ✅ | 可空 |
| `status_code_knowledge[*].status_code` | string | ✅ | 非空 |
| `status_code_knowledge[*].kb_hit` | boolean | ✅ | — |
| `status_code_knowledge[*].symptom_summary` | string/null | ✅ | kb_hit=false 时为 null |
| `matched_history_cases` | array | ✅ | 长度 0 ~ 3 |
| `matched_history_cases[*].case_id` | string | ✅ | 非空 |
| `matched_history_cases[*].match_score` | number | ✅ | [0.0, 1.0] |
| `matched_history_cases[*].title` | string | ✅ | 非空 |
| `matched_history_cases[*].relevance` | string | ✅ | 枚举 `HIGH`, `MEDIUM`, `LOW` |
| `matched_history_cases[*].note` | string | ✅ | ≤ 300 字 |
| `raw_log_refs` | array | ✅ | 长度 0 ~ 5 |
| `raw_log_refs[*].trace_id` | string | ✅ | 非空 |
| `raw_log_refs[*].log_file` | string | ✅ | 非空 |
| `raw_log_refs[*].timestamp` | string | ✅ | `YYYY-MM-DD HH:MM:SS` 格式 |
| `raw_log_refs[*].quote` | string | ✅ | ≤ 300 字 |
| `source_log_ids` | string[] | ✅ | 与 chapter_2.file_details[*].log_id 一致（子集） |

---

### 2.7 chapter_7_meta

| 字段 | 类型 | Required | 约束 |
|------|------|----------|------|
| `generated_at` | string | ✅ | `YYYY-MM-DD HH:MM:SS` 格式 |
| `generated_by` | string | ✅ | 固定: `"witty-ub-diagnostician-agent"` |
| `toolchain_version` | object | ✅ | — |
| `toolchain_version.backend` | string | ✅ | 非空 |
| `toolchain_version.report_schema` | string | ✅ | 固定: `"1.0"` |
| `toolchain_version.note` | string | ❌ | ≤ 200 字 |
| `validation` | object | ✅ | — |
| `validation.schema_validated` | boolean | ✅ | — |
| `validation.validator` | string/null | ✅ | schema_validated=true 时非空 |
| `validation.errors` | array | ✅ | schema_validated=false 时填写错误列表 |
| `validation.passed_at` | string/null | ✅ | schema_validated=true 时非空; 同 timestamp 格式 |

---

## 3. CaseDraft 案例沉淀契约（映射至 `CreateDiagCaseDraftRequest`）

本对象字段与 `latency/schemas/diag_case_library.py::CreateDiagCaseDraftRequest`
一一对应，可直接 `CreateDiagCaseDraftRequest.model_validate(case_draft)` 建草稿。

> ⚠️ **旧桥接（`DiagnosisCaseModel` 口径：`root_cause` / `recommendation` /
> `fingerprint_json` / `evidence_refs_json`）已废弃**：它没有带 `kind` 的证据锚点、
> 没有分步处置、也没有独立信号列，**过不了 `/diag_case_library/{case_id}/confirm`
> 的确认闸门**。不要再按旧口径组织写入数据。

### 3.1 三步链路（对话确认，不引入前端页面与审批流）

1. 报告渲染完成 → Agent 把报告路径与摘要交给用户；
2. 用户点头「报告 OK」→ `POST /diag_case_library`（本对象）取 `case_id` →
   `POST /diag_case_library/{case_id}/confirm`（`confirmed_by` = 用户标识）→
   案例进入可检索集合；
3. 处置执行 + 复测后 → `PATCH /diag_case_library/{case_id}` **只补** `verification_json`。

> 步骤 2 与 3 之间案例已可检索，但 `closed_loop` 为假：检索侧按「待验证处方」处理，
> `applicability` 上限 `adjust`（见 `case-matching/SKILL.md` 纪律 9）。

### 3.2 字段映射

| 字段 | 类型 | Required | 映射来源 |
|------|------|----------|---------|
| `log_type` | string | ✅ | 板块 1，`KVCache` / `UBSocket` |
| `source` | string | ✅ | `internal`（本系统现场）/ `community` / `online` |
| `source_url` | string | community/online 必填 | 外部来源链接 |
| `title` | string | ✅ | 报告标题 |
| `symptom_summary` | string | ✅ | 板块 2 现象摘要；**须能独立读懂**，不依赖报告上下文 |
| `root_cause_summary` | string | ✅ | 板块 4 根因结论，一句话根因 |
| `root_cause_detail` | string | ❌ | 板块 4 机理长文（推理链逐级证据） |
| `operation` | `GET`/`SET` | ❌ | `/stats/stages` 的 `operation`；GET 与 SET 不许混写一条案例 |
| `fault_type` | string | ✅ | `latency` / `connectivity` / `mixed` / `unknown` |
| `confidence` | number | ❌ | 板块 2 置信度；仅知识库解释支撑的不得给高值 |
| `status_codes[]` | string[] | ❌ | 板块 3 指纹，**原始故障码字符串**（`"1002"`），信号权重 3.0 |
| `failure_mode_ids[]` | string[] | ❌ | 板块 7 匹配到的故障模式 ID，信号权重 3.0 |
| `latency_components[]` | string[] | ❌ | 板块 6 阶段表**桶 key**（`set_client` / `urma`），禁中文展示名 |
| `log_keywords[]` | string[] | ❌ | 现场日志**原文短语**（保留大小写与下划线），禁意译 |
| `hosts[]` / `pods[]` / `src_ips[]` / `dst_ips[]` / `cluster_name` | array / string | ❌ | 板块 1 + 指纹；逐字取自现场接口返回值 |
| `version_json` | object | ❌ | `{kernel, os, urma, umq, ubsocket}`；**有可靠来源才填** |
| `stage_features_json` | object | ❌ | 板块 6 阶段桶快照 `{operation, buckets[], sample_cnt, truncated}` |
| `fault_shape` | string | ❌ | 板块 6 时间形状 |
| `time_window_json` | object | ❌ | `{start, end}` 故障时间窗 |
| `scope_limits` | string | ❌ | 不适用场景，防止被跨域误套用 |
| `node_type` | string | ❌ | 超节点形态 |
| `kb_id` / `kb_name` | string | ❌ | 来源标注；留空 = 全局案例（可跨库召回） |
| `evidence_json[]` | array | ✅ 闸门要求 ≥1 | `{kind: api\|trace\|log\|sql, ref, params, excerpt, note}` |
| `counter_evidence_json[]` | array | ❌ | 板块 4 反证检查的已排除项 |
| `remediation_json[]` | array | ✅ 闸门要求 ≥1 | `{step, action, expected, risk}`，由板块 3 建议拆成分步 |
| `relations_json[]` | array | ❌ | `{case_no, relation: same_fault\|upstream\|downstream\|false_positive, note}` |
| `source_log_ids[]` | string[] | ❌ | 板块 1 的来源日志 ID |
| `created_by` | string | ❌ | 报告生成者标识 |

**不提供的字段**（服务端生成或事后回填）：`case_no` / `search_text` / `status` /
`revision` / `verification_json`。

### 3.3 纪律（与确认闸门一致）

1. **`verification_json` 报告阶段留空**：处置尚未执行，`observed_result` 只允许在
   执行 + 复测后经 `PATCH` 回填；臆造验证记录比没有验证更坏。
2. `evidence_json[].ref` 必须可复现（trace_id / `文件:行号` / 接口+参数），
   不接受「某处日志显示」这类不可复核的写法。
3. `remediation_json` 每步都要写 `expected`（执行后应观察到什么）与 `risk`。
4. **至少一个可匹配信号**（`status_codes` / `failure_mode_ids` / `latency_components` /
   `log_keywords` / `hosts` / `pods` / IP / `cluster_name`）非空，否则案例永远检索不到；
   `operation` 不计入。
5. 特征只能来自现场观测，不得为凑匹配填入未观测到的 IP / Pod / 错误码；
   `log_keywords` 必须是本次现场日志的原文短语。

### 3.4 示例

```json
{
  "log_type": "KVCache",
  "source": "internal",
  "created_by": "witty-ub-diagnostician",
  "title": "SET 通断失败：umq 建链队列拥塞",
  "symptom_summary": "SET 请求大面积超时，客户端返回 kvcache_conn_fault_020，故障窗 19:02~19:11",
  "root_cause_summary": "umq 建链队列拥塞导致 SET 首包超时",
  "root_cause_detail": "set_client 桶堆积……（推理链逐级证据）",
  "operation": "SET",
  "fault_type": "latency",
  "confidence": 0.8,
  "status_codes": ["1004"],
  "failure_mode_ids": ["kvcache_conn_fault_020"],
  "latency_components": ["set_client", "set_worker"],
  "log_keywords": ["Connect Timeout"],
  "pods": ["kvcache-worker-3"],
  "version_json": {"kernel": "5.10", "urma": "2.4"},
  "scope_limits": "仅适用于 KVCache SET 场景",
  "time_window_json": {"start": "2026-09-21 19:02:00", "end": "2026-09-21 19:11:00"},
  "evidence_json": [
    {"kind": "api", "ref": "POST /stats/stages", "params": {"operation": "SET"},
     "excerpt": "set_client P90=12ms", "note": "定位到 set_client 桶"}
  ],
  "counter_evidence_json": [{"item": "worker 磁盘写满", "why_excluded": "磁盘水位 42%"}],
  "remediation_json": [
    {"step": 1, "action": "重启 umq 服务", "expected": "建链队列清空，SET P90 回落", "risk": "瞬断"}
  ]
}
```
