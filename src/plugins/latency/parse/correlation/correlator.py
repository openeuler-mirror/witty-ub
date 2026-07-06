import logging
import time
from datetime import datetime, timedelta
from collections import defaultdict
from bisect import bisect_left, bisect_right
from abc import ABC, abstractmethod
from typing import Any

from latency.schemas.ds_log import (
    EntryType,
    LogEntry,
    CorrelationResult,
    TupleField,
)

logger = logging.getLogger(__name__)

# 便捷别名（避免每次写 TupleField.XXX，提升可读性）
T_TIMESTAMP = TupleField.TIMESTAMP
T_OPERATION = TupleField.OPERATION
T_ELAPSED_US = TupleField.ELAPSED_US
T_DATA_SIZE = TupleField.DATA_SIZE
T_OBJECT_KEY = TupleField.OBJECT_KEY
T_TRACE_ID = TupleField.TRACE_ID
T_POD_IP = TupleField.POD_IP
T_STATUS_CODE = TupleField.STATUS_CODE
T_RESP_MSG = TupleField.RESP_MSG
T_ENTRY_TYPE = TupleField.ENTRY_TYPE
T_CLUSTER_NAME = TupleField.CLUSTER_NAME
T_SRC_ADDR = TupleField.SRC_ADDR
T_DST_ADDR = TupleField.DST_ADDR
T_INFLIGHT_COUNT = TupleField.INFLIGHT_COUNT
T_REQUEST_SIZE = TupleField.REQUEST_SIZE
T_LOG_ID = TupleField.LOG_ID


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
        worker_entries: list,
        urma_entries: list,
        remote_pull_entries: list,
        link_entries: list,
        query_meta_entries: list,
    ):
        self.worker_entries = worker_entries
        self.urma_entries = urma_entries
        self.remote_pull_entries = remote_pull_entries
        self.link_entries = link_entries
        self.query_meta_entries = query_meta_entries
        
        self._worker_is_tuple = worker_entries and isinstance(worker_entries[0], tuple)
        self._urma_is_tuple = urma_entries and isinstance(urma_entries[0], tuple)
        self._link_is_tuple = link_entries and isinstance(link_entries[0], tuple)
        
        self._build_indexes()

    def _build_indexes(self):
        logger.info("IndexManager._build_indexes: start (worker=%d, urma=%d, link=%d, meta=%d)",
                    len(self.worker_entries), len(self.urma_entries), len(self.link_entries), len(self.query_meta_entries))
        
        if self._worker_is_tuple:
            logger.info("  Building worker_by_trace index...")
            self.worker_by_trace = _group_by(self.worker_entries, lambda w: w[T_TRACE_ID])
            logger.info("  worker_by_trace built: %d groups", len(self.worker_by_trace))
        else:
            self.worker_by_trace = _group_by(self.worker_entries, lambda w: w.trace_id)
        
        logger.info("  Building worker_by_trace_object index...")
        self.worker_by_trace_object = defaultdict(list)
        self.worker_ts_by_trace = {}
        multi_worker_trace_count = 0

        if self._worker_is_tuple:
            for trace_id, entries in self.worker_by_trace.items():
                if len(entries) == 1:
                    continue
                multi_worker_trace_count += 1
                entries.sort(key=lambda x: x[T_TIMESTAMP])
                self.worker_ts_by_trace[trace_id] = [
                    entry[T_TIMESTAMP] for entry in entries
                ]
                for entry in entries:
                    if entry[T_OBJECT_KEY]:
                        self.worker_by_trace_object[(trace_id, entry[T_OBJECT_KEY])].append(entry)
        else:
            for trace_id, entries in self.worker_by_trace.items():
                if len(entries) == 1:
                    continue
                multi_worker_trace_count += 1
                entries.sort(key=lambda x: x.timestamp)
                self.worker_ts_by_trace[trace_id] = [
                    entry.timestamp for entry in entries
                ]
                for entry in entries:
                    if entry.object_key:
                        self.worker_by_trace_object[(trace_id, entry.object_key)].append(entry)

        self.worker_by_trace_object = dict(self.worker_by_trace_object)
        logger.info(
            "  worker_by_trace_object built: %d groups (%d multi-entry traces)",
            len(self.worker_by_trace_object),
            multi_worker_trace_count,
        )
        self.worker_index_by_id = {
            id(entry): idx
            for idx, entry in enumerate(self.worker_entries)
        }
        logger.info("  worker_index_by_id built: %d entries", len(self.worker_index_by_id))

        logger.info("  Building urma indexes... (urma=%d)", len(self.urma_entries))
        self.urma_by_dst_trace = defaultdict(list)
        self.urma_by_trace_endpoint = defaultdict(list)
        self.urma_untraced_by_pod: dict[str, tuple[list, list[datetime] | None]] = {}
        self.urma_count_by_pod: dict[str, int] = defaultdict(int)
        self.traced_count_by_pod: dict[str, int] = defaultdict(int)
        self.untraced_count_by_pod: dict[str, int] = defaultdict(int)
        self.traced_count_by_pod_trace: dict[tuple[str, str], int] = defaultdict(int)

        if self._urma_is_tuple:
            for u in self.urma_entries:
                self.urma_count_by_pod[u[T_POD_IP]] += 1
                if u[T_TRACE_ID]:
                    self.urma_by_dst_trace[(u[T_POD_IP], u[T_TRACE_ID])].append(u)
                    self.urma_by_trace_endpoint[(u[T_TRACE_ID], u[T_SRC_ADDR], u[T_DST_ADDR])].append(u)
                    self.traced_count_by_pod[u[T_POD_IP]] += 1
                    self.traced_count_by_pod_trace[(u[T_POD_IP], u[T_TRACE_ID])] += 1
                else:
                    if u[T_POD_IP] not in self.urma_untraced_by_pod:
                        self.urma_untraced_by_pod[u[T_POD_IP]] = ([], None)
                    self.urma_untraced_by_pod[u[T_POD_IP]][0].append(u)
                    self.untraced_count_by_pod[u[T_POD_IP]] += 1
        else:
            for u in self.urma_entries:
                self.urma_count_by_pod[u.pod_ip] += 1
                if u.trace_id:
                    self.urma_by_dst_trace[(u.pod_ip, u.trace_id)].append(u)
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
            if self._urma_is_tuple:
                entries.sort(key=lambda x: x[T_TIMESTAMP])
                self.urma_untraced_by_pod[pod_ip] = (entries, [e[T_TIMESTAMP] for e in entries])
            else:
                entries.sort(key=lambda x: x.timestamp)
                self.urma_untraced_by_pod[pod_ip] = (entries, [e.timestamp for e in entries])

        for entries in self.urma_by_dst_trace.values():
            if self._urma_is_tuple:
                entries.sort(key=lambda x: x[0])
            else:
                entries.sort(key=lambda x: x.timestamp)

        self.urma_by_dst_trace = dict(self.urma_by_dst_trace)
        self.urma_by_trace_endpoint = dict(self.urma_by_trace_endpoint)
        logger.info("  urma indexes built: dst_trace=%d, endpoint=%d, untraced_pods=%d",
                    len(self.urma_by_dst_trace), len(self.urma_by_trace_endpoint), len(self.urma_untraced_by_pod))

        logger.info("  Building link indexes... (link=%d)", len(self.link_entries))
        self.best_link_by_trace = {}
        self.best_link_by_pod_trace = {}
        if self._link_is_tuple:
            for link in self.link_entries:
                trace_id = link[T_TRACE_ID]
                pod_trace = (link[T_POD_IP], trace_id)
                current = self.best_link_by_trace.get(trace_id)
                if current is None or link[T_ELAPSED_US] > current[T_ELAPSED_US]:
                    self.best_link_by_trace[trace_id] = link
                current = self.best_link_by_pod_trace.get(pod_trace)
                if current is None or link[T_ELAPSED_US] > current[T_ELAPSED_US]:
                    self.best_link_by_pod_trace[pod_trace] = link
        else:
            for link in self.link_entries:
                pod_trace = (link.pod_ip, link.trace_id)
                current = self.best_link_by_trace.get(link.trace_id)
                if current is None or link.elapsed_us > current.elapsed_us:
                    self.best_link_by_trace[link.trace_id] = link
                current = self.best_link_by_pod_trace.get(pod_trace)
                if current is None or link.elapsed_us > current.elapsed_us:
                    self.best_link_by_pod_trace[pod_trace] = link
        logger.info("  link indexes built: by_trace=%d, by_pod_trace=%d",
                    len(self.best_link_by_trace), len(self.best_link_by_pod_trace))
        logger.info("IndexManager._build_indexes: DONE")
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
    def __init__(self, index_manager: IndexManager):
        super().__init__(index_manager)
        self._worker_is_tuple = index_manager._worker_is_tuple
        self._pull_is_tuple = index_manager.remote_pull_entries and isinstance(index_manager.remote_pull_entries[0], tuple)
    
    def correlate(self, worker_indices: set[int] | None = None) -> dict[int, list]:
        pulls_by_trace, pulls_by_trace_object = self._build_pull_indexes(worker_indices)
        results = {}
        for i, w in self.index_manager.iter_worker_items(worker_indices):
            w_trace_id = w[5] if self._worker_is_tuple else w.trace_id
            w_object_key = w[4] if self._worker_is_tuple else w.object_key
            candidates = pulls_by_trace.get(w_trace_id, [])
            if not candidates:
                continue
            choices = candidates
            if w_object_key:
                choices = pulls_by_trace_object.get(
                    (w_trace_id, w_object_key),
                    candidates,
                )
            if choices:
                results[i] = choices
        return results

    def _build_pull_indexes(
        self,
        worker_indices: set[int] | None,
    ) -> tuple[dict[str, list], dict[tuple[str, str], list]]:
        target_trace_ids = None
        target_trace_objects = None
        if worker_indices is not None:
            target_trace_ids = set()
            target_trace_objects = set()
            for _, worker in self.index_manager.iter_worker_items(worker_indices):
                w_trace_id = worker[5] if self._worker_is_tuple else worker.trace_id
                w_object_key = worker[4] if self._worker_is_tuple else worker.object_key
                target_trace_ids.add(w_trace_id)
                if w_object_key:
                    target_trace_objects.add((w_trace_id, w_object_key))

        pulls_by_trace = defaultdict(list)
        pulls_by_trace_object = defaultdict(list)
        for pull in self.index_manager.remote_pull_entries:
            pull_trace_id = pull[5] if self._pull_is_tuple else pull.trace_id
            pull_object_key = pull[4] if self._pull_is_tuple else pull.object_key
            if target_trace_ids is not None and pull_trace_id not in target_trace_ids:
                continue
            pulls_by_trace[pull_trace_id].append(pull)
            if pull_trace_id and pull_object_key:
                key = (pull_trace_id, pull_object_key)
                if target_trace_objects is None or key in target_trace_objects:
                    pulls_by_trace_object[key].append(pull)
        return dict(pulls_by_trace), dict(pulls_by_trace_object)


class WorkerLinkCorrelator(BaseCorrelator):
    def __init__(self, index_manager: IndexManager):
        super().__init__(index_manager)
        self._worker_is_tuple = index_manager._worker_is_tuple
    
    def correlate(self, worker_indices: set[int] | None = None) -> dict[int, list]:
        results = {}
        for i, w in self.index_manager.iter_worker_items(worker_indices):
            w_trace_id = w[5] if self._worker_is_tuple else w.trace_id
            w_pod_ip = w[6] if self._worker_is_tuple else w.pod_ip
            best = self.index_manager.best_link_by_trace.get(w_trace_id)
            if best is None:
                best = self.index_manager.best_link_by_pod_trace.get((w_pod_ip, w_trace_id))
            if best is not None:
                results[i] = [best]
        return results


class WorkerQueryMetaCorrelator(BaseCorrelator):
    def __init__(self, index_manager: IndexManager):
        super().__init__(index_manager)
        self._worker_is_tuple = index_manager._worker_is_tuple
        self._meta_is_tuple = index_manager.query_meta_entries and isinstance(index_manager.query_meta_entries[0], tuple)
    
    def correlate(self, worker_indices: set[int] | None = None) -> dict[int, list]:
        metas_by_pod_trace, metas_ts_by_pod_trace = self._build_meta_indexes(worker_indices)
        results = {}
        for i, w in self.index_manager.iter_worker_items(worker_indices):
            w_pod_ip = w[6] if self._worker_is_tuple else w.pod_ip
            w_trace_id = w[5] if self._worker_is_tuple else w.trace_id
            w_timestamp = w[0] if self._worker_is_tuple else w.timestamp
            w_elapsed_us = w[2] if self._worker_is_tuple else w.elapsed_us
            key = (w_pod_ip, w_trace_id)
            candidates = metas_by_pod_trace.get(key, [])
            if not candidates:
                continue
            start = w_timestamp - timedelta(microseconds=w_elapsed_us)
            ts_list = metas_ts_by_pod_trace.get(key, [])
            lo = bisect_left(ts_list, start)
            hi = bisect_right(ts_list, w_timestamp)
            if lo < hi:
                best = candidates[hi - 1]
            else:
                pos = bisect_left(ts_list, w_timestamp)
                if pos <= 0:
                    best = candidates[0]
                elif pos >= len(candidates):
                    best = candidates[-1]
                else:
                    before = candidates[pos - 1]
                    after = candidates[pos]
                    before_ts = before[0] if self._meta_is_tuple else before.timestamp
                    after_ts = after[0] if self._meta_is_tuple else after.timestamp
                    before_dt = abs((before_ts - w_timestamp).total_seconds())
                    after_dt = abs((after_ts - w_timestamp).total_seconds())
                    best = before if before_dt <= after_dt else after
            results[i] = [best]
        return results

    def _build_meta_indexes(
        self,
        worker_indices: set[int] | None,
    ) -> tuple[dict[tuple[str, str], list], dict[tuple[str, str], list[datetime]]]:
        target_pod_traces = None
        if worker_indices is not None:
            target_pod_traces = {
                (worker[6], worker[5]) if self._worker_is_tuple else (worker.pod_ip, worker.trace_id)
                for _, worker in self.index_manager.iter_worker_items(worker_indices)
            }

        metas_by_pod_trace = defaultdict(list)
        for meta in self.index_manager.query_meta_entries:
            meta_pod_ip = meta[6] if self._meta_is_tuple else meta.pod_ip
            meta_trace_id = meta[5] if self._meta_is_tuple else meta.trace_id
            key = (meta_pod_ip, meta_trace_id)
            if target_pod_traces is not None and key not in target_pod_traces:
                continue
            metas_by_pod_trace[key].append(meta)

        for entries in metas_by_pod_trace.values():
            if self._meta_is_tuple:
                entries.sort(key=lambda x: x[0])
            else:
                entries.sort(key=lambda x: x.timestamp)

        metas_ts_by_pod_trace = {}
        for key, entries in metas_by_pod_trace.items():
            if self._meta_is_tuple:
                metas_ts_by_pod_trace[key] = [e[0] for e in entries]
            else:
                metas_ts_by_pod_trace[key] = [e.timestamp for e in entries]
        
        return dict(metas_by_pod_trace), metas_ts_by_pod_trace


class WorkerUrmaCorrelator(BaseCorrelator):
    def __init__(self, index_manager: IndexManager):
        super().__init__(index_manager)
        self.worker_entries = index_manager.worker_entries
        self._worker_is_tuple = index_manager._worker_is_tuple
        self._pull_is_tuple = index_manager.remote_pull_entries and isinstance(index_manager.remote_pull_entries[0], tuple)
        self._urma_is_tuple = index_manager._urma_is_tuple

    def correlate(
        self,
        worker_remote_pull_map: dict[int, list],
        worker_indices: set[int] | None = None,
    ) -> tuple[dict[int, list], dict[int, list]]:
        results = {}
        worker_worker_results = {}

        for i, w in self.index_manager.iter_worker_items(worker_indices):
            w_trace_id = w[5] if self._worker_is_tuple else w.trace_id
            w_pod_ip = w[6] if self._worker_is_tuple else w.pod_ip
            w_timestamp = w[0] if self._worker_is_tuple else w.timestamp
            w_elapsed_us = w[2] if self._worker_is_tuple else w.elapsed_us
            
            remote_matched = self._match_urma_by_remote_pull(
                self.index_manager.urma_by_trace_endpoint,
                w_trace_id,
                worker_remote_pull_map.get(i, []),
            )
            if remote_matched:
                worker_worker_results[i] = remote_matched

            untraced = []
            cached = self.index_manager.urma_untraced_by_pod.get(w_pod_ip)
            if cached:
                urma_list, urma_ts = cached
                w_end = w_timestamp + timedelta(microseconds=w_elapsed_us)
                lo = bisect_left(urma_ts, w_timestamp)
                hi = bisect_right(urma_ts, w_end)
                if lo < hi:
                    untraced = urma_list[lo:hi]

            matched = self._dedup_urma(remote_matched, untraced)
            if matched:
                results[i] = matched
        return results, worker_worker_results

    def _match_urma_by_remote_pull(
        self,
        urma_by_trace_endpoint: dict[tuple[str, str, str], list],
        trace_id: str,
        remote_pulls: list,
    ) -> list:
        if not remote_pulls:
            return []
        matches = []
        seen_endpoints = set()
        for pull in remote_pulls:
            pull_src_addr = pull[11] if self._pull_is_tuple else pull.src_addr
            pull_dst_addr = pull[12] if self._pull_is_tuple else pull.dst_addr
            if not pull_src_addr or not pull_dst_addr:
                continue
            for src, dst in ((pull_dst_addr, pull_src_addr), (pull_src_addr, pull_dst_addr)):
                endpoint_key = (trace_id, src, dst)
                if endpoint_key in seen_endpoints:
                    continue
                seen_endpoints.add(endpoint_key)
                matches.extend(urma_by_trace_endpoint.get(endpoint_key, []))
        if len(matches) > 1:
            if self._urma_is_tuple:
                matches.sort(key=lambda x: x[0])
            else:
                matches.sort(key=lambda x: x.timestamp)
        return matches

    def _dedup_urma(self, *groups: list) -> list:
        results = []
        seen = set()
        for group in groups:
            for u in group:
                if self._urma_is_tuple:
                    key = (u[5], u[11], u[12])
                else:
                    key = (u.trace_id, u.src_addr, u.dst_addr)
                if key in seen:
                    continue
                seen.add(key)
                results.append(u)
        return results


class SdkWorkerCorrelator(BaseCorrelator):
    def __init__(self, index_manager: IndexManager, sdk_entries: list, time_window_ms: float = 100.0):
        super().__init__(index_manager)
        self.sdk_entries = sdk_entries
        self.time_window_ms = time_window_ms
        self._is_tuple = sdk_entries and isinstance(sdk_entries[0], tuple)
        self._worker_is_tuple = index_manager._worker_is_tuple

    def correlate(self) -> dict[int, object]:
        window_delta = timedelta(milliseconds=self.time_window_ms)
        if not self._is_tuple:
            return self._correlate_objects(window_delta)

        results = {}
        worker_by_trace_get = self.index_manager.worker_by_trace.get
        worker_ts_by_trace = self.index_manager.worker_ts_by_trace
        worker_by_trace_object_get = self.index_manager.worker_by_trace_object.get
        for i, sdk in enumerate(self.sdk_entries):
            trace_id = sdk[T_TRACE_ID]
            candidates = worker_by_trace_get(trace_id)
            if not candidates:
                continue
            # 单候选最终无论时间窗是否命中都会走原有唯一 trace 回退，
            # 因此可直接返回，避免为绝大多数 trace 建时间戳列表和二分搜索。
            if len(candidates) == 1:
                results[i] = candidates[0]
                continue
            ts_list = worker_ts_by_trace[trace_id]
            sdk_ts = sdk[T_TIMESTAMP]
            pos = bisect_left(ts_list, sdk_ts)
            if self._worker_is_tuple:
                best = None
                best_delta = None
                for candidate_idx in (pos - 1, pos):
                    if candidate_idx < 0 or candidate_idx >= len(candidates):
                        continue
                    candidate = candidates[candidate_idx]
                    delta = abs(candidate[T_TIMESTAMP] - sdk_ts)
                    if delta <= window_delta and (
                        best_delta is None or delta < best_delta
                    ):
                        best = candidate
                        best_delta = delta
            else:
                best = self._nearest_worker_in_window(
                    candidates, pos, sdk_ts, window_delta
                )
            if best is not None:
                results[i] = best
                continue

            object_key = sdk[T_OBJECT_KEY]
            key_matched = (
                worker_by_trace_object_get((trace_id, object_key))
                if object_key
                else None
            )
            if key_matched is not None and len(key_matched) == 1:
                results[i] = key_matched[0]
        return results

    def _correlate_objects(self, window_delta: timedelta) -> dict[int, object]:
        results = {}
        worker_by_trace_get = self.index_manager.worker_by_trace.get
        worker_ts_by_trace = self.index_manager.worker_ts_by_trace
        worker_by_trace_object_get = self.index_manager.worker_by_trace_object.get
        for i, sdk in enumerate(self.sdk_entries):
            trace_id = sdk.trace_id
            candidates = worker_by_trace_get(trace_id)
            if not candidates:
                continue
            if len(candidates) == 1:
                results[i] = candidates[0]
                continue
            sdk_ts = sdk.timestamp
            pos = bisect_left(worker_ts_by_trace[trace_id], sdk_ts)
            best = self._nearest_worker_in_window(
                candidates, pos, sdk_ts, window_delta
            )
            if best is not None:
                results[i] = best
                continue
            object_key = sdk.object_key
            key_matched = (
                worker_by_trace_object_get((trace_id, object_key))
                if object_key
                else None
            )
            if key_matched is not None and len(key_matched) == 1:
                results[i] = key_matched[0]
        return results

    def _nearest_worker_in_window(
        self,
        candidates: list,
        pos: int,
        sdk_ts: datetime,
        window_delta: timedelta,
    ) -> object | None:
        best = None
        best_delta = None
        for idx in (pos - 1, pos):
            if idx < 0 or idx >= len(candidates):
                continue
            candidate = candidates[idx]
            candidate_ts = candidate[0] if self._worker_is_tuple else candidate.timestamp
            delta = abs(candidate_ts - sdk_ts)
            if delta <= window_delta and (best_delta is None or delta < best_delta):
                best = candidate
                best_delta = delta
        return best


class SdkUrmaCorrelator(BaseCorrelator):
    def __init__(self, index_manager: IndexManager, sdk_entries: list):
        super().__init__(index_manager)
        self.sdk_entries = sdk_entries
        self._is_tuple = sdk_entries and isinstance(sdk_entries[0], tuple)

    def correlate(self) -> dict[int, list[LogEntry]]:
        results = {}
        for i, sdk in enumerate(self.sdk_entries):
            pod_ip = sdk[6] if self._is_tuple else sdk.pod_ip
            trace_id = sdk[5] if self._is_tuple else sdk.trace_id
            key = (pod_ip, trace_id)
            if key in self.index_manager.urma_by_dst_trace:
                results[i] = self.index_manager.urma_by_dst_trace[key]
        return results


class WorkerIdxCorrelator(BaseCorrelator):
    def __init__(self, index_manager: IndexManager):
        super().__init__(index_manager)
        self.worker_entries = index_manager.worker_entries

    def correlate(self, sdk_worker_map: dict[int, object]) -> dict[int, int]:
        worker_to_idx = self.index_manager.worker_index_by_id
        return {sdk_i: worker_to_idx[id(w)] for sdk_i, w in sdk_worker_map.items() if w and id(w) in worker_to_idx}


class UrmaEmptyReasonCorrelator(BaseCorrelator):
    def __init__(self, index_manager: IndexManager):
        super().__init__(index_manager)
        self.worker_entries = index_manager.worker_entries
        self._worker_is_tuple = index_manager._worker_is_tuple

    def correlate(
        self,
        worker_urma_map: dict[int, list],
        worker_indices: set[int] | None = None,
    ) -> dict[int, str]:
        reasons = {}
        for i, w in self.index_manager.iter_worker_items(worker_indices):
            if i in worker_urma_map:
                continue
            w_pod_ip = w[6] if self._worker_is_tuple else w.pod_ip
            w_trace_id = w[5] if self._worker_is_tuple else w.trace_id
            if self.index_manager.urma_count_by_pod[w_pod_ip] == 0:
                reasons[i] = "No Urma entries found for this trace ID"
            elif self.index_manager.traced_count_by_pod_trace[(w_pod_ip, w_trace_id)] == 0 and self.index_manager.traced_count_by_pod[w_pod_ip] > 0:
                if self.index_manager.untraced_count_by_pod[w_pod_ip] > 0:
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
        metrics_entries: list,
        target_pod_traces: set[tuple[str, str]] | None = None,
    ):
        super().__init__(index_manager)
        self.metrics_entries = metrics_entries
        self._metrics_is_tuple = metrics_entries and isinstance(metrics_entries[0], tuple)
        self._worker_is_tuple = index_manager._worker_is_tuple
        metrics_by_pod_trace_type = defaultdict(list)
        target_trace_ids = {trace_id for _, trace_id in target_pod_traces} if target_pod_traces else None
        
        if target_trace_ids is None:
            for m in metrics_entries:
                m_trace_id = m[T_TRACE_ID] if self._metrics_is_tuple else m.trace_id
                m_entry_type = m[T_ENTRY_TYPE] if self._metrics_is_tuple else m.entry_type
                metrics_by_pod_trace_type[(m_trace_id, m_entry_type)].append(m)
        else:
            for m in metrics_entries:
                m_trace_id = m[T_TRACE_ID] if self._metrics_is_tuple else m.trace_id
                if m_trace_id in target_trace_ids:
                    m_entry_type = m[T_ENTRY_TYPE] if self._metrics_is_tuple else m.entry_type
                    metrics_by_pod_trace_type[(m_trace_id, m_entry_type)].append(m)
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
            w_trace_id = w[5] if self._worker_is_tuple else w.trace_id
            values = self.metrics_by_pod_trace_type.get((w_trace_id, EntryType.SDK_PROCESS))
            if values:
                sdk_process_map[i] = values
            values = self.metrics_by_pod_trace_type.get((w_trace_id, EntryType.SDK_RPC))
            if values:
                sdk_rpc_map[i] = values
            values = self.metrics_by_pod_trace_type.get((w_trace_id, EntryType.LOCAL_WORKER_COST))
            if values:
                local_worker_cost_map[i] = values
            values = self.metrics_by_pod_trace_type.get((w_trace_id, EntryType.LOCAL_WORKER_LOCK))
            if values:
                local_worker_lock_map[i] = values
            values = self.metrics_by_pod_trace_type.get((w_trace_id, EntryType.REMOTE_WORKER_COST))
            if values:
                remote_worker_cost_map[i] = values
            values = self.metrics_by_pod_trace_type.get((w_trace_id, EntryType.REMOTE_WORKER_RPC))
            if values:
                remote_worker_rpc_map[i] = values
            values = self.metrics_by_pod_trace_type.get((w_trace_id, EntryType.MASTER_PROCESS))
            if values:
                master_process_map[i] = values
            values = self.metrics_by_pod_trace_type.get((w_trace_id, EntryType.MASTER_RPC))
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
    def __init__(self, parsed: dict[str, list], time_window_ms: float = 100.0):
        sdk_raw = parsed.get("SDK access parse", [])
        self.sdk_entries: list = sdk_raw

        self.worker_entries: list = parsed.get("Worker access parse", [])
        self.urma_entries: list = parsed.get("Worker urma parse", [])
        self.remote_pull_entries: list = parsed.get("Worker remote pull parse", [])
        self.link_entries: list = parsed.get("Worker link parse", [])
        self.query_meta_entries: list = parsed.get("Worker query meta parse", [])
        self.metrics_entries: list = parsed.get("Worker metrics parse", [])
        
        self._worker_is_tuple = self.worker_entries and isinstance(self.worker_entries[0], tuple)
        self._urma_is_tuple = self.urma_entries and isinstance(self.urma_entries[0], tuple)
        self._link_is_tuple = self.link_entries and isinstance(self.link_entries[0], tuple)
        self._query_meta_is_tuple = self.query_meta_entries and isinstance(self.query_meta_entries[0], tuple)
        self._metrics_is_tuple = self.metrics_entries and isinstance(self.metrics_entries[0], tuple)
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
        worker_idx_map = self._timed_stage(
            "worker_idx",
            lambda: WorkerIdxCorrelator(im).correlate(sdk_worker_map),
        )
        worker_indices = set(worker_idx_map.values()) if self.sdk_entries else None
        target_pod_traces = None
        if worker_indices is not None:
            target_pod_traces = {
                (im.worker_entries[idx][6], im.worker_entries[idx][5])
                if im._worker_is_tuple
                else (im.worker_entries[idx].pod_ip, im.worker_entries[idx].trace_id)
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
            sdk_urma_index=im.urma_by_dst_trace,
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
