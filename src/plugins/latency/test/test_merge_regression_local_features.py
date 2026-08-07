# Copyright (c) Huawei Technologies Co., Ltd. 2023-2025. All rights reserved.
"""Merge regression guard — local polars-pipeline features MUST survive the
upstream merge.

This file is written BEFORE the merge (pre-merge it must pass on the current
local tree). After merging upstream into the worktree, it stays the contract:
if any of these local features disappears or breaks, the merge is wrong.

Covers (all LOCAL, absolute priority):
- polars core: columnar / trace_frame / bucket.statistics / stage_progress
- df_trace contract: build_trace_frame + TRACE_COLUMNS
- scan progress callback: scanner.scan_all progress_cb param
- time-window + src_dst managers (T4)
- bucket precompute: LatencyBucket* models + compute_bucket_stats_from_frame
- schemas/request: local bucket_seconds / log_id on GetLatencyMetricsRequest
- schemas/log: TimeWindow* classes + kb_id on SrcDstAggregatedEvent
- stage_progress: [polars] prefix + DEFAULT_STAGES
- golden: summary-only golden_e2e_100m.json (31 B) — never the 11 MB dump
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest


def test_columnar_imports_and_contract():
    from latency.parse.parallel_scanner.columnar import (
        TRACE_COLUMNS,
        entries_to_columns,
        columns_to_frame,
    )

    assert "tid" in TRACE_COLUMNS
    assert "total_ms" in TRACE_COLUMNS
    assert callable(entries_to_columns)
    assert callable(columns_to_frame)


def test_trace_frame_build():
    from latency.parse.parallel_scanner.trace_frame import build_trace_frame
    from latency.parse.parallel_scanner.columnar import TRACE_COLUMNS, ALL_COLUMNS

    assert callable(build_trace_frame)
    # build_trace_frame consumes the columnar dict output (keys = ALL_COLUMNS)
    # and must still produce a frame with exactly TRACE_COLUMNS
    out = build_trace_frame({c: [] for c in ALL_COLUMNS})
    assert out.columns == list(TRACE_COLUMNS)


def test_stage_progress_contract():
    from latency.common.stage_progress import DEFAULT_STAGES, PROGRESS_MESSAGE_PREFIX

    assert PROGRESS_MESSAGE_PREFIX == "[polars]"
    labels = [s for s, _ in DEFAULT_STAGES]
    assert "scan" in labels and "aggregate" in labels and "store" in labels


def test_bucket_statistics_frame_path():
    from latency.bucket.statistics import (
        compute_bucket_stats_from_frame,
        compute_and_store_bucket_stats_from_frame,
    )

    assert callable(compute_bucket_stats_from_frame)
    assert callable(compute_and_store_bucket_stats_from_frame)


def test_bucket_models_exist():
    from latency.database.models import (
        LatencyBucket10s,
        LatencyBucket1min,
        LatencyBucket10min,
        LatencyBucket1h,
        TimeWindowAggregated,
    )

    for cls in (LatencyBucket10s, LatencyBucket1min, LatencyBucket10min, LatencyBucket1h):
        assert "log_id" in cls.__table__.columns
        assert "trace_id" in cls.__table__.columns
    assert "time_bucket" in TimeWindowAggregated.__table__.columns


def test_src_dst_kb_id_and_time_window_classes():
    from latency.schemas.log import (
        SrcDstAggregatedEventDataclass,
        TimeWindowAggregatedEventDataclass,
    )

    assert "kb_id" in SrcDstAggregatedEventDataclass.__dataclass_fields__
    assert "time_bucket" in TimeWindowAggregatedEventDataclass.__dataclass_fields__


def test_get_latency_metrics_request_keeps_local_fields():
    from latency.schemas.request import GetLatencyMetricsRequest

    fields = GetLatencyMetricsRequest.model_fields
    assert "bucket_seconds" in fields
    assert "log_id" in fields


def test_scanner_accepts_progress_cb():
    import inspect

    from latency.parse.parallel_scanner.scanner import ParallelFileScanner

    sig = inspect.signature(ParallelFileScanner.scan_all)
    assert "progress_cb" in sig.parameters


def test_scan_progress_cb_test_exists():
    # The unit test for the scan progress callback must survive the merge
    p = Path(__file__).parent / "test_scan_progress_cb.py"
    assert p.is_file(), "test_scan_progress_cb.py missing after merge"


def test_golden_is_summary_only():
    golden = Path(__file__).parent / "golden" / "golden_e2e_100m.json"
    if golden.is_file():
        data = json.loads(golden.read_text(encoding="utf-8"))
        assert set(data.keys()) == {"summary"}
        assert golden.stat().st_size < 100_000, "golden regrew to a huge dump"


def test_worker_has_aggregate_polars():
    import inspect

    from latency.task.worker.kv_cache_log_parse_worker import KVCacheLogParseWorker

    assert hasattr(KVCacheLogParseWorker, "_aggregate_polars")
    assert "df_trace" in inspect.signature(KVCacheLogParseWorker._aggregate_polars).parameters


def test_deploy_uses_venv_python():
    deploy = Path(__file__).resolve().parents[5] / "deploy" / "deploy.sh"
    if deploy.is_file():
        text = deploy.read_text(encoding="utf-8")
        assert ".venv/bin/python" in text, "deploy.sh must use venv python"


def test_no_upstream_detect_or_correlation_imports_in_parse_init():
    from latency.parse import __file__ as parse_init

    text = Path(parse_init).read_text(encoding="utf-8")
    assert "correlation" not in text, "parse/__init__ must not import correlation (local removed it)"


def test_no_upstream_detect_import_in_diagnosis_worker():
    from latency.task.worker import kv_cache_log_event_diagnosis_worker as m

    src = Path(m.__file__).read_text(encoding="utf-8")
    assert "latency.detect" not in src, "diagnosis worker must not import latency.detect"
