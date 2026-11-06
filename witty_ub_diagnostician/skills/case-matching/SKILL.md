---
name: case-matching
description: >
  历史案例特征匹配与检索 Skill。从现场证据提取分布特征（错误码分布、超时时延段、
  故障模式、时间形态、影响范围、机理关键词），调用
  POST /diag_case_library/search 从**已人工确认**的超节点诊断案例库宽召回候选，
  再做分布特征软匹配打分，按 L1/L2/L5 逐级判定与 applicability 判定可迁移性，
  采纳后回写命中。身份特征（IP/Pod/主机/集群名）不参与匹配。
  当需要判断"这个现象以前是否发生过"、"有没有可复用的处置经验"、"这个根因是否有先例"时使用。
license: MIT
compatibility: >
  Requires HTTP API access to FastAPI backend on port 9772 via bash curl for evidence retrieval.
  scripts/match_cases.py 仅依赖 Python 标准库。
metadata:
  author: witty-ub-diagnostician
  version: "2.2"
  keywords: [案例匹配, 历史案例, 分布特征, 软匹配, 经验复用, 知识库匹配, L1L2L5, diag_case_library, diagnosis_case, 反证检查]
allowed-tools: >
  Bash(curl:*) Bash(cd:*) Bash(python3:*)
  experience-skill
---

# 案例特征匹配 (Case Matching)

输入：本次现场证据（KVCache `/stats/*`、BRPC `/brpc-diagnosis/*`）或已完成的诊断结论。
输出：候选案例列表，每条带分布特征软匹配分、L1/L2/L5 逐级判定与 applicability。

**匹配口径（v2，分布特征软匹配）**：不按 IP/Pod/主机/集群**名字**做精确匹配（不同现场
必然不同，不可迁移），改用分布/语义特征软打分——故障模式（最强 4.0）、主导错误码
（3.0 ×share）、超时时延段/归因桶（2.0 ×share）、操作域一致性（1.0）、机理关键词
（1.0）、时间形态（1.0）、影响范围规模（0.5）。相对权重吸收自 Web 前端"相似案例分析"
模块（`similarity.py` 的 failure_mode 6.0 / status_code 4.0 / 段·操作 3.0 / 超时段·形态
2.0 / scope 1.0 比例），化用时保留 `share` 加权与宽召回口径。
权重表与 share 提取见 `references/FEATURE_SPEC.md`。召回为"宽召回"（operation +
fault_type + kb_id），相似度由 `scripts/match_cases.py` 客户端软打分决定。

**候选排除口径（v2.2+）**：宽召回后，`match_cases.py` 会剔除一级标签为
`Coordinator故障` / `UB管控面故障` 的候选，不参与软打分与投票（LOO 全量评估实证：
这两类候选与 Worker/硬件报告在软打分维度高度重叠、吸走 top1，而对应查询报告本身
判别特征不足，保留只引入干扰；剔除后不含管控 top1 63.4%→68.3%）。候选列表与
JSON 输出的 `excluded_control_plane` 字段会如实反映剔除条数。

本 Skill **只做检索侧**：不诊断、不写报告、不沉淀案例。案例写入由
`diagnostic-report-generation` 负责，字段口径见 `references/CASE_FEATURE_CONTRACT.md`。

## 三条检索通道（可信度不同，不得混用）

| 通道 | 端点 | 内容 | 用法纪律 |
|---|---|---|---|
| **phenomenon（先查目录卡）** | `POST /phenomenon/search` | 现象卡片：相似度、已发布短摘要、信任标签、报告/案例详情指针，不含全文 | 只用来找线索和指针；必须按指针回取详情，卡片摘要不得当结论 |
| **library（正解通道）** | `POST /diag_case_library/search` | 只返回 `status=confirmed` 的案例：人工确认过、含证据锚点、分步处置、验证闭环、不适用场景 | 可以作为经验依据引用，但仍须回到现场证据核对 |
| legacy（降级通道） | `POST /diagnosis_case/search` | 旧的 `diagnosis_case` 表：**无人工确认关卡**、内容物只有现象/根因/建议三段、`kb_id` 必填 | **只能当线索**，必须标注"来源=diagnosis_case（未经人工确认）"，不得作为结论依据 |

> 判别口诀：**没经确认的案例不是经验，只是别人的猜测。** 结论里引用案例时，必须写清来源通道。
>
> library 通道的案例带两级分类快照（`first_level_label` / `second_level_label`）。
> `POST /diag_case_library/search` 可传同名过滤字段或 `unclassified_only=true`；
> `GET /diag_case_library/{case_id}` 另返回 `source_report` 导航
> （`valid` / `stale` / `deleted` / `unavailable` / `independent`）与
> `classification_status`，引用前可据此回到源报告核对。

## 现象检索与回取（自然语言通道）

用本次现场证据提炼一段现象描述（操作对象、错误码、阻塞阶段、时延形态），先找历史线索：

```http
POST /phenomenon/search
{"query": "GET 对象不存在时阻塞在订阅超时，返回 K_NOT_FOUND", "top_k": 5}
```

- 过滤条件按需传 `log_type` / `operation` / `fault_type`；`operation` 传 `GET`/`SET` 时，
  `operation_scope=report` 的命中只代表整份报告包含该操作，须回取报告确认故障归属。
- **回取优先级**：`get_case` → `get_legacy_case` → `get_fault` → `get_report`。
  单故障接口只返回目标故障；`get_fault` 为空（合成键）时才回退完整报告并自行裁剪。
- **信任标签**：`verified` 可作为已验证方案参考；`confirmed_unverified` 是待验证处方，
  `applicability` 上限 `adjust`；`report_only` / `suspected` 只作诊断线索；`legacy_unverified`
  只能作非结构化历史线索。
- 指针返回 `404`、案例已归档或绑定已过期时，跳过该指针或回退到仍可用的关联报告，
  不得引用失效的历史处置方案。
- RAG 不可用（`503 retryable=true`）时回退 `POST /diag_case_library/search` 结构化检索；
  无命中只记录"现象通道未召回"，不推断系统无故障。

## 纪律（硬约束）

1. **命中案例是待验证假设，不是本次现场证据。** 检索结果只能用于提出候选根因；
   必须回到现场证据核对后，才允许写进结论。未核对的一律标注"待验证假设"。
2. **证据分层表述**：知识库解释（`failure_mode_knowledge` / `status_code_knowledge`）、
   历史案例（`diag_case_library` 已确认 / `diagnosis_case` 未经确认）、本次现场证据，
   三者分开写。禁止把知识库结论或历史案例的结论直接当成现场事实；
   引用未经确认的 legacy 案例时必须显式标注其未确认属性。
3. **反证检查先于结论**：每条拟采用的候选，必须写出一条"若不成立，现场会观察到什么"，
   并回到现场证据核对。案例自带 `counter_evidence_json` 的，优先借用其排除项。
4. **不许只给笼统匹配分**：每条候选必须给 L1/L2/L5 逐级"命中/不命中"判定（软匹配口径，
   写明命中哪些分布特征、对应 share 与权重），并给出 applicability。分数只是排序依据，
   不是采用依据。
5. **GET / SET 分开检索**：library 通道 `operation` 是纯过滤器（提交即隔离，不计入
   归一化分母）；legacy 通道没有该字段，隔离只能靠"分两次查询、各自只提交本
   operation 的信号"。任何通道都禁止把两种操作的信号合并成一次查询。
   `operation=MIXED` 或未标注操作的案例对两种操作都成立，会同时出现在 GET 与 SET 的
   结果里；`MIXED` 只说明整份报告覆盖该操作，判定故障归属仍须回取报告。
6. **特征只能来自现场观测**：不得为了凑匹配填入未观测到的错误码/故障模式/阶段桶；
   `share` 必须来自 `/stats/stages`、错误码统计的真实占比，不得拍脑袋给权重；
   `log_keywords` 必须是本次现场日志的原文短语，不能套用历史案例里的短语。
   身份信息（IP/Pod/主机/集群名）即使在场也只作来源标注，不参与匹配。
7. **命中即回写**：凡被采纳（含部分采纳）为参考的案例，回写对应通道的
   `POST /diag_case_library/{case_id}/hit` 或 `POST /diagnosis_case/{case_id}/hit`。
   检索后一条都没采纳的不回写。
8. **空结果不等于健康**：宽召回（operation/fault_type/kb_id）下 `total=0` 只说明库内
   无同类先例，不说明系统正常，也不能据此否定故障存在；候选非空但软打分为 0 的，
   说明该 operation 域下有案例但无分布特征命中，要按实际情况说明，不要当成"完全无先例"。
9. **未闭环案例的上限是 `adjust`**：`verification_json.closed_loop=false` 的案例（含报告阶段
   刚确认、处置尚未执行就入库的"待验证处方"）**不得给 `direct`**，`applicability` 上限为
   `adjust`，并在输出里标注"未闭环，方案未经验证"。只有 `closed_loop=true` 且 L1/L2
   都成立时才允许 `direct`（L5 机理命中是加分项，不强制）。

## 检索流程（5 步）

### 步骤 1 提取六层特征

按 `references/FEATURE_SPEC.md` 的清单取数，落盘为一份特征 JSON（骨架见该文件末尾）。
最低要求：`operation`、时间窗，以及至少一类分布特征（错误码/故障模式/超时时延段/
关键词等）——宽召回不要求"信号精确命中"，但没有任何分布特征时软打分全为 0，只能按
confidence/hit_count 排序。

- KVCache：`POST /stats/stages`（`operation` 各调一次）、
  `POST /stats/error_codes|pods|links|heatmap`、`/trace/list`、
  `/log_failure_event_result/list_trace_events`。
- BRPC：先 `GET /brpc-diagnosis/batch/{batch_id}/summary` 一页纸定位组件/Pod/时间窗/故障模式。
- 知识侧补充（不算现场证据）：`GET /failure_mode/{id}`、`GET /failure_mode/status_code/{code}`。
- 已取得的 `kb_id`、`log_id`、时间范围必须继续传递，不要因为字段"可选"就丢掉限定条件。

### 步骤 2 结构化检索

```bash
cd witty_ub_diagnostician/skills/case-matching/scripts
python3 match_cases.py /tmp/case_match/features.json --top 5 --json /tmp/case_match/result.json
python3 match_cases.py /tmp/case_match/features.json --source legacy   # 仅在 library 通道确实无结果时才考虑
```

脚本只构建宽召回查询（过滤头）→ 按 `--source` 选通道 → 在客户端做分布特征软匹配打分重排。

- **`--source library`（默认，正解通道）**：打 `POST /diag_case_library/search`，只召回
  `status=confirmed` 的已确认案例。`kb_id` 可省略（留空 = 跨知识库召回，`kb_id` 只作来源标注），
  `operation` 由服务端精确过滤，不参与计分。
- **`--source legacy`（降级通道）**：打 `POST /diagnosis_case/search`，`kb_id` 必填且服务端校验
  存在性，**不能传空串做跨库检索**；检索范围 = 本次知识库 + 全局案例。该通道案例未经人工确认，
  输出必须标注其来源属性。

### 步骤 3 逐级判定 L1 / L2 / L5

对每条候选按三级分别判定，命中级别与不命中级别都要写清（软匹配口径：看分布特征
是否命中、share 与权重多少，不比较 IP/Pod/主机/集群名字）：

| 级 | 看什么 | 命中判据 | 不命中意味着 |
|---|---|---|---|
| L1 错误码/故障模式 | `status_codes`（×share）、`failure_mode_ids` | 至少一个码/模式 ID 相同 | 故障语义不同，方案基本不可迁移 |
| L2 故障域 | `latency_components`（超时时延段/归因桶，×share）、`failure_domain`、操作域（GET/SET，MIXED 半权）、时间形态、影响范围规模 | 至少一个归因桶/域相同（父桶与子桶可算相关） | 只是现象相近，不是同类故障 |
| L5 机理 | `log_keywords`、证据锚点 | 关键词短语/证据同源 | 机理不同，不能借其排除项 |

> 补充证据：`score_norm` 高只说明"分布特征像"，不能替代 L1/L2 判定；`log_keywords`
> 命中可作 L5 机理佐证，但同样不能替代 L1/L2 的语义判定。

### 步骤 4 给出 applicability

必须四选一，并写清理由（不允许只给匹配分）：

| applicability | 适用条件 | 输出要求 |
|---|---|---|
| `direct` | L1+L2 命中，环境同构（版本/配置/规模可比），时间线形态一致，**且案例 `closed_loop=true`** | 可直接采用其处理方案，注明沿用的证据 |
| `adjust` | L1 或 L2 命中，但环境不同（版本、配置、规模）；或案例**未闭环** | 逐条列出"需要调整什么"，调整点必须能在现场验证 |
| `reference` | 仅 L2 同域、或仅 `log_keywords` 相近 | 只作排查方向，不得直接抄其结论 |
| `not_recommended` | L1 不命中且 L2 不同域 | 明确不建议采用，并说明否定理由（避免后来者重复踩） |

判定前先看案例的 `verification_json`：`closed_loop=false` 或缺失时，该案例是"待验证处方"，
`applicability` 最高只能到 `adjust`——它的方案还没被任何一次处置验证过（见纪律 9）。

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