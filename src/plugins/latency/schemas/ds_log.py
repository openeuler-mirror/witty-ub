from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field

from latency.ENUM.ds_log import EntryType, TupleField


@dataclass(slots=True)
class LogEntry:
    """日志解析条目（轻量级 dataclass，降低内存占用）"""
    timestamp: datetime
    trace_id: str
    pod_ip: str
    elapsed_us: float
    entry_type: EntryType
    log_id: Optional[str] = None
    operation: Optional[str] = None
    data_size: Optional[str] = None
    object_key: Optional[str] = None
    status_code: Optional[int] = None
    resp_msg: Optional[str] = None
    src_addr: Optional[str] = None
    dst_addr: Optional[str] = None
    inflight_count: Optional[int] = None
    request_size: Optional[str] = None
    cluster_name: Optional[str] = None

    def __reduce__(self):
        return (
            LogEntry,
            (
                self.timestamp, self.trace_id, self.pod_ip, self.elapsed_us,
                self.entry_type, self.log_id, self.operation, self.data_size,
                self.object_key, self.status_code, self.resp_msg,
                self.src_addr, self.dst_addr, self.inflight_count,
                self.request_size, self.cluster_name,
            ),
        )


class CorrelationResult(BaseModel):
    sdk_worker_map: dict = Field(default_factory=dict, description="sdk_idx → LogEntry (WORKER_GET)")
    sdk_urma_map: dict = Field(default_factory=dict, description="sdk_idx → list[LogEntry] (URMA) (C→W)")
    worker_urma_map: dict = Field(default_factory=dict, description="w_idx → list[LogEntry] (URMA)")
    worker_worker_urma_map: dict = Field(default_factory=dict, description="w_idx → list[LogEntry] (URMA) (W→W)")
    worker_remote_pull_map: dict = Field(default_factory=dict, description="w_idx → list[LogEntry] (REMOTE_PULL)")
    worker_link_map: dict = Field(default_factory=dict, description="w_idx → list[LogEntry] (LINK)")
    worker_query_meta_map: dict = Field(default_factory=dict, description="w_idx → list[LogEntry] (QUERY_META)")
    # 新增指标映射
    worker_sdk_process_map: dict = Field(default_factory=dict, description="w_idx → list[LogEntry] (SDK_PROCESS)")
    worker_sdk_rpc_map: dict = Field(default_factory=dict, description="w_idx → list[LogEntry] (SDK_RPC)")
    worker_local_worker_cost_map: dict = Field(default_factory=dict, description="w_idx → list[LogEntry] (LOCAL_WORKER_COST)")
    worker_local_worker_lock_map: dict = Field(default_factory=dict, description="w_idx → list[LogEntry] (LOCAL_WORKER_LOCK)")
    worker_remote_worker_cost_map: dict = Field(default_factory=dict, description="w_idx → list[LogEntry] (REMOTE_WORKER_COST)")
    worker_remote_worker_rpc_map: dict = Field(default_factory=dict, description="w_idx → list[LogEntry] (REMOTE_WORKER_RPC)")
    worker_master_process_map: dict = Field(default_factory=dict, description="w_idx → list[LogEntry] (MASTER_PROCESS)")
    worker_master_rpc_map: dict = Field(default_factory=dict, description="w_idx → list[LogEntry] (MASTER_RPC)")
    worker_idx_map: dict = Field(default_factory=dict, description="sdk_idx → w_idx")
    urma_empty_reasons: dict = Field(default_factory=dict, description="w_idx → reason str")