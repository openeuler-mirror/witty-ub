# Copyright (c) Huawei Technologies Co., Ltd. 2023-2024. All rights reserved.
import multiprocessing
import asyncio
import logging
import os
import signal
from latency.config.config import Config
from latency.database.engine import PGManager

logger = logging.getLogger(__name__)
multiprocessing = multiprocessing.get_context("spawn")


class ProcessHandler:
    """进程处理器类"""

    tasks = {}  # 存储进程的字典
    lock = multiprocessing.Lock()  # 创建一个锁对象
    max_processes = min(
        Config().get_config().task.cpu_limit,
        Config().get_config().task.max_concurrent_tasks,
    )
    time_out = 10

    @staticmethod
    async def _run_target_after_init(target, *args, **kwargs):
        config = Config().get_config()
        if config.db.backend == "postgresql":
            await PGManager.init_timezone()
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
        
        logging.getLogger("latency.task.task_handler").setLevel(logging.INFO)
        logging.getLogger("latency.database").setLevel(logging.WARNING)
        logging.getLogger("apscheduler.executors.default").setLevel(logging.WARNING)

    @staticmethod
    def subprocess_target(ready_event, target, *args, **kwargs):
        ProcessHandler._setup_child_process_logging()

        # Every task owns a process group.  Native tools launched by a worker
        # inherit this group, allowing cancellation to reap the complete tree
        # instead of only the Python wrapper process.
        try:
            os.setsid()
        except OSError:
            logger.exception("[ProcessHandler] 创建任务进程组失败")
        finally:
            ready_event.set()

        config = Config().get_config()
        if config.db.backend == "postgresql":
            PGManager.initialize(
                config.db.pg_dsn_url(),
                pool_size=config.db.pg_pool_size,
                max_overflow=config.db.pg_max_overflow,
            )

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
    def _cleanup_dead_processes():
        """清理已结束的进程"""
        dead_tasks = [
            tid for tid, proc in ProcessHandler.tasks.items() 
            if not proc.is_alive()
        ]
        for tid in dead_tasks:
            process = ProcessHandler.tasks.pop(tid)
            process.join()
            process.close()
            logger.debug(f"[ProcessHandler] 清理已结束的进程: {tid}")

    @staticmethod
    def has_capacity():
        """Check admission before spending disk IO on pending tasks."""
        if not ProcessHandler.lock.acquire(timeout=ProcessHandler.time_out):
            return False
        try:
            ProcessHandler._cleanup_dead_processes()
            return len(ProcessHandler.tasks) < ProcessHandler.max_processes
        finally:
            ProcessHandler.lock.release()

    @staticmethod
    def add_task(task_id: str, target, *args, **kwargs):
        """添加任务到进程池"""
        acquired = ProcessHandler.lock.acquire(timeout=ProcessHandler.time_out)
        if not acquired:
            warning = f"获取锁失败，可能是进程池已满或其他原因。请稍后再试。"
            logger.warning(f"[ProcessHandler] %s", warning)
            return False

        if len(ProcessHandler.tasks) >= ProcessHandler.max_processes:
            ProcessHandler._cleanup_dead_processes()
            
        if len(ProcessHandler.tasks) >= ProcessHandler.max_processes:
            warning = f"任务数量已达上限({ProcessHandler.max_processes})，请稍后再试。"
            logging.warning(f"[ProcessHandler] %s", warning)
            ProcessHandler.lock.release()
            return False

        if task_id not in ProcessHandler.tasks:
            try:
                ready_event = multiprocessing.Event()
                process = multiprocessing.Process(
                    target=ProcessHandler.subprocess_target,
                    args=(ready_event, target) + args,
                    kwargs=kwargs,
                )
                process.start()
                if not ready_event.wait(timeout=ProcessHandler.time_out):
                    logger.warning(
                        "[ProcessHandler] 任务 %s 等待进程组初始化超时", task_id
                    )
                ProcessHandler.tasks[task_id] = process
                logger.debug(f"[ProcessHandler] 任务 {task_id} 已添加到进程池，PID: {process.pid}")
                ProcessHandler.lock.release()
                return True
            except Exception as e:
                error = f"添加任务 {task_id} 失败: {e}"
                logger.error(f"[ProcessHandler] %s", error)
                ProcessHandler.lock.release()
                return False
        else:
            logger.debug(f"[ProcessHandler] 任务 {task_id} 已在进程池中，跳过添加")
            ProcessHandler.lock.release()
            return True

    @staticmethod
    def remove_task(task_id: str):
        acquired = ProcessHandler.lock.acquire(timeout=ProcessHandler.time_out)
        if not acquired:
            warning = f"获取锁失败，可能是进程池已满或其他原因。请稍后再试。"
            logger.warning(f"[ProcessHandler] %s", warning)
            return False
        
        if task_id in ProcessHandler.tasks:
            process = ProcessHandler.tasks[task_id]
            try:
                if process.is_alive():
                    pid = process.pid
                    try:
                        pgid = os.getpgid(pid)
                        if pgid == pid:
                            os.killpg(pgid, signal.SIGTERM)
                        else:
                            # Never signal a group we do not own (for example
                            # the API server's group if setsid failed).
                            process.terminate()
                    except ProcessLookupError:
                        pass
                    process.join(timeout=10)
                    if process.is_alive():
                        try:
                            pgid = os.getpgid(pid)
                            if pgid == pid:
                                os.killpg(pgid, signal.SIGKILL)
                            else:
                                process.kill()
                        except ProcessLookupError:
                            pass
                        process.join(timeout=5)
                    if process.is_alive():
                        logger.warning(
                            "[ProcessHandler] 任务 %s (PID: %s) 强制终止后仍存活",
                            task_id,
                            pid,
                        )
                        ProcessHandler.lock.release()
                        return False
                    else:
                        logger.info(
                            "[ProcessHandler] 任务 %s (PID: %s) 及其子进程已终止",
                            task_id,
                            pid,
                        )
                else:
                    logger.debug(f"[ProcessHandler] 任务 {task_id} 进程已自然结束")
                ProcessHandler.tasks.pop(task_id, None)
                process.close()
            except Exception as e:
                logger.warning(f"[ProcessHandler] 清理进程 {task_id} 失败: {e}")
                ProcessHandler.lock.release()
                return False
            logger.debug(f"[ProcessHandler] 任务 {task_id} 已从进程池移除")
        else:
            logger.debug(f"[ProcessHandler] 任务 {task_id} 不在进程池中，可能已结束或未启动")
        ProcessHandler.lock.release()
        return True
