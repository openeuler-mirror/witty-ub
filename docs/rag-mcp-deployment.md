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
# 手动部署时按架构与 CPU 指令集选择镜像。
case "$(uname -m)" in
  x86_64|amd64)
    export OPENGAUSS_RAG_IMAGE="${OPENGAUSS_RAG_IMAGE:-hub-harbor.oepkgs.net/neocopilot/opengauss@sha256:4fd44608ca3571d3ceb5bc2bc5cbcde131dde2ed2b8068ff3f58effc8c60d885}"
    export WITTY_RAG_CORE_IMAGE="${WITTY_RAG_CORE_IMAGE:-hub-harbor.oepkgs.net/neocopilot/witty-rag-core:0.10.2-release-x86}" ;;
  aarch64|arm64)
    if grep -qw atomics /proc/cpuinfo; then
      export OPENGAUSS_RAG_IMAGE="${OPENGAUSS_RAG_IMAGE:-hub-harbor.oepkgs.net/neocopilot/opengauss@sha256:38a63d58b2b41e3668cde9f9588a74cb4e8aee76b301f7feb86d6a49d871f10c}"
    else
      export OPENGAUSS_RAG_IMAGE="${OPENGAUSS_RAG_IMAGE:-${OPENGAUSS_RAG_IMAGE_NO_LSE:-hub-harbor.oepkgs.net/neocopilot/opengauss:7.0.0-lite-noLSE}}"
    fi
    export WITTY_RAG_CORE_IMAGE="${WITTY_RAG_CORE_IMAGE:-hub-harbor.oepkgs.net/neocopilot/witty-rag-core:0.10.2-release-arm}" ;;
  *)
    echo "不支持的架构，请显式选择兼容镜像。" >&2
    exit 1 ;;
esac
export RAG_CONFIG_FILE="$(pwd)/deploy/rag-core.toml"
```

使用部署脚本时无需执行上述镜像选择命令。`deploy_rag.sh` 在 ARM64 无 LSE
（`/proc/cpuinfo` 不含 `atomics`）时使用
`OPENGAUSS_RAG_IMAGE_NO_LSE`（默认 `hub-harbor.oepkgs.net/neocopilot/opengauss:7.0.0-lite-noLSE`）。
ARM64 有 LSE 时优先复用本地 Kunpeng HNSW 镜像，不存在时使用 ARM64 固定摘要；
x86_64 使用 x86_64 固定摘要。显式设置 `OPENGAUSS_RAG_IMAGE` 可覆盖自动选择。
noLSE 镜像基于 openGauss-Lite，支持 HNSW，但不包含鲲鹏 SRA Recall 的 PQ 加速。

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

模型名称、接口地址、API Key 和数据库密码由部署配置提供。含凭据的配置文件应限制访问权限，
不要纳入版本控制。

## 0. 配置 embedding 模型（必填项）

语义检索依赖 embedding。RAG Core 只认 **OpenAI 兼容的 `/v1/embeddings` 接口**，
因此可以指向任何实现了该协议的服务：公网 SaaS、内网自建 vLLM/TEI，或宿主机上的本地推理服务。

默认使用硅基流动的 `BAAI/bge-m3`，端点为
`https://api.siliconflow.cn/v1/embeddings`。使用该服务需要提供有效的 API Key。
要改用其它服务，可修改 `deploy.conf` 或在部署时通过环境变量覆盖：

| 变量 | 说明 | 默认 |
| --- | --- | --- |
| `RAG_EMBEDDING_ENDPOINT` | 完整的 `/v1/embeddings` 地址 | `https://api.siliconflow.cn/v1/embeddings` |
| `RAG_EMBEDDING_MODEL_NAME` | 端点上的模型名 | `BAAI/bge-m3` |
| `RAG_EMBEDDING_DIMENSION` | 向量维度上限，写入 `[service] max_vector_dimension` | `1024` |
| `RAG_EMBEDDING_API_KEY` | 服务的 API Key；仅无鉴权服务可留空 | 空（未配置） |
| `RAG_MODEL_API_KEY_SECRET_FILE` | 需要持久化 Key 时的文件路径 | `/etc/witty-ub/rag-secrets/model-api-key` |
| `RAG_RERANK_ENABLED` | 是否启用 rerank，`0`/`1` | `0`（关闭） |

### API Key 与鉴权

- 默认硅基流动服务需要有效的 API Key；配置为空不代表该服务支持无鉴权访问。
- 本地服务常常**没有鉴权**：不填 `RAG_EMBEDDING_API_KEY` 即可，脚本不会强制生成密钥文件。
- 有鉴权时，API Key 通过 `Authorization: Bearer <API_KEY>` 请求头发送。
- Key 会写入 `RAG_MODEL_API_KEY_SECRET_FILE`（权限 `0600`），不会进入容器环境变量或 Git。

### 服务在宿主机（不在 Docker 网络内）

RAG Core 运行在容器里，要访问宿主机上的模型服务需要一个容器可达的地址：

将 `RAG_EMBEDDING_ENDPOINT` 设置为容器可达的完整 `/v1/embeddings` 地址。可以使用宿主机
的局域网地址，或根据 Docker 网络配置确定网关地址；不要使用容器内的 `127.0.0.1`。

```bash
# 先设置 RAG_EMBEDDING_ENDPOINT，再部署。
RAG_EMBEDDING_ENDPOINT="${RAG_EMBEDDING_ENDPOINT}" \
RAG_EMBEDDING_MODEL_NAME="BAAI/bge-m3" \
RAG_EMBEDDING_DIMENSION="1024" \
  bash deploy/docker/manage.sh install-rag
```

vLLM、TEI、Xinference 等服务的 embedding 接口路径都是 `/v1/embeddings`，可直接使用；
只有提供 chat 接口、没有 embedding 接口的服务不能用于语义检索。

### 维度与换模型

- `max_vector_dimension` 是**上限**，实际向量不足时会补齐，超过则写入失败：
  维度不高于上限的模型可以直接用；3072 维模型（如 `text-embedding-3-large`）需要调大上限。
- **更换 embedding 模型必须全量重建索引**（不同模型的向量不可比），维度变化还需重建向量集合。
  重建后要重新校准 `RAG_MIN_SCORE`。
- 更换知识库（包括删除后重建为新 ID）后，原有映射不能用于新知识库的检索。
  后端启动时会核对映射，将旧知识库的映射退役并重新发布；也可以手动触发：

  ```bash
  docker exec witty-ub /var/witty-ub/latency/.venv/bin/python \
    -m latency.access.phenomenon_cli --reconcile
  ```

  返回结果中的 `stale_kb` 表示已退役的旧知识库映射数量；可通过
  `GET /phenomenon/status` 的 `cards.searchable` 查看重建进度。

### 健康检查

部署结束会探测一次端点；之后随时可用 `manage.sh status` 复查：

```text
RAG health:
  openGauss   healthy
  RAG REST    ok
  RAG MCP     ok
  embedding   BAAI/bge-m3 @ <配置的 embedding 地址> [ok]
  rerank      disabled
```

`embedding` 行出现 `unreachable` / `auth-failed` 时，语义检索不可用（结构化检索不受影响），
优先检查端点可达性、端口映射和 API Key。

---

## 1. 创建共享网络

### 部署脚本一键启动（推荐）

部署脚本先创建专用 openGauss 和 RAG Core，再启动 Witty-UB：

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

> 部署脚本（`manage.sh install-rag` / `deploy_rag.sh`）默认拉取预构建的
> `hub-harbor.oepkgs.net/neocopilot/witty-rag-core:mcp`，目标机不需要源码和编译环境。
> 只有镜像仓库不可达时才需要下面的手工步骤（`WITTY_RAG_MCP_BUILD=1` 可在本地构建）。

手动部署所用的 RAG MCP 源码依赖 MCP Python SDK 1.x 的 `FastMCP` API，需安装 `mcp<2`。
先将 `RAG_SOURCE_DIR` 设置为 RAG MCP 源码目录，再执行：

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

> 本节手动启动的 MCP 进程不会在容器重启后自动恢复，需要重新执行启动命令。
> 使用部署脚本和预构建 MCP 镜像时，REST 与 MCP 服务由容器入口启动，无需手动恢复。

## 5. 启动 Witty-UB

默认 MCP 地址为：

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

启用现象索引时，`all` 和 `backend` 容器每次启动或重启会先等待 RAG REST 服务，最多
30 秒。RAG 就绪后立即启动应用；超时则记录警告并继续启动，结构化功能不受影响。
现象索引任务会周期性重试，RAG 恢复后继续处理。手动 `docker run` 或 Docker Compose
不包含这一步等待。

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
