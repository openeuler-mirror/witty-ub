# Copyright (c) Huawei Technologies Co., Ltd. 2023-2025. All rights reserved.
"""PostgreSQL-specific manager for task."""
from __future__ import annotations

from typing import Any

from sqlalchemy import desc, func, insert, select, text

from latency.database.engine import PGManager
from latency.database.models import Task
from latency.database.utils import parse_timestamp
from latency.ENUM.task import TaskStatusEnum, TaskTypeEnum
from latency.schemas.task import TaskModel


class TaskPGManager:
    @staticmethod
    def _model_to_mapping(task: TaskModel) -> dict[str, Any]:
        return {
            "id": task.id,
            "kb_id": task.kb_id,
            "op_id": task.op_id,
            "retry_times": task.retry_times,
            "task_name": task.task_name,
            "task_type": task.task_type.value,
            "status": task.status.value,
            "existed_status": task.existed_status,
            "created_at": parse_timestamp(task.created_at),
            "completed_at": parse_timestamp(task.completed_at),
            "duration_seconds": task.duration_seconds,
        }

    @staticmethod
    async def add_task(task: TaskModel) -> bool:
        async with PGManager.session() as session:
            await session.execute(insert(Task), [TaskPGManager._model_to_mapping(task)])
        return True

    @staticmethod
    async def add_tasks(tasks: list[TaskModel]) -> list[str]:
        if not tasks:
            return []
        mappings = [TaskPGManager._model_to_mapping(t) for t in tasks]
        async with PGManager.session() as session:
            await session.execute(insert(Task), mappings)
        return [t.id for t in tasks]

    @staticmethod
    async def delete_task_by_task_id(task_id: str) -> bool:
        async with PGManager.session() as session:
            await session.execute(text("DELETE FROM task WHERE id = :id"), {"id": task_id})
        return True

    @staticmethod
    async def delete_tasks_by_task_ids(task_ids: list[str]) -> bool:
        if not task_ids:
            return False
        async with PGManager.session() as session:
            await session.execute(
                text("DELETE FROM task WHERE id = ANY(:ids)"),
                {"ids": task_ids},
            )
        return True

    @staticmethod
    async def delete_tasks_by_status(status: str) -> bool:
        async with PGManager.session() as session:
            await session.execute(
                text("DELETE FROM task WHERE status = :status"),
                {"status": status},
            )
        return True

    @staticmethod
    async def update_task(task_id: str, task_info_dict: dict) -> bool:
        allowed = {k: v for k, v in task_info_dict.items() if hasattr(Task, k)}
        if not allowed:
            return True
        set_clauses = ", ".join(f"{k} = :{k}" for k in allowed)
        params = {"id": task_id, **allowed}
        async with PGManager.session() as session:
            await session.execute(
                text(f"UPDATE task SET {set_clauses} WHERE id = :id"),
                params,
            )
        return True

    @staticmethod
    async def update_running_tasks_to_pending_tasks() -> bool:
        async with PGManager.session() as session:
            await session.execute(
                text(
                    "UPDATE task SET status = :pending_status "
                    "WHERE status = :running_status"
                ),
                {
                    "pending_status": TaskStatusEnum.PENDING.value,
                    "running_status": TaskStatusEnum.RUNNING.value,
                },
            )
        return True

    @staticmethod
    def _row_to_model(row: Task) -> TaskModel:
        return TaskModel(
            id=row.id,
            kb_id=row.kb_id or "",
            op_id=row.op_id or "",
            retry_times=row.retry_times or 0,
            task_name=row.task_name or "",
            task_type=TaskTypeEnum(row.task_type),
            status=TaskStatusEnum(row.status),
            existed_status=row.existed_status if row.existed_status is not None else True,
            created_at=row.created_at,
            completed_at=row.completed_at,
            duration_seconds=row.duration_seconds,
        )

    @staticmethod
    async def list_tasks_by_task_ids(task_ids: list[str]) -> list[TaskModel]:
        if not task_ids:
            return []
        async with PGManager.session() as session:
            result = await session.execute(
                select(Task).where(Task.id.in_(task_ids))
            )
            rows = result.scalars().all()
        return [TaskPGManager._row_to_model(r) for r in rows]

    @staticmethod
    async def list_all_tasks() -> list[TaskModel]:
        async with PGManager.session() as session:
            result = await session.execute(select(Task).order_by(desc(Task.created_at)))
            rows = result.scalars().all()
        return [TaskPGManager._row_to_model(r) for r in rows]

    @staticmethod
    async def get_task_by_task_id(task_id: str) -> TaskModel | None:
        async with PGManager.session() as session:
            result = await session.execute(select(Task).where(Task.id == task_id))
            row = result.scalar_one_or_none()
        if row is None:
            return None
        return TaskPGManager._row_to_model(row)

    @staticmethod
    async def list_tasks_by_kb_id(
        kb_id: str, status: list[TaskStatusEnum] | None = None
    ) -> list[TaskModel]:
        stmt = select(Task).where(Task.kb_id == kb_id)
        if status:
            stmt = stmt.where(Task.status.in_([s.value for s in status]))
        async with PGManager.session() as session:
            result = await session.execute(stmt)
            rows = result.scalars().all()
        return [TaskPGManager._row_to_model(r) for r in rows]

    @staticmethod
    async def list_tasks_by_status(status: list[TaskStatusEnum]) -> list[TaskModel]:
        if not status:
            return []
        stmt = select(Task).where(Task.status.in_([s.value for s in status]))
        async with PGManager.session() as session:
            result = await session.execute(stmt)
            rows = result.scalars().all()
        return [TaskPGManager._row_to_model(r) for r in rows]

    @staticmethod
    async def get_oldest_tasks_by_status(
        status: TaskStatusEnum, limit: int = 10
    ) -> list[TaskModel]:
        async with PGManager.session() as session:
            result = await session.execute(
                select(Task)
                .where(Task.status == status.value)
                .order_by(Task.created_at)
                .limit(limit)
            )
            rows = result.scalars().all()
        return [TaskPGManager._row_to_model(r) for r in rows]

    @staticmethod
    async def list_current_tasks_by_op_ids(
        op_ids: list[str],
        task_type: TaskTypeEnum | None = None,
    ) -> list[TaskModel]:
        if not op_ids:
            return []
        # 按 (op_id, task_type) 分区，确保每个 op_id 的每种任务类型都返回最新的任务
        # 这样可以获取一个 log_file_id 对应的所有任务（PARSE、DIAGNOSIS、STORE）
        partition_by = [Task.op_id, Task.task_type]
        subq = (
            select(
                Task,
                func.row_number()
                .over(partition_by=partition_by, order_by=desc(Task.created_at))
                .label("rn"),
            )
            .where(Task.op_id.in_(op_ids))
        )
        if task_type:
            subq = subq.where(Task.task_type == task_type.value)
        subq = subq.subquery()
        # 通过 JOIN 连接 Task 表和子查询，避免笛卡尔积
        stmt = select(Task).join(subq, Task.id == subq.c.id).where(subq.c.rn == 1)
        async with PGManager.session() as session:
            result = await session.execute(stmt)
            rows = result.scalars().all()
        return [TaskPGManager._row_to_model(r) for r in rows]

    @staticmethod
    async def get_current_task_by_op_id(
        op_id: str,
        task_type: TaskTypeEnum | None = None,
    ) -> TaskModel | None:
        stmt = select(Task).where(Task.op_id == op_id)
        if task_type:
            stmt = stmt.where(Task.task_type == task_type.value)
        stmt = stmt.order_by(desc(Task.created_at)).limit(1)
        async with PGManager.session() as session:
            result = await session.execute(stmt)
            row = result.scalar_one_or_none()
        if row is None:
            return None
        return TaskPGManager._row_to_model(row)
    
    @staticmethod
    async def list_tasks_by_op_id(op_id: str) -> list[TaskModel]:
        """查询指定op_id的所有任务"""
        stmt = select(Task).where(Task.op_id == op_id)
        async with PGManager.session() as session:
            result = await session.execute(stmt)
            rows = result.scalars().all()
        return [TaskPGManager._row_to_model(r) for r in rows]
