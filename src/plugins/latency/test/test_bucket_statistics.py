# Copyright (c) Huawei Technologies Co., Ltd. 2023-2025. All rights reserved.
"""分位桶统计模块单测（计划 Phase 1 任务 2-5 + T4/T7 验收）。

覆盖：
  1. compute_bucket_ids：手算桶号 / 跨天不碰撞 / 无 8h 偏移 / NaT 过滤
  2. 分位代表行：手算 floor(cnt*p)-1 索引（奇数桶 cnt=5、小桶 cnt=2、cnt=1 边界）
  3. numpy 参考复刻（本文件保留的等价参考）== polars frame 路径：
     四档粒度 rep-rows 全等（P3 起生产直接产出列式 frame，无 materializer）
  4. 写库幂等：临时表（与正式表同构 DDL）两次 run 同 log_id 行数相同
  5. 失败降级：_store_bucket_stats_degraded 异常仅记日志返回 None

运行：cd src/plugins/latency && PYTHONPATH=/home/li/witty-ub_8632/src/plugins \
  .venv/bin/python -m pytest test/test_bucket_statistics.py -v -p no:cacheprovider
"""
from __future__ import annotations

import os
import uuid
from datetime import datetime, timedelta

import numpy as np
import pytest
from sqlalchemy import text

from latency.bucket.statistics import (
    BUCKET_COLUMNS,
    GRANULARITY_KEYS,
    GRANULARITY_LABELS,
    METRIC_KEYS,
    PERCENTILE_MODES,
    _group_edges,
    _normalize_op,
    compute_bucket_stats_from_frame,
    compute_bucket_ids,
    percentile_kth_positions,
    pick_percentile_rows,
)
from latency.database.engine import PGManager
from latency.schemas.log import (
    YUANRONG_METRIC_FIELDS,
    LogParseResultDataclass,
    SparseLogParseResultDataclass,
)

PG_DSN = os.getenv(
    "LATENCY_PG_DSN",
    "postgresql://witty-ub:witty-ub@127.0.0.1:5432/witty-ub",
)

# 与正式表同构的临时表 DDL（无分区；测试自建自删，避免与建表任务竞争）。
_BUCKET_TEST_DDL = """
CREATE TABLE IF NOT EXISTS {tbl} (
    kb_id         varchar(64)   NOT NULL,
    log_id        varchar(64)   NOT NULL,
    bucket        timestamp     NOT NULL,
    operation     varchar(16)   NOT NULL,
    mode          varchar(8)    NOT NULL,
    src_ip        inet,
    dst_ip        inet,
    trace_id      varchar(64),
    total_latency float,
    urma_total_latency float,
    worker_query_meta_latency float,
    sdk_process float, sdk_rpc float,
    local_worker_cost float, local_worker_lock float,
    remote_worker_cost float, remote_worker_rpc float,
    master_process float, master_rpc_total float,
    create_latency float, publish_latency float,
    worker_total_latency float,
    total_latency_us float,
    request_mode varchar(16),
    sdk_processing_us float, master_processing_us float,
    worker_access_latency_us float,
    remote_worker_internal_us float,
    local_worker_internal_us float, local_worker_internal_active_us float,
    sdk_rpc_network_us float, sdk_rpc_framework_us float, sdk_rpc_total_us float,
    master_rpc_network_us float, master_rpc_framework_us float, master_rpc_total_us float,
    remote_worker_rpc_network_us float, remote_worker_rpc_framework_us float,
    remote_worker_rpc_total_us float,
    urma_processing_us float, urma_inflight_max integer,
    remote_worker_processing_us float,
    client_master_rpc_network_us float, client_master_rpc_framework_us float,
    client_master_rpc_total_us float,
    client_remote_rpc_network_us float, client_remote_rpc_framework_us float,
    client_remote_rpc_total_us float,
    PRIMARY KEY (log_id, bucket, operation, mode)
)
"""


def _make_row(
    i: int, ts: str | None, op: str, latency: float, sparse: bool = False
):
    """构造一行 LogParseResultDataclass / Sparse（sparse 行 src/dst 为 ClassVar None）。"""
    kw = dict(
        total_latency=latency,
        is_anomalous=False,
        log_id="lg",
        timestamp=ts,
        operation=op,
        trace_id=f"tr-{i}",
    )
    if sparse:
        return SparseLogParseResultDataclass(**kw)
    return LogParseResultDataclass(**kw)


# ---------------------------------------------------------------------------
# 1. compute_bucket_ids：手算桶号 / 跨天唯一 / 无 8h 偏移 / NaT 过滤
# ---------------------------------------------------------------------------

def test_compute_bucket_ids_hand_computed_and_cross_day():
    # 已知时间戳 → 绝对 epoch 秒手算桶号。
    # 基准：2026-05-10 10:00:00 的墙钟 epoch = 1778407200（= 2026-05-10 的
    # 00:00:00 epoch 1778371200 + 10*3600；已与 stdlib
    # datetime(..., tzinfo=timezone.utc).timestamp() 交叉验证一致）。
    ts = np.array(
        [
            np.datetime64("2026-05-10 10:00:00"),
            np.datetime64("2026-05-10 10:00:07"),
            np.datetime64("2026-05-10 10:01:30"),
        ]
    )
    # 10:00:00 → epoch 1778407200；10:01:30 → +90s = 1778407290。
    #   10s 桶：1778407200//10=177840720；1778407290//10=177840729
    #   60s 桶：1778407200//60=29640120；1778407290//60=29640121
    #   3600s 桶：两者都落在 10:00 的整点桶 1778407200//3600=494002
    assert list(compute_bucket_ids(ts, 10)) == [177840720, 177840720, 177840729]
    assert list(compute_bucket_ids(ts, 60)) == [29640120, 29640120, 29640121]
    assert list(compute_bucket_ids(ts, 3600)) == [494002, 494002, 494002]

    # 跨天数据不碰撞：23:59:55 与次日 00:00:05 恰差 10s →
    # 10s 桶号差恰为 1（回归 BLOCKER：按天重置会产生 0 桶碰撞）。
    cross_day = np.array(
        [
            np.datetime64("2026-05-10 23:59:55"),
            np.datetime64("2026-05-11 00:00:05"),
        ]
    )
    b = compute_bucket_ids(cross_day, 10)
    assert int(b[1]) == int(b[0]) + 1

    # 本地墙钟语义：12:00:00 的桶起点是 12:00:00，不是 04:00:00（无 8h 偏移）。
    local = np.array(
        [
            np.datetime64("2026-05-10 12:00:00"),
            np.datetime64("2026-05-10 12:00:10"),
        ]
    )
    b = compute_bucket_ids(local, 10)
    assert str(np.datetime64(int(b[0]) * 10, "s")) == "2026-05-10T12:00:00"
    assert str(np.datetime64(int(b[1]) * 10, "s")) == "2026-05-10T12:00:10"

    # C0 防护语义：timestamp=None 的行不参与（frame 路径由 polars
    # ``bucket_epoch.is_not_null()`` 过滤承担；compute_bucket_ids 只收已过滤数组）。
    ts_arr = np.array(
        ["2026-05-10 12:00:00", "2026-05-10 12:00:05"],
        dtype="datetime64[s]",
    )
    assert all(int(x) >= 0 for x in compute_bucket_ids(ts_arr, 10))


def test_op_normalization_real_handle_names():
    """MAJOR 1 回归：parse 结果 operation 为完整 handle 名，须按语义归一化。

    DS_KV_CLIENT_GET / DS_POSIX_GET 等含 "GET" → GET=0；SET/CREATE/PUBLISH
    及空串 → SET=1。字面量 "GET"/"SET" 用例保持兼容（含 GET → 0）。
    """
    # 直接测 _normalize_op 边界。
    assert _normalize_op("DS_KV_CLIENT_GET") == 0
    assert _normalize_op("DS_OBJECT_CLIENT_GET") == 0
    assert _normalize_op("DS_POSIX_GET") == 0
    assert _normalize_op("DS_KV_CLIENT_SET") == 1
    assert _normalize_op("DS_POSIX_CREATE") == 1
    assert _normalize_op("DS_POSIX_PUBLISH") == 1
    assert _normalize_op(None) == 1
    assert _normalize_op("") == 1
    assert _normalize_op("GET") == 0
    assert _normalize_op("SET") == 1


def test_compute_bucket_ids_wall_clock_alignment_non_aligned_start():
    """回归：数据起点非整桶秒（如 12:47:24）时，桶边界仍须墙钟对齐。

    旧实现以 ts.min() 为锚点，起点漂移导致桶起点 12:47:24/12:47:34…；
    本测试锁定墙钟对齐（10s→:20/:30/:40，60s→:00，3600s→整点），
    与回退实时 SQL 的 date_trunc 对齐语义一致（计划任务 16b）。
    """
    ts = np.array(
        [
            np.datetime64("2026-05-10 12:47:24"),
            np.datetime64("2026-05-10 12:47:33"),
            np.datetime64("2026-05-10 12:47:41"),
        ]
    )
    b10 = compute_bucket_ids(ts, 10)
    starts10 = [str(np.datetime64(int(x) * 10, "s")) for x in b10]
    assert starts10 == [
        "2026-05-10T12:47:20",
        "2026-05-10T12:47:30",
        "2026-05-10T12:47:40",
    ]
    b60 = compute_bucket_ids(ts, 60)
    assert str(np.datetime64(int(b60[0]) * 60, "s")) == "2026-05-10T12:47:00"
    b3600 = compute_bucket_ids(ts, 3600)
    assert str(np.datetime64(int(b3600[0]) * 3600, "s")) == "2026-05-10T12:00:00"


# ---------------------------------------------------------------------------
# 2. pick_percentile_rows：手算 floor(cnt*p)-1 索引
# ---------------------------------------------------------------------------

def test_pick_percentile_rows_hand_computed():
    # 100 行严格递增：排序位置 k 的行索引就是 k
    lat100 = np.arange(100, dtype=np.float64)
    kth100 = percentile_kth_positions(100)
    # 手算 floor(cnt*p)-1：median=49, p99=98, p9999=98, pmax=99
    assert kth100 == [49, 98, 98, 99]
    assert pick_percentile_rows(lat100) == [49, 98, 98, 99]

    # 奇数桶 cnt=5：[0,1,2,3,4] 手算
    #   median floor(2.5)-1=1；p99 floor(4.95)-1=3；p9999 floor(4.9995)-1=3；
    #   pmax floor(5)-1=4
    kth5 = percentile_kth_positions(5)
    assert kth5 == [1, 3, 3, 4]
    assert pick_percentile_rows(np.arange(5, dtype=np.float64)) == [1, 3, 3, 4]

    # 小桶 cnt=2：[10, 20] → median/p99/p9999 同落 index0，pmax=index1
    kth2 = percentile_kth_positions(2)
    assert kth2 == [0, 0, 0, 1]
    assert pick_percentile_rows(np.array([10.0, 20.0])) == [0, 0, 0, 1]

    # cnt=1 边界：全 clamp 到 0（防 floor(0.5)-1=-1 越界）
    assert percentile_kth_positions(1) == [0, 0, 0, 0]

    # mode 列名与顺序
    assert [m for m, _ in PERCENTILE_MODES] == [
        "median", "p99", "p9999", "pmax",
    ]


# ---------------------------------------------------------------------------
# 4. 写库幂等：临时表两次 run 同 log_id 行数相同
# ---------------------------------------------------------------------------

async def _count_rows(table: str, log_id: str) -> int:
    async with PGManager.session() as session:
        r = await session.execute(
            text("SELECT count(*) FROM " + table + " WHERE log_id = :log_id"),
            {"log_id": log_id},
        )
        return int(r.scalar())


async def _count_distinct_pk(table: str, log_id: str) -> int:
    async with PGManager.session() as session:
        r = await session.execute(
            text(
                "SELECT count(*) FROM (SELECT DISTINCT log_id, bucket, operation, mode"
                " FROM " + table + " WHERE log_id = :log_id) t"
            ),
            {"log_id": log_id},
        )
        return int(r.scalar())


# ---------------------------------------------------------------------------
# 5. Todo 5 — 换源（字段表）+ 失败降级
# ---------------------------------------------------------------------------

def _sdk_tuple(tid: str, op: str, elapsed_us: int, status: int, ts: str):
    """SDK entry 16 元组（TupleField 顺序），与 trace_index 切片的字段表来源一致。"""
    return (ts, op, elapsed_us, None, None, tid, "10.0.0.9", status, None, None,
            None, None, None, None, None, "log1")


def _urma_tuple(tid: str, src: str, dst: str):
    return ("2026-05-10 10:00:00", "URMA", 400, None, None, tid, None, 0, None,
            None, None, src, dst, None, None, "log1")


def _trace_index_fixture(n: int = 400):
    """trace_index fixture：n 个 trace，SDK entry 顺序，时间戳按秒递增。"""
    from datetime import datetime, timedelta

    base = datetime(2026, 5, 10, 10, 0, 0)
    trace_index: dict[str, dict[str, list]] = {}
    for i in range(n):
        ts = (base + timedelta(seconds=i)).strftime("%Y-%m-%d %H:%M:%S")
        op = "GET" if i % 2 == 0 else "SET"
        tid = f"ft-{i}"
        trace_index[tid] = {
            "SDK access parse": [_sdk_tuple(tid, op, 1000 + i, 0, ts)],
            "Worker urma parse": [_urma_tuple(tid, "10.0.0.1", "10.0.0.2")],
        }
    return trace_index


def _serial_pick(order, latency, per_gran):
    """串行 numpy 参考实现（T7 后 _parallel_pick 已删，用保留原语复刻）。

    与旧 ``_pick_segment_worker`` 单段语义一致：每 (桶, op) 组按
    ``pick_percentile_rows`` 取 5 个分位代表行 → (组下标, mode, 原始行索引)。
    """
    reps: dict[int, list[tuple[int, int, int]]] = {g: [] for g in per_gran}
    for g, (_, edges, _, _) in per_gran.items():
        for gi in range(len(edges) - 1):
            s, e = int(edges[gi]), int(edges[gi + 1])
            if e - s <= 0:
                continue
            for midx, rel in enumerate(pick_percentile_rows(latency[order[s:e]])):
                reps[g].append((gi, midx, int(order[s + rel])))
    return reps


def _pick_reps(rows):
    """字段表行 → (valid_rows, per_granularity, reps)（numpy 参考，不写库）。

    C0 过滤与 op 归一化在测试内联实现（生产已由 polars frame 路径承担），
    只复用保留的 ``compute_bucket_ids`` / ``_group_edges`` / ``pick_percentile_rows``。
    """
    timestamps = np.array(
        [r.timestamp for r in rows], dtype="datetime64[s]"
    )
    latency = np.array([r.total_latency for r in rows], dtype=np.float64)
    op_codes = np.array([_normalize_op(r.operation) for r in rows], dtype=np.int64)
    bucket10 = compute_bucket_ids(timestamps, 10)
    order = np.lexsort((bucket10, op_codes))
    per_gran = {}
    for g in GRANULARITY_KEYS:
        per_gran[g] = _group_edges(
            compute_bucket_ids(timestamps, g), op_codes, order
        )
    return rows, per_gran, _serial_pick(order, latency, per_gran)


# ---------------------------------------------------------------------------
# 3b. numpy 参考代表行（P3 起生产已删 _representative_tuple / _build_bucket_rows，
#     本文件保留一份等价参考实现，保证 T4 parity 测试的覆盖率不下降）
# ---------------------------------------------------------------------------

def _ip_str(value) -> str | None:
    """``parse_ip`` 归一化后的字符串形式（两侧比对的共同口径）。"""
    from latency.database.utils import parse_ip

    parsed = parse_ip(value)
    return None if parsed is None else str(parsed)


def _np_representative_tuple(kb_id, log_id, bucket_start_dt, op_code, mode_name, r):
    """旧生产 ``_representative_tuple`` 的等价参考（48 列，src/dst 走 parse_ip）。"""
    return (
        kb_id,
        log_id,
        bucket_start_dt,
        "GET" if op_code == 0 else "SET",
        mode_name,
        _ip_str(getattr(r, "src_ip", None)),
        _ip_str(getattr(r, "dst_ip", None)),
        getattr(r, "trace_id", None),
        *(getattr(r, name, None) for name in METRIC_KEYS),
        *(getattr(r, name, None) for name in YUANRONG_METRIC_FIELDS),
    )


def _np_build_bucket_rows(valid_rows, per_granularity, reps, kb_id, log_id):
    """旧生产 ``_build_bucket_rows`` 的等价参考（numpy 选取 + tuple 拼装）。"""
    rows_by_granularity: dict[int, list[tuple]] = {}
    for g in GRANULARITY_KEYS:
        _, _, ops, buckets = per_granularity[g]
        rows: list[tuple] = []
        for gid, mode_idx, orig in reps[g]:
            mode_name = PERCENTILE_MODES[mode_idx][0]
            bucket_start_dt = np.datetime64(int(buckets[gid]) * g, "s").item()
            rows.append(
                _np_representative_tuple(
                    kb_id, log_id, bucket_start_dt, int(ops[gid]), mode_name,
                    valid_rows[orig],
                )
            )
        rows_by_granularity[g] = rows
    return rows_by_granularity


def _frame_rows_as_tuples(frame) -> list[tuple]:
    """代表行 frame → ``BUCKET_COLUMNS`` 顺序的 tuple（src/dst 归一为字符串）。

    frame 里 src_ip/dst_ip 是原始字符串（INET 归一化在生产由
    ``log_parse_result_bulk.copy_dataframe`` 承担），参考路径给的是 ``parse_ip``
    产物，故两侧都按 ``str()`` 归一后比较。
    """
    from latency.database.managers.log_parse_result_bulk import (
        BUCKET_COLUMNS as _BULK_COLUMNS,
    )

    columns = list(_BULK_COLUMNS)
    out: list[tuple] = []
    for row in frame.select(columns).iter_rows():
        values = list(row)
        for index, name in enumerate(columns):
            if name in ("src_ip", "dst_ip"):
                values[index] = _ip_str(values[index])
        out.append(tuple(values))
    return out


def _trace_index_to_labeled(trace_index):
    """3 层 {trace_id: {label: [entries]}} → {label: [entries]} (扫描产物形态)。"""
    by_label: dict[str, list] = {}
    for labels in trace_index.values():
        for label, entries in labels.items():
            by_label.setdefault(label, []).extend(entries)
    return by_label


def test_bucket_percentiles_match_golden_field_table_source():
    """分位值 == golden fixture：单 (桶,op) 组 100 行 latency 严格递增 [0..99]，
    代表行的 total_latency 可手算 floor(cnt*p)-1（median=49, p99=98, p9999=98,
    pmax=99）；timestamp 齐全 → 无 epoch-0 桶行。"""
    rows = [_make_row(i, "2026-05-10 12:00:00", "GET", float(i)) for i in range(100)]
    valid, per_gran, reps = _pick_reps(rows)
    by_gran = _np_build_bucket_rows(valid, per_gran, reps, "kb", "lg")

    expected = [49.0, 98.0, 98.0, 99.0]
    for g in GRANULARITY_KEYS:
        # BUCKET_COLUMNS[8] = total_latency；同组 4 个分位代表行
        lats = sorted(r[8] for r in by_gran[g])
        assert lats == expected, f"granularity {g} 分位值 != golden"
        # 4 个 mode 齐全且顺序稳定
        assert sorted(r[4] for r in by_gran[g]) == [
            "median", "p99", "p9999", "pmax",
        ]
        # 无 0 桶行：桶起点为 2026 年（epoch 远大于 0）
        assert all(r[2].year == 2026 for r in by_gran[g]), f"granularity {g} 含 0 桶行"


async def _count_zero_bucket_rows(table: str, log_id: str) -> int:
    async with PGManager.session() as session:
        r = await session.execute(
            text(
                "SELECT count(*) FROM " + table
                + " WHERE log_id = :log_id AND bucket <= '1970-01-02'::timestamp"
            ),
            {"log_id": log_id},
        )
        return int(r.scalar())


@pytest.mark.asyncio(loop_scope="session")
async def test_bucket_field_table_source_four_granularities_nonzero():
    """换源契约（T5/T7）：df_trace（T2 产物）经 run() 的降级包装喂
    _store_bucket_stats_degraded → 4 档粒度桶行数均 > 0 且无 0 桶行。"""
    from latency.task.worker.kv_cache_log_parse_worker import (
        KVCacheLogParseWorker,
    )

    suffix = uuid.uuid4().hex[:8]
    tables = {
        g: f"latency_bucket_test_{suffix}_{GRANULARITY_LABELS[g]}"
        for g in GRANULARITY_KEYS
    }
    PGManager.initialize(PG_DSN)
    try:
        try:
            async with PGManager.connection() as conn:
                for tbl in tables.values():
                    await conn.execute(text(_BUCKET_TEST_DDL.format(tbl=tbl)))
        except Exception as e:
            pytest.skip(f"PostgreSQL 不可达或建临时表失败（跳过写库测试）: {e}")

        df_trace = _frame_from_trace_index(_trace_index_fixture(400))
        assert df_trace.height == 400
        assert df_trace["bucket_epoch"].is_not_null().all()  # timestamp 齐全

        log_id = f"pg-fieldtbl-{datetime.now().strftime('%Y%m%d%H%M%S')}"
        counts = await KVCacheLogParseWorker._store_bucket_stats_degraded(
            log_id, "kb-ft", df_trace, task_id=None, tables=tables
        )
        assert counts is not None
        for g in GRANULARITY_KEYS:
            assert counts[g] > 0, f"{GRANULARITY_LABELS[g]} 桶行数应为正"
            assert await _count_rows(tables[g], log_id) == counts[g]
            assert await _count_zero_bucket_rows(tables[g], log_id) == 0
    finally:
        try:
            async with PGManager.connection() as conn:
                for tbl in tables.values():
                    await conn.execute(text(f"DROP TABLE IF EXISTS {tbl}"))
        except Exception:
            pass
        await PGManager.close()


@pytest.mark.asyncio(loop_scope="session")
async def test_bucket_failure_degrades_does_not_block_main_flow(monkeypatch):
    """失败降级（T5）：bucket 写库异常经 _store_bucket_stats_degraded 仅记录日志
    （返回 None），不向 run() 主流程抛异常。"""
    from latency.task.worker.kv_cache_log_parse_worker import (
        KVCacheLogParseWorker,
    )

    async def _boom(*args, **kwargs):
        raise RuntimeError("bucket failure injected")

    monkeypatch.setattr(
        "latency.task.worker.kv_cache_log_parse_worker.compute_and_store_bucket_stats_from_frame",
        _boom,
    )
    result = await KVCacheLogParseWorker._store_bucket_stats_degraded(
        "lg", "kb", _frame_from_trace_index(_trace_index_fixture(10)), task_id="tid"
    )
    assert result is None


# ---------------------------------------------------------------------------
# 6. T4 — df_trace（polars 路径）rep-rows == numpy 路径 rep-rows
# ---------------------------------------------------------------------------

def _frame_from_trace_index(trace_index):
    """3 层 trace_index fixture → df_trace（polars, T2 产物形态）。"""
    from latency.parse.parallel_scanner.columnar import entries_to_columns
    from latency.parse.parallel_scanner.trace_frame import build_trace_frame

    return build_trace_frame(
        entries_to_columns(_trace_index_to_labeled(trace_index))
    )


def test_bucket_stats_from_frame_matches_numpy_path():
    """T4 golden parity：df_trace（polars）rep-rows == numpy 参考路径 rep-rows。

    同一 trace_index 两条喂入路径（同数据）：
    - numpy 参考：_build_field_table_rows（dataclass）→ _pick_reps（保留原语
      复刻，含 compute_bucket_ids/_group_edges/pick_percentile_rows）+
      _np_build_bucket_rows（本文件保留的等价参考）
    - polars：build_trace_frame（df_trace）→ compute_bucket_stats_from_frame
      直接产出列式 frame（P3 起生产路径，materializer 已删）
    四档粒度 rep-rows 前 22 列整行 tuple 相等（同 kth positions → 同 rep
    trace_ids、同 14 METRIC_KEYS 值、同 src/dst/bucket_start）。
    """
    from latency.task.worker.kv_cache_log_parse_worker import (
        KVCacheLogParseWorker,
    )

    trace_index = _trace_index_fixture(300)
    flat = KVCacheLogParseWorker._build_flat_trace_index(
        _trace_index_to_labeled(trace_index)
    )
    dc_rows = KVCacheLogParseWorker._build_field_table_rows(flat, "opft")
    df_trace = _frame_from_trace_index(trace_index)

    # numpy 参考路径（T7 后用保留原语复刻：_serial_pick；P3 后生产实现已删，
    # 参考实现保留在本文件内）
    valid, per_gran, reps = _pick_reps(dc_rows)
    rows_np = _np_build_bucket_rows(valid, per_gran, reps, "kb", "lg")

    # polars 路径（P3：直接产出列式 frame，无 materializer 参数）
    frames_pl = compute_bucket_stats_from_frame(df_trace, kb_id="kb", log_id="lg")

    # 300 条 trace（每秒 1 条, GET/SET 交替）→ 1s 桶 300 个（每桶 1 trace×4 mode）
    # / 10s 桶 30 个 / 60s 桶 5 个 / 600s 与 1h 各 1 个桶；每 (桶,op) 组 4 个 mode
    # 代表行。
    assert {g: frames_pl[g].height for g in GRANULARITY_KEYS} == {
        1: 1200, 10: 240, 60: 40, 600: 8, 3600: 8,
    }
    for g in GRANULARITY_KEYS:
        # 前 22 列（8 固定键 + 14 legacy 指标）tuple 集合相等
        # （mode/trace_id/src/dst/bucket_start + 14 值）；yuanrong 33 列只走
        # polars 路径，numpy 参考不含，故只比前 22 列。
        legacy_np = {tuple(r[:22]) for r in rows_np[g]}
        got = {tuple(r[:22]) for r in _frame_rows_as_tuples(frames_pl[g])}
        assert got == legacy_np, f"granularity {g} rep-rows 不一致"
        assert len(frames_pl[g].columns) == len(BUCKET_COLUMNS) == 55
        # BUCKET_COLUMNS 里的 total_latency_us 由拷贝路径写库，frame 里应非空
        assert frames_pl[g]["total_latency_us"][0] is not None


@pytest.mark.asyncio(loop_scope="session")
async def test_bucket_stats_from_frame_db_write_idempotent():
    """T4 写库契约：df_trace 喂 _store_bucket_stats_degraded（polars 路径）→
    4 张表行数 > 0、同 log_id 两次 run 幂等（先删后插无重复）。"""
    from latency.task.worker.kv_cache_log_parse_worker import (
        KVCacheLogParseWorker,
    )

    suffix = uuid.uuid4().hex[:8]
    tables = {
        g: f"latency_bucket_test_{suffix}_{GRANULARITY_LABELS[g]}"
        for g in GRANULARITY_KEYS
    }
    PGManager.initialize(PG_DSN)
    try:
        try:
            async with PGManager.connection() as conn:
                for tbl in tables.values():
                    await conn.execute(text(_BUCKET_TEST_DDL.format(tbl=tbl)))
        except Exception as e:
            pytest.skip(f"PostgreSQL 不可达或建临时表失败（跳过写库测试）: {e}")

        df_trace = _frame_from_trace_index(_trace_index_fixture(400))
        log_id = f"pg-frame-{datetime.now().strftime('%Y%m%d%H%M%S')}"
        counts1 = await KVCacheLogParseWorker._store_bucket_stats_degraded(
            log_id, "kb-frame", df_trace, task_id=None, tables=tables
        )
        assert counts1 is not None
        counts2 = await KVCacheLogParseWorker._store_bucket_stats_degraded(
            log_id, "kb-frame", df_trace, task_id=None, tables=tables
        )
        assert counts1 == counts2
        for g in GRANULARITY_KEYS:
            assert counts1[g] > 0, f"{GRANULARITY_LABELS[g]} 桶行数应为正"
            assert await _count_rows(tables[g], log_id) == counts1[g]
            assert await _count_rows(tables[g], log_id) == await _count_distinct_pk(
                tables[g], log_id
            )
    finally:
        try:
            async with PGManager.connection() as conn:
                for tbl in tables.values():
                    await conn.execute(text(f"DROP TABLE IF EXISTS {tbl}"))
        except Exception:
            pass
        await PGManager.close()


def test_bucket_rep_rows_carry_yuanrong():
    """yuanrong 富化契约：代表行 tuple 带 33 项分段时延（55 列），
    BUCKET_COLUMNS[22]=total_latency_us 非空、[23]=request_mode 合法。"""
    df_trace = _frame_from_trace_index(_trace_index_fixture(300))
    frames = compute_bucket_stats_from_frame(df_trace, kb_id="kb", log_id="lg")
    for g in GRANULARITY_KEYS:
        frame = frames[g]
        assert frame.height > 0, f"{GRANULARITY_LABELS[g]} 应产生代表行"
        assert len(frame.columns) == len(BUCKET_COLUMNS) == 55
        assert frame["total_latency_us"][0] is not None
        assert frame["request_mode"][0] in ("remote", "local", "unknown")

def test_frame_from_records_survives_float_after_100_int_rows():
    """回归：前 100 行时延恰好是整数、第 101 行出现浮点 → 旧实现整批建帧失败，
    被降级包装吞掉后 4 张分桶表 0 行（前端"暂无时延数据"）。"""
    import polars as pl

    from latency.bucket.statistics import _frame_from_records

    rows = [{"total_latency": 1} for _ in range(100)]
    rows.append({"total_latency": 408.0})
    rows.append({"total_latency": 2})
    df = _frame_from_records(rows)
    assert df.height == 102
    assert df["total_latency"].dtype == pl.Float64
    assert df["total_latency"].to_list()[100] == 408.0


# ---------------------------------------------------------------------------
# 7. GET 传输类型拆分：local/remote 分位代表合并进单行（2026-10 回归）
#    分桶表主键 (log_id, bucket, operation, mode) 不允许同桶同分位 GET 两行，
#    因此整体分位代表保留 legacy 指标与公共分段，local/remote 网络/框架分段
#    改由各自传输类型的分位代表行补齐（缺失侧为 null → 前端自动过滤）。
# ---------------------------------------------------------------------------

def _qg_light_frame():
    """light df_trace 形态帧（列 = _LIGHT_TRACE_COLUMNS）：同 10s 桶 4 条 GET +
    1 条 SET。整体排序升序 tl-lo(250) < tr-lo(300) < tl-hi(450) < tr-hi(500)；
    local 组（非 UB）：tl-lo/tl-hi，remote 组（UB）：tr-lo/tr-hi。"""
    import polars as pl

    bucket = 1778407200  # 2026-05-10 10:00:00 的 10s 对齐 epoch 秒
    rows = [
        # tid,      total_latency, transport
        ("tr-hi",   500.0,         "UB"),
        ("tr-lo",   300.0,         "UB"),
        ("tl-hi",   450.0,         "Fabric"),
        ("tl-lo",   250.0,         "Fabric"),
        ("s-lo",    100.0,         None),   # SET：无 transportType
    ]
    return pl.DataFrame({
        "tid": [r[0] for r in rows],
        "total_ms": [r[1] for r in rows],
        "total_latency": [r[1] for r in rows],
        "src": ["10.0.0.1"] * len(rows),
        "dst": ["10.0.0.2"] * len(rows),
        "op_key": ["GET"] * 4 + ["SET"],
        "operation": ["GET"] * 4 + ["SET"],
        "bucket_epoch": [bucket] * len(rows),
        "log_id": ["lg"] * len(rows),
        "__qgt": [r[2] for r in rows],
    })


def test_select_bucket_representatives_splits_get_by_transport():
    """select_bucket_representatives：GET 组按 __qgt 分 local/remote 各选分位代表
    （tid_local/tid_remote），整体代表不变；SET 组两者恒 null。"""
    import polars as pl

    from latency.bucket.representatives import select_bucket_representatives

    frame = _qg_light_frame()
    selected = select_bucket_representatives(frame, granularities=(3600,))[3600]
    # GET / SET 两组 × 4 mode = 8 行；SET 组代表 tid 恒为 s-lo
    assert len(selected) == 8

    p99 = selected.filter(
        (pl.col("mode") == "p99") & (pl.col("tid") != "s-lo")
    ).to_dicts()[0]
    # 整体 p99 → tl-hi；local 组 p99 → tl-lo；remote 组 p99 → tr-lo
    assert p99["tid"] == "tl-hi"
    assert p99["tid_local"] == "tl-lo"
    assert p99["tid_remote"] == "tr-lo"

    pmax = selected.filter(
        (pl.col("mode") == "pmax") & (pl.col("tid") != "s-lo")
    ).to_dicts()[0]
    assert pmax["tid"] == "tr-hi"        # 整体 pmax → tr-hi
    assert pmax["tid_local"] == "tl-hi"  # local 组 pmax → tl-hi
    assert pmax["tid_remote"] == "tr-hi"  # remote 组 pmax → tr-hi

    # SET 组：tid_local/tid_remote 恒 null
    s_row = selected.filter(pl.col("tid") == "s-lo").to_dicts()[0]
    assert s_row["tid_local"] is None
    assert s_row["tid_remote"] is None


def _qg_df_trace():
    """手工 df_trace 形态帧（TRACE_COLUMNS 子集 + __ 原材料列）：让
    _yuanrong_from_grouped 能产出 query_get_local/remote 网络/框架分段。
    每 trace 的 client RPC 三字段（__ce0/__cs0/__cnw0）按 transport 归属：
    local(fw)=ce0-cs0-cnw0，remote(fw) 同式。"""
    import polars as pl

    bucket = 1778407200
    # tid, latency, transport, ce0, cs0, cnw0
    rows = [
        ("tr-hi", 500.0, "UB",     500.0, 100.0, 50.0),
        ("tr-lo", 300.0, "UB",     300.0, 60.0,  30.0),
        ("tl-hi", 450.0, "Fabric", 450.0, 90.0,  40.0),
        ("tl-lo", 250.0, "Fabric", 250.0, 50.0,  20.0),
    ]
    n = len(rows)
    # 全 null 列必须带 dtype：全 None 列表会被推断为 null 类型，_yuanrong_from_grouped
    # 里 (col - col).clip(0) 只接受物理数值类型。
    nullf = pl.Series([None] * n, dtype=pl.Float64)
    nulls = pl.Series([None] * n, dtype=pl.Utf8)
    return pl.DataFrame({
        "tid": [r[0] for r in rows],
        "bucket_epoch": [bucket] * n,
        "total_ms": [r[1] for r in rows],
        "total_latency": [r[1] for r in rows],
        "operation": ["GET"] * n,
        "src": ["10.0.0.1"] * n,
        "dst": ["10.0.0.2"] * n,
        "__se": [r[1] * 1000.0 for r in rows],
        "__sop": nulls, "__wsum": nullf, "__wmax": nullf, "__wn": nullf,
        "__umax": nullf, "__uimax": nullf, "__usched": nullf, "__cuma": nullf,
        "__cn": nullf, "__ce1": nullf, "__ce2esum": nullf,
        "__cs1": nullf, "__cnw1": nullf,
        "__me": nullf, "__ms": nullf, "__mn": nullf,
        "__re": nullf, "__rs": nullf, "__rn": nullf,
        "__qm": nullf,
        "__qgt": [r[2] for r in rows],
        "__ce0": [r[3] for r in rows],
        "__cs0": [r[4] for r in rows],
        "__cnw0": [r[5] for r in rows],
    })


def test_bucket_rep_rows_merge_local_remote_qg_segments():
    """compute_bucket_stats_from_frame：GET 代表行把 local/remote 网络/框架分段
    合并进单行（主键不变）；整体 legacy 指标（total_latency）仍取整体分位代表。"""
    import polars as pl

    frames = compute_bucket_stats_from_frame(_qg_df_trace(), kb_id="kb", log_id="lg")
    for g in GRANULARITY_KEYS:
        by_mode = {
            row["mode"]: row
            for row in frames[g].iter_rows(named=True)
        }
        assert set(by_mode) == {"median", "p99", "p9999", "pmax"}

        # 整体分位：median=tr-lo(300)、p99/p9999=tl-hi(450)、pmax=tr-hi(500)
        assert by_mode["median"]["total_latency"] == 300.0
        assert by_mode["p99"]["total_latency"] == 450.0
        assert by_mode["pmax"]["total_latency"] == 500.0

        # 传输分段合并：local/remote 网络/框架恒取自各自传输类型代表
        # median 行：local 代表 tl-lo(20/180)、remote 代表 tr-lo(30/210)
        for m in ("median", "p99", "p9999"):
            r = by_mode[m]
            assert r["query_get_local_rpc_network_us"] == 20.0
            assert r["query_get_local_rpc_framework_us"] == 180.0
            assert r["query_get_remote_rpc_network_us"] == 30.0
            assert r["query_get_remote_rpc_framework_us"] == 210.0
        # pmax 行：local 代表 tl-hi(40/320)、remote 代表 tr-hi(50/350)
        r = by_mode["pmax"]
        assert r["query_get_local_rpc_network_us"] == 40.0
        assert r["query_get_local_rpc_framework_us"] == 320.0
        assert r["query_get_remote_rpc_network_us"] == 50.0
        assert r["query_get_remote_rpc_framework_us"] == 350.0
