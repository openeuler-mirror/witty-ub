# 试验性前端（exp）部署

## 1. 概述

试验性前端（exp）与既有前端并行演进，两者**同后端、同接口契约、同运维形态**
（Nginx 静态托管 + 同源 API 反代 + `/agent-api/` 反代 OpenCode），但目录、端口、服务与
包名完全独立，默认不安装、不启动，需显式选择部署；停用或卸载即完成回退。

| 资源 | 既有前端（不变） | 试验性前端（exp） |
| ------ | ------ | ------ |
| 静态目录 | `/var/witty-ub/web` | `/var/witty-ub/web-exp` |
| 端口（源码 / RPM） | 8080（nginx）/ 5173（vite） | 8081（nginx）/ 5174（vite） |
| 端口（容器） | 32413 → 8080 | 32414 → 8080 |
| systemd 单元 | `witty-ub-web.service` / `witty-ub-frontend.service` | `witty-ub-web-exp.service` / `witty-ub-frontend-exp.service` |
| 镜像标签 | `frontend`、`frontend-<release>` | `frontend-exp-<YYYYMMDD>`、`frontend-exp` |
| RPM 子包 | `witty-ub-web` | `witty-ub-web-exp` |
| 配置文件 | `/etc/witty-ub/web/env` | `/etc/witty-ub/web-exp/env` |

- 构建与产物说明（镜像 nightly、RPM 子包）见[试验性前端打包](../package/04-experimental-frontend-build.md)
- 界面使用、Agent 配置与常见问题见[试验性前端使用](../usage/04-experimental-frontend.md)

## 2. 前置条件

- 已构建 exp 产物：镜像 tag 形如 `<repo>/witty-ub:frontend-exp-<YYYYMMDD>`，
  RPM 子包形如 `witty-ub-web-exp-<version>-<release>.<arch>.rpm`
- 后端 FastAPI（9772）对前端节点可达；使用 AI 助手时需 OpenCode（4096）
- 容器部署：Docker 20.10+
- 源码部署：Node.js ≥ 20.18.2、nginx、systemd（或 nohup 回退）
- RPM 部署：dnf/yum，节点可访问 `Witty-Builder` 仓库（配置见[打包文档](../package/04-experimental-frontend-build.md) §3.6），或使用本地 rpm 文件

---

## 3. 容器部署

### 3.1 替换式（exp 作为独立前端节点）

```bash
bash deploy/docker/deploy_witty.sh --role frontend \
  --image hub-harbor.oepkgs.net/neocopilot/witty-ub:frontend-exp-20260916
```

既有的 `witty-ub:frontend` 镜像与部署方式保持不变，可随时回退。

### 3.2 与既有前端同机并行

```bash
docker run -d --name witty-ub-frontend-exp --restart unless-stopped \
  -p 32414:8080 \
  -v ~/.config/opencode:/root/.config/opencode \
  -v witty-ub-experience-data-exp:/var/witty-ub/witty_ub_diagnostician/.opencode/skills/experience-skill/data \
  -e WITTY_ROLE=frontend \
  -e WITTY_BACKEND_URL=http://<后端IP>:9772 \
  hub-harbor.oepkgs.net/neocopilot/witty-ub:frontend-exp-20260916
```

容器内仍是 8080（nginx 静态根 `/var/witty-ub/web-exp`，`/agent-api/` 反代容器内 OpenCode）。
并行时与既有前端容器（32413）端口、容器名、经验库卷均相互独立。

### 3.3 验证

```bash
curl -I  http://<前端IP>:32414/                          # 200
curl -s  http://<前端IP>:32414/health_check              # 后端经反代返回 200
curl -s  http://<前端IP>:32414/agent-api/global/health   # {"healthy":true,...}
docker exec witty-ub-frontend-exp cat /var/witty-ub/web-exp/BUILD_INFO
```

---

## 4. 源码 / 宿主机部署

适用于开发调试与不便打镜像的节点（openEuler 24.03 验证通过）。

### 4.1 依赖

```bash
sudo dnf install -y nginx nodejs npm gettext rsync
node -v   # 需要 >= 20.18.2
```

### 4.2 安装与启动

```bash
# 默认后端指向本机 9772；分离部署时指向后端节点
WITTY_BACKEND_URL=http://<后端IP>:9772 \
  bash deploy/host/deploy_frontend_exp.sh install
```

脚本流程：构建 exp 前端源码（`src/web_exp`，当前回退 `src/web_new`）→ 发布 `dist/` 到
`/var/witty-ub/web-exp` → 渲染 exp 版 Nginx 配置（8081）→ 安装并启动 systemd user unit
`witty-ub-frontend-exp.service`（`systemctl --user` 不可用时回退 nohup）。

其它子命令：

```bash
bash deploy/host/deploy_frontend_exp.sh status      # 单元状态 + 首页/健康检查
bash deploy/host/deploy_frontend_exp.sh stop
bash deploy/host/deploy_frontend_exp.sh uninstall   # 停服务 + 清理 /var/witty-ub/web-exp
```

环境变量：`WITTY_BACKEND_URL`、`WITTY_AGENT_URL`、`WITTY_WEB_EXP_PORT`（默认 8081）、
`EXP_WEB_DIR`、`DEPLOY_PM=systemd|nohup`。

### 4.3 跨机部署注意事项

- 传入的 `WITTY_BACKEND_URL` / `WITTY_AGENT_URL` / `WITTY_WEB_EXP_PORT` 会写入
  `.deploy-run/frontend-exp.env`，由 unit 通过 `EnvironmentFile` 加载，服务或机器重启后仍
  指向同一后端；更换后端地址重新执行 `install`（或修改该文件后 `restart`）即可。
- 后端节点需对新前端节点放行 9772（与既有前端节点相同）：

  ```bash
  firewall-cmd --permanent --add-rich-rule='rule family=ipv4 source address=<前端IP>/32 port port=9772 protocol=tcp accept'
  firewall-cmd --reload
  ```

### 4.4 验证

```bash
curl -I  http://127.0.0.1:8081/
curl -s  http://127.0.0.1:8081/health_check
curl -s  http://127.0.0.1:8081/agent-api/global/health
systemctl --user status witty-ub-frontend-exp.service --no-pager
```

---

## 5. RPM 部署

```bash
# 1) 配置仓库（一次性；详见打包文档 §3.6）
sudo tee /etc/yum.repos.d/Witty-Builder.repo >/dev/null <<'EOF'
[Witty-Builder]
name=EulerMaker Witty Builder
baseurl=https://eulermaker.openeuler.openatom.cn/api/ems5/repositories/witty-builder/openEuler:24.03-LTS-SP3/$basearch/
metadata_expire=60
enabled=1
gpgcheck=1
gpgkey=https://eulermaker.openeuler.openatom.cn/api/ems5/repositories/witty-builder/openEuler:24.03-LTS-SP3/$basearch/RPM-GPG-KEY-openEuler
EOF
sudo dnf makecache

# 2) 安装并启动
sudo dnf install -y witty-ub-web-exp
sudo witty-ub-web-exp-ctl enable --backend http://<后端IP>:9772
sudo witty-ub-web-exp-ctl status
```

控制脚本子命令：`enable` / `disable` / `restart` / `status` / `config --backend ... --agent ... --port ...` / `logs`。
`%post` 只做安装期准备（SELinux 标签、`daemon-reload`），不自动启动服务。

子包与 `witty-ub-web` 互不依赖、可同机共存（既有前端 8080，exp 8081）。

nightly 更新（版本号不变，仓库提供最新一次构建）：

```bash
sudo dnf --refresh reinstall -y witty-ub-web-exp   # 同 NVR 需显式 reinstall
cat /var/witty-ub/web-exp/BUILD_INFO               # 确认构建日期与 commit
```

回滚：仓库只保留最新构建，需要旧版本时用对应日期的 `Source1` 重新构建后安装
（见打包文档 §3.4）。

### 验证

```bash
rpm -q witty-ub-web witty-ub-web-exp      # 同机共存时两者版本一致
systemctl status witty-ub-web-exp --no-pager
curl -I http://127.0.0.1:8081/
curl -s http://127.0.0.1:8081/health_check
```

---

## 6. 回滚与卸载

| 链路 | 停止 exp | 彻底移除 |
| ------ | ------ | ------ |
| 容器 | `docker stop witty-ub-frontend-exp` | `docker rm witty-ub-frontend-exp`（既有容器不受影响） |
| 源码 | `bash deploy/host/deploy_frontend_exp.sh stop` | `... uninstall` |
| RPM | `sudo witty-ub-web-exp-ctl disable` | `sudo dnf remove -y witty-ub-web-exp` |

三条链路的回滚都不影响既有前端（8080/5173/32413）、后端（9772）与数据库。

---

## 7. 验收清单

| 检查项 | 命令 | 期望 |
| ------ | ------ | ------ |
| 既有前端未受影响 | `curl -I http://<host>:8080/`（或 5173 / 32413） | 200 |
| 既有镜像未变 | `docker buildx imagetools inspect <repo>:frontend` | digest 与 release 发布时一致 |
| exp 页面 | `curl -I http://<host>:8081/`（或 5174 / 32414） | 200，含 exp 资源 `/assets/index-*.js` |
| SPA 深路由 | `curl -o /dev/null -w '%{http_code}' http://<host>:8081/fault/mode` | 200（回退 index.html） |
| 后端反代 | `curl http://<host>:8081/health_check` | 200 |
| Agent 反代 | `curl http://<host>:8081/agent-api/global/health` | `{"healthy":true,...}` |
| 版本可追溯 | `cat /var/witty-ub/web-exp/BUILD_INFO` | base / commit / 日期齐全 |
| 同机共存 | 同时访问 8080 与 8081 | 均 200，互不影响 |
| 回滚 | 停止/卸载 exp 前端 | 既有前端、后端、数据库无变化 |

## 相关文档

- 打包（镜像 nightly、RPM 子包）→ [../package/04-experimental-frontend-build.md](../package/04-experimental-frontend-build.md)
- 使用（访问入口、Agent、常见问题）→ [../usage/04-experimental-frontend.md](../usage/04-experimental-frontend.md)
- 既有部署方式 → [01-overview.md](01-overview.md) | [02-script-host.md](02-script-host.md) | [03-script-container.md](03-script-container.md) | [07-rpm.md](07-rpm.md) | [08-container.md](08-container.md)
