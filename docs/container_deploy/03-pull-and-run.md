# 3. 镜像拉取、启动与使用

> 返回 [首页](Home.md)

## 拉取镜像

### 从镜像仓库拉取

```bash
# 拉取最新版本
docker pull <registry-url>/witty-ub:latest

# 例如：
docker pull hub-harbor.oepkgs.net/neocopilot/witty-ub:latest

# 拉取指定架构镜像
docker pull <registry-url>/witty-ub-x86_64:latest
docker pull <registry-url>/witty-ub-aarch64:latest
```

### 从 tar 包加载

```bash
# 加载镜像
docker load -i witty-ub.tar

# 加载压缩的镜像
gunzip -c witty-ub.tar.gz | docker load
```

### 验证镜像

```bash
docker images | grep witty-ub
```

---

## 启动容器

### 使用 docker compose 启动（推荐）

**步骤 1**：创建工作目录

```bash
mkdir -p witty-ub && cd witty-ub
```

**步骤 2**：创建 `docker-compose.yml` 文件

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
      - /home/tsn/jingpai:/home/tsn/jingpai:ro
    environment:
      - PYTHONPATH=/var/witty-ub
      - LOG_LEVEL=info
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
    driver: local
  witty-ub-logs:
    driver: local
  witty-ub-uploads:
    driver: local
  witty-ub-results:
    driver: local

networks:
  witty-ub-network:
    driver: bridge
```

**启动命令**：

```bash
# 后台启动
docker compose up -d

# 前台启动（查看实时日志）
docker compose up

# 指定配置文件
docker compose -f docker-compose.yml up -d

# 重新构建并启动
docker compose up -d --build
```

### 使用纯 Docker 命令启动（完整配置，低版本 Docker）

```bash
# 创建网络（首次启动时执行）
docker network create witty-ub-network

# 创建数据卷（首次启动时执行）
docker volume create witty-ub-data
docker volume create witty-ub-logs
docker volume create witty-ub-uploads
docker volume create witty-ub-results

# 启动容器（完整配置）
docker run -d \
  --name witty-ub \
  --restart unless-stopped \
  -p 32412:8080 \
  -v witty-ub-data:/var/witty-ub/data \
  -v witty-ub-logs:/var/log/witty-ub \
  -v witty-ub-uploads:/var/witty-ub/latency/file/file_upload \
  -v witty-ub-results:/var/witty-ub/latency/file/file_parse_result \
  -v /to/path/log:/to/path/log:ro \
  -e PYTHONPATH=/var/witty-ub \
  -e LOG_LEVEL=info \
  --health-cmd="curl -f http://localhost:9772/health_check" \
  --health-interval=30s \
  --health-timeout=10s \
  --health-retries=3 \
  --health-start-period=40s \
  --network witty-ub-network \
  witty-ub:latest
```

### 启动参数说明

| 参数 | 说明 |
|------|------|
| `-d` | 后台运行 |
| `--name witty-ub` | 指定容器名称 |
| `-p 32412:8080` | 端口映射（宿主机:容器） |
| `-v /host/path:/container/path` | 挂载宿主机目录 |
| `--restart always` | 自动重启 |

### 使用 docker run 启动（临时测试）

```bash
docker run -d \
  --name witty-ub \
  -p 32412:8080 \
  -v /to/path/log:/to/path/log:ro \
  witty-ub:latest
```

---

## 配置说明

修改配置后需要重启容器:

```bash
docker compose restart
```

### 环境变量

在 `docker-compose.yml` 中配置环境变量:

```yaml
environment:
  - PYTHONPATH=/var/witty-ub
  - LOG_LEVEL=info  # 可选: debug, info, warning, error
```
### 文件名匹配格式 配置

```bash
mkdir -p config

docker cp witty-ub:/var/witty-ub/config/filepath_config.json ./config/
```

```yaml
volumes:
  - ./config/filepath_config.json:/var/witty-ub/config/filepath_config.json:ro
```

### Latency Plugin 配置

配置文件位于: `/var/witty-ub/config/latency/latency_config.toml`

```toml
[DS_LOG_ANALYZER]
TOTAL_P99_THRESHOLD_MS = 2.0
C2W_P99_THRESHOLD_MS = 2.0
W2W_P99_THRESHOLD_MS = 1.5
```

### Nginx 配置

容器优化的 Nginx 配置文件位于: `docker/nginx.conf`

主要配置项:
- Web UI 端口: 8080 (容器内部)
- API 代理: 转发到 127.0.0.1:9772
- 静态文件目录: `/var/witty-ub/web`

**端口映射**: 通过 `docker-compose.yml` 配置宿主机端口映射到容器内 8080:

```yaml
ports:
  - "32412:8080"  # 外部访问端口
```

**修改外部端口**: 只需修改 `docker-compose.yml` 中的宿主机端口（前面的数字），容器内部端口无需改动。

---

## 数据持久化

### Docker Volumes

容器使用以下卷来持久化数据:

| 卷名称 | 用途 | 路径 |
|--------|------|------|
| `witty-ub-data` | 故障模式数据、KVCache 数据 | `/var/witty-ub/data` |
| `witty-ub-logs` | 应用日志 | `/var/log/witty-ub` |
| `witty-ub-uploads` | 上传的文件 | `/var/witty-ub/latency/file/file_upload` |
| `witty-ub-results` | 解析结果 | `/var/witty-ub/latency/file/file_parse_result` |

### 查看卷数据

```bash
# 列出所有卷
docker volume ls | grep witty-ub

# 查看卷详情
docker volume inspect witty-ub_witty-ub-data

# 挂载卷查看内容
docker run --rm -it -v witty-ub_witty-ub-data:/data alpine ls /data
```

### 使用宿主机目录（可选）

如果需要直接使用宿主机目录，修改 `docker-compose.yml`:

```yaml
volumes:
  - /path/to/your/data:/var/witty-ub/data
  - /path/to/your/logs:/var/log/witty-ub
  - /path/to/your/uploads:/var/witty-ub/latency/file/file_upload
  - /path/to/your/results:/var/witty-ub/latency/file/file_parse_result
```

### 数据备份

```bash
# 备份数据卷
docker run --rm \
  -v witty-ub_witty-ub-data:/data \
  -v $(pwd):/backup \
  alpine tar czf /backup/witty-ub-data-backup.tar.gz -C /data .

# 恢复数据卷
docker run --rm \
  -v witty-ub_witty-ub-data:/data \
  -v $(pwd):/backup \
  alpine tar xzf /backup/witty-ub-data-backup.tar.gz -C /data
```

---

## 验证部署

### 检查容器状态

```bash
docker compose ps

# 预期输出:
# NAME         STATUS         PORTS
# witty-ub     Up (healthy)   0.0.0.0:32412->8080/tcp
```

### 查看日志

```bash
# 查看所有日志
docker compose logs

# 实时查看日志
docker compose logs -f

# 查看最近 100 行
docker compose logs --tail=100
```

### 使用纯 Docker 命令验证部署（低版本 Docker）

```bash
# 检查容器状态
docker ps

# 预期输出:
# CONTAINER ID   IMAGE            COMMAND                  CREATED         STATUS                   PORTS                    NAMES
# abc123456789   witty-ub:latest  "/var/witty-ub/entry..."   5 minutes ago   Up 5 minutes (healthy)   0.0.0.0:32412->8080/tcp  witty-ub

# 查看容器日志
docker logs witty-ub

# 实时查看日志
docker logs -f witty-ub

# 查看最近 100 行
docker logs --tail=100 witty-ub

# 查看健康检查状态
docker inspect --format='{{.State.Health.Status}}' witty-ub

# 查看端口映射
docker port witty-ub
```

### 测试服务

```bash
# 测试 Web UI
curl -I http://localhost:32412

# 测试 API（通过 Nginx 反向代理）
curl http://localhost:32412/health_check

# 测试 C++ 工具
docker exec witty-ub witty-ub-log --help
docker exec witty-ub witty-ub-topo --help
docker exec witty-ub witty-ub-diag-tool --help
```

---

## 访问服务

- **Web UI**: http://localhost:32412
- **API**: http://localhost:32412/health_check
- **API 文档**: http://localhost:32412/docs

**远程访问**: 将 `localhost` 替换为服务器 IP 地址，如 `http://服务器IP:32412`

---

## Docker Compose 常用命令

```bash
# 启动服务
docker compose up -d

# 停止服务
docker compose stop

# 停止并删除容器
docker compose down

# 停止、删除容器并删除卷
docker compose down -v

# 重新构建并启动
docker compose up -d --build

# 查看服务状态
docker compose ps

# 查看日志
docker compose logs -f

# 重启服务
docker compose restart

# 进入容器
docker compose exec -it witty-ub bash
```

---

## Docker 常用命令

```bash
# 查看容器
docker ps
docker ps -a

# 进入容器
docker exec -it witty-ub /bin/bash

# 查看容器详情
docker inspect witty-ub

# 查看容器资源使用
docker stats witty-ub

# 停止/启动容器
docker stop witty-ub
docker start witty-ub

# 删除容器
docker rm witty-ub

# 查看镜像
docker images

# 删除镜像
docker rmi <image-id>
```

---

## 端口说明

| 端口 | 协议 | 用途 | 访问方式 |
|------|------|------|----------|
| 32412 | TCP | Web UI (Nginx + API代理) | http://localhost:32412 |
| 8080 | TCP | Nginx (容器内部) | 不直接访问 |
| 9772 | TCP | FastAPI (容器内部) | 通过 Nginx 代理访问 |

**端口映射关系**:
- 宿主机 `32412` → 容器 `8080` (Nginx)
- Nginx 内部代理 → 容器 `9772` (FastAPI)

---

## 下一步

- 继续阅读: [4. 故障排查](04-troubleshooting.md)
- 返回 [首页](Home.md)
