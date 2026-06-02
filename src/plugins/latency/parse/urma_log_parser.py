"""URMA日志解析器"""
from typing import Optional

from latency.common.ds_log_io import parse_timestamp
from latency.regex.kvcache_log import URMA_RE
from latency.regex.kvcache_log_file import URMA_LOG_PATTERNS
from latency.schemas.ds_log import LogEntry, EntryType
from latency.schemas.request import ParseConfig
from latency.parse.base_parser import LogParser


class UrmaLogParser(LogParser):
    """URMA日志解析器"""

    @property
    def patterns(self) -> list[str]:
        return URMA_LOG_PATTERNS

    label = "Worker urma parse"
    _handle_errors = True

    def __init__(self, parse_config: Optional[ParseConfig] = None):
        super().__init__(parse_config)

    def match_line(self, line: str, pod_ip: str) -> LogEntry | None:
        """匹配URMA日志行"""
        if "URMA_ELAPSED_TOTAL" not in line:
            return None
        
        parsed = self.parse_run_line(line)
        if not parsed:
            return None
        
        if not self._filter_by_time(parsed["timestamp"]):
            return None
        
        msg = parsed["msg"]
        m = URMA_RE.search(msg)
        if not m:
            return None
        
        elapsed_ms, src, dst, inflight = m.groups()
        return LogEntry(
            timestamp=parse_timestamp(parsed["timestamp"]),
            elapsed_us=float(elapsed_ms) * 1000,
            src_addr=src.strip(),
            dst_addr=dst.strip(),
            inflight_count=int(inflight),
            pod_ip=pod_ip,
            trace_id=parsed["trace_id"],
            entry_type=EntryType.URMA,
        )
