"""Select percentile requests once, without per-row window ranks."""


def select_bucket_representatives(frame, granularities=(10, 60, 600, 3600)):
    import polars as pl
    from latency.bucket.statistics import PERCENTILE_MODES

    # The total order also specifies which request wins a latency tie. Keeping
    # only selection keys avoids copying metric/text columns for every trace.
    ordered = (
        frame.select("tid", "bucket_epoch", "total_latency", "total_ms", "operation")
        .filter(pl.col("bucket_epoch").is_not_null() & pl.col("total_ms").is_not_null())
        .select(
            "tid", "bucket_epoch", "total_latency",
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
            ordered.with_columns((pl.col("bucket_epoch") // seconds).alias("_bucket_id"))
            .group_by("_bucket_id", "_op_code").agg(picks)
            .sort("_bucket_id", "_op_code")
        )
        result[seconds] = pl.concat([
            groups.select("_bucket_id", "_op_code", mode)
            .filter(pl.col(mode).is_not_null()).unnest(mode)
            .with_columns(pl.lit(mode).alias("mode"))
            for mode, _ in PERCENTILE_MODES
        ])
    return result
