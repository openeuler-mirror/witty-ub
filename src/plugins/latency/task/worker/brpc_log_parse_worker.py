# Copyright (c) Huawei Technologies Co., Ltd. 2023-2025. All rights reserved.
"""BRPC 日志解析 Worker。

解析 ubsocket_profiling_xxx.txt 格式的 BRPC profiling 日志文件，
将 21 个接口函数的时序统计信息存入 PostgreSQL。
"""

from __future__ import annotations

import logging
import re
import time
from typing import Optional

from latency.ENUM.task import TaskStatusEnum, TaskTypeEnum
from latency.config.config import Config
from latency.parse.brpc_profiling_parser import BrpcProfilingParser
from latency.database.managers.log_file import LogFilePGManager
from latency.database.managers.log_knowledge import LogKnowledgePGManager
from latency.database.managers.task import TaskPGManager
from latency.database.managers.task_report import TaskReportPGManager
from latency.database.managers.brpc_profiling_result import BrpcProfilingResultPGManager
from latency.schemas.task import TaskModel
from latency.task.worker.base import BaseWorker

logger = logging.getLogger(__name__)

_PROFILING_TIMESTAMP_RE = re.compile(r"^timeStamp:\s*\S")


def _is_profiling_log(file_path: str) -> bool:
    """Read the first line and check if it matches the profiling timestamp format."""
    try:
        with open(file_path, "r", encoding="utf-8-sig", errors="ignore") as f:
            first_line = f.readline().strip()
    except (IOError, OSError):
        return False
    return bool(_PROFILING_TIMESTAMP_RE.match(first_line))


class BrpcLogParseWorker(BaseWorker):
    """BRPC profiling 日志解析 Worker"""

    name = TaskTypeEnum.BRPC_LOG_PARSE_WORKER

    @staticmethod
    async def init(op_id: str) -> str | None:
        """初始化任务"""
        log_file_model = await LogFilePGManager.get_log_file_by_log_file_id(op_id)
        if not log_file_model:
            return None
        kb_id = log_file_model.kb_id
        log_kb_model = await LogKnowledgePGManager.get_log_kb_by_kb_id(kb_id)
        if not log_kb_model:
            return None

        task = TaskModel(
            kb_id=log_kb_model.id,
            op_id=op_id,
            task_name=f"Parse BRPC log file: {log_file_model.name}",
            task_type=TaskTypeEnum.BRPC_LOG_PARSE_WORKER,
            status=TaskStatusEnum.PENDING,
        )
        await TaskPGManager.add_task(task)
        await BaseWorker.report(task.id, "BRPC task initialized", 0.0)
        return task.id

    @staticmethod
    async def reinit(task_id: str) -> bool:
        """重新初始化任务"""
        task = await TaskPGManager.get_task_by_task_id(task_id)
        if not task:
            return False
        retry_limit = Config().get_config().task.task_retry_times
        if task.retry_times >= retry_limit:
            logger.warning(
                "BRPC parse task %s reached retry limit %d",
                task_id,
                retry_limit,
            )
            return False
        await BrpcProfilingResultPGManager.delete_by_log_id(task.op_id)
        await BaseWorker.report(task.id, "BRPC task reinitialized", 0.0)
        return True

    @staticmethod
    async def deinit(task_id: str) -> str:
        """析构任务"""
        return task_id

    @staticmethod
    async def parse_log(log_id: str = "", log_dir: str = "") -> int:
        """解析 BRPC profiling 日志文件。

        Args:
            log_id: 日志文件 ID
            log_dir: 日志目录路径

        Returns:
            解析出的记录数
        """
        if log_id:
            log_file = await LogFilePGManager.get_log_file_by_log_file_id(log_id)
            if not log_file:
                raise ValueError(f"Log file with id {log_id} not found")
            if not log_dir:
                log_dir = log_file.file_path

        if not log_dir:
            raise ValueError("Either log_id or log_dir must be provided")

        import os

        profiling_files: list[str] = []
        if os.path.isfile(log_dir):
            profiling_files = [log_dir]
        elif os.path.isdir(log_dir):
            for root, _, files in os.walk(log_dir):
                for f in files:
                    fp = os.path.join(root, f)
                    if _is_profiling_log(fp):
                        profiling_files.append(fp)

        if not profiling_files:
            logger.warning(f"未找到 BRPC profiling 文件: {log_dir}")
            return 0

        logger.info(f"找到 {len(profiling_files)} 个 BRPC profiling 文件")

        parser = BrpcProfilingParser()
        all_records = []
        for file_path in profiling_files:
            logger.info(f"解析 BRPC profiling 文件: {file_path}")
            records = parser.parse_file(file_path)
            all_records.extend(records)

        if all_records and log_id:
            await BrpcProfilingResultPGManager.add_profiling_results(log_id, all_records)

        return len(all_records)

    @staticmethod
    async def run(task_id: str, log_dir: str | None = None) -> bool:
        """运行任务"""
        try:
            task = await TaskPGManager.get_task_by_task_id(task_id)
            if not task:
                logger.error(f"Task {task_id} not found")
                return False

            await TaskPGManager.update_task(
                task_id, {"status": TaskStatusEnum.RUNNING.value}
            )
            await BaseWorker.report(task.id, "BRPC task running", 5.0)

            t_run_start = time.perf_counter()
            record_count = await BrpcLogParseWorker.parse_log(
                task.op_id,
                log_dir=log_dir or "",
            )
            t_parse = time.perf_counter() - t_run_start

            if record_count == 0:
                await BaseWorker.report(task.id, "无 BRPC profiling 文件，跳过 profiling 解析", 100.0)
                await LogKnowledgePGManager.touch_log_kb(task.kb_id)
                await TaskPGManager.update_task(
                    task_id, {"status": TaskStatusEnum.SUCCESSFUL_PENDING_REMOVE.value}
                )
                return True

            await BaseWorker.report(
                task.id,
                f"BRPC parse completed: {record_count} records in {t_parse:.1f}s",
                90.0,
            )

            await BaseWorker.report(task.id, "BRPC task completed successfully", 100.0)
            await LogKnowledgePGManager.touch_log_kb(task.kb_id)
            await TaskPGManager.update_task(
                task_id, {"status": TaskStatusEnum.SUCCESSFUL_PENDING_REMOVE.value}
            )

            logger.info(
                f"BRPC task {task_id} completed: {record_count} records, "
                f"parse time: {t_parse:.1f}s"
            )
            return True
        except Exception as e:
            logger.exception(f"BRPC task {task_id} failed: {e}")
            await TaskPGManager.update_task(
                task_id, {"status": TaskStatusEnum.FAILED_PENDING_REMOVE.value}
            )
            return False

    @staticmethod
    async def stop(task_id: str) -> str | None:
        """停止任务"""
        task = await TaskPGManager.get_task_by_task_id(task_id)
        if not task:
            return None
        if task.status in [TaskStatusEnum.PENDING, TaskStatusEnum.RUNNING]:
            await BrpcProfilingResultPGManager.delete_by_log_id(task.op_id)
            await TaskPGManager.update_task(
                task_id, {"status": TaskStatusEnum.CANCELLED.value}
            )
            return task_id
        return None

    @staticmethod
    async def delete(task_id: str) -> str:
        """删除任务"""
        task = await TaskPGManager.get_task_by_task_id(task_id)
        if not task:
            return ""

        log_id = task.op_id
        await BrpcProfilingResultPGManager.delete_by_log_id(log_id)
        return task_id
