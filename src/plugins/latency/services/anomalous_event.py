from latency.schemas.response import (
    GetAnomalousEventMsg,
)
from latency.database.managers.anomalous_event import AnomalousEventManager


class AnomalousEventService:
    """异常事件服务"""

    @staticmethod
    async def get_anomalous_event_by_id(event_id: str) -> GetAnomalousEventMsg:
        event = await AnomalousEventManager.get_anomalous_event_by_id(event_id)
        return GetAnomalousEventMsg(event=event)

    @staticmethod
    async def list_anomalous_events_by_log_id(log_id: str) -> list:
        events = await AnomalousEventManager.list_anomalous_events_by_log_id(log_id)
        return events
