"""T2 (polars-pipeline-rewrite): 列式 worker 输出 → 每 trace 一行 df_trace。

从 T1 的列式投影（``worker_columnar``：``{column: [values]}``，键 = ALL_COLUMNS
= 31 个 TRACE_COLUMNS + ``_label``/``_src_rank`` 内部列）重建 df_trace：
``group_by("tid")`` 按列 merge spec 归并 → 推导 c2w_urma_latency → 丢弃
无 SDK/负时延/空 tid trace → src/dst 空串兜底。

同时内置 yuanrong 26 项分段时延计算（原 compute_yuanrong），RPC 字符串解析已
在 entries_to_columns() 中完成，此处仅做 polars 矩阵运算（group_by + 加减乘除）。

merge spec 逐列可配（dict column → op，见 ``_MERGE_SPEC``）：

- ``"first"``：``drop_nulls().first()`` —— 取该列首个非空行，精确复现参考
  实现（``_build_flat_trace_index`` + ``_resolve_snapshot``）的 ``entries[0]``
  语义。golden fixture 捕获自该参考，改 merge op 前必须重新验证 parity。
- ``"max_rank"``：按 ``_src_rank`` 最大优先取该 trace 的 src/dst —— 复现
  ``_extract_trace_metrics`` 的 URMA→RemotePull→"" 取源链（URMA=2 > RemotePull=1）。

列式行的行序 = 扫描产物 ``{label: [entries]}`` 的插入序（``entries_to_columns``
逐 label 逐 entry 投影），与参考按 label 顺序 append 的 ``entries[0]`` 一致，
因此 ``first()`` 归并结果逐字段对齐。c2w 在归并后推导（``total_ms -
worker_total_latency``，两值均来自 SDK/Worker 首行 ELAPSED_US/1000.0），与
``_resolve_snapshot`` 的 ``(sdk_elapsed - worker_elapsed) / 1000.0`` 在
fixture 粒度精确等价。
"""

from latency.parse.parallel_scanner.columnar import (
    ALL_COLUMNS,
    INTERNAL_COLUMNS,
    SDK_LABEL,
    TRACE_COLUMNS,
    WORKER_ACCESS_LABEL,
)
from latency.parse.worker_info_parser import (
    CLIENT_RPC_LABEL,
    MASTER_RPC_LABEL,
    QUERY_META_LABEL,
    REMOTE_WORKER_RPC_LABEL,
    URMA_LABEL,
)
from latency.schemas.log import YUANRONG_METRIC_FIELDS

# 归并后推导 / 永不填充的列（columnar 投影不写它们；w2w/create/publish 参考
# 实现固定 None，c2w 由 build_trace_frame 在归并后计算）
_STATIC_NULL_COLUMNS: tuple[str, ...] = (
    "w2w_urma_latency",
    "create_latency",
    "publish_latency",
)
_COMPUTED_OR_STATIC: frozenset[str] = frozenset(
    ("tid", "c2w_urma_latency", *_STATIC_NULL_COLUMNS)
)

# 列 merge spec：默认 first()；src/dst 例外用 max-rank 取源。
# 后续想把某列改为 max() 只需改这一处映射。
_MERGE_SPEC: dict[str, str] = {
    col: "first" for col in TRACE_COLUMNS if col not in _COMPUTED_OR_STATIC
}
_MERGE_SPEC["src"] = "max_rank"
_MERGE_SPEC["dst"] = "max_rank"

_SRC_RANK_COL: str = INTERNAL_COLUMNS[1]  # "_src_rank"

# ── yuanrong 标签常量（与 yuanrong_metrics.py / columnar.py 对齐）─────────
_YUANRONG_LABELS: frozenset[str] = frozenset({
    SDK_LABEL,
    WORKER_ACCESS_LABEL,
    URMA_LABEL,
    CLIENT_RPC_LABEL,
    MASTER_RPC_LABEL,
    REMOTE_WORKER_RPC_LABEL,
    QUERY_META_LABEL,
})
_YUANRONG_EXTRA_COLS: tuple[str, ...] = (
    "_elapsed_us", "_rpc_e2e_us", "_rpc_server_exec_us", "_rpc_network_us",
    "op", "inflight_count",
)


def _has_yuanrong_cols(worker_columnar: dict[str, list]) -> bool:
    return all(k in worker_columnar for k in _YUANRONG_EXTRA_COLS)


# ── yuanrong 纯 polars 实现 ─────────────────────────────────────────────

def _yuanrong_from_grouped(df_trace) -> "pl.DataFrame":
    """对已 per-trace 归并的 df_trace 追加 26 项 yuanrong 分段时延。

    要求 df_trace 已含 __se/__we/__ue/__ce/__me/__re 等原材料列
    （由外层 group_by("tid") 一次性产出）。
    """
    import polars as pl

    yr = df_trace

    # ── Phase 2a: derived flags ─────────────────────────────────────────
    yr = yr.with_columns([
        (pl.col("__cn") >= 2).alias("__isd"),
        pl.col("__sop").cast(pl.Utf8).str.contains("SET").fill_null(False).alias("__isset"),
        pl.col("__me").is_not_null().alias("__hm"),
        pl.col("__re").is_not_null().alias("__hr"),
    ])

    # Phase 2b: __swap needs __hm, __hr, __isset from 2a
    yr = yr.with_columns(
        (pl.col("__hm") & ~pl.col("__hr") & ~pl.col("__isset")
         & (pl.col("__qm") == 0)).alias("__swap"),
    )

    # ── Phase 3: list aggregates for client RPC + worker ────────────────
    yr = yr.with_columns([
        pl.col("__we").list.sum().alias("__wsum"),
        pl.col("__we").list.max().alias("__wmax"),
        pl.col("__ce").list.sum().alias("__ce2esum"),
    ])

    # ── Phase 4: derived 26 output columns ──────────────────────────────
    _ce0 = pl.col("__ce").list.first()
    _ce1 = pl.col("__ce").list.tail(1).list.first()
    _cs0 = pl.col("__cs").list.first()
    _cs1 = pl.col("__cs").list.tail(1).list.first()
    _cnw0 = pl.col("__cnw").list.first()
    _cnw1 = pl.col("__cnw").list.tail(1).list.first()
    _ct_0 = (_ce0 - _cs0).clip(0)
    _ct_1 = (_ce1 - _cs1).clip(0)
    _cf_0 = (_ct_0 - _cnw0).clip(0)
    _cf_1 = (_ct_1 - _cnw1).clip(0)
    _mt = (pl.when(pl.col("__swap")).then(pl.col("__re")).otherwise(pl.col("__me"))
           - pl.when(pl.col("__swap")).then(pl.col("__rs")).otherwise(pl.col("__ms"))).clip(0)
    _mf = (_mt - pl.when(pl.col("__swap")).then(pl.col("__rn")).otherwise(pl.col("__mn"))).clip(0)
    _rt = (pl.when(pl.col("__swap")).then(pl.col("__me")).otherwise(pl.col("__re"))
           - pl.when(pl.col("__swap")).then(pl.col("__ms")).otherwise(pl.col("__rs"))).clip(0)
    _rf = (_rt - pl.when(pl.col("__swap")).then(pl.col("__mn")).otherwise(pl.col("__rn"))).clip(0)

    _m_e2e = pl.when(pl.col("__swap")).then(pl.col("__re")).otherwise(pl.col("__me"))
    _m_se = pl.when(pl.col("__swap")).then(pl.col("__rs")).otherwise(pl.col("__ms"))
    _m_nw = pl.when(pl.col("__swap")).then(pl.col("__rn")).otherwise(pl.col("__mn"))
    _r_e2e = pl.when(pl.col("__swap")).then(pl.col("__me")).otherwise(pl.col("__re"))
    _r_se = pl.when(pl.col("__swap")).then(pl.col("__rs")).otherwise(pl.col("__ms"))
    _r_nw = pl.when(pl.col("__swap")).then(pl.col("__mn")).otherwise(pl.col("__rn"))

    _remote_proc = pl.when(pl.col("__isd")).then(_cs1).otherwise(_r_se)

    yr = yr.with_columns([
        pl.col("__se").alias("total_latency_us"),

        pl.when(pl.col("__isd"))
          .then(pl.lit("remote"))
          .when((pl.col("__hm") | pl.col("__hr")))
          .then(pl.lit("local"))
          .otherwise(pl.lit("unknown"))
          .alias("request_mode"),

        pl.when(
            (pl.col("__cn") > 0) & (pl.col("__ce2esum") > 0)
        ).then(
            (pl.col("__se") - pl.col("__ce2esum")).clip(0)
        ).when(
            pl.col("__we").list.len() > 0
        ).then(
            (pl.col("__se") - pl.col("__wsum")).clip(0)
        ).otherwise(
            pl.col("__se")
        ).alias("sdk_processing_us"),

        pl.when(pl.col("__isd"))
          .then(_cs0)
          .otherwise(_m_se)
          .alias("master_processing_us"),

        pl.col("__wmax").alias("worker_access_latency_us"),

        pl.when(pl.col("__isset"))
          .then((_remote_proc - pl.col("__ue").list.max()).clip(0))
          .otherwise(_remote_proc)
          .alias("remote_worker_internal_us"),

        pl.when(~pl.col("__isd") & (pl.col("__we").list.len() > 0))
          .then((pl.col("__wsum") - _m_e2e.fill_null(0) - _r_e2e.fill_null(0)).clip(0))
          .alias("local_worker_internal_us"),

        pl.when(~pl.col("__isd")).then(_cnw0).alias("sdk_rpc_network_us"),
        pl.when(~pl.col("__isd")).then(_ct_0).alias("sdk_rpc_total_us"),
        pl.when(~pl.col("__isd")).then(_cf_0).alias("sdk_rpc_framework_us"),

        pl.when(~pl.col("__isd")).then(_m_nw).alias("master_rpc_network_us"),
        pl.when(~pl.col("__isd")).then(_mf).alias("master_rpc_framework_us"),
        pl.when(~pl.col("__isd")).then(_mt).alias("master_rpc_total_us"),

        pl.when(~pl.col("__isd")).then(_r_nw).alias("remote_worker_rpc_network_us"),
        pl.when(~pl.col("__isd")).then(_rf).alias("remote_worker_rpc_framework_us"),
        pl.when(~pl.col("__isd")).then(_rt).alias("remote_worker_rpc_total_us"),

        pl.when(pl.col("__isd")).then(_cnw0).alias("client_master_rpc_network_us"),
        pl.when(pl.col("__isd")).then(_cf_0).alias("client_master_rpc_framework_us"),
        pl.when(pl.col("__isd")).then(_ct_0).alias("client_master_rpc_total_us"),

        pl.when(pl.col("__isd")).then(_cnw1).alias("client_remote_rpc_network_us"),
        pl.when(pl.col("__isd")).then(_cf_1).alias("client_remote_rpc_framework_us"),
        pl.when(pl.col("__isd")).then(_ct_1).alias("client_remote_rpc_total_us"),

        pl.when(pl.col("__isset"))
          .then(pl.lit(None, dtype=pl.Float64))
          .otherwise(pl.col("__ue").list.max())
          .alias("urma_processing_us"),

        pl.when(pl.col("__isset"))
          .then(pl.lit(None, dtype=pl.Float64))
          .otherwise(pl.col("__ui").list.max())
          .alias("urma_inflight_max"),

        _remote_proc.alias("remote_worker_processing_us"),
    ])

    # Phase 4b: depends on Phase 4a output
    yr = yr.with_columns(
        pl.when(
            (pl.col("__isd").not_())
            & (pl.col("__hm") | pl.col("__hr"))
        ).then(pl.col("local_worker_internal_us"))
          .alias("local_worker_internal_active_us"),
    )

    # Drop internal columns
    _yr_internals = [c for c in yr.columns if c.startswith("__")]
    return yr.drop(_yr_internals)


# ── 主入口 ─────────────────────────────────────────────────────────────

def build_trace_frame(worker_columnar: dict[str, list]):
    """列式 worker 输出 → 每 trace 一行 df_trace（TRACE_COLUMNS + YUANRONG）。

    参数:
        worker_columnar: 所有 worker 行的列式投影（键 = ALL_COLUMNS 及
            内部列 _elapsed_us/_rpc_e2e_us 等）。

    返回:
        polars DataFrame：每 trace 一行，列 = TRACE_COLUMNS（31）+ 若存在
        yuanrong 内部列则追加 YUANRONG_METRIC_FIELDS（26）。
    """
    import polars as pl

    frame = pl.DataFrame({name: worker_columnar[name] for name in ALL_COLUMNS})

    do_yuanrong = _has_yuanrong_cols(worker_columnar)

    # ── 构建 agg_exprs：TRACE_COLUMNS 归并 + 若需要则 yuanrong 原材料 ──
    agg_exprs: dict[str, pl.Expr] = {}
    for col, op in _MERGE_SPEC.items():
        if op == "max_rank":
            agg_exprs[col] = (
                pl.col(col)
                .filter(pl.col(_SRC_RANK_COL) == pl.col(_SRC_RANK_COL).max())
                .first()
            )
        else:
            agg_exprs[col] = pl.col(col).drop_nulls().first()

    if do_yuanrong:
        yr_data = {k: worker_columnar[k] for k in _YUANRONG_EXTRA_COLS}
        frame = frame.with_columns(
            **{k: pl.Series(name=k, values=v, dtype=pl.Float64)
               if k.endswith("_us") or k == "inflight_count"
               else pl.Series(name=k, values=v)
               for k, v in yr_data.items()}
        )
        agg_exprs.update({
            "__se": pl.col("_elapsed_us").filter(pl.col("_label") == SDK_LABEL).first(),
            "__sop": pl.col("op").filter(pl.col("_label") == SDK_LABEL).first(),
            "__we": pl.col("_elapsed_us").filter(pl.col("_label") == WORKER_ACCESS_LABEL).implode(),
            "__ue": pl.col("_elapsed_us").filter(pl.col("_label") == URMA_LABEL).implode(),
            "__ui": pl.col("inflight_count").filter(pl.col("_label") == URMA_LABEL).implode(),
            "__cn": pl.col("_label").filter(pl.col("_label") == CLIENT_RPC_LABEL).count(),
            "__ce": pl.col("_rpc_e2e_us").filter(pl.col("_label") == CLIENT_RPC_LABEL).implode(),
            "__cs": pl.col("_rpc_server_exec_us").filter(pl.col("_label") == CLIENT_RPC_LABEL).implode(),
            "__cnw": pl.col("_rpc_network_us").filter(pl.col("_label") == CLIENT_RPC_LABEL).implode(),
            "__me": pl.col("_rpc_e2e_us").filter(pl.col("_label") == MASTER_RPC_LABEL).first(),
            "__ms": pl.col("_rpc_server_exec_us").filter(pl.col("_label") == MASTER_RPC_LABEL).first(),
            "__mn": pl.col("_rpc_network_us").filter(pl.col("_label") == MASTER_RPC_LABEL).first(),
            "__re": pl.col("_rpc_e2e_us").filter(pl.col("_label") == REMOTE_WORKER_RPC_LABEL).first(),
            "__rs": pl.col("_rpc_server_exec_us").filter(pl.col("_label") == REMOTE_WORKER_RPC_LABEL).first(),
            "__rn": pl.col("_rpc_network_us").filter(pl.col("_label") == REMOTE_WORKER_RPC_LABEL).first(),
            "__qm": pl.col("_label").filter(pl.col("_label") == QUERY_META_LABEL).count(),
        })

    df_trace = frame.group_by("tid").agg(**agg_exprs)

    # w2w/create/publish 固定 None；c2w 归并后推导
    df_trace = df_trace.with_columns(
        *[pl.lit(None, dtype=pl.Float64).alias(col) for col in _STATIC_NULL_COLUMNS],
        pl.when(
            pl.col("total_ms").is_not_null()
            & pl.col("worker_total_latency").is_not_null()
        )
        .then(pl.col("total_ms") - pl.col("worker_total_latency"))
        .otherwise(None)
        .alias("c2w_urma_latency"),
    )

    # _yuanrong_from_grouped deferred to run() — computed only on
    # top1000 + anomalous subset (~1k rows), not all 347k traces.
    # Internal __ columns preserved in output for the deferred call.

    df_trace = df_trace.filter(
        pl.col("tid").is_not_null()
        & (pl.col("tid") != "")
        & pl.col("total_ms").is_not_null()
        & (pl.col("total_ms") >= 0)
    )

    df_trace = df_trace.with_columns(
        pl.col("src").fill_null(""),
        pl.col("dst").fill_null(""),
    )

    out_cols = list(TRACE_COLUMNS)
    if do_yuanrong:
        internals = [c for c in df_trace.columns if c.startswith("__")]
        out_cols.extend(internals)
    return df_trace.select(out_cols)
