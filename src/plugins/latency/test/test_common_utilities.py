# Copyright (c) Huawei Technologies Co., Ltd. 2023-2025. All rights reserved.
"""common/ 工具模块 + bucket/statistics 缺口补充单测。

只补现有测试未覆盖的分支（覆盖率缺口），不重复既有用例：
  - sampler: 采样器纯逻辑（raw 窗口采样 / bucketed 聚合 / 时间戳解析）
  - zip_handler: is_zip_file / check_zip_file / zip_dir / 解压过滤与目录成员
  - aggregate_cache: 内存缓存 set/get/find/clear
  - ds_log_io: Progress 输出 / parse_timestamp / open_log gz
  - local_time: legacy_asset_timezone 无 zoneinfo 时的 POSIX 偏移回退
  - trace_context: collect 批量落库 / 损坏 gz / 通用异常跳过
  - disk: _read_rotational 异常分支
  - stage_progress: 未知 stage / report detail
  - bucket/statistics: _store_bucket_rows COPY 路径 / _report / 失败重抛
"""
from __future__ import annotations

import asyncio
import gzip
import io
import json
import os
import re
import zipfile
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import AsyncMock

import pytest

from latency.ENUM.sampling import SampleMode
from latency.common import disk
from latency.common import trace_context as trace_context_module
from latency.common.aggregate_cache import (
    clear_cache,
    find_aggregated_by_kb_id,
    get_aggregated_events,
    get_time_window_events,
    set_aggregated_events,
    set_time_window_events,
)
from latency.common.ds_log_io import (
    Progress,
    glob_paths,
    open_log,
    parse_timestamp,
)
from latency.common.local_time import legacy_asset_timezone
from latency.common.sampler import LatencyMetricsSampler, _METRIC_KEYS
from latency.common.stage_progress import StageProgress
from latency.common.trace_context import TRACE_CONTEXT_BATCH_SIZE, collect_trace_context_logs
from latency.common.zip_handler import ZipHandler
from latency.database.managers.log_failure_event import LogFailureEventPGManager
from latency.database.managers.time_window_aggregated_event import (
    TimeWindowAggregatedEventDataclass,
)
from latency.schemas.log import SrcDstAggregatedEventDataclass


# ---------------------------------------------------------------------------
# common/sampler.py
# ---------------------------------------------------------------------------

def _raw_metrics(n: int = 100) -> list[dict]:
    base = datetime(2024, 1, 1)
    return [
        {"time": base + timedelta(seconds=i), "total_latency": float(i)}
        for i in range(n)
    ]


class TestSampleRawData:
    def test_passthrough_when_under_limit(self):
        metrics = _raw_metrics(5)
        sampled, info = LatencyMetricsSampler.sample(metrics, 10, SampleMode.MAX)
        assert sampled == metrics
        assert info == {
            "mode": "none", "window_ms": 0,
            "original_count": 5, "sampled_count": 5,
        }

    def test_passthrough_when_max_points_minus_one(self):
        metrics = _raw_metrics(50)
        sampled, info = LatencyMetricsSampler.sample(metrics, -1, SampleMode.AVG)
        assert sampled == metrics
        assert info["mode"] == "none"
        assert info["sampled_count"] == 50

    def test_empty_metrics(self):
        sampled, info = LatencyMetricsSampler.sample([], 5, SampleMode.MAX)
        assert sampled == []
        assert info["mode"] == "none"
        assert info["sampled_count"] == 0

    def test_all_unparseable_times_returns_empty(self):
        metrics = [{"time": "not-a-date", "total_latency": 1.0} for _ in range(20)]
        sampled, info = LatencyMetricsSampler.sample(metrics, 5, SampleMode.MAX)
        assert sampled == []
        assert info == {
            "mode": "max", "window_ms": 0,
            "original_count": 20, "sampled_count": 0,
        }

    def test_identical_timestamps_collapse_to_single_point(self):
        ts = datetime(2024, 1, 1, 12, 0, 0)
        metrics = [{"time": ts, "total_latency": float(i)} for i in range(10)]
        sampled, info = LatencyMetricsSampler.sample(metrics, 2, SampleMode.MAX)
        assert len(sampled) == 1
        assert info["sampled_count"] == 1
        assert info["window_ms"] == 0
        # time_span<=0 分支直接取首行指标值（0.0），不做窗口聚合
        assert sampled[0]["total_latency"] == 0.0

    def test_window_sampling_buckets_by_time(self):
        metrics = _raw_metrics(100)
        base_ms = int(datetime(2024, 1, 1).timestamp() * 1000)
        sampled, info = LatencyMetricsSampler.sample(metrics, 10, SampleMode.MAX)
        assert info == {
            "mode": "max", "window_ms": 9900,
            "original_count": 100, "sampled_count": 10,
        }
        assert len(sampled) == 10
        for k, item in enumerate(sampled):
            # 窗口 k 覆盖秒 [k*10, k*10+9]，MAX 聚合 → k*10+9
            assert item["total_latency"] == float(k * 10 + 9)
            expected_mid_ms = base_ms + k * 10000 + 4500
            assert item["time"] == LatencyMetricsSampler._ms_to_timestamp(expected_mid_ms)

    def test_none_values_in_window_aggregate_to_none(self):
        base = datetime(2024, 1, 1)
        metrics = [
            {"time": base, "total_latency": None},
            {"time": base + timedelta(seconds=1), "total_latency": None},
        ]
        metrics += [
            {"time": base + timedelta(seconds=20 + i), "total_latency": 1.0}
            for i in range(5)
        ]
        sampled, info = LatencyMetricsSampler.sample(metrics, 2, SampleMode.MAX)
        # 窗口跨度 24s / 2 窗口 → 边界 12s：0s/1s 落窗口 1，20s+ 落窗口 2
        assert sampled[0]["total_latency"] is None
        assert sampled[1]["total_latency"] == 1.0


class TestSampleBucketedData:
    @staticmethod
    def _row(time: str, values: list) -> dict:
        return {"time": time, "total_latency_values": json.dumps(values)}

    def test_rows_aggregated_per_mode_with_window(self):
        rows = [
            self._row("2024-01-01 00:00:00", [1.0, 5.0, 3.0]),
            self._row("2024-01-01 00:00:10", [2.0, 2.0]),
            self._row("2024-01-01 00:00:20", [7.0]),
        ]
        sampled, info = LatencyMetricsSampler.sample(
            rows, 10, SampleMode.AVG, original_count=300
        )
        assert info == {
            "mode": "avg", "window_ms": 10000,
            "original_count": 300, "sampled_count": 3,
        }
        assert [r["total_latency"] for r in sampled] == [3.0, 2.0, 7.0]
        # 行内未提供的指标键 → None
        assert sampled[0]["sdk_process"] is None

    def test_single_row_window_zero(self):
        rows = [self._row("2024-01-01 00:00:00", [4.0, 2.0])]
        sampled, info = LatencyMetricsSampler.sample(rows, 10, SampleMode.MAX)
        assert info["window_ms"] == 0
        assert info["sampled_count"] == 1
        assert sampled[0]["total_latency"] == 4.0

    def test_multiple_rows_with_unparseable_times_window_zero(self):
        rows = [self._row("garbage", [1.0]), self._row("alsobad", [2.0])]
        sampled, info = LatencyMetricsSampler.sample(rows, 10, SampleMode.MAX)
        assert info["window_ms"] == 0
        assert len(sampled) == 2

    def test_percentile_mode_picks_sorted_rank(self):
        rows = [self._row("2024-01-01 00:00:00", list(range(100)))]
        sampled, info = LatencyMetricsSampler.sample(rows, 10, SampleMode.P99)
        assert info["mode"] == "p99"
        assert sampled[0]["total_latency"] == 98.0


class TestSamplerParseJsonArray:
    def test_none_and_empty(self):
        assert LatencyMetricsSampler._parse_json_array(None) == []
        assert LatencyMetricsSampler._parse_json_array("[]") == []

    def test_valid_with_null_filtered(self):
        assert LatencyMetricsSampler._parse_json_array('[1, 2.5, null]') == [1.0, 2.5]

    def test_invalid_json(self):
        assert LatencyMetricsSampler._parse_json_array("not-json") == []

    def test_non_string_input(self):
        assert LatencyMetricsSampler._parse_json_array(123) == []

    def test_non_numeric_members(self):
        assert LatencyMetricsSampler._parse_json_array('["a"]') == []


class TestSamplerParseTimestampToMs:
    def test_numeric_string_passthrough(self):
        assert LatencyMetricsSampler._parse_timestamp_to_ms("1700000000123") == 1700000000123

    def test_float_string_truncates(self):
        assert LatencyMetricsSampler._parse_timestamp_to_ms("1700000000.9") == 1700000000

    def test_naive_datetime(self):
        dt = datetime(2024, 1, 1, 10, 0, 0)
        assert LatencyMetricsSampler._parse_timestamp_to_ms(dt) == int(dt.timestamp() * 1000)

    def test_aware_datetime_strips_tzinfo(self):
        dt = datetime(2024, 1, 1, 10, 0, 0, tzinfo=timezone.utc)
        expected = int(datetime(2024, 1, 1, 10, 0, 0).timestamp() * 1000)
        assert LatencyMetricsSampler._parse_timestamp_to_ms(dt) == expected

    def test_space_separated_string_second_resolution(self):
        a = LatencyMetricsSampler._parse_timestamp_to_ms("2024-01-01 10:00:00")
        b = LatencyMetricsSampler._parse_timestamp_to_ms("2024-01-01 10:00:01")
        assert b - a == 1000

    def test_iso_t_string_matches_space_form(self):
        assert (
            LatencyMetricsSampler._parse_timestamp_to_ms("2024-01-01T10:00:00")
            == LatencyMetricsSampler._parse_timestamp_to_ms("2024-01-01 10:00:00")
        )

    def test_millisecond_fraction(self):
        a = LatencyMetricsSampler._parse_timestamp_to_ms("2024-01-01 10:00:00.123")
        b = LatencyMetricsSampler._parse_timestamp_to_ms("2024-01-01 10:00:00")
        assert a - b == 123

    def test_short_non_padded_form_via_strptime(self):
        # 18 字符（月份无前导零）绕过手写解析，走 strptime 兜底分支
        assert (
            LatencyMetricsSampler._parse_timestamp_to_ms("2024-1-01 10:00:00")
            == LatencyMetricsSampler._parse_timestamp_to_ms("2024-01-01 10:00:00")
        )

    def test_garbage_returns_none(self):
        assert LatencyMetricsSampler._parse_timestamp_to_ms("definitely-not-a-timestamp") is None

    def test_invalid_month_returns_none(self):
        assert LatencyMetricsSampler._parse_timestamp_to_ms("2024-13-01 10:00:00") is None


class TestSamplerAggregateValues:
    def test_empty_returns_none(self):
        assert LatencyMetricsSampler._aggregate_values([], SampleMode.MAX) is None

    def test_max(self):
        assert LatencyMetricsSampler._aggregate_values([1.0, 5.0, 3.0], SampleMode.MAX) == 5.0

    def test_min(self):
        assert LatencyMetricsSampler._aggregate_values([1.0, 5.0, 3.0], SampleMode.MIN) == 1.0

    def test_avg(self):
        assert LatencyMetricsSampler._aggregate_values([1.0, 5.0, 3.0], SampleMode.AVG) == 3.0

    def test_p99(self):
        assert LatencyMetricsSampler._aggregate_values(list(range(100)), SampleMode.P99) == 98.0

    def test_p95(self):
        assert LatencyMetricsSampler._aggregate_values(list(range(100)), SampleMode.P95) == 94.0

    def test_p9999(self):
        assert LatencyMetricsSampler._aggregate_values(list(range(100)), SampleMode.P9999) == 98.0

    def test_unmapped_mode_falls_back_to_max(self):
        assert LatencyMetricsSampler._aggregate_values([1.0, 5.0], SampleMode.NONE) == 5.0


class TestSamplerBuildSampledItem:
    def test_single_timestamp(self):
        values = [[] for _ in _METRIC_KEYS]
        values[0] = [1.0, 2.0]
        item = LatencyMetricsSampler._build_sampled_item([5000], values, SampleMode.MAX)
        assert item["time"] == LatencyMetricsSampler._ms_to_timestamp(5000.0)
        assert item[_METRIC_KEYS[0]] == 2.0
        assert item[_METRIC_KEYS[1]] is None

    def test_multiple_timestamps_use_midpoint(self):
        values = [[] for _ in _METRIC_KEYS]
        item = LatencyMetricsSampler._build_sampled_item([1000, 3000], values, SampleMode.AVG)
        assert item["time"] == LatencyMetricsSampler._ms_to_timestamp(2000.0)

    def test_ms_to_timestamp_millisecond_precision(self):
        result = LatencyMetricsSampler._ms_to_timestamp(1700000000123.0)
        expected = datetime.fromtimestamp(1700000000.123).strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
        assert result == expected


# ---------------------------------------------------------------------------
# common/zip_handler.py
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def _run_to_thread_inline(monkeypatch):
    async def to_thread(function, *args, **kwargs):
        return function(*args, **kwargs)

    monkeypatch.setattr(asyncio, "to_thread", to_thread)


class TestIsZipFile:
    def test_missing_file(self, tmp_path):
        assert ZipHandler.is_zip_file(str(tmp_path / "nope.zip")) is False

    def test_non_zip_file(self, tmp_path):
        plain = tmp_path / "plain.txt"
        plain.write_text("hello")
        assert ZipHandler.is_zip_file(str(plain)) is False

    def test_valid_zip(self, tmp_path):
        archive = tmp_path / "ok.zip"
        with zipfile.ZipFile(archive, "w") as zf:
            zf.writestr("a.log", "data")
        assert ZipHandler.is_zip_file(str(archive)) is True


class TestCheckZipFile:
    @staticmethod
    def _make_zip(tmp_path, n_files=2, content="x" * 10):
        archive = tmp_path / "check.zip"
        with zipfile.ZipFile(archive, "w") as zf:
            for i in range(n_files):
                zf.writestr(f"f{i}.log", content)
        return archive

    def test_within_limits(self, tmp_path):
        archive = self._make_zip(tmp_path, n_files=2, content="x" * 10)
        assert ZipHandler.check_zip_file(str(archive), max_file_num=5, max_file_size=100) is True

    def test_unlimited_when_limits_none(self, tmp_path):
        archive = self._make_zip(tmp_path, n_files=3)
        assert ZipHandler.check_zip_file(str(archive)) is True

    def test_exceeds_file_num(self, tmp_path):
        archive = self._make_zip(tmp_path, n_files=3)
        assert ZipHandler.check_zip_file(str(archive), max_file_num=2, max_file_size=1000) is False

    def test_exceeds_total_size(self, tmp_path):
        archive = self._make_zip(tmp_path, n_files=2, content="x" * 100)
        assert ZipHandler.check_zip_file(str(archive), max_file_num=10, max_file_size=150) is False

    def test_bad_zip_file(self, tmp_path):
        bad = tmp_path / "bad.zip"
        bad.write_bytes(b"this is not a zip archive")
        assert ZipHandler.check_zip_file(str(bad)) is False

    def test_missing_file(self, tmp_path):
        assert ZipHandler.check_zip_file(str(tmp_path / "missing.zip")) is False


class TestZipDir:
    def test_zips_directory_tree(self, tmp_path):
        src = tmp_path / "src"
        (src / "nested").mkdir(parents=True)
        (src / "top.log").write_text("top")
        (src / "nested" / "inner.log").write_text("inner")
        zip_path = tmp_path / "out.zip"

        asyncio.run(ZipHandler.zip_dir(str(src), str(zip_path)))

        with zipfile.ZipFile(zip_path) as zf:
            names = set(zf.namelist())
            assert names == {"top.log", "nested/inner.log"}
            assert zf.read("nested/inner.log") == b"inner"

    def test_error_is_reraised(self, tmp_path):
        src = tmp_path / "src"
        src.mkdir()
        with pytest.raises(FileNotFoundError):
            asyncio.run(ZipHandler.zip_dir(str(src), str(tmp_path / "no_such_dir" / "out.zip")))


class TestUnzipFileGaps:
    def test_files_to_extract_filters_members(self, tmp_path):
        archive = tmp_path / "sel.zip"
        with zipfile.ZipFile(archive, "w") as zf:
            zf.writestr("keep.log", "keep")
            zf.writestr("skip.log", "skip")
        target = tmp_path / "out"

        asyncio.run(ZipHandler.unzip_file(str(archive), str(target), ["keep.log"]))

        assert (target / "keep.log").read_text() == "keep"
        assert not (target / "skip.log").exists()

    def test_directory_members_create_dirs(self, tmp_path):
        archive = tmp_path / "dirs.zip"
        with zipfile.ZipFile(archive, "w") as zf:
            zf.writestr("nested/", "")
            zf.writestr("nested/file.log", "content")
        target = tmp_path / "out"

        asyncio.run(ZipHandler.unzip_file(str(archive), str(target)))

        assert (target / "nested").is_dir()
        assert (target / "nested" / "file.log").read_text() == "content"

    def test_corrupted_zip_raises(self, tmp_path):
        bad = tmp_path / "bad.zip"
        bad.write_bytes(b"not a zip")
        with pytest.raises(zipfile.BadZipFile):
            asyncio.run(ZipHandler.unzip_file(str(bad), str(tmp_path / "out")))


# ---------------------------------------------------------------------------
# common/aggregate_cache.py
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def _clean_aggregate_cache():
    clear_cache()
    yield
    clear_cache()


def _agg_event(log_id="lg-1", kb_id="") -> SrcDstAggregatedEventDataclass:
    return SrcDstAggregatedEventDataclass(
        id="e-1", src_ip="1.1.1.1", dst_ip="2.2.2.2", log_id=log_id, kb_id=kb_id
    )


class TestAggregatedEventCache:
    def test_set_get_roundtrip_without_kb_id(self):
        events = [_agg_event()]
        set_aggregated_events("lg-1", events)
        assert get_aggregated_events("lg-1") is events
        assert events[0].kb_id == ""
        assert get_aggregated_events("other") is None

    def test_set_with_kb_id_mutates_events(self):
        events = [_agg_event()]
        set_aggregated_events("lg-1", events, kb_id="kb-9")
        assert events[0].kb_id == "kb-9"

    def test_find_by_kb_id_hit(self):
        events = [_agg_event(kb_id="kb-9"), _agg_event(kb_id="kb-9")]
        set_aggregated_events("lg-1", events)
        assert find_aggregated_by_kb_id("kb-9") is events

    def test_find_by_kb_id_miss_returns_none(self):
        set_aggregated_events("lg-1", [_agg_event(kb_id="kb-9")])
        assert find_aggregated_by_kb_id("kb-other") is None
        # 空缓存同样返回 None
        clear_cache()
        assert find_aggregated_by_kb_id("kb-9") is None

    def test_clear_single_log_id_keeps_others(self):
        set_aggregated_events("lg-1", [_agg_event("lg-1")])
        set_aggregated_events("lg-2", [_agg_event("lg-2")])
        set_time_window_events("lg-1", [TimeWindowAggregatedEventDataclass()])
        clear_cache("lg-1")
        assert get_aggregated_events("lg-1") is None
        assert get_time_window_events("lg-1") is None
        assert get_aggregated_events("lg-2") is not None

    def test_clear_all(self):
        set_aggregated_events("lg-1", [_agg_event("lg-1")])
        set_time_window_events("lg-1", [TimeWindowAggregatedEventDataclass()])
        clear_cache()
        assert get_aggregated_events("lg-1") is None
        assert get_time_window_events("lg-1") is None


class TestTimeWindowCache:
    def test_set_get_roundtrip(self):
        events = [TimeWindowAggregatedEventDataclass(id="tw-1")]
        set_time_window_events("lg-1", events)
        assert get_time_window_events("lg-1") is events
        assert get_time_window_events("missing") is None

    def test_clear_removes_only_target(self):
        set_time_window_events("lg-1", [TimeWindowAggregatedEventDataclass()])
        set_time_window_events("lg-2", [TimeWindowAggregatedEventDataclass()])
        clear_cache("lg-1")
        assert get_time_window_events("lg-1") is None
        assert get_time_window_events("lg-2") is not None


# ---------------------------------------------------------------------------
# common/ds_log_io.py
# ---------------------------------------------------------------------------

class TestProgressOutput:
    def test_update_with_all_fields(self):
        progress = Progress("label", total_file=3)
        progress.update(
            file_idx=2,
            path="/data/Worker_pod/app.log",
            line=1000,
            row=42,
            match=7,
        )
        assert progress.last_len > 0

    def test_update_with_fewer_fields_shrinks_line(self):
        progress = Progress("label", total_file=3)
        progress.update(file_idx=1, path="/data/Worker_pod/a.log", line=999999, match=123456)
        assert progress.last_len > 0
        progress.update(file_idx=1)
        assert progress.last_len > 0

    def test_done_with_rows_and_match(self):
        progress = Progress("label")
        progress.update(line=5)
        progress.done(rows=100, match=10)
        assert progress.last_len == 0


class TestDsLogIoParseTimestamp:
    def test_valid_space_format(self):
        assert parse_timestamp("2024-01-15 10:30:00") == datetime(2024, 1, 15, 10, 30)

    def test_invalid_raises_with_message(self):
        with pytest.raises(ValueError, match="Invalid timestamp"):
            parse_timestamp("not-a-timestamp")


class TestOpenLog:
    def test_plain_file(self, tmp_path):
        path = tmp_path / "a.log"
        path.write_text("line1\nline2\n")
        with open_log(str(path)) as f:
            assert f.readlines() == ["line1\n", "line2\n"]

    def test_valid_gz_file(self, tmp_path):
        path = tmp_path / "a.log.gz"
        path.write_bytes(gzip.compress(b"compressed line\n"))
        with open_log(str(path)) as f:
            assert f.read() == "compressed line\n"

    def test_missing_gz_returns_empty_stream(self, tmp_path):
        with open_log(str(tmp_path / "missing.log.gz")) as f:
            assert f.read() == ""


class TestGlobPaths:
    def test_deduplicates_and_expands(self, tmp_path):
        (tmp_path / "a.log").write_text("a")
        (tmp_path / "b.log").write_text("b")
        pattern = str(tmp_path / "*.log")
        assert sorted(glob_paths([pattern, pattern])) == sorted(
            [str(tmp_path / "a.log"), str(tmp_path / "b.log")]
        )


# ---------------------------------------------------------------------------
# common/local_time.py（无 zoneinfo 时的 POSIX 偏移回退）
# ---------------------------------------------------------------------------

class TestLegacyAssetTimezoneFallback:
    def test_non_zoneinfo_localtime_yields_posix_offset(self, monkeypatch):
        monkeypatch.delenv("WITTY_LEGACY_ASSET_TIMEZONE", raising=False)
        monkeypatch.delenv("TZ", raising=False)
        # /etc/localtime 是拷贝（非 zoneinfo 链接）→ 走偏移计算分支
        monkeypatch.setattr(Path, "resolve", lambda self: "/etc/localtime")
        result = legacy_asset_timezone()
        assert re.fullmatch(r"UTC[+-]\d{2}:\d{2}:\d{2}", result)


# ---------------------------------------------------------------------------
# common/trace_context.py（collect 批量 / 异常文件跳过）
# ---------------------------------------------------------------------------

RUN_LINE = "2024-01-15 10:30:00|I|file.cpp:42|pod1|123:456|trace-1|cluster1|run message"


def _patch_failure_event_manager(monkeypatch):
    """内存版 PG manager：记录 delete / 两类批量写调用。"""
    state = {"deleted": [], "batches": [], "final": []}

    async def fake_delete(log_id):
        state["deleted"].append(log_id)

    async def fake_add_if_not_exist(batch):
        state["batches"].append(list(batch))

    async def fake_add(batch):
        state["final"].append(list(batch))

    monkeypatch.setattr(
        LogFailureEventPGManager, "delete_unclassified_log_events_by_log_id", fake_delete
    )
    monkeypatch.setattr(
        LogFailureEventPGManager, "add_log_failure_event_if_not_exist", fake_add_if_not_exist
    )
    monkeypatch.setattr(LogFailureEventPGManager, "add_log_failure_event", fake_add)
    return state


class TestCollectTraceContextLogsGaps:
    async def test_batch_flush_beyond_batch_size(self, tmp_path, monkeypatch):
        state = _patch_failure_event_manager(monkeypatch)
        n = TRACE_CONTEXT_BATCH_SIZE + 76
        (tmp_path / "app.log").write_text("\n".join(RUN_LINE for _ in range(n)) + "\n")

        total = await collect_trace_context_logs("log-1", str(tmp_path), {"trace-1"})

        assert total == n
        # 批大小触发 add_log_failure_event_if_not_exist，剩余走 add_log_failure_event
        assert len(state["batches"]) == 1
        assert len(state["batches"][0]) == TRACE_CONTEXT_BATCH_SIZE
        assert len(state["final"]) == 1
        assert len(state["final"][0]) == 76
        assert state["deleted"] == []

    async def test_corrupted_gz_file_is_skipped(self, tmp_path, monkeypatch):
        state = _patch_failure_event_manager(monkeypatch)
        (tmp_path / "good.log").write_text(RUN_LINE + "\n")
        raw = gzip.compress(("\n".join(RUN_LINE for _ in range(50)) + "\n").encode())
        (tmp_path / "broken.log.gz").write_bytes(raw[: len(raw) // 2])

        total = await collect_trace_context_logs("log-1", str(tmp_path), {"trace-1"})

        assert total == 1
        assert len(state["final"]) == 1

    async def test_unreadable_file_is_skipped(self, tmp_path, monkeypatch):
        state = _patch_failure_event_manager(monkeypatch)
        (tmp_path / "good.log").write_text(RUN_LINE + "\n")
        (tmp_path / "boom.log").write_text(RUN_LINE + "\n")

        real_open = trace_context_module.open_log

        def flaky_open(path):
            if os.path.basename(path) == "boom.log":
                raise ValueError("boom")
            return real_open(path)

        monkeypatch.setattr(trace_context_module, "open_log", flaky_open)

        total = await collect_trace_context_logs("log-1", str(tmp_path), {"trace-1"})

        assert total == 1
        assert state["final"][0][0].log_file == "good.log"


# ---------------------------------------------------------------------------
# common/disk.py（_read_rotational 异常分支）
# ---------------------------------------------------------------------------

class TestReadRotationalErrors:
    def test_missing_sysfs_returns_none(self):
        assert disk._read_rotational("definitely-not-a-device") is None

    def test_non_numeric_content_returns_none(self, monkeypatch):
        monkeypatch.setattr(
            disk, "open", lambda *a, **k: io.StringIO("not-a-number"), raising=False
        )
        assert disk._read_rotational("sda") is None


# ---------------------------------------------------------------------------
# common/stage_progress.py（未知 stage / report detail）
# ---------------------------------------------------------------------------

class TestStageProgressGaps:
    def _reporter(self):
        calls = []

        async def reporter(task_id, message, progress):
            calls.append((task_id, message, progress))

        return calls, reporter

    def test_unknown_stage_raises_value_error(self):
        progress = StageProgress("task-1")
        with pytest.raises(ValueError, match="unknown stage"):
            progress.overall("no-such-stage", 0.5)

    async def test_report_appends_detail_message(self):
        calls, reporter = self._reporter()
        progress = StageProgress("task-1", reporter=reporter, now_fn=lambda: 0.0)
        value = await progress.report("scan", 0.5, detail="scanned 10 files")
        assert value == pytest.approx(22.5)  # scan 权重 45% × 0.5
        assert len(calls) == 1
        task_id, message, progress_value = calls[0]
        assert task_id == "task-1"
        assert message.startswith("[polars][scan]")
        assert message.endswith("scanned 10 files")
        assert progress_value == pytest.approx(22.5)


# ---------------------------------------------------------------------------
# bucket/statistics.py（_store_bucket_rows COPY / _report / 失败重抛）
# ---------------------------------------------------------------------------

class _FakeDriverConnection:
    def __init__(self):
        self.executed = []
        self.copied = []

    async def execute(self, sql, *args):
        self.executed.append((sql, args))

    async def copy_records_to_table(self, table, records, columns=None):
        self.copied.append((table, list(records), columns))


class _FakeRawConnection:
    def __init__(self, driver):
        self.driver_connection = driver

    async def get_raw_connection(self):
        return self


def _patch_pg_connection(monkeypatch, driver):
    @asynccontextmanager
    async def fake_connection():
        yield _FakeRawConnection(driver)

    from latency.database.engine import PGManager

    monkeypatch.setattr(PGManager, "connection", fake_connection)
    return driver


class TestStoreBucketRows:
    async def test_copies_each_granularity_in_one_connection(self, monkeypatch):
        from latency.bucket.statistics import (
            BUCKET_COLUMNS,
            GRANULARITY_KEYS,
            _store_bucket_rows,
        )

        driver = _FakeDriverConnection()
        _patch_pg_connection(monkeypatch, driver)

        rows = {g: [(f"v{g}-{i}",) for i in range(2)] for g in GRANULARITY_KEYS}
        tables = {g: f"tbl_{g}" for g in GRANULARITY_KEYS}
        on_table_calls = []

        async def on_table(g, t_table, n_rows):
            on_table_calls.append((g, n_rows))

        await _store_bucket_rows("log-1", rows, tables, on_table=on_table)

        # 每张表先 DELETE（带 log_id 参数）再 COPY
        assert len(driver.executed) == len(GRANULARITY_KEYS)
        for sql, args in driver.executed:
            assert sql.startswith("DELETE FROM tbl_")
            assert args == ("log-1",)
        assert len(driver.copied) == len(GRANULARITY_KEYS)
        copied_tables = {table: (records, columns) for table, records, columns in driver.copied}
        for g in GRANULARITY_KEYS:
            records, columns = copied_tables[f"tbl_{g}"]
            assert records == rows[g]
            assert columns == BUCKET_COLUMNS
            assert (g, 2) in on_table_calls

    async def test_empty_rows_skip_copy_but_still_delete(self, monkeypatch):
        from latency.bucket.statistics import DEFAULT_TABLES, GRANULARITY_KEYS, _store_bucket_rows

        driver = _FakeDriverConnection()
        _patch_pg_connection(monkeypatch, driver)

        await _store_bucket_rows("log-1", {g: [] for g in GRANULARITY_KEYS}, DEFAULT_TABLES)

        assert len(driver.executed) == len(GRANULARITY_KEYS)
        assert driver.copied == []


def _mini_trace_frame():
    import polars as pl

    return pl.DataFrame(
        {
            "bucket_epoch": [1704067200, 1704067200, 1704067205],
            "total_ms": [1.0, 2.0, 3.0],
            "total_latency": [1.0, 2.0, 3.0],
            "operation": ["GET", "GET", "SET"],
            "tid": ["t1", "t2", "t3"],
            "src": ["1.1.1.1"] * 3,
            "dst": ["2.2.2.2"] * 3,
        }
    )


class TestBucketReportDelegation:
    async def test_report_with_task_id_delegates_to_base_worker(self, monkeypatch):
        from latency.bucket.statistics import _report
        from latency.task.worker.base import BaseWorker

        mock = AsyncMock()
        monkeypatch.setattr(BaseWorker, "report", mock)

        await _report("task-1", "message", 12.5)

        mock.assert_awaited_once_with("task-1", "message", 12.5)

    async def test_report_swallows_base_worker_failure(self, monkeypatch):
        from latency.bucket.statistics import _report
        from latency.task.worker.base import BaseWorker

        async def boom(*args, **kwargs):
            raise RuntimeError("report backend down")

        monkeypatch.setattr(BaseWorker, "report", boom)
        await _report("task-1", "message", 0.0)  # 不抛出

    async def test_compute_and_store_failure_reports_and_reraises(self, monkeypatch):
        from latency.bucket import statistics as bstat
        from latency.task.worker.base import BaseWorker

        async def boom(log_id, rows_by_granularity, tables, on_table=None):
            raise RuntimeError("copy failed")

        monkeypatch.setattr(bstat, "_store_bucket_rows", boom)
        mock = AsyncMock()
        monkeypatch.setattr(BaseWorker, "report", mock)

        with pytest.raises(RuntimeError, match="copy failed"):
            await bstat.compute_and_store_bucket_stats_from_frame(
                _mini_trace_frame(), log_id="log-1", kb_id="kb-1", task_id="task-1"
            )

        # 先打阶段点，再打 FAILED 点后重抛
        assert mock.await_count == 2
        assert "FAILED" in mock.await_args.args[1]
        assert mock.await_args.args[2] == 100.0
