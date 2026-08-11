import logging
import dataclasses

from latency.schemas.log import (
    SrcDstAggregatedEventDataclass,
    SrcDstAggregatedEventModel,
)
from latency.schemas.request import ListSrcDstAggregatedEventRequest, ListTimeWindowAggregatedEventRequest
from latency.schemas.response import (
    ListSrcDstAggregatedEventMsg,
    GetSrcDstAggregatedEventMsg,
    ListTimeWindowAggregatedEventMsg,
)
from latency.database.managers.src_dst_aggregated_event import SrcDstAggregatedEventPGManager
from latency.database.managers.time_window_aggregated_event import TimeWindowAggregatedEventPGManager
from latency.database.managers.log_file import LogFilePGManager
from latency.schemas.log import TimeWindowAggregatedEventModel, TimeWindowAggregatedIpPair
from latency.common.aggregate_cache import (
    get_aggregated_events,
    find_aggregated_by_kb_id,
)

logger = logging.getLogger(__name__)


class SrcDstAggregatedEventService:
    """聚合事件服务"""

    @staticmethod
    async def list_aggregated_events(req: ListSrcDstAggregatedEventRequest) -> ListSrcDstAggregatedEventMsg:
        cached: list[SrcDstAggregatedEventDataclass] | None = None
        if req.log_id:
            cached = get_aggregated_events(req.log_id)
            if cached is None and not req.kb_id:
                lf = await LogFilePGManager.get_log_file_by_log_file_id(req.log_id)
                if lf and lf.kb_id:
                    cached = find_aggregated_by_kb_id(lf.kb_id)
        elif req.kb_id:
            cached = find_aggregated_by_kb_id(req.kb_id)
        if cached is not None:
                events: list[SrcDstAggregatedEventModel] = [
                    SrcDstAggregatedEventModel(**dataclasses.asdict(event)) for event in cached
                ]
                filtered = SrcDstAggregatedEventService._filter_aggregated_in_memory(
                    events, req
                )
                total = len(filtered)
                start = (req.page_num - 1) * req.page_cnt
                page = filtered[start : start + req.page_cnt]
                logger.info(
                    "[CACHE-HIT] list_aggregated_events via=%s log_id=%s kb_id=%s total=%d page=%d",
                    "log_id" if req.log_id else "kb_id",
                    req.log_id or "",
                    req.kb_id or "",
                    total,
                    len(page),
                )
                return ListSrcDstAggregatedEventMsg(total=total, events=page)

        total, events = await SrcDstAggregatedEventPGManager.list_aggregated_events(req)
        return ListSrcDstAggregatedEventMsg(total=total, events=events)

    @staticmethod
    def _filter_aggregated_in_memory(
        events: list[SrcDstAggregatedEventModel],
        req: ListSrcDstAggregatedEventRequest,
    ) -> list[SrcDstAggregatedEventModel]:
        result = events
        if req.src_ip:
            result = [e for e in result if e.src_ip and req.src_ip in e.src_ip]
        if req.dst_ip:
            result = [e for e in result if e.dst_ip and req.dst_ip in e.dst_ip]
        if req.operation:
            op_upper = req.operation.strip().upper()
            # GET 操作：匹配包含 GET 的操作（如 DS_KV_CLIENT_GET）
            if op_upper == "GET":
                result = [e for e in result if "GET" in (e.operation or "").upper()]
            # SET 操作：匹配包含 SET/CREATE/PUBLISH 的操作
            elif op_upper == "SET":
                result = [
                    e for e in result 
                    if any(kw in (e.operation or "").upper() for kw in ["SET", "CREATE", "PUBLISH"])
                ]
            else:
                # 其他操作类型：精确匹配
                result = [e for e in result if (e.operation or "").strip().upper() == op_upper]
        if req.cluster_name:
            result = [e for e in result if e.cluster_name == req.cluster_name]
        if req.host:
            result = [e for e in result if e.host == req.host]
        if req.start_time:
            result = [e for e in result if e.created_at >= req.start_time]
        if req.end_time:
            result = [e for e in result if e.created_at <= req.end_time]
        return result

    @staticmethod
    async def get_aggregated_event_by_id(event_id: str) -> GetSrcDstAggregatedEventMsg:
        event = await SrcDstAggregatedEventPGManager.get_aggregated_event_by_id(event_id)
        return GetSrcDstAggregatedEventMsg(event=event)

    @staticmethod
    async def list_time_window_events(req: ListTimeWindowAggregatedEventRequest) -> ListTimeWindowAggregatedEventMsg:
        total, rows = await TimeWindowAggregatedEventPGManager.list_time_window_events(req)
        events = []
        for row in rows:
            ip_pairs = [TimeWindowAggregatedIpPair(**p) for p in row.pop("ip_pairs", [])]
            events.append(TimeWindowAggregatedEventModel(**row, ip_pairs=ip_pairs))
        return ListTimeWindowAggregatedEventMsg(total=total, events=events)
