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
    ("src_dst_aggregated_event", "operation", "VARCHAR"),
    ("time_window_aggregated", "operation", "VARCHAR"),
    ("time_window_aggregated", "ave_total_latency", "DOUBLE PRECISION"),
    ("time_window_aggregated", "latency_sum", "DOUBLE PRECISION"),
    ("time_window_aggregated", "min_total_latency", "DOUBLE PRECISION"),
    ("time_window_aggregated", "max_total_latency", "DOUBLE PRECISION"),
    ("time_window_aggregated", "p95_total_latency", "DOUBLE PRECISION"),
    ("time_window_aggregated", "p99_total_latency", "DOUBLE PRECISION"),
    ("brpc_diag_batch", "hit_count", "BIGINT"),
    ("brpc_diag_hit", "interface_id", "VARCHAR"),
    (
        "brpc_diag_hit",
        "interface_resolution",
        "VARCHAR NOT NULL DEFAULT 'unresolved'",
    ),
    ("brpc_profiling_result", "source_file", "VARCHAR"),
    ("failure_mode_knowledge", "error_code", "VARCHAR"),
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


async def _backfill_brpc_batch_hit_count() -> None:
    """Backfill the immutable batch count before enforcing NOT NULL."""
    async with PGManager.engine().begin() as conn:
        await conn.execute(text(
            "UPDATE brpc_diag_batch AS batch "
            "SET hit_count = ("
            "SELECT COUNT(*) FROM brpc_diag_hit AS hit "
            "WHERE hit.batch_id = batch.batch_id"
            ") WHERE batch.hit_count IS NULL"
        ))
        await conn.execute(text(
            "ALTER TABLE brpc_diag_batch "
            "ALTER COLUMN hit_count SET NOT NULL"
        ))


async def _backfill_brpc_batch_time_range() -> None:
    """Replace scan bounds with the actual imported-hit interval.

    BRPC query timestamps have second precision.  Keep the stored lower bound
    exact and round the exclusive upper bound to the next second so formatting
    cannot exclude the final hit.
    """
    async with PGManager.engine().begin() as conn:
        await conn.execute(text(
            "UPDATE brpc_diag_batch AS batch "
            "SET start_timestamp = bounds.start_timestamp, "
            "end_timestamp = bounds.end_timestamp "
            "FROM ("
            "SELECT batch_id, MIN(timestamp) AS start_timestamp, "
            "((MAX(timestamp) / 1000000) + 1) * 1000000 AS end_timestamp "
            "FROM brpc_diag_hit GROUP BY batch_id"
            ") AS bounds "
            "WHERE batch.batch_id = bounds.batch_id "
            "AND (batch.start_timestamp <> bounds.start_timestamp "
            "OR batch.end_timestamp <> bounds.end_timestamp)"
        ))
        await conn.execute(text(
            "UPDATE brpc_diag_batch "
            "SET start_timestamp = created_at_timestamp, "
            "end_timestamp = "
            "((created_at_timestamp / 1000000) + 1) * 1000000 "
            "WHERE hit_count = 0 "
            "AND (start_timestamp <> created_at_timestamp "
            "OR end_timestamp <> "
            "((created_at_timestamp / 1000000) + 1) * 1000000)"
        ))


async def _backfill_brpc_unique_interfaces() -> None:
    """Resolve historical hits whose schema mapping has one candidate."""
    async with PGManager.engine().begin() as conn:
        await conn.execute(text(
            "UPDATE brpc_diag_hit AS hit "
            "SET interface_id = candidate.interface_id, "
            "interface_resolution = 'static_unique' "
            "FROM ("
            "SELECT schema_id, failure_mode_id, MIN(interface_id) AS interface_id "
            "FROM brpc_diag_failure_interface "
            "GROUP BY schema_id, failure_mode_id "
            "HAVING COUNT(*) = 1"
            ") AS candidate "
            "WHERE hit.schema_id = candidate.schema_id "
            "AND hit.failure_mode_id = candidate.failure_mode_id "
            "AND hit.interface_id IS NULL"
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


BRPC_DIAG_INDEX_DDL = (
    "CREATE INDEX IF NOT EXISTS idx_brpc_diag_hit_batch_timestamp "
    "ON brpc_diag_hit (batch_id, timestamp)",
    "CREATE INDEX IF NOT EXISTS idx_brpc_diag_hit_batch_pod_timestamp "
    "ON brpc_diag_hit (batch_id, pod_ip, timestamp)",
    "CREATE INDEX IF NOT EXISTS idx_brpc_diag_hit_batch_thread_timestamp "
    "ON brpc_diag_hit (batch_id, pod_ip, thread_id, timestamp)",
    "CREATE INDEX IF NOT EXISTS idx_brpc_diag_hit_batch_failure "
    "ON brpc_diag_hit (batch_id, schema_id, failure_mode_id)",
    "CREATE INDEX IF NOT EXISTS idx_brpc_diag_failure_interface_lookup "
    "ON brpc_diag_failure_interface "
    "(schema_id, failure_mode_id, interface_id)",
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


async def migrate_yuanrong_bucket_columns() -> None:
    """为已有数据库幂等补齐 latency_bucket_* 的 yuanrong 请求级指标列。"""
    _cols = (
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
        for table in LATENCY_BUCKET_TABLES:
            for column in _cols:
                await conn.execute(text(
                    f"ALTER TABLE {table} ADD COLUMN IF NOT EXISTS {column} DOUBLE PRECISION"
                ))
            await conn.execute(text(
                f"ALTER TABLE {table} ADD COLUMN IF NOT EXISTS request_mode VARCHAR"
            ))
            await conn.execute(text(
                f"ALTER TABLE {table} ADD COLUMN IF NOT EXISTS urma_inflight_max INTEGER"
            ))


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


async def migrate_brpc_log_type_column() -> None:
    """为已有数据库幂等补齐 log_file 表的 log_type 列。"""
    async with PGManager.engine().begin() as conn:
        await conn.execute(text(
            "ALTER TABLE log_file ADD COLUMN IF NOT EXISTS log_type VARCHAR DEFAULT 'kv-cache'"
        ))


async def migrate_trace_failure_event_status_code_to_array() -> None:
    """将 trace_failure_event.status_code 从 VARCHAR 迁移为 VARCHAR[]。

    旧列存的是单值字符串；新列存的是保序去重后的字符串数组。旧值
    （含空串）按需包成单元素数组或空数组保留，避免历史数据丢失。
    幂等：先读取当前列类型，已经是数组时不再执行 ALTER TYPE。
    """
    async with PGManager.engine().begin() as conn:
        result = await conn.execute(text(
            "SELECT data_type FROM information_schema.columns "
            "WHERE table_schema = current_schema() "
            "AND table_name = 'trace_failure_event' "
            "AND column_name = 'status_code'"
        ))
        data_type = result.scalar_one_or_none()
        if data_type == "ARRAY":
            return
        await conn.execute(text(
            "ALTER TABLE trace_failure_event "
            "ALTER COLUMN status_code TYPE VARCHAR[] "
            "USING CASE "
            "WHEN status_code IS NULL OR status_code = '' THEN ARRAY[]::VARCHAR[] "
            "ELSE ARRAY[status_code]::VARCHAR[] "
            "END"
        ))


async def backfill_trace_failure_event_status_codes() -> None:
    """按 trace 命中的故障模式回填故障码，修复历史 access 状态码数据。"""
    async with PGManager.engine().begin() as conn:
        await conn.execute(text(
            "WITH failure_mode_codes AS ("
            "SELECT id, CASE "
            "WHEN error_code IS NULL OR "
            "UPPER(BTRIM(error_code)) IN "
            "('', 'NULL', 'NULLPTR', 'NONE', 'N/A', 'NA', '-') THEN NULL "
            "WHEN UPPER(BTRIM(error_code)) ~ '^K_OK\\(\\s*\\+?0+\\s*\\)$' THEN '0' "
            "WHEN BTRIM(error_code) ~ '^[-+]?[0-9]+$' OR "
            "BTRIM(error_code) ~ '\\(\\s*[-+]?0+\\s*\\)\\s*$' THEN NULL "
            "WHEN BTRIM(error_code) ~ '\\(\\s*[-+]?[0-9]+\\s*\\)\\s*$' "
            "THEN SUBSTRING(BTRIM(error_code) FROM '\\(\\s*([-+]?[0-9]+)\\s*\\)\\s*$') "
            "ELSE BTRIM(error_code) END AS error_code "
            "FROM failure_mode_knowledge"
            "), mode_codes AS ("
            "SELECT trace_event.id, failure_mode_code.error_code, "
            "MIN(matched_mode.ordinality) AS first_position "
            "FROM trace_failure_event AS trace_event "
            "JOIN LATERAL UNNEST(STRING_TO_ARRAY(COALESCE(trace_event.failure_mode, ''), ',')) "
            "WITH ORDINALITY AS matched_mode(failure_mode_id, ordinality) ON TRUE "
            "JOIN failure_mode_codes AS failure_mode_code "
            "ON failure_mode_code.id = BTRIM(matched_mode.failure_mode_id) "
            "WHERE failure_mode_code.error_code IS NOT NULL "
            "GROUP BY trace_event.id, failure_mode_code.error_code"
            "), derived AS ("
            "SELECT trace_event.id, COALESCE("
            "ARRAY_AGG(mode_codes.error_code ORDER BY mode_codes.first_position) "
            "FILTER (WHERE mode_codes.error_code IS NOT NULL), ARRAY[]::VARCHAR[]"
            ")::VARCHAR[] AS status_codes "
            "FROM trace_failure_event AS trace_event "
            "LEFT JOIN mode_codes ON mode_codes.id = trace_event.id "
            "GROUP BY trace_event.id"
            ") "
            "UPDATE trace_failure_event AS trace_event "
            "SET status_code = derived.status_codes "
            "FROM derived "
            "WHERE trace_event.id = derived.id "
            "AND trace_event.status_code IS DISTINCT FROM derived.status_codes"
        ))


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
    indexes += BRPC_DIAG_INDEX_DDL
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
    await _backfill_brpc_batch_hit_count()
    await _backfill_brpc_batch_time_range()
    await _backfill_brpc_unique_interfaces()
    await migrate_timestamptz_to_timestamp()
    await migrate_yuanrong_metric_columns()
    await migrate_brpc_log_type_column()
    await migrate_trace_failure_event_status_code_to_array()
    await create_log_parse_result_partitions()
    await create_time_window_partitions(datetime.now())
    await create_latency_bucket_partitions()
    await migrate_yuanrong_bucket_columns()
    await create_manual_indexes()
