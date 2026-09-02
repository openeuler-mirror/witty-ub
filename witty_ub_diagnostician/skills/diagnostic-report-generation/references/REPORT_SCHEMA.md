# 诊断报告 JSON Schema 参考

本文件为 `diagnostic-report-generation` Skill 输出的报告提供字段级校验规则。
所有字段与 `schemas/diagnosis_case.py` 中 `DiagnosisCaseModel` 对齐。

---

## 1. 顶层结构

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "Witty-UB Diagnostic Report",
  "type": "object",
  "required": ["report", "diagnosis_case_bridge"],
  "properties": {
    "report": { "$ref": "#/$defs/ReportBody" },
    "diagnosis_case_bridge": { "$ref": "#/$defs/DiagnosisCaseBridge" }
  }
}
```

---

## 2. ReportBody（八章节）

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

## 3. DiagnosisCaseBridge（映射至 DiagnosisCaseModel）

本对象的字段一一对应 `schemas/diagnosis_case.py` 中 `DiagnosisCaseModel`，
可直接 `DiagnosisCaseModel.model_validate(bridge)` 无转换写入。

> ⚠️ **经验引用注入规则**：由于 `DiagnosisCaseModel` 没有单独的经验引用
> 字段，chapter_0 的内容通过**三个现有字段**以带前缀的子对象形式注入，
> 既不破坏 model_validate，又保证经验追溯链完整。

| 字段 | 类型 | DiagnosisCaseModel 字段 | 映射来源（含经验引用注入规则） |
|------|------|------------------------|---------|
| `kb_id` | string/null | kb_id | chapter_1.kb_id |
| `fault_type` | string | fault_type | chapter_1.fault_type |
| `title` | string/null | title | chapter_1.title |
| `symptom_summary` | string | symptom_summary | chapter_3.symptom_detailed |
| `root_cause` | string | root_cause | chapter_4 final + 各cause拼接；若根因采用了经验库内容，在文末追加一行 `[参考经验：EID-<experience_id> (<name>)]` |
| `recommendation` | string | recommendation | chapter_5 short_term + long_term；建议来自经验库的条目末尾追加 `[来源：EID-<experience_id>]` |
| `confidence` | number | confidence | chapter_4 root_causes[0].confidence；若采用 adopted_as_evidence 经验，对 confidence ≤ 0.05 修正并注明 |
| `failure_mode_ids` | string[] | failure_mode_ids | chapter_3 structured_signals |
| `status_codes` | string[] | status_codes | chapter_3 structured_signals |
| `fingerprint_json` | object | fingerprint_json | chapter_3 structured_signals **原样保留**；在对象顶层新增 `_experience_refs_summary` 键 = chapter_0.summary（不影响 FTS5 检索，带下划线前缀作保留字段） |
| `evidence_refs_json` | array | evidence_refs_json | chapter_4 所有 primary_evidence（HTTP API 现场证据）保持原样；**追加** chapter_0 中 adopted_as_evidence 的条目，每条加 `_ref_type="experience_skill"` 前缀和 `eid="<experience_id>"` 字段 |
| `counter_evidence_json` | array | counter_evidence_json | chapter_4 所有 counter_checks（HTTP API 现场反证）保持原样；**追加** chapter_0 中 considered_not_adopted 的条目，每条加 `_ref_type="experience_skill_rejected"` 前缀、`eid`、`rejection_reason`（=how_used_in_diagnosis 或 conflict_detail） |
| `source_log_ids` | string[] | source_log_ids | chapter_6 source_log_ids |

### 经验引用字段注入示例（evidence_refs_json）

```json
[
  { "ref": "E-01", "description": "host-101 P99=1200ms（基线150ms）", "source_tool": "POST /aggregated_event/list", ... },
  {
    "_ref_type": "experience_skill",
    "eid": "a1b2c3d4-5678-...",
    "name": "ds-kv-cache-diagnosis",
    "adoption_status": "adopted_as_evidence",
    "how_used_in_diagnosis": "其 Worker 磁盘阈值=90% 判断 host-101 为瓶颈",
    "confidence_on_reference": 0.8
  }
]
```
