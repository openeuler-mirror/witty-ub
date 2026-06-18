from latency.schemas.request import (
    ListLogFailureEventResultRequest,
    ListTraceFailureEventResultRequest,
    GetErrCodeMetricsRequest,
    ListTimeAggregatedFailureEventRequest,
    ListPodAggregatedFailureEventRequest,
)
from latency.schemas.response import (
    ListLogFailureEventResultMsg,
    ListTraceFailureEventResultMsg,
    GetErrCodeMetricsMsg,
    ListTimeAggregatedFailureEventMsg,
    ListPodAggregatedFailureEventMsg,
)
from latency.schemas.log_failure_event import TimeAggregatedFailureEventModel, PodAggregatedFailureEventModel
from latency.database.managers.log_failure_event import LogFailureEventManager


class LogFailureEventResultService:
    """日志事件结果服务"""

    @staticmethod
    async def list_log_failure_event_result(req: ListLogFailureEventResultRequest) -> ListLogFailureEventResultMsg:
        total, results = await LogFailureEventManager.list_log_failure_events(req)
        return ListLogFailureEventResultMsg(total=total, log_failure_event_results=results)
    
    @staticmethod
    async def list_trace_failure_event_result(req: ListTraceFailureEventResultRequest) -> ListTraceFailureEventResultMsg:
        total, results = await LogFailureEventManager.list_trace_failure_events(req)
        return ListTraceFailureEventResultMsg(total=total, trace_failure_event_results=results)
    
    @staticmethod
    async def list_time_aggregated_failure_event_result(req: ListTimeAggregatedFailureEventRequest) -> ListTimeAggregatedFailureEventMsg:
        total, err_codes, results = await LogFailureEventManager.list_time_aggregated_failure_events(req)
        events = [TimeAggregatedFailureEventModel(**r) for r in results]
        return ListTimeAggregatedFailureEventMsg(total=total, err_codes=err_codes, events=events)

    @staticmethod
    async def list_pod_aggregated_failure_event_result(req: ListPodAggregatedFailureEventRequest) -> ListPodAggregatedFailureEventMsg:
        total, results = await LogFailureEventManager.list_pod_aggregated_failure_events(req)
        print(results)
        events = [PodAggregatedFailureEventModel(**r) for r in results]
        return ListPodAggregatedFailureEventMsg(total=total, events=events)

    @staticmethod
    async def get_err_code_metrics(req: GetErrCodeMetricsRequest) -> GetErrCodeMetricsMsg:
        """获取故障码指标时间曲线数据"""
        total, metrics = await LogFailureEventManager.get_err_code_metrics(req)
        return GetErrCodeMetricsMsg(
            total=total,
            metrics=metrics,
            time_range={
                "start_time": req.start_time,
                "end_time": req.end_time,
            },
        )