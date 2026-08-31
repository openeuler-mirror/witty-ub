# Witty-UB 系统架构与部署概览

## 系统架构

Witty-UB 是一个用于超节点故障定位的工具，前后端默认分离部署。两类节点的定位：

| 节点 | 部署位置 | 网络要求 | 运行组件 |
| ------ | --------- | --------- | --------- |
| 后端节点 | 有数据的机器 | 无出网要求，仅对前端节点开放 9772 | FastAPI、C++ 工具链、PostgreSQL |
| 前端节点 | 能访问大模型服务的机器 | 需出网访问 LLM API | Nginx、OpenCode AI Agent |

```text
┌─ 前端节点 ─────────────────────────────┐      ┌─ 后端节点 ──────────────────────────────┐
│                                         │      │                                          │
│  ┌──────────┐                           │      │  ┌────────────────┐   ┌───────────────┐ │
│  │  Nginx   │── API 反代 ─────────────────────────▶ FastAPI (9772) │─▶│ C++ 工具链    │ │
│  │ (8080)   │   静态资源 dist/          │      │  └────────┬───────┘   │ log/topo/diag │ │
│  └────┬─────┘                           │      │           │           └───────────────┘ │
│       │ /agent-api/ 反代                 │      │           ▼                               │
│       ▼                                 │      │  ┌──────────────┐                         │
│  ┌──────────────┐                       │      │  │  PostgreSQL  │                         │
│  │   OpenCode   │                       │      │  └──────────────┘                         │
│  │   (4096)     │── curl 只读诊断 API ──────────────▶ FastAPI (9772)                      │
│  └──────────────┘                       │      │                                           │
│  LLM key 与经验库保存在本机               │      │  数据卷 /var/witty-ub，仅暴露 9772          │
└─────────────────────────────────────────┘      └──────────────────────────────────────────┘
```

两类节点也可以合并部署在同一台机器上，即单机 All-in-One 模式，`WITTY_ROLE=all` 为默认值，行为等价于上图两个节点叠加。Docker、RPM、源码三种部署方式均通过 `WITTY_ROLE` / `WITTY_BACKEND_URL` 等环境变量支持两种形态。

### 分离部署核心变量

| 变量 | 默认值 | 说明 |
| ------ | -------- | ------ |
| `WITTY_ROLE` | `all` | `all` 单机全量 / `backend` 仅后端 / `frontend` 仅前端 |
| `WITTY_BACKEND_URL` | `http://127.0.0.1:9772` | 前端节点 Nginx 的 API 反代上游，指向后端节点 |
| `WITTY_API_BASE` | 跟随 `WITTY_BACKEND_URL` | Agent 提示词中的后端 API 基址 |
| `WITTY_AGENT_URL` | `http://127.0.0.1:4096` | Nginx `/agent-api/` 反代上游（OpenCode） |
| `OPENCODE_HOST` | `127.0.0.1` | OpenCode 监听地址 |

## 组件说明

| 组件 | 说明 | 落位 |
| ------ | ------ | ------ |
| **Web 前端** | Nginx 静态托管 + API/Agent 反代 | 前端节点 |
| **OpenCode** | AI Agent 服务，提供 AI 辅助故障诊断 | 前端节点 |
| **FastAPI 后端** | 诊断 API，只读，供 Web 与 Agent 调用 | 后端节点 |
| **C++ 工具链** | witty-ub-log、witty-ub-topo、witty-ub-diag-tool | 后端节点 |
| **PostgreSQL** | 关系型数据库，存储故障诊断数据 | 后端节点 |

## 部署方式对比

| 方式 | 适用场景 | 优点 | 缺点 |
| ------ | --------- | ------ | ------ |
| **容器化（推荐）** | 生产环境、快速部署 | 环境一致性、快速部署、易于扩展、版本管理 | 需要 Docker 环境 |
| **源码编译** | 开发调试、定制化需求 | 灵活修改、无需 Docker | 环境依赖多、编译耗时长 |
| **RPM 包** | openEuler 原生部署、无 Docker 环境 | 原生安装、系统级集成 | 依赖 openEuler 版本 |

> PostgreSQL 随后端节点部署（容器化或 RPM 均可）。

## 端口映射

### 前后端分离部署（默认形态）

| 节点 | 端口 | 协议 | 用途 |
| ------ | ------ | ------ | ------ |
| 后端节点 | 9772 | TCP | FastAPI（绑 `0.0.0.0`，仅对前端节点开放） |
| 前端节点 | 8080 / 32413 | TCP | Web UI（Nginx 静态托管 + 反代后端与本机 OpenCode） |
| 前端节点 | 4096 | TCP | OpenCode（仅本机/容器内，经 `/agent-api/` 反代） |

### 单机 All-in-One（前后端同机）

| 部署方式 | 对外端口 | 内部端口 |
| --------- | --------- | --------- |
| 容器 | 32412 → 8080（Nginx） | 9772（FastAPI）、4096（OpenCode），均经 Nginx 反代 |
| 容器 split profile | 32413 → 8080（前端容器） | backend 容器 9772 不对外 |
| 宿主机脚本 | 8080（Nginx，回退 vite preview 5173）、9772（后端） | 15432（PostgreSQL） |
| RPM | 8080（Nginx）、9772（FastAPI） | 5432（PostgreSQL） |

## 环境要求

### 必需软件

- **操作系统**: openEuler 24.03 LTS SP3 / SP4
- **Docker**: 20.10+，仅容器化部署需要

### 容器化部署额外要求

- **内存**: 至少 4GB RAM
- **磁盘**: 至少 10GB 可用空间

### 源码编译额外要求

- **GCC/G++**: 10+
- **CMake**: 3.16+
- **Python**: 3.9+
- **Node.js**: 18+，仅前端节点需要

### 前端节点额外要求

- 能出网访问大模型服务，OpenCode 调用 LLM API
- 源码或 RPM 部署方式需要 Node.js 18+ 与 `npm i -g opencode-ai`
- LLM API key 已配置于 `~/.config/opencode/opencode.jsonc`

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

```text
witty-ub/
├── Dockerfile                    # 应用容器构建
├── Dockerfile.base               # 基座镜像构建
├── Dockerfile.rpm                # RPM 包构建
├── build.sh                      # 镜像构建脚本
├── deploy/                       # 部署脚本
│   ├── deploy.conf               # 统一部署配置文件
│   ├── deploy_pg.sh              # PostgreSQL 部署
│   ├── host/                     # 宿主机/源码部署
│   │   ├── deploy.sh             # 一键部署脚本（--role backend/frontend）
│   │   ├── install_deps.sh       # 依赖安装
│   │   ├── run_frontend.sh       # 前端启动器 (vite preview / dev 回退)
│   │   ├── test_full_deploy.sh   # 全量部署回归测试
│   │   ├── systemd/              # systemd user unit 模板
│   │   └── _lib.sh               # 共享工具库
│   └── docker/                   # 容器部署
│       ├── manage.sh             # 统一管理入口
│       └── deploy_witty.sh       # witty-ub 部署
├── docker/                       # 容器配置
│   ├── entrypoint.sh             # 容器启动脚本（按 WITTY_ROLE 分角色）
│   ├── healthcheck.sh            # 角色感知健康检查
│   └── nginx.conf                # Nginx 配置
├── packaging/nginx/              # Nginx 配置模板（占位符渲染）
├── src/                          # 源码
├── data/                         # 数据文件
├── config/                       # 配置文件
└── docs/                         # 文档
```

## 快速开始

根据你的部署场景选择（以下方式均支持单机与分离部署）：

- **容器脚本部署** → [03-script-container.md](03-script-container.md)
- **宿主机脚本部署** → [02-script-host.md](02-script-host.md)
- **手动数据库部署** → [05-database.md](05-database.md)
- **手动源码部署** → [06-source.md](06-source.md)
- **手动 RPM 部署** → [07-rpm.md](07-rpm.md)
- **手动容器部署** → [08-container.md](08-container.md)
