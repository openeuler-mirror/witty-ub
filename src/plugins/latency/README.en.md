# Latency Plugin Development Guide

## Project Overview

This plugin is a FastAPI-based log parsing and anomaly detection service, designed with a layered architecture, supporting asynchronous task queues and multi-process task execution.

## Directory Structure

```
latency/
├── access/                 # Entry Layer (App)
│   ├── fastapi_server.py   # FastAPI application main entry
│   ├── mcp_server.py       # MCP server entry
│   └── shell_server.py     # Shell command-line entry
├── routers/                # Router Layer
│   ├── anomalous_event_chain.py
│   ├── anomalous_event.py
│   ├── log_file.py
│   ├── log_knowledge.py
│   ├── log_parse_result.py
│   └── src_dst_aggregated_event.py
├── services/               # Service Layer
│   ├── anomalous_event_chain.py
│   ├── anomalous_event.py
│   ├── log_file.py
│   ├── log_knowledge.py
│   ├── log_parse_result.py
│   └── src_dst_aggregated_event.py
├── database/               # Data Layer
│   ├── engine.py           # SQLite database engine (singleton)
│   └── managers/           # Data managers
│       ├── anomalous_event_chain.py
│       ├── anomalout_event.py
│       ├── log_file.py
│       ├── log_knowledge.py
│       ├── log_parse_result.py
│       ├── src_dst_aggregated_event.py
│       ├── task.py
│       └── task_report.py
├── task/                   # Task Processing Layer
│   ├── task_handler.py     # Task scheduler (TaskHandler)
│   ├── process_handle.py   # Multi-process manager
│   ├── parse/              # Log parsers
│   │   ├── base_parser.py
│   │   ├── remote_pull_log_parser.py
│   │   ├── worker_access_log_parser.py
│   │   ├── query_meta_log_parser.py
│   │   ├── sdk_access_log_parser.py
│   │   ├── urma_log_parser.py
│   │   └── correlation/    # Correlation analysis
│   │       ├── correlator.py
│   │       └── result_builder.py
│   └── worker/
│       ├── base.py         # Base worker (BaseWorker)
│       └── kv_cache_log_parse_worker.py  # Business worker
├── schemas/                # Pydantic Models
│   ├── config.py
│   ├── ds_log.py
│   ├── log.py
│   ├── request.py
│   ├── response.py
│   └── task.py
├── ENUM/                   # Enumerations
│   ├── ds_log.py
│   ├── general.py
│   ├── model.py
│   └── task.py
├── config/                 # Configuration module
│   └── config.py
├── common/                 # Common utilities
│   ├── convertor.py
│   ├── ds_log_io.py
│   └── zip_handler.py
├── models/                 # AI model wrappers
│   ├── chat.py
│   ├── embedding.py
│   ├── function.py
│   ├── ocr.py
│   └── reranker.py
├── regex/                  # Regex parsing rules
│   └── kvcache_log.py
├── sdk/                    # SDK
│   └── xxx.py
├── static/                 # Static resources
│   ├── config.toml
│   └── fault_patterns_tree.json
├── deploy/                 # Deployment files
│   ├── deploy.sh           # One-click deployment script
│   ├── pyproject.toml
│   └── requirements.txt
└── test/                   # Tests
    ├── test_all_apis.py    # Full API test
    ├── test_log_parser.py
    └── test.py
```

---

## Deployment Guide

### Requirements

- Python >= 3.10
- [uv](https://github.com/astral-sh/uv) (recommended) or pip

### One-Click Deployment

```bash
cd /path/to/latency/deploy
bash deploy.sh
```

The script will automatically:
1. Check if `uv` is installed
2. Create a virtual environment (`.venv`)
3. Install dependencies via **Aliyun mirror**
4. Create necessary directories
5. Start the FastAPI service (`http://127.0.0.1:9772`)

### Manual Deployment

#### 1. Create virtual environment and install dependencies

```bash
cd /path/to/witty-ub/src/plugins/latency

# Using uv (recommended)
uv venv .venv --python python3.10
uv pip install --python .venv/bin/python \
    --index-url https://mirrors.aliyun.com/pypi/simple/ \
    -r deploy/requirements.txt

# Or using pip
python3 -m venv .venv
source .venv/bin/activate
pip install -r deploy/requirements.txt
```

#### 2. Start the service

```bash
export PYTHONPATH=/path/to/witty-ub/src/plugins:$PYTHONPATH
python latency/access/fastapi_server.py
```

The service listens on `0.0.0.0:9772` by default. You can check the health status via `http://127.0.0.1:9772/health_check`.

### Dependency Versions

The following versions have been tested:

| Package | Version |
|---------|---------|
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

---

## Data Path 1: HTTP Request Processing

### app => router => service => manager

This path handles external HTTP requests using a classic layered architecture:

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│     App     │────▶│   Router    │────▶│   Service   │────▶│   Manager   │
│(FastAPI app)│     │(APIRouter)  │     │(Biz Logic)  │     │(DB Access)  │
└─────────────┘     └─────────────┘     └─────────────┘     └─────────────┘
     │                    │                    │                    │
     ▼                    ▼                    ▼                    ▼
 fastapi_server.py    log_file.py         log_file.py         task.py
                                           (example)           (example)
```

### Responsibilities and Development Standards

#### 1. App Layer (`access/fastapi_server.py`)

**Responsibilities**:
- Create FastAPI application instance
- Register routers
- Initialize database and directories on startup
- Configure APScheduler (executes `TaskHandler.handle_tasks` every 5 seconds)

**Key code**:
```python
app = fastapi.FastAPI(docs_url=None, redoc_url=None)

async def configure():
    app.include_router(log_file.router)

@app.on_event("startup")
async def startup_event():
    await configure()
    await mk_dirs()
    await AsyncSQLiteSingleton().init_database()
    scheduler.add_job(TaskHandler.handle_tasks, "interval", seconds=5)
    scheduler.start()
```

**Steps to add a new API**:
1. Register the new router in `configure()` in `access/fastapi_server.py`

#### 2. Router Layer (`routers/`)

**Responsibilities**:
- Define HTTP API endpoints (path, method, parameters, response model)
- Parameter validation (Path/Query/Body)
- Call Service layer for business logic
- Return standardized responses

**Example** (`routers/log_file.py`):
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

**Development standards**:
- Use `APIRouter` with unified `prefix` and `tags`
- Use `Annotated` for parameter description and validation
- Call corresponding Service static methods
- Return responses wrapped in `ResponseBase` subclasses

#### 3. Service Layer (`services/`)

**Responsibilities**:
- Implement business logic
- Coordinate multiple Managers for complex operations
- Data transformation and validation

**Example** (`services/log_file.py`):
```python
class LogFileService:
    @staticmethod
    async def upload_log_files(kb_id: str) -> UploadLogFilesMsg:
        # 1. Parameter validation/preprocessing
        # 2. Call Manager for data operations
        # 3. Execute business logic
        # 4. Return result
        return UploadLogFilesMsg(log_files_ids=[])
```

**Development standards**:
- Service classes use static methods (`@staticmethod`) to remain stateless
- Orchestrate complex business here; avoid putting business logic in Router or Manager

#### 4. Manager Layer (`database/managers/`)

**Responsibilities**:
- Direct database operations (SQLite)
- Encapsulate CRUD operations
- Convert database rows to Pydantic Models

**Example** (`database/managers/task.py`):
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

**Development standards**:
- Manager classes use static methods to remain stateless
- All SQL operations go through the `AsyncSQLiteSingleton`
- Query results are converted to Pydantic Models
- New tables require DDL definitions in `database/engine.py` (`table_ddl_list`)

---

## Data Path 2: Asynchronous Task Processing

### task_handler => base_worker => manager

This path handles background asynchronous tasks using producer-consumer pattern + multi-process execution:

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│ TaskHandler │────▶│  BaseWorker │────▶│   Worker    │────▶│   Manager   │
│ (scheduler) │     │(reflection) │     │(business)   │     │(persistence)│
└─────────────┘     └─────────────┘     └─────────────┘     └─────────────┘
     │                    │                    │                    │
     ▼                    ▼                    ▼                    ▼
task_handler.py      worker/base.py    kv_cache_log_parse_worker.py  task.py
                                             (example)              (example)
```

### Responsibilities and Development Standards

#### 1. TaskHandler Layer (`task/task_handler.py`)

**Responsibilities**:
- Scheduled by APScheduler every 5 seconds
- Poll task statuses in the database
- Manage task lifecycle: init, run, stop, delete
- Handle success / failure / pending task queues

**Core methods**:
```python
class TaskHandler:
    @staticmethod
    async def handle_tasks():
        """Main scheduler entry, executed every 5 seconds"""
        await TaskHandler.handle_successed_tasks()
        await TaskHandler.handle_failed_tasks()
        await TaskHandler.handle_pending_tasks()

    @staticmethod
    async def init_task(task_type: TaskTypeEnum, op_id: str) -> str:
        task_id = await BaseWorker.init(task_type, op_id)
        return task_id

    @staticmethod
    async def stop_task(task_id: str) -> str:
        return await BaseWorker.stop(task_id)
```

**Task state transitions**:

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
[SUCCESSFUL / FAILED / CANCELLED] ──[delete]──▶ (removed from DB) ◀───────────────────┘
```

**State descriptions**:

| State | Description |
|-------|-------------|
| `PENDING` | Waiting for TaskHandler to schedule |
| `RUNNING` | Executing, Worker subprocess has started |
| `SUCCESSFUL_PENDING_REMOVE` | Execution succeeded, waiting for `deinit` cleanup to become `SUCCESSFUL` |
| `FAILED_PENDING_REMOVE` | Execution failed, waiting for `reinit` retry or transition to `FAILED` |
| `SUCCESSFUL` | Final success state |
| `FAILED` | Final failure state (exceeded max retry limit) |
| `CANCELLED` | Manually stopped / cancelled |

**Scheduling order** (TaskHandler.handle_tasks runs every 5 seconds):
1. `handle_successed_tasks`: `SUCCESSFUL_PENDING_REMOVE` → `SUCCESSFUL`
2. `handle_failed_tasks`: `FAILED_PENDING_REMOVE` via `reinit` → `PENDING` (retry) or `FAILED` (final)
3. `handle_pending_tasks`: `PENDING` → `RUNNING`

**Service restart recovery**: On startup, tasks in `RUNNING` state are automatically restored to `PENDING` to prevent tasks from getting stuck after an unexpected restart.

#### 2. BaseWorker Layer (`task/worker/base.py`)

**Responsibilities**:
- Find concrete Worker subclasses via **reflection** (using `TaskTypeEnum`)
- Manage task state transitions
- Launch actual tasks via `ProcessHandler` in sub-processes
- Unified interfaces: `init` / `run` / `stop` / `delete` / `reinit` / `deinit`

**Reflection mechanism**:
```python
class BaseWorker:
    @staticmethod
    def find_worker_class(worker_name: TaskTypeEnum):
        subclasses = BaseWorker.__subclasses__()
        for subclass in subclasses:
            if subclass.name == worker_name:
                return subclass
        return None
```

**Multi-process execution** (`task/process_handle.py`):
- `ProcessHandler` maintains a process dict `tasks`, max count controlled by `cpu_limit`
- `add_task()` creates a new process to run Worker `run` method
- `remove_task()` terminates and cleans up processes

#### 3. Worker Layer (`task/worker/*.py`)

**Responsibilities**:
- Inherit from `BaseWorker` concept (linked by `name` attribute)
- Implement concrete business logic

**Steps to develop a new Worker**:
1. Add task type in `ENUM/task.py`:
   ```python
   class TaskTypeEnum(StrEnum):
       KV_CACHE_LOG_PARSE_WORKER = "kv_cache_log_parse_worker"
       MY_NEW_WORKER = "my_new_worker"
   ```

2. Create new Worker file under `task/worker/`:
   ```python
   from latency.ENUM.task import TaskStatusEnum, TaskTypeEnum
   from latency.task.worker.base import BaseWorker
   from latency.database.managers.task import TaskManager
   from latency.schemas.task import TaskModel
   import uuid

   class MyNewWorker:
       name = TaskTypeEnum.MY_NEW_WORKER

       @staticmethod
       async def init(op_id: str) -> str | None:
           """Initialize task data, insert into DB; return None if op_id is invalid"""
           task_id = str(uuid.uuid4())
           task = TaskModel(
               id=task_id,
               kb_id="",
               task_name="my_new_task",
               task_type=TaskTypeEnum.MY_NEW_WORKER,
               status=TaskStatusEnum.PENDING,
               op_id=op_id,
           )
           await TaskManager.add_task(task)
           return task_id

       @staticmethod
       async def run(task_id: str) -> bool:
           """Actual business logic, runs in sub-process"""
           try:
               task = await TaskManager.get_task_by_task_id(task_id)
               # ... execute business logic ...
               await BaseWorker.report(task_id, "Processing...", TaskStatusEnum.RUNNING, 50.0)
               await TaskManager.update_task(
                   task_id, {"status": TaskStatusEnum.SUCCESSFUL_PENDING_REMOVE.value}
               )
               await BaseWorker.report(task_id, "Done", TaskStatusEnum.RUNNING, 100.0)
               return True
           except Exception as e:
               await TaskManager.update_task(
                   task_id, {"status": TaskStatusEnum.FAILED_PENDING_REMOVE.value}
               )
               await BaseWorker.report(task_id, f"Failed: {e}", TaskStatusEnum.RUNNING, 0.0)
               return False

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

3. Worker lifecycle methods:

| Method | Trigger | Input | Output | Description |
|--------|---------|-------|--------|-------------|
| `init` | External task creation | `op_id: str` | `str \| None` | Initialize task data, insert into DB; return `None` on failure |
| `run` | TaskHandler schedules | `task_id: str` | `bool` | Actual business logic, runs in sub-process; return `True` on success |
| `stop` | External stop request | `task_id: str` | `str \| None` | Clean up running resources; return `task_id` or `None` |
| `delete` | External delete request | `task_id: str` | `str` | Permanently remove task data; return `task_id` |
| `reinit` | Failed task retry | `task_id: str` | `bool` | Reset task state for retry; return whether retry is allowed |
| `deinit` | Task success completion | `task_id: str` | `str` | Final cleanup; return `task_id` |

---

## Quick Development Example

### Example: Add a new "Log Analysis Task" API and Worker

#### Step 1: Add Router

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

#### Step 2: Register Router (App)

`access/fastapi_server.py`:
```python
from latency.routers import analysis

async def configure():
    app.include_router(log_file.router)
    app.include_router(analysis.router)
```

#### Step 3: Service Logic

`services/analysis.py`:
```python
from latency.task.task_handler import TaskHandler
from latency.ENUM.task import TaskTypeEnum

class AnalysisService:
    @staticmethod
    async def start_analysis(kb_id: str) -> str:
        task_id = await TaskHandler.init_task(TaskTypeEnum.LOG_ANALYSIS_WORKER, kb_id)
        return task_id
```

#### Step 4: Task Type (ENUM)

`ENUM/task.py`:
```python
class TaskTypeEnum(StrEnum):
    KV_CACHE_LOG_PARSE_WORKER = "kv_cache_log_parse_worker"
    LOG_ANALYSIS_WORKER = "log_analysis_worker"
```

#### Step 5: Worker Implementation

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
            task_name="Log Analysis Task",
            task_type=TaskTypeEnum.LOG_ANALYSIS_WORKER,
            status=TaskStatusEnum.PENDING,
            op_id=op_id,
        )
        await TaskManager.add_task(task)
        return task_id

    @staticmethod
    async def run(task_id: str) -> bool:
        await BaseWorker.report(task_id, "Started", TaskStatusEnum.RUNNING, 0.0)
        # ... execute analysis logic ...
        await TaskManager.update_task(
            task_id, {"status": TaskStatusEnum.SUCCESSFUL_PENDING_REMOVE.value}
        )
        await BaseWorker.report(task_id, "Completed", TaskStatusEnum.RUNNING, 100.0)
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

## Database Notes

- Uses **SQLite** as embedded database
- `AsyncSQLiteSingleton` provides singleton database connection
- Supports WAL mode for better concurrency
- All DB operations are wrapped in async interfaces (executed in thread pool)

**Steps to add a new table**:
1. Define `CREATE TABLE` DDL in `database/engine.py` (`table_ddl_list`)
2. Add corresponding Pydantic Model in `schemas/`
3. Add corresponding Manager class in `database/managers/`
