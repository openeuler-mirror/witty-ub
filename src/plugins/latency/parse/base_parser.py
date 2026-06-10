"""日志解析器基类"""
import logging
import os
import re
from abc import ABC, abstractmethod
from datetime import datetime
from enum import IntEnum
from typing import Optional

from latency.ENUM.ds_log import OpType, StatusCode
from latency.common.ds_log_io import Progress, glob_paths, parse_timestamp, open_log
from latency.regex.kvcache_log import OBJECT_KEY_RE
from latency.schemas.ds_log import LogEntry
from latency.schemas.log import LogFileModel
from latency.schemas.request import ParseConfig


logger = logging.getLogger(__name__)

SDK_GET_OPS = frozenset({OpType.DS_KV_CLIENT_GET, OpType.DS_OBJECT_CLIENT_GET})
WORKER_GET_OPS = frozenset({OpType.DS_POSIX_GET})
ACCESS_LOG_MIN_PARTS = 13
RUN_LOG_MIN_PARTS = 8


class LogParser(ABC):
    """日志解析器基类"""
    label: str = ""
    _handle_errors: bool = False

    _UUID_RE = re.compile(
        r"\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b",
        re.IGNORECASE,
    )

    def __init__(self, parse_config: Optional[ParseConfig] = None):
        self.parse_config = parse_config or ParseConfig()
        self._filtered_by_time = 0
    
    def _filter_by_time(self, timestamp_str: str) -> bool:
        """
        根据配置过滤时间
        
        返回 True 表示需要保留（通过过滤），返回 False 表示需要过滤掉
        """
        if not self.parse_config.is_time_filter_enabled():
            return True
        
        try:
            ts = parse_timestamp(timestamp_str)
            if self.parse_config.start_time:
                start_ts = parse_timestamp(self.parse_config.start_time)
                if ts < start_ts:
                    self._filtered_by_time += 1
                    return False
            if self.parse_config.end_time:
                end_ts = parse_timestamp(self.parse_config.end_time)
                if ts > end_ts:
                    self._filtered_by_time += 1
                    return False
            return True
        except Exception:
            return True

    class AccessCol(IntEnum):
        """Access格式日志列索引
        
        格式: timestamp | level | filename:lineno | pod_name | pid:tid | trace_id | cluster_name | status_code | handle | elapsed | size | req_msg | resp_msg
        """
        TIMESTAMP = 0
        LEVEL = 1
        FILENAME = 2
        POD_NAME = 3
        PID_TID = 4
        TRACE_ID = 5
        CLUSTER_NAME = 6
        STATUS_CODE = 7
        HANDLE = 8
        ELAPSED = 9
        SIZE = 10
        REQ_MSG = 11
        RESP_MSG = 12

    class RunCol(IntEnum):
        """Run格式日志列索引
        
        格式: timestamp | level | filename:lineno | pod_name | pid:tid | trace_id | cluster_name | msg
        """
        TIMESTAMP = 0
        LEVEL = 1
        FILENAME = 2
        POD_NAME = 3
        PID_TID = 4
        TRACE_ID = 5
        CLUSTER_NAME = 6
        MSG = 7

    @property
    def patterns(self) -> list[str]:
        """获取日志文件模式，子类需要实现这个属性"""
        raise NotImplementedError

    def parse(self, input_dir: str) -> list[LogEntry]:
        """解析目录下的日志文件"""
        entries: list[LogEntry] = []
        paths = glob_paths([os.path.join(input_dir, "**", p) for p in self.patterns])
        progress = Progress(self.label, len(paths))
        for file_idx, path in enumerate(paths, 1):
            pod_ip = self.extract_pod_ip(path)
            log_file = LogFileModel(file_path=path, file_size=os.path.getsize(path))
            progress.update(file_idx, path, line=0, match=len(entries))
            if self._handle_errors:
                try:
                    self._scan_file(path, pod_ip, log_file.id, entries, progress, file_idx)
                except EOFError as e:
                    logger.warning(f"Skipping corrupted file {path}: {e}")
                except Exception as e:
                    logger.warning(f"Error reading {path}: {e}")
            else:
                self._scan_file(path, pod_ip, log_file.id, entries, progress, file_idx)
            progress.update(file_idx, path, match=len(entries))
        entries.sort(key=lambda x: x.timestamp)
        progress.done(match=len(entries))
        return entries

    def _scan_file(self, path, pod_ip, log_id, entries, progress, file_idx):
        """扫描单个日志文件"""
        with open_log(path) as f:
            for line_no, line in enumerate(f, 1):
                if line_no % 100_000 == 0:
                    progress.update(file_idx, path, line=line_no, match=len(entries))
                entry = self.match_line(line, pod_ip)
                if entry:
                    entry.log_id = log_id
                    entries.append(entry)

    def extract_pod_ip(self, path: str) -> str:
        """从路径中提取Pod IP"""
        _dir = os.path.basename(os.path.dirname(path))
        return _dir.removeprefix("Worker_").removeprefix("dsworker_").removesuffix("worker_")

    def extract_trace_id(self, line: str) -> str:
        """从行中提取trace_id"""
        match = self._UUID_RE.search(line)
        return match.group(0) if match else ""
    
    @staticmethod
    def split_by_delimiter(line: str) -> list[str]:
        if not line:
            return []
        return line.split("|")

    @staticmethod
    def parse_access_line(line: str) -> dict | None:
        if not line or line[0] != "2":
            return None

        parts = line.split("|")
        if len(parts) < ACCESS_LOG_MIN_PARTS:
            return None

        col = LogParser.AccessCol
        plen = len(parts)
        return {
            "timestamp": parts[col.TIMESTAMP].strip(),
            "pod_name": parts[col.POD_NAME].strip() if col.POD_NAME < plen else "",
            "trace_id": parts[col.TRACE_ID].strip() if col.TRACE_ID < plen else "",
            "cluster_name": parts[col.CLUSTER_NAME].strip() if col.CLUSTER_NAME < plen else "",
            "status_code": parts[col.STATUS_CODE].strip() if col.STATUS_CODE < plen else "",
            "handle": parts[col.HANDLE].strip() if col.HANDLE < plen else "",
            "elapsed": parts[col.ELAPSED].strip() if col.ELAPSED < plen else "",
            "size": parts[col.SIZE].strip() if col.SIZE < plen else "",
            "req_msg": parts[col.REQ_MSG].strip() if col.REQ_MSG < plen else "",
            "resp_msg": parts[col.RESP_MSG].strip() if col.RESP_MSG < plen else "",
        }

    @staticmethod
    def parse_run_line(line: str) -> dict | None:
        if not line or line[0] != "2":
            return None

        parts = line.split("|")
        if len(parts) < RUN_LOG_MIN_PARTS:
            return None

        col = LogParser.RunCol
        plen = len(parts)
        return {
            "timestamp": parts[col.TIMESTAMP].strip(),
            "pod_name": parts[col.POD_NAME].strip() if col.POD_NAME < plen else "",
            "trace_id": parts[col.TRACE_ID].strip() if col.TRACE_ID < plen else "",
            "cluster_name": parts[col.CLUSTER_NAME].strip() if col.CLUSTER_NAME < plen else "",
            "msg": parts[col.MSG].strip() if col.MSG < plen else "",
        }

    @abstractmethod
    def match_line(self, line: str, pod_ip: str) -> LogEntry | None:
        """匹配日志行，子类需要实现"""
        ...


class AccessLogParser(LogParser):
    """访问日志解析器基类，提供Access格式日志的便捷解析能力"""

    @staticmethod
    def parse_status_code(raw: str) -> int:
        """解析状态码"""
        if raw.isdigit():
            return int(raw)
        return StatusCode.OK

    @staticmethod
    def extract_object_key(req_msg: str) -> str:
        """从请求消息中提取对象键"""
        match = OBJECT_KEY_RE.search(req_msg or "")
        return match.group(1) if match else ""