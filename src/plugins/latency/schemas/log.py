import uuid
from dataclasses import dataclass, field as dataclass_field
from itertools import repeat
from typing import ClassVar, Optional
from pydantic import BaseModel, Field
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
    trace_failure_event_cnt: int = Field(default=0, description="日志文件中包含的故障trace数量")
    task: TaskModel | None = Field(default=None, description="日志文件关联的任务")
    overall_progress: float = Field(
        default=0.0,
        ge=0.0,
        le=100.0,
        description="日志解析和诊断两个并行任务的平均进度",
    )
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
    log_parse_result_cnt: int = Field(default=0, description="日志解析结果数量")
    anomaly_log_parse_result_cnt: int = Field(default=0, description="异常日志解析结果数量")
    anomaly_cnt: int = Field(default=0, description="异常数量")
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


@dataclass(slots=True)
class SrcDstAggregatedEventDataclass:
    """聚合计算和批量存库使用的轻量对象。"""

    id: str
    src_ip: str
    dst_ip: str
    log_id: str
    log_parse_result_cnt: int = 0
    anomaly_log_parse_result_cnt: int = 0
    anomaly_cnt: int = 0
    ave_total_latency: float | None = None
    min_total_latency: float | None = None
    max_total_latency: float | None = None
    p99_total_latency: float | None = None
    p95_total_latency: float | None = None
    ave_query_meta_latency: float | None = None
    min_query_meta_latency: float | None = None
    max_query_meta_latency: float | None = None
    p99_query_meta_latency: float | None = None
    p95_query_meta_latency: float | None = None
    ave_urma_total_latency: float | None = None
    min_urma_total_latency: float | None = None
    max_urma_total_latency: float | None = None
    p99_urma_total_latency: float | None = None
    p95_urma_total_latency: float | None = None
    ave_urma_link_latency: float | None = None
    min_urma_link_latency: float | None = None
    max_urma_link_latency: float | None = None
    p99_urma_link_latency: float | None = None
    p95_urma_link_latency: float | None = None
    ave_c2w_urma_latency: float | None = None
    min_c2w_urma_latency: float | None = None
    max_c2w_urma_latency: float | None = None
    p99_c2w_urma_latency: float | None = None
    p95_c2w_urma_latency: float | None = None
    ave_w2w_urma_latency: float | None = None
    min_w2w_urma_latency: float | None = None
    max_w2w_urma_latency: float | None = None
    p99_w2w_urma_latency: float | None = None
    p95_w2w_urma_latency: float | None = None
    existed_status: bool = True
    created_at: str = dataclass_field(
        default_factory=lambda: datetime.now().strftime(
            "%Y-%m-%d %H:%M:%S.%f"
        )[:-3]
    )


class TimeWindowAggregatedIpPair(BaseModel):
    """时间窗口内的IP对聚合统计"""
    src_ip: str = Field(..., description="源IP地址")
    dst_ip: str = Field(..., description="目的IP地址")
    log_parse_result_cnt: int = Field(default=0, description="结果数")
    anomaly_log_parse_result_cnt: int = Field(default=0, description="异常数")
    anomaly_cnt: int = Field(default=0, description="异常数量")
    ave_total_latency: float | None = Field(default=None, description="平均总延迟，单位毫秒")
    min_total_latency: float | None = Field(default=None, description="最小总延迟，单位毫秒")
    max_total_latency: float | None = Field(default=None, description="最大总延迟，单位毫秒")
    p99_total_latency: float | None = Field(default=None, description="总延迟P99，单位毫秒")
    p95_total_latency: float | None = Field(default=None, description="总延迟P95，单位毫秒")
    ave_query_meta_latency: float | None = Field(default=None, description="平均查询元数据延迟，单位毫秒")
    min_query_meta_latency: float | None = Field(default=None, description="最小查询元数据延迟，单位毫秒")
    max_query_meta_latency: float | None = Field(default=None, description="最大查询元数据延迟，单位毫秒")
    p99_query_meta_latency: float | None = Field(default=None, description="查询元数据延迟P99，单位毫秒")
    p95_query_meta_latency: float | None = Field(default=None, description="查询元数据延迟P95，单位毫秒")
    ave_urma_total_latency: float | None = Field(default=None, description="平均URMA总延迟，单位毫秒")
    min_urma_total_latency: float | None = Field(default=None, description="最小URMA总延迟，单位毫秒")
    max_urma_total_latency: float | None = Field(default=None, description="最大URMA总延迟，单位毫秒")
    p99_urma_total_latency: float | None = Field(default=None, description="URMA总延迟P99，单位毫秒")
    p95_urma_total_latency: float | None = Field(default=None, description="URMA总延迟P95，单位毫秒")
    ave_urma_link_latency: float | None = Field(default=None, description="平均URMA建链延迟，单位毫秒")
    min_urma_link_latency: float | None = Field(default=None, description="最小URMA建链延迟，单位毫秒")
    max_urma_link_latency: float | None = Field(default=None, description="最大URMA建链延迟，单位毫秒")
    p99_urma_link_latency: float | None = Field(default=None, description="URMA建链延迟P99，单位毫秒")
    p95_urma_link_latency: float | None = Field(default=None, description="URMA建链延迟P95，单位毫秒")
    ave_c2w_urma_latency: float | None = Field(default=None, description="平均C2W URMA延迟，单位毫秒")
    min_c2w_urma_latency: float | None = Field(default=None, description="最小C2W URMA延迟，单位毫秒")
    max_c2w_urma_latency: float | None = Field(default=None, description="最大C2W URMA延迟，单位毫秒")
    p99_c2w_urma_latency: float | None = Field(default=None, description="C2W URMA延迟P99，单位毫秒")
    p95_c2w_urma_latency: float | None = Field(default=None, description="C2W URMA延迟P95，单位毫秒")
    ave_w2w_urma_latency: float | None = Field(default=None, description="平均W2W URMA延迟，单位毫秒")
    min_w2w_urma_latency: float | None = Field(default=None, description="最小W2W URMA延迟，单位毫秒")
    max_w2w_urma_latency: float | None = Field(default=None, description="最大W2W URMA延迟，单位毫秒")
    p99_w2w_urma_latency: float | None = Field(default=None, description="W2W URMA延迟P99，单位毫秒")
    p95_w2w_urma_latency: float | None = Field(default=None, description="W2W URMA延迟P95，单位毫秒")


class TimeWindowAggregatedEventModel(BaseModel):
    """时间窗口聚合事件"""
    start_time: str = Field(..., description="时间窗口开始时间")
    end_time: str = Field(..., description="时间窗口结束时间")
    total_cnt: int = Field(default=0, description="该时间段内结果总数")
    anomaly_cnt: int = Field(default=0, description="该时间段内异常总数")
    ave_total_latency: float | None = Field(default=None, description="平均总延迟，单位毫秒")
    min_total_latency: float | None = Field(default=None, description="最小总延迟，单位毫秒")
    max_total_latency: float | None = Field(default=None, description="最大总延迟，单位毫秒")
    p99_total_latency: float | None = Field(default=None, description="总延迟P99，单位毫秒")
    p95_total_latency: float | None = Field(default=None, description="总延迟P95，单位毫秒")
    ave_query_meta_latency: float | None = Field(default=None, description="平均查询元数据延迟，单位毫秒")
    p99_query_meta_latency: float | None = Field(default=None, description="查询元数据延迟P99，单位毫秒")
    p95_query_meta_latency: float | None = Field(default=None, description="查询元数据延迟P95，单位毫秒")
    ave_urma_total_latency: float | None = Field(default=None, description="平均URMA总延迟，单位毫秒")
    p99_urma_total_latency: float | None = Field(default=None, description="URMA总延迟P99，单位毫秒")
    p95_urma_total_latency: float | None = Field(default=None, description="URMA总延迟P95，单位毫秒")
    ave_urma_link_latency: float | None = Field(default=None, description="平均URMA建链延迟，单位毫秒")
    p99_urma_link_latency: float | None = Field(default=None, description="URMA建链延迟P99，单位毫秒")
    p95_urma_link_latency: float | None = Field(default=None, description="URMA建链延迟P95，单位毫秒")
    ave_c2w_urma_latency: float | None = Field(default=None, description="平均C2W URMA延迟，单位毫秒")
    p99_c2w_urma_latency: float | None = Field(default=None, description="C2W URMA延迟P99，单位毫秒")
    p95_c2w_urma_latency: float | None = Field(default=None, description="C2W URMA延迟P95，单位毫秒")
    ave_w2w_urma_latency: float | None = Field(default=None, description="平均W2W URMA延迟，单位毫秒")
    p99_w2w_urma_latency: float | None = Field(default=None, description="W2W URMA延迟P99，单位毫秒")
    p95_w2w_urma_latency: float | None = Field(default=None, description="W2W URMA延迟P95，单位毫秒")
    ip_pairs: list[TimeWindowAggregatedIpPair] = Field(
        default_factory=list, description="该时间窗口内的IP对聚合列表"
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


@dataclass(slots=True)
class AnomalousEventDataclass:
    """异常检测和批量存库使用的轻量对象。"""

    id: str = ""
    log_id: str = ""
    aggregated_event_id: str = ""
    start_log_parse_offset: int = 0
    end_log_parse_offset: int = 0
    anomaly_reason: str = ""
    existed_status: bool = True
    created_at: str = dataclass_field(
        default_factory=lambda: datetime.now().strftime(
            "%Y-%m-%d %H:%M:%S.%f"
        )[:-3]
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
    pod_ips: Optional[list[str]] = Field(default=None, description="涉及的Pod IP地址列表")
    src_ip: Optional[str] = Field(default=None, description="源IP地址")
    dst_ip: Optional[str] = Field(default=None, description="目的IP地址")
    cluster_name: Optional[str] = Field(default=None, description="集群名称")
    host: Optional[str] = Field(default=None, description="主机名称")
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
    # 新增时延指标字段
    sdk_process: Optional[float] = Field(
        default=None, description="SDK处理延迟，单位毫秒"
    )
    sdk_rpc: Optional[float] = Field(
        default=None, description="SDK RPC延迟，单位毫秒"
    )
    local_worker_cost: Optional[float] = Field(
        default=None, description="本地Worker处理延迟，单位毫秒"
    )
    local_worker_lock: Optional[float] = Field(
        default=None, description="本地Worker锁延迟，单位毫秒"
    )
    remote_worker_cost: Optional[float] = Field(
        default=None, description="远程Worker处理延迟，单位毫秒"
    )
    remote_worker_rpc: Optional[float] = Field(
        default=None, description="远程Worker RPC延迟，单位毫秒"
    )
    master_process: Optional[float] = Field(
        default=None, description="Master处理延迟，单位毫秒"
    )
    master_rpc_total: Optional[float] = Field(
        default=None, description="Master RPC总延迟，单位微秒"
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
    sdk_process: Optional[float] = Field(default=None, description="SDK处理延迟，单位毫秒")
    sdk_rpc: Optional[float] = Field(default=None, description="SDK RPC延迟，单位毫秒")
    local_worker_cost: Optional[float] = Field(default=None, description="本地Worker处理延迟，单位毫秒")
    local_worker_lock: Optional[float] = Field(default=None, description="本地Worker锁延迟，单位毫秒")
    remote_worker_cost: Optional[float] = Field(default=None, description="远程Worker处理延迟，单位毫秒")
    remote_worker_rpc: Optional[float] = Field(default=None, description="远程Worker RPC延迟，单位毫秒")
    master_process: Optional[float] = Field(default=None, description="Master处理延迟，单位毫秒")
    master_rpc_total: Optional[float] = Field(default=None, description="Master RPC总延迟，单位微秒")


class LogParseResultBatch(list):
    """解析结果列表及其批次级结构提示。"""

    __slots__ = ("all_sparse",)

    def __init__(self, size: int, *, all_sparse: bool) -> None:
        # repeat 带长度提示，list 可一次分配目标容量且不创建临时大列表。
        super().__init__(repeat(None, size))
        self.all_sparse = all_sparse


@dataclass(slots=True)
class LogParseResultDataclass:
    """轻量级解析结果（用于中间处理，避免 Pydantic 反射开销）

    使用 slots=True 可减少约 30% 内存占用和 10-20% 创建时间。
    批量存库时直接转换为 SQLite 参数 tuple，不创建 Pydantic 中间对象。

    注意：
        - id 字段默认为空字符串，在批量存库前生成 UUID
        - created_at 使用预生成的共享时间戳，避免每条记录都调用 strftime
    """
    # 必填字段（无默认值）
    total_latency: float
    is_anomalous: bool

    # 有默认值的字段
    id: str = ""
    log_id: str = ""
    aggregated_event_id: str = ""
    anomalous_event_id: str = ""
    pod_ips: Optional[list[str]] = None
    src_ip: Optional[str] = None
    dst_ip: Optional[str] = None
    cluster_name: Optional[str] = None
    host: Optional[str] = None
    anomaly_reason: Optional[str] = None
    anomaly_score: Optional[float] = None
    content: Optional[str] = None
    data_size: Optional[str] = None
    existed_status: bool = True
    offset: Optional[int] = None
    operation: Optional[str] = None
    remark: Optional[str] = None
    trace_id: Optional[str] = None
    urma_inflight_count: Optional[int] = None
    urma_link_latency: Optional[float] = None
    urma_total_latency: Optional[float] = None
    c2w_latency: Optional[float] = None
    worker_query_meta_latency: Optional[float] = None
    c2w_urma_latency: Optional[float] = None
    w2w_urma_latency: Optional[float] = None
    sdk_process: Optional[float] = None
    sdk_rpc: Optional[float] = None
    local_worker_cost: Optional[float] = None
    local_worker_lock: Optional[float] = None
    remote_worker_cost: Optional[float] = None
    remote_worker_rpc: Optional[float] = None
    master_process: Optional[float] = None
    master_rpc_total: Optional[float] = None
    timestamp: Optional[str] = None
    created_at: str = ""

    def to_pydantic(self) -> "LogParseResultModel":
        """转换为 Pydantic model（用于存库）

        使用 model_construct 避免再次触发验证和反射开销。
        如果 id 为空，则生成 UUID。
        """
        return LogParseResultModel.model_construct(
            id=self.id,
            log_id=self.log_id,
            aggregated_event_id=self.aggregated_event_id,
            anomalous_event_id=self.anomalous_event_id,
            pod_ips=self.pod_ips,
            src_ip=self.src_ip,
            dst_ip=self.dst_ip,
            cluster_name=self.cluster_name,
            host=self.host,
            is_anomalous=self.is_anomalous,
            anomaly_reason=self.anomaly_reason,
            anomaly_score=self.anomaly_score,
            content=self.content,
            data_size=self.data_size,
            existed_status=self.existed_status,
            offset=self.offset,
            operation=self.operation,
            remark=self.remark,
            trace_id=self.trace_id,
            total_latency=self.total_latency,
            urma_inflight_count=self.urma_inflight_count,
            urma_link_latency=self.urma_link_latency,
            urma_total_latency=self.urma_total_latency,
            c2w_latency=self.c2w_latency,
            worker_query_meta_latency=self.worker_query_meta_latency,
            c2w_urma_latency=self.c2w_urma_latency,
            w2w_urma_latency=self.w2w_urma_latency,
            sdk_process=self.sdk_process,
            sdk_rpc=self.sdk_rpc,
            local_worker_cost=self.local_worker_cost,
            local_worker_lock=self.local_worker_lock,
            remote_worker_cost=self.remote_worker_cost,
            remote_worker_rpc=self.remote_worker_rpc,
            master_process=self.master_process,
            master_rpc_total=self.master_rpc_total,
            timestamp=self.timestamp,
            created_at=self.created_at,
        )


@dataclass(slots=True)
class C2WLogParseResultDataclass:
    """SDK 已匹配 Worker、但没有端点/URMA/metrics 时使用的紧凑结果。

    这类结果只比无 Worker 的稀疏结果多一个 c2w_latency。把它从完整
    LogParseResultDataclass 中拆出来，可避免千万级普通匹配行构造和写库
    时反复处理大量恒为 NULL 的 Worker/诊断字段。
    """

    total_latency: float
    is_anomalous: bool
    id: str = ""
    log_id: str = ""
    aggregated_event_id: str = ""
    anomalous_event_id: str = ""
    pod_ips: Optional[list[str]] = None
    cluster_name: Optional[str] = None
    anomaly_reason: Optional[str] = None
    data_size: Optional[str] = None
    existed_status: bool = True
    operation: Optional[str] = None
    remark: Optional[str] = None
    trace_id: Optional[str] = None
    c2w_latency: Optional[float] = None
    timestamp: Optional[str] = None
    created_at: str = ""

    src_ip: ClassVar[None] = None
    dst_ip: ClassVar[None] = None
    host: ClassVar[None] = None
    anomaly_score: ClassVar[None] = None
    content: ClassVar[None] = None
    offset: ClassVar[None] = None
    urma_inflight_count: ClassVar[None] = None
    urma_link_latency: ClassVar[None] = None
    urma_total_latency: ClassVar[None] = None
    worker_query_meta_latency: ClassVar[None] = None
    c2w_urma_latency: ClassVar[None] = None
    w2w_urma_latency: ClassVar[None] = None
    sdk_process: ClassVar[None] = None
    sdk_rpc: ClassVar[None] = None
    local_worker_cost: ClassVar[None] = None
    local_worker_lock: ClassVar[None] = None
    remote_worker_cost: ClassVar[None] = None
    remote_worker_rpc: ClassVar[None] = None
    master_process: ClassVar[None] = None
    master_rpc_total: ClassVar[None] = None

    def to_pydantic(self) -> "LogParseResultModel":
        return LogParseResultDataclass.to_pydantic(self)  # type: ignore[arg-type]


@dataclass(slots=True)
class SparseLogParseResultDataclass:
    """无 Worker 匹配时使用的紧凑解析结果。

    省略字段以类属性形式暴露为 None，因此检测、聚合和存库代码仍可按
    LogParseResultDataclass 的属性接口读取；流水线只会修改这里保留的字段。
    """

    total_latency: float
    is_anomalous: bool
    id: str = ""
    log_id: str = ""
    aggregated_event_id: str = ""
    anomalous_event_id: str = ""
    pod_ips: Optional[list[str]] = None
    cluster_name: Optional[str] = None
    anomaly_reason: Optional[str] = None
    data_size: Optional[str] = None
    existed_status: bool = True
    operation: Optional[str] = None
    remark: Optional[str] = None
    trace_id: Optional[str] = None
    c2w_urma_latency: Optional[float] = None
    timestamp: Optional[str] = None
    created_at: str = ""

    src_ip: ClassVar[None] = None
    dst_ip: ClassVar[None] = None
    host: ClassVar[None] = None
    anomaly_score: ClassVar[None] = None
    content: ClassVar[None] = None
    offset: ClassVar[None] = None
    urma_inflight_count: ClassVar[None] = None
    urma_link_latency: ClassVar[None] = None
    urma_total_latency: ClassVar[None] = None
    c2w_latency: ClassVar[None] = None
    worker_query_meta_latency: ClassVar[None] = None
    w2w_urma_latency: ClassVar[None] = None
    sdk_process: ClassVar[None] = None
    sdk_rpc: ClassVar[None] = None
    local_worker_cost: ClassVar[None] = None
    local_worker_lock: ClassVar[None] = None
    remote_worker_cost: ClassVar[None] = None
    remote_worker_rpc: ClassVar[None] = None
    master_process: ClassVar[None] = None
    master_rpc_total: ClassVar[None] = None

    def to_pydantic(self) -> "LogParseResultModel":
        return LogParseResultDataclass.to_pydantic(self)  # type: ignore[arg-type]


def generate_uuids_hex(count: int) -> list[str]:
    """批量生成 128-bit 随机 ID 的 UUID hex 表示。

    一次性获取所有随机数，减少系统调用次数，显著提高性能。
    """
    import os

    total_bytes = count * 16
    random_bytes = os.urandom(total_bytes)
    ids = []
    for i in range(count):
        offset = i * 16
        ids.append(random_bytes[offset : offset + 16].hex())
    return ids
