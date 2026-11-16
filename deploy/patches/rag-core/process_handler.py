# Copyright (c) Huawei Technologies Co., Ltd. 2023-2026. All rights reserved.
"""Runtime compatibility fixes for the deployed RAG Core.

The upstream implementation only removes a process from ``tasks`` when a
later deinit callback reaches the same Uvicorn worker. With multiple API
workers that callback can run elsewhere, leaving exited children in the
local dict forever. Reap exited children before enforcing the slot limit so
one missed callback cannot permanently stop document parsing.

The x86 OpenGauss HNSW and BM25 implementations also crash the database
process while searching on this host.  Exact cosine distance and GIN-backed
full-text queries are stable, so retrieval avoids those two native index paths
until the upstream implementations are fixed.
"""

import asyncio
import logging
import multiprocessing
import os
import signal

from rag_core.config.config import Config

logger = logging.getLogger(__name__)
multiprocessing = multiprocessing.get_context("spawn")


def _install_safe_opengauss_search() -> None:
    """Replace the crashing HNSW/BM25 lookups with stable search paths."""
    from sqlalchemy import func, literal_column, select, text

    from rag_core.ENUM.general import ExistedStatus
    from rag_core.database.db_vector.opengauss.engine import ChunkEntity, OpenGauss
    from rag_core.database.db_vector.opengauss.manager.chunk_manager import (
        ChunkManager,
    )

    async def search_chunks_by_vector(
        kb_id,
        vector,
        top_k,
        doc_ids=None,
        banned_doc_ids=None,
        banned_chunk_ids=None,
    ):
        if doc_ids is not None and not doc_ids:
            return []

        async with await OpenGauss.get_session() as session:
            # HNSW search currently terminates OpenGauss with SIGSEGV.  An
            # exact scan uses the same cosine-distance operator without the
            # unstable index code path and keeps retrieval correct.
            await session.execute(text("SET enable_seqscan = on;"))
            await session.execute(text("SET enable_indexscan = off;"))
            await session.execute(text("SET enable_bitmapscan = off;"))
            vector_param = str(vector)
            vector_literal = literal_column(f"'{vector_param}'::vector")
            distance = ChunkEntity.vector.op("<=>")(vector_literal)
            stmt = (
                select(ChunkEntity)
                .where(ChunkEntity.vector.isnot(None))
                .where(ChunkEntity.doc_enabled == True)
                .where(ChunkEntity.kb_id == kb_id)
                .where(ChunkEntity.enabled == True)
                .where(ChunkEntity.status != ExistedStatus.DELETED.value)
            )
            if doc_ids:
                stmt = stmt.where(ChunkEntity.doc_id.in_(doc_ids))
            if banned_doc_ids:
                stmt = stmt.where(ChunkEntity.doc_id.notin_(banned_doc_ids))
            if banned_chunk_ids:
                stmt = stmt.where(ChunkEntity.id.notin_(banned_chunk_ids))
            result = await session.execute(stmt.order_by(distance).limit(top_k))
            chunk_entities = result.scalars().all()

        return [
            await OpenGauss.convertor.chunk_entity_to_chunk(entity)
            for entity in chunk_entities
        ]

    async def search_chunks_by_keywords(
        kb_id,
        query,
        top_k,
        doc_ids=None,
        banned_doc_ids=None,
        banned_chunk_ids=None,
        is_tight=True,
    ):
        del is_tight  # The native BM25 loose-match operator is not stable.
        if doc_ids is not None and not doc_ids:
            return []

        async with await OpenGauss.get_session() as session:
            tsquery = func.plainto_tsquery("chinese", query)
            similarity_score = func.ts_rank_cd(
                ChunkEntity.text_ts_vector, tsquery
            ).label("similarity_score")
            stmt = (
                select(ChunkEntity, similarity_score)
                .where(ChunkEntity.text_ts_vector.op("@@")(tsquery))
                .where(similarity_score > 0)
                .where(ChunkEntity.doc_enabled == True)
                .where(ChunkEntity.kb_id == kb_id)
                .where(ChunkEntity.enabled == True)
                .where(ChunkEntity.status != ExistedStatus.DELETED.value)
            )
            if doc_ids:
                stmt = stmt.where(ChunkEntity.doc_id.in_(doc_ids))
            if banned_doc_ids:
                stmt = stmt.where(ChunkEntity.doc_id.notin_(banned_doc_ids))
            if banned_chunk_ids:
                stmt = stmt.where(ChunkEntity.id.notin_(banned_chunk_ids))
            result = await session.execute(
                stmt.order_by(similarity_score.desc()).limit(top_k)
            )
            chunk_entities = result.scalars().all()

        return [
            await OpenGauss.convertor.chunk_entity_to_chunk(entity)
            for entity in chunk_entities
        ]

    ChunkManager.search_chunks_by_vector = staticmethod(search_chunks_by_vector)
    ChunkManager.search_chunks_by_keywords = staticmethod(search_chunks_by_keywords)
    logger.info(
        "[OpenGauss] unstable HNSW/BM25 search disabled; using exact vector and FTS"
    )


_install_safe_opengauss_search()


class ProcessHandler:
    """Manage the document parsing child processes owned by this API worker."""

    tasks = {}
    lock = multiprocessing.Lock()
    max_processes = max(1, Config().get_config().task.cpu_limit)
    time_out = 10

    @staticmethod
    async def _init_databases_in_child() -> None:
        """Bind database managers without rerunning global schema migrations.

        Spawned workers do not inherit the manager attributes assigned during
        the API process startup.  Calling ``init_database_specifics`` here used
        to repair that, but it also made every parse worker concurrently drop
        and recreate the OpenGauss full-text triggers.  Apart from deadlocks,
        OpenGauss can terminate under that DDL load.  The parent has already
        created the schema, so children only need the class-level bindings.
        """
        from rag_core.config.config import Config
        from rag_core.database.base_class import BaseDataBase
        from rag_core.database.db_scalar.base.engine import BaseScalarDataBase
        from rag_core.database.db_vector.base.engine import BaseVectorDataBase

        scalar_impl = BaseDataBase.find_sub_class_under(
            BaseScalarDataBase,
            Config().get_config().scalar_db.database_type,
        )
        vector_impl = BaseDataBase.find_sub_class_under(
            BaseVectorDataBase,
            Config().get_config().vector_db.database_type,
        )
        if scalar_impl is None or vector_impl is None:
            raise RuntimeError("RAG database implementation is not registered")

        for attr in (
            "access_key_manager",
            "knowledge_base_manager",
            "task_manager",
            "task_report_manager",
            "trace_manager",
            "trace_detail_manager",
            "model_manager",
            "convertor",
        ):
            setattr(BaseScalarDataBase, attr, getattr(scalar_impl, attr))

        for attr in ("chunk_manager", "doc_manager", "json_manager", "convertor"):
            setattr(BaseVectorDataBase, attr, getattr(vector_impl, attr))

    @staticmethod
    async def _run_target_after_init(target, *args, **kwargs):
        await ProcessHandler._init_databases_in_child()
        return await target(*args, **kwargs)

    @staticmethod
    def subprocess_target(target, *args, **kwargs):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(
                ProcessHandler._run_target_after_init(target, *args, **kwargs)
            )
        except Exception as exc:
            logger.exception("[ProcessHandler] 子进程任务异常: %s", exc)
            raise
        finally:
            loop.close()

    @staticmethod
    def _reap_finished_tasks_locked() -> int:
        """Join exited children and release their in-memory slots."""
        reaped = 0
        for task_id, process in list(ProcessHandler.tasks.items()):
            try:
                alive = process.is_alive()
            except (AssertionError, ValueError):
                alive = False
            if alive:
                continue
            try:
                process.join(timeout=0)
            except (AssertionError, ValueError):
                pass
            ProcessHandler.tasks.pop(task_id, None)
            reaped += 1
        if reaped:
            logger.info("[ProcessHandler] 已回收 %s 个已退出任务槽位", reaped)
        return reaped

    @staticmethod
    def add_task(task_id: str, target, *args, **kwargs):
        acquired = ProcessHandler.lock.acquire(timeout=ProcessHandler.time_out)
        if not acquired:
            logger.warning("[ProcessHandler] 获取锁失败，可能是进程池已满或其他原因。请稍后再试。")
            return False

        try:
            ProcessHandler._reap_finished_tasks_locked()
            if len(ProcessHandler.tasks) >= ProcessHandler.max_processes:
                logger.warning(
                    "[ProcessHandler] 任务数量已达上限(%s)，请稍后再试。",
                    ProcessHandler.max_processes,
                )
                return False

            if task_id in ProcessHandler.tasks:
                logger.info("[ProcessHandler] 任务ID %s 已存在，无法添加。", task_id)
                return False

            try:
                process = multiprocessing.Process(
                    target=ProcessHandler.subprocess_target,
                    args=(target,) + args,
                    kwargs=kwargs,
                )
                ProcessHandler.tasks[task_id] = process
                process.start()
                return True
            except Exception as exc:
                ProcessHandler.tasks.pop(task_id, None)
                logger.error("[ProcessHandler] 添加任务 %s 失败: %s", task_id, exc)
                return False
        finally:
            ProcessHandler.lock.release()

    @staticmethod
    def remove_task(task_id: str):
        acquired = ProcessHandler.lock.acquire(timeout=ProcessHandler.time_out)
        if not acquired:
            logger.warning("[ProcessHandler] 获取锁失败，可能是进程池已满或其他原因。请稍后再试。")
            return
        try:
            ProcessHandler._reap_finished_tasks_locked()
            process = ProcessHandler.tasks.pop(task_id, None)
            if process is None:
                logger.debug("[ProcessHandler] 任务ID %s 已被回收或不属于当前进程。", task_id)
                return
            try:
                if process.is_alive():
                    os.kill(process.pid, signal.SIGKILL)
                    process.join(timeout=ProcessHandler.time_out)
                    logger.info("[ProcessHandler] 进程 %s (%s) 被杀死。", task_id, process.pid)
                else:
                    process.join(timeout=0)
            except (AssertionError, OSError, ValueError) as exc:
                logger.warning("[ProcessHandler] 清理进程 %s 失败: %s", task_id, exc)
            logger.info("[ProcessHandler] 任务ID %s 被删除。", task_id)
        finally:
            ProcessHandler.lock.release()
