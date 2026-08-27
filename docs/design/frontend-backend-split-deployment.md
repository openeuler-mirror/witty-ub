# 前后端分离部署改造方案

## 1. 背景与目标

当前三种部署形态（Docker / RPM / 源码）均为"单机 All-in-One"：Nginx、FastAPI、OpenCode、（可选）PostgreSQL 同机部署，前端所有请求默认同源。实际场景中：

- **后端（FastAPI + C++ 工具链 + PG + 数据卷）必须跑在有数据的机器上**（日志/数据库就近）；
- **前端应部署在能访问 Agent（OpenCode）的机器上**（通常是办公网/能出网调 LLM 的机器）；
- 这两者通常是不同的机器，且网络不一定互通到"每台都能直连后端"。

目标：三种部署方式均支持**前端节点与后端节点分离部署**，同时保持现有 All-in-One 行为完全兼容（默认不变，分离为显式 opt-in）。

## 2. 现状分析

### 2.1 组件与端口

| 组件 | 端口 | 绑定地址 | 说明 |
| ------ | ------ | ---------- | ------ |
| Nginx（前端） | 8080（容器映射 32412）/ 5173（源码方式 vite preview） | 0.0.0.0 | 托管 `src/web/dist` 静态资源 + API 反代 |
| FastAPI 后端 | 9772 | `0.0.0.0`（`schemas/config.py` 默认） | CORS `allow_origins=["*"]` |
| OpenCode（Agent） | 4096 | **`127.0.0.1`**（`docker/entrypoint.sh`、`run_opencode.sh` 硬编码） | 前端经 `/agent-api/` 前缀访问 |
| PostgreSQL | 5432 / 15432 | — | 仅后端访问 |

### 2.2 请求链路（现状）

```text
浏览器 → Nginx:8080
            ├── /                    → dist/ 静态资源（SPA fallback）
            ├── /(log_kb|log_file|…) → proxy_pass http://127.0.0.1:9772
            └── /agent-api/          → proxy_pass http://127.0.0.1:4096/
```

### 2.3 前端 API 寻址（src/web）

- [App.vue:822-823](../../src/web/src/App.vue#L822-L823)：
  - `apiBase = VITE_API_BASE_URL ?? ''` —— 默认空串，即**同源相对路径**；
  - `defaultAgentApiBase = VITE_OPENCODE_API_BASE_URL ?? '/agent-api'`。
- 两者均为**构建期** env 固化，改后端地址需重新 `npm run build`。
- 例外：Agent 登录页已有 `agentServerAddress` 输入，Agent API 地址支持运行时覆盖。
- [vite.config.ts](../../src/web/vite.config.ts) 的 dev/preview proxy 目标硬编码 `127.0.0.1:9772 / 4096`。

### 2.4 各部署形态的耦合点

| 部署形态 | 前端托管 | 硬编码的同机假设 |
| ---------- | ---------- | ------------------ |
| Docker（`docker-compose.yml` + `Dockerfile`） | 容器内 Nginx 8080 | [docker/nginx.conf](../../docker/nginx.conf) 反代 `127.0.0.1:9772/4096`；entrypoint 同机拉起全部服务；OpenCode 绑 `127.0.0.1` |
| RPM（`witty-ub` + `witty-ub-manager`） | `witty-ub-web.service`（Nginx 8080） | [packaging/nginx/witty-ub-web.conf](../../packaging/nginx/witty-ub-web.conf) 反代 `127.0.0.1:9772/4096`；manager.sh 只管本机 systemd units |
| 源码/宿主机（`deploy/host/deploy.sh`） | vite preview 5173（dist/） | vite proxy 指向 `127.0.0.1`；deploy.sh 假定前后端同仓同机（systemd user units 成对安装） |

其它耦合：

- Agent（witty-ub-diagnostician）由 OpenCode 承载，直接查询 latency HTTP API，默认假定 `127.0.0.1:9772` 可达 → OpenCode 目前必须与后端同机；
- 日志上传走 API（Nginx `client_max_body_size 20G`），分离部署时上传链路须经前端节点反代或前端直连后端。

## 3. 目标拓扑

```text
┌─ 前端节点（能访问 Agent 的机器） ─────────────┐      ┌─ 后端节点（有数据的机器） ────────────────┐
│  Nginx:8080                                  │      │  FastAPI:9772  (0.0.0.0)                │
│   ├── /            → dist/ 静态资源           │      │  C++ 工具链 / 数据卷 /var/witty-ub       │
│   ├── /(api paths) ──────────────────────────────▶  │  PostgreSQL                              │
│  OpenCode:4096 (127.0.0.1，随前端节点)        │      │                                          │
│   └── /agent-api/ → 本机 4096                │      │  （无出网要求，仅暴露 9772 给前端节点）    │
│   Agent curl ─────────────────────────────────────▶ │                                          │
└──────────────────────────────────────────────┘      └──────────────────────────────────────────┘
```

### 3.1 连接方式决策

**推荐：前端节点 Nginx 反代（保持同源）**。前端代码无需感知后端地址，`apiBase` 仍为空串；跨机移动后端只改前端节点一处 Nginx 上游配置。CORS、混合内容、大文件上传直连等问题全部消解。

备选：前端直连后端（`apiBase = http://<backend>:9772`）。后端 CORS 已全开，技术上可行，但地址固化进构建产物/运行时配置，且浏览器→后端的网络必须全通，仅作为特殊场景（如前端节点无力跑 Nginx）的兜底。

### 3.2 OpenCode 落位：默认跑在前端节点

Agent（OpenCode + witty_ub_diagnostician bundle）对后端机的依赖**只有 9772 只读 HTTP API 一条链路**：提示词限定"只能通过 curl 调用后端 API"，各 Skill 声明"不直接读取本地文件"，且 opencode.json 权限将 bash 锁死为仅 `curl *` 与 experience-skill——Agent 即使与数据同机也拿不到任何本地数据。而 OpenCode 真正需要的出网访问 LLM 提供商与用户 API key 配置（`~/.config/opencode`）都不在后端机。

**分离部署时前端节点本来就必须能直达后端 9772**（否则 Web 页面的 API 反代就是断的），该链路对 Agent 的 curl 同样可用。因此：

| 落位 | 定位 | 说明 |
| ---- | ---- | ---- |
| **A. 跑在前端节点（默认）** | 推荐分离形态 | 后端机无出网要求、只暴露 9772；LLM key 与经验库（experience.db）留在用户侧；`/agent-api/` 反代本机 4096，与现状单机布局同构 |
| B. 留在后端节点（兜底） | 前端机无法安装 Node/OpenCode 等受限环境 | OpenCode 绑 `0.0.0.0`，前端节点 `/agent-api/` 反代 `<backend>:4096`；要求后端机能出网访问 LLM |

落位 A 的必要改动：Agent 提示词中的后端基址由 `http://127.0.0.1:9772` 参数化为 `<backend>:9772`（部署时渲染），`--noproxy` 同步调整（见 §4.6）。

## 4. 改造内容

### 4.1 src/web（前端）

1. **运行时配置注入（核心改动）**：
   - `public/config.json`（默认 `{"apiBase": "", "agentApiBase": "/agent-api"}`）随 dist 发布；
   - `index.html` 在应用启动前 fetch `/config.json` 写入 `window.__WITTY_CONFIG__`，`App.vue` 读取顺序：`VITE_* 构建期值`（回退）→ `config.json`；
   - 效果：同一份 dist 镜像/RPM 在前端节点上由部署脚本改写 `config.json` 即可切换后端，无需重新构建。选择反代方案时 `config.json` 保持默认即可，此机制主要服务备选直连方案与未来扩展。
2. **vite.config.ts proxy 参数化**：dev/preview proxy 目标从 `process.env.VITE_DEV_API_TARGET` / `VITE_DEV_AGENT_TARGET` 读取（默认仍 `127.0.0.1`），支持前端开发者远程连后端调试。
3. Agent 登录页的 `agentServerAddress` 已支持运行时覆盖，无需改动。

### 4.2 Nginx 配置统一模板化

- 合并 [docker/nginx.conf](../../docker/nginx.conf) 与 [packaging/nginx/witty-ub-web.conf](../../packaging/nginx/witty-ub-web.conf) 为一份模板 `packaging/nginx/witty-ub-web.conf.template`，上游以占位符表达：
  - `${WITTY_BACKEND_URL}`（默认 `http://127.0.0.1:9772`）
  - `${WITTY_AGENT_URL}`（默认 `http://127.0.0.1:4096`）
- 部署时由脚本 `envsubst` 渲染生成最终 conf（Docker entrypoint / RPM systemd `ExecStartPre` / host deploy.sh 三处复用同一模板）。
- 补充：上传路径 `proxy_request_buffering off`（大文件流式转发，避免前端节点磁盘缓存 20G 上传）；`/agent-api/` 的 WebSocket 升级头（`Upgrade`/`Connection`，Agent SSE/流式响应需要长连接）。

### 4.3 Docker 部署改造

- `docker/entrypoint.sh` 按 `WITTY_ROLE` 分角色（默认 `all`，行为与现状完全一致）：
  - `all`：现状流程（nginx + FastAPI + OpenCode 同容器）；
  - `backend`：仅 FastAPI（绑 `0.0.0.0`）+ 数据卷，不启动 nginx 与 OpenCode；
  - `frontend`：nginx + OpenCode（绑 `127.0.0.1:4096`，agent bundle 与 experience 卷随本角色挂载），entrypoint 用 envsubst 渲染 API 上游为 `${WITTY_BACKEND_URL}` 并将 `${WITTY_API_BASE}` 注入 Agent 提示词（见 §4.6），`/agent-api/` 反代本机 4096；健康检查改为探测后端 `/health_check`。
- `docker-compose.yml` 新增 `profiles: [split]` 的示例：`witty-ub-backend` + `witty-ub-frontend` 两个服务，前端服务通过环境变量指向后端服务名；默认 profile 保持单容器 All-in-One。
- 现有单镜像即可承载三种角色（dist、后端 runtime、agent bundle 都在镜像内），不拆镜像，降低交付复杂度。

### 4.4 RPM 部署改造

- 子包拆分：`witty-ub`（后端：FastAPI + C++ 工具 + 数据）、`witty-ub-web`（前端：dist + agent bundle + nodejs/OpenCode 依赖 + nginx conf 模板 + `witty-ub-web.service`）、`witty-ub-manager`（不变）。
- `/etc/witty-ub/web/env`（`EnvironmentFile`）承载 `WITTY_BACKEND_URL` / `WITTY_API_BASE`；`witty-ub-web.service` 增加 `ExecStartPre=/bin/sh -c "envsubst < /etc/witty-ub/web/nginx.conf.template > /run/witty-ub-web/nginx.conf"`。
- `witty-ub manager` 新增分离部署子命令：
  - 后端机：`witty-ub manager install --role backend`（跳过 web 子包与 OpenCode 检查）；
  - 前端机：`witty-ub manager install --role frontend --backend http://<backend>:9772`（写入 env 文件、渲染 nginx conf 与 Agent 提示词后拉起 `witty-ub-web` + OpenCode）。
- 两台机器各装所需子包，PG 仍随后端机部署；`OPENCODE_CONFIG_DIR`（LLM key 配置）在前端机用户侧。

### 4.5 源码 / 宿主机脚本部署改造

- `deploy/host/deploy.sh` 增加 `--role all|backend|frontend`（默认 `all`）：
  - `backend`：跳过前端构建、`witty-ub-frontend` unit 与 OpenCode 启动；
  - `frontend`：跳过 PG/venv/C++ 编译；启动 OpenCode（`run_opencode.sh`）+ nginx 静态托管（机器无 nginx 时回退 vite preview，并要求通过 `config.json` 直连后端）；systemd unit 模板按角色成套安装；
- 前端节点部署脚本负责渲染 `config.json`（直连场景）或 nginx conf（反代场景），并向 Agent 提示词注入 `WITTY_API_BASE`。

### 4.6 Agent（OpenCode）配置参数化

Agent bundle（`witty_ub_diagnostician/`）当前在提示词 [agents/witty-ub-diagnostician.md](../../witty_ub_diagnostician/agents/witty-ub-diagnostician.md) 中 3 处硬编码 `http://127.0.0.1:9772`，且明令"禁止通过 curl 访问其他主机、其他端口"，另有 `--noproxy 127.0.0.1`——这是 OpenCode 迁往前端节点的主要障碍。改造：

- 提示词模板化：仓库内保留 `witty-ub-diagnostician.md.template`，基址与 `--noproxy` 值以 `${WITTY_API_BASE}`（默认 `http://127.0.0.1:9772`）/ `${WITTY_NO_PROXY}` 占位；部署脚本 envsubst 渲染到运行时目录（opencode.json 的 `{file:...}` prompt 路径不变）。渲染后必须保留"只允许访问该基址"的约束表述，防止 Agent 越权 curl。
- `docker/entrypoint.sh`、`run_opencode.sh` 的 `--hostname` 参数化为 `${OPENCODE_HOST:-127.0.0.1}`（仅兜底落位 B 需要 `0.0.0.0`）。
- experience 卷（experience.db）与 `OPENCODE_CONFIG_DIR`（LLM key）归属前端节点的 agent 运行时，不随后端角色部署。
- 顺带修复该 commit 引入的问题：`deploy/pg.conf` 中 `OPENCODE_CONFIG_DIR` 硬编码个人路径 `/home/tsn/opencode`（应回退 `${HOME}/.config/opencode` 默认值）；目录名拼写 `witty_ub_diagnostician` → `witty_ub_diagnostician`（已扩散至 Dockerfile/entrypoint/run_opencode.sh/deploy.sh/opencode.json 多处路径，宜尽早统一更名）。

### 4.7 安全

- 跨机明文 HTTP：默认形态下后端机仅需对前端节点开放 9772（4096 留在前端节点本机回环，不出网）；兜底落位 B 才需暴露 4096。后续可迭代 TLS 终止在前端节点 Nginx + 后端 mTLS/静态 Token（本方案先不引入，避免过度设计）。
- 后端 CORS 由 `allow_origins=["*"]` 收敛为可配置项（`diagnosis_config.toml [service] allow_origins`），分离部署默认配前端节点 origin。
- OpenCode 4096 暴露到网络前确认其鉴权（前端 Agent 登录已有账号体系），建议同防火墙收敛。

## 5. 实施顺序

| 阶段 | 内容 | 依赖 |
| ------ | ------ | ------ |
| P1 | src/web 运行时 `config.json` + vite proxy 参数化 | 无 |
| P2 | Nginx 模板统一 + Agent 提示词模板化（`WITTY_API_BASE`/`WITTY_NO_PROXY`）+ envsubst 渲染 | 无 |
| P3 | Docker：entrypoint 角色化（frontend 角色含 OpenCode + experience 卷迁移）+ compose `split` profile | P2 |
| P4 | host deploy.sh / run_opencode.sh 角色化与 `OPENCODE_HOST` | P1、P2 |
| P5 | RPM 子包拆分（web 子包含 agent bundle + nodejs/OpenCode）+ manager 分离子命令 | P2 |
| P6 | 文档：`docs/deployment/` 增补分离部署章节，端口矩阵更新 | P3-P5 |

每阶段均保持 All-in-One 默认行为回归通过（现有 `deploy/host/test_full_deploy.sh`、Jenkins E2E）。

## 6. 验证清单

- [ ] All-in-One：三种部署方式行为与改造前一致（回归）；
- [ ] 分离·Docker：`docker compose --profile split up`，前端节点访问页面、上传大日志（>1GB）、Agent 对话正常；
- [ ] 分离·RPM：两台 openEuler 分别装 `witty-ub` / `witty-ub-web`，`manager install --role …` 后功能验证同上；
- [ ] 分离·源码：`deploy.sh --role backend/frontend` 两机部署验证；
- [ ] OpenCode 跑前端节点（默认形态）：Agent 经 `WITTY_API_BASE` 直连远程 9772 完成一次完整诊断，且提示词约束仍只允许访问该基址；后端机全程无出网；
- [ ] OpenCode 留后端节点（兜底形态）：绑 `0.0.0.0` 被前端反代，Agent 诊断链路可用；
- [ ] 前端节点重启后配置（env 文件/config.json）持久生效；
- [ ] 后端节点不可达时前端报错可读（Nginx 502 页面/健康检查状态）。
