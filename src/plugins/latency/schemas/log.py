import uuid
from typing import Optional
from pydantic import BaseModel, Field, field_serializer
from datetime import datetime
from latency.schemas.task import TaskModel
from latency.ENUM.task import TaskStatusEnum


class LogKnowledgeModel(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), description="知识ID")
    image_bytes: Optional[bytes] = Field(default=None, description="知识相关的图片数据")
    name: str = Field(..., description="知识名称")
    description: str = Field(..., description="知识描述")
    task_cnt: int = Field(0, description="关联的任务数量")
    log_file_cnt: int = Field(0, description="关联的日志文件数量")
    anomaly_cnt: int = Field(0, description="关联的异常数量")
    existed_status: bool = Field(
        True, description="知识是否存在的状态，默认为True表示存在"
    )
    created_at: str = Field(
        default_factory=lambda: datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3],
        description="知识创建时间",
    )
    updated_at: str = Field(
        default_factory=lambda: datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3],
        description="知识更新时间",
    )


class LogFileModel(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), description="日志文件ID")
    kb_id: str = Field(default="", description="关联的知识ID")
    name: str = Field(default="", description="日志文件名称")
    parse_status: TaskStatusEnum = Field(
        default=TaskStatusEnum.PENDING,
        description="日志文件解析状态，支持查询解析中的日志文件（parsing）、解析成功的日志文件（parsed）和解析失败的日志文件（failed）",
    )
    file_path: str = Field(default="", description="日志文件路径")
    file_size: int = Field(default=0, description="日志文件大小，单位字节")
    anomaly_cnt: int = Field(default=0, description="日志文件中包含的异常数量")
    task: TaskModel | None = Field(default=None, description="日志文件关联的任务")
    existed_status: bool = Field(
        default=True, description="知识是否存在的状态，默认为True表示存在"
    )
    created_at: str = Field(
        default_factory=lambda: datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3],
        description="日志文件创建时间",
    )


class SrcDstAggregatedEventModel(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), description="事件ID")
    src_ip: str = Field(..., description="源IP地址")
    dst_ip: str = Field(..., description="目的IP地址")
    log_id: str = Field(..., description="关联的日志ID")
    log_parse_result_cnt: int = Field(0, description="日志解析结果数量")
    anomaly_log_parse_result_cnt: int = Field(0, description="异常日志解析结果数量")
    anomaly_cnt: int = Field(0, description="异常数量")
    ave_total_latency: float | None = Field(
        default=None, description="平均总延迟，单位毫秒"
    )
    min_total_latency: float | None = Field(
        default=None, description="最小总延迟，单位毫秒"
    )
    max_total_latency: float | None = Field(
        default=None, description="最大总延迟，单位毫秒"
    )
    p99_total_latency: float | None = Field(
        default=None, description="总延迟的99百分位，单位毫秒"
    )
    p95_total_latency: float | None = Field(
        default=None, description="总延迟的95百分位，单位毫秒"
    )
    ave_query_meta_latency: float | None = Field(
        default=None, description="平均查询元数据延迟，单位毫秒"
    )
    min_query_meta_latency: float | None = Field(
        default=None, description="最小查询元数据延迟，单位毫秒"
    )
    max_query_meta_latency: float | None = Field(
        default=None, description="最大查询元数据延迟，单位毫秒"
    )
    p99_query_meta_latency: float | None = Field(
        default=None, description="查询元数据延迟的99百分位，单位毫秒"
    )
    p95_query_meta_latency: float | None = Field(
        default=None, description="查询元数据延迟的95百分位，单位毫秒"
    )
    ave_urma_total_latency: float | None = Field(
        default=None, description="平均URMA总延迟，单位毫秒"
    )
    min_urma_total_latency: float | None = Field(
        default=None, description="最小URMA总延迟，单位毫秒"
    )
    max_urma_total_latency: float | None = Field(
        default=None, description="最大URMA总延迟，单位毫秒"
    )
    p99_urma_total_latency: float | None = Field(
        default=None, description="URMA总延迟的99百分位，单位毫秒"
    )
    p95_urma_total_latency: float | None = Field(
        default=None, description="URMA总延迟的95百分位，单位毫秒"
    )
    ave_urma_link_latency: float | None = Field(
        default=None, description="平均URMA建链延迟，单位毫秒"
    )
    min_urma_link_latency: float | None = Field(
        default=None, description="最小URMA建链延迟，单位毫秒"
    )
    max_urma_link_latency: float | None = Field(
        default=None, description="最大URMA建链延迟，单位毫秒"
    )
    p99_urma_link_latency: float | None = Field(
        default=None, description="URMA建链延迟的99百分位，单位毫秒"
    )
    p95_urma_link_latency: float | None = Field(
        default=None, description="URMA建链延迟的95百分位，单位毫秒"
    )
    ave_c2w_urma_latency: float | None = Field(
        default=None, description="平均C2W URMA延迟，单位毫秒"
    )
    min_c2w_urma_latency: float | None = Field(
        default=None, description="最小C2W URMA延迟，单位毫秒"
    )
    max_c2w_urma_latency: float | None = Field(
        default=None, description="最大C2W URMA延迟，单位毫秒"
    )
    p99_c2w_urma_latency: float | None = Field(
        default=None, description="C2W URMA延迟的99百分位，单位毫秒"
    )
    p95_c2w_urma_latency: float | None = Field(
        default=None, description="C2W URMA延迟的95百分位，单位毫秒"
    )
    ave_w2w_urma_latency: float | None = Field(
        default=None, description="平均W2W URMA延迟，单位毫秒"
    )
    min_w2w_urma_latency: float | None = Field(
        default=None, description="最小W2W URMA延迟，单位毫秒"
    )
    max_w2w_urma_latency: float | None = Field(
        default=None, description="最大W2W URMA延迟，单位毫秒"
    )
    p99_w2w_urma_latency: float | None = Field(
        default=None, description="W2W URMA延迟的99百分位，单位毫秒"
    )
    p95_w2w_urma_latency: float | None = Field(
        default=None, description="W2W URMA延迟的95百分位，单位毫秒"
    )
    existed_status: bool = Field(
        True, description="知识是否存在的状态，默认为True表示存在"
    )
    created_at: str = Field(
        default_factory=lambda: datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3],
        description="事件创建时间",
    )


class AnomalousEventModel(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), description="异常事件ID")
    log_id: str = Field(default="", description="关联的日志ID")
    aggregated_event_id: str = Field(
        default="",
        description="关联的聚合事件ID，如果该异常事件是从聚合事件中识别出来的，则记录对应的聚合事件ID",
    )
    start_log_parse_offset: int = Field(
        default=0, description="异常事件在日志解析结果中的起始偏移量"
    )
    end_log_parse_offset: int = Field(
        default=0, description="异常事件在日志解析结果中的结束偏移量"
    )
    anomaly_reason: str = Field(default="", description="异常原因描述")
    existed_status: bool = Field(
        True, description="知识是否存在的状态，默认为True表示存在"
    )
    created_at: str = Field(
        default_factory=lambda: datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3],
        description="异常事件创建时间",
    )


class AnomalousEventChainModel(BaseModel):
    id: str = Field(
        default_factory=lambda: str(uuid.uuid4()), description="异常事件链ID"
    )
    log_id: str = Field(..., description="关联的日志ID")
    anomalous_event_id: str = Field(..., description="关联的异常事件ID")
    name: str = Field(default="default_chain", description="异常事件链名称")
    description: str = Field(default="", description="异常事件链描述")
    anomaly_code: str = Field(default="default_anomaly_code", description="异常代码")
    offset: int = Field(default=0, description="异常事件链的顺序偏移量")
    existed_status: bool = Field(
        True, description="知识是否存在的状态，默认为True表示存在"
    )
    created_at: str = Field(
        default_factory=lambda: datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3],
        description="异常事件链创建时间",
    )


class LogParseResultModel(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), description="解析结果ID")
    log_id: str = Field(default="", description="关联的日志目录路径")
    aggregated_event_id: str = Field(
        default="",
        description="关联的聚合事件ID，如果该解析结果是从聚合事件中识别出来的，则记录对应的聚合事件ID",
    )
    anomalous_event_id: str = Field(
        default="",
        description="关联的异常事件ID，如果该解析结果是从异常事件中识别出来的，则记录对应的异常事件ID",
    )
    pod_ip: Optional[str] = Field(default=None, description="Pod IP地址")
    src_ip: Optional[str] = Field(default=None, description="源IP地址")
    dst_ip: Optional[str] = Field(default=None, description="目的IP地址")
    is_anomalous: bool = Field(..., description="是否为异常解析结果")
    anomaly_reason: Optional[str] = Field(default=None, description="异常原因描述")
    anomaly_score: Optional[float] = Field(
        default=None, description="异常评分，范围通常为0.0到1.0"
    )
    content: Optional[str] = Field(default=None, description="解析结果的原始内容")
    data_size: Optional[str] = Field(default=None, description="数据大小")
    existed_status: bool = Field(
        True, description="知识是否存在的状态，默认为True表示存在"
    )
    offset: Optional[int] = Field(default=None, description="解析结果在日志中的偏移量")
    operation: Optional[str] = Field(default=None, description="操作类型")
    remark: Optional[str] = Field(default=None, description="备注信息")
    trace_id: Optional[str] = Field(default=None, description="追踪ID")
    total_latency: float = Field(..., description="总延迟，单位毫秒")
    urma_inflight_count: Optional[int] = Field(default=None, description="在途写请求数")
    urma_link_latency: Optional[float] = Field(
        default=None, description="URMA建链延迟，单位毫秒"
    )
    urma_total_latency: Optional[float] = Field(
        default=None, description="URMA总延迟，单位毫秒"
    )
    c2w_latency: Optional[float] = Field(
        default=None, description="Client到本地worker延迟，单位毫秒"
    )
    worker_query_meta_latency: Optional[float] = Field(
        default=None, description="Worker查询元数据延迟(w1->w2)，单位毫秒"
    )
    c2w_urma_latency: Optional[float] = Field(
        default=None, description="（故障情况）C2W URMA延迟，单位毫秒"
    )
    w2w_urma_latency: Optional[float] = Field(
        default=None, description="W2W URMA延迟，单位毫秒"
    )
    timestamp: Optional[str] = Field(default=None, description="事件时间戳")
    created_at: str = Field(
        default_factory=lambda: datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3],
        description="日志解析结果创建时间",
    )


class LatencyMetricItem(BaseModel):
    """延迟指标数据点（用于时间曲线）"""
    time: str = Field(..., description="时间戳")
    total_latency: Optional[float] = Field(default=None, description="总延迟，单位毫秒")
    urma_total_latency: Optional[float] = Field(default=None, description="URMA总延迟，单位毫秒")
    worker_query_meta_latency: Optional[float] = Field(default=None, description="Worker查询元数据延迟，单位毫秒")
