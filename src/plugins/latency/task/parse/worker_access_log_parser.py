"""Worker访问日志解析器"""

from latency.common.ds_log_io import parse_timestamp
from latency.regex.kvcache_log_file import WORKER_ACCESS_LOG_PATTERNS
from latency.schemas.ds_log import LogEntry, EntryType
from latency.task.parse.base_parser import AccessLogParser, WORKER_GET_OPS, logger


class WorkerAccessLogParser(AccessLogParser):
    """Worker访问日志解析器"""

    @property
    def patterns(self) -> list[str]:
        return WORKER_ACCESS_LOG_PATTERNS

    label = "Worker access parse"

    def __init__(self, start_time=None, end_time=None):
        self.start_time = start_time
        self.end_time = end_time
        self._filtered_by_time = 0

    def match_line(self, line: str, pod_ip: str) -> LogEntry | None:
        """匹配Worker GET操作日志行"""
        parsed = self.parse_access_line(line)
        if not parsed or parsed["handle"] not in WORKER_GET_OPS:
            return None
        if self.start_time or self.end_time:
            ts = parse_timestamp(parsed["timestamp"])
            if (self.start_time and ts < self.start_time) or (self.end_time and ts > self.end_time):
                self._filtered_by_time += 1
                return None
        try:
            elapsed = int(parsed["elapsed"])
        except ValueError:
            return None
        trace_id = parsed["trace_id"]
        if not trace_id:
            return None
        return LogEntry(
            timestamp=parse_timestamp(parsed["timestamp"]),
            elapsed_us=elapsed,
            object_key=self.extract_object_key(parsed["req_msg"]),
            trace_id=trace_id,
            pod_ip=pod_ip,
            status_code=self.parse_status_code(parsed["status_code"]),
            resp_msg=parsed["resp_msg"],
            entry_type=EntryType.WORKER_GET,
        )

    def parse(self, input_dir: str) -> list[LogEntry]:
        """解析Worker访问日志"""
        self._filtered_by_time = 0
        entries = super().parse(input_dir)
        if self._filtered_by_time > 0:
            logger.info(f"[{self.label}] Filtered out {self._filtered_by_time} entries by time")
        return entries
