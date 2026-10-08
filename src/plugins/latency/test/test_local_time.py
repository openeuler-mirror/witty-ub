"""Timezone changes must take effect without restarting the service process."""
import os
import time
from datetime import datetime, timezone
from unittest.mock import AsyncMock

import pytest

from latency.common.local_time import parse_asset_timestamp, utc_now
from latency.database.managers.log_knowledge import LogKnowledgePGManager
from latency.database.utils import format_timestamp
from latency.schemas.log import LogKnowledgeModel
from latency.schemas.request import ListLogKnowledgeRequest, ParseConfig


@pytest.fixture
def change_timezone(monkeypatch):
    if not hasattr(time, "tzset"):
        pytest.skip("requires POSIX timezone support")
    original = os.environ.get("TZ")

    def change(value):
        # Deliberately leave libc's timezone cache stale, as in a running server.
        monkeypatch.setenv("TZ", value)

    yield change
    if original is None:
        os.environ.pop("TZ", None)
    else:
        os.environ["TZ"] = original
    time.tzset()


def test_new_asset_timestamps_follow_timezone_changes(change_timezone):
    change_timezone("UTC0")
    before = LogKnowledgeModel(name="before", description="test")
    change_timezone("CST-8")
    after = LogKnowledgeModel(name="after", description="test")
    delta = datetime.fromisoformat(after.created_at) - datetime.fromisoformat(before.created_at)
    assert abs(delta.total_seconds()) < 5
    assert abs((utc_now() - datetime.fromisoformat(after.updated_at)).total_seconds()) < 5
    assert datetime.fromisoformat(before.created_at).tzinfo is not None


def test_format_timestamp_refreshes_timezone_without_changing_naive_values(change_timezone):
    instant = datetime(2026, 1, 1, tzinfo=timezone.utc)
    change_timezone("UTC0")
    assert format_timestamp(instant) == "2026-01-01 00:00:00.000"
    change_timezone("CST-8")
    assert format_timestamp(instant) == "2026-01-01 08:00:00.000"
    assert format_timestamp(instant.replace(tzinfo=None)) == "2026-01-01 00:00:00.000"


@pytest.mark.asyncio
async def test_asset_counter_update_binds_current_server_time(change_timezone):
    session = AsyncMock()
    change_timezone("UTC0")
    await LogKnowledgePGManager.refresh_kb_counters("asset", session=session)
    before = session.execute.call_args.args[1]["server_updated_at"]
    change_timezone("CST-8")
    await LogKnowledgePGManager.refresh_kb_counters("asset", session=session)
    sql, params = session.execute.call_args.args
    assert "NOW()" not in str(sql)
    assert ":server_updated_at" in str(sql)
    assert abs((params["server_updated_at"] - before).total_seconds()) < 5
    assert params["server_updated_at"].tzinfo is not None


def test_asset_timestamp_round_trip_preserves_instant_after_timezone_change(change_timezone):
    change_timezone("CST-8")
    stored = parse_asset_timestamp("2026-01-01 08:30:00.123")
    assert format_timestamp(stored) == "2026-01-01 08:30:00.123"
    change_timezone("UTC0")
    response = format_timestamp(stored)
    assert response == "2026-01-01 00:30:00.123"
    assert parse_asset_timestamp(response) == stored
    change_timezone("EST5")
    assert format_timestamp(stored) == "2025-12-31 19:30:00.123"


def test_asset_time_filter_uses_current_server_timezone(change_timezone):
    change_timezone("CST-8")
    assert parse_asset_timestamp("2026-01-01 08:00:00") == datetime(2026, 1, 1, tzinfo=timezone.utc)
    assert parse_asset_timestamp("2026-01-01T00:00:00Z") == datetime(2026, 1, 1, tzinfo=timezone.utc)
    assert parse_asset_timestamp(None) is None


@pytest.mark.parametrize("server_zone", ["UTC0", "CST-8", "EST5"])
def test_browser_asset_filter_preserves_instant_across_server_timezones(
    change_timezone, server_zone
):
    change_timezone(server_zone)
    req = ListLogKnowledgeRequest(
        created_at_start="2026-01-01T00:30:00.000Z",
        created_at_end="2026-01-01T08:31:00+08:00",
    )
    assert parse_asset_timestamp(req.created_at_start) == datetime(
        2026, 1, 1, 0, 30, tzinfo=timezone.utc
    )
    assert parse_asset_timestamp(req.created_at_end) == datetime(
        2026, 1, 1, 0, 31, tzinfo=timezone.utc
    )


def test_legacy_asset_filter_still_uses_server_timezone(change_timezone):
    change_timezone("CST-8")
    req = ListLogKnowledgeRequest(created_at_start="2026-01-01 08:30:00")
    assert parse_asset_timestamp(req.created_at_start) == datetime(
        2026, 1, 1, 0, 30, tzinfo=timezone.utc
    )


@pytest.mark.parametrize("value", ["2026-01-01", "invalid", "2026-01-01T00:30:00"])
def test_asset_filter_rejects_invalid_or_ambiguous_new_formats(value):
    with pytest.raises(ValueError):
        ListLogKnowledgeRequest(created_at_start=value)


def test_log_time_filters_keep_their_existing_format():
    with pytest.raises(ValueError):
        ParseConfig(start_time="2026-01-01T00:30:00.000Z")
