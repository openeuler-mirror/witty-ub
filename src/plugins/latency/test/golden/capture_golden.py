#!/usr/bin/env python3
# Copyright (c) Huawei Technologies Co., Ltd. 2023-2025. All rights reserved.
"""Golden capture for the polars pipeline rewrite (T0, refreshed for T7).

Runs the CURRENT (polars) aggregation pipeline on two data sources and
snapshots the 5 behavioral output categories to JSON:

  1. src_dst events        — SrcDstAggregatedEventDataclass, deterministic fields
  2. time_window events    — TimeWindowAggregatedEventDataclass, deterministic fields
  3. anomalous_tids        — sorted list
  4. detail rows           — LogParseResultDataclass (anomalous, persisted detail),
                             deterministic fields
  5. bucket rep-rows       — 4 granularities (10s/1min/10min/1h), 5 percentile modes

These fixtures are the behavioral golden anchor: every polars rewrite stage
(T3 aggregation / T4 bucket stats / T5 detail rows) must reproduce them.

Sources:
  (a) test_trace_frame._fixture_raw()    -> test/golden/golden_fixture.json
  (b) data/logs/e2e-test-100m (if present)  -> test/golden/golden_e2e_100m.json

Non-deterministic fields (uuid ``id`` / ``created_at`` / uuid link fields) are
excluded so the golden is reproducible and diffable across runs.

Usage:
    cd src/plugins/latency
    PYTHONPATH=/home/li/witty-ub_8632/src/plugins \
      .venv/bin/python test/golden/capture_golden.py
"""
from __future__ import annotations

import asyncio
import functools
import importlib.util
import ipaddress
import json
import logging
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

logger = logging.getLogger("capture-golden")

# ---------------------------------------------------------------------------
# 非确定性字段: uuid id / uuid link / created_at —— golden 需可复现可 diff
# ---------------------------------------------------------------------------
_SKIP_FIELDS = frozenset(
    {"id", "created_at", "aggregated_event_id", "anomalous_event_id"}
)


def _json_safe(value):
    """Convert a value (or nested structure) to JSON-safe Python types."""
    if value is None or isinstance(value, (str, int, bool)):
        return value
    if isinstance(value, float):
        return value
    if isinstance(value, (ipaddress.IPv4Address, ipaddress.IPv6Address)):
        return str(value)
    if isinstance(value, datetime):
        return value.isoformat()
    if hasattr(value, "isoformat"):  # np.datetime64 etc.
        return value.isoformat()
    if isinstance(value, dict):
        return {str(k): _json_safe(v) for k, v in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_json_safe(v) for v in value]
    return str(value)


def _dataclass_fields(dc, skip: frozenset[str]) -> dict:
    """Snapshot a dataclass's deterministic fields."""
    import dataclasses

    out = {}
    for f in dataclasses.fields(dc):
        if f.name in skip:
            continue
        out[f.name] = _json_safe(getattr(dc, f.name))
    return out


def _bucket_rep_rows(rows_by_granularity: dict[int, list[tuple]]) -> dict:
    """Serialize {granularity: [COPY tuples]} -> {label: [{col: val}, ...]}."""
    from latency.bucket.statistics import BUCKET_COLUMNS, GRANULARITY_LABELS

    out = {}
    for g, tuples in rows_by_granularity.items():
        out[GRANULARITY_LABELS[g]] = [
            dict(zip(BUCKET_COLUMNS, (_json_safe(v) for v in row)))
            for row in tuples
        ]
    return out


# ---------------------------------------------------------------------------
# 快照 trace_index 的 5 类输出（与生产 run() 相同的消费入口）
# ---------------------------------------------------------------------------

def snapshot_trace_index(df_trace, log_file_id: str, kb_id: str) -> dict:
    """Run the current (polars) pipeline over df_trace and snapshot.

    Mirrors ``KVCacheLogParseWorker.run``'s consumption of the aggregate
    5-tuple + ``_build_anomalous_detail_rows`` + ``compute_bucket_stats_from_frame``
    (no DB store).
    """
    from latency.task.worker.kv_cache_log_parse_worker import (
        KVCacheLogParseWorker,
    )

    # ── 聚合三路（polars，diagnosis_config=None → threshold 5.0）──
    (
        src_dst_events,
        _src_dst_to_agg_id_map,
        tw_events,
        anom_tids,
        df_trace_ret,
    ) = asyncio.run(
        KVCacheLogParseWorker._aggregate_three_way(
            df_trace, None, log_file_id
        )
    )

    # ── detail 行（异常 trace，生产持久化路径）──
    detail_rows = KVCacheLogParseWorker._build_anomalous_detail_rows(
        df_trace, anom_tids, kb_id=kb_id, log_file_id=log_file_id
    )

    # ── bucket rep-rows：纯 polars 选代表行（T4/T7 frame 路径）──
    from latency.bucket.statistics import (
        GRANULARITY_KEYS,
        compute_bucket_stats_from_frame,
    )

    created_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
    materializer = functools.partial(
        KVCacheLogParseWorker._make_field_row,
        log_file_id=log_file_id,
        created_at=created_at,
    )
    bucket_rep_rows = compute_bucket_stats_from_frame(
        df_trace, kb_id=kb_id, log_id=log_file_id, materializer=materializer
    )

    # ── 确定性排序（dict/set 迭代序不可靠）──
    src_dst_events.sort(key=lambda e: (e.src_ip, e.dst_ip, e.operation))
    tw_events.sort(key=lambda e: (e.time_bucket, e.src_ip, e.dst_ip))
    detail_rows.sort(key=lambda r: (r.trace_id or ""))

    return {
        "meta": {
            "source": "df_trace",
            "log_file_id": log_file_id,
            "kb_id": kb_id,
            "threshold_ms": 5.0,
        },
        "summary": {
            "traces": df_trace.height,
            "src_dst_events": len(src_dst_events),
            "time_window_events": len(tw_events),
            "anomalous_tids": len(anom_tids),
            "detail_rows": len(detail_rows),
            "bucket_rep_rows": {
                label: len(rows) for label, rows in bucket_rep_rows.items()
            },
        },
        "src_dst_events": [
            _dataclass_fields(e, _SKIP_FIELDS) for e in src_dst_events
        ],
        "time_window_events": [
            _dataclass_fields(e, _SKIP_FIELDS) for e in tw_events
        ],
        "anomalous_tids": sorted(anom_tids),
        "detail_rows": [
            _dataclass_fields(r, _SKIP_FIELDS) for r in detail_rows
        ],
        "bucket_rep_rows": _bucket_rep_rows(bucket_rep_rows),
    }


# ---------------------------------------------------------------------------
# 数据源 (a): test_field_table_slice._fixture()
# ---------------------------------------------------------------------------

def _load_fixture():
    """Load the fixture df_trace from test_trace_frame.py (no pytest run)."""
    test_dir = Path(__file__).resolve().parent.parent  # .../latency/test
    spec = importlib.util.spec_from_file_location(
        "test_trace_frame", test_dir / "test_trace_frame.py"
    )
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    from latency.parse.parallel_scanner.columnar import entries_to_columns
    from latency.parse.parallel_scanner.trace_frame import build_trace_frame

    return build_trace_frame(entries_to_columns(mod._fixture_raw()))


# ---------------------------------------------------------------------------
# 数据源 (b): data/logs/e2e-test-100m（真实日志目录，存在则解析）
# ---------------------------------------------------------------------------

async def _load_e2e_trace_index():
    """Headless full-pipeline scan of the e2e log directory (df_trace)."""
    from latency.task.worker.kv_cache_log_parse_worker import (
        KVCacheLogParseWorker,
    )

    # 仓库根 = 本文件上溯 6 级（golden/test/latency/plugins/src/根）
    repo_root = Path(__file__).resolve().parents[5]
    e2e_dir = repo_root / "data" / "logs" / "e2e-test-100m"
    if not e2e_dir.is_dir():
        return None
    logger.info("Scanning e2e dir: %s", e2e_dir)
    t0 = time.perf_counter()
    df_trace = await KVCacheLogParseWorker.parse_log(log_dir=str(e2e_dir))
    logger.info(
        "e2e parse done: %d traces in %.1fs",
        df_trace.height,
        time.perf_counter() - t0,
    )
    return df_trace


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------

def main() -> int:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )
    out_dir = Path(__file__).resolve().parent
    out_dir.mkdir(parents=True, exist_ok=True)

    # (a) fixture —— 小、快、确定性
    fixture = _load_fixture()
    logger.info("fixture traces=%d", fixture.height)
    snap_fixture = snapshot_trace_index(fixture, "op001", "test_kb")
    out_fixture = out_dir / "golden_fixture.json"
    out_fixture.write_text(
        json.dumps(snap_fixture, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    logger.info("wrote %s (%.1f KB)", out_fixture, out_fixture.stat().st_size / 1024)

    # (b) e2e-100m —— 真实日志（存在则用，失败不阻塞 fixture 产出）
    try:
        e2e_df_trace = asyncio.run(_load_e2e_trace_index())
    except Exception as e:  # pragma: no cover
        logger.exception("e2e scan failed: %s", e)
        e2e_df_trace = None

    if e2e_df_trace is not None:
        # 只写 summary（trace 计数），不落全量快照 —— 全量 11 MB 超出 gitcode
        # 单文件 10 MiB 上限，且 test_trace_frame 只消费 summary.traces。
        out_e2e = out_dir / "golden_e2e_100m.json"
        snap_e2e = {"summary": {"traces": e2e_df_trace.height}}
        out_e2e.write_text(
            json.dumps(snap_e2e, indent=2, ensure_ascii=False), encoding="utf-8"
        )
        logger.info("wrote %s (%.1f KB)", out_e2e, out_e2e.stat().st_size / 1024)
    else:
        logger.warning("e2e-test-100m not found/skipped — no golden_e2e_100m.json")

    return 0


if __name__ == "__main__":
    sys.exit(main())
