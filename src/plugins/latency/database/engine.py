# Copyright (c) Huawei Technologies Co., Ltd. 2023-2025. All rights reserved.
"""PostgreSQL async engine and session management based on SQLAlchemy 2.0."""
from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncIterator

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)


class PGManager:
    """SQLAlchemy async engine / session manager."""

    _engine: AsyncEngine | None = None
    _session_maker: async_sessionmaker[AsyncSession] | None = None

    @classmethod
    def initialize(
        cls,
        dsn: str,
        *,
        pool_size: int = 10,
        max_overflow: int = 20,
        pool_timeout: float = 30.0,
        pool_recycle: float = 3600.0,
        echo: bool = False,
    ) -> None:
        if cls._engine is not None:
            return

        # Ensure the asyncpg driver is used for async SQLAlchemy.
        if dsn.startswith("postgresql://"):
            dsn = dsn.replace("postgresql://", "postgresql+asyncpg://", 1)

        cls._engine = create_async_engine(
            dsn,
            pool_size=pool_size,
            max_overflow=max_overflow,
            pool_timeout=pool_timeout,
            pool_recycle=pool_recycle,
            echo=echo,
            connect_args={
                "server_settings": {
                    "application_name": "witty-ub-latency",
                    "jit": "off",
                },
            },
        )
        cls._session_maker = async_sessionmaker(
            bind=cls._engine,
            class_=AsyncSession,
            autoflush=False,
            expire_on_commit=False,
        )

    @classmethod
    async def init_timezone(cls) -> None:
        """No-op kept for backward compatibility.

        All timestamps are now stored as naive TIMESTAMP (no timezone),
        so no timezone initialization is needed.
        """
        pass

    @classmethod
    async def close(cls) -> None:
        if cls._engine is not None:
            await cls._engine.dispose()
            cls._engine = None

    @classmethod
    @asynccontextmanager
    async def session(cls) -> AsyncIterator[AsyncSession]:
        """获取一个自动提交/回滚的 AsyncSession。"""
        if cls._session_maker is None:
            raise RuntimeError("PGManager not initialized")
        async with cls._session_maker() as s:
            try:
                yield s
                await s.commit()
            except Exception:
                await s.rollback()
                raise

    @classmethod
    @asynccontextmanager
    async def connection(cls) -> AsyncIterator:
        """获取底层 AsyncConnection，用于 Core 批量操作或 COPY。"""
        if cls._engine is None:
            raise RuntimeError("PGManager not initialized")
        async with cls._engine.begin() as conn:
            yield conn

    @classmethod
    def engine(cls) -> AsyncEngine:
        if cls._engine is None:
            raise RuntimeError("PGManager not initialized")
        return cls._engine
