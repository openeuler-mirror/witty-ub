import asyncio
import logging
import os
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
    UrmaLogParser,
    RemotePullLogParser,
    LinkLogParser,
    QueryMetaLogParser,
    WorkerMetricsLogParser,  # 新增指标解析器
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
            task_name=f"解析日志文件 {log_file_model.name}",
            task_type=TaskTypeEnum.KV_CACHE_LOG_PARSE_WORKER,
            status=TaskStatusEnum.PENDING,
        )
        await TaskManager.add_task(task)
        await LogFileManager.update_log_file(
            log_file_model.id, {"parse_status": TaskStatusEnum.PENDING.value}
        )
        await BaseWorker.report(task.id, "初始化任务", 0.0)
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
                f"任务 {task_id} 重试次数 {task.retry_times} 已超过最大重试次数 {Config().get_config().task.task_retry_times}"
            )
            return False
        await LogFileManager.update_log_file(
            task.op_id, {"parse_status": TaskStatusEnum.PENDING.value}
        )
        await BaseWorker.report(task.id, "重新初始化任务", 0.0)
        return True

    @staticmethod
    async def deinit(task_id: str) -> str:
        """析构任务"""
        return task_id

    # 解析日志
    @staticmethod
    async def parse_log(
        log_dir: str,
        parse_config: Optional[ParseConfig] = None,
    ) -> list[LogParseResultModel]:
        parsers = [
            SdkAccessLogParser(parse_config),
            WorkerAccessLogParser(parse_config),
            UrmaLogParser(parse_config),
            RemotePullLogParser(parse_config),
            LinkLogParser(parse_config),
            QueryMetaLogParser(parse_config),
            WorkerMetricsLogParser(parse_config),  # 新增指标解析器
        ]

        # 使用并行扫描器（文件去重 + 多进程并行）
        scanner = ParallelFileScanner(
            max_processes=min(os.cpu_count() or 4, 8),  # 最多 8 进程
            split_strategy=TaskSplitStrategy.BY_FILE_SIZE,
            use_multiprocessing=True,
        )

        logger.info("=== Stage 1/3: Scanning files with parallel scanner ===")
        parsed = await scanner.scan_all(log_dir, parsers, parse_config)

        # 排序解析结果
        for label in parsed:
            parsed[label].sort(key=lambda x: x.timestamp)
            logger.info(f"  {label}: {len(parsed[label]):,} entries")

        logger.info("=== Stage 2/3: Correlating entries ===")
        correlator = LogCorrelator(parsed)
        correlated = correlator.correlate()
        logger.info(f"  SDK→Worker: {len(correlated.sdk_worker_map):,}, "
                     f"Worker→URMA: {len(correlated.worker_urma_map):,}")

        # 及时释放 parsed 中间结构
        sdk_entries = parsed.pop("SDK access parse", [])
        worker_entries = parsed.pop("Worker access parse", [])
        del parsed
        import gc
        gc.collect()
        logger.info("Released parsed entries")

        logger.info("=== Stage 3/3: Building parse results ===")
        builder = ParseResultBuilder(sdk_entries, worker_entries, correlated, log_dir=log_dir)
        results = builder.build()

        # 及时释放所有中间结构（降低内存峰值）
        del sdk_entries, worker_entries, correlated, builder
        gc.collect()
        logger.info("Released sdk_entries, worker_entries, correlated & builder")

        total = len(results)
        anomalous_count = sum(1 for r in results if r.is_anomalous)
        logger.info(f"Parse complete: {total:,} results, {anomalous_count:,} anomalous")

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
                logger.error(f"任务 {task_id} 不存在")
                return False
            
            await TaskManager.update_task(
                task_id, {"status": TaskStatusEnum.RUNNING.value}
            )
            await BaseWorker.report(task.id, "运行任务", 5.0)
            
            log_file = await LogFileManager.get_log_file_by_log_file_id(task.op_id)
            if not log_file:
                logger.error(f"LogFile {task.op_id} 不存在")
                await TaskManager.update_task(
                    task_id, {"status": TaskStatusEnum.FAILED_PENDING_REMOVE.value}
                )
                return False
            log_dir = log_file.file_path
            kb_id = log_file.kb_id

            await BaseWorker.report(task.id, "开始解析日志 请耐心等待", 10.0)
            
            # 从 TaskHandler 获取解析配置
            from latency.task.task_handler import TaskHandler
            parse_config = TaskHandler.get_task_config(task_id)
            if parse_config:
                logger.info(f"[任务 {task_id}] 使用解析配置: {parse_config}")
            
            list_log_parse_results = await KVCacheLogParseWorker.parse_log(log_dir, parse_config)
            await BaseWorker.report(task.id, "完成解析日志", 70.0)
            
            # 先检测异常（填充 anomalous_event_id）
            anomalous_events = await KVCacheLogParseWorker.detect_exception(list_log_parse_results)
            await BaseWorker.report(task.id, "检测异常事件", 80.0)
            
            # 再生成聚合事件（此时 anomalous_event_id 已填充）
            src_dst_aggregated_events, src_dst_to_agg_id_map = await KVCacheLogParseWorker.generate_aggregate_result(list_log_parse_results)
            await BaseWorker.report(task.id, "生成聚合事件", 85.0)
            
            # 更新异常事件的 aggregated_event_id
            for event in anomalous_events:
                start_idx = event.start_log_parse_offset
                if 0 <= start_idx < len(list_log_parse_results):
                    r = list_log_parse_results[start_idx]
                    src = r.src_ip or ""
                    dst = r.dst_ip or ""
                    event.aggregated_event_id = src_dst_to_agg_id_map.get((src, dst), "")
            
            anomalous_event_chains = await KVCacheLogParseWorker.match_fault(anomalous_events)
            await BaseWorker.report(task.id, "匹配故障事件", 90.0)

            stored = await KVCacheLogParseWorker.store_result(
                list_log_parse_results=list_log_parse_results,
                anomalous_events=anomalous_events,
                anomalous_event_chains=anomalous_event_chains or [],
                src_dst_aggregated_events=src_dst_aggregated_events,
            )
            await BaseWorker.report(task.id, "存库", 95.0)
            
            if not stored:
                logger.warning(f"任务 {task_id} 存库部分失败，但仍标记为成功")

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
            await BaseWorker.report(task.id, "任务成功", 100.0)
            return True
        except Exception as e:
            logger.exception(f"任务 {task_id} 执行失败: {e}")
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
