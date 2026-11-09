"""批量硬删除全部诊断案例库（diag_case_library）记录。

级联清理：现象索引卡片（phenomenon_index，按 case_id 关联）+ RAG 清理入队 +
信号表（diag_case_library_signal）+ 案例表（diag_case_library）。不可恢复。
"""
import asyncio

from sqlalchemy import delete, select

from latency.database.engine import PGManager
from latency.database.managers.phenomenon_index import PhenomenonIndexPGManager
from latency.database.models import DiagCaseLibrary, DiagCaseLibrarySignal, PhenomenonIndex


def _pg_dsn() -> str:
    import os

    host = os.getenv("PG_HOST", "127.0.0.1")
    port = os.getenv("PG_PORT", "15432")
    user = os.getenv("PG_USER", "witty-ub")
    password = os.getenv("PG_PASSWORD", "witty-ub")
    database = os.getenv("PG_DATABASE", "witty-ub")
    return f"postgresql://{user}:{password}@{host}:{port}/{database}"


async def main() -> None:
    PGManager.initialize(_pg_dsn())
    async with PGManager.session() as session:
        case_ids = list(
            (
                await session.execute(select(DiagCaseLibrary.id))
            ).scalars().all()
        )
    if not case_ids:
        print("diag_case_library 为空，无需删除")
        return
    print(f"待删除诊断案例: {len(case_ids)}")

    async with PGManager.session() as session:
        cards = list(
            (
                await session.execute(
                    select(PhenomenonIndex).where(
                        PhenomenonIndex.case_id.in_(case_ids)
                    )
                )
            ).scalars().all()
        )
        await session.execute(
            delete(PhenomenonIndex).where(PhenomenonIndex.case_id.in_(case_ids))
        )
        await session.execute(
            delete(DiagCaseLibrarySignal).where(
                DiagCaseLibrarySignal.case_id.in_(case_ids)
            )
        )
        await session.execute(
            delete(DiagCaseLibrary).where(DiagCaseLibrary.id.in_(case_ids))
        )

    # 事务外：被删卡片若已发布/待发布 RAG 文档，入队异步清理
    for card in cards:
        for kb_id, doc_id in (
            (card.rag_kb_id, card.rag_doc_id),
            (card.pending_rag_kb_id, card.pending_rag_doc_id),
        ):
            if kb_id and doc_id:
                await PhenomenonIndexPGManager.enqueue_cleanup(
                    kb_id, doc_id, "deleted", card.doc_id
                )

    print(f"删除完成：案例 {len(case_ids)}，现象索引卡片 {len(cards)}")


if __name__ == "__main__":
    asyncio.run(main())
