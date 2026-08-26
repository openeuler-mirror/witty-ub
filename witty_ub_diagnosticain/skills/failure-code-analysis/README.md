# failure-code-analysis

KVC 分布式缓存**故障码 / 通断故障诊断**Skill。基于 FastAPI 只读 HTTP 接口，
引导 Agent 按**五阶段流程**调用接口：

1. **数据准备**：`POST /log_kb/list` → `POST /log_file/list/{kb_id}` → `GET /task/{task_id}` → `GET /log_parse_result/options`
2. **时间定位**：`POST /log_failure_event_result/list_time_aggregated_failure_events`（分钟级窗口，定位故障集中时段）
3. **故障域识别**：`POST /log_failure_event_result/list_pod_aggregated_failure_events`（Top N Pod，单点/Host/集群/全局分布）
4. **量化 + 下钻**：`POST /log_failure_event_result/metrics/err_code` + `POST /log_failure_event_result/list_trace_events` + `POST /log_failure_event_result/list_log_events`
5. **知识解读**：`GET /failure_mode/status_code/{status_code}` + `GET /failure_mode/{failure_mode_id}`

适用场景：ERR_xxx / 负值状态码、请求失败率升高、已知 status_code/failure_mode_id 查询含义、
Pod/Host/Cluster 报连接失败或 trace 故障。

详细流程见 [SKILL.md](SKILL.md)，接口参数见 [references/TOOL_REFERENCE.md](references/TOOL_REFERENCE.md)。

与 `latency-analysis` 的区别：本 Skill 关注**非零返回码 / 连接失败**，
latency-analysis 关注**延迟升高但返回码为 0 的慢查询**。
