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
  version: "2.2"
  keywords: [时延分析, 高时延, P99, 延迟升高, 慢查询, KVC, 分布式缓存, 时间窗口, IP对聚合, GET, SET, 读写分离]
allowed-tools: >
  Bash(curl:*) Bash(cd:*)
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
初始关键词检索本地经验，作为**先验假设**输入（不能替代现场证据）。

```bash
cd witty_ub_diagnostician/.opencode/skills/experience-skill/scripts

# 时延相关关键词（用户提什么就换什么，如 P99、慢查询、延迟升高、超时）
uv run experience-skill search-experiences \
    --query "P99 延迟升高 慢查询" --type SKILL --top-k 5
uv run experience-skill search-experiences \
    --query "KVC 分布式缓存 时延基线" --type WIKI --top-k 5
```

**对每条命中结果**（无论是否最终采用），按文末"经验引用标注模板"记录
基础信息，填入 `used_in_stage = "stage_0_pre_search"`。

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

**默认参数模板（用户未给出时间/IP时使用，均为 JSON body 字段）：**

```
kb_id:       <阶段一拿到的ID>          （必填）
log_id:      <阶段一该日志文件的 id>    （当前调查对应某日志文件时必传）
operation:   "GET"          （必填；GET 或 SET；读写分开分析）
stat_type:   "p99"          （时延异常首选百分位；若P99为空再试"ave"/"max"）
sort_fields: [{field: "total_latency", order: "desc"}]
page_cnt:    50             （保证覆盖 Top IP 对）
```

**GET/SET 操作区分**：
- `operation` 必填，用于区分读操作（GET）和写操作（SET/CREATE/PUBLISH）
- 读写操作的时延特征和瓶颈点可能不同，必须分别分析
- 用户未指定时，先查 GET，再查 SET，对比两者差异

**用户给了时间范围时：** 追加 `start_time` / `end_time`（`YYYY-MM-DD HH:MM:SS`）。
**用户给了具体 IP 时：** 追加 `src_ip` / `dst_ip`，跳过广度扫描直接进入阶段四。

**返回结果关注点：**
- 取前 5~10 条显著高值，记录 `id`（= aggregated_event_id，下一阶段要用）
- 记录 `src_ip`, `dst_ip`, `total_latency`，以及各时延分量（urma/worker_query_meta 等）

---

## 阶段三：时间维度 — 定位延迟升高的具体窗口

### 核心工具：`POST /aggregated_event/list_time_window`

对阶段二标记的可疑 IP 对逐一调用（JSON body）：

```
kb_id:       <ID>
operation:   <阶段二的 operation>（必填；GET 或 SET）
src_ip/dst_ip:  <阶段二的 IP>（不填=全量观察整体趋势）
interval:    "minute"         （默认；>几小时故障用"hour"；<几分钟尖峰用"second"）
stat_type:   "p99"
sort_by:     "start_time"
sort_order:  "asc"            （asc 便于画时间线）
page_cnt:    100
```

**诊断要点：**
1. 识别 P99 跳变 > 2× 相邻窗口的**尖峰时段**
2. 与用户报告的故障时间对齐
3. **多 IP 对横向比较**：同时异常 = 公共依赖（网络/Worker/ETCD）；单个异常 = 端侧问题

---

## 阶段四：深度下钻 — 异常日志 + 指标量化证据

### 4.1 按聚合事件查异常日志：`POST /log_parse_result/list`

对阶段二拿到的 `aggregated_event_id` 调用（JSON body）：

```
kb_id:                <ID>
log_id:               <该日志文件的 id>（必传）
operation:            <阶段二的 operation>（必填；GET 或 SET）
aggregated_event_id:  <阶段二的 id>（可选；按聚合事件下钻时传）
is_anomalous:         true
page_cnt:             50
```

> 注意：该接口不存在 `exclude_normal`、`sort_by`、`sort_order`、`error_priority`
> 参数，不要臆造。

**返回重点字段（诊断证据来源）：**
| 字段 | 含义 |
|------|------|
| `trace_id` | 唯一请求标识 |
| `total_latency` / `urma_total_latency` / `worker_query_meta_latency` | 定位瓶颈在哪个阶段（网络 / Worker 元数据 / 存储层） |
| `src_ip`, `dst_ip`, `host`, `pod`, `cluster` | 故障域 |
| `anomaly_components` | 被标记异常的时延组件 |
| `anomaly_score`, `error_priority` | 异常严重等级 |

### 4.2 用户指定具体 trace/host/IP 时：

直接传 `trace_id` / `host` / `src_ip` / `dst_ip` 给 `POST /log_parse_result/list`，
先 `is_anomalous=true`，无结果再放宽为 `null/false`。

### 4.3 量化时间序列：`POST /log_parse_result/metrics/latency`

```
kb_id:       <ID>        （必填）
log_id:      <该日志文件的 id>（必传，= 阶段一 log_file.id，勿用文件名/路径/任务ID）
operation:   必填 "GET" 或 "SET"；读写分开观察
host/src/dst: <缩小范围，可空>
sample_mode: "p99"（尖峰） / "ave"（趋势） / "max"（最坏）
max_points:  1000（默认），细粒度可提至 5000；仅需完整数据时用 -1
```

**GET/SET 对比分析**：
- 分别查询 GET 和 SET 的指标，对比时延差异
- 若仅一种操作异常，瓶颈可能与特定操作路径相关（如 SET 的持久化、GET 的缓存查找）
- 若两者同时异常，可能是公共依赖问题（网络、Worker、存储层）

> ⚠️ 返回含 `sampling_metadata` 时，报告中必须注明"采样数据"，勿描述为原始全量。

### 4.4 反证检查（强制）

对每条候选根因，主动查反例：
- 怀疑 Worker 瓶颈 → 查同时段其他客户端连此 Worker 的延迟是否也升
- 怀疑网络 → 查同 host 其他 Pod 的延迟

---

## 阶段五：经验库二次检索（诊断后，引用必须标注）

**在形成候选根因和处理建议之后**，用阶段二~四发现的**更精确的新关键词**
（如具体异常组件名、Host、时延分量、关键日志短语）再次检索经验库：

```bash
cd witty_ub_diagnostician/.opencode/skills/experience-skill/scripts

# 示例：用发现的异常组件 worker_query_meta 作精确检索
uv run experience-skill search-experiences \
    --query "worker_query_meta latency P99" --type SKILL --top-k 5
uv run experience-skill search-experiences \
    --query "URMA 延迟 基线" --type WIKI --top-k 5
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
| `POST /diagnosis_case/search` | 有初略信号（IP/host/异常组件）时查历史案例 | 结果是假设，必须对现场证据；用 `fault_type="latency"` |
| `GET /diagnosis_case/{case_id}` | 搜索命中高相关案例时做完整复核 | |

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

- 所有 `sort_fields` 元素的 `field` 必须是非空字符串，`order` 只能是 `asc` 或 `desc`。
- `POST /aggregated_event/list`
  - `kb_id` 必填。
  - 当前调查对应阶段一某个日志文件时，同时显式传该文件的 `id` 作为 `log_id`；多个相关文件分别查询。
  - `operation` 只能是 `GET` 或 `SET`。
  - `stat_type` 只能是 `p99`、`p95`、`ave`、`min` 或 `max`，未指定时显式传 `p99`。
  - 未指定 `sort_fields` 或其值为空时，显式传 `[{"field": "total_latency", "order": "desc"}]`。
- `POST /aggregated_event/list_time_window`
  - `kb_id` 必填。
  - `operation` 只能是 `GET` 或 `SET`；`interval` 只能是 `second`、`minute` 或 `hour`。
  - `stat_type` 同上，未指定时显式传 `p99`。
  - `sort_by` 只能是 `start_time` 或 `total_latency`；`sort_order` 只能是 `asc` 或 `desc`。
- `POST /log_parse_result/list`
  - `kb_id` 必填，`operation` 只能是 `GET` 或 `SET`。
  - 未指定 `is_anomalous` 时显式传 `true`。
- `POST /log_parse_result/metrics/latency`
  - `kb_id` 必填，`operation` 只能是 `GET` 或 `SET`。
  - 完成 `POST /log_file/list/{kb_id}` 后，必须把当前相关日志文件对象的 `id` 作为 `log_id` 显式传入；`log_file.id` 与请求字段 `log_id` 是同一个值，不得改用文件名、路径、任务 ID，也不得因 OpenAPI 标 `log_id` 可选而省略。
  - 有多个相关日志文件时，逐文件查询并标明结果归属，不得任取一个代表整个知识库。
  - `max_points` 只能是 `-1`，或 1 到 5000 的整数。
- `POST /diagnosis_case/search` 的 `fault_type` 只能是 `latency`、`connectivity`、`mixed` 或 `unknown`。

## 时延标准流程补充

以下规则与阶段流程并列生效：

1. **`log_id` 传递**：阶段一记录每个相关日志文件的 `id`；后续凡请求 schema 支持 `log_id` 且调查范围是该日志文件时，都必须把该 `id` 作为 `log_id` 传入，尤其是 `POST /log_parse_result/metrics/latency`、`POST /aggregated_event/list` 和 `POST /log_parse_result/list`。不要把 `task_id` 与 `log_id` 混淆。只有 API 确实不支持 `log_id`，或用户明确要求跨文件的知识库级汇总时，才用 `kb_id` 范围；多日志文件且每次仅接受一个 `log_id` 时，逐文件查询再比较。
2. **Trace 直查优先**：用户提供 trace ID（单个或列表）或明确想查满足条件的具体 trace 时，跳过聚合事件定位，直接调用 `POST /log_parse_result/list`。即使聚合查询为零、聚合事件未包含该 trace，仍应执行 trace 直查。
3. **时延分支顺序**：先 `POST /log_parse_result/metrics/latency` 确认整体趋势和峰值时段，首次请求就必须同时传 `kb_id` 和 `log_id`（不能先省略 `log_id`、空结果后再补传）；再用 `POST /aggregated_event/list_time_window` 查窗口统计并比较同一窗口内 IP 对；用 `POST /aggregated_event/list` 定位受影响源/目的 IP 对（其时间参数用于筛选该时段出现过的聚合事件，时间范围内的统计值以 `list_time_window` 为准）；最后用 `POST /log_parse_result/list` 下钻。需要异常记录时显式 `is_anomalous=true`；需要正常样本对照时 `is_anomalous=false`，不要使用不存在的 `exclude_normal` 或 `error_priority`。
4. **采样透明**：调用指标 API 时记录 `sample_mode`、`max_points` 和响应中的采样元数据；只有明确需要完整数据时才用 `max_points=-1`。
5. **空指标核验**：若 metrics 返回 `total=0` 或 `original_count=0`，先核对 `log_id` 是否等于当前 `log_file.id`，并与日志文件的 `anomaly_cnt`、解析任务状态以及 trace/聚合查询交叉验证；只要这些证据显示存在已解析异常，就必须把空指标视为数据路径或统计口径不一致的信号，继续核验 OpenAPI 契约和其他只读端点并如实报告，不能据此宣布健康。
6. **时延/通断交叉验证**：对时延记录返回的 trace ID，调用 `POST /log_failure_event_result/list_trace_events`（body 传 `trace_ids`）检查是否同时存在通断故障。不能因为两个现象时间接近就认定为同一请求或存在因果关系。

---

## 附录 A：experience-skill 引用标注模板（强制）

**任何时候**引用了 `experience-skill` 知识库（SKILL 或 WIKI）的内容，
无论是用于根因假设、处理建议、还是参考了基线/阈值，都必须按以下 JSON 模板
记录**每条**引用。该记录将被 `diagnostic-report-generation` Skill 直接
采集并写入报告的 `chapter_0_experience_refs` 章节。

### JSON 模板（每条引用一个对象，汇总为数组）

```json
{
  "experience_refs": [
    {
      "experience_id": "<来自 Experience.id 的 UUID，必填>",
      "experience_type": "SKILL | WIKI",
      "name": "<来自 Experience.name>",
      "source_path": "<来自 Experience.source，如 data/skill_hub/ds-kv-cache-diagnosis/skill_def.md>",
      "keywords_matched": ["<检索该条经验时用的关键词，用于可追溯>"],
      "search_query_used": "<完整的 search-experiences --query 值>",
      "used_in_stage": "stage_0_pre_search | stage_5_post_search | stage_4_root_cause | stage_5_recommendation",
      "adoption_status": "adopted_as_evidence | adopted_as_suggestion | considered_not_adopted",
      "content_quoted": "<直接引用经验中的原文片段，≤200字；严禁超长粘贴>",
      "how_used_in_diagnosis": "<一句话说明：用在根因排序/处理方案/阈值对比……，如 采用该经验的 Worker 磁盘阈值判断 host-101 为异常>",
      "confidence_on_reference": 0.0 ~ 1.0,
      "confidence_reason": "<为何信任此条：与现场证据相符 / 来自 curated Skill / 有历史案例佐证>"
    }
  ]
}
```

### 字段说明（基于 `Experience` schema）

| 字段 | 来源（Experience / search 结果） | 约束 |
|------|---------------------------------|------|
| `experience_id` | `Experience.id` | 必填，UUID |
| `experience_type` | `Experience.type` | 必填，枚举 SKILL/WIKI |
| `name` | `Experience.name` | 必填，非空 |
| `source_path` | `Experience.source` | 必填，可追溯到 `data/skill_hub/.../skill_def.md` 或 `data/wiki_hub/...md` |
| `keywords_matched` | 人工记录 + `Experience.keywords` 交集 | 非空数组 |
| `search_query_used` | 执行 search-experiences 的 --query | 必填，可完全复现检索 |
| `used_in_stage` | 人工标记诊断阶段 | 严格按枚举值 |
| `adoption_status` | — | adopted_as_evidence = 影响了根因结论；adopted_as_suggestion = 仅用于建议；considered_not_adopted = 考虑过但未采用（必须填原因） |
| `content_quoted` | 原文摘录 | ≤200字；不允许用"省略号"/"大意如下"，必须是原文片段 |
| `how_used_in_diagnosis` | 人工描述 | ≤100字，说清楚引用 → 诊断结论的因果链 |
| `confidence_on_reference` | 人工打分 | 0.0~1.0，精度 0.01 |
| `confidence_reason` | 人工描述 | ≤100字 |

### 三条铁律

1. **用了必记，记必可追溯**：只要引用了经验（哪怕一句话），必须记录；
   `experience_id` + `source_path` 必须能唯一定位到源文件。
2. **经验 ≠ 证据**：`adopted_as_evidence` 需极度谨慎。经验库内容只有
   在被 HTTP API 返回的**现场事实**（trace / metrics / logs）验证后，
   才能升格为"证据"；否则只能是 suggestion 或 hypothesis。
3. **不采用也要说明原因**：检索命中但最终没用的，也要记录
   `considered_not_adopted` + 排除理由。这是避免"选择性忽略反例"
   的关键手段。
