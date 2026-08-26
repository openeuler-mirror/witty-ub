---
name: "UMDK URMA 日志收集指南"
description: "介绍如何在 openEuler 等系统上收集、重定向、轮转和保留 URMA 日志，包括 rsyslog 与 logrotate 配置示例。"
keywords:
  - UMDK
  - URMA
  - 日志收集
  - rsyslog
  - logrotate
  - 日志重定向
  - 日志轮转
references:
  - name: "UMDK v26.06.0_CAM 文档：URMA User Guide 6.5.1"
    type: offline
    source: "umdk-v26.06.0_CAM/doc/ch/urma/URMA User Guide.ch.md"
  - name: "UMDK v26.06.0_CAM 源码：urma_log.c"
    type: offline
    source: "umdk-v26.06.0_CAM/src/urma/lib/urma/core/urma_log.c"
  - name: "UMDK v26.06.0_CAM GitCode 仓库"
    type: online
    source: "https://gitcode.com/openeuler/umdk/tags/v26.06.0_CAM"
---

# UMDK URMA 日志收集指南

## 概述

URMA 用户态日志默认通过 `syslog()` 输出到系统日志。生产环境中通常需要将 URMA 日志重定向到独立目录，并配置日志轮转，便于集中采集和长期保留。

## 前提条件

确保系统已安装并运行：

```bash
yum install -y rsyslog logrotate
systemctl enable --now rsyslog
```

## 1. 配置 rsyslog 重定向 URMA 日志

创建 `/etc/rsyslog.d/urma.conf`：

```conf
# 将包含 URMA 标签的日志写入独立文件
:msg, contains, "[URMA]" /var/log/urma/urma.log

# 停止向默认系统日志继续写入（可选）
:msg, contains, "[URMA]" ~
```

或者使用更精确的过滤（rsyslog 属性过滤）：

```conf
:programname, startswith, "URMA" /var/log/urma/urma.log
:programname, startswith, "URMA" ~
```

创建日志目录并设置权限：

```bash
mkdir -p /var/log/urma
chown root:root /var/log/urma
chmod 755 /var/log/urma
```

重启 rsyslog：

```bash
systemctl restart rsyslog
```

## 2. 配置 logrotate 日志轮转

创建 `/etc/logrotate.d/urma`：

```conf
/var/log/urma/*.log {
    daily
    rotate 30
    missingok
    notifempty
    compress
    delaycompress
    sharedscripts
    postrotate
        /bin/kill -HUP $(cat /var/run/syslogd.pid 2>/dev/null) 2>/dev/null || true
    endscript
}
```

参数说明：

| 参数 | 含义 |
|------|------|
| `daily` | 每天轮转一次 |
| `rotate 30` | 保留最近 30 个归档文件 |
| `compress` / `delaycompress` | 压缩归档，延迟一天压缩 |
| `missingok` | 日志文件不存在时不报错 |
| `notifempty` | 空日志不轮转 |

## 3. 日志文件权限配置

在 `/etc/rsyslog.d/urma.conf` 中可以通过 `$FileOwner`、`$FileGroup`、`$FileCreateMode` 设置输出文件权限：

```conf
$FileOwner root
$FileGroup root
$FileCreateMode 0640
$DirCreateMode 0750

:msg, contains, "[URMA]" /var/log/urma/urma.log
```

## 4. 通过环境变量临时提升日志级别

复现问题时，可将日志级别调整为 `debug`：

```bash
export URMA_LOG_LEVEL=debug
systemctl restart your-urma-service
```

注意：`debug` 级别日志量很大，建议仅在临时排障时开启，并确保磁盘空间充足。

## 5. 应用日志接管

如果应用希望将 URMA 日志导入自有日志框架，可注册回调：

```c
void my_log_func(int level, char *message)
{
    // 将 message 写入自有日志系统
}

urma_register_log_func(my_log_func);
```

接管后，URMA 不再默认写入 syslog，需应用自行保证落盘和轮转。

## 6. 日志收集检查清单

- [ ] rsyslog 已安装并运行
- [ ] `/etc/rsyslog.d/urma.conf` 已配置
- [ ] `/var/log/urma/` 目录已创建并设置权限
- [ ] `/etc/logrotate.d/urma` 已配置
- [ ] 日志级别已根据问题类型调整（默认 `info`，排障可开 `debug`）
- [ ] 磁盘空间充足，特别是开启 `debug` 时
- [ ] 日志文件可被分析用户或日志采集 Agent 读取

## 常见问题

**Q1：URMA 日志没有写入独立文件？**

- 检查 rsyslog 配置语法是否正确
- 检查 `/etc/rsyslog.d/urma.conf` 是否被 rsyslog 主配置 include
- 检查日志目录权限

**Q2：日志文件增长过快？**

- 检查是否开启了 `debug` 级别且未配置 logrotate
- 检查是否出现了高频错误日志（可观察 `rate limit` 摘要）

**Q3：如何确认日志级别生效？**

- 在日志中查找 `URMA_LOG_LEVEL` 或检查应用启动后的首条日志
