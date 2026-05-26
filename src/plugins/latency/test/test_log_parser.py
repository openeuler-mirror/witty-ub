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
    """测试日志解析器"""
    from latency.task.parse import (
        SdkAccessLogParser,
        WorkerAccessLogParser,
        UrmaLogParser,
        RemotePullLogParser,
        LinkLogParser,
        QueryMetaLogParser,
        LogCorrelator,
        ParseResultBuilder,
    )
    from latency.schemas.log import LogParseResultModel

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
        parsed[parser.label] = entries
        logger.info(f"{parser.label}: {len(entries)} entries")

        # 打印前几条解析的条目
        for i, entry in enumerate(entries[:3]):
            logger.info(f"  Entry {i}: trace_id={entry.trace_id}, op={entry.operation}, elapsed={entry.elapsed_us}us")

    correlator = LogCorrelator(parsed)
    correlated = correlator.correlate()

    sdk_entries = parsed.get("SDK access parse", [])
    worker_entries = parsed.get("Worker access parse", [])

    builder = ParseResultBuilder(sdk_entries, worker_entries, correlated, log_dir=log_dir)
    results = builder.build()

    logger.info(f"\n{'='*60}")
    logger.info(f"Total results: {len(results)}")
    logger.info(f"Anomalous: {sum(1 for r in results if r.is_anomalous)}")
    logger.info(f"{'='*60}")

    for i, r in enumerate(results[:5]):  # 只打印前5条
        logger.info(f"\n--- Result {i} ---")
        logger.info(f"  log_id: {r.log_id}")
        logger.info(f"  trace_id: {r.trace_id}")
        logger.info(f"  timestamp: {r.timestamp}")
        logger.info(f"  pod_ip: {r.pod_ip}")
        logger.info(f"  total_latency: {r.total_latency}")
        logger.info(f"  operation: {r.operation}")
        logger.info(f"  data_size: {r.data_size}")
        logger.info(f"  is_anomalous: {r.is_anomalous}")

    logger.info(f"\n{'='*60}")
    logger.info("Model dump serialization test:")
    logger.info(f"{'='*60}")
    if results:
        dump = results[0].model_dump(exclude_none=False)
        logger.info(f"  timestamp type: {type(dump['timestamp']).__name__} = {dump['timestamp']}")
        logger.info(f"  created_at type: {type(dump['created_at']).__name__} = {dump['created_at']}")
        logger.info(f"  log_id: {dump['log_id']}")

    logger.info("\n=== TEST PASSED ===")
    return results


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
