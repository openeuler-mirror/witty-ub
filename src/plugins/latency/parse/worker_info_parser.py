"""Worker INFO 日志合并解析器 - 一次遍历处理所有 Run-format 日志类型"""

import logging
import os
from typing import Optional

from latency.common.ds_log_io import parse_timestamp, open_log
from latency.regex.kvcache_log import (
    URMA_RE, URMA_LINK_RE, REMOTE_GET_RE, REMOTE_PULL_RE,
    QUERY_META_RE, SDK_PROCESS_RE, SDK_RPC_RE,
    LOCAL_WORKER_COST_RE, LOCAL_WORKER_LOCK_RE,
    REMOTE_WORKER_COST_RE, REMOTE_WORKER_RPC_RE,
    MASTER_PROCESS_RE, MASTER_RPC_RE,
)
from latency.regex.kvcache_log_file import WORKER_INFO_LOG_PATTERNS
from latency.schemas.ds_log import LogEntry, EntryType
from latency.schemas.log import LogFileModel
from latency.schemas.request import ParseConfig
from latency.parse.base_parser import LogParser, RUN_LOG_MIN_PARTS

logger = logging.getLogger(__name__)

URMA_LABEL = "Worker urma parse"
REMOTE_PULL_LABEL = "Worker remote pull parse"
LINK_LABEL = "Worker link parse"
QUERY_META_LABEL = "Worker query meta parse"
METRICS_LABEL = "Worker metrics parse"

ALL_KEYWORDS = (
    "URMA_ELAPSED_TOTAL", "Remote get request", "Processing pull object[",
    "elapsed ms:", "Master query done", "totalCost:",
    "Worker to master rpc QueryMeta:", "ProcessGetObjectRequest:",
    "worker SafeObject WLock:", "[Get] finish", "[RemotePull] finish",
    "[Get] Remote done", "QueryMeta done", "[ZMQ_RPC_FRAMEWORK_SLOW]",
)


class WorkerInfoParser(LogParser):
    """Worker INFO 日志合并解析器

    合并 Urma / RemotePull / Link / QueryMeta / WorkerMetrics 5 个解析器，
    一次读文件 + 一次 if/elif 分派，消除重复的 _build_parsed_run 和 parse_timestamp。
    """
    label = "Worker info parse"
    _handle_errors = True
    _keywords = ALL_KEYWORDS

    @property
    def patterns(self) -> list[str]:
        return WORKER_INFO_LOG_PATTERNS

    def __init__(self, parse_config: Optional[ParseConfig] = None):
        super().__init__(parse_config)
        self._scan_scope_enabled = False
        self._target_trace_ids: set[str] = set()
        self._target_pod_trace_keys: set[tuple[str, str]] = set()
        self._target_pod_ips: set[str] = set()

    def set_scan_scope(self, scan_scope: Optional[dict]) -> None:
        """Limit INFO parsing to traces/pods that can contribute to final results."""
        if not scan_scope:
            self._scan_scope_enabled = False
            self._target_trace_ids = set()
            self._target_pod_trace_keys = set()
            self._target_pod_ips = set()
            return

        self._scan_scope_enabled = bool(scan_scope.get("enabled"))
        self._target_trace_ids = set(scan_scope.get("trace_ids") or ())
        self._target_pod_trace_keys = {
            (pod_ip, trace_id)
            for pod_ip, trace_id in (scan_scope.get("pod_trace_keys") or ())
        }
        self._target_pod_ips = set(scan_scope.get("pod_ips") or ())

    def scan_file(self, path: str) -> dict[str, list[LogEntry]]:
        """扫描单个 Run-format 日志文件，返回按原始 label 分组的 entries"""
        results: dict[str, list[LogEntry]] = {
            URMA_LABEL: [],
            REMOTE_PULL_LABEL: [],
            LINK_LABEL: [],
            QUERY_META_LABEL: [],
            METRICS_LABEL: [],
        }
        try:
            pod_ip = self.extract_pod_ip(path)
        except Exception as e:
            logger.warning(f"Failed to extract pod_ip from {path}: {e}")
            pod_ip = ""

        try:
            file_size = os.path.getsize(path)
        except OSError:
            file_size = 0

        log_file = LogFileModel(file_path=path, file_size=file_size)
        file_name = os.path.basename(path)
        line_count = 0
        match_count = 0

        try:
            with open_log(path) as f:
                for line in f:
                    line_count += 1
                    if not line or line[0] != "2":
                        continue
                    label = self._label_for_line(line)
                    if not label:
                        continue

                    parts = line.split("|")
                    plen = len(parts)
                    if plen < RUN_LOG_MIN_PARTS:
                        continue

                    parsed = self._build_run(parts, plen)
                    entry_pod_ip = parsed["pod_name"] if parsed["pod_name"] else pod_ip
                    if not self._scope_allows(label, parsed["trace_id"], entry_pod_ip):
                        continue
                    ts = parse_timestamp(parsed["timestamp"])
                    if not self._filter_by_time(ts):
                        continue

                    entry = self._dispatch(label, parsed, ts, pod_ip)
                    if entry:
                        entry.log_id = log_file.id
                        results[label].append(entry)
                        match_count += 1

        except EOFError:
            logger.warning(f"Skipping corrupted file {path}")
        except Exception as e:
            logger.warning(f"Error reading {path}: {e}")

        logger.info(
            f"[Worker info] done {file_name} | "
            f"lines {line_count:,} | match {match_count:,}"
        )
        return results

    def match_line(self, line: str, pod_ip: str) -> LogEntry | None:
        """兼容单行匹配接口（非热路径）"""
        if not line or line[0] != "2":
            return None
        label = self._label_for_line(line)
        if not label:
            return None

        parts = line.split("|")
        plen = len(parts)
        if plen < RUN_LOG_MIN_PARTS:
            return None

        parsed = self._build_run(parts, plen)
        entry_pod_ip = parsed["pod_name"] if parsed["pod_name"] else pod_ip
        if not self._scope_allows(label, parsed["trace_id"], entry_pod_ip):
            return None
        ts = parse_timestamp(parsed["timestamp"])
        if not self._filter_by_time(ts):
            return None

        return self._dispatch(label, parsed, ts, pod_ip)

    def _dispatch(self, label: str, parsed: dict, ts, pod_ip: str) -> LogEntry | None:
        """if/elif 关键字分派到对应的提取逻辑"""
        if label == URMA_LABEL:
            return self._parse_urma(parsed, ts, pod_ip)
        if label == REMOTE_PULL_LABEL:
            msg = parsed["msg"]
            if "Remote get request" in msg:
                return self._parse_remote_get(parsed, ts, pod_ip)
            return self._parse_remote_pull(parsed, ts, pod_ip)
        if label == LINK_LABEL:
            return self._parse_link(parsed, ts, pod_ip)
        if label == QUERY_META_LABEL:
            return self._parse_query_meta(parsed, ts, pod_ip)
        if label == METRICS_LABEL:
            return self._parse_metrics(parsed, ts, pod_ip)
        return None

    def _scope_allows(self, label: str, trace_id: str, pod_ip: str) -> bool:
        if not self._scan_scope_enabled:
            return True

        if label == URMA_LABEL:
            if pod_ip in self._target_pod_ips:
                return True
            if trace_id:
                return trace_id in self._target_trace_ids
            return False

        if label in (QUERY_META_LABEL, METRICS_LABEL):
            return bool(trace_id) and (pod_ip, trace_id) in self._target_pod_trace_keys

        if label in (REMOTE_PULL_LABEL, LINK_LABEL):
            return bool(trace_id) and trace_id in self._target_trace_ids

        return True

    @staticmethod
    def _label_for_line(line: str) -> str | None:
        if "URMA_ELAPSED_TOTAL" in line:
            return URMA_LABEL
        if "Remote get request" in line or "Processing pull object[" in line:
            return REMOTE_PULL_LABEL
        if "elapsed ms:" in line:
            return LINK_LABEL
        if "Master query done" in line:
            return QUERY_META_LABEL
        if WorkerInfoParser._any_metrics_keyword_in(line):
            return METRICS_LABEL
        return None

    # ---- 各类型提取逻辑 (从对应 parser 提取) ----

    def _parse_urma(self, parsed: dict, ts, pod_ip: str) -> LogEntry | None:
        msg = parsed["msg"]
        m = URMA_RE.search(msg)
        if not m:
            return None
        elapsed_ms, src, dst, inflight = m.groups()
        entry_pod_ip = parsed["pod_name"] if parsed["pod_name"] else pod_ip
        return LogEntry(
            timestamp=ts,
            elapsed_us=float(elapsed_ms) * 1000,
            src_addr=src.strip(),
            dst_addr=dst.strip(),
            inflight_count=int(inflight),
            pod_ip=entry_pod_ip,
            trace_id=parsed["trace_id"],
            entry_type=EntryType.URMA,
            cluster_name=parsed["cluster_name"] if parsed["cluster_name"] else None,
        )

    def _parse_remote_get(self, parsed: dict, ts, pod_ip: str) -> LogEntry | None:
        msg = parsed["msg"]
        trace_id = parsed["trace_id"]
        if not trace_id:
            return None
        m = REMOTE_GET_RE.search(msg)
        if not m:
            return None
        src_addr, dst_addr = m.groups()
        entry_pod_ip = parsed["pod_name"] if parsed["pod_name"] else pod_ip
        return LogEntry(
            timestamp=ts,
            elapsed_us=0,
            object_key="",
            request_size="",
            src_addr=src_addr.strip(),
            dst_addr=dst_addr.strip(),
            pod_ip=entry_pod_ip,
            trace_id=trace_id,
            entry_type=EntryType.REMOTE_PULL,
            cluster_name=parsed["cluster_name"] if parsed["cluster_name"] else None,
        )

    def _parse_remote_pull(self, parsed: dict, ts, pod_ip: str) -> LogEntry | None:
        msg = parsed["msg"]
        trace_id = parsed["trace_id"]
        if not trace_id:
            return None
        m = REMOTE_PULL_RE.search(msg)
        if not m:
            return None
        src_addr, dst_addr = m.groups()
        entry_pod_ip = parsed["pod_name"] if parsed["pod_name"] else pod_ip
        return LogEntry(
            timestamp=ts,
            elapsed_us=0,
            object_key="",
            request_size="",
            src_addr=src_addr.strip(),
            dst_addr=dst_addr.strip(),
            pod_ip=entry_pod_ip,
            trace_id=trace_id,
            entry_type=EntryType.REMOTE_PULL,
            cluster_name=parsed["cluster_name"] if parsed["cluster_name"] else None,
        )

    def _parse_link(self, parsed: dict, ts, pod_ip: str) -> LogEntry | None:
        msg = parsed["msg"]
        trace_id = parsed["trace_id"]
        if ("WorkerWorkerExchangeUrmaConnectInfo finish" not in msg
                and "Worker-worker transport connection exchange success" not in msg):
            return None
        if "WorkerWorkerExchangeUrmaConnectInfo finish" in msg and "status=code: [OK]" not in msg:
            return None
        m = URMA_LINK_RE.search(msg)
        if not m:
            return None
        elapsed_ms = m.group(1)
        entry_pod_ip = parsed["pod_name"] if parsed["pod_name"] else pod_ip
        return LogEntry(
            timestamp=ts,
            elapsed_us=float(elapsed_ms) * 1000,
            pod_ip=entry_pod_ip,
            trace_id=trace_id,
            entry_type=EntryType.LINK,
            cluster_name=parsed["cluster_name"] if parsed["cluster_name"] else None,
        )

    def _parse_query_meta(self, parsed: dict, ts, pod_ip: str) -> LogEntry | None:
        msg = parsed["msg"]
        trace_id = parsed["trace_id"]
        if not trace_id:
            return None
        m = QUERY_META_RE.search(msg)
        if not m:
            return None
        elapsed_ms = m.group(1)
        entry_pod_ip = parsed["pod_name"] if parsed["pod_name"] else pod_ip
        return LogEntry(
            timestamp=ts,
            elapsed_us=float(elapsed_ms) * 1000,
            pod_ip=entry_pod_ip,
            trace_id=trace_id,
            entry_type=EntryType.QUERY_META,
            cluster_name=parsed["cluster_name"] if parsed["cluster_name"] else None,
        )

    def _parse_metrics(self, parsed: dict, ts, pod_ip: str) -> LogEntry | None:
        msg = parsed["msg"]
        trace_id = parsed["trace_id"]
        if not trace_id:
            return None

        if "totalCost:" in msg:
            m = SDK_PROCESS_RE.search(msg)
            if m:
                return self._mk_metrics(parsed, ts, pod_ip, EntryType.SDK_PROCESS, float(m.group(1)) * 1000)
        if "Worker to master rpc QueryMeta:" in msg:
            m = SDK_RPC_RE.search(msg)
            if m:
                return self._mk_metrics(parsed, ts, pod_ip, EntryType.SDK_RPC, float(m.group(1)) * 1000)
        if "ProcessGetObjectRequest:" in msg:
            m = LOCAL_WORKER_COST_RE.search(msg)
            if m:
                return self._mk_metrics(parsed, ts, pod_ip, EntryType.LOCAL_WORKER_COST, float(m.group(1)) * 1000)
        if "worker SafeObject WLock:" in msg:
            m = LOCAL_WORKER_LOCK_RE.search(msg)
            if m:
                return self._mk_metrics(parsed, ts, pod_ip, EntryType.LOCAL_WORKER_LOCK, float(m.group(1)) * 1000)
        if "[Get] finish" in msg or "[RemotePull] finish" in msg:
            m = REMOTE_WORKER_COST_RE.search(msg)
            if m:
                return self._mk_metrics(parsed, ts, pod_ip, EntryType.REMOTE_WORKER_COST, float(m.group(1)) * 1000)
        if "[Get] Remote done" in msg:
            m = REMOTE_WORKER_RPC_RE.search(msg)
            if m:
                return self._mk_metrics(parsed, ts, pod_ip, EntryType.REMOTE_WORKER_RPC, float(m.group(1)) * 1000)
        if "QueryMeta done" in msg:
            m = MASTER_PROCESS_RE.search(msg)
            if m:
                return self._mk_metrics(parsed, ts, pod_ip, EntryType.MASTER_PROCESS, float(m.group(1)) * 1000)
        if "[ZMQ_RPC_FRAMEWORK_SLOW]" in msg:
            m = MASTER_RPC_RE.search(msg)
            if m:
                return self._mk_metrics(parsed, ts, pod_ip, EntryType.MASTER_RPC, float(m.group(1)))

        return None

    @staticmethod
    def _mk_metrics(parsed: dict, ts, pod_ip: str, entry_type: EntryType, elapsed_us: float) -> LogEntry:
        entry_pod_ip = parsed["pod_name"] if parsed["pod_name"] else pod_ip
        return LogEntry(
            timestamp=ts,
            elapsed_us=elapsed_us,
            pod_ip=entry_pod_ip,
            trace_id=parsed["trace_id"],
            entry_type=entry_type,
            cluster_name=parsed["cluster_name"] if parsed["cluster_name"] else None,
        )

    @staticmethod
    def _any_keyword_in(line: str) -> bool:
        for kw in ALL_KEYWORDS:
            if kw in line:
                return True
        return False

    @staticmethod
    def _any_metrics_keyword_in(line: str) -> bool:
        for kw in ALL_KEYWORDS[5:]:
            if kw in line:
                return True
        return False

    @staticmethod
    def _build_run(parts: list[str], plen: int) -> dict:
        col = (0, 3, 5, 6, 7)
        keys = ("timestamp", "pod_name", "trace_id", "cluster_name", "msg")
        return {k: parts[idx].strip() if idx < plen else "" for k, idx in zip(keys, col)}
