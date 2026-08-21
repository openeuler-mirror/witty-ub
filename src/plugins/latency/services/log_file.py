import requests
import os
import aiofiles
import aiohttp
import logging
import re
import shutil
from pathlib import Path
from fastapi import UploadFile
from sqlalchemy import select
from latency.database.engine import PGManager
from latency.database.models import Task
from latency.database.managers.log_file import LogFilePGManager
from latency.database.managers.log_parse_result import LogParseResultPGManager
from latency.database.managers.task import TaskPGManager
from latency.database.managers.task_report import TaskReportPGManager
from latency.database.managers.anomalous_event import AnomalousEventPGManager
from latency.database.managers.anomalous_event_chain import AnomalousEventChainPGManager
from latency.database.managers.brpc_diagnosis import BrpcDiagnosisPGManager
from latency.database.managers.brpc_profiling_result import BrpcProfilingResultPGManager
from latency.database.managers.src_dst_aggregated_event import SrcDstAggregatedEventPGManager
from latency.database.managers.log_failure_event import LogFailureEventPGManager
from latency.schemas.log import LogFileModel
from latency.ENUM.general import FilePath
from latency.ENUM.general import SourceType
from latency.schemas.request import (
    ParseConfig,
    RunBrpcDiagnosisRequest,
    UpLoadLogFileConfig,
    UpLoadLogFilesRequest,
    UpdateLogFileRequest,
    ListLogFilesRequest,
)
from latency.schemas.response import (
    UploadLogFilesMsg,
    DeleteLogFilesMsg,
    UpdateLogFileMsg,
    RunOrStopLogParseMsg,
    RunBrpcDiagnosisMsg,
    ListLogFilesMsg,
    GetLogFileMsg,
)
from latency.ENUM.task import TaskTypeEnum, TaskStatusEnum
from latency.task.task_handler import TaskHandler
from latency.task.progress import parallel_overall_progress, task_progress
from latency.task.worker.base import BaseWorker
from latency.task.worker.brpc_log_diagnosis_worker import BrpcLogDiagnosisWorker
from latency.task.log_preprocessor import cleanup_preprocess_dir, WITTY_DIR_DEFAULT
from latency.common.zip_handler import ZipHandler
from latency.exceptions import (
    BadRequestBizException,
    ConflictBizException,
    NotFoundBizException,
)

logger = logging.getLogger(__name__)
witty_dir = os.getenv("WITTY_DIR", WITTY_DIR_DEFAULT)

_PROFILING_TIMESTAMP_RE = re.compile(r"^timeStamp:\s*\S")


def _is_profiling_log(file_path: str | Path) -> bool:
    """Read the first line and check if it matches the profiling timestamp format."""
    try:
        with open(file_path, "r", encoding="utf-8-sig", errors="ignore") as f:
            first_line = f.readline().strip()
    except (IOError, OSError):
        return False
    return bool(_PROFILING_TIMESTAMP_RE.match(first_line))


class LogFileService:
    @staticmethod
    def _is_task_successful(task) -> bool:
        return task and task.status in [
            TaskStatusEnum.SUCCESSFUL,
            TaskStatusEnum.SUCCESSFUL_PENDING_REMOVE,
        ]

    @staticmethod
    def _select_visible_task(parse_task, diagnosis_task, store_task=None):
        if not parse_task:
            return diagnosis_task or store_task
        if not diagnosis_task:
            return parse_task
        if parse_task.status in [
            TaskStatusEnum.FAILED,
            TaskStatusEnum.FAILED_PENDING_REMOVE,
            TaskStatusEnum.CANCELLED,
        ]:
            return parse_task
        if parse_task.status not in [
            TaskStatusEnum.SUCCESSFUL,
            TaskStatusEnum.SUCCESSFUL_PENDING_REMOVE,
        ]:
            return parse_task
        if diagnosis_task.status in [
            TaskStatusEnum.FAILED,
            TaskStatusEnum.FAILED_PENDING_REMOVE,
            TaskStatusEnum.CANCELLED,
        ]:
            return diagnosis_task
        if not LogFileService._is_task_successful(diagnosis_task):
            return diagnosis_task
        if store_task:
            return store_task
        return diagnosis_task

    @staticmethod
    def _select_brpc_visible_task(parse_task, diagnosis_task):
        """Select UI detail without letting one failed BRPC task hide active work."""
        tasks = [task for task in (parse_task, diagnosis_task) if task]
        for status in (TaskStatusEnum.RUNNING, TaskStatusEnum.PENDING):
            for task in tasks:
                if task.status == status:
                    return task
        for task in tasks:
            if task.status in {
                TaskStatusEnum.FAILED,
                TaskStatusEnum.FAILED_PENDING_REMOVE,
                TaskStatusEnum.CANCELLED,
            }:
                return task
        return diagnosis_task or parse_task

    @staticmethod
    async def _populate_brpc_counts(log_file_model, parse_task, diagnosis_task) -> None:
        """Populate profiling count and diagnosis hit count for a BRPC log file."""
        success_statuses = {
            TaskStatusEnum.SUCCESSFUL,
            TaskStatusEnum.SUCCESSFUL_PENDING_REMOVE,
        }
        if parse_task and parse_task.status in success_statuses:
            try:
                profiling_cnt = await BrpcProfilingResultPGManager.count_files_by_log_id(
                    log_file_model.id
                )
                log_file_model.anomaly_cnt = profiling_cnt
            except Exception as exc:
                logger.warning("failed to count BRPC profiling results: %s", exc)
        if diagnosis_task and diagnosis_task.status in success_statuses:
            try:
                async with PGManager.session() as session:
                    batch = await BrpcDiagnosisPGManager.get_batch_by_task_id(
                        session, diagnosis_task.id
                    )
                    if batch:
                        log_file_model.trace_failure_event_cnt = batch.hit_count
            except Exception as exc:
                logger.warning("failed to get BRPC diagnosis hit count: %s", exc)

    @staticmethod
    async def _delete_brpc_diagnosis_results(tasks) -> None:
        """Delete BRPC batches for the supplied tasks; batch deletion cascades hits."""
        brpc_task_ids = [
            task.id
            for task in tasks
            if task.task_type == TaskTypeEnum.BRPC_LOG_DIAGNOSIS_WORKER.value
        ]
        if not brpc_task_ids:
            return

        async with PGManager.session() as session:
            for task_id in brpc_task_ids:
                batch_id = await BrpcDiagnosisPGManager.delete_batch_by_task_id(
                    session,
                    task_id,
                )
                if batch_id:
                    logger.warning(
                        "已删除 BRPC 诊断 batch %s (task=%s)",
                        batch_id,
                        task_id,
                    )

    @staticmethod
    def get_upload_path(*paths: str) -> str:
        latency_dir = os.path.dirname(os.path.dirname(__file__))
        full_path = os.path.join(latency_dir, FilePath.FILE_UPLOAD_PATH.value, *paths)
        os.makedirs(os.path.dirname(full_path), exist_ok=True)
        return full_path

    @staticmethod
    async def get_readable_dir_size(folder_path: str) -> int:
        total = 0
        for root, _, files in os.walk(folder_path):
            for f in files:
                try:
                    total += os.path.getsize(os.path.join(root, f))
                except:
                    pass

        # 格式化
        return total

    @staticmethod
    async def upload_log_files(
        kb_id: str, req: UpLoadLogFilesRequest
    ) -> UploadLogFilesMsg:
        log_file_models = []
        log_file_task_types: dict[str, TaskTypeEnum] = {}
        for upload_log_file_config in req.upload_log_file_configs:
            log_type = (upload_log_file_config.log_type or "kv-cache").strip().lower()
            log_file_model = LogFileModel(kb_id=kb_id, name=upload_log_file_config.name, log_type=log_type)
            if upload_log_file_config.source_type == SourceType.LOCAL:
                source_path = upload_log_file_config.source
                source = os.path.abspath(source_path)
                if not os.path.exists(source):
                    raise BadRequestBizException(message=f"路径不存在: {source}")
                if os.path.isdir(source):
                    if not os.access(source, os.R_OK):
                        raise BadRequestBizException(message=f"目录不可读: {source}")
                    log_file_model.file_path = source
                    log_file_model.file_size = await LogFileService.get_readable_dir_size(source)
                elif os.path.isfile(source):
                    if not os.access(source, os.R_OK):
                        raise BadRequestBizException(message=f"文件不可读: {source}")
                    log_file_model.file_path = source
                    log_file_model.file_size = os.path.getsize(source)
                else:
                    raise BadRequestBizException(message=f"路径既不是文件也不是目录: {source}")
            elif upload_log_file_config.source_type == SourceType.REMOTE:
                # 请求远程URL获取日志文件内容，并保存到本地文件系统中
                try:
                    async with aiohttp.ClientSession() as session:
                        async with session.get(
                            upload_log_file_config.source
                        ) as response:
                            response.raise_for_status()
                            content = await response.read()
                    local_zip_file_path = LogFileService.get_upload_path(
                        log_file_model.id + ".zip"
                    )
                    async with aiofiles.open(local_zip_file_path, "wb") as f:
                        await f.write(content)
                except Exception as e:
                    logger.error(
                        f"下载远程日志文件失败，URL: {upload_log_file_config.source}, 错误信息: {str(e)}"
                    )
                    continue
                if not ZipHandler.is_zip_file(local_zip_file_path):
                    logger.error(
                        f"下载的远程日志文件不是有效的ZIP文件，URL: {upload_log_file_config.source}"
                    )
                    continue
                extracted_file_path = LogFileService.get_upload_path(
                    log_file_model.id, ""
                )
                try:
                    await ZipHandler.unzip_file(local_zip_file_path, extracted_file_path)
                    log_file_model.file_path = extracted_file_path
                    log_file_model.file_size = (
                        await LogFileService.get_readable_dir_size(extracted_file_path)
                    )
                except Exception as e:
                    logger.error(
                        f"解压远程日志文件失败，ZIP文件路径: {local_zip_file_path}, 错误信息: {str(e)}"
                    )
                if os.path.exists(local_zip_file_path):
                    try:
                        os.remove(local_zip_file_path)
                    except Exception as e:
                        logger.error(
                            f"删除临时ZIP文件失败，ZIP文件路径: {local_zip_file_path}, 错误信息: {str(e)}"
                        )
            elif upload_log_file_config.source_type == SourceType.UPLOAD:
                uploaded_file: UploadFile = upload_log_file_config.source
                local_zip_file_path = LogFileService.get_upload_path(
                    log_file_model.id + ".zip"
                )
                try:
                    async with aiofiles.open(local_zip_file_path, "wb") as f:
                        content = await uploaded_file.read()
                        await f.write(content)
                except Exception as e:
                    logger.error(
                        f"保存上传的日志文件失败，文件名: {uploaded_file.filename}, 错误信息: {str(e)}"
                    )
                    continue
                if not ZipHandler.is_zip_file(local_zip_file_path):
                    if log_type == "brpc":
                        # brpc 日志可能是纯文本文件，直接使用
                        log_file_model.file_path = local_zip_file_path
                        log_file_model.file_size = (
                            os.path.getsize(local_zip_file_path)
                            if os.path.exists(local_zip_file_path)
                            else 0
                        )
                    else:
                        logger.error(
                            f"上传的日志文件不是有效的ZIP文件，文件名: {uploaded_file.filename}"
                        )
                        continue
                else:
                    extracted_file_path = LogFileService.get_upload_path(
                        log_file_model.id, ""
                    )
                    try:
                        await ZipHandler.unzip_file(local_zip_file_path, extracted_file_path)
                        log_file_model.file_path = extracted_file_path
                        log_file_model.file_size = (
                            await LogFileService.get_readable_dir_size(extracted_file_path)
                        )
                    except Exception as e:
                        logger.error(
                            f"解压上传的日志文件失败，ZIP文件路径: {local_zip_file_path}, 错误信息: {str(e)}"
                        )
                    if os.path.exists(local_zip_file_path):
                        try:
                            os.remove(local_zip_file_path)
                        except Exception as e:
                            logger.error(
                                f"删除临时ZIP文件失败，ZIP文件路径: {local_zip_file_path}, 错误信息: {str(e)}"
                            )
            if log_type == "brpc":
                log_file_models.append(log_file_model)
                log_file_task_types[log_file_model.id] = (
                    TaskTypeEnum.BRPC_LOG_PARSE_WORKER
                )
                continue

            log_file_models.append(log_file_model)
            log_file_task_types[log_file_model.id] = (
                TaskTypeEnum.KV_CACHE_LOG_PARSE_WORKER
            )
        log_file_ids = await LogFilePGManager.add_log_files(log_file_models)

        for log_file_id in log_file_ids:
            task_type = log_file_task_types[log_file_id]

            if task_type == TaskTypeEnum.BRPC_LOG_PARSE_WORKER:
                await TaskHandler.init_task(
                    task_type=TaskTypeEnum.BRPC_LOG_PARSE_WORKER,
                    op_id=log_file_id,
                    parse_config=req.parse_config,
                )
                await TaskHandler.init_task(
                    task_type=TaskTypeEnum.BRPC_LOG_DIAGNOSIS_WORKER,
                    op_id=log_file_id,
                    parse_config=req.parse_config,
                )
            elif task_type == TaskTypeEnum.BRPC_LOG_DIAGNOSIS_WORKER:
                await TaskHandler.init_task(
                    task_type=TaskTypeEnum.BRPC_LOG_DIAGNOSIS_WORKER,
                    op_id=log_file_id,
                    parse_config=req.parse_config,
                )
            else:
                await TaskHandler.init_task(
                    task_type=TaskTypeEnum.KV_CACHE_LOG_PARSE_WORKER,
                    op_id=log_file_id,
                    parse_config=req.parse_config,
                )
                await TaskHandler.init_task(
                    task_type=TaskTypeEnum.KV_CACHE_LOG_EVENT_DIAGNOSIS_WORKER,
                    op_id=log_file_id,
                    parse_config=req.parse_config
                )
                await TaskHandler.init_task(
                    task_type=TaskTypeEnum.STORE_TRACE_CONTEXT_LOGS_WORKER,
                    op_id=log_file_id,
                    parse_config=req.parse_config,
                )
        return UploadLogFilesMsg(log_file_ids=log_file_ids)

    @staticmethod
    async def delete_log_file_by_log_file_id(log_file_id: str) -> DeleteLogFilesMsg:
        logger.warning(f"==================== 开始删除日志文件: {log_file_id} ====================")
        log_file_model = await LogFilePGManager.get_log_file_by_log_file_id(log_file_id)
        if not log_file_model:
            raise NotFoundBizException(resource="日志文件")
        
        # 直接查询该日志文件的所有任务（不分状态），参考删除资产库的实现
        stmt = select(Task).where(Task.op_id == log_file_id)
        async with PGManager.session() as session:
            result = await session.execute(stmt)
            tasks = result.scalars().all()
        
        logger.warning(f"找到 {len(tasks)} 个任务与日志文件 {log_file_id} 相关")
        for task in tasks:
            logger.warning(f"任务 {task.id} 状态: {task.status} 类型: {task.task_type}")
            if task.status in [TaskStatusEnum.PENDING.value, TaskStatusEnum.RUNNING.value]:
                logger.warning(f"正在停止任务 {task.id}")
                await BaseWorker.stop(task.id)
                logger.warning(f"已停止任务 {task.id}")

        # BRPC batch 必须在 task 之前删除；hit 由 batch 外键级联删除。
        await LogFileService._delete_brpc_diagnosis_results(tasks)
        
        # 删除日志文件（硬删除）
        await LogFilePGManager.delete_log_file_by_log_file_id(log_file_id)
        
        # 删除所有相关数据
        await LogParseResultPGManager.delete_log_parse_results_by_log_id(log_file_id)
        await AnomalousEventPGManager.delete_anomalous_events_by_log_id(log_file_id)
        await AnomalousEventChainPGManager.delete_event_chains_by_log_id(log_file_id)
        await SrcDstAggregatedEventPGManager.delete_aggregated_events_by_log_id(log_file_id)
        await LogFailureEventPGManager.delete_log_failure_events_by_log_id(log_file_id)
        await LogFailureEventPGManager.delete_trace_failure_events_by_log_id(log_file_id)
        await BrpcProfilingResultPGManager.delete_by_log_id(log_file_id)
        
        # 删除任务报告和任务
        task_ids = [t.id for t in tasks]
        if task_ids:
            await TaskReportPGManager.delete_task_reports_by_task_ids(task_ids)
            await TaskPGManager.delete_tasks_by_task_ids(task_ids)
        
        # 等待进程完全释放资源
        import asyncio
        await asyncio.sleep(2)
        
        # 清理临时文件
        preprocess_dir = cleanup_preprocess_dir(log_file_id)
        if preprocess_dir:
            logger.warning(f"已清理日志文件预处理目录: {preprocess_dir}")
        else:
            logger.warning(f"日志文件预处理目录不存在或清理失败: {log_file_id}")
        
        diagnosis_output_dir = os.path.join(witty_dir, "log_" + log_file_id[:8])
        if os.path.exists(diagnosis_output_dir):
            try:
                shutil.rmtree(diagnosis_output_dir)
                logger.warning(f"已清理诊断输出目录: {diagnosis_output_dir}")
            except OSError as e:
                logger.error("清理诊断输出目录 %s 失败: %s", diagnosis_output_dir, e)
        
        logger.warning(f"==================== 完成删除日志文件: {log_file_id} ====================")
        return DeleteLogFilesMsg(log_file_ids=[log_file_id])

    @staticmethod
    async def update_log_file(
        log_file_id: str, req: UpdateLogFileRequest
    ) -> UpdateLogFileMsg:
        log_file_model = await LogFilePGManager.get_log_file_by_log_file_id(log_file_id)
        if not log_file_model:
            raise NotFoundBizException(resource="日志文件")
        rowcount = await LogFilePGManager.update_log_file(
            log_file_id, req.model_dump(exclude_none=True)
        )
        if rowcount > 0:
            return UpdateLogFileMsg(log_file_id=log_file_id)
        return UpdateLogFileMsg(log_file_id=None)

    @staticmethod
    async def run_or_stop_log_parse_by_log_file_id(
        log_file_id: str, run: bool
    ) -> RunOrStopLogParseMsg:
        log_file_model = await LogFilePGManager.get_log_file_by_log_file_id(log_file_id)
        if not log_file_model:
            return RunOrStopLogParseMsg(task_id=None)
        if run:
            log_type = getattr(log_file_model, "log_type", "kv-cache") or "kv-cache"
            task_type = TaskTypeEnum.KV_CACHE_LOG_PARSE_WORKER
            if log_type == "brpc":
                current_task = await TaskPGManager.get_current_task_by_op_id(log_file_id)
                task_type = (
                    current_task.task_type
                    if current_task
                    and current_task.task_type
                    in {
                        TaskTypeEnum.BRPC_LOG_PARSE_WORKER,
                        TaskTypeEnum.BRPC_LOG_DIAGNOSIS_WORKER,
                    }
                    else TaskTypeEnum.BRPC_LOG_PARSE_WORKER
                )
            task_id = await TaskHandler.init_task(
                task_type=task_type,
                op_id=log_file_id,
            )
            return RunOrStopLogParseMsg(task_id=task_id)
        task = await TaskPGManager.get_current_task_by_op_id(log_file_id)
        if task and task.status in [TaskStatusEnum.PENDING, TaskStatusEnum.RUNNING]:
            await TaskHandler.stop_task(task.id)
            return RunOrStopLogParseMsg(task_id=task.id)
        else:
            return RunOrStopLogParseMsg(task_id=None)

    @staticmethod
    async def run_brpc_diagnosis_by_log_file_id(
        log_file_id: str,
        req: RunBrpcDiagnosisRequest,
    ) -> RunBrpcDiagnosisMsg:
        log_file_model = await LogFilePGManager.get_log_file_by_log_file_id(
            log_file_id
        )
        if not log_file_model:
            raise NotFoundBizException(resource="日志文件")

        current_task = await TaskPGManager.get_current_task_by_op_id(
            log_file_id,
            TaskTypeEnum.BRPC_LOG_DIAGNOSIS_WORKER,
        )
        if current_task and current_task.status in {
            TaskStatusEnum.PENDING,
            TaskStatusEnum.RUNNING,
            TaskStatusEnum.FAILED_PENDING_REMOVE,
        }:
            raise ConflictBizException(message="BRPC 诊断任务尚未结束")

        task_id = await TaskHandler.init_task(
            task_type=TaskTypeEnum.BRPC_LOG_DIAGNOSIS_WORKER,
            op_id=log_file_id,
            parse_config=ParseConfig(start_time=req.start_time),
        )
        if not task_id:
            raise BadRequestBizException(message="创建 BRPC 诊断任务失败")
        return RunBrpcDiagnosisMsg(task_id=task_id)

    @staticmethod
    async def list_log_files(kb_id: str, req: ListLogFilesRequest) -> ListLogFilesMsg:
        total, log_file_models = await LogFilePGManager.list_log_files(kb_id, req)
        log_file_model_ids = [log_file_model.id for log_file_model in log_file_models]
        parse_tasks = await TaskPGManager.list_current_tasks_by_op_ids(
            log_file_model_ids,
            TaskTypeEnum.KV_CACHE_LOG_PARSE_WORKER,
        )
        brpc_parse_tasks = await TaskPGManager.list_current_tasks_by_op_ids(
            log_file_model_ids,
            TaskTypeEnum.BRPC_LOG_PARSE_WORKER,
        )
        brpc_diagnosis_tasks = await TaskPGManager.list_current_tasks_by_op_ids(
            log_file_model_ids,
            TaskTypeEnum.BRPC_LOG_DIAGNOSIS_WORKER,
        )
        diagnosis_tasks = await TaskPGManager.list_current_tasks_by_op_ids(
            log_file_model_ids,
            TaskTypeEnum.KV_CACHE_LOG_EVENT_DIAGNOSIS_WORKER,
        )
        store_tasks = await TaskPGManager.list_current_tasks_by_op_ids(
            log_file_model_ids,
            TaskTypeEnum.STORE_TRACE_CONTEXT_LOGS_WORKER,
        )
        parse_task_dict = {task.op_id: task for task in parse_tasks}
        brpc_parse_task_dict = {task.op_id: task for task in brpc_parse_tasks}
        brpc_diagnosis_task_dict = {
            task.op_id: task for task in brpc_diagnosis_tasks
        }
        diagnosis_task_dict = {task.op_id: task for task in diagnosis_tasks}
        store_task_dict = {task.op_id: task for task in store_tasks}
        task_op_ids = (
            set(parse_task_dict)
            | set(brpc_parse_task_dict)
            | set(brpc_diagnosis_task_dict)
            | set(diagnosis_task_dict)
            | set(store_task_dict)
        )
        fallback_op_ids = [
            log_file_model_id
            for log_file_model_id in log_file_model_ids
            if log_file_model_id not in task_op_ids
        ]
        fallback_task_dict = {}
        if fallback_op_ids:
            fallback_task_dict = {
                task.op_id: task
                for task in await TaskPGManager.list_current_tasks_by_op_ids(fallback_op_ids)
            }
        task_dict = {}
        for log_file_model in log_file_models:
            log_file_model_id = log_file_model.id
            if log_file_model.log_type == "brpc":
                visible_task = LogFileService._select_brpc_visible_task(
                    brpc_parse_task_dict.get(log_file_model_id),
                    brpc_diagnosis_task_dict.get(log_file_model_id),
                )
            else:
                visible_task = LogFileService._select_visible_task(
                    parse_task_dict.get(log_file_model_id),
                    diagnosis_task_dict.get(log_file_model_id),
                    store_task_dict.get(log_file_model_id),
                )
            task_dict[log_file_model_id] = (
                visible_task or fallback_task_dict.get(log_file_model_id)
            )
        # 收集所有类型任务的ID，一次性查询reports
        all_type_task_ids = [
            task.id
            for task in (
                list(parse_task_dict.values())
                + list(brpc_parse_task_dict.values())
                + list(brpc_diagnosis_task_dict.values())
                + list(diagnosis_task_dict.values())
                + list(store_task_dict.values())
            )
            if task
        ]
        all_type_task_reports = await TaskReportPGManager.list_task_reports_by_task_ids(all_type_task_ids)
        # 按 task_id 分组
        type_task_report_dict = {}
        for task_report in all_type_task_reports:
            if task_report.task_id not in type_task_report_dict:
                type_task_report_dict[task_report.task_id] = []
            type_task_report_dict[task_report.task_id].append(task_report)
        # 收集可见任务的ID，查询可见任务的reports
        visible_task_ids = [task.id for task in task_dict.values() if task]
        visible_task_reports = await TaskReportPGManager.list_task_reports_by_task_ids(visible_task_ids)
        visible_task_report_dict = {}
        for task_report in visible_task_reports:
            if task_report.task_id not in visible_task_report_dict:
                visible_task_report_dict[task_report.task_id] = []
            visible_task_report_dict[task_report.task_id].append(task_report)
        for log_file_model in log_file_models:
            parse_task = parse_task_dict.get(log_file_model.id)
            brpc_parse_task = brpc_parse_task_dict.get(log_file_model.id)
            if log_file_model.log_type == "brpc":
                diagnosis_task = brpc_diagnosis_task_dict.get(log_file_model.id)
            else:
                diagnosis_task = diagnosis_task_dict.get(log_file_model.id)
            store_task = store_task_dict.get(log_file_model.id)
            visible_task = task_dict.get(log_file_model.id)
            # 和get_log_file_by_log_file_id完全一致：分别挂载任务的reports
            if parse_task:
                parse_task.task_reports = type_task_report_dict.get(parse_task.id, [])
            if brpc_parse_task:
                brpc_parse_task.task_reports = type_task_report_dict.get(brpc_parse_task.id, [])
            if diagnosis_task:
                diagnosis_task.task_reports = type_task_report_dict.get(diagnosis_task.id, [])
            if store_task:
                store_task.task_reports = type_task_report_dict.get(store_task.id, [])

            if log_file_model.log_type == "brpc":
                log_file_model.overall_progress = parallel_overall_progress(
                    brpc_parse_task,
                    diagnosis_task,
                )
                await LogFileService._populate_brpc_counts(
                    log_file_model, brpc_parse_task, diagnosis_task
                )
            else:
                log_file_model.overall_progress = parallel_overall_progress(
                    parse_task,
                    diagnosis_task,
                    store_task,
                )
            # 和get_log_file_by_log_file_id完全一致：单独查询可见任务的reports并排序
            log_file_model.task = visible_task
            if visible_task:
                visible_task.task_reports = visible_task_report_dict.get(visible_task.id, [])
                visible_task.task_reports.sort(
                    key=lambda x: x.created_at, reverse=True
                )
        return ListLogFilesMsg(total=total, log_files=log_file_models)

    @staticmethod
    async def get_log_file_by_log_file_id(log_file_id: str) -> GetLogFileMsg:
        log_file_model = await LogFilePGManager.get_log_file_by_log_file_id(log_file_id)
        if not log_file_model:
            raise NotFoundBizException(resource="日志文件")
        log_type = getattr(log_file_model, "log_type", "kv-cache") or "kv-cache"
        if log_type == "brpc":
            parse_task = await TaskPGManager.get_current_task_by_op_id(
                log_file_id,
                TaskTypeEnum.BRPC_LOG_PARSE_WORKER,
            )
            diagnosis_task = await TaskPGManager.get_current_task_by_op_id(
                log_file_id,
                TaskTypeEnum.BRPC_LOG_DIAGNOSIS_WORKER,
            )
            store_task = None
        else:
            parse_task = await TaskPGManager.get_current_task_by_op_id(
                log_file_id,
                TaskTypeEnum.KV_CACHE_LOG_PARSE_WORKER,
            )
            diagnosis_task = await TaskPGManager.get_current_task_by_op_id(
                log_file_id,
                TaskTypeEnum.KV_CACHE_LOG_EVENT_DIAGNOSIS_WORKER,
            )
            store_task = await TaskPGManager.get_current_task_by_op_id(
                log_file_id,
                TaskTypeEnum.STORE_TRACE_CONTEXT_LOGS_WORKER,
            )
        if log_type == "brpc":
            task_model = LogFileService._select_brpc_visible_task(
                parse_task,
                diagnosis_task,
            )
        else:
            task_model = LogFileService._select_visible_task(
                parse_task, diagnosis_task, store_task
            )
        if not task_model:
            task_model = await TaskPGManager.get_current_task_by_op_id(log_file_id)
        if task_model:
            parse_reports = (
                await TaskReportPGManager.list_task_reports_by_task_ids([parse_task.id])
                if parse_task
                else []
            )
            diagnosis_reports = (
                await TaskReportPGManager.list_task_reports_by_task_ids([diagnosis_task.id])
                if diagnosis_task
                else []
            )
            store_reports = (
                await TaskReportPGManager.list_task_reports_by_task_ids([store_task.id])
                if store_task
                else []
            )
            if parse_task:
                parse_task.task_reports = parse_reports
            if diagnosis_task:
                diagnosis_task.task_reports = diagnosis_reports
            if store_task:
                store_task.task_reports = store_reports
            if log_type == "brpc":
                log_file_model.overall_progress = parallel_overall_progress(
                    parse_task,
                    diagnosis_task,
                )
                await LogFileService._populate_brpc_counts(
                    log_file_model, parse_task, diagnosis_task
                )
            else:
                log_file_model.overall_progress = parallel_overall_progress(
                    parse_task,
                    diagnosis_task,
                    store_task,
                )
            task_model.task_reports = await TaskReportPGManager.list_task_reports_by_task_ids(
                [task_model.id]
            )
        log_file_model.task = task_model
        return GetLogFileMsg(log_file=log_file_model)
