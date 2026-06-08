"""进程工作函数

包含子进程执行的扫描函数，负责：
1. 重建解析器实例（因为解析器不能被 pickle）
2. 使用多解析器扫描单个文件（文件只读一次）
3. 返回序列化后的结果
"""

import asyncio
import logging
import os
import traceback
from collections import defaultdict
from typing import Optional

from latency.schemas.log import LogFileModel
from latency.schemas.request import ParseConfig
from latency.common.ds_log_io import open_log

logger = logging.getLogger(__name__)

_PROGRESS_UPDATE_LINES = 100_000


def process_worker_func(
    file_group_files: list[tuple[str, list[int]]],
    group_id: int,
    parsers_info: list[dict],
    parse_config_dict: Optional[dict] = None,
) -> dict[str, list[dict]]:
    """
    子进程工作函数

    参数:
        file_group_files: 文件组 [(path, parser_indices), ...]
        group_id: 组 ID
        parsers_info: 解析器信息列表 [{"label": ..., "class_name": ...}, ...]
        parse_config_dict: 解析配置（dict 格式以便 pickle）

    返回:
        {parser_label: [serialized_entries]}
        每个 entry 已序列化为 dict
    """
    # 子进程配置日志
    logger.setLevel(logging.INFO)
    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(
            logging.Formatter(f'[Process-{group_id}] %(asctime)s %(levelname)s %(message)s')
        )
        logger.addHandler(handler)

    logger.info(f"Started processing group {group_id} with {len(file_group_files)} files")

    # 重建解析器
    parsers = _rebuild_parsers(parsers_info, parse_config_dict)

    async def _scan_group():
        """异步扫描文件组"""
        tasks = []
        for path, parser_indices in file_group_files:
            group_parsers = [parsers[idx] for idx in parser_indices]
            tasks.append(
                asyncio.to_thread(_scan_file_multi, group_parsers, path)
            )

        results = await asyncio.gather(*tasks)

        # 汇总结果
        merged = defaultdict(list)
        for result in results:
            for label, entries in result.items():
                merged[label].extend(entries)

        return dict(merged)

    loop = asyncio.new_event_loop()
    try:
        results = loop.run_until_complete(_scan_group())

        # 序列化结果（LogEntry → 紧凑元组）
        serialized = {
            label: [_serialize_entry(e) for e in entries]
            for label, entries in results.items()
        }

        total_entries = sum(len(entries) for entries in serialized.values())
        logger.info(
            f"Group {group_id} completed: "
            f"{len(serialized)} parsers, "
            f"{total_entries:,} total entries"
        )
        return serialized

    except Exception as e:
        logger.exception(f"Group {group_id} failed: {e}")
        raise
    finally:
        loop.close()


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
    )

    parse_config = ParseConfig(**parse_config_dict) if parse_config_dict else None

    parser_class_map = {
        "SdkAccessLogParser": SdkAccessLogParser,
        "WorkerAccessLogParser": WorkerAccessLogParser,
        "UrmaLogParser": UrmaLogParser,
        "RemotePullLogParser": RemotePullLogParser,
        "LinkLogParser": LinkLogParser,
        "QueryMetaLogParser": QueryMetaLogParser,
    }

    parsers = []
    for info in parsers_info:
        class_name = info["class_name"]
        parser_class = parser_class_map.get(class_name)
        if parser_class:
            parsers.append(parser_class(parse_config))
        else:
            logger.warning(f"Unknown parser class: {class_name}")

    return parsers


def _scan_file_multi(
    parsers: list,
    path: str,
) -> dict[str, list]:
    """
    用多个解析器同时扫描单个文件

    核心优化：文件只读取一次，每行被多个解析器匹配

    参数:
        parsers: 负责该文件的解析器列表
        path: 文件路径

    返回:
        {parser_label: [entries]}
    """
    # 初始化结果容器
    results: dict[str, list] = {p.label: [] for p in parsers}

    # 同一文件的 pod_ip 相同
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

    try:
        with open_log(path) as f:
            for line_no, line in enumerate(f, 1):
                line_count += 1

                # 进度日志
                if line_no % _PROGRESS_UPDATE_LINES == 0:
                    logger.info(
                        f"[Multi] scanning {file_name} | line {line_no:,}"
                    )

                # 核心：每个解析器尝试匹配当前行
                for parser in parsers:
                    try:
                        entry = parser.match_line(line, pod_ip)
                        if entry:
                            entry.log_id = log_file.id
                            results[parser.label].append(entry)
                            match_counts[parser.label] += 1
                    except Exception as e:
                        logger.warning(
                            f"[{parser.label}] error on {file_name}:{line_no}: {e}"
                        )

    except EOFError:
        logger.warning(f"Skipping corrupted file {path}")
    except Exception as e:
        logger.warning(f"Error reading {path}: {e}")

    # 输出统计
    for parser in parsers:
        label = parser.label
        logger.info(
            f"[{label}] done {file_name} | "
            f"lines {line_count:,} | match {match_counts[label]:,}"
        )

    return results


# LogEntry 紧凑元组序列化格式
# 索引: 0=timestamp, 1=operation, 2=elapsed_us, 3=data_size, 4=object_key,
#       5=trace_id, 6=pod_ip, 7=status_code, 8=resp_msg, 9=entry_type,
#       10=cluster_name, 11=src_addr, 12=dst_addr, 13=inflight_count,
#       14=request_size, 15=log_id


def _serialize_entry(entry) -> tuple:
    """
    将 LogEntry 序列化为紧凑元组

    相比 dict 格式节省约 80% 序列化体积：
    - dict: ~1.5KB/entry (含 key 字符串)
    - tuple: ~200 bytes/entry (纯值)
    """
    return (
        entry.timestamp.isoformat() if entry.timestamp else None,  # 0
        entry.operation,                                           # 1
        entry.elapsed_us,                                          # 2
        entry.data_size,                                           # 3
        entry.object_key,                                          # 4
        entry.trace_id,                                            # 5
        entry.pod_ip,                                              # 6
        entry.status_code,                                         # 7
        entry.resp_msg,                                            # 8
        entry.entry_type.value if entry.entry_type else None,      # 9
        entry.cluster_name,                                        # 10
        entry.src_addr,                                            # 11
        entry.dst_addr,                                            # 12
        entry.inflight_count,                                      # 13
        entry.request_size,                                        # 14
        entry.log_id,                                              # 15
    )


def _deserialize_entry(t: tuple):
    """
    将紧凑元组反序列化为 LogEntry

    用于主进程接收结果后重建对象
    """
    from datetime import datetime
    from latency.schemas.ds_log import LogEntry, EntryType

    # 反序列化时间戳
    timestamp = None
    if t[0]:
        try:
            timestamp = datetime.fromisoformat(t[0])
        except Exception:
            pass

    # 反序列化 entry_type
    entry_type = t[9]
    if isinstance(entry_type, str):
        try:
            entry_type = EntryType(entry_type)
        except Exception:
            entry_type = None

    return LogEntry(
        timestamp=timestamp,
        operation=t[1],
        elapsed_us=t[2],
        data_size=t[3],
        object_key=t[4],
        trace_id=t[5],
        pod_ip=t[6],
        status_code=t[7],
        resp_msg=t[8],
        entry_type=entry_type,
        cluster_name=t[10],
        src_addr=t[11],
        dst_addr=t[12],
        inflight_count=t[13],
        request_size=t[14],
        log_id=t[15],
    )
