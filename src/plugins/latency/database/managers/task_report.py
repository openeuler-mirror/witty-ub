# Copyright (c) Huawei Technologies Co., Ltd. 2023-2025. All rights reserved.
"""PostgreSQL-specific manager for task_report."""
from __future__ import annotations

from typing import Any

from sqlalchemy import desc, select, text
from sqlalchemy.dialects.postgresql import insert

from latency.database.engine import PGManager
from latency.database.models import TaskReport
from latency.database.utils import parse_timestamp
from latency.schemas.task import TaskReportModel


class TaskReportPGManager:
    @staticmethod
    def _report_to_mapping(report: TaskReportModel) -> dict[str, Any]:
        return {
            "task_id": report.task_id,
            "progress": report.progress,
            "message": report.message,
            "existed_status": report.existed_status,
            "created_at": parse_timestamp(report.created_at),
        }

    @staticmethod
    async def add_task_report(task_report: TaskReportModel) -> bool:
        async with PGManager.session() as session:
            await session.execute(insert(TaskReport), [TaskReportPGManager._report_to_mapping(task_report)])
        return True

    @staticmethod
    async def add_task_reports(task_reports: list[TaskReportModel]) -> list[str]:
        if not task_reports:
            return []
        mappings = [TaskReportPGManager._report_to_mapping(r) for r in task_reports]
        async with PGManager.session() as session:
            await session.execute(insert(TaskReport), mappings)
        return [r.task_id for r in task_reports]

    @staticmethod
    async def update_task_reports_existed_status_by_task_id(
        task_id: str, existed_status: int
    ) -> bool:
        async with PGManager.session() as session:
            await session.execute(
                text(
                    "UPDATE task_report SET existed_status = :existed_status "
                    "WHERE task_id = :task_id"
                ),
                {"task_id": task_id, "existed_status": bool(existed_status)},
            )
        return True

    @staticmethod
    async def list_task_reports_by_task_ids(
        task_ids: list[str],
    ) -> list[TaskReportModel]:
        if not task_ids:
            return []
        async with PGManager.session() as session:
            result = await session.execute(
                select(TaskReport.task_id, TaskReport.progress, TaskReport.message, TaskReport.existed_status, TaskReport.created_at)
                .where(TaskReport.task_id.in_(task_ids))
                .order_by(desc(TaskReport.created_at))
            )
            rows = result.mappings().all()
        return [TaskReportModel(**dict(r)) for r in rows]

    @staticmethod
    async def delete_task_reports_by_task_ids(task_ids: list[str]) -> bool:
        """软删除任务报告（设置 existed_status=False）"""
        if not task_ids:
            return True
        async with PGManager.session() as session:
            await session.execute(
                text(
                    "UPDATE task_report SET existed_status = FALSE "
                    "WHERE task_id = ANY(:task_ids)"
                ),
                {"task_ids": task_ids},
            )
        return True
