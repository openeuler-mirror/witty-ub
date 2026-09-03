# witty-ub RPM 包部署

## 概述

适用于 openEuler 原生部署场景，通过 systemd 管理服务。**前后端默认支持分离部署**：RPM 拆分为四个子包，按节点角色安装所需负载，管理工具 `witty-ub manager` 自动探测本机角色并只操作本机服务。

| 包名 | 内容 | 安装位置 |
| ------ | ------ | ------ |
| `witty-ub-backend` | FastAPI 后端、C++ 诊断工具、故障模式数据 | 后端节点 |
| `witty-ub-web` | Web 前端、Nginx 模板、OpenCode Agent 提示词与启动脚本 | 前端节点 |
| `witty-ub-manager` | `witty-ub` 命令与部署管理器 | 两端自动依赖安装 |
| `witty-ub` | meta 包，一键安装上述三个子包 | 单机部署 |

节点定义见[架构概览](01-overview.md)：后端节点部署在有数据的机器上，前端节点部署在能访问大模型服务的机器上。

| 节点 | 安装 | 运行的服务 |
| ------ | ------ | ----------- |
| 后端节点 | `witty-ub-backend` | `postgresql`(5432，服务名按已装包自动探测) + `witty-ub-latency`(9772) |
| 前端节点 | `witty-ub-web` | `witty-ub-web`(8080) + OpenCode(4096，手动启动) |
| 单机 | `witty-ub` | 以上全部 |

---

## 前置条件

- openEuler 24.03 LTS SP3 / SP4
- root 或 sudo 权限

> PostgreSQL 不需要预装，`witty-ub manager deploy` 会自动初始化（仅后端节点需要）。

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

### ① 后端节点

```bash
sudo dnf install -y witty-ub-backend   # 自动依赖 witty-ub-manager
sudo witty-ub manager deploy           # 初始化 PostgreSQL + 启动 latency
```

验证并仅对前端节点开放 9772：

```bash
curl http://127.0.0.1:9772/health_check   # 200
firewall-cmd --permanent --add-rich-rule='rule family=ipv4 source address=<前端IP>/32 port port=9772 protocol=tcp accept'
firewall-cmd --reload
```

### ② 前端节点

```bash
sudo dnf install -y witty-ub-web       # 自动依赖 witty-ub-manager

# 配置后端地址并启动（渲染 Nginx 反代，Agent 通过环境变量取得后端地址）
sudo witty-ub manager deploy --backend http://<后端IP>:9772
```

配置 OpenCode，然后通过交互菜单启动 Agent：

```bash
npm i -g opencode-ai   # 或参考 [opencode 官方文档](https://opencode.ai/zh/download)
vi ~/.config/opencode/opencode.jsonc   # 参考 [配置参考手册 · OpenCode 配置](../usage/03-configuration-reference.md#opencode-配置)

# 如果 OpenCode 连接大模型需要读取环境变量，先 export 再打开交互菜单
export XXX=value
sudo -E witty-ub manager
# 依次选择“a) 启动 / 停止 Agent 服务（OpenCode）”和“1) 启动 Agent 服务”
```

`sudo -E` 用于将当前 shell 中已 `export` 的环境变量传递给 RPM 管理器及其启动的 OpenCode 进程；是否允许保留环境变量受本机 sudo 策略控制。不需要额外环境变量时，可以直接执行 `sudo witty-ub manager`。

验证：

```bash
curl http://127.0.0.1:8080/                 # Web 200
curl http://127.0.0.1:8080/health_check     # 远端后端经反代 200
curl http://127.0.0.1:8080/agent-api/doc    # OpenCode 经反代 200
```

浏览器访问 `http://<前端IP>:8080`。

### 切换后端地址

前端节点修改后端地址，自动重渲染配置并重启服务：

```bash
sudo witty-ub manager config --backend http://<新后端IP>:9772
sudo witty-ub manager config --show        # 查看当前角色与连接配置
```

OpenCode 如在运行，需重启以加载新地址：

```bash
sudo witty-ub manager
# 进入“a) 启动 / 停止 Agent 服务（OpenCode）”，先停止再启动 Agent 服务
```

---

## 单机部署

前后端在同一台机器时，安装 meta 包一键装入全部子包：

```bash
sudo dnf install -y witty-ub
sudo witty-ub manager deploy
```

完成后访问 `http://<服务器IP>:8080`。

---

## PG 连接配置（后端节点）

PG 凭据位于 `/etc/witty-ub/deploy.conf`，旧安装的 `pg.conf` 自动兼容。默认值：`host=127.0.0.1 port=5432 db/user/pass=witty-ub`。

如需修改，例如指向外部 PG，编辑后重新执行 `sudo witty-ub manager deploy` 即可同步生效。

---

## 服务管理

`witty-ub manager` 按本机已安装子包探测角色，只操作本机服务：

```bash
sudo witty-ub manager             # 交互式菜单
sudo witty-ub manager deploy      # 完整部署
sudo witty-ub manager deps        # 仅安装/更新依赖
sudo witty-ub manager start       # 启动本机角色的服务
sudo witty-ub manager stop        # 停止
sudo witty-ub manager restart     # 重启
sudo witty-ub manager status      # 查看状态
sudo witty-ub manager logs        # 查看日志
sudo witty-ub manager psql        # 进入 psql（仅后端节点）
```

| 服务 | 落位 | 端口 |
| ------ | ------ | ------ |
| `witty-ub-web` | 前端节点（Nginx） | 8080 |
| `witty-ub-latency` | 后端节点（FastAPI） | 9772 |
| `postgresql` | 后端节点（数据库） | 5432 |

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
sudo dnf update -y witty-ub-backend && sudo witty-ub manager restart   # 后端节点升级
sudo dnf update -y witty-ub-web && sudo witty-ub manager restart      # 前端节点升级
sudo witty-ub manager clean                # 两档清理（PG + 运行数据 / 再加 venv 和日志）
sudo dnf remove -y witty-ub-backend witty-ub-manager    # 后端节点彻底卸载
sudo dnf remove -y witty-ub-web witty-ub-manager        # 前端节点彻底卸载
sudo dnf remove -y witty-ub witty-ub-backend witty-ub-web witty-ub-manager   # 单机彻底卸载
```

> 从旧版单包 `witty-ub` 升级：直接 `sudo dnf update -y witty-ub`，meta 包会拉入三个子包，角色自动探测为单机，已有数据与配置保留。

---

## 故障排查

| 问题 | 排查 |
| ------ | ------ |
| 后端 9772 起不来 | `sudo witty-ub manager logs`；最常见 PG 未就绪/密码不匹配 → `sudo witty-ub manager deploy` |
| 前端 8080 起不来 | `ss -tlnp \| grep 8080` 查端口占用；检查 `/etc/witty-ub/web/nginx.conf` 是否已渲染后端地址 |
| 前端页面接口 502 | 确认后端 9772 可达（`curl http://<后端IP>:9772/health_check`），检查后端防火墙 |
| psql 连不上 | `systemctl status postgresql`；`cat /etc/witty-ub/deploy.conf` |
| 重置一切 | `sudo witty-ub manager clean` → `sudo witty-ub manager deploy` |

---

## 后续步骤

- 数据库手动部署 → [05-database.md](05-database.md)
- 宿主机脚本部署 → [02-script-host.md](02-script-host.md)
- 容器脚本部署 → [03-script-container.md](03-script-container.md)
