"""Keep all-trace aggregation columns separate from selected detail columns."""
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import polars as pl


def detach_trace_strings(frame: "pl.DataFrame") -> "pl.DataFrame":
    """Copy only surviving text so string views cannot retain source log buffers."""
    import polars as pl

    expressions = []
    for name, dtype in frame.schema.items():
        if dtype == pl.String:
            expressions.append(pl.concat_str([pl.col(name), pl.lit("")]).alias(name))
        elif dtype == pl.List(pl.String):
            expressions.append(pl.col(name).list.eval(
                pl.concat_str([pl.element(), pl.lit("")])
            ).alias(name))
    return frame.with_columns(expressions) if expressions else frame


@dataclass(slots=True)
class TraceFrames:
    light: "pl.DataFrame"
    wide: "pl.DataFrame"
    null_columns: dict[str, "pl.DataType"] = field(default_factory=dict)
    wide_columns: tuple[str, ...] = ()
    bucket_representatives: dict[int, "pl.DataFrame"] | None = None

    @classmethod
    def from_frames(cls, light: "pl.DataFrame", wide: "pl.DataFrame") -> "TraceFrames":
        # One UInt32 locator per trace replaces dozens of mostly-null columns.
        index = wide.select("tid").with_row_index("_wide_row")
        indexed = light.join(index, on="tid", how="left", maintain_order="left")
        payload = wide.select([c for c in wide.columns if c not in light.columns])
        # Arrow typed-null numeric arrays still reserve a value buffer per row.
        # Keep their schema, and broadcast nulls only for an output batch.
        schema = payload.schema
        counts = payload.null_count().row(0, named=True) if payload.width else {}
        null_columns = {
            name: schema[name]
            for name, count in counts.items()
            if count == payload.height
        }
        return cls(indexed, payload.drop(list(null_columns)), null_columns, tuple(payload.columns))

    @property
    def height(self) -> int:
        return self.light.height

    def enrich(self, rows: "pl.DataFrame") -> "pl.DataFrame":
        """Gather wide values only for these rows; preserve their order and nulls."""
        from latency.parse.columns import TRACE_COLUMNS
        import polars as pl

        result = rows.drop("_wide_row")
        if self.wide.width:
            result = result.hstack(self.wide[rows["_wide_row"]])
        if self.null_columns:
            result = result.with_columns([
                pl.lit(None, dtype=dtype).alias(name)
                for name, dtype in self.null_columns.items()
            ])
        order = [c for c in TRACE_COLUMNS if c in result.columns]
        order.extend(c for c in rows.columns if c != "_wide_row" and c not in order)
        order.extend(c for c in (self.wide_columns or self.wide.columns) if c not in order)
        return result.select(order)
