<!-- Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved. -->
<!-- witty-ub is licensed under the Mulan PSL v2. -->

# 2. 镜像构建、上传与打包

> 返回 [首页](Home.md)

## 获取源码

```bash
git clone <repository-url>
cd witty-ub
```

---

## 构建镜像

首次构建需要 10-15 分钟（主要是安装依赖和 OpenCode），后续源码改动后重建只需 30 秒 - 2 分钟（利用缓存）。

> **新增服务说明**：Witty-UB 容器现在集成了 **OpenCode** 服务（端口 4096），用于提供 AI 辅助诊断功能。OpenCode 在 base 镜像构建时安装（避免 QEMU 环境问题），通过 MCP 协议与 latency 插件交互。

> **前端构建说明**：前端代码在本地环境构建（原生架构，速度快），构建产物通过 COPY 指令打包到镜像中，避免在 QEMU 模拟环境下构建导致的性能问题和内存不足。

### 方法一：使用 build.sh 脚本（推荐）

```bash
# 本地构建（自动识别当前架构）
bash build.sh

# 完整构建（包含 base 镜像）
bash build.sh

# 仅构建应用镜像（依赖已存在时）
docker build -f Dockerfile -t witty-ub:latest .
```

### 方法二：使用 RPM 包构建（推荐用于生产环境）

使用 RPM 包构建无需源码编译，直接安装 witty-ub RPM 包，构建速度更快。**使用 `--rpm` 时必须提供 `--repo-url` 参数**，用户只需输入到子目录级别，脚本自动拼接 `everything/$basearch/`。

```bash
# 本地构建（使用 RPM 包，必须提供 --repo-url）
bash build.sh --rpm --repo-url http://121.36.84.172/dailybuild/EBS-openEuler-24.03-LTS-SP3/<子目录>

# 指定架构构建（使用 RPM 包）
bash build.sh --rpm --platform linux/amd64 --repo-url http://121.36.84.172/dailybuild/EBS-openEuler-24.03-LTS-SP3/<子目录>
bash build.sh --rpm --platform linux/arm64 --repo-url http://121.36.84.172/dailybuild/EBS-openEuler-24.03-LTS-SP3/<子目录>

# 双架构构建并推送到仓库（使用 RPM 包）
bash build.sh --rpm --multi --registry hub-harbor.oepkgs.net/neocopilot/witty-ub --repo-url http://121.36.84.172/dailybuild/EBS-openEuler-24.03-LTS-SP3/<子目录>
```

**RPM 构建方式说明**：

| 项目 | 说明 |
|------|------|
| **基础镜像** | `openeuler/openeuler:24.03-lts` |
| **RPM 仓库** | 用户通过 `--repo-url` 指定，脚本自动拼接 `everything/$basearch/` |
| **安装方式** | `yum install -y witty-ub` |
| **构建时间** | 约 5-10 分钟（首次），后续重建约 1-2 分钟 |

**repo-url 参数说明**：

- 用户只需输入到子目录级别，如：`http://121.36.84.172/dailybuild/EBS-openEuler-24.03-LTS-SP3/<子目录>`
- 脚本自动拼接完整路径：`http://121.36.84.172/dailybuild/EBS-openEuler-24.03-LTS-SP3/<子目录>/everything/$basearch/`
- `$basearch` 在 yum 执行时自动替换为当前架构（`x86_64` 或 `aarch64`）

**源码构建 vs RPM 构建对比**：

| 维度 | 源码构建 | RPM 构建 |
|------|---------|---------|
| **构建时间** | 15-20 分钟（首次） | 5-10 分钟（首次） |
| **代码更新** | 支持热更新 | 需要重新打包 RPM |
| **版本一致性** | 依赖源码版本 | 与生产环境 RPM 版本一致 |
| **调试便捷性** | 源码在镜像中 | 源码不在镜像中 |
| **适用场景** | 开发、测试 | 生产环境 |

### 方法三：使用 docker compose 构建（开发调试）

> **注意**：此方法适用于开发调试，需要先构建 base 镜像和前端代码。

**前置条件**：
1. 已构建 base 镜像：`docker build -f Dockerfile.base -t witty-ub-base:latest .`
2. 已构建前端代码：在 `src/web` 目录执行 `npm run build-only`
3. 当前使用 `default` builder（确保能访问本地镜像）：`docker buildx use default`

```bash
# 切换到 default builder（确保能访问本地镜像）
docker buildx use default

# 完整构建（构建镜像并启动容器）
docker compose up -d --build

# 仅构建镜像（不启动容器）
docker compose build

# 使用 BuildKit 加速构建
DOCKER_BUILDKIT=1 docker compose build

# 不使用缓存重新构建
docker compose build --no-cache
```

**适用场景**：
- 开发调试时快速重建容器
- 修改代码后快速验证
- 不需要多架构支持

**注意事项**：
- docker-compose.yml 中配置了 `build` 字段，会直接使用 `Dockerfile` 构建
- 需要确保 `witty-ub-base:latest` 本地镜像已存在
- 需要确保 `src/web/dist` 前端构建目录已存在

### 方法四：使用纯 Docker 命令构建（低版本 Docker）

> **注意**：此方法适用于不支持 docker compose 的低版本 Docker 环境。

**前置条件**：
1. 当前使用 `default` builder：`docker buildx use default`

```bash
# 切换到 default builder（确保能访问本地镜像）
docker buildx use default

# 第一步：构建依赖基座镜像
docker build -f Dockerfile.base -t witty-ub-base:latest .

# 第二步：构建前端代码（在本地环境执行，避免 QEMU 性能问题）
cd src/web
npm ci --registry=https://mirrors.huaweicloud.com/repository/npm/
npm run build-only
cd ../..

# 第三步：构建应用镜像（基于 base 镜像）
docker build -f Dockerfile -t witty-ub:latest .

# 使用 BuildKit 加速构建
DOCKER_BUILDKIT=1 docker build -f Dockerfile -t witty-ub:latest .

# 不使用缓存重新构建
docker build -f Dockerfile.base -t witty-ub-base:latest --no-cache .
docker build -f Dockerfile -t witty-ub:latest --no-cache .
```

**适用场景**：
- 低版本 Docker 环境（不支持 docker compose）
- 需要精细控制构建过程
- CI/CD 流水线集成

**注意事项**：
- 需要手动执行前端构建步骤
- 需要确保 `witty-ub-base:latest` 本地镜像已存在
- 构建完成后需要手动启动容器

### 配置构建参数（可选）

创建 `.env` 文件自定义配置:

```bash
COMPOSE_PROJECT_NAME=witty-ub
DOCKER_BUILDKIT=1
```

---

## 多架构构建

### 架构支持

- **x86_64**: Linux AMD64
- **arm64/aarch64**: Linux ARM64

### 构建方式

#### 本地架构构建（默认）

```bash
bash build.sh
```

#### 指定单架构构建

使用 `--platform` 参数指定目标架构，脚本使用 default builder（能访问本地镜像缓存，速度更快）：

```bash
bash build.sh --platform linux/arm64
bash build.sh --platform linux/amd64
```

#### 双架构构建（需镜像仓库）

**镜像仓库**是用于存储和管理 Docker 镜像的服务（如 Harbor、Docker Hub、GitLab Registry 等）。本项目使用的仓库地址为：`hub-harbor.oepkgs.net/neocopilot/witty-ub`

**为什么双架构构建需要镜像仓库**：
- Docker Buildx 的多架构构建结果是一个 **manifest list**（清单列表）
- manifest list 无法直接加载到本地 Docker 引擎，必须推送到远程仓库
- 当不同架构的机器拉取同一镜像时，Docker 会根据宿主机架构自动选择对应的镜像层

**双架构构建流程**：

1. **构建 base 镜像**：先构建包含所有依赖的 base 镜像并推送到 registry
2. **构建 app 镜像**：从 registry 拉取 base 镜像，构建应用代码并推送到 registry
3. **创建 manifest list**：自动创建多架构清单，支持按架构自动选择

**标签是如何自动处理的**：

`build.sh` 会自动根据 `--registry` 参数拼接镜像标签：

| 镜像类型 | 本地构建标签 | 推送仓库后标签 |
|----------|-------------|---------------|
| base 镜像 | `witty-ub-base:latest` | `hub-harbor.oepkgs.net/neocopilot/witty-ub-base:latest` |
| app 镜像 | `witty-ub:latest` | `hub-harbor.oepkgs.net/neocopilot/witty-ub:latest` |

```bash
# 构建双架构镜像并推送到仓库（标签自动处理）
bash build.sh --multi --registry hub-harbor.oepkgs.net/neocopilot/witty-ub

# 在 x86_64 机器上拉取（自动获取 x86_64 架构镜像）
docker pull hub-harbor.oepkgs.net/neocopilot/witty-ub:latest

# 在 arm64 机器上拉取（自动获取 arm64 架构镜像）
docker pull hub-harbor.oepkgs.net/neocopilot/witty-ub:latest
```

**如果没有镜像仓库**：可以分别构建单架构镜像并通过 tar 包分发（见下文"推送不同架构的镜像"）

### 构建脚本参数

| 参数 | 说明 |
|------|------|
| `--multi` | 启用双架构构建 (x86_64 + arm64) |
| `--registry <url>` | 指定镜像仓库地址（双架构构建必需） |
| `--platform <platform>` | 指定目标平台: `local`, `linux/amd64`, `linux/arm64` |
| `--rpm` | 使用 RPM 包构建（替代源码编译），必须配合 `--repo-url` 使用 |
| `--repo-url <url>` | 指定 RPM 仓库地址（使用 `--rpm` 时必需），只需输入到子目录级别 |
| `-h, --help` | 显示帮助信息 |

### 使用注意事项

1. **首次使用多架构构建**: 需要 QEMU 支持，脚本会自动安装
2. **双架构镜像**: 必须推送到镜像仓库（Docker 限制）
3. **单架构构建**: 使用 default builder，能访问本地镜像缓存，速度更快
4. **前端构建**: 在本地环境构建，避免 QEMU 模拟环境下的性能问题
5. **OpenCode 安装**: 在 base 镜像中安装，避免 QEMU 环境下的 npm 安装失败
6. **运行时**: Docker 会自动拉取匹配宿主机架构的镜像

### 构建时间参考

| 构建方式 | 首次时间 | 后续时间（无 Dockerfile.base 修改） |
|---------|---------|-----------------------------------|
| 单架构构建 | 10-15 分钟 | 30 秒 - 2 分钟 |
| 双架构构建 | 15-30 分钟 | 5-10 分钟 |
| 仅修改前端代码 | 1-2 分钟 | 1-2 分钟 |
| 仅修改配置文件 | < 30 秒 | < 30 秒 |

> **提示**：双架构构建使用 QEMU 模拟环境，速度比单架构慢 2-3 倍。日常开发推荐使用单架构构建，发布时使用双架构构建。

---

## 上传镜像到仓库

### 登录镜像仓库

```bash
docker login <registry-url>
```

### 为镜像打标签

```bash
docker tag witty-ub:latest <registry-url>/witty-ub:latest

# 例如：
docker tag witty-ub:latest hub-harbor.oepkgs.net/neocopilot/witty-ub:latest
```

### 推送镜像

```bash
docker push <registry-url>/witty-ub:latest

# 例如：
docker push hub-harbor.oepkgs.net/neocopilot/witty-ub:latest
```

### 推送不同架构的镜像

如果需要分别构建不同架构的镜像（例如在不同机器上构建），可以按以下步骤操作：

```bash
# 构建并推送 x86_64 架构
bash build.sh --platform linux/amd64
docker tag witty-ub:latest <registry-url>/witty-ub-x86_64:latest
docker push <registry-url>/witty-ub-x86_64:latest

# 构建并推送 arm64 架构
bash build.sh --platform linux/arm64
docker tag witty-ub:latest <registry-url>/witty-ub-aarch64:latest
docker push <registry-url>/witty-ub-aarch64:latest

# 合并为 manifest list（支持按架构自动选择）
docker buildx imagetools create \
    -t <registry-url>/witty-ub:latest \
    <registry-url>/witty-ub-x86_64:latest \
    <registry-url>/witty-ub-aarch64:latest
```

> **说明**：合并后，当不同架构的机器拉取 `witty-ub:latest` 时，Docker 会根据宿主机架构自动选择对应的镜像。

### 验证推送结果

```bash
# 查看本地镜像
docker images | grep witty-ub

# 从仓库拉取验证
docker pull <registry-url>/witty-ub:latest
```

---

## 打包镜像为 tar 包

### 导出镜像

```bash
# 导出单个镜像
docker save witty-ub:latest -o witty-ub.tar

# 导出多个镜像（包含 base 镜像）
docker save witty-ub:latest witty-ub-base:latest -o witty-ub.tar

# 导出并压缩
docker save witty-ub:latest | gzip > witty-ub.tar.gz
```

### 查看导出的镜像内容

```bash
# 列出 tar 包中的镜像
docker load --input witty-ub.tar --quiet | head -n 5

# 或使用 tar 命令查看
tar -tf witty-ub.tar | grep manifest
```

### 传输 tar 包

```bash
# 使用 scp 传输到目标机器
scp witty-ub.tar user@target-host:/path/to/destination/

# 使用 rsync（大文件推荐）
rsync -av witty-ub.tar user@target-host:/path/to/destination/
```

### 从 tar 包加载镜像

在目标机器上执行:

```bash
# 加载镜像
docker load -i witty-ub.tar

# 加载压缩的镜像
gunzip -c witty-ub.tar.gz | docker load

# 验证加载结果
docker images | grep witty-ub
```

---

## 下一步

- 继续阅读: [3. 镜像拉取、启动与使用](03-pull-and-run.md)
- 返回 [首页](Home.md)
