# Docker 镜像构建

## 概述

witty-ub 采用分层镜像架构：

| 镜像 | Dockerfile | 说明 |
| ------ | ----------- | ------ |
| `witty-ub-base` | `Dockerfile.base` target `base` | 全量基础镜像（C++ 工具链 + 全部依赖），用于构建 C++ 与单机镜像 |
| `witty-ub-base-backend` | `Dockerfile.base` target `base-backend` | 后端基础镜像（C++ 运行库 + latency venv，约 640MB） |
| `witty-ub-base-frontend` | `Dockerfile.base` target `base-frontend` | 前端基础镜像（Nginx + OpenCode + experience-skill venv，约 1.2GB） |
| `witty-ub:latest` | `Dockerfile` 默认 target | 单机全量应用镜像（All-in-One） |
| `witty-ub:backend` | `Dockerfile` target `backend` | 后端角色镜像（FastAPI + C++ 诊断工具 + 数据，约 670MB） |
| `witty-ub:frontend` | `Dockerfile` target `frontend` | 前端角色镜像（Nginx + OpenCode + web dist，约 1.3GB） |

首次构建 base 镜像需要 10-15 分钟，后续源码修改只需重建应用镜像（30 秒 - 2 分钟）。

---

## 前置条件

- Docker 17.05+（多阶段构建最低要求）
- Docker 19.03+ + buildx 插件（`--platform` 指定平台构建）
- Docker 20.10+ + buildx 插件（`--multi` 双架构构建）
- Node.js 18+ 和 npm（前端构建）
- Git

> 无 buildx 的低版本 Docker（< 19.03）可使用 `--platform local`（默认）或[方法三：纯 Docker 命令](#方法三纯-docker-命令)。脚本会自动检测 buildx 可用性并回退。

```bash
git clone https://gitcode.com/openeuler/witty-ub.git
cd witty-ub
```

---

## 方法一：build.sh 脚本（推荐）

```bash
# 本地构建（自动构建 base + app）
bash build.sh

# 指定版本
bash build.sh --version v1.0.0
```

脚本自动执行：前端构建 → base 镜像 → 应用镜像。

### 构建参数

| 参数 | 说明 |
| ------ | ------ |
| `--version <tag>` | 镜像标签（默认 `latest`） |
| `--platform <platform>` | 目标平台：`local`、`linux/amd64`、`linux/arm64` |
| `--multi` | 双架构构建（x86_64 + arm64），需配合 `--registry` |
| `--registry <url>` | 镜像仓库地址（多架构构建必需） |
| `--rpm` | 使用 RPM 包构建 → [02-rpm-build.md](02-rpm-build.md) |
| `--repo-url <url>` | RPM 仓库地址（与 `--rpm` 配合） |

### 多架构构建

```bash
# 双架构构建并推送到仓库
bash build.sh --multi --registry hub-harbor.oepkgs.net/neocopilot/witty-ub

# 指定版本
bash build.sh --multi --registry hub-harbor.oepkgs.net/neocopilot/witty-ub --version v1.0.0
```

> 多架构构建需要 QEMU 支持（脚本自动安装），结果必须推送到镜像仓库。低版本 Docker（< 19.03，无 buildx）不支持双架构构建，需在各架构机器上分别构建后推送至同一 tag。

---

## 方法二：docker compose

适用于开发调试。

> 需要 Docker Compose。Docker 20.10+ 内置 `docker compose`（插件式 v2）；低版本需单独安装 `docker-compose`（v1，命令为 `docker-compose`）。

### 前置条件

```bash
# 1. 构建 base 镜像
docker build -f Dockerfile.base --target base -t witty-ub-base:latest .

# 2. 构建前端
cd src/web
npm ci --registry=https://mirrors.huaweicloud.com/repository/npm/
npm run build-only
cd ../..

# 3. 切换到 default builder（需要 buildx，无 buildx 可跳过）
docker buildx use default 2>/dev/null || true
```

### 构建

```bash
# 构建并启动
docker compose up -d --build        # Docker 20.10+（Compose v2）
# docker-compose up -d --build      # 低版本（Compose v1）

# 仅构建
docker compose build

# 不使用缓存
docker compose build --no-cache
```

---

## 方法三：纯 Docker 命令

适用于低版本 Docker 环境（无 buildx、无 Compose v2）。

```bash
# 1. 构建 base 镜像（全量，单机镜像与 C++ 编译需要）
docker build -f Dockerfile.base --target base -t witty-ub-base:latest .

# 2. 构建前端（必须在本地环境，避免 QEMU 性能问题）
cd src/web
npm ci --registry=https://mirrors.huaweicloud.com/repository/npm/
npm run build-only
cd ../..

# 3. 构建应用镜像
docker build -f Dockerfile -t witty-ub:latest .            # 单机全量

# 4. 分离部署角色镜像（可选，需先构建对应 base）
docker build -f Dockerfile.base --target base-backend -t witty-ub-base-backend:latest .
docker build -f Dockerfile.base --target base-frontend -t witty-ub-base-frontend:latest .
docker build -f Dockerfile --target backend -t witty-ub:backend .
docker build -f Dockerfile --target frontend -t witty-ub:frontend .
```

---

## 前端构建说明

前端代码（`src/web`）必须在本地环境构建：

- 避免 QEMU 模拟环境下的性能问题和内存不足
- 构建产物 `src/web/dist` 通过 COPY 指令打包到镜像

---

## 构建时间参考

| 场景 | 首次 | 后续 |
| ------ | ------ | ------ |
| 单架构 | 10-15 分钟 | 30 秒 - 2 分钟 |
| 双架构 | 15-30 分钟 | 5-10 分钟 |
| 仅前端修改 | 1-2 分钟 | 1-2 分钟 |

---

## 验证

```bash
docker images | grep witty-ub
```

---

## 下一步

- 推送镜像 → [03-distribution.md](03-distribution.md)
- RPM 包构建 → [02-rpm-build.md](02-rpm-build.md)
