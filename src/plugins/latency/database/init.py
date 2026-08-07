# Copyright (c) Huawei Technologies Co., Ltd. 2023-2025. All rights reserved.
"""PostgreSQL database initialization helpers."""
from __future__ import annotations

from datetime import datetime, timedelta

from sqlalchemy import text

from latency.database.engine import PGManager
from latency.database.models import Base

# (table_name, column_name, column_type) added to existing databases after the
# corresponding ORM model gained the column.  Each entry is a compile-time
# constant, never derived from untrusted input.
_MISSING_COLUMN_DDL: list[tuple[str, str, str]] = [
    ("trace_failure_event", "operation", "VARCHAR"),
    ("src_dst_aggregated_event", "kb_id", "VARCHAR"),
    ("time_window_aggregated", "ave_total_latency", "DOUBLE PRECISION"),
    ("time_window_aggregated", "latency_sum", "DOUBLE PRECISION"),
    ("time_window_aggregated", "min_total_latency", "DOUBLE PRECISION"),
    ("time_window_aggregated", "max_total_latency", "DOUBLE PRECISION"),
    ("time_window_aggregated", "p95_total_latency", "DOUBLE PRECISION"),
    ("time_window_aggregated", "p99_total_latency", "DOUBLE PRECISION"),
]


async def _ensure_missing_columns() -> None:
    """Add columns that exist on the ORM model but may be absent on old DBs.

    ``Base.metadata.create_all`` skips tables that already exist, so columns
    added to a model after the table was first created never appear on disk.
    ``ALTER TABLE ... ADD COLUMN IF NOT EXISTS`` is idempotent and is a no-op
    on fresh databases where create_all already created the column.
    """
    async with PGManager.engine().begin() as conn:
        for table, column, col_type in _MISSING_COLUMN_DDL:
            await conn.execute(text(
                f"ALTER TABLE {table} "
                f"ADD COLUMN IF NOT EXISTS {column} {col_type}"
            ))


def _month_iter(start: datetime, end: datetime):
    """Yield the first day of every month from start to end (inclusive)."""
    y, m = start.year, start.month
    end_y, end_m = end.year, end.month
    while (y, m) <= (end_y, end_m):
        yield datetime(y, m, 1)
        m += 1
        if m == 13:
            m = 1
            y += 1


async def _create_time_window_partition(conn, part_start: datetime) -> None:
    """Create a single monthly partition if it does not already exist."""
    if part_start.month == 12:
        part_end = datetime(part_start.year + 1, 1, 1)
    else:
        part_end = datetime(part_start.year, part_start.month + 1, 1)
    part_name = f"time_window_aggregated_{part_start:%Y%m}"
    from_bound = part_start.strftime("%Y-%m-%d %H:%M:%S")
    to_bound = part_end.strftime("%Y-%m-%d %H:%M:%S")
    await conn.execute(
        text(
            f"CREATE TABLE IF NOT EXISTS {part_name} "
            f"PARTITION OF time_window_aggregated "
            f"FOR VALUES FROM ('{from_bound}') TO ('{to_bound}')"
        )
    )


async def migrate_timestamptz_to_timestamp() -> None:
    """Convert all TIMESTAMPTZ columns to TIMESTAMP (no timezone).

    This keeps timestamp values exactly as they were written, without any
    timezone conversion.  Safe to run multiple times (idempotent).
    """
    async with PGManager.engine().begin() as conn:
        rows = await conn.execute(text(
            "SELECT table_name, column_name "
            "FROM information_schema.columns "
            "WHERE table_schema = 'public' "
            "AND data_type = 'timestamp with time zone'"
        ))
        for table_name, column_name in rows:
            await conn.execute(text(
                f"ALTER TABLE {table_name} "
                f"ALTER COLUMN {column_name} "
                f"TYPE timestamp without time zone"
            ))


async def create_log_parse_result_partitions() -> None:
    """Create 32 HASH partitions for log_parse_result."""
    async with PGManager.engine().begin() as conn:
        for i in range(32):
            await conn.execute(
                text(
                    f"CREATE TABLE IF NOT EXISTS log_parse_result_p{i} "
                    f"PARTITION OF log_parse_result FOR VALUES WITH (MODULUS 32, REMAINDER {i})"
                )
            )


async def migrate_yuanrong_metric_columns() -> None:
    """为已有数据库幂等补齐 yuanrong_tool 的请求级指标列。"""
    float_columns = (
        "total_latency_us", "sdk_processing_us", "master_processing_us",
        "worker_access_latency_us", "remote_worker_internal_us", "local_worker_internal_us",
        "local_worker_internal_active_us", "sdk_rpc_network_us", "sdk_rpc_framework_us",
        "sdk_rpc_total_us", "master_rpc_network_us", "master_rpc_framework_us",
        "master_rpc_total_us", "remote_worker_rpc_network_us", "remote_worker_rpc_framework_us",
        "remote_worker_rpc_total_us", "urma_processing_us", "remote_worker_processing_us",
        "client_master_rpc_network_us", "client_master_rpc_framework_us",
        "client_master_rpc_total_us", "client_remote_rpc_network_us",
        "client_remote_rpc_framework_us", "client_remote_rpc_total_us",
    )
    async with PGManager.engine().begin() as conn:
        for column in float_columns:
            await conn.execute(text(
                f"ALTER TABLE log_parse_result ADD COLUMN IF NOT EXISTS {column} DOUBLE PRECISION"
            ))
        await conn.execute(text(
            "ALTER TABLE log_parse_result ADD COLUMN IF NOT EXISTS request_mode VARCHAR"
        ))
        await conn.execute(text(
            "ALTER TABLE log_parse_result ADD COLUMN IF NOT EXISTS urma_inflight_max INTEGER"
        ))


LATENCY_BUCKET_TABLES = (
    "latency_bucket_10s",
    "latency_bucket_1min",
    "latency_bucket_10min",
    "latency_bucket_1h",
)


async def create_latency_bucket_partitions() -> None:
    """Create 32 HASH partitions for each latency_bucket_* table."""
    async with PGManager.engine().begin() as conn:
        for table in LATENCY_BUCKET_TABLES:
            for i in range(32):
                await conn.execute(
                    text(
                        f"CREATE TABLE IF NOT EXISTS {table}_p{i} "
                        f"PARTITION OF {table} FOR VALUES WITH (MODULUS 32, REMAINDER {i})"
                    )
                )


async def create_time_window_partitions(
    start: datetime,
    months: int = 24,
) -> None:
    """Create RANGE partitions for time_window_aggregated around ``start``.

    Partitions are created for ``months`` months starting one year before
    ``start`` so historical log data is covered immediately after startup.
    """
    part_start = (start - timedelta(days=365)).replace(
        day=1, hour=0, minute=0, second=0, microsecond=0
    )
    part_end = part_start
    for _ in range(months):
        if part_end.month == 12:
            part_end = datetime(part_end.year + 1, 1, 1)
        else:
            part_end = datetime(part_end.year, part_end.month + 1, 1)

    async with PGManager.engine().begin() as conn:
        for month_start in _month_iter(part_start, part_end):
            await _create_time_window_partition(conn, month_start)


async def ensure_time_window_partitions(
    start: datetime,
    end: datetime,
) -> None:
    """Create any missing monthly partitions needed for ``[start, end]``.

    This is used by the bulk insert path to avoid
    ``no partition of relation found for row`` errors when logs contain
    timestamps outside the initial partition window.
    """
    month_start = datetime(start.year, start.month, 1)
    month_end = datetime(end.year, end.month, 1)

    async with PGManager.engine().begin() as conn:
        for month in _month_iter(month_start, month_end):
            await _create_time_window_partition(conn, month)


async def create_manual_indexes() -> None:
    """Create GIN / partial indexes that are not auto-generated by SQLAlchemy."""
    indexes = [
        "CREATE INDEX IF NOT EXISTS idx_lpr_pod_ips ON log_parse_result USING GIN (pod_ips) WHERE existed_status = TRUE",
        "CREATE INDEX IF NOT EXISTS idx_lpr_log_id_time ON log_parse_result (log_id, timestamp, src_ip, dst_ip) WHERE existed_status = TRUE",
        "CREATE INDEX IF NOT EXISTS idx_lpr_timestamp ON log_parse_result (timestamp) WHERE existed_status = TRUE",
        "CREATE INDEX IF NOT EXISTS idx_lpr_cluster ON log_parse_result (cluster_name, aggregated_event_id) WHERE existed_status = TRUE",
        "CREATE INDEX IF NOT EXISTS idx_lpr_host ON log_parse_result (host, aggregated_event_id) WHERE existed_status = TRUE",
        "CREATE INDEX IF NOT EXISTS idx_lpr_trace_id ON log_parse_result (trace_id) WHERE existed_status = TRUE AND trace_id IS NOT NULL",
        "CREATE INDEX IF NOT EXISTS idx_lpr_log_total_latency ON log_parse_result (log_id, total_latency) WHERE existed_status = TRUE AND total_latency IS NOT NULL",
        "CREATE INDEX IF NOT EXISTS idx_twa_kb_time ON time_window_aggregated (kb_id, time_bucket) WHERE existed_status = TRUE",
        "CREATE INDEX IF NOT EXISTS idx_twa_log_time_pair ON time_window_aggregated (log_id, time_bucket, src_ip, dst_ip) WHERE existed_status = TRUE",
        "CREATE INDEX IF NOT EXISTS idx_twa_kb_src_dst ON time_window_aggregated (kb_id, src_ip, dst_ip) WHERE existed_status = TRUE",
        "CREATE INDEX IF NOT EXISTS idx_sdae_log_id ON src_dst_aggregated_event(log_id) WHERE existed_status = TRUE",
        "CREATE INDEX IF NOT EXISTS idx_sdae_src_dst ON src_dst_aggregated_event(src_ip, dst_ip) WHERE existed_status = TRUE",
    ]
    indexes += [
        f"CREATE INDEX IF NOT EXISTS ix_{table}_query "
        f"ON {table} (log_id, operation, bucket)"
        for table in LATENCY_BUCKET_TABLES
    ]
    async with PGManager.engine().begin() as conn:
        for idx_sql in indexes:
            await conn.execute(text(idx_sql))


async def init_postgresql_database() -> None:
    """Initialize PostgreSQL: create tables, partitions, indexes.

    当前为 PostgreSQL-only 后端，不再做历史 SQLite/schema 迁移；
    需要保留数据的历史升级请使用外部迁移工具（如 Alembic）。
    """
    async with PGManager.engine().begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    await _ensure_missing_columns()
    await migrate_timestamptz_to_timestamp()
    await migrate_yuanrong_metric_columns()
    await create_log_parse_result_partitions()
    await create_time_window_partitions(datetime.now())
    await create_latency_bucket_partitions()
    await create_manual_indexes()
