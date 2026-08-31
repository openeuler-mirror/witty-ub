# 基于 RPM 仓库构建镜像

## 概述

`build.sh --rpm` 从 RPM 仓库安装 witty-ub 子包并构建 Docker 镜像，无需本地源码编译，与生产环境 RPM 版本一致。支持三种角色镜像：`latest`（单机全量）、`backend`（后端）、`frontend`（前端）。

> RPM 包本身的构建（spec + rpmbuild）在 openEuler 打包仓 src-openeuler/witty-ub 维护，不在本仓库。RPM 部署方式见[部署文档](../deployment/07-rpm.md)。

| 项目 | 说明 |
| ------ | ------ |
| 基础镜像 | `openeuler/openeuler:24.03-lts-sp4` |
| 安装内容 | `all`: meta 包 `witty-ub`；`backend`: `witty-ub-backend`；`frontend`: `witty-ub-web` |
| 构建时间 | 首次 5-10 分钟，后续 1-2 分钟 |

---

## 前置条件

- RPM 仓库已配置（包含 witty-ub 包）
- Docker 20.10+

---

## 使用 build.sh 构建

```bash
# 单机全量镜像（必须提供 --repo-url）
bash build.sh --rpm --repo-url http://121.36.84.172/dailybuild/EBS-openEuler-24.03-LTS-SP3/<子目录>

# 角色镜像（分离部署）
bash build.sh --rpm --rpm-role backend --repo-url http://...
bash build.sh --rpm --rpm-role frontend --repo-url http://...

# 指定架构
bash build.sh --rpm --platform linux/amd64 --repo-url http://...
bash build.sh --rpm --platform linux/arm64 --repo-url http://...

# 双架构构建并推送
bash build.sh --rpm --multi --registry hub-harbor.oepkgs.net/neocopilot/witty-ub --repo-url http://...

# 指定版本
bash build.sh --rpm --version v1.0.0 --repo-url http://...
```

### repo-url 参数说明

- 用户只需输入到子目录级别：`http://121.36.84.172/dailybuild/EBS-openEuler-24.03-LTS-SP3/<子目录>`
- 脚本自动拼接：`<子目录>/everything/$basearch/`
- `$basearch` 在 yum 执行时自动替换为 `x86_64` 或 `aarch64`

---

## Dockerfile.rpm 说明

```dockerfile
FROM openeuler/openeuler:24.03-lts-sp4 AS repo

ARG REPO_URL

# 配置 RPM 仓库
RUN echo "[witty-ub]" > /etc/yum.repos.d/witty-ub.repo && \
    echo "baseurl=$REPO_URL" >> /etc/yum.repos.d/witty-ub.repo && \
    ...

# target all：安装 meta 包（拉入全部子包）
RUN yum install -y witty-ub nodejs npm && ...

# target backend：仅安装后端子包
RUN yum install -y witty-ub-backend && ...

# target frontend：安装前端子包 + OpenCode
RUN yum install -y witty-ub-web nodejs npm && ...
RUN npm install -g opencode-ai ...
```

| 镜像 | target | 安装子包 | 用途 |
| ------ | ------ | --------- | ------ |
| `witty-ub:latest` | `all`（默认） | `witty-ub`（meta） | 单机 All-in-One 部署 |
| `witty-ub:backend` | `backend` | `witty-ub-backend` | 分离部署的后端节点 |
| `witty-ub:frontend` | `frontend` | `witty-ub-web` | 分离部署的前端节点 |

镜像用法与源码构建的角色镜像一致，见[容器化部署](../deployment/08-container.md)。

---

## 源码构建 vs RPM 构建

| 维度 | 源码构建 | RPM 构建 |
| ------ | --------- | --------- |
| 构建时间 | 15-20 分钟（首次） | 5-10 分钟（首次） |
| 代码更新 | 支持热更新 | 需要 RPM 仓库更新 |
| 版本一致性 | 依赖源码版本 | 与生产环境 RPM 版本一致 |
| 角色镜像 | 支持 backend/frontend target | 支持 backend/frontend target |
| 适用场景 | 开发、测试 | 生产环境 |

---

## 验证

```bash
docker images | grep witty-ub
```

---

## 下一步

- 推送镜像 → [03-distribution.md](03-distribution.md)
- Docker 镜像构建 → [01-docker-build.md](01-docker-build.md)
- RPM 部署 → [../deployment/07-rpm.md](../deployment/07-rpm.md)
