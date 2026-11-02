from latency.schemas.request import ListLogParseResultRequest, ListTracesByHostRequest, GetLatencyMetricsRequest
from latency.schemas.response import (
    ListLogParseResultsMsg,
    GetLogParseResultMsg,
    ListTracesByHostMsg,
    GetLatencyMetricsMsg,
    GetLogParseOptionsMsg,
)
from latency.schemas.log_failure_event import PodRoleModel
from latency.schemas.log import LogParseResultModel
from latency.database.managers.log_parse_result import LogParseResultPGManager
from latency.database.managers.log_failure_event import LogFailureEventPGManager
from latency.database.managers.pod_role import PodRolePGManager
from latency.database.utils import format_timestamp
from latency.common.sampler import LatencyMetricsSampler
from latency.exceptions import NotFoundBizException
from typing import Any


class LogParseResultService:
    """日志解析结果服务"""

    @staticmethod
    async def list_log_parse_results(req: ListLogParseResultRequest) -> ListLogParseResultsMsg:
        total, results = await LogParseResultPGManager.list_log_parse_results(req)
        trace_ids = sorted({row.trace_id for row in results if row.trace_id})
        if trace_ids:
            # Match the runtime log dialog's KB/log scope in one page query.
            context_pods = await LogFailureEventPGManager.get_trace_pod_names(
                trace_ids, kb_id=req.kb_id, log_id=req.log_id,
            )
            for row in results:
                pods = context_pods.get(row.trace_id)
                if pods:
                    row.pod_ips = sorted(set(row.pod_ips or []) | set(pods))
        await LogParseResultService._attach_pod_roles(req, results)
        return ListLogParseResultsMsg(total=total, log_parse_results=results)

    @staticmethod
    async def _attach_pod_roles(
        req: ListLogParseResultRequest,
        results: list[LogParseResultModel],
    ) -> None:
        """把 pod_role 聚合结果挂到每个解析结果响应上（一次批量查询）。

        供时延故障监控的 Top500 / 异常 Trace 列表按角色着色 Pod 标签使用。

        注意：pod_role 按 trace_id 全局聚合，同一批日志被多个资产库上传时，
        同一 trace_id 会在不同 log_id 下各有一条角色记录。这里不按 kb 的
        log_ids 过滤（否则 Top500 中大部分 trace 匹配不到角色），而是在
        全量结果中优先取属于当前 kb 日志的那一行，取不到时回退任意一行。
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
    async def get_log_parse_result_by_id(result_id: str) -> GetLogParseResultMsg:
        result = await LogParseResultPGManager.get_log_parse_result_by_id(result_id)
        if result is None or not result.existed_status:
            raise NotFoundBizException(resource="日志解析结果")
        return GetLogParseResultMsg(log_parse_result=result)

    @staticmethod
    async def list_traces_by_host(req: ListTracesByHostRequest) -> ListTracesByHostMsg:
        """根据主机获取trace列表"""
        total, traces = await LogParseResultPGManager.list_traces_by_host(req)
        return ListTracesByHostMsg(total=total, traces=traces)

    @staticmethod
    async def get_latency_metrics(req: GetLatencyMetricsRequest) -> GetLatencyMetricsMsg:
        """获取延迟指标时间曲线数据"""
        # 从数据库获取分桶数据（dict 列表）
        total, rows = await LogParseResultPGManager.get_latency_metrics(req)

        # 桶模式（前端传 bucket_seconds，Pydantic 默认 60）：统计表已按粒度预聚合出
        # 代表行（每 (桶, op, mode) 一行），行数 = 桶数 ≤ 8640，直接透传，
        # 不得再做二次 p99-of-p99 / 窗口降采样
        bucket_mode = req.bucket_seconds is not None
        if bucket_mode:
            sampled_metrics = rows
            sampling_info = {
                "mode": req.sample_mode.value,
                "window_ms": 0,
                "original_count": total,
                "sampled_count": len(rows),
            }
        else:
            # 非桶模式（无 bucket_seconds，旧调用）：对原始数据做窗口采样
            sampled_metrics, sampling_info = LatencyMetricsSampler.sample(
                metrics=rows,
                max_points=req.max_points,
                sample_mode=req.sample_mode,
                original_count=total,
            )

        return GetLatencyMetricsMsg(
            total=total,
            metrics=sampled_metrics,
            time_range={
                "start_time": req.start_time,
                "end_time": req.end_time,
            },
            sampling_info=sampling_info,
        )

    @staticmethod
    async def get_log_parse_options(kb_id: str | None = None) -> GetLogParseOptionsMsg:
        """获取日志解析选项（集群和主机列表）"""
        clusters = await LogParseResultPGManager.get_cluster_list(kb_id)
        hosts = await LogParseResultPGManager.get_host_list(kb_id)
        return GetLogParseOptionsMsg(clusters=clusters, hosts=hosts)
