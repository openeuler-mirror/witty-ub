"""
KVCacheLogParseWorker 测试脚本

用法:
    python test_kv_cache_log_parse_worker.py all <log_dir>     # 运行所有测试
    python test_kv_cache_log_parse_worker.py parse <log_id>    # 测试解析
    python test_kv_cache_log_parse_worker.py anomaly <log_id>  # 测试异常明细（替代已删的 detect）
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


async def _parse_target(target: str):
    """解析 log_id 或 log_dir 为 trace_index（parse_log 双模式）"""
    from latency.task.worker.kv_cache_log_parse_worker import KVCacheLogParseWorker

    if os.path.isdir(target) or os.path.isfile(target):
        return await KVCacheLogParseWorker.parse_log(log_dir=target)
    return await KVCacheLogParseWorker.parse_log(log_id=target)


async def test_parse_log(log_id: str):
    """测试日志解析 - 使用 log_id"""
    logger.info("=" * 60)
    logger.info("TEST: parse_log (log_id=%s)", log_id)
    logger.info("=" * 60)

    start = time.perf_counter()
    trace_index = await _parse_target(log_id)
    elapsed = time.perf_counter() - start

    sdk_entries = trace_index.get("SDK access parse", [])
    total = len(sdk_entries)
    logger.info(f"解析完成: {total:,} 条 SDK 条目, 耗时: {elapsed:.3f}s")

    for i, r in enumerate(sdk_entries[:3]):
        logger.info(f"  [{i}] trace_id={r[5]}, elapsed_us={r[2]}, "
                     f"src_addr={r[11]}, dst_addr={r[12]}")

    logger.info("=== TEST PASSED ===")
    return trace_index


async def test_anomaly(target: str):
    """测试异常明细（detect 已删，异常判定由聚合侧承担）"""
    from latency.task.worker.kv_cache_log_parse_worker import KVCacheLogParseWorker

    logger.info("=" * 60)
    logger.info("TEST: anomaly detail rows (target=%s)", target)
    logger.info("=" * 60)

    trace_index = await _parse_target(target)
    if not trace_index.get("SDK access parse"):
        logger.warning("解析结果为空，跳过异常判定")
        return [], set()

    start = time.perf_counter()
    _, _, _, anom_tids, metrics_table = (
        await KVCacheLogParseWorker._aggregate_three_way(trace_index)
    )
    # T4：metrics_table 是轻量 dict 行，仅对异常 trace 物化 dataclass
    detail_rows = [
        KVCacheLogParseWorker._make_field_row(m, "")
        for m in metrics_table if m["tid"] in anom_tids
    ]
    elapsed = time.perf_counter() - start

    logger.info(f"异常明细完成: {len(detail_rows):,} 条, 耗时: {elapsed:.3f}s")

    for i, r in enumerate(detail_rows[:3]):
        logger.info(f"  [{i}] trace_id={r.trace_id}, total_latency={r.total_latency:.3f}")

    logger.info("=== TEST PASSED ===")
    return detail_rows, anom_tids


async def test_aggregate(target: str):
    """测试聚合统计"""
    from latency.task.worker.kv_cache_log_parse_worker import KVCacheLogParseWorker

    logger.info("=" * 60)
    logger.info("TEST: generate_aggregate_result (target=%s)", target)
    logger.info("=" * 60)

    trace_index = await _parse_target(target)
    if not trace_index.get("SDK access parse"):
        logger.warning("解析结果为空，跳过聚合")
        return [], {}

    start = time.perf_counter()
    agg_events, src_dst_map, time_window_events, anom_tids = (
        await KVCacheLogParseWorker.generate_aggregate_result(trace_index)
    )
    elapsed = time.perf_counter() - start

    logger.info(
        f"聚合完成: {len(agg_events):,} 个端点对, "
        f"{len(time_window_events):,} 个时间窗, {len(anom_tids):,} 个异常 trace, "
        f"耗时: {elapsed:.3f}s"
    )

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

    trace_index = await KVCacheLogParseWorker.parse_log(log_id=log_id)
    if not trace_index.get("SDK access parse"):
        logger.warning("解析结果为空，跳过往存库")
        return False

    agg_events, _, time_window_events, anom_tids = (
        await KVCacheLogParseWorker.generate_aggregate_result(trace_index)
    )
    _, _, _, _, metrics_table = (
        await KVCacheLogParseWorker._aggregate_three_way(trace_index)
    )
    detail_rows = [
        KVCacheLogParseWorker._make_field_row(m, "")
        for m in metrics_table if m["tid"] in anom_tids
    ]

    start = time.perf_counter()
    success = await KVCacheLogParseWorker.store_result(
        anomalous_detail_rows=detail_rows,
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
    trace_index = await KVCacheLogParseWorker.parse_log(log_id=log_id)
    sdk_count = len(trace_index.get("SDK access parse", []))
    logger.info(f"    -> {sdk_count:,} SDK entries")

    # 步骤2: 聚合（含异常判定 + 轻量 metrics 表）
    logger.info(">>> Step 2: _aggregate_three_way")
    agg_events, src_dst_map, time_window_events, anom_tids, metrics_table = (
        await KVCacheLogParseWorker._aggregate_three_way(trace_index)
    )
    logger.info(f"    -> {len(agg_events):,} aggregated events, "
                f"{len(anom_tids):,} anomalous tids")

    # 步骤3: 异常明细行（metrics 表按 anomalous_tids 过滤 + 物化 + is_anomalous=True）
    logger.info(">>> Step 3: build anomalous detail rows")
    detail_rows = [
        KVCacheLogParseWorker._make_field_row(m, "", is_anomalous=True)
        for m in metrics_table if m["tid"] in anom_tids
    ]
    for row in detail_rows:
        op = (row.operation or "").strip().upper()
        op_key = "SET" if "SET" in op else "GET"
        row.aggregated_event_id = src_dst_map.get(
            (row.src_ip or "", row.dst_ip or "", op_key), ""
        )
    logger.info(f"    -> {len(detail_rows):,} detail rows")

    # 步骤4: 存库
    logger.info(">>> Step 4: store_result")
    stored = await KVCacheLogParseWorker.store_result(
        anomalous_detail_rows=detail_rows,
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
    trace_index = await KVCacheLogParseWorker.parse_log(log_dir=log_dir)
    elapsed = time.perf_counter() - start

    total = len(trace_index.get("SDK access parse", []))
    logger.info(f"解析完成: {total:,} 条 SDK 条目, 耗时: {elapsed:.3f}s")

    logger.info("=== TEST PASSED ===")
    return trace_index


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
            await test_anomaly(target)
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

    elif cmd in ("detect", "anomaly"):
        await test_anomaly(target)
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
