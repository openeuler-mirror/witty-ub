import logging
import os
from datetime import datetime
from latency.ENUM.task import TaskStatusEnum, TaskTypeEnum
from latency.task.process_handle import ProcessHandler
from latency.database.managers.task import TaskPGManager
from latency.database.managers.task_report import TaskReportPGManager
from latency.schemas.task import TaskReportModel

logger = logging.getLogger(__name__)

PREPROCESS_TASK_TYPES = {
    TaskTypeEnum.KV_CACHE_LOG_PARSE_WORKER,
    TaskTypeEnum.KV_CACHE_LOG_EVENT_DIAGNOSIS_WORKER,
}


class BaseWorker:
    """
    BaseWorker
    """

    @staticmethod
    def find_worker_class(worker_name: TaskTypeEnum):
        subclasses = BaseWorker.__subclasses__()
        for subclass in subclasses:
            if subclass.name == worker_name:
                return subclass
        return None

    @staticmethod
    async def get_worker_name(task_id: str) -> TaskTypeEnum:
        """获取worker_name"""
        task = await TaskPGManager.get_task_by_task_id(task_id)
        if task is None:
            err = f"获取任务失败, 任务ID: {task_id}"
            logging.error("[BaseWorker] %s", err)
            raise ValueError(err)
        return task.task_type

    @staticmethod
    async def init(worker_name: TaskTypeEnum, op_id: str) -> str:
        """初始化任务"""
        task_id = await BaseWorker.find_worker_class(worker_name).init(op_id)
        await TaskPGManager.update_task(task_id, {"status": TaskStatusEnum.PENDING.value})
        return task_id

    @staticmethod
    async def reinit(task_id: str) -> bool:
        """重新初始化任务"""
        task = await TaskPGManager.get_task_by_task_id(task_id)
        if not task:
            logger.warning(f"[BaseWorker] reinit: 任务 {task_id} 不存在")
            return False
        
        worker_name = task.task_type
        flag = await BaseWorker.find_worker_class(worker_name).reinit(task_id)
        ProcessHandler.remove_task(task_id)
        if flag:
            await TaskPGManager.update_task(
                task_id,
                {
                    "status": TaskStatusEnum.PENDING.value,
                    "retry_times": task.retry_times + 1,
                },
            )
            return True
        else:
            completed_at = datetime.now()
            duration_seconds = (completed_at - task.created_at).total_seconds()
            
            await TaskPGManager.update_task(
                task_id, 
                {
                    "status": TaskStatusEnum.FAILED.value,
                    "completed_at": completed_at,
                    "duration_seconds": duration_seconds
                }
            )
            return False

    @staticmethod
    async def deinit(task_id: str) -> str:
        """析构任务"""
        task = await TaskPGManager.get_task_by_task_id(task_id)
        if not task:
            logger.warning(f"[BaseWorker] deinit: 任务 {task_id} 不存在")
            return ""
        
        worker_name = task.task_type
        ProcessHandler.remove_task(task_id)
        await BaseWorker.find_worker_class(worker_name).deinit(task_id)
        completed_at = datetime.now(timezone.utc)
        duration_seconds = (completed_at - task.created_at).total_seconds()
        
        await TaskPGManager.update_task(
            task_id, 
            {
                "status": TaskStatusEnum.SUCCESSFUL.value,
                "completed_at": completed_at,
                "duration_seconds": duration_seconds
            }
        )
        if worker_name in PREPROCESS_TASK_TYPES:
            await BaseWorker._cleanup_preprocess_dir_if_all_done(task.op_id)

    @staticmethod
    async def _cleanup_preprocess_dir_if_all_done(op_id: str) -> None:
        """两个日志 worker 都成功完成后清理共享预处理目录。"""
        tasks = [
            await TaskPGManager.get_current_task_by_op_id(op_id, task_type)
            for task_type in PREPROCESS_TASK_TYPES
        ]
        if not all(tasks):
            return
        if not all(task.status == TaskStatusEnum.SUCCESSFUL for task in tasks):
            return

        from latency.task.log_preprocessor import cleanup_preprocess_dir

        cleanup_preprocess_dir(op_id)

    @staticmethod
    async def run(task_id: str, log_dir: str | None = None) -> bool:
        """运行任务"""
        task = await TaskPGManager.get_task_by_task_id(task_id)
        if not task:
            logger.warning(f"[BaseWorker] run: 任务 {task_id} 不存在")
            return False
        
        worker_name = task.task_type
        args = (task_id, log_dir) if log_dir else (task_id,)
        flag = ProcessHandler.add_task(
            task_id, BaseWorker.find_worker_class(worker_name).run, *args
        )
        await TaskPGManager.update_task(task_id, {"status": TaskStatusEnum.RUNNING.value})
        return flag

    @staticmethod
    async def stop(task_id: str) -> bool:
        """停止任务"""
        task = await TaskPGManager.get_task_by_task_id(task_id)
        if not task:
            logger.warning(f"[BaseWorker] 任务 {task_id} 不存在")
            return True
        
        worker_name = task.task_type
        logger.warning(f"[BaseWorker] 停止任务 {task_id}, 当前状态: {task.status}, worker: {worker_name}")
        
        should_update_status = False
        if task.status == TaskStatusEnum.RUNNING:
            ProcessHandler.remove_task(task_id)
            logger.warning(f"[BaseWorker] 已调用 ProcessHandler.remove_task({task_id})")
            should_update_status = True
        elif task.status == TaskStatusEnum.PENDING:
            logger.warning(f"[BaseWorker] 任务 {task_id} 状态为 PENDING")
            should_update_status = True
        elif task.status == TaskStatusEnum.CANCELLED:
            logger.warning(f"[BaseWorker] 任务 {task_id} 已经是 CANCELLED 状态")
            return True
        else:
            logger.warning(f"[BaseWorker] 任务 {task_id} 状态为 {task.status}")
        
        logger.warning(f"[BaseWorker] 调用 {worker_name}.stop({task_id})")
        try:
            task_id_from_stop = await BaseWorker.find_worker_class(worker_name).stop(task_id)
            if task_id_from_stop:
                logger.warning(f"[BaseWorker] worker.stop 返回: {task_id_from_stop}")
        except Exception as e:
            logger.error(f"[BaseWorker] worker.stop 异常: {e}")
        
        if should_update_status:
            completed_at = datetime.now(timezone.utc)
            duration_seconds = (completed_at - task.created_at).total_seconds()
            
            await TaskPGManager.update_task(
                task_id, 
                {
                    "status": TaskStatusEnum.CANCELLED.value,
                    "completed_at": completed_at,
                    "duration_seconds": duration_seconds
                }
            )
            logger.warning(f"[BaseWorker] 任务 {task_id} 已更新为 CANCELLED 状态")
        return True

    @staticmethod
    async def delete(task_id: str) -> bool:
        """删除任务"""
        task = await TaskPGManager.get_task_by_task_id(task_id)
        if not task:
            logger.warning(f"[BaseWorker] delete: 任务 {task_id} 不存在")
            return False
        
        worker_name = task.task_type
        await BaseWorker.find_worker_class(worker_name).delete(task_id)
        await TaskPGManager.delete_task_by_task_id(task_id)
        return True

    @staticmethod
    async def report(
        task_id: str, message: str, progress: float
    ) -> bool:
        """添加任务报告"""
        task_report = TaskReportModel(
            task_id=task_id, message=message, progress=progress
        )
        flag = await TaskReportPGManager.add_task_report(task_report)
        return flag
