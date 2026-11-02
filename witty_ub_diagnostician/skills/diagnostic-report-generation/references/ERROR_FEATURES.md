# 通断故障：错误码构成与时间分布

`faults[].error` 与 `faults[].latency` 同级；扁平单故障支持顶层 `error`。
此块只描述错误码及其时间分布，不关联时延阶段，不改变根因确认程度。
旧报告缺省 / `null` / `{}` 时不显示；`simplified: true` 的次生故障不展开此块。

## 取数与提取

优先复用本次已保存的
`POST /log_failure_event_result/list_time_aggregated_failure_events` 请求与完整响应。
缺少时间分布时按本故障的范围补查；GET/SET 显式分开，指定完整的
`start_time/end_time`，粒度用 `second/minute/hour`，分页参数保持一致。
响应 `result.total` 为**有数据的原始桶数**，不是请求数或命中次数。

把真实请求/响应写成以下快照结构（下例为合成数据，仅示范接口格式）：

```json
{
  "series": [
    {
      "pages": [
        {
          "request": {
            "kb_id": "synthetic-kb",
            "operation": "GET",
            "start_time": "2026-10-26 12:00:00",
            "end_time": "2026-10-26 12:02:00",
            "interval": "minute",
            "sort_by": "timestamp",
            "sort_desc": false,
            "page_num": 1,
            "page_cnt": 100
          },
          "response": {
            "code": 200,
            "result": {
              "total": 1,
              "err_codes": ["all", "1004", "1009"],
              "events": [
                {
                  "start_time": "2026-10-26 12:00:00",
                  "end_time": "2026-10-26 12:01:00",
                  "status_code_cnt": {"all": 5, "1004": 3, "1009": 2}
                }
              ]
            }
          }
        }
      ]
    }
  ]
}
```

```bash
python3 scripts/error_features.py /tmp/error_snapshots.json /tmp/error.json
python3 scripts/render_report.py --spec error
# 可选 --top-n 1~10（默认 5），--max-windows 1~120（默认 48）
```

将输出整体填入对应故障的 `error`，再填写 `conclusion`。
可增加 `metrics[]`，形状与 latency 的指标卡一致：`{label,value,sub,tone}`。
提取器不联网、不选择根因、不生成诊断结论；失败退出 2，不覆盖已有输出。

每项 `series` 对应一种操作的同一查询范围；多页放在同一 `pages[]` 中，
不可把多个 Pod 的独立查询拼成分页。可用 `series[].codes` 指定本故障的原始错误码，
提取器在响应内筛选，并保留为 `code_filter`；不指定则取查询范围内的全部码。
同码同窗有多个独立故障时，还须通过故障域等现场条件区分，不能仅按码归属。

接口当前支持 `kb_id/operation/start_time/end_time/cluster_name/host/pod_ip/src_ip/dst_ip`；
**当前请求模型不支持 `log_id`**，不要照抄旧工具参考中的该参数。
无法限定到本故障时，不得把更大范围的统计冒充本故障统计；应说明范围限制或省略此块。

## 输出契约（每个 error 对象）

| 字段 | 含义与来源 |
|---|---|
| `metrics[]` | 可选展示指标；结论数据须来自本次分布，不填无分母的失败率 |
| `conclusion` | Agent 撰写：主导错误码、集中窗口、同时/先后变化及证据限制；相关性不等于因果 |
| `breakdowns[]` | GET、SET 各至多一套，不合并计数或比例 |
| `breakdowns[].operation` | 真实请求显式填写的 GET/SET |
| `scope` | 真实请求中的知识库、操作、时间与故障域过滤，不含分页/排序参数 |
| `code_filter` | 指定的原始错误码列表；未指定为 `null`；`all` 不是错误码 |
| `unit` | 固定 `trace_code_occurrence`，逐码命中次数 |
| `source.endpoint` | 固定 `/log_failure_event_result/list_time_aggregated_failure_events` |
| `source.pages[]` | 各页 `request` 原样保留；`response_path=result.events`，以及该页的 `total_windows/returned_windows` |
| `coverage.complete` | 唯一返回桶数等于 `result.total` 才为真；各页 total、查询范围与排序须一致 |
| `coverage.returned_windows/total_windows` | 返回/预期的有数据原始桶数，不等于展示窗数 |
| `code_distribution.total_count` | 取得的原始桶中，筛选后逐码命中次数之和；分页不全时为下界 |
| `code_distribution.items[]` | Top N `{code,count,share_pct}`，按 count 降序、原始码升序打破平局 |
| `items[].count` | 同一码在取得的原始桶中的计数之和；不是跨文件去重 trace 数 |
| `items[].share_pct` | `count / total_count × 100`，保留 6 位小数；仅分页完整且分母大于零时计算，否则 `null` |
| `code_distribution.other_count` | 筛选后非 Top N 错误码的命中次数；不将 Top N 重新归一化到 100% |
| `timeline.interval_seconds` | 展示窗的名义秒数，为原始粒度的整数倍 |
| `timeline.windows[]` | 连续覆盖整个请求范围，含 `start_time/end_time/complete/counts/other_count` |
| `windows[].counts` | `{原始码: 整数或 null}`，键与 Top N 列表一致 |
| `windows[].other_count` | 同一展示窗内非 Top N 的命中次数或 `null` |
| `windows[].complete` | 此展示窗是否已知完整；分页不全时也可能有个别已完整取得的窗 |

计数始终为非负整数，比例为数值或 `null`，不能用带单位的展示字符串替代。
`items[].count` 之和加 `other_count` 必须等于 `total_count`；
时间分布各列中非 null 计数之和也必须与对应构成计数相等。

## 时间与缺失口径

- 使用服务端事件时间（Asia/Shanghai，无偏移字符串）；查询范围为 `[start_time,end_time)`。
  原始桶由自然秒/分/时截断，首尾展示边界按请求范围截取，不对计数折算。
- 超过默认 48 个展示窗时，将相邻原始桶合并求和；不抽点、不平均、不跨操作合并。
  合并会改变峰值数值及定位精度，结论须按展示粒度表述；精确爆发时间回查原始响应。
- 分页完整：响应未出现的时间桶可填零，表示在该查询与模式识别口径下无命中。
- 分页不完整：未返回的时间桶未知，不能填零。合并窗若只取得部分原始桶，
  数值保留已取得计数作为下界，并置 `complete=false`；完全未取得则所有计数为 `null`。
  模板分别显示 `≥数值` 与 `—`（斜纹）；整体比例不展示。
- 空成功响应可形成全零分布，但不能单凭空结果认定系统健康，需结合解析完整性。
- 时间聚合接口要求 `failure_mode` 非空；结果仅覆盖已识别故障模式的记录。
  `/stats/error_codes` 不要求此过滤且采用每码 distinct trace 口径，不能拿它的计数替换本块计数。
- `all` 是逐码计数之和。同一 trace 携带多个码时会命中多列，
  **不得称为去重失败请求数、失败率或业务失败率**。
- 本版不从 `metrics/err_code` 裁剪后的时间点求整体计数，
  不使用 `/stats/stages.fail_cnt` 作为通断失败数，也不建立时延阶段关联。

## 展示

位置：故障结论 → 通断故障分布 → 时延阶段定位（mixed 时）→ 根因推理链。
每种操作展示错误码构成条形表、时间窗 × 错误码热力表、可折叠的来源。
相同错误码在同套构成表/时间表使用同色，所有时间单元格按共同最大计数着色，
单元格同时保留数字，打印时也能读取；无 JS 依赖。
