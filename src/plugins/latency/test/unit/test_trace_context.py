# Copyright (c) Huawei Technologies Co., Ltd. 2023-2025. All rights reserved.
"""latency.common.trace_context 单元测试（纯函数 + collect 流程 mock DB）。"""
from latency.common.trace_context import (
    build_trace_context_event,
    collect_trace_context_logs,
    match_trace_context_trace_id,
    split_pid_tid,
)
from latency.database.managers.log_failure_event import LogFailureEventPGManager

RUN_LINE = (
    "2024-01-15 10:30:00|I|file.cpp:42|pod1|123:456|trace-1|cluster1|run message here"
)
ACCESS_LINE = (
    "2024-01-15 10:30:00|I|file.cpp:42|pod1|123:456|trace-1|cluster1|"
    "200|GET|100|1024|req msg|resp msg"
)


class TestSplitPidTid:
    def test_with_colon(self):
        assert split_pid_tid("123:456") == ("123", "456")

    def test_without_colon(self):
        assert split_pid_tid("123") == ("123", "")

    def test_strips_whitespace(self):
        assert split_pid_tid(" 123 : 456 ") == ("123", "456")

    def test_empty(self):
        assert split_pid_tid("") == ("", "")


class TestMatchTraceContextTraceId:
    def test_raw_id_in_set(self):
        assert match_trace_context_trace_id("t1", "anything", {"t1"}) == "t1"

    def test_resolves_explicit_from_text(self):
        # 格式列不在集合中，但 message 中的显式 trace_id 在
        assert match_trace_context_trace_id("t2", "trace_id=t9", {"t9"}) == "t9"

    def test_raw_not_in_set_no_fallback(self):
        assert match_trace_context_trace_id("t2", "plain text", {"t1"}) == ""

    def test_empty_everything(self):
        assert match_trace_context_trace_id("", "", {"t1"}) == ""


class TestBuildTraceContextEvent:
    def test_run_line(self):
        event = build_trace_context_event(
            log_id="log-1", log_dir="/data", path="/data/Worker_10.0.0.1/app.log",
            line_no=1, line=RUN_LINE, trace_ids={"trace-1"},
        )
        assert event is not None
        assert event.log_id == "log-1"
        assert event.trace_id == "trace-1"
        assert event.pod_name == "pod1"
        assert event.pid == "123"
        assert event.tid == "456"
        assert event.level == "I"
        assert event.message == "run message here"
        assert event.status_code == ""

    def test_access_line(self):
        event = build_trace_context_event(
            log_id="log-1", log_dir="/data", path="/data/Worker_10.0.0.1/app.log",
            line_no=1, line=ACCESS_LINE, trace_ids={"trace-1"},
        )
        assert event is not None
        assert event.status_code == "200"
        assert "GET" in event.message
        assert "elapsed=100" in event.message

    def test_blank_line_returns_none(self):
        assert build_trace_context_event("l", "/d", "/d/f.log", 1, "   ", {"t"}) is None

    def test_non_timestamp_prefix_returns_none(self):
        line = "garbage|line|with|eight|columns|a|b|c|d"
        assert build_trace_context_event("l", "/d", "/d/f.log", 1, line, {"c"}) is None

    def test_short_line_returns_none(self):
        assert build_trace_context_event("l", "/d", "/d/f.log", 1, "2024 only", {"t"}) is None

    def test_trace_not_matched_returns_none(self):
        assert build_trace_context_event(
            "l", "/d", "/d/f.log", 1, RUN_LINE, {"other-trace"}
        ) is None


class TestCollectTraceContextLogs:
    @staticmethod
    def _patch_manager(monkeypatch):
        """替换 PG manager 的三个静态方法为内存记录版。"""
        state = {"deleted": [], "stored": []}

        @staticmethod
        async def fake_delete(log_id):
            state["deleted"].append(log_id)
            return True

        @staticmethod
        async def fake_add_if_not_exist(batch):
            state["stored"].extend(batch)
            return []

        @staticmethod
        async def fake_add(batch):
            state["stored"].extend(batch)
            return []

        monkeypatch.setattr(LogFailureEventPGManager, "delete_unclassified_log_events_by_log_id", fake_delete)
        monkeypatch.setattr(LogFailureEventPGManager, "add_log_failure_event_if_not_exist", fake_add_if_not_exist)
        monkeypatch.setattr(LogFailureEventPGManager, "add_log_failure_event", fake_add)
        return state

    async def test_collects_matching_lines(self, tmp_path, monkeypatch):
        state = self._patch_manager(monkeypatch)
        (tmp_path / "Worker_pod1").mkdir()
        (tmp_path / "Worker_pod1" / "app.log").write_text(
            RUN_LINE + "\n" + "garbage line\n", encoding="utf-8"
        )
        total = await collect_trace_context_logs(
            "log-1", str(tmp_path), {"trace-1"}, clear_existing=True
        )
        assert total == 1
        assert state["deleted"] == ["log-1"]
        assert len(state["stored"]) == 1
        event = state["stored"][0]
        assert event.trace_id == "trace-1"
        assert event.log_id == "log-1"

    async def test_no_clear_skips_delete(self, tmp_path, monkeypatch):
        state = self._patch_manager(monkeypatch)
        (tmp_path / "app.log").write_text(RUN_LINE + "\n", encoding="utf-8")
        total = await collect_trace_context_logs("log-1", str(tmp_path), {"trace-1"})
        assert total == 1
        assert state["deleted"] == []

    async def test_empty_trace_ids_returns_zero(self, tmp_path, monkeypatch):
        state = self._patch_manager(monkeypatch)
        assert await collect_trace_context_logs("log-1", str(tmp_path), set()) == 0
        assert state["stored"] == []

    async def test_missing_dir_returns_zero(self, tmp_path, monkeypatch):
        self._patch_manager(monkeypatch)
        assert await collect_trace_context_logs("log-1", str(tmp_path / "nope"), {"t"}) == 0

    async def test_whitespace_trace_ids_stripped(self, tmp_path, monkeypatch):
        state = self._patch_manager(monkeypatch)
        (tmp_path / "app.log").write_text(RUN_LINE + "\n", encoding="utf-8")
        total = await collect_trace_context_logs("log-1", str(tmp_path), {" trace-1 "})
        assert total == 1
        assert state["stored"][0].trace_id == "trace-1"
