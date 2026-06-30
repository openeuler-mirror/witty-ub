from pydantic import BaseModel, Field
from typing import Optional, Any, List
from fastapi import UploadFile
from latency.ENUM.general import SourceType
from latency.ENUM.task import TaskStatusEnum, TaskTypeEnum
from latency.ENUM.sampling import SampleMode


class SortField(BaseModel):
    """
    排序字段配置
    
    用于配置单个排序字段及其排序方向
    """
    field: str = Field(description="排序字段名称")
    order: Optional[str] = Field(default="desc", description="排序方向：asc升序，desc降序")


class ParseConfig(BaseModel):
    """
    日志解析配置
    
    用于配置解析器的行为，包括时间范围过滤、耗时阈值过滤等
    """
    start_time: Optional[str] = Field(
        default=None,
        description="日志内容时间范围开始，格式 YYYY-MM-DD HH:MM:SS"
    )
    end_time: Optional[str] = Field(
        default=None,
        description="日志内容时间范围结束，格式 YYYY-MM-DD HH:MM:SS"
    )
    min_elapsed_ms: Optional[int] = Field(
        default=None,
        description="最小耗时阈值（毫秒），用于过滤快速操作"
    )
    
    def is_time_filter_enabled(self) -> bool:
        """判断是否启用了时间过滤"""
        return self.start_time is not None or self.end_time is not None
    
    def is_elapsed_filter_enabled(self) -> bool:
        """判断是否启用了耗时过滤"""
        return self.min_elapsed_ms is not None


class CreateLogKnowledgeRequest(BaseModel):
    image_bytes: Optional[bytes] = Field(default=None, description="知识相关的图片数据")
    name: str = Field(..., description="知识名称")
    description: str = Field(..., description="知识描述")


class UpdateLogKnowledgeRequest(BaseModel):
    image_bytes: Optional[bytes] = Field(default=None, description="知识相关的图片数据")
    name: Optional[str] = Field(default=None, description="知识名称")
    description: Optional[str] = Field(default=None, description="知识描述")


class ListLogKnowledgeRequest(BaseModel):
    name: Optional[str] = Field(default=None, description="知识名称，支持模糊查询")
    description: Optional[str] = Field(
        default=None, description="知识描述，支持模糊查询"
    )
    created_at_start: Optional[str] = Field(
        default=None,
        description="知识创建时间范围查询的开始时间，格式为YYYY-MM-DD HH:MM:SS",
    )
    created_at_end: Optional[str] = Field(
        default=None,
        description="知识创建时间范围查询的结束时间，格式为YYYY-MM-DD HH:MM:SS",
    )
    created_sorted_desc: bool = Field(
        default=True,
        description="知识创建时间排序，True表示降序，False表示升序，默认为True",
    )
    page_cnt: int = Field(default=10, description="每页的知识数量，默认为10")
    page_num: int = Field(default=1, description="页码，默认为1表示第一页")


class UpLoadLogFileConfig(BaseModel):
    name: Optional[str] = Field(default=None, description="日志文件名称")
    source_type: Optional[SourceType] = Field(
        default=None, description="日志文件来源类型，支持local、remote和upload"
    )
    source: str | UploadFile = Field(
        default=None,
        description="日志文件来源，当source_type为local时，source为日志文件的绝对路径；当source_type为remote时，source为日志文件的URL地址；当source_type为upload时，source为上传的日志文件对象",
    )


class UpLoadLogFilesRequest(BaseModel):
    upload_log_file_configs: list[UpLoadLogFileConfig] = Field(
        default_factory=list, description="日志文件配置列表"
    )
    parse_config: Optional[ParseConfig] = Field(
        default=None, description="全局解析配置，应用于所有上传的日志文件"
    )


class UpdateLogFileRequest(BaseModel):
    name: Optional[str] = Field(default=None, description="日志文件名称")
    source_type: Optional[SourceType] = Field(
        default=None, description="日志文件来源类型，支持local、remote和upload"
    )
    source: str | UploadFile = Field(
        default=None,
        description="日志文件来源，当source_type为local时，source为日志文件的绝对路径；当source_type为remote时，source为日志文件的URL地址；当source_type为upload时，source为上传的日志文件对象",
    )


class ListLogFilesRequest(BaseModel):
    name: Optional[str] = Field(default=None, description="日志文件名称，支持模糊查询")
    parse_status: Optional[TaskStatusEnum] = Field(
        default=None,
        description="日志文件解析状态，支持查询解析中的日志文件（parsing）、解析成功的日志文件（parsed）和解析失败的日志文件（failed）",
    )
    created_at_start: Optional[str] = Field(
        default=None,
        description="日志文件创建时间范围查询的开始时间，格式为YYYY-MM-DD HH:MM:SS",
    )
    created_at_end: Optional[str] = Field(
        default=None,
        description="日志文件创建时间范围查询的结束时间，格式为YYYY-MM-DD HH:MM:SS",
    )
    created_sorted_desc: bool = Field(
        default=True,
        description="日志文件创建时间排序，True表示降序，False表示升序，默认为True",
    )
    page_cnt: int = Field(default=10, description="每页的日志文件数量，默认为10")
    page_num: int = Field(default=1, description="页码，默认为1表示第一页")


class ListSrcDstAggregatedEventRequest(BaseModel):
    log_id: Optional[str] = Field(default=None, description="日志文件ID，用于过滤指定日志的聚合事件")
    src_ip: Optional[str] = Field(default=None, description="源IP地址，支持模糊查询")
    dst_ip: Optional[str] = Field(default=None, description="目的IP地址，支持模糊查询")
    kb_id: Optional[str] = Field(default=None, description="知识库ID，用于过滤")
    created_at_start: Optional[str] = Field(
        default=None,
        description="聚合事件创建时间范围查询的开始时间，格式为YYYY-MM-DD HH:MM:SS",
    )
    created_at_end: Optional[str] = Field(
        default=None,
        description="聚合事件创建时间范围查询的结束时间，格式为YYYY-MM-DD HH:MM:SS",
    )
    stat_type: Optional[str] = Field(default="ave", description="统计类型：p99、p95、ave、min、max")
    sort_fields: Optional[List[SortField]] = Field(
        default=None,
        description="排序字段配置列表，支持多字段排序。示例：[{\"field\": \"total_latency\", \"order\": \"desc\"}, {\"field\": \"src_ip\", \"order\": \"asc\"}]"
    )
    page_cnt: int = Field(default=10, description="每页的聚合事件数量，默认为10")
    page_num: int = Field(default=1, description="页码，默认为1表示第一页")


class ListAnomalousEventChainRequest(BaseModel):
    log_id: Optional[str] = Field(default=None, description="日志文件ID，用于过滤指定日志的异常事件链")
    kb_id: Optional[str] = Field(default=None, description="知识库ID，用于过滤")
    page_cnt: int = Field(default=10, description="每页的异常事件链数量，默认为10")
    page_num: int = Field(default=1, description="页码，默认为1表示第一页")


class ListLogParseResultRequest(BaseModel):
    log_id: Optional[str] = Field(default=None, description="日志文件ID，用于过滤指定日志的解析结果")
    aggregated_event_id: Optional[str] = Field(default=None, description="聚合事件ID，用于过滤指定聚合事件的解析结果")
    kb_id: Optional[str] = Field(default=None, description="知识库ID，用于过滤")
    trace_id: Optional[str] = Field(default=None, description="Trace ID，用于过滤指定链路的解析结果")
    trace_ids: Optional[list[str]] = Field(default=None, description="Trace ID列表，用于批量查询多个链路的解析结果")
    src_ip: Optional[str] = Field(default=None, description="源IP地址，支持模糊查询")
    dst_ip: Optional[str] = Field(default=None, description="目的IP地址，支持模糊查询")
    host: Optional[str] = Field(default=None, description="主机名称，支持模糊查询")
    cluster_name: Optional[str] = Field(default=None, description="集群名称，支持模糊查询")
    start_time: Optional[str] = Field(default=None, description="日志时间戳范围开始时间，格式为YYYY-MM-DD HH:MM:SS")
    end_time: Optional[str] = Field(default=None, description="日志时间戳范围结束时间，格式为YYYY-MM-DD HH:MM:SS")
    is_anomalous: Optional[bool] = Field(
        default=None,
        description="是否为异常解析结果，True表示异常，False表示正常，None表示不区分",
    )
    created_at_start: Optional[str] = Field(
        default=None,
        description="日志解析结果创建时间范围查询的开始时间，格式为YYYY-MM-DD HH:MM:SS",
    )
    created_at_end: Optional[str] = Field(
        default=None,
        description="日志解析结果创建时间范围查询的结束时间，格式为YYYY-MM-DD HH:MM:SS",
    )
    start_time: Optional[str] = Field(
        default=None,
        description="日志事件时间范围查询的开始时间（基于timestamp字段），格式为YYYY-MM-DD HH:MM:SS",
    )
    end_time: Optional[str] = Field(
        default=None,
        description="日志事件时间范围查询的结束时间（基于timestamp字段），格式为YYYY-MM-DD HH:MM:SS",
    )
    sort_fields: Optional[List[SortField]] = Field(
        default=None,
        description="排序字段配置列表，支持多字段排序。示例：[{\"field\": \"total_latency\", \"order\": \"desc\"}, {\"field\": \"timestamp\", \"order\": \"asc\"}]"
    )
    sort_by: str = Field(
        default="created_at",
        description="排序字段，支持created_at、timestamp、total_latency、error_priority。error_priority表示失败日志优先，其次严重超时日志按总时延降序",
    )
    sort_order: str = Field(
        default="desc",
        description="排序方向，desc表示降序，asc表示升序；error_priority模式下仅用于普通日志的兜底时间排序",
    )
    severe_timeout_threshold_ms: float = Field(
        default=150.0,
        description="严重超时阈值，单位毫秒；仅sort_by=error_priority时用于区分超时日志和普通日志",
    )
    exclude_normal: bool = Field(
        default=False,
        description="是否排除正常日志，仅返回失败日志或严重超时日志",
    )
    page_cnt: int = Field(default=10, description="每页的日志解析结果数量，默认为10")
    page_num: int = Field(default=1, description="页码，默认为1表示第一页")


class ListLogFailureEventResultRequest(BaseModel):
    kb_id: Optional[str] = Field(default=None, description="日志知识库ID，用于过滤指定知识库的结果")
    log_id: Optional[str] = Field(default=None, description="日志文件路径ID，用于过滤指定日志文件路径的结果")
    trace_ids: list[str] = Field(
        default_factory=list, description="trace_id列表"
    )

class ListTraceFailureEventResultRequest(BaseModel):
    kb_id: str = Field(..., description="日志知识库ID，用于过滤指定知识库的结果")
    trace_ids: Optional[list[str]] = Field(default=None, description="Trace ID列表，用于批量查询多个链路的故障事件")
    pod_names: Optional[list[str]] = Field(
        default_factory=list, description="日志中包含的pod_id"
    )
    host_names: Optional[list[str]] = Field(
        default_factory=list, description="日志中包含的host_name"
    )
    cluster_names: Optional[list[str]] = Field(
        default_factory=list, description="日志中包含的cluster_id"
    )
    status_codes: Optional[list[str]] = Field(
        default_factory=list, description="日志中包含的status_code"
    )
    is_anomalous: Optional[bool] = Field(
        default=None,
        description="是否为异常解析结果，True表示异常，False表示正常，None表示不区分",
    )
    created_at_start: Optional[str] = Field(
        default=None,
        description="日志解析结果创建时间范围查询的开始时间，格式为YYYY-MM-DD HH:MM:SS",
    )
    created_at_end: Optional[str] = Field(
        default=None,
        description="日志解析结果创建时间范围查询的结束时间，格式为YYYY-MM-DD HH:MM:SS",
    )
    created_sorted_desc: Optional[bool] = Field(
        default=True,
        description="日志解析结果创建时间排序，True表示降序，False表示升序，默认为True",
    )
    page_cnt: int = Field(default=10, description="每页的日志解析结果数量，默认为10")
    page_num: int = Field(default=1, description="页码，默认为1表示第一页")


class ListAnomalousEventRequest(BaseModel):
    log_id: Optional[str] = Field(default=None, description="日志文件ID，用于过滤指定日志的异常事件")
    aggregated_event_id: Optional[str] = Field(default=None, description="聚合事件ID，用于过滤指定聚合事件的异常事件")
    kb_id: Optional[str] = Field(default=None, description="知识库ID，用于过滤")
    sort_fields: Optional[List[SortField]] = Field(
        default=None,
        description="排序字段配置列表，支持多字段排序。示例：[{\"field\": \"created_at\", \"order\": \"desc\"}]"
    )
    page_cnt: int = Field(default=10, description="每页的异常事件数量，默认为10")
    page_num: int = Field(default=1, description="页码，默认为1表示第一页")


class ListTracesByHostRequest(BaseModel):
    host: str = Field(..., description="主机名或IP地址")
    kb_id: Optional[str] = Field(default=None, description="知识库ID，用于过滤")
    start_time: Optional[str] = Field(
        default=None,
        description="开始时间，格式为YYYY-MM-DD HH:MM:SS",
    )
    end_time: Optional[str] = Field(
        default=None,
        description="结束时间，格式为YYYY-MM-DD HH:MM:SS",
    )
    operation: Optional[str] = Field(
        default=None,
        description="操作类型过滤：GET / SET",
    )
    is_anomalous: Optional[bool] = Field(
        default=None,
        description="是否为异常解析结果，True表示异常，False表示正常，None表示不区分",
    )
    page_cnt: int = Field(default=20, description="每页数量")
    page_num: int = Field(default=1, description="页码")
    sort_by: str = Field(default="timestamp", description="排序字段")
    sort_order: str = Field(default="desc", description="排序方向")

class ListTimeAggregatedFailureEventRequest(BaseModel):
    kb_id: Optional[str] = Field(default=None, description="知识库ID，用于过滤")
    created_at_start: Optional[str] = Field(
        default=None,
        description="聚合事件创建时间范围查询的开始时间，格式为YYYY-MM-DD HH:MM:SS",
    )
    created_at_end: Optional[str] = Field(
        default=None,
        description="聚合事件创建时间范围查询的结束时间，格式为YYYY-MM-DD HH:MM:SS",
    )
    interval: str = Field(
        default="minute",
        description="聚合事件事件间隔，可选second, minute, hour"
    )
    sort_by: str = Field(
        default="timestamp",
        description="聚合事件时间排序依据，可选timestamp"
    )
    created_sorted_desc: bool = Field(
        default=False,
        description="聚合事件创建时间排序，True表示降序，False表示升序，默认为True",
    )
    sort_fields: Optional[List[SortField]] = Field(
        default=None,
        description="排序字段配置列表，支持多字段排序。示例：[{\"field\": \"all\", \"order\": \"desc\"}, {\"field\": \"1004\", \"order\": \"asc\"}]",
    )
    page_cnt: int = Field(default=10, description="每页的聚合事件数量，默认为10")
    page_num: int = Field(default=1, description="页码，默认为1表示第一页")

class ListPodAggregatedFailureEventRequest(BaseModel):
    kb_id: Optional[str] = Field(default=None, description="知识库ID，用于过滤")
    created_at_start: Optional[str] = Field(
        default=None,
        description="聚合事件创建时间范围查询的开始时间，格式为YYYY-MM-DD HH:MM:SS",
    )
    created_at_end: Optional[str] = Field(
        default=None,
        description="聚合事件创建时间范围查询的结束时间，格式为YYYY-MM-DD HH:MM:SS",
    )
    sort_by: str = Field(
        default="all",
        description="聚合事件排序依据，可选all或故障码，如1004，1009等"
    )
    created_sorted_desc: bool = Field(
        default=True,
        description="聚合事件创建时间排序，True表示降序，False表示升序，默认为True",
    )
    sort_fields: Optional[List[SortField]] = Field(
        default=None,
        description="排序字段配置列表，支持多字段排序。示例：[{\"field\": \"all\", \"order\": \"desc\"}, {\"field\": \"1004\", \"order\": \"asc\"}]",
    )
    page_cnt: int = Field(default=10, description="每页的聚合事件数量，默认为10")
    page_num: int = Field(default=1, description="页码，默认为1表示第一页")

class GetLatencyMetricsRequest(BaseModel):
    """获取延迟指标时间曲线请求"""
    kb_id: Optional[str] = Field(default=None, description="知识库ID，用于过滤")
    host: Optional[str] = Field(default=None, description="主机名或 IP 地址，可选")
    src_ip: Optional[str] = Field(default=None, description="源 IP 地址，可选")
    dst_ip: Optional[str] = Field(default=None, description="目的 IP 地址，可选")
    start_time: Optional[str] = Field(
        default=None,
        description="开始时间，格式为 YYYY-MM-DD HH:MM:SS",
    )
    end_time: Optional[str] = Field(
        default=None,
        description="结束时间，格式为 YYYY-MM-DD HH:MM:SS",
    )
    operation: Optional[str] = Field(
        default=None,
        description="操作类型过滤：GET / SET",
    )
    max_points: int = Field(
        default=1000,
        description="最大返回数据点数，默认 1000；超过时自动触发采样；设置为 -1 返回全部数据"
    )
    sample_mode: SampleMode = Field(
        default=SampleMode.P99,
        description="采样模式：none-不采样，max-最大值，avg-平均值，min-最小值，p99/p95/p9999-百分位"
    )
    sort_by: str = Field(default="timestamp", description="排序字段")
    sort_order: str = Field(default="asc", description="排序方向，默认升序（时间正序）")

class GetErrCodeMetricsRequest(BaseModel):
    """获取故障码指标时间曲线请求"""
    kb_id: str = Field(..., description="日志知识库ID")
    err_codes: Optional[list[str]] = Field(
        default_factory=list, description="故障码"
    )
    host_names: Optional[list[str]] = Field(
        default_factory=list, description="主机名"
    )
    cluster_names: Optional[list[str]] = Field(
        default_factory=list, description="集群名"
    )
    pod_names: Optional[list[str]] = Field(
        default_factory=list, description="pod名"
    )
    start_time: Optional[str] = Field(
        default=None,
        description="开始时间，格式为YYYY-MM-DD HH:MM:SS",
    )
    end_time: Optional[str] = Field(
        default=None,
        description="结束时间，格式为YYYY-MM-DD HH:MM:SS",
    )
    max_points: int = Field(
        default=1000,
        description="最大返回数据点数，用于控制数据量，默认1000",
    )


class CreateDiagnosisCaseRequest(BaseModel):
    kb_id: Optional[str] = Field(default=None, description="来源日志知识库ID")
    fault_type: str = Field(default="unknown", description="故障类型：latency/connectivity/mixed/unknown")
    title: Optional[str] = Field(default=None, description="案例标题")
    symptom_summary: str = Field(..., description="故障现象摘要")
    root_cause: str = Field(..., description="诊断出的故障原因")
    recommendation: str = Field(..., description="建议处理方案")
    confidence: float = Field(default=0.0, description="结论置信度，0到1")
    failure_mode_ids: list[str] = Field(default_factory=list, description="关联故障模式ID")
    status_codes: list[str] = Field(default_factory=list, description="关联状态码")
    fingerprint_json: dict[str, Any] = Field(
        default_factory=dict,
        description="可泛化故障指纹，如src_ips、dst_ips、hosts、pods、clusters、latency_components、log_keywords",
    )
    evidence_refs_json: list[dict[str, Any]] = Field(default_factory=list, description="证据引用")
    counter_evidence_json: list[dict[str, Any]] = Field(default_factory=list, description="反证或排除项")
    source_log_ids: list[str] = Field(default_factory=list, description="来源日志ID")


class SearchDiagnosisCasesRequest(BaseModel):
    kb_id: Optional[str] = Field(default=None, description="知识库ID过滤")
    fault_type: Optional[str] = Field(default=None, description="故障类型过滤")
    status_codes: list[str] = Field(default_factory=list, description="待匹配状态码")
    failure_mode_ids: list[str] = Field(default_factory=list, description="待匹配故障模式ID")
    src_ips: list[str] = Field(default_factory=list, description="待匹配源IP")
    dst_ips: list[str] = Field(default_factory=list, description="待匹配目的IP")
    hosts: list[str] = Field(default_factory=list, description="待匹配主机")
    pods: list[str] = Field(default_factory=list, description="待匹配Pod")
    clusters: list[str] = Field(default_factory=list, description="待匹配集群")
    latency_components: list[str] = Field(default_factory=list, description="待匹配异常时延组件")
    log_keywords: list[str] = Field(default_factory=list, description="待匹配关键日志短语")
    min_confidence: Optional[float] = Field(default=None, description="最低案例置信度")
    page_cnt: int = Field(default=10, description="每页数量")
    page_num: int = Field(default=1, description="页码")

class CreateTaskRequest(BaseModel):
    task_type: TaskTypeEnum = Field(..., description="任务类型")
    op_id: str = Field(..., description="操作ID，关联的业务对象ID")
    kb_id: Optional[str] = Field(default=None, description="知识库ID")
    task_name: Optional[str] = Field(default=None, description="任务名称")


class ListTimeWindowAggregatedEventRequest(BaseModel):
    """时间窗口聚合事件查询请求"""
    kb_id: Optional[str] = Field(default=None, description="知识库ID，用于过滤")
    start_time: Optional[str] = Field(
        default=None,
        description="开始时间，格式为YYYY-MM-DD HH:MM:SS",
    )
    end_time: Optional[str] = Field(
        default=None,
        description="结束时间，格式为YYYY-MM-DD HH:MM:SS",
    )
    src_ip: Optional[str] = Field(default=None, description="源IP过滤")
    dst_ip: Optional[str] = Field(default=None, description="目标IP过滤")
    interval: str = Field(
        default="minute",
        description="时间窗口间隔，可选hour, minute, second"
    )
    stat_type: Optional[str] = Field(default="ave", description="统计类型：p99、p95、ave、min、max")
    sort_by: Optional[str] = Field(
        default="start_time",
        description="排序字段：start_time 或 total_latency"
    )
    sort_order: Optional[str] = Field(
        default="asc",
        description="排序方向：asc 升序，desc 降序"
    )
    page_cnt: int = Field(default=10, description="每页的时间窗口数量，默认为10")
    page_num: int = Field(default=1, description="页码，默认为1表示第一页")


class ListTasksRequest(BaseModel):
    task_type: Optional[TaskTypeEnum] = Field(default=None, description="任务类型")
    status: Optional[TaskStatusEnum] = Field(default=None, description="任务状态")
    kb_id: Optional[str] = Field(default=None, description="知识库ID")
    op_id: Optional[str] = Field(default=None, description="操作ID")
    created_at_start: Optional[str] = Field(
        default=None,
        description="任务创建时间范围查询的开始时间，格式为YYYY-MM-DD HH:MM:SS",
    )
    created_at_end: Optional[str] = Field(
        default=None,
        description="任务创建时间范围查询的结束时间，格式为YYYY-MM-DD HH:MM:SS",
    )
    created_sorted_desc: bool = Field(
        default=True,
        description="任务创建时间排序，True表示降序，False表示升序，默认为True",
    )
    page_cnt: int = Field(default=10, description="每页的任务数量，默认为10")
    page_num: int = Field(default=1, description="页码，默认为1表示第一页")
