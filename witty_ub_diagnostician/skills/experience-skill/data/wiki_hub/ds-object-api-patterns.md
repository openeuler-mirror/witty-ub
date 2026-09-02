---
name: "yuanrong-datasystem Object Cache 接口日志模式"
description: "汇总 openYuanrong datasystem Object Cache 接口的访问日志模式、关键参数、常见错误码和排查方法。"
keywords:
  - yuanrong-datasystem
  - datasystem
  - Object Cache
  - DS_OBJECT_CLIENT
  - Publish
  - Get
  - Delete
  - Seal
  - 嵌套引用
  - keep
references:
  - name: "yuanrong-datasystem 0.8.1.rc20 Object Client 实现"
    type: offline
    source: "yuanrong-datasystem-0.8.1.rc20/src/datasystem/client/object_cache/object_client.cpp"
  - name: "yuanrong-datasystem 0.8.1.rc20 日志指南"
    type: offline
    source: "yuanrong-datasystem-0.8.1.rc20/docs/source_zh_cn/appendix/log_guide.md"
---

# yuanrong-datasystem Object Cache 接口日志模式

## 概述

Object Cache 提供对象发布/获取接口，支持嵌套引用、手动生命周期管理（keep）和封印（seal）。本文档汇总访问日志中的 action、关键参数和典型错误模式。

## 1. 接口 action

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

## 2. 关键请求参数

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

## 3. 常见错误模式

### 3.1 对象已封印

```text
status_code=2000 action=DS_OBJECT_CLIENT_PUT ...
```

说明：对象已封印，不可修改。

### 3.2 对象不存在

```text
status_code=3 action=DS_OBJECT_CLIENT_GET ...
status_code=2001 action=DS_OBJECT_CLIENT_GET ...
status_code=2005 action=DS_OBJECT_CLIENT_GET ...
```

可能原因：未创建、已删除、Worker 下线、L2 缓存未命中、LRU 淘汰。

### 3.3 远端批量获取不足

```text
status_code=2002 action=DS_OBJECT_CLIENT_GET ...
```

可能原因：远端 Worker 响应不完整、网络异常、对象迁移中。

### 3.4 写回队列满

```text
status_code=2003 action=DS_OBJECT_CLIENT_PUBLISH ...
```

可能原因：L2 缓存写入慢或不可用、队列积压。

### 3.5 Buffer 已废弃

```text
status_code=2006 action=DS_OBJECT_CLIENT_GET ...
```

说明：对象数据已更新或释放，旧 buffer 无效。

## 4. 解析示例

### 统计 Object 错误码

```bash
awk -F'|' '$10 ~ /DS_OBJECT_CLIENT/ && $9 != 0 {print $10, $9}' access.log | sort | uniq -c | sort -rn
```

### 提取对象未命中请求

```bash
awk -F'|' '$9 == 3 && $10 == "DS_OBJECT_CLIENT_GET"' access.log
```

## 注意事项

- keep=true 时需要手动释放对象，否则可能内存泄漏。
- 嵌套引用对象删除前需确保所有引用已释放。
- 大对象 publish 会显著影响共享内存和 Spill 磁盘使用。
- L2 缓存未命中时，对象从远端 Worker 获取，耗时更长。
