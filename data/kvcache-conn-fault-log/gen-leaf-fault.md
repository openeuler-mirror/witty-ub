# 叶子故障日志生成检查报告

生成时间: 2026-05-21
总叶子故障数: 38
正确生成: 38
生成错误: 0

| 故障编码 | 故障名称 | 是否正确生成 | 涉及的日志文件 |
|---------|---------|------------|---------------|
| kvcache_conn_fault_002_001 | respMsg参数非法类故障 | 正确生成 | ds_client_access_1234.log |
| kvcache_conn_fault_002_002 | respMsg未配置Init故障 | 正确生成 | ds_client_access_1234.log |
| kvcache_conn_fault_002_003 | respMsg重复Publish故障 | 正确生成 | ds_client_1234.INFO.log, ds_client_access_1234.log |
| kvcache_conn_fault_002_004 | respMsg批次超限故障 | 正确生成 | ds_client_1234.INFO.log, ds_client_access_1234.log |
| kvcache_conn_fault_002_005 | respMsg对象不存在故障 | 正确生成 | ds_client_1234.INFO.log, ds_client_access_1234.log |
| kvcache_conn_fault_002_006 | 错误码2 K_INVALID | 正确生成 | ds_client_access_1234.log |
| kvcache_conn_fault_002_007 | 错误码3 K_NOT_FOUND | 正确生成 | ds_client_access_1234.log |
| kvcache_conn_fault_002_008 | 错误码8 K_NOT_READY | 正确生成 | ds_client_access_1234.log |
| kvcache_conn_fault_006_001 | code=5 + Get mmap entry failed (OS) | 正确生成 | datasystem_worker.INFO.log, ds_client_access_1234.log |
| kvcache_conn_fault_006_002 | code=5 + etcd is timeout/unavailable (三方etcd) | 正确生成 | datasystem_worker.INFO.log, ds_client_access_1234.log |
| kvcache_conn_fault_006_003 | code=5 + urma ... payload ... (URMA) | 正确生成 | datasystem_worker.INFO.log, ds_client_access_1234.log |
| kvcache_conn_fault_007 | 错误码6 K_OUT_OF_MEMORY (OS) | 正确生成 | ds_client_access_1234.log |
| kvcache_conn_fault_008 | 错误码7 K_IO_ERROR (OS) | 正确生成 | ds_client_access_1234.log |
| kvcache_conn_fault_009 | 错误码13 K_NO_SPACE (OS) | 正确生成 | ds_client_access_1234.log |
| kvcache_conn_fault_010 | 错误码18 K_FILE_LIMIT_REACHED (OS) | 正确生成 | ds_client_access_1234.log |
| kvcache_conn_fault_011 | 错误码25 K_MASTER_TIMEOUT (三方etcd) | 正确生成 | ds_client_access_1234.log |
| kvcache_conn_fault_012_001 | 对端处理慢/拒绝（RPC超时/服务不可用） | 正确生成 | ds_client_1234.INFO.log, ds_client_access_1234.log |
| kvcache_conn_fault_012_002 | ZMQ相关问题（重建/断开/握手） | 正确生成 | datasystem_worker.INFO.log, ds_client_access_1234.log |
| kvcache_conn_fault_012_003 | 三方etcd（Master/Worker日志中出现etcd超时） | 正确生成 | datasystem_worker.INFO.log, ds_client_access_1234.log |
| kvcache_conn_fault_012_004 | 心跳/生命周期/扩缩容 | 正确生成 | datasystem_worker.INFO.log, ds_client_access_1234.log |
| kvcache_conn_fault_020_001 | 1001/1002 → OS侧TCP连接失败（对端活） | 正确生成 | ds_client_1234.INFO.log, ds_client_access_1234.log |
| kvcache_conn_fault_020_002 | 1001/1002 → OS侧TCP连接重置/网络不可达 | 正确生成 | ds_client_1234.INFO.log, ds_client_access_1234.log |
| kvcache_conn_fault_020_003 | 1001/1002 → OS侧UDS连接失败/SHM fd传输失败 | 正确生成 | datasystem_worker.INFO.log, ds_client_access_1234.log |
| kvcache_conn_fault_020_004 | 1001/1002 → OS侧ZMQ发送/接收失败 | 正确生成 | datasystem_worker.INFO.log, ds_client_access_1234.log |
| kvcache_conn_fault_020_005 | 1001/1002 → 三方etcd（etcd超时/不可用） | 正确生成 | datasystem_worker.INFO.log, ds_client_access_1234.log |
| kvcache_conn_fault_020_006 | 1001/1002 → yuanrong-datasystem进程内：对端Worker不在 | 正确生成 | ds_client_1234.INFO.log, ds_client_access_1234.log |
| kvcache_conn_fault_020_007 | 1001/1002 → yuanrong-datasystem进程内：RPC接收超时（对端处理慢） | 正确生成 | ds_client_1234.INFO.log, ds_client_access_1234.log |
| kvcache_conn_fault_020_008 | 1001/1002 → yuanrong-datasystem进程内：RPC服务不可用（对端主动拒绝） | 正确生成 | ds_client_1234.INFO.log, ds_client_access_1234.log |
| kvcache_conn_fault_020_009 | 1001/1002 → yuanrong-datasystem进程内：TLS/认证配置（握手失败） | 正确生成 | datasystem_worker.INFO.log, ds_client_access_1234.log |
| kvcache_conn_fault_020_010 | 1001/1002 → 需进一步验证：SOCK/REMOTE握手超时 | 正确生成 | ds_client_1234.INFO.log, ds_client_access_1234.log |
| kvcache_conn_fault_028_001 | URMA_NEED_CONNECT + remoteInstanceId变化（对端Worker重启） | 正确生成 | datasystem_worker.INFO.log, ds_client_access_1234.log |
| kvcache_conn_fault_028_002 | URMA_NEED_CONNECT持续 + instanceId不变（UB链路不稳） | 正确生成 | datasystem_worker.INFO.log, ds_client_access_1234.log |
| kvcache_conn_fault_028_003 | URMA_RECREATE_JFS + cqeStatus=9（JFS异常自动重建） | 正确生成 | datasystem_worker.INFO.log, ds_client_access_1234.log |
| kvcache_conn_fault_028_004 | URMA_RECREATE_JFS_FAILED连续（JFS重建失败） | 正确生成 | datasystem_worker.INFO.log, ds_client_access_1234.log |
| kvcache_conn_fault_028_005 | fallback to TCP/IP payload（URMA降级TCP） | 正确生成 | datasystem_worker.INFO.log, ds_client_access_1234.log |
| kvcache_conn_fault_028_006 | URMA_POLL_ERROR（驱动/硬件） | 正确生成 | datasystem_worker.INFO.log, ds_client_access_1234.log |
| kvcache_conn_fault_028_007 | URMA_WAIT_TIMEOUT（等待CQE超时, code=1010） | 正确生成 | datasystem_worker.INFO.log, ds_client_access_1234.log |
| kvcache_conn_fault_028_008 | 错误码1009 K_URMA_CONNECT_FAILED（URMA建连失败） | 正确生成 | ds_client_access_1234.log |
