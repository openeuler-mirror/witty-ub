"""Link日志解析器"""
from typing import Optional

from latency.common.ds_log_io import parse_timestamp
from latency.regex.kvcache_log import URMA_LINK_RE
from latency.regex.kvcache_log_file import LINK_LOG_PATTERNS
from latency.schemas.ds_log import LogEntry, EntryType
from latency.schemas.request import ParseConfig
from latency.parse.base_parser import LogParser


class LinkLogParser(LogParser):
    """Link日志解析器"""

    @property
    def patterns(self) -> list[str]:
        return LINK_LOG_PATTERNS

    label = "Worker link parse"
    _handle_errors = True

    def __init__(self, parse_config: Optional[ParseConfig] = None):
        super().__init__(parse_config)

    def match_line(self, line: str, pod_ip: str) -> LogEntry | None:
        """匹配Link日志行"""
        if "elapsed ms:" not in line:
            return None
        if ("WorkerWorkerExchangeUrmaConnectInfo finish" not in line
                and "Worker-worker transport connection exchange success" not in line):
            return None
        
        parsed = self.parse_run_line(line)
        if not parsed:
            return None
        
        if not self._filter_by_time(parsed["timestamp"]):
            return None
        
        msg = parsed["msg"]
        trace_id = parsed["trace_id"]
        
        if "WorkerWorkerExchangeUrmaConnectInfo finish" in msg and "status=code: [OK]" not in msg:
            return None
        
        m = URMA_LINK_RE.search(msg)
        if not m:
            return None
        
        elapsed_ms = m.group(1)
        return LogEntry(
            timestamp=parse_timestamp(parsed["timestamp"]),
            elapsed_us=float(elapsed_ms) * 1000,
            pod_ip=pod_ip,
            trace_id=trace_id,
            entry_type=EntryType.LINK,
        )
