# Copyright (c) Huawei Technologies Co., Ltd. 2023-2024. All rights reserved.

import logging
from latency.schemas.request import CreateTaskRequest, ListTasksRequest
from latency.schemas.response import (
    CreateTaskMsg,
    StopTaskMsg,
    DeleteTaskMsg,
    ListTasksMsg,
    GetTaskMsg,
)
from latency.database.managers.task import TaskManager
from latency.database.managers.task_report import TaskReportManager
from latency.task.task_handler import TaskHandler
from latency.ENUM.task import TaskStatusEnum
from latency.exceptions import NotFoundBizException, ConflictBizException

logger = logging.getLogger(__name__)


class TaskService:
    """任务服务"""

    @staticmethod
    async def create_task(req: CreateTaskRequest) -> CreateTaskMsg:
        """创建任务"""
        task_id = await TaskHandler.init_task(
            task_type=req.task_type,
            op_id=req.op_id,
        )
        if not task_id:
            raise NotFoundBizException(resource="关联操作")
        return CreateTaskMsg(task_id=task_id)

    @staticmethod
    async def stop_task(task_id: str) -> StopTaskMsg:
        """停止任务"""
        task = await TaskManager.get_task_by_task_id(task_id)
        if not task:
            raise NotFoundBizException(resource="任务")
        
        if task.status not in [TaskStatusEnum.PENDING, TaskStatusEnum.RUNNING]:
            raise ConflictBizException(message=f"任务状态为{task.status}，不可停止")
        
        await TaskHandler.stop_task(task_id)
        return StopTaskMsg(task_id=task_id)

    @staticmethod
    async def delete_task(task_id: str) -> DeleteTaskMsg:
        """删除任务"""
        task = await TaskManager.get_task_by_task_id(task_id)
        if not task:
            raise NotFoundBizException(resource="任务")
        
        result_id = await TaskHandler.delete_task(task_id)
        if result_id:
            return DeleteTaskMsg(task_id=task_id)
        raise NotFoundBizException(resource="任务")

    @staticmethod
    async def list_tasks(req: ListTasksRequest) -> ListTasksMsg:
        """查询任务列表"""
        all_tasks = await TaskManager.list_all_tasks()
        
        filtered_tasks = []
        for task in all_tasks:
            if not task.existed_status:
                continue
            if req.task_type and task.task_type != req.task_type:
                continue
            if req.status and task.status != req.status:
                continue
            if req.kb_id and task.kb_id != req.kb_id:
                continue
            if req.op_id and task.op_id != req.op_id:
                continue
            if req.created_at_start and task.created_at < req.created_at_start:
                continue
            if req.created_at_end and task.created_at > req.created_at_end:
                continue
            filtered_tasks.append(task)
        
        if req.created_sorted_desc:
            filtered_tasks.sort(key=lambda x: x.created_at, reverse=True)
        else:
            filtered_tasks.sort(key=lambda x: x.created_at, reverse=False)
        
        total = len(filtered_tasks)
        start_idx = (req.page_num - 1) * req.page_cnt
        end_idx = start_idx + req.page_cnt
        paginated_tasks = filtered_tasks[start_idx:end_idx]
        
        task_ids = [task.id for task in paginated_tasks]
        task_reports = await TaskReportManager.list_task_reports_by_task_ids(task_ids)
        task_report_dict = {}
        for task_report in task_reports:
            if task_report.task_id not in task_report_dict:
                task_report_dict[task_report.task_id] = []
            task_report_dict[task_report.task_id].append(task_report)
        
        for task in paginated_tasks:
            task.task_reports = task_report_dict.get(task.id, [])
            task.task_reports.sort(key=lambda x: x.created_at, reverse=True)
        
        return ListTasksMsg(total=total, tasks=paginated_tasks)

    @staticmethod
    async def get_task_by_id(task_id: str) -> GetTaskMsg:
        """查询任务详情"""
        task = await TaskManager.get_task_by_task_id(task_id)
        if not task or not task.existed_status:
            return GetTaskMsg(task=None)
        
        task_reports = await TaskReportManager.list_task_reports_by_task_ids([task_id])
        task_reports.sort(key=lambda x: x.created_at, reverse=True)
        task.task_reports = task_reports
        
        return GetTaskMsg(task=task)
