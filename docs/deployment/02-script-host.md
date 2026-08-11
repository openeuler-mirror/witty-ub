# 宿主机脚本部署

## 概述

使用 `deploy/host/deploy.sh` 一键完成宿主机部署，自动完成系统依赖安装、PostgreSQL 初始化、Python 虚拟环境创建、C++ 诊断工具编译和服务启动。

适合开发调试和快速上手。

---

## 前置条件

- openEuler 24.03 LTS 或 Ubuntu 24.04 / WSL
- sudo 权限（安装系统包和启动 PostgreSQL）

---

## 一键部署

```bash
# 克隆仓库
git clone https://gitcode.com/openeuler/witty-ub.git
cd witty-ub

# 一键部署（首次运行约 5-10 分钟）
bash deploy/host/deploy.sh
```

部署完成后，浏览器打开 **`http://localhost:5173`**。

---

## 脚本完成的工作

| 步骤 | 内容 |
|------|------|
| ① OS 检测 | 自动识别 openEuler / Ubuntu，选择对应包管理器 (dnf / apt) |
| ② 系统依赖 | 安装 cmake, gcc-c++, PostgreSQL, Python3, Node.js 等 |
| ③ PostgreSQL | 创建 `witty-ub` 数据库和用户，监听 15432 端口 |
| ④ Python | 创建 `.venv` 虚拟环境，安装 FastAPI/SQLAlchemy/asyncpg 等依赖 |
| ⑤ C++ 编译 | 编译 `witty-ub-diag-tool` 诊断工具 |
| ⑥ 数据文件 | 将故障模式、配置文件复制到 `/var/witty-ub/` |
| ⑦ 启动服务 | 启动 FastAPI 后端 (9772) + Vite 前端 (5173) |

---

## 常用命令

```bash
# 仅启动服务（已部署过，跳过安装和编译）
bash deploy/host/deploy.sh --start

# 停止所有服务
bash deploy/host/deploy.sh --stop

# 一键清理
bash deploy/host/deploy.sh --clean

# 仅安装依赖（不启动服务）
bash deploy/host/install_deps.sh
```

---

## 服务说明

| 服务 | 地址 | 用途 |
|------|------|------|
| 前端 (Vite) | `http://localhost:5173` | Web 管理界面 |
| 后端 (FastAPI) | `http://localhost:9772` | 日志解析 / 异常检测 API |
| 健康检查 | `http://localhost:9772/health_check` | 服务可用性探测 |
| PostgreSQL | `127.0.0.1:15432` | 数据存储 |

---

## 日志

所有服务的运行日志位于 `.deploy-logs/` 目录：

```bash
# 查看后端日志
tail -f .deploy-logs/backend.log

# 查看前端日志
tail -f .deploy-logs/frontend.log
```

---

## 验证部署

```bash
# 后端健康检查
curl http://localhost:9772/health_check

# 浏览器访问
# http://localhost:5173
```

---

## 已知问题

- **sudo 权限**：安装系统包和启动 PostgreSQL 需要 `sudo` 权限。如果当前用户无 sudo 权限，脚本会提示需要手动执行的命令。
- **C++ 编译失败**：如果缺少 C++ 编译依赖导致诊断工具编译失败，脚本会自动生成一个 shell 存根替代。故障定界功能将不可用，但日志解析和异常检测仍正常工作。
- **端口冲突**：默认使用 5173（前端）和 9772（后端）。如需修改，编辑 `src/web/vite.config.ts` 和 `src/plugins/latency/access/fastapi_server.py`。
- **WSL**：建议 WSL 版本 >= 2，并在 `wsl.conf` 中启用 systemd。

---

## 后续步骤

- 脚本详细说明 → [../../deploy/docker/README.md](../../deploy/docker/README.md)
- 手动数据库部署 → [05-database.md](05-database.md)
- 手动源码部署 → [06-source.md](06-source.md)
- 手动 RPM 部署 → [07-rpm.md](07-rpm.md)
- 手动容器部署 → [08-container.md](08-container.md)
