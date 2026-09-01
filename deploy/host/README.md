# witty-ub 宿主机部署脚本

## 概述

本目录包含 witty-ub 的宿主机（裸金属 / 源码）部署脚本，一键完成系统依赖安装、PostgreSQL 初始化、Python 虚拟环境创建、前端编译、C++ 诊断工具编译和服务启动。

适合开发调试和快速上手。

---

## 脚本文件

| 文件 | 说明 |
|------|------|
| `deploy.sh` | 一键部署入口（交互式菜单 / 完整部署 / 启动 / 停止 / 清理） |
| `install_deps.sh` | 系统依赖 + Python venv 依赖安装 |
| `run_frontend.sh` | 前端启动器（vite preview 托管 dist/，无 dist 时回退 dev server） |
| `systemd/` | systemd user unit 模板（`witty-ub-backend.service` / `witty-ub-frontend.service`） |
| `_lib.sh` | 共享工具库（色彩日志 / OS 检测 / PG 凭据加载，被其他脚本 source） |

---

## 快速开始

### 交互式菜单（默认）

```bash
bash deploy/host/deploy.sh
```

```
========================================
  witty-ub 宿主机部署管理器
========================================

  📦  安装
    1) 完整部署（依赖 + PostgreSQL + 编译 + 启动）
    2) 仅安装依赖

  🔧  管理
    3) 仅启动服务（已部署过）
    4) 停止所有服务

  🗑️  清理
    5) 一键清理（交互选择范围）

    0) 退出
```

### 命令行模式

```bash
# 直接完整部署（跳过菜单，首次运行约 5-10 分钟）
bash deploy/host/deploy.sh --deploy

# 仅启动服务（已部署过，跳过安装和编译）
bash deploy/host/deploy.sh --start

# 停止所有服务
bash deploy/host/deploy.sh --stop

# 一键清理（交互选择范围）
bash deploy/host/deploy.sh --clean

# 仅安装依赖（不启动服务）
bash deploy/host/install_deps.sh
```

部署完成后，浏览器打开 **`http://localhost:5173`**。

---

## 内部调用链

```
deploy.sh
  ├── (无参数) 交互式菜单
  │     ├── [1] 完整部署 → main_deploy
  │     ├── [2] 仅安装依赖 → install_deps.sh
  │     ├── [3] 仅启动服务 → start_services
  │     ├── [4] 停止服务 → stop_services
  │     └── [5] 一键清理 → clean_all
  ├── --deploy 直接完整部署（跳过菜单）
  │     └── main_deploy
  │           ├── install_deps.sh           # 系统依赖 + Python venv
  │           ├── deploy_pg.sh --rpm|--apt  # PostgreSQL 初始化
  │           ├── build_frontend            # npm run build-only → dist/
  │           ├── build_cpp                 # cmake + make witty-ub-diag-tool
  │           ├── copy_data_files           # 数据文件 → /var/witty-ub/
  │           ├── sync_pg_credentials       # pg.conf 凭据 → diagnosis_config.toml
  │           └── start_services            # systemd units / nohup 回退
  ├── --start 仅启动服务
  │     └── start_services
  ├── --stop  停止服务
  │     └── stop_services
  └── --clean 一键清理
        └── clean_all
```

---

## 部署流程

脚本自动完成以下步骤：

1. **OS 检测**：自动识别 openEuler / Ubuntu，选择对应包管理器（dnf / apt）
2. **系统依赖**：安装 cmake、gcc-c++、PostgreSQL、Python3、Node.js 等（openEuler 24.03+ 另装 `systemd-pam`）
3. **PostgreSQL**：调用 `deploy_pg.sh` 初始化，创建 `witty-ub` 数据库和用户，监听 15432 端口
4. **Python 环境**：创建 `.venv` 虚拟环境，安装 FastAPI / SQLAlchemy / asyncpg / polars 等依赖
5. **前端编译**：`npm run build-only` 构建 `dist/`（编译失败回退 dev server，不阻塞部署）
6. **C++ 编译**：编译 `witty-ub-diag-tool` / `witty-ub-brpc-diag` 诊断工具（源码或 `CMakeLists.txt` 比二进制新则重编；`FORCE_REBUILD_CPP=1` 强制重编）
7. **数据文件**：将故障模式树、配置文件复制到 `/var/witty-ub/`
8. **凭据同步**：将 `deploy/deploy.conf` 的实际 PG 凭据写入 `diagnosis_config.toml`
9. **启动服务**：启动 FastAPI 后端 (9772) + Vite 前端 (5173)，等待健康检查通过

---

## 配置文件

### pg.conf

部署脚本读取 `deploy/pg.conf` 的 PostgreSQL 连接配置，修改后全局生效：

```conf
# ---------- 数据库连接配置 ----------
PG_HOST="127.0.0.1"        # 宿主机访问地址
PG_PORT="15432"            # 监听端口
PG_DATABASE="witty-ub"
PG_USER="witty-ub"
PG_PASSWORD="witty-ub"

# ---------- RPM 部署专用 ----------
# PG_DATA_DIR=""           # 数据目录（留空自动探测）
```

### 环境变量覆盖

通过环境变量临时覆盖 `pg.conf` 中的配置：

```bash
PG_HOST=10.0.0.5 PG_PORT=5432 bash deploy/host/deploy.sh
```

### 进程托管方式

`start_services` 按 `DEPLOY_PM` 环境变量选择托管方式（默认 `auto`）：

| 值 | 行为 |
|----|------|
| `auto`（默认） | systemd user units 优先；`systemctl --user` 不可用时自动回退 nohup 裸进程 + PID 文件 |
| `systemd` | 强制 systemd 托管（不可用时明确报错） |
| `nohup` | 强制裸进程托管（测试 / 排障） |

> `systemctl --user` 强依赖 `pam_systemd.so`（openEuler 24.03+ 拆到独立包 `systemd-pam`）。
> 缺失时 user 会话 PAM 加载失败 → `systemctl --user` 全部不可用 → 自动回退 nohup。

### 强制重新编译 C++

`build_cpp` 默认按 mtime 判定：`src/` 下任一源码（`*.cpp/*.cc/*.c/*.h/*.hpp`）或任一 `CMakeLists.txt` 比两个二进制中较旧的那个新就重编，否则跳过。改了 cpp 但二进制还在时不会再误判为已编译。

强制重编（绕过 mtime 检查）：

```bash
FORCE_REBUILD_CPP=1 bash deploy/host/deploy.sh --deploy
```

---

## 常见场景

### 已部署过，只重启服务

```bash
bash deploy/host/deploy.sh --start
# 跳过安装和编译，仅启动前后端
```

### 服务器无 systemd user 会话（回退 nohup）

```bash
bash deploy/host/deploy.sh --start
# 自动检测 systemctl --user 不可用 → 回退 nohup 托管
# 日志在 .deploy-logs/backend.log / frontend.log

# 恢复 systemd 托管（推荐，获得崩溃自愈/开机自启）
sudo dnf install -y systemd-pam   # openEuler 24.03+
# 或 Ubuntu: sudo apt-get install -y libpam-systemd
```

### 强制使用 nohup 托管

```bash
DEPLOY_PM=nohup bash deploy/host/deploy.sh --start
```

### 清理重装

```bash
bash deploy/host/deploy.sh --clean
# 选择清理范围:
#   1) 停服务 + 清空 PG 数据 + 清 /var/witty-ub（推荐, 保留构建产物秒级重装）
#   2) 以上全部 + 删除 build/ + .venv/ + 部署日志（彻底干净）

# 非交互式（CI/自动化）:
CLEAN_SCOPE=2 NONINTERACTIVE=1 bash deploy/host/deploy.sh --clean
```

---

## 日志

部署日志位于项目根目录 `.deploy-logs/`：

| 文件 | 内容 |
|------|------|
| `backend.log` | 后端运行日志（nohup 模式） |
| `frontend.log` | 前端运行日志（nohup 模式） |
| `pip-install.log` | Python 依赖安装日志 |
| `cpp-build.log` | C++ 编译日志 |
| `frontend-build.log` | 前端编译日志 |

systemd 托管时使用 `journalctl`：

```bash
journalctl --user -u witty-ub-backend.service -f
journalctl --user -u witty-ub-frontend.service -f
```

---

## 故障排查

| 问题 | 排查方式 |
|------|---------|
| `systemctl --user` 不可用 | openEuler 24.03+ 安装 `systemd-pam`；或 `loginctl enable-linger <用户>`。脚本已自动回退 nohup 不阻塞 |
| 后端启动超时 / 健康检查失败 | `journalctl --user -u witty-ub-backend.service` 或 `.deploy-logs/backend.log`（最常见：PG 密码/端口配置错误） |
| 前端 5173 无响应 | 确认 `src/web/dist/` 存在（无 dist 时回退 dev server）；`run_frontend.sh` 用 `--strictPort`，端口被占会立即失败 |
| 端口冲突 | `ss -tlnp \| grep 5173` / `ss -tlnp \| grep 9772` |
| C++ 编译失败 | 按报错补装依赖后重跑；`cmake . -DCMAKE_BUILD_TYPE=Release && make -j\$(nproc) witty-ub-diag-tool` |
| 前端编译失败 | `npm ping` 检查 registry 可达性；编译失败不阻塞部署，可先 `npm run dev` 用开发模式 |
| PostgreSQL 未就绪 | `pg_isready -h 127.0.0.1 -p 15432`；或设置 `PG_HOST` / `PG_PORT` 指向正确数据库 |

---

## 相关文档

- [宿主机脚本部署](../../docs/deployment/02-script-host.md)
- [容器脚本部署](../../docs/deployment/03-script-container.md)
- [手动数据库部署](../../docs/deployment/05-database.md)
- [手动源码部署](../../docs/deployment/06-source.md)
- [手动 RPM 部署](../../docs/deployment/07-rpm.md)
- [手动容器部署](../../docs/deployment/08-container.md)
