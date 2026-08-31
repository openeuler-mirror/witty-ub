# witty-ub 容器化部署

## 概述

容器化部署提供环境一致性、快速部署、易于扩展等优势。**同一镜像通过 `WITTY_ROLE` 支持分离部署**：`WITTY_ROLE=backend` 的后端容器承载数据卷与 FastAPI，无出网要求；`WITTY_ROLE=frontend` 的前端容器承载 Nginx 与 OpenCode，LLM key 与经验库随前端节点。两者可以运行在不同机器上。

> 推荐使用脚本部署 → [宿主机脚本部署](02-script-host.md) | [容器脚本部署](03-script-container.md)。本文档介绍手动 `docker run` 和 `docker compose` 方式。

---

## 前置条件

- Docker 20.10+ 已安装并运行
- PG 数据库已部署 → [05-database.md](05-database.md)
- 至少 4GB 内存、10GB 磁盘空间
- 前端节点：能出网访问 LLM，宿主机 `~/.config/opencode` 已配置 LLM key

### 获取镜像

```bash
# 拉取
docker pull hub-harbor.oepkgs.net/neocopilot/witty-ub:latest

# 本地 tag（简化名称）
docker tag hub-harbor.oepkgs.net/neocopilot/witty-ub:latest witty-ub:latest

# 离线导入
docker load -i witty-ub.tar
```

---

## 分离部署（默认：两台机器）

### 方式一：docker compose（仓库自带示例）

仓库 `docker-compose.yml` 内置 `split` profile，`postgres` + `witty-ub-backend` + `witty-ub-frontend` 三个服务：

```bash
docker compose --profile split up -d
```

| 服务 | 角色 | 说明 |
| ------ | ------ | ------ |
| `witty-ub-backend` | `WITTY_ROLE=backend` | FastAPI + 数据卷（不对外暴露端口） |
| `witty-ub-frontend` | `WITTY_ROLE=frontend` | 32413 → 8080（Nginx + OpenCode），`WITTY_BACKEND_URL` 指向 backend |
| `postgres` | 数据库 | 15432，仅 backend 使用 |

前端容器健康检查经反代探测远端后端 `/health_check`；`depends_on: condition: service_healthy` 保证后端就绪后才启动前端。

**跨机部署**：把两个服务拆到各自机器的 compose 文件中，前端服务的 `WITTY_BACKEND_URL` 改为后端机器地址：

```yaml
# 前端机器的 docker-compose.yml
services:
  witty-ub-frontend:
    image: witty-ub:latest
    ports:
      - "32413:8080"
    volumes:
      - ~/.config/opencode:/root/.config/opencode          # LLM key
      - witty-ub-experience-data:/var/witty-ub/witty_ub_diagnostician/.opencode/skills/experience-skill/data
    environment:
      - WITTY_ROLE=frontend
      - WITTY_BACKEND_URL=http://<后端机器IP>:9772
    networks:
      - witty-ub-network
```

后端机器的 compose 文件中 backend 服务需对前端机器暴露 9772：

```yaml
services:
  witty-ub-backend:
    image: witty-ub:latest
    ports:
      - "9772:9772"        # 对前端机器开放
    volumes:
      - witty-ub-data:/var/witty-ub/data
      - witty-ub-uploads:/var/witty-ub/latency/file/file_upload
      - witty-ub-results:/var/witty-ub/latency/file/file_parse_result
    environment:
      - WITTY_ROLE=backend
      - PG_HOST=<PG地址>
      - PG_PORT=5432
      - PG_DATABASE=witty-ub
      - PG_USER=witty-ub
      - PG_PASSWORD=witty-ub
```

### 方式二：docker run（分角色）

**后端机器**：

```bash
docker network create witty-ub-network
docker volume create witty-ub-data witty-ub-uploads witty-ub-results

docker run -d \
  --name witty-ub-backend \
  --restart unless-stopped \
  -p 9772:9772 \
  -v witty-ub-data:/var/witty-ub/data \
  -v witty-ub-uploads:/var/witty-ub/latency/file/file_upload \
  -v witty-ub-results:/var/witty-ub/latency/file/file_parse_result \
  -e WITTY_ROLE=backend \
  -e PYTHONPATH=/var/witty-ub \
  -e PG_HOST=172.18.0.1 \
  -e PG_PORT=5432 \
  -e PG_DATABASE=witty-ub \
  -e PG_USER=witty-ub \
  -e PG_PASSWORD=witty-ub \
  --network witty-ub-network \
  witty-ub:latest
```

**前端机器**：

```bash
docker run -d \
  --name witty-ub-frontend \
  --restart unless-stopped \
  -p 32413:8080 \
  -v ~/.config/opencode:/root/.config/opencode \
  -v witty-ub-experience-data:/var/witty-ub/witty_ub_diagnostician/.opencode/skills/experience-skill/data \
  -e WITTY_ROLE=frontend \
  -e WITTY_BACKEND_URL=http://<后端机器IP>:9772 \
  witty-ub:latest
```

容器启动时自动完成：envsubst 渲染 Nginx 配置（API 反代 `WITTY_BACKEND_URL`）→ 渲染 Agent 提示词后端基址 → 启动 OpenCode(4096) + Nginx(8080)。

### 验证

```bash
# 后端容器健康
docker inspect --format='{{.State.Health.Status}}' witty-ub-backend   # healthy

# 前端节点（宿主机访问, 如有代理需 --noproxy '*'）
curl http://<前端机器IP>:32413/                 # Web 200
curl http://<前端机器IP>:32413/health_check     # 远端后端经反代 200
curl http://<前端机器IP>:32413/agent-api/doc    # OpenCode 经反代 200
```

### 防火墙（后端机器，仅对前端机器开放）

```bash
firewall-cmd --permanent --add-rich-rule='rule family=ipv4 source address=<前端机器IP>/32 port port=9772 protocol=tcp accept'
firewall-cmd --reload
```

---

## 单机部署（前后端同机）

### docker compose

```yaml
version: '3.8'

services:
  witty-ub:
    image: witty-ub:latest
    container_name: witty-ub
    restart: unless-stopped
    ports:
      - "32412:8080"
    volumes:
      - witty-ub-data:/var/witty-ub/data
      - witty-ub-logs:/var/log/witty-ub
      - witty-ub-uploads:/var/witty-ub/latency/file/file_upload
      - witty-ub-results:/var/witty-ub/latency/file/file_parse_result
      - ~/.config/opencode:/root/.config/opencode
    environment:
      - PYTHONPATH=/var/witty-ub
      - LOG_LEVEL=info
      - PG_HOST=postgres
      - PG_PORT=5432
      - PG_DATABASE=witty-ub
      - PG_USER=witty-ub
      - PG_PASSWORD=witty-ub
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:9772/health_check"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s
    networks:
      - witty-ub-network

volumes:
  witty-ub-data:
  witty-ub-logs:
  witty-ub-uploads:
  witty-ub-results:

networks:
  witty-ub-network:
    driver: bridge
```

```bash
docker compose up -d
docker compose down    # 停止并删除
```

### docker run

```bash
# 创建网络和数据卷
docker network create witty-ub-network
docker volume create witty-ub-data witty-ub-logs witty-ub-uploads witty-ub-results

# 启动容器（默认 WITTY_ROLE=all）
docker run -d \
  --name witty-ub \
  --restart unless-stopped \
  -p 32412:8080 \
  -v witty-ub-data:/var/witty-ub/data \
  -v witty-ub-logs:/var/log/witty-ub \
  -v witty-ub-uploads:/var/witty-ub/latency/file/file_upload \
  -v witty-ub-results:/var/witty-ub/latency/file/file_parse_result \
  -v ~/.config/opencode:/root/.config/opencode \
  -e PYTHONPATH=/var/witty-ub \
  -e LOG_LEVEL=info \
  -e PG_HOST=postgres \
  -e PG_PORT=5432 \
  -e PG_DATABASE=witty-ub \
  -e PG_USER=witty-ub \
  -e PG_PASSWORD=witty-ub \
  --health-cmd="curl -f http://localhost:9772/health_check" \
  --health-interval=30s \
  --health-timeout=10s \
  --health-retries=3 \
  --health-start-period=40s \
  --network witty-ub-network \
  witty-ub:latest
```

> **说明**：若需修改 opencode 配置文件，请在宿主机上操作。部署会将宿主机的 opencode 配置目录（`~/.config/opencode/`）映射到容器中（`/root/.config/opencode/`），在容器内修改不会持久化。详见 [配置参考手册 · OpenCode 配置](../usage/03-configuration-reference.md#opencode-配置)。

---

## PostgreSQL 连接（后端节点）

### 场景一：PG 也是容器（同网络）

```
witty-ub-backend → postgres:5432  （Docker 内部 DNS）
```

确保两个容器在同一 `witty-ub-network` 网络中。

### 场景二：PG 在宿主机（RPM 部署）

```bash
# 获取 Docker 网关 IP
docker network inspect witty-ub-network --format '{{(index .IPAM.Config 0).Gateway}}'
# 典型: 172.18.0.1
```

```bash
docker run -d \
  ... \
  -e PG_HOST=172.18.0.1 \
  -e PG_PORT=15432 \
  ...
```

---

## 数据卷说明

| 卷名 | 容器路径 | 角色 | 用途 |
| ------ | --------- | ------ | ------ |
| `witty-ub-data` | `/var/witty-ub/data` | backend | 故障模式、KVCache |
| `witty-ub-uploads` | `/var/witty-ub/latency/file/file_upload` | backend | 上传文件 |
| `witty-ub-results` | `/var/witty-ub/latency/file/file_parse_result` | backend | 解析结果 |
| `~/.config/opencode` | `/root/.config/opencode` | frontend | LLM key 等配置 |
| `witty-ub-experience-data` | `.../experience-skill/data` | frontend | Agent 经验库（experience.db） |
| `witty-ub-logs` | `/var/log/witty-ub` | 通用 | 应用日志 |

---

## 常用命令

```bash
# 查看状态
docker ps | grep witty-ub

# 查看日志
docker logs -f witty-ub-frontend

# 进入容器
docker exec -it witty-ub-frontend bash

# 启停
docker stop witty-ub-frontend
docker start witty-ub-frontend

# 数据备份
docker run --rm -v witty-ub-data:/data -v $(pwd):/backup alpine tar czf /backup/backup.tar.gz -C /data .
```

---

## 环境变量

| 变量 | 默认值 | 说明 |
| ------ | -------- | ------ |
| `WITTY_ROLE` | `all` | `all` 单机全量 / `backend` 仅后端 / `frontend` 仅前端 |
| `WITTY_BACKEND_URL` | `http://127.0.0.1:9772` | frontend 角色的 API 反代上游，指向后端节点 |
| `WITTY_API_BASE` | 跟随 `WITTY_BACKEND_URL` | Agent 提示词中的后端 API 基址 |
| `WITTY_AGENT_URL` | `http://127.0.0.1:4096` | `/agent-api/` 反代上游 |
| `PG_HOST` | `postgres` | PG 主机（backend 视角） |
| `PG_PORT` | `5432` | PG 端口 |
| `PG_DATABASE` | `witty-ub` | PG 数据库名 |
| `PG_USER` | `witty-ub` | PG 用户名 |
| `PG_PASSWORD` | `witty-ub` | PG 密码 |
| `LOG_LEVEL` | `info` | 日志级别 |

---

## 后续步骤

- 宿主机脚本部署 → [02-script-host.md](02-script-host.md)
- 容器脚本部署 → [03-script-container.md](03-script-container.md)
- 手动数据库部署 → [05-database.md](05-database.md)
