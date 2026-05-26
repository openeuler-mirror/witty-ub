from latency.schemas.request import ListAnomalousEventChainRequest
from latency.schemas.response import (
    ListAnomalousEventChainsMsg,
)
from latency.database.managers.anomalous_event_chain import AnomalousEventChainManager


class AnomalousEventChainService:
    """异常事件链服务"""

    @staticmethod
    async def list_event_chains(req: ListAnomalousEventChainRequest) -> ListAnomalousEventChainsMsg:
        total, chains = await AnomalousEventChainManager.list_event_chains(req)
        return ListAnomalousEventChainsMsg(total=total, event_chains=chains)

    @staticmethod
    async def list_event_chains_by_log_id(log_id: str) -> list:
        chains = await AnomalousEventChainManager.list_event_chains_by_log_id(log_id)
        return chains
