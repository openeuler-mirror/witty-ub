# Expected Result for kvcache_conn_fault_002_001+kvcache_conn_fault_028_008+kvcache_conn_fault_006_001

## 涉及的故障编码
- kvcache_conn_fault_002_001
- kvcache_conn_fault_028_008
- kvcache_conn_fault_006_001

## 预期识别结果
识别出3条独立故障链：002_001（用户侧参数非法）、028_008（URMA建连失败）、006_001（OS mmap entry失败）

## 故障链结构
- 根节点 kvcache_conn_fault_001 → ... → kvcache_conn_fault_002_001
- 根节点 kvcache_conn_fault_001 → ... → kvcache_conn_fault_028_008
- 根节点 kvcache_conn_fault_001 → ... → kvcache_conn_fault_006_001
