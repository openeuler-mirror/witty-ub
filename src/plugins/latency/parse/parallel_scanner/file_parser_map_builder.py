"""文件-解析器映射构建器

负责遍历所有解析器，构建 文件路径 → [解析器列表] 的映射关系。
"""

import logging
import os
from collections import Counter, defaultdict
from typing import TYPE_CHECKING

from latency.common.ds_log_io import glob_paths

if TYPE_CHECKING:
    from latency.parse.base_parser import LogParser

logger = logging.getLogger(__name__)


class FileParserMapBuilder:
    """
    构建文件到解析器的映射关系

    输入: log_dir + 解析器列表
    输出: {
        "SDK_1/ds_client_access.log": [SdkAccessLogParser],
        "worker_1/datasystem_worker.INFO": [UrmaLogParser, RemotePullLogParser, ...]
    }

    核心优化：识别被多个解析器共享的文件，避免后续重复读取。
    """

    def __init__(self, log_dir: str, parsers: list["LogParser"]):
        self.log_dir = log_dir
        self.parsers = parsers

    def build(self) -> dict[str, list["LogParser"]]:
        """
        构建文件-解析器映射表

        遍历所有解析器的 patterns，将相同文件路径的解析器归类到一起。

        返回:
            {file_path: [parser1, parser2, ...]}
        """
        file_parser_map: dict[str, list["LogParser"]] = defaultdict(list)

        for parser in self.parsers:
            try:
                patterns = [os.path.join(self.log_dir, p) for p in parser.patterns]
                paths = glob_paths(patterns)

                for path in paths:
                    file_parser_map[path].append(parser)

            except Exception as e:
                logger.warning(f"[{parser.label}] failed to glob patterns: {e}")

        self._log_statistics(file_parser_map)
        return dict(file_parser_map)

    def _log_statistics(self, file_parser_map: dict[str, list["LogParser"]]) -> None:
        """输出映射统计信息，帮助理解文件分布情况"""
        total_files = len(file_parser_map)

        if total_files == 0:
            logger.warning("No log files found in the specified directory")
            return

        shared_files = sum(1 for p in file_parser_map.values() if len(p) > 1)
        max_shared = max(len(p) for p in file_parser_map.values())

        logger.info(
            f"File parser map built: "
            f"{total_files} total files, "
            f"{shared_files} shared by multiple parsers, "
            f"max {max_shared} parsers per file"
        )

        # 按解析器数量分组统计
        share_distribution = Counter(len(p) for p in file_parser_map.values())
        for parser_count, file_count in sorted(share_distribution.items()):
            logger.info(f"  {parser_count} parser(s): {file_count} file(s)")
