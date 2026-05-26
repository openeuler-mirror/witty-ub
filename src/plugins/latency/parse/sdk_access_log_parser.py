"""SDK访问日志解析器"""
import os

from latency.common.ds_log_io import parse_timestamp
from latency.regex.kvcache_log_file import SDK_ACCESS_LOG_PATTERNS
from latency.schemas.ds_log import LogEntry, EntryType
from latency.parse.base_parser import AccessLogParser, SDK_GET_OPS, logger


class SdkAccessLogParser(AccessLogParser):
    """SDK访问日志解析器"""

    @property
    def patterns(self) -> list[str]:
        return SDK_ACCESS_LOG_PATTERNS

    label = "SDK access parse"

    def __init__(self, start_time=None, end_time=None, min_total_time_ms=None):
        self.start_time = start_time
        self.end_time = end_time
        self.min_elapsed_us = min_total_time_ms * 1000 if min_total_time_ms else None
        self._filtered_by_time = 0
        self._filtered_by_elapsed = 0

    def extract_pod_ip(self, path: str) -> str:
        """从SDK日志路径提取Pod IP"""
        return os.path.basename(os.path.dirname(path)).replace("SDK_", "")

    def match_line(self, line: str, pod_ip: str) -> LogEntry | None:
        """匹配SDK GET操作日志行"""
        parsed = self.parse_access_line(line)
        if not parsed or parsed["handle"] not in SDK_GET_OPS:
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
        if self.min_elapsed_us is not None and elapsed < self.min_elapsed_us:
            self._filtered_by_elapsed += 1
            return None
        trace_id = parsed["trace_id"]
        if not trace_id:
            return None
        return LogEntry(
            timestamp=parse_timestamp(parsed["timestamp"]),
            operation=parsed["handle"],
            elapsed_us=elapsed,
            data_size=parsed["size"],
            object_key=self.extract_object_key(parsed["req_msg"]),
            trace_id=trace_id,
            pod_ip=pod_ip,
            status_code=self.parse_status_code(parsed["status_code"]),
            resp_msg=parsed["resp_msg"],
            entry_type=EntryType.SDK_GET,
        )

    def parse(self, input_dir: str) -> list[LogEntry]:
        """解析SDK访问日志"""
        self._filtered_by_time = 0
        self._filtered_by_elapsed = 0
        entries = super().parse(input_dir)
        if self._filtered_by_time > 0:
            logger.info(f"[{self.label}] Filtered out {self._filtered_by_time} entries by time")
        if self._filtered_by_elapsed > 0:
            logger.info(f"[{self.label}] Filtered out {self._filtered_by_elapsed} entries by elapsed time")
        return entries
