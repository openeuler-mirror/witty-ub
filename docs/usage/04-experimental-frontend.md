# 试验性前端（exp）使用

## 1. 访问入口

试验性前端与既有前端是同一平台的两套界面，访问地址按部署形态区分：

| 部署形态 | 地址 |
| ------ | ------ |
| 容器（独立前端节点） | `http://<前端IP>:32414` |
| 容器（替换式，`--role frontend`） | `http://<前端IP>:<前端容器映射端口>`（默认 32413） |
| 源码 / 宿主机 | `http://<前端IP>:8081`（无 nginx 时 vite preview `5174`） |
| RPM | `http://<前端IP>:8081` |

既有前端的地址（`8080` / `5173` / `32413`）保持不变，两者可同时访问、互不影响。

## 2. 功能与数据

- 与既有前端**共用同一后端**：知识库、任务、解析结果、故障模式与诊断数据完全一致，
  在任一界面创建的任务在另一界面同样可见。
- 界面为重构版：拓扑/故障模式视图、任务与资产、AI 助手等入口布局与旧版不同；
  功能对齐进度见 `src/web_new/docs/`（对齐计划与验收记录）。
- 大文件上传同样经前端节点 Nginx 流式转发（`client_max_body_size 20G`）。

## 3. AI 助手（Agent）

AI 助手依赖 OpenCode（默认 4096），Web 通过同源 `/agent-api/` 反代访问：

| 部署形态 | Agent 来源 | 说明 |
| ------ | ------ | ------ |
| 容器 | 镜像内置 | 随容器启动，无需额外安装 |
| 源码 / 宿主机 | 节点上安装 OpenCode + Agent bundle | 用 `deploy/deploy_opencode.sh` 手动启动，或用 `deploy/host/install_opencode_service.sh install` 注册为 systemd user 服务（与裸进程托管互斥，都占用 4096） |
| RPM | 节点上安装 OpenCode + Agent bundle | Agent bundle 随 `witty-ub-web` 子包提供；`witty-ub-web-exp` 本身不含 Agent |

分离部署时，Agent 的 `WITTY_API_BASE` 需指向后端节点（如 `http://<后端IP>:9772`），
且 `WITTY_NO_PROXY` 设为 `*` 或后端 IP，避免代理拦截 Agent 的 curl 请求。

连通性自检：

```bash
curl -s http://<前端IP>:8081/agent-api/global/health    # {"healthy":true,...}
```

## 4. 版本确认

```bash
# 容器
docker exec witty-ub-frontend-exp cat /var/witty-ub/web-exp/BUILD_INFO
# 源码 / RPM
cat /var/witty-ub/web-exp/BUILD_INFO
```

`BUILD_INFO` 记录底座 release、源码 commit、构建日期与构建方式（`nightly` / `rpm-patch`），
镜像另可通过 label 确认（`docker inspect <镜像> --format '{{json .Config.Labels}}'`）；
反馈问题时请附上上述信息。

## 5. 常见问题

| 现象 | 处理 |
| ------ | ------ |
| 页面打开但接口返回 502 | 后端不可达：确认 `WITTY_BACKEND_URL` 与后端节点 9772 放行 |
| `/agent-api/` 返回 502 | OpenCode 未启动或端口被占：检查 4096 与 Agent 启动日志 |
| 8081 无法访问 | 端口占用或服务未启动：`ss -tlnp \| grep 8081`、`systemctl status witty-ub-web-exp` |
| 页面样式/资源 404 | 静态产物不完整：重新部署（源码重新 `install`，容器重新拉取当日镜像） |
| 上游数据页无数据 | 与既有前端共用后端，先在既有界面或 API 确认知识库存在数据 |
| 想回到旧界面 | exp 与既有前端并行部署，直接访问旧端口即可；不需要停用 exp |

## 相关文档

- 部署（容器 / 源码 / RPM）→ [../deployment/09-experimental-frontend.md](../deployment/09-experimental-frontend.md)
- 打包（镜像 nightly、RPM 子包）→ [../package/04-experimental-frontend-build.md](../package/04-experimental-frontend-build.md)
- 平台操作指南（通用功能）→ [01-platform-guide.md](01-platform-guide.md)
