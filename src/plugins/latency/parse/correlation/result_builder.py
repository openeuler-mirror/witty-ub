import logging
from datetime import datetime
from typing import Any, Optional

from latency.ENUM.ds_log import StatusCode
from latency.regex.kvcache_log import NOT_FOUND_RE
from latency.schemas.ds_log import (
    LogEntry,
    CorrelationResult,
    TupleField,
)
from latency.schemas.log import (
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
            entry_type = type(self.sdk_entries[0])
            logger.info(
                f"Building results from {len(self.sdk_entries):,} entries, "
                f"first entry type: {entry_type.__name__}"
            )
            if isinstance(self.sdk_entries[0], tuple):
                return self._build_from_sdk_raw()
            return self._build_from_sdk()
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
            urma_empty_reason = self.correlated.urma_empty_reasons.get(
                w_idx, "URMA fields empty: no matching URMA entry"
            )

        return dict(urma_latency=urma_latency, urma_inflight_count=urma_inflight_count,
                    src_ip=src_ip, dst_ip=dst_ip, urma_empty_reason=urma_empty_reason)

    def _build_sdk_remark(self, sdk: LogEntry, worker: Optional[LogEntry], c2w_latency: Optional[float], w2w_latency: Optional[float],     
                        sdk_success: bool, worker_success: bool, urma_empty_reason: Optional[str]) -> str:
        remark = ""
        if not sdk_success:
            remark = self._merge_remark(remark, self._format_failure_remark("SDK", sdk.status_code, sdk.resp_msg))
        if worker and not worker_success:
            remark = self._merge_remark(remark, self._format_failure_remark("Worker", worker.status_code, worker.resp_msg))
        if c2w_latency is not None and c2w_latency < 0:
            remark = self._merge_remark(remark, "Client2WorkerTime(us) < 0")
        if urma_empty_reason:
            remark = self._merge_remark(remark, urma_empty_reason)
        if not worker and not sdk_success:
            remark = self._format_failure_remark("SDK", sdk.status_code, sdk.resp_msg)
        return remark

    def _build_from_sdk_raw(
        self,
    ) -> list[LogParseResultDataclass | SparseLogParseResultDataclass]:
        results: list[
            LogParseResultDataclass | SparseLogParseResultDataclass
        ] = [None] * len(self.sdk_entries)  # type: ignore[list-item]
        shared_created_at = self._format_timestamp(datetime.now()) or ""

        correlated = self.correlated
        sdk_worker_get = correlated.sdk_worker_map.get
        worker_idx_get = correlated.worker_idx_map.get
        sdk_urma_map = correlated.sdk_urma_map
        sdk_urma_get = sdk_urma_map.get
        has_legacy_sdk_urma_map = bool(sdk_urma_map)
        sdk_urma_index_get = correlated.sdk_urma_index.get
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
        sparse_result_type = SparseLogParseResultDataclass
        fixed_log_id = self.log_file_id
        fallback_log_dir = self.log_dir
        cached_second_key = None
        cached_second_prefix = ""

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
                if not sdk_urma_values:
                    sdk_urma_values = sdk_urma_index_get(
                        (sdk[T_POD_IP], sdk[T_TRACE_ID])
                    )
            else:
                sdk_urma_values = sdk_urma_index_get(
                    (sdk[T_POD_IP], sdk[T_TRACE_ID])
                )
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
                src_ip = None
                dst_ip = None
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
                second_key = (
                    sdk_timestamp.year,
                    sdk_timestamp.month,
                    sdk_timestamp.day,
                    sdk_timestamp.hour,
                    sdk_timestamp.minute,
                    sdk_timestamp.second,
                )
                if second_key != cached_second_key:
                    cached_second_key = second_key
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

    def _build_from_sdk(self) -> list[LogParseResultDataclass]:
        results: list[LogParseResultDataclass] = []

        # 预生成共享的 created_at 时间戳，避免每条记录都调用 strftime
        shared_created_at = self._format_timestamp(datetime.now()) or ""

        for i, sdk in enumerate(self.sdk_entries):
            worker = self.correlated.sdk_worker_map.get(i)
            sdk_success = self._is_success_status(sdk.status_code, sdk.resp_msg)
            worker_success = self._is_success_status(worker.status_code, worker.resp_msg) if worker else True

            c2w_latency = self._format_latency((sdk.elapsed_us - worker.elapsed_us) / 1000) if worker else None
            w_idx = self.correlated.worker_idx_map.get(i) if worker else None

            query_meta_latency = self._first_elapsed_us(self.correlated.worker_query_meta_map, w_idx) if w_idx is not None else None
            urma_link_latency = self._first_elapsed_us(self.correlated.worker_link_map, w_idx) if w_idx is not None else None
            sdk_urma_values = self.correlated.sdk_urma_map.get(i)
            if not sdk_urma_values:
                sdk_urma_values = self.correlated.sdk_urma_index.get(
                    (sdk.pod_ip, sdk.trace_id)
                )
            c2w_urma_latency = self._first_elapsed_us(sdk_urma_values, None)
            w2w_urma_latency = self._first_elapsed_us(self.correlated.worker_worker_urma_map.get(w_idx, []), None) if w_idx is not None else None
            
            # 获取新增指标
            sdk_process = self._first_elapsed_us(self.correlated.worker_sdk_process_map, w_idx) if w_idx is not None else None
            sdk_rpc = self._first_elapsed_us(self.correlated.worker_sdk_rpc_map, w_idx) if w_idx is not None else None
            local_worker_cost = self._first_elapsed_us(self.correlated.worker_local_worker_cost_map, w_idx) if w_idx is not None else None
            local_worker_lock = self._first_elapsed_us(self.correlated.worker_local_worker_lock_map, w_idx) if w_idx is not None else None
            remote_worker_cost = self._first_elapsed_us(self.correlated.worker_remote_worker_cost_map, w_idx) if w_idx is not None else None
            remote_worker_rpc = self._first_elapsed_us(self.correlated.worker_remote_worker_rpc_map, w_idx) if w_idx is not None else None
            master_process = self._first_elapsed_us(self.correlated.worker_master_process_map, w_idx) if w_idx is not None else None
            master_rpc_total = self._first_elapsed_us_raw(self.correlated.worker_master_rpc_map, w_idx) if w_idx is not None else None

            urma_info = self._resolve_urma_info(w_idx, sdk_success, worker_success)

            remark = self._build_sdk_remark(sdk, worker, c2w_urma_latency, w2w_urma_latency, sdk_success, worker_success,
                                            urma_info["urma_empty_reason"])
            is_anomalous = bool(remark) and remark != "OK"
            if is_anomalous:
                self.anomalous_count += 1

            # 优先使用传入的 log_file_id（数据库中的日志文件ID），其次使用 entry.log_id，最后使用 log_dir
            log_id = self.log_file_id or sdk.log_id or self.log_dir

            # 使用 LogParseResultDataclass 替代 LogParseResultModel.model_construct
            results.append(LogParseResultDataclass(
                log_id=log_id,
                trace_id=sdk.trace_id,
                timestamp=self._format_timestamp(sdk.timestamp),
                src_ip=urma_info["src_ip"],
                dst_ip=urma_info["dst_ip"],
                pod_ip=sdk.pod_ip,
                cluster_name=worker.cluster_name if worker and worker.cluster_name else sdk.cluster_name,
                host=None,
                total_latency=self._format_latency(sdk.elapsed_us / 1000),
                c2w_latency=c2w_latency,
                worker_query_meta_latency=query_meta_latency,
                urma_total_latency=urma_info["urma_latency"],
                urma_link_latency=urma_link_latency,
                urma_inflight_count=urma_info["urma_inflight_count"],
                c2w_urma_latency=c2w_urma_latency,
                w2w_urma_latency=w2w_urma_latency,
                sdk_process=sdk_process,
                sdk_rpc=sdk_rpc,
                local_worker_cost=local_worker_cost,
                local_worker_lock=local_worker_lock,
                remote_worker_cost=remote_worker_cost,
                remote_worker_rpc=remote_worker_rpc,
                master_process=master_process,
                master_rpc_total=master_rpc_total,
                operation=sdk.operation,
                data_size=sdk.data_size,
                is_anomalous=is_anomalous,
                anomaly_reason=remark if is_anomalous else None,
                remark=remark or "OK",
                created_at=shared_created_at,
            ))
        return results

    def _build_from_worker(self) -> list[LogParseResultDataclass]:
        results: list[LogParseResultDataclass] = []

        # 预生成共享的 created_at 时间戳，避免每条记录都调用 strftime
        shared_created_at = self._format_timestamp(datetime.now()) or ""

        for i, w in enumerate(self.worker_entries):
            worker_success = self._is_success_status(w.status_code, w.resp_msg)
            urma_info = self._resolve_urma_info(i, True, worker_success)

            remark = ""
            if not worker_success:
                remark = self._format_failure_remark("Worker", w.status_code, w.resp_msg)
            is_anomalous = bool(remark)
            if is_anomalous:
                self.anomalous_count += 1

            query_meta_list = self.correlated.worker_query_meta_map.get(i, [])
            link_list = self.correlated.worker_link_map.get(i, [])
            w2c_urma_list = self.correlated.worker_worker_urma_map.get(i, [])
            
            # 获取新增指标
            sdk_process_list = self.correlated.worker_sdk_process_map.get(i, [])
            sdk_rpc_list = self.correlated.worker_sdk_rpc_map.get(i, [])
            local_worker_cost_list = self.correlated.worker_local_worker_cost_map.get(i, [])
            local_worker_lock_list = self.correlated.worker_local_worker_lock_map.get(i, [])
            remote_worker_cost_list = self.correlated.worker_remote_worker_cost_map.get(i, [])
            remote_worker_rpc_list = self.correlated.worker_remote_worker_rpc_map.get(i, [])
            master_process_list = self.correlated.worker_master_process_map.get(i, [])
            master_rpc_total_list = self.correlated.worker_master_rpc_map.get(i, [])

            # 优先使用传入的 log_file_id（数据库中的日志文件ID），其次使用 entry.log_id，最后使用 log_dir
            log_id = self.log_file_id or w.log_id or self.log_dir

            # 使用 LogParseResultDataclass 替代 LogParseResultModel.model_construct
            results.append(LogParseResultDataclass(
                log_id=log_id,
                trace_id=w.trace_id,
                timestamp=self._format_timestamp(w.timestamp),
                src_ip=urma_info["src_ip"],
                dst_ip=urma_info["dst_ip"],
                pod_ip=w.pod_ip,
                cluster_name=w.cluster_name,
                host=None,
                total_latency=self._format_latency(w.elapsed_us / 1000),
                worker_query_meta_latency=self._format_latency(query_meta_list[0].elapsed_us / 1000) if query_meta_list else None,
                urma_total_latency=urma_info["urma_latency"],
                urma_link_latency=self._format_latency(link_list[0].elapsed_us / 1000) if link_list else None,
                urma_inflight_count=urma_info["urma_inflight_count"],
                w2w_urma_latency=self._format_latency(w2c_urma_list[0].elapsed_us / 1000) if w2c_urma_list else None,
                sdk_process=self._format_latency(sdk_process_list[0].elapsed_us / 1000) if sdk_process_list else None,
                sdk_rpc=self._format_latency(sdk_rpc_list[0].elapsed_us / 1000) if sdk_rpc_list else None,
                local_worker_cost=self._format_latency(local_worker_cost_list[0].elapsed_us / 1000) if local_worker_cost_list else None,
                local_worker_lock=self._format_latency(local_worker_lock_list[0].elapsed_us / 1000) if local_worker_lock_list else None,
                remote_worker_cost=self._format_latency(remote_worker_cost_list[0].elapsed_us / 1000) if remote_worker_cost_list else None,
                remote_worker_rpc=self._format_latency(remote_worker_rpc_list[0].elapsed_us / 1000) if remote_worker_rpc_list else None,
                master_process=self._format_latency(master_process_list[0].elapsed_us / 1000) if master_process_list else None,
                master_rpc_total=master_rpc_total_list[0].elapsed_us if master_rpc_total_list else None,
                operation="DS_POSIX_GET",
                is_anomalous=is_anomalous,
                anomaly_reason=remark if is_anomalous else None,
                remark=remark or "OK",
                created_at=shared_created_at,
            ))
        return results
