# Latency 插件开发指南

## 项目概述

本插件是一个基于 FastAPI 的日志解析与异常检测服务，采用分层架构设计，支持异步任务队列和多进程任务执行。

## 目录结构

```
latency/
├── access/                 # 入口层 (App)
│   ├── fastapi_server.py   # FastAPI 应用主入口
│   ├── mcp_server.py       # MCP 服务器入口
│   └── shell_server.py     # Shell 命令行入口
├── routers/                # 路由层 (Router)
│   ├── anomalous_event_chain.py
│   ├── anomalous_event.py
│   ├── log_file.py
│   ├── log_knowledge.py
│   ├── log_parse_result.py
│   ├── src_dst_aggregated_event.py
│   └── task.py
├── services/               # 服务层 (Service)
│   ├── anomalous_event_chain.py
│   ├── anomalous_event.py
│   ├── log_file.py
│   ├── log_knowledge.py
│   ├── log_parse_result.py
│   ├── src_dst_aggregated_event.py
│   └── task.py
├── database/               # 数据层
│   ├── engine.py           # SQLite 数据库引擎（单例模式）
│   └── managers/           # 数据管理器（Manager）
│       ├── anomalous_event_chain.py
│       ├── anomalous_event.py
│       ├── log_file.py
│       ├── log_knowledge.py
│       ├── log_parse_result.py
│       ├── src_dst_aggregated_event.py
│       ├── task.py
│       └── task_report.py
├── task/                   # 任务处理层
│   ├── task_handler.py     # 任务调度器（TaskHandler）
│   ├── process_handle.py   # 进程处理器（多进程管理）
│   └── worker/
│       ├── base.py         # 基础工作器（BaseWorker）
│       └── kv_cache_log_parse_worker.py  # 具体业务 Worker
├── parse/                  # 日志解析器
│   ├── base_parser.py
│   ├── remote_pull_log_parser.py
│   ├── worker_access_log_parser.py
│   ├── query_meta_log_parser.py
│   ├── sdk_access_log_parser.py
│   ├── link_log_parser.py
│   ├── urma_log_parser.py
│   └── correlation/        # 关联分析
│       ├── correlator.py
│       └── result_builder.py
├── schemas/                # 数据模型（Pydantic）
│   ├── config.py           # 配置模型
│   ├── ds_log.py           # DS 日志模型
│   ├── log.py              # 日志相关模型
│   ├── request.py          # 请求模型
│   ├── response.py         # 响应模型
│   └── task.py             # 任务模型
├── ENUM/                   # 枚举定义
│   ├── ds_log.py           # DS 日志枚举
│   ├── general.py          # 通用枚举
│   ├── model.py            # 模型枚举
│   └── task.py             # 任务相关枚举
├── config/                 # 配置模块
│   └── config.py           # 配置读取类
├── common/                 # 公共工具
│   ├── __init__.py
│   ├── convertor.py        # 数据转换器
│   ├── ds_log_io.py        # DS 日志 IO
│   ├── stats.py            # 统计工具
│   └── zip_handler.py      # ZIP 文件处理
├── models/                 # AI 模型封装
│   ├── chat.py             # 聊天模型
│   ├── embedding.py        # 嵌入模型
│   ├── function.py         # 函数调用模型
│   ├── ocr.py              # OCR 模型
│   └── reranker.py         # 重排序模型
├── regex/                  # 正则解析规则
│   ├── kvcache_log.py
│   └── kvcache_log_file.py
├── sdk/                    # SDK
│   └── xxx.py
├── static/                 # 静态资源
│   ├── config.toml         # TOML 配置文件
│   └── fault_patterns_tree.json
├── deploy/                 # 部署文件
│   ├── deploy.sh           # 一键部署脚本
│   ├── skill_build.sh      # Skill 构建脚本
│   ├── pyproject.toml
│   ├── requirements.txt
│   ├── log_detection.spec  # PyInstaller 打包配置
│   ├── Dockerfile          # Docker 镜像构建
│   └── Dockerfile-base     # 基础 Docker 镜像
├── test/                   # 测试
│   ├── test_all_apis.py    # 全接口测试
│   ├── test_log_parser.py
│   ├── test_full_link.py   # 全链路测试
│   ├── test_kv_cache_log_parse_worker.py
│   ├── test_scheduler_run.py
│   ├── test_task_service.py
│   └── test.py
├── ds_log_analyzer.py      # DS 日志分析器主入口
├── LICENSE                 # 许可证文件
└── README.en.md            # 英文文档
```

---

## 部署指南

### 环境要求

- Python >= 3.10
- [uv](https://github.com/astral-sh/uv)（推荐）或 pip
- unrar（可选，用于解压 .rar 文件）
  - Ubuntu/Debian: `sudo apt-get install unrar`
  - CentOS/RHEL: `sudo yum install unrar`
  - macOS: `brew install unrar`

### 一键部署

```bash
cd /path/to/latency/deploy
bash deploy.sh
```

脚本将自动完成：
1. 检查 `uv` 是否安装
2. 创建虚拟环境（`.venv`）
3. 基于**阿里源**安装依赖
4. 创建必要的目录
5. 启动 FastAPI 服务（`http://127.0.0.1:9772`）

### 手动部署

#### 1. 创建虚拟环境并安装依赖

```bash
cd /path/to/witty-ub/src/plugins/latency

# 使用 uv（推荐）
uv venv .venv --python python3.10
uv pip install --python .venv/bin/python \
    --index-url https://mirrors.aliyun.com/pypi/simple/ \
    -r deploy/requirements.txt

# 或使用 pip
python3 -m venv .venv
source .venv/bin/activate
pip install -r deploy/requirements.txt
```

#### 2. 启动服务

```bash
export PYTHONPATH=/path/to/witty-ub/src/plugins:$PYTHONPATH
python latency/access/fastapi_server.py
```

服务默认监听 `0.0.0.0:9772`，可通过 `http://127.0.0.1:9772/health_check` 检查健康状态。

#### 3. 启动只读 MCP 服务

先启动 FastAPI 服务，再为 Agent 启动 MCP 服务：

```bash
export PYTHONPATH=/path/to/witty-ub/src/plugins:$PYTHONPATH
export LATENCY_API_BASE_URL=http://127.0.0.1:9772
python -m latency.access.mcp_server
```

MCP 默认使用 `stdio` 传输。可用环境变量调整：

| 环境变量 | 默认值 | 说明 |
|----------|--------|------|
| `LATENCY_API_BASE_URL` | `http://127.0.0.1:9772` | Latency FastAPI 地址 |
| `LATENCY_API_TIMEOUT_SECONDS` | `30` | 单次 API 请求超时 |
| `LATENCY_MCP_TRANSPORT` | `stdio` | `stdio`、`sse` 或 `streamable-http` |

该 MCP 服务只开放日志状态、时延、通断故障和故障知识查询工具，不开放上传、修改、删除或停止任务操作。

OpenCode 会读取仓库根目录的 `opencode.json` 并按需启动 MCP 服务。确认 FastAPI 已启动后，可检查连接状态：

```bash
cd /path/to/witty-ub
opencode mcp list
```

仓库同时提供了 `witty-ub-diagnostician` OpenCode 主 Agent。启动 OpenCode 后，
使用 `Tab` 切换到该 Agent，即可用自然语言发起时延或通断故障调查。该 Agent
只能调用 `witty_ub_diag_mcp` 下的只读工具，不能执行命令或修改文件。

也可以先确认 Agent 已被识别：

```bash
opencode agent list
```

### 依赖版本说明

当前经过测试的依赖版本如下：

| 包名 | 版本 |
|------|------|
| fastapi | 0.110.2 |
| uvicorn | 0.21.0 |
| apscheduler | 3.10.4 |
| pydantic | 2.12.3 |
| aiohttp | 3.9.5 |
| aiofiles | 25.1.0 |
| chardet | 4.0.0 |
| requests | 2.32.2 |
| toml | 0.10.2 |
| httpx | 0.27.0 |
| mcp | >=1.28.0,<2.0.0 |

---

## 数据路径一：HTTP 请求处理流程

### app => router => service => manager

此路径处理外部 HTTP 请求，采用经典的分层架构：

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│     App     │────▶│   Router    │────▶│   Service   │────▶│   Manager   │
│(FastAPI app)│     │(APIRouter)  │     │(Biz Logic)  │     │(DB Access)  │
└─────────────┘     └─────────────┘     └─────────────┘     └─────────────┘
     │                    │                    │                    │
     ▼                    ▼                    ▼                    ▼
 fastapi_server.py    log_file.py         log_file.py         task.py
                                           (示例)              (示例)
```

### 各层职责与开发规范

#### 1. App 层 (`access/fastapi_server.py`)

**职责**：
- 创建 FastAPI 应用实例
- 注册 Router
- 启动时初始化数据库和目录
- 配置 APScheduler 定时任务调度器（每 5 秒执行一次 `TaskHandler.handle_tasks`）

**关键代码**：
```python
app = fastapi.FastAPI(docs_url=None, redoc_url=None)

async def configure():
    app.include_router(log_file.router)  # 注册路由

@app.on_event("startup")
async def startup_event():
    await configure()
    await mk_dirs()
    await AsyncSQLiteSingleton().init_database()
    scheduler.add_job(TaskHandler.handle_tasks, "interval", seconds=5)
    scheduler.start()
```

**开发新增接口时的步骤**：
1. 在 `access/fastapi_server.py` 的 `configure()` 函数中 `include_router` 注册新路由

#### 2. Router 层 (`routers/`)

**职责**：
- 定义 HTTP API 端点（路径、方法、参数、响应模型）
- 参数校验（Path/Query/Body）
- 调用 Service 层处理业务
- 返回标准化响应

**示例** (`routers/log_file.py`)：
```python
from fastapi import APIRouter
from latency.schemas.response import UploadLogFilesResponse
from latency.services.log_file import LogFileService

router = APIRouter(prefix="/log_file", tags=["log_file"])

@router.post("/{kb_id}", response_model=UploadLogFilesResponse)
async def upload_log_files(kb_id: str) -> UploadLogFilesResponse:
    upload_log_files_msg = await LogFileService.upload_log_files(kb_id)
    return UploadLogFilesResponse(result=upload_log_files_msg)
```

**开发规范**：
- 使用 `APIRouter` 组织路由，统一设置 `prefix` 和 `tags`
- 使用 `Annotated` 进行参数描述和校验
- 调用对应的 Service 类静态方法
- 返回 `ResponseBase` 子类包装的标准响应

#### 3. Service 层 (`services/`)

**职责**：
- 实现业务逻辑
- 协调多个 Manager 完成复杂操作
- 数据转换和校验

**示例** (`services/log_file.py`)：
```python
class LogFileService:
    @staticmethod
    async def upload_log_files(kb_id: str) -> UploadLogFilesMsg:
        # 1. 参数校验/预处理
        # 2. 调用 Manager 进行数据操作
        # 3. 执行业务逻辑
        # 4. 返回结果
        return UploadLogFilesMsg(log_files_ids=[])
```

**开发规范**：
- Service 类使用静态方法（`@staticmethod`），保持无状态
- 复杂业务在此层编排，避免在 Router 或 Manager 中写业务逻辑

#### 4. Manager 层 (`database/managers/`)

**职责**：
- 直接操作数据库（SQLite）
- 封装 CRUD 操作
- 将数据库行转换为 Pydantic Model

**示例** (`database/managers/task.py`)：
```python
class TaskManager:
    @staticmethod
    async def get_task_by_task_id(task_id: str) -> TaskModel | None:
        sql_str = "SELECT ... FROM task_table WHERE id = :task_id"
        results = await AsyncSQLiteSingleton().execute_query(sql_str, {"task_id": task_id})
        if results:
            return TaskModel(**results[0])
        return None

    @staticmethod
    async def add_task(task: TaskModel) -> bool:
        sql_str = "INSERT INTO task_table (...) VALUES (...)"
        return await AsyncSQLiteSingleton().execute_modify(sql_str, task.model_dump())
```

**开发规范**：
- Manager 类使用静态方法，保持无状态
- 所有 SQL 操作通过 `AsyncSQLiteSingleton` 单例执行
- 查询结果转换为 Pydantic Model 返回
- 新增表需要在 `database/engine.py` 的 `table_ddl_list` 中定义 DDL

---

## 数据路径二：异步任务处理流程

### task_handler => base_worker => manager

此路径处理后台异步任务，采用生产者-消费者模式 + 多进程执行：

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│ TaskHandler │────▶│  BaseWorker │────▶│   Worker    │────▶│   Manager   │
│(调度器/5s轮询)│     │(反射+状态机)  │     │(业务实现)    │     │(数据持久化)  │
└─────────────┘     └─────────────┘     └─────────────┘     └─────────────┘
     │                    │                    │                    │
     ▼                    ▼                    ▼                    ▼
task_handler.py      worker/base.py    kv_cache_log_parse_worker.py  task.py
                                             (示例)                 (示例)
```

### 各层职责与开发规范

#### 1. TaskHandler 层 (`task/task_handler.py`)

**职责**：
- 由 APScheduler 每 5 秒定时调度执行
- 轮询数据库中的任务状态
- 管理任务生命周期：初始化、执行、停止、删除
- 处理成功/失败/待执行三种状态的任务队列

**核心方法**：
```python
class TaskHandler:
    @staticmethod
    async def handle_tasks():
        """主调度入口，每 5 秒执行一次"""
        await TaskHandler.handle_successed_tasks()   # 清理成功任务
        await TaskHandler.handle_failed_tasks()      # 重试失败任务
        await TaskHandler.handle_pending_tasks()     # 执行待处理任务

    @staticmethod
    async def init_task(task_type: TaskTypeEnum, op_id: str) -> str:
        """初始化新任务，返回 task_id"""
        task_id = await BaseWorker.init(task_type, op_id)
        return task_id

    @staticmethod
    async def stop_task(task_id: str) -> str:
        """停止指定任务"""
        return await BaseWorker.stop(task_id)
```

**任务状态流转**：

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

**状态说明**：

| 状态 | 说明 |
|------|------|
| `PENDING` | 待执行，等待 TaskHandler 调度 |
| `RUNNING` | 正在执行，Worker 子进程已启动 |
| `SUCCESSFUL_PENDING_REMOVE` | 执行成功，等待 `deinit` 清理后转为 `SUCCESSFUL` |
| `FAILED_PENDING_REMOVE` | 执行失败，等待 `reinit` 重试或转为 `FAILED` |
| `SUCCESSFUL` | 最终成功状态 |
| `FAILED` | 最终失败状态（超过最大重试次数） |
| `CANCELLED` | 已被手动停止/取消 |

**调度顺序**（TaskHandler.handle_tasks 每 5 秒执行一次）：
1. `handle_successed_tasks`：将 `SUCCESSFUL_PENDING_REMOVE` → `SUCCESSFUL`
2. `handle_failed_tasks`：将 `FAILED_PENDING_REMOVE` 通过 `reinit` → `PENDING`（重试）或 `FAILED`（终态）
3. `handle_pending_tasks`：将 `PENDING` → `RUNNING`

**服务重启恢复**：启动时会自动将 `RUNNING` 状态的任务恢复为 `PENDING`，防止服务异常重启后任务卡住。

#### 2. BaseWorker 层 (`task/worker/base.py`)

**职责**：
- 通过**反射**查找具体的 Worker 子类（根据 `TaskTypeEnum`）
- 管理任务状态转换
- 通过 `ProcessHandler` 启动多进程执行实际任务
- 统一封装 `init` / `run` / `stop` / `delete` / `reinit` / `deinit` 接口

**反射机制**：
```python
class BaseWorker:
    @staticmethod
    def find_worker_class(worker_name: TaskTypeEnum):
        """自动查找 BaseWorker 的所有子类，匹配 name 属性"""
        subclasses = BaseWorker.__subclasses__()
        for subclass in subclasses:
            if subclass.name == worker_name:
                return subclass
        return None
```

**核心方法**：
```python
class BaseWorker:
    @staticmethod
    async def init(worker_name: TaskTypeEnum, op_id: str) -> str:
        """初始化任务：调用具体 Worker.init()，状态设为 PENDING"""
        task_id = await BaseWorker.find_worker_class(worker_name).init(op_id)
        await TaskManager.update_task(task_id, {"status": TaskStatusEnum.PENDING.value})
        return task_id

    @staticmethod
    async def run(task_id: str) -> bool:
        """运行任务：通过 ProcessHandler 启动子进程，状态设为 RUNNING"""
        worker_name = await BaseWorker.get_worker_name(task_id)
        flag = ProcessHandler.add_task(task_id, BaseWorker.find_worker_class(worker_name).run, task_id)
        await TaskManager.update_task(task_id, {"status": TaskStatusEnum.RUNNING.value})
        return flag

    @staticmethod
    async def report(task_id: str, message: str, status: TaskStatusEnum, progress: float) -> bool:
        """添加任务进度报告。注意：status 参数为保留位，当前未写入报告"""
        task_report = TaskReportModel(task_id=task_id, message=message, progress=progress)
        return await TaskReportManager.add_task_report(task_report)
```

**多进程执行** (`task/process_handle.py`)：
- `ProcessHandler` 维护进程字典 `tasks`，最大进程数由 `cpu_limit` 配置决定
- `add_task()` 创建新进程执行 Worker 的 `run` 方法
- `remove_task()` 终止并清理进程

#### 3. Worker 层 (`task/worker/*.py`)

**职责**：
- 继承 `BaseWorker` 的概念（通过 `name` 属性关联）
- 实现具体的业务逻辑

**开发新 Worker 的步骤**：
1. 在 `ENUM/task.py` 的 `TaskTypeEnum` 中新增任务类型：
   ```python
   class TaskTypeEnum(StrEnum):
       KV_CACHE_LOG_PARSE_WORKER = "kv_cache_log_parse_worker"
       MY_NEW_WORKER = "my_new_worker"  # 新增
   ```

2. 在 `task/worker/` 下创建新的 Worker 文件：
   ```python
   from latency.ENUM.task import TaskStatusEnum, TaskTypeEnum
   from latency.task.worker.base import BaseWorker
   from latency.database.managers.task import TaskManager
   from latency.schemas.task import TaskModel
   import uuid

   class MyNewWorker:
       name = TaskTypeEnum.MY_NEW_WORKER  # 必须设置 name，用于 BaseWorker 反射查找

       @staticmethod
       async def init(op_id: str) -> str | None:
           """初始化任务，创建数据库记录，返回 task_id；若 op_id 无效可返回 None"""
           task_id = str(uuid.uuid4())
           task = TaskModel(
               id=task_id,
               kb_id="",          # 若有关联知识库可填入 kb_id
               task_name="my_new_task",
               task_type=TaskTypeEnum.MY_NEW_WORKER,
               status=TaskStatusEnum.PENDING,
               op_id=op_id,
           )
           await TaskManager.add_task(task)
           return task_id

       @staticmethod
       async def run(task_id: str) -> bool:
           """实际执行业务逻辑（在子进程中运行）"""
           try:
               # 1. 获取任务信息
               task = await TaskManager.get_task_by_task_id(task_id)
               # 2. 执行业务逻辑...
               # 3. 上报进度（status 为保留位，当前未实际写入）
               await BaseWorker.report(task_id, "处理中...", TaskStatusEnum.RUNNING, 50.0)
               # 4. 完成
               await TaskManager.update_task(
                   task_id, {"status": TaskStatusEnum.SUCCESSFUL_PENDING_REMOVE.value}
               )
               await BaseWorker.report(task_id, "完成", TaskStatusEnum.RUNNING, 100.0)
               return True
           except Exception as e:
               await TaskManager.update_task(
                   task_id, {"status": TaskStatusEnum.FAILED_PENDING_REMOVE.value}
               )
               await BaseWorker.report(task_id, f"失败: {e}", TaskStatusEnum.RUNNING, 0.0)
               return False

       @staticmethod
       async def stop(task_id: str) -> str | None:
           """停止任务时的清理逻辑，返回 task_id 或 None"""
           return task_id

       @staticmethod
       async def delete(task_id: str) -> str:
           """删除任务时的清理逻辑，返回 task_id"""
           return task_id

       @staticmethod
       async def reinit(task_id: str) -> bool:
           """重试任务前的重置逻辑，返回是否允许重试"""
           return True

       @staticmethod
       async def deinit(task_id: str) -> str:
           """任务成功后的清理逻辑，返回 task_id"""
           return task_id
   ```

3. Worker 生命周期方法说明：

| 方法 | 调用时机 | 输入 | 输出 | 说明 |
|------|---------|------|------|------|
| `init` | 外部创建任务时 | `op_id: str` | `str \| None` | 初始化任务数据，插入数据库；失败返回 `None` |
| `run` | TaskHandler 调度执行时 | `task_id: str` | `bool` | 实际业务逻辑，在独立子进程中运行；成功返回 `True` |
| `stop` | 外部调用停止任务时 | `task_id: str` | `str \| None` | 清理运行中的资源；返回 `task_id` 或 `None` |
| `delete` | 外部调用删除任务时 | `task_id: str` | `str` | 彻底删除任务相关数据；返回 `task_id` |
| `reinit` | 失败任务重试时 | `task_id: str` | `bool` | 重置任务状态，准备重新执行；返回是否允许重试 |
| `deinit` | 任务成功完成后 | `task_id: str` | `str` | 最终清理，返回 `task_id` |

#### 4. Manager 层（在任务路径中的角色）

在任务处理路径中，Manager 层被 **BaseWorker** 和 **具体 Worker** 间接调用，用于：
- `TaskManager`：查询/更新任务状态、创建/删除任务记录
- `TaskReportManager`：记录任务执行进度和日志
- 其他 Manager：持久化业务数据（如解析结果、异常事件等）

---

## 快速开发示例

### 示例：新增一个 "日志分析任务" 接口和对应的 Worker

#### Step 1: 新增 API 入口（Router）

`routers/analysis.py`:
```python
from fastapi import APIRouter
from latency.schemas.response import ResponseBase
from latency.services.analysis import AnalysisService

router = APIRouter(prefix="/analysis", tags=["analysis"])

@router.post("/{kb_id}/start", response_model=ResponseBase)
async def start_analysis(kb_id: str) -> ResponseBase:
    task_id = await AnalysisService.start_analysis(kb_id)
    return ResponseBase(result={"task_id": task_id})
```

#### Step 2: 注册路由（App）

`access/fastapi_server.py`:
```python
from latency.routers import analysis

async def configure():
    app.include_router(log_file.router)
    app.include_router(analysis.router)  # 新增
```

#### Step 3: 业务逻辑（Service）

`services/analysis.py`:
```python
from latency.task.task_handler import TaskHandler
from latency.ENUM.task import TaskTypeEnum

class AnalysisService:
    @staticmethod
    async def start_analysis(kb_id: str) -> str:
        # 初始化一个异步任务
        task_id = await TaskHandler.init_task(TaskTypeEnum.LOG_ANALYSIS_WORKER, kb_id)
        return task_id
```

#### Step 4: 任务类型定义（ENUM）

`ENUM/task.py`:
```python
class TaskTypeEnum(StrEnum):
    KV_CACHE_LOG_PARSE_WORKER = "kv_cache_log_parse_worker"
    LOG_ANALYSIS_WORKER = "log_analysis_worker"  # 新增
```

#### Step 5: 实际任务执行（Worker）

`task/worker/log_analysis_worker.py`:
```python
from latency.ENUM.task import TaskStatusEnum, TaskTypeEnum
from latency.task.worker.base import BaseWorker
from latency.database.managers.task import TaskManager
from latency.schemas.task import TaskModel
import uuid

class LogAnalysisWorker:
    name = TaskTypeEnum.LOG_ANALYSIS_WORKER

    @staticmethod
    async def init(op_id: str) -> str | None:
        task_id = str(uuid.uuid4())
        task = TaskModel(
            id=task_id,
            task_name="日志分析任务",
            task_type=TaskTypeEnum.LOG_ANALYSIS_WORKER,
            status=TaskStatusEnum.PENDING,
            op_id=op_id,
        )
        await TaskManager.add_task(task)
        return task_id

    @staticmethod
    async def run(task_id: str) -> bool:
        # 实际业务逻辑在子进程中执行
        await BaseWorker.report(task_id, "开始分析", TaskStatusEnum.RUNNING, 0.0)
        # ... 执行分析逻辑 ...
        await TaskManager.update_task(
            task_id, {"status": TaskStatusEnum.SUCCESSFUL_PENDING_REMOVE.value}
        )
        await BaseWorker.report(task_id, "分析完成", TaskStatusEnum.RUNNING, 100.0)
        return True

    @staticmethod
    async def stop(task_id: str) -> str | None:
        return task_id

    @staticmethod
    async def delete(task_id: str) -> str:
        return task_id

    @staticmethod
    async def reinit(task_id: str) -> bool:
        return True

    @staticmethod
    async def deinit(task_id: str) -> str:
        return task_id
```

---

## 数据库说明

- 使用 **SQLite** 作为嵌入式数据库
- `AsyncSQLiteSingleton` 提供单例模式的数据库连接
- 支持 WAL 模式，提高并发性能
- 所有数据库操作通过异步接口封装（底层在线程池中执行）

**新增表步骤**：
1. 在 `database/engine.py` 的 `table_ddl_list` 中定义 `CREATE TABLE` DDL
2. 在 `schemas/` 下新增对应的 Pydantic Model
3. 在 `database/managers/` 下新增对应的 Manager 类
