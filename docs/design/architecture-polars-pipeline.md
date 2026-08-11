# Polars 管线重写 — 架构设计图

本次优化把 latency 插件的聚合管线从"平铺 dict + 串行 numpy + shared_memory
桶统计"重写为 **worker 直产 polars 列 → concat → polars 归并 → polars 聚合**,
用 polars 天然并行替代 numpy 单线程。

## 设计图

![Polars 管线架构](figures/polars-pipeline-architecture.png)

> PyCharm / VSCode / Typora 等本地编辑器直接显示上图;
> gitcode / GitHub 网页端渲染下方的 Mermaid 源码。

<details>
<summary>📐 Mermaid 源码(可编辑, gitcode/GitHub 网页端自动渲染)</summary>

```mermaid
%%{init: {'theme': 'base', 'themeVariables': {
  'fontSize': '14px',
  'fontFamily': 'Inter, PingFang SC, Microsoft YaHei, sans-serif',
  'primaryColor': '#1f6feb',
  'primaryTextColor': '#ffffff',
  'primaryBorderColor': '#1f6feb',
  'lineColor': '#8b949e',
  'secondaryColor': '#f6f8fa',
  'tertiaryColor': '#e6edf3',
  'clusterBkg': '#ffffff',
  'clusterBorder': '#d0d7de',
  'edgeLabelBackground': '#ffffff'
}}}%%
flowchart TB
    subgraph L0["📁 日志输入 · data/logs"]
        DIR["日志目录<br/>4 文件 · 106 MB<br/>347,471 条 trace 记录"]
    end

    subgraph L1["① 多进程扫描 · ParallelFileScanner"]
        P1["Process 1<br/>SDK 日志解析"]
        P2["Process 2<br/>Worker 日志解析"]
        P3["Process 3 · 4<br/>INFO 日志解析"]
        COL["列式投影<br/>entries_to_columns<br/>31 列 + _label/_src_rank"]
    end

    subgraph L2["② df_trace · Polars 列式归并"]
        CONCAT["pl.concat(各 worker)"]
        GROUP["group_by(tid)<br/>merge: first() / src·dst=max_rank"]
        TRACE["df_trace<br/>每 trace 一行 · 31 列<br/>347,471 → 每 trace 一行"]
    end

    subgraph L3["③ 三路消费 · 一份数据三种视角"]
        AGG["聚合 _aggregate_polars<br/>src_dst / time_window<br/>66 ms"]
        BUCKET["桶统计<br/>compute_bucket_stats_from_frame<br/>4 档粒度 · 5 分位代表行"]
        DETAIL["明细物化<br/>_build_anomalous_detail_rows<br/>仅异常 trace"]
    end

    subgraph L4["④ 落库 · PostgreSQL"]
        T1["src_dst_aggregated_event<br/>2 行"]
        T2["time_window_aggregated<br/>1,210 行"]
        T3["latency_bucket_{10s,1min,10min,1h}<br/>12,100 行"]
        T4["log_parse_result<br/>异常明细"]
        T5["trace_failure_event<br/>75 行 · 诊断产物"]
    end

    subgraph L5["⑤ 展示 · Vue 前端 5173"]
        UI["时延监控 / 通断监控<br/>聚合曲线 · 故障 trace · 中文进度"]
    end

    DIR --> P1 & P2 & P3
    P1 & P2 & P3 --> COL
    COL --> CONCAT
    CONCAT --> GROUP --> TRACE
    TRACE --> AGG
    TRACE --> BUCKET
    TRACE --> DETAIL
    AGG --> T1 & T2
    BUCKET --> T3
    DETAIL --> T4
    T1 & T2 & T3 & T4 & T5 --> UI

    classDef local fill:#ddf4ff,stroke:#1f6feb,stroke-width:2px,color:#0d1117
    classDef polars fill:#fff8c5,stroke:#bf8700,stroke-width:2px,color:#0d1117
    classDef db fill:#dafbe1,stroke:#1a7f37,stroke-width:2px,color:#0d1117
    class TRACE,AGG,BUCKET polars
    class T1,T2,T3,T4,T5 db
    class P1,P2,P3,COL local
```

</details>

> 可编辑源文件: [`polars-pipeline-architecture.mmd`](figures/polars-pipeline-architecture.mmd)
> (纯 Mermaid, 供编辑器 / mermaid-cli 使用) / [`polars-pipeline-architecture.svg`](figures/polars-pipeline-architecture.svg)

## 各层说明

| 层 | 组件 | 数据结构 | 关键点 |
|----|------|----------|--------|
| **① 扫描** | `ParallelFileScanner` (多进程) | `{label: [entries]}` → 列式 dict | 每 entry 一行, 31 列 TRACE_COLUMNS + 2 内部列(_label/_src_rank), 稀疏+None 对齐 |
| **② df_trace** | `build_trace_frame` (polars) | `pl.DataFrame` 每 trace 一行 | `group_by(tid)` + merge spec: `first()` 取首个非空, src/dst 按 max_rank(URMA>RemotePull) |
| **③ 三路消费** | `_aggregate_polars` / `compute_bucket_stats_from_frame` / `_build_anomalous_detail_rows` | 3 类 dataclass + 代表行 | **一份 df_trace, 三种视角**; 聚合 66ms / 桶统计 4 档 / 明细仅异常 |
| **④ 落库** | PostgreSQL | 5 类表 | src_dst / time_window / latency_bucket_{4档} / log_parse_result / 诊断表 |
| **⑤ 展示** | Vue 前端 | JSON → ECharts | 聚合曲线 + 故障 trace + 中文进度 |

## 性能对比(347,471 traces)

| 阶段 | 旧 numpy | Polars |
|------|---------|--------|
| 聚合 | 131.9s | **66ms** (~2000x) |
| 总解析 | ~155s | **8s** |

## 设计原则

1. **列式贯穿**: 从 L1 列式 → L2 df_trace 全程 polars, 无 dict 中间层
2. **一份数据三种消费**: 聚合/桶统计/明细共用 df_trace, 字段一致性有 golden 保证
3. **mergr spec 可配**: `_MERGE_SPEC` 集中管理归并规则, 改一处即可调整
4. **冻结契约**: TRACE_COLUMNS 是 31 列冻结契约, parity 测试逐字段验证
