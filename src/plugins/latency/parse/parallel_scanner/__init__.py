"""并行日志扫描模块

整合文件去重读取（Phase 1）和多进程并行（Phase 2），提供高性能的日志扫描能力。
"""

from .scanner import ParallelFileScanner
from .preprocessor import LogPreprocessor
from latency.ENUM.task import TaskSplitStrategy

__all__ = [
    "ParallelFileScanner",
    "LogPreprocessor",
    "TaskSplitStrategy",
]
