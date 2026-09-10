# witty-ub 容器部署脚本

## 概述

本目录包含 witty-ub 的容器部署脚本，提供交互式菜单和命令行两种部署方式。

---

## 脚本文件

| 文件 | 说明 |
| ------ | ------ |
| `manage.sh` | 统一管理入口（交互式菜单 + 命令行，含分离部署） |
| `deploy_witty.sh` | witty-ub 容器部署（`--role all/backend/frontend`） |
| `deploy_pg.sh` | PostgreSQL 容器部署 |

---

## 快速开始

### 交互式菜单

```bash
bash manage.sh
```

```text
========================================
  witty-ub Deployment Manager
========================================

  📦  Install
    1) One-shot install: PG + witty-ub (Docker)
    2) Install PostgreSQL only
    3) Install witty-ub only

  🗑️  Uninstall
    4) Uninstall everything (including data)
    5) Uninstall witty-ub containers only
    6) Uninstall the PostgreSQL container only

  🔧  Manage
    7) Start all
    8) Stop all
    9) Restart all (auto-detect: local/Docker)
   10) Show status
   11) Show logs

  💻  Tools
   12) Open psql (PG)
   13) Open container shell

  🔀  Split frontend/backend deployment
   14) Install the witty-ub backend only (role=backend)
   15) Install the witty-ub frontend only (role=frontend)

    0) Quit
```

> 容器部署脚本的用户可见输出（日志 / 菜单 / 提示）统一使用**英文**，与 `build.sh`、`docker/entrypoint.sh`、`scripts/publish_split_release.sh` 等既有脚本保持一致；本仓库文档（`docs/`、README）使用中文。

### 命令行模式

```bash
# 一键安装
bash manage.sh install-all

# 仅安装 witty-ub
bash manage.sh install-witty

# 分离部署：后端 / 前端（可分别在不同机器执行）
bash manage.sh install-backend
bash manage.sh install-frontend

# 查看状态
bash manage.sh status

# 查看日志
bash manage.sh logs
```

---

## 内部调用链

```text
manage.sh
  ├── [1] 一键安装
  │     ├── deploy_pg.sh --docker
  │     └── deploy_witty.sh
  ├── [2] 仅安装 PG
  │     └── deploy_pg.sh [--docker | --rpm]
  ├── [3] 仅安装 witty-ub
  │     └── deploy_witty.sh
  ├── [14] 仅安装 witty-ub 后端（分离）
  │     └── deploy_witty.sh --role backend
  └── [15] 仅安装 witty-ub 前端（分离）
        └── deploy_witty.sh --role frontend
```

---

## 部署流程

### PostgreSQL 数据库部署

脚本自动完成以下步骤：

1. **拉取镜像**：使用 `quay.io/sclorg/postgresql-15-c9s:latest`，由安全入口从密钥挂载读取密码
2. **创建网络**：创建 Docker 网络 `witty-ub-network`
3. **创建数据卷**：创建持久化数据卷 `pg15-data`
4. **启动容器**：启动 PostgreSQL 容器，自动配置性能参数
5. **健康检查**：等待数据库就绪（最多 120 秒）
6. **连接验证**：测试数据库连接是否正常

### witty-ub 应用部署

脚本自动完成以下步骤（按 `--role` 分角色，默认 all）：

1. **拉取镜像**：优先使用本地镜像，否则从 `hub-harbor.oepkgs.net/neocopilot/witty-ub:<角色tag>` 拉取
2. **验证镜像**：检查镜像完整性（frontend 校验 Nginx/Web/Agent 资产，其余校验 BRPC 工具与数据）
3. **创建网络**：复用已有的 Docker 网络
4. **创建数据卷**：all/backend 建 `witty-ub-data/logs/uploads/results`，frontend 建 `witty-ub-experience-data`
5. **配置 OpenCode**：all/frontend 准备 OpenCode 配置目录
6. **自动检测 PG**：all/backend 检测 PostgreSQL 部署方式，自动配置连接参数；frontend 不连数据库
7. **启动容器**：容器名分别为 `<名称>`、`<名称>-backend`、`<名称>-frontend`；backend 暴露 9772，frontend 暴露 32413 并按 `WITTY_BACKEND_URL` 反代后端
8. **健康检查**：等待应用就绪（最多 180 秒）

---

## 配置文件

所有脚本共用 `deploy/deploy.conf`（旧名 `pg.conf` 仍兼容）。`manage.sh` 与 `deploy_witty.sh` 都会加载该文件，配置优先级为：**环境变量 > `deploy.conf` > 脚本内置默认值**。

> 无 TTY 环境（CI、`ssh host 'cmd'`、脚本调用）下所有交互提示自动取默认值（即上面的优先级结果），可直接使用 `install-all` / `install-pg` / `install-backend` / `install-frontend` 等命令行子命令。

### 完整配置项

```conf
# ---------- PG 连接 ----------
PG_HOST="127.0.0.1"
PG_PORT="15432"
PG_DATABASE="witty-ub"
PG_USER="witty-ub"
PG_PASSWORD="<CHANGE_ME>"    # 占位符，实际口令在 /etc/witty-ub/pg.passwd

# 容器内访问 PG（留空自动检测）
PG_HOST_IN_CONTAINER=""
PG_PORT_IN_CONTAINER=""

# ---------- PG 性能调优（暂未实现，设置无效）----------
# 说明：部署脚本不注入以下参数，PG 使用镜像默认值；如需调优请在 deploy_pg.sh
# 的 docker run 中自行追加 -e POSTGRESQL_*，或直接修改 PG 配置。
# PG_SHARED_BUFFERS=""
# PG_EFFECTIVE_CACHE_SIZE=""
# PG_WORK_MEM=""
# PG_MAINTENANCE_WORK_MEM=""
# PG_WAL_BUFFERS=""
# PG_MAX_WAL_SIZE=""
# PG_MAX_CONNECTIONS=""

# ---------- PG Docker ----------
PG_CONTAINER_NAME="postgres"
PG_IMAGE="quay.io/sclorg/postgresql-15-c9s:latest"
PG_NETWORK="witty-ub-network"
PG_VOLUME="pg15-data"

# ---------- witty-ub ----------
WITTY_CONTAINER_NAME="witty-ub"
WITTY_IMAGE=""                          # 留空自动选择
WITTY_HOST_PORT="32412"
WITTY_LOG_LEVEL="info"
WITTY_EXTRA_MOUNTS="/home:/home:ro"     # 额外挂载（可选）

# ---------- 前后端分离部署 ----------
WITTY_BACKEND_HOST_PORT="9772"          # 后端容器宿主机端口（容器内 9772）
WITTY_FRONTEND_HOST_PORT="32413"        # 前端容器宿主机端口（容器内 8080）
WITTY_BACKEND_URL=""                    # 前端容器内反代上游；留空 = http://witty-ub-backend:9772，跨机填 http://<后端IP>:9772
```

### 镜像拉取优先级

| 脚本 | 角色 | 优先级 | 镜像 |
| ------ | ------ | ------ | ------ |
| `deploy_witty.sh` | all | 1 | `hub-harbor.oepkgs.net/neocopilot/witty-ub:latest` |
| | | 2 | `witty-ub:latest` |
| `deploy_witty.sh` | backend | 1 | `hub-harbor.oepkgs.net/neocopilot/witty-ub:backend` |
| | | 2 | `witty-ub:backend` |
| `deploy_witty.sh` | frontend | 1 | `hub-harbor.oepkgs.net/neocopilot/witty-ub:frontend` |
| | | 2 | `witty-ub:frontend` |
| `deploy_pg.sh` | - | 1 | `quay.io/sclorg/postgresql-15-c9s:latest` |

> 脚本优先使用本地已有镜像，本地没有时按顺序拉取，拉取失败自动回退到下一个。

### PG 连接自动检测

`deploy_witty.sh` 启动时自动检测 PostgreSQL 部署方式（all/backend 角色）：

| 优先级 | 检测条件 | 连接结果 |
| ------ | ------ | ------ |
| 0 | `deploy.conf` 显式设置 `PG_HOST_IN_CONTAINER` | 使用配置值 |
| 1 | 同网络 PG 容器正在运行 | `postgres:5432` |
| 2 | 宿主机 RPM PG 正在运行 | `Docker网关IP:监听端口` |
| 3 | 以上都未检测到 | 默认 `postgres:5432` |

---

## 常见场景

### 已有 PG 容器，只部署 witty-ub

```bash
bash manage.sh
# 选择 [3] 仅安装 witty-ub
# 脚本自动检测到 PG 容器并配置连接
```

### PG 在宿主机（RPM 部署）

```bash
# 1) 初始化宿主机 PG（写入 deploy/pg.passwd，配置 listen_addresses/pg_hba 并重启服务）
sudo bash deploy/deploy_pg.sh --rpm

# 2) 部署容器 witty-ub：脚本自动检测宿主机 PG，并自动查找 deploy/pg.passwd
bash manage.sh install-witty

# 如需手动指定容器内的 PG 地址（deploy.conf 中）：
# PG_HOST_IN_CONTAINER=172.18.0.1
# PG_PORT_IN_CONTAINER=5432
```

### 自定义端口部署

```bash
# 修改 deploy/deploy.conf
# WITTY_HOST_PORT=8080

bash manage.sh
# 选择 [1] 一键安装
```

### 多实例部署（修改容器名）

```bash
# 修改 deploy/deploy.conf
# WITTY_CONTAINER_NAME=witty-ub-test
# WITTY_HOST_PORT=32413

bash manage.sh
# 选择 [3] 仅安装 witty-ub
```

### 前后端分离部署（同机）

```bash
bash manage.sh
# 选择 [2] 仅安装 PostgreSQL（或复用已有 PG）
# 选择 [14] 安装后端（角色 backend，宿主机 9772）
# 选择 [15] 安装前端（角色 frontend，宿主机 32413，反代 witty-ub-backend:9772）
```

### 前后端分离部署（跨机）

```bash
# 后端机器：部署 PG + backend，并对前端机器开放 9772
bash manage.sh install-pg
bash manage.sh install-backend

# 前端机器：WITTY_BACKEND_URL 指向后端机器
WITTY_BACKEND_URL=http://<后端机器IP>:9772 bash manage.sh install-frontend
```

### 完全卸载

```bash
bash manage.sh
# 选择 [4] 一键卸载
# 选择是否同时删除镜像
```

### 查看实时日志

```bash
bash manage.sh
# 选择 [11] 查看日志
# 选择查看 PG、witty-ub 或分离角色容器（backend/frontend）日志
```

---

## 故障排查

| 问题 | 排查方式 |
| ------ | ------ |
| 镜像拉取失败 | 检查网络、镜像仓库地址、本地 tag 是否已设置 |
| 容器启动后健康检查失败 | `docker logs witty-ub`（或 `witty-ub-backend` / `witty-ub-frontend`）查看日志 |
| PG 连接被拒 | 确认 PG 容器状态 `docker ps \| grep postgres` |
| PG 容器反复重启（`Permission denied`） | `sudo chmod 0640 /etc/witty-ub/pg.passwd`（需 0640 root:root，容器内 postgres 用户经 gid 0 读取） |
| PG RPM 未检测到 | 在 `deploy.conf` 中手动设置 `PG_HOST_IN_CONTAINER`（宿主机 PG 需 `listen_addresses='*'` 且已重启） |
| 分离前端 unhealthy | 前端经反代探测 `WITTY_BACKEND_URL/health_check`，确认后端容器已就绪且地址可达 |
| 端口冲突 | `ss -tlnp \| grep <端口>` 检查占用 |
| 容器已有数据但无法启动 | 检查数据卷完整性、PG 数据目录权限 |
| 与 compose 混用报容器名冲突 | 脚本与 `docker-compose.yml` 互斥（容器名/卷名/网络名一致），请二选一 |

---

## 相关文档

- [宿主机脚本部署](../../docs/deployment/02-script-host.md)
- [容器脚本部署](../../docs/deployment/03-script-container.md)
- [手动数据库部署](../../docs/deployment/05-database.md)
- [手动源码部署](../../docs/deployment/06-source.md)
- [手动 RPM 部署](../../docs/deployment/07-rpm.md)
- [手动容器部署](../../docs/deployment/08-container.md)
