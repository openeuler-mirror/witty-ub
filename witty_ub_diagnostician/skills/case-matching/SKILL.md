---
name: case-matching
description: >
  历史案例特征匹配与检索 Skill。从现场证据提取六层特征（身份范围、时间演化、操作阶段、
  故障语义、组件版本、机理证据），组装结构化检索信号，调用
  POST /diag_case_library/search 从**已人工确认**的超节点诊断案例库召回案例，
  按 L1/L2/L3 逐级匹配逻辑与 applicability 判定可迁移性，采纳后回写命中。
  当需要判断"这个现象以前是否出现过"、"有没有可复用的处置经验"、"这个根因是否有先例"时使用。
license: MIT
compatibility: >
  Requires HTTP API access to FastAPI backend on port 9772 via bash curl for evidence retrieval.
  scripts/match_cases.py 仅依赖 Python 标准库。
metadata:
  author: witty-ub-diagnostician
  version: "2.0"
  keywords: [案例匹配, 历史案例, 特征提取, 经验复用, 知识库匹配, L1L2L3, diag_case_library, diagnosis_case, 反证检查]
allowed-tools: >
  Bash(curl:*) Bash(cd:*) Bash(python3:*)
  experience-skill
---

# 案例特征匹配 (Case Matching)

输入：本次现场证据（KVCache `/stats/*`、BRPC `/brpc-diagnosis/*`）或已完成的诊断结论。
输出：候选案例列表，每条带命中信号、归一化匹配分、L1/L2/L3 逐级判定与 applicability。

本 Skill **只做检索侧**：不诊断、不写报告、不沉淀案例。案例写入由
`diagnostic-report-generation` 负责，字段口径见 `references/CASE_FEATURE_CONTRACT.md`。

## 两条检索通道（可信度不同，不得混用）

| 通道 | 端点 | 内容 | 用法纪律 |
|---|---|---|---|
| **library（默认，正解通道）** | `POST /diag_case_library/search` | 只返回 `status=confirmed` 的案例：人工确认过、含证据锚点、分步处置、验证闭环、不适用场景 | 可以作为经验依据引用，但仍须回到现场证据核对 |
| legacy（降级通道） | `POST /diagnosis_case/search` | 旧的 `diagnosis_case` 表：**无人工确认关卡**、内容物只有现象/根因/建议三段、`kb_id` 必填 | **只能当线索**，必须标注"来源=diagnosis_case（未经人工确认）"，不得作为结论依据 |

> 判别口诀：**没经确认的案例不是经验，只是别人的猜测。** 结论里引用案例时，必须写清来源通道。

## 纪律（硬约束）

1. **命中案例是待验证假设，不是本次现场证据。** 检索结果只能用于提出候选根因；
   必须回到现场证据核对后，才允许写进结论。未核对的一律标注"待验证假设"。
2. **证据分层表述**：知识库解释（`failure_mode_knowledge` / `status_code_knowledge`）、
   历史案例（`diag_case_library` 已确认 / `diagnosis_case` 未经确认）、本次现场证据，
   三者分开写。禁止把知识库结论或历史案例的结论直接当成现场事实；
   引用未经确认的 legacy 案例时必须显式标注其未确认属性。
3. **反证检查先于结论**：每条拟采用的候选，必须写出一条"若不成立，现场会观察到什么"，
   并回到现场证据核对。案例自带 `counter_evidence_json` 的，优先借用其排除项。
4. **不许只给笼统匹配分**：每条候选必须给 L1/L2/L3 逐级"命中/不命中"判定，并给出
   applicability。分数只是排序依据，不是采用依据。
5. **GET / SET 分开检索**：library 通道 `operation` 是服务端过滤字段（提交即隔离，
   且计入归一化分母）；legacy 通道没有该字段，隔离只能靠"分两次查询、各自只提交本
   operation 的信号"。任何通道都禁止把两种操作的信号合并成一次查询。
6. **特征只能来自现场观测**：不得为了凑匹配填入未观测到的 IP / Pod / 错误码；
   `log_keywords` 必须是本次现场日志的原文短语，不能套用历史案例里的短语。
7. **命中即回写**：凡被采纳（含部分采纳）为参考的案例，回写对应通道的
   `POST /diag_case_library/{case_id}/hit` 或 `POST /diagnosis_case/{case_id}/hit`。
   检索后一条都没采纳的不回写。
8. **空结果不等于健康**：`total=0` 只说明库内无同类先例，不说明系统正常，
   也不能据此否定故障存在。

## 检索流程（5 步）

### 步骤 1 提取六层特征

按 `references/FEATURE_SPEC.md` 的清单取数，落盘为一份特征 JSON（骨架见该文件末尾）。
最低要求：`operation`、时间窗、以及至少一个可匹配信号。

- KVCache：`POST /stats/stages`（`operation` 各调一次）、
  `POST /stats/error_codes|pods|links|heatmap`、`/trace/list`、
  `/log_failure_event_result/list_trace_events`。
- BRPC：先 `GET /brpc-diagnosis/batch/{batch_id}/summary` 一页纸定位组件/Pod/时间窗/故障模式。
- 知识侧补充（不算现场证据）：`GET /failure_mode/{id}`、`GET /failure_mode/status_code/{code}`。
- 已取得的 `kb_id`、`log_id`、时间范围必须继续传递，不要因为字段"可选"就丢掉限定条件。

### 步骤 2 结构化检索

```bash
cd witty_ub_diagnostician/.opencode/skills/case-matching/scripts
python3 match_cases.py /tmp/case_match/features.json --top 5 --json /tmp/case_match/result.json
python3 match_cases.py /tmp/case_match/features.json --source legacy   # 仅在 library 通道确实无结果时才考虑
```

脚本组装信号 → 按 `--source` 选通道 → 用查询信号总权重做归一化重排。

- **`--source library`（默认，正解通道）**：打 `POST /diag_case_library/search`，只召回
  `status=confirmed` 的已确认案例。`kb_id` 可省略（留空 = 跨知识库召回，`kb_id` 只作来源标注），
  `operation` 由服务端过滤且计入归一化分母。
- **`--source legacy`（降级通道）**：打 `POST /diagnosis_case/search`，`kb_id` 必填且服务端校验
  存在性，**不能传空串做跨库检索**；检索范围 = 本次知识库 + 全局案例。该通道案例未经人工确认，
  输出必须标注其来源属性。

### 步骤 3 逐级判定 L1 / L2 / L3

对每条候选按三级分别判定，命中级别与不命中级别都要写清：

| 级 | 看什么 | 命中判据 | 不命中意味着 |
|---|---|---|---|
| L1 错误码 | `status_codes`、`failure_mode_ids` | 至少一个码/模式 ID 相同 | 故障语义不同，方案基本不可迁移 |
| L2 故障域 | `component`（ubsocket/umq/urma）、`failure_domain`、阶段桶族、GET/SET | 同域或同桶族（10^2 与 10^2_007 属同族，父桶与子桶可算相关） | 只是现象相近，不是同类故障 |
| L3 拓扑 | 源目 IP、Pod、主机、集群 | 同 Pod 最强，同集群次之，同主机同 IP 再次 | 跨集群时只能借机理，不能借配置结论 |

> 补充证据：`log_keywords` 命中和 `score_norm` 高只说明"文本/信号像"，不能替代 L1/L2 判定。

### 步骤 4 给出 applicability

必须四选一，并写清理由（不允许只给匹配分）：

| applicability | 适用条件 | 输出要求 |
|---|---|---|
| `direct` | L1+L2 命中，L3 同构（同 Pod/同集群），时间线形态一致 | 可直接采用其处理方案，注明沿用的证据 |
| `adjust` | L1 或 L2 命中，但 L3 或环境不同（版本、配置、规模） | 逐条列出"需要调整什么"，调整点必须能在现场验证 |
| `reference` | 仅 L2 同域、或仅 `log_keywords` 相近 | 只作排查方向，不得直接抄其结论 |
| `not_recommended` | L1 不命中且 L2 不同域 | 明确不建议采用，并说明否定理由（避免后来者重复踩） |

### 步骤 5 回写命中

```bash
python3 match_cases.py --hit <case_id>                          # library 通道（默认）
python3 match_cases.py --hit <case_id> --source legacy          # legacy 通道必须显式指定
```

回写端点必须与检索通道一致：不确定案例来自哪个通道时，先看步骤 2 落盘结果里的
`source` / `source_confirmed` 字段，不要凭记忆选。

## 输出格式

检索结果以一张候选表收敛（不是散文），每行至少包含：

`case_id | title | fault_type | confidence | score_norm | 覆盖 | 命中级别 | applicability | 待验证点`

表后附：三级判定的逐条说明、反证检查结论、以及"哪些结论来自知识库/历史案例、
哪些来自本次现场证据"的分层声明。

## 与其他 Skill 的边界

| 需求 | 走哪个 Skill |
|---|---|
| 判断现象是否有先例、能否复用经验 | 本 Skill |
| 查项目内的排查流程与参考资料（Skill/Wiki 全文检索） | `experience-skill` |
| 现场诊断、取证据 | `latency-analysis` / `failure-code-analysis` / `brpc-diagnosis` |
| 把结论写成报告、沉淀为案例 | `diagnostic-report-generation` |

本 Skill 与 `experience-skill` 是两条互补通道：前者面向**结构化故障案例**（可打分、可回写命中），
后者面向**流程性经验与参考资料**（全文检索）。两者都要跑，结论在报告里合并呈现。