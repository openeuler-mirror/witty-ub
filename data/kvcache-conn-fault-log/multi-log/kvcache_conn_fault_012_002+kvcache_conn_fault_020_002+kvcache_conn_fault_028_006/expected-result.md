# Expected Result for kvcache_conn_fault_012_002+kvcache_conn_fault_020_002+kvcache_conn_fault_028_006

## 涉及的故障编码
- kvcache_conn_fault_012_002
- kvcache_conn_fault_020_002
- kvcache_conn_fault_028_006

## 预期识别结果
识别出3条故障链：012_002（ZMQ断连）、020_002（TCP重置）、028_006（URMA POLL错误）

## 故障链结构
- 根节点 kvcache_conn_fault_001 → ... → kvcache_conn_fault_012_002
- 根节点 kvcache_conn_fault_001 → ... → kvcache_conn_fault_020_002
- 根节点 kvcache_conn_fault_001 → ... → kvcache_conn_fault_028_006
