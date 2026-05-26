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
from latency.database.managers.task import TaskManager
from latency.database.managers.log_knowledge import LogKnowledgeManager
from latency.task.worker.base import BaseWorker


class LogKnowledgeService:
    @staticmethod
    async def create_log_kb(req: CreateLogKnowledgeRequest) -> CreateLogKnowledgeMsg:
        log_kb = await Convertor.create_log_kb_req_to_log_kb_model(req)
        kb_id = await LogKnowledgeManager.add_log_kb(log_kb)
        return CreateLogKnowledgeMsg(kb_id=kb_id)

    @staticmethod
    async def delete_log_kb_by_kb_id(kb_id: str) -> DeleteLogKnowledgeMsg:
        tasks = await TaskManager.list_tasks_by_kb_id(
            kb_id, [TaskStatusEnum.PENDING, TaskStatusEnum.RUNNING]
        )
        for task in tasks:
            await BaseWorker.stop(task.id)
        flag = await LogKnowledgeManager.update_log_kb(kb_id, {"existed_status": False})
        if flag:
            return DeleteLogKnowledgeMsg(kb_id=kb_id)
        else:
            return DeleteLogKnowledgeMsg(kb_id=None)

    @staticmethod
    async def update_log_kb(
        kb_id: str, req: UpdateLogKnowledgeRequest
    ) -> UpdateLogKnowledgeMsg:
        flag = await LogKnowledgeManager.update_log_kb(
            kb_id, req.model_dump(exclude_none=True)
        )
        if flag:
            return UpdateLogKnowledgeMsg(kb_id=kb_id)
        else:
            return UpdateLogKnowledgeMsg(kb_id=None)

    @staticmethod
    async def list_log_kbs(req: ListLogKnowledgeRequest) -> ListLogKnowledgeMsg:
        total = await LogKnowledgeManager.count_log_kbs(req)
        log_kbs = await LogKnowledgeManager.list_log_kbs(req)
        return ListLogKnowledgeMsg(total=total, kbs=log_kbs)

    @staticmethod
    async def get_log_kb_by_kb_id(kb_id: str) -> GetLogKnowledgeMsg:
        log_kb = await LogKnowledgeManager.get_log_kb_by_kb_id(kb_id)
        return GetLogKnowledgeMsg(log_kb=log_kb)
