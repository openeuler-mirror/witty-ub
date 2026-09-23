# BRPC 组件故障诊断 HTTP 接口参数速查

本文档为 `brpc-diagnosis` Skill 使用的 FastAPI 只读 BRPC 诊断接口提供快速
参数参考。所有接口均为只读 GET。

## 通用调用约定

- 所有 BRPC 查询接口都是 `GET`；时间参数必须使用 UTC+8 字符串
  `YYYY-MM-DD HH:MM:SS`，作为 query 参数传入
  （用 `curl --get --data-urlencode`）。
- BRPC 诊断以 `batch_id` 为主键（不是 `kb_id`）。
- `component` 只能是 `ubsocket`、`umq`、`urma`；接受 `component` 过滤的接口
  仅有 `interface-timeline` 和 `summary`。`pod-events`、`thread-events`、
  `abnormal-threads`、`hits` 以及三个详情接口都**没有** `component` 参数，
  不得臆造。
- `window_size` 取值按接口区分：
  - `interface-timeline`、`abnormal-threads/{thread_key}`：`10s`、`1m`、`10m`、`1h`
  - `pod-events`、`thread-events`：`1s`、`1m`、`1h`
  - `summary` 的 `peak_window.window_size` 由服务端按跨度自动选窗
    （≤10min→10s、≤2h→1m、否则 1h），不接受 `window_size` 参数
- `sort_order` 只能是 `asc` 或 `desc`；使用 `sort_field`/`sort_direction`
  时必须一一对应。
- `page_num` ≥ 1；`page_cnt` 在 1 到 1000 之间（诊断期建议 ≤ 100）。
- `event_id` 与 `thread_key` 是 64 位小写十六进制字符串；详情查询必须把
  列表返回的 `event_id` / `thread_key`、`window_start_time`、
  `window_end_time`、`pod_ip`、`thread_id` 原样回传，不得改动或省略
  （它们是完整分组键的一部分，缺失或改动能导致详情查询失败）。

---

## 批次定位

### `GET /brpc-diagnosis/task/{task_id}/batch`

用户给 `task_id` 时获取 `batch_id`。`task_id` 为路径参数。

### `GET /brpc-diagnosis/batch/{batch_id}`

核验批次元数据：schema、覆盖时间（`start_time`/`end_time`）、`hit_count`。
`hit_count=0` 时说明批次没有导入命中。

---

## 全局画像（summary）

### `GET /brpc-diagnosis/batch/{batch_id}/summary` / `GET /brpc-diagnosis/knowledge/{kb_id}/summary`

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `start_time` / `end_time` | str \| None | 批次/kb 全域 | `YYYY-MM-DD HH:MM:SS`，**可选**，缺省为全域 |
| `component` | `"ubsocket"` \| `"umq"` \| `"urma"` \| None | None | 聚焦单组件 |
| `top_n` | int | 10 | 上限 50 |

**返回六块**：`hit_count` / `time_range`（实际查询范围）/ `components[]`
（组件命中分布，含 `pct`）/ `top_pods[]` / `top_failure_modes[]` /
`peak_window`（峰值单窗：最高命中 10s/1m/1h 窗口，自动选窗）。

> summary 只给峰值单窗不给时间序列；需要趋势/尖峰轮廓时用
> `interface-timeline`。

---

## 阶段二：调查入口

### 全局趋势：`GET /brpc-diagnosis/batch/{batch_id}/interface-timeline`

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `batch_id` | str | — | 必填（路径参数） |
| `window_size` | str | `"1m"` | `10s`/`1m`/`10m`/`1h`；瞬时尖峰用 `10s`，长时用 `10m`/`1h` |
| `start_time` / `end_time` | str | 批次范围 | `YYYY-MM-DD HH:MM:SS` |
| `component` | str \| None | None | `ubsocket`/`umq`/`urma` |

用途：识别命中突增的时间窗口、对比不同组件的命中模式、与用户报告的
故障时间对齐。

### Pod 维度聚合：`GET /brpc-diagnosis/batch/{batch_id}/pod-events`

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `batch_id` | str | — | 必填（路径参数） |
| `window_size` | str | `"1m"` | 仅 `1s`/`1m`/`1h` |
| `start_time` / `end_time` | str | — | 故障窗口 |
| `pod_ip` / `pod_name` | str \| None | None | 过滤 |

**返回重点字段**：`event_id`（详情查询必需）、`pod_ip`、
`window_start_time`/`window_end_time`（故障域定位）、
`interface_hits[].interface_hit_count`（各接口命中次数与严重程度）。

### 线程维度聚合：`GET /brpc-diagnosis/batch/{batch_id}/thread-events`

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `batch_id` | str | — | 必填（路径参数） |
| `window_size` | str | `"1m"` | 仅 `1s`/`1m`/`1h` |
| `start_time` / `end_time` | str | — | 故障窗口 |
| `pod_ip` | str \| None | None | 过滤 |

**返回重点字段**：`event_id`、`thread_id`（详情查询必需）、`pod_ip`、
`interface_hits[].interface_hit_count`。

### 异常线程排行：`GET /brpc-diagnosis/batch/{batch_id}/abnormal-threads`

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `batch_id` | str | — | 必填（路径参数） |
| `start_time` / `end_time` | str | — | 故障窗口 |
| `pod_ip` | str \| None | None | 过滤 |
| `search` | str \| None | None | 模糊匹配 thread_id / pod_ip / pod_name |

返回按 `total_interface_hit_count` 降序；关注 `first_hit_time` 到
`last_hit_time` 的持续时间；`thread_key` 是详情查询必需。

---

## 阶段三：详情下钻

### Pod 事件详情：`GET /brpc-diagnosis/batch/{batch_id}/pod-events/{event_id}`

| 参数 | 说明 |
|------|------|
| `event_id` | 阶段二返回 |
| `window_start_time` / `window_end_time` | 列表返回值**原样传回** |
| `pod_ip` | 列表返回值**原样传回** |

**返回内容**：`interface_hits`（接口级命中统计）、`failure_modes`
（命中的故障模式及次数）、`failure_graph`（故障关系图，`directly_hit=true`
才是直接命中）、`hits`（原始命中日志）。

### 线程事件详情：`GET /brpc-diagnosis/batch/{batch_id}/thread-events/{event_id}`

| 参数 | 说明 |
|------|------|
| `event_id` | 阶段二返回 |
| `window_start_time` / `window_end_time` / `pod_ip` / `thread_id` | 列表返回值**原样传回** |

### 异常线程详情：`GET /brpc-diagnosis/batch/{batch_id}/abnormal-threads/{thread_key}`

| 参数 | 类型 | 说明 |
|------|------|------|
| `thread_key` | str | 阶段二返回（路径参数） |
| `pod_ip` / `thread_id` | str | 列表返回值**原样传回** |
| `window_size` | str | `10s`/`1m`/`10m`/`1h`（默认 `1m`） |
| `start_time` / `end_time` | str | 调查时间范围 |

**返回内容**：线程级接口时间趋势、故障模式命中详情、故障关系图、
分页命中日志。

### 命中日志查询：`GET /brpc-diagnosis/batch/{batch_id}/hits`

| 参数 | 类型 | 说明 |
|------|------|------|
| `batch_id` | str | 必填（路径参数） |
| `pod_ip` | str | **必填** |
| `thread_id` | int | **必填**，整数 |
| `start_time` / `end_time` | str | 时间范围 |
| `pod_name` | str \| None | 已知时传递 |
