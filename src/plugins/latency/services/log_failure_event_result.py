import logging
from typing import Any

from latency.common.trace_context import collect_trace_context_logs
from latency.database.managers.log_failure_event import LogFailureEventPGManager
from latency.database.managers.log_file import LogFilePGManager
from latency.database.managers.pod_role import PodRolePGManager
from latency.database.utils import format_timestamp
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
from latency.schemas.log_failure_event import (
    TimeAggregatedFailureEventModel,
    PodAggregatedFailureEventModel,
    SrcDstAggregatedFailureEventModel,
    PodRoleModel,
    TraceFailureEventModel,
)


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
        # Backfill raw Run-format context only when no log_failure_event rows
        # exist for the trace. The parse worker (store_trace_context_logs_worker)
        # already collects both access and runtime log lines for traces in its
        # scope, so total > 0 means the context was already collected. Re-running
        # the backfill when rows already exist would (a) waste time re-scanning
        # the entire KB directory and (b) insert duplicate rows: the parse worker
        # uses random uuid4 ids while the backfill uses deterministic
        # uuid5(log_id:trace_id:raw_text) ids, so on_conflict_do_nothing never
        # collides and the same raw_text lands twice.
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
        await LogFailureEventResultService._attach_pod_roles(req, results)
        return ListTraceFailureEventResultMsg(total=total, trace_failure_event_results=results)

    @staticmethod
    async def _attach_pod_roles(
        req: ListTraceFailureEventResultRequest,
        results: list[TraceFailureEventModel],
    ) -> None:
        """把 pod_role 聚合结果挂到每个 trace 响应上（一次批量查询）。

        pod_role 按 trace_id 全局聚合，同一 trace 在多个 log_id 下可能都有
        角色记录（同一批日志被多个资产库上传/解析）。这里不按 kb 的 log_ids
        过滤，全量查询后在结果中优先取属于当前 kb 日志的行，避免部分 trace
        匹配不到角色。
        """
        trace_ids = [r.trace_id for r in results if r.trace_id]
        if not trace_ids:
            return
        log_ids = await LogFailureEventPGManager._log_ids_for_kb_id(req.kb_id)
        log_ids_set = set(log_ids)
        roles = await PodRolePGManager.list_pod_roles_by_trace_ids(
            trace_ids, log_ids=None
        )
        role_by_trace: dict[str, Any] = {}
        for role in roles:
            prev = role_by_trace.get(role.trace_id)
            if prev is None or (role.log_id in log_ids_set and prev.log_id not in log_ids_set):
                role_by_trace[role.trace_id] = role
        for result in results:
            role = role_by_trace.get(result.trace_id)
            if role is None:
                continue
            result.pod_role = PodRoleModel(
                trace_id=role.trace_id or "",
                log_id=role.log_id,
                operation=role.operation or "",
                client_pod=role.client_pod,
                entry_worker_pods=role.entry_worker_pods or [],
                meta_worker_pods=role.meta_worker_pods or [],
                data_worker_pods=role.data_worker_pods or [],
                timestamp=format_timestamp(role.timestamp) or "",
            )
    
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
