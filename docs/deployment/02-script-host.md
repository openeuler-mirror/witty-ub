# 宿主机脚本部署

## 概述

使用 `deploy/host/deploy.sh` 一键完成宿主机部署，自动完成系统依赖安装、PostgreSQL 初始化、Python 虚拟环境创建、前端编译、C++ 诊断工具编译和服务启动。

适合开发调试和快速上手。

---

## 前置条件

- **操作系统**：openEuler 24.03 LTS 或 Ubuntu 24.04 / WSL
- **sudo 权限**：安装系统包和启动 PostgreSQL
- **git**：克隆仓库（或已获取源码包）
- **软件源已配置（默认内网/无外网环境，必需）**：部署脚本需从各软件源拉取依赖，外网不可达时必须先配置内网镜像源：
  - **yum/dnf 源**：系统包（cmake、gcc-c++、PostgreSQL、nodejs 等）。配置 `/etc/yum.repos.d/` 指向内网镜像，`yum repolist` 可验证
  - **pypi 源**：Python 依赖（`pip install -r requirements.txt`）。配置 `~/.pip/pip.conf` 的 `index-url` 指向内网镜像
  - **npm 源**：前端依赖（`npm install`）。配置项目根目录或 `src/web/.npmrc` 的 `registry` 指向内网镜像
- **内存**：至少 8GB（Python 依赖安装和 C++ 编译较吃内存）

---

## 一键部署

```bash
# 克隆仓库
git clone https://gitcode.com/openeuler/witty-ub.git
cd witty-ub

# 交互式菜单（默认）
bash deploy/host/deploy.sh
# 选择 [1] 完整部署

# 或直接完整部署（跳过菜单）
bash deploy/host/deploy.sh --deploy

# 首次运行约 5-10 分钟
```

脚本自动完成：

| 步骤 | 内容 |
|------|------|
| ① OS 检测 | 自动识别 openEuler / Ubuntu，选择对应包管理器 (dnf / apt) |
| ② 系统依赖 | 安装 cmake, gcc-c++, PostgreSQL, Python3, Node.js 等（openEuler 24.03+ 另装 `systemd-pam`） |
| ③ PostgreSQL | 调用 `deploy_pg.sh` 初始化，创建 `witty-ub` 数据库和用户，监听 15432 端口 |
| ④ Python 环境 | 创建 `.venv` 虚拟环境，安装 FastAPI/SQLAlchemy/asyncpg/polars 等依赖 |
| ⑤ 前端编译 | `npm run build-only` 构建 `dist/`（失败回退 dev server，不阻塞部署） |
| ⑥ C++ 编译 | 编译 `witty-ub-diag-tool` 诊断工具（已存在则跳过） |
| ⑦ 数据文件 | 将故障模式、配置文件复制到 `/var/witty-ub/` |
| ⑧ 凭据同步 | 将 `deploy/pg.conf` 的实际 PG 凭据写入 `diagnosis_config.toml` |
| ⑨ 启动服务 | 启动 FastAPI 后端 (9772) + Vite 前端 (5173)，等待健康检查通过 |

### 验证部署

部署完成后验证服务是否正常：

```bash
# 后端健康检查
curl http://localhost:9772/health_check

# 前端 HTTP 状态
curl -s -o /dev/null -w "%{http_code}" http://localhost:5173/

# 浏览器访问
# http://localhost:5173
```

---

## 其他操作

### 直接完整部署（跳过菜单）

```bash
bash deploy/host/deploy.sh --deploy
```

### 仅启动服务（已部署过）

```bash
bash deploy/host/deploy.sh --start
```

跳过安装和编译，仅启动前后端。

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

### 配置文件 pg.conf

部署脚本读取 `deploy/pg.conf` 的 PostgreSQL 连接配置：

```conf
PG_HOST="127.0.0.1"
PG_PORT="15432"
PG_DATABASE="witty-ub"
PG_USER="witty-ub"
PG_PASSWORD="witty-ub"
```

### 环境变量覆盖

通过环境变量临时覆盖 `pg.conf` 中的配置：

```bash
PG_HOST=10.0.0.5 PG_PORT=5432 bash deploy/host/deploy.sh --start
```

### 进程托管方式

`start_services` 按 `DEPLOY_PM` 环境变量选择托管方式（默认 `auto`）：

| 值 | 行为 |
|----|------|
| `auto`（默认） | systemd user units 优先；`systemctl --user` 不可用时自动回退 nohup 裸进程 + PID 文件 |
| `systemd` | 强制 systemd 托管（不可用时明确报错） |
| `nohup` | 强制裸进程托管（测试 / 排障） |

---

## 已知问题

- **系统包安装失败（yum/dnf 源不可达）**：检查 `/etc/yum.repos.d/` 是否已配置内网镜像源，`yum repolist` 验证可达性
- **Python 依赖安装失败（pypi 源不可达）**：检查 `~/.pip/pip.conf` 的 `index-url` 是否指向内网镜像，或手动 `pip install -r src/plugins/latency/deploy/requirements.txt` 验证
- **前端编译失败（npm registry 不可达）**：检查 `.npmrc` 的 `registry` 配置；编译失败不阻塞部署，可 `cd src/web && npm run dev` 用开发模式
- **`systemctl --user` 不可用**：openEuler 24.03+ 缺 `systemd-pam` 包，执行 `sudo dnf install -y systemd-pam` 恢复；脚本已自动回退 nohup，不阻塞部署
- **后端启动超时**：最常见是 PostgreSQL 密码/端口配置错误。查看 `journalctl --user -u witty-ub-backend.service` 或 `.deploy-logs/backend.log` 定位
- **端口冲突**：前端 5173 / 后端 9772 被占。`ss -tlnp | grep 5173` 或 `ss -tlnp | grep 9772` 检查占用
- **C++ 编译失败**：缺少编译依赖。按报错补装后重跑 `cmake . -DCMAKE_BUILD_TYPE=Release && make -j$(nproc) witty-ub-diag-tool`
- **PostgreSQL 未就绪**：`pg_isready -h 127.0.0.1 -p 15432` 检查；或设置 `PG_HOST` / `PG_PORT` 指向正确数据库

---

## 后续步骤

- 脚本详细说明 → [../../deploy/host/README.md](../../deploy/host/README.md)
- 手动数据库部署 → [05-database.md](05-database.md)
- 手动源码部署 → [06-source.md](06-source.md)
- 手动 RPM 部署 → [07-rpm.md](07-rpm.md)
- 手动容器部署 → [08-container.md](08-container.md)
