# NON-PRODUCTION: reference implementation（逐行 parse()/match_line() 生产零调用；pattern / _keywords / 类身份仍被扫描器使用，见 test/test_layer_boundaries.py 的白名单）
"""日志解析器基类"""
import logging
import os
import re
from abc import ABC, abstractmethod
from datetime import datetime
from enum import IntEnum

from latency.ENUM.ds_log import OpType, StatusCode
from latency.common.ds_log_io import Progress, glob_paths, parse_timestamp, open_log
from latency.parse.keywords import (
    ACCESS_LOG_MIN_PARTS,
    RUN_LOG_MIN_PARTS,
    SDK_GET_OPS,
    SDK_SET_OPS,
    WORKER_GET_OPS,
    WORKER_SET_OPS,
)
from latency.parse.keywords import AccessCol as _AccessCol
from latency.parse.keywords import RunCol as _RunCol
from latency.parse.keywords import TRACE_FIELD_RE as _TRACE_FIELD_PATTERN
from latency.parse.keywords import UUID_RE as _UUID_PATTERN
from latency.regex.kvcache_log import OBJECT_KEY_RE
from latency.schemas.ds_log import LogEntry
from latency.schemas.log import LogFileModel
from latency.schemas.request import ParseConfig


logger = logging.getLogger(__name__)

# P1 契约层（2026-09-16）：OPS 集合与切段门禁已搬到 ``parse/keywords.py``，
# 本文件在最上方 import 回来再导出 —— 既有 ``from latency.parse.base_parser import
# SDK_GET_OPS`` 等用法一字不用改。


def _build_parsed_access(parts: list[str], plen: int) -> dict:
    """从已按 '|' 切分的 access 行提取字段（缺失列 pad 为空串）。

    parse_access_line 与 process_worker 的 _pre_parsed 预解析共享此实现，
    消除双实现漂移。字面量 dict（常量键）为实测最快形式。
    """
    col = LogParser.AccessCol
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


def _build_parsed_run(parts: list[str], plen: int) -> dict:
    """从已按 '|' 切分的 run 行提取字段（缺失列 pad 为空串）。"""
    col = LogParser.RunCol
    return {
        "timestamp": parts[col.TIMESTAMP].strip(),
        "pod_name": parts[col.POD_NAME].strip() if col.POD_NAME < plen else "",
        "trace_id": parts[col.TRACE_ID].strip() if col.TRACE_ID < plen else "",
        "cluster_name": parts[col.CLUSTER_NAME].strip() if col.CLUSTER_NAME < plen else "",
        "msg": parts[col.MSG].strip() if col.MSG < plen else "",
    }


class LogParser(ABC):
    """日志解析器基类"""
    label: str = ""
    _handle_errors: bool = False

    # P1 契约层：pattern 搬到 ``parse/keywords.py``（唯一来源），这里保持同名绑定，
    # 既有 ``LogParser._UUID_RE`` / ``LogParser._TRACE_FIELD_RE`` 用法不变。
    _UUID_RE = _UUID_PATTERN
    _TRACE_FIELD_RE = _TRACE_FIELD_PATTERN

    def __init__(self: "LogParser", parse_config: ParseConfig | None = None) -> None:
        self.parse_config = parse_config or ParseConfig()
        self._filtered_by_time = 0
        self._start_dt = None
        self._end_dt = None
        if parse_config and parse_config.is_time_filter_enabled():
            if parse_config.start_time:
                self._start_dt = parse_timestamp(parse_config.start_time)
            if parse_config.end_time:
                self._end_dt = parse_timestamp(parse_config.end_time)
    
    def _filter_by_time(self: "LogParser", ts: datetime) -> bool:
        if self._start_dt is not None and ts < self._start_dt:
            self._filtered_by_time += 1
            return False
        if self._end_dt is not None and ts > self._end_dt:
            self._filtered_by_time += 1
            return False
        return True

    # P1 契约层：段位次表搬到 ``parse/keywords.py``（唯一来源）。
    # 保留 ``LogParser.AccessCol`` / ``LogParser.RunCol`` 这两个名字，既有用法与
    # 类型注解一字不改。
    AccessCol = _AccessCol
    RunCol = _RunCol

    @property
    def patterns(self: "LogParser") -> list[str]:
        """获取日志文件模式，子类需要实现这个属性"""
        raise NotImplementedError

    def parse(self: "LogParser", input_dir: str) -> list[LogEntry]:
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

    def _scan_file(self: "LogParser", path: str, pod_ip: str, log_id: str,
                   entries: list[LogEntry], progress: Progress,
                   file_idx: int) -> None:
        """扫描单个日志文件"""
        with open_log(path) as f:
            for line_no, line in enumerate(f, 1):
                if line_no % 100_000 == 0:
                    progress.update(file_idx, path, line=line_no, match=len(entries))
                entry = self.match_line(line, pod_ip)
                if entry:
                    entry.log_id = log_id
                    entries.append(entry)

    def extract_pod_ip(self: "LogParser", path: str) -> str:
        """从路径中提取Pod IP"""
        _dir = os.path.basename(os.path.dirname(path))
        return _dir.removeprefix("Worker_").removeprefix("dsworker_").removesuffix("worker_")

    @staticmethod
    def _clean_trace_id(value: str) -> str:
        return value.strip().strip("[]{}()\"'")

    @classmethod
    def extract_explicit_trace_id(cls: "type[LogParser]", line: str) -> str:
        """从 trace_id=... / trace_id:... 这类显式字段中提取 trace_id"""
        match = cls._TRACE_FIELD_RE.search(line or "")
        return cls._clean_trace_id(match.group("trace")) if match else ""

    @classmethod
    def extract_trace_id(cls: "type[LogParser]", line: str) -> str:
        """从行中提取trace_id，优先使用显式 trace_id 字段，其次回退 UUID"""
        explicit = cls.extract_explicit_trace_id(line)
        if explicit:
            return explicit
        match = cls._UUID_RE.search(line or "")
        return match.group(0) if match else ""

    @classmethod
    def resolve_trace_id(cls: "type[LogParser]", current: str, *sources: str) -> str:
        """选择用于关联的 trace_id。

        message 中显式 trace_id=... 比格式列更接近实际链路 trace；
        没有显式 trace 时保留格式列，只有格式列为空才回退到 UUID。
        """
        for source in sources:
            explicit = cls.extract_explicit_trace_id(source)
            if explicit:
                return explicit
        if current:
            return current
        for source in sources:
            fallback = cls.extract_trace_id(source)
            if fallback:
                return fallback
        return ""
    
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

        return _build_parsed_access(parts, len(parts))

    @staticmethod
    def parse_run_line(line: str) -> dict | None:
        if not line or line[0] != "2":
            return None

        parts = line.split("|")
        if len(parts) < RUN_LOG_MIN_PARTS:
            return None

        return _build_parsed_run(parts, len(parts))

    @abstractmethod
    def match_line(self: "LogParser", line: str, pod_ip: str) -> LogEntry | None:
        """匹配日志行，子类需要实现"""
        ...


class AccessLogParser(LogParser):
    """接口日志解析器基类，提供Access格式日志的便捷解析能力"""

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
