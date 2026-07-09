<!-- Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved. -->
<!-- witty-ub is licensed under the Mulan PSL v2. -->

# 4. 故障排查

> 返回 [首页](Home.md)

## 容器无法启动

```bash
# 使用 docker compose
docker compose ps
docker compose logs witty-ub
docker compose exec -it witty-ub bash
```

### 使用纯 Docker 命令（低版本 Docker）

```bash
# 查看容器状态（运行中）
docker ps

# 查看容器状态（所有）
docker ps -a

# 查看详细日志
docker logs witty-ub

# 查看最近 100 行日志
docker logs --tail=100 witty-ub

# 查看容器退出原因
docker inspect witty-ub | grep "ExitCode"

# 进入容器调试（容器运行中）
docker exec -it witty-ub /bin/bash

# 以交互模式启动容器（调试启动问题）
docker run -it --rm --name witty-ub-debug \
  -p 32412:8080 \
  -v witty-ub-data:/var/witty-ub/data \
  witty-ub:latest /bin/bash
```

---

## 常见问题

### 1.witty-ub 容器无法启动

**症状**: 容器启动失败，提示镜像不存在

**解决方案**:
查看当前容器状态:

```bash
# 使用docker-compose查看容器状态
docker compose ps
# 使用docker查看镜像
docker images
```

可以根据当前镜像大小预计900m左右来锁定镜像，并观察其 tag 和 镜像名称为 none
为其打上标签，例如 `witty-ub:latest`
```bash
# 为镜像打上标签
docker tag <镜像ID> witty-ub:latest
```
打上标签后，即可启动容器，参考 [启动容器](03-pull-and-run.md)

### 1. 端口冲突

**症状**: 启动失败，提示端口已被占用

**解决方案**:

```bash
# 查看端口占用
netstat -tlnp | grep 32412

# 修改 docker-compose.yml 中的端口映射（只需修改宿主机端口）
ports:
  - "32413:8080"  # 改为其他可用端口
```

### 2. 权限问题

**症状**: 容器内无法写入数据

**解决方案**:

```bash
# 检查卷权限
docker exec witty-ub ls -la /var/witty-ub

# 修复权限
docker exec witty-ub chmod -R 755 /var/witty-ub
```

### 3. Latency Plugin 未启动

**症状**: API 返回 502 或连接拒绝

**解决方案**:

```bash
# 查看 Latency 服务日志
docker exec witty-ub cat /var/log/witty-ub/latency_server.log

# 手动启动 Latency 服务
docker exec witty-ub /var/witty-ub/latency/.venv/bin/python \
  /var/witty-ub/latency/access/fastapi_server.py

# 检查健康状态
docker exec witty-ub curl http://localhost:9772/health_check
```

### 4. Nginx 无法访问

**症状**: Web UI 无法打开

**解决方案**:

```bash
# 检查 Nginx 状态
docker exec witty-ub nginx -t

# 查看 Nginx 错误日志
docker exec witty-ub cat /var/log/witty-ub-web/error.log

# 重启 Nginx
docker exec witty-ub nginx -s reload
```

### 5. 磁盘空间不足

**症状**: 容器启动失败或运行异常

**解决方案**:

```bash
# 检查磁盘使用
df -h

# 清理 Docker 无用资源
docker system prune -a

# 清理悬空镜像
docker image prune

# 清理未使用的卷
docker volume prune
```

### 6. 依赖包找不到

**症状**: `cpp-httplib-devel` 等包安装失败

**解决方案**:

确保使用正确的基础镜像版本:
- `openeuler/openeuler:24.03-lts-sp4` (推荐，包含完整依赖)
- 基础版本 `24.03-lts` 可能缺少部分包

---

## 容器内调试

```bash
# 进入容器
docker exec -it witty-ub /bin/bash

# 查看进程
ps aux

# 查看网络
netstat -tlnp

# 查看 Python 环境
/var/witty-ub/latency/.venv/bin/pip list

# 手动启动服务
/var/witty-ub/latency/.venv/bin/python /var/witty-ub/latency/access/fastapi_server.py
```

---

## 日志管理

### 查看日志

```bash
# 使用 docker compose
docker compose logs
docker compose logs -f
docker compose logs --tail=100
docker compose logs --since 2024-01-01T10:00:00
```

### 使用纯 Docker 命令（低版本 Docker）

```bash
# 查看所有日志
docker logs witty-ub

# 实时查看日志
docker logs -f witty-ub

# 查看最近 100 行
docker logs --tail=100 witty-ub

# 查看特定时间后的日志
docker logs --since 2024-01-01T10:00:00 witty-ub

# 查看指定时间范围内的日志
docker logs --since 2024-01-01T00:00:00 --until 2024-01-01T23:59:59 witty-ub

# 查看容器内日志文件
docker exec witty-ub cat /var/log/witty-ub/latency_server.log
docker exec witty-ub cat /var/log/witty-ub-web/error.log
```

### 日志位置

容器内日志路径:

- **Nginx 接口日志**: `/var/log/witty-ub-web/access.log`
- **Nginx 错误日志**: `/var/log/witty-ub-web/error.log`
- **Latency 服务日志**: `/var/log/witty-ub/latency_server.log`
- **应用日志**: `/var/log/witty-ub/`

### 导出日志

```bash
# 导出所有日志到文件
docker compose logs > witty-ub-logs.txt

# 导出最近 24 小时日志
docker compose logs --since 24h > witty-ub-logs-recent.txt
```

### 导出日志

```bash
# 使用 docker compose
docker compose logs > witty-ub-logs.txt
docker compose logs --since 24h > witty-ub-logs-recent.txt
```

### 使用纯 Docker 命令导出日志（低版本 Docker）

```bash
# 导出所有日志到文件
docker logs witty-ub > witty-ub-logs.txt

# 导出最近 24 小时日志
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

**使用纯 Docker 命令（低版本 Docker）**:

在启动容器时添加日志选项:

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

## 生产环境建议

### 1. 资源限制

在 `docker-compose.yml` 中添加资源限制:

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

### 2. 重启策略

```yaml
services:
  witty-ub:
    restart: always  # 或 unless-stopped
```

### 3. 安全加固

- 使用非 root 用户运行:

```dockerfile
RUN groupadd -r witty-ub && useradd -r -g witty-ub witty-ub
USER witty-ub
```

- 扫描镜像漏洞:

```bash
docker scan witty-ub
```

### 4. 监控与告警

```yaml
healthcheck:
  test: ["CMD", "curl", "-f", "http://localhost:8080/health_check"]
  interval: 30s
  timeout: 10s
  retries: 3
  start_period: 40s
```

### 5. 日志集中管理

使用 Docker 日志驱动对接外部日志系统:

```yaml
logging:
  driver: "syslog"
  options:
    syslog-address: "tcp://log-server:514"
    tag: "witty-ub"
```

### 6. 备份策略

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

## 环境变量参考

| 变量名 | 默认值 | 说明 |
|--------|--------|------|
| PYTHONPATH | /var/witty-ub | Python 模块搜索路径 |
| LOG_LEVEL | info | 日志级别 (debug/info/warning/error) |

---

## 技术支持

- **项目文档**: 参考项目根目录下的 README.md
- **问题反馈**: 提交 Issue 到项目仓库
- **更新日志**: 查看 CHANGELOG

---

## 返回首页

[返回首页](Home.md)
