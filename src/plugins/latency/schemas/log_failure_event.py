import uuid

from pydantic import BaseModel, Field
class LogFailureEventModel(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), description="日志ID")
    log_id: str = Field(..., description="知识库对应的日志文件目录ID")
    log_file: str = Field(..., description="日志文件")
    raw_text: str = Field(..., description="原始日志")
    host_name: str = Field(default="Unknown", description="主机名")
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

class TraceFailureEventModel(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), description="Trace数据ID")
    trace_id: str = Field(..., description="Trace ID")
    log_id: str = Field(..., description="日志路径ID")
    pod_names: list[str] = Field(..., description="容器名列表")
    host_names: list[str] = Field(..., description="主机名列表")
    cluster_names: list[str] = Field(..., description="集群列表")
    timestamp: str = Field(..., description="日志最早时间戳")
    status_code: str = Field(..., description="状态码")
    failure_mode: str = Field(..., description="故障模式")

class ErrCodeMetricItem(BaseModel):
    """延迟指标数据点（用于时间曲线）"""
    time: str = Field(..., description="时间戳")
    err_cnt: int = Field(..., description="故障码计数")