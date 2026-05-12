# 执行失败命令清单

以下命令已安装但执行失败。

| 命令 | 故障模式 | 完整命令 | 错误信息 |
|------|---------|--------|--------|
| ls | kvcache_conn_fault_026 | `ls /dev/ub* 2>/dev/null 2>/dev/null` | exit code 2 |
| ping | kvcache_conn_fault_045 | `ping -c 3 <node_ip> 2>/dev/null` | exit code 2 |
