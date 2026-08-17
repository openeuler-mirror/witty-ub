# 常见问题诊断与解决

本文档汇总 witty-ub 部署和运行过程中的常见问题及其解决方案。

---

## 快速定位问题

```bash
# 使用 docker compose
docker compose ps
docker compose logs witty-ub
docker compose exec -it witty-ub bash

# 使用纯 Docker 命令
docker ps
docker logs witty-ub
docker exec -it witty-ub /bin/bash
```

---

## 1. 容器无法启动

**症状**: 容器启动失败，提示镜像不存在或启动后立即退出

**解决方案**:

```bash
# 查看当前容器状态
docker compose ps
docker images

# 如果镜像名称为 <none>，为其打上标签
docker tag <镜像ID> witty-ub:latest

# 重新启动容器
docker compose up -d
```

---

## 2. 端口冲突

**症状**: 启动失败，提示端口已被占用

**解决方案**:

```bash
# 查看端口占用
netstat -tlnp | grep 32412

# 修改 docker-compose.yml 中的端口映射（只需修改宿主机端口）
ports:
  - "32413:8080"  # 改为其他可用端口
```

---

## 3. 权限问题

**症状**: 容器内无法写入数据

**解决方案**:

```bash
# 检查卷权限
docker exec witty-ub ls -la /var/witty-ub

# 修复权限
docker exec witty-ub chmod -R 755 /var/witty-ub
```

---

## 4. Latency Plugin 未启动

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

---

## 5. Nginx 无法访问

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

---

## 6. 磁盘空间不足

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

---

## 7. OpenCode 服务异常

**症状**: AI 诊断功能无法使用，提示 "bad file reference"、"Agent 处理消息时发生错误" 或 OpenCode 服务未启动

### 7.1 配置目录未挂载

```bash
# 检查 opencode 配置目录是否存在
ls ~/.config/opencode/

# 确保 docker-compose.yml 中挂载了配置目录
# - ~/.config/opencode:/root/.config/opencode
```

> **说明**：docker 部署时修改 opencode 配置文件请在宿主机上操作，部署会将宿主机配置目录映射到容器中，在容器内修改不会持久化。详见 [配置参考手册 · OpenCode 配置](../usage/03-configuration-reference.md#opencode-配置)。

### 7.2 环境变量未设置

```bash
# 进入容器检查环境变量
docker exec witty-ub env | grep -E "(OPENCODE_CONFIG|WITTY_DIR)"

# 预期输出:
# OPENCODE_CONFIG=/var/witty-ub/config/opencode.json
# WITTY_DIR=/var/witty-ub
```

### 7.3 OpenCode 进程未启动

```bash
# 检查 OpenCode 进程是否运行
docker exec witty-ub ps aux | grep opencode

# 检查 OpenCode 日志
docker exec witty-ub cat /var/log/witty-ub/opencode_server.log

# 手动启动 OpenCode（会先校验配置）
docker exec witty-ub bash /var/witty-ub/latency/deploy/run_opencode.sh
```

### 7.4 Agent 文件路径错误

```bash
# 检查 agent 文件是否存在
docker exec witty-ub ls -la /var/witty-ub/config/agents/

# 检查 opencode.json 配置文件中的路径是否正确
docker exec witty-ub cat /var/witty-ub/config/opencode.json | grep -A5 prompt

# 预期输出:
# "prompt": "{file:{env:WITTY_DIR}/config/agents/witty-ub-diagnostician.md}"
```

### 7.5 Latency API 未启动

```bash
# Agent 直接依赖 Latency HTTP API
docker exec witty-ub curl --noproxy 127.0.0.1 http://127.0.0.1:9772/health_check
```

---

## 8. 依赖包找不到

**症状**: `cpp-httplib-devel` 等包安装失败

**解决方案**:

确保使用正确的基础镜像版本:
- `openeuler/openeuler:24.03-lts-sp4` (推荐，包含完整依赖)
- 基础版本 `24.03-lts` 可能缺少部分包

---

## 相关文档

- 容器运行问题排查 → [02-container-runtime.md](02-container-runtime.md)
- 部署指南 → [../deployment/01-overview.md](../deployment/01-overview.md)
- 配置参考 → [../usage/03-configuration-reference.md](../usage/03-configuration-reference.md)
