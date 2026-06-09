import logging
from datetime import datetime, timedelta
from collections import defaultdict
from bisect import bisect_left, bisect_right
from abc import ABC, abstractmethod
from typing import Any, Optional, Tuple

from latency.schemas.ds_log import (
    LogEntry,
    CorrelationResult,
)

logger = logging.getLogger(__name__)


def _group_by(entries, key_fn, filter_fn=None) -> dict:
    index: dict = {}
    for entry in entries:
        if filter_fn and not filter_fn(entry):
            continue
        k = key_fn(entry)
        index.setdefault(k, []).append(entry)
    return index


class IndexManager:
    def __init__(
        self,
        worker_entries: list[LogEntry],
        urma_entries: list[LogEntry],
        remote_pull_entries: list[LogEntry],
        link_entries: list[LogEntry],
        query_meta_entries: list[LogEntry],
    ):
        self.worker_entries = worker_entries
        self.urma_entries = urma_entries
        self.remote_pull_entries = remote_pull_entries
        self.link_entries = link_entries
        self.query_meta_entries = query_meta_entries
        self._build_indexes()

    def _build_indexes(self):
        self.worker_by_trace = _group_by(self.worker_entries, lambda w: w.trace_id)
        self.urma_traced_by_trace = _group_by(self.urma_entries, lambda u: u.trace_id, lambda u: u.trace_id)
        self.urma_traced_by_pod_trace = _group_by(self.urma_entries, lambda u: (u.pod_ip, u.trace_id), lambda u: u.trace_id)
        self.urma_by_dst_trace = _group_by(self.urma_entries, lambda u: (u.dst_addr, u.trace_id), lambda u: u.trace_id)
        self.pulls_by_trace = _group_by(self.remote_pull_entries, lambda p: p.trace_id)
        self.links_by_trace = _group_by(self.link_entries, lambda l: l.trace_id)
        self.links_by_pod_trace = _group_by(self.link_entries, lambda l: (l.pod_ip, l.trace_id))
        self.metas_by_pod_trace = _group_by(self.query_meta_entries, lambda m: (m.pod_ip, m.trace_id))

        self.urma_untraced_by_pod: dict[str, tuple[list[LogEntry], list[datetime] | None]] = {}
        for u in self.urma_entries:
            if u.trace_id:
                continue
            if u.pod_ip not in self.urma_untraced_by_pod:
                self.urma_untraced_by_pod[u.pod_ip] = ([], None)
            self.urma_untraced_by_pod[u.pod_ip][0].append(u)
        for pod_ip in self.urma_untraced_by_pod:
            entries = self.urma_untraced_by_pod[pod_ip][0]
            entries.sort(key=lambda x: x.timestamp)
            self.urma_untraced_by_pod[pod_ip] = (entries, [e.timestamp for e in entries])

        for entries in self.urma_traced_by_trace.values():
            entries.sort(key=lambda x: x.timestamp)
        for entries in self.urma_traced_by_pod_trace.values():
            entries.sort(key=lambda x: x.timestamp)
        for entries in self.urma_by_dst_trace.values():
            entries.sort(key=lambda x: x.timestamp)
        for entries in self.metas_by_pod_trace.values():
            entries.sort(key=lambda x: x.timestamp)

        self.urma_count_by_pod: dict[str, int] = defaultdict(int)
        self.traced_count_by_pod: dict[str, int] = defaultdict(int)
        self.untraced_count_by_pod: dict[str, int] = defaultdict(int)
        self.traced_count_by_pod_trace: dict[tuple[str, str], int] = defaultdict(int)
        for u in self.urma_entries:
            self.urma_count_by_pod[u.pod_ip] += 1
            if u.trace_id:
                self.traced_count_by_pod[u.pod_ip] += 1
                self.traced_count_by_pod_trace[(u.pod_ip, u.trace_id)] += 1
            else:
                self.untraced_count_by_pod[u.pod_ip] += 1


class BaseCorrelator(ABC):
    def __init__(self, index_manager: IndexManager):
        self.index_manager = index_manager

    @abstractmethod
    def correlate(self, **kwargs) -> Any:
        pass


class WorkerRemotePullCorrelator(BaseCorrelator):
    def correlate(self) -> dict[int, list[LogEntry]]:
        results = {}
        for i, w in enumerate(self.index_manager.worker_entries):
            candidates = self.index_manager.pulls_by_trace.get(w.trace_id, [])
            if not candidates:
                continue
            key_matched = [p for p in candidates if not w.object_key or p.object_key == w.object_key]
            choices = key_matched or candidates
            if choices:
                results[i] = choices
        return results


class WorkerLinkCorrelator(BaseCorrelator):
    def correlate(self) -> dict[int, list[LogEntry]]:
        results = {}
        for i, w in enumerate(self.index_manager.worker_entries):
            candidates = self.index_manager.links_by_trace.get(w.trace_id, [])
            if not candidates:
                candidates = self.index_manager.links_by_pod_trace.get((w.pod_ip, w.trace_id), [])
            if candidates:
                best = max(candidates, key=lambda x: x.elapsed_us)
                results[i] = [best]
        return results


class WorkerQueryMetaCorrelator(BaseCorrelator):
    def correlate(self) -> dict[int, list[LogEntry]]:
        results = {}
        for i, w in enumerate(self.index_manager.worker_entries):
            candidates = self.index_manager.metas_by_pod_trace.get((w.pod_ip, w.trace_id), [])
            if not candidates:
                continue
            start = w.timestamp - timedelta(microseconds=w.elapsed_us)
            in_range = [entry for entry in candidates if start <= entry.timestamp <= w.timestamp]
            choices = in_range or candidates
            best = min(choices, key=lambda x: abs(x.timestamp - w.timestamp).total_seconds())
            results[i] = [best]
        return results


class WorkerUrmaCorrelator(BaseCorrelator):
    def __init__(self, index_manager: IndexManager):
        super().__init__(index_manager)
        self.worker_entries = index_manager.worker_entries

    def correlate(self, worker_remote_pull_map: dict[int, list[LogEntry]]) -> tuple[dict[int, list[LogEntry]], dict[int, list[LogEntry]]]:
        results = {}
        worker_worker_results = {}

        for i, w in enumerate(self.worker_entries):
            remote_matched = self._match_urma_by_remote_pull(
                self.index_manager.urma_traced_by_trace.get(w.trace_id, []),
                worker_remote_pull_map.get(i, []),
            )
            if remote_matched:
                worker_worker_results[i] = remote_matched

            untraced = []
            cached = self.index_manager.urma_untraced_by_pod.get(w.pod_ip)
            if cached:
                urma_list, urma_ts = cached
                w_end = w.timestamp + timedelta(microseconds=w.elapsed_us)
                lo = bisect_left(urma_ts, w.timestamp)
                hi = bisect_right(urma_ts, w_end)
                if lo < hi:
                    untraced = urma_list[lo:hi]

            matched = self._dedup_urma(remote_matched, untraced)
            if matched:
                results[i] = matched
        return results, worker_worker_results

    @staticmethod
    def _match_urma_by_remote_pull(urma_candidates: list[LogEntry], remote_pulls: list[LogEntry]) -> list[LogEntry]:
        if not urma_candidates or not remote_pulls:
            return []
        write_endpoints = set()
        for pull in remote_pulls:
            if not pull.src_addr or not pull.dst_addr:
                continue
            write_endpoints.add((pull.dst_addr, pull.src_addr))
            write_endpoints.add((pull.src_addr, pull.dst_addr))
        if not write_endpoints:
            return []
        return [u for u in urma_candidates if (u.src_addr, u.dst_addr) in write_endpoints]

    @staticmethod
    def _dedup_urma(*groups: list[LogEntry]) -> list[LogEntry]:
        results = []
        seen = set()
        for group in groups:
            for u in group:
                key = (u.trace_id, u.src_addr, u.dst_addr)
                if key in seen:
                    continue
                seen.add(key)
                results.append(u)
        return results


class SdkWorkerCorrelator(BaseCorrelator):
    def __init__(self, index_manager: IndexManager, sdk_entries: list[LogEntry], time_window_ms: float = 100.0):
        super().__init__(index_manager)
        self.sdk_entries = sdk_entries
        self.time_window_ms = time_window_ms

    def correlate(self) -> dict[int, LogEntry]:
        window_us = self.time_window_ms * 1000
        results = {}
        for i, sdk in enumerate(self.sdk_entries):
            candidates = self.index_manager.worker_by_trace.get(sdk.trace_id, [])
            if not candidates:
                continue
            best = None
            best_dt = None
            for w in candidates:
                dt_us = abs((w.timestamp - sdk.timestamp).total_seconds()) * 1000000
                if 0 <= dt_us <= window_us:
                    if best_dt is None or dt_us < best_dt:
                        best = w
                        best_dt = dt_us
            if best is not None:
                results[i] = best
                continue
            key_matched = [w for w in candidates if w.object_key and w.object_key == sdk.object_key]
            if len(key_matched) == 1:
                results[i] = key_matched[0]
            elif len(candidates) == 1:
                results[i] = candidates[0]
        return results


class SdkUrmaCorrelator(BaseCorrelator):
    def __init__(self, index_manager: IndexManager, sdk_entries: list[LogEntry]):
        super().__init__(index_manager)
        self.sdk_entries = sdk_entries

    def correlate(self) -> dict[int, list[LogEntry]]:
        results = {}
        for i, sdk in enumerate(self.sdk_entries):
            key = (sdk.pod_ip, sdk.trace_id)
            if key in self.index_manager.urma_by_dst_trace:
                results[i] = self.index_manager.urma_by_dst_trace[key]
        return results


class WorkerIdxCorrelator(BaseCorrelator):
    def __init__(self, index_manager: IndexManager):
        super().__init__(index_manager)
        self.worker_entries = index_manager.worker_entries

    def correlate(self, sdk_worker_map: dict[int, LogEntry]) -> dict[int, int]:
        worker_to_idx = {id(w): i for i, w in enumerate(self.worker_entries)}
        return {sdk_i: worker_to_idx[id(w)] for sdk_i, w in sdk_worker_map.items() if w}


class UrmaEmptyReasonCorrelator(BaseCorrelator):
    def __init__(self, index_manager: IndexManager):
        super().__init__(index_manager)
        self.worker_entries = index_manager.worker_entries

    def correlate(self, worker_urma_map: dict[int, list[LogEntry]]) -> dict[int, str]:
        reasons = {}
        for i, w in enumerate(self.worker_entries):
            if i in worker_urma_map:
                continue
            if self.index_manager.urma_count_by_pod[w.pod_ip] == 0:
                reasons[i] = "No Urma entries found for this trace ID"
            elif self.index_manager.traced_count_by_pod_trace[(w.pod_ip, w.trace_id)] == 0 and self.index_manager.traced_count_by_pod[w.pod_ip] > 0:
                if self.index_manager.untraced_count_by_pod[w.pod_ip] > 0:
                    reasons[i] = "No Urma entries found for this trace ID with object key"
                else:
                    reasons[i] = "No Urma entries found for this trace ID"
            else:
                reasons[i] = "No Urma entries found for this trace ID"
        return reasons


class WorkerMetricsCorrelator(BaseCorrelator):
    def __init__(self, index_manager: IndexManager, metrics_entries: list[LogEntry]):
        super().__init__(index_manager)
        self.metrics_entries = metrics_entries
        self.metrics_by_pod_trace = _group_by(metrics_entries, lambda m: (m.pod_ip, m.trace_id))

    def correlate(self) -> tuple[dict, dict, dict, dict, dict, dict, dict, dict]:
        sdk_process_map = {}
        sdk_rpc_map = {}
        local_worker_cost_map = {}
        local_worker_lock_map = {}
        remote_worker_cost_map = {}
        remote_worker_rpc_map = {}
        master_process_map = {}
        master_rpc_map = {}

        from latency.schemas.ds_log import EntryType

        for i, w in enumerate(self.index_manager.worker_entries):
            key = (w.pod_ip, w.trace_id)
            candidates = self.metrics_by_pod_trace.get(key, [])
            
            if not candidates:
                continue

            for m in candidates:
                if m.entry_type == EntryType.SDK_PROCESS:
                    sdk_process_map.setdefault(i, []).append(m)
                elif m.entry_type == EntryType.SDK_RPC:
                    sdk_rpc_map.setdefault(i, []).append(m)
                elif m.entry_type == EntryType.LOCAL_WORKER_COST:
                    local_worker_cost_map.setdefault(i, []).append(m)
                elif m.entry_type == EntryType.LOCAL_WORKER_LOCK:
                    local_worker_lock_map.setdefault(i, []).append(m)
                elif m.entry_type == EntryType.REMOTE_WORKER_COST:
                    remote_worker_cost_map.setdefault(i, []).append(m)
                elif m.entry_type == EntryType.REMOTE_WORKER_RPC:
                    remote_worker_rpc_map.setdefault(i, []).append(m)
                elif m.entry_type == EntryType.MASTER_PROCESS:
                    master_process_map.setdefault(i, []).append(m)
                elif m.entry_type == EntryType.MASTER_RPC:
                    master_rpc_map.setdefault(i, []).append(m)

        return (
            sdk_process_map,
            sdk_rpc_map,
            local_worker_cost_map,
            local_worker_lock_map,
            remote_worker_cost_map,
            remote_worker_rpc_map,
            master_process_map,
            master_rpc_map,
        )


class LogCorrelator:
    def __init__(self, parsed: dict[str, list[LogEntry]], time_window_ms: float = 100.0):
        self.sdk_entries: list[LogEntry] = parsed.get("SDK access parse", [])
        self.worker_entries: list[LogEntry] = parsed.get("Worker access parse", [])
        self.urma_entries: list[LogEntry] = parsed.get("Worker urma parse", [])
        self.remote_pull_entries: list[LogEntry] = parsed.get("Worker remote pull parse", [])
        self.link_entries: list[LogEntry] = parsed.get("Worker link parse", [])
        self.query_meta_entries: list[LogEntry] = parsed.get("Worker query meta parse", [])
        # 提取新增指标的解析结果
        self.metrics_entries: list[LogEntry] = parsed.get("Worker metrics parse", [])
        self.time_window_ms = time_window_ms
        
        self.index_manager = IndexManager(
            worker_entries=self.worker_entries,
            urma_entries=self.urma_entries,
            remote_pull_entries=self.remote_pull_entries,
            link_entries=self.link_entries,
            query_meta_entries=self.query_meta_entries,
        )

    def correlate(self) -> CorrelationResult:
        worker_remote_pull_map = WorkerRemotePullCorrelator(self.index_manager).correlate()
        worker_link_map = WorkerLinkCorrelator(self.index_manager).correlate()
        worker_query_meta_map = WorkerQueryMetaCorrelator(self.index_manager).correlate()
        worker_urma_map, worker_worker_urma_map = WorkerUrmaCorrelator(self.index_manager).correlate(worker_remote_pull_map)
        sdk_worker_map = SdkWorkerCorrelator(self.index_manager, self.sdk_entries, self.time_window_ms).correlate()
        sdk_urma_map = SdkUrmaCorrelator(self.index_manager, self.sdk_entries).correlate()
        worker_idx_map = WorkerIdxCorrelator(self.index_manager).correlate(sdk_worker_map)
        urma_empty_reasons = UrmaEmptyReasonCorrelator(self.index_manager).correlate(worker_urma_map)
        
        # 关联新增指标
        (
            worker_sdk_process_map,
            worker_sdk_rpc_map,
            worker_local_worker_cost_map,
            worker_local_worker_lock_map,
            worker_remote_worker_cost_map,
            worker_remote_worker_rpc_map,
            worker_master_process_map,
            worker_master_rpc_map,
        ) = WorkerMetricsCorrelator(self.index_manager, self.metrics_entries).correlate()

        return CorrelationResult(
            sdk_worker_map=sdk_worker_map,
            sdk_urma_map=sdk_urma_map,
            worker_urma_map=worker_urma_map,
            worker_worker_urma_map=worker_worker_urma_map,
            worker_remote_pull_map=worker_remote_pull_map,
            worker_link_map=worker_link_map,
            worker_query_meta_map=worker_query_meta_map,
            worker_sdk_process_map=worker_sdk_process_map,
            worker_sdk_rpc_map=worker_sdk_rpc_map,
            worker_local_worker_cost_map=worker_local_worker_cost_map,
            worker_local_worker_lock_map=worker_local_worker_lock_map,
            worker_remote_worker_cost_map=worker_remote_worker_cost_map,
            worker_remote_worker_rpc_map=worker_remote_worker_rpc_map,
            worker_master_process_map=worker_master_process_map,
            worker_master_rpc_map=worker_master_rpc_map,
            worker_idx_map=worker_idx_map,
            urma_empty_reasons=urma_empty_reasons,
        )
