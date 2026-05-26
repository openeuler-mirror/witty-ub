import logging
from typing import Any, Optional

from ENUM.ds_log import StatusCode
from regex.kvcache_log import NOT_FOUND_RE
from schemas.ds_log import (
    LogEntry,
    CorrelationResult,
)
from schemas.log import LogParseResultModel

logger = logging.getLogger(__name__)


class ParseResultBuilder:
    def __init__(
        self,
        sdk_entries: list[LogEntry],
        worker_entries: list[LogEntry],
        correlated: CorrelationResult,
        log_dir: str = "",
    ) -> None:
        self.sdk_entries = sdk_entries
        self.worker_entries = worker_entries
        self.correlated = correlated
        self.log_dir = log_dir

    def build(self) -> list[LogParseResultModel]:
        if self.sdk_entries:
            return self._build_from_sdk()
        return self._build_from_worker()

    @staticmethod
    def _is_success_status(status_code: int, resp_msg: Optional[str]) -> bool:
        return status_code == StatusCode.OK and NOT_FOUND_RE.search(resp_msg) is None

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

    def _first_elapsed_us(self, entry_list: Optional[dict[int, list[LogEntry]] | list[LogEntry]], key: Optional[int]) -> Optional[float]:
        values = entry_list.get(key, []) if isinstance(entry_list, dict) else entry_list
        return values[0].elapsed_us / 1000 if values else None

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
            urma_latency = urma_list[0].elapsed_us / 1000
            urma_inflight_count = urma_list[0].inflight_count
            src_ip = urma_list[0].src_addr
            dst_ip = urma_list[0].dst_addr
        elif sdk_success and worker_success:
            remote_pulls = self.correlated.worker_remote_pull_map.get(w_idx, [])
            if remote_pulls:
                src_ip = remote_pulls[0].src_addr
                dst_ip = remote_pulls[0].dst_addr
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

    def _build_from_sdk(self) -> list[LogParseResultModel]:
        results: list[LogParseResultModel] = []

        for i, sdk in enumerate(self.sdk_entries):
            worker = self.correlated.sdk_worker_map.get(i)
            sdk_success = self._is_success_status(sdk.status_code, sdk.resp_msg)
            worker_success = self._is_success_status(worker.status_code, worker.resp_msg) if worker else True

            c2w_latency = (sdk.elapsed_us - worker.elapsed_us) / 1000 if worker else None
            w_idx = self.correlated.worker_idx_map.get(i) if worker else None

            query_meta_latency = self._first_elapsed_us(self.correlated.worker_query_meta_map, w_idx) if w_idx is not None else None
            urma_link_latency = self._first_elapsed_us(self.correlated.worker_link_map, w_idx) if w_idx is not None else None
            c2w_urma_latency = self._first_elapsed_us(self.correlated.sdk_urma_map.get(i, []), None)
            w2w_urma_latency = self._first_elapsed_us(self.correlated.worker_worker_urma_map.get(w_idx, []), None) if w_idx is not None else None

            urma_info = self._resolve_urma_info(w_idx, sdk_success, worker_success)

            remark = self._build_sdk_remark(sdk, worker, c2w_urma_latency, w2w_urma_latency, sdk_success, worker_success,
                                            urma_info["urma_empty_reason"])
            is_anomalous = bool(remark) and remark != "OK"

            results.append(LogParseResultModel(
                log_id=self.log_dir,
                trace_id=sdk.trace_id,
                timestamp=sdk.timestamp,
                src_ip=urma_info["src_ip"],
                dst_ip=urma_info["dst_ip"],
                pod_ip=sdk.pod_ip,
                total_latency=sdk.elapsed_us / 1000,
                c2w_latency=c2w_latency,
                worker_query_meta_latency=query_meta_latency,
                urma_total_latency=urma_info["urma_latency"],
                urma_link_latency=urma_link_latency,
                urma_inflight_count=urma_info["urma_inflight_count"],
                c2w_urma_latency=c2w_urma_latency,
                w2w_urma_latency=w2w_urma_latency,
                urma_write_source=None,
                urma_write_dst=None,
                operation=sdk.operation,
                data_size=sdk.data_size,
                is_anomalous=is_anomalous,
                anomaly_reason=remark if is_anomalous else None,
                remark=remark or "OK",
            ))
        return results

    def _build_from_worker(self) -> list[LogParseResultModel]:
        results: list[LogParseResultModel] = []

        for i, w in enumerate(self.worker_entries):
            worker_success = self._is_success_status(w.status_code, w.resp_msg)
            urma_info = self._resolve_urma_info(i, True, worker_success)

            remark = ""
            if not worker_success:
                remark = self._format_failure_remark("Worker", w.status_code, w.resp_msg)
            is_anomalous = bool(remark)

            query_meta_list = self.correlated.worker_query_meta_map.get(i, [])
            link_list = self.correlated.worker_link_map.get(i, [])
            w2c_urma_list = self.correlated.worker_worker_urma_map.get(i, [])

            results.append(LogParseResultModel(
                log_id=self.log_dir,
                trace_id=w.trace_id,
                timestamp=w.timestamp,
                src_ip=urma_info["src_ip"],
                dst_ip=urma_info["dst_ip"],
                pod_ip=w.pod_ip,
                total_latency=w.elapsed_us / 1000,
                worker_query_meta_latency=query_meta_list[0].elapsed_us / 1000 if query_meta_list else None,
                urma_total_latency=urma_info["urma_latency"],
                urma_link_latency=link_list[0].elapsed_us / 1000 if link_list else None,
                urma_inflight_count=urma_info["urma_inflight_count"],
                w2w_urma_latency=w2c_urma_list[0].elapsed_us / 1000 if w2c_urma_list else None,
                urma_write_source=None,
                urma_write_dst=None,
                operation="DS_POSIX_GET",
                is_anomalous=is_anomalous,
                anomaly_reason=remark if is_anomalous else None,
                remark=remark or "OK",
            ))
        return results
