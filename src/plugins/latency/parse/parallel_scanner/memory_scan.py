"""Project selected source rows in bounded, ordered batches.

The source text is read once. Numeric locators avoid a second string hash join;
only each projection batch expands to parser fields and per-line wide columns.
"""
from __future__ import annotations

import polars as pl

_WIDE_BATCH_ROWS = 524_288


def _wanted_series(tids) -> pl.Series:
    if isinstance(tids, pl.Series):
        return tids.cast(pl.String)
    # Do not expand a Polars column to Python strings and then a hash set.
    return pl.Series("tid", [str(tid) for tid in tids if tid], dtype=pl.String)


def iter_wide(ctx, tids, *, sparse=False, batch_rows=_WIDE_BATCH_ROWS, consume=True,
              selected_rows=None):
    """Yield selected rows in the scanner's access-then-info order.

    ``consume`` releases the scan context as it is used. Set it to False for
    callers that need to project a second subset from the same context.
    ``sparse`` also omits generated response text not consumed by the reducer.
    """
    from . import scan_vector as scan

    if batch_rows <= 0:
        raise ValueError("batch_rows must be positive")
    locator = ctx.light_rows
    source = ctx.lines
    info_cache = ctx.info_cache
    if source is None or locator is None or not source.height:
        return
    # The parse worker already selected these locators when counting rows.
    # Reuse them instead of hashing every source trace a second time.
    if selected_rows is None:
        wanted = _wanted_series(tids)
        selected_rows = locator.filter(pl.col("tid").is_in(wanted.implode()))
    keep = (
        selected_rows
        .select("__row")
        .unique()
        .sort("__row")
        .to_series()
    )
    if consume:
        ctx.light_rows = None
        ctx.lines = None
        ctx.info_cache = None
    del locator, selected_rows
    if keep.is_empty():
        return
    if len(keep) == source.height:
        selected = source
    else:
        selected = source[keep].with_columns(
            pl.concat_str([pl.col("line"), pl.lit("")]).alias("line")
        )
    del source, keep
    # read-with-progress uses load-balanced file groups. Reestablish the file
    # order before splitting so first/last selections and RPC sums stay exact.
    ranks = {path.replace("\\", "/"): rank for path, rank in ctx.file_rank.items()}
    ranked = selected.with_columns(
        pl.col("__file").cast(pl.String).str.replace("\\", "/", literal=True)
        .replace_strict(ranks, default=None, return_dtype=pl.Int64).alias("__rank")
    )
    # Read batches are file-rank contiguous, so the frame is usually already
    # ordered; the O(n) probe skips the full sort copy.
    if ranked["__rank"].null_count() or not ranked["__rank"].is_sorted():
        ranked = ranked.sort("__rank", maintain_order=True)
    selected = ranked.drop("__rank")

    for kind, pairs in (("access", ctx.access_pairs), ("info", ctx.info_pairs)):
        if not pairs:
            continue
        paths = [path for path, _ in pairs]
        family = selected.filter(scan._path_filter(selected, paths))
        args = (paths, [[ctx.parsers[index] for index in indices] for _, indices in pairs])
        kwargs = dict(file_rank=ctx.file_rank)
        if kind == "access":
            project = scan.access_label_columns
            kwargs.update(log_ids=ctx.log_ids, window=ctx.window,
                          min_elapsed_us=ctx.min_elapsed_us, sparse=sparse)
        else:
            project = scan.info_label_columns
            kwargs["sparse"] = sparse
            if info_cache is not None:
                family = family.join(
                    info_cache, on="__row", how="left", maintain_order="left",
                )
                info_cache = None
        for batch in family.iter_slices(batch_rows):
            rows = project(batch, *args, **kwargs)
            if rows.height:
                # Parser string slices may retain the full original log buffer.
                # Detach only output strings; bounded downstream reducers can
                # then release each source allocation independently.
                rows = rows.with_columns(
                    pl.concat_str([pl.col(name), pl.lit("")]).alias(name)
                    for name, dtype in rows.schema.items() if dtype == pl.String
                )
                yield rows if sparse else scan._normalize(rows)
