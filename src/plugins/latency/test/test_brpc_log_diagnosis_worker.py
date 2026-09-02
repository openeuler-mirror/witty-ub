import asyncio
from contextlib import asynccontextmanager
from datetime import datetime
import json
from pathlib import Path
import shutil
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from latency.ENUM.task import TaskStatusEnum, TaskTypeEnum
from latency.exceptions import ConflictBizException
from latency.schemas.config import LogFilenamePatternConfig
from latency.schemas.log import LogFileModel
from latency.schemas.request import (
    UpLoadLogFileConfig,
    UpLoadLogFilesRequest,
    ListLogFilesRequest,
    RunBrpcDiagnosisRequest,
)
from latency.ENUM.general import SourceType
from latency.services.log_file import LogFileService
from latency.task.progress import task_progress
from latency.task.task_handler import TaskHandler
from latency.task.worker.base import BaseWorker
from latency.task.worker.brpc_log_diagnosis_worker import (
    BrpcDiagnosisWorkerError,
    BrpcLogDiagnosisWorker,
)
from latency.task.worker.kv_cache_log_event_diagnosis_worker import (
    KVCacheLogEventDiagnosisWorker,
)
import latency.task.worker.brpc_log_diagnosis_worker as worker_module
import latency.services.log_file as log_file_service_module


FIXTURES = Path(__file__).parent / "fixtures" / "brpc_diag"
SCHEMA_ID = "1" * 64


class FakePopen:
    def __init__(
        self,
        *,
        returncode=0,
        stdout="tool stdout",
        stderr="tool stderr",
        timeout=False,
    ):
        self.pid = 43210
        self.returncode = returncode
        self._stdout = stdout
        self._stderr = stderr
        self._timeout = timeout
        self._communicate_calls = 0
        self.wait_calls = []

    def poll(self):
        return self.returncode

    def communicate(self, timeout=None):
        self._communicate_calls += 1
        if self._timeout and self._communicate_calls == 1:
            raise worker_module.subprocess.TimeoutExpired(
                "witty-ub-brpc-diag",
                timeout,
                output="partial stdout",
                stderr="partial stderr",
            )
        return self._stdout, self._stderr

    def wait(self, timeout=None):
        self.wait_calls.append(timeout)
        self.returncode = -15
        return self.returncode


def _run(coroutine):
    return asyncio.run(coroutine)


def _copy_result_files(output_dir, *, include_schema=True):
    output_dir.mkdir(parents=True, exist_ok=True)
    batch_path = output_dir / "batch_task-normal.jsonl"
    shutil.copyfile(
        FIXTURES / "valid" / "batch_task-normal.jsonl",
        batch_path,
    )
    schema_path = output_dir / f"schema_{SCHEMA_ID}.json"
    if include_schema:
        shutil.copyfile(
            FIXTURES / "valid" / f"schema_{SCHEMA_ID}.json",
            schema_path,
        )
    return schema_path, batch_path


def _configure_run_dependencies(monkeypatch, log_path):
    task = SimpleNamespace(
        id="task-normal",
        op_id="log-file-id",
        status=TaskStatusEnum.RUNNING,
    )
    log_file = SimpleNamespace(kb_id="kb-id", file_path=str(log_path))
    status_updates = []
    reports = []

    async def get_task(_task_id):
        return task

    async def update_task(_task_id, changes):
        status_updates.append(changes)
        if "status" in changes:
            task.status = TaskStatusEnum(changes["status"])
        return True

    async def get_log_file(_log_file_id):
        return log_file

    async def update_log_file(_log_file_id, _changes):
        return 1

    async def report(_task_id, message, progress):
        reports.append((message, progress))
        return True

    monkeypatch.setattr(worker_module.TaskPGManager, "get_task_by_task_id", get_task)
    monkeypatch.setattr(worker_module.TaskPGManager, "update_task", update_task)
    monkeypatch.setattr(
        worker_module.LogFilePGManager,
        "get_log_file_by_log_file_id",
        get_log_file,
    )
    monkeypatch.setattr(
        worker_module.LogFilePGManager,
        "update_log_file",
        update_log_file,
    )
    monkeypatch.setattr(worker_module.BaseWorker, "report", report)
    monkeypatch.setattr(
        BrpcLogDiagnosisWorker,
        "_resolve_start_time",
        lambda _task_id: "2026-08-11 10:20:30",
    )
    return task, status_updates, reports


def test_worker_type_and_default_patterns_are_defined():
    config = LogFilenamePatternConfig()

    assert BrpcLogDiagnosisWorker.name == TaskTypeEnum.BRPC_LOG_DIAGNOSIS_WORKER
    assert config.brpc_log_file_patterns == [
        "brpc.log",
        "brpc.log.*",
        "*brpc*.log",
    ]


def test_task_handler_dispatches_brpc_without_shared_preprocessing(monkeypatch):
    task = SimpleNamespace(
        id="brpc-task",
        task_type=TaskTypeEnum.BRPC_LOG_DIAGNOSIS_WORKER,
    )
    list_pending = AsyncMock(return_value=[task])
    preprocess = AsyncMock(
        side_effect=AssertionError("BRPC must not use KVCache preprocessing")
    )
    run_worker = AsyncMock(return_value=True)

    monkeypatch.setattr(
        worker_module.TaskPGManager,
        "get_oldest_tasks_by_status",
        list_pending,
    )
    monkeypatch.setattr(TaskHandler, "_preprocess_log_source", preprocess)
    monkeypatch.setattr(
        TaskHandler,
        "get_task_config",
        lambda _task_id: SimpleNamespace(start_time="2026-08-11 10:20:30"),
    )
    monkeypatch.setattr(BaseWorker, "run", run_worker)

    _run(TaskHandler.handle_pending_tasks())

    preprocess.assert_not_awaited()
    run_worker.assert_awaited_once_with(
        "brpc-task",
        log_dir=None,
        worker_kwargs={"start_time": "2026-08-11 10:20:30"},
    )


def test_task_handler_keeps_dispatching_after_one_worker_fails(monkeypatch):
    parse_task = SimpleNamespace(
        id="brpc-parse-task",
        task_type=TaskTypeEnum.BRPC_LOG_PARSE_WORKER,
    )
    diagnosis_task = SimpleNamespace(
        id="brpc-diagnosis-task",
        task_type=TaskTypeEnum.BRPC_LOG_DIAGNOSIS_WORKER,
    )
    monkeypatch.setattr(
        worker_module.TaskPGManager,
        "get_oldest_tasks_by_status",
        AsyncMock(return_value=[parse_task, diagnosis_task]),
    )
    monkeypatch.setattr(
        TaskHandler,
        "_preprocess_log_source",
        AsyncMock(return_value="/logs"),
    )
    run_worker = AsyncMock(side_effect=[False, True])
    monkeypatch.setattr(BaseWorker, "run", run_worker)

    _run(TaskHandler.handle_pending_tasks())

    assert [call.args[0] for call in run_worker.await_args_list] == [
        "brpc-parse-task",
        "brpc-diagnosis-task",
    ]


def test_upload_brpc_creates_one_model_and_two_tasks(monkeypatch, tmp_path):
    log1 = tmp_path / "brpc.log"
    log1.write_text("brpc log content 1", encoding="utf-8")
    profiling = tmp_path / "ubsocket_profiling.txt"
    profiling.write_text("timeStamp: 2026-08-13 10:00:00\ninterface stats\n", encoding="utf-8")
    added_models = []

    async def add_log_files(models):
        added_models.extend(models)
        return [model.id for model in models]

    init_task = AsyncMock(side_effect=["parse-task", "diagnosis-task"])
    monkeypatch.setattr(
        log_file_service_module.LogFilePGManager,
        "add_log_files",
        add_log_files,
    )
    monkeypatch.setattr(log_file_service_module.TaskHandler, "init_task", init_task)

    result = _run(
        LogFileService.upload_log_files(
            "kb-id",
            UpLoadLogFilesRequest(
                upload_log_file_configs=[
                    UpLoadLogFileConfig(
                        name=tmp_path.name,
                        source_type=SourceType.LOCAL,
                        source=str(tmp_path),
                        log_type="brpc",
                    )
                ]
            ),
        )
    )

    assert len(added_models) == 1
    assert added_models[0].file_path == str(tmp_path)
    assert result.log_file_ids == [added_models[0].id]
    assert [call.kwargs["task_type"] for call in init_task.await_args_list] == [
        TaskTypeEnum.BRPC_LOG_PARSE_WORKER,
        TaskTypeEnum.BRPC_LOG_DIAGNOSIS_WORKER,
    ]


def test_upload_brpc_directory_creates_two_tasks(monkeypatch, tmp_path):
    log1 = tmp_path / "brpc.log"
    log1.write_text("brpc log content 1", encoding="utf-8")
    log2 = tmp_path / "brpc.log.1"
    log2.write_text("brpc log content 2", encoding="utf-8")
    other = tmp_path / "subdir" / "other.log"
    other.parent.mkdir()
    other.write_text("other log content", encoding="utf-8")
    added_models = []

    async def add_log_files(models):
        added_models.extend(models)
        return [model.id for model in models]

    init_task = AsyncMock(side_effect=["parse-task", "diagnosis-task"])
    monkeypatch.setattr(
        log_file_service_module.LogFilePGManager,
        "add_log_files",
        add_log_files,
    )
    monkeypatch.setattr(log_file_service_module.TaskHandler, "init_task", init_task)

    result = _run(
        LogFileService.upload_log_files(
            "kb-id",
            UpLoadLogFilesRequest(
                upload_log_file_configs=[
                    UpLoadLogFileConfig(
                        name=tmp_path.name,
                        source_type=SourceType.LOCAL,
                        source=str(tmp_path),
                        log_type="brpc",
                    )
                ]
            ),
        )
    )

    assert len(added_models) == 1
    assert added_models[0].file_path == str(tmp_path)
    assert added_models[0].file_size == log1.stat().st_size + log2.stat().st_size + other.stat().st_size
    assert init_task.await_count == 2
    assert [call.kwargs["task_type"] for call in init_task.await_args_list] == [
        TaskTypeEnum.BRPC_LOG_PARSE_WORKER,
        TaskTypeEnum.BRPC_LOG_DIAGNOSIS_WORKER,
    ]


def test_get_brpc_log_file_returns_parallel_overall_progress(monkeypatch):
    log_file = LogFileModel(
        id="log-file-id",
        kb_id="kb-id",
        name="brpc-logs",
        log_type="brpc",
        file_path="/logs",
    )
    parse_task = SimpleNamespace(
        id="parse-task",
        op_id=log_file.id,
        task_type=TaskTypeEnum.BRPC_LOG_PARSE_WORKER,
        status=TaskStatusEnum.RUNNING,
        task_reports=[],
    )
    diagnosis_task = SimpleNamespace(
        id="diagnosis-task",
        op_id=log_file.id,
        task_type=TaskTypeEnum.BRPC_LOG_DIAGNOSIS_WORKER,
        status=TaskStatusEnum.RUNNING,
        task_reports=[],
    )
    get_current_calls = []

    async def get_current(_op_id, task_type=None):
        get_current_calls.append(task_type)
        return {
            TaskTypeEnum.BRPC_LOG_PARSE_WORKER: parse_task,
            TaskTypeEnum.BRPC_LOG_DIAGNOSIS_WORKER: diagnosis_task,
        }.get(task_type)

    async def list_reports(task_ids):
        if task_ids == [parse_task.id]:
            return [
                SimpleNamespace(
                    task_id=parse_task.id,
                    message="BRPC parse completed",
                    progress=80.0,
                )
            ]
        if task_ids == [diagnosis_task.id]:
            return [
                SimpleNamespace(
                    task_id=diagnosis_task.id,
                    message="BRPC 诊断工具运行完成",
                    progress=40.0,
                )
            ]
        return []

    monkeypatch.setattr(
        log_file_service_module.LogFilePGManager,
        "get_log_file_by_log_file_id",
        AsyncMock(return_value=log_file),
    )
    monkeypatch.setattr(
        log_file_service_module.TaskPGManager,
        "get_current_task_by_op_id",
        get_current,
    )
    monkeypatch.setattr(
        log_file_service_module.TaskReportPGManager,
        "list_task_reports_by_task_ids",
        list_reports,
    )
    monkeypatch.setattr(
        log_file_service_module.LogFileService,
        "_populate_brpc_counts",
        AsyncMock(),
    )

    result = _run(LogFileService.get_log_file_by_log_file_id(log_file.id))

    assert get_current_calls == [
        TaskTypeEnum.BRPC_LOG_PARSE_WORKER,
        TaskTypeEnum.BRPC_LOG_DIAGNOSIS_WORKER,
    ]
    assert result.log_file.overall_progress == 60.0
    assert result.log_file.overall_status == TaskStatusEnum.RUNNING.value


def test_list_brpc_log_files_returns_parallel_overall_progress(monkeypatch):
    log_file = LogFileModel(
        id="log-file-id",
        kb_id="kb-id",
        name="brpc-logs",
        log_type="brpc",
        file_path="/logs",
    )
    parse_task = SimpleNamespace(
        id="parse-task",
        op_id=log_file.id,
        task_type=TaskTypeEnum.BRPC_LOG_PARSE_WORKER,
        status=TaskStatusEnum.RUNNING,
        task_reports=[],
    )
    diagnosis_task = SimpleNamespace(
        id="diagnosis-task",
        op_id=log_file.id,
        task_type=TaskTypeEnum.BRPC_LOG_DIAGNOSIS_WORKER,
        status=TaskStatusEnum.RUNNING,
        task_reports=[],
    )
    queried_task_types = []

    async def list_current(_op_ids, task_type=None):
        queried_task_types.append(task_type)
        return {
            TaskTypeEnum.BRPC_LOG_PARSE_WORKER: [parse_task],
            TaskTypeEnum.BRPC_LOG_DIAGNOSIS_WORKER: [diagnosis_task],
        }.get(task_type, [])

    parse_report = SimpleNamespace(
        task_id=parse_task.id,
        message="BRPC parse completed",
        progress=80.0,
        created_at=datetime(2026, 8, 13, 10, 0, 0),
    )
    diagnosis_report = SimpleNamespace(
        task_id=diagnosis_task.id,
        message="BRPC 诊断工具运行完成",
        progress=40.0,
        created_at=datetime(2026, 8, 13, 10, 0, 1),
    )

    async def list_reports(task_ids):
        reports = {
            parse_task.id: parse_report,
            diagnosis_task.id: diagnosis_report,
        }
        return [reports[task_id] for task_id in task_ids if task_id in reports]

    monkeypatch.setattr(
        log_file_service_module.LogFilePGManager,
        "list_log_files",
        AsyncMock(return_value=(1, [log_file])),
    )
    monkeypatch.setattr(
        log_file_service_module.TaskPGManager,
        "list_current_tasks_by_op_ids",
        list_current,
    )
    monkeypatch.setattr(
        log_file_service_module.TaskReportPGManager,
        "list_task_reports_by_task_ids",
        list_reports,
    )
    monkeypatch.setattr(
        log_file_service_module.LogFileService,
        "_populate_brpc_counts",
        AsyncMock(),
    )

    result = _run(
        LogFileService.list_log_files("kb-id", ListLogFilesRequest())
    )

    assert TaskTypeEnum.BRPC_LOG_PARSE_WORKER in queried_task_types
    assert TaskTypeEnum.BRPC_LOG_DIAGNOSIS_WORKER in queried_task_types
    assert result.log_files[0].overall_progress == 60.0
    assert result.log_files[0].overall_status == TaskStatusEnum.RUNNING.value


def test_populate_brpc_counts_sets_profiling_and_diagnosis_counts(monkeypatch):
    log_file = LogFileModel(
        id="log-file-id",
        kb_id="kb-id",
        name="brpc-logs",
        log_type="brpc",
        file_path="/logs",
    )
    parse_task = SimpleNamespace(
        id="parse-task",
        status=TaskStatusEnum.SUCCESSFUL,
    )
    diagnosis_task = SimpleNamespace(
        id="diagnosis-task",
        status=TaskStatusEnum.SUCCESSFUL_PENDING_REMOVE,
    )
    batch = SimpleNamespace(hit_count=42)

    monkeypatch.setattr(
        log_file_service_module.BrpcProfilingResultPGManager,
        "count_files_by_log_id",
        AsyncMock(return_value=3),
    )

    @asynccontextmanager
    async def open_session():
        yield object()

    monkeypatch.setattr(
        log_file_service_module.PGManager,
        "session",
        staticmethod(open_session),
    )
    monkeypatch.setattr(
        log_file_service_module.BrpcDiagnosisPGManager,
        "get_batch_by_task_id",
        AsyncMock(return_value=batch),
    )

    _run(LogFileService._populate_brpc_counts(log_file, parse_task, diagnosis_task))

    assert log_file.anomaly_cnt == 3
    assert log_file.trace_failure_event_cnt == 42


def test_populate_brpc_counts_skips_unsuccessful_tasks(monkeypatch):
    log_file = LogFileModel(
        id="log-file-id",
        kb_id="kb-id",
        name="brpc-logs",
        log_type="brpc",
        file_path="/logs",
    )
    parse_task = SimpleNamespace(
        id="parse-task",
        status=TaskStatusEnum.RUNNING,
    )
    diagnosis_task = SimpleNamespace(
        id="diagnosis-task",
        status=TaskStatusEnum.FAILED,
    )

    _run(LogFileService._populate_brpc_counts(log_file, parse_task, diagnosis_task))

    assert log_file.anomaly_cnt == 0
    assert log_file.trace_failure_event_cnt == 0


@pytest.mark.parametrize(
    "parse_task_status,diag_status,expected_task",
    [
        (TaskStatusEnum.RUNNING, TaskStatusEnum.PENDING, "parse"),
        (TaskStatusEnum.PENDING, TaskStatusEnum.RUNNING, "diag"),
        (TaskStatusEnum.SUCCESSFUL, TaskStatusEnum.RUNNING, "diag"),
        (TaskStatusEnum.SUCCESSFUL, TaskStatusEnum.SUCCESSFUL_PENDING_REMOVE, "diag"),
        (TaskStatusEnum.FAILED, TaskStatusEnum.SUCCESSFUL, "parse"),
        (TaskStatusEnum.FAILED_PENDING_REMOVE, TaskStatusEnum.FAILED, "parse"),
    ],
)
def test_select_brpc_visible_task_priority(parse_task_status, diag_status, expected_task):
    parse_task = SimpleNamespace(
        id="parse-task",
        status=parse_task_status,
        task_type=TaskTypeEnum.BRPC_LOG_PARSE_WORKER,
    )
    diagnosis_task = SimpleNamespace(
        id="diag-task",
        status=diag_status,
        task_type=TaskTypeEnum.BRPC_LOG_DIAGNOSIS_WORKER,
    )
    selected = LogFileService._select_brpc_visible_task(parse_task, diagnosis_task)
    assert selected.id == ("parse-task" if expected_task == "parse" else "diag-task")


@pytest.mark.parametrize(
    "task_states,expected_status",
    [
        ([(TaskStatusEnum.PENDING, 0)], TaskStatusEnum.PENDING.value),
        ([(TaskStatusEnum.RUNNING, 0), (TaskStatusEnum.PENDING, 0)], TaskStatusEnum.RUNNING.value),
        (
            [(TaskStatusEnum.FAILED_PENDING_REMOVE, 0), (TaskStatusEnum.RUNNING, 0)],
            LogFileService.RETRYING_STATUS,
        ),
        ([(TaskStatusEnum.RUNNING, 1)], LogFileService.RETRYING_STATUS),
        (
            [(TaskStatusEnum.FAILED, 0), (TaskStatusEnum.RUNNING, 0)],
            TaskStatusEnum.RUNNING.value,
        ),
        (
            [(TaskStatusEnum.FAILED, 0), (TaskStatusEnum.SUCCESSFUL, 0)],
            TaskStatusEnum.FAILED.value,
        ),
        (
            [(TaskStatusEnum.CANCELLED, 0), (TaskStatusEnum.SUCCESSFUL, 0)],
            TaskStatusEnum.CANCELLED.value,
        ),
        (
            [
                (TaskStatusEnum.SUCCESSFUL, 0),
                (TaskStatusEnum.SUCCESSFUL_PENDING_REMOVE, 0),
            ],
            TaskStatusEnum.SUCCESSFUL_PENDING_REMOVE.value,
        ),
        (
            [(TaskStatusEnum.SUCCESSFUL, 0), (TaskStatusEnum.SUCCESSFUL, 0)],
            TaskStatusEnum.SUCCESSFUL.value,
        ),
    ],
)
def test_aggregate_task_status(task_states, expected_status):
    tasks = [
        SimpleNamespace(status=status, retry_times=retry_times)
        for status, retry_times in task_states
    ]

    assert LogFileService._aggregate_task_status(*tasks) == expected_status


def test_aggregate_task_status_is_unknown_without_tasks():
    assert LogFileService._aggregate_task_status() == "unknown"


def test_brpc_worker_is_registered_and_progress_is_recognized():
    assert (
        BaseWorker.find_worker_class(TaskTypeEnum.BRPC_LOG_DIAGNOSIS_WORKER)
        is BrpcLogDiagnosisWorker
    )
    task = SimpleNamespace(
        task_type=TaskTypeEnum.BRPC_LOG_DIAGNOSIS_WORKER,
        status=TaskStatusEnum.RUNNING,
        task_reports=[
            SimpleNamespace(message="unrelated report", progress=99.0),
            SimpleNamespace(message="BRPC 诊断工具运行完成", progress=60.0),
        ],
    )

    assert task_progress(task) == 60.0


def test_run_brpc_service_creates_independent_task(monkeypatch):
    get_log_file = AsyncMock(
        return_value=SimpleNamespace(id="log-file-id", file_path="/logs")
    )
    get_current_task = AsyncMock(return_value=None)
    init_task = AsyncMock(return_value="brpc-task-id")
    monkeypatch.setattr(
        log_file_service_module.LogFilePGManager,
        "get_log_file_by_log_file_id",
        get_log_file,
    )
    monkeypatch.setattr(
        log_file_service_module.TaskPGManager,
        "get_current_task_by_op_id",
        get_current_task,
    )
    monkeypatch.setattr(
        log_file_service_module.TaskHandler,
        "init_task",
        init_task,
    )

    result = _run(
        LogFileService.run_brpc_diagnosis_by_log_file_id(
            "log-file-id",
            RunBrpcDiagnosisRequest(start_time="2026-08-11 10:20:30"),
        )
    )

    assert result.task_id == "brpc-task-id"
    get_current_task.assert_awaited_once_with(
        "log-file-id",
        TaskTypeEnum.BRPC_LOG_DIAGNOSIS_WORKER,
    )
    init_task.assert_awaited_once()
    init_kwargs = init_task.await_args.kwargs
    assert init_kwargs["task_type"] == TaskTypeEnum.BRPC_LOG_DIAGNOSIS_WORKER
    assert init_kwargs["op_id"] == "log-file-id"
    assert init_kwargs["parse_config"].start_time == "2026-08-11 10:20:30"


@pytest.mark.parametrize(
    "active_status",
    [TaskStatusEnum.RUNNING, TaskStatusEnum.FAILED_PENDING_REMOVE],
)
def test_run_brpc_service_rejects_second_active_task(monkeypatch, active_status):
    monkeypatch.setattr(
        log_file_service_module.LogFilePGManager,
        "get_log_file_by_log_file_id",
        AsyncMock(return_value=SimpleNamespace(id="log-file-id")),
    )
    monkeypatch.setattr(
        log_file_service_module.TaskPGManager,
        "get_current_task_by_op_id",
        AsyncMock(
            return_value=SimpleNamespace(status=active_status)
        ),
    )
    init_task = AsyncMock(return_value="unexpected-task")
    monkeypatch.setattr(
        log_file_service_module.TaskHandler,
        "init_task",
        init_task,
    )

    with pytest.raises(ConflictBizException, match="BRPC 诊断任务尚未结束"):
        _run(
            LogFileService.run_brpc_diagnosis_by_log_file_id(
                "log-file-id",
                RunBrpcDiagnosisRequest(start_time="2026-08-11 10:20:30"),
            )
        )
    init_task.assert_not_awaited()


def test_delete_brpc_results_deletes_only_brpc_batches(monkeypatch):
    session = object()

    @asynccontextmanager
    async def open_session():
        yield session

    delete_batch = AsyncMock(return_value="batch-id")
    monkeypatch.setattr(
        log_file_service_module.PGManager,
        "session",
        staticmethod(open_session),
    )
    monkeypatch.setattr(
        log_file_service_module.BrpcDiagnosisPGManager,
        "delete_batch_by_task_id",
        delete_batch,
    )
    tasks = [
        SimpleNamespace(
            id="brpc-task",
            task_type=TaskTypeEnum.BRPC_LOG_DIAGNOSIS_WORKER.value,
        ),
        SimpleNamespace(
            id="kv-task",
            task_type=TaskTypeEnum.KV_CACHE_LOG_PARSE_WORKER.value,
        ),
    ]

    _run(LogFileService._delete_brpc_diagnosis_results(tasks))

    delete_batch.assert_awaited_once_with(session, "brpc-task")


def test_build_command_uses_documented_arguments(monkeypatch, tmp_path):
    monkeypatch.setenv("WITTY_INSTALL_PATH", "/opt/witty/bin")
    log_path = tmp_path / "brpc.log"

    command = BrpcLogDiagnosisWorker._build_command(
        log_path,
        "2026-08-11 10:20:30",
        "task-123",
    )

    assert command == [
        "/opt/witty/bin/witty-ub-brpc-diag",
        "--brpc-log",
        str(log_path),
        "--time",
        "2026-08-11 10:20:30",
        "--task-id",
        "task-123",
    ]


def test_build_command_omits_time_when_start_time_is_not_configured(
    monkeypatch,
    tmp_path,
):
    monkeypatch.setenv("WITTY_INSTALL_PATH", "/opt/witty/bin")
    log_path = tmp_path / "brpc.log"

    command = BrpcLogDiagnosisWorker._build_command(
        log_path,
        None,
        "task-123",
    )

    assert command == [
        "/opt/witty/bin/witty-ub-brpc-diag",
        "--brpc-log",
        str(log_path),
        "--task-id",
        "task-123",
    ]


def test_execute_tool_records_success_and_cleans_pid(monkeypatch, tmp_path):
    process = FakePopen()
    popen_calls = []

    def popen(command, **kwargs):
        popen_calls.append((command, kwargs))
        return process

    monkeypatch.setenv("WITTY_DIR", str(tmp_path))
    monkeypatch.setattr(worker_module.subprocess, "Popen", popen)
    execution = BrpcLogDiagnosisWorker._execute_tool(
        "task-success",
        ["/usr/bin/witty-ub-brpc-diag", "--task-id", "task-success"],
    )

    assert execution.returncode == 0
    assert execution.stdout == "tool stdout"
    assert execution.stderr == "tool stderr"
    assert popen_calls[0][1]["start_new_session"] is True
    assert "task-success" not in BrpcLogDiagnosisWorker._processes
    assert not BrpcLogDiagnosisWorker._pid_path("task-success").exists()


def test_execute_tool_rejects_nonzero_return_code(monkeypatch, tmp_path):
    process = FakePopen(returncode=7)
    monkeypatch.setenv("WITTY_DIR", str(tmp_path))
    monkeypatch.setattr(
        worker_module.subprocess,
        "Popen",
        lambda *_args, **_kwargs: process,
    )

    with pytest.raises(BrpcDiagnosisWorkerError, match="非零状态: 7"):
        BrpcLogDiagnosisWorker._execute_tool(
            "task-failed",
            ["witty-ub-brpc-diag"],
        )
    assert not BrpcLogDiagnosisWorker._pid_path("task-failed").exists()


def test_execute_tool_terminates_process_group_on_timeout(monkeypatch, tmp_path):
    process = FakePopen(returncode=None, timeout=True)
    signals = []
    monkeypatch.setenv("WITTY_DIR", str(tmp_path))
    monkeypatch.setenv("BRPC_DIAG_TIMEOUT_SECONDS", "0.1")
    monkeypatch.setattr(
        worker_module.subprocess,
        "Popen",
        lambda *_args, **_kwargs: process,
    )
    monkeypatch.setattr(
        worker_module.os,
        "killpg",
        lambda pid, sent_signal: signals.append((pid, sent_signal)),
    )

    with pytest.raises(BrpcDiagnosisWorkerError, match="运行超时"):
        BrpcLogDiagnosisWorker._execute_tool(
            "task-timeout",
            ["witty-ub-brpc-diag"],
        )

    assert signals == [(process.pid, worker_module.signal.SIGTERM)]
    assert process.wait_calls == [5]
    assert not BrpcLogDiagnosisWorker._pid_path("task-timeout").exists()


def test_worker_runs_tool_and_imports_only_after_outputs_exist(
    monkeypatch, tmp_path
):
    log_path = tmp_path / "logs" / "brpc.log"
    log_path.parent.mkdir()
    log_path.write_text("log", encoding="utf-8")
    output_dir = tmp_path / "witty" / "brpc-diag"
    schema_path, batch_path = _copy_result_files(output_dir)
    _, status_updates, reports = _configure_run_dependencies(
        monkeypatch,
        log_path.parent,
    )
    commands = []
    imports = []

    def execute(task_id, command):
        commands.append((task_id, command))

    async def import_result(**kwargs):
        imports.append(kwargs)

    monkeypatch.setenv("WITTY_DIR", str(tmp_path / "witty"))
    monkeypatch.setenv("WITTY_INSTALL_PATH", "/opt/witty/bin")
    monkeypatch.setattr(BrpcLogDiagnosisWorker, "_execute_tool", execute)
    monkeypatch.setattr(
        worker_module.BrpcDiagnosisImporter,
        "import_result",
        import_result,
    )

    assert _run(BrpcLogDiagnosisWorker.run("task-normal")) is True
    assert commands[0][1] == [
        "/opt/witty/bin/witty-ub-brpc-diag",
        "--brpc-log",
        str(log_path.parent),
        "--time",
        "2026-08-11 10:20:30",
        "--task-id",
        "task-normal",
    ]
    assert imports == [
        {
            "schema_path": schema_path,
            "batch_path": batch_path,
            "expected_task_id": "task-normal",
        }
    ]
    assert status_updates[-1] == {
        "status": TaskStatusEnum.SUCCESSFUL_PENDING_REMOVE.value
    }
    assert reports[-1] == ("BRPC 诊断任务成功", 100.0)


@pytest.mark.parametrize("include_batch,include_schema", [(False, False), (True, False)])
def test_missing_output_marks_task_failed(
    monkeypatch,
    tmp_path,
    include_batch,
    include_schema,
):
    log_path = tmp_path / "logs" / "brpc.log"
    log_path.parent.mkdir()
    log_path.write_text("log", encoding="utf-8")
    output_dir = tmp_path / "witty" / "brpc-diag"
    if include_batch:
        _copy_result_files(output_dir, include_schema=include_schema)
    _, status_updates, _ = _configure_run_dependencies(
        monkeypatch,
        log_path.parent,
    )
    importer_called = False

    async def import_result(**_kwargs):
        nonlocal importer_called
        importer_called = True

    monkeypatch.setenv("WITTY_DIR", str(tmp_path / "witty"))
    monkeypatch.setattr(
        BrpcLogDiagnosisWorker,
        "_execute_tool",
        lambda *_args, **_kwargs: None,
    )
    monkeypatch.setattr(
        worker_module.BrpcDiagnosisImporter,
        "import_result",
        import_result,
    )

    assert _run(BrpcLogDiagnosisWorker.run("task-normal")) is False
    assert importer_called is False
    assert status_updates[-1] == {
        "status": TaskStatusEnum.FAILED_PENDING_REMOVE.value
    }


def test_import_failure_marks_task_failed_and_preserves_outputs(
    monkeypatch, tmp_path
):
    log_path = tmp_path / "logs" / "brpc.log"
    log_path.parent.mkdir()
    log_path.write_text("log", encoding="utf-8")
    output_dir = tmp_path / "witty" / "brpc-diag"
    schema_path, batch_path = _copy_result_files(output_dir)
    _, status_updates, _ = _configure_run_dependencies(
        monkeypatch,
        log_path.parent,
    )

    async def import_result(**_kwargs):
        raise RuntimeError("import failed")

    monkeypatch.setenv("WITTY_DIR", str(tmp_path / "witty"))
    monkeypatch.setattr(
        BrpcLogDiagnosisWorker,
        "_execute_tool",
        lambda *_args, **_kwargs: None,
    )
    monkeypatch.setattr(
        worker_module.BrpcDiagnosisImporter,
        "import_result",
        import_result,
    )

    assert _run(BrpcLogDiagnosisWorker.run("task-normal")) is False
    assert schema_path.exists()
    assert batch_path.exists()
    assert status_updates[-1] == {
        "status": TaskStatusEnum.FAILED_PENDING_REMOVE.value
    }


def test_stop_terminates_registered_subprocess(monkeypatch, tmp_path):
    process = FakePopen(returncode=None)
    terminated = []
    monkeypatch.setenv("WITTY_DIR", str(tmp_path))
    BrpcLogDiagnosisWorker._processes["task-stop"] = process
    monkeypatch.setattr(
        BrpcLogDiagnosisWorker,
        "_terminate_popen",
        lambda selected: terminated.append(selected.pid),
    )

    assert _run(BrpcLogDiagnosisWorker.stop("task-stop")) == "task-stop"
    assert terminated == [process.pid]
    assert "task-stop" not in BrpcLogDiagnosisWorker._processes


def test_stop_uses_pid_file_after_outer_worker_was_killed(monkeypatch, tmp_path):
    task_id = "task-cross-process-stop"
    pid = 54321
    signals = []
    monkeypatch.setenv("WITTY_DIR", str(tmp_path))
    pid_path = BrpcLogDiagnosisWorker._pid_path(task_id)
    pid_path.parent.mkdir(parents=True)
    pid_path.write_text(str(pid), encoding="ascii")
    monkeypatch.setattr(
        BrpcLogDiagnosisWorker,
        "_pid_matches_task",
        lambda selected_pid, selected_task: (selected_pid, selected_task)
        == (pid, task_id),
    )
    monkeypatch.setattr(
        worker_module.os,
        "killpg",
        lambda selected_pid, sent_signal: signals.append(
            (selected_pid, sent_signal)
        ),
    )

    def process_gone(_pid, _signal):
        raise ProcessLookupError

    monkeypatch.setattr(worker_module.os, "kill", process_gone)

    assert _run(BrpcLogDiagnosisWorker.stop(task_id)) == task_id
    assert signals == [(pid, worker_module.signal.SIGTERM)]
    assert not pid_path.exists()


def test_kvcache_worker_does_not_forward_brpc_patterns(monkeypatch):
    captured_command = []
    task = SimpleNamespace(id="task-kvcache")

    async def parse_config(_kb_id):
        return {
            "resource_log_file": ["resource.log"],
            "brpc_log_file_patterns": ["brpc.log"],
        }

    async def report(*_args, **_kwargs):
        return True

    def run(command, **_kwargs):
        captured_command.extend(command)
        return SimpleNamespace(returncode=0, stdout="", stderr="")

    monkeypatch.setattr(
        KVCacheLogEventDiagnosisWorker,
        "parse_filepath_config",
        parse_config,
    )
    monkeypatch.setattr(worker_module.BaseWorker, "report", report)
    monkeypatch.setattr(
        "latency.task.worker.kv_cache_log_event_diagnosis_worker.subprocess.run",
        run,
    )

    assert _run(
        KVCacheLogEventDiagnosisWorker.run_diagnosis_tool(
            "/logs",
            task,
            "random",
            "kb-id",
        )
    ) is True
    assert "--resource-log-file" in captured_command
    assert "--brpc-log-file-patterns" not in captured_command
