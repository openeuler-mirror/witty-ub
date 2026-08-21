from pydantic import BaseModel, Field
from typing import Optional, Any
from latency.schemas.log import (
    LogKnowledgeModel,
    LogFileModel,
    SrcDstAggregatedEventModel,
    AnomalousEventModel,
    AnomalousEventChainModel,
    LogParseResultModel,
    TimeWindowAggregatedEventModel,
)
from latency.schemas.failure_mode import (
    FailureModeModel,
    StatusCodeKnowledgeModel,
)
from latency.schemas.log_failure_event import (
    LogFailureEventModel,
    TraceFailureEventModel,
    ErrCodeMetricItem,
    PodAggregatedFailureEventModel,
    SrcDstAggregatedFailureEventModel,
    TimeAggregatedFailureEventModel,
)
from latency.schemas.diagnosis_case import (
    DiagnosisCaseMatchModel,
    DiagnosisCaseModel,
)
from latency.schemas.task import TaskModel


class ResponseBase(BaseModel):
    code: int = Field(default=200, description="响应状态码")
    message: str = Field(default="success", description="响应消息")
    result: Any = Field(..., description="响应结果")


class CreateLogKnowledgeMsg(BaseModel):
    kb_id: Optional[str] = Field(default=None, description="创建的知识ID")


class CreateLogKnowledgeResponse(ResponseBase):
    result: CreateLogKnowledgeMsg = Field(..., description="创建日志知识响应结果")


class DeleteLogKnowledgeMsg(BaseModel):
    kb_id: Optional[str] = Field(default=None, description="删除的知识ID")


class DeleteLogKnowledgeResponse(ResponseBase):
    result: DeleteLogKnowledgeMsg = Field(..., description="删除日志知识响应结果")


class UpdateLogKnowledgeMsg(BaseModel):
    kb_id: Optional[str] = Field(default=None, description="更新的知识ID")


class UpdateLogKnowledgeResponse(ResponseBase):
    result: UpdateLogKnowledgeMsg = Field(..., description="更新日志知识响应结果")


class ListLogKnowledgeMsg(BaseModel):
    total: int = Field(..., description="符合条件的知识总数")
    kbs: list[LogKnowledgeModel] = Field(default_factory=list, description="知识列表")


class ListLogKnowledgeResponse(ResponseBase):
    result: ListLogKnowledgeMsg = Field(..., description="查询日志知识列表响应结果")


class GetLogKnowledgeMsg(BaseModel):
    kb: Optional[LogKnowledgeModel] = Field(default=None, description="知识详情")


class GetLogKnowledgeResponse(ResponseBase):
    result: GetLogKnowledgeMsg = Field(..., description="查询日志知识详情响应结果")


class UploadLogFilesMsg(BaseModel):
    log_file_ids: list[str] = Field(
        default_factory=list, description="上传日志文件的ID列表"
    )


class UploadLogFilesResponse(ResponseBase):
    result: UploadLogFilesMsg = Field(..., description="上传日志文件响应结果")


class DeleteLogFilesMsg(BaseModel):
    log_file_ids: list[str] = Field(
        default_factory=list, description="删除日志文件的ID列表"
    )


class DeleteLogFilesResponse(ResponseBase):
    result: DeleteLogFilesMsg = Field(..., description="删除日志文件响应结果")


class RunOrStopLogParseMsg(BaseModel):
    task_id: Optional[str] = Field(
        default=None, description="运行或停止日志解析的任务ID"
    )


class RunOrStopLogParseResponse(ResponseBase):
    result: RunOrStopLogParseMsg = Field(..., description="运行或停止日志解析响应结果")


class RunBrpcDiagnosisMsg(BaseModel):
    task_id: str = Field(..., description="BRPC 诊断任务 ID")


class RunBrpcDiagnosisResponse(ResponseBase):
    result: RunBrpcDiagnosisMsg = Field(..., description="BRPC 诊断任务创建结果")


class UpdateLogFileMsg(BaseModel):
    log_file_id: Optional[str] = Field(default=None, description="更新的日志文件ID")


class UpdateLogFileResponse(ResponseBase):
    result: UpdateLogFileMsg = Field(..., description="更新日志文件响应结果")


class ListLogFilesMsg(BaseModel):
    total: int = Field(..., description="符合条件的日志文件总数")
    log_files: list[LogFileModel] = Field(
        default_factory=list, description="日志文件列表"
    )


class ListLogFilesResponse(ResponseBase):
    result: ListLogFilesMsg = Field(..., description="查询日志文件列表响应结果")


class GetLogFileMsg(BaseModel):
    log_file: Optional[LogFileModel] = Field(default=None, description="日志文件详情")


class GetLogFileResponse(ResponseBase):
    result: GetLogFileMsg = Field(..., description="查询日志文件详情响应结果")


class GetFailureModeMsg(BaseModel):
    failure_mode: Optional[FailureModeModel] = Field(default=None, description="故障模式详情")


class GetFailureModeResponse(ResponseBase):
    result: GetFailureModeMsg = Field(..., description="查询故障模式详情响应结果")


class GetStatusCodeKnowledgeMsg(BaseModel):
    status_code_info: Optional[StatusCodeKnowledgeModel] = Field(
        default=None, description="故障码知识详情"
    )


class GetStatusCodeKnowledgeResponse(ResponseBase):
    result: GetStatusCodeKnowledgeMsg = Field(..., description="查询故障码知识响应结果")


class ListSrcDstAggregatedEventMsg(BaseModel):
    total: int = Field(..., description="符合条件的聚合事件总数")
    events: list[SrcDstAggregatedEventModel] = Field(
        default_factory=list, description="聚合事件列表"
    )


class ListSrcDstAggregatedEventResponse(ResponseBase):
    result: ListSrcDstAggregatedEventMsg = Field(
        ..., description="查询聚合事件列表响应结果"
    )


class ListTimeAggregatedFailureEventMsg(BaseModel):
    total: int = Field(..., description="符合条件的时间段总数")
    err_codes: list[str] = Field(..., description="故障码列表")
    events: list[TimeAggregatedFailureEventModel] = Field(
        default_factory=list, description="聚合时间段列表"
    )


class ListTimeAggregatedFailureEventResponse(ResponseBase):
    result: ListTimeAggregatedFailureEventMsg = Field(
        ..., description="查询聚合时间列表相应结果"
    )


class ListPodAggregatedFailureEventMsg(BaseModel):
    total: int = Field(..., description="符合条件的聚合事件总数")
    events: list[PodAggregatedFailureEventModel] = Field(
        default_factory=list, description="聚合事件列表"
    )


class ListPodAggregatedFailureEventResponse(ResponseBase):
    result: ListPodAggregatedFailureEventMsg = Field(
        ..., description="查询聚合事件列表相应结果"
    )


class ListSrcDstAggregatedFailureEventMsg(BaseModel):
    total: int = Field(..., description="符合条件的聚合事件总数")
    events: list[SrcDstAggregatedFailureEventModel] = Field(
        default_factory=list, description="聚合事件列表"
    )


class ListSrcDstAggregatedFailureEventResponse(ResponseBase):
    result: ListSrcDstAggregatedFailureEventMsg = Field(
        ..., description="查询聚合事件列表相应结果"
    )


class GetSrcDstAggregatedEventMsg(BaseModel):
    event: Optional[SrcDstAggregatedEventModel] = Field(
        default=None, description="聚合事件详情"
    )


class GetSrcDstAggregatedEventResponse(ResponseBase):
    result: GetSrcDstAggregatedEventMsg = Field(
        ..., description="查询聚合事件详情响应结果"
    )


class GetAnomalousEventMsg(BaseModel):
    event: Optional[AnomalousEventModel] = Field(
        default=None, description="异常事件详情"
    )


class GetAnomalousEventResponse(ResponseBase):
    result: GetAnomalousEventMsg = Field(..., description="查询异常事件详情响应结果")


class ListAnomalousEventsMsg(BaseModel):
    total: int = Field(..., description="符合条件的异常事件总数")
    events: list[AnomalousEventModel] = Field(
        default_factory=list, description="异常事件列表"
    )


class ListAnomalousEventsResponse(ResponseBase):
    result: ListAnomalousEventsMsg = Field(
        ..., description="查询异常事件列表响应结果"
    )


class ListAnomalousEventChainsMsg(BaseModel):
    total: int = Field(..., description="符合条件的异常事件链总数")
    event_chains: list[AnomalousEventChainModel] = Field(
        default_factory=list, description="异常事件链列表"
    )


class ListAnomalousEventChainsResponse(ResponseBase):
    result: ListAnomalousEventChainsMsg = Field(
        ..., description="查询异常事件链列表响应结果"
    )


class ListLogParseResultsMsg(BaseModel):
    total: int = Field(..., description="符合条件的日志解析结果总数")
    log_parse_results: list[LogParseResultModel] = Field(
        default_factory=list, description="日志解析结果列表"
    )


class ListLogParseResultsResponse(ResponseBase):
    result: ListLogParseResultsMsg = Field(
        ..., description="查询日志解析结果列表响应结果"
    )


class ListLogFailureEventResultMsg(BaseModel):
    total: int = Field(..., description="符合条件的log解析结果总数")
    log_failure_event_results: list[LogFailureEventModel] = Field(
        default_factory=list, description="故障日志结果列表"
    )

class ListLogFailureEventResultResponse(ResponseBase):
    result: ListLogFailureEventResultMsg = Field(
        ..., description="查询故障日志列表响应结果"
    )

class ListTraceFailureEventResultMsg(BaseModel):
    total: int = Field(..., description="符合条件的trace解析结果总数")
    trace_failure_event_results: list[TraceFailureEventModel] = Field(
        default_factory=list, description="故障Trace结果列表"
    )

class ListTraceFailureEventResultResponse(ResponseBase):
    result: ListTraceFailureEventResultMsg = Field(
        ..., description="查询故障Trace列表响应结果"
    )

class GetLogParseResultMsg(BaseModel):
    log_parse_result: Optional[LogParseResultModel] = Field(
        default=None, description="日志解析结果详情"
    )


class GetLogParseResultResponse(ResponseBase):
    result: GetLogParseResultMsg = Field(..., description="查询日志解析结果详情响应结果")


class TraceItem(BaseModel):
    trace_id: str = Field(..., description="追踪ID")
    pod_id: str = Field(..., description="Pod ID/名称")
    time: str = Field(..., description="时间戳")
    sdk_ms: float = Field(..., description="SDK端到端延迟(毫秒)")
    req_delay_ms: float = Field(..., description="请求延迟(毫秒)")
    rsp_delay_ms: float = Field(..., description="响应延迟(毫秒)")
    is_anomalous: bool = Field(default=False, description="是否为异常")


class ListTracesByHostMsg(BaseModel):
    total: int = Field(..., description="符合条件的trace总数")
    traces: list[TraceItem] = Field(default_factory=list, description="trace列表")


class ListTracesByHostResponse(ResponseBase):
    result: ListTracesByHostMsg = Field(..., description="查询trace列表响应结果")


class GetLatencyMetricsMsg(BaseModel):
    """延迟指标时间曲线响应"""
    total: int = Field(..., description="符合条件的数据点总数")
    metrics: list[dict] = Field(default_factory=list, description="延迟指标时间序列数据")
    time_range: dict = Field(
        default_factory=dict,
        description="实际查询的时间范围",
    )
    sampling_info: dict = Field(
        default_factory=dict,
        description="采样信息：{mode, window_ms, original_count, sampled_count}"
    )


class GetLatencyMetricsResponse(ResponseBase):
    result: GetLatencyMetricsMsg = Field(..., description="获取延迟指标时间曲线响应结果")


class GetErrCodeMetricsMsg(BaseModel):
    """故障码指标时间曲线响应"""
    total: int = Field(..., description="符合条件的数据点总数")
    metrics: dict[str, list[ErrCodeMetricItem]] = Field(default_factory=dict, description="故障码指标时间序列数据")
    time_range: dict = Field(
        default_factory=dict,
        description="实际查询的时间范围",
    )

class GetErrCodeMetricsResponse(ResponseBase):
    result: GetErrCodeMetricsMsg = Field(..., description="获取故障码指标时间曲线响应结果")


class CreateDiagnosisCaseMsg(BaseModel):
    case_id: Optional[str] = Field(default=None, description="创建的历史诊断案例ID")


class CreateDiagnosisCaseResponse(ResponseBase):
    result: CreateDiagnosisCaseMsg = Field(..., description="创建历史诊断案例响应结果")


class GetDiagnosisCaseMsg(BaseModel):
    case: Optional[DiagnosisCaseModel] = Field(default=None, description="历史诊断案例")


class GetDiagnosisCaseResponse(ResponseBase):
    result: GetDiagnosisCaseMsg = Field(..., description="获取历史诊断案例响应结果")


class SearchDiagnosisCasesMsg(BaseModel):
    total: int = Field(..., description="匹配的历史诊断案例总数")
    matches: list[DiagnosisCaseMatchModel] = Field(
        default_factory=list, description="历史诊断案例匹配列表"
    )


class SearchDiagnosisCasesResponse(ResponseBase):
    result: SearchDiagnosisCasesMsg = Field(..., description="搜索历史诊断案例响应结果")


class StopOrRunLogParseMsg(BaseModel):
    success: bool = Field(..., description="操作是否成功")


class StopOrRunLogParseResponse(ResponseBase):
    result: StopOrRunLogParseMsg = Field(..., description="停止或运行日志解析响应结果")


class CreateTaskMsg(BaseModel):
    task_id: Optional[str] = Field(default=None, description="创建的任务ID")


class CreateTaskResponse(ResponseBase):
    result: CreateTaskMsg = Field(..., description="创建任务响应结果")


class StopTaskMsg(BaseModel):
    task_id: Optional[str] = Field(default=None, description="停止的任务ID")


class StopTaskResponse(ResponseBase):
    result: StopTaskMsg = Field(..., description="停止任务响应结果")


class DeleteTaskMsg(BaseModel):
    task_id: Optional[str] = Field(default=None, description="删除的任务ID")


class DeleteTaskResponse(ResponseBase):
    result: DeleteTaskMsg = Field(..., description="删除任务响应结果")


class ListTasksMsg(BaseModel):
    total: int = Field(..., description="符合条件的任务总数")
    tasks: list[TaskModel] = Field(default_factory=list, description="任务列表")


class ListTasksResponse(ResponseBase):
    result: ListTasksMsg = Field(..., description="查询任务列表响应结果")


class GetTaskMsg(BaseModel):
    task: Optional[TaskModel] = Field(default=None, description="任务详情")


class GetTaskResponse(ResponseBase):
    result: GetTaskMsg = Field(..., description="查询任务详情响应结果")


class GetLogParseOptionsMsg(BaseModel):
    clusters: list[str] = Field(default_factory=list, description="集群名称列表")
    hosts: list[str] = Field(default_factory=list, description="主机名称列表")


class GetLogParseOptionsResponse(ResponseBase):
    result: GetLogParseOptionsMsg = Field(..., description="获取日志解析选项响应结果")


class ListTimeWindowAggregatedEventMsg(BaseModel):
    total: int = Field(..., description="符合条件的时间窗口总数")
    events: list[TimeWindowAggregatedEventModel] = Field(
        default_factory=list, description="时间窗口聚合事件列表"
    )


class ListTimeWindowAggregatedEventResponse(ResponseBase):
    result: ListTimeWindowAggregatedEventMsg = Field(
        ..., description="查询时间窗口聚合事件列表响应结果"
    )


# ============================================================
# BRPC Profiling
# ============================================================
class BrpcProfilingDataMsg(BaseModel):
    interface_names: list[str] = Field(default_factory=list, description="所有接口名列表")
    file_names: list[str] = Field(default_factory=list, description="所有源文件名列表")
    rows: list[dict] = Field(default_factory=list, description="时序数据行")


class BrpcProfilingDataResponse(ResponseBase):
    result: BrpcProfilingDataMsg = Field(..., description="BRPC profiling 数据")
