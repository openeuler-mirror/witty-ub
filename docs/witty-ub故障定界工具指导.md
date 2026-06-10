# witty-ub故障定界工具指导

## 简介

witty-ub故障定界工具witty-ub-diag-tool是C++语言编写的命令行工具，基于故障树驱动的诊断引擎，通过解析KVCache和URMA等组件日志，自动识别超节点系统中的连接故障，输出可视化故障分析报告。

## 命令介绍

witty-ub-diag-tool ：超节点系统故障定界工具，基于故障树模型对组件日志进行多级诊断分析，定位故障根因。

* 当前支持对KVCache故障（kvcache_conn）和URMA通信故障（urma）进行故障定界分析，输出可视化故障分析报告到```/var/witty-ub```目录下```failure-mode-view-vis.html```文件中

* 工具通过故障树模型进行诊断：从根节点开始，逐级遍历故障模式，每个故障模式通过匹配日志中的特征模式判断是否命中，最终定位到最终故障模式。日志通过traceId字段进行关联追踪，支持跨模块的故障链分析。

### witty-ub-diag-tool 命令行参数说明如下：
| 参数      | 参数类型   | 参数说明  | 使用说明 | 是否必选 |
|:--------:|:----------:|:---------|:---------|:-------:|
| --ds-log-path | string | 日志文件根目录 | 必须为已存在的目录，工具会递归搜索该目录下匹配的日志文件 | 是 |
| --ds-client-access-log-file | string | 客户端访问日志文件匹配模式 | 支持shell glob模式，如```"client_access*.log"```，用于匹配客户端访问日志文件 | 是 |
| --ds-client-info-log-file | string | 客户端信息日志文件匹配模式 | 支持shell glob模式，如```"client_info*.log"```，用于匹配客户端信息日志文件 | 是 |
| --ds-worker-info-log-file | string | 工作线程信息日志文件匹配模式 | 支持shell glob模式，如```"worker_info*.log"```，用于匹配工作线程信息日志文件 | 是 |
| --ds-worker-access-log-file | string | 工作线程访问日志文件匹配模式 | 支持shell glob模式，如```"worker_access*.log"```，用于匹配工作线程访问日志文件 | 是 |
| --resource-log-file | string | 资源日志文件匹配模式 | 支持shell glob模式，如```"resource*.log"```，用于匹配资源日志文件 | 是 |
| --start-time | string | 筛选发生在该时间后的故障事件 | 格式需要为```yyyy-mm-dd hh:mm:ss``` | 是 |
| --end-time | string | 筛选发生在该时间前的故障事件 | 格式需要为```yyyy-mm-dd hh:mm:ss```，且必须晚于start-time | 是 |
| --random-str | string | 输出目录后缀随机字符串 | 用于多个进程并发运行时隔离输出目录，指定后输出到```/var/witty-ub/log_<random-str>/```目录下 | 否 |

### 使用示例

* 基本用法：指定日志目录和文件匹配模式，对指定时间范围内的日志进行故障定界分析
  ```shell
  witty-ub-diag-tool \
    --ds-log-path /var/log/myapp \
    --ds-client-access-log-file "client_access.log" \
    --ds-client-info-log-file "client_info.log" \
    --ds-worker-info-log-file "worker_info.log" \
    --ds-worker-access-log-file "worker_access.log" \
    --resource-log-file "resource.log" \
    --start-time "2026-05-13 10:00:00" \
    --end-time "2026-05-13 11:00:00"
  ```

* 使用通配符匹配多个日志文件
  ```shell
  witty-ub-diag-tool \
    --ds-log-path /var/log/myapp \
    --ds-client-access-log-file "client_access*.log" \
    --ds-client-info-log-file "client_info*.log" \
    --ds-worker-info-log-file "worker_info*.log" \
    --ds-worker-access-log-file "worker_access*.log" \
    --resource-log-file "resource*.log" \
    --start-time "2026-06-01 00:00:00" \
    --end-time "2026-06-02 00:00:00"
  ```

* 多个进程并发诊断时，使用--random-str隔离输出目录
  ```shell
  witty-ub-diag-tool \
    --ds-log-path /var/log/myapp \
    --ds-client-access-log-file "client_access*.log" \
    --ds-client-info-log-file "client_info*.log" \
    --ds-worker-info-log-file "worker_info*.log" \
    --ds-worker-access-log-file "worker_access*.log" \
    --resource-log-file "resource*.log" \
    --start-time "2026-05-13 10:00:00" \
    --end-time "2026-05-13 11:00:00" \
    --random-str "run001"
  ```

### 输出说明

* 可视化故障分析报告：```/var/witty-ub/failure-mode-view-vis.html```
  * 包含故障树的交互式树形视图
  * 按时间排序的故障链轨迹（trace）列表
  * 每条日志行的详细信息（时间戳、文件名、行号、pod名称、PID/TID、traceId、集群名称、消息）
  * 命中计数和根因分析结果

### 故障树说明

工具从```/var/witty-ub/data/failure_mode_tree.json```加载故障树定义（可通过环境变量```WITTY_DIR```指定自定义路径）。故障树包含以下故障域：

* **kvcache_conn**：KVCache连接故障域，包含40个根故障模式
* **urma**：URMA通信故障域，包含875个根故障模式

诊断时从每个域的根节点开始遍历，通过日志模式匹配逐级定位到具体根因。KVCache故障的叶子节点如涉及URMA故障，会自动关联到URMA故障子树进行深层定界。

### 环境变量

| 环境变量      | 说明  | 默认值 |
|:--------:|:---------|:-------:|
| WITTY_DIR | 指定witty-ub工作目录，影响故障树JSON和输出目录的路径 | ```/var/witty-ub``` |
