import asyncio
import logging
import os
from datetime import datetime, timezone

import time
import uuid
import functools
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any, Awaitable, Callable, Optional, Sequence
from latency.schemas.log import (
    TimeWindowAggregatedEventDataclass,
    LogParseResultDataclass,
)
from latency.schemas.request import ParseConfig
from latency.ENUM.task import TaskStatusEnum, TaskTypeEnum
from latency.config.config import Config
from latency.parse import (
    SdkAccessLogParser,
    ClientInfoParser,
    WorkerAccessLogParser,
    WorkerInfoParser,
)
from latency.parse.worker_info_parser import (
    URMA_LABEL,
    REMOTE_PULL_LABEL,
    LINK_LABEL,
    QUERY_META_LABEL,
    SDK_PROCESS_LABEL,
    SDK_RPC_LABEL,
    LOCAL_WORKER_COST_LABEL,
    LOCAL_WORKER_LOCK_LABEL,
    REMOTE_WORKER_COST_LABEL,
    REMOTE_WORKER_RPC_LABEL,
    MASTER_PROCESS_LABEL,
    MASTER_RPC_LABEL,
    TIMED_LABELS,
)
from latency.ENUM.ds_log import EntryType
from latency.schemas.ds_log import TupleField
from latency.parse.parallel_scanner import ParallelFileScanner
from latency.parse.parallel_scanner.trace_frame import build_trace_frame
from latency.ENUM.task import TaskSplitStrategy
from latency.database.managers.log_parse_result import LogParseResultPGManager
from latency.database.managers.task import TaskPGManager
from latency.database.managers.task_report import TaskReportPGManager
from latency.database.managers.log_knowledge import LogKnowledgePGManager
from latency.database.managers.log_file import LogFilePGManager
from latency.database.managers.log_failure_event import LogFailureEventPGManager
from latency.database.utils import parse_timestamp
from latency.database.managers.src_dst_aggregated_event import (
    SrcDstAggregatedEventPGManager,
)
from latency.database.managers.time_window_aggregated_event import (
    TimeWindowAggregatedEventPGManager,

)
from latency.database.managers.anomalous_event import AnomalousEventPGManager
from latency.database.managers.anomalous_event_chain import AnomalousEventChainPGManager
from latency.schemas.task import TaskModel
from latency.schemas.log import (
    TimeWindowAggregatedEventDataclass,
    SrcDstAggregatedEventDataclass,
)
from latency.task.worker.base import BaseWorker
from latency.bucket.statistics import (
    compute_and_store_bucket_stats_from_frame,
)



logger = logging.getLogger(__name__)


def _utc_now_str() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S.%f")


def _trace_row_count(trace_index: Any) -> int:
    """Unified row count: df_trace (polars, ``.height``) or flat-dict (``len``).

    T2/T5 列式路径下 *trace_index* 是 polars DataFrame；legacy（
    WITTY_UB_SCAN_COLUMNS=0）下是平铺 dict。run() 的进度/日志统一走这里。
    """
    if hasattr(trace_index, "height"):
        return int(trace_index.height)
    return len(trace_index)

WORKER_INFO_LABEL_BY_ENTRY_TYPE = {
    EntryType.URMA.value: URMA_LABEL,
    EntryType.REMOTE_PULL.value: REMOTE_PULL_LABEL,
    EntryType.LINK.value: LINK_LABEL,
    EntryType.QUERY_META.value: QUERY_META_LABEL,
    EntryType.SDK_PROCESS.value: SDK_PROCESS_LABEL,
    EntryType.SDK_RPC.value: SDK_RPC_LABEL,
    EntryType.LOCAL_WORKER_COST.value: LOCAL_WORKER_COST_LABEL,
    EntryType.LOCAL_WORKER_LOCK.value: LOCAL_WORKER_LOCK_LABEL,
    EntryType.REMOTE_WORKER_COST.value: REMOTE_WORKER_COST_LABEL,
    EntryType.REMOTE_WORKER_RPC.value: REMOTE_WORKER_RPC_LABEL,
    EntryType.MASTER_PROCESS.value: MASTER_PROCESS_LABEL,
    EntryType.MASTER_RPC.value: MASTER_RPC_LABEL,
}

# scan_scope 会作为 ProcessPool 参数复制到每个子进程。大型日志通常每条
# SDK 都有唯一 trace_id；传递百万级集合的序列化成本远高于直接扫描日志。
MAX_PROCESS_SCAN_SCOPE_TRACE_IDS = 50_000

# _resolve_snapshot 返回的全部时延字段(平铺 dict 中与 dataclass 同名的键)。
# 供 _make_field_row 从平铺 dict 挑出, 构造 LogParseResultDataclass。
_SNAPSHOT_KEYS = frozenset({
    "total_latency", "c2w_urma_latency", "c2w_latency",
    "urma_total_latency", "urma_link_latency", "query_meta_latency",
    "worker_query_meta_latency", "worker_total_latency",
    "sdk_process", "sdk_rpc", "local_worker_cost", "local_worker_lock",
    "remote_worker_cost", "remote_worker_rpc",
    "master_process", "master_rpc_total",
    "w2w_urma_latency", "create_latency", "publish_latency",
    "urma_inflight_count",
})

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
    async def init(op_id: str) -> str | None:
        """初始化任务"""
        log_file_model = await LogFilePGManager.get_log_file_by_log_file_id(op_id)
        if not log_file_model:
            return None
        kb_id = log_file_model.kb_id
        log_kb_model = await LogKnowledgePGManager.get_log_kb_by_kb_id(kb_id)
        if not log_kb_model:
            return None

        task = TaskModel(
            kb_id=log_kb_model.id,
            op_id=op_id,
            task_name=f"Parse log file: {log_file_model.name}",
            task_type=TaskTypeEnum.KV_CACHE_LOG_PARSE_WORKER,
            status=TaskStatusEnum.PENDING,
        )
        await TaskPGManager.add_task(task)
        await LogFilePGManager.update_log_file(
            log_file_model.id, {"parse_status": TaskStatusEnum.PENDING.value}
        )
        await BaseWorker.report(task.id, "Task initialized", 0.0)
        return task.id

    @staticmethod
    async def reinit(task_id: str) -> bool:
        """重新初始化任务"""
        task = await TaskPGManager.get_task_by_task_id(task_id)
        if not task:
            return False
        await LogParseResultPGManager.update_log_parse_results_existed_status_by_log_id(
            task.op_id, existed_status=0
        )
        await AnomalousEventPGManager.update_anomalous_events_existed_status_by_log_id(
            task.op_id, existed_status=0
        )
        await AnomalousEventChainPGManager.update_event_chains_existed_status_by_log_id(
            task.op_id, existed_status=0
        )
        await SrcDstAggregatedEventPGManager.update_aggregated_events_existed_status_by_log_id(
            task.op_id, existed_status=0
        )
        await TimeWindowAggregatedEventPGManager.delete_by_log_id(task.op_id)
        await TaskReportPGManager.update_task_reports_existed_status_by_task_id(
            task_id, existed_status=TaskStatusEnum.PENDING
        )
        if task.retry_times > Config().get_config().task.task_retry_times:
            await LogFilePGManager.update_log_file(
                task.op_id, {"parse_status": TaskStatusEnum.FAILED.value}
            )
            logger.warning(
                f"Task {task_id} retry count {task.retry_times} exceeded max retries {Config().get_config().task.task_retry_times}"
            )
            return False
        await LogFilePGManager.update_log_file(
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
        # 追加而非覆盖：合并单趟扫描下，快路径（scan_file）文件已把 info
        # 条目直接写入子标签，多解析器路径的桶条目必须并入，不能覆盖丢失。
        for label, extra in split_entries.items():
            existing = parsed.get(label)
            if existing is None:
                parsed[label] = extra
            else:
                existing.extend(extra)

    @staticmethod
    def _trace_ids(entries: list) -> set[str]:
        if not entries:
            return set()
        if isinstance(entries[0], tuple):
            return {
                entry[TupleField.TRACE_ID]
                for entry in entries
                if entry[TupleField.TRACE_ID]
            }
        return {entry.trace_id for entry in entries if entry.trace_id}

    @staticmethod
    def _build_trace_overlap_stats(parsed: dict[str, list]) -> dict[str, int]:
        sdk_traces = KVCacheLogParseWorker._trace_ids(
            parsed.get("SDK access parse", [])
        )
        worker_traces = KVCacheLogParseWorker._trace_ids(
            parsed.get("Worker access parse", [])
        )
        urma_traces = KVCacheLogParseWorker._trace_ids(parsed.get(URMA_LABEL, []))
        remote_pull_traces = KVCacheLogParseWorker._trace_ids(
            parsed.get(REMOTE_PULL_LABEL, [])
        )
        query_meta_traces = KVCacheLogParseWorker._trace_ids(
            parsed.get(QUERY_META_LABEL, [])
        )
        timed_traces: set[str] = set()
        for label in TIMED_LABELS:
            timed_traces.update(
                KVCacheLogParseWorker._trace_ids(parsed.get(label, []))
            )

        return {
            "sdk_trace_ids": len(sdk_traces),
            "worker_trace_ids": len(worker_traces),
            "urma_trace_ids": len(urma_traces),
            "remote_pull_trace_ids": len(remote_pull_traces),
            "query_meta_trace_ids": len(query_meta_traces),
            "timed_trace_ids": len(timed_traces),
            "sdk_worker_trace_overlap": len(sdk_traces & worker_traces),
            "worker_urma_trace_overlap": len(worker_traces & urma_traces),
            "worker_remote_pull_trace_overlap": len(
                worker_traces & remote_pull_traces
            ),
            "worker_query_meta_trace_overlap": len(
                worker_traces & query_meta_traces
            ),
            "worker_timed_trace_overlap": len(worker_traces & timed_traces),
        }

    # 解析日志
    @staticmethod
    async def parse_log(
        log_id: str = "",
        parse_config: Optional[ParseConfig] = None,
        log_dir: str = "",  # 向后兼容参数
        task_id: str = "",  # 用于上报分阶段耗时到 TaskReport
        scan_progress_cb: Optional[Callable[[float], Awaitable]] = None,
    ) -> Any:
        """解析日志文件

        Args:
            log_id: 日志文件ID（数据库中的主键）
            parse_config: 解析配置
            log_dir: 日志目录路径（向后兼容，优先使用 log_id）
            task_id: 任务ID（用于上报分阶段耗时）
            scan_progress_cb: 可选扫描进度回调 ``async (fraction: float) -> None``，
                转发给 scanner.scan_all，使扫描阶段进度平滑前进；None 时无副作用。

        Returns:
            列式路径（默认，WITTY_UB_SCAN_COLUMNS=1）: polars DataFrame ——
            每 trace 一行，列 = TRACE_COLUMNS（31），即 df_trace 契约（D4）。
            Legacy 路径（WITTY_UB_SCAN_COLUMNS=0）: {trace_id: 平铺dict(29键)}
            字典，保持向后兼容。
        """
        # 优先使用 log_id，如果没有则使用 log_dir（向后兼容）
        if log_id:
            # 从数据库获取日志文件信息
            log_file = await LogFilePGManager.get_log_file_by_log_file_id(log_id)
            if not log_file:
                raise ValueError(f"Log file with id {log_id} not found")
            if not log_dir:
                log_dir = log_file.file_path
            from latency.database.managers.diagnosis_config import DiagnosisConfigPGManager

            diagnosis_config = await DiagnosisConfigPGManager.get_or_create(log_file.kb_id)
        elif not log_dir:
            raise ValueError("Either log_id or log_dir must be provided")
        else:
            diagnosis_config = Config().get_diagnosis_config()

        sdk_parsers = [SdkAccessLogParser(parse_config), ClientInfoParser(parse_config)]
        worker_access_parsers = [WorkerAccessLogParser(parse_config)]
        info_parsers = [WorkerInfoParser(parse_config)]
        filename_config = diagnosis_config.log_filename_pattern
        sdk_parsers[0]._runtime_patterns = filename_config.ds_client_access_log_file
        sdk_parsers[1]._runtime_patterns = filename_config.ds_client_info_log_file
        for parser in worker_access_parsers:
            parser._runtime_patterns = filename_config.ds_worker_access_log_file
        for parser in info_parsers:
            parser._runtime_patterns = filename_config.ds_worker_info_log_file

        # T5 (Block D): 3 次串行 scan_all（SDK / WorkerAccess / INFO）合并为
        # 1 次 scan_all + 3 parser 列表，每文件只读 1 遍（IO × 1/3）。
        # FileParserMapBuilder 已支持多 parser per file；_scan_file_multi
        # 按 keyword 把行路由到所有匹配 parser（all-matching）。
        scanner = KVCacheLogParseWorker._new_parallel_scanner()
        all_parsers = [*sdk_parsers, *worker_access_parsers, *info_parsers]

        logger.info("=== Stage 1/2: Scanning files with parallel scanner ===")
        t_scan_start = time.perf_counter()
        parsed = await scanner.scan_all(
            log_dir,
            all_parsers,
            parse_config,
            progress_cb=scan_progress_cb,
        )

        # T1 (polars rewrite): 列式输出已随 legacy 标签一并返回, 本任务暂不消费
        # （T2 用 build_trace_frame 从列重建 df_trace），弹出避免下游误读。
        column_rows = parsed.pop("columns", None)
        if column_rows is not None:
            logger.info(
                "Columnar scan output: %d per-line rows",
                len(column_rows.get("tid", [])),
            )
            # 从 column_rows 统计各 label 条目数（替代已删除的 {label:[tuple]}）
            from collections import Counter
            entry_counts = Counter(column_rows.get("_label", []))

        t_scan = time.perf_counter() - t_scan_start

        if column_rows is not None:
            # T2 (polars rewrite): 列式路径 —— 从列式行重建 df_trace
            # （pl.concat → group_by("tid") → 每 trace 一行，列 = TRACE_COLUMNS）。
            # yuanrong 26 项分段时延已内置在 build_trace_frame 中。
            trace_index = build_trace_frame(column_rows)
            del column_rows
            del parsed
            logger.info("Released parsed entries (columnar path)")
            total = trace_index.height
        else:
            # T7: columnar 是唯一解析路径（legacy 平铺 dict 兜底已删）。扫描器
            # 在 WITTY_UB_SCAN_COLUMNS=0 时不会产出 "columns"，此时必须显式报错。
            raise RuntimeError(
                "Columnar scan output missing — WITTY_UB_SCAN_COLUMNS must be "
                "enabled (columnar is the only supported parse path after T7)"
            )

        logger.info(f"Parse complete: {total:,} traces")

        # 分阶段耗时报告
        t_total = t_scan
        logger.info(
            f"=== [parse_log] Timing Breakdown (total={t_total:.1f}s) ===\n"
            f"  Scan + deserialize: {t_scan:7.1f}s ({t_scan/t_total*100:5.1f}%)"
        )

        if task_id:
            pct_scan = t_scan / t_total * 100 if t_total else 0.0
            await BaseWorker.report(task_id, f"[parse_log] Scan+deserialize: {t_scan:.1f}s ({pct_scan:.1f}%)", t_scan)
            metrics = scanner.metrics
            scan_build_map_s = metrics.build_map_time_ms / 1000
            scan_split_s = metrics.split_time_ms / 1000
            scan_worker_exec_s = metrics.scan_time_ms / 1000
            scan_merge_overhead_s = max(
                0.0,
                t_scan
                - scan_build_map_s
                - scan_split_s
                - scan_worker_exec_s,
            )
            await BaseWorker.report(
                task_id,
                (
                    "[perf][scan.summary] "
                    f"phases=1, files={metrics.total_files}, "
                    f"processes={metrics.total_processes}, "
                    f"entries={metrics.total_entries}, "
                    f"total={t_scan:.1f}s"
                ),
                t_scan,
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
                    f"timed={sum(entry_counts.get(l, 0) for l in TIMED_LABELS)}"
                ),
                0.0,
            )
            await BaseWorker.report(task_id, f"[parse_log] Total: {t_total:.1f}s, {total} results", 0.0)

        return trace_index

    @staticmethod
    def _resolve_snapshot(trace_entries: dict[str, list]) -> dict[str, float | None]:
        """Resolve ALL latency fields from a single trace's raw scanner entries.

        Extracts ``ELAPSED_US / 1000.0`` (us → ms) for every recognised
        label.  Computed fields (w2w, create, publish) are returned as None
        because they require the result-builder correlation stage and are
        not present in the raw trace_index.

        Returns:
            dict with keys matching the dataclass field suffix
            (e.g. ``total_latency``, ``query_meta_latency``, …).
        """
        sdk = trace_entries.get("SDK access parse", [])
        worker = trace_entries.get("Worker access parse", [])

        snapshot: dict[str, float | None] = {}

        # total_latency  ──────────────────────────────────────────
        snapshot["total_latency"] = (
            sdk[0][TupleField.ELAPSED_US] / 1000.0 if sdk else None
        )

        # c2w_urma_latency  ───────────────────────────────────────
        if sdk and worker:
            snapshot["c2w_urma_latency"] = (
                sdk[0][TupleField.ELAPSED_US]
                - worker[0][TupleField.ELAPSED_US]
            ) / 1000.0
        else:
            snapshot["c2w_urma_latency"] = None

        # Label-based fields  ─────────────────────────────────────
        _label_map = {
            "urma_total_latency": URMA_LABEL,
            "urma_link_latency": LINK_LABEL,
            "query_meta_latency": QUERY_META_LABEL,
            "worker_total_latency": "Worker access parse",
            "sdk_process": SDK_PROCESS_LABEL,
            "sdk_rpc": SDK_RPC_LABEL,
            "local_worker_cost": LOCAL_WORKER_COST_LABEL,
            "local_worker_lock": LOCAL_WORKER_LOCK_LABEL,
            "remote_worker_cost": REMOTE_WORKER_COST_LABEL,
            "remote_worker_rpc": REMOTE_WORKER_RPC_LABEL,
            "master_process": MASTER_PROCESS_LABEL,
            "master_rpc_total": MASTER_RPC_LABEL,
        }
        for suffix, label in _label_map.items():
            entries = trace_entries.get(label, [])
            snapshot[suffix] = (
                entries[0][TupleField.ELAPSED_US] / 1000.0 if entries else None
            )

        # Computed-only fields (not in raw trace_index)  ──────────
        for suffix in ("w2w_urma_latency", "create_latency", "publish_latency"):
            snapshot[suffix] = None
        return snapshot

    @staticmethod
    def _extract_trace_metrics(
        tid: str,
        entries: dict[str, list],
    ) -> dict | None:
        """Extract per-trace metrics shared by the aggregate and field-table builds.

        Returns ``None`` when the trace must be skipped (no SDK entry, or the
        SDK ``elapsed_us`` is missing/negative) — mirroring the aggregate's
        first pass so the two slices stay perfectly aligned.
        """
        sdk_entries = entries.get("SDK access parse", [])
        if not sdk_entries:
            return None
        first = sdk_entries[0]
        elapsed_us = first[TupleField.ELAPSED_US]
        if elapsed_us is None or elapsed_us < 0:
            return None
        total_ms = elapsed_us / 1000.0
        # Resolve src/dst from downstream entries (URMA/RemotePull), not from
        # the SDK entry, which never carries SRC_ADDR/DST_ADDR. Fallback
        # chain: URMA -> RemotePull -> empty.
        _urma = entries.get(URMA_LABEL, [])
        _pop = entries.get(REMOTE_PULL_LABEL, [])
        if _urma:
            src = str(_urma[0][TupleField.SRC_ADDR] or "").strip() or ""
            dst = str(_urma[0][TupleField.DST_ADDR] or "").strip() or ""
        elif _pop:
            src = str(_pop[0][TupleField.SRC_ADDR] or "").strip() or ""
            dst = str(_pop[0][TupleField.DST_ADDR] or "").strip() or ""
        else:
            src = ""
            dst = ""
        op = (str(first[TupleField.OPERATION] or "")).strip().upper()
        op_key = "SET" if "SET" in op else "GET"
        bucket_epoch = KVCacheLogParseWorker._bucket_epoch_10s(
            first[TupleField.TIMESTAMP]
        )
        log_id = first[TupleField.LOG_ID] or ""
        return {
            "tid": tid,
            "entries": entries,
            "sdk_entries": sdk_entries,
            "first": first,
            "total_ms": total_ms,
            "src": src,
            "dst": dst,
            "op": op,
            "op_key": op_key,
            "bucket_epoch": bucket_epoch,
            "log_id": log_id,
            "status_code": first[TupleField.STATUS_CODE],
        }

    @staticmethod
    def _build_flat_trace_index(
        parsed: dict[str, list],
    ) -> dict[str, dict]:
        """归并扫描产物 → {trace_id: 平铺dict(29键)}。

        按 trace_id 归并 + 每 trace 提取全部字段(聚合标量 + 全部时延 +
        明细字段), 是唯一数据源。下游(聚合/桶统计/明细)直接消费, 无三层。
        """
        from collections import defaultdict as _dd
        grouped: dict[str, dict[str, list]] = _dd(lambda: _dd(list))
        for label, entries in parsed.items():
            for e in entries:
                tid = e[TupleField.TRACE_ID]
                if tid:
                    grouped[tid][label].append(e)
        flat: dict[str, dict] = {}
        for tid, entries in grouped.items():
            metrics = KVCacheLogParseWorker._extract_trace_metrics(tid, entries)
            if metrics is None:
                continue
            first = metrics["first"]
            snapshot = KVCacheLogParseWorker._resolve_snapshot(entries)
            worker_query_meta = snapshot.pop("query_meta_latency", None)
            snapshot["worker_query_meta_latency"] = worker_query_meta
            ts_raw = first[TupleField.TIMESTAMP]
            flat[tid] = {
                "tid": tid,
                "total_ms": metrics["total_ms"],
                "total_latency": metrics["total_ms"],
                "src": metrics["src"],
                "dst": metrics["dst"],
                "op": metrics["op"],
                "operation": metrics["op"] or None,
                "op_key": metrics["op_key"],
                "bucket_epoch": metrics["bucket_epoch"],
                "log_id": metrics["log_id"],
                "status_code": metrics["status_code"],
                "timestamp": str(ts_raw) if ts_raw else None,
                "pod_ip": str(first[TupleField.POD_IP]) if first[TupleField.POD_IP] else None,
                "data_size": str(first[TupleField.DATA_SIZE]) if first[TupleField.DATA_SIZE] else None,
                "inflight_count": first[TupleField.INFLIGHT_COUNT],
                **snapshot,
            }
        return flat

    @staticmethod
    def _make_field_row(
        flat: dict,
        log_file_id: str = "",
        created_at: str | None = None,
        is_anomalous: bool = False,
    ) -> LogParseResultDataclass:
        """Build one ``LogParseResultDataclass`` row from a trace's flat dict.

        平铺 dict(parse_log 归并产物)已含所有字段: 聚合标量 + 全部时延 +
        明细字段, 直接读, 无 entries / 无回读。
        """
        snapshot = {k: v for k, v in flat.items() if k in _SNAPSHOT_KEYS}
        # c2w_urma_latency(_resolve_snapshot 键名) → dataclass 的 c2w_latency
        if "c2w_latency" not in snapshot and "c2w_urma_latency" in flat:
            snapshot["c2w_latency"] = flat.get("c2w_urma_latency")
        return LogParseResultDataclass(
            is_anomalous=is_anomalous,
            aggregated_event_id="",
            timestamp=flat.get("timestamp"),
            src_ip=flat.get("src") or None,
            dst_ip=flat.get("dst") or None,
            operation=flat.get("op") or None,
            trace_id=flat.get("tid"),
            log_id=log_file_id or flat.get("log_id", ""),
            pod_ips=(
                [str(flat["pod_ip"])] if flat.get("pod_ip") else None
            ),
            data_size=(
                str(flat["data_size"]) if flat.get("data_size") else None
            ),
            urma_inflight_count=(
                int(flat["inflight_count"])
                if isinstance(flat.get("inflight_count"), (int, float))
                else None
            ),
            created_at=created_at or _utc_now_str(),
            **snapshot,
        )

    @staticmethod
    def _build_field_table_rows(
        trace_index: dict[str, dict[str, list]],
        log_file_id: str = "",
    ) -> list[LogParseResultDataclass]:
        """Serial full-trace field-table build — the golden-fixture reference.

        One ``LogParseResultDataclass`` row per valid trace (``is_anomalous``
        always ``False``), in SDK-entry order.  Feed for anomalous detail rows
        (filtered by ``anomalous_tids``) and for the bucket percentile tables.
        trace_index 已是 {trace_id: 平铺dict}(parse_log 归并产物)。
        """
        created_at = _utc_now_str()
        rows: list[LogParseResultDataclass] = []
        for tid, flat in trace_index.items():
            rows.append(
                KVCacheLogParseWorker._make_field_row(
                    flat, log_file_id, created_at
                )
            )
        return rows

    @staticmethod
    def _bucket_epoch_10s(ts_raw: Any) -> int | None:
        """Wall-clock 10s-aligned bucket epoch seconds (int), or None.

        Alignment mirrors ``bucket/statistics.py`` ``compute_bucket_ids``:
        the naive wall-clock timestamp is treated as UTC for the epoch
        second count, then floored to 10s. Because 10 divides 60/600/3600,
        coarser query granularities align exactly on bucket boundaries.
        """
        ts = parse_timestamp(ts_raw)
        if ts is not None:
            epoch_sec = int(ts.replace(tzinfo=timezone.utc).timestamp())
            return (epoch_sec // 10) * 10
        return None

    @staticmethod
    def _format_bucket_epoch(bucket_epoch: int) -> str:
        """10s-aligned bucket epoch → ``YYYY-MM-DD HH:MM:SS`` string."""
        return datetime.fromtimestamp(bucket_epoch, tz=timezone.utc).strftime(
            "%Y-%m-%d %H:%M:%S"
        )

    # 基于src ip和dst ip的生成聚合结果
    @staticmethod
    async def generate_aggregate_result(
        trace_index: dict[str, dict[str, list]],
        diagnosis_config=None,
    ) -> tuple[
        list[SrcDstAggregatedEventDataclass],
        dict[tuple[str, str, str], str],
        list[TimeWindowAggregatedEventDataclass],
        set[str],
    ]:
        """Backward-compatible 4-tuple wrapper over ``_aggregate_three_way``.

        The field table is produced by the same one-slice parallel pass but
        only surfaced via ``_aggregate_three_way`` (the ``run()`` path).
        """
        results, agg_map, tw, anom_tids, _field_table = (
            await KVCacheLogParseWorker._aggregate_three_way(
                trace_index, diagnosis_config
            )
        )
        return results, agg_map, tw, anom_tids

    @staticmethod
    def _aggregate_polars(
        df_trace,
        threshold_ms: float,
        log_file_id: str = "",
    ) -> tuple[
        list[SrcDstAggregatedEventDataclass],
        dict[tuple[str, str, str], str],
        list[TimeWindowAggregatedEventDataclass],
        set[str],
    ]:
        """Polars aggregation for src_dst / time_window / anomalous traces (T3).

        One ``group_by`` pass over the per-trace ``df_trace`` (T2 contract,
        31 TRACE_COLUMNS, one row/trace); no spawn/pickle/sharding.

        Semantics:
        - anomaly mask ``(total_ms >= threshold_ms) | (status_code != 0)``
          (status_code null → not anomalous by status).
        - ``op_key`` 直接消费 df_trace 的 ``op_key`` 列（T1 列式投影已按
          ``"SET" if "SET" in op.upper() else "GET"`` 计算）。
        - ``bucket_str`` 复刻 ``_format_bucket_epoch``（10s-aligned epoch →
          ``YYYY-MM-DD HH:MM:SS``）；``bucket_epoch=None`` → ``""``。
        - p99 必须 ``quantile(0.99, interpolation="linear")`` —— polars 默认
          ``nearest`` 会偏差 ~1%（旧 numpy 参考实现是 ``np.percentile`` 默认
          linear）。
        - ``first_log`` = 组内首个非空 log_id（df_trace 行序 = 参考实现的
          entries 插入序）。

        Returns the legacy aggregate 4-tuple shape:
          (src_dst_results, src_dst_to_agg_id_map, time_window_results,
           anomalous_tids)
        """
        import polars as pl

        # ── anomaly mask（单 trace 阈值, 与旧 worker 首遍一致）─────────
        anomaly = (pl.col("total_ms") >= threshold_ms) | (
            pl.col("status_code").is_not_null() & (pl.col("status_code") != 0)
        )
        anomaly_i64 = anomaly.cast(pl.Int64)

        anomalous_tids: set[str] = set(df_trace.filter(anomaly)["tid"].to_list())

        # ── src_dst: group by (src, dst, op_key) ──────────────────────
        sd = df_trace.group_by(["src", "dst", "op_key"]).agg(
            pl.len().alias("cnt"),
            anomaly_i64.sum().alias("anomaly_sum"),
            pl.col("log_id").drop_nulls().first().alias("first_log"),
        )
        src_dst_results: list[SrcDstAggregatedEventDataclass] = []
        src_dst_to_agg_id_map: dict[tuple[str, str, str], str] = {}
        for r in sd.iter_rows(named=True):
            agg_id = str(uuid.uuid4())
            sd_key = (r["src"], r["dst"], r["op_key"])
            src_dst_to_agg_id_map[sd_key] = agg_id
            src_dst_results.append(
                SrcDstAggregatedEventDataclass(
                    id=agg_id,
                    src_ip=r["src"],
                    dst_ip=r["dst"],
                    log_id=log_file_id or r["first_log"] or "",
                    operation=r["op_key"],
                    log_parse_result_cnt=int(r["cnt"]),
                    anomaly_cnt=int(r["anomaly_sum"]),
                    anomaly_log_parse_result_cnt=0,
                )
            )

        # ── time_window: group by (bucket_str, src, dst) ──────────────
        # bucket_epoch 已是 10s-aligned 秒级 epoch（columnar._bucket_epoch_10s
        # 返回 ``(epoch_sec // 10) * 10``），直接格式化即 _format_bucket_epoch。
        df = df_trace.with_columns(
            pl.when(pl.col("bucket_epoch").is_not_null())
            .then(
                (pl.col("bucket_epoch").cast(pl.Int64) * 1000)
                .cast(pl.Datetime("ms"))
                .dt.replace_time_zone("UTC")
                .dt.strftime("%Y-%m-%d %H:%M:%S")
            )
            .otherwise(pl.lit(""))
            .alias("bucket_str")
        )
        tw = df.group_by(["bucket_str", "src", "dst"]).agg(
            pl.len().alias("cnt"),
            anomaly_i64.sum().alias("anomaly_sum"),
            pl.col("log_id").drop_nulls().first().alias("first_log"),
            pl.col("total_ms").mean().alias("ave_total_latency"),
            pl.col("total_ms").sum().alias("latency_sum"),
            pl.col("total_ms").min().alias("min_total_latency"),
            pl.col("total_ms").max().alias("max_total_latency"),
            pl.col("total_ms")
            .quantile(0.95, interpolation="linear")
            .alias("p95_total_latency"),
            pl.col("total_ms")
            .quantile(0.99, interpolation="linear")
            .alias("p99_total_latency"),
        )
        time_window_results: list[TimeWindowAggregatedEventDataclass] = []
        for r in tw.iter_rows(named=True):
            time_window_results.append(
                TimeWindowAggregatedEventDataclass(
                    id=str(uuid.uuid4()),
                    kb_id="",
                    log_id=log_file_id or r["first_log"] or "",
                    time_bucket=r["bucket_str"],
                    src_ip=r["src"],
                    dst_ip=r["dst"],
                    log_parse_result_cnt=int(r["cnt"]),
                    anomaly_cnt=int(r["anomaly_sum"]),
                    ave_total_latency=(
                        float(r["ave_total_latency"])
                        if r["ave_total_latency"] is not None
                        else None
                    ),
                    latency_sum=(
                        float(r["latency_sum"])
                        if r["latency_sum"] is not None
                        else None
                    ),
                    min_total_latency=(
                        float(r["min_total_latency"])
                        if r["min_total_latency"] is not None
                        else None
                    ),
                    max_total_latency=(
                        float(r["max_total_latency"])
                        if r["max_total_latency"] is not None
                        else None
                    ),
                    p95_total_latency=(
                        float(r["p95_total_latency"])
                        if r["p95_total_latency"] is not None
                        else None
                    ),
                    p99_total_latency=(
                        float(r["p99_total_latency"])
                        if r["p99_total_latency"] is not None
                        else None
                    ),
                )
            )

        logger.info(
            "[AGGREGATE][polars] sd_groups=%d tw_groups=%d anomalous=%d "
            "threshold_ms=%.1f",
            len(src_dst_results),
            len(time_window_results),
            len(anomalous_tids),
            threshold_ms,
        )
        return (
            src_dst_results,
            src_dst_to_agg_id_map,
            time_window_results,
            anomalous_tids,
        )

    @staticmethod
    async def _aggregate_three_way(
        trace_index: Any,
        diagnosis_config=None,
        log_file_id: str = "",
    ) -> tuple[
        list[SrcDstAggregatedEventDataclass],
        dict[tuple[str, str, str], str],
        list[TimeWindowAggregatedEventDataclass],
        set[str],
        Any,
    ]:
        """Aggregate src_dst / time_window / anomalous traces (T3, polars).

        列式路径（唯一, WITTY_UB_SCAN_COLUMNS=1）: *trace_index* 是
        ``parse_log`` 返回的 df_trace（polars DataFrame）→ 交给
        ``_aggregate_polars`` 单次聚合。第 5 位契约: df_trace 本身（T4/T5
        接手消费）。T7 已删除 numpy ``_worker_process_shard`` +
        ``_merge_and_finalize`` 兜底。
        """
        # ── config ──────────────────────────────────────────────────
        threshold_ms = 5.0
        if diagnosis_config is not None:
            threshold_ms = float(
                getattr(diagnosis_config, "total_p99_threshold_ms", 5.0) or 5.0
            )

        _t_agg_start = time.perf_counter()
        results, agg_map, tw, anom_tids = (
            KVCacheLogParseWorker._aggregate_polars(
                trace_index, threshold_ms, log_file_id
            )
        )
        logger.info(
            "[PERF][AGG] polars traces=%d sd=%d tw=%d anom=%d total=%dms",
            trace_index.height,
            len(results),
            len(tw),
            len(anom_tids),
            (time.perf_counter() - _t_agg_start) * 1000,
        )
        return results, agg_map, tw, anom_tids, trace_index

    @staticmethod
    def _build_anomalous_detail_rows(
        trace_index: Any,
        anomalous_tids: set[str],
        kb_id: str = "",
        log_file_id: str = "",
    ) -> list[LogParseResultDataclass]:
        """Construct LogParseResultDataclass rows for anomalous traces only.

        T5/T7（列式路径, 唯一）: *trace_index* 是 ``parse_log`` 返回的
        df_trace（polars DataFrame, T2/T3 契约）→ 按 ``tid ∈ anomalous_tids``
        过滤 → 每行 ``to_dict()`` → ``_make_field_row`` 物化
        （``_make_field_row`` 本身不变）。df_trace 列名 == 平铺 dict 键名
        （TRACE_COLUMNS 冻结契约，T2 parity 测试逐列验证），无需列名映射；
        src/dst 已是 ""（T2 fill_null），``_make_field_row`` 的 ``or None``
        归一化把 "" → None，与平铺 dict 路径语义一致。所有返回行
        ``is_anomalous=True``、``aggregated_event_id=""``。
        """
        rows: list[LogParseResultDataclass] = []

        if anomalous_tids:
            import polars as pl

            created_at = _utc_now_str()
            frame = trace_index.filter(pl.col("tid").is_in(anomalous_tids))
            # 拷贝 yuanrong 字段（df_trace 已含全量 26 列）
            from latency.schemas.log import YUANRONG_METRIC_FIELDS
            yuanrong_fields = list(YUANRONG_METRIC_FIELDS)
            for flat in frame.to_dicts():
                row = KVCacheLogParseWorker._make_field_row(
                    flat,
                    log_file_id,
                    created_at=created_at,
                    is_anomalous=True,
                )
                for field in yuanrong_fields:
                    val = flat.get(field)
                    if val is not None:
                        setattr(row, field, val)
                rows.append(row)
        logger.info(
            "[BUILD_DETAIL] anomalous_tids=%d rows_built=%d log_file_id=%s",
            len(anomalous_tids),
            len(rows),
            log_file_id or "(unset)",
        )
        return rows

    # 存库
    @staticmethod
    async def store_result(
        anomalous_detail_rows: list[LogParseResultDataclass],
        src_dst_aggregated_events: list[SrcDstAggregatedEventDataclass],
        time_window_aggregated_events: list[TimeWindowAggregatedEventDataclass] | None = None,
        kb_id: str = "",
    ) -> bool:
        """存库

        三表（log_parse_result / src_dst_aggregated_event / time_window_aggregated）
        各自独立写，asyncio.gather 并行（无表间依赖，pool_size 10 可容纳并行 COPY）。
        单表失败仅记日志并置 success=False，不阻塞其他表；bucket×4 由 run() 的
        _store_bucket_stats_degraded 单独写（降级语义，不入 gather）。
        anomalous_event/anomalous_event_chain 表保留但不再由 parse 写入（detect 已删）。
        """
        import time as _time

        if time_window_aggregated_events:
            for event in time_window_aggregated_events:
                event.kb_id = kb_id

        async def _store_detail() -> None:
            if not anomalous_detail_rows:
                return
            stored = await LogParseResultPGManager.add_log_parse_results(
                anomalous_detail_rows
            )
            if not stored:
                raise RuntimeError("Failed to batch insert anomalous log parse results")

        async def _store_src_dst() -> int:
            if not src_dst_aggregated_events:
                return 0
            for event in src_dst_aggregated_events:
                event.kb_id = kb_id
            await SrcDstAggregatedEventPGManager.add_aggregated_events(
                src_dst_aggregated_events
            )
            return len(src_dst_aggregated_events)

        async def _store_time_window() -> int:
            if not time_window_aggregated_events:
                return 0
            await TimeWindowAggregatedEventPGManager.add_events(
                time_window_aggregated_events
            )
            return len(time_window_aggregated_events)

        t_store_start = _time.perf_counter()
        results = await asyncio.gather(
            _store_detail(),
            _store_src_dst(),
            _store_time_window(),
            return_exceptions=True,
        )
        t_store_elapsed = _time.perf_counter() - t_store_start

        success = True
        num_aggregate_rows = 0
        for name, outcome in zip(
            ("log_parse_result", "src_dst_aggregated_event", "time_window_aggregated"),
            results,
        ):
            if isinstance(outcome, BaseException):
                logger.error("Failed to store %s: %s", name, outcome)
                success = False
            elif name != "log_parse_result":
                num_aggregate_rows += outcome or 0

        logger.info(
            "[STORE] detail_rows=%d store_elapsed=%.1fs aggregate_rows=%d",
            len(anomalous_detail_rows),
            t_store_elapsed,
            num_aggregate_rows,
        )

        return success

    @staticmethod
    async def _store_bucket_stats_degraded(
        log_id: str,
        kb_id: str,
        rows: Sequence[Any],
        task_id: str | None = None,
        tables=None,
    ) -> dict[int, int] | None:
        """Write 4 latency_bucket_* tables from df_trace, degrading on failure.

        T7: ``rows`` 唯一来源是 df_trace（polars DataFrame, T2/T3 产物）→
        ``compute_and_store_bucket_stats_from_frame``（纯 polars 选代表行）。
        materializer = ``_make_field_row`` 只对选中的代表行构造 dataclass
        （~300 个），其余行不物化。numpy 版 ``compute_and_store_bucket_stats``
        已删。非 df_trace 输入（legacy 平铺 dict）直接降级返回 None。

        ``compute_and_store_bucket_stats_from_frame`` 自己打
        ``[parse_log] Bucket stats:`` 进度点并在任何阶段失败时 re-raise；
        本包装捕获并仅记日志，保证桶统计失败永不阻塞主解析/落库。Returns
        ``{granularity: rows written}`` 或 ``None``（降级）。
        """
        if not (hasattr(rows, "height") and hasattr(rows, "columns")):
            logger.warning(
                "[run] Bucket stats skipped: expected df_trace (polars), got %s",
                type(rows).__name__,
            )
            return None

        materializer = functools.partial(
            KVCacheLogParseWorker._make_field_row,
            log_file_id=log_id,
            created_at=_utc_now_str(),
        )
        try:
            return await compute_and_store_bucket_stats_from_frame(
                df_trace=rows,
                log_id=log_id,
                kb_id=kb_id,
                task_id=task_id or None,
                tables=tables,
                materializer=materializer,
            )
        except Exception as e:
            logger.exception("[run] Bucket stats failed, degraded: %s", e)
            return None

    @staticmethod
    async def run(task_id: str, log_dir: str | None = None) -> bool:
        """运行任务"""
        try:
            task = await TaskPGManager.get_task_by_task_id(task_id)
            if not task:
                logger.error(f"Task {task_id} not found")
                return False
            
            await TaskPGManager.update_task(
                task_id, {"status": TaskStatusEnum.RUNNING.value}
            )
            # 平滑进度: 权重化/单调/限流上报(替换固定 5/20/40/70/100 上报点)。
            # 阶段注册表+权重表在 latency/common/stage_progress.py, 与 run() 解耦,
            # T3/T5 重构聚合/明细段时可调整阶段名/权重。
            from latency.common.stage_progress import StageProgress

            progress = StageProgress(task_id)
            await progress.report("scan", 0.0, detail="task started")

            # 从 TaskHandler 获取解析配置
            from latency.task.task_handler import TaskHandler
            parse_config = TaskHandler.get_task_config(task_id)
            if parse_config:
                logger.info(f"[Task {task_id}] Using parse config: {parse_config}")

            # 直接使用 task.op_id 作为 log_id，parse_log 内部会获取 log_file 信息
            t_run_start = time.perf_counter()
            # 平滑扫描子进度: 每文件组完成上报 scan 比例, 避免扫描期进度条冻结
            async def _scan_progress(fraction: float) -> None:
                await progress.report("scan", fraction)

            trace_index = await KVCacheLogParseWorker.parse_log(
                task.op_id,
                parse_config,
                log_dir=log_dir or "",
                task_id=task_id,
                scan_progress_cb=_scan_progress,
            )
            t_parse = time.perf_counter() - t_run_start

            if trace_index is None or _trace_row_count(trace_index) == 0:
                await BaseWorker.report(task.id, "解析失败：未在路径中识别到日志信息", 100.0)
                await TaskPGManager.update_task(
                    task_id, {"status": TaskStatusEnum.FAILED_PENDING_REMOVE.value}
                )
                await LogFilePGManager.update_log_file(
                    task.op_id, {"parse_status": TaskStatusEnum.FAILED.value}
                )
                return False

            trace_rows = _trace_row_count(trace_index)
            await progress.report("scan", 1.0)
            await progress.stage_log("scan", f"rows={trace_rows}", elapsed_ms=t_parse * 1000)
            await BaseWorker.report(
                task.id,
                f"[perf][parse.results] rows={trace_rows}",
                0.0,
            )

            # 检查任务是否被取消
            task = await TaskPGManager.get_task_by_task_id(task_id)
            if not task or task.status == TaskStatusEnum.CANCELLED:
                logger.warning(f"任务 {task_id} 已被取消或不存在，停止执行")
                return False

            # 获取 kb_id 用于后续更新知识库统计
            log_file = await LogFilePGManager.get_log_file_by_log_file_id(task.op_id)
            kb_id = log_file.kb_id if log_file else None

            # 解析聚合阈值配置（异常判定 = 聚合侧单 trace 阈值）
            analyzer_config = None
            if kb_id:
                from latency.database.managers.diagnosis_config import DiagnosisConfigPGManager

                analyzer_config = (
                    await DiagnosisConfigPGManager.get_or_create(kb_id)
                ).log_analyzer_params

            # 检查任务是否被取消
            task = await TaskPGManager.get_task_by_task_id(task_id)
            if not task or task.status == TaskStatusEnum.CANCELLED:
                logger.warning(f"任务 {task_id} 已被取消或不存在，停止执行")
                return False

            # 生成聚合事件（异常判定 = 聚合侧单 trace 阈值）
            t_agg_start = time.perf_counter()
            (
                src_dst_aggregated_events,
                src_dst_to_agg_id_map,
                time_window_aggregated_events,
                anomalous_tids,
                df_trace,
            ) = await KVCacheLogParseWorker._aggregate_three_way(
                trace_index, analyzer_config, log_file_id=task.op_id
            )
            t_agg = time.perf_counter() - t_agg_start
            await progress.report("aggregate", 1.0)
            await progress.stage_log(
                "aggregate",
                f"sd={len(src_dst_aggregated_events)} tw={len(time_window_aggregated_events)} anom={len(anomalous_tids)}",
                elapsed_ms=t_agg * 1000,
            )
            await BaseWorker.report(
                task.id,
                (
                    "[perf][aggregate.summary] "
                    f"results={trace_rows}, endpoints={len(src_dst_aggregated_events)}, "
                    f"time_windows={len(time_window_aggregated_events)}, time={t_agg:.3f}s"
                ),
                t_agg,
            )
            logger.info(
                "[AGGREGATE] df_trace=%d",
                _trace_row_count(df_trace),
            )

            # 检查任务是否被取消
            task = await TaskPGManager.get_task_by_task_id(task_id)
            if not task or task.status == TaskStatusEnum.CANCELLED:
                logger.warning(f"任务 {task_id} 已被取消或不存在，停止执行")
                return False

            # ── 内存缓存聚合事件（API 立即可用） ──────────────────
            from latency.common.aggregate_cache import (
                set_aggregated_events,
                set_time_window_events,
            )
            log_file_id = task.op_id
            # 设置 kb_id 后缓存，后续 API 可按 kb_id 查询
            for event in time_window_aggregated_events:
                event.kb_id = kb_id or ""
            set_aggregated_events(log_file_id, src_dst_aggregated_events, kb_id=kb_id or "")
            set_time_window_events(log_file_id, time_window_aggregated_events)

            # ── 明细行：yuanrong 分段时延仅对 top1000 + 异常 trace 子集计算（T5/T9）。
            #    _yuanrong_from_grouped 从全量 347k 行延后到 ~(1K+anomalous) 行子集，
            #    5 遍 with_columns 开销从 347k×5 降到 ~ (1K+anomalous)×5。
            import polars as pl
            from latency.parse.parallel_scanner.trace_frame import _yuanrong_from_grouped
            from latency.schemas.log import YUANRONG_METRIC_FIELDS

            top1000_tids: set[str] = set()
            try:
                top1000_tids = set(
                    trace_index.sort("total_latency", descending=True)
                    .head(1000)["tid"]
                    .to_list()
                )
            except Exception:
                logger.warning("[yuanrong] top1000 tid selection failed", exc_info=True)

            # 异常 trace 如果在 top1000 中：top1000 行标 is_anomalous，
            # 不再单独构建异常行（避免同一 trace 在 log_parse_result 存两行）。
            anomalous_only_tids: set[str] = anomalous_tids - top1000_tids
            if anomalous_only_tids:
                logger.info(
                    "[yuanrong] %d anomalous traces outside top1000, "
                    "will build separate rows",
                    len(anomalous_only_tids),
                )

            all_detail_tids: set[str] = top1000_tids | anomalous_tids
            if all_detail_tids:
                detail_subset = trace_index.filter(
                    pl.col("tid").is_in(all_detail_tids)
                )
                detail_subset = _yuanrong_from_grouped(detail_subset)

                if anomalous_only_tids:
                    detail_rows: list[LogParseResultDataclass] = (
                        KVCacheLogParseWorker._build_anomalous_detail_rows(
                            detail_subset,
                            anomalous_only_tids,
                            kb_id=kb_id or "",
                            log_file_id=log_file_id,
                        )
                    )
                else:
                    detail_rows = []

                yuanrong_fields = list(YUANRONG_METRIC_FIELDS)
                try:
                    top1000_df = detail_subset.filter(
                        pl.col("tid").is_in(top1000_tids)
                    ).sort("total_latency", descending=True)
                    if top1000_df.height > 0:
                        created_at = _utc_now_str()
                        top1000_rows = []
                        for flat in top1000_df.to_dicts():
                            row = KVCacheLogParseWorker._make_field_row(
                                flat, log_file_id=log_file_id, created_at=created_at,
                                is_anomalous=flat["tid"] in anomalous_tids,
                            )
                            for field in yuanrong_fields:
                                val = flat.get(field)
                                if val is not None:
                                    setattr(row, field, val)
                            top1000_rows.append(row)
                        detail_rows = top1000_rows + detail_rows
                        logger.info(
                            "[yuanrong] top%d detail rows built + %d anomalous-only, "
                            "merged into detail_rows",
                            len(top1000_rows),
                            len(detail_rows) - len(top1000_rows),
                        )
                except Exception:
                    logger.warning(
                        "[yuanrong] top1000 detail build failed, skipping",
                        exc_info=True,
                    )
            else:
                detail_rows = []
                logger.info("[yuanrong] no detail tids (top1000=%d anomalous=%d), skipped",
                           len(top1000_tids), len(anomalous_tids))
            await progress.report("detail", 1.0)
            await progress.stage_log("detail", f"rows={len(detail_rows)}")

            # 回填 aggregated_event_id：metrics 行已带统一取源链
            # （URMA→RemotePull→""）解析出的 src/dst/op，与聚合一致，经
            # agg_id_map 写入明细行，保持钻取链路。
            if detail_rows:
                for row in detail_rows:
                    op = (row.operation or "").strip().upper()
                    op_key = "SET" if "SET" in op else "GET"
                    row.aggregated_event_id = src_dst_to_agg_id_map.get(
                        (row.src_ip or "", row.dst_ip or "", op_key), ""
                    )

            # ── 分位桶统计：df_trace（T4 frame 路径, polars 选代表行）→
            # 4 张 latency_bucket_* 表。仅对选中代表行构造 dataclass（~300），
            # 失败经降级包装仅记录日志，不阻塞明细/聚合落库。
            await KVCacheLogParseWorker._store_bucket_stats_degraded(
                log_id=task.op_id,
                kb_id=kb_id or "",
                rows=df_trace,
                task_id=task_id,
            )
            await progress.report("bucket", 1.0)
            await progress.stage_log("bucket", "latency_bucket_* written")

            # ── 异步持久化（聚合事件已在内存缓存中，API 不阻塞）────
            t_store_start = time.perf_counter()
            stored = await KVCacheLogParseWorker.store_result(
                anomalous_detail_rows=detail_rows,
                src_dst_aggregated_events=src_dst_aggregated_events,
                time_window_aggregated_events=time_window_aggregated_events,
                kb_id=kb_id or "",
            )
            t_store = time.perf_counter() - t_store_start
            await progress.report("store", 1.0)
            await progress.stage_log("store", f"stored={stored}", elapsed_ms=t_store * 1000)
            await BaseWorker.report(
                task.id,
                (
                    "[perf][store.summary] "
                    f"detail_rows={len(detail_rows)}, "
                    f"aggregated={len(src_dst_aggregated_events)}, "
                    f"stored={stored}, time={t_store:.3f}s"
                ),
                t_store,
            )
            
            if not stored:
                logger.error(f"Task {task_id} store failed, marking task as failed")
                await TaskPGManager.update_task(
                    task_id, {"status": TaskStatusEnum.FAILED_PENDING_REMOVE.value}
                )
                await LogFilePGManager.update_log_file(
                    task.op_id, {"parse_status": TaskStatusEnum.FAILED.value}
                )
                await BaseWorker.report(task.id, "Task failed: store to DB unsuccessful", 100.0)
                return False

            await LogFilePGManager.update_log_file(
                task.op_id, {"anomalous_count": len(anomalous_tids)}
            )
            
            # 更新关联的知识库统计
            if kb_id:
                await LogKnowledgePGManager.update_log_kb(
                    kb_id, {"anomalous_count": len(anomalous_tids)}
                )
            
            await TaskPGManager.update_task(
                task_id, {"status": TaskStatusEnum.SUCCESSFUL_PENDING_REMOVE.value}
            )
            await LogFilePGManager.update_log_file(
                task.op_id, {"parse_status": TaskStatusEnum.SUCCESSFUL.value}
            )
            await BaseWorker.report(task.id, "Task completed successfully", 100.0)

            # 全流程耗时汇总
            t_total = t_parse + t_agg + t_store
            pct_p = t_parse / t_total * 100
            pct_a = t_agg / t_total * 100
            pct_s = t_store / t_total * 100
            logger.info(
                f"============================================================\n"
                f"=== [TASK TIMING] Total: {t_total:.1f}s ===\n"
                f"  [1] Parse log:       {t_parse:7.1f}s ({pct_p:5.1f}%)\n"
                f"  [2] Aggregate result:{t_agg:7.1f}s ({pct_a:5.1f}%)\n"
                f"  [3] Store to DB:     {t_store:7.1f}s ({pct_s:5.1f}%)\n"
                f"============================================================"
            )
            await BaseWorker.report(task.id, f"[TASK] Parse log: {t_parse:.1f}s ({pct_p:.1f}%)", t_parse)
            await BaseWorker.report(task.id, f"[TASK] Aggregate result: {t_agg:.1f}s ({pct_a:.1f}%)", t_agg)
            await BaseWorker.report(task.id, f"[TASK] Store to DB: {t_store:.1f}s ({pct_s:.1f}%)", t_store)
            await BaseWorker.report(task.id, f"[TASK] Total: {t_total:.1f}s", 0.0)
            return True
        except Exception as e:
            logger.exception(f"Task {task_id} failed: {e}")
            await TaskPGManager.update_task(
                task_id, {"status": TaskStatusEnum.FAILED_PENDING_REMOVE.value}
            )
            return False

    @staticmethod
    async def stop(task_id: str) -> str | None:
        """停止任务"""
        task = await TaskPGManager.get_task_by_task_id(task_id)
        if not task:
            return None
        if task.status in [TaskStatusEnum.PENDING, TaskStatusEnum.RUNNING]:
            await LogParseResultPGManager.update_log_parse_results_existed_status_by_log_id(
                task.op_id, existed_status=0
            )
            await AnomalousEventPGManager.update_anomalous_events_existed_status_by_log_id(
                task.op_id, existed_status=0
            )
            await AnomalousEventChainPGManager.update_event_chains_existed_status_by_log_id(
                task.op_id, existed_status=0
            )
            await SrcDstAggregatedEventPGManager.update_aggregated_events_existed_status_by_log_id(
                task.op_id, existed_status=0
            )
            await TaskReportPGManager.update_task_reports_existed_status_by_task_id(
                task_id, existed_status=0
            )
            await TaskPGManager.update_task(
                task_id, {"status": TaskStatusEnum.CANCELLED.value}
            )
            return task_id
        return None

    @staticmethod
    async def delete(task_id: str) -> str:
        """删除任务"""
        task = await TaskPGManager.get_task_by_task_id(task_id)
        if not task:
            return ""
        
        log_id = task.op_id
        
        all_tasks = await TaskPGManager.list_tasks_by_op_id(log_id)
        same_type_tasks = [t for t in all_tasks if t.task_type == task.task_type]
        
        if len(same_type_tasks) == 1:
            logger.info(f"[KVCacheLogParseWorker] 删除任务 {task_id} 时清理 log_id={log_id} 的所有数据")
            await LogParseResultPGManager.delete_log_parse_results_by_log_id(log_id)
            await AnomalousEventPGManager.delete_anomalous_events_by_log_id(log_id)
            await AnomalousEventChainPGManager.delete_event_chains_by_log_id(log_id)
            await SrcDstAggregatedEventPGManager.delete_aggregated_events_by_log_id(log_id)
            await LogFailureEventPGManager.delete_log_failure_events_by_log_id(log_id)
            await LogFailureEventPGManager.delete_trace_failure_events_by_log_id(log_id)
        else:
            logger.info(f"[KVCacheLogParseWorker] log_id={log_id} 还有其他同类任务，不清理数据")
        
        return task_id

