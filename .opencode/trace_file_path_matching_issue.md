# Trace operation和pod为空问题：文件路径匹配配置缺失

## 问题现象

用户提供的日志样例：
```
2026-06-30T17:05:04.907453 | I | access_recorder.cpp:182 | searchctrwirelesskvworker-24-00104 | 114:1029 | 084a61aa-c503-4281-b10a-e2aa7e7bc0da | model_kvcache_predictor | 5 | DS_POSIX_GET | 11714 | 0 | {Object_key:...} | URMA wait fallback...
```

关键信息：
- handle（operation）= `DS_POSIX_GET` （**Worker操作类型**）
- pod_name = `searchctrwirelesskvworker-24-00104`
- trace_id = `084a61aa-c503-4281-b10a-e2aa7e7bc0da`

**问题**：这条日志所在的trace没有被识别为GET类型，operation和pod字段为空。

## 根本原因

### 问题1：文件路径不匹配导致日志未被扫描

#### 默认文件路径匹配模式

**SDK Access日志**（`kvcache_log_file.py:4-9`）：
```python
_DEFAULT_SDK_ACCESS_LOG_PATTERNS = [
    "SDK_*/ds_client_access_*.log",
    "SDK_*/ds_client.log",
    "SDK_*/ds_client_access.log",
    "*_split_access.log",
]
```

**Worker Access日志**（`kvcache_log_file.py:11-17`）：
```python
_DEFAULT_WORKER_ACCESS_LOG_PATTERNS = [
    "*worker_*/access.log",
    "*worker_*/access*.log",
    "*worker_*/access.log.gz",
    "*worker_*/access*.log.gz",
    "*_split_access.log",
]
```

#### 问题触发场景

用户提到："文件名不在默认的路径中，需要被拆分"，说明：

1. **实际文件路径不符合默认模式**：
   - 默认Worker模式期望：`*worker_*/access.log`（如`data/worker_1/access.log`）
   - 用户文件可能是：`data/searchctrwirelesskvworker-24-00104.log`或其他格式

2. **FileParserMapBuilder找不到匹配的文件**（`file_parser_map_builder.py:63-64`）：
```python
patterns = [os.path.join(self.log_dir, "**", p) for p in parser.patterns]
paths = glob_paths(patterns)  # ⚠️ 如果路径不匹配，paths为空
```

3. **该文件不会被WorkerAccessLogParser扫描**：
   - 没有LogEntry被创建
   - 日志内容中的Worker Access信息丢失

4. **如果该trace也没有SDK Access日志**：
   - 整个trace没有任何Access日志
   - 只有URMA/Link等其他类型日志
   - 这些日志没有operation字段
   - 最终trace的operation字段为空

### 问题2：*_split_access.log模式冲突

注意：`*_split_access.log`同时出现在两个默认模式中：
```python
SDK默认模式: ["*_split_access.log", ...]
Worker默认模式: ["*_split_access.log", ...]
```

如果文件名是`xxx_split_access.log`：
1. SDK parser会扫描（但Worker operation不在SDK_GET_OPS中，会被跳过）
2. Worker parser也会扫描（正确处理）
3. 这种设计是为了支持"拆分后的access日志"，但需要文件名符合规范

### 问题3：配置未设置或设置不正确

**配置机制**（`kv_cache_log_parse_worker.py:370-374`）：
```python
filename_config = diagnosis_config.log_filename_pattern
sdk_parsers[0]._runtime_patterns = filename_config.ds_client_access_log_file
for parser in worker_access_parsers:
    parser._runtime_patterns = filename_config.ds_worker_access_log_file
```

**配置示例**（`kv_cache_log_event_diagnosis_worker.py:311-313`）：
```python
{
    "ds_client_access_log_file": ["ds_client_access*.log", "*_access.log", "*_split_access.log"],
    "ds_worker_access_log_file": ["access.log", "access*.log", "*_access.log", "*_split_access.log"],
}
```

如果配置未设置或设置不正确：
- `_runtime_patterns`为空列表
- 使用默认模式
- 如果默认模式也不匹配，文件被跳过

## 影响链路

```
文件路径不符合默认模式 
→ FileParserMapBuilder找不到文件 
→ WorkerAccessLogParser不扫描该文件 
→ LogEntry未创建 
→ 该trace的Worker Access信息丢失
→ 如果该trace也没有SDK Access日志
→ 整个trace没有operation信息 
→ operation和pod字段为空
```

## 解决方案

### 方案1：正确配置文件路径模式（推荐）

**步骤1：确认实际文件路径**

```bash
# 查找所有日志文件
find data/logs -type f -name "*.log" | head -20

# 示例输出
data/logs/searchctrwirelesskvworker-24-00104/access.log
data/logs/worker-A/access.log
data/logs/SDK-B/ds_client_access.log
```

**步骤2：更新diagnosis_config.json**

```json
{
  "log_filename_pattern": {
    "ds_client_access_log_file": [
      "SDK_*/ds_client_access*.log",
      "*_split_access.log",
      "ds_client_access*.log"
    ],
    "ds_worker_access_log_file": [
      "*worker*/access.log",
      "*wirelesskvworker*/access.log",
      "*_split_access.log",
      "access.log"
    ],
    "ds_client_info_log_file": [
      "SDK_*/ds_client*.INFO.log"
    ],
    "ds_worker_info_log_file": [
      "*worker*/datasystem_worker.INFO.*"
    ]
  }
}
```

**步骤3：验证配置生效**

```python
# 检查runtime_patterns是否设置
from latency.parse.worker_access_log_parser import WorkerAccessLogParser
from latency.config.config import Config

parser = WorkerAccessLogParser()
config = Config().get_diagnosis_config()
print(f"Worker patterns: {parser.patterns}")  # 应该显示配置的模式
```

### 方案2：支持更灵活的文件路径匹配

**改进默认模式**（`kvcache_log_file.py`）：

```python
_DEFAULT_SDK_ACCESS_LOG_PATTERNS = [
    "SDK_*/ds_client_access_*.log",
    "SDK_*/ds_client.log",
    "SDK_*/ds_client_access.log",
    "*_split_access.log",
    "ds_client_access*.log",  # ✅ 新增：支持无目录前缀
]

_DEFAULT_WORKER_ACCESS_LOG_PATTERNS = [
    "*worker*/access*.log",  # ✅ 改进：更通用的worker匹配
    "*worker_*/access*.log",
    "*_split_access.log",
    "access.log",  # ✅ 新增：支持无目录前缀
    "access*.log",
]
```

### 方案3：增强文件扫描日志

**添加扫描统计日志**（`file_parser_map_builder.py`）：

```python
def _log_statistics(self, file_parser_map: dict[str, list["LogParser"]]) -> None:
    # ... 现有逻辑 ...
    
    # ✅ 新增：输出未匹配文件的警告
    if total_files == 0:
        logger.warning(
            f"No log files found matching patterns. "
            f"Please check log_filename_pattern in diagnosis_config.json"
        )
        logger.info(f"SDK patterns: {[p.patterns for p in self.parsers if 'SDK' in p.label]}")
        logger.info(f"Worker patterns: {[p.patterns for p in self.parsers if 'Worker' in p.label]}")
```

### 方案4：统一access日志处理

**问题**：`*_split_access.log`同时被两个parser扫描，可能造成冗余。

**改进**：根据日志内容动态判断类型

```python
# worker_access_log_parser.py
def match_line(self, line: str, pod_ip: str) -> LogEntry | None:
    parsed = self.parse_access_line(line)
    if not parsed:
        return None
    
    # ✅ 改进：允许所有以DS_开头的operation
    handle = parsed.get("handle", "")
    if not handle.startswith("DS_"):
        return None
    
    # 根据handle内容判断是SDK还是Worker操作
    if handle in SDK_GET_OPS or handle in SDK_SET_OPS:
        # SDK操作，跳过（让SdkAccessLogParser处理）
        return None
    
    # Worker操作，继续处理
    # ... 现有逻辑 ...
```

## 验证方法

### 1. 检查文件是否被扫描

```python
from latency.parse.parallel_scanner.file_parser_map_builder import FileParserMapBuilder
from latency.parse import SdkAccessLogParser, WorkerAccessLogParser

parsers = [SdkAccessLogParser(), WorkerAccessLogParser()]
builder = FileParserMapBuilder("data/logs", parsers)
file_parser_map = builder.build()

print(f"Total files: {len(file_parser_map)}")
for file_path, parser_list in file_parser_map.items():
    print(f"{file_path}: {[p.label for p in parser_list]}")
```

### 2. 检查日志内容是否被解析

```python
from latency.parse.worker_access_log_parser import WorkerAccessLogParser

parser = WorkerAccessLogParser()
test_line = "2026-06-30T17:05:04.907453 | I | ... | DS_POSIX_GET | ..."
entry = parser.match_line(test_line, "10.0.0.1")

print(f"Entry: {entry}")
if entry:
    print(f"operation: {entry.operation}")
    print(f"pod_ip: {entry.pod_ip}")
```

### 3. 检查trace聚合结果

```python
# 解析整个日志目录后，检查trace是否包含Worker Access条目
from latency.task.worker.kv_cache_log_parse_worker import KVCacheLogParseWorker

# ... 运行解析 ...
trace_entries = parsed.get("Worker access parse", [])
print(f"Worker Access entries: {len(trace_entries)}")
```

## 调试建议

### 1. 添加文件扫描日志

在`file_parser_map_builder.py:64`后添加：
```python
paths = glob_paths(patterns)
logger.info(f"[{parser.label}] Found {len(paths)} files: {[os.path.basename(p) for p in paths[:5]]}")
```

### 2. 检查配置文件

```bash
# 查看当前配置
cat diagnosis_config.json | jq '.log_filename_pattern'

# 示例输出
{
  "ds_client_access_log_file": ["SDK_*/ds_client_access*.log"],
  "ds_worker_access_log_file": ["*worker*/access.log"]
}
```

### 3. 测试路径匹配

```python
import fnmatch
import os

patterns = ["*worker*/access.log"]
file_path = "data/logs/searchctrwirelesskvworker-24-00104/access.log"

matched = any(
    fnmatch.fnmatch(os.path.basename(file_path), p) 
    for p in patterns
)
print(f"File matched: {matched}")  # 应该为True
```

## 总结

**核心问题**：文件路径不符合默认匹配模式，导致Worker Access日志未被扫描，进而导致相关trace的operation和pod字段为空。

**关键修复**：
1. 在`diagnosis_config.json`中正确设置`log_filename_pattern`
2. 确保所有日志文件都能被正确匹配
3. 验证配置生效（检查`parser.patterns`和扫描结果）

**相关文件**：
- `src/plugins/latency/regex/kvcache_log_file.py` - 默认模式定义
- `src/plugins/latency/schemas/config.py` - 配置类定义
- `src/plugins/latency/parse/parallel_scanner/file_parser_map_builder.py` - 文件扫描逻辑
- `diagnosis_config.json` - 运行时配置文件