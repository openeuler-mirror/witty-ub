# witty-ub 容器部署脚本

## 概述

本目录包含 witty-ub 的容器部署脚本，提供交互式菜单和命令行两种部署方式。

---

## 脚本文件

| 文件 | 说明 |
|------|------|
| `manage.sh` | 统一管理入口（交互式菜单 + 命令行） |
| `deploy_witty.sh` | witty-ub 容器部署 |
| `deploy_pg.sh` | PostgreSQL 容器部署 |

---

## 快速开始

### 交互式菜单

```bash
bash manage.sh
```

```
========================================
  witty-ub 部署管理器
========================================

  📦  安装
    1) 一键安装：PG + witty-ub（Docker）
    2) 仅安装 PostgreSQL
    3) 仅安装 witty-ub

  🗑️  卸载
    4) 一键卸载：全部删除（含数据）
    5) 仅卸载 witty-ub 容器
    6) 仅卸载 PostgreSQL 容器

  🔧  管理
    7) 启动全部
    8) 停止全部
    9) 重启全部
   10) 查看状态
   11) 查看日志

  💻  工具
   12) 进入 psql（PG）
   13) 进入容器 Shell

    0) 退出
```

### 命令行模式

```bash
# 一键安装
bash manage.sh install-all

# 仅安装 witty-ub
bash manage.sh install-witty

# 查看状态
bash manage.sh status

# 查看日志
bash manage.sh logs
```

---

## 内部调用链

```
manage.sh
  ├── [1] 一键安装
  │     ├── deploy_pg.sh --docker
  │     └── deploy_witty.sh
  ├── [2] 仅安装 PG
  │     └── deploy_pg.sh [--docker | --rpm]
  └── [3] 仅安装 witty-ub
        └── deploy_witty.sh
```

---

## 部署流程

### PostgreSQL 数据库部署

脚本自动完成以下步骤：

1. **拉取镜像**：优先使用本地镜像，否则从 `quay.io/sclorg/postgresql-15-c9s:latest` 拉取
2. **创建网络**：创建 Docker 网络 `witty-ub-network`
3. **创建数据卷**：创建持久化数据卷 `pg15-data`
4. **启动容器**：启动 PostgreSQL 容器，自动配置性能参数
5. **健康检查**：等待数据库就绪（最多 120 秒）
6. **连接验证**：测试数据库连接是否正常

### witty-ub 应用部署

脚本自动完成以下步骤：

1. **拉取镜像**：优先使用本地镜像，否则从 `hub-harbor.oepkgs.net/neocopilot/witty-ub:latest` 拉取
2. **验证镜像**：检查镜像完整性
3. **创建网络**：复用已有的 Docker 网络
4. **创建数据卷**：创建应用数据卷
5. **配置 OpenCode**：准备 OpenCode 配置目录
6. **自动检测 PG**：检测 PostgreSQL 部署方式，自动配置连接参数
7. **启动容器**：启动 witty-ub 容器
8. **健康检查**：等待应用就绪（最多 180 秒）

---

## 配置文件

所有脚本共用 `deploy/deploy.conf`（旧名 `pg.conf` 仍兼容），修改后全局生效。

### 完整配置项

```conf
# ---------- PG 连接 ----------
PG_HOST="127.0.0.1"
PG_PORT="15432"
PG_DATABASE="witty-ub"
PG_USER="witty-ub"
PG_PASSWORD="witty-ub"

# 容器内访问 PG（留空自动检测）
PG_HOST_IN_CONTAINER=""
PG_PORT_IN_CONTAINER=""

# ---------- PG 性能调优（留空自动计算）----------
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
```

### 镜像拉取优先级

| 脚本 | 优先级 | 镜像 |
|------|--------|------|
| `deploy_witty.sh` | 1 | `hub-harbor.oepkgs.net/neocopilot/witty-ub:latest` |
| | 2 | `witty-ub:latest` |
| `deploy_pg.sh` | 1 | `quay.io/sclorg/postgresql-15-c9s:latest` |
| | 2 | `postgres:15` |
| | 3 | `postgres:latest` |

> 脚本优先使用本地已有镜像，本地没有时按顺序拉取，拉取失败自动回退到下一个。

### PG 连接自动检测

`deploy_witty.sh` 启动时自动检测 PostgreSQL 部署方式：

| 优先级 | 检测条件 | 连接结果 |
|--------|---------|---------|
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
bash manage.sh
# 选择 [3] 仅安装 witty-ub
# 脚本自动检测 RPM PG

# 或在 pg.conf 中手动指定
# PG_HOST_IN_CONTAINER=172.18.0.1
# PG_PORT_IN_CONTAINER=5432
```

### 自定义端口部署

```bash
# 修改 pg.conf
# WITTY_HOST_PORT=8080

bash manage.sh
# 选择 [1] 一键安装
```

### 多实例部署（修改容器名）

```bash
# 修改 pg.conf
# WITTY_CONTAINER_NAME=witty-ub-test
# WITTY_HOST_PORT=32413

bash manage.sh
# 选择 [3] 仅安装 witty-ub
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
# 选择查看 PG 或 witty-ub 日志
```

---

## 故障排查

| 问题 | 排查方式 |
|------|---------|
| 镜像拉取失败 | 检查网络、镜像仓库地址、本地 tag 是否已设置 |
| 容器启动后健康检查失败 | `docker logs witty-ub` 查看日志 |
| PG 连接被拒 | 确认 PG 容器状态 `docker ps \| grep postgres` |
| PG RPM 未检测到 | 在 `pg.conf` 中手动设置 `PG_HOST_IN_CONTAINER` |
| 端口冲突 | `ss -tlnp \| grep <端口>` 检查占用 |
| 容器已有数据但无法启动 | 检查数据卷完整性、PG 数据目录权限 |

---

## 相关文档

- [宿主机脚本部署](../../docs/deployment/02-script-host.md)
- [容器脚本部署](../../docs/deployment/03-script-container.md)
- [手动数据库部署](../../docs/deployment/05-database.md)
- [手动源码部署](../../docs/deployment/06-source.md)
- [手动 RPM 部署](../../docs/deployment/07-rpm.md)
- [手动容器部署](../../docs/deployment/08-container.md)
