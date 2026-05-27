#!/usr/bin/env python3
"""Generate KVCache connectivity fault delimitation code from fault mode document."""

import json
import csv
import os
import re

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.normpath(os.path.join(SCRIPT_DIR, ".."))
OUTPUT_DIR = os.path.join(PROJECT_ROOT, "src/diagnosis_tool/failure_mode_realization")
DATA_DIR = os.path.join(PROJECT_ROOT, "data")
CMAKE_FILE = os.path.join(PROJECT_ROOT, "src/diagnosis_tool/CMakeLists.txt")

# All fault modes data extracted from the document
FAULT_MODES = [
    {
        "id": "kvcache_conn_fault_001",
        "name": "KVCache通断异常",
        "children": ["kvcache_conn_fault_002", "kvcache_conn_fault_008", "kvcache_conn_fault_013", "kvcache_conn_fault_014", "kvcache_conn_fault_022", "kvcache_conn_fault_031", "kvcache_conn_fault_038", "kvcache_conn_fault_044"],
        "validation": "查询KVCache错误码非0或code=0但respMsg含NOT_FOUND",
        "root_cause": "向下级匹配。",
        "fix_sugg": "向下级匹配。",
        "logic_type": "composite",
        "sources": ["08-fault-triage-consolidated.md L12-L14", "10-customer-fault-scenarios.md L40-L42"],
        "lines": "L82-L97",
        "cases": [
            {
                "type": "uniq_code",
                "cmd": 'grep "DS_KV_CLIENT_PUT\\|DS_KV_CLIENT_GET" $LOG/ds_client_access_*.log | awk -F\'|\' \'{print $1}\' | sort | uniq -c',
                "check": "has_nonzero_code",
                "desc": "在uniq -c输出中，第二列(code)有非0值"
            },
            {
                "type": "access_log",
                "cmd": 'grep "DS_KV_CLIENT_PUT\\|DS_KV_CLIENT_GET" $LOG/ds_client_access_*.log',
                "check": "code_zero_with_not_found",
                "desc": "code=0但respMsg含NOT_FOUND或Can't find object"
            }
        ]
    },
    {
        "id": "kvcache_conn_fault_002",
        "name": "用户侧错误",
        "children": ["kvcache_conn_fault_003", "kvcache_conn_fault_004", "kvcache_conn_fault_005", "kvcache_conn_fault_006", "kvcache_conn_fault_007"],
        "validation": "KVCache错误码为2(K_INVALID)、3(K_NOT_FOUND)或8(K_NOT_READY)",
        "root_cause": "向下级匹配。",
        "fix_sugg": "向下级匹配。",
        "logic_type": "uniq_code",
        "sources": ["08-fault-triage-consolidated.md L73-L74", "10-customer-fault-scenarios.md L78-L80"],
        "lines": "L99-L108",
        "codes": [2, 3, 8]
    },
    {
        "id": "kvcache_conn_fault_003",
        "name": "参数非法",
        "children": [],
        "validation": "access log错误码为2(K_INVALID)或INFO log含K_INVALID及参数校验失败描述",
        "root_cause": "业务参数非法",
        "fix_sugg": "业务校验",
        "logic_type": "composite",
        "sources": ["08-fault-triage-consolidated.md L175-L176", "10-customer-fault-scenarios.md L127-L130"],
        "lines": "L110-L127",
        "cases": [
            {
                "type": "access_log_field",
                "cmd": "grep '^2 |' $LOG/ds_client_access_*.log",
                "check": "field_contains",
                "field": "respMsg",
                "keywords": ["The objectKey is empty", "dataSize should be bigger than zero", "length not match"],
                "desc": "access log中code=2且respMsg含参数校验失败描述"
            },
            {
                "type": "grep",
                "cmd": "grep 'K_INVALID' $LOG/ds_client_*.INFO.log",
                "check": "non_empty",
                "desc": "INFO log含K_INVALID"
            }
        ]
    },
    {
        "id": "kvcache_conn_fault_004",
        "name": "未配置Init",
        "children": [],
        "validation": "INFO log含ConnectOptions was not configured",
        "root_cause": "未配置Init",
        "fix_sugg": "检查Init",
        "logic_type": "grep",
        "sources": ["08-fault-triage-consolidated.md L177", "10-customer-fault-scenarios.md L131-L132"],
        "lines": "L129-L138",
        "grep_keyword": "ConnectOptions was not configured"
    },
    {
        "id": "kvcache_conn_fault_005",
        "name": "buffer重复Publish",
        "children": [],
        "validation": "INFO log含Client object is already sealed",
        "root_cause": "buffer重复Publish",
        "fix_sugg": "检查业务逻辑",
        "logic_type": "grep",
        "sources": ["08-fault-triage-consolidated.md L178", "10-customer-fault-scenarios.md L133-L134"],
        "lines": "L140-L149",
        "grep_keyword": "Client object is already sealed"
    },
    {
        "id": "kvcache_conn_fault_006",
        "name": "批次超限",
        "children": [],
        "validation": "access log含OBJECT_KEYS_MAX_SIZE_LIMIT",
        "root_cause": "批次超限",
        "fix_sugg": "拆batch",
        "logic_type": "grep",
        "sources": ["08-fault-triage-consolidated.md L179", "10-customer-fault-scenarios.md L135-L136"],
        "lines": "L151-L160",
        "grep_keyword": "OBJECT_KEYS_MAX_SIZE_LIMIT"
    },
    {
        "id": "kvcache_conn_fault_007",
        "name": "对象不存在",
        "children": [],
        "validation": "INFO log含K_NOT_FOUND或Can't find object，或access log code=0但respMsg含NOT_FOUND",
        "root_cause": "对象不存在",
        "fix_sugg": "业务自查key；检查业务是否先Put再Get、key生成逻辑、TTL是否提前过期",
        "logic_type": "composite",
        "sources": ["08-fault-triage-consolidated.md L180", "10-customer-fault-scenarios.md L273-L280"],
        "lines": "L162-L183",
        "cases": [
            {
                "type": "grep",
                "cmd": "grep -E 'K_NOT_FOUND|Can.?t find object' $LOG/ds_client_*.INFO.log",
                "check": "non_empty",
                "desc": "INFO log含K_NOT_FOUND或Can't find object"
            },
            {
                "type": "access_log",
                "cmd": 'grep "DS_KV_CLIENT_GET" $LOG/ds_client_access_*.log',
                "check": "code_zero_with_not_found",
                "desc": "access log中code=0但respMsg含NOT_FOUND或Can't find object"
            }
        ]
    },
    {
        "id": "kvcache_conn_fault_008",
        "name": "DS进程内错误",
        "children": ["kvcache_conn_fault_009", "kvcache_conn_fault_010", "kvcache_conn_fault_011", "kvcache_conn_fault_012"],
        "validation": "KVCache错误码为19(K_TRY_AGAIN)、23(K_CLIENT_WORKER_DISCONNECT)、29(K_SERVER_FD_CLOSED)、31(K_SCALE_DOWN)或32(K_SCALING)",
        "root_cause": "向下级匹配。",
        "fix_sugg": "向下级匹配。",
        "logic_type": "uniq_code",
        "sources": ["08-fault-triage-consolidated.md L73-L74", "10-customer-fault-scenarios.md L78-L80"],
        "lines": "L185-L194",
        "codes": [19, 23, 29, 31, 32]
    },
    {
        "id": "kvcache_conn_fault_009",
        "name": "对端处理慢/拒绝",
        "children": [],
        "validation": "INFO log含[RPC_RECV_TIMEOUT]且ZMQ fault=0，或含[RPC_SERVICE_UNAVAILABLE]",
        "root_cause": "对端Worker处理慢或主动拒绝，线程池打满",
        "fix_sugg": "查Worker CPU/锁；扩oc_rpc_thread_num",
        "logic_type": "composite",
        "sources": ["08-fault-triage-consolidated.md L120-L121", "10-customer-fault-scenarios.md L172-L173"],
        "lines": "L196-L213",
        "cases": [
            {
                "type": "grep_and_metrics",
                "grep_cmd": "grep '\\[RPC_RECV_TIMEOUT\\]' $LOG/datasystem_worker.INFO.log $LOG/ds_client_*.INFO.log | tail -50",
                "metrics_check": "zmq_send_failure_total=+0",
                "desc": "[RPC_RECV_TIMEOUT]且ZMQ fault=0"
            },
            {
                "type": "grep",
                "cmd": "grep '\\[RPC_SERVICE_UNAVAILABLE\\]' $LOG/datasystem_worker.INFO.log $LOG/ds_client_*.INFO.log | tail -50",
                "check": "non_empty",
                "desc": "[RPC_SERVICE_UNAVAILABLE]"
            }
        ]
    },
    {
        "id": "kvcache_conn_fault_010",
        "name": "ZMQ相关问题（重建/断开/握手）",
        "children": [],
        "validation": "INFO log含zmq_gateway_recreate_total或zmq_event_disconnect_total或zmq_event_handshake_failure_total上升，且对端Worker仍活",
        "root_cause": "ZMQ连接重建/断开/握手失败。低频忽略（SDK自重连）；高频转OS查网络；握手失败查TLS/认证配置",
        "fix_sugg": "低频忽略；高频查OS网络；握手失败查TLS/认证配置",
        "logic_type": "composite",
        "sources": ["08-fault-triage-consolidated.md L196-L198"],
        "lines": "L215-L229",
        "cases": [
            {
                "type": "metrics_increased",
                "cmd": "grep -E 'zmq_gateway_recreate_total|zmq_event_disconnect_total|zmq_event_handshake_failure_total' $LOG/datasystem_worker.INFO.log | tail -50",
                "metrics": ["zmq_gateway_recreate_total", "zmq_event_disconnect_total", "zmq_event_handshake_failure_total"],
                "desc": "ZMQ相关指标上升"
            },
            {
                "type": "process_check",
                "cmd": "pgrep -af datasystem_worker",
                "check": "non_empty",
                "desc": "对端Worker仍活"
            }
        ]
    },
    {
        "id": "kvcache_conn_fault_011",
        "name": "三方etcd（信号出现在DS日志中）",
        "children": [],
        "validation": "INFO log含etcd is timeout或etcd is unavailable",
        "root_cause": "etcd集群或到etcd的网络异常。主责三方etcd",
        "fix_sugg": "systemctl status etcd；etcdctl endpoint status；查到etcd的网络",
        "logic_type": "grep",
        "sources": ["08-fault-triage-consolidated.md L199-L200", "10-customer-fault-scenarios.md L161-L162"],
        "lines": "L231-L244",
        "grep_keyword": "etcd is timeout|etcd is unavailable"
    },
    {
        "id": "kvcache_conn_fault_012",
        "name": "心跳/生命周期/扩缩容",
        "children": [],
        "validation": "INFO log含Cannot receive heartbeat from worker或HealthCheck Worker is exiting now或meta_is_moving",
        "root_cause": "心跳断→Worker被STOP；退出由编排拉起；扩缩容中SDK自重试",
        "fix_sugg": "心跳断→kill -CONT <pid>；退出由编排拉起；扩缩容SDK自重试",
        "logic_type": "grep",
        "sources": ["08-fault-triage-consolidated.md L202-L204", "10-customer-fault-scenarios.md L621-L632"],
        "lines": "L246-L258",
        "grep_keyword": "Cannot receive heartbeat from worker|Worker is exiting now|meta_is_moving"
    },
    {
        "id": "kvcache_conn_fault_013",
        "name": "三方etcd错误",
        "children": [],
        "validation": "KVCache错误码为25(K_MASTER_TIMEOUT)或INFO log含etcd is timeout/unavailable或resource log含ETCD_QUEUE堆积",
        "root_cause": "etcd集群故障或到etcd的网络异常。主责三方etcd",
        "fix_sugg": "systemctl status etcd；etcdctl endpoint status -w table；查到etcd的网络",
        "logic_type": "composite",
        "sources": ["08-fault-triage-consolidated.md L73-L74", "10-customer-fault-scenarios.md L161-L166"],
        "lines": "L260-L285",
        "cases": [
            {
                "type": "uniq_code",
                "cmd": 'grep "DS_KV_CLIENT_PUT\\|DS_KV_CLIENT_GET" $LOG/ds_client_access_*.log | awk -F\'|\' \'{print $1}\' | sort | uniq -c',
                "check": "has_code",
                "codes": [25],
                "desc": "返回错误码中有25"
            },
            {
                "type": "grep",
                "cmd": "grep -E 'etcd is timeout|etcd is unavailable' $LOG/*.INFO.log | tail -20",
                "check": "non_empty",
                "desc": "INFO log含etcd is timeout或etcd is unavailable"
            },
            {
                "type": "resource_log",
                "cmd": "grep 'ETCD_REQUEST_SUCCESS_RATE\\|ETCD_QUEUE' $LOG/resource.log | tail -5",
                "check": "etcd_queue_high",
                "desc": "ETCD_QUEUE堆积或ETCD_REQUEST_SUCCESS_RATE下降"
            }
        ]
    },
    {
        "id": "kvcache_conn_fault_014",
        "name": "桶码错误",
        "children": ["kvcache_conn_fault_015", "kvcache_conn_fault_020", "kvcache_conn_fault_021"],
        "validation": "KVCache错误码为1001(K_RPC_DEADLINE_EXCEEDED)或1002(K_RPC_UNAVAILABLE)，需看日志前缀确定边界",
        "root_cause": "向下级匹配。",
        "fix_sugg": "向下级匹配。",
        "logic_type": "uniq_code",
        "sources": ["08-fault-triage-consolidated.md L73-L76", "10-customer-fault-scenarios.md L78-L83"],
        "lines": "L287-L300",
        "codes": [1001, 1002]
    },
    {
        "id": "kvcache_conn_fault_015",
        "name": "OS层（TCP/UDS/ZMQ系统调用层）",
        "children": ["kvcache_conn_fault_016", "kvcache_conn_fault_017", "kvcache_conn_fault_018", "kvcache_conn_fault_019"],
        "validation": "INFO log含[TCP_CONNECT_FAILED]或[TCP_CONNECT_RESET]或[TCP_NETWORK_UNREACHABLE]或[UDS_CONNECT_FAILED]或[SHM_FD_TRANSFER_FAILED]或[ZMQ_SEND_FAILURE_TOTAL]或[ZMQ_RECEIVE_FAILURE_TOTAL]",
        "root_cause": "向下级匹配。",
        "fix_sugg": "向下级匹配。",
        "logic_type": "grep",
        "sources": ["08-fault-triage-consolidated.md L103-L110", "10-customer-fault-scenarios.md L169-L178"],
        "lines": "L302-L316",
        "grep_keyword": "\\[(TCP|UDS|ZMQ|SHM_FD)_"
    },
    {
        "id": "kvcache_conn_fault_016",
        "name": "TCP建连失败（对端Worker活）",
        "children": [],
        "validation": "INFO log含[TCP_CONNECT_FAILED]且对端Worker进程仍存活",
        "root_cause": "端口不通/iptables/路由",
        "fix_sugg": "ss -tnlp；iptables -L -n；开端口/删规则",
        "logic_type": "composite",
        "sources": ["08-fault-triage-consolidated.md L103-L104", "10-customer-fault-scenarios.md L169-L170"],
        "lines": "L318-L332",
        "cases": [
            {
                "type": "grep",
                "cmd": "grep '\\[TCP_CONNECT_FAILED\\]' $LOG/datasystem_worker.INFO.log $LOG/ds_client_*.INFO.log | tail -50",
                "check": "non_empty",
                "desc": "[TCP_CONNECT_FAILED]"
            },
            {
                "type": "process_check",
                "cmd": "pgrep -af datasystem_worker",
                "check": "non_empty",
                "desc": "对端Worker仍活"
            }
        ]
    },
    {
        "id": "kvcache_conn_fault_017",
        "name": "TCP连接重置/网络不可达",
        "children": [],
        "validation": "INFO log含[TCP_CONNECT_RESET]或[TCP_NETWORK_UNREACHABLE]",
        "root_cause": "网络闪断（除非同窗Worker重启）",
        "fix_sugg": "dmesg；netstat -s | grep reset",
        "logic_type": "grep",
        "sources": ["08-fault-triage-consolidated.md L105-L106", "10-customer-fault-scenarios.md L171-L172"],
        "lines": "L334-L344",
        "grep_keyword": "\\[TCP_CONNECT_RESET\\]|\\[TCP_NETWORK_UNREACHABLE\\]"
    },
    {
        "id": "kvcache_conn_fault_018",
        "name": "UDS/SHM传fd失败",
        "children": [],
        "validation": "INFO log含[UDS_CONNECT_FAILED]或[SHM_FD_TRANSFER_FAILED]",
        "root_cause": "同机UDS路径/权限/fd上限；SCM_RIGHTS发送失败多为fd耗尽或权限问题",
        "fix_sugg": "检查UDS路径/权限；调大ulimit -n",
        "logic_type": "grep",
        "sources": ["08-fault-triage-consolidated.md L107-L108", "10-customer-fault-scenarios.md L173-L174"],
        "lines": "L346-L365",
        "grep_keyword": "\\[UDS_CONNECT_FAILED\\]|\\[SHM_FD_TRANSFER_FAILED\\]"
    },
    {
        "id": "kvcache_conn_fault_019",
        "name": "ZMQ发送/接收失败",
        "children": [],
        "validation": "INFO log含[ZMQ_SEND_FAILURE_TOTAL]或[ZMQ_RECEIVE_FAILURE_TOTAL]，按zmq_last_error_number对照errno",
        "root_cause": "zmq_msg_send/recv硬失败，按zmq_last_error_number对照errno确定具体OS原因",
        "fix_sugg": "按errno对照处置。errno对照表：11(EAGAIN背压)、101(ENETUNREACH路由不可达)、104(ECONNRESET对端reset)、110(ETIMEDOUT TCP超时)、111(ECONNREFUSED端口无监听)、113(EHOSTUNREACH主机不可达)",
        "logic_type": "grep",
        "sources": ["08-fault-triage-consolidated.md L109-L110", "10-customer-fault-scenarios.md L175-L176"],
        "lines": "L367-L380",
        "grep_keyword": "\\[ZMQ_SEND_FAILURE_TOTAL\\]|\\[ZMQ_RECEIVE_FAILURE_TOTAL\\]"
    },
    {
        "id": "kvcache_conn_fault_020",
        "name": "三方etcd层",
        "children": [],
        "validation": "INFO log含etcd is timeout或etcd is unavailable",
        "root_cause": "etcd集群或到etcd的网络异常",
        "fix_sugg": "systemctl status etcd；etcdctl endpoint status；查到etcd的网络",
        "logic_type": "grep",
        "sources": ["08-fault-triage-consolidated.md L113-L114", "10-customer-fault-scenarios.md L161-L166"],
        "lines": "L382-L394",
        "grep_keyword": "etcd is timeout|etcd is unavailable"
    },
    {
        "id": "kvcache_conn_fault_021",
        "name": "DS进程内层",
        "children": [],
        "validation": "INFO log含[TCP_CONNECT_FAILED]且对端Worker不在，或含[RPC_RECV_TIMEOUT]且ZMQ fault=0，或含[RPC_SERVICE_UNAVAILABLE]",
        "root_cause": "Worker crash/未拉起/机器故障、对端处理慢拖超时、对端主动拒绝",
        "fix_sugg": "查对端Worker存活；扩线程池",
        "logic_type": "composite",
        "sources": ["08-fault-triage-consolidated.md L115-L119", "10-customer-fault-scenarios.md L169-L178"],
        "lines": "L396-L418",
        "cases": [
            {
                "type": "grep_and_process",
                "grep_cmd": "grep '\\[TCP_CONNECT_FAILED\\]' $LOG/datasystem_worker.INFO.log $LOG/ds_client_*.INFO.log | tail -50",
                "process_check": "pgrep -af datasystem_worker",
                "process_expected": "empty",
                "desc": "[TCP_CONNECT_FAILED]且对端Worker不在"
            },
            {
                "type": "grep_and_metrics",
                "grep_cmd": "grep -E '\\[RPC_RECV_TIMEOUT\\]|\\[RPC_SERVICE_UNAVAILABLE\\]' $LOG/datasystem_worker.INFO.log $LOG/ds_client_*.INFO.log | tail -50",
                "metrics_check": "zmq_send_failure_total=+0",
                "desc": "[RPC_RECV_TIMEOUT]且ZMQ fault=0或[RPC_SERVICE_UNAVAILABLE]"
            }
        ]
    },
    {
        "id": "kvcache_conn_fault_022",
        "name": "URMA错误",
        "children": ["kvcache_conn_fault_023", "kvcache_conn_fault_024", "kvcache_conn_fault_025", "kvcache_conn_fault_026", "kvcache_conn_fault_027", "kvcache_conn_fault_028", "kvcache_conn_fault_029", "kvcache_conn_fault_030"],
        "validation": "KVCache错误码为1004/1006/1008/1009/1010",
        "root_cause": "向下级匹配。",
        "fix_sugg": "向下级匹配。",
        "logic_type": "uniq_code",
        "sources": ["08-fault-triage-consolidated.md L73-L74", "10-customer-fault-scenarios.md L78-L80"],
        "lines": "L420-L429",
        "codes": [1004, 1006, 1008, 1009, 1010]
    },
    {
        "id": "kvcache_conn_fault_023",
        "name": "URMA会话重连",
        "children": [],
        "validation": "INFO log含[URMA_NEED_CONNECT]或[URMA_RECREATE_JFS]",
        "root_cause": "对端Worker重启（instanceId变化）或UB链路不稳（instanceId不变）",
        "fix_sugg": "对端重启→等SDK自重连稳定；UB链路不稳→查UB硬件/驱动/端口/交换机抖动",
        "logic_type": "composite",
        "sources": ["08-fault-triage-consolidated.md L214-L217", "10-customer-fault-scenarios.md L148-L156"],
        "lines": "L431-L455",
        "cases": [
            {
                "type": "grep",
                "cmd": "grep '\\[URMA_NEED_CONNECT\\]' $LOG/datasystem_worker.INFO.log $LOG/ds_client_*.INFO.log | tail -50",
                "check": "non_empty",
                "desc": "[URMA_NEED_CONNECT]"
            }
        ]
    },
    {
        "id": "kvcache_conn_fault_024",
        "name": "URMA JFS异常",
        "children": [],
        "validation": "INFO log含Failed to import jfr或advise jfr",
        "root_cause": "JFS异常自动重建（cqeStatus=9 ACK TIMEOUT）；JFS重建失败",
        "fix_sugg": "无[URMA_RECREATE_JFS_FAILED]→自愈成功；有且连续→查UMDK/驱动日志并上报URMA团队",
        "logic_type": "composite",
        "sources": ["08-fault-triage-consolidated.md L218-L221"],
        "lines": "L457-L475",
        "cases": [
            {
                "type": "grep",
                "cmd": "grep '\\[URMA_RECREATE_JFS\\]' $LOG/datasystem_worker.INFO.log $LOG/ds_client_*.INFO.log | tail -50",
                "check": "non_empty",
                "desc": "[URMA_RECREATE_JFS]"
            },
            {
                "type": "grep",
                "cmd": "grep '\\[URMA_RECREATE_JFS_FAILED\\]' $LOG/datasystem_worker.INFO.log $LOG/ds_client_*.INFO.log | tail -50",
                "check": "non_empty",
                "desc": "[URMA_RECREATE_JFS_FAILED]"
            }
        ]
    },
    {
        "id": "kvcache_conn_fault_025",
        "name": "URMA驱动/CQ错误",
        "children": [],
        "validation": "INFO log含URMA CQ error或URMA driver error",
        "root_cause": "PollJfcWait报错（驱动/硬件）或等待CQE超时",
        "fix_sugg": "grep UMDK日志/dmesg；SDK重试白名单自愈",
        "logic_type": "grep",
        "sources": ["08-fault-triage-consolidated.md L226-L229", "10-customer-fault-scenarios.md L148-L158"],
        "lines": "L477-L495",
        "grep_keyword": "\\[URMA_POLL_ERROR\\]|\\[URMA_WAIT_TIMEOUT\\]"
    },
    {
        "id": "kvcache_conn_fault_026",
        "name": "URMA建连失败",
        "children": [],
        "validation": "KVCache错误码为1009或INFO log含[URMA_CONNECT_FAILED]",
        "root_cause": "URMA建连失败，UB端口down或设备节点缺失",
        "fix_sugg": "ifconfig ub0 up；检查UB设备节点",
        "logic_type": "composite",
        "sources": ["08-fault-triage-consolidated.md L230-L231", "10-customer-fault-scenarios.md L148-L149"],
        "lines": "L497-L520",
        "cases": [
            {
                "type": "uniq_code",
                "cmd": 'grep "DS_KV_CLIENT_PUT\\|DS_KV_CLIENT_GET" $LOG/ds_client_access_*.log | awk -F\'|\' \'{print $1}\' | sort | uniq -c',
                "check": "has_code",
                "codes": [1009],
                "desc": "返回错误码中有1009"
            },
            {
                "type": "cmd_check",
                "cmd": "ifconfig ub0 2>/dev/null",
                "check": "contains_down",
                "desc": "UB端口down"
            },
            {
                "type": "cmd_check",
                "cmd": "ls /dev/ub* 2>/dev/null",
                "check": "empty",
                "desc": "UB设备节点缺失"
            }
        ]
    },
    {
        "id": "kvcache_conn_fault_027",
        "name": "URMA初始化失败",
        "children": [],
        "validation": "INFO log含Failed to urma init或Failed to urma get device by name或Failed to urma get eid list或Failed to urma create context或Failed to initialize URMA dlopen loader",
        "root_cause": "UB初始化失败（UMDK设备/context/jfc等）",
        "fix_sugg": "UB/URMA运维排查",
        "logic_type": "grep",
        "sources": ["03-fault-mode-library.md L56-L57", "10-customer-fault-scenarios.md L148-L149"],
        "lines": "L522-L534",
        "grep_keyword": "Failed to urma init|Failed to urma get device by name|Failed to urma get eid list|Failed to urma create context|Failed to initialize URMA dlopen loader"
    },
    {
        "id": "kvcache_conn_fault_028",
        "name": "FastTransport/握手失败",
        "children": [],
        "validation": "INFO log含Fast transport handshake failed或Failed to import jfr或advise jfr",
        "root_cause": "UB握手失败、回退",
        "fix_sugg": "UB/URMA运维排查",
        "logic_type": "grep",
        "sources": ["03-fault-mode-library.md L60-L61", "03-fault-mode-library.md L95-L96"],
        "lines": "L536-L548",
        "grep_keyword": "Fast transport handshake failed|Failed to import jfr|advise jfr"
    },
    {
        "id": "kvcache_conn_fault_029",
        "name": "URMA数据面读写失败",
        "children": [],
        "validation": "INFO log含Failed to urma write object或Failed to urma read object",
        "root_cause": "读写到对端UB失败",
        "fix_sugg": "UB/URMA运维排查",
        "logic_type": "grep",
        "sources": ["03-fault-mode-library.md L64-L65", "03-fault-mode-library.md L95-L96"],
        "lines": "L550-L561",
        "grep_keyword": "Failed to urma write object|Failed to urma read object"
    },
    {
        "id": "kvcache_conn_fault_030",
        "name": "URMA超时",
        "children": [],
        "validation": "KVCache错误码为1010或INFO log含[URMA_WAIT_TIMEOUT]",
        "root_cause": "URMA等待CQE超时",
        "fix_sugg": "SDK重试白名单自愈；持续出现查UB链路",
        "logic_type": "composite",
        "sources": ["08-fault-triage-consolidated.md L228-L229"],
        "lines": "L497-L498（从1.5.4上下文推断）",
        "cases": [
            {
                "type": "uniq_code",
                "cmd": 'grep "DS_KV_CLIENT_PUT\\|DS_KV_CLIENT_GET" $LOG/ds_client_access_*.log | awk -F\'|\' \'{print $1}\' | sort | uniq -c',
                "check": "has_code",
                "codes": [1010],
                "desc": "返回错误码中有1010"
            },
            {
                "type": "grep",
                "cmd": "grep '\\[URMA_WAIT_TIMEOUT\\]' $LOG/datasystem_worker.INFO.log $LOG/ds_client_*.INFO.log | tail -50",
                "check": "non_empty",
                "desc": "[URMA_WAIT_TIMEOUT]"
            }
        ]
    },
    {
        "id": "kvcache_conn_fault_031",
        "name": "OS错误",
        "children": ["kvcache_conn_fault_032", "kvcache_conn_fault_033", "kvcache_conn_fault_034", "kvcache_conn_fault_035", "kvcache_conn_fault_036", "kvcache_conn_fault_037"],
        "validation": "KVCache错误码为5(K_RUNTIME_ERROR)、6(K_OUT_OF_MEMORY)、7(K_IO_ERROR)、13(K_NO_SPACE)或18(K_FILE_LIMIT_REACHED)",
        "root_cause": "向下级匹配。",
        "fix_sugg": "向下级匹配。",
        "logic_type": "uniq_code",
        "sources": ["08-fault-triage-consolidated.md L73-L74", "10-customer-fault-scenarios.md L78-L80"],
        "lines": "L563-L572",
        "codes": [5, 6, 7, 13, 18]
    },
    {
        "id": "kvcache_conn_fault_032",
        "name": "内存不足",
        "children": [],
        "validation": "KVCache错误码为6(K_OUT_OF_MEMORY)或dmesg含Out of memory或free -h可用内存不足",
        "root_cause": "OS内存不足（ENOMEM）",
        "fix_sugg": "扩内存/调cgroup上限",
        "logic_type": "composite",
        "sources": ["08-fault-triage-consolidated.md L226-L227", "10-customer-fault-scenarios.md L139-L140"],
        "lines": "L574-L596",
        "cases": [
            {
                "type": "uniq_code",
                "cmd": 'grep "DS_KV_CLIENT_PUT\\|DS_KV_CLIENT_GET" $LOG/ds_client_access_*.log | awk -F\'|\' \'{print $1}\' | sort | uniq -c',
                "check": "has_code",
                "codes": [6],
                "desc": "返回错误码中有6"
            },
            {
                "type": "cmd_check",
                "cmd": "dmesg | grep -i 'Out of memory'",
                "check": "non_empty",
                "desc": "dmesg含Out of memory"
            },
            {
                "type": "cmd_check",
                "cmd": "free -h",
                "check": "memory_low",
                "desc": "可用内存不足"
            }
        ]
    },
    {
        "id": "kvcache_conn_fault_033",
        "name": "IO错误",
        "children": [],
        "validation": "KVCache错误码为7(K_IO_ERROR)或dmesg含块设备/文件系统错误",
        "root_cause": "块设备/文件系统IO错误（EIO）",
        "fix_sugg": "修文件系统/挂载；分布式网盘故障联系存储运维",
        "logic_type": "composite",
        "sources": ["08-fault-triage-consolidated.md L226-L227", "10-customer-fault-scenarios.md L139-L140"],
        "lines": "L598-L616",
        "cases": [
            {
                "type": "uniq_code",
                "cmd": 'grep "DS_KV_CLIENT_PUT\\|DS_KV_CLIENT_GET" $LOG/ds_client_access_*.log | awk -F\'|\' \'{print $1}\' | sort | uniq -c',
                "check": "has_code",
                "codes": [7],
                "desc": "返回错误码中有7"
            },
            {
                "type": "cmd_check",
                "cmd": "dmesg | grep 'I/O error'",
                "check": "non_empty",
                "desc": "dmesg含I/O error"
            }
        ]
    },
    {
        "id": "kvcache_conn_fault_034",
        "name": "磁盘空间不足",
        "children": [],
        "validation": "KVCache错误码为13(K_NO_SPACE)或df -h磁盘使用率接近100%或resource log含SPILL_HARD_DISK/SHARED_DISK空间接近TOTAL_LIMIT",
        "root_cause": "磁盘空间不足（ENOSPC）",
        "fix_sugg": "清理/扩容（本地盘或分布式网盘挂载点）",
        "logic_type": "composite",
        "sources": ["08-fault-triage-consolidated.md L226-L227", "10-customer-fault-scenarios.md L139-L140"],
        "lines": "L618-L642",
        "cases": [
            {
                "type": "uniq_code",
                "cmd": 'grep "DS_KV_CLIENT_PUT\\|DS_KV_CLIENT_GET" $LOG/ds_client_access_*.log | awk -F\'|\' \'{print $1}\' | sort | uniq -c',
                "check": "has_code",
                "codes": [13],
                "desc": "返回错误码中有13"
            },
            {
                "type": "cmd_check",
                "cmd": "df -h",
                "check": "disk_usage_high",
                "desc": "磁盘使用率接近100%"
            },
            {
                "type": "resource_log",
                "cmd": "grep -E 'SPILL_HARD_DISK|SHARED_DISK' $LOG/resource.log | tail -5",
                "check": "disk_space_near_limit",
                "desc": "SPILL_HARD_DISK或SHARED_DISK空间接近TOTAL_LIMIT"
            }
        ]
    },
    {
        "id": "kvcache_conn_fault_035",
        "name": "文件描述符耗尽",
        "children": [],
        "validation": "KVCache错误码为18(K_FILE_LIMIT_REACHED)或fd数量接近ulimit -n的值",
        "root_cause": "文件描述符耗尽（EMFILE/ENFILE）",
        "fix_sugg": "ulimit -n 65535（永久改/etc/security/limits.conf）",
        "logic_type": "composite",
        "sources": ["08-fault-triage-consolidated.md L226-L227", "10-customer-fault-scenarios.md L139-L140"],
        "lines": "L644-L666",
        "cases": [
            {
                "type": "uniq_code",
                "cmd": 'grep "DS_KV_CLIENT_PUT\\|DS_KV_CLIENT_GET" $LOG/ds_client_access_*.log | awk -F\'|\' \'{print $1}\' | sort | uniq -c',
                "check": "has_code",
                "codes": [18],
                "desc": "返回错误码中有18"
            },
            {
                "type": "cmd_check",
                "cmd": "ls /proc/$(pgrep -f datasystem_worker | head -1)/fd 2>/dev/null | wc -l",
                "check": "fd_near_limit",
                "desc": "fd数量接近ulimit -n的值"
            }
        ]
    },
    {
        "id": "kvcache_conn_fault_036",
        "name": "mmap失败",
        "children": [],
        "validation": "KVCache错误码为5(K_RUNTIME_ERROR)且INFO log含Get mmap entry failed",
        "root_cause": "mlock限制导致mmap失败（ENOMEM）",
        "fix_sugg": "ulimit -l unlimited",
        "logic_type": "composite",
        "sources": ["08-fault-triage-consolidated.md L86-L87", "08-fault-triage-consolidated.md L233-L234"],
        "lines": "L668-L688",
        "cases": [
            {
                "type": "uniq_code",
                "cmd": 'grep "DS_KV_CLIENT_PUT\\|DS_KV_CLIENT_GET" $LOG/ds_client_access_*.log | awk -F\'|\' \'{print $1}\' | sort | uniq -c',
                "check": "has_code",
                "codes": [5],
                "desc": "返回错误码中有5"
            },
            {
                "type": "grep",
                "cmd": "grep 'Get mmap entry failed' $LOG/datasystem_worker.INFO.log | tail -50",
                "check": "non_empty",
                "desc": "INFO log含Get mmap entry failed"
            },
            {
                "type": "cmd_check",
                "cmd": "ulimit -l",
                "check": "not_unlimited",
                "desc": "mlock限制值"
            }
        ]
    },
    {
        "id": "kvcache_conn_fault_037",
        "name": "code=5按日志串细分",
        "children": [],
        "validation": "KVCache错误码为5(K_RUNTIME_ERROR)且需按日志串细分",
        "root_cause": "向下级匹配。",
        "fix_sugg": "向下级匹配。",
        "logic_type": "uniq_code",
        "sources": ["08-fault-triage-consolidated.md L86-L89"],
        "lines": "L690-L703",
        "codes": [5]
    },
    {
        "id": "kvcache_conn_fault_038",
        "name": "Client Init/连接Worker失败",
        "children": ["kvcache_conn_fault_039", "kvcache_conn_fault_040", "kvcache_conn_fault_041", "kvcache_conn_fault_042", "kvcache_conn_fault_043"],
        "validation": "INFO log含[TCP_CONNECT_FAILED]或[UDS_CONNECT_FAILED]或[SHM_FD_TRANSFER_FAILED]或ConnectOptions was not configured",
        "root_cause": "向下级匹配。",
        "fix_sugg": "向下级匹配。",
        "logic_type": "grep",
        "sources": ["10-customer-fault-scenarios.md L539-L540", "10-customer-fault-scenarios.md L548-L549"],
        "lines": "L705-L720",
        "grep_keyword": "\\[(TCP|UDS|SHM_FD)_|ConnectOptions was not configured"
    },
    {
        "id": "kvcache_conn_fault_039",
        "name": "Worker进程不存在",
        "children": [],
        "validation": "pgrep -af datasystem_worker无结果",
        "root_cause": "DataSystem/编排问题，Worker未拉起",
        "fix_sugg": "联系华为DS支持或编排侧拉起（systemd/k8s查重启原因：kubectl describe / journalctl -u ...）",
        "logic_type": "cmd_check",
        "sources": ["10-customer-fault-scenarios.md L513-L514"],
        "lines": "L722-L730",
        "cmd": "pgrep -af datasystem_worker",
        "expected": "empty"
    },
    {
        "id": "kvcache_conn_fault_040",
        "name": "Worker端口未LISTEN",
        "children": [],
        "validation": "ss -tnlp | grep <worker_port>无结果但Worker进程在",
        "root_cause": "DataSystem问题",
        "fix_sugg": "上报华为DS支持",
        "logic_type": "composite",
        "sources": ["10-customer-fault-scenarios.md L513-L514"],
        "lines": "L732-L743",
        "cases": [
            {
                "type": "process_check",
                "cmd": "pgrep -af datasystem_worker",
                "check": "non_empty",
                "desc": "Worker进程存在"
            },
            {
                "type": "cmd_check",
                "cmd": "ss -tnlp | grep 31402",
                "check": "empty",
                "desc": "端口未LISTEN"
            }
        ]
    },
    {
        "id": "kvcache_conn_fault_041",
        "name": "TCP建连失败（对端LISTEN）",
        "children": [],
        "validation": "INFO log含[TCP_CONNECT_FAILED]且对端端口LISTEN",
        "root_cause": "主机/网络，防火墙/路由不通",
        "fix_sugg": "iptables -L -n；nc -zv <worker> <port>；删除iptables DROP规则；检查安全组",
        "logic_type": "composite",
        "sources": ["10-customer-fault-scenarios.md L539-L540"],
        "lines": "L745-L758",
        "cases": [
            {
                "type": "grep",
                "cmd": "grep '\\[TCP_CONNECT_FAILED\\]' $LOG/ds_client_<pid>.INFO.log | head",
                "check": "non_empty",
                "desc": "[TCP_CONNECT_FAILED]"
            },
            {
                "type": "cmd_check",
                "cmd": "ss -tnlp | grep 31402",
                "check": "non_empty",
                "desc": "对端端口LISTEN"
            }
        ]
    },
    {
        "id": "kvcache_conn_fault_042",
        "name": "UDS路径/权限问题",
        "children": [],
        "validation": "INFO log含[UDS_CONNECT_FAILED]",
        "root_cause": "主机，同机UDS路径/权限/tenant_id不一致",
        "fix_sugg": "ls -la <uds_path>检查路径与权限；改权限/按部署文档挂载",
        "logic_type": "grep",
        "sources": ["10-customer-fault-scenarios.md L539-L540"],
        "lines": "L760-L770",
        "grep_keyword": "\\[UDS_CONNECT_FAILED\\]"
    },
    {
        "id": "kvcache_conn_fault_043",
        "name": "SHM传fd失败",
        "children": [],
        "validation": "INFO log含[SHM_FD_TRANSFER_FAILED]",
        "root_cause": "同机SHM fd传输失败，fd耗尽或权限问题",
        "fix_sugg": "检查ulimit -n；SELinux/AppArmor；/proc/sys/fs/file-max",
        "logic_type": "grep",
        "sources": ["10-customer-fault-scenarios.md L539-L540"],
        "lines": "L770-L775（从1.4.1.3上下文推断）",
        "grep_keyword": "\\[SHM_FD_TRANSFER_FAILED\\]"
    },
    {
        "id": "kvcache_conn_fault_044",
        "name": "机器/节点级故障",
        "children": ["kvcache_conn_fault_045", "kvcache_conn_fault_046", "kvcache_conn_fault_047", "kvcache_conn_fault_048", "kvcache_conn_fault_049", "kvcache_conn_fault_050"],
        "validation": "INFO log含大量K_CLIENT_WORKER_DISCONNECT(23)/K_RPC_UNAVAILABLE(1002)/Cannot receive heartbeat from worker聚集在某节点",
        "root_cause": "向下级匹配。",
        "fix_sugg": "向下级匹配。",
        "logic_type": "grep",
        "sources": ["10-customer-fault-scenarios.md L676-L677"],
        "lines": "L777-L788",
        "grep_keyword": "Cannot receive heartbeat from worker|K_CLIENT_WORKER_DISCONNECT"
    },
    {
        "id": "kvcache_conn_fault_045",
        "name": "节点不可达",
        "children": [],
        "validation": "ping -c 3 <node_ip>不通",
        "root_cause": "主机/基础设施，联系机房/云平台",
        "fix_sugg": "联系机房/云平台",
        "logic_type": "cmd_check",
        "sources": ["10-customer-fault-scenarios.md L684-L687"],
        "lines": "L790-L798",
        "cmd": "ping -c 3 <node_ip>",
        "expected": "unreachable"
    },
    {
        "id": "kvcache_conn_fault_046",
        "name": "节点NotReady（k8s）",
        "children": [],
        "validation": "kubectl describe node含taints/conditions异常",
        "root_cause": "编排/主机问题",
        "fix_sugg": "编排/主机运维排查",
        "logic_type": "cmd_check",
        "sources": ["10-customer-fault-scenarios.md L686-L687"],
        "lines": "L800-L808",
        "cmd": "kubectl describe node <n>",
        "expected": "not_ready"
    },
    {
        "id": "kvcache_conn_fault_047",
        "name": "Worker进程被OOM Killer杀掉",
        "children": [],
        "validation": "dmesg含OOM killer杀掉datasystem_worker",
        "root_cause": "主机OOM",
        "fix_sugg": "扩内存/调cgroup；补内存后编排拉起",
        "logic_type": "composite",
        "sources": ["10-customer-fault-scenarios.md L694-L699"],
        "lines": "L810-L826",
        "cases": [
            {
                "type": "cmd_check",
                "cmd": "pgrep -af datasystem_worker",
                "check": "empty",
                "desc": "Worker进程不存在"
            },
            {
                "type": "cmd_check",
                "cmd": "dmesg | grep 'OOM killer'",
                "check": "non_empty",
                "desc": "dmesg含OOM killer"
            },
            {
                "type": "cmd_check",
                "cmd": "dmesg | grep datasystem_worker",
                "check": "non_empty",
                "desc": "dmesg含datasystem_worker"
            }
        ]
    },
    {
        "id": "kvcache_conn_fault_048",
        "name": "Worker进程crash（非OOM）",
        "children": [],
        "validation": "Worker进程不存在且dmesg无OOM记录",
        "root_cause": "DataSystem进程crash",
        "fix_sugg": "上报华为+附journalctl/core dump",
        "logic_type": "composite",
        "sources": ["10-customer-fault-scenarios.md L694-L699"],
        "lines": "L828-L844",
        "cases": [
            {
                "type": "cmd_check",
                "cmd": "pgrep -af datasystem_worker",
                "check": "empty",
                "desc": "Worker进程不存在"
            },
            {
                "type": "cmd_check",
                "cmd": "dmesg | grep 'OOM killer'",
                "check": "empty",
                "desc": "dmesg无OOM记录"
            }
        ]
    },
    {
        "id": "kvcache_conn_fault_049",
        "name": "Worker进程在但端口不LISTEN",
        "children": [],
        "validation": "Worker进程在但ss -tnlp无端口LISTEN",
        "root_cause": "DataSystem问题",
        "fix_sugg": "上报华为DS支持",
        "logic_type": "composite",
        "sources": ["10-customer-fault-scenarios.md L698-L699"],
        "lines": "L846-L857",
        "cases": [
            {
                "type": "cmd_check",
                "cmd": "pgrep -af datasystem_worker",
                "check": "non_empty",
                "desc": "Worker进程存在"
            },
            {
                "type": "cmd_check",
                "cmd": "ss -tnlp | grep 31402",
                "check": "empty",
                "desc": "端口未LISTEN"
            }
        ]
    },
    {
        "id": "kvcache_conn_fault_050",
        "name": "Worker进程在、端口LISTEN但心跳断",
        "children": [],
        "validation": "Worker进程在、端口LISTEN但业务心跳断",
        "root_cause": "主机/网络（中间网络路径）",
        "fix_sugg": "查iptables/路由/MTU",
        "logic_type": "composite",
        "sources": ["10-customer-fault-scenarios.md L698-L699"],
        "lines": "L859-L873",
        "cases": [
            {
                "type": "cmd_check",
                "cmd": "pgrep -af datasystem_worker",
                "check": "non_empty",
                "desc": "Worker进程存在"
            },
            {
                "type": "cmd_check",
                "cmd": "ss -tnlp | grep 31402",
                "check": "non_empty",
                "desc": "端口LISTEN"
            },
            {
                "type": "grep",
                "cmd": "grep 'Cannot receive heartbeat from worker' $LOG/datasystem_worker.INFO.log | tail -50",
                "check": "non_empty",
                "desc": "心跳断"
            }
        ]
    }
]


def file_name_from_id(fault_id):
    """Convert fault ID like kvcache_conn_fault_001 to file name like kvcache_conn_fault_001."""
    return fault_id


def class_name_from_id(fault_id):
    """Convert fault ID like kvcache_conn_fault_001 to class name like KvcacheConnFault001."""
    parts = fault_id.split('_')
    return ''.join(p.capitalize() for p in parts)


def is_leaf(fm):
    """Check if a fault mode is a leaf node (no children)."""
    return len(fm.get("children", [])) == 0


def generate_header(fm):
    """Generate .h file content for a fault mode."""
    cn = class_name_from_id(fm["id"])
    fn = file_name_from_id(fm["id"])
    lines = []
    lines.append("#pragma once")
    lines.append("")
    lines.append("#include \"../failure_mode.h\"")
    lines.append("namespace diag {")
    lines.append(f"class {cn} : public FailureMode {{")
    lines.append("public:")
    lines.append(f"    {cn}() noexcept;")
    lines.append("    bool IsValid() override;")
    lines.append("    std::string GetName() const override;")
    lines.append("    std::string GetRootCauseDesc() const override;")
    lines.append("    RootCause AnalyzeRootCause() override;")
    lines.append("    std::string GetFixSuggDesc() const override;")
    lines.append("    std::string GetValidationMethodDesc() const override;")
    lines.append("    std::string GetId() const override;")
    lines.append("};")
    lines.append("}")
    return "\n".join(lines)


def generate_validation_code(fm):
    """Generate IsValid() implementation based on logic_type."""
    lt = fm["logic_type"]
    lines = []
    lines.append("    // 来源: references/kvcache_conn_fault_mode.md " + fm.get("lines", ""))
    for src in fm.get("sources", []):
        lines.append("    // 来源: " + src)

    if lt == "uniq_code":
        codes_str = ", ".join(str(c) for c in fm.get("codes", []))
        lines.append("    // 验证方法: " + fm["validation"])
        lines.append("    // 匹配逻辑: 在uniq -c输出中，第二列(code)有" + codes_str)
        lines.append('    std::string uniqOutput = kvcache_conn_utils::RunCommand(')
        lines.append('        R"(grep "DS_KV_CLIENT_PUT\\\\|DS_KV_CLIENT_GET" $LOG/ds_client_access_*.log')
        lines.append('            | awk -F\'|\' \'{print $1}\' | sort | uniq -c)");')
        lines.append(f"    return kvcache_conn_utils::HasCodeInUniqOutput(uniqOutput, {{{codes_str}}});")

    elif lt == "grep":
        kw = fm.get("grep_keyword", "")
        lines.append("    // 验证方法: " + fm["validation"])
        lines.append("    // 匹配逻辑: grep `" + kw.replace("|", "`或`") + "` 输出非空")
        lines.append('    std::string grepOutput = kvcache_conn_utils::RunCommand(')
        lines.append(f'        R"(grep -E \'{kw}\' $LOG/datasystem_worker.INFO.log $LOG/ds_client_*.INFO.log 2>/dev/null)");')
        lines.append("    return !grepOutput.empty();")

    elif lt == "cmd_check":
        expected = fm.get("expected", "non_empty")
        cmd = fm.get("cmd", "")
        lines.append("    // 验证方法: " + fm["validation"])
        lines.append(f"    // 匹配逻辑: 运行`{cmd}`")
        lines.append('    std::string output = kvcache_conn_utils::RunCommand(')
        lines.append(f'        R"({cmd} 2>/dev/null)");')
        if expected == "empty":
            lines.append("    return output.empty();")
        elif expected == "non_empty":
            lines.append("    return !output.empty();")
        elif expected == "unreachable":
            lines.append("    return output.find(\"unreachable\") != std::string::npos;")
        elif expected == "not_ready":
            lines.append("    return output.find(\"NotReady\") != std::string::npos;")
        else:
            lines.append("    return !output.empty();")

    elif lt == "composite":
        cases = fm.get("cases", [])
        conditions = []
        for i, case in enumerate(cases):
            case_type = case.get("type", "")
            if case_type == "uniq_code":
                check_type = case.get("check", "")
                codes = case.get("codes", [])
                conditions.append(f"case{i}_matched")
                lines.append(f"    // Case {i+1}: {case['desc']}")
                lines.append(f"    // 来源: references/kvcache_conn_fault_mode.md {fm.get('lines', '')}")
                lines.append('    std::string uniqOutput' + str(i) + ' = kvcache_conn_utils::RunCommand(')
                lines.append('        R"(grep "DS_KV_CLIENT_PUT\\\\|DS_KV_CLIENT_GET" $LOG/ds_client_access_*.log')
                lines.append('            | awk -F\'|\' \'{print $1}\' | sort | uniq -c)");')
                if check_type == "has_nonzero_code":
                    lines.append(f"    bool case{i}_matched = kvcache_conn_utils::HasNonZeroCode(uniqOutput{i});")
                else:
                    codes_str = ", ".join(str(c) for c in codes)
                    lines.append(f"    bool case{i}_matched = kvcache_conn_utils::HasCodeInUniqOutput(uniqOutput{i}, {{{codes_str}}});")
            elif case_type == "grep":
                cmd = case.get("cmd", "")
                conditions.append(f"case{i}_matched")
                lines.append(f"    // Case {i+1}: {case['desc']}")
                lines.append(f"    // 来源: references/kvcache_conn_fault_mode.md {fm.get('lines', '')}")
                lines.append('    std::string grepOutput' + str(i) + ' = kvcache_conn_utils::RunCommand(')
                lines.append(f'        R"({cmd} 2>/dev/null)");')
                lines.append(f"    bool case{i}_matched = !grepOutput{i}.empty();")
            elif case_type == "access_log":
                conditions.append(f"case{i}_matched")
                lines.append(f"    // Case {i+1}: {case['desc']}")
                lines.append(f"    // 来源: references/kvcache_conn_fault_mode.md {fm.get('lines', '')}")
                lines.append('    std::string accessOutput' + str(i) + ' = kvcache_conn_utils::RunCommand(')
                lines.append(f'        R"({case["cmd"]} 2>/dev/null)");')
                lines.append(f"    bool case{i}_matched = kvcache_conn_utils::HasCodeZeroWithNotFound(accessOutput{i});")
            elif case_type == "access_log_field":
                conditions.append(f"case{i}_matched")
                lines.append(f"    // Case {i+1}: {case['desc']}")
                lines.append(f"    // 来源: references/kvcache_conn_fault_mode.md {fm.get('lines', '')}")
                lines.append('    std::string accessOutput' + str(i) + ' = kvcache_conn_utils::RunCommand(')
                lines.append(f'        R"({case["cmd"]} 2>/dev/null)");')
                keywords_str = " || ".join(f'accessOutput{i}.find("{kw}") != std::string::npos' for kw in case.get("keywords", []))
                lines.append(f"    bool case{i}_matched = {keywords_str};")
            elif case_type == "process_check":
                conditions.append(f"case{i}_matched")
                lines.append(f"    // Case {i+1}: {case['desc']}")
                lines.append(f"    // 来源: references/kvcache_conn_fault_mode.md {fm.get('lines', '')}")
                lines.append(f"    bool case{i}_matched = kvcache_conn_utils::ProcessExists(\"datasystem_worker\");")
            elif case_type == "cmd_check":
                conditions.append(f"case{i}_matched")
                chk = case.get("check", "non_empty")
                cmd = case.get("cmd", "")
                lines.append(f"    // Case {i+1}: {case['desc']}")
                lines.append(f"    // 来源: references/kvcache_conn_fault_mode.md {fm.get('lines', '')}")
                lines.append('    std::string cmdOutput' + str(i) + ' = kvcache_conn_utils::RunCommand(')
                lines.append(f'        R"({cmd} 2>/dev/null)");')
                if chk == "non_empty":
                    lines.append(f"    bool case{i}_matched = !cmdOutput{i}.empty();")
                elif chk == "empty":
                    lines.append(f"    bool case{i}_matched = cmdOutput{i}.empty();")
                elif chk == "contains_down":
                    lines.append(f"    bool case{i}_matched = cmdOutput{i}.find(\"DOWN\") != std::string::npos;")
                elif chk == "memory_low":
                    lines.append(f"    // Warning: memory_low check requires baseline comparison, simplified to non-empty")
                    lines.append(f"    bool case{i}_matched = !cmdOutput{i}.empty();")
                elif chk == "disk_usage_high":
                    lines.append(f"    // Warning: disk_usage_high check requires parsing df output for Use% >= 95%")
                    lines.append(f"    bool case{i}_matched = !cmdOutput{i}.empty();")
                elif chk == "not_unlimited":
                    lines.append(f"    bool case{i}_matched = cmdOutput{i}.find(\"unlimited\") == std::string::npos;")
                elif chk == "fd_near_limit":
                    lines.append(f"    // Warning: fd_near_limit requires comparing fd count with ulimit -n")
                    lines.append(f"    bool case{i}_matched = !cmdOutput{i}.empty();")
                else:
                    lines.append(f"    bool case{i}_matched = !cmdOutput{i}.empty();")
            elif case_type == "grep_and_metrics":
                conditions.append(f"case{i}_matched")
                lines.append(f"    // Case {i+1}: {case['desc']}")
                lines.append(f"    // 来源: references/kvcache_conn_fault_mode.md {fm.get('lines', '')}")
                lines.append('    std::string grepOut' + str(i) + ' = kvcache_conn_utils::RunCommand(')
                lines.append(f'        R"({case["grep_cmd"]} 2>/dev/null)");')
                lines.append(f"    bool case{i}_matched = !grepOut{i}.empty();")
                lines.append(f"    // Warning: ZMQ fault=0 check requires parsing Metrics Summary section")
            elif case_type == "grep_and_process":
                conditions.append(f"case{i}_matched")
                lines.append(f"    // Case {i+1}: {case['desc']}")
                lines.append(f"    // 来源: references/kvcache_conn_fault_mode.md {fm.get('lines', '')}")
                lines.append('    std::string grepOut' + str(i) + ' = kvcache_conn_utils::RunCommand(')
                lines.append(f'        R"({case["grep_cmd"]} 2>/dev/null)");')
                proc_expected = case.get("process_expected", "empty")
                if proc_expected == "empty":
                    lines.append(f"    bool case{i}_matched = !grepOut{i}.empty() && !kvcache_conn_utils::ProcessExists(\"datasystem_worker\");")
                else:
                    lines.append(f"    bool case{i}_matched = !grepOut{i}.empty() && kvcache_conn_utils::ProcessExists(\"datasystem_worker\");")
            elif case_type == "metrics_increased":
                conditions.append(f"case{i}_matched")
                lines.append(f"    // Case {i+1}: {case['desc']}")
                lines.append(f"    // 来源: references/kvcache_conn_fault_mode.md {fm.get('lines', '')}")
                lines.append('    std::string metricsOut' + str(i) + ' = kvcache_conn_utils::RunCommand(')
                lines.append(f'        R"({case["cmd"]} 2>/dev/null)");')
                metrics = case.get("metrics", [])
                metrics_checks = " || ".join(f'kvcache_conn_utils::HasMetricsIncreased(metricsOut{i}, "{m}")' for m in metrics)
                lines.append(f"    bool case{i}_matched = {metrics_checks};")
            elif case_type == "resource_log":
                conditions.append(f"case{i}_matched")
                lines.append(f"    // Case {i+1}: {case['desc']}")
                lines.append(f"    // 来源: references/kvcache_conn_fault_mode.md {fm.get('lines', '')}")
                lines.append('    std::string resourceOut' + str(i) + ' = kvcache_conn_utils::RunCommand(')
                lines.append(f'        R"({case["cmd"]} 2>/dev/null)");')
                lines.append(f"    // Warning: resource log check requires parsing ETCD_QUEUE_USAGE >= 80% or success rate < 0.95")
                lines.append(f"    bool case{i}_matched = !resourceOut{i}.empty();")
            else:
                conditions.append(f"case{i}_matched")
                lines.append(f"    // Warning: Unrecognized case type '{case_type}' for Case {i+1}")
                lines.append(f"    bool case{i}_matched = false;")

        if conditions:
            lines.append("    return " + " || ".join(conditions) + ";")
        else:
            lines.append("    return false;")
    else:
        lines.append("    // Warning: Unrecognized logic_type '" + lt + "'")
        lines.append("    return false;")

    return "\n".join(lines)


def generate_cpp(fm):
    """Generate .cpp file content for a fault mode."""
    cn = class_name_from_id(fm["id"])
    fn = file_name_from_id(fm["id"])
    leaf = is_leaf(fm)
    lines = []
    lines.append("#include \"" + fn + ".h\"")
    lines.append("#include \"../failure_mode_factory.h\"")
    lines.append("#include \"kvcache_conn_utils.h\"")
    lines.append("")
    lines.append("namespace diag {")
    lines.append("")
    # AutoRegister - use full fault ID
    lines.append(f"static AutoRegister<{cn}> g_{cn}(\"{fm['id']}\");")
    lines.append("")
    # Constructor
    lines.append(f"{cn}::{cn}() noexcept")
    lines.append("{")
    lines.append("}")
    lines.append("")
    # IsValid
    lines.append(f"bool {cn}::IsValid()")
    lines.append("{")
    lines.append(generate_validation_code(fm))
    lines.append("}")
    lines.append("")
    # GetName
    lines.append(f"std::string {cn}::GetName() const")
    lines.append("{")
    lines.append(f"    return \"{fm['name']}\";")
    lines.append("}")
    lines.append("")
    # GetRootCauseDesc
    lines.append(f"std::string {cn}::GetRootCauseDesc() const")
    lines.append("{")
    lines.append(f"    return \"{fm['root_cause']}\";")
    lines.append("}")
    lines.append("")
    # AnalyzeRootCause - leaf returns true, non-leaf returns false
    lines.append(f"RootCause {cn}::AnalyzeRootCause()")
    lines.append("{")
    if leaf:
        lines.append(f"    return RootCause(true, \"{fm['root_cause']}\");")
    else:
        lines.append(f"    return RootCause(false, \"{fm['root_cause']}\");")
    lines.append("}")
    lines.append("")
    # GetFixSuggDesc
    lines.append(f"std::string {cn}::GetFixSuggDesc() const")
    lines.append("{")
    lines.append(f"    return \"{fm['fix_sugg']}\";")
    lines.append("}")
    lines.append("")
    # GetValidationMethodDesc
    lines.append(f"std::string {cn}::GetValidationMethodDesc() const")
    lines.append("{")
    lines.append(f"    return \"{fm['validation']}\";")
    lines.append("}")
    lines.append("")
    # GetId
    lines.append(f"std::string {cn}::GetId() const")
    lines.append("{")
    lines.append(f"    return \"{fm['id']}\";")
    lines.append("}")
    lines.append("")
    lines.append("} // namespace diag")
    return "\n".join(lines)


def generate_csv():
    """Generate CSV file with all fault mode fields, fault ID as leftmost column."""
    output_path = os.path.join(DATA_DIR, "kvcache_conn_fault_mode.csv")

    fieldnames = [
        "故障编码",
        "故障名称",
        "故障下级编码",
        "验证方法",
        "故障原因",
        "解决方法",
        "逻辑类型",
        "来源",
        "源文档行号",
        "故障现象",
    ]

    with open(output_path, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()

        for fm in FAULT_MODES:
            children_str = "、".join(fm.get("children", []))
            sources_str = "；".join(fm.get("sources", []))

            cases = fm.get("cases", [])
            if cases:
                case_parts = []
                for i, case in enumerate(cases, 1):
                    parts = [f"case {i}:"]
                    if "desc" in case:
                        parts.append(f"描述: {case['desc']}")
                    if "cmd" in case:
                        parts.append(f"命令: {case['cmd']}")
                    if "check" in case:
                        parts.append(f"检查方式: {case['check']}")
                    if "keywords" in case:
                        parts.append(f"关键字: {'、'.join(case['keywords'])}")
                    if "field" in case:
                        parts.append(f"字段: {case['field']}")
                    case_parts.append(" ".join(parts))
                phenomena_str = "\n".join(case_parts)
            elif fm.get("logic_type") == "uniq_code":
                codes = fm.get("codes", [])
                phenomena_str = f"错误码为: {', '.join(str(c) for c in codes)}"
            elif fm.get("logic_type") == "grep":
                phenomena_str = f"关键字: {fm.get('grep_keyword', '')}"
            else:
                phenomena_str = ""

            row = {
                "故障编码": fm.get("id", ""),
                "故障名称": fm.get("name", ""),
                "故障下级编码": children_str,
                "验证方法": fm.get("validation", ""),
                "故障原因": fm.get("root_cause", ""),
                "解决方法": fm.get("fix_sugg", ""),
                "逻辑类型": fm.get("logic_type", ""),
                "来源": sources_str,
                "源文档行号": fm.get("lines", ""),
                "故障现象": phenomena_str,
            }
            writer.writerow(row)

    print(f"Generated CSV: {output_path}")


def generate_fault_tree():
    """Generate JSON fault tree file with full IDs and inline children arrays."""
    fault_tree = {}
    for fm in FAULT_MODES:
        fault_id = fm["id"]
        children = list(fm.get("children", []))
        fault_tree[fault_id] = children

    output_path = os.path.join(DATA_DIR, "kvcache_conn_fault_mode_tree.json")
    with open(output_path, "w", encoding="utf-8") as f:
        f.write("{\n")
        f.write('    "kvcache_conn": {\n')
        keys = list(fault_tree.keys())
        for idx, key in enumerate(keys):
            children = fault_tree[key]
            children_str = ", ".join(f'"{c}"' for c in children)
            if idx < len(keys) - 1:
                f.write(f'        "{key}": [{children_str}],\n')
            else:
                f.write(f'        "{key}": [{children_str}]\n')
        f.write("    }\n")
        f.write("}\n")
    print(f"Generated fault tree: {output_path}")


def update_cmake_lists(new_files):
    """Update CMakeLists.txt with new source files."""
    if not os.path.exists(CMAKE_FILE):
        print(f"Warning: CMakeLists.txt not found at {CMAKE_FILE}")
        return

    with open(CMAKE_FILE, "r", encoding="utf-8") as f:
        content = f.read()

    # Find the add_library block
    lib_pattern = re.compile(r'(add_library\(diagnosis_tool STATIC\n)(.*?)(\))', re.DOTALL)
    match = lib_pattern.search(content)
    if not match:
        print(f"Warning: Could not find add_library block in {CMAKE_FILE}")
        return

    prefix = match.group(1)
    current_files = match.group(2)
    suffix = match.group(3)

    # Add new files if not already present
    added = []
    for file in new_files:
        if f"failure_mode_realization/{file}" not in current_files:
            current_files += f"    failure_mode_realization/{file}\n"
            added.append(file)

    if added:
        new_content = lib_pattern.sub(f"{prefix}{current_files}{suffix}", content)
        with open(CMAKE_FILE, "w", encoding="utf-8") as f:
            f.write(new_content)
        print(f"Updated CMakeLists.txt with {len(added)} new files.")
    else:
        print("CMakeLists.txt already up to date.")


def main():
    """Main function to generate all code and files."""
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    os.makedirs(DATA_DIR, exist_ok=True)

    generated_files = []

    # Generate header and cpp files for each fault mode
    for fm in FAULT_MODES:
        cn = class_name_from_id(fm["id"])
        fn = file_name_from_id(fm["id"])
        h_file = f"{fn}.h"
        cpp_file = f"{fn}.cpp"

        # Generate header
        h_path = os.path.join(OUTPUT_DIR, h_file)
        with open(h_path, "w", encoding="utf-8") as f:
            f.write(generate_header(fm))
        print(f"Generated: {h_path}")

        # Generate cpp
        cpp_path = os.path.join(OUTPUT_DIR, cpp_file)
        with open(cpp_path, "w", encoding="utf-8") as f:
            f.write(generate_cpp(fm))
        print(f"Generated: {cpp_path}")

        generated_files.append(cpp_file)

    # Generate fault tree JSON
    generate_fault_tree()

    # Generate CSV
    generate_csv()

    # Update CMakeLists.txt
    update_cmake_lists(generated_files)

    print(f"\nDone! Generated {len(generated_files)} fault mode files, fault tree, and CSV.")


if __name__ == "__main__":
    main()