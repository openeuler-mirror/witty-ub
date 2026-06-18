import logging

from latency.common.trace_context import collect_trace_context_logs
from latency.database.engine import AsyncSQLiteSingleton
from latency.database.managers.log_failure_event import LogFailureEventManager
from latency.schemas.request import (
    ListLogFailureEventResultRequest,
    ListTraceFailureEventResultRequest,
    GetErrCodeMetricsRequest,
)
from latency.schemas.response import (
    ListLogFailureEventResultMsg,
    ListTraceFailureEventResultMsg,
    GetErrCodeMetricsMsg
)


logger = logging.getLogger(__name__)


class LogFailureEventResultService:
    """日志事件结果服务"""

    @staticmethod
    async def list_log_failure_event_result(req: ListLogFailureEventResultRequest) -> ListLogFailureEventResultMsg:
        total, results = await LogFailureEventManager.list_log_failure_events(req)
        if total == 0:
            backfilled = await LogFailureEventResultService._backfill_trace_context_logs(req)
            if backfilled:
                total, results = await LogFailureEventManager.list_log_failure_events(req)
        return ListLogFailureEventResultMsg(total=total, log_failure_event_results=results)

    @staticmethod
    async def _backfill_trace_context_logs(req: ListLogFailureEventResultRequest) -> int:
        trace_ids = {trace_id.strip() for trace_id in req.trace_ids if trace_id and trace_id.strip()}
        if not trace_ids or (not req.kb_id and not req.log_id):
            return 0

        where_clauses = ["existed_status = 1"]
        params: dict[str, str] = {}
        if req.kb_id and req.log_id:
            where_clauses.append("(kb_id = :kb_id OR id = :log_id)")
            params["kb_id"] = req.kb_id
            params["log_id"] = req.log_id
        elif req.kb_id:
            where_clauses.append("kb_id = :kb_id")
            params["kb_id"] = req.kb_id
        elif req.log_id:
            where_clauses.append("id = :log_id")
            params["log_id"] = req.log_id

        rows = await AsyncSQLiteSingleton().execute_query(
            f"""
            SELECT id, file_path
            FROM log_file_table
            WHERE {' AND '.join(where_clauses)}
            ORDER BY created_at DESC
            """,
            params,
        )

        total = 0
        for row in rows:
            inserted = await collect_trace_context_logs(
                log_id=row["id"],
                log_dir=row["file_path"],
                trace_ids=trace_ids,
                clear_existing=False,
            )
            total += inserted

        if total:
            logger.info("Backfilled %s raw trace context rows", total)
        return total
    
    @staticmethod
    async def list_trace_failure_event_result(req: ListTraceFailureEventResultRequest) -> ListTraceFailureEventResultMsg:
        total, results = await LogFailureEventManager.list_trace_failure_events(req)
        return ListTraceFailureEventResultMsg(total=total, trace_failure_event_results=results)
    
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
