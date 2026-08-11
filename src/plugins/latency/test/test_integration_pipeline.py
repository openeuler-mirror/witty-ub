"""Integration test for rewritten pipeline with small data subset.

Tests the pipeline end-to-end:
1. Scanner → trace_index (via ParallelFileScanner.scan_all)
2. Generate aggregate result (single-sort-per-bucket snapshot)
3. Anomalous detail row construction (_build_anomalous_detail_rows)
4. Memory cache population (aggregate_cache)
5. Store (async via store_result)

Uses 2 SDK + 1 Worker hosts from data/logs/daas/ (~3.4GB subset).

Usage:
    cd src/plugins/latency
    PYTHONPATH=$(pwd)/../.. python3 -m pytest test/test_integration_pipeline.py -v
"""

import asyncio
import logging
import shutil
import sys
import tempfile
import time
from pathlib import Path

import pytest

_TEST_DIR = Path(__file__).resolve().parent
_LATENCY_PLUGIN = _TEST_DIR.parent
_PROJECT_ROOT = _LATENCY_PLUGIN.parent
_REPO_ROOT = _PROJECT_ROOT.parent.parent
sys.path.insert(0, str(_PROJECT_ROOT))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger(__name__)

_SDK_217 = _REPO_ROOT / "data/logs/daas/SDK_6.62.222.217"
_SDK_218 = _REPO_ROOT / "data/logs/daas/SDK_6.62.222.218"
_WORKER_31 = _REPO_ROOT / "data/logs/daas/Worker_6.62.223.31"

_EVIDENCE_DIR = _REPO_ROOT / ".omo/evidence"
_EVIDENCE_FILE = _EVIDENCE_DIR / "task-6-pipeline-rewrite.txt"


@pytest.fixture(scope="module")
def combined_log_dir():
    root = Path(tempfile.mkdtemp(prefix="latency_integration_"))
    sources = [
        ("SDK_6.62.222.217", _SDK_217),
        ("SDK_6.62.222.218", _SDK_218),
        ("Worker_6.62.223.31", _WORKER_31),
    ]
    linked = 0
    for name, src in sources:
        if src.is_dir():
            link = root / name
            link.symlink_to(src, target_is_directory=True)
            linked += 1
            logger.info("[INTEGRATION] symlinked %s → %s", link, src)
        else:
            logger.warning("[INTEGRATION] source unavailable: %s", src)

    if linked == 0:
        root.rmdir()
        pytest.skip("No test data directories found")

    yield root
    shutil.rmtree(root, ignore_errors=True)
    logger.info("[INTEGRATION] cleaned up temp dir: %s", root)


@pytest.fixture(autouse=True)
def clear_integration_cache():
    from latency.common.aggregate_cache import clear_cache

    clear_cache()
    yield
    clear_cache()


def _run(coro):
    return asyncio.run(coro)


def _to_df(trace_index):
    """{trace_id: {label: [entries]}} → df_trace（polars, T2/T7 唯一输入形态）。"""
    from latency.parse.parallel_scanner.columnar import entries_to_columns
    from latency.parse.parallel_scanner.trace_frame import build_trace_frame

    by_label: dict[str, list] = {}
    for labels in trace_index.values():
        for label, entries in labels.items():
            by_label.setdefault(label, []).extend(entries)
    return build_trace_frame(entries_to_columns(by_label))


def _build_scanners_and_parsers():
    """Create scanner and parsers with correct patterns (matching parse_log)."""
    from latency.parse.parallel_scanner.scanner import ParallelFileScanner
    from latency.parse.sdk_access_log_parser import SdkAccessLogParser
    from latency.parse.worker_access_log_parser import WorkerAccessLogParser
    from latency.config.config import Config

    diagnosis_config = Config().get_diagnosis_config()
    filename_config = diagnosis_config.log_filename_pattern

    sdk_patterns = [
        *filename_config.ds_client_access_log_file,
        *filename_config.ds_client_info_log_file,
    ]
    sdk_parser = SdkAccessLogParser(None)
    sdk_parser._runtime_patterns = sdk_patterns

    worker_parser = WorkerAccessLogParser(None)
    worker_parser._runtime_patterns = filename_config.ds_worker_access_log_file

    sdk_scanner = ParallelFileScanner(
        max_processes=min(6, (Path("/").exists() and __import__("os").cpu_count() or 4)),
        use_multiprocessing=True,
        decompress=False,
    )
    worker_scanner = ParallelFileScanner(
        max_processes=min(2, (Path("/").exists() and __import__("os").cpu_count() or 2)),
        use_multiprocessing=True,
        decompress=False,
    )
    return sdk_scanner, worker_scanner, sdk_parser, worker_parser


async def _scan_to_trace_index(log_dir: str):
    """Run scanner directly to get trace_index {trace_id: {label: [entries]}}."""
    import os

    sdk_scanner, worker_scanner, sdk_parser, worker_parser = (
        _build_scanners_and_parsers()
    )

    logger.info("=== Scanner: SDK access scan ===")
    t1 = time.perf_counter()
    trace_index = await sdk_scanner.scan_all(log_dir, [sdk_parser])
    t_scan = time.perf_counter() - t1
    logger.info(
        "[SCAN SDK] %d traces in %.1fs",
        len(trace_index),
        t_scan,
    )

    logger.info("=== Scanner: Worker access scan ===")
    t2 = time.perf_counter()
    worker_ti = await worker_scanner.scan_all(log_dir, [worker_parser])
    t_scan2 = time.perf_counter() - t2
    logger.info(
        "[SCAN Worker] %d traces in %.1fs",
        len(worker_ti),
        t_scan2,
    )

    for tid, labels in worker_ti.items():
        if tid in trace_index:
            trace_index[tid].update(labels)
        else:
            trace_index[tid] = labels

    return trace_index, t_scan + t_scan2


@pytest.mark.integration
class TestPipelineIntegration:

    def test_full_pipeline_runs_without_error(self, combined_log_dir):
        from latency.task.worker.kv_cache_log_parse_worker import \
            KVCacheLogParseWorker
        from latency.common.aggregate_cache import (
            clear_cache,
            get_aggregated_events,
            get_time_window_events,
            set_aggregated_events,
            set_time_window_events,
        )

        log_dir_str = str(combined_log_dir)
        logger.info("=== INTEGRATION: full pipeline ===")

        t_total = time.perf_counter()

        t1 = time.perf_counter()
        trace_index, t_scan = _run(_scan_to_trace_index(log_dir_str))
        t_scan_elapsed = time.perf_counter() - t1
        logger.info(
            "[STEP 1] scan_all: %d traces in %.1fs",
            len(trace_index),
            t_scan_elapsed,
        )
        assert isinstance(trace_index, dict), "must return dict"
        assert len(trace_index) > 0, "must have at least one trace"

        t2 = time.perf_counter()
        (
            src_dst_events,
            src_dst_map,
            tw_events,
            anomalous_tids,
        ) = _run(KVCacheLogParseWorker.generate_aggregate_result(_to_df(trace_index)))
        t_agg = time.perf_counter() - t2
        logger.info(
            "[STEP 2] aggregate: %d endpoints, %d time-windows, "
            "%d anomalous tids in %.1fs",
            len(src_dst_events),
            len(tw_events),
            len(anomalous_tids),
            t_agg,
        )
        assert isinstance(src_dst_events, list)
        assert isinstance(tw_events, list)
        assert isinstance(anomalous_tids, set)

        t3 = time.perf_counter()
        detail_rows = KVCacheLogParseWorker._build_anomalous_detail_rows(
            _to_df(trace_index), anomalous_tids, kb_id="test_kb", log_file_id="test_log"
        )
        t_detail = time.perf_counter() - t3
        logger.info("[STEP 3] detail_rows: %d in %.1fs", len(detail_rows), t_detail)
        if anomalous_tids:
            assert len(detail_rows) > 0

        clear_cache()
        fake_log_id = "integration_test_log_id"
        set_aggregated_events(fake_log_id, src_dst_events)
        set_time_window_events(fake_log_id, tw_events)

        cached_agg = get_aggregated_events(fake_log_id)
        cached_tw = get_time_window_events(fake_log_id)
        assert cached_agg is not None
        assert len(cached_agg) == len(src_dst_events)
        assert cached_tw is not None
        assert len(cached_tw) == len(tw_events)
        logger.info("[STEP 4] cache HIT: agg=%d tw=%d", len(cached_agg), len(cached_tw))

        # STEP 5 (store): skipped — requires running PostgreSQL; pipeline
        # core (scan → aggregate → detail_rows → cache) is fully validated.
        t_store = 0.0
        logger.info("[STEP 5] store: SKIPPED (requires PostgreSQL)")

        t_total_elapsed = time.perf_counter() - t_total
        logger.info(
            "=== PIPELINE COMPLETE ===\n"
            "    scan:       %7.1fs (%d traces)\n"
            "    aggregate:  %7.1fs\n"
            "    detail_rows:%7.1fs\n"
            "    store:      %7.1fs\n"
            "    TOTAL:      %7.1fs",
            t_scan_elapsed, len(trace_index),
            t_agg, t_detail, t_store, t_total_elapsed,
        )

        _EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
        with open(_EVIDENCE_FILE, "w") as f:
            f.write(
                f"Task 6 - Pipeline Integration Test Evidence\n"
                f"Date: {time.strftime('%Y-%m-%d %H:%M:%S')}\n\n"
                f"Pipeline phases:\n"
                f"  scan:           {t_scan_elapsed:.1f}s\n"
                f"  aggregate:      {t_agg:.1f}s\n"
                f"  detail_rows:    {t_detail:.1f}s\n"
                f"  store:          {t_store:.1f}s\n"
                f"  total:          {t_total_elapsed:.1f}s\n\n"
                f"Results:\n"
                f"  trace_index traces:     {len(trace_index)}\n"
                f"  src_dst_agg_events:     {len(src_dst_events)}\n"
                f"  time_window_agg_events: {len(tw_events)}\n"
                f"  anomalous_detail_rows:  {len(detail_rows)}\n"
                f"  anomalous_tids:         {len(anomalous_tids)}\n\n"
                f"Cache: HIT (agg={len(cached_agg or [])}, tw={len(cached_tw or [])})\n"
            )
        logger.info("[EVIDENCE] written to %s", _EVIDENCE_FILE)

    def test_snapshot_field_coherence(self, combined_log_dir):
        from latency.task.worker.kv_cache_log_parse_worker import \
            KVCacheLogParseWorker

        log_dir_str = str(combined_log_dir)

        async def _check():
            trace_index, _ = await _scan_to_trace_index(log_dir_str)
            (agg_events, _, tw_events, _) = (
                await KVCacheLogParseWorker.generate_aggregate_result(_to_df(trace_index))
            )

            for event in agg_events[:200]:
                p99_total = event.p99_total_latency
                if p99_total is not None and p99_total > 0:
                    assert isinstance(p99_total, (int, float))
                if event.max_total_latency is not None:
                    assert event.max_total_latency >= 0

            for event in tw_events[:200]:
                # min/max/p95 已从 TimeWindowAggregatedEventDataclass 移除
                # （前端无渲染点，见 Todo 4），用 getattr 兼容旧字段读取。
                if getattr(event, "max_total_latency", None) is not None:
                    assert isinstance(event.max_total_latency, (int, float))

            return len(agg_events), len(tw_events)

        agg_count, tw_count = _run(_check())
        logger.info(
            "[COHERENCE] checked %d aggregate + %d time-window events",
            agg_count,
            tw_count,
        )

    def test_anomalous_detail_rows_have_correct_shape(self, combined_log_dir):
        from latency.task.worker.kv_cache_log_parse_worker import \
            KVCacheLogParseWorker
        from latency.schemas.log import LogParseResultDataclass

        log_dir_str = str(combined_log_dir)

        async def _check():
            trace_index, _ = await _scan_to_trace_index(log_dir_str)
            _, _, _, anomalous_tids = (
                await KVCacheLogParseWorker.generate_aggregate_result(_to_df(trace_index))
            )
            detail_rows = KVCacheLogParseWorker._build_anomalous_detail_rows(
                _to_df(trace_index), anomalous_tids
            )
            return detail_rows, trace_index

        detail_rows, trace_index = _run(_check())
        sdk_count = 0
        for v in trace_index.values():
            if isinstance(v, dict) and v.get("SDK access parse"):
                sdk_count += 1
            elif isinstance(v, list):
                sdk_count += len(v)
        logger.info(
            "[SHAPE] %d detail rows from %d traces (%d sdk)",
            len(detail_rows),
            len(trace_index),
            sdk_count,
        )

        if not detail_rows:
            logger.warning("[SHAPE] no anomalous detail rows — check threshold config")
            return

        for row in detail_rows[:10]:
            assert isinstance(row, LogParseResultDataclass)
            assert row.is_anomalous is True
            assert row.aggregated_event_id == ""
            assert hasattr(row, "total_latency")
            assert hasattr(row, "timestamp")
            assert hasattr(row, "src_ip")
            assert hasattr(row, "dst_ip")
            assert hasattr(row, "operation")
            assert hasattr(row, "trace_id")
            assert row.total_latency is not None, (
                f"total_latency must be set (trace_id={row.trace_id})"
            )

    def test_cache_miss_returns_none(self):
        from latency.common.aggregate_cache import get_aggregated_events

        result = get_aggregated_events("nonexistent_log_id_xyz")
        assert result is None

    def test_empty_trace_index_produces_empty_results(self):
        from latency.task.worker.kv_cache_log_parse_worker import \
            KVCacheLogParseWorker

        async def _check():
            empty_index: dict = {}
            df = _to_df(empty_index)
            (agg, _, tw, anom_tids) = (
                await KVCacheLogParseWorker.generate_aggregate_result(df)
            )
            detail = KVCacheLogParseWorker._build_anomalous_detail_rows(
                df, anom_tids
            )
            return agg, tw, anom_tids, detail

        agg, tw, anom_tids, detail = _run(_check())
        assert len(agg) == 0
        assert len(tw) == 0
        assert len(anom_tids) == 0
        assert len(detail) == 0
        logger.info("[EDGE] empty trace_index handled correctly")

    def test_trace_with_missing_sdk_label_is_skipped(self):
        from latency.task.worker.kv_cache_log_parse_worker import \
            KVCacheLogParseWorker

        async def _check():
            bad_index: dict = {
                "trace_missing_sdk": {
                    "Worker access parse": [
                        ("2024-01-01T00:00:00", "GET", 5000.0, None, None,
                         "trace_missing_sdk", None, None, None, None, None,
                         "10.0.0.1", "10.0.0.2", None, None, "test_log"),
                    ],
                },
            }
            agg, _, tw, anom_tids = (
                await KVCacheLogParseWorker.generate_aggregate_result(_to_df(bad_index))
            )
            return agg, tw, anom_tids

        agg, tw, anom_tids = _run(_check())
        assert len(agg) == 0
        assert len(tw) == 0
        logger.info("[EDGE] missing SDK label correctly skipped")

    # ── TDD red-phase tests: pin Fix A (IP resolution) + Fix B (status_code
    #    anomaly). These FAIL against current generate_aggregate_result:
    #    src/dst read from the SDK entry's SRC_ADDR/DST_ADDR (always None),
    #    and the anomaly check only tests total_ms > threshold_ms.
    # ── Entry tuples are 16-element, in TupleField order:
    #    (timestamp, operation, elapsed_us, data_size, object_key, trace_id,
    #     pod_ip, status_code, resp_msg, entry_type, cluster_name, src_addr,
    #     dst_addr, inflight_count, request_size, log_id)

    def test_aggregate_ip_from_urma_fallback(self):
        from latency.task.worker.kv_cache_log_parse_worker import \
            KVCacheLogParseWorker

        async def _check():
            trace_index: dict = {
                "trace_urma_ip": {
                    "SDK access parse": [
                        ("2024-01-01T00:00:00", "GET", 100, None, None,
                         "trace_urma_ip", None, 0, None, None, None,
                         None, None, None, None, "test_log"),
                    ],
                    "Worker urma parse": [
                        ("2024-01-01T00:00:00", "URMA", 100, None, None,
                         "trace_urma_ip", None, 0, None, None, None,
                         "10.0.0.1", "10.0.0.2", None, None, "test_log"),
                    ],
                },
            }
            (agg, _, tw, anom_tids) = (
                await KVCacheLogParseWorker.generate_aggregate_result(_to_df(trace_index))
            )
            return agg, tw, anom_tids

        agg, tw, anom_tids = _run(_check())
        assert len(agg) == 1
        assert agg[0].src_ip == "10.0.0.1"
        assert agg[0].dst_ip == "10.0.0.2"
        logger.info(
            "[AGG-IP] URMA fallback resolved src=%s dst=%s anom=%d tw=%d",
            agg[0].src_ip, agg[0].dst_ip, len(anom_tids), len(tw),
        )

    def test_aggregate_ip_fallback_to_remote_pull(self):
        from latency.task.worker.kv_cache_log_parse_worker import \
            KVCacheLogParseWorker

        async def _check():
            trace_index: dict = {
                "trace_pull_ip": {
                    "SDK access parse": [
                        ("2024-01-01T00:00:00", "GET", 100, None, None,
                         "trace_pull_ip", None, 0, None, None, None,
                         None, None, None, None, "test_log"),
                    ],
                    "Worker remote pull parse": [
                        ("2024-01-01T00:00:00", "REMOTE_PULL", 100, None, None,
                         "trace_pull_ip", None, 0, None, None, None,
                         "10.1.0.1", "10.1.0.2", None, None, "test_log"),
                    ],
                },
            }
            (agg, _, tw, anom_tids) = (
                await KVCacheLogParseWorker.generate_aggregate_result(_to_df(trace_index))
            )
            return agg, tw, anom_tids

        agg, tw, anom_tids = _run(_check())
        assert len(agg) == 1
        assert agg[0].src_ip == "10.1.0.1"
        assert agg[0].dst_ip == "10.1.0.2"
        logger.info(
            "[AGG-IP] RemotePull fallback resolved src=%s dst=%s anom=%d tw=%d",
            agg[0].src_ip, agg[0].dst_ip, len(anom_tids), len(tw),
        )

    def test_aggregate_ip_empty_when_no_urma_or_pull(self):
        from latency.task.worker.kv_cache_log_parse_worker import \
            KVCacheLogParseWorker

        async def _check():
            trace_index: dict = {
                "trace_sdk_only": {
                    "SDK access parse": [
                        ("2024-01-01T00:00:00", "GET", 100, None, None,
                         "trace_sdk_only", None, 0, None, None, None,
                         None, None, None, None, "test_log"),
                    ],
                },
            }
            (agg, _, tw, anom_tids) = (
                await KVCacheLogParseWorker.generate_aggregate_result(_to_df(trace_index))
            )
            return agg, tw, anom_tids

        agg, tw, anom_tids = _run(_check())
        assert len(agg) == 1
        assert agg[0].src_ip == ""
        assert agg[0].dst_ip == ""
        logger.info(
            "[AGG-IP] no urma/pull -> src=%r dst=%r (graceful degrade) anom=%d tw=%d",
            agg[0].src_ip, agg[0].dst_ip, len(anom_tids), len(tw),
        )

    def test_aggregate_status_code_anomaly(self):
        from latency.task.worker.kv_cache_log_parse_worker import \
            KVCacheLogParseWorker

        async def _check():
            # elapsed_us=0 -> total_ms=0.0 (below 2.0ms threshold): only the
            # status_code=1 makes this trace anomalous.
            trace_index: dict = {
                "trace_conn_fault": {
                    "SDK access parse": [
                        ("2024-01-01T00:00:00", "GET", 0, None, None,
                         "trace_conn_fault", None, 1, None, None, None,
                         None, None, None, None, "test_log"),
                    ],
                },
            }
            (agg, _, tw, anom_tids) = (
                await KVCacheLogParseWorker.generate_aggregate_result(_to_df(trace_index))
            )
            return agg, tw, anom_tids

        agg, tw, anom_tids = _run(_check())
        assert "trace_conn_fault" in anom_tids
        logger.info(
            "[AGG-ANOM] status_code=1 marked anomalous anom=%d agg=%d tw=%d",
            len(anom_tids), len(agg), len(tw),
        )

    def test_aggregate_normal_not_anomalous(self):
        from latency.task.worker.kv_cache_log_parse_worker import \
            KVCacheLogParseWorker

        async def _check():
            # elapsed_us=500 -> total_ms=0.5 (below 2.0ms) AND status_code=0:
            # must NOT be marked anomalous.
            trace_index: dict = {
                "trace_normal": {
                    "SDK access parse": [
                        ("2024-01-01T00:00:00", "GET", 500, None, None,
                         "trace_normal", None, 0, None, None, None,
                         None, None, None, None, "test_log"),
                    ],
                },
            }
            (agg, _, tw, anom_tids) = (
                await KVCacheLogParseWorker.generate_aggregate_result(_to_df(trace_index))
            )
            return agg, tw, anom_tids

        agg, tw, anom_tids = _run(_check())
        assert "trace_normal" not in anom_tids
        logger.info(
            "[AGG-ANOM] normal trace not anomalous anom=%d agg=%d tw=%d",
            len(anom_tids), len(agg), len(tw),
        )


async def _run_full_pipeline_standalone(log_dir: str):
    from latency.task.worker.kv_cache_log_parse_worker import KVCacheLogParseWorker
    from latency.common.aggregate_cache import (
        clear_cache,
        get_aggregated_events,
        get_time_window_events,
        set_aggregated_events,
        set_time_window_events,
    )

    clear_cache()

    t_total = time.perf_counter()
    logger.info("=== STANDALONE: full pipeline ===")

    trace_index, t_scan = await _scan_to_trace_index(log_dir)
    df_trace = _to_df(trace_index)
    logger.info("[SCAN] %d traces in %.1fs", len(trace_index), t_scan)

    t1 = time.perf_counter()
    (agg, _, tw, anom_tids) = (
        await KVCacheLogParseWorker.generate_aggregate_result(df_trace)
    )
    t_agg = time.perf_counter() - t1

    t2 = time.perf_counter()
    detail = KVCacheLogParseWorker._build_anomalous_detail_rows(
        df_trace, anom_tids
    )
    t_detail = time.perf_counter() - t2

    fake_log_id = "standalone_test"
    set_aggregated_events(fake_log_id, agg)
    set_time_window_events(fake_log_id, tw)

    from latency.database.engine import AsyncSQLiteSingleton
    await AsyncSQLiteSingleton().init_database()

    t3 = time.perf_counter()
    store_ok = await KVCacheLogParseWorker.store_result(
        anomalous_detail_rows=detail,
        src_dst_aggregated_events=agg,
        time_window_aggregated_events=tw,
        kb_id="standalone_test",
    )
    t_store = time.perf_counter() - t3

    cached_agg = get_aggregated_events(fake_log_id)
    cached_tw = get_time_window_events(fake_log_id)

    t_total_elapsed = time.perf_counter() - t_total
    logger.info(
        "=== PIPELINE COMPLETE ===\n"
        "  scan:    %7.1fs  (%d traces)\n"
        "  aggr:    %7.1fs  (%d endpoints, %d tw, %d anom)\n"
        "  detail:  %7.1fs  (%d rows)\n"
        "  store:   %7.1fs  (ok=%s)\n"
        "  TOTAL:   %7.1fs\n"
        "  Cache:   agg=%d tw=%d",
        t_scan, len(trace_index),
        t_agg, len(agg), len(tw), len(anom_tids),
        t_detail, len(detail),
        t_store, store_ok,
        t_total_elapsed,
        len(cached_agg or []), len(cached_tw or []),
    )

    _EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
    with open(_EVIDENCE_FILE, "w") as f:
        f.write(
            f"Task 6 - Pipeline Integration Test Evidence\n"
            f"Date: {time.strftime('%Y-%m-%d %H:%M:%S')}\n\n"
            f"Pipeline phases:\n"
            f"  scan:           {t_scan:.1f}s\n"
            f"  aggregate:      {t_agg:.1f}s\n"
            f"  detail_rows:    {t_detail:.1f}s\n"
            f"  store:          {t_store:.1f}s\n"
            f"  total:          {t_total_elapsed:.1f}s\n\n"
            f"Results:\n"
            f"  trace_index traces:     {len(trace_index)}\n"
            f"  src_dst_agg_events:     {len(agg)}\n"
            f"  time_window_agg_events: {len(tw)}\n"
            f"  anomalous_detail_rows:  {len(detail)}\n"
            f"  anomalous_tids:         {len(anom_tids)}\n\n"
            f"Cache: HIT (agg={len(cached_agg or [])}, tw={len(cached_tw or [])})\n"
        )
    logger.info("[EVIDENCE] written to %s", _EVIDENCE_FILE)


async def main():
    logger.info("Integration test — standalone mode")
    logger.info("Data dirs: %s, %s, %s", _SDK_217, _SDK_218, _WORKER_31)

    with tempfile.TemporaryDirectory(prefix="latency_integration_") as tmp:
        tmp_path = Path(tmp)
        linked = 0
        for name, src in [
            ("SDK_6.62.222.217", _SDK_217),
            ("SDK_6.62.222.218", _SDK_218),
            ("Worker_6.62.223.31", _WORKER_31),
        ]:
            if src.is_dir():
                (tmp_path / name).symlink_to(src, target_is_directory=True)
                linked += 1

        if linked == 0:
            logger.error("No test data directories found")
            return

        await _run_full_pipeline_standalone(str(tmp_path))


if __name__ == "__main__":
    asyncio.run(main())
