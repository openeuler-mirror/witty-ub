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
| `parse_status` | str \| None | None | 可传 `"SUCCESS"` / `"RUNNING"` / `"FAILED"` 过滤 |
| `page_num` | int | 1 | ≥ 1 |
| `page_cnt` | int | 20 | 1 ~ 100 |

返回中的日志文件 `id` 即后续请求的 `log_id`。

### `GET /task/{task_id}`

根据 `task_id` 查看解析进度和报告。`task_id` 来自 `POST /log_file/list/{kb_id}`。

### `GET /log_parse_result/options`

获取已解析日志中实际存在的 cluster / host / pod 值。**禁止臆测**名称。
`kb_id` 作为查询参数传入，可选以限定范围。

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

### `POST /diagnosis_case/search`

从历史沉淀的诊断案例库中检索相似指纹，用于提出候选根因假设。

> ⚠️ 结果仅作**参考假设**，必须用当前现场数据验证。

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `fault_type` | `"latency"` \| `"connectivity"` \| `"mixed"` \| `"unknown"` | None | 本 Skill 用 `latency` |
| `kb_id` | str \| None | None | 限定知识库 |
| `status_codes` / `failure_mode_ids` | list[str] \| None | [] | 信号量 |
| `src_ips` / `dst_ips` / `hosts` / `pods` / `clusters` | list[str] \| None | [] | 故障域 |
| `latency_components` | list[str] \| None | [] | 如 `["worker_query_meta_latency"]` |
| `log_keywords` | list[str] \| None | [] | 关键日志短语 |
| `min_confidence` | float \| None | None | 置信度阈值 0~1 |
| `page_num` / `page_cnt` | int | 1 / 10 | — |

### `GET /diagnosis_case/{case_id}`

按 ID 获取完整历史案例详情（含证据、根因、解决方案）。`case_id` 来自
`POST /diagnosis_case/search` 的结果。