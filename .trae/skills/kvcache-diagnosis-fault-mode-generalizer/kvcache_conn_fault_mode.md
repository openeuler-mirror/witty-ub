# 文档：KVCache通断异常故障模式树

## 日志格式说明

本文档中匹配逻辑基于以下日志格式，所有字段引用均按此格式解析：

### 1. Client Access Log（ds_client_access_*.log）

每行以 `|` 分隔，格式如下：

```
code | handleName | microseconds | dataSize | reqMsg | respMsg
  ↑        ↑            ↑            ↑         ↑         ↑
错误码    接口名       耗时(μs)     数据大小   请求参数   响应信息
```

示例行：
```
0 | DS_KV_CLIENT_GET | 49469 | 8388608 | {Object_key:kv_test_1_0_28458466174080_0,timeout:0,transportType:SHM} |
```

- `$1` = code（错误码），如 `0`、`2`、`25`、`1002`
- `$2` = handleName（接口名），如 `DS_KV_CLIENT_GET`、`DS_KV_CLIENT_PUT`
- `$3` = microseconds（耗时μs），如 `49469`
- `$4` = dataSize（数据大小字节），如 `8388608`
- `$5` = reqMsg（请求参数），如 `{Object_key:...,timeout:0,transportType:SHM}`
- `$6` = respMsg（响应信息），如空串或 `NOT_FOUND`

**常用命令输出格式**：

```bash
# 查询KVCache错误码分布
grep "DS_KV_CLIENT_PUT\|DS_KV_CLIENT_GET" $LOG/ds_client_access_*.log | awk -F'|' '{print $1}' | sort | uniq -c
```
输出示例：
```
 120 0
   3 2
   1 1002
```
格式：`<count> <code>`，第一列是出现次数，第二列是错误码。

### 2. Worker/Client INFO Log（datasystem_worker.INFO.log / ds_client_*.INFO.log）

每行以 `|` 分隔，格式如下：

```
timestamp | level | source:line | host | tid:fid | traceId | tenant | message
```

示例行：
```
2026-05-06T13:25:28.429016 | I | worker_oc_service_get_impl.cpp:130 | kvc-jingpai-worker-7b9d7c9dfc-8f2fq | 11:291 | e18c3204-... | jingpai | [TCP_CONNECT_FAILED] addr=192.168.1.1:31402 ...
```

- message字段包含结构化前缀如 `[TCP_CONNECT_FAILED]`、`[URMA_NEED_CONNECT]`、`[RPC_RECV_TIMEOUT]` 等
- grep命令直接匹配message中的关键字即可

### 3. Metrics Summary（INFO log中的周期聚合段）

格式如下：

```
Metrics Summary, version=v0, cycle=<N>, interval=<intervalMs>ms

Total:
  <metric>=<value>

Compare with <intervalMs>ms before:
  <metric>=+<delta>                    ← Counter（增量）
  <metric>,count=+<N>,avg=<us>,max=<us> ← Histogram（直方图）
```

示例：
```
Compare with 10000ms before:
  zmq_gateway_recreate_total=+3
  zmq_event_disconnect_total=+1
  zmq_send_failure_total=+0
  client_rpc_get_latency,count=+85,avg=390us,max=1600us
  worker_process_get_latency,count=+85,avg=520us,max=2600us
```

- Counter格式：`<metric>=+<N>`，N为增量值
- Histogram格式：`<metric>,count=+<N>,avg=<us>,max=<us>`，max值是时延定界核心

### 4. Resource Log（resource.log）

格式为键值对，每个资源类型一段：

```
WORKER_OC_SERVICE_THREAD_POOL: IDLE_NUM=0, CURRENT_TOTAL_NUM=128, MAX_THREAD_NUM=128, WAITING_TASK_NUM=64, THREAD_POOL_USAGE=100%
ETCD_QUEUE: CURRENT_SIZE=50, TOTAL_LIMIT=100, ETCD_QUEUE_USAGE=50%
ETCD_REQUEST_SUCCESS_RATE: 0.85
SHARED_MEMORY: MEMORY_USAGE=8192MB, PHYSICAL_MEMORY_USAGE=7680MB, TOTAL_LIMIT=10240MB, ...
SPILL_HARD_DISK: SPACE_USAGE=500MB, TOTAL_LIMIT=1000MB
SHARED_DISK: USAGE=300MB, TOTAL_LIMIT=500MB
```

### 5. 系统命令输出

- `dmesg`：内核日志，含 `Out of memory`、`I/O error` 等
- `free -h`：内存使用，`available` 列为可用内存
- `df -h`：磁盘使用，`Use%` 列为使用率
- `ulimit -n`：文件描述符上限，如 `65535`
- `ulimit -l`：mlock限制，如 `unlimited` 或 `65536`
- `pgrep -af datasystem_worker`：查找Worker进程，有输出=进程存在
- `ss -tnlp | grep <port>`：查找端口监听，有输出=端口LISTEN
- `ifconfig ub0`：UB端口状态，含 `DOWN`=端口未启用
- `ls /dev/ub*`：UB设备节点，无输出=设备缺失
- `kubectl describe node <n>`：k8s节点状态，含 `NotReady`=节点异常
- `ping -c 3 <ip>`：网络可达性，含 `unreachable`=不可达

---

### 1 KVCache通断异常 [kvcache_conn_fault_001]

* 故障编码：kvcache_conn_fault_001
* 故障名称：KVCache通断异常
* 故障下级编码：kvcache_conn_fault_002、kvcache_conn_fault_008、kvcache_conn_fault_013、kvcache_conn_fault_014、kvcache_conn_fault_022、kvcache_conn_fault_031、kvcache_conn_fault_038、kvcache_conn_fault_044
* 验证方法：查询KVCache错误码非0或code=0但respMsg含NOT_FOUND
* 故障现象：
  * case 1:
    * 日志入口：查询KVCache错误码：grep "DS_KV_CLIENT_PUT\|DS_KV_CLIENT_GET" $LOG/ds_client_access_*.log | awk -F'|' '{print $1}' | sort | uniq -c，输出格式：`<count> <code>`（如 ` 120 0`、`  3 2`、`  1 1002`），字段含义：code=错误码【来源：08-fault-triage-consolidated.md L12-L14，10-customer-fault-scenarios.md L40-L42】
    * 关键字：返回错误码非0
    * 匹配逻辑：在`uniq -c`输出中，第二列(code)有非0值（如输出含`  3 2`或`  1 1002`，而不仅仅是` 120 0`）
  * case 2:
    * 日志入口：查询KVCache错误码：grep "DS_KV_CLIENT_PUT\|DS_KV_CLIENT_GET" $LOG/ds_client_access_*.log | awk -F'|' '{print $1}' | sort | uniq -c，输出格式：`<count> <code>`（如 ` 120 0`、`  3 2`、`  1 1002`），字段含义：code=错误码【来源：08-fault-triage-consolidated.md L12-L14，10-customer-fault-scenarios.md L40-L42】
    * 关键字：code=0但respMsg含NOT_FOUND或Can't find object
    * 匹配逻辑：在access log原始行中，`|`分隔的第1列code=0且第6列(respMsg)含`NOT_FOUND`或`Can't find object`（如`0 | DS_KV_CLIENT_GET | 49469 | 8388608 | {...} | NOT_FOUND`）
    * 说明：K_NOT_FOUND在access log会被记成code=0，业务"查不到"场景需同时看respMsg【来源：08-fault-triage-consolidated.md L15-L16，10-customer-fault-scenarios.md L58-L60】
* 故障原因：向下级匹配。
* 解决方法：向下级匹配。

#### 1.1 用户侧错误（code ∈ {2,3,8}） [kvcache_conn_fault_002]

* 故障编码：kvcache_conn_fault_002
* 故障名称：用户侧错误
* 故障下级编码：kvcache_conn_fault_003、kvcache_conn_fault_004、kvcache_conn_fault_005、kvcache_conn_fault_006、kvcache_conn_fault_007
* 验证方法：KVCache错误码为2(K_INVALID)、3(K_NOT_FOUND)或8(K_NOT_READY)
* 故障现象：
  * 日志入口：查询KVCache错误码：grep "DS_KV_CLIENT_PUT\|DS_KV_CLIENT_GET" $LOG/ds_client_access_*.log | awk -F'|' '{print $1}' | sort | uniq -c，输出格式：`<count> <code>`（如 ` 120 0`、`  3 2`、`  1 1002`），字段含义：code=错误码【来源：08-fault-triage-consolidated.md L12-L14，10-customer-fault-scenarios.md L40-L42】
  * 关键字：返回错误码中有2（K_INVALID）、3（K_NOT_FOUND）、8（K_NOT_READY）【来源：08-fault-triage-consolidated.md L73-L74，10-customer-fault-scenarios.md L78-L80】
  * 匹配逻辑：在`uniq -c`输出中，第二列(code)有2、3或8（如`  5 2`、`  3 3`、`  1 8`）
* 故障原因：向下级匹配。
* 解决方法：向下级匹配。

##### 1.1.1 参数非法 [kvcache_conn_fault_003]

* 故障编码：kvcache_conn_fault_003
* 故障名称：参数非法
* 验证方法：access log错误码为2(K_INVALID)或INFO log含K_INVALID及参数校验失败描述
* 故障现象：
  * case 1:
    * 日志入口：grep '^2 |' $LOG/ds_client_access_*.log 或 grep "K_INVALID" $LOG/ds_client_*.INFO.log，输出格式：`2 | DS_KV_CLIENT_PUT | <us> | <size> | <reqMsg> | <respMsg>`，字段含义：$1=code=2, $2=接口名, $3=耗时, $4=数据大小, $5=请求参数, $6=响应信息【来源：10-customer-fault-scenarios.md L127-L128】
    * 关键字：满足以下任一：The objectKey is empty、dataSize should be bigger than zero、length not match【来源：08-fault-triage-consolidated.md L175-L176，10-customer-fault-scenarios.md L129-L130】
    * 匹配逻辑：在access log原始行中，`|`分隔的第1列code=2，且第6列(respMsg)含`The objectKey is empty`或`dataSize should be bigger than zero`或`length not match`中的任一个
  * case 2:
    * 日志入口：grep "K_INVALID" $LOG/ds_client_*.INFO.log，输出格式：`<timestamp> | I | <source>:<line> | <host> | <tid:fid> | <traceId> | <tenant> | K_INVALID ...`【来源：10-customer-fault-scenarios.md L127-L128】
    * 关键字：K_INVALID
    * 匹配逻辑：grep `K_INVALID` 输出非空（即能找到含`K_INVALID`的行）
* 故障原因：业务参数非法【来源：08-fault-triage-consolidated.md L175-L176，10-customer-fault-scenarios.md L129-L130】。
* 解决方法：业务校验【来源：08-fault-triage-consolidated.md L176】。

##### 1.1.2 未配置Init [kvcache_conn_fault_004]

* 故障编码：kvcache_conn_fault_004
* 故障名称：未配置Init
* 验证方法：INFO log含ConnectOptions was not configured
* 故障现象：
  * 日志入口：grep 'ConnectOptions was not configured' $LOG/ds_client_*.INFO.log，输出格式：`<timestamp> | I | <source>:<line> | <host> | <tid:fid> | <traceId> | <tenant> | ConnectOptions was not configured`【来源：08-fault-triage-consolidated.md L177，10-customer-fault-scenarios.md L131-L132、L548-L549】
  * 关键字：ConnectOptions was not configured
  * 匹配逻辑：grep `ConnectOptions was not configured` 输出非空
* 故障原因：未配置Init【来源：08-fault-triage-consolidated.md L177，10-customer-fault-scenarios.md L131-L132】。
* 解决方法：检查Init【来源：08-fault-triage-consolidated.md L177】。

##### 1.1.3 buffer重复Publish [kvcache_conn_fault_005]

* 故障编码：kvcache_conn_fault_005
* 故障名称：buffer重复Publish
* 验证方法：INFO log含Client object is already sealed
* 故障现象：
  * 日志入口：grep 'Client object is already sealed' $LOG/ds_client_*.INFO.log，输出格式：`<timestamp> | I | <source>:<line> | <host> | <tid:fid> | <traceId> | <tenant> | Client object is already sealed`【来源：08-fault-triage-consolidated.md L178，10-customer-fault-scenarios.md L133-L134】
  * 关键字：Client object is already sealed
  * 匹配逻辑：grep `Client object is already sealed` 输出非空
* 故障原因：buffer重复Publish【来源：08-fault-triage-consolidated.md L178，10-customer-fault-scenarios.md L133-L134】。
* 解决方法：检查业务逻辑【来源：08-fault-triage-consolidated.md L178】。

##### 1.1.4 批次超限 [kvcache_conn_fault_006]

* 故障编码：kvcache_conn_fault_006
* 故障名称：批次超限
* 验证方法：access log含OBJECT_KEYS_MAX_SIZE_LIMIT
* 故障现象：
  * 日志入口：grep 'OBJECT_KEYS_MAX_SIZE_LIMIT' $LOG/ds_client_access_*.log，输出格式：`<code> | DS_KV_CLIENT_* | <us> | <size> | <reqMsg含OBJECT_KEYS_MAX_SIZE_LIMIT> | <respMsg>`【来源：08-fault-triage-consolidated.md L179，10-customer-fault-scenarios.md L135-L136】
  * 关键字：OBJECT_KEYS_MAX_SIZE_LIMIT
  * 匹配逻辑：在access log原始行中，`|`分隔的第5列(reqMsg)含`OBJECT_KEYS_MAX_SIZE_LIMIT`（如`2 | DS_KV_CLIENT_GET | ... | {...OBJECT_KEYS_MAX_SIZE_LIMIT...} |`）
* 故障原因：批次超限【来源：08-fault-triage-consolidated.md L179，10-customer-fault-scenarios.md L135-L136】。
* 解决方法：拆batch【来源：08-fault-triage-consolidated.md L179】。

##### 1.1.5 对象不存在 [kvcache_conn_fault_007]

* 故障编码：kvcache_conn_fault_007
* 故障名称：对象不存在
* 验证方法：INFO log含K_NOT_FOUND或Can't find object，或access log code=0但respMsg含NOT_FOUND
* 故障现象：
  * case 1:
    * 日志入口：grep -E 'K_NOT_FOUND|Can.?t find object' $LOG/ds_client_*.INFO.log，输出格式：`<timestamp> | I | <source>:<line> | <host> | <tid:fid> | <traceId> | <tenant> | K_NOT_FOUND ...` 或 `Can't find object ...`【来源：08-fault-triage-consolidated.md L180，10-customer-fault-scenarios.md L276-L277】
    * 关键字：满足以下任一：K_NOT_FOUND、Can't find object
    * 匹配逻辑：grep `K_NOT_FOUND`或`Can't find object` 输出非空（任一匹配即可）
  * case 2:
    * 日志入口：grep "DS_KV_CLIENT_GET" $LOG/ds_client_access_*.log | awk -F'|' '{print $1, $NF}' | sort | uniq -c | head，输出格式：`<count> <code>`（如 ` 120 0`、`  3 2`、`  1 1002`），字段含义：code=错误码【来源：10-customer-fault-scenarios.md L273-L275】
    * 关键字：code=0 + respMsg含NOT_FOUND或Can't find object
    * 匹配逻辑：在access log原始行中，`|`分隔的第1列code=0且第6列(respMsg)含`NOT_FOUND`或`Can't find object`（如`0 | DS_KV_CLIENT_GET | 49469 | 8388608 | {...} | NOT_FOUND`）
    * 说明：K_NOT_FOUND在access log会被记成code=0，不要只看code非0判断【来源：10-customer-fault-scenarios.md L278-L280】
* 故障原因：对象不存在【来源：08-fault-triage-consolidated.md L180】。
* 解决方法：业务自查key【来源：08-fault-triage-consolidated.md L180】；检查业务是否先Put再Get、key生成逻辑、TTL是否提前过期【来源：10-customer-fault-scenarios.md L289-L295】。

#### 1.2 DS进程内错误（code ∈ {19,23,29,31,32}） [kvcache_conn_fault_008]

* 故障编码：kvcache_conn_fault_008
* 故障名称：DS进程内错误
* 故障下级编码：kvcache_conn_fault_009、kvcache_conn_fault_010、kvcache_conn_fault_011、kvcache_conn_fault_012
* 验证方法：KVCache错误码为19(K_TRY_AGAIN)、23(K_CLIENT_WORKER_DISCONNECT)、29(K_SERVER_FD_CLOSED)、31(K_SCALE_DOWN)或32(K_SCALING)
* 故障现象：
  * 日志入口：查询KVCache错误码：grep "DS_KV_CLIENT_PUT\|DS_KV_CLIENT_GET" $LOG/ds_client_access_*.log | awk -F'|' '{print $1}' | sort | uniq -c，输出格式：`<count> <code>`（如 ` 120 0`、`  3 2`、`  1 1002`），字段含义：code=错误码【来源：08-fault-triage-consolidated.md L12-L14，10-customer-fault-scenarios.md L40-L42】
  * 关键字：返回错误码中有19（K_TRY_AGAIN）、23（K_CLIENT_WORKER_DISCONNECT）、29（K_SERVER_FD_CLOSED）、31（K_SCALE_DOWN）、32（K_SCALING）【来源：08-fault-triage-consolidated.md L73-L74，10-customer-fault-scenarios.md L78-L80】
  * 匹配逻辑：在`uniq -c`输出中，第二列(code)有19、23、29、31或32（如`  2 19`、`  1 23`）
* 故障原因：向下级匹配。
* 解决方法：向下级匹配。

##### 1.2.1 对端处理慢/拒绝 [kvcache_conn_fault_009]

* 故障编码：kvcache_conn_fault_009
* 故障名称：对端处理慢/拒绝
* 验证方法：INFO log含[RPC_RECV_TIMEOUT]且ZMQ fault=0，或含[RPC_SERVICE_UNAVAILABLE]
* 故障现象：
  * 日志入口：grep -E '\[RPC_RECV_TIMEOUT\]|\[RPC_SERVICE_UNAVAILABLE\]' $LOG/datasystem_worker.INFO.log $LOG/ds_client_*.INFO.log | tail -50，输出格式：`<timestamp> | I | <source>:<line> | <host> | <tid:fid> | <traceId> | <tenant> | [RPC_RECV_TIMEOUT] ...` 或 `[RPC_SERVICE_UNAVAILABLE] ...`【来源：08-fault-triage-consolidated.md L120-L121，10-customer-fault-scenarios.md L172-L173】
  * 关键字：需同时满足[RPC_RECV_TIMEOUT]和ZMQ fault=0；或匹配[RPC_SERVICE_UNAVAILABLE]【来源：08-fault-triage-consolidated.md L120-L121，10-customer-fault-scenarios.md L172-L173】
  * 匹配逻辑：满足以下任一：①grep `[RPC_RECV_TIMEOUT]` 输出非空，且`Compare with`段中`zmq_*_failure_total`增量=0（如`zmq_send_failure_total=+0`）；②grep `[RPC_SERVICE_UNAVAILABLE]` 输出非空
  * 说明：[RPC_RECV_TIMEOUT]且ZMQ fault=0表示对端处理慢拖超时，非网络问题【来源：08-fault-triage-consolidated.md L192-L193】
* 故障原因：对端Worker处理慢或主动拒绝，线程池打满【来源：08-fault-triage-consolidated.md L192-L193，10-customer-fault-scenarios.md L172-L173】。
* 解决方法：查Worker CPU/锁；扩oc_rpc_thread_num【来源：08-fault-triage-consolidated.md L192-L193】。

##### 1.2.2 ZMQ相关问题（重建/断开/握手） [kvcache_conn_fault_010]

* 故障编码：kvcache_conn_fault_010
* 故障名称：ZMQ相关问题（重建/断开/握手）
* 验证方法：INFO log含zmq_gateway_recreate_total或zmq_event_disconnect_total或zmq_event_handshake_failure_total上升，且对端Worker仍活
* 故障现象：
  * 日志入口：grep -E 'zmq_gateway_recreate_total|zmq_event_disconnect_total|zmq_event_handshake_failure_total' $LOG/datasystem_worker.INFO.log | tail -50，输出格式：`zmq_gateway_recreate_total=+<N>` / `zmq_event_disconnect_total=+<N>` / `zmq_event_handshake_failure_total=+<N>`【来源：08-fault-triage-consolidated.md L196-L197】
  * 关键字：满足以下任一：zmq_gateway_recreate_total↑、zmq_event_disconnect_total↑、zmq_event_handshake_failure_total↑，且对端Worker仍活【来源：08-fault-triage-consolidated.md L196-L197】
  * 匹配逻辑：步骤1：在`Compare with`段中，以下任一指标增量>0（如`zmq_gateway_recreate_total=+3`、`zmq_event_disconnect_total=+1`、`zmq_event_handshake_failure_total=+2`）；步骤2：运行`pgrep -af datasystem_worker`有输出（如`12345 /opt/datasystem/worker`）→对端Worker存活→匹配
* 故障原因：ZMQ连接重建/断开/握手失败。低频忽略（SDK自重连）；高频转OS查网络；握手失败查TLS/认证配置【来源：08-fault-triage-consolidated.md L196-L198】。
* 解决方法：低频忽略；高频查OS网络；握手失败查TLS/认证配置【来源：08-fault-triage-consolidated.md L196-L198】。

##### 1.2.3 三方etcd（信号出现在DS日志中） [kvcache_conn_fault_011]

* 故障编码：kvcache_conn_fault_011
* 故障名称：三方etcd（信号出现在DS日志中）
* 验证方法：INFO log含etcd is timeout或etcd is unavailable
* 故障现象：
  * 日志入口：grep -E 'etcd is timeout|etcd is unavailable' $LOG/datasystem_worker.INFO.log | tail -50，输出格式：`<timestamp> | I | <source>:<line> | <host> | <tid:fid> | <traceId> | <tenant> | etcd is timeout ...` 或 `etcd is unavailable ...`【来源：08-fault-triage-consolidated.md L199-L200，10-customer-fault-scenarios.md L161-L162】
  * 关键字：满足以下任一：etcd is timeout、etcd is unavailable【来源：08-fault-triage-consolidated.md L199-L200，10-customer-fault-scenarios.md L161-L162】
  * 匹配逻辑：grep `etcd is timeout`或`etcd is unavailable` 输出非空（任一匹配即可）
  * 说明：常同屏出现code=1002/25【来源：08-fault-triage-consolidated.md L113-L114】
* 故障原因：etcd集群或到etcd的网络异常。主责三方etcd【来源：08-fault-triage-consolidated.md L199-L201，10-customer-fault-scenarios.md L161-L166】。
* 解决方法：systemctl status etcd；etcdctl endpoint status；查到etcd的网络【来源：08-fault-triage-consolidated.md L199-L201，10-customer-fault-scenarios.md L161-L166】。

##### 1.2.4 心跳/生命周期/扩缩容 [kvcache_conn_fault_012]

* 故障编码：kvcache_conn_fault_012
* 故障名称：心跳/生命周期/扩缩容
* 验证方法：INFO log含Cannot receive heartbeat from worker或HealthCheck Worker is exiting now或meta_is_moving
* 故障现象：
  * 日志入口：grep -E 'Cannot receive heartbeat from worker|HealthCheck.*Worker is exiting now|meta_is_moving' $LOG/datasystem_worker.INFO.log | tail -50，输出格式：`<timestamp> | I | <source>:<line> | <host> | <tid:fid> | <traceId> | <tenant> | Cannot receive heartbeat from worker. ...` 或 `[HealthCheck] Worker is exiting now ...` 或 `meta_is_moving = true ...`【来源：08-fault-triage-consolidated.md L202-L203，10-customer-fault-scenarios.md L621-L623】
  * 关键字：满足以下任一：Cannot receive heartbeat from worker（code=23）、[HealthCheck] Worker is exiting now、meta_is_moving（code=31/32）【来源：08-fault-triage-consolidated.md L202-L203，10-customer-fault-scenarios.md L621-L623】
  * 匹配逻辑：grep `Cannot receive heartbeat from worker`或`Worker is exiting now`或`meta_is_moving` 输出非空（任一匹配即可）
* 故障原因：心跳断→Worker被STOP；退出由编排拉起；扩缩容中SDK自重试【来源：08-fault-triage-consolidated.md L202-L204，10-customer-fault-scenarios.md L628-L632】。
* 解决方法：心跳断→kill -CONT <pid>；退出由编排拉起；扩缩容SDK自重试【来源：08-fault-triage-consolidated.md L202-L204，10-customer-fault-scenarios.md L628-L632】。

#### 1.3 三方etcd错误（code=25） [kvcache_conn_fault_013]

* 故障编码：kvcache_conn_fault_013
* 故障名称：三方etcd错误
* 验证方法：KVCache错误码为25(K_MASTER_TIMEOUT)或INFO log含etcd is timeout/unavailable或resource log含ETCD_QUEUE堆积
* 故障现象：
  * case 1:
    * 日志入口：查询KVCache错误码：grep "DS_KV_CLIENT_PUT\|DS_KV_CLIENT_GET" $LOG/ds_client_access_*.log | awk -F'|' '{print $1}' | sort | uniq -c，输出格式：`<count> <code>`（如 ` 120 0`、`  3 2`、`  1 1002`），字段含义：code=错误码【来源：08-fault-triage-consolidated.md L12-L14，10-customer-fault-scenarios.md L40-L42】
    * 关键字：返回错误码中有25（K_MASTER_TIMEOUT）【来源：08-fault-triage-consolidated.md L73-L74，10-customer-fault-scenarios.md L78-L80】
    * 匹配逻辑：在`uniq -c`输出中，第二列(code)有25（如`  5 25`）
  * case 2:
    * 日志入口：grep -E 'etcd is timeout|etcd is unavailable' $LOG/*.INFO.log | tail -20，输出格式：`<timestamp> | I | <source>:<line> | <host> | <tid:fid> | <traceId> | <tenant> | etcd is timeout ...` 或 `etcd is unavailable ...`【来源：10-customer-fault-scenarios.md L161-L162】
    * 关键字：满足以下任一：etcd is timeout、etcd is unavailable
    * 匹配逻辑：grep `etcd is timeout`或`etcd is unavailable` 输出非空（任一匹配即可）
  * case 3:
    * 日志入口：grep 'ETCD_REQUEST_SUCCESS_RATE\|ETCD_QUEUE' $LOG/resource.log | tail -5，输出格式：`ETCD_QUEUE: CURRENT_SIZE=<N>, TOTAL_LIMIT=<N>, ETCD_QUEUE_USAGE=<%>` / `ETCD_REQUEST_SUCCESS_RATE: <rate>`【来源：10-customer-fault-scenarios.md L163-L164】
    * 关键字：ETCD_QUEUE堆积或ETCD_REQUEST_SUCCESS_RATE下降
    * 匹配逻辑：满足以下任一：①在resource.log中找到`ETCD_QUEUE: CURRENT_SIZE=<N>, TOTAL_LIMIT=<N>, ETCD_QUEUE_USAGE=<%>`行，USAGE≥80%（如`ETCD_QUEUE_USAGE=85%`）；②找到`ETCD_REQUEST_SUCCESS_RATE: <rate>`行，rate低于基线（如<0.95）
* 故障原因：etcd集群故障或到etcd的网络异常。主责三方etcd【来源：08-fault-triage-consolidated.md L73-L74，10-customer-fault-scenarios.md L161-L166】。
* 解决方法：systemctl status etcd；etcdctl endpoint status -w table；查到etcd的网络【来源：08-fault-triage-consolidated.md L199-L201，10-customer-fault-scenarios.md L161-L166】。

#### 1.4 桶码错误（code ∈ {1001,1002}） [kvcache_conn_fault_014]

* 故障编码：kvcache_conn_fault_014
* 故障名称：桶码错误
* 故障下级编码：kvcache_conn_fault_015、kvcache_conn_fault_020、kvcache_conn_fault_021
* 验证方法：KVCache错误码为1001(K_RPC_DEADLINE_EXCEEDED)或1002(K_RPC_UNAVAILABLE)，需看日志前缀确定边界
* 故障现象：
  * 日志入口：查询KVCache错误码：grep "DS_KV_CLIENT_PUT\|DS_KV_CLIENT_GET" $LOG/ds_client_access_*.log | awk -F'|' '{print $1}' | sort | uniq -c，输出格式：`<count> <code>`（如 ` 120 0`、`  3 2`、`  1 1002`），字段含义：code=错误码【来源：08-fault-triage-consolidated.md L12-L14，10-customer-fault-scenarios.md L40-L42】
  * 关键字：返回错误码中有1001（K_RPC_DEADLINE_EXCEEDED）或1002（K_RPC_UNAVAILABLE）【来源：08-fault-triage-consolidated.md L73-L74，10-customer-fault-scenarios.md L78-L80】
  * 匹配逻辑：在`uniq -c`输出中，第二列(code)有1001或1002（如`  3 1002`）
  * 说明：1002是桶码，DS crash、OS网络断、etcd不可用都会给1002，必须看日志前缀确定边界【来源：08-fault-triage-consolidated.md L75-L76，10-customer-fault-scenarios.md L82-L83】
* 故障原因：向下级匹配。
* 解决方法：向下级匹配。

##### 1.4.1 OS层（TCP/UDS/ZMQ系统调用层） [kvcache_conn_fault_015]

* 故障编码：kvcache_conn_fault_015
* 故障名称：OS层（TCP/UDS/ZMQ系统调用层）
* 故障下级编码：kvcache_conn_fault_016、kvcache_conn_fault_017、kvcache_conn_fault_018、kvcache_conn_fault_019
* 验证方法：INFO log含[TCP_CONNECT_FAILED]或[TCP_CONNECT_RESET]或[TCP_NETWORK_UNREACHABLE]或[UDS_CONNECT_FAILED]或[SHM_FD_TRANSFER_FAILED]或[ZMQ_SEND_FAILURE_TOTAL]或[ZMQ_RECEIVE_FAILURE_TOTAL]
* 故障现象：
  * 日志入口：grep -E '\[(TCP|UDS|ZMQ|SHM_FD)_' $LOG/datasystem_worker.INFO.log $LOG/ds_client_*.INFO.log | tail -50，输出格式：`<timestamp> | I | <source>:<line> | <host> | <tid:fid> | <traceId> | <tenant> | [TCP_*]/[UDS_*]/[ZMQ_*]/[SHM_FD_*] ...`【来源：08-fault-triage-consolidated.md L103-L104，10-customer-fault-scenarios.md L169-L170】
  * 关键字：满足以下任一且最先出现：[TCP_CONNECT_FAILED]+对端Worker活、[TCP_CONNECT_RESET]、[TCP_NETWORK_UNREACHABLE]、[UDS_CONNECT_FAILED]、[SHM_FD_TRANSFER_FAILED]、[ZMQ_SEND_FAILURE_TOTAL]、[ZMQ_RECEIVE_FAILURE_TOTAL]【来源：08-fault-triage-consolidated.md L103-L110，10-customer-fault-scenarios.md L169-L178】
  * 匹配逻辑：grep输出非空，含`[TCP_CONNECT_FAILED]`/`[TCP_CONNECT_RESET]`/`[TCP_NETWORK_UNREACHABLE]`/`[UDS_CONNECT_FAILED]`/`[SHM_FD_TRANSFER_FAILED]`/`[ZMQ_SEND_FAILURE_TOTAL]`/`[ZMQ_RECEIVE_FAILURE_TOTAL]`中的任一个
* 故障原因：向下级匹配。
* 解决方法：向下级匹配。

###### 1.4.1.1 TCP建连失败（对端Worker活） [kvcache_conn_fault_016]

* 故障编码：kvcache_conn_fault_016
* 故障名称：TCP建连失败（对端Worker活）
* 验证方法：INFO log含[TCP_CONNECT_FAILED]且对端Worker进程仍存活
* 故障现象：
  * 日志入口：grep '\[TCP_CONNECT_FAILED\]' $LOG/datasystem_worker.INFO.log $LOG/ds_client_*.INFO.log | tail -50，输出格式：`<timestamp> | I | <source>:<line> | <host> | <tid:fid> | <traceId> | <tenant> | [TCP_CONNECT_FAILED] addr=<ip:port> ...`【来源：08-fault-triage-consolidated.md L103-L104，10-customer-fault-scenarios.md L169-L170】
  * 关键字：[TCP_CONNECT_FAILED]且对端Worker仍活
  * 匹配逻辑：步骤1：grep `[TCP_CONNECT_FAILED]` 输出非空；步骤2：运行`pgrep -af datasystem_worker`有输出（如`12345 /opt/datasystem/worker`）→对端Worker存活→匹配
  * 说明：判"对端Worker活"的命令：pgrep -af datasystem_worker；ss -tnlp | grep <worker_port>【来源：10-customer-fault-scenarios.md L179-L180】
* 故障原因：端口不通/iptables/路由【来源：08-fault-triage-consolidated.md L103-L104，10-customer-fault-scenarios.md L169-L170】。
* 解决方法：ss -tnlp；iptables -L -n；开端口/删规则【来源：08-fault-triage-consolidated.md L237-L238，10-customer-fault-scenarios.md L186-L187】。

###### 1.4.1.2 TCP连接重置/网络不可达 [kvcache_conn_fault_017]

* 故障编码：kvcache_conn_fault_017
* 故障名称：TCP连接重置/网络不可达
* 验证方法：INFO log含[TCP_CONNECT_RESET]或[TCP_NETWORK_UNREACHABLE]
* 故障现象：
  * 日志入口：grep -E '\[TCP_CONNECT_RESET\]|\[TCP_NETWORK_UNREACHABLE\]' $LOG/datasystem_worker.INFO.log $LOG/ds_client_*.INFO.log | tail -50，输出格式：`<timestamp> | I | <source>:<line> | <host> | <tid:fid> | <traceId> | <tenant> | [TCP_CONNECT_RESET] ...` 或 `[TCP_NETWORK_UNREACHABLE] ...`【来源：08-fault-triage-consolidated.md L105-L106，10-customer-fault-scenarios.md L171-L172】
  * 关键字：满足以下任一：[TCP_CONNECT_RESET]、[TCP_NETWORK_UNREACHABLE]
  * 匹配逻辑：grep `[TCP_CONNECT_RESET]`或`[TCP_NETWORK_UNREACHABLE]` 输出非空（任一匹配即可）
* 故障原因：网络闪断（除非同窗Worker重启）【来源：08-fault-triage-consolidated.md L105-L106】。
* 解决方法：dmesg；netstat -s | grep reset【来源：08-fault-triage-consolidated.md L239-L240，10-customer-fault-scenarios.md L530-L531】。

###### 1.4.1.3 UDS/SHM传fd失败 [kvcache_conn_fault_018]

* 故障编码：kvcache_conn_fault_018
* 故障名称：UDS/SHM传fd失败
* 验证方法：INFO log含[UDS_CONNECT_FAILED]或[SHM_FD_TRANSFER_FAILED]
* 故障现象：
  * case 1:
    * 日志入口：grep -E '\[UDS_CONNECT_FAILED\]|\[SHM_FD_TRANSFER_FAILED\]' $LOG/datasystem_worker.INFO.log $LOG/ds_client_*.INFO.log | tail -50，输出格式：`<timestamp> | I | <source>:<line> | <host> | <tid:fid> | <traceId> | <tenant> | [UDS_CONNECT_FAILED] path=<path> ...` 或 `[SHM_FD_TRANSFER_FAILED] ...`【来源：08-fault-triage-consolidated.md L107-L108，10-customer-fault-scenarios.md L173-L174】
    * 关键字：满足以下任一：[UDS_CONNECT_FAILED]、[SHM_FD_TRANSFER_FAILED]
    * 匹配逻辑：grep `[UDS_CONNECT_FAILED]`或`[SHM_FD_TRANSFER_FAILED]` 输出非空（任一匹配即可）
  * case 2:
    * 日志入口：grep '\[SHM_FD_TRANSFER_FAILED\]' $LOG/ds_client_<pid>.INFO.log | head，输出格式：`<timestamp> | I | <source>:<line> | <host> | <tid:fid> | <traceId> | <tenant> | [SHM_FD_TRANSFER_FAILED] ...`【来源：10-customer-fault-scenarios.md L539-L540】
    * 关键字：[SHM_FD_TRANSFER_FAILED]
    * 匹配逻辑：grep `[SHM_FD_TRANSFER_FAILED]` 输出非空
    * 说明：检查ulimit -n（fd数）；SELinux/AppArmor；/proc/sys/fs/file-max【来源：10-customer-fault-scenarios.md L539-L540】
* 故障原因：同机UDS路径/权限/fd上限；SCM_RIGHTS发送失败多为fd耗尽或权限问题【来源：08-fault-triage-consolidated.md L107-L108、L235-L236，10-customer-fault-scenarios.md L539-L540】。
* 解决方法：检查UDS路径/权限；调大ulimit -n【来源：08-fault-triage-consolidated.md L235-L236，10-customer-fault-scenarios.md L186-L187、L539-L540】。

###### 1.4.1.4 ZMQ发送/接收失败 [kvcache_conn_fault_019]

* 故障编码：kvcache_conn_fault_019
* 故障名称：ZMQ发送/接收失败
* 验证方法：INFO log含[ZMQ_SEND_FAILURE_TOTAL]或[ZMQ_RECEIVE_FAILURE_TOTAL]，按zmq_last_error_number对照errno
* 故障现象：
  * 日志入口：grep -E '\[ZMQ_SEND_FAILURE_TOTAL\]|\[ZMQ_RECEIVE_FAILURE_TOTAL\]' $LOG/datasystem_worker.INFO.log $LOG/ds_client_*.INFO.log | tail -50，输出格式：`<timestamp> | I | <source>:<line> | <host> | <tid:fid> | <traceId> | <tenant> | [ZMQ_SEND_FAILURE_TOTAL] ... zmq_last_error_number=<N>`【来源：08-fault-triage-consolidated.md L109-L110，10-customer-fault-scenarios.md L175-L176】
  * 关键字：满足以下任一：[ZMQ_SEND_FAILURE_TOTAL]、[ZMQ_RECEIVE_FAILURE_TOTAL]
  * 匹配逻辑：grep `[ZMQ_SEND_FAILURE_TOTAL]`或`[ZMQ_RECEIVE_FAILURE_TOTAL]` 输出非空（任一匹配即可）
* 故障原因：zmq_msg_send/recv硬失败，按zmq_last_error_number对照errno确定具体OS原因【来源：08-fault-triage-consolidated.md L109-L110、L241-L242】。
* 解决方法：按errno对照处置【来源：08-fault-triage-consolidated.md L241-L242，10-customer-fault-scenarios.md L175-L176】。errno对照表：11(EAGAIN背压)、101(ENETUNREACH路由不可达)、104(ECONNRESET对端reset)、110(ETIMEDOUT TCP超时)、111(ECONNREFUSED端口无监听)、113(EHOSTUNREACH主机不可达)【来源：08-fault-triage-consolidated.md L247-L253，10-customer-fault-scenarios.md L181】。

##### 1.4.2 三方etcd层 [kvcache_conn_fault_020]

* 故障编码：kvcache_conn_fault_020
* 故障名称：三方etcd层
* 验证方法：INFO log含etcd is timeout或etcd is unavailable
* 故障现象：
  * 日志入口：grep -E 'etcd is timeout|etcd is unavailable' $LOG/datasystem_worker.INFO.log | tail -50，输出格式：`<timestamp> | I | <source>:<line> | <host> | <tid:fid> | <traceId> | <tenant> | etcd is timeout ...` 或 `etcd is unavailable ...`【来源：08-fault-triage-consolidated.md L113-L114，10-customer-fault-scenarios.md L161-L162】
  * 关键字：满足以下任一：etcd is timeout、etcd is unavailable
  * 匹配逻辑：grep `etcd is timeout`或`etcd is unavailable` 输出非空（任一匹配即可）
  * 说明：常同屏出现code=1002/25【来源：08-fault-triage-consolidated.md L113-L114】
* 故障原因：etcd集群或到etcd的网络异常【来源：08-fault-triage-consolidated.md L113-L114，10-customer-fault-scenarios.md L161-L166】。
* 解决方法：systemctl status etcd；etcdctl endpoint status；查到etcd的网络【来源：08-fault-triage-consolidated.md L199-L201，10-customer-fault-scenarios.md L161-L166】。

##### 1.4.3 DS进程内层 [kvcache_conn_fault_021]

* 故障编码：kvcache_conn_fault_021
* 故障名称：DS进程内层
* 验证方法：INFO log含[TCP_CONNECT_FAILED]且对端Worker不在，或含[RPC_RECV_TIMEOUT]且ZMQ fault=0，或含[RPC_SERVICE_UNAVAILABLE]
* 故障现象：
  * case 1:
    * 日志入口：grep '\[TCP_CONNECT_FAILED\]' $LOG/datasystem_worker.INFO.log $LOG/ds_client_*.INFO.log | tail -50，输出格式：`<timestamp> | I | <source>:<line> | <host> | <tid:fid> | <traceId> | <tenant> | [TCP_CONNECT_FAILED] addr=<ip:port> ...`【来源：08-fault-triage-consolidated.md L115-L116，10-customer-fault-scenarios.md L169-L170】
    * 关键字：[TCP_CONNECT_FAILED]且对端Worker不在
    * 匹配逻辑：步骤1：grep `[TCP_CONNECT_FAILED]` 输出非空；步骤2：运行`pgrep -af datasystem_worker`无输出→对端Worker不存在→匹配
    * 说明：判"对端Worker不在"：pgrep -af datasystem_worker无结果【来源：10-customer-fault-scenarios.md L179-L180、L513-L514】
  * case 2:
    * 日志入口：grep -E '\[RPC_RECV_TIMEOUT\]|\[RPC_SERVICE_UNAVAILABLE\]' $LOG/datasystem_worker.INFO.log $LOG/ds_client_*.INFO.log | tail -50，输出格式：`<timestamp> | I | <source>:<line> | <host> | <tid:fid> | <traceId> | <tenant> | [RPC_RECV_TIMEOUT] ...` 或 `[RPC_SERVICE_UNAVAILABLE] ...`【来源：08-fault-triage-consolidated.md L117-L118，10-customer-fault-scenarios.md L172-L173】
    * 关键字：[RPC_RECV_TIMEOUT]且ZMQ fault=0；或[RPC_SERVICE_UNAVAILABLE]
    * 匹配逻辑：满足以下任一：①grep `[RPC_RECV_TIMEOUT]` 输出非空，且`Compare with`段中`zmq_*_failure_total`增量=0（如`zmq_send_failure_total=+0`）；②grep `[RPC_SERVICE_UNAVAILABLE]` 输出非空
* 故障原因：Worker crash/未拉起/机器故障、对端处理慢拖超时、对端主动拒绝【来源：08-fault-triage-consolidated.md L115-L119，10-customer-fault-scenarios.md L169-L178】。
* 解决方法：查对端Worker存活；扩线程池【来源：08-fault-triage-consolidated.md L192-L193，10-customer-fault-scenarios.md L172-L173】。

#### 1.5 URMA错误（code ∈ {1004,1006,1008,1009,1010}） [kvcache_conn_fault_022]

* 故障编码：kvcache_conn_fault_022
* 故障名称：URMA错误
* 故障下级编码：kvcache_conn_fault_023、kvcache_conn_fault_024、kvcache_conn_fault_025、kvcache_conn_fault_026、kvcache_conn_fault_027、kvcache_conn_fault_028、kvcache_conn_fault_029、kvcache_conn_fault_030
* 验证方法：KVCache错误码为1004/1006/1008/1009/1010
* 故障现象：
  * 日志入口：查询KVCache错误码：grep "DS_KV_CLIENT_PUT\|DS_KV_CLIENT_GET" $LOG/ds_client_access_*.log | awk -F'|' '{print $1}' | sort | uniq -c，输出格式：`<count> <code>`（如 ` 120 0`、`  3 2`、`  1 1002`），字段含义：code=错误码【来源：08-fault-triage-consolidated.md L12-L14，10-customer-fault-scenarios.md L40-L42】
  * 关键字：返回错误码中有1004/1006/1008/1009/1010【来源：08-fault-triage-consolidated.md L73-L74，10-customer-fault-scenarios.md L78-L80】
  * 匹配逻辑：在`uniq -c`输出中，第二列(code)有1004/1006/1008/1009/1010中的任一个（如`  1 1009`）
* 故障原因：向下级匹配。
* 解决方法：向下级匹配。

##### 1.5.1 URMA会话重连 [kvcache_conn_fault_023]

* 故障编码：kvcache_conn_fault_023
* 故障名称：URMA会话重连
* 验证方法：INFO log含[URMA_NEED_CONNECT]或[URMA_RECREATE_JFS]
* 故障现象：
  * case 1:
    * 日志入口：grep '\[URMA_NEED_CONNECT\]' $LOG/datasystem_worker.INFO.log $LOG/ds_client_*.INFO.log | tail -50，输出格式：`<timestamp> | I | <source>:<line> | <host> | <tid:fid> | <traceId> | <tenant> | [URMA_*] ...`【来源：08-fault-triage-consolidated.md L214-L215，10-customer-fault-scenarios.md L148-L149】
    * 关键字：[URMA_NEED_CONNECT]+remoteInstanceId变化
    * 匹配逻辑：grep `[URMA_NEED_CONNECT]` 输出非空，且多行中`remoteInstanceId=`后面的值不同（如第1行`remoteInstanceId=100`，第2行`remoteInstanceId=200`）→对端Worker重启→匹配
    * 说明：remoteInstanceId变化表示对端Worker重启【来源：08-fault-triage-consolidated.md L214-L215，10-customer-fault-scenarios.md L153-L154】
  * case 2:
    * 日志入口：grep '\[URMA_NEED_CONNECT\]' $LOG/datasystem_worker.INFO.log $LOG/ds_client_*.INFO.log | tail -50，输出格式：`<timestamp> | I | <source>:<line> | <host> | <tid:fid> | <traceId> | <tenant> | [URMA_*] ...`【来源：08-fault-triage-consolidated.md L216-L217，10-customer-fault-scenarios.md L155-L156】
    * 关键字：[URMA_NEED_CONNECT]持续+instanceId不变
    * 匹配逻辑：grep `[URMA_NEED_CONNECT]` 输出非空，且多行中`instanceId=`后面的值相同（如每行都是`instanceId=100`）→UB链路不稳→匹配
    * 说明：instanceId不变表示UB链路不稳，需查同期是否伴[URMA_POLL_ERROR]/[URMA_RECREATE_JFS]【来源：08-fault-triage-consolidated.md L216-L217，10-customer-fault-scenarios.md L155-L156】
* 故障原因：对端Worker重启（instanceId变化）或UB链路不稳（instanceId不变）【来源：08-fault-triage-consolidated.md L214-L217，10-customer-fault-scenarios.md L153-L156】。
* 解决方法：对端重启→等SDK自重连稳定；UB链路不稳→查UB硬件/驱动/端口/交换机抖动【来源：08-fault-triage-consolidated.md L214-L217，10-customer-fault-scenarios.md L153-L156】。

##### 1.5.2 URMA JFS异常 [kvcache_conn_fault_024]

* 故障编码：kvcache_conn_fault_024
* 故障名称：URMA JFS异常
* 验证方法：INFO log含Failed to import jfr或advise jfr
* 故障现象：
  * case 1:
    * 日志入口：grep '\[URMA_RECREATE_JFS\]' $LOG/datasystem_worker.INFO.log $LOG/ds_client_*.INFO.log | tail -50，输出格式：`<timestamp> | I | <source>:<line> | <host> | <tid:fid> | <traceId> | <tenant> | [URMA_*] ...`【来源：08-fault-triage-consolidated.md L218-L219】
    * 关键字：[URMA_RECREATE_JFS]+cqeStatus=9（ACK TIMEOUT）
    * 匹配逻辑：grep输出中同一行或相邻行同时含`[URMA_RECREATE_JFS]`和`cqeStatus=9`（如`[URMA_RECREATE_JFS] cqeStatus=9 ...`）
  * case 2:
    * 日志入口：grep '\[URMA_RECREATE_JFS_FAILED\]' $LOG/datasystem_worker.INFO.log $LOG/ds_client_*.INFO.log | tail -50，输出格式：`<timestamp> | I | <source>:<line> | <host> | <tid:fid> | <traceId> | <tenant> | [URMA_RECREATE_JFS_FAILED] ...`【来源：08-fault-triage-consolidated.md L220-L221】
    * 关键字：[URMA_RECREATE_JFS_FAILED]连续出现
    * 匹配逻辑：grep `[URMA_RECREATE_JFS_FAILED]` 输出非空，且连续出现≥2次（如相邻2行都含此关键字）
    * 说明：需看[URMA_RECREATE_JFS_SKIP]是否并存（connection已过期则属正常跳过）；否则查UMDK/驱动日志并上报URMA团队【来源：08-fault-triage-consolidated.md L220-L221】
* 故障原因：JFS异常自动重建（cqeStatus=9 ACK TIMEOUT）；JFS重建失败【来源：08-fault-triage-consolidated.md L218-L221】。
* 解决方法：无[URMA_RECREATE_JFS_FAILED]→自愈成功；有且连续→查UMDK/驱动日志并上报URMA团队【来源：08-fault-triage-consolidated.md L218-L221】。

##### 1.5.3 URMA驱动/CQ错误 [kvcache_conn_fault_025]

* 故障编码：kvcache_conn_fault_025
* 故障名称：URMA驱动/CQ错误
* 验证方法：INFO log含URMA CQ error或URMA driver error
* 故障现象：
  * case 1:
    * 日志入口：grep '\[URMA_POLL_ERROR\]' $LOG/datasystem_worker.INFO.log $LOG/ds_client_*.INFO.log | tail -50，输出格式：`<timestamp> | I | <source>:<line> | <host> | <tid:fid> | <traceId> | <tenant> | [URMA_POLL_ERROR] ...`【来源：08-fault-triage-consolidated.md L226-L227，10-customer-fault-scenarios.md L148-L149】
    * 关键字：[URMA_POLL_ERROR]
    * 匹配逻辑：grep `[URMA_POLL_ERROR]` 输出非空
    * 说明：PollJfcWait报错（驱动/硬件），需看同期是否伴[URMA_WAIT_TIMEOUT]，驱动错先grep UMDK日志/dmesg【来源：08-fault-triage-consolidated.md L226-L227，10-customer-fault-scenarios.md L157-L158】
  * case 2:
    * 日志入口：grep '\[URMA_WAIT_TIMEOUT\]' $LOG/datasystem_worker.INFO.log $LOG/ds_client_*.INFO.log | tail -50，输出格式：`<timestamp> | I | <source>:<line> | <host> | <tid:fid> | <traceId> | <tenant> | [URMA_WAIT_TIMEOUT] instanceId=<id> ...`【来源：08-fault-triage-consolidated.md L228-L229，10-customer-fault-scenarios.md L148-L149】
    * 关键字：[URMA_WAIT_TIMEOUT]（code=1010）
    * 匹配逻辑：grep `[URMA_WAIT_TIMEOUT]` 输出非空
    * 说明：需看instanceId是否同期变动，变动则与1.5.1合并；单独出现则SDK重试白名单自愈【来源：08-fault-triage-consolidated.md L228-L229】
* 故障原因：PollJfcWait报错（驱动/硬件）或等待CQE超时【来源：08-fault-triage-consolidated.md L226-L229，10-customer-fault-scenarios.md L157-L158】。
* 解决方法：grep UMDK日志/dmesg；SDK重试白名单自愈【来源：08-fault-triage-consolidated.md L226-L229，10-customer-fault-scenarios.md L157-L158】。

##### 1.5.4 URMA建连失败（code=1009） [kvcache_conn_fault_026]

* 故障编码：kvcache_conn_fault_026
* 故障名称：URMA建连失败
* 验证方法：KVCache错误码为1009或INFO log含[URMA_CONNECT_FAILED]
* 故障现象：
  * case 1:
    * 日志入口：查询KVCache错误码：grep "DS_KV_CLIENT_PUT\|DS_KV_CLIENT_GET" $LOG/ds_client_access_*.log | awk -F'|' '{print $1}' | sort | uniq -c，输出格式：`<count> <code>`（如 ` 120 0`、`  3 2`、`  1 1002`），字段含义：code=错误码【来源：10-customer-fault-scenarios.md L148-L149】
    * 关键字：返回错误码中有1009（K_URMA_CONNECT_FAILED）
    * 匹配逻辑：在`uniq -c`输出中code有1009（如`  1 1009`），或grep日志能找到`[URMA_CONNECT_FAILED]`
  * case 2:
    * 执行命令行：ifconfig ub0；ubinfo【来源：08-fault-triage-consolidated.md L230-L231，10-customer-fault-scenarios.md L148-L149】
    * 关键字：UB端口down
    * 匹配逻辑：运行`ifconfig ub0`，输出中包含`DOWN`字样则匹配
  * case 3:
    * 执行命令行：ls /dev/ub*【来源：08-fault-triage-consolidated.md L230-L231】
    * 关键字：设备节点缺失
    * 匹配逻辑：运行`ls /dev/ub*`，无任何输出则匹配
* 故障原因：URMA建连失败，UB端口down或设备节点缺失【来源：08-fault-triage-consolidated.md L230-L231，10-customer-fault-scenarios.md L148-L149】。
* 解决方法：ifconfig ub0 up；检查UB设备节点【来源：08-fault-triage-consolidated.md L230-L231，10-customer-fault-scenarios.md L186-L187】。

##### 1.5.5 URMA初始化失败 [kvcache_conn_fault_027]

* 故障编码：kvcache_conn_fault_027
* 故障名称：URMA初始化失败
* 验证方法：INFO log含Failed to urma init或Failed to urma get device by name或Failed to urma get eid list或Failed to urma create context或Failed to initialize URMA dlopen loader
* 故障现象：
  * 日志入口：grep '\[URMA_' $LOG/datasystem_worker.INFO.log | tail -20，输出格式：`<timestamp> | I | <source>:<line> | <host> | <tid:fid> | <traceId> | <tenant> | [URMA_*] ...`【来源：10-customer-fault-scenarios.md L148-L149】
  * 关键字：满足以下任一：Failed to urma init、Failed to urma get device by name、Failed to urma get eid list、Failed to urma create context、Failed to initialize URMA dlopen loader【来源：03-fault-mode-library.md L56-L57】
  * 匹配逻辑：grep输出非空，含`Failed to urma init`/`Failed to urma get device by name`/`Failed to urma get eid list`/`Failed to urma create context`/`Failed to initialize URMA dlopen loader`中的任一个
* 故障原因：UB初始化失败（UMDK设备/context/jfc等）【来源：03-fault-mode-library.md L56-L57】。
* 解决方法：UB/URMA运维排查【来源：10-customer-fault-scenarios.md L148-L149】。

##### 1.5.6 FastTransport/握手失败 [kvcache_conn_fault_028]

* 故障编码：kvcache_conn_fault_028
* 故障名称：FastTransport/握手失败
* 验证方法：INFO log含Fast transport handshake failed或Failed to import jfr或advise jfr
* 故障现象：
  * 日志入口：grep -E 'Fast transport handshake|Failed to import jfr|advise jfr' $LOG/datasystem_worker.INFO.log $LOG/ds_client_*.INFO.log | tail -50，输出格式：`<timestamp> | I | <source>:<line> | <host> | <tid:fid> | <traceId> | <tenant> | Fast transport handshake failed ...` 或 `Failed to import jfr ...`【来源：03-fault-mode-library.md L95-L96】
  * 关键字：满足以下任一：Fast transport handshake failed、Failed to import jfr、advise jfr【来源：03-fault-mode-library.md L60-L61，L95-L96】
  * 匹配逻辑：grep输出非空，含`Fast transport handshake failed`/`Failed to import jfr`/`advise jfr`中的任一个
* 故障原因：UB握手失败、回退【来源：03-fault-mode-library.md L60-L61】。
* 解决方法：UB/URMA运维排查【来源：10-customer-fault-scenarios.md L148-L149】。

##### 1.5.7 URMA数据面读写失败 [kvcache_conn_fault_029]

* 故障编码：kvcache_conn_fault_029
* 故障名称：URMA数据面读写失败
* 验证方法：INFO log含Failed to urma write object或Failed to urma read object
* 故障现象：
  * 日志入口：grep -E 'Failed to urma write|Failed to urma read|urma_write|urma_read' $LOG/datasystem_worker.INFO.log $LOG/ds_client_*.INFO.log | tail -50，输出格式：`<timestamp> | I | <source>:<line> | <host> | <tid:fid> | <traceId> | <tenant> | Failed to urma write object ...` 或 `Failed to urma read object ...`【来源：03-fault-mode-library.md L95-L96】
  * 关键字：满足以下任一：Failed to urma write object、Failed to urma read object【来源：03-fault-mode-library.md L64-L65，L95-L96】
  * 匹配逻辑：grep输出非空，含`Failed to urma write object`或`Failed to urma read object`中的任一个
* 故障原因：读写到对端UB失败【来源：03-fault-mode-library.md L64-L65】。
* 解决方法：UB/URMA运维排查【来源：10-customer-fault-scenarios.md L148-L149】。

#### 1.6 OS错误（code ∈ {5,6,7,13,18}） [kvcache_conn_fault_031]

* 故障编码：kvcache_conn_fault_031
* 故障名称：OS错误
* 故障下级编码：kvcache_conn_fault_032、kvcache_conn_fault_033、kvcache_conn_fault_034、kvcache_conn_fault_035、kvcache_conn_fault_036、kvcache_conn_fault_037
* 验证方法：KVCache错误码为5(K_RUNTIME_ERROR)、6(K_OUT_OF_MEMORY)、7(K_IO_ERROR)、13(K_NO_SPACE)或18(K_FILE_LIMIT_REACHED)
* 故障现象：
  * 日志入口：查询KVCache错误码：grep "DS_KV_CLIENT_PUT\|DS_KV_CLIENT_GET" $LOG/ds_client_access_*.log | awk -F'|' '{print $1}' | sort | uniq -c，输出格式：`<count> <code>`（如 ` 120 0`、`  3 2`、`  1 1002`），字段含义：code=错误码【来源：08-fault-triage-consolidated.md L12-L14，10-customer-fault-scenarios.md L40-L42】
  * 关键字：返回错误码中有5（K_RUNTIME_ERROR）、6（K_OUT_OF_MEMORY）、7（K_IO_ERROR）、13（K_NO_SPACE）、18（K_FILE_LIMIT_REACHED）【来源：08-fault-triage-consolidated.md L73-L74，10-customer-fault-scenarios.md L78-L80】
  * 匹配逻辑：在`uniq -c`输出中，第二列(code)有5/6/7/13/18中的任一个（如`  2 6`、`  1 13`）
* 故障原因：向下级匹配。
* 解决方法：向下级匹配。

##### 1.6.1 内存不足（code=6） [kvcache_conn_fault_032]

* 故障编码：kvcache_conn_fault_032
* 故障名称：内存不足
* 验证方法：KVCache错误码为6(K_OUT_OF_MEMORY)或dmesg含Out of memory或free -h可用内存不足
* 故障现象：
  * case 1:
    * 日志入口：查询KVCache错误码：grep "DS_KV_CLIENT_PUT\|DS_KV_CLIENT_GET" $LOG/ds_client_access_*.log | awk -F'|' '{print $1}' | sort | uniq -c，输出格式：`<count> <code>`（如 ` 120 0`、`  3 2`、`  1 1002`），字段含义：code=错误码【来源：10-customer-fault-scenarios.md L139-L140】
    * 关键字：返回错误码中有6（K_OUT_OF_MEMORY）
    * 匹配逻辑：在`uniq -c`输出中，第二列(code)有6（如`  2 6`）
  * case 2:
    * 执行命令行：dmesg | grep -i 'Out of memory'【来源：08-fault-triage-consolidated.md L226-L227，10-customer-fault-scenarios.md L139-L140】
    * 关键字：Out of memory
    * 匹配逻辑：运行`dmesg | grep -i 'Out of memory'`，输出非空则匹配
  * case 3:
    * 执行命令行：free -h【来源：08-fault-triage-consolidated.md L226-L227，10-customer-fault-scenarios.md L139-L140】
    * 关键字：可用内存不足
    * 匹配逻辑：运行`free -h`，看`available`列的值（如`500M`），若低于正常基线（如<1GB）则匹配
* 故障原因：OS内存不足（ENOMEM）【来源：08-fault-triage-consolidated.md L226-L227，10-customer-fault-scenarios.md L139-L140】。
* 解决方法：扩内存/调cgroup上限【来源：08-fault-triage-consolidated.md L226-L227，10-customer-fault-scenarios.md L139-L140】。

##### 1.6.2 IO错误（code=7） [kvcache_conn_fault_033]

* 故障编码：kvcache_conn_fault_033
* 故障名称：IO错误
* 验证方法：KVCache错误码为7(K_IO_ERROR)或dmesg含块设备/文件系统错误
* 故障现象：
  * case 1:
    * 日志入口：查询KVCache错误码：grep "DS_KV_CLIENT_PUT\|DS_KV_CLIENT_GET" $LOG/ds_client_access_*.log | awk -F'|' '{print $1}' | sort | uniq -c，输出格式：`<count> <code>`（如 ` 120 0`、`  3 2`、`  1 1002`），字段含义：code=错误码【来源：10-customer-fault-scenarios.md L139-L140】
    * 关键字：返回错误码中有7（K_IO_ERROR）
    * 匹配逻辑：在`uniq -c`输出中，第二列(code)有7（如`  1 7`）
  * case 2:
    * 执行命令行：dmesg【来源：08-fault-triage-consolidated.md L226-L227，10-customer-fault-scenarios.md L139-L140】
    * 关键字：块设备/文件系统错误
    * 匹配逻辑：运行`dmesg | grep 'I/O error'`，输出非空则匹配
    * 说明：分布式网盘POSIX接口失败同样归此【来源：08-fault-triage-consolidated.md L226-L227】
* 故障原因：块设备/文件系统IO错误（EIO）【来源：08-fault-triage-consolidated.md L226-L227，10-customer-fault-scenarios.md L139-L140】。
* 解决方法：修文件系统/挂载；分布式网盘故障联系存储运维【来源：10-customer-fault-scenarios.md L139-L140】。

##### 1.6.3 磁盘空间不足（code=13） [kvcache_conn_fault_034]

* 故障编码：kvcache_conn_fault_034
* 故障名称：磁盘空间不足
* 验证方法：KVCache错误码为13(K_NO_SPACE)或df -h磁盘使用率接近100%或resource log含SPILL_HARD_DISK/SHARED_DISK空间接近TOTAL_LIMIT
* 故障现象：
  * case 1:
    * 日志入口：查询KVCache错误码：grep "DS_KV_CLIENT_PUT\|DS_KV_CLIENT_GET" $LOG/ds_client_access_*.log | awk -F'|' '{print $1}' | sort | uniq -c，输出格式：`<count> <code>`（如 ` 120 0`、`  3 2`、`  1 1002`），字段含义：code=错误码【来源：10-customer-fault-scenarios.md L139-L140】
    * 关键字：返回错误码中有13（K_NO_SPACE）
    * 匹配逻辑：在`uniq -c`输出中，第二列(code)有13（如`  1 13`）
  * case 2:
    * 执行命令行：df -h【来源：08-fault-triage-consolidated.md L226-L227，10-customer-fault-scenarios.md L139-L140】
    * 关键字：磁盘使用率接近100%
    * 匹配逻辑：运行`df -h`，看`Use%`列的值（如`97%`），若≥95%则匹配
  * case 3:
    * 日志入口：grep -E 'SPILL_HARD_DISK|SHARED_DISK' $LOG/resource.log | tail -5，输出格式：`SPILL_HARD_DISK: SPACE_USAGE=<N>MB, TOTAL_LIMIT=<N>MB` / `SHARED_DISK: USAGE=<N>MB, TOTAL_LIMIT=<N>MB`【来源：08-fault-triage-consolidated.md L226-L227，10-customer-fault-scenarios.md L139-L140】
    * 关键字：SPILL_HARD_DISK或SHARED_DISK空间接近TOTAL_LIMIT
    * 匹配逻辑：在resource.log中找到`SPILL_HARD_DISK: SPACE_USAGE=<N>MB, TOTAL_LIMIT=<N>MB`或`SHARED_DISK: USAGE=<N>MB, TOTAL_LIMIT=<N>MB`行，USAGE/SPACE_USAGE≥TOTAL_LIMIT×90%则匹配
* 故障原因：磁盘空间不足（ENOSPC）【来源：08-fault-triage-consolidated.md L226-L227，10-customer-fault-scenarios.md L139-L140】。
* 解决方法：清理/扩容（本地盘或分布式网盘挂载点）【来源：08-fault-triage-consolidated.md L226-L227，10-customer-fault-scenarios.md L139-L140】。

##### 1.6.4 文件描述符耗尽（code=18） [kvcache_conn_fault_035]

* 故障编码：kvcache_conn_fault_035
* 故障名称：文件描述符耗尽
* 验证方法：KVCache错误码为18(K_FILE_LIMIT_REACHED)或fd数量接近ulimit -n的值
* 故障现象：
  * case 1:
    * 日志入口：查询KVCache错误码：grep "DS_KV_CLIENT_PUT\|DS_KV_CLIENT_GET" $LOG/ds_client_access_*.log | awk -F'|' '{print $1}' | sort | uniq -c，输出格式：`<count> <code>`（如 ` 120 0`、`  3 2`、`  1 1002`），字段含义：code=错误码【来源：10-customer-fault-scenarios.md L139-L140】
    * 关键字：返回错误码中有18（K_FILE_LIMIT_REACHED）
    * 匹配逻辑：在`uniq -c`输出中，第二列(code)有18（如`  1 18`）
  * case 2:
    * 执行命令行：ls /proc/<pid>/fd | wc -l【来源：08-fault-triage-consolidated.md L226-L227，10-customer-fault-scenarios.md L139-L140】
    * 关键字：fd数量接近ulimit -n的值
    * 匹配逻辑：步骤1：运行`ls /proc/<pid>/fd | wc -l`得到已开fd数（如`58000`）；步骤2：运行`ulimit -n`得到fd上限（如`65535`）；步骤3：若已开fd数≥上限×90%（如58000/65535=88.5%→接近）则匹配
  * case 3:
    * 执行命令行：ulimit -n【来源：10-customer-fault-scenarios.md L139-L140】
    * 关键字：fd上限值
    * 匹配逻辑：运行`ulimit -n`得到fd上限（如`65535`），与`ls /proc/<pid>/fd | wc -l`的已开fd数比较，若差距<10%则匹配
* 故障原因：文件描述符耗尽（EMFILE/ENFILE）【来源：08-fault-triage-consolidated.md L226-L227，10-customer-fault-scenarios.md L139-L140】。
* 解决方法：ulimit -n 65535（永久改/etc/security/limits.conf）【来源：08-fault-triage-consolidated.md L226-L227，10-customer-fault-scenarios.md L139-L140、L186-L187】。

##### 1.6.5 mmap失败（code=5） [kvcache_conn_fault_036]

* 故障编码：kvcache_conn_fault_036
* 故障名称：mmap失败
* 验证方法：KVCache错误码为5(K_RUNTIME_ERROR)且INFO log含Get mmap entry failed
* 故障现象：
  * case 1:
    * 日志入口：grep -E 'K_RUNTIME_ERROR|Get mmap entry failed' $LOG/datasystem_worker.INFO.log | tail -50，输出格式：`<timestamp> | I | <source>:<line> | <host> | <tid:fid> | <traceId> | <tenant> | K_RUNTIME_ERROR ... Get mmap entry failed ...`【来源：08-fault-triage-consolidated.md L86-L87、L233-L234，03-fault-mode-library.md L95-L96】
    * 关键字：需同时满足K_RUNTIME_ERROR和Get mmap entry failed
    * 匹配逻辑：在`uniq -c`输出中code有5（如`  2 5`），且grep `Get mmap entry failed` 输出非空
  * case 2:
    * 执行命令行：ulimit -l【来源：08-fault-triage-consolidated.md L233-L234，10-customer-fault-scenarios.md L186-L187】
    * 关键字：mlock限制值
    * 匹配逻辑：运行`ulimit -l`，输出不是`unlimited`（如`65536`）则匹配
  * case 3:
    * 执行命令行：cat /proc/<pid>/limits【来源：08-fault-triage-consolidated.md L233-L234】
    * 关键字：max locked memory限制
    * 匹配逻辑：运行`cat /proc/<pid>/limits`，找到`Max locked memory`行，值偏低（如`65536`KB低于SHM需求）则匹配
* 故障原因：mlock限制导致mmap失败（ENOMEM）【来源：08-fault-triage-consolidated.md L233-L234】。
* 解决方法：ulimit -l unlimited【来源：08-fault-triage-consolidated.md L233-L234，10-customer-fault-scenarios.md L186-L187】。

##### 1.6.6 code=5按日志串细分 [kvcache_conn_fault_037]

* 故障编码：kvcache_conn_fault_037
* 故障名称：code=5按日志串细分
* 验证方法：KVCache错误码为5(K_RUNTIME_ERROR)且需按日志串细分：Get mmap entry failed→OS；etcd is timeout/unavailable→三方etcd；urma→URMA
* 故障现象：
  * 日志入口：grep -E 'K_RUNTIME_ERROR|Get mmap entry failed|etcd is|urma' $LOG/datasystem_worker.INFO.log | tail -50，输出格式：`<timestamp> | I | <source>:<line> | <host> | <tid:fid> | <traceId> | <tenant> | K_RUNTIME_ERROR ... Get mmap entry failed ...`【来源：08-fault-triage-consolidated.md L86-L87】
  * 关键字：K_RUNTIME_ERROR
  * 匹配逻辑：在`uniq -c`输出中code有5（如`  2 5`），且grep输出非空（含`Get mmap entry failed`或`etcd is`或`urma`中的任一个）
  * 说明：code=5需按日志串细分："Get mmap entry failed"→OS（1.6.5）；"etcd is timeout/unavailable"→三方etcd（1.3）；"urma ... payload ..."→URMA（1.5）【来源：08-fault-triage-consolidated.md L86-L89】
* 故障原因：向下级匹配。
* 解决方法：向下级匹配。

#### 1.7 Client Init/连接Worker失败 [kvcache_conn_fault_038]

* 故障编码：kvcache_conn_fault_038
* 故障名称：Client Init/连接Worker失败
* 故障下级编码：kvcache_conn_fault_039、kvcache_conn_fault_040、kvcache_conn_fault_041、kvcache_conn_fault_042、kvcache_conn_fault_043
* 验证方法：INFO log含[TCP_CONNECT_FAILED]或[UDS_CONNECT_FAILED]或[SHM_FD_TRANSFER_FAILED]或ConnectOptions was not configured
* 故障现象：
  * case 1:
    * 日志入口：grep -E '\[(TCP|UDS|SHM_FD)_' $LOG/ds_client_<pid>.INFO.log | head，输出格式：`<timestamp> | I | <source>:<line> | <host> | <tid:fid> | <traceId> | <tenant> | [TCP_CONNECT_FAILED]/[UDS_CONNECT_FAILED]/[SHM_FD_TRANSFER_FAILED] ...`【来源：10-customer-fault-scenarios.md L539-L540】
    * 关键字：满足以下任一：[TCP_CONNECT_FAILED]、[UDS_CONNECT_FAILED]、[SHM_FD_TRANSFER_FAILED]
    * 匹配逻辑：grep输出非空，含`[TCP_CONNECT_FAILED]`/`[UDS_CONNECT_FAILED]`/`[SHM_FD_TRANSFER_FAILED]`中的任一个
  * case 2:
    * 日志入口：grep 'ConnectOptions was not configured' $LOG/ds_client_*.INFO.log，输出格式：`<timestamp> | I | <source>:<line> | <host> | <tid:fid> | <traceId> | <tenant> | ConnectOptions was not configured`【来源：10-customer-fault-scenarios.md L548-L549】
    * 关键字：ConnectOptions was not configured
    * 匹配逻辑：grep `ConnectOptions was not configured` 输出非空
* 故障原因：向下级匹配。
* 解决方法：向下级匹配。

##### 1.7.1 Worker进程不存在 [kvcache_conn_fault_039]

* 故障编码：kvcache_conn_fault_039
* 故障名称：Worker进程不存在
* 验证方法：pgrep -af datasystem_worker无结果
* 故障现象：
  * 执行命令行：pgrep -af datasystem_worker【来源：10-customer-fault-scenarios.md L513-L514】
  * 关键字：无datasystem_worker进程
  * 匹配逻辑：运行`pgrep -af datasystem_worker`，无任何输出则匹配（表示Worker进程不存在）
* 故障原因：DataSystem/编排问题，Worker未拉起【来源：10-customer-fault-scenarios.md L513-L514】。
* 解决方法：联系华为DS支持或编排侧拉起（systemd/k8s查重启原因：kubectl describe / journalctl -u ...）【来源：10-customer-fault-scenarios.md L513-L514】。

##### 1.7.2 Worker端口未LISTEN [kvcache_conn_fault_040]

* 故障编码：kvcache_conn_fault_040
* 故障名称：Worker端口未LISTEN
* 验证方法：ss -tnlp | grep <worker_port>无结果但Worker进程在
* 故障现象：
  * 执行命令行：ss -tnlp | grep <worker_port>【来源：10-customer-fault-scenarios.md L513-L514】
  * 关键字：Worker进程在但端口未LISTEN
  * 匹配逻辑：步骤1：运行`pgrep -af datasystem_worker`有输出（如`12345 /opt/datasystem_worker`）→进程存在；步骤2：运行`ss -tnlp | grep <worker_port>`无输出→端口未LISTEN→匹配
* 故障原因：DataSystem问题【来源：10-customer-fault-scenarios.md L513-L514】。
* 解决方法：上报华为DS支持【来源：10-customer-fault-scenarios.md L513-L514】。

##### 1.7.3 TCP建连失败（对端LISTEN） [kvcache_conn_fault_041]

* 故障编码：kvcache_conn_fault_041
* 故障名称：TCP建连失败（对端LISTEN）
* 验证方法：INFO log含[TCP_CONNECT_FAILED]且对端端口LISTEN
* 故障现象：
  * 日志入口：grep '\[TCP_CONNECT_FAILED\]' $LOG/ds_client_<pid>.INFO.log | head，输出格式：`<timestamp> | I | <source>:<line> | <host> | <tid:fid> | <traceId> | <tenant> | [TCP_CONNECT_FAILED] addr=<ip:port> ...`【来源：10-customer-fault-scenarios.md L539-L540】
  * 关键字：[TCP_CONNECT_FAILED]+对端LISTEN
  * 匹配逻辑：步骤1：grep `[TCP_CONNECT_FAILED]` 输出非空；步骤2：运行`ss -tnlp | grep <worker_port>`输出含端口号（如`LISTEN 0 128 *:31402`）→匹配
* 故障原因：主机/网络，防火墙/路由不通【来源：10-customer-fault-scenarios.md L539-L540】。
* 解决方法：iptables -L -n；nc -zv <worker> <port>；删除iptables DROP规则；检查安全组【来源：10-customer-fault-scenarios.md L539-L540】。

##### 1.7.4 UDS路径/权限问题 [kvcache_conn_fault_042]

* 故障编码：kvcache_conn_fault_042
* 故障名称：UDS路径/权限问题
* 验证方法：INFO log含[UDS_CONNECT_FAILED]
* 故障现象：
  * 日志入口：grep '\[UDS_CONNECT_FAILED\]' $LOG/ds_client_<pid>.INFO.log | head，输出格式：`<timestamp> | I | <source>:<line> | <host> | <tid:fid> | <traceId> | <tenant> | [UDS_CONNECT_FAILED] path=<path> ...`【来源：10-customer-fault-scenarios.md L539-L540】
  * 关键字：[UDS_CONNECT_FAILED]
  * 匹配逻辑：grep `[UDS_CONNECT_FAILED]` 输出非空
* 故障原因：主机，同机UDS路径/权限/tenant_id不一致【来源：10-customer-fault-scenarios.md L539-L540】。
* 解决方法：ls -la <uds_path>检查路径与权限；改权限/按部署文档挂载【来源：10-customer-fault-scenarios.md L539-L540】。

#### 1.8 机器/节点级故障 [kvcache_conn_fault_044]

* 故障编码：kvcache_conn_fault_044
* 故障名称：机器/节点级故障
* 故障下级编码：kvcache_conn_fault_045、kvcache_conn_fault_046、kvcache_conn_fault_047、kvcache_conn_fault_048、kvcache_conn_fault_049、kvcache_conn_fault_050
* 验证方法：INFO log含大量K_CLIENT_WORKER_DISCONNECT(23)/K_RPC_UNAVAILABLE(1002)/Cannot receive heartbeat from worker聚集在某节点
* 故障现象：
  * 日志入口：grep -E 'Cannot receive heartbeat from worker|K_CLIENT_WORKER_DISCONNECT' $LOG/datasystem_worker.INFO.log $LOG/ds_client_*.INFO.log | tail -50，输出格式：`<timestamp> | I | <source>:<line> | <host> | <tid:fid> | <traceId> | <tenant> | Cannot receive heartbeat from worker. ...` 或 `K_CLIENT_WORKER_DISCONNECT ...`【来源：10-customer-fault-scenarios.md L676-L677】
  * 关键字：大量K_CLIENT_WORKER_DISCONNECT(23)/K_RPC_UNAVAILABLE(1002)/Cannot receive heartbeat from worker聚集在某节点【来源：10-customer-fault-scenarios.md L676-L677】
  * 匹配逻辑：grep输出非空，含`K_CLIENT_WORKER_DISCONNECT`/`K_RPC_UNAVAILABLE`/`Cannot receive heartbeat from worker`中的任一个
* 故障原因：向下级匹配。
* 解决方法：向下级匹配。

##### 1.8.1 节点不可达 [kvcache_conn_fault_045]

* 故障编码：kvcache_conn_fault_045
* 故障名称：节点不可达
* 验证方法：ping -c 3 <node_ip>不通
* 故障现象：
  * 执行命令行：ping -c 3 <node_ip>【来源：10-customer-fault-scenarios.md L684-L685】
  * 关键字：ping不通
  * 匹配逻辑：运行`ping -c 3 <node_ip>`，输出含`unreachable`字样则匹配
* 故障原因：主机/基础设施，联系机房/云平台【来源：10-customer-fault-scenarios.md L686-L687】。
* 解决方法：联系机房/云平台【来源：10-customer-fault-scenarios.md L686-L687】。

##### 1.8.2 节点NotReady（k8s） [kvcache_conn_fault_046]

* 故障编码：kvcache_conn_fault_046
* 故障名称：节点NotReady（k8s）
* 验证方法：kubectl describe node含taints/conditions异常
* 故障现象：
  * 执行命令行：kubectl describe node <n>【来源：10-customer-fault-scenarios.md L686-L687】
  * 关键字：taints/conditions异常
  * 匹配逻辑：运行`kubectl describe node <n>`，输出含`NotReady`或异常taints（如`node.kubernetes.io/not-ready`）则匹配
* 故障原因：编排/主机问题【来源：10-customer-fault-scenarios.md L686-L687】。
* 解决方法：编排/主机运维排查【来源：10-customer-fault-scenarios.md L686-L687】。

##### 1.8.3 Worker进程被OOM Killer杀掉 [kvcache_conn_fault_047]

* 故障编码：kvcache_conn_fault_047
* 故障名称：Worker进程被OOM Killer杀掉
* 验证方法：dmesg含OOM killer杀掉datasystem_worker
* 故障现象：
  * case 1:
    * 执行命令行：ssh <node> 'pgrep -af datasystem_worker'【来源：10-customer-fault-scenarios.md L694-L695】
    * 关键字：进程不存在
    * 匹配逻辑：运行`pgrep -af datasystem_worker`，无任何输出则匹配（表示Worker进程不存在）
  * case 2:
    * 执行命令行：ssh <node> 'dmesg | tail -100'【来源：10-customer-fault-scenarios.md L694-L695】
    * 关键字：OOM killer杀掉datasystem_worker
    * 匹配逻辑：运行`dmesg | grep 'OOM killer'`输出非空，且`dmesg | grep datasystem_worker`输出非空→匹配
* 故障原因：主机OOM【来源：10-customer-fault-scenarios.md L698-L699】。
* 解决方法：扩内存/调cgroup；补内存后编排拉起【来源：10-customer-fault-scenarios.md L698-L699】。

##### 1.8.4 Worker进程crash（非OOM） [kvcache_conn_fault_048]

* 故障编码：kvcache_conn_fault_048
* 故障名称：Worker进程crash（非OOM）
* 验证方法：Worker进程不存在且dmesg无OOM记录
* 故障现象：
  * case 1:
    * 执行命令行：ssh <node> 'pgrep -af datasystem_worker'【来源：10-customer-fault-scenarios.md L694-L695】
    * 关键字：进程不存在
    * 匹配逻辑：运行`pgrep -af datasystem_worker`，无任何输出则匹配（表示Worker进程不存在）
  * case 2:
    * 执行命令行：ssh <node> 'journalctl -u <worker-service> -n 200'【来源：10-customer-fault-scenarios.md L694-L695】
    * 关键字：非零退出码但无OOM
    * 匹配逻辑：运行`journalctl -u datasystem-worker`显示非零退出码，且`dmesg | grep OOM`无输出（非OOM导致）→匹配
* 故障原因：DataSystem进程crash【来源：10-customer-fault-scenarios.md L698-L699】。
* 解决方法：上报华为+附journalctl/core dump【来源：10-customer-fault-scenarios.md L698-L699】。

##### 1.8.5 Worker进程在但端口不LISTEN [kvcache_conn_fault_049]

* 故障编码：kvcache_conn_fault_049
* 故障名称：Worker进程在但端口不LISTEN
* 验证方法：Worker进程在但ss -tnlp无端口LISTEN
* 故障现象：
  * 执行命令行：ssh <node> 'pgrep -af datasystem_worker' && ssh <node> 'ss -tnlp | grep <worker_port>'【来源：10-customer-fault-scenarios.md L698-L699】
  * 关键字：进程在但端口未LISTEN
  * 匹配逻辑：步骤1：运行`pgrep -af datasystem_worker`有输出（如`12345 /opt/datasystem_worker`）→进程存在；步骤2：运行`ss -tnlp | grep <worker_port>`无输出→端口未LISTEN→匹配
* 故障原因：DataSystem问题【来源：10-customer-fault-scenarios.md L698-L699】。
* 解决方法：上报华为DS支持【来源：10-customer-fault-scenarios.md L698-L699】。

##### 1.8.6 Worker进程在、端口LISTEN但心跳断 [kvcache_conn_fault_050]

* 故障编码：kvcache_conn_fault_050
* 故障名称：Worker进程在、端口LISTEN但心跳断
* 验证方法：Worker进程在、端口LISTEN但业务心跳断
* 故障现象：
  * 执行命令行：ssh <node> 'pgrep -af datasystem_worker' && ssh <node> 'ss -tnlp | grep <worker_port>'【来源：10-customer-fault-scenarios.md L698-L699】
  * 关键字：进程在、端口LISTEN但业务心跳断
  * 匹配逻辑：步骤1：运行`pgrep -af datasystem_worker`有输出（如`12345 /opt/datasystem_worker`）→进程存在；步骤2：运行`ss -tnlp | grep <worker_port>`输出含端口号（如`LISTEN 0 128 *:31402`）→端口在LISTEN；步骤3：grep `Cannot receive heartbeat from worker` 输出非空→心跳断→匹配
* 故障原因：主机/网络（中间网络路径）【来源：10-customer-fault-scenarios.md L698-L699】。
* 解决方法：查iptables/路由/MTU【来源：10-customer-fault-scenarios.md L698-L699】。
