from latency.schemas.request import ListLogParseResultRequest, ListTracesByHostRequest, GetLatencyMetricsRequest
from latency.schemas.response import (
    ListLogParseResultsMsg,
    GetLogParseResultMsg,
    ListTracesByHostMsg,
    GetLatencyMetricsMsg,
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

    @staticmethod
    async def list_traces_by_host(req: ListTracesByHostRequest) -> ListTracesByHostMsg:
        """根据主机获取trace列表"""
        total, traces = await LogParseResultManager.list_traces_by_host(req)
        return ListTracesByHostMsg(total=total, traces=traces)

    @staticmethod
    async def get_latency_metrics(req: GetLatencyMetricsRequest) -> GetLatencyMetricsMsg:
        """获取延迟指标时间曲线数据"""
        total, metrics = await LogParseResultManager.get_latency_metrics(req)
        return GetLatencyMetricsMsg(
            total=total,
            metrics=metrics,
            time_range={
                "start_time": req.start_time,
                "end_time": req.end_time,
            },
        )
