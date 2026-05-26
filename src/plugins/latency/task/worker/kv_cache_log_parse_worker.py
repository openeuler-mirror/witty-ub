import logging
import os
from latency.ENUM.task import TaskStatusEnum, TaskTypeEnum
from latency.task.process_handle import ProcessHandler
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

logger = logging.getLogger(__name__)


class KVCacheLogParseWorker:
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
        await TaskReportManager.update_task_report_status_by_task_id(
            task_id, status=TaskStatusEnum.PENDING
        )
        if task.retry_times > Config().get_config().task_retry_times:
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
        return True

    @staticmethod
    async def deinit(task_id: str) -> str:
        """析构任务"""
        return task_id

    # 解析日志
    @staticmethod
    async def parse_log(log_dir: str) -> list[LogParseResultModel]:
        parsers: list[LogParser] = [
            SdkAccessLogParser(),
            WorkerAccessLogParser(),
            UrmaLogParser(),
            RemotePullLogParser(),
            LinkLogParser(),
            QueryMetaLogParser(),
        ]

        parsed: dict[str, list[BaseLogEntry]] = {}
        for parser in parsers:
            entries = parser.parse(log_dir)
            parsed[parser.label] = entries
            logger.info(f"{parser.label}: {len(entries)} entries")

        correlator = LogCorrelator(parsed)
        correlated = correlator.correlate()

        sdk_entries = parsed.get("SDK access parse", [])
        worker_entries = parsed.get("Worker access parse", [])

        builder = ParseResultBuilder(sdk_entries, worker_entries, correlated)
        results = builder.build()

        logger.info(
            f"Parse complete: {len(results)} results, "
            f"{sum(1 for r in results if r.is_anomalous)} anomalous"
        )

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
        try:
            task = await TaskManager.get_task_by_task_id(task_id)
            if not task:
                logger.error(f"任务 {task_id} 不存在")
                return False
            await TaskManager.update_task(
                task_id, {"status": TaskStatusEnum.RUNNING.value}
            )
            # TODO: 解析日志存库
            await TaskManager.update_task(
                task_id, {"status": TaskStatusEnum.SUCCESSFUL_PENDING_REMOVE.value}
            )
            await LogFileManager.update_log_file(
                task.op_id, {"parse_status": TaskStatusEnum.SUCCESSFUL.value}
            )
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
            await TaskReportManager.update_task_report_existed_status_by_task_id(
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
