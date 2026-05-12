# KVCache通断故障模式日志检查汇总

本文档汇总所有 KVCache 通断故障模式中检查的日志文件、检查内容及对应的故障编号和名称。

## 日志文件说明

| 日志文件 | 说明 |
|---------|------|
| ds_client_access_*.log | Client访问日志，格式：`code \| handleName \| microseconds \| dataSize \| reqMsg \| respMsg` |
| ds_client_*.INFO.log | Client INFO日志 |
| datasystem_worker.INFO.log | Worker INFO日志 |
| resource.log | 资源监控日志（内存/磁盘/线程池/etcd队列） |

## 日志文件与故障模式对应关系

| 日志文件 | 故障编号 | 故障名称 |
|---------|---------|---------|
| ds_client_access_*.log | kvcache_conn_fault_001 | KVCache通断异常 |
| ds_client_access_*.log | kvcache_conn_fault_002 | 用户侧错误 |
| ds_client_access_*.log | kvcache_conn_fault_003 | 参数非法 |
| ds_client_access_*.log | kvcache_conn_fault_007 | 对象不存在 |
| ds_client_access_*.log | kvcache_conn_fault_008 | DS进程内错误 |
| ds_client_access_*.log | kvcache_conn_fault_013 | 三方etcd错误 |
| ds_client_access_*.log | kvcache_conn_fault_014 | 桶码错误 |
| ds_client_access_*.log | kvcache_conn_fault_022 | URMA错误 |
| ds_client_access_*.log | kvcache_conn_fault_026 | URMA建连失败 |
| ds_client_access_*.log | kvcache_conn_fault_030 | URMA超时 |
| ds_client_access_*.log | kvcache_conn_fault_031 | OS错误 |
| ds_client_access_*.log | kvcache_conn_fault_032 | 内存不足 |
| ds_client_access_*.log | kvcache_conn_fault_033 | IO错误 |
| ds_client_access_*.log | kvcache_conn_fault_034 | 磁盘空间不足 |
| ds_client_access_*.log | kvcache_conn_fault_035 | 文件描述符耗尽 |
| ds_client_access_*.log | kvcache_conn_fault_036 | mmap失败 |
| ds_client_access_*.log | kvcache_conn_fault_037 | code=5按日志串细分 |
| ds_client_*.INFO.log | kvcache_conn_fault_003 | 参数非法 |
| ds_client_*.INFO.log | kvcache_conn_fault_004 | 未配置Init |
| ds_client_*.INFO.log | kvcache_conn_fault_005 | buffer重复Publish |
| ds_client_*.INFO.log | kvcache_conn_fault_006 | 批次超限 |
| ds_client_*.INFO.log | kvcache_conn_fault_007 | 对象不存在 |
| ds_client_*.INFO.log | kvcache_conn_fault_009 | 对端处理慢/拒绝 |
| ds_client_*.INFO.log | kvcache_conn_fault_011 | 三方etcd（信号出现在DS日志中） |
| ds_client_*.INFO.log | kvcache_conn_fault_012 | 心跳/生命周期/扩缩容 |
| ds_client_*.INFO.log | kvcache_conn_fault_015 | OS层（TCP/UDS/ZMQ系统调用层） |
| ds_client_*.INFO.log | kvcache_conn_fault_016 | TCP建连失败（对端Worker活） |
| ds_client_*.INFO.log | kvcache_conn_fault_017 | TCP连接重置/网络不可达 |
| ds_client_*.INFO.log | kvcache_conn_fault_018 | UDS/SHM传fd失败 |
| ds_client_*.INFO.log | kvcache_conn_fault_019 | ZMQ发送/接收失败 |
| ds_client_*.INFO.log | kvcache_conn_fault_020 | 三方etcd层 |
| ds_client_*.INFO.log | kvcache_conn_fault_021 | DS进程内层 |
| ds_client_*.INFO.log | kvcache_conn_fault_023 | URMA会话重连 |
| ds_client_*.INFO.log | kvcache_conn_fault_024 | URMA JFS异常 |
| ds_client_*.INFO.log | kvcache_conn_fault_025 | URMA驱动/CQ错误 |
| ds_client_*.INFO.log | kvcache_conn_fault_027 | URMA初始化失败 |
| ds_client_*.INFO.log | kvcache_conn_fault_028 | FastTransport/握手失败 |
| ds_client_*.INFO.log | kvcache_conn_fault_029 | URMA数据面读写失败 |
| ds_client_*.INFO.log | kvcache_conn_fault_030 | URMA超时 |
| ds_client_*.INFO.log | kvcache_conn_fault_036 | mmap失败 |
| ds_client_*.INFO.log | kvcache_conn_fault_038 | Client Init/连接Worker失败 |
| ds_client_*.INFO.log | kvcache_conn_fault_042 | UDS路径/权限问题 |
| ds_client_*.INFO.log | kvcache_conn_fault_043 | SHM传fd失败 |
| ds_client_*.INFO.log | kvcache_conn_fault_044 | 机器/节点级故障 |
| datasystem_worker.INFO.log | kvcache_conn_fault_004 | 未配置Init |
| datasystem_worker.INFO.log | kvcache_conn_fault_005 | buffer重复Publish |
| datasystem_worker.INFO.log | kvcache_conn_fault_006 | 批次超限 |
| datasystem_worker.INFO.log | kvcache_conn_fault_009 | 对端处理慢/拒绝 |
| datasystem_worker.INFO.log | kvcache_conn_fault_010 | ZMQ相关问题（重建/断开/握手） |
| datasystem_worker.INFO.log | kvcache_conn_fault_011 | 三方etcd（信号出现在DS日志中） |
| datasystem_worker.INFO.log | kvcache_conn_fault_012 | 心跳/生命周期/扩缩容 |
| datasystem_worker.INFO.log | kvcache_conn_fault_015 | OS层（TCP/UDS/ZMQ系统调用层） |
| datasystem_worker.INFO.log | kvcache_conn_fault_016 | TCP建连失败（对端Worker活） |
| datasystem_worker.INFO.log | kvcache_conn_fault_017 | TCP连接重置/网络不可达 |
| datasystem_worker.INFO.log | kvcache_conn_fault_018 | UDS/SHM传fd失败 |
| datasystem_worker.INFO.log | kvcache_conn_fault_019 | ZMQ发送/接收失败 |
| datasystem_worker.INFO.log | kvcache_conn_fault_020 | 三方etcd层 |
| datasystem_worker.INFO.log | kvcache_conn_fault_021 | DS进程内层 |
| datasystem_worker.INFO.log | kvcache_conn_fault_023 | URMA会话重连 |
| datasystem_worker.INFO.log | kvcache_conn_fault_024 | URMA JFS异常 |
| datasystem_worker.INFO.log | kvcache_conn_fault_025 | URMA驱动/CQ错误 |
| datasystem_worker.INFO.log | kvcache_conn_fault_027 | URMA初始化失败 |
| datasystem_worker.INFO.log | kvcache_conn_fault_028 | FastTransport/握手失败 |
| datasystem_worker.INFO.log | kvcache_conn_fault_029 | URMA数据面读写失败 |
| datasystem_worker.INFO.log | kvcache_conn_fault_030 | URMA超时 |
| datasystem_worker.INFO.log | kvcache_conn_fault_036 | mmap失败 |
| datasystem_worker.INFO.log | kvcache_conn_fault_038 | Client Init/连接Worker失败 |
| datasystem_worker.INFO.log | kvcache_conn_fault_042 | UDS路径/权限问题 |
| datasystem_worker.INFO.log | kvcache_conn_fault_043 | SHM传fd失败 |
| datasystem_worker.INFO.log | kvcache_conn_fault_044 | 机器/节点级故障 |
| datasystem_worker.INFO.log | kvcache_conn_fault_050 | Worker进程在、端口LISTEN但心跳断 |
| resource.log | kvcache_conn_fault_013 | 三方etcd错误 |
| resource.log | kvcache_conn_fault_034 | 磁盘空间不足 |
| (系统命令: ifconfig) | kvcache_conn_fault_026 | URMA建连失败 |
| (系统命令: ls /dev/ub*) | kvcache_conn_fault_026 | URMA建连失败 |
| (系统命令: ubinfo) | kvcache_conn_fault_025 | URMA驱动/CQ错误 |
| (系统命令: ubinfo) | kvcache_conn_fault_026 | URMA建连失败 |
| (系统命令: ubinfo) | kvcache_conn_fault_027 | URMA初始化失败 |
| (系统命令: dmesg) | kvcache_conn_fault_032 | 内存不足 |
| (系统命令: dmesg) | kvcache_conn_fault_033 | IO错误 |
| (系统命令: dmesg) | kvcache_conn_fault_047 | Worker进程被OOM Killer杀掉 |
| (系统命令: dmesg) | kvcache_conn_fault_048 | Worker进程crash（非OOM） |
| (系统命令: pgrep) | kvcache_conn_fault_035 | 文件描述符耗尽 |
| (系统命令: pgrep) | kvcache_conn_fault_039 | Worker进程不存在 |
| (系统命令: pgrep) | kvcache_conn_fault_047 | Worker进程被OOM Killer杀掉 |
| (系统命令: pgrep) | kvcache_conn_fault_048 | Worker进程crash（非OOM） |
| (系统命令: pgrep) | kvcache_conn_fault_049 | Worker进程在但端口不LISTEN |
| (系统命令: pgrep) | kvcache_conn_fault_050 | Worker进程在、端口LISTEN但心跳断 |
| (系统文件: /proc/\<pid\>/fd) | kvcache_conn_fault_035 | 文件描述符耗尽 |
| (系统命令: ulimit) | kvcache_conn_fault_036 | mmap失败 |
| (系统命令: ss) | kvcache_conn_fault_040 | Worker端口未LISTEN |
| (系统命令: ss) | kvcache_conn_fault_041 | TCP建连失败（对端LISTEN） |
| (系统命令: ss) | kvcache_conn_fault_049 | Worker进程在但端口不LISTEN |
| (系统命令: ss) | kvcache_conn_fault_050 | Worker进程在、端口LISTEN但心跳断 |
| (系统命令: ping) | kvcache_conn_fault_045 | 节点不可达 |
| (系统命令: kubectl) | kvcache_conn_fault_046 | 节点NotReady（k8s） |

## 故障模式检查详情

### kvcache_conn_fault_001 — KVCache通断异常

**匹配条件**：
1. 在uniq -c输出中，第二列(code)有非0值
2. code=0但respMsg含NOT_FOUND或Can't find object

**日志检查**：

| 检查项 | 日志文件 | grep模式 | 检查方式 |
|--------|---------|---------|---------|
| 1 | ds_client_access_*.log | `DS_KV_CLIENT_PUT\|DS_KV_CLIENT_GET` | HasCodeZeroWithNotFound (code=0但respMsg含NOT_FOUND) |
| 2 | ds_client_access_*.log | `DS_KV_CLIENT_PUT\|DS_KV_CLIENT_GET` | HasCodeZeroWithNotFound (code=0但respMsg含NOT_FOUND) |

---

### kvcache_conn_fault_002 — 用户侧错误

**验证方法**：KVCache错误码为2(K_INVALID)、3(K_NOT_FOUND)或8(K_NOT_READY)

**日志检查**：

| 检查项 | 日志文件 | grep模式 | 检查方式 |
|--------|---------|---------|---------|
| 1 | ds_client_access_*.log | `DS_KV_CLIENT_PUT\\|DS_KV_CLIENT_GET` | HasCodeInUniqOutput (uniq -c输出中code为2, 3, 8) |

---

### kvcache_conn_fault_003 — 参数非法

**匹配条件**：
1. access log中code=2且respMsg含参数校验失败描述
2. INFO log含K_INVALID

**日志检查**：

| 检查项 | 日志文件 | grep模式 | 检查方式 |
|--------|---------|---------|---------|
| 1 | ds_client_access_*.log | `^2 |` | 字符串查找: The objectKey is empty, dataSize should be bigger than zero, length not match |
| 2 | ds_client_*.INFO.log | `K_INVALID` | 字符串查找: The objectKey is empty, dataSize should be bigger than zero, length not match |

---

### kvcache_conn_fault_004 — 未配置Init

**验证方法**：INFO log含ConnectOptions was not configured

**日志检查**：

| 检查项 | 日志文件 | grep模式 | 检查方式 |
|--------|---------|---------|---------|
| 1 | ds_client_*.INFO.log<br>datasystem_worker.INFO.log | `ConnectOptions was not configured` | 输出非空判断 |

---

### kvcache_conn_fault_005 — buffer重复Publish

**验证方法**：INFO log含Client object is already sealed

**日志检查**：

| 检查项 | 日志文件 | grep模式 | 检查方式 |
|--------|---------|---------|---------|
| 1 | ds_client_*.INFO.log<br>datasystem_worker.INFO.log | `Client object is already sealed` | 输出非空判断 |

---

### kvcache_conn_fault_006 — 批次超限

**验证方法**：access log含OBJECT_KEYS_MAX_SIZE_LIMIT

**日志检查**：

| 检查项 | 日志文件 | grep模式 | 检查方式 |
|--------|---------|---------|---------|
| 1 | ds_client_*.INFO.log<br>datasystem_worker.INFO.log | `OBJECT_KEYS_MAX_SIZE_LIMIT` | 输出非空判断 |

---

### kvcache_conn_fault_007 — 对象不存在

**匹配条件**：
1. INFO log含K_NOT_FOUND或Can't find object
2. access log中code=0但respMsg含NOT_FOUND或Can't find object

**日志检查**：

| 检查项 | 日志文件 | grep模式 | 检查方式 |
|--------|---------|---------|---------|
| 1 | ds_client_*.INFO.log | `K_NOT_FOUND|Can.?t find object` | HasCodeZeroWithNotFound (code=0但respMsg含NOT_FOUND) |
| 2 | ds_client_access_*.log | `DS_KV_CLIENT_GET` | HasCodeZeroWithNotFound (code=0但respMsg含NOT_FOUND) |

---

### kvcache_conn_fault_008 — DS进程内错误

**验证方法**：KVCache错误码为19(K_TRY_AGAIN)、23(K_CLIENT_WORKER_DISCONNECT)、29(K_SERVER_FD_CLOSED)、31(K_SCALE_DOWN)或32(K_SCALING)

**日志检查**：

| 检查项 | 日志文件 | grep模式 | 检查方式 |
|--------|---------|---------|---------|
| 1 | ds_client_access_*.log | `DS_KV_CLIENT_PUT\\|DS_KV_CLIENT_GET` | HasCodeInUniqOutput (uniq -c输出中code为19, 23, 29, 31, 32) |

---

### kvcache_conn_fault_009 — 对端处理慢/拒绝

**匹配条件**：
1. [RPC_RECV_TIMEOUT]且ZMQ fault=0
2. [RPC_SERVICE_UNAVAILABLE]

**日志检查**：

| 检查项 | 日志文件 | grep模式 | 检查方式 |
|--------|---------|---------|---------|
| 1 | ds_client_*.INFO.log<br>datasystem_worker.INFO.log | `\[RPC_RECV_TIMEOUT\]` | 输出非空判断 |
| 2 | ds_client_*.INFO.log<br>datasystem_worker.INFO.log | `\[RPC_SERVICE_UNAVAILABLE\]` | 输出非空判断 |

---

### kvcache_conn_fault_010 — ZMQ相关问题（重建/断开/握手）

**匹配条件**：
1. ZMQ相关指标上升
2. 对端Worker仍活

**日志检查**：

| 检查项 | 日志文件 | grep模式 | 检查方式 |
|--------|---------|---------|---------|
| 1 | datasystem_worker.INFO.log | `zmq_gateway_recreate_total|zmq_event_disconnect_total|zmq_event_handshake_failure_total` | ProcessExists (进程是否存在) |

---

### kvcache_conn_fault_011 — 三方etcd（信号出现在DS日志中）

**验证方法**：INFO log含etcd is timeout或etcd is unavailable

**日志检查**：

| 检查项 | 日志文件 | grep模式 | 检查方式 |
|--------|---------|---------|---------|
| 1 | ds_client_*.INFO.log<br>datasystem_worker.INFO.log | `etcd is timeout|etcd is unavailable` | 输出非空判断 |

---

### kvcache_conn_fault_012 — 心跳/生命周期/扩缩容

**验证方法**：INFO log含Cannot receive heartbeat from worker或HealthCheck Worker is exiting now或meta_is_moving

**日志检查**：

| 检查项 | 日志文件 | grep模式 | 检查方式 |
|--------|---------|---------|---------|
| 1 | ds_client_*.INFO.log<br>datasystem_worker.INFO.log | `Cannot receive heartbeat from worker|Worker is exiting now|meta_is_moving` | 输出非空判断 |

---

### kvcache_conn_fault_013 — 三方etcd错误

**匹配条件**：
1. 返回错误码中有25
2. INFO log含etcd is timeout或etcd is unavailable
3. ETCD_QUEUE堆积或ETCD_REQUEST_SUCCESS_RATE下降

**日志检查**：

| 检查项 | 日志文件 | grep模式 | 检查方式 |
|--------|---------|---------|---------|
| 1 | ds_client_access_*.log | `DS_KV_CLIENT_PUT\\|DS_KV_CLIENT_GET` | HasCodeInUniqOutput (uniq -c输出中code为25) |
| 2 | - | `etcd is timeout|etcd is unavailable` | HasCodeInUniqOutput (uniq -c输出中code为25) |
| 3 | resource.log | `ETCD_REQUEST_SUCCESS_RATE\|ETCD_QUEUE` | HasCodeInUniqOutput (uniq -c输出中code为25) |

---

### kvcache_conn_fault_014 — 桶码错误

**验证方法**：KVCache错误码为1001(K_RPC_DEADLINE_EXCEEDED)或1002(K_RPC_UNAVAILABLE)，需看日志前缀确定边界

**日志检查**：

| 检查项 | 日志文件 | grep模式 | 检查方式 |
|--------|---------|---------|---------|
| 1 | ds_client_access_*.log | `DS_KV_CLIENT_PUT\\|DS_KV_CLIENT_GET` | HasCodeInUniqOutput (uniq -c输出中code为1001, 1002) |

---

### kvcache_conn_fault_015 — OS层（TCP/UDS/ZMQ系统调用层）

**验证方法**：INFO log含[TCP_CONNECT_FAILED]或[TCP_CONNECT_RESET]或[TCP_NETWORK_UNREACHABLE]或[UDS_CONNECT_FAILED]或[SHM_FD_TRANSFER_FAILED]或[ZMQ_SEND_FAILURE_TOTAL]或[ZMQ_RECEIVE_FAILURE_TOTAL]

**日志检查**：

| 检查项 | 日志文件 | grep模式 | 检查方式 |
|--------|---------|---------|---------|
| 1 | ds_client_*.INFO.log<br>datasystem_worker.INFO.log | `\[(TCP|UDS|ZMQ|SHM_FD)_` | 输出非空判断 |

---

### kvcache_conn_fault_016 — TCP建连失败（对端Worker活）

**匹配条件**：
1. [TCP_CONNECT_FAILED]
2. 对端Worker仍活

**日志检查**：

| 检查项 | 日志文件 | grep模式 | 检查方式 |
|--------|---------|---------|---------|
| 1 | ds_client_*.INFO.log<br>datasystem_worker.INFO.log | `\[TCP_CONNECT_FAILED\]` | ProcessExists (进程是否存在) |

---

### kvcache_conn_fault_017 — TCP连接重置/网络不可达

**验证方法**：INFO log含[TCP_CONNECT_RESET]或[TCP_NETWORK_UNREACHABLE]

**日志检查**：

| 检查项 | 日志文件 | grep模式 | 检查方式 |
|--------|---------|---------|---------|
| 1 | ds_client_*.INFO.log<br>datasystem_worker.INFO.log | `\[TCP_CONNECT_RESET\]|\[TCP_NETWORK_UNREACHABLE\]` | 输出非空判断 |

---

### kvcache_conn_fault_018 — UDS/SHM传fd失败

**验证方法**：INFO log含[UDS_CONNECT_FAILED]或[SHM_FD_TRANSFER_FAILED]

**日志检查**：

| 检查项 | 日志文件 | grep模式 | 检查方式 |
|--------|---------|---------|---------|
| 1 | ds_client_*.INFO.log<br>datasystem_worker.INFO.log | `\[UDS_CONNECT_FAILED\]|\[SHM_FD_TRANSFER_FAILED\]` | 输出非空判断 |

---

### kvcache_conn_fault_019 — ZMQ发送/接收失败

**验证方法**：INFO log含[ZMQ_SEND_FAILURE_TOTAL]或[ZMQ_RECEIVE_FAILURE_TOTAL]，按zmq_last_error_number对照errno

**日志检查**：

| 检查项 | 日志文件 | grep模式 | 检查方式 |
|--------|---------|---------|---------|
| 1 | ds_client_*.INFO.log<br>datasystem_worker.INFO.log | `\[ZMQ_SEND_FAILURE_TOTAL\]|\[ZMQ_RECEIVE_FAILURE_TOTAL\]` | 输出非空判断 |

---

### kvcache_conn_fault_020 — 三方etcd层

**验证方法**：INFO log含etcd is timeout或etcd is unavailable

**日志检查**：

| 检查项 | 日志文件 | grep模式 | 检查方式 |
|--------|---------|---------|---------|
| 1 | ds_client_*.INFO.log<br>datasystem_worker.INFO.log | `etcd is timeout|etcd is unavailable` | 输出非空判断 |

---

### kvcache_conn_fault_021 — DS进程内层

**匹配条件**：
1. [TCP_CONNECT_FAILED]且对端Worker不在
2. [RPC_RECV_TIMEOUT]且ZMQ fault=0或[RPC_SERVICE_UNAVAILABLE]

**日志检查**：

| 检查项 | 日志文件 | grep模式 | 检查方式 |
|--------|---------|---------|---------|
| 1 | ds_client_*.INFO.log<br>datasystem_worker.INFO.log | `\[TCP_CONNECT_FAILED\]` | ProcessExists (进程是否存在) |
| 2 | ds_client_*.INFO.log<br>datasystem_worker.INFO.log | `\[RPC_RECV_TIMEOUT\]|\[RPC_SERVICE_UNAVAILABLE\]` | ProcessExists (进程是否存在) |

---

### kvcache_conn_fault_022 — URMA错误

**验证方法**：KVCache错误码为1004/1006/1008/1009/1010

**日志检查**：

| 检查项 | 日志文件 | grep模式 | 检查方式 |
|--------|---------|---------|---------|
| 1 | ds_client_access_*.log | `DS_KV_CLIENT_PUT\\|DS_KV_CLIENT_GET` | HasCodeInUniqOutput (uniq -c输出中code为1004, 1006, 1008, 1009, 1010) |

---

### kvcache_conn_fault_023 — URMA会话重连

**匹配条件**：
1. [URMA_NEED_CONNECT]

**日志检查**：

| 检查项 | 日志文件 | grep模式 | 检查方式 |
|--------|---------|---------|---------|
| 1 | ds_client_*.INFO.log<br>datasystem_worker.INFO.log | `\[URMA_NEED_CONNECT\]` | 输出非空判断 |

---

### kvcache_conn_fault_024 — URMA JFS异常

**匹配条件**：
1. [URMA_RECREATE_JFS]
2. [URMA_RECREATE_JFS_FAILED]

**日志检查**：

| 检查项 | 日志文件 | grep模式 | 检查方式 |
|--------|---------|---------|---------|
| 1 | ds_client_*.INFO.log<br>datasystem_worker.INFO.log | `\[URMA_RECREATE_JFS\]` | 输出非空判断 |
| 2 | ds_client_*.INFO.log<br>datasystem_worker.INFO.log | `\[URMA_RECREATE_JFS_FAILED\]` | 输出非空判断 |

---

### kvcache_conn_fault_025 — URMA驱动/CQ错误

**验证方法**：INFO log含URMA CQ error或URMA driver error

**日志检查**：

| 检查项 | 日志文件 | grep模式 | 检查方式 |
|--------|---------|---------|---------|
| 1 | ds_client_*.INFO.log<br>datasystem_worker.INFO.log | `\[URMA_POLL_ERROR\]|\[URMA_WAIT_TIMEOUT\]` | 输出非空判断 |

---

### kvcache_conn_fault_026 — URMA建连失败

**匹配条件**：
1. 返回错误码中有1009
2. UB端口down
3. UB设备节点缺失

**日志检查**：

| 检查项 | 日志文件 | grep模式 | 检查方式 |
|--------|---------|---------|---------|
| 1 | ds_client_access_*.log | `DS_KV_CLIENT_PUT\\|DS_KV_CLIENT_GET` | 字符串查找: DOWN |
| 2 | (系统命令: ifconfig) | - | 字符串查找: DOWN |
| 3 | (系统命令: ls /dev/ub*) | - | 字符串查找: DOWN |

---

### kvcache_conn_fault_027 — URMA初始化失败

**验证方法**：INFO log含Failed to urma init或Failed to urma get device by name或Failed to urma get eid list或Failed to urma create context或Failed to initialize URMA dlopen loader

**日志检查**：

| 检查项 | 日志文件 | grep模式 | 检查方式 |
|--------|---------|---------|---------|
| 1 | ds_client_*.INFO.log<br>datasystem_worker.INFO.log | `Failed to urma init|Failed to urma get device by name|Failed to urma get eid list|Failed to urma create context|Failed to initialize URMA dlopen loader` | 输出非空判断 |

---

### kvcache_conn_fault_028 — FastTransport/握手失败

**验证方法**：INFO log含Fast transport handshake failed或Failed to import jfr或advise jfr

**日志检查**：

| 检查项 | 日志文件 | grep模式 | 检查方式 |
|--------|---------|---------|---------|
| 1 | ds_client_*.INFO.log<br>datasystem_worker.INFO.log | `Fast transport handshake failed|Failed to import jfr|advise jfr` | 输出非空判断 |

---

### kvcache_conn_fault_029 — URMA数据面读写失败

**验证方法**：INFO log含Failed to urma write object或Failed to urma read object

**日志检查**：

| 检查项 | 日志文件 | grep模式 | 检查方式 |
|--------|---------|---------|---------|
| 1 | ds_client_*.INFO.log<br>datasystem_worker.INFO.log | `Failed to urma write object|Failed to urma read object` | 输出非空判断 |

---

### kvcache_conn_fault_030 — URMA超时

**匹配条件**：
1. 返回错误码中有1010
2. [URMA_WAIT_TIMEOUT]

**日志检查**：

| 检查项 | 日志文件 | grep模式 | 检查方式 |
|--------|---------|---------|---------|
| 1 | ds_client_access_*.log | `DS_KV_CLIENT_PUT\\|DS_KV_CLIENT_GET` | HasCodeInUniqOutput (uniq -c输出中code为1010) |
| 2 | ds_client_*.INFO.log<br>datasystem_worker.INFO.log | `\[URMA_WAIT_TIMEOUT\]` | HasCodeInUniqOutput (uniq -c输出中code为1010) |

---

### kvcache_conn_fault_031 — OS错误

**验证方法**：KVCache错误码为5(K_RUNTIME_ERROR)、6(K_OUT_OF_MEMORY)、7(K_IO_ERROR)、13(K_NO_SPACE)或18(K_FILE_LIMIT_REACHED)

**日志检查**：

| 检查项 | 日志文件 | grep模式 | 检查方式 |
|--------|---------|---------|---------|
| 1 | ds_client_access_*.log | `DS_KV_CLIENT_PUT\\|DS_KV_CLIENT_GET` | HasCodeInUniqOutput (uniq -c输出中code为5, 6, 7, 13, 18) |

---

### kvcache_conn_fault_032 — 内存不足

**匹配条件**：
1. 返回错误码中有6
2. dmesg含Out of memory
3. 可用内存不足

**日志检查**：

| 检查项 | 日志文件 | grep模式 | 检查方式 |
|--------|---------|---------|---------|
| 1 | ds_client_access_*.log | `DS_KV_CLIENT_PUT\\|DS_KV_CLIENT_GET` | HasCodeInUniqOutput (uniq -c输出中code为6) |
| 2 | (系统命令: dmesg) | - | HasCodeInUniqOutput (uniq -c输出中code为6) |
| 3 | - | - | HasCodeInUniqOutput (uniq -c输出中code为6) |

---

### kvcache_conn_fault_033 — IO错误

**匹配条件**：
1. 返回错误码中有7
2. dmesg含I/O error

**日志检查**：

| 检查项 | 日志文件 | grep模式 | 检查方式 |
|--------|---------|---------|---------|
| 1 | ds_client_access_*.log | `DS_KV_CLIENT_PUT\\|DS_KV_CLIENT_GET` | HasCodeInUniqOutput (uniq -c输出中code为7) |
| 2 | (系统命令: dmesg) | `I/O error` | HasCodeInUniqOutput (uniq -c输出中code为7) |

---

### kvcache_conn_fault_034 — 磁盘空间不足

**匹配条件**：
1. 返回错误码中有13
2. 磁盘使用率接近100%
3. SPILL_HARD_DISK或SHARED_DISK空间接近TOTAL_LIMIT

**日志检查**：

| 检查项 | 日志文件 | grep模式 | 检查方式 |
|--------|---------|---------|---------|
| 1 | ds_client_access_*.log | `DS_KV_CLIENT_PUT\\|DS_KV_CLIENT_GET` | HasCodeInUniqOutput (uniq -c输出中code为13) |
| 2 | - | - | HasCodeInUniqOutput (uniq -c输出中code为13) |
| 3 | resource.log | `SPILL_HARD_DISK|SHARED_DISK` | HasCodeInUniqOutput (uniq -c输出中code为13) |

---

### kvcache_conn_fault_035 — 文件描述符耗尽

**匹配条件**：
1. 返回错误码中有18
2. fd数量接近ulimit -n的值

**日志检查**：

| 检查项 | 日志文件 | grep模式 | 检查方式 |
|--------|---------|---------|---------|
| 1 | (系统命令: pgrep)<br>(系统文件: /proc/<pid>/fd) | - | HasCodeInUniqOutput (uniq -c输出中code为18) |
| 2 | ds_client_access_*.log | `DS_KV_CLIENT_PUT\\|DS_KV_CLIENT_GET` | HasCodeInUniqOutput (uniq -c输出中code为18) |

---

### kvcache_conn_fault_036 — mmap失败

**匹配条件**：
1. 返回错误码中有5
2. INFO log含Get mmap entry failed
3. mlock限制值

**日志检查**：

| 检查项 | 日志文件 | grep模式 | 检查方式 |
|--------|---------|---------|---------|
| 1 | ds_client_access_*.log | `DS_KV_CLIENT_PUT\\|DS_KV_CLIENT_GET` | 字符串查找: unlimited |
| 2 | datasystem_worker.INFO.log | `Get mmap entry failed` | 字符串查找: unlimited |
| 3 | (系统命令: ulimit) | - | 字符串查找: unlimited |

---

### kvcache_conn_fault_037 — code=5按日志串细分

**验证方法**：KVCache错误码为5(K_RUNTIME_ERROR)且需按日志串细分

**日志检查**：

| 检查项 | 日志文件 | grep模式 | 检查方式 |
|--------|---------|---------|---------|
| 1 | ds_client_access_*.log | `DS_KV_CLIENT_PUT\\|DS_KV_CLIENT_GET` | HasCodeInUniqOutput (uniq -c输出中code为5) |

---

### kvcache_conn_fault_038 — Client Init/连接Worker失败

**验证方法**：INFO log含[TCP_CONNECT_FAILED]或[UDS_CONNECT_FAILED]或[SHM_FD_TRANSFER_FAILED]或ConnectOptions was not configured

**日志检查**：

| 检查项 | 日志文件 | grep模式 | 检查方式 |
|--------|---------|---------|---------|
| 1 | ds_client_*.INFO.log<br>datasystem_worker.INFO.log | `\[(TCP|UDS|SHM_FD)_|ConnectOptions was not configured` | 输出非空判断 |

---

### kvcache_conn_fault_039 — Worker进程不存在

**验证方法**：pgrep -af datasystem_worker无结果

**日志检查**：

| 检查项 | 日志文件 | grep模式 | 检查方式 |
|--------|---------|---------|---------|
| 1 | (系统命令: pgrep) | - | 输出非空判断 |

---

### kvcache_conn_fault_040 — Worker端口未LISTEN

**匹配条件**：
1. Worker进程存在
2. 端口未LISTEN

**日志检查**：

| 检查项 | 日志文件 | grep模式 | 检查方式 |
|--------|---------|---------|---------|
| 1 | (系统命令: ss) | `31402` | ProcessExists (进程是否存在) |

---

### kvcache_conn_fault_041 — TCP建连失败（对端LISTEN）

**匹配条件**：
1. [TCP_CONNECT_FAILED]
2. 对端端口LISTEN

**日志检查**：

| 检查项 | 日志文件 | grep模式 | 检查方式 |
|--------|---------|---------|---------|
| 1 | - | `\[TCP_CONNECT_FAILED\]` | 输出非空判断 |
| 2 | (系统命令: ss) | `31402` | 输出非空判断 |

---

### kvcache_conn_fault_042 — UDS路径/权限问题

**验证方法**：INFO log含[UDS_CONNECT_FAILED]

**日志检查**：

| 检查项 | 日志文件 | grep模式 | 检查方式 |
|--------|---------|---------|---------|
| 1 | ds_client_*.INFO.log<br>datasystem_worker.INFO.log | `\[UDS_CONNECT_FAILED\]` | 输出非空判断 |

---

### kvcache_conn_fault_043 — SHM传fd失败

**验证方法**：INFO log含[SHM_FD_TRANSFER_FAILED]

**日志检查**：

| 检查项 | 日志文件 | grep模式 | 检查方式 |
|--------|---------|---------|---------|
| 1 | ds_client_*.INFO.log<br>datasystem_worker.INFO.log | `\[SHM_FD_TRANSFER_FAILED\]` | 输出非空判断 |

---

### kvcache_conn_fault_044 — 机器/节点级故障

**验证方法**：INFO log含大量K_CLIENT_WORKER_DISCONNECT(23)/K_RPC_UNAVAILABLE(1002)/Cannot receive heartbeat from worker聚集在某节点

**日志检查**：

| 检查项 | 日志文件 | grep模式 | 检查方式 |
|--------|---------|---------|---------|
| 1 | ds_client_*.INFO.log<br>datasystem_worker.INFO.log | `Cannot receive heartbeat from worker|K_CLIENT_WORKER_DISCONNECT` | 输出非空判断 |

---

### kvcache_conn_fault_045 — 节点不可达

**验证方法**：ping -c 3 <node_ip>不通

**日志检查**：

| 检查项 | 日志文件 | grep模式 | 检查方式 |
|--------|---------|---------|---------|
| 1 | (系统命令: ping) | - | 字符串查找: unreachable |

---

### kvcache_conn_fault_046 — 节点NotReady（k8s）

**验证方法**：kubectl describe node含taints/conditions异常

**日志检查**：

| 检查项 | 日志文件 | grep模式 | 检查方式 |
|--------|---------|---------|---------|
| 1 | (系统命令: kubectl) | - | 字符串查找: NotReady |

---

### kvcache_conn_fault_047 — Worker进程被OOM Killer杀掉

**匹配条件**：
1. Worker进程不存在
2. dmesg含OOM killer
3. dmesg含datasystem_worker

**日志检查**：

| 检查项 | 日志文件 | grep模式 | 检查方式 |
|--------|---------|---------|---------|
| 1 | (系统命令: pgrep) | - | 输出非空判断 |
| 2 | (系统命令: dmesg) | `OOM killer` | 输出非空判断 |
| 3 | (系统命令: dmesg) | `datasystem_worker` | 输出非空判断 |

---

### kvcache_conn_fault_048 — Worker进程crash（非OOM）

**匹配条件**：
1. Worker进程不存在
2. dmesg无OOM记录

**日志检查**：

| 检查项 | 日志文件 | grep模式 | 检查方式 |
|--------|---------|---------|---------|
| 1 | (系统命令: pgrep) | - | 输出非空判断 |
| 2 | (系统命令: dmesg) | `OOM killer` | 输出非空判断 |

---

### kvcache_conn_fault_049 — Worker进程在但端口不LISTEN

**匹配条件**：
1. Worker进程存在
2. 端口未LISTEN

**日志检查**：

| 检查项 | 日志文件 | grep模式 | 检查方式 |
|--------|---------|---------|---------|
| 1 | (系统命令: pgrep) | - | 输出非空判断 |
| 2 | (系统命令: ss) | `31402` | 输出非空判断 |

---

### kvcache_conn_fault_050 — Worker进程在、端口LISTEN但心跳断

**匹配条件**：
1. Worker进程存在
2. 端口LISTEN
3. 心跳断

**日志检查**：

| 检查项 | 日志文件 | grep模式 | 检查方式 |
|--------|---------|---------|---------|
| 1 | (系统命令: pgrep) | - | 输出非空判断 |
| 2 | (系统命令: ss) | `31402` | 输出非空判断 |
| 3 | datasystem_worker.INFO.log | `Cannot receive heartbeat from worker` | 输出非空判断 |

---

## 按日志文件索引

### ds_client_access_*.log

- kvcache_conn_fault_001 KVCache通断异常
- kvcache_conn_fault_001 KVCache通断异常
- kvcache_conn_fault_002 用户侧错误
- kvcache_conn_fault_003 参数非法
- kvcache_conn_fault_007 对象不存在
- kvcache_conn_fault_008 DS进程内错误
- kvcache_conn_fault_013 三方etcd错误
- kvcache_conn_fault_014 桶码错误
- kvcache_conn_fault_022 URMA错误
- kvcache_conn_fault_026 URMA建连失败
- kvcache_conn_fault_030 URMA超时
- kvcache_conn_fault_031 OS错误
- kvcache_conn_fault_032 内存不足
- kvcache_conn_fault_033 IO错误
- kvcache_conn_fault_034 磁盘空间不足
- kvcache_conn_fault_035 文件描述符耗尽
- kvcache_conn_fault_036 mmap失败
- kvcache_conn_fault_037 code=5按日志串细分

### ds_client_*.INFO.log

- kvcache_conn_fault_003 参数非法
- kvcache_conn_fault_004 未配置Init
- kvcache_conn_fault_005 buffer重复Publish
- kvcache_conn_fault_006 批次超限
- kvcache_conn_fault_007 对象不存在
- kvcache_conn_fault_009 对端处理慢/拒绝
- kvcache_conn_fault_009 对端处理慢/拒绝
- kvcache_conn_fault_011 三方etcd（信号出现在DS日志中）
- kvcache_conn_fault_012 心跳/生命周期/扩缩容
- kvcache_conn_fault_015 OS层（TCP/UDS/ZMQ系统调用层）
- kvcache_conn_fault_016 TCP建连失败（对端Worker活）
- kvcache_conn_fault_017 TCP连接重置/网络不可达
- kvcache_conn_fault_018 UDS/SHM传fd失败
- kvcache_conn_fault_019 ZMQ发送/接收失败
- kvcache_conn_fault_020 三方etcd层
- kvcache_conn_fault_021 DS进程内层
- kvcache_conn_fault_021 DS进程内层
- kvcache_conn_fault_023 URMA会话重连
- kvcache_conn_fault_024 URMA JFS异常
- kvcache_conn_fault_024 URMA JFS异常
- kvcache_conn_fault_025 URMA驱动/CQ错误
- kvcache_conn_fault_027 URMA初始化失败
- kvcache_conn_fault_028 FastTransport/握手失败
- kvcache_conn_fault_029 URMA数据面读写失败
- kvcache_conn_fault_030 URMA超时
- kvcache_conn_fault_038 Client Init/连接Worker失败
- kvcache_conn_fault_042 UDS路径/权限问题
- kvcache_conn_fault_043 SHM传fd失败
- kvcache_conn_fault_044 机器/节点级故障

### datasystem_worker.INFO.log

- kvcache_conn_fault_004 未配置Init
- kvcache_conn_fault_005 buffer重复Publish
- kvcache_conn_fault_006 批次超限
- kvcache_conn_fault_009 对端处理慢/拒绝
- kvcache_conn_fault_009 对端处理慢/拒绝
- kvcache_conn_fault_010 ZMQ相关问题（重建/断开/握手）
- kvcache_conn_fault_011 三方etcd（信号出现在DS日志中）
- kvcache_conn_fault_012 心跳/生命周期/扩缩容
- kvcache_conn_fault_015 OS层（TCP/UDS/ZMQ系统调用层）
- kvcache_conn_fault_016 TCP建连失败（对端Worker活）
- kvcache_conn_fault_017 TCP连接重置/网络不可达
- kvcache_conn_fault_018 UDS/SHM传fd失败
- kvcache_conn_fault_019 ZMQ发送/接收失败
- kvcache_conn_fault_020 三方etcd层
- kvcache_conn_fault_021 DS进程内层
- kvcache_conn_fault_021 DS进程内层
- kvcache_conn_fault_023 URMA会话重连
- kvcache_conn_fault_024 URMA JFS异常
- kvcache_conn_fault_024 URMA JFS异常
- kvcache_conn_fault_025 URMA驱动/CQ错误
- kvcache_conn_fault_027 URMA初始化失败
- kvcache_conn_fault_028 FastTransport/握手失败
- kvcache_conn_fault_029 URMA数据面读写失败
- kvcache_conn_fault_030 URMA超时
- kvcache_conn_fault_036 mmap失败
- kvcache_conn_fault_038 Client Init/连接Worker失败
- kvcache_conn_fault_042 UDS路径/权限问题
- kvcache_conn_fault_043 SHM传fd失败
- kvcache_conn_fault_044 机器/节点级故障
- kvcache_conn_fault_050 Worker进程在、端口LISTEN但心跳断

### resource.log

- kvcache_conn_fault_013 三方etcd错误
- kvcache_conn_fault_034 磁盘空间不足

### (系统命令: ifconfig)

- kvcache_conn_fault_026 URMA建连失败

### (系统命令: ls /dev/ub*)

- kvcache_conn_fault_026 URMA建连失败

### (系统命令: dmesg)

- kvcache_conn_fault_032 内存不足
- kvcache_conn_fault_033 IO错误
- kvcache_conn_fault_047 Worker进程被OOM Killer杀掉
- kvcache_conn_fault_047 Worker进程被OOM Killer杀掉
- kvcache_conn_fault_048 Worker进程crash（非OOM）

### (系统命令: pgrep)

- kvcache_conn_fault_035 文件描述符耗尽
- kvcache_conn_fault_039 Worker进程不存在
- kvcache_conn_fault_047 Worker进程被OOM Killer杀掉
- kvcache_conn_fault_048 Worker进程crash（非OOM）
- kvcache_conn_fault_049 Worker进程在但端口不LISTEN
- kvcache_conn_fault_050 Worker进程在、端口LISTEN但心跳断

### (系统文件: /proc/<pid>/fd)

- kvcache_conn_fault_035 文件描述符耗尽

### (系统命令: ulimit)

- kvcache_conn_fault_036 mmap失败

### (系统命令: ss)

- kvcache_conn_fault_040 Worker端口未LISTEN
- kvcache_conn_fault_041 TCP建连失败（对端LISTEN）
- kvcache_conn_fault_049 Worker进程在但端口不LISTEN
- kvcache_conn_fault_050 Worker进程在、端口LISTEN但心跳断

### (系统命令: ping)

- kvcache_conn_fault_045 节点不可达

### (系统命令: kubectl)

- kvcache_conn_fault_046 节点NotReady（k8s）
