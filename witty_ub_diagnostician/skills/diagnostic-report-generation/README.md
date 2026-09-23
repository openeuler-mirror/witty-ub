# diagnostic-report-generation

诊断报告**标准化生成与案例沉淀** Skill。Agent 只准备一份数据 JSON，由
`scripts/render_report.py` 渲染成独立 HTML 报告（7 个带编号的顶层章节、9 类内容板块）；
报告经用户确认后可沉淀为**超节点诊断案例库**里可被检索的案例。

## 报告章节结构

渲染产物是 7 个连续编号的顶层章节：
`01 日志基本信息 → 02 事件诊断摘要 → 03 故障清单与关系(仅多故障) →
04 综合处置计划 → 05 统计分析 → 06 故障档案 → 07 诊断工作追踪`（单故障为 `01→05`）。
各板块字段清单与撰写原则见 `references/REPORT_BLOCKS.md`。

## 使用流程

1. 调用 latency-analysis / failure-code-analysis / brpc-diagnosis skill 完成诊断
2. 用 `scripts/render_report.py --spec <板块>` 查字段清单，据此写数据 JSON
3. `python3 scripts/render_report.py /tmp/report_data.json` 渲染 HTML（脚本做 schema-lite 校验）
4. 把报告路径与摘要交给用户；用户确认「报告 OK」后沉淀为案例：
   `POST /diag_case_library`（建草稿）→ `POST /diag_case_library/{case_id}/confirm`
   （走确认闸门，通过后才可被检索召回）
5. 处置执行 + 复测后：`PATCH /diag_case_library/{case_id}` 只补 `verification_json`
   （`closed_loop` / `observed_result` / `verified_at`）；**报告阶段严禁臆造验证结果**

详细流程见 [SKILL.md](SKILL.md)，案例字段契约见
[references/REPORT_SCHEMA.md](references/REPORT_SCHEMA.md) §3，
检索侧口径见 `../case-matching/SKILL.md`。
