"""Small, centralized existence queries for API resource identifiers."""

from __future__ import annotations

from collections.abc import Iterable

from sqlalchemy import select

from latency.database.engine import PGManager
from latency.database.models import (
    AnomalousEvent,
    BrpcDiagBatch,
    BrpcDiagNode,
    DiagnosisCase,
    FailureModeKnowledge,
    LogFailureEvent,
    LogFile,
    LogKnowledge,
    LogParseResult,
    SrcDstAggregatedEvent,
    Task,
    TraceFailureEvent,
)


class ResourceIdPGManager:
    """Resolve IDs without loading complete domain models.

    Keeping these checks here gives list/filter endpoints the same not-found
    behavior as detail and mutation endpoints, while allowing ID lists to be
    checked with one query instead of one query per ID.
    """

    _RESOURCE_COLUMNS = {
        "kb": (LogKnowledge.id, (LogKnowledge.existed_status.is_(True),)),
        "log": (LogFile.id, (LogFile.existed_status.is_(True),)),
        "task": (Task.id, (Task.existed_status.is_(True),)),
        "batch": (BrpcDiagBatch.batch_id, ()),
        "aggregated_event": (
            SrcDstAggregatedEvent.id,
            (SrcDstAggregatedEvent.existed_status.is_(True),),
        ),
        "anomalous_event": (
            AnomalousEvent.id,
            (AnomalousEvent.existed_status.is_(True),),
        ),
        "log_parse_result": (
            LogParseResult.id,
            (LogParseResult.existed_status.is_(True),),
        ),
        "diagnosis_case": (
            DiagnosisCase.id,
            (DiagnosisCase.existed_status.is_(True),),
        ),
    }

    @staticmethod
    def _unique(values: Iterable[str]) -> list[str]:
        return list(dict.fromkeys(values))

    @classmethod
    async def find_missing(cls, resource: str, values: Iterable[str]) -> list[str]:
        requested = cls._unique(values)
        if not requested:
            return []
        if resource == "failure_mode":
            return await cls.find_missing_failure_mode_ids(requested)

        column, conditions = cls._RESOURCE_COLUMNS[resource]
        stmt = select(column).where(column.in_(requested), *conditions).distinct()
        async with PGManager.session() as session:
            found = set((await session.execute(stmt)).scalars().all())
        return [value for value in requested if value not in found]

    @classmethod
    async def find_missing_failure_mode_ids(
        cls,
        values: Iterable[str],
    ) -> list[str]:
        """Accept failure modes from either knowledge source."""
        requested = cls._unique(values)
        if not requested:
            return []

        async with PGManager.session() as session:
            curated = set(
                (
                    await session.execute(
                        select(FailureModeKnowledge.id).where(
                            FailureModeKnowledge.id.in_(requested)
                        )
                    )
                )
                .scalars()
                .all()
            )
            brpc = set(
                (
                    await session.execute(
                        select(BrpcDiagNode.node_id)
                        .where(
                            BrpcDiagNode.node_id.in_(requested),
                            BrpcDiagNode.node_type == "failure_mode",
                        )
                        .distinct()
                    )
                )
                .scalars()
                .all()
            )
        found = curated | brpc
        return [value for value in requested if value not in found]

    @classmethod
    async def find_missing_trace_ids(cls, values: Iterable[str]) -> list[str]:
        """Find trace IDs absent from every trace-bearing result table."""
        requested = cls._unique(values)
        if not requested:
            return []

        async with PGManager.session() as session:
            parsed = set(
                (
                    await session.execute(
                        select(LogParseResult.trace_id)
                        .where(
                            LogParseResult.trace_id.in_(requested),
                            LogParseResult.existed_status.is_(True),
                        )
                        .distinct()
                    )
                )
                .scalars()
                .all()
            )
            failures = set(
                (
                    await session.execute(
                        select(TraceFailureEvent.trace_id)
                        .where(TraceFailureEvent.trace_id.in_(requested))
                        .distinct()
                    )
                )
                .scalars()
                .all()
            )
            raw_logs = set(
                (
                    await session.execute(
                        select(LogFailureEvent.trace_id)
                        .where(LogFailureEvent.trace_id.in_(requested))
                        .distinct()
                    )
                )
                .scalars()
                .all()
            )
        found = parsed | failures | raw_logs
        return [value for value in requested if value not in found]
