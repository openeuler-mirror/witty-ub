# 快速入门

witty-ub 超节点故障智能监控诊断平台提供 KVCache 和 URMA 组件的故障定界分析。

## 部署方式

### 脚本部署（推荐）

一键部署，适合快速上手：

```bash
# 宿主机部署（开发调试）
bash deploy/host/deploy.sh
```

→ [宿主机脚本部署](./deployment/02-script-host.md)

```bash
# 容器部署（生产环境）
bash deploy/docker/manage.sh
# 选择 [1] 一键安装
```

→ [容器脚本部署](./deployment/03-script-container.md)

### 手动部署

分步部署，适合开发调试：

1. [部署 PostgreSQL](./deployment/05-database.md)
2. 部署应用：[源码](./deployment/06-source.md) | [RPM](./deployment/07-rpm.md) | [容器](./deployment/08-container.md)

→ [架构概览](./deployment/01-overview.md)

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
