# 快速入门

witty-ub 超节点故障智能监控诊断平台提供 KVCache 和 URMA 组件的故障定界分析。

## 部署方式

前后端默认支持分离部署：后端跑在有数据的机器（无出网要求），前端与 AI Agent 跑在能访问大模型服务的机器；两者也可合并为单机 All-in-One（`WITTY_ROLE=all`）。各部署方式均支持两种形态。

### 脚本部署（推荐）

一键部署，适合快速上手：

```bash
# 宿主机部署
# 单机: 前后端同机
bash deploy/host/deploy.sh --deploy

# 分离: 后端节点（有数据的机器）
bash deploy/host/deploy.sh --deploy --role backend

# 分离: 前端节点（能访问 Agent/LLM 的机器）
WITTY_BACKEND_URL=http://<后端IP>:9772 \
  bash deploy/host/deploy.sh --deploy --role frontend
```

→ [宿主机脚本部署](./deployment/02-script-host.md)

```bash
# 容器部署（单机）
bash deploy/docker/manage.sh
# 选择 [1] 一键安装

# 容器分离部署（同机双容器, 跨机拆分见文档）
docker compose --profile split up -d
```

→ [容器脚本部署](./deployment/03-script-container.md) | [容器分离部署](./deployment/08-container.md)

### 手动部署

分步部署，适合开发调试：

1. [部署 PostgreSQL](./deployment/05-database.md)
2. 部署应用：[源码](./deployment/06-source.md) | [RPM](./deployment/07-rpm.md) | [容器](./deployment/08-container.md)

→ [架构概览](./deployment/01-overview.md)

## 打包构建

- [Docker 镜像构建](./package/01-docker-build.md) — 分层镜像架构，构建应用镜像用于容器部署
- [RPM 包构建](./package/02-rpm-build.md) — 生成 RPM 安装包，适用于生产环境快速部署
- [镜像分发](./package/03-distribution.md) — 镜像推送、导出 tar 包、离线加载

## 使用文档

- [平台操作指南](./usage/01-platform-guide.md)
- [数据采集工具](./usage/02-data-collection-guide.md)
- [配置参考](./usage/03-configuration-reference.md)

## 故障排查

- [常见问题](./troubleshooting/01-common-issues.md)
- [容器运行问题](./troubleshooting/02-container-runtime.md)

## 访问服务

- 本地：`http://localhost:8080`
- 远程：`http://<服务器IP>:8080`

默认端口：RPM/容器 `8080`，源码开发 `5173`
