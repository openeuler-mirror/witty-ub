# witty-ub RPM 包部署

## 概述

适用于 openEuler 原生部署场景，通过 systemd 管理服务。**前后端默认支持分离部署**：RPM 内 `witty-ub-latency`（FastAPI 后端）与 `witty-ub-web`（Nginx 前端）是相互独立的服务，可分别部署在不同机器上。`yum install witty-ub` 后，使用 `witty-ub manager` 完成 PG 初始化、服务启停、数据清理、日志查看等运维操作。

| 机器 | 安装 | 启用的服务 |
|------|------|-----------|
| 后端节点（有数据的机器） | `witty-ub` | `postgresql-15` + `witty-ub-latency`(9772)，禁用 `witty-ub-web` |
| 前端节点（能访问 Agent/LLM） | `witty-ub` | `witty-ub-web`(8080) + OpenCode(4096)，禁用 `witty-ub-latency` |

---

## 前置条件

- openEuler 24.03 LTS SP3 / SP4
- root 或 sudo 权限

> PostgreSQL 不需要预装，`witty-ub manager install` 会自动初始化（仅后端节点需要）。

---

## 配置 RPM 仓库

两台机器均需配置（或使用离线 rpm 包安装）：

### openEuler 24.03-LTS-SP3

```bash
sudo tee /etc/yum.repos.d/witty-ub.repo <<'EOF'
[witty-ub]
name=witty-ub
baseurl=http://121.36.84.172/dailybuild/EBS-openEuler-24.03-LTS-SP3/openeuler-2026-07-08-07-31-12/everything/$basearch/
enabled=1
gpgcheck=0
EOF
```

### openEuler 24.03-LTS-SP4

```bash
sudo tee /etc/yum.repos.d/witty-ub.repo <<'EOF'
[witty-ub]
name=witty-ub
baseurl=http://121.36.84.172/dailybuild/EBS-openEuler-24.03-LTS-SP4/openeuler-2026-07-08-07-31-12/everything/$basearch/
enabled=1
gpgcheck=0
EOF
```

> 注意：repo 源中的日期目录（如 `2026-07-08-07-31-12`）需替换为最新的每日构建目录。

---

## 分离部署（默认：两台机器）

### ① 后端节点（有数据的机器）

```bash
sudo yum install -y witty-ub
sudo witty-ub manager install          # 初始化 PostgreSQL + 启动服务

# 该机器不跑前端, 禁用 Web 服务
sudo systemctl disable --now witty-ub-web
```

验证并仅对前端节点开放 9772：

```bash
curl http://127.0.0.1:9772/health_check   # 200
firewall-cmd --permanent --add-rich-rule='rule family=ipv4 source address=<前端IP>/32 port port=9772 protocol=tcp accept'
firewall-cmd --reload
```

### ② 前端节点（能访问 Agent/LLM 的机器）

```bash
sudo yum install -y witty-ub

# 该机器不跑后端, 禁用 latency 与 PG
sudo systemctl disable --now witty-ub-latency 2>/dev/null || true
```

渲染 Nginx 配置，使 API 反代指向远端后端（`/agent-api/` 反代本机 OpenCode）：

```bash
sudo mkdir -p /etc/witty-ub/web /var/witty-ub/web
export WITTY_BACKEND_URL=http://<后端IP>:9772
export WITTY_AGENT_URL=http://127.0.0.1:4096
sudo -E envsubst '${WITTY_BACKEND_URL} ${WITTY_AGENT_URL}' \
  < /usr/share/witty-ub/nginx/witty-ub-web.conf.template \
  | sudo tee /etc/witty-ub/web/nginx.conf >/dev/null   # 模板路径以实际安装为准
sudo systemctl enable --now witty-ub-web
```

配置并启动 OpenCode Agent：

```bash
npm i -g opencode-ai   # 或参考 [opencode 官方文档](https://opencode.ai/zh/download)
vi ~/.config/opencode/opencode.jsonc   # 参考 配置参考手册 · OpenCode 配置

WITTY_API_BASE=http://<后端IP>:9772 \
  bash /var/witty-ub/latency/deploy/run_opencode.sh
```

验证：

```bash
curl http://127.0.0.1:8080/                 # Web 200
curl http://127.0.0.1:8080/health_check     # 远端后端经反代 200
curl http://127.0.0.1:8080/agent-api/doc    # OpenCode 经反代 200
```

浏览器访问 `http://<前端IP>:8080`。

---

## 单机部署（前后端同机）

前后端在同一台机器时，两个服务全部启用（默认行为）：

```bash
sudo yum install -y witty-ub
sudo witty-ub manager install    # 初始化 PostgreSQL + 启动服务
```

完成后访问 `http://<服务器IP>:8080`。

---

## PG 连接配置（后端节点）

PG 凭据位于 `/etc/witty-ub/pg.conf`，默认值：`host=127.0.0.1 port=15432 db/user/pass=witty-ub`。

如需修改（如指向外部 PG），编辑后重新执行 `sudo witty-ub manager install` 即可同步生效。

---

## 服务管理

```bash
sudo witty-ub manager             # 交互式菜单
sudo witty-ub manager start       # 启动
sudo witty-ub manager stop        # 停止
sudo witty-ub manager restart     # 重启
sudo witty-ub manager status      # 查看状态
sudo witty-ub manager logs        # 查看日志
sudo witty-ub manager psql        # 进入 psql
```

| 服务 | 落位 | 端口 |
|------|------|------|
| `witty-ub-web` | 前端节点（Nginx） | 8080 |
| `witty-ub-latency` | 后端节点（FastAPI） | 9772 |
| `postgresql-15` | 后端节点（数据库） | 15432 |

---

## 验证

```bash
# 后端节点
curl http://localhost:9772/health_check

# 前端节点
curl -I http://localhost:8080
curl http://localhost:8080/health_check   # 经反代访问远端后端
```

---

## 升级 / 卸载 / 清理

```bash
sudo yum update -y witty-ub && sudo witty-ub manager restart   # 升级（两台机器分别执行）
sudo witty-ub manager clean                                    # 清空数据（PG 表 + /var 数据，后端节点）
sudo witty-ub manager uninstall                                # 停服务 + 禁用 units
sudo yum remove -y witty-ub witty-ub-manager                   # 彻底卸载 RPM
```

---

## 故障排查

| 问题 | 排查 |
|------|------|
| 后端 9772 起不来 | `sudo witty-ub manager logs`；最常见 PG 未就绪/密码不匹配 → `sudo witty-ub manager install` |
| 前端 8080 起不来 | `ss -tlnp \| grep 8080` 查端口占用；分离部署时检查 `/etc/witty-ub/web/nginx.conf` 是否已渲染 `WITTY_BACKEND_URL` |
| 前端页面接口 502 | 确认后端 9772 可达（`curl http://<后端IP>:9772/health_check`），检查后端防火墙 |
| psql 连不上 | `systemctl status postgresql-15`；`cat /etc/witty-ub/pg.conf` |
| 重置一切 | `sudo witty-ub manager clean` → `sudo witty-ub manager install` |

---

## 后续步骤

- 数据库手动部署 → [05-database.md](05-database.md)
- 宿主机脚本部署 → [02-script-host.md](02-script-host.md)
- 容器脚本部署 → [03-script-container.md](03-script-container.md)
