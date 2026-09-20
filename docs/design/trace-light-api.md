# Agent 取数层轻量 API 设计（/trace + /stats + BRPC summary）

- 状态：已评审（设计阶段，全量设计、分批实施）
- 日期：2026-09-14（v2 修订 2026-09-15：`/stats/stages` 提进本轮，采用主导问题分类法；v3 修订 2026-09-15：`top_traces` 桶→trace 桥接、教学文档三层结构、降级路径；v4 修订 2026-09-15：第二批设计定稿——`/stats/*` 其余统计、BRPC summary 一页纸、component_src 契约、MCP 适配层，批次规划见 §10）
- 范围：src/plugins/latency 后端 + witty_ub_diagnostician 技能文档（KVCache 域批次 1，BRPC 域批次 2）

## 1. 背景与动机

诊断器现有面向 LLM Agent 的取数接口存在两类问题：

1. **`POST /light_result/overview` 大而全**：一次返回时延逐阶段 P99 归因、8 维组件归因、主导阶段分类、Top 故障码/Pod/源目对、时间热点桶、故障箱聚类与关系信号。Agent 每步往往只需要其中一个维度，其余字段全部成为上下文噪音；ms/us 双口径混入还引入判断歧义。
2. **粒度断层**：聚合接口（aggregated_event / 各类 aggregated failure events）只有 Top N 统计；明细接口（log_parse_result/list、list_trace_events）返回完整行。缺少"trace 清单"这一中间档——Agent 诊断的典型路径是"粗筛候选 trace → 对关心条目下钻"，当前接口无法低成本完成粗筛。

本设计新增一组以 trace 为核心的轻量原子接口，作为 Agent 的取数层。

结合诊断器的核心目标——**定位定界**（哪个组件/阶段时延高或通断、哪个节点出问题，先出大致结论，推理过程与解决方案后置），新接口按"组件定位 → 节点定界 → 代表证据 → 深挖"漏斗分工（见 §4 开头）。

## 2. 目标与非目标

**目标**

- Agent 用一次调用拿到"traceid + 点名字段"的最小清单（如 traceid+总时延、traceid+故障码、traceid+拓扑）
- 默认带排序与命中规模汇总（total），Agent 无需二次加工即可判断规模与 Top 项
- 时延单位统一毫秒，不暴露任何 `*_us` 字段
- 单条 trace 一次拿全轻量画像（下钻）
- 组件级定位一次调用完成：主导问题分类（互斥桶 trace 计数 + 证据耗时 + client 总时延对照 + 治理方向文案），时延与通断双信号同表（`/stats/stages`）
- 删除 `/light_result/overview`，能力下沉（主导问题分类下沉至 `/stats/stages`，其余随 overview 退役）

**非目标**

- 不改动任何现有老接口（`log_parse_result`、`log_failure_event_result`、`aggregated_event`、BRPC 16 个 GET 等全部保留）
- Top 错误码 / Top Pod / Top 源目 / 时间热点的 `/stats/*` 其余统计接口不在本轮实施（设计已定稿于 §11.1，按 §10 批次推进）
- BRPC 域接口本轮不动（summary 一页纸设计见 §11.2，批次 2 实施）
- 不做时延逐阶段 P99 序列、故障箱聚类、关系信号（随 overview 退役，报告侧改用老接口拼装；主导问题分类经 `/stats/stages` 保留）

## 3. 总体架构

```
src/plugins/latency/
├── routers/trace.py          # 新增，prefix="/trace"
├── routers/stats.py          # 新增，prefix="/stats"（本轮仅 /stats/stages）
├── services/trace.py         # 新增，TraceService：参数转换 + 双源查询 + 合并 + 投影
├── services/stats.py         # 新增，StatsService：主导问题分类（light_result 能力平移）
├── schemas/request.py        # 追加 ListTracesRequest / GetStageStatsRequest
├── schemas/response.py       # 追加轻量响应 model（TraceItem / TraceFailureCodeItem / GetTraceMsg / StageStatsItem 等）
└── access/fastapi_server.py  # 挂载 trace.router 与 stats.router；移除 light_result
```

复用原则：底层查询全部走现有能力，新 service 不写新 SQL。

- 时延侧：`LogParseResultPGManager.list_log_parse_results(req)`（构造 `ListLogParseResultRequest`，排序字段按需设置）
- 故障侧：`LogFailureEventResultService.list_trace_failure_event_result(req)`（构造 `ListTraceFailureEventResultRequest`）
- 主导问题分类：同样走 `list_log_parse_results` 取样（异常全量 + top 慢正常，`total_latency` 降序），26 us 字段 → 8 维归因在 service 内存完成
- 校验：`ResourceIdService.validate_request(req)`（自动校验 kb_id/log_id/trace_ids 存在性）

批次 2 扩展点（不新增文件）：`routers/stats.py` 追加四个统计端点（§11.1，`StatsService` 扩展）；`routers/brpc_diagnosis.py` 追加 summary 两个变体（§11.2，`BrpcDiagnosisService` 扩展 `get_summary()`）。

## 4. 端点规格

Agent 定位定界漏斗（① ~ ③ 为本轮新接口，典型 1~3 次调用形成大致结论）：

```
① POST /stats/stages   组件定位：哪个阶段/组件主导（互斥桶计数 + 证据耗时 + client 对照 + 治理方向 + top_traces）
② POST /trace/list     节点定界：主导桶 top_traces（或 is_anomalous 粗筛）+ include=["topology"] 看集中度
③ GET  /trace/{id}     代表证据：单 trace 轻量画像（时延 + 故障码 + 拓扑 + 时间）
④ 老接口               深挖原始日志 / 报告生成（后置）
```

时延类看 ① 的证据耗时与 client 对照列；通断类看 ① 的 fail_cnt 与 urma_timeout 桶——同一张表同时服务两类诊断。①→② 经 `top_traces` 桥接（见 §4.3）：桶→trace 映射仅存在于分类时的内存中、不落库，故 `/trace/list` 不支持按桶过滤，节点定界以主导桶 top_traces 为种子，单一主导桶场景可用 `is_anomalous` 近似（如 node48：query_meta 桶 374/375）。

### 4.1 POST /trace/list —— trace 清单（粗筛主接口）

**请求** `ListTracesRequest`（StrictRequestModel）：

| 参数 | 类型 | 默认 | 说明 |
|---|---|---|---|
| `kb_id` | str | 必填 | 知识库 |
| `log_id` | str? | — | 日志文件 |
| `trace_ids` | list[str]? | — | 指定 trace 批查 |
| `operation` | str? | — | GET / SET |
| `is_anomalous` | bool? | — | 时延异常标记过滤 |
| `pod_ip` / `host` / `cluster_name` | str? | — | 拓扑过滤 |
| `src_ip` / `dst_ip` | str? | — | 源目 IP 过滤 |
| `start_time` / `end_time` | TimeStr? | — | 时间窗（YYYY-MM-DD HH:MM:SS） |
| `status_codes` | list[str]? | — | 故障码过滤（"哪些 trace 挂了 -1002"） |
| `sort_by` | enum | `total_latency` | `total_latency` / `failure_cnt` / `timestamp` |
| `sort_order` | enum | `desc` | `desc` / `asc` |
| `page_cnt` | int | 20 | ≤500 |
| `page_num` | int | 1 | — |
| `include` | list[enum]? | `[]` | 附加块：`failure_codes` / `topology` 的子集 |

**响应**（默认最小形态 = "traceid+总时延"）：

```json
{
  "total": 3421,
  "items": [
    {"trace_id": "t-abc", "total_latency_ms": 1180.5, "is_anomalous": true, "operation": "GET"}
  ]
}
```

- `include=["failure_codes"]`：每条追加 `"failure_codes": [{"code": "-1002", "cnt": 3}]`
- `include=["topology"]`：每条追加 `"pod_ips": ["..."], "host": "...", "src_ip": "...", "dst_ip": "..."`
- `total` 恒返回（命中 trace 总数，规模汇总）；使用纪律（写入技能文档）：`total > 500` 时禁止翻页遍历，必须收窄过滤或只取 Top
- 单位统一 ms；`total_latency_ms` 取 `LogParseResultModel.total_latency`（原生 ms）
- 未 include 的块不出现在响应里（不是 null 占位）

### 4.2 GET /trace/{trace_id} —— 单 trace 下钻

一次拿全轻量画像：

```json
{
  "trace_id": "t-abc",
  "total_latency_ms": 1180.5,
  "is_anomalous": true,
  "operation": "GET",
  "failure_codes": [{"code": "-1002", "cnt": 3}],
  "pod_ips": ["10.0.1.5"],
  "host": "host-101",
  "src_ip": "10.0.1.5",
  "dst_ip": "10.0.2.8",
  "timestamp": "2026-09-03 12:03:11"
}
```

- 先 `ResourceIdService.require("trace", trace_id)` 校验存在性（`_RESOURCE_NAMES` 已含 "trace"）
- 双源合并；单侧缺失字段为 `null` / `[]`，不丢弃整条
- `timestamp` 取故障侧最早日志时间，无故障记录时取解析侧时间

### 4.3 POST /stats/stages —— 主导问题分类（组件定位入口）

每条 trace 按最大互斥阶段归入唯一桶（winner-take-all），桶间计数可直接比较、合计 = 采样数。血缘来自 `yuanrong-scripts/ds_trace_bottleneck.py` 的 `problem_summary`（图 1-1 主问题 Trace 数 / 图 1-2 关键证据耗时的数据源），实现上平移 `light_result.py` 的 `_build_dominant_classification` 四件套。

**请求** `GetStageStatsRequest`（StrictRequestModel）：

| 参数 | 类型 | 默认 | 说明 |
|---|---|---|---|
| `kb_id` | str | 必填 | 知识库 |
| `log_id` | str? | — | 日志文件 |
| `operation` | str? | GET | GET→8 桶读路径口径；SET→5 桶写路径口径（两套独立，见 §4.3.1）；其他值返回空 items + note |
| `start_time` / `end_time` | TimeStr? | — | 时间窗（YYYY-MM-DD HH:MM:SS） |
| `sample_cap` | int | 1000 | 采样上限（50–5000），与现有 `dominant_sample_cap` 同规格 |

**响应**（固定返回该 operation 的全部桶，含零计数桶；GET 8 个 / SET 5 个）：

```json
{
  "operation": "GET",
  "sample_cnt": 375,
  "truncated": false,
  "items": [
    {
      "key": "query_meta",
      "name": "QueryMeta",
      "trace_cnt": 374,
      "success_cnt": 0,
      "fail_cnt": 374,
      "p50_ms": 20.135,
      "p90_ms": 20.144,
      "max_ms": 20.183,
      "client_p50_ms": 20.155,
      "client_p90_ms": 20.166,
      "metric_name": "主阶段耗时",
      "action": "排查 Meta Worker 响应、元数据锁竞争、路由刷新与 metadata RPC。",
      "note": "worker_access_latency_us − urma_processing_us（queryAndGet 查元数据/业务）",
      "top_traces": [
        {"trace_id": "t-abc", "evidence_ms": 20.183, "client_ms": 20.201},
        {"trace_id": "t-def", "evidence_ms": 20.144, "client_ms": 20.166}
      ]
    }
  ],
  "note": "样本集=异常 trace 全量+top慢正常（合并去重，cap 截断）；URMA 超时为文本匹配近似口径"
}
```

**字段语义**：

- `p50_ms` / `p90_ms` / `max_ms` = 桶证据耗时，双口径：普通瓶颈取 winner 维度耗时；`urma_timeout` 桶取日志文本 timeout `elapsedMs`（无完成态 WR 不造数为 0）；`cross_window` 桶取总时延
- `client_p50_ms` / `client_p90_ms` = 该桶 trace 的 Client 总时延对照（`total_latency_us`），判断主阶段是否吃满总时延（如 QueryMeta 20.13 ≈ client 20.15 → 独占）
- `metric_name`：`"主阶段耗时"` / `"URMA timeout elapsedMs"`，随桶口径切换
- `action`：每类治理指引文案（来自脚本 `guidance_actions` 8 句，静态文本）
- `success_cnt` / `fail_cnt`：`is_anomalous` 真假分拆（与脚本 `status != 0` 口径近似，均为失败主导判定）
- `top_traces`：该桶按证据耗时降序的 top 3~5 条种子（`{trace_id, evidence_ms, client_ms}`），①→②/③ 的桥接——Agent 拿这些 trace_id 走 `/trace/list {trace_ids, include:["topology"]}` 批查节点集中度，或直接 `GET /trace/{id}` 取代表证据；全量约 8 桶 × 5 条 × ~60B ≈ 2.4KB，体积可控
- 桶清单：`rpc_network` / `rpc_queue` / `query_meta` / `urma` / `data_worker` / `cross_window` / `residual` / `urma_timeout`

**与 node48 脚本 problem_summary 的口径对照**：

| 脚本桶 | 本实现桶 | 差异 |
|---|---|---|
| 远端供数处理（server 父窗口−URMA） | `data_worker`（d6 调度+d7 sdk/master processing） | 归因维度不同源 |
| 数据访问父窗口/未细分（预算扣减残余） | `cross_window`（request_mode=unknown 观测缺失） | 脚本按扣减残余、本实现按观测缺失 |
| 其余 6 桶 | 同名同义 | — |

算法差异：脚本为预算瀑布（顺序扣减、每步封顶，Σ=client_ms）；本实现为 26 us 字段 8 维 winner-take-all（residual = total−Σ）。两者互斥，但归因边界个别条目可能分桶不同，以 node48 数据对齐验证（见 §9）。

**实现**：`_DOMINANT_BUCKET_SPEC` / `_component_dim_us` / `_classify_dominant` / `_build_dominant_classification` 四件套从 `light_result.py` 平移至 `services/stats.py`，增量三处——聚合时同步收集 client 总时延分位、桶定义表挂 `action` 文案、每桶维护证据耗时 top-N 种子（`heapq.nlargest(5)`，复用分类时已算出的 evidence_us，无额外查询）。

### 4.3.1 SET（写路径）独立视角

SET 与 GET 是**两套独立口径**，不做跨 operation 混合归桶：`get_stage_stats`
按 `operation` 分派到 `_get_stage_stats_get` / `_get_stage_stats_set`，两套
桶 key 不重叠，消费方（skill / 报告）各调一次自行并列。原因：写路径的请求
流程与可观测字段和读路径不同。

**node48 实测口径**（`log_parse_result` SET 行 3638 条 = `DS_KV_CLIENT_SET`
1902 + `DS_POSIX_CREATE` 1706 + `DS_POSIX_PUBLISH` 30，每 trace 仅 1 行）：

- 可用列：`sdk_processing_us`（客户端 SDK 段，含等待数据面返回）、
  `local_worker_internal_us`（Worker 端写处理）、`worker_access_latency_us`
  （判断数据面是否被观测）；**`sdk_processing_us + local_worker_internal_us
  ≡ total_latency_us`**（仅 1 行偏离 +8153us）
- 剔除列：`urma_processing_us` / `create_latency` / `publish_latency` /
  `w2w_urma_latency` 在 `trace_frame.py` 显式置 NULL；`c2w_urma_latency
  = total_ms − worker_total_latency` 而 SET 侧 worker_total ≈ 0 → 恒 ≈ 总时延，
  无额外信息量；master/remote/sdk RPC 细分列非空 ≈ 0
- 因此 SET 侧**不做** CREATE/PUBLISH 分段归因（该两列无产出，属解析侧缺口，
  另立任务）；`urma_link_latency`（615/3638 有值）仅作附注不参与归桶

**5 桶（判定顺序即优先级，互斥穷尽）**：

| 优先级 | key | 显示名 | 口径 | 证据 | node48 命中 |
|---|---|---|---|---|---|
| 1 | `set_urma_timeout` | SET·URMA超时 | `anomaly_reason`/`content` 文本匹配 timeout/超时（复用 `_TIMEOUT_TEXT_RE`） | 文本 elapsedMs，缺失取 total | 0 |
| 2 | `set_no_evidence` | SET·数据面未观测 | `local_worker_internal_us` 与 `worker_access_latency_us` 均空（无 Worker 侧行） | `total_latency_us` | 1164 |
| 3 | `set_residual` | SET·未解释残差 | `total − (sdk + worker) ≥ +0.5ms` | 残差 | 1 |
| 4 | `set_client` | SET·客户端SDK段 | 有 Worker 侧行且 `sdk ≥ worker` | `sdk_processing_us` | 2467 |
| 5 | `set_worker` | SET·Worker写处理 | 有 Worker 侧行且 `worker > sdk` | `local_worker_internal_us` | 6 |

- 残差阈值 0.5ms（`_SET_RESIDUAL_THRESHOLD_US`）：实测唯一偏离为 8153us，
  可捕获离群而不计入舍入误差
- `metric_name`：`set_urma_timeout` → `URMA timeout elapsedMs`；
  `set_no_evidence` → `Client 总时延（数据面未观测）`；其余 → `主阶段耗时`
- 各桶 `note` 追加家族构成（按 `row.operation` 原始 handle 统计，如
  `DS_KV_CLIENT_SET 12、DS_POSIX_CREATE 3`）；响应 `note` 显式列出被剔除
  维度及原因（避免消费方误读为"这些维度没问题"）
- 实现：`_SET_BUCKET_SPEC` / `_classify_dominant_set` / `_set_family_handle`
  + 共用采样管道 `_sample_traces` 与截断判定 `_is_truncated`

## 5. 数据流：双源合并规则

`log_parse_result`（时延侧，KV_CACHE_LOG_PARSE_WORKER 写入）与 `trace_failure_event`（故障侧，KV_CACHE_LOG_EVENT_DIAGNOSIS_WORKER 写入）覆盖集不保证重合，合并规则：

| 场景 | 主源 | 补源 | 说明 |
|---|---|---|---|
| `sort_by ∈ {total_latency, timestamp}` 且未 include `failure_codes` 且未传 `status_codes` | `log_parse_result` | 无 | 单查询最快路径 |
| `include` 含 `failure_codes` 或传了 `status_codes`（`sort_by ≠ failure_cnt`） | `log_parse_result` | `trace_failure_event` 按页内 trace_id LEFT JOIN（DB 聚合补源） | 时延粗筛为主，补故障码 |
| `sort_by = failure_cnt` | `trace_failure_event` | `log_parse_result` 按页内 trace_id LEFT JOIN | 故障粗筛为主源，避免无时延行的故障 trace 丢失 |

- 合并语义：LEFT JOIN；主源分页后按当前页 trace_ids 批量查补源，单页 ≤500 条量可控
- `failure_codes` 聚合位置：清单路径在 DB 侧完成（见下"规模设计"）；仅 `GET /trace/{trace_id}`（单 trace，事件行有界）在 service 内 Counter 聚合
- `failure_cnt` = 该 trace 故障码计数总和（排序键）
- 主源 total 即响应 total
- 排序执行位置：`total_latency` / `timestamp` 走主源原生排序（manager sort_fields / 时间字段）；`failure_cnt` 的聚合/排序/分页全部下推 DB（见下"规模设计"）
- 过滤跨源语义：各过滤参数作用于其原生数据源；`is_anomalous` 属时延侧字段，故障主源路径下若传入，由 SQL INNER JOIN `log_parse_result` 聚合子查询过滤（纯故障 trace 无时延行，会被该过滤剔除——与"时延侧口径"定义一致）
- `sort_by=timestamp` 的时间口径：主源该 trace 的时间字段（时延主源取解析侧时间，故障主源取最早日志时间；`total_latency`/`timestamp` 排序键经 LEFT JOIN 时延侧聚合子查询取 max(total_latency)/min(timestamp)）

### 5.1 规模设计：故障码聚合下推 DB（10W~50W 行）

故障主源路径（`sort_by=failure_cnt` 或传 `status_codes`）的原始实现为"manager 全量拉取 → service 内存 Counter 聚合排序"，在 10W~50W 行规模下存在两个问题：全量传输撑爆应用内存、聚合排序在 Python 侧线性放大。重新设计为**聚合/排序/分页全部下推 PostgreSQL**，应用侧只接收页内行（≤ page_cnt）：

**manager 层新增两个方法**（`LogFailureEventPGManager`）：

| 方法 | 调用方 | 职责 |
|---|---|---|
| `list_failure_code_stats(req) -> (total, [TraceFailureCodeStatModel])` | 故障主源路径 | 过滤 → unnest 聚合 → join 时延排序键 → ORDER/LIMIT/OFFSET，一次返回页行 + 码明细 |
| `list_failure_codes_by_trace_ids(kb_id, log_id, trace_ids) -> [TraceFailureCodeStatModel]` | 时延主源 `include=failure_codes` 补源 | 仅按页内 trace_ids（≤500）聚合，返回 trace_id + status_code 两列的聚合结果 |

**SQL 形态**（`list_failure_code_stats`，全部有界传输）：

```
expanded:  过滤后的行 × unnest(status_code)                 -- 每行一码
code_cnt:  GROUP BY (trace_id, code) → 每码计数              -- CTE
per_trace: GROUP BY (trace_id) → failure_cnt = Σ cnt
           （空码 trace 经 union_all 保留，failure_cnt=0，不丢条）
页行:      per_trace [LEFT|INNER] JOIN 时延侧排序键 → ORDER/LIMIT/OFFSET
计数:      JOIN 后的 per_trace 行数（total）
码明细:    页内 trace_id 的 code_cnt 行（cnt 降序、code 升序）
```

- `sort_by ∈ {total_latency, timestamp}` 或传 `is_anomalous` 时，per_trace LEFT JOIN `log_parse_result` 聚合子查询（`GROUP BY trace_id` 取 `max(total_latency)` / `min(timestamp)`，同一 trace 多日志行不重复计数）；`is_anomalous` 过滤时改 INNER JOIN
- 排序 `nulls_last`：纯故障 trace 无时延键时排末尾；翻页稳定性由次级排序键 `trace_id asc` 保证
- 过滤条件构造复用 `_trace_filter_conditions`（与老接口 `list_trace_failure_events` 同一构造器，过滤语义不漂移）；`is_anomalous` 例外——该字段在老接口为故障侧 `failure_mode` 口径，此处为时延侧口径（join `log_parse_result`），由 `ListFailureCodeStatsRequest` 独立声明

**请求字段映射**（service → `ListFailureCodeStatsRequest`）：`host → host_names=[host]`、`cluster_name → cluster_names=[cluster_name]`；`pod_ip` 不映射（时延侧存 IP 列表、故障侧存 pod 名称列表，无等价字段，避免错误过滤）。

**索引建议**（配合下推查询；当前 `trace_failure_event` 仅 PK(id) + index(log_id)）：

| 索引 | 服务的查询 |
|---|---|
| `trace_failure_event(trace_id)` | 码明细按页内 trace_ids 回查、`list_failure_codes_by_trace_ids` 补源、老接口 trace_ids 批查。压测实测：定点批查 0.49s→0.04s（12×）、页内补源 0.23s→0.09s |
| `trace_failure_event(log_id, timestamp)` | 时间窗过滤 + log_id 收窄（覆盖常用组合，避免全索引扫描后再回表）。压测实测：30min 窗（25% 选择率）Bitmap Index Scan 62ms、5min 窗（4%）10.6ms |
| `trace_failure_event status_code GIN`（可选） | **压测观察结论：不建**——`-1002` 过滤 60% 命中率下 planner 正确选择 Seq Scan（404ms），GIN 无收益；仅当故障码基数增大导致低命中率（<10%）时再评估 |
| `log_parse_result(log_id, trace_id)`（分区表内） | lat_scope 聚合子查询 + 页内时延补全（分区键 log_id 前置，分区裁剪 + trace_id 定位） |

三个 B-tree 索引已在压测环境验证（见 §9 项 5），建议纳入部署初始化（自动 DDL 机制）。

**规模约束与边界**：

- 设计目标 10W~50W 行：聚合/排序/分页均在 DB 执行，应用侧内存占用与数据量无关（仅页内行 + 码明细）
- 深翻页（大 OFFSET）仍是 O(offset) 扫描：Agent 消费场景以 top-N 粗筛为主（`total>500` 纪律见教学文档）；确需深翻页时用 `trace_ids` 批查或时间窗收窄替代
- `unnest` 展开使中间行数 = Σ|status_code|（每行通常 1~3 码），GROUP BY 在 DB 侧聚合，无传输放大

## 6. overview 移除

**删除前置——能力平移**：`services/light_result.py` 删除前，以下四件平移至 `services/stats.py`（§4.3 依赖，代码级复用非重写）：

- `_DOMINANT_BUCKET_SPEC`（GET 8 桶定义 + 口径 note + `action` 指引文案；SET 侧对应 `_SET_BUCKET_SPEC` 5 桶，见 §4.3.1）
- `_component_dim_us`（26 us 字段 → 8 维归因，内部 us、输出 ms；SET 侧不适用）
- `_classify_dominant`（URMA 超时文本 > 交叉窗口 > winner-take-all，含 elapsedMs 抽取正则；SET 侧对应 `_classify_dominant_set`）
- `_build_dominant_classification`（取样/聚合骨架，追加 client 总时延分位收集；现拆为 `_sample_traces` + `_get_stage_stats_get` / `_get_stage_stats_set`）

**删除清单：**

- `src/plugins/latency/routers/light_result.py`（整文件）
- `src/plugins/latency/services/light_result.py`（整文件）
- `schemas/request.py`：`GetLightOverviewRequest`（文件末尾类）
- `schemas/response.py`：全部 `Light*` 类（`LightStageItem` / `LightComponentItem` / `LightDominantStageItem` / `LightLatencyMsg` / `LightCodeItem` / `LightPodItem` / `LightSrcDstItem` / `LightHeatSlot` / `LightFailureMsg` / `LightFaultBox` / `LightBoxRelationSignal` / `GetLightOverviewMsg` / `GetLightOverviewResponse`；删除前 Read 确认边界，避免误删相邻类）
- `access/fastapi_server.py`：import 块的 `light_result` 与 `configure()` 的 `app.include_router(light_result.router)`

引用面已核实：全仓 `*.py` 仅 fastapi_server.py 引用 light_result，无测试引用。

## 7. 消费方文档切换（Agent 教学三层结构）

新接口的用法必须分层教会 Agent——路由层决定"何时用"，工具层决定"怎么调"，报告层决定"怎么呈现"：

| 层 | 文件 | 职责 |
|---|---|---|
| 路由层 | `witty_ub_diagnostician/agents/` 主指令 | 通用分诊心智：先 `/stats/stages` 看双信号（时延证据/通断 fail_cnt）定类，再进对应 skill 下钻；"空结果降级"原则 |
| 工具层 | 各 skill 的 `references/TOOL_REFERENCE.md` | 接口参数 + curl 示例 + 使用纪律 + 降级路径 |
| 报告层 | `diagnostic-report-generation/SKILL.md` | 报告板块 ↔ 取数接口映射 |

**逐文档变更清单：**

| 文档 | 变更 |
|---|---|
| `witty_ub_diagnostician/agents/` 主指令（agent.md 或等价文件） | "调查原则"段新增分诊前置步骤：诊断入口先调 `/stats/stages`（时延类看证据耗时/client 对照、通断类看 fail_cnt/urma_timeout 桶），据结果决定进 latency-analysis 或 failure-code-analysis；补充"归因子集为空（8 桶全 0）时降级"原则（见 §8）；既有"先验证数据可用、空结果不等于健康"原则不变 |
| `witty_ub_diagnostician/skills/latency-analysis/references/TOOL_REFERENCE.md` | overview 段（L48-110）替换为定位漏斗用法：`/stats/stages`（组件定位入口、双口径字段说明、top_traces 桥接、分诊规则）+ `/trace/list`（默认最小响应、include、sort_by 示例、`total>500` 使用纪律）+ `GET /trace/{id}` |
| `witty_ub_diagnostician/skills/failure-code-analysis/references/TOOL_REFERENCE.md` | overview 段（L16-56）替换为：`/stats/stages`（通断侧用法：fail_cnt/urma_timeout 桶 + top_traces 取代表 trace）+ `/trace/list`（include failure_codes、status_codes 过滤、sort_by=failure_cnt、`total>500` 使用纪律复述） |
| `witty_ub_diagnostician/skills/diagnostic-report-generation/SKILL.md` | 宏观概览/代表 trace 取数切 `/trace/list` + `/trace/{trace_id}`；主导问题分类板块（图 1-1/1-2 同源）切 `/stats/stages`（含 top_traces 作代表 trace 候选）；统计板块（Top 码/Pod/热点图）临时切老聚合接口（`list_time_aggregated_failure_events` / `list_pod_aggregated_failure_events` / `metrics/err_code` / `metrics/latency`），待 `/stats/*` 其余接口（§11.1）批次 2 落地后再切换 |

老接口全部原样保留，前端看板不受影响（未使用 overview）。

## 8. 错误处理与边界

- 复用现有全局异常体系：404（资源不存在）/ 400 / 422（参数校验）/ 503（数据库）
- `include` 非法值 → 422（pydantic Literal 收口，无自由投影）
- 空结果 → `{"total": 0, "items": []}`，不是错误
- 纯故障 trace（无时延行）→ `total_latency_ms: null`
- `status_codes` 过滤但 trace 无故障侧记录 → 自然为空集
- 排序：`total_latency`/`timestamp` 走主源原生排序；`failure_cnt` 的聚合/排序/分页下推 DB（见 §5.1）
- `/stats/stages` 数据可行性边界（明细表 us 字段落库仅覆盖异常全量+top1000，分类样本集与之对齐，零缺口）：
  - 归因子集为空（老格式日志缺 us 原材料列，`_has_yuanrong_cols` 不通过）→ 桶计数全 0 + note 说明，不是错误
  - `operation=SET` → 走写路径 5 桶独立口径（见 §4.3.1）；样本仍为空时返回 5 个零计数桶 + note
  - `operation` 既非 GET 也非 SET → items 空 + note（提示切换为 GET / SET）
  - 带 IP 维度过滤（pod_ip/host/src_ip/dst_ip）→ items 空 + note（us 字段无 IP 维度，节点定界交 `/trace/list`）
- Agent 降级路径（写入技能文档，接口返回上述边界态时的标准动作）：
  - 归因子集为空（桶全 0）→ 放弃组件定位，转 `/trace/list {is_anomalous:true, include:["topology"]}` 直接做异常粗筛 + 节点定界；需要阶段序列时转老 `metrics/latency`
  - `operation=SET` 归因子集为空（SET 样本缺 `total_latency_us`）→ 时延侧转 `/trace/list {operation:"SET"}` 粗筛，通断侧不受影响（故障侧无 operation 限制）
  - IP 维度过滤空结果 → 组件定位不带 IP 重调一次，节点定界改由 `/trace/list` 的拓扑过滤完成

## 9. 测试与验收

1. `python -m compileall src/plugins/latency` 编译通过
2. 启动服务，curl 验证：
   - `POST /trace/list {"kb_id": "..."}` → 默认最小响应，按 total_latency_ms 降序
   - `{"kb_id": "...", "include": ["failure_codes", "topology"]}` → 两附加块齐备
   - `{"kb_id": "...", "sort_by": "failure_cnt", "status_codes": ["-1002"]}` → 故障主源路径
   - `GET /trace/{id}` → 单条合并视图
3. 回归：`POST /light_result/overview` → 404；`/log_parse_result/list`、`/log_failure_event_result/list_trace_events` 等老接口行为不变
4. 双源对齐抽查：同一 kb 随机抽取 trace，验证 LEFT JOIN 语义（单侧缺失不丢条、字段补 null/[]）
5. 故障主源路径规模验证（§5.1）：50W 行级 `trace_failure_event` 数据下验证 `sort_by=failure_cnt` / `status_codes` 过滤查询——EXPLAIN 确认聚合/排序/分页在 DB 侧执行；响应时间满足交互级（秒级）；空码 trace（failure_cnt=0）不丢条；`is_anomalous` 过滤时纯故障 trace 被剔除
   ✅ **2026-09-16 压测通过**（50W 行 tfe + 10W 行 lpr，200K trace，确定性造数）：
   - 正确性：total 与 ground truth 精确一致（无过滤 200,000 / `-1002` 过滤 120,000 / `is_anomalous` INNER JOIN 剔除 25,000 / LEFT JOIN 时延排序 120,000）；空码 trace（含 NULL status_code，2 万条）经 union_all 全保留，`failure_cnt=0`；深分页 offset 99,980 正常
   - EXPLAIN：双层 HashAggregate + unnest 展开 + top-N heapsort 全部 DB 侧执行，应用侧仅收页内行
   - 性能（无索引基线 → 加三索引后）：首页 2.6s→2.5s、status_codes 1.6s→1.4s、is_anomalous 2.7s→2.6s、深分页 3.9s→3.7s（全量聚合路径 Seq Scan 本即最优，索引收益集中在定点/补源/时间窗路径：12× / 2.5× / Bitmap 62ms）；全部满足秒级交互
   - GIN 观察点：60% 命中率下 planner 选 Seq Scan，结论不建（§5.1 已更新）
6. `/stats/stages` 功能验证：curl 调用返回该 operation 的全部桶（GET 8 个 / SET 5 个，含零计数桶）、`sample_cnt` = Σ `trace_cnt`、`client_*` 对照列、`action` 文案与 `top_traces`（非零桶每桶 3~5 条、按 evidence_ms 降序、trace_id 可直接用于 `/trace/list` 批查与 `GET /trace/{id}`）齐备
6.1 SET 独立视角验证（2026-09-17）：单测 95 例全绿（新增 7 例覆盖 5 桶契约/边界/长尾/超时优先级/残差/GET 回归/未知 operation/下推 operation）；node48 真机只读 SQL 对照桶分布与 §4.3.1 表一致（`set_client` 2467 / `set_no_evidence` 1164 / `set_worker` 6 / `set_residual` 1 / `set_urma_timeout` 0，Σ=3638）
7. node48 数据对齐验证（分类算法验收基准）：将 `node48-error-analysis-share-20260831/raw-inputs/node48_collect-core.tar.gz` 灌入解析管线后调用 `/stats/stages`，确认：
   - us 字段覆盖率：异常 + top1000 子集 26 字段非空（`_has_yuanrong_cols` 通过）
   - `anomaly_reason`/`content` 中 elapsedMs 文本保留，`urma_timeout` 桶证据口径可用
   - 分类结果与脚本 `problem_summary`（`runs/run-01/` 内嵌 AGG）对齐：QueryMeta 主导 374/375、RPC网络 1 条、error_summary RPC截止超时 371；分桶计数偏差仅允许出现在"远端供数处理↔data_worker / 父窗口未细分↔cross_window"两对口径不同的桶（见 §4.3 对照表），其余桶需逐桶一致
   ⚠️ **2026-09-16 验证执行结果：管线与 API 层通过，分桶对齐未达成（根因为解析侧前置缺口，非 API 层问题）**：
   - ✅ 管线端到端：collect-core 7722 摘录 → (path,lineno) 去重重建 4592 源日志文件（36MB）→ 灌入解析管线 → 9030 traces / 5677 异常入库 → 诊断 7546 故障 trace → overall SUCCESSFUL 100%（诊断工具须用当前代码构建，host 旧版 /usr/bin 二进制有 start-time 解析 bug）
   - ✅ 26 字段结构产出（`_has_yuanrong_cols` 通过，`_yuanrong_from_grouped` 正常执行）；node48 数据实际 6 字段有值：total_latency_us / sdk_processing_us / worker_access_latency_us / local_worker_internal_us / urma_link_latency / urma_total_latency，其余因下述缺口 1 为空
   - ✅ 批次 1 三端点真实数据冒烟：`/trace/list`（total=5677、时延排序/分页正常）、`/trace/{trace_id}`（双源合并 failure_codes=["1001"] 正常）、`/stats/stages`（8 桶骨架/sample_cnt/client 对照列/top_traces 齐备）
   - ❌ 分桶对齐：实际 1000/1000 落 cross_window，基准为 QueryMeta 374/375、RPC网络 1。三个根因（均解析侧，API 层无法绕过）：
     1. **brpc perf 行未解析**：node48 的 RPC 分解数据全部在内嵌于 `ds_client_*.INFO.log` 的 `brpc_perf_trace.h:377` 行（`method=...e2e_us=...`，7886 行，QueryAndGet 1690 条），不在任何解析器关键字集内（`ClientInfoParser` 仅认 `[ZMQ_RPC_FRAMEWORK_SLOW]`，`brpc_log_file_patterns` 只匹配独立 brpc.log）→ 16 个 RPC 字段全空、`__me/__re/__cn` 无原材料；
     2. **request_mode 单跳语义**：QueryAndGet 直连单跳（`__cn=1`）既不满足 `__isd`（`__cn≥2`）也无 master/remote 条目 → unknown → 优先落 cross_window。即使补齐缺口 1，仍需把单跳 QueryAndGet e2e 映射进 query_meta 维（脚本口径 `client.rpc.direct_query_and_get` = QueryAndGet RPC e2e≈20.1ms，正是基准 QueryMeta 桶证据）；
     3. **anomaly 文本无来源**：`content`/`anomaly_reason` 自 detect 模块删除（commit 69af73d4）后列式路径结构性为空 → `urma_timeout` 桶文本口径不可用（本例基准 urma_timeout=0 碰巧一致，但 elapsedMs 证据链断裂）。
   - error_summary（RPC截止超时 371）对应批次 2 `/stats/error_codes`，随批次 2 验收
   - **处置决议（2026-09-16 定稿）：轻量两级架构，不做解析侧补齐**
     - **第一级（API 轻量粗分，已实施）**：`/stats/stages` 基于 DB 现有 7 个有值列（total_latency_us / sdk_processing_us / c2w_latency / worker_access_latency_us / worker_total_latency / local_worker_internal_us / total_latency）做 client/worker 粗分——node48 实测该数据已能回答"问题在客户端 SDK 侧等待、数据面无辜（worker 窗口 19~54µs vs total 21~25ms）、2952/5431 慢 trace 未触达数据面"。实施口径（`_classify_dominant` 分支 2，request_mode=unknown 时）：
       - worker 侧窗口 = max(worker_access_latency_us, local_worker_internal_us)，≥50% total_latency_us → `data_worker`（证据=worker 侧窗口）；否则 → `cross_window`（证据=总时延，客户端等待主导：worker 干净或未触达数据面）
       - `cross_window` 桶 note 动态覆盖为粗分口径：量化"N 条 worker 有窗口但干净（占比中位数 X%）/ M 条未触达数据面"+ 指引 `brpc_stage_drill.py` 深挖；`data_worker` 桶 note 追加粗分来源计数；顶部 note 增粗分规则总说明
       - 验证：单测 54/54 通过（新增 2 用例：三分支粗分 + 50% 含等号边界）；node48 端到端 1000 条全部 cross_window，note 量化"985/1000 未触达数据面、15/1000 worker 有窗口但干净（占比中位数 3.8%）"，data_worker 0 条（符合 node48 慢 trace 人群 worker 侧 19~54µs 的事实）——第一级结论"客户端等待主导"与第二级脚本深挖"100% QueryMeta"衔接成立
     - **第二级（skill 脚本深挖）**：`witty_ub_diagnostician/skills/latency-analysis/scripts/brpc_stage_drill.py` 旁路直扫原始日志的 `[BRPC_RPC_FRAMEWORK_SLOW]` 行（19 字段新格式，纯标准库，36MB 日志 0.7s），按父 trace 聚合 RPC 子过程、公式拆维（QueryMeta = QueryAndGet e2e − 框架分量；框架分量 = network_residual + server_req_queue + client_req_framework，超时无响应时为 0、QueryMeta 吸收全额等待）winner-take-all 分桶；SKILL.md 阶段 4.5 已接入
     - **node48 脚本验证（与基准对齐）**：getBuffer 失败人群（slow≥20ms & cntl_failed=1）命中 1552 trace **100% 落 QueryMeta**，与基准采样 374/375（99.7%）对齐；RPC网络桶 slow≥1.5ms 全量下命中 465 条（成功慢调用人群，基准采样集中失败人群故仅 1 条）；错误码 1008×5093（deadline 截止 = 基准 RPC截止超时同源）。setStringView 人群另分出 Master元数据写 430 / URMA链路 986（基准采样未含该人群）
     - 上述三个解析侧缺口（brpc perf 行 / 单跳 request_mode / anomaly 文本）维持现状不补；若未来需要 API 级 RPC 归因，前置工作清单见下（留档）：① 新增 brpc perf 行解析入库；② 单跳 QueryAndGet e2e → query_meta 维映射；③ anomaly 文本来源恢复
8. 教学文档验收：全仓 grep `light_result/overview` 于 `witty_ub_diagnostician/`（agents + skills）下零命中；四份消费方文档（agents 主指令、两个 TOOL_REFERENCE、报告 SKILL）均含 `/stats/stages` 分诊/桥接/降级内容；latency-analysis 与 failure-code-analysis 双文档均含 `total>500` 使用纪律

## 10. 实施批次（全量设计、分批实施）

设计一次性定稿（§4 批次 1 + §11 批次 2/3），实施按批次推进，每批独立可验收：

| 批次 | 范围 | 验收锚点 |
|---|---|---|
| 批次 1（本轮） | `/trace/list` + `/trace/{trace_id}` + `/stats/stages` + overview 移除 + 四份教学文档切换 | §9 全部 8 项 |
| 批次 2 | `/stats/*` 其余四端点（§11.1）+ BRPC summary（§11.2）+ 报告统计板块二次切换 + brpc SKILL 教学更新 | §11.1 / §11.2 各自验收点 |
| 批次 3（可选） | component_src 源码取证（§11.3）+ MCP 适配层（§11.4） | 依赖源码包接入方案 / MCP client 就绪 |

批次间无代码依赖：批次 2 仅扩展 `routers/stats.py` 与 `routers/brpc_diagnosis.py`，不改动批次 1 任何文件行为。

## 11. 第二批接口设计（定稿待实施）

### 11.1 /stats/* 其余单维度统计（报告统计板块承接）

四端点共用请求骨架（StrictRequestModel）：`kb_id` 必填；`log_id` / `operation` / `start_time`+`end_time` 可选；`top_n` 默认 20（≤100）。响应统一 `{"total": <维度基数>, "items": [...]}`，单位 ms、无 `*_us`。

| 端点 | items 元素 | 排序 | 数据来源（复用） |
|---|---|---|---|
| `POST /stats/error_codes` | `{status_code, trace_cnt, event_cnt}` | trace_cnt 降序 | 故障侧 trace 级 Counter（`TraceFailureEventModel.status_code`，同 §5 failure_codes 口径）；`event_cnt` 为日志级事件数（`log_failure_event` 侧，可得则返回） |
| `POST /stats/pods` | `{pod_ip, host, trace_cnt, fault_trace_cnt}` | fault_trace_cnt 降序 | 时延侧 pod 聚合 + 故障侧 join；多 Pod trace 在各 Pod 均计数一次（note 说明） |
| `POST /stats/links` | `{src_ip, dst_ip, trace_cnt, fault_trace_cnt}` | fault_trace_cnt 降序 | 时延侧 src/dst 聚合 + 故障侧 join |
| `POST /stats/heatmap` | `{window_start, fault_trace_cnt}` | window_start 升序 | 时间聚合（复用 `list_time_aggregated_failure_events` 逻辑） |

`/stats/heatmap` 追加 `window_size` 参数（`1m`/`10m`/`1h`，默认按时长自动：≤2h→1m、≤48h→10m、否则 1h），`slots` 上限 240（超限自动放大窗口）。

**联动纪律**（写入教学文档）：每个 `/stats/*` 的 Top 项即 `/trace/list` 对应过滤器的取值——Top 码 → `status_codes:[top_code]`、Top Pod → `pod_ip:...`、Top 源目 → `src_ip/dst_ip`，Agent 从统计一步切回 trace 粒度取证据。

与老聚合接口的关系：不替代、不改动——老接口继续服务前端看板；`/stats/*` 是 Agent 侧统一轻量契约（同一请求骨架、同一响应形状、同套教学文档），报告统计板块从"混用四个老接口"切换为"四个 `/stats/*`"。

**验收**：curl 四端点返回形状一致（total + items）、排序正确；heatmap 自动选窗与 slots 截断生效；与老聚合接口同参数抽查数值一致（口径对齐）。

✅ **2026-09-16 验收通过**（单测 + node48 真实数据，提交 d3ab3905/c5029913）：
- 单测 89/89（批次 1 54 用例回归 + 新增 35：schema 严格校验 / service 选窗与 note 分支 / router passthrough 与 422）
- error_codes 与 SQL ground truth 精确一致：1001→4613/6293、6→1561/3059、1010→44/44、3→7/7（Top 码 1001=RPC截止超时，与 §9 error_summary 锚点闭环）；`operation=GET` 过滤后 1001→2147
- pods：total=558；Top Pod 192.168.125.248 → trace 1576 / fault 1576 与 SQL 交叉核对一致（该 Pod 全部 trace 均为故障 trace，符合 node48 高故障率事实）
- links：total=1 为数据事实非代码缺陷——log_parse_result 5677 行仅 1 行有 src/dst，trace_failure_event 9240 行仅 1 行非空（9239 行双 NULL）
- heatmap：自动选窗 1m（36 槽，跨度 1.2h）；指定 10m 时 8 槽 Σ=9240 = 故障 trace 总数，分桶自洽

### 11.2 BRPC summary 一页纸（BRPC 域组件定位入口）

BRPC 现有 16 个 GET 接口职责单一、无大而全病灶，但缺漏斗 ① 级"一页纸"——形成"ubsocket 还是 urma 主导、哪个 Pod、什么时间窗、什么故障模式"的大致结论需 2~3 次调用 + 时间序列眼力推理。本端点补齐后，BRPC 漏斗对齐 KVCache：

```
① GET summary                      组件定位 + 节点定界 + 时间窗 + 故障模式 Top（一页纸）
② pod-events / abnormal-threads    聚合下钻（既有接口）
③ pod-events/{event_id} 等详情      证据分层（既有接口）
④ hits                             原始日志（既有接口）
```

**端点**（两个变体，同一 service 方法）：

- `GET /brpc-diagnosis/knowledge/{kb_id}/summary`
- `GET /brpc-diagnosis/batch/{batch_id}/summary`

**参数**：`start_time` / `end_time` 可选（默认 kb/batch 全域——解决现有接口时间必填、每次需先查批次元数据的摩擦）；`component` 可选（ubsocket/umq/urma）；`top_n` 默认 10、上限 50。

**响应**：

```json
{
  "hit_count": 12345,
  "time_range": {"start_time": "...", "end_time": "..."},
  "components": [{"component": "ubsocket", "hit_count": 11000, "pct": 89.1}],
  "top_pods": [{"pod_ip": "10.0.1.5", "pod_name": "...", "hit_count": 4200}],
  "top_failure_modes": [{"failure_mode_id": "...", "name": "...", "hit_count": 3800}],
  "peak_window": {"start_time": "...", "end_time": "...", "hit_count": 900, "window_size": "1m"}
}
```

**实现**：`BrpcDiagnosisService` 新增 `get_summary()`；聚合下推 DB 侧——`BrpcDiagnosisPGManager` 新增 `get_summary_component_counts` / `get_summary_pod_top` / `get_summary_peak_window`（hits 表直查，hit 行自带 component/pod 列无需 join 节点表；排序/LIMIT 全下推；peak 为分桶 max 单行，不拉时间序列）；top_failure_modes 复用既有 `get_failure_mode_hit_counts` 后 Python 侧组件过滤 + 排序截断（知识库节点级小基数）。peak_window 自动选窗（跨度 ≤10min→10s、≤2h→1m、否则 1h）。无存储变更、无老方法改动。

**消费方**：`brpc-diagnosis/SKILL.md` 阶段一后插入"1.5 全局一页纸"（summary 先行；hit_count=0 或组件/时间窗已清晰时直接跳阶段二对应入口）；`diagnostic-report-generation/SKILL.md` BRPC 分支宏观板块取数切 summary。SKILL 输入规则段同步补 summary 的参数说明（时间可选、GET、UTC+8）。

**验收**：summary 数值与既有接口交叉核对（components 合计 = hit_count、top_pods 与 pod-events 同窗口 Top 一致、peak_window 与 interface-timeline 尖峰一致）；时间缺省时默认全域且 `time_range` 回显实际查询范围。

✅ **2026-09-16 部分验收**（提交 8b12f64b/1aafc714；单测与 SQL 层通过，数值交叉核对待数据）：
- 单测 24/24（schema/service/router 三层：时间缺省回填、自动选窗三分支、空数据短路、pct 计算、failure_modes 过滤排序截断、422）；全量回归 156 通过（1 个存量失败经 HEAD 基线 worktree 对照确认与本批次无关）
- 三个新聚合的等价 SQL 在真实 PG 语法/列名验证通过（components coalesce 分组 / pods max(pod_name) 分组 / epoch floor 分桶）
- 响应规模按设计约束：components ≤ 组件枚举、top_* ≤ top_n、peak 单窗，最坏（top_n=50）<10KB，与 hit 行数解耦
- ⚠️ 数值交叉核对阻塞：库中暂无 BRPC 诊断 batch 数据（node48 为 KVCache 日志），待 ubsocket 诊断任务产出后补验 components 合计 / top_pods 一致性 / peak 与 timeline 尖峰一致性
- 教学切换完成：brpc SKILL 阶段 1.5 + 阶段二表格 summary 先行、报告 SKILL BRPC 分支 statistics 行、agents 主指令 BRPC 分诊规则、BRPC API 输入规则段

### 11.3 component_src 源码取证（契约冻结，实施阻塞于源码包接入）

报告 SKILL 已引用 `GET /diagnosis/component_src/{component}/{filename}`（当前"后端暂未落地，不可用时 source_code 设为 null"）。HTTP 契约定稿：

- **参数**：`component`（ubsocket/umq/urma 等）、`filename`；可选 `start_line` / `end_line`（默认全文件）
- **响应**：`{"content": "<源码文本>", "total_lines": 1024, "start_line": 1, "end_line": 1024}`；文件不存在 → 404
- **实施阻塞点**：组件源码包的接入与注册方案（目录约定 / 入库表 / 按 kb 还是全局）需先定——本节只冻结 HTTP 契约，源码包接入另行设计
- **消费方**：报告 SKILL 源码取证板块（`source_code` 从 null 兜底变为真实取数）

### 11.4 MCP 适配层（可选，批次 3）

在现有 FastAPI 上挂 `/mcp`（streamable HTTP），把 `/trace/list`、`/trace/{trace_id}`、`/stats/stages`（+ 批次 2 端点）映射为 MCP tools；skills 改为优先 MCP 工具、curl fallback，省去 TOOL_REFERENCE 的调用教学文档并消灭 curl 拼写出错。端点少而原子，MCP 化收益/代价比最优。切换策略：skills 文档保留 curl 用法作为降级路径，MCP 工具不可用时不阻塞诊断。
