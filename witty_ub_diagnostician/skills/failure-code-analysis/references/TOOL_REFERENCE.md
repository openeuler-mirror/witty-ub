# 故障码/通断诊断 HTTP 接口参数速查

本文档为 `failure-code-analysis` Skill 使用的 FastAPI 只读故障码类接口提供快速
参数参考。所有接口均为只读。真实 HTTP 路径与调用方式以本文件为准。

---

## 知识库与上下文（所有 Skill 共用）

`POST /log_kb/list`、`GET /log_kb/{kb_id}`、`POST /log_file/list/{kb_id}`、
`GET /task/{task_id}`、`GET /log_parse_result/options` 等见
`latency-analysis/references/TOOL_REFERENCE.md` 的对应条目。

---

## 定位定界漏斗（轻量两接口，通断诊断首选路径）

**组件定位 → 故障 trace 粗筛** 的标准漏斗；响应字段最小化，面向 LLM Agent
低 token 消耗设计。完整参数表见
`latency-analysis/references/TOOL_REFERENCE.md`，此处只列通断侧用法。

### 第 1 层：`POST /stats/stages`（组件定位入口）

一次调用返回**该 operation 的**互斥主导问题分类（每条 trace 按
winner-take-all 归入唯一桶），回答"哪个组件出了问题"。GET 与 SET 是两套独立
口径（GET 8 桶 / SET 5 桶，key 不重叠）：需分别调用，禁止跨 operation 混合归桶。

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `kb_id` | str | — | 必填 |
| `log_id` | str \| None | None | 精确到单个日志文件 |
| `operation` | `"GET"` \| `"SET"` | `"GET"` | GET→8 桶；SET→5 桶；其他值返回空 items + note |
| `start_time` / `end_time` | str \| None | None | `YYYY-MM-DD HH:MM:SS` |
| `sample_cap` | int | 1000 | 采样上限（50~5000）；异常 trace 全量保留 |

**通断侧读法**：

- `items[]` 中 `fail_cnt` 为该桶异常 trace 数（`is_anomalous=true`）——
  **通断/失败面的核心信号**，fail_cnt 最大的桶优先排查
- `urma_timeout` / `set_urma_timeout` 桶非零时优先（已观测 URMA_WAIT_TIMEOUT）
- `top_traces[]`：`{trace_id, evidence_ms, client_ms}` 桶内 Top-5——
  trace_id 直接作为**代表 trace**，供下一步下钻或传
  `list_log_events` 取原始日志全文

归因子集为空（桶全 0，note 有说明）时降级走 `/trace/list`
按 `sort_by=failure_cnt` 粗筛。

### 第 2 层：`POST /trace/list`（故障 trace 粗筛 / 代表 trace 批查）

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `kb_id` | str | — | 必填 |
| `log_id` | str \| None | None | 精确到单个日志文件 |
| `trace_ids` | list[str] \| None | None | 批量查询（承接 `/stats/stages` 的 top_traces） |
| `status_codes` | list[str] \| None | None | **故障侧语义**：只返回挂有任一指定故障码的 trace |
| `sort_by` | `"failure_cnt"` \| `"total_latency"` \| `"timestamp"` | `"total_latency"` | 故障粗筛用 `failure_cnt`（DB 侧聚合，10W~50W 行规模安全） |
| `include` | list | `[]` | `"failure_codes"`=故障码块；`"topology"`=拓扑块 |
| `page_cnt` / `page_num` | int | 20 / 1 | 每页条数 ≤500 |

**响应条目字段**（按请求组合）：

- 基础：`trace_id` / `total_latency_ms` / `is_anomalous` / `operation`
- include=failure_codes：`failure_codes: [{code, cnt}]`——页内即得故障码
  画像，无需再查聚合接口；无故障记录的 trace 得 `[]` 不丢条
- include=topology：`src_ip`/`dst_ip`（链路首末锚点）+ `host` +
  `pod_ips`（去重集合，无跳序）——故障域初判（单点 vs 同 Host vs 全局）

> ⚠️ **`total > 500` 使用纪律**：`total` 为命中 trace 总数；当 `total > 500`
> 时**禁止翻页遍历**，必须收窄过滤（status_codes / 时间窗 / pod_ip）或只取
> 排序后第一页 Top-N，或回到 `/stats/stages` 看聚合视图。

代表 trace 选定后：`POST /log_failure_event_result/list_log_events` 取
原始日志全文（第一手证据），再进 curated 知识库
（`GET /failure_mode/status_code/{code}`）比对。

### 单维度统计：`POST /stats/error_codes|pods|links|heatmap`

**通断统计首选路径**（替代下方老聚合接口的 Agent 侧用法）。四端点共用
请求骨架（`kb_id` 必填；`log_id`/`operation`/`start_time`/`end_time` 可选；
`top_n` 默认 20 上限 100），DB 侧全量精确聚合，响应统一 `{total, items, note}`：

| 端点 | `items[]` 字段 | 联动下钻 |
|------|--------------|---------|
| `/stats/error_codes` | `status_code`、`trace_cnt`（trace 级）、`event_cnt`（日志级事件数，双源缺一为 `null`） | Top 码 → `/trace/list {status_codes}` 或 `GET /failure_mode/status_code/{code}` |
| `/stats/pods` | `pod_ip`、`host`、`trace_cnt`、`fault_trace_cnt` | Top Pod → `/trace/list {pod_ip}` |
| `/stats/links` | `src_ip`、`dst_ip`、`trace_cnt`、`fault_trace_cnt` | 源目对 → `/trace/list {src_ip}/{dst_ip}`；两侧 IP 多为空时 `total=0` 属数据事实 |
| `/stats/heatmap` | `window_start`、`fault_trace_cnt`（另含 `window_size`） | 峰值窗口 → 各接口 `start_time`/`end_time` |

heatmap 缺省自动选窗（跨度 ≤2h→1m、≤48h→10m、否则 1h；自动模式 >240 槽
逐级放大），显式 `window_size` 可选 `1m`/`10m`/`1h`。

> 下方老聚合接口（时间窗口 / 源目对 / Pod 维度）继续保留服务前端看板；
> Agent 侧统计一律优先上表 `/stats/*`（同请求骨架、响应形状，无分页）。

---

## 时间窗口故障聚合

### `POST /log_failure_event_result/list_time_aggregated_failure_events`

**通断诊断广度扫描首选工具**。按时间窗口聚合所有故障码计数，快速定位
故障集中时段 / 识别周期性特征。

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `kb_id` | str | — | 必填 |
| `log_id` | str \| None | None | 精确到单个日志文件；为空=知识库下全部日志 |
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
| `log_id` | str \| None | None | 精确到单个日志文件；为空=知识库下全部日志 |
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
| `log_id` | str \| None | None | 精确到单个日志文件；为空=知识库下全部日志 |
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

### `POST /diag_case_library/search` / `GET /diag_case_library/{case_id}`（默认通道）

只返回 `status=confirmed` 的**已人工确认**案例。`fault_type` 用 `"connectivity"`；
`status_codes` 为用户提到或阶段四识别到的错误码列表；`failure_mode_ids` 来自
`list_trace_events`；故障域信号 `src_ips`/`dst_ips`/`hosts`/`pods`/`clusters`；
`log_keywords` 用原始日志关键字眼（如 "Connection refused"）。
`operation` 是服务端过滤字段（GET/SET 一提交即隔离）；`kb_id` 可空 = 跨知识库召回。
完整参数表见 `latency-analysis/references/TOOL_REFERENCE.md`。

### 降级通道：`POST /diagnosis_case/search` / `GET /diagnosis_case/{case_id}`

旧表，**无人工确认关卡**、内容物只有现象/根因/建议三段，且 `kb_id` 必填。
仅在确认案例库无结果时兜底使用；引用必须标注"未经人工确认"。