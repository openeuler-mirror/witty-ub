# RPM 包构建

## 概述

RPM 包构建适用于生产环境，无需源码编译，构建速度更快。

| 项目 | 说明 |
|------|------|
| 基础镜像 | `openeuler/openeuler:24.03-lts` |
| 安装方式 | `yum install -y witty-ub` |
| 构建时间 | 首次 5-10 分钟，后续 1-2 分钟 |

---

## 前置条件

- RPM 仓库已配置（包含 witty-ub 包）
- Docker 20.10+

---

## 使用 build.sh 构建

```bash
# 本地构建（必须提供 --repo-url）
bash build.sh --rpm --repo-url http://121.36.84.172/dailybuild/EBS-openEuler-24.03-LTS-SP3/<子目录>

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
FROM openeuler/openeuler:24.03-lts

ARG REPO_URL

# 配置 RPM 仓库
RUN echo "[witty-ub]" > /etc/yum.repos.d/witty-ub.repo && \
    echo "baseurl=$REPO_URL" >> /etc/yum.repos.d/witty-ub.repo && \
    ...

# 安装 witty-ub 和依赖
RUN yum install -y witty-ub nodejs npm && ...

# 安装 OpenCode
RUN npm install -g opencode-ai --registry=https://mirrors.huaweicloud.com/repository/npm/

# 暴露端口
EXPOSE 8080 9772 4096
```

---

## 源码构建 vs RPM 构建

| 维度 | 源码构建 | RPM 构建 |
|------|---------|---------|
| 构建时间 | 15-20 分钟（首次） | 5-10 分钟（首次） |
| 代码更新 | 支持热更新 | 需要重新打包 RPM |
| 版本一致性 | 依赖源码版本 | 与生产环境 RPM 版本一致 |
| 调试便捷性 | 源码在镜像中 | 源码不在镜像中 |
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
