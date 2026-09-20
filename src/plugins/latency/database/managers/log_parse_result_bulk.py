# Copyright (c) Huawei Technologies Co., Ltd. 2023-2025. All rights reserved.
"""DataFrame -> PostgreSQL COPY writers for the parse-result tables (P3).

路线图 P3「去物化」：把「解析结果写库」从「逐行造 Python 对象（dataclass）+ ORM
/ 逐行 tuple」改成「polars DataFrame（列已对齐目标表）-> 列式类型转换 ->
asyncpg 原生 ``copy_records_to_table``」。本模块只负责**写入**这一段：给定
一个 polars DataFrame，把它按目标表的列序与列类型转成 COPY 记录并批量写入。

设计要点
--------
* **列定义取自 ORM/DDL 单一真源**：``CopySpec.columns`` 默认直接引用
  ``database.utils.COPY_COLUMNS`` 或 ORM 模型的列序，列类型（INET / ARRAY /
  TIMESTAMP）由 ``Base.metadata`` 反射得到，避免手写第二份列清单。
* **列式转换 + 分块**：先把（块内）每个目标列一次性转成 Python list
  （``Series.to_list()`` + 按列做一次 list comprehension），再用 ``zip`` 拼
  记录。不构造 dataclass / pydantic 对象，不逐字段 ``getattr``。
  ``copy_dataframe`` 按 ``batch_size`` 对 frame 分块转换 + 分块 COPY，峰值
  内存 O(batch_size)，行序与 frame 行序严格一致。
* **语义与 ``_make_field_row`` + ``result_to_pg_tuple`` 逐字段对齐**：
  - ``src_ip`` / ``dst_ip``（INET）：``database.utils.parse_ip``（空串 -> NULL,
    ``1.2.3.4:80`` -> ``1.2.3.4``, ``[v6]:port`` -> 去端口）。
  - ``pod_ips``（TEXT[]）：list -> ``[str(x)]``（空 list -> NULL），tuple 同理，
    字符串走 ``parse_pod_ips``（JSON 解析），与现状一致。
  - 时间列（TIMESTAMP WITHOUT TIME ZONE）：``parse_timestamp``（字符串解析，
    aware datetime 去 tzinfo）。
  - ``id``：默认逐行生成 ``uuid4``（目标表 DDL 无 server default，PK NOT NULL）；
    frame 自带 ``id`` 列时用列值，空串 / NULL 的单元格按现状填 ``uuid4``。
  - ``created_at``：frame 无该列时用调用参数，其次默认为「本批共享一个
    ``datetime.utcnow()``」，复刻 ``_make_field_row`` 的 ``_utc_now_str()``。
  - ``existed_status`` / ``aggregated_event_id`` / ``anomalous_event_id``：
    spec 常量（与 ORM / dataclass 默认值一致）。
* **NOT NULL 校验**：写入前按 ORM metadata 检查目标表 NOT NULL 列是否出现
  NULL，命中直接 ``ValueError``（而不是让 COPY 抛一个没有列名的
  ``NotNullViolation``）。
* **事务**：默认自建 ``PGManager.connection()``（``engine.begin()``）；调用方
  已经持有事务（如分桶表的 DELETE + INSERT 幂等写）时可传 ``pg_conn``
  （asyncpg 原生连接）复用同一事务。

用法
----
    import polars as pl
    from latency.database.managers.log_parse_result_bulk import (
        LOG_PARSE_RESULT_SPEC, copy_dataframe, build_records,
    )

    df_trace                                    # polars DataFrame，每 trace 一行
    df = df_trace.with_columns(
        pl.col("tid").is_in(anomalous_tids).alias("is_anomalous")
    ).select(...)                               # 可选：只留需要的列

    res = await copy_dataframe(
        df,
        LOG_PARSE_RESULT_SPEC,
        values={"log_id": log_file_id},         # 本批常量（覆盖 frame 同名列）
        created_at=shared_created_at,           # 缺省 = 本批共享 UTC now
        generate_ids=True,                      # 逐行 uuid4（frame 有 id 时用列值）
        batch_size=50_000,
    )
    print(res.rows, res.seconds, res.batches)

    # 分桶表：换 spec/表名即可（4 张表共用同一个列形状）
    from latency.database.managers.log_parse_result_bulk import BUCKET_SPECS
    await copy_dataframe(df_reps, BUCKET_SPECS[60].with_table("latency_bucket_1min"))

    # 离线查看将要写入的记录（测试 / 预检）
    records, columns = build_records(df, LOG_PARSE_RESULT_SPEC)

    # 已有事务内复用（DELETE + COPY 幂等写）
    async with PGManager.connection() as conn:
        raw = await conn.get_raw_connection()
        pg = raw.driver_connection
        await pg.execute("DELETE FROM latency_bucket_1min WHERE log_id = $1", log_id)
        await copy_dataframe(df_reps, BUCKET_SPECS[60], pg_conn=pg)

本模块不 import parse worker / bucket 包，避免把写库层耦合回业务层；
``BUCKET_COLUMNS`` 与 ``bucket.statistics`` 的同名常量保持逐列一致（有单测断言）。
"""
from __future__ import annotations

import logging
import time
import os
from itertools import repeat
from dataclasses import dataclass, field, replace
from datetime import datetime, timezone
from typing import Any, Callable, Mapping, Sequence

from sqlalchemy import ARRAY, DateTime
from sqlalchemy.dialects.postgresql import INET

from latency.database.engine import PGManager
from latency.database.models import (
    LatencyBucket10min,
    LatencyBucket10s,
    LatencyBucket1h,
    LatencyBucket1min,
)
from latency.database.utils import (
    COPY_COLUMNS,
    parse_ip,
    parse_pod_ips,
    parse_timestamp,
)

logger = logging.getLogger(__name__)

__all__ = [
    "CopySpec",
    "CopyResult",
    "DEFAULT_BATCH_SIZE",
    "LOG_PARSE_RESULT_COLUMNS",
    "LOG_PARSE_RESULT_SPEC",
    "BUCKET_COLUMNS",
    "BUCKET_SPECS",
    "utc_now",
    "build_records",
    "project_frame",
    "copy_records",
    "copy_dataframe",
]

# COPY 单批行数上限（与 anomalous_event._COPY_BATCH_SIZE 同量级）。
DEFAULT_BATCH_SIZE = 50_000

# log_parse_result 的目标列序 = database.utils.COPY_COLUMNS（现状 COPY 用同一份）。
LOG_PARSE_RESULT_COLUMNS: tuple[str, ...] = tuple(COPY_COLUMNS)

# 4 张分桶表列序完全一致，直接取 ORM 模型列序（= DDL 列序 = bucket BUCKET_COLUMNS）。
_BUCKET_MODELS = (LatencyBucket10s, LatencyBucket1min, LatencyBucket10min, LatencyBucket1h)
BUCKET_COLUMNS: tuple[str, ...] = tuple(
    col.name for col in LatencyBucket10s.__table__.columns
)
for _model in _BUCKET_MODELS[1:]:
    _columns = tuple(col.name for col in _model.__table__.columns)
    if _columns != BUCKET_COLUMNS:
        raise RuntimeError(
            f"{_model.__tablename__} column order differs from "
            f"{LatencyBucket10s.__tablename__}; BUCKET_COLUMNS cannot be shared"
        )


def utc_now() -> datetime:
    """本批共享的 created_at（复刻 worker ``_utc_now_str()`` 的 UTC 语义）。"""
    return datetime.now(timezone.utc).replace(tzinfo=None)


# ---------------------------------------------------------------------------
# 列级 coercion：目标列 <- frame 列 的值归一化（可声明式指定）
# ---------------------------------------------------------------------------
def _coerce_str_or_none(value: Any) -> Any:
    """``str(v) if v else None`` —— 复刻 ``_make_field_row`` 的 data_size/... 写法。"""
    return str(value) if value else None


def _coerce_none_if_falsy(value: Any) -> Any:
    """``v or None`` —— 复刻 ``_make_field_row`` 的 ``operation=flat.get("op") or None``。

    空串 / 0 / None 一律写 NULL（前端过滤语义依赖它：空串与 NULL 在
    ``operation.ilike('%GET%')`` 下都是不命中，但列值本身必须一致）。
    """
    return value if value else None


def _coerce_str(value: Any) -> Any:
    return None if value is None else str(value)


def _coerce_list_join(value: Any) -> Any:
    """``", ".join(...)`` —— 复刻 cluster_name 的 list -> varchar 归一化。

    空 list 与现状一致地写成空串（**不是** NULL）：``_make_field_row`` 对
    list 分支直接 join，不做真值判断。
    """
    if isinstance(value, (list, tuple)):
        return ", ".join(str(item) for item in value)
    return str(value) if value else None


def _coerce_int_or_none(value: Any) -> Any:
    """``int(v)`` 仅当 v 是数值 —— 复刻 urma_inflight_count 的读法（NaN -> None）。"""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    if isinstance(value, float) and value != value:  # NaN
        return None
    return int(value)


COERCIONS: dict[str, Callable[[Any], Any]] = {
    "identity": lambda value: value,
    "str_or_none": _coerce_str_or_none,
    "none_if_falsy": _coerce_none_if_falsy,
    "str": _coerce_str,
    "list_join": _coerce_list_join,
    "int_or_none": _coerce_int_or_none,
}


# ---------------------------------------------------------------------------
# 目标列的物理类型（从 ORM metadata 反射，不再手写第二份）
# ---------------------------------------------------------------------------
def _column_meta(table: str) -> dict[str, tuple[str, bool]]:
    """{column: (kind, nullable)}；kind ∈ {"inet", "array", "datetime", "scalar"}。"""
    from latency.database.models import Base

    orm_table = Base.metadata.tables.get(table)
    if orm_table is None:
        raise KeyError(
            f"unknown table {table!r}: not in ORM metadata "
            f"(CopySpec.type_source must name a mapped table)"
        )
    meta: dict[str, tuple[str, bool]] = {}
    for column in orm_table.columns:
        col_type = column.type
        if isinstance(col_type, INET):
            kind = "inet"
        elif isinstance(col_type, ARRAY):
            kind = "array"
        elif isinstance(col_type, DateTime):
            kind = "datetime"
        else:
            kind = "scalar"
        meta[column.name] = (kind, bool(column.nullable))
    return meta


def _to_inet(value: Any) -> Any:
    if value is None:
        return None
    return parse_ip(value if isinstance(value, str) else str(value))


def _to_datetime(value: Any) -> Any:
    if value is None:
        return None
    return parse_timestamp(value)


def _to_array(value: Any) -> Any:
    if value is None:
        return None
    if isinstance(value, (list, tuple)):
        return [str(item) for item in value] if len(value) else None
    return parse_pod_ips(value)


_KIND_CONVERTERS: dict[str, Callable[[Any], Any]] = {
    "inet": _to_inet,
    "datetime": _to_datetime,
    "array": _to_array,
    "scalar": lambda value: value,
}


# ---------------------------------------------------------------------------
# 表规格
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class CopySpec:
    """一次 COPY 的目标表 + 列形状 + frame 列映射。

    Attributes:
        table: 目标表名（可被 ``with_table`` 换成同形状的临时表 / 分区）。
        columns: 目标列序（COPY 的 ``columns=``）。
        type_source: 用来反射列类型 / NULL 约束的 ORM 表名（默认 ``table``）。
        source_map: 目标列 -> frame 列名（未列出的列同名读取）。
        defaults: 目标列的兜底常量：frame 里找不到来源列时使用（如 NOT NULL 列
            ``aggregated_event_id=""``）。frame 有该列时以列为准。
        constants: 目标列的固定常量：无视 frame 同名列，恒定写这个值（如
            ``host=None`` —— 现状 ``_make_field_row`` 从不写 host，生产库里
            ``host`` 恒为 NULL）。
        coercions: 目标列 -> ``COERCIONS`` 里的归一化名（默认 identity）。
        id_column: 需要逐行生成主键的列名（None = 不生成）。
        created_at_column: 缺省时填「本批共享时间戳」的列名。
        strict_not_null: 目标列按 ORM 判为 NOT NULL 却出现 NULL 时是否报错。
    """

    table: str
    columns: tuple[str, ...]
    type_source: str | None = None
    source_map: Mapping[str, str] = field(default_factory=dict)
    defaults: Mapping[str, Any] = field(default_factory=dict)
    constants: Mapping[str, Any] = field(default_factory=dict)
    coercions: Mapping[str, str] = field(default_factory=dict)
    id_column: str | None = None
    created_at_column: str | None = None
    strict_not_null: bool = True

    def source_for(self, target: str) -> str:
        return self.source_map.get(target, target)

    def with_table(self, table: str) -> "CopySpec":
        """换目标表名（列形状/类型真源不变）——写临时表 / 分区副本时用。"""
        return replace(self, table=table)

    def with_columns(self, columns: Sequence[str]) -> "CopySpec":
        """只写列的子集（COPY 允许省略有 server default / 可空列）。"""
        return replace(self, columns=tuple(columns))

    def meta(self) -> dict[str, tuple[str, bool]]:
        return _column_meta(self.type_source or self.table)


# log_parse_result：frame = df_trace（列名见 parse/parallel_scanner/columnar.py
# 的 TRACE_COLUMNS），映射关系与 worker._make_field_row 逐字段一致。
LOG_PARSE_RESULT_SPEC = CopySpec(
    table="log_parse_result",
    columns=LOG_PARSE_RESULT_COLUMNS,
    type_source="log_parse_result",
    source_map={
        # 目标列 -> frame 列名（其余目标列同名直读 df_trace）
        "trace_id": "tid",
        "src_ip": "src",
        "dst_ip": "dst",
        "operation": "op",
        "pod_ips": "pod_ip",
        "urma_inflight_count": "inflight_count",
        # 现状把 frame.c2w_urma_latency 同时写进两列
        "c2w_latency": "c2w_urma_latency",
    },
    defaults={
        # frame 缺列时的兜底（NOT NULL 列；与 dataclass / ORM 默认值一致）
        "aggregated_event_id": "",
        "anomalous_event_id": "",
        "existed_status": True,
    },
    constants={
        # 现状 _make_field_row 从不写这些列（生产库实测恒 NULL：host/content/
        # remark/anomaly_reason/offset 非空行数均为 0），frame 同名列必须忽略。
        "host": None,
        "content": None,
        "remark": None,
        "anomaly_reason": None,
        "anomaly_score": None,
        "offset": None,
    },
    coercions={
        "data_size": "str_or_none",
        "cluster_name": "list_join",
        "urma_inflight_count": "int_or_none",
        "operation": "none_if_falsy",
    },
    id_column="id",
    created_at_column="created_at",
)

# 4 张分桶表：frame 列名 == 目标列名（bucket/statistics._representative_tuple
# 产出的行形状），只有 INET 两列需要类型归一化。
_BUCKET_SOURCE_MAP: Mapping[str, str] = {}
_BUCKET_DEFAULTS: Mapping[str, Any] = {}


def _bucket_spec(seconds: int) -> CopySpec:
    table = {
        10: "latency_bucket_10s",
        60: "latency_bucket_1min",
        600: "latency_bucket_10min",
        3600: "latency_bucket_1h",
    }[seconds]
    return CopySpec(
        table=table,
        columns=BUCKET_COLUMNS,
        type_source=table,
        source_map=_BUCKET_SOURCE_MAP,
        defaults=_BUCKET_DEFAULTS,
        id_column=None,
        created_at_column=None,
    )


# 粒度（秒）-> spec；bucket/statistics.DEFAULT_TABLES 的键口径一致。
BUCKET_SPECS: dict[int, CopySpec] = {
    seconds: _bucket_spec(seconds) for seconds in (10, 60, 600, 3600)
}


# ---------------------------------------------------------------------------
# DataFrame -> COPY records
# ---------------------------------------------------------------------------
@dataclass
class CopyResult:
    """一次 ``copy_dataframe`` 的结果 / 打点。"""

    table: str
    rows: int
    columns: tuple[str, ...]
    batches: int
    build_seconds: float
    copy_seconds: float
    total_seconds: float

    def as_dict(self) -> dict[str, Any]:
        return {
            "table": self.table,
            "rows": self.rows,
            "columns": len(self.columns),
            "batches": self.batches,
            "build_seconds": round(self.build_seconds, 4),
            "copy_seconds": round(self.copy_seconds, 4),
            "total_seconds": round(self.total_seconds, 4),
        }


def _require_polars():
    import polars as pl  # 延迟导入：本模块被 import 时不强依赖 polars

    return pl


def project_frame(df: Any, spec: CopySpec) -> Any:
    """按 spec 把 frame 投影/重命名成目标列（诊断 / 预检用，非写入路径）。

    产出的 frame 列名 == ``spec.columns``、列序一致；常量列与生成列不在此处
    落地（它们由 ``build_records`` 按行填充）。
    """
    pl = _require_polars()
    if not isinstance(df, pl.DataFrame):
        raise TypeError(f"expected polars.DataFrame, got {type(df)!r}")

    expressions = []
    for target in spec.columns:
        if target in spec.constants:
            continue
        source = spec.source_for(target)
        if source in df.columns:
            expressions.append(pl.col(source).alias(target))
    return df.select(expressions)


def _uuid4_strings(count: int) -> list[str]:
    """Generate one bounded COPY batch of RFC 4122 v4 IDs with one syscall."""
    data = os.urandom(count * 16).hex()
    variants = dict(zip("0123456789abcdef", "89ab" * 4))
    return [
        f"{value[:8]}-{value[8:12]}-4{value[13:16]}-"
        f"{variants[value[16]]}{value[17:20]}-{value[20:]}"
        for offset in range(0, len(data), 32)
        for value in (data[offset:offset + 32],)
    ]


def build_records(
    df: Any,
    spec: CopySpec,
    *,
    created_at: Any = None,
    generate_ids: bool | None = None,
    values: Mapping[str, Any] | None = None,
    materialize: bool = True,
) -> tuple[Any, tuple[str, ...]]:
    """DataFrame -> COPY 记录 + 列名（不连库，便于离线比对 / 预检）。

    Args:
        df: polars DataFrame（每行一条记录）。其它类型直接 ``TypeError``。
        spec: ``CopySpec``。
        created_at: ``spec.created_at_column`` 的常量值（frame 无该列时生效）；
            缺省 = 本批共享 ``utc_now()``。str / datetime 均可。
        generate_ids: 是否逐行生成 uuid4 主键。None = 目标表有 ``id_column``
            时自动开启；frame 自带同名列时，空串 / NULL 单元格仍会补 uuid4
            （与 ``result_to_pg_tuple`` 一致）。
        values: 本批常量列（优先级最高；如 ``{"log_id": log_file_id}``）。
        materialize: False 时返回有界列迭代器，直接由 COPY 消费，避免为
            整批同时分配宽 tuple；默认保留列表接口。

    Returns:
        ``(records, columns)``；``records`` 可直接喂
        ``asyncpg.copy_records_to_table(table, records=..., columns=columns)``。
    """
    pl = _require_polars()
    if not isinstance(df, pl.DataFrame):
        raise TypeError(f"expected polars.DataFrame, got {type(df)!r}")

    rows = df.height
    meta = spec.meta()
    overrides = dict(values or {})
    auto_ids = bool(spec.id_column) if generate_ids is None else bool(generate_ids)
    if auto_ids and not spec.id_column:
        raise ValueError("generate_ids=True but spec.id_column is None")

    created = None
    if spec.created_at_column is not None:
        created = (
            parse_timestamp(created_at) if created_at is not None else utc_now()
        )

    from latency.database.utils import _parse_created_at

    columns = []
    available = set(df.columns)
    for target in spec.columns:
        kind, nullable = meta.get(target, ("scalar", True))
        convert = (_parse_created_at if kind == "datetime" and target == spec.created_at_column
                   else _KIND_CONVERTERS[kind])
        coercion_name = spec.coercions.get(target, "identity")
        coercion = COERCIONS[coercion_name]
        source = spec.source_for(target)
        raw = None
        converted_native = False
        constant = None
        if target in overrides:
            constant = overrides[target]
        elif target in spec.constants:
            constant = spec.constants[target]
        elif source in available:
            series = df[source]
            if target == spec.id_column and auto_ids:
                raw = series.to_list()
                missing = [index for index, value in enumerate(raw) if not value]
                for index, value in zip(missing, _uuid4_strings(len(missing))):
                    raw[index] = value
            elif series.null_count() != rows:
                if series.dtype == pl.List(pl.String) and (
                    (kind == "array" and coercion_name == "identity")
                    or (kind == "scalar" and coercion_name == "list_join")
                ):
                    # Native string lists need no per-element Python str()
                    # calls or second list allocation. Match str(None) inside
                    # a list, while retaining null and empty-list semantics.
                    normalized = series.list.eval(pl.element().fill_null("None"))
                    if kind == "array":
                        raw = [value or None for value in normalized.to_list()]
                    else:
                        raw = normalized.list.join(", ").to_list()
                    converted_native = True
                elif kind == "datetime" and coercion_name == "identity" and (
                    isinstance(series.dtype, pl.Datetime) and series.dtype.time_zone is None
                ):
                    raw = series.to_list()
                    converted_native = True
                else:
                    raw = series.to_list()
        elif target == spec.id_column:
            if auto_ids:
                raw = _uuid4_strings(rows)
        elif target == spec.created_at_column:
            constant = created
        elif target in spec.defaults:
            constant = spec.defaults[target]
        elif not nullable:
            raise ValueError(
                f"{spec.table}.{target} is NOT NULL but frame has no source "
                f"column {source!r} and spec has no "
                f"default/constant/override for it"
            )

        if raw is None:
            # Do not allocate or convert an entire Python column for constants
            # and typed-null arrays. zip consumes only one batch of repeats.
            if rows:
                constant = convert(coercion(constant))
            invalid_index = 0 if constant is None and rows else None
            # Array conversion previously returned an independent list per row.
            # Keep that contract without allocating a full repeated column.
            column = (map(list, repeat(constant, rows)) if kind == "array" and constant is not None
                      else repeat(constant, rows))
        else:
            if converted_native:
                pass
            elif kind != "scalar" and coercion_name != "identity":
                raw = [convert(coercion(value)) for value in raw]
            elif kind != "scalar":
                raw = [convert(value) for value in raw]
            elif coercion_name != "identity":
                raw = [coercion(value) for value in raw]
            invalid_index = raw.index(None) if spec.strict_not_null and not nullable and None in raw else None
            column = raw
        if spec.strict_not_null and not nullable and invalid_index is not None:
            raise ValueError(
                f"{spec.table}.{target} is NOT NULL but row {invalid_index} is NULL "
                f"(source={source!r})"
            )
        columns.append(column)

    records = zip(*columns) if rows else iter(())
    return (list(records) if materialize else records), tuple(spec.columns)


async def copy_records(
    records: Sequence[Sequence[Any]],
    table: str,
    columns: Sequence[str],
    *,
    batch_size: int = DEFAULT_BATCH_SIZE,
    pg_conn: Any = None,
) -> CopyResult:
    """两阶段入口：已备好的 COPY 记录 -> 目标表（分批复用同一连接）。"""
    if batch_size <= 0:
        raise ValueError("batch_size must be > 0")
    started = time.perf_counter()
    batches = 0

    async def _run(pg: Any) -> None:
        nonlocal batches
        for offset in range(0, len(records), batch_size):
            batch = records[offset : offset + batch_size]
            await pg.copy_records_to_table(table, records=batch, columns=list(columns))
            batches += 1

    if pg_conn is not None:
        await _run(pg_conn)
    else:
        async with PGManager.connection() as conn:
            raw = await conn.get_raw_connection()
            await _run(raw.driver_connection)

    copy_seconds = time.perf_counter() - started
    result = CopyResult(
        table=table,
        rows=len(records),
        columns=tuple(columns),
        batches=batches,
        build_seconds=0.0,
        copy_seconds=copy_seconds,
        total_seconds=copy_seconds,
    )
    if records:
        logger.info(
            "[Store][PG] COPY %s rows into %s (%d cols, %d batches) in %.3fs",
            result.rows,
            table,
            len(columns),
            batches,
            copy_seconds,
        )
    return result


async def copy_dataframe(
    df: Any,
    spec: CopySpec | str,
    *,
    batch_size: int = DEFAULT_BATCH_SIZE,
    created_at: Any = None,
    generate_ids: bool | None = None,
    values: Mapping[str, Any] | None = None,
    pg_conn: Any = None,
    build: bool = True,
) -> CopyResult:
    """polars DataFrame -> 目标表（列式转换 + asyncpg COPY）。

    **分块**：``batch_size`` 同时是「转换块」与「COPY 批」的大小 —— 大于
    ``batch_size`` 的 frame 会被 ``slice`` 成块，逐块 ``build_records`` +
    COPY，保证 Python 侧峰值内存是 O(batch_size) 而不是 O(rows)，且**行序
    与 frame 行序严格一致**（切片不动序）。``created_at`` 缺省时全批共用一个
    时间戳（不因分块而漂移）。

    Args:
        df: 列已对齐目标表（或可通过 ``spec.source_map`` 对齐）的 polars DataFrame。
        spec: ``CopySpec``，或内置表名（``"log_parse_result"`` /
            ``"latency_bucket_10s|1min|10min|1h"``）
        batch_size: 单块/单批行数上限。
        created_at: 见 ``build_records``。
        generate_ids: 见 ``build_records``。
        values: 见 ``build_records``（本批常量列）。
        pg_conn: 已打开的 asyncpg 原生连接（复用调用方事务）；None 时本模块
            自建 ``PGManager.connection()``。
        build: False 时按 ``df`` 的原生行序直接 COPY（跳过 ``build_records``
            的逐列归一化，仅适用于列类型已完全对齐的 frame）。

    Returns:
        ``CopyResult``（行数 / 批数 / 转换耗时 / COPY 耗时）。
    """
    pl = _require_polars()
    if not isinstance(df, pl.DataFrame):
        raise TypeError(f"expected polars.DataFrame, got {type(df)!r}")
    if isinstance(spec, str):
        spec = spec_for_table(spec)
    if batch_size <= 0:
        raise ValueError("batch_size must be > 0")

    started = time.perf_counter()
    if not build:  # pragma: no cover - 逃生舱，列/类型必须已严格对齐
        return await copy_records(
            [tuple(row) for row in df.rows()],
            spec.table,
            tuple(spec.columns),
            batch_size=batch_size,
            pg_conn=pg_conn,
        )

    shared_created_at = created_at if created_at is not None else utc_now()
    state = {"build": 0.0, "copy": 0.0, "batches": 0, "columns": tuple(spec.columns)}

    async def _run(pg: Any) -> None:
        for offset in range(0, df.height, batch_size):
            chunk = df.slice(offset, batch_size)
            t_build = time.perf_counter()
            records, columns = build_records(
                chunk,
                spec,
                created_at=shared_created_at,
                generate_ids=generate_ids,
                values=values,
                materialize=False,
            )
            state["build"] += time.perf_counter() - t_build
            state["columns"] = columns
            if chunk.is_empty():
                continue
            t_copy = time.perf_counter()
            await pg.copy_records_to_table(
                spec.table, records=records, columns=list(columns)
            )
            state["copy"] += time.perf_counter() - t_copy
            state["batches"] += 1
            # The next build allocates Python columns and COPY tuples; release
            # this batch before that allocation instead of during assignment.
            del records, chunk

    if pg_conn is not None:
        await _run(pg_conn)
    else:
        async with PGManager.connection() as conn:
            raw = await conn.get_raw_connection()
            await _run(raw.driver_connection)

    result = CopyResult(
        table=spec.table,
        rows=df.height,
        columns=state["columns"],
        batches=state["batches"],
        build_seconds=state["build"],
        copy_seconds=state["copy"],
        total_seconds=time.perf_counter() - started,
    )
    if df.height:
        logger.info(
            "[Store][PG] COPY %s rows into %s (%d cols, %d batches, build=%.3fs "
            "copy=%.3fs)",
            result.rows,
            spec.table,
            len(result.columns),
            result.batches,
            result.build_seconds,
            result.copy_seconds,
        )
    return result


def spec_for_table(table: str) -> CopySpec:
    """内置表名 -> ``CopySpec``。"""
    if table == LOG_PARSE_RESULT_SPEC.table:
        return LOG_PARSE_RESULT_SPEC
    for spec in BUCKET_SPECS.values():
        if spec.table == table:
            return spec
    raise KeyError(
        f"no built-in CopySpec for table {table!r}; "
        f"pass an explicit CopySpec (e.g. LOG_PARSE_RESULT_SPEC.with_table(...))"
    )
