# 快速入门

- [快速入门](#快速入门)
  - [部署指导](#部署指导)
    - [一键部署（推荐）](#一键部署推荐)
    - [docker 容器部署](#docker-容器部署)
    - [从 RPM 包安装](#从-rpm-包安装)
    - [源码编译安装](#源码编译安装)
    - [访问 Web 服务](#访问-web-服务)
  - [使用指导](#使用指导)
    - [超节点故障智能监控诊断平台使用指导](#超节点故障智能监控诊断平台使用指导)

## 部署指导

### 一键部署（推荐）

witty-ub 提供一键部署脚本，自动完成系统依赖安装、PostgreSQL 初始化、Python 虚拟环境创建、C++ 诊断工具编译和服务启动。支持 **openEuler 24.03-LTS** 和 **Ubuntu 24.04 / WSL**。

#### 环境要求

| 环境 | 支持 |
|------|------|
| openEuler 24.03-LTS (x86_64 / aarch64) | ✅ 全功能 |
| Ubuntu 24.04 LTS | ✅ 全功能 |
| WSL (Ubuntu) | ✅ 需预先安装 WSL 内核和 systemd |

#### 部署脚本结构

```
deploy/
├── host/                     # 宿主机/本地部署
│   ├── _lib.sh               # 共享工具库
│   ├── install_deps.sh       # 依赖安装 (系统包 + Python venv)，可独立执行
│   └── deploy.sh             # 总控: PG 初始化 + C++ 编译 + 前端 + 启动 + stop/clean
├── docker/                   # 容器部署
│   ├── deploy_witty.sh       # Docker 一键部署
│   └── manage.sh             # 运维管理 (交互菜单 + 命令行)
├── deploy_pg.sh              # PostgreSQL 独立部署 (Docker/RPM/APT)，两边共用
└── pg.conf                   # PG 数据库连接配置，两边共用
```

#### 快速开始

```bash
# 1. 克隆仓库
git clone https://gitcode.com/openeuler/witty-ub.git
cd witty-ub

# 2. 一键部署（首次运行约 5-10 分钟，取决于网络和 CPU）
bash deploy/host/deploy.sh
```

部署完成后，浏览器打开 **`http://localhost:5173`**。

如果在远程服务器上部署，将 `localhost` 替换为服务器 IP：
```
http://<服务器IP>:5173
```

#### 脚本完成的工作

| 步骤 | 内容 |
|------|------|
| ① OS 检测 | 自动识别 openEuler / Ubuntu，选择对应包管理器 (dnf / apt) |
| ② 系统依赖 | 安装 cmake, gcc-c++, PostgreSQL, Python3, Node.js 等 |
| ③ PostgreSQL | 创建 `witty-ub` 数据库和用户，监听 15432 端口 |
| ④ Python | 创建 `.venv` 虚拟环境，安装 FastAPI/SQLAlchemy/asyncpg 等依赖 |
| ⑤ C++ 编译 | 编译 `witty-ub-diag-tool` 诊断工具 |
| ⑥ 数据文件 | 将故障模式、配置文件复制到 `/var/witty-ub/` |
| ⑦ 启动服务 | 启动 FastAPI 后端 (9772) + Vite 前端 (5173) |

#### 后续使用

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

#### 服务说明

| 服务 | 地址 | 用途 |
|------|------|------|
| 前端 (Vite) | `http://localhost:5173` | Web 管理界面 |
| 后端 (FastAPI) | `http://localhost:9772` | 日志解析 / 异常检测 API |
| 健康检查 | `http://localhost:9772/health_check` | 服务可用性探测 |
| PostgreSQL | `127.0.0.1:15432` | 数据存储 |

#### 日志

所有服务的运行日志位于 `.deploy-logs/` 目录：

```bash
# 查看后端日志
tail -f .deploy-logs/backend.log

# 查看前端日志
tail -f .deploy-logs/frontend.log
```

#### 已知问题

- **sudo 权限**：安装系统包和启动 PostgreSQL 需要 `sudo` 权限。如果当前用户无 sudo 权限，脚本会提示需要手动执行的命令。
- **C++ 编译失败**：如果缺少 C++ 编译依赖导致诊断工具编译失败，脚本会自动生成一个 shell 存根替代。故障定界功能将不可用，但日志解析和异常检测仍正常工作。
- **端口冲突**：默认使用 5173（前端）和 9772（后端）。如需修改，编辑 `src/web/vite.config.ts` 和 `src/plugins/latency/access/fastapi_server.py`。
- **WSL**：建议 WSL 版本 >= 2，并在 `wsl.conf` 中启用 systemd。

---

### docker 容器部署
1. 环境要求：已安装docker 18.09 或更高版本
2. 快速部署指导：
   - 获取witty-ub镜像
        ```bash
        docker pull hub-harbor.oepkgs.net/neocopilot/witty-ub:latest
        ```
    - 运行witty-ub容器，执行如下命令会启动一个witty-ub容器，可以按需进行如下配置：
        - 端口映射：映射主机32412端口到容器8080端口，主机端口可以按需修改为主机没有被占用的其他端口号，容器端口不能修改默认8080端口
        - 日志文件目录映射：witty-ub容器会将主机的`/host/path/log`目录挂载到容器的`/container/path/log`目录，用于存储上传给witty-ub的日志文件/日志压缩文件，用户可以按需修改为对应的主机目录路径和容器映射路径，然后将需要分析的日志文件/日志压缩文件放到`/host/path/log`目录下。其他映射路径无需修改，通过web交互页面进行故障定界时需传入`/container/path/log`目录下的日志文件
        - opencode配置文件目录映射：默认映射宿主机用户的opencode配置目录~/.config/opencode到容器内/root/.config/opencode目录，用户如需进行`model`、`baseurl`、`api-key`等参数配置，具体配置示例可以[参考](./container_deploy/03-pull-and-run.md#配置opencode)，或者查看opencode[官方说明](https://opencode.ai/docs/zh-cn/providers/)
        ```bash
        docker run -d \
            --name witty-ub \
            --restart unless-stopped \
            -p 32412:8080 \
            -v witty-ub-data:/var/witty-ub/data \
            -v witty-ub-logs:/var/log/witty-ub \
            -v witty-ub-uploads:/var/witty-ub/latency/file/file_upload \
            -v witty-ub-results:/var/witty-ub/latency/file/file_parse_result \
            -v /host/path/log:/container/path/log:ro \
            -v ~/.config/opencode:/root/.config/opencode \
            -e PYTHONPATH=/var/witty-ub \
            -e LOG_LEVEL=info \
            --health-cmd="curl -f http://localhost:9772/health_check" \
            --health-interval=30s \
            --health-timeout=10s \
            --health-retries=3 \
            --health-start-period=40s \
            --network witty-ub-network \
            witty-ub:latest
        ```
    - 检查容器状态，确认witty-ub容器已启动：

        ```bash
        docker ps -a | grep witty-ub        
        ```
4. witty-ub容器镜像介绍、容器镜像构建、上传与打包、部署与运行、已知问题等详细指导请见：[容器化部署指南](./container_deploy/Home.md)
4. 已经通过 RPM 包进行部署，希望迁移到容器化部署，请参考[从 RPM 迁移到容器化](./container_deploy/01-overview.md#从-rpm-迁移到容器化)

### 从 RPM 包安装
1. 系统要求：openEuler 24.03-LTS-SP3或openEuler 24.03-LTS-SP4
2. repo源配置，项目目前迭代中，体验witty-ub最新功能版本建议从openEuler 24.03-LTS-SP3或openEuler 24.03-LTS-SP4最新的每日构建repo源中安装witty-ub，openEuler 24.03-LTS-SP3或openEuler 24.03-LTS-SP4的每日构建repo源地址如下：
    - openEuler 24.03-LTS-SP3：http://121.36.84.172/dailybuild/EBS-openEuler-24.03-LTS-SP3/
    - openEuler 24.03-LTS-SP4：http://121.36.84.172/dailybuild/EBS-openEuler-24.03-LTS-SP4/
    - repo源配置参考配置如下（用户需要根据实际情况修改openeuler-2026-07-08-07-31-12为最新的每日构建目录）：
        - openEuler 24.03-LTS-SP3：
        ```bash
        sudo tee /etc/yum.repos.d/witty-ub.repo <<EOF
        [witty-ub]
        name=witty-ub
        baseurl=http://121.36.84.172/dailybuild/EBS-openEuler-24.03-LTS-SP3/openeuler-2026-07-08-07-31-12/everything/\$basearch/
        enabled=1
        gpgcheck=0
        EOF
        ```
        - openEuler 24.03-LTS-SP4：
        ```bash
        sudo tee /etc/yum.repos.d/witty-ub.repo <<EOF
        [witty-ub]
        name=witty-ub
        baseurl=http://121.36.84.172/dailybuild/EBS-openEuler-24.03-LTS-SP4/openeuler-2026-07-08-07-31-12/everything/\$basearch/
        enabled=1
        gpgcheck=0
        EOF
        ```     
3. 安装witty-ub RPM 包：

    ```bash
    sudo yum install -y witty-ub
    ```
4. opencode安装和配置
    * 安装opencode方法1：
        ```
        yum install opencode
        ```
    * 安装opecode方法2：按照opencode[官方安装说明](https://opencode.ai/docs/zh-cn/#%E5%AE%89%E8%A3%85)进行安装
    * opencode配置：如需进行`model`、`baseurl`、`api-key`等参数配置，具体配置示例可以[参考](./container_deploy/03-pull-and-run.md#配置opencode)，或者查看opencode[官方说明](https://opencode.ai/docs/zh-cn/providers/)

5. 启动opencode后台服务：
    如果需要使用远程部署的OpenCode Server，跳过此步骤，直接在前端Agent窗口填写远程OpenCode Server的地址和端口即可，参考[witty-ub超节点故障智能监控诊断平台操作流程](./witty-ub超节点故障智能监控诊断平台使用指导.md#操作流程)

    ```bash
    bash /var/witty-ub/latency/deploy/run_opencode.sh
    ```

6. 检查witty-ub服务状态：

    ```bash
    sudo systemctl status witty-ub-web
    sudo systemctl status witty-ub-latency
    ```

### 源码编译安装

1. 编译环境要求：openEuler 24.03-LTS-SP3/SP4 Linux x86/aarch64

2. 安装依赖项
    - cmake gcc-c++ make log4cplus-devel cpp-httplib-devel sqlite-devel jsoncpp-devel tinyxml2-devel openssl-devel zlib-devel brotli-devel re2-devel
    
    ```bash
    sudo yum install -y gcc-c++ make log4cplus-devel cpp-httplib-devel sqlite-devel jsoncpp-devel tinyxml2-devel openssl-devel zlib-devel brotli-devel re2-devel
    ```

3. 获取源码并编译

    ```bash
    git clone https://gitcode.com/openeuler/witty-ub.git
    cd witty-ub
    mkdir build
    sudo cmake -S . -B build
    sudo cmake --build build -j$(nproc)
    ```

4. 配置环境变量

    ```bash
    export WITTY_DIR=/var/witty-ub
    export WITTY_INSTALL_PATH=<project-path>/build/src
    ```

5. 复制数据和配置文件到 `/var/witty-ub` 目录

    ```bash
    sudo cp -r ./data /var/witty-ub/
    sudo cp -r ./config /var/witty-ub/
    ```

6. opencode安装和配置
    * 安装opencode方法1：
        ```
        yum install opencode
        ```
    * 安装opecode方法2：按照opencode[官方安装说明](https://opencode.ai/docs/zh-cn/#%E5%AE%89%E8%A3%85)进行安装
    * opencode配置：如需进行`model`、`baseurl`、`api-key`等参数配置，具体配置示例可以[参考](./container_deploy/03-pull-and-run.md#配置opencode)，或者查看opencode[官方说明](https://opencode.ai/docs/zh-cn/providers/)

7. 启动opencode后台服务：
    如果需要使用远程部署的OpenCode Server，跳过此步骤，直接在前端Agent窗口填写远程OpenCode Server的地址和端口即可，参考[witty-ub超节点故障智能监控诊断平台操作流程](./witty-ub超节点故障智能监控诊断平台使用指导.md#操作流程)

    ```bash
    bash src/plugins/latency/deploy/run_opencode.sh
    ```

8. 启动后端服务

    ```bash
    export PYTHONPATH=$PYTHONPATH:<project-path>/src/plugins
    cd src/plugins/latency
    python3 -m venv .venv   # 以venv为例
    source .venv/bin/activate
    pip install -r deploy/requirements.txt
    python3 access/fastapi_server.py
    ```

9. 启动 Web 服务

    ```bash
    # 切换终端
    cd src/web
    npm install
    npm run dev # 仅localhost访问，默认端口为 5173
    # 或 npm run dev -- --host # 远程访问
    ```

### 访问 Web 服务
1. 本机安装场景，在本机通过以上方式启动witty-ub：
    - 浏览器访问 `http://localhost:<witty-ub-web-port>`，即可访问witty-ub的web页面
    - witty-ub-web-port为witty-ub-web服务端口号，如witty-ub通过rpm包安装和启动，端口号默认值为8080，如witty-ub通过源码编译和启动，端口号默认值为5173
2. 远程服务器安装场景，在远程服务器通过以上方式启动witty-ub，本机可以访问远程服务器:    
    - 如witty-ub-web服务在远程服务器上启动，本机浏览器需要远程访问时，需要在远程服务器防火墙上开放witty-ub-web服务的端口号，或者通过ssh隧道进行访问。
    - 防火墙放行端口配置（假设端口号为5173）：      
        - 配置临时端口转发，当witty-ub服务运行在远程服务器的虚拟机中时，需配置端口转发虚拟机端口到物理机端口上，如不是此场景无需执行，直接执行下一步命令
            ```
            iptables -t nat -A PREROUTING -p tcp --dport 5173 -j DNAT --to-destination <虚拟机ip>:5173
            iptables -I FORWARD -d 192.168.122.8 -p tcp --dport 5173 -j ACCEPT
            ```
        - 在远程服务器上执行命令，让防火墙放行端口
            ```
            firewall-cmd --permanent --add-port=5173/tcp
            ```
        - 本机浏览器访问`http://<物理机ip>:5173`，即可访问witty-ub-diag-tool的web页面
    - 通过ssh隧道访问（假设端口号为5173）：
        - 当witty-ub服务运行在远程物理机上的虚拟机中时，需要在本机上执行ssh隧道访问命令```ssh -v -L <本机端口>:<虚拟机ip>:5173 <物理机user>@<物理机ip>```，命令示例如下
            ```
            ssh -v -L 5173:192.168.122.8:5173 root@10.11.112.79
            ```
        - 当witty-ub服务运行在远程物理机上时，需要在本机上执行ssh隧道访问命令```ssh -L <本机端口>:127.0.0.1:5173 <物理机user>@<物理机ip>```，命令示例如下：
            ```
            ssh -v -L 5173::127.0.0.1:5173 root@10.11.112.79
            ```
        本机浏览器访问`http://localhost:5173`，即可访问witty-ub-diag-tool的web页面

## 使用指导
### 超节点故障智能监控诊断平台使用指导
本项目提供了基于 Web 的超节点故障智能监控诊断平台，部署完成后，用户可以通过浏览器访问该平台，进行超节点故障定界分析。
- 使用指导：请参考[witty-ub超节点故障智能监控诊断平台使用指导](./witty-ub超节点故障智能监控诊断平台使用指导.md)
