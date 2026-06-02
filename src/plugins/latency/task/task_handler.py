# Copyright (c) Huawei Technologies Co., Ltd. 2023-2025. All rights reserved.
from typing import Optional
import logging
from latency.ENUM.task import TaskStatusEnum, TaskTypeEnum
from latency.task.worker.base import BaseWorker
from latency.database.managers.task import TaskManager

logger = logging.getLogger(__name__)


class TaskHandler:
    """任务队列"""
    
    _task_configs: dict[str, Optional["ParseConfig"]] = {}

    @staticmethod
    async def init_task_queue():
        """初始化任务队列"""
        await TaskManager.update_running_tasks_to_pending_tasks()

    @staticmethod
    async def init_task(task_type: TaskTypeEnum, op_id: str, parse_config: Optional["ParseConfig"] = None) -> str:
        """初始化任务"""
        try:
            task_id = await BaseWorker.init(task_type, op_id)
            if task_id:
                TaskHandler._task_configs[task_id] = parse_config
            return task_id
        except Exception as e:
            err = f"[TaskQueueService] 初始化任务失败 {e}"
            logger.exception(err)
    
    @staticmethod
    def get_task_config(task_id: str) -> Optional["ParseConfig"]:
        """获取任务的解析配置"""
        return TaskHandler._task_configs.get(task_id)
    
    @staticmethod
    def remove_task_config(task_id: str):
        """移除任务的解析配置"""
        TaskHandler._task_configs.pop(task_id, None)

    @staticmethod
    async def stop_task(task_id: str) -> Optional[str]:
        """停止任务"""
        try:
            flag = await BaseWorker.stop(task_id)
            if not flag:
                return None
            return task_id
        except Exception as e:
            err = f"[TaskQueueService] 停止任务失败 {e}"
            logger.exception(err)

    @staticmethod
    async def delete_task(task_id: str) -> Optional[str]:
        """删除任务"""
        try:
            stop_flag = await BaseWorker.stop(task_id)
            if not stop_flag:
                return None
            delete_flag = await BaseWorker.delete(task_id)
            if not delete_flag:
                return None
            return task_id
        except Exception as e:
            err = f"[TaskQueueService] 删除任务失败 {e}"
            logger.exception(err)

    @staticmethod
    async def handle_successed_tasks():
        handle_successed_task_limit = 128
        tasks = await TaskManager.get_oldest_tasks_by_status(
            TaskStatusEnum.SUCCESSFUL_PENDING_REMOVE, handle_successed_task_limit
        )
        for task in tasks:
            try:
                await BaseWorker.deinit(task.id)
            except Exception as e:
                err = f"[TaskQueueService] 处理成功任务失败 {e}"
                logger.error(err)

    @staticmethod
    async def handle_failed_tasks():
        handle_failed_task_limit = 128
        tasks = await TaskManager.get_oldest_tasks_by_status(
            TaskStatusEnum.FAILED_PENDING_REMOVE, handle_failed_task_limit
        )
        pending_task_ids = []
        fail_task_ids = []
        for task in tasks:
            try:
                flag = await BaseWorker.reinit(task.id)
            except Exception as e:
                err = f"[TaskQueueService] 处理失败任务失败 {e}"
                logger.error(err)
                fail_task_ids.append(task.id)
                continue
            if flag:
                pending_task_ids.append(task.id)
            else:
                fail_task_ids.append(task.id)

    @staticmethod
    async def handle_pending_tasks():
        handle_pending_task_limit = 128
        pending_tasks = await TaskManager.get_oldest_tasks_by_status(
            TaskStatusEnum.PENDING, handle_pending_task_limit
        )
        running_task_ids = []
        for task in pending_tasks:
            try:
                flag = await BaseWorker.run(task.id)
            except Exception as e:
                flag = False
                err = f"[TaskQueueService] 处理待处理任务失败 {e}"
                logger.error(err)
            if not flag:
                break
            running_task_ids.append(task.id)

    @staticmethod
    async def handle_tasks():
        await TaskHandler.handle_successed_tasks()
        await TaskHandler.handle_failed_tasks()
        await TaskHandler.handle_pending_tasks()
