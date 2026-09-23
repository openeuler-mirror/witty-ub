# case-matching

超节点日志**案例特征匹配与历史案例检索** Skill。只做检索侧：提取现场六层特征 →
组装结构化检索信号 → 召回**已人工确认**的案例 → 判定可迁移性 → 回写命中。

1. **提取特征**：L0 身份与范围 / L1 时间演化 / L2 操作与阶段（GET 8 桶、SET 5 桶）/
   L3 故障语义 / L4 组件与版本 / L5 机理与证据
2. **结构化检索**（默认通道）：`POST /diag_case_library/search`，只召回 `status=confirmed`
   的案例，本地按查询信号总权重归一化重排；`kb_id` 可省略（跨知识库召回）
3. **逐级判定**：L1 错误码 → L2 故障域 → L3 拓扑
4. **给出 applicability**：`direct` / `adjust` / `reference` / `not_recommended`
5. **回写命中**：`POST /diag_case_library/{case_id}/hit`

降级通道 `--source legacy`（`POST /diagnosis_case/search`）只返回**未经人工确认**的旧表案例，
只能当线索，引用时必须标注来源，回写走 `POST /diagnosis_case/{case_id}/hit`。

适用场景：判断现象是否有先例、根因是否有同类案例、处置方案能否直接复用。

- 流程与纪律见 [SKILL.md](SKILL.md)
- 特征清单与取数来源见 [references/FEATURE_SPEC.md](references/FEATURE_SPEC.md)
- 案例字段契约（写入侧 / 检索侧 / 后续 RAG 共用）见 [references/CASE_FEATURE_CONTRACT.md](references/CASE_FEATURE_CONTRACT.md)