import logging
import os
import operator
import time
import uuid
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Optional
from latency.schemas.log import (
    LogParseResultModel,
    LogParseResultDataclass,
    SparseLogParseResultDataclass,
)
from latency.schemas.request import ParseConfig
from latency.ENUM.task import TaskStatusEnum, TaskTypeEnum
from latency.config.config import Config
from latency.common.trace_context import collect_trace_context_logs
from latency.parse import (
    SdkAccessLogParser,
    WorkerAccessLogParser,
    WorkerInfoParser,
    WorkerMetricsLogParser,
    LogCorrelator,
    ParseResultBuilder,
)
from latency.ENUM.ds_log import EntryType
from latency.schemas.ds_log import TupleField
from latency.parse.parallel_scanner import ParallelFileScanner
from latency.ENUM.task import TaskSplitStrategy
from latency.common.stats import stats
from latency.detect import AnomalyDetector
from latency.database.managers.log_parse_result import LogParseResultManager
from latency.database.managers.task import TaskManager
from latency.database.managers.task_report import TaskReportManager
from latency.database.managers.log_knowledge import LogKnowledgeManager
from latency.database.managers.log_file import LogFileManager
from latency.database.managers.src_dst_aggregated_event import (
    SrcDstAggregatedEventManager,
)
from latency.database.managers.anomalous_event import AnomalousEventManager
from latency.database.managers.anomalous_event_chain import AnomalousEventChainManager
from latency.schemas.task import TaskModel
from latency.schemas.log import (
    SrcDstAggregatedEventDataclass,
    AnomalousEventDataclass,
    AnomalousEventChainModel,
)
from latency.task.worker.base import BaseWorker
from latency.regex.kvcache_log_file import (
    MIXED_ROTATED_GZ_PATTERN,
    include_gzip_patterns,
)



logger = logging.getLogger(__name__)

TRACE_CONTEXT_TIMEOUT_THRESHOLDS_MS = {
    "total_latency": 150.0,
    "worker_query_meta_latency": 150.0,
    "urma_total_latency": 150.0,
    "urma_link_latency": 150.0,
    "c2w_urma_latency": 100.0,
    "w2w_urma_latency": 100.0,
}

WORKER_INFO_LABEL_BY_ENTRY_TYPE = {
    EntryType.URMA.value: "Worker urma parse",
    EntryType.REMOTE_PULL.value: "Worker remote pull parse",
    EntryType.LINK.value: "Worker link parse",
    EntryType.QUERY_META.value: "Worker query meta parse",
}

# scan_scope 会作为 ProcessPool 参数复制到每个子进程。大型日志通常每条
# SDK 都有唯一 trace_id；传递百万级集合的序列化成本远高于直接扫描日志。
MAX_PROCESS_SCAN_SCOPE_TRACE_IDS = 50_000

def _expand_worker_access_patterns(patterns: list[str]) -> list[str]:
    """兼容 access_*.log 形式的 Worker access 日志文件名。

    诊断配置里常见默认值是 access.log/access.log.gz，但部分采集包会按滚动
    编号保存成 access_111.log。WorkerAccessLogParser 仍会按 DS_POSIX_GET
    关键字过滤内容，因此扩展文件名不会把 SDK access 误解析成 Worker 结果。
    """
    expanded: list[str] = []
    seen: set[str] = set()

    def add(pattern: str) -> None:
        if pattern and pattern not in seen:
            expanded.append(pattern)
            seen.add(pattern)

    for pattern in patterns:
        add(pattern)
        if pattern.endswith("access.log"):
            add(f"{pattern[:-len('access.log')]}access*.log")
        elif pattern.endswith("access.log.gz"):
            add(f"{pattern[:-len('access.log.gz')]}access*.log.gz")
    return expanded


@dataclass
class GroupStats:
    """增量统计分组（不维护完整对象引用，降低内存峰值）"""
    count: int = 0
    anomaly_count: int = 0
    anomaly_log_count: int = 0
    first_log_id: str = ""
    latency_values: dict[str, list[float]] = field(default_factory=dict)


class KVCacheLogParseWorker(BaseWorker):
    """
    KVCacheLogParseWorker
    """

    name = TaskTypeEnum.KV_CACHE_LOG_PARSE_WORKER

    @staticmethod
    def _include_gzip_patterns(patterns: list[str]) -> list[str]:
        """兼容 Worker 内部调用，实际规则由统一 pattern 模块维护。"""
        return include_gzip_patterns(patterns)

    @staticmethod
    async def init(op_id: str) -> str | None:
        """初始化任务"""
        log_file_model = await LogFileManager.get_log_file_by_log_file_id(op_id)
        if not log_file_model:
            return None
        kb_id = log_file_model.kb_id
        log_kb_model = await LogKnowledgeManager.get_log_kb_by_kb_id(kb_id)
        if not log_kb_model:
            return None

        task = TaskModel(
            kb_id=log_kb_model.id,
            op_id=op_id,
            task_name=f"Parse log file: {log_file_model.name}",
            task_type=TaskTypeEnum.KV_CACHE_LOG_PARSE_WORKER,
            status=TaskStatusEnum.PENDING,
        )
        await TaskManager.add_task(task)
        await LogFileManager.update_log_file(
            log_file_model.id, {"parse_status": TaskStatusEnum.PENDING.value}
        )
        await BaseWorker.report(task.id, "Task initialized", 0.0)
        return task.id

    @staticmethod
    async def reinit(task_id: str) -> bool:
        """重新初始化任务"""
        task = await TaskManager.get_task_by_task_id(task_id)
        if not task:
            return False
        await LogParseResultManager.update_log_parse_results_existed_status_by_log_id(
            task.op_id, existed_status=0
        )
        await AnomalousEventManager.update_anomalous_events_existed_status_by_log_id(
            task.op_id, existed_status=0
        )
        await AnomalousEventChainManager.update_event_chains_existed_status_by_log_id(
            task.op_id, existed_status=0
        )
        await SrcDstAggregatedEventManager.update_aggregated_events_existed_status_by_log_id(
            task.op_id, existed_status=0
        )
        await TaskReportManager.update_task_reports_existed_status_by_task_id(
            task_id, existed_status=TaskStatusEnum.PENDING
        )
        if task.retry_times > Config().get_config().task.task_retry_times:
            await LogFileManager.update_log_file(
                task.op_id, {"parse_status": TaskStatusEnum.FAILED.value}
            )
            logger.warning(
                f"Task {task_id} retry count {task.retry_times} exceeded max retries {Config().get_config().task.task_retry_times}"
            )
            return False
        await LogFileManager.update_log_file(
            task.op_id, {"parse_status": TaskStatusEnum.PENDING.value}
        )
        await BaseWorker.report(task.id, "Task reinitialized", 0.0)
        return True

    @staticmethod
    async def deinit(task_id: str) -> str:
        """析构任务"""
        return task_id

    @staticmethod
    def _new_parallel_scanner() -> ParallelFileScanner:
        return ParallelFileScanner(
            max_processes=os.cpu_count(),
            split_strategy=TaskSplitStrategy.BY_FILE_SIZE,
            use_multiprocessing=True,
            decompress=False,
        )

    @staticmethod
    def _build_worker_access_scan_scope(parsed: dict[str, list]) -> dict:
        sdk_entries = parsed.get("SDK access parse", [])

        if not sdk_entries:
            return {
                "enabled": False,
                "_stats": {
                    "sdk_traces": 0,
                },
            }

        is_tuple = isinstance(sdk_entries[0], tuple)
        trace_ids: set[str] = set()
        for entry in sdk_entries:
            trace_id = entry[TupleField.TRACE_ID] if is_tuple else entry.trace_id
            if not trace_id:
                continue
            trace_ids.add(trace_id)
            if len(trace_ids) > MAX_PROCESS_SCAN_SCOPE_TRACE_IDS:
                return {
                    "enabled": False,
                    "reason": "trace_scope_too_large",
                    "_stats": {
                        "sdk_entries": len(sdk_entries),
                        "sdk_traces": len(trace_ids),
                        "trace_limit": MAX_PROCESS_SCAN_SCOPE_TRACE_IDS,
                    },
                }
        return {
            "enabled": True,
            "trace_ids": trace_ids,
            "_stats": {
                "sdk_entries": len(sdk_entries),
                "sdk_traces": len(trace_ids),
                "trace_limit": MAX_PROCESS_SCAN_SCOPE_TRACE_IDS,
            },
        }

    @staticmethod
    def _build_worker_info_scan_scope(
        parsed: dict[str, list],
        sdk_trace_ids: Optional[set[str]] = None,
    ) -> dict:
        sdk_entries = parsed.get("SDK access parse", [])
        worker_entries = parsed.get("Worker access parse", [])

        if not sdk_entries:
            return {
                "enabled": False,
                "_stats": {
                    "sdk_traces": 0,
                    "worker_scope": len(worker_entries),
                    "pod_trace_scope": 0,
                    "pod_scope": 0,
                },
            }

        worker_is_tuple = worker_entries and isinstance(worker_entries[0], tuple)

        if sdk_trace_ids is None:
            sdk_is_tuple = isinstance(sdk_entries[0], tuple)
            trace_ids = (
                {
                    entry[TupleField.TRACE_ID]
                    for entry in sdk_entries
                    if entry[TupleField.TRACE_ID]
                }
                if sdk_is_tuple
                else {entry.trace_id for entry in sdk_entries if entry.trace_id}
            )
        else:
            trace_ids = sdk_trace_ids
        pod_trace_keys = set()
        pod_ips = set()
        worker_scope = 0
        for worker in worker_entries:
            w_trace_id = worker[TupleField.TRACE_ID] if worker_is_tuple else worker.trace_id
            if w_trace_id not in trace_ids:
                continue
            worker_scope += 1
            w_pod_ip = worker[TupleField.POD_IP] if worker_is_tuple else worker.pod_ip
            if w_pod_ip and w_trace_id:
                pod_trace_keys.add((w_pod_ip, w_trace_id))
            if w_pod_ip:
                pod_ips.add(w_pod_ip)

        return {
            "enabled": True,
            "trace_ids": trace_ids,  # 直接传递集合
            "pod_trace_keys": pod_trace_keys,  # 直接传递集合
            "pod_ips": pod_ips,  # 直接传递集合
            "_stats": {
                "sdk_traces": len(trace_ids),
                "worker_scope": worker_scope,
                "pod_trace_scope": len(pod_trace_keys),
                "pod_scope": len(pod_ips),
            },
        }

    @staticmethod
    def _split_worker_info_entries(parsed: dict[str, list]) -> None:
        """将聚合的 Worker INFO 结果单遍拆分为关联器使用的标签。"""
        info_entries = parsed.pop("Worker info parse", [])
        if not info_entries:
            return

        is_tuple = isinstance(info_entries[0], tuple)
        split_entries: dict[str, list] = defaultdict(list)
        label_get = WORKER_INFO_LABEL_BY_ENTRY_TYPE.get
        if is_tuple:
            # ProcessPool 序列化 tuple 中的 entry_type 已经是字符串，避免
            # 对每条记录重复做 Enum isinstance/value 分支。
            for entry in info_entries:
                label = label_get(entry[TupleField.ENTRY_TYPE])
                if label is not None:
                    split_entries[label].append(entry)
        else:
            for entry in info_entries:
                entry_type = entry.entry_type
                entry_type_value = (
                    entry_type.value
                    if isinstance(entry_type, EntryType)
                    else entry_type
                )
                label = label_get(entry_type_value)
                if label is not None:
                    split_entries[label].append(entry)
        parsed.update(split_entries)

    # 解析日志
    @staticmethod
    async def parse_log(
        log_id: str = "",
        parse_config: Optional[ParseConfig] = None,
        log_dir: str = "",  # 向后兼容参数
        task_id: str = "",  # 用于上报分阶段耗时到 TaskReport
    ) -> list[LogParseResultModel]:
        """解析日志文件

        Args:
            log_id: 日志文件ID（数据库中的主键）
            parse_config: 解析配置
            log_dir: 日志目录路径（向后兼容，优先使用 log_id）
            task_id: 任务ID（用于上报分阶段耗时）

        Returns:
            解析结果列表
        """
        # 优先使用 log_id，如果没有则使用 log_dir（向后兼容）
        if log_id:
            # 从数据库获取日志文件信息
            from latency.database.managers.log_file import LogFileManager
            log_file = await LogFileManager.get_log_file_by_log_file_id(log_id)
            if not log_file:
                raise ValueError(f"Log file with id {log_id} not found")
            log_dir = log_file.file_path
            from latency.database.managers.diagnosis_config import DiagnosisConfigManager

            diagnosis_config = await DiagnosisConfigManager.get_or_create(log_file.kb_id)
        elif not log_dir:
            raise ValueError("Either log_id or log_dir must be provided")
        else:
            diagnosis_config = Config().get_diagnosis_config()

        sdk_parsers = [SdkAccessLogParser(parse_config)]
        worker_access_parsers = [WorkerAccessLogParser(parse_config)]
        info_parsers = [WorkerInfoParser(parse_config), WorkerMetricsLogParser(parse_config)]
        filename_config = diagnosis_config.log_filename_pattern
        sdk_patterns = [
            *filename_config.ds_client_access_log_file,
            *filename_config.ds_client_info_log_file,
        ]
        for parser in sdk_parsers:
            parser._runtime_patterns = (
                KVCacheLogParseWorker._include_gzip_patterns(sdk_patterns)
            )
        worker_access_patterns = _expand_worker_access_patterns(
            list(filename_config.ds_worker_access_log_file)
        )
        for parser in worker_access_parsers:
            parser._runtime_patterns = (
                KVCacheLogParseWorker._include_gzip_patterns(
                    worker_access_patterns
                )
            )
        for parser in info_parsers:
            parser._runtime_patterns = (
                KVCacheLogParseWorker._include_gzip_patterns(
                    filename_config.ds_worker_info_log_file
                )
            )

        sdk_scanner = KVCacheLogParseWorker._new_parallel_scanner()
        worker_access_scanner = KVCacheLogParseWorker._new_parallel_scanner()
        info_scanner = KVCacheLogParseWorker._new_parallel_scanner()

        logger.info("=== Stage 1/3: Scanning files with parallel scanner ===")
        t_scan_start = time.perf_counter()
        parsed = await sdk_scanner.scan_all(log_dir, sdk_parsers, parse_config)

        t_worker_access_scope_start = time.perf_counter()
        worker_access_scan_scope = KVCacheLogParseWorker._build_worker_access_scan_scope(parsed)
        t_worker_access_scope = time.perf_counter() - t_worker_access_scope_start
        worker_access_scope_stats = worker_access_scan_scope.get("_stats", {})
        logger.info(
            "Worker access scan scope: enabled=%s, sdk_traces=%d, reason=%s",
            worker_access_scan_scope.get("enabled", False),
            worker_access_scope_stats.get("sdk_traces", 0),
            worker_access_scan_scope.get("reason", "bounded_scope"),
        )

        worker_access_parsed = await worker_access_scanner.scan_all(
            log_dir,
            worker_access_parsers,
            parse_config,
            scan_scope=worker_access_scan_scope,
        )
        parsed.update(worker_access_parsed)

        t_info_scope_start = time.perf_counter()
        if worker_access_scan_scope.get("enabled", False):
            info_scan_scope = KVCacheLogParseWorker._build_worker_info_scan_scope(
                parsed,
                worker_access_scan_scope["trace_ids"],
            )
        else:
            worker_entries = parsed.get("Worker access parse", [])
            info_scan_scope = {
                "enabled": False,
                "reason": worker_access_scan_scope.get("reason", "sdk_scope_disabled"),
                "_stats": {
                    "sdk_traces": worker_access_scope_stats.get("sdk_traces", 0),
                    "worker_scope": len(worker_entries),
                    "pod_trace_scope": 0,
                    "pod_scope": 0,
                },
            }
        t_info_scope = time.perf_counter() - t_info_scope_start
        info_scope_stats = info_scan_scope.get("_stats", {})
        logger.info(
            "Worker INFO scan scope: enabled=%s, sdk_traces=%d, worker_scope=%d, pod_trace_scope=%d, pod_scope=%d",
            info_scan_scope.get("enabled", False),
            info_scope_stats.get("sdk_traces", 0),
            info_scope_stats.get("worker_scope", 0),
            info_scope_stats.get("pod_trace_scope", 0),
            info_scope_stats.get("pod_scope", 0),
        )

        skip_info_scan = (
            info_scan_scope.get("enabled", False)
            and not info_scan_scope.get("trace_ids")
            and not info_scan_scope.get("pod_ips")
        )
        if skip_info_scan:
            info_parsed = {}
            logger.info("Skipping Worker INFO scan because SDK trace scope is empty")
        else:
            info_parsed = await info_scanner.scan_all(
                log_dir,
                info_parsers,
                parse_config,
                scan_scope=info_scan_scope,
            )
            parsed.update(info_parsed)
            
            # WorkerInfoParser 将所有结果存储在 "Worker info parse" 标签下，
            # 但 LogCorrelator 需要按旧独立解析器的标签分别获取。
            # 这里按 entry_type 拆分为各个旧标签。
            KVCacheLogParseWorker._split_worker_info_entries(parsed)

        t_scan = time.perf_counter() - t_scan_start

        # 排序解析结果
        t_sort_start = time.perf_counter()
        for label in parsed:
            entries = parsed[label]
            if entries and isinstance(entries[0], tuple):
                parsed[label].sort(key=operator.itemgetter(0))
            else:
                parsed[label].sort(key=operator.attrgetter("timestamp"))
            logger.info(f"  {label}: {len(parsed[label]):,} entries")
        entry_counts = {label: len(entries) for label, entries in parsed.items()}
        t_sort = time.perf_counter() - t_sort_start

        logger.info("=== Stage 2/3: Correlating entries ===")
        t_corr_start = time.perf_counter()
        correlator = LogCorrelator(parsed)
        correlated = correlator.correlate()
        t_corr = time.perf_counter() - t_corr_start
        logger.info(f"  SDK→Worker: {len(correlated.sdk_worker_map):,}, "
                     f"Worker→URMA: {len(correlated.worker_urma_map):,}")
        correlate_index_seconds = correlator.index_build_seconds
        correlate_stage_timings = list(correlator.stage_timings)
        correlate_worker_scope_count = correlator.worker_scope_count
        correlate_worker_scope_pod_trace_count = correlator.worker_scope_pod_trace_count
        metric_worker_indices = set()
        for metric_map in (
            correlated.worker_sdk_process_map,
            correlated.worker_sdk_rpc_map,
            correlated.worker_local_worker_cost_map,
            correlated.worker_local_worker_lock_map,
            correlated.worker_remote_worker_cost_map,
            correlated.worker_remote_worker_rpc_map,
            correlated.worker_master_process_map,
            correlated.worker_master_rpc_map,
        ):
            metric_worker_indices.update(metric_map.keys())
        correlate_match_counts = {
            "sdk_worker": len(correlated.sdk_worker_map),
            "sdk_urma_groups": len(correlated.sdk_urma_index),
            "worker_urma": len(correlated.worker_urma_map),
            "worker_link": len(correlated.worker_link_map),
            "worker_meta": len(correlated.worker_query_meta_map),
            "worker_metrics": len(metric_worker_indices),
        }

        # correlator 仍持有 parsed 列表和索引；先断开引用，再依靠引用计数
        # 即时回收。强制全量 GC 只会扫描千万级对象。
        del correlator
        sdk_entries = parsed.pop("SDK access parse", [])
        worker_entries = parsed.pop("Worker access parse", [])
        del parsed
        logger.info("Released parsed entries")

        logger.info("=== Stage 3/3: Building parse results ===")
        t_build_start = time.perf_counter()
        builder = ParseResultBuilder(sdk_entries, worker_entries, correlated, log_dir=log_dir, log_file_id=log_id)
        results = builder.build()
        anomalous_count = builder.anomalous_count
        t_build = time.perf_counter() - t_build_start

        # 及时释放所有中间结构（降低内存峰值）
        del sdk_entries, worker_entries, correlated, builder
        logger.info("Released sdk_entries, worker_entries, correlated & builder")

        total = len(results)
        logger.info(f"Parse complete: {total:,} results, {anomalous_count:,} anomalous")

        # 分阶段耗时报告
        t_total = t_scan + t_sort + t_corr + t_build
        logger.info(
            f"=== [parse_log] Timing Breakdown (total={t_total:.1f}s) ===\n"
            f"  Scan + deserialize: {t_scan:7.1f}s ({t_scan/t_total*100:5.1f}%)\n"
            f"  Sort entries:       {t_sort:7.1f}s ({t_sort/t_total*100:5.1f}%)\n"
            f"  Correlate:          {t_corr:7.1f}s ({t_corr/t_total*100:5.1f}%)\n"
            f"  Build results:      {t_build:7.1f}s ({t_build/t_total*100:5.1f}%)"
        )

        if task_id:
            pct_scan = t_scan / t_total * 100
            pct_sort = t_sort / t_total * 100
            pct_corr = t_corr / t_total * 100
            pct_build = t_build / t_total * 100
            await BaseWorker.report(task_id, f"[parse_log] Scan+deserialize: {t_scan:.1f}s ({pct_scan:.1f}%)", t_scan)
            sdk_metrics = sdk_scanner.metrics
            worker_access_metrics = worker_access_scanner.metrics
            info_metrics = info_scanner.metrics
            scan_build_map_s = (
                sdk_metrics.build_map_time_ms
                + worker_access_metrics.build_map_time_ms
                + info_metrics.build_map_time_ms
            ) / 1000
            scan_split_s = (
                sdk_metrics.split_time_ms
                + worker_access_metrics.split_time_ms
                + info_metrics.split_time_ms
            ) / 1000
            scan_worker_exec_s = (
                sdk_metrics.scan_time_ms
                + worker_access_metrics.scan_time_ms
                + info_metrics.scan_time_ms
            ) / 1000
            scan_merge_overhead_s = max(
                0.0,
                t_scan
                - t_worker_access_scope
                - t_info_scope
                - scan_build_map_s
                - scan_split_s
                - scan_worker_exec_s,
            )
            await BaseWorker.report(
                task_id,
                (
                    "[perf][scan.summary] "
                    f"phases=3, files={sdk_metrics.total_files + worker_access_metrics.total_files + info_metrics.total_files}, "
                    f"processes={sdk_metrics.total_processes}+{worker_access_metrics.total_processes}+{info_metrics.total_processes}, "
                    f"entries={sdk_metrics.total_entries + worker_access_metrics.total_entries + info_metrics.total_entries}, "
                    f"total={t_scan:.1f}s"
                ),
                t_scan,
            )
            await BaseWorker.report(
                task_id,
                (
                    "[perf][scan.sdk] "
                    f"files={sdk_metrics.total_files}, processes={sdk_metrics.total_processes}, "
                    f"entries={sdk_metrics.total_entries}, total={sdk_metrics.total_time_ms/1000:.1f}s"
                ),
                sdk_metrics.total_time_ms / 1000,
            )
            await BaseWorker.report(
                task_id,
                (
                    "[perf][scan.worker_access_scope] "
                    f"enabled={worker_access_scan_scope.get('enabled', False)}, "
                    f"sdk_traces={worker_access_scope_stats.get('sdk_traces', 0)}, "
                    f"reason={worker_access_scan_scope.get('reason', 'bounded_scope')}, "
                    f"time={t_worker_access_scope:.3f}s"
                ),
                t_worker_access_scope,
            )
            await BaseWorker.report(
                task_id,
                (
                    "[perf][scan.worker_access] "
                    f"files={worker_access_metrics.total_files}, processes={worker_access_metrics.total_processes}, "
                    f"entries={worker_access_metrics.total_entries}, total={worker_access_metrics.total_time_ms/1000:.1f}s"
                ),
                worker_access_metrics.total_time_ms / 1000,
            )
            await BaseWorker.report(
                task_id,
                (
                    "[perf][scan.info_scope] "
                    f"enabled={info_scan_scope.get('enabled', False)}, "
                    f"sdk_traces={info_scope_stats.get('sdk_traces', 0)}, "
                    f"worker_scope={info_scope_stats.get('worker_scope', 0)}/{entry_counts.get('Worker access parse', 0)}, "
                    f"pod_trace_scope={info_scope_stats.get('pod_trace_scope', 0)}, "
                    f"pods={info_scope_stats.get('pod_scope', 0)}, "
                    f"time={t_info_scope:.3f}s"
                ),
                t_info_scope,
            )
            await BaseWorker.report(
                task_id,
                (
                    "[perf][scan.info] "
                    f"files={info_metrics.total_files}, processes={info_metrics.total_processes}, "
                    f"entries={info_metrics.total_entries}, total={info_metrics.total_time_ms/1000:.1f}s"
                ),
                info_metrics.total_time_ms / 1000,
            )
            await BaseWorker.report(
                task_id,
                f"[perf][scan.build_map] {scan_build_map_s:.3f}s",
                scan_build_map_s,
            )
            await BaseWorker.report(
                task_id,
                f"[perf][scan.split] {scan_split_s:.3f}s",
                scan_split_s,
            )
            await BaseWorker.report(
                task_id,
                f"[perf][scan.worker_exec] {scan_worker_exec_s:.1f}s",
                scan_worker_exec_s,
            )
            await BaseWorker.report(
                task_id,
                f"[perf][scan.merge_overhead] {scan_merge_overhead_s:.1f}s",
                scan_merge_overhead_s,
            )
            await BaseWorker.report(
                task_id,
                (
                    "[perf][scan.entries] "
                    f"sdk={entry_counts.get('SDK access parse', 0)}, "
                    f"worker={entry_counts.get('Worker access parse', 0)}, "
                    f"urma={entry_counts.get('Worker urma parse', 0)}, "
                    f"pull={entry_counts.get('Worker remote pull parse', 0)}, "
                    f"link={entry_counts.get('Worker link parse', 0)}, "
                    f"meta={entry_counts.get('Worker query meta parse', 0)}, "
                    f"metrics={entry_counts.get('Worker metrics parse', 0)}"
                ),
                0.0,
            )
            await BaseWorker.report(task_id, f"[parse_log] Sort entries: {t_sort:.1f}s ({pct_sort:.1f}%)", t_sort)
            await BaseWorker.report(task_id, f"[parse_log] Correlate: {t_corr:.1f}s ({pct_corr:.1f}%)", t_corr)
            await BaseWorker.report(
                task_id,
                (
                    "[perf][correlate.index] "
                    f"{correlate_index_seconds:.3f}s "
                    f"sdk={entry_counts.get('SDK access parse', 0)}, "
                    f"worker={entry_counts.get('Worker access parse', 0)}, "
                    f"urma={entry_counts.get('Worker urma parse', 0)}, "
                    f"pull={entry_counts.get('Worker remote pull parse', 0)}, "
                    f"link={entry_counts.get('Worker link parse', 0)}, "
                    f"meta={entry_counts.get('Worker query meta parse', 0)}, "
                    f"metrics={entry_counts.get('Worker metrics parse', 0)}"
                ),
                correlate_index_seconds,
            )
            for stage_name, elapsed in correlate_stage_timings:
                await BaseWorker.report(
                    task_id,
                    f"[perf][correlate.{stage_name}] {elapsed:.3f}s",
                    elapsed,
                )
            await BaseWorker.report(
                task_id,
                (
                    "[perf][correlate.matches] "
                    f"worker_scope={correlate_worker_scope_count}/{entry_counts.get('Worker access parse', 0)}, "
                    f"pod_trace_scope={correlate_worker_scope_pod_trace_count}, "
                    f"sdk_worker={correlate_match_counts['sdk_worker']}/{entry_counts.get('SDK access parse', 0)}, "
                    f"sdk_urma_groups={correlate_match_counts['sdk_urma_groups']}, "
                    f"worker_urma={correlate_match_counts['worker_urma']}/{entry_counts.get('Worker access parse', 0)}, "
                    f"worker_link={correlate_match_counts['worker_link']}/{entry_counts.get('Worker access parse', 0)}, "
                    f"worker_meta={correlate_match_counts['worker_meta']}/{entry_counts.get('Worker access parse', 0)}, "
                    f"worker_metrics={correlate_match_counts['worker_metrics']}/{entry_counts.get('Worker access parse', 0)}"
                ),
                0.0,
            )
            await BaseWorker.report(task_id, f"[parse_log] Build results: {t_build:.1f}s ({pct_build:.1f}%)", t_build)
            await BaseWorker.report(task_id, f"[parse_log] Total: {t_total:.1f}s, {total} results", 0.0)
        return results

    # 异常事件检测
    @staticmethod
    async def detect_exception(
        list_log_parse_results: list[LogParseResultModel],
        analyzer_config=None,
    ) -> list[AnomalousEventDataclass]:
        """使用多窗口并行检测引擎检测异常事件"""
        n = len(list_log_parse_results)

        detector = AnomalyDetector.from_config(analyzer_config)
        events = await detector.detect(list_log_parse_results)

        if not events:
            return events

        from latency.schemas.log import generate_uuids_hex

        event_ids = generate_uuids_hex(len(events))
        for event, event_id in zip(events, event_ids):
            event.id = event_id
            event.aggregated_event_id = ""
            start_idx = event.start_log_parse_offset
            end_idx = event.end_log_parse_offset
            for idx in range(start_idx, end_idx + 1):
                if 0 <= idx < len(list_log_parse_results):
                    r = list_log_parse_results[idx]
                    r.anomalous_event_id = event.id
                    r.is_anomalous = True

        logger.info(
            f"Detect exception: {len(events):,} anomalous entries out of {n:,} results"
        )
        return events

    @staticmethod
    def _is_failure_result(result: LogParseResultModel) -> bool:
        remark = (result.remark or "").strip()
        if remark and remark.upper() != "OK":
            return True

        anomaly_reason = (result.anomaly_reason or "").strip()
        if anomaly_reason and "threshold" not in anomaly_reason.lower():
            return True

        return False

    @staticmethod
    def _is_timeout_result(result: LogParseResultModel) -> bool:
        for field_name, threshold in TRACE_CONTEXT_TIMEOUT_THRESHOLDS_MS.items():
            value = getattr(result, field_name, None)
            if isinstance(value, (int, float)) and value > threshold:
                return True
        return False

    @staticmethod
    def _collect_context_trace_ids(
        list_log_parse_results: list[LogParseResultModel],
    ) -> set[str]:
        trace_ids: set[str] = set()
        for result in list_log_parse_results:
            trace_id = (result.trace_id or "").strip()
            if not trace_id:
                continue
            if (
                KVCacheLogParseWorker._is_failure_result(result)
                or KVCacheLogParseWorker._is_timeout_result(result)
            ):
                trace_ids.add(trace_id)
        return trace_ids

    @staticmethod
    async def store_trace_context_logs(
        log_id: str,
        log_dir: str,
        list_log_parse_results: list[LogParseResultModel],
    ) -> int:
        trace_ids = KVCacheLogParseWorker._collect_context_trace_ids(list_log_parse_results)
        return await collect_trace_context_logs(
            log_id=log_id,
            log_dir=log_dir,
            trace_ids=trace_ids,
            clear_existing=True,
        )

    # 异常事件匹配故障
    @staticmethod
    async def match_fault(
        anomalous_events: list[AnomalousEventDataclass],
    ) -> list[AnomalousEventChainModel]:
        """异常事件匹配故障"""
        pass

    # 异常事件成因分析
    @staticmethod
    async def root_cause_analysis(
        anomalous_event_chains: list[AnomalousEventChainModel],
    ) -> list[AnomalousEventChainModel]:
        """异常事件成因分析"""
        pass

    # 基于src ip和dst ip的生成聚合结果
    @staticmethod
    async def generate_aggregate_result(
        list_log_parse_results: list[LogParseResultModel],
    ) -> tuple[
        list[SrcDstAggregatedEventDataclass], dict[tuple[str, str], str]
    ]:
        """按 src_ip/dst_ip 增量聚合统计（优化内存：不构建完整对象引用列表）"""
        sparse_hint = getattr(list_log_parse_results, "all_sparse", None)
        all_sparse = (
            sparse_hint
            if sparse_hint is not None
            else bool(list_log_parse_results)
            and all(
                type(result) is SparseLogParseResultDataclass
                for result in list_log_parse_results
            )
        )
        if all_sparse:
            logger.info(
                "Aggregate result: skipped %s sparse results without endpoints",
                f"{len(list_log_parse_results):,}",
            )
            return [], {}

        latency_fields = [
            ("total_latency", "total_latency"),
            ("query_meta_latency", "worker_query_meta_latency"),
            ("urma_total_latency", "urma_total_latency"),
            ("urma_link_latency", "urma_link_latency"),
            ("c2w_urma_latency", "c2w_urma_latency"),
            ("w2w_urma_latency", "w2w_urma_latency"),
        ]

        # 第一遍：增量收集统计值（不维护完整对象列表，降低内存峰值）
        groups: dict[tuple[str, str], GroupStats] = defaultdict(
            lambda: GroupStats(
                latency_values={prefix: [] for prefix, _ in latency_fields}
            )
        )
        
        for r in list_log_parse_results:
            src = r.src_ip or ""
            dst = r.dst_ip or ""
            if not src and not dst:
                continue
            
            key = (src, dst)
            g = groups[key]
            g.count += 1
            if r.is_anomalous:
                g.anomaly_count += 1
            if r.anomalous_event_id:
                g.anomaly_log_count += 1
            if not g.first_log_id:
                g.first_log_id = r.log_id or ""
            
            # 只收集延迟值，不保存完整对象引用
            for prefix, field_name in latency_fields:
                val = getattr(r, field_name)
                if val is not None:
                    g.latency_values[prefix].append(val)
        
        # 第二遍：构建聚合结果 + 反向写入 aggregated_event_id
        results: list[SrcDstAggregatedEventDataclass] = []
        src_dst_to_agg_id_map: dict[tuple[str, str], str] = {}
        
        for (src, dst), g in groups.items():
            agg_id = str(uuid.uuid4())
            src_dst_to_agg_id_map[(src, dst)] = agg_id
            
            agg: dict[str, float | None] = {}
            for prefix, _ in latency_fields:
                values = g.latency_values[prefix]
                if values:
                    st = stats(values)
                    agg[f"ave_{prefix}"] = st["ave"]
                    agg[f"min_{prefix}"] = st["min"]
                    agg[f"max_{prefix}"] = st["max"]
                    agg[f"p95_{prefix}"] = st["p95"]
                    agg[f"p99_{prefix}"] = st["p99"]
                else:
                    for f in [f"ave_{prefix}", f"min_{prefix}", f"max_{prefix}", f"p95_{prefix}", f"p99_{prefix}"]:
                        agg[f] = None
                g.latency_values[prefix] = []  # 计算完立即释放
            
            results.append(SrcDstAggregatedEventDataclass(
                id=agg_id,
                src_ip=src,
                dst_ip=dst,
                log_id=g.first_log_id,
                log_parse_result_cnt=g.count,
                anomaly_log_parse_result_cnt=g.anomaly_log_count,
                anomaly_cnt=g.anomaly_count,
                **agg,
            ))
        
        del groups  # 释放分组字典
        
        # 第三遍：反向写入 aggregated_event_id（保持与原逻辑一致）
        for r in list_log_parse_results:
            src = r.src_ip or ""
            dst = r.dst_ip or ""
            key = (src, dst)
            if key in src_dst_to_agg_id_map:
                r.aggregated_event_id = src_dst_to_agg_id_map[key]
        
        logger.info(f"Aggregate result: {len(results):,} endpoints from "
                     f"{len(list_log_parse_results):,} results")
        
        return results, src_dst_to_agg_id_map

    # 存库
    @staticmethod
    async def store_result(
        list_log_parse_results: list[LogParseResultDataclass],
        anomalous_events: list[AnomalousEventDataclass],
        anomalous_event_chains: list[AnomalousEventChainModel],
        src_dst_aggregated_events: list[SrcDstAggregatedEventDataclass],
    ) -> bool:
        """存库

        按引用顺序依次写入：log_parse_results → aggregated_events → anomalous_events → event_chains
        """
        success = True

        if list_log_parse_results:
            try:
                count = len(list_log_parse_results)
                stored = await LogParseResultManager.add_log_parse_results(
                    list_log_parse_results
                )
                if not stored:
                    raise RuntimeError("Failed to batch insert log parse results")
                logger.info(f"Stored {count:,} log parse results")
            except Exception as e:
                logger.error(f"Failed to store log parse results: {e}")
                success = False

        if src_dst_aggregated_events:
            try:
                await SrcDstAggregatedEventManager.add_aggregated_events(src_dst_aggregated_events)
                logger.info(f"Stored {len(src_dst_aggregated_events):,} aggregated events")
            except Exception as e:
                logger.error(f"Failed to store aggregated events: {e}")
                success = False

        if anomalous_events:
            try:
                await AnomalousEventManager.add_anomalous_events(anomalous_events)
                logger.info(f"Stored {len(anomalous_events):,} anomalous events")
            except Exception as e:
                logger.error(f"Failed to store anomalous events: {e}")
                success = False

        if anomalous_event_chains:
            try:
                await AnomalousEventChainManager.add_event_chains(anomalous_event_chains)
                logger.info(f"Stored {len(anomalous_event_chains):,} event chains")
            except Exception as e:
                logger.error(f"Failed to store event chains: {e}")
                success = False

        return success

    @staticmethod
    async def run(task_id: str) -> bool:
        """运行任务"""
        try:
            task = await TaskManager.get_task_by_task_id(task_id)
            if not task:
                logger.error(f"Task {task_id} not found")
                return False
            
            await TaskManager.update_task(
                task_id, {"status": TaskStatusEnum.RUNNING.value}
            )
            await BaseWorker.report(task.id, "Task running", 5.0)

            # 从 TaskHandler 获取解析配置
            from latency.task.task_handler import TaskHandler
            parse_config = TaskHandler.get_task_config(task_id)
            if parse_config:
                logger.info(f"[Task {task_id}] Using parse config: {parse_config}")

            # 直接使用 task.op_id 作为 log_id，parse_log 内部会获取 log_file 信息
            t_run_start = time.perf_counter()
            list_log_parse_results = await KVCacheLogParseWorker.parse_log(task.op_id, parse_config, task_id=task_id)
            t_parse = time.perf_counter() - t_run_start
            await BaseWorker.report(task.id, "Log parse completed", 40.0)
            await BaseWorker.report(
                task.id,
                f"[perf][parse.results] rows={len(list_log_parse_results)}",
                0.0,
            )

            # 获取 kb_id 用于后续更新知识库统计
            log_file = await LogFileManager.get_log_file_by_log_file_id(task.op_id)
            kb_id = log_file.kb_id if log_file else None

            # 先检测异常（填充 anomalous_event_id）
            t_detect_start = time.perf_counter()
            analyzer_config = None
            if kb_id:
                from latency.database.managers.diagnosis_config import DiagnosisConfigManager

                analyzer_config = (
                    await DiagnosisConfigManager.get_or_create(kb_id)
                ).log_analyzer_params
            anomalous_events = await KVCacheLogParseWorker.detect_exception(
                list_log_parse_results, analyzer_config
            )
            t_detect = time.perf_counter() - t_detect_start
            await BaseWorker.report(task.id, "Anomaly detection done", 50.0)
            await BaseWorker.report(
                task.id,
                f"[perf][detect.summary] results={len(list_log_parse_results)}, events={len(anomalous_events)}, time={t_detect:.3f}s",
                t_detect,
            )
            
            # 再生成聚合事件（此时 anomalous_event_id 已填充）
            t_agg_start = time.perf_counter()
            src_dst_aggregated_events, src_dst_to_agg_id_map = await KVCacheLogParseWorker.generate_aggregate_result(list_log_parse_results)
            t_agg = time.perf_counter() - t_agg_start
            await BaseWorker.report(task.id, "Aggregate events done", 60.0)
            await BaseWorker.report(
                task.id,
                (
                    "[perf][aggregate.summary] "
                    f"results={len(list_log_parse_results)}, endpoints={len(src_dst_aggregated_events)}, "
                    f"time={t_agg:.3f}s"
                ),
                t_agg,
            )
            
            # 更新异常事件的 aggregated_event_id
            for event in anomalous_events:
                start_idx = event.start_log_parse_offset
                if 0 <= start_idx < len(list_log_parse_results):
                    r = list_log_parse_results[start_idx]
                    src = r.src_ip or ""
                    dst = r.dst_ip or ""
                    event.aggregated_event_id = src_dst_to_agg_id_map.get((src, dst), "")
            
            anomalous_event_chains = await KVCacheLogParseWorker.match_fault(anomalous_events)
            await BaseWorker.report(task.id, "Fault matching done", 75.0)
            await BaseWorker.report(
                task.id,
                f"[perf][fault.summary] events={len(anomalous_events)}, chains={len(anomalous_event_chains or [])}",
                0.0,
            )

            t_store_start = time.perf_counter()
            stored = await KVCacheLogParseWorker.store_result(
                list_log_parse_results=list_log_parse_results,
                anomalous_events=anomalous_events,
                anomalous_event_chains=anomalous_event_chains or [],
                src_dst_aggregated_events=src_dst_aggregated_events,
            )
            t_store = time.perf_counter() - t_store_start
            await BaseWorker.report(task.id, "Results stored", 90.0)
            await BaseWorker.report(
                task.id,
                (
                    "[perf][store.summary] "
                    f"parse_results={len(list_log_parse_results)}, "
                    f"aggregated={len(src_dst_aggregated_events)}, "
                    f"anomalous={len(anomalous_events)}, "
                    f"chains={len(anomalous_event_chains or [])}, "
                    f"stored={stored}, time={t_store:.3f}s"
                ),
                t_store,
            )

            if log_file:
                t_context_start = time.perf_counter()
                context_log_count = await KVCacheLogParseWorker.store_trace_context_logs(
                    log_id=task.op_id,
                    log_dir=log_file.file_path,
                    list_log_parse_results=list_log_parse_results,
                )
                t_context = time.perf_counter() - t_context_start
                if context_log_count:
                    await BaseWorker.report(
                        task.id,
                        f"Trace context logs stored: {context_log_count}",
                        97.0,
                    )
                await BaseWorker.report(
                    task.id,
                    f"[perf][trace_context.summary] rows={context_log_count}, time={t_context:.3f}s",
                    t_context,
                )
            
            if not stored:
                logger.warning(f"Task {task_id} store partially failed, still marking as successful")

            await LogFileManager.update_log_file(
                task.op_id, {"anomaly_cnt": len(anomalous_events)}
            )
            
            # 更新关联的知识库统计
            if kb_id:
                await LogKnowledgeManager.update_log_kb(
                    kb_id, {"anomaly_cnt": len(anomalous_events)}
                )
            
            await TaskManager.update_task(
                task_id, {"status": TaskStatusEnum.SUCCESSFUL_PENDING_REMOVE.value}
            )
            await LogFileManager.update_log_file(
                task.op_id, {"parse_status": TaskStatusEnum.SUCCESSFUL.value}
            )
            await BaseWorker.report(task.id, "Task completed successfully", 100.0)

            # 全流程耗时汇总
            t_total = t_parse + t_detect + t_agg + t_store
            pct_p = t_parse / t_total * 100
            pct_d = t_detect / t_total * 100
            pct_a = t_agg / t_total * 100
            pct_s = t_store / t_total * 100
            logger.info(
                f"============================================================\n"
                f"=== [TASK TIMING] Total: {t_total:.1f}s ===\n"
                f"  [1] Parse log:       {t_parse:7.1f}s ({pct_p:5.1f}%)\n"
                f"  [2] Detect anomaly:  {t_detect:7.1f}s ({pct_d:5.1f}%)\n"
                f"  [3] Aggregate result:{t_agg:7.1f}s ({pct_a:5.1f}%)\n"
                f"  [4] Store to DB:     {t_store:7.1f}s ({pct_s:5.1f}%)\n"
                f"============================================================"
            )
            await BaseWorker.report(task.id, f"[TASK] Parse log: {t_parse:.1f}s ({pct_p:.1f}%)", t_parse)
            await BaseWorker.report(task.id, f"[TASK] Detect anomaly: {t_detect:.1f}s ({pct_d:.1f}%)", t_detect)
            await BaseWorker.report(task.id, f"[TASK] Aggregate result: {t_agg:.1f}s ({pct_a:.1f}%)", t_agg)
            await BaseWorker.report(task.id, f"[TASK] Store to DB: {t_store:.1f}s ({pct_s:.1f}%)", t_store)
            await BaseWorker.report(task.id, f"[TASK] Total: {t_total:.1f}s", 0.0)
            return True
        except Exception as e:
            logger.exception(f"Task {task_id} failed: {e}")
            await TaskManager.update_task(
                task_id, {"status": TaskStatusEnum.FAILED_PENDING_REMOVE.value}
            )
            return False

    @staticmethod
    async def stop(task_id: str) -> str | None:
        """停止任务"""
        task = await TaskManager.get_task_by_task_id(task_id)
        if task.status in [TaskStatusEnum.PENDING, TaskStatusEnum.RUNNING]:
            await LogParseResultManager.update_log_parse_results_existed_status_by_log_id(
                task.op_id, existed_status=0
            )
            await AnomalousEventManager.update_anomalous_events_existed_status_by_log_id(
                task.op_id, existed_status=0
            )
            await AnomalousEventChainManager.update_event_chains_existed_status_by_log_id(
                task.op_id, existed_status=0
            )
            await SrcDstAggregatedEventManager.update_aggregated_events_existed_status_by_log_id(
                task.op_id, existed_status=0
            )
            await TaskReportManager.update_task_reports_existed_status_by_task_id(
                task_id, existed_status=0
            )
            await TaskManager.update_task(
                task_id, {"status": TaskStatusEnum.CANCELLED.value}
            )
            return task_id
        return None

    @staticmethod
    async def delete(task_id: str) -> str:
        """删除任务"""
        return task_id
