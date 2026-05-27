#!/usr/bin/env python3
"""Generate fault log files, check commands, and aggregate logs for kvcache_conn fault modes."""

import csv
import os
import re
import shutil
import subprocess

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.normpath(os.path.join(SCRIPT_DIR, ".."))
DATA_DIR = os.path.join(PROJECT_ROOT, "data")
FAULT_LOG_DIR = os.path.join(DATA_DIR, "kvcache_conn_fault_log")

FAULT_MODES_CSV = os.path.join(DATA_DIR, "kvcache_conn_fault_mode.csv")

LOG_TEMPLATES = {
    "ds_client_access": {
        "normal": [
            "0 | DS_KV_CLIENT_GET | 49469 | 8388608 | {Object_key:kv_test_1_0_28458466174080_0,timeout:0,transportType:SHM} | ",
            "0 | DS_KV_CLIENT_PUT | 12345 | 4096 | {Object_key:kv_test_2_0_12345678901234_0,timeout:0,transportType:SHM} | ",
            "0 | DS_KV_CLIENT_GET | 8823 | 1048576 | {Object_key:kv_test_3_0_56789012345678_0,timeout:0,transportType:SHM} | ",
        ],
        "faults": {
            "kvcache_conn_fault_001": [
                "2 | DS_KV_CLIENT_PUT | 5000 | 4096 | {Object_key:bad_key,timeout:0} | The objectKey is empty",
                "1002 | DS_KV_CLIENT_GET | 30000 | 8192 | {Object_key:missing_obj,timeout:0} | ",
            ],
            "kvcache_conn_fault_002": [
                "2 | DS_KV_CLIENT_PUT | 5000 | 4096 | {Object_key:bad_key,timeout:0} | The objectKey is empty",
                "3 | DS_KV_CLIENT_GET | 8000 | 1024 | {Object_key:not_exist,timeout:0} | ",
                "8 | DS_KV_CLIENT_GET | 12000 | 2048 | {Object_key:not_ready,timeout:0} | ",
            ],
            "kvcache_conn_fault_003": [
                "2 | DS_KV_CLIENT_PUT | 5000 | 4096 | {Object_key:bad_key,timeout:0} | The objectKey is empty",
            ],
            "kvcache_conn_fault_006": [
                "2 | DS_KV_CLIENT_GET | 3000 | 512 | {Object_key:batch_key,OBJECT_KEYS_MAX_SIZE_LIMIT,timeout:0} | ",
            ],
            "kvcache_conn_fault_007": [
                "0 | DS_KV_CLIENT_GET | 49469 | 8388608 | {Object_key:kv_test_1_0_28458466174080_0,timeout:0,transportType:SHM} | NOT_FOUND",
            ],
            "kvcache_conn_fault_008": [
                "19 | DS_KV_CLIENT_GET | 15000 | 4096 | {Object_key:try_again,timeout:0} | ",
                "23 | DS_KV_CLIENT_GET | 20000 | 8192 | {Object_key:disconnect,timeout:0} | ",
                "29 | DS_KV_CLIENT_PUT | 10000 | 2048 | {Object_key:fd_closed,timeout:0} | ",
            ],
            "kvcache_conn_fault_013": [
                "25 | DS_KV_CLIENT_GET | 25000 | 4096 | {Object_key:etcd_timeout,timeout:0} | ",
            ],
            "kvcache_conn_fault_014": [
                "1001 | DS_KV_CLIENT_GET | 30000 | 8192 | {Object_key:deadline,timeout:0} | ",
                "1002 | DS_KV_CLIENT_GET | 35000 | 4096 | {Object_key:unavail,timeout:0} | ",
            ],
            "kvcache_conn_fault_022": [
                "1004 | DS_KV_CLIENT_GET | 20000 | 4096 | {Object_key:urma_err1,timeout:0} | ",
                "1006 | DS_KV_CLIENT_GET | 22000 | 8192 | {Object_key:urma_err2,timeout:0} | ",
                "1008 | DS_KV_CLIENT_PUT | 18000 | 2048 | {Object_key:urma_err3,timeout:0} | ",
                "1009 | DS_KV_CLIENT_GET | 25000 | 4096 | {Object_key:urma_connect,timeout:0} | ",
                "1010 | DS_KV_CLIENT_GET | 28000 | 8192 | {Object_key:urma_timeout,timeout:0} | ",
            ],
            "kvcache_conn_fault_026": [
                "1009 | DS_KV_CLIENT_GET | 25000 | 4096 | {Object_key:urma_connect_failed,timeout:0} | ",
            ],
            "kvcache_conn_fault_031": [
                "1001 | DS_KV_CLIENT_GET | 30000 | 8192 | {Object_key:deadline,timeout:0} | ",
                "1002 | DS_KV_CLIENT_GET | 35000 | 4096 | {Object_key:unavail,timeout:0} | ",
            ],
            "kvcache_conn_fault_032": [
                "0 | DS_KV_CLIENT_GET | 49469 | 8388608 | {Object_key:kv_test_1_0_28458466174080_0,timeout:0,transportType:SHM} | ",
            ],
            "kvcache_conn_fault_033": [
                "0 | DS_KV_CLIENT_GET | 49469 | 8388608 | {Object_key:kv_test_1_0_28458466174080_0,timeout:0,transportType:SHM} | ",
            ],
            "kvcache_conn_fault_034": [
                "0 | DS_KV_CLIENT_GET | 49469 | 8388608 | {Object_key:kv_test_1_0_28458466174080_0,timeout:0,transportType:SHM} | ",
            ],
            "kvcache_conn_fault_035": [
                "18 | DS_KV_CLIENT_GET | 5000 | 4096 | {Object_key:file_limit,timeout:0} | ",
            ],
            "kvcache_conn_fault_036": [
                "5 | DS_KV_CLIENT_GET | 8000 | 8192 | {Object_key:mmap_fail,timeout:0} | ",
            ],
            "kvcache_conn_fault_037": [
                "5 | DS_KV_CLIENT_GET | 8000 | 8192 | {Object_key:runtime_err,timeout:0} | ",
            ],
        }
    },
    "ds_client_INFO": {
        "normal": [
            "2026-05-06T13:25:28.429016 | I | client_impl.cpp:100 | kvc-client-pod-abc | 11:291 | e18c3204-0001-0001-0001-000000000001 | tenant1 | Client init success",
            "2026-05-06T13:25:29.123456 | I | client_impl.cpp:200 | kvc-client-pod-abc | 12:301 | e18c3204-0002-0002-0002-000000000002 | tenant1 | Get object success key=kv_test_1",
        ],
        "faults": {
            "kvcache_conn_fault_003": [
                "2026-05-06T13:26:00.000001 | I | client_impl.cpp:150 | kvc-client-pod-abc | 11:291 | e18c3204-0003-0003-0003-000000000003 | tenant1 | K_INVALID The objectKey is empty",
            ],
            "kvcache_conn_fault_004": [
                "2026-05-06T13:26:01.000001 | I | client_impl.cpp:80 | kvc-client-pod-abc | 11:291 | e18c3204-0004-0004-0004-000000000004 | tenant1 | ConnectOptions was not configured",
            ],
            "kvcache_conn_fault_005": [
                "2026-05-06T13:26:02.000001 | I | client_impl.cpp:250 | kvc-client-pod-abc | 11:291 | e18c3204-0005-0005-0005-000000000005 | tenant1 | Client object is already sealed",
            ],
            "kvcache_conn_fault_007": [
                "2026-05-06T13:26:03.000001 | I | client_impl.cpp:300 | kvc-client-pod-abc | 11:291 | e18c3204-0007-0007-0007-000000000007 | tenant1 | K_NOT_FOUND Can't find object key=missing_key",
            ],
            "kvcache_conn_fault_009": [
                "2026-05-06T13:26:04.000001 | I | client_impl.cpp:400 | kvc-client-pod-abc | 11:291 | e18c3204-0009-0009-0009-000000000009 | tenant1 | [RPC_RECV_TIMEOUT] req_id=12345 timeout=5000ms",
                "2026-05-06T13:26:05.000001 | I | client_impl.cpp:410 | kvc-client-pod-abc | 12:301 | e18c3204-0009-0010-0010-000000000010 | tenant1 | [RPC_SERVICE_UNAVAILABLE] worker=192.168.1.10:31402",
            ],
            "kvcache_conn_fault_011": [
                "2026-05-06T13:26:06.000001 | I | worker_oc_service_get_impl.cpp:130 | kvc-worker-pod-xyz | 11:291 | e18c3204-0011-0011-0011-000000000011 | tenant1 | etcd is timeout endpoint=http://etcd-0:2379",
            ],
            "kvcache_conn_fault_012": [
                "2026-05-06T13:26:07.000001 | I | health_check.cpp:50 | kvc-worker-pod-xyz | 11:291 | e18c3204-0012-0012-0012-000000000012 | tenant1 | Cannot receive heartbeat from worker. worker_id=worker-3",
            ],
            "kvcache_conn_fault_015": [
                "2026-05-06T13:26:08.000001 | I | tcp_channel.cpp:200 | kvc-worker-pod-xyz | 11:291 | e18c3204-0015-0015-0015-000000000015 | tenant1 | [TCP_CONNECT_FAILED] addr=192.168.1.10:31402 errno=111",
            ],
            "kvcache_conn_fault_016": [
                "2026-05-06T13:26:09.000001 | I | tcp_channel.cpp:200 | kvc-worker-pod-xyz | 11:291 | e18c3204-0016-0016-0016-000000000016 | tenant1 | [TCP_CONNECT_FAILED] addr=192.168.1.10:31402 errno=111",
            ],
            "kvcache_conn_fault_017": [
                "2026-05-06T13:26:10.000001 | I | tcp_channel.cpp:220 | kvc-worker-pod-xyz | 11:291 | e18c3204-0017-0017-0017-000000000017 | tenant1 | [TCP_CONNECT_RESET] addr=192.168.1.10:31402",
                "2026-05-06T13:26:11.000001 | I | tcp_channel.cpp:230 | kvc-worker-pod-xyz | 12:301 | e18c3204-0017-0018-0018-000000000018 | tenant1 | [TCP_NETWORK_UNREACHABLE] addr=192.168.1.20:31402",
            ],
            "kvcache_conn_fault_018": [
                "2026-05-06T13:26:12.000001 | I | uds_channel.cpp:100 | kvc-worker-pod-xyz | 11:291 | e18c3204-0018-0019-0019-000000000019 | tenant1 | [UDS_CONNECT_FAILED] path=/var/run/datasystem/worker.sock",
                "2026-05-06T13:26:13.000001 | I | shm_fd.cpp:80 | kvc-worker-pod-xyz | 12:301 | e18c3204-0018-0020-0020-000000000020 | tenant1 | [SHM_FD_TRANSFER_FAILED] reason=EMFILE",
            ],
            "kvcache_conn_fault_019": [
                "2026-05-06T13:26:14.000001 | I | zmq_stub.cpp:300 | kvc-worker-pod-xyz | 11:291 | e18c3204-0019-0021-0021-000000000021 | tenant1 | [ZMQ_SEND_FAILURE_TOTAL] zmq_last_error_number=111",
            ],
            "kvcache_conn_fault_020": [
                "2026-05-06T13:26:15.000001 | I | etcd_client.cpp:80 | kvc-worker-pod-xyz | 11:291 | e18c3204-0020-0022-0022-000000000022 | tenant1 | etcd is timeout endpoint=http://etcd-0:2379",
            ],
            "kvcache_conn_fault_021": [
                "2026-05-06T13:26:16.000001 | I | tcp_channel.cpp:200 | kvc-worker-pod-xyz | 11:291 | e18c3204-0021-0023-0023-000000000023 | tenant1 | [TCP_CONNECT_FAILED] addr=192.168.1.10:31402 errno=111",
            ],
            "kvcache_conn_fault_023": [
                "2026-05-06T13:26:17.000001 | I | urma_channel.cpp:100 | kvc-worker-pod-xyz | 11:291 | e18c3204-0023-0024-0024-000000000024 | tenant1 | [URMA_NEED_CONNECT] remoteInstanceId=200",
            ],
            "kvcache_conn_fault_024": [
                "2026-05-06T13:26:18.000001 | I | urma_channel.cpp:150 | kvc-worker-pod-xyz | 11:291 | e18c3204-0024-0025-0025-000000000025 | tenant1 | [URMA_RECREATE_JFS] cqeStatus=9",
                "2026-05-06T13:26:19.000001 | I | urma_channel.cpp:160 | kvc-worker-pod-xyz | 12:301 | e18c3204-0024-0026-0026-000000000026 | tenant1 | [URMA_RECREATE_JFS_FAILED] reason=ack_timeout",
            ],
            "kvcache_conn_fault_025": [
                "2026-05-06T13:26:20.000001 | I | urma_channel.cpp:200 | kvc-worker-pod-xyz | 11:291 | e18c3204-0025-0027-0027-000000000027 | tenant1 | [URMA_POLL_ERROR] errno=5",
                "2026-05-06T13:26:21.000001 | I | urma_channel.cpp:210 | kvc-worker-pod-xyz | 12:301 | e18c3204-0025-0028-0028-000000000028 | tenant1 | [URMA_WAIT_TIMEOUT] instanceId=100",
            ],
            "kvcache_conn_fault_027": [
                "2026-05-06T13:26:22.000001 | I | urma_init.cpp:50 | kvc-worker-pod-xyz | 11:291 | e18c3204-0027-0029-0029-000000000029 | tenant1 | Failed to urma init device=ub0",
            ],
            "kvcache_conn_fault_028": [
                "2026-05-06T13:26:23.000001 | I | fast_transport.cpp:100 | kvc-worker-pod-xyz | 11:291 | e18c3204-0028-0030-0030-000000000030 | tenant1 | [URMA_NEED_CONNECT] FastTransport handshake failed",
            ],
            "kvcache_conn_fault_036": [
                "2026-05-06T13:26:24.000001 | I | shm_mmap.cpp:80 | kvc-worker-pod-xyz | 11:291 | e18c3204-0036-0031-0031-000000000031 | tenant1 | K_RUNTIME_ERROR Get mmap entry failed size=8388608",
            ],
            "kvcache_conn_fault_037": [
                "2026-05-06T13:26:25.000001 | I | shm_mmap.cpp:80 | kvc-worker-pod-xyz | 11:291 | e18c3204-0037-0032-0032-000000000032 | tenant1 | K_RUNTIME_ERROR Get mmap entry failed size=8388608",
            ],
            "kvcache_conn_fault_038": [
                "2026-05-06T13:26:26.000001 | I | tcp_channel.cpp:200 | kvc-client-pod-abc | 11:291 | e18c3204-0038-0033-0033-000000000033 | tenant1 | [TCP_CONNECT_FAILED] addr=192.168.1.10:31402 errno=111",
            ],
            "kvcache_conn_fault_041": [
                "2026-05-06T13:26:27.000001 | I | tcp_channel.cpp:200 | kvc-client-pod-abc | 11:291 | e18c3204-0041-0034-0034-000000000034 | tenant1 | [TCP_CONNECT_FAILED] addr=192.168.1.10:31402 errno=111",
            ],
            "kvcache_conn_fault_042": [
                "2026-05-06T13:26:28.000001 | I | uds_channel.cpp:100 | kvc-client-pod-abc | 11:291 | e18c3204-0042-0035-0035-000000000035 | tenant1 | [UDS_CONNECT_FAILED] path=/var/run/datasystem/worker.sock",
            ],
            "kvcache_conn_fault_044": [
                "2026-05-06T13:26:29.000001 | I | health_check.cpp:50 | kvc-worker-pod-xyz | 11:291 | e18c3204-0044-0036-0036-000000000036 | tenant1 | Cannot receive heartbeat from worker. worker_id=worker-3",
                "2026-05-06T13:26:30.000001 | I | client_impl.cpp:400 | kvc-client-pod-abc | 12:301 | e18c3204-0044-0037-0037-000000000037 | tenant1 | K_CLIENT_WORKER_DISCONNECT worker=192.168.1.10:31402",
            ],
        }
    },
    "datasystem_worker_INFO": {
        "normal": [
            "2026-05-06T13:25:28.429016 | I | worker_oc_service_get_impl.cpp:130 | kvc-worker-pod-xyz | 11:291 | e18c3204-0001-0001-0001-000000000001 | tenant1 | Worker started on port 31402",
            "2026-05-06T13:25:29.123456 | I | worker_oc_service_get_impl.cpp:200 | kvc-worker-pod-xyz | 12:301 | e18c3204-0002-0002-0002-000000000002 | tenant1 | Metrics Summary, version=v0, cycle=100, interval=10000ms",
        ],
        "faults": {
            "kvcache_conn_fault_009": [
                "2026-05-06T13:26:04.000001 | I | worker_oc_service_get_impl.cpp:130 | kvc-worker-pod-xyz | 11:291 | e18c3204-0009-0009-0009-000000000009 | tenant1 | [RPC_RECV_TIMEOUT] req_id=67890 timeout=5000ms",
            ],
            "kvcache_conn_fault_010": [
                "2026-05-06T13:26:05.000001 | I | zmq_gateway.cpp:100 | kvc-worker-pod-xyz | 11:291 | e18c3204-0010-0010-0010-000000000010 | tenant1 | zmq_gateway_recreate_total=+3",
                "2026-05-06T13:26:05.000002 | I | zmq_gateway.cpp:110 | kvc-worker-pod-xyz | 11:292 | e18c3204-0010-0011-0011-000000000011 | tenant1 | zmq_event_disconnect_total=+1",
            ],
            "kvcache_conn_fault_011": [
                "2026-05-06T13:26:06.000001 | I | etcd_client.cpp:80 | kvc-worker-pod-xyz | 11:291 | e18c3204-0011-0011-0011-000000000011 | tenant1 | etcd is timeout endpoint=http://etcd-0:2379",
            ],
            "kvcache_conn_fault_012": [
                "2026-05-06T13:26:07.000001 | I | health_check.cpp:50 | kvc-worker-pod-xyz | 11:291 | e18c3204-0012-0012-0012-000000000012 | tenant1 | Cannot receive heartbeat from worker. worker_id=worker-3",
                "2026-05-06T13:26:07.000002 | I | health_check.cpp:80 | kvc-worker-pod-xyz | 12:301 | e18c3204-0012-0013-0013-000000000013 | tenant1 | [HealthCheck] Worker is exiting now",
            ],
            "kvcache_conn_fault_015": [
                "2026-05-06T13:26:08.000001 | I | tcp_channel.cpp:200 | kvc-worker-pod-xyz | 11:291 | e18c3204-0015-0015-0015-000000000015 | tenant1 | [TCP_CONNECT_FAILED] addr=192.168.1.10:31402 errno=111",
                "2026-05-06T13:26:08.000002 | I | zmq_stub.cpp:300 | kvc-worker-pod-xyz | 12:301 | e18c3204-0015-0016-0016-000000000016 | tenant1 | [ZMQ_SEND_FAILURE_TOTAL] zmq_last_error_number=111",
            ],
            "kvcache_conn_fault_016": [
                "2026-05-06T13:26:09.000001 | I | tcp_channel.cpp:200 | kvc-worker-pod-xyz | 11:291 | e18c3204-0016-0017-0017-000000000017 | tenant1 | [TCP_CONNECT_FAILED] addr=192.168.1.10:31402 errno=111",
            ],
            "kvcache_conn_fault_017": [
                "2026-05-06T13:26:10.000001 | I | tcp_channel.cpp:220 | kvc-worker-pod-xyz | 11:291 | e18c3204-0017-0018-0018-000000000018 | tenant1 | [TCP_CONNECT_RESET] addr=192.168.1.10:31402",
            ],
            "kvcache_conn_fault_018": [
                "2026-05-06T13:26:12.000001 | I | uds_channel.cpp:100 | kvc-worker-pod-xyz | 11:291 | e18c3204-0018-0019-0019-000000000019 | tenant1 | [UDS_CONNECT_FAILED] path=/var/run/datasystem/worker.sock",
            ],
            "kvcache_conn_fault_019": [
                "2026-05-06T13:26:14.000001 | I | zmq_stub.cpp:300 | kvc-worker-pod-xyz | 11:291 | e18c3204-0019-0021-0021-000000000021 | tenant1 | [ZMQ_SEND_FAILURE_TOTAL] zmq_last_error_number=111",
            ],
            "kvcache_conn_fault_020": [
                "2026-05-06T13:26:15.000001 | I | etcd_client.cpp:80 | kvc-worker-pod-xyz | 11:291 | e18c3204-0020-0022-0022-000000000022 | tenant1 | etcd is unavailable endpoint=http://etcd-1:2379",
            ],
            "kvcache_conn_fault_021": [
                "2026-05-06T13:26:16.000001 | I | tcp_channel.cpp:200 | kvc-worker-pod-xyz | 11:291 | e18c3204-0021-0023-0023-000000000023 | tenant1 | [TCP_CONNECT_FAILED] addr=192.168.1.10:31402 errno=111",
                "2026-05-06T13:26:16.000002 | I | rpc_service.cpp:100 | kvc-worker-pod-xyz | 12:301 | e18c3204-0021-0024-0024-000000000024 | tenant1 | [RPC_SERVICE_UNAVAILABLE] worker=192.168.1.10:31402",
            ],
            "kvcache_conn_fault_023": [
                "2026-05-06T13:26:17.000001 | I | urma_channel.cpp:100 | kvc-worker-pod-xyz | 11:291 | e18c3204-0023-0025-0025-000000000025 | tenant1 | [URMA_NEED_CONNECT] remoteInstanceId=200",
            ],
            "kvcache_conn_fault_024": [
                "2026-05-06T13:26:18.000001 | I | urma_channel.cpp:150 | kvc-worker-pod-xyz | 11:291 | e18c3204-0024-0026-0026-000000000026 | tenant1 | [URMA_RECREATE_JFS] cqeStatus=9",
            ],
            "kvcache_conn_fault_025": [
                "2026-05-06T13:26:20.000001 | I | urma_channel.cpp:200 | kvc-worker-pod-xyz | 11:291 | e18c3204-0025-0027-0027-000000000027 | tenant1 | [URMA_POLL_ERROR] errno=5",
            ],
            "kvcache_conn_fault_027": [
                "2026-05-06T13:26:22.000001 | I | urma_init.cpp:50 | kvc-worker-pod-xyz | 11:291 | e18c3204-0027-0029-0029-000000000029 | tenant1 | Failed to urma init device=ub0",
            ],
            "kvcache_conn_fault_028": [
                "2026-05-06T13:26:23.000001 | I | fast_transport.cpp:100 | kvc-worker-pod-xyz | 11:291 | e18c3204-0028-0030-0030-000000000030 | tenant1 | [URMA_NEED_CONNECT] FastTransport handshake failed",
            ],
            "kvcache_conn_fault_029": [
                "2026-05-06T13:26:24.000001 | I | worker_oc_service_get_impl.cpp:130 | kvc-worker-pod-xyz | 11:291 | e18c3204-0029-0031-0031-000000000031 | tenant1 | [RPC_RECV_TIMEOUT] req_id=11111 timeout=5000ms",
                "2026-05-06T13:26:24.000002 | I | metrics.cpp:50 | kvc-worker-pod-xyz | 12:301 | e18c3204-0029-0032-0032-000000000032 | tenant1 | zmq_send_failure_total=+0",
            ],
            "kvcache_conn_fault_030": [
                "2026-05-06T13:26:25.000001 | I | zmq_gateway.cpp:100 | kvc-worker-pod-xyz | 11:291 | e18c3204-0030-0033-0033-000000000033 | tenant1 | zmq_event_handshake_failure_total=+2",
            ],
            "kvcache_conn_fault_036": [
                "2026-05-06T13:26:26.000001 | I | shm_mmap.cpp:80 | kvc-worker-pod-xyz | 11:291 | e18c3204-0036-0034-0034-000000000034 | tenant1 | K_RUNTIME_ERROR Get mmap entry failed size=8388608",
            ],
            "kvcache_conn_fault_037": [
                "2026-05-06T13:26:27.000001 | I | shm_mmap.cpp:80 | kvc-worker-pod-xyz | 11:291 | e18c3204-0037-0035-0035-000000000035 | tenant1 | K_RUNTIME_ERROR etcd is timeout",
            ],
            "kvcache_conn_fault_044": [
                "2026-05-06T13:26:28.000001 | I | health_check.cpp:50 | kvc-worker-pod-xyz | 11:291 | e18c3204-0044-0036-0036-000000000036 | tenant1 | Cannot receive heartbeat from worker. worker_id=worker-3",
            ],
            "kvcache_conn_fault_050": [
                "2026-05-06T13:26:29.000001 | I | health_check.cpp:50 | kvc-worker-pod-xyz | 11:291 | e18c3204-0050-0037-0037-000000000037 | tenant1 | Cannot receive heartbeat from worker. worker_id=worker-3",
            ],
        }
    },
    "resource": {
        "normal": [
            "WORKER_OC_SERVICE_THREAD_POOL: IDLE_NUM=64, CURRENT_TOTAL_NUM=128, MAX_THREAD_NUM=128, WAITING_TASK_NUM=0, THREAD_POOL_USAGE=50%",
            "ETCD_QUEUE: CURRENT_SIZE=10, TOTAL_LIMIT=100, ETCD_QUEUE_USAGE=10%",
            "ETCD_REQUEST_SUCCESS_RATE: 0.99",
            "SHARED_MEMORY: MEMORY_USAGE=2048MB, PHYSICAL_MEMORY_USAGE=1800MB, TOTAL_LIMIT=10240MB",
            "SPILL_HARD_DISK: SPACE_USAGE=200MB, TOTAL_LIMIT=1000MB",
            "SHARED_DISK: USAGE=100MB, TOTAL_LIMIT=500MB",
        ],
        "faults": {
            "kvcache_conn_fault_013": [
                "ETCD_QUEUE: CURRENT_SIZE=90, TOTAL_LIMIT=100, ETCD_QUEUE_USAGE=90%",
                "ETCD_REQUEST_SUCCESS_RATE: 0.85",
            ],
            "kvcache_conn_fault_032": [
                "SHARED_MEMORY: MEMORY_USAGE=9500MB, PHYSICAL_MEMORY_USAGE=9000MB, TOTAL_LIMIT=10240MB",
            ],
            "kvcache_conn_fault_033": [
                "SPILL_HARD_DISK: SPACE_USAGE=950MB, TOTAL_LIMIT=1000MB",
                "SHARED_DISK: USAGE=480MB, TOTAL_LIMIT=500MB",
            ],
            "kvcache_conn_fault_034": [
                "WORKER_OC_SERVICE_THREAD_POOL: IDLE_NUM=0, CURRENT_TOTAL_NUM=128, MAX_THREAD_NUM=128, WAITING_TASK_NUM=64, THREAD_POOL_USAGE=100%",
            ],
        }
    },
}

SYSTEM_CMD_FAULTS = {
    "kvcache_conn_fault_026": {
        "ifconfig_ub0": "ub0: flags=4098<BROADCAST,MULTICAST>  mtu 1500\n        ether 00:1a:2b:3c:4d:5e  txqueuelen 1000  (Ethernet)\n        UP BROADCAST RUNNING  mtu 1500",
        "ls_dev_ub": "",
        "ubinfo": "",
    },
    "kvcache_conn_fault_035": {
        "ulimit_n": "65535",
        "ls_proc_fd_wc": "58000",
    },
    "kvcache_conn_fault_036": {
        "ulimit_l": "65536",
    },
    "kvcache_conn_fault_039": {
        "pgrep_worker": "",
    },
    "kvcache_conn_fault_040": {
        "pgrep_worker": "12345 /opt/datasystem/worker",
        "ss_tnlp": "",
    },
    "kvcache_conn_fault_041": {
        "ss_tnlp": "LISTEN 0 128 *:31402",
    },
    "kvcache_conn_fault_045": {
        "ping": "PING 192.168.1.10 (192.168.1.10) 56(84) bytes of data.\nFrom 192.168.1.1 icmp_seq=1 Destination Host Unreachable",
    },
    "kvcache_conn_fault_046": {
        "kubectl_describe": "Conditions:\n  Type             Status    Reason\n  Ready            False     NodeStatusUnknown\nTaints: node.kubernetes.io/not-ready:NoSchedule",
    },
    "kvcache_conn_fault_047": {
        "dmesg_oom": "Out of memory: Kill process 12345 (datasystem_worker) score 950 or sacrifice child",
        "pgrep_worker": "",
    },
    "kvcache_conn_fault_048": {
        "journalctl": "-- Logs begin at ... --\nMay 06 13:26:00 worker-node datasystem-worker[12345]: exited with code 139",
        "dmesg_no_oom": "",
        "pgrep_worker": "",
    },
    "kvcache_conn_fault_049": {
        "pgrep_worker": "12345 /opt/datasystem/worker",
        "ss_tnlp": "",
    },
    "kvcache_conn_fault_050": {
        "pgrep_worker": "12345 /opt/datasystem/worker",
        "ss_tnlp": "LISTEN 0 128 *:31402",
    },
}


def extract_commands_from_cpp():
    """Extract shell commands from generated .cpp files."""
    realization_dir = os.path.join(PROJECT_ROOT, "src/diagnosis_tool/failure_mode_realization")
    cmd_map = {}

    cpp_files = sorted([f for f in os.listdir(realization_dir) if f.startswith("kvcache_conn_fault_") and f.endswith(".cpp")])

    for cpp_file in cpp_files:
        fault_id = cpp_file.replace(".cpp", "")
        filepath = os.path.join(realization_dir, cpp_file)
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()

        pattern = r'R"\((.*?)\)"'
        matches = re.findall(pattern, content, re.DOTALL)

        for match in matches:
            cmd = match.strip()
            cmd = " ".join(cmd.split())
            if cmd and cmd not in cmd_map.get(fault_id, []):
                cmd_map.setdefault(fault_id, []).append(cmd)

    return cmd_map


def extract_base_commands(cmd_str):
    """Extract base command names from a shell pipeline string."""
    KNOWN_COMMANDS = {
        "grep", "awk", "sort", "uniq", "head", "tail", "wc", "cat", "ls",
        "ssh", "pgrep", "ss", "ifconfig", "ping", "kubectl", "dmesg",
        "free", "df", "ulimit", "journalctl", "ubinfo", "etcdctl",
        "systemctl", "nc", "iptables",
    }
    parts = cmd_str.split("|")
    base_cmds = []
    for part in parts:
        tokens = part.strip().split()
        if tokens:
            base_cmd = tokens[0]
            if base_cmd in KNOWN_COMMANDS:
                base_cmds.append(base_cmd)
    return base_cmds


def check_commands(cmd_map):
    """Check which commands are available and which fail. Return ignore and error lists."""
    ignore_cmds = []
    error_cmds = []

    checked = set()

    for fault_id, cmds in cmd_map.items():
        for cmd in cmds:
            base_cmds = extract_base_commands(cmd)
            for base_cmd in base_cmds:
                if base_cmd in checked:
                    continue
                checked.add(base_cmd)

                try:
                    result = subprocess.run(
                        ["which", base_cmd],
                        capture_output=True, text=True, timeout=5
                    )
                    if result.returncode != 0:
                        ignore_cmds.append((base_cmd, fault_id, cmd))
                        continue
                except Exception:
                    ignore_cmds.append((base_cmd, fault_id, cmd))
                    continue

                try:
                    safe_cmd = cmd.replace("$LOG", "/tmp/nonexistent_log_dir")
                    safe_cmd = safe_cmd.replace("<pid>", "1")
                    safe_cmd = safe_cmd.replace("<worker_port>", "31402")
                    safe_cmd = safe_cmd.replace("<node_ip>", "127.0.0.1")
                    safe_cmd = safe_cmd.replace("<n>", "localhost")
                    result = subprocess.run(
                        ["bash", "-c", safe_cmd],
                        capture_output=True, text=True, timeout=5
                    )
                    if result.returncode != 0 and result.returncode != 1:
                        error_cmds.append((base_cmd, fault_id, cmd, result.stderr[:200] if result.stderr else f"exit code {result.returncode}"))
                except subprocess.TimeoutExpired:
                    error_cmds.append((base_cmd, fault_id, cmd, "timeout after 5s"))
                except Exception as e:
                    error_cmds.append((base_cmd, fault_id, cmd, str(e)[:200]))

    return ignore_cmds, error_cmds


def generate_ignore_cmd_md(ignore_cmds, cmd_map):
    """Generate ignore-cmd.md for commands not installed."""
    output_path = os.path.join(DATA_DIR, "ignore-cmd.md")
    with open(output_path, "w", encoding="utf-8") as f:
        f.write("# 未安装命令清单\n\n")
        f.write("以下命令在当前环境中未安装，无法执行验证。\n\n")
        f.write("| 命令 | 故障模式 | 完整命令 |\n")
        f.write("|------|---------|--------|\n")
        for base_cmd, fault_id, cmd in ignore_cmds:
            f.write(f"| {base_cmd} | {fault_id} | `{cmd}` |\n")
    print(f"Generated: {output_path}")


def generate_error_cmd_md(error_cmds, cmd_map):
    """Generate error-cmd.md for commands that fail."""
    output_path = os.path.join(DATA_DIR, "error-cmd.md")
    with open(output_path, "w", encoding="utf-8") as f:
        f.write("# 执行失败命令清单\n\n")
        f.write("以下命令已安装但执行失败。\n\n")
        f.write("| 命令 | 故障模式 | 完整命令 | 错误信息 |\n")
        f.write("|------|---------|--------|--------|\n")
        for base_cmd, fault_id, cmd, err in error_cmds:
            f.write(f"| {base_cmd} | {fault_id} | `{cmd}` | {err} |\n")
    print(f"Generated: {output_path}")


def generate_fault_logs():
    """Generate fault log files for each fault mode."""
    if os.path.exists(FAULT_LOG_DIR):
        shutil.rmtree(FAULT_LOG_DIR)
    os.makedirs(FAULT_LOG_DIR, exist_ok=True)

    realization_dir = os.path.join(PROJECT_ROOT, "src/diagnosis_tool/failure_mode_realization")
    cpp_files = sorted([f for f in os.listdir(realization_dir) if f.startswith("kvcache_conn_fault_") and f.endswith(".cpp")])

    for cpp_file in cpp_files:
        fault_id = cpp_file.replace(".cpp", "")
        fault_dir = os.path.join(FAULT_LOG_DIR, fault_id)
        os.makedirs(fault_dir, exist_ok=True)

        for log_type, log_data in LOG_TEMPLATES.items():
            fault_lines = log_data["faults"].get(fault_id, [])
            if not fault_lines:
                continue

            if log_type == "ds_client_access":
                log_filename = f"{fault_id}_ds_client_access.log"
            elif log_type == "ds_client_INFO":
                log_filename = f"{fault_id}_ds_client.INFO.log"
            elif log_type == "datasystem_worker_INFO":
                log_filename = f"{fault_id}_datasystem_worker.INFO.log"
            elif log_type == "resource":
                log_filename = f"{fault_id}_resource.log"
            else:
                continue

            log_path = os.path.join(fault_dir, log_filename)
            with open(log_path, "w", encoding="utf-8") as f:
                for line in log_data["normal"]:
                    f.write(line + "\n")
                for line in fault_lines:
                    f.write(line + "\n")

        if fault_id in SYSTEM_CMD_FAULTS:
            sys_cmd_data = SYSTEM_CMD_FAULTS[fault_id]
            sys_log_filename = f"{fault_id}_system_cmd.log"
            sys_log_path = os.path.join(fault_dir, sys_log_filename)
            with open(sys_log_path, "w", encoding="utf-8") as f:
                for cmd_name, output in sys_cmd_data.items():
                    f.write(f"# {cmd_name}\n")
                    f.write(output + "\n")

        if not os.listdir(fault_dir):
            os.rmdir(fault_dir)

    print(f"Generated fault log directories under: {FAULT_LOG_DIR}")


def aggregate_logs():
    """Aggregate all fault logs by type into data/ directory."""
    aggregate_map = {
        "ds_client_access.log": [],
        "ds_client.INFO.log": [],
        "datasystem_worker.INFO.log": [],
        "resource.log": [],
        "system_cmd.log": [],
    }

    if not os.path.exists(FAULT_LOG_DIR):
        print("Warning: fault log directory does not exist, skipping aggregation.")
        return

    for fault_id in sorted(os.listdir(FAULT_LOG_DIR)):
        fault_dir = os.path.join(FAULT_LOG_DIR, fault_id)
        if not os.path.isdir(fault_dir):
            continue

        for log_file in sorted(os.listdir(fault_dir)):
            log_path = os.path.join(fault_dir, log_file)
            if not os.path.isfile(log_path):
                continue

            if log_file.endswith("_ds_client_access.log"):
                agg_key = "ds_client_access.log"
            elif log_file.endswith("_ds_client.INFO.log"):
                agg_key = "ds_client.INFO.log"
            elif log_file.endswith("_datasystem_worker.INFO.log"):
                agg_key = "datasystem_worker.INFO.log"
            elif log_file.endswith("_resource.log"):
                agg_key = "resource.log"
            elif log_file.endswith("_system_cmd.log"):
                agg_key = "system_cmd.log"
            else:
                continue

            with open(log_path, "r", encoding="utf-8") as f:
                content = f.read()
            aggregate_map[agg_key].append(f"# === {fault_id} ===\n{content}")

    for agg_filename, contents in aggregate_map.items():
        if not contents:
            continue
        agg_path = os.path.join(DATA_DIR, agg_filename)
        with open(agg_path, "w", encoding="utf-8") as f:
            f.write("\n".join(contents))
        print(f"Aggregated: {agg_path}")


def main():
    """Main function."""
    os.makedirs(DATA_DIR, exist_ok=True)

    print("=== Step 1: Extract commands from .cpp files ===")
    cmd_map = extract_commands_from_cpp()
    total_cmds = sum(len(v) for v in cmd_map.values())
    print(f"Extracted {total_cmds} commands from {len(cmd_map)} fault modes")

    print("\n=== Step 2: Check command availability ===")
    ignore_cmds, error_cmds = check_commands(cmd_map)
    print(f"Commands not installed: {len(ignore_cmds)}")
    print(f"Commands with errors: {len(error_cmds)}")

    generate_ignore_cmd_md(ignore_cmds, cmd_map)
    generate_error_cmd_md(error_cmds, cmd_map)

    print("\n=== Step 3: Generate fault log files ===")
    generate_fault_logs()

    print("\n=== Step 4: Aggregate logs by type ===")
    aggregate_logs()

    print("\nDone!")


if __name__ == "__main__":
    main()
