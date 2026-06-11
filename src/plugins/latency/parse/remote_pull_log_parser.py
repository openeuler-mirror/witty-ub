"""RemotePull日志解析器"""
from typing import Optional

from latency.common.ds_log_io import parse_timestamp
from latency.regex.kvcache_log import REMOTE_GET_RE, REMOTE_PULL_RE
from latency.regex.kvcache_log_file import REMOTE_PULL_LOG_PATTERNS
from latency.schemas.ds_log import LogEntry, EntryType
from latency.schemas.request import ParseConfig
from latency.parse.base_parser import LogParser


class RemotePullLogParser(LogParser):
    """RemotePull日志解析器"""

    @property
    def patterns(self) -> list[str]:
        return REMOTE_PULL_LOG_PATTERNS

    label = "Worker remote pull parse"
    _handle_errors = True
    _keywords = ("Remote get request", "Processing pull object[")

    def __init__(self, parse_config: Optional[ParseConfig] = None):
        super().__init__(parse_config)

    def match_line(self, line: str, pod_ip: str) -> LogEntry | None:
        """匹配RemotePull日志行"""
        if "Remote get request" in line:
            parsed = getattr(self, '_pre_parsed', None) or self.parse_run_line(line)
            if not parsed:
                return None
            
            if not self._filter_by_time(parsed["timestamp"]):
                return None
            
            msg = parsed["msg"]
            trace_id = parsed["trace_id"]
            if not trace_id:
                return None
            
            m = REMOTE_GET_RE.search(msg)
            if not m:
                return None
            src_addr, dst_addr = m.groups()
            # 优先使用日志行中的pod_name，为空时回退到路径提取的pod_ip
            entry_pod_ip = parsed["pod_name"] if parsed["pod_name"] else pod_ip
            return LogEntry(
                timestamp=parse_timestamp(parsed["timestamp"]),
                elapsed_us=0,
                object_key="",
                request_size="",
                src_addr=src_addr.strip(),
                dst_addr=dst_addr.strip(),
                pod_ip=entry_pod_ip,
                trace_id=trace_id,
                entry_type=EntryType.REMOTE_PULL,
                cluster_name=parsed["cluster_name"] if parsed["cluster_name"] else None,
            )
        
        if "Processing pull object[" in line:
            parsed = getattr(self, '_pre_parsed', None) or self.parse_run_line(line)
            if not parsed:
                return None
            
            if not self._filter_by_time(parsed["timestamp"]):
                return None
            
            msg = parsed["msg"]
            trace_id = parsed["trace_id"]
            if not trace_id:
                return None
            
            m = REMOTE_PULL_RE.search(msg)
            if not m:
                return None
            src_addr, dst_addr = m.groups()
            # 优先使用日志行中的pod_name，为空时回退到路径提取的pod_ip
            entry_pod_ip = parsed["pod_name"] if parsed["pod_name"] else pod_ip
            return LogEntry(
                timestamp=parse_timestamp(parsed["timestamp"]),
                elapsed_us=0,
                object_key="",
                request_size="",
                src_addr=src_addr.strip(),
                dst_addr=dst_addr.strip(),
                pod_ip=entry_pod_ip,
                trace_id=trace_id,
                entry_type=EntryType.REMOTE_PULL,
                cluster_name=parsed["cluster_name"] if parsed["cluster_name"] else None,
            )
        
        return None