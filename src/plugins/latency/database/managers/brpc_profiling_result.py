# Copyright (c) Huawei Technologies Co., Ltd. 2023-2025. All rights reserved.
"""BRPC profiling 结果数据库管理器。"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import delete, select, func

from latency.database.engine import PGManager
from latency.database.models import BrpcProfilingResult
from latency.parse.brpc_profiling_parser import BrpcProfilingRecord

logger = logging.getLogger(__name__)


class BrpcProfilingResultPGManager:
    """BRPC profiling 结果 PostgreSQL 管理器"""

    @staticmethod
    async def add_profiling_results(
        log_id: str,
        records: list[BrpcProfilingRecord],
    ) -> bool:
        """批量写入 BRPC profiling 结果。

        Args:
            log_id: 关联的日志文件 ID
            records: 解析后的记录列表

        Returns:
            是否写入成功
        """
        if not records:
            return True

        try:
            async with PGManager.session() as session:
                models = []
                for record in records:
                    model = BrpcProfilingResult(
                        id=str(uuid.uuid4()),
                        log_id=log_id,
                        source_file=record.source_file,
                        timestamp=record.timestamp,
                        interface_name=record.interface_name,
                        success_count=record.success_count,
                        failure_count=record.failure_count,
                        total_ns=record.total_ns,
                        avg_ns=record.avg_ns,
                        max_ns=record.max_ns,
                        min_ns=record.min_ns,
                        p50_ns=record.p50_ns,
                        p90_ns=record.p90_ns,
                        p95_ns=record.p95_ns,
                        p99_ns=record.p99_ns,
                        p999_ns=record.p999_ns,
                    )
                    models.append(model)

                session.add_all(models)
                await session.commit()

            logger.info(
                f"[PG] 写入 BRPC profiling 结果: {len(models)} 条, log_id={log_id}"
            )
            return True
        except Exception as e:
            logger.error(f"[PG] 写入 BRPC profiling 结果失败: {e}")
            return False

    @staticmethod
    async def delete_by_log_id(log_id: str) -> bool:
        """按 log_id 删除 profiling 结果。

        Args:
            log_id: 日志文件 ID

        Returns:
            是否删除成功
        """
        try:
            async with PGManager.session() as session:
                stmt = delete(BrpcProfilingResult).where(
                    BrpcProfilingResult.log_id == log_id
                )
                await session.execute(stmt)
                await session.commit()
            logger.info(f"[PG] 删除 BRPC profiling 结果: log_id={log_id}")
            return True
        except Exception as e:
            logger.error(f"[PG] 删除 BRPC profiling 结果失败: {e}")
            return False

    @staticmethod
    async def count_by_log_id(log_id: str) -> int:
        """按 log_id 统计 profiling 结果数量。

        Args:
            log_id: 日志文件 ID

        Returns:
            记录数量
        """
        try:
            async with PGManager.session() as session:
                stmt = select(func.count()).where(
                    BrpcProfilingResult.log_id == log_id,
                    BrpcProfilingResult.existed_status.is_(True),
                )
                result = await session.execute(stmt)
                count = result.scalar() or 0
            return count
        except Exception as e:
            logger.error(f"[PG] 统计 BRPC profiling 结果失败: {e}")
            return 0

    @staticmethod
    async def count_files_by_log_id(log_id: str) -> int:
        """按 log_id 统计不同 source_file 的数量。

        NULL source_file（旧数据）算作 1 个文件。
        """
        try:
            async with PGManager.session() as session:
                stmt = (
                    select(
                        func.count(
                            func.distinct(
                                func.coalesce(BrpcProfilingResult.source_file, "")
                            )
                        )
                    )
                    .where(
                        BrpcProfilingResult.log_id == log_id,
                        BrpcProfilingResult.existed_status.is_(True),
                    )
                )
                result = await session.execute(stmt)
                count = result.scalar() or 0
            return count
        except Exception as e:
            logger.error(f"[PG] 统计 BRPC profiling 文件数量失败: {e}")
            return 0

    @staticmethod
    async def get_file_names_by_log_id(log_id: str) -> list[str]:
        """获取指定日志文件的所有 source_file（去重排序）。

        NULL source_file（旧数据）返回空字符串占位。
        """
        try:
            async with PGManager.session() as session:
                stmt = (
                    select(
                        func.coalesce(BrpcProfilingResult.source_file, "").label(
                            "src_file"
                        )
                    )
                    .where(
                        BrpcProfilingResult.log_id == log_id,
                        BrpcProfilingResult.existed_status.is_(True),
                    )
                    .distinct()
                    .order_by("src_file")
                )
                result = await session.execute(stmt)
                names = [row[0] for row in result.all()]
            return names
        except Exception as e:
            logger.error(f"[PG] 获取 BRPC profiling 文件名列表失败: {e}")
            return []

    @staticmethod
    async def get_timestamps_by_log_id(log_id: str) -> list[datetime]:
        """获取指定日志文件的所有 timestamp（去重排序）。

        Args:
            log_id: 日志文件 ID

        Returns:
            timestamp 列表（升序）
        """
        try:
            async with PGManager.session() as session:
                stmt = (
                    select(BrpcProfilingResult.timestamp)
                    .where(
                        BrpcProfilingResult.log_id == log_id,
                        BrpcProfilingResult.existed_status.is_(True),
                    )
                    .distinct()
                    .order_by(BrpcProfilingResult.timestamp)
                )
                result = await session.execute(stmt)
                timestamps = [row[0] for row in result.all() if row[0] is not None]
            return timestamps
        except Exception as e:
            logger.error(f"[PG] 获取 BRPC profiling timestamp 列表失败: {e}")
            return []

    @staticmethod
    async def get_all_by_log_id(
        log_id: str, source_file: str | None = None
    ) -> list[BrpcProfilingResult]:
        """获取指定日志文件的所有 profiling 记录（按 timestamp 和 interface_name 排序）。

        Args:
            log_id: 日志文件 ID
            source_file: 可选，按源文件名过滤

        Returns:
            BrpcProfilingResult 列表
        """
        try:
            async with PGManager.session() as session:
                stmt = (
                    select(BrpcProfilingResult)
                    .where(
                        BrpcProfilingResult.log_id == log_id,
                        BrpcProfilingResult.existed_status.is_(True),
                    )
                )
                if source_file is not None:
                    stmt = stmt.where(
                        func.coalesce(BrpcProfilingResult.source_file, "")
                        == source_file
                    )
                stmt = stmt.order_by(
                    BrpcProfilingResult.timestamp, BrpcProfilingResult.interface_name
                )
                result = await session.execute(stmt)
                rows = result.scalars().all()
            return list(rows)
        except Exception as e:
            logger.error(f"[PG] 获取 BRPC profiling 全部结果失败: {e}")
            return []

    @staticmethod
    async def get_by_log_id_and_timestamp(
        log_id: str,
        timestamp: datetime,
    ) -> list[BrpcProfilingResult]:
        """获取指定日志文件和 timestamp 的所有接口记录。

        Args:
            log_id: 日志文件 ID
            timestamp: 时间戳

        Returns:
            BrpcProfilingResult 列表
        """
        try:
            async with PGManager.session() as session:
                stmt = (
                    select(BrpcProfilingResult)
                    .where(
                        BrpcProfilingResult.log_id == log_id,
                        BrpcProfilingResult.timestamp == timestamp,
                        BrpcProfilingResult.existed_status.is_(True),
                    )
                    .order_by(BrpcProfilingResult.interface_name)
                )
                result = await session.execute(stmt)
                rows = result.scalars().all()
            return list(rows)
        except Exception as e:
            logger.error(f"[PG] 获取 BRPC profiling 结果失败: {e}")
            return []