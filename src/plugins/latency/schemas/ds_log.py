from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

from latency.ENUM.ds_log import EntryType, TupleField as TupleField


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


@dataclass(slots=True)
class CorrelationResult:
    """关联结果的轻量容器；所有索引均按引用传递，不做 Pydantic 复制。"""

    sdk_worker_map: dict = field(default_factory=dict)
    sdk_urma_map: dict = field(default_factory=dict)
    worker_urma_map: dict = field(default_factory=dict)
    worker_worker_urma_map: dict = field(default_factory=dict)
    worker_remote_pull_map: dict = field(default_factory=dict)
    worker_link_map: dict = field(default_factory=dict)
    worker_query_meta_map: dict = field(default_factory=dict)
    worker_sdk_process_map: dict = field(default_factory=dict)
    worker_sdk_rpc_map: dict = field(default_factory=dict)
    worker_local_worker_cost_map: dict = field(default_factory=dict)
    worker_local_worker_lock_map: dict = field(default_factory=dict)
    worker_remote_worker_cost_map: dict = field(default_factory=dict)
    worker_remote_worker_rpc_map: dict = field(default_factory=dict)
    worker_master_process_map: dict = field(default_factory=dict)
    worker_master_rpc_map: dict = field(default_factory=dict)
    worker_idx_map: dict = field(default_factory=dict)
    urma_empty_reasons: dict = field(default_factory=dict)
    # (pod_ip, trace_id) → list[URMA]。构建结果时直接查此索引，避免为
    # 每条 SDK 复制一份 sdk_idx → list 映射并额外遍历千万条 SDK。
    sdk_urma_index: dict = field(default_factory=dict)
    # worker_index -> set[pod_ip]。预构建的 worker 索引到所有关联 pod_ip 的映射，
    # 用于在构建结果时高效收集整条 trace 涉及的所有 pod_ip。
    worker_pod_ips_map: dict = field(default_factory=dict)
