# Copyright (c) Huawei Technologies Co., Ltd. 2023-2025. All rights reserved.
"""PostgreSQL manager for mami 硬件日志事实表。

解析期由 ``KVCacheLogParseWorker`` 调用 ``replace_scan`` 落库窗口内的 mami 事实
（``mami_fault_event`` + ``mami_scan_summary``）；召回期通过 ``get_summary`` /
``list_events`` 查询。本 manager 不参与任何判断逻辑。
"""
from __future__ import annotations

import logging
import uuid
from datetime import datetime

from latency.database.engine import PGManager
from latency.database.models import MamiFaultEvent, MamiScanSummary
from latency.parse.mami_log_parser import MAMI_HARDWARE_CATEGORIES, MamiEvent
from sqlalchemy import delete, func, select

logger = logging.getLogger(__name__)

_INSERT_BATCH = 1_000


class MamiFaultEventPGManager:
    """mami_fault_event / mami_scan_summary 读写。"""

    @staticmethod
    async def replace_scan(
        summary: dict,
        events: list[MamiEvent],
    ) -> None:
        """写入（覆盖式）某个 log_id 的 mami 扫描结果。

        同一 log_id 重解析时先清后写，保证幂等。
        """
        log_id = summary["log_id"]
        rows = [
            {
                "id": str(uuid.uuid4()),
                "log_id": log_id,
                "kb_id": summary.get("kb_id") or "",
                "host_name": event.host_name or "",
                "source_file": event.source_file or "",
                "timestamp": event.timestamp,
                "level": event.level or "",
                "category": event.category or "",
                "signal": event.signal or "",
                "message": event.message or "",
            }
            for event in events
        ]
        summary_row = {
            "log_id": log_id,
            "kb_id": summary.get("kb_id") or "",
            "window_start": summary.get("window_start"),
            "window_end": summary.get("window_end"),
            "mami_files_found": int(summary.get("mami_files_found") or 0),
            "covered": summary.get("covered"),
            "event_count": int(summary.get("event_count") or 0),
            "hardware_event_count": int(summary.get("hardware_event_count") or 0),
        }
        async with PGManager.session() as session:
            await session.execute(
                delete(MamiFaultEvent).where(MamiFaultEvent.log_id == log_id)
            )
            await session.execute(
                delete(MamiScanSummary).where(MamiScanSummary.log_id == log_id)
            )
            for start in range(0, len(rows), _INSERT_BATCH):
                await session.execute(
                    MamiFaultEvent.__table__.insert(),
                    rows[start : start + _INSERT_BATCH],
                )
            await session.execute(MamiScanSummary.__table__.insert(), summary_row)

    @staticmethod
    async def delete_by_log_id(log_id: str) -> bool:
        """删除指定日志的 mami 扫描结果与事件。"""
        async with PGManager.session() as session:
            await session.execute(
                delete(MamiFaultEvent).where(MamiFaultEvent.log_id == log_id)
            )
            await session.execute(
                delete(MamiScanSummary).where(MamiScanSummary.log_id == log_id)
            )
        return True

    @staticmethod
    async def get_summary(log_id: str) -> dict | None:
        stmt = select(MamiScanSummary).where(MamiScanSummary.log_id == log_id)
        async with PGManager.session() as session:
            row = (await session.execute(stmt)).scalar_one_or_none()
        return MamiFaultEventPGManager._summary_to_dict(row) if row else None

    @staticmethod
    async def list_events(
        log_id: str | None = None,
        kb_id: str | None = None,
        categories: list[str] | None = None,
        hardware_only: bool = False,
        start: datetime | None = None,
        end: datetime | None = None,
        limit: int = 2_000,
    ) -> list[dict]:
        """按条件列出 mami 故障事实（供召回期定界使用）。"""
        stmt = select(MamiFaultEvent)
        if log_id:
            stmt = stmt.where(MamiFaultEvent.log_id == log_id)
        if kb_id:
            stmt = stmt.where(MamiFaultEvent.kb_id == kb_id)
        if categories:
            stmt = stmt.where(MamiFaultEvent.category.in_(categories))
        if hardware_only:
            stmt = stmt.where(
                MamiFaultEvent.category.in_(list(MAMI_HARDWARE_CATEGORIES))
            )
        if start is not None:
            stmt = stmt.where(MamiFaultEvent.timestamp >= start)
        if end is not None:
            stmt = stmt.where(MamiFaultEvent.timestamp <= end)
        stmt = stmt.order_by(MamiFaultEvent.timestamp.asc()).limit(limit)
        async with PGManager.session() as session:
            rows = (await session.execute(stmt)).scalars().all()
        return [MamiFaultEventPGManager._event_to_dict(row) for row in rows]

    @staticmethod
    async def count_events(log_id: str) -> int:
        stmt = select(func.count()).select_from(MamiFaultEvent).where(
            MamiFaultEvent.log_id == log_id
        )
        async with PGManager.session() as session:
            return int((await session.execute(stmt)).scalar() or 0)

    @staticmethod
    def _summary_to_dict(row: MamiScanSummary) -> dict:
        return {
            "log_id": row.log_id,
            "kb_id": row.kb_id,
            "window_start": row.window_start,
            "window_end": row.window_end,
            "mami_files_found": row.mami_files_found,
            "covered": row.covered,
            "event_count": row.event_count,
            "hardware_event_count": row.hardware_event_count,
        }

    @staticmethod
    def _event_to_dict(row: MamiFaultEvent) -> dict:
        return {
            "id": row.id,
            "log_id": row.log_id,
            "kb_id": row.kb_id,
            "host_name": row.host_name,
            "source_file": row.source_file,
            "timestamp": row.timestamp,
            "level": row.level,
            "category": row.category,
            "signal": row.signal,
            "message": row.message,
        }
