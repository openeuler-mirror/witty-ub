---
name: diagnostic-report-generation
description: >
  把已完成的诊断结论渲染成标准化 HTML 诊断报告（7 个带编号的顶层章节）。
  报告由 scripts/render_report.py 调用 Jinja2 模板生成：Agent 只负责按契约准备
  一个数据 JSON，不手写 HTML、不内联渲染模板。
  当诊断完成后需要输出结构化报告、沉淀案例或归档时使用本 Skill。
license: MIT
compatibility: >
  Requires HTTP API access to FastAPI backend on port 9772 via bash curl for evidence retrieval.
  渲染需要 python3 + jinja2（镜像已内置 python3-jinja2）。
metadata:
  author: witty-ub-diagnostician
  version: "2.1"
  keywords: [诊断报告, report, HTML报告, 推理链, 故障传播, 源码分析, 统计分析, 知识库匹配, 工作追踪, brpc, ubsocket, umq, urma]
allowed-tools: >
  Bash(curl:*) Bash(cd:*) Bash(python3:*)
  experience-skill
---

# 诊断报告生成 (Diagnostic Report Generation)

把诊断结论渲染为**独立 HTML 报告**（7 个带编号的顶层章节，内含 9 类内容板块）。
零 JS 依赖、纯 CSS 图表，可直接在浏览器打开或打印。

术语区分：**顶层章节**是渲染出的 7 个带编号章节；**内容板块**（日志基本信息、
分析结论、解决方案、根因分析、故障传播链、统计分析、知识库匹配、诊断工作追踪、
源码分析）是数据结构维度，其中多数渲染在单条故障档案内部，两套编号不同。

## 前置条件

本 Skill **不负责诊断**。使用前必须已从 `latency-analysis` / `failure-code-analysis` /
`brpc-diagnosis` Skill 或直接 HTTP API 调用拿到诊断结论与证据。

## 生成流程（3 步）

**步骤 1 收集数据**：数据来源速查表见 `references/REPORT_BLOCKS.md`
（组件定位、统计分布、故障模式、知识库、代表 trace、历史案例）。

**步骤 2 写数据 JSON**：把本次报告的**全部模板变量**写进一个 JSON 文件
（如 `/tmp/report_data.json`）。字段清单用脚本查，**不要整体读模板**
（`templates/report.html` 约 98 KB）或预读整份 references：

```bash
cd witty_ub_diagnostician/.opencode/skills/diagnostic-report-generation/scripts
python3 render_report.py --spec top          # 顶层契约、枚举与单故障兼容规则
python3 render_report.py --spec statistics   # 单板块字段清单（可换任意板块名）
```

字段含义、示例与各板块撰写原则按需查 `references/REPORT_BLOCKS.md` 对应小节。

**步骤 3 渲染**：

```bash
cd witty_ub_diagnostician/.opencode/skills/diagnostic-report-generation/scripts
python3 render_report.py /tmp/report_data.json
# 默认输出 $WITTY_REPORT_DIR/<kb_id>/report_<kb_id>_<时间戳>.html（容器内
# WITTY_REPORT_DIR=/var/witty-ub/reports，由 witty-ub-reports 卷持久化），
# 同目录写同名侧车 .json（原样报告数据，前端「诊断报告」列表靠它取标题/故障数）。
# 不要传 out 参数把报告挪到 /tmp 或仓库目录；本地调试可用 --kb-id 指定目录名。
```

脚本做 schema-lite 校验（必需顶层键、字段枚举、`share_bar` 百分比合计、
GET/SET 混桶），成功后**只回显 ≤15 行摘要**（输出路径/侧车/章节/故障/统计/提示）。
退出码：`0` 成功 / `2` 数据或渲染错误（按提示改 JSON 后重跑）/ `3` 模板缺失 /
`4` 缺 jinja2 / `5` 写盘失败（目录不可写）。**校验失败时修正 JSON 后重跑，
不要改用别的方式手写 HTML。**

## 报告契约（硬约束）

顶层变量：`report` / `basic_info` / `incident_summary` / `faults[]` /
`fault_relations[]` / `action_plan[]` / `statistics` / `workflow`。

章节顺序固定，编号连续：
`01 日志基本信息 → 02 事件诊断摘要 → 03 故障清单与关系(仅多故障) →
04 综合处置计划(有则显示) → 05 统计分析 → 06 故障档案 → 07 诊断工作追踪`
（单故障为 `01→05`）。**统计分析放在故障档案之前**：先给事件级横向定位，
再逐个档案纵向深挖。

**单故障兼容**：可直接传旧的扁平变量（`conclusion` / `solution` / `root_cause` /
`propagation` / `knowledge_matches` / `source_code`），模板自动包装成 F01 档案。

### 多故障分诊（先分诊，再分配诊断深度）

宏观概览后必须先区分"多异常现象"与"多独立故障"，按三信号判定：

| 信号 | 归并为同一故障 | 拆为独立故障 |
|------|--------------|-------------|
| 时间窗 | 同一尖峰窗，或 A 稳定领先 B 1~3 分钟（级联时序） | 时间窗互不重叠 |
| 故障域/组件 | 域相同或存在上下游调用关系 | 域不同且无调用关系 |
| 影响面 | 故障 pod/host 集合为包含关系 | 影响集合互不相交 |

- 同一根因引起的多个异常 → **归并为一个故障**，多表现用传播链 `branches` 展示，不拆开
- A 导致 B（三信号满足级联）→ A `role: primary`、B `role: secondary`，关系
  `type: causes`；次生故障若已能被上游解释则置 `simplified: true`（只渲染结论，
  必要时加方案）并填 `upstream` / `need_independent_fix`
- 两个根因互不依赖 → 各自 `role: independent`，关系 `type: independent`
- 只是多个尚未确认的候选原因 → 属同一故障下的候选假设，在根因推理链中用排除步骤
  体现，**禁止认定为多个故障**；必须单列时 `status: suspected`
- 同根因用 `common_cause`；仅时间上先后但因果未证实必须用 `correlated`
  （模板以虚线+琥珀色表达，与 causes 的红色实线严格区分），
  **禁止把相关性写成因果性**

多故障必填 `incident_summary`（一句话说清"识别了几个故障、谁是主故障、什么关系"，
不要把根因堆在一句话里）与 `fault_relations[]`（`from`/`to`/`type`/`confidence`/`evidence`）。
跨故障措施须在 `action_plan[]` 中**合并、去重、排序**：一条措施解决多个故障时只写
一条、用 `fault_ids` 关联多个编号。

### 故障档案与折叠纪律

`faults[]` 每项独立携带结论/时延阶段/根因/传播链/知识库/方案/源码。多故障时档案
**默认全部收起**，收起态卡片头必须给出一行一句话结论
（复用 `conclusion.one_line_conclusion`，使不展开也能看出发生了什么）；单故障默认展开，
此时不重复展示该行。故障清单、关系图、处置计划、统计阶段表中的编号链接会自动展开
并定位；打印/导出 PDF 时自动全部展开。

### GET 与 SET 是两套独立口径

`statistics` 用 **`stage_breakdowns`** 数组承载（GET 一套、SET 一套，各调一次
`/stats/stages`，`operation` 分别传 GET/SET）并列呈现；只有一种操作时也可用单对象
`stage_breakdown`（同时存在时以 `stage_breakdowns` 为准）。**禁止把两种操作的阶段
混进同一套 `share_bar` 百分比**；也禁止为 SET 编造 `create_latency` /
`publish_latency` / `urma_processing_us` 分段（解析路径不产出）。

### 知识库匹配纪律

- 1~3 条、按匹配度降序；`match_logic` 必须写明 **L1(错误码)/L2(故障域)/L3(拓扑)**
  三级匹配逻辑（哪级命中、哪级不命中）
- 每条必须给 `applicability`：`direct` 可直接采用 / `adjust` 调整后采用 /
  `reference` 仅供参考 / `not_recommended` 不建议采用——**不允许只给笼统匹配分**
- 必须同时覆盖 curated 知识（failure_mode_knowledge）与 experience-skill 经验
- 证据分层：知识库解释、历史案例与本次现场证据分别表述，不把知识库结论当成现场事实；
  `POST /diag_case_library/search` 命中的已确认案例也只能作为**待验证假设**，须有本次现场
  证据支撑才可用于根因，未验证的在结论中显式标注；若降级用了 `POST /diagnosis_case/search`
  （旧表、未经人工确认），必须显式标注其未确认属性

## 证据锚点纪律（faults[].evidence_traces[]）

每条故障可附 **0~5 条代表 trace 锚点**，让读者拿着 trace ID 回到现场复现结论
（`GET /trace/{id}` 或 `POST /trace/list`）。字段契约见
`references/REPORT_BLOCKS.md`「evidence_traces 块」。

取数（**均属本流程已调用的接口，不新增调用**）：

| `kind` | 来源 | 取值 |
|--------|------|------|
| `latency` | `POST /stats/stages` 响应 | 该故障**归因桶**的 `top_traces[]` 前 1~3 条 |
| `error` | `POST /log_failure_event_result/list_trace_events` | 按该故障 `status_code` + `pod`/`host` + 故障时间窗过滤后的返回行 |

纪律：

1. **禁止编造**：`trace_id` 必须逐字来自本次工具响应；不得凭印象、不得复用历史报告或
   知识库案例里的 ID，不得改写长度或大小写。
2. **`why` 必须可复核**：写明桶 key（如 `GET·URMA超时`）或完整过滤条件
   （status_code + pod + 时间窗）。`latency` 类必须点明"证据耗时 Top"口径——
   `top_traces` 是"桶内**证据耗时** Top"，代表该阶段耗时最极端的请求，
   **不等于故障最严重或最具普遍性**，不点明口径会被误读为严重度排序。
3. **只从归因桶取**：不跨桶凑数，跨桶 trace 属其它故障的证据，列错会把读者引向错误结论。
4. **允许 0 条**：取不到就省略该键或置 `[]`，**不得为填满而降低选择标准**。
   键缺省 / `null` / `[]` 三者行为一致，模板整块不渲染（不出标题、不出占位符）。
5. **上限 5 条**：超过 5 条对读者无增量，只稀释报告密度。
6. **不写数据保留期声明**：报告不加"锚点有效性以底层数据保留期为限"一类注记。
7. **数组内不重复**：同一 trace 同时命中时延与通断时只列一条，另一侧信息并入 `why`。

## 案例沉淀（报告确认后，三步链路）

报告渲染完成后，若用户认可报告，可把它沉淀为**可检索的历史案例**。契约与字段映射见
`references/REPORT_SCHEMA.md` §3（**不是**旧的 `DiagnosisCaseModel` 桥接口径）：

1. 把报告路径与一句话摘要交给用户，等用户明确点头；
2. 用户点头后：`POST /diag_case_library`（建草稿，拿 `case_id`）→
   `POST /diag_case_library/{case_id}/confirm`（`confirmed_by` = 用户标识）——
   通过确认闸门后案例才进入可检索集合；
3. 处置执行 + 复测后：`PATCH /diag_case_library/{case_id}` **只补** `verification_json`
   （`closed_loop` / `observed_result` / `verified_at`）。

确认闸门（`confirm` 的硬条件，缺一即被拒）：`draft` 态、`evidence_json` ≥1 条带 `kind`
的可复现锚点、`remediation_json` ≥1 步、**至少一个可匹配信号**（`status_codes` /
`failure_mode_ids` / `latency_components` / `log_keywords` / `hosts` / `pods` / IP /
`cluster_name`，`operation` 不计入）、`confirmed_by` 非空。**闸门不要求验证闭环**。

纪律：

- **`verification_json` 报告阶段必须留空。** 处置尚未执行，`observed_result` 只允许在
  执行 + 复测后经 `PATCH` 回填；臆造验证记录比没有验证更坏。
- **只写本次报告里真有的事实**：`log_keywords` 用现场日志原文短语，IP / Pod / 错误码
  必须来自现场观测，`version_json` 无可靠来源就不填。
- 报告阶段确认的案例 `closed_loop` 为假，检索侧按「待验证处方」处理，
  `applicability` 上限 `adjust`——不要把它当成已验证的黄金案例。
- `archived` 案例不可再改；`confirmed` 案例只开放 `verification_json`，内容物已冻结。

## BRPC 诊断报告差异

`fault_type=brpc` 时：`basic_info` 来自 `brpc_diag_batch`；
`conclusion.fault_component` / `fault_function` 来自 `brpc_diag_node`；
`statistics` 改用 `GET /brpc-diagnosis/batch/{batch_id}/summary`
（components → top_pods / top_failure_modes → peak_window；kb 全域用
`GET /brpc-diagnosis/knowledge/{kb_id}/summary`）；`top_hosts` 无对应，可省略。

## 典型使用场景

| 用户请求 | 前置条件 |
|---------|---------|
| "把刚才的诊断写成报告" / "生成一份诊断报告" | 本会话已运行诊断 Skill；未诊断则先回诊断 Skill |
| "把这个案例沉淀到经验库" | 先生成完整报告并取得用户确认，再按上文「案例沉淀」三步链路写入案例库 |