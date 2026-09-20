# Copyright (c) Huawei Technologies Co., Ltd. 2023-2024. All rights reserved.
import asyncio
import ctypes
import logging
import multiprocessing
import os
import signal

from latency.config.config import Config
from latency.database.engine import PGManager

logger = logging.getLogger(__name__)
multiprocessing = multiprocessing.get_context("spawn")

#: 子进程 CPU 优先级（nice）。解析类任务 = 0；诊断 / 上下文落库 = +10（给解析让路）。
#: 一个日志文件会同时派发这三个任务（闸门 = max_concurrent_tasks = 3），而诊断会拉起外部
#: 二进制扫同一批日志、没有任何并发限制；本地受控实验里额外 8 个竞争进程让扫描墙钟 +70%。
#: 置 0 即回到旧行为（改这一个常量就能回滚）。
CHILD_NICE_PARSE = 0
# 2026-09-17 用户要求「三个任务公平竞争」，把背景优先级从 10 改回 0。
# 想恢复错峰：把这里改回 10 即可（只动这一个常量，无其他副作用）。
CHILD_NICE_BACKGROUND = 0

# Linux ``comm`` is limited to 15 visible bytes.  Keep the type first so tools
# such as ps/top and scripts/monitor_worker_memory.sh can identify each worker.
_WORKER_PROCESS_NAMES = {
    "KVCacheLogParseWorker": "kv-parse",
    "KVCacheLogEventDiagnosisWorker": "kv-diag",
    "StoreTraceContextLogsWorker": "trace-store",
    "BrpcLogParseWorker": "brpc-parse",
    "BrpcLogDiagnosisWorker": "brpc-diag",
}


class ProcessHandler:
    """进程处理器类"""

    tasks = {}  # 存储进程的字典
    lock = multiprocessing.Lock()  # 创建一个锁对象
    max_processes = min(
        Config().get_config().task.cpu_limit,
        Config().get_config().task.max_concurrent_tasks,
    )
    time_out = 10
    # 收尾等待（秒）：SIGTERM 优雅退出后等多久、升级 SIGKILL 后再等多久
    _GRACEFUL_JOIN_S = 2
    _KILL_JOIN_S = 2

    @staticmethod
    def _process_name(target, task_id: str) -> str:
        owner = getattr(target, "__qualname__", "").split(".", 1)[0]
        worker = _WORKER_PROCESS_NAMES.get(owner, "latency-worker")
        return f"{worker}:{task_id[:8]}"

    @staticmethod
    def _set_os_process_name() -> None:
        """Expose the multiprocessing name through Linux /proc/PID/comm."""
        if os.name != "posix":
            return
        name = multiprocessing.current_process().name.encode("utf-8")[:15]
        try:
            libc = ctypes.CDLL(None, use_errno=True)
            if libc.prctl(15, ctypes.c_char_p(name), 0, 0, 0) != 0:  # PR_SET_NAME
                logger.debug("[ProcessHandler] 设置进程名失败: errno=%s", ctypes.get_errno())
        except (AttributeError, OSError):
            logger.debug("[ProcessHandler] 当前平台不支持设置进程名", exc_info=True)

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
    def subprocess_target(ready_event, target, *args, child_nice: int = 0, **kwargs):
        ProcessHandler._setup_child_process_logging()
        ProcessHandler._set_os_process_name()

        # Every task owns a process group.  Native tools launched by a worker
        # inherit this group, allowing cancellation to reap the complete tree
        # instead of only the Python wrapper process.
        try:
            os.setsid()
        except OSError:
            logger.exception("[ProcessHandler] 创建任务进程组失败")
        finally:
            ready_event.set()

        # 子进程优先级：解析拿默认优先级，诊断/落库退让（os.nice 仅 Unix 有）
        if child_nice and hasattr(os, "nice"):
            try:
                os.nice(int(child_nice))
            except OSError as exc:  # noqa: BLE001
                logger.warning("[ProcessHandler] set nice(%s) failed: %s", child_nice, exc)

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
        exits = {}
        dead_tasks = [
            tid for tid, proc in ProcessHandler.tasks.items() 
            if not proc.is_alive()
        ]
        for tid in dead_tasks:
            process = ProcessHandler.tasks.pop(tid)
            process.join()
            exits[tid] = process.exitcode
            process.close()
            logger.debug(f"[ProcessHandler] 清理已结束的进程: {tid}")
        return exits

    @staticmethod
    def collect_finished_tasks():
        """Collect child exit codes so the scheduler can persist abnormal exits."""
        if not ProcessHandler.lock.acquire(timeout=ProcessHandler.time_out):
            return {}
        try:
            return ProcessHandler._cleanup_dead_processes()
        finally:
            ProcessHandler.lock.release()

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
    def add_task(task_id: str, target, *args, child_nice: int = 0, **kwargs):
        """添加任务到进程池（child_nice 见 CHILD_NICE_* 常量）"""
        acquired = ProcessHandler.lock.acquire(timeout=ProcessHandler.time_out)
        if not acquired:
            warning = "获取锁失败，可能是进程池已满或其他原因。请稍后再试。"
            logger.warning("[ProcessHandler] %s", warning)
            return False

        if len(ProcessHandler.tasks) >= ProcessHandler.max_processes:
            ProcessHandler._cleanup_dead_processes()
            
        if len(ProcessHandler.tasks) >= ProcessHandler.max_processes:
            warning = f"任务数量已达上限({ProcessHandler.max_processes})，请稍后再试。"
            logging.warning("[ProcessHandler] %s", warning)
            ProcessHandler.lock.release()
            return False

        if task_id not in ProcessHandler.tasks:
            released = False
            try:
                ready_event = multiprocessing.Event()
                process = multiprocessing.Process(
                    name=ProcessHandler._process_name(target, task_id),
                    target=ProcessHandler.subprocess_target,
                    args=(ready_event, target) + args,
                    kwargs={**kwargs, "child_nice": child_nice},
                )
                process.start()
                ProcessHandler.tasks[task_id] = process
                logger.debug(f"[ProcessHandler] 任务 {task_id} 已添加到进程池，PID: {process.pid}")
                # 先放锁再等就绪：等的是子进程 import + 建进程组（可能数秒），
                # 握锁等会把同一批任务的 spawn 串行化（实测三个任务各差 3.7s）。
                ProcessHandler.lock.release()
                released = True
                if not ready_event.wait(timeout=ProcessHandler.time_out):
                    logger.warning(
                        "[ProcessHandler] 任务 %s 等待进程组初始化超时", task_id
                    )
                return True
            except Exception as e:
                error = f"添加任务 {task_id} 失败: {e}"
                logger.exception("[ProcessHandler] %s", error)
                if not released:
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
            warning = "获取锁失败，可能是进程池已满或其他原因。请稍后再试。"
            logger.warning("[ProcessHandler] %s", warning)
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
                    # 收尾等待不能长：这段在调度任务里被 await，等 10s 会把
                    # 1s 的派发节拍整拍吃掉（实测每轮 handle_tasks 跑 ~4s，
                    # 导致后续任务错峰开工）。
                    process.join(timeout=_GRACEFUL_JOIN_S)
                    if process.is_alive():
                        try:
                            pgid = os.getpgid(pid)
                            if pgid == pid:
                                os.killpg(pgid, signal.SIGKILL)
                            else:
                                process.kill()
                        except ProcessLookupError:
                            pass
                        process.join(timeout=_KILL_JOIN_S)
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
