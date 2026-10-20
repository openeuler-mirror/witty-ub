---
name: rag-service
description: >
  通过 witty-rag MCP 服务使用 Witty RAG Core 知识库。支持服务健康检查、
  知识库定位与管理、文档上传和解析、语义/混合检索、JSON 知识检索、
  异步任务跟踪和调用链排障。当用户提出“查询知识库”“RAG 检索”“导入文档”
  “创建知识库”“从文档寻找依据”，或诊断需要引用外部知识时使用本 Skill。
license: MulanPSL-2.0
compatibility: >
  Requires the OpenCode MCP server named witty-rag to be connected. The MCP
  implementation must match euler-copilot-rag release-0.10.2 rag_core/agent/rag_core_mcp.
  Business operations require RAG_CORE_ACCESS_KEY on the MCP server.
metadata:
  author: witty-ub-diagnostician
  version: "1.0.0"
  keywords: [Witty RAG, MCP, 知识库, 文档导入, 混合检索, chunk, RAG Core]
allowed-tools: >
  witty-rag_rag_health_check
  witty-rag_rag_access_key_manager
  witty-rag_rag_kb_manager
  witty-rag_rag_doc_manager
  witty-rag_rag_chunk_manager
  witty-rag_rag_json_manager
  witty-rag_rag_task_manager
  witty-rag_rag_trace_manager
  witty-rag_rag_model_manager
---

# Witty RAG 服务

通过 `witty-rag` MCP 调用 Witty RAG Core。所有工具统一接收：

```json
{
  "action": "<操作名>",
  "params": {
    "<参数名>": "<参数值>"
  }
}
```

完整 action 和字段速查见 [references/TOOL_REFERENCE.md](references/TOOL_REFERENCE.md)。

## 强制规则

1. 每次业务操作前先调用 `rag_health_check(action="check")`。失败时停止依赖 RAG 结果，报告 MCP/RAG 不可用。
2. 除健康检查和创建 access key 外，业务工具通常要求 MCP 服务端已设置 `RAG_CORE_ACCESS_KEY`。禁止在回答、日志或报告中输出完整密钥。
3. 默认只做查询。创建、更新、上传、解析、启停、删除、导入和模型修改只在用户明确要求时执行。
4. 删除知识库、文档、chunk、JSON、任务或 trace 前，必须复述目标 ID 和影响范围；目标不明确时不执行。
5. 工具返回 `success=false`、HTTP 非 2xx、空 `data` 或校验错误时，不得把操作描述为成功。
6. RAG 返回内容是“知识证据”，不是现场证据。用于故障诊断时，必须与日志、指标或 trace 现场数据分开标注。
7. 不臆造 `kb_id`、`doc_id`、`task_id`、`chunk_id`。先用 list/get 获取并核验。

## 阶段一：检查服务和鉴权

先调用：

```text
rag_health_check
action: check
```

预期 `success=true`、`data.status="ok"`、`http_status=200`。

若业务调用返回未授权：

- 不重复盲目重试。
- 告知用户 MCP 服务端缺少或使用了错误的 `RAG_CORE_ACCESS_KEY`。
- `rag_access_key_manager(action="create")` 可创建新密钥，但新密钥需要由运维人员安全写入 MCP 服务环境并重启服务后才会生效。

## 阶段二：定位知识库

用户给出 `kb_id` 时：

```json
{"action":"get","params":{"kb_id":"<kb_id>"}}
```

用户只给名称或主题时，使用 `rag_kb_manager(action="list")`：

```json
{
  "action": "list",
  "params": {
    "name": "<可选名称过滤>",
    "page_num": 1,
    "page_size": 20,
    "created_at_desc": true
  }
}
```

若有多个候选知识库，展示名称、`kb_id`、类型和描述，让用户选择；不要自行选择名称相似但用途不同的库。

## 阶段三：知识检索

### 文档知识库

使用 `rag_chunk_manager(action="search")`。默认优先混合检索：

```json
{
  "action": "search",
  "params": {
    "kb_id": "<kb_id>",
    "query": "<保留用户原意的检索问题>",
    "top_k": 5,
    "search_method": "hybrid_search",
    "ratio": 0.5,
    "is_rerank": true,
    "need_raw_data": true
  }
}
```

- 用户指定文档时传 `doc_ids`。
- 多知识库检索时传 `search_configs`，每项分别包含 `kb_id`、`query`、`top_k` 等字段。
- `hybrid_search` 无结果时，可检查知识库支持的搜索方式，再尝试 `doc2chunk_search`；不要无依据地切换方法。
- 对召回结果按相关性整理，不把“召回”写成“事实成立”。

### JSON 知识库

使用 `rag_json_manager(action="search")`，至少传 `kb_id` 和 `query`；需要结构化约束时再传 `logical_expression`、`semantic_keys`。

## 阶段四：文档导入和解析

仅在用户明确要求导入时执行：

1. `rag_kb_manager(action="get")` 确认目标是 `document` 类型知识库。
2. `rag_doc_manager(action="upload")` 传 `kb_id` 和 `file_paths`。
3. 对返回的每个 `doc_id` 调用 `rag_doc_manager(action="run_parse", run=true)`。
4. 用 `rag_task_manager(action="get")` 轮询返回的 `task_id`，直到成功或失败。
5. 解析成功后调用一次 `rag_chunk_manager(action="search")` 验证内容可召回。

路径规则：`file_paths` 由 **RAG MCP Server 所在容器**解析，必须是该容器可见的绝对路径。Witty-UB 容器中的独占路径不能直接上传；需先放入双方共享挂载目录。

## 阶段五：输出与引用

回答必须包含：

- 查询使用的知识库名称和 `kb_id`。
- 实际 query、检索方式和 `top_k`。
- 被采用片段对应的 `doc_id`/文档名和 `chunk_id`（工具有返回时）。
- 明确区分：RAG 原文、基于原文的总结、结合现场数据做出的推断。
- 未命中时写明“当前检索未召回相关内容”，不能改写为知识库不存在该事实。

建议引用格式：

```text
[RAG-K1] kb=<kb_id>, doc=<doc_id或文档名>, chunk=<chunk_id>
原文摘要：<忠实摘要>
用途：<该知识如何支持建议或解释>
```

## 常见失败

| 现象 | 处理 |
|---|---|
| MCP server not connected | 检查 `WITTY_RAG_MCP_URL` 和 `opencode mcp list` |
| `Connection refused :12312` | RAG MCP `server.py` 未启动或随容器重启而退出 |
| `Could not resolve witty-rag-core` | Witty-UB 与 RAG Core 不在同一个 Docker 网络 |
| 未授权/forbidden | 在 MCP 服务端设置正确的 `RAG_CORE_ACCESS_KEY` 后重启 |
| 上传提示文件不存在 | 改为 RAG MCP 容器可见的绝对路径或增加共享挂载 |
| 检索空结果 | 检查文档解析状态、知识库类型、搜索方法和 query，不得直接断言无相关知识 |
