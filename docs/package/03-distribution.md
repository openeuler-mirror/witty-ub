# 镜像分发与多架构发布

## 概述

镜像分发包括两部分：把某个 release 打成 `ARM64` / `X86-64` 双架构镜像并推送到
镜像仓；以及导出 tar、离线加载等操作。

**前后端分离部署**后，镜像按角色分布在**同一个 `witty-ub` 仓**下：单机全量用
`latest` / `<版本>`，后端、前端用 `backend` / `frontend`。每个 tag 都是多架构
`manifest list`（同一 tag 内含 `linux/amd64` + `linux/arm64`），不同架构机器拉
同一 tag 会自动选择对应架构。

底层的镜像构建（base、角色 target、前端原生构建）见
[01-docker-build.md](01-docker-build.md)。

## 命名与标签规则

`<repo>` 形如 `hub-harbor.oepkgs.net/neocopilot`。角色镜像复用同一 `witty-ub`
仓，用 tag 区分角色，与[分离部署文档](../deployment/08-container.md)中的
`docker pull .../witty-ub:backend`、`.../witty-ub:frontend` 保持一致。

- 单机全量镜像：`<repo>/witty-ub:<版本>` 与 `<repo>/witty-ub:latest`。
- 后端角色镜像：`<repo>/witty-ub:backend-<版本>` 与 `<repo>/witty-ub:backend`。
- 前端角色镜像：`<repo>/witty-ub:frontend-<版本>` 与
  `<repo>/witty-ub:frontend`。
- 基础镜像（构建用）：`<repo>/witty-ub-base`、
  `<repo>/witty-ub-base-backend`、`<repo>/witty-ub-base-frontend`。

### 版本号、标签、架构如何管理

- 版本号：以 release tag 为准（如 `v1.0.4-3`），`<版本>` 直接取该值，避免手写；
  发布流程从源码仓库的 release / tag 拉取源码并据此生成镜像 tag。
- 不可变标签：`<版本>`、`backend-<版本>`、`frontend-<版本>`，对应某个具体发布，
  可用于可追溯回滚。
- 移动标签：`latest`（单机）、`backend`（后端）、`frontend`（前端）。每次发布后
  指向新版本，始终代表最新发布。
- 架构：由 `--platform linux/amd64,linux/arm64` 一次构建两个架构再合并，无需架构
  后缀标签。若历史兼容需要，才用 `docker buildx imagetools create` 生成
  `-x86_64` / `-aarch64` 指针。

## 前置条件

- `docker` + `docker buildx`，且使用 `docker-container` driver（默认 `docker`
  driver 不支持交叉构建）。
- 交叉构建依赖 QEMU / binfmt；`docker buildx create --driver docker-container` 的
  bootstrap 会自动注册，无需单独安装。
- 目标镜像仓需允许创建子仓库并推送（Harbor 项目权限；若无建仓权限需先建好
  仓库）。
- 构建主机需能访问依赖仓库；基础镜像的 base 也要能拉取。
- `src/web` 前端必须在**宿主机（原生架构）**构建，不能用 `--platform` 放进
  QEMU 模拟环境；`src/web/dist` 会被 COPY 进镜像。

## 一键脚本

[scripts/publish_split_release.sh](../../scripts/publish_split_release.sh)
会：构建前端（原生）→（可选）发布三个 base → 发布 `latest` / `backend` /
`frontend` 角色镜像 → 校验 manifest。凭据由操作者登录提供，不入库。

```bash
docker login <registry>

VERSION=v1.0.4-3 \
REGISTRY=hub-harbor.oepkgs.net \
PROJECT=neocopilot \
bash scripts/publish_split_release.sh
```

只发布应用镜像、复用已有 base（更快）：

```bash
VERSION=v1.0.4-3 PUBLISH_BASE=0 bash scripts/publish_split_release.sh
```

## 手动步骤（等价于脚本）

以下在源码根目录执行：`REG` 为 `hub-harbor.oepkgs.net/neocopilot`，
`VER` 为发布版本（如 `v1.0.4-3`），`PLATFORMS=linux/amd64,linux/arm64`。

### 1. 拉取 release 源码并构建前端

```bash
git clone --branch "$VER" --depth 1 <upstream-url> witty-ub-src
cd witty-ub-src

pushd src/web
npm ci --no-audit --no-fund && npm run build-only
popd
```

### 2. 登录并搭建 buildx

```bash
docker login "$REG"
docker buildx create --name witty-ub-builder --driver docker-container --use
docker buildx inspect --bootstrap
docker buildx use witty-ub-builder
```

### 3. 发布基础镜像（每个都是多架构）

```bash
docker buildx build --platform "$PLATFORMS" --push -f Dockerfile.base --target base           -t "$REG/witty-ub-base:latest"           -t "$REG/witty-ub-base:$VER" .
docker buildx build --platform "$PLATFORMS" --push -f Dockerfile.base --target base-backend    -t "$REG/witty-ub-base-backend:latest"    -t "$REG/witty-ub-base-backend:$VER" .
docker buildx build --platform "$PLATFORMS" --push -f Dockerfile.base --target base-frontend   -t "$REG/witty-ub-base-frontend:latest"   -t "$REG/witty-ub-base-frontend:$VER" .
```

> 三个 base 都要随发布一起重新构建，不要复用历史 base：应用镜像的
> `builder-cpp` 阶段要用 all-in-one base 里的 C++ 工具链，`all` / `frontend`
> 目标还要调用 base 里预装的 `uv`。复用旧 base 可能缺 `uv`，会导致 `uv sync`
> 失败（`exit 127: /root/.local/bin/uv 不存在`）。

### 4. 发布应用角色镜像

应用镜像引用仓库里的 base（`--build-arg`）。后端 / 前端目标内置 `WITTY_ROLE`，
部署端直接 `docker pull .../witty-ub:backend` 即可。

```bash
docker buildx build --platform "$PLATFORMS" --push \
  --build-arg BASE_IMAGE="$REG/witty-ub-base:$VER" \
  -t "$REG/witty-ub:latest" -t "$REG/witty-ub:$VER" .

docker buildx build --platform "$PLATFORMS" --push \
  --build-arg BASE_IMAGE="$REG/witty-ub-base:$VER" \
  --build-arg BASE_IMAGE_BACKEND="$REG/witty-ub-base-backend:$VER" \
  --target backend \
  -t "$REG/witty-ub:backend" -t "$REG/witty-ub:backend-$VER" .

docker buildx build --platform "$PLATFORMS" --push \
  --build-arg BASE_IMAGE="$REG/witty-ub-base:$VER" \
  --build-arg BASE_IMAGE_FRONTEND="$REG/witty-ub-base-frontend:$VER" \
  --target frontend \
  -t "$REG/witty-ub:frontend" -t "$REG/witty-ub:frontend-$VER" .
```

### 5. 校验

```bash
docker buildx imagetools inspect "$REG/witty-ub:$VER"    # 应为 OCI index，含 amd64+arm64
docker buildx imagetools inspect "$REG/witty-ub:backend"
docker buildx imagetools inspect "$REG/witty-ub:frontend"
```

或拉取到目标机验证：`docker run --rm --platform linux/arm64
.../witty-ub:latest uname -m`。

### 6. 更新移动标签

脚本在步骤 4 里已把 `latest`、`backend`、`frontend` 同时打成当前版本。若要单独
更新移动标签：

```bash
docker buildx imagetools create -t "$REG/witty-ub:latest"    "$REG/witty-ub:$VER"
docker buildx imagetools create -t "$REG/witty-ub:backend"   "$REG/witty-ub:backend-$VER"
docker buildx imagetools create -t "$REG/witty-ub:frontend"  "$REG/witty-ub:frontend-$VER"
```

## 导出 tar 与离线加载

### 导出

```bash
docker save "$REG/witty-ub:latest" -o witty-ub.tar
docker save "$REG/witty-ub:latest" | gzip > witty-ub.tar.gz
```

### 传输

```bash
scp witty-ub.tar user@target-host:/tmp/
rsync -av witty-ub.tar user@target-host:/tmp/
```

### 加载

```bash
docker load -i witty-ub.tar
gunzip -c witty-ub.tar.gz | docker load
```

离线部署完整流程：在有网络的机器 `docker save` 导出应用与 `pg15` 镜像，传到目标
机后 `docker load`，再 `bash deploy/docker/manage.sh` 部署。

## 环境与网络注意事项

- buildx 驱动：必须用 `docker-container` driver；默认 `docker` driver 无法交叉
  构建（报 `OCI exporter is not supported for the docker driver`）。
- 镜像源网络：`Dockerfile.base` 内 `pip install` 硬编码了 `mirrors.aliyun.com`。
  部分网络环境可能连不上该源。建议把 pip 源做成 `--build-arg PIP_INDEX_URL`，或
  改用目标环境可达的源。
- 前端必须原生构建：不要用 `--platform` 让 buildx 在模拟环境跑
  `npm run build-only`；应在宿主机先构建出 `src/web/dist`。`.dockerignore` 的
  `dist/` 会排除该目录，若 `COPY src/web/dist` 报错需放开这行。
- 角色镜像依赖 base：`backend` / `frontend` target 的运行时 base 必须先发布到
  仓库，否则全新机器拉不到。
- 磁盘空间：双架构构建 base 占用较大空间，预留 10GB+。
- 上传大层时镜像仓网络偶发中断（`broken pipe` / `connection reset`），buildx
  会自动重试；失败时重跑同一条 `buildx build --push` 即可（层已缓存，速度很快）。

## 下一步

- 部署 witty-ub → [deployment/02-script-host.md](../deployment/02-script-host.md) |
  [deployment/03-script-container.md](../deployment/03-script-container.md)
- 镜像构建 → [01-docker-build.md](01-docker-build.md)
- 分离部署拉取镜像 → [../deployment/08-container.md](../deployment/08-container.md)
