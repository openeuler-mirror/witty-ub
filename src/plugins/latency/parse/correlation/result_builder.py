import logging
from datetime import datetime, timedelta
from typing import Any, Optional

from latency.ENUM.ds_log import StatusCode
from latency.regex.kvcache_log import NOT_FOUND_RE, REMOTE_ENDPOINT_RE
from latency.schemas.ds_log import (
    LogEntry,
    CorrelationResult,
    TupleField,
)
from latency.schemas.log import (
    C2WLogParseResultDataclass,
    LogParseResultBatch,
    LogParseResultDataclass,
    SparseLogParseResultDataclass,
)

logger = logging.getLogger(__name__)

# 便捷别名
T_TIMESTAMP = TupleField.TIMESTAMP
T_ELAPSED_US = TupleField.ELAPSED_US
T_OBJECT_KEY = TupleField.OBJECT_KEY
T_TRACE_ID = TupleField.TRACE_ID
T_POD_IP = TupleField.POD_IP
T_STATUS_CODE = TupleField.STATUS_CODE
T_RESP_MSG = TupleField.RESP_MSG
T_CLUSTER_NAME = TupleField.CLUSTER_NAME
T_SRC_ADDR = TupleField.SRC_ADDR
T_DST_ADDR = TupleField.DST_ADDR
T_INFLIGHT_COUNT = TupleField.INFLIGHT_COUNT
T_LOG_ID = TupleField.LOG_ID
T_OPERATION = TupleField.OPERATION


class ParseResultBuilder:
    def __init__(
        self,
        sdk_entries: list[LogEntry],
        worker_entries: list[LogEntry],
        correlated: CorrelationResult,
        log_dir: str = "",
        log_file_id: str = "",
    ) -> None:
        self.sdk_entries = sdk_entries
        self.worker_entries = worker_entries
        self.correlated = correlated
        self.log_dir = log_dir
        self.log_file_id = log_file_id  # 数据库中的日志文件ID
        self.anomalous_count = 0
        self._worker_indices_by_trace: dict[str, list[int]] = {}
        for index, entry in enumerate(worker_entries):
            trace_id = entry[T_TRACE_ID] if isinstance(entry, tuple) else entry.trace_id
            if trace_id:
                self._worker_indices_by_trace.setdefault(trace_id, []).append(index)

    @staticmethod
    def _entry_value(entry, field: TupleField, attr: str):
        return entry[field] if isinstance(entry, tuple) else getattr(entry, attr)

    @staticmethod
    def _rpc_detail(entry) -> dict[str, int | None]:
        if entry is None:
            return {}
        raw = entry[T_RESP_MSG] if isinstance(entry, tuple) else entry.resp_msg
        fields: dict[str, int | None] = {}
        for part in (raw or "").split(","):
            key, sep, value = part.strip().partition("=")
            if sep and value.strip().isdigit():
                fields[key.strip()] = int(value.strip())
        return fields

    @classmethod
    def _rpc_metrics(cls, entry) -> dict[str, float | None]:
        detail = cls._rpc_detail(entry)
        e2e = detail.get("e2e_us")
        server_exec = detail.get("server_exec_us")
        network = detail.get("network_residual_us")
        total = max(0, e2e - server_exec) if e2e is not None and server_exec is not None else None
        framework = max(0, total - network) if total is not None and network is not None else None
        return {
            "total_us": float(total) if total is not None else None,
            "network_us": float(network) if network is not None else None,
            "framework_us": float(framework) if framework is not None else None,
            "server_exec_us": float(server_exec) if server_exec is not None else None,
            "e2e_us": float(e2e) if e2e is not None else None,
        }

    def _build_yuanrong_metrics(self, sdk_index: int, sdk, worker_index: int | None) -> dict[str, Any]:
        """逐项复刻 yuanrong_tool.build_seg 与 analyzer 的派生口径。"""
        trace_id = self._entry_value(sdk, T_TRACE_ID, "trace_id")
        operation = (self._entry_value(sdk, T_OPERATION, "operation") or "").upper()
        total = float(self._entry_value(sdk, T_ELAPSED_US, "elapsed_us") or 0)
        worker_indices = self._worker_indices_by_trace.get(trace_id, [])
        worker_access = [self.worker_entries[index] for index in worker_indices]
        worker_sum = sum(float(self._entry_value(e, T_ELAPSED_US, "elapsed_us") or 0) for e in worker_access)
        worker_max = max(
            (float(self._entry_value(e, T_ELAPSED_US, "elapsed_us") or 0) for e in worker_access),
            default=None,
        )

        client_rpc_entries = self.correlated.sdk_client_rpc_map.get(sdk_index, [])
        client_rpcs = [self._rpc_metrics(entry) for entry in client_rpc_entries]
        is_client_direct = len(client_rpcs) >= 2

        if worker_index is None and worker_indices:
            worker_index = worker_indices[0]
        worker_rpc_entries = self.correlated.worker_master_rpc_map.get(worker_index, []) if worker_index is not None else []
        master_entry = worker_rpc_entries[0] if worker_rpc_entries else None
        remote_entry = worker_rpc_entries[1] if len(worker_rpc_entries) > 1 else None
        if master_entry is not None and remote_entry is None and "SET" not in operation:
            has_meta = bool(
                worker_index is not None
                and self.correlated.worker_query_meta_map.get(worker_index)
            )
            if not has_meta:
                remote_entry, master_entry = master_entry, None

        master_rpc = self._rpc_metrics(master_entry)
        remote_rpc = self._rpc_metrics(remote_entry)
        empty_rpc = {"total_us": None, "network_us": None, "framework_us": None, "server_exec_us": None, "e2e_us": None}

        urma_entries = self.correlated.sdk_urma_index.get(trace_id, []) if "GET" in operation else []
        urma_processing_raw = max(
            (float(self._entry_value(e, T_ELAPSED_US, "elapsed_us") or 0) for e in urma_entries),
            default=None,
        )
        # yuanrong_tool 先取毫秒最大值，再执行 int(ms * 1000)。
        urma_processing = int(urma_processing_raw) if urma_processing_raw is not None else None
        urma_inflight = max(
            (self._entry_value(e, T_INFLIGHT_COUNT, "inflight_count") for e in urma_entries
             if self._entry_value(e, T_INFLIGHT_COUNT, "inflight_count") is not None),
            default=None,
        )

        sdk_rpc_e2e = sum(float(rpc.get("e2e_us") or 0) for rpc in client_rpcs)
        sdk_processing = None
        if client_rpcs and sdk_rpc_e2e > 0:
            sdk_processing = max(0.0, total - sdk_rpc_e2e)
        elif worker_access:
            sdk_processing = max(0.0, total - worker_sum)

        if is_client_direct:
            client_master = client_rpcs[0]
            client_remote = client_rpcs[1]
            remote_processing = client_remote.get("server_exec_us")
            remote_internal = (
                max(0.0, remote_processing - urma_processing)
                if remote_processing is not None and urma_processing is not None
                else None
            )
            sdk_rpc = master_rpc = remote_rpc = empty_rpc
            master_processing = client_master.get("server_exec_us")
            local_internal = None
            mode = "remote"
        else:
            sdk_rpc = client_rpcs[0] if client_rpcs else empty_rpc
            client_master = client_remote = empty_rpc
            master_processing = master_rpc.get("server_exec_us")
            remote_processing = remote_rpc.get("server_exec_us")
            remote_internal = (
                max(0.0, remote_processing - urma_processing)
                if remote_processing is not None and urma_processing is not None
                else None
            )
            local_internal = worker_sum if worker_access else None
            if local_internal is not None:
                if master_rpc.get("e2e_us") is not None:
                    local_internal = max(0.0, local_internal - float(master_rpc["e2e_us"]))
                if remote_rpc.get("e2e_us") is not None:
                    local_internal = max(0.0, local_internal - float(remote_rpc["e2e_us"]))
            mode = "local" if sdk_rpc.get("total_us") else "unknown"

        local_active = (
            local_internal
            if mode == "local" and (master_rpc.get("total_us") or remote_rpc.get("total_us"))
            else None
        )
        return {
            "total_latency_us": total,
            "request_mode": mode,
            "sdk_processing_us": sdk_processing,
            "master_processing_us": master_processing,
            "worker_access_latency_us": worker_max,
            "remote_worker_internal_us": remote_internal,
            "local_worker_internal_us": local_internal,
            "local_worker_internal_active_us": local_active,
            "sdk_rpc_network_us": sdk_rpc.get("network_us"),
            "sdk_rpc_framework_us": sdk_rpc.get("framework_us"),
            "sdk_rpc_total_us": sdk_rpc.get("total_us"),
            "master_rpc_network_us": master_rpc.get("network_us"),
            "master_rpc_framework_us": master_rpc.get("framework_us"),
            "master_rpc_total_us": master_rpc.get("total_us"),
            "remote_worker_rpc_network_us": remote_rpc.get("network_us"),
            "remote_worker_rpc_framework_us": remote_rpc.get("framework_us"),
            "remote_worker_rpc_total_us": remote_rpc.get("total_us"),
            "urma_processing_us": urma_processing,
            "urma_inflight_max": urma_inflight,
            "remote_worker_processing_us": remote_processing,
            "client_master_rpc_network_us": client_master.get("network_us"),
            "client_master_rpc_framework_us": client_master.get("framework_us"),
            "client_master_rpc_total_us": client_master.get("total_us"),
            "client_remote_rpc_network_us": client_remote.get("network_us"),
            "client_remote_rpc_framework_us": client_remote.get("framework_us"),
            "client_remote_rpc_total_us": client_remote.get("total_us"),
        }

    def build(
        self,
    ) -> list[LogParseResultDataclass | SparseLogParseResultDataclass]:
        self.anomalous_count = 0
        logger.info(f"开始构建解析结果 - SDK条目数: {len(self.sdk_entries)}, Worker条目数: {len(self.worker_entries)}")
        if self.sdk_entries:
            results = self._build_from_sdk_raw()
        else:
            results = self._build_from_worker()
        logger.info(f"解析结果构建完成 - 结果总数: {len(results)}, 异常数: {self.anomalous_count}")
        return results

    @staticmethod
    def _is_success_status(status_code: int, resp_msg: Optional[str]) -> bool:
        return status_code == StatusCode.OK and (
            not resp_msg or NOT_FOUND_RE.search(resp_msg) is None
        )

    @staticmethod
    def _format_timestamp(value: Optional[datetime]) -> Optional[str]:
        """格式化到毫秒，输出与原 strftime(... )[:-3] 保持一致。"""
        if value is None:
            return None
        return value.isoformat(sep=" ", timespec="milliseconds")[:23]

    @staticmethod
    def _format_failure_remark(source: str, status_code: int, resp_msg: Optional[str]) -> str:
        msg = resp_msg.strip() if resp_msg else ""
        if status_code == StatusCode.OK and NOT_FOUND_RE.search(msg):
            return f"{source} not found,{msg}"
        if msg:
            return f"{source} failed with status_code={status_code} resp_msg={msg}"
        return f"{source} failed with status_code={status_code}"

    @staticmethod
    def _merge_remark(current: Optional[str], extra: Optional[str]) -> str:
        if not current:
            return extra or ""
        if current == "OK":
            return f"OK;{extra}" if extra and extra != "OK" else current
        if not extra or extra == "OK":
            return current
        return f"{current};{extra}"

    @staticmethod
    def _format_latency(value: Optional[float]) -> Optional[float]:
        """格式化延迟值为3位小数，提高存储和传输效率"""
        return round(value, 3) if value is not None else None

    @staticmethod
    def _collect_pod_ips(
        sdk_pod_ip: Optional[str],
        worker_pod_ip: Optional[str],
        worker_pod_ips: Optional[set[str]] = None,
    ) -> Optional[list[str]]:
        """收集所有涉及的Pod IP地址
        
        Args:
            sdk_pod_ip: SDK侧的pod_ip
            worker_pod_ip: Worker Access侧的pod_ip
            worker_pod_ips: 预构建的worker关联的所有pod_ip集合(包括URMA/RemotePull/Link/QueryMeta/Timed等)
        """
        pod_ips = set()
        if sdk_pod_ip:
            pod_ips.add(sdk_pod_ip)
        if worker_pod_ip:
            pod_ips.add(worker_pod_ip)
        # 合并所有关联条目的pod_ip
        if worker_pod_ips:
            pod_ips.update(worker_pod_ips)
        return list(pod_ips) if pod_ips else None

    def _first_elapsed_us(self, entry_list: Optional[dict[int, list] | list], key: Optional[int]) -> Optional[float]:
        values = entry_list.get(key, []) if isinstance(entry_list, dict) else entry_list
        if not values:
            return None
        first = values[0]
        elapsed_us = first[T_ELAPSED_US] if isinstance(first, tuple) else first.elapsed_us
        return self._format_latency(elapsed_us / 1000)
    
    def _first_elapsed_us_raw(self, entry_list: Optional[dict[int, list]], key: Optional[int]) -> Optional[float]:
        """获取第一个条目的elapsed_us（不转换为ms）"""
        values = entry_list.get(key, []) if isinstance(entry_list, dict) else []
        if not values:
            return None
        first = values[0]
        return first[T_ELAPSED_US] if isinstance(first, tuple) else first.elapsed_us

    @staticmethod
    def _first_endpoint(values: Optional[list]) -> tuple[str, str] | None:
        if not values:
            return None
        for entry in values:
            if isinstance(entry, tuple):
                src_addr = entry[T_SRC_ADDR]
                dst_addr = entry[T_DST_ADDR]
            else:
                src_addr = entry.src_addr
                dst_addr = entry.dst_addr
            if src_addr and dst_addr:
                return src_addr, dst_addr
        return None

    def _resolve_urma_info(self, w_idx: Optional[int], sdk_success: bool, worker_success: bool) -> dict[str, Any]:
        urma_latency: Optional[float] = None
        urma_inflight_count: Optional[int] = None
        src_ip: Optional[str] = None
        dst_ip: Optional[str] = None
        urma_empty_reason: Optional[str] = None

        if w_idx is None:
            return dict(urma_latency=urma_latency, urma_inflight_count=urma_inflight_count,
                        src_ip=src_ip, dst_ip=dst_ip, urma_empty_reason=urma_empty_reason)

        # Fallback 1: 从 URMA 列表获取 IP 对
        urma_list = self.correlated.worker_urma_map.get(w_idx, [])
        if urma_list:
            first_urma = urma_list[0]
            if isinstance(first_urma, tuple):
                urma_latency = self._format_latency(first_urma[T_ELAPSED_US] / 1000)
                urma_inflight_count = first_urma[T_INFLIGHT_COUNT]
                src_ip = first_urma[T_SRC_ADDR]
                dst_ip = first_urma[T_DST_ADDR]
            else:
                urma_latency = self._format_latency(first_urma.elapsed_us / 1000)
                urma_inflight_count = first_urma.inflight_count
                src_ip = first_urma.src_addr
                dst_ip = first_urma.dst_addr

        # Fallback 2: 从 Remote Pull 列表获取 IP 对（无论成败都检查）
        if src_ip is None or dst_ip is None:
            remote_pulls = self.correlated.worker_remote_pull_map.get(w_idx)
            if remote_pulls:
                first_pull = remote_pulls[0]
                pull_src = first_pull[T_SRC_ADDR] if isinstance(first_pull, tuple) else first_pull.src_addr
                pull_dst = first_pull[T_DST_ADDR] if isinstance(first_pull, tuple) else first_pull.dst_addr
                if pull_src and pull_dst:
                    src_ip, dst_ip = pull_src, pull_dst

        # Fallback 3: 从 remote_worker_rpc_map / remote_worker_cost_map 获取 IP 对（无论成败都检查）
        if src_ip is None or dst_ip is None:
            endpoint = (
                self._first_endpoint(self.correlated.worker_remote_worker_rpc_map.get(w_idx))
                or self._first_endpoint(self.correlated.worker_remote_worker_cost_map.get(w_idx))
            )
            if endpoint:
                src_ip, dst_ip = endpoint

        # Fallback 4: 从 resp_msg 正则提取（所有来源都失败后的最后兜底）
        if src_ip is None or dst_ip is None:
            if isinstance(self.worker_entries[w_idx], tuple):
                msg = self.worker_entries[w_idx][T_RESP_MSG]
            else:
                msg = self.worker_entries[w_idx].resp_msg
            if msg:
                m = REMOTE_ENDPOINT_RE.search(msg)
                if m:
                    src_ip, dst_ip = (value.strip() for value in m.groups())

        if src_ip is None or dst_ip is None:
            urma_empty_reason = self.correlated.urma_empty_reasons.get(
                w_idx, "URMA fields empty: no matching URMA entry"
            )

        return dict(urma_latency=urma_latency, urma_inflight_count=urma_inflight_count,
                    src_ip=src_ip, dst_ip=dst_ip, urma_empty_reason=urma_empty_reason)

    def _build_unmatched_sdk_raw(
        self,
    ) -> list[LogParseResultDataclass | SparseLogParseResultDataclass]:
        """构建没有 Worker 匹配的 SDK 结果，保留可用的 SDK→URMA 指标。"""
        results: list[
            LogParseResultDataclass | SparseLogParseResultDataclass
        ] = LogParseResultBatch(
            len(self.sdk_entries),
            all_sparse=True,
        )
        shared_created_at = self._format_timestamp(datetime.now()) or ""
        correlated = self.correlated
        sdk_urma_map = correlated.sdk_urma_map
        sdk_urma_get = sdk_urma_map.get
        has_legacy_sdk_urma_map = bool(sdk_urma_map)
        sdk_urma_index = correlated.sdk_urma_index
        sdk_urma_index_get = sdk_urma_index.get
        has_sdk_urma_index = bool(sdk_urma_index)
        not_found_search = NOT_FOUND_RE.search
        format_failure_remark = self._format_failure_remark
        merge_remark = self._merge_remark
        sparse_result_type = SparseLogParseResultDataclass
        full_result_type = LogParseResultDataclass
        fixed_log_id = self.log_file_id
        fallback_log_dir = self.log_dir
        cached_second_start = None
        cached_second_end = None
        cached_second_prefix = ""
        one_second = timedelta(seconds=1)

        for i, sdk in enumerate(self.sdk_entries):
            sdk_status_code = sdk[T_STATUS_CODE]
            sdk_resp_msg = sdk[T_RESP_MSG]
            sdk_success = sdk_status_code == StatusCode.OK and (
                not sdk_resp_msg or not_found_search(sdk_resp_msg) is None
            )

            if has_legacy_sdk_urma_map:
                sdk_urma_values = sdk_urma_get(i)
                if not sdk_urma_values and has_sdk_urma_index:
                    sdk_urma_values = sdk_urma_index_get(
                        sdk[T_TRACE_ID]
                    )
            elif has_sdk_urma_index:
                sdk_urma_values = sdk_urma_index_get(
                    sdk[T_TRACE_ID]
                )
            else:
                sdk_urma_values = None
            src_ip = None
            dst_ip = None
            urma_inflight_count = None
            urma_total_latency = None
            if sdk_urma_values:
                first_sdk_urma = sdk_urma_values[0]
                sdk_urma_elapsed_us = (
                    first_sdk_urma[T_ELAPSED_US]
                    if isinstance(first_sdk_urma, tuple)
                    else first_sdk_urma.elapsed_us
                )
                c2w_urma_latency = round(sdk_urma_elapsed_us / 1000, 3)
                urma_total_latency = c2w_urma_latency
                urma_inflight_count = (
                    first_sdk_urma[T_INFLIGHT_COUNT]
                    if isinstance(first_sdk_urma, tuple)
                    else first_sdk_urma.inflight_count
                )
                endpoint = self._first_endpoint(sdk_urma_values)
                if endpoint:
                    src_ip, dst_ip = endpoint
            else:
                c2w_urma_latency = None

            remark = ""
            if not sdk_success:
                remark = format_failure_remark(
                    "SDK", sdk_status_code, sdk_resp_msg
                )
            if c2w_urma_latency is not None and c2w_urma_latency < 0:
                remark = merge_remark(
                    remark, "Client2WorkerTime(us) < 0"
                )
            is_anomalous = False

            sdk_timestamp = sdk[T_TIMESTAMP]
            if sdk_timestamp is None:
                timestamp = None
            elif sdk_timestamp.tzinfo is not None:
                timestamp = self._format_timestamp(sdk_timestamp)
            else:
                if (
                    cached_second_end is None
                    or sdk_timestamp < cached_second_start
                    or sdk_timestamp >= cached_second_end
                ):
                    cached_second_start = sdk_timestamp.replace(microsecond=0)
                    cached_second_end = cached_second_start + one_second
                    cached_second_prefix = sdk_timestamp.isoformat(
                        sep=" ", timespec="seconds"
                    )
                timestamp = (
                    cached_second_prefix
                    + "."
                    + str(sdk_timestamp.microsecond // 1000).zfill(3)
                )

            sdk_elapsed_us = sdk[T_ELAPSED_US]
            total_latency = (
                sdk_elapsed_us / 1000
                if isinstance(sdk_elapsed_us, int)
                else round(sdk_elapsed_us / 1000, 3)
            )
            log_id = fixed_log_id or sdk[T_LOG_ID] or fallback_log_dir
            if src_ip and dst_ip:
                results.all_sparse = False
                results[i] = full_result_type(
                    total_latency,
                    is_anomalous,
                    "",  # id
                    log_id,
                    "",  # aggregated_event_id
                    "",  # anomalous_event_id
                    self._collect_pod_ips(sdk[T_POD_IP], None, None),
                    src_ip,
                    dst_ip,
                    sdk[T_CLUSTER_NAME],
                    None,  # host
                    remark if is_anomalous else None,
                    None,  # anomaly_score
                    None,  # content
                    sdk[3],  # data_size
                    True,  # existed_status
                    None,  # offset
                    sdk[1],  # operation
                    remark or "OK",
                    sdk[T_TRACE_ID],
                    urma_inflight_count,
                    None,  # urma_link_latency
                    urma_total_latency,
                    None,  # c2w_latency
                    None,  # worker_query_meta_latency
                    c2w_urma_latency,
                    None,  # w2w_urma_latency
                    None,  # sdk_process
                    None,  # sdk_rpc
                    None,  # local_worker_cost
                    None,  # local_worker_lock
                    None,  # remote_worker_cost
                    None,  # remote_worker_rpc
                    None,  # master_process
                    None,  # master_rpc_total
                    None,  # create_latency
                    None,  # publish_latency
                    None,  # worker_total_latency
                    timestamp,
                    shared_created_at,
                )
            else:
                results[i] = sparse_result_type(
                    total_latency,
                    is_anomalous,
                    "",
                    log_id,
                    "",
                    "",
                    self._collect_pod_ips(sdk[T_POD_IP], None, None),
                    sdk[T_CLUSTER_NAME],
                    remark if is_anomalous else None,
                    sdk[3],
                    True,
                    sdk[1],
                    remark or "OK",
                    sdk[T_TRACE_ID],
                    c2w_urma_latency,
                    timestamp,
                    shared_created_at,
                )
        return results

    def _build_from_sdk_raw(
        self,
    ) -> list[
        LogParseResultDataclass
        | C2WLogParseResultDataclass
        | SparseLogParseResultDataclass
    ]:
        correlated = self.correlated
        # 即使没有 Worker Access，也必须继续构建：Client Direct 模式的两段
        # ZMQ RPC 本身即可形成完整的 yuanrong_tool 指标。

        results: list[
            LogParseResultDataclass
            | C2WLogParseResultDataclass
            | SparseLogParseResultDataclass
        ] = [None] * len(self.sdk_entries)  # type: ignore[list-item]
        shared_created_at = self._format_timestamp(datetime.now()) or ""

        sdk_worker_get = correlated.sdk_worker_map.get
        sdk_set_worker_get = correlated.sdk_set_worker_map.get
        worker_idx_get = correlated.worker_idx_map.get
        sdk_urma_map = correlated.sdk_urma_map
        sdk_urma_get = sdk_urma_map.get
        has_legacy_sdk_urma_map = bool(sdk_urma_map)
        sdk_urma_index = correlated.sdk_urma_index
        sdk_urma_index_get = sdk_urma_index.get
        has_sdk_urma_index = bool(sdk_urma_index)
        worker_urma_get = correlated.worker_urma_map.get
        worker_remote_pull_get = correlated.worker_remote_pull_map.get
        worker_worker_urma_get = correlated.worker_worker_urma_map.get
        worker_query_meta_get = correlated.worker_query_meta_map.get
        worker_link_get = correlated.worker_link_map.get
        worker_sdk_process_get = correlated.worker_sdk_process_map.get
        worker_sdk_rpc_get = correlated.worker_sdk_rpc_map.get
        worker_local_worker_cost_get = correlated.worker_local_worker_cost_map.get
        worker_local_worker_lock_get = correlated.worker_local_worker_lock_map.get
        worker_remote_worker_cost_get = correlated.worker_remote_worker_cost_map.get
        worker_remote_worker_rpc_get = correlated.worker_remote_worker_rpc_map.get
        worker_master_process_get = correlated.worker_master_process_map.get
        worker_master_rpc_get = correlated.worker_master_rpc_map.get
        urma_empty_reason_get = correlated.urma_empty_reasons.get

        format_failure_remark = self._format_failure_remark
        merge_remark = self._merge_remark
        not_found_search = NOT_FOUND_RE.search
        result_type = LogParseResultDataclass
        c2w_result_type = C2WLogParseResultDataclass
        sparse_result_type = SparseLogParseResultDataclass
        fixed_log_id = self.log_file_id
        fallback_log_dir = self.log_dir
        cached_second_start = None
        cached_second_end = None
        cached_second_prefix = ""
        one_second = timedelta(seconds=1)

        def first_elapsed_ms(values: Optional[list]) -> Optional[float]:
            if not values:
                return None
            first = values[0]
            elapsed_us = first[T_ELAPSED_US] if isinstance(first, tuple) else first.elapsed_us
            return round(elapsed_us / 1000, 3)

        def first_elapsed_raw(values: Optional[list]) -> Optional[float]:
            if not values:
                return None
            first = values[0]
            return first[T_ELAPSED_US] if isinstance(first, tuple) else first.elapsed_us

        def first_endpoint(values: Optional[list]) -> tuple[str, str] | None:
            if not values:
                return None
            for entry in values:
                if isinstance(entry, tuple):
                    src_addr = entry[T_SRC_ADDR]
                    dst_addr = entry[T_DST_ADDR]
                else:
                    src_addr = entry.src_addr
                    dst_addr = entry.dst_addr
                if src_addr and dst_addr:
                    return src_addr, dst_addr
            return None

        for i, sdk in enumerate(self.sdk_entries):
            worker = sdk_worker_get(i)
            sdk_status_code = sdk[T_STATUS_CODE]
            sdk_resp_msg = sdk[T_RESP_MSG]
            sdk_success = sdk_status_code == StatusCode.OK and (
                not sdk_resp_msg or not_found_search(sdk_resp_msg) is None
            )
            
            # worker 可能是 tuple 或 LogEntry
            if worker is not None:
                w_status_code = worker[T_STATUS_CODE] if isinstance(worker, tuple) else worker.status_code
                w_resp_msg = worker[T_RESP_MSG] if isinstance(worker, tuple) else worker.resp_msg
                w_elapsed_us = worker[T_ELAPSED_US] if isinstance(worker, tuple) else worker.elapsed_us
                w_cluster_name = worker[T_CLUSTER_NAME] if isinstance(worker, tuple) else worker.cluster_name
                w_pod_ip = worker[T_POD_IP] if isinstance(worker, tuple) else worker.pod_ip
                worker_success = w_status_code == StatusCode.OK and (
                    not w_resp_msg or not_found_search(w_resp_msg) is None
                )
            else:
                worker_success = True
                w_elapsed_us = None
                w_cluster_name = None
                w_pod_ip = None

            sdk_elapsed_us = sdk[T_ELAPSED_US]
            if w_elapsed_us is not None:
                c2w_elapsed_us = sdk_elapsed_us - w_elapsed_us
                c2w_latency = (
                    c2w_elapsed_us / 1000
                    if isinstance(c2w_elapsed_us, int)
                    else round(c2w_elapsed_us / 1000, 3)
                )
            else:
                c2w_latency = None
            w_idx = worker_idx_get(i) if worker is not None else None
            exact_metrics = self._build_yuanrong_metrics(i, sdk, w_idx)

            # SET 关联处理：1条SDK SET → (worker_create, worker_publish)
            set_workers = sdk_set_worker_get(i)
            create_latency = None
            publish_latency = None
            worker_total_latency = None
            if set_workers is not None:
                worker_create, worker_publish = set_workers
                wc_elapsed = worker_create[T_ELAPSED_US] if isinstance(worker_create, tuple) else worker_create.elapsed_us
                wp_elapsed = worker_publish[T_ELAPSED_US] if isinstance(worker_publish, tuple) else worker_publish.elapsed_us
                create_latency = round(wc_elapsed / 1000, 3)
                publish_latency = round(wp_elapsed / 1000, 3)
                worker_total_latency = round(create_latency + publish_latency, 3)

            if has_legacy_sdk_urma_map:
                sdk_urma_values = sdk_urma_get(i)
                if not sdk_urma_values and has_sdk_urma_index:
                    sdk_urma_values = sdk_urma_index_get(
                        sdk[T_TRACE_ID]
                    )
            elif has_sdk_urma_index:
                sdk_urma_values = sdk_urma_index_get(
                    sdk[T_TRACE_ID]
                )
            else:
                sdk_urma_values = None
            if sdk_urma_values:
                first_sdk_urma = sdk_urma_values[0]
                sdk_urma_elapsed_us = (
                    first_sdk_urma[T_ELAPSED_US]
                    if isinstance(first_sdk_urma, tuple)
                    else first_sdk_urma.elapsed_us
                )
                c2w_urma_latency = round(sdk_urma_elapsed_us / 1000, 3)
                if isinstance(first_sdk_urma, tuple):
                    sdk_urma_src = first_sdk_urma[T_SRC_ADDR]
                    sdk_urma_dst = first_sdk_urma[T_DST_ADDR]
                else:
                    sdk_urma_src = first_sdk_urma.src_addr
                    sdk_urma_dst = first_sdk_urma.dst_addr
            else:
                c2w_urma_latency = None
                sdk_urma_src = None
                sdk_urma_dst = None
            # 初始化所有 Worker 端变量为 None（SET 请求时 w_idx 为 None，不会进入 else 分支）
            query_meta_latency = None
            urma_link_latency = None
            w2w_urma_latency = None
            sdk_process = None
            sdk_rpc = None
            local_worker_cost = None
            local_worker_lock = None
            remote_worker_cost = None
            remote_worker_rpc = None
            master_process = None
            master_rpc_total = None
            urma_latency = None
            urma_inflight_count = None
            src_ip = sdk_urma_src
            dst_ip = sdk_urma_dst
            urma_empty_reason = None

            # SET 请求：统一使用 SDK → Worker 的 pod_ip 作为端点对。
            # GET 请求的 src/dst 是 URMA 传输层端点，SET 请求没有 URMA 传输层，
            # 其数据路径是 SDK → Worker（CREATE + PUBLISH），Worker → Master 是内部细节。
            # 直接用 pod_ip 保证所有 SET 请求端点语义一致，聚合结果才有意义。
            if set_workers is not None and not src_ip and not dst_ip:
                worker_create = set_workers[0]
                src_ip = sdk[T_POD_IP]
                dst_ip = worker_create[T_POD_IP] if isinstance(worker_create, tuple) else worker_create.pod_ip

            if w_idx is not None:
                query_meta_latency = first_elapsed_ms(worker_query_meta_get(w_idx))
                urma_link_latency = first_elapsed_ms(worker_link_get(w_idx))
                w2w_urma_latency = first_elapsed_ms(worker_worker_urma_get(w_idx))
                sdk_process = first_elapsed_ms(worker_sdk_process_get(w_idx))
                sdk_rpc = first_elapsed_ms(worker_sdk_rpc_get(w_idx))
                local_worker_cost = first_elapsed_ms(worker_local_worker_cost_get(w_idx))
                local_worker_lock = first_elapsed_ms(worker_local_worker_lock_get(w_idx))
                remote_worker_cost = first_elapsed_ms(worker_remote_worker_cost_get(w_idx))
                remote_worker_rpc = first_elapsed_ms(worker_remote_worker_rpc_get(w_idx))
                master_process = first_elapsed_ms(worker_master_process_get(w_idx))
                master_rpc_total = first_elapsed_raw(worker_master_rpc_get(w_idx))

                urma_info = self._resolve_urma_info(w_idx, sdk_success, worker_success)
                urma_latency = urma_info["urma_latency"]
                urma_inflight_count = urma_info["urma_inflight_count"]
                # Worker 端取到就用 Worker 端的，取不到就保留 SDK URMA 已有的值
                worker_src = urma_info["src_ip"]
                worker_dst = urma_info["dst_ip"]
                if worker_src and worker_dst:
                    src_ip, dst_ip = worker_src, worker_dst
                urma_empty_reason = urma_info["urma_empty_reason"]

            # 旧字段仅作为 API 兼容别名，数值统一从 yuanrong_tool 口径生成。
            def exact_ms(name: str) -> Optional[float]:
                value = exact_metrics.get(name)
                return round(float(value) / 1000, 3) if value is not None else None

            sdk_process = exact_ms("sdk_processing_us")
            sdk_rpc = exact_ms("sdk_rpc_total_us")
            local_worker_cost = exact_ms("local_worker_internal_us")
            local_worker_lock = None
            remote_worker_cost = exact_ms("remote_worker_internal_us")
            remote_worker_rpc = exact_ms("remote_worker_rpc_total_us")
            master_process = exact_ms("master_processing_us")
            master_rpc_total = exact_ms("master_rpc_total_us")
            query_meta_latency = master_process
            urma_latency = exact_ms("urma_processing_us")
            urma_inflight_count = exact_metrics.get("urma_inflight_max")

            remark = ""
            if not sdk_success:
                remark = merge_remark(
                    remark, format_failure_remark("SDK", sdk_status_code, sdk_resp_msg)
                )
            if worker is not None and not worker_success:
                remark = merge_remark(
                    remark, format_failure_remark("Worker", w_status_code, w_resp_msg)
                )
            if c2w_urma_latency is not None and c2w_urma_latency < 0:
                remark = merge_remark(remark, "Client2WorkerTime(us) < 0")
            if urma_empty_reason:
                remark = merge_remark(remark, urma_empty_reason)
            is_anomalous = False

            log_id = fixed_log_id or sdk[T_LOG_ID] or fallback_log_dir

            sdk_timestamp = sdk[T_TIMESTAMP]
            if sdk_timestamp is None:
                timestamp = None
            elif sdk_timestamp.tzinfo is not None:
                # 保持旧 strftime 语义：结果不携带时区后缀。
                timestamp = self._format_timestamp(sdk_timestamp)
            else:
                if (
                    cached_second_end is None
                    or sdk_timestamp < cached_second_start
                    or sdk_timestamp >= cached_second_end
                ):
                    cached_second_start = sdk_timestamp.replace(microsecond=0)
                    cached_second_end = cached_second_start + one_second
                    cached_second_prefix = sdk_timestamp.isoformat(
                        sep=" ", timespec="seconds"
                    )
                timestamp = (
                    cached_second_prefix
                    + "."
                    + str(sdk_timestamp.microsecond // 1000).zfill(3)
                )
            total_latency = (
                sdk_elapsed_us / 1000
                if isinstance(sdk_elapsed_us, int)
                else round(sdk_elapsed_us / 1000, 3)
            )

            # LogParseResultDataclass 的字段顺序由回归测试锁定。位置参数避免
            # 千万次构造时重复进行约 30 个关键字参数匹配，实测构造快约 2 倍。
            # 获取该 worker 关联的所有 pod_ip
            w_pod_ips = self.correlated.worker_pod_ips_map.get(w_idx) if w_idx is not None else None
            
            if False and w_idx is None and set_workers is None:
                results[i] = sparse_result_type(
                    total_latency,
                    is_anomalous,
                    "",  # id
                    log_id,
                    "",  # aggregated_event_id
                    "",  # anomalous_event_id
                    self._collect_pod_ips(sdk[T_POD_IP], w_pod_ip, w_pod_ips),
                    w_cluster_name if w_cluster_name else sdk[T_CLUSTER_NAME],
                    remark if is_anomalous else None,
                    sdk[3],  # data_size
                    True,  # existed_status
                    sdk[1],  # operation
                    remark or "OK",
                    sdk[T_TRACE_ID],
                    c2w_urma_latency,
                    timestamp,
                    shared_created_at,
                )
            elif False and (
                set_workers is None
                and src_ip is None
                and dst_ip is None
                and urma_inflight_count is None
                and urma_link_latency is None
                and urma_latency is None
                and query_meta_latency is None
                and c2w_urma_latency is None
                and w2w_urma_latency is None
                and sdk_process is None
                and sdk_rpc is None
                and local_worker_cost is None
                and local_worker_lock is None
                and remote_worker_cost is None
                and remote_worker_rpc is None
                and master_process is None
                and master_rpc_total is None
            ):
                results[i] = c2w_result_type(
                    total_latency,
                    is_anomalous,
                    "",  # id
                    log_id,
                    "",  # aggregated_event_id
                    "",  # anomalous_event_id
                    self._collect_pod_ips(sdk[T_POD_IP], w_pod_ip, w_pod_ips),
                    w_cluster_name if w_cluster_name else sdk[T_CLUSTER_NAME],
                    remark if is_anomalous else None,
                    sdk[3],  # data_size
                    True,  # existed_status
                    sdk[1],  # operation
                    remark or "OK",
                    sdk[T_TRACE_ID],
                    c2w_latency,
                    timestamp,
                    shared_created_at,
                )
            else:
                result = result_type(
                    total_latency,
                    is_anomalous,
                    "",  # id
                    log_id,
                    "",  # aggregated_event_id
                    "",  # anomalous_event_id
                    self._collect_pod_ips(sdk[T_POD_IP], w_pod_ip, w_pod_ips),
                    src_ip,
                    dst_ip,
                    w_cluster_name if w_cluster_name else sdk[T_CLUSTER_NAME],
                    None,  # host
                    remark if is_anomalous else None,
                    None,  # anomaly_score
                    None,  # content
                    sdk[3],  # data_size
                    True,  # existed_status
                    None,  # offset
                    sdk[1],  # operation
                    remark or "OK",
                    sdk[T_TRACE_ID],
                    urma_inflight_count,
                    urma_link_latency,
                    urma_latency,
                    c2w_latency,
                    query_meta_latency,
                    c2w_urma_latency,
                    w2w_urma_latency,
                    sdk_process,
                    sdk_rpc,
                    local_worker_cost,
                    local_worker_lock,
                    remote_worker_cost,
                    remote_worker_rpc,
                    master_process,
                    master_rpc_total,
                    create_latency,
                    publish_latency,
                    worker_total_latency,
                    timestamp,
                    shared_created_at,
                )
                for metric_name, metric_value in exact_metrics.items():
                    setattr(result, metric_name, metric_value)
                results[i] = result
        return results

    def _build_from_worker(self) -> list[LogParseResultDataclass]:
        results: list[LogParseResultDataclass] = []

        # 预生成共享的 created_at 时间戳，避免每条记录都调用 strftime
        shared_created_at = self._format_timestamp(datetime.now()) or ""

        for i, w in enumerate(self.worker_entries):
            w_status_code = w[T_STATUS_CODE] if isinstance(w, tuple) else w.status_code
            w_resp_msg = w[T_RESP_MSG] if isinstance(w, tuple) else w.resp_msg
            w_elapsed_us = w[T_ELAPSED_US] if isinstance(w, tuple) else w.elapsed_us
            w_log_id = w[T_LOG_ID] if isinstance(w, tuple) else w.log_id
            w_trace_id = w[T_TRACE_ID] if isinstance(w, tuple) else w.trace_id
            w_timestamp = w[T_TIMESTAMP] if isinstance(w, tuple) else w.timestamp
            w_pod_ip = w[T_POD_IP] if isinstance(w, tuple) else w.pod_ip
            w_cluster_name = w[T_CLUSTER_NAME] if isinstance(w, tuple) else w.cluster_name

            worker_success = self._is_success_status(w_status_code, w_resp_msg)
            urma_info = self._resolve_urma_info(i, True, worker_success)

            remark = ""
            if not worker_success:
                remark = self._format_failure_remark("Worker", w_status_code, w_resp_msg)
            is_anomalous = False

            # 获取各指标 - 使用 _first_elapsed_us 统一处理 tuple/LogEntry

            # 优先使用传入的 log_file_id（数据库中的日志文件ID），其次使用 entry.log_id，最后使用 log_dir
            log_id = self.log_file_id or w_log_id or self.log_dir
            
            # 获取该 worker 关联的所有 pod_ip
            w_pod_ips = self.correlated.worker_pod_ips_map.get(i)
            all_pod_ips = self._collect_pod_ips(None, w_pod_ip, w_pod_ips)

            # 使用 LogParseResultDataclass 替代 LogParseResultModel.model_construct
            results.append(LogParseResultDataclass(
                log_id=log_id,
                trace_id=w_trace_id,
                timestamp=w_timestamp.strftime("%Y-%m-%d %H:%M:%S.%f")[:-3] if w_timestamp else None,
                src_ip=urma_info["src_ip"],
                dst_ip=urma_info["dst_ip"],
                pod_ips=all_pod_ips,
                cluster_name=w_cluster_name,
                host=None,
                total_latency=self._format_latency(w_elapsed_us / 1000),
                worker_query_meta_latency=self._first_elapsed_us(self.correlated.worker_query_meta_map, i),
                urma_total_latency=urma_info["urma_latency"],
                urma_link_latency=self._first_elapsed_us(self.correlated.worker_link_map, i),
                urma_inflight_count=urma_info["urma_inflight_count"],
                w2w_urma_latency=self._first_elapsed_us(self.correlated.worker_worker_urma_map, i),
                sdk_process=self._first_elapsed_us(self.correlated.worker_sdk_process_map, i),
                sdk_rpc=self._first_elapsed_us(self.correlated.worker_sdk_rpc_map, i),
                local_worker_cost=self._first_elapsed_us(self.correlated.worker_local_worker_cost_map, i),
                local_worker_lock=self._first_elapsed_us(self.correlated.worker_local_worker_lock_map, i),
                remote_worker_cost=self._first_elapsed_us(self.correlated.worker_remote_worker_cost_map, i),
                remote_worker_rpc=self._first_elapsed_us(self.correlated.worker_remote_worker_rpc_map, i),
                master_process=self._first_elapsed_us(self.correlated.worker_master_process_map, i),
                master_rpc_total=self._first_elapsed_us_raw(self.correlated.worker_master_rpc_map, i),
                operation="DS_POSIX_GET",
                is_anomalous=is_anomalous,
                anomaly_reason=remark if is_anomalous else None,
                remark=remark or "OK",
                created_at=shared_created_at,
            ))
        return results
