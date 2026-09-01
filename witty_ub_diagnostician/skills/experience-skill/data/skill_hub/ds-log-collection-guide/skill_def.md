---
name: ds-log-collection-guide
description: >
  介绍 openYuanrong datasystem 的日志收集方式、关键 gflags、log_monitor 开关、
  日志采样（log_rate_limit）、动态配置热更新、以及常见日志收集问题的排查方法。
license: MIT
compatibility: yuanrong-datasystem 0.8.1.rc20
metadata:
  author: yuanrong-datasystem-log-analysis
  version: "1.0"
  keywords: [yuanrong-datasystem, datasystem, 日志收集, log_monitor, gflags, log_rate_limit, 动态配置]
allowed-tools: Bash(grep:*) Bash(awk:*) Bash(sed:*) Bash(cat:*)
---

# yuanrong-datasystem 日志收集配置 Skill

## 概述

openYuanrong datasystem 的日志通过 gflags 控制目录、文件名、监控开关、采样和动态热更新。合理配置 `log_dir`、`log_monitor`、`log_rate_limit` 等参数，是故障排查和性能分析的前提。

## 约束

- Worker 日志由 gflags 控制；Client 日志还受环境变量 `DATASYSTEM_CLIENT_LOG_NAME` 和 `DATASYSTEM_CLIENT_ACCESS_LOG_NAME` 影响。
- `log_monitor` 控制访问日志、资源日志、request_out 日志、sc_metrics 的开启。
- `log_rate_limit` 采样仅针对带 trace_id 的 SDK 请求，后台线程日志不参与采样。
- 动态配置通过 `monitor_config_file` 指定的文件热更新，无需重启进程。

## 流程

1. 确认运行环境（Worker 启动参数 / Embedded Worker / Standalone Client）。
2. 配置 `log_dir` 和 `log_filename`，确保磁盘空间充足。
3. 按需开启 `log_monitor` 和 `log_monitor_exporter`（默认 `harddisk`）。
4. 大流量场景下设置 `log_rate_limit` 减少日志磁盘 I/O。
5. 需要更细粒度调试时，使用 `--v=N` 或 `--vmodule=module=N` 开启 VLOG。
6. 配置 `monitor_config_file` 实现运行时参数热更新。
7. 排查日志缺失时，检查 gflags、环境变量、进程权限和磁盘空间。

## 能力

- 输出 Worker 与 Client 的日志配置方式。
- 输出 6 类日志的开启条件和文件路径。
- 输出 `log_rate_limit` 采样机制与配置示例。
- 输出动态配置热更新方法。
- 输出常见日志收集问题排查步骤。

## 规则

- 生产环境开启 `log_monitor` 前评估磁盘 I/O 和容量。
- 设置 `log_rate_limit` 后，ERROR/FATAL 日志仍会保留，不影响故障排查。
- 动态配置修改后，应观察日志确认生效，而非立即重启。
- 日志目录需要进程写权限，避免启动失败或日志丢失。

## 关键 gflags

### 日志目录与文件名

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `log_dir` | `GOOGLE_LOG_DIR` 环境变量 | 日志输出目录 |
| `log_filename` | 程序名 | 运行日志文件名前缀 |
| `monitor_config_file` | `~/datasystem/config/datasystem.config` | 动态配置热更新文件 |

### 日志监控开关

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `log_monitor` | true | 是否启用访问/资源/request_out/sc_metrics 日志 |
| `log_monitor_interval_ms` | 10000 | 资源日志采集间隔，单位 ms |
| `log_monitor_exporter` | "harddisk" | 导出方式：`harddisk` 或 `backend` |
| `log_rate_limit` | 0 | 每秒采样 trace 数，0 表示不限 |

### 集群与节点健康相关

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `etcd_address` | "" | ETCD 地址 |
| `cluster_name` | "" | 集群名 |
| `node_timeout_s` | 60 | 节点被认为丢失的最大时间 |
| `node_dead_timeout_s` | 300 | master 判定节点死亡的最大时间 |
| `heartbeat_interval_ms` | 1000 | ETCD keepalive 心跳间隔 |
| `client_dead_timeout_s` | 120 | client 死亡超时 |
| `client_reconnect_wait_s` | 10 | client 重连等待时间 |

## 日志文件路径

| 类型 | 文件路径 | 开启条件 |
|------|----------|----------|
| 运行日志 | `{log_dir}/{log_filename}.INFO.log`（及 .WARNING、.ERROR 等） | 默认开启 |
| 访问日志 | `{log_dir}/access.log` | `log_monitor=true` |
| 资源日志 | `{log_dir}/resource.log` | `log_monitor=true` 且 `log_monitor_exporter=harddisk` |
| 请求第三方日志 | `{log_dir}/request_out.log` | `log_monitor=true` |
| 流缓存指标日志 | `{log_dir}/sc_metrics.log` | `log_monitor=true` |
| 容器/进程日志 | `{log_dir}/container.log` | 默认开启 |
| Client 运行日志 | `{log_dir}/ds_client_{pid}.INFO.log` | 默认开启 |
| Client 访问日志 | `{log_dir}/ds_client_access_{pid}.log` | 默认开启 |

## 配置示例

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

### 动态配置热更新

编辑 `monitor_config_file` 指定的文件（如 `~/datasystem/config/datasystem.config`），修改 `log_rate_limit` 等参数后，进程会周期性读取并生效。示例：

```text
log_rate_limit=50
```

## 日志采样机制

- 采样粒度为“请求（traceId）”，不是单条日志。
- `log_rate_limit=N` 表示每秒最多采样 N 个新请求。
- 对采样到的请求：完整打印 INFO/WARNING/ERROR/FATAL。
- 对未采样请求：仅保留 ERROR/FATAL，其余丢弃。
- 仅 SDK 请求 trace 参与采样；后台线程日志即使带 traceId 也不参与。
- 采样决策会随 RPC 元数据传播，跨 client/worker 保持一致。

## 常见问题

1. **access.log 或 resource.log 为空**：检查 `--log_monitor` 是否为 true，以及 `log_monitor_exporter` 是否为 `harddisk`。
2. **日志目录不可写**：进程启动时会失败或回退到默认目录；检查启动日志中的路径信息。
3. **日志量过大**：设置 `log_rate_limit` 并配合 `logrotate` 进行轮转。
4. **动态配置未生效**：确认 `monitor_config_file` 路径正确，且文件内容格式为 `key=value`。
5. **Client 日志名不符合预期**：检查环境变量 `DATASYSTEM_CLIENT_LOG_NAME` 和 `DATASYSTEM_CLIENT_ACCESS_LOG_NAME`。

## 相关参考

- `docs/source_zh_cn/appendix/log_guide.md`
- `src/datasystem/common/util/gflag/common_gflag_define.cpp`
