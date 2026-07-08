# KVCache定位定界故障模式树 - 通断场景

> **生成依据**：本文档基于 `docs/observable/08-fault-triage-consolidated.md`（简称"08手册"）和 `docs/observable/10-customer-fault-scenarios.md`（简称"10案例"）生成。
> **故障编码规则**：`kvcache_conn_fault_XXX` 表示通断场景故障，子级编码形式为 `kvcache_conn_fault_XXX_YYY`。
> **日志模板**：运行日志格式为 `Time | level | filename | pod_name | pid:tid | trace_id | cluster_name | message`；接口日志格式为 `Time | level | filename | pod_name | pid:tid | trace_id | cluster_name | status_code | action | cost | data size | request param | response param`。详见 `.opencode/skills/kvcache/references/log_template.md:L31-37`。

---

## 日志模板说明

### 运行日志 (INFO log)
文件路径：`$log_dir/ds_client_<pid>.INFO.log`（Client）、`$log_dir/datasystem_worker.INFO.log`（Worker）

格式：`Time | level | filename | pod_name | pid:tid | trace_id | cluster_name | message`

日志示例（来自 `ds_client_1234.INFO.log`）：
```
2026-05-13T00:00:00.018819 | I | worker_oc_service_get_impl.cpp:130 | 6.62.223.31 | 112:403 | d6eef87a-2743-4fff-90e9-efa961b10a8b | model_kvcache_predictor |  [Get] Receive, clientId: 15d6263b-515c-469e-ab96-b99dc40db78f, serverApiReadCost: 0.010ms, inflightRemoteGet: 0
```
来源：`.opencode/skills/kvcache/references/log-example/ds_client_1234.INFO.log:L1`

### 接口日志 (access log)
文件路径：`$log_dir/ds_client_access_<pid>.log`

格式：`Time | level | filename | pod_name | pid:tid | trace_id | cluster_name | status_code | action | cost | data size | request param | response param`
以`|`为分隔符，各字段位置：第1列=Time，第2列=level，第3列=filename，第4列=pod_name，第5列=pid:tid，第6列=trace_id，第7列=cluster_name，**第8列=status_code(code)**，第9列=action(handleName)，第10列=cost(microseconds)，第11列=data size(dataSize)，第12列=request param(reqMsg)，**第13列=response param(respMsg)**。
08手册简化映射：`code(=第8列) | handleName(=第9列) | microseconds(=第10列) | dataSize(=第11列) | reqMsg(=第12列) | respMsg(=第13列)`（来源：08手册:L14-17）

日志示例（来自 `ds_client_access_1234.log`）：
```
2026-05-13T15:27:26.429773 | I | access_recorder.cpp:219 | yxh-worker1-kvclient-1 | 10411:10411 | 3b0dd657-acb9-4ad6-bb62-888ec9776f3b | | 0 | DS_KV_CLIENT_GET | 2410 | 8388608 | {Object_key:[T_yxh_master_kvclient_1_0],time_out:2000} |
```
来源：`.opencode/skills/kvcache/references/log-example/ds_client_access_1234.log:L1`

### 资源日志 (resource.log)
文件路径：`$log_dir/resource.log`

格式：`Time | level | filename | pod_name | pid:tid | trace_id | cluster_name | shm info | spill disk info | client nums | object nums | ... | ETCD_QUEUE | ETCD_REQUEST_SUCCESS_RATE | ... | 线程池信息`
来源：`.opencode/skills/kvcache/references/log_template.md:L38`

**Metrics Summary 格式**（在 INFO log 中每 10s 输出）：
```
Metrics Summary, version=v0, cycle=<N>, interval=<intervalMs>ms

Total:
  <metric>=<value>

Compare with <intervalMs>ms before:
  <metric>=+<delta>
  <metric>,count=+<N>,avg=<us>,max=<us>
```
来源：08手册:L41-50

---

## 故障模式树

### 1 KVCache中断异常

* **故障现象**：
  * 故障现象可能性1：通过接口日志识别（来源：08手册:L14-17）
    * 日志入口：查询access log错误码分布（来源：08手册:L20）
      ```
      awk -F'|' '{gsub(/^ +| +$/,"",$8); print $8}' $LOG/ds_client_access_*.log | sort | uniq -c
      ```
    * 关键字：access log中status_code（第8列，即code）非0大量增多，或进程挂、连接断（来源：08手册:L74）
    * **注意**：`K_NOT_FOUND`在access log会被记成`code=0`；业务"查不到"场景需同时看`respMsg`是否含`NOT_FOUND / Can't find object`（来源：08手册:L22）
    * 命令行输出示例：
      ```
      1537 0
      42 1002
      18 5
      7 23
      3 1009
      ```
      → 匹配逻辑：若输出中非0错误码（1002/5/23/1009等）数量明显增多，则判断为中断异常。
  * 故障现象可能性2：通过两类故障分流判断（来源：08手册:L72-75）
    * 日志入口：grep access log
    * 关键字：接口大量失败、`code`非0明显增多、进程挂、连接断 → 走失败定界（§3）
* **故障原因**：向下级匹配。
* **解决办法**：向下级匹配。
* **故障编码**：kvcache_conn_fault_001
* **故障下级编码**：kvcache_conn_fault_002, kvcache_conn_fault_006, kvcache_conn_fault_007, kvcache_conn_fault_008, kvcache_conn_fault_009, kvcache_conn_fault_010, kvcache_conn_fault_011, kvcache_conn_fault_012, kvcache_conn_fault_020, kvcache_conn_fault_028

---

### 1.1 用户侧错误（code=0/respMsg异常 + code=2/3/8）

* **故障现象**：
  * 故障现象可能性1：通过access log识别（来源：08手册:L127-130, 08手册:L187-190）
    * 日志入口：查询access log respMsg（来源：08手册:L22）
      ```
      grep -E 'DS_KV_CLIENT_(PUT|GET)' $LOG/ds_client_access_*.log | awk -F'|' '{gsub(/^ +| +$/,"",$8); gsub(/^ +| +$/,"",$13); print $8, $13}' | sort | uniq -c | head
      ```
    * 关键字：
      - `code=0` + `respMsg`含`NOT_FOUND` / `Can't find object` → 对象不存在（来源：08手册:L22, 08手册:L252）
      - `code=0` + `respMsg`其他异常内容 → 用户参数/业务问题（来源：08手册:L130, 08手册:L246-252）
      - `code=2`（`K_INVALID`）→ 业务参数非法（来源：08手册:L130, 08手册:L189）
      - `code=3`（`K_NOT_FOUND`）→ 对象不存在（来源：08手册:L130, 08手册:L189）
      - `code=8`（`K_NOT_READY`）→ Init顺序/未就绪（来源：08手册:L130, 08手册:L189）
      - 对应枚举值见错误码→边界总表（来源：08手册:L127-138）
      - 代码定义位置：`include/datasystem/utils/status.h`（来源：03-fault-mode-library.md:L7）
    * 命令行输出示例：
      ```
      1537 0
       42 2 The objectKey is empty
       18 3 Can't find object
        7 8 ConnectOptions was not configured
      ```
      → 匹配逻辑：若输出中出现status_code（第8列）为2/3/8，或status_code=0配合response param（第13列）含异常内容，则判断为**用户侧**错误。
* **故障原因**：向下级匹配。
* **解决办法**：向下级匹配。
* **故障编码**：kvcache_conn_fault_002
* **故障下级编码**：kvcache_conn_fault_002_001, kvcache_conn_fault_002_002, kvcache_conn_fault_002_003, kvcache_conn_fault_002_004, kvcache_conn_fault_002_005, kvcache_conn_fault_002_006, kvcache_conn_fault_002_007

---

#### 1.1.1 respMsg参数非法类故障

* **故障现象**：
  * 故障现象可能性1：通过日志关键字识别（来源：08手册:L246-249）
    * 日志入口：
      ```
      grep -E 'DS_KV_CLIENT_(PUT|GET)' $LOG/ds_client_access_*.log | grep -E 'The objectKey is empty|dataSize should be bigger than zero|length not match'
      ```
    * 关键字（匹配任意一个即为此故障，来源：08手册:L247）：
      - `The objectKey is empty` → 参数为空（来源：08手册:L247）
      - `dataSize should be bigger than zero` → 数据大小为0（来源：08手册:L247）
      - `length not match` → 长度不匹配（来源：08手册:L247）
    * 日志示例（access log中第8列为2、第13列为错误描述的片段）：
      ```
      ... | 2 | DS_KV_CLIENT_PUT | ... | ... | ... | ... | ... | The objectKey is empty
      ```
    * 命令行输出示例（来源：08手册:L558）：
      ```
      ... | 2 | DS_KV_CLIENT_PUT | ... | ... | ... | ... | ... | The objectKey is empty
      ```
      → 匹配逻辑：提取`code=2`且`respMsg`含上述关键字之一，确认参数非法。
* **故障原因**：业务参数非法，属于用户侧问题。（来源：08手册:L247"参数非法" → "业务校验"）
* **解决办法**：业务方校验调用参数。（来源：08手册:L247"业务校验"）
* **故障编码**：kvcache_conn_fault_002_001

---

#### 1.1.2 respMsg未配置Init故障

* **故障现象**：
  * 故障现象可能性1：通过日志关键字识别（来源：08手册:L248）
    * 日志入口：
      ```
      grep 'ConnectOptions was not configured' $LOG/ds_client_access_*.log $LOG/ds_client_*.INFO.log
      ```
    * 关键字：`ConnectOptions was not configured`（来源：08手册:L248）
    * 日志示例（access log中第13列response param片段）：
      ```
      ... | ... | ... | ... | ... | ... | ... | ... | ... | ... | ... | ... | ConnectOptions was not configured
      ```
* **故障原因**：未配置Init就发起调用，属于用户侧问题。（来源：08手册:L248"未配置 Init" → "检查 Init"）
* **解决办法**：检查业务侧Init调用是否正确配置ConnectOptions。（来源：08手册:L248"检查 Init"）
* **故障编码**：kvcache_conn_fault_002_002

---

#### 1.1.3 respMsg重复Publish故障

* **故障现象**：
  * 故障现象可能性1：通过日志关键字识别（来源：08手册:L249）
    * 日志入口：
      ```
      grep 'Client object is already sealed' $LOG/ds_client_access_*.log $LOG/ds_client_*.INFO.log
      ```
    * 关键字：`Client object is already sealed`（来源：08手册:L249）
* **故障原因**：buffer重复Publish，属于用户业务逻辑问题。（来源：08手册:L249"buffer 重复 Publish" → "业务逻辑"）
* **解决办法**：检查业务逻辑，确认是否对同一对象重复调用Publish。（来源：08手册:L249"业务逻辑"）
* **故障编码**：kvcache_conn_fault_002_003

---

#### 1.1.4 respMsg批次超限故障

* **故障现象**：
  * 故障现象可能性1：通过日志关键字识别（来源：08手册:L250）
    * 日志入口：
      ```
      grep 'OBJECT_KEYS_MAX_SIZE_LIMIT' $LOG/ds_client_access_*.log $LOG/ds_client_*.INFO.log
      ```
    * 关键字：`OBJECT_KEYS_MAX_SIZE_LIMIT`（来源：08手册:L250）
* **故障原因**：批处理大小超过最大限制，属于用户侧问题。（来源：08手册:L250"批次超限" → "拆 batch"）
* **解决办法**：拆分批次，减小单次请求的对象数量。（来源：08手册:L250"拆 batch"）
* **故障编码**：kvcache_conn_fault_002_004

---

#### 1.1.5 respMsg对象不存在故障

* **故障现象**：
  * 故障现象可能性1：通过日志关键字识别（来源：08手册:L251）
    * 日志入口：查询access log respMsg（来源：08手册:L55-556）
      ```
      grep -E 'Can.?t find object|K_NOT_FOUND' $LOG/ds_client_*.INFO.log
      ```
    * 关键字（来源：08手册:L251）：
      - `Can't find object`
      - `K_NOT_FOUND`
    * **陷阱**：`K_NOT_FOUND`在access log会被记成`code=0`（来源：08手册:L22, 10案例:L77）
    * 日志示例（INFO log片段）：
      ```
      2026-05-13T15:27:26.429773 | I | kv_client.cpp:67 | ... | K_NOT_FOUND | Can't find object, objectKey: xxx
      ```
    * 命令行输出示例：
      ```
      K_NOT_FOUND  Can't find object, objectKey: xxx
      ```
      → 匹配逻辑：在`ds_client_*.INFO.log`中匹配到`K_NOT_FOUND`或`Can't find object`即为此故障。access log中`code=0`配合`respMsg`含`NOT_FOUND`同样确认为此故障。
* **故障原因**：对象不存在，属于用户侧问题。可能原因：业务未Put直接Get、对象已过期（TTL）、key拼写错误。（来源：08手册:L251"对象不存在" → "业务自查 key"）
* **解决办法**：业务方自查Put/Get顺序、key正确性、TTL设置。（来源：08手册:L251"业务自查 key"）
* **故障编码**：kvcache_conn_fault_002_005

---

#### 1.1.6 错误码2 K_INVALID

* **故障现象**：
  * 故障现象可能性1：通过access log识别（来源：08手册:L130, 08手册:L189）
    * 日志入口：
      ```
      awk -F'|' '{gsub(/^ +| +$/,"",$8); print $8}' $LOG/ds_client_access_*.log | sort | uniq -c | grep -w 2
      ```
    * 关键字：access log中status_code（第8列）为`2`，即`K_INVALID`（来源：08手册:L130）
  * 故障现象可能性2：通过access log按code过滤（来源：08手册:L558）
    * 日志入口：
      ```
      awk -F'|' '$8 ~ / 2 /' $LOG/ds_client_access_*.log
      ```
    * 关键字：status_code（第8列）为2，对应`K_INVALID`（来源：08手册:L558）
    * 命令行输出示例：
      ```
      2 DS_KV_CLIENT_PUT 350 1024 {Object_key:[xxx]} The objectKey is empty
      ```
      → 匹配逻辑：access log中status_code（第8列）为`2`，确认`K_INVALID`错误。
* **故障原因**：`K_INVALID`表示业务参数非法，属于用户侧问题。（来源：08手册:L130"K_INVALID(2)"→"用户"→"业务参数"）
* **解决办法**：业务方校验调用参数。（来源：08手册:L130, 08手册:L247）
* **故障编码**：kvcache_conn_fault_002_006

---

#### 1.1.7 错误码3 K_NOT_FOUND

* **故障现象**：
  * 故障现象可能性1：通过access log识别（来源：08手册:L130, 08手册:L189）
    * 日志入口：
      ```
      awk -F'|' '{gsub(/^ +| +$/,"",$8); print $8}' $LOG/ds_client_access_*.log | sort | uniq -c | grep -w 3
      ```
    * 关键字：access log中status_code（第8列）为`3`，即`K_NOT_FOUND`（来源：08手册:L130）
* **故障原因**：`K_NOT_FOUND(3)`表示对象不存在，属于用户侧问题。（来源：08手册:L130"K_NOT_FOUND(3)"→"用户"→"业务参数/Init顺序"）
* **解决办法**：业务方自查key正确性和Put/Get顺序。（来源：08手册:L251）
* **故障编码**：kvcache_conn_fault_002_007
* **备注**：与kvcache_conn_fault_002_005（respMsg对象不存在）属于相同故障，分别对应access log `code=3`和`code=0+respMsg`两种不同表现。来源：08手册:L141"0 ≠ 一切正常：Get 的 NOT_FOUND 被记成 0"

---

#### 1.1.8 错误码8 K_NOT_READY

* **故障现象**：
  * 故障现象可能性1：通过access log识别（来源：08手册:L130, 08手册:L189）
    * 日志入口：
      ```
      awk -F'|' '{gsub(/^ +| +$/,"",$8); print $8}' $LOG/ds_client_access_*.log | sort | uniq -c | grep -w 8
      ```
    * 关键字：access log中status_code（第8列）`code=8`（来源：08手册:L130）
* **故障原因**：`K_NOT_READY(8)`表示Client未就绪，通常Init未完成或顺序错误，属于用户侧问题。（来源：08手册:L130"K_NOT_READY(8)"→"用户"→"Init顺序"）
* **解决办法**：检查业务侧Init调用和ConnectOptions配置顺序，确保在Put/Get前已完成Init。（来源：08手册:L248）
* **故障编码**：kvcache_conn_fault_002_008

---

### 1.2 错误码5 K_RUNTIME_ERROR

* **故障现象**：
  * 故障现象可能性1：通过access log识别（来源：08手册:L131, 08手册:L191-195）
    * 日志入口：
      ```
      awk -F'|' '{gsub(/^ +| +$/,"",$8); print $8}' $LOG/ds_client_access_*.log | sort | uniq -c | grep -w 5
      ```
    * 关键字：access log中status_code（第8列）`code=5`（来源：08手册:L131）
  * 故障现象可能性2：通过Worker INFO log按日志串细分（来源：08手册:L191-195）
    * 日志入口：
      ```
      grep -E 'K_RUNTIME_ERROR|Get mmap entry failed|etcd is (timeout|unavailable)|urma.*payload' $LOG/datasystem_worker.INFO.log | tail -50
      ```
    * 关键字：需按日志串内容细分（来源：08手册:L191-195）：
      - 若含`Get mmap entry failed` → OS（→kvcache_conn_fault_006_001）
      - 若含`etcd is timeout` / `etcd is unavailable` → 三方etcd（→kvcache_conn_fault_006_002）
      - 若含`urma ... payload ...` → URMA（→kvcache_conn_fault_006_003）
* **故障原因**：向下级匹配。
* **解决办法**：向下级匹配。
* **故障编码**：kvcache_conn_fault_006
* **故障下级编码**：kvcache_conn_fault_006_001, kvcache_conn_fault_006_002, kvcache_conn_fault_006_003

---

#### 1.2.1 code=5 + "Get mmap entry failed" (OS)

* **故障现象**：
  * 故障现象可能性1：通过日志关键字识别（来源：08手册:L192, 08手册:L334）
    * 日志入口：
      ```
      grep -E 'Get mmap entry failed' $LOG/datasystem_worker.INFO.log $LOG/ds_client_*.INFO.log | tail -20
      ```
    * 关键字：`Get mmap entry failed`（来源：08手册:L192, 08手册:L334）
    * 含义：mmap表项未建立或fd无效导致`K_RUNTIME_ERROR(5)`（来源：08手册:L636）
    * 日志示例（INFO log片段）：
      ```
      2026-05-13T15:27:26.429773 | E | object_client_impl.cpp:xxx | ... | Get mmap entry failed for objectKey: xxx, errno=12
      ```
* **故障原因**：`K_RUNTIME_ERROR(5)`配合`Get mmap entry failed`，属于OS层mlock内存限制问题（来源：08手册:L334"ulimit -l限制" → "ENOMEM(mlock限制)"）
* **解决办法**：`ulimit -l unlimited`；或查看`/proc/<pid>/limits`确认mlock上限。（来源：08手册:L334）
* **故障编码**：kvcache_conn_fault_006_001

---

#### 1.2.2 code=5 + "etcd is timeout/unavailable" (三方etcd)

* **故障现象**：
  * 故障现象可能性1：通过日志关键字识别（来源：08手册:L193, 08手册:L217）
    * 日志入口：
      ```
      grep -E 'etcd is (timeout|unavailable)' $LOG/datasystem_worker.INFO.log $LOG/ds_client_*.INFO.log | tail -20
      ```
    * 关键字（来源：08手册:L217）：
      - `etcd is timeout`（Master侧看到，来源：08手册:L632）
      - `etcd is unavailable`（Worker侧看到，来源：08手册:L633）
* **故障原因**：etcd集群或到etcd的网络问题，属于三方etcd责任。（来源：08手册:L217"etcd 集群或到 etcd 的网络"）
* **解决办法**：`systemctl status etcd`；`etcdctl endpoint status`；排查到etcd的网络。（来源：08手册:L273"systemctl status etcd；etcdctl endpoint status；查到 etcd 的网络"）
* **故障编码**：kvcache_conn_fault_006_002

---

#### 1.2.3 code=5 + "urma ... payload ..." (URMA)

* **故障现象**：
  * 故障现象可能性1：通过日志关键字识别（来源：08手册:L194）
    * 日志入口：
      ```
      grep -E 'urma.*payload|Failed to urma' $LOG/datasystem_worker.INFO.log $LOG/ds_client_*.INFO.log | tail -20
      ```
    * 关键字：`urma ... payload`（来源：08手册:L194）
* **故障原因**：URMA数据面payload问题，属于URMA责任。（来源：08手册:L194"urma ... payload ..."→"URMA"）
* **解决办法**：向下级匹配URMA故障（见kvcache_conn_fault_028节）。（来源：08手册:L281-308）
* **故障编码**：kvcache_conn_fault_006_003
* **故障下级编码**：见kvcache_conn_fault_028系列

---

### 1.3 错误码6 K_OUT_OF_MEMORY (OS)

* **故障现象**：
  * 故障现象可能性1：通过access log识别（来源：08手册:L132, 08手册:L196）
    * 日志入口：
      ```
      awk -F'|' '{gsub(/^ +| +$/,"",$8); print $8}' $LOG/ds_client_access_*.log | sort | uniq -c | grep -w 6
      ```
    * 关键字：access log中status_code（第8列）`code=6`（来源：08手册:L132）
  * 故障现象可能性2：通过OS枚举确认（来源：08手册:L330）
    * 日志入口：
      ```
      dmesg | grep -i 'Out of memory'
      ```
    * 关键字：`Out of memory`（来源：08手册:L330）
    * yuanrong-datasystem枚举：`K_OUT_OF_MEMORY`；OS枚举：`ENOMEM`（来源：08手册:L330）
* **故障原因**：内存不足（OOM），属于OS层问题。（来源：08手册:L132"K_OUT_OF_MEMORY(6)"→"OS"→"内存"）
* **解决办法**：`dmesg | grep -i 'Out of memory'`；`free -h`；扩内存或调整cgroup限制。（来源：08手册:L330）
* **故障编码**：kvcache_conn_fault_007

---

### 1.4 错误码7 K_IO_ERROR (OS)

* **故障现象**：
  * 故障现象可能性1：通过access log识别（来源：08手册:L132, 08手册:L196）
    * 日志入口：
      ```
      awk -F'|' '{gsub(/^ +| +$/,"",$8); print $8}' $LOG/ds_client_access_*.log | sort | uniq -c | grep -w 7
      ```
    * 关键字：access log中status_code（第8列）`code=7`（来源：08手册:L132）
  * 故障现象可能性2：通过OS枚举确认（来源：08手册:L331）
    * 日志入口：
      ```
      dmesg | tail -500
      ```
    * 关键字：`K_IO_ERROR`（来源：08手册:L331）；OS枚举：`EIO`（来源：08手册:L331）
* **故障原因**：IO错误，可能原因包括块设备/文件系统故障或分布式网盘POSIX接口失败。（来源：08手册:L331"查块设备/文件系统；分布式网盘POSIX接口失败同样归此"）
* **解决办法**：`dmesg`查看IO错误日志；查块设备/文件系统健康状态；分布式网盘POSIX接口失败同样归此类别。（来源：08手册:L331）
* **故障编码**：kvcache_conn_fault_008

---

### 1.5 错误码13 K_NO_SPACE (OS)

* **故障现象**：
  * 故障现象可能性1：通过access log识别（来源：08手册:L132, 08手册:L196）
    * 日志入口：
      ```
      awk -F'|' '{gsub(/^ +| +$/,"",$8); print $8}' $LOG/ds_client_access_*.log | sort | uniq -c | grep -w 13
      ```
    * 关键字：access log中status_code（第8列）`code=13`（来源：08手册:L132）
  * 故障现象可能性2：通过OS枚举确认（来源：08手册:L332）
    * 日志入口：
      ```
      df -h
      ```
    * 关键字：`K_NO_SPACE`（来源：08手册:L332）；OS枚举：`ENOSPC`（来源：08手册:L332）
    * 补充：检查resource.log中`SPILL_HARD_DISK`和`SHARED_DISK`使用情况（来源：08手册:L332）
    * 命令行输出示例：
      ```
      Filesystem      Size  Used Avail Use% Mounted on
      /dev/sda1       100G  100G     0 100% /
      ```
      → 匹配逻辑：检查挂载点使用率接近100%或Avail为0，确认磁盘满。
* **故障原因**：磁盘空间不足，属于OS层问题。（来源：08手册:L132"K_NO_SPACE(13)"→"OS"→"磁盘"）
* **解决办法**：`df -h`确认磁盘使用情况；检查resource.log中`SPILL_HARD_DISK`/`SHARED_DISK`字段；清理磁盘或扩容（本地盘或分布式网盘挂载点）。（来源：08手册:L332）
* **故障编码**：kvcache_conn_fault_009

---

### 1.6 错误码18 K_FILE_LIMIT_REACHED (OS)

* **故障现象**：
  * 故障现象可能性1：通过access log识别（来源：08手册:L132, 08手册:L196）
    * 日志入口：
      ```
      awk -F'|' '{gsub(/^ +| +$/,"",$8); print $8}' $LOG/ds_client_access_*.log | sort | uniq -c | grep -w 18
      ```
    * 关键字：access log中status_code（第8列）`code=18`（来源：08手册:L132）
  * 故障现象可能性2：通过OS枚举确认（来源：08手册:L333）
    * 日志入口：需要用户在故障机器上执行
      ```
      ls /proc/<pid>/fd | wc -l
      ```
    * 关键字：`K_FILE_LIMIT_REACHED`（来源：08手册:L333）；OS枚举：`EMFILE / ENFILE`（来源：08手册:L333）
* **故障原因**：文件描述符耗尽，属于OS层问题。（来源：08手册:L132"K_FILE_LIMIT_REACHED(18)"→"OS"→"fd"）
* **解决办法**：`ls /proc/<pid>/fd | wc -l`对比`ulimit -n`；调大`ulimit -n`。（来源：08手册:L333）
* **故障编码**：kvcache_conn_fault_010

---

### 1.7 错误码25 K_MASTER_TIMEOUT (三方etcd)

* **故障现象**：
  * 故障现象可能性1：通过access log识别（来源：08手册:L135, 08手册:L196）
    * 日志入口：
      ```
      awk -F'|' '{gsub(/^ +| +$/,"",$8); print $8}' $LOG/ds_client_access_*.log | sort | uniq -c | grep -w 25
      ```
    * 关键字：access log中status_code（第8列）`code=25`（来源：08手册:L196）
  * 故障现象可能性2：通过Worker日志确认etcd超时信号（来源：08手册:L135, 08手册:L217）
    * 日志入口：
      ```
      grep -E 'etcd is (timeout|unavailable)' $LOG/datasystem_worker.INFO.log | tail -20
      ```
    * 关键字（来源：08手册:L217）：
      - `etcd is timeout`（Master侧，来源：08手册:L632）
      - `etcd is unavailable`（Worker侧，来源：08手册:L633）
  * 故障现象可能性3：通过resource.log交叉验证（来源：08手册:L149, 08手册:L674-675）
    * 日志入口：
      ```
      grep -E 'ETCD_QUEUE|ETCD_REQUEST_SUCCESS_RATE' $LOG/resource.log | tail -5
      ```
    * 关键字：
      - `ETCD_QUEUE`堆积（来源：08手册:L674"堆积→三方etcd瓶颈"）
      - `ETCD_REQUEST_SUCCESS_RATE`下降（来源：08手册:L675"下降→§3.5.2(c)"）
    * 命令行输出示例（resource.log片段）：
      ```
      ... | ETCD_QUEUE:128/256/50% | ETCD_REQUEST_SUCCESS_RATE:85.5% | ...
      ```
      → 匹配逻辑：`ETCD_QUEUE` `CURRENT_SIZE`接近`TOTAL_LIMIT`且`ETCD_REQUEST_SUCCESS_RATE`低于基线（如<95%），确认etcd瓶颈。
* **故障原因**：etcd集群或到etcd的网络问题，属于三方etcd责任。（来源：08手册:L135"K_MASTER_TIMEOUT(25)"→"三方(etcd)"→"兼查Master与网络"）
* **解决办法**：`systemctl status etcd`；`etcdctl endpoint status`；排查到etcd的网络。（来源：08手册:L273）
* **故障编码**：kvcache_conn_fault_011

---

### 1.8 yuanrong-datasystem进程内故障（19/23/29/31/32）

* **故障现象**：
  * 故障现象可能性1：通过access log识别（来源：08手册:L133-136, 08手册:L197）
    * 日志入口：
      ```
      awk -F'|' '{gsub(/^ +| +$/,"",$8); print $8}' $LOG/ds_client_access_*.log | sort | uniq -c
      ```
    * 关键字（来源：08手册:L133-136）：
      - `code=19`（`K_TRY_AGAIN`）→ 瞬时繁忙（来源：08手册:L133）
      - `code=23`（`K_CLIENT_WORKER_DISCONNECT`）→ 断连（来源：08手册:L134）
      - `code=29`（`K_SERVER_FD_CLOSED`）→ 生命周期（来源：08手册:L136）
      - `code=31`（`K_SCALE_DOWN`）→ 扩缩容（来源：08手册:L136）
      - `code=32`（`K_SCALING`）→ 扩缩容（来源：08手册:L136）
    * 枚举定义位置：`include/datasystem/utils/status.h`（来源：03-fault-mode-library.md:L7）
* **故障原因**：向下级匹配，需要根据证据进一步定界。（来源：08手册:L256-278）
* **解决办法**：向下级匹配。（来源：08手册:L256-278）
* **故障编码**：kvcache_conn_fault_012
* **故障下级编码**：kvcache_conn_fault_012_001, kvcache_conn_fault_012_002, kvcache_conn_fault_012_003, kvcache_conn_fault_012_004

---

#### 1.8.1 对端处理慢/拒绝（RPC超时/服务不可用）

* **故障现象**：
  * 故障现象可能性1：通过日志关键字识别（来源：08手册:L271）
    * 日志入口：查询Worker INFO log RPC前缀（来源：08手册:L224-225, 08手册:L271）
      ```
      grep -E '\[RPC_RECV_TIMEOUT\]|\[RPC_SERVICE_UNAVAILABLE\]' $LOG/ds_client_*.INFO.log $LOG/datasystem_worker.INFO.log | tail -20
      ```
    * 关键字（来源：08手册:L224-225, 08手册:L271）：
      - `[RPC_RECV_TIMEOUT]`：Client等应答超时（来源：08手册:L608）
      - `[RPC_SERVICE_UNAVAILABLE]`：服务端主动把失败回包（来源：08手册:L609）
      - ZMQ fault=0：排除ZMQ/网络故障（来源：08手册:L224, 08手册:L271）
  * 故障现象可能性2：通过resource.log线程池堆积确认（来源：08手册:L271）
    * 日志入口：
      ```
      grep -E 'WAITING_TASK_NUM' $LOG/resource.log | tail -10
      ```
    * 关键字：`WAITING_TASK_NUM`堆积，所有线程池`*_OC_SERVICE_THREAD_POOL`中`WAITING_TASK_NUM`值高（来源：08手册:L271, 08手册:L667）
    * 日志示例（resource.log线程池片段）：
      ```
      ... | WORKER_OC_SERVICE_THREAD_POOL: idle(2),total(64),wait(128)... | ...
      ```
      → 匹配逻辑：`WAITING_TASK_NUM`显著高于基线（如>0且持续增长），配合`[RPC_RECV_TIMEOUT]`且ZMQ fault=0，确认对端处理慢/线程池打满。
* **故障原因**：Worker对端处理慢或线程池打满导致RPC超时，属于yuanrong-datasystem进程内问题。（来源：08手册:L271"查Worker CPU/锁；扩oc_rpc_thread_num"）
* **解决办法**：查Worker CPU使用率、锁争用情况；扩`oc_rpc_thread_num`线程数。（来源：08手册:L271）
* **故障编码**：kvcache_conn_fault_012_001

---

#### 1.8.2 ZMQ相关问题（重建/断开/握手）

* **故障现象**：
  * 故障现象可能性1：通过日志关键字识别（来源：08手册:L272）
    * 日志入口：
      ```
      grep -E 'zmq_gateway_recreate_total|zmq_event_disconnect_total|zmq_event_handshake_failure_total' $LOG/datasystem_worker.INFO.log | tail -20
      ```
    * 关键字（来源：08手册:L272）：
      - `zmq_gateway_recreate_total` ↑：网关重建次数增多（来源：08手册:L272）
      - `zmq_event_disconnect_total` ↑：ZMQ断连事件增多（来源：08手册:L272）
      - `zmq_event_handshake_failure_total` ↑：TLS/认证握手失败增多（来源：08手册:L272）
  * 故障现象可能性2：通过Metrics Summary确认（来源：08手册:L761, 08手册:L762, 08手册:L764）
    * 日志入口：
      ```
      grep 'Compare with' $LOG/datasystem_worker.INFO.log | tail -3
      ```
    * 关键字：`zmq_gateway_recreate_total`/`zmq_event_disconnect_total`/`zmq_event_handshake_failure_total`的delta为正（来源：08手册:L761-764）
* **故障原因**：分为两种情况（来源：08手册:L272）：
  - 低频出现：SDK自重连，可忽略
  - 高频出现：转OS查网络（zmq_gateway_recreate/disconnect↑且对端Worker仍活→OS网络问题）；握手失败查TLS/认证配置
* **解决办法**：低频可忽略（SDK自重连）；高频转OS查网络；握手失败查TLS/认证配置。（来源：08手册:L272）
* **故障编码**：kvcache_conn_fault_012_002

---

#### 1.8.3 三方etcd（Master/Worker日志中出现etcd超时）

* **故障现象**：
  * 故障现象可能性1：通过日志关键字识别（来源：08手册:L273）
    * 日志入口：
      ```
      grep -E 'etcd is (timeout|unavailable)' $LOG/datasystem_worker.INFO.log | tail -20
      ```
    * 关键字（来源：08手册:L273, 08手册:L632-633）：
      - Master日志：`etcd is timeout`（来源：08手册:L632）
      - Worker日志：`etcd is unavailable`（来源：08手册:L633）
  * 故障现象可能性2：通过resource.log确认（来源：08手册:L273）
    * 日志入口：
      ```
      grep -E 'ETCD_QUEUE|ETCD_REQUEST_SUCCESS_RATE' $LOG/resource.log | tail -5
      ```
    * 关键字：`ETCD_QUEUE`堆积、`ETCD_REQUEST_SUCCESS_RATE`下降（来源：08手册:L273, 08手册:L674-675）
* **故障原因**：**主责写三方etcd**（来源：08手册:L273"主责写三方"）
* **解决办法**：`systemctl status etcd`；`etcdctl endpoint status`；排查到etcd的网络。（来源：08手册:L273）
* **故障编码**：kvcache_conn_fault_012_003

---

#### 1.8.4 心跳/生命周期/扩缩容

* **故障现象**：
  * 故障现象可能性1：通过日志关键字识别（来源：08手册:L274）
    * 日志入口：
      ```
      grep -E 'Cannot receive heartbeat from worker|\[HealthCheck\] Worker is exiting now|meta_is_moving' $LOG/datasystem_worker.INFO.log $LOG/ds_client_*.INFO.log | tail -20
      ```
    * 关键字（来源：08手册:L274, 08手册:L630-635）：
      - `Cannot receive heartbeat from worker.`：心跳超时 → code=23（来源：08手册:L274, 08手册:L631）
      - `[HealthCheck] Worker is exiting now`：Worker主动退出（来源：08手册:L274, 08手册:L630）
      - `meta_is_moving = true`：扩缩容中 → code=31/32（来源：08手册:L274, 08手册:L635）
* **故障原因**：分为三种情况（来源：08手册:L274）：
  - 心跳断：`kill -CONT <pid>`恢复
  - 退出：由编排自动拉起
  - 扩缩容：SDK自重试
* **解决办法**：心跳断 → `kill -CONT <pid>`；退出由编排拉起；扩缩容SDK自重试。（来源：08手册:L274）
* **故障编码**：kvcache_conn_fault_012_004

---

### 1.9 错误码1001 K_RPC_DEADLINE_EXCEEDED / 1002 K_RPC_UNAVAILABLE（桶码）

* **故障现象**：
  * 故障现象可能性1：通过access log识别（来源：08手册:L137, 08手册:L198）
    * 日志入口：
      ```
      awk -F'|' '{gsub(/^ +| +$/,"",$8); print $8}' $LOG/ds_client_access_*.log | sort | uniq -c | grep -E '1001|1002'
      ```
    * 关键字：access log中status_code（第8列）`code=1001`或`code=1002`（来源：08手册:L198）
    * ⚠️ **1002是桶码**：yuanrong-datasystem crash、OS网络断、etcd不可用都会给1002，必须看日志前缀（来源：08手册:L140, 08手册:L202）
    * ⚠️ **1001也是桶码**：需进Step2按日志前缀分流（来源：08手册:L137）
* **故障原因**：向下级匹配，必须按日志前缀分流定界。（来源：08手册:L202-234）
* **解决办法**：向下级匹配。
* **故障编码**：kvcache_conn_fault_020
* **故障下级编码**：kvcache_conn_fault_020_001, kvcache_conn_fault_020_002, kvcache_conn_fault_020_003, kvcache_conn_fault_020_004, kvcache_conn_fault_020_005, kvcache_conn_fault_020_006, kvcache_conn_fault_020_007, kvcache_conn_fault_020_008, kvcache_conn_fault_020_009, kvcache_conn_fault_020_010

---

#### 1.9.1 1001/1002 → OS侧TCP连接失败（对端活）

* **故障现象**：
  * 故障现象可能性1：通过日志关键字识别（来源：08手册:L208, 08手册:L336）
    * 日志入口：
      ```
      grep -E '\[TCP_CONNECT_FAILED\]' $LOG/ds_client_*.INFO.log $LOG/datasystem_worker.INFO.log | tail -20
      ```
    * 关键字：`[TCP_CONNECT_FAILED]` + **对端Worker活**（来源：08手册:L208）
    * 含义：`connect()`对端不可达，addrinfo全部失败（来源：08手册:L602）
    * 定界关键：对端Worker仍在运行且端口监听，但连接失败 → 端口不通/iptables/路由（来源：08手册:L208"端口不通/iptables/路由"）
  * 故障现象可能性2：通过交叉验证确认对端存活（来源：08手册:L238-240）
    * 日志入口：需要用户在故障机器上执行（来源：08手册:L568）
      ```
      ss -tnlp | grep <port>
      ping -c 5 <peer>
      ```
    * 关键字：端口LISTEN且ping可达但连接仍失败
    * 枚举对应的OS errno：`ECONNREFUSED` / `EHOSTUNREACH`（来源：08手册:L336）
* **故障原因**：端口不通/iptables/路由问题，属于OS层。（来源：08手册:L208"端口不通/iptables/路由"）
* **解决办法**：`ss -tnlp`确认端口LISTEN；`iptables -L -n`检查规则；开端口/删规则。（来源：08手册:L336"ss -tnlp；iptables -L -n；开端口/删规则"）
* **故障编码**：kvcache_conn_fault_020_001

---

#### 1.9.2 1001/1002 → OS侧TCP连接重置/网络不可达

* **故障现象**：
  * 故障现象可能性1：通过日志关键字识别（来源：08手册:L209, 08手册:L337）
    * 日志入口：
      ```
      grep -E '\[TCP_CONNECT_RESET\]|\[TCP_NETWORK_UNREACHABLE\]' $LOG/ds_client_*.INFO.log $LOG/datasystem_worker.INFO.log | tail -20
      ```
    * 关键字（来源：08手册:L209, 08手册:L337）：
      - `[TCP_CONNECT_RESET]`：`ECONNRESET`/`EPIPE`（来源：08手册:L603）
      - `[TCP_NETWORK_UNREACHABLE]`：`ZMQ_POLLOUT`失败（来源：08手册:L604）
    * 含义：`[TCP_CONNECT_RESET]`表示网络闪断（来源：08手册:L209"网络闪断"）；`[TCP_NETWORK_UNREACHABLE]`表示心跳探测网络不可达（来源：08手册:L604）
    * OS枚举：`ECONNRESET`/`EPIPE`（来源：08手册:L337）
  * 故障现象可能性2：通过dmesg/netstat确认（来源：08手册:L337）
    * 日志入口：需要用户在故障机器上执行
      ```
      dmesg | tail -200
      netstat -s | grep reset
      ```
    * 关键字：重置/丢包相关统计增加
* **故障原因**：网络闪断或路由不可达，属于OS层。（来源：08手册:L209）
* **解决办法**：`dmesg`查看系统日志；`netstat -s | grep reset`查看重置统计。（来源：08手册:L337）
* **故障编码**：kvcache_conn_fault_020_002

---

#### 1.9.3 1001/1002 → OS侧UDS连接失败/SHM fd传输失败

* **故障现象**：
  * 故障现象可能性1：通过日志关键字识别（来源：08手册:L210, 08手册:L335）
    * 日志入口：
      ```
      grep -E '\[UDS_CONNECT_FAILED\]|\[SHM_FD_TRANSFER_FAILED\]' $LOG/ds_client_*.INFO.log $LOG/datasystem_worker.INFO.log | tail -20
      ```
    * 关键字（来源：08手册:L210, 08手册:L335）：
      - `[UDS_CONNECT_FAILED]`：同机UDS路径失败（来源：08手册:L606）
      - `[SHM_FD_TRANSFER_FAILED]`：SCM_RIGHTS传shm fd失败（来源：08手册:L607）
    * 含义：同机UDS/SCM_RIGHTS传fd失败（路径、权限、fd限制）（来源：08手册:L210"路径/权限/fd限制"）
    * OS枚举：`ENOENT`/`EACCES`/`EPIPE`（来源：08手册:L335）
* **故障原因**：同机UDS路径不存在/权限不足/fd耗尽，SCM_RIGHTS发送失败多为fd耗尽或权限，属于OS层。（来源：08手册:L210, 08手册:L335"SCM_RIGHTS发送失败多为fd耗尽或权限"）
* **解决办法**：检查UDS路径和权限；检查fd上限（`ls /proc/<pid>/fd | wc -l` vs `ulimit -n`）。（来源：08手册:L335）
* **故障编码**：kvcache_conn_fault_020_003

---

#### 1.9.4 1001/1002 → OS侧ZMQ发送/接收失败

* **故障现象**：
  * 故障现象可能性1：通过日志关键字识别（来源：08手册:L211, 08手册:L338）
    * 日志入口：
      ```
      grep -E '\[ZMQ_SEND_FAILURE_TOTAL\]|\[ZMQ_RECEIVE_FAILURE_TOTAL\]' $LOG/ds_client_*.INFO.log $LOG/datasystem_worker.INFO.log | tail -20
      ```
    * 关键字（来源：08手册:L211, 08手册:L338）：
      - `[ZMQ_SEND_FAILURE_TOTAL]`：`zmq_msg_send`硬失败（来源：08手册:L610）
      - `[ZMQ_RECEIVE_FAILURE_TOTAL]`：`zmq_msg_recv`硬失败（来源：08手册:L611）
  * 故障现象可能性2：通过zmq_last_error_number对照errno确定具体原因（来源：08手册:L211, 08手册:L338-349）
    * 日志入口：
      ```
      grep -E 'zmq_last_error_number' $LOG/ds_client_*.INFO.log $LOG/datasystem_worker.INFO.log | tail -10
      ```
    * 关键字：`zmq_last_error_number=<N>`（来源：08手册:L338），按N对照errno表（来源：08手册:L342-349）
    * **errno对照表**（来源：08手册:L342-349）：
      | N | 枚举 | 典型含义 |
      |---|------|---------|
      | 11 | `EAGAIN/EWOULDBLOCK` | 背压（非错） |
      | 101 | `ENETUNREACH` | 路由不可达 |
      | 104 | `ECONNRESET` | 对端reset |
      | 110 | `ETIMEDOUT` | TCP超时 |
      | 111 | `ECONNREFUSED` | 端口无监听 |
      | 113 | `EHOSTUNREACH` | 主机不可达 |
* **故障原因**：ZMQ系统调用层硬失败，按errno对应OS问题。（来源：08手册:L338"对应OS排查"）
* **解决办法**：按`zmq_last_error_number`对应的OS errno进行排查：检查端口/路由/防火墙/资源限制。（来源：08手册:L338）
* **故障编码**：kvcache_conn_fault_020_004

---

#### 1.9.5 1001/1002 → 三方etcd（etcd超时/不可用）

* **故障现象**：
  * 故障现象可能性1：通过日志关键字识别（来源：08手册:L217）
    * 日志入口：
      ```
      grep -E 'etcd is (timeout|unavailable)' $LOG/datasystem_worker.INFO.log | tail -20
      ```
    * 关键字（来源：08手册:L217）：
      - `etcd is timeout`
      - `etcd is unavailable`
    * 常同屏出现1002/25错误码（来源：08手册:L217"常同屏1002/25"）
* **故障原因**：etcd集群或到etcd的网络问题，属于三方etcd责任。（来源：08手册:L217"etcd 集群或到 etcd 的网络"）
* **解决办法**：`systemctl status etcd`；`etcdctl endpoint status`；排查到etcd的网络。（来源：08手册:L273）
* **故障编码**：kvcache_conn_fault_020_005

---

#### 1.9.6 1001/1002 → yuanrong-datasystem进程内：对端Worker不在

* **故障现象**：
  * 故障现象可能性1：通过日志关键字识别（来源：08手册:L223）
    * 日志入口：
      ```
      grep -E '\[TCP_CONNECT_FAILED\]' $LOG/ds_client_*.INFO.log | tail -20
      ```
    * 关键字：`[TCP_CONNECT_FAILED]` + **对端Worker不在**（来源：08手册:L223）
    * 对端Worker不在的验证方法：Worker crash/未拉起，对应节点上`pgrep -af datasystem_worker`无输出（来源：08手册:L223）
  * 故障现象可能性2：通过交叉验证Worker存活状态（来源：08手册:L239）
    * 日志入口：检查对端Worker INFO log同时间窗有无受理日志
    * 关键字：无受理日志 → 再看是否有`[HealthCheck] Worker is exiting now`
    * 补充：`worker_object_count` / access log计数断崖 → Worker重启（来源：08手册:L240）
* **故障原因**：Worker crash/未拉起/机器故障，属于yuanrong-datasystem进程内问题。（来源：08手册:L223"Worker crash/未拉起/机器故障"）
* **解决办法**：检查Worker进程状态（`pgrep -af datasystem_worker`）；若无进程则由编排拉起；若反复crash则查Worker crash dump。（来源：08手册:L223）
* **故障编码**：kvcache_conn_fault_020_006

---

#### 1.9.7 1001/1002 → yuanrong-datasystem进程内：RPC接收超时（对端处理慢）

* **故障现象**：
  * 故障现象可能性1：通过日志关键字识别（来源：08手册:L224）
    * 日志入口：
      ```
      grep -E '\[RPC_RECV_TIMEOUT\]' $LOG/ds_client_*.INFO.log | tail -20
      ```
    * 关键字：`[RPC_RECV_TIMEOUT]` + ZMQ fault=0（来源：08手册:L224）
    * 含义：对端处理慢拖超时，非网络问题（来源：08手册:L224"对端处理慢拖超时，非网络"）
  * 故障现象可能性2：通过resource.log确认线程池堆积（来源：08手册:L224, 08手册:L271）
    * 日志入口：
      ```
      grep -E 'WAITING_TASK_NUM' $LOG/resource.log | tail -10
      ```
    * 关键字：`WAITING_TASK_NUM`堆积
* **故障原因**：对端处理慢导致超时，属于yuanrong-datasystem进程内问题。（来源：08手册:L224）
* **解决办法**：查Worker CPU使用率、锁争用情况；扩`oc_rpc_thread_num`线程数。（来源：08手册:L271）
* **故障编码**：kvcache_conn_fault_020_007
* **备注**：与kvcache_conn_fault_012_001属于相同故障（对端处理慢/拒绝），来自不同入口错误码。

---

#### 1.9.8 1001/1002 → yuanrong-datasystem进程内：RPC服务不可用（对端主动拒绝）

* **故障现象**：
  * 故障现象可能性1：通过日志关键字识别（来源：08手册:L225）
    * 日志入口：
      ```
      grep -E '\[RPC_SERVICE_UNAVAILABLE\]' $LOG/ds_client_*.INFO.log | tail -20
      ```
    * 关键字：`[RPC_SERVICE_UNAVAILABLE]`（来源：08手册:L225）
    * 含义：对端主动拒绝服务（状态/shutting down）（来源：08手册:L225"对端主动拒绝（状态/shutting down）"）
* **故障原因**：对端Worker正在shutting down或状态异常，属于yuanrong-datasystem进程内问题。（来源：08手册:L225）
* **解决办法**：检查对端Worker状态，确认是否在正常退出/扩缩容流程中；若非预期退出，检查Worker日志中的`[HealthCheck]`相关条目。（来源：08手册:L225, 08手册:L274）
* **故障编码**：kvcache_conn_fault_020_008

---

#### 1.9.9 1001/1002 → yuanrong-datasystem进程内：TLS/认证配置（握手失败）

* **故障现象**：
  * 故障现象可能性1：通过日志关键字识别（来源：08手册:L226）
    * 日志入口：
      ```
      grep -E 'zmq_event_handshake_failure_total' $LOG/datasystem_worker.INFO.log | tail -10
      ```
    * 关键字：`zmq_event_handshake_failure_total` ↑（来源：08手册:L226）
  * 故障现象可能性2：通过Metrics Summary确认（来源：08手册:L764）
    * 日志入口：
      ```
      grep 'Compare with' $LOG/datasystem_worker.INFO.log | tail -3
      ```
    * 关键字：`zmq_event_handshake_failure_total` delta为正
* **故障原因**：TLS/认证配置问题，属于yuanrong-datasystem进程内配置问题。（来源：08手册:L226"TLS/认证配置"）
* **解决办法**：检查TLS证书配置、认证参数是否正确。（来源：08手册:L226）
* **故障编码**：kvcache_conn_fault_020_009

---

#### 1.9.10 1001/1002 → 需进一步验证：SOCK/REMOTE握手超时

* **故障现象**：
  * 故障现象可能性1：通过日志关键字识别（来源：08手册:L232）
    * 日志入口：
      ```
      grep -E '\[SOCK_CONN_WAIT_TIMEOUT\]|\[REMOTE_SERVICE_WAIT_TIMEOUT\]' $LOG/ds_client_*.INFO.log $LOG/datasystem_worker.INFO.log | tail -20
      ```
    * 关键字（来源：08手册:L232, 08手册:L605）：
      - `[SOCK_CONN_WAIT_TIMEOUT]`：建连等待超时（来源：08手册:L605）
      - `[REMOTE_SERVICE_WAIT_TIMEOUT]`：建连等待超时（来源：08手册:L605）
  * 故障现象可能性2：需要交叉验证对端Worker存活状态才能定界（来源：08手册:L232）
    * 步骤1：检查对端Worker存活状态
      - 对端Worker活 → OS网络慢（来源：08手册:L232"活=OS网络慢"）
      - 对端Worker不活 → yuanrong-datasystem（来源：08手册:L232"不活=yuanrong-datasystem"）
    * 步骤2（来源：08手册:L238-240）：
      ```
      ping -c 5 <peer>
      ss -tnlp | grep <port>
      ```
      → 对端IP可达、端口LISTEN → 排除OS，问题在yuanrong-datasystem侧
* **故障原因**：握手延迟超时，需根据对端Worker存活状态区分是OS网络慢还是yuanrong-datasystem问题。（来源：08手册:L232）
* **解决办法**：根据对端存活状态定界后按对应边界处置。（来源：08手册:L232）
* **故障编码**：kvcache_conn_fault_020_010

---

### 1.10 URMA故障（1004-1010）

* **故障现象**：
  * 故障现象可能性1：通过access log识别（来源：08手册:L137-138, 08手册:L199）
    * 日志入口：
      ```
      awk -F'|' '{gsub(/^ +| +$/,"",$8); print $8}' $LOG/ds_client_access_*.log | sort | uniq -c | grep -E '1004|1006|1008|1009|1010'
      ```
    * 关键字：access log中status_code（第8列）为1004/1006/1008/1009/1010（来源：08手册:L137-138）
    * 错误码含义（来源：08手册:L137-138）：
      - `code=1004`（`K_URMA_ERROR`）→ UB硬件/驱动
      - `code=1006`（`K_URMA_NEED_CONNECT`）→ 需重连
      - `code=1008`（`K_URMA_TRY_AGAIN`）→ 瞬时重试
      - `code=1009`（`K_URMA_CONNECT_FAILED`）→ 建连失败
      - `code=1010`（`K_URMA_WAIT_TIMEOUT`）→ 等待超时
    * 枚举定义位置：`include/datasystem/utils/status.h`（来源：03-fault-mode-library.md:L7）
  * 故障现象可能性2：通过Worker INFO log URMA前缀识别（来源：08手册:L281-308）
    * 日志入口：
      ```
      grep -E '\[URMA_' $LOG/datasystem_worker.INFO.log $LOG/ds_client_*.INFO.log | tail -30
      ```
    * 关键字：按URMA标签进一步细分（见下级故障）
* **故障原因**：向下级匹配。（来源：08手册:L281-308）
* **解决办法**：向下级匹配。（来源：08手册:L281-308）
* **故障编码**：kvcache_conn_fault_028
* **故障下级编码**：kvcache_conn_fault_028_001, kvcache_conn_fault_028_002, kvcache_conn_fault_028_003, kvcache_conn_fault_028_004, kvcache_conn_fault_028_005, kvcache_conn_fault_028_006, kvcache_conn_fault_028_007, kvcache_conn_fault_028_008

---

#### 1.10.1 URMA_NEED_CONNECT + remoteInstanceId变化（对端Worker重启）

* **故障现象**：
  * 故障现象可能性1：通过日志关键字识别（来源：08手册:L297）
    * 日志入口：
      ```
      grep -E '\[URMA_NEED_CONNECT\]' $LOG/datasystem_worker.INFO.log | tail -20
      ```
    * 关键字：`[URMA_NEED_CONNECT]` + `remoteInstanceId` 变化（来源：08手册:L297, 10案例:L123）
    * 含义：对端Worker重启，连接不存在/实例不匹配（来源：08手册:L618）
    * 进一步确认：同屏查对端Worker日志（`[HealthCheck]`、新pid）（来源：08手册:L297"同屏查对端Worker日志"）
    * 日志示例（INFO log片段）：
      ```
      2026-05-13T15:27:26.429773 | I | urma_manager.cpp:xxx | ... | [URMA_NEED_CONNECT] remoteAddress: xxx, remoteInstanceId: 12345→67890, remoteWorkerId: xxx
      ```
      → 匹配逻辑：若出现`[URMA_NEED_CONNECT]`且`remoteInstanceId`较之前值发生变化，说明对端实例已重启。
* **故障原因**：对端Worker重启导致URMA连接失效，属于预期行为，等待SDK自重连稳定。（来源：08手册:L297"若确认重启→等SDK自重连稳定"）
* **解决办法**：确认对端Worker确实重启后，等待SDK自重连稳定；若重启由编排触发则属正常。（来源：08手册:L297）
* **故障编码**：kvcache_conn_fault_028_001

---

#### 1.10.2 URMA_NEED_CONNECT持续 + instanceId不变（UB链路不稳）

* **故障现象**：
  * 故障现象可能性1：通过日志关键字识别（来源：08手册:L298, 10案例:L124）
    * 日志入口：
      ```
      grep -E '\[URMA_NEED_CONNECT\]' $LOG/datasystem_worker.INFO.log | tail -20
      ```
    * 关键字：`[URMA_NEED_CONNECT]`持续出现且`instanceId`不变（来源：08手册:L298, 10案例:L124）
  * 故障现象可能性2：进一步查同期URMA日志区分（来源：08手册:L298）
    * 若同期伴`[URMA_POLL_ERROR]` / `[URMA_RECREATE_JFS]` → UB硬件/驱动（来源：08手册:L298"两者都有→UB硬件/驱动"）
    * 若仅此出现 → UB端口/交换机抖动（来源：08手册:L298"仅此→UB端口/交换机抖动"）
* **故障原因**：UB链路不稳，需区分是硬件/驱动问题还是端口/交换机抖动。（来源：08手册:L298）
* **解决办法**：检查UB端口状态和交换机；若伴POLL_ERROR/RECREATE_JFS则需联系URMA/UB运维。（来源：08手册:L298）
* **故障编码**：kvcache_conn_fault_028_002

---

#### 1.10.3 URMA_RECREATE_JFS + cqeStatus=9（JFS异常自动重建）

* **故障现象**：
  * 故障现象可能性1：通过日志关键字识别（来源：08手册:L299）
    * 日志入口：
      ```
      grep -E '\[URMA_RECREATE_JFS\]' $LOG/datasystem_worker.INFO.log | tail -20
      ```
    * 关键字：`[URMA_RECREATE_JFS]` + `cqeStatus=9`（ACK TIMEOUT）（来源：08手册:L299）
    * 含义：JFS异常自动重建（来源：08手册:L299"JFS异常自动重建"）
    * 进一步检查：**继续grep `[URMA_RECREATE_JFS_FAILED]`**（来源：08手册:L299"继续grep"）
      - 无`FAILED`标记 → 自愈成功（来源：08手册:L299"无→自愈成功"）
      - 有且连续 → 重建失败（→kvcache_conn_fault_028_004）
  * **业务影响**：JFS重建过程中，业务侧可能短暂感知到`code=19`（`K_TRY_AGAIN`）或P99抖动，属于预期现象（来源：10案例:L127）
* **故障原因**：JFS ACK超时触发的自动重建，通常自愈；若失败则需进一步排查UMDK/驱动。（来源：08手册:L299）
* **解决办法**：若无`URMA_RECREATE_JFS_FAILED`则视为自愈成功无需处理；若有FAILED则见kvcache_conn_fault_028_004。（来源：08手册:L299）
* **故障编码**：kvcache_conn_fault_028_003

---

#### 1.10.4 URMA_RECREATE_JFS_FAILED连续（JFS重建失败）

* **故障现象**：
  * 故障现象可能性1：通过日志关键字识别（来源：08手册:L300, 10案例:L125）
    * 日志入口：
      ```
      grep -E '\[URMA_RECREATE_JFS_FAILED\]' $LOG/datasystem_worker.INFO.log | tail -20
      ```
    * 关键字：`[URMA_RECREATE_JFS_FAILED]`连续出现（来源：08手册:L300, 10案例:L125）
  * 故障现象可能性2：检查是否伴`URMA_RECREATE_JFS_SKIP`（来源：08手册:L300）
    * 日志入口：
      ```
      grep -E '\[URMA_RECREATE_JFS_SKIP\]' $LOG/datasystem_worker.INFO.log | tail -10
      ```
    * 关键字：`[URMA_RECREATE_JFS_SKIP]`并存 → connection已过期则属正常跳过（来源：08手册:L300"connection已过期则属正常跳过"）
    * 若无SKIP且连续FAILED → UMDK/驱动异常（来源：08手册:L300"查UMDK/驱动日志并上报URMA团队"）
* **故障原因**：JFS重建连续失败，可能为UMDK/驱动异常，属于URMA责任。（来源：08手册:L300）
* **解决办法**：查UMDK/驱动日志；上报URMA团队。（来源：08手册:L300）
* **故障编码**：kvcache_conn_fault_028_004

---

#### 1.10.5 fallback to TCP/IP payload（URMA降级TCP）

* **故障现象**：
  * 故障现象可能性1：通过日志关键字识别（来源：08手册:L301, 08手册:L624）
    * 日志入口：
      ```
      grep -E 'fallback to TCP/IP payload' $LOG/datasystem_worker.INFO.log $LOG/ds_client_*.INFO.log | tail -20
      ```
    * 关键字：`fallback to TCP/IP payload`（来源：08手册:L301, 08手册:L624）
    * ⚠️ **非失败**（功能正常但性能降级）（来源：08手册:L306, 08手册:L624）
    * 定界关键：看频率与`client_*_urma_*_bytes` / `client_*_tcp_*_bytes` delta对比（来源：08手册:L301）
      - 间歇少量 → UB抖（来源：08手册:L301"间歇少量→UB抖"）
      - 持续高频 → UB端口down（来源：08手册:L301"持续高频→UB端口down"）
  * 故障现象可能性2：通过Metrics Summary确认降级（来源：08手册:L740）
    * 日志入口：
      ```
      grep 'Compare with' $LOG/datasystem_worker.INFO.log | tail -3 | grep -E 'urma|tcp'
      ```
    * 关键字：`*_urma_*_bytes` delta=0 且 `*_tcp_*_bytes` delta↑（来源：08手册:L740"降级判据"）
* **故障原因**：URMA已降级到TCP（功能正常但性能退化），属于URMA问题引起的时延/性能降级。（来源：08手册:L306"归§4.5时延侧"）
* **解决办法**：检查UB端口状态（`ifconfig ub0 up`）；修UMDK。（来源：08手册:L587"UB降级→ifconfig ub0 up；修UMDK"）
* **故障编码**：kvcache_conn_fault_028_005

---

#### 1.10.6 URMA_POLL_ERROR（驱动/硬件）

* **故障现象**：
  * 故障现象可能性1：通过日志关键字识别（来源：08手册:L302, 10案例:L128）
    * 日志入口：
      ```
      grep -E '\[URMA_POLL_ERROR\]' $LOG/datasystem_worker.INFO.log | tail -20
      ```
    * 关键字：`[URMA_POLL_ERROR]`（来源：08手册:L302, 10案例:L128）
    * 含义：`PollJfcWait`报错（驱动/硬件）（来源：08手册:L302"PollJfcWait报错（驱动/硬件）"）
  * 故障现象可能性2：检查同期是否伴`[URMA_WAIT_TIMEOUT]`（来源：08手册:L302）
    * 日志入口：
      ```
      grep -E '\[URMA_WAIT_TIMEOUT\]' $LOG/datasystem_worker.INFO.log | tail -10
      ```
    * 关键字：`[URMA_WAIT_TIMEOUT]`出现
    * 故障处理：驱动错先grep UMDK日志/`dmesg`（来源：08手册:L302"驱动错先grep UMDK日志/dmesg"）
* **故障原因**：UB驱动/硬件报告Poll错误，属于URMA责任。（来源：08手册:L302）
* **解决办法**：grep UMDK日志；检查`dmesg`中UB相关错误。（来源：08手册:L302）
* **故障编码**：kvcache_conn_fault_028_006

---

#### 1.10.7 URMA_WAIT_TIMEOUT（等待CQE超时, code=1010）

* **故障现象**：
  * 故障现象可能性1：通过日志关键字识别（来源：08手册:L303）
    * 日志入口：
      ```
      grep -E '\[URMA_WAIT_TIMEOUT\]' $LOG/datasystem_worker.INFO.log | tail -20
      ```
    * 关键字：`[URMA_WAIT_TIMEOUT]`（code=1010）（来源：08手册:L303）
    * 含义：等待CQE超时（来源：08手册:L303"等待CQE超时"）
  * 故障现象可能性2：检查`instanceId`是否同期变动（来源：08手册:L303）
    * 若`instanceId`同期变动 → 与URMA_NEED_CONNECT合并（来源：08手册:L303"是→与(a)合并"）
    * 若单独出现 → SDK重试白名单自愈（来源：08手册:L303"单独出现则SDK重试白名单自愈"）
* **故障原因**：CQE等待超时，可能是链路抖动或对端重启触发；单独出现则由SDK白名单重试自愈。（来源：08手册:L303）
* **解决办法**：若伴`instanceId`变化则按kvcache_conn_fault_028_001处理；若单独出现则由SDK白名单重试自愈。（来源：08手册:L303）
* **故障编码**：kvcache_conn_fault_028_007

---

#### 1.10.8 错误码1009 K_URMA_CONNECT_FAILED（URMA建连失败）

* **故障现象**：
  * 故障现象可能性1：通过access log识别（来源：08手册:L304）
    * 日志入口：
      ```
      awk -F'|' '{gsub(/^ +| +$/,"",$8); print $8}' $LOG/ds_client_access_*.log | sort | uniq -c | grep -w 1009
      ```
    * 关键字：access log中status_code（第8列）`code=1009`（`K_URMA_CONNECT_FAILED`）（来源：08手册:L304）
  * 故障现象可能性2：通过URMA连接状态确认（来源：08手册:L304）
    * 日志入口：需要用户在故障机器上执行
      ```
      ifconfig ub0
      ubinfo
      ls /dev/ub*
      ```
    * 关键字：`ifconfig ub0`输出显示端口状态down；或`ls /dev/ub*`无输出（来源：08手册:L304）
* **故障原因**：URMA建连失败，可能UB端口down或设备节点缺失，属于URMA责任。（来源：08手册:L304"URMA建连失败→ifconfig ub0/ubinfo查端口up/down"）
* **解决办法**：`ifconfig ub0`查端口up/down；`ls /dev/ub*`看设备节点是否存在。（来源：08手册:L304）
* **故障编码**：kvcache_conn_fault_028_008

---

## 附录A · 需用户在故障机器上执行的命令汇总

以下故障的解决办法中涉及需要在出现故障的机器上执行命令来确认状态（如`dmesg`、`ls /dev/ub*`等），不放在故障现象中而是放在解决办法中。以下汇总列出：

| 故障编码 | 故障名称 | 需在机器上执行的命令 |
|---------|---------|---------------------|
| kvcache_conn_fault_007 | 错误码6 K_OUT_OF_MEMORY (OS) | `dmesg \| grep -i 'Out of memory'`; `free -h`（来源：08手册:L330）|
| kvcache_conn_fault_008 | 错误码7 K_IO_ERROR (OS) | `dmesg \| tail -500`（来源：08手册:L331）|
| kvcache_conn_fault_009 | 错误码13 K_NO_SPACE (OS) | `df -h`（来源：08手册:L332）|
| kvcache_conn_fault_010 | 错误码18 K_FILE_LIMIT_REACHED (OS) | `ls /proc/<pid>/fd \| wc -l`; `ulimit -n`（来源：08手册:L333）|
| kvcache_conn_fault_006_001 | code=5 + Get mmap entry failed (OS) | `ulimit -l`；`cat /proc/<pid>/limits`（来源：08手册:L334）|
| kvcache_conn_fault_020_001 | 1001/1002 → TCP连接失败 | `ss -tnlp`; `iptables -L -n`（来源：08手册:L336）|
| kvcache_conn_fault_020_002 | 1001/1002 → TCP连接重置/网络不可达 | `dmesg \| tail -200`; `netstat -s \| grep reset`（来源：08手册:L337）|
| kvcache_conn_fault_020_003 | 1001/1002 → UDS/SHM fd失败 | `ls /proc/<pid>/fd \| wc -l` vs `ulimit -n`（来源：08手册:L335）|
| kvcache_conn_fault_020_006 | 1001/1002 → 对端Worker不在 | `pgrep -af datasystem_worker`（来源：08手册:L223）|
| kvcache_conn_fault_020_010 | 1001/1002 → SOCK/REMOTE握手超时 | `ping -c 5 <peer>`; `ss -tnlp \| grep <port>`（来源：08手册:L238-239）|
| kvcache_conn_fault_011 | 错误码25 K_MASTER_TIMEOUT (etcd) | `systemctl status etcd`; `etcdctl endpoint status`（来源：08手册:L273）|
| kvcache_conn_fault_028_008 | code=1009 K_URMA_CONNECT_FAILED | `ifconfig ub0`; `ubinfo`; `ls /dev/ub*`（来源：08手册:L304）|
| kvcache_conn_fault_028_005 | fallback to TCP/IP payload | `ifconfig ub0`; `ubinfo`（来源：08手册:L571）|
| kvcache_conn_fault_028_006 | URMA_POLL_ERROR | `dmesg` grep UMDK日志（来源：08手册:L302）|

---

## 附录B · 故障编码树形结构（摘要）

```
kvcache_conn_fault_001          KVCache中断异常（根节点）
├── kvcache_conn_fault_002      用户侧错误（code=0/respMsg异常 + code=2/3/8）
│   ├── kvcache_conn_fault_002_001  respMsg参数非法类
│   ├── kvcache_conn_fault_002_002  respMsg未配置Init
│   ├── kvcache_conn_fault_002_003  respMsg重复Publish
│   ├── kvcache_conn_fault_002_004  respMsg批次超限
│   ├── kvcache_conn_fault_002_005  respMsg对象不存在
│   ├── kvcache_conn_fault_002_006  错误码2 K_INVALID
│   ├── kvcache_conn_fault_002_007  错误码3 K_NOT_FOUND
│   └── kvcache_conn_fault_002_008  错误码8 K_NOT_READY
├── kvcache_conn_fault_006      错误码5 K_RUNTIME_ERROR
│   ├── kvcache_conn_fault_006_001  Get mmap entry failed (OS)
│   ├── kvcache_conn_fault_006_002  etcd is timeout/unavailable (etcd)
│   └── kvcache_conn_fault_006_003  urma payload (URMA)
├── kvcache_conn_fault_007      错误码6 K_OUT_OF_MEMORY (OS)
├── kvcache_conn_fault_008      错误码7 K_IO_ERROR (OS)
├── kvcache_conn_fault_009      错误码13 K_NO_SPACE (OS)
├── kvcache_conn_fault_010      错误码18 K_FILE_LIMIT_REACHED (OS)
├── kvcache_conn_fault_011      错误码25 K_MASTER_TIMEOUT (etcd)
├── kvcache_conn_fault_012      yuanrong-datasystem进程内 (19/23/29/31/32)
│   ├── kvcache_conn_fault_012_001  对端处理慢/拒绝
│   ├── kvcache_conn_fault_012_002  ZMQ相关问题
│   ├── kvcache_conn_fault_012_003  三方etcd
│   └── kvcache_conn_fault_012_004  心跳/生命周期/扩缩容
├── kvcache_conn_fault_020      错误码1001/1002（桶码）
│   ├── kvcache_conn_fault_020_001  TCP连接失败 (OS)
│   ├── kvcache_conn_fault_020_002  TCP连接重置/网络不可达 (OS)
│   ├── kvcache_conn_fault_020_003  UDS/SHM fd传输失败 (OS)
│   ├── kvcache_conn_fault_020_004  ZMQ发送/接收失败 (OS)
│   ├── kvcache_conn_fault_020_005  etcd超时/不可用 (etcd)
│   ├── kvcache_conn_fault_020_006  对端Worker不在 (yuanrong-datasystem)
│   ├── kvcache_conn_fault_020_007  RPC接收超时 (yuanrong-datasystem)
│   ├── kvcache_conn_fault_020_008  RPC服务不可用 (yuanrong-datasystem)
│   ├── kvcache_conn_fault_020_009  TLS/认证握手失败 (yuanrong-datasystem)
│   └── kvcache_conn_fault_020_010  SOCK/REMOTE握手超时 (需进一步验证)
└── kvcache_conn_fault_028      URMA故障 (1004-1010)
    ├── kvcache_conn_fault_028_001  URMA_NEED_CONNECT + 对端重启
    ├── kvcache_conn_fault_028_002  URMA_NEED_CONNECT + 链路不稳
    ├── kvcache_conn_fault_028_003  URMA_RECREATE_JFS + cqeStatus=9
    ├── kvcache_conn_fault_028_004  URMA_RECREATE_JFS_FAILED连续
    ├── kvcache_conn_fault_028_005  fallback to TCP/IP payload
    ├── kvcache_conn_fault_028_006  URMA_POLL_ERROR
    ├── kvcache_conn_fault_028_007  URMA_WAIT_TIMEOUT (code=1010)
    └── kvcache_conn_fault_028_008  K_URMA_CONNECT_FAILED (code=1009)
```

---

## 附录C · 源文档行号索引

本文档所有内容均来源于以下源文档，每行内容标注了来源位置：

| 来源文档 | 路径 |
|---------|------|
| 08手册 | `docs/observable/08-fault-triage-consolidated.md`（832行）|
| 10案例 | `docs/observable/10-customer-fault-scenarios.md`（324行）|
| 03故障模式库 | `docs/observable/03-fault-mode-library.md`（236行）|
| 日志模板 | `.opencode/skills/kvcache/references/log_template.md`（127行）|
| INFO日志示例 | `.opencode/skills/kvcache/references/log-example/ds_client_1234.INFO.log`（19行）|
| Access日志示例 | `.opencode/skills/kvcache/references/log-example/ds_client_access_1234.log`（2行）|
| 故障示例模板 | `.opencode/skills/kvcache/references/fault_example.md`（84行）|
| JSON模板 | `.opencode/skills/kvcache/references/failure_mode_tree.json`（9行）|
