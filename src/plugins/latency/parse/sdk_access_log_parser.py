"""SDK访问日志解析器"""
import os
from datetime import datetime
from typing import Optional

from latency.common.ds_log_io import parse_timestamp
from latency.regex.kvcache_log_file import SDK_ACCESS_LOG_PATTERNS
from latency.schemas.ds_log import LogEntry, EntryType
from latency.schemas.request import ParseConfig
from latency.parse.base_parser import AccessLogParser, SDK_GET_OPS, logger


class SdkAccessLogParser(AccessLogParser):
    """SDK访问日志解析器"""

    @property
    def patterns(self) -> list[str]:
        return SDK_ACCESS_LOG_PATTERNS

    label = "SDK access parse"
    _keywords = ("DS_KV_CLIENT_GET", "DS_OBJECT_CLIENT_GET")

    def __init__(
        self,
        parse_config: Optional[ParseConfig] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        min_total_time_ms: Optional[float] = None,
    ):
        # Backward compatible: older callers passed start_time as the first arg.
        if isinstance(parse_config, ParseConfig):
            super().__init__(parse_config)
            self.start_time = self._start_dt
            self.end_time = self._end_dt
            self.min_elapsed_us = (
                parse_config.min_elapsed_ms * 1000
                if parse_config.min_elapsed_ms is not None
                else None
            )
        else:
            super().__init__(None)
            if parse_config is not None:
                # Legacy positional form: SdkAccessLogParser(start_time, end_time, min_total_time_ms)
                self.start_time = parse_config
                self.end_time = start_time
                self.min_elapsed_us = end_time * 1000 if end_time else None
            else:
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
        parsed = getattr(self, '_pre_parsed', None) or self.parse_access_line(line)
        if not parsed or parsed["handle"] not in SDK_GET_OPS:
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
        ts = parse_timestamp(parsed["timestamp"])
        if self.start_time or self.end_time:
            if (self.start_time and ts < self.start_time) or (self.end_time and ts > self.end_time):
                self._filtered_by_time += 1
                return None
        # 优先使用日志行中的pod_name，为空时回退到路径提取的pod_ip
        entry_pod_ip = parsed["pod_name"] if parsed["pod_name"] else pod_ip
        return LogEntry(
            timestamp=ts,
            operation=parsed["handle"],
            elapsed_us=elapsed,
            data_size=parsed["size"],
            object_key=self.extract_object_key(parsed["req_msg"]),
            trace_id=trace_id,
            pod_ip=entry_pod_ip,
            status_code=self.parse_status_code(parsed["status_code"]),
            resp_msg=parsed["resp_msg"],
            entry_type=EntryType.SDK_GET,
            cluster_name=parsed["cluster_name"] if parsed["cluster_name"] else None,
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
