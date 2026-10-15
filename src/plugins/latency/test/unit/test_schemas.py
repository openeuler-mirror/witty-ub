# Copyright (c) Huawei Technologies Co., Ltd. 2023-2025. All rights reserved.
"""latency schemas 单元测试：parse_config / ds_log。"""
import pickle
from datetime import datetime

import pytest
from pydantic import ValidationError

from latency.ENUM.ds_log import EntryType
from latency.schemas.ds_log import CorrelationResult, LogEntry
from latency.schemas.parse_config import ParseConfig, SortField


class TestParseConfig:
    def test_defaults(self):
        cfg = ParseConfig()
        assert cfg.start_time is None
        assert cfg.end_time is None
        assert cfg.min_elapsed_ms is None
        assert cfg.is_time_filter_enabled() is False
        assert cfg.is_elapsed_filter_enabled() is False

    def test_time_filter_enabled(self):
        cfg = ParseConfig(start_time="2024-01-15 00:00:00")
        assert cfg.is_time_filter_enabled() is True

        cfg = ParseConfig(end_time="2024-01-15 23:59:59")
        assert cfg.is_time_filter_enabled() is True

    def test_elapsed_filter_enabled(self):
        cfg = ParseConfig(min_elapsed_ms=100)
        assert cfg.is_elapsed_filter_enabled() is True

    def test_invalid_time_format_rejected(self):
        with pytest.raises(ValidationError):
            ParseConfig(start_time="2024/01/15 00:00:00")
        with pytest.raises(ValidationError):
            ParseConfig(start_time="not-a-time")

    def test_strict_mode_rejects_string_int(self):
        with pytest.raises(ValidationError):
            ParseConfig(min_elapsed_ms="100")

    def test_valid_full_config(self):
        cfg = ParseConfig(
            start_time="2024-01-15 00:00:00",
            end_time="2024-01-16 00:00:00",
            min_elapsed_ms=50,
        )
        assert cfg.start_time == "2024-01-15 00:00:00"
        assert cfg.end_time == "2024-01-16 00:00:00"
        assert cfg.min_elapsed_ms == 50
        assert cfg.is_time_filter_enabled() is True
        assert cfg.is_elapsed_filter_enabled() is True


class TestSortField:
    def test_defaults(self):
        sf = SortField(field="total_latency")
        assert sf.field == "total_latency"
        assert sf.order == "desc"

    def test_explicit_order(self):
        sf = SortField(field="timestamp", order="asc")
        assert sf.order == "asc"

    def test_field_required(self):
        with pytest.raises(ValidationError):
            SortField()


class TestLogEntry:
    def make_entry(self, **overrides):
        base = dict(
            timestamp=datetime(2024, 1, 15, 10, 30, 0),
            trace_id="t1",
            pod_ip="10.0.0.1",
            elapsed_us=123.5,
            entry_type=EntryType.SDK_GET,
        )
        base.update(overrides)
        return LogEntry(**base)

    def test_required_fields(self):
        e = self.make_entry()
        assert e.trace_id == "t1"
        assert e.pod_ip == "10.0.0.1"
        assert e.elapsed_us == 123.5
        assert e.entry_type == EntryType.SDK_GET

    def test_optional_defaults(self):
        e = self.make_entry()
        assert e.log_id is None
        assert e.operation is None
        assert e.object_key is None
        assert e.status_code is None
        assert e.cluster_name is None

    def test_pickle_roundtrip(self):
        e = self.make_entry(status_code=200, operation="GET")
        restored = pickle.loads(pickle.dumps(e))
        assert restored.trace_id == "t1"
        assert restored.status_code == 200
        assert restored.entry_type == EntryType.SDK_GET
        assert restored.timestamp == e.timestamp


class TestCorrelationResult:
    def test_all_maps_default_empty(self):
        import dataclasses

        cr = CorrelationResult()
        for f in dataclasses.fields(cr):
            assert getattr(cr, f.name) == {}, f"{f.name} 应默认为空 dict"

    def test_maps_are_independent(self):
        cr = CorrelationResult()
        cr.sdk_worker_map["a"] = 1
        assert cr.sdk_urma_map == {}
