# 试验性前端（exp）打包

## 1. 概述

试验性前端（exp）对外提供两种产物，均由既有 release 产物派生，不改动后端与既有前端：

| 产物 | 版本规则 | 用途 |
| ------ | ------ | ------ |
| 容器镜像 `<repo>/witty-ub:frontend-exp-<YYYYMMDD>`（移动标签 `frontend-exp`） | 按日期，一天一个 nightly | 容器化部署 exp 前端 |
| RPM 子包 `witty-ub-web-exp-<version>-<release>.<arch>.rpm` | 与主包同 `Version-Release`，不单独发版本号 | RPM 部署 exp 前端 |

镜像 = **当前 release 前端镜像**（`witty-ub:frontend-<release>`，含 Nginx、OpenCode、诊断工具与
Agent bundle）+ 当日 exp 前端静态产物，只替换静态资源与 nginx 静态根。

追溯信息：

| 产物 | 记录位置 |
| ------ | ------ |
| exp 镜像 | OCI label：`org.opencontainers.image.version=exp-<日期>`、`.revision=<commit>`、`.created`、`com.witty-ub.base.release`、`com.witty-ub.base.digest` |
| 镜像 / RPM 载荷 | `/var/witty-ub/web-exp/BUILD_INFO`（`base_release`、`source_commit`、`build_date`、`build_kind`） |

---

## 2. 构建镜像

### 2.1 前置条件

- Node.js ≥ 20.18.2、npm（宿主机原生构建，不能放进 QEMU）
- `docker` + `buildx`，且使用 `docker-container` driver：
  `docker buildx create --name witty-ub-builder --driver docker-container --use`
- 已登录镜像仓：`docker login hub-harbor.oepkgs.net`
- 已发布对应 release 的前端镜像：`<repo>/witty-ub:frontend-<release>`

### 2.2 构建与推送

```bash
# 当天 nightly：底座取仓库最新 release tag，推送 frontend-exp-<今天> 与 frontend-exp
bash scripts/publish_frontend_exp.sh

# 指定底座 / 日期 / 只本地构建（调试）
BASE_RELEASE=v1.0.4-5 EXP_DATE=20260916 bash scripts/publish_frontend_exp.sh
PUSH=0 bash scripts/publish_frontend_exp.sh          # 本地 load，多平台自动收敛为当前架构
SKIP_BUILD=1 bash scripts/publish_frontend_exp.sh    # 复用已有 dist，仅重打镜像
```

| 环境变量 | 默认值 | 说明 |
| ------ | ------ | ------ |
| `REGISTRY` / `PROJECT` | `hub-harbor.oepkgs.net` / `neocopilot` | 镜像仓与项目 |
| `BASE_RELEASE` | 仓库最新 `v*` tag | exp 镜像的 release 底座 |
| `EXP_DATE` | 当天 `YYYYMMDD` | exp 版本日期 |
| `EXP_SOURCE_DIR` | `src/web_exp`，缺失时回退 `src/web_new` | exp 前端源码目录 |
| `PLATFORMS` | `linux/amd64,linux/arm64` | 目标平台 |
| `PUSH` / `SKIP_BUILD` / `KEEP_CONTEXT` | `1` / `0` / `0` | 推送 / 跳过构建 / 保留临时上下文 |

脚本只推送 `frontend-exp-*` 标签，不会触碰 `frontend`、`latest`、`backend` 与 `base-*`。

### 2.3 镜像构成

`deploy/docker/Dockerfile.frontend-exp` 为 overlay 构建（构建上下文由发布脚本组装，仅
`dist/` 与 nginx 模板）：

- `COPY dist/ /var/witty-ub/web-exp/`（含 `BUILD_INFO`）
- 由 release 容器模板派生 nginx 配置，**只替换静态根**为 `/var/witty-ub/web-exp`，
  其余（`/run/witty-ub-web`、`/var/log/witty-ub-web`、`listen 8080`、反代规则）沿用容器既有布局
- 写入镜像 label（版本、commit、构建时间、底座 release/digest）

### 2.4 校验

```bash
docker buildx imagetools inspect <repo>/witty-ub:frontend-exp-<YYYYMMDD>   # OCI index，amd64+arm64
docker run --rm --entrypoint cat <repo>/witty-ub:frontend-exp-<YYYYMMDD> /var/witty-ub/web-exp/BUILD_INFO
```

---

## 3. 构建 RPM 子包

RPM 子包由 EulerMaker 工程 **witty-builder** 构建，预构建产物直接发布到该工程的仓库，
安装端只需配置仓库即可 `dnf install`：

| 项 | 值 |
| ------ | ------ |
| 构建工程 | <https://eulermaker.openeuler.openatom.cn/project/overview?osProject=witty-builder> |
| 仓库 ID | `Witty-Builder` |
| 仓库地址 | `https://eulermaker.openeuler.openatom.cn/api/ems5/repositories/witty-builder/openEuler:24.03-LTS-SP3/$basearch/` |
| 目标版本 | openEuler 24.03 LTS SP3（仓库组件 `openEuler:24.03-LTS-SP3`） |

### 3.1 打包仓改动

spec 与 patch 位于打包仓 `hongyu-shi/src-witty-ub` 的 `feat/frontend-exp` 分支：
<https://atomgit.com/hongyu-shi/src-witty-ub/tree/feat/frontend-exp>

- `witty-ub.spec`：新增 `Source1`、`Patch74`，以及 `%package / %files / %install /
  %post / %preun / %postun web-exp` 段；
- `0074-feat-web-exp-experimental-frontend-runtime-assets.patch`：向源码树加入
  `packaging/systemd/witty-ub-web-exp.service`、`packaging/nginx/witty-ub-web-exp.conf.template`、
  `deploy/rpm/web-exp.env`、`deploy/rpm/witty-ub-web-exp-ctl`。

`witty-ub-web-exp` 与 `witty-ub-web` 互不依赖、互不冲突，meta 包 `witty-ub` 不依赖它；
RPM 版本沿用主包 `%{version}-%{release}`，不随 nightly 变化。

### 3.2 Source1（exp 前端 dist）的来源与生成

`Source1: witty-ub-web-exp-dist.tar.gz` 为预构建产物，来源为源码仓
`hongyu-shi/witty-ub` 的 `feat/frontend-refresh` 分支（目录 `src/web_new`）：
<https://atomgit.com/hongyu-shi/witty-ub/tree/feat/frontend-refresh>。

```bash
# 在该分支检出目录执行
cd src/web_new && npm ci --no-audit --no-fund && npm run build-only && cd ../..
COPYFILE_DISABLE=1 tar -czf witty-ub-web-exp-dist.tar.gz -C src/web_new dist
# macOS 上 COPYFILE_DISABLE=1 用于避免 ._* 元数据进入压缩包（否则 rpm 打包会报未打包文件）
```

压缩包含 `dist/` 与 `dist/BUILD_INFO`（`source_commit` / `build_date` / `build_kind=rpm-patch` /
`package_version`）。

### 3.3 在 EulerMaker 工程构建

1. 在 `witty-builder` 工程中刷新 `Source1` 附件 `witty-ub-web-exp-dist.tar.gz`（内容按 3.2 生成）；
2. 触发构建（工程使用打包仓 `feat/frontend-exp` 分支的 spec 与 Patch74）；
3. 构建完成后产物发布到工程仓库，机器按 3.6 配置仓库安装即可。

每次 nightly 只刷新附件与重编，**spec、Patch74 与 NVR 均不变**。

### 3.4 本地复现构建（可选）

用于在提交工程前验证 spec 与 Patch74：

```bash
rpmdev-setuptree
cd /path/to/src-witty-ub                # 打包仓检出目录（分支 feat/frontend-exp）
cp witty-ub-v1.0.4.tar.gz witty-ub-web-exp-dist.tar.gz ./*.patch ~/rpmbuild/SOURCES/
cp witty-ub.spec ~/rpmbuild/SPECS/
rpmbuild -bb ~/rpmbuild/SPECS/witty-ub.spec
# 产物：~/rpmbuild/RPMS/<arch>/witty-ub-web-exp-<version>-<release>.<arch>.rpm
```

### 3.5 包内容

| 路径 | 说明 |
| ------ | ------ |
| `/var/witty-ub/web-exp/` | exp 前端静态产物（含 `BUILD_INFO`） |
| `/etc/witty-ub/web-exp/env` | 连接配置（`WITTY_BACKEND_URL` / `WITTY_AGENT_URL` / `WITTY_WEB_EXP_PORT`） |
| `/usr/share/witty-ub/nginx/witty-ub-web-exp.conf.template` | Nginx 模板（8081，静态根 `web-exp`） |
| `/usr/lib/systemd/system/witty-ub-web-exp.service` | systemd 服务 |
| `/usr/bin/witty-ub-web-exp-ctl` | 控制脚本（渲染配置 + 启停 + SELinux 标签） |

### 3.6 仓库配置与安装 / 更新

把 `witty-builder` 仓库写入 `/etc/yum.repos.d/Witty-Builder.repo`：

```ini
[Witty-Builder]
name=EulerMaker Witty Builder
baseurl=https://eulermaker.openeuler.openatom.cn/api/ems5/repositories/witty-builder/openEuler:24.03-LTS-SP3/$basearch/
metadata_expire=60
enabled=1
gpgcheck=1
gpgkey=https://eulermaker.openeuler.openatom.cn/api/ems5/repositories/witty-builder/openEuler:24.03-LTS-SP3/$basearch/RPM-GPG-KEY-openEuler
```

```bash
sudo dnf makecache
sudo dnf install -y witty-ub-web-exp

# 更新到当日构建：NVR 不变，需显式 reinstall（metadata_expire=60 保证元数据已刷新）
sudo dnf --refresh reinstall -y witty-ub-web-exp

# 只想从该仓库取 exp 子包时，可在 .repo 中加：
# includepkgs=witty-ub-web-exp
```

- 仓库提供的是**最新一次构建**的产物（同 NVR 覆盖）：升级用 `reinstall`；如需回到较早版本，
  用对应日期的 `Source1` 按 3.4 重新构建该 RPM 后安装。
- 该仓库同时包含工程构建的其他 witty-ub 子包，`includepkgs` 可避免其他包被仓库内容替换。

## 相关文档

- 部署（容器 / 源码 / RPM）→ [../deployment/09-experimental-frontend.md](../deployment/09-experimental-frontend.md)
- 使用（访问入口、Agent、常见问题）→ [../usage/04-experimental-frontend.md](../usage/04-experimental-frontend.md)
- 既有镜像构建与分发 → [01-docker-build.md](01-docker-build.md) | [03-distribution.md](03-distribution.md)
