import asyncio
import fnmatch
import logging
import os
import re
import uuid
import subprocess
import time
from latency.schemas.log_failure_event import TraceFailureEventModel
from latency.ENUM.task import TaskStatusEnum, TaskTypeEnum
from latency.common.ds_log_io import glob_paths, open_log
from latency.config.config import Config
from latency.database.managers.log_parse_result import LogParseResultPGManager
from latency.database.managers.task import TaskPGManager
from latency.database.managers.task_report import TaskReportPGManager
from latency.database.managers.log_file import LogFilePGManager
from latency.database.managers.log_knowledge import LogKnowledgePGManager
from latency.database.managers.log_failure_event import LogFailureEventPGManager
from latency.database.managers.diagnosis_config import DiagnosisConfigPGManager
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
        log_file_model = await LogFilePGManager.get_log_file_by_log_file_id(op_id)
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
        await TaskPGManager.add_task(task)
        await LogFilePGManager.update_log_file(
            log_file_model.id, {"parse_status": TaskStatusEnum.PENDING.value}
        )
        await BaseWorker.report(task.id, "初始化任务", 0.0)
        return task.id

    @staticmethod
    async def reinit(task_id: str) -> bool:
        """重新初始化任务"""
        task = await TaskPGManager.get_task_by_task_id(task_id)
        if not task:
            return False
        if task.retry_times >= Config().get_config().task.task_retry_times:
            await LogFilePGManager.update_log_file(
                task.op_id, {"parse_status": TaskStatusEnum.FAILED.value}
            )
            logger.warning(
                "任务 %s 重试次数 %d 已超过最大重试次数 %d",
                task_id, task.retry_times, Config().get_config().task.task_retry_times,
            )
            return False
        await BaseWorker.report(task.id, "重新初始化任务", 0.0)
        return True

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
    def _extract_src_dst_ip(raw_text: str):
        import re
        
        ip_pattern = r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}'
        
        src_ip = ""
        dst_ip = ""
        
        # 模式1: src=IP, dst=IP
        src_match = re.search(r'src=(' + ip_pattern + ')', raw_text, re.IGNORECASE)
        dst_match = re.search(r'dst=(' + ip_pattern + ')', raw_text, re.IGNORECASE)

        if src_match:
            src_ip = src_match.group(1)
        if dst_match:
            dst_ip = dst_match.group(1)
        
        # 模式2: src address:IP...target address:IP
        if not src_ip:
            src_match = re.search(r'src address:(' + ip_pattern + ')', raw_text, re.IGNORECASE)
            if src_match:
                src_ip = src_match.group(1)
        
        if not dst_ip:
            dst_match = re.search(r'target address:(' + ip_pattern + ')', raw_text, re.IGNORECASE)
            if dst_match:
                dst_ip = dst_match.group(1)
        
        # 模式3: srcAddress = IP...targetAddress = IP
        if not src_ip:
            src_match = re.search(r'srcAddress\s*=\s*(' + ip_pattern + ')', raw_text, re.IGNORECASE)
            if src_match:
                src_ip = src_match.group(1)
        
        if not dst_ip:
            dst_match = re.search(r'targetAddress\s*=\s*(' + ip_pattern + ')', raw_text, re.IGNORECASE)
            if dst_match:
                dst_ip = dst_match.group(1)
        
        if not src_ip or not dst_ip:
            return "", ""
        
        return src_ip, dst_ip

    @staticmethod
    def _extract_operation(raw_text: str) -> str:
        parts = raw_text.split('|')
        if len(parts) < 9:
            return ""

        handle = parts[8].strip()
        from latency.parse.base_parser import SDK_GET_OPS, SDK_SET_OPS, WORKER_GET_OPS, WORKER_SET_OPS
        from latency.ENUM.ds_log import OpType

        try:
            op_type = OpType(handle)
            if op_type in SDK_GET_OPS or op_type in WORKER_GET_OPS:
                return "GET"
            elif op_type in SDK_SET_OPS or op_type in WORKER_SET_OPS:
                return "SET"
        except ValueError:
            pass

        return ""

    @staticmethod
    def _merge_trace_failure_event(
        trace_failure_events_map: dict[str, dict],
        log_failure_event: dict,
        failure_mode_cache: dict,
    ) -> None:
        trace_id = log_failure_event["trace_id"]

        raw_text = log_failure_event.get("raw_text", "")
        src_ip, dst_ip = KVCacheLogEventDiagnosisWorker._extract_src_dst_ip(raw_text)
        operation = KVCacheLogEventDiagnosisWorker._extract_operation(raw_text)

        # 单条日志可能命中多个故障模式；父子同时命中时只保留更深的子节点。
        leaf_modes = KVCacheLogEventDiagnosisWorker._leaf_failure_modes(
            log_failure_event.get("failure_mode") or [], failure_mode_cache
        )

        if trace_id not in trace_failure_events_map:
            trace_failure_events_map[trace_id] = {
                "id": str(uuid.uuid5(uuid.NAMESPACE_URL, f"{log_failure_event['log_id']}:{trace_id}")),
                "log_id": log_failure_event["log_id"],
                "trace_id": trace_id,
                "pod_names": [log_failure_event["pod_name"]] if log_failure_event["pod_name"] else [],
                "src_ip": src_ip,
                "dst_ip": dst_ip,
                "host_names": [log_failure_event["host_name"]] if log_failure_event["host_name"] else [],
                "cluster_names": [log_failure_event["cluster_name"]] if log_failure_event["cluster_name"] else [],
                "timestamp": log_failure_event["timestamp"],
                "status_code": KVCacheLogEventDiagnosisWorker._failure_mode_error_codes(
                    leaf_modes, failure_mode_cache
                ),
                "failure_mode": list(leaf_modes),
                "operation": operation,
            }
            return

        trace_failure_event = trace_failure_events_map[trace_id]

        pod_name = log_failure_event["pod_name"]
        host_name = log_failure_event["host_name"]
        cluster_name = log_failure_event["cluster_name"]
        timestamp = log_failure_event["timestamp"]

        if pod_name and pod_name not in trace_failure_event["pod_names"]:
            trace_failure_event["pod_names"].append(pod_name)

        if host_name and host_name not in trace_failure_event["host_names"]:
            trace_failure_event["host_names"].append(host_name)

        if cluster_name and cluster_name not in trace_failure_event["cluster_names"]:
            trace_failure_event["cluster_names"].append(cluster_name)

        if timestamp < trace_failure_event["timestamp"]:
            trace_failure_event["timestamp"] = timestamp

        if src_ip:
            trace_failure_event["src_ip"] = src_ip
        if dst_ip:
            trace_failure_event["dst_ip"] = dst_ip

        if operation and not trace_failure_event.get("operation"):
            trace_failure_event["operation"] = operation

        # trace 汇聚其涉及日志命中的全部故障模式（保序去重）。
        for mode in leaf_modes:
            if mode not in trace_failure_event["failure_mode"]:
                trace_failure_event["failure_mode"].append(mode)

        trace_failure_event["failure_mode"] = (
            KVCacheLogEventDiagnosisWorker._leaf_failure_modes(
                trace_failure_event["failure_mode"], failure_mode_cache
            )
        )
        trace_failure_event["status_code"] = (
            KVCacheLogEventDiagnosisWorker._failure_mode_error_codes(
                trace_failure_event["failure_mode"], failure_mode_cache
            )
        )
    
    @staticmethod
    async def parse_filepath_config(kb_id: str | None = None):
        try:
            if kb_id:
                config = await DiagnosisConfigPGManager.get_or_create(kb_id)
                args = config.log_filename_pattern.model_dump()
            else:
                args = Config().get_config().log_filename_pattern.model_dump()
            logger.info("读取日志文件名参数: %s", args)
            return args
        except Exception as e:
            logger.warning("KB/global config unavailable (%s), using built-in defaults", e)
            return {
                "ds_client_access_log_file": ["ds_client_access*.log", "*_access.log", "*_split_access.log"],
                "ds_client_info_log_file": ["ds_client*.INFO.log", "*_runtime.log", "*_split_runtime.log"],
                "ds_worker_access_log_file": ["access.log", "access*.log", "*_access.log", "*_split_access.log"],
                "ds_worker_info_log_file": ["datasystem_worker.INFO*.log", "kvcache.INFO*.log", "*_runtime.log", "*_split_runtime.log"],
                "resource_log_file": ["resource.log"],
            }
    
    @staticmethod
    async def run_diagnosis_tool(
        file_path: str, task: TaskModel, random_str: str, kb_id: str | None = None
    ) -> bool:
        config = await KVCacheLogEventDiagnosisWorker.parse_filepath_config(kb_id)
        if not config:
            logger.warning("KB config empty, falling back to global config")
            config = Config().get_config().log_filename_pattern.model_dump()

        # 构建命令行参数
        witty_install_path = os.getenv("WITTY_INSTALL_PATH", WITTY_INSTALL_PATH_DEFAULT)
        diag_tool_path = os.path.join(witty_install_path, "witty-ub-diag-tool")
        
        cmd_args = [
            diag_tool_path,
            "--ds-log-path", file_path,
            "--start-time", "2020-01-01 00:00:00",
            "--end-time", "2099-12-31 23:59:59",
            "--random-str", random_str,
        ]
        
        # 添加配置文件中的参数
        for key, patterns in config.items():
            if key == "brpc_log_file_patterns":
                continue
            if patterns:
                cmd_args.extend([
                    f"--{key.replace('_', '-')}",
                    ",".join(patterns),
                ])
        
        logger.debug("运行定界工具: %s", ' '.join(cmd_args))
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
                await TaskPGManager.update_task(
                    task.id, {"status": TaskStatusEnum.FAILED_PENDING_REMOVE.value}
                )
                return False

            combined_output = (result.stdout or "") + (result.stderr or "")
            if "[ERROR]" in combined_output:
                error_lines = [
                    line.strip()
                    for line in combined_output.splitlines()
                    if "[ERROR]" in line
                ]
                logger.error(f"定界工具输出包含错误标记，任务失败: {len(error_lines)} 条错误")
                for line in error_lines[:50]:
                    logger.error("定界工具错误输出: %s", line)
                await TaskPGManager.update_task(
                    task.id, {"status": TaskStatusEnum.FAILED_PENDING_REMOVE.value}
                )
                return False

            logger.info(f"定界工具运行成功: {result.stdout}")
            await BaseWorker.report(task.id, "定界工具运行完成", 40.0)
            
        except subprocess.TimeoutExpired:
            logger.error("定界工具运行超时")
            await TaskPGManager.update_task(
                task.id, {"status": TaskStatusEnum.FAILED_PENDING_REMOVE.value}
            )
            return False
        except Exception as e:
            logger.error(f"运行定界工具时发生错误: {e}")
            await TaskPGManager.update_task(
                task.id, {"status": TaskStatusEnum.FAILED_PENDING_REMOVE.value}
            )
            return False
        return True
    
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
    def _leaf_failure_modes(failure_modes: list[str], failure_mode_cache: dict) -> list[str]:
        """返回列表中没有更深层命中出现的模式（父子同时命中时只保留子节点），保序去重。"""
        result: list[str] = []
        candidates = [mode for mode in failure_modes if mode]
        candidate_set = set(candidates)
        for mode in candidates:
            has_descendant = any(
                other != mode
                and KVCacheLogEventDiagnosisWorker._is_child_failure_mode(
                    mode, other, failure_mode_cache
                )
                for other in candidate_set
            )
            if has_descendant:
                continue
            if mode not in result:
                result.append(mode)
        return result

    @staticmethod
    def _failure_mode_error_codes(
        failure_modes: list[str], failure_mode_cache: dict
    ) -> list[str]:
        """Return normalized codes for matched modes, preserving mode order."""
        result: list[str] = []
        for mode in failure_modes:
            failure_mode = failure_mode_cache.get(mode)
            raw_error_code = getattr(failure_mode, "error_code", None)
            error_code = KVCacheLogEventDiagnosisWorker._normalize_failure_mode_error_code(
                raw_error_code
            )
            if error_code and error_code not in result:
                result.append(error_code)
        return result

    @staticmethod
    def _normalize_failure_mode_error_code(raw_error_code) -> str:
        """Normalize ``K_NAME(1004)``/numeric codes and ignore no-code sentinels."""
        if raw_error_code is None:
            return ""
        error_code = str(raw_error_code).strip()
        if not error_code or error_code.upper() in {
            "NULL",
            "NULLPTR",
            "NONE",
            "N/A",
            "NA",
            "-",
        }:
            return ""
        if re.fullmatch(r"K_OK\(\s*\+?0+\s*\)", error_code, re.IGNORECASE):
            return "0"
        numeric_suffix = re.search(r"\(\s*([-+]?\d+)\s*\)\s*$", error_code)
        if numeric_suffix:
            numeric_code = numeric_suffix.group(1)
            return "" if int(numeric_code) == 0 else numeric_code
        if re.fullmatch(r"[-+]?\d+", error_code):
            return ""
        return error_code

    @staticmethod
    async def run(task_id: str, log_dir: str | None = None) -> bool:
        """运行任务"""
        import asyncio as _asyncio
        for attempt in range(5):
            try:
                task = await TaskPGManager.get_task_by_task_id(task_id)
                if task:
                    break
            except Exception:
                pass
            await _asyncio.sleep(1)
        else:
            logger.error(f"任务 {task_id} PGManager 初始化失败，重试耗尽")
            return False

        if not task:
            logger.error(f"任务 {task_id} 不存在")
            return False

        try:
            await TaskPGManager.update_task(
                task_id, {"status": TaskStatusEnum.RUNNING.value}
            )
            await BaseWorker.report(task.id, "运行任务", 5.0)

            log_file = await LogFilePGManager.get_log_file_by_log_file_id(task.op_id)
            if not log_file:
                logger.error(f"LogFile {task.op_id} 不存在")
                await TaskPGManager.update_task(
                    task_id, {"status": TaskStatusEnum.FAILED_PENDING_REMOVE.value}
                )
                return False

            random_str = log_file.id[:8]
            preprocessed_log_dir = log_dir or log_file.file_path

            logger.info("故障定界工具开始运行")
            result = await KVCacheLogEventDiagnosisWorker.run_diagnosis_tool(
                file_path=preprocessed_log_dir,
                task=task,
                random_str=random_str,
                kb_id=log_file.kb_id,
            )
            if not result:
                return False

            output_log_path = os.path.join(witty_dir, "log_" + random_str)
            if not os.path.isdir(output_log_path) or not os.listdir(output_log_path):
                logger.error(f"定界工具输出目录不存在或为空: {output_log_path}")
                await TaskPGManager.update_task(
                    task_id, {"status": TaskStatusEnum.FAILED_PENDING_REMOVE.value}
                )
                return False

            # 检查任务是否被取消
            task = await TaskPGManager.get_task_by_task_id(task_id)
            if not task or task.status == TaskStatusEnum.CANCELLED:
                logger.warning(f"任务 {task_id} 已被取消或不存在，停止执行")
                return False

            logger.info("故障定界工具运行完成")
            await BaseWorker.report(task.id, "故障定界完成，等待Trace上下文落库任务处理", 80.0)
            await LogFilePGManager.update_log_file(
                task.op_id, {"parse_status": TaskStatusEnum.SUCCESSFUL.value}
            )
            if log_file.kb_id:
                from sqlalchemy import text
                from latency.database.engine import PGManager
                async with PGManager.session() as session:
                    await session.execute(
                        text("UPDATE log_knowledge SET updated_at = NOW() WHERE id = :kb_id"),
                        {"kb_id": log_file.kb_id}
                    )
            await BaseWorker.report(task.id, "任务成功", 100.0)
            await TaskPGManager.update_task(
                task_id, {"status": TaskStatusEnum.SUCCESSFUL_PENDING_REMOVE.value}
            )
            logger.info("故障定界任务成功")
            return True
        except Exception as e:
            logger.exception(f"任务 {task_id} 执行失败: {e}")
            await TaskPGManager.update_task(
                task_id, {"status": TaskStatusEnum.FAILED_PENDING_REMOVE.value}
            )
            return False

    @staticmethod
    async def stop(task_id: str) -> str | None:
        """停止任务"""
        task = await TaskPGManager.get_task_by_task_id(task_id)
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
        #     await TaskPGManager.update_task(
        #         task_id, {"status": TaskStatusEnum.CANCELLED.value}
        #     )
            # return task_id
        return None

    @staticmethod
    async def delete(task_id: str) -> str:
        """删除任务"""
        return task_id
    
