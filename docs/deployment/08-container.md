# witty-ub 容器化部署

## 概述

容器化部署提供环境一致性、快速部署、易于扩展等优势。

> 推荐使用脚本部署 → [宿主机脚本部署](02-script-host.md) | [容器脚本部署](03-script-container.md)。本文档介绍手动 `docker run` 和 `docker compose` 方式。

---

## 前置条件

- Docker 20.10+ 已安装并运行
- PG 数据库已部署 → [05-database.md](05-database.md)
- 至少 4GB 内存、10GB 磁盘空间

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

## 方式一：docker compose

创建 `docker-compose.yml`：

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

---

## 方式二：docker run

```bash
# 创建网络和数据卷
docker network create witty-ub-network
docker volume create witty-ub-data witty-ub-logs witty-ub-uploads witty-ub-results

# 启动容器
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

---

## PostgreSQL 连接

### 场景一：PG 也是容器（同网络）

```
witty-ub → postgres:5432  （Docker 内部 DNS）
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

| 卷名 | 容器路径 | 用途 |
|------|---------|------|
| `witty-ub-data` | `/var/witty-ub/data` | 故障模式、KVCache |
| `witty-ub-logs` | `/var/log/witty-ub` | 应用日志 |
| `witty-ub-uploads` | `/var/witty-ub/latency/file/file_upload` | 上传文件 |
| `witty-ub-results` | `/var/witty-ub/latency/file/file_parse_result` | 解析结果 |

---

## 常用命令

```bash
# 查看状态
docker ps | grep witty-ub

# 查看日志
docker logs -f witty-ub

# 进入容器
docker exec -it witty-ub bash

# 启停
docker stop witty-ub
docker start witty-ub
docker restart witty-ub

# 数据备份
docker run --rm -v witty-ub-data:/data -v $(pwd):/backup alpine tar czf /backup/backup.tar.gz -C /data .
```

---

## 验证

```bash
# 健康检查
docker inspect --format='{{.State.Health.Status}}' witty-ub
# 预期: healthy

# 测试 API
curl http://localhost:32412/health_check
```

浏览器访问：`http://localhost:32412`

---

## 环境变量

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `PG_HOST` | `postgres` | PG 主机（容器内视角） |
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
