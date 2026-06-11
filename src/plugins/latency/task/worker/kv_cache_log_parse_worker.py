import asyncio
import logging
import os
import time
import uuid
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Optional
from latency.schemas.log import LogParseResultModel
from latency.schemas.request import ParseConfig
from latency.ENUM.task import TaskStatusEnum, TaskTypeEnum
from latency.config.config import Config
from latency.task.process_handle import ProcessHandler
from latency.parse import (
    SdkAccessLogParser,
    WorkerAccessLogParser,
    WorkerInfoParser,
    LogCorrelator,
    ParseResultBuilder,
)
from latency.parse.parallel_scanner import ParallelFileScanner
from latency.ENUM.task import TaskSplitStrategy
from latency.common.stats import stats
from latency.detect import AnomalyDetector
from latency.database.engine import AsyncSQLiteSingleton
from latency.database.managers.log_parse_result import LogParseResultManager
from latency.database.managers.task import TaskManager
from latency.database.managers.task_report import TaskReportManager
from latency.database.managers.log_knowledge import LogKnowledgeManager
from latency.database.managers.log_file import LogFileManager
from latency.database.managers.log_parse_result import LogParseResultManager
from latency.database.managers.src_dst_aggregated_event import (
    SrcDstAggregatedEventManager,
)
from latency.database.managers.anomalous_event import AnomalousEventManager
from latency.database.managers.anomalous_event_chain import AnomalousEventChainManager
from latency.config.config import Config
from latency.schemas.task import TaskModel
from latency.schemas.log import (
    LogFileModel,
    SrcDstAggregatedEventModel,
    AnomalousEventModel,
    AnomalousEventChainModel,
    LogParseResultModel,
)
from latency.task.worker.base import BaseWorker



logger = logging.getLogger(__name__)


@dataclass
class GroupStats:
    """增量统计分组（不维护完整对象引用，降低内存峰值）"""
    count: int = 0
    anomaly_count: int = 0
    anomaly_log_count: int = 0
    first_log_id: str = ""
    latency_values: dict[str, list[float]] = field(default_factory=dict)


class KVCacheLogParseWorker(BaseWorker):
    """
    KVCacheLogParseWorker
    """

    name = TaskTypeEnum.KV_CACHE_LOG_PARSE_WORKER

    @staticmethod
    async def init(op_id: str) -> str | None:
        """初始化任务"""
        log_file_model = await LogFileManager.get_log_file_by_log_file_id(op_id)
        if not log_file_model:
            return None
        kb_id = log_file_model.kb_id
        log_kb_model = await LogKnowledgeManager.get_log_kb_by_kb_id(kb_id)
        if not log_kb_model:
            return None

        task = TaskModel(
            kb_id=log_kb_model.id,
            op_id=op_id,
            task_name=f"Parse log file: {log_file_model.name}",
            task_type=TaskTypeEnum.KV_CACHE_LOG_PARSE_WORKER,
            status=TaskStatusEnum.PENDING,
        )
        await TaskManager.add_task(task)
        await LogFileManager.update_log_file(
            log_file_model.id, {"parse_status": TaskStatusEnum.PENDING.value}
        )
        await BaseWorker.report(task.id, "Task initialized", 0.0)
        return task.id

    @staticmethod
    async def reinit(task_id: str) -> bool:
        """重新初始化任务"""
        task = await TaskManager.get_task_by_task_id(task_id)
        if not task:
            return False
        await LogParseResultManager.update_log_parse_results_existed_status_by_log_id(
            task.op_id, existed_status=0
        )
        await AnomalousEventManager.update_anomalous_events_existed_status_by_log_id(
            task.op_id, existed_status=0
        )
        await AnomalousEventChainManager.update_event_chains_existed_status_by_log_id(
            task.op_id, existed_status=0
        )
        await SrcDstAggregatedEventManager.update_aggregated_events_existed_status_by_log_id(
            task.op_id, existed_status=0
        )
        await TaskReportManager.update_task_reports_existed_status_by_task_id(
            task_id, existed_status=TaskStatusEnum.PENDING
        )
        if task.retry_times > Config().get_config().task.task_retry_times:
            await LogFileManager.update_log_file(
                task.op_id, {"parse_status": TaskStatusEnum.FAILED.value}
            )
            logger.warning(
                f"Task {task_id} retry count {task.retry_times} exceeded max retries {Config().get_config().task.task_retry_times}"
            )
            return False
        await LogFileManager.update_log_file(
            task.op_id, {"parse_status": TaskStatusEnum.PENDING.value}
        )
        await BaseWorker.report(task.id, "Task reinitialized", 0.0)
        return True

    @staticmethod
    async def deinit(task_id: str) -> str:
        """析构任务"""
        return task_id

    # 解析日志
    @staticmethod
    async def parse_log(
        log_id: str = "",
        parse_config: Optional[ParseConfig] = None,
        log_dir: str = "",  # 向后兼容参数
        task_id: str = "",  # 用于上报分阶段耗时到 TaskReport
    ) -> list[LogParseResultModel]:
        """解析日志文件

        Args:
            log_id: 日志文件ID（数据库中的主键）
            parse_config: 解析配置
            log_dir: 日志目录路径（向后兼容，优先使用 log_id）
            task_id: 任务ID（用于上报分阶段耗时）

        Returns:
            解析结果列表
        """
        # 优先使用 log_id，如果没有则使用 log_dir（向后兼容）
        if log_id:
            # 从数据库获取日志文件信息
            from latency.database.managers.log_file import LogFileManager
            log_file = await LogFileManager.get_log_file_by_log_file_id(log_id)
            if not log_file:
                raise ValueError(f"Log file with id {log_id} not found")
            log_dir = log_file.file_path
        elif not log_dir:
            raise ValueError("Either log_id or log_dir must be provided")

        parsers = [
            SdkAccessLogParser(parse_config),
            WorkerAccessLogParser(parse_config),
            WorkerInfoParser(parse_config),
        ]

        # 使用并行扫描器（文件去重 + 多进程并行）
        scanner = ParallelFileScanner(
            max_processes=os.cpu_count(),
            split_strategy=TaskSplitStrategy.BY_FILE_SIZE,
            use_multiprocessing=True,
            decompress=False,
        )

        logger.info("=== Stage 1/3: Scanning files with parallel scanner ===")
        t0 = time.perf_counter()
        parsed = await scanner.scan_all(log_dir, parsers, parse_config)
        t_scan = time.perf_counter() - t0

        # 排序解析结果
        t_sort_start = time.perf_counter()
        for label in parsed:
            parsed[label].sort(key=lambda x: x.timestamp)
            logger.info(f"  {label}: {len(parsed[label]):,} entries")
        entry_counts = {label: len(entries) for label, entries in parsed.items()}
        t_sort = time.perf_counter() - t_sort_start

        logger.info("=== Stage 2/3: Correlating entries ===")
        t_corr_start = time.perf_counter()
        correlator = LogCorrelator(parsed)
        correlated = correlator.correlate()
        t_corr = time.perf_counter() - t_corr_start
        logger.info(f"  SDK→Worker: {len(correlated.sdk_worker_map):,}, "
                     f"Worker→URMA: {len(correlated.worker_urma_map):,}")
        correlate_index_seconds = correlator.index_build_seconds
        correlate_stage_timings = list(correlator.stage_timings)
        metric_worker_indices = set()
        for metric_map in (
            correlated.worker_sdk_process_map,
            correlated.worker_sdk_rpc_map,
            correlated.worker_local_worker_cost_map,
            correlated.worker_local_worker_lock_map,
            correlated.worker_remote_worker_cost_map,
            correlated.worker_remote_worker_rpc_map,
            correlated.worker_master_process_map,
            correlated.worker_master_rpc_map,
        ):
            metric_worker_indices.update(metric_map.keys())
        correlate_match_counts = {
            "sdk_worker": len(correlated.sdk_worker_map),
            "sdk_urma": len(correlated.sdk_urma_map),
            "worker_urma": len(correlated.worker_urma_map),
            "worker_link": len(correlated.worker_link_map),
            "worker_meta": len(correlated.worker_query_meta_map),
            "worker_metrics": len(metric_worker_indices),
        }

        # 及时释放 parsed 中间结构
        sdk_entries = parsed.pop("SDK access parse", [])
        worker_entries = parsed.pop("Worker access parse", [])
        del parsed
        import gc
        gc.collect()
        logger.info("Released parsed entries")

        logger.info("=== Stage 3/3: Building parse results ===")
        t_build_start = time.perf_counter()
        builder = ParseResultBuilder(sdk_entries, worker_entries, correlated, log_dir=log_dir, log_file_id=log_id)
        results = builder.build()
        t_build = time.perf_counter() - t_build_start

        # 及时释放所有中间结构（降低内存峰值）
        del sdk_entries, worker_entries, correlated, builder
        gc.collect()
        logger.info("Released sdk_entries, worker_entries, correlated & builder")

        total = len(results)
        anomalous_count = sum(1 for r in results if r.is_anomalous)
        logger.info(f"Parse complete: {total:,} results, {anomalous_count:,} anomalous")

        # 分阶段耗时报告
        t_total = t_scan + t_sort + t_corr + t_build
        logger.info(
            f"=== [parse_log] Timing Breakdown (total={t_total:.1f}s) ===\n"
            f"  Scan + deserialize: {t_scan:7.1f}s ({t_scan/t_total*100:5.1f}%)\n"
            f"  Sort entries:       {t_sort:7.1f}s ({t_sort/t_total*100:5.1f}%)\n"
            f"  Correlate:          {t_corr:7.1f}s ({t_corr/t_total*100:5.1f}%)\n"
            f"  Build results:      {t_build:7.1f}s ({t_build/t_total*100:5.1f}%)"
        )

        if task_id:
            pct_scan = t_scan / t_total * 100
            pct_sort = t_sort / t_total * 100
            pct_corr = t_corr / t_total * 100
            pct_build = t_build / t_total * 100
            await BaseWorker.report(task_id, f"[parse_log] Scan+deserialize: {t_scan:.1f}s ({pct_scan:.1f}%)", t_scan)
            metrics = scanner.metrics
            scan_overhead_s = max(
                0.0,
                metrics.total_time_ms
                - metrics.build_map_time_ms
                - metrics.split_time_ms
                - metrics.scan_time_ms,
            ) / 1000
            await BaseWorker.report(
                task_id,
                (
                    "[perf][scan.summary] "
                    f"files={metrics.total_files}, processes={metrics.total_processes}, "
                    f"entries={metrics.total_entries}, total={metrics.total_time_ms/1000:.1f}s"
                ),
                metrics.total_time_ms / 1000,
            )
            await BaseWorker.report(
                task_id,
                f"[perf][scan.build_map] {metrics.build_map_time_ms/1000:.3f}s",
                metrics.build_map_time_ms / 1000,
            )
            await BaseWorker.report(
                task_id,
                f"[perf][scan.split] {metrics.split_time_ms/1000:.3f}s",
                metrics.split_time_ms / 1000,
            )
            await BaseWorker.report(
                task_id,
                f"[perf][scan.worker_exec] {metrics.scan_time_ms/1000:.1f}s",
                metrics.scan_time_ms / 1000,
            )
            await BaseWorker.report(
                task_id,
                f"[perf][scan.merge_overhead] {scan_overhead_s:.1f}s",
                scan_overhead_s,
            )
            await BaseWorker.report(
                task_id,
                (
                    "[perf][scan.entries] "
                    f"sdk={entry_counts.get('SDK access parse', 0)}, "
                    f"worker={entry_counts.get('Worker access parse', 0)}, "
                    f"urma={entry_counts.get('Worker urma parse', 0)}, "
                    f"pull={entry_counts.get('Worker remote pull parse', 0)}, "
                    f"link={entry_counts.get('Worker link parse', 0)}, "
                    f"meta={entry_counts.get('Worker query meta parse', 0)}, "
                    f"metrics={entry_counts.get('Worker metrics parse', 0)}"
                ),
                0.0,
            )
            await BaseWorker.report(task_id, f"[parse_log] Sort entries: {t_sort:.1f}s ({pct_sort:.1f}%)", t_sort)
            await BaseWorker.report(task_id, f"[parse_log] Correlate: {t_corr:.1f}s ({pct_corr:.1f}%)", t_corr)
            await BaseWorker.report(
                task_id,
                (
                    "[perf][correlate.index] "
                    f"{correlate_index_seconds:.3f}s "
                    f"sdk={entry_counts.get('SDK access parse', 0)}, "
                    f"worker={entry_counts.get('Worker access parse', 0)}, "
                    f"urma={entry_counts.get('Worker urma parse', 0)}, "
                    f"pull={entry_counts.get('Worker remote pull parse', 0)}, "
                    f"link={entry_counts.get('Worker link parse', 0)}, "
                    f"meta={entry_counts.get('Worker query meta parse', 0)}, "
                    f"metrics={entry_counts.get('Worker metrics parse', 0)}"
                ),
                correlate_index_seconds,
            )
            for stage_name, elapsed in correlate_stage_timings:
                await BaseWorker.report(
                    task_id,
                    f"[perf][correlate.{stage_name}] {elapsed:.3f}s",
                    elapsed,
                )
            await BaseWorker.report(
                task_id,
                (
                    "[perf][correlate.matches] "
                    f"sdk_worker={correlate_match_counts['sdk_worker']}/{entry_counts.get('SDK access parse', 0)}, "
                    f"sdk_urma={correlate_match_counts['sdk_urma']}/{entry_counts.get('SDK access parse', 0)}, "
                    f"worker_urma={correlate_match_counts['worker_urma']}/{entry_counts.get('Worker access parse', 0)}, "
                    f"worker_link={correlate_match_counts['worker_link']}/{entry_counts.get('Worker access parse', 0)}, "
                    f"worker_meta={correlate_match_counts['worker_meta']}/{entry_counts.get('Worker access parse', 0)}, "
                    f"worker_metrics={correlate_match_counts['worker_metrics']}/{entry_counts.get('Worker access parse', 0)}"
                ),
                0.0,
            )
            await BaseWorker.report(task_id, f"[parse_log] Build results: {t_build:.1f}s ({pct_build:.1f}%)", t_build)
            await BaseWorker.report(task_id, f"[parse_log] Total: {t_total:.1f}s, {total} results", 0.0)
        return results

    # 异常事件检测
    @staticmethod
    async def detect_exception(
        list_log_parse_results: list[LogParseResultModel],
    ) -> list[AnomalousEventModel]:
        """使用多窗口并行检测引擎检测异常事件"""
        n = len(list_log_parse_results)

        detector = AnomalyDetector.from_config()
        events = await detector.detect(list_log_parse_results)

        if not events:
            return events

        for event in events:
            event.id = str(uuid.uuid4())
            event.aggregated_event_id = ""
            start_idx = event.start_log_parse_offset
            end_idx = event.end_log_parse_offset
            for idx in range(start_idx, end_idx + 1):
                if 0 <= idx < len(list_log_parse_results):
                    r = list_log_parse_results[idx]
                    r.anomalous_event_id = event.id
                    r.is_anomalous = True

        logger.info(
            f"Detect exception: {len(events):,} anomalous entries out of {n:,} results"
        )
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
    ) -> tuple[list[SrcDstAggregatedEventModel], dict[tuple[str, str], str]]:
        """按 src_ip/dst_ip 增量聚合统计（优化内存：不构建完整对象引用列表）"""
        latency_fields = [
            ("total_latency", "total_latency"),
            ("query_meta_latency", "worker_query_meta_latency"),
            ("urma_total_latency", "urma_total_latency"),
            ("urma_link_latency", "urma_link_latency"),
            ("c2w_urma_latency", "c2w_urma_latency"),
            ("w2w_urma_latency", "w2w_urma_latency"),
        ]

        # 第一遍：增量收集统计值（不维护完整对象列表，降低内存峰值）
        groups: dict[tuple[str, str], GroupStats] = defaultdict(
            lambda: GroupStats(
                latency_values={prefix: [] for prefix, _ in latency_fields}
            )
        )
        
        for r in list_log_parse_results:
            src = r.src_ip or ""
            dst = r.dst_ip or ""
            if not src and not dst:
                continue
            
            key = (src, dst)
            g = groups[key]
            g.count += 1
            if r.is_anomalous:
                g.anomaly_count += 1
            if r.anomalous_event_id:
                g.anomaly_log_count += 1
            if not g.first_log_id:
                g.first_log_id = r.log_id or ""
            
            # 只收集延迟值，不保存完整对象引用
            for prefix, field_name in latency_fields:
                val = getattr(r, field_name)
                if val is not None:
                    g.latency_values[prefix].append(val)
        
        # 第二遍：构建聚合结果 + 反向写入 aggregated_event_id
        results: list[SrcDstAggregatedEventModel] = []
        src_dst_to_agg_id_map: dict[tuple[str, str], str] = {}
        
        for (src, dst), g in groups.items():
            agg_id = str(uuid.uuid4())
            src_dst_to_agg_id_map[(src, dst)] = agg_id
            
            agg: dict[str, float | None] = {}
            for prefix, _ in latency_fields:
                values = g.latency_values[prefix]
                if values:
                    st = stats(values)
                    agg[f"ave_{prefix}"] = st["ave"]
                    agg[f"min_{prefix}"] = st["min"]
                    agg[f"max_{prefix}"] = st["max"]
                    agg[f"p95_{prefix}"] = st["p95"]
                    agg[f"p99_{prefix}"] = st["p99"]
                else:
                    for f in [f"ave_{prefix}", f"min_{prefix}", f"max_{prefix}", f"p95_{prefix}", f"p99_{prefix}"]:
                        agg[f] = None
                g.latency_values[prefix] = []  # 计算完立即释放
            
            results.append(SrcDstAggregatedEventModel(
                id=agg_id,
                src_ip=src,
                dst_ip=dst,
                log_id=g.first_log_id,
                log_parse_result_cnt=g.count,
                anomaly_log_parse_result_cnt=g.anomaly_log_count,
                anomaly_cnt=g.anomaly_count,
                **agg,
            ))
        
        del groups  # 释放分组字典
        
        # 第三遍：反向写入 aggregated_event_id（保持与原逻辑一致）
        for r in list_log_parse_results:
            src = r.src_ip or ""
            dst = r.dst_ip or ""
            key = (src, dst)
            if key in src_dst_to_agg_id_map:
                r.aggregated_event_id = src_dst_to_agg_id_map[key]
        
        logger.info(f"Aggregate result: {len(results):,} endpoints from "
                     f"{len(list_log_parse_results):,} results")
        
        return results, src_dst_to_agg_id_map

    # 存库
    @staticmethod
    async def store_result(
        list_log_parse_results: list[LogParseResultModel],
        anomalous_events: list[AnomalousEventModel],
        anomalous_event_chains: list[AnomalousEventChainModel],
        src_dst_aggregated_events: list[SrcDstAggregatedEventModel],
    ) -> bool:
        """存库

        按引用顺序依次写入：log_parse_results → aggregated_events → anomalous_events → event_chains
        """
        success = True

        if list_log_parse_results:
            try:
                await LogParseResultManager.add_log_parse_results(list_log_parse_results)
                logger.info(f"Stored {len(list_log_parse_results):,} log parse results")
            except Exception as e:
                logger.error(f"Failed to store log parse results: {e}")
                success = False

        if src_dst_aggregated_events:
            try:
                await SrcDstAggregatedEventManager.add_aggregated_events(src_dst_aggregated_events)
                logger.info(f"Stored {len(src_dst_aggregated_events):,} aggregated events")
            except Exception as e:
                logger.error(f"Failed to store aggregated events: {e}")
                success = False

        if anomalous_events:
            try:
                await AnomalousEventManager.add_anomalous_events(anomalous_events)
                logger.info(f"Stored {len(anomalous_events):,} anomalous events")
            except Exception as e:
                logger.error(f"Failed to store anomalous events: {e}")
                success = False

        if anomalous_event_chains:
            try:
                await AnomalousEventChainManager.add_event_chains(anomalous_event_chains)
                logger.info(f"Stored {len(anomalous_event_chains):,} event chains")
            except Exception as e:
                logger.error(f"Failed to store event chains: {e}")
                success = False

        return success

    @staticmethod
    async def run(task_id: str) -> bool:
        """运行任务"""
        try:
            task = await TaskManager.get_task_by_task_id(task_id)
            if not task:
                logger.error(f"Task {task_id} not found")
                return False
            
            await TaskManager.update_task(
                task_id, {"status": TaskStatusEnum.RUNNING.value}
            )
            await BaseWorker.report(task.id, "Task running", 5.0)

            # 从 TaskHandler 获取解析配置
            from latency.task.task_handler import TaskHandler
            parse_config = TaskHandler.get_task_config(task_id)
            if parse_config:
                logger.info(f"[Task {task_id}] Using parse config: {parse_config}")

            # 直接使用 task.op_id 作为 log_id，parse_log 内部会获取 log_file 信息
            t_run_start = time.perf_counter()
            list_log_parse_results = await KVCacheLogParseWorker.parse_log(task.op_id, parse_config, task_id=task_id)
            t_parse = time.perf_counter() - t_run_start
            await BaseWorker.report(task.id, "Log parse completed", 70.0)
            await BaseWorker.report(
                task.id,
                f"[perf][parse.results] rows={len(list_log_parse_results)}",
                0.0,
            )

            # 获取 kb_id 用于后续更新知识库统计
            log_file = await LogFileManager.get_log_file_by_log_file_id(task.op_id)
            kb_id = log_file.kb_id if log_file else None

            # 先检测异常（填充 anomalous_event_id）
            t_detect_start = time.perf_counter()
            anomalous_events = await KVCacheLogParseWorker.detect_exception(list_log_parse_results)
            t_detect = time.perf_counter() - t_detect_start
            await BaseWorker.report(task.id, "Anomaly detection done", 80.0)
            await BaseWorker.report(
                task.id,
                f"[perf][detect.summary] results={len(list_log_parse_results)}, events={len(anomalous_events)}, time={t_detect:.3f}s",
                t_detect,
            )
            
            # 再生成聚合事件（此时 anomalous_event_id 已填充）
            t_agg_start = time.perf_counter()
            src_dst_aggregated_events, src_dst_to_agg_id_map = await KVCacheLogParseWorker.generate_aggregate_result(list_log_parse_results)
            t_agg = time.perf_counter() - t_agg_start
            await BaseWorker.report(task.id, "Aggregate events done", 85.0)
            await BaseWorker.report(
                task.id,
                (
                    "[perf][aggregate.summary] "
                    f"results={len(list_log_parse_results)}, endpoints={len(src_dst_aggregated_events)}, "
                    f"time={t_agg:.3f}s"
                ),
                t_agg,
            )
            
            # 更新异常事件的 aggregated_event_id
            for event in anomalous_events:
                start_idx = event.start_log_parse_offset
                if 0 <= start_idx < len(list_log_parse_results):
                    r = list_log_parse_results[start_idx]
                    src = r.src_ip or ""
                    dst = r.dst_ip or ""
                    event.aggregated_event_id = src_dst_to_agg_id_map.get((src, dst), "")
            
            anomalous_event_chains = await KVCacheLogParseWorker.match_fault(anomalous_events)
            await BaseWorker.report(task.id, "Fault matching done", 90.0)
            await BaseWorker.report(
                task.id,
                f"[perf][fault.summary] events={len(anomalous_events)}, chains={len(anomalous_event_chains or [])}",
                0.0,
            )

            t_store_start = time.perf_counter()
            stored = await KVCacheLogParseWorker.store_result(
                list_log_parse_results=list_log_parse_results,
                anomalous_events=anomalous_events,
                anomalous_event_chains=anomalous_event_chains or [],
                src_dst_aggregated_events=src_dst_aggregated_events,
            )
            t_store = time.perf_counter() - t_store_start
            await BaseWorker.report(task.id, "Results stored", 95.0)
            await BaseWorker.report(
                task.id,
                (
                    "[perf][store.summary] "
                    f"parse_results={len(list_log_parse_results)}, "
                    f"aggregated={len(src_dst_aggregated_events)}, "
                    f"anomalous={len(anomalous_events)}, "
                    f"chains={len(anomalous_event_chains or [])}, "
                    f"stored={stored}, time={t_store:.3f}s"
                ),
                t_store,
            )
            
            if not stored:
                logger.warning(f"Task {task_id} store partially failed, still marking as successful")

            await LogFileManager.update_log_file(
                task.op_id, {"anomaly_cnt": len(anomalous_events)}
            )
            
            # 更新关联的知识库统计
            if kb_id:
                await LogKnowledgeManager.update_log_kb(
                    kb_id, {"anomaly_cnt": len(anomalous_events)}
                )
            
            await TaskManager.update_task(
                task_id, {"status": TaskStatusEnum.SUCCESSFUL_PENDING_REMOVE.value}
            )
            await LogFileManager.update_log_file(
                task.op_id, {"parse_status": TaskStatusEnum.SUCCESSFUL.value}
            )
            await BaseWorker.report(task.id, "Task completed successfully", 100.0)

            # 全流程耗时汇总
            t_total = t_parse + t_detect + t_agg + t_store
            pct_p = t_parse / t_total * 100
            pct_d = t_detect / t_total * 100
            pct_a = t_agg / t_total * 100
            pct_s = t_store / t_total * 100
            logger.info(
                f"============================================================\n"
                f"=== [TASK TIMING] Total: {t_total:.1f}s ===\n"
                f"  [1] Parse log:       {t_parse:7.1f}s ({pct_p:5.1f}%)\n"
                f"  [2] Detect anomaly:  {t_detect:7.1f}s ({pct_d:5.1f}%)\n"
                f"  [3] Aggregate result:{t_agg:7.1f}s ({pct_a:5.1f}%)\n"
                f"  [4] Store to DB:     {t_store:7.1f}s ({pct_s:5.1f}%)\n"
                f"============================================================"
            )
            await BaseWorker.report(task.id, f"[TASK] Parse log: {t_parse:.1f}s ({pct_p:.1f}%)", t_parse)
            await BaseWorker.report(task.id, f"[TASK] Detect anomaly: {t_detect:.1f}s ({pct_d:.1f}%)", t_detect)
            await BaseWorker.report(task.id, f"[TASK] Aggregate result: {t_agg:.1f}s ({pct_a:.1f}%)", t_agg)
            await BaseWorker.report(task.id, f"[TASK] Store to DB: {t_store:.1f}s ({pct_s:.1f}%)", t_store)
            await BaseWorker.report(task.id, f"[TASK] Total: {t_total:.1f}s", 0.0)
            return True
        except Exception as e:
            logger.exception(f"Task {task_id} failed: {e}")
            await TaskManager.update_task(
                task_id, {"status": TaskStatusEnum.FAILED_PENDING_REMOVE.value}
            )
            return False

    @staticmethod
    async def stop(task_id: str) -> str | None:
        """停止任务"""
        task = await TaskManager.get_task_by_task_id(task_id)
        if task.status in [TaskStatusEnum.PENDING, TaskStatusEnum.RUNNING]:
            await LogParseResultManager.update_log_parse_results_existed_status_by_log_id(
                task.op_id, existed_status=0
            )
            await AnomalousEventManager.update_anomalous_events_existed_status_by_log_id(
                task.op_id, existed_status=0
            )
            await AnomalousEventChainManager.update_event_chains_existed_status_by_log_id(
                task.op_id, existed_status=0
            )
            await SrcDstAggregatedEventManager.update_aggregated_events_existed_status_by_log_id(
                task.op_id, existed_status=0
            )
            await TaskReportManager.update_task_reports_existed_status_by_task_id(
                task_id, existed_status=0
            )
            await TaskManager.update_task(
                task_id, {"status": TaskStatusEnum.CANCELLED.value}
            )
            return task_id
        return None

    @staticmethod
    async def delete(task_id: str) -> str:
        """删除任务"""
        return task_id
