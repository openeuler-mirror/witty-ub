"""进程工作函数

包含子进程执行的扫描函数，负责：
1. 重建解析器实例（因为解析器不能被 pickle）
2. 使用多解析器扫描单个文件（文件只读一次）
3. 返回序列化后的结果

T6 (Block E) IO/解析解耦：
- 仅磁盘类型为 hdd 时启用（快 IO 下线程开销 > 收益，实测同步 270ms vs
  解耦 422ms——P1 决策，SSD/NVMe 保持同步）。
- 组级解耦（_scan_group_decoupled，多进程生产路径）：IO 线程逐个读整个
  文件（一次大块顺序读）→ 文件级队列（maxsize=2）；解析线程（唯一
  mutator）从队列取文件 → _iter_lines 惰性逐行解析。文件内容在内存中
  每份 1×（无 splitlines 二次复制），峰值 ≈ 3×文件大小（P1-5 Oracle）。
- 单文件解耦（_scan_file_multi_decoupled，asyncio 降级路径）：同一结构。
- 两路径共用 _parse_lines（T5 all-matching 路由），parity by construction。
"""

import logging
import os
import queue
import threading
import time
from collections import defaultdict
from dataclasses import dataclass
from typing import Optional

from latency.schemas.log import LogFileModel
from latency.schemas.ds_log import LogEntry
from latency.ENUM.ds_log import EntryType, TupleField
from latency.schemas.request import ParseConfig
from latency.common.ds_log_io import open_log
from latency.common.disk import detect_disk_type
from latency.parse.base_parser import (
    ACCESS_LOG_MIN_PARTS,
    AccessLogParser,
    _build_parsed_access,
)

logger = logging.getLogger(__name__)

_PROGRESS_UPDATE_LINES = 100_000
_CPROFILE_DIR_ENV = "WITTY_UB_CPROFILE_DIR"

# T6 (Block E): IO/解析解耦参数（P1-5 Oracle 内存预算）
_IO_QUEUE_MAXSIZE = 2                # 文件级队列上限：2×文件 + 解析中 1×文件 ≈ 3×文件
_IO_DECOUPLE_ENV = "WITTY_UB_IO_DECOUPLE"  # 强制覆盖开关（auto 按磁盘类型）
_QUEUE_STOP = object()               # 队列结束哨兵

# T8 (Block G): per-file IO/解析计时（纯观测）。方案 A：worker 返回 dict 内挂
# 保留键 __perf__（小 pickle 开销）→ 父进程 _merge_results 弹出打 [perf][total]
# 聚合日志；方案 B：子进程 logger 输出 [perf][file.io]/[perf][file.parse]
# （grep 通道）。两方案都做。无 per-line 计时；开销仅 2 次 perf_counter + 1 次写。
_PERF_MARKER = "__perf__"


@dataclass
class _PerFileTiming:
    """单文件 IO/解析耗时（ms）。解耦路径两字段由 IO/解析线程分别写。"""
    io_ms: float = 0.0
    parse_ms: float = 0.0


class _TimingCollector:
    """进程内单例：线程安全收集 per-file 计时。

    子进程模式：worker 复用同一实例，每次 _process_worker_func 起始 reset、
    结尾 snapshot_and_reset，group 间不串数据。asyncio 模式：主进程多个 group
    并发记录（lock 保护），_scan_with_asyncio gather 后 snapshot 一次。
    """

    def __init__(self) -> None:
        self._lock: threading.Lock = threading.Lock()
        self._timings: dict[str, _PerFileTiming] = {}

    def record(self, path: str, io_ms: float, parse_ms: float) -> None:
        with self._lock:
            timing = self._timings.setdefault(path, _PerFileTiming())
            timing.io_ms += io_ms
            timing.parse_ms += parse_ms

    def reset(self) -> None:
        with self._lock:
            self._timings.clear()

    def snapshot_and_reset(self) -> dict[str, dict[str, float]]:
        """返回 {basename: {"io_ms", "parse_ms"}} 并清空。"""
        with self._lock:
            data = {
                os.path.basename(p): {"io_ms": t.io_ms, "parse_ms": t.parse_ms}
                for p, t in self._timings.items()
            }
            self._timings.clear()
        return data


_TIMING_COLLECTOR = _TimingCollector()


def _record_file_timing(path: str, io_ms: float, parse_ms: float) -> None:
    """记录单文件计时 + 输出 grep 日志（方案 B）。调用方保证每文件恰好一次。"""
    _TIMING_COLLECTOR.record(path, io_ms, parse_ms)
    file_name = os.path.basename(path)
    logger.info(f"[perf][file.io] {file_name} io={io_ms:.1f}ms")
    logger.info(f"[perf][file.parse] {file_name} parse={parse_ms:.1f}ms")


def process_worker_func(
    file_group_files: list[tuple[str, list[int]]],
    group_id: int,
    parsers_info: list[dict],
    parse_config_dict: Optional[dict] = None,
    scan_scope: Optional[dict] = None,
) -> dict[str, list[dict]]:
    profile_dir = os.environ.get(_CPROFILE_DIR_ENV)
    if not profile_dir:
        return _process_worker_func(
            file_group_files,
            group_id,
            parsers_info,
            parse_config_dict,
            scan_scope,
        )

    import cProfile
    from pathlib import Path
    import time

    output_dir = Path(profile_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    profile_path = output_dir / (
        f"worker-{os.getpid()}-group-{group_id}-{time.time_ns()}.prof"
    )
    profiler = cProfile.Profile()
    try:
        return profiler.runcall(
            _process_worker_func,
            file_group_files,
            group_id,
            parsers_info,
            parse_config_dict,
            scan_scope,
        )
    finally:
        profiler.dump_stats(str(profile_path))


def _process_worker_func(
    file_group_files: list[tuple[str, list[int]]],
    group_id: int,
    parsers_info: list[dict],
    parse_config_dict: Optional[dict] = None,
    scan_scope: Optional[dict] = None,
) -> dict[str, list[dict]]:

    import logging
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.INFO)
    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(
            logging.Formatter(f'[Process-{group_id}] %(asctime)s %(levelname)s %(message)s')
        )
        logger.addHandler(handler)

    logger.info(f"Started processing group {group_id} with {len(file_group_files)} files")

    # T8: 每次调用独立计时区间（worker 进程被 pool 复用时防止 group 间串数据）
    _TIMING_COLLECTOR.reset()

    parsers = _rebuild_parsers(parsers_info, parse_config_dict)
    _apply_scan_scope(parsers, scan_scope)

    if file_group_files and all(_should_decouple(path) for path, _ in file_group_files):
        merged = _scan_group_decoupled(file_group_files, parsers, group_id)
    else:
        merged = _scan_group_serial(file_group_files, parsers, group_id)

    timing_data = _TIMING_COLLECTOR.snapshot_and_reset()

    total_entries = sum(len(entries) for entries in merged.values())
    logger.info(
        f"Group {group_id} completed: "
        f"{len(merged)} parsers, "
        f"{total_entries:,} total entries"
    )

    result = {}
    from .columnar import COLUMNS_KEY, entries_to_columns

    result[COLUMNS_KEY] = entries_to_columns(merged)

    if timing_data:
        result[_PERF_MARKER] = timing_data

    return result


def _rebuild_parsers(
    parsers_info: list[dict],
    parse_config_dict: Optional[dict],
) -> list:
    """
    重建解析器实例

    因为解析器实例不能被 pickle，需要在子进程中重新创建。
    """
    from latency.parse import (
        SdkAccessLogParser,
        WorkerAccessLogParser,
        UrmaLogParser,
        RemotePullLogParser,
        LinkLogParser,
        QueryMetaLogParser,
        WorkerInfoParser,
        ClientInfoParser,
    )

    parse_config = ParseConfig(**parse_config_dict) if parse_config_dict else None

    parser_class_map = {
        "SdkAccessLogParser": SdkAccessLogParser,
        "WorkerAccessLogParser": WorkerAccessLogParser,
        "UrmaLogParser": UrmaLogParser,
        "RemotePullLogParser": RemotePullLogParser,
        "LinkLogParser": LinkLogParser,
        "QueryMetaLogParser": QueryMetaLogParser,
        "WorkerInfoParser": WorkerInfoParser,
        "ClientInfoParser": ClientInfoParser,
    }

    parsers = []
    for info in parsers_info:
        class_name = info["class_name"]
        parser_class = parser_class_map.get(class_name)
        if parser_class:
            parser = parser_class(parse_config)
            parser._runtime_patterns = list(info.get("patterns", parser.patterns))
            parsers.append(parser)
        else:
            logger.warning(f"Unknown parser class: {class_name}")

    return parsers


def _apply_scan_scope(parsers: list, scan_scope: Optional[dict]) -> None:
    for parser in parsers:
        setter = getattr(parser, "set_scan_scope", None)
        if setter:
            setter(scan_scope)


def _scan_group_serial(
    file_group_files: list[tuple[str, list[int]]],
    parsers: list,
    group_id: int,
) -> dict[str, list]:
    """串行扫描文件组（非全 HDD 组/降级路径）：逐文件经 _scan_file_multi 处理。"""
    merged: dict[str, list] = defaultdict(list)
    for path, parser_indices in file_group_files:
        group_parsers = [parsers[idx] for idx in parser_indices]
        try:
            result = _scan_file_multi(group_parsers, path)
            for label, entries in result.items():
                merged[label].extend(entries)
        except Exception as e:
            logger.warning(f"Failed to scan {path}: {e}")
    return merged


def _scan_group_decoupled(
    file_group_files: list[tuple[str, list[int]]],
    parsers: list,
    group_id: int,
) -> dict[str, list]:
    """组级 IO/解析解耦（仅全组文件均为 HDD 时启用）。

    IO 线程逐个读整个文件（1MB 大块）→ 文件级队列（maxsize=2）；解析线程
    （唯一 mutator）从队列取文件 → _parse_lines 逐行解析。内存峰值 ≈ 3×文件。
    """
    q: queue.Queue = queue.Queue(maxsize=_IO_QUEUE_MAXSIZE)
    merged: dict[str, list] = defaultdict(list)
    timings: dict[str, _PerFileTiming] = {}
    timings_lock = threading.Lock()

    def _record(path: str, io_ms: float = 0.0, parse_ms: float = 0.0) -> None:
        with timings_lock:
            timing = timings.setdefault(path, _PerFileTiming())
            timing.io_ms += io_ms
            timing.parse_ms += parse_ms

    def _reader() -> None:
        try:
            for path, parser_indices in file_group_files:
                t_io = time.perf_counter()
                buf = _read_whole_file(path)
                io_ms = (time.perf_counter() - t_io) * 1000
                if buf is None:
                    continue
                _record(path, io_ms=io_ms)
                group_parsers = [parsers[idx] for idx in parser_indices]
                q.put((path, group_parsers, buf))
        finally:
            q.put(_QUEUE_STOP)

    def _parser_worker() -> None:
        while True:
            item = q.get()
            if item is _QUEUE_STOP:
                break
            path, group_parsers, buf = item
            try:
                t_parse = time.perf_counter()
                result = _parse_lines(group_parsers, path, _iter_lines(buf))
                parse_ms = (time.perf_counter() - t_parse) * 1000
                _record(path, parse_ms=parse_ms)
            except Exception as e:
                logger.warning(f"Failed to scan {path}: {e}")
                result = {p.label: [] for p in group_parsers}
            for label, entries in result.items():
                merged[label].extend(entries)

    _run_threads(_reader, _parser_worker, path_hint=group_id)
    for path, timing in timings.items():
        _record_file_timing(path, timing.io_ms, timing.parse_ms)
    return merged


def _run_threads(io_fn, parse_fn, path_hint) -> None:
    t_io = threading.Thread(target=io_fn, name=f"io-scan-{path_hint}")
    t_parse = threading.Thread(target=parse_fn, name=f"parse-scan-{path_hint}")
    t_io.start()
    t_parse.start()
    t_io.join()
    t_parse.join()


def _read_whole_file(path: str) -> Optional[str]:
    """IO 线程读整个文件 → 单个 str（一次大块顺序读，HDD 最友好）。

    解析线程用 _iter_lines 惰性逐行迭代，不构造 splitlines 列表（避免二次
    复制）；文件内容在内存中仅 1 份。读失败（gzip 损坏/缺失）返回 None。
    """
    try:
        with open_log(path) as f:
            return f.read()
    except EOFError:
        logger.warning(f"Skipping corrupted file {path}")
    except Exception as e:
        logger.warning(f"Error reading {path}: {e}")
    return None


def _iter_lines(text: str):
    """惰性按行迭代，保留行尾 '\n'（与 `for line in f` 完全一致，parity 对齐）。"""
    start = 0
    n = len(text)
    while start < n:
        idx = text.find("\n", start)
        if idx == -1:
            yield text[start:]
            return
        yield text[start:idx + 1]
        start = idx + 1


def _should_decouple(path: str) -> bool:
    """IO/解析解耦已关闭——实测 HDD 下线程开销 > 收益，统一走同步路径。"""
    return False


def _any_keyword_in(line: str, keywords: tuple[str, ...]) -> bool:
    for kw in keywords:
        if kw in line:
            return True
    return False


def _parser_may_match(parser, keywords, line: str) -> bool:
    """行是否可能命中该解析器。

    优先使用解析器自定义的行匹配器（如 WorkerInfoParser._line_may_match，
    它在关键字之外还包含 src/dst 兜底匹配）；否则退化为关键字检查。
    """
    may_match = getattr(parser, "_line_may_match", None)
    if may_match is not None:
        return may_match(line)
    return bool(keywords) and _any_keyword_in(line, keywords)


def _scan_file_multi(
    parsers: list,
    path: str,
) -> dict[str, list]:
    """扫描单文件：单解析器快路径优先；多解析器按磁盘类型分派解耦/同步。"""
    if len(parsers) == 1 and hasattr(parsers[0], 'scan_file'):
        return _scan_file_fast_path(parsers, path)
    if _should_decouple(path):
        return _scan_file_multi_decoupled(parsers, path)
    return _scan_file_multi_sync(parsers, path)


def _scan_file_fast_path(parsers: list, path: str) -> dict[str, list]:
    """单解析器快路径：WorkerInfoParser.scan_file 整文件一次遍历（不做解耦）。

    scan_file 内部自行读文件 + 解析，无法进一步拆分 → 全部计入 parse_ms。
    """
    t_parse = time.perf_counter()
    result = parsers[0].scan_file(path)
    parse_ms = (time.perf_counter() - t_parse) * 1000
    serialized = {}
    for label, entries in result.items():
        serialized[label] = [_serialize_entry(e) for e in entries]
    _record_file_timing(path, 0.0, parse_ms)
    return serialized


def _scan_file_multi_sync(
    parsers: list,
    path: str,
) -> dict[str, list]:
    """同步路径（SSD/NVMe/非 HDD）：逐行读 + 解析串行（原 _scan_file_multi 逻辑）。

    读与解析在同一循环内交错，IO 无法逐次分离 → io_ms = 总耗时 - parse_ms
    （即非解析时间，主要为磁盘等待），保证 io+parse ≈ 总耗时。
    """
    if len(parsers) == 1 and hasattr(parsers[0], 'scan_file'):
        return _scan_file_fast_path(parsers, path)
    t_total = time.perf_counter()
    try:
        with open_log(path) as f:
            t_parse = time.perf_counter()
            result = _parse_lines(parsers, path, f)
            parse_ms = (time.perf_counter() - t_parse) * 1000
    except EOFError:
        logger.warning(f"Skipping corrupted file {path}")
        return {p.label: [] for p in parsers}
    except Exception as e:
        logger.warning(f"Error reading {path}: {e}")
        return {p.label: [] for p in parsers}
    total_ms = (time.perf_counter() - t_total) * 1000
    _record_file_timing(path, total_ms - parse_ms, parse_ms)
    return result


def _scan_file_multi_decoupled(
    parsers: list,
    path: str,
) -> dict[str, list]:
    """单文件 IO/解析解耦：IO 线程读整文件（大块）→ 文件级队列；解析线程逐行解析。

    与组级解耦（_scan_group_decoupled）共享 _read_whole_file/_parse_lines；
    队列 maxsize=2 与组级口径一致（单文件实际占用 1 槽）。
    """
    if len(parsers) == 1 and hasattr(parsers[0], 'scan_file'):
        return _scan_file_fast_path(parsers, path)

    q: queue.Queue = queue.Queue(maxsize=_IO_QUEUE_MAXSIZE)
    result: dict[str, list] = {}
    timing = _PerFileTiming()

    def _reader() -> None:
        try:
            t_io = time.perf_counter()
            buf = _read_whole_file(path)
            timing.io_ms = (time.perf_counter() - t_io) * 1000
            q.put((path, buf))
        finally:
            q.put(_QUEUE_STOP)

    def _parser_worker() -> None:
        item = q.get()
        if item is _QUEUE_STOP:
            result.update({p.label: [] for p in parsers})
            return
        _, buf = item
        if buf is None:
            result.update({p.label: [] for p in parsers})
            return
        try:
            t_parse = time.perf_counter()
            result.update(_parse_lines(parsers, path, _iter_lines(buf)))
            timing.parse_ms = (time.perf_counter() - t_parse) * 1000
        except Exception as e:
            logger.warning(f"Failed to scan {path}: {e}")
            result.update({p.label: [] for p in parsers})

    _run_threads(_reader, _parser_worker, path_hint=os.path.basename(path))
    _record_file_timing(path, timing.io_ms, timing.parse_ms)
    return result


def _parse_lines(
    parsers: list,
    path: str,
    line_iter,
) -> dict[str, list]:
    """对行迭代器执行 T5 all-matching 解析（IO 已就绪）。

    同步路径（_scan_file_multi_sync）与解耦解析线程（_scan_group_decoupled /
    _scan_file_multi_decoupled）共用同一实现，parity by construction。
    返回 {parser.label: [LogEntry]}。
    """
    try:
        pod_ip = parsers[0].extract_pod_ip(path)
    except Exception as e:
        logger.warning(f"Failed to extract pod_ip from {path}: {e}")
        pod_ip = ""

    try:
        file_size = os.path.getsize(path)
    except OSError:
        file_size = 0

    log_file = LogFileModel(file_path=path, file_size=file_size)
    file_name = os.path.basename(path)

    results: dict[str, list] = {p.label: [] for p in parsers}
    line_count = 0
    match_counts = {p.label: 0 for p in parsers}

    parser_keywords = [
        getattr(p, '_keywords', None) for p in parsers
    ]
    # 合并所有解析器关键词为扁平元组，用于行级快速跳过
    all_keywords = tuple(
        kw for kws in parser_keywords if kws for kw in kws
    ) if any(parser_keywords) else ()
    # 部分解析器（WorkerInfoParser）在关键字之外还有 src/dst 兜底匹配，
    # 仅按 all_keywords 预过滤会丢掉这类行，因此需要额外的行匹配器兜底。
    has_extra_matcher = any(
        getattr(p, "_line_may_match", None) is not None for p in parsers
    )

    try:
        for line_no, line in enumerate(line_iter, 1):
            line_count += 1

            if line_no % _PROGRESS_UPDATE_LINES == 0:
                logger.info(
                    f"[Multi] scanning {file_name} | line {line_no:,}"
                )

            if not line or line[0] != "2":
                continue

            if all_keywords and not _any_keyword_in(line, all_keywords):
                if not has_extra_matcher or not any(
                    p._line_may_match(line)
                    for p in parsers
                    if getattr(p, "_line_may_match", None) is not None
                ):
                    continue

            parts = line.split("|")
            plen = len(parts)

            # 行分派：路由到所有匹配的解析器（all-matching）。
            # 共享文件（如 *_access.log 同时匹配 SDK+WorkerAccess；
            # *_runtime.log 同时匹配 SDK+WorkerInfo）的行必须被每个
            # 匹配解析器都处理，first-match-wins 会丢行导致 parity 漂移。
            matched_parsers = [
                p
                for p, kws in zip(parsers, parser_keywords)
                if _parser_may_match(p, kws, line)
            ]

            for parser in matched_parsers:
                # 仅 Access 格式解析器使用 _pre_parsed 优化；Run 格式
                # 解析器（WorkerInfoParser）在 match_line 内部自建
                # _build_run；plen 不足 13 时不设 _pre_parsed（让
                # parse_access_line 自然返回 None，避免 KeyError 噪音）。
                if isinstance(parser, AccessLogParser):
                    if plen >= ACCESS_LOG_MIN_PARTS:
                        parser._pre_parsed = _build_parsed_access(parts, plen)

                try:
                    entries = parser.match_line(line, pod_ip)
                    if entries:
                        if isinstance(entries, list):
                            for entry in entries:
                                entry.log_id = log_file.id
                                results[parser.label].append(entry)
                                match_counts[parser.label] += 1
                        else:
                            entries.log_id = log_file.id
                            results[parser.label].append(entries)
                            match_counts[parser.label] += 1
                except Exception as e:
                    logger.warning(
                        f"[{parser.label}] error on {file_name}:{line_no}: {e}"
                    )
                finally:
                    parser._pre_parsed = None

    except EOFError:
        logger.warning(f"Skipping corrupted file {path}")
    except Exception as e:
        logger.warning(f"Error reading {path}: {e}")

    for parser in parsers:
        label = parser.label
        logger.info(
            f"[{label}] done {file_name} | "
            f"lines {line_count:,} | match {match_counts[label]:,}"
        )

    return results


def _serialize_entry(entry) -> tuple:
    return (
        entry.timestamp,
        entry.operation,
        entry.elapsed_us,
        entry.data_size,
        entry.object_key,
        entry.trace_id,
        entry.pod_ip,
        entry.status_code,
        entry.resp_msg,
        entry.entry_type.value if entry.entry_type else None,
        entry.cluster_name,
        entry.src_addr,
        entry.dst_addr,
        entry.inflight_count,
        entry.request_size,
        entry.log_id,
    )


def _deserialize_entry(t: tuple):
    entry_type = t[TupleField.ENTRY_TYPE]
    if isinstance(entry_type, str):
        try:
            entry_type = EntryType(entry_type)
        except Exception:
            entry_type = None

    return LogEntry(
        timestamp=t[TupleField.TIMESTAMP],
        operation=t[TupleField.OPERATION],
        elapsed_us=t[TupleField.ELAPSED_US],
        data_size=t[TupleField.DATA_SIZE],
        object_key=t[TupleField.OBJECT_KEY],
        trace_id=t[TupleField.TRACE_ID],
        pod_ip=t[TupleField.POD_IP],
        status_code=t[TupleField.STATUS_CODE],
        resp_msg=t[TupleField.RESP_MSG],
        entry_type=entry_type,
        cluster_name=t[TupleField.CLUSTER_NAME],
        src_addr=t[TupleField.SRC_ADDR],
        dst_addr=t[TupleField.DST_ADDR],
        inflight_count=t[TupleField.INFLIGHT_COUNT],
        request_size=t[TupleField.REQUEST_SIZE],
        log_id=t[TupleField.LOG_ID],
    )
