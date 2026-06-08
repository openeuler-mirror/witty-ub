"""任务分组策略

负责将文件列表按策略分配到多个进程组，确保各进程负载均衡。
"""

import logging
import os
import random
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from latency.ENUM.task import TaskSplitStrategy

if TYPE_CHECKING:
    from latency.parse.base_parser import LogParser

logger = logging.getLogger(__name__)


@dataclass
class FileGroup:
    """
    单个进程的文件组

    Attributes:
        group_id: 组 ID（进程编号）
        files: 文件列表 [(path, parser_indices), ...]
               parser_indices 是解析器在 parsers 列表中的索引
        total_size_bytes: 总文件大小（字节）
        total_parser_calls: 预估的解析调用次数
    """
    group_id: int
    files: list[tuple[str, list[int]]] = field(default_factory=list)
    total_size_bytes: int = 0
    total_parser_calls: int = 0

    def add_file(self, path: str, parser_indices: list[int], size: int) -> None:
        """添加文件到当前组"""
        self.files.append((path, parser_indices))
        self.total_size_bytes += size
        self.total_parser_calls += len(parser_indices)

    @property
    def file_count(self) -> int:
        """文件数量"""
        return len(self.files)


class ScanTaskSplitter:
    """
    任务分组器

    将文件映射表拆分成多个进程组，确保各进程负载均衡。

    支持三种分组策略：
    1. BY_FILE_SIZE: 按文件大小加权（推荐，适用于文件大小差异大的场景）
    2. BY_FILE_COUNT: 按文件数量平均（适用于文件大小相近的场景）
    3. BY_PARSER_COUNT: 按解析器调用次数加权（适用于解析器性能差异大的场景）
    """

    def __init__(
        self,
        file_parser_map: dict[str, list["LogParser"]],
        parsers: list["LogParser"],
        max_processes: int,
        strategy: TaskSplitStrategy = TaskSplitStrategy.BY_FILE_SIZE,
    ):
        self.file_parser_map = file_parser_map
        self.parsers = parsers
        self.max_processes = max_processes
        self.strategy = strategy

        # 构建解析器实例到索引的映射
        self._parser_to_index = {id(p): i for i, p in enumerate(parsers)}

    def split(self) -> list[FileGroup]:
        """
        执行分组

        返回:
            FileGroup 列表（已过滤空组）
        """
        if self.strategy == TaskSplitStrategy.BY_FILE_SIZE:
            return self._split_by_file_size()
        elif self.strategy == TaskSplitStrategy.BY_FILE_COUNT:
            return self._split_by_file_count()
        elif self.strategy == TaskSplitStrategy.BY_PARSER_COUNT:
            return self._split_by_parser_count()
        else:
            raise ValueError(f"Unknown strategy: {self.strategy}")

    def _split_by_file_size(self) -> list[FileGroup]:
        """
        按文件大小加权分配（推荐）

        策略：大文件优先，贪心分配到当前负载最小的组
        适用于：文件大小差异大的场景
        """
        # 1. 收集文件大小
        file_info: list[tuple[str, list[int], int]] = []
        for path, parsers in self.file_parser_map.items():
            try:
                size = os.path.getsize(path)
            except OSError:
                size = 0
            parser_indices = [self._parser_to_index[id(p)] for p in parsers]
            file_info.append((path, parser_indices, size))

        # 2. 按大小降序排序（大文件优先）
        file_info.sort(key=lambda x: x[2], reverse=True)

        # 3. 创建分组
        groups = [FileGroup(group_id=i) for i in range(self.max_processes)]
        group_loads = [0] * self.max_processes  # 按字节负载

        # 4. 贪心分配
        for path, parser_indices, size in file_info:
            min_idx = group_loads.index(min(group_loads))
            groups[min_idx].add_file(path, parser_indices, size)
            group_loads[min_idx] += size

        # 5. 移除空组并重新编号
        active_groups = [g for g in groups if g.files]
        for i, group in enumerate(active_groups):
            group.group_id = i

        self._log_split_result(active_groups)
        return active_groups

    def _split_by_file_count(self) -> list[FileGroup]:
        """
        按文件数量平均分配

        适用于：文件大小相近的场景
        """
        items = list(self.file_parser_map.items())
        random.shuffle(items)  # 打乱避免顺序偏差

        groups = [FileGroup(group_id=i) for i in range(self.max_processes)]

        for i, (path, parsers) in enumerate(items):
            group_idx = i % self.max_processes
            try:
                size = os.path.getsize(path)
            except OSError:
                size = 0
            parser_indices = [self._parser_to_index[id(p)] for p in parsers]
            groups[group_idx].add_file(path, parser_indices, size)

        active_groups = [g for g in groups if g.files]
        self._log_split_result(active_groups)
        return active_groups

    def _split_by_parser_count(self) -> list[FileGroup]:
        """
        按解析器调用次数加权分配

        适用于：解析器性能差异大的场景
        """
        file_info = []
        for path, parsers in self.file_parser_map.items():
            try:
                size = os.path.getsize(path)
            except OSError:
                size = 0
            parser_indices = [self._parser_to_index[id(p)] for p in parsers]
            parser_cost = len(parsers)  # 简单估算
            file_info.append((path, parser_indices, size, parser_cost))

        # 按解析器数量降序
        file_info.sort(key=lambda x: x[3], reverse=True)

        groups = [FileGroup(group_id=i) for i in range(self.max_processes)]
        group_loads = [0] * self.max_processes

        for path, parser_indices, size, cost in file_info:
            min_idx = group_loads.index(min(group_loads))
            groups[min_idx].add_file(path, parser_indices, size)
            group_loads[min_idx] += cost

        active_groups = [g for g in groups if g.files]
        for i, group in enumerate(active_groups):
            group.group_id = i

        self._log_split_result(active_groups)
        return active_groups

    def _log_split_result(self, groups: list[FileGroup]) -> None:
        """输出分组结果日志"""
        logger.info(
            f"Task split complete: {len(self.file_parser_map)} files → "
            f"{len(groups)} process groups"
        )
        for group in groups:
            size_mb = group.total_size_bytes / 1024 / 1024
            logger.info(
                f"  Group {group.group_id}: "
                f"{group.file_count} files, "
                f"{size_mb:.1f} MB, "
                f"~{group.total_parser_calls} parser calls"
            )
