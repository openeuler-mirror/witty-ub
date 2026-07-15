"""QueryMeta日志解析器"""
from typing import Optional

from latency.common.ds_log_io import parse_timestamp
from latency.regex.kvcache_log import QUERY_META_RE
from latency.regex.kvcache_log_file import QUERY_META_LOG_PATTERNS
from latency.schemas.ds_log import LogEntry
from latency.ENUM.ds_log import EntryType
from latency.schemas.request import ParseConfig
from latency.parse.base_parser import LogParser


class QueryMetaLogParser(LogParser):
    """QueryMeta日志解析器"""

    @property
    def patterns(self) -> list[str]:
        return QUERY_META_LOG_PATTERNS

    label = "Worker query meta parse"
    _handle_errors = True
    _keywords = ("Master query done",)

    def __init__(self, parse_config: Optional[ParseConfig] = None):
        super().__init__(parse_config)

    def match_line(self, line: str, pod_ip: str) -> LogEntry | None:
        """匹配QueryMeta日志行"""
        if "Master query done" not in line:
            return None
        
        parsed = getattr(self, '_pre_parsed', None) or self.parse_run_line(line)
        if not parsed:
            return None
        
        ts = parse_timestamp(parsed["timestamp"])
        if not self._filter_by_time(ts):
            return None
        
        msg = parsed["msg"]
        trace_id = parsed["trace_id"]
        if not trace_id:
            return None
        
        m = QUERY_META_RE.search(msg)
        if not m:
            return None
        
        elapsed_ms = m.group(1)
        # 优先使用日志行中的pod_name，为空时回退到路径提取的pod_ip
        entry_pod_ip = parsed["pod_name"] if parsed["pod_name"] else pod_ip
        return LogEntry(
            timestamp=ts,
            elapsed_us=float(elapsed_ms) * 1000,
            pod_ip=entry_pod_ip,
            trace_id=trace_id,
            entry_type=EntryType.QUERY_META,
            cluster_name=parsed["cluster_name"] if parsed["cluster_name"] else None,
        )