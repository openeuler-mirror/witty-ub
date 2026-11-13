# Copyright (c) Huawei Technologies Co., Ltd. 2023-2026. All rights reserved.
"""Runtime patch for RAG Core's multiprocessing task slots.

The upstream implementation only removes a process from ``tasks`` when a
later deinit callback reaches the same Uvicorn worker. With multiple API
workers that callback can run elsewhere, leaving exited children in the
local dict forever. Reap exited children before enforcing the slot limit so
one missed callback cannot permanently stop document parsing.
"""

import asyncio
import logging
import multiprocessing
import os
import signal

from rag_core.config.config import Config

logger = logging.getLogger(__name__)
multiprocessing = multiprocessing.get_context("spawn")


class ProcessHandler:
    """Manage the document parsing child processes owned by this API worker."""

    tasks = {}
    lock = multiprocessing.Lock()
    max_processes = max(1, Config().get_config().task.cpu_limit)
    time_out = 10

    @staticmethod
    async def _init_databases_in_child() -> None:
        from rag_core.database.db_scalar.base.engine import BaseScalarDataBase
        from rag_core.database.db_vector.base.engine import BaseVectorDataBase

        await BaseScalarDataBase.init_database_specifics()
        await BaseVectorDataBase.init_database_specifics()

    @staticmethod
    async def _run_target_after_init(target, *args, **kwargs):
        await ProcessHandler._init_databases_in_child()
        return await target(*args, **kwargs)

    @staticmethod
    def subprocess_target(target, *args, **kwargs):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(
                ProcessHandler._run_target_after_init(target, *args, **kwargs)
            )
        except Exception as exc:
            logger.exception("[ProcessHandler] 子进程任务异常: %s", exc)
            raise
        finally:
            loop.close()

    @staticmethod
    def _reap_finished_tasks_locked() -> int:
        """Join exited children and release their in-memory slots."""
        reaped = 0
        for task_id, process in list(ProcessHandler.tasks.items()):
            try:
                alive = process.is_alive()
            except (AssertionError, ValueError):
                alive = False
            if alive:
                continue
            try:
                process.join(timeout=0)
            except (AssertionError, ValueError):
                pass
            ProcessHandler.tasks.pop(task_id, None)
            reaped += 1
        if reaped:
            logger.info("[ProcessHandler] 已回收 %s 个已退出任务槽位", reaped)
        return reaped

    @staticmethod
    def add_task(task_id: str, target, *args, **kwargs):
        acquired = ProcessHandler.lock.acquire(timeout=ProcessHandler.time_out)
        if not acquired:
            logger.warning("[ProcessHandler] 获取锁失败，可能是进程池已满或其他原因。请稍后再试。")
            return False

        try:
            ProcessHandler._reap_finished_tasks_locked()
            if len(ProcessHandler.tasks) >= ProcessHandler.max_processes:
                logger.warning(
                    "[ProcessHandler] 任务数量已达上限(%s)，请稍后再试。",
                    ProcessHandler.max_processes,
                )
                return False

            if task_id in ProcessHandler.tasks:
                logger.info("[ProcessHandler] 任务ID %s 已存在，无法添加。", task_id)
                return False

            try:
                process = multiprocessing.Process(
                    target=ProcessHandler.subprocess_target,
                    args=(target,) + args,
                    kwargs=kwargs,
                )
                ProcessHandler.tasks[task_id] = process
                process.start()
                return True
            except Exception as exc:
                ProcessHandler.tasks.pop(task_id, None)
                logger.error("[ProcessHandler] 添加任务 %s 失败: %s", task_id, exc)
                return False
        finally:
            ProcessHandler.lock.release()

    @staticmethod
    def remove_task(task_id: str):
        acquired = ProcessHandler.lock.acquire(timeout=ProcessHandler.time_out)
        if not acquired:
            logger.warning("[ProcessHandler] 获取锁失败，可能是进程池已满或其他原因。请稍后再试。")
            return
        try:
            ProcessHandler._reap_finished_tasks_locked()
            process = ProcessHandler.tasks.pop(task_id, None)
            if process is None:
                logger.debug("[ProcessHandler] 任务ID %s 已被回收或不属于当前进程。", task_id)
                return
            try:
                if process.is_alive():
                    os.kill(process.pid, signal.SIGKILL)
                    process.join(timeout=ProcessHandler.time_out)
                    logger.info("[ProcessHandler] 进程 %s (%s) 被杀死。", task_id, process.pid)
                else:
                    process.join(timeout=0)
            except (AssertionError, OSError, ValueError) as exc:
                logger.warning("[ProcessHandler] 清理进程 %s 失败: %s", task_id, exc)
            logger.info("[ProcessHandler] 任务ID %s 被删除。", task_id)
        finally:
            ProcessHandler.lock.release()
