# Copyright (c) Huawei Technologies Co., Ltd. 2023-2025. All rights reserved.
"""latency.parse.base_parser 单元测试（静态/类方法 + 实例流程）。"""
from datetime import datetime

import pytest

from latency.ENUM.ds_log import EntryType, StatusCode
from latency.parse.base_parser import AccessLogParser, LogParser
from latency.schemas.ds_log import LogEntry
from latency.schemas.parse_config import ParseConfig

UUID_STR = "550e8400-e29b-41d4-a716-446655440000"

ACCESS_LINE = (
    "2024-01-15 10:30:00|I|file.cpp:42|pod1|123:456|trace-1|cluster1|"
    "200|GET|100|1024|req msg|resp msg"
)
RUN_LINE = "2024-01-15 10:30:00|I|file.cpp:42|pod1|123:456|trace-1|cluster1|run message"


class FakeParser(LogParser):
    """最小可运行子类：按 run 格式行产出 LogEntry。"""

    label = "fake"

    @property
    def patterns(self):
        return ["*.log"]

    def match_line(self, line: str, pod_ip: str):
        result = LogParser.parse_run_line(line)
        if result is None:
            return None
        return LogEntry(
            timestamp=datetime.strptime(result["timestamp"], "%Y-%m-%d %H:%M:%S"),
            trace_id=result["trace_id"],
            pod_ip=pod_ip,
            elapsed_us=1.0,
            entry_type=EntryType.SDK_GET,
        )


class TestParserInit:
    def test_default_config(self):
        parser = FakeParser()
        assert parser._start_dt is None
        assert parser._end_dt is None
        assert parser._filtered_by_time == 0

    def test_time_filter_config(self):
        parser = FakeParser(
            ParseConfig(start_time="2024-01-15 10:00:00", end_time="2024-01-15 11:00:00")
        )
        assert parser._start_dt == datetime(2024, 1, 15, 10, 0, 0)
        assert parser._end_dt == datetime(2024, 1, 15, 11, 0, 0)

    def test_no_time_filter_when_disabled(self):
        parser = FakeParser(ParseConfig(min_elapsed_ms=10))
        assert parser._start_dt is None
        assert parser._end_dt is None


class TestFilterByTime:
    def test_in_range(self):
        parser = FakeParser(
            ParseConfig(start_time="2024-01-15 10:00:00", end_time="2024-01-15 11:00:00")
        )
        assert parser._filter_by_time(datetime(2024, 1, 15, 10, 30, 0)) is True
        assert parser._filtered_by_time == 0

    def test_before_start(self):
        parser = FakeParser(ParseConfig(start_time="2024-01-15 10:00:00"))
        assert parser._filter_by_time(datetime(2024, 1, 15, 9, 0, 0)) is False
        assert parser._filtered_by_time == 1

    def test_after_end(self):
        parser = FakeParser(ParseConfig(end_time="2024-01-15 11:00:00"))
        assert parser._filter_by_time(datetime(2024, 1, 15, 12, 0, 0)) is False
        assert parser._filtered_by_time == 1

    def test_boundary_inclusive(self):
        parser = FakeParser(
            ParseConfig(start_time="2024-01-15 10:00:00", end_time="2024-01-15 11:00:00")
        )
        assert parser._filter_by_time(datetime(2024, 1, 15, 10, 0, 0)) is True
        assert parser._filter_by_time(datetime(2024, 1, 15, 11, 0, 0)) is True


class TestExtractPodIp:
    def test_worker_prefix(self):
        parser = FakeParser()
        assert parser.extract_pod_ip("/data/Worker_10.0.0.1/app.log") == "10.0.0.1"

    def test_dsworker_prefix(self):
        parser = FakeParser()
        assert parser.extract_pod_ip("/data/dsworker_pod-a/app.log") == "pod-a"

    def test_no_prefix(self):
        parser = FakeParser()
        assert parser.extract_pod_ip("/data/plain/app.log") == "plain"


class TestAbstractInterface:
    def test_patterns_property_raises_on_base(self):
        parser = FakeParser.__new__(FakeParser)
        with pytest.raises(NotImplementedError):
            LogParser.patterns.fget(parser)


class TestParseDirectory:
    def test_parse_collects_and_sorts(self, tmp_path):
        log_dir = tmp_path / "Worker_10.0.0.1"
        log_dir.mkdir()
        later = RUN_LINE.replace("10:30:00", "11:30:00")
        (log_dir / "app.log").write_text(
            later + "\n" + RUN_LINE + "\n" + "garbage line\n", encoding="utf-8"
        )
        parser = FakeParser()
        entries = parser.parse(str(tmp_path))
        # 两行合法 run 行 + 1 行垃圾（不以 2 开头被拒）
        assert len(entries) == 2
        # 结果按时间戳升序
        assert entries[0].timestamp < entries[1].timestamp
        # log_id 被绑定（同一文件共享）
        assert entries[0].log_id == entries[1].log_id
        assert entries[0].pod_ip == "10.0.0.1"

    def test_parse_empty_dir(self, tmp_path):
        parser = FakeParser()
        assert parser.parse(str(tmp_path)) == []

    def test_handle_errors_swallows_exception(self, tmp_path):
        class BrokenParser(FakeParser):
            _handle_errors = True

            def match_line(self, line, pod_ip):
                raise RuntimeError("boom")

        log_dir = tmp_path / "pod"
        log_dir.mkdir()
        (log_dir / "app.log").write_text(RUN_LINE + "\n", encoding="utf-8")
        parser = BrokenParser()
        assert parser.parse(str(tmp_path)) == []



class TestExtractExplicitTraceId:
    def test_equals_form(self):
        assert LogParser.extract_explicit_trace_id("x trace_id=abc123 y") == "abc123"

    def test_colon_form(self):
        assert LogParser.extract_explicit_trace_id("trace_id: abc123") == "abc123"

    def test_traceid_no_underscore(self):
        assert LogParser.extract_explicit_trace_id("traceid=xyz") == "xyz"

    def test_trace_hyphen_id(self):
        assert LogParser.extract_explicit_trace_id("trace-id: xyz") == "xyz"

    def test_no_trace_keyword(self):
        assert LogParser.extract_explicit_trace_id("hello world") == ""

    def test_empty(self):
        assert LogParser.extract_explicit_trace_id("") == ""

    def test_strips_brackets_and_quotes(self):
        assert LogParser.extract_explicit_trace_id('trace_id="[abc]"') == "abc"


class TestExtractTraceId:
    def test_prefers_explicit_over_uuid(self):
        line = f"trace_id=explicit-id uuid {UUID_STR}"
        assert LogParser.extract_trace_id(line) == "explicit-id"

    def test_falls_back_to_uuid(self):
        assert LogParser.extract_trace_id(f"some uuid {UUID_STR} here") == UUID_STR

    def test_returns_empty_when_neither(self):
        assert LogParser.extract_trace_id("no ids at all") == ""

    def test_empty_line(self):
        assert LogParser.extract_trace_id("") == ""


class TestResolveTraceId:
    def test_explicit_in_source_wins(self):
        assert LogParser.resolve_trace_id("col-id", "trace_id=msg-id") == "msg-id"

    def test_keeps_current_when_no_explicit(self):
        assert LogParser.resolve_trace_id("col-id", "plain message") == "col-id"

    def test_falls_back_to_uuid_in_source(self):
        assert LogParser.resolve_trace_id("", f"uuid {UUID_STR}") == UUID_STR

    def test_empty_when_nothing_available(self):
        assert LogParser.resolve_trace_id("", "nothing") == ""


class TestSplitByDelimiter:
    def test_basic(self):
        assert LogParser.split_by_delimiter("a|b|c") == ["a", "b", "c"]

    def test_empty(self):
        assert LogParser.split_by_delimiter("") == []


class TestParseAccessLine:
    def test_valid_line(self):
        result = LogParser.parse_access_line(ACCESS_LINE)
        assert result is not None
        assert result["timestamp"] == "2024-01-15 10:30:00"
        assert result["pod_name"] == "pod1"
        assert result["trace_id"] == "trace-1"
        assert result["cluster_name"] == "cluster1"
        assert result["status_code"] == "200"
        assert result["handle"] == "GET"
        assert result["elapsed"] == "100"
        assert result["size"] == "1024"
        assert result["req_msg"] == "req msg"
        assert result["resp_msg"] == "resp msg"

    def test_rejects_non_2_prefix(self):
        assert LogParser.parse_access_line("1999-01-01|x") is None

    def test_rejects_empty(self):
        assert LogParser.parse_access_line("") is None

    def test_rejects_short_line(self):
        # 12 列 < ACCESS_LOG_MIN_PARTS(13)
        short = "|".join(["x"] * 12)
        assert LogParser.parse_access_line("2" + short[1:]) is None

    def test_pads_missing_trailing_columns(self):
        # 13 列恰好满足，追加缺失列场景：截断到 11 列会失败
        line = ACCESS_LINE.rsplit("|", 2)[0]  # 去掉最后 2 列 → 11 列
        assert LogParser.parse_access_line(line) is None


class TestParseRunLine:
    def test_valid_line(self):
        result = LogParser.parse_run_line(RUN_LINE)
        assert result is not None
        assert result["timestamp"] == "2024-01-15 10:30:00"
        assert result["msg"] == "run message"
        assert result["trace_id"] == "trace-1"

    def test_rejects_non_2_prefix(self):
        assert LogParser.parse_run_line("x|a|b|c|d|e|f|g") is None

    def test_rejects_short_line(self):
        assert LogParser.parse_run_line("2|a|b|c|d|e|f") is None  # 7 列 < 8


class TestAccessLogParserHelpers:
    def test_parse_status_code_digits(self):
        assert AccessLogParser.parse_status_code("200") == 200

    def test_parse_status_code_non_digits_falls_back_ok(self):
        assert AccessLogParser.parse_status_code("abc") == StatusCode.OK
        assert AccessLogParser.parse_status_code("") == StatusCode.OK

    def test_extract_object_key_bracketed(self):
        assert AccessLogParser.extract_object_key("Object_key:[obj-123]") == "obj-123"

    def test_extract_object_key_plain(self):
        assert AccessLogParser.extract_object_key("object_key:obj-456, x") == "obj-456"

    def test_extract_object_key_missing(self):
        assert AccessLogParser.extract_object_key("no key here") == ""
        assert AccessLogParser.extract_object_key("") == ""
