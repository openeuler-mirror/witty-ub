# 超节点日志案例特征清单（六层）

本文件是**查表型**参考：定义"一个日志案例该记录哪些特征、每个特征从哪个 API/表取、在匹配里起什么作用"。
判决标准与纪律在 `SKILL.md`，本文件不重复。

适用范围：KVCache（时延/通断）与 BRPC 两类诊断对象。两者的标识体系不混用。

---

## 特征总览（v2：分布特征软匹配）

| 层 | 特征 | 回答的问题 | 匹配作用 | 软匹配权重 |
|---|---|---|---|---|
| L0 身份与范围 | 样本标识与拓扑边界 | 这是哪一份样本 | **不参与打分**（不同现场 IP/Pod 必然不同，按名字匹配不可迁移）；`kb_id` 只作召回过滤 | 0 |
| L1 时间演化 | 故障的时间形状 | 怎么发生的 | 多故障分诊的时间窗信号 + 软匹配弱加分 | 1.0（时间形态相等） |
| L2 操作与阶段 | 瓶颈在哪一段 | 卡在哪里 | **L2 故障域；时延故障核心特征（超时时延段）**；`operation` 操作域一致性 | 2.0 × share（归因桶占比加权）+ 1.0（操作域） |
| L3 故障语义 | 系统报了什么 | 报的什么错 | L1 错误码（按分布占比加权）+ 故障模式（最强语义） | 3.0 × share（错误码）/ 4.0（故障模式） |
| L4 组件与版本 | 跑在什么组件上 | 环境是否同构 | 不参与打分（案例侧记录） | 0 |
| L5 机理与证据 | 证据长什么样 | 证据是否同源 | 语义匹配佐证；反证护栏 | 1.0（关键词） |
| 影响范围 | 波及 Pod/Host 规模 | 影响面多大 | 分布特征（规模分类，不用名字） | 0.5（规模分类相等） |
| 拓扑形状 | 源目链路对 | 受影响实体是否成对 | 分布特征（link_pair 形状相等） | 0.5（仅 link_pair） |

> **v1 → v2 变化**：身份特征（src_ip/dst_ip/host/pod/cluster 的具体名字）退出匹配；
> 改用**分布/语义**特征软打分——错误码、故障模式、时延阶段桶（超时时延段）按现场贡献
> 占比 `share` 加权，时间形态、操作域与影响规模作为弱加分。召回也由"信号精确命中"改为
> "宽召回 + 客户端软打分"（详见 `SKILL.md` 与 `scripts/match_cases.py`）。

> **相对权重参考**：本表的权重比例吸收自 Web 前端"相似案例分析"模块
> （`src/plugins/latency/services/similarity.py`）——故障模式分布 6.0 / 状态码分布 4.0 /
> 操作·段排名 3.0 / 超时段集合·时延形态 2.0 / 空间规模 1.0~2.5。本 Skill 在保留
> `share` 加权与宽召回口径的前提下做化用：故障模式权重提到 4.0（高于错误码 3.0，
> 语义最可迁移）、时延形态 0.5→1.0、新增 `operation` 弱加分；Web 的类别 gate 与
> 不对称惩罚已被宽召回（fault_type 过滤）与查询侧分母归一化天然覆盖，不再重复实现。

软匹配权重表（`scripts/match_cases.py` 的 `SOFT_WEIGHT`，Agent 书写报告时据此给出
逐级命中判定；服务端 API 自身的信号表不改，直接调用 `/diag_case_library/search` 的
外部消费者仍走服务端口径）：

| 特征 | 权重 | 取值形式 | share 来源 |
|---|---|---|---|
| `failure_mode_id` | 4.0 | 精确语义 ID | 1.0（跨现场可迁移，不稀释） |
| `status_code` | 3.0 × **F1** | 主导错误码列表 + 占比 | `F1 = 2PR/(P+R)`；`P = 命中码数 / 案例码集大小`，`R = 命中码数 / 查询码数` |
| `latency_component` | 2.0 × share | 归因桶 key + 占比 | `/stats/stages` 中该桶 trace_cnt / 归因桶总 trace_cnt |
| `operation` | 1.0 | GET / SET（案例 MIXED 给半权） | 1.0（library 通道已服务端过滤，仅区分 MIXED） |
| `log_keyword` | 1.0 | 现场日志原文短语 | 1.0 |
| `time_shape` | 1.0 | `突发单点`/`短时簇发`/`持续劣化` | 1.0（相等即加分） |
| `affected_scope` | 0.5 | `single_pod`/`few_pods`/`multi_pod` | 1.0（规模分类相等即加分） |
| `topology_shape` | 0.0 | `link_pair`（源目链路对；其余形状预留不参与） | 1.0（查询/案例均为 link_pair 即加分；**权重已归零**，提取逻辑保留） |
| `domain_prior` | 0.2 × p | 码/故障模式→故障域先验（见下） | 候选池内 码（通道权重 0.25）+ 故障模式（通道权重 0.1）→一级标签 投票，命中预测标签者得 0.2 × 该标签得票占比 p |

`score_norm`（基础软匹配分）`= Σ(命中特征 base×share) / Σ(全部查询特征 base×share)`，0~1，跨查询可比；
最终排序主键还会叠加域先验与日志语义码次级通道（见「日志语义码次级通道」节），故落盘值可 >1。

> **v2.4 打分改造（训练集 1110 LOO 实证）**：原等权打分下 82.2% 的查询 top1 与其它候选
> `score_norm` 完全并列（55.7% 跨一级标签），最终靠 `text_sim` 抛硬币，是"硬件↔Worker
> 互混"的主因。三条正交改造（`scripts/match_cases.py`）：① `status_code` 由等权召回改为
> **F1（精度×召回）**计分，使"码集完全命中"的精确案例压过"码多且杂"的宽泛案例；
> ② 新增 **码/故障模式→故障域先验**：按候选池内 码→一级标签 分布对查询真实码投票，命中预测
> 域的候选加 `0.2 × 得票占比`；故障模式通道权重 0.1（与错误码 0.25 构成 2.5:1，LOO 网格最优）；
> Agent 折算的相近码 share=0.5，只发挥一半影响；
> ③ `topology_shape` 权重 0.5 → 1.5（后经 LOO 消融证伪为净负特征，已归零为 0.0）。实测（不含C/不含集群 185 条）：top1 68.6% → **70.8%**，
> label_vote K14 67.6% → **68.6%**；关键字去重（81 类）K14 63.0% → **67.9%**。

---

## L0 身份与范围（仅记录，不参与打分）

| 特征 | 取值 | 提取来源 |
|---|---|---|
| `log_type` | `KVCACHE` / `BRPC` | `log_file.log_type`、`diagnosis_config` |
| `kb_id` / `log_id` | 知识库 ID / 日志文件 ID | `POST /log_kb/list`、`POST /log_file/list/{kb_id}` |
| `cluster_name` / `host` / `pod_ips` | 实际存在的取值，不臆造 | `GET /log_parse_result/options?kb_id=` |
| `src_ip` / `dst_ip` | 源目对；无源目对的 trace 不要硬凑 | `POST /stats/links`、`/trace/list`（`include=topology`） |
| `time_window` | `start` / `end` | `/stats/heatmap`、`/trace/list` |

> - `GET /log_parse_result/options` 返回空 cluster/host 时表示未解析出，不是"没有集群"。
> - IP/Pod/主机/集群名**只作样本来源标注**（报告 provenance），不得提交为匹配特征。

## L1 时间演化（软匹配弱加分）

| 特征 | 字段 | 提取来源 |
|---|---|---|
| 时间跨度 | 首末事件时间之差 | `/stats/heatmap` 的 `window_start` 序列 |
| 峰值槽 | `window_start` + `fault_trace_cnt` 最大的槽 | `POST /stats/heatmap`（自动选窗 `1m`/`10m`/`1h`，slots ≤ 240） |
| 峰值占比 | 峰值槽故障数 / 故障总数 | 由 heatmap 结果自算 |
| 时间形状 | `突发单点` / `短时簇发` / `持续劣化` | 由峰值占比与跨度判断（阈值见 SKILL.md 判定规则） |

> `time_shape` 提交到特征 JSON 后参与软匹配：案例 `fault_shape` 与之相等得 0.5。
> 案例侧 `fault_shape` 未填（null）时不加分、不扣分。

## L2 操作与阶段（时延故障核心特征，按占比加权）

必须**按 operation 分开**：GET 走 8 桶，SET 走 5 桶，两套口径独立。

| operation | 桶 key（固定顺序，含零计数桶） |
|---|---|
| GET | `rpc_network`、`rpc_queue`、`query_meta`、`urma`、`data_worker`、`cross_window`、`residual`、`urma_timeout` |
| SET | `set_urma_timeout`、`set_no_evidence`、`set_residual`、`set_client`、`set_worker` |

每桶可用字段（`POST /stats/stages`，`operation` 各调一次）：

| 字段 | 含义 |
|---|---|
| `trace_cnt` / `success_cnt` / `fail_cnt` | 归入该桶的 trace 数、其中成功/失败数 |
| `p50_ms` / `p90_ms` / `max_ms` | 该桶**主阶段证据耗时**分位（口径见 `metric_name`） |
| `client_p50_ms` / `client_p90_ms` | 桶内 trace 的 Client 总时延对照 |
| `metric_name` | 证据口径：主阶段耗时 / URMA timeout elapsedMs / Client 总时延（数据面未观测） |
| `note` | 桶构成字段说明；`set_no_evidence` 等的判桶依据在这里 |
| `top_traces[].trace_id` | 下钻种子 |
| `sample_cnt` / `truncated` | 采样总数 / 是否被 `sample_cap` 截断 |

> - 写入 `latency_components` 时使用**桶 key**（如 `urma`、`set_client`），与案例写入侧约定一致；
>   不要写中文桶显示名，否则匹配对不上。
> - **share 提取**：超时时延段（归因桶）的贡献占比 = 该桶 `trace_cnt` ÷ 归因桶总 `trace_cnt`
>   （参与分类的样本内占比，保留 `sample_cnt`/`truncated` 注记）。把占比最大的 1~2 个桶
>   连同 share 一起写入 `latency_components` 与 `latency_component_shares`。
> - 时延故障**至少**要提交归因桶（超时时延段）作为匹配特征；通断故障不产出阶段桶，
>   以错误码/故障模式/关键词为主。

## L3 故障语义（按分布占比加权）

| 特征 | 取值 | 提取来源 |
|---|---|---|
| `status_codes` | 故障码（如 `1001`、`1002`、`3`、`21`） | `POST /stats/error_codes`、`/log_failure_event_result/list_trace_events` |
| 故障码知识 | `symptom` / `root_cause` | `GET /failure_mode/status_code/{code}`（404 = 未知码，不等于健康） |
| `failure_mode_ids` | 如 `kvcache_conn_fault_020`、`kvcache_conn_fault_020_007` | `list_trace_events` 的 `failure_mode` |
| 故障模式知识 | `failure_domain`、`error_code`、`children_failure_mode_ids`、`solution` | `GET /failure_mode/{failure_mode_id}` |
| `fault_type` | `latency` / `connectivity` / `mixed` / `unknown` | 由状态码与现象判定（检索时服务端会附带 `mixed`、`unknown`） |

> - **share 提取**：提交主导错误码 1~3 个，share = 该码命中次数 ÷ 全部故障码命中次数
>   （逐码命中口径）。`status_code_shares` 缺省时该码 share=1.0（全权重精确匹配）。
> - **口径不一致要如实记录**：`/stats/error_codes`、`/metrics/err_code`、
>   `list_time_aggregated_failure_events` 与 `list_trace_events` 的 total 可能不一致（数据侧
>   两条链路不同源），不要用一套 API 的空结果去否定另一套的非空结果。

## L4 组件与版本（不参与打分）

BRPC 侧：

| 特征 | 字段 | 提取来源 |
|---|---|---|
| `component` | `ubsocket` / `umq` / `urma` | `brpc_diag_node.component`、`GET /brpc-diagnosis/batch/{batch_id}/summary` |
| 故障节点 | `node_id`、`name`、`function_name`、`filename` | `brpc_diag_node`、`brpc_diag_node` 详情接口 |
| 现象/根因/方案 | `phenomenon`、`cause`、`solution`、`error_code` | 同上 |
| 线程/接口 | `thread_key`、命中接口 | `brpc_diag_hit`、`brpc_diag_failure_interface` |
| 峰值窗口 | `peak_window` | `/brpc-diagnosis/*/summary` |

KVCache 侧：`log_parse_result.request_mode`（如 `__cn` 单跳/多跳相关分支）。

> **版本承载**：`diag_case_library` 有 `version_json` 字段（`kernel` / `os` / `urma` / `umq` /
> `ubsocket`），写入侧有可靠来源时应填写；legacy 表**没有**该字段。
> 版本不参与打分，只作 `applicability` 的可迁移性判据进正文。
> 取不到时只能靠日志原文（`uname`、组件启动 banner）或用户提供，必须在输出中标注来源与不确定性，
> 不得臆造版本号。

## 影响范围（分布特征，用规模不用名字）

| 特征 | 取值 | 提取来源 |
|---|---|---|
| `affected_scope` | `single_pod` / `few_pods` / `multi_pod` | 本次故障波及的 Pod/Host 去重数量：≤1 → `single_pod`；2~4 → `few_pods`；≥5 → `multi_pod` |

> 案例侧由 `pods`/`hosts` 字段数量分类（脚本自动换算，Agent 不需要在案例侧填）。
> 规模分类相等得 0.5 弱加分；**不使用具体 Pod/Host 名字做匹配**。

## 拓扑形状（分布特征，规模无关）

| 特征 | 取值 | 提取来源 |
|---|---|---|
| `topology_shape` | `link_pair`（当前仅此值参与；`bi_pair`/`conc_1`/`conc_multi`/`spread` 预留） | 本次故障受影响实体的**源目链路对表示**（`A ↔ B` / `A → B` / `A -> B` 等箭头形式） |

> - **提取规则（查询侧）**：报告 `statistics.top_pods[].pod` 中任意一项含箭头（`↔`/`→`/`->`/`⟷`/`⇄`/`⇒`）→ 提交 `topology_shape = "link_pair"`；否则**不提交该字段**。
> - **案例侧**：由案例 `pods` 字段自动判定（同一箭头规则），Agent 不需要在案例侧填。
> - 判据全部无量纲，不依赖绝对 Pod 数量，大集群下规则仍成立；LOO 实测 link_pair 100% 指向硬件故障（client_*_tcp_down / scale_in_tcp_down 等）。
> - 查询/案例均为 link_pair 时加 0.5 弱加分；其余形状因案例侧 `pods` 无浓度(pct)信息暂不参与，避免单侧进分母稀释。

## L5 机理与证据

| 特征 | 说明 | 提取来源 |
|---|---|---|
| `log_keywords` | 可复现的日志短语，如 `RPC_RECV_TIMEOUT`、`URMA_ELAPSED_TOTAL`、`meta is moving`、`disconnected from worker`、`K_SHUTTING_DOWN` | 原始日志、`log_failure_event.raw_text`（**只能来自现场观测，不得套用历史案例里的短语**） |
| 证据锚点 | `trace_id` + 文件 + 行号 / API 调用 | `evidence_refs_json` |
| 反证点 | 已排除的候选（如"Worker 侧几乎未收到请求"排除 Worker 崩溃） | `counter_evidence_json` |

---

## 日志语义码次级通道（v2.5，非 SOFT_WEIGHT 特征）

软打分之外新增一条**加性次级通道** `log_semantic`：查询侧与候选案例侧各有一份
「日志语义错误码轮廓」，取 cosine 相似度，按 `LOG_SEMANTIC_WEIGHT = 0.5` 加到
`score_norm`（仅用于排序与 margin 判定，不进 `_soft_score` 的分母）。

- 轮廓定义：`log_failure_event`（level ∈ E/W）原文里的语义错误码
  `code: [Not ready]`、`code: [Urma wait for completion timed out]`，
  以及日志常量 token `URMA_WAIT_TIMEOUT`、`E2001` 等；各自归一化为单位向量
  （常量 token 权重 ×3）。抽取实现以后端 `services/log_semantic_profile.py` 为唯一权威。
- 轮廓随文档/案例**持久化**（不再依赖离线资产）：
  - 报告侧：`render_report.py` 生成文档时调
    `POST /log_failure_event_result/log_semantic_profile` 写入 `basic_info.log_semantic_profile`。
  - 案例侧：报告确认建案时，`build_draft_from_fault` 透传文档自带轮廓；文档未带该字段则由
    后端按来源资产（`kb_id`→`log_file.kb_id`，回退 `kb_name`→`log_file.name`）兜底现算，
    落到 `diag_case_library.log_semantic_profile`，随 `/search` 响应返回。
- 候选案例侧：直接读 `/search` 返回的 `case.log_semantic_profile`；
  旧数据缺失时回退静态资产 `references/log_semantic_profiles.json` 的 `by_case_id`。
- 查询侧：优先用特征 JSON 的内联 `log_semantic_profile`；否则按 `kb_id` 调同一接口现算；
  再否则按 `log_id`/`kb_name` 查静态资产。全都没有则该通道自动关闭（对结果无副作用）。
  可用 `--no-log-semantic` 关闭做消融。
- 实测（188 条不含C / 237 案例池，冻结口径）：top1 66.5%→**70.7%**、K4 69.7%→**70.7%**；
  收益全部落在"硬件↔Worker"边界（URMA 时延族 vs Not ready/RPC peer dead 族）；
  SDK/OS/容器 等无 E/W 日志的小类不受影响（无提升也无误伤）。

---

## 已证伪的候选特征（勿重复尝试）

以下方向均已用「合并集 prefix-LOO」口径（475 条非 C 有标签场景 = train 195 + v7 280；
**排除与查询同前缀的候选**，即同场景重放，严格无泄漏）做过消融，**结论为负**，
不要重复实现。基线：top1 **69.5%** / K4@margin=0.05 **65.9%**。

### 1. 否定证据 / 缺席特征通道（2026-11-13，负）

曾设想「打分为纯加性正证据，小类必被大类吸走，故补充反面证据」。实测四个二值存在特征：

| 特征 | 含义 | 分布 |
|---|---|---|
| `has_ctrl_plane` | 日志文件名含 master/coordinator 进程 | SDK **0/12**，容器 19%、OS 10%，Worker 31%、硬件 22% |
| `has_rpc_dead` | E/W 原文含 `RPC peer dead` / `Metadata owner unavailable` / `brpc errno` / `deadline exceeded` | Worker 54~61%，**SDK 全 0** |
| `has_urma_write` | 含 token `URMA_WRITE` | SDK 100%、容器 63%，Worker 25%、硬件 44% |
| `has_worker_code` | 错误码含 39 / 1001 / 1002 | Worker 富集，**SDK 0%** |

消融结果（prefix-LOO）：

| 变体 | top1 | K4 | 硬件 | Worker | 容器 | SDK | OS |
|---|---|---|---|---|---|---|---|
| base | 69.5% | 65.9% | 225/278 | 105/148 | 0/27 | 0/12 | 0/10 |
| +bin（等值加分 w=0.5~2.0） | 68.2~68.4% | 66.1~66.7% | 219 | 103~104 | 0/27 | 2/12 | 0/10 |
| +veto（无 worker_code 且无 rpc_dead → 剔 Worker 候选） | 69.1% | 66.1% | 238 | 90 | 0/27 | 0/12 | 0/10 |

**无一组整体优于 base。** 失败原因：这四个特征与硬件/Worker 高度共享（`URMA_WRITE` 在硬件占 44%），
等值加分淹在 278 条硬件里；`veto` 只拦得住 Worker，拦不住真正吸走小类 top1 的**硬件**大类，
而硬件与小类共享 URMA 错误码族、没有可用的否定证据。

### 2. 已计算但未进 `SOFT_WEIGHT` 的派生量（2026-11-13，对小类无区分力）

`latency.p99_p50_ratio`、`latency.op_p99_p50_ratio`、`latency.anomalous_ratio`、
`connectivity.spatial_*.scope`、`summary` 三计数、`fault_category`——**对容器/OS/SDK 全无区分力**，
最多用于微调"硬件↔Worker"边界（如 p75 的 p99/p50：Worker 4.92 vs 硬件 2.00），
补进权重表救不了小类。

### 3. 小类（容器 / SDK / OS）的现状与结论

- **容器故障 27 条**：与硬件共享 URMA 错误族，逐特征仅高 20~28pp，无干净信号；
  且**容器重启事件根本不落日志**（E/W 原文无 restart/oom/kill 关键词），
  唯一独有线索「E/W 时间跨度中位 9s（突发）」噪声过大。
- **OS 故障 10 条**：样本过少，各特征在硬件/Worker/OS 间均为 30~40%，当前不可分。
- **SDK 故障 12 条**：存在 100% 召回规则（`URMA_WRITE` 且无 {39,1001,1002} 且无 RPC-dead 族，
  且**场景里没有管控面进程日志**），但误伤硬件 116 条，只能当否决票、不能做正分类。
- 三小类合计 49 条，任何 ±2 条的差异都在噪声内。

**结论：小类在当前数据上已无算法空间，需先补数据**——容器重启/退出事件、独立的 OS 日志源，
否则任何特征工程都是在噪声里拟合 49 条样本。

---

## 特征 JSON 骨架（`scripts/match_cases.py` 的输入）

```json
{
  "operation": "SET",
  "kb_id": "<本次知识库ID；library 通道可省略（留空=跨库召回），legacy 通道必填且必须真实存在>",
  "kb_name": "<报告 basic_info.kb_name；日志语义码次级通道查询侧的回退索引>",
  "log_id": "<可选>",
  "log_semantic_profile": "<可选：报告 basic_info.log_semantic_profile 内联轮廓，日志语义码次级通道查询侧首选>",
  "fault_type": "latency",
  "status_codes": ["1004"],
  "status_code_shares": {"1004": 0.8},
  "failure_mode_ids": ["kvcache_access_022"],
  "latency_components": ["set_client", "set_worker"],
  "latency_component_shares": {"set_client": 0.6, "set_worker": 0.3},
  "time_shape": "持续劣化",
  "affected_scope": "multi_pod",
  "topology_shape": "link_pair",
  "log_keywords": ["K_SHUTTING_DOWN"],
  "query_text": "SET 写路径集中超时：归因桶 set_client，客户端 Create/Publish RPC 等待占主导，trace 证据 P99 42ms",
  "time_window": { "start": "2026-05-11 00:08:00", "end": "2026-05-11 00:15:00" },
  "notes": "SET 写路径集中超时，归因桶 set_client；IP/Pod 等身份信息只进 provenance，不作匹配特征"
}
```

约束：

- `kb_id`：library 通道可选，留空 = 跨知识库召回（`kb_id` 只作来源标注）；legacy 通道必填，
  服务端校验知识库存在性，**空串会被拒**，不能用来做"跨库检索"。
- **不再要求"至少一个可匹配信号"**（v1 约束）：宽召回按过滤头拉候选，软打分在客户端完成；
  但未提供任何分布特征时所有候选打分为 0，只会按 confidence/hit_count 排序——尽量给出
  错误码、时延段、关键词等至少一类分布特征。
- `operation`：library 通道是纯过滤字段，提交即隔离 GET/SET；legacy 通道没有该字段，
  只能把 `operation` 留在正文标注。任何通道都禁止把两种操作的信号合并成一次查询。
- **用户使用问题锁定召回**：查询 `status_codes` 命中
  `USER_USAGE_FAULT_CODES`（`1/3/9/12/17/28/2000/2001/2004/2006/3000/3001/3002/3004/3006/3007/3009`，
  剔除 `0/2/8/36`，其中 `0` 为「无错误/成功」码）时，召回查询额外带 `first_level_label=用户相关故障` +
  `second_level_label=使用问题`，**只召回该类案例**；命中码见输出 `user_usage_codes`，
  锁定标签见 `fault_label_override`。库内无该类案例时返回空，不降级、不回退。
- **未见码的相近码回退**：`relaxed_status_codes`（可选）装案例库未收录的故障码所对应的
  相近已知码，由 `scripts/suggest_similar_codes.py` 产出（依据：人工映射表
  `references/similar_code_map.json` > 同码段家族 > 同知识库故障域）。这些码以
  `share=0.5` 并入软打分；不计入 `status_code_shares`，不参与用户使用问题硬判定，
  也不出现在报告的错误码清单里。检索输出会回显 `relaxed_status_codes`。
- `share` ∈ (0,1]，表示该特征在本次故障中的贡献占比；占比小但确认存在的特征也应提交
  （分母会相应加权，保证 score_norm 可比）。
- `query_text`（可选）：诊断中途草稿文本，**只含现象确认与阶段定位**（confirmed=True 的
  推理步、阶段桶名、证据 trace 与时延指标），**不得写入候选根因/反证/结论/处置**。
  脚本用它做词级 cosine 文本相似度，与案例表现字段（symptom_summary/fault_shape/
  latency_components/log_keywords）比对，作为 score_norm 并列时的次级排序键
  （LOO 消融实验"草稿Q/表现C"口径 59.2%，+5.9pp，零引导性污染）。缺失时该维度为 0，
  排序退化为纯软打分。
- `src_ips` / `dst_ips` / `hosts` / `pods` / `clusters` 可留在特征 JSON 里作来源标注，
  **脚本不把它们提交为匹配信号**。
- `time_window`、`notes` 不参与打分，落盘留存供报告引用。

## 检索结果字段（`--json` 落盘）

| 字段 | 含义 |
|---|---|
| `score_norm` | 排序主键 = 分布特征软匹配分 + 域先验 + 日志语义码次级通道（见上节），后两项为加性项，故**可 >1** |
| `score_raw` | 未归一化的软匹配命中权重和 |
| `text_sim` | `query_text` 与案例表现文本的词级 cosine 相似度（0~1）。案例表现文本 = symptom_summary/fault_shape/latency_components/log_keywords + evidence_json.excerpt（前 6 条现场证据锚点）；错误码/日志常量词（K_URMA_ERROR、E112 等）权重 ×3。score_norm 并列时的次级排序键；未提供 query_text 时恒为 0 |
| 翻盘规则 | top1 与候选 score_norm 差 <0.2 且候选 text_sim 显著更高（>0.15）时，文本匹配最强的候选提到第 1 位（P2），修正 norm 错位但文本高度吻合的误排 |
| `feature_coverage` | 命中特征数 / 查询特征数 |
| `levels` | L1/L2/L5 各级命中的具体特征值 |
| `level_summary` | 命中级别摘要，如 `L2`、`L1+L2` |
| `counter_evidence_count` | 案例自带反证条数，用于借力排除 |
| `source` / `source_confirmed` | 检索通道；`source_confirmed=false` 即 legacy，引用时必须标注未确认 |
| `case_no` / `status` / `revision` | 可读编号 / 状态 / 修订号（legacy 通道为空） |
| `verification_closed` / `verification_result` | 验证是否闭环 / 实测结果（根因是否被证实的硬证据） |
| `scope_limits` | 案例声明的**不适用场景**，判定 applicability 时必须逐条比对 |
| `evidence_ref_count` | 证据锚点条数（library 为 `evidence_json`，legacy 为 `evidence_refs_json`） |
