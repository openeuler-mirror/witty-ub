# 故障码/通断诊断 HTTP 接口参数速查

本文档为 `failure-code-analysis` Skill 使用的 FastAPI 只读故障码类接口提供快速
参数参考。所有接口均为只读。真实 HTTP 路径与调用方式以本文件为准。

---

## 知识库与上下文（所有 Skill 共用）

`POST /log_kb/list`、`GET /log_kb/{kb_id}`、`POST /log_file/list/{kb_id}`、
`GET /task/{task_id}`、`GET /log_parse_result/options` 等见
`latency-analysis/references/TOOL_REFERENCE.md` 的对应条目。

---

## 时间窗口故障聚合

### `POST /log_failure_event_result/list_time_aggregated_failure_events`

**通断诊断广度扫描首选工具**。按时间窗口聚合所有故障码计数，快速定位
故障集中时段 / 识别周期性特征。

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `kb_id` | str | — | 必填 |
| `operation` | `"GET"` \| `"SET"` | None | 读写分开分析 |
| `interval` | `"second"` \| `"minute"` \| `"hour"` | `"minute"` | 粒度：尖峰=sec；长时=hour |
| `start_time` / `end_time` | str \| None | None | `YYYY-MM-DD HH:MM:SS` |
| `cluster_name` / `host` / `pod_ip` / `src_ip` / `dst_ip` | str \| None | None | 精确过滤 |
| `sort_by` | str | `"timestamp"` | 已内置（timestamp），诊断时序不改 |
| `sort_desc` | bool | False | False=升序，便于画时间线 |
| `page_num` / `page_cnt` | int | 1 / 10 | 长时段增大 page_cnt（建议 100） |

**返回关键字段**：`timestamp`（窗口起始时间）、各类错误码聚合计数。

---

## 源/目的 IP 维度聚合

### `POST /log_failure_event_result/list_src_dst_aggregated_failure_events`

按源/目的 IP 对聚合故障码，用于**定位主要故障路径**（哪个 IP 对最集中）。

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `kb_id` | str | — | 必填 |
| `operation` | `"GET"` \| `"SET"` | None | 读写分开分析 |
| `start_time` / `end_time` | str \| None | None | 用时间窗口识别出的故障窗口 |
| `cluster_name` / `host` / `pod_ip` / `src_ip` / `dst_ip` | str \| None | None | 精确过滤 |
| `sort_by` | str | `"all"` | `"all"`=综合；或具体错误码（如 `1004`、`1009`） |
| `sort_desc` | bool | True | 取 Top N，降序 |
| `page_num` / `page_cnt` | int | 1 / 10 | 诊断期建议 30~50 |

---

## Pod 维度聚合

### `POST /log_failure_event_result/list_pod_aggregated_failure_events`

按 Pod 维度聚合故障码，用于**故障域识别**：单点 vs 同 Host vs 同 Cluster
vs 全局均匀。

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `kb_id` | str | — | 必填 |
| `operation` | `"GET"` \| `"SET"` | None | 读写分开分析 |
| `start_time` / `end_time` | str \| None | None | 用阶段二识别的故障窗口 |
| `sort_by` | str | `"all"` | `"all"`=综合；或具体错误码（如 `1004`、`1009`） |
| `sort_desc` | bool | True | 取 Top N，降序 |
| `page_num` / `page_cnt` | int | 1 / 10 | 诊断期建议 30~50 |

> 该接口用 `sort_desc`（bool），**没有** `sort_order` 参数。

**返回关键字段**：`pod_name`、`host_name`、`cluster_name`、各类错误码聚合计数与占比。

---

## 错误码时间序列

### `POST /log_failure_event_result/metrics/err_code`

获取采样后的各错误码**频次时间序列**，定量比较爆发顺序 / 峰值 / 回落时间，
用于识别级联故障（A 先涨，B/C 随后涨 → A 可能是根因）。

> ⚠️ **采样透明原则**：引用结果时必须注明采样元数据。

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `kb_id` | str | — | 必填 |
| `operation` | `"GET"` \| `"SET"` | None | 读写分开分析 |
| `err_codes` | list[str] \| None | [] | 空=全量；建议传入 Top N 高频码 |
| `cluster_names` / `host_names` / `pod_names` | list[str] \| None | [] | 过滤 |
| `src_ip` / `dst_ip` | str \| None | None | IP 过滤 |
| `start_time` / `end_time` | str \| None | None | 时间范围 |
| `max_points` | int | 1000 | 1 ~ 5000 |

**返回关键字段**：每个 `err_code` 独立的 (timestamps, counts) 序列、
`sampling_metadata`（若存在）。

---

## Trace 级故障详情

### `POST /log_failure_event_result/list_trace_events`

**故障下钻核心工具**。按 status_code / cluster / host / pod / time 列出解析
后的 trace 级故障记录，包含 `failure_mode_id` 供 curated KB 查询。

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `kb_id` | str | — | 必填 |
| `operation` | `"GET"` \| `"SET"` | None | 读写分开分析 |
| `trace_ids` | list[str] \| None | None | 直接按 trace 查 |
| `status_codes` | list[str] \| None | [] | 空=全量；可指定重点码 |
| `cluster_names` / `host_names` / `pod_names` | list[str] \| None | [] | 过滤 |
| `src_ip` / `dst_ip` | str \| None | None | IP 过滤 |
| `start_time` / `end_time` | str \| None | None | 时间范围 |
| `is_anomalous` | bool \| None | 显式传 `true` | True=仅异常；False=正常；None=全部 |
| `sort_desc` | bool | True | 最新/严重优先 |
| `page_num` / `page_cnt` | int | 1 / 10 | 建议首次 50~100 |

> 该接口**没有** `log_id` 参数。

**返回关键字段**：
- `trace_id` → 传 `POST /log_failure_event_result/list_log_events`
- `status_code` → 传 `GET /failure_mode/status_code/{status_code}`
- `failure_mode_id` → 传 `GET /failure_mode/{failure_mode_id}`
- `src_ip`、`dst_ip`、`host`、`pod`、`cluster`、`timestamp`、`anomaly_score`

---

## 原始日志证据

### `POST /log_failure_event_result/list_log_events`

基于 trace_id 精准获取原始日志事件记录，是诊断的**第一手证据**。

> ⚠️ 单次最多传入 100 个 trace_id；超过时分批查询。

| 参数 | 类型 | 说明 |
|------|------|------|
| `trace_ids` | list[str] | **必填**，长度 1~100，来自 `list_trace_events` |
| `kb_id` | str | — | **必填**，限定知识库范围 |
| `log_id` | str \| None | 可选，指定单个 log_id 精确查找 |

**返回关键字段**：原始日志全文（含 `src=... dst=...`）、timestamp、trace_id、
status_code（与 trace 记录比对一致性）。

---

## Curated 故障知识库

### `GET /failure_mode/status_code/{status_code}`

快速查询**单个状态码**在 curated 知识库中的解释（症状 + 已知根因）。
`status_code` 为路径参数，例如 `-1002`、`-5`、`ERR_TIMEOUT`。

**重要边界**：
- 404 = 知识库未收录该代码 **≠** 该事件是正常的，必须用现场证据补充推断
- 非 404 结果仅为 curated 经验，仍需与现场数据比对确认

### `GET /failure_mode/{failure_mode_id}`

获取完整的故障模式详情（症状-根因-解决方案三件套 + 故障域分类 + 父子关系）。
`failure_mode_id` 为路径参数，来自 `POST /log_failure_event_result/list_trace_events`。

**返回关键字段**：`symptom`、`root_cause`、`solution`、`failure_domain`
（网络 / Pod / Host / Cluster / 组件）、父/子 `failure_mode` 关系。

---

## 历史案例

### `POST /diagnosis_case/search` / `GET /diagnosis_case/{case_id}`

`fault_type` 用 `"connectivity"`；`status_codes` 为用户提到或阶段四识别到的
错误码列表；`failure_mode_ids` 来自 `list_trace_events`；故障域信号
`src_ips`/`dst_ips`/`hosts`/`pods`/`clusters`；`log_keywords` 用原始日志关键
字眼（如 "Connection refused"）。完整参数表见
`latency-analysis/references/TOOL_REFERENCE.md`。