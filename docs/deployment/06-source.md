# witty-ub 源码编译部署

## 概述

适用于开发调试或定制化修改场景。需要在宿主机上安装编译工具链。

> 生产环境建议使用脚本部署 → [宿主机脚本部署](02-script-host.md) | [容器脚本部署](03-script-container.md)

---

## 前置条件

### 编译工具链

```bash
sudo yum install -y \
  gcc-c++ make cmake \
  log4cplus-devel cpp-httplib-devel sqlite-devel \
  jsoncpp-devel tinyxml2-devel openssl-devel \
  zlib-devel brotli-devel re2-devel
```

### 运行时

- Python 3.9+、Node.js 18+、npm

### PostgreSQL

请先完成 PG 部署 → [05-database.md](05-database.md)

---

## 编译构建

```bash
# 获取源码
git clone https://gitcode.com/openeuler/witty-ub.git witty-ub && cd witty-ub

# 编译 C++ 代码
mkdir build
cmake -S . -B build
cmake --build build -j$(nproc)
```

产物：`build/src/witty-ub-log`、`witty-ub-topo`、`witty-ub-diag-tool`

---

## 安装部署

```bash
# 复制数据
sudo mkdir -p /var/witty-ub
sudo cp -r ./data /var/witty-ub/
sudo cp -r ./config /var/witty-ub/

# 设置环境变量
export WITTY_DIR=/var/witty-ub
export WITTY_INSTALL_PATH=$(pwd)/build/src
export PYTHONPATH=$PYTHONPATH:$(pwd)/src/plugins
```

---

## 安装 OpenCode

```bash
# RPM 安装
npm i -g opencode-ai # 或按照 [opencode 官方文档](https://opencode.ai/zh/download) 安装

# 修改配置，参考 [配置参考手册 · OpenCode 配置](../usage/03-configuration-reference.md#opencode-配置)
vi ~/.config/opencode/opencode.jsonc

# 启动后台服务
bash ./src/plugins/latency/deploy/run_opencode.sh
```

---

## 启动服务

### 后端（FastAPI）

```bash
cd src/plugins/latency
python3 -m venv .venv && source .venv/bin/activate
pip install -r deploy/requirements.txt
python3 access/fastapi_server.py
# 监听端口: 9772
```

### 前端（Web）

```bash
cd src/web
npm install
npm run dev -- --host
# 监听端口: 5173
```

---

## PG 连接配置

```bash
# 设置环境变量（与 pg.conf 保持一致）
export PG_HOST=127.0.0.1
export PG_PORT=15432
export PG_DATABASE=witty-ub
export PG_USER=witty-ub
export PG_PASSWORD=witty-ub
```

---

## 验证

```bash
# 后端健康检查
curl http://localhost:9772/health_check

# 浏览器访问
# http://localhost:5173
```

---

## 防火墙

```bash
firewall-cmd --permanent --add-port=5173/tcp
firewall-cmd --reload
```

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
