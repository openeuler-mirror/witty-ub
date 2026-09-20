import asyncio
import os
import logging
import uuid
import time
import shutil
import gzip
from io import BytesIO

from dataclasses import dataclass
from concurrent.futures import ThreadPoolExecutor

from collections.abc import Iterator
from typing import Any

from latency.task.worker.base import BaseWorker
from latency.config.config import Config
from latency.common.trace_context import match_trace_context_trace_id
from latency.database.managers.log_file import LogFilePGManager
from latency.database.managers.log_knowledge import LogKnowledgePGManager
from latency.database.managers.log_parse_result import LogParseResultPGManager
from latency.database.managers.task import TaskPGManager
from latency.task.worker.kv_cache_log_event_diagnosis_worker import KVCacheLogEventDiagnosisWorker
from latency.ENUM.task import TaskStatusEnum, TaskTypeEnum
from latency.database.managers.log_failure_event import LogFailureEventPGManager
from latency.schemas.log import LogFileModel
from latency.schemas.task import TaskModel
from latency.database.managers.failure_mode_knowledge import FailureModeKnowledgePGManager
from latency.database.utils import parse_timestamp
from latency.task.log_preprocessor import cleanup_preprocess_dir
from latency.common.stage_timing import StageTimer


logger = logging.getLogger(__name__)
WITTY_DIR_DEFAULT = "/var/witty-ub"
witty_dir = os.getenv("WITTY_DIR", WITTY_DIR_DEFAULT)

# 扫描实现开关：默认走 polars（WITTY_STORE_POLARS=0 回退旧逐行实现）
STORE_POLARS_ENV = "WITTY_STORE_POLARS"
# Amortize native query planning and group aggregation over larger blocks.
# The reader and preparer each prefetch only one block, keeping memory bounded.
_CONTEXT_INPUT_BYTES = 64 * 1024 * 1024
_CONTEXT_BATCH_ROWS = 262144
# COPY 载荷以 polars 原生 CSV 字节流交给 PostgreSQL（FORMAT csv）：
# 每片全量字符串加引号、NULL 写未引用的 \N，空串与字面 "\N" 保持精确。
_CONTEXT_CSV_ROWS = 65536
_CSV_NULL = "\\N"
_CSV_DATETIME_FORMAT = "%Y-%m-%d %H:%M:%S%.f"
# failure_trace.log 索引构建的输入块（字节）：限住 scan_lines + splitn 的瞬时分配。
_FAILURE_INDEX_BYTES = 32 * 1024 * 1024
_CONTEXT_COLUMNS = (
    "log_file", "raw_text", "timestamp", "level", "filename", "pod_name",
    "pid", "tid", "trace_id", "cluster_name", "message", "status_code",
    "src_ip", "dst_ip", "operation",
)
_UUID_VARIANTS = dict(zip("0123456789abcdef", "89ab89ab89ab89ab"))



def store_polars_enabled() -> bool:
    return os.getenv(STORE_POLARS_ENV, "1").strip().lower() not in {"0", "false", "no"}

SUCCESS_STATUSES = {
    TaskStatusEnum.SUCCESSFUL_PENDING_REMOVE,
    TaskStatusEnum.SUCCESSFUL,
}
FAILED_STATUSES = {
    TaskStatusEnum.FAILED_PENDING_REMOVE,
    TaskStatusEnum.FAILED,
    TaskStatusEnum.CANCELLED,
}
MONITOR_INTERVAL_SECONDS = 1


class ContextStoreError(RuntimeError):
    """A failed write must fail the task, rather than skip a raw log line."""


class _FailureModeFrame:
    """Native ``(raw_text, modes)`` failure lookup built once per task.

    The polars ingest path joins scan batches against the frame natively —
    no per-row Python hashing and no per-row Python string materialization.
    The legacy row path (and dict-compat callers) materialize a dict lazily;
    equal mode lists are shared so the previous list-identity contract holds.
    """

    __slots__ = ("_frame", "_lookup")

    def __init__(self, frame) -> None:
        self._frame = frame
        self._lookup: dict[str, list[str]] | None = None

    @classmethod
    def empty(cls) -> "_FailureModeFrame":
        import polars as pl

        return cls(pl.DataFrame(
            schema={"raw_text": pl.String, "modes": pl.List(pl.String)}
        ))

    @property
    def frame(self):
        return self._frame

    def __len__(self) -> int:
        return self._frame.height

    def __bool__(self) -> bool:
        return self._frame.height > 0

    def to_lookup(self) -> dict[str, list[str]]:
        if self._lookup is None:
            shared: dict[tuple[str, ...], list[str]] = {}
            lookup: dict[str, list[str]] = {}
            for raw_text, modes in zip(
                self._frame["raw_text"], self._frame["modes"]
            ):
                lookup[raw_text] = shared.setdefault(tuple(modes), list(modes))
            self._lookup = lookup
        return self._lookup

    def get(self, raw_text: str, default=None):
        return self.to_lookup().get(raw_text, default)


def _as_failure_frame(lookup: Any) -> _FailureModeFrame | None:
    """Normalize a failure lookup input into a native frame (None = no lookup)."""
    if lookup is None:
        return None
    if isinstance(lookup, _FailureModeFrame):
        return lookup or None
    if not lookup:
        return None
    return _FailureModeFrame(_raw_lookup_frame(lookup))


def _raw_lookup_frame(lookup) -> Any:
    import polars as pl

    return pl.DataFrame({
        "raw_text": list(lookup.keys()),
        "modes": [list(modes) for modes in lookup.values()],
    })


@dataclass(slots=True)
class _TraceContextState:
    """Only retain fields that vary per trace while raw rows are streamed."""

    timestamp: str
    pod_names: tuple[str, ...]
    cluster_names: tuple[str, ...]
    src_ip: str = ""
    dst_ip: str = ""
    operation: str = ""
    failure_modes: tuple[str, ...] = ()
    access_failure_modes: tuple[str, ...] = ()

    def merge(self, row: dict) -> None:
        pod = row["pod_name"]
        cluster = row["cluster_name"]
        if pod and pod not in self.pod_names:
            self.pod_names += (pod,)
        if cluster and cluster not in self.cluster_names:
            self.cluster_names += (cluster,)
        if row["timestamp"] < self.timestamp:
            self.timestamp = row["timestamp"]
        if row["src_ip"]:
            self.src_ip = row["src_ip"]
            self.dst_ip = row["dst_ip"]
        if row["operation"] and not self.operation:
            self.operation = row["operation"]
        modes = row["failure_mode"]
        if modes:
            for mode in modes:
                if mode and mode not in self.failure_modes:
                    self.failure_modes += (mode,)
                if row["status_code"] and mode and mode not in self.access_failure_modes:
                    self.access_failure_modes += (mode,)

    def event(self, log_id: str, trace_id: str, failure_mode_cache: dict) -> dict:
        diagnosis = KVCacheLogEventDiagnosisWorker
        access_modes = diagnosis._leaf_failure_modes(self.access_failure_modes, failure_mode_cache)
        return {
            "id": str(uuid.uuid5(uuid.NAMESPACE_URL, f"{log_id}:{trace_id}")),
            "log_id": log_id,
            "trace_id": trace_id,
            "pod_names": list(self.pod_names),
            "host_names": ["Unknown"],
            "cluster_names": list(self.cluster_names),
            "timestamp": self.timestamp,
            "src_ip": self.src_ip,
            "dst_ip": self.dst_ip,
            "operation": self.operation,
            "failure_mode": diagnosis._leaf_failure_modes(self.failure_modes, failure_mode_cache),
            "status_code": diagnosis._failure_mode_error_codes(access_modes, failure_mode_cache),
        }


class _TraceContextEvents:
    """Sized, single-pass event source for one atomic trace-table COPY."""

    def __init__(self, states: dict, log_id: str, failure_mode_cache: dict) -> None:
        self.states = states
        self.log_id = log_id
        self.failure_mode_cache = failure_mode_cache
        self.count = len(states)

    def __len__(self) -> int:
        return self.count

    def __iter__(self) -> Iterator[dict]:
        for trace_id, state in self.states.items():
            event = state.event(self.log_id, trace_id, self.failure_mode_cache)
            # Replacing values preserves dict size/order during iteration and
            # releases each state without materializing a second full list.
            self.states[trace_id] = None
            yield event


def cleanup_temp_dirs(output_log_path: str, log_file_id: str) -> None:
    """清理临时文件夹，包括诊断输出和预处理的日志"""
    if output_log_path and os.path.exists(output_log_path):
        try:
            shutil.rmtree(output_log_path)
            logger.info("清理诊断输出目录: %s", output_log_path)
        except OSError as e:
            logger.error("清理诊断输出目录 %s 失败: %s", output_log_path, e)
    
    if log_file_id:
        cleanup_preprocess_dir(log_file_id)


class StoreTraceContextLogsWorker(BaseWorker):
    """
    Worker for storing trace context logs.
    """

    name = TaskTypeEnum.STORE_TRACE_CONTEXT_LOGS_WORKER

    @staticmethod
    def _build_failure_index(path: str) -> tuple[set[str], Any]:
        """Native ``(trace_ids, raw_text→modes frame)`` from failure_trace.log.

        分块（_FAILURE_INDEX_BYTES）scan_lines + splitn + list 表达式，全程
        原生；modes 逐元素 strip、去空、按首次出现去重（复刻旧
        ``list(dict.fromkeys(...))``），raw_text 去重取最后一行（复刻旧 dict
        覆盖写）。trace_id 取第 6 个字段的 strip 值（splitn("|", 7) 的
        field_5，与旧 ``raw_text.split('|', 6)[5]`` 同位）。
        """
        import polars as pl

        schema = {"raw_text": pl.String, "modes": pl.List(pl.String)}
        parts: list = []
        trace_ids: set[str] = set()
        with open(path, "rb") as stream:
            while block := stream.read(_FAILURE_INDEX_BYTES):
                if not block.endswith(b"\n"):
                    block += stream.readline()
                split = pl.col("line").str.splitn("|", 2)
                raw = split.struct.field("field_1").str.strip_chars()
                modes = (
                    split.struct.field("field_0").str.strip_chars()
                    .str.split(",")
                    .list.eval(pl.element().str.strip_chars())
                    .list.eval(
                        pl.element().filter(
                            pl.element().is_first_distinct() & (pl.element() != "")
                        )
                    )
                )
                tid = raw.str.splitn("|", 7).struct.field("field_5").str.strip_chars()
                indexed = (
                    pl.scan_lines(block)
                    .select(
                        raw.alias("raw_text"), modes.alias("modes"), tid.alias("tid")
                    )
                    .collect(engine="streaming")
                )
                del block
                tids = indexed["tid"].unique()
                trace_ids.update(
                    tids.filter(tids.is_not_null() & (tids != "")).to_list()
                )
                parts.append(indexed.select("raw_text", "modes"))
                del indexed
        frame = (
            pl.concat(parts) if len(parts) > 1
            else parts[0] if parts
            else pl.DataFrame(schema=schema)
        )
        del parts
        frame = frame.filter(pl.col("raw_text").is_not_null()).unique(
            subset="raw_text", keep="last", maintain_order=True
        )
        return trace_ids, frame

    @staticmethod
    async def _generate_trace_id_set_diagnosis(
        output_log_path: str, *, compact: bool = False,
    ) -> tuple[set[str], dict[str, list[str]] | _FailureModeFrame]:
        if not os.path.exists(output_log_path):
            logger.error(f"输出日志路径不存在: {output_log_path}")
            return set(), (_FailureModeFrame.empty() if compact else {})

        failure_trace_path = os.path.join(output_log_path, "failure_trace.log")
        if not os.path.exists(failure_trace_path):
            return set(), (_FailureModeFrame.empty() if compact else {})

        try:
            trace_id_set, frame = (
                StoreTraceContextLogsWorker._build_failure_index(failure_trace_path)
            )
            logger.info(f"从 failure_trace.log 提取到 {len(trace_id_set)} 个 trace_id")
        except Exception as e:
            # 原生构建对坏字节严格失败：与其落一半故障模式，不如显式置空并留全栈
            logger.exception(f"解析 failure_trace.log 失败: {e}")
            return set(), (_FailureModeFrame.empty() if compact else {})

        if compact:
            return trace_id_set, _FailureModeFrame(frame)
        return trace_id_set, _FailureModeFrame(frame).to_lookup()

    @staticmethod
    def _context_projection(source: Any, trace_ids: Any, access_names: list[str]) -> Any:
        """Build the shared projection without collecting or retaining source text."""
        import polars as pl
        from latency.parse.keywords import (
            SDK_GET_OPS, SDK_SET_OPS, WORKER_GET_OPS, WORKER_SET_OPS,
        )

        ip = r"(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})"
        strip = lambda expr: expr.str.strip_chars()  # noqa: E731

        def field(index: int):
            return pl.col("_p").struct.field(f"field_{index}")

        f4 = strip(field(4))
        two_parts = f4.str.count_matches(":") == 1
        # splitn 只切一次（无逐行 list 分配）；two_parts 为真时 field_1 就是
        # 冒号后的整段，与旧 split(":")[1] 逐值一致。
        pid_tid = f4.str.splitn(":", 2)
        src = pl.coalesce([
            pl.col("line").str.extract(r"(?i)src=" + ip, 1),
            pl.col("line").str.extract(r"(?i)src address:" + ip, 1),
            pl.col("line").str.extract(r"(?i)srcAddress\s*=\s*" + ip, 1),
        ])
        dst = pl.coalesce([
            pl.col("line").str.extract(r"(?i)dst=" + ip, 1),
            pl.col("line").str.extract(r"(?i)target address:" + ip, 1),
            pl.col("line").str.extract(r"(?i)targetAddress\s*=\s*" + ip, 1),
        ])
        both = src.is_not_null() & dst.is_not_null()
        # Only the status and operation are needed; the remaining message can
        # contain many separators and must not become a temporary string list.
        sub7 = field(7).str.splitn("|", 3)
        handle = strip(sub7.struct.field("field_1"))
        is_access = pl.col("log_file").is_in(access_names)
        get_vals = sorted({op.value for op in (*SDK_GET_OPS, *WORKER_GET_OPS)})
        set_vals = sorted({op.value for op in (*SDK_SET_OPS, *WORKER_SET_OPS)})
        if trace_ids.flags["SORTED_ASC"]:
            # A large selection must not rebuild a million-entry hash table
            # for every bounded input block. Reuse its sorted native index.
            position = pl.lit(trace_ids).search_sorted(pl.col("trace_id"))
            selected = (
                pl.lit(trace_ids).gather(position.clip(upper_bound=len(trace_ids) - 1))
                == pl.col("trace_id")
            )
        else:
            selected = pl.col("trace_id").is_in(trace_ids.implode())

        # splitn 只切一次（抄 parse/parallel_scanner 的做法），后面都从 _p 取字段
        lf = source.with_columns(
            log_file=pl.col("_path").str.extract(r"([^/\\]+)$", 1),
            _p=pl.col("line").str.splitn("|", 8),
        )
        return (
            lf.with_columns([field(index).alias(f"_f{index}") for index in range(8)])
            .filter(pl.col("_f6").is_not_null())  # ≥7 段
            .with_columns(trace_id=strip(pl.col("_f5")))
            .filter(pl.col("trace_id") != "")
            .filter(selected)
            .filter(~(is_access & pl.col("_f7").is_null()))  # access 行必须 ≥8 段
            .select([
                pl.col("log_file"),
                # 与旧实现一致：raw_text 是 strip() 之后的整行
                strip(pl.col("line")).alias("raw_text"),
                strip(pl.col("_f0")).str.replace_all("T", " ").alias("timestamp"),
                strip(pl.col("_f1")).alias("level"),
                strip(pl.col("_f2")).alias("filename"),
                strip(pl.col("_f3")).alias("pod_name"),
                pl.when(two_parts).then(pid_tid.struct.field("field_0")).otherwise(f4).alias("pid"),
                pl.when(two_parts).then(pid_tid.struct.field("field_1").fill_null("")).otherwise(pl.lit("")).alias("tid"),
                pl.col("trace_id"),
                strip(pl.col("_f6")).alias("cluster_name"),
                strip(pl.col("_f7").fill_null("")).alias("message"),
                pl.when(is_access)
                .then(strip(sub7.struct.field("field_0")))
                .otherwise(pl.lit(""))
                .alias("status_code"),
                pl.when(both).then(src).otherwise(pl.lit("")).alias("src_ip"),
                pl.when(both).then(dst).otherwise(pl.lit("")).alias("dst_ip"),
                pl.when(handle.is_in(get_vals)).then(pl.lit("GET"))
                .when(handle.is_in(set_vals)).then(pl.lit("SET"))
                .otherwise(pl.lit(""))
                .alias("operation"),
            ])
        )

    @staticmethod
    def _context_source_queries(log_files: list[tuple[str, str]]) -> Iterator[Any]:
        """Bound native reader input bytes, including expanded gzip input.

        A streaming sink alone can still read ahead through a whole large file.
        Small plain files share a native scan; large files and gzip streams are
        presented as newline-aligned blocks. One exceptionally long log line is
        necessarily kept intact even when it exceeds the target block size.
        """
        import polars as pl

        pending: list[str] = []
        pending_bytes = 0
        for _name, path in log_files:
            if not os.path.isfile(path):
                continue
            size = os.path.getsize(path)
            if size == 0:
                continue
            compressed = path.lower().endswith(".gz")
            if compressed or size > _CONTEXT_INPUT_BYTES:
                if pending:
                    yield pl.scan_lines(pending, include_file_paths="_path")
                    pending, pending_bytes = [], 0
                opener = gzip.open if compressed else open
                with opener(path, "rb") as stream:
                    while block := stream.read(_CONTEXT_INPUT_BYTES):
                        if not block.endswith(b"\n"):
                            block += stream.readline()
                        source = pl.scan_lines(block).with_columns(pl.lit(path).alias("_path"))
                        del block
                        yield source
                        del source
            else:
                if pending and pending_bytes + size > _CONTEXT_INPUT_BYTES:
                    yield pl.scan_lines(pending, include_file_paths="_path")
                    pending, pending_bytes = [], 0
                pending.append(path)
                pending_bytes += size
        if pending:
            yield pl.scan_lines(pending, include_file_paths="_path")

    @staticmethod
    def _context_scan_batches(
        log_files: list[tuple[str, str]],
        trace_id_set: set,
        worker_access_patterns: list[str],
        client_access_patterns: list[str],
    ) -> Iterator[Any]:
        """Overlap one bounded native scan with row conversion and COPY."""
        import polars as pl

        if not trace_id_set:
            return
        access_names = [
            name for name, _path in log_files
            if KVCacheLogEventDiagnosisWorker._matches_any(name, worker_access_patterns)
            or KVCacheLogEventDiagnosisWorker._matches_any(name, client_access_patterns)
        ]
        trace_ids = pl.Series("trace_id", list(trace_id_set), dtype=pl.String)
        if len(trace_ids) > 131_072:
            trace_ids = trace_ids.sort()
        sources = StoreTraceContextLogsWorker._context_source_queries(log_files)

        def scan_next():
            source = next(sources, None)
            if source is None:
                return None
            plan = StoreTraceContextLogsWorker._context_projection(source, trace_ids, access_names)
            return plan.collect(engine="streaming")

        # Polars releases the GIL while scanning. A single pending scan hides
        # native reader time behind Python conversion and database I/O, without
        # letting a fast reader accumulate frames for the whole input.
        executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="context-scan")
        future = executor.submit(scan_next)
        try:
            while (frame := future.result()) is not None:
                future = executor.submit(scan_next)
                yield from frame.iter_slices(_CONTEXT_BATCH_ROWS)
                del frame
        finally:
            # A failed COPY must join the bounded in-flight read before closing
            # its generator, including gzip file handles, on this thread.
            future.cancel()
            executor.shutdown(wait=True, cancel_futures=True)
            sources.close()

    @staticmethod
    def _context_scan_frame(
        log_files: list[tuple[str, str]],
        trace_id_set: set,
        worker_access_patterns: list[str],
        client_access_patterns: list[str],
    ) -> Any:
        """Compatibility helper for small callers; production consumes batches."""
        import polars as pl

        parts = list(StoreTraceContextLogsWorker._context_scan_batches(
            log_files, trace_id_set, worker_access_patterns, client_access_patterns
        ))
        return pl.concat(parts) if parts else pl.DataFrame({name: [] for name in _CONTEXT_COLUMNS})

    @staticmethod
    def _legacy_row_batches(
        log_files: list[tuple[str, str]],
        trace_id_set: set,
        worker_access_patterns: list[str],
        client_access_patterns: list[str],
    ) -> Iterator[list[dict]]:
        """旧的逐行扫描（WITTY_STORE_POLARS=0 回退用），固定批大小。"""
        for log_file_name, log_file_path in log_files:
            try:
                is_access_log = False
                if KVCacheLogEventDiagnosisWorker._matches_any(
                    log_file_name, worker_access_patterns
                ):
                    is_access_log = True
                if KVCacheLogEventDiagnosisWorker._matches_any(
                    log_file_name, client_access_patterns
                ):
                    is_access_log = True
                rows = []
                # errors='replace'：非 UTF-8 字符不让整批崩掉
                with open(log_file_path, "r", encoding="utf-8", errors="replace") as handle:
                    for line in handle:
                        try:
                            raw_line = line.strip()
                            if not raw_line:
                                continue
                            parts = raw_line.split("|", 8)
                            if len(parts) < 7:
                                continue
                            trace_id = match_trace_context_trace_id(
                                parts[5].strip() if len(parts) > 5 else "",
                                raw_line,
                                trace_id_set,
                            )
                            if not trace_id:
                                continue
                            pid_tid = parts[4].strip()
                            pid_tid_parts = pid_tid.split(":")
                            if len(pid_tid_parts) == 2:
                                pid, tid = pid_tid_parts
                            else:
                                pid, tid = pid_tid, ""
                            if is_access_log:
                                if len(parts) > 7:
                                    status_code = parts[7].strip()
                                    message = "|".join(parts[7:])
                                else:
                                    logger.warning(
                                        f"access log格式不正确，字段不足: {raw_line}"
                                    )
                                    continue
                            else:
                                status_code = ""
                                message = "|".join(parts[7:]) if len(parts) > 7 else ""
                            rows.append({
                                "log_file": log_file_name,
                                "raw_text": raw_line,
                                "timestamp": parts[0].strip().replace("T", " "),
                                "level": parts[1].strip(),
                                "filename": parts[2].strip(),
                                "pod_name": parts[3].strip(),
                                "pid": pid,
                                "tid": tid,
                                "trace_id": trace_id,
                                "cluster_name": parts[6].strip() if len(parts) > 6 else "",
                                "message": message.strip(),
                                "status_code": status_code,
                            })
                            if len(rows) >= _CONTEXT_BATCH_ROWS:
                                yield rows
                                rows = []
                        except Exception as exc:  # noqa: BLE001
                            logger.warning(
                                f"读取日志文件 {log_file_path} 行失败: {line}, 错误: {exc}"
                            )
                            continue
                if rows:
                    yield rows
            except Exception as exc:  # noqa: BLE001
                logger.warning(f"读取日志文件 {log_file_path} 失败: {exc}")
                continue

    @staticmethod
    async def _load_store_context(
        output_log_path: str,
        log_id: str,
    ) -> tuple[list[str], list[str], dict, list[tuple[str, str]]]:
        """输入：输出目录 + log_id → 输出：(access 模式, failure_mode_cache, 待扫文件)。"""
        log_file_model = await LogFilePGManager.get_log_file_by_log_file_id(log_id)
        config = await KVCacheLogEventDiagnosisWorker.parse_filepath_config(
            log_file_model.kb_id if log_file_model else None
        )
        failure_mode_cache = await FailureModeKnowledgePGManager.get_all_failure_modes()
        worker_access_patterns = config.get("ds_worker_access_log_file", [])
        client_access_patterns = config.get("ds_client_access_log_file", [])

        log_files = []
        for file in os.listdir(output_log_path):
            file_path = os.path.join(output_log_path, file)
            if os.path.isfile(file_path) and file != "failure_trace.log":
                log_files.append((file, file_path))
        return worker_access_patterns, client_access_patterns, failure_mode_cache, log_files

    @staticmethod
    def _scan_context_rows(
        log_files: list[tuple[str, str]],
        trace_id_set: set[str],
        worker_access_patterns: list[str],
        client_access_patterns: list[str],
    ) -> tuple[int, bool, Any]:
        """Return a single-pass reader; the total becomes known at EOF."""
        use_polars = store_polars_enabled()
        if use_polars:
            batches = StoreTraceContextLogsWorker._context_scan_batches(
                log_files, trace_id_set, worker_access_patterns, client_access_patterns
            )
        else:
            batches = StoreTraceContextLogsWorker._legacy_row_batches(
                log_files, trace_id_set, worker_access_patterns, client_access_patterns
            )
        return 0, use_polars, batches

    @staticmethod
    def _prepare_context_batch(
        batch: Any, failure_frame: _FailureModeFrame | None, log_id: str,
    ) -> tuple[int, list[bytes], Any]:
        """Batch -> (row count, CSV byte chunks, per-trace group frame).

        行转换全部留在原生代码：uuid 列、failure-mode 左连接（不再逐行
        sha256）、trace 分组聚合、时间戳解析、以及最终的 CSV 编码——Python
        侧不再物化任何逐行对象。CSV 片直接供 PostgreSQL ``FORMAT csv``
        COPY 消费：全量字符串加引号、NULL 写未引用 ``\\N``。
        """
        import polars as pl

        random = pl.col("_random")
        random_ids = pl.Series("_random", [os.urandom(batch.height * 16).hex()])
        random_ids = random_ids.str.extract_all(r".{32}").explode(empty_as_null=False)
        ids = random_ids.to_frame().select(pl.concat_str([
            random.str.slice(0, 8), random.str.slice(8, 4),
            pl.lit("4") + random.str.slice(13, 3),
            random.str.slice(16, 1).str.replace_many(
                list("0123456789abcdef"), list("89ab89ab89ab89ab"),
            ) + random.str.slice(17, 3),
            random.str.slice(20, 12),
        ], separator="-").alias("id")).to_series()
        has_modes = failure_frame is not None and failure_frame.frame.height > 0
        if has_modes:
            joined = batch.select("raw_text").join(
                failure_frame.frame, on="raw_text",
                how="left", maintain_order="left",
            )
            batch = batch.with_columns(
                joined["modes"].fill_null([]).alias("_modes")
            )
            failure_column = pl.col("_modes").list.join(",")
        else:
            failure_column = pl.lit("")
        has_src = pl.col("src_ip") != ""
        aggregates = [
            pl.col("timestamp").min(),
            pl.col("pod_name").filter(pl.col("pod_name") != "").unique(maintain_order=True),
            pl.col("cluster_name").filter(pl.col("cluster_name") != "").unique(maintain_order=True),
            pl.col("src_ip").filter(has_src).last().fill_null(""),
            pl.col("dst_ip").filter(has_src).last().fill_null(""),
            pl.col("operation").filter(pl.col("operation") != "").first().fill_null(""),
        ]
        if has_modes:
            aggregates.extend([
                pl.col("_modes").explode(empty_as_null=True).drop_nulls().unique(maintain_order=True).alias("failure_modes"),
                pl.col("_modes").filter(pl.col("status_code") != "").explode(empty_as_null=True).drop_nulls()
                .unique(maintain_order=True).alias("access_failure_modes"),
            ])
        groups = batch.group_by("trace_id", maintain_order=True).agg(aggregates)

        # Chrono accepts excess precision, leap seconds and year zero; the
        # database utility rejects them. Preserve its timestamp semantics.
        stamp = batch["timestamp"]
        canonical = stamp.str.contains(r"^[0-9]{4}-[0-9]{2}-[0-9]{2} [0-9]{2}:[0-9]{2}:[0-5][0-9](?:\.[0-9]{1,6})?$")
        canonical = canonical & (stamp.str.slice(0, 4) != "0000")
        parsed = stamp.str.to_datetime("%Y-%m-%d %H:%M:%S%.f", strict=False, time_unit="us")
        if not canonical.all():
            fallback = [parse_timestamp(value) for value in stamp.filter(~canonical)]
            parsed = parsed.scatter((~canonical).arg_true(), fallback)
        record_frame = batch.with_columns(
            ids, parsed.alias("timestamp"), pl.lit(log_id).alias("log_id"),
            pl.lit("Unknown").alias("host_name"), failure_column.alias("failure_mode"),
        ).select(LogFailureEventPGManager._LOG_FAILURE_COPY_COLUMNS)
        chunks: list[bytes] = []
        for chunk in record_frame.iter_slices(_CONTEXT_CSV_ROWS):
            buffer = BytesIO()
            chunk.write_csv(
                buffer, include_header=False, quote_style="non_numeric",
                null_value=_CSV_NULL, datetime_format=_CSV_DATETIME_FORMAT,
            )
            chunks.append(buffer.getvalue())
            del buffer, chunk
        del record_frame
        return batch.height, chunks, groups

    @staticmethod
    def _prepared_context_batches(frame: Any, failure_frame: _FailureModeFrame | None, log_id: str) -> Iterator[Any]:
        """Overlap native conversion/grouping/CSV with COPY using one queued batch.

        Only the producer touches the input iterator. Joining it before closing
        the reader also makes cancellation and failed COPY safe for gzip scans.
        """
        reader = iter(frame)

        def prepare_next():
            for batch in reader:
                if batch.height:
                    return StoreTraceContextLogsWorker._prepare_context_batch(
                        batch, failure_frame, log_id,
                    )
            return None

        executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="context-prepare")
        future = executor.submit(prepare_next)
        try:
            while (prepared := future.result()) is not None:
                future = executor.submit(prepare_next)
                yield prepared
                del prepared
        finally:
            future.cancel()
            executor.shutdown(wait=True, cancel_futures=True)
            close = getattr(reader, "close", None)
            if close is not None:
                close()

    @staticmethod
    def _merge_context_group_parts(parts: list, canonical) -> dict[str, _TraceContextState]:
        """Reduce per-batch trace groups into states with one native pass.

        每批的 group frame 只保留每 trace 的摘要；这里 concat 后再 group_by
        一次，把旧实现 O(批数 × trace 数) 的 Python 增量合并压成一次原生
        归约（min 时间戳、首现序去重 pod/cluster/modes、末个非空 src/dst、
        首个非空 operation），语义与逐批 merge 逐字段一致。
        """
        import polars as pl

        if not parts:
            return {}
        frame = pl.concat(parts) if len(parts) > 1 else parts[0]
        parts.clear()
        has_modes = "failure_modes" in frame.columns
        aggregates = [
            pl.col("timestamp").min(),
            pl.col("pod_name").explode().drop_nulls().unique(maintain_order=True),
            pl.col("cluster_name").explode().drop_nulls().unique(maintain_order=True),
            pl.col("src_ip").filter(pl.col("src_ip") != "").last().fill_null(""),
            pl.col("dst_ip").filter(pl.col("src_ip") != "").last().fill_null(""),
            pl.col("operation").filter(pl.col("operation") != "").first().fill_null(""),
        ]
        if has_modes:
            aggregates.extend([
                pl.col("failure_modes").explode(empty_as_null=True).drop_nulls().unique(maintain_order=True),
                pl.col("access_failure_modes").explode(empty_as_null=True).drop_nulls().unique(maintain_order=True),
            ])
        merged = frame.group_by("trace_id", maintain_order=True).agg(aggregates)
        states: dict[str, _TraceContextState] = {}
        for row in merged.iter_rows():
            trace_id, timestamp, pods, clusters, src, dst, operation, *mode_columns = row
            state = _TraceContextState(
                timestamp,
                tuple(canonical(pod) for pod in pods if pod),
                tuple(canonical(cluster) for cluster in clusters if cluster),
                canonical(src), canonical(dst), operation or "",
            )
            if mode_columns and mode_columns[0]:
                state.failure_modes = tuple(mode_columns[0])
            if len(mode_columns) > 1 and mode_columns[1]:
                state.access_failure_modes = tuple(mode_columns[1])
            states[trace_id] = state
        return states

    @staticmethod
    async def _ingest_context_frames(
        frame: Any, trace_failure_id: Any, log_id: str, task_id: str | None,
        total_log_failure_events: int, progress_base: float, progress_end: float,
    ) -> tuple[int, dict[str, _TraceContextState]]:
        """One atomic CSV COPY over bounded blocks; retain only trace summaries."""
        failure_frame = _as_failure_frame(trace_failure_id)
        strings: dict[str, str] = {"": ""}
        total_inserted = 0
        last_report = time.monotonic()
        report_task = None
        group_parts: list = []
        reader = StoreTraceContextLogsWorker._prepared_context_batches(
            frame, failure_frame, log_id
        )

        def canonical(value):
            if len(strings) < 4096:
                return strings.setdefault(value, value)
            return strings.get(value, value)

        async def report_progress(inserted):
            progress = progress_base
            if total_log_failure_events:
                progress += (progress_end - progress_base) * inserted / total_log_failure_events
            try:
                await BaseWorker.report(task_id, f"Trace context logs stored {inserted}", min(progress, progress_end))
            except Exception:
                logger.warning("Trace context progress report failed", exc_info=True)

        def chunks():
            nonlocal total_inserted, last_report, report_task
            for row_count, csv_chunks, groups in reader:
                group_parts.append(groups)
                total_inserted += row_count
                yield from csv_chunks
                del csv_chunks
                now = time.monotonic()
                if (task_id and now - last_report >= 1.0
                        and (report_task is None or report_task.done())):
                    report_task = asyncio.create_task(report_progress(total_inserted))
                    last_report = now

        async def source():
            for chunk in chunks():
                yield chunk

        stream = source()
        try:
            await LogFailureEventPGManager.add_log_failure_event_csv(stream)
        except Exception as exc:
            raise ContextStoreError("Failed to store trace context batch") from exc
        finally:
            await stream.aclose()
            close = getattr(reader, "close", None)
            if close is not None:
                close()
            if report_task is not None:
                await report_task
        states = StoreTraceContextLogsWorker._merge_context_group_parts(
            group_parts, canonical
        )
        return total_inserted, states

    @staticmethod
    async def _ingest_log_failure_events(
        log_files: list[tuple[str, str]],
        trace_id_set: set[str],
        trace_failure_id: dict[str, list[str]] | _FailureModeFrame | None,
        failure_mode_cache: dict,
        log_id: str,
        task_id: str | None,
        use_polars: bool,
        frame: Any,
        total_log_failure_events: int,
        progress_base: float,
        progress_end: float,
        worker_access_patterns: list[str],
        client_access_patterns: list[str],
    ) -> tuple[int, dict[str, _TraceContextState]]:
        """Consume bounded scan batches, retaining compact per-trace state only."""
        if use_polars:
            return await StoreTraceContextLogsWorker._ingest_context_frames(
                frame, trace_failure_id, log_id, task_id, total_log_failure_events,
                progress_base, progress_end,
            )
        trace_failure_events_map: dict[str, _TraceContextState] = {}
        total_inserted = 0
        pending: list = []
        # Reuse common pod/cluster/IP strings across traces. Bound this cache so
        # unexpectedly high cardinality cannot turn it into another row store.
        strings: dict[str, str] = {"": ""}
        lookup_modes = trace_failure_id.get if trace_failure_id else None
        last_report = time.monotonic()
        report_task: asyncio.Task | None = None

        def canonical(value: str) -> str:
            if len(strings) < 4096:
                return strings.setdefault(value, value)
            return strings.get(value, value)

        async def write_batch(batch: list) -> None:
            nonlocal total_inserted, last_report, report_task
            try:
                await LogFailureEventPGManager.add_log_failure_event_raw(batch)
            except Exception as exc:
                raise ContextStoreError("Failed to store trace context batch") from exc
            total_inserted += len(batch)
            # Keep at most one report in flight, so a slow reporting connection
            # neither accumulates tasks nor stalls the COPY path.
            now = time.monotonic()
            if (task_id and now - last_report >= 1.0
                    and (report_task is None or report_task.done())):
                if total_log_failure_events:
                    progress = progress_base + (progress_end - progress_base) * total_inserted / total_log_failure_events
                else:
                    progress = progress_base
                report_task = asyncio.create_task(report_progress(total_inserted, progress))
                last_report = now

        async def report_progress(inserted: int, progress: float) -> None:
            try:
                await BaseWorker.report(
                    task_id, f"Trace context logs stored {inserted}", min(progress, progress_end),
                )
            except Exception:
                logger.warning("Trace context progress report failed", exc_info=True)

        reader = iter(frame)
        try:
            for batch in reader:
                rows = batch
                # One random read per batch instead of one system call per row.
                random_ids = os.urandom(len(rows) * 16).hex()
                for index, row in enumerate(rows):
                    value = random_ids[index * 32:(index + 1) * 32]
                    row["id"] = (f"{value[:8]}-{value[8:12]}-4{value[13:16]}-"
                                 f"{_UUID_VARIANTS[value[16]]}{value[17:20]}-{value[20:]}")
                    row["log_id"] = log_id
                    row["host_name"] = "Unknown"
                    row["failure_mode"] = lookup_modes(row["raw_text"], []) if lookup_modes else None
                    row["src_ip"], row["dst_ip"] = KVCacheLogEventDiagnosisWorker._extract_src_dst_ip(row["raw_text"])
                    row["operation"] = KVCacheLogEventDiagnosisWorker._extract_operation(row["raw_text"])
                    trace_id = row["trace_id"]
                    state = trace_failure_events_map.get(trace_id)
                    if state is None:
                        row["pod_name"] = canonical(row["pod_name"])
                        row["cluster_name"] = canonical(row["cluster_name"])
                        state = _TraceContextState(
                            timestamp=row["timestamp"],
                            pod_names=(row["pod_name"],) if row["pod_name"] else (),
                            cluster_names=(row["cluster_name"],) if row["cluster_name"] else (),
                        )
                        trace_failure_events_map[trace_id] = state
                    elif row["pod_name"] not in state.pod_names:
                        row["pod_name"] = canonical(row["pod_name"])
                    if row["cluster_name"] not in state.cluster_names:
                        row["cluster_name"] = canonical(row["cluster_name"])
                    if row["src_ip"]:
                        row["src_ip"] = canonical(row["src_ip"])
                        row["dst_ip"] = canonical(row["dst_ip"])
                    state.merge(row)
                # Native chunks can be shorter than the requested chunk size;
                # coalesce them so PostgreSQL still receives full COPY batches.
                if pending:
                    missing = _CONTEXT_BATCH_ROWS - len(pending)
                    pending.extend(rows[:missing])
                    rows = rows[missing:]
                    if len(pending) == _CONTEXT_BATCH_ROWS:
                        await write_batch(pending)
                        pending = []
                while len(rows) >= _CONTEXT_BATCH_ROWS:
                    await write_batch(rows[:_CONTEXT_BATCH_ROWS])
                    rows = rows[_CONTEXT_BATCH_ROWS:]
                pending = rows or pending
                del batch, rows
            if pending:
                await write_batch(pending)
        finally:
            close = getattr(reader, "close", None)
            if close is not None:
                close()
            if report_task is not None:
                await report_task
        return total_inserted, trace_failure_events_map

    @staticmethod
    async def _write_trace_failure_events(
        trace_failure_events_map: dict[str, _TraceContextState],
        failure_mode_cache: dict,
        total_inserted: int,
        total_log_failure_events: int,
        store_started_at: float,
        task_id: str | None,
        progress_end: float,
        log_id: str = "",
    ) -> None:
        """Stream completed trace state into a single atomic COPY."""
        trace_count = len(trace_failure_events_map)
        if trace_count:
            events = _TraceContextEvents(trace_failure_events_map, log_id, failure_mode_cache)
            try:
                await LogFailureEventPGManager.add_trace_failure_event_raw(events)
            finally:
                trace_failure_events_map.clear()
        logger.info(
            "Trace context logs store done: %s log_failure_events, %s trace_failure_events, total %.3fs",
            total_inserted, trace_count, time.perf_counter() - store_started_at,
        )
        if task_id:
            await BaseWorker.report(
                task_id, f"Trace context logs stored {total_inserted}/{total_inserted}", progress_end,
            )

    @staticmethod
    async def _store_trace_context_logs(
        output_log_path: str,
        log_id: str,
        trace_id_set: set,
        trace_failure_id: dict[str, list[str]] | _FailureModeFrame | None,
        task_id: str | None = None,
        progress_base: float = 0.0,
        progress_end: float = 100.0,
    ) -> None:
        # 将output_log_path下，除了failure_trace.log以外的所有日志读到log_failure_event_table数据库中
        # 除了failure_trace.log以外，output_log_path目录下的日志都是以下模板："timestamp | level | filename | pod_name | pid:tid | trace_id | cluster_name | message"，  
        # 对应LogFailureEventModel数据结构中的相应字段。除了这些字段以外，log_id对应函数参数输入，log_file对应日志文件名，raw_text对应原始日志。
        # status_code的读取方式略微复杂。仅当log_file对应的日志文件名能够匹配parse_filepath_config()得到的字典中，键为ds-worker-access-log-file和
        # ds-client-access-log-file的值所表示的正则表达式，即为access log日志时，日志才有status_code字段。具体而言，status_code字段是message字段中以" | "分割的第一个字段
        # 将failure_trace.log中的故障模式字段添加到数据库中
        # 将output_log_path下的failure_trace.log中是解析到的所有故障日志。每行日志的格式为failure_mode | raw_text，即将failure_mode字段添加到raw_text对应行的数据库条目中。你应该需要在
        # LogFailureEventManager中加入一个update_failure_mode_by_raw_log函数来完成数据库更新的操作。
        try:
            if not trace_id_set:
                logger.info("failure_trace.log 中没有可落库的 trace_id")
                return

            (
                worker_access_patterns,
                client_access_patterns,
                failure_mode_cache,
                log_files,
            ) = await StoreTraceContextLogsWorker._load_store_context(output_log_path, log_id)

            (
                total_log_failure_events,
                use_polars,
                frame,
            ) = StoreTraceContextLogsWorker._scan_context_rows(
                log_files, trace_id_set, worker_access_patterns, client_access_patterns
            )

            logger.info(
                f"开始流式日志落库，共{len(trace_id_set)}条故障trace"
                f"（扫描={'polars' if use_polars else 'legacy'}）"
            )
            t_store_start = time.perf_counter()

            (
                total_inserted,
                trace_failure_events_map,
            ) = await StoreTraceContextLogsWorker._ingest_log_failure_events(
                log_files=log_files,
                trace_id_set=trace_id_set,
                trace_failure_id=trace_failure_id,
                failure_mode_cache=failure_mode_cache,
                log_id=log_id,
                task_id=task_id,
                use_polars=use_polars,
                frame=frame,
                total_log_failure_events=total_log_failure_events,
                progress_base=progress_base,
                progress_end=progress_end,
                worker_access_patterns=worker_access_patterns,
                client_access_patterns=client_access_patterns,
            )

            await StoreTraceContextLogsWorker._write_trace_failure_events(
                trace_failure_events_map=trace_failure_events_map,
                failure_mode_cache=failure_mode_cache,
                total_inserted=total_inserted,
                total_log_failure_events=total_log_failure_events,
                store_started_at=t_store_start,
                task_id=task_id,
                progress_end=progress_end,
                log_id=log_id,
            )

            return

        except Exception as e:
            # 不打第二套机制：上下文留全后照旧外抛，由 run() 统一落失败原因
            logger.exception(
                "parse_log_failure_events 执行失败: %s (task_id=%s, log_id=%s, output_log_path=%s)",
                e,
                task_id,
                log_id,
                output_log_path,
            )
            raise

        return

    @staticmethod
    async def init(op_id: str) -> str | None:
        log_file_model = await LogFilePGManager.get_log_file_by_log_file_id(op_id)
        if not log_file_model:
            return None

        task = TaskModel(
            kb_id=log_file_model.kb_id,
            op_id=op_id,
            task_name=f"Store trace context logs: {log_file_model.name}",
            task_type=TaskTypeEnum.STORE_TRACE_CONTEXT_LOGS_WORKER,
            status=TaskStatusEnum.PENDING,
        )
        await TaskPGManager.add_task(task)
        await BaseWorker.report(task.id, "Task initialized", 0.0)
        return task.id

    @staticmethod
    async def reinit(task_id: str) -> bool:
        task = await TaskPGManager.get_task_by_task_id(task_id)
        if not task:
            return False
        if task.retry_times >= Config().get_config().task.task_retry_times:
            logger.warning(
                "Task %s retry count %s exceeded max retries %s",
                task_id,
                task.retry_times,
                Config().get_config().task.task_retry_times,
            )
            return False
        await BaseWorker.report(task.id, "Task reinitialized", 0.0)
        return True

    @staticmethod
    async def deinit(task_id: str) -> str:
        return task_id

    @staticmethod
    async def _wait_for_worker_success(
        op_id: str,
        task_type: TaskTypeEnum,
        dependency_name: str,
        monitor_task_id: str,
        progress: float,
    ) -> bool:
        while True:
            task = await TaskPGManager.get_current_task_by_op_id(op_id, task_type)
            if not task:
                await BaseWorker.report(
                    monitor_task_id,
                    f"Waiting for {dependency_name} task to be created",
                    progress,
                )
                await asyncio.sleep(MONITOR_INTERVAL_SECONDS)
                continue

            if task.status in SUCCESS_STATUSES:
                await BaseWorker.report(
                    monitor_task_id,
                    f"{dependency_name} task completed",
                    progress,
                )
                return True

            if task.status in FAILED_STATUSES:
                logger.error(
                    "%s task %s ended with status %s",
                    dependency_name,
                    task.id,
                    task.status,
                )
                await BaseWorker.report(
                    monitor_task_id,
                    f"{dependency_name} task ended with status {task.status}",
                    progress,
                )
                return False

            await BaseWorker.report(
                monitor_task_id,
                f"Waiting for {dependency_name} task, current status: {task.status}",
                progress,
            )
            await asyncio.sleep(MONITOR_INTERVAL_SECONDS)

    @staticmethod
    async def run(task_id: str, log_dir: str | None = None) -> bool:
        output_log_path = None
        log_file_id = None
        log_id = None
        t_run_start = time.perf_counter()  # [timing] 阶段偏移的基准 = run() 起点
        try:
            task = await TaskPGManager.get_task_by_task_id(task_id)
            if not task:
                logger.error("Task %s not found", task_id)
                return False

            await TaskPGManager.update_task(
                task_id, {"status": TaskStatusEnum.RUNNING.value}
            )
            await BaseWorker.report(task.id, "Task running", 5.0)
            # [timing] 三段在这里登记（契约见 common/stage_timing.py）：
            # 等诊断/等解析 → 生成 trace_id 集合 → 落库；任务成功结束前 emit。
            timer = StageTimer(
                started_at=t_run_start,
                wall_started_at=getattr(task, "created_at", None),
                task_type=TaskTypeEnum.STORE_TRACE_CONTEXT_LOGS_WORKER.value,
            )

            log_file = await LogFilePGManager.get_log_file_by_log_file_id(task.op_id)
            if not log_file:
                logger.error("LogFile %s not found", task.op_id)
                await TaskPGManager.mark_failed_with_report(
                    task_id,
                    f"任务失败：日志文件不存在（{task.op_id}）",
                    status=TaskStatusEnum.FAILED_PENDING_REMOVE,
                )
                cleanup_temp_dirs(None, task.op_id)
                return False

            log_id = log_file.id
            log_file_id = log_file.id
            random_str = log_file.id[:8]
            output_log_path = os.path.join(witty_dir, "log_" + random_str)

            diagnosis_trace_ids = await StoreTraceContextLogsWorker._stage_after_diagnosis(
                task, timer, output_log_path, log_id, log_file_id
            )
            if diagnosis_trace_ids is None:  # None=已按失败收敛；空集合是合法结果
                return False

            if not await StoreTraceContextLogsWorker._stage_after_parse(
                task, timer, output_log_path, log_id, log_file_id, diagnosis_trace_ids
            ):
                return False

            await StoreTraceContextLogsWorker._finish_run(
                task, log_file, output_log_path, log_file_id, timer
            )
            return True
        except Exception as e:
            # 该吞还得吞：更新任务状态后返回 False，但栈与定位信息留全
            logger.exception(
                "Task %s failed (log_id=%s, output_log_path=%s): %s",
                task_id,
                log_id,
                output_log_path,
                e,
            )
            await TaskPGManager.mark_failed_with_report(
                task_id,
                f"任务失败：Trace 上下文落库异常，{type(e).__name__}: {e}",
                status=TaskStatusEnum.FAILED_PENDING_REMOVE,
            )
            return False

    @staticmethod
    async def _stage_after_diagnosis(
        task: TaskModel,
        timer: StageTimer,
        output_log_path: str,
        log_id: str,
        log_file_id: str,
    ) -> set[str] | None:
        """输入：任务 + 计时器 + 输出目录 → 输出：定界 trace_id 集合；失败收敛时返回 None。"""
        with timer.stage("trace_store_wait") as wait_scope:
            wait_scope.detail = "等故障定界完成"
            diagnosis_done = await StoreTraceContextLogsWorker._wait_for_worker_success(
                task.op_id,
                TaskTypeEnum.KV_CACHE_LOG_EVENT_DIAGNOSIS_WORKER,
                "diagnosis",
                task.id,
                20.0,
            )
            if not diagnosis_done:
                await TaskPGManager.mark_failed_with_report(
                    task.id,
                    "任务失败：依赖的故障诊断任务未成功完成",
                    status=TaskStatusEnum.FAILED_PENDING_REMOVE,
                )
                cleanup_temp_dirs(output_log_path, log_file_id)
                return None

            # 检查任务是否被取消
            current_task = await TaskPGManager.get_task_by_task_id(task.id)
            if not current_task or current_task.status == TaskStatusEnum.CANCELLED:
                logger.warning(f"任务 {task.id} 已被取消或不存在，停止执行")
                cleanup_temp_dirs(output_log_path, log_file_id)
                return None

            if not os.path.isdir(output_log_path) or not os.listdir(output_log_path):
                logger.error(f"诊断输出目录不存在或为空: {output_log_path}")
                await TaskPGManager.mark_failed_with_report(
                    task.id,
                    f"任务失败：诊断输出目录不存在或为空（{output_log_path}）",
                    status=TaskStatusEnum.FAILED_PENDING_REMOVE,
                )
                cleanup_temp_dirs(output_log_path, log_file_id)
                return None

        with timer.stage("trace_store_collect") as collect_scope:
            trace_id_set, trace_failure_id = await StoreTraceContextLogsWorker._generate_trace_id_set_diagnosis(
                output_log_path=output_log_path,
                compact=True,
            )
            collect_scope.detail = f"定界产出 {len(trace_id_set)} 个故障 trace"

        with timer.stage("trace_store_write") as write_scope:
            await StoreTraceContextLogsWorker._store_trace_context_logs(
                output_log_path=output_log_path,
                log_id=log_id,
                trace_id_set=trace_id_set,
                trace_failure_id=trace_failure_id,
                task_id=task.id,
                progress_base=20.0,
                progress_end=45.0,
            )
            # Raw diagnostic lines are no longer needed while waiting for parse.
            del trace_failure_id
            await LogFilePGManager.update_log_file(
                task.op_id, {
                    "failure_count": len(trace_id_set),
                    "trace_failure_event_cnt": len(trace_id_set),
                }
            )
            await BaseWorker.report(
                task.id,
                f"Trace context logs stored after diagnosis: {len(trace_id_set)}",
                45.0,
            )
            write_scope.detail = f"故障 trace {len(trace_id_set)} 条落库"

        return trace_id_set

    @staticmethod
    async def _stage_after_parse(
        task: TaskModel,
        timer: StageTimer,
        output_log_path: str,
        log_id: str,
        log_file_id: str,
        diagnosis_trace_id_set: set[str],
    ) -> bool:
        """输入：任务 + 计时器 + 定界 trace 集合 → 输出：True=可以收尾，False=已按失败收敛。"""
        with timer.stage("trace_store_wait") as wait_scope:
            wait_scope.detail = "等解析完成"
            parse_done = await StoreTraceContextLogsWorker._wait_for_worker_success(
                task.op_id,
                TaskTypeEnum.KV_CACHE_LOG_PARSE_WORKER,
                "parse",
                task.id,
                65.0,
            )
            if not parse_done:
                await TaskPGManager.mark_failed_with_report(
                    task.id,
                    "任务失败：依赖的日志解析任务未成功完成",
                    status=TaskStatusEnum.FAILED_PENDING_REMOVE,
                )
                cleanup_temp_dirs(output_log_path, log_file_id)
                return False

            # 检查任务是否被取消
            current_task = await TaskPGManager.get_task_by_task_id(task.id)
            if not current_task or current_task.status == TaskStatusEnum.CANCELLED:
                logger.warning(f"任务 {task.id} 已被取消或不存在，停止执行")
                cleanup_temp_dirs(output_log_path, log_file_id)
                return False

        with timer.stage("trace_store_collect") as collect_scope:
            t_ids = time.perf_counter()
            latency_anomalous_trace_id_set = await LogParseResultPGManager.list_anomalous_trace_ids_by_log_id(
                log_id
            )
            anomalous_trace_count = len(latency_anomalous_trace_id_set)
            latency_anomalous_trace_id_set.difference_update(diagnosis_trace_id_set)
            trace_id_set = latency_anomalous_trace_id_set
            collect_scope.detail = f"解析新增时延异常 {len(trace_id_set)} 个 trace_id"
            logger.info(
                "新增 %s 个时延异常 trace_id",
                len(trace_id_set),
            )
            logger.info("[perf][context.ids] new_traces=%d elapsed_s=%.3f",
                        len(trace_id_set), time.perf_counter() - t_ids)

        with timer.stage("trace_store_write") as write_scope:
            await StoreTraceContextLogsWorker._store_trace_context_logs(
                output_log_path=output_log_path,
                log_id=log_id,
                trace_id_set=trace_id_set,
                trace_failure_id=None,
                task_id=task.id,
                progress_base=65.0,
                progress_end=90.0,
            )
            await BaseWorker.report(
                task.id,
                f"Trace context logs stored after parse: {anomalous_trace_count}",
                90.0,
            )
            write_scope.detail = f"时延异常 trace {len(trace_id_set)} 条落库"
        return True

    @staticmethod
    async def _finish_run(
        task: TaskModel,
        log_file: LogFileModel,
        output_log_path: str,
        log_file_id: str,
        timer: StageTimer,
    ) -> None:
        """输入：任务 + 日志文件 + 计时器 → 输出：无（清临时目录、置成功、发 [timing] 打点）。"""
        if log_file.kb_id:
            # failure_count 刚更新到 log_file，重新聚合保证 KB 计数同步。
            await LogKnowledgePGManager.refresh_kb_counters(log_file.kb_id)

        cleanup_temp_dirs(output_log_path, log_file_id)
        await BaseWorker.report(task.id, "Task completed successfully", 100.0)
        await TaskPGManager.update_task(
            task.id, {"status": TaskStatusEnum.SUCCESSFUL_PENDING_REMOVE.value}
        )
        try:  # 打点失败绝不影响任务成败
            await timer.emit(task.id, rows=0)
        except Exception:
            logger.warning("[timing] emit failed for %s", task.id, exc_info=True)

    @staticmethod
    async def stop(task_id: str) -> str | None:
        task = await TaskPGManager.get_task_by_task_id(task_id)
        if not task:
            return None
        if task.status in [TaskStatusEnum.PENDING, TaskStatusEnum.RUNNING]:
            await TaskPGManager.update_task(
                task_id, {"status": TaskStatusEnum.CANCELLED.value}
            )
            return task_id
        return None

    @staticmethod
    async def delete(task_id: str) -> str:
        return task_id
