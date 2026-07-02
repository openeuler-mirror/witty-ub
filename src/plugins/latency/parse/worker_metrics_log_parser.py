"""Worker指标日志解析器 - 解析8个新增的时延指标"""
import logging
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
from latency.schemas.ds_log import LogEntry
from latency.ENUM.ds_log import EntryType
from latency.schemas.request import ParseConfig
from latency.parse.base_parser import LogParser

logger = logging.getLogger(__name__)


class WorkerMetricsLogParser(LogParser):
    """Worker指标日志解析器 - 解析SDK处理、RPC、本地Worker、远程Worker、Master等时延指标"""

    @property
    def patterns(self) -> list[str]:
        return getattr(self, "_runtime_patterns", URMA_LOG_PATTERNS)

    label = "Worker metrics parse"
    _handle_errors = True
    _keywords = (
        "totalCost:", "Worker to master rpc QueryMeta:",
        "ProcessGetObjectRequest:", "worker SafeObject WLock:",
        "[Get] Done", "[Get/RemotePull] finish",
        "[Get] Remote done", "QueryMeta done",
        "[ZMQ_RPC_FRAMEWORK_SLOW]",
    )

    def __init__(self, parse_config: Optional[ParseConfig] = None):
        super().__init__(parse_config)

    def _match_and_extract(self, line: str) -> Tuple[EntryType, float] | None:
        """匹配日志行并提取时延值，返回(entry_type, elapsed_us) - 兼容旧接口"""
        results = self._extract_all_metrics(line)
        return results[0] if results else None
    
    def _extract_all_metrics(self, line: str) -> list[Tuple[EntryType, float]]:
        """提取日志行中的所有指标，返回列表[(entry_type, elapsed_us), ...]"""
        results = []
        
        # 1. sdk_process - 关键字: totalCost: Xms
        if "totalCost:" in line:
            m = SDK_PROCESS_RE.search(line)
            if m:
                results.append((EntryType.SDK_PROCESS, float(m.group(1)) * 1000))
        
        # 2. sdk_rpc - 关键字: Worker to master rpc QueryMeta: Xms
        if "Worker to master rpc QueryMeta:" in line:
            m = SDK_RPC_RE.search(line)
            if m:
                results.append((EntryType.SDK_RPC, float(m.group(1)) * 1000))
        
        # 3. local_worker_cost - 关键字: ProcessGetObjectRequest: Xms
        if "ProcessGetObjectRequest:" in line:
            m = LOCAL_WORKER_COST_RE.search(line)
            if m:
                results.append((EntryType.LOCAL_WORKER_COST, float(m.group(1)) * 1000))
        
        # 4. local_worker_lock - 关键字: worker SafeObject WLock: Xms
        if "worker SafeObject WLock:" in line:
            m = LOCAL_WORKER_LOCK_RE.search(line)
            if m:
                results.append((EntryType.LOCAL_WORKER_LOCK, float(m.group(1)) * 1000))
        
        # 5. remote_worker_cost - 关键字: [Get/RemotePull] finish ... cost: Xms
        if "[Get/RemotePull] finish" in line:
            m = REMOTE_WORKER_COST_RE.search(line)
            if m:
                results.append((EntryType.REMOTE_WORKER_COST, float(m.group(1)) * 1000))
        
        # 6. remote_worker_rpc - 关键字: [Get] Remote done ... cost: Xms
        if "[Get] Remote done" in line:
            m = REMOTE_WORKER_RPC_RE.search(line)
            if m:
                results.append((EntryType.REMOTE_WORKER_RPC, float(m.group(1)) * 1000))
        
        # 7. master_process - 关键字: QueryMeta done ... cost: Xms
        if "QueryMeta done" in line:
            m = MASTER_PROCESS_RE.search(line)
            if m:
                results.append((EntryType.MASTER_PROCESS, float(m.group(1)) * 1000))
        
        # 8. master_rpc - 关键字: [ZMQ_RPC_FRAMEWORK_SLOW] ... remote_processing_us=X
        if "[ZMQ_RPC_FRAMEWORK_SLOW]" in line:
            m = MASTER_RPC_RE.search(line)
            if m:
                results.append((EntryType.MASTER_RPC, float(m.group(1))))  # 已经是us
        
        return results

    def match_line(self, line: str, pod_ip: str) -> list[LogEntry] | None:
        """匹配Worker指标日志行，返回所有提取到的指标列表"""
        results = self._extract_all_metrics(line)
        if not results:
            return None
        
        # 优先使用预解析的数据（多解析器模式）
        parsed = getattr(self, '_pre_parsed', None)
        if parsed is None:
            # 单解析器模式下尝试解析
            parsed = self.parse_run_line(line)
        
        # 如果无法解析标准格式，使用默认值
        if not parsed:
            import time
            ts = time.time()
            trace_id = ""
            entry_pod_ip = pod_ip
            cluster_name = None
        else:
            ts = parse_timestamp(parsed["timestamp"])
            if not self._filter_by_time(ts):
                return None
            trace_id = parsed["trace_id"]
            entry_pod_ip = parsed["pod_name"] if parsed["pod_name"] else pod_ip
            cluster_name = parsed["cluster_name"] if parsed["cluster_name"] else None
        
        # 如果没有trace_id，尝试从日志行中提取
        if not trace_id:
            trace_id = self._extract_trace_id(line)
        
        # 如果仍然没有trace_id，跳过这条日志
        if not trace_id:
            logger.debug(f"No trace_id found in line: {line[:100]}")
            return None
        
        # 为每个指标创建一个LogEntry
        entries = []
        for entry_type, elapsed_us in results:
            entries.append(LogEntry(
                timestamp=ts,
                elapsed_us=elapsed_us,
                pod_ip=entry_pod_ip,
                trace_id=trace_id,
                entry_type=entry_type,
                cluster_name=cluster_name,
            ))
        
        return entries
    
    def _extract_trace_id(self, line: str) -> str:
        """从日志行中提取trace_id"""
        import re
        uuid_pattern = r'[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}'
        match = re.search(uuid_pattern, line, re.IGNORECASE)
        if match:
            return match.group(0)
        return ""
