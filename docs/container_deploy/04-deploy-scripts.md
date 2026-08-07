<!-- Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved. -->
<!-- witty-ub is licensed under the Mulan PSL v2. -->

# 4. 部署脚本使用指南

> 返回 [首页](Home.md)

## 概述

项目在 `deploy/` 目录下提供了一组一键部署脚本，分为**宿主机部署** (`host/`) 和**容器部署** (`docker/`) 两个场景，另有共用的 PG 部署脚本和配置文件。

```
deploy/
├── host/                     # 宿主机/本地部署
│   ├── _lib.sh               # 共享工具库
│   ├── install_deps.sh       # 依赖安装 (系统包 + Python venv)，可独立执行
│   └── deploy.sh             # 总控: PG 初始化 + C++ 编译 + 启动 + stop/clean
├── docker/                   # 容器部署
│   ├── deploy_witty.sh       # witty-ub 容器一键部署
│   └── manage.sh             # 统一管理入口 (交互式菜单 + 命令行)
├── deploy_pg.sh              # PostgreSQL 独立部署 (Docker/RPM/APT)，两边共用
└── pg.conf                   # 统一配置文件 (所有脚本共用)
```

---

## 统一配置文件：pg.conf

所有部署脚本都从 `deploy/pg.conf` 读取配置。修改该文件后，所有脚本都会生效。

### PostgreSQL 配置

```conf
# PostgreSQL 连接信息（宿主机视角）
PG_HOST="127.0.0.1"
PG_PORT="15432"
PG_DATABASE="latency_diag"
PG_USER="witty_ub"
PG_PASSWORD="witty_ub"

# PostgreSQL 连接信息（容器内视角，留空则自动检测）
# 自动检测逻辑：
#   - 检测到同网络有 PG 容器 → 使用容器名:5432
#   - 检测到宿主机 RPM PG    → 使用 Docker 网关 IP:监听端口
#   - 如需覆盖自动检测，手动填写即可
PG_HOST_IN_CONTAINER=""
PG_PORT_IN_CONTAINER=""

# PG 容器名
PG_CONTAINER_NAME="postgres"
```

### witty-ub 配置

```conf
# 容器名
WITTY_CONTAINER_NAME="witty-ub"

# 镜像（留空则自动选择：本地镜像 > 拉取镜像）
WITTY_IMAGE=""

# 宿主机端口（外部访问端口）
WITTY_HOST_PORT="32412"

# Docker 网络
WITTY_NETWORK="witty-ub-network"

# 数据卷
WITTY_VOLUME_DATA="witty-ub-data"
WITTY_VOLUME_LOGS="witty-ub-logs"
WITTY_VOLUME_UPLOADS="witty-ub-uploads"
WITTY_VOLUME_RESULTS="witty-ub-results"

# OpenCode 配置目录
OPENCODE_CONFIG_DIR="$HOME/.config/opencode"

# 额外目录挂载（容器访问宿主机日志/数据文件）
# 格式：宿主机路径:容器内路径[:ro|rw]  多个用空格分隔
# 示例：WITTY_EXTRA_MOUNTS="/data/logs:/var/witty-ub/host_logs:ro /data/models:/var/witty-ub/models:ro"
WITTY_EXTRA_MOUNTS=""
```

---

## 一键部署：manage.sh

`deploy/docker/manage.sh` 是统一管理入口，支持**交互式菜单**和**命令行直接调用**两种模式。

### 模式一：交互式菜单（推荐新手）

```bash
bash deploy/docker/manage.sh
```

输出：

```
========================================
  Witty-UB Deployment Manager
========================================

  PostgreSQL:  检测中...
  witty-ub:    检测中...

========================================
  Main Menu
========================================
  [1]  一键安装 (PostgreSQL + witty-ub)
  [2]  仅安装 PostgreSQL (Docker)
  [3]  仅安装 witty-ub
  [4]  卸载 witty-ub
  [5]  卸载 PostgreSQL
  [6]  全部卸载
  [7]  重启 witty-ub
  [8]  重启全部服务
  [9]  查看服务状态
  [0]  退出

请选择操作 [0-9]:
```

选择 `3) 仅安装 witty-ub` 后，会进入交互式配置：

```
┌─────────────────────────────────────────────────────┐
│           witty-ub 部署参数配置                       │
│           直接回车使用 [ ] 中的默认值                  │
└─────────────────────────────────────────────────────┘

  [1] 宿主机端口          [32412]:

  [2] 额外目录挂载（容器访问宿主机日志/数据文件）
      格式: 宿主机路径:容器内路径[:ro|rw]  多个用空格分隔
      ro=只读(推荐)  rw=读写  留空=跳过
                         [留空跳过]:

  [3] 指定镜像            [留空自动选择]:

┌─────────────────────────────────────────────────────┐
│                    配置汇总                            │
├─────────────────────────────────────────────────────┤
│  宿主机端口        32412                               │
│  镜像                 自动选择                        │
│  额外挂载           无                                   │
└─────────────────────────────────────────────────────┘

[OK]    检测到 PostgreSQL: 宿主机服务（postgresql.service，端口 15432）
```

### 模式二：命令行直接调用（适合自动化）

```bash
# 一键安装 PostgreSQL + witty-ub
bash deploy/docker/manage.sh install-all

# 仅安装 PostgreSQL（Docker 方式）
bash deploy/docker/manage.sh install-pg

# 仅安装 witty-ub
bash deploy/docker/manage.sh install-witty

# 卸载 witty-ub
bash deploy/docker/manage.sh uninstall-witty

# 卸载全部
bash deploy/docker/manage.sh uninstall-all

# 重启 witty-ub
bash deploy/docker/manage.sh restart-witty

# 查看状态
bash deploy/docker/manage.sh status

# 查看帮助
bash deploy/docker/manage.sh --help
```

---

## 单独部署：deploy_witty.sh

只需要部署 witty-ub 时使用，适合已有 PostgreSQL 的场景。

### 基本用法

```bash
# 使用默认配置（从 pg.conf 读取）
bash deploy/docker/deploy_witty.sh

# 指定镜像
bash deploy/docker/deploy_witty.sh --image hub-harbor.oepkgs.net/neocopilot/witty-ub:latest

# 查看帮助
bash deploy/docker/deploy_witty.sh --help
```

### 自动完成的工作

`deploy_witty.sh` 会自动完成以下步骤：

```
[Step 1/3] 检查并拉取镜像
  - 优先使用本地已有的镜像
  - 本地没有时按优先级拉取（harbor 镜像 > witty-ub:latest）

[Step 2/3] 验证镜像
  - 确认镜像存在，打印 ID 和大小

[Step 3/3] 启动容器
  - 创建 Docker 网络（witty-ub-network）
  - 创建 4 个数据卷（data/logs/uploads/results）
  - 准备 OpenCode 配置目录
  - 自动检测 PG 连接配置
  - 清理旧容器（如有）
  - 启动新容器
  - 等待健康检查通过
  - 验证 API 连通性
```

部署完成输出：

```
========================================
witty-ub Deployment Completed!
========================================
  Container:  witty-ub
  Image:      witty-ub:latest
  Web UI:     http://localhost:32412
  API:        http://localhost:32412/health_check
  API Docs:   http://localhost:32412/docs
  OpenCode:   http://localhost:32412/opencode/
  Network:    witty-ub-network
  PG Host:    172.18.0.1:15432 (container)
  Extra mounts:
    - /data/logs:/var/witty-ub/host_logs:ro
```

### 环境变量覆盖

也可以通过环境变量临时覆盖 pg.conf 配置：

```bash
# 指定端口和镜像
WITTY_HOST_PORT=8080 WITTY_IMAGE=my-custom:v1 bash deploy/docker/deploy_witty.sh

# 指定额外挂载
WITTY_EXTRA_MOUNTS="/data/logs:/var/witty-ub/logs:ro" bash deploy/docker/deploy_witty.sh

# 手动指定 PG 连接（覆盖自动检测）
PG_HOST_IN_CONTAINER=172.18.0.1 PG_PORT_IN_CONTAINER=15432 bash deploy/docker/deploy_witty.sh
```

---

## 单独部署 PostgreSQL：deploy_pg.sh

只需要部署 PostgreSQL 时使用。

### 基本用法

```bash
# 默认 Docker 方式部署
bash deploy/deploy_pg.sh

# Docker 方式部署
bash deploy/deploy_pg.sh --docker

# RPM 方式部署
bash deploy/deploy_pg.sh --rpm

# 查看帮助
bash deploy/deploy_pg.sh --help
```

部署完成后：
- 数据保存在 `pg15-data` Docker 卷（Docker 方式）
- 或保存在 RPM 默认数据目录（RPM 方式）
- 端口：`15432`（宿主机）/ `5432`（容器内）

---

## 常见场景

### 场景 1：全新部署（PostgreSQL + witty-ub 都用 Docker）

```bash
# 方式一：交互式
bash deploy/docker/manage.sh
# 选择 [1] 一键安装

# 方式二：命令行
bash deploy/docker/manage.sh install-all
```

### 场景 2：已有 RPM PostgreSQL，仅部署 witty-ub

```bash
# 脚本会自动检测到宿主机 PG，无需额外配置
bash deploy/docker/manage.sh install-witty
```

### 场景 3：需要容器访问宿主机日志目录

在 `deploy/pg.conf` 中配置：

```conf
WITTY_EXTRA_MOUNTS="/var/log/neocopilot:/var/witty-ub/host_logs:ro"
```

然后重新部署：

```bash
bash deploy/docker/deploy_witty.sh
```

### 场景 4：使用自定义镜像

```bash
bash deploy/docker/deploy_witty.sh --image my-registry.com/witty-ub:v2.0
```

或在 `pg.conf` 中永久配置：

```conf
WITTY_IMAGE="my-registry.com/witty-ub:v2.0"
```

---

## 下一步

- 继续阅读: [5. 故障排查](05-troubleshooting.md)
- 返回 [首页](Home.md)
