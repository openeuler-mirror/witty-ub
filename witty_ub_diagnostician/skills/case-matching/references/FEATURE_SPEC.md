# 超节点日志案例特征清单（六层）

本文件是**查表型**参考：定义"一个日志案例该记录哪些特征、每个特征从哪个 API/表取、在匹配里起什么作用"。
判决标准与纪律在 `SKILL.md`，本文件不重复。

适用范围：KVCache（时延/通断）与 BRPC 两类诊断对象。两者的标识体系不混用。

---

## 特征总览

| 层 | 特征 | 回答的问题 | 匹配作用 | 规则通道权重 |
|---|---|---|---|---|
| L0 身份与范围 | 样本标识与拓扑边界 | 这是哪一份样本 | L3 拓扑；决定可复用范围 | 1.5（IP/Pod/主机/集群） |
| L1 时间演化 | 故障的时间形状 | 怎么发生的 | 多故障分诊的时间窗信号 | 不参与打分（案例侧记录） |
| L2 操作与阶段 | 瓶颈在哪一段 | 卡在哪里 | L2 故障域；最可迁移的机理特征 | 1.5（阶段桶） |
| L3 故障语义 | 系统报了什么 | 报的什么错 | L1 错误码 | 3.0（状态码/故障模式） |
| L4 组件与版本 | 跑在什么组件上 | 环境是否同构 | L2 故障域；可迁移性判定 | 不参与打分（案例侧记录） |
| L5 机理与证据 | 证据长什么样 | 证据是否同源 | 语义匹配主力；反证护栏 | 1.0（关键词） |

规则通道的权重取自 `DiagCaseLibraryPGManager._signals_for_search`（library 通道）与
`DiagnosisCasePGManager._signals_for_search`（legacy 通道），两者同源；`scripts/match_cases.py`
的 `SIGNAL_WEIGHT` 与之同源。**服务端调整权重时必须同步脚本**，否则归一化口径漂移。

---

## L0 身份与范围

| 特征 | 取值 | 提取来源 |
|---|---|---|
| `log_type` | `KVCACHE` / `BRPC` | `log_file.log_type`、`diagnosis_config` |
| `kb_id` / `log_id` | 知识库 ID / 日志文件 ID | `POST /log_kb/list`、`POST /log_file/list/{kb_id}` |
| `cluster_name` / `host` / `pod_ips` | 实际存在的取值，不臆造 | `GET /log_parse_result/options?kb_id=` |
| `src_ip` / `dst_ip` | 源目对；无源目对的 trace 不要硬凑 | `POST /stats/links`、`/trace/list`（`include=topology`） |
| `time_window` | `start` / `end` | `/stats/heatmap`、`/trace/list` |

> `GET /log_parse_result/options` 返回空 cluster/host 时表示未解析出，不是"没有集群"。

## L1 时间演化

| 特征 | 字段 | 提取来源 |
|---|---|---|
| 时间跨度 | 首末事件时间之差 | `/stats/heatmap` 的 `window_start` 序列 |
| 峰值槽 | `window_start` + `fault_trace_cnt` 最大的槽 | `POST /stats/heatmap`（自动选窗 `1m`/`10m`/`1h`，slots ≤ 240） |
| 峰值占比 | 峰值槽故障数 / 故障总数 | 由 heatmap 结果自算 |
| 时间形状 | `突发单点` / `短时簇发` / `持续劣化` | 由峰值占比与跨度判断（阈值见 SKILL.md 判定规则） |

## L2 操作与阶段（最可迁移）

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

> 写入 `latency_components` 时使用**桶 key**（如 `urma`、`set_client`），与案例写入侧约定一致；
> 不要写中文桶显示名，否则信号值对不上。

## L3 故障语义

| 特征 | 取值 | 提取来源 |
|---|---|---|
| `status_codes` | 故障码（如 `1001`、`1002`、`3`） | `POST /stats/error_codes`、`/log_failure_event_result/list_trace_events` |
| 故障码知识 | `symptom` / `root_cause` | `GET /failure_mode/status_code/{code}`（404 = 未知码，不等于健康） |
| `failure_mode_ids` | 如 `kvcache_conn_fault_020`、`kvcache_conn_fault_020_007` | `list_trace_events` 的 `failure_mode` |
| 故障模式知识 | `failure_domain`、`error_code`、`children_failure_mode_ids`、`solution` | `GET /failure_mode/{failure_mode_id}` |
| `fault_type` | `latency` / `connectivity` / `mixed` / `unknown` | 由状态码与现象判定（检索时服务端会附带 `mixed`、`unknown`） |

> **口径不一致要如实记录**：`/stats/error_codes`、`/metrics/err_code`、
> `list_time_aggregated_failure_events` 与 `list_trace_events` 的 total 可能不一致（数据侧
> 两条链路不同源），不要用一套 API 的空结果去否定另一套的非空结果。

## L4 组件与版本

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
> 但检索打分仍不消费版本（查询侧没有对应信号类型），版本只作 `applicability` 的可迁移性判据进正文。
> 取不到时只能靠日志原文（`uname`、组件启动 banner）或用户提供，必须在输出中标注来源与不确定性，
> 不得臆造版本号。

## L5 机理与证据

| 特征 | 说明 | 提取来源 |
|---|---|---|
| `log_keywords` | 可复现的日志短语，如 `RPC_RECV_TIMEOUT`、`URMA_ELAPSED_TOTAL`、`meta is moving`、`disconnected from worker` | 原始日志、`log_failure_event.raw_text`（**只能来自现场观测，不得套用历史案例里的短语**） |
| 证据锚点 | `trace_id` + 文件 + 行号 / API 调用 | `evidence_refs_json` |
| 反证点 | 已排除的候选（如"Worker 侧几乎未收到请求"排除 Worker 崩溃） | `counter_evidence_json` |

---

## 特征 JSON 骨架（`scripts/match_cases.py` 的输入）

```json
{
  "operation": "SET",
  "kb_id": "<本次知识库ID；library 通道可省略（留空=跨库召回），legacy 通道必填且必须真实存在>",
  "log_id": "<可选>",
  "fault_type": "connectivity",
  "status_codes": ["1002", "1001"],
  "failure_mode_ids": ["kvcache_conn_fault_020", "kvcache_conn_fault_020_007"],
  "src_ips": ["192.168.219.66"],
  "dst_ips": ["192.168.235.172"],
  "hosts": [],
  "pods": ["192.168.219.66"],
  "clusters": ["jingpai"],
  "latency_components": ["set_client", "set_worker"],
  "log_keywords": ["RPC_RECV_TIMEOUT", "disconnected from worker"],
  "time_window": { "start": "2026-05-11 00:08:00", "end": "2026-05-11 00:15:00" },
  "notes": "SET 写路径集中失败，GET 侧仅单条离群"
}
```

约束：

- `kb_id`：library 通道可选，留空 = 跨知识库召回（`kb_id` 只作来源标注）；legacy 通道必填，
  服务端校验知识库存在性，**空串会被拒**，不能用来做"跨库检索"。
- 至少要有一个可匹配信号，否则脚本以退出码 2 拒绝。
- `operation`：library 通道是服务端过滤字段，提交即隔离 GET/SET，且计入归一化分母；
  legacy 通道没有该字段，只能把 `operation` 留在正文标注，靠"分两次查询、各自只提交本
  operation 的信号"实现隔离。任何通道都禁止把两种操作的信号合并成一次查询。
- `time_window`、`notes` 不参与打分，落盘留存供报告引用。

## 检索结果字段（`--json` 落盘）

| 字段 | 含义 |
|---|---|
| `score_norm` | 命中权重和 / 查询权重和，0~1，跨查询可比，排序主键 |
| `score_raw` | 服务端口径的命中权重和（未归一化） |
| `signal_coverage` | 命中信号数 / 提交信号数 |
| `levels` | L1/L2/L3/L5 各级命中的具体信号值 |
| `level_summary` | 命中级别摘要，如 `L1+L3` |
| `counter_evidence_count` | 案例自带反证条数，用于借力排除 |
| `source` / `source_confirmed` | 检索通道；`source_confirmed=false` 即 legacy，引用时必须标注未确认 |
| `case_no` / `status` / `revision` | 可读编号 / 状态 / 修订号（legacy 通道为空） |
| `server_score_norm` | 服务端返回的归一化分（library 通道有，与本脚本口径一致） |
| `verification_closed` / `verification_result` | 验证是否闭环 / 实测结果（根因是否被证实的硬证据） |
| `scope_limits` | 案例声明的**不适用场景**，判定 applicability 时必须逐条比对 |
| `evidence_ref_count` | 证据锚点条数（library 为 `evidence_json`，legacy 为 `evidence_refs_json`） |