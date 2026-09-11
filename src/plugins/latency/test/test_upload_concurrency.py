import asyncio
import io
import zipfile
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest
from starlette.datastructures import UploadFile

from latency.schemas.request import UpLoadLogFileConfig, UpLoadLogFilesRequest
from latency.services.log_file import LogFileService
from latency.task.task_handler import TaskHandler
from latency.task.process_handle import ProcessHandler
from latency.task.worker.base import BaseWorker
from latency.database.managers.task import TaskPGManager
from latency.database.managers.log_file import LogFilePGManager
from latency.common.zip_handler import ZipHandler
import latency.task.process_handle as process_handle_module


@pytest.mark.asyncio
async def test_ten_uploads_store_archives_without_extracting(monkeypatch, tmp_path):
    content = io.BytesIO()
    with zipfile.ZipFile(content, 'w') as archive:
        archive.writestr('ds_client_access.log', b'x' * (2 * 1024 * 1024))
    payload = content.getvalue()
    models = []

    async def save(batch):
        models.extend(batch)
        return [model.id for model in batch]

    class ChunkedUpload(UploadFile):
        async def read(self, size=-1):
            assert 0 < size <= 1024 * 1024
            return await super().read(size)

    monkeypatch.setattr(LogFileService, 'get_upload_path', lambda *p: str(tmp_path.joinpath(*p)))
    monkeypatch.setattr(LogFilePGManager, 'add_log_files', save)
    monkeypatch.setattr(TaskHandler, 'init_task', AsyncMock(return_value='task'))
    extract = AsyncMock(side_effect=AssertionError('must extract in background'))
    monkeypatch.setattr(ZipHandler, 'unzip_file', extract)

    async def upload(index):
        file = ChunkedUpload(io.BytesIO(payload), filename='logs.zip')
        try:
            return await LogFileService.upload_log_files(str(index), UpLoadLogFilesRequest(
                upload_log_file_configs=[UpLoadLogFileConfig(
                    name='logs.zip', source_type='upload', source=file,
                    log_type='KVCache',
                )],
            ))
        finally:
            await file.close()

    await asyncio.gather(*(upload(index) for index in range(10)))
    assert len(models) == 10
    assert len({model.file_path for model in models}) == 10
    for model in models:
        assert model.file_size == len(payload)
        assert zipfile.is_zipfile(model.file_path)
    extract.assert_not_awaited()


@pytest.mark.asyncio
async def test_full_pool_does_not_preprocess_pending_tasks(monkeypatch):
    monkeypatch.setattr(TaskPGManager, 'get_oldest_tasks_by_status', AsyncMock(
        return_value=[SimpleNamespace(id=str(i)) for i in range(10)]))
    monkeypatch.setattr(ProcessHandler, 'has_capacity', Mock(return_value=False))
    preprocess = AsyncMock()
    run = AsyncMock()
    monkeypatch.setattr(TaskHandler, '_preprocess_log_source', preprocess)
    monkeypatch.setattr(BaseWorker, 'run', run)
    await TaskHandler.handle_pending_tasks()
    preprocess.assert_not_awaited()
    run.assert_not_awaited()


def test_remove_task_terminates_the_complete_task_process_group(monkeypatch):
    class FakeProcess:
        pid = 24680

        def __init__(self):
            self.alive = True
            self.closed = False

        def is_alive(self):
            return self.alive

        def join(self, timeout=None):
            return None

        def close(self):
            self.closed = True

        def terminate(self):
            raise AssertionError("owned task groups must use killpg")

        def kill(self):
            raise AssertionError("owned task groups must use killpg")

    process = FakeProcess()
    signals = []

    def kill_group(pgid, sent_signal):
        signals.append((pgid, sent_signal))
        process.alive = False

    monkeypatch.setattr(ProcessHandler, "tasks", {"task-id": process})
    monkeypatch.setattr(process_handle_module.os, "getpgid", lambda pid: pid)
    monkeypatch.setattr(process_handle_module.os, "killpg", kill_group)

    assert ProcessHandler.remove_task("task-id") is True
    assert signals == [(process.pid, process_handle_module.signal.SIGTERM)]
    assert process.closed is True
    assert "task-id" not in ProcessHandler.tasks
