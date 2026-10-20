# Witty RAG MCP 工具速查

来源：`euler-copilot-rag` `release-0.10.2` 分支的 `rag_core/agent/rag_core_mcp`。

所有工具返回：

```json
{"success":true,"message":"success","data":{},"http_status":200}
```

## 工具与 action

| 工具 | action | 核心必填参数 |
|---|---|---|
| `rag_health_check` | `check` | 无 |
| `rag_access_key_manager` | `create` | `owner_id`, `owner_name` |
|  | `get`, `delete` | 无；使用服务端 access key |
|  | `update` | 至少一个更新字段 |
|  | `list` | `owner_id` |
| `rag_kb_manager` | `create` | `name`; `meta_data_type=document/json` |
|  | `get`, `update`, `delete`, `search_methods`, `export` | `kb_id` |
|  | `list` | 无；可按名称/所有者过滤 |
|  | `import` | `zip_paths` |
|  | `download_export` | `task_id` |
| `rag_doc_manager` | `upload` | `kb_id`, `file_paths` |
|  | `list` | `kb_id` |
|  | `get`, `update`, `delete`, `run_parse`, `download`, `parse_modes` | `doc_id` |
|  | `switch` | `doc_ids`, `enabled` |
| `rag_chunk_manager` | `search` | `kb_id+query`，或 `search_configs` |
|  | `list` | `doc_id` |
|  | `update` | `chunk_id`, `content` |
|  | `switch` | `chunk_ids`, `enabled` |
|  | `delete` | `chunk_id` |
| `rag_json_manager` | `create` | `kb_id`, `name`, `content` |
|  | `list` | `kb_id` |
|  | `get`, `delete` | `json_id` |
|  | `search` | `kb_id+query`，或 `search_configs` |
| `rag_task_manager` | `get`, `delete` | `task_id` |
|  | `list` | `kb_id` |
|  | `batch_delete` | `task_ids` |
| `rag_trace_manager` | `list` | 无；可按名称/任务过滤 |
|  | `get`, `delete`, `list_details` | `trace_id` |
|  | `get_detail` | `trace_detail_id` |
| `rag_model_manager` | `get`, `update` | `model_id` |

## 通用分页和时间字段

支持分页的 action 使用：

```json
{
  "page_num": 1,
  "page_size": 20,
  "created_at_start": "YYYY-MM-DD HH:MM:SS",
  "created_at_end": "YYYY-MM-DD HH:MM:SS",
  "created_at_desc": true
}
```

## Chunk search 参数

| 字段 | 说明 |
|---|---|
| `kb_id` | 知识库 ID |
| `query` | 检索文本 |
| `top_k` | 返回数量，默认 5 |
| `search_method` | `hybrid_search`, `doc2chunk_search`, `json_search` |
| `doc_ids` | 限定文档 |
| `banned_doc_ids` | 排除文档 |
| `banned_chunk_ids` | 排除 chunk |
| `is_related_surrounding` | 是否带相邻上下文，默认 true |
| `is_classify_by_doc` | 是否按文档分组，默认 false |
| `is_rerank` | 是否重排，默认 false |
| `is_compress` | 是否压缩，默认 false |
| `tokens_limit` | token 上限，默认 8192 |
| `ratio` | 语义检索占比 0-1，默认 0.5 |
| `need_raw_data` | 是否返回原始数据 |
| `search_configs` | 多知识库检索配置数组 |

## 文档操作字段

| 字段 | 说明 |
|---|---|
| `file_paths` | MCP 容器内可见的绝对路径列表 |
| `parse_mode` | 文档解析模式 |
| `chunk_size` | 分块大小 |
| `parse_status` | 列表状态过滤 |
| `run` | `run_parse` 中 true=启动、false=停止 |
| `enabled` | `switch` 中启用/禁用状态 |

## `payload_json`

所有 manager 参数都支持 `payload_json` 透传 REST 请求体；它与结构化字段合并时优先生效。只有上层字段无法表达服务端新参数时才使用，使用前应确认 RAG Core 的真实请求 schema，避免绕过参数校验规则。
