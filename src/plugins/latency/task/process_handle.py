# Copyright (c) Huawei Technologies Co., Ltd. 2023-2024. All rights reserved.
import multiprocessing
import uuid
import asyncio
import logging
from latency.config.config import Config

logger = logging.getLogger(__name__)
multiprocessing = multiprocessing.get_context("spawn")


class ProcessHandler:
    """进程处理器类"""

    tasks = {}  # 存储进程的字典
    lock = multiprocessing.Lock()  # 创建一个锁对象
    max_processes = max(1, Config().get_config().task.cpu_limit)
    time_out = 10

    @staticmethod
    async def _run_target_after_init(target, *args, **kwargs):
        return await target(*args, **kwargs)

    @staticmethod
    def _setup_child_process_logging():
        config = Config().get_config()
        log_level_str = config.service.log_level.value
        numeric_level = getattr(logging, log_level_str, logging.INFO)
        
        logging.basicConfig(
            level=numeric_level,
            format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        
        logging.getLogger("latency.task.task_handler").setLevel(logging.WARNING)
        logging.getLogger("latency.database").setLevel(logging.WARNING)
        logging.getLogger("apscheduler.executors.default").setLevel(logging.WARNING)

    @staticmethod
    def subprocess_target(target, *args, **kwargs):
        ProcessHandler._setup_child_process_logging()
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(
                ProcessHandler._run_target_after_init(target, *args, **kwargs)
            )
        except Exception as e:
            logger.exception("[ProcessHandler] 子进程任务异常: %s", e)
            raise
        finally:
            loop.close()

    @staticmethod
    def add_task(task_id: str, target, *args, **kwargs):
        """添加任务到进程池"""
        acquired = ProcessHandler.lock.acquire(timeout=ProcessHandler.time_out)
        if not acquired:
            warning = f"获取锁失败，可能是进程池已满或其他原因。请稍后再试。"
            logger.warning(f"[ProcessHandler] %s", warning)
            return False

        if len(ProcessHandler.tasks) >= ProcessHandler.max_processes:
            warning = f"任务数量已达上限({ProcessHandler.max_processes})，请稍后再试。"
            logging.warning(f"[ProcessHandler] %s", warning)
            ProcessHandler.lock.release()
            return False

        if task_id not in ProcessHandler.tasks:
            try:
                process = multiprocessing.Process(
                    target=ProcessHandler.subprocess_target,
                    args=(target,) + args,
                    kwargs=kwargs,
                )
                ProcessHandler.tasks[task_id] = process
                process.start()
                ProcessHandler.lock.release()
                return True
            except Exception as e:
                error = f"添加任务 {task_id} 失败: {e}"
                logger.error(f"[ProcessHandler] %s", error)
                ProcessHandler.lock.release()
                return False
        else:
            info = f"任务ID {task_id} 已存在，无法添加。"
            logger.info(f"[ProcessHandler] %s", info)
            ProcessHandler.lock.release()
            return False

    @staticmethod
    def remove_task(task_id: str):
        acquired = ProcessHandler.lock.acquire(timeout=ProcessHandler.time_out)
        if not acquired:
            warning = f"获取锁失败，可能是进程池已满或其他原因。请稍后再试。"
            logger.warning(f"[ProcessHandler] %s", warning)
            return
        if task_id in ProcessHandler.tasks.keys():
            process = ProcessHandler.tasks[task_id]
            del ProcessHandler.tasks[task_id]
            try:
                if process.is_alive():
                    pid = process.pid
                    process.kill()
                    info = f"任务 {task_id} ({pid}) 被杀死。"
                    logger.info(f"[ProcessHandler] %s", info)
            except Exception as e:
                warning = f"杀死进程 {task_id} 失败: {e}"
                logger.warning(f"[ProcessHandler] %s", warning)
            info = f"任务ID {task_id} 被删除。"
            logger.info(f"[ProcessHandler] %s", info)
        else:
            waring = f"任务ID {task_id} 不存在，无法删除。"
            logger.warning(f"[ProcessHandler] %s", waring)
        ProcessHandler.lock.release()