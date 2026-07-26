<!-- Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved. -->
<!-- witty-ub is licensed under the Mulan PSL v2. -->

# 1. 容器化部署说明

> 返回 [首页](Home.md)

## 概述

Witty-UB 是一个用于 Lingqu(UB) 架构 SuperPod 故障定位的工具。本文档介绍如何使用 Docker 容器化方式部署 Witty-UB，替代传统的 RPM 包部署方式。

### 容器化优势

- **环境一致性**: 一次构建，到处运行，消除环境差异
- **快速部署**: 一条命令即可启动所有服务
- **易于扩展**: 支持水平扩展和负载均衡
- **资源隔离**: 容器级别隔离，不影响宿主机
- **版本管理**: 镜像版本控制，支持快速回滚
- **依赖缓存**: 分离依赖镜像和应用镜像，源码改动后快速重建

---

## 架构说明

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
│         │                               │
│         └───────────────▶│ OpenCode     │  │
│                          │  (Port 4096) │  │
│                          │  (Internal)  │  │
│                          └───────────────┘  │
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
│  │   - OpenCode config & agents     │   │
│  └──────────────────────────────────┘   │
└─────────────────────────────────────────┘

外部端口映射:
- 宿主机端口 32412 → 容器内 8080 (Nginx + API 代理)
- 9772 仅容器内部使用，不暴露给外部
- 4096 仅容器内部使用，不暴露给外部（OpenCode）
```

### 外部依赖：PostgreSQL

witty-UB 容器依赖 PostgreSQL 存储故障诊断数据。PostgreSQL 不属于容器内部组件，需单独部署，支持两种方式：

```
┌──────────────────────────────────────────────────────────────┐
│                        witty-ub-network                       │
│                                                              │
│  ┌──────────────────────┐         ┌──────────────────────┐  │
│  │   Witty-UB Container  │         │   PostgreSQL (可选)   │  │
│  │                      │         │  容器名: postgres      │  │
│  │  FastAPI (9772) ───┼─────────┼─▶  端口: 5432          │  │
│  │                      │         │                      │  │
│  └──────────────────────┘         └──────────────────────┘  │
│                                 │                              │
│                                 │  或（PG 在宿主机）           │
│                                 ▼                              │
│                       ┌──────────────────┐                     │
│                       │  宿主机 RPM PG    │                     │
│                       │  端口: 15432     │                     │
│                       └──────────────────┘                     │
└──────────────────────────────────────────────────────────────┘
```

| 部署方式 | 连接地址（容器内视角） | 端口 | 适用场景 |
|---------|----------------------|------|---------|
| Docker 容器（同网络） | `postgres`（容器名） | `5432` | 全新部署、开发测试 |
| 宿主机 RPM | Docker 网络网关 IP（如 `172.18.0.1`） | `15432` | 已有 RPM PG、数据迁移 |

> **提示**：使用 `deploy/deploy_witty.sh` 部署时，脚本会自动检测 PostgreSQL 的部署方式并配置连接参数，无需手动填写。详见 [PostgreSQL 连接配置](03-pull-and-run.md#postgresql-连接配置)。

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
│  - openEuler 24.03 LTS SP4 基础镜像      │
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

## 文件结构

```
witty-ub/
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
tar czf witty-ub-data-backup.tar.gz \
  /var/witty-ub/data \
  /var/witty-ub/config \
  /var/log/witty-ub

cp /var/witty-ub/data/*.db ./backup/
```

#### 3. 卸载 RPM 包

```bash
rpm -qa | grep witty-ub
rpm -e witty-ub-1.0.2-3
```

#### 4. 部署容器版本

```bash
git clone <repository-url>
cd witty-ub

bash build.sh
docker compose up -d
```

#### 5. 恢复数据

```bash
docker run --rm \
  -v witty-ub_witty-ub-data:/data \
  -v $(pwd):/backup \
  alpine tar xzf /backup/witty-ub-data-backup.tar.gz -C /data
```

#### 6. 验证迁移

```bash
docker compose ps
curl http://localhost:32412/health_check
docker exec witty-ub ls -la /var/witty-ub/data
```

### 迁移注意事项

1. **数据兼容性**: 确保数据格式版本兼容
2. **网络配置**: 更新防火墙规则，开放容器端口 (32412)
3. **依赖服务**: 确认依赖的外部服务可访问
4. **监控告警**: 更新监控配置，指向新的容器服务
5. **回滚方案**: 保留 RPM 包，以便紧急回滚

---

## 下一步

- 继续阅读: [2. 镜像构建、上传与打包](02-build-and-package.md)
- 返回 [首页](Home.md)
