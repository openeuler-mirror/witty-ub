"""Worker运行日志合并解析器 - 一次遍历处理所有 Run-format 日志类型"""

import logging
import os
from typing import Optional

from latency.common.ds_log_io import parse_timestamp, open_log
from latency.regex.kvcache_log import (
    URMA_RE, URMA_LINK_RE, REMOTE_GET_RE, REMOTE_PULL_RE,
    QUERY_META_RE, SDK_PROCESS_RE, SDK_RPC_RE,
    LOCAL_WORKER_COST_RE, LOCAL_WORKER_LOCK_RE,
    REMOTE_WORKER_COST_RE, REMOTE_WORKER_RPC_RE,
    REMOTE_ENDPOINT_RE,
    MASTER_PROCESS_RE, MASTER_RPC_RE,
)
from latency.regex.kvcache_log_file import WORKER_INFO_LOG_PATTERNS
from latency.schemas.ds_log import LogEntry
from latency.ENUM.ds_log import EntryType
from latency.schemas.log import LogFileModel
from latency.schemas.request import ParseConfig
from latency.parse.base_parser import LogParser, RUN_LOG_MIN_PARTS

logger = logging.getLogger(__name__)

URMA_LABEL = "Worker urma parse"
REMOTE_PULL_LABEL = "Worker remote pull parse"
LINK_LABEL = "Worker link parse"
QUERY_META_LABEL = "Worker query meta parse"
METRICS_LABEL = "Worker metrics parse"

# 基础关键字（WorkerInfoParser 使用）
BASE_KEYWORDS = (
    "URMA_ELAPSED_TOTAL", "Remote get request", "Processing pull object[",
    "elapsed ms:", "Master query done",
)

# 指标关键字（WorkerMetricsLogParser 使用）
METRICS_KEYWORDS = (
    "totalCost:", "Worker to master rpc QueryMeta:",
    "ProcessGetObjectRequest:", "worker SafeObject WLock:",
    "[Get/RemotePull] finish",
    "[Get] Remote done", "QueryMeta done", "[ZMQ_RPC_FRAMEWORK_SLOW]",
)

ALL_KEYWORDS = BASE_KEYWORDS + METRICS_KEYWORDS


class WorkerInfoParser(LogParser):
    """Worker运行日志合并解析器

    合并 Urma / RemotePull / Link / QueryMeta 4 个解析器，
    一次读文件 + 一次 if/elif 分派，消除重复的 _build_parsed_run 和 parse_timestamp。
    
    注意：指标日志由 WorkerMetricsLogParser 单独处理，避免关键字冲突。
    """
    label = "Worker info parse"
    _handle_errors = True
    _keywords = BASE_KEYWORDS

    @property
    def patterns(self) -> list[str]:
        return getattr(self, "_runtime_patterns", WORKER_INFO_LOG_PATTERNS)

    def __init__(self, parse_config: Optional[ParseConfig] = None):
        super().__init__(parse_config)
        self._scan_scope_enabled = False
        self._target_trace_ids: set[str] = set()
        self._target_pod_trace_keys: set[tuple[str, str]] = set()
        self._target_pod_ips: set[str] = set()

    def set_scan_scope(self, scan_scope: Optional[dict]) -> None:
        """Limit INFO parsing to traces/pods that can contribute to final results.
        
        优化策略：主进程预构建集合后直接传递，子进程直接使用，避免重新创建集合。
        """
        if not scan_scope:
            self._scan_scope_enabled = False
            self._target_trace_ids = set()
            self._target_pod_trace_keys = set()
            self._target_pod_ips = set()
            return

        self._scan_scope_enabled = bool(scan_scope.get("enabled"))
        
        # 直接使用传递过来的集合对象（已经是 set），避免重新创建
        trace_ids = scan_scope.get("trace_ids")
        if isinstance(trace_ids, set):
            self._target_trace_ids = trace_ids
        else:
            self._target_trace_ids = set(trace_ids or ())
        
        pod_trace_keys = scan_scope.get("pod_trace_keys")
        if isinstance(pod_trace_keys, set):
            self._target_pod_trace_keys = pod_trace_keys
        else:
            self._target_pod_trace_keys = {
                (pod_ip, trace_id)
                for pod_ip, trace_id in (pod_trace_keys or ())
            }
        
        pod_ips = scan_scope.get("pod_ips")
        if isinstance(pod_ips, set):
            self._target_pod_ips = pod_ips
        else:
            self._target_pod_ips = set(pod_ips or ())

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
                    if not self._file_scope_may_allow(label, entry_pod_ip):
                        continue
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
        if not self._file_scope_may_allow(label, entry_pod_ip):
            return None
        if not self._scope_allows(label, parsed["trace_id"], entry_pod_ip):
            return None
        ts = parse_timestamp(parsed["timestamp"])
        if not self._filter_by_time(ts):
            return None

        return self._dispatch(label, parsed, ts, pod_ip)

    def _dispatch(self, label: str, parsed: dict, ts, pod_ip: str) -> list[LogEntry] | None:
        """if/elif 关键字分派到对应的提取逻辑，返回列表"""
        if label == URMA_LABEL:
            entry = self._parse_urma(parsed, ts, pod_ip)
            return [entry] if entry else None
        if label == REMOTE_PULL_LABEL:
            msg = parsed["msg"]
            if "Remote get request" in msg:
                entry = self._parse_remote_get(parsed, ts, pod_ip)
            else:
                entry = self._parse_remote_pull(parsed, ts, pod_ip)
            return [entry] if entry else None
        if label == LINK_LABEL:
            entry = self._parse_link(parsed, ts, pod_ip)
            return [entry] if entry else None
        if label == QUERY_META_LABEL:
            entry = self._parse_query_meta(parsed, ts, pod_ip)
            return [entry] if entry else None
        if label == METRICS_LABEL:
            entry = self._parse_metrics(parsed, ts, pod_ip)
            return [entry] if entry else None
        return None

    def _scope_allows(self, label: str, trace_id: str, pod_ip: str) -> bool:
        if not self._scan_scope_enabled:
            return True

        if label == URMA_LABEL:
            if trace_id:
                return trace_id in self._target_trace_ids
            return pod_ip in self._target_pod_ips

        if label == QUERY_META_LABEL:
            # 优先检查 trace_id，其次检查 (pod_ip, trace_id) 组合
            if trace_id and trace_id in self._target_trace_ids:
                return True
            if trace_id and (pod_ip, trace_id) in self._target_pod_trace_keys:
                return True
            return False

        if label in (REMOTE_PULL_LABEL, LINK_LABEL, METRICS_LABEL):
            return bool(trace_id) and trace_id in self._target_trace_ids

        return True

    def _file_scope_may_allow(self, label: str, pod_ip: str) -> bool:
        if not self._scan_scope_enabled:
            return True

        if label == QUERY_META_LABEL:
            # 优先检查 trace_id，其次检查 pod_ip
            if self._target_trace_ids:
                return True
            return pod_ip in self._target_pod_ips

        if label == URMA_LABEL:
            return pod_ip in self._target_pod_ips or bool(self._target_trace_ids)

        if label in (REMOTE_PULL_LABEL, LINK_LABEL, METRICS_LABEL):
            return bool(self._target_trace_ids)

        return True

    @staticmethod
    def _label_for_line(line: str, allow_pod_scoped_labels: bool = True) -> str | None:
        if "URMA_ELAPSED_TOTAL" in line:
            return URMA_LABEL
        if "Remote get request" in line or "Processing pull object[" in line:
            return REMOTE_PULL_LABEL
        if "elapsed ms:" in line:
            return LINK_LABEL
        if not allow_pod_scoped_labels:
            return None
        if "Master query done" in line:
            return QUERY_META_LABEL
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
        endpoint_match = REMOTE_ENDPOINT_RE.search(parsed["msg"])
        if endpoint_match:
            src_addr, dst_addr = (value.strip() for value in endpoint_match.groups())
        else:
            src_addr = None
            dst_addr = None
        return LogEntry(
            timestamp=ts,
            elapsed_us=elapsed_us,
            pod_ip=entry_pod_ip,
            trace_id=parsed["trace_id"],
            entry_type=entry_type,
            cluster_name=parsed["cluster_name"] if parsed["cluster_name"] else None,
            src_addr=src_addr,
            dst_addr=dst_addr,
        )

    @staticmethod
    def _any_keyword_in(line: str) -> bool:
        for kw in ALL_KEYWORDS:
            if kw in line:
                return True
        return False

    @staticmethod
    def _any_metrics_keyword_in(line: str) -> bool:
        for kw in METRICS_KEYWORDS:
            if kw in line:
                return True
        return False

    @staticmethod
    def _build_run(parts: list[str], plen: int) -> dict:
        col = (0, 3, 5, 6, 7)
        keys = ("timestamp", "pod_name", "trace_id", "cluster_name", "msg")
        return {k: parts[idx].strip() if idx < plen else "" for k, idx in zip(keys, col)}
