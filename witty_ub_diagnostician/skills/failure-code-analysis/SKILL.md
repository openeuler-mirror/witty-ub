---
name: failure-code-analysis
description: >
  通过 HTTP API 进行 KVC 分布式缓存的通断故障
  （connectivity fault）与错误码诊断。引导按五阶段流程调用 HTTP API：
  知识库定位 → 时间窗口故障聚合 → Pod 维度 Top N 排序 → 错误码量化与
  Trace 下钻 → 状态码/故障模式知识库解读。当用户提出"连接失败"、"状态码异常"、
  "请求报错 ERR_xxx"、"通断率上升"、"trace 故障"、"错误码增多"等问题时，
  优先使用本 Skill。
license: HUAWEI
compatibility: >
  Requires HTTP API access to FastAPI backend on port 9772 via bash curl.
metadata:
  author: witty-ub-diagnostician
  version: "2.1"
  keywords: [故障码, 通断故障, 状态码, connectivity, 错误码, status_code, failure_mode, trace, ERR, 连接失败]
allowed-tools: >
  Bash(curl:*) Bash(cd:*)
  experience-skill
---

# 故障码与通断诊断 (Failure Code & Connectivity Analysis)

引导 Agent 按**五阶段流程**顺序调用 HTTP API 的故障码类接口，
从时间定位 → 故障域识别 → 证据下钻 → 知识解读，层层收敛。

**强制要求**：凡引用了 `experience-skill` 知识库（SKILL 或 WIKI）的内容，
**必须**按本文末尾的引用标注规则逐条记录；不得把经验库的内容冒充现场证据
或 curated 知识库（`GET /failure_mode/status_code/{status_code}` / `GET /failure_mode/{failure_mode_id}`）的内容。

---

## 阶段 0：经验库预检索（诊断前）

**在调用任何诊断接口之前**，先用 `experience-skill` 基于用户提供的
初始关键词检索本地经验，作为**先验假设**输入（不能替代现场证据）：

```bash
cd witty_ub_diagnostician/.opencode/skills/experience-skill/scripts
# 关键词随用户问题替换（如 ERR_xxx、连接失败、状态码 -1002）
uv run experience-skill search-experiences \
    --query "连接失败 ERR_UNAVAILABLE status_code" --type SKILL --top-k 5
```

**对每条命中结果**（无论是否最终采用），按文末附录 A 记录，
填入 `used_in_stage = "stage_0_pre_search"`。

---

## 阶段一：数据准备 — 先确认数据完整性

**任何诊断前必须先做此步。空结果 ≠ 系统健康。**

| 步骤 | 查询接口 | 关键参数 | 目的 |
|------|---------|---------|------|
| 1.1 | `POST /log_kb/list` | `created_sorted_desc=true`, `page_cnt=20` | 定位知识库 `kb_id` |
| 1.2 | `GET /log_kb/{kb_id}` | — | 二次校验 |
| 1.3 | `POST /log_file/list/{kb_id}` | 不按状态过滤 | 检查 `overall_status` 与 fault 计数，记录 `task.id` 与 `log_file.id` |
| 1.4 | `GET /task/{task_id}` | — | overall_status≠successful 时查进度，声明"基于不完整数据" |
| 1.5 | `GET /log_parse_result/options` | `kb_id` | 获取真实 cluster/host/pod 值，禁止臆测 |

---

## 阶段二：时间定位 — 识别故障集中窗口

### 核心工具：`POST /log_failure_event_result/list_time_aggregated_failure_events`（通断诊断首步查询）

按时间窗口聚合所有故障码计数。关键决策：`interval` 默认 `minute`
（长时故障→`hour`；尖峰→`second`）；按 `timestamp` 升序便于画时间线；
`page_cnt` 100（长时段增大）。完整参数表见 `references/TOOL_REFERENCE.md`。

**operation 参数说明（GET vs SET）：**
- `"GET"`（默认）— 查询/读取类操作的故障（缓存未命中、读取超时、连接查询失败等）。**大多数诊断场景使用 GET。**
- `"SET"` — 写入/更新类操作的故障（缓存写入失败、数据更新超时、元数据同步异常等）。
- 用户未明确区分时默认 `"GET"`；明确提到"写入失败""更新异常"等写操作描述时改用
  `"SET"`。也可分别调用两次（GET 和 SET）对比分析。

**诊断要点：**
1. 找错误码显著高于相邻窗口的**尖峰时段**或**持续多窗口高值期**
2. 与用户报告的故障时间对齐，排除非故障时段的偶发干扰
3. 若呈现**周期性重复**（如每 5 分钟一次尖峰），记录周期特征
   （可能指向 ETCD lease 续约失败、定时任务冲突、心跳超时等）
4. **结果为空时**：返回阶段一核验 overall_status，或直接跳阶段四用
   `POST /log_failure_event_result/list_trace_events` 无时间过滤查

---

## 阶段三：故障域识别 — Pod / Host / Cluster 聚合

### 核心工具：`POST /log_failure_event_result/list_pod_aggregated_failure_events`

以阶段二识别的故障窗口（或用户给的明确时段）为时间范围：`sort_by`
用 `"all"`（综合；也可传具体错误码，如 1004、1009），`sort_desc=true`
取 Top N（`page_cnt` 30~50）。完整参数表见 `references/TOOL_REFERENCE.md`。

**返回重点字段**：`pod_name`/`host_name`/`cluster_name`（故障域三元组）、
每类错误码的计数与占比。

**故障扩散模式判断：**
| 模式 | 特征 | 可能根因层级 |
|------|------|-------------|
| 单点爆发 | 单 Pod 占 80%+ 错误 | Pod 级：进程异常、资源耗尽、本地存储损坏 |
| 同 Host 多 Pod | 错误集中在同一 host 的多个 pod | Host 级：OS 异常、网卡抖动、磁盘 IO 瓶颈 |
| 同 Cluster 多 Host | 跨 host 但同 cluster | 集群级：ETCD 不可达、Metastore 异常、控制面故障 |
| 全局均匀 | 所有 pod/host 均匀分布 | 客户端 / 网络 / DNS 等更上游 |

---

## 阶段四：错误码量化 + Trace 下钻

### 4.1 错误码频次与趋势：`POST /log_failure_event_result/metrics/err_code`

对阶段三中可疑的 Pod / Host / Cluster 调用：`err_codes` 传阶段三识别的
Top N 高频错误码（空=全量），时间范围用阶段二的故障窗口。
完整参数表见 `references/TOOL_REFERENCE.md`。

**返回分析要点：**
- 多错误码对比**爆发起点 / 峰值 / 回落时间**
- A 先涨 → B/C 随后涨 → **级联故障**（A 可能是根因，B/C 是派生失败）
- 多错误码**同时突发升高** → 共同根因（如网络断连导致所有操作失败）

> ⚠️ 返回含采样元数据时，报告中必须注明"采样数据"。

### 4.2 Trace 级故障详情：`POST /log_failure_event_result/list_trace_events`

以阶段二/三识别的时间范围与故障域筛选：`is_anomalous=true`（结果不足→
`null` 放宽）、`sort_desc=true`（最新/最严重优先）、`page_cnt` 50~100。
完整参数表见 `references/TOOL_REFERENCE.md`。

**返回重点字段（向下游传递的关键）：**
- `trace_id` → `POST /log_failure_event_result/list_log_events`（下钻原始日志）
- `status_code` → `GET /failure_mode/status_code/{status_code}`（查 curated 状态码解释）
- `failure_mode_id` → `GET /failure_mode/{failure_mode_id}`（查完整症状/根因/方案）
- `src_ip` / `dst_ip` / `host` / `pod` / `cluster` — 故障两端证据
- `timestamp` / `is_anomalous` / `anomaly_score` — 异常判定依据

### 4.3 原始日志证据：`POST /log_failure_event_result/list_log_events`

对阶段 4.2 中最具代表性的 trace（Top 错误码 × Top Pod 组合），
批量传入 `trace_ids`，**一次 ≤ 100 条**（`kb_id` 必填，`log_id` 可选）。

**原始日志使用原则：**
- 重点看日志原文中的 `src=xxx, dst=xxx` 对（若结构化返回中没解析，
  在原文中直接找）
- 看返回前后的上下文堆栈 / 错误描述 / 组件名称
- 时间戳与 4.2 的 trace 级结果**交叉验证一致**；不一致时以原始日志为准
- 引用时用摘要式："trace_id=xxx 的日志显示 `src=A dst=B err_msg='Connection refused'`"，**不要贴几百条全文**

---

## 阶段五：知识解读 — Curated 知识库 + 根因综合

### 5.1 状态码知识库：`GET /failure_mode/status_code/{status_code}`

对阶段四中出现的每类高频 `status_code` 逐一调用：
- **200 返回** → 记录 `symptom`（症状）和 `root_cause`（已知根因），
  与现场证据比对
- **404 返回** → 明确记录"该状态码未收录入 curated 知识库，
  结论仅基于现场证据和通用知识"，**不要妄加解释**

### 5.2 故障模式详情：`GET /failure_mode/{failure_mode_id}`

对阶段 4.2 中出现的 `failure_mode_id` 逐一调用，获取：
- `symptom` / `root_cause` / `solution` — 完整三件套
- `failure_domain` — 故障域分类（网络 / Pod / Host / Cluster / 组件）
- child failure_mode 关系 — 级联故障路径

### 5.3 根因综合输出

按置信度从高到低排序候选根因，每条必须具备：
1. **现场证据**（≥1 条来自 `POST /log_failure_event_result/list_trace_events` /
   `POST /log_failure_event_result/list_log_events` /
   `POST /log_failure_event_result/metrics/err_code` 的事实数据）
2. **反证检查**（尝试证伪未果的验证步骤）
3. **解决方案**（优先引用 `GET /failure_mode/{failure_mode_id}` 的 solution）
4. **知识来源**（failure_mode_id、或"现场证据推断"）

---

## 阶段六：经验库二次检索（诊断后，引用必须标注）

**在形成候选根因和处理建议之后**，用阶段二~五发现的**更精确的新关键词**
（如具体 status_code / failure_mode_id / Pod / Host / 关键错误短语）
再次检索经验库：

```bash
cd witty_ub_diagnostician/.opencode/skills/experience-skill/scripts
uv run experience-skill search-experiences \
    --query "status_code -1002 K_RPC_UNAVAILABLE" --type SKILL --top-k 5
```

**关键规则**：
1. 若二次检索命中的经验内容**被采用进了根因/解决方案**，必须标注为
   `used_in_stage = "stage_6_post_search"`，并记录具体引用的内容片段。
2. 若命中但**未采用**（与现场证据不符或与 `GET /failure_mode/{failure_mode_id}` 内容冲突），
   也要记录为 `used_in_stage = "stage_6_post_search"`，并在
   `adoption_status` 中标注 `"considered_not_adopted"` + 原因
   （如"`GET /failure_mode/{failure_mode_id}` 的 curated solution 更权威，未采用经验库方案"）。
3. **不得**将经验库的结论直接当作现场证据；必须写明：
   "经验库 X 建议根因为 Y，但本次现场证据是 Z，两者相符/不符，故……"
4. **特别注意**：经验库中对某 status_code 的解释**不得覆盖**
   `GET /failure_mode/status_code/{status_code}` 返回的 curated 官方解释。两者冲突时
   以 curated 为准，并在经验引用中标注 `"considered_not_adopted"` +
   冲突详情。

---

## 交叉辅助工具（按需使用）

| 接口 | 何时用 | 注意点 |
|------|--------|--------|
| `POST /diag_case_library/search` | 有初略信号时查历史案例 | 只返回已人工确认的案例；传 `fault_type="connectivity"`；结果是假设，必须现场验证 |
| `GET /diag_case_library/{case_id}` | 搜索命中高相关案例做完整复核 | |
| `POST /diagnosis_case/search`（降级） | 确认案例库无结果时的兜底 | 旧表**未经人工确认**、内容物薄，引用必须标注来源 |

---

## 典型入口场景速查

| 用户问题 | 第一步接口 | 后续串联 |
|---------|-----------|---------|
| "最近好多 ERR_xxx 错误" | `POST /log_failure_event_result/list_time_aggregated_failure_events` | 窗口定位 → `POST /log_failure_event_result/list_pod_aggregated_failure_events` → `POST /log_failure_event_result/metrics/err_code` → `POST /log_failure_event_result/list_trace_events` → `GET /failure_mode/status_code/{ERR_xxx}`。**operation 参数**：默认用 `"GET"`；若用户明确提到"写入失败""更新异常"等写操作问题，改用 `"SET"` |
| "返回码 -5 是什么意思" | `GET /failure_mode/status_code/-5` | 若 404 → 查 `POST /log_failure_event_result/list_trace_events(status_codes=["-5"])` 用现场数据推断 |
| "pod-abc-123 报错很多" | `GET /log_parse_result/options` 确认真实 pod 名 → `POST /log_failure_event_result/list_pod_aggregated_failure_events` | → `POST /log_failure_event_result/list_trace_events(pod_names=)` → `POST /log_failure_event_result/list_log_events` → `GET /failure_mode/{id}` |
| "failure_mode_id=FM-7 是什么" | `GET /failure_mode/FM-7` | 拿完整症状/根因/方案 → `POST /diag_case_library/search(failure_mode_ids=["FM-7"])` 查已确认的历史案例 |
| "trace_id=t-abc 失败了" | `POST /log_failure_event_result/list_log_events(trace_ids=["t-abc"])` | 直接拿原始日志证据（比先查 traces 更快） |

> GET/SET 取值规则见阶段二的 operation 参数说明。

---

## 通断 API 输入规则

以下约束必须遵守，即使 OpenAPI schema 将参数标为可选，也按此显式传参。
完整参数表见 `references/TOOL_REFERENCE.md`。

- 所有 `sort_fields` 元素的 `field` 必须是非空字符串，`order` 只能是 `asc` 或 `desc`。
- `POST /log_failure_event_result/list_time_aggregated_failure_events`：
  `kb_id` 必填；`interval` 限 `second/minute/hour`；`operation` 只能 GET/SET。
- `POST /log_failure_event_result/list_pod_aggregated_failure_events` 和
  `POST /log_failure_event_result/list_src_dst_aggregated_failure_events`：
  `kb_id` 必填；`operation` 只能 GET/SET。
- `POST /log_failure_event_result/list_trace_events`：`kb_id` 必填；
  `operation` 只能 GET/SET；未指定 `is_anomalous` 时显式传 `true`。
- `POST /log_failure_event_result/metrics/err_code`：`kb_id` 必填；
  `operation` 只能 GET/SET；`max_points` 必须是 1 到 5000 的整数。
- `POST /log_failure_event_result/list_log_events`：`trace_ids` 必填且
  包含 1 到 100 个 trace ID；`kb_id` 必填；`log_id` 可选，建议传以加速。
- `POST /diag_case_library/search`（及降级的 `POST /diagnosis_case/search`）的 `fault_type`
  只能是 `latency`、`connectivity`、`mixed` 或 `unknown`。

## 通断标准流程补充

以下规则与阶段流程并列生效：

1. **`log_id` 传递**：阶段一记录每个相关日志文件的 `id`。`POST /log_failure_event_result/list_log_events` 支持 `log_id`，当调查范围是某日志文件时把该 `id` 作为 `log_id` 传入；不要把 `task_id` 与 `log_id` 混淆。
2. **Trace 直查优先**：用户提供 trace ID 或明确想查满足条件的具体 trace 时，跳过聚合定位，直接调用 `POST /log_failure_event_result/list_trace_events`，并用 `POST /log_failure_event_result/list_log_events` 取原始日志。即使聚合查询为零，仍应执行 trace 直查。
3. **通断分支顺序**：先用 `POST /log_failure_event_result/list_time_aggregated_failure_events` 定位故障集中时段，再用 `POST /log_failure_event_result/list_src_dst_aggregated_failure_events` 识别主要源/目的 IP 故障路径。只有问题明确要求按 Pod 汇总时，才补充 `POST /log_failure_event_result/list_pod_aggregated_failure_events`。用 `POST /log_failure_event_result/metrics/err_code` 按错误码和 IP 对量化频次及时间趋势，再用 `POST /log_failure_event_result/list_trace_events` 按时间、IP 对、状态码或 trace ID 获取故障事件和故障模式 ID，最后用 `POST /log_failure_event_result/list_log_events` 获取原始现场证据。
4. **历史案例检索**：获得现场状态码、IP、host、pod、cluster 等信号后，调用 `POST /diag_case_library/search` 查**已人工确认**的历史案例（`kb_id` 可省略 = 跨知识库召回）。命中的案例只能作为待验证假设，不能替代现场证据；必要时 `GET /diag_case_library/{case_id}` 查看完整案例（含证据锚点与验证闭环）。确认库无结果时才降级查 `POST /diagnosis_case/search`，并标注其未经确认。
5. **Curated 知识解读**：对发现的状态码调用 `GET /failure_mode/status_code/{status_code}`；对故障模式 ID 调用 `GET /failure_mode/{failure_mode_id}`。curated 内容是解释依据，不是现场已经命中的独立证明。
6. **原始日志证据**：优先用 `POST /log_failure_event_result/list_log_events` 取得原始现场证据；不直接读取本地文件。API 未暴露所需内容时，如实说明证据缺口。
7. **时延/通断交叉验证**：对通断记录返回的 trace ID，调用 `POST /log_parse_result/list`（body 传 `trace_ids`）检查是否同时存在时延异常。不能因两现象时间接近就认定属于同一请求或存在因果关系。
8. **反证检查与候选排序**：对每个候选根因至少一条现场证据和一条反证检查；证据不足时给出候选根因排序，不下确定性结论。

---

## 附录 A：experience-skill 引用标注（强制）

凡引用 `experience-skill`（SKILL/WIKI）的内容——根因假设、处理建议、
错误码含义辅助判断、阈值参考——**每条**都必须按统一 JSON 模板逐条记录
（含 `conflict_with_curated_knowledge` / `conflict_detail` 字段）；记录将被
`diagnostic-report-generation` 采集写入报告 `chapter_0_experience_refs` 章节。

**完整 JSON 模板、字段说明与铁律见
`experience-skill/references/CITATION_TEMPLATE.md`**。铁律要点：用了必记且
可追溯；经验 ≠ 证据，更 ≠ curated 官方知识——与
`GET /failure_mode/status_code/{status_code}` / `GET /failure_mode/{failure_mode_id}`
冲突时 **curated 优先**并标记 `considered_not_adopted`；检索命中但未采用也要
记录原因；curated 内容本身不需过 experience-skill 标注（在报告
chapter_6_relations 中记录）。

本 Skill 的 `used_in_stage` 枚举：`stage_0_pre_search` / `stage_6_post_search` /
`stage_4_trace_drill` / `stage_5_knowledge` / `recommendation`。
