# Copyright (c) Huawei Technologies Co., Ltd. 2023-2026. All rights reserved.
"""per-line 解析优化（T1 / Block B）parity 单测。

覆盖：
  1. parse_access_line / parse_run_line 对 valid / invalid / short 行行为不变。
  2. process_worker 的 _build_parsed_access / _build_parsed_run 与
     parse_access_line / parse_run_line 共享同一字段提取（去重后单实现），
     缺失列统一 pad 为空串。
  3. parse_timestamp 改 fromisoformat（先 ts.replace(" ", "T", 1)）后与旧
     手动切片在样本行（含空格分隔）上等价。
  4. Python 3.10 兼容：fromisoformat 必须先 replace 空格→T（3.10 拒绝空格
     分隔，本地 3.12 会掩盖崩溃 —— Oracle P1-3）。
  5. _pre_parsed 通路：解析器收到 process_worker 预解析 dict 时，match_line
     结果与直接 parse 完全一致。

运行：cd src/plugins/latency && PYTHONPATH=/home/li/witty-ub_8632/src/plugins \
  .venv/bin/python -m pytest test/test_parse_perline.py -v -p no:cacheprovider
"""
from __future__ import annotations

from datetime import datetime

import pytest

from latency.common.ds_log_io import parse_timestamp
from latency.parse.base_parser import LogParser

# ---------------------------------------------------------------------------
# 样本行（来自 data/logs/e2e-test-100m/ 真实日志）
# ---------------------------------------------------------------------------

ACCESS_LINE = (
    "2026-05-10T12:47:24.934807 | I | access_recorder.cpp:182 | "
    "searchctrwirelessub-24-00031 | 3941:3949 | "
    "9131c35c-9094-41bf-8204-e6b2ff438207 |  | 0 | DS_KV_CLIENT_GET | "
    "1204 | 8395125 | "
    "{Object_key:f6edb6d6-3efb-4144-83cd-0a4163eb1e73,timeout:0,transportType:SHM} | "
)

WORKER_ACCESS_LINE = (
    "2026-05-11T05:25:20.207278 | I | access_recorder.cpp:220 | "
    "searchctrwirelessub-24-00031 | 3941:3970 | "
    "56cc269c-2f76-47bc-a4fc-f1067f822fd1 |  | 0 | DS_POSIX_GET | "
    "773 | 8395125 | "
    "{Object_key:a2f216fd-d1a3-4c8c-b9ce-fa3e07e293e4,timeout:0,transportType:SHM} | "
)

RUN_LINE = (
    "2026-05-11T05:25:47.836541 | I | worker_impl.cpp:100 | "
    "searchctrwirelessub-24-00031 | 3941:3963 | "
    "8464033e-830d-448b-a845-ee419b8cab35 |  | "
    "[RPC_RECV_TIMEOUT] client timeout: 5000ms, peer worker alive"
)


def _new_helpers():
    """T1 去重后移入 base_parser 的字段提取 helper（延迟导入）。"""
    from latency.parse.base_parser import _build_parsed_access, _build_parsed_run

    return _build_parsed_access, _build_parsed_run


def _line_with_n_parts(n: int) -> str:
    """构造首字符为 '2'、恰好 n 个 '|' 分隔段的日志行。"""
    return "2" + "|".join(["x"] * n)


# ---------------------------------------------------------------------------
# 1. parse_access_line / parse_run_line 行为锁定
# ---------------------------------------------------------------------------

def test_parse_access_line_valid_returns_full_dict():
    d = LogParser.parse_access_line(ACCESS_LINE)
    assert d is not None
    assert d["timestamp"] == "2026-05-10T12:47:24.934807"
    assert d["pod_name"] == "searchctrwirelessub-24-00031"
    assert d["trace_id"] == "9131c35c-9094-41bf-8204-e6b2ff438207"
    assert d["cluster_name"] == ""
    assert d["status_code"] == "0"
    assert d["handle"] == "DS_KV_CLIENT_GET"
    assert d["elapsed"] == "1204"
    assert d["size"] == "8395125"
    assert d["req_msg"] == (
        "{Object_key:f6edb6d6-3efb-4144-83cd-0a4163eb1e73,"
        "timeout:0,transportType:SHM}"
    )
    assert d["resp_msg"] == ""


def test_parse_access_line_invalid_returns_none():
    assert LogParser.parse_access_line("") is None
    assert LogParser.parse_access_line(None) is None
    assert LogParser.parse_access_line("I | not | enough | parts") is None
    assert LogParser.parse_access_line("not starting with 2") is None


def test_parse_access_line_short_returns_none():
    # 12 段 < ACCESS_LOG_MIN_PARTS(13) → None
    assert LogParser.parse_access_line(_line_with_n_parts(12)) is None
    # 恰好 13 段 → dict
    assert LogParser.parse_access_line(_line_with_n_parts(13)) is not None


def test_parse_run_line_valid_returns_full_dict():
    d = LogParser.parse_run_line(RUN_LINE)
    assert d is not None
    assert d["timestamp"] == "2026-05-11T05:25:47.836541"
    assert d["pod_name"] == "searchctrwirelessub-24-00031"
    assert d["trace_id"] == "8464033e-830d-448b-a845-ee419b8cab35"
    assert d["cluster_name"] == ""
    assert d["msg"] == "[RPC_RECV_TIMEOUT] client timeout: 5000ms, peer worker alive"


def test_parse_run_line_short_and_invalid():
    assert LogParser.parse_run_line("") is None
    assert LogParser.parse_run_line("1...") is None
    # 7 段 < RUN_LOG_MIN_PARTS(8) → None；恰好 8 段 → dict
    assert LogParser.parse_run_line(_line_with_n_parts(7)) is None
    assert LogParser.parse_run_line(_line_with_n_parts(8)) is not None


# ---------------------------------------------------------------------------
# 2. 去重 helper 与 parse_*_line 等价（process_worker 通路）
# ---------------------------------------------------------------------------

def test_build_parsed_access_matches_parse_access_line():
    build_access, _ = _new_helpers()
    parts = ACCESS_LINE.split("|")
    assert build_access(parts, len(parts)) == LogParser.parse_access_line(ACCESS_LINE)


def test_build_parsed_run_matches_parse_run_line():
    _, build_run = _new_helpers()
    parts = RUN_LINE.split("|")
    assert build_run(parts, len(parts)) == LogParser.parse_run_line(RUN_LINE)


def test_build_parsed_run_pads_missing_msg():
    """process_worker 仅对 plen>=8 调 run builder，但缺失列契约仍须 pad 空串。"""
    _, build_run = _new_helpers()
    parts = RUN_LINE.split("|")
    assert build_run(parts, 7)["msg"] == ""


# ---------------------------------------------------------------------------
# 3. parse_timestamp：fromisoformat(replace 空格→T) 与旧手动切片等价
# ---------------------------------------------------------------------------

def _old_manual_parse_timestamp(ts: str) -> datetime:
    """T1 之前的 parse_timestamp 手动切片实现（仅用于 parity 对比）。"""
    return datetime(
        int(ts[0:4]), int(ts[5:7]), int(ts[8:10]),
        int(ts[11:13]), int(ts[14:16]), int(ts[17:19]),
        int(ts[20:26]) if len(ts) > 20 else 0,
    )


@pytest.mark.parametrize("ts", [
    "2026-05-10T12:47:24.934807",   # T 分隔 + 6 位微秒（实际日志格式）
    "2026-05-10 12:47:24.934807",   # 空格分隔（3.10 崩溃场景）
    "2026-05-10T12:47:24",          # T 分隔、无微秒
    "2026-05-10 12:47:24",          # 空格分隔、无微秒
])
def test_parse_timestamp_equivalent_to_manual_slice(ts):
    assert parse_timestamp(ts) == _old_manual_parse_timestamp(ts)


# ---------------------------------------------------------------------------
# 4. Python 3.10 兼容：replace 必须先于 fromisoformat
# ---------------------------------------------------------------------------

def test_parse_timestamp_replaces_space_before_fromisoformat(monkeypatch):
    """3.10 的 fromisoformat 拒绝空格分隔（3.11+ 才接受）。

    用子类模拟 3.10 行为：若收到含空格的串直接抛 ValueError。
    只有 replace(" ", "T", 1) 先执行，本测试才通过。
    """
    import latency.common.ds_log_io as ds_log_io

    seen: list[str] = []

    class Py310Datetime(datetime):
        @classmethod
        def fromisoformat(cls, s: str) -> datetime:
            seen.append(s)
            if " " in s:
                raise ValueError(f"Invalid isoformat string: {s!r}")
            return super().fromisoformat(s)

    monkeypatch.setattr(ds_log_io, "datetime", Py310Datetime)

    assert parse_timestamp("2026-05-10 12:47:24.934807") == datetime(
        2026, 5, 10, 12, 47, 24, 934807
    )
    assert seen == ["2026-05-10T12:47:24.934807"], (
        "fromisoformat 必须收到 replace 后的 T 分隔串"
    )


# ---------------------------------------------------------------------------
# 5. _pre_parsed 通路：预解析 dict 与直接 parse 结果一致
# ---------------------------------------------------------------------------

def test_pre_parsed_access_pathway_sdk():
    from latency.parse.sdk_access_log_parser import SdkAccessLogParser

    build_access, _ = _new_helpers()

    p1 = SdkAccessLogParser()
    e1 = p1.match_line(ACCESS_LINE, "10.0.0.9")

    p2 = SdkAccessLogParser()
    p2._pre_parsed = build_access(ACCESS_LINE.split("|"), len(ACCESS_LINE.split("|")))
    try:
        e2 = p2.match_line(ACCESS_LINE, "10.0.0.9")
    finally:
        p2._pre_parsed = None

    assert e1 is not None
    assert e2 == e1


def test_pre_parsed_access_pathway_worker():
    from latency.parse.worker_access_log_parser import WorkerAccessLogParser

    build_access, _ = _new_helpers()

    p1 = WorkerAccessLogParser()
    e1 = p1.match_line(WORKER_ACCESS_LINE, "10.0.0.9")

    p2 = WorkerAccessLogParser()
    p2._pre_parsed = build_access(
        WORKER_ACCESS_LINE.split("|"), len(WORKER_ACCESS_LINE.split("|"))
    )
    try:
        e2 = p2.match_line(WORKER_ACCESS_LINE, "10.0.0.9")
    finally:
        p2._pre_parsed = None

    assert e1 is not None
    assert e2 == e1
