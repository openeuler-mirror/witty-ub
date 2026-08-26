# latency-analysis

KVC 分布式缓存**时延异常诊断**Skill。基于 FastAPI 只读 HTTP 接口，
引导 Agent 按**四阶段流程**调用接口：

1. **数据准备**：`POST /log_kb/list` → `POST /log_file/list/{kb_id}` → `GET /task/{task_id}` → `GET /log_parse_result/options`
2. **广度扫描**：`POST /aggregated_event/list`（P99 IP 对聚合，Top N 高时延）
3. **时间窗口**：`POST /aggregated_event/list_time_window`（定位延迟升高窗口）
4. **深度下钻**：`POST /log_parse_result/list` + `POST /log_parse_result/metrics/latency`

适用场景：P99/P95/AVG 延迟升高、GET/SET 慢查询、特定 IP 对/Host/Pod/集群时延异常。

详细流程见 [SKILL.md](SKILL.md)，接口参数见 [references/TOOL_REFERENCE.md](references/TOOL_REFERENCE.md)。
