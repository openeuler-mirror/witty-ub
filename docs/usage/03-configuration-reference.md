# 配置参考手册

本文档汇总 witty-ub 系统的所有配置项，包括环境变量、端口映射、数据卷、Nginx 配置、OpenCode 配置和 deploy.conf 配置。

> **PG 密码**：`deploy.conf` 中 `PG_PASSWORD` 仅为 `<CHANGE_ME>` 占位符，实际口令存放在独立密钥文件：源码 host 部署为 `deploy/pg.passwd`（0400），容器化 PG 为 `/etc/witty-ub/pg.passwd`（0440，容器内 postgres 需组可读），RPM 包部署为 `/etc/witty-ub/pg.passwd`（0600）。口令不写入运行时 TOML，由启动器/容器入口在启动后端时读入进程环境；Docker 使用 `/run/secrets/pg_password` 只读挂载。

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
| `PG_PASSWORD` | （进程启动时注入） | PostgreSQL 密码；容器入口从 `/run/secrets/pg_password` 读取，不写入容器配置 |

### 前后端分离部署环境变量

> 分离部署（`WITTY_ROLE=backend/frontend`，后端节点与前端节点可不在同一台机器）详见 [架构概览](../deployment/01-overview.md)

| 变量名 | 默认值 | 说明 |
| -------- | -------- | ------ |
| `WITTY_ROLE` | `all` | 容器/部署角色：`all` 单机全量 / `backend` 仅后端 / `frontend` 仅前端 |
| `WITTY_BACKEND_URL` | `http://127.0.0.1:9772` | Nginx API 反代上游（前端节点指向后端节点地址） |
| `WITTY_API_BASE` | 跟随 `WITTY_BACKEND_URL` | Agent Bash 执行时展开的后端 API 基址（提示词保持原文） |
| `WITTY_NO_PROXY` | `127.0.0.1` | Agent curl `--noproxy` 参数 |
| `WITTY_AGENT_URL` | `http://127.0.0.1:4096` | Nginx `/agent-api/` 反代上游 |
| `WITTY_CORS_ORIGINS` | 空 | FastAPI 允许的跨域前端源，多个源用逗号分隔；经 Nginx 同源反代时无需设置 |
| `OPENCODE_HOST` | `127.0.0.1` | OpenCode 监听地址（OpenCode 留在后端节点时改 `0.0.0.0`） |

仅当前端浏览器直接访问后端 `9772` 端口时需要设置 `WITTY_CORS_ORIGINS`。源必须包含协议、主机和端口，可在前端页面的浏览器控制台执行 `window.location.origin` 获取，例如：

```bash
export WITTY_CORS_ORIGINS="https://witty.example.com,http://192.168.1.10:5173"
```

### 前端运行时配置（config.json）

前端构建产物目录下的 `config.json` 支持不改构建切换后端（优先级低于 `VITE_*` 构建期环境变量）：

```json
{
  "apiBase": "",
  "agentApiBase": "/agent-api"
}
```

- `apiBase`（默认 `""`）：后端 API 基址；留空 = 同源（经 Nginx 反代），设为 `http://<后端>:9772` 则浏览器直连
- `agentApiBase`（默认 `/agent-api`）：OpenCode Agent API 基址

### PostgreSQL 容器环境变量

| 变量名 | 默认值 | 说明 |
| -------- | -------- | ------ |
| `POSTGRESQL_USER` | `witty-ub` | 数据库用户 |
| `POSTGRESQL_PASSWORD` | （见密钥文件） | 数据库密码；由部署脚本从 `pg.passwd` 密钥文件读取后注入 PG 容器 |
| `POSTGRESQL_DATABASE` | `witty-ub` | 数据库名称 |

---

## 端口映射

### 前后端分离部署（默认形态）

| 节点 | 服务 | 端口 | 说明 |
| ---- | ---- | ---- | ---- |
| 后端节点 | Latency Plugin API | 9772 | 后端 API 服务（FastAPI，仅对前端节点开放） |
| 后端节点 | PostgreSQL | 5432 | 数据库服务（仅本机/后端内部；Docker 可映射为宿主机 15432） |
| 前端节点 | Web UI (Nginx) | 8080 / 32413 | Web 界面和 API/Agent 反代 |
| 前端节点 | OpenCode Server | 4096 | AI 诊断服务（仅本机，经 `/agent-api/` 反代） |

### 单机部署端口（前后端同机）

| 服务 | 容器内端口 | 宿主机端口 | 说明 |
| ------ | ----------- | ----------- | ------ |
| Web UI (Nginx) | 8080 | 32412 | Web 界面和 API/Agent 代理（对外唯一入口） |
| Latency Plugin API | 9772 | 不发布 | 仅容器内，经 Nginx 按路径前缀（`/health_check`、`/log_file` 等）反代 |
| OpenCode Server | 4096 | 不发布 | 仅容器内，经 Nginx `/agent-api/` 反代 |
| PostgreSQL | 5432 | 15432 | 数据库服务（`PG_PORT`） |

> 需要从宿主机直接访问 API/OpenCode 时（排查用），可 `docker exec -it witty-ub curl --noproxy 127.0.0.1 http://127.0.0.1:9772/health_check`，或自行在 `docker run`/compose 中追加 `-p`。

RPM 单机部署：Nginx 8080、FastAPI 9772、OpenCode 4096、PostgreSQL 5432。

---

## 数据卷

### 容器数据卷配置

| 卷名 | 类型 | 容器路径 | 用途 |
| ------ | ------ | --------- | ------ |
| `witty-ub-data` | 命名卷 | `/var/witty-ub/data` | 故障模式数据、KVCache、拓扑数据 |
| `witty-ub-logs` | 命名卷 | `/var/log/witty-ub` | 应用日志 |
| `witty-ub-uploads` | 命名卷 | `/var/witty-ub/latency/file/file_upload` | 上传的日志文件 |
| `witty-ub-results` | 命名卷 | `/var/witty-ub/latency/file/file_parse_result` | 解析结果 |
| `witty-ub-experience-data` | 命名卷 | `…/skills/experience-skill/data` | Agent 经验库 `experience.db` |
| `~/.config/opencode` | bind mount | `/root/.config/opencode` | OpenCode 配置目录 |
| `pg15-data` | 命名卷 | `/var/lib/pgsql/data` | PostgreSQL 数据目录 |

### 目录结构

```text
/var/witty-ub/
├── data/                    # 数据目录
│   ├── failure_mode_tree.json
│   ├── kvcache/
│   ├── ubsocket/
│   ├── umq/
│   ├── urma/
│   └── view-vis/
├── latency/                 # Latency Plugin 代码
├── web/                     # Web 前端文件
├── config/                  # 配置文件
├── deploy/                  # deploy_opencode.sh
└── witty_ub_diagnostician/  # Agent bundle

/var/log/witty-ub/
├── latency_server.log       # FastAPI 后端日志
└── opencode_server.log      # OpenCode 日志

/var/log/witty-ub-web/
├── access.log
└── error.log
```

---

## Nginx 配置

### 配置文件位置

- **容器部署**：`/etc/witty-ub/web/nginx.conf`
- **RPM 部署**：`/etc/witty-ub/web/nginx.conf`

### 模板与渲染

- 模板：`packaging/nginx/witty-ub-web.conf.template`
- 占位符：`${WITTY_BACKEND_URL}`、`${WITTY_AGENT_URL}`
- 渲染：容器 entrypoint（`envsubst`）、RPM `manager.sh`（`sed`）、源码 `deploy/host/deploy.sh`（`envsubst`）

> 反代路径前缀、上传缓冲与 `/agent-api/` 转发规则以模板为准；改后端地址用
> `WITTY_BACKEND_URL`（容器/源码）或 `witty-ub manager config --backend <url>`（RPM）。

### 日志配置

- **错误日志**：`/var/log/witty-ub-web/error.log`（级别：warn）
- **访问日志**：`/var/log/witty-ub-web/access.log`
- **PID 文件**：`/run/witty-ub-web/nginx.pid`

---

## OpenCode 配置

### 配置文件位置（OpenCode）

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

### 随包 Agent 与 Skills

随包 bundle 提供 `witty-ub-diagnostician` 诊断 Agent 与诊断 Skills（latency-analysis、failure-code-analysis、brpc-diagnosis、diagnostic-report-generation、experience-skill），OpenCode 启动时经 `OPENCODE_CONFIG_DIR` 注入：

| 部署形态 | bundle 位置 |
| -------- | ----------- |
| 源码 | `<仓库>/witty_ub_diagnostician/` |
| 容器 | `/var/witty-ub/witty_ub_diagnostician/.opencode/` |
| RPM | `/var/witty-ub/config/` |

与用户配置的合并关系：

- `~/.config/opencode/` 下的用户配置、模型与 Skills 始终生效；bundle 的 agents/skills 与其合并，同名项以 bundle 为准
- 环境变量 `OPENCODE_CONFIG` / `OPENCODE_CONFIG_DIR` 已设置时使用用户值，脚本不覆盖
- 自定义 Skills 放 `~/.config/opencode/skills/<名称>/SKILL.md` 即可被诊断 Agent 使用

### 启动命令

```bash
# 启动 OpenCode 后台服务
bash /var/witty-ub/deploy/deploy_opencode.sh
```

### 配置注意事项

> **API-key 仅支持直接修改配置文件时**：如果用户的 API-key 只支持直接修改 opencode 的配置文件（即无法通过前端页面配置），此时无需在前端页面进行配置，直接在本机的 opencode 配置文件（通常是 `~/.config/opencode/opencode.jsonc`）按照 API-key 提供方给出的教程进行配置即可，平台会自动识别大模型。
>
> **Docker 部署修改 opencode 配置**：docker 部署时，如果需要修改 opencode 配置文件，请在宿主机上进行操作。部署时会将宿主机的 opencode 配置目录（`~/.config/opencode/`）映射到容器中（`/root/.config/opencode/`），在容器内直接修改不会持久化。

---

## deploy.conf 配置

### 数据库连接配置

| 配置项 | 默认值 | 说明 |
| -------- | -------- | ------ |
| `PG_HOST` | `127.0.0.1` | PostgreSQL 主机地址 |
| `PG_PORT` | `15432` | PG 容器的宿主机映射端口，只影响宿主机侧客户端 |
| `PG_HOST_IN_CONTAINER` | 空 | 应用容器内看到的 PG 地址，留空自动探测 |
| `PG_PORT_IN_CONTAINER` | 空 | 应用容器内看到的 PG 端口，留空自动探测 |
| `PG_PORT_RPM` | `5432` | PostgreSQL 监听端口，源码/RPM 部署使用 |
| `PG_DATABASE` | `witty-ub` | 数据库名 |
| `PG_USER` | `witty-ub` | 用户名 |
| `PG_PASSWORD` | `<CHANGE_ME>` | 密码占位符；实际口令存于密钥文件 `pg.passwd`（源码 host: `deploy/pg.passwd`，Docker/RPM: `/etc/witty-ub/pg.passwd`），不回写本文件 |
| `PG_POOL_SIZE` | `10` | 连接池大小，部署脚本不注入；应用读取 `config/diagnosis_config.toml` 的 `[db]` |
| `PG_MAX_OVERFLOW` | `20` | 连接池最大溢出数，同上 |

### PG_HOST 场景说明

| 场景 | PG_HOST | PG_PORT | 说明 |
| ------ | --------- | --------- | ------ |
| 源码部署，宿主机访问 | `127.0.0.1` | `5432` | `PG_PORT_RPM` 默认值 |
| RPM 部署，宿主机访问 | `127.0.0.1` | `5432` | `PG_PORT_RPM` 默认值 |
| 容器访问宿主机 RPM PG | `172.18.0.1` | `5432` | Docker 网络网关 |
| 容器访问 PG 容器 | `postgres` | `5432` | Docker 网络 DNS |

### Docker 部署专用配置

| 配置项 | 默认值 | 说明 |
| -------- | -------- | ------ |
| `PG_CONTAINER_NAME` | `postgres` | PostgreSQL 容器名称 |
| `PG_IMAGE` | `quay.io/sclorg/postgresql-15-c9s:latest` | PostgreSQL 镜像；部署入口从只读 secret mount 加载密码 |
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

- `PG_DATA_DIR`（自动探测）：PostgreSQL 数据目录
- `PG_SERVICE_NAME`（自动探测）：PostgreSQL 服务名

---

## 健康检查配置

### PostgreSQL 健康检查

```yaml
test: ["CMD", "pg_isready", "-U", "witty-ub", "-d", "witty-ub"]
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
