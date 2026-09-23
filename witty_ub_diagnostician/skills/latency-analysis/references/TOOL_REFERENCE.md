# 时延诊断 HTTP 接口参数速查

本文档为 `latency-analysis` Skill 使用的 FastAPI 只读时延类接口提供快速参数参考。
所有接口均为只读。真实 HTTP 路径与调用方式以本文件为准。

## 知识库与上下文（所有 Skill 共用）

### `POST /log_kb/list`

发现可用的日志知识库。分页浏览，优先按创建时间倒序。

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `name` | str \| None | None | 名称模糊匹配 |
| `description` | str \| None | None | 描述模糊匹配 |
| `created_at_start` | str \| None | None | 起始时间 `YYYY-MM-DD HH:MM:SS` |
| `created_at_end` | str \| None | None | 结束时间 |
| `created_sorted_desc` | bool | True | 创建时间倒序 |
| `page_num` | int | 1 | ≥ 1 |
| `page_cnt` | int | 20 | 1 ~ 100 |

### `GET /log_kb/{kb_id}`

查询单个知识库的完整元信息。`kb_id` 来自 `POST /log_kb/list` 的结果。

### `POST /log_file/list/{kb_id}`

列出知识库中的日志文件，重点关注解析状态与故障计数。

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `page_num` | int | 1 | ≥ 1 |
| `page_cnt` | int | 20 | 1 ~ 100 |

返回中的 `overall_status` 是文件关联任务的聚合状态，日志文件 `id` 即后续请求的 `log_id`。

### `GET /task/{task_id}`

根据 `task_id` 查看解析进度和报告。`task_id` 来自 `POST /log_file/list/{kb_id}`。

### `GET /log_parse_result/options`

获取已解析日志中实际存在的 cluster / host / pod 值。**禁止臆测**名称。
`kb_id` 作为查询参数传入，必填，用于限定范围。

---

## 定位定界漏斗（轻量三接口，Agent 首选路径）

**组件定位 → 节点定界 → 证据下钻** 的标准漏斗；响应字段最小化，
按需 include，面向 LLM Agent 低 token 消耗设计。

### 第 1 层：`POST /stats/stages`（组件定位入口）

一次调用返回**该 operation 的互斥主导问题分类**（每条 trace 按
winner-take-all 归入唯一桶，Σ各桶 trace_cnt = sample_cnt），回答"哪个组件
出了问题"。GET 与 SET 是**两套独立口径**（读路径 8 桶 / 写路径 5 桶，key 不
重叠）：需分别调用两次，禁止跨 operation 混合归桶。

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `kb_id` | str | — | 必填 |
| `log_id` | str \| None | None | 精确到单个日志文件 |
| `operation` | `"GET"` \| `"SET"` | `"GET"` | GET→8 桶；SET→5 桶；其他值返回空 items + note |
| `start_time` / `end_time` | str \| None | None | `YYYY-MM-DD HH:MM:SS` |
| `sample_cap` | int | 1000 | 采样上限：异常 trace 全量 + top 慢正常合并去重（50~5000） |

**返回 `result` 关键字段**：

- `sample_cnt` / `truncated`：实际采样数与是否截断
- `items[]`（固定顺序，零计数桶照常返回；GET 8 个 / SET 5 个）：
  `{key, name, trace_cnt, success_cnt, fail_cnt, p50_ms, p90_ms, max_ms, client_p50_ms, client_p90_ms, metric_name, action, note, top_traces[]}`
  - GET 桶 key：`rpc_network` / `rpc_queue` / `query_meta` / `urma` /
    `data_worker` / `cross_window` / `residual` / `urma_timeout`
  - SET 桶 key：`set_urma_timeout` / `set_no_evidence` / `set_residual` /
    `set_client` / `set_worker`（判定顺序即优先级：超时文本 → 数据面未观测 →
    未解释残差 → SDK 段 / Worker 端比大小）
  - **双口径读法**：`fail_cnt` 为异常 trace 数（`is_anomalous=true`，判定
    通断/失败面）；`success_cnt` 为正常但落入该桶的慢 trace 数（判定时延面）。
    通断问题看 fail_cnt 高的桶，时延问题看 trace_cnt/p90 高的桶
  - `p50_ms`/`p90_ms`/`max_ms` 为该桶**主阶段证据耗时**分位（`metric_name`
    标注口径：普通瓶颈=winner 维度耗时；URMA 超时=日志 elapsedMs 近似；
    SET·数据面未观测=Client 总时延）；`client_*` 为桶内 trace Client 总时延对照
  - `action`：该类问题的治理指引文案（可直接进报告建议段）
  - **`top_traces[]` 桥接**：`{trace_id, evidence_ms, client_ms}`，桶内证据
    耗时 Top-5，trace_id 直接用于 `/trace/list` 批查或 `GET /trace/{id}` 下钻
- `note`：样本集/口径说明；SET 侧额外列出**被剔除维度及原因**（实测口径）

**SET 侧口径与剔除维度**（node48 实测 3638 条写路径行）：

- 可用：`sdk_processing_us`（客户端 SDK 段，含等待数据面返回）与
  `local_worker_internal_us`（Worker 端写处理），二者之和 ≡ `total_latency_us`；
  另有 `worker_access_latency_us` 用于判断数据面是否被观测
- 剔除：`urma_processing_us` / `create_latency` / `publish_latency` /
  `w2w_urma_latency` 在当前解析路径恒为空；`c2w_urma_latency` 恒 ≈ 总时延，
  无额外信息量；RPC 细分列在 SET 侧几乎全空
- 实测分布（`set_client` 2467 / `set_no_evidence` 1164 / `set_worker` 6 /
  `set_residual` 1 / `set_urma_timeout` 0），故 SET 侧**不做** CREATE/PUBLISH
  分段归因；`urma_link_latency` 仅作附注，不参与归桶

**分诊规则**：先看 fail_cnt 最大桶（通断优先）；无异常再按 trace_cnt × p90_ms
排序看时延主导桶；`urma_timeout` / `set_urma_timeout` 桶非零时优先（已观测
URMA_WAIT_TIMEOUT）。归因子集为空（note 说明）时降级走 `/trace/list` 按总时延粗筛。

### 第 2 层：`POST /trace/list`（trace 粗筛 / 节点定界）

**默认最小响应**：每条仅 4 基础字段
`{trace_id, total_latency_ms, is_anomalous, operation}`；附加块按 `include`
显式请求，未指定的块不出现在响应里（非 null 占位）。

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `kb_id` | str | — | 必填 |
| `log_id` | str \| None | None | 精确到单个日志文件 |
| `trace_ids` | list[str] \| None | None | 批量查询（承接 `/stats/stages` 的 top_traces） |
| `operation` | `"GET"` \| `"SET"` \| None | None | 操作类型过滤 |
| `is_anomalous` | bool \| None | None | **时延侧口径**：True 仅异常，False 仅正常 |
| `status_codes` | list[str] \| None | None | **故障侧语义**：返回挂有任一指定故障码的 trace（触发故障主源路径） |
| `start_time` / `end_time` | str \| None | None | `YYYY-MM-DD HH:MM:SS` |
| `pod_ip` / `host` / `cluster_name` / `src_ip` / `dst_ip` | str \| None | None | 过滤（pod_ip/host/cluster 为时延侧；src/dst 双源） |
| `sort_by` | `"total_latency"` \| `"failure_cnt"` \| `"timestamp"` | `"total_latency"` | `failure_cnt` 走故障主源（DB 侧聚合下推） |
| `sort_order` | `"desc"` \| `"asc"` | `"desc"` | 排序方向 |
| `page_cnt` | int | 20 | 每页条数 ≤500 |
| `page_num` | int | 1 | 页码 |
| `include` | list | `[]` | `"failure_codes"`=故障码聚合块；`"topology"`=拓扑块（pod_ips/host/src_ip/dst_ip） |

**响应条目字段**（按请求组合）：

- 基础：`trace_id` / `total_latency_ms` / `is_anomalous` / `operation`
- include=failure_codes：`failure_codes: [{code, cnt}]` + 故障主源路径另有
  `failure_cnt`（无故障记录的 trace 得 `[]`，不丢条；纯故障 trace 时延侧字段为 null）
- include=topology：`pod_ips`（**去重集合，无跳序**；逐跳顺序数据层未保留）/
  `host` / `src_ip` / `dst_ip`（链路首末锚点，节点定界用）

**sort_by 路径选择**：时延粗筛用默认 `total_latency`（单查询最快路径）；
"哪些 trace 挂了故障码" 用 `sort_by=failure_cnt` 或传 `status_codes`
（unnest → GROUP BY → 排序分页全部 DB 侧完成，10W~50W 行规模安全）。

> ⚠️ **`total > 500` 使用纪律**：`total` 为命中 trace 总数；当 `total > 500`
> 时**禁止翻页遍历**，必须收窄过滤（时间窗 / is_anomalous / status_codes /
> pod_ip）或只取 Top（默认第一页即按排序键 Top-N），或回到 `/stats/stages`
> 看聚合视图。

### 第 3 层：`GET /trace/{trace_id}`（代表 trace 证据下钻）

单 trace 完整画像（时延 + 拓扑 + 故障码 + 时间戳），用于确认代表 trace 的
证据链。查询参数：`kb_id`（必填）、`log_id`（可选）、`include`（可选，
同上）。返回 `result`：基础 4 字段 + `failure_codes` + 拓扑 4 字段 +
`timestamp`（取故障侧最早日志时间，无故障记录回退解析侧时间）。
trace 不存在时 404。

### 单维度统计：`POST /stats/error_codes|pods|links|heatmap`

四个统计端点共用请求骨架（`kb_id` 必填；`log_id`/`operation`/`start_time`/
`end_time` 可选；`top_n` 默认 20 上限 100），DB 侧全量精确聚合，响应统一
`{total, items, note}`，不受 `/trace/list` 分页截断影响：

| 端点 | `items[]` 字段 | 排序 | 联动下钻 |
|------|--------------|------|---------|
| `/stats/error_codes` | `status_code`、`trace_cnt`、`event_cnt`（日志级事件数，双源缺一为 `null`） | `trace_cnt` 降序 | Top 码 → `/trace/list {status_codes}` |
| `/stats/pods` | `pod_ip`、`host`、`trace_cnt`、`fault_trace_cnt` | `fault_trace_cnt` 降序 | Top Pod → `/trace/list {pod_ip}` |
| `/stats/links` | `src_ip`、`dst_ip`、`trace_cnt`、`fault_trace_cnt` | `fault_trace_cnt` 降序 | 源目对 → `/trace/list {src_ip}/{dst_ip}`；两侧 IP 多为空时 `total=0` 属数据事实 |
| `/stats/heatmap` | `window_start`、`fault_trace_cnt`（另含 `window_size`） | 时间升序 | 峰值窗口 → 各接口 `start_time`/`end_time` |

heatmap `window_size` 可选 `1m`/`10m`/`1h`，缺省自动选窗（跨度 ≤2h→1m、
≤48h→10m、否则 1h；自动模式槽位数 >240 逐级放大，显式指定不放大仅 note
提示）。`note` 字段说明口径（如 `event_cnt` 双源口径、pods 各 Pod 计数一次）。

---

## IP 对聚合

### `POST /aggregated_event/list`

**时延广度扫描首选工具**。按源/目的 IP 对聚合统计延迟，默认按
`total_latency` 降序，快速定位高延迟 IP 对。

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `kb_id` | str | — | 必填 |
| `log_id` | str \| None | None | 当前调查对应某日志文件时必传该文件 `id` |
| `operation` | `"GET"` \| `"SET"` | — | 读写分开分析 |
| `start_time` / `end_time` | str \| None | None | `YYYY-MM-DD HH:MM:SS` |
| `src_ip` / `dst_ip` | str \| None | None | 支持模糊查询 |
| `stat_type` | `"p99"` \| `"p95"` \| `"ave"` \| `"min"` \| `"max"` | 显式传 `"p99"` | 时延异常首选 P99 |
| `sort_fields` | list | `[{"field":"total_latency","order":"desc"}]` | `field` 非空、`order` 为 asc/desc |
| `page_num` / `page_cnt` | int | 1 / 10 | 扫描期建议 50 |

**返回关键字段**：`id`（= `aggregated_event_id`）、`src_ip`/`dst_ip`、
`total_latency` 及各分量延迟、`request_count`/`anomalous_count`。

---

## 时间窗口

### `POST /aggregated_event/list_time_window`

按时间窗口聚合延迟，用于定位延迟升高/恢复的具体时间点。

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `kb_id` | str | — | 必填 |
| `operation` | `"GET"` \| `"SET"` | — | 读写分开分析 |
| `src_ip` / `dst_ip` | str \| None | None | 限定 IP 对 |
| `start_time` / `end_time` | str \| None | None | 时间范围 |
| `interval` | str | `"minute"` | `second`/`minute`/`hour`（后端也接受整数秒） |
| `stat_type` | str | 显式传 `"p99"` | p99/p95/ave/min/max |
| `sort_by` | `"start_time"` \| `"total_latency"` | `"start_time"` | 诊断时序选 start_time |
| `sort_order` | `"asc"` \| `"desc"` | `"asc"` | 便于画时间线 |
| `page_num` / `page_cnt` | int | 1 / 100 | 长时段增大 page_cnt |

> 该接口没有 `log_id` 参数。

---

## 异常日志详情

### `POST /log_parse_result/list`

**时延下钻核心工具**。按聚合事件、IP、trace_id、host 等维度列出解析
后的日志记录，包含各时延分量与异常标记。

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `kb_id` | str | — | 必填 |
| `log_id` | str \| None | None | 当前调查对应某日志文件时必传 |
| `operation` | `"GET"` \| `"SET"` | — | 读写分开分析 |
| `aggregated_event_id` | str \| None | None | 来自 `POST /aggregated_event/list` 的 id |
| `trace_id` / `trace_ids` | str / list[str] \| None | None | 精确查询某（些）请求的全链路 |
| `host` / `pod_ip` / `cluster_name` | str \| None | None | 先用 `GET /log_parse_result/options` 确认 |
| `src_ip` / `dst_ip` | str \| None | None | 按 IP 对过滤 |
| `start_time` / `end_time` | str \| None | None | 时间范围 |
| `is_anomalous` | bool \| None | 显式传 `true` | True=仅异常；False=正常；None=全部 |
| `sort_fields` | list \| None | None | 排序配置 |
| `page_num` / `page_cnt` | int | 1 / 10 | 建议首次 50 |

> 该接口**没有** `exclude_normal`、`sort_by`、`sort_order`、`error_priority`
> 参数，不要臆造。

**返回关键字段**：`trace_id`、时延分量（`total_latency`、`urma_total_latency`、
`worker_query_meta_latency` 等）、`anomaly_components`、`src_ip`/`dst_ip`/`host`/
`pod`/`cluster`、`anomaly_score`。

---

## 指标时间序列

### `POST /log_parse_result/metrics/latency`

获取采样后的延迟时间序列，用于绘制趋势图与定量分析。

> ⚠️ **采样透明原则**：描述结果时必须注明 `sample_mode`、`max_points` 与
> `sampling_metadata`，采样后数据不代表完整原始点集。

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `kb_id` | str | — | 必填 |
| `log_id` | str | — | **必传**（= 阶段一 `log_file.id`），不得省略 |
| `operation` | `"GET"` \| `"SET"` | — | 读写分开观察 |
| `start_time` / `end_time` | str \| None | None | 时间范围 |
| `host` / `src_ip` / `dst_ip` / `pod_ip` | str \| None | None | 过滤维度 |
| `sample_mode` | `"none"` `"max"` `"avg"` `"min"` `"p99"` `"p95"` `"p9999"` | `"p99"` | 降采样策略 |
| `max_points` | int | 1000 | 1 ~ 5000；`-1` = 全量（仅确需完整数据时用） |

---

## 历史案例

### `POST /diag_case_library/search`（默认通道）

从**已人工确认**的超节点诊断案例库中检索相似指纹，用于提出候选根因假设。

> ⚠️ 结果仅作**参考假设**，必须用当前现场数据验证。
> 只返回 `status=confirmed` 的案例；未经确认的旧表案例见下方降级通道。

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `fault_type` | `"latency"` \| `"connectivity"` \| `"mixed"` \| `"unknown"` | None | 本 Skill 用 `latency` |
| `operation` | `"GET"` \| `"SET"` \| `"N/A"` | None | 服务端过滤，GET/SET 一提交即隔离 |
| `log_type` | `"KVCache"` \| `"UBSocket"` | None | 日志类型过滤 |
| `kb_id` | str | — | **可空**；留空 = 跨知识库召回（`kb_id` 仅作来源标注） |
| `status_codes` / `failure_mode_ids` | list[str] \| None | [] | 信号量 |
| `src_ips` / `dst_ips` / `hosts` / `pods` / `clusters` | list[str] \| None | [] | 故障域 |
| `latency_components` | list[str] \| None | [] | 桶 key，如 `set_client`（见 FEATURE_SPEC 的桶表） |
| `log_keywords` | list[str] \| None | [] | 关键日志短语 |
| `min_confidence` | float \| None | None | 置信度阈值 0~1 |
| `include_status` | list[str] | `["confirmed"]` | 纳入检索的状态集合，一般不改 |
| `page_num` / `page_cnt` | int | 1 / 10 | — |

### `GET /diag_case_library/{case_id}`

按 ID 获取完整案例详情（含证据锚点、根因机理、分步处置、验证闭环）。`case_id` 来自
`POST /diag_case_library/search` 的结果。

### 降级通道：`POST /diagnosis_case/search` / `GET /diagnosis_case/{case_id}`

旧表，**无人工确认关卡**、内容物只有现象/根因/建议三段，且 `kb_id` 必填。
仅在确认案例库无结果时兜底使用；引用时必须标注"来源=diagnosis_case（未经人工确认）"。
