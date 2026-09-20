# experience-skill 引用标注模板（强制）

本文档是所有诊断 Skill（latency-analysis / failure-code-analysis /
brpc-diagnosis）共享的经验引用标注规范。**任何时候**引用了
`experience-skill` 知识库（SKILL 或 WIKI）的内容——无论用于根因假设、
处理建议、错误码含义辅助判断、还是参考了阈值/基线——都必须按本模板
记录**每条**引用。该记录将被 `diagnostic-report-generation` Skill 直接
采集并写入报告的 `chapter_0_experience_refs` 章节。

## JSON 模板（每条引用一个对象，汇总为数组）

```json
{
  "experience_refs": [
    {
      "experience_id": "<来自 Experience.id 的 UUID，必填>",
      "experience_type": "SKILL | WIKI",
      "name": "<来自 Experience.name>",
      "source_path": "<来自 Experience.source，如 data/skill_hub/ds-kv-cache-diagnosis/skill_def.md>",
      "keywords_matched": ["<检索该条经验时用的关键词，用于可追溯>"],
      "search_query_used": "<完整的 search-experiences --query 值>",
      "used_in_stage": "<按所用 Skill 的阶段枚举填写，见下表>",
      "adoption_status": "adopted_as_evidence | adopted_as_suggestion | considered_not_adopted",
      "conflict_with_curated_knowledge": true | false,
      "conflict_detail": "<仅 conflict=true 时必填，说明与 `GET /failure_mode/status_code/{status_code}` / `GET /failure_mode/{failure_mode_id}` 的哪条内容冲突、最终如何取舍>",
      "content_quoted": "<直接引用经验中的原文片段，≤200字；严禁超长粘贴>",
      "how_used_in_diagnosis": "<一句话说明：用在根因排序/处理方案/错误码辅助判断……，如 采用该经验的 ETCD 续约失败周期=5min 特征匹配本次尖峰周期>",
      "confidence_on_reference": 0.0 ~ 1.0,
      "confidence_reason": "<为何信任此条：与现场证据相符 / 与 curated failure_mode 一致 / 有历史案例佐证>"
    }
  ]
}
```

## 字段说明（基于 `Experience` schema）

| 字段 | 来源（Experience / search 结果） | 约束 |
|------|---------------------------------|------|
| `experience_id` | `Experience.id` | 必填，UUID |
| `experience_type` | `Experience.type` | 必填，枚举 SKILL/WIKI |
| `name` | `Experience.name` | 必填，非空 |
| `source_path` | `Experience.source` | 必填，可追溯到 `data/skill_hub/.../skill_def.md` 或 `data/wiki_hub/...md` |
| `keywords_matched` | 人工记录 + `Experience.keywords` 交集 | 非空数组 |
| `search_query_used` | 执行 search-experiences 的 --query | 必填，可完全复现检索 |
| `used_in_stage` | 人工标记诊断阶段 | 严格按各 Skill 的枚举值（见下表） |
| `adoption_status` | — | adopted_as_evidence = 影响了根因结论；adopted_as_suggestion = 仅用于建议；considered_not_adopted = 考虑过但未采用（必须填原因） |
| `conflict_with_curated_knowledge` | 人工判断 | 与 `GET /failure_mode/status_code/{status_code}` / `GET /failure_mode/{failure_mode_id}` 返回的 curated 内容冲突时 = true；否则 = false |
| `conflict_detail` | 人工描述 | conflict=true 时必填，≤200字 |
| `content_quoted` | 原文摘录 | ≤200字；不允许用"省略号"/"大意如下"，必须是原文片段 |
| `how_used_in_diagnosis` | 人工描述 | ≤100字，说清楚引用 → 诊断结论的因果链 |
| `confidence_on_reference` | 人工打分 | 0.0~1.0，精度 0.01 |
| `confidence_reason` | 人工描述 | ≤100字 |

## used_in_stage 枚举（按 Skill 区分）

| Skill | 合法枚举值 |
|-------|-----------|
| latency-analysis | `stage_0_pre_search` / `stage_5_post_search` / `stage_4_root_cause` / `stage_5_recommendation` |
| failure-code-analysis | `stage_0_pre_search` / `stage_6_post_search` / `stage_4_trace_drill` / `stage_5_knowledge` / `recommendation` |
| brpc-diagnosis | `stage_0_pre_search` / `stage_6_post_search` |

## 四条铁律

1. **用了必记，记必可追溯**：只要引用了经验（哪怕一句话），必须记录；
   `experience_id` + `source_path` 必须能唯一定位到源文件。
2. **经验 ≠ 证据，更 ≠ Curated 官方知识**：`adopted_as_evidence` 需极度谨慎。
   经验库内容只有在被 HTTP API 返回的**现场事实**（trace / metrics / logs）
   验证后，才能升格为"证据"；否则只能是 suggestion 或 hypothesis。
   与 `GET /failure_mode/status_code/{status_code}` /
   `GET /failure_mode/{failure_mode_id}` 的 curated 内容冲突时，**curated 优先**，
   本条经验必须标记 `considered_not_adopted` 并填写冲突详情。
3. **不采用也要说明原因**：检索命中但最终没用的，也要记录
   `considered_not_adopted` + 排除理由（特别是与 curated 冲突的情况）。
   这是避免"选择性忽略反例"的关键手段。
4. **Curated 内容不需要过 experience-skill 标注**：
   `GET /failure_mode/status_code/{status_code}` 和
   `GET /failure_mode/{failure_mode_id}` 是后端自带的 curated 知识库，
   不属于 experience-skill，**不要**在本模板标注。二者的使用和引用
   在报告 chapter_6_relations 中记录。
