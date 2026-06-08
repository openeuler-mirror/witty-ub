"""QueryMeta日志解析器"""

from latency.common.ds_log_io import parse_timestamp
from latency.regex.kvcache_log import QUERY_META_RE
from latency.regex.kvcache_log_file import QUERY_META_LOG_PATTERNS
from latency.schemas.ds_log import LogEntry, EntryType
from latency.parse.base_parser import LogParser


class QueryMetaLogParser(LogParser):
    """QueryMeta日志解析器"""

    @property
    def patterns(self) -> list[str]:
        return QUERY_META_LOG_PATTERNS

    label = "Worker query meta parse"
    _handle_errors = True

    def match_line(self, line: str, pod_ip: str) -> LogEntry | None:
        """匹配QueryMeta日志行"""
        if "Master query done" not in line:
            return None
        m = QUERY_META_RE.search(line)
        if not m:
            return None
        ts_str, elapsed_ms = m.groups()
        trace_id = self.extract_trace_id(line)
        if not trace_id:
            return None
        return LogEntry(
            timestamp=parse_timestamp(ts_str),
            elapsed_us=float(elapsed_ms) * 1000,
            pod_ip=pod_ip,
            trace_id=trace_id,
            entry_type=EntryType.QUERY_META,
        )
