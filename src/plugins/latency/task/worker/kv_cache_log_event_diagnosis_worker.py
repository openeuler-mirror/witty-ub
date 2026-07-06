import asyncio
import fnmatch
import logging
import os
import uuid
import subprocess
import shutil
import gzip
import zipfile
import time
from datetime import datetime
from latency.schemas.log_failure_event import TraceFailureEventModel
from latency.ENUM.task import TaskStatusEnum, TaskTypeEnum
from latency.common.ds_log_io import glob_paths, open_log
from latency.config.config import Config
from latency.detect import AnomalyDetector
from latency.database.engine import AsyncSQLiteSingleton
from latency.database.managers.log_parse_result import LogParseResultManager
from latency.database.managers.task import TaskManager
from latency.database.managers.task_report import TaskReportManager
from latency.database.managers.log_knowledge import LogKnowledgeManager
from latency.database.managers.log_file import LogFileManager
from latency.database.managers.log_failure_event import LogFailureEventManager
from latency.database.managers.src_dst_aggregated_event import (
    SrcDstAggregatedEventManager,
)
from latency.database.managers.anomalous_event import AnomalousEventManager
from latency.database.managers.anomalous_event_chain import AnomalousEventChainManager
from latency.schemas.task import TaskModel
from latency.schemas.log import (
    LogFileModel,
)
from latency.task.worker.base import BaseWorker



logger = logging.getLogger(__name__)
WITTY_INSTALL_PATH_DEFAULT = "/usr/bin"
WITTY_DIR_DEFAULT = "/var/witty-ub"
witty_dir = os.getenv("WITTY_DIR", WITTY_DIR_DEFAULT)

class KVCacheLogEventDiagnosisWorker(BaseWorker):
    """
    KVCacheLogEventDiagnosisWorker
    """

    name = TaskTypeEnum.KV_CACHE_LOG_EVENT_DIAGNOSIS_WORKER

    @staticmethod
    async def init(op_id: str) -> str | None:
        """初始化任务"""
        log_file_model = await LogFileManager.get_log_file_by_log_file_id(op_id)
        if not log_file_model:
            return None
        kb_id = log_file_model.kb_id
        task = TaskModel(
            kb_id=kb_id,
            op_id=op_id,
            task_name=f"诊断日志文件夹中的故障事件 {log_file_model.file_path}",
            task_type=TaskTypeEnum.KV_CACHE_LOG_EVENT_DIAGNOSIS_WORKER,
            status=TaskStatusEnum.PENDING,
        )
        await TaskManager.add_task(task)
        await LogFileManager.update_log_file(
            log_file_model.id, {"parse_status": TaskStatusEnum.PENDING.value}
        )
        await BaseWorker.report(task.id, "初始化任务", 0.0)
        return task.id

    @staticmethod
    async def reinit(task_id: str) -> bool:
        """重新初始化任务"""
        task = await TaskManager.get_task_by_task_id(task_id)
        if not task:
            return False
        # await LogParseResultManager.update_log_parse_results_existed_status_by_log_id(
        #     task.op_id, existed_status=0
        # )
        # await AnomalousEventManager.update_anomalous_events_existed_status_by_log_id(
        #     task.op_id, existed_status=0
        # )
        # await AnomalousEventChainManager.update_event_chains_existed_status_by_log_id(
        #     task.op_id, existed_status=0
        # )
        # await SrcDstAggregatedEventManager.update_aggregated_events_existed_status_by_log_id(
        #     task.op_id, existed_status=0
        # )
        # await TaskReportManager.update_task_reports_existed_status_by_task_id(
        #     task_id, status=TaskStatusEnum.PENDING
        # )
        # if task.retry_times > Config().get_config().task.task_retry_times:
        #     await LogFileManager.update_log_file(
        #         task.op_id, {"parse_status": TaskStatusEnum.FAILED.value}
        #     )
        #     logger.warning(
        #         f"任务 {task_id} 重试次数 {task.retry_times} 已超过最大重试次数 {Config().get_config().task.task_retry_times}"
        #     )
        #     return False
        # await LogFileManager.update_log_file(
        #     task.op_id, {"parse_status": TaskStatusEnum.PENDING.value}
        # )
        # await BaseWorker.report(task.id, "重新初始化任务", 0.0)
        # return True

    @staticmethod
    async def deinit(task_id: str) -> str:
        """析构任务"""
        return task_id

    @staticmethod
    async def remove_duplicates(lst):
        seen = set()
        result = []
        for item in lst:
            if item not in seen:
                seen.add(item)
                result.append(item)
        return result

    @staticmethod
    async def parse_log_failure_events(output_log_path: str, log_id: str) -> int:
        # 将output_log_path下，除了failure_trace.log以外的所有日志读到log_failure_event_table数据库中
        # 除了failure_trace.log以外，output_log_path目录下的日志都是以下模板："timestamp | level | filename | pod_name | pid:tid | trace_id | cluster_name | message"，  
        # 对应LogFailureEventModel数据结构中的相应字段。除了这些字段以外，log_id对应函数参数输入，log_file对应日志文件名，raw_text对应原始日志。
        # status_code的读取方式略微复杂。仅当log_file对应的日志文件名能够匹配parse_filepath_config()得到的字典中，键为ds-worker-access-log-file和
        # ds-client-access-log-file的值所表示的正则表达式，即为access log日志时，日志才有status_code字段。具体而言，status_code字段是message字段中以" | "分割的第一个字段
        # 将failure_trace.log中的故障模式字段添加到数据库中
        # 将output_log_path下的failure_trace.log中是解析到的所有故障日志。每行日志的格式为failure_mode | raw_text，即将failure_mode字段添加到raw_text对应行的数据库条目中。你应该需要在
        # LogFailureEventManager中加入一个update_failure_mode_by_raw_log函数来完成数据库更新的操作。
        try:
            from latency.database.managers.failure_mode_knowledge import FailureModeKnowledgeManager

            trace_id_set = set()
            trace_failure_id = dict()
            if not os.path.exists(output_log_path):
                logger.error(f"输出日志路径不存在: {output_log_path}")
                return 0
            
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
            
            if not trace_id_set:
                logger.info("failure_trace.log 中没有可落库的 trace_id")
                return 0

            log_file_model = await LogFileManager.get_log_file_by_log_file_id(log_id)
            config = await KVCacheLogEventDiagnosisWorker.parse_filepath_config(
                log_file_model.kb_id if log_file_model else None
            )
            failure_mode_cache = await FailureModeKnowledgeManager.get_all_failure_modes()
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
            batch_size = 10000
            total_log_failure_events = KVCacheLogEventDiagnosisWorker._count_log_failure_events(
                log_files,
                trace_id_set,
                worker_access_patterns,
                client_access_patterns,
            )
            
            print(f"开始日志落库，共{len(trace_id_set)}条故障trace，{total_log_failure_events}条日志事件")
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
                                
                                failure_mode = trace_failure_id.get(raw_line, [])
                                log_failure_event = {
                                    "id": str(uuid.uuid5(uuid.NAMESPACE_URL, raw_line)),
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
                                    await LogFailureEventManager.add_log_failure_event_raw(log_failure_events)
                                    total_inserted += len(log_failure_events)
                                    progress_msg = (
                                        f"日志事件落盘进度：{total_inserted}/{total_log_failure_events}"
                                    )
                                    logger.info(progress_msg)
                                    print(progress_msg)
                                    log_failure_events = []
                            
                            except Exception as e:
                                logger.warning(f"读取日志文件 {log_file_path} 行失败: {line}, 错误: {e}")
                                continue
                
                except Exception as e:
                    logger.warning(f"读取日志文件 {log_file_path} 失败: {e}")
                    continue
            
            if log_failure_events:
                await LogFailureEventManager.add_log_failure_event_raw(log_failure_events)
                total_inserted += len(log_failure_events)
                progress_msg = (
                    f"日志事件落盘进度：{total_inserted}/{total_log_failure_events}"
                )
                logger.info(progress_msg)
                print(progress_msg)

            trace_failure_events = list(trace_failure_events_map.values())
            if trace_failure_events:
                trace_store_start = time.perf_counter()
                await LogFailureEventManager.add_trace_failure_event_raw(trace_failure_events)
                logger.info(
                    "成功插入 %s 条trace故障事件，耗时 %.3fs",
                    len(trace_failure_events),
                    time.perf_counter() - trace_store_start,
                )

            return sum(1 for event in trace_failure_events if event["failure_mode"])
    
        except Exception as e:
            logger.error(f"parse_log_failure_events 执行失败: {e}")
        
        return 0

    @staticmethod
    def _count_log_failure_events(
        log_files: list[tuple[str, str]],
        trace_id_set: set[str],
        worker_access_patterns: list[str],
        client_access_patterns: list[str],
    ) -> int:
        total = 0
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

                with open(log_file_path, "r", encoding="utf-8") as f:
                    for line in f:
                        raw_line = line.strip()
                        if not raw_line:
                            continue

                        parts = raw_line.split("|")
                        if len(parts) < 7:
                            continue

                        trace_id = parts[5].strip() if len(parts) > 5 else ""
                        if not trace_id or trace_id not in trace_id_set:
                            continue

                        if is_access_log and len(parts) <= 7:
                            continue

                        total += 1
            except Exception as e:
                logger.warning(f"统计日志文件 {log_file_path} 失败: {e}")
                continue
        return total

    @staticmethod
    def _matches_any(filename: str, patterns: list[str]) -> bool:
        return any(fnmatch.fnmatch(filename, pattern) for pattern in patterns)

    @staticmethod
    def _merge_trace_failure_event(
        trace_failure_events_map: dict[str, dict],
        log_failure_event: dict,
        failure_mode_cache: dict,
    ) -> None:
        trace_id = log_failure_event["trace_id"]

        if trace_id not in trace_failure_events_map:
            failure_mode = log_failure_event["failure_mode"]
            leaf_mode = (
                KVCacheLogEventDiagnosisWorker._find_leaf_failure_mode(
                    failure_mode, failure_mode_cache
                )
                if failure_mode
                else ""
            )
            trace_failure_events_map[trace_id] = {
                "id": str(uuid.uuid5(uuid.NAMESPACE_URL, f"{log_failure_event['log_id']}:{trace_id}")),
                "log_id": log_failure_event["log_id"],
                "trace_id": trace_id,
                "pod_names": [log_failure_event["pod_name"]] if log_failure_event["pod_name"] else [],
                "host_names": [log_failure_event["host_name"]] if log_failure_event["host_name"] else [],
                "cluster_names": [log_failure_event["cluster_name"]] if log_failure_event["cluster_name"] else [],
                "timestamp": log_failure_event["timestamp"],
                "status_code": log_failure_event["status_code"] if log_failure_event["status_code"] else "",
                "failure_mode": leaf_mode,
            }
            return

        trace_failure_event = trace_failure_events_map[trace_id]

        pod_name = log_failure_event["pod_name"]
        host_name = log_failure_event["host_name"]
        cluster_name = log_failure_event["cluster_name"]
        timestamp = log_failure_event["timestamp"]
        status_code = log_failure_event["status_code"]
        failure_mode = log_failure_event["failure_mode"]

        if pod_name and pod_name not in trace_failure_event["pod_names"]:
            trace_failure_event["pod_names"].append(pod_name)

        if host_name and host_name not in trace_failure_event["host_names"]:
            trace_failure_event["host_names"].append(host_name)

        if cluster_name and cluster_name not in trace_failure_event["cluster_names"]:
            trace_failure_event["cluster_names"].append(cluster_name)

        if timestamp < trace_failure_event["timestamp"]:
            trace_failure_event["timestamp"] = timestamp

        if not trace_failure_event["status_code"] and status_code:
            trace_failure_event["status_code"] = status_code

        if trace_failure_event["status_code"] == "0" and status_code != "0":
            trace_failure_event["status_code"] = status_code

        if not failure_mode:
            return

        new_leaf_mode = KVCacheLogEventDiagnosisWorker._find_leaf_failure_mode(
            failure_mode, failure_mode_cache
        )
        if not new_leaf_mode:
            return

        if not trace_failure_event["failure_mode"]:
            trace_failure_event["failure_mode"] = new_leaf_mode
            return

        if KVCacheLogEventDiagnosisWorker._is_child_failure_mode(
            trace_failure_event["failure_mode"],
            new_leaf_mode,
            failure_mode_cache,
        ):
            trace_failure_event["failure_mode"] = new_leaf_mode
    
    @staticmethod
    async def parse_filepath_config(kb_id: str | None = None):
        try:
            if kb_id:
                from latency.database.managers.diagnosis_config import DiagnosisConfigManager

                config = await DiagnosisConfigManager.get_or_create(kb_id)
                args = config.log_filename_pattern.model_dump()
            else:
                args = Config().get_config().log_filename_pattern.model_dump()
            logger.info("读取日志文件名参数: %s", args)
            return args
        except Exception as e:
            logger.error("读取统一配置文件失败: %s", e)
            return {}
    
    @staticmethod
    async def run_diagnosis_tool(
        file_path: str, task: TaskModel, random_str: str, kb_id: str | None = None
    ) -> bool:
        config = await KVCacheLogEventDiagnosisWorker.parse_filepath_config(kb_id)
        # 获取当前机器时间
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # 构建命令行参数
        witty_install_path = os.getenv("WITTY_INSTALL_PATH", WITTY_INSTALL_PATH_DEFAULT)
        diag_tool_path = os.path.join(witty_install_path, "witty-ub-diag-tool")
        
        cmd_args = [
            diag_tool_path,
            "--ds-log-path", file_path,
            "--start-time", "2020-01-01 00:00:00",
            "--end-time", current_time,
            "--random-str", random_str,
        ]
        
        # 添加配置文件中的参数
        for key, patterns in config.items():
            plain_patterns = [
                pattern for pattern in patterns
                if not pattern.lower().endswith(".gz")
            ]
            if plain_patterns:
                cmd_args.extend([
                    f"--{key.replace('_', '-')}",
                    ",".join(plain_patterns),
                ])
        
        for arg in cmd_args:
            print(arg)
        logger.info(f"运行定界工具: {' '.join(cmd_args)}")
        await BaseWorker.report(task.id, "运行定界工具", 20.0)
        
        # 运行定界工具
        try:
            result = subprocess.run(
                cmd_args,
                capture_output=True,
                text=True,
                timeout=3600  # 1小时超时
            )
            
            if result.returncode != 0:
                logger.error(f"定界工具运行失败，返回码: {result.returncode}")
                logger.error(f"错误输出: {result.stderr}")
                await TaskManager.update_task(
                    task.id, {"status": TaskStatusEnum.FAILED_PENDING_REMOVE.value}
                )
                return False
            
            logger.info(f"定界工具运行成功: {result.stdout}")
            await BaseWorker.report(task.id, "定界工具运行完成", 40.0)
            
        except subprocess.TimeoutExpired:
            logger.error("定界工具运行超时")
            await TaskManager.update_task(
                task.id, {"status": TaskStatusEnum.FAILED_PENDING_REMOVE.value}
            )
            return False
        except Exception as e:
            logger.error(f"运行定界工具时发生错误: {e}")
            await TaskManager.update_task(
                task.id, {"status": TaskStatusEnum.FAILED_PENDING_REMOVE.value}
            )
            return False
        return True

    @staticmethod
    async def parse_trace_failure_events(trace_id_set: set[str], log_id: str) -> int:
        # 从log_failure_event_table中读取trace_id的所有log_failure_events，解析出trace_failure_events
        # 首先，通过list_log_failure_events读取所有满足条件的log到列表log_failure_events_list，ListLogFailureEventResultRequest的参数中，log_id为log_id，trace_ids为trace_id_set
        # 然后，构建一个字典trace_failure_events_map，字典的键为trace_id，值为TraceFailureEventModel类型的对象
        # 依次遍历log_failure_events_list中的元素log_failure_event，用于更新trace_failure_events，更新规则如下：
        # 若log_failure_events_map中没有trace_id的键，创建一个新的TraceFailureEventModel，其log_id为输入log_id，trace_id、timestamp、status_code、failure_domain、failure_mode与log_failure_event相同，其pod_names、host_names、cluster_names中各有一个元素为log_failure_event的pod_name、host_name、cluster_name
        # 若log_failure_events_map中已有trace_id的键，记查询到的值为trace_failure_event，遵循以下规则使用log_failure_event更新trace_failure_event：
        # 1.若现有trace_failure_event的pod_names/host_names不含log_failure_event的pod_name/host_name，将log_failure_event的pod_name/host_name加入trace_failure_event的pod_names/host_names；
        # 2.将trace_failure_event的timestamp值更新为现有timestamp和log_failure_event的timestamp中更早的值
        # 3.若当前trace_failure_event的status_code为None且log_failure_event的status_code为非None，将trace_failure_event的status_code覆盖为log_failure_event的status_code；
        # 4.若当前trace_failure_event和log_failure_event的failure_mode都为非空，则需要判断log_failure_event的故障模式failure_mode是否为trace_failure_event的故障模式的子故障模式。若为子故障模式，则需要更新trace_failure_event的failure_mode为log_failure_event的failure_mode。判断逻辑如下：
        # 使用FailureModeKnowledgeManager的get_failure_mode_by_id可以通过failure_mode查询故障模式信息，其中children_failure_mode_ids字段是该故障的子故障ID列表，由","分割。如果子故障没有查到，还需要继续该过程进行迭代查询，直至children_failure_mode_ids字段为None。任意下级故障都可认为是上级故障的子故障。
        # 最后，调用add_trace_failure_event，向trace_failure_event_table数据库中加入解析到的trace_failure_events
        try:
            from latency.schemas.request import ListLogFailureEventResultRequest
            from latency.database.managers.failure_mode_knowledge import FailureModeKnowledgeManager
            
            failure_mode_cache = await FailureModeKnowledgeManager.get_all_failure_modes()
            
            req = ListLogFailureEventResultRequest(
                log_id=log_id
            )
            
            total, log_failure_events_list = await LogFailureEventManager.list_log_failure_events(req)
            
            trace_failure_events_map: dict[str, TraceFailureEventModel] = {}
            
            for log_failure_event in log_failure_events_list:
                trace_id = log_failure_event.trace_id
                
                if trace_id not in trace_failure_events_map:
                    leaf_mode = KVCacheLogEventDiagnosisWorker._find_leaf_failure_mode(
                        log_failure_event.failure_mode, failure_mode_cache
                    ) if log_failure_event.failure_mode else ""
                    
                    trace_failure_event = TraceFailureEventModel(
                        log_id=log_id,
                        trace_id=trace_id,
                        pod_names=[log_failure_event.pod_name] if log_failure_event.pod_name else [],
                        host_names=[log_failure_event.host_name] if log_failure_event.host_name else [],
                        cluster_names=[log_failure_event.cluster_name] if log_failure_event.cluster_name else [],
                        timestamp=log_failure_event.timestamp,
                        status_code=log_failure_event.status_code if log_failure_event.status_code else "",
                        failure_mode=leaf_mode
                    )
                    trace_failure_events_map[trace_id] = trace_failure_event
                else:
                    trace_failure_event = trace_failure_events_map[trace_id]
                    
                    if log_failure_event.pod_name and log_failure_event.pod_name not in trace_failure_event.pod_names:
                        trace_failure_event.pod_names.append(log_failure_event.pod_name)
                    
                    if log_failure_event.host_name and log_failure_event.host_name not in trace_failure_event.host_names:
                        trace_failure_event.host_names.append(log_failure_event.host_name)
                    
                    if log_failure_event.timestamp < trace_failure_event.timestamp:
                        trace_failure_event.timestamp = log_failure_event.timestamp
                    
                    if not trace_failure_event.status_code and log_failure_event.status_code:
                        trace_failure_event.status_code = log_failure_event.status_code
                    
                    if trace_failure_event.status_code == "0" and log_failure_event.status_code != "0":
                        trace_failure_event.status_code = log_failure_event.status_code
                    
                    if log_failure_event.failure_mode:
                        new_leaf_mode = KVCacheLogEventDiagnosisWorker._find_leaf_failure_mode(
                            log_failure_event.failure_mode, failure_mode_cache
                        )
                        
                        if new_leaf_mode:
                            if trace_failure_event.failure_mode:
                                is_child = KVCacheLogEventDiagnosisWorker._is_child_failure_mode(
                                    trace_failure_event.failure_mode, 
                                    new_leaf_mode,
                                    failure_mode_cache
                                )
                                if is_child:
                                    trace_failure_event.failure_mode = new_leaf_mode
                            else:
                                trace_failure_event.failure_mode = new_leaf_mode
            
            trace_failure_events = list(trace_failure_events_map.values())
            
            if trace_failure_events:
                await LogFailureEventManager.add_trace_failure_event(trace_failure_events)
                logger.info(f"成功插入 {len(trace_failure_events)} 条trace故障事件")
            
            trace_failure_event_cnt = 0
            for trace_id in trace_failure_events_map.keys():
                if trace_failure_events_map[trace_id].failure_mode:
                    trace_failure_event_cnt += 1
            return trace_failure_event_cnt
            
        except Exception as e:
            logger.error(f"parse_trace_failure_events 执行失败: {e}")
            return 0
    
    @staticmethod
    def _is_child_failure_mode(parent_mode: str, child_mode: str, failure_mode_cache: dict) -> bool:
        if not parent_mode or not child_mode:
            return False
        visited = set()
        to_check = [parent_mode]
        while to_check:
            current_mode = to_check.pop(0)
            if current_mode in visited:
                continue
            visited.add(current_mode)
            if current_mode == child_mode:
                return True  
            failure_mode_info = failure_mode_cache.get(current_mode)
            if failure_mode_info and failure_mode_info.children_failure_mode_ids:
                children_ids = [cid.strip() for cid in failure_mode_info.children_failure_mode_ids.split(',') if cid.strip()]
                to_check.extend(children_ids)
        return False
    
    @staticmethod
    def _find_leaf_failure_mode(failure_modes: list[str], failure_mode_cache: dict) -> str:
        if not failure_modes:
            return ""
        
        failure_modes_set = set(failure_modes)
        
        for mode in failure_modes:
            failure_mode_info = failure_mode_cache.get(mode)
            
            if not failure_mode_info or not failure_mode_info.children_failure_mode_ids:
                return mode
            
            children_ids = [cid.strip() for cid in failure_mode_info.children_failure_mode_ids.split(',') if cid.strip()]
            
            has_child_in_list = any(child_id in failure_modes_set for child_id in children_ids)
            
            if not has_child_in_list:
                return mode
        
        return failure_modes[0]

    @staticmethod
    def split_unmatched_log_files(
        log_dir: str, filename_patterns: dict[str, list[str]]
    ) -> dict[str, tuple[int, int]]:
        """按日志字段数拆分不符合配置文件名规则的文本日志。

        每行包含 7 个 ``" | "`` 时写入 ``*_runtime.log``，包含 12 或
        13 个时写入 ``*_access.log``，其他行忽略。拆分成功后删除原文件。
        """
        patterns = [
            pattern
            for pattern_list in filename_patterns.values()
            for pattern in pattern_list
        ]
        split_stats: dict[str, tuple[int, int]] = {}

        for root, _, files in os.walk(log_dir):
            for filename in files:
                if any(fnmatch.fnmatch(filename, pattern) for pattern in patterns):
                    continue
                if not filename.lower().endswith(".log"):
                    continue
                if filename.endswith(("_runtime.log", "_access.log")):
                    continue

                source_path = os.path.join(root, filename)
                stem, _ = os.path.splitext(filename)
                runtime_path = os.path.join(root, f"{stem}_runtime.log")
                access_path = os.path.join(root, f"{stem}_access.log")
                runtime_count = 0
                access_count = 0

                try:
                    with open(
                        source_path, "r", encoding="utf-8", errors="ignore"
                    ) as source, open(
                        runtime_path, "w", encoding="utf-8"
                    ) as runtime_file, open(
                        access_path, "w", encoding="utf-8"
                    ) as access_file:
                        for line in source:
                            delimiter_count = line.count(" | ")
                            if delimiter_count == 7:
                                runtime_file.write(line)
                                runtime_count += 1
                            elif delimiter_count in (12, 13):
                                access_file.write(line)
                                access_count += 1
                except OSError as e:
                    logger.error("拆分日志 %s 失败: %s", source_path, e)
                    continue

                try:
                    os.remove(source_path)
                except OSError as e:
                    logger.error("删除已拆分日志 %s 失败: %s", source_path, e)
                    continue

                split_stats[source_path] = (
                    runtime_count,
                    access_count,
                )
                logger.info(
                    "拆分未匹配日志 %s: runtime=%d, access=%d",
                    source_path,
                    runtime_count,
                    access_count,
                )

        return split_stats

    @staticmethod
    async def extract_log_file(
        file_path: str,
        random_str: str,
        filename_patterns: dict[str, list[str]] | None = None,
    ) -> str:
        """解压所有文件到目录下"""
        # TODO: 首先，递归扫描目录中所有文件，如果文件没有.gz结尾的，即没有压缩文件，则直接返回file_path
        # 如果有，则extracted_log_file_path=os.path.join(witty_dir, "log_extracted_" + random_str)
        # 然后，保持目录结构不变，将所有.gz结尾的压缩包解压到相应目录下，其他文件按原样复制到相应目录下     
        try:
            import rarfile
            HAS_RARFILE = True
        except ImportError:
            HAS_RARFILE = False
            logger.warning("rarfile 模块未安装，.rar 文件将不会被解压")
        
        has_compressed_file = False
        compressed_extensions = ('.gz', '.zip', '.rar')
        
        for root, dirs, files in os.walk(file_path):
            for file in files:
                if file.lower().endswith(compressed_extensions):
                    has_compressed_file = True
                    break
            if has_compressed_file:
                break
        
        if not has_compressed_file:
            return file_path
        
        extracted_log_file_path = os.path.join(witty_dir, "log_extracted_" + random_str)
        
        os.makedirs(extracted_log_file_path, exist_ok=True)
        
        for root, dirs, files in os.walk(file_path):
            relative_path = os.path.relpath(root, file_path)
            target_dir = os.path.join(extracted_log_file_path, relative_path)
            
            if not os.path.exists(target_dir):
                os.makedirs(target_dir, exist_ok=True)
            
            for file in files:
                source_file = os.path.join(root, file)
                file_lower = file.lower()
                
                if file_lower.endswith('.gz'):
                    target_file = os.path.join(target_dir, file[:-3])
                    try:
                        with gzip.open(source_file, 'rb') as f_in:
                            with open(target_file, 'wb') as f_out:
                                shutil.copyfileobj(f_in, f_out)
                    except Exception as e:
                        logger.error(f"解压 .gz 文件 {source_file} 失败: {e}")
                        continue
                
                elif file_lower.endswith('.zip'):
                    try:
                        with zipfile.ZipFile(source_file, 'r') as zip_ref:
                            zip_ref.extractall(target_dir)
                    except Exception as e:
                        logger.error(f"解压 .zip 文件 {source_file} 失败: {e}")
                        continue
                
                elif file_lower.endswith('.rar'):
                    if not HAS_RARFILE:
                        logger.warning(f"跳过 .rar 文件 {source_file}：rarfile 模块未安装")
                        continue
                    try:
                        with rarfile.RarFile(source_file, 'r') as rar_ref:
                            rar_ref.extractall(target_dir)
                    except Exception as e:
                        logger.error(f"解压 .rar 文件 {source_file} 失败: {e}")
                        continue
                
                else:
                    target_file = os.path.join(target_dir, file)
                    try:
                        shutil.copy2(source_file, target_file)
                    except Exception as e:
                        logger.error(f"复制文件 {source_file} 失败: {e}")
                        continue

        if filename_patterns is not None:
            KVCacheLogEventDiagnosisWorker.split_unmatched_log_files(
                extracted_log_file_path, filename_patterns
            )

        return extracted_log_file_path
        
    @staticmethod
    async def run(task_id: str) -> bool:
        """运行任务"""
        try:
            task = await TaskManager.get_task_by_task_id(task_id)
            if not task:
                logger.error(f"任务 {task_id} 不存在")
                return False
            
            await TaskManager.update_task(
                task_id, {"status": TaskStatusEnum.RUNNING.value}
            )
            await BaseWorker.report(task.id, "运行任务", 5.0)
            
            log_file = await LogFileManager.get_log_file_by_log_file_id(task.op_id)
            if not log_file:
                logger.error(f"LogFile {task.op_id} 不存在")
                await TaskManager.update_task(
                    task_id, {"status": TaskStatusEnum.FAILED_PENDING_REMOVE.value}
                )
                return False
            
            # TODO: 运行时启用真实业务逻辑
            random_str = log_file.id[:8]
            filename_patterns = (
                Config()
                .get_default_diagnosis_config()
                .log_filename_pattern.model_dump()
            )
            extracted_log_file_path = await KVCacheLogEventDiagnosisWorker.extract_log_file(
                log_file.file_path,
                random_str,
                filename_patterns=filename_patterns,
            )
            
            # TODO: 运行时启用真实业务逻辑
            print("故障定界工具开始运行")
            result = await KVCacheLogEventDiagnosisWorker.run_diagnosis_tool(
                file_path=extracted_log_file_path,
                task=task,
                random_str=random_str,
                kb_id=log_file.kb_id,
            )
            try:
              if extracted_log_file_path == os.path.join(witty_dir, "log_extracted_" + random_str):
                  shutil.rmtree(extracted_log_file_path)
            except Exception as e:
                logger.exception(f"删除文件夹 {extracted_log_file_path} 失败: {e}")
            if not result:
                return False
            print("故障定界工具运行完成")
            output_log_path = os.path.join(witty_dir, "log_" + random_str)
            trace_failure_event_cnt = await KVCacheLogEventDiagnosisWorker.parse_log_failure_events(output_log_path=output_log_path, log_id=log_file.id)
            await BaseWorker.report(task.id, "故障事件和Trace解析完成", 80.0)
            print("故障事件和Trace解析完成")
            await LogFileManager.update_log_file(
                task.op_id, {"trace_failure_event_cnt": trace_failure_event_cnt}
            )
            # 以下是自带内容
            await TaskManager.update_task(
                task_id, {"status": TaskStatusEnum.SUCCESSFUL_PENDING_REMOVE.value}
            )
            await LogFileManager.update_log_file(
                task.op_id, {"parse_status": TaskStatusEnum.SUCCESSFUL.value}
            )
            await BaseWorker.report(task.id, "任务成功", 100.0)
            print("故障定界任务成功")
            return True
        except Exception as e:
            logger.exception(f"任务 {task_id} 执行失败: {e}")
            await TaskManager.update_task(
                task_id, {"status": TaskStatusEnum.FAILED_PENDING_REMOVE.value}
            )
            return False

    @staticmethod
    async def stop(task_id: str) -> str | None:
        """停止任务"""
        task = await TaskManager.get_task_by_task_id(task_id)
        # if task.status in [TaskStatusEnum.PENDING, TaskStatusEnum.RUNNING]:
        #     await LogParseResultManager.update_log_parse_results_existed_status_by_log_id(
        #         task.op_id, existed_status=0
        #     )
        #     await SrcDstAggregatedEventManager.update_aggregated_events_existed_status_by_log_id(
        #         task.op_id, existed_status=0
        #     )
        #     await TaskReportManager.update_task_reports_existed_status_by_task_id(
        #         task_id, existed_status=0
        #     )
        #     await TaskManager.update_task(
        #         task_id, {"status": TaskStatusEnum.CANCELLED.value}
        #     )
            # return task_id
        return None

    @staticmethod
    async def delete(task_id: str) -> str:
        """删除任务"""
        return task_id
    
