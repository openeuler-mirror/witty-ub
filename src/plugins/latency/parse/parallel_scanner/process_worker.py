"""进程工作函数

包含子进程执行的扫描函数，负责：
1. 重建解析器实例（因为解析器不能被 pickle）
2. 使用多解析器扫描单个文件（文件只读一次）
3. 返回序列化后的结果
"""

import logging
import os
from collections import defaultdict
from typing import Optional

from latency.schemas.log import LogFileModel
from latency.schemas.ds_log import LogEntry
from latency.ENUM.ds_log import EntryType, TupleField
from latency.schemas.request import ParseConfig
from latency.common.ds_log_io import open_log

logger = logging.getLogger(__name__)

_PROGRESS_UPDATE_LINES = 100_000
_CPROFILE_DIR_ENV = "WITTY_UB_CPROFILE_DIR"


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

    parsers = _rebuild_parsers(parsers_info, parse_config_dict)
    _apply_scan_scope(parsers, scan_scope)

    merged = defaultdict(list)
    for path, parser_indices in file_group_files:
        group_parsers = [parsers[idx] for idx in parser_indices]
        try:
            result = _scan_file_multi(group_parsers, path)
            for label, entries in result.items():
                merged[label].extend(entries)
        except Exception as e:
            logger.warning(f"Failed to scan {path}: {e}")

    total_entries = sum(len(entries) for entries in merged.values())
    logger.info(
        f"Group {group_id} completed: "
        f"{len(merged)} parsers, "
        f"{total_entries:,} total entries"
    )

    serialized = {
        label: [e if isinstance(e, tuple) else _serialize_entry(e) for e in entries]
        for label, entries in merged.items()
    }

    return serialized


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


def _scan_file_multi(
    parsers: list,
    path: str,
) -> dict[str, list]:
    if len(parsers) == 1 and hasattr(parsers[0], 'scan_file'):
        result = parsers[0].scan_file(path)
        # 确保结果被正确序列化（与多解析器模式保持一致）
        serialized = {}
        for label, entries in result.items():
            serialized[label] = [_serialize_entry(e) for e in entries]
        return serialized

    results: dict[str, list] = {p.label: [] for p in parsers}

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

    line_count = 0
    match_counts = {p.label: 0 for p in parsers}

    parser_keywords = [
        getattr(p, '_keywords', None) for p in parsers
    ]
    # 合并所有解析器关键词为扁平元组，用于行级快速跳过
    all_keywords = tuple(
        kw for kws in parser_keywords if kws for kw in kws
    ) if any(parser_keywords) else ()

    try:
        with open_log(path) as f:
            for line_no, line in enumerate(f, 1):
                line_count += 1

                if line_no % _PROGRESS_UPDATE_LINES == 0:
                    logger.info(
                        f"[Multi] scanning {file_name} | line {line_no:,}"
                    )

                if not line or line[0] != "2":
                    continue

                if all_keywords and not _any_keyword_in(line, all_keywords):
                    continue

                parts = line.split("|")
                plen = len(parts)

                parser_idx = -1
                for i, kws in enumerate(parser_keywords):
                    if kws and _any_keyword_in(line, kws):
                        parser_idx = i
                        break

                if parser_idx < 0:
                    continue

                parser = parsers[parser_idx]
                if plen >= 13:
                    parser._pre_parsed = _build_parsed_access(parts, plen)
                elif plen >= 8:
                    parser._pre_parsed = _build_parsed_run(parts, plen)

                try:
                    entries = parser.match_line(line, pod_ip)
                    if entries:
                        # 处理 match_line 返回列表的情况（如 WorkerInfoParser）
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


def _build_parsed_access(parts: list[str], plen: int) -> dict:
    col = (0, 3, 5, 6, 7, 8, 9, 10, 11, 12)
    keys = ("timestamp", "pod_name", "trace_id", "cluster_name",
            "status_code", "handle", "elapsed", "size", "req_msg", "resp_msg")
    return {k: parts[idx].strip() if idx < plen else "" for k, idx in zip(keys, col)}


def _build_parsed_run(parts: list[str], plen: int) -> dict:
    col = (0, 3, 5, 6, 7)
    keys = ("timestamp", "pod_name", "trace_id", "cluster_name", "msg")
    return {k: parts[idx].strip() if idx < plen else "" for k, idx in zip(keys, col)}


def _any_keyword_in(line: str, keywords: tuple[str, ...]) -> bool:
    for kw in keywords:
        if kw in line:
            return True
    return False


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
