"""并行文件扫描器 - 核心调度器

整合 Phase 1（文件去重读取）和 Phase 2（多进程并行），提供统一的扫描接口。
"""

import asyncio
import logging
import os
import time
from collections import defaultdict
from concurrent.futures import ProcessPoolExecutor
from dataclasses import dataclass, field
from typing import Optional

from latency.schemas.request import ParseConfig
from latency.ENUM.task import TaskSplitStrategy

from .file_parser_map_builder import FileParserMapBuilder
from .preprocessor import LogPreprocessor
from .process_worker import process_worker_func
from .task_splitter import FileGroup, ScanTaskSplitter

logger = logging.getLogger(__name__)


@dataclass
class ScanMetrics:
    """扫描性能指标"""
    total_files: int = 0
    total_processes: int = 0
    total_lines: int = 0
    total_entries: int = 0
    build_map_time_ms: float = 0.0
    split_time_ms: float = 0.0
    scan_time_ms: float = 0.0
    total_time_ms: float = 0.0
    per_group_metrics: list[dict] = field(default_factory=list)


class ParallelFileScanner:
    """
    并行文件扫描器

    整合文件去重读取（Phase 1）和多进程并行（Phase 2），提供高性能的日志扫描能力。

    核心特性:
    1. 文件去重：每个文件只读取一次，多个解析器同时匹配
    2. 多进程并行：突破 GIL 限制，利用多核 CPU
    3. 负载均衡：智能任务分组，避免单进程过载
    4. 优雅降级：多进程失败时自动降级到 asyncio

    使用示例:
        scanner = ParallelFileScanner(
            max_processes=8,
            split_strategy=TaskSplitStrategy.BY_FILE_SIZE,
        )
        parsed = await scanner.scan_all(log_dir, parsers, parse_config)
    """

    def __init__(
        self,
        max_processes: Optional[int] = None,
        split_strategy: TaskSplitStrategy = TaskSplitStrategy.BY_FILE_SIZE,
        use_multiprocessing: bool = True,
        decompress: bool = False,
    ):
        """
        参数:
            max_processes: 最大进程数（默认 CPU 核数）
            split_strategy: 任务分组策略
            use_multiprocessing: 是否使用多进程（False 则用 asyncio）
            decompress: 是否预解压 .gz 文件（False 则在 worker 中直接流式解压）
        """
        self.max_processes = max_processes or (os.cpu_count() or 4)
        self.split_strategy = split_strategy
        self.use_multiprocessing = use_multiprocessing
        self.decompress = decompress
        self.metrics = ScanMetrics()

    async def scan_all(
        self,
        log_dir: str,
        parsers: list,
        parse_config: Optional[ParseConfig] = None,
        scan_scope: Optional[dict] = None,
    ) -> dict[str, list]:
        """
        扫描所有日志文件

        参数:
            log_dir: 日志目录
            parsers: 解析器列表
            parse_config: 解析配置

        返回:
            {parser_label: [entries]} 所有解析结果
        """
        overall_start = time.perf_counter()

        # Step 1: 构建文件-解析器映射
        map_start = time.perf_counter()
        gz_mapping = {}
        if self.decompress:
            preprocessor = LogPreprocessor()
            gz_mapping = await preprocessor.decompress_all(log_dir)
        builder = FileParserMapBuilder(log_dir, parsers, gz_mapping=gz_mapping)
        file_parser_map = builder.build()
        self.metrics.build_map_time_ms = (time.perf_counter() - map_start) * 1000

        if not file_parser_map:
            logger.warning("No log files found")
            return {}

        self.metrics.total_files = len(file_parser_map)

        # Step 2: 任务分组
        split_start = time.perf_counter()
        actual_processes = min(self.max_processes, len(file_parser_map))
        splitter = ScanTaskSplitter(
            file_parser_map=file_parser_map,
            parsers=parsers,
            max_processes=actual_processes,
            strategy=self.split_strategy,
        )
        file_groups = splitter.split()
        self.metrics.split_time_ms = (time.perf_counter() - split_start) * 1000
        self.metrics.total_processes = len(file_groups)

        if not file_groups:
            logger.warning("No file groups after splitting")
            return {}

        # 诊断日志：检查文件分组情况
        group_sizes = []
        for group in file_groups:
            group_file_count = len(group.files)
            group_size = sum(
                os.path.getsize(path) if os.path.exists(path) else 0
                for path, _ in group.files
            )
            group_sizes.append((group.group_id, group_file_count, group_size))
        
        logger.info(
            f"Task splitting result: {len(file_groups)} groups, "
            f"{len(file_parser_map)} total files, "
            f"use_multiprocessing={self.use_multiprocessing}"
        )
        for group_id, file_count, size in group_sizes:
            logger.info(
                f"  Group {group_id}: {file_count} files, {size/1024/1024:.2f} MB"
            )

        # Step 3: 执行扫描
        scan_start = time.perf_counter()
        if self.use_multiprocessing and len(file_groups) > 1:
            logger.info(f"Using multiprocessing with {len(file_groups)} processes")
            try:
                results = await self._scan_with_multiprocessing(
                    file_groups, parsers, log_dir, parse_config, scan_scope
                )
            except Exception as e:
                logger.warning(
                    f"Multiprocessing failed, fallback to asyncio: {e}"
                )
                results = await self._scan_with_asyncio(
                    file_groups, parsers, scan_scope
                )
        else:
            logger.info(
                f"Using asyncio mode: use_multiprocessing={self.use_multiprocessing}, "
                f"len(file_groups)={len(file_groups)}"
            )
            results = await self._scan_with_asyncio(file_groups, parsers, scan_scope)

        self.metrics.scan_time_ms = (time.perf_counter() - scan_start) * 1000

        # Step 4: 汇总结果
        merged = self._merge_results(results)
        self.metrics.total_entries = sum(
            len(entries) for entries in merged.values()
        )

        self.metrics.total_time_ms = (time.perf_counter() - overall_start) * 1000

        # 输出性能指标
        self._log_metrics()

        return merged

    async def _scan_with_multiprocessing(
        self,
        file_groups: list[FileGroup],
        parsers: list,
        log_dir: str,
        parse_config: Optional[ParseConfig],
        scan_scope: Optional[dict],
    ) -> list[dict[str, list[dict]]]:
        """
        使用多进程执行扫描

        返回:
            [{parser_label: [serialized_entries]}, ...]
        """
        logger.info(
            f"Starting {len(file_groups)} processes for parallel scanning"
        )

        # 准备解析器信息（用于子进程重建）
        parsers_info = [
            {
                "label": p.label,
                "class_name": p.__class__.__name__,
            }
            for p in parsers
        ]

        # 序列化 parse_config
        parse_config_dict = parse_config.dict() if parse_config else None

        loop = asyncio.get_event_loop()
        with ProcessPoolExecutor(max_workers=len(file_groups)) as executor:
            futures = []
            for group in file_groups:
                future = loop.run_in_executor(
                    executor,
                    process_worker_func,
                    group.files,
                    group.group_id,
                    parsers_info,
                    parse_config_dict,
                    scan_scope,
                )
                futures.append(future)

            results = await asyncio.gather(*futures)

        return results

    async def _scan_with_asyncio(
        self,
        file_groups: list[FileGroup],
        parsers: list,
        scan_scope: Optional[dict] = None,
    ) -> list[dict[str, list]]:
        """
        使用 asyncio 执行扫描（单进程模式 / 降级模式）

        返回:
            [{parser_label: [entries]}, ...]
        """
        logger.info(
            f"Starting asyncio scanning with {len(file_groups)} groups"
        )

        # 构建 group_id → 解析器索引映射
        group_parser_map = {}
        for group in file_groups:
            all_indices = set()
            for _, indices in group.files:
                all_indices.update(indices)
            group_parser_map[group.group_id] = sorted(all_indices)

        tasks = []
        for group in file_groups:
            task = asyncio.create_task(
                self._scan_group_asyncio(group, parsers, scan_scope)
            )
            tasks.append(task)

        return await asyncio.gather(*tasks)

    async def _scan_group_asyncio(
        self,
        file_group: FileGroup,
        parsers: list,
        scan_scope: Optional[dict] = None,
    ) -> dict[str, list]:
        """异步扫描单个文件组（单进程模式）"""
        from .process_worker import _apply_scan_scope, _scan_file_multi, _serialize_entry

        _apply_scan_scope(parsers, scan_scope)

        tasks = []
        for path, parser_indices in file_group.files:
            group_parsers = [parsers[idx] for idx in parser_indices]
            task = asyncio.to_thread(_scan_file_multi, group_parsers, path)
            tasks.append(task)

        results = await asyncio.gather(*tasks)

        # 汇总并序列化（与多进程模式保持一致）
        merged = defaultdict(list)
        for result in results:
            for label, entries in result.items():
                for e in entries:
                    if isinstance(e, tuple):
                        merged[label].append(e)
                    else:
                        merged[label].append(_serialize_entry(e))

        return dict(merged)

    @staticmethod
    def _merge_results(
        results: list[dict[str, list]],
    ) -> dict[str, list]:
        merged = defaultdict(list)
        t0 = time.perf_counter()
        total_tuples = 0

        for result in results:
            for label, entries in result.items():
                if entries and isinstance(entries[0], tuple):
                    merged[label].extend(entries)
                    total_tuples += len(entries)
                else:
                    merged[label].extend(entries)

        merge_ms = (time.perf_counter() - t0) * 1000
        logger.info(
            f"Results merged: {len(results)} groups, "
            f"{len(merged)} parsers, "
            f"{sum(len(e) for e in merged.values()):,} total entries, "
            f"{total_tuples:,} tuples (no deserialization), "
            f"merge={merge_ms:.0f}ms"
        )

        return dict(merged)

    def _log_metrics(self) -> None:
        """输出性能指标日志"""
        logger.info(
            f"=== Scan Performance Metrics ===\n"
            f"  Total files:      {self.metrics.total_files}\n"
            f"  Processes:        {self.metrics.total_processes}\n"
            f"  Total entries:    {self.metrics.total_entries:,}\n"
            f"  Build map time:   {self.metrics.build_map_time_ms:.0f} ms\n"
            f"  Split time:       {self.metrics.split_time_ms:.0f} ms\n"
            f"  Scan time:        {self.metrics.scan_time_ms:.0f} ms\n"
            f"  Total time:       {self.metrics.total_time_ms:.0f} ms\n"
            f"  ================================"
        )
