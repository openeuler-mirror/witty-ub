"""Worker接口日志解析器"""

from datetime import datetime
from typing import Optional

from latency.common.ds_log_io import parse_timestamp
from latency.regex.kvcache_log_file import WORKER_ACCESS_LOG_PATTERNS
from latency.schemas.ds_log import LogEntry
from latency.ENUM.ds_log import EntryType
from latency.schemas.request import ParseConfig
from latency.parse.base_parser import AccessLogParser, WORKER_GET_OPS, WORKER_SET_OPS, logger


class WorkerAccessLogParser(AccessLogParser):
    """Worker接口日志解析器"""

    @property
    def patterns(self) -> list[str]:
        return getattr(self, "_runtime_patterns", WORKER_ACCESS_LOG_PATTERNS)

    label = "Worker access parse"
    _keywords = ("DS_POSIX_GET", "DS_POSIX_CREATE", "DS_POSIX_PUBLISH")

    def __init__(
        self,
        parse_config: Optional[ParseConfig] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
    ):
        # Backward compatible: older callers passed start_time as the first arg.
        if isinstance(parse_config, ParseConfig):
            super().__init__(parse_config)
            self.start_time = self._start_dt
            self.end_time = self._end_dt
        else:
            super().__init__(None)
            if parse_config is not None:
                # Legacy positional form: WorkerAccessLogParser(start_time, end_time)
                self.start_time = parse_config
                self.end_time = start_time
            else:
                self.start_time = start_time
                self.end_time = end_time
        self._filtered_by_time = 0
        self._scan_scope_enabled = False
        self._target_trace_ids: set[str] = set()

    def set_scan_scope(self, scan_scope: Optional[dict]) -> None:
        """使用类级别缓存避免重复创建大集合"""
        if not scan_scope:
            self._scan_scope_enabled = False
            self._target_trace_ids = set()
            return
        
        self._scan_scope_enabled = bool(scan_scope.get("enabled"))
        
        # 直接使用传递过来的集合对象（已经是 set），避免重新创建
        trace_ids = scan_scope.get("trace_ids")
        if isinstance(trace_ids, set):
            self._target_trace_ids = trace_ids
        else:
            self._target_trace_ids = set(trace_ids or ())

    def match_line(self, line: str, pod_ip: str) -> LogEntry | None:
        """匹配Worker GET/SET操作日志行"""
        parsed = getattr(self, '_pre_parsed', None) or self.parse_access_line(line)
        if not parsed or (parsed["handle"] not in WORKER_GET_OPS and parsed["handle"] not in WORKER_SET_OPS):
            return None
        trace_id = self.resolve_trace_id(
            parsed["trace_id"],
            parsed["req_msg"],
            parsed["resp_msg"],
        )
        if not trace_id:
            return None
        if self._scan_scope_enabled and trace_id not in self._target_trace_ids:
            return None
        try:
            elapsed = int(parsed["elapsed"])
        except ValueError:
            return None
        ts = parse_timestamp(parsed["timestamp"])
        if self.start_time or self.end_time:
            if (self.start_time and ts < self.start_time) or (self.end_time and ts > self.end_time):
                self._filtered_by_time += 1
                return None
        # 优先使用日志行中的pod_name，为空时回退到路径提取的pod_ip
        entry_pod_ip = parsed["pod_name"] if parsed["pod_name"] else pod_ip
        # 根据操作类型设置 entry_type
        if parsed["handle"] == "DS_POSIX_CREATE":
            entry_type = EntryType.WORKER_CREATE
        elif parsed["handle"] == "DS_POSIX_PUBLISH":
            entry_type = EntryType.WORKER_PUBLISH
        else:
            entry_type = EntryType.WORKER_GET
        return LogEntry(
            timestamp=ts,
            operation=parsed["handle"],
            elapsed_us=elapsed,
            object_key=self.extract_object_key(parsed["req_msg"]),
            trace_id=trace_id,
            pod_ip=entry_pod_ip,
            status_code=self.parse_status_code(parsed["status_code"]),
            resp_msg=parsed["resp_msg"],
            entry_type=entry_type,
            cluster_name=parsed["cluster_name"] if parsed["cluster_name"] else None,
        )

    def parse(self, input_dir: str) -> list[LogEntry]:
        """解析Worker接口日志"""
        self._filtered_by_time = 0
        entries = super().parse(input_dir)
        if self._filtered_by_time > 0:
            logger.info(f"[{self.label}] Filtered out {self._filtered_by_time} entries by time")
        return entries
