import logging
from datetime import datetime, timedelta
from typing import Any, Optional

from latency.ENUM.ds_log import StatusCode
from latency.regex.kvcache_log import NOT_FOUND_RE
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

    def build(
        self,
    ) -> list[LogParseResultDataclass | SparseLogParseResultDataclass]:
        self.anomalous_count = 0
        if self.sdk_entries:
            return self._build_from_sdk_raw()
        return self._build_from_worker()

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
        elif sdk_success and worker_success:
            remote_pulls = self.correlated.worker_remote_pull_map.get(w_idx, [])
            if remote_pulls:
                first_pull = remote_pulls[0]
                src_ip = first_pull[T_SRC_ADDR] if isinstance(first_pull, tuple) else first_pull.src_addr
                dst_ip = first_pull[T_DST_ADDR] if isinstance(first_pull, tuple) else first_pull.dst_addr
            else:
                endpoint = (
                    self._first_endpoint(self.correlated.worker_remote_worker_rpc_map.get(w_idx))
                    or self._first_endpoint(self.correlated.worker_remote_worker_cost_map.get(w_idx))
                )
                if endpoint:
                    src_ip, dst_ip = endpoint
        else:
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
                        (sdk[T_POD_IP], sdk[T_TRACE_ID])
                    )
            elif has_sdk_urma_index:
                sdk_urma_values = sdk_urma_index_get(
                    (sdk[T_POD_IP], sdk[T_TRACE_ID])
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
            is_anomalous = bool(remark) and remark != "OK"
            if is_anomalous:
                self.anomalous_count += 1

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
                    sdk[T_POD_IP],
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
                    sdk[T_POD_IP],
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
        if not correlated.sdk_worker_map:
            return self._build_unmatched_sdk_raw()

        results: list[
            LogParseResultDataclass
            | C2WLogParseResultDataclass
            | SparseLogParseResultDataclass
        ] = [None] * len(self.sdk_entries)  # type: ignore[list-item]
        shared_created_at = self._format_timestamp(datetime.now()) or ""

        sdk_worker_get = correlated.sdk_worker_map.get
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
                worker_success = w_status_code == StatusCode.OK and (
                    not w_resp_msg or not_found_search(w_resp_msg) is None
                )
            else:
                worker_success = True
                w_elapsed_us = None
                w_cluster_name = None

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

            if has_legacy_sdk_urma_map:
                sdk_urma_values = sdk_urma_get(i)
                if not sdk_urma_values and has_sdk_urma_index:
                    sdk_urma_values = sdk_urma_index_get(
                        (sdk[T_POD_IP], sdk[T_TRACE_ID])
                    )
            elif has_sdk_urma_index:
                sdk_urma_values = sdk_urma_index_get(
                    (sdk[T_POD_IP], sdk[T_TRACE_ID])
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
            else:
                c2w_urma_latency = None
            if w_idx is None:
                urma_empty_reason = None
            else:
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

                urma_latency = None
                urma_inflight_count = None
                src_ip = None
                dst_ip = None
                urma_empty_reason = None
                urma_list = worker_urma_get(w_idx)
                if urma_list:
                    first_urma = urma_list[0]
                    if isinstance(first_urma, tuple):
                        urma_latency = round(first_urma[T_ELAPSED_US] / 1000, 3)
                        urma_inflight_count = first_urma[T_INFLIGHT_COUNT]
                        src_ip = first_urma[T_SRC_ADDR]
                        dst_ip = first_urma[T_DST_ADDR]
                    else:
                        urma_latency = round(first_urma.elapsed_us / 1000, 3)
                        urma_inflight_count = first_urma.inflight_count
                        src_ip = first_urma.src_addr
                        dst_ip = first_urma.dst_addr
                elif sdk_success and worker_success:
                    remote_pulls = worker_remote_pull_get(w_idx)
                    if remote_pulls:
                        first_pull = remote_pulls[0]
                        if isinstance(first_pull, tuple):
                            src_ip = first_pull[T_SRC_ADDR]
                            dst_ip = first_pull[T_DST_ADDR]
                        else:
                            src_ip = first_pull.src_addr
                            dst_ip = first_pull.dst_addr
                    else:
                        endpoint = (
                            first_endpoint(worker_remote_worker_rpc_get(w_idx))
                            or first_endpoint(worker_remote_worker_cost_get(w_idx))
                        )
                        if endpoint:
                            src_ip, dst_ip = endpoint
                else:
                    urma_empty_reason = urma_empty_reason_get(
                        w_idx, "URMA fields empty: no matching URMA entry"
                    )

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
            is_anomalous = bool(remark) and remark != "OK"
            if is_anomalous:
                self.anomalous_count += 1

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
            if w_idx is None:
                results[i] = sparse_result_type(
                    total_latency,
                    is_anomalous,
                    "",  # id
                    log_id,
                    "",  # aggregated_event_id
                    "",  # anomalous_event_id
                    sdk[T_POD_IP],
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
            elif (
                src_ip is None
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
                    sdk[T_POD_IP],
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
                results[i] = result_type(
                    total_latency,
                    is_anomalous,
                    "",  # id
                    log_id,
                    "",  # aggregated_event_id
                    "",  # anomalous_event_id
                    sdk[T_POD_IP],
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
                    timestamp,
                    shared_created_at,
                )
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
            is_anomalous = bool(remark)
            if is_anomalous:
                self.anomalous_count += 1

            # 获取各指标 - 使用 _first_elapsed_us 统一处理 tuple/LogEntry

            # 优先使用传入的 log_file_id（数据库中的日志文件ID），其次使用 entry.log_id，最后使用 log_dir
            log_id = self.log_file_id or w_log_id or self.log_dir

            # 使用 LogParseResultDataclass 替代 LogParseResultModel.model_construct
            results.append(LogParseResultDataclass(
                log_id=log_id,
                trace_id=w_trace_id,
                timestamp=w_timestamp.strftime("%Y-%m-%d %H:%M:%S.%f")[:-3] if w_timestamp else None,
                src_ip=urma_info["src_ip"],
                dst_ip=urma_info["dst_ip"],
                pod_ip=w_pod_ip,
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
