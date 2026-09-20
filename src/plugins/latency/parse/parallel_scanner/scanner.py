"""并行文件扫描器（唯一路径：单进程两步法）。

```
scan_all(log_dir, parsers, ...)
  ├─ FileParserMapBuilder：文件 → 解析器（含 .gz）
  └─ scan_frame：一次读 + 一条列表达式链 + 一次 collect → 40 列 DataFrame
```

历史：这里曾经有三条路径（多进程逐行、asyncio 降级、单进程列运算）。前两条已删除 ——
不再有"回退"这回事：扫描要么按列运算跑通，要么把异常抛给调用方（任务失败，看得见）。
"""

import asyncio
import logging
import time
from dataclasses import dataclass, field
from typing import Awaitable, Callable, TYPE_CHECKING

from latency.schemas.request import ParseConfig

from .file_parser_map_builder import FileParserMapBuilder
from .preprocessor import LogPreprocessor
from .scan_vector import scan_frame
from .columnar import COLUMNS_KEY

if TYPE_CHECKING:  # 仅注解使用，运行时不导入
    from latency.ENUM.task import TaskSplitStrategy

logger = logging.getLogger(__name__)

#: scan_all 结果里"被跳过的坏文件"键：[(路径, 原因)]
SKIPPED_FILES_KEY = "skipped_files"

#: scan_all 结果里"轻列扫描现场"键（light=True 时才有）：ScanContext
SCAN_CTX_KEY = "scan_ctx"


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
    """扫描一个资产目录：文件 → 解析器映射，然后一次列运算出 40 列。"""

    def __init__(
        self: "ParallelFileScanner",
        max_processes: int | None = None,
        split_strategy: "TaskSplitStrategy | None" = None,
        use_multiprocessing: bool = True,
        decompress: bool = False,
    ) -> None:
        # 参数保留仅为兼容既有调用方；单进程列运算路径用不到它们。
        self.max_processes = max_processes
        self.split_strategy = split_strategy
        self.use_multiprocessing = use_multiprocessing
        self.decompress = decompress
        self.metrics = ScanMetrics()

    async def scan_all(
        self: "ParallelFileScanner",
        log_dir: str,
        parsers: list,
        parse_config: ParseConfig | None = None,
        scan_scope: dict | None = None,
        progress_cb: Callable[[float], Awaitable] | None = None,
        light: bool = False,
    ) -> dict:
        """扫描目录下所有被认领的日志文件，返回 ``{COLUMNS_KEY: DataFrame}``。

        ``light=True``：只投影轻列，并在结果里多带一个 ``SCAN_CTX_KEY``
        （:class:`ScanContext`，持有 read 产物）—— 宽列随后用
        ``scan_vector.materialize_wide(ctx, tids)`` 按需补算，不重读文件。
        """
        overall_start = time.perf_counter()

        gz_mapping = {}
        if self.decompress:
            gz_mapping = await LogPreprocessor().decompress_all(log_dir)

        map_start = time.perf_counter()
        file_parser_map = FileParserMapBuilder(log_dir, parsers, gz_mapping=gz_mapping).build()
        self.metrics.build_map_time_ms = (time.perf_counter() - map_start) * 1000
        self.metrics.total_files = len(file_parser_map)
        if not file_parser_map:
            logger.warning("No log files found")
            return {}

        index_of = {id(parser): index for index, parser in enumerate(parsers)}
        files = [
            [path, [index_of[id(p)] for p in file_parsers if id(p) in index_of]]
            for path, file_parsers in file_parser_map.items()
        ]
        files = [item for item in files if item[1]]
        if not files:
            logger.warning("No files matched any parser")
            return {}

        scan_start = time.perf_counter()
        if progress_cb is None:
            frame, skipped_files, scan_ctx = scan_frame(
                files, parsers, parse_config, scan_scope, light=light
            )
        else:
            # scan_frame 是同步的：直接调用会把事件循环占住，进度回调只能等扫描结束
            # 才执行（实测会一次性刷出几十条相同百分比）。放到线程里跑，用队列把
            # 进度实时喂回事件循环，让它在读取过程中就能上报。
            loop = asyncio.get_running_loop()
            queue: asyncio.Queue[float | None] = asyncio.Queue()

            def _on_progress(fraction: float) -> None:
                loop.call_soon_threadsafe(queue.put_nowait, fraction)

            async def _pump() -> None:
                while True:
                    fraction = await queue.get()
                    if fraction is None:
                        return
                    await progress_cb(fraction)

            pump = asyncio.create_task(_pump())
            try:
                def _with_light(*args):
                    return scan_frame(*args, light=light)

                frame, skipped_files, scan_ctx = await asyncio.to_thread(
                    _with_light, files, parsers, parse_config, scan_scope, _on_progress
                )
            finally:
                loop.call_soon_threadsafe(queue.put_nowait, None)
                await pump
        self.metrics.scan_time_ms = (time.perf_counter() - scan_start) * 1000
        self.metrics.total_entries = frame.height
        self.metrics.total_time_ms = (time.perf_counter() - overall_start) * 1000
        logger.info(
            f"[scan] {len(files)} file(s) → {frame.height:,} column rows "
            f"in {self.metrics.scan_time_ms / 1000:.2f}s"
        )
        if progress_cb is not None:
            await progress_cb(1.0)
        result = {COLUMNS_KEY: frame}
        if light:
            result[SCAN_CTX_KEY] = scan_ctx
        if skipped_files:
            # 坏文件不静默：交给 worker 告警 + 前端展示
            result[SKIPPED_FILES_KEY] = skipped_files
            logger.warning(
                "[skip] %d file(s) unreadable, skipped: %s",
                len(skipped_files),
                ", ".join(path for path, _ in skipped_files),
            )
        return result
