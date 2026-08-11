# 容器运行问题排查

本文档介绍 witty-ub 容器运行时常见问题的排查方法，包括 seccomp/clone3 问题、Docker 版本兼容性、日志管理、容器内调试和生产环境建议。

---

## 1. seccomp/clone3 问题

### 问题描述

**症状**: 容器启动后运行异常，出现以下情况之一:
- Latency Plugin 报 `RuntimeError: can't start new thread`
- 容器内进程创建失败或线程池无法扩展
- OpenCode 服务无法正常启动
- 应用日志中出现 `clone3` 系统调用失败相关错误

**根本原因**: 宿主机 Docker、runc 或 libseccomp 版本较旧（通常 Docker < 20.10），默认 seccomp 政策不支持 glibc 新版本中用于创建线程/进程的 `clone3` 系统调用。

### 验证步骤

#### 步骤 1: 检查宿主机 Docker 版本

```bash
docker --version
```

如果版本低于 `20.10`，则可能存在此问题。

#### 步骤 2: 检查容器内线程创建能力

```bash
docker exec witty-ub \
  /var/witty-ub/latency/.venv/bin/python \
  -c 'import threading; t=threading.Thread(target=lambda: print("thread ok")); t.start(); t.join()'
```

如果输出 `RuntimeError: can't start new thread`，说明线程创建失败。

#### 步骤 3: 验证 seccomp 限制

启动临时容器，关闭 seccomp 限制后再次测试:

```bash
IMAGE=$(docker inspect witty-ub --format '{{.Config.Image}}')

docker run --rm \
  --security-opt seccomp=unconfined \
  --entrypoint /var/witty-ub/latency/.venv/bin/python \
  "$IMAGE" \
  -c 'import threading; t=threading.Thread(target=lambda: print("thread ok")); t.start(); t.join()'
```

如果临时容器输出 `thread ok`，可以确认是 seccomp 兼容问题。

#### 步骤 4: 检查 libseccomp 版本

```bash
ldconfig -p | grep libseccomp
rpm -qa | grep libseccomp  # CentOS/RHEL/openEuler
dpkg -l | grep libseccomp  # Debian/Ubuntu
```

如果 libseccomp 版本低于 `2.5.0`，可能无法正确处理 `clone3` 系统调用。

### 修复方案

#### 方案一: 添加 `--security-opt seccomp=unconfined` 参数（临时兼容）

这是最快的临时解决方案，适用于无法立即升级 Docker 的环境。

**使用 docker run 命令**:

```bash
docker run -d \
  --name witty-ub \
  --restart unless-stopped \
  -p 32412:8080 \
  -v witty-ub-data:/var/witty-ub/data \
  -v witty-ub-logs:/var/log/witty-ub \
  --security-opt seccomp=unconfined \
  witty-ub:latest
```

**使用 docker compose**:

修改 `docker-compose.yml`:

```yaml
services:
  witty-ub:
    image: witty-ub:latest
    container_name: witty-ub
    restart: unless-stopped
    ports:
      - "32412:8080"
    volumes:
      - witty-ub-data:/var/witty-ub/data
      - witty-ub-logs:/var/log/witty-ub
    security_opt:
      - seccomp=unconfined
```

然后重新创建容器:

```bash
docker compose down
docker compose up -d
docker logs -f witty-ub
```

#### 方案二: 升级 Docker Engine 和 libseccomp（推荐）

长期解决方案是升级宿主机的 Docker Engine、runc 和 libseccomp 到最新版本。

**在 openEuler/CentOS/RHEL 上**:

```bash
# 升级 libseccomp
yum update -y libseccomp

# 升级 Docker（参考官方文档）
# https://docs.docker.com/engine/install/
```

#### 方案三: 使用自定义 seccomp 配置

如果不想完全关闭 seccomp，可以创建自定义配置文件，允许 `clone3` 系统调用:

```json
{
  "defaultAction": "SCMP_ACT_ALLOW",
  "syscalls": [
    {
      "name": "clone3",
      "action": "SCMP_ACT_ALLOW"
    }
  ]
}
```

保存为 `seccomp.json`，然后启动容器时使用:

```bash
docker run --security-opt seccomp=./seccomp.json ...
```

### 验证修复结果

修复后，重新进入容器验证线程创建:

```bash
docker exec witty-ub \
  /var/witty-ub/latency/.venv/bin/python \
  -c 'import threading; t=threading.Thread(target=lambda: print("thread ok")); t.start(); t.join()'
```

如果输出 `thread ok`，说明修复成功。

检查 Latency Plugin 服务状态:

```bash
docker exec witty-ub curl http://localhost:9772/health_check
```

预期输出: `{"status": "healthy"}`

> **安全提示**: `seccomp=unconfined` 会关闭容器的默认 seccomp 系统调用过滤，降低了容器的安全隔离性。仅建议用作问题验证或临时兼容方案。长期建议升级宿主机的 Docker Engine、runc 和 libseccomp，并在升级后移除此参数。

---

## 2. Docker 版本兼容性

### 版本要求

- **最低版本**: Docker 20.10+
- **推荐版本**: Docker 24.0+

### 检查版本

```bash
docker --version
docker compose version
```

### 低版本 Docker 注意事项

如果 Docker 版本低于 20.10:
1. 可能遇到 seccomp/clone3 问题（见上文）
2. 不支持 `docker compose` 命令，需使用 `docker-compose`（带连字符）
3. 多架构构建功能受限

### 升级 Docker

**在 openEuler 上**:

```bash
# 卸载旧版本
sudo yum remove docker docker-client docker-client-latest docker-common docker-latest docker-latest-logrotate docker-logrotate docker-engine

# 安装依赖
sudo yum install -y yum-utils

# 添加 Docker 仓库
sudo yum-config-manager --add-repo https://download.docker.com/linux/centos/docker-ce.repo

# 安装 Docker
sudo yum install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin

# 启动 Docker
sudo systemctl start docker
sudo systemctl enable docker
```

---

## 3. 日志管理

### 查看日志

```bash
# 使用 docker compose
docker compose logs
docker compose logs -f
docker compose logs --tail=100
docker compose logs --since 2024-01-01T10:00:00

# 使用纯 Docker 命令
docker logs witty-ub
docker logs -f witty-ub
docker logs --tail=100 witty-ub
docker logs --since 2024-01-01T10:00:00 witty-ub
```

### 日志位置

容器内日志路径:

| 日志类型 | 路径 |
|---------|------|
| Nginx 访问日志 | `/var/log/witty-ub-web/access.log` |
| Nginx 错误日志 | `/var/log/witty-ub-web/error.log` |
| Latency 服务日志 | `/var/log/witty-ub/latency_server.log` |
| OpenCode 日志 | `/var/log/witty-ub/opencode_server.log` |
| 应用日志 | `/var/log/witty-ub/` |

### 导出日志

```bash
# 导出容器日志到文件
docker compose logs > witty-ub-logs.txt
docker logs witty-ub > witty-ub-logs.txt

# 导出特定时间范围的日志
docker compose logs --since 24h > witty-ub-logs-recent.txt
docker logs --since 24h witty-ub > witty-ub-logs-recent.txt

# 导出容器内日志文件到宿主机
docker cp witty-ub:/var/log/witty-ub/latency_server.log ./latency_server.log
docker cp witty-ub:/var/log/witty-ub-web/error.log ./nginx-error.log
```

### 日志轮转

Docker 默认日志驱动为 `json-file`，建议配置日志轮转:

**使用 docker compose**:

```yaml
services:
  witty-ub:
    logging:
      driver: "json-file"
      options:
        max-size: "100m"
        max-file: "3"
```

**使用纯 Docker 命令**:

```bash
docker run -d \
  --name witty-ub \
  -p 32412:8080 \
  --log-driver json-file \
  --log-opt max-size=100m \
  --log-opt max-file=3 \
  witty-ub:latest
```

---

## 4. 容器内调试

### 进入容器

```bash
# 进入运行中的容器
docker exec -it witty-ub /bin/bash

# 以交互模式启动临时容器（调试启动问题）
docker run -it --rm --name witty-ub-debug \
  -p 32412:8080 \
  -v witty-ub-data:/var/witty-ub/data \
  witty-ub:latest /bin/bash
```

### 常用调试命令

```bash
# 查看进程
ps aux

# 查看网络
netstat -tlnp

# 查看 Python 环境
/var/witty-ub/latency/.venv/bin/pip list

# 手动启动服务
/var/witty-ub/latency/.venv/bin/python /var/witty-ub/latency/access/fastapi_server.py

# 查看容器退出原因
docker inspect witty-ub | grep "ExitCode"
```

---

## 5. 生产环境建议

### 5.1 资源限制

```yaml
services:
  witty-ub:
    deploy:
      resources:
        limits:
          cpus: '4'
          memory: 8G
        reservations:
          cpus: '2'
          memory: 4G
```

### 5.2 重启策略

```yaml
services:
  witty-ub:
    restart: always  # 或 unless-stopped
```

### 5.3 安全加固

**使用非 root 用户运行**:

```dockerfile
RUN groupadd -r witty-ub && useradd -r -g witty-ub witty-ub
USER witty-ub
```

**扫描镜像漏洞**:

```bash
docker scan witty-ub
```

### 5.4 监控与告警

```yaml
healthcheck:
  test: ["CMD", "curl", "-f", "http://localhost:9772/health_check"]
  interval: 30s
  timeout: 10s
  retries: 3
  start_period: 40s
```

### 5.5 日志集中管理

```yaml
logging:
  driver: "syslog"
  options:
    syslog-address: "tcp://log-server:514"
    tag: "witty-ub"
```

### 5.6 备份策略

```bash
#!/bin/bash
# backup.sh
BACKUP_DIR="/backup/witty-ub"
DATE=$(date +%Y%m%d_%H%M%S)

mkdir -p $BACKUP_DIR

docker run --rm \
  -v witty-ub_witty-ub-data:/data \
  -v $BACKUP_DIR:/backup \
  alpine tar czf /backup/data_$DATE.tar.gz -C /data .

find $BACKUP_DIR -name "*.tar.gz" -mtime +30 -delete
```

---

## 相关文档

- 常见问题诊断 → [01-common-issues.md](01-common-issues.md)
- 部署指南 → [../deployment/01-overview.md](../deployment/01-overview.md)
- 配置参考 → [../usage/03-configuration-reference.md](../usage/03-configuration-reference.md)
