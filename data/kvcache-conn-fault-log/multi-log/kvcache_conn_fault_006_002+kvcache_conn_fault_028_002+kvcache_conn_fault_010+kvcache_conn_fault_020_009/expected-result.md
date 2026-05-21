# Expected Result for kvcache_conn_fault_006_002+kvcache_conn_fault_028_002+kvcache_conn_fault_010+kvcache_conn_fault_020_009

## 涉及的故障编码
- kvcache_conn_fault_006_002
- kvcache_conn_fault_028_002
- kvcache_conn_fault_010
- kvcache_conn_fault_020_009

## 预期识别结果
识别出4条故障链：006_002（etcd不可用）、028_002（UB链路不稳）、010（fd耗尽）、020_009（TLS握手失败）

## 故障链结构
- 根节点 kvcache_conn_fault_001 → ... → kvcache_conn_fault_006_002
- 根节点 kvcache_conn_fault_001 → ... → kvcache_conn_fault_028_002
- 根节点 kvcache_conn_fault_001 → ... → kvcache_conn_fault_010
- 根节点 kvcache_conn_fault_001 → ... → kvcache_conn_fault_020_009
