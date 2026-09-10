# 容器脚本部署

## 概述

使用 `deploy/docker/manage.sh` 完成容器化部署，自动处理镜像拉取、容器创建、服务启动、健康检查全流程。支持两种形态：

- **前后端分离（推荐）**：后端容器（FastAPI + 数据卷，宿主机 9772）+ 前端容器（Nginx + OpenCode，宿主机 32413），可同机也可分机 → 见下方[分离部署](#分离部署前后端分角色)。
- **单机 All-in-One**：前端与后端在同一容器内（菜单 `[1]`/`[3]`），适合快速验证或前后端必须同机的场景。

> 部署失败即中止：PG 或 witty-ub 未健康时脚本会打印容器日志并以非 0 退出；`install-all` 在 PG 阶段失败时不会再继续部署 witty-ub。
>
> **输出语言**：容器部署脚本（`deploy/docker/*`、`deploy/deploy_pg.sh`）的日志、菜单、提示等用户可见文本统一为**英文**（与 `build.sh`、`docker/entrypoint.sh` 等既有脚本一致）；本文档等中文文档仅作说明。

---

## 前置条件

- Docker 20.10+ 已安装并运行
- 至少 4GB 内存、10GB 可用磁盘空间
- 有权限拉取镜像，或本地已有镜像
- 当前用户在 `docker` 组内（或使用 root）；`sudo usermod -aG docker $USER` 后需重新登录
- 数据库相关操作需要 root 或可免密 `sudo`：写入 `/etc/witty-ub`、设置密钥文件权限（`deploy_pg.sh` 与 `deploy_witty.sh` 通过 `sudo -n` 回退）。仅部署 frontend 角色不需要该权限。

> openEuler 24.03 官方源的 `docker-engine` 为 18.09（cgroup v2 上无法启动）、`docker-compose` 为 1.22（不支持 `--profile`），请按 [容器运行问题排查](../troubleshooting/02-container-runtime.md#2-docker-版本兼容性) 安装 Docker CE 20.10+。

```bash
# 验证 Docker 环境
docker info
```

---

## 交互式部署

```bash
bash deploy/docker/manage.sh
# 选择 [1] 一键安装
```

无 TTY 环境（CI、`ssh host 'cmd'`、脚本调用）下同样可用：所有提示自动取默认值，可用环境变量或 `deploy.conf` 覆盖（详见[环境变量覆盖](#环境变量覆盖)）。

选择 `[1] 一键安装` 即可自动完成：

```text
  [PG]    拉取镜像 → 创建网络 → 创建数据卷 → 启动容器 → 等待健康
  [witty] 拉取镜像 → 验证 → 创建网络/数据卷 → 启动 → 等待健康 → 验证
```

---

## 离线部署

```bash
# 在有网络的机器导出镜像
docker pull hub-harbor.oepkgs.net/neocopilot/witty-ub:latest
docker pull quay.io/sclorg/postgresql-15-c9s:latest

docker save -o witty-ub.tar hub-harbor.oepkgs.net/neocopilot/witty-ub:latest
docker save -o pg15.tar quay.io/sclorg/postgresql-15-c9s:latest

# 传输并导入
scp witty-ub.tar pg15.tar root@<目标机器>:/tmp/
docker load -i witty-ub.tar && docker load -i pg15.tar

# 执行部署
bash deploy/docker/manage.sh
```

---

## 配置说明

### 配置文件 deploy.conf

所有脚本共用 `deploy/deploy.conf`（旧名 `pg.conf` 仍兼容），修改后全局生效：

```bash
vi deploy/deploy.conf
```

常用配置：

```conf
# witty-ub
WITTY_HOST_PORT="32412"              # 宿主机端口
WITTY_EXTRA_MOUNTS="/home:/home:ro"   # 额外挂载

# PostgreSQL
PG_PORT="15432"                       # 宿主机端口
PG_HOST_IN_CONTAINER=""               # 容器内访问，留空自动检测
PG_PORT_IN_CONTAINER=""
PG_USER="witty-ub"
PG_PASSWORD="<CHANGE_ME>"             # 仅占位符，实际口令在 /etc/witty-ub/pg.passwd
PG_DATABASE="witty-ub"
```

> **PG 密码**：Docker 部署时口令存放在 `/etc/witty-ub/pg.passwd`（权限 0440，属主 root；容器内 postgres 用户经 gid 0 读取），由 `deploy_pg.sh --docker` 生成。`deploy_witty.sh` 将该文件只读挂载到 `/run/secrets/pg_password`，容器入口启动后端前才读取并注入进程环境；密码不会写入 `deploy.conf`、运行时 TOML 或 `docker inspect` 可见的容器环境配置。
>
> **宿主机 PG（RPM/源码）场景**：`deploy_pg.sh --rpm/--apt` 生成的密钥在 `deploy/pg.passwd`；`deploy_witty.sh` 按 `/etc/witty-ub/pg.passwd` → `deploy/pg.passwd` 的顺序自动查找，无需手工搬运。宿主机 PG 需允许 Docker 网关访问（`listen_addresses='*'` + `pg_hba` 放通），`deploy_pg.sh --rpm` 会自动完成并**重启**服务。
>
> **脚本与 compose 互斥**：`deploy/docker/manage.sh`（脚本）与仓库 `docker-compose.yml` 使用相同的容器名/卷名/网络名，二者**不要混用**（同名容器会冲突，卷名不同会数据分裂）。compose 用法见 [手动容器部署](08-container.md)。

### 环境变量覆盖

通过环境变量临时覆盖 `deploy.conf` 中的配置：

```bash
WITTY_HOST_PORT=8080 bash deploy/docker/manage.sh
WITTY_IMAGE=my-custom:v1 bash deploy/docker/manage.sh
PG_HOST_IN_CONTAINER=172.18.0.1 bash deploy/docker/manage.sh
```

> **说明**：环境变量优先级高于 `deploy.conf`，作用于脚本安装路径（菜单 `[1]`/`[3]`，即 `deploy_witty.sh` / `deploy_pg.sh`）；Docker 容器内的运行时配置不受影响。若需修改 opencode 配置文件，请在宿主机上操作：`manage.sh` 会将宿主机的 opencode 配置目录（默认 `~/.config/opencode/`，可通过 `OPENCODE_CONFIG_DIR` 覆盖）映射到容器中，在容器内修改不会持久化。详见 [配置参考手册 · OpenCode 配置](../usage/03-configuration-reference.md#opencode-配置)。
>
> `deploy_witty.sh` 会直接加载 `deploy.conf`，因此菜单 `[1]` 一键安装、直接 `bash deploy/docker/deploy_witty.sh --role …` 与菜单 `[3]`/`[14]`/`[15]` 的配置来源一致；优先级为：环境变量 > `deploy.conf` > 脚本内置默认值。

---

## 分离部署（前后端分角色）

使用按角色构建的镜像（`witty-ub:backend` / `witty-ub:frontend`，多架构发布见 [镜像分发](../package/03-distribution.md)），前后端可同机也可分机：

```bash
bash deploy/docker/manage.sh
# 选择 [2] 仅安装 PostgreSQL（或复用已有 PG）
# 选择 [14] 仅安装 witty-ub 后端：PG + FastAPI，宿主机 9772
# 选择 [15] 仅安装 witty-ub 前端：Nginx + OpenCode，宿主机 32413，反代 witty-ub-backend:9772

# 命令行等价
bash deploy/docker/manage.sh install-backend
WITTY_BACKEND_URL=http://<后端机器IP>:9772 bash deploy/docker/manage.sh install-frontend
```

提示行会回显当前值（来自环境变量或 `deploy.conf`），直接回车即保留该值：

```text
  [2] 后端地址            [http://192.168.1.10:9772]:
```

与单机部署的差异：

- 后端：容器 `<名称>-backend`，暴露 9772 供前端反代，挂载数据卷并连接 PG，需要 `/etc/witty-ub/pg.passwd`。
- 前端：容器 `<名称>-frontend`，暴露 32413，挂载 opencode 配置与经验库数据卷，不连数据库、无需 PG 密钥。
- 跨机部署时，前端机器通过 `WITTY_BACKEND_URL=http://<后端机器IP>:9772`（环境变量或 `deploy.conf`）指向后端，后端机器防火墙需对该前端机器开放 9772。
- 健康检查角色感知：frontend 容器经 Nginx 反代探测远端后端 `/health_check`，[10] 查看状态会列出分离角色容器。

手动 `docker run` / `docker compose --profile split` 方式 → [手动容器部署 · 分离部署](08-container.md)。

---

## 验证部署

```bash
bash deploy/docker/manage.sh
# 选择 [10] 查看状态

curl http://localhost:32412/health_check
```

浏览器访问：`http://<IP>:32412`

非交互（CI / `ssh host 'cmd'`）下可一次性完成部署与验证：

```bash
bash deploy/docker/manage.sh install-all < /dev/null   # 退出码非 0 即部署失败
bash deploy/docker/manage.sh status
curl -sf http://localhost:32412/health_check           # {"status":"ok"}
```

> 成功判据：`manage.sh`/`deploy_witty.sh` 只有在 PG 与 witty-ub 都 `healthy`、且 `/health_check` 返回 `{"status":"ok"}` 时才以 0 退出；否则会打印容器日志并以非 0 退出。

---

## 卸载与清理

卸载属于破坏性操作，交互式执行时会二次确认（默认 No）：

```bash
bash deploy/docker/manage.sh
# 选择 [4] 一键卸载 → 选择范围（1 容器+卷 / 2 容器+卷+镜像）→ 确认 y
```

**非交互（CI / `ssh host 'cmd'`）必须显式加 `--yes`**，否则提示取默认值 No、脚本会
"什么都没删"但退出码仍为 0：

```bash
bash deploy/docker/manage.sh uninstall --yes            # 容器 + 数据卷
bash deploy/docker/manage.sh uninstall-witty --yes      # 仅 witty-ub 容器（含分离角色）
bash deploy/docker/manage.sh uninstall-pg --yes         # 仅 PostgreSQL 容器
```

> 与 compose 混用的机器请用 `docker compose --profile allinone down -v` /
> `docker compose --profile split down -v` 清理，两者不要交叉操作。

---

## 已知问题

- **镜像拉取失败**：检查网络、镜像仓库地址、本地 tag 是否已设置
- **容器启动后健康检查失败**：`docker logs witty-ub`（分离部署为 `witty-ub-backend` / `witty-ub-frontend`）查看日志
- **PG 连接被拒**：确认 PG 容器状态 `docker ps | grep postgres`
- **分离前端 unhealthy**：前端经反代探测后端 `/health_check`，确认后端容器已就绪且 `WITTY_BACKEND_URL` 可达
- **端口冲突**：`ss -tlnp | grep <端口>` 检查占用

---

## 后续步骤

- 脚本详细说明 → [../../deploy/docker/README.md](../../deploy/docker/README.md)
- 手动数据库部署 → [05-database.md](05-database.md)
- 手动源码部署 → [06-source.md](06-source.md)
- 手动 RPM 部署 → [07-rpm.md](07-rpm.md)
- 手动容器部署 → [08-container.md](08-container.md)
