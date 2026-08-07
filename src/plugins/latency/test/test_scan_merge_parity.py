#!/usr/bin/env python3
"""E2E parity harness for T7: df_trace (polars) contract stability.

parse_log now returns a polars DataFrame (df_trace, columns = TRACE_COLUMNS,
one row per trace, ``tid`` column present). This harness snapshots that
df_trace as {"df_trace": {"count": height, "traces": sorted(tid list)}} and
asserts the current implementation is identical to a stored baseline.

Usage:
    # capture baseline:
    PYTHONPATH=<src/plugins> python test/test_scan_merge_parity.py \
        --capture <log_dir> -o .omo/evidence/perf-overhaul-io-aware/task-5-baseline.json

    # pytest mode: compare current implementation against the stored baseline:
    PYTHONPATH=<src/plugins> python -m pytest test/test_scan_merge_parity.py -v
"""

import argparse
import asyncio
import json
import logging
import os
import sys
import time
from pathlib import Path

import pytest

_TEST_DIR = Path(__file__).resolve().parent
_PROJECT_ROOT = _TEST_DIR.parent
_REPO_ROOT = _TEST_DIR.parents[3]
sys.path.insert(0, str(_PROJECT_ROOT))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger("scan-merge-parity")

_DEFAULT_LOG_DIR = _REPO_ROOT / "data/logs/e2e-test-100m"
_DEFAULT_BASELINE = (
    _REPO_ROOT / ".omo/evidence/perf-overhaul-io-aware/task-5-baseline.json"
)


async def scan_snapshot(log_dir: str) -> dict:
    """Run parse_log and snapshot df_trace (row count + sorted trace set)."""
    from latency.task.worker.kv_cache_log_parse_worker import KVCacheLogParseWorker

    t0 = time.perf_counter()
    df_trace = await KVCacheLogParseWorker.parse_log(log_dir=log_dir)
    elapsed = time.perf_counter() - t0

    traces = sorted(t for t in df_trace["tid"].to_list() if t)
    snapshot = {"df_trace": {"count": df_trace.height, "traces": traces}}

    logger.info(
        "[SNAPSHOT] df_trace count=%d traces=%d, %.1fs",
        snapshot["df_trace"]["count"], len(traces), elapsed,
    )
    return snapshot


def assert_parity(current: dict, baseline: dict) -> None:
    """Assert current df_trace snapshot == baseline snapshot."""
    assert "df_trace" in current, "current snapshot missing df_trace key"
    assert "df_trace" in baseline, "baseline missing df_trace key"

    cur = current["df_trace"]
    base = baseline["df_trace"]
    assert cur["count"] == base["count"], (
        f"df_trace count {cur['count']} != baseline {base['count']}"
    )
    assert cur["traces"] == base["traces"], (
        f"df_trace trace set differs (len {len(cur['traces'])} "
        f"vs baseline {len(base['traces'])})"
    )
    logger.info("[PARITY] OK — df_trace identical to baseline (count=%d)", base["count"])


def test_parity_vs_baseline():
    if not _DEFAULT_LOG_DIR.is_dir():
        pytest.skip(f"no e2e data at {_DEFAULT_LOG_DIR}")
    if not _DEFAULT_BASELINE.exists():
        pytest.skip(f"no baseline at {_DEFAULT_BASELINE}")

    baseline = json.loads(_DEFAULT_BASELINE.read_text())
    current = asyncio.run(scan_snapshot(str(_DEFAULT_LOG_DIR)))
    assert_parity(current, baseline)


def test_baseline_file_exists():
    assert _DEFAULT_BASELINE.exists(), (
        "baseline missing — run: python test/test_scan_merge_parity.py "
        f"--capture {_DEFAULT_LOG_DIR} -o {_DEFAULT_BASELINE}"
    )


async def main() -> None:
    parser = argparse.ArgumentParser(description="T7 df_trace parity harness")
    parser.add_argument(
        "--capture",
        metavar="LOG_DIR",
        help="capture baseline snapshot of the given log dir",
    )
    parser.add_argument("-o", "--output", default=str(_DEFAULT_BASELINE))
    args = parser.parse_args()

    if args.capture:
        snapshot = await scan_snapshot(args.capture)
        out = Path(args.output)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(
            json.dumps(snapshot, indent=1, sort_keys=True) + "\n"
        )
        logger.info("[BASELINE] written to %s", out)
        return

    snapshot = await scan_snapshot(str(_DEFAULT_LOG_DIR))
    baseline = json.loads(_DEFAULT_BASELINE.read_text())
    assert_parity(snapshot, baseline)


if __name__ == "__main__":
    asyncio.run(main())
