"""Transactional data access primitives for UBSocket diagnosis results."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Sequence
from typing import Any

from sqlalchemy import (
    Numeric,
    String,
    and_,
    cast,
    delete,
    func,
    insert,
    literal,
    or_,
    select,
    text,
)
from sqlalchemy.ext.asyncio import AsyncSession

from latency.ENUM.task import TaskStatusEnum, TaskTypeEnum
from latency.database.models import (
    BrpcDiagBatch as BrpcDiagBatchRow,
    BrpcDiagEdge as BrpcDiagEdgeRow,
    BrpcDiagFailureInterface as BrpcDiagFailureInterfaceRow,
    BrpcDiagFailureSubgraph as BrpcDiagFailureSubgraphRow,
    BrpcDiagHit as BrpcDiagHitRow,
    BrpcDiagInterfaceBucket as BrpcDiagInterfaceBucketRow,
    BrpcDiagNode as BrpcDiagNodeRow,
    BrpcDiagSchema as BrpcDiagSchemaRow,
    LogFile,
    Task,
)
from latency.schemas.brpc_diagnosis import (
    BRPC_TOTAL_SORT_FIELD,
    BrpcDiagBatch,
    BrpcDiagEdge,
    BrpcDiagHit,
    BrpcDiagNode,
    BrpcDiagSchema,
    BrpcFailureInterface,
    BrpcMetricSortField,
    BrpcSortOrder,
)

UNRESOLVED_INTERFACE_ID = "__unresolved__"
UNRESOLVED_INTERFACE_NAME = "未确定接口"
BRPC_TIMELINE_WINDOW_US = (
    10_000_000,
    60_000_000,
    600_000_000,
    3_600_000_000,
)


class BrpcDiagnosisPGManager:
    """UBSocket diagnosis operations scoped to a caller-owned transaction.

    The manager never commits or rolls back. Importers should call these methods
    with one ``AsyncSession`` obtained from ``PGManager.session()`` so schema,
    batch replacement, and hit writes remain atomic.
    """

    @staticmethod
    async def schema_exists(session: AsyncSession, schema_id: str) -> bool:
        return await session.get(BrpcDiagSchemaRow, schema_id) is not None

    @staticmethod
    async def batch_exists(session: AsyncSession, batch_id: str) -> bool:
        return await session.get(BrpcDiagBatchRow, batch_id) is not None

    @staticmethod
    async def get_batch(
        session: AsyncSession, batch_id: str
    ) -> BrpcDiagBatchRow | None:
        return await session.get(BrpcDiagBatchRow, batch_id)

    @staticmethod
    async def get_batch_by_task_id(
        session: AsyncSession, task_id: str
    ) -> BrpcDiagBatchRow | None:
        result = await session.execute(
            select(BrpcDiagBatchRow).where(BrpcDiagBatchRow.task_id == task_id)
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def list_batches_by_kb_id(
        session: AsyncSession, kb_id: str
    ) -> list[BrpcDiagBatchRow]:
        """Return every live diagnosis batch owned by a knowledge base."""
        result = await session.execute(
            select(BrpcDiagBatchRow)
            .join(Task, Task.id == BrpcDiagBatchRow.task_id)
            .join(LogFile, LogFile.id == Task.op_id)
            .where(
                Task.kb_id == kb_id,
                Task.task_type == TaskTypeEnum.BRPC_LOG_DIAGNOSIS_WORKER.value,
                Task.status.in_(
                    (
                        TaskStatusEnum.SUCCESSFUL_PENDING_REMOVE.value,
                        TaskStatusEnum.SUCCESSFUL.value,
                    )
                ),
                Task.existed_status.is_(True),
                LogFile.existed_status.is_(True),
            )
            .order_by(
                BrpcDiagBatchRow.start_timestamp,
                BrpcDiagBatchRow.batch_id,
            )
        )
        return list(result.scalars().all())

    @staticmethod
    def _batch_filter(column, batch_id: str | Sequence[str]):
        if isinstance(batch_id, str):
            return column == batch_id
        return column.in_(list(batch_id))

    @staticmethod
    async def list_hits(
        session: AsyncSession,
        *,
        batch_id: str,
        page_num: int,
        page_cnt: int,
        start_timestamp: int | None = None,
        end_timestamp: int | None = None,
        pod_ip: str | None = None,
        pod_name: str | None = None,
        thread_id: int | None = None,
    ) -> tuple[int, list[BrpcDiagHitRow]]:
        """Return one stable, newest-first page of hits from a single batch."""
        filters = [BrpcDiagHitRow.batch_id == batch_id]
        if start_timestamp is not None:
            filters.append(BrpcDiagHitRow.timestamp >= start_timestamp)
        if end_timestamp is not None:
            filters.append(BrpcDiagHitRow.timestamp < end_timestamp)
        if pod_ip is not None:
            filters.append(BrpcDiagHitRow.pod_ip == pod_ip)
        if pod_name is not None:
            filters.append(BrpcDiagHitRow.pod_name == pod_name)
        if thread_id is not None:
            filters.append(BrpcDiagHitRow.thread_id == thread_id)

        total_result = await session.execute(
            select(func.count()).select_from(BrpcDiagHitRow).where(*filters)
        )
        total = int(total_result.scalar_one())
        rows_result = await session.execute(
            select(BrpcDiagHitRow)
            .where(*filters)
            .order_by(
                BrpcDiagHitRow.timestamp.desc(),
                BrpcDiagHitRow.hit_id.desc(),
            )
            .limit(page_cnt)
            .offset((page_num - 1) * page_cnt)
        )
        return total, list(rows_result.scalars().all())

    @staticmethod
    async def get_interface_timeline_aggregates(
        session: AsyncSession,
        *,
        batch_id: str | Sequence[str],
        start_timestamp: int,
        end_timestamp: int,
        window_us: int,
        interface_component: str | None = None,
        interface_id: str | None = None,
        pod_ip: str | None = None,
        pod_name: str | None = None,
        thread_id: int | None = None,
    ) -> list[dict[str, Any]]:
        """Aggregate each hit once by its resolved interface or unresolved."""
        window_start_timestamp = (
            func.floor(cast(BrpcDiagHitRow.timestamp, Numeric) / window_us)
            * window_us
        ).label("window_start_timestamp")
        filters = [
            BrpcDiagnosisPGManager._batch_filter(BrpcDiagHitRow.batch_id, batch_id),
            BrpcDiagHitRow.timestamp >= start_timestamp,
            BrpcDiagHitRow.timestamp < end_timestamp,
        ]
        if interface_id is not None:
            filters.append(
                BrpcDiagHitRow.interface_id.is_(None)
                if interface_id == UNRESOLVED_INTERFACE_ID
                else BrpcDiagHitRow.interface_id == interface_id
            )
        if pod_ip is not None:
            filters.append(BrpcDiagHitRow.pod_ip == pod_ip)
        if pod_name is not None:
            filters.append(BrpcDiagHitRow.pod_name == pod_name)
        if thread_id is not None:
            filters.append(BrpcDiagHitRow.thread_id == thread_id)

        component = func.coalesce(BrpcDiagNodeRow.component, "unknown")
        resolved_interface_id = func.coalesce(
            BrpcDiagHitRow.interface_id, UNRESOLVED_INTERFACE_ID
        )
        interface_name = func.coalesce(
            BrpcDiagNodeRow.name, UNRESOLVED_INTERFACE_NAME
        )
        function_name = func.coalesce(BrpcDiagNodeRow.function_name, "")
        if interface_component is not None:
            # A cross-component failure can resolve to an interface belonging
            # to another component. Filter by the resolved interface metadata,
            # which is also what the response exposes.
            filters.append(component == interface_component)
        statement = (
            select(
                window_start_timestamp,
                component.label("component"),
                resolved_interface_id.label("interface_id"),
                interface_name.label("interface_name"),
                function_name.label("function_name"),
                func.count(BrpcDiagHitRow.hit_id).label("interface_hit_count"),
            )
            .select_from(BrpcDiagHitRow)
            .outerjoin(
                BrpcDiagNodeRow,
                and_(
                    BrpcDiagNodeRow.schema_id
                    == BrpcDiagHitRow.schema_id,
                    BrpcDiagNodeRow.node_id
                    == BrpcDiagHitRow.interface_id,
                ),
            )
            .where(*filters)
            .group_by(
                window_start_timestamp,
                component,
                resolved_interface_id,
                interface_name,
                function_name,
            )
            .order_by(
                component,
                resolved_interface_id,
                window_start_timestamp,
            )
        )
        result = await session.execute(statement)
        return [dict(row) for row in result.mappings().all()]

    @staticmethod
    async def get_interface_timeline_bucket_aggregates(
        session: AsyncSession,
        *,
        batch_id: str | Sequence[str],
        start_timestamp: int,
        end_timestamp: int,
        window_us: int,
        interface_component: str | None = None,
        interface_id: str | None = None,
        pod_ip: str | None = None,
        pod_name: str | None = None,
    ) -> list[dict[str, Any]]:
        """Read fully-contained windows from the import-time bucket table."""
        filters = [
            BrpcDiagnosisPGManager._batch_filter(
                BrpcDiagInterfaceBucketRow.batch_id, batch_id
            ),
            BrpcDiagInterfaceBucketRow.window_seconds == window_us // 1_000_000,
            BrpcDiagInterfaceBucketRow.window_start_timestamp >= start_timestamp,
            BrpcDiagInterfaceBucketRow.window_start_timestamp < end_timestamp,
        ]
        if interface_component is not None:
            filters.append(
                BrpcDiagInterfaceBucketRow.component == interface_component
            )
        if interface_id is not None:
            filters.append(BrpcDiagInterfaceBucketRow.interface_id == interface_id)
        if pod_ip is not None:
            filters.append(BrpcDiagInterfaceBucketRow.pod_ip == pod_ip)
        if pod_name is not None:
            filters.append(BrpcDiagInterfaceBucketRow.pod_name == pod_name)

        statement = (
            select(
                BrpcDiagInterfaceBucketRow.window_start_timestamp,
                BrpcDiagInterfaceBucketRow.component,
                BrpcDiagInterfaceBucketRow.interface_id,
                BrpcDiagInterfaceBucketRow.interface_name,
                BrpcDiagInterfaceBucketRow.function_name,
                func.sum(BrpcDiagInterfaceBucketRow.interface_hit_count).label(
                    "interface_hit_count"
                ),
            )
            .where(*filters)
            .group_by(
                BrpcDiagInterfaceBucketRow.window_start_timestamp,
                BrpcDiagInterfaceBucketRow.component,
                BrpcDiagInterfaceBucketRow.interface_id,
                BrpcDiagInterfaceBucketRow.interface_name,
                BrpcDiagInterfaceBucketRow.function_name,
            )
            .order_by(
                BrpcDiagInterfaceBucketRow.component,
                BrpcDiagInterfaceBucketRow.interface_id,
                BrpcDiagInterfaceBucketRow.window_start_timestamp,
            )
        )
        result = await session.execute(statement)
        return [dict(row) for row in result.mappings().all()]

    @staticmethod
    async def rebuild_interface_timeline_buckets(
        session: AsyncSession,
        batch_id: str,
    ) -> None:
        """Build all four timeline granularities inside the import transaction."""
        # Match the startup migration for newly imported results: a failure
        # mode with exactly one candidate interface can be resolved immediately
        # and should appear in the component-specific overview without waiting
        # for a service restart.
        await session.execute(
            text(
                "UPDATE brpc_diag_hit AS hit "
                "SET interface_id = candidate.interface_id, "
                "interface_resolution = 'static_unique' "
                "FROM ("
                "SELECT schema_id, failure_mode_id, "
                "MIN(interface_id) AS interface_id "
                "FROM brpc_diag_failure_interface "
                "GROUP BY schema_id, failure_mode_id HAVING COUNT(*) = 1"
                ") AS candidate "
                "WHERE hit.batch_id = :batch_id "
                "AND hit.schema_id = candidate.schema_id "
                "AND hit.failure_mode_id = candidate.failure_mode_id "
                "AND hit.interface_id IS NULL"
            ),
            {"batch_id": batch_id},
        )
        await session.execute(
            delete(BrpcDiagInterfaceBucketRow).where(
                BrpcDiagInterfaceBucketRow.batch_id == batch_id
            )
        )
        for window_us in BRPC_TIMELINE_WINDOW_US:
            window_start_timestamp = (
                func.floor(cast(BrpcDiagHitRow.timestamp, Numeric) / window_us)
                * window_us
            )
            component = func.coalesce(BrpcDiagNodeRow.component, "unknown")
            interface_id = func.coalesce(
                BrpcDiagHitRow.interface_id, UNRESOLVED_INTERFACE_ID
            )
            interface_name = func.coalesce(
                BrpcDiagNodeRow.name, UNRESOLVED_INTERFACE_NAME
            )
            function_name = func.coalesce(BrpcDiagNodeRow.function_name, "")
            pod_ip = func.coalesce(BrpcDiagHitRow.pod_ip, "")
            pod_name = func.coalesce(BrpcDiagHitRow.pod_name, "")
            bucket_select = (
                select(
                    BrpcDiagHitRow.batch_id,
                    literal(window_us // 1_000_000),
                    window_start_timestamp,
                    component,
                    interface_id,
                    interface_name,
                    function_name,
                    pod_ip,
                    pod_name,
                    func.count(BrpcDiagHitRow.hit_id),
                )
                .select_from(BrpcDiagHitRow)
                .outerjoin(
                    BrpcDiagNodeRow,
                    and_(
                        BrpcDiagNodeRow.schema_id == BrpcDiagHitRow.schema_id,
                        BrpcDiagNodeRow.node_id == BrpcDiagHitRow.interface_id,
                    ),
                )
                .where(BrpcDiagHitRow.batch_id == batch_id)
                .group_by(
                    BrpcDiagHitRow.batch_id,
                    window_start_timestamp,
                    component,
                    interface_id,
                    interface_name,
                    function_name,
                    pod_ip,
                    pod_name,
                )
            )
            await session.execute(
                insert(BrpcDiagInterfaceBucketRow).from_select(
                    [
                        "batch_id",
                        "window_seconds",
                        "window_start_timestamp",
                        "component",
                        "interface_id",
                        "interface_name",
                        "function_name",
                        "pod_ip",
                        "pod_name",
                        "interface_hit_count",
                    ],
                    bucket_select,
                )
            )

    @staticmethod
    def _scope_filters(
        *,
        batch_id: str | Sequence[str],
        start_timestamp: int,
        end_timestamp: int,
        pod_ip: str | None = None,
        pod_name: str | None = None,
        thread_id: int | None = None,
    ) -> list[Any]:
        filters: list[Any] = [
            BrpcDiagnosisPGManager._batch_filter(BrpcDiagHitRow.batch_id, batch_id),
            BrpcDiagHitRow.timestamp >= start_timestamp,
            BrpcDiagHitRow.timestamp < end_timestamp,
        ]
        if pod_ip is not None:
            filters.append(BrpcDiagHitRow.pod_ip == pod_ip)
        if pod_name is not None:
            filters.append(BrpcDiagHitRow.pod_name == pod_name)
        if thread_id is not None:
            filters.append(BrpcDiagHitRow.thread_id == thread_id)
        return filters

    @staticmethod
    async def get_interface_hit_counts(
        session: AsyncSession,
        *,
        batch_id: str | Sequence[str],
        start_timestamp: int,
        end_timestamp: int,
        pod_ip: str | None = None,
        pod_name: str | None = None,
        thread_id: int | None = None,
    ) -> list[dict[str, Any]]:
        filters = BrpcDiagnosisPGManager._scope_filters(
            batch_id=batch_id,
            start_timestamp=start_timestamp,
            end_timestamp=end_timestamp,
            pod_ip=pod_ip,
            pod_name=pod_name,
            thread_id=thread_id,
        )
        component = func.coalesce(BrpcDiagNodeRow.component, "unknown")
        resolved_interface_id = func.coalesce(
            BrpcDiagHitRow.interface_id, UNRESOLVED_INTERFACE_ID
        )
        interface_name = func.coalesce(
            BrpcDiagNodeRow.name, UNRESOLVED_INTERFACE_NAME
        )
        function_name = func.coalesce(BrpcDiagNodeRow.function_name, "")
        result = await session.execute(
            select(
                component.label("component"),
                resolved_interface_id.label("interface_id"),
                interface_name.label("interface_name"),
                function_name.label("function_name"),
                func.count(BrpcDiagHitRow.hit_id).label("interface_hit_count"),
            )
            .select_from(BrpcDiagHitRow)
            .outerjoin(
                BrpcDiagNodeRow,
                and_(
                    BrpcDiagNodeRow.schema_id
                    == BrpcDiagHitRow.schema_id,
                    BrpcDiagNodeRow.node_id
                    == BrpcDiagHitRow.interface_id,
                ),
            )
            .where(*filters)
            .group_by(
                component,
                resolved_interface_id,
                interface_name,
                function_name,
            )
            .order_by(component, resolved_interface_id)
        )
        return [dict(row) for row in result.mappings().all()]

    @staticmethod
    async def get_failure_mode_hit_counts(
        session: AsyncSession,
        *,
        batch_id: str | Sequence[str],
        start_timestamp: int,
        end_timestamp: int,
        pod_ip: str | None = None,
        pod_name: str | None = None,
        thread_id: int | None = None,
    ) -> list[dict[str, Any]]:
        filters = BrpcDiagnosisPGManager._scope_filters(
            batch_id=batch_id,
            start_timestamp=start_timestamp,
            end_timestamp=end_timestamp,
            pod_ip=pod_ip,
            pod_name=pod_name,
            thread_id=thread_id,
        )
        result = await session.execute(
            select(
                BrpcDiagHitRow.failure_mode_id.label("failure_mode_id"),
                BrpcDiagNodeRow.component.label("component"),
                BrpcDiagNodeRow.name.label("failure_mode_name"),
                func.count(BrpcDiagHitRow.hit_id).label("hit_count"),
                func.array_agg(func.distinct(BrpcDiagHitRow.interface_id))
                .filter(BrpcDiagHitRow.interface_id.is_not(None))
                .label("interface_ids"),
                func.count(BrpcDiagHitRow.hit_id)
                .filter(BrpcDiagHitRow.interface_id.is_(None))
                .label("unresolved_hit_count"),
            )
            .select_from(BrpcDiagHitRow)
            .join(
                BrpcDiagNodeRow,
                and_(
                    BrpcDiagNodeRow.schema_id == BrpcDiagHitRow.schema_id,
                    BrpcDiagNodeRow.node_id
                    == BrpcDiagHitRow.failure_mode_id,
                ),
            )
            .where(*filters, BrpcDiagNodeRow.node_type == "failure_mode")
            .group_by(
                BrpcDiagHitRow.failure_mode_id,
                BrpcDiagNodeRow.component,
                BrpcDiagNodeRow.name,
            )
            .order_by(BrpcDiagNodeRow.component, BrpcDiagHitRow.failure_mode_id)
        )
        return [dict(row) for row in result.mappings().all()]

    @staticmethod
    def _window_start_timestamp(window_us: int):
        return (
            func.floor(cast(BrpcDiagHitRow.timestamp, Numeric) / window_us)
            * window_us
        )

    @staticmethod
    def _hit_metric_expression(sort_field: BrpcMetricSortField):
        if sort_field.field == BRPC_TOTAL_SORT_FIELD:
            return func.count(BrpcDiagHitRow.hit_id)
        condition = (
            or_(
                BrpcDiagHitRow.interface_id.is_(None),
                BrpcDiagHitRow.interface_id == UNRESOLVED_INTERFACE_ID,
            )
            if sort_field.field == UNRESOLVED_INTERFACE_ID
            else BrpcDiagHitRow.interface_id == sort_field.field
        )
        return func.count(BrpcDiagHitRow.hit_id).filter(condition)

    @staticmethod
    def _sort_expression(expression, order: BrpcSortOrder):
        return expression.desc() if order == "desc" else expression.asc()

    @staticmethod
    async def list_pod_events(
        session: AsyncSession,
        *,
        batch_id: str | Sequence[str],
        start_timestamp: int,
        end_timestamp: int,
        window_us: int,
        sort_order: BrpcSortOrder = "asc",
        metric_sort_fields: Sequence[BrpcMetricSortField] = (),
        page_num: int,
        page_cnt: int,
        pod_ip: str | None = None,
        pod_name: str | None = None,
    ) -> tuple[int, list[dict[str, Any]]]:
        window_start_timestamp = (
            BrpcDiagnosisPGManager._window_start_timestamp(window_us).label(
                "window_start_timestamp"
            )
        )
        scope = BrpcDiagnosisPGManager._scope_filters(
            batch_id=batch_id,
            start_timestamp=start_timestamp,
            end_timestamp=end_timestamp,
            pod_ip=pod_ip,
            pod_name=pod_name,
        )
        metric_columns = [
            BrpcDiagnosisPGManager._hit_metric_expression(sort_field).label(
                f"sort_metric_{index}"
            )
            for index, sort_field in enumerate(metric_sort_fields)
        ]
        window_keys = (
            select(
                BrpcDiagHitRow.batch_id.label("batch_id"),
                window_start_timestamp,
                *metric_columns,
            )
            .where(*scope, BrpcDiagHitRow.pod_ip.is_not(None))
            .group_by(BrpcDiagHitRow.batch_id, window_start_timestamp)
            .subquery()
        )
        total_result = await session.execute(
            select(func.count()).select_from(window_keys)
        )
        window_metric_order = [
            BrpcDiagnosisPGManager._sort_expression(
                window_keys.c[f"sort_metric_{index}"],
                sort_field.order,
            )
            for index, sort_field in enumerate(metric_sort_fields)
        ]
        window_time_order = BrpcDiagnosisPGManager._sort_expression(
            window_keys.c.window_start_timestamp,
            sort_order,
        )
        paged_windows = (
            select(window_keys.c.batch_id, window_keys.c.window_start_timestamp)
            .add_columns(
                *[
                    window_keys.c[f"sort_metric_{index}"]
                    for index in range(len(metric_sort_fields))
                ]
            )
            .order_by(*window_metric_order, window_time_order, window_keys.c.batch_id)
            .limit(page_cnt)
            .offset((page_num - 1) * page_cnt)
            .subquery()
        )

        component = func.coalesce(BrpcDiagNodeRow.component, "unknown")
        resolved_interface_id = func.coalesce(
            BrpcDiagHitRow.interface_id, UNRESOLVED_INTERFACE_ID
        )
        interface_name = func.coalesce(
            BrpcDiagNodeRow.name, UNRESOLVED_INTERFACE_NAME
        )
        function_name = func.coalesce(BrpcDiagNodeRow.function_name, "")
        interface_rows = (
            select(
                BrpcDiagHitRow.batch_id.label("batch_id"),
                window_start_timestamp,
                BrpcDiagHitRow.pod_ip.label("pod_ip"),
                func.max(BrpcDiagHitRow.pod_name).label("pod_name"),
                component.label("component"),
                resolved_interface_id.label("interface_id"),
                interface_name.label("interface_name"),
                function_name.label("function_name"),
                func.count(BrpcDiagHitRow.hit_id).label("interface_hit_count"),
            )
            .select_from(BrpcDiagHitRow)
            .outerjoin(
                BrpcDiagNodeRow,
                and_(
                    BrpcDiagNodeRow.schema_id
                    == BrpcDiagHitRow.schema_id,
                    BrpcDiagNodeRow.node_id
                    == BrpcDiagHitRow.interface_id,
                ),
            )
            .where(
                *scope,
                BrpcDiagHitRow.pod_ip.is_not(None),
            )
            .group_by(
                BrpcDiagHitRow.batch_id,
                window_start_timestamp,
                BrpcDiagHitRow.pod_ip,
                component,
                resolved_interface_id,
                interface_name,
                function_name,
            )
            .subquery()
        )
        statement = (
            select(
                interface_rows.c.batch_id,
                interface_rows.c.window_start_timestamp,
                interface_rows.c.pod_ip,
                func.max(interface_rows.c.pod_name).label("pod_name"),
                func.jsonb_agg(
                    func.jsonb_build_object(
                        "component",
                        interface_rows.c.component,
                        "interface_id",
                        interface_rows.c.interface_id,
                        "interface_name",
                        interface_rows.c.interface_name,
                        "function_name",
                        interface_rows.c.function_name,
                        "interface_hit_count",
                        interface_rows.c.interface_hit_count,
                    )
                ).label("interface_hits"),
            )
            .join(
                paged_windows,
                and_(
                    interface_rows.c.batch_id == paged_windows.c.batch_id,
                    interface_rows.c.window_start_timestamp
                    == paged_windows.c.window_start_timestamp,
                ),
            )
            .group_by(
                interface_rows.c.batch_id,
                interface_rows.c.window_start_timestamp,
                interface_rows.c.pod_ip,
                *[
                    paged_windows.c[f"sort_metric_{index}"]
                    for index in range(len(metric_sort_fields))
                ],
            )
            .order_by(
                *[
                    BrpcDiagnosisPGManager._sort_expression(
                        paged_windows.c[f"sort_metric_{index}"],
                        sort_field.order,
                    )
                    for index, sort_field in enumerate(metric_sort_fields)
                ],
                BrpcDiagnosisPGManager._sort_expression(
                    interface_rows.c.window_start_timestamp,
                    sort_order,
                ),
                interface_rows.c.batch_id,
                interface_rows.c.pod_ip,
            )
        )
        rows_result = await session.execute(statement)
        return int(total_result.scalar_one()), [
            dict(row) for row in rows_result.mappings().all()
        ]

    @staticmethod
    async def list_thread_events(
        session: AsyncSession,
        *,
        batch_id: str | Sequence[str],
        start_timestamp: int,
        end_timestamp: int,
        window_us: int,
        sort_order: BrpcSortOrder = "asc",
        metric_sort_fields: Sequence[BrpcMetricSortField] = (),
        page_num: int,
        page_cnt: int,
        pod_ip: str | None = None,
        pod_name: str | None = None,
    ) -> tuple[int, list[dict[str, Any]]]:
        window_start_timestamp = (
            BrpcDiagnosisPGManager._window_start_timestamp(window_us).label(
                "window_start_timestamp"
            )
        )
        scope = BrpcDiagnosisPGManager._scope_filters(
            batch_id=batch_id,
            start_timestamp=start_timestamp,
            end_timestamp=end_timestamp,
            pod_ip=pod_ip,
            pod_name=pod_name,
        )
        required = [
            BrpcDiagHitRow.pod_ip.is_not(None),
            BrpcDiagHitRow.thread_id.is_not(None),
        ]
        metric_columns = [
            BrpcDiagnosisPGManager._hit_metric_expression(sort_field).label(
                f"sort_metric_{index}"
            )
            for index, sort_field in enumerate(metric_sort_fields)
        ]
        window_keys = (
            select(
                BrpcDiagHitRow.batch_id.label("batch_id"),
                window_start_timestamp,
                *metric_columns,
            )
            .where(*scope, *required)
            .group_by(BrpcDiagHitRow.batch_id, window_start_timestamp)
            .subquery()
        )
        total_result = await session.execute(
            select(func.count()).select_from(window_keys)
        )
        window_metric_order = [
            BrpcDiagnosisPGManager._sort_expression(
                window_keys.c[f"sort_metric_{index}"],
                sort_field.order,
            )
            for index, sort_field in enumerate(metric_sort_fields)
        ]
        window_time_order = BrpcDiagnosisPGManager._sort_expression(
            window_keys.c.window_start_timestamp,
            sort_order,
        )
        paged_windows = (
            select(window_keys.c.batch_id, window_keys.c.window_start_timestamp)
            .add_columns(
                *[
                    window_keys.c[f"sort_metric_{index}"]
                    for index in range(len(metric_sort_fields))
                ]
            )
            .order_by(*window_metric_order, window_time_order, window_keys.c.batch_id)
            .limit(page_cnt)
            .offset((page_num - 1) * page_cnt)
            .subquery()
        )

        component = func.coalesce(BrpcDiagNodeRow.component, "unknown")
        resolved_interface_id = func.coalesce(
            BrpcDiagHitRow.interface_id, UNRESOLVED_INTERFACE_ID
        )
        interface_name = func.coalesce(
            BrpcDiagNodeRow.name, UNRESOLVED_INTERFACE_NAME
        )
        function_name = func.coalesce(BrpcDiagNodeRow.function_name, "")
        interface_rows = (
            select(
                BrpcDiagHitRow.batch_id.label("batch_id"),
                window_start_timestamp,
                BrpcDiagHitRow.pod_ip.label("pod_ip"),
                func.max(BrpcDiagHitRow.pod_name).label("pod_name"),
                BrpcDiagHitRow.thread_id.label("thread_id"),
                component.label("component"),
                resolved_interface_id.label("interface_id"),
                interface_name.label("interface_name"),
                function_name.label("function_name"),
                func.count(BrpcDiagHitRow.hit_id).label("interface_hit_count"),
            )
            .select_from(BrpcDiagHitRow)
            .outerjoin(
                BrpcDiagNodeRow,
                and_(
                    BrpcDiagNodeRow.schema_id
                    == BrpcDiagHitRow.schema_id,
                    BrpcDiagNodeRow.node_id
                    == BrpcDiagHitRow.interface_id,
                ),
            )
            .where(*scope, *required)
            .group_by(
                BrpcDiagHitRow.batch_id,
                window_start_timestamp,
                BrpcDiagHitRow.pod_ip,
                BrpcDiagHitRow.thread_id,
                component,
                resolved_interface_id,
                interface_name,
                function_name,
            )
            .subquery()
        )
        statement = (
            select(
                interface_rows.c.batch_id,
                interface_rows.c.window_start_timestamp,
                interface_rows.c.pod_ip,
                func.max(interface_rows.c.pod_name).label("pod_name"),
                interface_rows.c.thread_id,
                func.jsonb_agg(
                    func.jsonb_build_object(
                        "component",
                        interface_rows.c.component,
                        "interface_id",
                        interface_rows.c.interface_id,
                        "interface_name",
                        interface_rows.c.interface_name,
                        "function_name",
                        interface_rows.c.function_name,
                        "interface_hit_count",
                        interface_rows.c.interface_hit_count,
                    )
                ).label("interface_hits"),
            )
            .join(
                paged_windows,
                and_(
                    interface_rows.c.batch_id == paged_windows.c.batch_id,
                    interface_rows.c.window_start_timestamp
                    == paged_windows.c.window_start_timestamp,
                ),
            )
            .group_by(
                interface_rows.c.batch_id,
                interface_rows.c.window_start_timestamp,
                interface_rows.c.pod_ip,
                interface_rows.c.thread_id,
                *[
                    paged_windows.c[f"sort_metric_{index}"]
                    for index in range(len(metric_sort_fields))
                ],
            )
            .order_by(
                *[
                    BrpcDiagnosisPGManager._sort_expression(
                        paged_windows.c[f"sort_metric_{index}"],
                        sort_field.order,
                    )
                    for index, sort_field in enumerate(metric_sort_fields)
                ],
                BrpcDiagnosisPGManager._sort_expression(
                    interface_rows.c.window_start_timestamp,
                    sort_order,
                ),
                interface_rows.c.batch_id,
                interface_rows.c.pod_ip,
                interface_rows.c.thread_id,
            )
        )
        rows_result = await session.execute(statement)
        return int(total_result.scalar_one()), [
            dict(row) for row in rows_result.mappings().all()
        ]

    @staticmethod
    async def list_abnormal_threads(
        session: AsyncSession,
        *,
        batch_id: str | Sequence[str],
        start_timestamp: int,
        end_timestamp: int,
        page_num: int,
        page_cnt: int,
        pod_ip: str | None = None,
        pod_name: str | None = None,
        thread_id: int | None = None,
        search: str | None = None,
        metric_sort_fields: Sequence[BrpcMetricSortField] = (),
    ) -> tuple[int, list[dict[str, Any]]]:
        scope = BrpcDiagnosisPGManager._scope_filters(
            batch_id=batch_id,
            start_timestamp=start_timestamp,
            end_timestamp=end_timestamp,
            pod_ip=pod_ip,
            pod_name=pod_name,
            thread_id=thread_id,
        )
        if search:
            escaped_search = (
                search.replace("\\", "\\\\")
                .replace("%", "\\%")
                .replace("_", "\\_")
            )
            search_pattern = f"%{escaped_search}%"
            scope.append(
                or_(
                    cast(BrpcDiagHitRow.thread_id, String).ilike(
                        search_pattern,
                        escape="\\",
                    ),
                    BrpcDiagHitRow.pod_ip.ilike(search_pattern, escape="\\"),
                    BrpcDiagHitRow.pod_name.ilike(search_pattern, escape="\\"),
                )
            )
        required = [
            BrpcDiagHitRow.pod_ip.is_not(None),
            BrpcDiagHitRow.thread_id.is_not(None),
        ]
        keys = (
            select(
                BrpcDiagHitRow.batch_id,
                BrpcDiagHitRow.pod_ip,
                BrpcDiagHitRow.thread_id,
            )
            .where(*scope, *required)
            .group_by(
                BrpcDiagHitRow.batch_id,
                BrpcDiagHitRow.pod_ip,
                BrpcDiagHitRow.thread_id,
            )
            .subquery()
        )
        total_result = await session.execute(select(func.count()).select_from(keys))
        component = func.coalesce(BrpcDiagNodeRow.component, "unknown")
        resolved_interface_id = func.coalesce(
            BrpcDiagHitRow.interface_id, UNRESOLVED_INTERFACE_ID
        )
        interface_name = func.coalesce(
            BrpcDiagNodeRow.name, UNRESOLVED_INTERFACE_NAME
        )
        function_name = func.coalesce(BrpcDiagNodeRow.function_name, "")
        interface_rows = (
            select(
                BrpcDiagHitRow.batch_id.label("batch_id"),
                BrpcDiagHitRow.pod_ip.label("pod_ip"),
                func.max(BrpcDiagHitRow.pod_name).label("pod_name"),
                BrpcDiagHitRow.thread_id.label("thread_id"),
                func.min(BrpcDiagHitRow.timestamp).label("first_hit_timestamp"),
                func.max(BrpcDiagHitRow.timestamp).label("last_hit_timestamp"),
                component.label("component"),
                resolved_interface_id.label("interface_id"),
                interface_name.label("interface_name"),
                function_name.label("function_name"),
                func.count(BrpcDiagHitRow.hit_id).label("interface_hit_count"),
            )
            .select_from(BrpcDiagHitRow)
            .outerjoin(
                BrpcDiagNodeRow,
                and_(
                    BrpcDiagNodeRow.schema_id
                    == BrpcDiagHitRow.schema_id,
                    BrpcDiagNodeRow.node_id
                    == BrpcDiagHitRow.interface_id,
                ),
            )
            .where(*scope, *required)
            .group_by(
                BrpcDiagHitRow.batch_id,
                BrpcDiagHitRow.pod_ip,
                BrpcDiagHitRow.thread_id,
                component,
                resolved_interface_id,
                interface_name,
                function_name,
            )
            .subquery()
        )
        metric_order = []
        for sort_field in metric_sort_fields:
            metric_value = func.sum(interface_rows.c.interface_hit_count)
            if sort_field.field != BRPC_TOTAL_SORT_FIELD:
                metric_value = func.coalesce(
                    metric_value.filter(
                        interface_rows.c.interface_id == sort_field.field
                    ),
                    0,
                )
            metric_order.append(
                BrpcDiagnosisPGManager._sort_expression(
                    metric_value,
                    sort_field.order,
                )
            )
        statement = (
            select(
                interface_rows.c.batch_id,
                interface_rows.c.pod_ip,
                func.max(interface_rows.c.pod_name).label("pod_name"),
                interface_rows.c.thread_id,
                func.min(interface_rows.c.first_hit_timestamp).label(
                    "first_hit_timestamp"
                ),
                func.max(interface_rows.c.last_hit_timestamp).label(
                    "last_hit_timestamp"
                ),
                func.sum(interface_rows.c.interface_hit_count).label(
                    "total_interface_hit_count"
                ),
                func.jsonb_agg(
                    func.jsonb_build_object(
                        "component",
                        interface_rows.c.component,
                        "interface_id",
                        interface_rows.c.interface_id,
                        "interface_name",
                        interface_rows.c.interface_name,
                        "function_name",
                        interface_rows.c.function_name,
                        "interface_hit_count",
                        interface_rows.c.interface_hit_count,
                    )
                ).label("interface_hits"),
            )
            .group_by(
                interface_rows.c.batch_id,
                interface_rows.c.pod_ip,
                interface_rows.c.thread_id,
            )
            .order_by(
                *metric_order,
                func.max(interface_rows.c.last_hit_timestamp).desc(),
                interface_rows.c.batch_id,
                interface_rows.c.pod_ip,
                interface_rows.c.thread_id,
            )
            .limit(page_cnt)
            .offset((page_num - 1) * page_cnt)
        )
        result = await session.execute(statement)
        return int(total_result.scalar_one()), [
            dict(row) for row in result.mappings().all()
        ]

    @staticmethod
    async def get_schema(
        session: AsyncSession, schema_id: str
    ) -> BrpcDiagSchema | None:
        schema_row = await session.get(BrpcDiagSchemaRow, schema_id)
        if schema_row is None:
            return None

        node_result = await session.execute(
            select(BrpcDiagNodeRow)
            .where(BrpcDiagNodeRow.schema_id == schema_id)
            .order_by(BrpcDiagNodeRow.node_id)
        )
        edge_result = await session.execute(
            select(BrpcDiagEdgeRow)
            .where(BrpcDiagEdgeRow.schema_id == schema_id)
            .order_by(
                BrpcDiagEdgeRow.source_node_id,
                BrpcDiagEdgeRow.target_node_id,
                BrpcDiagEdgeRow.edge_type,
            )
        )
        mapping_result = await session.execute(
            select(BrpcDiagFailureInterfaceRow)
            .where(BrpcDiagFailureInterfaceRow.schema_id == schema_id)
            .order_by(
                BrpcDiagFailureInterfaceRow.failure_mode_id,
                BrpcDiagFailureInterfaceRow.interface_id,
            )
        )
        subgraph_result = await session.execute(
            select(BrpcDiagFailureSubgraphRow)
            .where(BrpcDiagFailureSubgraphRow.schema_id == schema_id)
            .order_by(BrpcDiagFailureSubgraphRow.failure_mode_id)
        )

        nodes = [
            BrpcDiagNode(
                node_id=row.node_id,
                node_type=row.node_type,
                component=row.component,
                name=row.name,
                filename=row.filename,
                function_name=row.function_name,
                phenomenon=row.phenomenon,
                cause=row.cause,
                solution=row.solution,
                error_code=row.error_code,
            )
            for row in node_result.scalars().all()
        ]
        edges = [
            BrpcDiagEdge(
                source_node_id=row.source_node_id,
                target_node_id=row.target_node_id,
                edge_type=row.edge_type,
            )
            for row in edge_result.scalars().all()
        ]
        interface_ids_by_failure: dict[str, list[str]] = defaultdict(list)
        for row in mapping_result.scalars().all():
            interface_ids_by_failure[row.failure_mode_id].append(row.interface_id)
        subgraph_edges_by_failure = {
            row.failure_mode_id: list(row.subgraph_edge_indexes)
            for row in subgraph_result.scalars().all()
        }
        mappings = [
            BrpcFailureInterface(
                failure_mode_id=failure_mode_id,
                interface_ids=interface_ids,
                subgraph_edge_indexes=subgraph_edges_by_failure[
                    failure_mode_id
                ],
            )
            for failure_mode_id, interface_ids in sorted(
                interface_ids_by_failure.items()
            )
        ]
        return BrpcDiagSchema(
            format_version=schema_row.format_version,
            schema_id=schema_row.schema_id,
            nodes=nodes,
            edges=edges,
            failure_interface_mappings=mappings,
        )

    @staticmethod
    async def add_schema(
        session: AsyncSession, schema: BrpcDiagSchema
    ) -> None:
        # SQLAlchemy cannot infer the required insert order here because these
        # models do not declare ORM relationships.  Flush each FK layer while
        # keeping all layers in the caller-owned transaction.
        session.add_all(
            [
                BrpcDiagSchemaRow(
                    schema_id=schema.schema_id,
                    format_version=schema.format_version,
                )
            ]
        )
        await session.flush()

        node_rows = [
            BrpcDiagNodeRow(
                schema_id=schema.schema_id,
                node_id=node.node_id,
                node_type=node.node_type,
                component=node.component,
                name=node.name,
                filename=node.filename,
                function_name=node.function_name,
                phenomenon=node.phenomenon,
                cause=node.cause,
                solution=node.solution,
                error_code=node.error_code,
            )
            for node in schema.nodes
        ]
        session.add_all(node_rows)
        await session.flush()

        dependent_rows: list[object] = [
            BrpcDiagEdgeRow(
                schema_id=schema.schema_id,
                source_node_id=edge.source_node_id,
                target_node_id=edge.target_node_id,
                edge_type=edge.edge_type,
            )
            for edge in schema.edges
        ]
        dependent_rows.extend(
            BrpcDiagFailureInterfaceRow(
                schema_id=schema.schema_id,
                failure_mode_id=mapping.failure_mode_id,
                interface_id=interface_id,
            )
            for mapping in schema.failure_interface_mappings
            for interface_id in mapping.interface_ids
        )
        dependent_rows.extend(
            BrpcDiagFailureSubgraphRow(
                schema_id=schema.schema_id,
                failure_mode_id=mapping.failure_mode_id,
                subgraph_edge_indexes=mapping.subgraph_edge_indexes,
            )
            for mapping in schema.failure_interface_mappings
        )
        session.add_all(dependent_rows)
        await session.flush()

    @staticmethod
    async def add_batch(
        session: AsyncSession,
        batch: BrpcDiagBatch,
        hits: Sequence[BrpcDiagHit],
    ) -> None:
        session.add_all(
            [
                BrpcDiagBatchRow(
                    batch_id=batch.batch_id,
                    task_id=batch.task_id,
                    schema_id=batch.schema_id,
                    created_at_timestamp=batch.created_at_timestamp,
                    start_timestamp=batch.start_timestamp,
                    end_timestamp=batch.end_timestamp,
                    hit_count=batch.hit_count,
                )
            ]
        )
        await session.flush()

        hit_rows = [
            BrpcDiagHitRow(
                hit_id=hit.hit_id,
                batch_id=batch.batch_id,
                schema_id=batch.schema_id,
                failure_mode_id=hit.failure_mode_id,
                interface_id=hit.interface_id,
                interface_resolution=hit.interface_resolution,
                timestamp=hit.timestamp,
                pod_name=hit.pod_name,
                pod_ip=hit.pod_ip,
                component=hit.component,
                filename=hit.filename,
                function_name=hit.function_name,
                line_number=hit.line_number,
                thread_id=hit.thread_id,
                trace_id=hit.trace_id,
                message=hit.message,
            )
            for hit in hits
        ]
        session.add_all(hit_rows)
        await session.flush()
        await BrpcDiagnosisPGManager.rebuild_interface_timeline_buckets(
            session, batch.batch_id
        )

    @staticmethod
    async def delete_batch(session: AsyncSession, batch_id: str) -> bool:
        result = await session.execute(
            delete(BrpcDiagBatchRow)
            .where(BrpcDiagBatchRow.batch_id == batch_id)
            .returning(BrpcDiagBatchRow.batch_id)
        )
        return result.scalar_one_or_none() is not None

    @staticmethod
    async def delete_batch_by_task_id(
        session: AsyncSession, task_id: str
    ) -> str | None:
        result = await session.execute(
            delete(BrpcDiagBatchRow)
            .where(BrpcDiagBatchRow.task_id == task_id)
            .returning(BrpcDiagBatchRow.batch_id)
        )
        return result.scalar_one_or_none()
