"""Link日志解析器"""

from latency.common.ds_log_io import parse_timestamp
from latency.regex.kvcache_log import URMA_LINK_RE
from latency.schemas.ds_log import LogEntry, EntryType
from latency.task.parse.base_parser import LogParser


class LinkLogParser(LogParser):
    """Link日志解析器"""

    @property
    def patterns(self) -> list[str]:
        from latency.task.parse.base_parser import get_ds_log_config
        return get_ds_log_config().link_log_patterns

    label = "Worker link parse"
    _handle_errors = True

    def match_line(self, line: str, pod_ip: str) -> LogEntry | None:
        """匹配Link日志行"""
        if "elapsed ms:" not in line:
            return None
        if ("WorkerWorkerExchangeUrmaConnectInfo finish" not in line
                and "Worker-worker transport connection exchange success" not in line):
            return None
        if "WorkerWorkerExchangeUrmaConnectInfo finish" in line and "status=code: [OK]" not in line:
            return None
        m = URMA_LINK_RE.search(line)
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
            entry_type=EntryType.LINK,
        )
