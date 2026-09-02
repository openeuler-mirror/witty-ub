# PostgreSQL 数据库部署（手动）

## 概述

本文档介绍不依赖部署脚本，手动部署 PostgreSQL 数据库的方法。PG 支持容器化和 RPM 两种部署方式。

> 如果使用脚本部署，请参考 [宿主机脚本部署](02-script-host.md) 或 [容器脚本部署](03-script-container.md)。

### 版本要求

- PostgreSQL 15.x
- 数据库名：`witty-ub`
- 用户名：`witty-ub`
- 密码：`witty-ub`

---

## 获取镜像

```bash
docker pull quay.io/sclorg/postgresql-15-c9s:latest
```

## 方式一：容器化部署（推荐）

### 手动 docker run

```bash
# 创建网络
docker network create witty-ub-network

# 创建数据卷
docker volume create pg15-data

# 启动 PG 容器
docker run -d \
  --name postgres \
  --restart unless-stopped \
  -p 15432:5432 \
  -v pg15-data:/var/lib/pgsql/data \
  -e POSTGRESQL_USER=witty-ub \
  -e POSTGRESQL_PASSWORD=witty-ub \
  -e POSTGRESQL_DATABASE=witty-ub \
  -e POSTGRESQL_SHARED_BUFFERS=2GB \
  -e POSTGRESQL_EFFECTIVE_CACHE_SIZE=6GB \
  -e POSTGRESQL_MAX_CONNECTIONS=200 \
  --health-cmd="pg_isready -U witty-ub -d witty-ub" \
  --health-interval=30s \
  --health-timeout=10s \
  --health-retries=3 \
  --health-start-period=40s \
  --network witty-ub-network \
  quay.io/sclorg/postgresql-15-c9s:latest
```

> `shared_buffers` 建议为物理内存的 25%，`effective_cache_size` 建议为 75%。

### 使用 docker compose

```yaml
version: '3.8'

services:
  postgres:
    image: quay.io/sclorg/postgresql-15-c9s:latest
    container_name: postgres
    restart: unless-stopped
    ports:
      - "15432:5432"
    environment:
      - POSTGRESQL_USER=witty-ub
      - POSTGRESQL_PASSWORD=witty-ub
      - POSTGRESQL_DATABASE=witty-ub
      - POSTGRESQL_SHARED_BUFFERS=2GB
      - POSTGRESQL_EFFECTIVE_CACHE_SIZE=6GB
      - POSTGRESQL_MAX_CONNECTIONS=200
    volumes:
      - pg15-data:/var/lib/pgsql/data
    healthcheck:
      test: ["CMD", "pg_isready", "-U", "witty-ub", "-d", "witty-ub"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s
    networks:
      - witty-ub-network

volumes:
  pg15-data:

networks:
  witty-ub-network:
```

```bash
docker compose up -d
```

### 验证

```bash
# 查看容器
docker ps | grep postgres

# 健康状态
docker inspect --format='{{.State.Health.Status}}' postgres

# 测试连接
docker exec postgres pg_isready -U witty-ub -d witty-ub

# 查看日志
docker logs postgres
```

---

## 方式二：RPM 包部署

RPM 方式安装的 PG 默认监听 5432 端口，与 RPM 部署的 witty-ub 读取的 `PG_PORT_RPM` 默认值一致。

### 手动安装步骤

```bash
# 安装
sudo yum install -y postgresql15-server postgresql

# 初始化
sudo /usr/pgsql-15/bin/postgresql-15-setup initdb

# 配置
sudo vi /var/lib/pgsql/15/data/postgresql.conf
# 添加/修改: listen_addresses = '*', port = 5432

# 认证
sudo vi /var/lib/pgsql/15/data/pg_hba.conf
# 添加: host all all 0.0.0.0/0 md5

# 启动
sudo systemctl start postgresql-15
sudo systemctl enable postgresql-15

# 创建用户和数据库
sudo -u postgres psql -c "CREATE USER witty-ub WITH PASSWORD 'witty-ub';"
sudo -u postgres psql -c "CREATE DATABASE witty-ub OWNER witty-ub;"
```

### 验证

```bash
# 服务状态
sudo systemctl status postgresql-15

# 测试连接
psql -h 127.0.0.1 -p 5432 -U witty-ub -d witty-ub

# 监听端口
ss -tlnp | grep postgres
```

---

## witty-ub 连接 PG

### PG 为容器（同网络）

```conf
PG_HOST_IN_CONTAINER=postgres    # 容器名作为主机
PG_PORT_IN_CONTAINER=5432
```

### PG 为 RPM（宿主机）

```bash
# 获取 Docker 网关 IP
docker network inspect witty-ub-network --format '{{(index .IPAM.Config 0).Gateway}}'
# 典型: 172.18.0.1
```

```conf
PG_HOST_IN_CONTAINER=172.18.0.1
PG_PORT_IN_CONTAINER=5432
```

---

## 卸载

### 容器化

```bash
docker stop postgres && docker rm postgres
docker volume rm pg15-data    # 删除数据（谨慎）
```

### RPM

```bash
sudo systemctl stop postgresql-15
sudo systemctl disable postgresql-15
sudo yum remove -y postgresql15-server
# 删除数据: sudo rm -rf /var/lib/pgsql/15/data
```

---

## 常用命令

```bash
# 容器方式
docker logs -f postgres
docker exec -it postgres psql -U witty-ub -d witty-ub

# RPM 方式
journalctl -u postgresql-15 -f
```

---

## 后续步骤

- 宿主机脚本部署 → [02-script-host.md](02-script-host.md)
- 容器脚本部署 → [03-script-container.md](03-script-container.md)
- 手动源码部署 → [06-source.md](06-source.md)
- 手动 RPM 部署 → [07-rpm.md](07-rpm.md)
- 手动容器部署 → [08-container.md](08-container.md)
