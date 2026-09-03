---
name: diagnostic-report-generation
description: >
  标准化生成 KVC 分布式缓存的时延/故障码诊断报告，以及 BRPC 组件故障诊断报告。
  引导 Agent 按八章节结构（经验库引用标注、报告概览、数据完整性、现象与指纹、
  根因分析、处理建议、关联信息、生成元数据）逐一构造 JSON 片段，最终组合为完整
  报告并通过 JSON Schema 校验，可以直接映射为 DiagnosisCaseModel 写入历史案例库。
  当诊断完成后需要输出结构化报告、沉淀案例、或归档时使用本 Skill。特别地，
  chapter_0 强制记录所有引用了 experience-skill 知识库的内容及其采用状态，
  保证结论的可追溯性和知识边界清晰。
license: MIT
compatibility: >
  Requires HTTP API access to FastAPI backend on port 9772 via bash curl for evidence retrieval.
  Output JSON conforms to DiagnosisCaseModel fields in schemas/diagnosis_case.py and can be
  validated via any JSON Schema validator (Pydantic model_validate, jsonschema, etc.).
metadata:
  author: witty-ub-diagnostician
  version: "1.1"
  keywords: [诊断报告, report, 报告生成, JSON Schema, DiagnosisCase, 结构化输出, 案例沉淀, 根因报告, brpc, ubsocket, umq, urma, 组件故障]
allowed-tools: >
  Bash(curl:*) Bash(cd:*)
  experience-skill
---

# 诊断报告生成 (Diagnostic Report Generation)

引导 Agent 按**七章节顺序**逐一构造 JSON 子对象，合并后即为完整报告。
每章节末尾有"字段校验清单"，填写后必须自检通过才能进入下一章节。

---

## 前置条件：必须先完成诊断

本 Skill **不负责诊断本身**。使用本 Skill 前，必须已通过以下路径之一
获取了诊断结论和证据：

- 已运行 `latency-analysis` Skill（四阶段时延诊断流程）
- 已运行 `failure-code-analysis` Skill（五阶段故障码诊断流程）
- 已运行 `brpc-diagnosis` Skill（BRPC 组件故障诊断流程）
- 已通过直接 HTTP API 调用拿到了完整的诊断数据和结论

若尚未诊断，先回到对应诊断 Skill 完成流程。

---

## 章节顺序（严格按 0→7）

每章产出一个独立 JSON 对象（`chapter_0`, `chapter_1`, ...），
最后一步将 8 个 chapter 合并为 `full_report` 并做 Schema 校验。

---

## 章节 0：经验库引用标注 (chapter_0_experience_refs)

**本章强制要求。** 凡在诊断过程中引用了 `experience-skill` 知识库
（SKILL 或 WIKI）的内容，**必须**全部记录在本章。内容**直接复用**
latency-analysis / failure-code-analysis 附录A中的 `experience_refs`
数组输出，无需重新构造。

### JSON 模板（直接来自诊断 Skill 的附录 A 输出）

```json
{
  "experience_refs": [
    {
      "experience_id": "<Experience.id UUID>",
      "experience_type": "SKILL | WIKI",
      "name": "<Experience.name>",
      "source_path": "<Experience.source>",
      "keywords_matched": ["<匹配的关键词>"],
      "search_query_used": "<完整的 search-experiences --query 字符串>",
      "used_in_stage": "<在诊断 Skill 的哪个阶段引用>",
      "adoption_status": "adopted_as_evidence | adopted_as_suggestion | considered_not_adopted",
      "conflict_with_curated_knowledge": true | false,
      "conflict_detail": "<仅 conflict=true 时填；curated 优先说明>",
      "content_quoted": "<引用原文片段，≤200字>",
      "how_used_in_diagnosis": "<一句话：引用如何作用于诊断结论>",
      "confidence_on_reference": 0.0 ~ 1.0,
      "confidence_reason": "<为何信任/不信任该引用>"
    }
  ],
  "summary": {
    "total_references": <int>,
    "adopted_as_evidence_count": <int>,
    "adopted_as_suggestion_count": <int>,
    "considered_not_adopted_count": <int>,
    "conflicted_with_curated_count": <int>,
    "reference_coverage_note": "<100字内说明：本报告的根因/建议中，经验库贡献了哪些、哪些完全来自现场证据>"
  }
}
```

### 汇总统计规则（summary 字段自动计算）

| 字段 | 计算方式 |
|------|---------|
| `total_references` | `len(experience_refs)` |
| 三个 *_count | 对应 `adoption_status` 的计数 |
| `conflicted_with_curated_count` | `conflict_with_curated_knowledge = true` 的条数 |

### 自检清单（必须全部 Yes）

- [ ] 若诊断 Skill 中运行过 `experience-skill search-experiences`，**每条命中**都在本章有记录（无论是否采用）
- [ ] 每条 `content_quoted` ≤ 200 字，且为原文片段，非大意总结
- [ ] 所有 `adopted_as_evidence` 的条目都有对应的现场证据（可在 chapter_4 中找到 E-xx 编号交叉验证）
- [ ] 所有 `conflict_with_curated_knowledge = true` 的条目均填写了 `conflict_detail`，且明确了取舍
- [ ] `reference_coverage_note` 如实写明了经验库在本报告中的作用边界

---

## 章节 1：报告概览 (chapter_1_overview)

### JSON 模板

```json
{
  "report_id": "RPT-<YYYYMMDD>-<4位随机>",
  "title": "<一句话概括：故障类型 + 核心现象 + 影响范围>",
  "fault_type": "latency | connectivity | brpc | mixed | unknown",
  "summary": "<100字以内摘要：何时+何地+什么现象+主要根因>",
  "kb_id": "<来自 POST /log_kb/list 的知识库ID>",
  "kb_name": "<知识库名称>",
  "time_range": {
    "start": "YYYY-MM-DD HH:MM:SS",
    "end": "YYYY-MM-DD HH:MM:SS"
  },
  "affected_scope": {
    "clusters": ["<cluster名>"],
    "hosts": ["<host名或IP>"],
    "pods": ["<pod名>"],
    "src_ips": ["<源IP>"],
    "dst_ips": ["<目的IP>"],
    "note": "<影响范围的自然语言补充>"
  },
  "schema_version": "1.0"
}
```

### 字段提取来源

| 字段 | 提取来源 |
|------|---------|
| `kb_id` / `kb_name` | `GET /log_kb/{kb_id}` 返回结果 |
| `fault_type` | 用了 latency 工具 = latency；用了 failure 工具 = connectivity；两者都有 = mixed；不确定 = unknown |
| `time_range.start/end` | `POST /log_failure_event_result/list_time_aggregated_failure_events` 或 `POST /aggregated_event/list_time_window` 的最早/最晚时间戳；或用户明确给出 |
| `affected_scope.*` | `POST /log_failure_event_result/list_pod_aggregated_failure_events` 返回的 pod/host/cluster；或 `POST /aggregated_event/list` 的 src/dst IP |

### 自检清单（必须全部 Yes）

- [ ] title 含：故障类型 + 现象 + 范围（如"KVC集群P99延迟升高-影响host-101"）
- [ ] summary 在 100 字以内，覆盖了"何时何地何事何因"
- [ ] fault_type 是四个枚举值之一（无拼写错误）
- [ ] time_range 格式严格为 `YYYY-MM-DD HH:MM:SS`
- [ ] affected_scope 的列表项**全部来自工具实际返回值**，无臆测

---

## 章节 2：数据完整性声明 (chapter_2_data_integrity)

### JSON 模板

```json
{
  "parse_overview": {
    "total_files": <int>,
    "success_files": <int>,
    "running_files": <int>,
    "failed_files": <int>,
    "unknown_files": <int>
  },
  "file_details": [
    {
      "log_id": "<文件ID>",
      "log_name": "<文件名>",
      "overall_status": "successful | running | retrying | failed | pending | cancelled | unknown",
      "task_id": "<task_id 或 null>",
      "fault_count_total": <int>
    }
  ],
  "integrity_rating": "FULL | PARTIAL | INSUFFICIENT",
  "integrity_statement": "<自然语言声明：数据完整 / 基于部分数据的暂定结论 / 数据不足结论不可靠>"
}
```

### 字段提取来源

全部来自 `POST /log_file/list/{kb_id}` 结果的逐文件统计。若存在 overall_status≠successful
的文件，追加调用 `GET /task/{task_id}` 补充进度信息。

**integrity_rating 判定规则：**

| 情况 | 评级 |
|------|------|
| 100% 文件 overall_status=successful 且 fault_count > 0 | FULL |
| 有 running、retrying 或 failed 文件，但成功文件占比 ≥ 60% | PARTIAL |
| 成功文件 < 60% 或 0 成功文件 | INSUFFICIENT |

### 自检清单

- [ ] parse_overview 四类计数之和 = total_files
- [ ] file_details 每条 log_id 唯一
- [ ] PARTIAL/INSUFFICIENT 时 integrity_statement 明确写了"暂定结论"或"不可靠"
- [ ] 每个失败文件都有对应的 task_id（若工具返回了）

---

## 章节 3：故障现象与结构化指纹 (chapter_3_fingerprint)

**本章对应 `DiagnosisCaseModel.fingerprint_json` + `symptom_summary`。**

### JSON 模板

```json
{
  "symptom_detailed": "<200字以内详细现象：用户初始报告 + 工具发现的客观表现>",
  "structured_signals": {
    "status_codes": ["<状态码字符串，如 -1002、K_RPC_UNAVAILABLE>"],
    "failure_mode_ids": ["<FM-xxx>"],
    "src_ips": ["<源IP>"],
    "dst_ips": ["<目的IP>"],
    "hosts": ["<host名>"],
    "pods": ["<pod名>"],
    "clusters": ["<cluster名>"],
    "latency_components": ["<如 urma_total_latency、worker_query_meta_latency>"],
    "log_keywords": ["<关键日志短语，如 Connection refused>"]
  },
  "top_findings": [
    {
      "finding": "<客观发现，如 IP对10.0.0.5→10.0.0.8 P99达1200ms，超基线8倍>",
      "evidence_source": "<接口.返回字段，如 POST /aggregated_event/list.total_latency>",
      "severity": "CRITICAL | HIGH | MEDIUM | LOW"
    }
  ]
}
```

### 字段提取来源

| 字段 | latency 诊断来源 | failure 诊断来源 |
|------|-----------------|-----------------|
| status_codes | —（通常无） | `POST /log_failure_event_result/list_trace_events` 返回的 status_code（去重，Top 5 高频） |
| failure_mode_ids | — | `POST /log_failure_event_result/list_trace_events` 返回的 failure_mode_id（去重） |
| src/dst_ips | `POST /aggregated_event/list` Top N | `POST /log_failure_event_result/list_trace_events` 返回的 src_ip/dst_ip |
| hosts/pods/clusters | `POST /log_parse_result/list` 的 host/pod/cluster | `POST /log_failure_event_result/list_pod_aggregated_failure_events` 返回 |
| latency_components | `POST /log_parse_result/list` 的 anomaly_components（去重） | — |
| log_keywords | `POST /log_parse_result/list` 原始日志关键短语 | `POST /log_failure_event_result/list_log_events` 原始日志关键短语 |
| top_findings | `POST /aggregated_event/list` / `POST /aggregated_event/list_time_window` 极值 | `POST /log_failure_event_result/list_time_aggregated_failure_events` / `POST /log_failure_event_result/list_pod_aggregated_failure_events` 极值 |

### 自检清单

- [ ] symptom_detailed 中**客观描述 ≥ 70%**，主观推测 ≤ 30%
- [ ] structured_signals 列表项**全部去重**，无重复值
- [ ] latency_components / status_codes 至少有一个非空（否则 fault_type 可能判定错误）
- [ ] top_findings 至少 3 条，最多 10 条；每条 evidence_source 指向具体工具和字段

---

## 章节 4：根因分析与置信度 (chapter_4_root_cause)

**本章对应 `DiagnosisCaseModel.root_cause` + `confidence` + `evidence_refs_json`
+ `counter_evidence_json`。**

### JSON 模板

```json
{
  "root_causes": [
    {
      "rank": 1,
      "cause_summary": "<一句话根因：如 worker节点磁盘IO打满导致GET操作阻塞>",
      "cause_detailed": "<100-300字详细描述：机制链路、为何会导致观测现象、为何不是其他原因>",
      "confidence": 0.0 ~ 1.0,
      "confidence_reason": "<为何给此置信度：证据强度+是否有反证>",
      "primary_evidence": [
        {
          "ref": "<证据编号，如 E-01>",
          "description": "<证据描述，如 host-101 iowait=92%>",
          "source_tool": "<工具名>",
          "source_field": "<字段路径>",
          "raw_snippet": "<工具返回的原始片段（≤2行）>"
        }
      ],
      "counter_checks": [
        {
          "ref": "<反证编号，如 C-01>",
          "check": "<尝试排除的内容，如 检查host-102是否同样异常>",
          "result": "EXCLUDED | INCONCLUSIVE | CONFIRMED_ALTERNATIVE",
          "detail": "<结果说明>"
        }
      ]
    }
  ],
  "final_root_cause_summary": "<最终结论：30字以内，对应rank=1的cause_summary>"
}
```

### 置信度打分参考

| 置信度区间 | 含义 | 判定条件 |
|-----------|------|---------|
| ≥ 0.9 | 确定 | 多条独立证据 + curated failure_mode 完全匹配 + 无矛盾反证 |
| 0.7 ~ 0.89 | 高可信 | 2~3 条证据 + 1 条 failure_mode / status_code 知识匹配 + 反证已排除 |
| 0.4 ~ 0.69 | 中等 | 1 条强证据 + 1~2 条弱佐证；或存在未排除的替代假设 |
| 0.1 ~ 0.39 | 低 | 仅有推测，缺乏直接证据；或与历史案例相似度低 |
| < 0.1 | 无结论 | 无法排除，仅为假设 |

### 自检清单

- [ ] root_causes 按 confidence **降序**排列（rank 从 1 开始连续编号）
- [ ] 每条 cause_summary 后至少有 2 条 primary_evidence
- [ ] 每条 cause 至少有 1 条 counter_checks（即便是 INCONCLUSIVE 也要写"检查了什么、为何未排除"）
- [ ] confidence 只有 1 位小数（如 0.8、0.75 不要写 0.8231）
- [ ] final_root_cause_summary 与 rank=1 的 cause_summary 语义一致（无冲突）
- [ ] raw_snippet 长度 ≤ 两行，不粘贴大量原始日志

---

## 章节 5：处理建议 (chapter_5_recommendations)

**本章对应 `DiagnosisCaseModel.recommendation`。**

### JSON 模板

```json
{
  "short_term": [
    {
      "action": "<可立即执行的操作：如 重启pod-worker-101>",
      "urgency": "IMMEDIATE | HOURS | DAYS",
      "expected_effect": "<预期效果，如 恢复80%流量>",
      "risk": "NONE | LOW | MEDIUM | HIGH",
      "risk_detail": "<风险说明，HIGH时必须写>"
    }
  ],
  "long_term": [
    {
      "action": "<长期方案：如 将host-101磁盘升级为NVMe>",
      "owner": "<负责方，如 基础设施团队>",
      "timeframe": "WEEKS | MONTHS | QUARTERS",
      "expected_effect": "<如 消除此类故障复发>"
    }
  ],
  "verification_steps": [
    "<步骤1：验证操作后P99回到基线>",
    "<步骤2：验证错误码归零>",
    "<步骤3：持续观察24小时无复发>"
  ]
}
```

### 字段提取优先级（降序）

1. `GET /failure_mode/{failure_mode_id}` 返回的 `solution` 字段
2. `GET /failure_mode/status_code/{status_code}` 返回的 `root_cause` 对应的通用修复方案
3. `GET /diagnosis_case/{case_id}` 返回的 `recommendation` 历史案例的方案
4. 现场证据推导的合理方案（必须标注"基于现场证据推断，非标准方案"）

### 自检清单

- [ ] short_term 至少 1 条；long_term 至少 1 条（根因明确时）
- [ ] verification_steps 至少 3 条，可操作性强（无"观察"之类空话）
- [ ] HIGH 风险操作均有 risk_detail
- [ ] 每条 action 都是**祈使句**（动词开头，如"重启X"、"配置Y"）

---

## 章节 6：关联信息 (chapter_6_relations)

**本章对应 `DiagnosisCaseModel.failure_mode_ids` + `status_codes`
+ `source_log_ids` + 匹配的历史案例引用。**

### JSON 模板

```json
{
  "failure_modes": [
    {
      "failure_mode_id": "<FM-xxx>",
      "symptom": "<来自 GET /failure_mode/{failure_mode_id} 的 symptom 摘要>",
      "matched": true | false,
      "match_reason": "<为何匹配/不匹配>"
    }
  ],
  "status_code_knowledge": [
    {
      "status_code": "<-1002>",
      "kb_hit": true | false,
      "symptom_summary": "<知识库摘要，或 404 时写 null>"
    }
  ],
  "matched_history_cases": [
    {
      "case_id": "<历史案例ID>",
      "match_score": <float>,
      "title": "<案例标题>",
      "relevance": "HIGH | MEDIUM | LOW",
      "note": "<与本次的异同>"
    }
  ],
  "raw_log_refs": [
    {
      "trace_id": "<trace_id>",
      "log_file": "<日志文件名或路径>",
      "timestamp": "YYYY-MM-DD HH:MM:SS",
      "quote": "<引用的日志原文，≤1行>"
    }
  ],
  "source_log_ids": ["<来自 POST /log_file/list/{kb_id} 的 log_id，用于 DiagnosisCaseModel 写入>"]
}
```

### 字段提取来源

| 字段 | 工具 |
|------|------|
| failure_modes | 逐 ID 调用 `GET /failure_mode/{failure_mode_id}` |
| status_code_knowledge | 逐码调用 `GET /failure_mode/status_code/{status_code}`；200 = kb_hit=true；404 = kb_hit=false |
| matched_history_cases | `POST /diagnosis_case/search` 返回的 matches，取 Top 3 |
| raw_log_refs | `POST /log_failure_event_result/list_log_events` 返回的最具代表性日志（≤ 5 条） |
| source_log_ids | `POST /log_file/list/{kb_id}` 返回的 log_id 列表 |

### 自检清单

- [ ] failure_modes 和 status_code_knowledge 中，kb_hit=false 的条目**如实标注**（不隐瞒 404）
- [ ] matched_history_cases 最多 3 条；每条 match_score 来自工具实际返回（不臆造）
- [ ] raw_log_refs ≤ 5 条，每条 quote ≤ 1 行
- [ ] source_log_ids 与 chapter_2 中 file_details 的 log_id 一致（可做子集）

---

## 章节 7：生成元数据 (chapter_7_meta)

### JSON 模板

```json
{
  "generated_at": "YYYY-MM-DD HH:MM:SS",
  "generated_by": "witty-ub-diagnostician-agent",
  "toolchain_version": {
    "backend": "witty-ub-diagnosis-backend@1.x",
    "report_schema": "1.0",
    "note": "<版本差异说明或备注，可空>"
  },
  "validation": {
    "schema_validated": false,
    "validator": "<Pydantic model_validate / jsonschema CLI 等>",
    "errors": [],
    "passed_at": null
  }
}
```

### 注意

- `generated_at` 为当前时间（报告完成的时间，不是故障发生时间）
- `validation.schema_validated` 在最后一步校验通过后改为 `true`
- 未校验前永远是 `false`，**不得提前填写为 true**

---

## 最后一步：组合 + Schema 校验

### 组合为完整报告

将 8 个章节对象合并为一个顶层 JSON：

```json
{
  "report": {
    "chapter_0_experience_refs": { ... },
    "chapter_1_overview": { ... },
    "chapter_2_data_integrity": { ... },
    "chapter_3_fingerprint": { ... },
    "chapter_4_root_cause": { ... },
    "chapter_5_recommendations": { ... },
    "chapter_6_relations": { ... },
    "chapter_7_meta": { ... }
  },
  "diagnosis_case_bridge": {
    "kb_id": "<chapter_1.kb_id>",
    "fault_type": "<chapter_1.fault_type>",
    "title": "<chapter_1.title>",
    "symptom_summary": "<chapter_3.symptom_detailed>",
    "root_cause": "<chapter_4.final_root_cause_summary + \n\n + 各条cause的cause_detailed拼接>",
    "recommendation": "<chapter_5 short_term + long_term 逐条拼接>",
    "confidence": <chapter_4.root_causes[rank=1].confidence>,
    "failure_mode_ids": "<chapter_3.structured_signals.failure_mode_ids>",
    "status_codes": "<chapter_3.structured_signals.status_codes>",
    "fingerprint_json": {
      "<chapter_3.structured_signals 完整对象保留>" : "...",
      "_experience_refs_summary": {
        "total": "<chapter_0.summary.total_references>",
        "adopted_evidence": "<chapter_0.summary.adopted_as_evidence_count>",
        "adopted_suggestion": "<chapter_0.summary.adopted_as_suggestion_count>",
        "considered_not_adopted": "<chapter_0.summary.considered_not_adopted_count>",
        "conflicts_with_curated": "<chapter_0.summary.conflicted_with_curated_count>"
      }
    },
    "evidence_refs_json": [
      "<chapter_4 所有 primary_evidence 打平为数组>",
      { "_ref_type": "experience_skill", "<chapter_0 中 adopted_as_evidence 的条目原样追加，每条带 experience_id 前缀 EID-xxx>" }
    ],
    "counter_evidence_json": [
      "<chapter_4 所有 counter_checks 打平为数组>",
      { "_ref_type": "experience_skill_rejected", "<chapter_0 中 considered_not_adopted 的条目，仅记录 experience_id + 排除原因>" }
    ],
    "source_log_ids": "<chapter_6.source_log_ids>"
  }
}
```

### Schema 校验

使用 references/REPORT_SCHEMA.md 中定义的规则，任选一种方式校验：

1. **Pydantic（推荐）**：将 `diagnosis_case_bridge` 字段传给
   `DiagnosisCaseModel.model_validate(...)`，无异常即通过
2. **jsonschema CLI**：`jsonschema -i report.json REPORT_SCHEMA.json`
3. **手动**：对照 REPORT_SCHEMA.md 中每个字段的 type/required/范围检查

**校验通过后**，将 `chapter_7_meta.validation.schema_validated` 改为 `true`，
填入 `validator` 和 `passed_at`，最终输出完整 JSON。

---

## BRPC 诊断报告特殊字段

当 `fault_type` 为 `brpc` 时，报告需要包含以下 BRPC 组件诊断的特殊字段：

### batch_id（BRPC 诊断批次 ID）

- **字段路径**：`chapter_1_overview.brpc_context.batch_id`
- **来源**：`GET /brpc-diagnosis/batch/{batch_id}` 或 `GET /brpc-diagnosis/task/{task_id}/batch` 返回的批次标识
- **说明**：标识本次 BRPC 诊断的批次，用于关联同一诊断流程中的所有数据

### component（组件类型）

- **字段路径**：`chapter_1_overview.brpc_context.component`
- **枚举值**：`ubsocket | umq | urma`
- **来源**：从 `GET /brpc-diagnosis/batch/{batch_id}` 返回的组件类型，或从 `GET /brpc-diagnosis/batch/{batch_id}/hits` 返回的命中记录中提取
- **说明**：标识故障发生的 BRPC 组件类型

### thread_key（线程标识）

- **字段路径**：`chapter_3_fingerprint.structured_signals.thread_keys`
- **来源**：`GET /brpc-diagnosis/batch/{batch_id}/abnormal-threads` 或 `GET /brpc-diagnosis/batch/{batch_id}/thread-events/{event_id}` 返回的线程标识
- **说明**：标识异常线程，用于定位具体的线程级故障

### failure_graph（故障关系图）

- **字段路径**：`chapter_4_root_cause.failure_graph`
- **来源**：综合 `GET /brpc-diagnosis/batch/{batch_id}/interface-timeline`、`GET /brpc-diagnosis/batch/{batch_id}/pod-events`、`GET /brpc-diagnosis/batch/{batch_id}/thread-events` 等接口返回的调用链和事件关系构建
- **结构**：
  ```json
  {
    "nodes": [
      {
        "id": "<节点ID，如 pod名/线程ID/接口名>",
        "type": "pod | thread | interface | component",
        "label": "<节点标签>",
        "status": "normal | abnormal | critical"
      }
    ],
    "edges": [
      {
        "source": "<源节点ID>",
        "target": "<目标节点ID>",
        "relation": "calls | depends_on | triggers | blocks",
        "latency_ms": <可选：调用延迟>,
        "error_count": <可选：错误次数>
      }
    ]
  }
  ```
- **说明**：可视化展示故障在组件、线程、接口之间的传播路径和依赖关系

### BRPC 诊断数据提取来源

| 字段 | 工具 |
|------|------|
| `batch_id` | `GET /brpc-diagnosis/batch/{batch_id}` 或 `GET /brpc-diagnosis/task/{task_id}/batch` |
| `component` | `GET /brpc-diagnosis/batch/{batch_id}` 的 `component` 字段，或从命中记录推断 |
| `thread_keys` | `GET /brpc-diagnosis/batch/{batch_id}/abnormal-threads` 返回的线程标识列表 |
| `failure_graph.nodes` | 综合 `GET /brpc-diagnosis/batch/{batch_id}/pod-events`、`/thread-events`、`/interface-timeline` |
| `failure_graph.edges` | 从调用链、事件时序、依赖关系中提取 |

### BRPC 自检清单

- [ ] `batch_id` 非空且与实际诊断批次一致
- [ ] `component` 是三个枚举值之一（ubsocket/umq/urma）
- [ ] `thread_keys` 列表中的每个线程都能在 `GET /brpc-diagnosis/batch/{batch_id}/abnormal-threads` 中找到对应记录
- [ ] `failure_graph` 至少包含 2 个节点和 1 条边（否则无法体现故障传播）
- [ ] `failure_graph.nodes` 的 `status` 字段准确反映了各节点的健康状态

---

## 典型使用场景

| 用户请求 | 配合的诊断 Skill |
|---------|-----------------|
| "把刚才的诊断写成报告" | 本次会话已运行 latency-analysis 或 failure-code-analysis |
| "生成一份结构化诊断报告" | 同上；若未诊断则先回到诊断 Skill |
| "把这个案例沉淀到经验库" | 生成完整报告后，取 diagnosis_case_bridge 调用后端写入接口 |
