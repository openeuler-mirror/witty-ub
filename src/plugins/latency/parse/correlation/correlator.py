import logging
import time
from datetime import datetime, timedelta
from collections import defaultdict
from bisect import bisect_left, bisect_right
from abc import ABC, abstractmethod
from typing import Any, Optional, Tuple

from latency.schemas.ds_log import (
    EntryType,
    LogEntry,
    CorrelationResult,
)

logger = logging.getLogger(__name__)


def _group_by(entries, key_fn, filter_fn=None) -> dict:
    index: dict = defaultdict(list)
    for entry in entries:
        if filter_fn and not filter_fn(entry):
            continue
        k = key_fn(entry)
        index[k].append(entry)
    return dict(index)


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
        self.worker_by_trace_object = defaultdict(list)
        for trace_id, entries in self.worker_by_trace.items():
            entries.sort(key=lambda x: x.timestamp)
            for entry in entries:
                if entry.object_key:
                    self.worker_by_trace_object[(trace_id, entry.object_key)].append(entry)
        self.worker_ts_by_trace = {
            trace_id: [entry.timestamp for entry in entries]
            for trace_id, entries in self.worker_by_trace.items()
        }
        self.worker_by_trace_object = dict(self.worker_by_trace_object)
        self.worker_index_by_id = {
            id(entry): idx
            for idx, entry in enumerate(self.worker_entries)
        }

        self.urma_by_dst_trace = defaultdict(list)
        self.urma_by_trace_endpoint = defaultdict(list)
        self.urma_untraced_by_pod: dict[str, tuple[list[LogEntry], list[datetime] | None]] = {}
        self.urma_count_by_pod: dict[str, int] = defaultdict(int)
        self.traced_count_by_pod: dict[str, int] = defaultdict(int)
        self.untraced_count_by_pod: dict[str, int] = defaultdict(int)
        self.traced_count_by_pod_trace: dict[tuple[str, str], int] = defaultdict(int)

        for u in self.urma_entries:
            self.urma_count_by_pod[u.pod_ip] += 1
            if u.trace_id:
                self.urma_by_dst_trace[(u.dst_addr, u.trace_id)].append(u)
                self.urma_by_trace_endpoint[(u.trace_id, u.src_addr, u.dst_addr)].append(u)
                self.traced_count_by_pod[u.pod_ip] += 1
                self.traced_count_by_pod_trace[(u.pod_ip, u.trace_id)] += 1
            else:
                if u.pod_ip not in self.urma_untraced_by_pod:
                    self.urma_untraced_by_pod[u.pod_ip] = ([], None)
                self.urma_untraced_by_pod[u.pod_ip][0].append(u)
                self.untraced_count_by_pod[u.pod_ip] += 1

        for pod_ip in self.urma_untraced_by_pod:
            entries = self.urma_untraced_by_pod[pod_ip][0]
            entries.sort(key=lambda x: x.timestamp)
            self.urma_untraced_by_pod[pod_ip] = (entries, [e.timestamp for e in entries])

        for entries in self.urma_by_dst_trace.values():
            entries.sort(key=lambda x: x.timestamp)

        self.urma_by_dst_trace = dict(self.urma_by_dst_trace)
        self.urma_by_trace_endpoint = dict(self.urma_by_trace_endpoint)

        self.links_by_trace = _group_by(self.link_entries, lambda l: l.trace_id)
        self.links_by_pod_trace = _group_by(self.link_entries, lambda l: (l.pod_ip, l.trace_id))
        self.best_link_by_trace = {
            trace_id: max(entries, key=lambda x: x.elapsed_us)
            for trace_id, entries in self.links_by_trace.items()
        }
        self.best_link_by_pod_trace = {
            key: max(entries, key=lambda x: x.elapsed_us)
            for key, entries in self.links_by_pod_trace.items()
        }
    def iter_worker_items(self, worker_indices: set[int] | None = None):
        if worker_indices is None:
            return enumerate(self.worker_entries)
        return ((idx, self.worker_entries[idx]) for idx in worker_indices)


class BaseCorrelator(ABC):
    def __init__(self, index_manager: IndexManager):
        self.index_manager = index_manager

    @abstractmethod
    def correlate(self, **kwargs) -> Any:
        pass


class WorkerRemotePullCorrelator(BaseCorrelator):
    def correlate(self, worker_indices: set[int] | None = None) -> dict[int, list[LogEntry]]:
        pulls_by_trace, pulls_by_trace_object = self._build_pull_indexes(worker_indices)
        results = {}
        for i, w in self.index_manager.iter_worker_items(worker_indices):
            candidates = pulls_by_trace.get(w.trace_id, [])
            if not candidates:
                continue
            choices = candidates
            if w.object_key:
                choices = pulls_by_trace_object.get(
                    (w.trace_id, w.object_key),
                    candidates,
                )
            if choices:
                results[i] = choices
        return results

    def _build_pull_indexes(
        self,
        worker_indices: set[int] | None,
    ) -> tuple[dict[str, list[LogEntry]], dict[tuple[str, str], list[LogEntry]]]:
        target_trace_ids = None
        target_trace_objects = None
        if worker_indices is not None:
            target_trace_ids = set()
            target_trace_objects = set()
            for _, worker in self.index_manager.iter_worker_items(worker_indices):
                target_trace_ids.add(worker.trace_id)
                if worker.object_key:
                    target_trace_objects.add((worker.trace_id, worker.object_key))

        pulls_by_trace = defaultdict(list)
        pulls_by_trace_object = defaultdict(list)
        for pull in self.index_manager.remote_pull_entries:
            if target_trace_ids is not None and pull.trace_id not in target_trace_ids:
                continue
            pulls_by_trace[pull.trace_id].append(pull)
            if pull.trace_id and pull.object_key:
                key = (pull.trace_id, pull.object_key)
                if target_trace_objects is None or key in target_trace_objects:
                    pulls_by_trace_object[key].append(pull)
        return dict(pulls_by_trace), dict(pulls_by_trace_object)


class WorkerLinkCorrelator(BaseCorrelator):
    def correlate(self, worker_indices: set[int] | None = None) -> dict[int, list[LogEntry]]:
        results = {}
        for i, w in self.index_manager.iter_worker_items(worker_indices):
            best = self.index_manager.best_link_by_trace.get(w.trace_id)
            if best is None:
                best = self.index_manager.best_link_by_pod_trace.get((w.pod_ip, w.trace_id))
            if best is not None:
                results[i] = [best]
        return results


class WorkerQueryMetaCorrelator(BaseCorrelator):
    def correlate(self, worker_indices: set[int] | None = None) -> dict[int, list[LogEntry]]:
        metas_by_pod_trace, metas_ts_by_pod_trace = self._build_meta_indexes(worker_indices)
        results = {}
        for i, w in self.index_manager.iter_worker_items(worker_indices):
            key = (w.pod_ip, w.trace_id)
            candidates = metas_by_pod_trace.get(key, [])
            if not candidates:
                continue
            start = w.timestamp - timedelta(microseconds=w.elapsed_us)
            ts_list = metas_ts_by_pod_trace.get(key, [])
            lo = bisect_left(ts_list, start)
            hi = bisect_right(ts_list, w.timestamp)
            if lo < hi:
                best = candidates[hi - 1]
            else:
                pos = bisect_left(ts_list, w.timestamp)
                if pos <= 0:
                    best = candidates[0]
                elif pos >= len(candidates):
                    best = candidates[-1]
                else:
                    before = candidates[pos - 1]
                    after = candidates[pos]
                    before_dt = abs((before.timestamp - w.timestamp).total_seconds())
                    after_dt = abs((after.timestamp - w.timestamp).total_seconds())
                    best = before if before_dt <= after_dt else after
            results[i] = [best]
        return results

    def _build_meta_indexes(
        self,
        worker_indices: set[int] | None,
    ) -> tuple[dict[tuple[str, str], list[LogEntry]], dict[tuple[str, str], list[datetime]]]:
        target_pod_traces = None
        if worker_indices is not None:
            target_pod_traces = {
                (worker.pod_ip, worker.trace_id)
                for _, worker in self.index_manager.iter_worker_items(worker_indices)
            }

        metas_by_pod_trace = defaultdict(list)
        for meta in self.index_manager.query_meta_entries:
            key = (meta.pod_ip, meta.trace_id)
            if target_pod_traces is not None and key not in target_pod_traces:
                continue
            metas_by_pod_trace[key].append(meta)

        for entries in metas_by_pod_trace.values():
            entries.sort(key=lambda x: x.timestamp)
        metas_ts_by_pod_trace = {
            key: [entry.timestamp for entry in entries]
            for key, entries in metas_by_pod_trace.items()
        }
        return dict(metas_by_pod_trace), metas_ts_by_pod_trace


class WorkerUrmaCorrelator(BaseCorrelator):
    def __init__(self, index_manager: IndexManager):
        super().__init__(index_manager)
        self.worker_entries = index_manager.worker_entries

    def correlate(
        self,
        worker_remote_pull_map: dict[int, list[LogEntry]],
        worker_indices: set[int] | None = None,
    ) -> tuple[dict[int, list[LogEntry]], dict[int, list[LogEntry]]]:
        results = {}
        worker_worker_results = {}

        for i, w in self.index_manager.iter_worker_items(worker_indices):
            remote_matched = self._match_urma_by_remote_pull(
                self.index_manager.urma_by_trace_endpoint,
                w.trace_id,
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
    def _match_urma_by_remote_pull(
        urma_by_trace_endpoint: dict[tuple[str, str, str], list[LogEntry]],
        trace_id: str,
        remote_pulls: list[LogEntry],
    ) -> list[LogEntry]:
        if not remote_pulls:
            return []
        matches = []
        seen_endpoints = set()
        for pull in remote_pulls:
            if not pull.src_addr or not pull.dst_addr:
                continue
            for src, dst in ((pull.dst_addr, pull.src_addr), (pull.src_addr, pull.dst_addr)):
                endpoint_key = (trace_id, src, dst)
                if endpoint_key in seen_endpoints:
                    continue
                seen_endpoints.add(endpoint_key)
                matches.extend(urma_by_trace_endpoint.get(endpoint_key, []))
        if len(matches) > 1:
            matches.sort(key=lambda x: x.timestamp)
        return matches

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
        window_delta = timedelta(milliseconds=self.time_window_ms)
        results = {}
        for i, sdk in enumerate(self.sdk_entries):
            candidates = self.index_manager.worker_by_trace.get(sdk.trace_id, [])
            if not candidates:
                continue
            ts_list = self.index_manager.worker_ts_by_trace.get(sdk.trace_id, [])
            pos = bisect_left(ts_list, sdk.timestamp)
            best = self._nearest_worker_in_window(candidates, pos, sdk.timestamp, window_delta)
            if best is not None:
                results[i] = best
                continue

            key_matched = (
                self.index_manager.worker_by_trace_object.get((sdk.trace_id, sdk.object_key), [])
                if sdk.object_key
                else []
            )
            if len(key_matched) == 1:
                results[i] = key_matched[0]
            elif len(candidates) == 1:
                results[i] = candidates[0]
        return results

    @staticmethod
    def _nearest_worker_in_window(
        candidates: list[LogEntry],
        pos: int,
        sdk_ts: datetime,
        window_delta: timedelta,
    ) -> LogEntry | None:
        best = None
        best_delta = None
        for idx in (pos - 1, pos):
            if idx < 0 or idx >= len(candidates):
                continue
            candidate = candidates[idx]
            delta = abs(candidate.timestamp - sdk_ts)
            if delta <= window_delta and (best_delta is None or delta < best_delta):
                best = candidate
                best_delta = delta
        return best


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
        worker_to_idx = self.index_manager.worker_index_by_id
        return {sdk_i: worker_to_idx[id(w)] for sdk_i, w in sdk_worker_map.items() if w}


class UrmaEmptyReasonCorrelator(BaseCorrelator):
    def __init__(self, index_manager: IndexManager):
        super().__init__(index_manager)
        self.worker_entries = index_manager.worker_entries

    def correlate(
        self,
        worker_urma_map: dict[int, list[LogEntry]],
        worker_indices: set[int] | None = None,
    ) -> dict[int, str]:
        reasons = {}
        for i, w in self.index_manager.iter_worker_items(worker_indices):
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
    def __init__(
        self,
        index_manager: IndexManager,
        metrics_entries: list[LogEntry],
        target_pod_traces: set[tuple[str, str]] | None = None,
    ):
        super().__init__(index_manager)
        self.metrics_entries = metrics_entries
        metrics_by_pod_trace_type = defaultdict(list)
        if target_pod_traces is None:
            for m in metrics_entries:
                metrics_by_pod_trace_type[(m.pod_ip, m.trace_id, m.entry_type)].append(m)
        else:
            for m in metrics_entries:
                pod_trace = (m.pod_ip, m.trace_id)
                if pod_trace in target_pod_traces:
                    metrics_by_pod_trace_type[(m.pod_ip, m.trace_id, m.entry_type)].append(m)
        self.metrics_by_pod_trace_type = dict(metrics_by_pod_trace_type)

    def correlate(
        self,
        worker_indices: set[int] | None = None,
    ) -> tuple[dict, dict, dict, dict, dict, dict, dict, dict]:
        sdk_process_map = {}
        sdk_rpc_map = {}
        local_worker_cost_map = {}
        local_worker_lock_map = {}
        remote_worker_cost_map = {}
        remote_worker_rpc_map = {}
        master_process_map = {}
        master_rpc_map = {}

        for i, w in self.index_manager.iter_worker_items(worker_indices):
            pod_trace = (w.pod_ip, w.trace_id)
            values = self.metrics_by_pod_trace_type.get((*pod_trace, EntryType.SDK_PROCESS))
            if values:
                sdk_process_map[i] = values
            values = self.metrics_by_pod_trace_type.get((*pod_trace, EntryType.SDK_RPC))
            if values:
                sdk_rpc_map[i] = values
            values = self.metrics_by_pod_trace_type.get((*pod_trace, EntryType.LOCAL_WORKER_COST))
            if values:
                local_worker_cost_map[i] = values
            values = self.metrics_by_pod_trace_type.get((*pod_trace, EntryType.LOCAL_WORKER_LOCK))
            if values:
                local_worker_lock_map[i] = values
            values = self.metrics_by_pod_trace_type.get((*pod_trace, EntryType.REMOTE_WORKER_COST))
            if values:
                remote_worker_cost_map[i] = values
            values = self.metrics_by_pod_trace_type.get((*pod_trace, EntryType.REMOTE_WORKER_RPC))
            if values:
                remote_worker_rpc_map[i] = values
            values = self.metrics_by_pod_trace_type.get((*pod_trace, EntryType.MASTER_PROCESS))
            if values:
                master_process_map[i] = values
            values = self.metrics_by_pod_trace_type.get((*pod_trace, EntryType.MASTER_RPC))
            if values:
                master_rpc_map[i] = values

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

        index_start = time.perf_counter()
        self.index_manager = IndexManager(
            worker_entries=self.worker_entries,
            urma_entries=self.urma_entries,
            remote_pull_entries=self.remote_pull_entries,
            link_entries=self.link_entries,
            query_meta_entries=self.query_meta_entries,
        )
        self.index_build_seconds = time.perf_counter() - index_start
        self.stage_timings: list[tuple[str, float]] = []
        self.worker_scope_count = len(self.worker_entries)
        self.worker_scope_pod_trace_count = 0
        logger.info(
            "Correlate index build: %.3fs (sdk=%d, worker=%d, urma=%d, pull=%d, link=%d, meta=%d, metrics=%d)",
            self.index_build_seconds,
            len(self.sdk_entries),
            len(self.worker_entries),
            len(self.urma_entries),
            len(self.remote_pull_entries),
            len(self.link_entries),
            len(self.query_meta_entries),
            len(self.metrics_entries),
        )

    def _timed_stage(self, stage_name: str, func):
        start = time.perf_counter()
        result = func()
        elapsed = time.perf_counter() - start
        self.stage_timings.append((stage_name, elapsed))
        logger.info("Correlate stage %-20s %.3fs", stage_name + ":", elapsed)
        return result

    def correlate(self) -> CorrelationResult:
        im = self.index_manager

        sdk_worker_map = self._timed_stage(
            "sdk_worker",
            lambda: SdkWorkerCorrelator(im, self.sdk_entries, self.time_window_ms).correlate(),
        )
        sdk_urma_map = self._timed_stage(
            "sdk_urma",
            lambda: SdkUrmaCorrelator(im, self.sdk_entries).correlate(),
        )
        worker_idx_map = self._timed_stage(
            "worker_idx",
            lambda: WorkerIdxCorrelator(im).correlate(sdk_worker_map),
        )
        worker_indices = set(worker_idx_map.values()) if self.sdk_entries else None
        target_pod_traces = None
        if worker_indices is not None:
            target_pod_traces = {
                (im.worker_entries[idx].pod_ip, im.worker_entries[idx].trace_id)
                for idx in worker_indices
            }
            self.worker_scope_count = len(worker_indices)
            self.worker_scope_pod_trace_count = len(target_pod_traces)
            logger.info(
                "Correlate worker scope: %d/%d workers, %d pod-trace keys",
                len(worker_indices),
                len(self.worker_entries),
                len(target_pod_traces),
            )

        worker_remote_pull_map = self._timed_stage(
            "worker_remote_pull",
            lambda: WorkerRemotePullCorrelator(im).correlate(worker_indices),
        )
        worker_link_map = self._timed_stage(
            "worker_link",
            lambda: WorkerLinkCorrelator(im).correlate(worker_indices),
        )
        worker_query_meta_map = self._timed_stage(
            "worker_query_meta",
            lambda: WorkerQueryMetaCorrelator(im).correlate(worker_indices),
        )
        worker_urma_map, worker_worker_urma_map = self._timed_stage(
            "worker_urma",
            lambda: WorkerUrmaCorrelator(im).correlate(worker_remote_pull_map, worker_indices),
        )
        urma_empty_reasons = self._timed_stage(
            "urma_empty_reasons",
            lambda: UrmaEmptyReasonCorrelator(im).correlate(worker_urma_map, worker_indices),
        )

        (
            worker_sdk_process_map,
            worker_sdk_rpc_map,
            worker_local_worker_cost_map,
            worker_local_worker_lock_map,
            worker_remote_worker_cost_map,
            worker_remote_worker_rpc_map,
            worker_master_process_map,
            worker_master_rpc_map,
        ) = self._timed_stage(
            "worker_metrics",
            lambda: WorkerMetricsCorrelator(
                im,
                self.metrics_entries,
                target_pod_traces,
            ).correlate(worker_indices),
        )

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
