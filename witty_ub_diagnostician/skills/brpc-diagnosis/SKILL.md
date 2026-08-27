---
name: brpc-diagnosis
description: >
  通过 HTTP API 进行 BRPC 组件故障诊断。
  引导用户按六阶段流程调用 HTTP API:批次定位 → 调查入口选择 → 
  深度下钻 → 证据分层解释 → 反证检查 → 根因综合。当用户提出
  "BRPC 故障"、"组件异常"、"ubsocket/umq/urma 问题"、"线程异常"、
  "Pod BRPC 报错"等问题时,优先使用本 Skill。
license: HUAWEI
compatibility: >
  Requires HTTP API access to FastAPI backend on port 9772 via bash curl.
  BRPC diagnosis uses batch_id as the primary key, not kb_id. All BRPC
  queries are GET with UTC+8 time strings as query parameters.
metadata:
  author: witty-ub-diagnostician
  version: "1.2"
  keywords: [BRPC, 组件故障, ubsocket, umq, urma, 线程异常, Pod故障, batch_id]
allowed-tools: >
  Bash(curl:*) Bash(cd:*)
  experience-skill
---

# BRPC 组件故障诊断 (BRPC Component Diagnosis)

引导 Agent 按**六阶段流程**顺序调用 HTTP API 的 BRPC 诊断接口,
从批次定位到根因综合,避免在海量数据中盲目查询。

**强制要求**:凡引用了 `experience-skill` 知识库(SKILL 或 WIKI)的内容,
**必须**按本文末尾的引用标注规则逐条记录;不得把经验库的内容冒充现场证据。

---

## 阶段 0:经验库预检索(诊断前)

**在调用任何 BRPC 诊断 API 之前**,先用 `experience-skill` 基于用户提供的
初始关键词检索本地经验:

```bash
cd /var/witty-ub/witty_ub_diagnostician/.opencode/skills/experience-skill/scripts

# BRPC 相关关键词
uv run experience-skill search-experiences \
    --query "BRPC 故障诊断 ubsocket" --type SKILL --top-k 5
uv run experience-skill search-experiences \
    --query "BRPC 组件故障 通断异常" --type WIKI --top-k 5
```

**对每条命中结果**,按文末"经验引用标注模板"记录,填入 `used_in_stage = "stage_0_pre_search"`。

---

## 阶段一:定位并核验 BRPC 批次

| 步骤 | 查询接口 | 关键参数 | 目的 |
|------|---------|---------|------|
| 1.1 | `GET /brpc-diagnosis/task/{task_id}/batch` | task_id | 用户给 task_id 时,获取 batch_id |
| 1.2 | `GET /brpc-diagnosis/batch/{batch_id}` | batch_id | 核验批次元数据:schema、覆盖时间、hit_count |

**关键检查**:
- 记录批次的 `start_time`、`end_time` 和 `hit_count`
- 后续未指定时间时,以批次覆盖时间作为调查边界
- `hit_count=0` 时说明批次没有导入命中,不继续虚构异常

---

## 阶段二:选择调查入口

根据问题类型选择合适的入口:

| 问题类型 | 入口接口 | 后续串联 |
|---------|-------------|---------|
| 全局趋势未知 | `GET /brpc-diagnosis/batch/{batch_id}/interface-timeline` | 先看各组件接口命中趋势,再缩小时间段 |
| Pod 故障 | `GET /brpc-diagnosis/batch/{batch_id}/pod-events` | 定位时间窗口和 Pod → `.../pod-events/{event_id}` |
| 瞬时线程故障 | `GET /brpc-diagnosis/batch/{batch_id}/thread-events` | 定位窗口和线程 → `.../thread-events/{event_id}` |
| 持续异常线程 | `GET /brpc-diagnosis/batch/{batch_id}/abnormal-threads` | 按命中数排行 → `.../abnormal-threads/{thread_key}` |
| 已知 (pod_ip, thread_id) | `GET /brpc-diagnosis/batch/{batch_id}/hits` | 直接获取命中日志 |

### 2.1 全局趋势:interface-timeline

```
batch_id:     <ID>
window_size:  "1m"          (默认;瞬时尖峰用 "10s";长时用 "10m" 或 "1h")
start_time:   <批次 start 或用户指定>
end_time:     <批次 end 或用户指定>
component:    <可空,ubsocket/umq/urma>
```

**诊断要点**:
- 识别命中突增的时间窗口
- 对比不同组件的命中模式
- 与用户报告的故障时间对齐

### 2.2 Pod 维度聚合:pod-events

```
batch_id:     <ID>
window_size:  "1m"          (仅 1s / 1m / 1h)
start_time:   <故障窗口>
end_time:     <故障窗口>
pod_ip:       <可空>
pod_name:     <可空>
```

**返回重点字段**:
- `event_id` — 详情查询必需
- `pod_ip`, `window_start_time`, `window_end_time` — 故障域定位
- `interface_hits[].interface_hit_count` — 各接口命中次数与严重程度

### 2.3 线程维度聚合:thread-events

```
batch_id:     <ID>
window_size:  "1m"          (仅 1s / 1m / 1h)
start_time:   <故障窗口>
end_time:     <故障窗口>
pod_ip:       <可空>
```

**返回重点字段**:
- `event_id`, `thread_id` — 详情查询必需
- `pod_ip`, `thread_id` — 线程标识
- `interface_hits[].interface_hit_count` — 各接口命中次数

### 2.4 异常线程排行:abnormal-threads

```
batch_id:     <ID>
start_time:   <故障窗口>
end_time:     <故障窗口>
pod_ip:       <可空>
search:       <可空,模糊匹配 thread_id / pod_ip / pod_name>
```

**诊断要点**:
- 按 `total_interface_hit_count` 降序排列
- 关注 `first_hit_time` 到 `last_hit_time` 的持续时间
- `thread_key` 是详情查询必需;选择 Top 3-5 候选进入阶段三

---

## 阶段三:深度下钻

### 3.1 Pod 事件详情:`GET /brpc-diagnosis/batch/{batch_id}/pod-events/{event_id}`

```
batch_id:           <ID>
event_id:           <阶段二返回>
window_start_time:  <原样传回>
window_end_time:    <原样传回>
pod_ip:             <原样传回>
```

**返回内容**:
- `interface_hits` — 接口级命中统计
- `failure_modes` — 命中的故障模式及次数
- `failure_graph` — 故障关系图(`directly_hit=true` 才是直接命中)
- `hits` — 原始命中日志

### 3.2 线程事件详情:`GET /brpc-diagnosis/batch/{batch_id}/thread-events/{event_id}`

```
batch_id:           <ID>
event_id:           <阶段二返回>
window_start_time:  <原样传回>
window_end_time:    <原样传回>
pod_ip:             <原样传回>
thread_id:          <原样传回>
```

### 3.3 异常线程详情:`GET /brpc-diagnosis/batch/{batch_id}/abnormal-threads/{thread_key}`

```
batch_id:     <ID>
thread_key:   <阶段二返回>
pod_ip:       <原样传回>
thread_id:    <原样传回>
window_size:  "1m"          (10s / 1m / 10m / 1h)
start_time:   <调查时间范围>
end_time:     <调查时间范围>
```

**返回内容**:
- 线程级接口时间趋势
- 故障模式命中详情
- 故障关系图
- 分页命中日志

### 3.4 命中日志查询:`GET /brpc-diagnosis/batch/{batch_id}/hits`

```
batch_id:     <ID>
pod_ip:       <必填>
thread_id:    <必填,整数>
start_time:   <时间范围>
end_time:     <时间范围>
pod_name:     <已知时传递>
```

---

## 阶段四:证据分层解释

BRPC 详情响应中的证据分层:

| 字段 | 含义 | 使用注意 |
|------|------|---------|
| `interface_hits` / `interface_timeline` | 故障模式映射到接口后的命中统计 | 用于定位异常接口 |
| `failure_modes` | 当前范围内实际命中的故障模式及次数 | 用于根因分析 |
| `failure_graph.nodes[].directly_hit` | `=true` 表示节点被现场日志直接命中 | 其余节点和边是上下文,不是直接证据 |
| `hits[].message` | 原始现场证据(日志消息) | 时间、Pod、组件、源码位置、线程、trace |

**强制规则**:
- 不得把图中的上下文节点描述成已经直接命中的根因
- 只有 `directly_hit=true` 的节点才能作为直接证据

---

## 阶段五:反证检查与根因综合

### 5.1 反证检查(强制)

对每个候选根因:
- 检查同一时间段其他 Pod/线程是否也命中
- 对比接口趋势与命中日志的时间一致性
- 核对故障模式说明与现场证据

### 5.2 根因综合输出

按置信度从高到低排序候选根因,每条必须具备:
1. **现场证据**(≥1 条来自 hits / pod-events / thread-events 的事实数据)
2. **故障模式匹配**(failure_modes 中的命中记录)
3. **反证检查**(尝试证伪未果的验证步骤)
4. **知识来源**(failure_mode_id、或"现场证据推断")

---

## 阶段六:经验库二次检索(诊断后)

**在形成候选根因之后**,用阶段二~五发现的更精确关键词再次检索:

```bash
cd /var/witty-ub/witty_ub_diagnostician/.opencode/skills/experience-skill/scripts

# 示例:用发现的故障模式作精确检索
uv run experience-skill search-experiences \
    --query "ubsocket 连接超时 failure_mode" --type SKILL --top-k 5
uv run experience-skill search-experiences \
    --query "BRPC 组件故障 根因分析" --type WIKI --top-k 5
```

**关键规则**:
1. 若二次检索命中的经验被采用,必须标注 `used_in_stage = "stage_6_post_search"`
2. 若命中但未采用,也要记录 `considered_not_adopted` + 原因
3. 不得将经验库的结论直接当作现场证据

---

## 跨系统关联(仅在用户明确要求时)

只有用户明确要求关联 KVCache 与 BRPC 时才执行跨系统对照:
- 分别陈述两套 API 的数据范围和事实
- 只能用共同的时间、Pod、IP 或 trace 等现场字段建立候选关联
- 不得仅凭时间接近断言 BRPC 是 KVCache 时延或通断故障的原因

---

## BRPC API 输入规则

- 所有 BRPC 查询接口都是 `GET`;时间参数必须使用 UTC+8 字符串
  `YYYY-MM-DD HH:MM:SS`,作为 query 参数传入(用 `curl --get --data-urlencode`)。
- `component` 只能是 `ubsocket`、`umq`、`urma`;**仅** `interface-timeline` 接受
  `component` 过滤。`pod-events`、`thread-events`、`abnormal-threads`、`hits`
  以及三个详情接口都**没有** `component` 参数,不得臆造。
- `window_size` 取值按接口区分:
  - `interface-timeline`、`abnormal-threads/{thread_key}`:`10s`、`1m`、`10m`、`1h`;
  - `pod-events`、`thread-events`:`1s`、`1m`、`1h`。
- `event_id` 与 `thread_key` 是 64 位小写十六进制字符串;详情查询必须把列表返回的
  `event_id` / `thread_key`、`window_start_time`、`window_end_time`、`pod_ip`、
  `thread_id` 原样回传,不得改动或省略。
- `hits` 的 `pod_ip`(字符串)与 `thread_id`(整数)都是必填。
- `sort_order` 只能是 `asc` 或 `desc`;使用 `sort_field`/`sort_direction` 时必须一一对应。
- `page_num` ≥ 1;`page_cnt` 在 1 到 1000 之间(诊断期建议 ≤ 100)。

## BRPC 标准流程补充

1. **批次定位**:用户给 `task_id` 时先 `GET /brpc-diagnosis/task/{task_id}/batch`
   拿到 `batch_id`;用户直接给 `batch_id` 时先 `GET /brpc-diagnosis/batch/{batch_id}`
   核验元数据。`hit_count=0` 时如实报告"批次无命中",停止虚构异常。
2. **入口选择**:全局趋势未知 → `interface-timeline`;已知是某个 Pod 的问题 →
   `pod-events` → `pod-events/{event_id}`;是瞬时线程问题 → `thread-events` →
   `thread-events/{event_id}`;需要找持续异常线程 → `abnormal-threads` →
   `abnormal-threads/{thread_key}`;已知 `(pod_ip, thread_id)` → `hits` 直查。
3. **标识回传**:从列表进入详情时,把列表返回的 `event_id` / `thread_key` 以及
   `window_start_time` / `window_end_time` / `pod_ip` / `thread_id` 原样回传,
   它们是完整分组键的一部分,缺失或改动能导致详情查询失败。
4. **证据分层**:只有 `failure_graph.nodes[].directly_hit=true` 的节点是现场直接
   命中;其余节点与边是上下文。`failure_modes` 是故障模式命中统计,
   `hits[].message` 是第一手原始证据。
5. **反证与候选排序**:每个候选根因都要有现场证据 + 反证检查;证据不足时给出
   候选排序,不下确定性结论。

---

## 典型入口场景速查

| 用户问题 | 第一步 | 后续串联 |
|---------|--------|---------|
| "BRPC 诊断 task_id=xxx" | `GET /brpc-diagnosis/task/{task_id}/batch` | 获取 batch_id → 阶段二选择入口 |
| "batch_id=xxx 有什么异常" | `GET /brpc-diagnosis/batch/{batch_id}` | 核验批次 → interface-timeline 全局扫描 |
| "pod-xxx BRPC 报错" | `GET /brpc-diagnosis/batch/{batch_id}/pod-events?pod_ip=...` | 定位窗口 → `.../pod-events/{event_id}` |
| "thread-xxx 异常" | `GET /brpc-diagnosis/batch/{batch_id}/thread-events` | 定位窗口 → `.../thread-events/{event_id}` |
| "哪些线程持续异常" | `GET /brpc-diagnosis/batch/{batch_id}/abnormal-threads` | 排行 → `.../abnormal-threads/{thread_key}` |

---

## 附录 A:experience-skill 引用标注模板(强制)

**任何时候**引用了 `experience-skill` 知识库的内容,都必须按以下 JSON 模板记录。

### JSON 模板

```json
{
  "experience_refs": [
    {
      "experience_id": "<Experience.id UUID>",
      "experience_type": "SKILL | WIKI",
      "name": "<Experience.name>",
      "source_path": "<Experience.source>",
      "keywords_matched": ["<匹配的关键词>"],
      "search_query_used": "<完整的 search-experiences --query 字符串>",
      "used_in_stage": "stage_0_pre_search | stage_6_post_search",
      "adoption_status": "adopted_as_evidence | adopted_as_suggestion | considered_not_adopted",
      "conflict_with_curated_knowledge": true | false,
      "conflict_detail": "<仅 conflict=true 时填>",
      "content_quoted": "<引用原文片段,≤200字>",
      "how_used_in_diagnosis": "<一句话说明引用如何作用于诊断结论>",
      "confidence_on_reference": 0.0 ~ 1.0,
      "confidence_reason": "<为何信任/不信任该引用>"
    }
  ]
}
```

### 三条铁律

1. **用了必记,记必可追溯**
2. **经验 ≠ 证据**:adopted_as_evidence 需极度谨慎
3. **不采用也要说明原因**