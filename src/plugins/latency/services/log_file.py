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
            elif upload_log_file_config.source_type == SourceType.remote:
                # 请求远程URL获取日志文件内容，并保存到本地文件系统中
                try:
                    async with aiohttp.ClientSession() as session:
                        async with session.get(
                            upload_log_file_config.source
                        ) as response:
                            response.raise_for_status()
                            content = await response.read()
                    local_zip_file_path = os.path.join(
                        FilePath.FILE_UPLOAD_PATH.value, log_file_model.id + ".zip"
                    )
                    async with aiofiles.open(local_zip_file_path, "wb") as f:
                        await f.write(content)
                except Exception as e:
                    logger.error(
                        f"下载远程日志文件失败，URL: {upload_log_file_config.source}, 错误信息: {str(e)}"
                    )
                if not ZipHandler.is_zip_file(local_zip_file_path):
                    logger.error(
                        f"下载的远程日志文件不是有效的ZIP文件，URL: {upload_log_file_config.source}"
                    )
                    continue
                extracted_file_path = os.path.join(
                    FilePath.FILE_UPLOAD_PATH.value, log_file_model.id
                )
                try:
                    ZipHandler.unzip_file(local_zip_file_path, extracted_file_path)
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
            elif upload_log_file_config.source_type == SourceType.upload:
                uploaded_file: UploadFile = upload_log_file_config.source
                local_zip_file_path = os.path.join(
                    FilePath.FILE_UPLOAD_PATH.value, log_file_model.id + ".zip"
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
                extracted_file_path = os.path.join(
                    FilePath.FILE_UPLOAD_PATH.value, log_file_model.id
                )
                try:
                    ZipHandler.unzip_file(local_zip_file_path, extracted_file_path)
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
        tasks = await TaskManager.list_current_tasks_by_op_ids(log_file_model_ids)
        task_dict = {task.op_id: task for task in tasks}
        task_reports = await TaskReportManager.list_task_reports_by_task_ids(
            [task.id for task in tasks]
        )
        task_report_dict = {}
        for task_report in task_reports:
            if task_report.task_id not in task_report_dict:
                task_report_dict[task_report.task_id] = []
            task_report_dict[task_report.task_id].append(task_report)
        for log_file_model in log_file_models:
            log_file_model.task = task_dict.get(log_file_model.id)
            if log_file_model.task:
                log_file_model.task.task_reports = task_report_dict.get(
                    log_file_model.task.id, []
                )
                log_file_model.task.task_reports.sort(
                    key=lambda x: x.created_at, reverse=True
                )
        return ListLogFilesMsg(total=total, log_files=log_file_models)

    @staticmethod
    async def get_log_file_by_log_file_id(log_file_id: str) -> GetLogFileMsg:
        log_file_model = await LogFileManager.get_log_file_by_log_file_id(log_file_id)
        return GetLogFileMsg(log_file=log_file_model)
