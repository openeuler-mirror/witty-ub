import asyncio
import logging
import os
from datetime import datetime, timezone

import time
import uuid
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any, Awaitable, Callable, Optional, Sequence
from latency.schemas.log import (
    LogParseResultDataclass,
    SrcDstAggregatedEventDataclass,
    TimeWindowAggregatedEventDataclass,
)
from latency.schemas.parse_config import ParseConfig
from latency.ENUM.task import TaskStatusEnum, TaskTypeEnum
from latency.config.config import Config
from latency.parse import (
    SdkAccessLogParser,
    ClientInfoParser,
    WorkerAccessLogParser,
    WorkerInfoParser,
)
from latency.parse.labels import (
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
    CLIENT_RPC_LABEL,
    TIMED_LABELS,
)
from latency.ENUM.ds_log import EntryType, TupleField
from latency.parse.parallel_scanner import ParallelFileScanner
from latency.parse.trace_frames import TraceFrames, detach_trace_strings
from latency.parse.parallel_scanner.trace_frame import (
    build_trace_frame,
    build_trace_frame_light,
    detail_tids_from,
    deterministic_enabled,
)
from latency.ENUM.task import TaskSplitStrategy
from latency.database.managers.log_parse_result import LogParseResultPGManager
from latency.database.managers.log_parse_result_bulk import (
    LOG_PARSE_RESULT_SPEC,
    build_records,
    copy_dataframe,
)
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
from latency.task.worker.base import BaseWorker
from latency.common.stage_timing import as_stage_timer
from latency.bucket.statistics import (
    compute_and_store_bucket_stats_from_frame,
)



logger = logging.getLogger(__name__)


def _utc_now_str() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S.%f")


# ── P3 写库路径 ────────────────────────────────────────────────────────
# 明细写库与 4 张分桶表都走列式批量模块
#   (log_parse_result_bulk.copy_dataframe)：df_trace 片段 -> 列式归一化 -> COPY。
# 被取代的逐行物化写法（_make_field_row -> LogParseResultPGManager.
# add_log_parse_results 的明细写库分支）已删除；P3/P3b 用同一输入逐字段 + 142 组
# API 查询证明两条写法产出的行序与字段完全一致。


def _trace_row_count(trace_index: Any) -> int:
    """Unified row count: df_trace (polars, ``.height``) or flat-dict (``len``).

    T2/T5 列式路径下 *trace_index* 是 polars DataFrame；legacy（
    WITTY_UB_SCAN_COLUMNS=0）下是平铺 dict。run() 的进度/日志统一走这里。
    """
    if hasattr(trace_index, "height"):
        return int(trace_index.height)
    return len(trace_index)


def _diagnosis_threshold_ms(diagnosis_config) -> float:
    """时延异常阈值（ms），对齐 _aggregate_three_way 的读取语义。

    threshold 位于 ``log_analyzer_params.total_p99_threshold_ms``；缺省 5.0。
    parse_log 用它限定 build_trace_frame 的 yuanrong 明细子集，保证与
    run() 的 anomalous_tids 判定同阈值，__ 列对子集必然非空。
    """
    try:
        lp = getattr(diagnosis_config, "log_analyzer_params", None)
        if lp is not None:
            return float(getattr(lp, "total_p99_threshold_ms", 5.0) or 5.0)
    except Exception:
        pass
    return 5.0


def _merge_light_then_wide(light_rows, scan_ctx, threshold_ms: float, *, compact: bool = False):
    """轻列归并 → 定"需要算的 trace" → 第二次投影补宽列 → 拼回一份 df_trace。

    全量只算轻列（LIGHT_COLUMNS）；宽列只给 明细子集 ∪ 分桶代表行 算。
    从扫描缓存逐批补宽列，大输入按 trace 分区归并，不重读源日志。
    输出的列集与列序与旧的单次 40 列归并**逐列一致**（契约不变）。
    compact=True 时返回 TraceFrames，把宽列保留到明细/分桶消费时才按批展开。
    """
    from latency.parse.columns import TRACE_COLUMNS
    from latency.parse.parallel_scanner.scan_vector import materialize_wide
    import polars as pl

    trace_light = detach_trace_strings(build_trace_frame_light(light_rows))
    # group_by 产物不再引用逐行轻列载荷；在宽列投影前释放它。
    del light_rows
    needed = detail_tids_from(trace_light, threshold_ms, as_series=True)
    # Keep the small representative selection for bucket persistence, so the
    # all-trace sort/group selection runs only once per parse task.
    from latency.bucket.representatives import select_bucket_representatives
    representatives = select_bucket_representatives(trace_light)
    needed = pl.concat([needed, *(rows["tid"] for rows in representatives.values())]).unique()
    if needed.is_empty():
        return trace_light

    selected_rows = scan_ctx.light_rows.filter(
        pl.col("tid").is_in(needed.implode())
    ).select("__row")
    expected_rows = selected_rows.height
    if expected_rows > 262_144:
        from latency.parse.parallel_scanner.memory_scan import iter_wide
        from latency.parse.parallel_scanner.bounded_trace import build_trace_frame_batched

        wide_trace = build_trace_frame_batched(
            iter_wide(scan_ctx, needed, sparse=True, selected_rows=selected_rows),
            expected_rows,
            # Prefer fewer native reductions over small memory partitions.
            # Very large inputs still retain the compressed fallback.
            target_partition_rows=1_048_576,
            target_partition_bytes=256 * 1024 * 1024,
            compression_threshold_bytes=2 * 1024 * 1024 * 1024,
            complete_schema=True,
        )
        # Shared source lines can emit extra tids; retain their base metrics,
        # but only requested tids carry deferred yuanrong materials.
        wanted_mask = wide_trace["tid"].is_in(needed.implode())
        wide_trace = wide_trace.with_columns([
            pl.when(wanted_mask).then(pl.col(name)).alias(name)
            for name in wide_trace.columns if name.startswith("__")
        ])
    else:
        wide_rows = materialize_wide(scan_ctx, needed, selected_rows=selected_rows)
        # No later phase reads scanner source text or per-line row locators.
        scan_ctx.lines = None
        scan_ctx.light_rows = None
        scan_ctx.info_cache = None
        all_selected = wide_rows["tid"].is_in(needed.implode()).all()
        wide_trace = build_trace_frame(
            wide_rows, threshold_ms=None if all_selected else threshold_ms, detail_tids=needed
        )
        wide_trace = detach_trace_strings(wide_trace)
        del wide_rows

    del selected_rows

    if compact:
        details = TraceFrames.from_frames(trace_light, wide_trace)
        details.bucket_representatives = representatives
        return details

    merge_cols = [
        name
        for name in wide_trace.columns
        if name != "tid" and name not in trace_light.columns
    ]
    if not merge_cols:
        del wide_trace
        return trace_light
    merged = trace_light.join(
        wide_trace.select(["tid", *merge_cols]),
        on="tid",
        how="left",
        coalesce=True,
    )
    del wide_trace
    # 列序回到旧契约：TRACE_COLUMNS 在前、``__`` 原材料在后
    order = [name for name in TRACE_COLUMNS if name in merged.columns]
    order += [name for name in merged.columns if name.startswith("__")]
    return merged.select(order)


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
    EntryType.CLIENT_RPC.value: CLIENT_RPC_LABEL,
}

# scan_scope 会作为 ProcessPool 参数复制到每个子进程。大型日志通常每条
# SDK 都有唯一 trace_id；传递百万级集合的序列化成本远高于直接扫描日志。
MAX_PROCESS_SCAN_SCOPE_TRACE_IDS = 50_000

# _resolve_snapshot 返回的全部时延字段(平铺 dict 中与 dataclass 同名的键)。
# 供 _make_field_row 从平铺 dict 挑出, 构造 LogParseResultDataclass
# （逐行参照实现，见 _build_field_table_rows）。
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


_ARCHIVE_EXTENSIONS = (".tar.gz", ".tgz", ".zip", ".rar")


def _map_to_original_path(
    preprocessed_path: str, log_dir: str, source_path: str | None
) -> str:
    """把预处理目录下的文件路径映射回用户可见的原始路径。

    - 无预处理（``source_path is None`` 或 ``source_path == log_dir``）：路径本身就是原始路径。
    - 源是目录：``source_path / relpath``。
    - 源是压缩包：``source_path(relpath)``，内部相对路径用括号标注。
    """
    if source_path is None or source_path == log_dir:
        return preprocessed_path
    rel = os.path.relpath(preprocessed_path, log_dir)
    lower = source_path.lower()
    if any(lower.endswith(ext) for ext in _ARCHIVE_EXTENSIONS):
        return f"{source_path}({rel})"
    return os.path.join(source_path, rel)


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
        if task.retry_times >= Config().get_config().task.task_retry_times:
            logger.warning(
                f"Task {task_id} retry count {task.retry_times} exceeded max retries {Config().get_config().task.task_retry_times}"
            )
            return False
        await BaseWorker.report(task.id, "Task reinitialized", 0.0)
        return True

    @staticmethod
    async def deinit(task_id: str) -> str:
        """析构任务"""
        return task_id

    @staticmethod
    def _new_parallel_scanner() -> ParallelFileScanner:
        task_config = Config().get_config().task
        return ParallelFileScanner(
            max_processes=min(
                os.cpu_count() or 1,
                task_config.parse_workers,
                max(1, task_config.cpu_limit // task_config.max_concurrent_tasks),
            ),
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
        stage_timer: Any = None,  # latency.common.stage_timing.StageTimer | None
        compact: bool = False,
    ) -> Any:
        """解析日志文件

        Args:
            log_id: 日志文件ID（数据库中的主键）
            parse_config: 解析配置
            log_dir: 日志目录路径（向后兼容，优先使用 log_id）
            task_id: 任务ID（用于上报分阶段耗时）
            scan_progress_cb: 可选扫描进度回调 ``async (fraction: float) -> None``，
                转发给 scanner.scan_all，使扫描阶段进度平滑前进；None 时无副作用。
            stage_timer: 可选 ``StageTimer``（``None`` → 空计时器，行为与本改造前
                完全一致）。本函数只登记两个阶段（CPU 也在这里读）：
                ``scan`` = 整段 ``scanner.scan_all``（detail = 文件数 / 扫描行数）、
                ``trace_frame`` = ``build_trace_frame`` 归并（detail = trace 行数）。
                报告由调用方（``run``）统一 ``emit``。
            compact: 任务内部保留轻列与明细宽列分离的 TraceFrames，避免全量铺宽列。
                默认 False 保持直接调用者的 DataFrame 返回契约。

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
        timer = as_stage_timer(stage_timer)
        t_scan_start = time.perf_counter()
        # [timing] scan = 读文件 + 行闸门 + 切列抽取 + 投影（整段 scan_all）
        with timer.stage("scan") as scan_scope:
            parsed = await scanner.scan_all(
                log_dir,
                all_parsers,
                parse_config,
                progress_cb=scan_progress_cb,
                light=True,
            )
            # 坏文件：解析侧已清洗或跳过并记账（后端 WARNING/INFO 日志）
            sanitized_files = parsed.pop("sanitized_files", None) or []
            skipped_files = parsed.pop("skipped_files", None) or []
            if sanitized_files:
                logger.info(
                    "[utf8] %d 个日志文件含非 UTF-8 字节已清洗: %s",
                    len(sanitized_files),
                    ", ".join(sanitized_files),
                )
            if skipped_files:
                logger.warning(
                    "[utf8] %d 个日志文件清洗失败已跳过: %s",
                    len(skipped_files),
                    ", ".join(f"{p}({r})" for p, r in skipped_files),
                )

            # T1 (polars rewrite): 列式输出已随 legacy 标签一并返回, 本任务暂不消费
            # （T2 用 build_trace_frame 从列重建 df_trace），弹出避免下游误读。
            column_rows = parsed.pop("columns", None)
            # 轻列扫描留下的现场（read 产物 + 路由）：定完子集后补算宽列用
            scan_ctx = parsed.pop("scan_ctx", None)
            if column_rows is not None:
                # 单进程列运算路径直接返回 DataFrame；多进程路径返回 {列名: [值]}。
                import polars as _pl

                if isinstance(column_rows, _pl.DataFrame):
                    n_rows = column_rows.height
                    # 轻列路径没有 _label（它是宽列）→ 这一行统计仅供参考，
                    # 行数本身在 scan_scope.detail 里照常有。
                    labels = (
                        column_rows["_label"].to_list()
                        if "_label" in column_rows.columns
                        else []
                    )
                else:
                    n_rows = len(column_rows.get("tid", []))
                    labels = column_rows.get("_label", [])
                logger.info("Columnar scan output: %d per-line rows", n_rows)
                # 从 column_rows 统计各 label 条目数（替代已删除的 {label:[tuple]}）
                from collections import Counter

                entry_counts = Counter(labels)
                scan_scope.detail = f"{scanner.metrics.total_files} 文件 / {n_rows} 行"

        t_scan = time.perf_counter() - t_scan_start

        if "trace_frame" in parsed:
            trace_index = parsed.pop("trace_frame")
            entry_counts = parsed.pop("entry_counts")
            del parsed
            total = trace_index.height
        elif column_rows is not None:
            # T2 (polars rewrite): 列式路径 —— 从列式行重建 df_trace
            # （pl.concat → group_by("tid") → 每 trace 一行，列 = TRACE_COLUMNS）。
            # yuanrong 26 项分段时延已内置在 build_trace_frame 中。
            # [timing] 归并从 scan 段里拆出来单独计时（原先被 t_scan 一起吞掉）。
            with timer.stage("trace_frame") as frame_scope:
                threshold_ms = _diagnosis_threshold_ms(diagnosis_config)
                if scan_ctx is not None:
                    # 轻列 → 定"需要算的 trace" → 从 read 产物补算宽列（不重读文件）
                    # pop 后调用期间只剩 helper 持有逐行轻列帧，使其能在
                    # group_by 完成后、宽列物化前真正释放。
                    light_rows_holder = [column_rows]
                    column_rows = None
                    trace_index = _merge_light_then_wide(
                        light_rows_holder.pop(), scan_ctx, threshold_ms, compact=compact
                    )
                else:
                    trace_index = build_trace_frame(
                        column_rows, threshold_ms=threshold_ms
                    )
                frame_scope.detail = f"{trace_index.height} 条 trace"
            del column_rows
            del scan_ctx
            del parsed
            logger.info("Released parsed entries (columnar path)")
            total = trace_index.height
        else:
            # T7: columnar 是唯一解析路径（legacy 平铺 dict 兜底已删）。走到这里
            # 说明扫描器没返回 "columns"，实测最常见的原因是**一个文件都没匹配到**
            # （日志目录为空，或文件名与 parse_config 的正则对不上）——先把现场写清楚。
            # 旧文案让人去设 WITTY_UB_SCAN_COLUMNS，而那个开关在 T7 之后已从代码里
            # 删掉（全仓只有这句报错和注释还提它），会把人带偏：2026-09-15 的
            # backend.log 里就有这样一条假线索。
            scanned_files = getattr(getattr(scanner, "metrics", None), "total_files", None)
            if skipped_files:
                source_path = log_file.file_path if log_id else None
                detail = "；".join(
                    f"{_map_to_original_path(p, log_dir, source_path)}（{r}）"
                    for p, r in skipped_files[:5]
                )
                raise RuntimeError(
                    f"扫描没有产出任何列式行：{len(skipped_files)} 个日志文件全部清洗失败"
                    f"——{detail}；log_dir={log_dir}"
                )
            raise RuntimeError(
                "扫描没有产出任何列式行（没有匹配到日志文件？）："
                f"已扫描文件数={scanned_files}，log_dir={log_dir}"
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
        # 支持三种场景：只有SDK、只有Worker、都有
        if sdk:
            snapshot["total_latency"] = sdk[0][TupleField.ELAPSED_US] / 1000.0
        elif worker:
            snapshot["total_latency"] = worker[0][TupleField.ELAPSED_US] / 1000.0
        else:
            snapshot["total_latency"] = None

        # c2w_urma_latency  ───────────────────────────────────────
        # 只有同时有SDK和Worker时才能计算C2W时延
        if sdk and worker:
            snapshot["c2w_urma_latency"] = (
                sdk[0][TupleField.ELAPSED_US]
                - worker[0][TupleField.ELAPSED_US]
            ) / 1000.0
        else:
            # 只有SDK或只有Worker，无法计算C2W
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

        Returns ``None`` when the trace must be skipped (no SDK/Worker entry, or the
        elapsed_us is missing/negative) — mirroring the aggregate's
        first pass so the two slices stay perfectly aligned.
        
        支持三种场景：
        1. 只有SDK access日志
        2. 只有Worker access日志
        3. 同时包含SDK和Worker access日志
        """
        sdk_entries = entries.get("SDK access parse", [])
        worker_entries = entries.get("Worker access parse", [])
        
        if sdk_entries:
            first = sdk_entries[0]
        elif worker_entries:
            first = worker_entries[0]
        else:
            return None
        
        elapsed_us = first[TupleField.ELAPSED_US]
        if elapsed_us is None or elapsed_us < 0:
            return None
        total_ms = elapsed_us / 1000.0
        # Resolve src/dst from downstream entries (URMA/RemotePull/RemoteWorker), not from
        # the SDK entry, which never carries SRC_ADDR/DST_ADDR. Fallback
        # chain: URMA -> RemotePull -> RemoteWorkerCost -> RemoteWorkerRpc -> empty.
        _urma = entries.get(URMA_LABEL, [])
        _pop = entries.get(REMOTE_PULL_LABEL, [])
        _rwc = entries.get(REMOTE_WORKER_COST_LABEL, [])
        _rwr = entries.get(REMOTE_WORKER_RPC_LABEL, [])
        if _urma:
            src = str(_urma[0][TupleField.SRC_ADDR] or "").strip() or ""
            dst = str(_urma[0][TupleField.DST_ADDR] or "").strip() or ""
        elif _pop:
            src = str(_pop[0][TupleField.SRC_ADDR] or "").strip() or ""
            dst = str(_pop[0][TupleField.DST_ADDR] or "").strip() or ""
        elif _rwc:
            src = str(_rwc[0][TupleField.SRC_ADDR] or "").strip() or ""
            dst = str(_rwc[0][TupleField.DST_ADDR] or "").strip() or ""
        elif _rwr:
            src = str(_rwr[0][TupleField.SRC_ADDR] or "").strip() or ""
            dst = str(_rwr[0][TupleField.DST_ADDR] or "").strip() or ""
        else:
            src = ""
            dst = ""
        op = (str(first[TupleField.OPERATION] or "")).strip().upper()
        # 对于Worker-only trace，operation可能是DS_POSIX_GET/CREATE/PUBLISH
        # 对于SDK trace，operation是DS_KV_CLIENT_GET/SET等
        # 统一映射到GET/SET分类
        op_key = "GET" if "GET" in op else "SET"
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
            # pod_ip 现在是一个列表（implode_unique 策略），需要处理列表类型
            pod_ips=(
                list(dict.fromkeys(
                    str(ip).strip()
                    for ip in flat["pod_ip"]
                    if ip is not None and str(ip).strip()
                )) or None
                if isinstance(flat.get("pod_ip"), list)
                else (
                    [str(flat["pod_ip"]).strip()]
                    if flat.get("pod_ip") and str(flat["pod_ip"]).strip()
                    else None
                )
            ),
            # cluster_name 现在也是一个列表（implode_unique 策略），需要处理列表类型
            cluster_name=(
                ", ".join(str(cn) for cn in flat["cluster_name"])
                if isinstance(flat.get("cluster_name"), list)
                else (str(flat["cluster_name"]) if flat.get("cluster_name") else None)
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
        materialize_anomaly_ids: bool = True,
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
        - 先计算 anomalous_tids（仅包含时延异常：total_ms >= threshold_ms）
        - 再在 df_trace 中添加 is_anomalous_int 列（标记每个trace是否在 anomalous_tids 中）
        - 聚合时统计 is_anomalous_int.sum()（确保 anomaly_cnt 与实际异常trace数量一致）
        - ``anomaly_cnt`` 总和 = ``len(anomalous_tids)``（严格等于）
        - 注意：状态码异常在通断故障部分处理，不影响时延故障部分
        - ``op_key`` 直接消费 df_trace 的 ``op_key`` 列（T1 列式投影已按
          ``"GET" if "GET" in op.upper() else "SET"`` 计算）。
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
        # 时延异常（仅用于时延故障部分）
        latency_anomaly = (pl.col("total_ms") >= threshold_ms)

        # anomalous_tids 只包含时延超过阈值的 trace（用于时延故障部分）
        # 状态码异常在通断故障部分处理，不影响时延故障部分
        anomalous_tids = df_trace.select("tid", "total_ms").filter(latency_anomaly)["tid"]
        if materialize_anomaly_ids:
            anomalous_tids = set(anomalous_tids.to_list())

        # 在 df_trace 中添加 is_anomalous 列，用于聚合统计。
        # T2 契约：df_trace 一行一个 trace、tid 唯一（实测 2,469,627 行 / 2,469,627 个
        # 不同 tid），故「tid 在 anomalous_tids 中」与「本行 total_ms >= threshold_ms
        # 且 tid 非空」逐行等价。原写法 ``pl.col("tid").is_in(<python set>)`` 要在
        # 247 万行上逐行做 Python 对象哈希比较（实测 0.147s），复用掩码后 0.005s。
        # （polars 1.44 的 is_in(Series) / is_in(Series.implode()) 实测无收益且已
        # deprecated，故不走那条路。）
        df_trace = df_trace.with_columns(
            (latency_anomaly & pl.col("tid").is_not_null())
            .fill_null(False)
            .cast(pl.Int64)
            .alias("is_anomalous_int")
        )

        # ── src_dst: group by (src, dst, op_key) ──────────────────────
        # maintain_order=True: 组输出行序 = 组内首次出现序（WITTY_UB_DETERMINISTIC
        # 默认开；显式设 0 回退 polars 默认的哈希序）。src_dst 表物理行序随之稳定。
        sd = df_trace.group_by(
            ["src", "dst", "op_key"], maintain_order=deterministic_enabled()
        ).agg(
            pl.len().alias("cnt"),
            pl.col("is_anomalous_int").sum().alias("anomaly_sum"),
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
                    anomaly_log_parse_result_cnt=int(r["anomaly_sum"]),
                )
            )

        # ── time_window: group by (bucket_epoch, src, dst, op_key) ────────────
        # bucket_epoch 已是 10s-aligned 秒级 epoch（columnar._bucket_epoch_10s
        # 返回 ``(epoch_sec // 10) * 10``），格式化即 _format_bucket_epoch。
        # 分组键用 bucket_epoch（Int64）而不是 bucket_str：分桶串与 bucket_epoch
        # 一一对应（null → ""），先在全部行上 strftime 再 group_by 是纯浪费——
        # 改成先 group_by、再对分组结果格式化，实测 0.770s → 0.055s
        # （本例 247 万行 / 19664 组，产物与改前 frame.equals() 为 True）。
        tw = df_trace.group_by(
            ["bucket_epoch", "src", "dst", "op_key"], maintain_order=deterministic_enabled()
        ).agg(
            pl.len().alias("cnt"),
            pl.col("is_anomalous_int").sum().alias("anomaly_sum"),
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
        tw = tw.with_columns(
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
        tw = tw.filter(pl.col("bucket_str") != "")
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
                    operation=r["op_key"],
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
        materialize_anomaly_ids: bool = True,
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
                trace_index, threshold_ms, log_file_id, materialize_anomaly_ids
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

        P3 起生产写库路径由 ``_build_detail_frame`` 直接产出列式 frame，不再逐行
        物化；本方法保留作为 golden / 单测的逐行参照实现（无生产调用点）。

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
            # 使用 iter_rows() 代替 to_dicts()，减少内存占用
            for flat in frame.iter_rows(named=True):
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

    @staticmethod
    def _detail_row_count(payload: Any) -> int:
        """明细载荷行数（列式路径 = polars DataFrame，回退路径 = dataclass 列表）。"""
        if payload is None:
            return 0
        if hasattr(payload, "height"):
            return int(payload.height)
        return len(payload)

    @staticmethod
    def _op_key_expr() -> Any:
        """复刻 op_key 归一化：含 'GET' -> 'GET'，其余（含 None/空串）-> 'SET'。

        与聚合侧 ``op_key``（columnar）及旧 ``run()`` 回填用的
        ``(row.operation or "").strip().upper()`` 同语义。
        """
        import polars as pl

        return (
            pl.when(
                pl.col("op")
                .fill_null("")
                .str.strip_chars()
                .str.to_uppercase()
                .str.contains("GET", literal=True)
            )
            .then(pl.lit("GET"))
            .otherwise(pl.lit("SET"))
        )

    @staticmethod
    def _build_detail_frame(
        detail_subset: Any,
        top1000_tids: set[str],
        anomalous_only_tids: Any,
        anomalous_tids: Any,
        src_dst_to_agg_id_map: dict | None = None,
        log_file_id: str = "",
        top1000_created_at: str | None = None,
        anomalous_created_at: str | None = None,
        threshold_ms: float | None = None,
        anomalous_only_count: int | None = None,
        aggregate_keys: Any = None,
        top_rows_sorted: bool = False,
        ordered_top_count: int | None = None,
    ) -> Any:
        """df_trace 片段 -> log_parse_result 待写 frame（P3 列式写库路径）。

        行序契约（前端分页在并列值上依赖物理行序，见 P3 报告 4.5）：
          1) 先 top1000（``tid in top1000_tids``），按 ``total_latency`` 降序；
          2) 再 anomalous-only（``tid in anomalous_only_tids``），保持 df_trace 行序。
        两段各取一次 ``created_at``（先 anomalous 后 top1000，与旧代码
        ``_utc_now_str()`` 的调用序一致）：``created_at`` 排序同样没有 tie-break，
        若两段共用一个时间戳，``created_at`` 排序的翻页结果会与现状不同。

        列 = df_trace 的列 + ``is_anomalous`` / ``aggregated_event_id`` /
        ``created_at`` / ``log_id``；列到目标表的映射、常量列（host 等 6 列恒
        NULL）与类型归一化由 ``LOG_PARSE_RESULT_SPEC`` 负责。
        """
        import polars as pl

        if threshold_ms is None:
            anomaly_expr = pl.col("tid").is_in(anomalous_tids)
            anomaly_only_expr = pl.col("tid").is_in(anomalous_only_tids)
            has_anomalous_only = bool(anomalous_only_tids)
        else:
            # 生产路径直接复用阈值表达式，避免把所有异常 tid
            # 再物化为 Python set（高异常率时这一份就可占用数百 MB）。
            anomaly_expr = (pl.col("total_ms") >= threshold_ms).fill_null(False)
            anomaly_only_expr = anomaly_expr & ~pl.col("tid").is_in(top1000_tids)
            has_anomalous_only = (
                anomalous_only_count > 0
                if anomalous_only_count is not None
                else bool(detail_subset.select(anomaly_only_expr.any()).item())
            )

        # created_at 取值顺序与旧路径逐字对齐：先 anomalous 后 top1000，且只有在
        # 真有 anomalous-only 行时才为异常段取（旧 _build_anomalous_detail_rows
        # 也是在 ``if anomalous_tids:`` 分支里才调 _utc_now_str()）。
        if anomalous_created_at is None:
            anomalous_created_at = _utc_now_str() if has_anomalous_only else None
        if top1000_created_at is None:
            top1000_created_at = _utc_now_str()
        if anomalous_created_at is None:
            # 无 anomalous-only 行：该段 0 行，取值不影响落库
            anomalous_created_at = top1000_created_at

        if ordered_top_count is not None:
            # The bounded iterator already selected and ordered every row. Mark
            # its top/anomaly boundary directly instead of filtering/copying all
            # metric columns twice and concatenating them back together.
            top_count = ordered_top_count
            if not 0 <= top_count <= detail_subset.height:
                raise ValueError("ordered_top_count outside detail batch")
            anomaly_count = detail_subset.height - top_count
            detail_frame = detail_subset.with_columns(
                anomaly_expr.alias("is_anomalous"),
                pl.when(pl.int_range(pl.len()) < top_count)
                .then(pl.lit(top1000_created_at)).otherwise(pl.lit(anomalous_created_at))
                .alias("created_at"),
            )
        else:
            empty = detail_subset.head(0)
            if top1000_tids:
                top_frame = detail_subset.filter(pl.col("tid").is_in(top1000_tids))
                if not top_rows_sorted:
                    top_frame = top_frame.sort("total_latency", descending=True)
                top_frame = (
                    top_frame.with_columns(
                        anomaly_expr.alias("is_anomalous"),
                        pl.lit(top1000_created_at).alias("created_at"),
                    )
                )
            else:
                top_frame = empty.with_columns(
                    pl.lit(False).alias("is_anomalous"),
                    pl.lit(top1000_created_at).alias("created_at"),
                )
            if has_anomalous_only:
                anomalous_frame = detail_subset.filter(
                    anomaly_only_expr
                ).with_columns(
                    pl.lit(True).alias("is_anomalous"),
                    pl.lit(anomalous_created_at).alias("created_at"),
                )
            else:
                anomalous_frame = empty.with_columns(
                    pl.lit(True).alias("is_anomalous"),
                    pl.lit(anomalous_created_at).alias("created_at"),
                )
            detail_frame = pl.concat([top_frame, anomalous_frame], how="vertical")
            top_count = top_frame.height
            anomaly_count = anomalous_frame.height

        # log_id：旧路径 ``log_file_id or flat.get("log_id", "")``
        if log_file_id:
            detail_frame = detail_frame.with_columns(
                pl.lit(log_file_id).alias("log_id")
            )

        agg_map = src_dst_to_agg_id_map or {}
        if agg_map:
            agg_keys = aggregate_keys if aggregate_keys is not None else pl.DataFrame(
                {
                    "_src_k": [key[0] for key in agg_map],
                    "_dst_k": [key[1] for key in agg_map],
                    "_op_k": [key[2] for key in agg_map],
                    "_agg_id": [value for value in agg_map.values()],
                },
                schema={
                    "_src_k": pl.String,
                    "_dst_k": pl.String,
                    "_op_k": pl.String,
                    "_agg_id": pl.String,
                },
            )
            detail_frame = (
                detail_frame.with_columns(
                    pl.col("src").fill_null("").alias("_src_k"),
                    pl.col("dst").fill_null("").alias("_dst_k"),
                    KVCacheLogParseWorker._op_key_expr().alias("_op_k"),
                )
                .join(
                    agg_keys, on=["_src_k", "_dst_k", "_op_k"],
                    how="left", maintain_order="left",
                )
                .with_columns(
                    pl.col("_agg_id").fill_null("").alias("aggregated_event_id")
                )
                .drop(["_src_k", "_dst_k", "_op_k", "_agg_id"])
            )
        else:
            detail_frame = detail_frame.with_columns(
                pl.lit("").alias("aggregated_event_id")
            )

        logger.info(
            "[yuanrong] detail frame built: top%d (total_latency desc) + "
            "anomalous-only %d = %d rows, agg_id map=%d",
            top_count,
            anomaly_count,
            detail_frame.height,
            len(agg_map),
        )
        return detail_frame

    @staticmethod
    def _build_detail_payload(
        detail_subset: Any,
        top1000_tids: set[str],
        anomalous_only_tids: Any,
        anomalous_tids: Any,
        src_dst_to_agg_id_map: dict | None = None,
        log_file_id: str = "",
        kb_id: str = "",
        threshold_ms: float | None = None,
        anomalous_only_count: int | None = None,
    ) -> Any:
        """明细待写载荷：列式 frame（``_build_detail_frame`` 的唯一产物）。

        行序（top1000 total_latency 降序 + anomalous-only）、``created_at``
        取法、``aggregated_event_id`` 回填口径与改动前的逐行写法逐字段一致。
        """
        return KVCacheLogParseWorker._build_detail_frame(
            detail_subset,
            top1000_tids=top1000_tids,
            anomalous_only_tids=anomalous_only_tids,
            anomalous_tids=anomalous_tids,
            src_dst_to_agg_id_map=src_dst_to_agg_id_map,
            log_file_id=log_file_id,
            threshold_ms=threshold_ms,
            anomalous_only_count=anomalous_only_count,
        )

    @staticmethod
    def _iter_detail_frames(
        trace_index: Any,
        top1000_tids: set[str],
        threshold_ms: float,
        src_dst_to_agg_id_map: dict,
        log_file_id: str,
        anomalous_only_count: int,
        batch_size: int = 100_000,
        trace_details: TraceFrames | None = None,
    ):
        """按 top1000 + anomalous-only 顺序物化有界明细帧。

        全量只保留窄行号索引；26 项 yuanrong 派生列和入库宽列每次
        最多存活 ``batch_size`` 行。原生计算每批 100K，Python COPY 转换
        每批最多 50K；所有批次共享一次 COPY。
        """
        import polars as pl
        from latency.parse.parallel_scanner.trace_frame import _yuanrong_from_grouped

        if batch_size < 1:
            raise ValueError("batch_size must be positive")

        index = trace_index.select(
            "tid", "total_ms", "total_latency"
        ).with_row_index("_row")
        anomaly_expr = (pl.col("total_ms") >= threshold_ms).fill_null(False)
        top_indices = (
            index.filter(pl.col("tid").is_in(top1000_tids))
            .sort("total_latency", descending=True)
            ["_row"]
        )
        anomaly_indices = index.filter(
            anomaly_expr & ~pl.col("tid").is_in(top1000_tids)
        )["_row"]
        top_count = len(top_indices)
        indices = pl.concat([top_indices, anomaly_indices])
        del index, top_indices, anomaly_indices
        expected_rows = len(top1000_tids) + anomalous_only_count
        if len(indices) != expected_rows:
            raise ValueError(f"Detail selection count mismatch: {len(indices)}/{expected_rows}")

        anomalous_created_at = (
            _utc_now_str() if anomalous_only_count else None
        )
        top_created_at = _utc_now_str()
        # Endpoint groups are shared by every detail batch. Build their lookup
        # once, including when anomaly volume spans hundreds of COPY batches.
        aggregate_keys = None
        if src_dst_to_agg_id_map:
            aggregate_keys = pl.DataFrame({
                "_src_k": [key[0] for key in src_dst_to_agg_id_map],
                "_dst_k": [key[1] for key in src_dst_to_agg_id_map],
                "_op_k": [key[2] for key in src_dst_to_agg_id_map],
                "_agg_id": list(src_dst_to_agg_id_map.values()),
            }, schema={name: pl.String for name in ("_src_k", "_dst_k", "_op_k", "_agg_id")})
        for offset in range(0, len(indices), batch_size):
            subset = trace_index[indices.slice(offset, batch_size)]
            if trace_details is not None:
                subset = trace_details.enrich(subset)
            subset = _yuanrong_from_grouped(subset)
            yield KVCacheLogParseWorker._build_detail_frame(
                subset,
                top1000_tids=top1000_tids,
                anomalous_only_tids=None,
                anomalous_tids=None,
                src_dst_to_agg_id_map=src_dst_to_agg_id_map,
                log_file_id=log_file_id,
                top1000_created_at=top_created_at,
                anomalous_created_at=anomalous_created_at,
                threshold_ms=threshold_ms,
                anomalous_only_count=anomalous_only_count,
                aggregate_keys=aggregate_keys,
                top_rows_sorted=True,
                ordered_top_count=min(max(top_count - offset, 0), subset.height),
            )
            del subset

    @staticmethod
    async def _store_detail_frames(frames, *, stage_timer=None, build_timing=None) -> int:
        """Stream bounded detail batches through one COPY and one transaction."""
        from latency.database.engine import PGManager
        from latency.common.stage_timing import read_cpu_seconds

        total = 0
        iterator = iter(frames)
        timer = as_stage_timer(stage_timer)

        def records():
            nonlocal total
            while True:
                started = time.perf_counter()
                cpu_started = read_cpu_seconds()
                with timer.stage("detail") as scope:
                    frame = next(iterator, None)
                    scope.detail = f"{frame.height if frame is not None else 0} 行"
                if build_timing is not None:
                    build_timing["wall"] += time.perf_counter() - started
                    cpu_finished = read_cpu_seconds()
                    if cpu_started is not None and cpu_finished is not None:
                        build_timing["cpu"] += cpu_finished - cpu_started
                if frame is None:
                    return
                # Bound conversion even for callers supplying larger frames.
                # Preserve copy_dataframe's shared fallback timestamp per frame.
                created_at = datetime.now(timezone.utc)
                for chunk in frame.iter_slices(50_000):
                    batch, _ = build_records(
                        chunk, LOG_PARSE_RESULT_SPEC, created_at=created_at, materialize=False
                    )
                    count = chunk.height
                    yield from batch
                    total += count
                    del batch, chunk
                del frame

        stream = records()
        try:
            async with PGManager.connection() as conn:
                raw = await conn.get_raw_connection()
                status = await raw.driver_connection.copy_records_to_table(
                    LOG_PARSE_RESULT_SPEC.table,
                    records=stream,
                    columns=list(LOG_PARSE_RESULT_SPEC.columns),
                )
                if status != f"COPY {total}":
                    raise RuntimeError(f"Failed to bulk copy log parse results: {status}, expected {total}")
        finally:
            stream.close()
            close = getattr(iterator, "close", None)
            if close is not None:
                close()
        return total

    # 存库
    @staticmethod
    async def store_result(
        anomalous_detail_rows: Any,
        src_dst_aggregated_events: list[SrcDstAggregatedEventDataclass],
        time_window_aggregated_events: list[TimeWindowAggregatedEventDataclass] | None = None,
        kb_id: str = "",
        *,
        detail_frames=None,
        stage_timer=None,
    ) -> bool:
        """存库

        三表（log_parse_result / src_dst_aggregated_event / time_window_aggregated）
        各自独立写，asyncio.gather 并行（无表间依赖，pool_size 10 可容纳并行 COPY）。
        单表失败仅记日志并置 success=False，不阻塞其他表；bucket×4 由 run() 的
        _store_bucket_stats_degraded 单独写（降级语义，不入 gather）。
        anomalous_event/anomalous_event_chain 表保留但不再由 parse 写入（detect 已删）。

        Args:
            anomalous_detail_rows: 明细待写载荷。``_build_detail_frame`` 产出的
                polars DataFrame -> ``log_parse_result_bulk.copy_dataframe``
                （列式归一化 + COPY）。旧的 ``LogParseResultDataclass`` 列表仍
                支持（少数测试/工具直接构造行对象），走
                ``add_log_parse_results``。
            detail_frames: 生产路径的有界明细迭代器，与两种聚合表保持并发写入。
            stage_timer: 分别记录迭代器构建明细和并发写库耗时。
        """
        import time as _time
        from latency.common.stage_timing import read_cpu_seconds

        build_timing = {"wall": 0.0, "cpu": 0.0}
        detail_rows_written = KVCacheLogParseWorker._detail_row_count(anomalous_detail_rows)

        if time_window_aggregated_events:
            for event in time_window_aggregated_events:
                event.kb_id = kb_id

        async def _store_detail() -> None:
            nonlocal detail_rows_written
            if detail_frames is not None:
                detail_rows_written = await KVCacheLogParseWorker._store_detail_frames(
                    detail_frames, stage_timer=stage_timer, build_timing=build_timing
                )
                return
            if anomalous_detail_rows is None:
                return
            import polars as pl

            if isinstance(anomalous_detail_rows, pl.DataFrame):
                copy_result = await copy_dataframe(
                    anomalous_detail_rows, LOG_PARSE_RESULT_SPEC
                )
                if copy_result.rows != int(anomalous_detail_rows.height):
                    raise RuntimeError(
                        "Failed to bulk copy log parse results: "
                        f"{copy_result.rows}/{anomalous_detail_rows.height} rows"
                    )
                return
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
        cpu_started = read_cpu_seconds()
        results = await asyncio.gather(
            _store_detail(),
            _store_src_dst(),
            _store_time_window(),
            return_exceptions=True,
        )
        t_store_elapsed = _time.perf_counter() - t_store_start
        cpu_finished = read_cpu_seconds()
        # Detail construction is synchronous and blocks the event loop. Account
        # for it separately while retaining the three concurrent database writes.
        as_stage_timer(stage_timer).add(
            "store",
            wall_s=max(0.0, t_store_elapsed - build_timing["wall"]),
            cpu_s=(
                max(0.0, cpu_finished - cpu_started - build_timing["cpu"])
                if cpu_started is not None and cpu_finished is not None else None
            ),
            detail="明细与聚合写库",
            start=t_store_start,
            end=t_store_start + t_store_elapsed,
        )

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
            detail_rows_written,
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
        stage_timer: Any = None,
        trace_details: TraceFrames | None = None,
    ) -> dict[int, int] | None:
        """Write 4 latency_bucket_* tables from df_trace, degrading on failure.

        T7: ``rows`` 唯一来源是 df_trace（polars DataFrame, T2/T3 产物）→
        ``compute_and_store_bucket_stats_from_frame``（纯 polars 选代表行）。
        P3: 代表行直接以列式 frame 交给 ``log_parse_result_bulk.copy_dataframe``
        （``materializer`` 参数已删，报告已证明它与 ``None`` 逐字段相同）；
        numpy 版 ``compute_and_store_bucket_stats`` 已删。非 df_trace 输入
        （legacy 平铺 dict）直接降级返回 None。

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

        try:
            return await compute_and_store_bucket_stats_from_frame(
                df_trace=rows,
                log_id=log_id,
                kb_id=kb_id,
                task_id=task_id or None,
                tables=tables,
                stage_timer=stage_timer,
                trace_details=trace_details,
            )
        except Exception as e:
            logger.exception("[run] Bucket stats failed, degraded: %s", e)
            return None

    @staticmethod
    async def run(
        task_id: str,
        log_dir: str | None = None,
        parse_config: ParseConfig | None = None,
    ) -> bool:
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
            from latency.common.stage_timing import StageTimer

            progress = StageProgress(task_id)
            await progress.report("scan", 0.0, detail="task started")
            # [timing] 结构化分阶段耗时：各阶段在这里登记，任务成功结束前
            # 统一 emit 一行 [timing] {json}（契约见 common/stage_timing.py）。
            # 直接使用 task.op_id 作为 log_id，parse_log 内部会获取 log_file 信息
            t_run_start = time.perf_counter()
            # 计时器以 run() 起点为基准 → 报告里能给出端到端（含预处理/调度/收尾）
            timer = StageTimer(started_at=t_run_start,
                              wall_started_at=getattr(task, "created_at", None),
                              task_type=TaskTypeEnum.KV_CACHE_LOG_PARSE_WORKER.value)

            if parse_config:
                logger.info(f"[Task {task_id}] Using parse config: {parse_config}")
            # 平滑扫描子进度: 每文件组完成上报 scan 比例, 避免扫描期进度条冻结
            async def _scan_progress(fraction: float) -> None:
                # 读文件阶段会分批上报 0..1；到 1.0 说明文件读完，紧接着就是
                # build_trace_frame（归并）—— 立刻把前端标签切过去，别停在"扫描中"。
                if fraction >= 1.0:
                    await progress.report("scan", 1.0)
                    await progress.report("trace_frame", 0.0, detail="拼装 trace")
                else:
                    await progress.report("scan", fraction)

            trace_index = await KVCacheLogParseWorker.parse_log(
                task.op_id,
                parse_config,
                log_dir=log_dir or "",
                task_id=task_id,
                scan_progress_cb=_scan_progress,
                stage_timer=timer,
                compact=True,
            )
            trace_details = trace_index if isinstance(trace_index, TraceFrames) else None
            if trace_details is not None:
                trace_index = trace_details.light
            t_parse = time.perf_counter() - t_run_start

            if trace_index is None or _trace_row_count(trace_index) == 0:
                await TaskPGManager.mark_failed_with_report(
                    task_id,
                    "任务失败：未在路径中识别到日志信息",
                    status=TaskStatusEnum.FAILED_PENDING_REMOVE,
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
            threshold_ms = float(
                getattr(analyzer_config, "total_p99_threshold_ms", 5.0) or 5.0
            )

            # 检查任务是否被取消
            task = await TaskPGManager.get_task_by_task_id(task_id)
            if not task or task.status == TaskStatusEnum.CANCELLED:
                logger.warning(f"任务 {task_id} 已被取消或不存在，停止执行")
                return False

            # 生成聚合事件（异常判定 = 聚合侧单 trace 阈值）
            await progress.report("aggregate", 0.0, detail="聚合中")
            t_agg_start = time.perf_counter()
            # [timing] aggregate = _aggregate_three_way（src_dst / 时间窗 / 异常三路）
            with timer.stage("aggregate") as agg_scope:
                (
                    src_dst_aggregated_events,
                    src_dst_to_agg_id_map,
                    time_window_aggregated_events,
                    anomalous_tids,
                    df_trace,
                ) = await KVCacheLogParseWorker._aggregate_three_way(
                    trace_index,
                    analyzer_config,
                    log_file_id=task.op_id,
                    materialize_anomaly_ids=False,
                )
                agg_scope.detail = (
                    f"端点 {len(src_dst_aggregated_events)} / "
                    f"时间窗 {len(time_window_aggregated_events)} / "
                    f"异常 {len(anomalous_tids)}"
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

            # Build and persist bounded detail batches, including every anomaly.
            log_file_id = task.op_id
            # ── 内存缓存聚合事件（API 立即可用） ──────────────────
            from latency.common.aggregate_cache import (
                set_aggregated_events,
                set_time_window_events,
            )
            # 设置 kb_id 后缓存，后续 API 可按 kb_id 查询
            for event in time_window_aggregated_events:
                event.kb_id = kb_id or ""
            set_aggregated_events(log_file_id, src_dst_aggregated_events, kb_id=kb_id or "")
            set_time_window_events(log_file_id, time_window_aggregated_events)

            # ── 明细行：yuanrong 分段时延仅对 top1000 + 异常 trace 子集计算（T5/T9）。
            #    _yuanrong_from_grouped 从全量 347k 行延后到 ~(1K+anomalous) 行子集，
            #    5 遍 with_columns 开销从 347k×5 降到 ~ (1K+anomalous)×5。
            import polars as pl

            # [timing] detail = yuanrong 分段 + top1000/异常子集 → 明细载荷
            t_detail_start = time.perf_counter()
            await progress.report("detail", 0.0, detail="生成明细")
            with timer.stage("detail") as detail_scope:
                top1000_tids: set[str] = set()
                try:
                    # 使用 top_k 代替 sort + head，避免对整个 DataFrame 排序
                    # top_k 使用堆排序，内存占用更小，性能更好
                    # 注意：top_k 的正确用法是 top_k(k=..., by=...)
                    top1000_tids = set(
                        trace_index.top_k(k=1000, by="total_latency")["tid"]
                        .to_list()
                    )
                except Exception:
                    logger.warning("[yuanrong] top1000 tid selection failed", exc_info=True)

                # 异常 trace 如果在 top1000 中：top1000 行标 is_anomalous，
                # 不再单独构建异常行（避免同一 trace 在 log_parse_result 存两行）。
                anomaly_expr = (pl.col("total_ms") >= threshold_ms).fill_null(False)
                anomalous_only_count = int(
                    trace_index.select(
                        (anomaly_expr & ~pl.col("tid").is_in(top1000_tids)).sum()
                    ).item()
                    or 0
                )
                if anomalous_only_count:
                    logger.info(
                        "[yuanrong] %d anomalous traces outside top1000, "
                        "will build separate rows",
                        anomalous_only_count,
                    )

                detail_count = len(top1000_tids) + anomalous_only_count
                detail_frames = None
                if top1000_tids or len(anomalous_tids):
                    detail_frames = KVCacheLogParseWorker._iter_detail_frames(
                        trace_index,
                        top1000_tids,
                        threshold_ms,
                        src_dst_to_agg_id_map,
                        log_file_id,
                        anomalous_only_count,
                        trace_details=trace_details,
                    )
                else:
                    logger.info("[yuanrong] no detail tids (top1000=%d anomalous=%d), skipped",
                               len(top1000_tids), len(anomalous_tids))
                detail_scope.detail = f"{detail_count} 行（准备分批写入）"
            t_detail = time.perf_counter() - t_detail_start
            await progress.report("detail", 1.0)
            await progress.stage_log(
                "detail",
                f"rows={detail_count}, prepared for bounded writes",
            )

            anomalous_count = len(anomalous_tids)
            del trace_index, anomalous_tids

            # ── 分位桶统计：df_trace（T4 frame 路径, polars 选代表行）→
            # 4 张 latency_bucket_* 表。仅对选中代表行构造 dataclass（~300），
            # 失败经降级包装仅记录日志，不阻塞明细/聚合落库。
            await progress.report("bucket", 0.0, detail="计算分位桶")
            written = await KVCacheLogParseWorker._store_bucket_stats_degraded(
                log_id=task.op_id,
                kb_id=kb_id or "",
                rows=df_trace,
                task_id=task_id,
                stage_timer=timer,
                trace_details=trace_details,
            )
            await progress.report("bucket", 1.0)
            # 降级返回 None 时必须如实报告：原先无条件打 "written"，导致
            # "分桶表 0 行 + 任务报告一切正常"，前端表现为"暂无时延数据"。
            if written:
                await progress.stage_log(
                    "bucket",
                    f"latency_bucket_* written rows={sum(written.values())}",
                )
            else:
                await progress.stage_log(
                    "bucket",
                    "latency_bucket_* NOT written (degraded, see backend log)",
                )

            del df_trace, trace_details

            # The detail iterator owns its input until all batches are consumed;
            # keep detail and aggregate writes concurrent as before.
            t_store_start = time.perf_counter()
            # [timing] store = 写库插入；分桶 4 表的 delete+insert 已在
            # compute_and_store_bucket_stats_from_frame 里登记到同一阶段（累加）。
            await progress.report("store", 0.0, detail="写库")
            stored = await KVCacheLogParseWorker.store_result(
                anomalous_detail_rows=None,
                src_dst_aggregated_events=src_dst_aggregated_events,
                time_window_aggregated_events=time_window_aggregated_events,
                kb_id=kb_id or "",
                detail_frames=detail_frames,
                stage_timer=timer,
            )
            del detail_frames
            t_store = time.perf_counter() - t_store_start
            await progress.report("store", 1.0)
            await progress.stage_log("store", f"stored={stored}", elapsed_ms=t_store * 1000)
            await BaseWorker.report(
                task.id,
                (
                    "[perf][store.summary] "
                    f"detail_rows={detail_count}, "
                    f"aggregated={len(src_dst_aggregated_events)}, "
                    f"stored={stored}, time={t_store:.3f}s"
                ),
                t_store,
            )
            
            if not stored:
                logger.error(f"Task {task_id} store failed, marking task as failed")
                await TaskPGManager.mark_failed_with_report(
                    task_id,
                    "任务失败：解析结果写入数据库未成功",
                    status=TaskStatusEnum.FAILED_PENDING_REMOVE,
                )
                return False

            await LogFilePGManager.update_log_file(
                task.op_id, {"anomalous_count": anomalous_count}
            )
            
            # 重新聚合知识库统计：多日志共存时按剩余日志求和，
            # 直接写本日志的计数会覆盖其它日志的贡献。
            if kb_id:
                await LogKnowledgePGManager.refresh_kb_counters(kb_id)
            
            await TaskPGManager.update_task(
                task_id, {"status": TaskStatusEnum.SUCCESSFUL_PENDING_REMOVE.value}
            )
            await BaseWorker.report(task.id, "Task completed successfully", 100.0)

            # 全流程耗时汇总
            t_total = time.perf_counter() - t_run_start
            pct_p = t_parse / t_total * 100
            pct_a = t_agg / t_total * 100
            pct_s = t_store / t_total * 100
            logger.info(
                f"============================================================\n"
                f"=== [TASK TIMING] Total: {t_total:.1f}s ===\n"
                f"  [1] Parse log:       {t_parse:7.1f}s ({pct_p:5.1f}%)\n"
                f"  [2] Aggregate result:{t_agg:7.1f}s ({pct_a:5.1f}%)\n"
                f"  [3] Prepare detail: {t_detail:7.1f}s\n"
                f"  [4] Build/store results: {t_store:7.1f}s ({pct_s:5.1f}%)\n"
                f"============================================================"
            )
            await BaseWorker.report(task.id, f"[TASK] Parse log: {t_parse:.1f}s ({pct_p:.1f}%)", t_parse)
            await BaseWorker.report(task.id, f"[TASK] Aggregate result: {t_agg:.1f}s ({pct_a:.1f}%)", t_agg)
            await BaseWorker.report(task.id, f"[TASK] Store to DB: {t_store:.1f}s ({pct_s:.1f}%)", t_store)
            await BaseWorker.report(task.id, f"[TASK] Total: {t_total:.1f}s", 0.0)

            # ── [timing] 结构化阶段耗时：任务成功结束（写库之后）发这一条 ──
            # 契约（前缀 / JSON 键 / 小数位 / 缺失阶段不补 0）见
            # common/stage_timing.py 模块 docstring；打点失败只记日志，
            # 绝不影响任务成功。
            try:
                await timer.emit(task_id, rows=trace_rows)
            except Exception:
                logger.warning("[timing] emit failed, task unaffected", exc_info=True)
            return True
        except Exception as e:
            logger.exception(f"Task {task_id} failed: {e}")
            await TaskPGManager.mark_failed_with_report(
                task_id,
                f"任务失败：日志解析异常，{type(e).__name__}: {e}",
                status=TaskStatusEnum.FAILED_PENDING_REMOVE,
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
