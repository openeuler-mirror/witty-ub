"""
KVCacheLogParseWorker 测试脚本

用法:
    python test_kv_cache_log_parse_worker.py all <log_dir>     # 运行所有测试
    python test_kv_cache_log_parse_worker.py parse <log_id>    # 测试解析
    python test_kv_cache_log_parse_worker.py detect <log_id>   # 测试异常检测
    python test_kv_cache_log_parse_worker.py aggregate <log_id> # 测试聚合
    python test_kv_cache_log_parse_worker.py store <log_id>    # 测试存库
    python test_kv_cache_log_parse_worker.py run <log_id>      # 测试完整流水线
    python test_kv_cache_log_parse_worker.py <log_dir>         # 兼容旧方式（使用log_dir）
"""

import sys
import os
import asyncio
import logging
import time

# 设置模块搜索路径
_test_dir = os.path.dirname(__file__)
_project_root = os.path.abspath(os.path.join(_test_dir, "..", ".."))
sys.path.insert(0, _project_root)

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
logger = logging.getLogger(__name__)


async def test_parse_log(log_id: str):
    """测试日志解析 - 使用 log_id"""
    from latency.task.worker.kv_cache_log_parse_worker import KVCacheLogParseWorker

    logger.info("=" * 60)
    logger.info("TEST: parse_log (log_id=%s)", log_id)
    logger.info("=" * 60)

    start = time.perf_counter()
    results = await KVCacheLogParseWorker.parse_log(log_id=log_id)
    elapsed = time.perf_counter() - start

    total = len(results)
    anomalous = sum(1 for r in results if r.is_anomalous)
    logger.info(f"解析完成: {total:,} 条结果, {anomalous:,} 条异常, 耗时: {elapsed:.3f}s")

    for i, r in enumerate(results[:3]):
        logger.info(f"  [{i}] trace_id={r.trace_id}, total_latency={r.total_latency:.3f}, "
                     f"src_ip={r.src_ip}, dst_ip={r.dst_ip}")

    logger.info("=== TEST PASSED ===")
    return results


async def test_detect_exception(log_id: str):
    """测试异常检测 - 使用 log_id"""
    from latency.task.worker.kv_cache_log_parse_worker import KVCacheLogParseWorker

    logger.info("=" * 60)
    logger.info("TEST: detect_exception (log_id=%s)", log_id)
    logger.info("=" * 60)

    results = await KVCacheLogParseWorker.parse_log(log_id=log_id)
    if not results:
        logger.warning("解析结果为空，跳过异常检测")
        return []

    start = time.perf_counter()
    events = await KVCacheLogParseWorker.detect_exception(results)
    elapsed = time.perf_counter() - start

    logger.info(f"异常检测完成: {len(events):,} 个异常事件, 耗时: {elapsed:.3f}s")

    for i, e in enumerate(events[:3]):
        logger.info(f"  [{i}] id={e.id[:8]}..., reason={e.anomaly_reason[:80]}...")

    logger.info("=== TEST PASSED ===")
    return events


async def test_aggregate(log_id: str):
    """测试聚合统计 - 使用 log_id"""
    from latency.task.worker.kv_cache_log_parse_worker import KVCacheLogParseWorker

    logger.info("=" * 60)
    logger.info("TEST: generate_aggregate_result (log_id=%s)", log_id)
    logger.info("=" * 60)

    results = await KVCacheLogParseWorker.parse_log(log_id=log_id)
    if not results:
        logger.warning("解析结果为空，跳过聚合")
        return [], {}

    start = time.perf_counter()
    agg_events, src_dst_map, _ = await KVCacheLogParseWorker.generate_aggregate_result(results)
    elapsed = time.perf_counter() - start

    logger.info(f"聚合完成: {len(agg_events):,} 个端点对, 耗时: {elapsed:.3f}s")

    for i, a in enumerate(agg_events[:3]):
        logger.info(f"  [{i}] {a.src_ip} -> {a.dst_ip}, "
                     f"count={a.log_parse_result_cnt}, anomaly={a.anomaly_cnt}")

    logger.info("=== TEST PASSED ===")
    return agg_events, src_dst_map


async def test_store(log_id: str):
    """测试存库 - 使用 log_id"""
    from latency.task.worker.kv_cache_log_parse_worker import KVCacheLogParseWorker

    logger.info("=" * 60)
    logger.info("TEST: store_result (log_id=%s)", log_id)
    logger.info("=" * 60)

    results = await KVCacheLogParseWorker.parse_log(log_id=log_id)
    if not results:
        logger.warning("解析结果为空，跳过往存库")
        return False

    events = await KVCacheLogParseWorker.detect_exception(results)
    agg_events, _, time_window_events = await KVCacheLogParseWorker.generate_aggregate_result(results)

    # 更新异常事件的 aggregated_event_id
    for event in events:
        idx = event.start_log_parse_offset
        if 0 <= idx < len(results):
            r = results[idx]
            event.aggregated_event_id = r.aggregated_event_id or ""

    start = time.perf_counter()
    success = await KVCacheLogParseWorker.store_result(
        list_log_parse_results=results,
        anomalous_events=events,
        anomalous_event_chains=[],
        src_dst_aggregated_events=agg_events,
        time_window_aggregated_events=time_window_events,
    )
    elapsed = time.perf_counter() - start

    logger.info(f"存库{'成功' if success else '失败'}, 耗时: {elapsed:.3f}s")
    logger.info("=== TEST PASSED ===")
    return success


async def test_run_pipeline(log_id: str):
    """测试完整流水线 - 使用 log_id"""
    from latency.task.worker.kv_cache_log_parse_worker import KVCacheLogParseWorker

    logger.info("=" * 60)
    logger.info("TEST: run pipeline (log_id=%s)", log_id)
    logger.info("=" * 60)

    start = time.perf_counter()

    # 步骤1: 解析
    logger.info(">>> Step 1: parse_log")
    results = await KVCacheLogParseWorker.parse_log(log_id=log_id)
    logger.info(f"    -> {len(results):,} results")

    # 步骤2: 异常检测
    logger.info(">>> Step 2: detect_exception")
    events = await KVCacheLogParseWorker.detect_exception(results)
    logger.info(f"    -> {len(events):,} events")

    # 步骤3: 聚合
    logger.info(">>> Step 3: generate_aggregate_result")
    agg_events, src_dst_map, time_window_events = await KVCacheLogParseWorker.generate_aggregate_result(results)
    logger.info(f"    -> {len(agg_events):,} aggregated events")

    # 步骤4: 更新异常事件的 aggregated_event_id
    for event in events:
        idx = event.start_log_parse_offset
        if 0 <= idx < len(results):
            r = results[idx]
            event.aggregated_event_id = src_dst_map.get((r.src_ip, r.dst_ip), "")

    # 步骤5: 存库
    logger.info(">>> Step 4: store_result")
    stored = await KVCacheLogParseWorker.store_result(
        list_log_parse_results=results,
        anomalous_events=events,
        anomalous_event_chains=[],
        src_dst_aggregated_events=agg_events,
        time_window_aggregated_events=time_window_events,
    )
    logger.info(f"    -> stored: {stored}")

    elapsed = time.perf_counter() - start
    logger.info(f"流水线完成, 总耗时: {elapsed:.3f}s")
    logger.info("=== TEST PASSED ===")


# ============================================================
# 兼容旧版: 使用 log_dir 直接解析（不经过数据库）
# ============================================================

async def test_parse_log_dir(log_dir: str):
    """兼容旧版: 使用 log_dir 直接解析"""
    from latency.task.worker.kv_cache_log_parse_worker import KVCacheLogParseWorker

    logger.info("=" * 60)
    logger.info("TEST: parse_log (log_dir=%s)", log_dir)
    logger.info("=" * 60)

    start = time.perf_counter()
    results = await KVCacheLogParseWorker.parse_log(log_dir=log_dir)
    elapsed = time.perf_counter() - start

    total = len(results)
    anomalous = sum(1 for r in results if r.is_anomalous)
    logger.info(f"解析完成: {total:,} 条结果, {anomalous:,} 条异常, 耗时: {elapsed:.3f}s")

    logger.info("=== TEST PASSED ===")
    return results


# ============================================================
# 入口
# ============================================================

async def main():
    args = sys.argv[1:]
    if not args:
        print(__doc__)
        return

    cmd = args[0]
    target = args[1] if len(args) > 1 else None

    # 判断是 log_id 还是 log_dir
    is_log_dir = target and (os.path.isdir(target) or os.path.isfile(target))

    if cmd == "all":
        if is_log_dir:
            await test_parse_log_dir(target)
        elif target:
            await test_parse_log(target)
            await test_detect_exception(target)
            await test_aggregate(target)
            await test_store(target)
            await test_run_pipeline(target)
        else:
            logger.error("请提供 log_id 或 log_dir")

    elif cmd == "parse":
        if target and is_log_dir:
            await test_parse_log_dir(target)
        elif target:
            await test_parse_log(target)
        else:
            logger.error("请提供 log_id 或 log_dir")

    elif cmd == "detect":
        await test_detect_exception(target)
    elif cmd == "aggregate":
        await test_aggregate(target)
    elif cmd == "store":
        await test_store(target)
    elif cmd == "run":
        await test_run_pipeline(target)
    elif is_log_dir:
        # 兼容旧版: 直接传入路径
        await test_parse_log_dir(cmd)
    else:
        print(__doc__)


if __name__ == "__main__":
    asyncio.run(main())
