"""Opt-in upgrade drill; creates and removes its own isolated database.

WITTY_REPORT_CASE_TEST_PG_DSN=postgresql://postgres:postgres@127.0.0.1:5432/postgres
"""
import os
import uuid

import pytest
from sqlalchemy import text
from sqlalchemy.engine import make_url
from sqlalchemy.exc import IntegrityError

from latency.database.engine import PGManager
from latency.database.init import _ensure_missing_columns, init_phenomenon_schema
from latency.database.models import Base

LEGACY_COLUMNS = (
    "source_sidecar_hash",
    "first_level_label",
    "second_level_label",
    "label_taxonomy_version",
    "source_label_hash",
    "verification_history_json",
)
VERIFICATION = '{"method":"replay","closed_loop":true,"observed_result":"恢复"}'


@pytest.mark.asyncio
async def test_legacy_cases_keep_state_across_upgrade(monkeypatch):
    dsn = os.environ.get("WITTY_REPORT_CASE_TEST_PG_DSN")
    if not dsn:
        pytest.skip("set WITTY_REPORT_CASE_TEST_PG_DSN to run isolated upgrade drill")
    import asyncpg

    database = "report_case_upgrade_" + uuid.uuid4().hex
    admin = await asyncpg.connect(dsn)
    monkeypatch.setattr(PGManager, "_engine", None)
    monkeypatch.setattr(PGManager, "_session_maker", None)
    try:
        await admin.execute(f'CREATE DATABASE "{database}"')
        test_dsn = make_url(dsn).set(database=database).render_as_string(
            hide_password=False
        )
        PGManager.initialize(test_dsn, pool_size=1, max_overflow=0)
        tables = list(Base.metadata.tables.values())
        async with PGManager.connection() as conn:
            await conn.run_sync(
                lambda sync: Base.metadata.create_all(sync, tables=tables)
            )
        async with PGManager.connection() as conn:
            # 还原升级前的表结构：没有分类快照与验证历史，唯一键只按故障版本。
            for column in LEGACY_COLUMNS:
                await conn.execute(text(
                    f"ALTER TABLE diag_case_library DROP COLUMN IF EXISTS {column}"
                ))
            await conn.execute(text(
                "DROP INDEX IF EXISTS ux_dcl_bound_snapshot"
            ))
            await conn.execute(text("DROP INDEX IF EXISTS ix_dcl_labels"))
            await conn.execute(text(
                "CREATE UNIQUE INDEX ux_dcl_bound_version "
                "ON diag_case_library (report_id, source_fault_id, source_fault_hash) "
                "WHERE report_id IS NOT NULL AND source_fault_id IS NOT NULL "
                "AND status <> 'archived'"
            ))
            await conn.execute(
                text(
                    "INSERT INTO diag_case_library ("
                    "id, status, revision, created_by, confirmed_by, confirmed_at, "
                    "source, title, report_id, source_fault_id, source_fault_hash, "
                    "log_type, fault_type, symptom_summary, root_cause_summary, "
                    "confidence, hit_count, verification_json, existed_status, "
                    "created_at, updated_at"
                    ") VALUES ("
                    "'legacy-bound', 'confirmed', 3, 'alice', 'bob', "
                    "'2026-10-01 10:00:00', 'internal', '历史案例', "
                    "'report_legacy', 'F01', :hash, 'KVCache', 'unknown', "
                    "'GET 阻塞', '订阅等待', 0.0, 0, CAST(:verification AS jsonb), "
                    "TRUE, '2026-09-01 09:00:00', '2026-10-01 10:00:00'"
                    ")"
                ),
                {"hash": "a" * 64, "verification": VERIFICATION},
            )
            await conn.execute(text(
                "INSERT INTO diag_case_library ("
                "id, status, revision, source, title, log_type, fault_type, "
                "symptom_summary, root_cause_summary, confidence, hit_count, "
                "existed_status, created_at, updated_at"
                ") VALUES ('legacy-independent', 'draft', 1, 'internal', "
                "'独立案例', 'KVCache', 'unknown', '现象', '根因', 0.0, 0, TRUE, "
                "'2026-09-02 09:00:00', '2026-09-02 09:00:00')"
            ))

        await _ensure_missing_columns()
        await init_phenomenon_schema()

        async with PGManager.connection() as conn:
            bound = (
                await conn.execute(text(
                    "SELECT status, revision, created_by, confirmed_by, "
                    "verification_json, verification_history_json, "
                    "first_level_label, second_level_label, "
                    "label_taxonomy_version, source_sidecar_hash "
                    "FROM diag_case_library WHERE id = 'legacy-bound'"
                ))
            ).mappings().one()
            assert bound["status"] == "confirmed"
            assert bound["revision"] == 3
            assert bound["created_by"] == "alice"
            assert bound["confirmed_by"] == "bob"
            assert bound["verification_json"]["closed_loop"] is True
            assert bound["verification_history_json"] == []
            assert bound["first_level_label"] is None
            assert bound["second_level_label"] is None
            assert bound["label_taxonomy_version"] is None
            assert bound["source_sidecar_hash"] is None

            independent = (
                await conn.execute(text(
                    "SELECT status, verification_history_json, "
                    "first_level_label, label_taxonomy_version "
                    "FROM diag_case_library WHERE id = 'legacy-independent'"
                ))
            ).mappings().one()
            assert independent["status"] == "draft"
            assert independent["verification_history_json"] == []
            assert independent["first_level_label"] is None
            assert independent["label_taxonomy_version"] is None

            assert await conn.scalar(text(
                "SELECT count(*) FROM pg_indexes "
                "WHERE tablename = 'diag_case_library' "
                "AND indexname = 'ux_dcl_bound_snapshot'"
            )) == 1
            assert await conn.scalar(text(
                "SELECT count(*) FROM pg_indexes "
                "WHERE tablename = 'diag_case_library' "
                "AND indexname = 'ux_dcl_bound_version'"
            )) == 0

        # 新唯一键按分类快照区分，同一故障版本可并存不同分类。
        async with PGManager.connection() as conn:
            for case_id, first, second in (
                ("new-worker", "Worker故障", "Worker故障-进程退出"),
                ("new-os", "OS故障", "OS故障-磁盘"),
            ):
                await conn.execute(
                    text(
                        "INSERT INTO diag_case_library ("
                        "id, status, revision, source, title, report_id, "
                        "source_fault_id, source_fault_hash, log_type, fault_type, "
                        "symptom_summary, root_cause_summary, first_level_label, "
                        "second_level_label, confidence, hit_count, existed_status, "
                        "created_at, updated_at"
                        ") VALUES (:id, 'draft', 0, 'internal', '新案例', "
                        "'report_legacy', 'F01', :hash, 'KVCache', 'unknown', "
                        "'现象', '根因', :first, :second, 0.0, 0, "
                        "TRUE, '2026-10-02 09:00:00', '2026-10-02 09:00:00')"
                    ),
                    {"id": case_id, "hash": "a" * 64, "first": first, "second": second},
                )
        with pytest.raises(IntegrityError):
            async with PGManager.connection() as conn:
                await conn.execute(
                    text(
                        "INSERT INTO diag_case_library ("
                        "id, status, revision, source, title, report_id, "
                        "source_fault_id, source_fault_hash, log_type, fault_type, "
                        "symptom_summary, root_cause_summary, first_level_label, "
                        "second_level_label, confidence, hit_count, existed_status, "
                        "created_at, updated_at"
                        ") VALUES ('new-worker-dup', 'draft', 0, 'internal', "
                        "'重复分类', 'report_legacy', 'F01', :hash, 'KVCache', "
                        "'unknown', '现象', '根因', "
                        "'Worker故障', 'Worker故障-进程退出', 0.0, 0, TRUE, "
                        "'2026-10-02 09:00:00', '2026-10-02 09:00:00')"
                    ),
                    {"hash": "a" * 64},
                )

        # 迁移可重复执行，存量行不被改写。
        await _ensure_missing_columns()
        await init_phenomenon_schema()
        async with PGManager.connection() as conn:
            assert await conn.scalar(text(
                "SELECT status FROM diag_case_library WHERE id = 'legacy-bound'"
            )) == "confirmed"
            assert await conn.scalar(text(
                "SELECT verification_json->>'closed_loop' "
                "FROM diag_case_library WHERE id = 'legacy-bound'"
            )) == "true"
    finally:
        await PGManager.close()
        await admin.execute(f'DROP DATABASE IF EXISTS "{database}"')
        await admin.close()
