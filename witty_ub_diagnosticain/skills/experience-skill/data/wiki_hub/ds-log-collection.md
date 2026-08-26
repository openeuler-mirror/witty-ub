---
name: "yuanrong-datasystem 日志收集配置"
description: "介绍 openYuanrong datasystem 的日志目录、文件名、log_monitor 开关、log_rate_limit 采样机制、动态配置热更新以及常见日志收集问题排查。"
keywords:
  - yuanrong-datasystem
  - datasystem
  - 日志收集
  - log_monitor
  - log_rate_limit
  - gflags
  - 动态配置
  - 热更新
references:
  - name: "yuanrong-datasystem 0.8.1.rc20 日志指南"
    type: offline
    source: "yuanrong-datasystem-0.8.1.rc20/docs/source_zh_cn/appendix/log_guide.md"
  - name: "yuanrong-datasystem 0.8.1.rc20 通用 gflags 定义"
    type: offline
    source: "yuanrong-datasystem-0.8.1.rc20/src/datasystem/common/util/gflag/common_gflag_define.cpp"
  - name: "yuanrong-datasystem 0.8.1.rc20 GitCode 仓库"
    type: online
    source: "https://gitcode.com/openeuler/yuanrong-datasystem/tree/0.8.1.rc20"
---

# yuanrong-datasystem 日志收集配置

## 概述

openYuanrong datasystem 的日志通过 gflags 和环境变量控制目录、文件名、监控开关、采样率和动态热更新。本文档汇总关键配置项和常见收集问题。

## 关键配置参数

### 日志目录与文件名

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `log_dir` | `GOOGLE_LOG_DIR` 环境变量 | 日志输出目录，示例：`/var/log/yr_datasystem` |
| `log_filename` | 程序名 | 运行日志文件名前缀，示例：`datasystem_worker` |
| `monitor_config_file` | `~/datasystem/config/datasystem.config` | 动态配置热更新文件 |

### 日志监控开关

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `log_monitor` | true | 是否启用访问日志、资源日志、request_out 日志、sc_metrics 日志 |
| `log_monitor_interval_ms` | 10000 | 资源日志采集间隔，单位 ms |
| `log_monitor_exporter` | "harddisk" | 导出方式：`harddisk`（落盘）或 `backend`（后端） |
| `log_rate_limit` | 0 | 每秒采样 trace 数，0 表示不限 |

### 日志级别

- 运行日志级别：INFO、WARNING、ERROR、FATAL。
- 更细粒度调试通过 VLOG 与 gflags 控制，如 `--v=1`、 `--vmodule=module=2`。

## 日志文件路径

| 类型 | 文件路径 | 开启条件 |
|------|----------|----------|
| 运行日志 | `{log_dir}/{log_filename}.INFO.log`（及 `.WARNING`、`.ERROR`） | 默认开启 |
| 访问日志 | `{log_dir}/access.log` | `log_monitor=true` |
| 资源日志 | `{log_dir}/resource.log` | `log_monitor=true` 且 `log_monitor_exporter=harddisk` |
| 请求第三方日志 | `{log_dir}/request_out.log` | `log_monitor=true` |
| 流缓存指标日志 | `{log_dir}/sc_metrics.log` | `log_monitor=true` |
| 容器/进程日志 | `{log_dir}/container.log` | 默认开启 |
| Client 运行日志 | `{log_dir}/ds_client_{pid}.INFO.log` | 默认开启 |
| Client 访问日志 | `{log_dir}/ds_client_access_{pid}.log` | 默认开启 |

## 配置方式

### Worker 命令行

```bash
./datasystem_worker \
  --log_dir=/var/log/yr_datasystem \
  --log_filename=datasystem_worker \
  --log_monitor=true \
  --log_monitor_interval_ms=10000 \
  --log_rate_limit=20 \
  --monitor_config_file=/etc/yr_datasystem/datasystem.config
```

### Embedded Worker

```cpp
EmbeddedConfig config;
config.LogDir("/var/log/yr_datasystem")
      .LogFilename("datasystem_worker")
      .LogMonitor(true)
      .LogMonitorIntervalMs(10000)
      .LogRateLimit(20);
```

### Standalone Client

```bash
export DATASYSTEM_LOG_RATE_LIMIT=20
export DATASYSTEM_CLIENT_LOG_NAME=ds_client
export DATASYSTEM_CLIENT_ACCESS_LOG_NAME=ds_client_access
./my_app
```

## 动态配置热更新

通过 `monitor_config_file` 指定的文件可在运行时修改部分参数，无需重启进程。文件格式为 `key=value`：

```text
log_rate_limit=50
```

修改后，Worker 会周期性读取并生效。建议修改后观察日志确认生效。

## 日志采样机制

- 采样粒度为“请求（traceId）”，不是单条日志。
- `log_rate_limit=N` 表示每秒最多采样 N 个新请求。
- 对采样到的请求：完整打印 INFO/WARNING/ERROR/FATAL。
- 对未采样请求：仅保留 ERROR/FATAL，其余丢弃。
- 仅 SDK 请求 trace 参与采样；后台线程日志即使带 traceId 也不参与。
- 采样决策会随 RPC 元数据传播，跨 client/worker 保持一致。

## 常见问题排查

| 问题 | 可能原因 | 排查方法 |
|------|----------|----------|
| access.log 为空 | `log_monitor=false` 或 `log_monitor_exporter` 非 `harddisk` | 检查 gflags 和环境变量 |
| resource.log 为空 | 同上，或目录不可写 | 检查 gflags 和目录权限 |
| 日志量过大 | 未设置 `log_rate_limit` | 设置合理采样率并配置 logrotate |
| 动态配置未生效 | 文件路径错误或格式不对 | 检查 `monitor_config_file` 路径和内容格式 |
| Client 日志名异常 | 环境变量未生效 | 检查 `DATASYSTEM_CLIENT_LOG_NAME` 等环境变量 |
| 日志目录不可写 | 权限不足 | 检查进程用户和目录权限 |

## 最佳实践

- 生产环境建议开启 `log_monitor` 并设置 `log_rate_limit` 避免磁盘 I/O 压力。
- 使用 `logrotate` 对日志进行轮转和压缩。
- 关键问题排查时，可临时提升 `log_rate_limit` 或关闭采样，获取更多上下文。
- 定期收集 `resource.log` 用于容量规划和性能基线分析。
