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
