# 未安装命令清单

以下命令在当前环境中未安装，无法执行验证。

| 命令 | 故障模式 | 完整命令 |
|------|---------|--------|
| ifconfig | kvcache_conn_fault_026 | `ifconfig ub0 2>/dev/null 2>/dev/null` |
| ulimit | kvcache_conn_fault_036 | `ulimit -l 2>/dev/null` |
| kubectl | kvcache_conn_fault_046 | `kubectl describe node <n> 2>/dev/null` |
