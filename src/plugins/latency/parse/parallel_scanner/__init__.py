"""并行日志扫描模块

整合文件去重读取（Phase 1）和多进程并行（Phase 2），提供高性能的日志扫描能力。
"""

from .scanner import ParallelFileScanner
from .file_parser_map_builder import FileParserMapBuilder
from .task_splitter import FileGroup, ScanTaskSplitter
from latency.ENUM.task import TaskSplitStrategy

__all__ = [
    "ParallelFileScanner",
    "FileParserMapBuilder",
    "ScanTaskSplitter",
    "FileGroup",
    "TaskSplitStrategy",
]
