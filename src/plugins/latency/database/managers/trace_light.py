# Copyright (c) Huawei Technologies Co., Ltd. 2023-2025. All rights reserved.
"""Trace 轻量取数专用读路径（/trace/list + /trace/{trace_id}）。

独立新增 manager（设计文档 docs/design/trace-light-api.md §5），
不修改任何既有 manager / schema 文件：
- 投影只取响应所需列（时延侧 9 列 / 故障事件 4 列），不拉全模型行、
  不做 ORM→Pydantic 全模型转换；
- 故障码聚合（unnest → GROUP BY → ORDER/LIMIT/OFFSET）全部下推 DB，
  面向 10W~50W 行规模，应用侧只接收页内行。

⚠️ 口径对齐说明：本文件的过滤条件构造器为自包含实现（工程约束：
只新增不改旧代码），语义与老接口逐条对齐——
- 时延侧 _apply_latency_filters ↔ LogParseResultPGManager.list_log_parse_results
  的内联过滤逻辑；
- 故障侧 _trace_filter_conditions ↔ LogFailureEventPGManager
  的 _ip_eq / _array_overlap / _log_ids_for_kb_id / _narrow_log_ids /
  _trace_filter_conditions。
任一侧口径调整时，两处需同步修改。
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Optional

from sqlalchemy import func, literal, or_, select
from sqlalchemy.dialects.postgresql import array

from latency.database.engine import PGManager
from latency.database.models import LogFile, LogParseResult, TraceFailureEvent
from latency.database.utils import format_ip, format_timestamp, parse_timestamp
from latency.schemas.request import ListLogParseResultRequest
from latency.schemas.trace_light import (
    FailureCodeCntItem,
    ListFailureCodeStatsRequest,
    TraceFailureCodeStatModel,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# 自包含过滤条件构造器（口径对齐老接口，见模块 docstring）
# ---------------------------------------------------------------------------

def _apply_latency_filters(stmt, req: ListLogParseResultRequest):
    """log_parse_result 过滤条件（语义对齐 LogParseResultPGManager.
    list_log_parse_results 的内联实现：existed_status + kb join + 全部
    请求字段条件），供轻量投影查询复用。
    """
    stmt = stmt.where(LogParseResult.existed_status.is_(True))

    if req.log_id:
        stmt = stmt.where(LogParseResult.log_id == req.log_id)
    if req.kb_id:
        stmt = stmt.join(LogFile, LogParseResult.log_id == LogFile.id).where(
            LogFile.kb_id == req.kb_id
        )
    if req.aggregated_event_id:
        stmt = stmt.where(LogParseResult.aggregated_event_id == req.aggregated_event_id)
    if req.trace_id:
        stmt = stmt.where(LogParseResult.trace_id == req.trace_id)
    if req.trace_ids:
        stmt = stmt.where(LogParseResult.trace_id.in_(req.trace_ids))
    if req.src_ip is not None:
        if req.src_ip == "":
            stmt = stmt.where(LogParseResult.src_ip.is_(None))
        else:
            stmt = stmt.where(
                func.host(LogParseResult.src_ip).like(f"%{req.src_ip}%")
            )
    if req.dst_ip is not None:
        if req.dst_ip == "":
            stmt = stmt.where(LogParseResult.dst_ip.is_(None))
        else:
            stmt = stmt.where(
                func.host(LogParseResult.dst_ip).like(f"%{req.dst_ip}%")
            )
    if req.pod_ip:
        stmt = stmt.where(LogParseResult.pod_ips.contains([req.pod_ip]))
    if req.host:
        stmt = stmt.where(LogParseResult.host.ilike(f"%{req.host}%"))
    if req.cluster_name:
        stmt = stmt.where(LogParseResult.cluster_name == req.cluster_name)
    if req.is_anomalous is not None:
        stmt = stmt.where(LogParseResult.is_anomalous.is_(req.is_anomalous))
    if req.start_time:
        stmt = stmt.where(LogParseResult.timestamp >= parse_timestamp(req.start_time))
    if req.end_time:
        stmt = stmt.where(LogParseResult.timestamp <= parse_timestamp(req.end_time))
    if req.created_at_start:
        stmt = stmt.where(LogParseResult.created_at >= parse_timestamp(req.created_at_start))
    if req.created_at_end:
        stmt = stmt.where(LogParseResult.created_at <= parse_timestamp(req.created_at_end))
    if req.operation:
        if req.operation.upper() == "GET":
            stmt = stmt.where(LogParseResult.operation.ilike("%GET%"))
        elif req.operation.upper() == "SET":
            stmt = stmt.where(
                LogParseResult.operation.in_(["DS_KV_CLIENT_SET", "DS_POSIX_CREATE", "DS_POSIX_PUBLISH"])
            )
    return stmt


def _ip_eq(column, value: str | None):
    """INET 列精确匹配（host 部分）；空串语义=IS NULL。

    对齐 LogFailureEventPGManager._ip_eq。
    """
    if value is None:
        return None
    if value == "":
        return column.is_(None)
    return func.host(column) == value


def _array_overlap(column, values: list[str] | None):
    """数组列重叠过滤；去除空串后无有效值则不过滤。

    对齐 LogFailureEventPGManager._array_overlap。
    """
    if not values:
        return None
    clean = [v for v in values if v]
    if not clean:
        return None
    return column.overlap(array(clean))


async def _log_ids_for_kb_id(kb_id: str | None) -> list[str]:
    """kb_id → 有效 log_id 列表（LogFile.existed_status=True）。

    对齐 LogFailureEventPGManager._log_ids_for_kb_id。
    """
    if not kb_id:
        return []
    stmt = select(LogFile.id).where(LogFile.kb_id == kb_id).where(
        LogFile.existed_status.is_(True)
    )
    async with PGManager.session() as session:
        result = await session.execute(stmt)
        return [r for r in result.scalars().all()]


def _narrow_log_ids(log_ids: list[str], log_id: str | None) -> list[str]:
    """在知识库级 log_id 列表基础上收窄到单个日志文件。

    对齐 LogFailureEventPGManager._narrow_log_ids：指定的 log_id 不属于
    该知识库时，返回不可能匹配的哨兵值，保证查询返回零行而非退化为
    全库扫描。
    """
    if not log_id:
        return log_ids
    return [lid for lid in log_ids if lid == log_id] or ["__not_in_this_kb__"]


def _trace_filter_conditions(req, log_ids: list[str]) -> list:
    """trace_failure_event 通用过滤条件。

    对齐 LogFailureEventPGManager._trace_filter_conditions（老接口与轻量
    聚合统计同一套过滤语义）。不含 is_anomalous：老接口该字段为故障侧
    failure_mode 口径，聚合统计接口为时延侧口径（join log_parse_result），
    各自构造。入参 log_ids 需先经 _log_ids_for_kb_id + _narrow_log_ids
    收窄。
    """
    conds = []
    if log_ids:
        conds.append(TraceFailureEvent.log_id.in_(log_ids))
    if req.trace_ids:
        conds.append(TraceFailureEvent.trace_id.in_(req.trace_ids))

    for column, values in (
        (TraceFailureEvent.pod_names, req.pod_names),
        (TraceFailureEvent.host_names, req.host_names),
        (TraceFailureEvent.cluster_names, req.cluster_names),
    ):
        cond = _array_overlap(column, values)
        if cond is not None:
            conds.append(cond)

    for column, value in (
        (TraceFailureEvent.src_ip, req.src_ip),
        (TraceFailureEvent.dst_ip, req.dst_ip),
    ):
        cond = _ip_eq(column, value)
        if cond is not None:
            conds.append(cond)

    if req.status_codes:
        conds.append(
            TraceFailureEvent.status_code.overlap(array(req.status_codes))
        )

    if req.start_time:
        conds.append(
            TraceFailureEvent.timestamp >= parse_timestamp(req.start_time)
        )
    if req.end_time:
        conds.append(
            TraceFailureEvent.timestamp <= parse_timestamp(req.end_time)
        )

    if req.operation:
        conds.append(TraceFailureEvent.operation == req.operation)
    return conds


# ---------------------------------------------------------------------------
# 轻量投影行
# ---------------------------------------------------------------------------

@dataclass
class LatencyTraceRow:
    """log_parse_result 轻量投影行（9 列，/trace 响应所需）。"""

    trace_id: str
    total_latency: Optional[float] = None
    is_anomalous: Optional[bool] = None
    operation: Optional[str] = None
    timestamp: Optional[str] = None
    pod_ips: Optional[list[str]] = None
    host: Optional[str] = None
    src_ip: Optional[str] = None
    dst_ip: Optional[str] = None


@dataclass
class FailureEventRow:
    """trace_failure_event 轻量投影行（get_trace 故障侧所需 4 列）。"""

    trace_id: str
    status_code: list[str] = field(default_factory=list)
    operation: str = ""
    timestamp: Optional[str] = None


class TraceLightPGManager:
    """轻量 trace 取数（独立读路径，无老 service/manager 依赖）。"""

    # 轻量 API 支持的时延侧排序键（老接口的排序映射子集）
    _LATENCY_SORT_COLUMNS = {
        "total_latency": LogParseResult.total_latency,
        "timestamp": LogParseResult.timestamp,
        "trace_id": LogParseResult.trace_id,
    }

    @staticmethod
    async def list_latency_projection(
        req: ListLogParseResultRequest,
    ) -> tuple[int, list[LatencyTraceRow]]:
        """时延侧投影查询：仅取响应 9 列 + count，过滤语义同老接口。

        trace_id.asc() 作为次级排序保证分页确定性；timestamp/src_ip/dst_ip
        与老接口同口径格式化。
        """
        stmt = _apply_latency_filters(
            select(
                LogParseResult.trace_id,
                LogParseResult.total_latency,
                LogParseResult.is_anomalous,
                LogParseResult.operation,
                LogParseResult.timestamp,
                LogParseResult.pod_ips,
                LogParseResult.host,
                LogParseResult.src_ip,
                LogParseResult.dst_ip,
            ),
            req,
        )

        count_stmt = select(func.count()).select_from(stmt.subquery())
        async with PGManager.session() as session:
            total = (await session.execute(count_stmt)).scalar() or 0

        order_clauses = []
        if req.sort_fields:
            for sf in req.sort_fields:
                col = TraceLightPGManager._LATENCY_SORT_COLUMNS.get(sf.field)
                if col is not None:
                    order_clauses.append(
                        col.desc() if sf.order == "desc" else col.asc()
                    )
        if not order_clauses:
            order_clauses.append(LogParseResult.total_latency.desc())
        stmt = stmt.order_by(*order_clauses, LogParseResult.trace_id.asc())
        stmt = stmt.offset((req.page_num - 1) * req.page_cnt).limit(req.page_cnt)

        async with PGManager.session() as session:
            rows = (await session.execute(stmt)).all()

        return total, [
            LatencyTraceRow(
                trace_id=r.trace_id,
                total_latency=r.total_latency,
                is_anomalous=r.is_anomalous,
                operation=r.operation,
                timestamp=format_timestamp(r.timestamp),
                pod_ips=r.pod_ips,
                host=r.host,
                src_ip=format_ip(r.src_ip),
                dst_ip=format_ip(r.dst_ip),
            )
            for r in rows
        ]

    @staticmethod
    async def list_failure_events_by_trace_ids(
        kb_id: str | None,
        log_id: str | None,
        trace_ids: list[str],
    ) -> list[FailureEventRow]:
        """按 trace_ids 批量取故障事件投影（get_trace 用，4 列）。

        按时间升序返回（get_trace 取最早日志时间作 trace 时间戳）。
        """
        if not trace_ids:
            return []
        log_ids = await _log_ids_for_kb_id(kb_id)
        if kb_id and not log_ids:
            return []
        log_ids = _narrow_log_ids(log_ids, log_id)

        conds = [TraceFailureEvent.trace_id.in_(trace_ids)]
        if log_ids:
            conds.append(TraceFailureEvent.log_id.in_(log_ids))
        stmt = (
            select(
                TraceFailureEvent.trace_id,
                TraceFailureEvent.status_code,
                TraceFailureEvent.operation,
                TraceFailureEvent.timestamp,
            )
            .where(*conds)
            .order_by(TraceFailureEvent.timestamp.asc())
        )
        async with PGManager.session() as session:
            rows = (await session.execute(stmt)).all()
        return [
            FailureEventRow(
                trace_id=r.trace_id,
                status_code=r.status_code or [],
                operation=r.operation or "",
                timestamp=format_timestamp(r.timestamp),
            )
            for r in rows
        ]

    @staticmethod
    async def list_failure_code_stats(
        req: ListFailureCodeStatsRequest,
    ) -> tuple[int, list[TraceFailureCodeStatModel]]:
        """按 trace 聚合故障码计数，支持 failure_cnt / 时延侧键排序与分页。

        面向 10W~50W 行规模：聚合（unnest → GROUP BY）、排序、LIMIT/OFFSET
        全部下推 DB，应用侧只接收页内行（≤ page_cnt），不做全量拉取。

        SQL 形态（均为有界传输）：
          expanded:  过滤后的行 × unnest(status_code)
          code_cnt:  GROUP BY (trace_id, code) → 每码计数
          per_trace: GROUP BY (trace_id) → failure_cnt（空码 trace 经
                     union_all 保留，failure_cnt=0）
          页行:      per_trace [LEFT|INNER] JOIN 时延侧排序键 → ORDER/LIMIT
          计数:      JOIN 后的 per_trace 行数（total）
          码明细:    页内 trace_id 的 code_cnt 行

        is_anomalous 为时延侧口径：INNER JOIN log_parse_result 聚合子查询
        过滤（纯故障 trace 无时延行，会被剔除）。
        """
        log_ids = await _log_ids_for_kb_id(req.kb_id)
        if req.kb_id and not log_ids:
            return 0, []
        log_ids = _narrow_log_ids(log_ids, req.log_id)
        conds = _trace_filter_conditions(req, log_ids)

        expanded = (
            select(
                TraceFailureEvent.trace_id.label("trace_id"),
                TraceFailureEvent.operation.label("operation"),
                func.unnest(TraceFailureEvent.status_code).label("code"),
            )
            .where(*conds)
            .cte("expanded")
        )
        code_cnt = (
            select(
                expanded.c.trace_id.label("trace_id"),
                expanded.c.code.label("code"),
                func.count().label("cnt"),
                func.min(expanded.c.operation).label("operation"),
            )
            .group_by(expanded.c.trace_id, expanded.c.code)
            .cte("code_cnt")
        )
        # 空码 trace（unnest 展开后消失）单独聚合后 union 回来，failure_cnt=0
        empty_trace = (
            select(
                TraceFailureEvent.trace_id.label("trace_id"),
                literal(0).label("failure_cnt"),
                func.min(TraceFailureEvent.operation).label("operation"),
            )
            .where(
                *conds,
                or_(
                    TraceFailureEvent.status_code.is_(None),
                    func.cardinality(TraceFailureEvent.status_code) == 0,
                ),
            )
            .group_by(TraceFailureEvent.trace_id)
        )
        agg_trace = (
            select(
                code_cnt.c.trace_id.label("trace_id"),
                func.sum(code_cnt.c.cnt).label("failure_cnt"),
                func.min(code_cnt.c.operation).label("operation"),
            )
            .group_by(code_cnt.c.trace_id)
        )
        per_trace = agg_trace.union_all(empty_trace).cte("per_trace")

        # 时延侧排序键 / is_anomalous 过滤（join log_parse_result 聚合子查询，
        # 同一 trace 多日志行时 total_latency 取最大、timestamp 取最早）
        needs_latency = (
            req.sort_by in ("total_latency", "timestamp")
            or req.is_anomalous is not None
        )
        if needs_latency:
            lat_conds = [LogParseResult.existed_status.is_(True)]
            if log_ids:
                lat_conds.append(LogParseResult.log_id.in_(log_ids))
            if req.is_anomalous is not None:
                lat_conds.append(LogParseResult.is_anomalous.is_(req.is_anomalous))
            lat_scope = (
                select(
                    LogParseResult.trace_id.label("trace_id"),
                    func.max(LogParseResult.total_latency).label("total_latency"),
                    func.min(LogParseResult.timestamp).label("timestamp"),
                )
                .where(*lat_conds)
                .group_by(LogParseResult.trace_id)
                .cte("lat_scope")
            )
            if req.is_anomalous is not None:
                join = per_trace.join(
                    lat_scope, per_trace.c.trace_id == lat_scope.c.trace_id
                )
            else:
                join = per_trace.outerjoin(
                    lat_scope, per_trace.c.trace_id == lat_scope.c.trace_id
                )
            base = (
                select(
                    per_trace.c.trace_id.label("trace_id"),
                    per_trace.c.failure_cnt.label("failure_cnt"),
                    per_trace.c.operation.label("operation"),
                    lat_scope.c.total_latency.label("total_latency"),
                    lat_scope.c.timestamp.label("timestamp"),
                )
                .select_from(join)
                .cte("traced")
            )
            order_col = (
                base.c.total_latency
                if req.sort_by == "total_latency"
                else base.c.timestamp
            )
        else:
            base = per_trace
            order_col = base.c.failure_cnt

        direction = req.sort_order == "asc"
        order = (
            order_col.asc().nulls_last() if direction else order_col.desc().nulls_last()
        )
        page_stmt = (
            select(
                base.c.trace_id,
                base.c.failure_cnt,
                base.c.operation,
            )
            .order_by(order, base.c.trace_id.asc())
            .offset((req.page_num - 1) * req.page_cnt)
            .limit(req.page_cnt)
        )
        count_stmt = select(func.count()).select_from(base)

        async with PGManager.session() as session:
            total = (await session.execute(count_stmt)).scalar() or 0
            page_rows = (await session.execute(page_stmt)).all()
            page_ids = [row.trace_id for row in page_rows]
            codes_map: dict[str, list[FailureCodeCntItem]] = {}
            if page_ids:
                codes_stmt = (
                    select(
                        code_cnt.c.trace_id,
                        code_cnt.c.code,
                        code_cnt.c.cnt,
                    )
                    .where(code_cnt.c.trace_id.in_(page_ids))
                    .order_by(code_cnt.c.cnt.desc(), code_cnt.c.code.asc())
                )
                for row in (await session.execute(codes_stmt)).all():
                    codes_map.setdefault(
                        row.trace_id, []
                    ).append(FailureCodeCntItem(code=row.code, cnt=row.cnt))

        stats = [
            TraceFailureCodeStatModel(
                trace_id=row.trace_id,
                failure_cnt=row.failure_cnt,
                codes=codes_map.get(row.trace_id, []),
                operation=row.operation,
            )
            for row in page_rows
        ]
        return total, stats

    @staticmethod
    async def list_failure_codes_by_trace_ids(
        kb_id: str,
        log_id: str | None,
        trace_ids: list[str],
    ) -> list[TraceFailureCodeStatModel]:
        """按 trace_ids 批量取故障码聚合（页内补源，入参必须有界 ≤500）。

        /trace/list include=failure_codes 的 LEFT JOIN 补源：仅需 trace_id +
        status_code 两列的聚合结果，不拉全模型行。
        """
        if not trace_ids:
            return []
        log_ids = await _log_ids_for_kb_id(kb_id)
        if kb_id and not log_ids:
            return []
        log_ids = _narrow_log_ids(log_ids, log_id)

        conds = [TraceFailureEvent.trace_id.in_(trace_ids)]
        if log_ids:
            conds.append(TraceFailureEvent.log_id.in_(log_ids))
        expanded = (
            select(
                TraceFailureEvent.trace_id.label("trace_id"),
                func.unnest(TraceFailureEvent.status_code).label("code"),
            )
            .where(*conds)
            .cte("expanded")
        )
        stmt = (
            select(
                expanded.c.trace_id.label("trace_id"),
                expanded.c.code.label("code"),
                func.count().label("cnt"),
            )
            .group_by(expanded.c.trace_id, expanded.c.code)
            .order_by(func.count().desc(), expanded.c.code.asc())
        )
        async with PGManager.session() as session:
            rows = (await session.execute(stmt)).all()

        stats_map: dict[str, TraceFailureCodeStatModel] = {}
        for row in rows:
            stat = stats_map.setdefault(
                row.trace_id, TraceFailureCodeStatModel(trace_id=row.trace_id)
            )
            stat.codes.append(FailureCodeCntItem(code=row.code, cnt=row.cnt))
        for stat in stats_map.values():
            stat.failure_cnt = sum(item.cnt for item in stat.codes)
        return list(stats_map.values())
