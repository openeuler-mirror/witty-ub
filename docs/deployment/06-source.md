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
  zlib-devel brotli-devel re2-devel
```

- Python 3.9+
- PostgreSQL → [05-database.md](05-database.md)

### 编译 C++ 工具链

```bash
git clone https://gitcode.com/openeuler/witty-ub.git witty-ub && cd witty-ub
mkdir build
cmake -S . -B build
cmake --build build -j$(nproc)
```

产物：`build/src/witty-ub-log`、`witty-ub-topo`、`witty-ub-diag-tool`

### 安装数据与环境变量

```bash
sudo mkdir -p /var/witty-ub
sudo cp -r ./data /var/witty-ub/
sudo cp -r ./config /var/witty-ub/

export WITTY_DIR=/var/witty-ub
export WITTY_INSTALL_PATH=$(pwd)/build/src
export PYTHONPATH=$PYTHONPATH:$(pwd)/src/plugins
```

### 启动 FastAPI

```bash
cd src/plugins/latency
python3 -m venv .venv && source .venv/bin/activate
pip install -r deploy/requirements.txt
python3 access/fastapi_server.py
# 监听 0.0.0.0:9772, 需对前端节点可达
```

PG 连接配置：

```bash
export PG_HOST=127.0.0.1
export PG_PORT=15432        # 以实际 PG 配置为准：脚本部署默认 15432，RPM 手动部署默认 5432
export PG_DATABASE=witty-ub
export PG_USER=witty-ub
export PG_PASSWORD=witty-ub
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

```bash
git clone https://gitcode.com/openeuler/witty-ub.git witty-ub && cd witty-ub/src/web
npm install
npm run build-only   # 产物 dist/
```

### 启动 OpenCode Agent

```bash
npm i -g opencode-ai   # 或参考 [opencode 官方文档](https://opencode.ai/zh/download)
vi ~/.config/opencode/opencode.jsonc   # 参考 配置参考手册 · OpenCode 配置

# 指向后端节点启动（渲染 Agent 提示词中的后端基址）
cd witty-ub
WITTY_API_BASE=http://<后端IP>:9772 \
  bash deploy/deploy_opencode.sh
# 监听 127.0.0.1:4096
```

`deploy_opencode.sh` 支持的变量：`WITTY_API_BASE`（默认 `http://127.0.0.1:9772`）、`WITTY_NO_PROXY`（默认 `127.0.0.1`）、`OPENCODE_HOST`（默认 `127.0.0.1`）、`OPENCODE_CONFIG` / `OPENCODE_CONFIG_DIR`（自定义 OpenCode 配置，已设置时不覆盖；未设置时使用随包 bundle，详见[配置参考](../usage/03-configuration-reference.md#opencode-配置)）。

随包 bundle 提供 `witty-ub-diagnostician` 诊断 Agent 与诊断 Skills，经 `OPENCODE_CONFIG_DIR` 注入，与用户 `~/.config/opencode/` 下的配置和 Skills 合并生效。

### 启动 Web（Nginx 托管 + 反代）

使用仓库自带的 Nginx 模板渲染配置（API 反代远端后端，`/agent-api/` 反代本机 OpenCode）：

```bash
sudo mkdir -p /var/witty-ub/web
sudo cp -r dist/ /var/witty-ub/web/

export WITTY_BACKEND_URL=http://<后端IP>:9772   # API 反代上游
export WITTY_AGENT_URL=http://127.0.0.1:4096    # OpenCode 反代上游
sudo -E envsubst '${WITTY_BACKEND_URL} ${WITTY_AGENT_URL}' \
  < ../../packaging/nginx/witty-ub-web.conf.template \
  | sudo tee /etc/witty-ub/web/nginx.conf >/dev/null

# 按需调整 listen / 日志路径后启动
sudo nginx -c /etc/witty-ub/web/nginx.conf
```

无 nginx 的环境可回退 `vite preview`（开发/调试，代理目标经环境变量指向远端）：

```bash
VITE_DEV_API_TARGET=http://<后端IP>:9772 \
  VITE_DEV_AGENT_TARGET=http://127.0.0.1:4096 \
  npm run preview -- --host --port 5173
```

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
curl http://127.0.0.1:8080/                 # Web 200
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
