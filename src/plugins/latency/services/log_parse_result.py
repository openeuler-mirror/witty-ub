from latency.schemas.request import ListLogParseResultRequest, ListTracesByHostRequest, GetLatencyMetricsRequest
from latency.schemas.response import (
    ListLogParseResultsMsg,
    GetLogParseResultMsg,
    ListTracesByHostMsg,
    GetLatencyMetricsMsg,
    GetLogParseOptionsMsg,
)
from latency.database.managers.log_parse_result import LogParseResultManager
from latency.common.sampler import LatencyMetricsSampler


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
        # 从数据库获取分桶数据（dict 列表）
        total, rows = await LogParseResultManager.get_latency_metrics(req)
        
        # 对分桶数据做聚合（JSON 数组 → 单值）或原始数据采样
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
        clusters = await LogParseResultManager.get_cluster_list(kb_id)
        hosts = await LogParseResultManager.get_host_list(kb_id)
        return GetLogParseOptionsMsg(clusters=clusters, hosts=hosts)
