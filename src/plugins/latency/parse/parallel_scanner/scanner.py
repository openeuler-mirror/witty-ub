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
from typing import Awaitable, Callable, Optional

from latency.schemas.request import ParseConfig
from latency.ENUM.task import TaskSplitStrategy
from latency.common.disk import io_concurrency_for

from .file_parser_map_builder import FileParserMapBuilder
from .preprocessor import LogPreprocessor
from .process_worker import (
    _PERF_MARKER,
    _TIMING_COLLECTOR,
    process_worker_func,
)
from .task_splitter import FileGroup, ScanTaskSplitter
from .columnar import COLUMNS_KEY

logger = logging.getLogger(__name__)

# T7: 有界提交死锁保护超时 — 窗口内任一任务超时未完成即判死锁, 取消并降级
# asyncio 路径。正常批次(数分钟级)远小于 600s, 不会误触发。
_BOUNDED_SUBMIT_WAIT_TIMEOUT_S = 600


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
        progress_cb: Optional[Callable[[float], Awaitable]] = None,
    ) -> dict[str, list]:
        """
        扫描所有日志文件

        参数:
            log_dir: 日志目录
            parsers: 解析器列表
            parse_config: 解析配置
            progress_cb: 可选扫描进度回调 ``async (fraction: float) -> None``，
                每个文件组完成后以 0.0→1.0 的单调递增比例调用；None 时不调用
                （向后兼容，既有调用方/测试不受影响）。

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
        # multiprocessing 主路径不做 IO 并发限制（池=窗口=全量）;
        # asyncio 降级路径保留 io_concurrency gate（T7 契约, fallback 限 IO）。
        io_concurrency = io_concurrency_for(log_dir)
        logger.info(
            f"asyncio fallback IO gate: disk io_concurrency={io_concurrency}"
        )
        scan_start = time.perf_counter()
        if self.use_multiprocessing and len(file_groups) > 1:
            logger.info(f"Using multiprocessing with {len(file_groups)} processes")
            try:
                results = await self._scan_with_multiprocessing(
                    file_groups,
                    parsers,
                    log_dir,
                    parse_config,
                    scan_scope,
                    io_concurrency=io_concurrency,
                    progress_cb=progress_cb,
                )
            except Exception as e:
                logger.warning(
                    f"Multiprocessing failed, fallback to asyncio: {e}"
                )
                results = await self._scan_with_asyncio(
                    file_groups,
                    parsers,
                    scan_scope,
                    io_concurrency=io_concurrency,
                    progress_cb=progress_cb,
                )
        else:
            logger.info(
                f"Using asyncio mode: use_multiprocessing={self.use_multiprocessing}, "
                f"len(file_groups)={len(file_groups)}"
            )
            results = await self._scan_with_asyncio(
                file_groups,
                parsers,
                scan_scope,
                io_concurrency=io_concurrency,
                progress_cb=progress_cb,
            )

        self.metrics.scan_time_ms = (time.perf_counter() - scan_start) * 1000

        # Step 4: 汇总结果
        merged = self._merge_results(results)
        self.metrics.total_entries = sum(
            len(entries)
            for label, entries in merged.items()
            if label != COLUMNS_KEY
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
        io_concurrency: Optional[int] = None,
        progress_cb: Optional[Callable[[float], Awaitable]] = None,
    ) -> list[dict[str, list[dict]]]:
        """
        使用多进程执行扫描

        T7: 进程池 max_workers 与有界提交窗口均按 IO 并发 cap 限制, 避免
        HDD 下全量提交导致 IO 风暴。

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
                "patterns": list(p.patterns),
            }
            for p in parsers
        ]

        # 序列化 parse_config
        parse_config_dict = parse_config.dict() if parse_config else None

        # 进程池大小决定解析并行度（吃满 CPU）; 有界提交窗口 = 池大小,
        # 即全量提交由进程池自然调度, 不做额外 IO 并发限制。
        parse_workers = max(1, self.max_processes or (os.cpu_count() or 1))
        logger.info(f"Parallel scanning: pool={parse_workers} workers")

        executor = ProcessPoolExecutor(max_workers=parse_workers)
        try:
            results = await self._submit_bounded_multiprocessing(
                executor,
                file_groups,
                parsers_info,
                parse_config_dict,
                scan_scope,
                parse_workers,
                progress_cb=progress_cb,
            )
        except Exception:
            # 卡死场景下 shutdown(wait=True) 会同步等 worker 结束而挂起 → 立即释放
            executor.shutdown(wait=False, cancel_futures=True)
            raise
        else:
            executor.shutdown(wait=True)

        return results

    async def _submit_bounded_multiprocessing(
        self,
        executor,
        file_groups: list[FileGroup],
        parsers_info: list[dict],
        parse_config_dict: Optional[dict],
        scan_scope: Optional[dict],
        max_concurrent: int,
        progress_cb: Optional[Callable[[float], Awaitable]] = None,
    ) -> list[dict[str, list[dict]]]:
        """有界提交: 同时最多 max_concurrent 个任务在途, 完成一个补位一个。

        parent 侧 asyncio.Semaphore 包提交循环是 no-op(所有 future 已同时
        提交), 因此这里用 asyncio.wait(FIRST_COMPLETED) 做真正的有界提交,
        并对每次等待加超时保护, 防止"完成一个补一个"死锁时永久挂起(P1-4)。
        返回顺序与 file_groups 一致, 保持原返回类型 list[dict]。

        progress_cb: 可选进度回调, 每完成一个 group 后以
            ``completed_groups / total_groups``（0.0→1.0 单调递增）调用。
        """
        pending: dict[asyncio.Future, int] = {}
        results: dict[int, dict[str, list[dict]]] = {}
        iterator = iter(enumerate(file_groups))
        total_groups = len(file_groups) or 1
        completed_groups = 0

        def _submit(group: FileGroup) -> asyncio.Future:
            return asyncio.wrap_future(
                executor.submit(
                    process_worker_func,
                    group.files,
                    group.group_id,
                    parsers_info,
                    parse_config_dict,
                    scan_scope,
                )
            )

        # 初始窗口: 一次提交 max_concurrent 个
        for _ in range(max_concurrent):
            try:
                index, group = next(iterator)
            except StopIteration:
                break
            pending[_submit(group)] = index

        while pending:
            try:
                done, _ = await asyncio.wait_for(
                    asyncio.wait(list(pending), return_when=asyncio.FIRST_COMPLETED),
                    timeout=_BOUNDED_SUBMIT_WAIT_TIMEOUT_S,
                )
            except asyncio.TimeoutError:
                for fut in list(pending):
                    fut.cancel()
                raise RuntimeError(
                    "Bounded multiprocess submission deadlocked: no group "
                    f"completed within {_BOUNDED_SUBMIT_WAIT_TIMEOUT_S}s "
                    f"(pending={len(pending)})"
                ) from None

            for fut in done:
                index = pending.pop(fut)
                try:
                    results[index] = await fut
                except Exception:
                    # 任务失败: 取消其余在途任务, 交由 scan_all 降级 asyncio 路径
                    for other in list(pending):
                        other.cancel()
                    raise
                completed_groups += 1

            if progress_cb is not None:
                await progress_cb(completed_groups / total_groups)

            # 补位: 每个完成的槽位提交下一个 group
            for _ in range(len(done)):
                try:
                    index, group = next(iterator)
                except StopIteration:
                    break
                pending[_submit(group)] = index

        return [results[i] for i in range(len(file_groups))]

    async def _scan_with_asyncio(
        self,
        file_groups: list[FileGroup],
        parsers: list,
        scan_scope: Optional[dict] = None,
        io_concurrency: Optional[int] = None,
        log_dir: Optional[str] = None,
        progress_cb: Optional[Callable[[float], Awaitable]] = None,
    ) -> list[dict[str, list]]:
        """
        使用 asyncio 执行扫描（单进程模式 / 降级模式）

        T7: 用 asyncio.Semaphore(max_concurrent) 包 _scan_file_multi 的
        to_thread 调用, 限制降级路径的 IO 并发(这里 Semaphore 是有效模式,
        因为 to_thread 是真正并发执行的, 与 multiprocessing 提交循环不同)。

        返回:
            [{parser_label: [entries]}, ...]
        """
        logger.info(
            f"Starting asyncio scanning with {len(file_groups)} groups"
        )

        if io_concurrency is None:
            io_concurrency = io_concurrency_for(log_dir) if log_dir else 3
        io_semaphore = asyncio.Semaphore(max(1, io_concurrency))
        logger.info(
            f"IO-aware asyncio gate: max_concurrent={io_concurrency} "
            f"(Semaphore around _scan_file_multi to_thread)"
        )

        # 构建 group_id → 解析器索引映射
        group_parser_map = {}
        for group in file_groups:
            all_indices = set()
            for _, indices in group.files:
                all_indices.update(indices)
            group_parser_map[group.group_id] = sorted(all_indices)

        # T8: asyncio 路径在父进程内计时（_scan_file_multi 写入共享收集器）。
        # 起始 reset 防止与其他扫描调用串数据；gather 后 snapshot 挂到首组结果。
        _TIMING_COLLECTOR.reset()

        async def _collect(index: int, group: FileGroup) -> tuple[int, dict]:
            return index, await self._scan_group_asyncio(
                group, parsers, scan_scope, io_semaphore
            )

        # as_completed 逐个收集, 每个 group 完成后触发 progress_cb（若提供）。
        tasks = [
            asyncio.create_task(_collect(index, group))
            for index, group in enumerate(file_groups)
        ]
        total_groups = len(tasks) or 1
        completed_groups = 0
        results = [None] * len(tasks)
        for done_task in asyncio.as_completed(tasks):
            index, result = await done_task
            results[index] = result
            completed_groups += 1
            if progress_cb is not None:
                await progress_cb(completed_groups / total_groups)

        timing_data = _TIMING_COLLECTOR.snapshot_and_reset()
        if timing_data and results:
            results[0][_PERF_MARKER] = timing_data
        return results

    async def _scan_group_asyncio(
        self,
        file_group: FileGroup,
        parsers: list,
        scan_scope: Optional[dict] = None,
        io_semaphore: Optional[asyncio.Semaphore] = None,
    ) -> dict[str, list]:
        """异步扫描单个文件组（单进程模式）"""
        from .process_worker import _apply_scan_scope, _scan_file_multi

        _apply_scan_scope(parsers, scan_scope)

        tasks = []
        for path, parser_indices in file_group.files:
            group_parsers = [parsers[idx] for idx in parser_indices]
            if io_semaphore is None:
                task = asyncio.to_thread(_scan_file_multi, group_parsers, path)
            else:
                task = self._bounded_to_thread(
                    io_semaphore, _scan_file_multi, group_parsers, path
                )
            tasks.append(task)

        results = await asyncio.gather(*tasks)

        # 汇总为列式输出（与多进程模式保持一致）
        merged = defaultdict(list)
        for result in results:
            for label, entries in result.items():
                merged[label].extend(entries)

        from .columnar import entries_to_columns

        return {COLUMNS_KEY: entries_to_columns(dict(merged))}

    @staticmethod
    async def _bounded_to_thread(semaphore: asyncio.Semaphore, func, *args):
        """Semaphore 包 to_thread: 真正限制并发线程数(IO 读)。"""
        async with semaphore:
            return await asyncio.to_thread(func, *args)

    @staticmethod
    def _merge_results(
        results: list[dict[str, list]],
    ) -> dict[str, list]:
        merged = defaultdict(list)
        merged_columns: dict | None = None
        t0 = time.perf_counter()

        perf_files = 0
        perf_io_ms = 0.0
        perf_parse_ms = 0.0

        for result in results:
            timing = result.pop(_PERF_MARKER, None)
            if isinstance(timing, dict):
                perf_files += len(timing)
                for file_name, t in timing.items():
                    perf_io_ms += t["io_ms"]
                    perf_parse_ms += t["parse_ms"]
            columns = result.pop(COLUMNS_KEY, None)
            if columns is not None:
                if merged_columns is None:
                    merged_columns = {k: list(v) for k, v in columns.items()}
                else:
                    for k, v in columns.items():
                        merged_columns[k].extend(v)

        merge_ms = (time.perf_counter() - t0) * 1000
        entry_count = len(merged_columns.get("_label", [])) if merged_columns else 0
        logger.info(
            f"Results merged: {len(results)} groups, "
            f"{entry_count:,} column rows, "
            f"merge={merge_ms:.0f}ms"
        )
        if perf_files:
            logger.info(
                f"[perf][total] files={perf_files} "
                f"io={perf_io_ms:.1f}ms parse={perf_parse_ms:.1f}ms"
            )

        if merged_columns is not None:
            merged[COLUMNS_KEY] = merged_columns
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
