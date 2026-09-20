---
name: latency-analysis
description: >
  通过 HTTP API 进行 KVC 分布式缓存的时延异常诊断。
  引导用户按四阶段流程调用 HTTP API：知识库定位 → IP 对高时延聚合扫描 →
  时间窗口分析 → 异常日志与指标下钻。当用户提出"高时延"、"慢查询"、
  "延迟升高"、"P99 抖动"、"请求超时"等问题时，优先使用本 Skill。
license: HUAWEI
compatibility: >
  Requires HTTP API access to FastAPI backend on port 9772 via bash curl.
metadata:
  author: witty-ub-diagnostician
  version: "2.3"
  keywords: [时延分析, 高时延, P99, 延迟升高, 慢查询, KVC, 分布式缓存, 时间窗口, IP对聚合, GET, SET, 读写分离, RPC阶段, bRPC]
allowed-tools: >
  Bash(curl:*) Bash(cd:*) Bash(python3:*)
  experience-skill
---

# 时延异常诊断 (Latency Analysis)

引导 Agent 按**四阶段流程**顺序调用 HTTP API 的时延类接口，
从广度扫描到深度下钻，避免在海量日志中盲目查询。

**强制要求**：凡引用了 `experience-skill` 知识库（SKILL 或 WIKI）的内容，
**必须**按本文末尾的引用标注规则逐条记录；不得把经验库的内容冒充现场证据
或通用知识。

---

## 阶段 0：经验库预检索（诊断前）

**在调用任何诊断接口之前**，先用 `experience-skill` 基于用户提供的
初始关键词检索本地经验，作为**先验假设**输入（不能替代现场证据）：

```bash
cd witty_ub_diagnostician/.opencode/skills/experience-skill/scripts
# 关键词随用户问题替换（如 P99、慢查询、延迟升高、超时）
uv run experience-skill search-experiences \
    --query "P99 延迟升高 慢查询" --type SKILL --top-k 5
```

**对每条命中结果**（无论是否最终采用），按文末附录 A 记录，
填入 `used_in_stage = "stage_0_pre_search"`。

---

## 阶段一：数据准备 — 先确认数据完整性

**任何诊断前必须先做此步。空结果 ≠ 系统健康。**

| 步骤 | 查询接口 | 关键参数 | 目的 |
|------|---------|---------|------|
| 1.1 | `POST /log_kb/list` | `created_sorted_desc=true`, `page_cnt=20` | 找到最新/匹配的知识库 `kb_id` |
| 1.2 | `GET /log_kb/{kb_id}` | — | 二次校验知识库元数据，避免对错数据集操作 |
| 1.3 | `POST /log_file/list/{kb_id}` | 不按状态过滤（看全部） | 检查每个文件的 `overall_status` 是否为 `successful`，记录 `task.id` 与 `log_file.id`（后续作 `log_id` 用） |
| 1.4 | `GET /task/{task_id}` | — | 若 overall_status≠successful，查进度/报告并声明"结论基于不完整数据" |
| 1.5 | `GET /log_parse_result/options` | `kb_id` | 获取真实存在的 cluster/host/pod 值，禁止臆测名称 |

---

## 阶段二：广度扫描 — IP 对聚合定位 Top 高时延点

### 核心工具：`POST /aggregated_event/list`

按源/目的 IP 对聚合时延。关键决策：`stat_type` 首选 `p99`（空值再降
`ave`/`max`）；`sort_fields` 用 `total_latency` 降序；`page_cnt` 50
覆盖 Top IP 对。完整参数表见 `references/TOOL_REFERENCE.md`。

**GET/SET 操作区分**：
- `operation` 必填，区分读（GET）/写（SET/CREATE/PUBLISH）操作；读写路径与可观测字段都不同，必须分别分析
- 用户未指定时，先查 GET，再查 SET，对比两者差异
- `/stats/stages` 是**按 operation 的独立视角**（GET 8 桶 / SET 5 桶，key 不重叠）：两次各调一次，**禁止跨 operation 混合归桶**——SET 写路径走 CREATE/PUBLISH，与 GET 的 8 维读路径公式不通用

**用户给了时间范围时**：追加 `start_time` / `end_time`（`YYYY-MM-DD HH:MM:SS`）。
**用户给了具体 IP 时**：追加 `src_ip` / `dst_ip`，跳过广度扫描直接进入阶段四。

**返回结果关注点**：取前 5~10 条显著高值，记录 `id`（= aggregated_event_id，
下一阶段要用）、`src_ip`/`dst_ip`、`total_latency` 及各时延分量
（urma/worker_query_meta 等）。

---

## 阶段三：时间维度 — 定位延迟升高的具体窗口

### 核心工具：`POST /aggregated_event/list_time_window`

对阶段二标记的可疑 IP 对逐一调用（不填 IP = 全量观察整体趋势）。
关键决策：`interval` 默认 `minute`（>几小时故障用 `hour`，<几分钟尖峰用
`second`）；`stat_type` 用 `p99`；按 `start_time` 升序便于画时间线。
完整参数表见 `references/TOOL_REFERENCE.md`。

**诊断要点：**
1. 识别 P99 跳变 > 2× 相邻窗口的**尖峰时段**
2. 与用户报告的故障时间对齐
3. **多 IP 对横向比较**：同时异常 = 公共依赖（网络/Worker/ETCD）；单个异常 = 端侧问题

---

## 阶段四：深度下钻 — 异常日志 + 指标量化证据

### 4.1 按聚合事件查异常日志：`POST /log_parse_result/list`

对阶段二拿到的 `aggregated_event_id` 下钻：`log_id` 必传、
`is_anomalous=true`、`page_cnt` 50。完整参数表见 `references/TOOL_REFERENCE.md`。

> 注意：该接口不存在 `exclude_normal`、`sort_by`、`sort_order`、`error_priority`
> 参数，不要臆造。

**返回重点字段（诊断证据来源）**：`trace_id`（唯一请求标识）；时延分量
`total_latency` / `urma_total_latency` / `worker_query_meta_latency`
（定位瓶颈在网络 / Worker 元数据 / 存储层）；`src_ip`/`dst_ip`/`host`/
`pod`/`cluster`（故障域）；`anomaly_components`；`anomaly_score`、
`error_priority`（异常严重等级）。

### 4.2 用户指定具体 trace/host/IP 时：

直接传 `trace_id` / `host` / `src_ip` / `dst_ip` 给 `POST /log_parse_result/list`，
先 `is_anomalous=true`，无结果再放宽为 `null/false`。

### 4.3 量化时间序列：`POST /log_parse_result/metrics/latency`

`kb_id` + `log_id`（= 阶段一 `log_file.id`，勿用文件名/路径/任务 ID）必传，
首次请求就同时传；`operation` 读写分开观察；`sample_mode` 按 `p99`（尖峰）/
`ave`（趋势）/`max`（最坏）选取；`max_points` 默认 1000，细粒度可提至 5000，
仅确需完整数据时用 `-1`。

**GET/SET 对比分析**：
- 分别查询 GET 和 SET 的指标，对比时延差异
- 若仅一种操作异常，瓶颈可能与特定操作路径相关（如 SET 的持久化、GET 的缓存查找）
- 若两者同时异常，可能是公共依赖问题（网络、Worker、存储层）

> ⚠️ 返回含 `sampling_metadata` 时，报告中必须注明"采样数据"，勿描述为原始全量。

### 4.4 反证检查（强制）

对每条候选根因，主动查反例：
- 怀疑 Worker 瓶颈 → 查同时段其他客户端连此 Worker 的延迟是否也升
- 怀疑网络 → 查同 host 其他 Pod 的延迟

### 4.5 bRPC RPC 阶段深挖脚本（客户端等待主导时使用）

**触发条件**：阶段四发现异常集中在客户端侧等待（worker 侧分量干净、
total≈sdk 处理窗口），需要进一步区分 QueryMeta / RPC网络 / RPC排队 /
Master元数据写 / DataWorker / URMA链路 时，调用本脚本。
KVC 解析管线当前未入库新版 bRPC perf 行（`[BRPC_RPC_FRAMEWORK_SLOW]`，
19 字段格式，嵌于 `ds_client_*.INFO.log`），本脚本旁路直扫原始日志补齐该维度。

```bash
cd witty_ub_diagnostician/.opencode/skills/latency-analysis/scripts

# 输入 = 原始日志目录或上传 zip（须含 ds_client_*.INFO.log；预处理目录清理后用原始 zip）
python3 brpc_stage_drill.py <日志目录|zip> --slow-ms 20 --failed-only --top 5

# 常用过滤：
#   --slow-ms 1.5    慢 RPC 阈值(ms)，按 trace 内最大 e2e 过滤（默认 1.5）
#   --failed-only    只统计含失败 RPC（cntl_failed=1）的 trace
#   --json out.json  结果另存 JSON（供报告生成）
```

**输出解读**：
- **桶分布**：每条 trace 按 winner-take-all 归入唯一主导桶
  （QueryMeta / RPC网络 / RPC排队 / Master元数据写 / DataWorker处理 / URMA链路），
  每桶附治理指引文案，可直接用于报告建议章节。
- **阶段拆解口径**：QueryMeta = QueryAndGet 的 `e2e − 框架分量`
  （框架分量 = network_residual + server_req_queue + client_req_framework；
  超时无响应时三分量无测量为 0，QueryMeta 吸收全额等待，与瓶颈脚本口径一致）。
- **RPC 错误码分布**：`1008` = deadline 截止（即"RPC截止超时"），`2001`/`110`
  结合现场判断。
- **每桶 top 样例 trace**：可回填 `POST /log_parse_result/list(trace_id=...)`
  取该 trace 的完整明细做交叉验证。

**注意**：
1. 脚本只依赖 Python 标准库，秒级完成（GB 级日志约分钟级）；
2. `getBuffer-*` trace 的 RPC 子过程为 QueryAndGet（GET 路径查元数据），
   `setStringView-*` 为 Create/Publish（SET 路径写元数据）——桶归属解读时注意路径差异；
3. 本脚本结果与 `/stats/stages`（DB 轻量粗分）互补：API 出方向，脚本出 RPC 细分归因。

---

## 阶段五：经验库二次检索（诊断后，引用必须标注）

**在形成候选根因和处理建议之后**，用阶段二~四发现的**更精确的新关键词**
（如具体异常组件名、Host、时延分量、关键日志短语）再次检索：

```bash
cd witty_ub_diagnostician/.opencode/skills/experience-skill/scripts
uv run experience-skill search-experiences \
    --query "worker_query_meta latency P99" --type SKILL --top-k 5
```

**关键规则**：
1. 若二次检索命中的经验内容**被采用进了根因/解决方案**，必须标注为
   `used_in_stage = "stage_5_post_search"`，并记录具体引用的内容片段。
2. 若命中但**未采用**（与现场证据不符），也要记录为
   `used_in_stage = "stage_5_post_search"`，并在 `adoption_status` 中标注
   `"considered_not_adopted"` + 原因（如"与当前 trace 的异常组件不一致"）。
3. **不得**将经验库的结论直接当作现场证据；必须写明：
   "经验库 X 建议根因为 Y，但本次现场证据是 Z，两者相符/不符，故……"

---

## 交叉辅助工具（按需使用，非强制顺序）

| 接口 | 何时用 | 注意点 |
|------|--------|--------|
| `POST /diag_case_library/search` | 有初略信号（IP/host/异常组件）时查历史案例 | 只返回已人工确认的案例；结果是假设，仍须对现场证据；用 `fault_type="latency"` |
| `GET /diag_case_library/{case_id}` | 搜索命中高相关案例时做完整复核 | |
| `POST /diagnosis_case/search`（降级） | 确认案例库无结果时的兜底 | 旧表**未经人工确认**、内容物薄，引用必须标注来源 |

---

## 典型入口场景速查

| 用户问题 | 第一步接口 | 后续串联 |
|---------|-----------|---------|
| "P99 最近很高" | `POST /log_kb/list` → `POST /aggregated_event/list(operation="GET")` | 阶段二全量扫 Top IP → 阶段三时间窗口 → 阶段四下钻；再查 `operation="SET"` 对比读写差异 |
| "trace_id=t-abc 超时了" | `POST /log_kb/list` → `POST /log_parse_result/list(trace_id="t-abc", operation="GET")` | 跳过阶段二/三，直接看该 trace 的分量延迟；根据实际操作类型调整 `operation` 参数 |
| "10.0.0.5 → 10.0.0.8 很慢" | `POST /aggregated_event/list(src_ip="10.0.0.5", dst_ip="10.0.0.8", operation="GET")` | 拿到 aggregated_event_id 后时间窗口 + 下钻日志；分别用 GET/SET 查询对比 |
| "pod-worker-3 延迟异常" | `GET /log_parse_result/options` 确认 pod 对应的 host → `POST /log_parse_result/list(host=, operation="GET")` | 或用 `POST /log_parse_result/metrics/latency(host=, operation="GET")` 看趋势；GET/SET 分别观察 |
| "GET 和 SET 哪个更慢" | `POST /aggregated_event/list(operation="GET")` + `POST /aggregated_event/list(operation="SET")` | 分别查询读写操作的时延，对比 P99/AVE 差异，定位瓶颈是否与特定操作路径相关 |

---

## 时延 API 输入规则

以下约束必须遵守，即使 OpenAPI schema 将参数标为可选，也按此显式传参。
完整参数表见 `references/TOOL_REFERENCE.md`。

- 所有 `sort_fields` 元素的 `field` 必须是非空字符串，`order` 只能是 `asc` 或 `desc`。
- `POST /aggregated_event/list`：`kb_id` 必填；调查对应某日志文件时显式传该文件
  `id` 作 `log_id`；`operation` 只能 GET/SET；`stat_type` 限 `p99/p95/ave/min/max`，
  未指定时显式传 `p99`；未指定 `sort_fields` 时显式传
  `[{"field": "total_latency", "order": "desc"}]`。
- `POST /aggregated_event/list_time_window`：`kb_id` 必填；`operation` 只能
  GET/SET；`interval` 限 `second/minute/hour`；`stat_type` 同上；`sort_by` 限
  `start_time/total_latency`；`sort_order` 限 `asc/desc`。
- `POST /log_parse_result/list`：`kb_id` 必填；`operation` 只能 GET/SET；
  未指定 `is_anomalous` 时显式传 `true`。
- `POST /log_parse_result/metrics/latency`：`kb_id` 必填；`operation` 只能
  GET/SET；`log_id` 必传（= `log_file.id`，不得改用文件名、路径、任务 ID）；
  有多个相关日志文件时逐文件查询并标明结果归属，不得任取一个代表整个
  知识库；`max_points` 只能 `-1` 或 1~5000 的整数。
- `POST /diag_case_library/search`（及降级的 `POST /diagnosis_case/search`）的 `fault_type`
  只能是 `latency`、`connectivity`、`mixed` 或 `unknown`。

## 时延标准流程补充

以下规则与阶段流程并列生效：

1. **`log_id` 传递**：阶段一记录每个相关日志文件的 `id`；后续凡请求 schema 支持 `log_id` 且调查范围是该日志文件时，都必须把该 `id` 作为 `log_id` 传入，尤其是 `POST /log_parse_result/metrics/latency`、`POST /aggregated_event/list` 和 `POST /log_parse_result/list`。不要把 `task_id` 与 `log_id` 混淆。只有 API 确实不支持 `log_id`，或用户明确要求跨文件的知识库级汇总时，才用 `kb_id` 范围；多日志文件且每次仅接受一个 `log_id` 时，逐文件查询再比较。
2. **Trace 直查优先**：用户提供 trace ID（单个或列表）或明确想查满足条件的具体 trace 时，跳过聚合事件定位，直接调用 `POST /log_parse_result/list`。即使聚合查询为零、聚合事件未包含该 trace，仍应执行 trace 直查。
3. **时延分支顺序**：先 `POST /log_parse_result/metrics/latency` 确认整体趋势和峰值时段，首次请求就必须同时传 `kb_id` 和 `log_id`（不能先省略 `log_id`、空结果后再补传）；再用 `POST /aggregated_event/list_time_window` 查窗口统计并比较同一窗口内 IP 对；用 `POST /aggregated_event/list` 定位受影响源/目的 IP 对（其时间参数用于筛选该时段出现过的聚合事件，时间范围内的统计值以 `list_time_window` 为准）；最后用 `POST /log_parse_result/list` 下钻。需要异常记录时显式 `is_anomalous=true`；需要正常样本对照时 `is_anomalous=false`，不要使用不存在的 `exclude_normal` 或 `error_priority`。
4. **采样透明**：调用指标 API 时记录 `sample_mode`、`max_points` 和响应中的采样元数据；只有明确需要完整数据时才用 `max_points=-1`。
5. **空指标核验**：若 metrics 返回 `total=0` 或 `original_count=0`，先核对 `log_id` 是否等于当前 `log_file.id`，并与日志文件的 `anomaly_cnt`、解析任务状态以及 trace/聚合查询交叉验证；只要这些证据显示存在已解析异常，就必须把空指标视为数据路径或统计口径不一致的信号，继续核验 OpenAPI 契约和其他只读端点并如实报告，不能据此宣布健康。
6. **时延/通断交叉验证**：对时延记录返回的 trace ID，调用 `POST /log_failure_event_result/list_trace_events`（body 传 `trace_ids`）检查是否同时存在通断故障。不能因为两个现象时间接近就认定为同一请求或存在因果关系。

---

## 附录 A：experience-skill 引用标注（强制）

凡引用 `experience-skill`（SKILL/WIKI）的内容——根因假设、处理建议、
阈值/基线参考——**每条**都必须按统一 JSON 模板逐条记录；记录将被
`diagnostic-report-generation` 采集写入报告 `chapter_0_experience_refs` 章节。

**完整 JSON 模板、字段说明与铁律见
`experience-skill/references/CITATION_TEMPLATE.md`**。铁律要点：用了必记且
可追溯；经验 ≠ 证据，未经现场事实验证只能是 suggestion；检索命中但未采用
也要记录 `considered_not_adopted` + 原因。

本 Skill 的 `used_in_stage` 枚举：`stage_0_pre_search` / `stage_5_post_search` /
`stage_4_root_cause` / `stage_5_recommendation`。
