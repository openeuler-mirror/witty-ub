# 时延段特征：字段作用与上游来源

## 适用范围

新增可选对象 `faults[].latency.stages[].features`；扁平单故障同样支持
`latency.stages[].features`。旧字段继续使用，旧报告无需迁移。

这些新特征是 **`/stats/stages` 互斥归因桶的证据画像**。同一实际阶段可能覆盖多个桶，
桶内统计也只针对归入该桶的请求。Agent 根据本次归因把正确桶附到对应阶段；
不要按中文名称自动匹配，更不要用全桶数据替代物理阶段的全请求分布。
如果一个阶段需要说明多个桶，可分别增加阶段行并在 `name/detail` 点明桶口径。

上游代码依据（路径相对仓库根目录）：

- `src/plugins/latency/schemas/trace_light.py`：`GetStageStatsRequest`、`StageStatsItem`、
  `GetStageStatsMsg`、`ListTracesRequest`、`TraceListItem`。
- `src/plugins/latency/services/stats.py`：异常 + top 慢正常选样、互斥分类、
  只对有效证据耗时计算分位、按证据耗时选 Top trace。

## 提取已有响应

把本次真实调用的**请求和完整响应**（`code=200`）写入一个快照 JSON。只有 `current` 必填；
`baseline` / `windows` / `traces` 未调用就省略，不为填满字段强制额外查询。

```text
{
  "current": {"request": /stats/stages 的真实请求对象,
              "response": 对应完整响应对象},
  "bucket_keys": [本故障归因桶的 key],
  "baseline": {"request": 对照窗口 /stats/stages 请求,
               "response": 对照窗口完整响应},
  "windows": [{"request": 子窗口 /stats/stages 请求,
               "response": 子窗口完整响应}],
  "traces": {"request": /trace/list 请求,
             "response": 对应完整响应}
}
```

```bash
python3 scripts/latency_features.py /tmp/stage_snapshots.json /tmp/stage_features.json
python3 scripts/render_report.py --spec latency
```

取输出 `features_by_bucket[归因桶key]` **整体**放入该阶段的 `features`；不要手抄数字。
`bucket_keys` 缺省提取响应中的全部桶。脚本不修改上游、不联网、也不自动决定
阶段 `name/status/detail`。错误输入退出 2，不生成降级或补造的特征。

请求约束：

- `current.request` 保留 `kb_id`、显式 `operation`，以及实际使用的
  `log_id/start_time/end_time/sample_cap`；不把 `/stats/stages` 不支持的 host/IP 过滤塞入请求。
- GET key：`rpc_network/rpc_queue/query_meta/urma/data_worker/cross_window/residual/urma_timeout`。
  SET key：`set_urma_timeout/set_no_evidence/set_residual/set_client/set_worker`。
- 对照/子窗口：相同 `kb_id/log_id/operation/bucket_key/metric_name`；完整时间窗，
  对照不得与当前窗口重叠，子窗口须在当前窗口内、有序且无重叠。保留各窗独立样本量和截断标记，
  不累加各窗分位数；边界请求也不据此重复求和。时间沿用上游无偏移事件时间（Asia/Shanghai）。
- 对照响应只代表所选对照窗口；Agent 还须确认其业务负载、路径和现场状态可比，
  不得仅因指定为 baseline 就称为“健康基线”。归因桶成员随窗口变化，比较不是配对请求实验。
- `traces.request` 显式 `trace_ids` 包含所选桶全部 `top_traces[].trace_id` 的并集，
  `include` 包含 `topology/failure_codes`，其 `kb_id/log_id/operation/start_time/end_time`
  与当前统计一致。允许分页结果不全，但须保留缺失 ID；脚本只合并当前桶的 Top trace。

## 核心字段（每个 features 对象）

下表 `item` 指 `current.response.result.items[]` 中 key 对应的唯一桶，
`result` 指 `current.response.result`。所有 `_ms` 为数值型毫秒，比例 `_pct` 为 0～100。
无值的数值为 `null`；零值仍显示为零，不能用零代替未知。

| 字段 | 来源 / 计算 | 作用 |
|---|---|---|
| `operation` | `result.operation`，须与请求一致 | 隔离 GET/SET 两套统计口径 |
| `bucket_key` | `item.key` | 稳定标识归因桶，便于关联与匹配 |
| `metric_name` | `item.metric_name` | 区分主阶段耗时、URMA timeout elapsedMs、未观测数据面的 Client 总时延等证据口径 |
| `source.endpoint` | 固定 `/stats/stages` | 标识来源接口 |
| `source.request` | 本次真实请求原样保留 | 复现知识库、日志文件、操作、时间范围及采样上限 |
| `source.response_path` | 对应 `result.items[i]` 路径 | 定位响应中的具体证据桶 |
| `sample_cnt` | `result.sample_cnt` | 所有互斥桶计数总和，也是桶占比的分母 |
| `truncated` | `result.truncated` | 提示是否受采样上限等因素截断 |
| `sample_note` | `result.note` | 保留选样、粗分和数据路径限制 |
| `trace_cnt` | `item.trace_cnt` | 本桶样本请求数 |
| `normal_cnt` | `item.success_cnt` | `is_anomalous=false` 的计数，**不是业务成功数** |
| `anomalous_cnt` | `item.fail_cnt` | `is_anomalous=true` 的计数，**不是业务失败数/超时数** |
| `bucket_share_pct` | `trace_cnt / sample_cnt × 100` | 本桶在分类样本中的请求占比，**不是耗时占比** |
| `anomalous_ratio_pct` | `anomalous_cnt / trace_cnt × 100` | 桶内异常标记比例，**不是该阶段超阈率/超时率** |
| `distribution.p50_ms` | `item.p50_ms` | 桶内有效证据耗时的中位数 |
| `distribution.p90_ms` | `item.p90_ms` | 桶内有效证据耗时的尾部分位 |
| `distribution.max_ms` | `item.max_ms` | 桶内最大有效证据耗时 |
| `distribution.client_p50_ms` | `item.client_p50_ms` | 同桶请求的 Client 总时延中位数对照 |
| `distribution.client_p90_ms` | `item.client_p90_ms` | 同桶请求的 Client 总时延 P90 对照 |
| `tail_ratio_p90_p50` | 证据 P90 / P50 | 描述该桶有效测量的长尾程度，**不是相对基线的放大倍数** |
| `note` | `item.note` | 桶构成与未细分边界说明 |
| `action` | `item.action` | 上游静态治理提示，只作调查方向，不当作现场结论 |
| `top_traces[]` | `item.top_traces[]`，最多 5 条 | 证据耗时极端请求的复核锚点 |
| `top_traces[].trace_id` | 同名上游字段，逐字保留 | 回查具体请求 |
| `top_traces[].evidence_ms` | 同名上游字段 | 该 trace 对应桶的证据耗时 |
| `top_traces[].client_ms` | 同名上游字段 | **同一请求**的 Client 总时延对照 |

分母为零或任一输入缺失时，相应比值为 `null`，计算保留最多 6 位小数。
`normal_cnt + anomalous_cnt = trace_cnt <= sample_cnt`。桶计数包含没有有效耗时的请求，
因此 **`trace_cnt` 不能标成分位数的有效测量数**；上游未提供该有效测量数，本版不伪造。
Client 与证据分位的有效集合可能不同，不相减得到“其它阶段耗时”。
即使 `truncated=false`，仍须保留异常 + top 慢正常选样的限制，不宣称总体无偏分布。

## 可选对照与时间序列

| 字段 | 来源 / 计算 | 作用 |
|---|---|---|
| `baseline` | 独立对照窗口 `/stats/stages` 中同 key 桶的上述完整核心特征 | 保留对照值、来源、计数和采样条件 |
| `baseline.delta_p90_ms` | 当前证据 P90 − 对照证据 P90，可为负数 | 量化增加或减少的证据耗时 |
| `baseline.p90_amplification` | 当前证据 P90 / 对照证据 P90，零分母为 null | 量化相对对照窗口的变化倍数 |
| `windows[]` | 各子窗口 `/stats/stages` 同 key 桶的完整核心特征 | 观察随时间的桶计数、P90、异常标记比例与采样情况 |
| `windows[].source.request.start_time/end_time` | 真实子窗口请求 | 给每个时间点明确统计边界 |

不自动产生“持续抬升/周期性/尖峰”等分类标签；这种判断需要明确规则及足够窗口，
可在已有 `detail/conclusion` 中结合证据解释，不能把推理当原始测量。

## 可选 Top trace 空间与错误特征

只按完全一致的 trace ID 合并 `/trace/list result.items[]`；不跨桶补齐，不以时间接近替代关联。

| 字段 | 来源 | 作用 |
|---|---|---|
| `top_traces[].is_anomalous` | 同 ID `TraceListItem.is_anomalous` | 复核该代表请求的异常标记 |
| `top_traces[].host` | 同 ID `TraceListItem.host` | 定位代表请求所属主机 |
| `top_traces[].pod_ips` | 同 ID `TraceListItem.pod_ips` | 保留涉及的 Pod IP 集合，**不是 Pod 名称** |
| `top_traces[].src_ip/dst_ip` | 同 ID 同名字段 | 定位代表请求端点和链路 |
| `top_traces[].failure_codes[].code/cnt` | 同 ID `TraceListItem.failure_codes` | 关联该请求的错误码与事件计数，不自动推断因果或超时 |
| `trace_source.endpoint/request/response_path` | `/trace/list`、真实请求、`result.items` | 复现拓扑/错误码补查 |
| `trace_coverage.requested_cnt` | 本桶 Top trace ID 去重数 | 本桶期望补查的代表请求数 |
| `trace_coverage.returned_cnt` | 响应中与本桶 Top trace ID 匹配的去重数 | 实际返回多少代表请求 |
| `trace_coverage.missing_trace_ids` | Top ID 集合减返回 ID 集合 | 显式揭示分页或数据缺失，不将未返回解释为健康 |

未补查时不生成以上可选字段；补查返回字段为 null 时原样保留。
`failure_codes=[]` 表示该响应没有关联错误码，缺省/null 表示未知。
Top trace 按证据耗时挑选，只适合列出空间线索；本版**不输出全量节点集中度或覆盖率**。

## 与旧字段和案例库的关系

- `p99/baseline/ratio/share/status/detail` 继续作为旧展示字段；新特征不自动覆盖它们。
  `/stats/stages` 没有 P99，不用 P90、max 或少量 Top trace 推算 P99。
  只有取得其它接口的真实阶段 P99 且注明对应样本口径时才填旧 `p99`，否则填 `"—"`。
- 没有上游的有效测量数、重传次数、阈值、真实超时率、子阶段测量就不增加这些字段。
  SET 仍不编造 CREATE/PUBLISH/URMA 细分；`set_no_evidence` 的 Client 总时延不是网络实测值。
- HTML 显示这些特征，报告侧车 JSON 原样保留。案例库的 `StageFeaturesModel` 目前仅支持
  桶 key、计数、P50/P90/max、口径和采样元信息；按已有 `REPORT_SCHEMA.md` 映射其支持字段，
  不把整个 `features` 直接提交并期待新增字段被持久化或参与打分。
  `latency_components` 仍只写桶 key，报告展示名和新派生比值不冒充检索信号。
