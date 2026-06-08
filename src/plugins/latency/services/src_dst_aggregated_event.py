from latency.schemas.request import ListSrcDstAggregatedEventRequest
from latency.schemas.response import (
    ListSrcDstAggregatedEventMsg,
    GetSrcDstAggregatedEventMsg,
)
from latency.database.managers.src_dst_aggregated_event import SrcDstAggregatedEventManager


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
