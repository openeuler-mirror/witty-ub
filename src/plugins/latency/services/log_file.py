import requests
import os
import aiofiles
import aiohttp
import logging
from fastapi import UploadFile
from latency.database.managers.log_file import LogFileManager
from latency.database.managers.task import TaskManager
from latency.database.managers.task_report import TaskReportManager
from latency.schemas.log import LogFileModel
from latency.ENUM.general import FilePath
from latency.ENUM.general import SourceType
from latency.schemas.request import (
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
    ListLogFilesMsg,
    GetLogFileMsg,
)
from latency.ENUM.task import TaskTypeEnum, TaskStatusEnum
from latency.task.task_handler import TaskHandler
from latency.common.zip_handler import ZipHandler

logger = logging.getLogger(__name__)


class LogFileService:
    @staticmethod
    def _select_visible_task(parse_task, diagnosis_task):
        if not parse_task:
            return diagnosis_task
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
        return diagnosis_task

    @staticmethod
    def _clamp_progress(progress: float | int | None) -> float:
        if progress is None:
            return 0.0
        return min(100.0, max(0.0, float(progress)))

    @staticmethod
    def _latest_progress(task) -> float:
        if not task or not task.task_reports:
            return 0.0
        return max(LogFileService._clamp_progress(report.progress) for report in task.task_reports)

    @staticmethod
    def _average_task_report_progress(task, companion_task) -> None:
        if not task or not companion_task:
            return
        companion_progress = LogFileService._latest_progress(companion_task)
        for report in task.task_reports:
            report.progress = (
                LogFileService._clamp_progress(report.progress) + companion_progress
            ) / 2.0

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
        for upload_log_file_config in req.upload_log_file_configs:
            log_file_model = LogFileModel(kb_id=kb_id, name=upload_log_file_config.name)
            if upload_log_file_config.source_type == SourceType.LOCAL:
                log_file_model.file_path = upload_log_file_config.source
                try:
                    log_file_model.file_size = os.path.getsize(
                        upload_log_file_config.source
                    )
                except (FileNotFoundError, OSError):
                    log_file_model.file_size = 0
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
                    logger.error(
                        f"上传的日志文件不是有效的ZIP文件，文件名: {uploaded_file.filename}"
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
                        f"解压上传的日志文件失败，ZIP文件路径: {local_zip_file_path}, 错误信息: {str(e)}"
                    )
                if os.path.exists(local_zip_file_path):
                    try:
                        os.remove(local_zip_file_path)
                    except Exception as e:
                        logger.error(
                            f"删除临时ZIP文件失败，ZIP文件路径: {local_zip_file_path}, 错误信息: {str(e)}"
                        )
            log_file_models.append(log_file_model)
        log_file_ids = await LogFileManager.add_log_files(log_file_models)
        
        for log_file_id in log_file_ids:
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
        return UploadLogFilesMsg(log_file_ids=log_file_ids)

    @staticmethod
    async def delete_log_file_by_log_file_id(log_file_id: str) -> DeleteLogFilesMsg:
        flag = await LogFileManager.update_log_file(
            log_file_id, {"existed_status": False}
        )
        if flag:
            return DeleteLogFilesMsg(log_file_id=log_file_id)
        return DeleteLogFilesMsg(log_file_id=None)

    @staticmethod
    async def update_log_file(
        log_file_id: str, req: UpdateLogFileRequest
    ) -> UpdateLogFileMsg:
        flag = await LogFileManager.update_log_file(
            log_file_id, req.model_dump(exclude_none=True)
        )
        if flag:
            return UpdateLogFileMsg(log_file_id=log_file_id)
        return UpdateLogFileMsg(log_file_id=None)

    @staticmethod
    async def run_or_stop_log_parse_by_log_file_id(
        log_file_id: str, run: bool
    ) -> RunOrStopLogParseMsg:
        log_file_model = await LogFileManager.get_log_file_by_log_file_id(log_file_id)
        if not log_file_model:
            return RunOrStopLogParseMsg(task_id=None)
        if run:
            task_id = await TaskHandler.init_task(
                task_type=TaskTypeEnum.KV_CACHE_LOG_PARSE_WORKER,
                op_id=log_file_id,
            )
            return RunOrStopLogParseMsg(task_id=task_id)
        task = await TaskManager.get_current_task_by_op_id(log_file_id)
        if task and task.status in [TaskStatusEnum.PENDING, TaskStatusEnum.RUNNING]:
            await TaskHandler.stop_task(task.id)
            return RunOrStopLogParseMsg(task_id=task.id)
        else:
            return RunOrStopLogParseMsg(task_id=None)

    @staticmethod
    async def list_log_files(kb_id: str, req: ListLogFilesRequest) -> ListLogFilesMsg:
        total, log_file_models = await LogFileManager.list_log_files(kb_id, req)
        log_file_model_ids = [log_file_model.id for log_file_model in log_file_models]
        parse_tasks = await TaskManager.list_current_tasks_by_op_ids(
            log_file_model_ids,
            TaskTypeEnum.KV_CACHE_LOG_PARSE_WORKER,
        )
        diagnosis_tasks = await TaskManager.list_current_tasks_by_op_ids(
            log_file_model_ids,
            TaskTypeEnum.KV_CACHE_LOG_EVENT_DIAGNOSIS_WORKER,
        )
        parse_task_dict = {task.op_id: task for task in parse_tasks}
        diagnosis_task_dict = {task.op_id: task for task in diagnosis_tasks}
        task_op_ids = set(parse_task_dict) | set(diagnosis_task_dict)
        fallback_op_ids = [
            log_file_model_id
            for log_file_model_id in log_file_model_ids
            if log_file_model_id not in task_op_ids
        ]
        fallback_task_dict = {}
        if fallback_op_ids:
            fallback_task_dict = {
                task.op_id: task
                for task in await TaskManager.list_current_tasks_by_op_ids(fallback_op_ids)
            }
        task_dict = {
            log_file_model_id: LogFileService._select_visible_task(
                parse_task_dict.get(log_file_model_id),
                diagnosis_task_dict.get(log_file_model_id),
            )
            or fallback_task_dict.get(log_file_model_id)
            for log_file_model_id in log_file_model_ids
        }
        tasks = [
            task
            for task in (
                list(task_dict.values())
                + list(parse_task_dict.values())
                + list(diagnosis_task_dict.values())
            )
            if task
        ]
        tasks = list({task.id: task for task in tasks}.values())
        task_reports = await TaskReportManager.list_task_reports_by_task_ids(
            [task.id for task in tasks]
        )
        task_report_dict = {}
        for task_report in task_reports:
            if task_report.task_id not in task_report_dict:
                task_report_dict[task_report.task_id] = []
            task_report_dict[task_report.task_id].append(task_report)
        for log_file_model in log_file_models:
            parse_task = parse_task_dict.get(log_file_model.id)
            diagnosis_task = diagnosis_task_dict.get(log_file_model.id)
            if parse_task:
                parse_task.task_reports = task_report_dict.get(parse_task.id, [])
            if diagnosis_task:
                diagnosis_task.task_reports = task_report_dict.get(diagnosis_task.id, [])

            log_file_model.task = task_dict.get(log_file_model.id)
            if log_file_model.task:
                log_file_model.task.task_reports = task_report_dict.get(
                    log_file_model.task.id, []
                )
                companion_task = (
                    diagnosis_task
                    if log_file_model.task.task_type == TaskTypeEnum.KV_CACHE_LOG_PARSE_WORKER
                    else parse_task
                )
                LogFileService._average_task_report_progress(
                    log_file_model.task,
                    companion_task,
                )
                log_file_model.task.task_reports.sort(
                    key=lambda x: x.created_at, reverse=True
                )
        return ListLogFilesMsg(total=total, log_files=log_file_models)

    @staticmethod
    async def get_log_file_by_log_file_id(log_file_id: str) -> GetLogFileMsg:
        log_file_model = await LogFileManager.get_log_file_by_log_file_id(log_file_id)
        parse_task = await TaskManager.get_current_task_by_op_id(
            log_file_id,
            TaskTypeEnum.KV_CACHE_LOG_PARSE_WORKER,
        )
        diagnosis_task = await TaskManager.get_current_task_by_op_id(
            log_file_id,
            TaskTypeEnum.KV_CACHE_LOG_EVENT_DIAGNOSIS_WORKER,
        )
        task_model = LogFileService._select_visible_task(parse_task, diagnosis_task)
        if not task_model:
            task_model = await TaskManager.get_current_task_by_op_id(log_file_id)
        if task_model:
            parse_reports = (
                await TaskReportManager.list_task_reports_by_task_ids([parse_task.id])
                if parse_task
                else []
            )
            diagnosis_reports = (
                await TaskReportManager.list_task_reports_by_task_ids([diagnosis_task.id])
                if diagnosis_task
                else []
            )
            if parse_task:
                parse_task.task_reports = parse_reports
            if diagnosis_task:
                diagnosis_task.task_reports = diagnosis_reports
            task_model.task_reports = await TaskReportManager.list_task_reports_by_task_ids(
                [task_model.id]
            )
            companion_task = (
                diagnosis_task
                if task_model.task_type == TaskTypeEnum.KV_CACHE_LOG_PARSE_WORKER
                else parse_task
            )
            LogFileService._average_task_report_progress(
                task_model,
                companion_task,
            )
        log_file_model.task = task_model
        return GetLogFileMsg(log_file=log_file_model)
