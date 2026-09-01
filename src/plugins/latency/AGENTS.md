# Latency Plugin — FastAPI Log Parse & Anomaly Detection Microservice

## OVERVIEW

Python FastAPI microservice (port 9772) for DS log parsing, latency anomaly detection, and AI-assisted fault diagnosis. Layered architecture: HTTP (access→routers→services→managers) + async task pipeline (task_handler→base_worker→worker/*). SQLite WAL, multiprocessing.spawn, APScheduler 5s polling.

## STRUCTURE

```
latency/
├── access/              # Entry points: FastAPI(9772), shell CLI
├── routers/             # FastAPI API definitions (prefix+tags per resource)
├── services/            # Business logic, @staticmethod stateless classes
├── database/
│   ├── engine.py        # AsyncSQLiteSingleton, table_ddl_list, WAL mode
│   └── managers/        # CRUD per table (Task, LogFile, ParseResult, etc.)
├── task/
│   ├── task_handler.py  # APScheduler entry: 3-queue dispatch (success/fail/pending)
│   ├── process_handle.py # multiprocessing.Process pool with cpu_limit
│   └── worker/          # BaseWorker + KVCacheLogParseWorker + diagnosis worker
├── parse/
│   ├── parallel_scanner/ # Phase 1: dedup+split, Phase 2: multiprocess file scan
│   ├── correlation/     # LogCorrelator (10-stage join), ParseResultBuilder
│   └── *_parser.py      # SdkAccess, WorkerAccess, WorkerInfo, URMA, Link, etc.
├── detect/
│   ├── detectors.py     # SlidingWindowP99Detector, ThresholdDirectDetector, registry
│   └── engine.py        # DetectionEngine: field-grouped parallel detection
├── schemas/             # Pydantic v2 models + dataclass(slots=True) intermediates
├── ENUM/                # StrEnum enums (TaskType, TaskStatus, DetectionMode, etc.)
├── config/config.py     # Config singleton: diagnosis_config.toml with hot-reload
├── common/              # Stats, converter, trace_context, zip_handler
├── models/              # AI model wrappers (chat, embedding, OCR, reranker)
├── deploy/              # deploy.sh (uv venv), pyproject.toml, Dockerfile
├── test/                # 9 pytest files + 11 script-style tests
└── regex/               # kvcache_log regex patterns
```

## WHERE TO LOOK

| Task | File(s) | Notes |
|------|---------|-------|
| Main entry + startup | `access/fastapi_server.py` | `configure()`, `startup_event()`, APScheduler 5s |
| Parse pipeline (core) | `task/worker/kv_cache_log_parse_worker.py` | `parse_log()`: 3 scan stages → correlation → build → detect → DB batch insert |
| Parallel scanner | `parse/parallel_scanner/scanner.py` | `ParallelFileScanner.scan_all()` with ProcessPoolExecutor |
| Correlation engine | `parse/correlation/correlator.py` | `LogCorrelator.correlate()`: IndexManager + 10 stage correlators |
| Result builder | `parse/correlation/result_builder.py` | `ParseResultBuilder.build()`: SDK/Worker join → dataclass construction |
| Anomaly detection | `detect/engine.py` | `DetectionEngine.run_parallel()`: 17 detectors × 5 metrics × 4 windows |
| Task FSM | `task/task_handler.py` | `handle_tasks()` → 3-queue dispatch, 7-state machine |
| Worker pattern | `task/worker/base.py` | `__subclasses__()` reflection, `init/run/stop/delete/reinit/deinit` |
| DB engine | `database/engine.py` | `AsyncSQLiteSingleton`, `table_ddl_list` (18 tables), 1 write + 5 read pool |
| Configuration | `config/config.py` | `Config` singleton, `diagnosis_config.toml`, `DiagnosisRuntimeConfig` |
| API response models | `schemas/response.py` | `ResponseBase`, `PaginatedResponse` |
| Parse result schemas | `schemas/log.py` | `LogParseResultDataclass`(36 fields), `C2WLogParseResultDataclass`(18), `SparseLogParseResultDataclass`(15) |
| Diagnosis API | `routers/` | Read-only HTTP queries used directly by the AI Agent |

## KEY PATTERNS

**Parse Pipeline (3 Scan → 10 Correlation → Build → Batch)**:
1. **SDK Access Scan**: `ParallelFileScanner` + `SdkAccessLogParser`, no scope filter
2. **Worker Access Scan**: scope narrowed to SDK trace_ids; full scan fallback if >50K traces
3. **Worker INFO Scan**: scope narrowed to (pod_ip, trace_id) pairs; sub-labels split by EntryType
4. **Correlation**: `LogCorrelator` 10-stage join (Worker→URMA/RemotePull/Link/QueryMeta/Timed×6) by trace_id
5. **Build**: `ParseResultBuilder` joins SDK+Worker via `CorrelationResult` → tiered dataclasses
6. **Detect**: `DetectionEngine` field-grouped → `SlidingWindowP99Detector`/`ThresholdDirectDetector`
7. **Batch insert**: 4-channel (minimal/sparse/c2w/full) via `asyncio.to_thread`

**Memory Optimization**: Tiered dataclasses with `slots=True`: `LogParseResultDataclass`(36), `C2WLogParseResultDataclass`(18 fields + ClassVar[None] for unused Worker), `SparseLogParseResultDataclass`(15 + ClassVar[None]). `LogParseResultBatch(all_sparse=True)` batch hint. Batch UUID via `os.urandom(N*16)`, shared `created_at`.

**Task System**: APScheduler 5s → `TaskHandler.handle_tasks()` → 3 queues (successed/failed/pending). 7-state FSM: PENDING→RUNNING→SUCCESSFUL_PENDING_REMOVE→SUCCESSFUL (or →FAILED). `ProcessHandler` with `cpu_limit`, `multiprocessing.spawn`. Restart recovery: RUNNING→PENDING.

**Worker Reflection**: `__subclasses__()` to match `TaskTypeEnum`. New worker: `name` attr, implement `init/run/stop/delete/reinit/deinit`. **DB batch**: 4-channel `insert_batch` (minimal/sparse/c2w/full) via `executemany`, WAL mode.

## ANTI-PATTERNS

- **5x duplicated SQL builders** in `log_failure_event.py` — same WHERE clauses rebuilt per method
- **`print()` instead of logger** (29 instances) — `log_failure_event.py`, `services/log_file.py`
- **Bare `except:` clauses** (6 instances) — silently swallows all exceptions
- **TODO stubs** (3 unimplemented methods) — `log_failure_event.py:477,725,908`
- **Wildcard import**: `fastapi_server.py: from latency.task.worker import *`
- **Monolithic modules** (>500 LOC): `kv_cache_log_parse_worker.py`(1381), `engine.py`(1033), `result_builder.py`(812)
- **Database state mutation in reinit** — marks related rows `existed_status=0` instead of using transactions

## COMMANDS

```bash
# Deploy & run
cd deploy && bash deploy.sh                              # uv venv + start (9772)
bash deploy/deploy_opencode.sh                             # OpenCode serve (4096)
PYTHONPATH=$(pwd)/src/plugins python latency/access/fastapi_server.py

# Tests
source .venv/bin/activate && pytest test/ -v
python test/test_kv_cache_log_parse_worker.py all /path/to/logs

# Health: curl http://127.0.0.1:9772/health_check
```
