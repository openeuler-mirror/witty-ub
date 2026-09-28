# 容器运行问题排查

本文档介绍 witty-ub 容器运行时常见问题的排查方法，包括 seccomp/clone3 问题、Docker 版本兼容性、Docker 网络不被信任导致的容器间不通、挂载目录改动后找不到路径、日志管理、容器内调试和生产环境建议。

> **容器名速查**：单机 All-in-One = `witty-ub`（Web 32412）；分离部署 = `witty-ub-backend`（API 9772，无 Web）+ `witty-ub-frontend`（Web 32413，反代后端）；数据库 = `postgres`（宿主机 15432）。
> **PG 密钥**：PG 容器要求 `/etc/witty-ub/pg.passwd` 为 `0440 root:root`（容器内 postgres 用户 uid26/gid0 读），否则会崩溃循环，详见 [常见问题 · PG 容器崩溃循环](01-common-issues.md#9-pg-容器崩溃循环--后端连不上数据库)。

---

## 1. seccomp/clone3 问题

### 问题描述

**症状**: 容器启动后运行异常，出现以下情况之一:

- Latency Plugin 报 `RuntimeError: can't start new thread`
- 容器内进程创建失败或线程池无法扩展
- OpenCode 服务无法正常启动
- 应用日志中出现 `clone3` 系统调用失败相关错误

**根本原因**: 宿主机 Docker、runc 或 libseccomp 版本较旧（通常 Docker < 20.10），默认 seccomp 政策不支持 glibc 新版本中用于创建线程/进程的 `clone3` 系统调用。

### 验证步骤

#### 步骤 1: 检查宿主机 Docker 版本

```bash
docker --version
```

如果版本低于 `20.10`，则可能存在此问题。

#### 步骤 2: 检查容器内线程创建能力

```bash
docker exec witty-ub \
  /var/witty-ub/latency/.venv/bin/python \
  -c 'import threading; t=threading.Thread(target=lambda: print("thread ok")); t.start(); t.join()'
```

如果输出 `RuntimeError: can't start new thread`，说明线程创建失败。

#### 步骤 3: 验证 seccomp 限制

启动临时容器，关闭 seccomp 限制后再次测试:

```bash
IMAGE=$(docker inspect witty-ub --format '{{.Config.Image}}')

docker run --rm \
  --security-opt seccomp=unconfined \
  --entrypoint /var/witty-ub/latency/.venv/bin/python \
  "$IMAGE" \
  -c 'import threading; t=threading.Thread(target=lambda: print("thread ok")); t.start(); t.join()'
```

如果临时容器输出 `thread ok`，可以确认是 seccomp 兼容问题。

#### 步骤 4: 检查 libseccomp 版本

```bash
ldconfig -p | grep libseccomp
rpm -qa | grep libseccomp  # CentOS/RHEL/openEuler
dpkg -l | grep libseccomp  # Debian/Ubuntu
```

如果 libseccomp 版本低于 `2.5.0`，可能无法正确处理 `clone3` 系统调用。

### 修复方案

#### 方案一: 添加 `--security-opt seccomp=unconfined` 参数（临时兼容）

这是最快的临时解决方案，适用于无法立即升级 Docker 的环境。

**使用 docker run 命令**:

```bash
docker run -d \
  --name witty-ub \
  --restart unless-stopped \
  -p 32412:8080 \
  -v witty-ub-data:/var/witty-ub/data \
  -v witty-ub-logs:/var/log/witty-ub \
  -v /etc/witty-ub/pg.passwd:/run/secrets/pg_password:ro \
  --security-opt seccomp=unconfined \
  witty-ub:latest
```

> 该容器是**增补的调试容器**：`witty-ub` 名称若已被现有部署占用，请改用别的 `--name` 与端口。缺少 `/run/secrets/pg_password` 挂载时入口会直接退出（数据库口令为必需项）。

**使用 docker compose**:

修改 `docker-compose.yml`:

```yaml
services:
  witty-ub:
    image: witty-ub:latest
    container_name: witty-ub
    restart: unless-stopped
    ports:
      - "32412:8080"
    volumes:
      - witty-ub-data:/var/witty-ub/data
      - witty-ub-logs:/var/log/witty-ub
    secrets:
      - pg_password
    security_opt:
      - seccomp=unconfined

secrets:
  pg_password:
    file: /etc/witty-ub/pg.passwd
```

然后重新创建容器:

```bash
docker compose --profile allinone down
docker compose --profile allinone up -d
docker logs -f witty-ub
```

#### 方案二: 升级 Docker Engine 和 libseccomp（推荐）

长期解决方案是升级宿主机的 Docker Engine、runc 和 libseccomp 到最新版本。

**在 openEuler/CentOS/RHEL 上**:

```bash
# 升级 libseccomp
yum update -y libseccomp

# 升级 Docker（参考官方文档）
# https://docs.docker.com/engine/install/
```

#### 方案三: 使用自定义 seccomp 配置

如果不想完全关闭 seccomp，可以创建自定义配置文件，允许 `clone3` 系统调用:

```json
{
  "defaultAction": "SCMP_ACT_ALLOW",
  "syscalls": [
    {
      "name": "clone3",
      "action": "SCMP_ACT_ALLOW"
    }
  ]
}
```

保存为 `seccomp.json`，然后启动容器时使用:

```bash
docker run --security-opt seccomp=./seccomp.json ...
```

### 验证修复结果

修复后，重新进入容器验证线程创建:

```bash
docker exec witty-ub \
  /var/witty-ub/latency/.venv/bin/python \
  -c 'import threading; t=threading.Thread(target=lambda: print("thread ok")); t.start(); t.join()'
```

如果输出 `thread ok`，说明修复成功。

检查 Latency Plugin 服务状态:

```bash
docker exec witty-ub curl http://localhost:9772/health_check
```

预期输出: `{"status": "healthy"}`

> **安全提示**: `seccomp=unconfined` 会关闭容器的默认 seccomp 系统调用过滤，降低了容器的安全隔离性。仅建议用作问题验证或临时兼容方案。长期建议升级宿主机的 Docker Engine、runc 和 libseccomp，并在升级后移除此参数。

---

## 2. Docker 版本兼容性

### 版本要求

- **最低版本**: Docker 20.10+
- **推荐版本**: Docker 24.0+

### 检查版本

```bash
docker --version
docker compose version
```

### 低版本 Docker 注意事项

如果 Docker 版本低于 20.10:

1. 可能遇到 seccomp/clone3 问题（见上文）
2. 不支持 `docker compose` 命令，需使用 `docker-compose`（带连字符）
3. 多架构构建功能受限

### 升级 Docker

**在 openEuler 24.03 上**（该发行版官方源只有 `docker-engine 18.09` / `docker-compose 1.22`，
即上文点名"不可用"的版本；也不提供 `yum-utils`、`yum-config-manager`，因此不能照抄
CentOS/RHEL 的通用步骤）:

```bash
# 卸载旧版本
sudo yum remove docker docker-client docker-client-latest docker-common docker-latest docker-latest-logrotate docker-logrotate docker-engine

# 配置 Docker CE 仓库：openEuler 的 $releasever 是 24.03，不能直接用 centos 的 repo 文件，
# 需显式固定为 centos/9（依赖 container-selinux 由 openEuler 源提供）
sudo tee /etc/yum.repos.d/docker-ce.repo >/dev/null <<'EOF'
[docker-ce-stable]
name=Docker CE Stable
baseurl=https://download.docker.com/linux/centos/9/$basearch/stable
enabled=1
gpgcheck=1
gpgkey=https://download.docker.com/linux/centos/gpg
EOF

# 安装 Docker（实测：Docker CE 29.x + Compose v2 插件）
sudo dnf install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin docker-buildx-plugin

# 启动 Docker
sudo systemctl enable --now docker

# 授权当前用户（否则 docker info 报 permission denied，部署脚本会提示加入 docker 组）
sudo usermod -aG docker "$USER" && newgrp docker

# 校验
docker version
docker compose version
```

> 完全离线环境：在用网机器执行
> `dnf download --resolve docker-ce docker-ce-cli containerd.io docker-compose-plugin docker-buildx-plugin`，
> 把 RPM 与 `container-selinux` 一起带到目标机后 `sudo dnf install ./*.rpm`。
>
> 若目标机不能改仓库，也可用 Docker 官方静态包
> （`https://download.docker.com/linux/static/stable/<arch>/docker-<ver>.tgz`）解压到
> `/usr/bin` 并自行提供 `docker.service`（无 `docker compose` 插件，需改用 `docker run` 系列命令）。

---

## 3. Docker 网络不被信任导致容器间无法通信

### 问题描述

**症状**: PG 容器与 witty-ub 容器都在同一个 Docker 网络 `witty-ub-network` 内，容器本身都能正常启动，但二者互相不可达:

- 部署脚本末尾的自检报 `Self-check: app -> PostgreSQL failed (HTTP 503): the app is up but cannot reach postgres:5432`
- witty-ub 启动后健康检查一直 `unhealthy`，或部署脚本报 `Latency Plugin failed to start`
- `/var/log/witty-ub/latency_server.log` / `docker logs witty-ub` 报数据库连接被拒或超时（`connection refused` / `timeout expired` / `could not connect to server`）
- 在 witty-ub 容器内 `getent hosts postgres` 能正常解析出 IP（容器名 DNS 没问题），但 TCP 5432 连不上
- 在 PG 容器内自检正常（`docker exec postgres psql -U witty-ub -d witty-ub -c 'select 1'` 通过），说明 PG 本身没问题

**根本原因**: 部分安全加固过的服务器（常见于开启 firewalld 且默认 zone 目标为 `DROP`/`REJECT` 的 openEuler/CentOS/RHEL 机器，或安装了主机安全策略的机器）默认把 Docker 创建的网桥（`docker0`、`br-<hash>`）视为**不可信区域**，没有纳入信任域。此时同一 Docker 网络内两个容器之间的流量会在宿主机的入站/转发环节被拦截，表现出来就像"网络不通"。

> 与 [常见问题 §9 PG 容器崩溃循环](01-common-issues.md#9-pg-容器崩溃循环--后端连不上数据库) 的区别：那个是密钥文件权限导致 **PG 自己起不来**；这里是 **PG 正常运行但网络流量被策略阻断**，`docker ps` 里 PG 是 `healthy` 的。

### 验证步骤

#### 步骤 1: 先看部署自检结论

部署脚本起完容器后会**在容器内**探测 `/health_check`（不是探宿主机端口，专门为避免"宿主机端口通了、容器内到 PG 的链路断了"的假成功），直接给出结论:

```
[OK]    Self-check: app -> PostgreSQL OK (HTTP 200, postgres:5432)
[ERROR] Self-check: app -> PostgreSQL failed (HTTP 503): the app is up but cannot reach postgres:5432
```

判定对照:

| 自检输出 | 含义 | 是否本节场景 |
| --- | --- | --- |
| `app -> PostgreSQL OK (HTTP 200, …)` | 应用与 PG 全通 | 否，不必往下查 |
| `app -> PostgreSQL failed (HTTP 503)…` | **应用在跑但连不上 PG** | **是** |
| `did not serve /health_check (HTTP refused)` | 应用/反代没起来 | 否，先看 `docker logs` |
| `answered 200 but not the API health payload` | 该端口不是本 API（如 nginx 的 SPA 回退） | 否，端口被别的进程占用 |

若自检根本没执行到（端口冲突、镜像问题等更早的阶段就失败了），先解决那些；该步可用 `WITTY_NETWORK_SELFCHECK=false` 关闭。

#### 步骤 2: 取证（网络 / 连通性 / 宿主机策略）

```bash
# 两容器应在同一网络且各有 IP
docker network inspect witty-ub-network \
  --format '{{range .Containers}}{{.Name}} {{.IPv4Address}}{{"\n"}}{{end}}'

# 镜像内自带 Python，做 TCP 探测不依赖 nc/telnet
docker exec witty-ub /var/witty-ub/latency/.venv/bin/python -c \
  "import socket; socket.create_connection(('postgres', 5432), 3); print('tcp ok')"

# 宿主机策略
firewall-cmd --state
firewall-cmd --get-default-zone
firewall-cmd --zone="$(firewall-cmd --get-default-zone)" --list-all
firewall-cmd --zone=trusted --list-all
iptables -L FORWARD -n --line-numbers
```

判定要点: 容器各有 IP，但 TCP 探测卡住 3 秒后抛 `TimeoutError`/`ConnectionRefusedError`；且默认 zone 的 `target` 为 `DROP`/`REJECT`、`br-<hash>`（或 `docker0`）接口与 Docker 网段都没出现在 `trusted` zone 的 `interfaces`/`sources` 中。

### 修复方案

#### 方案一: 把 Docker 网络加入信任域（推荐，保留标准部署）

不改动容器端口映射与部署脚本，只调整宿主机策略，是首选。按**网段**加信任域（也可以按网桥接口 `--add-interface="br-<hash>"`，但接口名会随网络重建而变，不推荐）:

```bash
NET=witty-ub-network
SUBNET=$(docker network inspect "$NET" --format '{{(index .IPAM.Config 0).Subnet}}')

sudo firewall-cmd --permanent --zone=trusted --add-source="$SUBNET"
sudo firewall-cmd --reload
firewall-cmd --zone=trusted --list-all   # 确认

# 若 FORWARD 链默认 DROP、Docker 自身的转发规则又被安全策略清理掉了，
# 仅加 trusted zone 还不够，需额外放通网段转发（重启会丢失，需持久化）
sudo iptables -I FORWARD -s "$SUBNET" -j ACCEPT
sudo iptables -I FORWARD -d "$SUBNET" -j ACCEPT
```

#### 方案二: 改用 host 网络模式（可按容器分别指定）

适用于主机安全策略不允许修改防火墙/信任域的机器。容器直接共享宿主机网络命名空间，容器间通信走 `127.0.0.1`，不再经过 Docker 网桥，因此不受信任域策略影响。

**用部署脚本（推荐）**。网络模式可以按容器分别指定，键留空即继承全局 `WITTY_NETWORK_MODE`（默认 `bridge`）:

```bash
# 只切应用容器（PG 仍走 Docker 网络）
WITTY_NETWORK_MODE_APP=host bash deploy/docker/deploy_witty.sh

# PG 与应用都切
WITTY_NETWORK_MODE_PG=host WITTY_NETWORK_MODE_APP=host bash deploy/docker/deploy_witty.sh
```

同机分离部署时后端与前端必须用同一模式（不一致脚本直接报错退出），跨机分离各机器只读本机相关的键。三种形态各自生效的键、以及**部署后逐链路自检**（`WITTY_NETWORK_SELFCHECK`）与**自检失败自动切 host 重试一次**（`WITTY_NETWORK_FALLBACK=auto`）的取值说明，见 [配置参考 §容器级网络模式与部署形态](../usage/03-configuration-reference.md)。

也可以写进 `deploy/deploy.conf` 持久化，或在 `bash deploy/docker/manage.sh install` 交互式安装时选择。

脚本会自动完成联动改写：容器用 `--network host`、跳过 `-p` 与网络创建、容器内 PG 地址按「PG 容器模式 × 应用容器模式」组合推导（host + host → `127.0.0.1:5432`；应用 host + PG bridge → `127.0.0.1:15432`；应用 bridge + PG host → Docker 网关）、前端反代改为 `http://127.0.0.1:9772`。**混合模式（一个 host 一个 bridge）不保证可用**。前端角色回退时会一并改写 `WITTY_BACKEND_URL`；跨机分离失败时脚本**不会**建议切 host，只提示检查对端地址与防火墙。

**host 模式的注意事项**

| 项目 | bridge（默认） | host |
| --- | --- | --- |
| Web UI 访问 | `http://<宿主机IP>:32412` | `http://<宿主机IP>:8080`（`-p` 被忽略，直接占用容器内端口） |
| 容器内访问 PG | `postgres:5432`（容器名 DNS） | `127.0.0.1:5432`（PG 也用 host 时） |
| 宿主机 5432 占用 | 不占用（映射到 15432） | **被 PG 容器占用**，宿主机已有 PG 需先停用 |
| 分离部署 | backend 9772 / frontend 32413，反代 `http://witty-ub-backend:9772` | backend 9772 / frontend 8080，反代 `http://127.0.0.1:9772`（跨机填后端机 IP） |
| 端口冲突 | 由 `WITTY_HOST_PORT` 决定，冲突时启动报 `port is already allocated` | 直接占用容器内端口，宿主机已有服务监听 8080/9772 会启动失败 |

`docker-compose.yml` 无法用变量在 bridge/host 间干净切换，host 模式仍需手工改该文件（`network_mode: host` + 删除 `networks:`/`ports:`，并给 frontend 设 `WITTY_BACKEND_URL=http://127.0.0.1:9772`），详见文件头部说明。

### 验证修复结果

重新部署，脚本末尾自检应通过 `Self-check: app -> PostgreSQL OK (HTTP 200, …)`。需手工复核时（host 模式下地址随之变化）:

```bash
docker inspect --format '{{.State.Health.Status}}' witty-ub          # healthy
docker exec witty-ub curl -s http://127.0.0.1:9772/health_check     # {"status":"healthy"}
```

完整配置项见 [配置参考 §容器级网络模式与部署形态](../usage/03-configuration-reference.md)。

---

## 4. 挂载目录被移动/嵌套后容器内找不到路径

### 问题描述

**症状**: 通过 `WITTY_EXTRA_MOUNTS` 挂载进容器的宿主机目录（默认 `WITTY_EXTRA_MOUNTS="/home:/home:ro"`）在宿主机上被移动、改名或重新组织目录层级后，平台侧访问报找不到路径（注册/上传日志时返回"路径不存在: /..."，或解析任务报日志目录不存在），但在宿主机上确认该路径存在；**重建容器**后又恢复正常。

**典型触发操作**（把远端数据拷到本地挂载目录时多套了一层）:

```bash
mkdir yxh_new
mv logs_20260825 yxh_new/logs_20260825     # 把旧目录收进 yxh_new
cd yxh_new/
mkdir logs_20260924
cd logs_20260924/
# 注意：scp -r 会把源目录整体拷到当前目录下
scp -r root@l41.62.33.7:/home/share/kvcache/yxh_new .
# 实际结果：logs_20260924/yxh_new/...（比预期多一层）
```

**根本原因**: 有两类，现象相似但处理方式完全不同，需先分辨。

1. **数据实际不在预期路径上（路径错位）**。上面的 `scp -r <远端>/yxh_new .` 会产生一层嵌套（真实路径是 `logs_20260924/yxh_new/logs_20260825`，而不是 `logs_20260924/logs_20260825`）。此时宿主机和容器内**看到的是同一份错位结构**，路径本身确实不存在。
2. **挂载源路径在容器创建时解析一次，之后改名/移动不会跟随**。bind 挂载的源路径在 `docker run` 时固定下来：
   - 挂载源目录**本身**（或它的某一级祖先）被 `mv`/改名/重新创建后，容器挂载点仍指向旧的目录对象，宿主机新路径下的内容不会出现；`docker restart` 不重新解析挂载源，只有**重建**容器才会
   - 修改 `WITTY_EXTRA_MOUNTS`（新增挂载或改指向）也必须**重建容器**才能生效，运行中的容器无法追加挂载

   > 若挂载的是上级目录（默认挂载 `/home`），其**子目录**的移动在容器内是实时可见的 —— 这种情况下"找不到路径"基本都属于原因 1（路径写错/嵌套），而不是挂载失效。

### 验证步骤

#### 步骤 1: 看宿主机上的真实层级

```bash
ls -d /home/share/kvcache/yxh_new/logs_20260924/yxh_new   # 嵌套后真实存在的那一层
ls -l /home/share/kvcache/yxh_new/logs_20260924/
```

#### 步骤 2: 看容器内的挂载点与内容

```bash
# 当前生效的挂载源（改过 WITTY_EXTRA_MOUNTS 后这里能看出是否已生效）
docker inspect witty-ub --format '{{range .Mounts}}{{.Source}} -> {{.Destination}} ({{.Mode}}){{"\n"}}{{end}}'

# 容器内同一路径下有什么
docker exec witty-ub ls -l /home/share/kvcache/yxh_new/logs_20260924/
```

#### 步骤 3: 对照结论

| 对比结果 | 结论 |
| ---------- | ------ |
| 容器内与宿主机层级一致，但都缺数据（或都多一层） | 原因 1：路径错位，改路径即可，**不用**重建容器 |
| 容器内为空/与宿主机当前内容不一致；或 `docker inspect` 里的挂载源不是刚配置的值 | 原因 2：挂载源失效或挂载配置未生效，需**重建容器** |

### 修复方案

#### 场景一: 路径错位（无需重建容器）

把数据摆到预期层级，或按实际路径注册（二选一）:

```bash
# A. 拍平嵌套（把多出来那一层的内容提上来）
mv /home/share/kvcache/yxh_new/logs_20260924/yxh_new/* /home/share/kvcache/yxh_new/logs_20260924/
```

下次拷贝时用下面写法避免嵌套（`/.` 结尾表示"只拷目录里的内容"）:

```bash
scp -r root@<远端>:/home/share/kvcache/yxh_new/. /home/share/kvcache/<目标目录>/
# 或
rsync -a root@<远端>:/home/share/kvcache/yxh_new/ /home/share/kvcache/<目标目录>/
```

> 平台在注册日志时会把**当时的绝对路径**记入数据库，路径一变旧记录必然失效：整理完目录后需要在页面上按新路径重新注册，容器是否重建与这一步无关。

#### 场景二: 挂载源被移动/改名，或改过 `WITTY_EXTRA_MOUNTS`（必须重建容器）

```bash
# 单机 All-in-One：脚本会停掉并删除旧容器再重新 run，挂载按新配置解析
bash deploy/docker/manage.sh install-witty

# compose 方式
docker compose --profile allinone up -d --force-recreate
```

> `bash deploy/docker/manage.sh restart`（即 `docker restart`）只重启容器进程，**不会**重新解析挂载源、也不生效新的 `-v` 配置。

### 预防建议

- **先在宿主机把目录结构定好，再在平台上注册路径**；注册后不要再移动、改名或重新组织这些目录
- 不要 `mv`/改名挂载源目录**本身**或其上级目录（与子目录不同，这会让容器挂载点失效）
- 默认挂载是只读（`/home:/home:ro`）：容器内改不动数据，所有目录整理都在宿主机做
- 建议把挂载收敛到确定的目录，而不是整个 `/home`，例如 `WITTY_EXTRA_MOUNTS="/home/share/kvcache:/var/witty-ub/host_logs:ro"`，路径变动的影响面更小、也更易发现
- 若挂载源位于宿主机上的**独立挂载点**（NFS、数据盘挂在 `/home/share` 等），其**挂载关系**变化不会传播进容器（Docker bind 传播为 `rprivate`），同样需要重建容器

---

## 5. 日志管理

### 查看日志

```bash
# 使用 docker compose
docker compose --profile split logs -f              # 分离；单机用 --profile allinone
docker compose --profile split logs --tail=100
docker compose --profile split logs --since 2024-01-01T10:00:00

# 使用纯 Docker 命令
docker logs witty-ub                                 # 单机
docker logs -f witty-ub-frontend                     # 分离前端
docker logs --tail=100 witty-ub
docker logs --since 2024-01-01T10:00:00 witty-ub
```

### 日志位置

容器内日志路径:

| 日志类型 | 路径 |
| --------- | ------ |
| Nginx 访问日志 | `/var/log/witty-ub-web/access.log` |
| Nginx 错误日志 | `/var/log/witty-ub-web/error.log` |
| Latency 服务日志 | `/var/log/witty-ub/latency_server.log` |
| OpenCode 日志 | `/var/log/witty-ub/opencode_server.log` |
| 应用日志 | `/var/log/witty-ub/` |

### 导出日志

```bash
# 导出容器日志到文件
docker compose logs > witty-ub-logs.txt
docker logs witty-ub > witty-ub-logs.txt

# 导出特定时间范围的日志
docker compose logs --since 24h > witty-ub-logs-recent.txt
docker logs --since 24h witty-ub > witty-ub-logs-recent.txt

# 导出容器内日志文件到宿主机
docker cp witty-ub:/var/log/witty-ub/latency_server.log ./latency_server.log
docker cp witty-ub:/var/log/witty-ub-web/error.log ./nginx-error.log
```

### 日志轮转

Docker 默认日志驱动为 `json-file`，建议配置日志轮转:

**使用 docker compose**:

```yaml
services:
  witty-ub:
    logging:
      driver: "json-file"
      options:
        max-size: "100m"
        max-file: "3"
```

**使用纯 Docker 命令**:

```bash
docker run -d \
  --name witty-ub \
  -p 32412:8080 \
  --log-driver json-file \
  --log-opt max-size=100m \
  --log-opt max-file=3 \
  witty-ub:latest
```

---

## 6. 容器内调试

### 进入容器

```bash
# 进入运行中的容器
docker exec -it witty-ub /bin/bash

# 以交互模式启动临时容器（调试启动问题）
docker run -it --rm --name witty-ub-debug \
  -p 32412:8080 \
  -v witty-ub-data:/var/witty-ub/data \
  witty-ub:latest /bin/bash
```

### 常用调试命令

```bash
# 查看进程
ps aux

# 查看网络
netstat -tlnp

# 查看 Python 环境
/var/witty-ub/latency/.venv/bin/pip list

# 手动启动服务
/var/witty-ub/latency/.venv/bin/python /var/witty-ub/latency/access/fastapi_server.py

# 查看容器退出原因
docker inspect witty-ub | grep "ExitCode"
```

---

## 7. 生产环境建议

### 7.1 资源限制

```yaml
services:
  witty-ub:
    deploy:
      resources:
        limits:
          cpus: '4'
          memory: 8G
        reservations:
          cpus: '2'
          memory: 4G
```

### 7.2 重启策略

```yaml
services:
  witty-ub:
    restart: always  # 或 unless-stopped
```

### 7.3 安全加固

**使用非 root 用户运行**:

```dockerfile
RUN groupadd -r witty-ub && useradd -r -g witty-ub witty-ub
USER witty-ub
```

**扫描镜像漏洞**:

```bash
docker scan witty-ub
```

### 7.4 监控与告警

```yaml
healthcheck:
  test: ["CMD", "curl", "-f", "http://localhost:9772/health_check"]
  interval: 30s
  timeout: 10s
  retries: 3
  start_period: 40s
```

### 7.5 日志集中管理

```yaml
logging:
  driver: "syslog"
  options:
    syslog-address: "tcp://log-server:514"
    tag: "witty-ub"
```

### 7.6 备份策略

```bash
#!/bin/bash
# backup.sh
BACKUP_DIR="/backup/witty-ub"
DATE=$(date +%Y%m%d_%H%M%S)

mkdir -p $BACKUP_DIR

docker run --rm \
  -v witty-ub_witty-ub-data:/data \
  -v $BACKUP_DIR:/backup \
  alpine tar czf /backup/data_$DATE.tar.gz -C /data .

find $BACKUP_DIR -name "*.tar.gz" -mtime +30 -delete
```

---

## 相关文档

- 常见问题诊断 → [01-common-issues.md](01-common-issues.md)
- 部署指南 → [../deployment/01-overview.md](../deployment/01-overview.md)
- 配置参考 → [../usage/03-configuration-reference.md](../usage/03-configuration-reference.md)
