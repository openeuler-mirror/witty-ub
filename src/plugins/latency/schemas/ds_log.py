from pydantic import BaseModel, Field
from datetime import datetime
from enum import StrEnum


class EntryType(StrEnum):
    SDK_GET = "SDK_GET"
    WORKER_GET = "WORKER_GET"
    URMA = "URMA"
    REMOTE_PULL = "REMOTE_PULL"
    LINK = "LINK"
    QUERY_META = "QUERY_META"


class LogEntry(BaseModel):
    timestamp: datetime = Field(..., description="时间戳")
    trace_id: str = Field(..., description="追踪ID")
    pod_ip: str = Field(..., description="Pod IP地址")
    elapsed_us: float = Field(..., description="事件耗时，单位微秒")
    log_id: str | None = Field(default=None, description="来源日志文件ID")
    
    entry_type: EntryType = Field(..., description="条目类型")
    
    operation: str | None = Field(default=None, description="操作类型")
    data_size: str | None = Field(default=None, description="数据大小")
    object_key: str | None = Field(default=None, description="对象键")
    status_code: int | None = Field(default=None, description="状态码")
    resp_msg: str | None = Field(default=None, description="响应消息")
    src_addr: str | None = Field(default=None, description="源地址")
    dst_addr: str | None = Field(default=None, description="目的地址")
    inflight_count: int | None = Field(default=None, description="在途写请求数")
    request_size: str | None = Field(default=None, description="请求大小")


class CorrelationResult(BaseModel):
    sdk_worker_map: dict = Field(default_factory=dict, description="sdk_idx → LogEntry (WORKER_GET)")
    sdk_urma_map: dict = Field(default_factory=dict, description="sdk_idx → list[LogEntry] (URMA) (C→W)")
    worker_urma_map: dict = Field(default_factory=dict, description="w_idx → list[LogEntry] (URMA)")
    worker_worker_urma_map: dict = Field(default_factory=dict, description="w_idx → list[LogEntry] (URMA) (W→W)")
    worker_remote_pull_map: dict = Field(default_factory=dict, description="w_idx → list[LogEntry] (REMOTE_PULL)")
    worker_link_map: dict = Field(default_factory=dict, description="w_idx → elapsed_us")
    worker_query_meta_map: dict = Field(default_factory=dict, description="w_idx → elapsed_us")
    worker_idx_map: dict = Field(default_factory=dict, description="sdk_idx → w_idx")
    urma_empty_reasons: dict = Field(default_factory=dict, description="w_idx → reason str")
