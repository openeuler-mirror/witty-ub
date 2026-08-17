# 异步传播规则

仅当 URMA 调用或 UMQ 日志之间涉及 callback、线程、队列、WR/CR、JFC/JFCE、notifier、eventfd 或 async event 时使用本参考。

## 证据链

异步边必须同时证明：

1. **生产**：某个 UMQ 公共 API 创建、提交或登记具体对象、请求、WR、id、handle、fd、context 或用户数据。
2. **关联**：后台入口、callback、provider 或后续 API 通过同一对象、id、handle、fd 或 context 字段接收该状态。
3. **消费**：URMA 调用的返回、输出或注入状态被写入该对象，并最终被 UMQ 条件读取且触发具体错误日志。

仅有共享全局 context、同一设备、同一线程、组件相同或时间先后关系，不足以生成边。

分析记录至少写出：

```text
UMQ 公共 API -> 对象/请求生产点 -> id/handle/fd/context 关联 ->
异步入口 -> 状态消费点 -> 最近 UMQ 错误日志
```

## 常见路径

- WR/CR：追踪 `bad_wr`、WR id、CR 数量及 `cr[].status`，确认提交对象与完成对象一致。
- JFC/JFCE：追踪 poll/wait、eventfd 和 notifier 关联，不能仅凭使用同一个 JFC 推断。
- async event：追踪 event type、目标对象和 ack/消费位置。
- callback/线程：从注册或 `pthread_create` 的参数追踪入口及其实际数据源；注册关系只证明候选可执行。
- queue/runner：证明生产者写入的失败状态由对应消费者读取，且中途没有被覆盖、恢复或转换为成功。

若一个物理调用点被多个异步上下文复用，分别记录每个上下文的对象关联、UMQ API 归属和最近日志。
若日志受 `enable_log`、`silent`、`verbose`、采样或限流控制，追踪声明、默认值和全部赋值点，确认当前上下文实际会输出该日志。

缺少生产、关联或消费中的任一类证据时，结论为“证据不足”，不得写边。
