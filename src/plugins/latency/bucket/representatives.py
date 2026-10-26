"""Select percentile requests once, without per-row window ranks."""

import polars as pl  # 模块级导入：_bucket_id_expr / _transport_representatives 均使用


def select_bucket_representatives(frame, granularities=(1, 10, 60, 600, 3600)):
    from latency.bucket.statistics import PERCENTILE_MODES

    # The total order also specifies which request wins a latency tie. Keeping
    # only selection keys avoids copying metric/text columns for every trace.
    # ``__qgt``（QueryAndGet 传输类型）是分桶代表行按 local/remote 分别选代表
    # 的前置依赖：light 路径由 build_trace_frame_light 产出，宽路径由
    # _yuanrong_agg_exprs 产出；无该列（历史/非 QueryAndGet 数据）时回退旧逻辑。
    has_qgt = "__qgt" in frame.columns
    # ``epoch_sec``（原始秒级 epoch，与 bucket_epoch 同源但**不做 10s 对齐**）：
    # 1s 粒度的桶号来源 —— ``bucket_epoch // 1`` 会退化为 10s 对齐值，把 10s
    # 窗口内的 trace 全塞进同一个"1秒桶"；无该列（手工构造的测试帧等）时
    # 回退旧逻辑（1s 桶按 10s 对齐值，桶内 trace 数量被压缩，但仍可运行）。
    has_epoch_sec = "epoch_sec" in frame.columns
    sel_cols = ["tid", "bucket_epoch", "total_latency", "total_ms", "operation"]
    if has_epoch_sec:
        sel_cols.append("epoch_sec")
    if has_qgt:
        sel_cols.append("__qgt")
    ordered = (
        frame.select(sel_cols)
        .filter(pl.col("bucket_epoch").is_not_null() & pl.col("total_ms").is_not_null())
        .select(
            "tid", "bucket_epoch", "total_latency",
            *(["epoch_sec"] if has_epoch_sec else []),
            *(["__qgt"] if has_qgt else []),
            pl.when(pl.col("operation").str.contains("GET", literal=True))
            .then(pl.lit(0, dtype=pl.Int64)).otherwise(pl.lit(1, dtype=pl.Int64))
            .alias("_op_code"),
        )
        .sort(["total_latency", "tid"], nulls_last=True)
    )
    picks = []
    for mode, percentile in PERCENTILE_MODES:
        index = (pl.len().cast(pl.Float64) * percentile).floor().cast(pl.Int64).clip(lower_bound=1) - 1
        # rank(ordinal) omits null latencies but len() includes them. Preserve
        # that behavior, including a selected request whose tid itself is null.
        index = pl.when(index < pl.col("total_latency").count()).then(index)
        picks.append(pl.struct("tid", "total_latency").get(index).alias(mode))
    result = {}
    for seconds in granularities:
        groups = (
            ordered.with_columns(_bucket_id_expr(seconds, has_epoch_sec))
            .group_by("_bucket_id", "_op_code").agg(picks)
            .sort("_bucket_id", "_op_code")
        )
        base = pl.concat([
            groups.select("_bucket_id", "_op_code", mode)
            .filter(pl.col(mode).is_not_null()).unnest(mode)
            .with_columns(pl.lit(mode).alias("mode"))
            for mode, _ in PERCENTILE_MODES
        ])
        # GET 组再按传输类型分别选 local/remote 分位代表，与整体代表合并进单行
        # （分桶表主键 (log_id, bucket, operation, mode) 不允许同桶同分位两行）。
        if has_qgt:
            base = base.join(
                _transport_representatives(ordered, seconds, has_epoch_sec),
                on=["_bucket_id", "_op_code", "mode"], how="left",
            )
        else:
            base = base.with_columns(
                pl.lit(None, dtype=pl.Utf8).alias("tid_local"),
                pl.lit(None, dtype=pl.Utf8).alias("tid_remote"),
            )
        result[seconds] = base
    return result


def _bucket_id_expr(seconds: int, has_epoch_sec: bool):
    """组键 ``_bucket_id``：1s 粒度取原始秒级 epoch，其余粒度取 10s 对齐值整除。

    10 整除 60/600/3600，故 ``bucket_epoch // g`` 对 g>1 与原始时间戳整除一致；
    而 g=1 时 ``bucket_epoch // 1`` 退化为 10s 对齐值（一个"1秒桶"实际容纳 10s
    窗口的 trace），必须改用秒级 ``epoch_sec`` 才能得到真正的秒级桶。
    """
    if has_epoch_sec and seconds == 1:
        # info-only trace 无 SDK 秒级时间戳，epoch_sec 为 null；回退 bucket_epoch
        # （10s 对齐值）兜底，避免 _bucket_id 为 null 使分位统计崩溃降级。
        return pl.coalesce(pl.col("epoch_sec"), pl.col("bucket_epoch")).alias("_bucket_id")
    return (pl.col("bucket_epoch") // seconds).alias("_bucket_id")


def _transport_representatives(ordered, seconds, has_epoch_sec: bool = False):
    """GET 组按 QueryAndGet 传输类型（local/remote）分别选出的分位代表行。

    传输判定对齐 ``trace_frame._yuanrong_from_grouped``：``__qgt`` 大写 == "UB"
    → remote，其余非空值 → local（``__qgt`` 为 null 的 trace 不参与 —— 非
    QueryAndGet，无 query_get_* 分段）。返回列
    ``_bucket_id / _op_code(恒 0) / mode / tid_local / tid_remote``；某桶某分位
    只有单侧代表时，缺失侧为 null（统计层相应分段取 null，前端自动过滤）。
    """
    import polars as pl
    from latency.bucket.statistics import PERCENTILE_MODES

    qg = ordered.filter(
        (pl.col("_op_code") == 0) & pl.col("__qgt").is_not_null()
    ).with_columns(
        # 全 null 时 __qgt 可能推断为 null dtype，显式 cast 到 String 再判 UB。
        (pl.col("__qgt").cast(pl.Utf8, strict=False).str.to_uppercase() == "UB")
        .fill_null(False).alias("_is_ub"),
        _bucket_id_expr(seconds, has_epoch_sec),
    )
    picks = []
    for mode, percentile in PERCENTILE_MODES:
        index = (pl.len().cast(pl.Float64) * percentile).floor().cast(pl.Int64).clip(lower_bound=1) - 1
        index = pl.when(index < pl.col("total_latency").count()).then(index)
        picks.append(pl.struct("tid").get(index).alias(mode))
    per_type = qg.group_by("_bucket_id", "_is_ub").agg(picks).sort("_bucket_id", "_is_ub")
    parts = []
    for mode, _ in PERCENTILE_MODES:
        rows = (
            per_type.select("_bucket_id", "_is_ub", mode)
            .filter(pl.col(mode).is_not_null()).unnest(mode)
            .with_columns(pl.lit(mode).alias("mode"))
        )
        merged = (
            rows.filter(~pl.col("_is_ub")).select("_bucket_id", "mode", "tid")
            .rename({"tid": "tid_local"})
            .join(
                rows.filter(pl.col("_is_ub")).select("_bucket_id", "mode", "tid")
                .rename({"tid": "tid_remote"}),
                on=["_bucket_id", "mode"], how="full", coalesce=True,
            )
        )
        parts.append(merged)
    return (
        pl.concat(parts)
        .with_columns(pl.lit(0, dtype=pl.Int64).alias("_op_code"))
        .sort("_bucket_id", "mode")
    )
