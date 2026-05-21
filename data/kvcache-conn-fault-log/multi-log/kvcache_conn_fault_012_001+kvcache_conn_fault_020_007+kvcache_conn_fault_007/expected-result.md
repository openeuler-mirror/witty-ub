# Expected Result for kvcache_conn_fault_012_001+kvcache_conn_fault_020_007+kvcache_conn_fault_007

## 涉及的故障编码
- kvcache_conn_fault_012_001
- kvcache_conn_fault_020_007
- kvcache_conn_fault_007

## 预期识别结果
识别出3条故障链：012_001（对端处理慢）、020_007（RPC接收超时）、007（OOM错误码6）

## 故障链结构
- 根节点 kvcache_conn_fault_001 → ... → kvcache_conn_fault_012_001
- 根节点 kvcache_conn_fault_001 → ... → kvcache_conn_fault_020_007
- 根节点 kvcache_conn_fault_001 → ... → kvcache_conn_fault_007
