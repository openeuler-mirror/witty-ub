import logging
import os
from latency.ENUM.task import TaskStatusEnum, TaskTypeEnum
from latency.task.process_handle import ProcessHandler
from latency.database.managers.task import TaskManager
from latency.database.managers.task_report import TaskReportManager
from latency.schemas.log import (
    LogFileModel,
    src_dst_aggregated_eventModel,
    AnomalousEventModel,
    AnomalousEventChainModel,
    LogParseResultModel,
)

logger = logging.getLogger(__name__)


class KVCacheLogParseWorker:
    """
    KVCacheLogParseWorker
    """

    name = TaskTypeEnum.KV_CACHE_LOG_PARSE

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
    async def parse_log(log_file: LogFileModel) -> list[LogParseResultModel]:
        """解析日志"""
        pass

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
    ) -> list[src_dst_aggregated_eventModel]:
        """生成聚合结果"""
        pass

    # 存库
    @staticmethod
    async def store_result(
        list_log_parse_results: list[LogParseResultModel],
        anomalous_events: list[AnomalousEventModel],
        anomalous_event_chains: list[AnomalousEventChainModel],
        src_dst_aggregated_events: list[src_dst_aggregated_eventModel],
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
