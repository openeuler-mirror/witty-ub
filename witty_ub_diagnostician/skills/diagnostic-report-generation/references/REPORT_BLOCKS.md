# 诊断报告九板块数据结构参考

本文档收纳 `diagnostic-report-generation` 报告各板块的**完整 JSON 结构、
字段说明、示例，以及各板块的撰写原则与数据来源**（后者集中在文末
「各板块撰写原则与数据来源」）。SKILL.md 只保留报告契约、分诊纪律与生成流程；
填充模板（`templates/report.html`，Jinja2）时按本文档结构逐一对应，
变量命名与模板中的 `{{ variable }}` 严格对应。

> **编号说明**：本文档的"板块 1~9"是**内容板块**（数据结构维度），
> 与报告渲染出的**顶层章节**不是同一套编号。顶层章节共 7 个、连续编号，
> 顺序为 `01 日志基本信息 → 02 事件诊断摘要 → 03 故障清单与关系(仅多故障)
> → 04 综合处置计划(有则显示) → 05 统计分析 → 06 故障档案 → 07 诊断工作追踪`
> （统计分析在故障档案**之前**）；其中板块 2~5、7、9 渲染在**单条故障档案内部**，
> 随该故障对象一起传入。

---

## 故障档案数据结构（faults[]）

```json
{
  "id": "F01",
  "title": "故障名称（一句话，含对象与现象）",
  "role": "primary",
  "status": "confirmed",
  "severity": "P1",
  "confidence": 92,
  "category": "mixed",
  "affected_scope": "host-101 / pod-worker-3；67.6% 故障 trace；12:03-12:11",
  "conclusion": {},
  "latency": {},
  "root_cause": {},
  "propagation": {},
  "evidence_traces": [],
  "knowledge_matches": [],
  "solution": {},
  "source_code": {},
  "simplified": false,
  "upstream": "F01",
  "need_independent_fix": false
}
```

- `role`: `primary` 主故障 / `secondary` 次生故障 / `independent` 独立故障
- `status`: `confirmed` 已确认 / `suspected` 疑似（候选假设，模板有专门提示条）/ `excluded` 已排除
- `severity`: `P1` / `P2` / `P3`
- `category`（故障类型，控制档案头标签）：`error` 错误/通断类（连接失败、错误码突增）/ `latency` 时延类（P99 超阈、慢调用，可无报错）/ `mixed` 时延与错误并存且同源（如丢包既导致慢又导致超时错误）。

### latency 块（时延阶段定位，时延类/mixed 故障必填）

渲染在"故障结论"之后、"根因推理链"之前：

```json
{
  "metrics": [
    {"label": "总时延 P99", "value": "1,180ms", "sub": "超时预算 1,200ms · 已耗 98%", "tone": "danger"},
    {"label": "瓶颈阶段 P99", "value": "1,150ms", "sub": "URMA C2W · 阈值 150ms", "tone": "danger"},
    {"label": "相对基线放大", "value": "63.9×", "sub": "基线 C2W 约 18ms", "tone": "danger"},
    {"label": "慢请求占比", "value": "62.3%", "sub": "时延异常 trace 占比"}
  ],
  "stages": [
    {"name": "URMA 网络（C2W/W2W）", "p99": "1,150ms", "baseline": "18ms", "ratio": "63.9×", "share": "92.0%", "status": "bottleneck",
     "detail": "C2W 段丢包重传，单跳 RTT 从 0.8ms 升至 120ms+；慢 trace 中 62.3% 卡在该阶段"}
  ],
  "conclusion": "时延归因结论，可用 <strong> 强调关键数字；须说明慢在哪个阶段、放大倍数、与错误是否同源"
}
```

- `stages[].status`：`bottleneck` 瓶颈（红）/ `warn` 异常（琥珀）/ `ok` 正常（绿）；`baseline`/`ratio`/`share` 可缺省显示 "—"。
- **结论必须回答**：额外耗时集中在哪个阶段、相对基线放大多少、是否已逼近超时预算、Worker/进程内阶段是否正常（用于排除进程内瓶颈）。

### evidence_traces 块（证据锚点，可选）

渲染在"确认根因"卡片之后。作用是让读者拿着 trace ID 回到现场复现结论
（`GET /trace/{id}` 或 `POST /trace/list`）。**纯文本、无链接、无按钮。**

```json
[
  {
    "trace_id": "a1b2c3d4e5f60718293a4b5c6d7e8f90",
    "kind": "latency",
    "why": "GET·URMA超时 桶内证据耗时 Top1（该桶占异常 trace 62.3%）",
    "evidence_ms": 1180,
    "client_ms": 1200
  },
  {
    "trace_id": "0f9e8d7c6b5a43210fedcba987654321",
    "kind": "error",
    "why": "-1002 首条异常（pod-worker-3 / host-101）",
    "status_code": "-1002",
    "failure_mode_id": "kvcache_runtime_089",
    "pod": "pod-worker-3",
    "host": "host-101",
    "timestamp": "2026-09-22 12:03:11"
  }
]
```

| 字段 | 类型 | 必填 | 取值 / 校验 |
| --- | --- | --- | --- |
| `trace_id` | string | ✅ | 非空；**逐字来自本次工具响应**，不得改写长度或大小写 |
| `kind` | string | ✅ | `latency` 时延锚点 / `error` 通断锚点 |
| `why` | string | ✅ | ≤120 字；必须含**桶 key** 或**过滤条件**（status_code + pod + 时间窗） |
| `evidence_ms` | number | ❌ | `latency` 类填 `top_traces[].evidence_ms` |
| `client_ms` | number | ❌ | `latency` 类填 `top_traces[].client_ms` |
| `status_code` | string | ❌ | `error` 类填 `list_trace_events` 行值 |
| `failure_mode_id` | string | ❌ | 同上 |
| `pod` / `host` | string | ❌ | 同上 |
| `timestamp` | string | ❌ | `YYYY-MM-DD HH:MM:SS` |

- 数组长度 **0~5**；`latency` 类取 `/stats/stages` 该故障**归因桶**的 `top_traces[]` 前 1~3 条。
- **取不到就省略该键或置 `[]`**：键缺省 / `null` / `[]` 三者行为一致，模板整块不渲染
  （不出标题、不出占位符、不占垂直空间）。不得为填满而编造 ID 或降低选择标准。
- 数组内 `trace_id` 不得重复；同一 trace 同时命中时延与通断时只列一条，另一侧信息并入 `why`。

---

## 事件级对象

### incident_summary

```json
{
  "one_line_conclusion": "一句话说明：识别了几个故障、哪个是主故障、它们的关系；不要把所有根因堆在一句话中",
  "fault_count": 3,
  "primary_fault_id": "F01",
  "secondary_fault_count": 1,
  "independent_fault_count": 1,
  "overall_impact": "3421 条故障 trace，波及 2 台 host、3 个 pod",
  "confidence": "高 88%"
}
```

### action_plan[]（综合处置计划）

跨故障措施必须**合并、去重、排序**。一条措施同时解决多个故障时只写一条、
`fault_ids` 关联多个编号：

```json
{
  "priority": "P0",
  "fault_ids": ["F01", "F02"],
  "action": "具体操作",
  "depends_on": "前置依赖（无则填 无）",
  "expected_effect": "预期效果",
  "verify": "验证标准"
}
```

---

## 知识库案例绑定故障（板块 7 字段增强）

`knowledge_matches[]` 归属于具体故障（模板自动在卡片头标注"支撑 F0x"）。
除原有 rank/id/stars/match_logic/symptom/root_cause/solution 外，建议补充：

```json
{
  "phenomenon_fit": "现象契合点（与本次现象的一致程度与差异）",
  "log_fit": "日志或调用栈契合点",
  "rc_consistency": "根因一致性（一致 / 方向不同 / 不一致）",
  "env_diff": "环境及版本差异",
  "adaptation": "需要进行的适配修改",
  "applicability": "direct"
}
```

`applicability` 取值（模板按级别着色，不允许只给笼统匹配分）：
`direct` 可直接采用 / `adjust` 调整后采用 / `reference` 仅供参考 / `not_recommended` 不建议采用。

---

## 板块 1：日志基本信息 (basic_info)

```json
{
  "kb_id": "xxx",
  "kb_name": "production-cluster-01",
  "log_file": "access_20240903.log",
  "operation": "GET",
  "time_range_start": "2024-09-03 12:00:00",
  "time_range_end": "2024-09-03 12:30:00",
  "total_trace_cnt": 128341,
  "fault_trace_cnt": 3421,
  "fault_ratio": "2.67",
  "parse_ok": true,
  "diagnosis_ok": true
}
```

---

## 板块 2：分析结论 (conclusion)

```json
{
  "one_line_conclusion": "pod-worker-3 (host-101) 与 etcd 节点之间网络抖动导致 RPC 连接超时，引发 kvcache GET 请求大面积返回 -1002 错误，影响 67.6% 的故障请求，持续 8 分钟。",
  "fault_domain": "RPC/网络",
  "fault_component": "etcd 连接",
  "fault_function": "TcpConnector::connect()",
  "fault_function_loc": "src/transport/tcp_connector.cpp:161",
  "affected_scope_pct": "67.6",
  "affected_scope_desc": "pod-worker-3 集中",
  "confidence": "高 92%",
  "key_findings": [
    "错误码 -1002 (RPC不可用) 占比 44.5%，为绝对主导错误码",
    "故障集中在 pod-worker-3 (host-101)，占 67.6%，其他 pod 正常",
    "12:03 突发尖峰，12:11 回落，无周期性，符合网络瞬时故障特征",
    "trace 日志确认 etcd 连接超时为主因，排除 worker 进程自身异常"
  ]
}
```

---

## 板块 3：解决方案 (solution)

```json
{
  "short_term": [
    "检查 pod-worker-3 所在 host-101 到 etcd 的网络链路：ping -c 100 etcd-ip",
    "若持续超时，将 pod-worker-3 驱逐到其他节点"
  ],
  "long_term": [
    "为 etcd 连接增加重试+退避机制，避免单次网络抖动导致大面积故障",
    "配置网络监控告警：RTT > 10ms 或丢包率 > 1% 触发通知"
  ],
  "verification": [
    "观察 30 分钟内 -1002 错误码是否归零",
    "确认 P99 时延恢复到基线 50ms 以下",
    "检查 pod-worker-3 在新节点上的 etcd 连接是否正常"
  ]
}
```

---

## 板块 4：根因分析（推理链）(root_cause)

```json
{
  "reasoning_chain": [
    {
      "step_label": "① 现象观察",
      "title": "错误码 -1002 突增",
      "description": "12:03 起，错误码 -1002 (RPC不可用) 突增至 1523 次，占总故障的 44.5%，为绝对主导错误码。",
      "evidence": "[POST /stats/error_codes] Top 故障码 trace 级统计",
      "excluded": false,
      "confirmed": false
    },
    {
      "step_label": "② 范围定位",
      "title": "故障集中在 pod-worker-3",
      "description": "故障 Pod 分布显示 pod-worker-3 (host-101) 占 67.6%，其他 pod 正常，排除集群级故障。",
      "evidence": "[pod_aggregation API] top_pods",
      "excluded": false,
      "confirmed": false
    },
    {
      "step_label": "③ 候选根因",
      "title": "提出三个候选假设",
      "description": "候选1: host-101 网络故障；候选2: worker 进程自身异常；候选3: 上游 etcd 不可达。",
      "evidence": null,
      "excluded": false,
      "confirmed": false
    },
    {
      "step_label": "④ 排除分析",
      "title": "排除 worker 进程异常和通用网络故障",
      "description": "host-101 上其他 pod 正常（排除候选2）；host-101 到其他节点的延迟正常（排除候选1）。",
      "evidence": "[trace log] 原始日志交叉验证",
      "excluded": true,
      "confirmed": false
    },
    {
      "step_label": "⑤ 确认根因",
      "title": "etcd 网络链路丢包",
      "description": "trace 日志显示 etcd 连接超时，host-101 到 etcd 节点的网络路径存在间歇性丢包，导致 RPC 连接超时，进而引发 kvcache GET 请求失败。",
      "evidence": "[failure_mode] kvcache_runtime_089: etcd连接超时→RPC不可用",
      "excluded": false,
      "confirmed": true
    }
  ],
  "confirmed_root_cause": "host-101 到 etcd 节点的网络路径存在间歇性丢包，导致 RPC 连接超时",
  "supporting_knowledge": "kvcache_runtime_089 (etcd连接超时)，kvcache_runtime_042 (连接池耗尽-辅助)"
}
```

---

## 板块 5：故障传播链 (propagation)

与板块 9 源码调用链同一视觉语言：垂直排列的节点卡片（序号圆点 + 标题 +
补充信息 + 右侧角色标签），节点间用带文字的箭头连接器标注**传播机制**，
末端分叉展开多条影响路径。

```json
{
  "chain": [
    {
      "label": "etcd 网络丢包",
      "detail": "host-101 → etcd 链路",
      "type": "origin",
      "transition": "建连超时 · poll() 无限等待"
    },
    {
      "label": "worker 连接超时",
      "detail": "pod-worker-3, RPC timeout 3s",
      "type": null,
      "transition": "错误沿请求路径返回",
      "branches": [
        {
          "label": "GET 读路径",
          "nodes": [
            {"label": "GET 请求失败", "detail": "-1002, 1523次", "type": "impact", "transition": "错误码返回客户端"},
            {"label": "用户读取缓存失败", "detail": "影响 67.6% GET 请求", "type": "impact"}
          ]
        },
        {
          "label": "SET 写路径",
          "nodes": [
            {"label": "SET 请求失败", "detail": "-1002, 89次", "type": "impact", "transition": "错误码返回客户端"},
            {"label": "用户写入缓存失败", "detail": "影响 4.2% SET 请求", "type": "impact"}
          ]
        }
      ]
    }
  ],
  "impact_scope": [
    "集群: prod-cluster-01",
    "Host: host-101 (1台)",
    "Pod: pod-worker-3 (1个)",
    "IP 对: host-101 → 10.0.1.100 (etcd)"
  ]
}
```

---

## 板块 6：统计分析 (statistics)

```json
{
  "stage_breakdown": {
    "operation": "GET",
    "total_p99_ms": "1200ms",
    "share_bar": [
      {"name": "URMA 网络", "pct": "92.0", "cls": "s-bottleneck"},
      {"name": "RPC 网络", "pct": "5.5", "cls": "s-warn"},
      {"name": "其他阶段", "pct": "2.5", "cls": "s-ok"}
    ],
    "stages": [
      {"name": "SDK 处理", "p99": "1.2ms", "anomaly_rate": "0.1%", "fail_share": null, "status": "ok"},
      {"name": "SDK RPC（SDK→Master）", "p99": "45ms", "anomaly_rate": "4.1%", "fail_share": "3.2%", "status": "warn", "fault": "F01",
       "detail": "RPC 网络段随 URMA 超时被动抬升，框架段正常"},
      {"name": "URMA 网络（C2W/W2W）", "p99": "1180ms", "anomaly_rate": "62.3%", "fail_share": "70.6%", "status": "bottleneck", "fault": "F01",
       "detail": "C2W URMA P99 1150ms，超 150ms 阈值 7.7 倍；失败 trace 中 70.6% 卡在该阶段"}
    ],
    "conclusion": "瓶颈阶段：URMA 网络。62.3% 的异常 trace 卡在 URMA（C2W）阶段，占总时延 92%；各 Worker 内部处理阶段均正常，后续定位应聚焦 host-101 → etcd 的 URMA/网络链路。"
  },
  "heatmap_metric": "fault",
  "top_error_codes": [
    {"code": "-1002", "name": "RPC不可用", "pct": "44.5"},
    {"code": "-1009", "name": "连接超时", "pct": "26.0"},
    {"code": "-1005", "name": "资源不足", "pct": "10.2"},
    {"code": "-1001", "name": "参数错误", "pct": "8.1"},
    {"code": "-1008", "name": "内部错误", "pct": "5.5"}
  ],
  "top_failure_domains": [
    {"domain": "RPC/网络", "pct": "70.6"},
    {"domain": "KVCache", "pct": "26.1"},
    {"domain": "其他", "pct": "3.3"}
  ],
  "top_pods": [
    {"pod": "pod-worker-3", "host": "host-101", "pct": "67.6"},
    {"pod": "pod-worker-7", "host": "host-102", "pct": "22.0"},
    {"pod": "pod-worker-2", "host": "host-101", "pct": "5.1"}
  ],
  "top_hosts": [
    {"host": "host-101", "pct": "72.7"},
    {"host": "host-102", "pct": "22.0"}
  ],
  "time_heatmap": [
    {"time": "12:00", "level": "0", "pct": "3", "spike": false},
    {"time": "12:03", "level": "4", "pct": "100", "spike": true},
    {"time": "12:06", "level": "4", "pct": "98", "spike": false},
    {"time": "12:09", "level": "3", "pct": "73", "spike": false},
    {"time": "12:12", "level": "2", "pct": "28", "spike": false},
    {"time": "12:15", "level": "0", "pct": "5", "spike": false}
  ]
}
```

**GET / SET 并列呈现**：两种操作都有数据时，各调一次 `/stats/stages`
（`operation` 分别传 GET/SET），用 **`"stage_breakdowns": [{"operation":"GET",...},
{"operation":"SET",...}]`** 并列渲染（数组元素结构与上面的 `stage_breakdown`
完全相同）；只有一种操作时也可仍传单对象 `"stage_breakdown": {...}`，
模板两者都支持（同时存在时 `stage_breakdowns` 优先）。**禁止把两种操作的
阶段混进同一套 `share_bar` 百分比**。

### GET 操作的标准阶段清单（按请求流经顺序，对应 log_parse_result 字段）

| 报告阶段名 | 底层字段（ms 级 / us 级） | 异常阈值 |
|---|---|---|
| SDK 处理 | `sdk_process` / `sdk_processing_us` | 1.5ms |
| SDK RPC（SDK→Master） | `sdk_rpc` / `sdk_rpc_total_us`（network+framework） | 1.5ms |
| Master 处理 | `master_process` / `master_processing_us` | 1.5ms |
| Master RPC（Master→Worker） | `master_rpc_total` / `master_rpc_total_us` | 150ms |
| Worker 查询元数据 | `worker_query_meta_latency` / `worker_access_latency_us` | 150ms |
| Local Worker 内部 | `local_worker_cost` / `local_worker_internal_us`（含 `local_worker_lock`） | 1.5ms |
| Remote Worker 内部 | `remote_worker_cost` / `remote_worker_internal_us` + `remote_worker_processing_us` | 1.5ms |
| URMA 网络（C2W/W2W） | `urma_total_latency`（含 `c2w_urma_latency`/`w2w_urma_latency`/`urma_link_latency`）/ `urma_processing_us` | 150ms |

### SET 操作的标准阶段清单（写路径独立视角，实测口径）

SET 走 CREATE/PUBLISH 写路径，**可用字段与 GET 不同**，阶段表按实测重建
（node48 3638 条写路径行）：

| 报告阶段名 | 底层字段（ms 级 / us 级） | 异常阈值 | 说明 |
|---|---|---|---|
| 客户端 SDK 段 | `sdk_process` / `sdk_processing_us` | 1.5ms | 含等待数据面返回，SET 侧主流（2467/3638） |
| Worker 写处理 | `local_worker_cost` / `local_worker_internal_us` | 1.5ms | Worker 端 CREATE/PUBLISH 处理（含 `local_worker_lock`） |
| 数据面未观测 | `total_latency_us` | 150ms | 该 trace 无 Worker 侧行（`local_worker_internal_us` 与 `worker_access_latency_us` 均空，1164/3638），只能取总时延 |
| URMA 链路（附注） | `urma_link_latency` | 150ms | 仅附注不参与归因 |

- **不要**为 SET 编造 `create_latency` / `publish_latency` / `urma_processing_us`
  分段：这几个列在当前解析路径恒为空/恒≈总时延（见 `/stats/stages` 的
  `operation="SET"` 响应 note）。`urma_processing_us` 仅 GET 有效。
- SET 阶段表同样来自 `log_parse_result` / `latency_bucket_*` 聚合（avg/p99），
  但注意 `sdk_processing_us + local_worker_internal_us ≡ total_latency_us`，
  两段之外的差异属个别不自洽行（残差桶），报告需显式说明而非套用 GET 阈值。

**统计板块呈现**：GET / SET 各出一套**并列呈现**（各调一次 `/stats/stages`，
`operation` 分别传 GET/SET，用 `"stage_breakdowns"` 数组承载），禁止把两种
操作的阶段混在同一套百分比里。

**阶段表通用规则（GET/SET 共用）**：

- 阶段时延来自 `log_parse_result` / `latency_bucket_*` 聚合（avg/p99）；
  阶段失败占比来自 failure_mode 的故障域归属（URMA/RPC网络/KVCache 等
  域映射到对应阶段）
- 纯通断案例也应填阶段表（时延列填故障窗口内实测值，失败占比列为主）；
  无时延数据的阶段 `p99` 填 "—"
- `detail` 可选，用于补充关键对比（如"C2W 异常而 W2W 正常"这种区分性证据）

---

## 板块 7：知识库匹配 (knowledge_matches)

```json
[
  {
    "rank": "①",
    "id": "kvcache_runtime_089",
    "stars": "★★★★★",
    "match_logic": "L1: 错误码 -1002 命中; L2: 故障域 RPC/网络 匹配; L3: pod 级故障集中度匹配",
    "symptom": "etcd 连接超时导致 RPC 不可用",
    "root_cause": "网络链路丢包或抖动",
    "solution": "检查网络链路，必要时切换备用链路",
    "adoption_class": "adoption-adopted",
    "adoption_label": "已采用"
  },
  {
    "rank": "②",
    "id": "kvcache_runtime_042",
    "stars": "★★★★☆",
    "match_logic": "L1: 错误码 -1002 命中; L2: 故障域部分匹配",
    "symptom": "worker 连接池耗尽",
    "root_cause": "上游服务响应慢导致连接堆积",
    "solution": "增加连接池大小，设置合理的超时配置",
    "adoption_class": "adoption-reference",
    "adoption_label": "作为参考"
  }
]
```

---

## 板块 8：诊断工作追踪 (workflow)

```json
{
  "session_id": "sess-abc123",
  "total_steps": 6,
  "api_calls": 4,
  "duration": "45s",
  "steps": [
    {
      "title": "Step 1 经验库预检索",
      "api_calls": ["experience-skill search --query 'etcd timeout kvcache -1002'"],
      "result": "命中 2 条 WIKI, 1 条 SKILL"
    },
    {
      "title": "Step 2 数据准备",
      "api_calls": ["GET /log_kb/kb-prod-01", "POST /log_file/list/kb-prod-01"],
      "result": "确认数据可用，1 个日志文件"
    },
    {
      "title": "Step 3 组件定位与故障粗筛",
      "api_calls": ["POST /stats/stages", "POST /stats/error_codes (top_n=5)", "POST /stats/pods (top_n=5)", "POST /stats/heatmap"],
      "result": "-1002 占 44.5%, pod-worker-3 占 67.6%"
    },
    {
      "title": "Step 4 定向验证",
      "api_calls": ["POST /failure_mode/by_ids", "POST /log_failure_event_result/list_log_events (page_cnt=5)"],
      "result": "确认 etcd 连接超时，排除其他候选"
    },
    {
      "title": "Step 5 知识库复核",
      "api_calls": ["experience-skill search --query 'etcd network troubleshooting'"],
      "result": "补充网络诊断建议"
    },
    {
      "title": "Step 6 生成报告",
      "api_calls": [],
      "result": "输出 HTML 诊断报告"
    }
  ]
}
```

---

## 板块 9：源码分析 (source_code)

源码分析按**调用链**组织：从业务入口逐层下钻到故障点函数，每个链节点给出
精简代码 + 一句分析，节点间用 `calls` 连接器标注调用关系和调用点行号。

```json
{
  "component": "ubsocket",
  "failure_mode_id": "ubsocket_042",
  "call_chain": [
    {
      "function": "KVClient::get()",
      "file": "src/client/kv_client.cpp",
      "line": 88,
      "role": "entry",
      "role_label": "入口",
      "call_site": "kv_client.cpp:92",
      "code": [
        {"num": 86, "text": "Status KVClient::get(const Key& k, Value* v) {", "highlight": false, "ellipsis": false},
        {"num": 92, "text": "  rpc_channel_->CallMethod(&conn, req, resp);", "highlight": false, "ellipsis": false},
        {"num": 93, "text": "  // 未对 CallMethod 设置总超时上限", "highlight": false, "ellipsis": false}
      ],
      "analysis": "业务入口发起 GET，同步等待 RPC 返回；此处未对整个调用设置截止时间（deadline），下游一旦阻塞会无限向上传导。"
    },
    {
      "function": "TcpConnector::connect()",
      "file": "src/transport/tcp_connector.cpp",
      "line": 156,
      "role": "fault-point",
      "role_label": "故障点",
      "code": [
        {"num": 158, "text": "  setsockopt(fd, SO_RCVTIMEO, &tv3s, ...);", "highlight": false, "ellipsis": false},
        {"num": 161, "text": "    poll(fd, POLLOUT, -1);  // BUG: 无限等待", "highlight": true, "ellipsis": false},
        {"num": 0, "text": "// ... 其余错误处理省略 ...", "highlight": false, "ellipsis": true}
    ],
    "analysis": "根因落点：setsockopt 的 3s 超时只约束 connect() 本身；返回 EINPROGRESS 后 poll() 第三参数为 -1（无限等待），对端丢包无响应时永久阻塞。"
  }
],
"fix_suggestion": "将 poll(fd, POLLOUT, -1) 改为 poll(fd, POLLOUT, remaining_timeout_ms)；RpcChannel 层增加 deadline 透传与一次重试。"
}
```

---

# 各板块撰写原则与数据来源

> 本节原为 SKILL.md 内嵌内容，为降低 SKILL.md 的静态上下文成本而下沉到此处。
> 填充 JSON 前按板块查阅；变量命名与模板 `{{ variable }}` 严格对应，结构见上文各板块。

## 板块 1：日志基本信息

**数据来源**
- `kb_id` / `kb_name`: `GET /log_kb/{kb_id}`
- `log_file`: `POST /log_file/list/{kb_id}`
- `operation`: 用户输入或 API 参数
- `time_range`: 诊断阶段 2 的时间聚合结果
- `total_trace_cnt` / `fault_trace_cnt`: `POST /trace/list` 的 `total`
  （`fault_trace_cnt` 用 `is_anomalous=true` 过滤，或 `/stats/stages` 各桶 `fail_cnt` 求和）
- `parse_ok` / `diagnosis_ok`: `GET /task/{task_id}` 状态

## 板块 2：分析结论

**撰写原则**
- `one_line_conclusion`: 一句话包含"时间+地点+组件+现象+原因+影响"，≤150 字
- `fault_function`: 仅当能从 failure_mode 或 BRPC node 获取时填写，否则省略；
  渲染为卡片下方全宽函数定位条，长函数名自动换行不溢出
- `fault_function_loc`: 可选，格式 `源文件:行号`（如 `src/transport/tcp_connector.cpp:161`），与函数名同行
- `confidence`: 文字+数字（如"高 92%"），与根因分析置信度一致
- `key_findings`: 3~5 条，每条是客观事实，非主观推测

## 板块 3：解决方案

**撰写原则**
- `short_term`: 2~3 条可立即执行的操作，祈使句
- `long_term`: 1~2 条预防性措施
- `verification`: 3 条可量化的验证步骤
- 优先使用 failure_mode 知识库的 `solution`，其次使用 experience-skill 建议

## 板块 4：根因分析（推理链）

**撰写原则**
- 3~5 步，从"现象"到"根因"逐步递进
- 每步必须有 `evidence`（数据来源，格式如 `[POST /stats/error_codes] Top 故障码 trace 级统计`）或明确标注为推理
- `excluded: true` 标记被排除的候选假设（模板渲染为灰色+删除线）
- `confirmed: true` 仅用于最后一步（模板渲染为红色实心圆点）
- `confirmed_root_cause`: 30 字以内，精确描述根因

## 板块 5：故障传播链

**撰写原则**
- 渲染为**垂直节点卡片链**：主链节点带数字序号圆点（① 红=源头 / ② 蓝=传播环节），
  分叉节点带字母序号（a/b/c/d，橙=业务影响）；连接器胶囊文字是 `transition`（传播机制）
- `type`: `origin`（红，全链唯一且必须第一个）/ `impact`（橙，业务影响）/ `null`（灰，传播环节）
- `transition` ≤20 字；没把握时省略，只显示箭头
- `branches`: 带 `branches` 的节点必须是 `chain` 末节点，每条分支 1~3 节点、分支数 ≤3
- 无分叉的线性链只填 `chain`（2~5 节点）
- `label` ≤16 字；`detail` ≤28 字，放量化信息（错误码+次数、影响比例、时延数值）
- `impact_scope`: 精确列出受影响的集群/Host/Pod/IP

## 板块 6：统计分析

**阶段分解（stage_breakdown）—— 宏观→阶段→微观漏斗的核心**

实战思路是"先看宏观，再按请求流程阶段分解，优先分析高失败/高时延的阶段"：
- `stages` 按请求流经顺序排列，每阶段给 P99 时延、时延异常率（超该阶段阈值的 trace 占比）、
  失败占比（通断场景下归属该阶段的故障 trace 占比，时延场景填 null 渲染为 "—"）
- `status` 三态：`ok`（绿）/ `warn`（黄，异常率或失败占比 >10%）/ `bottleneck`（红，全表唯一）
- `share_bar`：各阶段时延占总时延的构成条，聚合 2~4 段（`s-bottleneck` 红 / `s-warn` 黄 / `s-ok` 蓝），
  `pct` 之和应为 100
- `fault`（可选）：该阶段异常归属的故障编号，渲染为可点击 F 标签；正常阶段不填。
  多故障时 warn/bottleneck 阶段必须归属到具体故障
- `conclusion`：一句话点明瓶颈阶段 + 后续定位方向（聚焦哪个链路/组件，排除哪些阶段）
- **GET 与 SET 是两套独立口径**（读路径 8 阶段 / 写路径实测阶段，见上文清单）：
  两种操作都有数据时用 **`stage_breakdowns` 列表**各出一套并列呈现，禁止把两种操作
  的阶段混进同一套 `share_bar` 百分比；只有一种操作时用单对象 `stage_breakdown` 亦可
- **SET 写路径不要编造 `create_latency`/`publish_latency`/`urma_processing_us` 分段**（解析路径不产出）
- 纯通断案例也应填阶段表（时延列填故障窗口内实测值，失败占比列为主）；
  `detail` 可选，用于补充关键对比（如"C2W 异常而 W2W 正常"这种区分性证据）

**时间热点图（time_heatmap）两种模式**
- 故障量模式（默认，`"heatmap_metric": "fault"` 或不填）：柱高与数值为该时段故障 trace 占比
- 时延模式（`"heatmap_metric": "latency"`）：每个 slot 额外填 `"lat_ms"`（该时段 P99 毫秒数），
  柱高仍按 `pct` 归一化，数值区显示 P99 ms，标题自动标注"各时段 P99 时延"
- `slot.fault`：该尖峰归属的故障编号（`top_*` 条目同理可带 `"fault"` 显示 F 标签）

**数据来源和注意事项**
- `top_error_codes` / `top_pods` / `top_hosts`: `POST /stats/error_codes`（`items[]` 的
  `status_code`+`trace_cnt`，`name` 经 `GET /failure_mode/status_code/{code}` 补全，
  `pct` = `trace_cnt` / 各码合计）、`POST /stats/pods`（`items[]` 的 `pod_ip`/`host`+`fault_trace_cnt`，
  `pct` = `fault_trace_cnt` / 故障 trace 合计；`top_hosts` 由 `items[]` 按 `host` 归并求和后取 Top）；
  全量 DB 侧精确聚合，不受 `/trace/list` 页内截断；`top_failure_domains` 由 `top_error_codes`
  经 `GET /failure_mode/status_code/{code}` 映射 `failure_domain` 归并；四项均为纯 CSS 环形饼图，2×2 网格
- `pct` 是百分比数值（不带 `%` 符号），各项按占比降序；**只填 Top N**（错误码/Pod/Host 取 Top 5，
  故障域全量），余量模板自动补灰色「其他」扇区（四舍五入到 100%，无需手工补齐）
- `dist_total`: 可选，饼图中心总量数字（如 `"3,421"`），不填则中心留白；四个饼图共用
- 饼图扇区颜色由模板色板自动分配，8 色循环且按下标取模（扇区数超色板长度也不越界），
  数据中不需要填颜色；「其他」扇区固定灰 `#C3CBD4`
- `time_heatmap`: `POST /stats/heatmap`（自动选窗 1m/10m/1h，返回 `items[]` 的 `window_start`
  +`fault_trace_cnt`；显式传 `window_size` 控制槽宽，如故障窗短用 `"1m"`；6~12 个时间槽为宜），
  `pct` = `fault_trace_cnt` / 峰值槽，`time` 取 `window_start` 的 `HH:MM`；渲染为垂直迷你柱图，
  `level` 0 → 灰=无故障、1 → `--brand-pale`、2 → `--brand-soft`、3 → `--brand`；
  **红色仅由 `spike: true` 触发**（不随 level 变化），尖峰柱顶部显示红色徽章且时间标签变红；
  时间维度是趋势不是构成，故用柱图不用饼图
- 所有百分比值**不带 `%` 符号**，模板会自动添加
- 前端看板用 ECharts，本报告饼图是 conic-gradient 纯 CSS 实现，与之完全隔离

## 板块 7：知识库匹配

**撰写原则**
- 1~3 条匹配结果，按匹配度降序；`stars` 表示匹配度（5 星=完美，3 星=中等）
- `match_logic`: 说明 L1(错误码)/L2(故障域)/L3(拓扑) 三级匹配逻辑
- `adoption_class`: `adoption-adopted` / `adoption-reference` / `adoption-not-adopted`
- 必须同时包含 failure_mode_knowledge 的 curated 知识与 experience-skill 的经验知识

## 板块 8：诊断工作追踪

**撰写原则**
- `session_id` 从 opencode session 环境变量或用户输入获取；`duration` 为诊断到出报告的总耗时
- `api_calls` 为实际调用次数（含重复调用）；`result` 摘要 ≤30 字，简洁有信息量
- 典型 Step 3「组件定位与故障粗筛」的 API 组合：`POST /stats/stages`、
  `POST /stats/error_codes (top_n=5)`、`POST /stats/pods (top_n=5)`、`POST /stats/heatmap`

## 板块 9：源码分析

**数据来源和注意事项**
- `component`: 来自 `brpc_diag_node` 表或 failure_mode 知识库；源码通过
  `GET /diagnosis/component_src/{component}/{filename}` 获取（后端暂未落地，不可用时 `source_code` 设 `null`）
- `call_chain`: 2~4 个节点，按调用方向排列（入口 → 中间调用 → 故障点）
  - `role`: `entry`（灰）/ `intermediate`（蓝）/ `fault-point`（红，全链唯一且在最后）
  - `call_site`: 本节点调用下一函数的代码位置（文件:行号），显示在节点间连接器上；末节点不填
  - `code`: **每节点只保留 3~6 行关键代码**，无关代码用省略行
    `{"num": 0, "text": "// ... 其余省略 ...", "ellipsis": true}`（灰色斜体居中、不显示行号）
  - `highlight: true` 标记问题行，仅故障点节点使用，1~2 行
  - `analysis`: 每节点一句话，说清该函数在故障链中的作用/缺陷，≤80 字
- `fix_suggestion`: 具体代码修改建议，≤100 字，放在调用链底部绿色条
- 向后兼容：无法组织调用链时可退回单函数结构
  （`filename`/`function_name`/`line_range`/`code_snippet`/`analysis` 数组），模板自动适配
- 无法获取源码（组件仓库未拉取或故障模式未关联源码）时 `source_code` 设 `null`

## 报告数据来源速查

| 数据 | 来源 |
|------|------|
| 基本信息和任务状态 | `GET /log_kb/{kb_id}`, `POST /log_file/list/{kb_id}`, `GET /task/{task_id}` |
| 组件定位 | `POST /stats/stages`（必传 `kb_id`，可选 `log_id`；`operation` GET→8 桶 / SET→5 桶，各调一次、禁止混合归桶；返回 `fail_cnt` 通断面、`success_cnt`+`trace_cnt` 时延面、`p50/p90/max_ms` 证据耗时与 `client_*` 对照、`top_traces[]` 桥接） |
| 统计分布 | `POST /stats/error_codes` / `POST /stats/pods` / `POST /stats/heatmap` / `POST /stats/links`（源目对，多数数据源目为空时 total=0 属数据事实） |
| 主问题归因 | `POST /stats/stages` 的 `items[]`：每条问题 trace 按最大瓶颈阶段归入唯一桶；GET 桶序：RPC网络/RPC排队/QueryMeta/URMA/Data Worker服务端处理/Client/Worker交叉窗口未细分/未解释残差/URMA超时；SET 桶序：SET·URMA超时/SET·数据面未观测/SET·未解释残差/SET·客户端SDK段/SET·Worker写处理 |
| 故障模式和知识库 | `POST /failure_mode/by_ids`, `GET /failure_mode/status_code/{status_code}` |
| 经验库 | experience-skill 检索结果（复用诊断 Skill 的附录 A） |
| 代表 trace 证据 | `POST /log_failure_event_result/list_trace_events` (page_cnt=5), `POST /log_failure_event_result/list_log_events` (page_cnt=5)；取到的代表 trace 必须落到 `faults[].evidence_traces[]`（见上文"evidence_traces 块"），只写在 `reasoning_chain[].evidence` 自由文本里等于没落地 |
| BRPC 源码 | `GET /diagnosis/component_src/{component}/{filename}`（规划接口，暂未落地；不可用时 `source_code` 设 `null`） |
| 历史案例 | `POST /diag_case_library/search`（默认，只返回已人工确认案例；`kb_id` 可空 = 跨库召回）；无结果时才降级 `POST /diagnosis_case/search` 并标注未经确认 |
