import uuid
from typing import Optional

from pydantic import BaseModel, Field
class LogFailureEventModel(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), description="日志ID")
    log_id: str = Field(..., description="知识库对应的日志文件目录ID")
    log_file: str = Field(..., description="日志文件")
    raw_text: str = Field(..., description="原始日志")
    host_name: Optional[str] = Field(default=None, description="主机名")
    timestamp: str = Field(..., description="日志时间戳")
    level: str = Field(..., description="日志级别")
    filename: str = Field(..., description="报错文件名")
    pod_name: str = Field(..., description="容器名")
    pid: str = Field(..., description="进程号")
    tid: str = Field(..., description="线程号")
    trace_id: str = Field(..., description="Trace ID")
    cluster_name: str = Field(..., description="集群名")
    message: str = Field(..., description="日志文件")
    status_code: str = Field(..., description="状态码")
    failure_mode: list[str] = Field(..., description="故障模式")

class PodRoleModel(BaseModel):
    """trace 级容器角色聚合：每行一个 trace，记录该 trace 内各角色的 pod.

    - client_pod：该 trace 的 client 容器（通常唯一）
    - entry_worker_pods / meta_worker_pods / data_worker_pods：对应角色的容器集合
    - set 请求不涉及远端拉取，data_worker_pods 通常为空数组
    """
    trace_id: str = Field(..., description="Trace ID")
    log_id: str = Field(..., description="日志路径ID")
    operation: str = Field(default="", description="操作类型：GET / SET")
    client_pod: Optional[str] = Field(default=None, description="client 容器")
    entry_worker_pods: list[str] = Field(default_factory=list, description="entry worker 容器列表")
    meta_worker_pods: list[str] = Field(default_factory=list, description="meta worker 容器列表")
    data_worker_pods: list[str] = Field(default_factory=list, description="data worker 容器列表")
    timestamp: str = Field(default="", description="日志最早时间戳")

class TraceFailureEventModel(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), description="Trace数据ID")
    trace_id: str = Field(..., description="Trace ID")
    log_id: str = Field(..., description="日志路径ID")
    pod_names: list[str] = Field(..., description="容器名列表")
    src_ip: str = Field(default="", description="起始容器")
    dst_ip: str = Field(default="", description="目标容器")
    host_names: list[str] = Field(..., description="主机名列表")
    cluster_names: list[str] = Field(..., description="集群列表")
    timestamp: str = Field(..., description="日志最早时间戳")
    status_code: list[str] = Field(default_factory=list, description="状态码列表")
    failure_mode: list[str] = Field(default_factory=list, description="trace涉及日志命中的故障模式列表")
    operation: str = Field(default="", description="操作类型：GET / SET")
    pod_role: Optional[PodRoleModel] = Field(default=None, description="trace 级容器角色聚合")

class ErrCodeMetricItem(BaseModel):
    """延迟指标数据点（用于时间曲线）"""
    time: str = Field(..., description="时间戳")
    err_cnt: int = Field(..., description="故障码计数")

class PodAggregatedFailureEventModel(BaseModel):
    pod_name: str = Field(..., description="容器名")
    status_code_cnt: dict = Field(..., description="故障码计数")

class SrcDstAggregatedFailureEventModel(BaseModel):
    src_ip: str = Field(..., description="源IP地址")
    dst_ip: str = Field(..., description="目标IP地址")
    status_code_cnt: dict = Field(..., description="故障码计数")

class TimeAggregatedFailureEventModel(BaseModel):
    start_time: str = Field(..., description="开始时间")
    end_time: str = Field(..., description="结束时间")
    status_code_cnt: dict = Field(..., description="故障码计数")
