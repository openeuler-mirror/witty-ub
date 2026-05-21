# Expected Result for kvcache_conn_fault_002_005+kvcache_conn_fault_011+kvcache_conn_fault_028_004

## 涉及的故障编码
- kvcache_conn_fault_002_005
- kvcache_conn_fault_011
- kvcache_conn_fault_028_004

## 预期识别结果
识别出3条故障链：002_005（对象不存在）、011（etcd超时）、028_004（JFS重建失败）

## 故障链结构
- 根节点 kvcache_conn_fault_001 → ... → kvcache_conn_fault_002_005
- 根节点 kvcache_conn_fault_001 → ... → kvcache_conn_fault_011
- 根节点 kvcache_conn_fault_001 → ... → kvcache_conn_fault_028_004
