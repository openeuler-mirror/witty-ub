"""日志预处理模块

负责将 .gz 压缩日志文件预解压到临时目录，避免解析时重复解压导致的 CPU 和内存瓶颈。
"""

import asyncio
import glob
import gzip
import logging
import os
import shutil
import tempfile
from concurrent.futures import ProcessPoolExecutor
from typing import Optional

logger = logging.getLogger(__name__)

_DECOMPRESS_BUFFER_SIZE = 8 * 1024 * 1024  # 8MB


def decompress_file_worker(gz_path: str, temp_dir: str) -> tuple[str, str]:
    """
    解压单个 .gz 文件

    参数:
        gz_path: 原始 .gz 文件路径
        temp_dir: 临时目录

    返回:
        (原.gz路径, 解压后的.log路径)
    """
    # 保持原始目录结构
    # 例如: /data/logs/SDK_1/ds_client_access.log.gz
    #   → temp_dir/data_logs_SDK_1/ds_client_access.log
    # 用哈希避免目录名冲突
    base_dir = os.path.basename(os.path.dirname(gz_path))
    filename = os.path.basename(gz_path)

    # 创建子目录
    sub_dir = os.path.join(temp_dir, base_dir)
    os.makedirs(sub_dir, exist_ok=True)

    # 去掉 .gz 后缀
    log_filename = filename[:-3] if filename.endswith(".gz") else filename
    dest_path = os.path.join(sub_dir, log_filename)

    # 流式解压，避免内存峰值
    try:
        with gzip.open(gz_path, "rb") as f_in:
            with open(dest_path, "wb") as f_out:
                while True:
                    chunk = f_in.read(_DECOMPRESS_BUFFER_SIZE)
                    if not chunk:
                        break
                    f_out.write(chunk)
    except Exception as e:
        logger.error(f"Failed to decompress {gz_path}: {e}")
        if os.path.exists(dest_path):
            os.remove(dest_path)
        return gz_path, ""

    orig_size = os.path.getsize(gz_path)
    decompressed_size = os.path.getsize(dest_path)
    logger.info(
        f"Decompressed: {filename} | "
        f"{orig_size / 1024 / 1024:.1f}MB → {decompressed_size / 1024 / 1024:.1f}MB"
    )

    return gz_path, dest_path


class LogPreprocessor:
    """
    日志预处理器

    将 .gz 压缩日志文件预解压到临时目录，供后续多进程解析使用。

    使用示例:
        preprocessor = LogPreprocessor()
        mapping = await preprocessor.decompress_all(log_dir)
        # 使用 mapping 替换 .gz 路径
        try:
            ... 解析流程 ...
        finally:
            preprocessor.cleanup()
    """

    def __init__(
        self,
        temp_dir: Optional[str] = None,
        max_workers: int = 0,
    ):
        """
        参数:
            temp_dir: 自定义临时目录（None 则自动生成）
            max_workers: 解压并发数（默认 CPU 核数）
        """
        self.max_workers = max_workers or (os.cpu_count() or 4)
        self.need_cleanup = temp_dir is None

        if temp_dir:
            self.temp_dir = temp_dir
        else:
            self.temp_dir = tempfile.mkdtemp(prefix="latency_unzip_")

        # .gz 路径 → 解压后的 .log 路径
        self.path_mapping: dict[str, str] = {}

    async def decompress_all(self, log_dir: str) -> dict[str, str]:
        """
        扫描并解压目录下所有 .gz 文件

        参数:
            log_dir: 日志目录

        返回:
            {原.gz路径: 解压后.log路径}
        """
        # 1. 扫描 .gz 文件
        gz_files = self._scan_gz_files(log_dir)
        if not gz_files:
            logger.info("No .gz files found, skipping decompression")
            return {}

        total_size = sum(size for _, size in gz_files)
        logger.info(
            f"Found {len(gz_files)} .gz files, "
            f"total {total_size / 1024 / 1024:.1f}MB"
        )

        # 2. 按大小降序排列（大文件优先）
        gz_files.sort(key=lambda x: x[1], reverse=True)

        # 3. 多进程解压
        await self._decompress_parallel(gz_files)

        logger.info(
            f"Decompression complete: {len(self.path_mapping)} files → {self.temp_dir}"
        )

        return self.path_mapping

    def _scan_gz_files(self, log_dir: str) -> list[tuple[str, int]]:
        """扫描目录下所有 .gz 文件及其大小"""
        gz_files: list[tuple[str, int]] = []

        # 递归扫描
        pattern = os.path.join(log_dir, "**", "*.gz")
        for path in glob.glob(pattern, recursive=True):
            try:
                size = os.path.getsize(path)
                gz_files.append((path, size))
            except OSError:
                pass

        return gz_files

    async def _decompress_parallel(
        self, gz_files: list[tuple[str, int]]
    ) -> None:
        """多进程并行解压"""

        loop = asyncio.get_event_loop()
        with ProcessPoolExecutor(max_workers=self.max_workers) as executor:
            futures = [
                loop.run_in_executor(
                    executor,
                    decompress_file_worker,
                    gz_path,
                    self.temp_dir,
                )
                for gz_path, _ in gz_files
            ]

            results = await asyncio.gather(*futures)

        # 收集结果
        for gz_path, log_path in results:
            if log_path:
                self.path_mapping[gz_path] = log_path

    def get_effective_path(self, original_path: str) -> str:
        """
        获取有效路径

        如果原路径是 .gz 且已解压，返回解压后的路径；否则返回原路径。
        """
        return self.path_mapping.get(original_path, original_path)

    def cleanup(self) -> None:
        """清理临时目录"""
        if self.need_cleanup and os.path.exists(self.temp_dir):
            try:
                shutil.rmtree(self.temp_dir, ignore_errors=True)
                logger.info(f"Cleaned up temp dir: {self.temp_dir}")
            except Exception as e:
                logger.warning(f"Failed to cleanup temp dir: {e}")
