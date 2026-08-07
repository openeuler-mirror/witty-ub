# Copyright (c) Huawei Technologies Co., Ltd. 2023-2025. All rights reserved.
"""分位桶统计模块（计划 latency-percentile-bucket-scale 的 C0-C5）。

在 parse worker 解析完成、明细表落库前，对内存中的解析结果按四档粒度
（10s / 1min / 10min / 1h）计算“分位代表请求”，写入 4 张统计表。

数据流（T7 后唯一入口 = df_trace，纯 polars，见 compute_bucket_stats_from_frame）：
    C0  输入过滤：timestamp / total_latency 为 None 的行不参与统计
        （polars filter ``bucket_epoch.is_not_null() & total_ms.is_not_null()``）。
    C1  算桶号：绝对墙钟对齐（epoch 秒 // 粒度，floor），跨天自动唯一，
        无时区 / DST 坑；桶起点可直接由桶号还原，与回退实时 SQL 一致。
    C2  组键：(桶号, operation)，GET/SET 分开选代表行。
    C3  组内按 total_latency 排序（``rank("ordinal")``）后取 5 分位代表行。
    C4  主进程拼 22 列 tuple，4 张表 delete+insert 放一个事务（写库幂等）。

T7 已删除 numpy / shared_memory / multiprocessing.spawn 旧实现
（``_filter_and_build_arrays`` / ``_parallel_pick`` / ``_pick_segment_worker``
/ ``_split_into_segments`` / ``compute_and_store_bucket_stats``）。

模块自包含：只依赖 schemas/engine/base 与 database.utils；不 import parse worker。
"""
from __future__ import annotations

import asyncio
import logging
import math
import os
import time
from typing import Any, Sequence

import numpy as np

from latency.database.utils import parse_ip

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# 常量
# ---------------------------------------------------------------------------

# 四档粒度（秒）与展示名 / 表名的映射。
GRANULARITY_KEYS: tuple[int, ...] = (10, 60, 600, 3600)

GRANULARITY_LABELS: dict[int, str] = {
    10: "10s",
    60: "1min",
    600: "10min",
    3600: "1h",
}

DEFAULT_TABLES: dict[int, str] = {
    10: "latency_bucket_10s",
    60: "latency_bucket_1min",
    600: "latency_bucket_10min",
    3600: "latency_bucket_1h",
}

# 14 个时延指标列，与 log_parse_result 的 metric_cols 保持一致。
METRIC_KEYS: tuple[str, ...] = (
    "total_latency",
    "urma_total_latency",
    "worker_query_meta_latency",
    "sdk_process",
    "sdk_rpc",
    "local_worker_cost",
    "local_worker_lock",
    "remote_worker_cost",
    "remote_worker_rpc",
    "master_process",
    "master_rpc_total",
    "create_latency",
    "publish_latency",
    "worker_total_latency",
)

# 5 种分位模式：(模式名, 分位点)。pmax=1.0 → floor(cnt*1)-1 = cnt-1（最大值行）。
PERCENTILE_MODES: tuple[tuple[str, float], ...] = (
    ("median", 0.5),
    ("p95", 0.95),
    ("p99", 0.99),
    ("p9999", 0.9999),
    ("pmax", 1.0),
)

# 统计表 COPY 列，与正式表 DDL 列序一致。
BUCKET_COLUMNS: tuple[str, ...] = (
    "kb_id",
    "log_id",
    "bucket",
    "operation",
    "mode",
    "src_ip",
    "dst_ip",
    "trace_id",
    "total_latency",
    "urma_total_latency",
    "worker_query_meta_latency",
    "sdk_process",
    "sdk_rpc",
    "local_worker_cost",
    "local_worker_lock",
    "remote_worker_cost",
    "remote_worker_rpc",
    "master_process",
    "master_rpc_total",
    "create_latency",
    "publish_latency",
    "worker_total_latency",
)

def _normalize_op(operation: Any) -> int:
    """归一化 handle → GET/SET 编码：含 'GET' 字样的 handle 视为 GET(0)，
    其余（SET/CREATE/PUBLISH/其他）一律视为 SET(1)。与 parse worker 的
    SDK_GET_OPS / WORKER_GET_OPS 语义一致（DS_KV_CLIENT_GET、DS_POSIX_GET
    等原始 handle 名，见计划 C2）。
    """
    op = operation or ""
    return 0 if "GET" in op.upper() else 1


def _row_field(row: Any, name: str) -> Any:
    """从 dataclass 行或轻量 metrics dict 行读取字段（双源支持）。

    ``_representative_tuple`` 需同时接受 dataclass（materializer 物化）与
    ``_frame_row_to_representative_dict`` 产出的 dict 行。
    """
    if isinstance(row, dict):
        return row.get(name)
    return getattr(row, name, None)


# ---------------------------------------------------------------------------
# C1. 算桶号
# ---------------------------------------------------------------------------

def compute_bucket_ids(timestamps: np.ndarray, granularity: int) -> np.ndarray:
    """向量化计算每行的桶号（绝对墙钟对齐，跨天自动唯一，无时区 / DST 坑）。

    调用前必须先过滤 NaT（见 C0），否则 NaT→INT64_MIN→负桶号。

    Args:
        timestamps: ``datetime64`` 数组（任意单位，本地墙钟语义）。
        granularity: 桶粒度（秒），如 10 / 60 / 600 / 3600。

    Returns:
        ``int64`` 数组：桶号 = epoch 秒（墙钟）// 粒度（floor）。``bucket_id *
        granularity`` 可直接还原墙钟对齐的桶起点（10s → xx:xx:10/20/30…，
        60s → xx:xx:00，3600s → xx:00:00），与回退实时 SQL 的
        ``date_trunc('minute'/'hour')`` 等墙钟对齐表达式一致。10/60/600/3600
        均整除 86400，因此跨天桶不碰撞、DST 日（23/25 小时）也不碰撞。
    """
    ts = timestamps.astype("datetime64[s]")
    return ts.astype("int64") // granularity


# ---------------------------------------------------------------------------
# C2. 排序 + 复合键分片
# ---------------------------------------------------------------------------

def _group_edges(
    bucket_ids: np.ndarray, op_codes: np.ndarray, order: np.ndarray
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """对单个粒度派生 (桶, operation) 组的边界。

    Args:
        bucket_ids: 该粒度的桶号数组（``int64``）。
        op_codes: operation 编码数组（``int64``，GET=0 / SET=1）。
        order: ``np.lexsort((bucket_10s, op_codes))`` 的全局排序下标。
            op 为主键、bucket 为次键 → 对任意粒度 G，组 (op, bucket_G) 的
            行在 ``order`` 中连续，且 ``op*K+bucket_G`` 单调。

    Returns:
        (keys, edges, ops, buckets)：``keys`` 为出现的复合键（升序）；
        ``edges`` 为各组在 ``order`` 中的绝对起点（末位补 ``len(order)``）；
        ``ops`` / ``buckets`` 与 ``keys`` 对齐的 op 编码与桶号。
    """
    k = int(bucket_ids.max()) + 1  # k > 最大桶号，复合键 = op*k + bucket
    sort_key = op_codes * k + bucket_ids
    keys = np.unique(sort_key)  # 用 unique 而非 arange(max+2)，防异常时间戳撑爆内存
    edges = np.searchsorted(sort_key[order], keys)
    edges = np.concatenate([edges, [len(order)]])
    return keys, edges, keys // k, keys % k


# ---------------------------------------------------------------------------
# C3. 每进程 argpartition 选 5 分位代表行
# ---------------------------------------------------------------------------

def percentile_kth_positions(count: int) -> list[int]:
    """每 (桶, op) 组内 5 个分位在排序后行中的相对位置（0-based）。

    用 ``math.floor(cnt*p) - 1`` 而非 ``round()``：round 是 banker's rounding
    （round(2.5)=2），会 off-by-one。结果 clamp 到 [0, cnt-1] 防越界
    （cnt>=1 时 floor(1*0.5)-1=-1 → 0；pmax 恒为 cnt-1）。
    小桶（如 cnt=2）时多个分位可能落同一行，允许重复（语义：小桶内
    p95≈p99≈p9999≈pmax 同请求，写库时不同 mode 是不同行）。
    """
    if count <= 0:
        return [0] * len(PERCENTILE_MODES)
    return [
        max(0, min(int(math.floor(count * p)) - 1, count - 1))
        for _, p in PERCENTILE_MODES
    ]


def pick_percentile_rows(
    latency_slice: np.ndarray, kth_positions: list[int] | None = None
) -> list[int]:
    """对一组 (桶, op) 的延迟数组用 argpartition 一次选出 5 个分位代表行。

    Args:
        latency_slice: 该组所有行的 total_latency（无需预排序，argpartition
            内部处理；O(n) 非全排序，一次拿 5 个 kth）。
        kth_positions: 5 个分位位置，缺省时用 ``percentile_kth_positions``
            按组内行数计算。

    Returns:
        与 ``PERCENTILE_MODES`` 对齐的相对行索引（0-based，组内下标）。
    """
    if kth_positions is None:
        kth_positions = percentile_kth_positions(len(latency_slice))
    if len(latency_slice) == 0:
        return []
    unique_kth = sorted(set(kth_positions))
    part = np.argpartition(latency_slice, unique_kth)
    return [int(part[k]) for k in kth_positions]


# ---------------------------------------------------------------------------
# C4. 合并 + 写库
# ---------------------------------------------------------------------------

def _representative_tuple(
    kb_id: str,
    log_id: str,
    bucket_start_dt,
    op_code: int,
    mode_name: str,
    r: Any,
) -> tuple[Any, ...]:
    """把一行代表行拼成统计表 COPY tuple（与 ``BUCKET_COLUMNS`` 对齐）。

    ``r`` 支持两种行源：dataclass（属性访问）或
    ``_frame_row_to_representative_dict`` 的 dict 行（``_row_field`` 读取），
    保证 materializer / 无 materializer 两条路径逐字段一致。
    """
    return (
        kb_id,
        log_id,
        bucket_start_dt,
        "GET" if op_code == 0 else "SET",
        mode_name,
        parse_ip(_row_field(r, "src_ip")),
        parse_ip(_row_field(r, "dst_ip")),
        _row_field(r, "trace_id"),
        _row_field(r, "total_latency"),
        _row_field(r, "urma_total_latency"),
        _row_field(r, "worker_query_meta_latency"),
        _row_field(r, "sdk_process"),
        _row_field(r, "sdk_rpc"),
        _row_field(r, "local_worker_cost"),
        _row_field(r, "local_worker_lock"),
        _row_field(r, "remote_worker_cost"),
        _row_field(r, "remote_worker_rpc"),
        _row_field(r, "master_process"),
        _row_field(r, "master_rpc_total"),
        _row_field(r, "create_latency"),
        _row_field(r, "publish_latency"),
        _row_field(r, "worker_total_latency"),
    )


# ---------------------------------------------------------------------------
# T4. df_trace → 分位代表行（polars 版，替代 shared_memory _parallel_pick）
# ---------------------------------------------------------------------------
def _frame_row_to_representative_dict(row: dict[str, object]) -> dict[str, object]:
    """df_trace 行（``iter_rows(named=True)``）→ ``_representative_tuple`` 可读行。

    df_trace 列名与轻量 metrics dict 只差 3 处映射：``tid``→``trace_id``、
    ``src``→``src_ip``、``dst``→``dst_ip``；14 个 METRIC_KEYS 列名与
    dataclass 字段完全一致。无 materializer 时用本映射直读 df 行；有
    materializer 时（worker 传 ``_make_field_row``）改由 dataclass 属性读取，
    两条路径逐字段一致。
    """
    return {
        "trace_id": row.get("tid"),
        "src_ip": row.get("src"),
        "dst_ip": row.get("dst"),
        **{key: row.get(key) for key in METRIC_KEYS},
    }


def compute_bucket_stats_from_frame(
    df_trace,
    kb_id: str = "",
    log_id: str = "",
    materializer: Any = None,
) -> dict[int, list[tuple[Any, ...]]]:
    """纯 polars 分位代表行选择（T7 后唯一选择路径）。

    语义（与 numpy 参考实现逐字段一致，见 T4 parity 测试）：
    - C0 过滤：``bucket_epoch``（= trace 时间戳的 10s 对齐 epoch 秒；非空
      即时间戳可解析）与 ``total_ms`` 非空的行才参与。
    - 组键：(bucket_id, op_code)。bucket_id = ``bucket_epoch // g`` ——
      10 整除 60/600/3600，故 10s 对齐 epoch 整除粒度 == 原时间戳整除粒度，
      桶起点与墙钟对齐一致。op_code 复用 ``_normalize_op`` 语义
      （含 "GET" → 0，其余含 None → 1）。
    - 代表行：组内按 ``total_latency`` 排序（``rank("ordinal")``，并列按
      行序稳定断结）后取 ``percentile_kth_positions(cnt)`` 指定的 kth 位置
      行。

    Args:
        df_trace: T2 ``parse_log`` 产出的 polars DataFrame（31 TRACE_COLUMNS，
            每 trace 一行）。
        kb_id / log_id: 写库冗余键（COPY tuple 前两列，与 ``_build_bucket_rows``
            同序）。
        materializer: 可选 ``callable(df_row_dict) -> dataclass``。df 行 dict
            → ``LogParseResultDataclass``（worker 的 ``_make_field_row``），
            只对选中的代表行调用（~300 个），其余行不物化。为 ``None`` 时直接
            按 ``_frame_row_to_representative_dict`` 读取 df 行。

    Returns:
        {granularity: rep 行 tuple 列表}。tuple 与 ``BUCKET_COLUMNS`` 对齐
        （``_representative_tuple`` 产物），可直接喂 ``_store_bucket_rows``。
    """
    import polars as pl

    df = df_trace.filter(
        pl.col("bucket_epoch").is_not_null()
        & pl.col("total_ms").is_not_null()
    )
    if df.height == 0:
        return {g: [] for g in GRANULARITY_KEYS}

    df = df.with_columns(
        pl.when(pl.col("operation").str.contains("GET", literal=True))
        .then(pl.lit(0, dtype=pl.Int64))
        .otherwise(pl.lit(1, dtype=pl.Int64))
        .alias("_op_code"),
    )

    rows_by_granularity: dict[int, list[tuple[Any, ...]]] = {}
    for g in GRANULARITY_KEYS:
        dg = df.with_columns((pl.col("bucket_epoch") // g).alias("_bucket_id"))
        dg = dg.with_columns(
            pl.col("total_latency")
            .rank("ordinal")
            .over(["_bucket_id", "_op_code"])
            .cast(pl.Int64)
            .alias("_rank"),
            pl.len().over(["_bucket_id", "_op_code"]).alias("_cnt"),
        )
        rows: list[tuple[Any, ...]] = []
        for mode_name, p in PERCENTILE_MODES:
            # kth rank（1-based）= max(1, min(floor(cnt*p), cnt))，与
            # percentile_kth_positions 的 0-based 位置 +1 完全一致（pmax→cnt）。
            kth_rank = (
                (pl.col("_cnt").cast(pl.Float64) * p)
                .floor()
                .cast(pl.Int64)
                .clip(lower_bound=1, upper_bound=pl.col("_cnt"))
            )
            for row in dg.filter(pl.col("_rank") == kth_rank).iter_rows(named=True):
                # 桶起点 = 桶号 * 粒度（epoch 秒，与 compute_bucket_ids 同源）。
                bucket_start_dt = np.datetime64(
                    int(row["_bucket_id"]) * g, "s"
                ).item()
                r: Any = _frame_row_to_representative_dict(row)
                if materializer is not None:
                    r = materializer(row)
                rows.append(
                    _representative_tuple(
                        kb_id,
                        log_id,
                        bucket_start_dt,
                        int(row["_op_code"]),
                        mode_name,
                        r,
                    )
                )
        rows_by_granularity[g] = rows
    return rows_by_granularity


def _build_bucket_rows(
    valid_rows: Sequence[Any],
    per_granularity: dict[int, tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]],
    reps: dict[int, list[tuple[int, int, int]]],
    kb_id: str,
    log_id: str,
    materializer: Any = None,
) -> dict[int, list[tuple[Any, ...]]]:
    """主进程按代表行原始索引取 14 列，拼各粒度待写行。

    Args:
        materializer: 可选 ``callable(row_dict) -> dataclass``。轻量 dict 行
            按 reps 选中的 orig 索引只对代表行构造 dataclass（~300 个），
            其余行保持 dict 不物化。为 ``None`` 时行源即 dataclass。
    """
    rows_by_granularity: dict[int, list[tuple[Any, ...]]] = {}
    # 同一代表行可被多个粒度选中；按 orig 索引只物化一次（T4 ~300 个）。
    materialized: dict[int, Any] = {}
    for g in GRANULARITY_KEYS:
        _, _, ops, buckets = per_granularity[g]
        rows: list[tuple[Any, ...]] = []
        for gid, mode_idx, orig in reps[g]:
            mode_name = PERCENTILE_MODES[mode_idx][0]
            # 桶起点 = 桶号 * 粒度（epoch 秒，墙钟对齐，与 compute_bucket_ids 同源）。
            bucket_start_dt = np.datetime64(int(buckets[gid]) * g, "s").item()
            row = valid_rows[orig]
            if materializer is not None and orig not in materialized:
                materialized[orig] = materializer(row)
            if materializer is not None:
                row = materialized[orig]
            rows.append(
                _representative_tuple(
                    kb_id, log_id, bucket_start_dt, int(ops[gid]), mode_name,
                    row,
                )
            )
        rows_by_granularity[g] = rows
    return rows_by_granularity


async def _store_bucket_rows(
    log_id: str,
    rows_by_granularity: dict[int, list[tuple[Any, ...]]],
    tables: dict[int, str],
    on_table: Any | None = None,
) -> None:
    """4 张表 ``DELETE WHERE log_id=?`` + INSERT 放一个事务（写库幂等）。

    复用 ``LogParseResultPGManager.add_log_parse_results`` 的 COPY 模式：
    在 ``PGManager.connection()``（SQLAlchemy ``engine.begin()``）事务内用
    asyncpg 原生 ``copy_records_to_table``；任一表失败整体回滚，杜绝
    部分表有数据、部分空的混合状态。

    Args:
        on_table: 可选回调 ``on_table(granularity, t_stage_start, n_rows)``，
            在每个表 delete+insert 结束后调用（主流程用于逐表打点）。
    """
    from latency.database.engine import PGManager  # 延迟导入，保持模块自包含

    async with PGManager.connection() as conn:
        raw = await conn.get_raw_connection()
        pg = raw.driver_connection
        for g in GRANULARITY_KEYS:
            t_table = time.perf_counter()
            table = tables[g]
            rows = rows_by_granularity[g]
            await pg.execute(f"DELETE FROM {table} WHERE log_id = $1", log_id)
            if rows:
                await pg.copy_records_to_table(
                    table, records=rows, columns=BUCKET_COLUMNS
                )
            if on_table is not None:
                await on_table(g, t_table, len(rows))


# ---------------------------------------------------------------------------
# 打点（进度上报）
# ---------------------------------------------------------------------------

async def _report(task_id: str | None, message: str, progress: float) -> None:
    """沿用 ``BaseWorker.report``；无 task_id 时静默跳过（测试 / 降级场景）。"""
    if not task_id:
        return
    try:
        from latency.task.worker.base import BaseWorker  # 延迟导入

        await BaseWorker.report(task_id, message, progress)
    except Exception as e:  # 打点失败不影响统计主流程
        logger.warning("[parse_log] Bucket stats report failed: %s", e)


async def _report_stage(
    task_id: str | None,
    t_stage_start: float,
    t_overall_start: float,
    label: str,
    extra: str = "",
) -> float:
    """阶段结束打点：耗时 + 占已流逝总时间的比例（与现有 [parse_log] 格式一致）。"""
    t = time.perf_counter() - t_stage_start
    elapsed = time.perf_counter() - t_overall_start
    pct = (t / elapsed * 100.0) if elapsed > 0 else 100.0
    await _report(task_id, f"[parse_log] Bucket stats: {label}: {t:.1f}s ({pct:.1f}%){extra}", t)
    return t


# ---------------------------------------------------------------------------
# 对外主入口
# ---------------------------------------------------------------------------

async def compute_and_store_bucket_stats_from_frame(
    df_trace,
    log_id: str,
    kb_id: str,
    task_id: str | None = None,
    tables: dict[int, str] | None = None,
    materializer: Any = None,
) -> dict[int, int]:
    """df_trace → 4 张统计表（T7 后唯一写库入口）。

    任一阶段异常先打 ``FAILED`` 点再 re-raise，由调用方（worker 的
    ``_store_bucket_stats_degraded``）降级记录日志。polars 计算是同步的，
    用 ``asyncio.to_thread`` 不让事件循环阻塞。

    Args:
        df_trace: T2 ``parse_log`` 产出的 polars DataFrame（每 trace 一行）。
        log_id / kb_id / task_id / tables / materializer: 语义与
            ``compute_bucket_stats_from_frame`` 同参一致。

    Returns:
        {granularity: 写入行数}。
    """
    tables = dict(tables) if tables else dict(DEFAULT_TABLES)
    t_overall = time.perf_counter()
    try:
        t0 = time.perf_counter()
        rows_by_granularity = await asyncio.to_thread(
            compute_bucket_stats_from_frame, df_trace, kb_id, log_id, materializer
        )
        await _report_stage(task_id, t0, t_overall, "polars percentile pick")

        async def _on_table(g: int, t_table: float, n_rows: int) -> None:
            await _report_stage(
                task_id, t_table, t_overall,
                f"merge + insert {GRANULARITY_LABELS[g]}",
                f" ({n_rows} rows)",
            )

        await _store_bucket_rows(
            log_id, rows_by_granularity, tables, on_table=_on_table
        )

        n_total = sum(len(r) for r in rows_by_granularity.values())
        await _report(
            task_id,
            f"[parse_log] Bucket stats: total: {time.perf_counter() - t_overall:.1f}s ({n_total} rows)",
            0.0,
        )
        return {g: len(rows_by_granularity[g]) for g in GRANULARITY_KEYS}
    except Exception as e:
        await _report(task_id, f"[parse_log] Bucket stats: FAILED: {e}", 100.0)
        logger.exception("[parse_log] Bucket stats FAILED: %s", e)
        raise
