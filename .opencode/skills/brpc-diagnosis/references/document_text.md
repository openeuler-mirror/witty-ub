## 故障模式
建链超时/RPC定界超时
## 故障现象
1、系统日志文件（/var/log/messages）中或者标准输出，存在reached timeout日志，详细日志如下：
...
W0127 20:08:06.65200 1260348 0 /home/brpc/example/echo c++/client.cpp:98 main] [E1008]Reached timeout=20ms @xx.xx.xx.xx:8000
...
2、brpc日志中，存在timeout关键字。
## 问题原因
brpc设置的通信或者建链时间太小
## 解决方法
根据实际场景设置brpc通信或者建链的时长
---
## 故障模式
初始化内存失败
## 故障现象
系统日志文件（/var/log/messages）中或者标准输出，存在buf alloc failed日志，详细日志如下：
... 
0127 20:16:58.342246|ERROR|UMQ|fetch_from_global[263]|buf with data not enough, rest count: 499 
0127 20:16:58.342249|ERROR|UMQ|umq_qbuf_alloc[357]|fetch from global failed, current size: 0, alloc num: 1 
0127 20:16:58.342253|ERROR|UMQ|umq_ub_create_impl[644]|buf alloc failed 
... 
0127 20:16:58.343910|ERROR|UMQ|umq_create[531]|create transport resource failed 
0127 20:16:58.343917|ERROR|RPC_ADPT|CreateLocalUmq[1024]|Failed to execute umq_create failed 
0127 20:16:58.343920|ERROR|RPC_ADPT|DoConnect[363]|Failed to create umq 
...
## 问题原因
初始化设置的内存小于block size ，或者小于实际需要发送的数据大小
## 解决方法：
根据配置block size（RPC_ADPT_BLOCK_TYPE）和发送数据大小，合理分配内存（RPC_ADPT_POOL_INITIAL_SIZE）
---
...

## 规范：每一条需要具备故障模式、故障现象、问题原因、解决方法四个字段。故障现象可以分为多种，每一种故障现象需要指明读取的是什么日志，在skill中有对应读取方法描述。