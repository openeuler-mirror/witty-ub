import asyncio
import os
import logging
import uuid
import time
import shutil

from latency.task.worker.base import BaseWorker
from latency.config.config import Config
from latency.database.managers.log_file import LogFilePGManager
from latency.database.managers.log_parse_result import LogParseResultPGManager
from latency.database.managers.task import TaskPGManager
from latency.task.worker.kv_cache_log_event_diagnosis_worker import KVCacheLogEventDiagnosisWorker
from latency.ENUM.task import TaskStatusEnum, TaskTypeEnum
from latency.database.managers.log_failure_event import LogFailureEventPGManager
from latency.schemas.task import TaskModel
from latency.database.managers.failure_mode_knowledge import FailureModeKnowledgePGManager
from latency.task.log_preprocessor import cleanup_preprocess_dir


logger = logging.getLogger(__name__)
WITTY_DIR_DEFAULT = "/var/witty-ub"
witty_dir = os.getenv("WITTY_DIR", WITTY_DIR_DEFAULT)

SUCCESS_STATUSES = {
    TaskStatusEnum.SUCCESSFUL_PENDING_REMOVE,
    TaskStatusEnum.SUCCESSFUL,
}
FAILED_STATUSES = {
    TaskStatusEnum.FAILED_PENDING_REMOVE,
    TaskStatusEnum.FAILED,
    TaskStatusEnum.CANCELLED,
}
MONITOR_INTERVAL_SECONDS = 5


def cleanup_temp_dirs(output_log_path: str, log_file_id: str) -> None:
    """清理临时文件夹，包括诊断输出和预处理的日志"""
    if output_log_path and os.path.exists(output_log_path):
        try:
            shutil.rmtree(output_log_path)
            logger.info("清理诊断输出目录: %s", output_log_path)
        except OSError as e:
            logger.error("清理诊断输出目录 %s 失败: %s", output_log_path, e)
    
    if log_file_id:
        cleanup_preprocess_dir(log_file_id)


class StoreTraceContextLogsWorker(BaseWorker):
    """
    Worker for storing trace context logs.
    """

    name = TaskTypeEnum.STORE_TRACE_CONTEXT_LOGS_WORKER

    @staticmethod
    async def _generate_trace_id_set_diagnosis(output_log_path: str) -> tuple[set[str], dict[str, list[str]]]:
        trace_id_set = set()
        trace_failure_id = dict()
        if not os.path.exists(output_log_path):
            logger.error(f"输出日志路径不存在: {output_log_path}")
            return set(), dict()
        
        failure_trace_path = os.path.join(output_log_path, "failure_trace.log")
        if os.path.exists(failure_trace_path):
            try:
                with open(failure_trace_path, 'r', encoding='utf-8') as f:
                    for line in f:
                        line = line.strip()
                        if not line:
                            continue
                        
                        parts = line.split('|', 1)
                        if len(parts) == 2:
                            raw_text = parts[1].strip()
                            raw_parts = raw_text.split('|')
                            trace_failure_id[raw_text] = list(dict.fromkeys(
                                mode.strip()
                                for mode in parts[0].split(",")
                                if mode.strip()
                            ))
                            if len(raw_parts) >= 6:
                                trace_id = raw_parts[5].strip()
                                if trace_id:
                                    trace_id_set.add(trace_id)
                
                logger.info(f"从 failure_trace.log 提取到 {len(trace_id_set)} 个 trace_id")
            
            except Exception as e:
                logger.error(f"解析 failure_trace.log 失败: {e}")

        return trace_id_set, trace_failure_id

    @staticmethod
    async def _store_trace_context_logs(
        output_log_path: str,
        log_id: str,
        trace_id_set: set,
        trace_failure_id: dict[str, list[str]],
        task_id: str | None = None,
        progress_base: float = 0.0,
        progress_end: float = 100.0,
    ):
        # 将output_log_path下，除了failure_trace.log以外的所有日志读到log_failure_event_table数据库中
        # 除了failure_trace.log以外，output_log_path目录下的日志都是以下模板："timestamp | level | filename | pod_name | pid:tid | trace_id | cluster_name | message"，  
        # 对应LogFailureEventModel数据结构中的相应字段。除了这些字段以外，log_id对应函数参数输入，log_file对应日志文件名，raw_text对应原始日志。
        # status_code的读取方式略微复杂。仅当log_file对应的日志文件名能够匹配parse_filepath_config()得到的字典中，键为ds-worker-access-log-file和
        # ds-client-access-log-file的值所表示的正则表达式，即为access log日志时，日志才有status_code字段。具体而言，status_code字段是message字段中以" | "分割的第一个字段
        # 将failure_trace.log中的故障模式字段添加到数据库中
        # 将output_log_path下的failure_trace.log中是解析到的所有故障日志。每行日志的格式为failure_mode | raw_text，即将failure_mode字段添加到raw_text对应行的数据库条目中。你应该需要在
        # LogFailureEventManager中加入一个update_failure_mode_by_raw_log函数来完成数据库更新的操作。
        try:
            if not trace_id_set:
                logger.info("failure_trace.log 中没有可落库的 trace_id")
                return

            log_file_model = await LogFilePGManager.get_log_file_by_log_file_id(log_id)
            config = await KVCacheLogEventDiagnosisWorker.parse_filepath_config(
                log_file_model.kb_id if log_file_model else None
            )
            failure_mode_cache = await FailureModeKnowledgePGManager.get_all_failure_modes()
            worker_access_patterns = config.get("ds_worker_access_log_file", [])
            client_access_patterns = config.get("ds_client_access_log_file", [])
               
            log_files = []
            for file in os.listdir(output_log_path):
                file_path = os.path.join(output_log_path, file)
                if os.path.isfile(file_path) and file != "failure_trace.log":
                    log_files.append((file, file_path))
            
            log_failure_events = []
            trace_failure_events_map: dict[str, dict] = {}
            total_inserted = 0
            batch_size = 100000
            total_log_failure_events = KVCacheLogEventDiagnosisWorker._count_log_failure_events(
                log_files,
                trace_id_set,
                worker_access_patterns,
                client_access_patterns,
            )
            
            print(f"开始日志落库，共{len(trace_id_set)}条故障trace，{total_log_failure_events}条日志事件")
            t_store_start = time.perf_counter()

            def _report_progress(inserted: int) -> None:
                if not task_id or total_log_failure_events <= 0:
                    return
                progress = progress_base + (progress_end - progress_base) * (
                    inserted / total_log_failure_events
                )
                asyncio.create_task(
                    BaseWorker.report(
                        task_id,
                        f"Trace context logs stored {inserted}/{total_log_failure_events}",
                        min(progress, progress_end),
                    )
                )

            for log_file_name, log_file_path in log_files:
                try:
                    is_access_log = False  
                    if KVCacheLogEventDiagnosisWorker._matches_any(
                        log_file_name, worker_access_patterns
                    ):
                        is_access_log = True
                    if KVCacheLogEventDiagnosisWorker._matches_any(
                        log_file_name, client_access_patterns
                    ):
                        is_access_log = True
                    with open(log_file_path, 'r', encoding='utf-8') as f:
                        for line in f:
                            try:
                                raw_line = line.strip()
                                if not raw_line:
                                    continue
                                
                                parts = raw_line.split('|')
                                
                                if len(parts) < 7:
                                    continue
                                
                                trace_id = parts[5].strip() if len(parts) > 5 else ""
                                
                                if not trace_id or trace_id not in trace_id_set:
                                    continue
                                
                                timestamp = parts[0].strip()
                                level = parts[1].strip()
                                filename = parts[2].strip()
                                pod_name = parts[3].strip()
                                pid_tid = parts[4].strip()
                                cluster_name = parts[6].strip() if len(parts) > 6 else ""
                                
                                pid_tid_parts = pid_tid.split(':')
                                if len(pid_tid_parts) == 2:
                                    pid, tid = pid_tid_parts
                                else:
                                    pid = pid_tid
                                    tid = ""
                                
                                status_code = ""
                                message = ""	 
                                   
                                if is_access_log:
                                    if len(parts) > 7:  
                                        status_code = parts[7].strip()  
                                        message = '|'.join(parts[7:]) if len(parts) > 7 else ""  
                                    else:  
                                        logger.warning(f"access log格式不正确，字段不足: {raw_line}")  
                                        continue  
                                else:  
                                    message = '|'.join(parts[7:]) if len(parts) > 7 else ""
                                
                                failure_mode = trace_failure_id.get(raw_line, []) if trace_failure_id else None
                                log_failure_event = {
                                    "id": str(uuid.uuid4()),
                                    "log_id": log_id,
                                    "log_file": log_file_name,
                                    "raw_text": raw_line,
                                    "host_name": "Unknown",
                                    "timestamp": timestamp.replace("T", " "),
                                    "level": level,
                                    "filename": filename,
                                    "pod_name": pod_name,
                                    "pid": pid,
                                    "tid": tid,
                                    "trace_id": trace_id,
                                    "cluster_name": cluster_name,
                                    "message": message.strip(),
                                    "status_code": status_code,
                                    "failure_mode": failure_mode,
                                }
                                KVCacheLogEventDiagnosisWorker._merge_trace_failure_event(
                                    trace_failure_events_map,
                                    log_failure_event,
                                    failure_mode_cache,
                                )
                                log_failure_events.append(log_failure_event)
                                
                                if len(log_failure_events) >= batch_size:
                                    await LogFailureEventPGManager.add_log_failure_event_raw(log_failure_events)
                                    total_inserted += len(log_failure_events)
                                    progress_msg = (
                                        f"日志事件落盘进度：{total_inserted}/{total_log_failure_events}"
                                    )
                                    logger.info(progress_msg)
                                    print(progress_msg)
                                    _report_progress(total_inserted)
                                    log_failure_events = []
                            
                            except Exception as e:
                                logger.warning(f"读取日志文件 {log_file_path} 行失败: {line}, 错误: {e}")
                                continue
                
                except Exception as e:
                    logger.warning(f"读取日志文件 {log_file_path} 失败: {e}")
                    continue
            
            if log_failure_events:
                await LogFailureEventPGManager.add_log_failure_event_raw(log_failure_events)
                total_inserted += len(log_failure_events)
                progress_msg = (
                    f"日志事件落盘进度：{total_inserted}/{total_log_failure_events}"
                )
                logger.info(progress_msg)
                print(progress_msg)
                _report_progress(total_inserted)

            trace_failure_events = list(trace_failure_events_map.values())
            if trace_failure_events:
                trace_store_start = time.perf_counter()
                await LogFailureEventPGManager.add_trace_failure_event_raw(trace_failure_events)
                logger.info(
                    "成功插入 %s 条trace故障事件，耗时 %.3fs",
                    len(trace_failure_events),
                    time.perf_counter() - trace_store_start,
                )

            logger.info(
                "Trace context logs store done: %s log_failure_events, %s trace_failure_events, total %.3fs",
                total_inserted,
                len(trace_failure_events),
                time.perf_counter() - t_store_start,
            )

            if task_id:
                await BaseWorker.report(
                    task_id,
                    f"Trace context logs stored {total_inserted}/{total_log_failure_events}",
                    progress_end,
                )

            return
    
        except Exception as e:
            logger.error(f"parse_log_failure_events 执行失败: {e}")
        
        return

    @staticmethod
    async def init(op_id: str) -> str | None:
        log_file_model = await LogFilePGManager.get_log_file_by_log_file_id(op_id)
        if not log_file_model:
            return None

        task = TaskModel(
            kb_id=log_file_model.kb_id,
            op_id=op_id,
            task_name=f"Store trace context logs: {log_file_model.name}",
            task_type=TaskTypeEnum.STORE_TRACE_CONTEXT_LOGS_WORKER,
            status=TaskStatusEnum.PENDING,
        )
        await TaskPGManager.add_task(task)
        await BaseWorker.report(task.id, "Task initialized", 0.0)
        return task.id

    @staticmethod
    async def reinit(task_id: str) -> bool:
        task = await TaskPGManager.get_task_by_task_id(task_id)
        if not task:
            return False
        if task.retry_times > Config().get_config().task.task_retry_times:
            logger.warning(
                "Task %s retry count %s exceeded max retries %s",
                task_id,
                task.retry_times,
                Config().get_config().task.task_retry_times,
            )
            return False
        await BaseWorker.report(task.id, "Task reinitialized", 0.0)
        return True

    @staticmethod
    async def deinit(task_id: str) -> str:
        return task_id

    @staticmethod
    async def _wait_for_worker_success(
        op_id: str,
        task_type: TaskTypeEnum,
        dependency_name: str,
        monitor_task_id: str,
        progress: float,
    ) -> bool:
        while True:
            task = await TaskPGManager.get_current_task_by_op_id(op_id, task_type)
            if not task:
                await BaseWorker.report(
                    monitor_task_id,
                    f"Waiting for {dependency_name} task to be created",
                    progress,
                )
                await asyncio.sleep(MONITOR_INTERVAL_SECONDS)
                continue

            if task.status in SUCCESS_STATUSES:
                await BaseWorker.report(
                    monitor_task_id,
                    f"{dependency_name} task completed",
                    progress,
                )
                return True

            if task.status in FAILED_STATUSES:
                logger.error(
                    "%s task %s ended with status %s",
                    dependency_name,
                    task.id,
                    task.status,
                )
                await BaseWorker.report(
                    monitor_task_id,
                    f"{dependency_name} task ended with status {task.status}",
                    progress,
                )
                return False

            await BaseWorker.report(
                monitor_task_id,
                f"Waiting for {dependency_name} task, current status: {task.status}",
                progress,
            )
            await asyncio.sleep(MONITOR_INTERVAL_SECONDS)

    @staticmethod
    async def run(task_id: str, log_dir: str | None = None) -> bool:
        output_log_path = None
        log_file_id = None
        try:
            task = await TaskPGManager.get_task_by_task_id(task_id)
            if not task:
                logger.error("Task %s not found", task_id)
                return False

            await TaskPGManager.update_task(
                task_id, {"status": TaskStatusEnum.RUNNING.value}
            )
            await BaseWorker.report(task.id, "Task running", 5.0)

            log_file = await LogFilePGManager.get_log_file_by_log_file_id(task.op_id)
            if not log_file:
                logger.error("LogFile %s not found", task.op_id)
                await TaskPGManager.update_task(
                    task_id, {"status": TaskStatusEnum.FAILED_PENDING_REMOVE.value}
                )
                cleanup_temp_dirs(None, task.op_id)
                return False

            log_id = log_file.id
            log_file_id = log_file.id
            random_str = log_file.id[:8]
            output_log_path = os.path.join(witty_dir, "log_" + random_str)

            diagnosis_done = await StoreTraceContextLogsWorker._wait_for_worker_success(
                task.op_id,
                TaskTypeEnum.KV_CACHE_LOG_EVENT_DIAGNOSIS_WORKER,
                "diagnosis",
                task.id,
                20.0,
            )
            if not diagnosis_done:
                await TaskPGManager.update_task(
                    task_id, {"status": TaskStatusEnum.FAILED_PENDING_REMOVE.value}
                )
                cleanup_temp_dirs(output_log_path, log_file_id)
                return False

            trace_id_set, trace_failure_id = await StoreTraceContextLogsWorker._generate_trace_id_set_diagnosis(
                output_log_path=output_log_path,
            )
            await StoreTraceContextLogsWorker._store_trace_context_logs(
                output_log_path=output_log_path,
                log_id=log_id,
                trace_id_set=trace_id_set,
                trace_failure_id=trace_failure_id,
                task_id=task.id,
                progress_base=20.0,
                progress_end=45.0,
            )
            await LogFilePGManager.update_log_file(
                task.op_id, {"failure_count": len(trace_id_set)}
            )
            await BaseWorker.report(
                task.id,
                f"Trace context logs stored after diagnosis: {len(trace_id_set)}",
                45.0,
            )

            parse_done = await StoreTraceContextLogsWorker._wait_for_worker_success(
                task.op_id,
                TaskTypeEnum.KV_CACHE_LOG_PARSE_WORKER,
                "parse",
                task.id,
                65.0,
            )
            if not parse_done:
                await TaskPGManager.update_task(
                    task_id, {"status": TaskStatusEnum.FAILED_PENDING_REMOVE.value}
                )
                cleanup_temp_dirs(output_log_path, log_file_id)
                return False

            latency_anomalous_trace_id_set = await LogParseResultPGManager.list_anomalous_trace_ids_by_log_id(
                log_id
            )
            trace_id_set = latency_anomalous_trace_id_set - trace_id_set
            logger.info(
                "新增 %s 个时延异常 trace_id",
                len(trace_id_set),
            )
            await StoreTraceContextLogsWorker._store_trace_context_logs(
                output_log_path=output_log_path,
                log_id=log_id,
                trace_id_set=trace_id_set,
                trace_failure_id=None,
                task_id=task.id,
                progress_base=65.0,
                progress_end=90.0,
            )
            await BaseWorker.report(
                task.id,
                f"Trace context logs stored after parse: {len(latency_anomalous_trace_id_set)}",
                90.0,
            )

            await BaseWorker.report(task.id, "Task completed successfully", 100.0)
            await TaskPGManager.update_task(
                task_id, {"status": TaskStatusEnum.SUCCESSFUL_PENDING_REMOVE.value}
            )
            return True
        except Exception as e:
            logger.exception("Task %s failed: %s", task_id, e)
            await TaskPGManager.update_task(
                task_id, {"status": TaskStatusEnum.FAILED_PENDING_REMOVE.value}
            )
            return False

    @staticmethod
    async def stop(task_id: str) -> str | None:
        task = await TaskPGManager.get_task_by_task_id(task_id)
        if not task:
            return None
        if task.status in [TaskStatusEnum.PENDING, TaskStatusEnum.RUNNING]:
            await TaskPGManager.update_task(
                task_id, {"status": TaskStatusEnum.CANCELLED.value}
            )
            return task_id
        return None

    @staticmethod
    async def delete(task_id: str) -> str:
        return task_id
