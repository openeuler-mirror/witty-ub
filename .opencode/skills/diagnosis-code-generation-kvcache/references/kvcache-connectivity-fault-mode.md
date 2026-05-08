# 文档：KVCache通断异常故障模式树

### 1 KVCache通断异常

* 故障现象：
  * case 1:
    * 日志入口：查询KVCache错误码：grep "DS_KV_CLIENT_PUT\|DS_KV_CLIENT_GET" $LOG/ds_client_access_*.log | awk -F'|' '{print $1}' | sort | uniq -c【来源：08-fault-triage-consolidated.md §1.1，10-customer-fault-scenarios.md §2.2】
    * 关键字：返回错误码非0
  * case 2:
    * 日志入口：查询KVCache错误码：grep "DS_KV_CLIENT_PUT\|DS_KV_CLIENT_GET" $LOG/ds_client_access_*.log | awk -F'|' '{print $1}' | sort | uniq -c【来源：08-fault-triage-consolidated.md §1.1，10-customer-fault-scenarios.md §2.2】
    * 关键字：code=0但respMsg含NOT_FOUND或Can't find object
    * 说明：K_NOT_FOUND在access log会被记成code=0，业务"查不到"场景需同时看respMsg【来源：08-fault-triage-consolidated.md §1.1，10-customer-fault-scenarios.md §2.2】
* 故障原因：向下级匹配。
* 解决方法：向下级匹配。

#### 1.1 用户侧错误（code ∈ {2,3,8}）

* 故障现象：
  * 日志入口：查询KVCache错误码：grep "DS_KV_CLIENT_PUT\|DS_KV_CLIENT_GET" $LOG/ds_client_access_*.log | awk -F'|' '{print $1}' | sort | uniq -c【来源：08-fault-triage-consolidated.md §1.1，10-customer-fault-scenarios.md §2.2】
  * 关键字：返回错误码中有2（K_INVALID）、3（K_NOT_FOUND）、8（K_NOT_READY）【来源：08-fault-triage-consolidated.md §2.2，10-customer-fault-scenarios.md §2.3】
* 故障原因：向下级匹配。
* 解决方法：向下级匹配。

##### 1.1.1 参数非法

* 故障现象：
  * case 1:
    * 日志入口：grep '^2 |' $LOG/ds_client_access_*.log 或 grep "K_INVALID" $LOG/ds_client_*.INFO.log【来源：10-customer-fault-scenarios.md §4.1步骤1】
    * 关键字：满足以下任一：The objectKey is empty、dataSize should be bigger than zero、length not match【来源：08-fault-triage-consolidated.md §3.5.1，10-customer-fault-scenarios.md §4.1步骤1】
  * case 2:
    * 日志入口：grep "K_INVALID" $LOG/ds_client_*.INFO.log【来源：10-customer-fault-scenarios.md §4.1步骤1】
    * 关键字：K_INVALID
* 故障原因：业务参数非法【来源：08-fault-triage-consolidated.md §3.5.1，10-customer-fault-scenarios.md §4.1步骤1】。
* 解决方法：业务校验【来源：08-fault-triage-consolidated.md §3.5.1】。

##### 1.1.2 未配置Init

* 故障现象：
  * 日志入口：grep 'ConnectOptions was not configured' $LOG/ds_client_*.INFO.log【来源：08-fault-triage-consolidated.md §3.5.1，10-customer-fault-scenarios.md §4.1步骤1、§4.4步骤3】
  * 关键字：ConnectOptions was not configured
* 故障原因：未配置Init【来源：08-fault-triage-consolidated.md §3.5.1，10-customer-fault-scenarios.md §4.1步骤1】。
* 解决方法：检查Init【来源：08-fault-triage-consolidated.md §3.5.1】。

##### 1.1.3 buffer重复Publish

* 故障现象：
  * 日志入口：grep 'Client object is already sealed' $LOG/ds_client_*.INFO.log【来源：08-fault-triage-consolidated.md §3.5.1，10-customer-fault-scenarios.md §4.1步骤1】
  * 关键字：Client object is already sealed
* 故障原因：buffer重复Publish【来源：08-fault-triage-consolidated.md §3.5.1，10-customer-fault-scenarios.md §4.1步骤1】。
* 解决方法：检查业务逻辑【来源：08-fault-triage-consolidated.md §3.5.1】。

##### 1.1.4 批次超限

* 故障现象：
  * 日志入口：grep 'OBJECT_KEYS_MAX_SIZE_LIMIT' $LOG/ds_client_access_*.log【来源：08-fault-triage-consolidated.md §3.5.1，10-customer-fault-scenarios.md §4.1步骤1】
  * 关键字：OBJECT_KEYS_MAX_SIZE_LIMIT
* 故障原因：批次超限【来源：08-fault-triage-consolidated.md §3.5.1，10-customer-fault-scenarios.md §4.1步骤1】。
* 解决方法：拆batch【来源：08-fault-triage-consolidated.md §3.5.1】。

##### 1.1.5 对象不存在

* 故障现象：
  * case 1:
    * 日志入口：grep -E 'K_NOT_FOUND|Can.?t find object' $LOG/ds_client_*.INFO.log【来源：08-fault-triage-consolidated.md §3.5.1，10-customer-fault-scenarios.md §4.2步骤1】
    * 关键字：满足以下任一：K_NOT_FOUND、Can't find object
  * case 2:
    * 日志入口：grep "DS_KV_CLIENT_GET" $LOG/ds_client_access_*.log | awk -F'|' '{print $1, $NF}' | sort | uniq -c | head【来源：10-customer-fault-scenarios.md §4.2步骤1】
    * 关键字：code=0 + respMsg含NOT_FOUND或Can't find object
    * 说明：K_NOT_FOUND在access log会被记成code=0，不要只看code非0判断【来源：10-customer-fault-scenarios.md §4.2步骤1】
* 故障原因：对象不存在【来源：08-fault-triage-consolidated.md §3.5.1】。
* 解决方法：业务自查key【来源：08-fault-triage-consolidated.md §3.5.1】；检查业务是否先Put再Get、key生成逻辑、TTL是否提前过期【来源：10-customer-fault-scenarios.md §4.2步骤1、步骤2】。

##### 1.1.6 SDK未就绪

* 故障现象：
  * 日志入口：查询KVCache错误码：grep "DS_KV_CLIENT_PUT\|DS_KV_CLIENT_GET" $LOG/ds_client_access_*.log | awk -F'|' '{print $1}' | sort | uniq -c【来源：10-customer-fault-scenarios.md §2.3】
  * 关键字：返回错误码中有8（K_NOT_READY）
* 故障原因：未Init / 正在shutdown【来源：10-customer-fault-scenarios.md §4.2步骤1、§4.4步骤3】。
* 解决方法：业务检查SDK生命周期【来源：10-customer-fault-scenarios.md §4.2步骤1】。

#### 1.2 DS进程内错误（code ∈ {19,23,29,31,32}）

* 故障现象：
  * 日志入口：查询KVCache错误码：grep "DS_KV_CLIENT_PUT\|DS_KV_CLIENT_GET" $LOG/ds_client_access_*.log | awk -F'|' '{print $1}' | sort | uniq -c【来源：08-fault-triage-consolidated.md §1.1，10-customer-fault-scenarios.md §2.2】
  * 关键字：返回错误码中有19（K_TRY_AGAIN）、23（K_CLIENT_WORKER_DISCONNECT）、29（K_SERVER_FD_CLOSED）、31（K_SCALE_DOWN）、32（K_SCALING）【来源：08-fault-triage-consolidated.md §2.2，10-customer-fault-scenarios.md §2.3】
* 故障原因：向下级匹配。
* 解决方法：向下级匹配。

##### 1.2.1 对端处理慢/拒绝

* 故障现象：
  * 日志入口：grep -E '\[RPC_RECV_TIMEOUT\]|\[RPC_SERVICE_UNAVAILABLE\]' $LOG/datasystem_worker.INFO.log $LOG/ds_client_*.INFO.log | tail -50【来源：08-fault-triage-consolidated.md §3.3，10-customer-fault-scenarios.md §4.1.5】
  * 关键字：需同时满足[RPC_RECV_TIMEOUT]和ZMQ fault=0；或匹配[RPC_SERVICE_UNAVAILABLE]【来源：08-fault-triage-consolidated.md §3.3，10-customer-fault-scenarios.md §4.1.5】
  * 说明：[RPC_RECV_TIMEOUT]且ZMQ fault=0表示对端处理慢拖超时，非网络问题【来源：08-fault-triage-consolidated.md §3.5.2(a)】
* 故障原因：对端Worker处理慢或主动拒绝，线程池打满【来源：08-fault-triage-consolidated.md §3.5.2(a)，10-customer-fault-scenarios.md §4.1.5】。
* 解决方法：查Worker CPU/锁；扩oc_rpc_thread_num【来源：08-fault-triage-consolidated.md §3.5.2(a)】。

##### 1.2.2 ZMQ相关问题（重建/断开/握手）

* 故障现象：
  * 日志入口：grep -E 'zmq_gateway_recreate_total|zmq_event_disconnect_total|zmq_event_handshake_failure_total' $LOG/datasystem_worker.INFO.log | tail -50【来源：08-fault-triage-consolidated.md §3.5.2(b)】
  * 关键字：满足以下任一：zmq_gateway_recreate_total↑、zmq_event_disconnect_total↑、zmq_event_handshake_failure_total↑，且对端Worker仍活【来源：08-fault-triage-consolidated.md §3.5.2(b)】
* 故障原因：ZMQ连接重建/断开/握手失败。低频忽略（SDK自重连）；高频转OS查网络；握手失败查TLS/认证配置【来源：08-fault-triage-consolidated.md §3.5.2(b)】。
* 解决方法：低频忽略；高频查OS网络；握手失败查TLS/认证配置【来源：08-fault-triage-consolidated.md §3.5.2(b)】。

##### 1.2.3 三方etcd（信号出现在DS日志中）

* 故障现象：
  * 日志入口：grep -E 'etcd is timeout|etcd is unavailable' $LOG/datasystem_worker.INFO.log | tail -50【来源：08-fault-triage-consolidated.md §3.5.2(c)，10-customer-fault-scenarios.md §4.1.4】
  * 关键字：满足以下任一：etcd is timeout、etcd is unavailable【来源：08-fault-triage-consolidated.md §3.5.2(c)，10-customer-fault-scenarios.md §4.1.4】
  * 说明：常同屏出现code=1002/25【来源：08-fault-triage-consolidated.md §3.3】
* 故障原因：etcd集群或到etcd的网络异常。主责三方etcd【来源：08-fault-triage-consolidated.md §3.5.2(c)，10-customer-fault-scenarios.md §4.1.4】。
* 解决方法：systemctl status etcd；etcdctl endpoint status；查到etcd的网络【来源：08-fault-triage-consolidated.md §3.5.2(c)，10-customer-fault-scenarios.md §4.1.4】。

##### 1.2.4 心跳/生命周期/扩缩容

* 故障现象：
  * 日志入口：grep -E 'Cannot receive heartbeat from worker|HealthCheck.*Worker is exiting now|meta_is_moving' $LOG/datasystem_worker.INFO.log | tail -50【来源：08-fault-triage-consolidated.md §3.5.2(d)，10-customer-fault-scenarios.md §4.6步骤1】
  * 关键字：满足以下任一：Cannot receive heartbeat from worker（code=23）、[HealthCheck] Worker is exiting now、meta_is_moving（code=31/32）【来源：08-fault-triage-consolidated.md §3.5.2(d)，10-customer-fault-scenarios.md §4.6】
* 故障原因：心跳断→Worker被STOP；退出由编排拉起；扩缩容中SDK自重试【来源：08-fault-triage-consolidated.md §3.5.2(d)，10-customer-fault-scenarios.md §4.6】。
* 解决方法：心跳断→kill -CONT <pid>；退出由编排拉起；扩缩容SDK自重试【来源：08-fault-triage-consolidated.md §3.5.2(d)，10-customer-fault-scenarios.md §4.6步骤2】。

#### 1.3 三方etcd错误（code=25）

* 故障现象：
  * case 1:
    * 日志入口：查询KVCache错误码：grep "DS_KV_CLIENT_PUT\|DS_KV_CLIENT_GET" $LOG/ds_client_access_*.log | awk -F'|' '{print $1}' | sort | uniq -c【来源：08-fault-triage-consolidated.md §1.1，10-customer-fault-scenarios.md §2.2】
    * 关键字：返回错误码中有25（K_MASTER_TIMEOUT）【来源：08-fault-triage-consolidated.md §2.2，10-customer-fault-scenarios.md §2.3】
  * case 2:
    * 日志入口：grep -E 'etcd is timeout|etcd is unavailable' $LOG/*.INFO.log | tail -20【来源：10-customer-fault-scenarios.md §4.1.4】
    * 关键字：满足以下任一：etcd is timeout、etcd is unavailable
  * case 3:
    * 日志入口：grep 'ETCD_REQUEST_SUCCESS_RATE\|ETCD_QUEUE' $LOG/resource.log | tail -5【来源：10-customer-fault-scenarios.md §4.1.4】
    * 关键字：ETCD_QUEUE堆积或ETCD_REQUEST_SUCCESS_RATE下降
* 故障原因：etcd集群故障或到etcd的网络异常。主责三方etcd【来源：08-fault-triage-consolidated.md §2.2，10-customer-fault-scenarios.md §4.1.4】。
* 解决方法：systemctl status etcd；etcdctl endpoint status -w table；查到etcd的网络【来源：08-fault-triage-consolidated.md §3.5.2(c)，10-customer-fault-scenarios.md §4.1.4】。

#### 1.4 桶码错误（code ∈ {1001,1002}）

* 故障现象：
  * 日志入口：查询KVCache错误码：grep "DS_KV_CLIENT_PUT\|DS_KV_CLIENT_GET" $LOG/ds_client_access_*.log | awk -F'|' '{print $1}' | sort | uniq -c【来源：08-fault-triage-consolidated.md §1.1，10-customer-fault-scenarios.md §2.2】
  * 关键字：返回错误码中有1001（K_RPC_DEADLINE_EXCEEDED）或1002（K_RPC_UNAVAILABLE）【来源：08-fault-triage-consolidated.md §2.2，10-customer-fault-scenarios.md §2.3】
  * 说明：1002是桶码，DS crash、OS网络断、etcd不可用都会给1002，必须看日志前缀确定边界【来源：08-fault-triage-consolidated.md §2.2，10-customer-fault-scenarios.md §2.3】
* 故障原因：向下级匹配。
* 解决方法：向下级匹配。

##### 1.4.1 OS层（TCP/UDS/ZMQ系统调用层）

* 故障现象：
  * 日志入口：grep -E '\[(TCP|UDS|ZMQ|SHM_FD)_' $LOG/datasystem_worker.INFO.log $LOG/ds_client_*.INFO.log | tail -50【来源：08-fault-triage-consolidated.md §3.3，10-customer-fault-scenarios.md §4.1.5】
  * 关键字：满足以下任一且最先出现：[TCP_CONNECT_FAILED]+对端Worker活、[TCP_CONNECT_RESET]、[TCP_NETWORK_UNREACHABLE]、[UDS_CONNECT_FAILED]、[SHM_FD_TRANSFER_FAILED]、[ZMQ_SEND_FAILURE_TOTAL]、[ZMQ_RECEIVE_FAILURE_TOTAL]【来源：08-fault-triage-consolidated.md §3.3，10-customer-fault-scenarios.md §4.1.5】
* 故障原因：向下级匹配。
* 解决方法：向下级匹配。

###### 1.4.1.1 TCP建连失败（对端Worker活）

* 故障现象：
  * 日志入口：grep '\[TCP_CONNECT_FAILED\]' $LOG/datasystem_worker.INFO.log $LOG/ds_client_*.INFO.log | tail -50【来源：08-fault-triage-consolidated.md §3.3，10-customer-fault-scenarios.md §4.1.5】
  * 关键字：[TCP_CONNECT_FAILED]且对端Worker仍活
  * 说明：判"对端Worker活"的命令：pgrep -af datasystem_worker；ss -tnlp | grep <worker_port>【来源：10-customer-fault-scenarios.md §4.1.5】
* 故障原因：端口不通/iptables/路由【来源：08-fault-triage-consolidated.md §3.3，10-customer-fault-scenarios.md §4.1.5】。
* 解决方法：ss -tnlp；iptables -L -n；开端口/删规则【来源：08-fault-triage-consolidated.md §3.5.4，10-customer-fault-scenarios.md §4.1步骤3】。

###### 1.4.1.2 TCP连接重置/网络不可达

* 故障现象：
  * 日志入口：grep -E '\[TCP_CONNECT_RESET\]|\[TCP_NETWORK_UNREACHABLE\]' $LOG/datasystem_worker.INFO.log $LOG/ds_client_*.INFO.log | tail -50【来源：08-fault-triage-consolidated.md §3.3，10-customer-fault-scenarios.md §4.1.5】
  * 关键字：满足以下任一：[TCP_CONNECT_RESET]、[TCP_NETWORK_UNREACHABLE]
* 故障原因：网络闪断（除非同窗Worker重启）【来源：08-fault-triage-consolidated.md §3.3】。
* 解决方法：dmesg；netstat -s | grep reset【来源：08-fault-triage-consolidated.md §3.5.4，10-customer-fault-scenarios.md §4.4步骤2】。

###### 1.4.1.3 UDS/SHM传fd失败

* 故障现象：
  * case 1:
    * 日志入口：grep -E '\[UDS_CONNECT_FAILED\]|\[SHM_FD_TRANSFER_FAILED\]' $LOG/datasystem_worker.INFO.log $LOG/ds_client_*.INFO.log | tail -50【来源：08-fault-triage-consolidated.md §3.3，10-customer-fault-scenarios.md §4.1.5】
    * 关键字：满足以下任一：[UDS_CONNECT_FAILED]、[SHM_FD_TRANSFER_FAILED]
  * case 2:
    * 日志入口：grep '\[SHM_FD_TRANSFER_FAILED\]' $LOG/ds_client_<pid>.INFO.log | head【来源：10-customer-fault-scenarios.md §4.4步骤2】
    * 关键字：[SHM_FD_TRANSFER_FAILED]
    * 说明：检查ulimit -n（fd数）；SELinux/AppArmor；/proc/sys/fs/file-max【来源：10-customer-fault-scenarios.md §4.4步骤2】
* 故障原因：同机UDS路径/权限/fd上限；SCM_RIGHTS发送失败多为fd耗尽或权限问题【来源：08-fault-triage-consolidated.md §3.3、§3.5.4，10-customer-fault-scenarios.md §4.4步骤2】。
* 解决方法：检查UDS路径/权限；调大ulimit -n【来源：08-fault-triage-consolidated.md §3.5.4，10-customer-fault-scenarios.md §4.1步骤3、§4.4步骤2】。

###### 1.4.1.4 ZMQ发送/接收失败

* 故障现象：
  * 日志入口：grep -E '\[ZMQ_SEND_FAILURE_TOTAL\]|\[ZMQ_RECEIVE_FAILURE_TOTAL\]' $LOG/datasystem_worker.INFO.log $LOG/ds_client_*.INFO.log | tail -50【来源：08-fault-triage-consolidated.md §3.3，10-customer-fault-scenarios.md §4.1.5】
  * 关键字：满足以下任一：[ZMQ_SEND_FAILURE_TOTAL]、[ZMQ_RECEIVE_FAILURE_TOTAL]
* 故障原因：zmq_msg_send/recv硬失败，按zmq_last_error_number对照errno确定具体OS原因【来源：08-fault-triage-consolidated.md §3.3、§3.5.4】。
* 解决方法：按errno对照处置【来源：08-fault-triage-consolidated.md §3.5.4，10-customer-fault-scenarios.md §4.1.5】。errno对照表：11(EAGAIN背压)、101(ENETUNREACH路由不可达)、104(ECONNRESET对端reset)、110(ETIMEDOUT TCP超时)、111(ECONNREFUSED端口无监听)、113(EHOSTUNREACH主机不可达)【来源：08-fault-triage-consolidated.md §3.5.4，10-customer-fault-scenarios.md §4.1.5】。

##### 1.4.2 三方etcd层

* 故障现象：
  * 日志入口：grep -E 'etcd is timeout|etcd is unavailable' $LOG/datasystem_worker.INFO.log | tail -50【来源：08-fault-triage-consolidated.md §3.3，10-customer-fault-scenarios.md §4.1.4】
  * 关键字：满足以下任一：etcd is timeout、etcd is unavailable
  * 说明：常同屏出现code=1002/25【来源：08-fault-triage-consolidated.md §3.3】
* 故障原因：etcd集群或到etcd的网络异常【来源：08-fault-triage-consolidated.md §3.3，10-customer-fault-scenarios.md §4.1.4】。
* 解决方法：systemctl status etcd；etcdctl endpoint status；查到etcd的网络【来源：08-fault-triage-consolidated.md §3.5.2(c)，10-customer-fault-scenarios.md §4.1.4】。

##### 1.4.3 DS进程内层

* 故障现象：
  * case 1:
    * 日志入口：grep '\[TCP_CONNECT_FAILED\]' $LOG/datasystem_worker.INFO.log $LOG/ds_client_*.INFO.log | tail -50【来源：08-fault-triage-consolidated.md §3.3，10-customer-fault-scenarios.md §4.1.5】
    * 关键字：[TCP_CONNECT_FAILED]且对端Worker不在
    * 说明：判"对端Worker不在"：pgrep -af datasystem_worker无结果【来源：10-customer-fault-scenarios.md §4.1.5、§4.4步骤1】
  * case 2:
    * 日志入口：grep -E '\[RPC_RECV_TIMEOUT\]|\[RPC_SERVICE_UNAVAILABLE\]' $LOG/datasystem_worker.INFO.log $LOG/ds_client_*.INFO.log | tail -50【来源：08-fault-triage-consolidated.md §3.3，10-customer-fault-scenarios.md §4.1.5】
    * 关键字：[RPC_RECV_TIMEOUT]且ZMQ fault=0；或[RPC_SERVICE_UNAVAILABLE]
* 故障原因：Worker crash/未拉起/机器故障、对端处理慢拖超时、对端主动拒绝【来源：08-fault-triage-consolidated.md §3.3，10-customer-fault-scenarios.md §4.1.5】。
* 解决方法：查对端Worker存活；扩线程池【来源：08-fault-triage-consolidated.md §3.5.2(a)，10-customer-fault-scenarios.md §4.1.5】。

##### 1.4.4 待进一步验证（握手迟）

* 故障现象：
  * 日志入口：grep -E '\[SOCK_CONN_WAIT_TIMEOUT\]|\[REMOTE_SERVICE_WAIT_TIMEOUT\]' $LOG/datasystem_worker.INFO.log $LOG/ds_client_*.INFO.log | tail -50【来源：08-fault-triage-consolidated.md §3.3】
  * 关键字：满足以下任一：[SOCK_CONN_WAIT_TIMEOUT]、[REMOTE_SERVICE_WAIT_TIMEOUT]
  * 说明：需看对端Worker存活判断：活→OS网络慢，不活→DS【来源：08-fault-triage-consolidated.md §3.3】
* 故障原因：握手迟，需交叉验证对端Worker存活状态【来源：08-fault-triage-consolidated.md §3.3】。
* 解决方法：对端活→查OS网络；不活→查DS进程【来源：08-fault-triage-consolidated.md §3.3】。

#### 1.5 URMA错误（code ∈ {1004,1006,1008,1009,1010}）

* 故障现象：
  * 日志入口：查询KVCache错误码：grep "DS_KV_CLIENT_PUT\|DS_KV_CLIENT_GET" $LOG/ds_client_access_*.log | awk -F'|' '{print $1}' | sort | uniq -c【来源：08-fault-triage-consolidated.md §1.1，10-customer-fault-scenarios.md §2.2】
  * 关键字：返回错误码中有1004/1006/1008/1009/1010【来源：08-fault-triage-consolidated.md §2.2，10-customer-fault-scenarios.md §2.3】
* 故障原因：向下级匹配。
* 解决方法：向下级匹配。

##### 1.5.1 URMA会话重连

* 故障现象：
  * case 1:
    * 日志入口：grep '\[URMA_NEED_CONNECT\]' $LOG/datasystem_worker.INFO.log $LOG/ds_client_*.INFO.log | tail -50【来源：08-fault-triage-consolidated.md §3.5.3，10-customer-fault-scenarios.md §4.1.3】
    * 关键字：[URMA_NEED_CONNECT]+remoteInstanceId变化
    * 说明：remoteInstanceId变化表示对端Worker重启【来源：08-fault-triage-consolidated.md §3.5.3，10-customer-fault-scenarios.md §4.1.3】
  * case 2:
    * 日志入口：grep '\[URMA_NEED_CONNECT\]' $LOG/datasystem_worker.INFO.log $LOG/ds_client_*.INFO.log | tail -50【来源：08-fault-triage-consolidated.md §3.5.3，10-customer-fault-scenarios.md §4.1.3】
    * 关键字：[URMA_NEED_CONNECT]持续+instanceId不变
    * 说明：instanceId不变表示UB链路不稳，需查同期是否伴[URMA_POLL_ERROR]/[URMA_RECREATE_JFS]【来源：08-fault-triage-consolidated.md §3.5.3，10-customer-fault-scenarios.md §4.1.3】
##### 1.5.3 URMA驱动/CQ错误

* 故障现象：
  * case 1:
    * 日志入口：grep '\[URMA_POLL_ERROR\]' $LOG/datasystem_worker.INFO.log $LOG/ds_client_*.INFO.log | tail -50【来源：08-fault-triage-consolidated.md §3.5.3，10-customer-fault-scenarios.md §4.1.3，03-fault-mode-library.md §3.1】
    * 关键字：[URMA_POLL_ERROR]
    * 说明：PollJfcWait报错（驱动/硬件），需看同期是否伴[URMA_WAIT_TIMEOUT]，驱动错先grep UMDK日志/dmesg【来源：08-fault-triage-consolidated.md §3.5.3，10-customer-fault-scenarios.md §4.1.3】
  * case 2:
    * 日志入口：grep '\[URMA_WAIT_TIMEOUT\]' $LOG/datasystem_worker.INFO.log $LOG/ds_client_*.INFO.log | tail -50【来源：08-fault-triage-consolidated.md §3.5.3，10-customer-fault-scenarios.md §4.1.3】
    * 关键字：[URMA_WAIT_TIMEOUT]（code=1010）
    * 说明：需看instanceId是否同期变动，变动则与1.5.1合并；单独出现则SDK重试白名单自愈【来源：08-fault-triage-consolidated.md §3.5.3】
* 故障原因：PollJfcWait报错（驱动/硬件）或等待CQE超时【来源：08-fault-triage-consolidated.md §3.5.3，10-customer-fault-scenarios.md §4.1.3】。
* 解决方法：grep UMDK日志/dmesg；SDK重试白名单自愈【来源：08-fault-triage-consolidated.md §3.5.3，10-customer-fault-scenarios.md §4.1.3】。

##### 1.5.4 URMA建连失败（code=1009）

* 故障现象：
  * case 1:
    * 日志入口：查询KVCache错误码：grep "DS_KV_CLIENT_PUT\|DS_KV_CLIENT_GET" $LOG/ds_client_access_*.log | awk -F'|' '{print $1}' | sort | uniq -c【来源：10-customer-fault-scenarios.md §4.1.3】
    * 关键字：返回错误码中有1009（K_URMA_CONNECT_FAILED）
  * case 2:
    * 执行命令行：ifconfig ub0；ubinfo【来源：08-fault-triage-consolidated.md §3.5.3，10-customer-fault-scenarios.md §4.1.3】
    * 关键字：UB端口down
  * case 3:
    * 执行命令行：ls /dev/ub*【来源：08-fault-triage-consolidated.md §3.5.3】
    * 关键字：设备节点缺失
* 故障原因：URMA建连失败，UB端口down或设备节点缺失【来源：08-fault-triage-consolidated.md §3.5.3，10-customer-fault-scenarios.md §4.1.3】。
* 解决方法：ifconfig ub0 up；检查UB设备节点【来源：08-fault-triage-consolidated.md §3.5.3，10-customer-fault-scenarios.md §4.1步骤3】。

##### 1.5.5 URMA初始化失败

* 故障现象：
  * 日志入口：grep '\[URMA_' $LOG/datasystem_worker.INFO.log | tail -20【来源：10-customer-fault-scenarios.md §4.1.3】
  * 关键字：满足以下任一：Failed to urma init、Failed to urma get device by name、Failed to urma get eid list、Failed to urma create context、Failed to initialize URMA dlopen loader【来源：03-fault-mode-library.md §2 FM-003】
* 故障原因：UB初始化失败（UMDK设备/context/jfc等）【来源：03-fault-mode-library.md §2 FM-003】。
* 解决方法：UB/URMA运维排查【来源：10-customer-fault-scenarios.md §4.1.3】。

##### 1.5.6 FastTransport/握手失败

* 故障现象：
  * 日志入口：grep -E 'Fast transport handshake|Failed to import jfr|advise jfr' $LOG/datasystem_worker.INFO.log $LOG/ds_client_*.INFO.log | tail -50【来源：03-fault-mode-library.md §3.1】
  * 关键字：满足以下任一：Fast transport handshake failed、Failed to import jfr、advise jfr【来源：03-fault-mode-library.md §2 FM-005，§3.1】
* 故障原因：UB握手失败、回退【来源：03-fault-mode-library.md §2 FM-005】。
* 解决方法：UB/URMA运维排查【来源：10-customer-fault-scenarios.md §4.1.3】。

##### 1.5.7 URMA数据面读写失败

* 故障现象：
  * 日志入口：grep -E 'Failed to urma write|Failed to urma read|urma_write|urma_read' $LOG/datasystem_worker.INFO.log $LOG/ds_client_*.INFO.log | tail -50【来源：03-fault-mode-library.md §3.1】
  * 关键字：满足以下任一：Failed to urma write object、Failed to urma read object【来源：03-fault-mode-library.md §2 FM-010，§3.1】
* 故障原因：读写到对端UB失败【来源：03-fault-mode-library.md §2 FM-010】。
* 解决方法：UB/URMA运维排查【来源：10-customer-fault-scenarios.md §4.1.3】。

#### 1.6 OS错误（code ∈ {5,6,7,13,18}）

* 故障现象：
  * 日志入口：查询KVCache错误码：grep "DS_KV_CLIENT_PUT\|DS_KV_CLIENT_GET" $LOG/ds_client_access_*.log | awk -F'|' '{print $1}' | sort | uniq -c【来源：08-fault-triage-consolidated.md §1.1，10-customer-fault-scenarios.md §2.2】
  * 关键字：返回错误码中有5（K_RUNTIME_ERROR）、6（K_OUT_OF_MEMORY）、7（K_IO_ERROR）、13（K_NO_SPACE）、18（K_FILE_LIMIT_REACHED）【来源：08-fault-triage-consolidated.md §2.2，10-customer-fault-scenarios.md §2.3】
* 故障原因：向下级匹配。
* 解决方法：向下级匹配。

##### 1.6.1 内存不足（code=6）

* 故障现象：
  * case 1:
    * 日志入口：查询KVCache错误码：grep "DS_KV_CLIENT_PUT\|DS_KV_CLIENT_GET" $LOG/ds_client_access_*.log | awk -F'|' '{print $1}' | sort | uniq -c【来源：10-customer-fault-scenarios.md §4.1.2】
    * 关键字：返回错误码中有6（K_OUT_OF_MEMORY）
  * case 2:
    * 执行命令行：dmesg | grep -i 'Out of memory'【来源：08-fault-triage-consolidated.md §3.5.4，10-customer-fault-scenarios.md §4.1.2】
    * 关键字：Out of memory
  * case 3:
    * 执行命令行：free -h【来源：08-fault-triage-consolidated.md §3.5.4，10-customer-fault-scenarios.md §4.1.2】
    * 关键字：可用内存不足
* 故障原因：OS内存不足（ENOMEM）【来源：08-fault-triage-consolidated.md §3.5.4，10-customer-fault-scenarios.md §4.1.2】。
* 解决方法：扩内存/调cgroup上限【来源：08-fault-triage-consolidated.md §3.5.4，10-customer-fault-scenarios.md §4.1.2】。

##### 1.6.2 IO错误（code=7）

* 故障现象：
  * case 1:
    * 日志入口：查询KVCache错误码：grep "DS_KV_CLIENT_PUT\|DS_KV_CLIENT_GET" $LOG/ds_client_access_*.log | awk -F'|' '{print $1}' | sort | uniq -c【来源：10-customer-fault-scenarios.md §4.1.2】
    * 关键字：返回错误码中有7（K_IO_ERROR）
  * case 2:
    * 执行命令行：dmesg【来源：08-fault-triage-consolidated.md §3.5.4，10-customer-fault-scenarios.md §4.1.2】
    * 关键字：块设备/文件系统错误
    * 说明：分布式网盘POSIX接口失败同样归此【来源：08-fault-triage-consolidated.md §3.5.4】
* 故障原因：块设备/文件系统IO错误（EIO）【来源：08-fault-triage-consolidated.md §3.5.4，10-customer-fault-scenarios.md §4.1.2】。
* 解决方法：修文件系统/挂载；分布式网盘故障联系存储运维【来源：10-customer-fault-scenarios.md §4.1.2】。

##### 1.6.3 磁盘空间不足（code=13）

* 故障现象：
  * case 1:
    * 日志入口：查询KVCache错误码：grep "DS_KV_CLIENT_PUT\|DS_KV_CLIENT_GET" $LOG/ds_client_access_*.log | awk -F'|' '{print $1}' | sort | uniq -c【来源：10-customer-fault-scenarios.md §4.1.2】
    * 关键字：返回错误码中有13（K_NO_SPACE）
  * case 2:
    * 执行命令行：df -h【来源：08-fault-triage-consolidated.md §3.5.4，10-customer-fault-scenarios.md §4.1.2】
    * 关键字：磁盘使用率接近100%
  * case 3:
    * 日志入口：grep -E 'SPILL_HARD_DISK|SHARED_DISK' $LOG/resource.log | tail -5【来源：08-fault-triage-consolidated.md §3.5.4，10-customer-fault-scenarios.md §4.1.2】
    * 关键字：SPILL_HARD_DISK或SHARED_DISK空间接近TOTAL_LIMIT
* 故障原因：磁盘空间不足（ENOSPC）【来源：08-fault-triage-consolidated.md §3.5.4，10-customer-fault-scenarios.md §4.1.2】。
* 解决方法：清理/扩容（本地盘或分布式网盘挂载点）【来源：08-fault-triage-consolidated.md §3.5.4，10-customer-fault-scenarios.md §4.1.2】。

##### 1.6.4 文件描述符耗尽（code=18）

* 故障现象：
  * case 1:
    * 日志入口：查询KVCache错误码：grep "DS_KV_CLIENT_PUT\|DS_KV_CLIENT_GET" $LOG/ds_client_access_*.log | awk -F'|' '{print $1}' | sort | uniq -c【来源：10-customer-fault-scenarios.md §4.1.2】
    * 关键字：返回错误码中有18（K_FILE_LIMIT_REACHED）
  * case 2:
    * 执行命令行：ls /proc/<pid>/fd | wc -l【来源：08-fault-triage-consolidated.md §3.5.4，10-customer-fault-scenarios.md §4.1.2】
    * 关键字：fd数量接近ulimit -n的值
  * case 3:
    * 执行命令行：ulimit -n【来源：10-customer-fault-scenarios.md §4.1.2】
    * 关键字：fd上限值
* 故障原因：文件描述符耗尽（EMFILE/ENFILE）【来源：08-fault-triage-consolidated.md §3.5.4，10-customer-fault-scenarios.md §4.1.2】。
* 解决方法：ulimit -n 65535（永久改/etc/security/limits.conf）【来源：08-fault-triage-consolidated.md §3.5.4，10-customer-fault-scenarios.md §4.1.2、§4.1步骤3】。

##### 1.6.5 mmap失败（code=5）

* 故障现象：
  * case 1:
    * 日志入口：grep -E 'K_RUNTIME_ERROR|Get mmap entry failed' $LOG/datasystem_worker.INFO.log | tail -50【来源：08-fault-triage-consolidated.md §3.2、§3.5.4，03-fault-mode-library.md §3.1】
    * 关键字：需同时满足K_RUNTIME_ERROR和Get mmap entry failed
  * case 2:
    * 执行命令行：ulimit -l【来源：08-fault-triage-consolidated.md §3.5.4，10-customer-fault-scenarios.md §4.1步骤3】
    * 关键字：mlock限制值
  * case 3:
    * 执行命令行：cat /proc/<pid>/limits【来源：08-fault-triage-consolidated.md §3.5.4】
    * 关键字：max locked memory限制
* 故障原因：mlock限制导致mmap失败（ENOMEM）【来源：08-fault-triage-consolidated.md §3.5.4】。
* 解决方法：ulimit -l unlimited【来源：08-fault-triage-consolidated.md §3.5.4，10-customer-fault-scenarios.md §4.1步骤3】。

##### 1.6.6 code=5按日志串细分

* 故障现象：
  * 日志入口：grep -E 'K_RUNTIME_ERROR|Get mmap entry failed|etcd is|urma' $LOG/datasystem_worker.INFO.log | tail -50【来源：08-fault-triage-consolidated.md §3.2】
  * 关键字：K_RUNTIME_ERROR
  * 说明：code=5需按日志串细分："Get mmap entry failed"→OS（1.6.5）；"etcd is timeout/unavailable"→三方etcd（1.3）；"urma ... payload ..."→URMA（1.5）【来源：08-fault-triage-consolidated.md §3.2】
* 故障原因：向下级匹配。
* 解决方法：向下级匹配。

#### 1.7 Client Init/连接Worker失败

* 故障现象：
  * case 1:
    * 日志入口：grep -E '\[(TCP|UDS|SHM_FD)_' $LOG/ds_client_<pid>.INFO.log | head【来源：10-customer-fault-scenarios.md §4.4步骤2】
    * 关键字：满足以下任一：[TCP_CONNECT_FAILED]、[UDS_CONNECT_FAILED]、[SHM_FD_TRANSFER_FAILED]
  * case 2:
    * 日志入口：grep 'ConnectOptions was not configured' $LOG/ds_client_*.INFO.log【来源：10-customer-fault-scenarios.md §4.4步骤3】
    * 关键字：ConnectOptions was not configured
* 故障原因：向下级匹配。
* 解决方法：向下级匹配。

##### 1.7.1 Worker进程不存在

* 故障现象：
  * 执行命令行：pgrep -af datasystem_worker【来源：10-customer-fault-scenarios.md §4.4步骤1】
  * 关键字：无datasystem_worker进程
* 故障原因：DataSystem/编排问题，Worker未拉起【来源：10-customer-fault-scenarios.md §4.4步骤1】。
* 解决方法：联系华为DS支持或编排侧拉起（systemd/k8s查重启原因：kubectl describe / journalctl -u ...）【来源：10-customer-fault-scenarios.md §4.4步骤1】。

##### 1.7.2 Worker端口未LISTEN

* 故障现象：
  * 执行命令行：ss -tnlp | grep <worker_port>【来源：10-customer-fault-scenarios.md §4.4步骤1】
  * 关键字：Worker进程在但端口未LISTEN
* 故障原因：DataSystem问题【来源：10-customer-fault-scenarios.md §4.4步骤1】。
* 解决方法：上报华为DS支持【来源：10-customer-fault-scenarios.md §4.4步骤1】。

##### 1.7.3 TCP建连失败（对端LISTEN）

* 故障现象：
  * 日志入口：grep '\[TCP_CONNECT_FAILED\]' $LOG/ds_client_<pid>.INFO.log | head【来源：10-customer-fault-scenarios.md §4.4步骤2】
  * 关键字：[TCP_CONNECT_FAILED]+对端LISTEN
* 故障原因：主机/网络，防火墙/路由不通【来源：10-customer-fault-scenarios.md §4.4步骤2】。
* 解决方法：iptables -L -n；nc -zv <worker> <port>；删除iptables DROP规则；检查安全组【来源：10-customer-fault-scenarios.md §4.4步骤2】。

##### 1.7.4 UDS路径/权限问题

* 故障现象：
  * 日志入口：grep '\[UDS_CONNECT_FAILED\]' $LOG/ds_client_<pid>.INFO.log | head【来源：10-customer-fault-scenarios.md §4.4步骤2】
  * 关键字：[UDS_CONNECT_FAILED]
* 故障原因：主机，同机UDS路径/权限/tenant_id不一致【来源：10-customer-fault-scenarios.md §4.4步骤2】。
* 解决方法：ls -la <uds_path>检查路径与权限；改权限/按部署文档挂载【来源：10-customer-fault-scenarios.md §4.4步骤2】。

#### 1.8 机器/节点级故障

* 故障现象：
  * 日志入口：grep -E 'Cannot receive heartbeat from worker|K_CLIENT_WORKER_DISCONNECT' $LOG/datasystem_worker.INFO.log $LOG/ds_client_*.INFO.log | tail -50【来源：10-customer-fault-scenarios.md §4.7】
  * 关键字：大量K_CLIENT_WORKER_DISCONNECT(23)/K_RPC_UNAVAILABLE(1002)/Cannot receive heartbeat from worker聚集在某节点【来源：10-customer-fault-scenarios.md §4.7】
* 故障原因：向下级匹配。
* 解决方法：向下级匹配。

##### 1.8.1 节点不可达

* 故障现象：
  * 执行命令行：ping -c 3 <node_ip>【来源：10-customer-fault-scenarios.md §4.7步骤1】
  * 关键字：ping不通
* 故障原因：主机/基础设施，联系机房/云平台【来源：10-customer-fault-scenarios.md §4.7步骤1】。
* 解决方法：联系机房/云平台【来源：10-customer-fault-scenarios.md §4.7步骤1】。

##### 1.8.2 节点NotReady（k8s）

* 故障现象：
  * 执行命令行：kubectl describe node <n>【来源：10-customer-fault-scenarios.md §4.7步骤1】
  * 关键字：taints/conditions异常
* 故障原因：编排/主机问题【来源：10-customer-fault-scenarios.md §4.7步骤1】。
* 解决方法：编排/主机运维排查【来源：10-customer-fault-scenarios.md §4.7步骤1】。

##### 1.8.3 Worker进程被OOM Killer杀掉

* 故障现象：
  * case 1:
    * 执行命令行：ssh <node> 'pgrep -af datasystem_worker'【来源：10-customer-fault-scenarios.md §4.7步骤2】
    * 关键字：进程不存在
  * case 2:
    * 执行命令行：ssh <node> 'dmesg | tail -100'【来源：10-customer-fault-scenarios.md §4.7步骤2】
    * 关键字：OOM killer杀掉datasystem_worker
* 故障原因：主机OOM【来源：10-customer-fault-scenarios.md §4.7步骤2】。
* 解决方法：扩内存/调cgroup；补内存后编排拉起【来源：10-customer-fault-scenarios.md §4.5步骤3、§4.7步骤2】。

##### 1.8.4 Worker进程crash（非OOM）

* 故障现象：
  * case 1:
    * 执行命令行：ssh <node> 'pgrep -af datasystem_worker'【来源：10-customer-fault-scenarios.md §4.7步骤2】
    * 关键字：进程不存在
  * case 2:
    * 执行命令行：ssh <node> 'journalctl -u <worker-service> -n 200'【来源：10-customer-fault-scenarios.md §4.7步骤2】
    * 关键字：非零退出码但无OOM
* 故障原因：DataSystem进程crash【来源：10-customer-fault-scenarios.md §4.7步骤2】。
* 解决方法：上报华为+附journalctl/core dump【来源：10-customer-fault-scenarios.md §4.7步骤2】。

##### 1.8.5 Worker进程在但端口不LISTEN

* 故障现象：
  * 执行命令行：ssh <node> 'pgrep -af datasystem_worker' && ssh <node> 'ss -tnlp | grep <worker_port>'【来源：10-customer-fault-scenarios.md §4.7步骤2】
  * 关键字：进程在但端口未LISTEN
* 故障原因：DataSystem问题【来源：10-customer-fault-scenarios.md §4.7步骤2】。
* 解决方法：上报华为DS支持【来源：10-customer-fault-scenarios.md §4.7步骤2】。

##### 1.8.6 Worker进程在、端口LISTEN但心跳断

* 故障现象：
  * 执行命令行：ssh <node> 'pgrep -af datasystem_worker' && ssh <node> 'ss -tnlp | grep <worker_port>'【来源：10-customer-fault-scenarios.md §4.7步骤2】
  * 关键字：进程在、端口LISTEN但业务心跳断
* 故障原因：主机/网络（中间网络路径）【来源：10-customer-fault-scenarios.md §4.7步骤2】。
* 解决方法：查iptables/路由/MTU【来源：10-customer-fault-scenarios.md §4.7步骤2】。
