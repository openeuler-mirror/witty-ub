"""KVCacheLogParseWorker cProfile performance test.

Usage:
    python test_kv_cache_log_parse_worker_profile.py parse <log_id|log_dir>
    python test_kv_cache_log_parse_worker_profile.py detect <log_id|log_dir>
    python test_kv_cache_log_parse_worker_profile.py aggregate <log_id|log_dir>
    python test_kv_cache_log_parse_worker_profile.py pipeline <log_id|log_dir>
    python test_kv_cache_log_parse_worker_profile.py run <log_id|log_dir>

Examples:
    python test_kv_cache_log_parse_worker_profile.py parse /data/logs/sample
    python test_kv_cache_log_parse_worker_profile.py pipeline <log_id> \
        --output /data/profiles/pipeline.prof --limit 50
    python test_kv_cache_log_parse_worker_profile.py run /data/logs/sample \
        --output /data/profiles/run.prof --limit 50

The detect and aggregate commands prepare parse results before enabling cProfile,
so their reports contain only the requested stage. The pipeline command profiles
parse, anomaly detection, and aggregation together. It does not write to the
database. The run command profiles the same complete workflow as the run command
in test_kv_cache_log_parse_worker.py, including database storage. When run receives
a local path, it automatically registers that path as a log file so all stored
results have a valid log ID. The all command remains an alias of pipeline.
"""

import argparse
import asyncio
import cProfile
from datetime import datetime
import logging
import os
from pathlib import Path
import pstats
import sys
import tempfile
import time
from typing import Awaitable, Callable


_TEST_DIR = Path(__file__).resolve().parent
_PROJECT_ROOT = _TEST_DIR.parent.parent
sys.path.insert(0, str(_PROJECT_ROOT))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
)
logger = logging.getLogger(__name__)

ProfileOperation = Callable[[], Awaitable[dict[str, object]]]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "command",
        choices=("parse", "detect", "aggregate", "pipeline", "run", "all"),
        help="Stage to profile; run stores results and all is an alias of pipeline",
    )
    parser.add_argument("target", help="Database log ID or local log directory")
    parser.add_argument(
        "--output",
        type=Path,
        help="Binary .prof output path; defaults to /tmp/witty-ub-cprofile",
    )
    parser.add_argument(
        "--report",
        type=Path,
        help="Text report path; defaults to the .prof path with a .txt suffix",
    )
    parser.add_argument(
        "--sort",
        choices=("cumulative", "tottime", "calls", "name"),
        default="cumulative",
        help="Console report sort order",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=40,
        help="Number of functions printed in each report section",
    )
    return parser.parse_args()


def default_profile_path(command: str) -> Path:
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    profile_dir = Path(tempfile.gettempdir()) / "witty-ub-cprofile"
    return profile_dir / f"{command}-{timestamp}-{os.getpid()}.prof"


async def parse_target(target: str):
    from latency.task.worker.kv_cache_log_parse_worker import KVCacheLogParseWorker

    target_path = Path(target).expanduser()
    if target_path.exists():
        return await KVCacheLogParseWorker.parse_log(log_dir=str(target_path.resolve()))
    return await KVCacheLogParseWorker.parse_log(log_id=target)


async def prepare_run_target(target: str) -> tuple[str, bool]:
    """Return a database log ID, registering a local path when necessary."""
    target_path = Path(target).expanduser()
    if not target_path.exists():
        if target_path.is_absolute() or len(target_path.parts) > 1:
            raise FileNotFoundError(f"Local log path does not exist: {target_path}")
        return target, False

    from latency.database.engine import AsyncSQLiteSingleton
    from latency.database.managers.log_file import LogFileManager
    from latency.schemas.log import LogFileModel

    resolved_path = target_path.resolve()
    database = AsyncSQLiteSingleton()
    if not await database.init_database():
        raise RuntimeError("Failed to initialize the profile database")

    log_file = LogFileModel(
        name=resolved_path.name,
        file_path=str(resolved_path),
    )
    if not await LogFileManager.add_log_file(log_file):
        raise RuntimeError(f"Failed to register local log path: {resolved_path}")

    logger.info(
        "Registered local log path for run profile: log_id=%s, path=%s",
        log_file.id,
        resolved_path,
    )
    return log_file.id, True


def write_text_report(
    profile_path: Path,
    report_path: Path,
    command: str,
    target: str,
    elapsed: float,
    summary: dict[str, object],
    limit: int,
) -> None:
    report_path.parent.mkdir(parents=True, exist_ok=True)
    with report_path.open("w", encoding="utf-8") as stream:
        stream.write("KVCacheLogParseWorker cProfile report\n")
        stream.write(f"command: {command}\n")
        stream.write(f"target: {target}\n")
        stream.write(f"elapsed_seconds: {elapsed:.6f}\n")
        stream.write(f"summary: {summary}\n\n")

        stats = pstats.Stats(str(profile_path), stream=stream).strip_dirs()
        stream.write("Top functions by cumulative time\n")
        stats.sort_stats("cumulative").print_stats(limit)
        stream.write("\nTop functions by internal time\n")
        stats.sort_stats("tottime").print_stats(limit)


async def profile_operation(
    operation: ProfileOperation,
    command: str,
    target: str,
    profile_path: Path,
    report_path: Path,
    sort_by: str,
    limit: int,
) -> dict[str, object]:
    profile_path.parent.mkdir(parents=True, exist_ok=True)
    profiler = cProfile.Profile()
    started = time.perf_counter()

    profiler.enable()
    try:
        summary = await operation()
    finally:
        profiler.disable()
        profiler.dump_stats(str(profile_path))

    elapsed = time.perf_counter() - started
    write_text_report(
        profile_path=profile_path,
        report_path=report_path,
        command=command,
        target=target,
        elapsed=elapsed,
        summary=summary,
        limit=limit,
    )

    logger.info("Profile complete in %.3fs: %s", elapsed, summary)
    logger.info("Binary profile: %s", profile_path)
    logger.info("Text report: %s", report_path)
    logger.info(
        "cProfile records the parent process; ProcessPool child CPU time requires "
        "profiling inside process_worker_func"
    )

    pstats.Stats(str(profile_path)).strip_dirs().sort_stats(sort_by).print_stats(limit)
    return summary


async def run_profile(args: argparse.Namespace) -> dict[str, object]:
    from latency.task.worker.kv_cache_log_parse_worker import KVCacheLogParseWorker

    command = "pipeline" if args.command == "all" else args.command
    profile_path = (args.output or default_profile_path(command)).expanduser().resolve()
    report_path = (
        args.report.expanduser().resolve()
        if args.report
        else profile_path.with_suffix(".txt")
    )

    if args.limit <= 0:
        raise ValueError("--limit must be greater than zero")

    if command == "parse":
        async def operation() -> dict[str, object]:
            results = await parse_target(args.target)
            return {"parse_results": len(results)}

    elif command == "detect":
        logger.info("Preparing parse results outside cProfile")
        results = await parse_target(args.target)

        async def operation() -> dict[str, object]:
            events = await KVCacheLogParseWorker.detect_exception(results)
            return {
                "parse_results": len(results),
                "anomalous_events": len(events),
            }

    elif command == "aggregate":
        logger.info("Preparing parse and detection results outside cProfile")
        results = await parse_target(args.target)
        events = await KVCacheLogParseWorker.detect_exception(results)

        async def operation() -> dict[str, object]:
            aggregates, _ = await KVCacheLogParseWorker.generate_aggregate_result(results)
            return {
                "parse_results": len(results),
                "anomalous_events": len(events),
                "aggregated_events": len(aggregates),
            }

    elif command == "pipeline":
        async def operation() -> dict[str, object]:
            parse_started = time.perf_counter()
            results = await parse_target(args.target)
            parse_elapsed = time.perf_counter() - parse_started

            detect_started = time.perf_counter()
            events = await KVCacheLogParseWorker.detect_exception(results)
            detect_elapsed = time.perf_counter() - detect_started

            aggregate_started = time.perf_counter()
            aggregates, _ = await KVCacheLogParseWorker.generate_aggregate_result(results)
            aggregate_elapsed = time.perf_counter() - aggregate_started

            return {
                "parse_results": len(results),
                "anomalous_events": len(events),
                "aggregated_events": len(aggregates),
                "parse_seconds": round(parse_elapsed, 6),
                "detect_seconds": round(detect_elapsed, 6),
                "aggregate_seconds": round(aggregate_elapsed, 6),
            }

    elif command == "run":
        log_id, registered_local_path = await prepare_run_target(args.target)

        async def operation() -> dict[str, object]:
            parse_started = time.perf_counter()
            results = await KVCacheLogParseWorker.parse_log(log_id=log_id)
            parse_elapsed = time.perf_counter() - parse_started

            detect_started = time.perf_counter()
            events = await KVCacheLogParseWorker.detect_exception(results)
            detect_elapsed = time.perf_counter() - detect_started

            aggregate_started = time.perf_counter()
            aggregates, src_dst_map = (
                await KVCacheLogParseWorker.generate_aggregate_result(results)
            )
            aggregate_elapsed = time.perf_counter() - aggregate_started

            link_started = time.perf_counter()
            for event in events:
                idx = event.start_log_parse_offset
                if 0 <= idx < len(results):
                    result = results[idx]
                    event.aggregated_event_id = src_dst_map.get(
                        (result.src_ip, result.dst_ip), ""
                    )
            link_elapsed = time.perf_counter() - link_started

            store_started = time.perf_counter()
            stored = await KVCacheLogParseWorker.store_result(
                list_log_parse_results=results,
                anomalous_events=events,
                anomalous_event_chains=[],
                src_dst_aggregated_events=aggregates,
            )
            store_elapsed = time.perf_counter() - store_started

            return {
                "log_id": log_id,
                "registered_local_path": registered_local_path,
                "parse_results": len(results),
                "anomalous_events": len(events),
                "aggregated_events": len(aggregates),
                "stored": stored,
                "parse_seconds": round(parse_elapsed, 6),
                "detect_seconds": round(detect_elapsed, 6),
                "aggregate_seconds": round(aggregate_elapsed, 6),
                "link_seconds": round(link_elapsed, 6),
                "store_seconds": round(store_elapsed, 6),
            }

    return await profile_operation(
        operation=operation,
        command=command,
        target=args.target,
        profile_path=profile_path,
        report_path=report_path,
        sort_by=args.sort,
        limit=args.limit,
    )


def main() -> None:
    args = parse_args()
    asyncio.run(run_profile(args))


if __name__ == "__main__":
    main()
