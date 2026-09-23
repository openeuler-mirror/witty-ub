# Witty RAG MCP 接入指导

Witty-UB 中的 OpenCode Agent 通过 MCP SSE 调用 Witty RAG。推荐链路如下：

```text
Witty-UB/OpenCode -> http://witty-rag-core:12312/sse
                  -> RAG MCP Server
                  -> http://127.0.0.1:9988
                  -> Witty RAG Core -> openGauss
```

`9988` 是 RAG REST API，`12312` 是 Agent 使用的 MCP SSE 接口，两者不能互换。

## 前置文件

准备以下文件和变量：

```bash
export OPENGAUSS_RAG_IMAGE="hub-harbor.oepkgs.net/neocopilot/opengauss:latest"
export WITTY_RAG_CORE_IMAGE="hub-harbor.oepkgs.net/neocopilot/witty-rag-core:0.10.2-release-arm"
export RAG_SOURCE_DIR="/home/euler-copilot-rag"
export RAG_CONFIG_FILE="$(pwd)/deploy/rag-core.toml"
```

`config.toml` 中标量库和向量库应使用容器 DNS 名：

```toml
[service]
uvicorn_ip = "0.0.0.0"
uvicorn_port = 9988

[scalar_db]
database_type = "opengauss"
database_host = "opengauss-rag"
database_port = 5432

[vector_db]
database_type = "opengauss"
database_host = "opengauss-rag"
database_port = 5432
```

模型名称、地址、API Key 和数据库密码按实际环境填写，不要提交到 Git。

## 1. 创建共享网络

### 部署脚本一键启动（推荐）

部署脚本现在可以先创建专用 openGauss 和 RAG Core，再启动 Witty-UB：

```bash
sudo install -d -m 700 /etc/witty-ub
chmod 600 deploy/rag-core.toml
sudo sh -c 'umask 077; printf "%s" "<RAG_DB_PASSWORD>" > /etc/witty-ub/rag-opengauss.passwd'

# 先编辑 deploy/rag-core.toml，填写模型名称、地址和 API Key。
bash deploy/docker/deploy_witty.sh --with-rag --image witty-ub:latest
```

脚本会强制把运行时配置中的 `[scalar_db]` 和 `[vector_db]` 都改为
`opengauss-rag:5432`，因此 openGauss 同时作为 RAG 的标量库和向量库。
已有同名容器只会被复用和接入网络，不会被删除；这可以避免误删已有数据。

也可以只部署数据库和 RAG：

```bash
bash deploy/docker/deploy_rag.sh
```

下面是对应的手工部署过程。

```bash
docker network create witty-ub-network 2>/dev/null || true
```

Witty-UB、RAG Core 和 openGauss 必须加入同一网络，才能使用容器名互相访问。

## 2. 启动 openGauss

```bash
docker run -d \
  --name opengauss-rag \
  --restart unless-stopped \
  --network witty-ub-network \
  -p 5440:5432 \
  -e GS_PASSWORD='<CHANGE_ME>' \
  "${OPENGAUSS_RAG_IMAGE}"
```

首次启动完成后，按 RAG 文档要求启用空字符串兼容：

```bash
docker exec -u omm opengauss-rag \
  gs_guc reload -D /var/lib/opengauss/data \
  -c "behavior_compat_options='accept_empty_str'"
```

## 3. 启动 RAG Core

```bash
mkdir -p /opt/witty-rag/logs

docker run -d \
  --name witty-rag-core \
  --restart unless-stopped \
  --network witty-ub-network \
  -p 9990:9988 \
  -e RAG_WORKERS=4 \
  -v "${RAG_CONFIG_FILE}:/rag-service/rag_core/config.toml:ro" \
  -v /opt/witty-rag/logs:/rag-service/logs \
  "${WITTY_RAG_CORE_IMAGE}"
```

验证 REST 服务：

```bash
docker exec witty-rag-core \
  curl -fsS http://127.0.0.1:9988/health_check
curl -fsS http://127.0.0.1:9990/health_check
```

## 4. 在 RAG Core 中启动 MCP SSE

当前 RAG MCP 源码使用 MCP Python SDK 1.x 的 `FastMCP` API，因此必须固定 `mcp<2`：

```bash
docker exec witty-rag-core pip install \
  'mcp<2' 'fastapi>=0.115.0' 'starlette>=0.49.1' APScheduler pyyaml

docker cp "${RAG_SOURCE_DIR}" \
  witty-rag-core:/rag-service/euler-copilot-rag

docker exec witty-rag-core cp \
  /rag-service/rag_core/config.toml \
  /rag-service/euler-copilot-rag/rag_core/config.toml

docker exec witty-rag-core sh -lc '
  cd /rag-service/euler-copilot-rag/rag_core/agent/rag_core_mcp
  RAG_CORE_BASE_URL=http://127.0.0.1:9988 \
  RAG_CORE_MCP_HOST=0.0.0.0 \
  RAG_CORE_MCP_PORT=12312 \
  nohup python3 server.py >/tmp/rag-mcp.log 2>&1 &
'
```

验证 MCP SSE：

```bash
docker exec witty-rag-core tail -50 /tmp/rag-mcp.log
docker exec witty-rag-core sh -lc \
  'curl -sS --max-time 2 -D - http://127.0.0.1:12312/sse -o /dev/null || true'
```

SSE 是长连接，`curl` 在短超时后退出是正常现象；响应头应包含 `200 OK` 和 `text/event-stream`。

> 当前上游实现中，直接重启 `witty-rag-core` 会终止 MCP 进程，需要重新执行本节最后一条启动命令。生产环境建议把 MCP 制作为独立镜像/Compose 服务并配置 `restart: unless-stopped`。

## 5. 启动 Witty-UB

项目默认 MCP 地址已经设置为：

```text
http://witty-rag-core:12312/sse
```

Docker Compose 启动：

```bash
export WITTY_RAG_MCP_URL="http://witty-rag-core:12312/sse"
docker compose up -d postgres witty-ub
```

使用部署脚本：

```bash
WITTY_RAG_MCP_URL="http://witty-rag-core:12312/sse" \
  bash deploy/docker/deploy_witty.sh --image witty-ub:latest
```

如果 RAG 位于另一个已存在的 Docker 网络：

```bash
WITTY_RAG_NETWORK="witty-rag-net" \
WITTY_RAG_MCP_URL="http://witty-rag-core:12312/sse" \
  bash deploy/docker/deploy_witty.sh --image witty-ub:latest
```

## 6. 验证 Agent 连接

```bash
docker exec witty-ub getent hosts witty-rag-core
docker exec witty-ub curl -fsS \
  http://witty-rag-core:9988/health_check

docker exec witty-ub sh -lc '
  cd /var/witty-ub/witty_ub_diagnostician
  opencode mcp list
'
```

预期状态：

```text
witty-rag connected
http://witty-rag-core:12312/sse
```

Agent 应能发现 `rag_health_check`、`rag_kb_manager`、`rag_doc_manager`、`rag_chunk_manager` 等工具。

## 故障排查

- `Could not resolve host: witty-rag-core`：容器不在同一个 Docker 网络。
- `Connection refused :12312`：MCP `server.py` 未启动或随 RAG 容器重启而退出。
- `No module named mcp.server.fastmcp`：错误安装了 MCP SDK 2.x，重新安装 `mcp<2`。
- RAG 健康检查失败：先检查 `/tmp/rag-mcp.log`、RAG 日志、`config.toml` 中的数据库主机和模型地址。
