# 宿主机脚本部署

## 概述

使用 `deploy/host/deploy.sh` 一键完成宿主机部署。脚本按 `--role`（或环境变量 `WITTY_ROLE`）区分角色：

- **后端节点**（`--role backend`，有数据的机器）：PostgreSQL + Python 依赖 + C++ 工具链编译 + 数据文件 + FastAPI(9772)，不需要 Node.js/出网
- **前端节点**（`--role frontend`，能访问 Agent/LLM 的机器）：前端编译 + Nginx 托管(8080) + 反代远端后端 + OpenCode Agent
- **单机**（`--role all`，默认）：两个角色叠加在同一台机器

两台机器都从同一份源码仓库部署，前端节点通过 `WITTY_BACKEND_URL` 指向后端节点。

---

## 前置条件

### 后端节点

- Linux（脚本按实际可用的 dnf、yum 或 apt-get 选择依赖安装方式，不限定发行版及版本）
- sudo 权限、git、内存至少 8GB，Python 依赖安装和 C++ 编译内存占用较高
- 软件源已配置：yum/dnf 源与 pypi 源，pypi 源通过 `~/.pip/pip.conf` 的 `index-url` 指定。内网或无外网环境必须提前配置
- 数据文件位于仓库 `data/`，或挂载数据卷到 `/var/witty-ub/data`

### 前端节点

- sudo 权限、git、npm 源已配置，registry 位于项目根目录或 `src/web/.npmrc`
- Node.js 18+ 与 nginx 均可由脚本自动安装；nginx 缺失时回退 vite preview
- 能出网访问大模型服务；已安装 OpenCode 并配置 LLM key：

```bash
npm i -g opencode-ai
vi ~/.config/opencode/opencode.jsonc   # 参考 配置参考手册 · OpenCode 配置
```

Agent 的技能（`witty_ub_diagnostician/skills/`）通过 `uv run experience-skill ...`
检索本地经验库，因此前端节点还需要 Python 包管理器 `uv` 与已同步的经验库——
`deploy/host/install_deps.sh` 会自动装好（`uv` 装到 `/usr/local/bin`，systemd user
服务的 PATH 不含 `~/.local/bin`），无需手工准备。

---

## 分离部署（默认：两台机器）

### ① 后端节点

```bash
git clone https://gitcode.com/openeuler/witty-ub.git && cd witty-ub

# 部署后端（PG + 依赖 + C++ 编译 + 数据 + FastAPI）
NONINTERACTIVE=1 bash deploy/host/deploy.sh --deploy --role backend
```

验证：

```bash
curl http://127.0.0.1:9772/health_check   # 200
```

### ② 前端节点

```bash
git clone https://gitcode.com/openeuler/witty-ub.git && cd witty-ub

# 指向后端节点部署前端（Web + Agent）
NONINTERACTIVE=1 WITTY_BACKEND_URL=http://<后端IP>:9772 \
  bash deploy/host/deploy.sh --deploy --role frontend
```

脚本自动完成：前端编译 `dist/` → 发布到 `/var/witty-ub/web`（nginx 静态托管）→ 渲染 Nginx 配置（API 反代 `WITTY_BACKEND_URL`，`/agent-api/` 反代本机 OpenCode）→ 导出 Agent 运行时环境变量 → 启动 OpenCode(4096) + Nginx(8080)。Agent 提示词文件保持仓库原文。

验证：

```bash
curl http://127.0.0.1:8080/                 # 前端页面 200
curl http://127.0.0.1:8080/health_check     # 远端后端经反代 200
curl http://127.0.0.1:8080/agent-api/doc    # OpenCode 经反代 200
```

浏览器访问 `http://<前端IP>:8080`。

### 后端防火墙（仅对前端节点开放 9772）

```bash
firewall-cmd --permanent --add-rich-rule='rule family=ipv4 source address=<前端IP>/32 port port=9772 protocol=tcp accept'
firewall-cmd --reload
```

---

## 单机部署（前后端同机）

前后端在同一台机器时，使用默认角色 `all`（行为与历史版本一致）：

```bash
bash deploy/host/deploy.sh --deploy
```

| 步骤 | 内容 |
| ------ | ------ |
| ① 包管理器检测 | 自动识别 dnf / yum / apt-get，选择 RPM 或 APT 依赖安装路径 |
| ② 系统依赖 | 安装 cmake, gcc-c++, PostgreSQL, Python3, Node.js, nginx 等 |
| ③ PostgreSQL | 调用 `deploy_pg.sh` 初始化，创建 `witty-ub` 数据库和用户，监听 5432 端口 |
| ④ Python 环境 | 创建 `.venv` 虚拟环境，安装 FastAPI/SQLAlchemy/asyncpg/polars 等依赖 |
| ④' Agent 运行时 | 前端节点额外准备 Agent 技能工具链：安装 `uv`、编译 simple 分词器、`uv sync`、同步经验库（`experience-skill sync`） |
| ⑤ 前端编译 | `npm run build-only` 构建 `dist/`（失败回退 dev server，不阻塞部署） |
| ⑥ C++ 编译 | 编译 `witty-ub-diag-tool` 诊断工具（已存在则跳过） |
| ⑦ 数据文件 | 将故障模式、配置文件复制到 `/var/witty-ub/` |
| ⑧ 凭据同步 | 仅将 host/port/user/db 写入 `diagnosis_config.toml`；后端启动时从 `deploy/pg.passwd` 读取密码并注入进程环境 |
| ⑨ 启动服务 | FastAPI(9772) + 前端（vite preview 5173；`--role frontend` 时改为 nginx 8080）+ OpenCode(4096) |

### 验证部署

```bash
curl http://localhost:9772/health_check
curl -s -o /dev/null -w "%{http_code}" http://localhost:5173/   # 单机默认（vite preview）
```

> `--role all` 的单机部署用 Vite 模式（`run_frontend_vite.sh`，5173）托管构建产物；
> Nginx 模式（`run_frontend_nginx.sh`，8080）用于 `--role frontend` 的分离部署。单机也要
> Nginx 模式时，构建完 `dist/` 后执行 `bash deploy/host/run_frontend_nginx.sh start`，即可
> 保留 5173 并在 8080 提供静态托管 + 反代入口（详见 [源码部署](06-source.md)）。

---

## 其他操作

### 启动 OpenCode Agent

OpenCode 服务支持通过交互菜单或直接运行脚本启动。

通过交互菜单启动时，如果 OpenCode 连接大模型需要读取环境变量，应先 `export` 再打开菜单：

```bash
# 前端节点还需设置 WITTY_ROLE=frontend 和实际后端地址
export WITTY_ROLE=frontend
export WITTY_API_BASE=http://<后端IP>:9772
export XXX=value

bash deploy/host/deploy.sh
# 选择“5) 启动 Agent 服务（OpenCode）”
```

直接运行脚本时，可以先 `export` 再启动：

```bash
export XXX=value
bash deploy/deploy_opencode.sh
```

也可以只为本次启动显式指定变量：

```bash
XXX=value bash deploy/deploy_opencode.sh
```

上述环境变量会由 OpenCode 及其子进程继承。若服务已经运行，需要先停止旧进程再使用新环境变量启动。

#### 可选：把 OpenCode 注册为 systemd user 服务

`deploy.sh` 默认把 OpenCode 作为**裸进程 + pidfile** 托管（`deploy/deploy_opencode.sh`），
进程退出或机器重启后不会自动拉起，需要人工重新启动。若希望 Agent 常驻并开机自启
（例如前端节点长期在线、VM/开发机），可改用 systemd user 单元托管：

```bash
# 安装 + 启用 + 启动（默认后端 http://127.0.0.1:9772）
bash deploy/host/install_opencode_service.sh install

# 分离部署时指定远端后端（Agent 的 curl 需绕过代理）
WITTY_API_BASE=http://<后端IP>:9772 WITTY_NO_PROXY='*' \
  bash deploy/host/install_opencode_service.sh install

bash deploy/host/install_opencode_service.sh status
bash deploy/host/install_opencode_service.sh uninstall   # 改回裸进程托管
```

- 单元模板：`deploy/host/systemd/witty-ub-opencode.service`（渲染 `__PROJECT_DIR__`、
  `__OPENCODE_BIN__`、`__WITTY_API_BASE__`、`__WITTY_NO_PROXY__` 后写入
  `~/.config/systemd/user/`）。
- 两种托管方式都监听 4096，**互斥**：切换到单元托管前先停止裸进程
  （`deploy.sh` 菜单里的"停止 Agent 服务"），反之亦然。
- 需要 `systemctl --user` 可用（openEuler：`sudo dnf install -y systemd-pam` +
  `loginctl enable-linger <user>`）；RPM 部署请使用 `witty-ub manager` 的 Agent 菜单，
  不要使用该 user 单元。

### 仅启动服务（已部署过）

```bash
bash deploy/host/deploy.sh --start                       # 单机
WITTY_ROLE=backend bash deploy/host/deploy.sh --start    # 后端节点
WITTY_ROLE=frontend WITTY_BACKEND_URL=http://<后端IP>:9772 \
  bash deploy/host/deploy.sh --start                     # 前端节点
```

跳过安装和编译，仅启动对应角色的服务。

### 停止服务

```bash
bash deploy/host/deploy.sh --stop
```

### 一键清理

```bash
bash deploy/host/deploy.sh --clean
# 选择清理范围:
#   1) 停服务 + 清空 PG 数据 + 清 /var/witty-ub（保留构建产物，可秒级重装）
#   2) 以上全部 + 删除 build/ + .venv/ + 部署日志（彻底干净）

# 非交互式（CI/自动化）
CLEAN_SCOPE=2 NONINTERACTIVE=1 bash deploy/host/deploy.sh --clean
```

### 仅安装依赖

```bash
bash deploy/host/install_deps.sh
```

---

## 配置说明

### 角色与分离部署变量

| 变量 | 默认值 | 说明 |
| ------ | -------- | ------ |
| `WITTY_ROLE` | `all` | `--role` 参数与其等价：`all` / `backend` / `frontend` |
| `WITTY_BACKEND_URL` | `http://127.0.0.1:9772` | 前端节点的后端反代上游（前端节点必填为后端地址） |
| `WITTY_API_BASE` | 跟随 `WITTY_BACKEND_URL` | Agent 提示词中的后端基址 |
| `WITTY_NO_PROXY` | `127.0.0.1` | Agent curl `--noproxy` 参数 |
| `WITTY_AGENT_URL` | `http://127.0.0.1:4096` | `/agent-api/` 反代上游 |

### 配置文件 deploy.conf（后端节点）

部署脚本读取 `deploy/deploy.conf` 的 PostgreSQL 连接配置。密码存放在独立密钥文件 `deploy/pg.passwd`（权限 0400），不回写 `deploy.conf`：

```conf
PG_HOST="127.0.0.1"
PG_PORT_RPM="5432"
PG_DATABASE="witty-ub"
PG_USER="witty-ub"
PG_PASSWORD="<CHANGE_ME>"     # 仅占位符，实际口令在 deploy/pg.passwd
```

首次部署时 `deploy_pg.sh` 会交互输入或自动生成随机口令，写入 `deploy/pg.passwd`。
运行时 TOML 不保存密码且权限为 `0600`；systemd 与 nohup 使用统一启动器读取密钥。

### 环境变量覆盖

通过环境变量临时覆盖 `deploy.conf` 中的配置：

```bash
PG_HOST=10.0.0.5 PG_PORT_RPM=5432 bash deploy/host/deploy.sh --start
```

### 进程托管方式

`start_services` 按 `DEPLOY_PM` 环境变量选择托管方式（默认 `auto`）：

| 值 | 行为 |
| ---- | ------ |
| `auto`（默认） | systemd user units 优先；`systemctl --user` 不可用时自动回退 nohup 裸进程 + PID 文件 |
| `systemd` | 强制 systemd 托管（不可用时明确报错） |
| `nohup` | 强制裸进程托管（测试 / 排障） |

---

## 已知问题

- **AI 助手一直卡在 `uv: command not found`**：前端节点缺 `uv`（Agent 技能全部经由 `uv run experience-skill ...` 检索经验库）。执行 `bash deploy/host/install_deps.sh` 补装；验证：`command -v uv && cd witty_ub_diagnostician/skills/experience-skill/scripts && uv run experience-skill list-experiences | head -3`
- **AI 助手检索结果恒为 0 条**：经验库未同步。`cd witty_ub_diagnostician/skills/experience-skill/scripts && uv run experience-skill sync`（应为 28 个 Skill + 32 篇 Wiki）
- **系统包安装失败（yum/dnf 源不可达）**：检查 `/etc/yum.repos.d/` 是否已配置内网镜像源，`yum repolist` 验证可达性
- **Python 依赖安装失败（pypi 源不可达）**：检查 `~/.pip/pip.conf` 的 `index-url` 是否指向内网镜像，或手动 `pip install -r src/plugins/latency/deploy/requirements.txt` 验证
- **前端编译失败（npm registry 不可达）**：检查 `.npmrc` 的 `registry` 配置；编译失败不阻塞部署，可 `cd src/web && npm run dev` 用开发模式
- **`systemctl --user` 不可用**：openEuler 24.03+ 缺 `systemd-pam` 包，执行 `sudo dnf install -y systemd-pam` 恢复；脚本已自动回退 nohup，不阻塞部署
- **后端启动超时**：最常见是 PostgreSQL 密码/端口配置错误。查看 `journalctl --user -u witty-ub-backend.service` 或 `.deploy-logs/backend.log` 定位
- **前端节点页面打不开/接口 502**：确认 `WITTY_BACKEND_URL` 指向正确且后端 9772 可达（`curl http://<后端IP>:9772/health_check`），检查后端防火墙
- **端口冲突**：前端 8080 / 后端 9772 被占。`ss -tlnp | grep -E '8080|9772'` 检查占用
- **C++ 编译失败**：缺少编译依赖。按报错补装后重跑 `cmake . -DCMAKE_BUILD_TYPE=Release && make -j$(nproc) witty-ub-diag-tool`
- **PostgreSQL 未就绪**：`pg_isready -h 127.0.0.1 -p 5432` 检查；或设置 `PG_HOST` / `PG_PORT_RPM` 指向正确数据库

---

## 后续步骤

- 脚本详细说明 → [../../deploy/host/README.md](../../deploy/host/README.md)
- 手动数据库部署 → [05-database.md](05-database.md)
- 手动源码部署 → [06-source.md](06-source.md)
- 手动 RPM 部署 → [07-rpm.md](07-rpm.md)
- 手动容器部署 → [08-container.md](08-container.md)
