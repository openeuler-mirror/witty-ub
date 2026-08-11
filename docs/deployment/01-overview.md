                                                                    # Witty-UB 系统架构与部署概览

## 系统架构

Witty-UB 是一个用于超节点故障定位的工具，由以下两个核心组件组成：

```
┌──────────────────────────────────────────────────────────────┐
│                        Witty-UB 系统                          │
│                                                              │
│  ┌────────────────────────────────────────────────────────┐  │
│  │                 witty-ub 应用服务                       │  │
│  │                                                        │  │
│  │  ┌──────────┐   ┌───────────┐   ┌──────────────────┐  │  │
│  │  │  Nginx   │──▶│  FastAPI   │──▶│  C++ 工具链       │  │  │
│  │  │ (8080)   │   │ (9772)    │   │  - witty-ub-log  │  │  │
│  │  └──────────┘   └─────┬─────┘   │  - witty-ub-topo│  │  │
│  │          │             │         │  - witty-ub-diag│  │  │
│  │          │             │         └──────────────────┘  │  │
│  │          │             ▼                                 │  │
│  │          │      ┌──────────────┐                       │  │
│  │          │      │   OpenCode   │                       │  │
│  │          │      │  (AI Agent)  │                       │  │
│  │          │      └──────────────┘                       │  │
│  │          │                                              │  │
│  │          ▼                                              │  │
│  │     数据持久化 (Docker Volumes / RPM 目录)                 │  │
│  └────────────────────────────────────────────────────────┘  │
│                          │                                   │
│                          │ 连接                               │
│                          ▼                                   │
│  ┌────────────────────────────────────────────────────────┐  │
│  │               PostgreSQL 数据库                         │  │
│  │               (故障诊断数据存储)                          │  │
│  └────────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────────┘
```

## 组件说明

| 组件 | 说明 | 可选部署方式 |
|------|------|-------------|
| **witty-ub** | 核心应用服务，提供 Web UI、API、AI 辅助诊断 | 容器化（推荐）、源码编译、RPM 包 |
| **PostgreSQL** | 关系型数据库，存储故障诊断数据 | 容器化（推荐）、RPM 包 |
| **OpenCode** | AI Agent 服务，提供 AI 辅助故障诊断 | 随 witty-ub 部署（内置） |
| **C++ 工具链** | witty-ub-log、witty-ub-topo、witty-ub-diag-tool | 随 witty-ub 部署（内置） |

## 部署方式对比

### witty-ub 应用

| 方式 | 适用场景 | 优点 | 缺点 |
|------|---------|------|------|
| **容器化（推荐）** | 生产环境、快速部署 | 环境一致性、快速部署、易于扩展、版本管理 | 需要 Docker 环境 |
| **源码编译** | 开发调试、定制化需求 | 灵活修改、无需 Docker | 环境依赖多、编译耗时长 |
| **RPM 包** | openEuler 原生部署、无 Docker 环境 | 原生安装、系统级集成 | 依赖 openEuler 版本 |

### PostgreSQL 数据库

| 方式 | 适用场景 | 优点 | 缺点 |
|------|---------|------|------|
| **容器化（推荐）** | 全新部署、与 witty-ub 一起部署 | 快速部署、数据隔离、易于迁移 | 需要 Docker 环境 |
| **RPM 包** | 已有 RPM PG、生产环境 | 原生安装、系统级集成 | 需手动配置 |

## 端口映射

### 容器化部署

| 端口 | 协议 | 用途 | 访问方式 |
|------|------|------|----------|
| 32412 | TCP | Web UI (Nginx + API) | 外部访问 |
| 8080 | TCP | Nginx（容器内部） | 不直接访问 |
| 9772 | TCP | FastAPI（容器内部） | 通过 Nginx 代理 |
| 4096 | TCP | OpenCode（容器内部） | 通过 Nginx 代理 |

**端口映射关系**：

```
宿主机 32412  →  容器 8080 (Nginx)  →  内部转发
                                        ├── 9772 (FastAPI)
                                        └── 4096 (OpenCode)
```

### 宿主机脚本部署（deploy/host/deploy.sh）

| 端口 | 协议 | 用途 | 访问方式 |
|------|------|------|----------|
| 5173 | TCP | Web UI（vite preview 托管 `dist/`；无 `dist/` 时回退 dev server） | 外部访问 |
| 9772 | TCP | FastAPI（后端服务） | 外部访问 |
| 15432 | TCP | PostgreSQL（数据存储） | 本机访问（部署脚本） |
| 4096 | TCP | OpenCode（AI Agent） | 不直接访问 |

> 该方式前端直接由 Vite 托管（无 Nginx 反代），后端 9772 无需代理即可访问。

### RPM / 源码部署

| 端口 | 协议 | 用途 |
|------|------|------|
| 8080 | TCP | Web UI（RPM 部署） |
| 5173 | TCP | Web UI（源码开发模式） |
| 9772 | TCP | FastAPI（后端服务） |
| 4096 | TCP | OpenCode（AI Agent） |

## 环境要求

### 必需软件

- **Docker**: 20.10 或更高版本（容器化部署）
- **操作系统**: openEuler 24.03 LTS SP3 / SP4

### 容器化部署额外要求

- **内存**: 至少 4GB RAM
- **磁盘**: 至少 10GB 可用空间

### 源码编译额外要求

- **GCC/G++**: 10+
- **CMake**: 3.16+
- **Python**: 3.9+
- **Node.js**: 18+

### 验证环境

```bash
# Docker 版本
docker --version

# GCC 版本
gcc --version

# CMake 版本
cmake --version

# Python 版本
python3 --version

# Node.js 版本
node --version
```

## 文件结构

```
witty-ub/
├── Dockerfile                    # 应用容器构建
├── Dockerfile.base               # 基座镜像构建
├── Dockerfile.rpm                # RPM 包构建
├── build.sh                      # 镜像构建脚本
├── deploy/                       # 部署脚本
│   ├── pg.conf                   # 统一配置文件
│   ├── deploy_pg.sh              # PostgreSQL 部署
│   ├── host/                     # 宿主机/源码部署
│   │   ├── deploy.sh             # 一键部署脚本
│   │   ├── install_deps.sh       # 依赖安装
│   │   ├── run_frontend.sh       # 前端启动器 (vite preview / dev 回退)
│   │   ├── test_full_deploy.sh   # 全量部署回归测试
│   │   ├── systemd/              # systemd user unit 模板
│   │   └── _lib.sh               # 共享工具库
│   └── docker/                   # 容器部署
│       ├── manage.sh             # 统一管理入口
│       └── deploy_witty.sh       # witty-ub 部署
├── docker/                       # 容器配置
│   ├── entrypoint.sh             # 容器启动脚本
│   └── nginx.conf                # Nginx 配置
├── src/                          # 源码
├── data/                         # 数据文件
├── config/                       # 配置文件
└── docs/                         # 文档
```

## 快速开始

根据你的部署场景选择：

- **容器脚本部署** → [03-script-container.md](03-script-container.md)
- **宿主机脚本部署** → [02-script-host.md](02-script-host.md)
- **手动数据库部署** → [05-database.md](05-database.md)
- **手动源码部署** → [06-source.md](06-source.md)
- **手动 RPM 部署** → [07-rpm.md](07-rpm.md)
- **手动容器部署** → [08-container.md](08-container.md)
