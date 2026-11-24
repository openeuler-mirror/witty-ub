# Copyright (c) Huawei Technologies Co., Ltd. 2023-2025. All rights reserved.
"""mami 硬件故障扫描结果查询：召回期定界的唯一后端入口。

解析期由 ``KVCacheLogParseWorker`` 把窗口内的 mami 事实落入
``mami_fault_event`` / ``mami_scan_summary``（见
``database/managers/mami_fault_event.py``）；本模块只做**读取与汇总**，不做任何
加权/判断 —— 是否据此对候选加分由检索脚本（case-matching 的 ``MAMI_*`` 通道）
决定。

返回的 ``covered`` 为三态事实（来自解析期）：
  - ``True``  ：故障窗口由失败 trace 界定；
  - ``None``  ：有 trace 但无失败 trace（窗口退回全量运行期）；
  - ``False`` ：无任何可用 trace，窗口缺失（此时代码不落 mami 事件）。
"""
from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from latency.database.engine import PGManager

# 单次返回的硬件故障事件明细上限（signal/category 去重取数已足够）。
MAX_EVENTS = 2_000


async def _resolve_log_ids(
    session: AsyncSession,
    kb_name: str | None,
    kb_id: str | None,
    log_id: str | None,
) -> list[str]:
    """解析资产对应的 log_id 列表（与 log_semantic_profile 同口径）。

    ``kb_name`` 即 ``log_file.name``（报告 ``basic_info.kb_name``），优先按名解析；
    ``log_file.kb_id`` 仅作兜底。
    """
    if log_id:
        return [log_id]
    if kb_name:
        result = await session.execute(
            text("SELECT id FROM log_file WHERE name = :name"),
            {"name": kb_name},
        )
        ids = list(result.scalars().all())
        if ids:
            return ids
    if kb_id:
        result = await session.execute(
            text("SELECT id FROM log_file WHERE kb_id = :kb_id"),
            {"kb_id": kb_id},
        )
        return list(result.scalars().all())
    return []


def _empty_scan() -> dict:
    return {
        "found": False,
        "log_id": None,
        "covered": None,
        "window_start": None,
        "window_end": None,
        "mami_files_found": 0,
        "event_count": 0,
        "hardware_event_count": 0,
        "hardware_hit": False,
        "signals": [],
        "categories": [],
    }


async def resolve_mami_scan(
    kb_name: str | None = None,
    log_id: str | None = None,
    kb_id: str | None = None,
) -> dict:
    """按资产返回窗口内的 mami 硬件故障汇总；无数据返回 ``found=False`` 的空结果。

    三个定位参数都缺省时直接返回空结果（通道自动关闭，无副作用）。
    多个候选 log_id 时，优先取「有窗口且事件最多」的一条，保证召回期信号稳定。
    """
    if not kb_name and not log_id and not kb_id:
        return _empty_scan()

    async with PGManager.session() as session:
        log_ids = await _resolve_log_ids(session, kb_name, kb_id, log_id)
        if not log_ids:
            return _empty_scan()
        rows = (
            await session.execute(
                text(
                    "SELECT log_id, kb_id, window_start, window_end, mami_files_found, "
                    "covered, event_count, hardware_event_count "
                    "FROM mami_scan_summary WHERE log_id = ANY(:log_ids)"
                ),
                {"log_ids": log_ids},
            )
        ).mappings().all()
        if not rows:
            return _empty_scan()
        # 排序：先硬件事件多的，再事件多的（covered 仅作记录，不作硬门槛）。
        best = max(
            rows,
            key=lambda r: (int(r["hardware_event_count"] or 0), int(r["event_count"] or 0)),
        )
        events = (
            await session.execute(
                text(
                    "SELECT category, signal FROM mami_fault_event "
                    "WHERE log_id = :log_id ORDER BY timestamp ASC LIMIT :limit"
                ),
                {"log_id": best["log_id"], "limit": MAX_EVENTS},
            )
        ).mappings().all()

    signals = sorted({e["signal"] for e in events if e["signal"]})
    categories = sorted({e["category"] for e in events if e["category"]})
    hardware_count = int(best["hardware_event_count"] or 0)
    covered = best["covered"]
    return {
        "found": True,
        "log_id": best["log_id"],
        "covered": None if covered is None else bool(covered),
        "window_start": best["window_start"].isoformat() if best["window_start"] else None,
        "window_end": best["window_end"].isoformat() if best["window_end"] else None,
        "mami_files_found": int(best["mami_files_found"] or 0),
        "event_count": int(best["event_count"] or 0),
        "hardware_event_count": hardware_count,
        "hardware_hit": hardware_count > 0,
        "signals": signals,
        "categories": categories,
    }
