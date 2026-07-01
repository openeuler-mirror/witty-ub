# Witty-UB 容器化部署指南

## 目录

- [概述](#概述)
- [环境要求](#环境要求)
- [快速开始](#快速开始)
- [详细部署步骤](#详细部署步骤)
- [配置说明](#配置说明)
- [数据持久化](#数据持久化)
- [日志管理](#日志管理)
- [故障排查](#故障排查)
- [多架构构建](#多架构构建)
- [生产环境建议](#生产环境建议)
- [从 RPM 迁移到容器化](#从-rpm-迁移到容器化)

---

## 概述

Witty-UB 是一个用于 Lingqu(UB) 架构 SuperPod 故障定位的工具。本文档介绍如何使用 Docker 容器化方式部署 Witty-UB，替代传统的 RPM 包部署方式。

### 容器化优势

- **环境一致性**: 一次构建，到处运行，消除环境差异
- **快速部署**: 一条命令即可启动所有服务
- **易于扩展**: 支持水平扩展和负载均衡
- **资源隔离**: 容器级别隔离，不影响宿主机
- **版本管理**: 镜像版本控制，支持快速回滚
- **依赖缓存**: 分离依赖镜像和应用镜像，源码改动后快速重建

### 架构说明

容器内包含以下组件:

```
┌─────────────────────────────────────────┐
│           Witty-UB Container            │
│                                         │
│  ┌──────────────┐    ┌───────────────┐  │
│  │   Nginx      │───▶│  FastAPI      │  │
│  │  (Port 8080) │    │  (Port 9772)  │  │
│  │  (API Proxy) │    │  (Internal)   │  │
│  └──────────────┘    └───────────────┘  │
│                                         │
│  ┌──────────────────────────────────┐   │
│  │   C++ Binaries                   │   │
│  │   - witty-ub-log                 │   │
│  │   - witty-ub-topo                │   │
│  │   - witty-ub-diag-tool           │   │
│  └──────────────────────────────────┘   │
│                                         │
│  ┌──────────────────────────────────┐   │
│  │   Data & Configuration           │   │
│  │   - Failure mode data            │   │
│  │   - Config files                 │   │
│  │   - Web frontend                 │   │
│  └──────────────────────────────────┘   │
└─────────────────────────────────────────┘

外部端口映射:
- 宿主机端口 32412 → 容器内 8080 (Nginx + API 代理)
- 9772 仅容器内部使用，不暴露给外部
```

### 镜像分层架构

```
┌──────────────────────────────────────────┐
│  witty-ub:latest (应用镜像)              │
│  - 源码 COPY                             │
│  - C++ 编译产物                          │
│  - Web 前端构建产物                      │
│  - 运行时配置                            │
└──────────────────────────────────────────┘
                    ↑
┌──────────────────────────────────────────┐
│  witty-ub-base:latest (依赖基座镜像)      │
│  - openEuler 24.03 LTS 基础镜像          │
│  - C++ 编译工具链 (cmake, gcc-c++)       │
│  - 运行时依赖库 (log4cplus, sqlite, etc) │
│  - Python 虚拟环境及依赖                  │
│  - 目录结构创建                          │
└──────────────────────────────────────────┘
```

---

## 环境要求

### 必需软件

- **Docker**: 20.10 或更高版本
- **Docker Compose**: 2.0 或更高版本
- **Docker Buildx**: 0.10 或更高版本（多架构构建）
- **操作系统**: openEuler 24.03 LTS
- **磁盘空间**: 至少 10GB 可用空间
- **内存**: 至少 4GB RAM

### 验证环境

```bash
# 检查 Docker 版本
docker --version

# 检查 Docker Compose 版本
docker compose version

# 检查 Buildx 版本
docker buildx version

# 验证 Docker 运行状态
docker run hello-world
```

---

## 快速开始

### 1. 获取源码

```bash
git clone <repository-url>
cd witty-ub-dockerfile
```

### 2. 构建镜像

```bash
# 使用构建脚本（推荐）
bash build.sh

# 或使用 docker-compose 直接构建
docker compose up -d --build
```

首次构建需要 15-20 分钟（主要是安装依赖），后续源码改动后重建只需 2-5 分钟。

### 3. 启动服务

```bash
# 使用 docker-compose 启动
docker compose up -d
```

### 4. 验证部署

```bash
# 查看容器状态
docker compose ps

# 查看日志
docker compose logs -f

# 健康检查（通过 Nginx 代理）
curl http://localhost:32412/health_check
```

### 5. 访问服务

- **Web UI**: http://localhost:32412
- **API**: http://localhost:32412/health_check
- **API 文档**: http://localhost:32412/docs

**远程访问**: 将 `localhost` 替换为服务器 IP 地址，如 `http://服务器IP:32412`

---

## 详细部署步骤

### 步骤 1: 准备构建环境

确保 Docker 服务正常运行:

```bash
systemctl status docker
```

如果 Docker 未启动:

```bash
systemctl start docker
systemctl enable docker
```

### 步骤 2: 配置构建参数 (可选)

如果需要自定义配置，可以创建 `.env` 文件:

```bash
# .env 文件示例
COMPOSE_PROJECT_NAME=witty-ub
DOCKER_BUILDKIT=1
```

### 步骤 3: 构建镜像

#### 使用 build.sh 脚本（推荐）

```bash
# 本地构建（自动识别当前架构）
bash build.sh

# 完整构建（包含 base 镜像）
bash build.sh

# 仅构建应用镜像（依赖已存在时）
docker build -f Dockerfile -t witty-ub:latest .
```
#### 使用 docker compose 构建

```bash
# 完整构建
docker compose build

# 使用 BuildKit 加速构建
DOCKER_BUILDKIT=1 docker compose build

# 不使用缓存重新构建
docker compose build --no-cache
```

### 步骤 4: 启动容器

```bash
# 后台启动
docker compose up -d

# 前台启动 (查看实时日志)
docker compose up

# 指定配置文件
docker compose -f docker-compose.yml up -d
```

### 步骤 5: 验证服务

```bash
# 检查容器状态
docker compose ps

# 预期输出:
# NAME         STATUS         PORTS
# witty-ub     Up (healthy)   0.0.0.0:32412->8080/tcp

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

## 配置说明

### 环境变量

在 `docker-compose.yml` 中配置环境变量:

```yaml
environment:
  - PYTHONPATH=/var/witty-ub
  - LOG_LEVEL=info  # 可选: debug, info, warning, error
```

### Latency Plugin 配置

配置文件位于: `/var/witty-ub/config/latency/latency_config.toml`

```toml
[DS_LOG_ANALYZER]
TOTAL_P99_THRESHOLD_MS = 2.0
C2W_P99_THRESHOLD_MS = 2.0
W2W_P99_THRESHOLD_MS = 1.5
```

修改配置后需要重启容器:

```bash
docker compose restart
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

### 使用宿主机目录 (可选)

如果需要直接使用宿主机目录，修改 `docker-compose.yml`:

```yaml
volumes:
  # 将 Docker volumes 改为 bind mounts
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

## 日志管理

### 查看日志

```bash
# 查看所有日志
docker compose logs

# 实时查看日志
docker compose logs -f

# 查看最近 100 行
docker compose logs --tail=100

# 查看特定时间后的日志
docker compose logs --since 2024-01-01T10:00:00
```

### 日志位置

容器内日志路径:

- **Nginx 访问日志**: `/var/log/witty-ub-web/access.log`
- **Nginx 错误日志**: `/var/log/witty-ub-web/error.log`
- **Latency 服务日志**: `/var/log/witty-ub/latency_server.log`
- **应用日志**: `/var/log/witty-ub/`

### 导出日志

```bash
# 导出所有日志到文件
docker compose logs > witty-ub-logs.txt

# 导出最近 24 小时日志
docker compose logs --since 24h > witty-ub-logs-recent.txt
```

### 日志轮转

Docker 默认日志驱动为 `json-file`，建议配置日志轮转:

在 `docker-compose.yml` 中添加:

```yaml
services:
  witty-ub:
    logging:
      driver: "json-file"
      options:
        max-size: "100m"
        max-file: "3"
```

---

## 故障排查

### 容器无法启动

```bash
# 查看容器状态
docker compose ps

# 查看详细日志
docker compose logs witty-ub

# 进入容器调试
docker compose exec -it witty-ub bash
```

### 常见问题

#### 1. 端口冲突

**症状**: 启动失败，提示端口已被占用

**解决方案**:

```bash
# 查看端口占用
netstat -tlnp | grep 32412

# 修改 docker-compose.yml 中的端口映射（只需修改宿主机端口）
ports:
  - "32413:8080"  # 改为其他可用端口
```

#### 2. 权限问题

**症状**: 容器内无法写入数据

**解决方案**:

```bash
# 检查卷权限
docker exec witty-ub ls -la /var/witty-ub

# 修复权限
docker exec witty-ub chmod -R 755 /var/witty-ub
```

#### 3. Latency Plugin 未启动

**症状**: API 返回 502 或连接拒绝

**解决方案**:

```bash
# 查看 Latency 服务日志
docker exec witty-ub cat /var/log/witty-ub/latency_server.log

# 手动启动 Latency 服务
docker exec witty-ub /var/witty-ub/latency/.venv/bin/python \
  /var/witty-ub/latency/access/fastapi_server.py

# 检查健康状态
docker exec witty-ub curl http://localhost:9772/health_check
```

#### 4. Nginx 无法访问

**症状**: Web UI 无法打开

**解决方案**:

```bash
# 检查 Nginx 状态
docker exec witty-ub nginx -t

# 查看 Nginx 错误日志
docker exec witty-ub cat /var/log/witty-ub-web/error.log

# 重启 Nginx
docker exec witty-ub nginx -s reload
```

#### 5. 磁盘空间不足

**症状**: 容器启动失败或运行异常

**解决方案**:

```bash
# 检查磁盘使用
df -h

# 清理 Docker 无用资源
docker system prune -a

# 清理悬空镜像
docker image prune

# 清理未使用的卷
docker volume prune
```

#### 6. 依赖包找不到

**症状**: `cpp-httplib-devel` 等包安装失败

**解决方案**:

确保使用正确的基础镜像版本:
- `openeuler/openeuler:22.03-lts-sp4` (推荐，包含完整依赖)
- 基础版本 `22.03-lts` 可能缺少部分包

### 容器内调试

```bash
# 进入容器
docker exec -it witty-ub /bin/bash

# 查看进程
ps aux

# 查看网络
netstat -tlnp

# 查看 Python 环境
/var/witty-ub/latency/.venv/bin/pip list

# 手动启动服务
/var/witty-ub/latency/.venv/bin/python /var/witty-ub/latency/access/fastapi_server.py
```

---

## 多架构构建

### 架构支持

- **x86_64**: Linux AMD64
- **arm64/aarch64**: Linux ARM64

### 构建方式

#### 本地架构构建（默认）

```bash
# 自动识别当前宿主机架构
bash build.sh
```

#### 指定单架构构建

```bash
# 在 x86_64 机器上构建 ARM64 镜像
bash build.sh --platform linux/arm64

# 在 ARM64 机器上构建 x86_64 镜像
bash build.sh --platform linux/amd64
```

#### 双架构构建（需镜像仓库）

```bash
# 构建双架构镜像并推送到仓库
bash build.sh --multi --registry your-registry.com/witty-ub
```

### 构建脚本参数

| 参数 | 说明 |
|------|------|
| `--multi` | 启用双架构构建 (x86_64 + arm64) |
| `--registry <url>` | 指定镜像仓库地址（双架构构建必需） |
| `--platform <platform>` | 指定目标平台: `local`, `linux/amd64`, `linux/arm64` |
| `-h, --help` | 显示帮助信息 |

### 使用注意事项

1. **首次使用多架构构建**: 需要 QEMU 支持，脚本会自动安装
2. **双架构镜像**: 必须推送到镜像仓库（Docker 限制）
3. **单架构交叉编译**: 使用 `--platform` 指定，可用 `--load` 加载到本地
4. **运行时**: Docker 会自动拉取匹配宿主机架构的镜像

### 示例工作流

```bash
# 1. 在开发机上构建双架构镜像
bash build.sh --multi --registry registry.example.com/witty-ub

# 2. 在 x86_64 生产机上部署
docker-compose up -d

# 3. 在 ARM64 生产机上部署（自动使用 ARM64 镜像）
docker-compose up -d
```

---

## 生产环境建议

### 1. 资源限制

在 `docker-compose.yml` 中添加资源限制:

```yaml
services:
  witty-ub:
    deploy:
      resources:
        limits:
          cpus: '4'
          memory: 8G
        reservations:
          cpus: '2'
          memory: 4G
```

### 2. 重启策略

```yaml
services:
  witty-ub:
    restart: always  # 或 unless-stopped
```

### 3. 安全加固

- 使用非 root 用户运行:

```dockerfile
# 在 Dockerfile 中添加
RUN groupadd -r witty-ub && useradd -r -g witty-ub witty-ub
USER witty-ub
```

- 扫描镜像漏洞:

```bash
docker scan witty-ub
```

### 4. 监控与告警

```yaml
# 添加健康检查（通过 Nginx 代理）
healthcheck:
  test: ["CMD", "curl", "-f", "http://localhost:8080/health_check"]
  interval: 30s
  timeout: 10s
  retries: 3
  start_period: 40s
```

### 5. 日志集中管理

使用 Docker 日志驱动对接外部日志系统:

```yaml
logging:
  driver: "syslog"
  options:
    syslog-address: "tcp://log-server:514"
    tag: "witty-ub"
```

### 6. 备份策略

```bash
#!/bin/bash
# backup.sh
BACKUP_DIR="/backup/witty-ub"
DATE=$(date +%Y%m%d_%H%M%S)

mkdir -p $BACKUP_DIR

# 备份数据卷
docker run --rm \
  -v witty-ub_witty-ub-data:/data \
  -v $BACKUP_DIR:/backup \
  alpine tar czf /backup/data_$DATE.tar.gz -C /data .

# 清理 30 天前的备份
find $BACKUP_DIR -name "*.tar.gz" -mtime +30 -delete
```

---

## 从 RPM 迁移到容器化

### 迁移步骤

#### 1. 停止 RPM 部署的服务

```bash
systemctl stop witty-ub-web
systemctl stop witty-ub-latency
systemctl disable witty-ub-web
systemctl disable witty-ub-latency
```

#### 2. 备份现有数据

```bash
# 备份数据目录
tar czf witty-ub-data-backup.tar.gz \
  /var/witty-ub/data \
  /var/witty-ub/config \
  /var/log/witty-ub

# 备份数据库 (如果有)
cp /var/witty-ub/data/*.db ./backup/
```

#### 3. 卸载 RPM 包

```bash
rpm -qa | grep witty-ub
rpm -e witty-ub-1.0.2-3
```

#### 4. 部署容器版本

```bash
# 获取源码
git clone <repository-url>
cd witty-ub-dockerfile

# 构建并启动
bash build.sh
docker compose up -d
```

#### 5. 恢复数据

```bash
# 将备份数据复制到容器卷
docker run --rm \
  -v witty-ub_witty-ub-data:/data \
  -v $(pwd):/backup \
  alpine tar xzf /backup/witty-ub-data-backup.tar.gz -C /data
```

#### 6. 验证迁移

```bash
# 检查服务状态
docker compose ps

# 测试 API
curl http://localhost:32412/health_check

# 检查数据完整性
docker exec witty-ub ls -la /var/witty-ub/data
```

### 迁移注意事项

1. **数据兼容性**: 确保数据格式版本兼容
2. **网络配置**: 更新防火墙规则，开放容器端口 (32412)
3. **依赖服务**: 确认依赖的外部服务可访问
4. **监控告警**: 更新监控配置，指向新的容器服务
5. **回滚方案**: 保留 RPM 包，以便紧急回滚

---

## 附录

### A. build.sh 脚本使用

```bash
# 本地构建（自动识别架构）
bash build.sh

# 构建指定架构
bash build.sh --platform linux/amd64
bash build.sh --platform linux/arm64

# 构建双架构镜像（需推送仓库）
bash build.sh --multi --registry your-registry.com/witty-ub

# 显示帮助
bash build.sh --help
```

### B. Docker Compose 常用命令

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

# 扩展服务实例
docker compose up -d --scale witty-ub=2
```

### C. Docker 常用命令

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

### D. 文件结构

```
witty-ub-dockerfile/
├── Dockerfile                    # 应用构建文件（基于 base 镜像）
├── Dockerfile.base               # 依赖基座镜像构建文件
├── docker-compose.yml            # 容器编排配置
├── build.sh                      # 构建脚本（支持多架构）
├── .dockerignore                 # Docker 构建排除文件
├── docker/
│   ├── entrypoint.sh             # 容器启动脚本
│   └── nginx.conf                # Nginx 容器配置
├── src/                          # 源码目录
├── data/                         # 数据文件
├── config/                       # 配置文件
└── docs/                         # 文档目录
```

### E. 端口说明

| 端口 | 协议 | 用途 | 访问方式 |
|------|------|------|----------|
| 32412 | TCP | Web UI (Nginx + API代理) | http://localhost:32412 |
| 8080 | TCP | Nginx (容器内部) | 不直接访问 |
| 9772 | TCP | FastAPI (容器内部) | 通过 Nginx 代理访问 |

**端口映射关系**:
- 宿主机 `32412` → 容器 `8080` (Nginx)
- Nginx 内部代理 → 容器 `9772` (FastAPI)

**修改外部端口**: 只需修改 `docker-compose.yml` 中的宿主机端口映射。

### F. 环境变量参考

| 变量名 | 默认值 | 说明 |
|--------|--------|------|
| PYTHONPATH | /var/witty-ub | Python 模块搜索路径 |
| LOG_LEVEL | info | 日志级别 (debug/info/warning/error) |

---

## 技术支持

- **项目文档**: 参考项目根目录下的 README.md
- **问题反馈**: 提交 Issue 到项目仓库
- **更新日志**: 查看 CHANGELOG

---

*Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.*

*witty-ub is licensed under the Mulan PSL v2.*