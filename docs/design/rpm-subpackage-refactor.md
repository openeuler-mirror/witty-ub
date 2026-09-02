# RPM 子包化重构方案

## 1. 现状检查结论

当前 RPM 形态为**一个大负载包 + 一个小工具包**：

| 包 | 内容 |
| ---- | ---- |
| `witty-ub` 主包 | 全部负载：FastAPI 代码、C++ 工具链、数据文件、web dist、Agent bundle、`witty-ub-web.service` + `witty-ub-latency.service`、nginx 模板 |
| `witty-ub-manager` 子包 | `/usr/bin/witty-ub` 派发器、`/usr/libexec/witty-ub-manager/` 脚本、`/etc/witty-ub/deploy.conf` |

spec 文件在仓外（openEuler 社区打包仓），仓内只有 `deploy/rpm/libexec/` 与 `packaging/`。

分离部署的问题：

1. **两台机器装同一个大包**：前端机被迫装上 PG/后端代码/数据卷，后端机被迫装上 web dist 与 Agent bundle；
2. **角色靠手动裁剪**：装完后手动 `systemctl disable --now` 不需要的服务；
3. **配置链路手动**：前端机手动 `envsubst` 渲染 nginx conf、手动 `WITTY_API_BASE=... bash deploy_opencode.sh` 启动 OpenCode；
4. **manager 不感知角色**：`_lib.sh` 中 `WITTY_SERVICES=(witty-ub-web witty-ub-latency)` 硬编码，`install` 子命令假设单机 All-in-One（初始化 PG + 启全部服务）。

## 2. 目标

1. `dnf install witty-ub` 一键安装 `witty-ub-backend` + `witty-ub-web` + `witty-ub-manager`（All-in-One 不回退）；
2. `dnf install witty-ub-backend`：仅后端负载，自动依赖 `witty-ub-manager`；
3. `dnf install witty-ub-web`：仅前端负载，自动依赖 `witty-ub-manager`；
4. **配置即生效**：前端机 `witty-ub manager` 配置后端地址后自动渲染 nginx，Agent 通过 OpenCode 进程环境变量取得配置；后端机同理（PG 初始化 + 凭据同步 + 启动 latency）。

## 3. 子包设计

### 3.1 文件归属矩阵

路径沿用现有 RPM 布局（`/var/witty-ub/...`），不迁移到 `/usr/share`：本轮只做归属拆分，避免数据/配置路径迁移牵连 C++ 工具、FastAPI 与 Agent 的路径解析。

| 路径 | witty-ub-backend | witty-ub-web | witty-ub-manager | witty-ub (meta) |
| ---- | :--: | :--: | :--: | :--: |
| `/var/witty-ub/latency/`（FastAPI 代码 + deploy 脚本） | ✓ | | | |
| C++ 工具（witty-ub-log / topo / diag-tool / brpc-diag） | ✓ | | | |
| `/var/witty-ub/data/`（故障模式数据） | ✓ | | | |
| `/var/witty-ub/config/diagnosis_config.toml` | ✓ | | | |
| `witty-ub-latency.service` | ✓ | | | |
| web dist（`/var/witty-ub/web/`） | | ✓ | | |
| Agent bundle（`/var/witty-ub/witty_ub_diagnostician/.opencode/`） | | ✓ | | |
| `/var/witty-ub/deploy/deploy_opencode.sh` | | ✓ | | |
| `/usr/share/witty-ub/nginx/witty-ub-web.conf.template` + `witty-ub-web.service` | | ✓ | | |
| `/etc/witty-ub/web/env`（前端连接配置，安装默认值） | | ✓ | | |
| `/usr/bin/witty-ub` + `/usr/libexec/witty-ub-manager/` | | | ✓ | |
| `/etc/witty-ub/deploy.conf`（PG 凭据） | | | ✓ | |
| 无负载文件，仅 Requires + license | | | | ✓ |

`/var/witty-ub`、`/var/witty-ub/latency{,/deploy}`、`/var/witty-ub/deploy` 等父目录由相关子包共享属主（RPM 允许多包共有一个目录），保证单角色机器上目录齐全。

### 3.2 依赖关系（spec Requires）

| 包 | Requires |
| ---- | ---- |
| `witty-ub`（meta） | `witty-ub-backend`、`witty-ub-web`、`witty-ub-manager` |
| `witty-ub-backend` | `witty-ub-manager`、C++ 运行库（log4cplus/sqlite/brotli/zlib/jsoncpp/tinyxml2/openssl-libs/re2）、`python3` |
| `witty-ub-web` | `witty-ub-manager`、`nginx`、`nodejs >= 18`、`curl` |
| `witty-ub-manager` | `systemd`、`curl` |

调整：

- postgresql 依赖不进任何子包的 Requires（openEuler 各版本 PG 包名不稳定，`postgresql-server` vs `postgresql15-server`）；PG 由 `manager install` 在后端机上按需补装（deploy_pg.sh 已实现），文档明确"PG 无需预装"。
- `witty-ub-backend`/`witty-ub-web` 增加 `Conflicts: witty-ub < %{version}-%{release}`，承接旧单包升级时的文件归属迁移。
- `opencode-ai` 是 npm 全局包而非系统 RPM，由前端机执行 `npm i -g opencode-ai`（前端机可出网），不进 Requires。

### 3.3 spec 留在打包仓（src-openeuler/witty-ub）

spec 不进本仓，仍在 src-openeuler 社区打包仓（openEuler-24.03-LTS-SP3 分支）维护。本轮改造向打包仓交付两部分：

- 新增 Patch0017：携带本仓 `deploy/rpm/*` 角色化脚本、`packaging/nginx/witty-ub-web.conf.template`、`deploy/rpm/web.env`、`deploy_opencode.sh` 参数化，以及打包仓树内 `config/agents` 提示词参数化与 `config/opencode.json` curl 权限放宽（Agent bundle 含 2.6MB 二进制，不随 patch 携带，打包仓沿用 `config/agents` 提示词布局，`deploy_opencode.sh`/`_lib.sh` 双布局兼容）；
- spec 改写为四包结构（子包拆分、依赖矩阵、%post 归属），Release 递增；
- 验证路径：OrbStack openEuler VM 内 `rpmbuild` 构建 → 本地 repo → `dnf install` 分离部署实测。

**服务维持手动启动**：spec 的 %post 只做安装期准备（backend 建 venv、web 渲染默认 nginx.conf、daemon-reload），不 `systemctl enable --now` 任何服务；服务一律由用户显式执行 `witty-ub manager install` 或 `systemctl start` 启动。

## 4. manager 角色化改造（deploy/rpm/libexec/）

### 4.1 角色探测

不依赖显式 `--role`，默认按已安装子包自动探测：

```bash
detect_role() {
    local backend=0 web=0
    rpm -q witty-ub-backend >/dev/null 2>&1 && backend=1
    rpm -q witty-ub-web      >/dev/null 2>&1 && web=1
    # backend+web → all; 仅 backend → backend; 仅 web → frontend
    # 均未安装但旧单包 witty-ub 在 → all（旧单包负载全量）
}
```

`WITTY_ROLE_FORCE` 环境变量可覆盖探测结果（测试/特殊场景）。`WITTY_SERVICES` 由角色动态生成：`backend → (witty-ub-latency)`、`frontend → (witty-ub-web)`、`all → 全部`。start/stop/status/logs/uninstall 自动只操作本机角色的服务，文档中"手动 disable"步骤整体消失。

### 4.2 install 子命令按角色分流

```bash
witty-ub manager install [--backend http://<ip>:9772]
```

| 角色 | 动作 |
| ---- | ---- |
| backend | 依赖检查 → PG 初始化（deploy_pg.sh）→ 凭据同步 → enable --now witty-ub-latency → 健康检查 |
| frontend | 依赖检查 → 写 `/etc/witty-ub/web/env` → 渲染 nginx conf（`--backend` 指定，默认读 env 现值）→ Agent 启动时导出 env → enable --now witty-ub-web → 端到端探测 |
| all | 依次执行 backend + frontend（`--backend` 默认 127.0.0.1，行为与现状一致） |

### 4.3 config 子命令（配置即生效）

```bash
witty-ub manager config --backend http://192.168.1.10:9772   # 前端机：切换后端地址
witty-ub manager config --show
```

流程：写入 `/etc/witty-ub/web/env`（`WITTY_BACKEND_URL` / `WITTY_API_BASE` / `WITTY_NO_PROXY`）→ 重新渲染 `/etc/witty-ub/web/nginx.conf`（sed 替换模板占位符，不依赖 gettext/envsubst）→ `systemctl restart witty-ub-web`。Agent 提示词保持原文，OpenCode 启动时导出 env。

### 4.4 OpenCode 维持手动启动

**不新增 `witty-ub-agent.service`**：OpenCode 仍由用户在前端机手动执行 `deploy_opencode.sh` 启动（沿用源码/Docker 部署已验证的流程）。LLM key 位于 `~/.config/opencode`，因用户而异，纳入 systemd 反而引入运行用户与密钥路径问题。`manager config` 切换后端地址后提示用户重启 OpenCode，新进程会导出更新后的环境变量：

```bash
set -a; source /etc/witty-ub/web/env; set +a
bash /var/witty-ub/deploy/deploy_opencode.sh
```

### 4.5 install_deps.sh / 文案同步

- 依赖检查按角色裁剪（frontend 不查 psql/PG，backend 不查 nginx/node）；
- `witty-ub` 派发器与 manager 帮助文案更新为新子包模型。

## 5. 兼容与迁移

| 场景 | 策略 |
| ---- | ---- |
| 旧 `witty-ub` 单包升级 | 新 meta 包同名 `witty-ub` 承接，`dnf update` 自动拉入三个子包；旧主包文件由对应子包接管（子包 Provides/Conflicts 处理文件归属迁移） |
| 旧 `witty-ub-manager` | 包名不变，脚本原地升级 |
| 单机 All-in-One 用户 | `dnf install witty-ub` + `manager install` 流程与现状完全一致，零感知 |

## 6. 实施阶段

| 阶段 | 内容 | 产出 | 依赖 |
| ---- | ---- | ---- | ---- |
| R1 | manager 角色化：角色探测、install/config 子命令、动态服务集 | `deploy/rpm/libexec/` 改造，`test_deploy_integration.py` 补测试 | 无 |
| R2 | 打包仓 spec 改写为四包结构 + Patch0017 携带角色化脚本（venv 创建移入 backend %post，不自动启服务） | 打包仓可构建的四包 spec + patch | R1 |
| R3 | VM 验证：witty-ub-be 上 rpmbuild → 本地 dnf repo → 三种安装路径（meta/backend+manager/web+manager）+ 分离部署端到端 + All-in-One 回归 | 验证记录 | R1、R2 |
| R4 | 文档：07-rpm.md 按新包模型重写（删除手动 disable/手动渲染步骤）、01-overview 端口表同步 | 文档 | R3 |

## 7. 验证清单

- [ ] `dnf install witty-ub` → 三个子包齐装，安装后无服务自动启动，`manager install` 后 All-in-One 行为与现状回归一致；
- [ ] 后端机 `dnf install witty-ub-backend` → 自动带入 manager；`manager install` 完成 PG 初始化 + latency 启动 + 健康检查 200；
- [ ] 前端机 `dnf install witty-ub-web` → 自动带入 manager；`manager install --backend http://<be>:9772` 后页面 200 / API 反代 200；手动启动 OpenCode 后 agent-api 200；
- [ ] 前端机 `manager config --backend <新地址>` → env/nginx 更新、witty-ub-web 自动重启，OpenCode 重启后新地址生效；
- [ ] 前端机重启后配置持久（env 文件 + 渲染产物 + enabled units）；
- [ ] 后端机不可达时前端 502 报错可读；
- [ ] 旧单包 `dnf update` 升级路径文件无冲突；
- [ ] manager start/stop/status/logs 在两种角色机器上均只操作本机服务。
