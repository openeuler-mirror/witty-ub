# 配置参考手册

本文档汇总 witty-ub 系统的所有配置项，包括环境变量、端口映射、数据卷、Nginx 配置、OpenCode 配置和 deploy.conf 配置。

---

## 环境变量

### witty-ub 容器环境变量

| 变量名 | 默认值 | 说明 |
| -------- | -------- | ------ |
| `PYTHONPATH` | `/var/witty-ub` | Python 模块搜索路径 |
| `LOG_LEVEL` | `info` | 日志级别（debug/info/warning/error） |
| `PG_HOST` | `postgres` | PostgreSQL 主机地址 |
| `PG_PORT` | `5432` | PostgreSQL 端口 |
| `PG_DATABASE` | `witty-ub` | PostgreSQL 数据库名 |
| `PG_USER` | `witty-ub` | PostgreSQL 用户名 |
| `PG_PASSWORD` | `witty-ub` | PostgreSQL 密码 |

### 前后端分离部署环境变量

> 分离部署（`WITTY_ROLE=backend/frontend`，后端节点与前端节点可不在同一台机器）详见 [架构概览](../deployment/01-overview.md)

| 变量名 | 默认值 | 说明 |
| -------- | -------- | ------ |
| `WITTY_ROLE` | `all` | 容器/部署角色：`all` 单机全量 / `backend` 仅后端 / `frontend` 仅前端 |
| `WITTY_BACKEND_URL` | `http://127.0.0.1:9772` | Nginx API 反代上游（前端节点指向后端节点地址） |
| `WITTY_API_BASE` | 跟随 `WITTY_BACKEND_URL` | Agent 提示词中的后端 API 基址（部署时渲染） |
| `WITTY_NO_PROXY` | `127.0.0.1` | Agent curl `--noproxy` 参数 |
| `WITTY_AGENT_URL` | `http://127.0.0.1:4096` | Nginx `/agent-api/` 反代上游 |
| `OPENCODE_HOST` | `127.0.0.1` | OpenCode 监听地址（OpenCode 留在后端节点时改 `0.0.0.0`） |

### 前端运行时配置（config.json）

前端构建产物目录下的 `config.json` 支持不改构建切换后端（优先级低于 `VITE_*` 构建期环境变量）：

```json
{
  "apiBase": "",
  "agentApiBase": "/agent-api"
}
```

| 字段 | 默认值 | 说明 |
|------|--------|------|
| `apiBase` | `""` | 后端 API 基址；留空 = 同源（经 Nginx 反代），设为 `http://<后端>:9772` 则浏览器直连 |
| `agentApiBase` | `/agent-api` | OpenCode Agent API 基址 |

### PostgreSQL 容器环境变量

| 变量名 | 默认值 | 说明 |
| -------- | -------- | ------ |
| `POSTGRESQL_USER` | `witty-ub` | 数据库用户 |
| `POSTGRESQL_PASSWORD` | `witty-ub` | 数据库密码 |
| `POSTGRESQL_DATABASE` | `witty-ub` | 数据库名称 |
| `POSTGRESQL_SHARED_BUFFERS` | `2GB` | 共享缓冲区大小 |
| `POSTGRESQL_EFFECTIVE_CACHE_SIZE` | `6GB` | 有效缓存大小 |
| `POSTGRESQL_MAX_CONNECTIONS` | `200` | 最大连接数 |

---

## 端口映射

### 前后端分离部署（默认形态）

| 节点 | 服务 | 端口 | 说明 |
| ---- | ---- | ---- | ---- |
| 后端节点 | Latency Plugin API | 9772 | 后端 API 服务（FastAPI，仅对前端节点开放） |
| 后端节点 | PostgreSQL | 5432 / 15432 | 数据库服务（仅本机/后端内部） |
| 前端节点 | Web UI (Nginx) | 8080 / 32413 | Web 界面和 API/Agent 反代 |
| 前端节点 | OpenCode Server | 4096 | AI 诊断服务（仅本机，经 `/agent-api/` 反代） |

### 单机部署端口（前后端同机）

| 服务 | 容器内端口 | 宿主机端口 | 说明 |
| ------ | ----------- | ----------- | ------ |
| Web UI (Nginx) | 8080 | 32412 | Web 界面和 API 代理 |
| Latency Plugin API | 9772 | 9772 | 后端 API 服务（FastAPI） |
| OpenCode Server | 4096 | 4096 | AI 诊断服务 |
| PostgreSQL | 5432 | 15432 | 数据库服务 |

RPM 单机部署：Nginx 8080、FastAPI 9772、OpenCode 4096、PostgreSQL 5432 或 15432（取决于配置）。

---

## 数据卷

### 容器数据卷配置

| 卷名 | 容器路径 | 用途 |
| ------ | --------- | ------ |
| `witty-ub-data` | `/var/witty-ub/data` | 故障模式数据、KVCache、拓扑数据 |
| `witty-ub-logs` | `/var/log/witty-ub` | 应用日志 |
| `witty-ub-uploads` | `/var/witty-ub/latency/file/file_upload` | 上传的日志文件 |
| `witty-ub-results` | `/var/witty-ub/latency/file/file_parse_result` | 解析结果 |
| `~/.config/opencode` | `/root/.config/opencode` | OpenCode 配置目录 |
| `pg15-data` | `/var/lib/pgsql/data` | PostgreSQL 数据目录 |

### 目录结构

```
/var/witty-ub/
├── data/                    # 数据目录
│   ├── failure_mode_tree.json
│   ├── kvcache/
│   ├──urma/
│   └── view-vis/
├── latency/                 # Latency Plugin 代码
├── web/                     # Web 前端文件
├── config/                  # 配置文件
└── log/                     # 日志目录

/var/log/witty-ub/
├── web.log
├── latency.log
└── opencode.log
```

---

## Nginx 配置

### 配置文件位置

- **容器部署**：`/etc/witty-ub/web/nginx.conf`
- **RPM 部署**：`/etc/nginx/conf.d/witty-ub-web.conf`

### 主要配置项

```nginx
server {
    listen 8080;
    server_name _;

    root /var/witty-ub/web;
    index index.html;

    # 前端路由
    location / {
        try_files $uri $uri/ /index.html;
    }

    # API 代理到 Latency Plugin
    location ~ ^/(log_kb|log_file|log_parse_result|aggregated_event|anomalous_event|anomalous_event_chain|log_failure_event_result|failure_mode|task|health_check|docs|openapi.json) {
        proxy_pass http://127.0.0.1:9772;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # OpenCode API 代理
    location /agent-api/ {
        proxy_pass http://127.0.0.1:4096/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

### 日志配置

- **错误日志**：`/var/log/witty-ub-web/error.log`（级别：warn）
- **访问日志**：`/var/log/witty-ub-web/access.log`
- **PID 文件**：`/run/witty-ub-web/nginx.pid`

---

## OpenCode 配置

### 配置文件位置

- **宿主机**：`~/.config/opencode/opencode.jsonc`
- **容器内**：`/root/.config/opencode/opencode.jsonc`

### 配置示例

```jsonc
{
   "$schema": "https://opencode.ai/config.json",
   "provider": {
        "provider-ID": {
            "name": "provider-name",
            "npm": "@ai-sdk/openai-compatible",
            "options": {
                "apiKey": "your-api-key",
                "baseURL": "your-base-url",
                "setCacheKey": true
            },
            "models": {
                "model-name": {
                    "name": "model-name"
                }
            }
        }
    }
}
```

### 启动命令

```bash
# 启动 OpenCode 后台服务
bash /var/witty-ub/latency/deploy/run_opencode.sh
```

### 配置注意事项

> **API-key 仅支持直接修改配置文件时**：如果用户的 API-key 只支持直接修改 opencode 的配置文件（即无法通过前端页面配置），此时无需在前端页面进行配置，直接在本机的 opencode 配置文件（通常是 `~/.config/opencode/opencode.jsonc`）按照 API-key 提供方给出的教程进行配置即可，平台会自动识别大模型。

> **Docker 部署修改 opencode 配置**：docker 部署时，如果需要修改 opencode 配置文件，请在宿主机上进行操作。部署时会将宿主机的 opencode 配置目录（`~/.config/opencode/`）映射到容器中（`/root/.config/opencode/`），在容器内直接修改不会持久化。

---

## deploy.conf 配置

### 数据库连接配置

| 配置项 | 默认值 | 说明 |
| -------- | -------- | ------ |
| `PG_HOST` | `127.0.0.1` | PostgreSQL 主机地址 |
| `PG_PORT` | `15432` | PostgreSQL 宿主机映射端口，Docker 部署使用 |
| `PG_PORT_RPM` | `5432` | PostgreSQL 监听端口，RPM 部署使用 |
| `PG_DATABASE` | `witty-ub` | 数据库名 |
| `PG_USER` | `witty-ub` | 用户名 |
| `PG_PASSWORD` | `witty-ub` | 密码 |
| `PG_POOL_SIZE` | `10` | 连接池大小 |
| `PG_MAX_OVERFLOW` | `20` | 连接池最大溢出数 |

### PG_HOST 场景说明

| 场景 | PG_HOST | PG_PORT | 说明 |
| ------ | --------- | --------- | ------ |
| 源码部署，宿主机访问 | `127.0.0.1` | `15432` | 部署脚本、本地开发 |
| RPM 部署，宿主机访问 | `127.0.0.1` | `5432` | `PG_PORT_RPM` 默认值 |
| 容器访问宿主机 RPM PG | `172.18.0.1` | `5432` | Docker 网络网关 |
| 容器访问 PG 容器 | `postgres` | `5432` | Docker 网络 DNS |

### PostgreSQL 性能调优参数

以下参数留空时由部署脚本根据宿主机内存自动计算：

| 配置项 | 说明 | 推荐值（8GB 内存） |
| -------- | ------ | ------------------- |
| `PG_SHARED_BUFFERS` | 共享缓冲区 | `2GB`（物理内存 25%） |
| `PG_EFFECTIVE_CACHE_SIZE` | 优化器缓存 | `6GB`（物理内存 50%-75%） |
| `PG_WORK_MEM` | 排序/哈希内存 | `64MB` |
| `PG_MAINTENANCE_WORK_MEM` | 维护操作内存 | `512MB` |
| `PG_WAL_BUFFERS` | WAL 缓冲区 | `64MB` |
| `PG_MAX_WAL_SIZE` | 最大 WAL 体积 | `4GB` |
| `PG_CHECKPOINT_COMPLETION_TARGET` | checkpoint 分散度 | `0.9` |
| `PG_RANDOM_PAGE_COST` | 随机页成本 | `1.1`（SSD）/ `4.0`（HDD） |
| `PG_EFFECTIVE_IO_CONCURRENCY` | 并发 IO 数 | `200`（SSD）/ `2`（HDD） |
| `PG_MAX_CONNECTIONS` | 最大连接数 | `200` |

### Docker 部署专用配置

| 配置项 | 默认值 | 说明 |
| -------- | -------- | ------ |
| `PG_CONTAINER_NAME` | `postgres` | PostgreSQL 容器名称 |
| `PG_IMAGE` | `quay.io/sclorg/postgresql-15-c9s:latest` | PostgreSQL 镜像 |
| `PG_NETWORK` | `witty-ub-network` | Docker 网络名称 |
| `PG_VOLUME` | `pg15-data` | 数据卷名称 |
| `PG_CONTAINER_DATA_DIR` | `/var/lib/pgsql/data` | 容器内数据目录 |

### witty-ub 容器部署专用配置

| 配置项 | 默认值 | 说明 |
| -------- | -------- | ------ |
| `WITTY_CONTAINER_NAME` | `witty-ub` | witty-ub 容器名称 |
| `WITTY_IMAGE` | （自动选择） | witty-ub 镜像 |
| `WITTY_HOST_PORT` | `32412` | 宿主机端口 |
| `WITTY_LOG_LEVEL` | `info` | 日志级别 |
| `OPENCODE_CONFIG_DIR` | `${HOME}/.config/opencode` | OpenCode 配置目录 |
| `WITTY_EXTRA_MOUNTS` | `/home:/home:ro` | 额外目录挂载 |

### RPM 部署专用配置

| 配置项 | 默认值 | 说明 |
|--------|--------|------|
| `PG_DATA_DIR` | （自动探测） | PostgreSQL 数据目录 |
| `PG_SERVICE_NAME` | （自动探测） | PostgreSQL 服务名 |

---

## 健康检查配置

### PostgreSQL 健康检查

```yaml
test: ["CMD", "pg_isready", "-U", "postgres", "-d", "witty-ub"]
interval: 30s
timeout: 10s
retries: 3
start_period: 40s
```

### witty-ub 健康检查

```yaml
test: ["CMD", "curl", "-f", "http://localhost:9772/health_check"]
interval: 30s
timeout: 10s
retries: 3
start_period: 40s
```

---

## 相关文档

- 平台操作指南 → [01-platform-guide.md](01-platform-guide.md)
- 数据采集工具 → [02-data-collection-guide.md](02-data-collection-guide.md)
- 部署指南 → [../deployment/01-overview.md](../deployment/01-overview.md)
