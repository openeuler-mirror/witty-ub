# 输出、错误码与字段契约

生成三个最终 JSON、access 根或错误码信息表时读取本文件。

## 输出文件

- `data/kvcache/kvcache_failure_mode.json`：access 根和 runtime 节点数组。
- `data/failure_mode_tree.json`：只重建 `kvcache` key，其他 key 完全不变。
- `data/kvcache/kvcache_error_code_info.json`：`status.h` 中全部 K_* 的信息表。
- `data/kvcache/kvcache_conn_fault_mode.json` 是手工手册，不修改。

编号分别从 `kvcache_access_001`、`kvcache_runtime_001` 连续递增，互不冲突。

## 节点字段

字段顺序固定：

| 字段 | access 根 | runtime 节点 |
| --- | --- | --- |
| `故障编号` | `kvcache_access_NNN`，如有必要增加位数 | `kvcache_runtime_NNN`，如有必要增加位数 |
| `节点类型` | `access_log_entry` | `runtime_log` |
| `故障名称` | 从错误码原因和日志原文提炼的自然语言，≤20字 | “某操作时某原因”，要明确是什么操作，不能宽泛地填写“运行操作时”；不含源码、文件、函数或日志原文；每个故障节点的故障模式不能相同，不能用数字区分 |
| `故障现象` | 直接取错误码信息表；特殊根按下文 | “依次匹配`关键字1`、`关键字2`” |
| `日志匹配` | 不存在 | 通常不存在；仅源码分析后仍无稳定关键字的例外节点存在，值为 `{"enabled": false, "reason": "具体原因"}` |
| `错误码` | 单码根为 `K_NAME(value)`；`code=0 + respMsg 非空` 根为 `K_OK(0)`；FATAL 根为 `null` | 唯一非零 K_*；多码、动态 Status 和 FATAL 为 `null` |
| `匹配条件` | 仅 `code=0 + respMsg 非空` 根存在，紧随 `错误码` | 不存在 |
| `故障原因` | 直接取错误码信息表 | 一句话说明触发条件、失败来源和影响，建议结合日志内容，以 `故障名称` 为基础扩写 |
| `解决办法` | `向下级匹配` | 默认 `无`；仅采用已有明确操作建议 |
| `函数名` | `向下级匹配` | 物理点裸函数名，不含命名空间、签名、`::` |
| `文件名` | `向下级匹配` | 完整路径最后一级文件名 |
| `故障域` | 按 K_* 语义 | 按物理子系统 |

构造/析构保留 `Class`/`~Class`；lambda 取词法外层最近具名函数。

“无稳定关键字（按文件名、函数名和ERROR/FATAL级别定位）”不是普通降级结果。只有对应 `resolve_log_template` 已完成源码分析、checkpoint 中保留证据且最终节点包含禁用的 `日志匹配` 时才允许使用。诊断工具不得索引或匹配这类节点。

## Access 根

为 runtime 扫描中实际出现的每个非零 K_* 建一个根，按 `error_definitions` 数值升序编号。同一 K_* 只建一个根。随后追加：

1. `code=0 + respMsg 非空`：规定错误码 `K_OK(0)`、故障域 `用户`，此外必须增加结构化字段 `"匹配条件": {"status_code": 0, "resp_msg_nonempty": true}`；定界代码不得通过编号或自然语言识别该根。
2. `进程级 FATAL 故障`：CHECK/LOG(FATAL) 导致 SIGABRT、access recorder 可能不输出正常行；`错误码=null`、函数 `FailureWriter`、文件 `failure_handler.cpp`、故障域 `KVCache`。

K_* 根的 `故障名称` 必须是“业务参数非法”“对象不存在”等自然语言，不得使用 `K_NAME(value) 错误码故障` 的枚举拼接形式。`故障现象`、`故障原因` 必须直接取错误码信息表。

## 错误码信息表

顶层是按数值升序的对象，key 为数值字符串；每个值只含 `故障现象`、`故障原因`，顺序固定：

```json
{
  "2": {
    "故障现象": "请求返回K_INVALID，参数校验失败。",
    "故障原因": "key、数据大小、长度或调用选项等业务参数非法。"
  }
}
```

对 `/tmp/kvcache_status_codes.json` 的每个 K_*：

1. 在 `status.h` 核对枚举和值。
2. 搜索 `src/datasystem`，必要时搜索 `include/datasystem`，汇总构造/返回点的操作类型、失败条件和责任方。按错误码一次性阅读其主要返回点，不按物理日志重复搜索。
3. `故障现象` 必须以 `请求返回K_*，` 开头且只有一句；`故障原因` 只有一句并明确责任方，不含文件、函数或日志原文。
4. 无构造点的预留码仍生成：现象说明当前源码无构造点，原因说明按枚举语义域理解且暂无实际路径。
5. 每个错误码一个条目，不得合并。

K_OK(0) 是特例：当 `Status::IsOk()` 为真但 `respMsg` 非空时仍可能表示业务参数或调用顺序故障。现象须写“请求返回K_OK，但respMsg非空，提示……”，原因覆盖参数非法、未 Init、重复 Publish 或批次超限等用户侧问题，不得跳过。

## Access 根故障域建议

建议值不是硬规则；源码实际语义不同时按事实填写并在分析记录说明。

| K_* | 值 | 建议故障域 |
| --- | ---: | --- |
| K_OK | 0 | 用户 |
| K_DUPLICATED | 1 | 用户 |
| K_INVALID | 2 | 用户 |
| K_NOT_FOUND | 3 | 用户 |
| K_KVSTORE_ERROR | 4 | 三方 etcd |
| K_RUNTIME_ERROR | 5 | KVCache |
| K_OUT_OF_MEMORY | 6 | OS |
| K_IO_ERROR | 7 | OS |
| K_NOT_READY | 8 | 用户 |
| K_NOT_AUTHORIZED | 9 | 用户 |
| K_UNKNOWN_ERROR | 10 | KVCache |
| K_INTERRUPTED | 11 | OS |
| K_OUT_OF_RANGE | 12 | 用户 |
| K_NO_SPACE | 13 | OS |
| K_NOT_LEADER_MASTER | 14 | 三方 etcd |
| K_RECOVERY_ERROR | 15 | KVCache |
| K_RECOVERY_IN_PROGRESS | 16 | KVCache |
| K_FILE_NAME_TOO_LONG | 17 | OS |
| K_FILE_LIMIT_REACHED | 18 | OS |
| K_TRY_AGAIN | 19 | KVCache |
| K_DATA_INCONSISTENCY | 20 | KVCache |
| K_SHUTTING_DOWN | 21 | KVCache |
| K_WORKER_ABNORMAL | 22 | KVCache |
| K_CLIENT_WORKER_DISCONNECT | 23 | KVCache |
| K_WORKER_TIMEOUT | 24 | KVCache |
| K_MASTER_TIMEOUT | 25 | 三方 etcd |
| K_NOT_FOUND_IN_L2CACHE | 26 | KVCache |
| K_REPLICA_NOT_READY | 27 | KVCache |
| K_CLIENT_WORKER_VERSION_MISMATCH | 28 | KVCache |
| K_SERVER_FD_CLOSED | 29 | KVCache |
| K_RPC_DEADLINE_EXCEEDED | 1001 | RPC/网络 |
| K_RPC_UNAVAILABLE | 1002 | RPC/网络 |
| K_URMA_ERROR | 1004 | URMA/硬件 |
| K_RDMA_ERROR | 1005 | URMA/硬件 |
| K_URMA_NEED_CONNECT | 1006 | URMA |
| K_URMA_TRY_AGAIN | 1008 | URMA |
| K_URMA_WAIT_TIMEOUT | 1010 | URMA/硬件 |
| K_OC_REMOTE_GET_NOT_ENOUGH | 2002 | KVCache |
| K_OC_KEY_ALREADY_EXIST | 2004 | 用户 |
| K_SC_STREAM_IN_RESET_STATE | 3004 | KVCache |
| K_SC_WORKER_WAS_LOST | 3005 | KVCache |
| K_SC_STREAM_RESOURCE_ERROR | 3008 | KVCache |
| K_SC_ALREADY_CLOSED | 3009 | KVCache |
| K_FUTURE_TIMEOUT | 5002 | KVCache |

入口根故障域用于按 status_code 找责任大类；runtime 故障域用于精确定位物理责任方，两者不要求一致。
