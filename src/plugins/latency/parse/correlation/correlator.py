import logging
import time
from collections import defaultdict
from abc import ABC, abstractmethod
from typing import Any

from latency.schemas.ds_log import (
    EntryType,
    LogEntry,
    CorrelationResult,
    TupleField,
)
from latency.parse.worker_info_parser import TIMED_LABELS

logger = logging.getLogger(__name__)

# 便捷别名（避免每次写 TupleField.XXX，提升可读性）
T_ELAPSED_US = TupleField.ELAPSED_US
T_TRACE_ID = TupleField.TRACE_ID
T_ENTRY_TYPE = TupleField.ENTRY_TYPE
T_POD_IP = TupleField.POD_IP
T_OPERATION = TupleField.OPERATION


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
            self.worker_by_trace = _group_by(
                self.worker_entries,
                lambda w: w[T_TRACE_ID],
                lambda w: bool(w[T_TRACE_ID]),
            )
            logger.info("  worker_by_trace built: %d groups", len(self.worker_by_trace))
        else:
            self.worker_by_trace = _group_by(
                self.worker_entries,
                lambda w: w.trace_id,
                lambda w: bool(w.trace_id),
            )
        
        # 关联规则统一为仅按 trace_id；保留空索引属性兼容测试/诊断代码。
        self.worker_by_trace_object = {}
        self.worker_index_by_id = {
            id(entry): idx
            for idx, entry in enumerate(self.worker_entries)
        }
        logger.info("  worker_index_by_id built: %d entries", len(self.worker_index_by_id))

        logger.info("  Building urma_by_trace index... (urma=%d)", len(self.urma_entries))
        if self._urma_is_tuple:
            self.urma_by_trace = _group_by(
                self.urma_entries,
                lambda u: u[T_TRACE_ID],
                lambda u: bool(u[T_TRACE_ID]),
            )
        else:
            self.urma_by_trace = _group_by(
                self.urma_entries,
                lambda u: u.trace_id,
                lambda u: bool(u.trace_id),
            )

        # 旧字段保留为空/trace 别名，避免其它兼容代码访问时报错。
        self.urma_by_dst_trace = self.urma_by_trace
        self.urma_by_trace_endpoint = {}
        logger.info("  urma_by_trace built: %d groups", len(self.urma_by_trace))

        logger.info("  Building link indexes... (link=%d)", len(self.link_entries))
        self.best_link_by_trace = {}
        if self._link_is_tuple:
            for link in self.link_entries:
                trace_id = link[T_TRACE_ID]
                if not trace_id:
                    continue
                current = self.best_link_by_trace.get(trace_id)
                if current is None or link[T_ELAPSED_US] > current[T_ELAPSED_US]:
                    self.best_link_by_trace[trace_id] = link
        else:
            for link in self.link_entries:
                if not link.trace_id:
                    continue
                current = self.best_link_by_trace.get(link.trace_id)
                if current is None or link.elapsed_us > current.elapsed_us:
                    self.best_link_by_trace[link.trace_id] = link
        self.best_link_by_pod_trace = {}
        logger.info("  link indexes built: by_trace=%d", len(self.best_link_by_trace))
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
        pulls_by_trace = self._build_pull_indexes(worker_indices)
        results = {}
        for i, w in self.index_manager.iter_worker_items(worker_indices):
            w_trace_id = w[5] if self._worker_is_tuple else w.trace_id
            candidates = pulls_by_trace.get(w_trace_id, [])
            if candidates:
                results[i] = candidates
        return results

    def _build_pull_indexes(
        self,
        worker_indices: set[int] | None,
    ) -> dict[str, list]:
        target_trace_ids = None
        if worker_indices is not None:
            target_trace_ids = {
                worker[5] if self._worker_is_tuple else worker.trace_id
                for _, worker in self.index_manager.iter_worker_items(worker_indices)
            }

        pulls_by_trace = defaultdict(list)
        for pull in self.index_manager.remote_pull_entries:
            pull_trace_id = pull[5] if self._pull_is_tuple else pull.trace_id
            if not pull_trace_id:
                continue
            if target_trace_ids is not None and pull_trace_id not in target_trace_ids:
                continue
            pulls_by_trace[pull_trace_id].append(pull)
        return dict(pulls_by_trace)


class WorkerLinkCorrelator(BaseCorrelator):
    def __init__(self, index_manager: IndexManager):
        super().__init__(index_manager)
        self._worker_is_tuple = index_manager._worker_is_tuple
    
    def correlate(self, worker_indices: set[int] | None = None) -> dict[int, list]:
        results = {}
        for i, w in self.index_manager.iter_worker_items(worker_indices):
            w_trace_id = w[5] if self._worker_is_tuple else w.trace_id
            best = self.index_manager.best_link_by_trace.get(w_trace_id)
            if best is not None:
                results[i] = [best]
        return results


class WorkerQueryMetaCorrelator(BaseCorrelator):
    def __init__(self, index_manager: IndexManager):
        super().__init__(index_manager)
        self._worker_is_tuple = index_manager._worker_is_tuple
        self._meta_is_tuple = index_manager.query_meta_entries and isinstance(index_manager.query_meta_entries[0], tuple)
    
    def correlate(self, worker_indices: set[int] | None = None) -> dict[int, list]:
        metas_by_trace = self._build_meta_indexes(worker_indices)
        results = {}
        for i, w in self.index_manager.iter_worker_items(worker_indices):
            w_trace_id = w[5] if self._worker_is_tuple else w.trace_id
            candidates = metas_by_trace.get(w_trace_id, [])
            if candidates:
                results[i] = candidates
        return results

    def _build_meta_indexes(
        self,
        worker_indices: set[int] | None,
    ) -> dict[str, list]:
        target_trace_ids = None
        if worker_indices is not None:
            target_trace_ids = {
                worker[5] if self._worker_is_tuple else worker.trace_id
                for _, worker in self.index_manager.iter_worker_items(worker_indices)
            }

        metas_by_trace = defaultdict(list)
        for meta in self.index_manager.query_meta_entries:
            meta_trace_id = meta[5] if self._meta_is_tuple else meta.trace_id
            if not meta_trace_id:
                continue
            if target_trace_ids is not None and meta_trace_id not in target_trace_ids:
                continue
            metas_by_trace[meta_trace_id].append(meta)
        
        return dict(metas_by_trace)


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
            matched = self.index_manager.urma_by_trace.get(w_trace_id, [])
            if matched:
                results[i] = matched
                worker_worker_results[i] = matched
        return results, worker_worker_results


class SdkWorkerCorrelator(BaseCorrelator):
    def __init__(self, index_manager: IndexManager, sdk_entries: list, time_window_ms: float = 100.0):
        super().__init__(index_manager)
        self.sdk_entries = sdk_entries
        self.time_window_ms = time_window_ms
        self._is_tuple = sdk_entries and isinstance(sdk_entries[0], tuple)
        self._worker_is_tuple = index_manager._worker_is_tuple

    def correlate(self) -> dict[int, object]:
        results = {}
        worker_by_trace_get = self.index_manager.worker_by_trace.get
        for i, sdk in enumerate(self.sdk_entries):
            trace_id = sdk[T_TRACE_ID] if self._is_tuple else sdk.trace_id
            candidates = worker_by_trace_get(trace_id)
            if not candidates:
                continue
            results[i] = candidates[0]
        return results


class SdkSetWorkerCorrelator(BaseCorrelator):
    """SDK SET 请求关联器：1条SDK SET → 2条Worker (CREATE + PUBLISH)"""

    def __init__(self, index_manager: IndexManager, sdk_entries: list):
        super().__init__(index_manager)
        self.sdk_entries = sdk_entries
        self._is_tuple = sdk_entries and isinstance(sdk_entries[0], tuple)
        self._worker_is_tuple = index_manager._worker_is_tuple

    def correlate(self) -> dict[int, tuple]:
        """返回 dict[sdk_idx, (worker_create, worker_publish)]"""
        results: dict[int, tuple] = {}
        worker_by_trace_get = self.index_manager.worker_by_trace.get

        for i, sdk in enumerate(self.sdk_entries):
            if self._is_tuple:
                operation = sdk[T_OPERATION]
                if operation != "DS_KV_CLIENT_SET":
                    continue
                trace_id = sdk[T_TRACE_ID]
            else:
                if sdk.operation != "DS_KV_CLIENT_SET":
                    continue
                trace_id = sdk.trace_id

            candidates = worker_by_trace_get(trace_id)
            if not candidates:
                continue

            worker_create = None
            worker_publish = None
            for w in candidates:
                if self._worker_is_tuple:
                    etype = w[T_ENTRY_TYPE]
                else:
                    etype = w.entry_type
                if etype == "WORKER_CREATE" or etype == EntryType.WORKER_CREATE:
                    if worker_create is None:
                        worker_create = w
                elif etype == "WORKER_PUBLISH" or etype == EntryType.WORKER_PUBLISH:
                    if worker_publish is None:
                        worker_publish = w

            if worker_create is not None and worker_publish is not None:
                results[i] = (worker_create, worker_publish)

        return results


class SdkUrmaCorrelator(BaseCorrelator):
    def __init__(self, index_manager: IndexManager, sdk_entries: list):
        super().__init__(index_manager)
        self.sdk_entries = sdk_entries
        self._is_tuple = sdk_entries and isinstance(sdk_entries[0], tuple)

    def correlate(self) -> dict[int, list[LogEntry]]:
        results = {}
        for i, sdk in enumerate(self.sdk_entries):
            trace_id = sdk[5] if self._is_tuple else sdk.trace_id
            if trace_id in self.index_manager.urma_by_trace:
                results[i] = self.index_manager.urma_by_trace[trace_id]
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
            reasons[i] = "No Urma entries found for this trace ID"
        return reasons


class WorkerTimedEntryCorrelator(BaseCorrelator):
    def __init__(
        self,
        index_manager: IndexManager,
        timed_entries: list,
        target_trace_ids: set[str] | None = None,
    ):
        super().__init__(index_manager)
        self.timed_entries = timed_entries
        self._timed_is_tuple = timed_entries and isinstance(timed_entries[0], tuple)
        self._worker_is_tuple = index_manager._worker_is_tuple
        timed_by_trace_type = defaultdict(list)
        
        if target_trace_ids is None:
            for entry in timed_entries:
                trace_id = entry[T_TRACE_ID] if self._timed_is_tuple else entry.trace_id
                if not trace_id:
                    continue
                entry_type = entry[T_ENTRY_TYPE] if self._timed_is_tuple else entry.entry_type
                timed_by_trace_type[(trace_id, entry_type)].append(entry)
        else:
            for entry in timed_entries:
                trace_id = entry[T_TRACE_ID] if self._timed_is_tuple else entry.trace_id
                if trace_id in target_trace_ids:
                    entry_type = entry[T_ENTRY_TYPE] if self._timed_is_tuple else entry.entry_type
                    timed_by_trace_type[(trace_id, entry_type)].append(entry)
        self.timed_by_trace_type = dict(timed_by_trace_type)

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
            values = self.timed_by_trace_type.get((w_trace_id, EntryType.SDK_PROCESS))
            if values:
                sdk_process_map[i] = values
            values = self.timed_by_trace_type.get((w_trace_id, EntryType.SDK_RPC))
            if values:
                sdk_rpc_map[i] = values
            values = self.timed_by_trace_type.get((w_trace_id, EntryType.LOCAL_WORKER_COST))
            if values:
                local_worker_cost_map[i] = values
            values = self.timed_by_trace_type.get((w_trace_id, EntryType.LOCAL_WORKER_LOCK))
            if values:
                local_worker_lock_map[i] = values
            values = self.timed_by_trace_type.get((w_trace_id, EntryType.REMOTE_WORKER_COST))
            if values:
                remote_worker_cost_map[i] = values
            values = self.timed_by_trace_type.get((w_trace_id, EntryType.REMOTE_WORKER_RPC))
            if values:
                remote_worker_rpc_map[i] = values
            values = self.timed_by_trace_type.get((w_trace_id, EntryType.MASTER_PROCESS))
            if values:
                master_process_map[i] = values
            values = self.timed_by_trace_type.get((w_trace_id, EntryType.MASTER_RPC))
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
        self.timed_entries: list = self._collect_timed_entries(parsed)
        
        self._worker_is_tuple = self.worker_entries and isinstance(self.worker_entries[0], tuple)
        self._urma_is_tuple = self.urma_entries and isinstance(self.urma_entries[0], tuple)
        self._link_is_tuple = self.link_entries and isinstance(self.link_entries[0], tuple)
        self._query_meta_is_tuple = self.query_meta_entries and isinstance(self.query_meta_entries[0], tuple)
        self._timed_is_tuple = self.timed_entries and isinstance(self.timed_entries[0], tuple)
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
            "Correlate index build: %.3fs (sdk=%d, worker=%d, urma=%d, pull=%d, link=%d, meta=%d, timed=%d)",
            self.index_build_seconds,
            len(self.sdk_entries),
            len(self.worker_entries),
            len(self.urma_entries),
            len(self.remote_pull_entries),
            len(self.link_entries),
            len(self.query_meta_entries),
            len(self.timed_entries),
        )

    @staticmethod
    def _collect_timed_entries(parsed: dict[str, list]) -> list:
        entries = []
        for label in TIMED_LABELS:
            entries.extend(parsed.get(label, []))
        return entries

    def _build_worker_pod_ips_map(
        self,
        worker_indices: set[int] | None,
        worker_urma_map: dict,
        worker_remote_pull_map: dict,
        worker_link_map: dict,
        worker_query_meta_map: dict,
        worker_sdk_process_map: dict,
        worker_sdk_rpc_map: dict,
        worker_local_worker_cost_map: dict,
        worker_local_worker_lock_map: dict,
        worker_remote_worker_cost_map: dict,
        worker_remote_worker_rpc_map: dict,
        worker_master_process_map: dict,
        worker_master_rpc_map: dict,
    ) -> dict[int, set[str]]:
        """为每个 worker_index 收集所有关联条目的 pod_ip。
        
        返回: worker_index -> set[pod_ip]
        """
        im = self.index_manager
        worker_pod_ips: dict[int, set[str]] = {}
        
        # 辅助函数:从 entry 中提取 pod_ip
        def get_pod_ip(entry) -> str | None:
            if isinstance(entry, tuple):
                return entry[T_POD_IP]
            return entry.pod_ip
        
        # 遍历所有 worker_indices
        for i, w in im.iter_worker_items(worker_indices):
            pod_ips = set()
            
            # Worker Access 自身的 pod_ip
            w_pod_ip = w[T_POD_IP] if isinstance(w, tuple) else w.pod_ip
            if w_pod_ip:
                pod_ips.add(w_pod_ip)
            
            # URMA 条目
            for entry in worker_urma_map.get(i, []):
                pod_ip = get_pod_ip(entry)
                if pod_ip:
                    pod_ips.add(pod_ip)
            
            # Remote Pull 条目
            for entry in worker_remote_pull_map.get(i, []):
                pod_ip = get_pod_ip(entry)
                if pod_ip:
                    pod_ips.add(pod_ip)
            
            # Link 条目
            for entry in worker_link_map.get(i, []):
                pod_ip = get_pod_ip(entry)
                if pod_ip:
                    pod_ips.add(pod_ip)
            
            # Query Meta 条目
            for entry in worker_query_meta_map.get(i, []):
                pod_ip = get_pod_ip(entry)
                if pod_ip:
                    pod_ips.add(pod_ip)
            
            # Timed 条目 (SDK Process, SDK RPC, Local Worker Cost, etc.)
            for entry in worker_sdk_process_map.get(i, []):
                pod_ip = get_pod_ip(entry)
                if pod_ip:
                    pod_ips.add(pod_ip)
            for entry in worker_sdk_rpc_map.get(i, []):
                pod_ip = get_pod_ip(entry)
                if pod_ip:
                    pod_ips.add(pod_ip)
            for entry in worker_local_worker_cost_map.get(i, []):
                pod_ip = get_pod_ip(entry)
                if pod_ip:
                    pod_ips.add(pod_ip)
            for entry in worker_local_worker_lock_map.get(i, []):
                pod_ip = get_pod_ip(entry)
                if pod_ip:
                    pod_ips.add(pod_ip)
            for entry in worker_remote_worker_cost_map.get(i, []):
                pod_ip = get_pod_ip(entry)
                if pod_ip:
                    pod_ips.add(pod_ip)
            for entry in worker_remote_worker_rpc_map.get(i, []):
                pod_ip = get_pod_ip(entry)
                if pod_ip:
                    pod_ips.add(pod_ip)
            for entry in worker_master_process_map.get(i, []):
                pod_ip = get_pod_ip(entry)
                if pod_ip:
                    pod_ips.add(pod_ip)
            for entry in worker_master_rpc_map.get(i, []):
                pod_ip = get_pod_ip(entry)
                if pod_ip:
                    pod_ips.add(pod_ip)
            
            if pod_ips:
                worker_pod_ips[i] = pod_ips
        
        return worker_pod_ips

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
        sdk_set_worker_map = self._timed_stage(
            "sdk_set_worker",
            lambda: SdkSetWorkerCorrelator(im, self.sdk_entries).correlate(),
        )
        worker_idx_map = self._timed_stage(
            "worker_idx",
            lambda: WorkerIdxCorrelator(im).correlate(sdk_worker_map),
        )
        # SDK 日志存在但一个 Worker 都未匹配时，不能把 Worker 关联范围收缩成
        # 空集合。此时结果构建会回退到 Worker 视角，需要完整的 URMA、
        # QueryMeta 和细分时延指标。
        worker_indices = set(worker_idx_map.values()) if sdk_worker_map else None
        target_trace_ids = None
        if worker_indices is not None:
            target_trace_ids = {
                im.worker_entries[idx][5]
                if im._worker_is_tuple
                else im.worker_entries[idx].trace_id
                for idx in worker_indices
            }
            self.worker_scope_count = len(worker_indices)
            self.worker_scope_pod_trace_count = len(target_trace_ids)
            logger.info(
                "Correlate worker scope: %d/%d workers, %d trace keys",
                len(worker_indices),
                len(self.worker_entries),
                len(target_trace_ids),
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
            "worker_timed_entries",
            lambda: WorkerTimedEntryCorrelator(
                im,
                self.timed_entries,
                target_trace_ids,
            ).correlate(worker_indices),
        )

        # 预构建 worker_index -> set[pod_ip] 索引，用于结果构建时高效收集所有关联 pod_ip
        worker_pod_ips_map = self._timed_stage(
            "worker_pod_ips",
            lambda: self._build_worker_pod_ips_map(
                worker_indices,
                worker_urma_map,
                worker_remote_pull_map,
                worker_link_map,
                worker_query_meta_map,
                worker_sdk_process_map,
                worker_sdk_rpc_map,
                worker_local_worker_cost_map,
                worker_local_worker_lock_map,
                worker_remote_worker_cost_map,
                worker_remote_worker_rpc_map,
                worker_master_process_map,
                worker_master_rpc_map,
            ),
        )

        return CorrelationResult(
            sdk_worker_map=sdk_worker_map,
            sdk_set_worker_map=sdk_set_worker_map,
            sdk_urma_index=im.urma_by_trace,
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
            worker_pod_ips_map=worker_pod_ips_map,
        )
