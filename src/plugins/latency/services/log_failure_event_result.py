import logging

from latency.common.trace_context import collect_trace_context_logs
from latency.database.managers.log_failure_event import LogFailureEventPGManager
from latency.database.managers.log_file import LogFilePGManager
from latency.schemas.request import (
    ListLogFailureEventResultRequest,
    ListTraceFailureEventResultRequest,
    GetErrCodeMetricsRequest,
    ListTimeAggregatedFailureEventRequest,
    ListPodAggregatedFailureEventRequest,
    ListSrcDstAggregatedFailureEventRequest,
)
from latency.schemas.response import (
    ListLogFailureEventResultMsg,
    ListTraceFailureEventResultMsg,
    GetErrCodeMetricsMsg,
    ListTimeAggregatedFailureEventMsg,
    ListPodAggregatedFailureEventMsg,
    ListSrcDstAggregatedFailureEventMsg,
)
from latency.schemas.log_failure_event import TimeAggregatedFailureEventModel, PodAggregatedFailureEventModel, SrcDstAggregatedFailureEventModel


logger = logging.getLogger(__name__)


class LogFailureEventResultService:
    """日志事件结果服务"""

    @staticmethod
    def _normalize_unknown_host_name(host_name: str | None) -> str | None:
        if host_name is None:
            return None
        normalized = host_name.strip()
        if not normalized or normalized.lower() == "unknown":
            return None
        return host_name

    @staticmethod
    def _normalize_unknown_host_names(host_names: list[str | None]) -> list[str | None]:
        return [
            LogFailureEventResultService._normalize_unknown_host_name(host_name)
            for host_name in host_names
        ]

    @staticmethod
    async def list_log_failure_event_result(req: ListLogFailureEventResultRequest) -> ListLogFailureEventResultMsg:
        total, results = await LogFailureEventPGManager.list_log_failure_events(req)
        if total == 0:
            backfilled = await LogFailureEventResultService._backfill_trace_context_logs(req)
            if backfilled:
                total, results = await LogFailureEventPGManager.list_log_failure_events(req)
        for result in results:
            result.host_name = LogFailureEventResultService._normalize_unknown_host_name(
                result.host_name
            )
        return ListLogFailureEventResultMsg(total=total, log_failure_event_results=results)

    @staticmethod
    async def _backfill_trace_context_logs(req: ListLogFailureEventResultRequest) -> int:
        trace_ids = {trace_id.strip() for trace_id in req.trace_ids if trace_id and trace_id.strip()}
        if not trace_ids or (not req.kb_id and not req.log_id):
            return 0

        rows = await LogFilePGManager.list_log_file_paths(
            kb_id=req.kb_id, log_id=req.log_id
        )

        total = 0
        for log_id, file_path in rows:
            inserted = await collect_trace_context_logs(
                log_id=log_id,
                log_dir=file_path,
                trace_ids=trace_ids,
                clear_existing=False,
            )
            total += inserted

        if total:
            logger.info("Backfilled %s raw trace context rows", total)
        return total
    
    @staticmethod
    async def list_trace_failure_event_result(req: ListTraceFailureEventResultRequest) -> ListTraceFailureEventResultMsg:
        total, results = await LogFailureEventPGManager.list_trace_failure_events(req)
        for result in results:
            result.host_names = LogFailureEventResultService._normalize_unknown_host_names(
                result.host_names
            )
        return ListTraceFailureEventResultMsg(total=total, trace_failure_event_results=results)
    
    @staticmethod
    async def list_time_aggregated_failure_event_result(req: ListTimeAggregatedFailureEventRequest) -> ListTimeAggregatedFailureEventMsg:
        total, err_codes, results = await LogFailureEventPGManager.list_time_aggregated_failure_events(req)
        events = [TimeAggregatedFailureEventModel(**r) for r in results]
        return ListTimeAggregatedFailureEventMsg(total=total, err_codes=err_codes, events=events)

    @staticmethod
    async def list_pod_aggregated_failure_event_result(req: ListPodAggregatedFailureEventRequest) -> ListPodAggregatedFailureEventMsg:
        total, results = await LogFailureEventPGManager.list_pod_aggregated_failure_events(req)
        events = [PodAggregatedFailureEventModel(**r) for r in results]
        return ListPodAggregatedFailureEventMsg(total=total, events=events)

    @staticmethod
    async def list_src_dst_aggregated_failure_event_result(req: ListSrcDstAggregatedFailureEventRequest) -> ListSrcDstAggregatedFailureEventMsg:
        total, results = await LogFailureEventPGManager.list_src_dst_aggregated_failure_events(req)
        events = [SrcDstAggregatedFailureEventModel(**r) for r in results]
        return ListSrcDstAggregatedFailureEventMsg(total=total, events=events)

    @staticmethod
    async def get_err_code_metrics(req: GetErrCodeMetricsRequest) -> GetErrCodeMetricsMsg:
        """获取故障码指标时间曲线数据"""
        total, metrics = await LogFailureEventPGManager.get_err_code_metrics(req)
        return GetErrCodeMetricsMsg(
            total=total,
            metrics=metrics,
            time_range={
                "start_time": req.start_time,
                "end_time": req.end_time,
            },
        )
