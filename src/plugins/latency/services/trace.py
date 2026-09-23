# Copyright (c) Huawei Technologies Co., Ltd. 2023-2025. All rights reserved.
"""Trace 轻量取数服务（/trace/list + /trace/{trace_id}）。

设计文档 docs/design/trace-light-api.md §4.1/§4.2/§5：
- 读路径全部走独立 manager（TraceLightPGManager）：投影只取响应所需列，
  不经过老 service / 全模型转换；
- 时延侧（log_parse_result）与故障侧（trace_failure_event）双源合并，
  LEFT JOIN 语义；
- sort_by ∈ {total_latency, timestamp} 且无 status_codes：时延侧主源
  （默认最快路径：单查询）；
- sort_by = failure_cnt 或传 status_codes：故障侧主源，聚合/排序/分页全部
  下推 DB（面向 10W~50W 行规模，应用侧只接收页内行），纯故障 trace 不丢条；
- include 指定的附加块（failure_codes/topology）才赋值，未指定的块不出现在
  响应里；补源查询仅按页内 trace_ids（≤500）取数，永远有界。
"""

import asyncio
import logging
from collections import Counter
from typing import Any, Optional

from latency.database.managers.trace_light import TraceLightPGManager
from latency.exceptions import NotFoundBizException
from latency.schemas.request import (
    ListLogParseResultRequest,
    SortField,
)
from latency.schemas.trace_light import (
    GetTraceMsg,
    ListFailureCodeStatsRequest,
    ListTracesMsg,
    ListTracesRequest,
    TraceFailureCodeItem,
    TraceListItem,
)

logger = logging.getLogger(__name__)


class TraceService:
    """trace 轻量取数服务"""

    # ------------------------------------------------------------------
    # 公共入口
    # ------------------------------------------------------------------
    @staticmethod
    async def list_traces(req: ListTracesRequest) -> ListTracesMsg:
        if req.sort_by == "failure_cnt" or req.status_codes:
            return await TraceService._list_failure_primary(req)
        return await TraceService._list_by_latency(req)

    @staticmethod
    async def get_trace(
        trace_id: str,
        kb_id: Optional[str] = None,
        log_id: Optional[str] = None,
    ) -> GetTraceMsg:
        latency_req = ListLogParseResultRequest(
            kb_id=kb_id or "",
            log_id=log_id,
            trace_id=trace_id,
            page_cnt=10,
            page_num=1,
        )
        (latency_pack, events) = await asyncio.gather(
            TraceLightPGManager.list_latency_projection(latency_req),
            TraceLightPGManager.list_failure_events_by_trace_ids(
                kb_id, log_id, [trace_id]
            ),
        )
        _total, latency_rows = latency_pack
        row = latency_rows[0] if latency_rows else None
        if row is None and not events:
            raise NotFoundBizException(
                resource="Trace", detail=f"不存在的 trace_id: {trace_id}"
            )

        codes_map = TraceService._aggregate_failure_codes(events)
        timestamps = [ev.timestamp for ev in events if ev.timestamp]
        return GetTraceMsg(
            trace_id=trace_id,
            total_latency_ms=row.total_latency if row else None,
            is_anomalous=row.is_anomalous if row else None,
            operation=(
                row.operation if row
                else (events[0].operation if events else None)
            ),
            failure_codes=codes_map.get(trace_id, []),
            pod_ips=row.pod_ips if row else None,
            host=row.host if row else None,
            src_ip=row.src_ip if row else None,
            dst_ip=row.dst_ip if row else None,
            timestamp=(
                min(timestamps) if timestamps
                else (row.timestamp if row else None)
            ),
        )

    # ------------------------------------------------------------------
    # 路径 1/2：时延侧主源（sort_by ∈ {total_latency, timestamp}，无 status_codes）
    # ------------------------------------------------------------------
    @staticmethod
    async def _list_by_latency(req: ListTracesRequest) -> ListTracesMsg:
        """时延主源：原生排序分页（默认最快路径单查询）。

        include 含 failure_codes 时按当前页 trace_ids 批量补故障码（LEFT JOIN，
        无故障记录的 trace 得 []，不丢条）。补源仅按 join 键（kb/log/trace_ids）
        取数，避免跨源过滤口径（如时延侧模糊 IP vs 故障侧精确 IP）误伤故障码。
        """
        sort_field = "total_latency" if req.sort_by == "total_latency" else "timestamp"
        total, rows = await TraceLightPGManager.list_latency_projection(
            TraceService._latency_request(req, sort_field=sort_field)
        )

        need_codes = "failure_codes" in req.include
        codes_map: dict[str, list[TraceFailureCodeItem]] = {}
        if need_codes and rows:
            stats = await TraceLightPGManager.list_failure_codes_by_trace_ids(
                req.kb_id, req.log_id, [r.trace_id for r in rows]
            )
            codes_map = {
                stat.trace_id: TraceService._to_code_items(stat.codes)
                for stat in stats
            }

        items = [
            TraceService._item_from_row(
                row,
                include_topology="topology" in req.include,
                codes=codes_map.get(row.trace_id, []) if need_codes else None,
            )
            for row in rows
        ]
        return ListTracesMsg(total=total, items=items)

    # ------------------------------------------------------------------
    # 路径 3/4：故障侧主源（sort_by=failure_cnt 或 status_codes 过滤）
    # ------------------------------------------------------------------
    @staticmethod
    async def _list_failure_primary(req: ListTracesRequest) -> ListTracesMsg:
        """故障主源：“哪些 trace 挂了故障码” / 按故障码计数排序。

        聚合/排序/分页全部下推 DB（unnest → GROUP BY → ORDER/LIMIT/OFFSET），
        服务层只做页内时延补全（trace_ids IN ≤ page_cnt，有界）。纯故障
        trace（无时延行）保留，total_latency_ms/is_anomalous 为 null；
        is_anomalous 为时延侧口径，由 SQL join log_parse_result 过滤
        （纯故障 trace 会被该过滤剔除）。
        """
        stats_req = ListFailureCodeStatsRequest(
            kb_id=req.kb_id,
            log_id=req.log_id,
            trace_ids=req.trace_ids,
            host_names=[req.host] if req.host else None,
            cluster_names=[req.cluster_name] if req.cluster_name else None,
            # pod_ip 无故障侧原生等价（时延侧存 IP 列表、故障侧存 pod 名称列表），
            # 不做映射，避免错误过滤
            src_ip=req.src_ip,
            dst_ip=req.dst_ip,
            status_codes=req.status_codes,
            is_anomalous=req.is_anomalous,
            start_time=req.start_time,
            end_time=req.end_time,
            operation=req.operation,
            sort_by=req.sort_by,
            sort_order=req.sort_order,
            page_cnt=req.page_cnt,
            page_num=req.page_num,
        )
        total, stats = await TraceLightPGManager.list_failure_code_stats(
            stats_req
        )

        latency_map: dict[str, Any] = {}
        page_ids = [stat.trace_id for stat in stats]
        if page_ids:
            enrich_req = ListLogParseResultRequest(
                kb_id=req.kb_id,
                log_id=req.log_id,
                trace_ids=page_ids,
                page_cnt=len(page_ids),
                page_num=1,
            )
            _total, lat_rows = await TraceLightPGManager.list_latency_projection(
                enrich_req
            )
            latency_map = {r.trace_id: r for r in lat_rows}

        include_topology = "topology" in req.include
        items = [
            TraceService._item_from_stat(
                stat, latency_map.get(stat.trace_id), include_topology
            )
            for stat in stats
        ]
        return ListTracesMsg(total=total, items=items)

    # ------------------------------------------------------------------
    # 请求构造 / 投影
    # ------------------------------------------------------------------
    @staticmethod
    def _latency_request(
        req: ListTracesRequest,
        *,
        trace_ids: Optional[list[str]] = None,
        sort_field: str = "total_latency",
        page_cnt: Optional[int] = None,
        page_num: Optional[int] = None,
    ) -> ListLogParseResultRequest:
        return ListLogParseResultRequest(
            kb_id=req.kb_id,
            log_id=req.log_id,
            trace_ids=trace_ids if trace_ids is not None else req.trace_ids,
            operation=req.operation,
            is_anomalous=req.is_anomalous,
            pod_ip=req.pod_ip,
            host=req.host,
            cluster_name=req.cluster_name,
            src_ip=req.src_ip,
            dst_ip=req.dst_ip,
            start_time=req.start_time,
            end_time=req.end_time,
            sort_fields=[SortField(field=sort_field, order=req.sort_order)],
            page_cnt=page_cnt if page_cnt is not None else req.page_cnt,
            page_num=page_num if page_num is not None else req.page_num,
        )

    @staticmethod
    def _aggregate_failure_codes(
        events: list[Any],
    ) -> dict[str, list[TraceFailureCodeItem]]:
        """按 trace 聚合故障码：status_code 列表 Counter → [{code, cnt}]。

        仅 get_trace（单 trace，事件行有界）使用；清单路径的聚合已在
        DB 侧完成（list_failure_code_stats / list_failure_codes_by_trace_ids）。
        """
        per_trace: dict[str, Counter] = {}
        for ev in events:
            per_trace.setdefault(ev.trace_id, Counter()).update(ev.status_code or [])
        return {
            tid: [
                TraceFailureCodeItem(code=code, cnt=cnt)
                for code, cnt in sorted(
                    counter.items(), key=lambda kv: (-kv[1], kv[0])
                )
            ]
            for tid, counter in per_trace.items()
        }

    @staticmethod
    def _to_code_items(codes: list[Any]) -> list[TraceFailureCodeItem]:
        return [TraceFailureCodeItem(code=c.code, cnt=c.cnt) for c in codes]

    @staticmethod
    def _item_from_row(
        row: Any,
        *,
        include_topology: bool,
        codes: Optional[list[TraceFailureCodeItem]],
    ) -> TraceListItem:
        extra: dict[str, Any] = {}
        if codes is not None:
            extra["failure_codes"] = codes
        if include_topology:
            extra["pod_ips"] = row.pod_ips
            extra["host"] = row.host
            extra["src_ip"] = row.src_ip
            extra["dst_ip"] = row.dst_ip
        return TraceListItem(
            trace_id=row.trace_id,
            total_latency_ms=row.total_latency,
            is_anomalous=row.is_anomalous,
            operation=row.operation,
            **extra,
        )

    @staticmethod
    def _item_from_stat(
        stat: Any,
        row: Any,
        include_topology: bool,
    ) -> TraceListItem:
        extra: dict[str, Any] = {
            "failure_codes": TraceService._to_code_items(stat.codes),
            "failure_cnt": stat.failure_cnt,
        }
        if include_topology and row is not None:
            extra["pod_ips"] = row.pod_ips
            extra["host"] = row.host
            extra["src_ip"] = row.src_ip
            extra["dst_ip"] = row.dst_ip
        return TraceListItem(
            trace_id=stat.trace_id,
            total_latency_ms=row.total_latency if row else None,
            is_anomalous=row.is_anomalous if row else None,
            operation=row.operation if row else stat.operation,
            **extra,
        )
