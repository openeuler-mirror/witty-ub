---
name: ds-object-cache-diagnosis
description: >
  介绍 openYuanrong datasystem Object Cache 的日志分析方法，覆盖 DS_OBJECT_CLIENT Create/Publish/Get/Delete/Seal、
  嵌套引用、生命周期（keep）、一致性、本地/远端命中和对象状态异常。
license: MIT
compatibility: yuanrong-datasystem 0.8.1.rc20
metadata:
  author: yuanrong-datasystem-log-analysis
  version: "1.0"
  keywords: [yuanrong-datasystem, datasystem, Object Cache, DS_OBJECT_CLIENT, Publish, Get, Seal, 嵌套引用, keep]
allowed-tools: Bash(grep:*) Bash(awk:*) Bash(sed:*) Bash(cat:*)
---

# yuanrong-datasystem Object Cache 诊断 Skill

## 概述

Object Cache 提供对象发布/获取接口（Create/Put/Publish/Get/Delete/Seal/GIncreaseRef/GDecreaseRef 等）。对象支持嵌套引用、手动生命周期管理（keep）和封印（seal）。分析 Object Cache 日志需要关注访问日志中的 `DS_OBJECT_CLIENT_*` action 和对象状态相关错误码。

## 约束

- 对象生命周期默认自动管理，可通过 `keep=true` 手动管理。
- 对象支持嵌套引用（Nested_keys）。
- 对象封印后不可修改（`is_seal=1`）。
- 对象可分布在本地内存、磁盘、L2 缓存和远端 Worker。

## 流程

1. 在访问日志中过滤 `DS_OBJECT_CLIENT_*` action。
2. 关注 `status_code` 非 0 的请求，特别是对象相关错误码（2000–2006）。
3. 分析 `Object_key`、`Nested_keys`、`keep`、`is_seal` 等参数。
4. 检查对象是否存在本地/远端命中问题（`K_NOT_FOUND_IN_L2CACHE`、`K_WORKER_PULL_OBJECT_NOT_FOUND`）。
5. 检查嵌套引用对象的生命周期和引用计数。
6. 结合 `Cache_Hit_Info` 判断缓存命中情况。

## 能力

- 输出 Object Cache 接口 action 列表和常见错误码。
- 输出对象生命周期、嵌套引用和封印的日志分析方法。
- 输出对象本地/远端命中和 L2 缓存未命中的排查方向。
- 输出对象状态异常（已封印、不存在、被引用）的判断方法。

## 规则

- `keep=true` 时对象需要手动释放，否则可能长期占用内存。
- 封印后的对象修改会返回 `K_OC_ALREADY_SEALED`。
- 嵌套引用对象删除时，需要确保所有引用已释放。
- 对象缓存与 KV Cache 共享资源，资源竞争会影响性能。

## 接口 action 列表

| action | 说明 |
|--------|------|
| DS_OBJECT_CLIENT_CREATE | 创建对象 |
| DS_OBJECT_CLIENT_PUT | 写入对象数据 |
| DS_OBJECT_CLIENT_PUBLISH | 发布对象 |
| DS_OBJECT_CLIENT_GET | 获取对象 |
| DS_OBJECT_CLIENT_DELETE | 删除对象 |
| DS_OBJECT_CLIENT_SEAL | 封印对象 |
| DS_OBJECT_CLIENT_GINCREASEREF | 全局增加引用 |
| DS_OBJECT_CLIENT_GDECREASEREF | 全局减少引用 |
| DS_OBJECT_CLIENT_QUERY_GLOBAL_REF_NUM | 查询全局引用数 |
| DS_OBJECT_CLIENT_GET_OBJ_META_INFO | 获取对象元信息 |

## 关键请求参数

| 参数 | 说明 |
|------|------|
| Object_key | 对象 ID |
| object_keys | 批量对象 ID |
| Nested_keys | 嵌套引用对象 ID |
| keep | 是否手动管理生命周期 |
| Write_mode | 写模式 |
| is_seal | 是否封印 |
| is_retry | 是否重试 |
| data_size | 对象大小 |

## 常见错误模式

### 1. 对象已封印（K_OC_ALREADY_SEALED=2000）

```text
status_code=2000 action=DS_OBJECT_CLIENT_PUT ...
```

可能原因：
- 对象已封印，尝试再次写入。

排查：
- 检查对象是否需要重新创建而不是修改。
- 确认应用写入逻辑。

### 2. 对象不存在（K_NOT_FOUND=3 / K_OC_OBJECT_NOT_IN_USED=2001 / K_WORKER_PULL_OBJECT_NOT_FOUND=2005）

```text
status_code=3 action=DS_OBJECT_CLIENT_GET ...
status_code=2001 action=DS_OBJECT_CLIENT_GET ...
status_code=2005 action=DS_OBJECT_CLIENT_GET ...
```

可能原因：
- 对象未创建或已删除。
- 对象所在 Worker 已下线。
- L2 缓存配置错误或不可达。
- 对象被 LRU 淘汰。

排查：
- 确认对象是否已创建。
- 检查对象所在 Worker 状态。
- 检查 L2 缓存类型和路径。

### 3. 远端批量获取不足（K_OC_REMOTE_GET_NOT_ENOUGH=2002）

```text
status_code=2002 action=DS_OBJECT_CLIENT_GET ...
```

可能原因：
- 远端 Worker 响应不完整。
- 网络/传输层异常导致部分数据丢失。
- 远端对象正在迁移或删除。

排查：
- 检查远端 Worker 日志。
- 检查 URMA/RDMA 连接状态。
- 重试请求。

### 4. 写回队列满（K_WRITE_BACK_QUEUE_FULL=2003）

```text
status_code=2003 action=DS_OBJECT_CLIENT_PUBLISH ...
```

可能原因：
- 写回队列积压，通常因为下游（如 L2 缓存）写入慢。
- L2 缓存不可用或性能差。

排查：
- 检查 `resource.log` 中队列和线程池状态。
- 检查 L2 缓存（OBS/SFS/分布式磁盘）可用性。

### 5. Buffer 已废弃（K_BUFFER_DEPRECATED=2006）

```text
status_code=2006 action=DS_OBJECT_CLIENT_GET ...
```

可能原因：
- 对象数据已被更新或释放，旧 buffer 不再有效。

排查：
- 检查对象是否被重新发布或删除。
- 确认应用是否持有过期 buffer 引用。

## 解析示例

### 统计 Object 接口错误码

```bash
awk -F'|' '$10 ~ /DS_OBJECT_CLIENT/ && $9 != 0 {print $10, $9}' access.log | sort | uniq -c | sort -rn
```

### 提取对象未命中请求

```bash
awk -F'|' '$9 == 3 && $10 == "DS_OBJECT_CLIENT_GET"' access.log
```

### 提取封印对象再修改请求

```bash
awk -F'|' '$9 == 2000 && $10 ~ /DS_OBJECT_CLIENT/' access.log
```

## 注意事项

- 对象缓存和 KV 缓存共享 Worker 内存和磁盘资源，需要整体监控。
- 大对象 publish 会显著影响共享内存和 Spill 磁盘使用。
- 嵌套引用对象的生命周期管理复杂，容易出现引用泄漏或过早释放。
- L2 缓存未命中时，对象可能从远端 Worker 获取，耗时更长。
- 对象封印是不可逆操作，设计应用逻辑时需考虑。
