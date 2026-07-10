<!-- Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved. -->
<!-- witty-ub is licensed under the Mulan PSL v2. -->

# 3. 镜像拉取、启动与使用

> 返回 [首页](Home.md)

## 拉取镜像

### 方法一：从镜像仓库拉取

```bash
# 拉取官方多架构镜像（自动匹配宿主机架构）
docker pull hub-harbor.oepkgs.net/neocopilot/witty-ub:latest

# 拉取私有镜像
docker pull <registry-url>/witty-ub:latest
```

> **说明：** `witty-ub:latest` 是多架构 manifest list，Docker 会自动选择匹配宿主机架构的镜像层。架构特定标签（如 `witty-ub-x86_64:latest`、`witty-ub-aarch64:latest`）需手动构建并推送，详情参见 [02-build-and-package.md](02-build-and-package.md)。

### 方法二：从离线 tar 包加载

```bash
# 加载镜像
docker load -i witty-ub.tar

# 加载压缩的镜像
gunzip -c witty-ub.tar.gz | docker load
```

## 验证镜像

```bash
docker images | grep witty-ub
```

**预期输出**：

```bash
# 从仓库拉取的镜像（完整路径）
hub-harbor.oepkgs.net/neocopilot/witty-ub    latest    1c0ca38d7cf9    14 minutes ago    1.81GB

# 本地构建的镜像（简洁名称）
witty-ub    latest    abc123def456    5 minutes ago    1.81GB
```

> **镜像名称说明**：
> - 从远程仓库拉取的镜像会保留完整的 registry 路径作为镜像名（如 `hub-harbor.oepkgs.net/neocopilot/witty-ub:latest`）
> - 本地构建的镜像使用简洁名称（如 `witty-ub:latest`）
> - 如需使用简洁名称，可以为镜像打本地 tag：
>   ```bash
>   docker tag hub-harbor.oepkgs.net/neocopilot/witty-ub:latest witty-ub:latest
>   ```

---

## 启动容器

### 启动参数说明

| 参数 | 说明 |
|------|------|
| `-d` | 后台运行 |
| `--name witty-ub` | 指定容器名称 |
| `-p 32412:8080` | 端口映射（宿主机:容器） |
| `-v /host/path:/container/path` | 挂载宿主机目录 |
| `--restart always` | 自动重启 |

**说明：**
- `/host/path:/container/path:ro` 表示只读挂载，容器只能读取日志文件，不能写入，在容器中输入'/container/path/'等价于访问'/host/path/'目录。
- 端口映射中的宿主机端口号取决于当前宿主机开放端口设置，建议使用未被占用的端口号，例如`-p 32412:8080`。

### 方法一：使用 docker compose 启动（推荐）

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
      - /to/path/log:/to/path/log:ro
      - ~/.config/opencode:/root/.config/opencode
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

### 方法二：使用纯 Docker 命令启动（完整配置，低版本 Docker）

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
  -v ~/.config/opencode:/root/.config/opencode \
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

### 方法三：使用 docker run 启动（临时测试）

```bash
docker run -d \
  --name witty-ub \
  -p 32412:8080 \
  -v /to/path/log:/to/path/log:ro \
  witty-ub:latest
```

---

## 启动Web UI

**访问 Web UI**:

- 访问 `http://localhost:32412` 即可访问 Web UI。
- 或者访问 `http://<宿主机IP>:32412/` 即可访问 Web UI。

## 配置opencode

目前opencode默认使用宿主机的~/.config/opencode目录。
若需调整opencode的配置，则直接修改宿主机的~/.config/opencode/下的配置即可。

**opencode.json配置LLM参考**
```
{
  "$schema": "https://opencode.ai/config.json",
  "provider": {
    "my-provider": {
      "options": {
        "apiKey": "sk-xxxxx"
      }
    },
    "models": {
        "model_name": {
          "name": "my model",
          "options": {
            "thinking": {
              "type": "disabled"
            },
            "temperature": 0.3,
            "topP": 0.7
          }
        }  
      }
  },
  "model":"my-provider/model_name"
}
```

## 容器配置说明

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

### 统一配置

配置文件位于: `/var/witty-ub/config/diagnosis_config.json`

```json
{
  "log_analyzer_params": {
    "total_p99_threshold_ms": 2.0,
    "c2w_p99_threshold_ms": 2.0,
    "w2w_p99_threshold_ms": 1.5
  }
}
```

### Nginx 配置

容器优化的 Nginx 配置文件位于: `docker/nginx.conf`

主要配置项:
- Web UI 端口: 8080 (容器内部)
- API 代理: 转发到 127.0.0.1:9772
- OpenCode 代理: 转发到 127.0.0.1:4096
- 静态文件目录: `/var/witty-ub/web`

**端口映射**: 通过 `docker-compose.yml` 配置宿主机端口映射到容器内 8080:

```yaml
ports:
  - "32412:8080"  # 外部访问端口
```

**修改外部端口**: 只需修改 `docker-compose.yml` 中的宿主机端口（前面的数字），容器内部端口无需改动。

### OpenCode 配置

OpenCode 是 AI 辅助诊断服务，需要挂载宿主机的配置目录。

**配置目录挂载**:

```yaml
volumes:
  - ~/.config/opencode:/root/.config/opencode
```

**配置目录结构**:

```
~/.config/opencode/
├── config.yaml          # OpenCode 主配置文件
└── agents/              # 自定义 agent 目录
    └── witty-ub-diagnostician.md  # 故障诊断 agent
```

**WITTY_DIR 环境变量**:

容器启动时会自动设置 `WITTY_DIR=/var/witty-ub/config`，OpenCode 通过此环境变量解析配置文件中的路径引用。

**OpenCode 服务配置**:

OpenCode 服务启动参数:
- 配置文件: `OPENCODE_CONFIG=/var/witty-ub/config/opencode.json`
- 工作目录: `/var/witty-ub/latency`
- 日志级别: `DEBUG`

**访问 OpenCode**:

通过 Nginx 反向代理访问:
- OpenCode API: http://localhost:32412/opencode/
- OpenCode WebUI: http://localhost:32412/opencode/webui/

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
| `~/.config/opencode` | OpenCode 配置文件（绑定挂载） | `/root/.config/opencode` |

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
- **OpenCode**: http://localhost:32412/opencode/

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
| 4096 | TCP | OpenCode (容器内部) | 通过 Nginx 代理访问 |

**端口映射关系**:
- 宿主机 `32412` → 容器 `8080` (Nginx)
- Nginx 内部代理 → 容器 `9772` (FastAPI)
- Nginx 内部代理 → 容器 `4096` (OpenCode)

---

## 下一步

- 继续阅读: [4. 故障排查](04-troubleshooting.md)
- 返回 [首页](Home.md)
