import asyncio
import logging
import os
from collections import defaultdict
from latency.ENUM.task import TaskTypeEnum
from latency.config.config import Config
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
from latency.common.stats import stats

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
        """逐条检测异常事件"""
        cfg = Config().get_config().ds_log_analyzer

        thresholds = [
            ("total_latency", cfg.total_p99_threshold_ms),
            ("c2w_latency", cfg.c2w_p99_threshold_ms),
            ("w2w_urma_latency", cfg.w2w_p99_threshold_ms),
            ("urma_link_latency", cfg.urma_link_p99_threshold_ms),
            ("worker_query_meta_latency", cfg.query_meta_p99_threshold_ms),
        ]

        events: list[AnomalousEventModel] = []
        anomalous_count = 0

        for idx, r in enumerate(list_log_parse_results):
            reasons: list[str] = []

            if r.is_anomalous and r.anomaly_reason:
                reasons.append(r.anomaly_reason)

            if r.c2w_latency is not None and r.c2w_latency < 0:
                reasons.append("Client2WorkerTime(us) < 0")

            if r.c2w_urma_latency is not None:
                reasons.append(f"c2w_urma_latency={r.c2w_urma_latency:.3f}ms (remote URMA path)")

            for field_name, threshold_ms in thresholds:
                value = getattr(r, field_name, None)
                if value is not None and value > threshold_ms:
                    reasons.append(f"{field_name}={value:.3f}ms > threshold {threshold_ms}ms")

            if not reasons:
                continue

            anomalous_count += 1
            log_id = r.log_id or ""

            events.append(AnomalousEventModel(
                log_id=log_id,
                aggregated_event_id="",
                start_log_parse_offset=idx,
                end_log_parse_offset=idx,
                anomaly_reason="; ".join(reasons),
            ))

        logger.info(f"Detect exception: {anomalous_count:,} anomalous out of "
                     f"{len(list_log_parse_results):,} results")

        return events

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
        """按 src_ip/dst_ip 聚合统计"""
        latency_fields = [
            ("total_latency", "total_latency"),
            ("query_meta_latency", "worker_query_meta_latency"),
            ("urma_total_latency", "urma_total_latency"),
            ("urma_link_latency", "urma_link_latency"),
            ("c2w_urma_latency", "c2w_urma_latency"),
            ("w2w_urma_latency", "w2w_urma_latency"),
        ]

        groups: dict[tuple[str, str], list[LogParseResultModel]] = defaultdict(list)
        for r in list_log_parse_results:
            src = r.src_ip or ""
            dst = r.dst_ip or ""
            if not src and not dst:
                continue
            groups[(src, dst)].append(r)

        results: list[SrcDstAggregatedEventModel] = []
        for (src, dst), items in groups.items():
            log_id = items[0].log_id or ""
            total_cnt = len(items)
            anomaly_cnt = sum(1 for r in items if r.is_anomalous)
            anomaly_log_cnt = sum(1 for r in items if r.anomalous_event_id)

            agg: dict[str, float | None] = {}
            for prefix, field_name in latency_fields:
                values = [getattr(r, field_name) for r in items]
                values = [v for v in values if v is not None]
                st = stats(values)
                agg[f"ave_{prefix}"] = st["ave"]
                agg[f"min_{prefix}"] = st["min"]
                agg[f"max_{prefix}"] = st["max"]
                agg[f"p95_{prefix}"] = st["p95"]
                agg[f"p99_{prefix}"] = st["p99"]

            results.append(SrcDstAggregatedEventModel(
                src_ip=src,
                dst_ip=dst,
                log_id=log_id,
                log_parse_result_cnt=total_cnt,
                anomaly_log_parse_result_cnt=anomaly_log_cnt,
                anomaly_cnt=anomaly_cnt,
                **agg,
            ))

        logger.info(f"Aggregate result: {len(results):,} endpoints from "
                     f"{len(list_log_parse_results):,} results")

        return results

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
