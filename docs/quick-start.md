# 快速入门

- [快速入门](#快速入门)
  - [部署指导](#部署指导)
    - [从 RPM 包安装](#从-rpm-包安装)
    - [源码编译安装](#源码编译安装)
  - [使用指导](#使用指导)
    - [超节点系统拓扑实时感知工具witty-ub-topo使用指导](#超节点系统拓扑实时感知工具witty-ub-topo使用指导)
    - [超节点多源系统日志解析工具witty-ub-log使用指导](#超节点多源系统日志解析工具witty-ub-log使用指导)
    - [超节点故障定界工具witty-ub-diag-tool使用指导](#超节点故障定界工具witty-ub-diag-tool使用指导)

## 部署指导

### 从 RPM 包安装

1. 下载 RPM 包：

```bash
sudo yum install -y witty-ub
```

二进制文件位于 `/usr/bin` 目录下，必要的数据和配置文件位于 `/var/witty-ub` 目录下

- witty-ub-topo: 超节点系统拓扑实时感知工具，基于管理组件提供的接口或日志，采集超节点计算节点上资源拓扑信息
- witty-ub-log: 超节点多源系统日志解析工具，采集超节点各组件日志，识别组件故障事件及关联日志
- witty-ub-diag-tool: 超节点故障定界工具，基于故障树驱动的诊断引擎，对KVCache和URMA组件日志进行多级故障定界分析，生成可视化故障分析报告

2. 完成配置
    1. 时延配置：在 `/var/witty-ub/config/latency/latency_config.toml` 中配置时延参数
        1. 时延阈值：各指标的P99异常阈值
            - `TOTAL_P99_THRESHOLD_MS`：总时延 P99 阈值
            - `C2W_P99_THRESHOLD_MS`：C2W 时延 P99 阈值
            - `W2W_P99_THRESHOLD_MS`：W2W 时延 P99 阈值
            - `URMA_P99_THRESHOLD_MS`：URMA 时延 P99 阈值
            - `QUERY_META_P99_THRESHOLD_MS`：查询元数据时延 P99 阈值
        2. 滑动窗口参数：各指标滑动窗口检测的参数
            - `SLIDING_WINDOW_SIZES`：滑动窗口大小
            - `SLIDING_WINDOW_STEPS`：滑动窗口步长
        3. 异常密度阈值：窗口被判定为异常的密度阈值
            - `ZONE_ANOMALY_DENSITY_THRESHOLD`：异常密度阈值
        4. 日志路径 pattern
            - `ds-client-access-log-file`：client接口日志
            - `ds-client-info-log-file`：client运行日志
            - `ds-worker-access-log-file`：worker接口日志
            - `ds-worker-info-log-file`：worker运行日志
    2. 通断配置：在 `/var/witty-ub/config/filepath_config.json` 中配置通断参数
        1. 日志路径 pattern
            - `ds-client-access-log-file`：client接口日志
            - `ds-client-info-log-file`：client运行日志
            - `ds-worker-access-log-file`：worker接口日志
            - `ds-worker-info-log-file`：worker运行日志
            - `resource-log-file`：资源日志

3. 启动服务：

```bash
sudo systemctl daemon-reload
sudo systemctl start witty-ub-latency   # 启动后端服务
sudo systemctl start witty-ub-web       # 启动 Web 服务
```

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
sudo mkdir -p /var/witty-ub/config/latency
cp src/plugins/latency/static/config.toml /var/witty-ub/config/latency/latency_config.toml
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

### 超节点系统拓扑实时感知工具witty-ub-topo使用指导

- 在witty-ub根目录下执行以下命令，输出对应json格式的拓扑信息到文件```/var/witty-ub```目录下```lcne-topology.json```和```urma-topology.json```文件中。        
- 命令行参数如下，详情请见[witty-ub工具使用指导](./witty-ub数据采集工具指导.md)
    ```bash
    ./build/src/witty-ub-topo --network-mode fullmesh --pod-mode on --umq-log-path "pod-name1:/log/path/to/pod-name1,pod-name2:/log/path/to/pod-name2" --pod-id pod-name1,pod-name2
    ```

### 超节点多源系统日志解析工具witty-ub-log使用指导

- 在witty-ub根目录下执行以下命令，输出对应json格式的拓扑信息到文件```/var/witty-ub```目录下```failure-event.json```文件中。
- 命令行参数如下，详情请见[witty-ub工具使用指导](./witty-ub数据采集工具指导.md)
    ```bash
    witty-ub-log --pod-mode on \
    --ubsocket-log-path "pod-name1:/log/messages/path/to/pod-name1,pod-name2:/log/messages/path/to/pod-name2" \
    --umq-log-path "pod-name1:/path/to/pod-name1/umdk/umq/,pod-name2:/path/to/pod-name2/umdk/umq/" \
    --liburma-log-path "pod-name1:/path/to/pod-name1/umdk/urma/,pod-name2:/path/to/pod-name2/umdk/urma/" \
    --libudma-log-path "pod-name1:/log/messages/path/to/pod-name1,pod-name2:/log/messages/path/to/pod-name2" \
    --start-time "2026-03-09 00:00:00" --end-time "2026-03-10 00:00:00"
    ```

### 超节点故障定界工具witty-ub-diag-tool使用指导

- 浏览器访问 `http://localhost:<web-port>`
    - web-port为witty-ub-web服务启动时的端口号，安装 RPM 包部署时为8080，源码编译部署时为5173
    - 远程访问时，请确保防火墙已放行web-port端口，或使用SSH隧道转发web-port端口