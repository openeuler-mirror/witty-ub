# Copyright (c) Huawei Technologies Co., Ltd. 2023-2025. All rights reserved.
"""PostgreSQL manager for failure mode knowledge and status code knowledge."""
from __future__ import annotations

from typing import Optional

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert

from latency.database.engine import PGManager
from latency.database.models import FailureModeKnowledge, StatusCodeKnowledge
from latency.schemas.failure_mode import FailureModeModel, StatusCodeKnowledgeModel


class FailureModeKnowledgePGManager:
    """PostgreSQL-backed failure mode knowledge manager."""

    @staticmethod
    async def get_status_code_knowledge(
        status_code: str,
    ) -> Optional[StatusCodeKnowledgeModel]:
        async with PGManager.session() as session:
            row = await session.get(StatusCodeKnowledge, status_code)
        if row is None:
            return None
        return StatusCodeKnowledgeModel(
            status_code=row.status_code,
            symptom=row.symptom or "",
            root_cause=row.root_cause or "",
        )

    @staticmethod
    async def add_status_code_knowledge(
        results: list[StatusCodeKnowledgeModel],
    ) -> list[str]:
        if not results:
            return []
        values = [
            {
                "status_code": item.status_code,
                "symptom": item.symptom,
                "root_cause": item.root_cause,
            }
            for item in results
        ]
        async with PGManager.session() as session:
            insert_stmt = insert(StatusCodeKnowledge).values(values)
            stmt = insert_stmt.on_conflict_do_update(
                index_elements=["status_code"],
                set_={
                    "symptom": insert_stmt.excluded.symptom,
                    "root_cause": insert_stmt.excluded.root_cause,
                },
            )
            await session.execute(stmt)
        return [item.status_code for item in results]

    @staticmethod
    async def get_failure_mode_by_id(failure_mode_id: str) -> Optional[FailureModeModel]:
        async with PGManager.session() as session:
            row = await session.get(FailureModeKnowledge, failure_mode_id)
        if row is None:
            return None
        return FailureModeModel(
            id=row.id,
            name=row.name or "",
            symptom=row.symptom or "",
            root_cause=row.root_cause or "",
            solution=row.solution or "",
            failure_domain=row.failure_domain or "",
            children_failure_mode_ids=row.children_failure_mode_ids or "",
        )

    @staticmethod
    async def get_all_failure_modes() -> dict[str, FailureModeModel]:
        async with PGManager.session() as session:
            result = await session.execute(select(FailureModeKnowledge))
            rows = result.scalars().all()
        return {
            row.id: FailureModeModel(
                id=row.id,
                name=row.name or "",
                symptom=row.symptom or "",
                root_cause=row.root_cause or "",
                solution=row.solution or "",
                failure_domain=row.failure_domain or "",
                children_failure_mode_ids=row.children_failure_mode_ids or "",
            )
            for row in rows
        }

    @staticmethod
    async def add_failure_mode_knowledge(
        results: list[FailureModeModel],
    ) -> list[str]:
        ids_added: list[str] = []
        if not results:
            return ids_added

        batch_size = 1024
        for i in range(0, len(results), batch_size):
            batch = results[i : i + batch_size]
            values = [
                failure_mode.model_dump(exclude_none=False, by_alias=True)
                for failure_mode in batch
            ]
            async with PGManager.session() as session:
                insert_stmt = insert(FailureModeKnowledge).values(values)
                stmt = insert_stmt.on_conflict_do_update(
                    index_elements=["id"],
                    set_={
                        "name": insert_stmt.excluded.name,
                        "symptom": insert_stmt.excluded.symptom,
                        "root_cause": insert_stmt.excluded.root_cause,
                        "solution": insert_stmt.excluded.solution,
                        "failure_domain": insert_stmt.excluded.failure_domain,
                        "children_failure_mode_ids": insert_stmt.excluded.children_failure_mode_ids,
                    },
                )
                await session.execute(stmt)
            ids_added.extend([failure_mode.id for failure_mode in batch])
        return ids_added
