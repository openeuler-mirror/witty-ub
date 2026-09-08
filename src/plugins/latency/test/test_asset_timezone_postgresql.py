"""Opt-in migration regression; creates and removes its own isolated database.

WITTY_TIME_TEST_PG_DSN=postgresql://postgres@127.0.0.1:25439/postgres
"""
import os
import time
import uuid
from datetime import datetime, timezone

import pytest

from latency.database.engine import PGManager
from latency.database.init import (
    ASSET_TIMESTAMP_COLUMNS,
    migrate_asset_timestamps,
    migrate_timestamptz_to_timestamp,
)
from latency.database.managers.log_file import LogFilePGManager
from latency.database.managers.log_knowledge import LogKnowledgePGManager
from latency.database.models import Base, LogFile, LogKnowledge
from latency.schemas.log import LogFileModel, LogKnowledgeModel
from latency.schemas.request import ListLogKnowledgeRequest, ListLogFilesRequest


@pytest.mark.asyncio
async def test_existing_assets_follow_runtime_timezone_and_survive_restart(monkeypatch):
    dsn = os.environ.get("WITTY_TIME_TEST_PG_DSN")
    if not dsn:
        pytest.skip("set WITTY_TIME_TEST_PG_DSN to run isolated PostgreSQL migration test")
    import asyncpg
    from sqlalchemy import text

    database = "asset_time_test_" + uuid.uuid4().hex
    admin = await asyncpg.connect(dsn)
    original_tz = os.environ.get("TZ")
    monkeypatch.setattr(PGManager, "_engine", None)
    monkeypatch.setattr(PGManager, "_session_maker", None)
    try:
        await admin.execute(f'CREATE DATABASE "{database}"')
        # Preserve admin credentials/options while replacing the database name.
        from sqlalchemy.engine import make_url
        test_dsn = make_url(dsn).set(database=database).render_as_string(hide_password=False)
        PGManager.initialize(test_dsn, pool_size=1, max_overflow=0)
        monkeypatch.setenv("TZ", "Asia/Shanghai")
        monkeypatch.setenv("WITTY_LEGACY_ASSET_TIMEZONE", "Asia/Shanghai")
        async with PGManager.connection() as conn:
            await conn.run_sync(lambda sync: Base.metadata.create_all(
                sync, tables=[LogKnowledge.__table__, LogFile.__table__]
            ))
            await conn.execute(text("CREATE TABLE event_time_test (timestamp timestamp)"))
            await conn.execute(text("INSERT INTO event_time_test VALUES ('2026-01-01 08:30:00')"))
        await LogKnowledgePGManager.add_log_kb(LogKnowledgeModel(
            id="historical", name="historical", description="test",
            created_at="2026-01-01T00:30:00.123+00:00",
            updated_at="2026-01-01T00:30:00.123+00:00",
        ))
        await LogFilePGManager.add_log_file(LogFileModel(
            id="historical-file", kb_id="historical", created_at="2026-01-01T00:30:00.123Z",
        ))
        # Simulate the legacy schema and its original server-local wall times.
        async with PGManager.connection() as conn:
            for table, column in sorted(ASSET_TIMESTAMP_COLUMNS):
                await conn.execute(text(
                    f'ALTER TABLE "{table}" ALTER COLUMN "{column}" TYPE timestamp '
                    f'USING "{column}" AT TIME ZONE \'Asia/Shanghai\''
                ))
        await migrate_asset_timestamps()
        for zone, expected in [
            ("Asia/Shanghai", "2026-01-01 08:30:00.123+08:00"),
            ("UTC", "2026-01-01 00:30:00.123+00:00"),
            ("America/New_York", "2025-12-31 19:30:00.123-05:00"),
        ]:
            monkeypatch.setenv("TZ", zone)  # No tzset or process restart.
            asset = await LogKnowledgePGManager.get_log_kb_by_kb_id("historical")
            file = await LogFilePGManager.get_log_file_by_log_file_id("historical-file")
            assert asset.created_at == asset.updated_at == file.created_at == expected
            start = expected[:19]
            end = expected[:17] + "01"
            assets = await LogKnowledgePGManager.list_log_kbs(ListLogKnowledgeRequest(
                created_at_start=start, created_at_end=end,
            ))
            assert len(assets) == 1 and assets[0].created_at == expected
            count, files = await LogFilePGManager.list_log_files("historical", ListLogFilesRequest(
                created_at_start=start, created_at_end=end,
            ))
            assert count == 1 and files[0].created_at == expected
            # Both startup migrations must preserve the already-migrated instants.
            await migrate_asset_timestamps()
            await migrate_timestamptz_to_timestamp()
        async with PGManager.connection() as conn:
            assert await conn.scalar(text("SELECT timestamp FROM event_time_test")) == datetime(2026, 1, 1, 8, 30)
            assert await conn.scalar(text("SELECT created_at FROM log_knowledge WHERE id = 'historical'")) == datetime(2026, 1, 1, 0, 30, 0, 123000, tzinfo=timezone.utc)
        await LogKnowledgePGManager.update_log_kb("historical", {"description": "updated"})
        await LogFilePGManager.update_log_file("historical-file", {"name": "updated"})
        updated = await LogKnowledgePGManager.get_log_kb_by_kb_id("historical")
        assert abs((datetime.fromisoformat(updated.updated_at) - datetime.now(timezone.utc)).total_seconds()) < 5
        assert updated.created_at == "2025-12-31 19:30:00.123-05:00"
    finally:
        await PGManager.close()
        await admin.execute(f'DROP DATABASE IF EXISTS "{database}"')
        await admin.close()
        if original_tz is None:
            os.environ.pop("TZ", None)
        else:
            os.environ["TZ"] = original_tz
        time.tzset()
