# Latency 插件开发指南

## 项目概述

本插件是一个基于 FastAPI 的日志解析、异常检测与故障定界服务，采用分层架构设计，支持异步任务队列和多进程任务执行。

- **后端存储**：使用 **PostgreSQL**，启动时自动建表、建分区、建索引。
- **日志解析**：通过多进程并行扫描、关联分析、异常检测，将结果写入 `log_parse_result`、`anomalous_event` 等表。
- **故障定界**：解析完成后由 `kv_cache_log_event_diagnosis_worker` 调用 C++ 二进制 `witty-ub-diag-tool` 对日志进行定界，生成 `log_failure_event`、`trace_failure_event` 与 `diagnosis_case`。

---

## 目录结构

```
latency/
├── access/                     # 入口层 (App)
│   ├── fastapi_server.py       # FastAPI 应用主入口
│   └── shell_server.py         # Shell 命令行入口
├── routers/                    # 路由层 (Router)
│   ├── anomalous_event.py
│   ├── anomalous_event_chain.py
│   ├── diagnosis_case.py
│   ├── diagnosis_config.py
│   ├── failure_mode_knowledge.py
│   ├── log_failure_event_result.py
│   ├── log_file.py
│   ├── log_knowledge.py
│   ├── log_parse_result.py
│   ├── src_dst_aggregated_event.py
│   └── task.py
├── services/                   # 服务层 (Service)
│   ├── anomalous_event.py
│   ├── anomalous_event_chain.py
│   ├── diagnosis_case.py
│   ├── failure_mode_knowledge.py
│   ├── log_failure_event_result.py
│   ├── log_file.py
│   ├── log_knowledge.py
│   ├── log_parse_result.py
│   ├── src_dst_aggregated_event.py
│   └── task.py
├── database/                   # 数据层
│   ├── engine.py               # PostgreSQL 异步引擎 / PGManager
│   ├── models.py               # SQLAlchemy ORM 模型
│   ├── init.py                 # 初始化、分区、索引
│   ├── utils.py                # 时间 / IP / COPY 等转换辅助
│   └── managers/               # 数据管理器
├── task/                       # 任务处理层
│   ├── task_handler.py         # 任务调度器
│   ├── process_handle.py       # 多进程管理（spawn 子进程）
│   └── worker/
│       ├── base.py             # 基础 Worker
│       ├── kv_cache_log_parse_worker.py
│       ├── kv_cache_log_event_diagnosis_worker.py
│       └── store_trace_context_logs_worker.py
├── parse/                      # 日志解析器
│   ├── base_parser.py
│   ├── sdk_access_log_parser.py
│   ├── worker_access_log_parser.py
│   ├── query_meta_log_parser.py
│   ├── remote_pull_log_parser.py
│   ├── link_log_parser.py
│   ├── urma_log_parser.py
│   └── correlation/            # 关联分析
│       ├── correlator.py
│       └── result_builder.py
├── schemas/                    # 数据模型（Pydantic）
│   ├── config.py
│   ├── detect.py
│   ├── diagnosis_case.py
│   ├── ds_log.py
│   ├── failure_mode.py
│   ├── log.py
│   ├── log_failure_event.py
│   ├── request.py
│   ├── response.py
│   └── task.py
├── ENUM/                       # 枚举定义
│   ├── detect.py
│   ├── ds_log.py
│   ├── general.py
│   ├── model.py
│   ├── sampling.py
│   └── task.py
├── config/                     # 配置模块
│   └── config.py
├── common/                     # 公共工具
│   ├── convertor.py
│   ├── ds_log_io.py
│   ├── stats.py
│   └── zip_handler.py
├── regex/                      # 正则解析规则
│   ├── kvcache_log.py
│   └── kvcache_log_file.py
├── deploy/                     # 部署文件
│   ├── deploy.sh
│   ├── requirements.txt
│   └── ...
├── test/                       # 测试
│   ├── test_api_unit.py
│   ├── test_postgresql_integration.py
│   ├── test_detection_optimized.py
│   ├── test_diagnosis_case.py
│   ├── test_diagnosis_api_contract.py
│   └── ...
├── ds_log_analyzer.py          # DS 日志分析器主入口
├── LICENSE
└── README.en.md
```

---

## 技术栈与依赖

### Python 运行时

- Python >= 3.10
- FastAPI、Uvicorn、APScheduler、Pydantic v2
- SQLAlchemy 2.x + asyncpg（PostgreSQL 异步驱动）
- aiohttp、aiofiles、httpx、requests、rarfile 等

完整依赖见 `deploy/requirements.txt`，其中已包含 PostgreSQL 所需的 `sqlalchemy` 与 `asyncpg`。

### PostgreSQL

- PostgreSQL 14+（测试使用 PostgreSQL 16）
- 需要创建目标数据库，例如 `latency_test`

### C++ 故障定界工具

- 可执行文件：`witty-ub-diag-tool`
- 默认查找路径：`/usr/bin/witty-ub-diag-tool`
- 可通过环境变量 `WITTY_INSTALL_PATH` 自定义
- 运行时需要 `/var/witty-ub/data` 和 `/var/witty-ub/config` 下的数据与配置文件

---

## 部署指南

### 环境要求

- Python >= 3.10
- PostgreSQL 14+
- 如需解压 `.rar`：`unrar` 或 `rarfile` 依赖
- 如需完整故障定界能力：需要编译或安装 `witty-ub-diag-tool`

### 1. 启动 PostgreSQL

可以使用本地实例或容器：

```bash
# 示例：用容器启动一个 PG16 测试实例
docker run -d --name pg16-test \
  -e POSTGRES_USER=postgres \
  -e POSTGRES_PASSWORD=postgres \
  -e POSTGRES_DB=latency_test \
  -p 15432:5432 postgres:16
```

### 2. 创建 Python 虚拟环境并安装依赖

```bash
cd /path/to/witty-ub/src/plugins/latency

python3 -m venv .venv
source .venv/bin/activate

pip install -r deploy/requirements.txt
```

### 3. 编译 / 安装 `witty-ub-diag-tool`

#### 方式 A：源码编译（推荐开发环境）

依赖（Ubuntu/Debian 示例）：

```bash
apt-get install -y cmake g++ make \
  liblog4cplus-dev libcpp-httplib-dev libsqlite3-dev \
  libjsoncpp-dev libtinyxml2-dev libssl-dev zlib1g-dev \
  libbrotli-dev libre2-dev
```

openEuler 环境依赖见项目根目录 `Dockerfile.base`：

```text
cmake gcc-c++ make log4cplus-devel cpp-httplib-devel sqlite-devel
jsoncpp-devel tinyxml2-devel openssl-devel zlib-devel brotli-devel re2-devel
```

编译：

```bash
cd /path/to/witty-ub
mkdir build && cd build
cmake ..
make -j$(nproc) witty-ub-diag-tool

sudo cp src/witty-ub-diag-tool /usr/bin/witty-ub-diag-tool
sudo chmod 0755 /usr/bin/witty-ub-diag-tool
```

> 在 Ubuntu 上编译时，`libtinyxml2-dev` 可能不提供 CMake config 文件，需要补充 `Findtinyxml2.cmake` 或在 `CMAKE_MODULE_PATH` 中指定查找模块。

#### 方式 B：Docker 镜像（推荐生产环境）

项目根目录提供 `Dockerfile.base` 和 `Dockerfile`：

```bash
# 构建基础镜像（含依赖）
docker build -f Dockerfile.base -t witty-ub-base:latest .

# 构建应用镜像（会自动编译 C++ 二进制并复制到 /usr/bin）
docker build -f Dockerfile -t witty-ub:latest .
```

### 4. 准备数据与配置文件

将项目数据文件复制到运行目录：

```bash
sudo mkdir -p /var/witty-ub/data/kvcache /var/witty-ub/data/urma \
             /var/witty-ub/data/view-vis /var/witty-ub/config/agents

sudo cp /path/to/witty-ub/data/failure_mode_tree.json /var/witty-ub/data/
sudo cp /path/to/witty-ub/data/kvcache/*.json /var/witty-ub/data/kvcache/
sudo cp /path/to/witty-ub/data/urma/*.json /var/witty-ub/data/urma/
sudo cp /path/to/witty-ub/data/view-vis/* /var/witty-ub/data/view-vis/

sudo cp /path/to/witty-ub/config/diagnosis_config.toml /var/witty-ub/config/
sudo cp /path/to/witty-ub/config/opencode.json /var/witty-ub/config/
sudo cp /path/to/witty-ub/config/agents/witty-ub-diagnostician.md /var/witty-ub/config/agents/
```

### 5. 配置 TOML

所有配置统一放在 `diagnosis_config.toml`，默认路径 `/var/witty-ub/config/diagnosis_config.toml`，也可通过环境变量 `CONFIG` 指定其他 TOML 文件。

完整示例：

```toml
[db]
pg_host = "127.0.0.1"
pg_port = 5432
pg_database = "latency_test"
pg_user = "postgres"
pg_password = "postgres"
pg_pool_size = 10
pg_max_overflow = 20

[log_filename_pattern]
ds_client_access_log_file = ["ds_client_access*.log", "*_access.log", "*_split_access.log"]
ds_client_info_log_file = ["ds_client*.INFO.log", "*_runtime.log", "*_split_runtime.log"]
ds_worker_access_log_file = ["access*.log", "*_access.log", "*_split_access.log"]
ds_worker_info_log_file = ["datasystem_worker.INFO*.log", "kvcache.INFO*.log", "*_runtime.log", "*_split_runtime.log"]
resource_log_file = ["resource.log"]

[log_analyzer_params]
total_p99_threshold_ms = 5.0
c2w_p99_threshold_ms = 2.0
w2w_p99_threshold_ms = 1.5
urma_link_p99_threshold_ms = 4.0
query_meta_p99_threshold_ms = 1.0
total_p9999_threshold_ms = 5.0
total_pmax_threshold_ms = 5.0
total_ave_threshold_ms = 5.0
```

#### 日志路径映射 `[log_filename_pattern]`

Worker 解析日志时，会根据上传日志所在的目录，按以下 key 的 glob 规则匹配文件名：

| key | 用途 | 默认匹配文件 |
|-----|------|-------------|
| `ds_client_access_log_file` | SDK 客户端接口日志 | `ds_client_access*.log`、`*_access.log`、`*_split_access.log` |
| `ds_client_info_log_file` | SDK 客户端信息/运行时日志 | `ds_client*.INFO.log`、`*_runtime.log`、`*_split_runtime.log` |
| `ds_worker_access_log_file` | Worker 接口日志 | `access*.log`、`*_access.log`、`*_split_access.log` |
| `ds_worker_info_log_file` | Worker 信息/运行时日志 | `datasystem_worker.INFO*.log`、`kvcache.INFO*.log`、`*_runtime.log`、`*_split_runtime.log` |
| `resource_log_file` | 资源日志 | `resource.log` |

> 如果实际日志文件名与默认值不同，可修改对应 key 的 glob 列表，无需改代码。

#### 异常检测参数 `[log_analyzer_params]`

异常检测采用**直接阈值判断**：单条日志的某个指标超过对应阈值即标记为异常。

| key | 说明 |
|-----|------|
| `total_p99_threshold_ms` | 总时延 P99 阈值（毫秒） |
| `c2w_p99_threshold_ms` | Client-to-Worker 时延阈值 |
| `w2w_p99_threshold_ms` | Worker-to-Worker 时延阈值 |
| `urma_link_p99_threshold_ms` | URMA 建链时延阈值 |
| `query_meta_p99_threshold_ms` | Worker QueryMeta 时延阈值 |
| `total_p9999_threshold_ms` | 总时延 P9999 阈值（毫秒） |
| `total_pmax_threshold_ms` | 总时延最大值阈值（毫秒） |
| `total_ave_threshold_ms` | 总时延均值阈值（毫秒） |

### 6. 启动服务

```bash
cd /path/to/witty-ub/src/plugins/latency
source .venv/bin/activate
export PYTHONPATH=/path/to/witty-ub/src/plugins:$PYTHONPATH

python -m latency.access.fastapi_server
```

服务默认监听 `0.0.0.0:9772`。

健康检查：

```bash
curl http://127.0.0.1:9772/health_check
```

### 7. 启动 OpenCode（可选）

诊断 Agent 通过 HTTP 直接查询已启动的 FastAPI 服务。使用部署脚本校验配置并启动
OpenCode：

```bash
bash /path/to/witty-ub/deploy/deploy_opencode.sh
```

---

## 配置说明

`latency/schemas/config.py` 定义了配置模型，关键字段如下：

| 字段 | 类型 | 说明 |
|------|------|------|
| `db.backend` | str | 固定为 `"postgresql"` |
| `db.pg_host` | str | PG 主机 |
| `db.pg_port` | int | PG 端口 |
| `db.pg_database` | str | 数据库名 |
| `db.pg_user` | str | 用户名 |
| `db.pg_password` | str | 密码 |
| `db.pg_pool_size` | int | 连接池大小 |
| `db.pg_max_overflow` | int | 最大溢出连接 |
| `service.uvicorn_ip` | str | FastAPI 监听 IP |
| `service.uvicorn_port` | int | FastAPI 监听端口 |
| `service.log_level` | str | 日志级别 |
| `task.cpu_limit` | int | 任务子进程 CPU 限制 |
| `task.task_retry_times` | int | 任务最大重试次数 |
| `log_filename_pattern` | dict[list[str]] | 各类日志文件的 glob 匹配规则 |
| `log_analyzer_params` | dict | 异常检测阈值与滑动窗口参数 |


---

## 数据路径一：HTTP 请求处理流程

### app => router => service => manager

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│     App     │────▶│   Router    │────▶│   Service   │────▶│   Manager   │
│(FastAPI app)│     │(APIRouter)  │     │(Biz Logic)  │     │(DB Access)  │
└─────────────┘     └─────────────┘     └─────────────┘     └─────────────┘
     │                    │                    │                    │
     ▼                    ▼                    ▼                    ▼
 fastapi_server.py    log_file.py         log_file.py         log_file.py
```

### 各层职责

#### 1. App 层 (`access/fastapi_server.py`)

- 创建 FastAPI 应用实例
- 注册 Router
- 启动时初始化 PostgreSQL（`PGManager.initialize` + `init_postgresql_database`）
- 加载故障模式知识库
- 配置 APScheduler 每 5 秒执行 `TaskHandler.handle_tasks`

```python
@app.on_event("startup")
async def startup_event():
    await configure()
    await mk_dirs()
    config = Config().get_config()
    PGManager.initialize(config.db.pg_dsn_url(), ...)
    await init_postgresql_database()
    await FailureModeKnowledge().init_failure_mode_knowledge()
    scheduler.add_job(TaskHandler.handle_tasks, "interval", seconds=5)
    scheduler.start()
```

#### 2. Router 层 (`routers/`)

- 定义 HTTP API 端点、路径、方法、参数、响应模型
- 参数校验（Path / Query / Body）
- 调用 Service 层，返回标准响应

示例：

```python
router = APIRouter(prefix="/log_file", tags=["log_file"])

@router.post("/{kb_id}", response_model=UploadLogFilesResponse)
async def upload_log_files(kb_id: str, request: Request):
    ...
```

#### 3. Service 层 (`services/`)

- 实现业务逻辑
- 编排多个 Manager
- 数据转换与校验

Service 类使用静态方法，保持无状态。

#### 4. Manager 层 (`database/managers/*.py`)

- 直接操作 PostgreSQL
- 封装 CRUD、批量写入、聚合查询
- 将数据库行转换为 Pydantic Model

例如 `LogParseResultPGManager` 使用 `asyncpg COPY` 进行高性能批量写入。

---

## 数据路径二：异步任务处理流程

### task_handler => base_worker => worker => manager

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│ TaskHandler │────▶│  BaseWorker │────▶│   Worker    │────▶│   Manager   │
│(调度器/5s轮询)│     │(反射+状态机)  │     │(业务实现)    │     │(PG 持久化)  │
└─────────────┘     └─────────────┘     └─────────────┘     └─────────────┘
```

### 任务状态流转

```
                         ┌─────────────────────────────────────────┐
                         │                                         │
                         ▼                                         │
PENDING ──[run]──▶ RUNNING ──[success]──▶ SUCCESSFUL_PENDING_REMOVE ──[deinit]──▶ SUCCESSFUL
    │                  │                                                              │
    │                  │ [fail/exception]                                             │
    │                  ▼                                                              │
    │            FAILED_PENDING_REMOVE ──[reinit]──▶ PENDING (retry, retry_times+1)   │
    │                  │                              │                               │
    │                  │ [reinit fail / max retry]    │                               │
    │                  ▼                              │                               │
    │                 FAILED ◀────────────────────────┘                               │
    │                                                                                 │
    └──[stop]──▶ CANCELLED                                                          │
                                                                                      │
[SUCCESSFUL / FAILED / CANCELLED] ──[delete]──▶ (从数据库删除) ◀──────────────────────┘
```

| 状态 | 说明 |
|------|------|
| `PENDING` | 待执行 |
| `RUNNING` | 执行中 |
| `SUCCESSFUL_PENDING_REMOVE` | 成功待清理 |
| `FAILED_PENDING_REMOVE` | 失败待重试 |
| `SUCCESSFUL` | 终态：成功 |
| `FAILED` | 终态：失败 |
| `CANCELLED` | 已取消 |

### 多进程与子进程 PG 初始化

`ProcessHandler` 使用 `multiprocessing.get_context("spawn")` 启动子进程。子进程不会继承父进程的 `PGManager`，因此 `process_handle.py` 的 `subprocess_target` 会在子进程启动时重新初始化 PostgreSQL 连接：

```python
from latency.database.engine import PGManager
PGManager.initialize(
    Config().get_config().db.pg_dsn_url(),
    pool_size=...,
    max_overflow=...,
)
```

### Worker 说明

| Worker | 说明 |
|--------|------|
| `kv_cache_log_parse_worker` | 解析日志，检测异常，生成 `log_parse_result` / `anomalous_event` / 聚合事件 |
| `kv_cache_log_event_diagnosis_worker` | 调用 `witty-ub-diag-tool` 进行故障定界 |
| `store_trace_context_logs_worker` | 根据诊断结果生成 `log_failure_event` / `trace_failure_event` |

---

## PostgreSQL 后端说明

### 关键文件

- `database/engine.py`：`PGManager`（SQLAlchemy 异步引擎 + 会话上下文）
- `database/models.py`：ORM 模型定义
- `database/init.py`：建表、HASH/RANGE 分区、GIN / Partial 索引
- `database/utils.py`：时间戳、IP、`pod_ips`、COPY tuple 转换工具

### 分区与索引

- `log_parse_result` 按 `log_id` 做 32 个 HASH 分区
- `time_window_aggregated` 按 `time_bucket` 做 24 个月 RANGE 分区
- 手动创建 GIN 索引和部分索引以加速常见查询

### Manager 命名

当前实际使用的 Manager 为 `database/managers/*.py`。Service 层已全部切换到这些 Manager。

---

## C++ 故障定界工具说明

### 编译位置

CMake 目标定义在 `src/CMakeLists.txt`：

```cmake
add_executable(witty-ub-diag-tool
    witty_ub_diag_tool_main.cpp
)
target_link_options(witty-ub-diag-tool PRIVATE 
    "-Wl,--whole-archive" 
    "$<TARGET_FILE:diagnosis_tool>"
    "-Wl,--no-whole-archive"
)
target_link_libraries(witty-ub-diag-tool PRIVATE ubse_context diagnosis_tool log4cplus)
```

`diagnosis_tool` 静态库位于 `src/diagnosis_tool/`，包含 kvcache / urma 故障模式实现。

### 运行查找

Python Worker 默认查找：

```python
WITTY_INSTALL_PATH_DEFAULT = "/usr/bin"
```

可通过环境变量覆盖：

```bash
export WITTY_INSTALL_PATH=/custom/path
```


---

## 端到端 API 使用示例

### 1. 创建知识库

```bash
curl -s -X POST http://127.0.0.1:9772/log_kb \
  -H 'Content-Type: application/json' \
  -d '{"name":"my_kb","description":"test kb"}'
```

返回：

```json
{"code":200,"message":"success","result":{"kb_id":"..."}}
```

### 2. 上传本地日志文件

```bash
KB_ID=<kb_id>
curl -s -X POST "http://127.0.0.1:9772/log_file/${KB_ID}" \
  -H 'Content-Type: application/json' \
  -d '{
    "upload_log_file_configs":[{
      "name":"ds_client_access.log",
      "source_type":"local",
      "source":"/path/to/ds_client_access_1234.log"
    }]
  }'
```

返回：

```json
{"code":200,"message":"success","result":{"log_file_ids":["..."]}}
```

### 3. 触发解析任务

```bash
LOG_FILE_ID=<log_file_id>
curl -s -X PUT "http://127.0.0.1:9772/log_file/run/${LOG_FILE_ID}?run=true"
```

返回：

```json
{"code":200,"message":"success","result":{"task_id":"..."}}
```

上传日志时系统会自动创建 `kv_cache_log_event_diagnosis_worker` 和 `store_trace_context_logs_worker` 任务。

### 4. 查看任务状态

```bash
curl -s -X POST http://127.0.0.1:9772/task/list \
  -H 'Content-Type: application/json' \
  -d "{\"kb_id\":\"${KB_ID}\",\"page_num\":1,\"page_cnt\":10}"
```

### 5. 查询解析结果

```bash
curl -s -X POST http://127.0.0.1:9772/log_parse_result/list \
  -H 'Content-Type: application/json' \
  -d "{\"kb_id\":\"${KB_ID}\",\"log_id\":\"${LOG_FILE_ID}\",\"page_num\":1,\"page_cnt\":10}"
```

### 6. 查询异常事件

```bash
curl -s -X POST http://127.0.0.1:9772/anomalous_event/list \
  -H 'Content-Type: application/json' \
  -d "{\"kb_id\":\"${KB_ID}\",\"log_id\":\"${LOG_FILE_ID}\",\"page_num\":1,\"page_cnt\":10}"
```

### 7. 查询聚合事件

```bash
curl -s -X POST http://127.0.0.1:9772/aggregated_event/list \
  -H 'Content-Type: application/json' \
  -d "{\"kb_id\":\"${KB_ID}\",\"log_id\":\"${LOG_FILE_ID}\",\"page_num\":1,\"page_cnt\":10}"

curl -s -X POST http://127.0.0.1:9772/aggregated_event/list_time_window \
  -H 'Content-Type: application/json' \
  -d "{\"kb_id\":\"${KB_ID}\",\"log_id\":\"${LOG_FILE_ID}\",\"page_num\":1,\"page_cnt\":10}"
```

### 8. 查询故障事件

```bash
curl -s -X POST http://127.0.0.1:9772/log_failure_event_result/list_log_events \
  -H 'Content-Type: application/json' \
  -d "{\"kb_id\":\"${KB_ID}\",\"log_id\":\"${LOG_FILE_ID}\",\"page_num\":1,\"page_cnt\":10}"

curl -s -X POST http://127.0.0.1:9772/log_failure_event_result/list_trace_events \
  -H 'Content-Type: application/json' \
  -d "{\"kb_id\":\"${KB_ID}\",\"log_id\":\"${LOG_FILE_ID}\",\"page_num\":1,\"page_cnt\":10}"
```

### 9. 查询诊断案例

```bash
curl -s -X POST http://127.0.0.1:9772/diagnosis_case/search \
  -H 'Content-Type: application/json' \
  -d "{\"kb_id\":\"${KB_ID}\",\"page_num\":1,\"page_cnt\":10}"
```

### 10. 查询故障模式 / 状态码知识

```bash
# 状态码知识
curl -s http://127.0.0.1:9772/failure_mode/status_code/2410

# 故障模式详情
curl -s http://127.0.0.1:9772/failure_mode/<failure_mode_id>
```

---

## 数据库表说明

| 表名 | 说明 |
|------|------|
| `log_knowledge` | 知识库 |
| `log_file` | 日志文件元数据 |
| `log_parse_result` | 日志解析结果（按 log_id HASH 分区） |
| `src_dst_aggregated_event` | 源-目的 IP 聚合事件 |
| `time_window_aggregated` | 时间窗口聚合事件（RANGE 分区） |
| `anomalous_event` | 异常事件 |
| `anomalous_event_chain` | 异常事件链 |
| `task` | 异步任务 |
| `task_report` | 任务进度报告 |
| `diagnosis_config` | 诊断运行时配置 |
| `log_failure_event` | 单条日志故障事件 |
| `trace_failure_event` | Trace 级故障事件 |
| `failure_mode_knowledge` | 故障模式知识库 |
| `status_code_knowledge` | 状态码知识库 |
| `diagnosis_case` | 诊断案例 |
| `diagnosis_case_signal` | 诊断案例信号 |

---

## 测试

推荐运行当前维护中的测试：

```bash
cd /path/to/witty-ub/src/plugins/latency
source .venv/bin/activate
export PYTHONPATH=/path/to/witty-ub/src/plugins:$PYTHONPATH

pytest test/ -q
```

> `pytest.ini` 已忽略旧 SQLite 脚本测试和部分手动测试文件。

---

## 开发新 Worker 的步骤

1. 在 `ENUM/task.py` 的 `TaskTypeEnum` 中新增任务类型
2. 在 `task/worker/` 下创建新的 Worker 文件，继承 `BaseWorker` 概念（设置 `name` 属性）
3. 实现 `init` / `run` / `stop` / `delete` / `reinit` / `deinit` 静态方法
4. 在 `task/worker/__init__.py` 或 `access/fastapi_server.py` 中确保模块被导入，使 `BaseWorker.__subclasses__()` 能反射到
5. 通过 `/task/create` 或 Service 层调用 `TaskHandler.init_task(...)` 创建任务

Worker `run` 方法在独立子进程中执行，需自行处理异常并正确设置任务状态：

```python
await TaskPGManager.update_task(task_id, {"status": TaskStatusEnum.SUCCESSFUL_PENDING_REMOVE.value})
```

---

## 常见问题

### 1. 启动时提示 `PGManager not initialized`

- 检查 `diagnosis_config.toml`（或 `CONFIG` 环境变量指向的 TOML 文件）中 `db` 配置是否正确
- 检查 PG 是否能连通
- 对于 Worker 子进程，`process_handle.py` 已自动初始化；若自定义子进程入口，需手动调用 `PGManager.initialize`

### 2. 诊断任务失败：`No such file or directory: '/usr/bin/witty-ub-diag-tool'`

- 未安装或编译 C++ 故障定界工具
- 或 `WITTY_INSTALL_PATH` 环境变量未指向正确目录

### 3. `witty-ub-diag-tool` 运行时报找不到数据文件

- 确保 `/var/witty-ub/data` 和 `/var/witty-ub/config` 已按上文复制
- 可通过环境变量 `WITTY_DIR` 修改数据根目录

### 4. 任务一直在 `FAILED_PENDING_REMOVE` 并重试

- 查看服务日志定位 Worker 异常
- 超过 `task.task_retry_times` 后会进入终态 `FAILED`

---

## 许可证

本项目采用 Mulan PSL v2 许可证，详见项目根目录 `LICENSE`。
