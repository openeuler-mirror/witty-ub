import asyncio
import logging
import os
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
from latency.common.convertor import Convertor
from latency.database.engine import PGManager
from latency.database.managers.task import TaskPGManager
from latency.database.managers.log_knowledge import LogKnowledgePGManager
from latency.database.managers.log_file import LogFilePGManager
from latency.database.managers.diagnosis_config import DiagnosisConfigPGManager
from latency.task.deletion import (
    cleanup_log_artifacts,
    cleanup_log_temp_dirs,
    default_upload_root,
)
from latency.task.log_preprocessor import WITTY_DIR_DEFAULT
from latency.task.task_handler import TaskHandler
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
        # Reserve at asset scope before the first database await.  This is
        # intentionally synchronous so scheduler work in this process yields
        # to deletion immediately.
        TaskHandler.reserve_deletion(kb_id=kb_id)
        tasks = []
        fenced_log_ids = set()
        try:
            log_kb = await LogKnowledgePGManager.get_log_kb_by_kb_id(kb_id)
            if not log_kb:
                raise NotFoundBizException(resource="知识库")

            # Fence every state, not only PENDING/RUNNING:
            # FAILED_PENDING_REMOVE is the automatic-retry window after OOM.
            tasks = await TaskPGManager.list_tasks_by_kb_id(kb_id)
            log_file_ids = await LogFilePGManager.list_log_file_ids(
                kb_id=kb_id, include_inactive=True
            )
            log_files = []
            for log_file_id in log_file_ids:
                log_file = await LogFilePGManager.get_log_file_by_log_file_id(log_file_id)
                if log_file is not None:
                    log_files.append(log_file)

            fenced_log_ids = set(log_file_ids)
            fenced_log_ids.update(
                task.op_id
                for task in tasks
                if isinstance(getattr(task, "op_id", None), str) and task.op_id
            )
            TaskHandler.reserve_deletion(log_ids=fenced_log_ids)
            await TaskHandler.begin_deletion(
                tasks,
                log_ids=fenced_log_ids,
                kb_id=kb_id,
            )
            for log_file in log_files:
                await asyncio.to_thread(
                    cleanup_log_artifacts,
                    log_file,
                    witty_dir=witty_dir,
                    upload_root=default_upload_root(),
                )
            # An interrupted upload can leave a task and temp directory after
            # its log row disappeared.  The task's op_id still gives us the
            # owned temp-directory names, so cascade those as well.
            persisted_log_ids = {log_file.id for log_file in log_files}
            for orphan_log_id in fenced_log_ids - persisted_log_ids:
                await asyncio.to_thread(
                    cleanup_log_temp_dirs,
                    orphan_log_id,
                    witty_dir=witty_dir,
                )

            for log_file_id in log_file_ids:
                deleted = await LogFilePGManager.hard_delete_log_file_with_related_data(
                    log_file_id
                )
                if not deleted:
                    raise RuntimeError(f"级联删除日志文件失败: {log_file_id}")

            # Remove tasks not tied to a current log row as well (for example,
            # remnants of an interrupted upload), then physically remove the KB.
            await TaskPGManager.hard_delete_tasks_by_kb_id(kb_id)
            await DiagnosisConfigPGManager.delete(kb_id)
            if not await LogKnowledgePGManager.delete_log_kb_by_kb_id(kb_id):
                raise RuntimeError("删除资产库失败")
        finally:
            TaskHandler.end_deletion(
                tasks,
                log_ids=fenced_log_ids,
                kb_id=kb_id,
            )
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
