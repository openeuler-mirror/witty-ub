# 快速入门

- [快速入门](#快速入门)
  - [部署指导](#部署指导)
    - [docker 容器部署](#docker-容器部署)
    - [从 RPM 包安装](#从-rpm-包安装)
    - [源码编译安装](#源码编译安装)
  - [使用指导](#使用指导)
    - [超节点故障智能监控诊断平台使用指导](#超节点故障智能监控诊断平台使用指导)
    - [超节点系统拓扑实时感知工具witty-ub-topo使用指导](#超节点系统拓扑实时感知工具witty-ub-topo使用指导)
    - [超节点多源系统日志解析工具witty-ub-log使用指导](#超节点多源系统日志解析工具witty-ub-log使用指导)
    - [超节点故障定界工具witty-ub-diag-tool使用指导](#超节点故障定界工具witty-ub-diag-tool使用指导)

## 部署指导

### docker 容器部署

本项目提供了 docker 容器化部署方式，替代传统的 RPM 包部署方式。

- 容器化部署指南首页：[容器化部署指南](./container_deploy/Home.md)
- 已经通过 RPM 包进行部署，希望迁移到容器化部署，请参考[从 RPM 迁移到容器化](./container_deploy/01-overview.md#从-rpm-迁移到容器化)
- 需要构建本地镜像，请参考[镜像构建、上传与打包](./container_deploy/02-build-and-package.md)
- 本项目提供打包好的镜像，可以直接拉取并运行 witty-ub 服务，参考[拉取镜像并运行](./container_deploy/03-pull-and-run.md)
- 部分问题排查与解决方案，请参考[问题排查与解决方案](./container_deploy/04-troubleshooting.md)

### 从 RPM 包安装

1. 下载 RPM 包：

```bash
sudo yum install -y witty-ub
```

二进制文件位于 `/usr/bin` 目录下，必要的数据和配置文件位于 `/var/witty-ub` 目录下

- witty-ub-topo: 超节点系统拓扑实时感知工具，基于管理组件提供的接口或日志，采集超节点计算节点上资源拓扑信息
- witty-ub-log: 超节点多源系统日志解析工具，采集超节点各组件日志，识别组件故障事件及关联日志
- witty-ub-diag-tool: 超节点故障定界工具，基于故障树驱动的诊断引擎，对KVCache和URMA组件日志进行多级故障定界分析，生成可视化故障分析报告

安装 RPM 包后，超节点故障智能监控诊断平台的后端和 Web 服务会自动启动，使用方式参考[witty-ub超节点故障智能监控诊断平台使用指导](./witty-ub超节点故障智能监控诊断平台使用指导.md)

### 源码编译安装

1. 编译环境：openEuler Linux x86/aarch64

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

编译生成的二进制文件位于 `build/src` 目录下

- witty-ub-topo：见[从 RPM 包安装](#从-rpm-包安装)
- witty-ub-log：见[从 RPM 包安装](#从-rpm-包安装)
- witty-ub-diag-tool：见[从 RPM 包安装](#从-rpm-包安装)

5. 复制数据和配置文件到 `/var/witty-ub` 目录

```bash
sudo cp -r ./data /var/witty-ub/
sudo cp -r ./config /var/witty-ub/
```

6. 启动后端服务

```bash
export PYTHONPATH=$PYTHONPATH:<project-path>/src/plugins
cd src/plugins/latency
python3 -m venv .venv   # 以venv为例
source .venv/bin/activate
pip install -r deploy/requirements.txt
python3 access/fastapi_server.py
```

7. 启动 Web 服务

```bash
# 切换终端
cd src/web
npm install
npm run dev # 仅localhost访问，默认端口为 5173
# 或 npm run dev -- --host # 远程访问
```

## 使用指导

### 超节点故障智能监控诊断平台使用指导

本项目提供了基于 Web 的超节点故障智能监控诊断平台，部署完成后，用户可以通过浏览器访问该平台，进行超节点故障定界分析。
- 使用指导：请参考[witty-ub超节点故障智能监控诊断平台使用指导](./witty-ub超节点故障智能监控诊断平台使用指导.md)
- 访问方式；浏览器访问`http://localhost:<web-port>`
    - Web服务在生产环境中默认监听8080端口，开发环境（源码编译安装）监听5173端口，通过docker部署时容器外部访问端口为32412

### 超节点系统拓扑实时感知工具witty-ub-topo使用指导

- 在witty-ub根目录下执行以下命令，输出对应json格式的拓扑信息到文件```/var/witty-ub```目录下```lcne-topology.json```和```urma-topology.json```文件中。        
- 命令行参数如下，详情请见[witty-ub数据采集工具使用指导](./witty-ub数据采集工具指导.md)
    ```bash
    ./build/src/witty-ub-topo --network-mode fullmesh --pod-mode on --umq-log-path "pod-name1:/log/path/to/pod-name1,pod-name2:/log/path/to/pod-name2" --pod-id pod-name1,pod-name2
    ```

### 超节点多源系统日志解析工具witty-ub-log使用指导

- 在witty-ub根目录下执行以下命令，输出对应json格式的拓扑信息到文件```/var/witty-ub```目录下```failure_event.json```文件中。
- 命令行参数如下，详情请见[witty-ub数据采集工具使用指导](./witty-ub数据采集工具指导.md)
    ```bash
    witty-ub-log --pod-mode on \
    --ubsocket-log-path "pod-name1:/log/messages/path/to/pod-name1,pod-name2:/log/messages/path/to/pod-name2" \
    --umq-log-path "pod-name1:/path/to/pod-name1/umdk/umq/,pod-name2:/path/to/pod-name2/umdk/umq/" \
    --liburma-log-path "pod-name1:/path/to/pod-name1/umdk/urma/,pod-name2:/path/to/pod-name2/umdk/urma/" \
    --libudma-log-path "pod-name1:/log/messages/path/to/pod-name1,pod-name2:/log/messages/path/to/pod-name2" \
    --start-time "2026-03-09 00:00:00" --end-time "2026-03-10 00:00:00"
    ```

### 超节点故障定界工具witty-ub-diag-tool使用指导

- 在witty-ub根目录下执行以下命令，输出对应json格式的拓扑信息到文件```/var/witty-ub/log_<random_string>```目录下```failure_view_vis.html```和```failure_traces.log```文件中。
- 命令行参数如下
    ```bash
    witty-ub-diag-tool  \
        --ds-log-path "/path/to/ds_log" \
        --ds-client-access-log-file "<client_access_log_filename_pattern>" \
        --ds-client-info-log-file "<client_info_log_filename_pattern>" \
        --ds-worker-access-log-file "<worker_access_log_filename_pattern>" \
        --ds-worker-info-log-file "<worker_info_log_filename_pattern>" \
        --resource-log-file "<resource_log_filename_pattern>" \
        --start-time "2026-03-09 00:00:00" --end-time "2026-03-10 00:00:00" \
        --random-str "<random_string>" \
    ```