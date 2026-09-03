from latency.schemas.response import (
    GetAnomalousEventMsg,
    ListAnomalousEventsMsg,
)
from latency.schemas.request import ListAnomalousEventRequest
from latency.database.managers.anomalous_event import AnomalousEventPGManager
from latency.exceptions import NotFoundBizException


class AnomalousEventService:
    """异常事件服务"""

    @staticmethod
    async def get_anomalous_event_by_id(event_id: str) -> GetAnomalousEventMsg:
        event = await AnomalousEventPGManager.get_anomalous_event_by_id(event_id)
        if event is None or not event.existed_status:
            raise NotFoundBizException(resource="异常事件")
        return GetAnomalousEventMsg(event=event)

    @staticmethod
    async def list_anomalous_events_by_log_id(log_id: str) -> ListAnomalousEventsMsg:
        events = await AnomalousEventPGManager.list_anomalous_events_by_log_id(log_id)
        return ListAnomalousEventsMsg(total=len(events), events=events)

    @staticmethod
    async def list_anomalous_events(req: ListAnomalousEventRequest) -> ListAnomalousEventsMsg:
        total, events = await AnomalousEventPGManager.list_anomalous_events(req)
        return ListAnomalousEventsMsg(total=total, events=events)
