# diagnostic-report-generation

KVC 分布式缓存**诊断报告标准化生成**Skill。引导 Agent 按**七章节**结构
生成诊断报告，每章节独立构造 JSON，组合后通过内置 JSON Schema 校验，
最终可一键沉淀为 `DiagnosisCaseModel` 格式的历史案例。

## 报告章节结构

| 章节 | 内容 | 输入来源 |
|------|------|---------|
| 1 报告概览 | 标题、故障类型、时间范围、版本 | 用户问题 + POST /log_kb/list |
| 2 数据完整性声明 | 解析状态、数据集范围、完整性评级 | POST /log_file/list/{kb_id} + GET /task/{task_id} |
| 3 故障现象与指纹 | 现象描述、结构化信号（status_code/IPs/hosts/pods/components） | POST /aggregated_event/list / 各 failure 接口 结果 |
| 4 根因分析与置信度 | 候选根因排序（置信度）、证据引用、反证排除 | 诊断结论 + 工具返回事实 |
| 5 处理建议 | 短期缓解 + 长期修复 + 验证步骤 | GET /failure_mode/{failure_mode_id} solution + 通用知识 |
| 6 关联信息 | failure_mode_ids、status_codes、历史案例ID、原始日志引用 | GET /failure_mode/status_code/{status_code} / POST /diagnosis_case/search |
| 7 生成元数据 | 生成时间、生成者、版本 | 系统字段 |

## 使用流程

1. 调用 latency-analysis / failure-code-analysis skill 完成诊断
2. 按本 Skill 七章节顺序逐一填充 JSON 片段
3. 组合为完整报告 JSON
4. 使用 references/REPORT_SCHEMA.json 校验（Pydantic/jsonschema 库）
5. 通过后端写入接口（或手动）沉淀为 diagnosis_case

详细流程见 [SKILL.md](SKILL.md)，Schema 定义见
[references/REPORT_SCHEMA.md](references/REPORT_SCHEMA.md)。
