"""URMA日志解析器"""

from latency.common.ds_log_io import parse_timestamp
from latency.regex.kvcache_log import URMA_RE
from latency.regex.kvcache_log_file import URMA_LOG_PATTERNS
from latency.schemas.ds_log import LogEntry, EntryType
from latency.task.parse.base_parser import LogParser


class UrmaLogParser(LogParser):
    """URMA日志解析器"""

    @property
    def patterns(self) -> list[str]:
        return URMA_LOG_PATTERNS

    label = "Worker urma parse"
    _handle_errors = True

    def match_line(self, line: str, pod_ip: str) -> LogEntry | None:
        """匹配URMA日志行"""
        if "URMA_ELAPSED_TOTAL" not in line:
            return None
        m = URMA_RE.search(line)
        if not m:
            return None
        ts_str, elapsed_ms, src, dst, inflight = m.groups()
        return LogEntry(
            timestamp=parse_timestamp(ts_str),
            elapsed_us=float(elapsed_ms) * 1000,
            src_addr=src.strip(),
            dst_addr=dst.strip(),
            inflight_count=int(inflight),
            pod_ip=pod_ip,
            trace_id=self.extract_trace_id(line),
            entry_type=EntryType.URMA,
        )
