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
from latency.ENUM.task import TaskStatusEnum
from latency.common.convertor import Convertor
from latency.database.engine import PGManager
from latency.database.managers.task import TaskPGManager
from latency.database.managers.log_knowledge import LogKnowledgePGManager
from latency.database.managers.log_file import LogFilePGManager
from latency.database.managers.diagnosis_config import DiagnosisConfigPGManager
from latency.task.worker.base import BaseWorker
from latency.task.log_preprocessor import cleanup_preprocess_dir, WITTY_DIR_DEFAULT
from latency.exceptions import ConflictBizException, NotFoundBizException

logger = logging.getLogger(__name__)
witty_dir = os.getenv("WITTY_DIR", WITTY_DIR_DEFAULT)


class LogKnowledgeService:
    @staticmethod
    async def create_log_kb(req: CreateLogKnowledgeRequest) -> CreateLogKnowledgeMsg:
        log_kb = await Convertor.create_log_kb_req_to_log_kb_model(req)
        # The asset and its default configuration must commit or roll back together.
        async with PGManager.session() as session:
            kb_id = await LogKnowledgePGManager.add_log_kb(log_kb, session=session)
            if not kb_id:
                raise ConflictBizException(message="资产库名称已存在")
            await DiagnosisConfigPGManager.reset(kb_id, session=session)
        return CreateLogKnowledgeMsg(kb_id=kb_id)

    @staticmethod
    async def delete_log_kb_by_kb_id(kb_id: str) -> DeleteLogKnowledgeMsg:
        log_kb = await LogKnowledgePGManager.get_log_kb_by_kb_id(kb_id)
        if not log_kb:
            raise NotFoundBizException(resource="知识库")

        # Stop every active task tree before making the asset invisible.  A
        # failed stop is recorded for operations, but does not prevent the
        # user-requested asset deletion from completing.
        tasks = await TaskPGManager.list_tasks_by_kb_id(
            kb_id, [TaskStatusEnum.PENDING, TaskStatusEnum.RUNNING]
        )
        failed_task_ids = []
        for task in tasks:
            try:
                if not await BaseWorker.stop(task.id):
                    failed_task_ids.append(task.id)
            except Exception:
                failed_task_ids.append(task.id)
                logger.exception("停止资产库任务进程树失败: task_id=%s", task.id)
        if failed_task_ids:
            logger.error(
                "资产库 %s 删除前有 %d 个任务进程树未能确认停止，继续删除: %s",
                kb_id,
                len(failed_task_ids),
                failed_task_ids,
            )

        rowcount = await LogKnowledgePGManager.update_log_kb(
            kb_id, {"existed_status": False}
        )
        if rowcount == 0:
            raise NotFoundBizException(resource="知识库")
        
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
