# witty-ub 源码编译部署

## 概述

适用于开发调试或定制化修改场景，需要在宿主机上安装编译工具链。**前后端默认分离部署**：后端节点跑 FastAPI + C++ 工具链 + 数据 + PG（无需 Node.js/出网），前端节点跑 Web + OpenCode Agent（需出网访问 LLM）。前后端同机时两套步骤在同一台机器执行即可。

> 生产环境建议使用脚本部署 → [宿主机脚本部署](02-script-host.md)（`--role backend/frontend` 自动完成下述步骤） | [容器脚本部署](03-script-container.md)

---

## 后端节点（有数据的机器）

### 前置条件

```bash
sudo yum install -y \
  gcc-c++ make cmake \
  log4cplus-devel cpp-httplib-devel sqlite-devel \
  jsoncpp-devel tinyxml2-devel openssl-devel \
  zlib-devel brotli-devel re2-devel \
  python3 python3-pip git
```

- Python 3.9+（`python3 -m venv` 可用）；`pip install` 需要 pypi 源，内网环境先配置
  `~/.pip/pip.conf` 的 `index-url`
- PostgreSQL：由下文[准备 PG 凭据](#准备-pg-凭据)的 `deploy/deploy_pg.sh --rpm` 自动安装并
  初始化；使用已有/外部 PG 时见 [05-database.md](05-database.md)

### 编译 C++ 工具链

```bash
git clone https://gitcode.com/openeuler/witty-ub.git witty-ub && cd witty-ub
mkdir build
cmake -S . -B build
cmake --build build -j$(nproc)
```

产物：`build/src/witty-ub-log`、`witty-ub-topo`、`witty-ub-diag-tool`

### 安装数据

```bash
sudo mkdir -p /var/witty-ub
sudo cp -r ./data /var/witty-ub/
sudo cp -r ./config /var/witty-ub/
```

数据目录默认为 `/var/witty-ub`；`deploy/host/run_backend.sh` 会自动设置 `PYTHONPATH` 与
`WITTY_INSTALL_PATH=<仓库>/build/src`。构建产物或数据放在别处时，用同名环境变量覆盖。

### 准备 PG 凭据

PG 连接配置：

```bash
export PG_HOST=127.0.0.1
export PG_PORT=5432         # 源码/RPM 部署统一使用 PostgreSQL 标准端口
export PG_DATABASE=witty-ub
export PG_USER=witty-ub
```

口令不写在配置文件里，也不建议 `export`，而是放在权限为 `0400` 的密钥文件
`deploy/pg.passwd`，由 `deploy/host/run_backend.sh` 启动时读入后端进程。**没有这个文件
后端会直接启动失败**（`[error] 未找到 PostgreSQL 口令`），先按下面任一方式生成：

```bash
# 方式一（推荐）：由部署脚本初始化/对齐 PG 并生成随机口令
sudo bash deploy/deploy_pg.sh --rpm     # Ubuntu/Debian 用 --apt

# 方式二：PG 已另行初始化（例如按 05-database.md 手工建库），把已知口令写入密钥文件
printf '%s' '<PG 口令>' | install -m 0400 /dev/stdin deploy/pg.passwd

# 确认结果（期望属主是运行后端的用户，权限 0400）
ls -l deploy/pg.passwd     # -r-------- <部署用户> ... deploy/pg.passwd
```

> 密钥文件必须能被**运行后端的那个用户**读取：若以 `sudo` 执行 `deploy_pg.sh`，脚本会把
> 属主改回当前登录用户；若整条流程都用 root 执行，而服务以普通用户运行，需要手工
> `sudo chown $(id -u):$(id -g) deploy/pg.passwd`。
>
> 口令缺失或不可读时，`run_backend.sh` 会打印已查找的路径、补口令的三种方式，以及密钥
> 存在但属主不可读时的修复命令。

### 启动 FastAPI

```bash
cd src/plugins/latency
python3 -m venv .venv && source .venv/bin/activate
pip install -r deploy/requirements.txt
cd ../../..
deploy/host/run_backend.sh
# 监听 0.0.0.0:9772, 需对前端节点可达
```

### 验证与防火墙

```bash
curl http://127.0.0.1:9772/health_check   # 200

# 仅对前端节点开放 9772
firewall-cmd --permanent --add-rich-rule='rule family=ipv4 source address=<前端IP>/32 port port=9772 protocol=tcp accept'
firewall-cmd --reload
```

---

## 前端节点（能访问 Agent/LLM 的机器）

### 构建前端

前置：Node.js ≥ 20.18.2（与 `src/web/package.json` 的 `engines.node` 一致）。

```bash
# 发行版软件源（openEuler 24.03 提供 20.18.2）
sudo yum install -y nodejs npm

# 源内版本偏低时改用官方预编译包（按 uname -m 选择 arm64 / x64）
URL=https://nodejs.org/dist/latest-v22.x/
ARCH=$(uname -m | sed 's/x86_64/x64/; s/aarch64/arm64/')
FILE=$(curl -s "$URL" | grep -oE "node-v22\.[0-9]+\.[0-9]+-linux-$ARCH\.tar\.xz" | sort -V | tail -1)
sudo mkdir -p /opt/node22
curl -fsSL "$URL$FILE" | sudo tar -xJ -C /opt/node22 --strip-components=1
sudo ln -sf /opt/node22/bin/node /usr/local/bin/node
sudo ln -sf /opt/node22/bin/npm /usr/local/bin/npm

node --version        # 需 >= 20.18.2
```

构建：

```bash
git clone https://gitcode.com/openeuler/witty-ub.git witty-ub && cd witty-ub/src/web
npm config set registry <npm 镜像地址>   # 内网环境按需配置, 公网可略过
npm install
npm run build-only   # 产物 dist/
```

### 启动 OpenCode Agent

```bash
npm i -g opencode-ai   # 或参考 [opencode 官方文档](https://opencode.ai/zh/download)
vi ~/.config/opencode/opencode.jsonc   # 写入大模型 provider 与 API key, 见 [配置参考手册 · OpenCode 配置](../usage/03-configuration-reference.md#opencode-配置)
```

OpenCode 服务支持以下两种启动方式。

#### 方式一：通过交互菜单启动

```bash
cd witty-ub

# 前端节点需指定后端地址
export WITTY_ROLE=frontend
export WITTY_API_BASE=http://<后端IP>:9772

# 如果 OpenCode 连接大模型还需要其他环境变量，先 export 再打开菜单
export XXX=value

bash deploy/host/deploy.sh
# 在菜单中选择“5) 启动 Agent 服务（OpenCode）”
```

通过交互菜单启动时，OpenCode 会继承打开菜单前已 `export` 的环境变量。

#### 方式二：直接运行启动脚本

```bash
cd witty-ub

# 指向后端节点启动（变量导出给 OpenCode/Agent Bash 子进程）
WITTY_API_BASE=http://<后端IP>:9772 \
  bash deploy/deploy_opencode.sh
# 监听 127.0.0.1:4096
```

如果 OpenCode 连接大模型还需要其他环境变量，可以先 `export` 再运行脚本：

```bash
export XXX=value
bash deploy/deploy_opencode.sh
```

也可以只为本次启动显式指定变量：

```bash
XXX=value bash deploy/deploy_opencode.sh
```

以上两种写法中的环境变量都会由 OpenCode 及其子进程继承。若服务已经运行，需要先停止旧进程再使用新环境变量启动。

`deploy_opencode.sh` 支持的变量：`WITTY_API_BASE`（默认 `http://127.0.0.1:9772`）、`WITTY_NO_PROXY`（默认 `127.0.0.1`）、`OPENCODE_HOST`（默认 `127.0.0.1`）、`OPENCODE_CONFIG` / `OPENCODE_CONFIG_DIR`（自定义 OpenCode 配置，已设置时不覆盖；未设置时使用随包 bundle，详见[配置参考](../usage/03-configuration-reference.md#opencode-配置)）。

随包 bundle 提供 `witty-ub-diagnostician` 诊断 Agent 与诊断 Skills，经 `OPENCODE_CONFIG_DIR` 注入，与用户 `~/.config/opencode/` 下的配置和 Skills 合并生效。

### 启动前端（Nginx 模式）

前端由 nginx 托管 `dist/` 构建产物，并把 API 与 `/agent-api/` 反代到后端和本机 OpenCode。

前置：安装 nginx（`sudo yum install -y nginx`，Debian 系用 `apt-get`）。

```bash
cd witty-ub

# 前端节点：WITTY_BACKEND_URL 指向后端节点；单机保持默认 127.0.0.1
export WITTY_BACKEND_URL=http://<后端IP>:9772   # API 反代上游
export WITTY_AGENT_URL=http://127.0.0.1:4096    # /agent-api/ 反代上游

bash deploy/host/run_frontend_nginx.sh start     # 监听 8080
bash deploy/host/run_frontend_nginx.sh status    # 进程状态 + 反代健康检查
bash deploy/host/run_frontend_nginx.sh reload    # 改地址/改端口后重载
bash deploy/host/run_frontend_nginx.sh stop      # 停止
```

启动器依次完成三件事：

1. 把 `src/web/dist/` 发布到 `/var/witty-ub/web`（nginx worker 通常降权运行，无法穿透用户
   home 目录的 `750` 权限，因此不直接托管 `~/witty-ub/src/web/dist`）
2. 以 `packaging/nginx/witty-ub-web.conf.template` 渲染配置到 `<仓库>/.deploy-run/nginx.conf`
3. `nginx -t` 校验后启动，并 curl `http://127.0.0.1:<端口>/` 自检

环境变量：

| 变量 | 默认值 | 说明 |
| --- | --- | --- |
| `WITTY_BACKEND_URL` | `http://127.0.0.1:9772` | API 反代上游 |
| `WITTY_AGENT_URL` | `http://127.0.0.1:4096` | `/agent-api/` 反代上游 |
| `WITTY_WEB_PORT` | `8080` | 监听端口 |
| `WITTY_WEB_ROOT` | `/var/witty-ub/web` | 静态根目录 |
| `WITTY_WEB_CONF` | `<仓库>/.deploy-run/nginx.conf` | 渲染出的配置路径 |

运行时文件：

| 文件 | 路径 |
| --- | --- |
| nginx 配置 | `<仓库>/.deploy-run/nginx.conf` |
| PID | `<仓库>/.deploy-run/nginx.pid` |
| 错误日志 | `<仓库>/.deploy-logs/web-error.log` |
| 访问日志 | `<仓库>/.deploy-logs/web-access.log` |

启动的 nginx 是裸进程：机器重启后需重新执行 `start`，需要开机自启时交给 systemd 托管
（可参考 RPM 包的系统单元 `witty-ub-web.service`）。该配置是独立配置（自带 `events`/`http`，
由 `-c` 指定），`systemctl reload nginx` 对它无效，重载用启动器的 `reload` 子命令。

### 启动前端（Vite 模式，可选）

没有 nginx 时可用 Vite 模式：`vite preview` 托管 `dist/`（无 dist 时回退 dev server），
监听 5173，不需要 root。API 与 `/agent-api/` 反代由 `src/web/vite.config.ts` 的
`server.proxy` 提供，上游经环境变量指定：

```bash
VITE_DEV_API_TARGET=http://<后端IP>:9772 \
  VITE_DEV_AGENT_TARGET=http://127.0.0.1:4096 \
  bash deploy/host/run_frontend_vite.sh
```

两种模式的区别：对外提供服务的入口用 Nginx 模式（8080，与容器/RPM 部署一致，带 20G 大文件
流式转发与 SSE 长连接参数）；Vite 模式（5173）不需要 root、可由 systemd user unit
`witty-ub-frontend.service` 托管，适合单机部署与开发调试。

### 运行时切换后端（可选）

前端构建产物目录下的 `config.json` 支持不改构建切换后端：

```json
{
  "apiBase": "",              // 留空 = 同源（经 Nginx 反代）
  "agentApiBase": "/agent-api"
}
```

### 验证

```bash
curl http://127.0.0.1:8080/                 # 前端页面 200
curl http://127.0.0.1:8080/health_check     # 远端后端经反代 200
curl http://127.0.0.1:8080/agent-api/doc    # OpenCode 经反代 200
```

浏览器访问 `http://<前端IP>:8080`。

### 防火墙

```bash
firewall-cmd --permanent --add-port=8080/tcp
firewall-cmd --reload
```

---

## 单机（前后端同机）

后端节点与前端节点的全部步骤在同一台机器执行，`WITTY_BACKEND_URL` / `WITTY_API_BASE` 保持默认 `http://127.0.0.1:9772` 即可。开发模式下也可直接 `npm run dev`（监听 5173）。

前端入口为 `bash deploy/host/run_frontend_nginx.sh start` 启动的 `http://<IP>:8080`
（静态托管 + 同源反代后端与 `/agent-api/`）；`npm run dev`（5173）仅用于开发调试。

---

## 开发调试

```bash
# 重新编译
cmake --build build -j$(nproc)

# 后端日志
tail -f src/plugins/latency/logs/*.log
```

---

## 后续步骤

- 手动数据库部署 → [05-database.md](05-database.md)
- 宿主机脚本部署 → [02-script-host.md](02-script-host.md)
- 容器脚本部署 → [03-script-container.md](03-script-container.md)
