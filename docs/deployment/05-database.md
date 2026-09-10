# PostgreSQL 数据库部署（手动）

## 概述

本文档介绍不依赖部署脚本，手动部署 PostgreSQL 数据库的方法。PG 支持容器化和 RPM 两种部署方式。

> 如果使用脚本部署，请参考 [宿主机脚本部署](02-script-host.md) 或 [容器脚本部署](03-script-container.md)。

### 版本要求

- PostgreSQL 15.x
- 数据库名：`witty-ub`
- 用户名：`witty-ub`
- 密码：必须使用唯一的强口令

> 使用部署脚本首次初始化时，可按提示隐藏输入至少 6 位字母数字口令；直接回车或非交互部署会自动生成随机口令。口令写入独立密钥文件（源码 host 部署 0400，容器化 PG 0440，RPM 包部署 0600），不回写 `deploy.conf` —— 配置文件始终保持 `<CHANGE_ME>` 占位；脚本在写入后会**校验实际权限**，不符合预期即报错退出。密钥文件路径按部署形态不同：
>
> - **源码 host 部署**（`deploy_pg.sh --rpm/--apt`）：`deploy/pg.passwd`
> - **Docker 部署**（`deploy_pg.sh --docker`）和 **RPM 包部署**（`witty-ub manager deploy`）：`/etc/witty-ub/pg.passwd`
>
> 容器方式访问宿主机 PG 时，`deploy_witty.sh` 会按 `/etc/witty-ub/pg.passwd` → `deploy/pg.passwd` 顺序自动查找，无需手工复制密钥。
>
> 生产部署后必须轮换；手动部署时请将下文的 `<STRONG_PASSWORD>` 替换为唯一的强口令。

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

# 创建密钥（也可运行 bash deploy/deploy_pg.sh --docker 自动生成）
# 目录需可被部署用户遍历（0755），密钥本身 0440 root:root：
# PG 容器内的 postgres 用户为 uid=26/gid=0，需组可读才能读到 /run/secrets/pg_password
sudo install -d -m 0755 /etc/witty-ub
printf '%s' "<STRONG_PASSWORD>" | sudo install -m 0440 -o root -g root /dev/stdin /etc/witty-ub/pg.passwd

# 启动 PG 容器
docker run -d \
  --name postgres \
  --restart unless-stopped \
  -p 15432:5432 \
  -v pg15-data:/var/lib/pgsql/data \
  -v /etc/witty-ub/pg.passwd:/run/secrets/pg_password:ro \
  -e POSTGRESQL_USER=witty-ub \
  -e POSTGRESQL_DATABASE=witty-ub \
  --health-cmd="pg_isready -U witty-ub -d witty-ub" \
  --health-interval=30s \
  --health-timeout=10s \
  --health-retries=3 \
  --health-start-period=40s \
  --network witty-ub-network \
  --entrypoint /bin/bash \
  quay.io/sclorg/postgresql-15-c9s:latest \
  -c 'export POSTGRESQL_PASSWORD="$(tr -d "\r\n" </run/secrets/pg_password)";
      test -n "$POSTGRESQL_PASSWORD" || exit 1;
      exec /usr/bin/container-entrypoint /usr/bin/run-postgresql'
```

> `shared_buffers` 建议为物理内存的 25%，`effective_cache_size` 建议为 75%。

### 使用 docker compose

```yaml
services:
  postgres:
    image: quay.io/sclorg/postgresql-15-c9s:latest
    container_name: postgres
    restart: unless-stopped
    ports:
      - "15432:5432"
    environment:
      - POSTGRESQL_USER=witty-ub
      - POSTGRESQL_DATABASE=witty-ub
    secrets:
      - pg_password
    entrypoint: /bin/bash
    command:
      - -c
      - >-
        export POSTGRESQL_PASSWORD="$$(cat /run/secrets/pg_password)";
        test -n "$$POSTGRESQL_PASSWORD" || exit 1;
        exec /usr/bin/container-entrypoint /usr/bin/run-postgresql
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

secrets:
  pg_password:
    file: /etc/witty-ub/pg.passwd
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
sudo -u postgres psql -c "CREATE USER witty-ub WITH PASSWORD '<STRONG_PASSWORD>';"
sudo -u postgres psql -c "CREATE DATABASE witty-ub OWNER witty-ub;"
```

### 验证（RPM 部署）

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
