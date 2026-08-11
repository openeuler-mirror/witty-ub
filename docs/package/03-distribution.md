# 镜像分发

## 概述

镜像分发包括推送到仓库、导出 tar 包、离线加载等操作。

---

## 推送到镜像仓库

### 登录仓库

```bash
docker login <registry-url>
```

### 打标签

```bash
# 本地镜像打标签
docker tag witty-ub:latest hub-harbor.oepkgs.net/neocopilot/witty-ub:latest

# 指定版本
docker tag witty-ub:v1.0.0 hub-harbor.oepkgs.net/neocopilot/witty-ub:v1.0.0
```

### 推送镜像

```bash
docker push hub-harbor.oepkgs.net/neocopilot/witty-ub:latest
```

### 验证

```bash
# 查看本地镜像
docker images | grep witty-ub

# 从仓库拉取验证
docker pull hub-harbor.oepkgs.net/neocopilot/witty-ub:latest
```

---

## 多架构镜像合并

如果需要分别构建不同架构的镜像，可以合并为 manifest list：

```bash
# 构建并推送 x86_64
bash build.sh --platform linux/amd64
docker tag witty-ub:latest hub-harbor.oepkgs.net/neocopilot/witty-ub-x86_64:latest
docker push hub-harbor.oepkgs.net/neocopilot/witty-ub-x86_64:latest

# 构建并推送 arm64
bash build.sh --platform linux/arm64
docker tag witty-ub:latest hub-harbor.oepkgs.net/neocopilot/witty-ub-aarch64:latest
docker push hub-harbor.oepkgs.net/neocopilot/witty-ub-aarch64:latest

# 合并为 manifest list
docker buildx imagetools create \
    -t hub-harbor.oepkgs.net/neocopilot/witty-ub:latest \
    hub-harbor.oepkgs.net/neocopilot/witty-ub-x86_64:latest \
    hub-harbor.oepkgs.net/neocopilot/witty-ub-aarch64:latest
```

合并后，不同架构的机器拉取同一镜像时会自动选择对应架构版本。

---

## 导出 tar 包

### 导出镜像

```bash
# 导出单个镜像
docker save witty-ub:latest -o witty-ub.tar

# 导出并压缩
docker save witty-ub:latest | gzip > witty-ub.tar.gz

# 导出多个镜像
docker save witty-ub:latest pg15:latest -o all-images.tar
```

### 传输 tar 包

```bash
# 使用 scp
scp witty-ub.tar user@target-host:/tmp/

# 使用 rsync（大文件推荐）
rsync -av witty-ub.tar user@target-host:/tmp/
```

---

## 离线加载镜像

### 从 tar 包加载

```bash
# 加载 tar 包
docker load -i witty-ub.tar

# 加载压缩的 tar 包
gunzip -c witty-ub.tar.gz | docker load

# 验证
docker images | grep witty-ub
```

---

## 离线部署流程

完整离线部署流程：

```bash
# 1. 在有网络的机器上导出镜像
docker save -o witty-ub.tar hub-harbor.oepkgs.net/neocopilot/witty-ub:latest
docker save -o pg15.tar quay.io/sclorg/postgresql-15-c9s:latest

# 2. 传输到目标机器
scp witty-ub.tar pg15.tar root@<目标机器>:/tmp/

# 3. 在目标机器上加载镜像
docker load -i /tmp/witty-ub.tar
docker load -i /tmp/pg15.tar

# 4. 使用 manage.sh 部署
bash deploy/docker/manage.sh
```

---

## 验证

```bash
# 查看本地镜像
docker images

# 测试运行
docker run --rm witty-ub:latest echo "Image loaded successfully"
```

---

## 下一步

- 部署 witty-ub → [deployment/02-script-host.md](../deployment/02-script-host.md) | [deployment/03-script-container.md](../deployment/03-script-container.md)
- Docker 镜像构建 → [01-docker-build.md](01-docker-build.md)
