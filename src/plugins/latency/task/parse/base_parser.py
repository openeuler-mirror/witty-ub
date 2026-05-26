"""日志解析器基类"""
import logging
import os
import re
from abc import ABC, abstractmethod
from datetime import datetime
import hashlib

from latency.ENUM.ds_log import OpType, AccessLogCol, StatusCode
from latency.common.ds_log_io import Progress, glob_paths, parse_timestamp, open_log
from latency.config.config import Config
from latency.regex.kvcache_log import OBJECT_KEY_RE
from latency.schemas.ds_log import LogEntry
from latency.schemas.log import LogFileModel


def get_ds_log_config():
    """获取DS日志分析配置"""
    config = Config()
    return config.get_config().ds_log_analyzer


logger = logging.getLogger(__name__)

SDK_GET_OPS = frozenset({OpType.DS_KV_CLIENT_GET, OpType.DS_OBJECT_CLIENT_GET})
WORKER_GET_OPS = frozenset({OpType.DS_POSIX_GET})
ACCESS_LOG_MIN_PARTS = 13
# 通用日志分隔符：竖线，支持前后带空白
LOG_DELIMITER = r"\s*\|\s*"


class LogParser(ABC):
    """日志解析器基类"""
    label: str = ""
    _handle_errors: bool = False

    _UUID_RE = re.compile(
        r"\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b",
        re.IGNORECASE,
    )

    @property
    def patterns(self) -> list[str]:
        """获取日志文件模式，子类需要实现这个属性"""
        raise NotImplementedError

    def parse(self, input_dir: str) -> list[LogEntry]:
        """解析目录下的日志文件"""
        entries: list[LogEntry] = []
        paths = glob_paths([os.path.join(input_dir, p) for p in self.patterns])
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
        """
        按通用竖线分隔符拆分日志行，自动处理分隔符前后空白
        返回拆分后的字段列表
        """
        if not line:
            return []
        return re.split(LOG_DELIMITER, line.strip())

    @abstractmethod
    def match_line(self, line: str, pod_ip: str) -> LogEntry | None:
        """匹配日志行，子类需要实现"""
        ...


class AccessLogParser(LogParser):
    """访问日志解析器基类"""

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

    @staticmethod
    def parse_access_line(line: str):
        """
        解析访问日志行，支持两种格式：
        1. 简化格式：用 | 分隔，包含 status_code | handle | elapsed | size | req_msg | resp_msg
        2. 完整格式：用空格分隔，至少13列
        """
        # 去除首尾空白
        line = line.strip()
        if not line:
            return None

        # 检测日志格式：简化格式用 | 分隔，完整格式用空格分隔
        if "|" in line:
            # 简化格式: status_code | handle | elapsed | size | req_msg | resp_msg
            parts = LogParser.split_by_delimiter(line)
            if len(parts) < 5:
                return None
            # 简化格式没有 timestamp 和 trace_id，生成基于内容的 trace_id
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
            # 使用行内容生成伪 trace_id
            content_hash = hashlib.md5(line.encode()).hexdigest()[:16]
            trace_id = f"{content_hash[:8]}-{content_hash[8:12]}-{content_hash[12:16]}-0000-000000000000"
            return {
                "timestamp": timestamp,
                "trace_id": trace_id,
                "status_code": parts[0],
                "handle": parts[1],
                "elapsed": parts[2],
                "size": parts[3],
                "req_msg": parts[4] if len(parts) > 4 else "",
                "resp_msg": parts[5] if len(parts) > 5 else "",
            }
        else:
            # 完整格式: 空格分隔，至少13列
            if len(line) < 80 or line[0] != "2":
                return None
            parts = line.split()
            if len(parts) < ACCESS_LOG_MIN_PARTS:
                return None
            handle = parts[AccessLogCol.HANDLE].strip()
            return {
                "timestamp": parts[AccessLogCol.TIMESTAMP].strip(),
                "trace_id": parts[AccessLogCol.TRACE_ID].strip(),
                "status_code": parts[AccessLogCol.STATUS_CODE].strip(),
                "handle": handle,
                "elapsed": parts[AccessLogCol.ELAPSED].strip(),
                "size": parts[AccessLogCol.SIZE].strip(),
                "req_msg": parts[AccessLogCol.REQ_MSG].strip(),
                "resp_msg": parts[AccessLogCol.RESP_MSG].strip(),
            }
