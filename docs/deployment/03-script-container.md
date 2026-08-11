# 容器脚本部署

## 概述

使用 `deploy/docker/manage.sh` 一键完成容器化部署，自动处理镜像拉取、容器创建、服务启动、健康检查等全流程。

适合生产环境。

---

## 前置条件

- Docker 18.09+ 已安装并运行
- 至少 4GB 内存、10GB 可用磁盘空间
- 有权限拉取镜像（或本地已有镜像）

```bash
# 验证 Docker 环境
docker info
```

---

## 交互式部署

```bash
bash deploy/docker/manage.sh
# 选择 [1] 一键安装
```

选择 `[1] 一键安装` 即可自动完成：

```
  [PG]    拉取镜像 → 创建网络 → 创建数据卷 → 启动容器 → 等待健康
  [witty] 拉取镜像 → 验证 → 创建网络/数据卷 → 启动 → 等待健康 → 验证
```

---

## 离线部署

```bash
# 在有网络的机器导出镜像
docker save -o witty-ub.tar hub-harbor.oepkgs.net/neocopilot/witty-ub:latest
docker save -o pg15.tar quay.io/sclorg/postgresql-15-c9s:latest

# 传输并导入
scp witty-ub.tar pg15.tar root@<目标机器>:/tmp/
docker load -i witty-ub.tar && docker load -i pg15.tar

# 执行部署
bash deploy/docker/manage.sh
```

---

## 配置说明

### 配置文件 pg.conf

所有脚本共用 `deploy/pg.conf`，修改后全局生效：

```bash
vi deploy/pg.conf
```

常用配置：

```conf
# witty-ub
WITTY_HOST_PORT="32412"              # 宿主机端口
WITTY_EXTRA_MOUNTS="/home:/home:ro"   # 额外挂载

# PostgreSQL
PG_PORT="15432"                       # 宿主机端口
PG_HOST_IN_CONTAINER=""               # 容器内访问，留空自动检测
PG_PORT_IN_CONTAINER=""
PG_USER="witty-ub"
PG_PASSWORD="witty-ub"
PG_DATABASE="witty-ub"
```

### 环境变量覆盖

通过环境变量临时覆盖 `pg.conf` 中的配置：

```bash
WITTY_HOST_PORT=8080 bash deploy/docker/manage.sh
WITTY_IMAGE=my-custom:v1 bash deploy/docker/manage.sh
PG_HOST_IN_CONTAINER=172.18.0.1 bash deploy/docker/manage.sh
```

---

## 验证部署

```bash
bash deploy/docker/manage.sh
# 选择 [10] 查看状态

curl http://localhost:32412/health_check
```

浏览器访问：`http://<IP>:32412`

---

## 已知问题

- **镜像拉取失败**：检查网络、镜像仓库地址、本地 tag 是否已设置
- **容器启动后健康检查失败**：`docker logs witty-ub` 查看日志
- **PG 连接被拒**：确认 PG 容器状态 `docker ps | grep postgres`
- **端口冲突**：`ss -tlnp | grep <端口>` 检查占用

---

## 后续步骤

- 脚本详细说明 → [../../deploy/docker/README.md](../../deploy/docker/README.md)
- 手动数据库部署 → [05-database.md](05-database.md)
- 手动源码部署 → [06-source.md](06-source.md)
- 手动 RPM 部署 → [07-rpm.md](07-rpm.md)
- 手动容器部署 → [08-container.md](08-container.md)
