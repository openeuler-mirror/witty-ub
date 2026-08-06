# Copyright (c) Huawei Technologies Co., Ltd. 2023-2025. All rights reserved.
"""PostgreSQL-specific manager for anomalous_event_chain."""
from __future__ import annotations

import logging
import time
from typing import Any

from sqlalchemy import desc, func, select, text
from sqlalchemy.dialects.postgresql import insert

from latency.database.engine import PGManager
from latency.database.models import AnomalousEventChain, LogFile
from latency.database.utils import format_timestamp, parse_timestamp
from latency.schemas.log import AnomalousEventChainModel
from latency.schemas.request import ListAnomalousEventChainRequest

logger = logging.getLogger(__name__)


class AnomalousEventChainPGManager:
    _COPY_THRESHOLD = 1_000
    _COPY_BATCH_SIZE = 50_000

    _COPY_COLUMNS = [
        "id",
        "log_id",
        "anomalous_event_id",
        "name",
        "description",
        "anomaly_code",
        "offset",
        "existed_status",
        "created_at",
    ]

    @staticmethod
    def _chain_to_mapping(chain: AnomalousEventChainModel) -> dict[str, Any]:
        return {
            "id": chain.id,
            "log_id": chain.log_id,
            "anomalous_event_id": chain.anomalous_event_id,
            "name": chain.name,
            "description": chain.description,
            "anomaly_code": chain.anomaly_code,
            "offset": chain.offset,
            "existed_status": chain.existed_status,
            "created_at": parse_timestamp(chain.created_at),
        }

    @staticmethod
    def _chain_to_copy_tuple(chain: AnomalousEventChainModel) -> tuple[Any, ...]:
        return (
            chain.id,
            chain.log_id,
            chain.anomalous_event_id,
            chain.name,
            chain.description,
            chain.anomaly_code,
            chain.offset,
            chain.existed_status,
            parse_timestamp(chain.created_at),
        )

    @staticmethod
    def _row_to_model(row: Any) -> AnomalousEventChainModel:
        data = {
            "id": row.id,
            "log_id": row.log_id,
            "anomalous_event_id": row.anomalous_event_id,
            "name": row.name,
            "description": row.description,
            "anomaly_code": row.anomaly_code,
            "offset": row.offset,
            "existed_status": row.existed_status,
            "created_at": format_timestamp(row.created_at),
        }
        return AnomalousEventChainModel(**data)

    @staticmethod
    async def add_event_chains(
        chains: list[AnomalousEventChainModel],
    ) -> list[str]:
        if not chains:
            return []
        if len(chains) >= AnomalousEventChainPGManager._COPY_THRESHOLD:
            return await AnomalousEventChainPGManager._add_event_chains_copy(chains)
        mappings = [AnomalousEventChainPGManager._chain_to_mapping(c) for c in chains]
        async with PGManager.session() as session:
            await session.execute(insert(AnomalousEventChain), mappings)
        return [c.id for c in chains]

    @staticmethod
    async def _add_event_chains_copy(
        chains: list[AnomalousEventChainModel],
    ) -> list[str]:
        t_start = time.perf_counter()
        records = [AnomalousEventChainPGManager._chain_to_copy_tuple(c) for c in chains]
        async with PGManager.connection() as conn:
            raw_conn = await conn.get_raw_connection()
            asyncpg_conn = raw_conn.driver_connection
            for i in range(0, len(records), AnomalousEventChainPGManager._COPY_BATCH_SIZE):
                batch = records[i : i + AnomalousEventChainPGManager._COPY_BATCH_SIZE]
                await asyncpg_conn.copy_records_to_table(
                    "anomalous_event_chain",
                    records=batch,
                    columns=AnomalousEventChainPGManager._COPY_COLUMNS,
                )
        logger.info(
            "[Store][PG] COPY %s anomalous_event_chain rows done in %.3fs",
            len(chains),
            time.perf_counter() - t_start,
        )
        return [c.id for c in chains]

    @staticmethod
    async def update_event_chains_existed_status_by_log_id(
        log_id: str, existed_status: int
    ) -> bool:
        async with PGManager.session() as session:
            await session.execute(
                text(
                    "UPDATE anomalous_event_chain SET existed_status = :existed_status "
                    "WHERE log_id = :log_id"
                ),
                {"log_id": log_id, "existed_status": bool(existed_status)},
            )
        return True

    @staticmethod
    async def delete_event_chains_by_log_id(log_id: str) -> bool:
        """Hard delete all event chains for a log_id."""
        async with PGManager.session() as session:
            await session.execute(
                text("DELETE FROM anomalous_event_chain WHERE log_id = :log_id"),
                {"log_id": log_id},
            )
        return True

    @staticmethod
    async def list_event_chains(
        req: ListAnomalousEventChainRequest,
    ) -> tuple[int, list[AnomalousEventChainModel]]:
        stmt = select(AnomalousEventChain).where(
            AnomalousEventChain.existed_status.is_(True)
        )
        if req.log_id:
            stmt = stmt.where(AnomalousEventChain.log_id == req.log_id)
        if req.kb_id:
            stmt = stmt.join(LogFile, AnomalousEventChain.log_id == LogFile.id).where(
                LogFile.kb_id == req.kb_id
            )

        count_stmt = select(func.count()).select_from(stmt.subquery())
        async with PGManager.session() as session:
            total = (await session.execute(count_stmt)).scalar() or 0

        stmt = stmt.order_by(desc(AnomalousEventChain.created_at))
        offset = (req.page_num - 1) * req.page_cnt
        stmt = stmt.offset(offset).limit(req.page_cnt)

        async with PGManager.session() as session:
            result = await session.execute(stmt)
            rows = result.scalars().all()
        return total, [AnomalousEventChainPGManager._row_to_model(r) for r in rows]

    @staticmethod
    async def list_event_chains_by_log_id(
        log_id: str,
    ) -> list[AnomalousEventChainModel]:
        async with PGManager.session() as session:
            result = await session.execute(
                select(AnomalousEventChain)
                .where(
                    AnomalousEventChain.log_id == log_id,
                    AnomalousEventChain.existed_status.is_(True),
                )
                .order_by(AnomalousEventChain.offset, desc(AnomalousEventChain.created_at))
            )
            rows = result.scalars().all()
        return [AnomalousEventChainPGManager._row_to_model(r) for r in rows]

    @staticmethod
    async def get_event_chain_by_id(
        chain_id: str,
    ) -> AnomalousEventChainModel | None:
        async with PGManager.session() as session:
            result = await session.execute(
                select(AnomalousEventChain).where(AnomalousEventChain.id == chain_id)
            )
            row = result.scalar_one_or_none()
        if row is None:
            return None
        return AnomalousEventChainPGManager._row_to_model(row)
