# diagnostic-report-generation

诊断报告**标准化生成与案例沉淀** Skill。Agent 只准备一份数据 JSON，由
`scripts/render_report.py` 用统一契约独立校验，并可渲染成 HTML 报告（7 个带编号的
顶层章节、9 类内容板块）；
报告经用户确认后可沉淀为**超节点诊断案例库**里可被检索的案例。

## 报告章节结构

渲染产物是 7 个连续编号的顶层章节：
`01 日志基本信息 → 02 事件诊断摘要 → 03 故障清单与关系(仅多故障) →
04 综合处置计划 → 05 统计分析 → 06 故障档案 → 07 诊断工作追踪`（单故障为 `01→05`）。
各板块字段清单与撰写原则见 `references/REPORT_BLOCKS.md`。
故障档案支持同级的 `faults[].error`（错误码构成与时间分布）和
`faults[].latency`（时延阶段定位）；通断数据提取与口径见
[ERROR_FEATURES.md](references/ERROR_FEATURES.md)，字段速查用 `--spec error`。

## 使用流程

1. 调用 latency-analysis / failure-code-analysis / brpc-diagnosis skill 完成诊断
2. 用 `scripts/render_report.py --spec <板块>` 查字段清单，据此写数据 JSON；读取
   [标签参考](references/log_label.json)，在每条故障的 `conclusion` 中填写
   `first_level_label` / `second_level_label`（无法匹配的层级填 `null`）
3. 必须先运行 `python3 scripts/render_report.py /tmp/report_data.json --validate-only`；
   只要 JSON / 不渲染 HTML 时通过后即可停止，不会写 HTML、侧车或清理报告目录
4. 需要 HTML 时运行 `python3 scripts/render_report.py /tmp/report_data.json`；正式渲染
   会再次执行同一个校验器
5. 把报告路径与摘要交给用户；用户确认「报告 OK」后先确认整份报告
   （`POST /diagnostic_report/{report_id}/confirm`，带页面所见的 `expected_sidecar_hash`），
   再从目标故障生成案例草稿
   （`POST /diagnostic_report/{report_id}/faults/{fault_id}/case`）→
   `POST /diag_case_library/{case_id}/confirm`（走确认闸门，通过后才可被检索召回）
6. 处置执行 + 复测后：`PATCH /diag_case_library/{case_id}` 只补 `verification_json`
   （`closed_loop` / `observed_result` / `verified_by`，带 `expected_revision`）；
   **报告阶段严禁臆造验证结果**

详细流程见 [SKILL.md](SKILL.md)，案例字段契约见
[references/REPORT_SCHEMA.md](references/REPORT_SCHEMA.md) §3，
检索侧口径见 `../case-matching/SKILL.md`。
