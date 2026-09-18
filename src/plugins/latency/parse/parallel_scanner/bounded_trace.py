"""Merge ordered scan batches without retaining the full per-line wide frame.

Each trace belongs to one hash partition. Sparse batches use dictionary-encoded
metadata, switching to in-memory LZ4 IPC for inputs above the compression limit.
Only one partition is expanded for the existing reducer. Keeping original rows,
instead of intermediate sums, preserves first/last and floating-point sum order.
Memory still grows with per-trace output and retained sparse/compressed payloads;
partition targets limit working data, not total process memory.
"""

from __future__ import annotations

from collections.abc import Iterable
from io import BytesIO
from math import ceil

import polars as pl

from latency.parse.columns import FLOAT_COLUMNS, INT_COLUMNS, OUTPUT_COLUMNS
from latency.parse.trace_frames import detach_trace_strings
from latency.parse.parallel_scanner.trace_frame import (
    _base_agg_exprs,
    _yuanrong_agg_exprs,
    build_trace_frame,
    deterministic_enabled,
)


_INPUT_COLUMNS = frozenset(
    {"tid"}.union(
        *(
            expr.meta.root_names()
            for expr in (*_base_agg_exprs().values(), *_yuanrong_agg_exprs().values())
        )
    )
)
_PARTITION_COLUMN = "__trace_partition"
_TARGET_PARTITION_ROWS = 262_144
_TARGET_PARTITION_BYTES = 64 * 1024 * 1024
_COMPRESSION_THRESHOLD_BYTES = 1024 * 1024 * 1024
# These fields repeat across many traces. Keep high-cardinality trace IDs and
# timestamps as strings to avoid populating a large dictionary for each parse.
_CATEGORICAL_COLUMNS = frozenset({
    "_label", "op", "operation", "op_key", "src", "dst", "pod_ip",
    "cluster_name", "host", "log_id",
})


def _empty_input() -> pl.DataFrame:
    return pl.DataFrame(
        schema={
            name: (
                pl.Float64 if name in FLOAT_COLUMNS
                else pl.Int64 if name in INT_COLUMNS else pl.String
            )
            for name in OUTPUT_COLUMNS if name in _INPUT_COLUMNS
        }
    )


def _restore_columns(
    parts: list[pl.DataFrame], schema: dict[str, pl.DataType]
) -> pl.DataFrame:
    # Fill missing columns when reducing one partition (or the small direct
    # input), rather than expanding all retained batches to the full schema.
    frame = pl.concat(parts, how="diagonal", rechunk=False)
    missing = [
        pl.lit(None, dtype=dtype).alias(name)
        for name, dtype in schema.items() if name not in frame.columns
    ]
    return frame.with_columns(missing) if missing else frame


def build_trace_frame_batched(
    batches: Iterable[pl.DataFrame],
    expected_rows: int,
    *,
    target_partition_rows: int = _TARGET_PARTITION_ROWS,
    target_partition_bytes: int = _TARGET_PARTITION_BYTES,
    compression: bool | None = None,
    compression_threshold_bytes: int = _COMPRESSION_THRESHOLD_BYTES,
    complete_schema: bool = False,
) -> pl.DataFrame:
    """Consume ordered scan batches and return the usual per-trace frame.

    ``expected_rows`` is an estimate of selected *per-line* rows, used with the
    first nonempty batch's size to choose a fixed number of hash partitions.
    Targets are sizing heuristics: every row of a very frequent tid must stay
    together. The caller should yield bounded batches and release them after
    consumption; a list retaining every source frame prevents those releases.
    All sparse/compressed partitions and the growing per-trace output remain
    resident; neither partition targets nor compression impose a hard RSS cap.

    Inputs use the existing scan column contract and must have compatible
    dtypes. All-null columns and columns unused by the reducer are omitted from
    retained payloads. Empty batches still contribute their schema. Small inputs
    take the same reducer directly, without hashing or dictionary encoding.
    Production sparse inputs pass ``complete_schema=True`` to restore omitted
    scanner columns with typed nulls. The default keeps the observed schema,
    including absence of optional yuanrong inputs.

    Partitioned inputs keep native frames with low-cardinality string metadata
    encoded as Categorical. Columns are restored to their original dtypes before
    reduction, so sorting and output schemas retain the existing contract.
    ``compression=None`` switches to LZ4 IPC if estimated sparse input exceeds
    ``compression_threshold_bytes`` (1 GiB); False disables IPC and True forces
    it for partitioned inputs. No variant writes temporary files.

    Threshold/detail selection belongs to the caller. Yuanrong materials are
    computed for every surviving trace when the restored schema supplies them.
    """
    if expected_rows < 0:
        raise ValueError("expected_rows must be nonnegative")
    if (target_partition_rows <= 0 or target_partition_bytes <= 0
            or compression_threshold_bytes <= 0):
        raise ValueError("partition targets must be positive")

    schema: dict[str, pl.DataType] = dict(_empty_input().schema) if complete_schema else {}
    direct: list[pl.DataFrame] = []
    partitions: list[list[bytes | pl.DataFrame]] | None = None
    partition_count = 0
    use_ipc = False

    for batch in batches:
        projected = batch.select(
            name for name in batch.columns if name in _INPUT_COLUMNS
        )
        for name, dtype in projected.schema.items():
            previous = schema.setdefault(name, dtype)
            if dtype != previous:
                raise pl.exceptions.SchemaError(
                    f"scan batch column {name!r} changed dtype: {previous} -> {dtype}"
                )
        if projected.is_empty():
            continue

        # null_count reads validity metadata, without scanning all the values.
        sparse = projected.select(
            name for name, count in zip(
                projected.columns, projected.null_count().row(0)
            ) if count != projected.height or name == "tid"
        )
        del projected, batch

        if not partition_count:
            rows = max(expected_rows, sparse.height)
            estimated_bytes = rows * (sparse.estimated_size() / sparse.height)
            partition_count = max(
                1,
                ceil(rows / target_partition_rows),
                ceil(estimated_bytes / target_partition_bytes),
            )
            if partition_count > 1:
                partitions = [[] for _ in range(partition_count)]
                use_ipc = (
                    estimated_bytes > compression_threshold_bytes
                    if compression is None else compression
                )

        if partitions is None:
            direct.append(sparse)
        else:
            if not use_ipc:
                sparse = sparse.with_columns(
                    pl.col(name).cast(pl.Categorical)
                    for name, dtype in sparse.schema.items()
                    if name in _CATEGORICAL_COLUMNS and dtype == pl.String
                )
            grouped = sparse.with_columns(
                (pl.col("tid").hash(seed=0) % partition_count)
                .alias(_PARTITION_COLUMN)
            ).partition_by(
                _PARTITION_COLUMN,
                maintain_order=False,
            )
            del sparse
            # partition_by preserves row order inside each group, including
            # when group order is unspecified. Append maintains batch order.
            while grouped:
                piece = grouped.pop()
                key = piece.drop_in_place(_PARTITION_COLUMN)[0]
                if use_ipc:
                    # Standard UTF-8 IPC copies selected values; StringView IPC
                    # could retain backing buffers belonging to other buckets.
                    buffer = piece.write_ipc(None, compression="lz4", compat_level=pl.CompatLevel.oldest())
                    partitions[key].append(buffer.getvalue())
                    del buffer
                else:
                    partitions[key].append(piece)
                del piece
            del grouped

    if not partition_count:
        empty = pl.DataFrame(schema=schema) if schema else _empty_input()
        return build_trace_frame(empty)
    if partitions is None:
        return build_trace_frame(_restore_columns(direct, schema))

    result: list[pl.DataFrame] = []
    for index in range(len(partitions)):
        payloads = partitions[index]
        if not payloads:
            continue
        partitions[index] = []
        if use_ipc:
            # Release compressed buffers as decoding proceeds.
            parts = []
            for position in range(len(payloads)):
                payload = payloads[position]
                payloads[position] = b""
                parts.append(pl.read_ipc(BytesIO(payload), memory_map=False))
                del payload
            payloads.clear()
        else:
            parts = payloads
        frame = _restore_columns(parts, schema)
        del parts, payloads
        if not use_ipc:
            frame = frame.with_columns(
                pl.col(name).cast(schema[name])
                for name, dtype in frame.schema.items() if dtype == pl.Categorical
            )
        reduced = build_trace_frame(frame)
        # List(String) values (pod/cluster) also retain StringView buffers after
        # unique/sort/implode. Detach both scalar and nested surviving text.
        result.append(detach_trace_strings(reduced))
        del frame, reduced

    merged = pl.concat(result, how="vertical", rechunk=False)
    return merged.sort("tid") if deterministic_enabled() else merged
