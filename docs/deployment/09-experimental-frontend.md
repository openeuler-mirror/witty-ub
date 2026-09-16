# 试验性前端（exp）构建与部署

## 1. 概述

试验性前端是相对既有前端 `src/web` 重写的新界面，与既有前端**同后端、同接口契约、同运维形态**
（Nginx 静态托管 + 同源 API 反代 + `/agent-api/` 反代 OpenCode）。它处于长期试验阶段，
与既有前端并行演进：

- 独立命名空间：所有标识使用 **`exp`**（experimental），不占用既有前端任何资源；
- 独立版本：镜像按**日期**发 nightly（`frontend-exp-<YYYYMMDD>`）；RPM 子包随主包版本，包名区分；
- 默认不安装、不启动，需显式选择部署；停用或卸载即完成回退，既有前端与后端不受影响。

| 资源 | 既有前端（不变） | 试验性前端（exp） |
| ------ | ------ | ------ |
| 静态目录 | `/var/witty-ub/web` | `/var/witty-ub/web-exp` |
| 端口（源码/RPM） | 8080（nginx）/ 5173（vite） | 8081（nginx）/ 5174（vite） |
| 端口（容器） | 32413 → 8080 | 32414 → 8080 |
| systemd 单元 | `witty-ub-web.service` / `witty-ub-frontend.service` | `witty-ub-web-exp.service` / `witty-ub-frontend-exp.service` |
| 镜像标签 | `frontend`、`frontend-<release>` | `frontend-exp-<YYYYMMDD>`、`frontend-exp` |
| RPM 子包 | `witty-ub-web` | `witty-ub-web-exp` |
| 配置文件 | `/etc/witty-ub/web/env` | `/etc/witty-ub/web-exp/env` |

设计细节见 [设计文档](../design/experimental-frontend-deployment.md)。

---

## 2. 版本与可追溯性

| 产物 | 版本规则 | 追溯信息 |
| ------ | ------ | ------ |
| exp 镜像 | `frontend-exp-<YYYYMMDD>`（不可变）+ `frontend-exp`（移动标签） | 镜像 label：`org.opencontainers.image.version/revision/created`、`com.witty-ub.base.release/digest` |
| 容器/源码/RPM 载荷 | —— | `/var/witty-ub/web-exp/BUILD_INFO`（`base_release`、`source_commit`、`build_date`、`build_kind`） |
| RPM 子包 | 与主包同 `Version-Release`（如 `1.0.4-6`），不单独发版本号 | 同上 |

> exp 镜像的底座**固定为当前 release 前端镜像**（`witty-ub:frontend-<release>`）：
> Nginx、OpenCode、诊断工具、Agent bundle 与 release 完全一致，只替换前端静态资源。

---

## 3. 前置条件

- 构建机：Node.js ≥ 20.18.2、npm；`docker` + `buildx`（`docker-container` driver 才能多架构）
- 推送镜像：`docker login hub-harbor.oepkgs.net`（neocopilot 账号）
- 已有 release 镜像：`hub-harbor.oepkgs.net/neocopilot/witty-ub:frontend-<release>`
- 运行节点：后端 FastAPI（9772）可达；Agent 需要 OpenCode（4096）

---

## 4. 链路 A：容器镜像（推荐）

### 4.1 构建并推送 nightly

```bash
# 当天 nightly：base 默认取仓库最新 release tag，推送 frontend-exp-<今天> 与 frontend-exp
bash scripts/publish_frontend_exp.sh

# 指定底座 / 日期 / 只本地构建
BASE_RELEASE=v1.0.4-5 EXP_DATE=20260916 bash scripts/publish_frontend_exp.sh
PUSH=0 bash scripts/publish_frontend_exp.sh          # 本地 load，便于先冒烟
SKIP_BUILD=1 bash scripts/publish_frontend_exp.sh    # 复用已有 dist，仅重打镜像
```

脚本做的事：解析底座 release → 宿主机原生构建 exp 前端（`npm ci && npm run build-only`）
→ 组装最小上下文（`dist/` + 指向 `web-exp` 的 nginx 模板 + `BUILD_INFO`）
→ `docker buildx build --platform linux/amd64,linux/arm64 --push`
→ 推 `frontend-exp-<日期>` 与 `frontend-exp` → 校验 manifest。

它**不会**触碰 `frontend`、`latest`、`backend` 与 `base-*` 标签。

### 4.2 部署

替换式（把 exp 当作独立前端节点，既有的 `frontend` 镜像仍可随时回退）：

```bash
bash deploy/docker/deploy_witty.sh --role frontend \
  --image hub-harbor.oepkgs.net/neocopilot/witty-ub:frontend-exp-20260916
```

与既有前端同机并行（对比验收）：

```bash
docker run -d --name witty-ub-frontend-exp --restart unless-stopped \
  -p 32414:8080 \
  -v ~/.config/opencode:/root/.config/opencode \
  -e WITTY_ROLE=frontend \
  -e WITTY_BACKEND_URL=http://<后端IP>:9772 \
  hub-harbor.oepkgs.net/neocopilot/witty-ub:frontend-exp-20260916
```

> 容器内仍是 8080（nginx root 指向 `/var/witty-ub/web-exp`），并行时用 32414 与既有前端的
> 32413 错开；两个容器各自运行 OpenCode，互不影响。

### 4.3 验证

```bash
curl -I  http://<前端IP>:32414/                       # 200，页面标题为 witty-ub
curl -s  http://<前端IP>:32414/health_check           # 后端经反代 200
curl -s  http://<前端IP>:32414/agent-api/global/health  # {"healthy":true,...}
docker exec witty-ub-frontend-exp cat /var/witty-ub/web-exp/BUILD_INFO
```

---

## 5. 链路 B：源码 / 宿主机部署

适用于开发调试与不便于打镜像的机器（openEuler 24.03 验证通过）。

### 5.1 依赖

```bash
sudo dnf install -y nginx nodejs npm gettext rsync
node -v   # 需要 >= 20.18.2
```

### 5.2 安装与启动

```bash
# 默认后端指向本机 9772；分离部署时指向后端节点
WITTY_BACKEND_URL=http://<后端IP>:9772 \
  bash deploy/host/deploy_frontend_exp.sh install
```

脚本流程：构建 `src/web_new`（或已改名的 `src/web_exp`）→ 发布 `dist/` 到
`/var/witty-ub/web-exp` → 用 `packaging/nginx/witty-ub-web-exp.conf.template` 渲染
`nginx.conf`（8081）→ 安装并启动 systemd user unit `witty-ub-frontend-exp.service`
（无 systemd --user 时回退 nohup 托管）。

其它子命令：

```bash
bash deploy/host/deploy_frontend_exp.sh status      # 单元状态 + 首页/健康检查
bash deploy/host/deploy_frontend_exp.sh stop
bash deploy/host/deploy_frontend_exp.sh uninstall   # 停服务 + 清理 /var/witty-ub/web-exp
```

环境变量：`WITTY_BACKEND_URL`、`WITTY_AGENT_URL`、`WITTY_WEB_EXP_PORT`（默认 8081）、
`EXP_WEB_DIR`（默认自动选择 `src/web_exp` / `src/web_new`）、`DEPLOY_PM=systemd|nohup`。

跨机部署（前端节点 + 后端节点分离）时注意两点：

- 传入的 `WITTY_BACKEND_URL` / `WITTY_AGENT_URL` / `WITTY_WEB_EXP_PORT` 会写入
  `.deploy-run/frontend-exp.env`，由 systemd 单元 `EnvironmentFile` 加载，服务重启或
  机器重启后仍指向同一后端；改动后端地址只需重新执行 `install`（或修改该文件后 `restart`）。
- 后端节点需对新的前端节点放行 9772（与既有前端节点相同）：
  `firewall-cmd --permanent --add-rich-rule='rule family=ipv4 source address=<前端IP>/32 port port=9772 protocol=tcp accept' && firewall-cmd --reload`。

### 5.3 验证

```bash
curl -I  http://127.0.0.1:8081/
curl -s  http://127.0.0.1:8081/health_check
curl -s  http://127.0.0.1:8081/agent-api/global/health
systemctl --user status witty-ub-frontend-exp.service --no-pager
cat /var/witty-ub/web-exp/BUILD_INFO   # 若通过脚本发布 dist 时生成
```

### 5.4 Agent（OpenCode）

exp 前端与既有前端共用本机（或远端）OpenCode：`/agent-api/` 由 nginx 反代到
`WITTY_AGENT_URL`（默认 `http://127.0.0.1:4096`）。启动方式与既有前端相同：

```bash
set -a; source /etc/witty-ub/web/env 2>/dev/null || true; set +a
bash deploy/deploy_opencode.sh
```

如需让 OpenCode 常驻并开机自启，可使用 `deploy/host/systemd/witty-ub-opencode.service`
（systemd **user** unit）——它与默认的裸进程托管互斥（都监听 4096），安装方式见
[宿主机脚本部署](02-script-host.md) 的「可选：把 OpenCode 注册为 systemd user 服务」：

```bash
bash deploy/host/install_opencode_service.sh install
curl -s http://127.0.0.1:8081/agent-api/global/health   # exp 前端反代到本机 OpenCode
```

---

## 6. 链路 C：RPM（私仓）

### 6.1 包说明

子包 `witty-ub-web-exp` 与主包**同 `Version-Release`**（如 `1.0.4-6`），只在私有
EulerMaker 工程构建；上游打包仓不受影响。

| 路径 | 内容 |
| ------ | ------ |
| `/var/witty-ub/web-exp/` | exp 前端静态产物（含 `BUILD_INFO`） |
| `/etc/witty-ub/web-exp/env` | 连接配置（`WITTY_BACKEND_URL` / `WITTY_AGENT_URL` / `WITTY_WEB_EXP_PORT`） |
| `/usr/share/witty-ub/nginx/witty-ub-web-exp.conf.template` | Nginx 模板（8081） |
| `/usr/lib/systemd/system/witty-ub-web-exp.service` | systemd 系统服务 |
| `/usr/bin/witty-ub-web-exp-ctl` | 控制脚本（渲染配置 + 启停 + SELinux 标签） |

> Agent（OpenCode）不在本子包内：AI 助手功能需要节点上已安装 OpenCode
> （`npm i -g opencode-ai`），并使用 Agent bundle（随 `witty-ub-web` 子包提供）或用户自己的
> OpenCode 配置；纯浏览/查询页面不依赖 Agent。

### 6.2 构建（私有打包仓 / rpmbuild）

资产与 spec 改动位于打包仓（`src-openeuler/witty-ub`）的 `feat/frontend-exp` 分支：
`Patch74` 携带运行时资产，`Source1` 为预构建的前端 dist 压缩包。

```bash
# 1) 生成 exp 前端 dist 压缩包（在源码仓执行）
cd src/web_new && npm ci --no-audit --no-fund && npm run build-only && cd ../..
# macOS 上需 COPYFILE_DISABLE=1，避免打包出 ._* 元数据文件
COPYFILE_DISABLE=1 tar -czf witty-ub-web-exp-dist.tar.gz -C src/web_new dist

# 2) 准备 rpmbuild 工作树（SOURCES 需含 Source0 压缩包、全部 patch 与 Source1）
rpmdev-setuptree
cd /path/to/src-openeuler-witty-ub
cp witty-ub-v1.0.4.tar.gz witty-ub-web-exp-dist.tar.gz ./*.patch ~/rpmbuild/SOURCES/
cp witty-ub.spec ~/rpmbuild/SPECS/
rpmbuild -bb ~/rpmbuild/SPECS/witty-ub.spec
```

构建产物：`witty-ub-web-exp-<version>-<release>.<arch>.rpm`（与主包同版本号）。

### 6.3 安装与使用

```bash
sudo dnf install -y witty-ub-web-exp
sudo witty-ub-web-exp-ctl enable --backend http://<后端IP>:9772
sudo witty-ub-web-exp-ctl status
```

nightly 更新（版本号不变，靠日期化私仓路径区分）：

```bash
# 私仓 repo 文件按日期切路径后刷新
sudo dnf --refresh reinstall -y witty-ub-web-exp
cat /var/witty-ub/web-exp/BUILD_INFO     # 确认当天构建
```

回滚：把私仓 `.repo` 的 `baseurl` 指回旧日期路径后再次 `reinstall`。

> 私仓 `.repo` 建议加 `includepkgs=witty-ub-web-exp`，确保官方 `witty-ub-web` /
> `witty-ub-backend` / `witty-ub-manager` 不会被私仓内容替换。

### 6.4 验证

```bash
rpm -q witty-ub-web witty-ub-web-exp            # 两者同版本，互不冲突
systemctl status witty-ub-web-exp --no-pager
curl -I http://127.0.0.1:8081/
curl -s http://127.0.0.1:8081/health_check
```

---

## 7. 回滚与卸载

| 链路 | 停止 exp | 彻底移除 |
| ------ | ------ | ------ |
| 容器 | `docker stop witty-ub-frontend-exp` | `docker rm witty-ub-frontend-exp`（既有容器不受影响） |
| 源码 | `bash deploy/host/deploy_frontend_exp.sh stop` | `... uninstall` |
| RPM | `sudo witty-ub-web-exp-ctl disable` | `sudo dnf remove -y witty-ub-web-exp` |

三条链路的回滚都不影响既有前端（8080/5173/32413）、后端（9772）与数据库。

---

## 8. 常见问题

| 现象 | 处理 |
| ------ | ------ |
| `npm ci` 报 Node 版本不支持 | 升级到 Node ≥ 20.18.2（openEuler 24.03 源内 `nodejs-20.18.2` 可用） |
| 8081 被占用 | `ss -tlnp \| grep 8081`；改 `WITTY_WEB_EXP_PORT` 后重启 |
| 页面打开但接口 502 | 后端不可达：确认 `WITTY_BACKEND_URL` 与后端防火墙（9772） |
| `/agent-api/` 502 | OpenCode 未启动：`bash deploy/deploy_opencode.sh`，或检查 4096 |
| RPM 安装后首页 404 | 先执行 `witty-ub-web-exp-ctl enable`（`%post` 只做安装，不自动启动），并确认配置已渲染 |
| SELinux 拒绝（RPM） | `witty-ub-web-exp-ctl enable` 会自动设置端口/目录标签与 `httpd_can_network_connect`；可 `ausearch -m AVC -ts recent` 复核 |
| `dnf upgrade` 拿不到新 nightly | 属预期：NVR 不变，需 `dnf --refresh reinstall witty-ub-web-exp`（或切换日期化 repo 路径） |
| 构建机无法多架构构建 | 使用 `docker-container` driver：`docker buildx create --name witty-ub-builder --driver docker-container --use` |

---

## 9. 相关文档

- 设计文档 → [experimental-frontend-deployment.md](../design/experimental-frontend-deployment.md)
- 镜像构建 / 分发 → [01-docker-build.md](../package/01-docker-build.md) | [03-distribution.md](../package/03-distribution.md)
- 既有部署方式 → [02-script-host.md](02-script-host.md) | [03-script-container.md](03-script-container.md) | [07-rpm.md](07-rpm.md) | [08-container.md](08-container.md)
