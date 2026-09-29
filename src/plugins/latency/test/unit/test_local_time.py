# Copyright (c) Huawei Technologies Co., Ltd. 2023-2025. All rights reserved.
"""latency.common.local_time 单元测试。"""
from datetime import datetime, timezone

from latency.common.local_time import (
    legacy_asset_timezone,
    local_now,
    parse_asset_timestamp,
    utc_now,
)


class TestLocalNow:
    def test_returns_naive(self):
        assert local_now().tzinfo is None

    def test_close_to_now(self):
        delta = abs((local_now() - datetime.now()).total_seconds())
        assert delta < 5


class TestUtcNow:
    def test_returns_aware(self):
        assert utc_now().tzinfo is not None


class TestParseAssetTimestamp:
    def test_none(self):
        assert parse_asset_timestamp(None) is None

    def test_iso_string(self):
        result = parse_asset_timestamp("2024-01-15T10:30:00")
        assert result is not None
        assert result.year == 2024
        assert result.month == 1

    def test_aware_datetime_preserved(self):
        dt = datetime(2024, 1, 15, 10, 30, 0, tzinfo=timezone.utc)
        assert parse_asset_timestamp(dt) is dt

    def test_naive_datetime_becomes_aware(self):
        dt = datetime(2024, 1, 15, 10, 30, 0)
        result = parse_asset_timestamp(dt)
        assert result.tzinfo is not None


class TestLegacyAssetTimezone:
    def test_env_var_wins(self, monkeypatch):
        monkeypatch.setenv("WITTY_LEGACY_ASSET_TIMEZONE", "Asia/Tokyo")
        assert legacy_asset_timezone() == "Asia/Tokyo"

    def test_tz_env_var(self, monkeypatch):
        monkeypatch.delenv("WITTY_LEGACY_ASSET_TIMEZONE", raising=False)
        monkeypatch.setenv("TZ", ":Asia/Shanghai")
        assert legacy_asset_timezone() == "Asia/Shanghai"

    def test_fallback_returns_string(self, monkeypatch):
        monkeypatch.delenv("WITTY_LEGACY_ASSET_TIMEZONE", raising=False)
        monkeypatch.delenv("TZ", raising=False)
        result = legacy_asset_timezone()
        assert isinstance(result, str)
        assert len(result) > 0
