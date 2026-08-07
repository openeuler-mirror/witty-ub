"""日志解析器测试模块"""
import sys
import os
import asyncio
import logging
import tempfile
import shutil

# 添加模块搜索路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

# 设置日志
logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(message)s")
logger = logging.getLogger(__name__)


async def test_log_parser(log_dir: str = None):
    """测试日志解析器（关联/构建阶段已删，改用聚合三路产出验证链路）"""
    from latency.parse import (
        SdkAccessLogParser,
        WorkerAccessLogParser,
        UrmaLogParser,
        RemotePullLogParser,
        LinkLogParser,
        QueryMetaLogParser,
    )
    from latency.task.worker.kv_cache_log_parse_worker import KVCacheLogParseWorker

    # 如果没有指定日志目录，使用默认的测试数据目录
    if log_dir is None:
        log_dir = os.path.join(os.path.dirname(__file__), "test_data")

    logger.info(f"Testing with dir: {log_dir}")
    logger.info(f"Directory exists: {os.path.exists(log_dir)}")

    if not os.path.exists(log_dir):
        logger.error(f"Directory not found: {log_dir}")
        return

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
        entries = parser.parse(log_dir)
        # 聚合侧消费 TupleField 序元组（parse_log scanner 产物形态），单 parser 返回 LogEntry
        parsed[parser.label] = [
            (
                e.timestamp, e.operation, e.elapsed_us, e.data_size,
                e.object_key, e.trace_id, e.pod_ip, e.status_code,
                e.resp_msg, e.entry_type, e.cluster_name, e.src_addr,
                e.dst_addr, e.inflight_count, e.request_size, e.log_id,
            )
            for e in entries
        ]
        logger.info(f"{parser.label}: {len(entries)} entries")

        # 打印前几条解析的条目
        for i, entry in enumerate(entries[:3]):
            logger.info(f"  Entry {i}: trace_id={entry.trace_id}, op={entry.operation}, "
                        f"elapsed={entry.elapsed_us}us, cluster_name={entry.cluster_name}")

    # 关联/结果构建阶段已删除（Todo 1）；用聚合三路产出（metrics 表 + src_dst +
    # time_window + 异常 trace）验证整条解析链路仍可用。
    src_dst_events, src_dst_map, time_window_events, anom_tids, metrics_table = (
        await KVCacheLogParseWorker._aggregate_three_way(parsed)
    )

    # T4：metrics_table 是轻量 dict 行，仅对展示/序列化按需物化前 5 行
    field_rows = [
        KVCacheLogParseWorker._make_field_row(m, "") for m in metrics_table[:5]
    ]

    logger.info(f"\n{'='*60}")
    logger.info(f"Metrics table rows: {len(metrics_table)}")
    logger.info(f"src_dst aggregated: {len(src_dst_events)}")
    logger.info(f"time_window aggregated: {len(time_window_events)}")
    logger.info(f"Anomalous trace ids: {len(anom_tids)}")
    logger.info(f"{'='*60}")

    for i, r in enumerate(field_rows):
        logger.info(f"\n--- Field row {i} ---")
        logger.info(f"  trace_id: {r.trace_id}")
        logger.info(f"  timestamp: {r.timestamp}")
        logger.info(f"  pod_ips: {r.pod_ips}")
        logger.info(f"  cluster_name: {r.cluster_name}")
        logger.info(f"  host: {r.host}")
        logger.info(f"  total_latency: {r.total_latency}")
        logger.info(f"  operation: {r.operation}")
        logger.info(f"  src_ip: {r.src_ip} dst_ip: {r.dst_ip}")
        logger.info(f"  is_anomalous: {r.is_anomalous}")

    logger.info(f"\n{'='*60}")
    logger.info("Field row serialization (dataclass -> dict) test:")
    logger.info(f"{'='*60}")
    if field_rows:
        from dataclasses import asdict
        dump = asdict(field_rows[0])
        logger.info(f"  timestamp type: {type(dump.get('timestamp')).__name__}")
        logger.info(f"  total_latency: {dump.get('total_latency')}")

    logger.info("\n=== TEST PASSED ===")
    return field_rows


async def test_data_file(data_file: str):
    """测试指定的数据文件"""
    import tempfile
    import shutil

    # 创建临时测试目录结构
    temp_dir = tempfile.mkdtemp(prefix="latency_test_")
    sdk_dir = os.path.join(temp_dir, "SDK_test")
    os.makedirs(sdk_dir)

    # 复制日志文件到临时目录
    shutil.copy(data_file, os.path.join(sdk_dir, os.path.basename(data_file)))
    logger.info(f"Created temp test dir: {temp_dir}")

    try:
        await test_log_parser(temp_dir)
    finally:
        # 清理临时目录
        shutil.rmtree(temp_dir)
        logger.info(f"Cleaned up temp dir: {temp_dir}")


if __name__ == "__main__":
    # 获取命令行参数
    if len(sys.argv) > 1:
        # 如果提供了参数，测试指定的文件或目录
        path = sys.argv[1]
        if os.path.isfile(path):
            asyncio.run(test_data_file(path))
        elif os.path.isdir(path):
            asyncio.run(test_log_parser(path))
        else:
            logger.error(f"Invalid path: {path}")
    else:
        # 默认测试 data/ds_client_access_1234.log 文件
        data_file = os.path.join(os.path.dirname(__file__), "..", "..", "..", "..", "data", "ds_client_access_1234.log")
        if os.path.exists(data_file):
            asyncio.run(test_data_file(data_file))
        else:
            logger.error(f"Default test file not found: {data_file}")
            logger.info("Usage: python test_log_parser.py [path_to_file_or_dir]")
