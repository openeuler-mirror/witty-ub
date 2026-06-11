"""Worker指标日志解析器 - 解析8个新增的时延指标"""
from typing import Optional, Tuple

from latency.common.ds_log_io import parse_timestamp
from latency.regex.kvcache_log import (
    SDK_PROCESS_RE,
    SDK_RPC_RE,
    LOCAL_WORKER_COST_RE,
    LOCAL_WORKER_LOCK_RE,
    REMOTE_WORKER_COST_RE,
    REMOTE_WORKER_RPC_RE,
    MASTER_PROCESS_RE,
    MASTER_RPC_RE,
)
from latency.regex.kvcache_log_file import URMA_LOG_PATTERNS  # 复用worker日志模式
from latency.schemas.ds_log import LogEntry, EntryType
from latency.schemas.request import ParseConfig
from latency.parse.base_parser import LogParser


class WorkerMetricsLogParser(LogParser):
    """Worker指标日志解析器 - 解析SDK处理、RPC、本地Worker、远程Worker、Master等时延指标"""

    @property
    def patterns(self) -> list[str]:
        return URMA_LOG_PATTERNS  # 使用worker日志文件模式

    label = "Worker metrics parse"
    _handle_errors = True
    _keywords = (
        "totalCost:", "Worker to master rpc QueryMeta:",
        "ProcessGetObjectRequest:", "worker SafeObject WLock:",
        "[Get] finish", "[RemotePull] finish",
        "[Get] Remote done", "QueryMeta done",
        "[ZMQ_RPC_FRAMEWORK_SLOW]",
    )

    def __init__(self, parse_config: Optional[ParseConfig] = None):
        super().__init__(parse_config)

    def _match_and_extract(self, line: str) -> Tuple[EntryType, float] | None:
        """匹配日志行并提取时延值，返回(entry_type, elapsed_us)"""
        
        # 1. sdk_process - 关键字: totalCost: Xms
        if "totalCost:" in line:
            m = SDK_PROCESS_RE.search(line)
            if m:
                return EntryType.SDK_PROCESS, float(m.group(1)) * 1000
        
        # 2. sdk_rpc - 关键字: Worker to master rpc QueryMeta: Xms
        if "Worker to master rpc QueryMeta:" in line:
            m = SDK_RPC_RE.search(line)
            if m:
                return EntryType.SDK_RPC, float(m.group(1)) * 1000
        
        # 3. local_worker_cost - 关键字: ProcessGetObjectRequest: Xms
        if "ProcessGetObjectRequest:" in line:
            m = LOCAL_WORKER_COST_RE.search(line)
            if m:
                return EntryType.LOCAL_WORKER_COST, float(m.group(1)) * 1000
        
        # 4. local_worker_lock - 关键字: worker SafeObject WLock: Xms
        if "worker SafeObject WLock:" in line:
            m = LOCAL_WORKER_LOCK_RE.search(line)
            if m:
                return EntryType.LOCAL_WORKER_LOCK, float(m.group(1)) * 1000
        
        # 5. remote_worker_cost - 关键字: [Get/RemotePull] finish ... cost: Xms
        if "[Get] finish" in line or "[RemotePull] finish" in line:
            m = REMOTE_WORKER_COST_RE.search(line)
            if m:
                return EntryType.REMOTE_WORKER_COST, float(m.group(1)) * 1000
        
        # 6. remote_worker_rpc - 关键字: [Get] Remote done ... cost: Xms
        if "[Get] Remote done" in line:
            m = REMOTE_WORKER_RPC_RE.search(line)
            if m:
                return EntryType.REMOTE_WORKER_RPC, float(m.group(1)) * 1000
        
        # 7. master_process - 关键字: QueryMeta done ... cost: Xms
        if "QueryMeta done" in line:
            m = MASTER_PROCESS_RE.search(line)
            if m:
                return EntryType.MASTER_PROCESS, float(m.group(1)) * 1000
        
        # 8. master_rpc - 关键字: [ZMQ_RPC_FRAMEWORK_SLOW] ... remote_processing_us=X
        if "[ZMQ_RPC_FRAMEWORK_SLOW]" in line:
            m = MASTER_RPC_RE.search(line)
            if m:
                return EntryType.MASTER_RPC, float(m.group(1))  # 已经是us
        
        return None

    def match_line(self, line: str, pod_ip: str) -> LogEntry | None:
        """匹配Worker指标日志行"""
        result = self._match_and_extract(line)
        if not result:
            return None
        
        entry_type, elapsed_us = result
        
        parsed = getattr(self, '_pre_parsed', None) or self.parse_run_line(line)
        if not parsed:
            return None
        
        ts = parse_timestamp(parsed["timestamp"])
        if not self._filter_by_time(ts):
            return None
        
        trace_id = parsed["trace_id"]
        if not trace_id:
            return None
        
        # 优先使用日志行中的pod_name，为空时回退到路径提取的pod_ip
        entry_pod_ip = parsed["pod_name"] if parsed["pod_name"] else pod_ip
        
        return LogEntry(
            timestamp=ts,
            elapsed_us=elapsed_us,
            pod_ip=entry_pod_ip,
            trace_id=trace_id,
            entry_type=entry_type,
            cluster_name=parsed["cluster_name"] if parsed["cluster_name"] else None,
        )