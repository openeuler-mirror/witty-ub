import sys
import os
import asyncio
import logging
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(message)s")
logger = logging.getLogger(__name__)


async def test_kv_cache_log_parse_worker(log_dir: str = None):
    from latency.task.worker.kv_cache_log_parse_worker import KVCacheLogParseWorker
    from latency.database.engine import AsyncSQLiteSingleton
    from latency.database.managers.log_parse_result import LogParseResultManager
    from latency.schemas.request import ListLogParseResultRequest

    if log_dir is None:
        log_dir = os.path.join(os.path.dirname(__file__), "test_data")

    logger.info(f"Testing KVCacheLogParseWorker with dir: {log_dir}")
    logger.info(f"Directory exists: {os.path.exists(log_dir)}")

    if not os.path.exists(log_dir):
        logger.error(f"Directory not found: {log_dir}")
        return

    start = time.perf_counter()
    results = await KVCacheLogParseWorker.parse_log(log_dir)
    elapsed = time.perf_counter() - start
    logger.info(f"\nParse elapsed: {elapsed:.3f}s")

    total = len(results)
    anomalous = sum(1 for r in results if r.is_anomalous)
    logger.info(f"\n{'='*60}")
    logger.info(f"Total results: {total}")
    logger.info(f"Anomalous: {anomalous}")
    logger.info(f"{'='*60}")

    for i, r in enumerate(results[:5]):
        logger.info(f"\n--- Result {i} ---")
        logger.info(f"  trace_id: {r.trace_id}")
        logger.info(f"  timestamp: {r.timestamp}")
        logger.info(f"  pod_ip: {r.pod_ip}")
        logger.info(f"  total_latency: {r.total_latency}")
        logger.info(f"  operation: {r.operation}")
        logger.info(f"  is_anomalous: {r.is_anomalous}")

    logger.info("\n=== TEST PASSED ===")


async def test_data_file(data_file: str):
    import tempfile
    import shutil

    temp_dir = tempfile.mkdtemp(prefix="latency_worker_test_")
    sdk_dir = os.path.join(temp_dir, "SDK_test")
    os.makedirs(sdk_dir)

    shutil.copy(data_file, os.path.join(sdk_dir, os.path.basename(data_file)))
    logger.info(f"Created temp test dir: {temp_dir}")

    try:
        await test_kv_cache_log_parse_worker(temp_dir)
    finally:
        shutil.rmtree(temp_dir)
        logger.info(f"Cleaned up temp dir: {temp_dir}")


if __name__ == "__main__":
    if len(sys.argv) > 1:
        path = sys.argv[1]
        if os.path.isfile(path):
            asyncio.run(test_data_file(path))
        elif os.path.isdir(path):
            asyncio.run(test_kv_cache_log_parse_worker(path))
        else:
            logger.error(f"Invalid path: {path}")
    else:
        data_file = os.path.join(
            os.path.dirname(__file__),
            "..",
            "..",
            "..",
            "..",
            "data",
            "ds_client_access_1234.log",
        )
        if os.path.exists(data_file):
            asyncio.run(test_data_file(data_file))
        else:
            logger.error(f"Default test file not found: {data_file}")
            logger.info(
                "Usage: python test_kv_cache_log_parse_worker.py <log_dir>"
            )
