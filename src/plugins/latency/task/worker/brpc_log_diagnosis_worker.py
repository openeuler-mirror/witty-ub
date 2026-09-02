"""Worker that runs the BRPC diagnosis binary and imports its V2.1 output."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import json
import logging
import os
from pathlib import Path
import re
import signal
import subprocess
import time

from pydantic import ValidationError

from latency.ENUM.task import TaskStatusEnum, TaskTypeEnum
from latency.config.config import Config
from latency.database.managers.log_file import LogFilePGManager
from latency.database.managers.task import TaskPGManager
from latency.schemas.brpc_diagnosis import BrpcDiagBatch
from latency.schemas.task import TaskModel
from latency.services.brpc_diagnosis_importer import BrpcDiagnosisImporter
from latency.task.worker.base import BaseWorker


logger = logging.getLogger(__name__)

WITTY_INSTALL_PATH_DEFAULT = "/usr/bin"
WITTY_DIR_DEFAULT = "/var/witty-ub"
BRPC_DIAG_TIMEOUT_SECONDS_DEFAULT = 3600.0
_TASK_ID_PATTERN = re.compile(r"^[A-Za-z0-9_-]{1,128}$")


class BrpcDiagnosisWorkerError(RuntimeError):
    """Raised when the worker cannot produce an importable diagnosis result."""


@dataclass(frozen=True, slots=True)
class BrpcToolExecution:
    command: tuple[str, ...]
    returncode: int
    stdout: str
    stderr: str


class BrpcLogDiagnosisWorker(BaseWorker):
    name = TaskTypeEnum.BRPC_LOG_DIAGNOSIS_WORKER
    _processes: dict[str, subprocess.Popen[str]] = {}

    @staticmethod
    async def init(op_id: str) -> str | None:
        log_file = await LogFilePGManager.get_log_file_by_log_file_id(op_id)
        if log_file is None:
            return None
        task = TaskModel(
            kb_id=log_file.kb_id,
            op_id=op_id,
            task_name=f"诊断 BRPC 日志 {log_file.file_path}",
            task_type=TaskTypeEnum.BRPC_LOG_DIAGNOSIS_WORKER,
            status=TaskStatusEnum.PENDING,
        )
        await TaskPGManager.add_task(task)
        await BaseWorker.report(task.id, "初始化 BRPC 诊断任务", 0.0)
        return task.id

    @staticmethod
    async def reinit(task_id: str) -> bool:
        task = await TaskPGManager.get_task_by_task_id(task_id)
        if task is None:
            return False
        retry_limit = Config().get_config().task.task_retry_times
        if task.retry_times >= retry_limit:
            logger.warning(
                "BRPC diagnosis task %s reached retry limit %d",
                task_id,
                retry_limit,
            )
            return False
        await BaseWorker.report(task_id, "重新初始化 BRPC 诊断任务", 0.0)
        return True

    @staticmethod
    async def deinit(task_id: str) -> str:
        BrpcLogDiagnosisWorker._unregister_process(task_id)
        return task_id

    @staticmethod
    async def delete(task_id: str) -> str:
        await BrpcLogDiagnosisWorker.stop(task_id)
        return task_id

    @staticmethod
    def _validate_start_time(start_time: str) -> str:
        try:
            parsed = datetime.strptime(start_time, "%Y-%m-%d %H:%M:%S")
        except (TypeError, ValueError) as exc:
            raise BrpcDiagnosisWorkerError(
                "BRPC diagnosis start_time must use YYYY-MM-DD HH:MM:SS"
            ) from exc
        if parsed.strftime("%Y-%m-%d %H:%M:%S") != start_time:
            raise BrpcDiagnosisWorkerError(
                "BRPC diagnosis start_time must use YYYY-MM-DD HH:MM:SS"
            )
        return start_time

    @staticmethod
    def _resolve_start_time(task_id: str) -> str | None:
        from latency.task.task_handler import TaskHandler

        parse_config = TaskHandler.get_task_config(task_id)
        if parse_config is not None and parse_config.end_time:
            logger.info(
                "BRPC diagnosis ignores ParseConfig.end_time=%s; "
                "the binary scans until its own startup time",
                parse_config.end_time,
            )
        if parse_config is None or not parse_config.start_time:
            return None
        return BrpcLogDiagnosisWorker._validate_start_time(
            parse_config.start_time
        )

    @staticmethod
    def _timeout_seconds() -> float:
        raw_value = os.getenv(
            "BRPC_DIAG_TIMEOUT_SECONDS",
            str(BRPC_DIAG_TIMEOUT_SECONDS_DEFAULT),
        )
        try:
            timeout = float(raw_value)
        except ValueError as exc:
            raise BrpcDiagnosisWorkerError(
                f"invalid BRPC_DIAG_TIMEOUT_SECONDS: {raw_value!r}"
            ) from exc
        if timeout <= 0:
            raise BrpcDiagnosisWorkerError(
                "BRPC_DIAG_TIMEOUT_SECONDS must be greater than zero"
            )
        return timeout

    @staticmethod
    def _output_dir() -> Path:
        return Path(os.getenv("WITTY_DIR", WITTY_DIR_DEFAULT)) / "brpc-diag"

    @staticmethod
    def _pid_path(task_id: str) -> Path:
        if _TASK_ID_PATTERN.fullmatch(task_id) is None:
            raise BrpcDiagnosisWorkerError(f"invalid BRPC task ID: {task_id!r}")
        return BrpcLogDiagnosisWorker._output_dir() / f".worker_{task_id}.pid"

    @staticmethod
    def _register_process(task_id: str, process: subprocess.Popen[str]) -> None:
        BrpcLogDiagnosisWorker._processes[task_id] = process
        pid_path = BrpcLogDiagnosisWorker._pid_path(task_id)
        pid_path.parent.mkdir(parents=True, exist_ok=True)
        temp_path = pid_path.with_name(f"{pid_path.name}.{os.getpid()}.tmp")
        try:
            temp_path.write_text(str(process.pid), encoding="ascii")
            os.replace(temp_path, pid_path)
        finally:
            try:
                temp_path.unlink(missing_ok=True)
            except OSError:
                logger.warning("failed to clean temporary BRPC worker PID file")

    @staticmethod
    def _unregister_process(task_id: str, pid: int | None = None) -> None:
        process = BrpcLogDiagnosisWorker._processes.get(task_id)
        if process is not None and (pid is None or process.pid == pid):
            BrpcLogDiagnosisWorker._processes.pop(task_id, None)
        try:
            pid_path = BrpcLogDiagnosisWorker._pid_path(task_id)
            if not pid_path.exists():
                return
            stored_pid = int(pid_path.read_text(encoding="ascii").strip())
            if pid is None or stored_pid == pid:
                pid_path.unlink()
        except (OSError, ValueError, BrpcDiagnosisWorkerError) as exc:
            logger.warning("failed to clean BRPC worker PID file: %s", exc)

    @staticmethod
    def _terminate_popen(process: subprocess.Popen[str]) -> None:
        if process.poll() is not None:
            return
        try:
            os.killpg(process.pid, signal.SIGTERM)
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            os.killpg(process.pid, signal.SIGKILL)
            process.wait(timeout=5)
        except ProcessLookupError:
            return

    @staticmethod
    def _pid_matches_task(pid: int, task_id: str) -> bool:
        try:
            command_line = Path(f"/proc/{pid}/cmdline").read_bytes()
        except OSError:
            return False
        arguments = [
            item.decode("utf-8", errors="replace")
            for item in command_line.split(b"\0")
            if item
        ]
        if not arguments or Path(arguments[0]).name != "witty-ub-brpc-diag":
            return False
        try:
            task_id_index = arguments.index("--task-id")
        except ValueError:
            return False
        return (
            task_id_index + 1 < len(arguments)
            and arguments[task_id_index + 1] == task_id
        )

    @staticmethod
    def _terminate_pid(task_id: str) -> bool:
        pid_path = BrpcLogDiagnosisWorker._pid_path(task_id)
        try:
            pid = int(pid_path.read_text(encoding="ascii").strip())
        except (FileNotFoundError, OSError, ValueError):
            return False
        if not BrpcLogDiagnosisWorker._pid_matches_task(pid, task_id):
            logger.warning(
                "refusing to terminate stale or unexpected BRPC worker PID %s",
                pid,
            )
            BrpcLogDiagnosisWorker._unregister_process(task_id, pid)
            return False
        try:
            os.killpg(pid, signal.SIGTERM)
        except ProcessLookupError:
            BrpcLogDiagnosisWorker._unregister_process(task_id, pid)
            return False

        deadline = time.monotonic() + 5
        while time.monotonic() < deadline:
            try:
                os.kill(pid, 0)
            except ProcessLookupError:
                BrpcLogDiagnosisWorker._unregister_process(task_id, pid)
                return True
            time.sleep(0.05)
        try:
            os.killpg(pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        BrpcLogDiagnosisWorker._unregister_process(task_id, pid)
        return True

    @staticmethod
    def _execute_tool(task_id: str, command: list[str]) -> BrpcToolExecution:
        logger.info("running BRPC diagnosis command: %s", command)
        timeout = BrpcLogDiagnosisWorker._timeout_seconds()
        process = subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            start_new_session=True,
        )
        try:
            BrpcLogDiagnosisWorker._register_process(task_id, process)
            try:
                stdout, stderr = process.communicate(timeout=timeout)
            except subprocess.TimeoutExpired as exc:
                BrpcLogDiagnosisWorker._terminate_popen(process)
                stdout, stderr = process.communicate()
                logger.error(
                    "BRPC diagnosis timed out; returncode=%s stdout=%s stderr=%s",
                    process.returncode,
                    stdout or exc.stdout or "",
                    stderr or exc.stderr or "",
                )
                raise BrpcDiagnosisWorkerError("BRPC 诊断工具运行超时") from exc

            logger.info("BRPC diagnosis stdout: %s", stdout)
            logger.info("BRPC diagnosis stderr: %s", stderr)
            logger.info("BRPC diagnosis return code: %d", process.returncode)
            if process.returncode != 0:
                raise BrpcDiagnosisWorkerError(
                    f"BRPC 诊断工具返回非零状态: {process.returncode}"
                )
            return BrpcToolExecution(
                command=tuple(command),
                returncode=process.returncode,
                stdout=stdout,
                stderr=stderr,
            )
        except Exception:
            if process.poll() is None:
                BrpcLogDiagnosisWorker._terminate_popen(process)
            raise
        finally:
            BrpcLogDiagnosisWorker._unregister_process(task_id, process.pid)

    @staticmethod
    def _build_command(
        log_path: Path,
        start_time: str | None,
        task_id: str,
    ) -> list[str]:
        if _TASK_ID_PATTERN.fullmatch(task_id) is None:
            raise BrpcDiagnosisWorkerError(f"invalid BRPC task ID: {task_id!r}")
        binary_path = (
            Path(os.getenv("WITTY_INSTALL_PATH", WITTY_INSTALL_PATH_DEFAULT))
            / "witty-ub-brpc-diag"
        )
        command = [
            str(binary_path),
            "--brpc-log",
            str(log_path),
        ]
        if start_time is not None:
            command.extend(
                [
                    "--time",
                    BrpcLogDiagnosisWorker._validate_start_time(start_time),
                ]
            )
        command.extend(["--task-id", task_id])
        return command

    @staticmethod
    def _result_paths(task_id: str) -> tuple[Path, Path]:
        batch_path = BrpcLogDiagnosisWorker._output_dir() / f"batch_{task_id}.jsonl"
        if not batch_path.is_file():
            raise BrpcDiagnosisWorkerError(
                f"BRPC 诊断输出 batch 文件不存在: {batch_path}"
            )
        try:
            with batch_path.open("r", encoding="utf-8") as batch_file:
                first_line = batch_file.readline()
            raw_batch = json.loads(first_line)
            batch = BrpcDiagBatch.model_validate(raw_batch)
        except (OSError, json.JSONDecodeError, ValidationError) as exc:
            raise BrpcDiagnosisWorkerError(
                f"BRPC 诊断 batch 首行无效: {batch_path}"
            ) from exc
        if batch.task_id != task_id:
            raise BrpcDiagnosisWorkerError(
                f"BRPC 诊断 batch task_id 不匹配: {batch.task_id!r}"
            )
        schema_path = (
            BrpcLogDiagnosisWorker._output_dir()
            / f"schema_{batch.schema_id}.json"
        )
        if not schema_path.is_file():
            raise BrpcDiagnosisWorkerError(
                f"BRPC 诊断输出 schema 文件不存在: {schema_path}"
            )
        return schema_path, batch_path

    @staticmethod
    async def _mark_failed(task_id: str, message: str) -> None:
        try:
            await BaseWorker.report(task_id, f"BRPC 诊断失败: {message}", 100.0)
        except Exception:
            logger.exception("failed to report BRPC diagnosis failure")
        try:
            await TaskPGManager.update_task(
                task_id,
                {"status": TaskStatusEnum.FAILED_PENDING_REMOVE.value},
            )
        except Exception:
            logger.exception("failed to update BRPC diagnosis task status")

    @staticmethod
    async def run(task_id: str, start_time: str | None = None) -> bool:
        try:
            task = await TaskPGManager.get_task_by_task_id(task_id)
            if task is None:
                logger.error("BRPC diagnosis task not found: %s", task_id)
                return False
            await TaskPGManager.update_task(
                task_id,
                {"status": TaskStatusEnum.RUNNING.value},
            )
            await BaseWorker.report(task_id, "开始 BRPC 日志诊断", 5.0)

            log_file = await LogFilePGManager.get_log_file_by_log_file_id(task.op_id)
            if log_file is None:
                raise BrpcDiagnosisWorkerError(
                    f"BRPC diagnosis LogFile does not exist: {task.op_id}"
                )
            selected_log = Path(log_file.file_path)
            if not selected_log.exists():
                raise BrpcDiagnosisWorkerError(
                    f"BRPC diagnosis log path not found: {selected_log}"
                )
            if start_time is None:
                start_time = BrpcLogDiagnosisWorker._resolve_start_time(task_id)
            else:
                start_time = BrpcLogDiagnosisWorker._validate_start_time(start_time)
            command = BrpcLogDiagnosisWorker._build_command(
                selected_log,
                start_time,
                task_id,
            )
            await BaseWorker.report(task_id, f"BRPC 诊断数据源: {selected_log}", 15.0)

            BrpcLogDiagnosisWorker._execute_tool(task_id, command)
            await BaseWorker.report(task_id, "BRPC 诊断工具运行完成", 60.0)

            current_task = await TaskPGManager.get_task_by_task_id(task_id)
            if current_task is None or current_task.status == TaskStatusEnum.CANCELLED:
                logger.warning("BRPC diagnosis task was cancelled: %s", task_id)
                return False

            schema_path, batch_path = BrpcLogDiagnosisWorker._result_paths(task_id)
            await BrpcDiagnosisImporter.import_result(
                schema_path=schema_path,
                batch_path=batch_path,
                expected_task_id=task_id,
            )
            await BaseWorker.report(task_id, "BRPC 诊断结果导入完成", 90.0)
            await TaskPGManager.update_task(
                task_id,
                {"status": TaskStatusEnum.SUCCESSFUL_PENDING_REMOVE.value},
            )
            await BaseWorker.report(task_id, "BRPC 诊断任务成功", 100.0)
            return True
        except Exception as exc:
            logger.exception("BRPC diagnosis task %s failed: %s", task_id, exc)
            await BrpcLogDiagnosisWorker._mark_failed(task_id, str(exc))
            return False

    @staticmethod
    async def stop(task_id: str) -> str | None:
        process = BrpcLogDiagnosisWorker._processes.get(task_id)
        terminated = False
        if process is not None:
            BrpcLogDiagnosisWorker._terminate_popen(process)
            BrpcLogDiagnosisWorker._unregister_process(task_id, process.pid)
            terminated = True
        else:
            terminated = BrpcLogDiagnosisWorker._terminate_pid(task_id)
        return task_id if terminated else None
