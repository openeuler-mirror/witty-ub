"""RemotePull日志解析器"""

from latency.common.ds_log_io import parse_timestamp
from latency.regex.kvcache_log import REMOTE_GET_RE, REMOTE_PULL_RE
from latency.schemas.ds_log import LogEntry, EntryType
from latency.task.parse.base_parser import LogParser


class RemotePullLogParser(LogParser):
    """RemotePull日志解析器"""

    @property
    def patterns(self) -> list[str]:
        from latency.task.parse.base_parser import get_ds_log_config
        return get_ds_log_config().remote_pull_log_patterns

    label = "Worker remote pull parse"
    _handle_errors = True

    def match_line(self, line: str, pod_ip: str) -> LogEntry | None:
        """匹配RemotePull日志行"""
        if "Remote get request" in line:
            m = REMOTE_GET_RE.search(line)
            if not m:
                return None
            ts_str, src_addr, dst_addr = m.groups()
            trace_id = self.extract_trace_id(line)
            if not trace_id:
                return None
            return LogEntry(
                timestamp=parse_timestamp(ts_str),
                elapsed_us=0,
                object_key="",
                request_size="",
                src_addr=src_addr.strip(),
                dst_addr=dst_addr.strip(),
                pod_ip=pod_ip,
                trace_id=trace_id,
                entry_type=EntryType.REMOTE_PULL,
            )
        if "Processing pull object[" in line:
            m = REMOTE_PULL_RE.search(line)
            if not m:
                return None
            ts_str, src_addr, dst_addr = m.groups()
            return LogEntry(
                timestamp=parse_timestamp(ts_str),
                elapsed_us=0,
                object_key="",
                request_size="",
                src_addr=src_addr.strip(),
                dst_addr=dst_addr.strip(),
                pod_ip=pod_ip,
                trace_id=self.extract_trace_id(line),
                entry_type=EntryType.REMOTE_PULL,
            )
        return None
