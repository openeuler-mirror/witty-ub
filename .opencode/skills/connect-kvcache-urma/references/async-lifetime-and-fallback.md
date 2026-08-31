# 异步、生命周期与回退规则

仅在 URMA 调用与可观察点（日志节点或 access 边界）之间涉及线程、callback、future、队列、RPC、WR/CR、JFC/JFCE、
async event、RAII 析构、重试、降级回退或日志控制变量时使用本参考。

## 异步归属与传播

异步边必须同时证明：

1. **生产**：某个上游入口（公共 API、RPC handler、后台提交点）创建、提交或登记具体请求、buffer、future、WR、request id、handle、context 或队列元素；
2. **关联**：后台入口通过同一对象、id、handle、用户上下文字段或明确的映射表接收它；
3. **消费**：物理 `ds_urma_*` 调用处理该对象，或其失败状态写入该对象并由后续完成路径读取；
4. **观察**：失败触发调用函数或沿调用图最近 upstream 的 KVCache 错误日志，或以确定 `K_*` 到达 access 边界。

记录完整链：

```text
上游入口 -> 请求/对象生产 -> id/handle/context 关联 -> 后台入口 ->
ds_urma_* 物理调用或完成状态消费 -> 最近日志节点或 access 边界状态码
```

共享同一个 `UrmaManager`、context、JFC、线程或设备不足以证明归属。对 `PostJettyRw`、`PollJfcWait`、
`UrmaAsyncEventHandler::GetAsyncEvent/Run` 等候选入口，必须追踪实际 WR、CR、request id、event target 和完成回调；函数名只用于定位。
`bad_wr`、完成数量和 `cr[].status` 是独立失败通道，须分别检查。若任一通道先在调用函数构造 `RETURN_STATUS` 或
`CHECK_FAIL_RETURN_STATUS` 的状态故障并记录日志，跨组件边停在该日志节点，后续日志通过 KVCache 内部边连接它。

## 资源生命周期与析构

`UrmaContext`、`UrmaJfc`、`UrmaJfce`、`UrmaJfr`、`UrmaJetty`、本地/远端 segment 等 RAII 对象的销毁可能晚于创建它的
上游入口返回。析构调用归属必须证明：

- 对象由哪个上游入口或请求上下文创建、持有和转移；
- 销毁由正常关闭、请求完成、回滚还是独立后台清理触发；
- 析构失败的返回或日志是否仍能关联到某个可观察点（日志节点或 access 边界），还是只属于 `ShutDown`、全局管理线程等独立生命周期；
- 对象是否已被移动、共享或放入跨请求池，导致无法唯一归属。

仅有“创建和销毁同一资源类型”不能把析构 URMA 调用连接到创建时的观察点。无法证明唯一对象身份时标记证据不足。析构函数忽略返回值且
没有日志或其他可观察状态时按无边处理。

## 重试、回退和部分成功

- 重试向上只传播最终失败。每次失败若独立触发具体 ERROR/FATAL 日志，该日志仍可连接对应 `urma_NNN` 接口节点；未记录且后续成功的尝试不连接。
- URMA 失败后回退 TCP 并成功时，停止 access 入口根上提；若回退前已有 KVCache 错误日志，只保留该日志到对应 `urma_NNN` 接口节点的“仅日志可观测”边。
- 回退也失败时，区分最近捕获 URMA 失败的日志与捕获 TCP/整体失败的日志。除非后者直接检查仍携带原 URMA 状态，否则不得越过
  前者连接 `urma_NNN` 接口节点。
- 批量操作、部分 WR 成功或部分副本成功时，分别追踪失败元素的状态是否影响最终 API 结果；不能用整体成功或失败替代逐项证据。
- 清理 API 由主操作失败触发，不代表主操作日志依赖清理 API 的结果。仅当清理返回或状态本身触发该日志时才连接。

## `void`、事件确认和日志控制

`ds_urma_ack_jfc`、`ds_urma_ack_async_event`、`ds_urma_free_eid_list`、`ds_urma_put_rjetty`、`ds_urma_put_seg_ctx` 等
`void` 调用默认无普通跨组件边。只有源码证明 KVCache 观察与该调用关联的 errno、输出或异步失败状态时才连接。
UMQ skill 中物理位置受限的 `urma_ack_jfc` 特例不是 URMA API 的全局规则，不能用于 KVCache 的 `PollJfcWait` 调用点。

本参考中的 `urma_xxx` 表示源码接口函数名，`urma_NNN` 表示故障节点编号。所有确认边 target 必须是存在于
`urma_failure_mode.json` 和 `failure_mode_tree.json.urma` 的 `urma_NNN`；连接分析不得修改 URMA 节点定义或树。

日志受采样、限流、`enable_log`、silent/debug 开关或回退模式控制时，追踪默认值、相关赋值和当前调用上下文。只有目标上下文中日志
实际可触发且与 URMA 失败有控制或数据依赖时，才能作为源节点。

缺少生产、关联、消费、观察或日志可触发性中的任一必要证据时，结论为“证据不足”，不得写边。
