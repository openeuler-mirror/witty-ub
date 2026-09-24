# Copyright (c) Huawei Technologies Co., Ltd. 2023-2026. All rights reserved.
"""parse/ 顶层 8 个日志解析器单元测试（纯逻辑直测）。

覆盖模块：
  - urma_log_parser / link_log_parser / query_meta_log_parser /
    remote_pull_log_parser：Run 格式单关键字解析器
  - sdk_access_log_parser / worker_access_log_parser：Access 格式解析器
  - worker_info_parser：合并解析器（多 label 路由 + scan_scope + scan_file）
  - brpc_profiling_parser：UBSocket profiling 文本解析器

每个解析器至少覆盖：正常匹配行、关键词不匹配、正则不匹配、
时间过滤剔除、空/畸形输入。所有用例均为纯逻辑直测，
文件类用例仅使用 pytest tmp_path 临时目录。
"""
from datetime import datetime

import pytest

from latency.ENUM.ds_log import EntryType
from latency.parse.brpc_profiling_parser import BrpcProfilingParser
from latency.parse.link_log_parser import LinkLogParser
from latency.parse.query_meta_log_parser import QueryMetaLogParser
from latency.parse.remote_pull_log_parser import RemotePullLogParser
from latency.parse.sdk_access_log_parser import SdkAccessLogParser
from latency.parse.urma_log_parser import UrmaLogParser
from latency.parse.worker_access_log_parser import WorkerAccessLogParser
from latency.parse.worker_info_parser import (
    ClientInfoParser,
    WorkerInfoParser,
    URMA_LABEL,
    REMOTE_PULL_LABEL,
    LINK_LABEL,
    QUERY_META_LABEL,
    SDK_PROCESS_LABEL,
    SDK_RPC_LABEL,
    LOCAL_WORKER_COST_LABEL,
    LOCAL_WORKER_LOCK_LABEL,
    REMOTE_WORKER_COST_LABEL,
    REMOTE_WORKER_RPC_LABEL,
    MASTER_PROCESS_LABEL,
    MASTER_RPC_LABEL,
    CLIENT_RPC_LABEL,
)
from latency.parse.parallel_scanner.spill import SpillError
from latency.schemas.parse_config import ParseConfig

# ---------------------------------------------------------------------------
# 行构造 helper（格式见 base_parser.RunCol / AccessCol 的 docstring）
# ---------------------------------------------------------------------------


def run_line(
    msg: str,
    ts: str = "2026-05-13T00:03:42.487820",
    trace: str = "trace-1",
    pod: str = "pod-w1",
    cluster: str = "clusterA",
) -> str:
    """构造 Run 格式行：ts|I|file|pod|pid:tid|trace|cluster|msg"""
    return " | ".join([ts, "I", "worker_impl.cpp:100", pod, "112:409", trace, cluster, msg])


def access_line(
    handle: str = "DS_KV_CLIENT_GET",
    elapsed: str = "773",
    trace: str = "trace-sdk-1",
    pod: str = "sdk-pod-1",
    ts: str = "2026-05-11T05:25:20.207278",
    cluster: str = "",
    status: str = "0",
    size: str = "8395125",
    req: str = "{Object_key:key-sdk-1,timeout:0}",
    resp: str = "resp-msg",
) -> str:
    """构造 Access 格式行（13 列）"""
    return " | ".join([
        ts, "I", "access_recorder.cpp:220", pod, "3941:3970",
        trace, cluster, status, handle, elapsed, size, req, resp,
    ])


def worker_access_line(
    handle: str = "DS_POSIX_GET",
    elapsed: str = "417",
    trace: str = "trace-worker-1",
    pod: str = "worker-pod-1",
    ts: str = "2026-05-11T05:25:21.087136",
) -> str:
    return access_line(
        handle=handle, elapsed=elapsed, trace=trace, pod=pod, ts=ts,
        req="{Object_key:key-worker-1,timeout:0}",
    )


# 常用消息样例（格式来自 regex/kvcache_log.py 与真实日志样例）
URMA_MSG = (
    "[URMA_ELAPSED_TOTAL]: Waiting URMA jfc event done after "
    "urma_post_jetty_send_wr cost 1.27262ms, request id:2052374, "
    "src address:6.62.223.31:31501, target address:6.62.222.250:31501, "
    "dataSize:8395125, cpuid:2, status: code: [OK], msg: [DS_KV_CLIENT_GET], "
    "urma_inflight_wr_count: 1"
)
CREATE_META_MSG = "Processing CreateMetaReq, id=1 src=10.0.0.1:9000, dst=10.0.0.2:9000"
REMOTE_GET_MSG = "Remote get request: src=1.1.1.1, dst=2.2.2.2]"
REMOTE_PULL_MSG = "Processing pull object[key1] src=3.3.3.3, dst=4.4.4.4]"
LINK_OK_MSG = "WorkerWorkerExchangeUrmaConnectInfo finish, elapsed ms: 42.5, status=code: [OK]"
LINK_TRANSPORT_MSG = "Worker-worker transport connection exchange success, elapsed ms: 7"
QUERY_META_MSG = "Master query done, cost: 15.5ms"
ZMQ_SLOW_MSG = (
    "[ZMQ_RPC_FRAMEWORK_SLOW] trace_id=t1 framework_us=1 e2e_us=2 "
    "client_req_framework_us=3 remote_processing_us=4 client_rsp_framework_us=5 "
    "server_req_queue_us=6 server_exec_us=7 server_rsp_queue_us=8 "
    "network_residual_us=9"
)

# 细分耗时（timed）日志样例：msg -> (entry_type, 期望 elapsed_us)
TIMED_CASES = [
    ("[Get] Done, clientId: c1, objects: 3, transferPath: p1, "
     "totalCost: 12.5ms, inflightRemoteGet: 2 exceed 10ms: {a: 1}",
     EntryType.SDK_PROCESS, 12500.0),
    ("Worker to master rpc QueryMeta: 45.6 ms", EntryType.SDK_RPC, 45600.0),
    ("ProcessGetObjectRequest: 3.2 ms", EntryType.LOCAL_WORKER_COST, 3200.0),
    ("worker SafeObject WLock: 1.1 ms", EntryType.LOCAL_WORKER_LOCK, 1100.0),
    ("[Get/RemotePull] finish, count: 2, firstObjectKey: key-1, payload size: 1024, "
     "start remainingTime: 100ms, cost: 9.9ms, src = 1.1.1.1, dst = 2.2.2.2",
     EntryType.REMOTE_WORKER_COST, 9900.0),
    ("[Get] Remote done, count: 1, path: p9, cost: 5.5ms, src = 3.3.3.3, dst = 4.4.4.4",
     EntryType.REMOTE_WORKER_RPC, 5500.0),
    ("QueryMeta done, target num 4, success num 3, cost: 6.6ms",
     EntryType.MASTER_PROCESS, 6600.0),
]


# ---------------------------------------------------------------------------
# UrmaLogParser
# ---------------------------------------------------------------------------


class TestUrmaLogParser:
    def test_valid_line(self):
        parser = UrmaLogParser()
        entry = parser.match_line(run_line(URMA_MSG), "10.0.0.9")
        assert entry is not None
        assert entry.entry_type == EntryType.URMA
        assert entry.elapsed_us == pytest.approx(1272.62)
        assert entry.src_addr == "6.62.223.31:31501"
        assert entry.dst_addr == "6.62.222.250:31501"
        assert entry.inflight_count == 1
        assert entry.pod_ip == "pod-w1"
        assert entry.trace_id == "trace-1"
        assert entry.cluster_name == "clusterA"

    def test_pod_and_cluster_fallback(self):
        parser = UrmaLogParser()
        entry = parser.match_line(run_line(URMA_MSG, pod="", cluster=""), "10.0.0.9")
        assert entry.pod_ip == "10.0.0.9"
        assert entry.cluster_name is None

    def test_keyword_missing(self):
        parser = UrmaLogParser()
        assert parser.match_line(run_line("plain message"), "10.0.0.9") is None
        assert parser.match_line("", "10.0.0.9") is None

    def test_malformed_line(self):
        parser = UrmaLogParser()
        # 不以 2 开头 / 段数不足
        assert parser.match_line("URMA_ELAPSED_TOTAL but not log format", "10.0.0.9") is None
        assert parser.match_line("2|a|b|c|URMA_ELAPSED_TOTAL", "10.0.0.9") is None

    def test_regex_not_matched(self):
        parser = UrmaLogParser()
        assert parser.match_line(run_line("[URMA_ELAPSED_TOTAL] no numbers here"), "10.0.0.9") is None

    def test_time_filter(self):
        parser = UrmaLogParser(ParseConfig(start_time="2026-05-14 00:00:00"))
        assert parser.match_line(run_line(URMA_MSG), "10.0.0.9") is None
        assert parser._filtered_by_time == 1

    def test_time_filter_end(self):
        parser = UrmaLogParser(ParseConfig(end_time="2026-05-12 00:00:00"))
        assert parser.match_line(run_line(URMA_MSG), "10.0.0.9") is None

    def test_patterns(self):
        assert isinstance(UrmaLogParser().patterns, list)


# ---------------------------------------------------------------------------
# LinkLogParser
# ---------------------------------------------------------------------------


class TestLinkLogParser:
    def test_valid_exchange_finish(self):
        parser = LinkLogParser()
        entry = parser.match_line(run_line(LINK_OK_MSG), "10.0.0.9")
        assert entry is not None
        assert entry.entry_type == EntryType.LINK
        assert entry.elapsed_us == pytest.approx(42500.0)
        assert entry.trace_id == "trace-1"

    def test_valid_transport_success(self):
        parser = LinkLogParser()
        entry = parser.match_line(run_line(LINK_TRANSPORT_MSG), "10.0.0.9")
        assert entry is not None
        assert entry.elapsed_us == pytest.approx(7000.0)

    def test_keyword_missing(self):
        parser = LinkLogParser()
        assert parser.match_line(run_line("no keyword at all"), "10.0.0.9") is None
        assert parser.match_line("", "10.0.0.9") is None

    def test_elapsed_keyword_without_exchange(self):
        parser = LinkLogParser()
        assert parser.match_line(run_line("something elapsed ms: 5, no exchange"), "10.0.0.9") is None

    def test_finish_without_ok_status(self):
        parser = LinkLogParser()
        line = run_line("WorkerWorkerExchangeUrmaConnectInfo finish, elapsed ms: 42.5")
        assert parser.match_line(line, "10.0.0.9") is None

    def test_regex_not_matched(self):
        parser = LinkLogParser()
        line = run_line("Worker-worker transport connection exchange success, elapsed ms: ab")
        assert parser.match_line(line, "10.0.0.9") is None

    def test_malformed_line(self):
        parser = LinkLogParser()
        assert parser.match_line("2|a|b|c|elapsed ms: 5", "10.0.0.9") is None

    def test_time_filter(self):
        parser = LinkLogParser(ParseConfig(start_time="2026-05-14 00:00:00"))
        assert parser.match_line(run_line(LINK_OK_MSG), "10.0.0.9") is None
        assert parser._filtered_by_time == 1

    def test_pod_fallback(self):
        parser = LinkLogParser()
        entry = parser.match_line(run_line(LINK_OK_MSG, pod="", cluster=""), "10.0.0.9")
        assert entry.pod_ip == "10.0.0.9"
        assert entry.cluster_name is None


# ---------------------------------------------------------------------------
# QueryMetaLogParser
# ---------------------------------------------------------------------------


class TestQueryMetaLogParser:
    def test_valid_line(self):
        parser = QueryMetaLogParser()
        entry = parser.match_line(run_line(QUERY_META_MSG), "10.0.0.9")
        assert entry is not None
        assert entry.entry_type == EntryType.QUERY_META
        assert entry.elapsed_us == pytest.approx(15500.0)
        assert entry.trace_id == "trace-1"
        assert entry.pod_ip == "pod-w1"

    def test_keyword_missing(self):
        parser = QueryMetaLogParser()
        assert parser.match_line(run_line("other message cost: 1ms"), "10.0.0.9") is None
        assert parser.match_line("", "10.0.0.9") is None

    def test_malformed_line(self):
        parser = QueryMetaLogParser()
        assert parser.match_line("2|a|b|c|Master query done", "10.0.0.9") is None
        assert parser.match_line("Master query done but not log", "10.0.0.9") is None

    def test_time_filter(self):
        parser = QueryMetaLogParser(ParseConfig(start_time="2026-05-14 00:00:00"))
        assert parser.match_line(run_line(QUERY_META_MSG), "10.0.0.9") is None
        assert parser._filtered_by_time == 1

    def test_no_trace_id(self):
        parser = QueryMetaLogParser()
        assert parser.match_line(run_line(QUERY_META_MSG, trace=""), "10.0.0.9") is None

    def test_regex_not_matched(self):
        parser = QueryMetaLogParser()
        assert parser.match_line(run_line("Master query done, no cost field"), "10.0.0.9") is None


# ---------------------------------------------------------------------------
# RemotePullLogParser
# ---------------------------------------------------------------------------


class TestRemotePullLogParser:
    def test_remote_get_valid(self):
        parser = RemotePullLogParser()
        entry = parser.match_line(run_line(REMOTE_GET_MSG), "10.0.0.9")
        assert entry is not None
        assert entry.entry_type == EntryType.REMOTE_PULL
        assert entry.elapsed_us == 0
        assert entry.src_addr == "1.1.1.1"
        assert entry.dst_addr == "2.2.2.2"
        assert entry.trace_id == "trace-1"

    def test_remote_pull_valid(self):
        parser = RemotePullLogParser()
        entry = parser.match_line(run_line(REMOTE_PULL_MSG), "10.0.0.9")
        assert entry is not None
        assert entry.src_addr == "3.3.3.3"
        assert entry.dst_addr == "4.4.4.4"

    def test_keyword_missing(self):
        parser = RemotePullLogParser()
        assert parser.match_line(run_line("nothing here"), "10.0.0.9") is None
        assert parser.match_line("", "10.0.0.9") is None

    @pytest.mark.parametrize("msg", [REMOTE_GET_MSG, REMOTE_PULL_MSG])
    def test_malformed_line(self, msg):
        parser = RemotePullLogParser()
        assert parser.match_line("2|a|b|c|" + msg, "10.0.0.9") is None

    @pytest.mark.parametrize("msg", [REMOTE_GET_MSG, REMOTE_PULL_MSG])
    def test_time_filter(self, msg):
        parser = RemotePullLogParser(ParseConfig(start_time="2026-05-14 00:00:00"))
        assert parser.match_line(run_line(msg), "10.0.0.9") is None
        assert parser._filtered_by_time == 1

    @pytest.mark.parametrize("msg", [REMOTE_GET_MSG, REMOTE_PULL_MSG])
    def test_no_trace_id(self, msg):
        parser = RemotePullLogParser()
        assert parser.match_line(run_line(msg, trace=""), "10.0.0.9") is None

    @pytest.mark.parametrize(
        "msg",
        ["Remote get request: no addresses", "Processing pull object[k] no addresses"],
    )
    def test_regex_not_matched(self, msg):
        parser = RemotePullLogParser()
        assert parser.match_line(run_line(msg), "10.0.0.9") is None

    def test_pod_fallback(self):
        parser = RemotePullLogParser()
        entry = parser.match_line(run_line(REMOTE_GET_MSG, pod="", cluster=""), "10.0.0.9")
        assert entry.pod_ip == "10.0.0.9"
        assert entry.cluster_name is None


# ---------------------------------------------------------------------------
# SdkAccessLogParser
# ---------------------------------------------------------------------------


class TestSdkAccessLogParser:
    def test_valid_get(self):
        parser = SdkAccessLogParser()
        entry = parser.match_line(access_line(), "10.0.0.9")
        assert entry is not None
        assert entry.entry_type == EntryType.SDK_GET
        assert entry.operation == "DS_KV_CLIENT_GET"
        assert entry.elapsed_us == 773
        assert entry.data_size == "8395125"
        assert entry.object_key == "key-sdk-1"
        assert entry.status_code == 0
        assert entry.resp_msg == "resp-msg"
        assert entry.pod_ip == "sdk-pod-1"

    def test_valid_set(self):
        parser = SdkAccessLogParser()
        entry = parser.match_line(access_line(handle="DS_KV_CLIENT_SET"), "10.0.0.9")
        assert entry is not None
        assert entry.entry_type == EntryType.SDK_SET

    def test_wrong_handle(self):
        parser = SdkAccessLogParser()
        assert parser.match_line(access_line(handle="DS_POSIX_GET"), "10.0.0.9") is None

    def test_malformed_line(self):
        parser = SdkAccessLogParser()
        assert parser.match_line("", "10.0.0.9") is None
        assert parser.match_line("2|x" * 5, "10.0.0.9") is None

    def test_elapsed_not_int(self):
        parser = SdkAccessLogParser()
        assert parser.match_line(access_line(elapsed="abc"), "10.0.0.9") is None

    def test_min_elapsed_filter(self):
        parser = SdkAccessLogParser(ParseConfig(min_elapsed_ms=1))
        # 773us < 1000us 被剔除，2000us 保留
        assert parser.match_line(access_line(elapsed="773"), "10.0.0.9") is None
        assert parser._filtered_by_elapsed == 1
        assert parser.match_line(access_line(elapsed="2000"), "10.0.0.9") is not None

    def test_no_trace_id(self):
        parser = SdkAccessLogParser()
        line = access_line(trace="", req="{}", resp="")
        assert parser.match_line(line, "10.0.0.9") is None

    def test_time_filter(self):
        parser = SdkAccessLogParser(ParseConfig(start_time="2026-05-11 06:00:00"))
        assert parser.match_line(access_line(), "10.0.0.9") is None
        assert parser._filtered_by_time == 1

    def test_parse_config_init(self):
        parser = SdkAccessLogParser(
            ParseConfig(start_time="2026-05-11 05:00:00", end_time="2026-05-11 06:00:00")
        )
        assert parser.start_time == datetime(2026, 5, 11, 5, 0, 0)
        assert parser.end_time == datetime(2026, 5, 11, 6, 0, 0)
        assert parser.min_elapsed_us is None

    def test_legacy_positional_init(self):
        # 旧调用形式：SdkAccessLogParser(start_time, end_time, min_total_time_ms)
        parser = SdkAccessLogParser(
            datetime(2026, 5, 11, 5, 0, 0), datetime(2026, 5, 11, 6, 0, 0), 5.0
        )
        assert parser.start_time == datetime(2026, 5, 11, 5, 0, 0)
        assert parser.end_time == datetime(2026, 5, 11, 6, 0, 0)
        assert parser.min_elapsed_us == pytest.approx(5000.0)

    def test_extract_pod_ip(self):
        parser = SdkAccessLogParser()
        assert parser.extract_pod_ip("/data/SDK_pod-9/ds_client.log") == "pod-9"

    def test_parse_directory(self, tmp_path):
        log_dir = tmp_path / "SDK_pod-9"
        log_dir.mkdir()
        log_dir.joinpath("access.log").write_text(
            access_line(elapsed="2000") + "\n"          # 命中
            + access_line(elapsed="773") + "\n"         # 低于 min_elapsed → 剔除
            + access_line(elapsed="2000", ts="2026-05-11T07:25:20") + "\n",  # 超出时间窗
            encoding="utf-8",
        )
        parser = SdkAccessLogParser(
            ParseConfig(start_time="2026-05-11 05:00:00", end_time="2026-05-11 06:00:00",
                        min_elapsed_ms=1)
        )
        parser._runtime_patterns = ["access.log"]
        entries = parser.parse(str(tmp_path))
        assert len(entries) == 1
        assert entries[0].entry_type == EntryType.SDK_GET
        assert entries[0].pod_ip == "sdk-pod-1"
        assert parser._filtered_by_elapsed == 1
        assert parser._filtered_by_time == 1


# ---------------------------------------------------------------------------
# WorkerAccessLogParser
# ---------------------------------------------------------------------------


class TestWorkerAccessLogParser:
    def test_valid_get(self):
        parser = WorkerAccessLogParser()
        entry = parser.match_line(worker_access_line(), "10.0.0.9")
        assert entry is not None
        assert entry.entry_type == EntryType.WORKER_GET
        assert entry.operation == "DS_POSIX_GET"
        assert entry.elapsed_us == 417
        assert entry.object_key == "key-worker-1"
        assert entry.pod_ip == "worker-pod-1"

    def test_valid_create_and_publish(self):
        parser = WorkerAccessLogParser()
        create = parser.match_line(worker_access_line(handle="DS_POSIX_CREATE"), "10.0.0.9")
        publish = parser.match_line(worker_access_line(handle="DS_POSIX_PUBLISH"), "10.0.0.9")
        assert create.entry_type == EntryType.WORKER_CREATE
        assert publish.entry_type == EntryType.WORKER_PUBLISH

    def test_wrong_handle(self):
        parser = WorkerAccessLogParser()
        assert parser.match_line(access_line(handle="DS_KV_CLIENT_GET"), "10.0.0.9") is None

    def test_malformed_line(self):
        parser = WorkerAccessLogParser()
        assert parser.match_line("", "10.0.0.9") is None
        assert parser.match_line("2|x" * 5, "10.0.0.9") is None

    def test_no_trace_id(self):
        parser = WorkerAccessLogParser()
        line = worker_access_line(trace="")
        line = line.replace("{Object_key:key-worker-1,timeout:0}", "{}")
        assert parser.match_line(line, "10.0.0.9") is None

    def test_elapsed_not_int(self):
        parser = WorkerAccessLogParser()
        assert parser.match_line(worker_access_line(elapsed="abc"), "10.0.0.9") is None

    def test_time_filter(self):
        parser = WorkerAccessLogParser(ParseConfig(start_time="2026-05-11 06:00:00"))
        assert parser.match_line(worker_access_line(), "10.0.0.9") is None
        assert parser._filtered_by_time == 1

    def test_parse_config_init(self):
        parser = WorkerAccessLogParser(
            ParseConfig(start_time="2026-05-11 05:00:00", end_time="2026-05-11 06:00:00")
        )
        assert parser.start_time == datetime(2026, 5, 11, 5, 0, 0)
        assert parser.end_time == datetime(2026, 5, 11, 6, 0, 0)

    def test_legacy_positional_init(self):
        # 旧调用形式：WorkerAccessLogParser(start_time, end_time)
        parser = WorkerAccessLogParser(datetime(2026, 5, 11, 5, 0, 0), datetime(2026, 5, 11, 6, 0, 0))
        assert parser.start_time == datetime(2026, 5, 11, 5, 0, 0)
        assert parser.end_time == datetime(2026, 5, 11, 6, 0, 0)

    def test_set_scan_scope_filters_trace(self):
        parser = WorkerAccessLogParser()
        parser.set_scan_scope({"enabled": True, "trace_ids": {"trace-worker-1"}})
        assert parser.match_line(worker_access_line(), "10.0.0.9") is not None
        assert parser.match_line(worker_access_line(trace="trace-other"), "10.0.0.9") is None
        # 列表输入会被转成 set
        parser.set_scan_scope({"enabled": True, "trace_ids": ["trace-worker-1"]})
        assert parser.match_line(worker_access_line(), "10.0.0.9") is not None
        # 传 None 关闭过滤
        parser.set_scan_scope(None)
        assert parser.match_line(worker_access_line(trace="trace-any"), "10.0.0.9") is not None

    def test_parse_directory(self, tmp_path):
        log_dir = tmp_path / "worker_a"
        log_dir.mkdir()
        log_dir.joinpath("access.log").write_text(
            worker_access_line() + "\n"
            + worker_access_line(handle="DS_POSIX_CREATE") + "\n"
            + worker_access_line(handle="DS_POSIX_PUBLISH") + "\n"
            + worker_access_line(ts="2026-05-11T07:25:21") + "\n",  # 超出时间窗
            encoding="utf-8",
        )
        parser = WorkerAccessLogParser(
            ParseConfig(start_time="2026-05-11 05:00:00", end_time="2026-05-11 06:00:00")
        )
        parser._runtime_patterns = ["access.log"]
        entries = parser.parse(str(tmp_path))
        assert len(entries) == 3
        assert {e.entry_type for e in entries} == {
            EntryType.WORKER_GET, EntryType.WORKER_CREATE, EntryType.WORKER_PUBLISH,
        }
        assert parser._filtered_by_time == 1


# ---------------------------------------------------------------------------
# WorkerInfoParser：match_line 各 label 路由
# ---------------------------------------------------------------------------


class TestWorkerInfoMatchLine:
    def test_urma(self):
        parser = WorkerInfoParser()
        entries = parser.match_line(run_line(URMA_MSG), "10.0.0.9")
        assert entries and len(entries) == 1
        e = entries[0]
        assert e.entry_type == EntryType.URMA
        assert e.elapsed_us == pytest.approx(1272.62)
        assert e.src_addr == "6.62.223.31:31501"
        assert e.dst_addr == "6.62.222.250:31501"
        assert e.inflight_count == 1

    def test_urma_create_meta_req(self):
        parser = WorkerInfoParser()
        entries = parser.match_line(run_line(CREATE_META_MSG), "10.0.0.9")
        assert entries
        e = entries[0]
        assert e.entry_type == EntryType.URMA
        assert e.elapsed_us == 0
        assert e.src_addr == "10.0.0.1"
        assert e.dst_addr == "10.0.0.2"
        assert e.inflight_count == 0

    def test_remote_get(self):
        parser = WorkerInfoParser()
        entries = parser.match_line(run_line(REMOTE_GET_MSG), "10.0.0.9")
        assert entries
        e = entries[0]
        assert e.entry_type == EntryType.REMOTE_PULL
        assert e.src_addr == "1.1.1.1"
        assert e.dst_addr == "2.2.2.2"

    def test_remote_pull(self):
        parser = WorkerInfoParser()
        entries = parser.match_line(run_line(REMOTE_PULL_MSG), "10.0.0.9")
        assert entries
        assert entries[0].src_addr == "3.3.3.3"
        assert entries[0].dst_addr == "4.4.4.4"

    def test_link(self):
        parser = WorkerInfoParser()
        entries = parser.match_line(run_line(LINK_OK_MSG), "10.0.0.9")
        assert entries
        assert entries[0].entry_type == EntryType.LINK
        assert entries[0].elapsed_us == pytest.approx(42500.0)

    def test_link_without_ok_status(self):
        parser = WorkerInfoParser()
        line = run_line("WorkerWorkerExchangeUrmaConnectInfo finish, elapsed ms: 42.5")
        assert parser.match_line(line, "10.0.0.9") is None

    def test_query_meta(self):
        parser = WorkerInfoParser()
        entries = parser.match_line(run_line(QUERY_META_MSG), "10.0.0.9")
        assert entries
        assert entries[0].entry_type == EntryType.QUERY_META
        assert entries[0].elapsed_us == pytest.approx(15500.0)

    @pytest.mark.parametrize("msg,entry_type,elapsed_us", TIMED_CASES)
    def test_timed_entries(self, msg, entry_type, elapsed_us):
        parser = WorkerInfoParser()
        entries = parser.match_line(run_line(msg), "10.0.0.9")
        assert entries, f"timed 行未命中: {msg}"
        e = entries[0]
        assert e.entry_type == entry_type
        assert e.elapsed_us == pytest.approx(elapsed_us)
        assert e.trace_id == "trace-1"

    def test_sdk_process_full_fields(self):
        parser = WorkerInfoParser()
        msg = TIMED_CASES[0][0]
        e = parser.match_line(run_line(msg), "10.0.0.9")[0]
        assert e.inflight_count == 2
        assert "client_id=c1" in e.resp_msg
        assert "transfer_path=p1" in e.resp_msg

    def test_remote_worker_cost_full_fields(self):
        parser = WorkerInfoParser()
        msg = TIMED_CASES[4][0]
        e = parser.match_line(run_line(msg), "10.0.0.9")[0]
        assert e.object_key == "key-1"
        assert e.request_size == "1024"
        assert e.src_addr == "1.1.1.1"
        assert e.dst_addr == "2.2.2.2"
        assert e.resp_msg == ("count=2, first_object_key=key-1, "
                              "payload_size=1024, start_remaining_time=100ms")

    def test_remote_worker_rpc_resp_msg(self):
        parser = WorkerInfoParser()
        msg = TIMED_CASES[5][0]
        e = parser.match_line(run_line(msg), "10.0.0.9")[0]
        assert e.resp_msg == "count=1, path=p9"

    def test_master_rpc(self):
        parser = WorkerInfoParser()
        # 显式 trace_id=t1 覆盖格式列 trace；multiplier=1 → 取 remote_processing_us
        entries = parser.match_line(run_line(ZMQ_SLOW_MSG, trace="trace-col-1"), "10.0.0.9")
        assert entries
        e = entries[0]
        assert e.entry_type == EntryType.MASTER_RPC
        assert e.elapsed_us == 4.0
        assert e.trace_id == "t1"
        assert "rpc_trace_id=t1" in e.resp_msg
        assert "network_residual_us=9" in e.resp_msg

    def test_src_dst_fallback(self):
        parser = WorkerInfoParser()
        msg = "handshake done, src 6.62.223.31:31501, dst 6.62.222.250:31501, ok"
        entries = parser.match_line(run_line(msg), "10.0.0.9")
        assert entries
        e = entries[0]
        assert e.entry_type == EntryType.REMOTE_PULL
        assert e.src_addr == "6.62.223.31:31501"
        assert e.dst_addr == "6.62.222.250:31501"
        assert e.resp_msg == msg

    def test_src_dst_fallback_non_ip_rejected(self):
        parser = WorkerInfoParser()
        line = run_line("handshake done, src abc, dst def, ok")
        assert parser.match_line(line, "10.0.0.9") is None

    # ---- 负例：关键词 / 格式 / 时间过滤 ----

    def test_reject_non_log_line(self):
        parser = WorkerInfoParser()
        assert parser.match_line("garbage", "10.0.0.9") is None
        assert parser.match_line("", "10.0.0.9") is None

    def test_reject_no_keyword(self):
        parser = WorkerInfoParser()
        assert parser.match_line(run_line("plain run message"), "10.0.0.9") is None

    def test_reject_short_line(self):
        parser = WorkerInfoParser()
        assert parser.match_line("2|a|b|c|Remote get request", "10.0.0.9") is None

    def test_reject_by_time_filter(self):
        parser = WorkerInfoParser(ParseConfig(start_time="2026-05-14 00:00:00"))
        assert parser.match_line(run_line(URMA_MSG), "10.0.0.9") is None
        assert parser._filtered_by_time == 1

    def test_keyword_without_pattern_returns_none(self):
        parser = WorkerInfoParser()
        # 关键词命中但正则不匹配 / 缺 trace / 缺正则
        assert parser.match_line(run_line("[URMA_ELAPSED_TOTAL] no numbers"), "10.0.0.9") is None
        assert parser.match_line(run_line(REMOTE_GET_MSG, trace=""), "10.0.0.9") is None
        assert parser.match_line(run_line("Remote get request: no addresses"), "10.0.0.9") is None
        assert parser.match_line(run_line("totalCost: 5"), "10.0.0.9") is None
        assert parser.match_line(run_line("totalCost: 5ms", trace=""), "10.0.0.9") is None
        # src/dst 都在但无端点正则命中
        assert parser.match_line(run_line("has src and dst words only"), "10.0.0.9") is None


# ---------------------------------------------------------------------------
# WorkerInfoParser：静态/类辅助方法
# ---------------------------------------------------------------------------


class _FakeMatch:
    """替身 match 对象，供 _elapsed_value_from_match 直测。"""

    def __init__(self, *groups):
        self._groups = groups

    def groups(self):
        return self._groups


class TestWorkerInfoHelpers:
    def test_elapsed_value_prefers_named_groups(self):
        assert WorkerInfoParser._elapsed_value_from_match(
            _FakeMatch(), {"remote_processing_us": "7"}) == "7"
        assert WorkerInfoParser._elapsed_value_from_match(
            _FakeMatch("9.9"), {"cost": "9.9"}) == "9.9"

    def test_elapsed_value_fallback_to_numeric_group(self):
        m = _FakeMatch("abc", "1.5", None)
        assert WorkerInfoParser._elapsed_value_from_match(m, {"cost": None}) == "1.5"

    def test_elapsed_value_none_when_no_numeric(self):
        assert WorkerInfoParser._elapsed_value_from_match(
            _FakeMatch("x"), {"cost": None}) is None

    def test_timed_fields_endpoint_fallback(self):
        fields = WorkerInfoParser._timed_fields_from_groups(
            "tail: src 1.1.1.1:1, dst 2.2.2.2:2",
            {"src": None, "dst": "  ", "first_object_key": " key-1 ",
             "payload_size": None, "inflight_remote_get": "3"},
        )
        assert fields["src_addr"] == "1.1.1.1:1"
        assert fields["dst_addr"] == "2.2.2.2:2"
        assert fields["object_key"] == "key-1"
        assert fields["request_size"] is None
        assert fields["inflight_count"] == 3

    def test_clean_group(self):
        assert WorkerInfoParser._clean_group(None) is None
        assert WorkerInfoParser._clean_group("   ") is None
        assert WorkerInfoParser._clean_group(" x ") == "x"

    def test_optional_int(self):
        assert WorkerInfoParser._optional_int(None) is None
        assert WorkerInfoParser._optional_int("  ") is None
        assert WorkerInfoParser._optional_int("abc") is None
        assert WorkerInfoParser._optional_int("3") == 3

    def test_format_timed_resp_msg(self):
        # 全部被排除/为空 → None
        assert WorkerInfoParser._format_timed_resp_msg({"cost": "1", "src": "a"}) is None
        assert WorkerInfoParser._format_timed_resp_msg({}) is None
        result = WorkerInfoParser._format_timed_resp_msg(
            {"cost": "1", "client_id": "c1", "objects": "  "})
        assert result == "client_id=c1"

    def test_line_may_match(self):
        assert WorkerInfoParser._line_may_match("xx URMA_ELAPSED_TOTAL yy")
        assert WorkerInfoParser._line_may_match("has src and dst")
        assert not WorkerInfoParser._line_may_match("nothing special here")

    def test_build_run_pads_missing(self):
        parsed = WorkerInfoParser._build_run(["2026", "I", "f", "pod"], 4)
        assert parsed["msg"] == ""
        assert parsed["trace_id"] == ""
        assert parsed["cluster_name"] == ""

    def test_looks_like_ip_endpoint(self):
        assert WorkerInfoParser._looks_like_ip_endpoint("1.2.3.4:5")
        assert not WorkerInfoParser._looks_like_ip_endpoint("abc")


# ---------------------------------------------------------------------------
# WorkerInfoParser：scan_scope 过滤
# ---------------------------------------------------------------------------


def _scope_dict(trace_ids=(), pod_trace_keys=(), pod_ips=(), enabled=True):
    return {
        "enabled": enabled,
        "trace_ids": set(trace_ids),
        "pod_trace_keys": set(pod_trace_keys),
        "pod_ips": set(pod_ips),
    }


class TestWorkerInfoScope:
    def test_disabled_scope_allows_all(self):
        parser = WorkerInfoParser()
        parser.set_scan_scope(None)
        assert parser._scan_scope_enabled is False
        assert parser.match_line(run_line(URMA_MSG), "10.0.0.9")

        parser.set_scan_scope({})
        assert parser._scan_scope_enabled is False
        assert parser.match_line(run_line(URMA_MSG), "10.0.0.9")

    def test_list_inputs_converted_to_sets(self):
        parser = WorkerInfoParser()
        parser.set_scan_scope({
            "enabled": True,
            "trace_ids": ["trace-1"],
            "pod_trace_keys": [("pod-w1", "trace-1")],
            "pod_ips": ["pod-w1"],
        })
        assert isinstance(parser._target_trace_ids, set)
        assert isinstance(parser._target_pod_trace_keys, set)
        assert isinstance(parser._target_pod_ips, set)
        assert parser.match_line(run_line(URMA_MSG), "10.0.0.9")

    def test_urma_scope_by_trace(self):
        parser = WorkerInfoParser()
        parser.set_scan_scope(_scope_dict(trace_ids={"trace-1"}))
        assert parser.match_line(run_line(URMA_MSG), "10.0.0.9")
        assert parser.match_line(run_line(URMA_MSG, trace="trace-2"), "10.0.0.9") is None

    def test_urma_scope_by_pod_when_trace_empty(self):
        parser = WorkerInfoParser()
        parser.set_scan_scope(_scope_dict(pod_ips={"pod-w1"}))
        assert parser.match_line(run_line(URMA_MSG, trace=""), "10.0.0.9")
        assert parser.match_line(run_line(URMA_MSG, trace="", pod="pod-other"), "10.0.0.9") is None

    def test_urma_file_scope_rejects_unknown_pod(self):
        # trace_ids 为空且 pod 不在名单 → 文件级直接拒绝
        parser = WorkerInfoParser()
        parser.set_scan_scope(_scope_dict(pod_ips={"pod-other"}))
        assert parser.match_line(run_line(URMA_MSG), "10.0.0.9") is None

    def test_query_meta_scope_by_trace(self):
        parser = WorkerInfoParser()
        parser.set_scan_scope(_scope_dict(trace_ids={"trace-1"}))
        assert parser.match_line(run_line(QUERY_META_MSG), "10.0.0.9")
        assert parser.match_line(run_line(QUERY_META_MSG, trace="trace-2"), "10.0.0.9") is None

    def test_query_meta_scope_by_pod_trace_key(self):
        # (pod_ip, trace_id) 组合键放行；文件级需 trace_ids 非空才放行
        parser = WorkerInfoParser()
        parser.set_scan_scope(_scope_dict(
            trace_ids={"other"}, pod_trace_keys={("pod-w1", "trace-9")}))
        entries = parser.match_line(run_line(QUERY_META_MSG, trace="trace-9"), "10.0.0.9")
        assert entries

    def test_query_meta_file_scope_by_pod_ips(self):
        # trace_ids 为空时文件级按 pod_ips 判定；scope 级组合键不命中 → 拒绝
        parser = WorkerInfoParser()
        parser.set_scan_scope(_scope_dict(pod_ips={"pod-w1"}))
        assert parser.match_line(run_line(QUERY_META_MSG, trace="trace-2"), "10.0.0.9") is None

    def test_link_scope_requires_trace_ids(self):
        parser = WorkerInfoParser()
        parser.set_scan_scope(_scope_dict(trace_ids={"trace-1"}))
        assert parser.match_line(run_line(LINK_OK_MSG), "10.0.0.9")
        assert parser.match_line(run_line(LINK_OK_MSG, trace="trace-2"), "10.0.0.9") is None
        # trace_ids 为空 → 文件级拒绝
        parser.set_scan_scope(_scope_dict(pod_ips={"pod-w1"}))
        assert parser.match_line(run_line(LINK_OK_MSG), "10.0.0.9") is None

    def test_unknown_label_always_allowed(self):
        parser = WorkerInfoParser()
        parser.set_scan_scope(_scope_dict(trace_ids={"x"}))
        # CLIENT_RPC 等未列出的 label 恒放行
        assert parser._scope_allows(CLIENT_RPC_LABEL, "any", "any") is True
        assert parser._file_scope_may_allow(CLIENT_RPC_LABEL, "any") is True

    def test_scope_disabled_helpers_allow_all(self):
        parser = WorkerInfoParser()
        assert parser._scope_allows(URMA_LABEL, "x", "y") is True
        assert parser._file_scope_may_allow(URMA_LABEL, "y") is True


# ---------------------------------------------------------------------------
# WorkerInfoParser：scan_file / _scan_file
# ---------------------------------------------------------------------------


class _FakeSink:
    """entry_sink 替身：register 记录 label，append 收集条目。"""

    def __init__(self):
        self.registered = []
        self.appended = []

    def register(self, labels):
        self.registered.extend(labels)

    def append(self, label, entry):
        self.appended.append((label, entry))


def _write_info_log(tmp_path, lines, name="info.log"):
    path = tmp_path / name
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return str(path)


class TestWorkerInfoScanFile:
    def _mixed_lines(self):
        return [
            "garbage line without timestamp",              # 非 2 开头
            run_line("plain run msg, no keyword"),          # 关键词不命中
            "2|a|b|c|Remote get request",                   # 段数不足
            run_line("[URMA_ELAPSED_TOTAL] no numbers"),    # 关键词命中但正则失败
            run_line(URMA_MSG),                             # 正常 URMA
            run_line(QUERY_META_MSG, trace="trace-qm"),     # 正常 QueryMeta
        ]

    def test_scan_file_groups_by_label(self, tmp_path):
        parser = WorkerInfoParser()
        path = _write_info_log(tmp_path, self._mixed_lines())
        results = parser.scan_file(path)
        assert len(results[URMA_LABEL]) == 1
        assert len(results[QUERY_META_LABEL]) == 1
        assert results[URMA_LABEL][0].log_id is not None
        assert results[URMA_LABEL][0].entry_type == EntryType.URMA
        # 其余 label 均为空
        for label in (REMOTE_PULL_LABEL, LINK_LABEL, SDK_PROCESS_LABEL, MASTER_RPC_LABEL):
            assert results[label] == []

    def test_scan_file_time_filter(self, tmp_path):
        parser = WorkerInfoParser(ParseConfig(end_time="2026-05-12 00:00:00"))
        path = _write_info_log(tmp_path, [run_line(URMA_MSG)])
        results = parser.scan_file(path)
        assert results[URMA_LABEL] == []
        assert parser._filtered_by_time == 1

    def test_scan_file_with_entry_sink(self, tmp_path):
        parser = WorkerInfoParser()
        path = _write_info_log(tmp_path, self._mixed_lines())
        sink = _FakeSink()
        results = parser.scan_file(path, entry_sink=sink)
        # 命中条目全部进入 sink，本地 results 为空
        assert len(sink.appended) == 2
        assert {label for label, _ in sink.appended} == {URMA_LABEL, QUERY_META_LABEL}
        assert URMA_LABEL in sink.registered
        assert results[URMA_LABEL] == []

    def test_scan_file_with_line_filter(self, tmp_path):
        parser = WorkerInfoParser()
        path = _write_info_log(tmp_path, self._mixed_lines())
        results = parser.scan_file(path, line_filter=lambda f: (ln for ln in f if "URMA" in ln))
        assert len(results[URMA_LABEL]) == 1
        assert results[QUERY_META_LABEL] == []

    def test_scan_file_swallows_eof_error(self, tmp_path):
        parser = WorkerInfoParser()
        path = _write_info_log(tmp_path, [run_line(URMA_MSG)])

        def _raise_eof(f):
            raise EOFError("corrupted")

        results = parser.scan_file(path, line_filter=_raise_eof)
        assert results[URMA_LABEL] == []

    def test_scan_file_swallows_generic_error(self, tmp_path):
        parser = WorkerInfoParser()
        path = _write_info_log(tmp_path, [run_line(URMA_MSG)])

        def _raise_value(f):
            raise ValueError("bad")

        results = parser.scan_file(path, line_filter=_raise_value)
        assert results[URMA_LABEL] == []

    def test_scan_file_reraises_spill_error(self, tmp_path):
        parser = WorkerInfoParser()
        path = _write_info_log(tmp_path, [run_line(URMA_MSG)])

        def _raise_spill(f):
            raise SpillError("disk full")

        with pytest.raises(SpillError):
            parser.scan_file(path, entry_sink=_FakeSink(), line_filter=_raise_spill)

    def test_scan_file_missing_file(self, tmp_path):
        parser = WorkerInfoParser()
        results = parser.scan_file(str(tmp_path / "missing.log"))
        assert results[URMA_LABEL] == []

    def test_scan_file_pod_ip_extract_failure(self, tmp_path, monkeypatch):
        parser = WorkerInfoParser()
        monkeypatch.setattr(
            parser, "extract_pod_ip",
            lambda p: (_ for _ in ()).throw(ValueError("bad path")),
        )
        path = _write_info_log(tmp_path, [run_line(URMA_MSG, pod="")])
        results = parser.scan_file(path)
        # extract_pod_ip 失败时回退空 pod_ip，条目仍产出
        assert len(results[URMA_LABEL]) == 1
        assert results[URMA_LABEL][0].pod_ip == ""

    def test_base_scan_file_compat(self, tmp_path):
        from latency.common.ds_log_io import Progress

        parser = WorkerInfoParser()
        path = _write_info_log(tmp_path, [run_line(URMA_MSG)])
        entries = []
        progress = Progress("test-scan", 1)
        parser._scan_file(path, "10.0.0.9", "log-1", entries, progress, 1)
        assert len(entries) == 1
        assert entries[0].log_id == "log-1"

    def test_patterns(self):
        assert isinstance(WorkerInfoParser().patterns, list)


# ---------------------------------------------------------------------------
# ClientInfoParser
# ---------------------------------------------------------------------------


class TestClientInfoParser:
    def test_valid_zmq_slow_line(self):
        parser = ClientInfoParser()
        entries = parser.match_line(run_line(ZMQ_SLOW_MSG, trace="trace-col-1"), "10.0.0.9")
        assert entries and len(entries) == 1
        e = entries[0]
        assert e.entry_type == EntryType.CLIENT_RPC
        assert e.elapsed_us == 4.0
        assert e.trace_id == "t1"

    def test_non_zmq_line_rejected(self):
        parser = ClientInfoParser()
        # 即使命中其它 WorkerInfo 关键词，ClientInfo 只认 ZMQ_SLOW
        assert parser.match_line(run_line(URMA_MSG), "10.0.0.9") is None
        assert parser.match_line(run_line("plain msg"), "10.0.0.9") is None
        assert parser.match_line("", "10.0.0.9") is None

    def test_zmq_line_regex_fail(self):
        parser = ClientInfoParser()
        assert parser.match_line(run_line("[ZMQ_RPC_FRAMEWORK_SLOW] partial data"), "10.0.0.9") is None

    def test_time_filter(self):
        parser = ClientInfoParser(ParseConfig(start_time="2026-05-14 00:00:00"))
        assert parser.match_line(run_line(ZMQ_SLOW_MSG), "10.0.0.9") is None

    def test_patterns(self):
        assert isinstance(ClientInfoParser().patterns, list)


# ---------------------------------------------------------------------------
# BrpcProfilingParser
# ---------------------------------------------------------------------------

BRPC_FILE = "\n".join([
    "[BEFORE_TS]  1 1 1 1 1 1 1",           # timestamp 之前 → 跳过
    "timeStamp: 2026-07-29 20:30:42",
    "[TRACE_NAME]  SUCCESS  FAILURE  TOTAL(ns)  AVG(ns)  MAX(ns)  MIN(ns)  P50(ns)  P90(ns)  P95(ns)  P99(ns)  P999(ns)",
    "[--]",
    "[CORE_ACCEPT]  1  0  994310  100  200  50  60  70  80  90  100",
    "",                                     # 空行 → 跳过
    "random junk line",                     # 未知行 → 跳过
    "[NOT_NUMERIC]  a b c d e f g",         # 数值非法 → 跳过
    "[SHORT_ROW]  1 2 3",                   # 列数不足 → 跳过
    "timeStamp: not-a-timestamp",           # 非法时间戳 → 当前时间置空
    "[AFTER_BAD_TS]  1 1 1 1 1 1 1",        # 无有效时间戳 → 跳过
    "timeStamp: 2026-07-29T20:31:42",       # T 分隔格式
    "[CORE_CONNECT]  2  1  100  10  20  5  7",   # 7 列（无 P90+）
    "[UB_SEND]  0  0  0  0  0  0  0  0  0  0  0",  # 全零行
])


class TestBrpcProfilingParser:
    def test_parse_file_full(self, tmp_path):
        path = tmp_path / "ubsocket_profiling_x.txt"
        path.write_text(BRPC_FILE, encoding="utf-8")
        parser = BrpcProfilingParser()
        records = parser.parse_file(str(path))
        assert len(records) == 3
        by_name = {r.interface_name: r for r in records}

        accept = by_name["CORE_ACCEPT"]
        assert accept.timestamp == datetime(2026, 7, 29, 20, 30, 42)
        assert accept.success_count == 1
        assert accept.failure_count == 0
        assert accept.total_ns == 994310
        assert accept.avg_ns == 100
        assert accept.max_ns == 200
        assert accept.min_ns == 50
        assert accept.p50_ns == 60
        assert accept.p90_ns == 70
        assert accept.p95_ns == 80
        assert accept.p99_ns == 90
        assert accept.p999_ns == 100
        assert accept.source_file == "ubsocket_profiling_x.txt"

        connect = by_name["CORE_CONNECT"]
        assert connect.timestamp == datetime(2026, 7, 29, 20, 31, 42)
        assert connect.p50_ns == 7
        assert connect.p90_ns is None
        assert connect.p999_ns is None

        assert by_name["UB_SEND"].total_ns == 0

    def test_parse_file_empty(self, tmp_path):
        path = tmp_path / "empty.txt"
        path.write_text("", encoding="utf-8")
        assert BrpcProfilingParser().parse_file(str(path)) == []

    def test_parse_file_missing(self, tmp_path):
        assert BrpcProfilingParser().parse_file(str(tmp_path / "no_such.txt")) == []

    def test_parse_file_reuse_reset(self, tmp_path):
        # 二次调用应重置内部记录
        p1 = tmp_path / "a.txt"
        p1.write_text("timeStamp: 2026-07-29 20:30:42\n[IFACE]  1 0 1 1 1 1 1\n", encoding="utf-8")
        p2 = tmp_path / "b.txt"
        p2.write_text("", encoding="utf-8")
        parser = BrpcProfilingParser()
        assert len(parser.parse_file(str(p1))) == 1
        assert parser.parse_file(str(p2)) == []

    def test_parse_timestamp_formats(self):
        assert BrpcProfilingParser._parse_timestamp("2026-07-29 20:30:42") == datetime(
            2026, 7, 29, 20, 30, 42)
        assert BrpcProfilingParser._parse_timestamp("2026-07-29T20:30:42") == datetime(
            2026, 7, 29, 20, 30, 42)
        assert BrpcProfilingParser._parse_timestamp("bad-format") is None

    def test_parse_interface_row_valid(self):
        rec = BrpcProfilingParser._parse_interface_row(
            datetime(2026, 7, 29, 20, 30, 42), "IFACE", "1 0 100 10 20 5 60 70")
        assert rec is not None
        assert rec.success_count == 1
        assert rec.p50_ns == 60
        assert rec.p90_ns == 70
        assert rec.p95_ns is None

    def test_parse_interface_row_too_short(self):
        rec = BrpcProfilingParser._parse_interface_row(
            datetime(2026, 7, 29, 20, 30, 42), "IFACE", "1 2 3")
        assert rec is None

    def test_parse_interface_row_not_numeric(self):
        rec = BrpcProfilingParser._parse_interface_row(
            datetime(2026, 7, 29, 20, 30, 42), "IFACE", "a b c d e f g")
        assert rec is None
