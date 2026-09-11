# Copyright (c) Huawei Technologies Co., Ltd. 2023-2025. All rights reserved.
import asyncio
import concurrent.futures
import errno
from typing import Optional
import logging
from latency.ENUM.task import TaskStatusEnum, TaskTypeEnum
from latency.task.worker.base import BaseWorker
from latency.task.process_handle import ProcessHandler
from latency.database.managers.task import TaskPGManager
from latency.database.managers.log_file import LogFilePGManager
from latency.task.log_preprocessor import (
    default_preprocess_dir,
    needs_preprocess,
    preprocess_log_dir,
)
from latency.schemas.parse_config import ParseConfig

logger = logging.getLogger(__name__)

_executor = concurrent.futures.ThreadPoolExecutor(max_workers=1)


class TaskHandler:
    """任务队列"""
    
    _task_configs: dict[str, Optional["ParseConfig"]] = {}
    # 正在后台派发（预处理+启动）的任务 ID，防止下一轮重复派发同一任务。
    _dispatching_task_ids: set[str] = set()
    # 后台派发协程的强引用，避免被 GC；协程结束后自动移除。
    _dispatch_tasks: set["asyncio.Task"] = set()
    # 同一日志文件的多个任务共享同一次预处理，避免并发重复解压。
    _preprocess_inflight: dict[str, "asyncio.Future"] = {}

    @staticmethod
    async def init_task_queue():
        """恢复因服务异常退出而中断的任务。"""
        await TaskPGManager.mark_interrupted_running_tasks_for_retry()

    @staticmethod
    async def init_task(task_type: TaskTypeEnum, op_id: str, parse_config: Optional["ParseConfig"] = None) -> str:
        """初始化任务"""
        task_id = None
        try:
            task_id = await BaseWorker.init(task_type, op_id)
            if not task_id:
                raise RuntimeError(f"{task_type.value} 未创建任务记录")
            TaskHandler._task_configs[task_id] = parse_config
            await TaskPGManager.update_task(
                task_id,
                {
                    "task_config": (
                        parse_config.model_dump(mode="json")
                        if parse_config is not None
                        else None
                    )
                },
            )
            return task_id
        except Exception as e:
            if task_id:
                TaskHandler._task_configs.pop(task_id, None)
            err = f"[TaskQueueService] 初始化任务失败 {e}"
            logger.exception(err)
            raise

    @staticmethod
    async def _fail_preprocess_for_insufficient_space(task) -> None:
        """Remove partial files and persist a user-facing terminal failure."""
        from latency.task.log_preprocessor import cleanup_preprocess_dir

        await asyncio.to_thread(cleanup_preprocess_dir, task.op_id)
        message = "任务失败：服务器磁盘空间不足，请清理空间后重新提交"
        try:
            await TaskPGManager.mark_failed_with_report(task.id, message)
        except Exception:
            logger.exception("记录磁盘空间不足任务失败状态失败: task_id=%s", task.id)
    
    @staticmethod
    async def _fail_task_for_dispatch_error(task, error: Exception) -> None:
        """把持续失败的派发标记为失败，进入标准重试链路。

        源路径被删除/移动、输出目录不可写等错误不会自愈；不标记失败的
        话任务会每轮派发都失败，永远停留在待解析状态。标记为
        FAILED_PENDING_REMOVE 后由 handle_failed_tasks 走 reinit 重试，
        重试耗尽即终态 FAILED。
        """
        message = f"任务失败：日志预处理或启动失败，{error}"
        try:
            await TaskPGManager.mark_failed_with_report(
                task.id,
                message,
                status=TaskStatusEnum.FAILED_PENDING_REMOVE,
            )
        except Exception:
            logger.exception("记录任务派发失败状态失败: task_id=%s", task.id)

    @staticmethod
    def get_task_config(task_id: str) -> Optional["ParseConfig"]:
        """获取任务的解析配置"""
        return TaskHandler._task_configs.get(task_id)
    
    @staticmethod
    def remove_task_config(task_id: str):
        """移除任务的解析配置"""
        TaskHandler._task_configs.pop(task_id, None)

    @staticmethod
    async def _preprocess_log_source(task) -> str | None:
        log_file = await LogFilePGManager.get_log_file_by_log_file_id(task.op_id)
        if not log_file:
            return None

        # 同一日志文件的多个 worker（解析/诊断/上下文落库）共享一次预处理，
        # 避免并发重复解压，也避免读到解压到一半的目录。
        inflight = TaskHandler._preprocess_inflight.get(log_file.id)
        if inflight is not None:
            result = await inflight
        else:
            # 纯文本日志目录(无压缩包、文件全匹配 filename_patterns)无需拷贝/拆分:
            # scan_all 可直接扫源路径,省去每次上传重复拷贝 106MB 级日志的浪费。
            if not await asyncio.to_thread(needs_preprocess, log_file.file_path):
                logger.info(
                    "日志无需预处理, 直接扫描源目录: %s (log_file=%s)",
                    log_file.file_path,
                    log_file.id,
                )
                await BaseWorker.report(task.id, "日志无需预处理，直接扫描源目录", 5.0)
                return log_file.file_path

            # 解压/拷贝可能耗时数分钟：先落一条进度报告，前端不会在
            # “解析中”停留数分钟却没有任何进度反馈。
            await BaseWorker.report(task.id, "正在预处理日志（解压/拷贝）", 1.0)
            output_dir = default_preprocess_dir(log_file.id)
            loop = asyncio.get_running_loop()
            future = loop.run_in_executor(
                _executor, preprocess_log_dir, log_file.file_path, output_dir
            )
            TaskHandler._preprocess_inflight[log_file.id] = future
            try:
                result = await future
            finally:
                TaskHandler._preprocess_inflight.pop(log_file.id, None)

        logger.info(
            "日志预处理完成: task=%s log_file=%s source=%s output=%s extracted=%d copied=%d split=%d reused=%s",
            task.id,
            log_file.id,
            result.source_dir,
            result.output_dir,
            result.extracted_count,
            result.copied_count,
            result.split_count,
            result.reused,
        )
        message = "复用已完成的日志预处理目录" if result.reused else "日志预处理完成"
        await BaseWorker.report(task.id, message, 5.0)
        return result.output_dir

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
        tasks = await TaskPGManager.get_oldest_tasks_by_status(
            TaskStatusEnum.SUCCESSFUL_PENDING_REMOVE, handle_successed_task_limit
        )
        for task in tasks:
            try:
                await BaseWorker.deinit(task.id)
            except Exception as e:
                logger.exception(f"[TaskQueueService] 处理成功任务失败，task_id={task.id}, error={e}")

    @staticmethod
    async def handle_failed_tasks():
        handle_failed_task_limit = 128
        tasks = await TaskPGManager.get_oldest_tasks_by_status(
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
    async def _dispatch_pending_task(task) -> bool:
        """在后台预处理并启动单个待处理任务。

        由 handle_pending_tasks 以 fire-and-forget 协程调用：耗时的解压/拷贝
        不再阻塞成功收尾、失败重试与后续任务派发。
        """
        try:
            # 原子抢占：任务被并发停止/删除时直接放弃，避免复活已取消的任务。
            if not await TaskPGManager.transition_task_status(
                task.id, TaskStatusEnum.PENDING, TaskStatusEnum.RUNNING
            ):
                logger.info(
                    "[TaskQueueService] 任务 %s 派发前已被停止/删除，跳过", task.id
                )
                return False
            # All log workers share the same preprocessing entry point so
            # local archive paths are expanded before parsing/diagnosis.
            log_dir = await TaskHandler._preprocess_log_source(task)
            current_task = await TaskPGManager.get_task_by_task_id(task.id)
            if not current_task or current_task.status != TaskStatusEnum.RUNNING:
                logger.info(
                    "[TaskQueueService] 任务 %s 预处理期间被停止/删除，跳过启动",
                    task.id,
                )
                return False
            worker_kwargs = None
            persisted_config = getattr(task, "task_config", None)
            parse_config = (
                ParseConfig.model_validate(persisted_config)
                if persisted_config is not None
                else TaskHandler.get_task_config(task.id)
            )
            if task.task_type == TaskTypeEnum.KV_CACHE_LOG_PARSE_WORKER:
                worker_kwargs = {"parse_config": parse_config}
            if task.task_type == TaskTypeEnum.BRPC_LOG_DIAGNOSIS_WORKER:
                if parse_config and parse_config.start_time:
                    worker_kwargs = {"start_time": parse_config.start_time}
            flag = await BaseWorker.run(
                task.id,
                log_dir=log_dir,
                worker_kwargs=worker_kwargs,
            )
            if not flag:
                # 进程池满等临时原因没有启动进程：回到待解析，等下一轮派发。
                await TaskPGManager.transition_task_status(
                    task.id, TaskStatusEnum.RUNNING, TaskStatusEnum.PENDING
                )
            return flag
        except Exception as e:
            logger.exception(f"[TaskQueueService] 处理待处理任务失败 {e}")
            if isinstance(e, OSError) and e.errno == errno.ENOSPC:
                await TaskHandler._fail_preprocess_for_insufficient_space(task)
            else:
                await TaskHandler._fail_task_for_dispatch_error(task, e)
            return False
        finally:
            TaskHandler._dispatching_task_ids.discard(task.id)

    @staticmethod
    async def handle_pending_tasks():
        handle_pending_task_limit = 128
        single_batch_limit = 10
        pending_tasks = await TaskPGManager.get_oldest_tasks_by_status(
            TaskStatusEnum.PENDING, handle_pending_task_limit
        )
        dispatch_batch = []
        for task in pending_tasks:
            if len(dispatch_batch) >= single_batch_limit:
                break
            # 限制在途派发总量：单线程解压队列排队的任务不该抢先占住 RUNNING。
            if len(TaskHandler._dispatching_task_ids) >= single_batch_limit:
                break
            if task.id in TaskHandler._dispatching_task_ids:
                continue
            if not await asyncio.to_thread(ProcessHandler.has_capacity):
                break
            dispatch_batch.append(task)
        for task in dispatch_batch:
            TaskHandler._dispatching_task_ids.add(task.id)
            dispatch_task = asyncio.create_task(
                TaskHandler._dispatch_pending_task(task)
            )
            TaskHandler._dispatch_tasks.add(dispatch_task)
            dispatch_task.add_done_callback(TaskHandler._dispatch_tasks.discard)

    @staticmethod
    async def handle_tasks():
        await TaskHandler.handle_successed_tasks()
        await TaskHandler.handle_failed_tasks()
        await TaskHandler.handle_pending_tasks()
