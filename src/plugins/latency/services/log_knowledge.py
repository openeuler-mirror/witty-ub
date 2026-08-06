import logging
import os
import shutil
from latency.schemas.request import (
    CreateLogKnowledgeRequest,
    UpdateLogKnowledgeRequest,
    ListLogKnowledgeRequest,
)
from latency.schemas.response import (
    CreateLogKnowledgeMsg,
    DeleteLogKnowledgeMsg,
    UpdateLogKnowledgeMsg,
    ListLogKnowledgeMsg,
    GetLogKnowledgeMsg,
)
from latency.ENUM.task import TaskTypeEnum, TaskStatusEnum
from latency.common.convertor import Convertor
from latency.database.managers.task import TaskPGManager
from latency.database.managers.log_knowledge import LogKnowledgePGManager
from latency.database.managers.log_file import LogFilePGManager
from latency.database.managers.diagnosis_config import DiagnosisConfigPGManager
from latency.task.worker.base import BaseWorker
from latency.task.log_preprocessor import cleanup_preprocess_dir, WITTY_DIR_DEFAULT
from latency.exceptions import NotFoundBizException

logger = logging.getLogger(__name__)
witty_dir = os.getenv("WITTY_DIR", WITTY_DIR_DEFAULT)


class LogKnowledgeService:
    @staticmethod
    async def create_log_kb(req: CreateLogKnowledgeRequest) -> CreateLogKnowledgeMsg:
        log_kb = await Convertor.create_log_kb_req_to_log_kb_model(req)
        kb_id = await LogKnowledgePGManager.add_log_kb(log_kb)
        if kb_id:
            await DiagnosisConfigPGManager.reset(kb_id)
        return CreateLogKnowledgeMsg(kb_id=kb_id)

    @staticmethod
    async def delete_log_kb_by_kb_id(kb_id: str) -> DeleteLogKnowledgeMsg:
        rowcount = await LogKnowledgePGManager.update_log_kb(kb_id, {"existed_status": False})
        if rowcount == 0:
            raise NotFoundBizException(resource="知识库")
        
        tasks = await TaskPGManager.list_tasks_by_kb_id(
            kb_id, [TaskStatusEnum.PENDING, TaskStatusEnum.RUNNING]
        )
        for task in tasks:
            await BaseWorker.stop(task.id)
        
        log_file_ids = await LogFilePGManager.list_log_file_ids(kb_id=kb_id)
        for log_file_id in log_file_ids:
            cleanup_preprocess_dir(log_file_id)
            logger.info("已清理日志文件预处理目录: %s", log_file_id)
            
            diagnosis_output_dir = os.path.join(witty_dir, "log_" + log_file_id[:8])
            if os.path.exists(diagnosis_output_dir):
                try:
                    shutil.rmtree(diagnosis_output_dir)
                    logger.info("已清理诊断输出目录: %s", diagnosis_output_dir)
                except OSError as e:
                    logger.error("清理诊断输出目录 %s 失败: %s", diagnosis_output_dir, e)
        
        await DiagnosisConfigPGManager.delete(kb_id)
        return DeleteLogKnowledgeMsg(kb_id=kb_id)

    @staticmethod
    async def update_log_kb(
        kb_id: str, req: UpdateLogKnowledgeRequest
    ) -> UpdateLogKnowledgeMsg:
        log_kb = await LogKnowledgePGManager.get_log_kb_by_kb_id(kb_id)
        if not log_kb:
            raise NotFoundBizException(resource="知识库")
        rowcount = await LogKnowledgePGManager.update_log_kb(
            kb_id, req.model_dump(exclude_none=True)
        )
        if rowcount > 0:
            return UpdateLogKnowledgeMsg(kb_id=kb_id)
        else:
            return UpdateLogKnowledgeMsg(kb_id=None)

    @staticmethod
    async def list_log_kbs(req: ListLogKnowledgeRequest) -> ListLogKnowledgeMsg:
        total = await LogKnowledgePGManager.count_log_kbs(req)
        log_kbs = await LogKnowledgePGManager.list_log_kbs(req)
        return ListLogKnowledgeMsg(total=total, kbs=log_kbs)

    @staticmethod
    async def get_log_kb_by_kb_id(kb_id: str) -> GetLogKnowledgeMsg:
        log_kb = await LogKnowledgePGManager.get_log_kb_by_kb_id(kb_id)
        if not log_kb:
            raise NotFoundBizException(resource="知识库")
        return GetLogKnowledgeMsg(kb=log_kb)
