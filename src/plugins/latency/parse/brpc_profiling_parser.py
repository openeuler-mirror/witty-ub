# Copyright (c) Huawei Technologies Co., Ltd. 2023-2025. All rights reserved.
"""BRPC profiling 日志解析器。

解析 ubsocket_profiling_xxx.txt 格式的 BRPC profiling 日志文件。
每个 timestamp 间隔内包含 21 个接口函数的统计信息：
  SUCCESS, FAILURE, TOTAL(ns), AVG(ns), MAX(ns), MIN(ns),
  P50(ns), P90(ns), P95(ns), P99(ns), P999(ns)

其中 P50 及之后的 4 列（P90/P95/P99/P999）为可选字段。
"""

from __future__ import annotations

import logging
import os
import re
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

logger = logging.getLogger(__name__)

# 匹配 timestamp 行: timeStamp: 2026-07-29 20:30:42
_TIMESTAMP_RE = re.compile(r"^timeStamp:\s*(.+)$")

# 匹配 header 行: [TRACE_NAME]  SUCCESS  FAILURE  TOTAL(ns) ...
_HEADER_RE = re.compile(r"^\[TRACE_NAME\]")

# 匹配分隔行: [--]
_SEPARATOR_RE = re.compile(r"^\[--\]")

# 匹配接口数据行: [CORE_ACCEPT]  1  0  994310  ...
_INTERFACE_RE = re.compile(r"^\[([^\]]+)\]\s+(.+)$")

# 全零行（接口名存在但所有数值为 0）也应该被保存
_ZERO_ROW_RE = re.compile(r"^\[([^\]]+)\]\s+0\s+0\s+0\s+0\s+0\s+0\s+0\s+0\s+0\s+0\s+0\s*$")


@dataclass
class BrpcProfilingRecord:
    """BRPC profiling 单条记录"""
    timestamp: datetime
    interface_name: str
    source_file: str = ""
    success_count: int = 0
    failure_count: int = 0
    total_ns: int = 0
    avg_ns: int = 0
    max_ns: int = 0
    min_ns: int = 0
    p50_ns: Optional[int] = None
    p90_ns: Optional[int] = None
    p95_ns: Optional[int] = None
    p99_ns: Optional[int] = None
    p999_ns: Optional[int] = None


class BrpcProfilingParser:
    """BRPC profiling 日志解析器"""

    # 必填列数（不含 P50 及之后的列）
    _MANDATORY_COLUMN_COUNT = 8  # interface_name, SUCCESS, FAILURE, TOTAL, AVG, MAX, MIN, P50

    def __init__(self):
        self._records: list[BrpcProfilingRecord] = []

    def parse_file(self, file_path: str) -> list[BrpcProfilingRecord]:
        """解析 BRPC profiling 日志文件。

        Args:
            file_path: 日志文件路径

        Returns:
            解析后的 BrpcProfilingRecord 列表
        """
        self._records = []
        current_timestamp: Optional[datetime] = None
        source_file = os.path.basename(file_path)

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                lines = f.readlines()
        except (IOError, OSError) as e:
            logger.error(f"读取 BRPC profiling 日志文件失败: {file_path}, 错误: {e}")
            return []

        for line in lines:
            line = line.rstrip("\n\r")

            # 空行跳过
            if not line.strip():
                continue

            # 匹配 timestamp 行
            ts_match = _TIMESTAMP_RE.match(line)
            if ts_match:
                current_timestamp = self._parse_timestamp(ts_match.group(1).strip())
                continue

            # 跳过 header 行
            if _HEADER_RE.match(line):
                continue

            # 跳过分隔行
            if _SEPARATOR_RE.match(line):
                continue

            # 匹配接口数据行
            iface_match = _INTERFACE_RE.match(line)
            if iface_match and current_timestamp is not None:
                interface_name = iface_match.group(1).strip()
                values_str = iface_match.group(2).strip()
                record = self._parse_interface_row(current_timestamp, interface_name, values_str)
                if record:
                    record.source_file = source_file
                    self._records.append(record)

        logger.info(f"BRPC profiling 解析完成: {len(self._records)} 条记录, "
                     f"时间点: {len(set(r.timestamp for r in self._records))} 个")
        return self._records

    @staticmethod
    def _parse_timestamp(ts_str: str) -> Optional[datetime]:
        """解析 timestamp 字符串为 datetime 对象。

        支持的格式: YYYY-MM-DD HH:MM:SS
        """
        formats = [
            "%Y-%m-%d %H:%M:%S",
            "%Y-%m-%dT%H:%M:%S",
        ]
        for fmt in formats:
            try:
                return datetime.strptime(ts_str, fmt)
            except ValueError:
                continue
        logger.warning(f"无法解析 timestamp: {ts_str}")
        return None

    @staticmethod
    def _parse_interface_row(
        timestamp: datetime, interface_name: str, values_str: str
    ) -> Optional[BrpcProfilingRecord]:
        """解析单行接口数据。

        Args:
            timestamp: 当前 timestamp
            interface_name: 接口名称
            values_str: 数值字符串

        Returns:
            BrpcProfilingRecord 或 None
        """
        parts = values_str.split()
        try:
            values = [int(p) for p in parts]
        except ValueError:
            logger.warning(f"无法解析接口行数值: [{interface_name}] {values_str}")
            return None

        if len(values) < 7:  # 至少需要 SUCCESS, FAILURE, TOTAL, AVG, MAX, MIN, P50
            logger.warning(f"接口行数值不足（少于7列）: [{interface_name}] {values_str}")
            return None

        return BrpcProfilingRecord(
            timestamp=timestamp,
            interface_name=interface_name,
            success_count=values[0] if len(values) > 0 else 0,
            failure_count=values[1] if len(values) > 1 else 0,
            total_ns=values[2] if len(values) > 2 else 0,
            avg_ns=values[3] if len(values) > 3 else 0,
            max_ns=values[4] if len(values) > 4 else 0,
            min_ns=values[5] if len(values) > 5 else 0,
            p50_ns=values[6] if len(values) > 6 else None,
            p90_ns=values[7] if len(values) > 7 else None,
            p95_ns=values[8] if len(values) > 8 else None,
            p99_ns=values[9] if len(values) > 9 else None,
            p999_ns=values[10] if len(values) > 10 else None,
        )