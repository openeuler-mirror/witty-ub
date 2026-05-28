import sys
import os
import asyncio
import logging
import random
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", ".."))

logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(message)s")
logger = logging.getLogger(__name__)


def _build_mock_results(
    n: int = 2000,
    spike_start: int = 800,
    spike_end: int = 1000,
    spike_multiplier: float = 5.0,
) -> list:
    from latency.schemas.log import LogParseResultModel

    results: list[LogParseResultModel] = []
    for i in range(n):
        in_spike = spike_start <= i < spike_end
        base_total = random.uniform(0.5, 2.0)
        base_c2w = random.uniform(0.3, 1.0)
        base_w2w = random.uniform(0.2, 0.8)
        base_urma_link = random.uniform(0.3, 1.5)
        base_query_meta = random.uniform(0.1, 0.5)

        if in_spike:
            total = base_total * spike_multiplier + random.uniform(0, 3)
            c2w = base_c2w * spike_multiplier + random.uniform(0, 2)
            w2w = base_w2w * spike_multiplier + random.uniform(0, 1)
            urma_link = base_urma_link * spike_multiplier + random.uniform(0, 2)
            query_meta = base_query_meta * spike_multiplier + random.uniform(0, 1)
        else:
            total = base_total
            c2w = base_c2w
            w2w = base_w2w
            urma_link = base_urma_link
            query_meta = base_query_meta

        src_ip = f"10.0.{i % 5}.{i % 256}"
        dst_ip = f"10.1.{i % 3}.{i % 256}"
        pod_ip = f"10.2.0.{i % 10}"

        results.append(LogParseResultModel(
            log_id="test_log_id",
            is_anomalous=False,
            total_latency=total,
            c2w_latency=c2w,
            w2w_urma_latency=w2w,
            urma_link_latency=urma_link,
            worker_query_meta_latency=query_meta,
            src_ip=src_ip,
            dst_ip=dst_ip,
            pod_ip=pod_ip,
            timestamp=f"2025-01-01 00:{i // 60:02d}:{i % 60:02d}.000",
        ))

    return results


async def test_kv_cache_log_parse_worker(log_dir: str = None):
    from latency.task.worker.kv_cache_log_parse_worker import KVCacheLogParseWorker

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


async def test_detect_exception():
    from latency.task.worker.kv_cache_log_parse_worker import KVCacheLogParseWorker

    logger.info("\n" + "=" * 60)
    logger.info("TEST: detect_exception (sliding window P99)")
    logger.info("=" * 60)

    results = _build_mock_results(n=2000, spike_start=800, spike_end=1000)

    start = time.perf_counter()
    events = await KVCacheLogParseWorker.detect_exception(results)
    elapsed = time.perf_counter() - start
    logger.info(f"detect_exception elapsed: {elapsed:.3f}s")

    logger.info(f"Anomalous events: {len(events)}")
    if events:
        offsets = [e.start_log_parse_offset for e in events]
        logger.info(f"  offset range: [{min(offsets)}, {max(offsets)}]")
        spike_in_events = sum(
            1 for e in events if 800 <= e.start_log_parse_offset < 1000
        )
        non_spike_in_events = len(events) - spike_in_events
        logger.info(f"  in spike zone [800,1000): {spike_in_events}")
        logger.info(f"  outside spike zone: {non_spike_in_events}")

        for i, e in enumerate(events[:3]):
            logger.info(f"\n  --- Event {i} ---")
            logger.info(f"    offset: {e.start_log_parse_offset}")
            logger.info(f"    reason: {e.anomaly_reason[:120]}...")

    spike_hit = any(800 <= e.start_log_parse_offset < 1000 for e in events)
    logger.info(f"\nSpike zone detected: {spike_hit}")
    assert spike_hit, "Spike zone [800,1000) should be detected"
    logger.info("=== test_detect_exception PASSED ===\n")


async def test_generate_aggregate_result():
    from latency.task.worker.kv_cache_log_parse_worker import KVCacheLogParseWorker

    logger.info("\n" + "=" * 60)
    logger.info("TEST: generate_aggregate_result")
    logger.info("=" * 60)

    results = _build_mock_results(n=2000, spike_start=800, spike_end=1000)

    start = time.perf_counter()
    agg_events = await KVCacheLogParseWorker.generate_aggregate_result(results)
    elapsed = time.perf_counter() - start
    logger.info(f"generate_aggregate_result elapsed: {elapsed:.3f}s")

    logger.info(f"Aggregated events: {len(agg_events)}")

    src_dst_pairs = set()
    for a in agg_events:
        pair = (a.src_ip, a.dst_ip)
        src_dst_pairs.add(pair)
        logger.info(
            f"  {a.src_ip} → {a.dst_ip} | "
            f"cnt={a.log_parse_result_cnt}, anomaly_cnt={a.anomaly_cnt}, "
            f"p99_total={a.p99_total_latency:.3f}ms, "
            f"p99_urma_link={a.p99_urma_link_latency:.3f}ms"
        )

    assert len(agg_events) > 0, "Should have at least one aggregated event"
    assert len(src_dst_pairs) == len(agg_events), "Each event should be a unique src-dst pair"

    for a in agg_events:
        assert a.p99_total_latency is not None, "p99_total_latency should be computed"
        assert a.ave_total_latency is not None, "ave_total_latency should be computed"

    logger.info("=== test_generate_aggregate_result PASSED ===\n")


async def test_store_result():
    from latency.task.worker.kv_cache_log_parse_worker import KVCacheLogParseWorker
    from latency.database.engine import AsyncSQLiteSingleton
    from latency.schemas.log import LogParseResultModel

    logger.info("\n" + "=" * 60)
    logger.info("TEST: store_result")
    logger.info("=" * 60)

    await AsyncSQLiteSingleton().init_database()

    results = _build_mock_results(n=500, spike_start=200, spike_end=300)
    agg_events = await KVCacheLogParseWorker.generate_aggregate_result(results)
    anomalous_events = await KVCacheLogParseWorker.detect_exception(results)

    logger.info(
        f"Storing: {len(results)} results, "
        f"{len(agg_events)} aggregated events, "
        f"{len(anomalous_events)} anomalous events"
    )

    start = time.perf_counter()
    stored = await KVCacheLogParseWorker.store_result(
        list_log_parse_results=results,
        anomalous_events=anomalous_events,
        anomalous_event_chains=[],
        src_dst_aggregated_events=agg_events,
    )
    elapsed = time.perf_counter() - start
    logger.info(f"store_result elapsed: {elapsed:.3f}s")
    logger.info(f"store_result returned: {stored}")

    from latency.database.managers.log_parse_result import LogParseResultManager
    from latency.database.managers.src_dst_aggregated_event import SrcDstAggregatedEventManager
    from latency.database.managers.anomalous_event import AnomalousEventManager
    from latency.schemas.request import ListLogParseResultRequest

    req = ListLogParseResultRequest(page_num=1, page_cnt=1)
    total_results, _ = await LogParseResultManager.list_log_parse_results(req)
    logger.info(f"DB log_parse_result count: {total_results}")
    assert total_results > 0, "Should have stored log parse results"

    from latency.schemas.request import ListSrcDstAggregatedEventRequest
    agg_req = ListSrcDstAggregatedEventRequest(page_num=1, page_cnt=100)
    total_agg, agg_rows = await SrcDstAggregatedEventManager.list_aggregated_events(agg_req)
    logger.info(f"DB aggregated_event count: {total_agg}")
    assert total_agg > 0, "Should have stored aggregated events"

    ae_list = await AnomalousEventManager.list_anomalous_events_by_log_id("test_log_id")
    logger.info(f"DB anomalous_event count: {len(ae_list)}")

    logger.info("=== test_store_result PASSED ===\n")


async def test_all(log_dir: str = None):
    await test_detect_exception()
    await test_generate_aggregate_result()
    await test_store_result()
    logger.info("\n" + "=" * 60)
    logger.info("ALL TESTS PASSED")
    logger.info("=" * 60)


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
        arg = sys.argv[1]
        if arg == "detect":
            asyncio.run(test_detect_exception())
        elif arg == "aggregate":
            asyncio.run(test_generate_aggregate_result())
        elif arg == "store":
            asyncio.run(test_store_result())
        elif arg == "all":
            asyncio.run(test_all())
        elif os.path.isfile(arg):
            asyncio.run(test_data_file(arg))
        elif os.path.isdir(arg):
            asyncio.run(test_kv_cache_log_parse_worker(arg))
        else:
            logger.error(f"Invalid path or unknown test: {arg}")
    else:
        asyncio.run(test_all())
