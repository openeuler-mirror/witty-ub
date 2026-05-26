from latency.schemas.request import ListLogParseResultRequest
from latency.schemas.response import (
    ListLogParseResultsMsg,
    GetLogParseResultMsg,
)
from latency.database.managers.log_parse_result import LogParseResultManager


class LogParseResultService:
    """日志解析结果服务"""

    @staticmethod
    async def list_log_parse_results(req: ListLogParseResultRequest) -> ListLogParseResultsMsg:
        total, results = await LogParseResultManager.list_log_parse_results(req)
        return ListLogParseResultsMsg(total=total, log_parse_results=results)

    @staticmethod
    async def get_log_parse_result_by_id(result_id: str) -> GetLogParseResultMsg:
        result = await LogParseResultManager.get_log_parse_result_by_id(result_id)
        return GetLogParseResultMsg(log_parse_result=result)
