from latency.schemas.request import ListLogParseResultRequest, ListTracesByHostRequest, GetLatencyMetricsRequest
from latency.schemas.response import (
    ListLogParseResultsMsg,
    GetLogParseResultMsg,
    ListTracesByHostMsg,
    GetLatencyMetricsMsg,
    GetLogParseOptionsMsg,
)
from latency.database.managers.log_parse_result import LogParseResultPGManager
from latency.common.sampler import LatencyMetricsSampler


class LogParseResultService:
    """日志解析结果服务"""

    @staticmethod
    async def list_log_parse_results(req: ListLogParseResultRequest) -> ListLogParseResultsMsg:
        total, results = await LogParseResultPGManager.list_log_parse_results(req)
        return ListLogParseResultsMsg(total=total, log_parse_results=results)

    @staticmethod
    async def get_log_parse_result_by_id(result_id: str) -> GetLogParseResultMsg:
        result = await LogParseResultPGManager.get_log_parse_result_by_id(result_id)
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
