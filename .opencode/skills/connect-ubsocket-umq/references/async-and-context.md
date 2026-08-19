# 异步与上下文规则

仅在调用点涉及异步对象、线程、事件 runner、callback、模板/虚函数展开或日志控制变量时使用本参考。

## 异步归属证据

异步路径必须同时证明：

1. **生产**：`Connect`、`Accept`、`ReadV` 或 `WriteV` 创建、提交或登记具体 qbuf、CQE、UMQ handle、fd、队列元素、事件计数、请求上下文或状态。
2. **关联**：异步入口通过同一对象、socket fd、handle、队列元素或用户上下文字段接收它。
3. **消费**：物理 UMQ 调用处理该对象，且其失败结果或状态能到达选定的 UBSocket 日志或 API 根。

记录完整链：

```text
UBSocket 公共 API -> 对象/状态生产点 -> id/handle/fd/context 关联 ->
异步入口 -> 消费函数 -> 物理 UMQ 调用 -> 最近日志或 API 根
```

共享全局对象、同一类、同一 socket 类型、资源方向或时间先后关系都不足以证明归属。TX/RX 名称不能单独证明属于
`WriteV`/`ReadV`；重试、回滚、解绑、刷新、销毁和析构路径必须按实际调用入口归属。

回归路径：`WriteV -> PostSend -> TX qbuf/CQE -> TxCqePoller::RunInThread` 或
`UmqTpTxEpollRunnerOps::ProcessOneEvent -> umq_get_cq_event` 属于 WriteV 异步候选，但仍须核对同一对象及状态消费。

## 包装与多上下文

- 枚举模板函数的全部相关实例化调用点、callback/虚函数注册点、线程启动点和 runner 入口。
- 恢复 `公共 API -> 调用者 -> 包装函数 -> 物理 UMQ 调用点`，不能只凭裸函数名或后缀匹配。
- 同一调用点被多个上下文复用时分别记录实参、API 归属、结果处理和日志条件。
- 同步和异步归属均为空但仍有未解析入口时，结论是“证据不足”，不是“链外调用”。
- 若现有树显示日志可从某根到达而源码归属未包含该根，记录归属冲突并重新检查；现有树不能作为归属证据。

## 日志控制变量

日志受 `silent_poll_err`、`enable_log`、`verbose`、`debug_only` 或类似变量控制时：

1. 搜索变量声明、默认值、全部相关赋值点和调用方；
2. 分别记录每个调用上下文的实际值；
3. 只要目标 API 范围内存在满足日志条件的路径，就保留该日志候选；
4. 控制条件不能替代返回值或状态依赖，不能因此连接同一函数族中的无关日志。

回归路径：`PollUmqTxForFcReturn -> silent_poll_err = true -> PollUmqTxInternal -> umq_poll` 中，
`umq_poll` 的负返回能够触发 `PollUmqTxInternal` 的错误日志，因此必须纳入 WriteV 异步故障分析。

缺少生产、关联、消费或日志可触发性证据时，标记“证据不足”，不得写边。
