"""Worker运行日志合并解析器 - 一次遍历处理所有 Run-format 日志类型"""

import logging
import os
import re
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
SDK_PROCESS_LABEL = "Worker sdk process parse"
SDK_RPC_LABEL = "Worker sdk rpc parse"
LOCAL_WORKER_COST_LABEL = "Worker local worker cost parse"
LOCAL_WORKER_LOCK_LABEL = "Worker local worker lock parse"
REMOTE_WORKER_COST_LABEL = "Worker remote worker cost parse"
REMOTE_WORKER_RPC_LABEL = "Worker remote worker rpc parse"
MASTER_PROCESS_LABEL = "Worker master process parse"
MASTER_RPC_LABEL = "Worker master rpc parse"

TIMED_LABELS = (
    SDK_PROCESS_LABEL,
    SDK_RPC_LABEL,
    LOCAL_WORKER_COST_LABEL,
    LOCAL_WORKER_LOCK_LABEL,
    REMOTE_WORKER_COST_LABEL,
    REMOTE_WORKER_RPC_LABEL,
    MASTER_PROCESS_LABEL,
    MASTER_RPC_LABEL,
)

# 基础关键字（WorkerInfoParser 使用）
BASE_KEYWORDS = (
    "URMA_ELAPSED_TOTAL", "Remote get request", "Processing pull object[",
    "elapsed ms:", "Master query done",
)

# 细分耗时关键字（每个关键字对应一个明确的 Worker info label）
TIMED_KEYWORDS = (
    "totalCost:", "Worker to master rpc QueryMeta:",
    "ProcessGetObjectRequest:", "worker SafeObject WLock:",
    "[Get/RemotePull] finish", "[Get] Remote done",
    "QueryMeta done", "[ZMQ_RPC_FRAMEWORK_SLOW]",
)

ALL_KEYWORDS = BASE_KEYWORDS + TIMED_KEYWORDS

_TIMED_RESP_EXCLUDED_FIELDS = frozenset({"cost", "src", "dst"})
_IP_ENDPOINT_RE = re.compile(r"\b\d{1,3}(?:\.\d{1,3}){3}(?::\d+)?\b")


class WorkerInfoParser(LogParser):
    """Worker运行日志合并解析器

    合并 URMA / RemotePull / Link / QueryMeta / 细分耗时解析，
    一次读文件 + 一次 if/elif 分派，消除重复的 _build_parsed_run 和 parse_timestamp。
    
    细分耗时日志也在这里按独立 label 输出，避免多解析器首个命中导致遗漏。
    """
    label = "Worker info parse"
    _handle_errors = True
    _keywords = ALL_KEYWORDS

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
            SDK_PROCESS_LABEL: [],
            SDK_RPC_LABEL: [],
            LOCAL_WORKER_COST_LABEL: [],
            LOCAL_WORKER_LOCK_LABEL: [],
            REMOTE_WORKER_COST_LABEL: [],
            REMOTE_WORKER_RPC_LABEL: [],
            MASTER_PROCESS_LABEL: [],
            MASTER_RPC_LABEL: [],
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
                    if not self._line_may_match(line):
                        continue

                    parts = line.split("|")
                    plen = len(parts)
                    if plen < RUN_LOG_MIN_PARTS:
                        continue

                    parsed = self._build_run(parts, plen)
                    ts = parse_timestamp(parsed["timestamp"])
                    if not self._filter_by_time(ts):
                        continue

                    matched = self._parse_first_match(line, parsed, ts, pod_ip)
                    if not matched:
                        continue

                    label, entry = matched
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

    def _scan_file(self, path, pod_ip, log_id, entries, progress, file_idx):
        """兼容基类 parse() 路径：match_line 返回列表。"""
        with open_log(path) as f:
            for line_no, line in enumerate(f, 1):
                if line_no % 100_000 == 0:
                    progress.update(file_idx, path, line=line_no, match=len(entries))
                matched_entries = self.match_line(line, pod_ip)
                for entry in matched_entries or ():
                    entry.log_id = log_id
                    entries.append(entry)

    def match_line(self, line: str, pod_ip: str) -> list[LogEntry] | None:
        """兼容单行匹配接口（非热路径）"""
        if not line or line[0] != "2":
            return None
        if not self._line_may_match(line):
            return None

        parts = line.split("|")
        plen = len(parts)
        if plen < RUN_LOG_MIN_PARTS:
            return None

        parsed = self._build_run(parts, plen)
        ts = parse_timestamp(parsed["timestamp"])
        if not self._filter_by_time(ts):
            return None

        matched = self._parse_first_match(line, parsed, ts, pod_ip)
        if not matched:
            return None
        return [matched[1]]

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

        if label in (REMOTE_PULL_LABEL, LINK_LABEL, *TIMED_LABELS):
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

        if label in (REMOTE_PULL_LABEL, LINK_LABEL, *TIMED_LABELS):
            return bool(self._target_trace_ids)

        return True

    def _parse_first_match(
        self,
        line: str,
        parsed: dict,
        ts,
        pod_ip: str,
    ) -> tuple[str, LogEntry] | None:
        """按固定优先级命中第一个关键字并立即解析；一行最多产出一个 entry。"""
        if "URMA_ELAPSED_TOTAL" in line:
            return self._parse_label(
                URMA_LABEL,
                self._parse_urma,
                parsed,
                ts,
                pod_ip,
                allow_trace_fallback=True,
                trace_source=line,
            )
        if "Remote get request" in line:
            return self._parse_label(
                REMOTE_PULL_LABEL,
                self._parse_remote_get,
                parsed,
                ts,
                pod_ip,
                allow_trace_fallback=True,
                trace_source=line,
            )
        if "Processing pull object[" in line:
            return self._parse_label(
                REMOTE_PULL_LABEL,
                self._parse_remote_pull,
                parsed,
                ts,
                pod_ip,
                allow_trace_fallback=True,
                trace_source=line,
            )
        if "elapsed ms:" in line:
            return self._parse_label(
                LINK_LABEL,
                self._parse_link,
                parsed,
                ts,
                pod_ip,
                allow_trace_fallback=True,
                trace_source=line,
            )
        if "Master query done" in line:
            return self._parse_label(
                QUERY_META_LABEL,
                self._parse_query_meta,
                parsed,
                ts,
                pod_ip,
                allow_trace_fallback=True,
                trace_source=line,
            )
        if "totalCost:" in line:
            return self._parse_label(
                SDK_PROCESS_LABEL,
                self._parse_sdk_process,
                parsed,
                ts,
                pod_ip,
                allow_trace_fallback=True,
                trace_source=line,
            )
        if "Worker to master rpc QueryMeta:" in line:
            return self._parse_label(
                SDK_RPC_LABEL,
                self._parse_sdk_rpc,
                parsed,
                ts,
                pod_ip,
                allow_trace_fallback=True,
                trace_source=line,
            )
        if "ProcessGetObjectRequest:" in line:
            return self._parse_label(
                LOCAL_WORKER_COST_LABEL,
                self._parse_local_worker_cost,
                parsed,
                ts,
                pod_ip,
                allow_trace_fallback=True,
                trace_source=line,
            )
        if "worker SafeObject WLock:" in line:
            return self._parse_label(
                LOCAL_WORKER_LOCK_LABEL,
                self._parse_local_worker_lock,
                parsed,
                ts,
                pod_ip,
                allow_trace_fallback=True,
                trace_source=line,
            )
        if "[Get/RemotePull] finish" in line:
            return self._parse_label(
                REMOTE_WORKER_COST_LABEL,
                self._parse_remote_worker_cost,
                parsed,
                ts,
                pod_ip,
                allow_trace_fallback=True,
                trace_source=line,
            )
        if "[Get] Remote done" in line:
            return self._parse_label(
                REMOTE_WORKER_RPC_LABEL,
                self._parse_remote_worker_rpc,
                parsed,
                ts,
                pod_ip,
                allow_trace_fallback=True,
                trace_source=line,
            )
        if "QueryMeta done" in line:
            return self._parse_label(
                MASTER_PROCESS_LABEL,
                self._parse_master_process,
                parsed,
                ts,
                pod_ip,
                allow_trace_fallback=True,
                trace_source=line,
            )
        if "[ZMQ_RPC_FRAMEWORK_SLOW]" in line:
            return self._parse_label(
                MASTER_RPC_LABEL,
                self._parse_master_rpc,
                parsed,
                ts,
                pod_ip,
                allow_trace_fallback=True,
                trace_source=line,
            )
        if "src" in line and "dst" in line:
            return self._parse_label(
                REMOTE_PULL_LABEL,
                self._parse_src_dst_fallback,
                parsed,
                ts,
                pod_ip,
                allow_trace_fallback=True,
                trace_source=line,
            )
        return None

    def _parse_label(
        self,
        label: str,
        parse_func,
        parsed: dict,
        ts,
        pod_ip: str,
        allow_trace_fallback: bool = False,
        trace_source: str = "",
    ) -> tuple[str, LogEntry] | None:
        if allow_trace_fallback:
            parsed["trace_id"] = self.resolve_trace_id(
                parsed["trace_id"],
                trace_source or parsed["msg"],
            )
        entry_pod_ip = parsed["pod_name"] if parsed["pod_name"] else pod_ip
        if not self._file_scope_may_allow(label, entry_pod_ip):
            return None
        if not self._scope_allows(label, parsed["trace_id"], entry_pod_ip):
            return None
        entry = parse_func(parsed, ts, pod_ip)
        if not entry:
            return None
        return label, entry

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

    def _parse_src_dst_fallback(self, parsed: dict, ts, pod_ip: str) -> LogEntry | None:
        msg = parsed["msg"]
        trace_id = parsed["trace_id"]
        if not trace_id:
            return None
        m = REMOTE_ENDPOINT_RE.search(msg)
        if not m:
            return None
        src_addr, dst_addr = (value.strip() for value in m.groups())
        if not (
            self._looks_like_ip_endpoint(src_addr)
            and self._looks_like_ip_endpoint(dst_addr)
        ):
            return None
        entry_pod_ip = parsed["pod_name"] if parsed["pod_name"] else pod_ip
        return LogEntry(
            timestamp=ts,
            elapsed_us=0,
            object_key="",
            request_size="",
            resp_msg=msg,
            src_addr=src_addr,
            dst_addr=dst_addr,
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

    def _parse_sdk_process(self, parsed: dict, ts, pod_ip: str) -> LogEntry | None:
        return self._parse_timed_entry(
            parsed, ts, pod_ip, SDK_PROCESS_RE, EntryType.SDK_PROCESS
        )

    def _parse_sdk_rpc(self, parsed: dict, ts, pod_ip: str) -> LogEntry | None:
        return self._parse_timed_entry(
            parsed, ts, pod_ip, SDK_RPC_RE, EntryType.SDK_RPC
        )

    def _parse_local_worker_cost(self, parsed: dict, ts, pod_ip: str) -> LogEntry | None:
        return self._parse_timed_entry(
            parsed, ts, pod_ip, LOCAL_WORKER_COST_RE, EntryType.LOCAL_WORKER_COST
        )

    def _parse_local_worker_lock(self, parsed: dict, ts, pod_ip: str) -> LogEntry | None:
        return self._parse_timed_entry(
            parsed, ts, pod_ip, LOCAL_WORKER_LOCK_RE, EntryType.LOCAL_WORKER_LOCK
        )

    def _parse_remote_worker_cost(self, parsed: dict, ts, pod_ip: str) -> LogEntry | None:
        return self._parse_timed_entry(
            parsed, ts, pod_ip, REMOTE_WORKER_COST_RE, EntryType.REMOTE_WORKER_COST
        )

    def _parse_remote_worker_rpc(self, parsed: dict, ts, pod_ip: str) -> LogEntry | None:
        return self._parse_timed_entry(
            parsed, ts, pod_ip, REMOTE_WORKER_RPC_RE, EntryType.REMOTE_WORKER_RPC
        )

    def _parse_master_process(self, parsed: dict, ts, pod_ip: str) -> LogEntry | None:
        return self._parse_timed_entry(
            parsed, ts, pod_ip, MASTER_PROCESS_RE, EntryType.MASTER_PROCESS
        )

    def _parse_master_rpc(self, parsed: dict, ts, pod_ip: str) -> LogEntry | None:
        return self._parse_timed_entry(
            parsed, ts, pod_ip, MASTER_RPC_RE, EntryType.MASTER_RPC, multiplier=1
        )

    def _parse_timed_entry(
        self,
        parsed: dict,
        ts,
        pod_ip: str,
        regex,
        entry_type: EntryType,
        multiplier: float = 1000,
    ) -> LogEntry | None:
        if not parsed["trace_id"]:
            return None
        m = regex.search(parsed["msg"])
        if not m:
            return None
        groups = m.groupdict()
        elapsed_raw = self._elapsed_value_from_match(m, groups)
        if elapsed_raw is None:
            return None
        timed_fields = self._timed_fields_from_groups(parsed["msg"], groups)
        return self._mk_timed_entry(
            parsed,
            ts,
            pod_ip,
            entry_type,
            float(elapsed_raw) * multiplier,
            **timed_fields,
        )

    @staticmethod
    def _elapsed_value_from_match(match, groups: dict[str, str | None]) -> str | None:
        for key in ("cost", "remote_processing_us"):
            value = groups.get(key)
            if value:
                return value
        for value in match.groups():
            if value and value.replace(".", "", 1).isdigit():
                return value
        return None

    @classmethod
    def _timed_fields_from_groups(
        cls,
        msg: str,
        groups: dict[str, str | None],
    ) -> dict[str, str | int | None]:
        src_addr = cls._clean_group(groups.get("src"))
        dst_addr = cls._clean_group(groups.get("dst"))
        if not src_addr or not dst_addr:
            endpoint_match = REMOTE_ENDPOINT_RE.search(msg)
            if endpoint_match:
                src_addr, dst_addr = (
                    value.strip() for value in endpoint_match.groups()
                )

        inflight_count = cls._optional_int(groups.get("inflight_remote_get"))
        resp_msg = cls._format_timed_resp_msg(groups)

        return {
            "object_key": cls._clean_group(groups.get("first_object_key")),
            "request_size": cls._clean_group(groups.get("payload_size")),
            "src_addr": src_addr,
            "dst_addr": dst_addr,
            "inflight_count": inflight_count,
            "resp_msg": resp_msg,
        }

    @staticmethod
    def _clean_group(value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        return value or None

    @staticmethod
    def _optional_int(value: str | None) -> int | None:
        if value is None:
            return None
        value = value.strip()
        if not value:
            return None
        try:
            return int(value)
        except ValueError:
            return None

    @classmethod
    def _format_timed_resp_msg(cls, groups: dict[str, str | None]) -> str | None:
        parts = []
        for key, value in groups.items():
            if key in _TIMED_RESP_EXCLUDED_FIELDS:
                continue
            cleaned = cls._clean_group(value)
            if not cleaned:
                continue
            parts.append(f"{key}={cleaned}")
        return ", ".join(parts) if parts else None

    @staticmethod
    def _mk_timed_entry(
        parsed: dict,
        ts,
        pod_ip: str,
        entry_type: EntryType,
        elapsed_us: float,
        object_key: str | None = None,
        request_size: str | None = None,
        src_addr: str | None = None,
        dst_addr: str | None = None,
        inflight_count: int | None = None,
        resp_msg: str | None = None,
    ) -> LogEntry:
        entry_pod_ip = parsed["pod_name"] if parsed["pod_name"] else pod_ip
        return LogEntry(
            timestamp=ts,
            elapsed_us=elapsed_us,
            pod_ip=entry_pod_ip,
            trace_id=parsed["trace_id"],
            entry_type=entry_type,
            cluster_name=parsed["cluster_name"] if parsed["cluster_name"] else None,
            object_key=object_key,
            request_size=request_size,
            resp_msg=resp_msg,
            src_addr=src_addr,
            dst_addr=dst_addr,
            inflight_count=inflight_count,
        )

    @staticmethod
    def _any_keyword_in(line: str) -> bool:
        for kw in ALL_KEYWORDS:
            if kw in line:
                return True
        return False

    @classmethod
    def _line_may_match(cls, line: str) -> bool:
        return cls._any_keyword_in(line) or ("src" in line and "dst" in line)

    @staticmethod
    def _looks_like_ip_endpoint(value: str) -> bool:
        return bool(_IP_ENDPOINT_RE.search(value))

    @staticmethod
    def _build_run(parts: list[str], plen: int) -> dict:
        return {
            "timestamp": parts[0].strip() if plen > 0 else "",
            "pod_name": parts[3].strip() if plen > 3 else "",
            "trace_id": parts[5].strip() if plen > 5 else "",
            "cluster_name": parts[6].strip() if plen > 6 else "",
            "msg": "|".join(parts[7:]).strip() if plen > 7 else "",
        }
