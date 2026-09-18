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
    C3  组内按 total_latency 排序（``rank("ordinal")``）后取 4 分位代表行。
    C4  每档粒度产出一个 ``BUCKET_COLUMNS`` 形状的列式 frame（8 固定键 +
        14 legacy 指标 + 26 yuanrong 分段时延），4 张表 delete+insert 放一个
        事务（写库幂等）；COPY 由 ``log_parse_result_bulk.copy_dataframe``
        完成（P3 取代原先在主进程拼 48 列 tuple 的逐行写法）。

T7 已删除 numpy / shared_memory / multiprocessing.spawn 旧实现
（``_filter_and_build_arrays`` / ``_parallel_pick`` / ``_pick_segment_worker``
/ ``_split_into_segments`` / ``compute_and_store_bucket_stats``）。

模块自包含：只依赖 schemas/engine/base 与 database.utils；不 import parse worker。
"""
from __future__ import annotations

import asyncio
import logging
import math
import time
from typing import TYPE_CHECKING, Any

import numpy as np

from latency.schemas.log import YUANRONG_METRIC_FIELDS

if TYPE_CHECKING:
    # F821: polars 只出现在返回注解（本模块运行时惰性 import polars）
    import polars as pl

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

# Phase 1（定序 + 取分位位次）实际读到的列：桶号由 bucket_epoch 现算，
# 代表行落地只需要 tid / src / dst + 14 个时延列，其余列不参与排序与取位次。
_SORT_COLUMNS: tuple[str, ...] = (
    "bucket_epoch",
    "_op_code",
    "tid",
    "src",
    "dst",
    *METRIC_KEYS,
)

# 4 种分位模式：(模式名, 分位点)。pmax=1.0 → floor(cnt*1)-1 = cnt-1（最大值行）。
PERCENTILE_MODES: tuple[tuple[str, float], ...] = (
    ("median", 0.5),
    ("p99", 0.99),
    ("p9999", 0.9999),
    ("pmax", 1.0),
)

# 统计表 COPY 列（8 个固定键 + 14 个 legacy 时延指标 + 26 个 yuanrong 分段
# 时延），与正式表 DDL 列序一致。
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
    *YUANRONG_METRIC_FIELDS,
)

# df_trace 中 yuanrong 内部原材料列（``_yuanrong_from_grouped`` 的输入），
# 用于判断 df_trace 是否携带可计算的 yuanrong 分段时延。
_YUANRONG_INTERNAL_COLS: tuple[str, ...] = (
    "__se", "__sop", "__we", "__ue", "__ui", "__cn", "__ce", "__cs", "__cnw",
    "__me", "__ms", "__mn", "__re", "__rs", "__rn", "__qm",
)

def _normalize_op(operation: Any) -> int:
    """归一化 handle → GET/SET 编码：含 'GET' 字样的 handle 视为 GET(0)，
    其余（SET/CREATE/PUBLISH/其他）一律视为 SET(1)。与 parse worker 的
    SDK_GET_OPS / WORKER_GET_OPS 语义一致（DS_KV_CLIENT_GET、DS_POSIX_GET
    等原始 handle 名，见计划 C2）。
    """
    op = operation or ""
    return 0 if "GET" in op.upper() else 1


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
    """每 (桶, op) 组内 4 个分位在排序后行中的相对位置（0-based）。

    用 ``math.floor(cnt*p) - 1`` 而非 ``round()``：round 是 banker's rounding
    （round(2.5)=2），会 off-by-one。结果 clamp 到 [0, cnt-1] 防越界
    （cnt>=1 时 floor(1*0.5)-1=-1 → 0；pmax 恒为 cnt-1）。
    小桶（如 cnt=2）时多个分位可能落同一行，允许重复（语义：小桶内
    p99≈p9999≈pmax 同请求，写库时不同 mode 是不同行）。
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
    """对一组 (桶, op) 的延迟数组用 argpartition 一次选出 4 个分位代表行。

    Args:
        latency_slice: 该组所有行的 total_latency（无需预排序，argpartition
            内部处理；O(n) 非全排序，一次拿 4 个 kth）。
        kth_positions: 4 个分位位置，缺省时用 ``percentile_kth_positions``
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
# C4. 写库（P3: 分位代表行 frame -> log_parse_result_bulk.copy_dataframe）
# ---------------------------------------------------------------------------

def _empty_bucket_frame():
    """0 行、列名 == ``BUCKET_COLUMNS`` 的空 frame（空粒度 / 无可统计行）。

    ``copy_dataframe`` 对 0 行 frame 不产生 COPY，因此只有列名有意义。
    """
    import polars as pl

    return pl.DataFrame({name: [] for name in BUCKET_COLUMNS})


def compute_bucket_stats_from_frame(
    df_trace,
    kb_id: str = "",
    log_id: str = "",
) -> dict[int, Any]:
    """纯 polars 分位代表行选择（T7 后唯一选择路径，含 yuanrong 富化）。

    语义（与 numpy 参考实现逐字段一致，见 T4 parity 测试）：
    - C0 过滤：``bucket_epoch``（= trace 时间戳的 10s 对齐 epoch 秒；非空
      即时间戳可解析）与 ``total_ms`` 非空的行才参与。
    - 组键：(bucket_id, op_code)。bucket_id = ``bucket_epoch // g`` ——
      10 整除 60/600/3600，故 10s 对齐 epoch 整除粒度 == 原时间戳整除粒度，
      桶起点与墙钟对齐一致。op_code 复用 ``_normalize_op`` 语义
      （含 "GET" → 0，其余含 None → 1）。
    - 代表行：组内按 ``total_latency`` 排序（``rank("ordinal")``，并列按
      行序稳定断结）后取 ``percentile_kth_positions(cnt)`` 指定的 kth 位置行。
      实现上（A2）先投影到 ``_SORT_COLUMNS`` 只排一次序，再按档用 window
      取位次，语义与逐档 ``sort()`` 一致。
    - yuanrong 富化（Phase 2）：对 4 档粒度收集到的代表 trace_id 去重后，
      仅当 df_trace 携带 ``_YUANRONG_INTERNAL_COLS`` 内部列时调用
      ``_yuanrong_from_grouped`` 一次算出 26 项分段时延，再按 tid 并入代表行
      （4 档粒度共用同一份 lookup，不重复计算）。

    P3 起产出**列式 frame**（不再是 48 列 tuple）：列名 == ``BUCKET_COLUMNS``、
    取值语义与原 ``_representative_tuple`` 逐字段一致，交给
    ``log_parse_result_bulk.copy_dataframe`` 做类型归一化（INET / TIMESTAMP）
    与 COPY。行序仍为「粒度 (10,60,600,3600) × 模式
    (median,p99,p9999,pmax) × df 行序」，与原实现相同。

    Args:
        df_trace: T2 ``parse_log`` 产出的 polars DataFrame（TRACE_COLUMNS
            + yuanrong 内部列，每 trace 一行）。
        kb_id / log_id: 写库冗余键（frame 前两列）。

    Returns:
        {granularity: polars.DataFrame}，4 档各一份，可直接喂 ``_store_bucket_rows``。
    """
    import polars as pl

    from latency.parse.parallel_scanner.trace_frame import _yuanrong_from_grouped

    df = df_trace.filter(
        pl.col("bucket_epoch").is_not_null()
        & pl.col("total_ms").is_not_null()
    )
    if df.height == 0:
        return {g: _empty_bucket_frame() for g in GRANULARITY_KEYS}

    df = df.with_columns(
        pl.when(pl.col("operation").str.contains("GET", literal=True))
        .then(pl.lit(0, dtype=pl.Int64))
        .otherwise(pl.lit(1, dtype=pl.Int64))
        .alias("_op_code"),
    )

    # ── Phase 1: collect all representative rows (in df row order) ───
    # ① 投影：排序只看 _SORT_COLUMNS（19 列），不再对 49 列全宽排序
    #    （本机 kv218 实测：50 列裸排序 0.95s → 投影 19 列 0.30s）。
    # ② 一次排序服务 4 档：组内相对序只由 (total_latency, tid) 决定
    #    （_bucket_id / _op_code 是分组键，组内恒定），故按 (total_latency, tid)
    #    全局定序后，每个 (桶, op) 组内的相对序与原来每档
    #    sort(["_bucket_id", "_op_code", "total_latency", "tid"]) 完全一致，
    #    代表行仍与输入行序无关（total_latency 并列时由 tid 断结）。
    # ③ 各档改为在**同一个**已定序帧上用 window 取 rank("ordinal") / pl.len()，
    #    不再每档各排一次全量；本机 kv218 实测 Phase 1 合计 4.76s → 1.31s
    #    （整个分桶函数 6.54s → 3.11s，其余是未改动的 Phase 2/3）。
    df_ord = df.select(_SORT_COLUMNS).sort(["total_latency", "tid"], nulls_last=True)

    pending: list[dict[str, Any]] = []
    for g in GRANULARITY_KEYS:
        dg = df_ord.with_columns((pl.col("bucket_epoch") // g).alias("_bucket_id"))
        dg = dg.with_columns(
            pl.col("total_latency")
            .rank("ordinal")
            .over(["_bucket_id", "_op_code"])
            .cast(pl.Int64)
            .alias("_rank"),
            pl.len().over(["_bucket_id", "_op_code"]).alias("_cnt"),
        )
        for mode_name, p in PERCENTILE_MODES:
            # kth rank（1-based）= max(1, min(floor(cnt*p), cnt))，与
            # percentile_kth_positions 的 0-based 位置 +1 完全一致（pmax→cnt）。
            kth_rank = (
                (pl.col("_cnt").cast(pl.Float64) * p)
                .floor()
                .cast(pl.Int64)
                .clip(lower_bound=1, upper_bound=pl.col("_cnt"))
            )
            # 取中的行散布在 (total_latency, tid) 全局序里，按 (桶, op) 复原原行序：
            # 每个 (桶, op) 每个模式恰一行，(桶, op) 即全序。
            hit = dg.filter(pl.col("_rank") == kth_rank).sort(
                ["_bucket_id", "_op_code"]
            )
            for row in hit.iter_rows(named=True):
                # 桶起点 = 桶号 * 粒度（epoch 秒，与 compute_bucket_ids 同源）。
                bucket_start_dt = np.datetime64(
                    int(row["_bucket_id"]) * g, "s"
                ).item()
                pending.append({
                    "g": g,
                    "bucket_dt": bucket_start_dt,
                    "op_code": int(row["_op_code"]),
                    "mode": mode_name,
                    "row": row,
                    "tid": row.get("tid"),
                })

    # ── Phase 2: yuanrong enrichment (dedup across all granularities) ─
    rep_tids: set[Any] = {p["tid"] for p in pending if p["tid"]}
    yr_lookup: dict[Any, dict[str, Any]] = {}
    if rep_tids and all(c in df.columns for c in _YUANRONG_INTERNAL_COLS):
        rep_df = df.filter(pl.col("tid").is_in(rep_tids))
        if rep_df.height > 0:
            yr = _yuanrong_from_grouped(rep_df)
            yr_lookup = {
                r["tid"]: {name: r[name] for name in YUANRONG_METRIC_FIELDS}
                for r in yr.iter_rows(named=True)
            }

    # ── Phase 3: 每档粒度一个 BUCKET_COLUMNS 形状的 frame ─────────────
    records: dict[int, list[dict[str, Any]]] = {g: [] for g in GRANULARITY_KEYS}
    for item in pending:
        row = item["row"]
        yrow = yr_lookup.get(item["tid"]) if item["tid"] else None
        records[item["g"]].append({
            "kb_id": kb_id,
            "log_id": log_id,
            "bucket": item["bucket_dt"],
            "operation": "GET" if item["op_code"] == 0 else "SET",
            "mode": item["mode"],
            # tid -> trace_id / src -> src_ip / dst -> dst_ip（INET 归一化交
            # 给 copy_dataframe 的 parse_ip，与原 _representative_tuple 同源）
            "trace_id": row.get("tid"),
            "src_ip": row.get("src"),
            "dst_ip": row.get("dst"),
            **{name: row.get(name) for name in METRIC_KEYS},
            **{
                name: (yrow.get(name) if yrow else None)
                for name in YUANRONG_METRIC_FIELDS
            },
        })
    return {g: _frame_from_records(records[g]) for g in GRANULARITY_KEYS}


def _frame_from_records(rows: list[dict]) -> pl.DataFrame:
    """按**全量**推断 + 对 double 列显式给 schema 建帧。

    原实现 ``pl.DataFrame(rows)`` 默认只拿前 100 行推断类型：时延列前 100 行恰好都是
    整数（例如 1），第 101 行出现 408.0 就抛
        ComputeError: could not append value: 408.0 of type f64
    该异常被 ``_store_bucket_stats_degraded`` 捕获后**只记日志**，任务报告却仍打
    ``latency_bucket_* written`` → 4 张分桶表 0 行、前端"暂无时延数据"。
    这里改成 full inference + 按数据库列型（double precision）显式覆盖浮点列。
    """
    import polars as pl

    if not rows:
        return _empty_bucket_frame()
    float_cols = set(METRIC_KEYS) | (set(YUANRONG_METRIC_FIELDS) - {"request_mode"})
    return pl.DataFrame(
        rows,
        infer_schema_length=None,
        schema_overrides={name: pl.Float64 for name in float_cols},
    )



async def _store_bucket_rows(
    log_id: str,
    frames_by_granularity: dict[int, Any],
    tables: dict[int, str],
    on_table: Any | None = None,
) -> None:
    """4 张表 ``DELETE WHERE log_id=?`` + COPY 放一个事务（写库幂等）。

    COPY 走列式批量模块（``log_parse_result_bulk.copy_dataframe``，``pg_conn``
    复用本函数持有的事务）：任一表失败整体回滚，杜绝部分表有数据、部分空的
    混合状态；行序 = frame 行序（即分位代表行的选取序）。

    Args:
        frames_by_granularity: {粒度: ``BUCKET_COLUMNS`` 形状的 polars DataFrame}。
        on_table: 可选回调 ``on_table(granularity, t_stage_start, n_rows)``，
            在每个表 delete+insert 结束后调用（主流程用于逐表打点）。
    """
    from latency.database.engine import PGManager  # 延迟导入，保持模块自包含
    from latency.database.managers.log_parse_result_bulk import (
        BUCKET_SPECS,
        copy_dataframe,
    )

    async with PGManager.connection() as conn:
        raw = await conn.get_raw_connection()
        pg = raw.driver_connection
        for g in GRANULARITY_KEYS:
            t_table = time.perf_counter()
            table = tables[g]
            frame = frames_by_granularity[g]
            await pg.execute(f"DELETE FROM {table} WHERE log_id = $1", log_id)
            # type_source 仍指向 ORM 表（列类型 / NOT NULL 真源），只换目标表名
            await copy_dataframe(frame, BUCKET_SPECS[g].with_table(table), pg_conn=pg)
            if on_table is not None:
                await on_table(g, t_table, frame.height)


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
    stage_timer: Any | None = None,
) -> dict[int, int]:
    """df_trace → 4 张统计表（T7 后唯一写库入口）。

    任一阶段异常先打 ``FAILED`` 点再 re-raise，由调用方（worker 的
    ``_store_bucket_stats_degraded``）降级记录日志。polars 计算是同步的，
    用 ``asyncio.to_thread`` 不让事件循环阻塞。

    Args:
        df_trace: T2 ``parse_log`` 产出的 polars DataFrame（每 trace 一行）。
        log_id / kb_id / task_id / tables: 语义与
            ``compute_bucket_stats_from_frame`` 同参一致。
        stage_timer: 可选 ``latency.common.stage_timing.StageTimer``（None = 不
            打结构化耗时）。按调用边界登记两个阶段：``bucket`` = polars 选代表行
            （计算部分）、``store`` = 4 张表的 delete+insert（插入部分）。

    Returns:
        {granularity: 写入行数}。
    """
    tables = dict(tables) if tables else dict(DEFAULT_TABLES)
    # 延迟导入：保持本模块"只依赖 schemas/engine/base"的自包含性
    from latency.common.stage_timing import as_stage_timer

    timer = as_stage_timer(stage_timer)
    t_overall = time.perf_counter()
    try:
        t0 = time.perf_counter()
        # [timing] bucket = 分桶代表行计算（不碰 DB）
        with timer.stage("bucket") as bucket_scope:
            frames_by_granularity = await asyncio.to_thread(
                compute_bucket_stats_from_frame, df_trace, kb_id, log_id
            )
            bucket_scope.detail = (
                f"{len(GRANULARITY_KEYS)} 粒度 / "
                f"{sum(f.height for f in frames_by_granularity.values())} 代表行"
            )
        await _report_stage(task_id, t0, t_overall, "polars percentile pick")

        async def _on_table(g: int, t_table: float, n_rows: int) -> None:
            await _report_stage(
                task_id, t_table, t_overall,
                f"merge + insert {GRANULARITY_LABELS[g]}",
                f" ({n_rows} rows)",
            )

        # [timing] store = 写库插入（4 张表一个事务里的 DELETE + COPY）
        with timer.stage("store"):
            await _store_bucket_rows(
                log_id, frames_by_granularity, tables, on_table=_on_table
            )

        n_total = sum(f.height for f in frames_by_granularity.values())
        await _report(
            task_id,
            f"[parse_log] Bucket stats: total: {time.perf_counter() - t_overall:.1f}s "
            f"({n_total} rows)",
            0.0,
        )
        return {g: frames_by_granularity[g].height for g in GRANULARITY_KEYS}
    except Exception as e:
        await _report(task_id, f"[parse_log] Bucket stats: FAILED: {e}", 100.0)
        logger.exception("[parse_log] Bucket stats FAILED: %s", e)
        raise
