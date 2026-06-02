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
    from latency.parse.correlation.correlator import IndexManager, WorkerUrmaCorrelator, WorkerRemotePullCorrelator

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

    # 添加诊断日志：检查 parse_log 内部的关联过程
    logger.info("\n" + "=" * 60)
    logger.info("DIAGNOSTIC: 检查 parse_log 内部的关联过程")
    logger.info("=" * 60)
    
    # 重新解析以获取中间结果
    from latency.parse import (
        SdkAccessLogParser,
        WorkerAccessLogParser,
        UrmaLogParser,
        RemotePullLogParser,
        LinkLogParser,
        QueryMetaLogParser,
        LogCorrelator,
    )
    from latency.common.ds_log_io import glob_paths
    from latency.schemas.request import ParseConfig
    import asyncio
    
    parsers = [
        SdkAccessLogParser(),
        WorkerAccessLogParser(),
        UrmaLogParser(),
        RemotePullLogParser(),
        LinkLogParser(),
        QueryMetaLogParser(),
    ]
    
    parsed = {}
    for parser in parsers:
        paths = glob_paths([os.path.join(log_dir, p) for p in parser.patterns])
        logger.info(f"[{parser.label}] found {len(paths)} file(s)")
        all_entries = []
        for path in paths:
            pod_ip = parser.extract_pod_ip(path)
            with open(path, 'r', errors='replace') as f:
                for line in f:
                    entry = parser.match_line(line, pod_ip)
                    if entry:
                        all_entries.append(entry)
        parsed[parser.label] = all_entries
        logger.info(f"  [{parser.label}] parsed {len(all_entries)} entries")
    
    # 检查 trace_id 分布
    worker_entries = parsed.get("Worker access parse", [])
    urma_entries = parsed.get("Worker urma parse", [])
    remote_pull_entries = parsed.get("Worker remote pull parse", [])
    
    logger.info(f"\n--- trace_id 分布统计 ---")
    worker_trace_ids = set(w.trace_id for w in worker_entries if w.trace_id)
    urma_trace_ids = set(u.trace_id for u in urma_entries if u.trace_id)
    pull_trace_ids = set(p.trace_id for p in remote_pull_entries if p.trace_id)
    
    logger.info(f"Worker trace_id 数量: {len(worker_trace_ids)} (总条目: {len(worker_entries)})")
    logger.info(f"URMA trace_id 数量: {len(urma_trace_ids)} (总条目: {len(urma_entries)})")
    logger.info(f"RemotePull trace_id 数量: {len(pull_trace_ids)} (总条目: {len(remote_pull_entries)})")
    
    # 检查 trace_id 重叠
    worker_urma_overlap = worker_trace_ids & urma_trace_ids
    worker_pull_overlap = worker_trace_ids & pull_trace_ids
    
    logger.info(f"\n--- trace_id 重叠检查 ---")
    logger.info(f"Worker ∩ URMA: {len(worker_urma_overlap)} 个共同 trace_id")
    logger.info(f"Worker ∩ RemotePull: {len(worker_pull_overlap)} 个共同 trace_id")
    
    if len(worker_urma_overlap) == 0:
        logger.warning("⚠️ Worker 和 URMA 没有共同的 trace_id！")
        if worker_entries and urma_entries:
            logger.info(f"  Worker 示例 trace_id: {worker_entries[0].trace_id}")
            logger.info(f"  URMA 示例 trace_id: {urma_entries[0].trace_id if urma_entries else 'N/A'}")
    
    # 检查 pod_ip 分布
    worker_pod_ips = set(w.pod_ip for w in worker_entries)
    urma_pod_ips = set(u.pod_ip for u in urma_entries if u.pod_ip)
    worker_urma_pod_overlap = worker_pod_ips & urma_pod_ips
    
    logger.info(f"\n--- pod_ip 分布检查 ---")
    logger.info(f"Worker pod_ip 数量: {len(worker_pod_ips)}")
    logger.info(f"URMA pod_ip 数量: {len(urma_pod_ips)}")
    logger.info(f"Worker ∩ URMA pod_ip: {len(worker_urma_pod_overlap)}")
    
    if len(worker_urma_pod_overlap) == 0:
        logger.warning("⚠️ Worker 和 URMA 没有共同的 pod_ip！")
    
    # 构建关联器并检查中间结果
    if worker_entries or urma_entries:
        logger.info(f"\n--- 构建 IndexManager 和 Correlator ---")
        index_manager = IndexManager(
            worker_entries=worker_entries,
            urma_entries=urma_entries,
            remote_pull_entries=remote_pull_entries,
            link_entries=parsed.get("Worker link parse", []),
            query_meta_entries=parsed.get("Worker query meta parse", []),
        )
        
        logger.info(f"IndexManager 索引统计:")
        logger.info(f"  worker_by_trace: {len(index_manager.worker_by_trace)}")
        logger.info(f"  urma_traced_by_trace: {len(index_manager.urma_traced_by_trace)}")
        logger.info(f"  urma_untraced_by_pod: {len(index_manager.urma_untraced_by_pod)}")
        logger.info(f"  pulls_by_trace: {len(index_manager.pulls_by_trace)}")
        
        # 检查 Worker Remote Pull 关联
        worker_remote_pull_map = WorkerRemotePullCorrelator(index_manager).correlate()
        logger.info(f"\nWorker Remote Pull 关联结果: {len(worker_remote_pull_map)} 个 Worker 关联到 Remote Pull")
        
        # 检查 Worker URMA 关联
        worker_urma_correlator = WorkerUrmaCorrelator(index_manager)
        worker_urma_map, worker_worker_urma_map = worker_urma_correlator.correlate(worker_remote_pull_map)
        logger.info(f"Worker URMA 关联结果: {len(worker_urma_map)} 个 Worker 关联到 URMA")
        logger.info(f"Worker Worker URMA 关联结果: {len(worker_worker_urma_map)} 个 Worker 关联到 Worker-Worker URMA")
        
        if len(worker_urma_map) == 0:
            logger.warning("⚠️ Worker→URMA 关联完全失败！可能原因:")
            if len(worker_remote_pull_map) == 0:
                logger.warning("  1. worker_remote_pull_map 为空（Remote Pull 没有与 Worker 关联）")
            if len(index_manager.urma_traced_by_trace) == 0:
                logger.warning("  2. urma_traced_by_trace 为空（URMA 没有 trace_id）")
            if len(index_manager.urma_untraced_by_pod) == 0:
                logger.warning("  3. urma_untraced_by_pod 为空（没有未追踪的 URMA）")
            
            # 采样检查第一个 Worker 的关联过程
            if worker_entries:
                w = worker_entries[0]
                logger.info(f"\n--- 采样检查第一个 Worker ---")
                logger.info(f"  Worker trace_id: {w.trace_id}")
                logger.info(f"  Worker pod_ip: {w.pod_ip}")
                logger.info(f"  Worker object_key: {w.object_key}")
                
                urma_candidates = index_manager.urma_traced_by_trace.get(w.trace_id, [])
                pulls = worker_remote_pull_map.get(0, [])
                logger.info(f"  URMA candidates (by trace_id): {len(urma_candidates)}")
                logger.info(f"  Remote Pulls (for this worker): {len(pulls)}")
                
                cached = index_manager.urma_untraced_by_pod.get(w.pod_ip)
                logger.info(f"  Untraced URMA (by pod_ip): {'有' if cached else '无'}")
    
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
    agg_events, src_dst_to_agg_id_map = await KVCacheLogParseWorker.generate_aggregate_result(results)
    elapsed = time.perf_counter() - start
    logger.info(f"generate_aggregate_result elapsed: {elapsed:.3f}s")

    logger.info(f"Aggregated events: {len(agg_events)}")
    logger.info(f"src_dst_to_agg_id_map entries: {len(src_dst_to_agg_id_map)}")

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
    agg_events, src_dst_to_agg_id_map = await KVCacheLogParseWorker.generate_aggregate_result(results)
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
