# Copyright (c) Huawei Technologies Co., Ltd. 2023-2025. All rights reserved.
"""latency.regex.kvcache_log 正则模式单元测试。"""
from latency.regex import kvcache_log as rx


class TestObjectKeyRe:
    def test_bracketed(self):
        m = rx.OBJECT_KEY_RE.search("Object_key:[obj-123]")
        assert m is not None
        assert m.group(1) == "obj-123"

    def test_lowercase(self):
        m = rx.OBJECT_KEY_RE.search("object_key:obj-456")
        assert m is not None
        assert m.group(1) == "obj-456"

    def test_stops_at_comma(self):
        m = rx.OBJECT_KEY_RE.search("object_key:key1, other=1")
        assert m is not None
        assert m.group(1) == "key1"

    def test_no_match(self):
        assert rx.OBJECT_KEY_RE.search("nothing here") is None


class TestNotFoundRe:
    def test_k_not_found(self):
        assert rx.NOT_FOUND_RE.search("error K_NOT_FOUND in op") is not None

    def test_not_found_spaced(self):
        assert rx.NOT_FOUND_RE.search("resource not found") is not None

    def test_notfound_joined(self):
        assert rx.NOT_FOUND_RE.search("oops notfound") is not None

    def test_no_match(self):
        assert rx.NOT_FOUND_RE.search("all good") is None


class TestUrmaRe:
    LINE = (
        "[URMA_ELAPSED_TOTAL] cost 12.5ms src address : 1.2.3.4, "
        "target address : 5.6.7.8, extra urma_inflight_wr_count: 3"
    )

    def test_full_match(self):
        m = rx.URMA_RE.search(self.LINE)
        assert m is not None
        assert m.group(1) == "12.5"
        assert m.group(2) == "1.2.3.4"
        assert m.group(3) == "5.6.7.8"
        assert m.group(4) == "3"

    def test_no_match(self):
        assert rx.URMA_RE.search("unrelated log line") is None


class TestCreateMetaReqRe:
    def test_match(self):
        m = rx.CREATE_META_REQ_RE.search(
            "Processing CreateMetaReq, id=1 src=10.0.0.1:9000, dst=10.0.0.2:9000"
        )
        assert m is not None
        assert m.group(1) == "10.0.0.1"
        assert m.group(2) == "10.0.0.2"


class TestUrmaLinkRe:
    def test_match(self):
        m = rx.URMA_LINK_RE.search(
            "WorkerWorkerExchangeUrmaConnectInfo finish, elapsed ms: 42.5"
        )
        assert m is not None
        assert m.group(1) == "42.5"

    def test_alt_keyword(self):
        m = rx.URMA_LINK_RE.search(
            "Worker-worker transport connection exchange success, elapsed ms: 7"
        )
        assert m is not None
        assert m.group(1) == "7"


class TestRemoteRegexes:
    def test_remote_get(self):
        m = rx.REMOTE_GET_RE.search("Remote get request: src=1.1.1.1, dst=2.2.2.2]")
        assert m is not None
        assert m.group(1) == "1.1.1.1"
        assert m.group(2) == "2.2.2.2"

    def test_remote_pull(self):
        m = rx.REMOTE_PULL_RE.search(
            "Processing pull object[key1] src=3.3.3.3, dst=4.4.4.4]"
        )
        assert m is not None
        assert m.group(1) == "3.3.3.3"
        assert m.group(2) == "4.4.4.4"

    def test_remote_endpoint(self):
        m = rx.REMOTE_ENDPOINT_RE.search("src: 5.5.5.5, dst: 6.6.6.6")
        assert m is not None
        assert m.group(1) == "5.5.5.5"
        assert m.group(2) == "6.6.6.6"


class TestQueryMetaRe:
    def test_match(self):
        m = rx.QUERY_META_RE.search("QueryMeta done cost: 15.5ms")
        assert m is not None
        assert m.group(1) == "15.5"

    def test_no_unit(self):
        m = rx.QUERY_META_RE.search("cost: 9")
        assert m is None or m.group(1) == "9"


class TestLeadingFloatRe:
    def test_with_ms_and_paren(self):
        m = rx.LEADING_FLOAT_RE.match("123ms(slow)")
        assert m is not None
        assert m.group(1) == "123"

    def test_bare_number(self):
        m = rx.LEADING_FLOAT_RE.match("  45.6")
        assert m is not None
        assert m.group(1) == "45.6"


class TestLatencyMetricRegexes:
    def test_sdk_process(self):
        m = rx.SDK_PROCESS_RE.search("totalCost: 88.5ms")
        assert m is not None
        assert m.group("cost") == "88.5"

    def test_sdk_process_full(self):
        line = (
            "[Get] Done, clientId: c1, objects: 3, transferPath: p1, "
            "totalCost: 12.5ms, inflightRemoteGet: 2 exceed 10ms: {a: 1}"
        )
        m = rx.SDK_PROCESS_RE.search(line)
        assert m is not None
        assert m.group("client_id") == "c1"
        assert m.group("objects") == "3"
        assert m.group("cost") == "12.5"
        assert m.group("inflight_remote_get") == "2"

    def test_sdk_rpc(self):
        m = rx.SDK_RPC_RE.search("Worker to master rpc QueryMeta: 45.6 ms")
        assert m is not None
        assert m.group("cost") == "45.6"

    def test_local_worker_cost(self):
        m = rx.LOCAL_WORKER_COST_RE.search("ProcessGetObjectRequest: 3.2 ms")
        assert m is not None
        assert m.group("cost") == "3.2"

    def test_local_worker_lock(self):
        m = rx.LOCAL_WORKER_LOCK_RE.search("worker SafeObject WLock: 1.1 ms")
        assert m is not None
        assert m.group("cost") == "1.1"

    def test_remote_worker_cost(self):
        m = rx.REMOTE_WORKER_COST_RE.search(
            "[Get/RemotePull] finish, count: 2, cost: 9.9ms, src = 1.1.1.1, dst = 2.2.2.2"
        )
        assert m is not None
        assert m.group("cost") == "9.9"
        assert m.group("src") == "1.1.1.1"

    def test_remote_worker_rpc(self):
        m = rx.REMOTE_WORKER_RPC_RE.search("[Get] Remote done, count: 1, cost: 5.5ms")
        assert m is not None
        assert m.group("cost") == "5.5"

    def test_master_process(self):
        m = rx.MASTER_PROCESS_RE.search(
            "QueryMeta done, target num 4, success num 3, cost: 6.6ms"
        )
        assert m is not None
        assert m.group("target_num") == "4"
        assert m.group("cost") == "6.6"

    def test_master_rpc(self):
        line = (
            "[ZMQ_RPC_FRAMEWORK_SLOW] trace_id=t1 framework_us=1 e2e_us=2 "
            "client_req_framework_us=3 remote_processing_us=4 client_rsp_framework_us=5 "
            "server_req_queue_us=6 server_exec_us=7 server_rsp_queue_us=8 "
            "network_residual_us=9"
        )
        m = rx.MASTER_RPC_RE.search(line)
        assert m is not None
        assert m.group("rpc_trace_id") == "t1"
        assert m.group("remote_processing_us") == "4"
        assert m.group("network_residual_us") == "9"
