import asyncio
import logging
import os
from latency.ENUM.task import TaskStatusEnum, TaskTypeEnum
from latency.task.process_handle import ProcessHandler
from latency.parse import (
    SdkAccessLogParser,
    WorkerAccessLogParser,
    UrmaLogParser,
    RemotePullLogParser,
    LinkLogParser,
    QueryMetaLogParser,
    LogCorrelator,
    ParseResultBuilder,
)
from latency.common.ds_log_io import glob_paths, open_log
from latency.database.engine import AsyncSQLiteSingleton
from latency.database.managers.log_parse_result import LogParseResultManager
from latency.database.managers.task import TaskManager
from latency.database.managers.task_report import TaskReportManager
from latency.schemas.log import (
    LogFileModel,
    SrcDstAggregatedEventModel,
    AnomalousEventModel,
    AnomalousEventChainModel,
    LogParseResultModel,
)

logger = logging.getLogger(__name__)

_PROGRESS_UPDATE_LINES = 100_000


def _scan_file(parser, path: str) -> tuple[str, list]:
    pod_ip = parser.extract_pod_ip(path)
    log_file = LogFileModel(file_path=path, file_size=os.path.getsize(path))
    file_name = os.path.basename(path)
    entries = []
    try:
        with open_log(path) as f:
            for line_no, line in enumerate(f, 1):
                if line_no % _PROGRESS_UPDATE_LINES == 0:
                    logger.info(
                        f"[{parser.label}] scanning {file_name} | "
                        f"line {line_no:,} | match {len(entries):,}"
                    )
                entry = parser.match_line(line, pod_ip)
                if entry:
                    entry.log_id = log_file.id
                    entries.append(entry)
    except EOFError:
        logger.warning(f"Skipping corrupted file {path}")
    except Exception as e:
        logger.warning(f"Error reading {path}: {e}")
    logger.info(
        f"[{parser.label}] done {file_name} | "
        f"lines scanned | match {len(entries):,}"
    )
    return parser.label, entries


class KVCacheLogParseWorker:
    """
    KVCacheLogParseWorker
    """

    name = TaskTypeEnum.KV_CACHE_LOG_PARSE_WORKER

    @staticmethod
    async def init(op_id: str) -> str:
        """初始化任务"""
        pass

    @staticmethod
    async def reinit(task_id: str) -> bool:
        """重新初始化任务"""
        pass

    @staticmethod
    async def deinit(task_id: str) -> str:
        """析构任务"""
        pass

    # 解析日志
    @staticmethod
    async def parse_log(
        log_dir: str,
    ) -> list[LogParseResultModel]:
        parsers = [
            SdkAccessLogParser(),
            WorkerAccessLogParser(),
            UrmaLogParser(),
            RemotePullLogParser(),
            LinkLogParser(),
            QueryMetaLogParser(),
        ]

        scan_tasks = []
        for parser in parsers:
            paths = glob_paths(
                [os.path.join(log_dir, p) for p in parser.patterns]
            )
            logger.info(f"[{parser.label}] found {len(paths)} file(s)")
            for path in paths:
                scan_tasks.append(asyncio.to_thread(_scan_file, parser, path))

        total_tasks = len(scan_tasks)
        logger.info(f"=== Stage 1/3: Scanning {total_tasks} file(s) ===")

        scan_results = await asyncio.gather(*scan_tasks)

        parsed: dict[str, list] = {}
        for label, entries in scan_results:
            parsed.setdefault(label, []).extend(entries)
        del scan_results

        for label in parsed:
            parsed[label].sort(key=lambda x: x.timestamp)
            logger.info(f"  {label}: {len(parsed[label]):,} entries")

        logger.info("=== Stage 2/3: Correlating entries ===")
        correlator = LogCorrelator(parsed)
        correlated = correlator.correlate()
        logger.info(f"  SDK→Worker: {len(correlated.sdk_worker_map):,}, "
                     f"Worker→URMA: {len(correlated.worker_urma_map):,}")

        sdk_entries = parsed.get("SDK access parse", [])
        worker_entries = parsed.get("Worker access parse", [])

        logger.info("=== Stage 3/3: Building parse results ===")
        builder = ParseResultBuilder(sdk_entries, worker_entries, correlated, log_dir=log_dir)
        results = builder.build()

        del parsed, correlated, builder
        logger.info("Released parsed & correlated intermediate data")

        total = len(results)
        anomalous_count = sum(1 for r in results if r.is_anomalous)
        logger.info(f"Parse complete: {total:,} results, {anomalous_count:,} anomalous")

        return results

    # 异常事件检测
    @staticmethod
    async def detect_exception(
        list_log_parse_results: list[LogParseResultModel],
    ) -> list[AnomalousEventModel]:
        """异常检测"""
        pass

    # 异常事件匹配故障
    @staticmethod
    async def match_fault(
        anomalous_events: list[AnomalousEventModel],
    ) -> list[AnomalousEventChainModel]:
        """异常事件匹配故障"""
        pass

    # 异常事件成因分析
    @staticmethod
    async def root_cause_analysis(
        anomalous_event_chains: list[AnomalousEventChainModel],
    ) -> list[AnomalousEventChainModel]:
        """异常事件成因分析"""
        pass

    # 基于src ip和dst ip的生成聚合结果
    @staticmethod
    async def generate_aggregate_result(
        list_log_parse_results: list[LogParseResultModel],
    ) -> list[SrcDstAggregatedEventModel]:
        """生成聚合结果"""
        pass

    # 存库
    @staticmethod
    async def store_result(
        list_log_parse_results: list[LogParseResultModel],
        anomalous_events: list[AnomalousEventModel],
        anomalous_event_chains: list[AnomalousEventChainModel],
        src_dst_aggregated_events: list[SrcDstAggregatedEventModel],
    ) -> bool:
        """存库"""
        pass

    @staticmethod
    async def run(task_id: str) -> bool:
        """运行任务"""
        pass

    @staticmethod
    async def stop(task_id: str) -> bool:
        """停止任务"""
        pass

    @staticmethod
    async def delete(task_id: str) -> bool:
        """删除任务"""
        pass
