from pydantic import BaseModel, Field
from typing import Optional, Any
from fastapi import UploadFile
from latency.ENUM.general import SourceType
from latency.ENUM.task import TaskStatusEnum, TaskTypeEnum
from latency.ENUM.sampling import SampleMode


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
    created_at_start: Optional[str] = Field(
        default=None,
        description="聚合事件创建时间范围查询的开始时间，格式为YYYY-MM-DD HH:MM:SS",
    )
    created_at_end: Optional[str] = Field(
        default=None,
        description="聚合事件创建时间范围查询的结束时间，格式为YYYY-MM-DD HH:MM:SS",
    )
    created_sorted_desc: bool = Field(
        default=True,
        description="聚合事件创建时间排序，True表示降序，False表示升序，默认为True",
    )
    page_cnt: int = Field(default=10, description="每页的聚合事件数量，默认为10")
    page_num: int = Field(default=1, description="页码，默认为1表示第一页")


class ListAnomalousEventChainRequest(BaseModel):
    log_id: Optional[str] = Field(default=None, description="日志文件ID，用于过滤指定日志的异常事件链")
    page_cnt: int = Field(default=10, description="每页的异常事件链数量，默认为10")
    page_num: int = Field(default=1, description="页码，默认为1表示第一页")


class ListLogParseResultRequest(BaseModel):
    log_id: Optional[str] = Field(default=None, description="日志文件ID，用于过滤指定日志的解析结果")
    src_ip: Optional[str] = Field(default=None, description="源IP地址，支持模糊查询")
    dst_ip: Optional[str] = Field(default=None, description="目的IP地址，支持模糊查询")
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
    created_sorted_desc: bool = Field(
        default=True,
        description="日志解析结果创建时间排序，True表示降序，False表示升序，默认为True",
    )
    page_cnt: int = Field(default=10, description="每页的日志解析结果数量，默认为10")
    page_num: int = Field(default=1, description="页码，默认为1表示第一页")


class ListAnomalousEventRequest(BaseModel):
    log_id: Optional[str] = Field(default=None, description="日志文件ID，用于过滤指定日志的异常事件")
    aggregated_event_id: Optional[str] = Field(default=None, description="聚合事件ID，用于过滤指定聚合事件的异常事件")
    page_cnt: int = Field(default=10, description="每页的异常事件数量，默认为10")
    page_num: int = Field(default=1, description="页码，默认为1表示第一页")


class ListTracesByHostRequest(BaseModel):
    host: str = Field(..., description="主机名或IP地址")
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


class GetLatencyMetricsRequest(BaseModel):
    """获取延迟指标时间曲线请求"""
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


class CreateTaskRequest(BaseModel):
    task_type: TaskTypeEnum = Field(..., description="任务类型")
    op_id: str = Field(..., description="操作ID，关联的业务对象ID")
    kb_id: Optional[str] = Field(default=None, description="知识库ID")
    task_name: Optional[str] = Field(default=None, description="任务名称")


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
