from latency.schemas.request import ListSrcDstAggregatedEventRequest, ListTimeWindowAggregatedEventRequest
from latency.schemas.response import (
    ListSrcDstAggregatedEventMsg,
    GetSrcDstAggregatedEventMsg,
    ListTimeWindowAggregatedEventMsg,
)
from latency.database.managers.src_dst_aggregated_event import SrcDstAggregatedEventManager
from latency.schemas.log import TimeWindowAggregatedEventModel, TimeWindowAggregatedIpPair


class SrcDstAggregatedEventService:
    """聚合事件服务"""

    @staticmethod
    async def list_aggregated_events(req: ListSrcDstAggregatedEventRequest) -> ListSrcDstAggregatedEventMsg:
        total, events = await SrcDstAggregatedEventManager.list_aggregated_events(req)
        return ListSrcDstAggregatedEventMsg(total=total, events=events)

    @staticmethod
    async def get_aggregated_event_by_id(event_id: str) -> GetSrcDstAggregatedEventMsg:
        event = await SrcDstAggregatedEventManager.get_aggregated_event_by_id(event_id)
        return GetSrcDstAggregatedEventMsg(event=event)

    @staticmethod
    async def list_time_window_events(req: ListTimeWindowAggregatedEventRequest) -> ListTimeWindowAggregatedEventMsg:
        total, rows = await SrcDstAggregatedEventManager.list_time_window_events(req)
        events = []
        for row in rows:
            ip_pairs = [TimeWindowAggregatedIpPair(**p) for p in row.pop("ip_pairs", [])]
            events.append(TimeWindowAggregatedEventModel(**row, ip_pairs=ip_pairs))
        return ListTimeWindowAggregatedEventMsg(total=total, events=events)
