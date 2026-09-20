"""T2 (polars-pipeline-rewrite): 列式 worker 输出 → 每 trace 一行 df_trace。

从 T1 的列式投影（``worker_columnar``：``{column: [values]}``，键 = ALL_COLUMNS
= 33 个 TRACE_COLUMNS + ``_label``/``_src_rank`` 内部列）重建 df_trace：
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

import os

from latency.parse.columns import LIGHT_COLUMNS  # P2 轻列契约：全量只算这 11 列
from latency.parse.parallel_scanner.columnar import (
    ALL_COLUMNS,
    INTERNAL_COLUMNS,
    SDK_LABEL,
    TRACE_COLUMNS,
    WORKER_ACCESS_LABEL,
)
from latency.parse.labels import (
    CLIENT_RPC_LABEL,
    MASTER_RPC_LABEL,
    QUERY_META_LABEL,
    REMOTE_WORKER_RPC_LABEL,
    URMA_LABEL,
)  # P1 契约层：label 常量取自 labels.py，不再依赖老解析器实现

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
# operation 字段：优先从 SDK 提取，如果没有则从 Worker access 提取
# 这样即使只有 Worker 日志（没有 SDK 日志），operation 字段也能正确填充
_MERGE_SPEC["op"] = "first"
_MERGE_SPEC["operation"] = "first"
_MERGE_SPEC["op_key"] = "first"
# pod_ip 和 cluster_name：使用 implode 策略收集所有涉及的 pod_ip 和 cluster_name
# 参考通断故障的做法，确保所有相关 pod 和集群都被记录
# timestamp：显式定义成"请求发起方（SDK access）的时间戳"，无 SDK 行时退回 Worker access。
# 实测同一 tid 只有这两个候选（Worker 恒早 ~0.17ms），不定义就会随行序在两者间漂移。
_MERGE_SPEC["timestamp"] = "sdk_then_worker"
_MERGE_SPEC["pod_ip"] = "implode_unique"
_MERGE_SPEC["cluster_name"] = "implode_unique"

_SRC_RANK_COL: str = INTERNAL_COLUMNS[1]  # "_src_rank"

# ── 确定性开关（WITTY_UB_DETERMINISTIC，默认开启）────────────────────────
# 打开后同时修两处"同一份数据重跑结果会变"的既有不确定：
#   1. df_trace 行序固定为 tid 升序。polars 的 group_by / join 输出行序不稳
#      ——同一份 columns 连算两次 tid 行序就不同；而下游
#      compute_bucket_stats_from_frame 用 rank("ordinal") 选分桶代表行
#      （并列断结靠行序）、明细/聚合按 frame 行序落库，行序一变前端看到的
#      内容就跟着变（实测同一份数据两次运行：10s/60s/600s/3600s 四档分桶表
#      代表行各有 4/3/2/1 行不同）。
#   2. 明细子集（``__`` 原材料列）的选择用
#      ``sort(total_latency desc, tid asc).head(k)`` 取代 ``DataFrame.top_k``：
#      top_k 在并列处按内部实现断结（既不等于 tid 升序也不等于 tid 降序），
#      第 1000 名 ``total_latency`` 并列时两次运行会选到不同的 trace
#      （实测 ``__`` 列 1~2 条 trace 不同）。实现上不整帧排序：见
#      ``_tie_exact_top_k_tids``（top_k 定阈值 + 并列按 tid 升序补齐）。
# 默认 **开启**（数据一致性优先，用户定稿）；显式设 0 时 == 保持改动前的行为
# （与改动前逐列逐值一致）。
DETERMINISTIC_ENV: str = "WITTY_UB_DETERMINISTIC"
_FALSY_VALUES: frozenset[str] = frozenset(("0", "false", "no", "off"))


def deterministic_enabled() -> bool:
    """读 ``WITTY_UB_DETERMINISTIC``（每次调用现读，便于进程内 A/B 与回退）。

    默认开启：df_trace 行序固定 tid 升序、明细子集用稳定排序断结（同一份数据
    重跑结果一致）。显式设 ``0`` / ``false`` / ``no`` / ``off`` 回退改动前行为。
    """
    return (
        os.environ.get(DETERMINISTIC_ENV, "1").strip().lower() not in _FALSY_VALUES
    )


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

    要求 df_trace 已含 __se/__wsum/__umax/__ce0/__me/__re 等原材料列
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
    # 扫描归并时已将后续计算所需信息压成标量，不再保留可变长 List 列。

    # ── Phase 4: derived 26 output columns ──────────────────────────────
    _ce0, _ce1 = pl.col("__ce0"), pl.col("__ce1")
    _cs0, _cs1 = pl.col("__cs0"), pl.col("__cs1")
    _cnw0, _cnw1 = pl.col("__cnw0"), pl.col("__cnw1")
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
        pl.when(pl.col("__se").is_not_null())
        .then(pl.col("__se"))
        .otherwise(pl.col("total_latency") * 1000.0)
        .alias("total_latency_us"),

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
            pl.col("__wn") > 0
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
          .then((_remote_proc - pl.col("__umax")).clip(0))
          .otherwise(_remote_proc)
          .alias("remote_worker_internal_us"),

        pl.when(~pl.col("__isd") & (pl.col("__wn") > 0))
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
          .otherwise(pl.col("__umax"))
          .alias("urma_processing_us"),

        pl.when(pl.col("__isset"))
          .then(pl.lit(None, dtype=pl.Float64))
          .otherwise(pl.col("__uimax"))
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

def _base_agg_exprs(
    columns: "frozenset[str] | set[str] | None" = None,
    *,
    nullable_rank: bool = False,
) -> dict[str, "pl.Expr"]:
    """构建 TRACE_COLUMNS 归并 agg 表达式（精确复现参考实现 entries[0] 语义）。

    与旧版 build_trace_frame 的 _MERGE_SPEC 循环一致；抽出共享，供
    build_trace_frame / build_trace_frame_light / detail_tids 推导使用，
    避免双实现漂移。

    Args:
        columns: 只构建这些列的表达式（None = _MERGE_SPEC 全量）。轻列路径传
            ``LIGHT_COLUMNS`` —— 表达式由**同一段代码**产出，轻列与全宽路径
            不存在第二套归并实现。
    """
    import polars as pl

    agg_exprs: dict[str, pl.Expr] = {}
    for col, op in _MERGE_SPEC.items():
        if columns is not None and col not in columns:
            continue
        if op == "max_rank":
            # Rank is non-null for scanner rows. arg_max selects the first
            # maximum (including ties) without allocating/sorting each group.
            agg_exprs[col] = (
                pl.col(col).sort_by(pl.col(_SRC_RANK_COL), descending=True).first()
                if nullable_rank else
                pl.col(col).get(pl.col(_SRC_RANK_COL).arg_max())
            )
        elif op == "sdk_first":
            agg_exprs[col] = (
                pl.col(col)
                .filter(pl.col("_label") == SDK_LABEL)
                .first(ignore_nulls=True)
            )
        elif op == "sdk_then_worker":
            # 取**请求发起方**（SDK access）的值；没有 SDK 行（纯 worker 日志）时退回
            # Worker access —— 与 total_latency 的"只有SDK/只有Worker/都有"三种场景同源。
            # 这样该列与输入行序无关（原先 first() 会在 SDK/Worker 两条候选里随行序挑）。
            agg_exprs[col] = pl.coalesce([
                pl.col(col)
                .filter(pl.col("_label") == SDK_LABEL)
                .first(ignore_nulls=True),
                pl.col(col)
                .filter(pl.col("_label") == WORKER_ACCESS_LABEL)
                .first(ignore_nulls=True),
            ])
        elif op == "implode_unique":
            # 收集所有非空且非重复的值到列表（用于 pod_ip / cluster_name）。
            # 末尾 sort：列表**内容**与行序无关，再让**顺序**也与行序无关
            # （否则前端看到的多 pod 列表顺序会随物理行序漂移）。
            agg_exprs[col] = pl.col(col).drop_nulls().unique().sort().implode()
        else:
            agg_exprs[col] = pl.col(col).first(ignore_nulls=True)
    return agg_exprs


def _yuanrong_agg_exprs() -> dict[str, "pl.Expr"]:
    """构建 yuanrong 紧凑原材料（``__`` 前缀）agg 表达式。

    这些列只供 _yuanrong_from_grouped 消费（run() 对 subset 延后计算）。
    """
    import polars as pl

    return {
        "__se": pl.col("_elapsed_us").filter(pl.col("_label") == SDK_LABEL).first(),
        "__sop": pl.col("op").filter(pl.col("_label") == SDK_LABEL).first(),
        # Use the original list reduction order for bit-for-bit floating-point
        # parity, but retain only its scalar result between pipeline stages.
        "__wsum": pl.col("_elapsed_us").filter(pl.col("_label") == WORKER_ACCESS_LABEL).implode().list.sum(),
        "__wmax": pl.col("_elapsed_us").filter(pl.col("_label") == WORKER_ACCESS_LABEL).max(),
        "__wn": pl.col("_label").filter(pl.col("_label") == WORKER_ACCESS_LABEL).len(),
        "__umax": pl.col("_elapsed_us").filter(pl.col("_label") == URMA_LABEL).max(),
        "__uimax": pl.col("inflight_count").filter(pl.col("_label") == URMA_LABEL).max(),
        "__cn": pl.col("_label").filter(pl.col("_label") == CLIENT_RPC_LABEL).count(),
        "__ce0": pl.col("_rpc_e2e_us").filter(pl.col("_label") == CLIENT_RPC_LABEL).first(),
        "__ce1": pl.col("_rpc_e2e_us").filter(pl.col("_label") == CLIENT_RPC_LABEL).last(),
        "__ce2esum": pl.col("_rpc_e2e_us").filter(pl.col("_label") == CLIENT_RPC_LABEL).implode().list.sum(),
        "__cs0": pl.col("_rpc_server_exec_us").filter(pl.col("_label") == CLIENT_RPC_LABEL).first(),
        "__cs1": pl.col("_rpc_server_exec_us").filter(pl.col("_label") == CLIENT_RPC_LABEL).last(),
        "__cnw0": pl.col("_rpc_network_us").filter(pl.col("_label") == CLIENT_RPC_LABEL).first(),
        "__cnw1": pl.col("_rpc_network_us").filter(pl.col("_label") == CLIENT_RPC_LABEL).last(),
        "__me": pl.col("_rpc_e2e_us").filter(pl.col("_label") == MASTER_RPC_LABEL).first(),
        "__ms": pl.col("_rpc_server_exec_us").filter(pl.col("_label") == MASTER_RPC_LABEL).first(),
        "__mn": pl.col("_rpc_network_us").filter(pl.col("_label") == MASTER_RPC_LABEL).first(),
        "__re": pl.col("_rpc_e2e_us").filter(pl.col("_label") == REMOTE_WORKER_RPC_LABEL).first(),
        "__rs": pl.col("_rpc_server_exec_us").filter(pl.col("_label") == REMOTE_WORKER_RPC_LABEL).first(),
        "__rn": pl.col("_rpc_network_us").filter(pl.col("_label") == REMOTE_WORKER_RPC_LABEL).first(),
        "__qm": pl.col("_label").filter(pl.col("_label") == QUERY_META_LABEL).count(),
    }


def _tie_exact_top_k_tids(df_trace, top_k: int) -> set:
    """``sort(total_latency desc, tid asc).head(top_k)`` 的 tid 集合，但不整帧排序。

    整帧排序在 247 万行实测 best 1.06s（三轮 1.060 / 2.206 / 2.005）。这里用
    ``top_k`` 只定「第 k 名的 total_latency 阈值」—— 选择算法取到的 k 个值里最小的
    一定是第 k 大的值，与并列处取到哪一条无关 —— 再取严格大于阈值的全部行、在该
    阈值上按 tid 升序补足到 k 条，正是整帧排序后取前 k 条的结果。total_latency
    为 null 的行与整帧排序路径一样被排除。并列 / 全并列 / 不足 k 条 / 含 null 的
    逐值比对见 ``test/test_trace_frame_topk_ties.py``。
    """
    import polars as pl

    if top_k <= 0:
        return set()
    nn = df_trace.select("tid", "total_latency").filter(
        pl.col("total_latency").is_not_null()
    )
    if nn.height <= top_k:
        return set(nn["tid"].to_list())
    thr = nn.top_k(k=top_k, by="total_latency")["total_latency"].min()
    strict = nn.filter(pl.col("total_latency") > thr)
    tids = set(strict["tid"].to_list())
    need = top_k - strict.height
    if need > 0:
        # 第 k 名并列：按 tid 升序补足（与 sort(total_latency desc, tid asc) 同序）
        ties = nn.filter(pl.col("total_latency") == thr).sort("tid").head(need)
        tids |= set(ties["tid"].to_list())
    return tids


def detail_tids_from(
    df_trace,
    threshold_ms: float,
    top_k: int = 1000,
    det: bool | None = None,
    *,
    as_series: bool = False,
) -> "set[str] | pl.Series":
    """明细子集 tid（= 时延异常 ∪ total_latency top_k）。

    口径与 :func:`build_trace_frame` 内部推导**同一份代码**（从那里搬出来，
    不是重写）：异常 = ``total_ms >= threshold_ms``；top_k 在确定性模式下用
    ``sort(total_latency desc, tid asc)`` 稳定断结（``_tie_exact_top_k_tids``），
    再与 ``DataFrame.top_k`` 取并集。轻列路径先用它定子集，再去补算宽列。
    """
    import polars as pl

    # Keep large anomaly sets columnar in the production path.
    if det is None:
        det = deterministic_enabled()
    anomalies = df_trace.select("tid", "total_ms").filter(
        pl.col("total_ms") >= threshold_ms
    )["tid"]
    ranked = df_trace.select("tid", "total_latency")
    tids = set()
    if det:
        # WITTY_UB_DETERMINISTIC=1：sort(total_latency desc, tid asc).head(k)
        # 稳定断结（DataFrame.top_k 在并列处按内部实现取，不可复现）。
        # 实现不整帧排序（247 万行 best 1.06s → 0.047s），见 _tie_exact_top_k_tids。
        tids |= _tie_exact_top_k_tids(df_trace, top_k)
        # 现状不变式：worker 侧 top1000 仍走 top_k，它选出的每条明细 trace
        # 都必须带 __ 列。故取两条规则的并集（行序固定后 top_k 本身也是
        # 确定的，不破坏可复现性），最多多算 1 条 trace。
        try:
            tids |= set(
                ranked.top_k(k=top_k, by="total_latency")["tid"].to_list()
            )
        except Exception:
            pass
    else:
        try:
            tids |= set(
                ranked.top_k(k=top_k, by="total_latency")["tid"].to_list()
            )
        except Exception:
            pass
    if as_series:
        return pl.concat([anomalies, pl.Series("tid", list(tids), dtype=pl.String)]).unique()
    return tids | set(anomalies.to_list())


def build_trace_frame(
    worker_columnar: dict[str, list],
    threshold_ms: float | None = None,
    top_k: int = 1000,
    detail_tids: set[str] | None = None,
):
    """列式 worker 输出 → 每 trace 一行 df_trace（TRACE_COLUMNS + ``__`` 原材料）。

    参数:
        worker_columnar: 所有 worker 行的列式投影（键 = ALL_COLUMNS 及
            内部列 _elapsed_us/_rpc_e2e_us 等）。
        threshold_ms: 时延异常阈值。为 None 时对**全部** trace 计算 yuanrong
            原材料列（测试/通用路径，保持旧契约）；提供时仅对
            ``top_k ∪ 时延异常`` 子集计算（``__`` 列对非子集为 null），
            显著降低对全量 trace 的 implode/first 聚合开销 —— 普通 trace
            只取总时延（p99/p9999 折线图），仅异常/明细 trace 才带分段时延。
        detail_tids: 显式指定"要算 ``__`` 原材料"的 trace 集合（轻列/宽列分离
            路径用：它把明细子集与分桶代表行一起传进来）。为 None 时按
            :func:`detail_tids_from` 就地推导（与旧行为一致）。

    环境变量 ``WITTY_UB_DETERMINISTIC``（默认开启）：df_trace 行序固定 tid
    升序，且明细子集改用 ``sort(total_latency desc, tid asc).head(k)``
    （见 ``deterministic_enabled``）。显式设 0 时与改动前逐列逐值一致。

    返回:
        polars DataFrame：每 trace 一行，列 = TRACE_COLUMNS（33）+ ``__``
        原材料内部列（供 run() 调用 _yuanrong_from_grouped 延后计算）。
    """
    import polars as pl

    # 单进程列运算路径直接传 DataFrame 进来：省掉 to_list() + 重建 DataFrame 的往返
    # （实测节点 217 / 207 万行：to_list 单项就 1.83s）。
    prebuilt = isinstance(worker_columnar, pl.DataFrame)
    if prebuilt:
        frame = worker_columnar
        det = deterministic_enabled()
        do_yuanrong = all(k in frame.columns for k in _YUANRONG_EXTRA_COLS)
    else:
        frame = pl.DataFrame({name: worker_columnar[name] for name in ALL_COLUMNS})
        det = deterministic_enabled()
        do_yuanrong = _has_yuanrong_cols(worker_columnar)

    if do_yuanrong and not prebuilt:
        yr_data = {k: worker_columnar[k] for k in _YUANRONG_EXTRA_COLS}
        frame = frame.with_columns(
            **{k: pl.Series(name=k, values=v, dtype=pl.Float64)
               if k.endswith("_us") or k == "inflight_count"
               else pl.Series(name=k, values=v)
               for k, v in yr_data.items()}
        )

        # 基础归并：TRACE_COLUMNS（总时延等聚合标量，用于 p99/p9999 折线图、
    # src_dst / time_window 聚合、分位桶统计）。仅在 无阈值(测试/全量) 时
    # 一并聚合 yuanrong 原材料列（单段 group_by，与旧实现等价、零倒退）。
    # Scanner ranks are non-null. Generic callers may supply null ranks;
    # preserve the original null-first ordering for those inputs.
    base_exprs = _base_agg_exprs(nullable_rank=bool(frame[_SRC_RANK_COL].null_count()))
    if do_yuanrong and threshold_ms is None:
        df_trace = frame.group_by("tid", maintain_order=det).agg(
            **{**base_exprs, **_yuanrong_agg_exprs()}
        )
    else:
        df_trace = frame.group_by("tid", maintain_order=det).agg(**base_exprs)

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

    # Fallback: when SDK access data is missing (total_ms is null), use
    # worker_total_latency so traces can still be built from worker-only logs.
    df_trace = df_trace.with_columns(
        pl.when(pl.col("total_ms").is_null())
        .then(pl.col("worker_total_latency"))
        .otherwise(pl.col("total_ms"))
        .alias("total_ms"),
        pl.when(pl.col("total_latency").is_null())
        .then(pl.col("worker_total_latency"))
        .otherwise(pl.col("total_latency"))
        .alias("total_latency"),
    )

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

    # yuanrong 原材料列（__）：仅对明细子集计算（提供阈值时），否则已在单段聚合中。
    if do_yuanrong and threshold_ms is not None:
        yr_exprs = _yuanrong_agg_exprs()
        # 显式给了集合就用它（轻列/宽列分离路径：明细子集 ∪ 分桶代表行）；
        # 否则就地推导（口径见 detail_tids_from，与本文件旧实现逐字一致）。
        if detail_tids is None:
            detail_tids = detail_tids_from(
                df_trace, threshold_ms, top_k=top_k, det=det, as_series=True
            )
        elif not isinstance(detail_tids, pl.Series):
            detail_tids = pl.Series("tid", list(detail_tids), dtype=pl.String)
        # 空子集时 filter 得空 frame，group_by 后仍保留 __ 列（全 null），
        # join how="left" 使非明细 trace 的 __ 列为 null，契约列数不变。
        detail_frame = (
            frame.filter(pl.col("tid").is_in(detail_tids.implode()))
            .group_by("tid", maintain_order=det)
            .agg(**yr_exprs)
        )
        df_trace = df_trace.join(detail_frame, on="tid", how="left", coalesce=True)

    out_cols = list(TRACE_COLUMNS)
    if do_yuanrong:
        internals = [c for c in df_trace.columns if c.startswith("__")]
        out_cols.extend(internals)
    out = df_trace.select(out_cols)
    if det:
        # WITTY_UB_DETERMINISTIC=1：行序固定 tid 升序。polars 的
        # group_by / join 输出行序不稳定，而下游分桶代表行
        # （rank("ordinal") 并列断结）与明细/聚合落库都吃 frame 行序。
        out = out.sort("tid")
    return out


# ── P2 轻列路径（扫描瘦身：全量只算 11 列）────────────────────────────────
# 全量行只保留 LIGHT_COLUMNS（见 parse/columns.py），宽列只对"明细子集 ∪
# 分桶代表行"计算。轻列路径产出两个东西：
#   1. ``build_trace_frame_light``：每 trace 一行、只含轻列列式输出的 df_trace；
#   2. ``bucket_representative_tids``：在轻列 df_trace 上选出的分桶代表行 tid 集合
#      （宽列子集 = 明细子集 ∪ 这个集合，故这里必须先算出来）。
# 两条路径的口径必须与全宽路径**逐步一致**，否则桶表/聚合结果会漂移。

# 轻列 df_trace 的输出列（与 build_trace_frame 的 TRACE_COLUMNS 子集逐列同名同序）。
_LIGHT_TRACE_COLUMNS: tuple[str, ...] = (
    "tid",
    "total_ms",
    "total_latency",
    "src",
    "dst",
    "op_key",
    "operation",
    "bucket_epoch",
    "log_id",
)

# 与 bucket/statistics.py PERCENTILE_MODES 同源的本地副本：仅在分层 import
# 不可用时兜底（见 _percentile_modes），正常路径读 statistics 的真值。
_PERCENTILE_MODES_FALLBACK: tuple[tuple[str, float], ...] = (
    ("median", 0.5),
    ("p99", 0.99),
    ("p9999", 0.9999),
    ("pmax", 1.0),
)


def _percentile_modes() -> tuple[tuple[str, float], ...]:
    """(模式名, 分位点) —— 直接取 ``latency/bucket/statistics.py:94-99`` 的
    ``PERCENTILE_MODES``（惰性 import：parse 层不在模块导入期拉起 bucket 层）。
    """
    try:
        from latency.bucket.statistics import PERCENTILE_MODES

        return tuple(PERCENTILE_MODES)
    except Exception:  # pragma: no cover - 分层/依赖不可用时兜底
        return _PERCENTILE_MODES_FALLBACK


def build_trace_frame_light(frame) -> "pl.DataFrame":
    """轻列行帧 → 每 trace 一行，列 = ``_LIGHT_TRACE_COLUMNS``（9 列）。

    口径与 ``build_trace_frame`` 逐步一致（同一条代码路径，不是第二套实现）：

    1. 分组键 ``tid``，确定性开关语义同 ``deterministic_enabled()``
       （开 → 归并后按 tid 升序；关 → ``maintain_order=True`` 保持输入序）。
    2. 归并表达式由 ``_base_agg_exprs(LIGHT_COLUMNS)`` 产出 —— 与全宽路径
       **同一个函数、同一份 _MERGE_SPEC**：``total_ms`` / ``total_latency`` /
       ``worker_total_latency`` / ``op_key`` / ``operation`` / ``bucket_epoch``
       / ``log_id`` 走 ``drop_nulls().first()``，``src`` / ``dst`` 走
       ``max_rank``（按 ``_src_rank`` 降序取首行）。
    3. 归并后完全复刻 build_trace_frame 的后续处理：``total_ms`` 为空退回本
       trace 的 ``worker_total_latency``、``total_latency`` 为空同理、src/dst
       ``fill_null("")``、filter（tid 非空且 total_ms 非空且 total_ms >= 0）。
    4. ``c2w_urma_latency`` 与 w2w/create/publish 静态 null 列**不产出**
       （它们是宽列，只有明细子集需要）。

    Args:
        frame: 只含 ``LIGHT_COLUMNS`` 的 polars DataFrame（或同形状 dict）。

    Returns:
        polars DataFrame，列 = ``_LIGHT_TRACE_COLUMNS``，行序与同数据下
        ``build_trace_frame`` 的轻列子集逐行一致。
    """
    import polars as pl

    if isinstance(frame, pl.DataFrame):
        src = frame
    else:
        src = pl.DataFrame({name: frame[name] for name in LIGHT_COLUMNS})
    det = deterministic_enabled()

    df_trace = src.group_by("tid", maintain_order=det).agg(
        **_base_agg_exprs(LIGHT_COLUMNS, nullable_rank=bool(src[_SRC_RANK_COL].null_count()))
    )

    # Fallback: total_ms / total_latency 为空时退回 worker_total_latency
    # （与 build_trace_frame 逐字一致，缺 SDK 行时只用 worker 日志也能建 trace）
    df_trace = df_trace.with_columns(
        pl.when(pl.col("total_ms").is_null())
        .then(pl.col("worker_total_latency"))
        .otherwise(pl.col("total_ms"))
        .alias("total_ms"),
        pl.when(pl.col("total_latency").is_null())
        .then(pl.col("worker_total_latency"))
        .otherwise(pl.col("total_latency"))
        .alias("total_latency"),
    )

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

    out = df_trace.select(list(_LIGHT_TRACE_COLUMNS))
    if det:
        out = out.sort("tid")
    return out


def bucket_representative_tids(
    df_trace_light, *, granularities: tuple[int, ...] = (10, 60, 600, 3600)
) -> set:
    """Use the same percentile selector as bucket persistence."""
    from latency.bucket.representatives import select_bucket_representatives

    return {
        tid
        for selected in select_bucket_representatives(df_trace_light, granularities).values()
        for tid in selected["tid"].to_list()
    }
