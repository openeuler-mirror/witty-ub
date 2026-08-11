#!/usr/bin/env python3
"""End-to-end log parse test — scan + aggregate + detect (no DB required).

Runs the full pipeline against real daas log data and reports results.
Usage:
    cd src/plugins/latency
    PYTHONPATH=$(dirname $(pwd))/.. python3 test/run_e2e_log_parse.py
"""

import asyncio
import logging
import os
import sys
import time
import tempfile
import shutil
from collections import Counter
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parents[4]
_SRC_PLUGINS = _PROJECT_ROOT / "src" / "plugins"
sys.path.insert(0, str(_SRC_PLUGINS))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger("e2e-log-parse")


async def main() -> None:
    from latency.parse.parallel_scanner.scanner import ParallelFileScanner
    from latency.parse.sdk_access_log_parser import SdkAccessLogParser
    from latency.parse.worker_access_log_parser import WorkerAccessLogParser
    from latency.task.worker.kv_cache_log_parse_worker import KVCacheLogParseWorker
    from latency.config.config import Config

    diagnosis_config = Config().get_diagnosis_config()
    filename_config = diagnosis_config.log_filename_pattern

    log_dir = os.environ.get(
        "LOG_DIR",
        str(_PROJECT_ROOT / "data" / "logs" / "daas"),
    )
    sdk_host = os.environ.get("SDK_HOST", "SDK_6.62.222.217")
    worker_host = os.environ.get("WORKER_HOST", "Worker_6.62.223.31")

    sources = {}
    sdk_path = Path(log_dir) / sdk_host
    worker_path = Path(log_dir) / worker_host
    for name, src in [(sdk_host, sdk_path), (worker_host, worker_path)]:
        if src.is_dir():
            import tempfile
            tmp = tempfile.mkdtemp(prefix="e2e_")
            link = Path(tmp) / name
            link.symlink_to(src, target_is_directory=True)
            sources[name] = str(link)
            logger.info("symlinked %s -> %s", link, src)

    if not sources:
        logger.error("No data dirs found under %s", log_dir)
        return

    # Use a temp dir combining all sources
    tmp_root = next(iter(sources.values()))
    scan_dir = str(Path(tmp_root).parent)

    logger.info("=" * 70)
    logger.info("Phase 1: SDK Access Scan")
    logger.info("=" * 70)
    t_start = time.perf_counter()

    sdk_patterns = [
        *filename_config.ds_client_access_log_file,
        *filename_config.ds_client_info_log_file,
    ]
    sdk_parser = SdkAccessLogParser(None)
    sdk_parser._runtime_patterns = sdk_patterns
    sdk_scanner = ParallelFileScanner(
        max_processes=min(6, os.cpu_count() or 4),
        use_multiprocessing=True,
        decompress=False,
    )

    trace_index = await sdk_scanner.scan_all(scan_dir, [sdk_parser])
    t_scan = time.perf_counter() - t_start
    logger.info(
        "[SCAN] %d SDK traces in %.1fs", len(trace_index), t_scan,
    )

    worker_patterns = filename_config.ds_worker_access_log_file
    worker_parser = WorkerAccessLogParser(None)
    worker_parser._runtime_patterns = worker_patterns
    worker_scanner = ParallelFileScanner(
        max_processes=min(2, os.cpu_count() or 2),
        use_multiprocessing=True,
        decompress=False,
    )
    worker_ti = await worker_scanner.scan_all(scan_dir, [worker_parser])
    for tid, labels in worker_ti.items():
        trace_index.setdefault(tid, {}).update(labels)
    logger.info(
        "[SCAN] +%d Worker traces, total=%d",
        len(worker_ti), len(trace_index),
    )

    logger.info("=" * 70)
    logger.info("Phase 2: Aggregate + Anomaly Detection")
    logger.info("=" * 70)
    t_agg = time.perf_counter()
    src_dst_events, src_dst_map, tw_events, anomalous_tids = (
        await KVCacheLogParseWorker.generate_aggregate_result(trace_index)
    )
    t_agg_elapsed = time.perf_counter() - t_agg

    logger.info(
        "[AGGREGATE] src_dst_groups=%d tw_groups=%d anomalous=%d in %.1fs",
        len(src_dst_events), len(tw_events), len(anomalous_tids), t_agg_elapsed,
    )

    logger.info("=" * 70)
    logger.info("Phase 3: Build Anomalous Detail Rows")
    logger.info("=" * 70)
    t_detail = time.perf_counter()
    detail_rows = KVCacheLogParseWorker._build_anomalous_detail_rows(
        trace_index, anomalous_tids,
    )
    t_detail_elapsed = time.perf_counter() - t_detail
    logger.info(
        "[DETAIL] %d anomalous detail rows in %.1fs",
        len(detail_rows), t_detail_elapsed,
    )

    t_total = time.perf_counter() - t_start

    # Show sample results
    logger.info("=" * 70)
    logger.info("Phase 4: Results Summary")
    logger.info("=" * 70)

    op_counter: Counter = Counter()
    for event in src_dst_events:
        op_counter[getattr(event, "operation", "?")] += 1

    logger.info("--- SrcDst Aggregated Events ---")
    for op, cnt in op_counter.most_common(5):
        logger.info("  %s: %d groups", op, cnt)

    logger.info("--- Top 5 Anomalous Traces (by total_latency) ---")
    top_traces = sorted(anomalous_tids)[:5]
    for tid in top_traces:
        logger.info("  trace=%s", tid[:16])

    logger.info("--- TimeWindow Stats ---")
    high_anomaly_tws = [e for e in tw_events[:1000] if getattr(e, "anomaly_cnt", 0) > 0]
    logger.info("  time_window_events: total=%d, with_anomalies=%d (sampled first 1000)",
                len(tw_events), len(high_anomaly_tws))

    logger.info("=" * 70)
    logger.info(
        "PIPELINE COMPLETE — total %.1fs | scan=%.1fs agg=%.1fs detail=%.1fs",
        t_total, t_scan, t_agg_elapsed, t_detail_elapsed,
    )
    logger.info(
        "traces=%d | src_dst=%d | tw=%d | anomalous=%d | detail_rows=%d",
        len(trace_index), len(src_dst_events), len(tw_events),
        len(anomalous_tids), len(detail_rows),
    )
    logger.info("=" * 70)

    # Clean up temp dirs
    shutil.rmtree(Path(tmp_root).parent, ignore_errors=True)


if __name__ == "__main__":
    asyncio.run(main())
